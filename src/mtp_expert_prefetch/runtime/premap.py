from __future__ import annotations

import hashlib
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


@dataclass(frozen=True)
class PremapAddressRecord:
    """Prepared descriptor/address handle without payload transfer.

    The address key is an audit/cache-manager key, not a device pointer. Keeping
    it explicit lets the runtime validate descriptor/address preparation without
    giving ready credit or moving expert payload bytes.
    """

    sample_idx: int
    layer_idx: int
    expert_id: int
    priority: int
    source: str
    score: float
    descriptor_slot: int
    address_key: str
    descriptor_bytes: int
    payload_bytes: int = 0

    def as_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


@dataclass(frozen=True)
class PremapPreparedPlan:
    """Compact plan produced by premap descriptor/address preparation."""

    records: tuple[PremapAddressRecord, ...]
    descriptor_count: int
    unique_experts: int
    unique_layers: int
    unique_sample_layers: int
    descriptor_bytes: int
    actual_bytes: int
    payload_bytes: int
    descriptor_hash: str
    address_hash: str
    address_namespace: str
    by_priority: dict[str, int]
    by_source: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["records"] = [record.as_dict() for record in self.records]
        return result


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


def prepare_premap_address_plan(
    descriptors: list[ExpertPrefetchDescriptor],
    *,
    descriptor_bytes: int = 4_096,
    address_namespace: str = "expert_weight_descriptor",
) -> PremapPreparedPlan:
    """Prepare descriptor/address handles for a premap-only runtime action.

    This intentionally does not move payload bytes. It creates deterministic
    descriptor slots and address keys that a cache-manager shim can audit or use
    for low-cost descriptor/address setup.
    """

    descriptor_bytes = int(descriptor_bytes)
    if descriptor_bytes < 0:
        msg = f"descriptor_bytes must be non-negative, got {descriptor_bytes}"
        raise ValueError(msg)
    namespace = str(address_namespace or "expert_weight_descriptor")
    ordered = sorted(
        descriptors,
        key=lambda item: (
            int(item.sample_idx),
            int(item.layer_idx),
            int(item.priority),
            -float(item.score),
            int(item.expert_id),
            str(item.source),
        ),
    )
    records: list[PremapAddressRecord] = []
    by_priority: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for slot, descriptor in enumerate(ordered):
        priority_key = str(int(descriptor.priority))
        source_key = str(descriptor.source)
        by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
        by_source[source_key] = by_source.get(source_key, 0) + 1
        address_key = (
            f"{namespace}:"
            f"l{int(descriptor.layer_idx)}:"
            f"e{int(descriptor.expert_id)}"
        )
        records.append(
            PremapAddressRecord(
                sample_idx=int(descriptor.sample_idx),
                layer_idx=int(descriptor.layer_idx),
                expert_id=int(descriptor.expert_id),
                priority=int(descriptor.priority),
                source=source_key,
                score=float(descriptor.score),
                descriptor_slot=int(slot),
                address_key=address_key,
                descriptor_bytes=descriptor_bytes,
                payload_bytes=0,
            )
        )
    descriptor_hash, address_hash = hash_premap_address_records(records)
    return PremapPreparedPlan(
        records=tuple(records),
        descriptor_count=len(records),
        unique_experts=len({record.expert_id for record in records}),
        unique_layers=len({record.layer_idx for record in records}),
        unique_sample_layers=len({(record.sample_idx, record.layer_idx) for record in records}),
        descriptor_bytes=descriptor_bytes,
        actual_bytes=len(records) * descriptor_bytes,
        payload_bytes=0,
        descriptor_hash=descriptor_hash,
        address_hash=address_hash,
        address_namespace=namespace,
        by_priority=by_priority,
        by_source=by_source,
    )


def hash_premap_address_records(
    records: tuple[PremapAddressRecord, ...] | list[PremapAddressRecord],
) -> tuple[str, str]:
    descriptor_hasher = hashlib.sha256()
    address_hasher = hashlib.sha256()
    for record in records:
        descriptor_row = (
            int(record.sample_idx),
            int(record.layer_idx),
            int(record.expert_id),
            int(record.priority),
            str(record.source),
            f"{float(record.score):.9g}",
            int(record.descriptor_slot),
            str(record.address_key),
        )
        address_row = (
            int(record.descriptor_slot),
            str(record.address_key),
            int(record.sample_idx),
            int(record.layer_idx),
            int(record.expert_id),
            int(record.priority),
            str(record.source),
        )
        descriptor_hasher.update("|".join(map(str, descriptor_row)).encode("utf-8"))
        descriptor_hasher.update(b"\n")
        address_hasher.update("|".join(map(str, address_row)).encode("utf-8"))
        address_hasher.update(b"\n")
    return descriptor_hasher.hexdigest(), address_hasher.hexdigest()


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
