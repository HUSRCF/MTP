#!/usr/bin/env python3
"""Run the payloadless execution gate for the future WNA16 typed-slot variant.

This stage consumes the independent typed-slot benchmark artifact and can run a
fresh native typed-slot canary as a payloadless execution proof.  It is still
separate from the current WNA16 fused-MoE ABI: no payload is dereferenced, no
current WNA16 argument slot is reused, and no vLLM kernel arguments are passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_future_wna16_typed_slot_kernel_timing_stub as timing_runner


DEFAULT_BENCHMARK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_benchmark_v1_repeat3.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_payloadless_execution_v1.json"
)
DEFAULT_EXECUTION_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_payloadless_execution"
)

EXECUTION_NAME = "premap_future_wna16_typed_slot_payloadless_execution_v1"
EXECUTION_MODE = "independent_future_wna16_typed_slot_payloadless_execution"
EXECUTION_SOURCE = "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1"
NEXT_RUNTIME_STAGE = (
    "implement_future_wna16_typed_slot_kernel_variant_one_field_handoff_canary"
)
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
EXPECTED_BENCHMARK_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_variant_benchmark",
    "benchmark_name": "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1",
    "benchmark_mode": "independent_future_wna16_typed_slot_native_stub_benchmark",
    "benchmark_source": "premap_future_wna16_typed_slot_kernel_timing_stub_v1",
    "benchmark_scope": "independent_native_typed_slot_stub_host_wall",
    "passed": True,
    "typed_slot_variant_benchmark_ready": True,
    "future_wna16_variant_benchmark_ready": True,
    "independent_kernel_variant_benchmark": True,
    "independent_kernel_variant_benchmark_scope_declared": True,
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
    "next_runtime_stage": (
        "implement_future_wna16_typed_slot_kernel_variant_payloadless_execution"
    ),
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


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 < parsed <= 0xFFFFFFFFFFFFFFFF


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _positive_ms(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0


def _check_benchmark(
    benchmark: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
    min_repeat_count: int,
) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_BENCHMARK_FLAGS.items():
        if benchmark.get(key) != expected:
            failures.append(
                f"benchmark_{key}_mismatch:{benchmark.get(key)!r}!={expected!r}"
            )
    source_count = _int_metric(benchmark, "source_count")
    if source_count is None or source_count < min_source_count:
        failures.append("benchmark_source_count_invalid")
    row_count = _int_metric(benchmark, "row_count")
    row_ok_count = _int_metric(benchmark, "row_ok_count")
    if row_count is None or row_count < min_row_count:
        failures.append("benchmark_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("benchmark_row_ok_count_mismatch")
    if benchmark.get("field_names") != list(HANDLE_FIELDS):
        failures.append("benchmark_field_names_mismatch")
    row_ok_counts = benchmark.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("benchmark_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = benchmark.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("benchmark_field_read_hashes_missing")
        field_hashes = {}
    expected_fields = set(HANDLE_FIELDS)
    if set(row_ok_counts) != expected_fields:
        failures.append("benchmark_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != expected_fields:
        failures.append("benchmark_field_read_hashes_keys_mismatch")
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"benchmark_{field}_read_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"benchmark_{field}_read_hash_invalid")
    for key in (
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
    ):
        if not _is_hex_u64(benchmark.get(key)):
            failures.append(f"benchmark_{key}_invalid")
    repeat_count = _int_metric(benchmark, "repeat_count_measured")
    if repeat_count is None or repeat_count < min_repeat_count:
        failures.append("benchmark_repeat_count_measured_invalid")
    stats = benchmark.get("native_stub_host_wall_ms_stats")
    values = benchmark.get("native_stub_host_wall_ms_values")
    if not isinstance(stats, dict):
        failures.append("benchmark_native_stub_host_wall_ms_stats_missing")
        stats = {}
    if not isinstance(values, list) or not values:
        failures.append("benchmark_native_stub_host_wall_ms_values_missing")
        values = []
    if repeat_count is not None and len(values) != repeat_count:
        failures.append("benchmark_native_stub_host_wall_ms_values_count_mismatch")
    if stats.get("count") != len(values):
        failures.append("benchmark_native_stub_host_wall_ms_stats_count_mismatch")
    for value in values:
        if not _positive_ms(value):
            failures.append("benchmark_native_stub_host_wall_ms_value_invalid")
            break
    for key in ("min_ms", "median_ms", "mean_ms", "p90_ms", "max_ms"):
        if not _positive_ms(stats.get(key)):
            failures.append(f"benchmark_native_stub_host_wall_ms_{key}_invalid")
    timing_stub_path_value = benchmark.get("timing_stub_json")
    timing_stub_sha_value = benchmark.get("timing_stub_sha256")
    if not isinstance(timing_stub_path_value, str) or not timing_stub_path_value:
        failures.append("benchmark_timing_stub_json_missing")
    elif not _is_sha256_hex(timing_stub_sha_value):
        failures.append("benchmark_timing_stub_sha256_invalid")
    else:
        timing_stub_path = _resolve(timing_stub_path_value)
        if not timing_stub_path.exists():
            failures.append("benchmark_timing_stub_json_not_found")
        else:
            try:
                timing_stub_sha = _sha256(timing_stub_path)
            except Exception as exc:
                failures.append(
                    f"benchmark_timing_stub_sha256_failed:"
                    f"{exc.__class__.__name__}:{exc}"
                )
            else:
                if timing_stub_sha != timing_stub_sha_value:
                    failures.append("benchmark_timing_stub_sha256_mismatch")
    return failures


def _check_execution_timing_stub(
    report: dict[str, Any],
    *,
    seed: dict[str, Any],
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected = {
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
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            failures.append(
                f"execution_{key}_mismatch:{report.get(key)!r}!={expected_value!r}"
            )
    source_count = _int_metric(report, "source_count")
    row_count = _int_metric(report, "row_count")
    row_ok_count = _int_metric(report, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("execution_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("execution_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("execution_row_ok_count_mismatch")
    for key in (
        "entrypoint_sha256",
        "runner_sha256",
        "source_count",
        "row_count",
        "row_ok_count",
        "field_names",
        "field_read_row_ok_counts",
        "field_read_hashes",
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
    ):
        if report.get(key) != seed.get(key):
            failures.append(f"execution_{key}_mismatch")
    if not _positive_ms(report.get("native_stub_host_wall_ms")):
        failures.append("execution_native_stub_host_wall_ms_invalid")
    return failures


def _check_benchmark_repeat_artifacts(
    benchmark: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
    min_repeat_count: int,
) -> tuple[list[str], dict[str, Any] | None]:
    failures: list[str] = []
    seed: dict[str, Any] | None = None
    timing_stub_path_value = benchmark.get("timing_stub_json")
    if isinstance(timing_stub_path_value, str) and timing_stub_path_value:
        try:
            seed = _load_json(_resolve(timing_stub_path_value))
        except Exception as exc:
            failures.append(
                f"benchmark_timing_stub_json_load_failed:"
                f"{exc.__class__.__name__}:{exc}"
            )
    if seed is not None:
        failures.extend(
            f"seed_{item}"
            for item in _check_execution_timing_stub(
                seed,
                seed=seed,
                min_source_count=min_source_count,
                min_row_count=min_row_count,
            )
        )
        for key in (
            "source_count",
            "row_count",
            "row_ok_count",
            "field_names",
            "field_read_row_ok_counts",
            "field_read_hashes",
            "row_hash_accumulator",
            "handle_projection_hash_accumulator",
        ):
            if benchmark.get(key) != seed.get(key):
                failures.append(f"benchmark_seed_{key}_mismatch")
    repeat_count = _int_metric(benchmark, "repeat_count_measured")
    repeat_jsons = benchmark.get("repeat_output_jsons")
    repeat_shas = benchmark.get("repeat_output_sha256s")
    if repeat_count is None or repeat_count < min_repeat_count:
        return failures, seed
    if not isinstance(repeat_jsons, list) or len(repeat_jsons) != repeat_count:
        failures.append("benchmark_repeat_output_jsons_count_mismatch")
        repeat_jsons = []
    if not isinstance(repeat_shas, list) or len(repeat_shas) != repeat_count:
        failures.append("benchmark_repeat_output_sha256s_count_mismatch")
        repeat_shas = []
    if seed is None:
        failures.append("benchmark_repeat_seed_timing_stub_missing")
        return failures, seed
    for index, (path_value, sha_value) in enumerate(zip(repeat_jsons, repeat_shas)):
        if not isinstance(path_value, str) or not path_value:
            failures.append(f"benchmark_repeat_{index}_json_missing")
            continue
        if not _is_sha256_hex(sha_value):
            failures.append(f"benchmark_repeat_{index}_sha256_invalid")
            continue
        repeat_path = _resolve(path_value)
        if not repeat_path.exists():
            failures.append(f"benchmark_repeat_{index}_json_not_found")
            continue
        try:
            actual_sha = _sha256(repeat_path)
        except Exception as exc:
            failures.append(
                f"benchmark_repeat_{index}_sha256_failed:"
                f"{exc.__class__.__name__}:{exc}"
            )
            continue
        if actual_sha != sha_value:
            failures.append(f"benchmark_repeat_{index}_sha256_mismatch")
            continue
        try:
            repeat_payload = _load_json(repeat_path)
        except Exception as exc:
            failures.append(
                f"benchmark_repeat_{index}_json_load_failed:"
                f"{exc.__class__.__name__}:{exc}"
            )
            continue
        repeat_failures = _check_execution_timing_stub(
            repeat_payload,
            seed=seed,
            min_source_count=min_source_count,
            min_row_count=min_row_count,
        )
        failures.extend(
            f"benchmark_repeat_{index}:{item}" for item in repeat_failures
        )
    return failures, seed


def _observed_bool(
    benchmark: dict[str, Any],
    execution_report: dict[str, Any] | None,
    key: str,
) -> bool:
    return benchmark.get(key) is True or (
        execution_report is not None and execution_report.get(key) is True
    )


def _observed_payload_bytes(
    benchmark: dict[str, Any],
    execution_report: dict[str, Any] | None,
) -> int:
    values: list[int] = []
    for payload in (benchmark, execution_report or {}):
        value = payload.get("payload_bytes")
        if isinstance(value, int) and not isinstance(value, bool):
            values.append(value)
    return max(values) if values else 0


def _build_timing_stub_args(
    args: argparse.Namespace,
    *,
    benchmark: dict[str, Any],
) -> argparse.Namespace:
    timing_stub_path = _resolve(str(benchmark["timing_stub_json"]))
    timing_stub = _load_json(timing_stub_path)
    entrypoint_json = timing_stub.get("entrypoint_json")
    runner_json = timing_stub.get("runner_json")
    if not isinstance(entrypoint_json, str) or not entrypoint_json:
        raise ValueError("timing stub artifact does not include entrypoint_json")
    if not isinstance(runner_json, str) or not runner_json:
        raise ValueError("timing stub artifact does not include runner_json")
    output_dir = _resolve(args.execution_output_dir)
    argv = [
        "--entrypoint-json",
        entrypoint_json,
        "--runner-json",
        runner_json,
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
        str(output_dir / "payloadless_execution_timing_stub.json"),
        "--canary-output-json",
        str(output_dir / "payloadless_execution_canary.json"),
        "--source-manifest-json",
        str(output_dir / "payloadless_execution_source_manifest.json"),
        "--merged-output-json",
        str(output_dir / "payloadless_execution_merged_input.json"),
        "--stub-output-json",
        str(output_dir / "payloadless_execution_typed_consumer_stub.json"),
    ]
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.force_build:
        argv.append("--force-build")
    return timing_runner.build_parser().parse_args(argv)


def _run_payloadless_execution(
    args: argparse.Namespace,
    *,
    benchmark: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    timing_args = _build_timing_stub_args(args, benchmark=benchmark)
    start_ns = time.perf_counter_ns()
    report = timing_runner.run_timing_stub(timing_args)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def run_payloadless_execution(args: argparse.Namespace) -> dict[str, Any]:
    benchmark_path = _resolve(args.benchmark_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    benchmark: dict[str, Any] = {}
    try:
        benchmark = _load_json(benchmark_path)
    except Exception as exc:
        failures.append(
            f"benchmark_json_load_failed:{exc.__class__.__name__}:{exc}"
        )
    benchmark_failures: list[str] = []
    repeat_failures: list[str] = []
    timing_stub_seed: dict[str, Any] | None = None
    if benchmark:
        benchmark_failures = _check_benchmark(
            benchmark,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
            min_repeat_count=args.min_repeat_count,
        )
        repeat_failures, timing_stub_seed = _check_benchmark_repeat_artifacts(
            benchmark,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
            min_repeat_count=args.min_repeat_count,
        )
        failures.extend(benchmark_failures)
        failures.extend(repeat_failures)
    gate_ready = bool(benchmark) and not benchmark_failures and not repeat_failures
    execution_report: dict[str, Any] | None = None
    execution_outer_wall_ms: float | None = None
    if args.run_native_execution and gate_ready:
        try:
            execution_report, execution_outer_wall_ms = _run_payloadless_execution(
                args,
                benchmark=benchmark,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            failures.append(
                "payloadless_execution_exception:"
                f"{exc.__class__.__name__}:{exc}"
            )
        if execution_report is not None:
            failures.extend(
                _check_execution_timing_stub(
                    execution_report,
                    seed=timing_stub_seed,
                    min_source_count=args.min_source_count,
                    min_row_count=args.min_row_count,
                )
            )
    elif args.run_native_execution:
        failures.append("payloadless_execution_skipped_due_to_benchmark_failure")
    if args.require_native_execution and execution_report is None:
        failures.append("payloadless_execution_required_but_not_executed")
    benchmark_sha256: str | None = None
    if benchmark_path.exists():
        try:
            benchmark_sha256 = _sha256(benchmark_path)
        except Exception as exc:
            failures.append(
                f"benchmark_json_sha256_failed:{exc.__class__.__name__}:{exc}"
            )
    execution_output_dir = _resolve(args.execution_output_dir)
    timing_stub_json_path = execution_output_dir / "payloadless_execution_timing_stub.json"
    canary_json_path = execution_output_dir / "payloadless_execution_canary.json"
    timing_stub_sha256: str | None = None
    if execution_report is not None and timing_stub_json_path.exists():
        try:
            timing_stub_sha256 = _sha256(timing_stub_json_path)
        except Exception as exc:
            failures.append(
                f"payloadless_timing_stub_sha256_failed:"
                f"{exc.__class__.__name__}:{exc}"
            )
            passed = False
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_payloadless_execution",
        "payloadless_execution_name": EXECUTION_NAME,
        "payloadless_execution_mode": EXECUTION_MODE,
        "payloadless_execution_source": EXECUTION_SOURCE,
        "passed": passed,
        "failures": failures,
        "benchmark_json": str(benchmark_path),
        "benchmark_sha256": benchmark_sha256,
        "source_count": benchmark.get("source_count"),
        "row_count": benchmark.get("row_count"),
        "row_ok_count": benchmark.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": benchmark.get("field_read_row_ok_counts"),
        "field_read_hashes": benchmark.get("field_read_hashes"),
        "row_hash_accumulator": benchmark.get("row_hash_accumulator"),
        "handle_projection_hash_accumulator": benchmark.get(
            "handle_projection_hash_accumulator"
        ),
        "benchmark_repeat_count_measured": benchmark.get("repeat_count_measured"),
        "benchmark_native_stub_host_wall_ms_stats": benchmark.get(
            "native_stub_host_wall_ms_stats"
        ),
        "payloadless_execution_gate_ready": gate_ready,
        "payloadless_execution_ready": passed,
        "payloadless_execution_native_requested": bool(args.run_native_execution),
        "payloadless_execution_native_executed": execution_report is not None,
        "payloadless_execution_native_passed": (
            execution_report.get("passed") if execution_report else None
        ),
        "payloadless_execution_native_host_wall_ms": (
            execution_report.get("native_stub_host_wall_ms")
            if execution_report
            else None
        ),
        "payloadless_execution_outer_wall_ms": execution_outer_wall_ms,
        "payloadless_execution_timing_stub_json": str(
            timing_stub_json_path
        ),
        "payloadless_execution_timing_stub_sha256": timing_stub_sha256,
        "payloadless_execution_runner_json": (
            execution_report.get("runner_json") if execution_report else None
        ),
        "payloadless_execution_runner_sha256": (
            execution_report.get("runner_sha256") if execution_report else None
        ),
        "payloadless_execution_canary_json": str(
            canary_json_path
        ),
        "payloadless_execution_scope": (
            "independent_native_typed_slot_payloadless_execution"
        ),
        "benchmark_is_current_wna16_fused_moe": False,
        "expected_measures_vllm_latency": False,
        "expected_measures_tpot": False,
        "expected_wna16_benchmark_ready": False,
        "expected_uses_current_wna16_args": False,
        "expected_passes_current_wna16_args": False,
        "expected_current_wna16_arg_compatible": False,
        "expected_requires_wna16_arg_reinterpretation": False,
        "expected_payload_bytes": 0,
        "expected_payload_deref_allowed": False,
        "expected_kernel_arg_pass_allowed": False,
        "expected_passed_to_kernel": False,
        "expected_changes_kernel_launch_args": False,
        "measures_vllm_latency": _observed_bool(
            benchmark, execution_report, "measures_vllm_latency"
        ),
        "measures_tpot": _observed_bool(benchmark, execution_report, "measures_tpot"),
        "wna16_benchmark_ready": _observed_bool(
            benchmark, execution_report, "wna16_benchmark_ready"
        ),
        "uses_current_wna16_args": _observed_bool(
            benchmark, execution_report, "uses_current_wna16_args"
        ),
        "passes_current_wna16_args": _observed_bool(
            benchmark, execution_report, "passes_current_wna16_args"
        ),
        "current_wna16_arg_compatible": _observed_bool(
            benchmark, execution_report, "current_wna16_arg_compatible"
        ),
        "requires_wna16_arg_reinterpretation": _observed_bool(
            benchmark, execution_report, "requires_wna16_arg_reinterpretation"
        ),
        "payload_bytes": _observed_payload_bytes(benchmark, execution_report),
        "payload_deref_allowed": _observed_bool(
            benchmark, execution_report, "payload_deref_allowed"
        ),
        "kernel_arg_pass_allowed": _observed_bool(
            benchmark, execution_report, "kernel_arg_pass_allowed"
        ),
        "passed_to_kernel": _observed_bool(benchmark, execution_report, "passed_to_kernel"),
        "changes_kernel_launch_args": _observed_bool(
            benchmark, execution_report, "changes_kernel_launch_args"
        ),
        "block_threads": int(args.block_threads),
        "device": int(args.device),
        "offload_arch": str(args.offload_arch),
        "hip_visible_devices": args.hip_visible_devices,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot payloadless execution failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and optionally execute the payloadless independent future "
            "WNA16 typed-slot native path. This does not pass current WNA16 "
            "fused-MoE kernel args and does not move payload."
        )
    )
    parser.add_argument("--benchmark-json", default=str(DEFAULT_BENCHMARK_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--execution-output-dir", default=str(DEFAULT_EXECUTION_DIR))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--min-repeat-count", type=int, default=3)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--run-native-execution", action="store_true")
    parser.add_argument("--require-native-execution", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_payloadless_execution(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
