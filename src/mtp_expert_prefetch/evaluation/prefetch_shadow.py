from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from mtp_expert_prefetch.admission import (
    add_metadata_budget_decisions,
    add_premap_budget_decisions,
    build_mtp_extra_utility_scores as _runtime_build_mtp_extra_utility_scores,
    novel_mtp_extra_mask as _runtime_novel_mtp_extra_mask,
    novel_mtp_extra_rank_mask as _runtime_novel_mtp_extra_rank_mask,
    score_threshold_mtp_extra_decision_masks as _runtime_score_threshold_mtp_extra_decision_masks,
    score_threshold_mtp_extra_mask as _runtime_score_threshold_mtp_extra_mask,
    select_topk_mask,
    tail_swap_mtp_extra_mask as _runtime_tail_swap_mtp_extra_mask,
)
from mtp_expert_prefetch.tracing import load_trace_payload
from mtp_expert_prefetch.training import (
    TokenFrequencyTable,
    apply_transition_matrix,
    build_mtp_router_alignment,
    build_token_frequency_table,
    router_topk_to_dense_feature,
    target_expert_ids_to_dense_weights,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.training.alignment_merge import (
    manifest_record_path,
    read_trace_manifest,
)


@dataclass(frozen=True)
class PrefetchShadowDataset:
    target_mass: torch.Tensor
    current_feature: torch.Tensor
    target_token_ids: torch.Tensor
    mtp_topm_ids: torch.Tensor
    mtp_topm_probs: torch.Tensor
    sample_indices: list[int]
    token_sample_indices: torch.Tensor


@dataclass(frozen=True)
class PrefetchShadowReport:
    merged_manifest: str
    mtp_token_manifest: str
    train_sample_positions: list[int]
    val_sample_positions: list[int]
    eval_split: str
    num_train_token_examples: int
    num_eval_token_examples: int
    transition_topk: int
    mtp_topk: int
    max_extras: list[int]
    policies: dict[str, dict[str, float]]
    capacity_guarded_policies: dict[str, dict[str, float]]
    priority_admission_policies: dict[str, dict[str, float]]
    action_shadow_policies: dict[str, dict[str, Any]]
    priority_tiers: dict[str, dict[str, float]]
    policy_working_sets: dict[str, dict[str, float]]
    per_layer: dict[str, dict[str, Any]]
    recommendation: dict[str, Any]
    notes: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "merged_manifest": self.merged_manifest,
            "mtp_token_manifest": self.mtp_token_manifest,
            "train_sample_positions": self.train_sample_positions,
            "val_sample_positions": self.val_sample_positions,
            "eval_split": self.eval_split,
            "num_train_token_examples": self.num_train_token_examples,
            "num_eval_token_examples": self.num_eval_token_examples,
            "transition_topk": self.transition_topk,
            "mtp_topk": self.mtp_topk,
            "max_extras": self.max_extras,
            "policies": self.policies,
            "capacity_guarded_policies": self.capacity_guarded_policies,
            "priority_admission_policies": self.priority_admission_policies,
            "action_shadow_policies": self.action_shadow_policies,
            "priority_tiers": self.priority_tiers,
            "policy_working_sets": self.policy_working_sets,
            "per_layer": self.per_layer,
            "recommendation": self.recommendation,
            "notes": self.notes,
        }


