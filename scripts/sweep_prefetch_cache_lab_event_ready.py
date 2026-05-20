#!/usr/bin/env python3
"""Sweep ready-time-aware event queue budgets for cache-lab replay."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_prefetch_cache_lab import (
    CacheLabConfig,
    _add_delta_rows,
    apply_cache_lab_gate_to_policies,
    build_cache_lab_gate_decision,
    build_policy_masks,
    build_policy_priority_scores,
    demand_stream_indices,
    evaluate_pass_gate,
    load_measured_copy_envelope,
    replay_policy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tensor_cache", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--split", default=None)
    parser.add_argument("--campaign", default="event_ready_budget_sweep")
    parser.add_argument("--trace-source", default=None)
    parser.add_argument("--cache-lab-gate-config", type=Path)
    parser.add_argument("--cache-capacity", type=int, default=10240)
    parser.add_argument("--bandwidth-gbps", type=float, default=6.589)
    parser.add_argument("--expert-bytes", type=int, default=1_650_000)
    parser.add_argument("--overlap-factor", type=float, default=0.5)
    parser.add_argument("--gate-max-extra", type=int, default=8)
    parser.add_argument("--keep-fraction", type=float, default=0.5)
    parser.add_argument("--manager-us-per-issue", type=float, default=50.0)
    parser.add_argument("--lookup-us-per-demand", type=float, default=0.0)
    parser.add_argument("--decision-us-per-token-layer", type=float, default=0.0)
    parser.add_argument("--measured-copy-json", type=Path, required=True)
    parser.add_argument("--measured-copy-stat", choices=("mean", "p50", "p90", "p95"), default="p95")
    parser.add_argument("--measured-copy-experts", type=int, default=8)
    parser.add_argument("--measured-copy-pinned", choices=("true", "false", "any"), default="true")
    parser.add_argument(
        "--copy-scale",
        type=float,
        default=1.0,
        help=(
            "Scale measured copy latency for what-if faster/slower copy envelope "
            "sweeps. 1.0 preserves the measured-copy row."
        ),
    )
    parser.add_argument("--max-inflight", type=int, nargs="+", required=True)
    parser.add_argument("--deadline-us", type=float, nargs="+", required=True)
    parser.add_argument("--queue-batch-size", type=int, default=8)
    parser.add_argument("--queue-policy", choices=("wait", "drop"), default="drop")
    parser.add_argument(
        "--queue-admission-policy",
        choices=("prefix", "score", "protected_score"),
        default="protected_score",
    )
    parser.add_argument("--queue-event-interval-us", type=float, default=50.0)
    parser.add_argument("--stress-fallback", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache = torch.load(args.tensor_cache, map_location="cpu")
    measured_copy = load_measured_copy_envelope(
        args.measured_copy_json,
        stat=str(args.measured_copy_stat),
        experts=int(args.measured_copy_experts),
        pinned=str(args.measured_copy_pinned),
    )
    measured_copy = _scale_measured_copy(measured_copy, scale=float(args.copy_scale))
    base_config = _make_config(args, measured_copy, max_inflight=0, deadline_us=0.0)
    policies, stress_shutdown_counts = build_policy_masks(
        train_transition_scores=cache["train_transition_scores"],
        train_mtp_scores=cache["train_mtp_scores"],
        train_target_mass=cache["train_target_mass"],
        transition_scores=cache["transition_scores"],
        mtp_scores=cache["mtp_scores"],
        target_mass=cache["target_mass"],
        config=base_config,
    )
    priority_scores = build_policy_priority_scores(
        train_transition_scores=cache["train_transition_scores"],
        train_mtp_scores=cache["train_mtp_scores"],
        train_target_mass=cache["train_target_mass"],
        transition_scores=cache["transition_scores"],
        mtp_scores=cache["mtp_scores"],
        config=base_config,
    )
    target_mass = cache["target_mass"]
    demand_indices = demand_stream_indices(target_mass)
    base_policy = f"transition_top{base_config.transition_topk}"
    base_mask = policies[base_policy]
    base_scores = priority_scores[base_policy]
    sweep_rows: list[dict[str, Any]] = []
    raw_runs: list[dict[str, Any]] = []
    for max_inflight in sorted({int(item) for item in args.max_inflight}):
        for deadline_us in sorted({float(item) for item in args.deadline_us}):
            config = _make_config(
                args,
                measured_copy,
                max_inflight=max_inflight,
                deadline_us=deadline_us,
            )
            run_policies = {name: mask.clone() for name, mask in policies.items()}
            run_shutdown = dict(stress_shutdown_counts)
            gate_decision = build_cache_lab_gate_decision(
                args.cache_lab_gate_config,
                config=config,
            )
            apply_cache_lab_gate_to_policies(
                run_policies,
                run_shutdown,
                gate_decision=gate_decision,
                config=config,
            )
            rows = []
            for policy, mask in run_policies.items():
                protected_mask = (
                    base_mask
                    if (
                        policy == base_policy
                        or policy.startswith(base_policy + "_plus_")
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
                        stress_shutdown_count=run_shutdown.get(policy, 0),
                        priority_scores=priority_scores.get(policy),
                        protected_mask=protected_mask,
                        protected_priority_scores=base_scores,
                    )
                )
            _add_delta_rows(rows, baseline=base_policy)
            by_policy = {row["policy"]: row for row in rows}
            raw_runs.append(
                {
                    "max_inflight": max_inflight,
                    "deadline_us": deadline_us,
                    "pass_gate": evaluate_pass_gate(by_policy),
                    "rows": rows,
                }
            )
            for row in rows:
                if not (
                    row["policy"] == base_policy
                    or row["policy"].endswith("_plus_score_keep50")
                    or row["policy"].endswith("_plus_utility_keep50")
                ):
                    continue
                sweep_rows.append(
                    {
                        "max_inflight": max_inflight,
                        "deadline_us": deadline_us,
                        "policy": row["policy"],
                        "net_saved_ms_vs_transition": float(
                            row["net_saved_us_vs_transition"]
                        )
                        / 1000.0,
                        "demand_hit_rate": row["demand_hit_rate"],
                        "issued_fetch_count": row["issued_fetch_count"],
                        "used_per_issued_fetch": row["used_per_issued_fetch"],
                        "late_miss_count": row.get(
                            "prefetch_ready_late_miss_count",
                            0,
                        ),
                        "late_completion_unused_count": row.get(
                            "prefetch_late_completion_unused_count",
                            0,
                        ),
                        "unused_fetch_count": row.get("unused_fetch_count", 0),
                        "queue_pressure": row["prefetch_queue_pressure"],
                        "queue_service_ms": float(row["prefetch_queue_service_us"])
                        / 1000.0,
                        "queue_max_delay_ms": float(row["prefetch_queue_max_delay_us"])
                        / 1000.0,
                    }
                )
    _add_extra_issued_delta(sweep_rows, baseline_policy=base_policy)

    first_positive = _first_positive_by_policy(
        sweep_rows,
        require_extra_issued=False,
    )
    first_positive_mtp_extra_issued = _first_positive_by_policy(
        sweep_rows,
        require_extra_issued=True,
    )
    payload = {
        "ok": True,
        "boundary": (
            "Ready-time-aware event queue cache-lab sweep only; not endpoint "
            "TPOT and not a real vLLM DMA/cache manager."
        ),
        "tensor_cache": str(args.tensor_cache),
        "metadata": {
            "campaign": args.campaign,
            "dataset": args.dataset,
            "split": args.split,
            "trace_source": args.trace_source,
            "copy_scale": float(args.copy_scale),
        },
        "base_config": base_config.__dict__,
        "max_inflight": sorted({int(item) for item in args.max_inflight}),
        "deadline_us": sorted({float(item) for item in args.deadline_us}),
        "copy_scale": float(args.copy_scale),
        "first_positive": first_positive,
        "first_positive_mtp_extra_issued": first_positive_mtp_extra_issued,
        "sweep_rows": sweep_rows,
        "raw_runs": raw_runs,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "sweep.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(args.output_dir / "summary.csv", sweep_rows)
    (args.output_dir / "summary.md").write_text(_render_markdown(payload), encoding="utf-8")
    print(_render_markdown(payload))


def _make_config(
    args: argparse.Namespace,
    measured_copy: dict[str, Any] | None,
    *,
    max_inflight: int,
    deadline_us: float,
) -> CacheLabConfig:
    return CacheLabConfig(
        transition_topk=32,
        mtp_topk=64,
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
        max_inflight_prefetches=int(max_inflight),
        queue_model="event",
        queue_batch_size=int(args.queue_batch_size),
        queue_coalesce_scope="global",
        queue_policy=str(args.queue_policy),
        queue_admission_policy=str(args.queue_admission_policy),
        queue_wait_us_per_overflow=(
            0.0 if measured_copy is None else float(measured_copy["copy_us_per_issue"])
        ),
        queue_event_interval_us=float(args.queue_event_interval_us),
        queue_deadline_us=float(deadline_us),
    )


def _first_positive_by_policy(
    rows: list[dict[str, Any]], *, require_extra_issued: bool
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    candidates = sorted(
        rows,
        key=lambda row: (
            int(row["max_inflight"]),
            float(row["deadline_us"]),
            str(row["policy"]),
        ),
    )
    for row in candidates:
        policy = str(row["policy"])
        if not policy.endswith("_plus_score_keep50") and not policy.endswith(
            "_plus_utility_keep50"
        ):
            continue
        if policy in out:
            continue
        if require_extra_issued and int(row.get("extra_issued_vs_transition", 0)) <= 0:
            continue
        if float(row["net_saved_ms_vs_transition"]) > 0.0:
            out[policy] = {
                "max_inflight": int(row["max_inflight"]),
                "deadline_us": float(row["deadline_us"]),
                "net_saved_ms_vs_transition": float(
                    row["net_saved_ms_vs_transition"]
                ),
                "late_miss_count": int(row["late_miss_count"]),
                "late_completion_unused_count": int(
                    row.get("late_completion_unused_count", 0)
                ),
                "extra_issued_vs_transition": int(
                    row.get("extra_issued_vs_transition", 0)
                ),
            }
    return out


def _scale_measured_copy(
    measured_copy: dict[str, Any] | None, *, scale: float
) -> dict[str, Any] | None:
    if measured_copy is None:
        return None
    scale = float(scale)
    if scale <= 0.0:
        raise ValueError("--copy-scale must be positive.")
    out = dict(measured_copy)
    out["copy_us_per_issue"] = float(out["copy_us_per_issue"]) * scale
    out["copy_us_per_batch"] = float(out["copy_us_per_batch"]) * scale
    out["copy_scale"] = scale
    if float(out.get("effective_gbps", 0.0)) > 0.0:
        out["effective_gbps"] = float(out["effective_gbps"]) / scale
    return out


def _add_extra_issued_delta(
    rows: list[dict[str, Any]], *, baseline_policy: str
) -> None:
    baseline_issued: dict[tuple[int, float], int] = {}
    for row in rows:
        if row["policy"] == baseline_policy:
            baseline_issued[(int(row["max_inflight"]), float(row["deadline_us"]))] = int(
                row["issued_fetch_count"]
            )
    for row in rows:
        key = (int(row["max_inflight"]), float(row["deadline_us"]))
        row["extra_issued_vs_transition"] = int(row["issued_fetch_count"]) - int(
            baseline_issued.get(key, 0)
        )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "max_inflight",
        "deadline_us",
        "policy",
        "net_saved_ms_vs_transition",
        "demand_hit_rate",
        "issued_fetch_count",
        "extra_issued_vs_transition",
        "used_per_issued_fetch",
        "late_miss_count",
        "late_completion_unused_count",
        "unused_fetch_count",
        "queue_pressure",
        "queue_service_ms",
        "queue_max_delay_ms",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ready-Time Event Queue Sweep",
        "",
        "Boundary:",
        "",
        "```text",
        str(payload["boundary"]),
        "```",
        "",
        "## First Positive",
        "",
        "```json",
        json.dumps(payload["first_positive"], indent=2, sort_keys=True),
        "```",
        "",
        "## First Positive With Extra Issued",
        "",
        "```json",
        json.dumps(
            payload.get("first_positive_mtp_extra_issued", {}),
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Rows",
        "",
        "| max_inflight | deadline us | policy | net vs transition ms | hit | issued | extra issued | used/issued | late miss | late unused | queue pressure | max delay ms |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["sweep_rows"]:
        lines.append(
            "| {max_inflight} | {deadline:.1f} | {policy} | {net:.3f} | {hit:.2%} | {issued} | {extra_issued} | {used:.4f} | {late} | {late_unused} | {pressure:.3f} | {delay:.3f} |".format(
                max_inflight=row["max_inflight"],
                deadline=float(row["deadline_us"]),
                policy=row["policy"],
                net=float(row["net_saved_ms_vs_transition"]),
                hit=float(row["demand_hit_rate"]),
                issued=int(row["issued_fetch_count"]),
                extra_issued=int(row.get("extra_issued_vs_transition", 0)),
                used=float(row["used_per_issued_fetch"]),
                late=int(row["late_miss_count"]),
                late_unused=int(row.get("late_completion_unused_count", 0)),
                pressure=float(row["queue_pressure"]),
                delay=float(row["queue_max_delay_ms"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
