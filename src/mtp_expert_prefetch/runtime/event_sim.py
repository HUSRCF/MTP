from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch

from mtp_expert_prefetch.admission import (
    add_metadata_budget_decisions,
    add_premap_budget_decisions,
    score_threshold_mtp_extra_decision_masks,
)
from mtp_expert_prefetch.evaluation.prefetch_shadow import (
    mask_metrics,
    novel_mtp_extra_mask,
    priority_admission_mask,
    queue_aware_ready_mask,
    topk_mask,
)


@dataclass(frozen=True)
class StallProxyReport:
    transition_topk: int
    mtp_topk: int
    num_layers: int
    layer_ms: float
    sampling_ms: float
    mtp_delay_ms: float
    bandwidth_gbps: float
    expert_bytes: int
    admission_capacity_per_layer: int | None
    policies: dict[str, dict[str, float]]
    notes: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = True
        return payload


def simulate_stall_proxy(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    transition_topk: int = 32,
    mtp_topk: int = 64,
    max_extras: list[int] | None = None,
    num_layers: int = 40,
    layer_ms: float = 1.0,
    sampling_ms: float = 0.0,
    mtp_delay_ms: float = 0.0,
    bandwidth_gbps: float = 16.0,
    expert_bytes: int = 1_650_000,
    token_sample_indices: torch.Tensor | None = None,
    admission_capacity_per_layer: int | None = None,
    gated_score_tensors: dict[str, torch.Tensor] | None = None,
    gated_score_thresholds: dict[str, float] | None = None,
    gated_metadata_budget_score_tensors: dict[str, torch.Tensor] | None = None,
    gated_metadata_budget_score_thresholds: dict[str, float] | None = None,
    gated_metadata_budget_max_extra: int | None = None,
    gated_premap_budget_max_extra: int | None = None,
    gated_max_extra: int | None = None,
    enable_gated_action_downgrade: bool = False,
    gated_metadata_threshold_ratio: float = 0.5,
    gated_premap_threshold_ratio: float = 0.25,
    gated_full_fetch_ready_threshold: float = 0.75,
    gated_metadata_downgrade_enabled: bool = True,
    gated_premap_downgrade_enabled: bool = True,
    metadata_bytes: int = 65_536,
    premap_bytes: int = 4_096,
    metadata_supplemental_saved_us: float = 20.0,
    premap_supplemental_saved_us: float = 5.0,
    action_cost_overlap_factor: float = 0.0,
    include_unique_payload_counters: bool = True,
    include_score_bin_counters: bool = True,
) -> StallProxyReport:
    """Estimate true-router supplemental fetch/stall after prefetch readiness.

    This is a trace-driven proxy, not a real DMA runtime. It derives token/layer
    demand from the recorded true router top-k mass and derives ready candidates
    from the queue-aware prefetch model. Missing true experts are counted as
    supplemental fetches at demand time.
    """
    _validate_shapes(transition_scores, mtp_scores, target_mass)
    max_extras = sorted({int(value) for value in (max_extras or [0, 4, 8]) if int(value) >= 0})
    if 0 not in max_extras:
        max_extras = [0, *max_extras]

    base_mask = topk_mask(transition_scores, k=transition_topk)
    base_admission = _admission_mask(
        transition_scores,
        mtp_scores,
        token_sample_indices=token_sample_indices,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=0,
        capacity=admission_capacity_per_layer,
    )
    base_issued_mask = base_mask & base_admission
    offline_masks = {"transition_ready": base_mask}
    for max_extra in max_extras:
        if max_extra == 0:
            continue
        extra = novel_mtp_extra_mask(
            base_mask,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
        )
        offline_masks[f"transition_top{transition_topk}_plus_offline_mtp_extra{max_extra}"] = (
            base_mask | extra
        )

    policies: dict[str, dict[str, float]] = {}
    transition_ready_raw, transition_queue_stats = queue_aware_ready_mask(
        transition_scores,
        mtp_scores,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=0,
        num_layers=num_layers,
        layer_ms=layer_ms,
        sampling_ms=sampling_ms,
        mtp_delay_ms=mtp_delay_ms,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
    )
    transition_ready = transition_ready_raw & base_issued_mask
    transition_metrics = _policy_stall_metrics(
        transition_ready,
        target_mass,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
    )
    transition_metrics.update(
        _shadow_counter_metrics(
            requested_mask=base_mask,
            issued_mask=base_issued_mask,
            ready_mask=transition_ready,
            target_mass=target_mass,
            expert_bytes=expert_bytes,
            token_sample_indices=token_sample_indices,
            include_unique_payload_counters=include_unique_payload_counters,
        )
    )
    transition_metrics.update(
        _prefixed_float_dict(mask_metrics(transition_ready, target_mass), "ready")
    )
    transition_metrics.update(_prefixed_float_dict(transition_queue_stats, "queue"))
    policies["transition_ready"] = transition_metrics

    baseline_missing_fetches = transition_metrics["supplemental_fetch_count"]
    baseline_stall_ms = transition_metrics["supplemental_stall_ms_sum"]
    baseline_miss_mass = transition_metrics["supplemental_miss_mass_fraction"]

    for max_extra in max_extras:
        if max_extra == 0:
            continue
        ready, queue_stats = queue_aware_ready_mask(
            transition_scores,
            mtp_scores,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            num_layers=num_layers,
            layer_ms=layer_ms,
            sampling_ms=sampling_ms,
            mtp_delay_ms=mtp_delay_ms,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
        )
        offline_name = f"transition_top{transition_topk}_plus_offline_mtp_extra{max_extra}"
        admitted = _admission_mask(
            transition_scores,
            mtp_scores,
            token_sample_indices=token_sample_indices,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            capacity=admission_capacity_per_layer,
        )
        issued_mask = offline_masks[offline_name] & admitted
        ready = ready & issued_mask
        metrics = _policy_stall_metrics(
            ready,
            target_mass,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
        )
        metrics.update(
            _shadow_counter_metrics(
                requested_mask=offline_masks[offline_name],
                issued_mask=issued_mask,
                ready_mask=ready,
                target_mass=target_mass,
                expert_bytes=expert_bytes,
                token_sample_indices=token_sample_indices,
                include_unique_payload_counters=include_unique_payload_counters,
            )
        )
        metrics.update(
            _prefixed_float_dict(mask_metrics(ready, target_mass, base_mask=base_mask), "ready")
        )
        metrics.update(_prefixed_float_dict(queue_stats, "queue"))
        offline_metrics = mask_metrics(offline_masks[offline_name], target_mass, base_mask=base_mask)
        admitted_metrics = mask_metrics(issued_mask, target_mass, base_mask=base_issued_mask)
        metrics["offline_pool_mass_coverage"] = float(offline_metrics["pool_mass_coverage"])
        metrics["offline_delta_pool_mass_coverage"] = float(
            offline_metrics["pool_mass_coverage"]
            - mask_metrics(base_mask, target_mass)["pool_mass_coverage"]
        )
        metrics["admitted_pool_mass_coverage"] = float(admitted_metrics["pool_mass_coverage"])
        metrics["admitted_delta_pool_mass_coverage"] = float(
            admitted_metrics["pool_mass_coverage"]
            - mask_metrics(base_issued_mask, target_mass)["pool_mass_coverage"]
        )
        metrics["saved_supplemental_fetch_count_vs_transition"] = float(
            baseline_missing_fetches - metrics["supplemental_fetch_count"]
        )
        metrics["saved_supplemental_fetch_bytes_vs_transition"] = float(
            metrics["saved_supplemental_fetch_count_vs_transition"] * float(expert_bytes)
        )
        metrics["saved_supplemental_stall_ms_vs_transition"] = float(
            baseline_stall_ms - metrics["supplemental_stall_ms_sum"]
        )
        metrics["saved_miss_mass_fraction_vs_transition"] = float(
            baseline_miss_mass - metrics["supplemental_miss_mass_fraction"]
        )
        metrics["stall_reduction_ratio_vs_transition"] = (
            metrics["saved_supplemental_stall_ms_vs_transition"] / baseline_stall_ms
            if baseline_stall_ms > 0.0
            else 0.0
        )
        _add_transition_delta_metrics(metrics, transition_metrics)
        policies[f"transition_top{transition_topk}_plus_ready_mtp_extra{max_extra}"] = metrics

    if gated_score_tensors:
        gated_score_thresholds = gated_score_thresholds or {}
        gated_cap = int(gated_max_extra if gated_max_extra is not None else max(max_extras))
        gated_cap = max(0, gated_cap)
        gated_ready_raw, gated_queue_stats = queue_aware_ready_mask(
            transition_scores,
            mtp_scores,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=gated_cap,
            num_layers=num_layers,
            layer_ms=layer_ms,
            sampling_ms=sampling_ms,
            mtp_delay_ms=mtp_delay_ms,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
        )
        gated_admission = _admission_mask(
            transition_scores,
            mtp_scores,
            token_sample_indices=token_sample_indices,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            max_extra=gated_cap,
            capacity=admission_capacity_per_layer,
        )
        for policy_name, score_tensor in gated_score_tensors.items():
            if policy_name not in gated_score_thresholds:
                msg = f"Missing score threshold for gated policy {policy_name!r}."
                raise ValueError(msg)
            if score_tensor.shape != transition_scores.shape:
                msg = (
                    f"Gated score tensor {policy_name!r} must have shape "
                    f"{tuple(transition_scores.shape)}, got {tuple(score_tensor.shape)}."
                )
                raise ValueError(msg)
            threshold = float(gated_score_thresholds[policy_name])
            action_threshold = threshold
            policy_allowed_mask = None
            metadata_allowed_mask = None
            premap_allowed_mask = None
            downgrade_stats: dict[str, float] = {}
            if enable_gated_action_downgrade:
                metadata_threshold = threshold * float(gated_metadata_threshold_ratio)
                premap_threshold = threshold * float(gated_premap_threshold_ratio)
                action_threshold = premap_threshold
                (
                    policy_allowed_mask,
                    metadata_allowed_mask,
                    premap_allowed_mask,
                    downgrade_stats,
                ) = _gated_action_downgrade_masks(
                    score_tensor.to(transition_scores.device),
                    full_fetch_score_threshold=threshold,
                    metadata_score_threshold=metadata_threshold,
                    premap_score_threshold=premap_threshold,
                    num_layers=num_layers,
                    layer_ms=layer_ms,
                    sampling_ms=sampling_ms,
                    mtp_delay_ms=mtp_delay_ms,
                    bandwidth_gbps=bandwidth_gbps,
                    expert_bytes=expert_bytes,
                    max_extra=gated_cap,
                    full_fetch_ready_threshold=gated_full_fetch_ready_threshold,
                    metadata_enabled=gated_metadata_downgrade_enabled,
                    premap_enabled=gated_premap_downgrade_enabled,
                )
            full_decisions = score_threshold_mtp_extra_decision_masks(
                base_mask,
                score_tensor.to(transition_scores.device),
                mtp_topk=mtp_topk,
                max_extra=gated_cap,
                score_threshold=action_threshold,
                policy_allowed_mask=policy_allowed_mask,
                metadata_allowed_mask=metadata_allowed_mask,
                premap_allowed_mask=premap_allowed_mask,
            )
            if (
                gated_metadata_budget_score_tensors is not None
                and gated_metadata_budget_score_thresholds is not None
                and policy_name in gated_metadata_budget_score_tensors
                and policy_name in gated_metadata_budget_score_thresholds
            ):
                decisions = add_metadata_budget_decisions(
                    base_mask,
                    full_decisions=full_decisions,
                    metadata_scores=gated_metadata_budget_score_tensors[policy_name].to(
                        transition_scores.device
                    ),
                    mtp_topk=mtp_topk,
                    metadata_max_extra=(
                        gated_cap
                        if gated_metadata_budget_max_extra is None
                        else int(gated_metadata_budget_max_extra)
                    ),
                    metadata_score_threshold=float(
                        gated_metadata_budget_score_thresholds[policy_name]
                    ),
                )
            else:
                decisions = full_decisions
            if gated_premap_budget_max_extra is not None and int(gated_premap_budget_max_extra) > 0:
                decisions = add_premap_budget_decisions(
                    base_mask,
                    decisions=decisions,
                    premap_scores=mtp_scores.to(transition_scores.device),
                    mtp_topk=mtp_topk,
                    premap_max_extra=int(gated_premap_budget_max_extra),
                )
            requested_mask = decisions.final_prefetch_mask(base_mask)
            issued_mask = requested_mask & gated_admission
            ready_mask = gated_ready_raw & issued_mask
            metrics = _policy_stall_metrics(
                ready_mask,
                target_mass,
                bandwidth_gbps=bandwidth_gbps,
                expert_bytes=expert_bytes,
            )
            metrics.update(
                _shadow_counter_metrics(
                    requested_mask=requested_mask,
                    issued_mask=issued_mask,
                    ready_mask=ready_mask,
                    target_mass=target_mass,
                    expert_bytes=expert_bytes,
                    token_sample_indices=token_sample_indices,
                    include_unique_payload_counters=include_unique_payload_counters,
                )
            )
            metrics.update(
                _prefixed_float_dict(
                    mask_metrics(ready_mask, target_mass, base_mask=base_mask),
                    "ready",
                )
            )
            metrics.update(_prefixed_float_dict(gated_queue_stats, "queue"))
            requested_metrics = mask_metrics(requested_mask, target_mass, base_mask=base_mask)
            admitted_metrics = mask_metrics(issued_mask, target_mass, base_mask=base_issued_mask)
            metrics["score_threshold"] = threshold
            metrics["action_score_threshold"] = float(action_threshold)
            metrics["gated_max_extra"] = float(gated_cap)
            metrics["gated_action_downgrade_enabled"] = float(
                bool(enable_gated_action_downgrade)
            )
            if (
                gated_metadata_budget_score_thresholds is not None
                and policy_name in gated_metadata_budget_score_thresholds
            ):
                metrics["metadata_budget_score_threshold"] = float(
                    gated_metadata_budget_score_thresholds[policy_name]
                )
                metrics["metadata_budget_max_extra"] = float(
                    gated_cap
                    if gated_metadata_budget_max_extra is None
                    else int(gated_metadata_budget_max_extra)
                )
            if gated_premap_budget_max_extra is not None:
                metrics["premap_budget_max_extra"] = float(
                    int(gated_premap_budget_max_extra)
                )
            if enable_gated_action_downgrade:
                metrics["metadata_score_threshold"] = float(
                    threshold * float(gated_metadata_threshold_ratio)
                )
                metrics["premap_score_threshold"] = float(
                    threshold * float(gated_premap_threshold_ratio)
                )
                metrics["full_fetch_ready_threshold"] = float(
                    gated_full_fetch_ready_threshold
                )
                metrics["metadata_downgrade_enabled"] = float(
                    bool(gated_metadata_downgrade_enabled)
                )
                metrics["premap_downgrade_enabled"] = float(
                    bool(gated_premap_downgrade_enabled)
                )
                metrics.update(_prefixed_float_dict(downgrade_stats, "downgrade"))
            metrics["requested_pool_mass_coverage"] = float(
                requested_metrics["pool_mass_coverage"]
            )
            metrics["requested_delta_pool_mass_coverage"] = float(
                requested_metrics["pool_mass_coverage"]
                - mask_metrics(base_mask, target_mass)["pool_mass_coverage"]
            )
            metrics["admitted_pool_mass_coverage"] = float(
                admitted_metrics["pool_mass_coverage"]
            )
            metrics["admitted_delta_pool_mass_coverage"] = float(
                admitted_metrics["pool_mass_coverage"]
                - mask_metrics(base_issued_mask, target_mass)["pool_mass_coverage"]
            )
            metrics["admission_reason_counters"] = _decision_reason_counter_metrics(
                decisions,
                expert_bytes=expert_bytes,
            )
            metrics["admission_action_counters"] = _decision_action_counter_metrics(
                decisions,
                expert_bytes=expert_bytes,
            )
            metrics["admission_action_reason_matrix"] = (
                _decision_action_reason_matrix_metrics(
                    decisions,
                    expert_bytes=expert_bytes,
                )
            )
            metrics["admission_action_outcomes"] = _decision_action_outcome_metrics(
                decisions,
                target_mass=target_mass,
                score_tensor=score_tensor.to(transition_scores.device),
                base_mask=base_mask,
                mtp_topk=mtp_topk,
                max_extra=gated_cap,
                expert_bytes=expert_bytes,
                metadata_bytes=metadata_bytes,
                premap_bytes=premap_bytes,
                metadata_supplemental_saved_us=metadata_supplemental_saved_us,
                premap_supplemental_saved_us=premap_supplemental_saved_us,
                action_cost_overlap_factor=action_cost_overlap_factor,
                bandwidth_gbps=bandwidth_gbps,
                include_score_bin_counters=include_score_bin_counters,
            )
            metrics["saved_supplemental_fetch_count_vs_transition"] = float(
                baseline_missing_fetches - metrics["supplemental_fetch_count"]
            )
            metrics["saved_supplemental_fetch_bytes_vs_transition"] = float(
                metrics["saved_supplemental_fetch_count_vs_transition"] * float(expert_bytes)
            )
            metrics["saved_supplemental_stall_ms_vs_transition"] = float(
                baseline_stall_ms - metrics["supplemental_stall_ms_sum"]
            )
            metrics["saved_miss_mass_fraction_vs_transition"] = float(
                baseline_miss_mass - metrics["supplemental_miss_mass_fraction"]
            )
            metrics["stall_reduction_ratio_vs_transition"] = (
                metrics["saved_supplemental_stall_ms_vs_transition"] / baseline_stall_ms
                if baseline_stall_ms > 0.0
                else 0.0
            )
            action_outcomes = metrics["admission_action_outcomes"]
            metrics["metadata_premap_setup_saved_ms"] = float(
                action_outcomes["metadata"]["later_used_setup_saved_ms"]
                + action_outcomes["premap"]["later_used_setup_saved_ms"]
            )
            metrics["serial_action_actual_transfer_ms"] = float(
                action_outcomes["summary"]["actual_transfer_ms_sum"]
            )
            metrics["overlap_adjusted_action_cost_ms"] = float(
                action_outcomes["summary"]["overlap_adjusted_actual_transfer_ms_sum"]
            )
            metrics["serial_net_benefit_ms_vs_transition"] = float(
                metrics["saved_supplemental_stall_ms_vs_transition"]
                + metrics["metadata_premap_setup_saved_ms"]
                - metrics["serial_action_actual_transfer_ms"]
            )
            metrics["overlap_adjusted_net_benefit_ms_vs_transition"] = float(
                metrics["saved_supplemental_stall_ms_vs_transition"]
                + metrics["metadata_premap_setup_saved_ms"]
                - metrics["overlap_adjusted_action_cost_ms"]
            )
            _add_transition_delta_metrics(metrics, transition_metrics)
            policies[f"transition_top{transition_topk}_plus_gated_{policy_name}"] = metrics

    return StallProxyReport(
        transition_topk=int(transition_topk),
        mtp_topk=int(mtp_topk),
        num_layers=int(num_layers),
        layer_ms=float(layer_ms),
        sampling_ms=float(sampling_ms),
        mtp_delay_ms=float(mtp_delay_ms),
        bandwidth_gbps=float(bandwidth_gbps),
        expert_bytes=int(expert_bytes),
        admission_capacity_per_layer=(
            int(admission_capacity_per_layer)
            if admission_capacity_per_layer is not None
            else None
        ),
        policies=policies,
        notes={
            "model": (
                "Queue-aware ready-before-demand candidates are compared with "
                "recorded true router top-k demand. Missing true experts are "
                "counted as supplemental fetches at demand time."
            ),
            "stall_proxy": (
                "stall_ms assumes serial supplemental transfer at configured "
                "bandwidth and does not include kernel scheduling or real DMA "
                "contention; use deltas rather than absolute latency claims."
            ),
            "admission": (
                "When admission_capacity_per_layer is set, token-policy issued "
                "candidates are intersected with sample/layer priority admission "
                "so P4/P5 cannot displace protected transition candidates."
            ),
            "gated_policies": (
                "Optional gated policies use canonical score-threshold MTP-extra "
                "admission masks and report action/reason counters alongside "
                "issued, ready, used, unused, and skipped byte counters. When "
                "downgrade actions are enabled, only full_fetch MTP extras enter "
                "the ready/prefetch mask; metadata and premap remain lightweight "
                "preparation actions with separate cost and later-used counters."
            ),
            "unique_payload_counters": (
                "Unique sample/layer/expert payload counters are optional because "
                "they are substantially more expensive than token-level runtime "
                "shadow counters."
            ),
        },
    )


