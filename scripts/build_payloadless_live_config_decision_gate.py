#!/usr/bin/env python3
"""Build the payloadless live-config performance decision gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REPEAT_SUMMARY_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_ab_repeat3_summary_v1.json"
)
DEFAULT_HELDOUT_COMPARISON_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot_heldout32"
    / "future_wna16_typed_slot_payloadless_useful_ab_comparison_dolly32_heldout32_gen64_graph_v1.json"
)
DEFAULT_USEFUL_CONSUMER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_useful_consumer_entry_args_ptr_native_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "payloadless_live_config_performance_decision_gate_v1.json"
)

ARTIFACT_KIND = "payloadless_live_config_performance_decision_gate"
DECISION_NAME = "premap_payloadless_live_config_performance_decision_v1"
DECISION_MODE = "original_positive_heldout_negative_useful_consumer_ready"
NEXT_RUNTIME_STAGE = "focus_real_useful_consumer_or_payload_cache_manager_path"
NOOP_FALSE_FIELDS = (
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "current_wna16_arg_compatible",
    "requires_wna16_arg_reinterpretation",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _check_noop_boundary(payload: dict[str, Any], failures: list[str], *, prefix: str) -> None:
    if payload.get("payload_bytes") != 0:
        failures.append(f"{prefix}_payload_bytes_not_zero")
    for field in NOOP_FALSE_FIELDS:
        if payload.get(field) is not False:
            failures.append(f"{prefix}_{field}_not_false")


def _check_repeat_summary(payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    if payload.get("artifact_kind") != "future_wna16_typed_slot_payloadless_useful_ab_repeat_summary":
        failures.append("repeat_summary_artifact_kind_mismatch")
    if payload.get("passed") is not True:
        failures.append("repeat_summary_not_passed")
    if payload.get("failures") != []:
        failures.append("repeat_summary_failures_not_empty")
    if payload.get("positive_all_repeats") is not True:
        failures.append("repeat_summary_positive_all_repeats_not_true")
    repeat_count = payload.get("repeat_count")
    if not isinstance(repeat_count, int) or repeat_count < 3:
        failures.append("repeat_summary_repeat_count_invalid")
    speedup_stats = payload.get("speedup_stats")
    speedup_min = _finite_float(speedup_stats.get("min") if isinstance(speedup_stats, dict) else None)
    speedup_mean = _finite_float(speedup_stats.get("mean") if isinstance(speedup_stats, dict) else None)
    if speedup_min is None or speedup_min <= 1.0:
        failures.append("repeat_summary_speedup_min_not_positive")
    _check_noop_boundary(payload, failures, prefix="repeat_summary")
    return {
        "repeat_count": repeat_count,
        "speedup_min": speedup_min,
        "speedup_mean": speedup_mean,
        "performance_signal": "small_positive_original_split",
    }


def _path_contains(path_value: Any, needle: str) -> bool:
    return isinstance(path_value, str) and needle in path_value


def _check_heldout_comparison(
    payload: dict[str, Any],
    failures: list[str],
    *,
    artifact_path: Path,
) -> dict[str, Any]:
    if payload.get("artifact_kind") != "future_wna16_typed_slot_payloadless_useful_ab_comparison":
        failures.append("heldout_artifact_kind_mismatch")
    if payload.get("passed") is not False:
        failures.append("heldout_passed_not_false")
    if payload.get("comparison_ready") is not True:
        failures.append("heldout_comparison_ready_not_true")
    if payload.get("measures_tpot") is not True or payload.get("measures_vllm_latency") is not True:
        failures.append("heldout_measurement_flags_not_true")
    if payload.get("performance_claim_ready") is not False:
        failures.append("heldout_performance_claim_ready_not_false")
    if payload.get("candidate_faster") is not False:
        failures.append("heldout_candidate_faster_not_false")
    if payload.get("diagnostic_only") is not True:
        failures.append("heldout_diagnostic_only_not_true")
    failures_value = payload.get("failures")
    if not isinstance(failures_value, list) or "candidate_not_faster_than_baseline_diagnostic_only" not in failures_value:
        failures.append("heldout_expected_negative_failure_missing")
    speedup = _finite_float(payload.get("speedup_vs_baseline"))
    improvement = _finite_float(payload.get("improvement_pct"))
    if speedup is None or speedup >= 1.0:
        failures.append("heldout_speedup_not_negative")
    if improvement is None or improvement >= 0.0:
        failures.append("heldout_improvement_not_negative")
    if payload.get("expected_sample_count") != 32:
        failures.append("heldout_expected_sample_count_mismatch")
    if payload.get("expected_requested_output_token_count") != 2048:
        failures.append("heldout_expected_requested_output_token_count_mismatch")
    if str(payload.get("expected_gpu")) != "1":
        failures.append("heldout_expected_gpu_mismatch")
    if "heldout32" not in str(artifact_path):
        failures.append("heldout_artifact_path_not_heldout32")
    for field in ("baseline_json", "candidate_json"):
        if not _path_contains(payload.get(field), "heldout32"):
            failures.append(f"heldout_{field}_not_heldout32")
        if not _path_contains(payload.get(field), "production_like_tpot_heldout32"):
            failures.append(f"heldout_{field}_not_production_like_tpot_heldout32")
    _check_noop_boundary(payload, failures, prefix="heldout")
    return {
        "speedup": speedup,
        "improvement_pct": improvement,
        "performance_signal": "negative_heldout32",
    }


def _check_useful_consumer(payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    if payload.get("artifact_kind") != "future_wna16_typed_slot_kernel_variant_useful_consumer":
        failures.append("useful_artifact_kind_mismatch")
    if payload.get("passed") is not True:
        failures.append("useful_not_passed")
    if payload.get("failures") != []:
        failures.append("useful_failures_not_empty")
    if payload.get("useful_consumer_ready") is not True:
        failures.append("useful_consumer_ready_not_true")
    if payload.get("useful_consumer_native_stub_checked") is not True:
        failures.append("useful_native_stub_checked_not_true")
    if payload.get("measures_tpot") is not False or payload.get("measures_vllm_latency") is not False:
        failures.append("useful_measurement_flags_not_false")
    rows_consumed = payload.get("useful_consumer_rows_consumed")
    row_count = payload.get("row_count")
    if not isinstance(row_count, int) or row_count <= 0:
        failures.append("useful_row_count_invalid")
    if rows_consumed != row_count:
        failures.append("useful_rows_consumed_mismatch")
    expected_fields = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    if payload.get("useful_consumer_fields_consumed") != expected_fields:
        failures.append("useful_fields_consumed_mismatch")
    _check_noop_boundary(payload, failures, prefix="useful")
    return {
        "row_count": row_count,
        "rows_consumed": rows_consumed,
        "fields_consumed": payload.get("useful_consumer_fields_consumed"),
        "consumer_signal": "ready_but_not_tpot_measured",
    }


def build_decision(args: argparse.Namespace) -> dict[str, Any]:
    repeat_path = _resolve(args.repeat_summary_json)
    heldout_path = _resolve(args.heldout_comparison_json)
    useful_path = _resolve(args.useful_consumer_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    try:
        repeat = _load_json(repeat_path)
    except Exception as exc:
        repeat = {}
        failures.append(f"repeat_summary_load_failed:{exc.__class__.__name__}:{exc}")
    try:
        heldout = _load_json(heldout_path)
    except Exception as exc:
        heldout = {}
        failures.append(f"heldout_comparison_load_failed:{exc.__class__.__name__}:{exc}")
    try:
        useful = _load_json(useful_path)
    except Exception as exc:
        useful = {}
        failures.append(f"useful_consumer_load_failed:{exc.__class__.__name__}:{exc}")

    repeat_summary = _check_repeat_summary(repeat, failures) if repeat else {}
    heldout_summary = (
        _check_heldout_comparison(heldout, failures, artifact_path=heldout_path)
        if heldout
        else {}
    )
    useful_summary = _check_useful_consumer(useful, failures) if useful else {}
    passed = not failures
    freeze_live_config_performance = bool(
        passed
        and repeat_summary.get("speedup_min", 0.0) > 1.0
        and heldout_summary.get("speedup", 1.0) < 1.0
    )
    report = {
        "artifact_kind": ARTIFACT_KIND,
        "decision_name": DECISION_NAME,
        "decision_mode": DECISION_MODE,
        "passed": passed,
        "failures": failures,
        "repeat_summary_json": str(repeat_path),
        "repeat_summary_sha256": _sha256(repeat_path) if repeat_path.exists() else None,
        "heldout_comparison_json": str(heldout_path),
        "heldout_comparison_sha256": _sha256(heldout_path) if heldout_path.exists() else None,
        "useful_consumer_json": str(useful_path),
        "useful_consumer_sha256": _sha256(useful_path) if useful_path.exists() else None,
        "repeat_summary": repeat_summary,
        "heldout_summary": heldout_summary,
        "useful_consumer_summary": useful_summary,
        "freeze_payloadless_live_config_performance_claim": freeze_live_config_performance,
        "payloadless_live_config_status": (
            "safe_participation_path_not_performance_mainline"
            if freeze_live_config_performance
            else "decision_not_ready"
        ),
        "real_performance_next_path": (
            "future_typed_slot_useful_consumer_or_payload_cache_manager"
            if freeze_live_config_performance
            else "fix_decision_inputs"
        ),
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
            "Decision gate only.  It freezes the payloadless live-config path as "
            "safe/participation evidence when heldout TPOT is negative.  It is "
            "not a speedup claim and does not pass kernel arguments."
        ),
        "next_runtime_stage": NEXT_RUNTIME_STAGE if passed else "fix_payloadless_decision_gate",
    }
    _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(1)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat-summary-json", default=str(DEFAULT_REPEAT_SUMMARY_JSON))
    parser.add_argument("--heldout-comparison-json", default=str(DEFAULT_HELDOUT_COMPARISON_JSON))
    parser.add_argument("--useful-consumer-json", default=str(DEFAULT_USEFUL_CONSUMER_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_decision(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
