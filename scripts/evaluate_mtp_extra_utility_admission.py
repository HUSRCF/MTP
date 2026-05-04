#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    _apply_mtp_token_frequency_table,
    _load_alignment_samples,
    _load_mtp_token_samples,
    _samples_to_dataset,
    _split_positions,
    novel_mtp_extra_mask,
    novel_mtp_extra_rank_mask,
    priority_admission_mask,
    queue_aware_ready_mask,
    score_threshold_mtp_extra_decision_masks,
    tail_swap_mtp_extra_mask,
    topk_mask,
)
from mtp_expert_prefetch.admission import (  # noqa: E402
    ScoreThresholdMetadata,
    build_mtp_extra_utility_scores,
)
from mtp_expert_prefetch.runtime.event_sim import (  # noqa: E402
    _policy_stall_metrics,
    _shadow_counter_metrics,
)
from mtp_expert_prefetch.training import (  # noqa: E402
    apply_transition_matrix,
    build_token_frequency_table,
    train_frequency_scores,
    train_transition_matrix,
)
from mtp_expert_prefetch.utils.config import find_project_root, load_yaml, resolve_path  # noqa: E402


DEFAULT_CONFIG = Path("configs/eval/prefetch_shadow_256sample_mtp_extra.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate per-rank and score-threshold utility admission for MTP extras."
    )
    parser.add_argument("config", type=Path, nargs="?", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/prefetch_shadow_256sample_mtp_extra/mtp_extra_utility_admission.json"),
    )
    parser.add_argument("--transition-topk", type=int, default=None)
    parser.add_argument("--mtp-topk", type=int, default=None)
    parser.add_argument("--max-extra", type=int, default=8)
    parser.add_argument("--bandwidth-gbps", type=float, default=6.589118730994282)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--layer-ms", type=float, default=1.0)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--mtp-delay-ms", type=float, default=2.0)
    parser.add_argument("--admission-capacity-per-layer", type=int, default=160)
    parser.add_argument("--threshold-calibration-fraction", type=float, default=0.5)
    parser.add_argument("--utility-rank-alpha", type=float, default=1.0)
    parser.add_argument("--disable-utility-layer-factor", action="store_true")
    parser.add_argument("--disable-utility-ready-factor", action="store_true")
    parser.add_argument(
        "--keep-fraction",
        type=float,
        action="append",
        default=None,
        help="Global fraction of MTP extra candidates to keep by MTP prior score.",
    )
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def _resolve_device(name: str) -> torch.device:
    if name.startswith("cuda") and not torch.cuda.is_available():
        msg = f"Requested {name}, but torch.cuda.is_available() is false."
        raise RuntimeError(msg)
    return torch.device(name)


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.config)
    config = load_yaml(args.config)
    merged_manifest = resolve_path(config["merged_manifest"], base_dir=project_root)
    mtp_token_manifest = resolve_path(config["mtp_token_manifest"], base_dir=project_root)
    output = resolve_path(args.output, base_dir=project_root)
    transition_topk = int(args.transition_topk or config.get("transition_topk", 32))
    mtp_topk = int(args.mtp_topk or config.get("mtp_topk", 64))
    keep_fractions = sorted(
        {float(value) for value in (args.keep_fraction or [0.125, 0.25, 0.5, 0.75, 1.0])}
    )

    future_window = int(config.get("future_window", 1))
    if future_window != 1:
        msg = "Utility admission evaluator currently expects future_window=1."
        raise ValueError(msg)
    alignment_samples = _load_alignment_samples(
        merged_manifest,
        future_window=future_window,
        max_samples=int(config["max_samples"]) if config.get("max_samples") is not None else None,
    )
    token_samples = _load_mtp_token_samples(mtp_token_manifest)
    train_positions, val_positions = _split_positions(
        len(alignment_samples),
        float(config.get("val_fraction", 0.25)),
    )
    train = _samples_to_dataset(
        alignment_samples,
        token_samples,
        train_positions,
        num_experts=int(config.get("num_experts", 256)),
        max_tokens=int(config["max_tokens"]) if config.get("max_tokens") is not None else None,
    )
    val = _samples_to_dataset(
        alignment_samples,
        token_samples,
        val_positions,
        num_experts=int(config.get("num_experts", 256)),
        max_tokens=int(config["max_tokens"]) if config.get("max_tokens") is not None else None,
    )
    eval_data = val if val is not None else train
    if train is None or eval_data is None:
        msg = "Empty train/eval split; cannot evaluate utility admission."
        raise RuntimeError(msg)

    transition = train_transition_matrix(train.current_feature, train.target_mass)
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

    admission_cpu = priority_admission_mask(
        transition_scores,
        mtp_scores,
        eval_data.token_sample_indices,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=int(args.max_extra),
        capacity=int(args.admission_capacity_per_layer),
    )
    device = _resolve_device(args.device)
    transition_scores = transition_scores.to(device)
    mtp_scores = mtp_scores.to(device)
    target_mass = eval_data.target_mass.to(device)
    admission = admission_cpu.to(device)
    token_sample_indices = eval_data.token_sample_indices.to(device)
    calibration_rows_cpu, heldout_rows_cpu, split_metadata = _calibration_heldout_rows(
        eval_data.token_sample_indices,
        fraction=float(args.threshold_calibration_fraction),
    )
    calibration_rows = calibration_rows_cpu.to(device)
    heldout_rows = heldout_rows_cpu.to(device)

    base = topk_mask(transition_scores, k=transition_topk)
    metadata_context = _threshold_metadata_context(
        config=config,
        merged_manifest=merged_manifest,
        mtp_token_manifest=mtp_token_manifest,
        output=output,
        num_samples=len(alignment_samples),
        target_mass=target_mass,
        mtp_topm_ids=eval_data.mtp_topm_ids,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=int(args.max_extra),
    )
    ready_raw, queue_stats = queue_aware_ready_mask(
        transition_scores,
        mtp_scores,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=int(args.max_extra),
        num_layers=int(config.get("num_layers", 40)),
        layer_ms=float(args.layer_ms),
        sampling_ms=float(args.sampling_ms),
        mtp_delay_ms=float(args.mtp_delay_ms),
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
    )
    base_issued = base & admission
    base_ready = ready_raw & base_issued
    base_metrics = _event_metrics(
        requested=base,
        issued=base_issued,
        ready=base_ready,
        target_mass=target_mass,
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        token_sample_indices=token_sample_indices,
    )
    layer_factors = (
        torch.ones(int(target_mass.shape[2]), device=device)
        if args.disable_utility_layer_factor
        else _calibrated_layer_factors(
            base,
            mtp_scores,
            target_mass,
            rows=calibration_rows,
            mtp_topk=mtp_topk,
            max_extra=int(args.max_extra),
        )
    )
    ready_factors = (
        torch.ones(int(target_mass.shape[2]), device=device)
        if args.disable_utility_ready_factor
        else _ready_layer_factors(
            num_layers=int(target_mass.shape[2]),
            layer_ms=float(args.layer_ms),
            sampling_ms=float(args.sampling_ms),
            mtp_delay_ms=float(args.mtp_delay_ms),
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
            max_extra=int(args.max_extra),
            device=device,
        )
    )
    utility_scores = build_mtp_extra_utility_scores(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        rank_alpha=float(args.utility_rank_alpha),
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )

    extra_all = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=int(args.max_extra),
    )
    per_rank = {}
    for rank in range(1, int(args.max_extra) + 1):
        rank_mask = novel_mtp_extra_rank_mask(
            base,
            mtp_scores,
            mtp_topk=mtp_topk,
            rank=rank,
        )
        issued = rank_mask & admission
        ready = ready_raw & issued
        per_rank[f"rank_{rank}"] = _extra_only_metrics(
            requested=rank_mask,
            issued=issued,
            ready=ready,
            target_mass=target_mass,
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
            token_sample_indices=token_sample_indices,
        )

    threshold_policies = {}
    candidate_scores = mtp_scores[extra_all]
    for keep_fraction in keep_fractions:
        keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
        if keep_fraction <= 0.0 or candidate_scores.numel() == 0:
            extra = torch.zeros_like(extra_all)
            threshold = float("inf")
        elif keep_fraction >= 1.0:
            extra = extra_all
            threshold = float(candidate_scores.min().item())
        else:
            threshold = float(torch.quantile(candidate_scores.float(), 1.0 - keep_fraction).item())
        decisions = score_threshold_mtp_extra_decision_masks(
            base,
            mtp_scores,
            mtp_topk=mtp_topk,
            max_extra=int(args.max_extra),
            score_threshold=threshold,
        )
        extra = decisions.admitted_full_fetch
        requested = base | extra
        issued = requested & admission
        ready = ready_raw & issued
        metrics = _event_metrics(
            requested=requested,
            issued=issued,
            ready=ready,
            target_mass=target_mass,
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
            token_sample_indices=token_sample_indices,
        )
        _add_delta_metrics(metrics, base_metrics, expert_bytes=int(args.expert_bytes))
        metrics["score_threshold"] = threshold
        metrics["admission_reason_counters"] = _decision_reason_counters(
            decisions,
            expert_bytes=int(args.expert_bytes),
        )
        metrics["score_threshold_metadata"] = ScoreThresholdMetadata(
            threshold=float(threshold),
            threshold_type="percentile",
            optimization_goal="stall_reduction",
            target_budget=f"keep_top_{keep_fraction:.3f}",
            metric="stall_saved_ms_per_extra_issued_gb",
            calibration_split="eval_all",
            heldout_split="eval_all",
            notes="Diagnostic threshold selected and evaluated on the same eval split.",
            **metadata_context,
        ).as_dict()
        metrics["keep_fraction"] = keep_fraction
        metrics["requested_extra_count"] = float(extra.float().sum().item())
        threshold_policies[f"keep_top_{keep_fraction:.3f}"] = metrics

    utility_threshold_policies = _evaluate_score_threshold_policies(
        base=base,
        score_tensor=utility_scores,
        target_mass=target_mass,
        admission=admission,
        ready_raw=ready_raw,
        token_sample_indices=token_sample_indices,
        base_metrics=base_metrics,
        mtp_topk=mtp_topk,
        max_extra=int(args.max_extra),
        keep_fractions=keep_fractions,
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        metadata_context={
            **metadata_context,
            "score_source": "mtp_token_prior_rank_layer_ready_utility_score",
        },
        threshold_type="percentile",
        calibration_split="eval_all",
        heldout_split="eval_all",
        notes=(
            "Diagnostic utility threshold selected and evaluated on the same eval split. "
            "Utility score applies MTP score, novel-rank decay, calibration layer factor, "
            "and lead-time ready factor."
        ),
    )

    tail_swap_policies = _evaluate_tail_swap_policies(
        transition_scores=transition_scores,
        mtp_scores=mtp_scores,
        target_mass=target_mass,
        admission=admission,
        ready_raw=ready_raw,
        token_sample_indices=token_sample_indices,
        base_metrics=base_metrics,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        swap_counts=[1, 2, 4, int(args.max_extra)],
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
    )

    oracle_extra = extra_all & target_mass.gt(0.0)
    oracle_requested = base | oracle_extra
    oracle_issued = oracle_requested & admission
    oracle_ready = ready_raw & oracle_issued
    oracle_metrics = _event_metrics(
        requested=oracle_requested,
        issued=oracle_issued,
        ready=oracle_ready,
        target_mass=target_mass,
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        token_sample_indices=token_sample_indices,
    )
    _add_delta_metrics(oracle_metrics, base_metrics, expert_bytes=int(args.expert_bytes))

    heldout = _evaluate_heldout_thresholds(
        base=base,
        mtp_scores=mtp_scores,
        target_mass=target_mass,
        admission=admission,
        ready_raw=ready_raw,
        calibration_rows=calibration_rows,
        heldout_rows=heldout_rows,
        token_sample_indices=token_sample_indices,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        max_extra=int(args.max_extra),
        keep_fractions=keep_fractions,
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        metadata_context=metadata_context,
        transition_scores=transition_scores,
        utility_scores=utility_scores,
    )

    payload = {
        "ok": True,
        "config": str(resolve_path(args.config, base_dir=project_root)),
        "merged_manifest": str(merged_manifest),
        "mtp_token_manifest": str(mtp_token_manifest),
        "output": str(output),
        "device": str(device),
        "eval_split": "val" if val is not None else "train",
        "num_eval_token_examples": int(target_mass.shape[0]),
        "threshold_calibration": split_metadata,
        "transition_topk": transition_topk,
        "mtp_topk": mtp_topk,
        "max_extra": int(args.max_extra),
        "admission_capacity_per_layer": int(args.admission_capacity_per_layer),
        "bandwidth_gbps": float(args.bandwidth_gbps),
        "layer_ms": float(args.layer_ms),
        "mtp_delay_ms": float(args.mtp_delay_ms),
        "queue_stats": queue_stats,
        "transition": base_metrics,
        "per_rank_extra": per_rank,
        "threshold_policies": threshold_policies,
        "utility_threshold_policies": utility_threshold_policies,
        "tail_swap_policies": tail_swap_policies,
        "oracle_used_extra_policy": oracle_metrics,
        "heldout_threshold_policies": heldout,
        "utility_gate": {
            "rank_alpha": float(args.utility_rank_alpha),
            "layer_factor_enabled": not bool(args.disable_utility_layer_factor),
            "ready_factor_enabled": not bool(args.disable_utility_ready_factor),
            "layer_factors": [float(value) for value in layer_factors.detach().cpu().tolist()],
            "ready_factors": [float(value) for value in ready_factors.detach().cpu().tolist()],
        },
        "notes": {
            "threshold_model": (
                "Threshold policies keep a global fraction of max-extra MTP candidates "
                "by MTP-token prior score, then apply priority-protected admission and "
                "the queue-aware ready mask. This is a conservative replay because queue "
                "capacity is not recomputed after threshold filtering."
            ),
            "oracle": (
                "Oracle policy keeps only MTP extras that are actually used by the true "
                "router demand, giving an upper bound for utility admission."
            ),
            "heldout": (
                "Held-out threshold policies choose score thresholds on calibration "
                "samples and report metrics on disjoint held-out samples."
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _event_metrics(
    *,
    requested: torch.Tensor,
    issued: torch.Tensor,
    ready: torch.Tensor,
    target_mass: torch.Tensor,
    bandwidth_gbps: float,
    expert_bytes: int,
    token_sample_indices: torch.Tensor | None = None,
) -> dict[str, float]:
    metrics = _policy_stall_metrics(
        ready,
        target_mass,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
    )
    metrics.update(
        _shadow_counter_metrics(
            requested_mask=requested,
            issued_mask=issued,
            ready_mask=ready,
            target_mass=target_mass,
            expert_bytes=expert_bytes,
            token_sample_indices=token_sample_indices,
        )
    )
    return metrics


def _extra_only_metrics(
    *,
    requested: torch.Tensor,
    issued: torch.Tensor,
    ready: torch.Tensor,
    target_mass: torch.Tensor,
    bandwidth_gbps: float,
    expert_bytes: int,
    token_sample_indices: torch.Tensor | None = None,
) -> dict[str, float]:
    metrics = _event_metrics(
        requested=requested,
        issued=issued,
        ready=ready,
        target_mass=target_mass,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
        token_sample_indices=token_sample_indices,
    )
    metrics["saved_supplemental_fetch_count"] = metrics["used_count"]
    metrics["saved_supplemental_fetch_bytes"] = metrics["used_bytes"]
    metrics["saved_supplemental_stall_ms"] = float(
        metrics["used_count"] * metrics["per_expert_supplemental_fetch_ms"]
    )
    metrics["saved_supplemental_bytes_per_issued_byte"] = float(
        metrics["used_bytes"] / max(1.0, metrics["issued_bytes"])
    )
    metrics["stall_saved_ms_per_issued_gb"] = float(
        metrics["saved_supplemental_stall_ms"]
        / max(1e-12, metrics["issued_bytes"] / 1_000_000_000.0)
    )
    return metrics


def _decision_reason_counters(
    decisions,
    *,
    expert_bytes: int,
) -> dict[str, dict[str, float]]:
    counters = {}
    for reason, mask in decisions.reason_masks().items():
        count = float(mask.float().sum().item())
        counters[reason] = {
            "count": count,
            "bytes": float(count * int(expert_bytes)),
        }
    return counters


def _evaluate_tail_swap_policies(
    *,
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    admission: torch.Tensor,
    ready_raw: torch.Tensor,
    token_sample_indices: torch.Tensor,
    base_metrics: dict[str, float],
    transition_topk: int,
    mtp_topk: int,
    swap_counts: list[int],
    bandwidth_gbps: float,
    expert_bytes: int,
) -> dict[str, dict[str, float]]:
    policies = {}
    for swap_count in sorted({int(value) for value in swap_counts if int(value) > 0}):
        mask = tail_swap_mtp_extra_mask(
            transition_scores,
            mtp_scores,
            transition_topk=transition_topk,
            mtp_topk=mtp_topk,
            swap_count=swap_count,
        )
        issued = mask & admission
        ready = ready_raw & issued
        metrics = _event_metrics(
            requested=mask,
            issued=issued,
            ready=ready,
            target_mass=target_mass,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
            token_sample_indices=token_sample_indices,
        )
        _add_delta_metrics(metrics, base_metrics, expert_bytes=expert_bytes)
        metrics["swap_count"] = float(swap_count)
        metrics["protected_transition_head"] = float(max(0, transition_topk - swap_count))
        policies[f"tail_swap_{swap_count}"] = metrics
    return policies


def _evaluate_score_threshold_policies(
    *,
    base: torch.Tensor,
    score_tensor: torch.Tensor,
    target_mass: torch.Tensor,
    admission: torch.Tensor,
    ready_raw: torch.Tensor,
    token_sample_indices: torch.Tensor,
    base_metrics: dict[str, float],
    mtp_topk: int,
    max_extra: int,
    keep_fractions: list[float],
    bandwidth_gbps: float,
    expert_bytes: int,
    metadata_context: dict[str, object],
    threshold_type: str,
    calibration_split: str,
    heldout_split: str,
    notes: str,
) -> dict[str, dict[str, object]]:
    extra_all = novel_mtp_extra_mask(
        base,
        score_tensor,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    candidate_scores = _finite_candidate_scores(score_tensor[extra_all])
    policies = {}
    for keep_fraction in keep_fractions:
        keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
        if keep_fraction <= 0.0 or candidate_scores.numel() == 0:
            score_threshold = float("inf")
        elif keep_fraction >= 1.0:
            score_threshold = float(candidate_scores.min().item())
        else:
            score_threshold = float(
                torch.quantile(candidate_scores.float(), 1.0 - keep_fraction).item()
            )
        decisions = score_threshold_mtp_extra_decision_masks(
            base,
            score_tensor,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            score_threshold=score_threshold,
        )
        extra = decisions.admitted_full_fetch
        requested = base | extra
        issued = requested & admission
        ready = ready_raw & issued
        metrics = _event_metrics(
            requested=requested,
            issued=issued,
            ready=ready,
            target_mass=target_mass,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
            token_sample_indices=token_sample_indices,
        )
        _add_delta_metrics(metrics, base_metrics, expert_bytes=expert_bytes)
        metrics["score_threshold"] = float(score_threshold)
        metrics["admission_reason_counters"] = _decision_reason_counters(
            decisions,
            expert_bytes=expert_bytes,
        )
        metrics["score_threshold_metadata"] = ScoreThresholdMetadata(
            threshold=float(score_threshold),
            threshold_type=threshold_type,
            optimization_goal="stall_reduction",
            target_budget=f"keep_top_{keep_fraction:.3f}",
            metric="stall_saved_ms_per_extra_issued_gb",
            calibration_split=calibration_split,
            heldout_split=heldout_split,
            notes=notes,
            **metadata_context,
        ).as_dict()
        metrics["keep_fraction"] = float(keep_fraction)
        metrics["requested_extra_count"] = float(extra.float().sum().item())
        policies[f"keep_top_{keep_fraction:.3f}"] = metrics
    return policies


def _evaluate_heldout_thresholds(
    *,
    transition_scores: torch.Tensor,
    utility_scores: torch.Tensor,
    base: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    admission: torch.Tensor,
    ready_raw: torch.Tensor,
    calibration_rows: torch.Tensor,
    heldout_rows: torch.Tensor,
    token_sample_indices: torch.Tensor,
    transition_topk: int,
    mtp_topk: int,
    max_extra: int,
    keep_fractions: list[float],
    bandwidth_gbps: float,
    expert_bytes: int,
    metadata_context: dict[str, object],
) -> dict[str, object]:
    base_h = base[heldout_rows]
    transition_h = transition_scores[heldout_rows]
    utility_h = utility_scores[heldout_rows]
    admission_h = admission[heldout_rows]
    ready_raw_h = ready_raw[heldout_rows]
    target_h = target_mass[heldout_rows]
    sample_h = token_sample_indices[heldout_rows]
    base_metrics = _event_metrics(
        requested=base_h,
        issued=base_h & admission_h,
        ready=ready_raw_h & base_h & admission_h,
        target_mass=target_h,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
        token_sample_indices=sample_h,
    )

    extra_all = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    calibration_scores = mtp_scores[calibration_rows][extra_all[calibration_rows]]
    utility_calibration_scores = utility_scores[calibration_rows][extra_all[calibration_rows]]
    extra_all_h = extra_all[heldout_rows]
    mtp_scores_h = mtp_scores[heldout_rows]

    fixed = {}
    fixed_extras = sorted({1, 2, 4, max_extra})
    for extra_count in fixed_extras:
        extra = novel_mtp_extra_mask(
            base_h,
            mtp_scores_h,
            mtp_topk=mtp_topk,
            max_extra=extra_count,
        )
        requested = base_h | extra
        issued = requested & admission_h
        ready = ready_raw_h & issued
        metrics = _event_metrics(
            requested=requested,
            issued=issued,
            ready=ready,
            target_mass=target_h,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
            token_sample_indices=sample_h,
        )
        _add_delta_metrics(metrics, base_metrics, expert_bytes=expert_bytes)
        metrics["max_extra"] = float(extra_count)
        fixed[f"fixed_extra{extra_count}"] = metrics

    threshold = {}
    for keep_fraction in keep_fractions:
        keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
        if keep_fraction <= 0.0 or calibration_scores.numel() == 0:
            score_threshold = float("inf")
            extra = torch.zeros_like(extra_all_h)
        elif keep_fraction >= 1.0:
            score_threshold = -float("inf")
        else:
            score_threshold = float(
                torch.quantile(calibration_scores.float(), 1.0 - keep_fraction).item()
            )
        decisions = score_threshold_mtp_extra_decision_masks(
            base_h,
            mtp_scores_h,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            score_threshold=score_threshold,
        )
        extra = decisions.admitted_full_fetch
        requested = base_h | extra
        issued = requested & admission_h
        ready = ready_raw_h & issued
        metrics = _event_metrics(
            requested=requested,
            issued=issued,
            ready=ready,
            target_mass=target_h,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
            token_sample_indices=sample_h,
        )
        _add_delta_metrics(metrics, base_metrics, expert_bytes=expert_bytes)
        metrics["score_threshold"] = float(score_threshold)
        metrics["admission_reason_counters"] = _decision_reason_counters(
            decisions,
            expert_bytes=expert_bytes,
        )
        metrics["score_threshold_metadata"] = ScoreThresholdMetadata(
            threshold=float(score_threshold),
            threshold_type="calibrated_absolute",
            optimization_goal="stall_reduction",
            target_budget=f"keep_top_{keep_fraction:.3f}",
            metric="stall_saved_ms_per_extra_issued_gb",
            calibration_split="calibration_sample_ids",
            heldout_split="heldout_sample_ids",
            notes="Threshold selected from calibration MTP extra scores and evaluated on held-out samples.",
            **metadata_context,
        ).as_dict()
        metrics["keep_fraction"] = float(keep_fraction)
        metrics["requested_extra_count"] = float(extra.float().sum().item())
        threshold[f"keep_top_{keep_fraction:.3f}"] = metrics

    utility_threshold = _evaluate_heldout_score_threshold_policies(
        base_h=base_h,
        score_h=utility_h,
        target_h=target_h,
        admission_h=admission_h,
        ready_raw_h=ready_raw_h,
        sample_h=sample_h,
        base_metrics=base_metrics,
        calibration_scores=utility_calibration_scores,
        mtp_topk=mtp_topk,
        max_extra=max_extra,
        keep_fractions=keep_fractions,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
        metadata_context={
            **metadata_context,
            "score_source": "mtp_token_prior_rank_layer_ready_utility_score",
        },
    )

    tail_swap = _evaluate_tail_swap_policies(
        transition_scores=transition_h,
        mtp_scores=mtp_scores_h,
        target_mass=target_h,
        admission=admission_h,
        ready_raw=ready_raw_h,
        token_sample_indices=sample_h,
        base_metrics=base_metrics,
        transition_topk=transition_topk,
        mtp_topk=mtp_topk,
        swap_counts=[1, 2, 4, max_extra],
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
    )

    oracle_extra = extra_all_h & target_h.gt(0.0)
    oracle_requested = base_h | oracle_extra
    oracle_issued = oracle_requested & admission_h
    oracle_ready = ready_raw_h & oracle_issued
    oracle = _event_metrics(
        requested=oracle_requested,
        issued=oracle_issued,
        ready=oracle_ready,
        target_mass=target_h,
        bandwidth_gbps=bandwidth_gbps,
        expert_bytes=expert_bytes,
        token_sample_indices=sample_h,
    )
    _add_delta_metrics(oracle, base_metrics, expert_bytes=expert_bytes)
    return {
        "transition": base_metrics,
        "fixed_rank_policies": fixed,
        "score_threshold_policies": threshold,
        "utility_threshold_policies": utility_threshold,
        "tail_swap_policies": tail_swap,
        "oracle_used_extra_policy": oracle,
        "same_issued_byte_comparison": _same_issued_byte_comparison(fixed, threshold),
    }


def _same_issued_byte_comparison(
    fixed: dict[str, dict[str, float]],
    threshold: dict[str, dict[str, float]],
) -> dict[str, dict[str, float | str]]:
    result: dict[str, dict[str, float | str]] = {}
    threshold_items = list(threshold.items())
    for fixed_name, fixed_metrics in fixed.items():
        fixed_extra = fixed_metrics.get("delta_issued_bytes_vs_transition", 0.0)
        closest_name, closest_metrics = min(
            threshold_items,
            key=lambda item: abs(
                item[1].get("delta_issued_bytes_vs_transition", 0.0) - fixed_extra
            ),
        )
        result[fixed_name] = {
            "closest_threshold_policy": closest_name,
            "fixed_extra_issued_gb": float(fixed_extra / 1_000_000_000.0),
            "threshold_extra_issued_gb": float(
                closest_metrics.get("delta_issued_bytes_vs_transition", 0.0)
                / 1_000_000_000.0
            ),
            "fixed_stall_reduction": float(
                fixed_metrics.get("stall_reduction_ratio_vs_transition", 0.0)
            ),
            "threshold_stall_reduction": float(
                closest_metrics.get("stall_reduction_ratio_vs_transition", 0.0)
            ),
            "delta_stall_reduction": float(
                closest_metrics.get("stall_reduction_ratio_vs_transition", 0.0)
                - fixed_metrics.get("stall_reduction_ratio_vs_transition", 0.0)
            ),
        }
    return result


def _evaluate_heldout_score_threshold_policies(
    *,
    base_h: torch.Tensor,
    score_h: torch.Tensor,
    target_h: torch.Tensor,
    admission_h: torch.Tensor,
    ready_raw_h: torch.Tensor,
    sample_h: torch.Tensor,
    base_metrics: dict[str, float],
    calibration_scores: torch.Tensor,
    mtp_topk: int,
    max_extra: int,
    keep_fractions: list[float],
    bandwidth_gbps: float,
    expert_bytes: int,
    metadata_context: dict[str, object],
) -> dict[str, dict[str, object]]:
    calibration_scores = _finite_candidate_scores(calibration_scores)
    threshold = {}
    for keep_fraction in keep_fractions:
        keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
        if keep_fraction <= 0.0 or calibration_scores.numel() == 0:
            score_threshold = float("inf")
        elif keep_fraction >= 1.0:
            score_threshold = float(calibration_scores.min().item())
        else:
            score_threshold = float(
                torch.quantile(calibration_scores.float(), 1.0 - keep_fraction).item()
            )
        decisions = score_threshold_mtp_extra_decision_masks(
            base_h,
            score_h,
            mtp_topk=mtp_topk,
            max_extra=max_extra,
            score_threshold=score_threshold,
        )
        extra = decisions.admitted_full_fetch
        requested = base_h | extra
        issued = requested & admission_h
        ready = ready_raw_h & issued
        metrics = _event_metrics(
            requested=requested,
            issued=issued,
            ready=ready,
            target_mass=target_h,
            bandwidth_gbps=bandwidth_gbps,
            expert_bytes=expert_bytes,
            token_sample_indices=sample_h,
        )
        _add_delta_metrics(metrics, base_metrics, expert_bytes=expert_bytes)
        metrics["score_threshold"] = float(score_threshold)
        metrics["admission_reason_counters"] = _decision_reason_counters(
            decisions,
            expert_bytes=expert_bytes,
        )
        metrics["score_threshold_metadata"] = ScoreThresholdMetadata(
            threshold=float(score_threshold),
            threshold_type="calibrated_absolute",
            optimization_goal="stall_reduction",
            target_budget=f"keep_top_{keep_fraction:.3f}",
            metric="stall_saved_ms_per_extra_issued_gb",
            calibration_split="calibration_sample_ids",
            heldout_split="heldout_sample_ids",
            notes=(
                "Utility threshold selected from calibration MTP utility scores and "
                "evaluated on held-out samples."
            ),
            **metadata_context,
        ).as_dict()
        metrics["keep_fraction"] = float(keep_fraction)
        metrics["requested_extra_count"] = float(extra.float().sum().item())
        threshold[f"keep_top_{keep_fraction:.3f}"] = metrics
    return threshold


def _calibration_heldout_rows(
    token_sample_indices: torch.Tensor,
    *,
    fraction: float,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, object]]:
    sample_ids = torch.unique(token_sample_indices.to(torch.long).cpu(), sorted=True)
    if int(sample_ids.numel()) < 2:
        rows = torch.ones_like(token_sample_indices, dtype=torch.bool)
        return rows, rows, {
            "calibration_sample_ids": [int(value) for value in sample_ids.tolist()],
            "heldout_sample_ids": [int(value) for value in sample_ids.tolist()],
            "fraction": 1.0,
        }
    fraction = min(max(float(fraction), 0.05), 0.95)
    calibration_count = int(round(float(sample_ids.numel()) * fraction))
    calibration_count = min(int(sample_ids.numel()) - 1, max(1, calibration_count))
    calibration_ids = sample_ids[:calibration_count]
    heldout_ids = sample_ids[calibration_count:]
    calibration_rows = _rows_for_sample_ids(token_sample_indices, calibration_ids)
    heldout_rows = _rows_for_sample_ids(token_sample_indices, heldout_ids)
    return calibration_rows, heldout_rows, {
        "calibration_sample_ids": [int(value) for value in calibration_ids.tolist()],
        "heldout_sample_ids": [int(value) for value in heldout_ids.tolist()],
        "fraction": fraction,
        "num_calibration_token_examples": int(calibration_rows.long().sum().item()),
        "num_heldout_token_examples": int(heldout_rows.long().sum().item()),
    }


def _calibrated_layer_factors(
    base: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    *,
    rows: torch.Tensor,
    mtp_topk: int,
    max_extra: int,
) -> torch.Tensor:
    extra = novel_mtp_extra_mask(
        base[rows],
        mtp_scores[rows],
        mtp_topk=mtp_topk,
        max_extra=max_extra,
    )
    target = target_mass[rows]
    count_by_layer = extra.float().sum(dim=(0, 1, 3)).clamp_min(1.0)
    gain_by_layer = (extra.float() * target).sum(dim=(0, 1, 3)) / count_by_layer
    positive = gain_by_layer[gain_by_layer.gt(0.0)]
    if positive.numel() == 0:
        return torch.ones_like(gain_by_layer)
    normalized = gain_by_layer / positive.mean().clamp_min(1e-12)
    return normalized.clamp(0.5, 1.5)


def _ready_layer_factors(
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
        return torch.ones(num_layers, device=device)
    bytes_per_ms = float(bandwidth_gbps) * 1_000_000_000.0 / 1000.0
    factors = []
    for layer_idx in range(int(num_layers)):
        lead_ms = max(
            0.0,
            float(layer_idx) * float(layer_ms)
            + float(sampling_ms)
            - float(mtp_delay_ms),
        )
        fetch_capacity = lead_ms * bytes_per_ms / max(1.0, float(expert_bytes))
        factors.append(min(1.0, fetch_capacity / float(max_extra)))
    return torch.tensor(factors, dtype=torch.float32, device=device)


def _finite_candidate_scores(scores: torch.Tensor) -> torch.Tensor:
    scores = scores.float()
    return scores[torch.isfinite(scores)]


def _threshold_metadata_context(
    *,
    config: dict[str, object],
    merged_manifest: Path,
    mtp_token_manifest: Path,
    output: Path,
    num_samples: int,
    target_mass: torch.Tensor,
    mtp_topm_ids: torch.Tensor,
    transition_topk: int,
    mtp_topk: int,
    max_extra: int,
) -> dict[str, object]:
    token_examples = int(target_mass.shape[0])
    future = int(target_mass.shape[1]) if target_mass.ndim >= 2 else 1
    layers = int(target_mass.shape[2]) if target_mass.ndim >= 3 else None
    experts = int(target_mass.shape[3]) if target_mass.ndim >= 4 else None
    top_m_tokens = int(mtp_topm_ids.shape[-1]) if mtp_topm_ids.ndim > 0 else None
    prefc_fixed = "prefc_fixed" in str(merged_manifest) or "prefc_fixed" in str(
        mtp_token_manifest
    )
    return {
        "model_id": str(config.get("model_id")) if config.get("model_id") is not None else None,
        "trace_id": str(merged_manifest),
        "sidecar_model_id": (
            str(config.get("sidecar_model_id"))
            if config.get("sidecar_model_id") is not None
            else None
        ),
        "router_trace_model_id": (
            str(config.get("router_trace_model_id"))
            if config.get("router_trace_model_id") is not None
            else None
        ),
        "prefc_fixed": bool(prefc_fixed),
        "num_samples": int(num_samples),
        "num_tokens": token_examples,
        "num_token_layer_examples": int(token_examples * future * layers)
        if layers is not None
        else None,
        "num_layers": layers,
        "num_experts": experts,
        "top_m_tokens": top_m_tokens,
        "base_policy": f"transition_top{transition_topk}",
        "max_extra": int(max_extra),
        "score_source": f"mtp_token_top{mtp_topk}_prior_score",
        "calibration_report_path": str(output),
        "heldout_report_path": str(output),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": output.stem,
    }


def _rows_for_sample_ids(
    token_sample_indices: torch.Tensor,
    sample_ids: torch.Tensor,
) -> torch.Tensor:
    rows = torch.zeros_like(token_sample_indices, dtype=torch.bool)
    for sample_id in sample_ids.tolist():
        rows |= token_sample_indices.to(torch.long).eq(int(sample_id))
    return rows


def _add_delta_metrics(
    metrics: dict[str, float],
    base_metrics: dict[str, float],
    *,
    expert_bytes: int,
) -> None:
    metrics["saved_supplemental_fetch_count_vs_transition"] = float(
        base_metrics["supplemental_fetch_count"] - metrics["supplemental_fetch_count"]
    )
    metrics["saved_supplemental_fetch_bytes_vs_transition"] = float(
        metrics["saved_supplemental_fetch_count_vs_transition"] * float(expert_bytes)
    )
    metrics["saved_supplemental_stall_ms_vs_transition"] = float(
        base_metrics["supplemental_stall_ms_sum"] - metrics["supplemental_stall_ms_sum"]
    )
    metrics["stall_reduction_ratio_vs_transition"] = float(
        metrics["saved_supplemental_stall_ms_vs_transition"]
        / max(1e-12, base_metrics["supplemental_stall_ms_sum"])
    )
    delta_issued = metrics["issued_bytes"] - base_metrics["issued_bytes"]
    metrics["delta_issued_bytes_vs_transition"] = float(delta_issued)
    metrics["delta_used_bytes_vs_transition"] = float(
        metrics["used_bytes"] - base_metrics["used_bytes"]
    )
    metrics["delta_unused_bytes_vs_transition"] = float(
        metrics["unused_bytes"] - base_metrics["unused_bytes"]
    )
    metrics["saved_supplemental_bytes_per_extra_issued_byte"] = float(
        metrics["saved_supplemental_fetch_bytes_vs_transition"] / max(1.0, delta_issued)
    )
    metrics["delta_used_bytes_per_extra_issued_byte"] = float(
        metrics["delta_used_bytes_vs_transition"] / max(1.0, delta_issued)
    )
    metrics["delta_unused_bytes_per_extra_issued_byte"] = float(
        metrics["delta_unused_bytes_vs_transition"] / max(1.0, delta_issued)
    )
    metrics["stall_saved_ms_per_extra_issued_gb"] = float(
        metrics["saved_supplemental_stall_ms_vs_transition"]
        / max(1e-12, delta_issued / 1_000_000_000.0)
    )


if __name__ == "__main__":
    main()