def write_stall_proxy_report(report: StallProxyReport, output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def _policy_stall_metrics(
    ready_mask: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    bandwidth_gbps: float,
    expert_bytes: int,
) -> dict[str, float]:
    demand_mask = target_mass.float().gt(0.0)
    missing = demand_mask & ~ready_mask
    ready_true = demand_mask & ready_mask
    mass = target_mass.float().clamp_min(0.0)
    total_mass = mass.sum().clamp_min(1e-12)
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0
    per_expert_ms = float(expert_bytes) / max(bytes_per_ms, 1e-12)
    missing_counts = missing.float().sum(dim=-1)
    true_top1 = mass.argmax(dim=-1, keepdim=True)
    true_top1_weight = mass.gather(-1, true_top1).squeeze(-1)
    top1_missing = ~ready_mask.gather(-1, true_top1).squeeze(-1)
    top1_weighted_miss = true_top1_weight * top1_missing.float()
    token_layer_count = int(missing_counts.numel())
    return {
        "true_demand_count": float(demand_mask.float().sum().item()),
        "ready_true_demand_count": float(ready_true.float().sum().item()),
        "ready_true_demand_rate": float(
            ready_true.float().sum().item() / max(1.0, demand_mask.float().sum().item())
        ),
        "supplemental_fetch_count": float(missing.float().sum().item()),
        "supplemental_fetch_bytes": float(missing.float().sum().item() * float(expert_bytes)),
        "supplemental_stall_ms_sum": float(missing_counts.sum().item() * per_expert_ms),
        "supplemental_stall_ms_mean_per_token_layer": float(
            missing_counts.mean().item() * per_expert_ms
        ),
        "supplemental_stall_ms_p95_per_token_layer": float(
            torch.quantile(missing_counts.flatten(), 0.95).item() * per_expert_ms
        ),
        "supplemental_miss_mass_fraction": float((mass[missing].sum() / total_mass).item()),
        "ready_mass_fraction": float((mass[ready_true].sum() / total_mass).item()),
        "top1_supplemental_fetch_rate": float(top1_missing.float().mean().item()),
        "weighted_top1_supplemental_miss": float(top1_weighted_miss.mean().item()),
        "token_layer_count": float(token_layer_count),
        "per_expert_supplemental_fetch_ms": float(per_expert_ms),
    }


def _admission_mask(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    *,
    token_sample_indices: torch.Tensor | None,
    transition_topk: int,
    mtp_topk: int,
    max_extra: int,
    capacity: int | None,
) -> torch.Tensor:
    if capacity is None:
        return torch.ones_like(transition_scores, dtype=torch.bool)
    if token_sample_indices is None:
        msg = "token_sample_indices is required when admission_capacity_per_layer is set."
        raise ValueError(msg)
    return priority_admission_mask(
        transition_scores,
        mtp_scores,
        token_sample_indices.to(torch.long).to(transition_scores.device),
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
        capacity=int(capacity),
    )


def _gated_action_downgrade_masks(
    score_tensor: torch.Tensor,
    *,
    full_fetch_score_threshold: float,
    metadata_score_threshold: float,
    premap_score_threshold: float,
    num_layers: int,
    layer_ms: float,
    sampling_ms: float,
    mtp_delay_ms: float,
    bandwidth_gbps: float,
    expert_bytes: int,
    max_extra: int,
    full_fetch_ready_threshold: float,
    metadata_enabled: bool,
    premap_enabled: bool,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, float]]:
    """Build action masks for score-gated MTP extras.

    The score threshold passed into the canonical admission helper is the
    premap threshold. These masks then promote eligible candidates to metadata
    or full_fetch only when their stronger thresholds and ready constraints pass.
    """
    score = score_tensor.float()
    metadata_threshold = max(float(premap_score_threshold), float(metadata_score_threshold))
    full_threshold = max(metadata_threshold, float(full_fetch_score_threshold))
    premap_threshold = float(premap_score_threshold)
    finite = torch.isfinite(score)
    actual_layers = int(score.shape[2])
    layer_ready = _mtp_extra_ready_layer_factors(
        num_layers=actual_layers,
        layer_ms=float(layer_ms),
        sampling_ms=float(sampling_ms),
        mtp_delay_ms=float(mtp_delay_ms),
        bandwidth_gbps=float(bandwidth_gbps),
        expert_bytes=int(expert_bytes),
        max_extra=int(max_extra),
        device=score.device,
    )
    ready_mask = layer_ready.view(1, 1, actual_layers, 1).ge(
        float(full_fetch_ready_threshold)
    )
    ready_mask = ready_mask.expand_as(score)
    full_fetch_allowed = finite & score.ge(full_threshold) & ready_mask
    metadata_allowed = (
        finite & score.ge(metadata_threshold)
        if bool(metadata_enabled)
        else torch.zeros_like(finite, dtype=torch.bool)
    )
    premap_allowed = (
        finite & score.ge(premap_threshold)
        if bool(premap_enabled)
        else torch.zeros_like(finite, dtype=torch.bool)
    )
    ready_min = float(layer_ready.min().item()) if layer_ready.numel() else 0.0
    ready_mean = float(layer_ready.mean().item()) if layer_ready.numel() else 0.0
    ready_max = float(layer_ready.max().item()) if layer_ready.numel() else 0.0
    ready_layer_count = float(
        layer_ready.ge(float(full_fetch_ready_threshold)).float().sum().item()
    )
    return (
        full_fetch_allowed,
        metadata_allowed,
        premap_allowed,
        {
            "layer_ready_min": ready_min,
            "layer_ready_mean": ready_mean,
            "layer_ready_max": ready_max,
            "full_fetch_ready_layer_count": ready_layer_count,
            "full_fetch_ready_layer_fraction": ready_layer_count
            / max(1.0, float(actual_layers)),
        },
    )


