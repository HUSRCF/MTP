from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import torch

from mtp_expert_prefetch.admission import (
    novel_mtp_extra_mask,
    select_topk_mask,
)

ScoreReduce = Literal["max", "mean", "sum"]


@dataclass(frozen=True)
class ExpertPrefetchDescriptor:
    sample_idx: int
    layer_idx: int
    expert_id: int
    priority: int
    source: str
    score: float

    def as_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def build_priority_masks(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    max_extra: int = 8,
) -> dict[str, torch.Tensor]:
    """Build disjoint priority masks for runtime pre-map scheduling.

    Priority convention:
      P2: transition top-16, highest predicted-value protected candidates.
      P3: transition tail up to transition_topk, still protected.
      P4: first four novel MTP-token extras.
      P5: remaining MTP-token extras up to max_extra.

    P0/P1 are intentionally left for true-router misses and always-on/shared
    expert handling in the real runtime.
    """
    transition_head_k = min(16, int(transition_topk))
    transition_head = select_topk_mask(transition_scores, k=transition_head_k)
    transition_full = select_topk_mask(transition_scores, k=transition_topk)
    transition_tail = transition_full & ~transition_head
    mtp_extra_head = novel_mtp_extra_mask(
        transition_full,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=min(4, int(max_extra)),
    )
    mtp_extra_all = novel_mtp_extra_mask(
        transition_full,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    mtp_extra_tail = mtp_extra_all & ~mtp_extra_head
    return {
        "P2_transition_top16": transition_head,
        f"P3_transition_top17_to_{int(transition_topk)}": transition_tail,
        "P4_mtp_extra1_to_4": mtp_extra_head,
        f"P5_mtp_extra5_to_{max(int(max_extra), 4)}": mtp_extra_tail,
    }


def build_premap_descriptors(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    token_sample_indices: torch.Tensor,
    *,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    max_extra: int = 8,
    reduce: ScoreReduce = "max",
) -> list[ExpertPrefetchDescriptor]:
    """Convert token-level priority masks into sample/layer expert descriptors.

    The output is deduplicated over tokens inside each sample/layer. If the same
    expert appears in multiple tiers, the highest-priority tier wins.
    """
    _validate_scores(transition_scores, mtp_scores, token_sample_indices)
    priority_masks = build_priority_masks(
        transition_scores,
        mtp_scores,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    priorities = [
        ("P2_transition_top16", 2, "transition_head", transition_scores),
        (f"P3_transition_top17_to_{int(transition_topk)}", 3, "transition_tail", transition_scores),
        ("P4_mtp_extra1_to_4", 4, "mtp_token_extra_head", mtp_scores),
        (f"P5_mtp_extra5_to_{max(int(max_extra), 4)}", 5, "mtp_token_extra_tail", mtp_scores),
    ]

    descriptors: list[ExpertPrefetchDescriptor] = []
    sample_ids = token_sample_indices.to(torch.long).cpu()
    for sample_idx in torch.unique(sample_ids).tolist():
        rows = sample_ids.eq(int(sample_idx))
        if not rows.any():
            continue
        claimed = torch.zeros(
            transition_scores.shape[2:],
            dtype=torch.bool,
            device=transition_scores.device,
        )
        for mask_name, priority, source, scores in priorities:
            mask = priority_masks[mask_name][rows]
            score_rows = scores[rows]
            layer_expert_mask = mask.any(dim=(0, 1)) & ~claimed
            if not layer_expert_mask.any():
                continue
            layer_ids, expert_ids = torch.nonzero(layer_expert_mask, as_tuple=True)
            reduced_scores = _reduce_scores(score_rows, mask, reduce=reduce)
            for layer_idx, expert_id in zip(layer_ids.tolist(), expert_ids.tolist(), strict=True):
                descriptors.append(
                    ExpertPrefetchDescriptor(
                        sample_idx=int(sample_idx),
                        layer_idx=int(layer_idx),
                        expert_id=int(expert_id),
                        priority=int(priority),
                        source=source,
                        score=float(reduced_scores[layer_idx, expert_id].item()),
                    )
                )
            claimed |= layer_expert_mask
    descriptors.sort(
        key=lambda item: (
            item.sample_idx,
            item.layer_idx,
            item.priority,
            -item.score,
            item.expert_id,
        )
    )
    return descriptors


def descriptor_summary(
    descriptors: list[ExpertPrefetchDescriptor],
    *,
    expert_bytes: int | None = None,
) -> dict[str, object]:
    by_priority: dict[str, int] = {}
    by_source: dict[str, int] = {}
    per_sample_layer: dict[tuple[int, int], int] = {}
    for descriptor in descriptors:
        by_priority[str(descriptor.priority)] = by_priority.get(str(descriptor.priority), 0) + 1
        by_source[descriptor.source] = by_source.get(descriptor.source, 0) + 1
        key = (descriptor.sample_idx, descriptor.layer_idx)
        per_sample_layer[key] = per_sample_layer.get(key, 0) + 1
    counts = torch.tensor(list(per_sample_layer.values()), dtype=torch.float32)
    result: dict[str, object] = {
        "num_descriptors": len(descriptors),
        "by_priority": by_priority,
        "by_source": by_source,
        "per_sample_layer_count": _summary(counts),
    }
    if expert_bytes is not None:
        expert_bytes = int(expert_bytes)
        result["expert_bytes"] = expert_bytes
        result["total_descriptor_bytes"] = int(len(descriptors) * expert_bytes)
        result["per_sample_layer_bytes"] = _summary(counts * float(expert_bytes))
    return result


def _reduce_scores(
    scores: torch.Tensor,
    mask: torch.Tensor,
    *,
    reduce: ScoreReduce,
) -> torch.Tensor:
    masked = scores.float().masked_fill(~mask, 0.0)
    if reduce == "sum":
        return masked.sum(dim=(0, 1))
    if reduce == "mean":
        counts = mask.float().sum(dim=(0, 1)).clamp_min(1.0)
        return masked.sum(dim=(0, 1)) / counts
    if reduce == "max":
        return scores.float().masked_fill(~mask, -float("inf")).amax(dim=(0, 1)).clamp_min(0.0)
    msg = f"Unsupported score reduction: {reduce}"
    raise ValueError(msg)


def _validate_scores(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    token_sample_indices: torch.Tensor,
) -> None:
    if transition_scores.shape != mtp_scores.shape:
        msg = (
            "transition_scores and mtp_scores must share shape, got "
            f"{tuple(transition_scores.shape)} and {tuple(mtp_scores.shape)}"
        )
        raise ValueError(msg)
    if transition_scores.ndim != 4:
        msg = (
            "Expected scores with shape [tokens, future, layers, experts], got "
            f"{tuple(transition_scores.shape)}"
        )
        raise ValueError(msg)
    if int(token_sample_indices.numel()) != int(transition_scores.shape[0]):
        msg = "token_sample_indices length must match score token dimension."
        raise ValueError(msg)


def _summary(values: torch.Tensor) -> dict[str, float]:
    values = values.detach().float().cpu()
    if values.numel() == 0:
        return {"mean": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "mean": float(values.mean().item()),
        "p50": float(torch.quantile(values, 0.50).item()),
        "p90": float(torch.quantile(values, 0.90).item()),
        "p95": float(torch.quantile(values, 0.95).item()),
        "max": float(values.max().item()),
    }
