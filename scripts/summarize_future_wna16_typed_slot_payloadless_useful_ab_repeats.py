#!/usr/bin/env python3
"""Summarize repeated payloadless live-config TPOT A/B comparisons."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUTS = [
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_ab_comparison_blocked_by_decision_gate_v2.json",
]
DEFAULT_DECISION_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "payloadless_live_config_performance_decision_gate_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_ab_repeat_summary_blocked_by_decision_gate_v2.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_ab_repeat_summary"
SUMMARY_NAME = "premap_future_wna16_typed_slot_payloadless_useful_ab_repeat3_summary_v1"
SUMMARY_MODE = "production_like_payloadless_live_config_vs_no_recorder_baseline_repeat_summary"
NEXT_RUNTIME_STAGE = "decide_payloadless_live_config_gate_or_promote_real_typed_slot_consumer"
COMPARISON_KIND = "future_wna16_typed_slot_payloadless_useful_ab_comparison"
EXPECTED_GPU = 1
EXPECTED_SAMPLE_COUNT = 32
EXPECTED_REQUESTED_OUTPUT_TOKEN_COUNT = 2048


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    if isinstance(value, str) and str(parsed) != value:
        return None
    return parsed


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "values": [],
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "stdev": None,
        }
    ordered = sorted(values)
    return {
        "count": len(values),
        "values": values,
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "sorted": ordered,
    }


def _check_comparison(path: Path, payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    prefix = path.name
    if payload.get("artifact_kind") != COMPARISON_KIND:
        failures.append(f"{prefix}:artifact_kind_mismatch")
    for key in (
        "passed",
        "comparison_ready",
        "measures_tpot",
        "measures_vllm_latency",
        "performance_claim_ready",
        "candidate_faster",
    ):
        if payload.get(key) is not True:
            failures.append(f"{prefix}:{key}_not_true")
    if payload.get("failures") != []:
        failures.append(f"{prefix}:failures_not_empty")
    payload_bytes = _optional_int(payload.get("payload_bytes"))
    if payload_bytes != 0:
        failures.append(f"{prefix}:payload_bytes_not_zero")
    for key in (
        "payload_deref_allowed",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "current_wna16_arg_compatible",
        "requires_wna16_arg_reinterpretation",
    ):
        if payload.get(key) is not False:
            failures.append(f"{prefix}:{key}_not_false")
    baseline_tpot = _finite_float(payload.get("baseline_tpot"))
    candidate_tpot = _finite_float(payload.get("candidate_tpot"))
    speedup = _finite_float(payload.get("speedup_vs_baseline"))
    improvement = _finite_float(payload.get("improvement_pct"))
    if baseline_tpot is None or baseline_tpot <= 0:
        failures.append(f"{prefix}:baseline_tpot_invalid")
    if candidate_tpot is None or candidate_tpot <= 0:
        failures.append(f"{prefix}:candidate_tpot_invalid")
    if speedup is None or speedup <= 1.0:
        failures.append(f"{prefix}:speedup_not_positive")
    if improvement is None or improvement <= 0.0:
        failures.append(f"{prefix}:improvement_not_positive")
    if baseline_tpot and candidate_tpot and speedup:
        expected = baseline_tpot / candidate_tpot
        if not math.isclose(speedup, expected, rel_tol=1.0e-12, abs_tol=1.0e-12):
            failures.append(f"{prefix}:speedup_mismatch")
    expected_gpu = _optional_int(payload.get("expected_gpu"))
    expected_sample_count = _optional_int(payload.get("expected_sample_count"))
    expected_output_tokens = _optional_int(payload.get("expected_requested_output_token_count"))
    if expected_gpu != EXPECTED_GPU:
        failures.append(f"{prefix}:expected_gpu_mismatch")
    if expected_sample_count != EXPECTED_SAMPLE_COUNT:
        failures.append(f"{prefix}:expected_sample_count_mismatch")
    if expected_output_tokens != EXPECTED_REQUESTED_OUTPUT_TOKEN_COUNT:
        failures.append(f"{prefix}:expected_requested_output_token_count_mismatch")
    baseline = payload.get("baseline") or {}
    candidate = payload.get("candidate") or {}
    return {
        "path": str(path),
        "baseline_tpot": baseline_tpot,
        "candidate_tpot": candidate_tpot,
        "speedup": speedup,
        "improvement_pct": improvement,
        "payload_bytes": payload_bytes,
        "expected_gpu": expected_gpu,
        "expected_sample_count": expected_sample_count,
        "expected_requested_output_token_count": expected_output_tokens,
        "baseline_json": payload.get("baseline_json"),
        "candidate_json": payload.get("candidate_json"),
        "baseline_sha256": payload.get("baseline_sha256"),
        "candidate_sha256": payload.get("candidate_sha256"),
        "baseline_trace_dir": baseline.get("trace_dir"),
        "candidate_trace_dir": candidate.get("trace_dir"),
    }


def _check_decision_gate(payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    expected = {
        "artifact_kind": "payloadless_live_config_performance_decision_gate",
        "decision_name": "premap_payloadless_live_config_performance_decision_v1",
        "passed": True,
        "failures": [],
        "freeze_payloadless_live_config_performance_claim": True,
        "payloadless_live_config_status": "safe_participation_path_not_performance_mainline",
        "real_performance_next_path": "future_typed_slot_useful_consumer_or_payload_cache_manager",
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"decision_gate_{key}_mismatch")
    if payload.get("freeze_payloadless_live_config_performance_claim") is True:
        failures.append("payloadless_repeat_summary_blocked_by_decision_gate")
    return {
        "freeze_payloadless_live_config_performance_claim": payload.get(
            "freeze_payloadless_live_config_performance_claim"
        ),
        "payloadless_live_config_status": payload.get("payloadless_live_config_status"),
        "real_performance_next_path": payload.get("real_performance_next_path"),
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    output_path = _resolve(args.output_json)
    paths = [_resolve(path) for path in args.inputs]
    decision_gate_path = _resolve(args.decision_gate_json)
    failures: list[str] = []
    try:
        decision_gate = _load_json(decision_gate_path)
    except Exception as exc:
        decision_gate = {}
        failures.append(f"decision_gate_load_failed:{exc.__class__.__name__}:{exc}")
    decision_summary = _check_decision_gate(decision_gate, failures)
    if len(set(paths)) != len(paths):
        failures.append("duplicate_input_paths")
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            failures.append(f"{path.name}:missing")
            continue
        try:
            payload = _load_json(path)
        except Exception as exc:
            failures.append(f"{path.name}:load_failed:{exc.__class__.__name__}:{exc}")
            continue
        rows.append(_check_comparison(path, payload, failures))

    min_repeats = int(args.min_repeats)
    if len(rows) < min_repeats:
        failures.append("insufficient_repeat_count")
    for field in (
        "baseline_trace_dir",
        "candidate_trace_dir",
        "baseline_json",
        "candidate_json",
        "baseline_sha256",
        "candidate_sha256",
    ):
        values = [row.get(field) for row in rows]
        if any(not value for value in values):
            failures.append(f"{field}_missing")
        elif len(set(values)) != len(values):
            failures.append(f"{field}_not_unique")
    speedups = [row["speedup"] for row in rows if isinstance(row.get("speedup"), float)]
    improvements = [
        row["improvement_pct"]
        for row in rows
        if isinstance(row.get("improvement_pct"), float)
    ]
    positive_all = bool(len(speedups) >= min_repeats and all(value > 1.0 for value in speedups))
    if not positive_all:
        failures.append("not_positive_all_repeats")

    passed = not failures
    result = {
        "artifact_kind": ARTIFACT_KIND,
        "summary_name": SUMMARY_NAME,
        "summary_mode": SUMMARY_MODE,
        "passed": passed,
        "failures": failures,
        "repeat_count": len(rows),
        "min_repeats": min_repeats,
        "positive_all_repeats": positive_all,
        "performance_claim_ready": False,
        "decision_gate_json": str(decision_gate_path),
        "decision_summary": decision_summary,
        "payloadless_live_config_performance_claim_frozen": decision_summary.get(
            "freeze_payloadless_live_config_performance_claim"
        ),
        "payloadless_repeat_summary_allowed": False,
        "rows": rows,
        "speedup_stats": _stats(speedups),
        "improvement_pct_stats": _stats(improvements),
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "claim_boundary": (
            "Blocked repeat summary for the payloadless live-config path. This "
            "is not a performance claim, not a real WNA16 typed-slot kernel "
            "benchmark, and does not pass or mutate kernel arguments."
        ),
        "next_runtime_stage": (
            decision_summary.get("real_performance_next_path")
            if decision_summary.get("freeze_payloadless_live_config_performance_claim") is True
            else NEXT_RUNTIME_STAGE
        ),
    }
    _write_json(output_path, result)
    if args.require_pass and not passed:
        raise SystemExit(1)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", default=[str(path) for path in DEFAULT_INPUTS])
    parser.add_argument("--decision-gate-json", default=str(DEFAULT_DECISION_GATE_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-repeats", type=int, default=3)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_summary(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