def _mtp_extra_ready_layer_factors(
    *,
    num_layers: int,
    layer_ms: float,
    sampling_ms: float,
    mtp_delay_ms: float,
    bandwidth_gbps: float,
    expert_bytes: int,
    max_extra: int,
    device: torch.device,
) -> torch.Tensor:
    if max_extra <= 0:
        return torch.ones(num_layers, dtype=torch.float32, device=device)
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0
    values = []
    for layer_idx in range(int(num_layers)):
        lead_ms = max(
            0.0,
            float(layer_idx) * float(layer_ms) + float(sampling_ms) - float(mtp_delay_ms),
        )
        fetch_capacity = lead_ms * bytes_per_ms / max(1.0, float(expert_bytes))
        values.append(min(1.0, fetch_capacity / float(max_extra)))
    return torch.tensor(values, dtype=torch.float32, device=device)


def _shadow_counter_metrics(
    *,
    requested_mask: torch.Tensor,
    issued_mask: torch.Tensor,
    ready_mask: torch.Tensor,
    target_mass: torch.Tensor,
    expert_bytes: int,
    token_sample_indices: torch.Tensor | None = None,
    include_unique_payload_counters: bool = True,
) -> dict[str, float]:
    requested = requested_mask.bool()
    issued = issued_mask.bool()
    ready = ready_mask.bool() & issued
    late = issued & ~ready
    demand = target_mass.float().gt(0.0)
    used = ready & demand
    unused = ready & ~demand
    skipped = requested & ~issued
    issued_count = issued.float().sum().item()
    ready_count = ready.float().sum().item()
    used_count = used.float().sum().item()
    unused_count = unused.float().sum().item()
    skipped_count = skipped.float().sum().item()
    metrics = {
        "requested_count": float(requested.float().sum().item()),
        "requested_bytes": float(requested.float().sum().item() * float(expert_bytes)),
        "issued_count": float(issued_count),
        "issued_bytes": float(issued_count * float(expert_bytes)),
        "ready_count": float(ready_count),
        "ready_bytes": float(ready_count * float(expert_bytes)),
        "late_count": float(late.float().sum().item()),
        "late_bytes": float(late.float().sum().item() * float(expert_bytes)),
        "unused_count": float(unused_count),
        "unused_bytes": float(unused_count * float(expert_bytes)),
        "used_count": float(used_count),
        "used_bytes": float(used_count * float(expert_bytes)),
        "skipped_count": float(skipped_count),
        "skipped_bytes": float(skipped_count * float(expert_bytes)),
        "issued_ratio_of_requested": float(issued_count / max(1.0, requested.float().sum().item())),
        "skipped_ratio_of_requested": float(
            skipped_count / max(1.0, requested.float().sum().item())
        ),
        "ready_ratio_of_issued": float(ready_count / max(1.0, issued_count)),
        "used_ratio_of_issued": float(used_count / max(1.0, issued_count)),
        "unused_ratio_of_issued": float(unused_count / max(1.0, issued_count)),
        "unused_ratio_of_ready": float(unused_count / max(1.0, ready_count)),
    }
    if token_sample_indices is not None and include_unique_payload_counters:
        metrics.update(
            _unique_payload_counter_metrics(
                requested=requested,
                issued=issued,
                ready=ready,
                demand=demand,
                token_sample_indices=token_sample_indices,
                expert_bytes=expert_bytes,
            )
        )
    return metrics


