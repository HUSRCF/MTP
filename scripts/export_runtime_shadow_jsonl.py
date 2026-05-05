#!/usr/bin/env python
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    _calibrated_layer_factors,
    _threshold_from_keep_fraction,
    queue_aware_ready_mask,
    topk_mask,
)
from mtp_expert_prefetch.runtime import (  # noqa: E402
    RuntimeSignals,
    ShadowPolicyConfig,
    add_metadata_budget_decisions,
    add_premap_budget_decisions,
    aggregate_shadow_events,
    aggregate_shadow_tensors,
    build_mtp_extra_utility_scores,
    iter_shadow_summary_outcome_events,
    score_threshold_mtp_extra_decision_masks,
    select_runtime_prefetch_policy,
)
from mtp_expert_prefetch.utils.config import find_project_root, resolve_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export runtime-style shadow summary/outcome JSONL from cached tensors."
    )
    parser.add_argument(
        "--tensor-cache",
        type=Path,
        required=True,
        help="Tensor cache written by simulate_prefetch_event_stalls.py.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL path.")
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=None,
        help="Optional aggregate JSON report path. Defaults to <output>.summary.json.",
    )
    parser.add_argument("--request-id", default="offline-replay")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Skip JSONL emission and compute aggregate counters with vectorized tensors.",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--transition-topk", type=int, default=32)
    parser.add_argument("--mtp-topk", type=int, default=64)
    parser.add_argument("--full-fetch-max-extra", type=int, default=4)
    parser.add_argument("--metadata-max-extra", type=int, default=1)
    parser.add_argument("--premap-max-extra", type=int, default=1)
    parser.add_argument(
        "--optimization-goal",
        choices=["stall_reduction", "bandwidth_efficiency"],
        default="stall_reduction",
    )
    parser.add_argument("--action-keep-fraction", type=float, default=0.5)
    parser.add_argument("--metadata-score-ratio", type=float, default=0.95)
    parser.add_argument("--utility-rank-alpha", type=float, default=1.0)
    parser.add_argument("--disable-layer-factor", action="store_true")
    parser.add_argument("--disable-ready-factor", action="store_true")
    parser.add_argument("--bandwidth-gbps", type=float, default=6.589)
    parser.add_argument("--layer-ms", type=float, default=1.0)
    parser.add_argument("--sampling-ms", type=float, default=0.0)
    parser.add_argument("--mtp-delay-ms", type=float, default=2.0)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--metadata-bytes", type=int, default=65_536)
    parser.add_argument("--premap-bytes", type=int, default=4_096)
    parser.add_argument("--cache-pressure", type=float, default=0.40)
    parser.add_argument("--queue-pressure", type=float, default=0.40)
    parser.add_argument("--effective-capacity", type=int, default=160)
    parser.add_argument(
        "--max-token-examples",
        type=int,
        default=None,
        help="Optional prefix of eval token examples to export for smoke logs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = find_project_root(args.tensor_cache)
    tensor_cache = resolve_path(args.tensor_cache, base_dir=project_root)
    output = resolve_path(args.output, base_dir=project_root)
    summary_output = (
        resolve_path(args.summary_output, base_dir=project_root)
        if args.summary_output is not None
        else output.with_suffix(output.suffix + ".summary.json")
    )
    device = _resolve_device(args.device)
    cache = torch.load(tensor_cache, map_location="cpu")
    tensors = _load_cached_tensors(cache, device=device, max_token_examples=args.max_token_examples)

    train_base = topk_mask(tensors["train_transition_scores"], k=int(args.transition_topk))
    candidate_start = time.perf_counter()
    eval_base = topk_mask(tensors["transition_scores"], k=int(args.transition_topk))
    candidate_elapsed = time.perf_counter() - candidate_start
    ready_factors = (
        _ready_layer_factors(
            num_layers=int(tensors["target_mass"].shape[2]),
            layer_ms=float(args.layer_ms),
            sampling_ms=float(args.sampling_ms),
            mtp_delay_ms=float(args.mtp_delay_ms),
            bandwidth_gbps=float(args.bandwidth_gbps),
            expert_bytes=int(args.expert_bytes),
            max_extra=int(args.full_fetch_max_extra),
            device=device,
        )
        if not bool(args.disable_ready_factor)
        else torch.ones(int(tensors["target_mass"].shape[2]), device=device)
    )
    layer_factors = (
        _calibrated_layer_factors(
            train_base.cpu(),
            tensors["train_mtp_scores"].cpu(),
            tensors["train_target_mass"].cpu(),
            mtp_topk=int(args.mtp_topk),
            max_extra=int(args.full_fetch_max_extra),
        ).to(device)
        if not bool(args.disable_layer_factor)
        else torch.ones(int(tensors["target_mass"].shape[2]), device=device)
    )
    train_utility = build_mtp_extra_utility_scores(
        train_base,
        tensors["train_mtp_scores"],
        mtp_topk=int(args.mtp_topk),
        rank_alpha=float(args.utility_rank_alpha),
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )
    eval_utility = build_mtp_extra_utility_scores(
        eval_base,
        tensors["mtp_scores"],
        mtp_topk=int(args.mtp_topk),
        rank_alpha=float(args.utility_rank_alpha),
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )
    full_threshold = _threshold_from_keep_fraction(
        train_base.cpu(),
        tensors["train_mtp_scores"].cpu(),
        train_utility.cpu(),
        mtp_topk=int(args.mtp_topk),
        max_extra=int(args.full_fetch_max_extra),
        keep_fraction=float(args.action_keep_fraction),
    )
    raw_threshold = _threshold_from_keep_fraction(
        train_base.cpu(),
        tensors["train_mtp_scores"].cpu(),
        tensors["train_mtp_scores"].cpu(),
        mtp_topk=int(args.mtp_topk),
        max_extra=int(args.full_fetch_max_extra),
        keep_fraction=float(args.action_keep_fraction),
    )
    _, ready_stats = queue_aware_ready_mask(
        tensors["transition_scores"].cpu(),
        tensors["mtp_scores"].cpu(),
        transition_topk=int(args.transition_topk),
        mtp_topk=int(args.mtp_topk),
        max_extra=int(args.full_fetch_max_extra),
        num_layers=int(tensors["target_mass"].shape[2]),
        layer_ms=float(args.layer_ms),
        sampling_ms=float(args.sampling_ms),
        mtp_delay_ms=float(args.mtp_delay_ms),
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
    )
    runtime_policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=float(ready_stats["ready_base_fraction"]),
            cache_pressure=float(args.cache_pressure),
            queue_pressure=float(args.queue_pressure),
            effective_capacity=int(args.effective_capacity),
            mtp_delay_ms=float(args.mtp_delay_ms),
            mtp_ready_fraction=float(ready_stats["ready_extra_fraction"]),
            bandwidth_gbps=float(args.bandwidth_gbps),
            layer_ms=float(args.layer_ms),
        ),
        optimization_goal=str(args.optimization_goal),
    )
    allow_full = torch.full_like(eval_base, bool(runtime_policy.allow_full_mtp_fetch))
    admission_start = time.perf_counter()
    decisions = score_threshold_mtp_extra_decision_masks(
        eval_base,
        eval_utility,
        mtp_topk=int(args.mtp_topk),
        max_extra=int(runtime_policy.max_extra),
        score_threshold=float(full_threshold),
        policy_allowed_mask=allow_full,
    )
    if bool(runtime_policy.allow_mtp_metadata) and int(runtime_policy.metadata_max_extra) > 0:
        decisions = add_metadata_budget_decisions(
            eval_base,
            full_decisions=decisions,
            metadata_scores=tensors["mtp_scores"],
            mtp_topk=int(args.mtp_topk),
            metadata_max_extra=int(runtime_policy.metadata_max_extra),
            metadata_score_threshold=float(raw_threshold) * float(args.metadata_score_ratio),
        )
    if bool(runtime_policy.allow_mtp_premap) and int(args.premap_max_extra) > 0:
        decisions = add_premap_budget_decisions(
            eval_base,
            decisions=decisions,
            premap_scores=tensors["mtp_scores"],
            mtp_topk=int(args.mtp_topk),
            premap_max_extra=int(args.premap_max_extra),
        )
    admission_elapsed = time.perf_counter() - admission_start
    summary_count = int(
        tensors["target_mass"].shape[0]
        * tensors["target_mass"].shape[1]
        * tensors["target_mass"].shape[2]
    )
    candidate_construction_us = _per_summary_us(candidate_elapsed, summary_count)
    admission_decision_us = _per_summary_us(admission_elapsed, summary_count)

    policy_config = ShadowPolicyConfig(
        policy_mode=str(runtime_policy.mode),
        optimization_goal=str(args.optimization_goal),
        action_keep_fraction=float(args.action_keep_fraction),
        metadata_score_ratio=float(args.metadata_score_ratio),
        full_fetch_max_extra=int(runtime_policy.max_extra),
        metadata_max_extra=int(runtime_policy.metadata_max_extra),
        premap_max_extra=int(args.premap_max_extra),
        threshold_metadata_id="offline_calibrated_runtime_shadow",
        policy_reason=str(runtime_policy.reason),
        allow_full_mtp_fetch=bool(runtime_policy.allow_full_mtp_fetch),
        allow_mtp_metadata=bool(runtime_policy.allow_mtp_metadata),
        allow_mtp_premap=bool(runtime_policy.allow_mtp_premap),
    )
    if bool(args.summary_only):
        counter_start = time.perf_counter()
        aggregate = aggregate_shadow_tensors(
            base_mask=eval_base,
            decisions=decisions,
            target_mass=tensors["target_mass"],
            expert_bytes=int(args.expert_bytes),
            metadata_bytes=int(args.metadata_bytes),
            premap_bytes=int(args.premap_bytes),
            candidate_construction_us=candidate_construction_us,
            admission_decision_us=admission_decision_us,
        )
        counter_elapsed = time.perf_counter() - counter_start
        counter_update_us = _per_summary_us(counter_elapsed, summary_count)
        decision_us = candidate_construction_us + admission_decision_us + counter_update_us
        aggregate["counter_update_us_sum"] = counter_update_us * summary_count
        aggregate["counter_update_us_mean"] = counter_update_us
        aggregate["decision_us_sum"] = decision_us * summary_count
        aggregate["decision_us_mean"] = decision_us
    else:
        events = iter_shadow_summary_outcome_events(
            base_mask=eval_base,
            decisions=decisions,
            target_mass=tensors["target_mass"],
            policy=policy_config,
            request_id=str(args.request_id),
            token_sample_indices=tensors.get("token_sample_indices"),
            transition_topk_count=int(args.transition_topk),
            mtp_requested_count=int(args.mtp_topk),
            expert_bytes=int(args.expert_bytes),
            metadata_bytes=int(args.metadata_bytes),
            premap_bytes=int(args.premap_bytes),
            mtp_delay_ms=float(args.mtp_delay_ms),
            transition_ready_rate=float(ready_stats["ready_base_fraction"]),
            mtp_ready_fraction=float(ready_stats["ready_extra_fraction"]),
            bandwidth_gbps=float(args.bandwidth_gbps),
            layer_ms=float(args.layer_ms),
            cache_pressure=float(args.cache_pressure),
            queue_pressure=float(args.queue_pressure),
            decision_us=candidate_construction_us + admission_decision_us,
            candidate_construction_us=candidate_construction_us,
            admission_decision_us=admission_decision_us,
        )
        aggregate = aggregate_shadow_events(_write_and_yield(events, output))
    payload = {
        "ok": True,
        "tensor_cache": str(tensor_cache),
        "output": str(output),
        "summary_only": bool(args.summary_only),
        "summary_output": str(summary_output),
        "device": str(device),
        "num_eval_token_examples": int(tensors["target_mass"].shape[0]),
        "policy": policy_config.as_dict(),
        "runtime_policy": runtime_policy.as_dict(),
        "ready_stats": ready_stats,
        "full_fetch_threshold": float(full_threshold),
        "metadata_score_threshold": float(raw_threshold) * float(args.metadata_score_ratio),
        "aggregate": aggregate,
        "overhead": {
            "candidate_construction_us_mean": candidate_construction_us,
            "admission_decision_us_mean": admission_decision_us,
            "counter_update_us_mean": float(aggregate.get("counter_update_us_mean", 0.0)),
            "decision_us_mean": float(aggregate.get("decision_us_mean", 0.0)),
        },
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _resolve_device(name: str) -> torch.device:
    if name.startswith("cuda") and not torch.cuda.is_available():
        msg = f"Requested {name}, but torch.cuda.is_available() is false."
        raise RuntimeError(msg)
    return torch.device(name)


def _load_cached_tensors(
    cache: dict[str, Any],
    *,
    device: torch.device,
    max_token_examples: int | None,
) -> dict[str, torch.Tensor]:
    tensors = {
        "train_transition_scores": cache["train_transition_scores"].to(device),
        "train_mtp_scores": cache["train_mtp_scores"].to(device),
        "train_target_mass": cache["train_target_mass"].to(device),
        "transition_scores": cache["transition_scores"].to(device),
        "mtp_scores": cache["mtp_scores"].to(device),
        "target_mass": cache["target_mass"].to(device),
    }
    if cache.get("token_sample_indices") is not None:
        tensors["token_sample_indices"] = cache["token_sample_indices"].to("cpu")
    if max_token_examples is not None:
        limit = max(0, int(max_token_examples))
        for key in ("transition_scores", "mtp_scores", "target_mass"):
            tensors[key] = tensors[key][:limit]
        if "token_sample_indices" in tensors:
            tensors["token_sample_indices"] = tensors["token_sample_indices"][:limit]
    return tensors


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
            float(layer_idx) * float(layer_ms) + float(sampling_ms) - float(mtp_delay_ms),
        )
        fetch_capacity = lead_ms * bytes_per_ms / max(1.0, float(expert_bytes))
        factors.append(min(1.0, fetch_capacity / float(max_extra)))
    return torch.tensor(factors, dtype=torch.float32, device=device)


def _write_and_yield(events: Iterable[Any], output: Path) -> Iterable[dict[str, Any]]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for event in events:
            payload = event.as_dict() if hasattr(event, "as_dict") else dict(event)
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            yield payload


def _per_summary_us(elapsed_seconds: float, summary_count: int) -> float:
    return float(elapsed_seconds) * 1_000_000.0 / max(1, int(summary_count))


if __name__ == "__main__":
    main()
