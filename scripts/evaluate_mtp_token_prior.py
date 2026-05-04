#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.training import (  # noqa: E402
    TokenFrequencyTable,
    apply_token_frequency_table,
    apply_transition_matrix,
    build_mtp_router_alignment,
    build_token_frequency_table,
    mass_coverage_at_m,
    recall_at_m,
    router_topk_to_dense_feature,
    target_expert_ids_to_dense_weights,
    target_expert_ids_to_multihot,
    top1_risk_at_m,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.training.alignment_merge import (  # noqa: E402
    manifest_record_path,
    read_trace_manifest,
)
from mtp_expert_prefetch.tracing import load_trace_payload  # noqa: E402
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402

DEFAULT_MERGED_MANIFEST = Path("data/traces/aya_dataset_smoke_merged_mtp_vllm/manifest.jsonl")
DEFAULT_MTP_TOKEN_MANIFEST = Path(
    "data/traces/mtp_token_topm_64sample_prefc_fixed/manifest.jsonl"
)


@dataclass(frozen=True)
class AlignmentSample:
    sample_idx: int
    batch: dict[str, torch.Tensor]


@dataclass(frozen=True)
class MtpTokenSample:
    sample_idx: int
    input_ids: torch.Tensor
    topm_ids: torch.Tensor
    topm_probs: torch.Tensor


@dataclass(frozen=True)
class TensorDataset:
    labels: torch.Tensor
    target_mass: torch.Tensor
    current_feature: torch.Tensor
    source_token_ids: torch.Tensor
    target_token_ids: torch.Tensor
    mtp_offset_token_ids: torch.Tensor
    mtp_topm_ids: torch.Tensor
    mtp_topm_probs: torch.Tensor
    sample_indices: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate MTP predicted-token expert-prior baselines."
    )
    parser.add_argument("--merged-manifest", type=Path, default=DEFAULT_MERGED_MANIFEST)
    parser.add_argument("--mtp-token-manifest", type=Path, default=DEFAULT_MTP_TOKEN_MANIFEST)
    parser.add_argument("--output", type=Path, default=Path("outputs/mtp_token_prior_metrics.json"))
    parser.add_argument("--future-window", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--num-experts", type=int, default=256)
    parser.add_argument("--val-fraction", type=float, default=0.25)
    parser.add_argument("--recall-at-ms", default="8,16,32")
    parser.add_argument("--fusion-alphas", default="0,0.25,0.5,1,2")
    parser.add_argument("--fusion-beta", type=float, default=0.0)
    parser.add_argument("--alignment-token-offsets", default="0,1,2")
    parser.add_argument("--union-mtp-topk", type=int, default=16)
    parser.add_argument("--union-transition-topk", type=int, default=32)
    parser.add_argument("--candidate-pool-mtp-topks", default="8,16,32,64,128")
    parser.add_argument("--candidate-pool-transition-topk", type=int, default=32)
    parser.add_argument("--transition-tail-baseline-topks", default="32,36,40")
    parser.add_argument("--dynamic-extra-mtp-topk", type=int, default=16)
    parser.add_argument("--dynamic-max-extras", default="1,2,4,8")
    parser.add_argument("--fixed-budget-total", type=int, default=32)
    parser.add_argument("--fixed-budget-mtp-topk", type=int, default=64)
    parser.add_argument("--fixed-budget-replacements", default="1,2,4,8")
    parser.add_argument("--layer-aware-cutoffs", default="0,1,2,3,4,8,40")
    parser.add_argument("--layer-aware-mtp-topk", type=int, default=64)
    parser.add_argument("--layer-aware-max-extra", type=int, default=4)
    parser.add_argument("--layer-aware-transition-tail-topk", type=int, default=36)
    parser.add_argument(
        "--mtp-sidecar-model",
        default="Intel/Qwen3.6-35B-A3B-int4-AutoRound",
    )
    parser.add_argument(
        "--router-trace-model",
        default="cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit",
    )
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in str(value).split(",") if part.strip()]


def _parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in str(value).split(",") if part.strip()]


def _split_positions(num_samples: int, val_fraction: float) -> tuple[list[int], list[int]]:
    if num_samples == 1:
        return [0], []
    val_count = int(round(num_samples * val_fraction))
    val_count = min(num_samples - 1, max(1, val_count))
    return list(range(num_samples - val_count)), list(range(num_samples - val_count, num_samples))


def _load_alignment_samples(
    manifest_path: Path,
    *,
    future_window: int,
    max_samples: int | None,
) -> list[AlignmentSample]:
    records = read_trace_manifest(manifest_path)
    if max_samples is not None:
        records = records[: int(max_samples)]
    samples: list[AlignmentSample] = []
    for record in records:
        payload = load_trace_payload(manifest_record_path(record))
        alignment = build_mtp_router_alignment(payload, future_window=future_window)
        samples.append(
            AlignmentSample(
                sample_idx=int(record.get("sample_idx", len(samples))),
                batch=alignment.as_dict(),
            )
        )
    if not samples:
        msg = f"No alignment samples loaded from {manifest_path}"
        raise RuntimeError(msg)
    return samples