def _decision_reason_counter_metrics(
    decisions: Any,
    *,
    expert_bytes: int,
) -> dict[str, dict[str, float]]:
    counters = {}
    for reason, mask in decisions.reason_masks().items():
        count = float(mask.float().sum().item())
        counters[str(reason)] = {
            "count": count,
            "bytes": float(count * int(expert_bytes)),
        }
    return counters


def _decision_action_counter_metrics(
    decisions: Any,
    *,
    expert_bytes: int,
) -> dict[str, dict[str, float]]:
    counters = {}
    for action, mask in decisions.action_masks().items():
        count = float(mask.float().sum().item())
        counters[str(action)] = {
            "count": count,
            "bytes": float(count * int(expert_bytes)),
        }
    return counters


def _decision_action_reason_matrix_metrics(
    decisions: Any,
    *,
    expert_bytes: int,
) -> dict[str, dict[str, dict[str, float]]]:
    matrix = {}
    action_masks = decisions.action_masks()
    for reason, reason_mask in decisions.reason_masks().items():
        reason_row = {}
        for action, action_mask in action_masks.items():
            count = float((reason_mask & action_mask).float().sum().item())
            reason_row[str(action)] = {
                "count": count,
                "bytes": float(count * int(expert_bytes)),
            }
        matrix[str(reason)] = reason_row
    return matrix


