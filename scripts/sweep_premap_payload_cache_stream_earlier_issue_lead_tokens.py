#!/usr/bin/env python3
"""Sweep producer-side earlier issue in decode-token lead units."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_stream_earlier_issue_lead_tokens_dolly4_gen64_decode75ms_v1_20260620.json"
)
SAFE_FALSE_FLAGS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "full_fetch_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
SAFE_ZERO_FLAGS = ("payload_bytes",)


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _load_stream_sweep_module():
    path = REPO_ROOT / "scripts" / "sweep_premap_payload_cache_issue_stream_executor_lookahead.py"
    spec = importlib.util.spec_from_file_location(
        "sweep_premap_payload_cache_issue_stream_executor_lookahead",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load stream sweep module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _parse_nonnegative_ints(raw: str, *, label: str) -> list[int]:
    values = [int(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    if any(value < 0 for value in values):
        raise ValueError(f"{label} values must be non-negative")
    if values != sorted(values):
        raise ValueError(f"{label} values must be sorted in ascending order")
    return values


def _check_safety(payload: dict[str, Any], failures: list[str], *, prefix: str) -> None:
    for key in SAFE_FALSE_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif not _valid_number(payload.get(key)) or float(payload.get(key)) != 0.0:
            failures.append(f"{prefix}_{key}_not_zero")


def _validate_stream_sweep(
    sweep: dict[str, Any],
    *,
    expected_lookahead_values: list[float],
    expected_lead_tokens: list[int],
    failures: list[str],
) -> None:
    if (
        sweep.get("artifact_kind")
        != "premap_payload_cache_issue_stream_executor_lookahead_sweep"
    ):
        failures.append("stream_sweep_artifact_kind_mismatch")
    if sweep.get("passed") is not True:
        failures.append("stream_sweep_not_passed")
    if sweep.get("failures") not in ([], None):
        failures.append("stream_sweep_failures_not_empty")
    _check_safety(sweep, failures, prefix="stream_sweep")
    if sweep.get("event_timing_mode") != "token_index":
        failures.append("stream_sweep_event_timing_mode_not_token_index")
    if sweep.get("token_timing_enabled") is not True:
        failures.append("stream_sweep_token_timing_enabled_not_true")
    if sweep.get("lookahead_us_kind") != "requested_token_lead_us":
        failures.append("stream_sweep_lookahead_us_kind_mismatch")
    if sweep.get("issue_lead_token_values") != expected_lead_tokens:
        failures.append("stream_sweep_issue_lead_token_values_mismatch")
    rows = sweep.get("rows")
    lookahead_values = sweep.get("lookahead_us_values")
    if lookahead_values != expected_lookahead_values:
        failures.append("stream_sweep_lookahead_values_mismatch")
    if not isinstance(rows, list) or len(rows) != len(expected_lookahead_values):
        failures.append("stream_sweep_rows_count_mismatch")
        return
    for index, (row, expected_lookahead) in enumerate(zip(rows, expected_lookahead_values)):
        if not isinstance(row, dict):
            failures.append(f"stream_sweep_row_{index}_not_object")
            continue
        if row.get("lookahead_us") != expected_lookahead:
            failures.append(f"stream_sweep_row_{index}_lookahead_mismatch")
        if row.get("event_timing_mode") != "token_index":
            failures.append(f"stream_sweep_row_{index}_event_timing_mode_not_token_index")
        if row.get("token_timing_enabled") is not True:
            failures.append(f"stream_sweep_row_{index}_token_timing_enabled_not_true")
        if row.get("lookahead_us_kind") != "requested_token_lead_us":
            failures.append(f"stream_sweep_row_{index}_lookahead_us_kind_mismatch")
        if row.get("issue_lead_tokens") != expected_lead_tokens[index]:
            failures.append(f"stream_sweep_row_{index}_issue_lead_tokens_mismatch")
        _check_safety(row, failures, prefix=f"stream_sweep_row_{index}")
        model_passed = row.get("model_passed")
        safety_passed = row.get("safety_passed")
        safety_failures = row.get("safety_failures")
        row_passed = row.get("passed")
        if type(model_passed) is not bool:
            failures.append(f"stream_sweep_row_{index}_model_passed_invalid")
        if type(safety_passed) is not bool:
            failures.append(f"stream_sweep_row_{index}_safety_passed_invalid")
        if not isinstance(safety_failures, list):
            failures.append(f"stream_sweep_row_{index}_safety_failures_invalid")
            safety_failures = []
        if type(row_passed) is not bool:
            failures.append(f"stream_sweep_row_{index}_passed_invalid")
        elif (
            type(model_passed) is bool
            and type(safety_passed) is bool
            and row_passed is not (model_passed and safety_passed)
        ):
            failures.append(f"stream_sweep_row_{index}_passed_safety_mismatch")
        if safety_failures:
            failures.append(f"stream_sweep_row_{index}_safety_failures_not_empty")


def run_earlier_issue_lead_token_sweep(args: argparse.Namespace) -> dict[str, Any]:
    stream_sweep = _load_stream_sweep_module()
    output_path = _resolve(args.output_json)
    lead_tokens = _parse_nonnegative_ints(args.lead_token_values, label="lead token")
    decode_token_us = float(args.decode_token_us)
    if not math.isfinite(decode_token_us) or decode_token_us <= 0.0:
        raise ValueError("decode-token-us must be a positive finite number")
    layer_event_interval_us = float(getattr(args, "layer_event_interval_us", 1.0))
    allow_config_token_source = bool(
        getattr(args, "allow_config_token_source", False)
    )
    allow_empty_config_packets = bool(
        getattr(args, "allow_empty_config_packets", False)
    )
    event_timing_mode = str(getattr(args, "event_timing_mode", "token_index"))
    if event_timing_mode != "token_index":
        raise ValueError("event-timing-mode must be token_index for lead-token sweep")
    lookahead_values = [float(value) * decode_token_us for value in lead_tokens]
    lookahead_csv = ",".join(str(value) for value in lookahead_values)
    lead_token_csv = ",".join(str(value) for value in lead_tokens)
    temp_output = output_path.parent / f".{output_path.stem}.stream_sweep_tmp.json"
    sweep_args = stream_sweep.build_parser().parse_args(
        [
            "--online-canary-json",
            str(_resolve(args.online_canary_json)),
            "--measured-copy-json",
            str(_resolve(args.measured_copy_json)),
            "--measured-copy-stat",
            str(args.measured_copy_stat),
            "--measured-copy-experts",
            str(args.measured_copy_experts),
            "--measured-copy-pinned",
            str(args.measured_copy_pinned),
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
            "--layer-event-interval-us",
            str(layer_event_interval_us),
            "--issue-lead-token-values",
            lead_token_csv,
            "--issue-arrival-us",
            str(args.issue_arrival_us),
            "--lookahead-us-values",
            lookahead_csv,
            "--min-demand-hit-rate",
            str(args.min_demand_hit_rate),
            "--max-ready-late-miss-rate",
            str(args.max_ready_late_miss_rate),
            "--min-used-per-issued-fetch",
            str(args.min_used_per_issued_fetch),
            "--output-json",
            str(temp_output),
        ]
        + (["--allow-config-token-source"] if allow_config_token_source else [])
        + (["--allow-empty-config-packets"] if allow_empty_config_packets else [])
    )
    try:
        sweep = stream_sweep.run_stream_lookahead_sweep(sweep_args)
    finally:
        try:
            temp_output.unlink()
        except OSError:
            pass

    failures: list[str] = []
    _validate_stream_sweep(
        sweep,
        expected_lookahead_values=lookahead_values,
        expected_lead_tokens=lead_tokens,
        failures=failures,
    )
    rows: list[dict[str, Any]] = []
    first_model_passing_lead_tokens: int | None = None
    raw_rows = sweep.get("rows")
    if not isinstance(raw_rows, list):
        raw_rows = []
    for lead, expected_lookahead, row in zip(
        lead_tokens,
        lookahead_values,
        raw_rows,
    ):
        if not isinstance(row, dict):
            rows.append(
                {
                    "lead_tokens": int(lead),
                    "decode_token_us": decode_token_us,
                    "lookahead_us": expected_lookahead,
                    "model_passed": False,
                    "passed": False,
                    "malformed_row": True,
                }
            )
            continue
        row_model_passed = row.get("model_passed") is True
        if row_model_passed and first_model_passing_lead_tokens is None:
            first_model_passing_lead_tokens = int(lead)
        rows.append(
            {
                "lead_tokens": int(lead),
                "decode_token_us": decode_token_us,
                "lookahead_us": expected_lookahead,
                "effective_ready_deadline_us": row.get("effective_ready_deadline_us"),
                "model_passed": row_model_passed,
                "passed": bool(row.get("passed", False)),
                "demand_hit_rate": row.get("demand_hit_rate"),
                "ready_late_miss_rate": row.get("ready_late_miss_rate"),
                "used_per_issued_fetch": row.get("used_per_issued_fetch"),
                "full_fetch_allowed": row.get("full_fetch_allowed"),
                "full_fetch_block_reason": row.get("full_fetch_block_reason"),
                "payload_bytes": row.get("payload_bytes"),
                "payload_transfer_enabled": row.get("payload_transfer_enabled"),
                "kernel_arg_pass_allowed": row.get("kernel_arg_pass_allowed"),
                "passed_to_kernel": row.get("passed_to_kernel"),
                "measures_tpot": row.get("measures_tpot"),
                "measures_vllm_latency": row.get("measures_vllm_latency"),
            }
        )

    payload = {
        "artifact_kind": "premap_payload_cache_stream_earlier_issue_lead_token_sweep",
        "passed": first_model_passing_lead_tokens is not None and not failures,
        "failures": failures,
        "first_model_passing_lead_tokens": first_model_passing_lead_tokens,
        "first_model_passing_lookahead_us": (
            None
            if first_model_passing_lead_tokens is None
            else float(first_model_passing_lead_tokens) * decode_token_us
        ),
        "lead_token_values": lead_tokens,
        "decode_token_us": decode_token_us,
        "event_timing_mode": event_timing_mode,
        "token_timing_enabled": True,
        "lookahead_us_values": lookahead_values,
        "queue_deadline_us": float(args.queue_deadline_us),
        "layer_event_interval_us": layer_event_interval_us,
        "allow_config_token_source": allow_config_token_source,
        "allow_empty_config_packets": allow_empty_config_packets,
        "event_interval_us": float(args.event_interval_us),
        "issue_arrival_us": float(args.issue_arrival_us),
        "online_canary_json": str(_resolve(args.online_canary_json)),
        "measured_copy_json": str(_resolve(args.measured_copy_json)),
        "measured_copy_stat": str(args.measured_copy_stat),
        "measured_copy_experts": int(args.measured_copy_experts),
        "measured_copy_pinned": str(args.measured_copy_pinned),
        "capacity": int(args.capacity),
        "full_fetch_runtime_allowed": False,
        "full_fetch_allowed": False,
        "full_fetch_block_reason": (
            "real_payload_runtime_not_enabled"
            if first_model_passing_lead_tokens is not None
            else "insufficient_lead_tokens"
        ),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "rows": rows,
        "boundary": (
            "producer-side earlier issue lead-token model only; no payload movement, "
            "ready credit, kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": (
            "export_real_token_provenance_for_shifted_producer_replay"
            if first_model_passing_lead_tokens is not None
            else "increase_predictive_window_or_keep_full_fetch_blocked"
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    stream_sweep = _load_stream_sweep_module()
    stream_defaults = stream_sweep.build_parser().parse_args([])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online-canary-json",
        type=Path,
        default=stream_defaults.online_canary_json,
    )
    parser.add_argument(
        "--measured-copy-json",
        type=Path,
        default=stream_defaults.measured_copy_json,
    )
    parser.add_argument("--measured-copy-stat", default="p95")
    parser.add_argument("--measured-copy-experts", type=int, default=8)
    parser.add_argument("--measured-copy-pinned", default="true")
    parser.add_argument("--capacity", type=int, default=12288)
    parser.add_argument("--queue-deadline-us", type=float, default=200.0)
    parser.add_argument(
        "--layer-event-interval-us",
        type=float,
        default=stream_defaults.layer_event_interval_us,
    )
    parser.add_argument(
        "--allow-config-token-source",
        action="store_true",
        default=bool(stream_defaults.allow_config_token_source),
    )
    parser.add_argument(
        "--allow-empty-config-packets",
        action="store_true",
        default=bool(stream_defaults.allow_empty_config_packets),
    )
    parser.add_argument("--event-interval-us", type=float, default=1.0)
    parser.add_argument(
        "--event-timing-mode",
        choices=("token_index",),
        default="token_index",
        help=(
            "Lead-token sweep requires token-index provenance; packet-index "
            "timing is intentionally unsupported here."
        ),
    )
    parser.add_argument("--issue-arrival-us", type=float, default=0.0)
    parser.add_argument("--decode-token-us", type=float, default=75_000.0)
    parser.add_argument("--lead-token-values", default="0,1,2,3,4")
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.5)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.2)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.5)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_earlier_issue_lead_token_sweep(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
