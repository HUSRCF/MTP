#!/usr/bin/env python3
"""Replay action policies through a bounded expert-payload cache manager.

This is a lab harness, not a vLLM runtime patch.  It consumes the existing
event-stall tensor cache and asks whether a policy still has positive net
benefit after payload de-duplication, bounded cache capacity, transfer cost,
and simple manager/lookup overhead are accounted for.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict, deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.evaluation.prefetch_shadow import (  # noqa: E402
    novel_mtp_extra_mask,
    topk_mask,
)
from mtp_expert_prefetch.runtime.admission import (  # noqa: E402
    build_mtp_extra_utility_scores,
)
from mtp_expert_prefetch.runtime.cache_lab_gate import (  # noqa: E402
    CacheLabGateConfig,
    CacheLabGateDecision,
    CacheLabRuntimeSignals,
    select_cache_lab_prefetch_gate,
)
from mtp_expert_prefetch.runtime.cache_manager import (  # noqa: E402
    CacheManagerEntry,
    CacheManagerSnapshot,
    ControlledExpertCacheManager,
)
from mtp_expert_prefetch.utils.config import load_yaml  # noqa: E402


@dataclass(frozen=True)
class CacheLabConfig:
    transition_topk: int
    mtp_topk: int
    gate_max_extra: int
    keep_fraction: float
    cache_capacity: int
    bandwidth_gbps: float
    expert_bytes: int
    overlap_factor: float
    manager_us_per_issue: float
    lookup_us_per_demand: float
    decision_us_per_token_layer: float
    stress_fallback: bool
    measured_copy_us_per_issue: float | None = None
    measured_copy_source: str | None = None
    measured_copy_stat: str | None = None
    measured_copy_effective_gbps: float | None = None
    measured_copy_us_per_batch: float | None = None
    measured_copy_batch_size: int = 0
    max_inflight_prefetches: int = 0
    queue_model: str = "burst"
    queue_batch_size: int = 0
    queue_coalesce_scope: str = "token_layer"
    queue_policy: str = "wait"
    queue_admission_policy: str = "prefix"
    queue_wait_us_per_overflow: float = 0.0
    queue_event_interval_us: float = 0.0
    queue_deadline_us: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tensor_cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path)
    parser.add_argument("--campaign", default=None)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--split", default=None)
    parser.add_argument("--trace-source", default=None)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument(
        "--cache-lab-gate-config",
        type=Path,
        help="Optional replay-derived envelope gate for MTP full_fetch extras.",
    )
    parser.add_argument("--cache-capacity", type=int, default=2048)
    parser.add_argument("--bandwidth-gbps", type=float, default=6.589)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--overlap-factor", type=float, default=0.8)
    parser.add_argument("--gate-max-extra", type=int, default=8)
    parser.add_argument("--keep-fraction", type=float, default=0.5)
    parser.add_argument("--manager-us-per-issue", type=float, default=0.0)
    parser.add_argument("--lookup-us-per-demand", type=float, default=0.0)
    parser.add_argument("--decision-us-per-token-layer", type=float, default=0.0)
    parser.add_argument(
        "--measured-copy-json",
        type=Path,
        help=(
            "Optional expert-transfer benchmark JSON. When present, replay uses "
            "the selected H2D row's measured latency per expert instead of the "
            "analytic bandwidth model for prefetch and demand-copy cost."
        ),
    )
    parser.add_argument(
        "--measured-copy-stat",
        choices=("mean", "p50", "p90", "p95"),
        default="p95",
    )
    parser.add_argument("--measured-copy-experts", type=int, default=1)
    parser.add_argument(
        "--measured-copy-pinned",
        choices=("true", "false", "any"),
        default="true",
    )
    parser.add_argument(
        "--max-inflight-prefetches",
        type=int,
        default=0,
        help=(
            "Optional per token/layer issue-burst in-flight limit. 0 disables "
            "queue-pressure accounting. This is a per-token-layer burst "
            "overflow approximation, not a real async DMA scheduler simulation."
        ),
    )
    parser.add_argument(
        "--queue-batch-size",
        type=int,
        default=0,
        help=(
            "Optional coalesced H2D batch size in expert payloads. 0 keeps "
            "per-issue copy accounting."
        ),
    )
    parser.add_argument(
        "--queue-model",
        choices=("burst", "event"),
        default="burst",
        help=(
            "burst: legacy aggregate overflow approximation. event: small "
            "event-driven batch queue with virtual service time, deadline "
            "flush, and cross-event coalescing."
        ),
    )
    parser.add_argument(
        "--queue-policy",
        choices=("wait", "drop"),
        default="wait",
        help=(
            "For --queue-model burst, wait admits all requested prefetches and "
            "adds burst-overflow wait; drop skips overflow prefetches. For "
            "--queue-model event, wait admits all requested prefetches into the "
            "virtual DMA queue; drop clips each token/layer burst before queueing."
        ),
    )
    parser.add_argument(
        "--queue-admission-policy",
        choices=("prefix", "score", "protected_score"),
        default="prefix",
        help=(
            "Admission order used when --queue-policy drop clips an issue burst. "
            "prefix keeps the existing expert order; score keeps the highest "
            "policy-priority experts within the burst; protected_score keeps "
            "the transition baseline prefix first and uses scores only for the "
            "remaining extra slots."
        ),
    )
    parser.add_argument(
        "--queue-event-interval-us",
        type=float,
        default=0.0,
        help=(
            "Logical inter-arrival interval between token/layer issue events "
            "for --queue-model event. 0 makes all issue events immediately "
            "available to the virtual queue."
        ),
    )
    parser.add_argument(
        "--queue-deadline-us",
        type=float,
        default=0.0,
        help=(
            "Optional event-driven coalescing deadline. Pending partial batches "
            "flush after this many us from their first payload. 0 flushes "
            "remaining partial batches at the final arrival."
        ),
    )
    parser.add_argument(
        "--queue-coalesce-scope",
        choices=("token_layer", "global"),
        default="token_layer",
        help=(
            "token_layer: each token/layer issue burst forms batches. global: "
            "coalesce all issued payloads into full batches as an optimistic "
            "lower-bound for a smarter fetch manager."
        ),
    )
    parser.add_argument(
        "--queue-wait-us-per-overflow",
        type=float,
        default=None,
        help=(
            "Optional queue wait penalty per overflowed issue. Defaults to the "
            "measured copy us/issue when --measured-copy-json is used, else 0. "
            "Only the burst queue model uses this as a cost term; the event "
            "model reports overflow pressure separately and charges queue wait "
            "from the virtual service timeline."
        ),
    )
    parser.add_argument(
        "--stress-fallback",
        action="store_true",
        help="Disable gated MTP full_fetch payloads and report shutdown counts.",
    )
    parser.add_argument(
        "--max-token-examples",
        type=int,
        default=None,
        help="Optional smoke/debug cap over eval token examples.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache = torch.load(args.tensor_cache, map_location="cpu")
    transition_scores = _maybe_limit(cache["transition_scores"], args.max_token_examples)
    mtp_scores = _maybe_limit(cache["mtp_scores"], args.max_token_examples)
    target_mass = _maybe_limit(cache["target_mass"], args.max_token_examples)
    train_transition_scores = cache["train_transition_scores"]
    train_mtp_scores = cache["train_mtp_scores"]
    train_target_mass = cache["train_target_mass"]
    measured_copy = load_measured_copy_envelope(
        args.measured_copy_json,
        stat=str(args.measured_copy_stat),
        experts=int(args.measured_copy_experts),
        pinned=str(args.measured_copy_pinned),
    )
    queue_wait_us_per_overflow = (
        float(args.queue_wait_us_per_overflow)
        if args.queue_wait_us_per_overflow is not None
        else (
            float(measured_copy["copy_us_per_issue"])
            if measured_copy is not None
            else 0.0
        )
    )

    config = CacheLabConfig(
        transition_topk=int(cache.get("transition_topk", 32)),
        mtp_topk=int(cache.get("mtp_topk", 64)),
        gate_max_extra=int(args.gate_max_extra),
        keep_fraction=float(args.keep_fraction),
        cache_capacity=int(args.cache_capacity),
        bandwidth_gbps=float(args.bandwidth_gbps),
        expert_bytes=int(args.expert_bytes),
        overlap_factor=float(args.overlap_factor),
        manager_us_per_issue=float(args.manager_us_per_issue),
        lookup_us_per_demand=float(args.lookup_us_per_demand),
        decision_us_per_token_layer=float(args.decision_us_per_token_layer),
        stress_fallback=bool(args.stress_fallback),
        measured_copy_us_per_issue=(
            None if measured_copy is None else float(measured_copy["copy_us_per_issue"])
        ),
        measured_copy_source=(
            None if measured_copy is None else str(measured_copy["source"])
        ),
        measured_copy_stat=(
            None if measured_copy is None else str(measured_copy["stat"])
        ),
        measured_copy_effective_gbps=(
            None if measured_copy is None else float(measured_copy["effective_gbps"])
        ),
        measured_copy_us_per_batch=(
            None if measured_copy is None else float(measured_copy["copy_us_per_batch"])
        ),
        measured_copy_batch_size=(
            0 if measured_copy is None else int(measured_copy["selected_experts"])
        ),
        max_inflight_prefetches=int(args.max_inflight_prefetches),
        queue_model=str(args.queue_model),
        queue_batch_size=int(args.queue_batch_size),
        queue_coalesce_scope=(
            "global"
            if str(args.queue_model) == "event"
            else str(args.queue_coalesce_scope)
        ),
        queue_policy=str(args.queue_policy),
        queue_admission_policy=str(args.queue_admission_policy),
        queue_wait_us_per_overflow=queue_wait_us_per_overflow,
        queue_event_interval_us=float(args.queue_event_interval_us),
        queue_deadline_us=float(args.queue_deadline_us),
    )
    gate_decision = build_cache_lab_gate_decision(
        args.cache_lab_gate_config,
        config=config,
    )

    policies, stress_shutdown_counts = build_policy_masks(
        train_transition_scores=train_transition_scores,
        train_mtp_scores=train_mtp_scores,
        train_target_mass=train_target_mass,
        transition_scores=transition_scores,
        mtp_scores=mtp_scores,
        target_mass=target_mass,
        config=config,
    )
    priority_scores = build_policy_priority_scores(
        train_transition_scores=train_transition_scores,
        train_mtp_scores=train_mtp_scores,
        train_target_mass=train_target_mass,
        transition_scores=transition_scores,
        mtp_scores=mtp_scores,
        config=config,
    )
    apply_cache_lab_gate_to_policies(
        policies,
        stress_shutdown_counts,
        gate_decision=gate_decision,
        config=config,
    )
    demand_indices = demand_stream_indices(target_mass)
    true_router_indices = true_router_stream_indices(target_mass)
    rows = []
    base_policy = f"transition_top{config.transition_topk}"
    base_mask = policies.get(base_policy)
    base_scores = priority_scores.get(base_policy)
    for policy, mask in policies.items():
        protected_mask = (
            base_mask
            if (
                base_mask is not None
                and (policy == base_policy or policy.startswith(base_policy + "_plus_"))
            )
            else None
        )
        rows.append(
            replay_policy(
                policy,
                mask,
                target_mass=target_mass,
                demand_indices=demand_indices,
                config=config,
                stress_shutdown_count=stress_shutdown_counts.get(policy, 0),
                priority_scores=priority_scores.get(policy),
                protected_mask=protected_mask,
                protected_priority_scores=base_scores,
            )
        )
    by_policy = {row["policy"]: row for row in rows}
    _add_delta_rows(rows, baseline=f"transition_top{config.transition_topk}")

    payload = {
        "ok": True,
        "boundary": (
            "Lab cache-manager replay only; not endpoint TPOT and not a real "
            "vLLM cache-manager implementation."
        ),
        "tensor_cache": str(args.tensor_cache),
        "tensor_cache_sha256": sha256_file(args.tensor_cache),
        "metadata": {
            "campaign": args.campaign,
            "dataset": args.dataset,
            "split": args.split,
            "trace_source": args.trace_source,
            "run_tag": args.run_tag,
            "max_token_examples": args.max_token_examples,
        },
        "config": config.__dict__,
        "shape": {
            "token_examples": int(target_mass.shape[0]),
            "future_window": int(target_mass.shape[1]),
            "layers": int(target_mass.shape[2]),
            "experts": int(target_mass.shape[3]),
        },
        "demand_stream_hash": hash_demand_stream(demand_indices),
        "true_router_stream_hash": hash_demand_stream(true_router_indices),
        "stream_contract": {
            "demand_stream_scope": "current_demand_future_window_0",
            "demand_stream_columns": ["token_idx", "layer_idx", "expert_idx"],
            "true_router_stream_scope": "all_future_windows",
            "true_router_stream_columns": [
                "token_idx",
                "future_window_idx",
                "layer_idx",
                "expert_idx",
            ],
        },
        "stream_shapes": {
            "demand_stream_rows": int(demand_indices.shape[0]),
            "true_router_stream_rows": int(true_router_indices.shape[0]),
            "demand_stream_columns": int(demand_indices.shape[1]),
            "true_router_stream_columns": int(true_router_indices.shape[1]),
        },
        "policy_config_hash": hash_json(config.__dict__),
        "measured_copy_envelope": measured_copy,
        "cache_lab_gate_decision": (
            None if gate_decision is None else gate_decision.as_dict()
        ),
        "rows": rows,
        "pass_gate": evaluate_pass_gate(by_policy),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def _maybe_limit(tensor: torch.Tensor, max_token_examples: int | None) -> torch.Tensor:
    if max_token_examples is None:
        return tensor
    return tensor[: int(max_token_examples)]


def build_cache_lab_gate_decision(
    path: Path | None,
    *,
    config: CacheLabConfig,
):
    if path is None:
        return None
    payload = load_yaml(path)
    gate_config = CacheLabGateConfig(**payload)
    return select_cache_lab_prefetch_gate(
        CacheLabRuntimeSignals(
            payload_capacity=int(config.cache_capacity),
            overlap_factor=float(config.overlap_factor),
            manager_us_per_issue=float(config.manager_us_per_issue),
            bandwidth_gbps=float(config.bandwidth_gbps),
            stress_fallback_active=bool(config.stress_fallback),
        ),
        config=gate_config,
    )


def load_measured_copy_envelope(
    path: Path | None, *, stat: str, experts: int, pinned: str
) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        row
        for row in payload.get("rows", [])
        if isinstance(row, dict) and row.get("direction") == "h2d"
    ]
    if pinned != "any":
        want_pinned = pinned == "true"
        rows = [row for row in rows if bool(row.get("pinned")) is want_pinned]
    if not rows:
        raise ValueError(f"No matching H2D measured-copy rows in {path}.")
    selected = min(rows, key=lambda row: abs(int(row.get("experts", 0)) - int(experts)))
    selected_experts = max(1, int(selected.get("experts") or 1))
    stat_key = f"{stat}_ms"
    gbps_key = f"{stat}_gbps"
    if stat_key not in selected:
        raise KeyError(f"Measured-copy row lacks {stat_key!r}.")
    copy_us_per_issue = float(selected[stat_key]) * 1000.0 / float(selected_experts)
    return {
        "source": str(path),
        "stat": stat,
        "requested_experts": int(experts),
        "selected_experts": selected_experts,
        "pinned": bool(selected.get("pinned")),
        "direction": "h2d",
        "copy_us_per_batch": float(selected[stat_key]) * 1000.0,
        "copy_us_per_issue": copy_us_per_issue,
        "effective_gbps": float(selected.get(gbps_key, 0.0)),
        "row": selected,
    }


def build_policy_masks(
    *,
    train_transition_scores: torch.Tensor,
    train_mtp_scores: torch.Tensor,
    train_target_mass: torch.Tensor,
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    target_mass: torch.Tensor,
    config: CacheLabConfig,
) -> tuple[dict[str, torch.Tensor], dict[str, int]]:
    base = topk_mask(transition_scores, k=config.transition_topk)
    train_base = topk_mask(train_transition_scores, k=config.transition_topk)
    extra = novel_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=config.mtp_topk,
        max_extra=config.gate_max_extra,
    )
    train_extra = novel_mtp_extra_mask(
        train_base,
        train_mtp_scores,
        mtp_topk=config.mtp_topk,
        max_extra=config.gate_max_extra,
    )
    train_utility = build_mtp_extra_utility_scores(
        train_base,
        train_mtp_scores,
        mtp_topk=config.mtp_topk,
        layer_factors=_layer_factors(train_extra, train_target_mass),
    )
    eval_utility = build_mtp_extra_utility_scores(
        base,
        mtp_scores,
        mtp_topk=config.mtp_topk,
        layer_factors=_layer_factors(train_extra, train_target_mass),
    )
    score_threshold = threshold_from_keep_fraction(
        train_mtp_scores[train_extra],
        config.keep_fraction,
    )
    utility_threshold = threshold_from_keep_fraction(
        train_utility[train_extra],
        config.keep_fraction,
    )
    score_extra = extra & mtp_scores.float().ge(score_threshold)
    utility_extra = extra & eval_utility.float().ge(utility_threshold)
    score_shutdown = int(score_extra.sum().item()) if config.stress_fallback else 0
    utility_shutdown = int(utility_extra.sum().item()) if config.stress_fallback else 0
    if config.stress_fallback:
        score_extra = torch.zeros_like(score_extra)
        utility_extra = torch.zeros_like(utility_extra)
    score_name = f"transition_top{config.transition_topk}_plus_score_keep50"
    utility_name = f"transition_top{config.transition_topk}_plus_utility_keep50"
    return {
        "no_prefetch": torch.zeros_like(base),
        f"transition_top{config.transition_topk}": base,
        score_name: base | score_extra,
        utility_name: base | utility_extra,
        "oracle_used": target_mass.gt(0),
    }, {
        score_name: score_shutdown,
        utility_name: utility_shutdown,
    }


def build_policy_priority_scores(
    *,
    train_transition_scores: torch.Tensor,
    train_mtp_scores: torch.Tensor,
    train_target_mass: torch.Tensor,
    transition_scores: torch.Tensor,
    mtp_scores: torch.Tensor,
    config: CacheLabConfig,
) -> dict[str, torch.Tensor]:
    """Build same-shape priority tensors for queue backpressure admission.

    These scores do not change policy membership. They only choose which already
    admitted experts survive a drop/backpressure clip within a token/layer burst.
    """

    train_base = topk_mask(train_transition_scores, k=config.transition_topk)
    train_extra = novel_mtp_extra_mask(
        train_base,
        train_mtp_scores,
        mtp_topk=config.mtp_topk,
        max_extra=config.gate_max_extra,
    )
    eval_base = topk_mask(transition_scores, k=config.transition_topk)
    eval_utility = build_mtp_extra_utility_scores(
        eval_base,
        mtp_scores,
        mtp_topk=config.mtp_topk,
        layer_factors=_layer_factors(train_extra, train_target_mass),
    )
    score_name = f"transition_top{config.transition_topk}_plus_score_keep50"
    utility_name = f"transition_top{config.transition_topk}_plus_utility_keep50"
    return {
        "no_prefetch": torch.zeros_like(transition_scores.float()),
        f"transition_top{config.transition_topk}": transition_scores.float(),
        score_name: transition_scores.float() + mtp_scores.float(),
        utility_name: transition_scores.float() + eval_utility.float(),
        "oracle_used": torch.ones_like(transition_scores.float()),
    }


def apply_cache_lab_gate_to_policies(
    policies: dict[str, torch.Tensor],
    stress_shutdown_counts: dict[str, int],
    *,
    gate_decision: CacheLabGateDecision | None,
    config: CacheLabConfig,
) -> None:
    """Collapse gated MTP policies to the transition baseline when the gate rejects."""

    if gate_decision is None or gate_decision.allow_full_fetch_mtp:
        return
    base_name = f"transition_top{config.transition_topk}"
    for policy_name in list(policies):
        if policy_name.startswith(base_name + "_plus_"):
            stress_shutdown_counts[policy_name] = int(
                (policies[policy_name] & ~policies[base_name]).sum().item()
            )
            policies[policy_name] = policies[base_name].clone()


def _layer_factors(extra: torch.Tensor, target_mass: torch.Tensor) -> torch.Tensor:
    count = extra.float().sum(dim=(0, 1, 3)).clamp_min(1.0)
    gain = (extra.float() * target_mass.float()).sum(dim=(0, 1, 3)) / count
    positive = gain[gain.gt(0)]
    if positive.numel() == 0:
        return torch.ones_like(gain)
    return (gain / positive.mean().clamp_min(1e-12)).clamp(0.5, 1.5)


def threshold_from_keep_fraction(scores: torch.Tensor, keep_fraction: float) -> float:
    scores = scores.float()
    scores = scores[torch.isfinite(scores)]
    keep_fraction = min(max(float(keep_fraction), 0.0), 1.0)
    if keep_fraction <= 0.0 or scores.numel() == 0:
        return float("inf")
    if keep_fraction >= 1.0:
        return float(scores.min().item())
    return float(torch.quantile(scores, 1.0 - keep_fraction).item())


def demand_stream_indices(target_mass: torch.Tensor) -> torch.Tensor:
    # Columns: token_idx, layer_idx, expert_idx.  future_window is fixed at 0.
    positive = target_mass[:, 0].gt(0)
    return positive.nonzero(as_tuple=False).to(torch.int64)


def true_router_stream_indices(target_mass: torch.Tensor) -> torch.Tensor:
    # Columns: token_idx, future_window_idx, layer_idx, expert_idx.
    return target_mass.gt(0).nonzero(as_tuple=False).to(torch.int64)


def replay_policy(
    policy: str,
    prefetch_mask: torch.Tensor,
    *,
    target_mass: torch.Tensor,
    demand_indices: torch.Tensor,
    config: CacheLabConfig,
    stress_shutdown_count: int = 0,
    priority_scores: torch.Tensor | None = None,
    protected_mask: torch.Tensor | None = None,
    protected_priority_scores: torch.Tensor | None = None,
) -> dict[str, Any]:
    if config.queue_model == "event":
        return replay_policy_event_ready(
            policy,
            prefetch_mask,
            target_mass=target_mass,
            demand_indices=demand_indices,
            config=config,
            stress_shutdown_count=stress_shutdown_count,
            priority_scores=priority_scores,
            protected_mask=protected_mask,
            protected_priority_scores=protected_priority_scores,
        )

    manager = ControlledExpertCacheManager(capacity=config.cache_capacity)
    demand_count = int(demand_indices.shape[0])
    token_layers = int(target_mass.shape[0]) * int(target_mass.shape[2])
    demands_by_token_layer: dict[tuple[int, int], list[int]] = {}
    for token_idx, layer_idx, expert_idx in demand_indices.tolist():
        demands_by_token_layer.setdefault((int(token_idx), int(layer_idx)), []).append(
            int(expert_idx)
        )
    issue_batch_sizes: list[int] = []
    requested_issue_batch_sizes: list[int] = []
    backpressure_dropped_count = 0

    for token_idx in range(int(target_mass.shape[0])):
        for layer_idx in range(int(target_mass.shape[2])):
            row_mask = prefetch_mask[token_idx, 0, layer_idx]
            if policy == "oracle_used":
                experts = demands_by_token_layer.get((token_idx, layer_idx), [])
            else:
                experts = row_mask.nonzero(as_tuple=False).flatten().tolist()
            requested_issue_batch_sizes.append(len(experts))
            if (
                config.queue_policy == "drop"
                and config.max_inflight_prefetches > 0
                and len(experts) > config.max_inflight_prefetches
            ):
                backpressure_dropped_count += len(experts) - config.max_inflight_prefetches
                experts = select_admitted_experts(
                    experts,
                    token_idx=token_idx,
                    layer_idx=layer_idx,
                    limit=config.max_inflight_prefetches,
                    admission_policy=config.queue_admission_policy,
                    priority_scores=priority_scores,
                    protected_experts=(
                        None
                        if protected_mask is None
                        else protected_mask[token_idx, 0, layer_idx]
                        .nonzero(as_tuple=False)
                        .flatten()
                        .tolist()
                    ),
                    protected_priority_scores=protected_priority_scores,
                )
            issued_this_group = 0
            for expert_idx in experts:
                if manager.issue_prefetch(layer_idx, int(expert_idx)):
                    issued_this_group += 1
            issue_batch_sizes.append(issued_this_group)
            for expert_idx in demands_by_token_layer.get((token_idx, layer_idx), []):
                manager.demand(layer_idx, int(expert_idx))

    snapshot = manager.snapshot()
    queue_metrics = compute_prefetch_queue_metrics(
        issued_issue_batch_sizes=issue_batch_sizes,
        requested_issue_batch_sizes=requested_issue_batch_sizes,
        issued_count=snapshot.issued_fetch_count,
        config=config,
        dropped_count=backpressure_dropped_count,
    )
    raw_prefetch_dma_us = float(queue_metrics["queue_service_us"])
    effective_overlap_factor = clamp_unit_interval(config.overlap_factor)
    overlap_adjusted_prefetch_dma_us = raw_prefetch_dma_us * (
        1.0 - effective_overlap_factor
    )
    demand_stall_us = copy_cost_us(snapshot.demand_miss_count, config=config)
    manager_us = snapshot.issued_fetch_count * float(config.manager_us_per_issue)
    cache_lookup_us = snapshot.demand_count * float(config.lookup_us_per_demand)
    policy_decision_us = token_layers * float(config.decision_us_per_token_layer)
    total_cost_us = (
        demand_stall_us
        + overlap_adjusted_prefetch_dma_us
        + manager_us
        + queue_metrics["queue_wait_us"]
        + cache_lookup_us
        + policy_decision_us
    )
    used_per_issued_fetch = (
        snapshot.used_fetch_count / snapshot.issued_fetch_count
        if snapshot.issued_fetch_count
        else 0.0
    )
    return {
        "policy": policy,
        "demand_count": snapshot.demand_count,
        "demand_miss_count": snapshot.demand_miss_count,
        "demand_hit_count": snapshot.demand_hit_count,
        "issued_fetch_count": snapshot.issued_fetch_count,
        "issued_fetch_bytes": snapshot.issued_fetch_count * config.expert_bytes,
        "used_fetch_count": snapshot.used_fetch_count,
        "used_fetch_bytes": snapshot.used_fetch_count * config.expert_bytes,
        "unused_fetch_count": snapshot.unused_fetch_count,
        "unused_fetch_bytes": snapshot.unused_fetch_count * config.expert_bytes,
        "evicted_before_use_count": snapshot.evicted_before_use_count,
        "evicted_before_use_bytes": snapshot.evicted_before_use_count
        * config.expert_bytes,
        "cache_manager_snapshot": snapshot.as_dict(),
        "stress_shutdown_count": int(stress_shutdown_count),
        "fallback_count": 0,
        "demand_stall_us": demand_stall_us,
        "prefetch_dma_us": raw_prefetch_dma_us,
        "overlap_adjusted_prefetch_dma_us": overlap_adjusted_prefetch_dma_us,
        "effective_overlap_factor": effective_overlap_factor,
        "prefetch_manager_us": manager_us,
        "prefetch_queue_wait_us": queue_metrics["queue_wait_us"],
        "prefetch_queue_model": queue_metrics["queue_model"],
        "prefetch_queue_backpressure_semantics": queue_metrics.get(
            "queue_backpressure_semantics"
        ),
        "prefetch_queue_policy": queue_metrics["queue_policy"],
        "prefetch_queue_admission_policy": queue_metrics[
            "queue_admission_policy"
        ],
        "prefetch_queue_batch_size": queue_metrics["queue_batch_size"],
        "prefetch_queue_coalesce_scope": queue_metrics["queue_coalesce_scope"],
        "prefetch_queue_batch_count": queue_metrics["queue_batch_count"],
        "prefetch_queue_service_us": queue_metrics["queue_service_us"],
        "prefetch_queue_total_span_us": queue_metrics["queue_total_span_us"],
        "prefetch_queue_max_delay_us": queue_metrics["queue_max_delay_us"],
        "prefetch_queue_event_interval_us": queue_metrics[
            "queue_event_interval_us"
        ],
        "prefetch_queue_deadline_us": queue_metrics["queue_deadline_us"],
        "prefetch_backpressure_dropped_count": queue_metrics[
            "backpressure_dropped_count"
        ],
        "prefetch_queue_overflow_count": queue_metrics["queue_overflow_count"],
        "prefetch_queue_group_count": queue_metrics["queue_group_count"],
        "prefetch_queue_pressure": queue_metrics["queue_pressure"],
        "prefetch_max_issue_burst": queue_metrics["max_issue_burst"],
        "prefetch_avg_issue_burst": queue_metrics["avg_issue_burst"],
        "cache_lookup_us": cache_lookup_us,
        "policy_decision_us": policy_decision_us,
        "total_cost_us": total_cost_us,
        "used_per_issued_fetch": used_per_issued_fetch,
        "used_per_extra_byte": used_per_issued_fetch,
        "demand_hit_rate": (
            snapshot.demand_hit_count / snapshot.demand_count
            if snapshot.demand_count
            else 0.0
        ),
    }


def replay_policy_event_ready(
    policy: str,
    prefetch_mask: torch.Tensor,
    *,
    target_mass: torch.Tensor,
    demand_indices: torch.Tensor,
    config: CacheLabConfig,
    stress_shutdown_count: int = 0,
    priority_scores: torch.Tensor | None = None,
    protected_mask: torch.Tensor | None = None,
    protected_priority_scores: torch.Tensor | None = None,
) -> dict[str, Any]:
    """Replay an event-queue manager with ready-before-demand semantics.

    A prefetch is a demand hit only after its virtual H2D completion time is no
    later than the demand deadline for the token/layer event.  This is stricter
    than the legacy residency-only event queue and makes ``queue_deadline_us``
    part of the benefit model rather than only a queue diagnostic.
    """

    capacity = int(config.cache_capacity)
    cache: OrderedDict[tuple[int, int], CacheManagerEntry] = OrderedDict()
    pending_keys: list[tuple[int, int]] = []
    pending_first_arrival_us: float | None = None
    completions: deque[tuple[float, list[tuple[int, int]]]] = deque()
    inflight: set[tuple[int, int]] = set()

    issued_fetch_count = 0
    used_fetch_count = 0
    demand_count = 0
    demand_hit_count = 0
    demand_miss_count = 0
    evicted_before_use_count = 0
    ready_late_miss_count = 0
    late_completion_unused_count = 0
    backpressure_dropped_count = 0
    issue_batch_sizes: list[int] = []
    requested_issue_batch_sizes: list[int] = []

    batch_size = max(1, int(config.queue_batch_size) or 1)
    event_interval_us = max(0.0, float(config.queue_event_interval_us))
    deadline_us = max(0.0, float(config.queue_deadline_us))
    server_available_us = 0.0
    service_us_total = 0.0
    queue_wait_us_total = 0.0
    max_delay_us = 0.0
    batch_count = 0
    last_completion_us = 0.0
    last_arrival_us = 0.0

    demands_by_token_layer: dict[tuple[int, int], list[int]] = {}
    for token_idx, layer_idx, expert_idx in demand_indices.tolist():
        demands_by_token_layer.setdefault((int(token_idx), int(layer_idx)), []).append(
            int(expert_idx)
        )

    def insert_cache(key: tuple[int, int], entry: CacheManagerEntry) -> None:
        nonlocal evicted_before_use_count
        if capacity <= 0:
            if entry.prefetched and not entry.used:
                evicted_before_use_count += 1
            return
        cache[key] = entry
        cache.move_to_end(key)
        while len(cache) > capacity:
            _, old = cache.popitem(last=False)
            if old.prefetched and not old.used:
                evicted_before_use_count += 1

    def drain_ready(ready_time_us: float) -> None:
        nonlocal late_completion_unused_count
        while completions and completions[0][0] <= ready_time_us:
            _, keys = completions.popleft()
            for key in keys:
                inflight.discard(key)
                entry = cache.get(key)
                if entry is not None:
                    if not entry.prefetched:
                        late_completion_unused_count += 1
                    cache.move_to_end(key)
                    continue
                insert_cache(key, CacheManagerEntry(prefetched=True, used=False))

    def flush_pending(
        keys: list[tuple[int, int]],
        *,
        ready_us: float,
        first_arrival_us: float,
    ) -> None:
        nonlocal batch_count
        nonlocal last_completion_us
        nonlocal max_delay_us
        nonlocal queue_wait_us_total
        nonlocal service_us_total
        nonlocal server_available_us
        if not keys:
            return
        service_us = batch_copy_cost_us(len(keys), config=config)
        start_us = max(server_available_us, ready_us)
        wait_us = max(0.0, start_us - ready_us)
        completion_us = start_us + service_us
        batch_count += 1
        service_us_total += service_us
        queue_wait_us_total += wait_us
        max_delay_us = max(max_delay_us, completion_us - first_arrival_us)
        server_available_us = completion_us
        last_completion_us = completion_us
        completions.append((completion_us, list(keys)))

    def flush_due_pending(arrival_us: float) -> None:
        nonlocal pending_first_arrival_us
        if (
            pending_keys
            and pending_first_arrival_us is not None
            and deadline_us > 0.0
            and arrival_us >= pending_first_arrival_us + deadline_us
        ):
            first_arrival_us = pending_first_arrival_us
            keys = list(pending_keys)
            pending_keys.clear()
            pending_first_arrival_us = None
            flush_pending(
                keys,
                ready_us=first_arrival_us + deadline_us,
                first_arrival_us=first_arrival_us,
            )

    def issue_prefetch(key: tuple[int, int], arrival_us: float) -> bool:
        nonlocal issued_fetch_count
        nonlocal pending_first_arrival_us
        if key in cache:
            cache.move_to_end(key)
            return False
        if key in inflight:
            return False
        issued_fetch_count += 1
        inflight.add(key)
        if not pending_keys:
            pending_first_arrival_us = arrival_us
        pending_keys.append(key)
        while len(pending_keys) >= batch_size:
            first_arrival_us = (
                arrival_us
                if pending_first_arrival_us is None
                else pending_first_arrival_us
            )
            keys = pending_keys[:batch_size]
            del pending_keys[:batch_size]
            flush_pending(
                keys,
                ready_us=arrival_us,
                first_arrival_us=first_arrival_us,
            )
            pending_first_arrival_us = arrival_us if pending_keys else None
        return True

    for token_idx in range(int(target_mass.shape[0])):
        for layer_idx in range(int(target_mass.shape[2])):
            event_idx = token_idx * int(target_mass.shape[2]) + layer_idx
            arrival_us = float(event_idx) * event_interval_us
            last_arrival_us = arrival_us
            flush_due_pending(arrival_us)
            drain_ready(arrival_us)

            if policy == "oracle_used":
                experts = demands_by_token_layer.get((token_idx, layer_idx), [])
            else:
                experts = (
                    prefetch_mask[token_idx, 0, layer_idx]
                    .nonzero(as_tuple=False)
                    .flatten()
                    .tolist()
                )
            requested_issue_batch_sizes.append(len(experts))
            if (
                config.queue_policy == "drop"
                and config.max_inflight_prefetches > 0
                and len(experts) > config.max_inflight_prefetches
            ):
                backpressure_dropped_count += len(experts) - config.max_inflight_prefetches
                experts = select_admitted_experts(
                    experts,
                    token_idx=token_idx,
                    layer_idx=layer_idx,
                    limit=config.max_inflight_prefetches,
                    admission_policy=config.queue_admission_policy,
                    priority_scores=priority_scores,
                    protected_experts=(
                        None
                        if protected_mask is None
                        else protected_mask[token_idx, 0, layer_idx]
                        .nonzero(as_tuple=False)
                        .flatten()
                        .tolist()
                    ),
                    protected_priority_scores=protected_priority_scores,
                )

            issued_this_group = 0
            for expert_idx in experts:
                if issue_prefetch((int(layer_idx), int(expert_idx)), arrival_us):
                    issued_this_group += 1
            issue_batch_sizes.append(issued_this_group)

            demand_deadline_us = arrival_us + deadline_us
            flush_due_pending(demand_deadline_us)
            drain_ready(demand_deadline_us)
            for expert_idx in demands_by_token_layer.get((token_idx, layer_idx), []):
                key = (int(layer_idx), int(expert_idx))
                demand_count += 1
                entry = cache.get(key)
                if entry is not None:
                    demand_hit_count += 1
                    if entry.prefetched and not entry.used:
                        used_fetch_count += 1
                    entry.used = True
                    cache.move_to_end(key)
                    continue
                if key in inflight:
                    ready_late_miss_count += 1
                demand_miss_count += 1
                insert_cache(key, CacheManagerEntry(prefetched=False, used=True))

    if pending_keys and pending_first_arrival_us is not None:
        first_arrival_us = pending_first_arrival_us
        ready_us = (
            first_arrival_us + deadline_us
            if deadline_us > 0.0
            else last_arrival_us
        )
        keys = list(pending_keys)
        pending_keys.clear()
        pending_first_arrival_us = None
        flush_pending(keys, ready_us=ready_us, first_arrival_us=first_arrival_us)
    drain_ready(float("inf"))

    resident_unused_fetch_count = sum(
        1 for entry in cache.values() if entry.prefetched and not entry.used
    )
    unused_fetch_count = resident_unused_fetch_count + late_completion_unused_count
    snapshot = CacheManagerSnapshot(
        capacity=capacity,
        resident_count=len(cache),
        issued_fetch_count=issued_fetch_count,
        used_fetch_count=used_fetch_count,
        unused_fetch_count=unused_fetch_count,
        demand_count=demand_count,
        demand_hit_count=demand_hit_count,
        demand_miss_count=demand_miss_count,
        evicted_before_use_count=evicted_before_use_count,
    )
    requested_positive = [
        int(size) for size in requested_issue_batch_sizes if int(size) > 0
    ]
    requested_count = sum(requested_positive)
    issued_positive = [int(size) for size in issue_batch_sizes if int(size) > 0]
    if int(config.max_inflight_prefetches) <= 0:
        overflow = 0
    else:
        overflow = sum(
            max(0, size - int(config.max_inflight_prefetches))
            for size in requested_positive
        )
    queue_wait_us = (
        0.0
        if str(config.queue_policy) == "drop"
        else max(0.0, last_completion_us - service_us_total)
    )
    queue_metrics: dict[str, float | int | str] = {
        "queue_model": "event_driven_ready_time_batch_queue",
        "queue_backpressure_semantics": (
            "drop clips each token/layer burst before enqueue; wait admits all "
            "requested prefetches into the virtual DMA queue. Demand hits "
            "require H2D completion no later than the token/layer demand "
            "deadline."
        ),
        "queue_policy": str(config.queue_policy),
        "queue_admission_policy": str(config.queue_admission_policy),
        "queue_batch_size": int(config.queue_batch_size),
        "queue_coalesce_scope": "global",
        "queue_batch_count": int(batch_count),
        "queue_group_count": len(requested_positive),
        "queue_overflow_count": int(overflow),
        "backpressure_dropped_count": int(backpressure_dropped_count),
        "queue_pressure": (
            float(overflow) / float(requested_count) if requested_count else 0.0
        ),
        "queue_service_us": float(service_us_total),
        "queue_total_span_us": (
            max(0.0, last_completion_us) if issued_fetch_count else 0.0
        ),
        "queue_wait_us": float(queue_wait_us),
        "queue_cumulative_wait_us": float(queue_wait_us_total),
        "queue_max_delay_us": float(max_delay_us),
        "queue_event_interval_us": event_interval_us,
        "queue_deadline_us": deadline_us,
        "max_issue_burst": max(requested_positive, default=0),
        "avg_issue_burst": (
            float(requested_count) / float(len(requested_positive))
            if requested_positive
            else 0.0
        ),
    }

    raw_prefetch_dma_us = float(queue_metrics["queue_service_us"])
    effective_overlap_factor = clamp_unit_interval(config.overlap_factor)
    overlap_adjusted_prefetch_dma_us = raw_prefetch_dma_us * (
        1.0 - effective_overlap_factor
    )
    demand_stall_us = copy_cost_us(snapshot.demand_miss_count, config=config)
    manager_us = snapshot.issued_fetch_count * float(config.manager_us_per_issue)
    cache_lookup_us = snapshot.demand_count * float(config.lookup_us_per_demand)
    token_layers = int(target_mass.shape[0]) * int(target_mass.shape[2])
    policy_decision_us = token_layers * float(config.decision_us_per_token_layer)
    total_cost_us = (
        demand_stall_us
        + overlap_adjusted_prefetch_dma_us
        + manager_us
        + float(queue_metrics["queue_wait_us"])
        + cache_lookup_us
        + policy_decision_us
    )
    used_per_issued_fetch = (
        snapshot.used_fetch_count / snapshot.issued_fetch_count
        if snapshot.issued_fetch_count
        else 0.0
    )
    return {
        "policy": policy,
        "demand_count": snapshot.demand_count,
        "demand_miss_count": snapshot.demand_miss_count,
        "demand_hit_count": snapshot.demand_hit_count,
        "issued_fetch_count": snapshot.issued_fetch_count,
        "issued_fetch_bytes": snapshot.issued_fetch_count * config.expert_bytes,
        "used_fetch_count": snapshot.used_fetch_count,
        "used_fetch_bytes": snapshot.used_fetch_count * config.expert_bytes,
        "unused_fetch_count": snapshot.unused_fetch_count,
        "unused_fetch_bytes": snapshot.unused_fetch_count * config.expert_bytes,
        "evicted_before_use_count": snapshot.evicted_before_use_count,
        "evicted_before_use_bytes": snapshot.evicted_before_use_count
        * config.expert_bytes,
        "cache_manager_snapshot": snapshot.as_dict(),
        "stress_shutdown_count": int(stress_shutdown_count),
        "fallback_count": 0,
        "demand_stall_us": demand_stall_us,
        "prefetch_dma_us": raw_prefetch_dma_us,
        "overlap_adjusted_prefetch_dma_us": overlap_adjusted_prefetch_dma_us,
        "effective_overlap_factor": effective_overlap_factor,
        "prefetch_manager_us": manager_us,
        "prefetch_queue_wait_us": queue_metrics["queue_wait_us"],
        "prefetch_queue_model": queue_metrics["queue_model"],
        "prefetch_queue_backpressure_semantics": queue_metrics.get(
            "queue_backpressure_semantics"
        ),
        "prefetch_queue_policy": queue_metrics["queue_policy"],
        "prefetch_queue_admission_policy": queue_metrics[
            "queue_admission_policy"
        ],
        "prefetch_queue_batch_size": queue_metrics["queue_batch_size"],
        "prefetch_queue_coalesce_scope": queue_metrics["queue_coalesce_scope"],
        "prefetch_queue_batch_count": queue_metrics["queue_batch_count"],
        "prefetch_queue_service_us": queue_metrics["queue_service_us"],
        "prefetch_queue_total_span_us": queue_metrics["queue_total_span_us"],
        "prefetch_queue_max_delay_us": queue_metrics["queue_max_delay_us"],
        "prefetch_queue_event_interval_us": queue_metrics[
            "queue_event_interval_us"
        ],
        "prefetch_queue_deadline_us": queue_metrics["queue_deadline_us"],
        "prefetch_ready_late_miss_count": int(ready_late_miss_count),
        "prefetch_late_completion_unused_count": int(
            late_completion_unused_count
        ),
        "prefetch_resident_unused_count": int(resident_unused_fetch_count),
        "prefetch_backpressure_dropped_count": queue_metrics[
            "backpressure_dropped_count"
        ],
        "prefetch_queue_overflow_count": queue_metrics["queue_overflow_count"],
        "prefetch_queue_group_count": queue_metrics["queue_group_count"],
        "prefetch_queue_pressure": queue_metrics["queue_pressure"],
        "prefetch_max_issue_burst": queue_metrics["max_issue_burst"],
        "prefetch_avg_issue_burst": queue_metrics["avg_issue_burst"],
        "cache_lookup_us": cache_lookup_us,
        "policy_decision_us": policy_decision_us,
        "total_cost_us": total_cost_us,
        "used_per_issued_fetch": used_per_issued_fetch,
        "used_per_extra_byte": used_per_issued_fetch,
        "demand_hit_rate": (
            snapshot.demand_hit_count / snapshot.demand_count
            if snapshot.demand_count
            else 0.0
        ),
    }


def _add_delta_rows(rows: list[dict[str, Any]], *, baseline: str) -> None:
    by_policy = {row["policy"]: row for row in rows}
    base = by_policy[baseline]
    no_prefetch = by_policy["no_prefetch"]
    for row in rows:
        row["demand_stall_saved_us_vs_no_prefetch"] = (
            no_prefetch["demand_stall_us"] - row["demand_stall_us"]
        )
        row["demand_stall_saved_us_vs_transition"] = (
            base["demand_stall_us"] - row["demand_stall_us"]
        )
        row["net_saved_us_vs_transition"] = base["total_cost_us"] - row["total_cost_us"]
        row["net_saved_us_vs_no_prefetch"] = (
            no_prefetch["total_cost_us"] - row["total_cost_us"]
        )
        row["stall_reduction_vs_transition"] = (
            row["demand_stall_saved_us_vs_transition"] / base["demand_stall_us"]
            if base["demand_stall_us"] > 0
            else 0.0
        )


def select_admitted_experts(
    experts: list[int],
    *,
    token_idx: int,
    layer_idx: int,
    limit: int,
    admission_policy: str,
    priority_scores: torch.Tensor | None,
    protected_experts: list[int] | None = None,
    protected_priority_scores: torch.Tensor | None = None,
) -> list[int]:
    limit = max(0, int(limit))
    if len(experts) <= limit:
        return list(experts)
    if limit <= 0:
        return []
    if admission_policy == "protected_score":
        protected_set = {int(expert_idx) for expert_idx in protected_experts or []}
        protected = [int(expert_idx) for expert_idx in experts if int(expert_idx) in protected_set]
        protected_ranked = _rank_experts_by_score(
            protected,
            token_idx=token_idx,
            layer_idx=layer_idx,
            scores=protected_priority_scores,
        )
        if len(protected_ranked) >= limit:
            return protected_ranked[:limit]
        extras = [int(expert_idx) for expert_idx in experts if int(expert_idx) not in protected_set]
        extra_ranked = _rank_experts_by_score(
            extras,
            token_idx=token_idx,
            layer_idx=layer_idx,
            scores=priority_scores,
        )
        return protected_ranked + extra_ranked[: limit - len(protected_ranked)]
    if admission_policy != "score" or priority_scores is None:
        return list(experts[:limit])
    return _rank_experts_by_score(
        experts,
        token_idx=token_idx,
        layer_idx=layer_idx,
        scores=priority_scores,
    )[:limit]


def _rank_experts_by_score(
    experts: list[int],
    *,
    token_idx: int,
    layer_idx: int,
    scores: torch.Tensor | None,
) -> list[int]:
    if scores is None:
        return list(experts)
    ranked = sorted(
        enumerate(experts),
        key=lambda item: (
            float(scores[int(token_idx), 0, int(layer_idx), int(item[1])]),
            -int(item[0]),
        ),
        reverse=True,
    )
    return [int(expert_idx) for _, expert_idx in ranked]


def evaluate_pass_gate(by_policy: dict[str, dict[str, Any]]) -> dict[str, Any]:
    utility = _first_policy_suffix(by_policy, "_plus_utility_keep50")
    score = _first_policy_suffix(by_policy, "_plus_score_keep50")
    return {
        "utility_net_positive_vs_transition": (
            float(utility.get("net_saved_us_vs_transition", 0.0)) > 0.0
        ),
        "score_net_positive_vs_transition": (
            float(score.get("net_saved_us_vs_transition", 0.0)) > 0.0
        ),
        "any_gated_net_positive_vs_transition": (
            float(utility.get("net_saved_us_vs_transition", 0.0)) > 0.0
            or float(score.get("net_saved_us_vs_transition", 0.0)) > 0.0
        ),
    }


def _first_policy_suffix(
    by_policy: dict[str, dict[str, Any]],
    suffix: str,
) -> dict[str, Any]:
    for name, row in by_policy.items():
        if name.endswith(suffix):
            return row
    return {}


def transfer_us(byte_count: int | float, bandwidth_gbps: float) -> float:
    if bandwidth_gbps <= 0:
        return float("inf")
    return float(byte_count) / (float(bandwidth_gbps) * 1_000_000_000.0) * 1_000_000.0


def clamp_unit_interval(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def copy_cost_us(issue_count: int, *, config: CacheLabConfig) -> float:
    if issue_count <= 0:
        return 0.0
    if config.measured_copy_us_per_issue is not None:
        return float(issue_count) * float(config.measured_copy_us_per_issue)
    return transfer_us(int(issue_count) * config.expert_bytes, config.bandwidth_gbps)


def batch_copy_cost_us(payload_count: int, *, config: CacheLabConfig) -> float:
    if payload_count <= 0:
        return 0.0
    if config.measured_copy_us_per_batch is not None:
        source_batch_size = max(1, int(config.measured_copy_batch_size))
        selected_batch_us = float(config.measured_copy_us_per_batch)
        return selected_batch_us * float(payload_count) / float(source_batch_size)
    if config.measured_copy_us_per_issue is not None:
        return float(config.measured_copy_us_per_issue) * float(payload_count)
    return transfer_us(int(payload_count) * config.expert_bytes, config.bandwidth_gbps)


def prefetch_copy_cost_us(
    issue_batch_sizes: list[int], *, issued_count: int, config: CacheLabConfig
) -> float:
    batch_size = int(config.queue_batch_size)
    if batch_size <= 0:
        return copy_cost_us(issued_count, config=config)
    if config.queue_coalesce_scope == "global":
        batch_count = ceil_div(int(issued_count), batch_size)
    else:
        batch_count = sum(ceil_div(int(size), batch_size) for size in issue_batch_sizes)
    batch_us = batch_copy_cost_us(batch_size, config=config)
    return float(batch_count) * batch_us


def compute_prefetch_queue_metrics(
    *,
    issued_issue_batch_sizes: list[int],
    requested_issue_batch_sizes: list[int],
    issued_count: int,
    config: CacheLabConfig,
    dropped_count: int = 0,
) -> dict[str, float | int | str]:
    if config.queue_model == "event":
        return simulate_event_driven_queue(
            issued_issue_batch_sizes,
            requested_issue_batch_sizes=requested_issue_batch_sizes,
            config=config,
            dropped_count=dropped_count,
        )
    metrics = compute_queue_pressure(
        requested_issue_batch_sizes,
        max_inflight=config.max_inflight_prefetches,
        wait_us_per_overflow=config.queue_wait_us_per_overflow,
        batch_size=config.queue_batch_size,
        coalesce_scope=config.queue_coalesce_scope,
        policy=config.queue_policy,
        dropped_count=dropped_count,
    )
    metrics["queue_admission_policy"] = str(config.queue_admission_policy)
    metrics["queue_service_us"] = prefetch_copy_cost_us(
        issued_issue_batch_sizes,
        issued_count=issued_count,
        config=config,
    )
    metrics["queue_total_span_us"] = float(metrics["queue_service_us"])
    metrics["queue_max_delay_us"] = float(metrics["queue_wait_us"])
    metrics["queue_event_interval_us"] = 0.0
    metrics["queue_deadline_us"] = 0.0
    return metrics


def compute_queue_pressure(
    issue_batch_sizes: list[int],
    *,
    max_inflight: int,
    wait_us_per_overflow: float,
    batch_size: int = 0,
    coalesce_scope: str = "token_layer",
    policy: str = "wait",
    dropped_count: int = 0,
) -> dict[str, float | int | str]:
    positive = [int(size) for size in issue_batch_sizes if int(size) > 0]
    issued = sum(positive)
    max_burst = max(positive, default=0)
    avg_burst = (float(issued) / float(len(positive))) if positive else 0.0
    if max_inflight <= 0:
        overflow = 0
    else:
        overflow = sum(max(0, size - int(max_inflight)) for size in positive)
    effective_batch = max(1, int(batch_size))
    if batch_size <= 0:
        batch_count = len(positive)
    elif coalesce_scope == "global":
        batch_count = ceil_div(issued, effective_batch)
    else:
        batch_count = sum(ceil_div(size, effective_batch) for size in positive)
    queue_wait_us = (
        0.0
        if policy == "drop"
        else float(overflow) * float(wait_us_per_overflow)
    )
    return {
        "queue_model": "per_token_layer_burst_overflow",
        "queue_policy": str(policy),
        "queue_admission_policy": "prefix",
        "queue_batch_size": int(batch_size),
        "queue_coalesce_scope": str(coalesce_scope),
        "queue_batch_count": int(batch_count),
        "queue_group_count": len(positive),
        "queue_overflow_count": int(overflow),
        "backpressure_dropped_count": int(dropped_count),
        "queue_pressure": (float(overflow) / float(issued)) if issued else 0.0,
        "queue_wait_us": queue_wait_us,
        "max_issue_burst": int(max_burst),
        "avg_issue_burst": avg_burst,
    }


def simulate_event_driven_queue(
    issue_batch_sizes: list[int],
    *,
    requested_issue_batch_sizes: list[int],
    config: CacheLabConfig,
    dropped_count: int = 0,
) -> dict[str, float | int | str]:
    requested_positive = [
        int(size) for size in requested_issue_batch_sizes if int(size) > 0
    ]
    requested_count = sum(requested_positive)
    issued_positive = [int(size) for size in issue_batch_sizes if int(size) > 0]
    issued_count = sum(issued_positive)
    max_burst = max(requested_positive, default=0)
    avg_burst = (
        float(requested_count) / float(len(requested_positive))
        if requested_positive
        else 0.0
    )
    if int(config.max_inflight_prefetches) <= 0:
        overflow = 0
    else:
        overflow = sum(
            max(0, size - int(config.max_inflight_prefetches))
            for size in requested_positive
        )

    batch_size = max(1, int(config.queue_batch_size) or 1)
    event_interval_us = max(0.0, float(config.queue_event_interval_us))
    deadline_us = max(0.0, float(config.queue_deadline_us))
    server_available_us = 0.0
    pending_payloads = 0
    pending_first_arrival_us: float | None = None
    service_us_total = 0.0
    queue_wait_us_total = 0.0
    max_delay_us = 0.0
    batch_count = 0
    last_completion_us = 0.0
    last_arrival_us = 0.0

    def flush(payloads: int, ready_us: float) -> None:
        nonlocal batch_count
        nonlocal last_completion_us
        nonlocal max_delay_us
        nonlocal queue_wait_us_total
        nonlocal service_us_total
        nonlocal server_available_us
        if payloads <= 0:
            return
        service_us = batch_copy_cost_us(payloads, config=config)
        start_us = max(server_available_us, ready_us)
        wait_us = max(0.0, start_us - ready_us)
        completion_us = start_us + service_us
        batch_count += 1
        service_us_total += service_us
        queue_wait_us_total += wait_us
        max_delay_us = max(max_delay_us, completion_us - ready_us)
        server_available_us = completion_us
        last_completion_us = completion_us

    for event_idx, size in enumerate(issue_batch_sizes):
        arrival_us = float(event_idx) * event_interval_us
        last_arrival_us = arrival_us
        if (
            pending_payloads > 0
            and pending_first_arrival_us is not None
            and deadline_us > 0.0
            and arrival_us >= pending_first_arrival_us + deadline_us
        ):
            flush(pending_payloads, pending_first_arrival_us + deadline_us)
            pending_payloads = 0
            pending_first_arrival_us = None
        if size <= 0:
            continue
        if pending_payloads == 0:
            pending_first_arrival_us = arrival_us
        pending_payloads += int(size)
        while pending_payloads >= batch_size:
            flush(batch_size, arrival_us)
            pending_payloads -= batch_size
            pending_first_arrival_us = arrival_us if pending_payloads > 0 else None

    if pending_payloads > 0 and pending_first_arrival_us is not None:
        ready_us = (
            pending_first_arrival_us + deadline_us
            if deadline_us > 0.0
            else last_arrival_us
        )
        flush(pending_payloads, ready_us)

    return {
        "queue_model": "event_driven_batch_queue",
        "queue_backpressure_semantics": (
            "drop clips each token/layer burst before enqueue; wait admits all "
            "requested prefetches and charges only virtual DMA queue span."
        ),
        "queue_policy": str(config.queue_policy),
        "queue_admission_policy": str(config.queue_admission_policy),
        "queue_batch_size": int(config.queue_batch_size),
        "queue_coalesce_scope": "global",
        "queue_batch_count": int(batch_count),
        "queue_group_count": len(requested_positive),
        "queue_overflow_count": int(overflow),
        "backpressure_dropped_count": int(dropped_count),
        "queue_pressure": (
            float(overflow) / float(requested_count) if requested_count else 0.0
        ),
        "queue_service_us": float(service_us_total),
        "queue_total_span_us": (
            max(0.0, last_completion_us) if issued_count else 0.0
        ),
        "queue_wait_us": max(0.0, last_completion_us - service_us_total),
        "queue_cumulative_wait_us": float(queue_wait_us_total),
        "queue_max_delay_us": float(max_delay_us),
        "queue_event_interval_us": event_interval_us,
        "queue_deadline_us": deadline_us,
        "max_issue_burst": int(max_burst),
        "avg_issue_burst": avg_burst,
    }


def ceil_div(value: int, divisor: int) -> int:
    if value <= 0:
        return 0
    return (int(value) + int(divisor) - 1) // int(divisor)


def hash_demand_stream(indices: torch.Tensor) -> str:
    digest = hashlib.sha256()
    digest.update(str(tuple(indices.shape)).encode("ascii"))
    digest.update(indices.contiguous().numpy().tobytes())
    return digest.hexdigest()


def hash_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prefetch Cache Lab Replay",
        "",
        "Boundary:",
        "",
        "```text",
        str(payload["boundary"]),
        "```",
        "",
        f"Tensor cache: `{payload['tensor_cache']}`",
        "",
        "## Configuration",
        "",
        "```json",
        json.dumps(payload["config"], indent=2, sort_keys=True),
        "```",
        "",
        "## Policies",
        "",
        "| policy | demand hit | issued | used/issued | evicted-unused | demand stall ms | prefetch dma ms | total cost ms | net saved vs transition ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {policy} | {hit:.2%} | {issued} | {used:.3f} | {evicted} | {stall:.3f} | {dma:.3f} | {total:.3f} | {net:.3f} |".format(
                policy=row["policy"],
                hit=float(row["demand_hit_rate"]),
                issued=int(row["issued_fetch_count"]),
                used=float(row["used_per_extra_byte"]),
                evicted=int(row["evicted_before_use_count"]),
                stall=float(row["demand_stall_us"]) / 1000.0,
                dma=float(row["prefetch_dma_us"]) / 1000.0,
                total=float(row["total_cost_us"]) / 1000.0,
                net=float(row["net_saved_us_vs_transition"]) / 1000.0,
            )
        )
    lines.extend(
        [
            "",
            "## Pass Gate",
            "",
            "```json",
            json.dumps(payload["pass_gate"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