def _decision_action_outcome_metrics(
    decisions: Any,
    *,
    target_mass: torch.Tensor,
    score_tensor: torch.Tensor,
    base_mask: torch.Tensor,
    mtp_topk: int,
    max_extra: int,
    expert_bytes: int,
    metadata_bytes: int,
    premap_bytes: int,
    metadata_supplemental_saved_us: float,
    premap_supplemental_saved_us: float,
    action_cost_overlap_factor: float,
    bandwidth_gbps: float,
    include_score_bin_counters: bool,
) -> dict[str, Any]:
    action_masks = decisions.action_masks()
    demand = target_mass.float().gt(0.0)
    novel_rank = _novel_rank_tensor(base_mask, score_tensor, mtp_topk=mtp_topk)
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0
    overlap_factor = min(max(float(action_cost_overlap_factor), 0.0), 1.0)
    action_cost_bytes = {
        "full_fetch": int(expert_bytes),
        "metadata": int(metadata_bytes),
        "premap": int(premap_bytes),
        "skip": 0,
    }
    setup_saved_us = {
        "full_fetch": 0.0,
        "metadata": float(metadata_supplemental_saved_us),
        "premap": float(premap_supplemental_saved_us),
        "skip": 0.0,
    }
    outcomes: dict[str, Any] = {}
    total_actual_bytes = 0.0
    total_payload_equivalent_bytes = 0.0
    total_later_used_setup_saved_ms = 0.0
    for action, mask in action_masks.items():
        selected = mask.bool()
        count = float(selected.float().sum().item())
        later_used = selected & demand
        unused = selected & ~demand
        later_used_count = float(later_used.float().sum().item())
        unused_count = float(unused.float().sum().item())
        actual_bytes = count * float(action_cost_bytes[str(action)])
        payload_equivalent_bytes = count * float(expert_bytes)
        actual_transfer_ms = actual_bytes / max(bytes_per_ms, 1e-12)
        overlap_adjusted_transfer_ms = actual_transfer_ms * (1.0 - overlap_factor)
        later_used_setup_saved_ms = (
            later_used_count * float(setup_saved_us[str(action)]) / 1000.0
        )
        total_actual_bytes += actual_bytes
        total_payload_equivalent_bytes += payload_equivalent_bytes
        total_later_used_setup_saved_ms += later_used_setup_saved_ms
        action_outcome = {
            "count": count,
            "payload_equivalent_bytes": payload_equivalent_bytes,
            "actual_bytes": actual_bytes,
            "actual_transfer_ms": actual_transfer_ms,
            "overlap_adjusted_actual_transfer_ms": overlap_adjusted_transfer_ms,
            "later_used_count": later_used_count,
            "later_used_payload_equivalent_bytes": later_used_count * float(expert_bytes),
            "later_used_rate": later_used_count / max(1.0, count),
            "unused_count": unused_count,
            "unused_payload_equivalent_bytes": unused_count * float(expert_bytes),
            "unused_rate": unused_count / max(1.0, count),
            "later_used_setup_saved_ms": later_used_setup_saved_ms,
            "net_setup_benefit_ms": later_used_setup_saved_ms - actual_transfer_ms,
            "overlap_adjusted_net_setup_benefit_ms": later_used_setup_saved_ms
            - overlap_adjusted_transfer_ms,
            "by_layer": _action_by_layer_metrics(selected, later_used),
            "by_rank": _action_by_rank_metrics(
                selected,
                later_used,
                novel_rank=novel_rank,
                max_extra=max_extra,
            ),
        }
        if include_score_bin_counters:
            action_outcome["by_score_bin"] = _action_by_score_bin_metrics(
                selected,
                later_used,
                scores=score_tensor.float(),
                actual_bytes_per_action=float(action_cost_bytes[str(action)]),
                setup_saved_us=float(setup_saved_us[str(action)]),
                bytes_per_ms=bytes_per_ms,
                overlap_factor=overlap_factor,
            )
        outcomes[str(action)] = action_outcome
    skip_would_have_used = action_masks["skip"].bool() & demand
    skip_would_have_used_count = float(skip_would_have_used.float().sum().item())
    outcomes["skip"]["would_have_used_count"] = skip_would_have_used_count
    outcomes["skip"]["would_have_used_payload_equivalent_bytes"] = (
        skip_would_have_used_count * float(expert_bytes)
    )
    outcomes["summary"] = {
        "actual_bytes": total_actual_bytes,
        "payload_equivalent_bytes": total_payload_equivalent_bytes,
        "actual_transfer_ms_sum": total_actual_bytes / max(bytes_per_ms, 1e-12),
        "overlap_adjusted_actual_transfer_ms_sum": (
            total_actual_bytes / max(bytes_per_ms, 1e-12)
        )
        * (1.0 - overlap_factor),
        "action_cost_overlap_factor": overlap_factor,
        "metadata_premap_setup_saved_ms": total_later_used_setup_saved_ms,
        "metadata_bytes_per_action": float(metadata_bytes),
        "premap_bytes_per_action": float(premap_bytes),
        "metadata_supplemental_saved_us": float(metadata_supplemental_saved_us),
        "premap_supplemental_saved_us": float(premap_supplemental_saved_us),
    }
    return outcomes


