#!/usr/bin/env python3
"""Ablate the payloadless useful typed-slot native-stub repeat benchmark.

This gate consumes the explicit repeat benchmark artifact and checks whether the
independent native typed-slot stub is stable enough to justify the next
production-like vLLM timing experiment.  It is still payloadless: it does not
pass current WNA16 kernel arguments, does not dereference payloads, and does not
measure vLLM TPOT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_REPEAT_BENCHMARK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_entry_args_ptr_repeat3_gpu1_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_runtime_ablation_entry_args_ptr_repeat3_gpu1_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_runtime_ablation"
ABLATION_NAME = "premap_future_wna16_typed_slot_payloadless_useful_runtime_ablation_v1"
ABLATION_MODE = "payloadless_useful_native_stub_repeat_stability_ablation"
ABLATION_SOURCE = "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_payloadless_useful_production_like_timing"
FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
EXPECTED_REPEAT_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_payloadless_useful_repeat_benchmark",
    "benchmark_name": "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1",
    "benchmark_mode": "payloadless_useful_native_stub_repeat_benchmark",
    "benchmark_source": "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1",
    "benchmark_scope": "payloadless_useful_independent_native_stub_host_wall",
    "measurement_source": "repeated_independent_native_typed_slot_timing_stub",
    "passed": True,
    "failures": [],
    "payloadless_useful_repeat_benchmark_ready": True,
    "seed_only": False,
    "benchmark_is_current_wna16_fused_moe": False,
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
    "next_runtime_stage": "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation",
}
EXPECTED_HARNESS_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_payloadless_useful_benchmark_harness",
    "harness_name": "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1",
    "harness_mode": "independent_payloadless_useful_native_stub_benchmark_harness",
    "harness_source": "premap_future_wna16_typed_slot_payloadless_useful_runtime_gate_v1",
    "passed": True,
    "failures": [],
    "payloadless_useful_benchmark_harness_ready": True,
    "benchmark_harness_ready": True,
}
EXPECTED_TIMING_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
    "timing_stub_name": "premap_future_wna16_typed_slot_kernel_timing_stub_v1",
    "timing_stub_mode": "independent_future_wna16_typed_slot_native_stub_timing",
    "timing_stub_source": "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1",
    "passed": True,
    "failures": [],
    "timing_stub_ready": True,
    "native_stub_requested": True,
    "native_stub_executed": True,
    "native_stub_passed": True,
    "measures_native_stub_host_wall_time": True,
}
EXPECTED_NOOP_FLAGS: dict[str, Any] = {
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
}
EXPECTED_STUB_FLAGS: dict[str, Any] = {
    "passed": True,
    "failures": [],
    "payload_bytes": 0,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "wna16_side_consumer_variant_execution_payload_bytes": 0,
    "wna16_side_consumer_variant_execution_payload_deref_allowed": False,
    "wna16_side_consumer_variant_execution_kernel_arg_pass_allowed": False,
    "wna16_side_consumer_variant_execution_passed_to_kernel": False,
    "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
    "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
    "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
    "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
    "wna16_side_consumer_variant_execution_error_count": 0,
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


def _numeric_ms(value: Any) -> float | None:
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


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_expected_flags(
    payload: dict[str, Any],
    failures: list[str],
    *,
    expected: dict[str, Any],
    label: str,
) -> None:
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"{label}_{key}_mismatch")


def _load_bound_child(
    payload: dict[str, Any],
    failures: list[str],
    *,
    path_key: str,
    sha_key: str,
    label: str,
) -> dict[str, Any]:
    path_value = payload.get(path_key)
    sha_value = payload.get(sha_key)
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{label}_{path_key}_missing")
        return {}
    child_path = _resolve(path_value)
    if not child_path.exists():
        failures.append(f"{label}_{path_key}_missing")
        return {}
    if _sha256(child_path) != sha_value:
        failures.append(f"{label}_{sha_key}_mismatch")
        return {}
    try:
        return _load_json(child_path)
    except Exception as exc:
        failures.append(f"{label}_load_failed:{exc.__class__.__name__}:{exc}")
        return {}


def _check_noop(payload: dict[str, Any], failures: list[str], *, label: str) -> None:
    for key, expected in EXPECTED_NOOP_FLAGS.items():
        if key in payload and payload.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")


def _check_field_hashes(
    payload: dict[str, Any],
    failures: list[str],
    *,
    label: str,
    expected_hashes: dict[str, Any],
    row_count: int | None,
) -> None:
    if payload.get("field_names") != list(FIELDS):
        failures.append(f"{label}_field_names_mismatch")
    hashes = payload.get("field_read_hashes")
    if not isinstance(hashes, dict):
        failures.append(f"{label}_field_read_hashes_missing")
        hashes = {}
    for field in FIELDS:
        if hashes.get(field) != expected_hashes.get(field):
            failures.append(f"{label}_{field}_field_hash_mismatch")
    if row_count is not None:
        for key in ("row_count", "row_ok_count"):
            if _int_metric(payload, key) != row_count:
                failures.append(f"{label}_{key}_mismatch")


def _check_native_stub(
    stub: dict[str, Any],
    failures: list[str],
    *,
    label: str,
    row_count: int | None,
) -> None:
    for key, expected in EXPECTED_STUB_FLAGS.items():
        if stub.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    if row_count is not None:
        if _int_metric(stub, "wna16_side_consumer_variant_execution_row_count") != row_count:
            failures.append(f"{label}_wna16_row_count_mismatch")
        if _int_metric(stub, "wna16_side_consumer_variant_execution_row_ok_count") != row_count:
            failures.append(f"{label}_wna16_row_ok_count_mismatch")
        for field in FIELDS:
            prefix = f"wna16_side_consumer_variant_execution_{field}_read"
            if _int_metric(stub, f"{prefix}_row_count") != row_count:
                failures.append(f"{label}_{field}_row_count_mismatch")
            if _int_metric(stub, f"{prefix}_row_ok_count") != row_count:
                failures.append(f"{label}_{field}_row_ok_count_mismatch")
            if _int_metric(stub, f"{prefix}_error_count") != 0:
                failures.append(f"{label}_{field}_error_count_mismatch")
            if not _is_hex_u64(stub.get(f"{prefix}_hash_accumulator")):
                failures.append(f"{label}_{field}_hash_invalid")


def _check_timing_artifact(
    timing: dict[str, Any],
    failures: list[str],
    *,
    label: str,
    repeat: dict[str, Any],
    expected_wall_ms: float | None,
    row_count: int | None,
) -> None:
    _check_expected_flags(timing, failures, expected=EXPECTED_TIMING_FLAGS, label=label)
    _check_noop(timing, failures, label=label)
    expected_hashes = repeat.get("field_read_hashes")
    if not isinstance(expected_hashes, dict):
        expected_hashes = {}
    _check_field_hashes(
        timing,
        failures,
        label=label,
        expected_hashes=expected_hashes,
        row_count=row_count,
    )
    if expected_wall_ms is not None and timing.get("native_stub_host_wall_ms") != expected_wall_ms:
        failures.append(f"{label}_native_stub_host_wall_ms_mismatch")
    stub = _load_bound_child(
        timing,
        failures,
        path_key="native_stub_output_json",
        sha_key="native_stub_output_sha256",
        label=f"{label}_native_stub",
    )
    if stub:
        _check_native_stub(stub, failures, label=f"{label}_native_stub", row_count=row_count)


def _stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "min_ms": 0.0,
            "median_ms": 0.0,
            "mean_ms": 0.0,
            "max_ms": 0.0,
            "stdev_ms": 0.0,
            "relative_range": 0.0,
            "coefficient_of_variation": 0.0,
        }
    mean = float(statistics.fmean(values))
    median = float(statistics.median(values))
    stdev = float(statistics.stdev(values)) if len(values) > 1 else 0.0
    relative_range = ((max(values) - min(values)) / median) if median > 0 else 0.0
    coefficient_of_variation = stdev / mean if mean > 0 else 0.0
    return {
        "count": len(values),
        "min_ms": float(min(values)),
        "median_ms": median,
        "mean_ms": mean,
        "max_ms": float(max(values)),
        "stdev_ms": stdev,
        "relative_range": float(relative_range),
        "coefficient_of_variation": float(coefficient_of_variation),
    }


def _check_repeat_children(
    repeat: dict[str, Any],
    failures: list[str],
    *,
    root: Path,
    expected_count: int,
    expected_values: list[float],
) -> None:
    repeat_jsons = repeat.get("repeat_output_jsons")
    repeat_sha256s = repeat.get("repeat_output_sha256s")
    if not isinstance(repeat_jsons, list):
        failures.append("repeat_output_jsons_missing")
        repeat_jsons = []
    if not isinstance(repeat_sha256s, list):
        failures.append("repeat_output_sha256s_missing")
        repeat_sha256s = []
    if len(repeat_jsons) != expected_count:
        failures.append("repeat_output_jsons_count_mismatch")
    if len(repeat_sha256s) != expected_count:
        failures.append("repeat_output_sha256s_count_mismatch")
    for idx, child_path_value in enumerate(repeat_jsons):
        child_sha = repeat_sha256s[idx] if idx < len(repeat_sha256s) else None
        if not isinstance(child_path_value, str) or not child_path_value:
            failures.append(f"repeat_{idx}_json_missing")
            continue
        child_path = _resolve(child_path_value)
        if not child_path.exists():
            failures.append(f"repeat_{idx}_json_missing")
            continue
        if _sha256(child_path) != child_sha:
            failures.append(f"repeat_{idx}_sha256_mismatch")
            continue
        try:
            child = _load_json(child_path)
        except Exception as exc:
            failures.append(f"repeat_{idx}_load_failed:{exc.__class__.__name__}:{exc}")
            continue
        child_required_noop = {
            key: value
            for key, value in EXPECTED_NOOP_FLAGS.items()
            if key != "benchmark_is_current_wna16_fused_moe"
        }
        for key, expected in {**EXPECTED_TIMING_FLAGS, **child_required_noop}.items():
            if child.get(key) != expected:
                failures.append(f"repeat_{idx}_{key}_mismatch")
        if child.get("field_read_hashes") != repeat.get("field_read_hashes"):
            failures.append(f"repeat_{idx}_field_hashes_mismatch")
        for key in ("source_count", "row_count", "row_ok_count"):
            if child.get(key) != repeat.get(key):
                failures.append(f"repeat_{idx}_{key}_mismatch")
        expected_wall = expected_values[idx] if idx < len(expected_values) else None
        if expected_wall is not None and child.get("native_stub_host_wall_ms") != expected_wall:
            failures.append(f"repeat_{idx}_native_stub_host_wall_ms_mismatch")
        _check_timing_artifact(
            child,
            failures,
            label=f"repeat_{idx}",
            repeat=repeat,
            expected_wall_ms=expected_wall,
            row_count=_int_metric(repeat, "row_count"),
        )


def run_payloadless_useful_runtime_ablation(args: argparse.Namespace) -> dict[str, Any]:
    repeat_path = _resolve(args.repeat_benchmark_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    try:
        repeat = _load_json(repeat_path)
    except Exception as exc:
        repeat = {}
        failures.append(f"repeat_benchmark_load_failed:{exc.__class__.__name__}:{exc}")

    _check_expected_flags(
        repeat,
        failures,
        expected=EXPECTED_REPEAT_FLAGS,
        label="repeat_benchmark",
    )

    source_count = _int_metric(repeat, "source_count")
    row_count = _int_metric(repeat, "row_count")
    row_ok_count = _int_metric(repeat, "row_ok_count")
    rows_consumed = _int_metric(repeat, "rows_consumed")
    repeat_count_requested = _int_metric(repeat, "repeat_count_requested")
    repeat_count_measured = _int_metric(repeat, "repeat_count_measured")
    if source_count is None or source_count < args.min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count < args.min_row_count:
        failures.append("row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    if row_count is not None and rows_consumed != row_count:
        failures.append("rows_consumed_mismatch")
    if (
        repeat_count_requested is None
        or repeat_count_requested < args.min_repeat_count
        or repeat_count_measured != repeat_count_requested
    ):
        failures.append("repeat_count_invalid")

    if repeat.get("field_names") != list(FIELDS):
        failures.append("field_names_mismatch")
    field_hashes = repeat.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("field_read_hashes_missing")
        field_hashes = {}
    for field in FIELDS:
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"{field}_field_hash_invalid")

    for key in (
        "harness_sha256",
        "native_timing_seed_sha256",
    ):
        if not _is_sha256_hex(repeat.get(key)):
            failures.append(f"{key}_invalid")
    for key in (
        "harness_json",
        "native_timing_seed_json",
    ):
        if not isinstance(repeat.get(key), str) or not repeat.get(key):
            failures.append(f"{key}_missing")

    harness = _load_bound_child(
        repeat,
        failures,
        path_key="harness_json",
        sha_key="harness_sha256",
        label="harness",
    )
    if harness:
        _check_expected_flags(
            harness,
            failures,
            expected={**EXPECTED_HARNESS_FLAGS, **EXPECTED_NOOP_FLAGS},
            label="harness",
        )
        _check_field_hashes(
            harness,
            failures,
            label="harness",
            expected_hashes=field_hashes,
            row_count=row_count,
        )

    timing_seed = _load_bound_child(
        repeat,
        failures,
        path_key="native_timing_seed_json",
        sha_key="native_timing_seed_sha256",
        label="native_timing_seed",
    )

    values_raw = repeat.get("native_stub_host_wall_ms_values")
    values: list[float] = []
    if not isinstance(values_raw, list):
        failures.append("native_stub_host_wall_ms_values_missing")
    else:
        for idx, value in enumerate(values_raw):
            numeric = _numeric_ms(value)
            if numeric is None:
                failures.append(f"native_stub_host_wall_ms_value_{idx}_invalid")
            else:
                values.append(numeric)
    if repeat_count_measured is not None and len(values) != repeat_count_measured:
        failures.append("native_stub_host_wall_ms_values_count_mismatch")
    if timing_seed:
        _check_timing_artifact(
            timing_seed,
            failures,
            label="native_timing_seed",
            repeat=repeat,
            expected_wall_ms=None,
            row_count=row_count,
        )
    stat_payload = _stats(values)
    if stat_payload["count"] and stat_payload["relative_range"] > args.max_relative_range:
        failures.append("native_stub_host_wall_relative_range_too_high")
    if (
        stat_payload["count"]
        and stat_payload["coefficient_of_variation"] > args.max_coefficient_of_variation
    ):
        failures.append("native_stub_host_wall_cv_too_high")

    expected_count = repeat_count_measured if isinstance(repeat_count_measured, int) else 0
    _check_repeat_children(
        repeat,
        failures,
        root=repeat_path.parent,
        expected_count=expected_count,
        expected_values=values,
    )

    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "ablation_name": ABLATION_NAME,
        "ablation_mode": ABLATION_MODE,
        "ablation_source": ABLATION_SOURCE,
        "ablation_scope": "payloadless_native_stub_repeat_stability_only",
        "passed": passed,
        "failures": failures,
        "repeat_benchmark_json": str(repeat_path),
        "repeat_benchmark_sha256": _sha256(repeat_path) if repeat_path.exists() else None,
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_ok_count,
        "rows_consumed": rows_consumed,
        "field_names": list(FIELDS),
        "field_read_hashes": field_hashes,
        "repeat_count_requested": repeat_count_requested,
        "repeat_count_measured": repeat_count_measured,
        "native_stub_host_wall_ms_values": values,
        "native_stub_host_wall_ms_stats": stat_payload,
        "max_relative_range": float(args.max_relative_range),
        "max_coefficient_of_variation": float(args.max_coefficient_of_variation),
        "payloadless_useful_runtime_ablation_ready": passed,
        "runtime_ablation_ready": passed,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_native_stub_host_wall_time": passed and bool(values),
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
            "future WNA16 typed-slot payloadless useful runtime ablation failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat-benchmark-json", default=str(DEFAULT_REPEAT_BENCHMARK_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
    parser.add_argument("--min-repeat-count", type=int, default=3)
    parser.add_argument("--max-relative-range", type=float, default=0.05)
    parser.add_argument("--max-coefficient-of-variation", type=float, default=0.03)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_payloadless_useful_runtime_ablation(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
