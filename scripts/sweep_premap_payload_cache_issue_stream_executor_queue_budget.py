#!/usr/bin/env python3
"""Sweep capacity/deadline/lead budgets for the payload-cache stream executor."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_stream_executor_queue_budget_sweep_v1.json"
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


def _load_lookahead_module():
    path = REPO_ROOT / "scripts" / "sweep_premap_payload_cache_issue_stream_executor_lookahead.py"
    spec = importlib.util.spec_from_file_location(
        "sweep_premap_payload_cache_issue_stream_executor_lookahead",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load lookahead sweep module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _parse_int_values(raw: str, *, label: str, positive: bool = False) -> list[int]:
    values = [int(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} sweep must contain at least one value")
    lower_bound = 1 if positive else 0
    if any(value < lower_bound for value in values):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{label} sweep values must be {qualifier}")
    if values != sorted(values):
        raise ValueError(f"{label} sweep values must be sorted in ascending order")
    return values


def _parse_float_values(raw: str, *, label: str) -> list[float]:
    values = [float(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} sweep must contain at least one value")
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"{label} sweep values must be finite")
    if any(value < 0.0 for value in values):
        raise ValueError(f"{label} sweep values must be non-negative")
    if values != sorted(values):
        raise ValueError(f"{label} sweep values must be sorted in ascending order")
    return values


def _check_cell_safety(
    result: dict[str, Any],
    failures: list[str],
    *,
    cell_index: int,
) -> dict[str, Any]:
    safety: dict[str, Any] = {}
    for key in SAFE_FALSE_FLAGS:
        value = result.get(key)
        safety[key] = value
        if key not in result:
            failures.append(f"cell_{cell_index}_{key}_missing")
        elif value is not False:
            failures.append(f"cell_{cell_index}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        value = result.get(key)
        safety[key] = value
        if key not in result:
            failures.append(f"cell_{cell_index}_{key}_missing")
        elif not _valid_number(value) or float(value) != 0.0:
            failures.append(f"cell_{cell_index}_{key}_not_zero")
    return safety


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _first_passing_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row.get("passed") is True:
            return row
    return None


def _best_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            float(row.get("demand_hit_rate", 0.0) or 0.0),
            -float(row.get("ready_late_miss_rate", 1.0) or 1.0),
            float(row.get("used_per_issued_fetch", 0.0) or 0.0),
        ),
    )


def run_queue_budget_sweep(args: argparse.Namespace) -> dict[str, Any]:
    lookahead = _load_lookahead_module()
    output_path = _resolve(args.output_json)
    capacity_values = _parse_int_values(
        args.capacity_values,
        label="capacity",
        positive=True,
    )
    queue_deadline_us_values = _parse_float_values(
        args.queue_deadline_us_values,
        label="queue deadline",
    )
    issue_lead_token_values = _parse_int_values(
        args.issue_lead_token_values,
        label="issue lead token",
    )
    event_timing_mode = str(args.event_timing_mode).strip().lower()
    if event_timing_mode != "token_index":
        raise ValueError("queue budget sweep currently requires token_index timing")

    cells: list[dict[str, Any]] = []
    failures: list[str] = []
    first_model_passing_cell: dict[str, Any] | None = None
    cell_index = 0
    for capacity in capacity_values:
        for queue_deadline_us in queue_deadline_us_values:
            cell_output = output_path.parent / (
                f".{output_path.stem}_capacity_{capacity}_deadline_{int(queue_deadline_us)}.json"
            )
            cell_args = SimpleNamespace(
                online_canary_json=args.online_canary_json,
                measured_copy_json=args.measured_copy_json,
                measured_copy_stat=args.measured_copy_stat,
                measured_copy_experts=args.measured_copy_experts,
                measured_copy_pinned=args.measured_copy_pinned,
                capacity=capacity,
                queue_deadline_us=queue_deadline_us,
                event_timing_mode=event_timing_mode,
                decode_token_us=args.decode_token_us,
                issue_lead_token_values=",".join(str(value) for value in issue_lead_token_values),
                layer_event_interval_us=args.layer_event_interval_us,
                allow_config_token_source=args.allow_config_token_source,
                allow_empty_config_packets=args.allow_empty_config_packets,
                event_interval_us=args.event_interval_us,
                issue_arrival_us=args.issue_arrival_us,
                lookahead_us_values=args.lookahead_us_values,
                min_demand_hit_rate=args.min_demand_hit_rate,
                max_ready_late_miss_rate=args.max_ready_late_miss_rate,
                min_used_per_issued_fetch=args.min_used_per_issued_fetch,
                output_json=cell_output,
            )
            try:
                result = lookahead.run_stream_lookahead_sweep(cell_args)
            finally:
                try:
                    cell_output.unlink()
                except OSError:
                    pass
            first_row = _first_passing_row(list(result.get("rows", [])))
            best_row = _best_row(list(result.get("rows", [])))
            failure_count_before_safety = len(failures)
            child_failures = [
                f"cell_{cell_index}_{failure}"
                for failure in list(result.get("failures", []))
            ]
            failures.extend(child_failures)
            cell_safety = _check_cell_safety(result, failures, cell_index=cell_index)
            cell_safety_failures = failures[failure_count_before_safety:]
            child_model_passed = (
                result.get("first_model_passing_lookahead_us") is not None
            )
            cell_passed = bool(result.get("passed")) and not cell_safety_failures
            cell = {
                "cell_index": cell_index,
                "capacity": capacity,
                "queue_deadline_us": float(queue_deadline_us),
                "model_passed": child_model_passed,
                "child_passed": bool(result.get("passed")),
                "safety_passed": not cell_safety_failures,
                "passed": cell_passed,
                "safety_failures": cell_safety_failures,
                "first_model_passing_issue_lead_tokens": result.get(
                    "first_model_passing_issue_lead_tokens"
                ),
                "first_model_passing_lookahead_us": result.get(
                    "first_model_passing_lookahead_us"
                ),
                "first_passing_row": first_row,
                "best_row": best_row,
                "row_count": len(result.get("rows", [])),
                "rows": result.get("rows", []),
                "failures": result.get("failures", []),
            }
            cell.update(cell_safety)
            cells.append(cell)
            if child_model_passed and first_model_passing_cell is None:
                first_model_passing_cell = {
                    "capacity": capacity,
                    "queue_deadline_us": float(queue_deadline_us),
                    "issue_lead_tokens": result.get(
                        "first_model_passing_issue_lead_tokens"
                    ),
                    "lookahead_us": result.get("first_model_passing_lookahead_us"),
                    "cell_index": cell_index,
            }
            cell_index += 1

    passed = first_model_passing_cell is not None and not failures
    first_passing_cell = first_model_passing_cell if passed else None
    payload = {
        "artifact_kind": "premap_payload_cache_issue_stream_executor_queue_budget_sweep",
        "passed": passed,
        "failures": failures,
        "first_passing_cell": first_passing_cell,
        "first_model_passing_cell": first_model_passing_cell,
        "capacity_values": capacity_values,
        "queue_deadline_us_values": queue_deadline_us_values,
        "issue_lead_token_values": issue_lead_token_values,
        "event_timing_mode": event_timing_mode,
        "decode_token_us": float(args.decode_token_us),
        "layer_event_interval_us": float(args.layer_event_interval_us),
        "allow_config_token_source": bool(args.allow_config_token_source),
        "allow_empty_config_packets": bool(args.allow_empty_config_packets),
        "online_canary_json": str(_resolve(args.online_canary_json)),
        "measured_copy_json": (
            None
            if args.measured_copy_json is None
            else str(_resolve(args.measured_copy_json))
        ),
        "measured_copy_stat": str(args.measured_copy_stat),
        "measured_copy_experts": int(args.measured_copy_experts),
        "measured_copy_pinned": str(args.measured_copy_pinned),
        "min_demand_hit_rate": float(args.min_demand_hit_rate),
        "max_ready_late_miss_rate": float(args.max_ready_late_miss_rate),
        "min_used_per_issued_fetch": float(args.min_used_per_issued_fetch),
        "cell_count": len(cells),
        "cells": cells,
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
            "queue-budget replay only; no real payload movement, ready credit, "
            "kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": "calibrate_queue_budget_or_keep_full_fetch_blocked",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    lookahead = _load_lookahead_module()
    defaults = lookahead.build_parser().parse_args([])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online-canary-json",
        type=Path,
        default=defaults.online_canary_json,
    )
    parser.add_argument("--measured-copy-json", type=Path, default=defaults.measured_copy_json)
    parser.add_argument("--measured-copy-stat", default=defaults.measured_copy_stat)
    parser.add_argument("--measured-copy-experts", type=int, default=defaults.measured_copy_experts)
    parser.add_argument("--measured-copy-pinned", default=defaults.measured_copy_pinned)
    parser.add_argument("--capacity-values", default="64,128,256,512,4096,12288")
    parser.add_argument("--queue-deadline-us-values", default="200,1000,5000,20000")
    parser.add_argument("--event-timing-mode", choices=("token_index",), default="token_index")
    parser.add_argument("--decode-token-us", type=float, default=defaults.decode_token_us)
    parser.add_argument("--issue-lead-token-values", default="0,1,2,4,8")
    parser.add_argument("--layer-event-interval-us", type=float, default=defaults.layer_event_interval_us)
    parser.add_argument("--allow-config-token-source", action="store_true")
    parser.add_argument("--allow-empty-config-packets", action="store_true")
    parser.add_argument("--event-interval-us", type=float, default=defaults.event_interval_us)
    parser.add_argument("--issue-arrival-us", type=float, default=defaults.issue_arrival_us)
    parser.add_argument("--lookahead-us-values", default=defaults.lookahead_us_values)
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.6)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.4)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.4)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_queue_budget_sweep(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