def _novel_rank_tensor(
    base_mask: torch.Tensor,
    scores: torch.Tensor,
    *,
    mtp_topk: int,
) -> torch.Tensor:
    mtp_topk = min(max(0, int(mtp_topk)), int(scores.shape[-1]))
    ranks = torch.zeros_like(base_mask, dtype=torch.int16)
    if mtp_topk == 0:
        return ranks
    finite_scores = scores.float().masked_fill(~torch.isfinite(scores.float()), -float("inf"))
    ranked = torch.topk(finite_scores, k=mtp_topk, dim=-1).indices
    ranked_novel = ~base_mask.gather(-1, ranked)
    ranked_novel_rank = ranked_novel.to(torch.int16).cumsum(dim=-1)
    ranks.scatter_(
        -1,
        ranked,
        torch.where(ranked_novel, ranked_novel_rank, torch.zeros_like(ranked_novel_rank)).to(
            ranks.dtype
        ),
    )
    return ranks


def _action_by_layer_metrics(
    selected: torch.Tensor,
    later_used: torch.Tensor,
) -> dict[str, list[float]]:
    count_by_layer = selected.float().sum(dim=(0, 1, 3))
    later_used_by_layer = later_used.float().sum(dim=(0, 1, 3))
    rate_by_layer = later_used_by_layer / count_by_layer.clamp_min(1.0)
    return {
        "count": [float(value) for value in count_by_layer.detach().cpu().tolist()],
        "later_used_count": [
            float(value) for value in later_used_by_layer.detach().cpu().tolist()
        ],
        "later_used_rate": [float(value) for value in rate_by_layer.detach().cpu().tolist()],
    }


