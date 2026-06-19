#!/usr/bin/env python3
"""Sweep issue-to-demand lookahead for the payload-cache stream executor."""

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
    / "premap_payload_cache_issue_stream_executor_measured_copy_lookahead_sweep_v1.json"
)
DEFAULT_MEASURED_COPY_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "prefetch_action_replay"
    / "measured_copy_gpu1_expert_transfer_v1.json"
)
SAFE_FALSE_FLAGS = (
    "full_fetch_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
SAFE_ZERO_FLAGS = ("payload_bytes",)


def _load_executor_module():
    path = REPO_ROOT / "scripts" / "run_premap_payload_cache_issue_stream_executor.py"
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_issue_stream_executor",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load stream executor module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _parse_values(raw: str, *, label: str) -> list[float]:
    values = [float(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} sweep must contain at least one value")
    if any(value < 0.0 for value in values):
        raise ValueError(f"{label} sweep values must be non-negative")
    if values != sorted(values):
        raise ValueError(f"{label} sweep values must be sorted in ascending order")
    return values


def _check_row_safety(
    result: dict[str, Any],
    failures: list[str],
    *,
    row_index: int,
) -> dict[str, Any]:
    safety: dict[str, Any] = {}
    for key in SAFE_FALSE_FLAGS:
        value = result.get(key)
        safety[key] = value
        if key not in result:
            failures.append(f"row_{row_index}_{key}_missing")
        elif value is not False:
            failures.append(f"row_{row_index}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        value = result.get(key)
        safety[key] = value
        if key not in result:
            failures.append(f"row_{row_index}_{key}_missing")
        elif value != 0:
            failures.append(f"row_{row_index}_{key}_not_zero")
    return safety


def run_stream_lookahead_sweep(args: argparse.Namespace) -> dict[str, Any]:
    executor = _load_executor_module()
    output_path = _resolve(args.output_json)
    lookahead_values = _parse_values(args.lookahead_us_values, label="lookahead")
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    first_model_passing_lookahead_us: float | None = None

    for index, lookahead_us in enumerate(lookahead_values):
        row_output = output_path.parent / (
            f".{output_path.stem}_pid_{os.getpid()}_lookahead_{index:03d}.json"
        )
        argv = [
            "--online-canary-json",
            str(_resolve(args.online_canary_json)),
            "--output-json",
            str(row_output),
            "--capacity",
            str(args.capacity),
            "--queue-deadline-us",
            str(args.queue_deadline_us),
            "--event-interval-us",
            str(args.event_interval_us),
            "--issue-arrival-us",
            str(args.issue_arrival_us),
            "--demand-gap-us",
            str(lookahead_us),
            "--min-demand-hit-rate",
            str(args.min_demand_hit_rate),
            "--max-ready-late-miss-rate",
            str(args.max_ready_late_miss_rate),
            "--min-used-per-issued-fetch",
            str(args.min_used_per_issued_fetch),
        ]
        if args.measured_copy_json is not None:
            argv.extend(
                [
                    "--measured-copy-json",
                    str(_resolve(args.measured_copy_json)),
                    "--measured-copy-stat",
                    str(args.measured_copy_stat),
                    "--measured-copy-experts",
                    str(args.measured_copy_experts),
                    "--measured-copy-pinned",
                    str(args.measured_copy_pinned),
                ]
            )
        row_args = executor.build_parser().parse_args(argv)
        try:
            result = executor.run_issue_stream_executor(row_args)
        finally:
            try:
                row_output.unlink()
            except OSError:
                pass
        model_passed = bool(result.get("passed"))
        failure_count_before_safety = len(failures)
        row_safety = _check_row_safety(result, failures, row_index=index)
        row_safety_failures = failures[failure_count_before_safety:]
        row = {
            "lookahead_us": float(lookahead_us),
            "queue_deadline_us": float(args.queue_deadline_us),
            "effective_ready_deadline_us": float(lookahead_us)
            + float(args.queue_deadline_us),
            "model_passed": model_passed,
            "passed": model_passed and not row_safety_failures,
            "safety_passed": not row_safety_failures,
            "safety_failures": row_safety_failures,
            "full_fetch_allowed": bool(result.get("full_fetch_allowed")),
            "full_fetch_block_reason": result.get("full_fetch_block_reason"),
            "payload_bytes": result.get("payload_bytes"),
            "ready_credit": result.get("ready_credit"),
            "ready_before_demand_credit": result.get("ready_before_demand_credit"),
            "real_ready_credit_granted": result.get("real_ready_credit_granted"),
            "payload_transfer_enabled": result.get("payload_transfer_enabled"),
            "payload_deref_allowed": result.get("payload_deref_allowed"),
            "kernel_arg_pass_allowed": result.get("kernel_arg_pass_allowed"),
            "passed_to_kernel": result.get("passed_to_kernel"),
            "changes_kernel_launch_args": result.get("changes_kernel_launch_args"),
            "uses_current_wna16_args": result.get("uses_current_wna16_args"),
            "passes_current_wna16_args": result.get("passes_current_wna16_args"),
            "measures_tpot": result.get("measures_tpot"),
            "measures_vllm_latency": result.get("measures_vllm_latency"),
            "demand_hit_rate": float(result.get("demand_hit_rate", 0.0) or 0.0),
            "ready_late_miss_rate": float(
                result.get("ready_late_miss_rate", 0.0) or 0.0
            ),
            "used_per_issued_fetch": float(
                result.get("used_per_issued_fetch", 0.0) or 0.0
            ),
            "queue_total_span_us": float(result.get("queue_total_span_us", 0.0) or 0.0),
            "queue_service_us": float(result.get("queue_service_us", 0.0) or 0.0),
            "queue_max_delay_us": float(result.get("queue_max_delay_us", 0.0) or 0.0),
            "measured_copy_us_per_batch": result.get("measured_copy_us_per_batch"),
            "measured_copy_us_per_issue": result.get("measured_copy_us_per_issue"),
            "failures": result.get("failures", []),
        }
        row.update(row_safety)
        rows.append(row)
        if model_passed and first_model_passing_lookahead_us is None:
            first_model_passing_lookahead_us = float(lookahead_us)

    payload = {
        "artifact_kind": "premap_payload_cache_issue_stream_executor_lookahead_sweep",
        "passed": first_model_passing_lookahead_us is not None and not failures,
        "failures": failures,
        "first_model_passing_lookahead_us": first_model_passing_lookahead_us,
        "first_passing_lookahead_us": first_model_passing_lookahead_us,
        "queue_deadline_us": float(args.queue_deadline_us),
        "event_interval_us": float(args.event_interval_us),
        "issue_arrival_us": float(args.issue_arrival_us),
        "lookahead_us_values": lookahead_values,
        "rows": rows,
        "online_canary_json": str(_resolve(args.online_canary_json)),
        "measured_copy_json": (
            None
            if args.measured_copy_json is None
            else str(_resolve(args.measured_copy_json))
        ),
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
            "ready-time stream lookahead sweep only; no real payload movement, "
            "ready credit, kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": "increase_stream_lookahead_or_keep_full_fetch_blocked",
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
        "--online-canary-json",
        type=Path,
        default=executor.DEFAULT_ONLINE_CANARY_JSON,
    )
    parser.add_argument("--measured-copy-json", type=Path, default=DEFAULT_MEASURED_COPY_JSON)
    parser.add_argument("--measured-copy-stat", default="p95")
    parser.add_argument("--measured-copy-experts", type=int, default=8)
    parser.add_argument("--measured-copy-pinned", default="true")
    parser.add_argument("--capacity", type=int, default=12288)
    parser.add_argument("--queue-deadline-us", type=float, default=200.0)
    parser.add_argument("--event-interval-us", type=float, default=1.0)
    parser.add_argument("--issue-arrival-us", type=float, default=0.0)
    parser.add_argument(
        "--lookahead-us-values",
        default="0,1000,5000,10000,50000,100000,200000,243000,245000,250000,300000",
    )
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.5)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.2)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.5)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_stream_lookahead_sweep(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
