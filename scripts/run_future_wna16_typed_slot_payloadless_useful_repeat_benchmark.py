#!/usr/bin/env python3
"""Repeat/aggregate the payloadless useful typed-slot native-stub benchmark.

Default mode is seed-only (``--repeat-count 0``): it consumes the already
validated benchmark harness artifact and reports the seed native-stub wall time.
Explicit repeats may re-run the independent timing stub.  This remains
payloadless and does not measure vLLM TPOT or pass current WNA16 arguments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_future_wna16_typed_slot_kernel_timing_stub as timing_runner


DEFAULT_HARNESS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_benchmark_harness_entry_args_ptr_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_entry_args_ptr_seed_v1.json"
)
DEFAULT_REPEAT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_repeats"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_repeat_benchmark"
BENCHMARK_NAME = "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1"
BENCHMARK_MODE = "payloadless_useful_native_stub_repeat_benchmark"
BENCHMARK_SOURCE = "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
EXPECTED_HARNESS_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_payloadless_useful_benchmark_harness",
    "harness_name": "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1",
    "harness_mode": "independent_payloadless_useful_native_stub_benchmark_harness",
    "harness_source": "premap_future_wna16_typed_slot_payloadless_useful_runtime_gate_v1",
    "passed": True,
    "payloadless_useful_benchmark_harness_ready": True,
    "benchmark_harness_ready": True,
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
    "next_runtime_stage": "implement_future_wna16_typed_slot_payloadless_useful_repeat_benchmark",
}
EXPECTED_TIMING_SEED_FLAGS: dict[str, Any] = {
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


def _measurement_stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "min_ms": 0.0,
            "median_ms": 0.0,
            "mean_ms": 0.0,
            "max_ms": 0.0,
        }
    return {
        "count": len(values),
        "min_ms": float(min(values)),
        "median_ms": float(statistics.median(values)),
        "mean_ms": float(statistics.fmean(values)),
        "max_ms": float(max(values)),
    }


def _check_harness(harness: dict[str, Any], failures: list[str]) -> None:
    for key, expected in EXPECTED_HARNESS_FLAGS.items():
        if harness.get(key) != expected:
            failures.append(f"harness_{key}_mismatch")
    if harness.get("failures") != []:
        failures.append("harness_failures_not_empty")
    if harness.get("field_names") != list(FIELDS):
        failures.append("harness_field_names_mismatch")
    row_count = _int_metric(harness, "row_count")
    row_ok_count = _int_metric(harness, "row_ok_count")
    rows_consumed = _int_metric(harness, "rows_consumed")
    if row_count is None:
        failures.append("harness_row_count_invalid")
    else:
        if row_ok_count != row_count:
            failures.append("harness_row_ok_count_mismatch")
        if rows_consumed != row_count:
            failures.append("harness_rows_consumed_mismatch")
    hashes = harness.get("field_read_hashes")
    if not isinstance(hashes, dict):
        failures.append("harness_field_read_hashes_missing")
    else:
        for field in FIELDS:
            if not _is_hex_u64(hashes.get(field)):
                failures.append(f"harness_{field}_field_hash_invalid")
    if _numeric_ms(harness, "native_stub_host_wall_ms") is None:
        failures.append("harness_native_stub_host_wall_ms_invalid")


def _check_timing_seed(
    timing_seed: dict[str, Any],
    harness: dict[str, Any],
    failures: list[str],
) -> None:
    for key, expected in EXPECTED_TIMING_SEED_FLAGS.items():
        if timing_seed.get(key) != expected:
            failures.append(f"timing_seed_{key}_mismatch")
    if timing_seed.get("failures") != []:
        failures.append("timing_seed_failures_not_empty")
    for key in ("source_count", "row_count", "row_ok_count", "field_names", "field_read_hashes"):
        if timing_seed.get(key) != harness.get(key):
            failures.append(f"timing_seed_{key}_mismatch")
    row_count = _int_metric(harness, "row_count")
    row_counts = timing_seed.get("field_read_row_ok_counts")
    if not isinstance(row_counts, dict):
        failures.append("timing_seed_field_read_row_ok_counts_missing")
    else:
        for field in FIELDS:
            if row_count is not None and _int_metric(row_counts, field) != row_count:
                failures.append(f"timing_seed_{field}_row_ok_count_mismatch")
    seed_ms = _numeric_ms(timing_seed, "native_stub_host_wall_ms")
    harness_ms = _numeric_ms(harness, "native_stub_host_wall_ms")
    if seed_ms is None:
        failures.append("timing_seed_native_stub_host_wall_ms_invalid")
    elif harness_ms is not None and seed_ms != harness_ms:
        failures.append("timing_seed_native_stub_host_wall_ms_mismatch")
    stub_path = timing_seed.get("native_stub_output_json")
    if not isinstance(stub_path, str) or not stub_path:
        failures.append("timing_seed_native_stub_output_json_missing")
    elif _resolve(stub_path).resolve() != _resolve(harness.get("native_stub_json", "")).resolve():
        failures.append("timing_seed_native_stub_output_json_mismatch")
    if timing_seed.get("native_stub_output_sha256") != harness.get("native_stub_sha256"):
        failures.append("timing_seed_native_stub_output_sha256_mismatch")


def _repeat_timing_args(
    args: argparse.Namespace,
    *,
    timing_seed: dict[str, Any],
    repeat_index: int,
) -> argparse.Namespace:
    repeat_dir = _resolve(args.repeat_output_dir)
    argv = [
        "--entrypoint-json",
        str(timing_seed["entrypoint_json"]),
        "--runner-json",
        str(timing_seed["runner_json"]),
        "--run-native-stub",
        "--min-source-count",
        str(args.min_source_count),
        "--min-row-count",
        str(args.min_row_count),
        "--block-threads",
        str(args.block_threads),
        "--device",
        str(args.device),
        "--offload-arch",
        str(args.offload_arch),
        "--output-json",
        str(repeat_dir / f"timing_stub_repeat_{repeat_index:03d}.json"),
        "--canary-output-json",
        str(repeat_dir / f"canary_repeat_{repeat_index:03d}.json"),
        "--source-manifest-json",
        str(repeat_dir / f"source_manifest_repeat_{repeat_index:03d}.json"),
        "--merged-output-json",
        str(repeat_dir / f"merged_repeat_{repeat_index:03d}.json"),
        "--stub-output-json",
        str(repeat_dir / f"typed_consumer_stub_repeat_{repeat_index:03d}.json"),
    ]
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.force_build:
        argv.append("--force-build")
    return timing_runner.build_parser().parse_args(argv)


def _check_repeat_timing(
    repeat_report: dict[str, Any],
    harness: dict[str, Any],
    failures: list[str],
    *,
    repeat_index: int,
) -> None:
    prefix = f"repeat_{repeat_index}"
    expected = {
        "passed": True,
        "timing_stub_ready": True,
        "native_stub_executed": True,
        "native_stub_passed": True,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    for key, expected_value in expected.items():
        if repeat_report.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    for key in ("source_count", "row_count", "row_ok_count", "field_names", "field_read_hashes"):
        if repeat_report.get(key) != harness.get(key):
            failures.append(f"{prefix}_{key}_mismatch")
    if _numeric_ms(repeat_report, "native_stub_host_wall_ms") is None:
        failures.append(f"{prefix}_native_stub_host_wall_ms_invalid")


def run_payloadless_useful_repeat_benchmark(
    args: argparse.Namespace,
) -> dict[str, Any]:
    harness_path = _resolve(args.harness_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    try:
        harness = _load_json(harness_path)
    except Exception as exc:
        harness = {}
        failures.append(f"harness_load_failed:{exc.__class__.__name__}:{exc}")
    _check_harness(harness, failures)

    timing_seed_value = harness.get("native_timing_json")
    timing_seed: dict[str, Any] = {}
    if not isinstance(timing_seed_value, str) or not timing_seed_value:
        timing_seed_path = None
        failures.append("native_timing_seed_missing")
    else:
        timing_seed_path = _resolve(timing_seed_value)
    if timing_seed_path is not None and not timing_seed_path.exists():
        failures.append("native_timing_seed_missing")
    elif timing_seed_path is not None:
        if _sha256(timing_seed_path) != harness.get("native_timing_sha256"):
            failures.append("native_timing_seed_sha256_mismatch")
        timing_seed = _load_json(timing_seed_path)
        _check_timing_seed(timing_seed, harness, failures)

    native_ms: list[float] = []
    outer_ms: list[float] = []
    repeat_output_jsons: list[str] = []
    repeat_output_sha256s: list[str] = []
    if args.repeat_count < 0:
        failures.append("repeat_count_negative")
    if args.repeat_count == 0:
        seed_ms = _numeric_ms(harness, "native_stub_host_wall_ms")
        if seed_ms is not None:
            native_ms.append(seed_ms)
    elif not failures:
        for index in range(args.repeat_count):
            try:
                repeat_args = _repeat_timing_args(
                    args,
                    timing_seed=timing_seed,
                    repeat_index=index,
                )
                start_ns = time.perf_counter_ns()
                repeat_report = timing_runner.run_timing_stub(repeat_args)
                repeat_outer_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            except Exception as exc:
                failures.append(
                    f"repeat_{index}:exception:{exc.__class__.__name__}:{exc}"
                )
                continue
            _check_repeat_timing(repeat_report, harness, failures, repeat_index=index)
            repeat_output = _resolve(args.repeat_output_dir) / (
                f"timing_stub_repeat_{index:03d}.json"
            )
            repeat_output_jsons.append(str(repeat_output))
            if repeat_output.exists():
                repeat_output_sha256s.append(_sha256(repeat_output))
            else:
                failures.append(f"repeat_{index}:output_json_missing")
            repeat_ms = _numeric_ms(repeat_report, "native_stub_host_wall_ms")
            if repeat_ms is not None:
                native_ms.append(repeat_ms)
                outer_ms.append(repeat_outer_ms)

    expected_measurements = 1 if args.repeat_count == 0 else max(0, args.repeat_count)
    if len(native_ms) != expected_measurements:
        failures.append("repeat_measurement_count_mismatch")
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_mode": BENCHMARK_MODE,
        "benchmark_source": BENCHMARK_SOURCE,
        "benchmark_scope": "payloadless_useful_independent_native_stub_host_wall",
        "measurement_source": (
            "validated_harness_seed_native_stub_host_wall"
            if int(args.repeat_count) == 0
            else "repeated_independent_native_typed_slot_timing_stub"
        ),
        "seed_only": int(args.repeat_count) == 0,
        "passed": passed,
        "failures": failures,
        "harness_json": str(harness_path),
        "harness_sha256": _sha256(harness_path) if harness_path.exists() else None,
        "native_timing_seed_json": (
            str(timing_seed_path) if timing_seed_path is not None else None
        ),
        "native_timing_seed_sha256": harness.get("native_timing_sha256"),
        "source_count": harness.get("source_count"),
        "row_count": harness.get("row_count"),
        "row_ok_count": harness.get("row_ok_count"),
        "rows_consumed": harness.get("rows_consumed"),
        "field_names": list(FIELDS),
        "field_read_hashes": harness.get("field_read_hashes"),
        "repeat_count_requested": int(args.repeat_count),
        "repeat_count_measured": len(native_ms),
        "repeat_output_jsons": repeat_output_jsons,
        "repeat_output_sha256s": repeat_output_sha256s,
        "native_stub_host_wall_ms_values": native_ms,
        "native_stub_host_wall_ms_stats": _measurement_stats(native_ms),
        "benchmark_outer_wall_ms_values": outer_ms,
        "benchmark_outer_wall_ms_stats": _measurement_stats(outer_ms),
        "payloadless_useful_repeat_benchmark_ready": passed,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_native_stub_host_wall_time": passed and bool(native_ms),
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
            "future WNA16 typed-slot payloadless useful repeat benchmark failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-json", default=str(DEFAULT_HARNESS_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--repeat-output-dir", default=str(DEFAULT_REPEAT_DIR))
    parser.add_argument("--repeat-count", type=int, default=0)
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_payloadless_useful_repeat_benchmark(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