def _action_by_rank_metrics(
    selected: torch.Tensor,
    later_used: torch.Tensor,
    *,
    novel_rank: torch.Tensor,
    max_extra: int,
) -> dict[str, list[float]]:
    max_rank = max(0, int(max_extra))
    counts = []
    later_counts = []
    rates = []
    for rank in range(1, max_rank + 1):
        rank_mask = selected & novel_rank.eq(rank)
        rank_later_used = later_used & novel_rank.eq(rank)
        count = float(rank_mask.float().sum().item())
        later_count = float(rank_later_used.float().sum().item())
        counts.append(count)
        later_counts.append(later_count)
        rates.append(later_count / max(1.0, count))
    return {
        "count": counts,
        "later_used_count": later_counts,
        "later_used_rate": rates,
    }


def _action_by_score_bin_metrics(
    selected: torch.Tensor,
    later_used: torch.Tensor,
    *,
    scores: torch.Tensor,
    actual_bytes_per_action: float,
    setup_saved_us: float,
    bytes_per_ms: float,
    overlap_factor: float,
) -> dict[str, list[float] | list[str]]:
    selected_scores = scores[selected & torch.isfinite(scores)]
    labels = ["0_10", "10_25", "25_50", "50_75", "75_90", "90_100"]
    quantiles = [0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 1.0]
    if selected_scores.numel() == 0:
        return {
            "labels": labels,
            "score_min": [],
            "score_max": [],
            "count": [0.0 for _ in labels],
            "later_used_count": [0.0 for _ in labels],
            "later_used_rate": [0.0 for _ in labels],
            "actual_transfer_ms": [0.0 for _ in labels],
            "net_setup_benefit_ms": [0.0 for _ in labels],
            "overlap_adjusted_net_setup_benefit_ms": [0.0 for _ in labels],
        }
    # ROCm/PyTorch quantile has practical input-size limits on large action tensors.
    # Use a deterministic score sample for bin boundaries while keeping full-tensor
    # masks below for the actual counts/outcomes.
    boundary_scores = selected_scores.detach().float().flatten()
    max_boundary_scores = 1_000_000
    if boundary_scores.numel() > max_boundary_scores:
        sample_indices = torch.linspace(
            0,
            boundary_scores.numel() - 1,
            steps=max_boundary_scores,
            device=boundary_scores.device,
            dtype=torch.long,
        )
        boundary_scores = boundary_scores.index_select(0, sample_indices)
    boundaries = torch.quantile(
        boundary_scores.cpu(),
        torch.tensor(quantiles, dtype=torch.float32),
    ).to(device=selected_scores.device)
    counts = []
    later_counts = []
    rates = []
    actual_transfer_ms = []
    net_setup_benefit_ms = []
    overlap_adjusted_net_setup_benefit_ms = []
    score_min = []
    score_max = []
    for idx, label in enumerate(labels):
        lower = boundaries[idx]
        upper = boundaries[idx + 1]
        if label == labels[0]:
            bin_mask = selected & torch.isfinite(scores) & scores.ge(lower) & scores.le(upper)
        else:
            bin_mask = selected & torch.isfinite(scores) & scores.gt(lower) & scores.le(upper)
        bin_later_used = later_used & bin_mask
        count = float(bin_mask.float().sum().item())
        later_count = float(bin_later_used.float().sum().item())
        transfer_ms = count * float(actual_bytes_per_action) / max(bytes_per_ms, 1e-12)
        overlap_transfer_ms = transfer_ms * (1.0 - float(overlap_factor))
        setup_saved_ms = later_count * float(setup_saved_us) / 1000.0
        counts.append(count)
        later_counts.append(later_count)
        rates.append(later_count / max(1.0, count))
        actual_transfer_ms.append(transfer_ms)
        net_setup_benefit_ms.append(setup_saved_ms - transfer_ms)
        overlap_adjusted_net_setup_benefit_ms.append(setup_saved_ms - overlap_transfer_ms)
        score_min.append(float(lower.item()))
        score_max.append(float(upper.item()))
    return {
        "labels": labels,
        "score_min": score_min,
        "score_max": score_max,
        "count": counts,
        "later_used_count": later_counts,
        "later_used_rate": rates,
        "actual_transfer_ms": actual_transfer_ms,
        "net_setup_benefit_ms": net_setup_benefit_ms,
        "overlap_adjusted_net_setup_benefit_ms": overlap_adjusted_net_setup_benefit_ms,
    }