def simulate_prefetch_shadow(
    merged_manifest: str | Path,
    mtp_token_manifest: str | Path,
    *,
    future_window: int = 1,
    num_experts: int = 256,
    val_fraction: float = 0.25,
    max_samples: int | None = None,
    max_tokens: int | None = None,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    max_extras: list[int] | None = None,
    default_max_extra: int = 4,
    high_budget_max_extra: int = 8,
    cache_capacities: list[int] | None = None,
    action_keep_fraction: float = 0.5,
    metadata_score_ratio: float = 0.95,
    metadata_max_extra: int = 1,
    premap_max_extra: int = 1,
) -> PrefetchShadowReport:
    if future_window != 1:
        msg = "Prefetch shadow simulation currently expects future_window=1."
        raise ValueError(msg)
    max_extras = sorted({int(item) for item in (max_extras or [1, 2, 4, 8])})
    if not max_extras:
        msg = "At least one max_extra value is required."
        raise ValueError(msg)

    merged_manifest = Path(merged_manifest).expanduser().resolve()
    mtp_token_manifest = Path(mtp_token_manifest).expanduser().resolve()
    alignment_samples = _load_alignment_samples(
        merged_manifest,
        future_window=future_window,
        max_samples=max_samples,
    )
    mtp_token_samples = _load_mtp_token_samples(mtp_token_manifest)
    train_positions, val_positions = _split_positions(len(alignment_samples), val_fraction)
    train = _samples_to_dataset(
        alignment_samples,
        mtp_token_samples,
        train_positions,
        num_experts=num_experts,
        max_tokens=max_tokens,
    )
    val = _samples_to_dataset(
        alignment_samples,
        mtp_token_samples,
        val_positions,
        num_experts=num_experts,
        max_tokens=max_tokens,
    )
    eval_data = val if val is not None else train

    transition = train_transition_matrix(train.current_feature, train.target_mass)
    train_transition_scores = apply_transition_matrix(train.current_feature, transition)
    transition_scores = apply_transition_matrix(eval_data.current_feature, transition)
    frequency_scores = train_frequency_scores(train.target_mass)
    target_token_table = build_token_frequency_table(
        train.target_token_ids,
        train.target_mass,
        fallback=frequency_scores,
    )
    mtp_scores = _apply_mtp_token_frequency_table(
        target_token_table,
        eval_data.mtp_topm_ids,
        eval_data.mtp_topm_probs,
    )
    train_mtp_scores = _apply_mtp_token_frequency_table(
        target_token_table,
        train.mtp_topm_ids,
        train.mtp_topm_probs,
    )

    base_mask = topk_mask(transition_scores, k=transition_topk)
    policy_masks = {
        f"transition_top{transition_topk}": base_mask,
    }
    for max_extra in max_extras:
        extra_mask = novel_mtp_extra_mask(
            base_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
        )
        policy_masks[
            f"transition_top{transition_topk}_plus_mtp_top{mtp_topk}_max_extra{max_extra}"
        ] = base_mask | extra_mask

    base_metrics = mask_metrics(base_mask, eval_data.target_mass)
    action_shadow_policies = _action_shadow_policy_metrics(
        train_transition_scores,
        train_mtp_scores,
        train.target_mass,
        transition_scores,
        mtp_scores,
        eval_data.target_mass,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        full_fetch_max_extra=default_max_extra,
        action_keep_fraction=float(action_keep_fraction),
        metadata_score_ratio=float(metadata_score_ratio),
        metadata_max_extra=int(metadata_max_extra),
        premap_max_extra=int(premap_max_extra),
    )
    policies = {}
    for name, mask in policy_masks.items():
        metrics = mask_metrics(mask, eval_data.target_mass, base_mask=base_mask)
        metrics["delta_pool_mass_coverage"] = (
            metrics["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
        )
        metrics["delta_weighted_top1_miss"] = (
            metrics["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
        )
        policies[name] = metrics

    capacity_guarded_policies = {}
    guarded_masks = {}
    capacities = sorted({int(item) for item in cache_capacities or [] if int(item) >= 0})
    for cap in capacities:
        for guarded_extra in sorted({default_max_extra, high_budget_max_extra}):
            guarded_name = (
                f"capacity{cap}_guard_transition_top{transition_topk}_plus_"
                f"mtp_top{mtp_topk}_max_extra{guarded_extra}"
            )
            candidate_name = (
                f"transition_top{transition_topk}_plus_mtp_top{mtp_topk}_max_extra"
                f"{guarded_extra}"
            )
            candidate_mask = policy_masks.get(candidate_name)
            if candidate_mask is None:
                continue
            guarded_mask = capacity_guarded_mask(
                base_mask,
                candidate_mask,
                eval_data.token_sample_indices,
                capacity=cap,
            )
            guarded_masks[guarded_name] = guarded_mask
            metrics = mask_metrics(guarded_mask, eval_data.target_mass, base_mask=base_mask)
            metrics["delta_pool_mass_coverage"] = (
                metrics["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
            )
            metrics["delta_weighted_top1_miss"] = (
                metrics["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
            )
            metrics["enabled_sample_layer_fraction"] = enabled_sample_layer_fraction(
                candidate_mask,
                eval_data.token_sample_indices,
                capacity=cap,
            )
            capacity_guarded_policies[guarded_name] = metrics

    highest_extra = max(max_extras)
    priority_admission_policies = {}
    admission_masks = {}
    for cap in capacities:
        for admission_extra in sorted({default_max_extra, high_budget_max_extra}):
            admission_name = (
                f"priority_admit_capacity{cap}_transition_top{transition_topk}_plus_"
                f"mtp_top{mtp_topk}_max_extra{admission_extra}"
            )
            admission_mask = priority_admission_mask(
                transition_scores,
                mtp_scores,
                eval_data.token_sample_indices,
                transition_topk=transition_topk,
                mtp_topk=mtp_topk,
                max_extra=admission_extra,
                capacity=cap,
            )
            admission_masks[admission_name] = admission_mask
            metrics = mask_metrics(admission_mask, eval_data.target_mass, base_mask=base_mask)
            metrics["delta_pool_mass_coverage"] = (
                metrics["pool_mass_coverage"] - base_metrics["pool_mass_coverage"]
            )
            metrics["delta_weighted_top1_miss"] = (
                metrics["weighted_top1_miss"] - base_metrics["weighted_top1_miss"]
            )
            priority_admission_policies[admission_name] = metrics

    priority_tiers = priority_tier_metrics(
        transition_scores,
        mtp_scores,
        eval_data.target_mass,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=highest_extra,
    )
    policy_working_sets = {
        name: policy_working_set_summary(
            mask,
            eval_data.token_sample_indices,
            capacities=cache_capacities,
        )
        for name, mask in {**policy_masks, **guarded_masks, **admission_masks}.items()
    }
    per_layer = per_layer_policy_metrics(policy_masks, eval_data.target_mass, base_mask=base_mask)

    return PrefetchShadowReport(
        merged_manifest=str(merged_manifest),
        mtp_token_manifest=str(mtp_token_manifest),
        train_sample_positions=train_positions,
        val_sample_positions=val_positions,
        eval_split="val" if val is not None else "train",
        num_train_token_examples=int(train.target_mass.shape[0]),
        num_eval_token_examples=int(eval_data.target_mass.shape[0]),
        transition_topk=int(transition_topk),
        mtp_topk=int(mtp_topk),
        max_extras=max_extras,
        policies=policies,
        capacity_guarded_policies=capacity_guarded_policies,
        priority_admission_policies=priority_admission_policies,
        action_shadow_policies=action_shadow_policies,
        priority_tiers=priority_tiers,
        policy_working_sets=policy_working_sets,
        per_layer=per_layer,
        recommendation={
            "protected_base": f"transition_top{transition_topk}",
            "default_policy": (
                f"transition_top{transition_topk}_plus_mtp_top{mtp_topk}_max_extra"
                f"{default_max_extra}"
            ),
            "high_budget_policy": (
                f"transition_top{transition_topk}_plus_mtp_top{mtp_topk}_max_extra"
                f"{high_budget_max_extra}"
            ),
            "runtime_rule": (
                "Never evict protected transition candidates for MTP extras unless "
                "a fixed-budget replacement policy is explicitly selected."
            ),
            "action_policy": (
                "transition_topK + utility-gated full_fetch up to default_max_extra "
                "+ raw-score metadata max1 + tiny premap budget; only full_fetch "
                "contributes to ready-before-demand."
            ),
        },
        notes={
            "policy_mode": "offline shadow mode; no real expert transfer is performed",
            "candidate_policy": (
                "transition_topK is protected; MTP-token prior only appends novel experts."
            ),
            "shared_expert_policy": (
                "shared experts are not included in routed-expert prediction budgets"
            ),
        },
    )


def write_prefetch_shadow_report(report: PrefetchShadowReport, output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def _action_shadow_policy_metrics(
    train_transition_scores: torch.Tensor,
    train_mtp_scores: torch.Tensor,
    train_target_mass: torch.Tensor,
    eval_transition_scores: torch.Tensor,
    eval_mtp_scores: torch.Tensor,
    eval_target_mass: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    full_fetch_max_extra: int,
    action_keep_fraction: float,
    metadata_score_ratio: float,
    metadata_max_extra: int,
    premap_max_extra: int,
    expert_bytes: int = 1_650_000,
    metadata_bytes: int = 65_536,
    premap_bytes: int = 4_096,
) -> dict[str, dict[str, Any]]:
    train_base = topk_mask(train_transition_scores, k=transition_topk)
    eval_base = topk_mask(eval_transition_scores, k=transition_topk)
    layer_factors = _calibrated_layer_factors(
        train_base,
        train_mtp_scores,
        train_target_mass,
        mtp_topk=mtp_topk,
        max_extra=full_fetch_max_extra,
    )
    train_utility = build_mtp_extra_utility_scores(
        train_base,
        train_mtp_scores,
        mtp_topk=mtp_topk,
        rank_alpha=1.0,
        layer_factors=layer_factors,
    )
    eval_utility = build_mtp_extra_utility_scores(
        eval_base,
        eval_mtp_scores,
        mtp_topk=mtp_topk,
        rank_alpha=1.0,
        layer_factors=layer_factors,
    )
    full_threshold = _threshold_from_keep_fraction(
        train_base,
        train_mtp_scores,
        train_utility,
        mtp_topk=mtp_topk,
        max_extra=full_fetch_max_extra,
        keep_fraction=action_keep_fraction,
    )
    raw_threshold = _threshold_from_keep_fraction(
        train_base,
        train_mtp_scores,
        train_mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=full_fetch_max_extra,
        keep_fraction=action_keep_fraction,
    )
    full_decisions = score_threshold_mtp_extra_decision_masks(
        eval_base,
        eval_utility,
        mtp_topk=mtp_topk,
        max_extra=full_fetch_max_extra,
        score_threshold=full_threshold,
    )
    decisions = add_metadata_budget_decisions(
        eval_base,
        full_decisions=full_decisions,
        metadata_scores=eval_mtp_scores,
        mtp_topk=mtp_topk,
        metadata_max_extra=metadata_max_extra,
        metadata_score_threshold=raw_threshold * float(metadata_score_ratio),
    )
    if int(premap_max_extra) > 0:
        decisions = add_premap_budget_decisions(
            eval_base,
            decisions=decisions,
            premap_scores=eval_mtp_scores,
            mtp_topk=mtp_topk,
            premap_max_extra=premap_max_extra,
        )
    return {
        "utility_keep50_action_policy": {
            "full_fetch_max_extra": float(full_fetch_max_extra),
            "metadata_max_extra": float(metadata_max_extra),
            "premap_max_extra": float(premap_max_extra),
            "action_keep_fraction": float(action_keep_fraction),
            "full_fetch_threshold": float(full_threshold),
            "metadata_score_ratio": float(metadata_score_ratio),
            "metadata_score_threshold": float(raw_threshold * float(metadata_score_ratio)),
            "actions": _action_shadow_counter_metrics(
                decisions,
                eval_target_mass,
                expert_bytes=expert_bytes,
                metadata_bytes=metadata_bytes,
                premap_bytes=premap_bytes,
            ),
        }
    }


def _threshold_from_keep_fraction(
    base: torch.Tensor,
    mtp_scores: torch.Tensor,
    score_tensor: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
    keep_fraction: float,
) -> float:
    candidate = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    valid = candidate & torch.isfinite(score_tensor.float())
    scores = score_tensor.float()[valid]
    if scores.numel() == 0:
        return float("inf")
    keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
    if keep_fraction <= 0.0:
        return float("inf")
    if keep_fraction >= 1.0:
        return float(scores.min().item())
    return float(torch.quantile(scores, 1.0 - keep_fraction).item())


def _calibrated_layer_factors(
    base: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
) -> torch.Tensor:
    extra = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    count_by_layer = extra.float().sum(dim=(0, 1, 3)).clamp_min(1.0)
    gain_by_layer = (extra.float() * target_mass).sum(dim=(0, 1, 3)) / count_by_layer
    positive = gain_by_layer[gain_by_layer.gt(0.0)]
    if positive.numel() == 0:
        return torch.ones_like(gain_by_layer)
    return (gain_by_layer / positive.mean().clamp_min(1e-12)).clamp(0.5, 1.5)


def _action_shadow_counter_metrics(
    decisions: Any,
    target_mass: torch.Tensor,
    *,
    expert_bytes: int,
    metadata_bytes: int,
    premap_bytes: int,
) -> dict[str, Any]:
    demand = target_mass.float().gt(0.0)
    action_bytes = {
        "full_fetch": int(expert_bytes),
        "metadata": int(metadata_bytes),
        "premap": int(premap_bytes),
        "skip": 0,
    }
    payload_bytes = int(expert_bytes)
    counters: dict[str, Any] = {}
    for action, mask in decisions.action_masks().items():
        selected = mask.bool()
        later_used = selected & demand
        count = float(selected.float().sum().item())
        later_used_count = float(later_used.float().sum().item())
        counters[str(action)] = {
            "count": count,
            "payload_equivalent_bytes": float(count * payload_bytes),
            "actual_bytes": float(count * action_bytes[str(action)]),
            "later_used_count": later_used_count,
            "later_used_rate": later_used_count / max(1.0, count),
            "unused_count": float((selected & ~demand).float().sum().item()),
            "unused_rate": float((selected & ~demand).float().sum().item())
            / max(1.0, count),
        }
    counters["summary"] = {
        "full_fetch_count": counters["full_fetch"]["count"],
        "metadata_count": counters["metadata"]["count"],
        "premap_count": counters["premap"]["count"],
        "skip_count": counters["skip"]["count"],
    }
    counters["reasons"] = _shadow_reason_counter_metrics(decisions)
    counters["action_reason_matrix"] = _shadow_action_reason_matrix_metrics(decisions)
    return counters


def _shadow_reason_counter_metrics(decisions: Any) -> dict[str, dict[str, float]]:
    counters = {}
    for reason, mask in decisions.reason_masks().items():
        counters[str(reason)] = {"count": float(mask.float().sum().item())}
    return counters


def _shadow_action_reason_matrix_metrics(
    decisions: Any,
) -> dict[str, dict[str, dict[str, float]]]:
    matrix = {}
    action_masks = decisions.action_masks()
    for reason, reason_mask in decisions.reason_masks().items():
        row = {}
        for action, action_mask in action_masks.items():
            row[str(action)] = {
                "count": float((reason_mask & action_mask).float().sum().item())
            }
        matrix[str(reason)] = row
    return matrix


def topk_mask(scores: torch.Tensor, *, k: int) -> torch.Tensor:
    return select_topk_mask(scores, k=k)


def novel_mtp_extra_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
) -> torch.Tensor:
    return _runtime_novel_mtp_extra_mask(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )


def novel_mtp_extra_rank_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    rank: int,
) -> torch.Tensor:
    return _runtime_novel_mtp_extra_rank_mask(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        rank=rank,
    )


def score_threshold_mtp_extra_mask(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
    score_threshold: float,
) -> torch.Tensor:
    return _runtime_score_threshold_mtp_extra_mask(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
        score_threshold=score_threshold,
    )


def score_threshold_mtp_extra_decision_masks(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    max_extra: int,
    score_threshold: float,
    policy_allowed_mask: torch.Tensor | None = None,
    metadata_allowed_mask: torch.Tensor | None = None,
    premap_allowed_mask: torch.Tensor | None = None,
):
    return _runtime_score_threshold_mtp_extra_decision_masks(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
        score_threshold=score_threshold,
        policy_allowed_mask=policy_allowed_mask,
        metadata_allowed_mask=metadata_allowed_mask,
        premap_allowed_mask=premap_allowed_mask,
    )


def tail_swap_mtp_extra_mask(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    swap_count: int,
) -> torch.Tensor:
    return _runtime_tail_swap_mtp_extra_mask(
        transition_scores,
        mtp_scores,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        swap_count=swap_count,
    )


def build_mtp_extra_utility_scores(
    base_mask: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    mtp_topk: int,
    rank_alpha: float = 1.0,
    layer_factors: torch.Tensor | None = None,
    ready_factors: torch.Tensor | None = None,
) -> torch.Tensor:
    return _runtime_build_mtp_extra_utility_scores(
        base_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        rank_alpha=rank_alpha,
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )


def lead_time_ready_mask(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    max_extra: int = 4,
    num_layers: int = 40,
    layer_ms: float = 1.0,
    sampling_ms: float = 0.0,
    mtp_delay_ms: float = 0.0,
    bandwidth_gbps: float = 16.0,
    expert_bytes: int = 1_650_000,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Build a token-level pool after applying lead-time transfer limits.

    Transition candidates are assumed to be emitted one token early at the same
    layer, so their deadline window is roughly one full forward pass. MTP-token
    extras are assumed to be emitted after token-level MTP prediction, so their
    window for layer `l` is roughly `l * layer_ms - mtp_delay_ms`.
    """
    if transition_scores.shape != mtp_scores.shape:
        msg = "transition_scores and mtp_scores must have the same shape."
        raise ValueError(msg)
    if transition_scores.ndim != 4:
        msg = f"Expected [tokens, future, layers, experts], got {transition_scores.shape}."
        raise ValueError(msg)
    layer_count = int(transition_scores.shape[2])
    if int(num_layers) != layer_count:
        num_layers = layer_count
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0

    protected_base = topk_mask(transition_scores, k=transition_topk)
    ready = torch.zeros_like(protected_base)
    raw_extra_count = 0.0
    ready_extra_count = 0.0
    transition_cap_values = []
    mtp_cap_values = []
    for layer_idx in range(layer_count):
        transition_lead = float(num_layers) * float(layer_ms) + float(sampling_ms)
        transition_cap = int(max(0, transition_lead * bytes_per_ms // int(expert_bytes)))
        transition_k = min(int(transition_topk), transition_cap)
        transition_cap_values.append(float(transition_cap))
        if transition_k > 0:
            ready[:, :, layer_idx : layer_idx + 1, :] |= topk_mask(
                transition_scores[:, :, layer_idx : layer_idx + 1, :],
                k=transition_k,
            )

        raw_extra = novel_mtp_extra_mask(
            protected_base[:, :, layer_idx : layer_idx + 1, :],
            mtp_scores[:, :, layer_idx : layer_idx + 1, :],
            mtp_topk=mtp_topk,
            max_extra=max_extra,
        )
        raw_extra_count += float(raw_extra.float().sum().item())
        mtp_lead = max(
            0.0,
            float(layer_idx) * float(layer_ms)
            + float(sampling_ms)
            - float(mtp_delay_ms),
        )
        mtp_cap = int(max(0, mtp_lead * bytes_per_ms // int(expert_bytes)))
        mtp_cap_values.append(float(mtp_cap))
        effective_extra = min(int(max_extra), mtp_cap)
        if effective_extra <= 0:
            continue
        ready_extra = novel_mtp_extra_mask(
            protected_base[:, :, layer_idx : layer_idx + 1, :],
            mtp_scores[:, :, layer_idx : layer_idx + 1, :],
            mtp_topk=mtp_topk,
            max_extra=effective_extra,
        )
        ready_extra_count += float(ready_extra.float().sum().item())
        ready[:, :, layer_idx : layer_idx + 1, :] |= ready_extra

    transition_cap_tensor = torch.tensor(transition_cap_values, dtype=torch.float32)
    mtp_cap_tensor = torch.tensor(mtp_cap_values, dtype=torch.float32)
    return ready, {
        "raw_extra_count": raw_extra_count,
        "ready_extra_count": ready_extra_count,
        "ready_extra_fraction": ready_extra_count / max(1.0, raw_extra_count),
        "transition_cap_min": float(transition_cap_tensor.min().item()),
        "transition_cap_mean": float(transition_cap_tensor.mean().item()),
        "mtp_cap_min": float(mtp_cap_tensor.min().item()),
        "mtp_cap_mean": float(mtp_cap_tensor.mean().item()),
        "mtp_cap_p50": float(torch.quantile(mtp_cap_tensor, 0.50).item()),
    }


def queue_aware_ready_mask(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    max_extra: int = 4,
    num_layers: int = 40,
    layer_ms: float = 1.0,
    sampling_ms: float = 0.0,
    mtp_delay_ms: float = 0.0,
    bandwidth_gbps: float = 16.0,
    expert_bytes: int = 1_650_000,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Build a ready mask with a simple priority queue approximation.

    Compared with `lead_time_ready_mask`, this function models contention between
    transition candidates and MTP extras. Experts that can be fetched before MTP
    is available are selected from transition P2/P3 only. The later MTP window is
    then shared by remaining transition candidates and MTP extras, ordered by
    priority: P2, P3, P4, P5.
    """
    if transition_scores.shape != mtp_scores.shape:
        msg = "transition_scores and mtp_scores must have the same shape."
        raise ValueError(msg)
    if transition_scores.ndim != 4:
        msg = f"Expected [tokens, future, layers, experts], got {transition_scores.shape}."
        raise ValueError(msg)
    layer_count = int(transition_scores.shape[2])
    if int(num_layers) != layer_count:
        num_layers = layer_count
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0

    p2 = topk_mask(transition_scores, k=min(16, int(transition_topk)))
    p32 = topk_mask(transition_scores, k=transition_topk)
    p3 = p32 & ~p2
    p4 = novel_mtp_extra_mask(
        p32,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=min(4, int(max_extra)),
    )
    pall = novel_mtp_extra_mask(
        p32,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    p5 = pall & ~p4

    ready = torch.zeros_like(p32)
    raw_extra_count = float((p4 | p5).float().sum().item())
    raw_base_count = float(p32.float().sum().item())
    transition_cap_values = []
    mtp_cap_values = []
    prefix_cap_values = []
    for layer_idx in range(layer_count):
        transition_lead = float(num_layers) * float(layer_ms) + float(sampling_ms)
        mtp_lead = max(
            0.0,
            float(layer_idx) * float(layer_ms)
            + float(sampling_ms)
            - float(mtp_delay_ms),
        )
        transition_cap = int(max(0, transition_lead * bytes_per_ms // int(expert_bytes)))
        mtp_cap = int(max(0, mtp_lead * bytes_per_ms // int(expert_bytes)))
        prefix_cap = max(0, transition_cap - mtp_cap)
        transition_cap_values.append(float(transition_cap))
        mtp_cap_values.append(float(mtp_cap))
        prefix_cap_values.append(float(prefix_cap))

        layer_scores = transition_scores[:, :, layer_idx : layer_idx + 1, :]
        layer_mtp_scores = mtp_scores[:, :, layer_idx : layer_idx + 1, :]
        layer_p2 = p2[:, :, layer_idx : layer_idx + 1, :]
        layer_p3 = p3[:, :, layer_idx : layer_idx + 1, :]
        layer_p4 = p4[:, :, layer_idx : layer_idx + 1, :]
        layer_p5 = p5[:, :, layer_idx : layer_idx + 1, :]

        prefix_ready = _priority_topk_mask(
            [
                (layer_p2, layer_scores, 2),
                (layer_p3, layer_scores, 3),
            ],
            k=prefix_cap,
        )
        tail_ready = _priority_topk_mask(
            [
                (layer_p2 & ~prefix_ready, layer_scores, 2),
                (layer_p3 & ~prefix_ready, layer_scores, 3),
                (layer_p4, layer_mtp_scores, 4),
                (layer_p5, layer_mtp_scores, 5),
            ],
            k=mtp_cap,
        )
        ready[:, :, layer_idx : layer_idx + 1, :] = prefix_ready | tail_ready

    transition_cap_tensor = torch.tensor(transition_cap_values, dtype=torch.float32)
    mtp_cap_tensor = torch.tensor(mtp_cap_values, dtype=torch.float32)
    prefix_cap_tensor = torch.tensor(prefix_cap_values, dtype=torch.float32)
    ready_extra_count = float((ready & (p4 | p5)).float().sum().item())
    ready_base_count = float((ready & p32).float().sum().item())
    return ready, {
        "raw_base_count": raw_base_count,
        "ready_base_count": ready_base_count,
        "ready_base_fraction": ready_base_count / max(1.0, raw_base_count),
        "raw_extra_count": raw_extra_count,
        "ready_extra_count": ready_extra_count,
        "ready_extra_fraction": ready_extra_count / max(1.0, raw_extra_count),
        "transition_cap_min": float(transition_cap_tensor.min().item()),
        "transition_cap_mean": float(transition_cap_tensor.mean().item()),
        "mtp_cap_min": float(mtp_cap_tensor.min().item()),
        "mtp_cap_mean": float(mtp_cap_tensor.mean().item()),
        "mtp_cap_p50": float(torch.quantile(mtp_cap_tensor, 0.50).item()),
        "prefix_cap_mean": float(prefix_cap_tensor.mean().item()),
    }


def mask_metrics(
    mask: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    base_mask: torch.Tensor | None = None,
) -> dict[str, float]:
    mass = target_mass.float().clamp_min(0.0)
    total_mass = mass.sum().clamp_min(1e-12)
    true_top1 = mass.argmax(dim=-1, keepdim=True)
    true_top1_weight = mass.gather(-1, true_top1).squeeze(-1)
    top1_hit = mask.gather(-1, true_top1).squeeze(-1).float()
    weighted_top1_miss = (true_top1_weight * (1.0 - top1_hit)).mean()
    metrics = {
        "pool_mass_coverage": float((mass[mask].sum() / total_mass).item()),
        "avg_pool_size": float(mask.float().sum(dim=-1).mean().item()),
        "top1_hit_rate": float(top1_hit.mean().item()),
        "weighted_top1_miss": float(weighted_top1_miss.item()),
    }
    if base_mask is not None:
        introduced = mask & ~base_mask
        introduced_count = introduced.float().sum().clamp_min(1.0)
        introduced_mass = mass[introduced].sum()
        metrics.update(
            {
                "avg_extra_count": float(introduced.float().sum(dim=-1).mean().item()),
                "introduced_mass_fraction": float((introduced_mass / total_mass).item()),
                "introduced_mass_per_added_expert": float(
                    (introduced_mass / introduced_count).item()
                ),
            }
        )
    return metrics


def _priority_topk_mask(
    tiers: list[tuple[torch.Tensor, torch.Tensor, int]],
    *,
    k: int,
) -> torch.Tensor:
    reference = tiers[0][0]
    output = torch.zeros_like(reference, dtype=torch.bool)
    k = max(0, int(k))
    if k == 0:
        return output
    composite = torch.full(reference.shape, -float("inf"), dtype=torch.float32, device=reference.device)
    for mask, scores, priority in tiers:
        priority_score = -float(priority) * 1_000_000.0 + scores.float()
        composite = torch.maximum(composite, priority_score.masked_fill(~mask, -float("inf")))
    available = torch.isfinite(composite).sum(dim=-1, keepdim=True)
    if int(available.max().item()) == 0:
        return output
    topk = min(k, int(composite.shape[-1]))
    indices = torch.topk(composite, k=topk, dim=-1).indices
    selected_values = composite.gather(-1, indices)
    selected = torch.isfinite(selected_values)
    rank = torch.arange(topk, device=reference.device).view(
        *((1,) * (selected.ndim - 1)),
        topk,
    )
    selected = selected & rank.lt(available.clamp_max(k))
    output.scatter_(-1, indices, selected)
    return output


def priority_tier_metrics(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    max_extra: int,
) -> dict[str, dict[str, float]]:
    transition_top16 = topk_mask(transition_scores, k=min(16, transition_topk))
    transition_topk_mask = topk_mask(transition_scores, k=transition_topk)
    transition_tail = transition_topk_mask & ~transition_top16
    mtp_extra4 = novel_mtp_extra_mask(
        transition_topk_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=min(4, max_extra),
    )
    mtp_extra_all = novel_mtp_extra_mask(
        transition_topk_mask,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    mtp_extra_after4 = mtp_extra_all & ~mtp_extra4
    return {
        "P2_transition_top16": tier_metrics(transition_top16, target_mass),
        f"P3_transition_top17_to_{transition_topk}": tier_metrics(
            transition_tail,
            target_mass,
        ),
        "P4_mtp_extra1_to_4": tier_metrics(mtp_extra4, target_mass),
        f"P5_mtp_extra5_to_{max(max_extra, 4)}": tier_metrics(mtp_extra_after4, target_mass),
    }


def tier_metrics(mask: torch.Tensor, target_mass: torch.Tensor) -> dict[str, float]:
    mass = target_mass.float().clamp_min(0.0)
    total_mass = mass.sum().clamp_min(1e-12)
    true_top1 = mass.argmax(dim=-1, keepdim=True)
    top1_hit = mask.gather(-1, true_top1).squeeze(-1).float()
    return {
        "mass_fraction": float((mass[mask].sum() / total_mass).item()),
        "avg_count": float(mask.float().sum(dim=-1).mean().item()),
        "exclusive_top1_hit_rate": float(top1_hit.mean().item()),
    }


def policy_working_set_summary(
    mask: torch.Tensor,
    token_sample_indices: torch.Tensor,
    *,
    capacities: list[int] | None = None,
) -> dict[str, float]:
    """Summarize unique candidate experts per sample/layer chunk.

    Token-level budgets such as top32/top36 are not the actual prefill pressure:
    a prompt chunk unions candidates across all tokens in the same layer. This
    summary estimates that per-sample/layer pre-map working set.
    """
    if mask.ndim != 4:
        msg = f"Expected mask [tokens, future, layers, experts], got {tuple(mask.shape)}"
        raise ValueError(msg)
    sample_ids = token_sample_indices.to(torch.long).cpu()
    values = []
    for sample_id in torch.unique(sample_ids):
        rows = sample_ids.eq(sample_id)
        if not rows.any():
            continue
        layer_expert_mask = mask[rows].any(dim=(0, 1))
        values.append(layer_expert_mask.float().sum(dim=-1))
    if not values:
        return _summary(torch.empty(0))
    counts = torch.cat(values, dim=0)
    summary = _summary(counts)
    for capacity in sorted({int(item) for item in capacities or [] if int(item) >= 0}):
        summary[f"fit_fraction_at_{capacity}"] = float(
            counts.le(capacity).float().mean().item()
        )
    return summary


def capacity_guarded_mask(
    base_mask: torch.Tensor,
    candidate_mask: torch.Tensor,
    token_sample_indices: torch.Tensor,
    *,
    capacity: int,
) -> torch.Tensor:
    guarded = base_mask.clone()
    sample_ids = token_sample_indices.to(torch.long).cpu()
    layer_count = int(base_mask.shape[2])
    for sample_id in torch.unique(sample_ids):
        rows = sample_ids.eq(sample_id)
        if not rows.any():
            continue
        candidate_layer_counts = candidate_mask[rows].any(dim=(0, 1)).float().sum(dim=-1)
        for layer_idx in range(layer_count):
            if float(candidate_layer_counts[layer_idx].item()) <= float(capacity):
                guarded[rows, :, layer_idx, :] = candidate_mask[rows, :, layer_idx, :]
    return guarded


def priority_admission_mask(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    token_sample_indices: torch.Tensor,
    *,
    transition_topk: int,
    mtp_topk: int,
    max_extra: int,
    capacity: int,
) -> torch.Tensor:
    """Select up to `capacity` experts per sample/layer by priority then score."""
    p2 = topk_mask(transition_scores, k=min(16, int(transition_topk)))
    p32 = topk_mask(transition_scores, k=transition_topk)
    p3 = p32 & ~p2
    p4 = novel_mtp_extra_mask(
        p32,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=min(4, int(max_extra)),
    )
    pall = novel_mtp_extra_mask(
        p32,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    p5 = pall & ~p4
    priorities = [
        (p2, transition_scores, 2),
        (p3, transition_scores, 3),
        (p4, mtp_scores, 4),
        (p5, mtp_scores, 5),
    ]
    admitted = torch.zeros_like(transition_scores, dtype=torch.bool)
    sample_ids = token_sample_indices.to(torch.long).cpu()
    layer_count = int(transition_scores.shape[2])
    capacity = max(0, int(capacity))
    if capacity == 0:
        return admitted
    for sample_id in torch.unique(sample_ids):
        rows = sample_ids.eq(sample_id)
        if not rows.any():
            continue
        for layer_idx in range(layer_count):
            candidates: dict[int, tuple[int, float]] = {}
            for mask, scores, priority in priorities:
                layer_mask = mask[rows, :, layer_idx, :]
                if not layer_mask.any():
                    continue
                reduced_scores = scores[rows, :, layer_idx, :].float().masked_fill(
                    ~layer_mask,
                    -float("inf"),
                ).amax(dim=(0, 1))
                expert_ids = torch.nonzero(torch.isfinite(reduced_scores), as_tuple=False).flatten()
                for expert_id in expert_ids.tolist():
                    score = float(reduced_scores[expert_id].item())
                    previous = candidates.get(int(expert_id))
                    if previous is None or priority < previous[0] or (
                        priority == previous[0] and score > previous[1]
                    ):
                        candidates[int(expert_id)] = (priority, score)
            selected = sorted(
                candidates.items(),
                key=lambda item: (item[1][0], -item[1][1], item[0]),
            )[:capacity]
            if selected:
                expert_ids = torch.tensor(
                    [expert_id for expert_id, _value in selected],
                    dtype=torch.long,
                    device=admitted.device,
                )
                layer_admitted = admitted[rows, :, layer_idx, :].clone()
                layer_admitted[:, :, expert_ids] = True
                admitted[rows, :, layer_idx, :] = layer_admitted
    return admitted


def enabled_sample_layer_fraction(
    candidate_mask: torch.Tensor,
    token_sample_indices: torch.Tensor,
    *,
    capacity: int,
) -> float:
    sample_ids = token_sample_indices.to(torch.long).cpu()
    enabled = []
    for sample_id in torch.unique(sample_ids):
        rows = sample_ids.eq(sample_id)
        if not rows.any():
            continue
        candidate_layer_counts = candidate_mask[rows].any(dim=(0, 1)).float().sum(dim=-1)
        enabled.append(candidate_layer_counts.le(capacity).float())
    if not enabled:
        return 0.0
    return float(torch.cat(enabled, dim=0).mean().item())


def per_layer_policy_metrics(
    policy_masks: dict[str, torch.Tensor],
    target_mass: torch.Tensor,
    *,
    base_mask: torch.Tensor,
) -> dict[str, dict[str, Any]]:
    if target_mass.ndim != 4:
        msg = f"Expected target_mass [tokens, future, layers, experts], got {target_mass.shape}"
        raise ValueError(msg)
    layer_count = int(target_mass.shape[2])
    result: dict[str, dict[str, Any]] = {}
    base_by_layer = [
        mask_metrics(base_mask[:, :, layer_idx : layer_idx + 1, :], target_mass[:, :, layer_idx : layer_idx + 1, :])
        for layer_idx in range(layer_count)
    ]
    for policy_name, mask in policy_masks.items():
        policy_result: dict[str, Any] = {}
        deltas = []
        risk_deltas = []
        for layer_idx in range(layer_count):
            layer_slice = slice(layer_idx, layer_idx + 1)
            metrics = mask_metrics(
                mask[:, :, layer_slice, :],
                target_mass[:, :, layer_slice, :],
                base_mask=base_mask[:, :, layer_slice, :],
            )
            delta = metrics["pool_mass_coverage"] - base_by_layer[layer_idx]["pool_mass_coverage"]
            risk_delta = (
                metrics["weighted_top1_miss"]
                - base_by_layer[layer_idx]["weighted_top1_miss"]
            )
            metrics["delta_pool_mass_coverage"] = delta
            metrics["delta_weighted_top1_miss"] = risk_delta
            policy_result[f"layer_{layer_idx:02d}"] = metrics
            if policy_name != next(iter(policy_masks)):
                deltas.append(delta)
                risk_deltas.append(risk_delta)
        if deltas:
            policy_result["_summary"] = {
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
        result[policy_name] = policy_result
    return result


def _load_alignment_samples(
    manifest_path: Path,
    *,
    future_window: int,
    max_samples: int | None,
) -> list[tuple[int, dict[str, torch.Tensor]]]:
    records = read_trace_manifest(manifest_path)
    if max_samples is not None:
        records = records[: int(max_samples)]
    samples = []
    for record in records:
        payload = load_trace_payload(manifest_record_path(record))
        alignment = build_mtp_router_alignment(payload, future_window=future_window)
        samples.append((int(record.get("sample_idx", len(samples))), alignment.as_dict()))
    if not samples:
        msg = f"No alignment samples loaded from {manifest_path}"
        raise RuntimeError(msg)
    return samples


def _load_mtp_token_samples(manifest_path: Path) -> dict[int, dict[str, torch.Tensor]]:
    records = read_trace_manifest(manifest_path)
    samples: dict[int, dict[str, torch.Tensor]] = {}
    for record in records:
        payload = torch.load(manifest_record_path(record), map_location="cpu", weights_only=False)
        input_ids = torch.as_tensor(payload["input_ids"]).long()
        topm_ids = torch.as_tensor(payload["native_mtp_token_topm_ids"]).long()
        topm_probs = torch.as_tensor(payload["native_mtp_token_topm_probs"]).float()
        if input_ids.ndim == 2:
            input_ids = input_ids[0]
        if topm_ids.ndim == 3:
            topm_ids = topm_ids[0]
            topm_probs = topm_probs[0]
        samples[int(record["sample_idx"])] = {
            "input_ids": input_ids,
            "topm_ids": topm_ids,
            "topm_probs": topm_probs,
        }
    if not samples:
        msg = f"No MTP token samples loaded from {manifest_path}"
        raise RuntimeError(msg)
    return samples


def _split_positions(num_samples: int, val_fraction: float) -> tuple[list[int], list[int]]:
    if num_samples == 1:
        return [0], []
    val_count = int(round(num_samples * val_fraction))
    val_count = min(num_samples - 1, max(1, val_count))
    return list(range(num_samples - val_count)), list(range(num_samples - val_count, num_samples))


def _samples_to_dataset(
    alignment_samples: list[tuple[int, dict[str, torch.Tensor]]],
    token_samples: dict[int, dict[str, torch.Tensor]],
    positions: list[int],
    *,
    num_experts: int,
    max_tokens: int | None,
) -> PrefetchShadowDataset | None:
    if not positions:
        return None
    target_parts = []
    current_parts = []
    target_token_parts = []
    mtp_id_parts = []
    mtp_prob_parts = []
    token_sample_parts = []
    sample_indices = []
    for position in positions:
        sample_idx, batch = alignment_samples[position]
        sidecar = token_samples[sample_idx]
        target_ids = batch["target_expert_ids"].long()
        target_weights = batch["target_expert_weights"].float()
        current_ids = batch["current_expert_ids"].long()
        current_weights = batch["current_expert_weights"].float()
        target_token_ids = batch["target_token_ids"].long()
        source_indices = batch["source_token_indices"].long()
        token_count = min(
            int(target_ids.shape[0]),
            int(sidecar["topm_ids"].shape[0]),
            int(source_indices.shape[0]),
        )
        if max_tokens is not None:
            token_count = min(token_count, int(max_tokens))
        if token_count <= 0:
            continue
        target_parts.append(
            target_expert_ids_to_dense_weights(
                target_ids[:token_count],
                target_weights[:token_count],
                num_experts=num_experts,
            )
        )
        current_parts.append(
            router_topk_to_dense_feature(
                current_ids[:token_count],
                current_weights[:token_count],
                num_experts=num_experts,
            )
        )
        target_token_parts.append(target_token_ids[:token_count])
        mtp_id_parts.append(sidecar["topm_ids"][source_indices[:token_count]])
        mtp_prob_parts.append(sidecar["topm_probs"][source_indices[:token_count]])
        token_sample_parts.append(torch.full((token_count,), int(sample_idx), dtype=torch.long))
        sample_indices.append(sample_idx)
    if not target_parts:
        msg = "No token examples were built for prefetch shadow simulation."
        raise RuntimeError(msg)
    return PrefetchShadowDataset(
        target_mass=torch.cat(target_parts, dim=0),
        current_feature=torch.cat(current_parts, dim=0),
        target_token_ids=torch.cat(target_token_parts, dim=0),
        mtp_topm_ids=torch.cat(mtp_id_parts, dim=0),
        mtp_topm_probs=torch.cat(mtp_prob_parts, dim=0),
        sample_indices=sample_indices,
        token_sample_indices=torch.cat(token_sample_parts, dim=0),
    )


def _apply_mtp_token_frequency_table(
    table: TokenFrequencyTable,
    topm_ids: torch.Tensor,
    topm_probs: torch.Tensor,
) -> torch.Tensor:
    fallback = table.fallback
    if fallback.shape[1] != 1:
        msg = "MTP token prior currently supports future_window=1 only."
        raise ValueError(msg)
    output = torch.zeros(
        int(topm_ids.shape[0]),
        int(fallback.shape[1]),
        int(fallback.shape[2]),
        int(fallback.shape[3]),
        dtype=torch.float32,
    )
    fallback_value = fallback[0, 0]
    for token_index in range(int(topm_ids.shape[0])):
        weights = topm_probs[token_index].float()
        weights = weights / weights.sum().clamp_min(1e-12)
        mixed = torch.zeros_like(fallback_value)
        for candidate_index, weight in enumerate(weights):
            token_id = int(topm_ids[token_index, candidate_index])
            mixed = mixed + float(weight.item()) * table.values.get((0, token_id), fallback_value)
        output[token_index, 0] = mixed
    return output


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
