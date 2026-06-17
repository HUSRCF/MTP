#!/usr/bin/env python3
"""Benchmark the independent future WNA16 typed-slot kernel-variant stub.

This script is intentionally scoped to the separate typed-slot ABI path.  It
does not reuse, reinterpret, or pass the current WNA16 fused-MoE kernel
arguments.  The measured value is the host wall time of the independent native
typed-slot stub/canary path, not vLLM TPOT and not routed expert kernel time.
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


DEFAULT_TIMING_STUB_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_timing_stub_v1_native_run.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_benchmark_v1.json"
)
DEFAULT_REPEAT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_benchmark_repeats"
)

BENCHMARK_NAME = "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1"
BENCHMARK_MODE = "independent_future_wna16_typed_slot_native_stub_benchmark"
BENCHMARK_SOURCE = "premap_future_wna16_typed_slot_kernel_timing_stub_v1"
NEXT_RUNTIME_STAGE = (
    "implement_future_wna16_typed_slot_kernel_variant_payloadless_execution"
)
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
EXPECTED_TIMING_STUB_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
    "timing_stub_name": "premap_future_wna16_typed_slot_kernel_timing_stub_v1",
    "timing_stub_mode": "independent_future_wna16_typed_slot_native_stub_timing",
    "timing_stub_source": "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1",
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
    "next_runtime_stage": "implement_future_wna16_typed_slot_kernel_variant_benchmark",
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


def _numeric_ms(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if value > 0 else None


def _check_timing_stub(
    timing_stub: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_TIMING_STUB_FLAGS.items():
        if timing_stub.get(key) != expected:
            failures.append(
                f"timing_stub_{key}_mismatch:"
                f"{timing_stub.get(key)!r}!={expected!r}"
            )
    source_count = _int_metric(timing_stub, "source_count")
    if source_count is None or source_count < min_source_count:
        failures.append("timing_stub_source_count_invalid")
    row_count = _int_metric(timing_stub, "row_count")
    row_ok_count = _int_metric(timing_stub, "row_ok_count")
    if row_count is None or row_count < min_row_count:
        failures.append("timing_stub_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("timing_stub_row_ok_count_mismatch")
    if timing_stub.get("field_names") != list(HANDLE_FIELDS):
        failures.append("timing_stub_field_names_mismatch")
    row_ok_counts = timing_stub.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("timing_stub_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = timing_stub.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("timing_stub_field_read_hashes_missing")
        field_hashes = {}
    expected_fields = set(HANDLE_FIELDS)
    if set(row_ok_counts) != expected_fields:
        failures.append("timing_stub_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != expected_fields:
        failures.append("timing_stub_field_read_hashes_keys_mismatch")
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"timing_stub_{field}_read_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"timing_stub_{field}_read_hash_invalid")
    for key in (
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
    ):
        if not _is_hex_u64(timing_stub.get(key)):
            failures.append(f"timing_stub_{key}_invalid")
    if _numeric_ms(timing_stub, "native_stub_host_wall_ms") is None:
        failures.append("timing_stub_native_stub_host_wall_ms_invalid")
    return failures


def _repeat_seed_artifact_failures(seed: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for label in ("entrypoint", "runner"):
        path_value = seed.get(f"{label}_json")
        sha_value = seed.get(f"{label}_sha256")
        if not isinstance(path_value, str) or not path_value:
            failures.append(f"seed_{label}_json_missing")
            continue
        if not _is_sha256_hex(sha_value):
            failures.append(f"seed_{label}_sha256_invalid")
            continue
        artifact_path = _resolve(path_value)
        if not artifact_path.exists():
            failures.append(f"seed_{label}_json_not_found")
            continue
        actual_sha = _sha256(artifact_path)
        if actual_sha != sha_value:
            failures.append(f"seed_{label}_sha256_mismatch")
    return failures


def _percentile_nearest(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("cannot compute percentile over an empty list")
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return float(ordered[index])


def _repeat_timing_stub_args(
    args: argparse.Namespace,
    *,
    timing_stub: dict[str, Any],
    repeat_index: int,
) -> argparse.Namespace:
    repeat_dir = _resolve(args.repeat_output_dir)
    entrypoint_json = timing_stub.get("entrypoint_json")
    if not isinstance(entrypoint_json, str) or not entrypoint_json:
        raise ValueError("timing stub artifact does not include entrypoint_json")
    runner_json = timing_stub.get("runner_json")
    if not isinstance(runner_json, str) or not runner_json:
        raise ValueError("timing stub artifact does not include runner_json")
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


def _run_repeat(
    args: argparse.Namespace,
    *,
    timing_stub: dict[str, Any],
    repeat_index: int,
) -> tuple[dict[str, Any], float]:
    repeat_args = _repeat_timing_stub_args(
        args,
        timing_stub=timing_stub,
        repeat_index=repeat_index,
    )
    start_ns = time.perf_counter_ns()
    report = timing_runner.run_timing_stub(repeat_args)
    outer_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, outer_ms


def _measurement_stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "min_ms": 0.0,
            "p10_ms": 0.0,
            "median_ms": 0.0,
            "mean_ms": 0.0,
            "p90_ms": 0.0,
            "max_ms": 0.0,
        }
    return {
        "count": len(values),
        "min_ms": float(min(values)),
        "p10_ms": _percentile_nearest(values, 0.10),
        "median_ms": float(statistics.median(values)),
        "mean_ms": float(statistics.fmean(values)),
        "p90_ms": _percentile_nearest(values, 0.90),
        "max_ms": float(max(values)),
    }


def _repeat_contract_failures(
    repeat_report: dict[str, Any],
    *,
    seed: dict[str, Any],
    repeat_index: int,
) -> list[str]:
    failures: list[str] = []
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
        if repeat_report.get(key) != seed.get(key):
            failures.append(f"{key}_mismatch")
    return failures


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    timing_stub_path = _resolve(args.timing_stub_json)
    output_path = _resolve(args.output_json)
    timing_stub = _load_json(timing_stub_path)
    failures = _check_timing_stub(
        timing_stub,
        min_source_count=args.min_source_count,
        min_row_count=args.min_row_count,
    )
    repeat_reports: list[dict[str, Any]] = []
    repeat_output_jsons: list[str] = []
    repeat_output_sha256s: list[str] = []
    native_stub_wall_ms: list[float] = []
    outer_wall_ms: list[float] = []

    if args.repeat_count > 0:
        failures.extend(_repeat_seed_artifact_failures(timing_stub))
    seed_contract_ok = not failures
    if args.repeat_count < 0:
        failures.append("repeat_count_negative")
    if args.repeat_count == 0:
        source_ms = _numeric_ms(timing_stub, "native_stub_host_wall_ms")
        if source_ms is not None:
            native_stub_wall_ms.append(source_ms)
    elif not seed_contract_ok:
        failures.append("repeat_skipped_due_to_seed_contract_failure")
    for index in range(max(0, args.repeat_count) if seed_contract_ok else 0):
        try:
            repeat_report, repeat_outer_ms = _run_repeat(
                args,
                timing_stub=timing_stub,
                repeat_index=index,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            failures.append(
                f"repeat_{index}:exception:{exc.__class__.__name__}:{exc}"
            )
            continue
        repeat_failures = _check_timing_stub(
            repeat_report,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
        )
        repeat_failures.extend(
            _repeat_contract_failures(
                repeat_report,
                seed=timing_stub,
                repeat_index=index,
            )
        )
        failures.extend(f"repeat_{index}:{item}" for item in repeat_failures)
        repeat_reports.append(repeat_report)
        repeat_output = _resolve(args.repeat_output_dir) / (
            f"timing_stub_repeat_{index:03d}.json"
        )
        repeat_output_jsons.append(str(repeat_output))
        if repeat_output.exists():
            repeat_output_sha256s.append(_sha256(repeat_output))
        repeat_ms = _numeric_ms(repeat_report, "native_stub_host_wall_ms")
        if repeat_ms is None:
            failures.append(f"repeat_{index}:native_stub_host_wall_ms_invalid")
        elif not repeat_failures:
            native_stub_wall_ms.append(repeat_ms)
        if not repeat_failures and repeat_ms is not None:
            outer_wall_ms.append(repeat_outer_ms)

    expected_measurements = 1 if args.repeat_count == 0 else max(0, args.repeat_count)
    if len(native_stub_wall_ms) != expected_measurements:
        failures.append("benchmark_measurement_count_mismatch")
    passed = not failures
    source_count = timing_stub.get("source_count")
    row_count = timing_stub.get("row_count")
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_benchmark",
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_mode": BENCHMARK_MODE,
        "benchmark_source": BENCHMARK_SOURCE,
        "benchmark_scope": "independent_native_typed_slot_stub_host_wall",
        "passed": passed,
        "failures": failures,
        "timing_stub_json": str(timing_stub_path),
        "timing_stub_sha256": _sha256(timing_stub_path),
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": timing_stub.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": timing_stub.get("field_read_row_ok_counts"),
        "field_read_hashes": timing_stub.get("field_read_hashes"),
        "row_hash_accumulator": timing_stub.get("row_hash_accumulator"),
        "handle_projection_hash_accumulator": timing_stub.get(
            "handle_projection_hash_accumulator"
        ),
        "repeat_count_requested": int(args.repeat_count),
        "repeat_count_measured": len(native_stub_wall_ms),
        "repeat_output_jsons": repeat_output_jsons,
        "repeat_output_sha256s": repeat_output_sha256s,
        "native_stub_host_wall_ms_values": native_stub_wall_ms,
        "native_stub_host_wall_ms_stats": _measurement_stats(native_stub_wall_ms),
        "benchmark_outer_wall_ms_values": outer_wall_ms,
        "benchmark_outer_wall_ms_stats": _measurement_stats(outer_wall_ms),
        "typed_slot_variant_benchmark_ready": passed,
        "future_wna16_variant_benchmark_ready": passed,
        "independent_kernel_variant_benchmark": passed,
        "independent_kernel_variant_benchmark_scope_declared": True,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_native_stub_host_wall_time": passed and bool(native_stub_wall_ms),
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
            "future WNA16 typed-slot kernel-variant benchmark failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a benchmark artifact for the independent future WNA16 "
            "typed-slot native stub path. This is not a current WNA16 fused-MoE "
            "argument handoff and not a vLLM TPOT benchmark."
        )
    )
    parser.add_argument("--timing-stub-json", default=str(DEFAULT_TIMING_STUB_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--repeat-output-dir", default=str(DEFAULT_REPEAT_DIR))
    parser.add_argument("--repeat-count", type=int, default=0)
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_benchmark(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