def _unique_payload_counter_metrics(
    *,
    requested: torch.Tensor,
    issued: torch.Tensor,
    ready: torch.Tensor,
    demand: torch.Tensor,
    token_sample_indices: torch.Tensor,
    expert_bytes: int,
) -> dict[str, float]:
    sample_ids = token_sample_indices.to(device=requested.device, dtype=torch.long)
    totals = {
        "requested": 0.0,
        "issued": 0.0,
        "ready": 0.0,
        "late": 0.0,
        "used": 0.0,
        "unused": 0.0,
        "skipped": 0.0,
    }
    for sample_id in torch.unique(sample_ids):
        rows = sample_ids.eq(sample_id)
        if not rows.any():
            continue
        unique_requested = requested[rows].any(dim=(0, 1))
        unique_issued = issued[rows].any(dim=(0, 1))
        unique_ready = ready[rows].any(dim=(0, 1)) & unique_issued
        unique_demand = demand[rows].any(dim=(0, 1))
        unique_late = unique_issued & ~unique_ready
        unique_used = unique_ready & unique_demand
        unique_unused = unique_ready & ~unique_demand
        unique_skipped = unique_requested & ~unique_issued
        totals["requested"] += float(unique_requested.float().sum().item())
        totals["issued"] += float(unique_issued.float().sum().item())
        totals["ready"] += float(unique_ready.float().sum().item())
        totals["late"] += float(unique_late.float().sum().item())
        totals["used"] += float(unique_used.float().sum().item())
        totals["unused"] += float(unique_unused.float().sum().item())
        totals["skipped"] += float(unique_skipped.float().sum().item())
    unique_issued = max(1.0, totals["issued"])
    unique_ready = max(1.0, totals["ready"])
    return {
        "unique_requested_count": totals["requested"],
        "unique_requested_bytes": totals["requested"] * float(expert_bytes),
        "unique_issued_count": totals["issued"],
        "unique_issued_bytes": totals["issued"] * float(expert_bytes),
        "unique_ready_count": totals["ready"],
        "unique_ready_bytes": totals["ready"] * float(expert_bytes),
        "unique_late_count": totals["late"],
        "unique_late_bytes": totals["late"] * float(expert_bytes),
        "unique_used_count": totals["used"],
        "unique_used_bytes": totals["used"] * float(expert_bytes),
        "unique_unused_count": totals["unused"],
        "unique_unused_bytes": totals["unused"] * float(expert_bytes),
        "unique_skipped_count": totals["skipped"],
        "unique_skipped_bytes": totals["skipped"] * float(expert_bytes),
        "unique_used_ratio_of_issued": totals["used"] / unique_issued,
        "unique_unused_ratio_of_issued": totals["unused"] / unique_issued,
        "unique_unused_ratio_of_ready": totals["unused"] / unique_ready,
        "payload_reuse_factor_issued": float(issued_count := issued.float().sum().item())
        / unique_issued,
    }


def _add_transition_delta_metrics(
    metrics: dict[str, float],
    transition_metrics: dict[str, float],
) -> None:
    for name in (
        "requested_bytes",
        "issued_bytes",
        "ready_bytes",
        "late_bytes",
        "used_bytes",
        "unused_bytes",
        "skipped_bytes",
        "requested_count",
        "issued_count",
        "ready_count",
        "late_count",
        "used_count",
        "unused_count",
        "skipped_count",
        "unique_requested_bytes",
        "unique_issued_bytes",
        "unique_ready_bytes",
        "unique_late_bytes",
        "unique_used_bytes",
        "unique_unused_bytes",
        "unique_skipped_bytes",
        "unique_requested_count",
        "unique_issued_count",
        "unique_ready_count",
        "unique_late_count",
        "unique_used_count",
        "unique_unused_count",
        "unique_skipped_count",
    ):
        if name in metrics or name in transition_metrics:
            metrics[f"delta_{name}_vs_transition"] = float(
                metrics.get(name, 0.0) - transition_metrics.get(name, 0.0)
            )

    extra_issued_gb = metrics["delta_issued_bytes_vs_transition"] / 1_000_000_000.0
    extra_issued_bytes = max(metrics["delta_issued_bytes_vs_transition"], 1.0)
    metrics["stall_saved_ms_per_extra_issued_gb"] = float(
        metrics.get("saved_supplemental_stall_ms_vs_transition", 0.0)
        / max(extra_issued_gb, 1e-12)
    )
    metrics["saved_supplemental_bytes_per_extra_issued_byte"] = float(
        metrics.get("saved_supplemental_fetch_bytes_vs_transition", 0.0)
        / extra_issued_bytes
    )
    metrics["delta_used_bytes_per_extra_issued_byte"] = float(
        metrics["delta_used_bytes_vs_transition"] / extra_issued_bytes
    )
    metrics["delta_unused_bytes_per_extra_issued_byte"] = float(
        metrics["delta_unused_bytes_vs_transition"] / extra_issued_bytes
    )


def _prefixed_float_dict(values: dict[str, float], prefix: str) -> dict[str, float]:
    return {
        f"{prefix}_{key}": float(value)
        for key, value in values.items()
        if isinstance(value, int | float)
    }


def _validate_shapes(
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
) -> None:
    if transition_scores.shape != mtp_scores.shape or transition_scores.shape != target_mass.shape:
        msg = (
            "transition_scores, mtp_scores, and target_mass must share shape; "
            f"got {tuple(transition_scores.shape)}, {tuple(mtp_scores.shape)}, "
            f"{tuple(target_mass.shape)}"
        )
        raise ValueError(msg)
    if transition_scores.ndim != 4:
        msg = f"Expected [tokens, future, layers, experts], got {transition_scores.shape}."
        raise ValueError(msg)
