#!/usr/bin/env python3
"""Run the future WNA16 typed-slot timing-stub gate.

This is a timing canary for the independent typed-slot consumer path, not a
vLLM TPOT benchmark and not a current WNA16 fused-MoE argument handoff.  When
``--run-native-stub`` is used, the script reuses the existing online-merged
native typed-consumer runner to execute the future WNA16 typed-slot stub and
records host wall time around that canary.
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

from scripts import run_premap_online_merged_native_arg_slot_canary as canary_runner


DEFAULT_ENTRYPOINT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_entrypoint_four_field_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_timing_stub_v1.json"
)
DEFAULT_CANARY_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_timing_stub_canary_runner.json"
)
DEFAULT_MERGED_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_timing_stub_merged_input.json"
)
DEFAULT_STUB_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_future_wna16_typed_slot_kernel_timing_stub.json"
)
DEFAULT_SOURCE_MANIFEST_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_timing_stub_source_manifest.json"
)

TIMING_STUB_NAME = "premap_future_wna16_typed_slot_kernel_timing_stub_v1"
TIMING_STUB_MODE = "independent_future_wna16_typed_slot_native_stub_timing"
TIMING_STUB_SOURCE = "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_kernel_variant_benchmark"
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
EXPECTED_ENTRYPOINT_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_variant_entrypoint",
    "entrypoint_name": "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1",
    "entrypoint_mode": "readonly_independent_typed_slot_kernel_variant_entrypoint",
    "entrypoint_source": "premap_wna16_typed_slot_benchmark_harness_v1",
    "passed": True,
    "typed_slot_entrypoint_ready": True,
    "entrypoint_accepts_typed_slot": True,
    "entrypoint_consumes_handle_fields": True,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
    "payload_bytes": 0,
    "payload_deref_allowed": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "measures_latency": False,
    "wna16_benchmark_ready": False,
    "next_runtime_stage": "implement_future_wna16_typed_slot_kernel_timing_stub",
    "fourth_field_handoff_ready": True,
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


def _check_entrypoint(
    entrypoint: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_ENTRYPOINT_FLAGS.items():
        if entrypoint.get(key) != expected:
            failures.append(
                f"entrypoint_{key}_mismatch:{entrypoint.get(key)!r}!={expected!r}"
            )
    source_count = _int_metric(entrypoint, "source_count")
    if source_count is None or source_count < min_source_count:
        failures.append("entrypoint_source_count_invalid")
    row_count = _int_metric(entrypoint, "row_count")
    row_ok_count = _int_metric(entrypoint, "row_ok_count")
    if row_count is None or row_count < min_row_count:
        failures.append("entrypoint_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("entrypoint_row_ok_count_mismatch")
    if entrypoint.get("field_names") != list(HANDLE_FIELDS):
        failures.append("entrypoint_field_names_mismatch")
    row_ok_counts = entrypoint.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("entrypoint_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = entrypoint.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("entrypoint_field_read_hashes_missing")
        field_hashes = {}
    expected_fields = set(HANDLE_FIELDS)
    if set(row_ok_counts) != expected_fields:
        failures.append("entrypoint_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != expected_fields:
        failures.append("entrypoint_field_read_hashes_keys_mismatch")
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"entrypoint_{field}_read_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"entrypoint_{field}_read_hash_invalid")
    for key in (
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
        "fourth_field_handoff_field_read_hash",
        "fourth_field_handoff_runner_hash",
    ):
        if not _is_hex_u64(entrypoint.get(key)):
            failures.append(f"entrypoint_{key}_invalid")
    fourth_source_count = _int_metric(entrypoint, "fourth_field_handoff_source_count")
    if fourth_source_count is None:
        failures.append("entrypoint_fourth_field_handoff_source_count_invalid")
    elif source_count is not None and fourth_source_count != source_count:
        failures.append("entrypoint_fourth_field_handoff_source_count_mismatch")
    fourth_row_count = _int_metric(entrypoint, "fourth_field_handoff_row_count")
    fourth_row_ok_count = _int_metric(entrypoint, "fourth_field_handoff_row_ok_count")
    if fourth_row_count is None:
        failures.append("entrypoint_fourth_field_handoff_row_count_invalid")
    elif row_count is not None and fourth_row_count != row_count:
        failures.append("entrypoint_fourth_field_handoff_row_count_mismatch")
    if fourth_row_ok_count is None:
        failures.append("entrypoint_fourth_field_handoff_row_ok_count_invalid")
    elif fourth_row_count is not None and fourth_row_ok_count != fourth_row_count:
        failures.append("entrypoint_fourth_field_handoff_row_ok_count_mismatch")
    descriptor_hash = field_hashes.get("descriptor_ptr")
    if entrypoint.get("fourth_field_handoff_field_read_hash") != descriptor_hash:
        failures.append("entrypoint_fourth_field_handoff_descriptor_hash_mismatch")
    return failures


def _runner_json_from_entrypoint(entrypoint: dict[str, Any]) -> Path | None:
    harness_path_value = entrypoint.get("harness_json")
    if not isinstance(harness_path_value, str) or not harness_path_value:
        return None
    harness_path = _resolve(harness_path_value)
    if not harness_path.exists():
        return None
    harness = _load_json(harness_path)
    runner_path_value = harness.get("runner_json")
    if not isinstance(runner_path_value, str) or not runner_path_value:
        return None
    return _resolve(runner_path_value)


def _source_manifest_from_runner_json(
    runner_json: Path,
    *,
    output_path: Path,
) -> Path:
    payload = _load_json(runner_json)
    existing = payload.get("online_prelaunch_input_jsons")
    if isinstance(existing, list) and existing:
        return runner_json
    input_jsons = payload.get("input_jsons")
    if not isinstance(input_jsons, list) or not input_jsons:
        raise ValueError(f"runner JSON does not list input_jsons: {runner_json}")
    manifest = {"online_prelaunch_input_jsons": [str(item) for item in input_jsons]}
    _write_json(output_path, manifest)
    return output_path


def _run_native_stub(
    args: argparse.Namespace,
    *,
    entrypoint: dict[str, Any],
    runner_json: Path,
) -> tuple[dict[str, Any], float]:
    source_count = int(entrypoint["source_count"])
    row_count = int(entrypoint["row_count"])
    source_manifest_json = _source_manifest_from_runner_json(
        runner_json,
        output_path=_resolve(args.source_manifest_json),
    )
    canary_args = canary_runner.build_parser().parse_args(
        [
            "--runner-json",
            str(source_manifest_json),
            "--max-inputs",
            str(source_count),
            "--min-source-count",
            str(args.min_source_count),
            "--min-total-rows",
            str(row_count),
            "--block-threads",
            str(args.block_threads),
            "--device",
            str(args.device),
            "--offload-arch",
            str(args.offload_arch),
            "--merged-output-json",
            str(_resolve(args.merged_output_json)),
            "--stub-output-json",
            str(_resolve(args.stub_output_json)),
            "--output-json",
            str(_resolve(args.canary_output_json)),
            "--require-future-wna16-kernel-side-consumer-execution",
            "--require-wna16-side-consumer-variant-execution",
        ]
    )
    if args.hip_visible_devices is not None:
        canary_args.hip_visible_devices = str(args.hip_visible_devices)
    if args.force_build:
        canary_args.force_build = True
    start_ns = time.perf_counter_ns()
    canary_report = canary_runner.run_canary(canary_args)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return canary_report, elapsed_ms


def _check_canary_report(
    report: dict[str, Any],
    *,
    entrypoint: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    row_count = _int_metric(entrypoint, "row_count")
    source_count = _int_metric(entrypoint, "source_count")
    expected = {
        "passed": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_wna16_side_consumer_variant_execution": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            failures.append(f"canary_{key}_mismatch:{report.get(key)!r}!={value!r}")
    if source_count is not None and report.get("selected_source_count") != source_count:
        failures.append("canary_source_count_mismatch")
    if row_count is not None and report.get("merged_row_count") != row_count:
        failures.append("canary_row_count_mismatch")
    for prefix in (
        "future_wna16_kernel_side_consumer_execution",
        "wna16_side_consumer_variant_execution",
    ):
        if row_count is not None and report.get(f"{prefix}_row_count") != row_count:
            failures.append(f"canary_{prefix}_row_count_mismatch")
        if row_count is not None and report.get(f"{prefix}_row_ok_count") != row_count:
            failures.append(f"canary_{prefix}_row_ok_count_mismatch")
        if report.get(f"{prefix}_payload_bytes") != 0:
            failures.append(f"canary_{prefix}_payload_bytes_mismatch")
        payload_deref_allowed = report.get(f"{prefix}_payload_deref_allowed")
        if payload_deref_allowed not in (False, None):
            failures.append(f"canary_{prefix}_payload_deref_allowed_mismatch")
        kernel_arg_pass_allowed = report.get(f"{prefix}_kernel_arg_pass_allowed")
        if kernel_arg_pass_allowed not in (False, None):
            failures.append(f"canary_{prefix}_kernel_arg_pass_allowed_mismatch")
        if report.get(f"{prefix}_passed_to_kernel") is not False:
            failures.append(f"canary_{prefix}_passed_to_kernel_mismatch")
        if report.get(f"{prefix}_changes_kernel_launch_args") is not False:
            failures.append(f"canary_{prefix}_changes_kernel_launch_args_mismatch")
        if report.get(f"{prefix}_current_wna16_arg_compatible") is not False:
            failures.append(f"canary_{prefix}_current_wna16_arg_compatible_mismatch")
        if report.get(f"{prefix}_requires_wna16_arg_reinterpretation") is not False:
            failures.append(
                f"canary_{prefix}_requires_wna16_arg_reinterpretation_mismatch"
            )
        if report.get(f"{prefix}_reuses_current_wna16_arg_slot") is not False:
            failures.append(f"canary_{prefix}_reuses_current_wna16_arg_slot_mismatch")
    return failures


def run_timing_stub(args: argparse.Namespace) -> dict[str, Any]:
    entrypoint_path = _resolve(args.entrypoint_json)
    output_path = _resolve(args.output_json)
    entrypoint = _load_json(entrypoint_path)
    failures = _check_entrypoint(
        entrypoint,
        min_source_count=args.min_source_count,
        min_row_count=args.min_row_count,
    )
    canary_report: dict[str, Any] | None = None
    native_stub_host_wall_ms: float | None = None
    runner_json = _resolve(args.runner_json) if args.runner_json else None
    if runner_json is None:
        runner_json = _runner_json_from_entrypoint(entrypoint)
    if args.run_native_stub:
        if runner_json is None:
            failures.append("runner_json_missing")
        elif not runner_json.exists():
            failures.append("runner_json_not_found")
        else:
            canary_report, native_stub_host_wall_ms = _run_native_stub(
                args,
                entrypoint=entrypoint,
                runner_json=runner_json,
            )
            failures.extend(_check_canary_report(canary_report, entrypoint=entrypoint))
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "timing_stub_name": TIMING_STUB_NAME,
        "timing_stub_mode": TIMING_STUB_MODE,
        "timing_stub_source": TIMING_STUB_SOURCE,
        "passed": passed,
        "failures": failures,
        "entrypoint_json": str(entrypoint_path),
        "entrypoint_sha256": _sha256(entrypoint_path),
        "runner_json": str(runner_json) if runner_json is not None else None,
        "runner_sha256": _sha256(runner_json) if runner_json is not None and runner_json.exists() else None,
        "source_count": entrypoint.get("source_count"),
        "row_count": entrypoint.get("row_count"),
        "row_ok_count": entrypoint.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": entrypoint.get("field_read_row_ok_counts"),
        "field_read_hashes": entrypoint.get("field_read_hashes"),
        "row_hash_accumulator": entrypoint.get("row_hash_accumulator"),
        "handle_projection_hash_accumulator": entrypoint.get(
            "handle_projection_hash_accumulator"
        ),
        "fourth_field_handoff_ready": entrypoint.get("fourth_field_handoff_ready"),
        "fourth_field_handoff_source_count": entrypoint.get(
            "fourth_field_handoff_source_count"
        ),
        "fourth_field_handoff_row_count": entrypoint.get(
            "fourth_field_handoff_row_count"
        ),
        "fourth_field_handoff_row_ok_count": entrypoint.get(
            "fourth_field_handoff_row_ok_count"
        ),
        "fourth_field_handoff_field_read_hash": entrypoint.get(
            "fourth_field_handoff_field_read_hash"
        ),
        "fourth_field_handoff_runner_hash": entrypoint.get(
            "fourth_field_handoff_runner_hash"
        ),
        "timing_stub_ready": passed,
        "native_stub_requested": bool(args.run_native_stub),
        "native_stub_executed": canary_report is not None,
        "native_stub_host_wall_ms": native_stub_host_wall_ms,
        "native_stub_passed": canary_report.get("passed") if canary_report else None,
        "native_stub_canary_output_json": str(_resolve(args.canary_output_json)),
        "native_stub_source_manifest_json": str(_resolve(args.source_manifest_json)),
        "native_stub_merged_output_json": str(_resolve(args.merged_output_json)),
        "native_stub_output_json": str(_resolve(args.stub_output_json)),
        "block_threads": int(args.block_threads),
        "device": int(args.device),
        "offload_arch": str(args.offload_arch),
        "hip_visible_devices": args.hip_visible_devices,
        "measures_native_stub_host_wall_time": canary_report is not None,
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
    if canary_report is not None:
        report["native_stub_selected_source_count"] = canary_report.get(
            "selected_source_count"
        )
        report["native_stub_merged_row_count"] = canary_report.get("merged_row_count")
        report["native_stub_dispatch_active_rows"] = canary_report.get(
            "dispatch_active_rows"
        )
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot timing stub gate failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the future WNA16 typed-slot entrypoint and optionally run "
            "the independent native typed-slot timing stub."
        )
    )
    parser.add_argument("--entrypoint-json", default=str(DEFAULT_ENTRYPOINT_JSON))
    parser.add_argument("--runner-json")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--canary-output-json", default=str(DEFAULT_CANARY_OUTPUT_JSON))
    parser.add_argument("--source-manifest-json", default=str(DEFAULT_SOURCE_MANIFEST_JSON))
    parser.add_argument("--merged-output-json", default=str(DEFAULT_MERGED_OUTPUT_JSON))
    parser.add_argument("--stub-output-json", default=str(DEFAULT_STUB_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--run-native-stub", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_timing_stub(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