def _load_mtp_token_samples(manifest_path: Path) -> dict[int, MtpTokenSample]:
    records = read_trace_manifest(manifest_path)
    samples: dict[int, MtpTokenSample] = {}
    for record in records:
        path = manifest_record_path(record)
        payload = torch.load(path, map_location="cpu", weights_only=False)
        input_ids = torch.as_tensor(payload["input_ids"]).to(torch.long)
        topm_ids = torch.as_tensor(payload["native_mtp_token_topm_ids"]).to(torch.long)
        topm_probs = torch.as_tensor(payload["native_mtp_token_topm_probs"]).to(torch.float32)
        if input_ids.ndim == 2:
            input_ids = input_ids[0]
        if topm_ids.ndim == 3:
            topm_ids = topm_ids[0]
            topm_probs = topm_probs[0]
        if topm_ids.ndim != 2 or topm_probs.shape != topm_ids.shape:
            msg = (
                "MTP token top-M tensors must have shape [tokens, top_m], "
                f"got ids={tuple(topm_ids.shape)}, probs={tuple(topm_probs.shape)}"
            )
            raise ValueError(msg)
        sample_idx = int(record["sample_idx"])
        samples[sample_idx] = MtpTokenSample(sample_idx, input_ids, topm_ids, topm_probs)
    if not samples:
        msg = f"No MTP token samples loaded from {manifest_path}"
        raise RuntimeError(msg)
    return samples


def _samples_to_dataset(
    samples: list[AlignmentSample],
    token_samples: dict[int, MtpTokenSample],
    positions: list[int],
    *,
    num_experts: int,
    max_tokens: int | None,
    alignment_offsets: list[int],
    device: torch.device,
) -> TensorDataset | None:
    if not positions:
        return None

    labels_parts: list[torch.Tensor] = []
    mass_parts: list[torch.Tensor] = []
    current_parts: list[torch.Tensor] = []
    source_token_parts: list[torch.Tensor] = []
    target_token_parts: list[torch.Tensor] = []
    mtp_offset_token_parts: list[torch.Tensor] = []
    mtp_id_parts: list[torch.Tensor] = []
    mtp_prob_parts: list[torch.Tensor] = []
    sample_indices: list[int] = []

    for position in positions:
        sample = samples[position]
        if sample.sample_idx not in token_samples:
            msg = f"Missing MTP token top-M sidecar for sample_idx={sample.sample_idx}"
            raise KeyError(msg)
        batch = sample.batch
        sidecar = token_samples[sample.sample_idx]
        target_ids = batch["target_expert_ids"].to(torch.long)
        target_weights = batch["target_expert_weights"].to(torch.float32)
        current_ids = batch["current_expert_ids"].to(torch.long)
        current_weights = batch["current_expert_weights"].to(torch.float32)
        source_token_ids = batch["source_token_ids"].to(torch.long)
        target_token_ids = batch["target_token_ids"].to(torch.long)
        source_indices = batch["source_token_indices"].to(torch.long)

        token_count = min(
            int(target_ids.shape[0]),
            int(sidecar.topm_ids.shape[0]),
            int(source_indices.shape[0]),
        )
        if max_tokens is not None:
            token_count = min(token_count, int(max_tokens))
        if token_count <= 0:
            continue

        target_ids = target_ids[:token_count]
        target_weights = target_weights[:token_count]
        current_ids = current_ids[:token_count]
        current_weights = current_weights[:token_count]
        source_token_ids = source_token_ids[:token_count]
        target_token_ids = target_token_ids[:token_count]
        source_indices = source_indices[:token_count]

        mtp_topm_ids = sidecar.topm_ids[source_indices]
        mtp_topm_probs = sidecar.topm_probs[source_indices]
        offset_ids = torch.full(
            (token_count, len(alignment_offsets)),
            -1,
            dtype=torch.long,
        )
        for offset_position, offset in enumerate(alignment_offsets):
            candidate_indices = source_indices + int(offset)
            valid = (candidate_indices >= 0) & (candidate_indices < sidecar.input_ids.shape[0])
            if valid.any():
                offset_ids[valid, offset_position] = sidecar.input_ids[candidate_indices[valid]]
        labels_parts.append(target_expert_ids_to_multihot(target_ids, num_experts=num_experts))
        mass_parts.append(
            target_expert_ids_to_dense_weights(
                target_ids,
                target_weights,
                num_experts=num_experts,
            )
        )
        current_parts.append(
            router_topk_to_dense_feature(
                current_ids,
                current_weights,
                num_experts=num_experts,
            )
        )
        source_token_parts.append(source_token_ids)
        target_token_parts.append(target_token_ids)
        mtp_offset_token_parts.append(offset_ids)
        mtp_id_parts.append(mtp_topm_ids)
        mtp_prob_parts.append(mtp_topm_probs)
        sample_indices.append(sample.sample_idx)

    if not labels_parts:
        msg = "No token examples were built."
        raise RuntimeError(msg)

    return TensorDataset(
        labels=torch.cat(labels_parts, dim=0).to(device),
        target_mass=torch.cat(mass_parts, dim=0).to(device),
        current_feature=torch.cat(current_parts, dim=0).to(device),
        source_token_ids=torch.cat(source_token_parts, dim=0).to(device),
        target_token_ids=torch.cat(target_token_parts, dim=0).to(device),
        mtp_offset_token_ids=torch.cat(mtp_offset_token_parts, dim=0).to(device),
        mtp_topm_ids=torch.cat(mtp_id_parts, dim=0).to(device),
        mtp_topm_probs=torch.cat(mtp_prob_parts, dim=0).to(device),
        sample_indices=sample_indices,
    )


