#!/usr/bin/env python3
"""Sweep issue-to-demand lookahead for the payload-cache stream executor."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
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
    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"{label} sweep values must be finite")
    if any(value < 0.0 for value in values):
        raise ValueError(f"{label} sweep values must be non-negative")
    if values != sorted(values):
        raise ValueError(f"{label} sweep values must be sorted in ascending order")
    return values


def _parse_int_values(raw: str, *, label: str) -> list[int]:
    values = [int(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} sweep must contain at least one value")
    if any(value < 0 for value in values):
        raise ValueError(f"{label} sweep values must be non-negative")
    if values != sorted(values):
        raise ValueError(f"{label} sweep values must be sorted in ascending order")
    return values


def _positive_float_arg(args: argparse.Namespace, name: str, default: float) -> float:
    value = float(getattr(args, name, default))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name.replace('_', '-')} must be a positive finite number")
    return value


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
    event_timing_mode = str(getattr(args, "event_timing_mode", "packet_index")).strip().lower()
    if event_timing_mode not in {"packet_index", "token_index"}:
        raise ValueError("event-timing-mode must be packet_index or token_index")
    token_timing_enabled = event_timing_mode == "token_index"
    lookahead_values = _parse_values(args.lookahead_us_values, label="lookahead")
    decode_token_us = _positive_float_arg(args, "decode_token_us", 75_000.0)
    issue_lead_token_values = _parse_int_values(
        getattr(args, "issue_lead_token_values", "0,1,2,3,4,8"),
        label="issue lead token",
    )
    layer_event_interval_us = float(getattr(args, "layer_event_interval_us", 1.0))
    allow_config_token_source = bool(getattr(args, "allow_config_token_source", False))
    sweep_values: list[float | int]
    if token_timing_enabled:
        sweep_values = issue_lead_token_values
    else:
        sweep_values = lookahead_values
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    first_model_passing_lookahead_us: float | None = None
    first_model_passing_issue_lead_tokens: int | None = None

    for index, sweep_value in enumerate(sweep_values):
        lookahead_us = (
            float(int(sweep_value) * decode_token_us)
            if token_timing_enabled
            else float(sweep_value)
        )
        if not math.isfinite(lookahead_us):
            raise ValueError("derived lookahead_us must be finite")
        issue_lead_tokens = int(sweep_value) if token_timing_enabled else 0
        row_output = output_path.parent / (
            f".{output_path.stem}_pid_{os.getpid()}_row_{index:03d}.json"
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
            "--event-timing-mode",
            event_timing_mode,
            "--decode-token-us",
            str(decode_token_us),
            "--issue-lead-tokens",
            str(issue_lead_tokens),
            "--layer-event-interval-us",
            str(layer_event_interval_us),
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
        if allow_config_token_source:
            argv.append("--allow-config-token-source")
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
        issue_arrival_min_us = result.get("issue_arrival_min_us")
        issue_arrival_max_us = result.get("issue_arrival_max_us")
        demand_arrival_min_us = result.get("demand_arrival_min_us")
        demand_arrival_max_us = result.get("demand_arrival_max_us")
        observed_lead_min_us = None
        observed_lead_max_us = None
        issue_arrival_clamp_at_zero_possible = False
        try:
            if issue_arrival_min_us is not None and demand_arrival_min_us is not None:
                observed_lead_min_us = max(
                    0.0,
                    float(demand_arrival_min_us) - float(issue_arrival_min_us),
                )
            if issue_arrival_max_us is not None and demand_arrival_max_us is not None:
                observed_lead_max_us = max(
                    0.0,
                    float(demand_arrival_max_us) - float(issue_arrival_max_us),
                )
            issue_arrival_clamp_at_zero_possible = bool(
                token_timing_enabled
                and demand_arrival_min_us is not None
                and float(lookahead_us) > float(demand_arrival_min_us)
            )
        except (TypeError, ValueError):
            observed_lead_min_us = None
            observed_lead_max_us = None
            issue_arrival_clamp_at_zero_possible = False
        row = {
            "event_timing_mode": event_timing_mode,
            "token_timing_enabled": token_timing_enabled,
            "issue_lead_tokens": issue_lead_tokens,
            "lookahead_us": float(lookahead_us),
            "lookahead_us_kind": (
                "requested_token_lead_us"
                if token_timing_enabled
                else "packet_index_demand_gap_us"
            ),
            "requested_lookahead_us": float(lookahead_us),
            "decode_token_us": decode_token_us,
            "layer_event_interval_us": layer_event_interval_us,
            "queue_deadline_us": float(args.queue_deadline_us),
            "effective_ready_deadline_us": float(lookahead_us)
            + float(args.queue_deadline_us),
            "requested_effective_ready_deadline_us": float(lookahead_us)
            + float(args.queue_deadline_us),
            "issue_arrival_clamp_at_zero_possible": issue_arrival_clamp_at_zero_possible,
            "observed_issue_to_demand_lead_min_us": observed_lead_min_us,
            "observed_issue_to_demand_lead_max_us": observed_lead_max_us,
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
            "token_index_count": result.get("token_index_count"),
            "token_index_min": result.get("token_index_min"),
            "token_index_max": result.get("token_index_max"),
            "token_source_decode_workload_count": result.get(
                "token_source_decode_workload_count"
            ),
            "token_source_config_count": result.get("token_source_config_count"),
            "token_source_missing_count": result.get("token_source_missing_count"),
            "allow_config_token_source": result.get("allow_config_token_source"),
            "issue_arrival_min_us": issue_arrival_min_us,
            "issue_arrival_max_us": issue_arrival_max_us,
            "demand_arrival_min_us": demand_arrival_min_us,
            "demand_arrival_max_us": demand_arrival_max_us,
            "failures": result.get("failures", []),
        }
        row.update(row_safety)
        rows.append(row)
        if model_passed and first_model_passing_lookahead_us is None:
            first_model_passing_lookahead_us = float(lookahead_us)
            first_model_passing_issue_lead_tokens = (
                int(issue_lead_tokens) if token_timing_enabled else None
            )

    payload = {
        "artifact_kind": "premap_payload_cache_issue_stream_executor_lookahead_sweep",
        "passed": first_model_passing_lookahead_us is not None and not failures,
        "failures": failures,
        "first_model_passing_lookahead_us": first_model_passing_lookahead_us,
        "first_passing_lookahead_us": first_model_passing_lookahead_us,
        "first_model_passing_issue_lead_tokens": first_model_passing_issue_lead_tokens,
        "event_timing_mode": event_timing_mode,
        "token_timing_enabled": token_timing_enabled,
        "lookahead_us_kind": (
            "requested_token_lead_us"
            if token_timing_enabled
            else "packet_index_demand_gap_us"
        ),
        "decode_token_us": decode_token_us,
        "issue_lead_token_values": issue_lead_token_values,
        "layer_event_interval_us": layer_event_interval_us,
        "allow_config_token_source": allow_config_token_source,
        "queue_deadline_us": float(args.queue_deadline_us),
        "event_interval_us": float(args.event_interval_us),
        "issue_arrival_us": float(args.issue_arrival_us),
        "lookahead_us_values": [float(row["lookahead_us"]) for row in rows],
        "configured_lookahead_us_values": lookahead_values,
        "requested_lookahead_us_values": [float(row["requested_lookahead_us"]) for row in rows],
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
    parser.add_argument(
        "--event-timing-mode",
        choices=("packet_index", "token_index"),
        default="packet_index",
    )
    parser.add_argument("--decode-token-us", type=float, default=75_000.0)
    parser.add_argument("--issue-lead-token-values", default="0,1,2,3,4,8")
    parser.add_argument("--layer-event-interval-us", type=float, default=1.0)
    parser.add_argument("--allow-config-token-source", action="store_true")
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
