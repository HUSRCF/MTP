#!/usr/bin/env python3
"""Sweep ready-time slack for the payload-cache issue-plan executor."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_plan_executor_measured_copy_slack_sweep_v1.json"
)


def _load_executor_module():
    path = REPO_ROOT / "scripts" / "run_premap_payload_cache_issue_plan_executor.py"
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_issue_plan_executor",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load executor module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _parse_deadlines(raw: str) -> list[float]:
    values = [float(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError("deadline sweep must contain at least one value")
    if any(value < 0.0 for value in values):
        raise ValueError("deadline sweep values must be non-negative")
    if values != sorted(values):
        raise ValueError("deadline sweep values must be sorted in ascending order")
    return values


def run_slack_sweep(args: argparse.Namespace) -> dict[str, Any]:
    executor = _load_executor_module()
    output_path = _resolve(args.output_json)
    deadlines = _parse_deadlines(args.deadline_us_values)
    rows: list[dict[str, Any]] = []
    first_passing_deadline_us: float | None = None
    for index, deadline_us in enumerate(deadlines):
        row_output = output_path.parent / (
            f".{output_path.stem}_pid_{os.getpid()}_deadline_{index:03d}.json"
        )
        row_args = executor.build_parser().parse_args(
            [
                "--issue-plan-gate-json",
                str(_resolve(args.issue_plan_gate_json)),
                "--output-json",
                str(row_output),
                "--capacity",
                str(args.capacity),
                "--measured-copy-json",
                str(_resolve(args.measured_copy_json)),
                "--measured-copy-stat",
                str(args.measured_copy_stat),
                "--measured-copy-experts",
                str(args.measured_copy_experts),
                "--measured-copy-pinned",
                str(args.measured_copy_pinned),
                "--queue-deadline-us",
                str(deadline_us),
                "--min-demand-hit-rate",
                str(args.min_demand_hit_rate),
                "--max-ready-late-miss-rate",
                str(args.max_ready_late_miss_rate),
                "--min-used-per-issued-fetch",
                str(args.min_used_per_issued_fetch),
            ]
        )
        try:
            result = executor.run_issue_plan_executor(row_args)
        finally:
            try:
                row_output.unlink()
            except OSError:
                pass
        row = {
            "deadline_us": float(deadline_us),
            "passed": bool(result.get("passed")),
            "model_passed": bool(result.get("passed")),
            "full_fetch_allowed": bool(result.get("full_fetch_allowed")),
            "full_fetch_block_reason": result.get("full_fetch_block_reason"),
            "demand_hit_rate": float(result.get("demand_hit_rate", 0.0) or 0.0),
            "ready_late_miss_rate": float(
                result.get("ready_late_miss_rate", 0.0) or 0.0
            ),
            "used_per_issued_fetch": float(
                result.get("used_per_issued_fetch", 0.0) or 0.0
            ),
            "queue_total_span_us": float(result.get("queue_total_span_us", 0.0) or 0.0),
            "queue_service_us": float(result.get("queue_service_us", 0.0) or 0.0),
            "measured_copy_us_per_batch": result.get("measured_copy_us_per_batch"),
            "measured_copy_us_per_issue": result.get("measured_copy_us_per_issue"),
            "failures": result.get("failures", []),
        }
        rows.append(row)
        if row["passed"] and first_passing_deadline_us is None:
            first_passing_deadline_us = float(deadline_us)
    payload = {
        "artifact_kind": "premap_payload_cache_issue_plan_executor_slack_sweep",
        "passed": first_passing_deadline_us is not None,
        "first_passing_deadline_us": first_passing_deadline_us,
        "first_model_passing_deadline_us": first_passing_deadline_us,
        "deadline_us_values": deadlines,
        "rows": rows,
        "issue_plan_gate_json": str(_resolve(args.issue_plan_gate_json)),
        "measured_copy_json": str(_resolve(args.measured_copy_json)),
        "measured_copy_stat": str(args.measured_copy_stat),
        "measured_copy_experts": int(args.measured_copy_experts),
        "measured_copy_pinned": str(args.measured_copy_pinned),
        "capacity": int(args.capacity),
        "min_demand_hit_rate": float(args.min_demand_hit_rate),
        "max_ready_late_miss_rate": float(args.max_ready_late_miss_rate),
        "min_used_per_issued_fetch": float(args.min_used_per_issued_fetch),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "full_fetch_allowed": False,
        "full_fetch_block_reason": "real_payload_runtime_not_enabled",
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "boundary": (
            "ready-time measured-copy slack sweep only; not real payload movement "
            "and not endpoint latency"
        ),
        "next_runtime_stage": "increase_lookahead_slack_or_keep_full_fetch_blocked",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    executor = _load_executor_module()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issue-plan-gate-json",
        type=Path,
        default=executor.DEFAULT_ISSUE_PLAN_GATE_JSON,
    )
    parser.add_argument(
        "--measured-copy-json",
        type=Path,
        default=REPO_ROOT
        / "configs"
        / "runtime"
        / "premap_payload_cache_gpu0_pcie4x16_h2d_measured_copy_20260625.json",
    )
    parser.add_argument("--measured-copy-stat", default="p95")
    parser.add_argument("--measured-copy-experts", type=int, default=8)
    parser.add_argument("--measured-copy-pinned", default="true")
    parser.add_argument("--capacity", type=int, default=12288)
    parser.add_argument(
        "--deadline-us-values",
        default="200,1000,5000,10000,14661.311949203082,15000,20000",
    )
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.5)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.2)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.5)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_slack_sweep(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