def _apply_mtp_token_frequency_table(
    table: TokenFrequencyTable,
    topm_ids: torch.Tensor,
    topm_probs: torch.Tensor,
    *,
    device: torch.device,
) -> torch.Tensor:
    if topm_ids.ndim != 2 or topm_probs.shape != topm_ids.shape:
        msg = (
            "MTP token ids/probs must share shape [tokens, top_m], "
            f"got ids={tuple(topm_ids.shape)}, probs={tuple(topm_probs.shape)}"
        )
        raise ValueError(msg)
    fallback = table.fallback
    if fallback.shape[1] != 1:
        msg = "MTP token prior currently supports future_window=1 only."
        raise ValueError(msg)
    num_tokens = int(topm_ids.shape[0])
    output = torch.zeros(
        num_tokens,
        int(fallback.shape[1]),
        int(fallback.shape[2]),
        int(fallback.shape[3]),
        dtype=torch.float32,
    )
    ids = topm_ids.to(torch.long).cpu()
    probs = topm_probs.to(torch.float32).cpu()
    fallback_value = fallback[0, 0]
    for token_index in range(num_tokens):
        weights = probs[token_index]
        weight_sum = float(weights.sum().item())
        if weight_sum <= 0.0:
            weights = torch.full_like(weights, 1.0 / max(1, weights.numel()))
        else:
            weights = weights / weight_sum
        mixed = torch.zeros_like(fallback_value)
        for candidate_index, weight in enumerate(weights):
            token_id = int(ids[token_index, candidate_index])
            value = table.values.get((0, token_id), fallback_value)
            mixed = mixed + float(weight.item()) * value
        output[token_index, 0] = mixed
    return output.to(device=device)


