#!/usr/bin/env python3
"""Build a payloadless-useful benchmark harness readiness artifact.

This is a harness gate for the independent typed-slot native-stub path.  It is
not a current WNA16 fused-MoE benchmark, does not measure vLLM TPOT, and does
not pass or reinterpret existing WNA16 kernel arguments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_RUNTIME_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_runtime_gate_entry_args_ptr_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_benchmark_harness_entry_args_ptr_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_benchmark_harness"
HARNESS_NAME = "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1"
HARNESS_MODE = "independent_payloadless_useful_native_stub_benchmark_harness"
HARNESS_SOURCE = "premap_future_wna16_typed_slot_payloadless_useful_runtime_gate_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_payloadless_useful_repeat_benchmark"
FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
USEFUL_WORK_KIND = "native_typed_slot_four_field_row_projection"
EXPECTED_RUNTIME_GATE_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_payloadless_useful_runtime_gate",
    "runtime_gate_name": "premap_future_wna16_typed_slot_payloadless_useful_runtime_gate_v1",
    "runtime_gate_mode": "readonly_payloadless_useful_runtime_gate",
    "runtime_gate_source": "premap_lab_preflight_payloadless_useful_execution_gate",
    "passed": True,
    "runtime_gate_ready": True,
    "payloadless_useful_runtime_gate_ready": True,
    "payloadless_useful_execution_gate_ready": True,
    "benchmark_is_current_wna16_fused_moe": False,
    "measures_vllm_latency": False,
    "measures_tpot": False,
    "wna16_benchmark_ready": False,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
    "payload_bytes": 0,
    "payload_deref_allowed": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "next_runtime_stage": "implement_future_wna16_typed_slot_payloadless_useful_benchmark_harness",
}
EXPECTED_TIMING_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
    "passed": True,
    "timing_stub_ready": True,
    "native_stub_requested": True,
    "native_stub_executed": True,
    "native_stub_passed": True,
    "measures_native_stub_host_wall_time": True,
    "measures_vllm_latency": False,
    "measures_tpot": False,
    "wna16_benchmark_ready": False,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
    "payload_bytes": 0,
    "payload_deref_allowed": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
}
EXPECTED_STUB_FLAGS: dict[str, Any] = {
    "passed": True,
    "payload_bytes": 0,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "wna16_side_consumer_variant_execution_checked": True,
    "wna16_side_consumer_variant_execution_error_count": 0,
    "wna16_side_consumer_variant_execution_payload_bytes": 0,
    "wna16_side_consumer_variant_execution_payload_deref_allowed": False,
    "wna16_side_consumer_variant_execution_kernel_arg_pass_allowed": False,
    "wna16_side_consumer_variant_execution_passed_to_kernel": False,
    "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
    "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
    "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
    "wna16_side_consumer_variant_execution_explicit_typed_abi_slot": True,
    "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
}
OPTIONAL_STUB_SAFETY_FLAGS: dict[str, Any] = {
    "payload_deref_allowed": False,
    "kernel_arg_pass_allowed": False,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
}


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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _numeric_ms(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if value > 0 else None


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 <= parsed <= 0xFFFFFFFFFFFFFFFF


def _check_expected_flags(
    payload: dict[str, Any],
    failures: list[str],
    *,
    label: str,
    expected: dict[str, Any],
) -> None:
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"{label}_{key}_mismatch")


def _check_field_coverage(
    payload: dict[str, Any],
    failures: list[str],
    *,
    label: str,
    row_count: int | None,
    row_counts_key: str = "field_read_row_ok_counts",
    hashes_key: str = "field_read_hashes",
    require_row_counts: bool = True,
) -> dict[str, str]:
    if payload.get("field_names") != list(FIELDS):
        failures.append(f"{label}_field_names_mismatch")
    row_counts = payload.get(row_counts_key)
    hashes = payload.get(hashes_key)
    if require_row_counts and not isinstance(row_counts, dict):
        failures.append(f"{label}_{row_counts_key}_missing")
        row_counts = {}
    if not isinstance(hashes, dict):
        failures.append(f"{label}_{hashes_key}_missing")
        hashes = {}
    valid_hashes: dict[str, str] = {}
    for field in FIELDS:
        if (
            require_row_counts
            and row_count is not None
            and _int_metric(row_counts, field) != row_count
        ):
            failures.append(f"{label}_{field}_row_ok_count_mismatch")
        field_hash = hashes.get(field)
        if not _is_hex_u64(field_hash):
            failures.append(f"{label}_{field}_hash_invalid")
        else:
            valid_hashes[field] = field_hash
    return valid_hashes


def _check_optional_expected_flags(
    payload: dict[str, Any],
    failures: list[str],
    *,
    label: str,
    expected: dict[str, Any],
) -> None:
    for key, expected_value in expected.items():
        if key in payload and payload.get(key) != expected_value:
            failures.append(f"{label}_{key}_mismatch")


def run_payloadless_useful_benchmark_harness(
    args: argparse.Namespace,
) -> dict[str, Any]:
    runtime_gate_path = _resolve(args.runtime_gate_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    try:
        runtime_gate = _load_json(runtime_gate_path)
    except Exception as exc:
        runtime_gate = {}
        failures.append(f"runtime_gate_load_failed:{exc.__class__.__name__}:{exc}")

    _check_expected_flags(
        runtime_gate,
        failures,
        label="runtime_gate",
        expected=EXPECTED_RUNTIME_GATE_FLAGS,
    )
    if runtime_gate.get("failures") != []:
        failures.append("runtime_gate_failures_not_empty")

    runtime_gate_sha = _sha256(runtime_gate_path) if runtime_gate_path.exists() else None
    source_count = _int_metric(runtime_gate, "source_count")
    row_count = _int_metric(runtime_gate, "row_count")
    row_ok_count = _int_metric(runtime_gate, "row_ok_count")
    rows_consumed = _int_metric(runtime_gate, "rows_consumed")
    if source_count is None or source_count < args.min_source_count:
        failures.append("runtime_gate_source_count_invalid")
    if row_count is None or row_count < args.min_row_count:
        failures.append("runtime_gate_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("runtime_gate_row_ok_count_mismatch")
    if row_count is not None and rows_consumed != row_count:
        failures.append("runtime_gate_rows_consumed_mismatch")
    field_count = _int_metric(runtime_gate, "field_count")
    fields_per_row = _int_metric(runtime_gate, "fields_per_row")
    useful_work_units = _int_metric(runtime_gate, "useful_work_units")
    expected_useful_work_units = _int_metric(
        runtime_gate,
        "expected_useful_work_units",
    )
    expected_units = int(row_count or 0) * len(FIELDS)
    if field_count != len(FIELDS):
        failures.append("runtime_gate_field_count_mismatch")
    if fields_per_row != len(FIELDS):
        failures.append("runtime_gate_fields_per_row_mismatch")
    if expected_useful_work_units != expected_units:
        failures.append("runtime_gate_expected_useful_work_units_mismatch")
    if useful_work_units != expected_useful_work_units:
        failures.append("runtime_gate_useful_work_units_mismatch")
    if useful_work_units is None or useful_work_units <= 0:
        failures.append("runtime_gate_useful_work_units_not_positive")
    if runtime_gate.get("useful_work_coverage") != 1.0:
        failures.append("runtime_gate_useful_work_coverage_mismatch")
    if runtime_gate.get("useful_work_kind") != USEFUL_WORK_KIND:
        failures.append("runtime_gate_useful_work_kind_mismatch")
    if runtime_gate.get("native_consumer_has_useful_work") is not True:
        failures.append("runtime_gate_native_consumer_has_useful_work_mismatch")
    runtime_field_hashes = _check_field_coverage(
        runtime_gate,
        failures,
        label="runtime_gate",
        row_count=row_count,
        require_row_counts=False,
    )

    timing_path_value = runtime_gate.get("native_timing_json")
    timing: dict[str, Any] = {}
    if not isinstance(timing_path_value, str) or not timing_path_value:
        timing_path = None
        failures.append("native_timing_json_missing")
    else:
        timing_path = _resolve(timing_path_value)
    if timing_path is not None and not timing_path.exists():
        failures.append("native_timing_json_missing")
    elif timing_path is not None:
        timing_sha = _sha256(timing_path)
        if timing_sha != runtime_gate.get("native_timing_sha256"):
            failures.append("native_timing_sha256_mismatch")
        timing = _load_json(timing_path)
        _check_expected_flags(
            timing,
            failures,
            label="timing",
            expected=EXPECTED_TIMING_FLAGS,
        )
        if timing.get("failures") != []:
            failures.append("timing_failures_not_empty")
        timing_stub_path = timing.get("native_stub_output_json")
        timing_stub_sha = timing.get("native_stub_output_sha256")
        if not isinstance(timing_stub_path, str) or not timing_stub_path:
            failures.append("timing_native_stub_output_json_missing")
        elif _resolve(timing_stub_path).resolve() != _resolve(
            runtime_gate.get("native_stub_json", "")
        ).resolve():
            failures.append("timing_native_stub_output_json_mismatch")
        if timing_stub_sha != runtime_gate.get("native_stub_sha256"):
            failures.append("timing_native_stub_output_sha256_mismatch")
    timing_host_wall_ms = _numeric_ms(timing, "native_stub_host_wall_ms")
    if timing_host_wall_ms is None:
        failures.append("native_stub_host_wall_ms_invalid")
    if source_count is not None and _int_metric(timing, "source_count") != source_count:
        failures.append("timing_source_count_mismatch")
    if row_count is not None and _int_metric(timing, "row_count") != row_count:
        failures.append("timing_row_count_mismatch")
    timing_field_hashes = _check_field_coverage(
        timing,
        failures,
        label="timing",
        row_count=row_count,
    )
    if runtime_field_hashes and timing_field_hashes != runtime_field_hashes:
        failures.append("runtime_timing_field_hashes_mismatch")

    stub_path_value = runtime_gate.get("native_stub_json")
    stub: dict[str, Any] = {}
    if not isinstance(stub_path_value, str) or not stub_path_value:
        stub_path = None
        failures.append("native_stub_json_missing")
    else:
        stub_path = _resolve(stub_path_value)
    if stub_path is not None and not stub_path.exists():
        failures.append("native_stub_json_missing")
    elif stub_path is not None:
        stub_sha = _sha256(stub_path)
        if stub_sha != runtime_gate.get("native_stub_sha256"):
            failures.append("native_stub_sha256_mismatch")
        stub = _load_json(stub_path)
        _check_expected_flags(
            stub,
            failures,
            label="stub",
            expected=EXPECTED_STUB_FLAGS,
        )
        _check_optional_expected_flags(
            stub,
            failures,
            label="stub",
            expected=OPTIONAL_STUB_SAFETY_FLAGS,
        )
        if stub.get("failures") != []:
            failures.append("stub_failures_not_empty")

    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "harness_name": HARNESS_NAME,
        "harness_mode": HARNESS_MODE,
        "harness_source": HARNESS_SOURCE,
        "passed": passed,
        "failures": failures,
        "runtime_gate_json": str(runtime_gate_path),
        "runtime_gate_sha256": runtime_gate_sha,
        "native_timing_json": str(timing_path) if timing_path is not None else None,
        "native_timing_sha256": runtime_gate.get("native_timing_sha256"),
        "native_stub_json": str(stub_path) if stub_path is not None else None,
        "native_stub_sha256": runtime_gate.get("native_stub_sha256"),
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_ok_count,
        "rows_consumed": rows_consumed,
        "field_count": field_count,
        "fields_per_row": fields_per_row,
        "useful_work_units": useful_work_units,
        "expected_useful_work_units": expected_useful_work_units,
        "useful_work_coverage": runtime_gate.get("useful_work_coverage"),
        "useful_work_kind": runtime_gate.get("useful_work_kind"),
        "native_consumer_has_useful_work": runtime_gate.get(
            "native_consumer_has_useful_work",
        ),
        "field_names": list(FIELDS),
        "field_read_hashes": runtime_field_hashes,
        "native_stub_host_wall_ms": timing_host_wall_ms,
        "payloadless_useful_benchmark_harness_ready": passed,
        "benchmark_harness_ready": passed,
        "benchmark_harness_kind": "future_payloadless_useful_typed_slot_native_stub_harness",
        "measures_native_stub_host_wall_time": timing_host_wall_ms is not None,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot payloadless useful benchmark harness failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-gate-json", default=str(DEFAULT_RUNTIME_GATE_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_payloadless_useful_benchmark_harness(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