def _safe_log(scores: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    return torch.log(scores.float().clamp_min(eps))


def _union_mask(logits: torch.Tensor, *, k: int) -> torch.Tensor:
    k = min(int(k), int(logits.shape[-1]))
    topk = torch.topk(logits.float(), k=k, dim=-1).indices
    mask = torch.zeros_like(logits, dtype=torch.bool)
    mask.scatter_(-1, topk, True)
    return mask


def _candidate_union_logits(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    frequency_scores: torch.Tensor,
    *,
    alpha: float,
    beta: float,
    transition_topk: int,
    mtp_topk: int,
) -> torch.Tensor:
    transition_logits = _safe_log(transition_scores)
    fused = transition_logits + alpha * _safe_log(mtp_scores)
    if beta:
        fused = fused + beta * _safe_log(frequency_scores.expand_as(fused))
    mask = _union_mask(transition_scores, k=transition_topk) | _union_mask(mtp_scores, k=mtp_topk)
    return fused.masked_fill(~mask, -1.0e30)


def _metrics_for_logits(
    logits: torch.Tensor,
    labels: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    recall_ms: list[int],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for m in recall_ms:
        recall = recall_at_m(logits, labels, m=m)
        mass = mass_coverage_at_m(logits, target_mass, m=m)
        risk = top1_risk_at_m(logits, target_mass, m=m)
        metrics[str(m)] = {
            "recall": recall.recall,
            "mass_coverage": mass.coverage,
            "top1_hit_rate": risk.top1_hit_rate,
            "weighted_top1_miss": risk.weighted_top1_miss,
        }
    return metrics


def _alignment_metrics(
    dataset: TensorDataset,
    *,
    alignment_offsets: list[int],
) -> dict[str, float | dict[str, int] | dict[str, dict[str, float]]]:
    target = dataset.target_token_ids[:, 0].to(torch.long)
    topm = dataset.mtp_topm_ids.to(torch.long)
    probs = dataset.mtp_topm_probs.to(torch.float32)
    top1 = topm[:, 0]
    hits = topm.eq(target[:, None])
    target_prob = (hits.to(torch.float32) * probs).sum(dim=-1)
    normalized_probs = probs / probs.sum(dim=-1, keepdim=True).clamp_min(1e-12)
    entropy = -(normalized_probs * normalized_probs.clamp_min(1e-12).log()).sum(dim=-1)
    unique_top1, counts = torch.unique(top1.cpu(), return_counts=True)
    top_counts = sorted(
        zip(unique_top1.tolist(), counts.tolist(), strict=True),
        key=lambda item: item[1],
        reverse=True,
    )[:10]
    offset_metrics = {}
    for offset_position, offset in enumerate(alignment_offsets):
        offset_target = dataset.mtp_offset_token_ids[:, offset_position].to(torch.long)
        valid = offset_target >= 0
        if not valid.any():
            offset_metrics[str(offset)] = {
                "num_valid": 0,
                "top1_accuracy": 0.0,
                "topm_recall": 0.0,
                "mean_prob_assigned_in_topm": 0.0,
            }
            continue
        offset_topm = topm[valid]
        offset_probs = probs[valid]
        offset_target = offset_target[valid]
        offset_hits = offset_topm.eq(offset_target[:, None])
        offset_target_prob = (offset_hits.to(torch.float32) * offset_probs).sum(dim=-1)
        offset_metrics[str(offset)] = {
            "num_valid": int(offset_target.numel()),
            "top1_accuracy": float(offset_topm[:, 0].eq(offset_target).float().mean().item()),
            "topm_recall": float(offset_hits.any(dim=-1).float().mean().item()),
            "mean_prob_assigned_in_topm": float(offset_target_prob.mean().item()),
        }
    return {
        "num_examples": int(target.numel()),
        "top1_accuracy_as_next_token": float(top1.eq(target).float().mean().item()),
        "topm_recall_as_next_token": float(hits.any(dim=-1).float().mean().item()),
        "mean_prob_assigned_to_next_token_in_topm": float(target_prob.mean().item()),
        "mean_topm_entropy": float(entropy.mean().item()),
        "max_topm_entropy": float(math.log(max(1, topm.shape[-1]))),
        "offset_metrics": offset_metrics,
        "top1_token_counts": {str(int(token)): int(count) for token, count in top_counts},
    }


def _introduced_mass(
    logits: torch.Tensor,
    transition_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    m: int,
) -> dict[str, float]:
    pred_mask = _union_mask(logits, k=m)
    transition_mask = _union_mask(transition_scores, k=m)
    introduced = pred_mask & ~transition_mask
    overlap = pred_mask & transition_mask
    mass = target_mass.float().clamp_min(0.0)
    introduced_mass = mass[introduced].sum()
    total_mass = mass.sum().clamp_min(1e-12)
    overlap_count = overlap.to(torch.float32).sum()
    pred_count = pred_mask.to(torch.float32).sum().clamp_min(1.0)
    return {
        "introduced_mass_fraction": float((introduced_mass / total_mass).item()),
        "introduced_expert_fraction": float(
            (introduced.to(torch.float32).sum() / pred_count).item()
        ),
        "overlap_fraction": float((overlap_count / pred_count).item()),
    }


def _mask_metrics(
    mask: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    base_mask: torch.Tensor | None = None,
) -> dict[str, float]:
    mass = target_mass.float().clamp_min(0.0)
    total_mass = mass.sum().clamp_min(1e-12)
    pool_mass = mass[mask].sum()
    true_top1 = mass.argmax(dim=-1, keepdim=True)
    true_top1_weight = mass.gather(-1, true_top1).squeeze(-1)
    top1_hit = mask.gather(-1, true_top1).squeeze(-1).to(torch.float32)
    weighted_top1_miss = (true_top1_weight * (1.0 - top1_hit)).mean()
    avg_pool_size = mask.to(torch.float32).sum(-1).mean()

    metrics = {
        "pool_mass_coverage": float((pool_mass / total_mass).item()),
        "avg_pool_size": float(avg_pool_size.item()),
        "top1_hit_rate": float(top1_hit.mean().item()),
        "weighted_top1_miss": float(weighted_top1_miss.item()),
    }
    if base_mask is not None:
        introduced = mask & ~base_mask
        introduced_count = introduced.to(torch.float32).sum()
        introduced_mass = mass[introduced].sum()
        metrics.update(
            {
                "avg_extra_count": float(
                    introduced.to(torch.float32).sum(-1).mean().item()
                ),
                "introduced_mass_fraction": float((introduced_mass / total_mass).item()),
                "introduced_mass_per_added_expert": float(
                    (introduced_mass / introduced_count.clamp_min(1.0)).item()
                ),
            }
        )
    return metrics


def _candidate_pool_diagnostics(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topks: list[int],
) -> dict[str, dict[str, float]]:
    transition_mask = _union_mask(transition_scores, k=transition_topk)
    diagnostics = {
        "transition_only": _mask_metrics(transition_mask, target_mass),
    }
    transition_mass = diagnostics["transition_only"]["pool_mass_coverage"]
    transition_top1_risk = diagnostics["transition_only"]["weighted_top1_miss"]
    for mtp_topk in mtp_topks:
        pool = transition_mask | _union_mask(mtp_scores, k=int(mtp_topk))
        metrics = _mask_metrics(pool, target_mass, base_mask=transition_mask)
        metrics["delta_pool_mass_coverage"] = metrics["pool_mass_coverage"] - transition_mass
        metrics["delta_weighted_top1_miss"] = (
            metrics["weighted_top1_miss"] - transition_top1_risk
        )
        diagnostics[f"transition_top{transition_topk}_union_mtp_top{mtp_topk}"] = metrics
    return diagnostics


def _transition_tail_budget_diagnostics(
    transition_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    transition_topks: list[int],
    base_topk: int,
) -> dict[str, dict[str, float]]:
    """Measure the value of spending extra budget only on transition tail.

    This is the same-candidate-count control for MTP extra-budget expansion:
    transition_top36/top40 answers whether MTP_extra4/8 adds information beyond
    simply keeping more transition-ranked experts.
    """
    base_mask = _union_mask(transition_scores, k=base_topk)
    base_metrics = _mask_metrics(base_mask, target_mass)
    base_mass = base_metrics["pool_mass_coverage"]
    base_top1_risk = base_metrics["weighted_top1_miss"]

    diagnostics: dict[str, dict[str, float]] = {}
    for topk in sorted({int(k) for k in transition_topks if int(k) > 0}):
        mask = _union_mask(transition_scores, k=topk)
        metrics = _mask_metrics(mask, target_mass, base_mask=base_mask)
        metrics["delta_pool_mass_coverage"] = metrics["pool_mass_coverage"] - base_mass
        metrics["delta_weighted_top1_miss"] = (
            metrics["weighted_top1_miss"] - base_top1_risk
        )
        metrics["extra_budget_vs_base"] = float(max(0, topk - base_topk))
        diagnostics[f"transition_top{topk}"] = metrics
    return diagnostics


def _novel_mtp_extra_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
) -> torch.Tensor:
    """Select the first `max_extra` MTP-ranked experts absent from `base_mask`.

    The selection is fully vectorized over all prefix dimensions. It preserves
    MTP score rank order through cumulative counts over the top-k list.
    """
    max_extra = max(0, int(max_extra))
    if max_extra == 0:
        return torch.zeros_like(base_mask)
    mtp_topk = min(int(mtp_topk), int(mtp_scores.shape[-1]))
    ranked = torch.topk(mtp_scores.float(), k=mtp_topk, dim=-1).indices
    base_hits = base_mask.gather(-1, ranked)
    novel = ~base_hits
    selected_rank = novel & (novel.to(torch.int16).cumsum(dim=-1) <= max_extra)
    selected = torch.zeros_like(base_mask)
    selected.scatter_(-1, ranked, selected_rank)
    return selected & ~base_mask


def _dynamic_extra_budget_diagnostics(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    max_extras: list[int],
) -> dict[str, dict[str, float]]:
    """Add at most N novel MTP-token candidates on top of transition_topK.

    This models the runtime policy we actually want to test: keep transition as
    the protected candidate generator, and spend only a small optional budget on
    MTP-token experts that are not already covered by transition_topK.
    """
    transition_mask = _union_mask(transition_scores, k=transition_topk)
    base_metrics = _mask_metrics(transition_mask, target_mass)
    base_mass = base_metrics["pool_mass_coverage"]
    base_top1_risk = base_metrics["weighted_top1_miss"]

    diagnostics = {"transition_only": base_metrics}
    for max_extra in max_extras:
        selected_extra = _novel_mtp_extra_mask(
            transition_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=int(max_extra),
        )
        pool = transition_mask | selected_extra
        metrics = _mask_metrics(pool, target_mass, base_mask=transition_mask)
        metrics["delta_pool_mass_coverage"] = metrics["pool_mass_coverage"] - base_mass
        metrics["delta_weighted_top1_miss"] = metrics["weighted_top1_miss"] - base_top1_risk
        diagnostics[f"transition_top{transition_topk}_plus_mtp_top{mtp_topk}_max_extra{max_extra}"] = (
            metrics
        )
    return diagnostics


def _dynamic_extra_budget_masks(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    max_extras: list[int],
) -> dict[str, torch.Tensor]:
    transition_mask = _union_mask(transition_scores, k=transition_topk)

    masks = {f"transition_top{transition_topk}": transition_mask}
    for max_extra in max_extras:
        selected_extra = _novel_mtp_extra_mask(
            transition_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=int(max_extra),
        )
        masks[
            f"transition_top{transition_topk}_plus_mtp_top{mtp_topk}_max_extra{max_extra}"
        ] = transition_mask | selected_extra
    return masks


def _per_layer_dynamic_extra_budget_diagnostics(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    max_extras: list[int],
) -> dict[str, dict[str, dict[str, float]]]:
    masks = _dynamic_extra_budget_masks(
        transition_scores,
        mtp_scores,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extras=max_extras,
    )
    baseline_name = f"transition_top{transition_topk}"
    baseline = masks[baseline_name]
    if target_mass.ndim != 4:
        msg = f"Expected target_mass [tokens, future, layers, experts], got {target_mass.shape}"
        raise ValueError(msg)
    layer_count = int(target_mass.shape[2])
    diagnostics: dict[str, dict[str, dict[str, float]]] = {}
    for method_name, mask in masks.items():
        method_layers: dict[str, dict[str, float]] = {}
        for layer_idx in range(layer_count):
            layer_slice = slice(layer_idx, layer_idx + 1)
            layer_metrics = _mask_metrics(
                mask[:, :, layer_slice, :],
                target_mass[:, :, layer_slice, :],
                base_mask=baseline[:, :, layer_slice, :] if method_name != baseline_name else None,
            )
            if method_name != baseline_name:
                base_metrics = _mask_metrics(
                    baseline[:, :, layer_slice, :],
                    target_mass[:, :, layer_slice, :],
                )
                layer_metrics["delta_pool_mass_coverage"] = (
                    layer_metrics["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
                )
                layer_metrics["delta_weighted_top1_miss"] = (
                    layer_metrics["weighted_top1_miss"]
                    - base_metrics["weighted_top1_miss"]
                )
            method_layers[f"layer_{layer_idx:02d}"] = layer_metrics
        if method_name != baseline_name:
            deltas = [
                value["delta_pool_mass_coverage"]
                for value in method_layers.values()
            ]
            risk_deltas = [
                value["delta_weighted_top1_miss"]
                for value in method_layers.values()
            ]
            method_layers["_summary"] = {
                "positive_delta_mass_layers": float(sum(delta > 0.0 for delta in deltas)),
                "nonpositive_top1_miss_delta_layers": float(
                    sum(delta <= 0.0 for delta in risk_deltas)
                ),
                "mean_delta_pool_mass_coverage": float(sum(deltas) / len(deltas)),
                "mean_delta_weighted_top1_miss": float(
                    sum(risk_deltas) / len(risk_deltas)
                ),
                "best_delta_pool_mass_coverage": float(max(deltas)),
                "worst_delta_pool_mass_coverage": float(min(deltas)),
            }
        diagnostics[method_name] = method_layers
    return diagnostics


def _fixed_budget_replacement_diagnostics(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    total_budget: int,
    mtp_topk: int,
    replacements: list[int],
) -> dict[str, dict[str, float]]:
    """Keep total pool size fixed while replacing transition tail candidates.

    A replacement value R builds:
        transition_top(total_budget - R) + up to R highest-ranked MTP candidates
        not already in that protected transition prefix.

    This distinguishes opportunistic extra-budget expansion from the stronger
    claim that MTP-token candidates can replace transition tail experts.
    """
    total_budget = min(int(total_budget), int(transition_scores.shape[-1]))
    baseline_mask = _union_mask(transition_scores, k=total_budget)
    base_metrics = _mask_metrics(baseline_mask, target_mass)
    base_mass = base_metrics["pool_mass_coverage"]
    base_top1_risk = base_metrics["weighted_top1_miss"]

    diagnostics = {f"transition_top{total_budget}": base_metrics}
    for replacement_count in replacements:
        replacement_count = max(0, int(replacement_count))
        protected_k = max(0, total_budget - replacement_count)
        if protected_k:
            protected_mask = _union_mask(transition_scores, k=protected_k)
        else:
            protected_mask = torch.zeros_like(baseline_mask)
        mtp_extra = _novel_mtp_extra_mask(
            protected_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=total_budget - protected_k,
        )
        pool = protected_mask | mtp_extra
        metrics = _mask_metrics(pool, target_mass, base_mask=baseline_mask)
        replaced_from_transition_tail = baseline_mask & ~pool
        metrics.update(
            {
                "protected_transition_k": float(protected_k),
                "requested_replacements": float(replacement_count),
                "avg_mtp_selected_count": float(
                    mtp_extra.to(torch.float32).sum(-1).mean().item()
                ),
                "avg_replaced_transition_count": float(
                    replaced_from_transition_tail.to(torch.float32).sum(-1).mean().item()
                ),
                "replaced_transition_mass_fraction": float(
                    (
                        target_mass.float().clamp_min(0.0)[replaced_from_transition_tail].sum()
                        / target_mass.float().clamp_min(0.0).sum().clamp_min(1e-12)
                    ).item()
                ),
            }
        )
        metrics["delta_pool_mass_coverage"] = metrics["pool_mass_coverage"] - base_mass
        metrics["delta_weighted_top1_miss"] = metrics["weighted_top1_miss"] - base_top1_risk
        diagnostics[
            f"transition_top{protected_k}_plus_mtp_top{mtp_topk}_capped_top{total_budget}"
        ] = metrics
    return diagnostics


def _layer_aware_same_budget_diagnostics(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    base_topk: int,
    early_transition_topk: int,
    mtp_topk: int,
    max_extra: int,
    early_layer_cutoffs: list[int],
) -> dict[str, dict[str, float]]:
    """Use transition tail for early layers and MTP extras for later layers.

    MTP-token extras have less lead time in early layers. This diagnostic keeps
    the same nominal candidate count as extra-budget MTP (for example 36) while
    replacing the early-layer MTP extras with transition tail candidates.
    """
    if target_mass.ndim != 4:
        msg = f"Expected target_mass [tokens, future, layers, experts], got {target_mass.shape}"
        raise ValueError(msg)
    layer_count = int(target_mass.shape[2])
    base_mask = _union_mask(transition_scores, k=base_topk)
    early_mask = _union_mask(transition_scores, k=early_transition_topk)
    mtp_extra = _novel_mtp_extra_mask(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    late_mask = base_mask | mtp_extra
    base_metrics = _mask_metrics(base_mask, target_mass)
    base_mass = base_metrics["pool_mass_coverage"]
    base_top1_risk = base_metrics["weighted_top1_miss"]

    diagnostics: dict[str, dict[str, float]] = {
        f"transition_top{base_topk}": base_metrics,
        f"all_layers_transition_top{early_transition_topk}": _mask_metrics(
            early_mask,
            target_mass,
            base_mask=base_mask,
        ),
        f"all_layers_mtp_extra{max_extra}": _mask_metrics(
            late_mask,
            target_mass,
            base_mask=base_mask,
        ),
    }
    for value in diagnostics.values():
        value["delta_pool_mass_coverage"] = value["pool_mass_coverage"] - base_mass
        value["delta_weighted_top1_miss"] = (
            value["weighted_top1_miss"] - base_top1_risk
        )

    layer_ids = torch.arange(layer_count, device=target_mass.device).view(1, 1, layer_count, 1)
    for cutoff in sorted({int(value) for value in early_layer_cutoffs}):
        cutoff = min(max(0, cutoff), layer_count)
        early_layer_mask = layer_ids < cutoff
        mixed = torch.where(early_layer_mask, early_mask, late_mask)
        metrics = _mask_metrics(mixed, target_mass, base_mask=base_mask)
        metrics["delta_pool_mass_coverage"] = metrics["pool_mass_coverage"] - base_mass
        metrics["delta_weighted_top1_miss"] = (
            metrics["weighted_top1_miss"] - base_top1_risk
        )
        metrics["early_layers_use_transition_tail"] = float(cutoff)
        metrics["late_layers_use_mtp_extra"] = float(layer_count - cutoff)
        diagnostics[
            (
                f"early_layers_0_to_{cutoff - 1}_transition_top{early_transition_topk}"
                f"_late_mtp_extra{max_extra}"
            )
            if cutoff
            else f"all_layers_mtp_extra{max_extra}_alias"
        ] = metrics
    return diagnostics


def main() -> None:
    args = parse_args()
    if int(args.future_window) != 1:
        msg = "MTP predicted-token prior evaluator currently expects --future-window 1."
        raise ValueError(msg)
    recall_ms = _parse_int_list(args.recall_at_ms)
    fusion_alphas = _parse_float_list(args.fusion_alphas)
    alignment_offsets = _parse_int_list(args.alignment_token_offsets)
    candidate_pool_mtp_topks = _parse_int_list(args.candidate_pool_mtp_topks)
    transition_tail_baseline_topks = _parse_int_list(args.transition_tail_baseline_topks)
    dynamic_max_extras = _parse_int_list(args.dynamic_max_extras)
    fixed_budget_replacements = _parse_int_list(args.fixed_budget_replacements)
    layer_aware_cutoffs = _parse_int_list(args.layer_aware_cutoffs)
    project_root = find_project_root(args.merged_manifest)
    merged_manifest = resolve_path(args.merged_manifest, base_dir=project_root)
    mtp_token_manifest = resolve_path(args.mtp_token_manifest, base_dir=project_root)
    output_path = resolve_path(args.output, base_dir=project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)

    alignment_samples = _load_alignment_samples(
        merged_manifest,
        future_window=int(args.future_window),
        max_samples=args.max_samples,
    )
    token_samples = _load_mtp_token_samples(mtp_token_manifest)
    train_positions, val_positions = _split_positions(len(alignment_samples), args.val_fraction)
    train = _samples_to_dataset(
        alignment_samples,
        token_samples,
        train_positions,
        num_experts=int(args.num_experts),
        max_tokens=args.max_tokens,
        alignment_offsets=alignment_offsets,
        device=device,
    )
    val = _samples_to_dataset(
        alignment_samples,
        token_samples,
        val_positions,
        num_experts=int(args.num_experts),
        max_tokens=args.max_tokens,
        alignment_offsets=alignment_offsets,
        device=device,
    )
    if train is None:
        msg = "Training split is empty."
        raise RuntimeError(msg)
    eval_data = val if val is not None else train

    frequency_scores = train_frequency_scores(train.target_mass)
    transition = train_transition_matrix(train.current_feature, train.target_mass)
    source_token_table = build_token_frequency_table(
        train.source_token_ids,
        train.target_mass,
        fallback=frequency_scores,
    )
    target_token_table = build_token_frequency_table(
        train.target_token_ids,
        train.target_mass,
        fallback=frequency_scores,
    )

    frequency_eval = frequency_scores.expand_as(eval_data.target_mass).to(device)
    transition_eval = apply_transition_matrix(eval_data.current_feature, transition).to(device)
    source_token_eval = apply_token_frequency_table(
        source_token_table,
        eval_data.source_token_ids,
        device=device,
    )
    true_target_token_eval = apply_token_frequency_table(
        target_token_table,
        eval_data.target_token_ids,
        device=device,
    )
    mtp_token_eval = _apply_mtp_token_frequency_table(
        target_token_table,
        eval_data.mtp_topm_ids,
        eval_data.mtp_topm_probs,
        device=device,
    )

    logits_by_name: dict[str, torch.Tensor] = {
        "train_frequency": frequency_eval,
        "source_token_frequency": source_token_eval,
        "true_target_token_frequency_oracle": true_target_token_eval,
        "mtp_predicted_token_frequency": mtp_token_eval,
        "transition": transition_eval,
    }
    for alpha in fusion_alphas:
        name = f"transition_plus_mtp_token_alpha_{alpha:g}"
        logits_by_name[name] = _safe_log(transition_eval) + alpha * _safe_log(mtp_token_eval)
        if args.fusion_beta:
            logits_by_name[name] = logits_by_name[name] + args.fusion_beta * _safe_log(
                frequency_eval
            )
        union_name = f"transition_union_mtp_token_alpha_{alpha:g}"
        logits_by_name[union_name] = _candidate_union_logits(
            transition_eval,
            mtp_token_eval,
            frequency_eval,
            alpha=alpha,
            beta=float(args.fusion_beta),
            transition_topk=int(args.union_transition_topk),
            mtp_topk=int(args.union_mtp_topk),
        )

    methods = {
        name: _metrics_for_logits(
            logits,
            eval_data.labels,
            eval_data.target_mass,
            recall_ms=recall_ms,
        )
        for name, logits in logits_by_name.items()
    }
    relative_to_transition = {}
    transition_metrics = methods["transition"]
    for name, values in methods.items():
        if name == "transition":
            continue
        relative_to_transition[name] = {
            m: {
                "delta_mass_coverage": values[m]["mass_coverage"]
                - transition_metrics[m]["mass_coverage"],
                "delta_top1_hit_rate": values[m]["top1_hit_rate"]
                - transition_metrics[m]["top1_hit_rate"],
                "delta_weighted_top1_miss": values[m]["weighted_top1_miss"]
                - transition_metrics[m]["weighted_top1_miss"],
            }
            for m in transition_metrics
        }

    candidate_diagnostics = {}
    for name, logits in logits_by_name.items():
        if name == "transition":
            continue
        candidate_diagnostics[name] = {
            str(m): _introduced_mass(
                logits,
                transition_eval,
                eval_data.target_mass,
                m=m,
            )
            for m in recall_ms
        }

    report = {
        "ok": True,
        "merged_manifest": str(merged_manifest),
        "mtp_token_manifest": str(mtp_token_manifest),
        "train_sample_positions": train_positions,
        "val_sample_positions": val_positions,
        "eval_split": "val" if val is not None else "train",
        "num_train_token_examples": int(train.labels.shape[0]),
        "num_eval_token_examples": int(eval_data.labels.shape[0]),
        "recall_at_ms": recall_ms,
        "mtp_token_alignment": _alignment_metrics(
            eval_data,
            alignment_offsets=alignment_offsets,
        ),
        "methods": methods,
        "relative_to_transition": relative_to_transition,
        "candidate_diagnostics_vs_transition": candidate_diagnostics,
        "candidate_pool_diagnostics": _candidate_pool_diagnostics(
            transition_eval,
            mtp_token_eval,
            eval_data.target_mass,
            transition_topk=int(args.candidate_pool_transition_topk),
            mtp_topks=candidate_pool_mtp_topks,
        ),
        "transition_tail_budget_diagnostics": _transition_tail_budget_diagnostics(
            transition_eval,
            eval_data.target_mass,
            transition_topks=transition_tail_baseline_topks,
            base_topk=int(args.candidate_pool_transition_topk),
        ),
        "dynamic_extra_budget_diagnostics": _dynamic_extra_budget_diagnostics(
            transition_eval,
            mtp_token_eval,
            eval_data.target_mass,
            transition_topk=int(args.candidate_pool_transition_topk),
            mtp_topk=int(args.dynamic_extra_mtp_topk),
            max_extras=dynamic_max_extras,
        ),
        "per_layer_dynamic_extra_budget_diagnostics": (
            _per_layer_dynamic_extra_budget_diagnostics(
                transition_eval,
                mtp_token_eval,
                eval_data.target_mass,
                transition_topk=int(args.candidate_pool_transition_topk),
                mtp_topk=int(args.dynamic_extra_mtp_topk),
                max_extras=dynamic_max_extras,
            )
        ),
        "fixed_budget_replacement_diagnostics": _fixed_budget_replacement_diagnostics(
            transition_eval,
            mtp_token_eval,
            eval_data.target_mass,
            total_budget=int(args.fixed_budget_total),
            mtp_topk=int(args.fixed_budget_mtp_topk),
            replacements=fixed_budget_replacements,
        ),
        "layer_aware_same_budget_diagnostics": _layer_aware_same_budget_diagnostics(
            transition_eval,
            mtp_token_eval,
            eval_data.target_mass,
            base_topk=int(args.candidate_pool_transition_topk),
            early_transition_topk=int(args.layer_aware_transition_tail_topk),
            mtp_topk=int(args.layer_aware_mtp_topk),
            max_extra=int(args.layer_aware_max_extra),
            early_layer_cutoffs=layer_aware_cutoffs,
        ),
        "notes": {
            "future_window": int(args.future_window),
            "mtp_probs": "top-M truncated probabilities normalized within recorded candidates",
            "candidate_policy": (
                "transition remains protected; MTP-token prior is evaluated as optional "
                "novel-expert expansion, not replacement."
            ),
            "mtp_sidecar_model": str(args.mtp_sidecar_model),
            "router_trace_model": str(args.router_trace_model),
            "cross_quantization_caveat": (
                "MTP sidecar features and router labels may come from different int4 "
                "quantization variants; same-checkpoint validation is still required "
                "before paper/runtime claims."
            ),
        },
    }
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
