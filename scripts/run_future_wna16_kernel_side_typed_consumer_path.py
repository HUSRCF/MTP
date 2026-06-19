#!/usr/bin/env python3
"""Run a stricter independent future-WNA16 kernel-side typed consumer path.

This stage consumes the all-four-field typed-slot lab gate and reruns the
native typed-consumer stub with the future-WNA16 kernel-side consumer and
WNA16-side variant execution macros enabled.  It is still independent from the
current AWQ WNA16 fused-MoE launch signature: no payload is dereferenced, no
current WNA16 argument slot is reused, and no kernel arguments are passed.
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

from scripts import run_premap_online_merged_native_arg_slot_canary as native_runner  # noqa: E402


DEFAULT_ALL_FOUR_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_kernel_side_typed_consumer_path_v1.json"
)
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_kernel_side_typed_consumer_path_v1"
)

ARTIFACT_KIND = "future_wna16_kernel_side_typed_consumer_path"
PATH_NAME = "premap_future_wna16_kernel_side_typed_consumer_path_v1"
PATH_MODE = "independent_future_wna16_kernel_side_typed_consumer_path"
PATH_SOURCE = "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
NEXT_RUNTIME_STAGE = (
    "implement_future_wna16_typed_slot_kernel_variant_payloadless_execution"
)
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
REQUIRED_PREFIXES = (
    "future_wna16_kernel_side_consumer_execution",
    "wna16_side_consumer_variant_execution",
)
REQUIRED_FALSE_BOUNDARY_KEYS = (
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
    "requires_wna16_arg_reinterpretation",
)
REQUIRED_PREFIX_FALSE_BOUNDARY_KEYS = REQUIRED_FALSE_BOUNDARY_KEYS + (
    "reuses_current_wna16_arg_slot",
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


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 < parsed <= 0xFFFFFFFFFFFFFFFF


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _input_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = [
        {"index": index, "path": str(path), "sha256": _sha256(path)}
        for index, path in enumerate(paths)
    ]
    digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "input_json_count": len(paths),
        "input_manifest_sha256": digest,
        "input_manifest_entries": entries,
    }


def _check_false_boundary(prefix: str, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in REQUIRED_FALSE_BOUNDARY_KEYS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    if payload.get("payload_bytes") != 0:
        failures.append(f"{prefix}_payload_bytes_not_zero")
    return failures


def _load_input_paths_from_native_report(path: Path) -> tuple[list[Path], list[str]]:
    failures: list[str] = []
    try:
        payload = _load_json(path)
    except Exception as exc:
        return [], [f"native_consumer_json_load_failed:{exc.__class__.__name__}:{exc}"]
    raw_paths = payload.get("input_jsons")
    if not isinstance(raw_paths, list) or not raw_paths:
        return [], ["native_consumer_input_jsons_missing"]
    paths: list[Path] = []
    for item in raw_paths:
        if not isinstance(item, str) or not item:
            failures.append("native_consumer_input_jsons_invalid")
            continue
        candidate = _resolve(item)
        if not candidate.exists():
            failures.append(f"native_consumer_input_json_missing:{candidate}")
        elif not candidate.is_file():
            failures.append(f"native_consumer_input_json_not_file:{candidate}")
        else:
            paths.append(candidate)
    return paths, failures


def _check_all_four_gate(
    payload: dict[str, Any],
    *,
    all_four_path: Path,
    min_source_count: int,
    min_row_count: int,
) -> tuple[list[Path], list[str]]:
    failures: list[str] = []
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_all_four_field_consumer",
        "all_four_field_consumer_name": (
            "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
        ),
        "all_four_field_consumer_mode": (
            "readonly_future_wna16_typed_slot_all_four_field_consumer"
        ),
        "all_four_field_consumer_source": (
            "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
        ),
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "passed": True,
        "failures": [],
        "native_consumer_executed": True,
        "native_consumer_passed": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"all_four_{key}_mismatch")

    source_count = _int_metric(payload, "source_count")
    row_count = _int_metric(payload, "row_count")
    row_ok_count = _int_metric(payload, "row_ok_count")
    selected_input_json_count = _int_metric(payload, "selected_input_json_count")
    if source_count is None or source_count < min_source_count:
        failures.append("all_four_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("all_four_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("all_four_row_ok_count_mismatch")

    fourth_path_raw = payload.get("fourth_field_json")
    fourth_sha = payload.get("fourth_field_sha256")
    if not isinstance(fourth_path_raw, str) or not fourth_path_raw:
        failures.append("all_four_fourth_field_json_missing")
    else:
        fourth_path = _resolve(fourth_path_raw)
        if not fourth_path.exists():
            failures.append("all_four_fourth_field_json_missing_on_disk")
        elif _sha256(fourth_path) != fourth_sha:
            failures.append("all_four_fourth_field_sha256_mismatch")
        else:
            try:
                fourth_payload = _load_json(fourth_path)
            except Exception as exc:
                failures.append(
                    f"all_four_fourth_field_json_load_failed:"
                    f"{exc.__class__.__name__}:{exc}"
                )
            else:
                fourth_expected = {
                    "artifact_kind": (
                        "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
                    ),
                    "passed": True,
                    "failures": [],
                    "fourth_field_name": "descriptor_ptr",
                    "payload_bytes": 0,
                    "payload_deref_allowed": False,
                    "kernel_arg_pass_allowed": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                    "uses_current_wna16_args": False,
                    "passes_current_wna16_args": False,
                    "measures_tpot": False,
                    "measures_vllm_latency": False,
                    "wna16_benchmark_ready": False,
                }
                for key, expected_value in fourth_expected.items():
                    if fourth_payload.get(key) != expected_value:
                        failures.append(f"all_four_fourth_field_{key}_mismatch")
                fourth_source_count = _int_metric(fourth_payload, "source_count")
                fourth_row_count = _int_metric(fourth_payload, "row_count")
                fourth_row_ok_count = _int_metric(fourth_payload, "row_ok_count")
                if source_count is not None and fourth_source_count != source_count:
                    failures.append("all_four_fourth_field_source_count_mismatch")
                if row_count is not None and fourth_row_count != row_count:
                    failures.append("all_four_fourth_field_row_count_mismatch")
                if fourth_row_count is not None and fourth_row_ok_count != fourth_row_count:
                    failures.append("all_four_fourth_field_row_ok_count_mismatch")

    native_path_raw = payload.get("native_consumer_json")
    native_sha = payload.get("native_consumer_sha256")
    input_paths: list[Path] = []
    if not isinstance(native_path_raw, str) or not native_path_raw:
        failures.append("all_four_native_consumer_json_missing")
    else:
        native_path = _resolve(native_path_raw)
        if not native_path.exists():
            failures.append("all_four_native_consumer_json_missing_on_disk")
        elif _sha256(native_path) != native_sha:
            failures.append("all_four_native_consumer_sha256_mismatch")
        else:
            input_paths, input_failures = _load_input_paths_from_native_report(native_path)
            failures.extend(input_failures)
    if source_count is not None and input_paths and len(input_paths) != source_count:
        failures.append("all_four_native_input_json_count_mismatch")
    if selected_input_json_count is None:
        failures.append("all_four_selected_input_json_count_invalid")
    elif input_paths and selected_input_json_count != len(input_paths):
        failures.append("all_four_selected_input_json_count_mismatch")
    selected_sha = payload.get("selected_input_manifest_sha256")
    post_sha = payload.get("post_native_input_manifest_sha256")
    if input_paths:
        manifest_sha = _input_manifest(input_paths)["input_manifest_sha256"]
        if selected_sha != manifest_sha:
            failures.append("all_four_selected_input_manifest_sha256_mismatch")
        if post_sha != manifest_sha:
            failures.append("all_four_post_native_input_manifest_sha256_mismatch")
    if not all_four_path.exists():
        failures.append("all_four_json_missing_on_disk")
    return input_paths, failures


def _native_args(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> argparse.Namespace:
    output_dir = _resolve(args.output_dir)
    argv = [
        "--max-inputs",
        str(args.max_inputs),
        "--min-source-count",
        str(args.min_source_count),
        "--min-total-rows",
        str(args.min_row_count),
        "--block-threads",
        str(args.block_threads),
        "--mirror-field",
        "descriptor_ptr",
        "--require-future-wna16-kernel-side-consumer-execution",
        "--require-wna16-side-consumer-variant-execution",
        "--device",
        str(args.device),
        "--offload-arch",
        str(args.offload_arch),
        "--merged-output-json",
        str(output_dir / "kernel_side_consumer_path_merged_input.json"),
        "--stub-output-json",
        str(output_dir / "kernel_side_consumer_path_typed_consumer_stub.json"),
        "--output-json",
        str(output_dir / "kernel_side_consumer_path_native_runner.json"),
    ]
    for input_path in input_paths:
        argv.extend(["--input-json", str(input_path)])
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.force_build:
        argv.append("--force-build")
    parsed = native_runner.build_parser().parse_args(argv)
    parsed.runner_json = None
    return parsed


def _run_native(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> tuple[dict[str, Any], float]:
    parsed = _native_args(args, input_paths=input_paths)
    start_ns = time.perf_counter_ns()
    report = native_runner.run_canary(parsed)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def _check_native_report(
    report: dict[str, Any],
    stub: dict[str, Any],
    *,
    input_paths: list[Path],
    input_manifest: dict[str, Any],
    all_four: dict[str, Any],
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    if report.get("passed") is not True:
        failures.append("native_report_not_passed")
    if report.get("failures") != []:
        failures.append("native_report_failures_not_empty")
    if report.get("source") != "online_merged_future_native_arg_slot_canary_runner":
        failures.append("native_report_source_mismatch")
    source_count = _int_metric(report, "selected_source_count")
    row_count = _int_metric(report, "merged_row_count")
    active_rows = _int_metric(report, "dispatch_active_rows")
    if source_count is None or source_count < min_source_count:
        failures.append("native_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("native_row_count_invalid")
    if source_count != all_four.get("source_count"):
        failures.append("native_source_count_all_four_mismatch")
    if row_count != all_four.get("row_count"):
        failures.append("native_row_count_all_four_mismatch")
    if row_count is not None and active_rows != row_count:
        failures.append("native_dispatch_active_rows_mismatch")
    if report.get("input_jsons") != [str(path) for path in input_paths]:
        failures.append("native_input_jsons_manifest_mismatch")
    if report.get("selected_input_json_count") != len(input_paths):
        failures.append("native_selected_input_json_count_mismatch")
    if report.get("selected_input_manifest_sha256") != input_manifest["input_manifest_sha256"]:
        failures.append("native_selected_input_manifest_sha256_mismatch")
    for key in (
        "require_future_wna16_typed_slot_kernel_variant",
        "require_future_wna16_kernel_accept_typed_slot",
        "require_future_wna16_kernel_side_consumer_execution",
        "require_wna16_side_consumer_variant_execution",
        "require_wna16_adjacent_typed_slot",
    ):
        if report.get(key) is not True:
            failures.append(f"{key}_not_true")
    for key in (
        "future_wna16_typed_slot_kernel_variant_all_handle_fields_read",
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read",
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read",
        "wna16_side_consumer_variant_execution_all_handle_fields_read",
    ):
        if report.get(key) is not True:
            failures.append(f"{key}_not_true")
    failures.extend(_check_false_boundary("native_report", report))
    if report.get("no_payload") is not True:
        failures.append("native_report_no_payload_not_true")

    for prefix in REQUIRED_PREFIXES:
        if stub.get(f"{prefix}_checked") is not True:
            failures.append(f"{prefix}_checked_not_true")
        if stub.get(f"{prefix}_row_count") != row_count:
            failures.append(f"{prefix}_row_count_mismatch")
        if stub.get(f"{prefix}_row_ok_count") != row_count:
            failures.append(f"{prefix}_row_ok_count_mismatch")
        if stub.get(f"{prefix}_error_count") != 0:
            failures.append(f"{prefix}_error_count_nonzero")
        if stub.get(f"{prefix}_payload_bytes") != 0:
            failures.append(f"{prefix}_payload_bytes_nonzero")
        for key in REQUIRED_PREFIX_FALSE_BOUNDARY_KEYS:
            full_key = f"{prefix}_{key}"
            if full_key not in stub:
                failures.append(f"{full_key}_missing")
            elif stub.get(full_key) is not False:
                failures.append(f"{full_key}_not_false")
        if stub.get(f"{prefix}_explicit_typed_abi_slot") is not True:
            failures.append(f"{prefix}_explicit_typed_abi_slot_not_true")
        if not _is_hex_u64(stub.get(f"{prefix}_hash_accumulator")):
            failures.append(f"{prefix}_hash_accumulator_invalid")
        if not _is_hex_u64(stub.get(f"{prefix}_handle_projection_hash_accumulator")):
            failures.append(f"{prefix}_handle_projection_hash_accumulator_invalid")
        for field in HANDLE_FIELDS:
            base = f"{prefix}_{field}_read"
            if stub.get(f"{base}_row_count") != row_count:
                failures.append(f"{base}_row_count_mismatch")
            if stub.get(f"{base}_row_ok_count") != row_count:
                failures.append(f"{base}_row_ok_count_mismatch")
            if stub.get(f"{base}_error_count") != 0:
                failures.append(f"{base}_error_count_nonzero")
            if not _is_hex_u64(stub.get(f"{base}_hash_accumulator")):
                failures.append(f"{base}_hash_invalid")
    return failures


def run_kernel_side_typed_consumer_path(args: argparse.Namespace) -> dict[str, Any]:
    all_four_path = _resolve(args.all_four_json)
    output_path = _resolve(args.output_json)
    output_dir = _resolve(args.output_dir)
    failures: list[str] = []
    all_four: dict[str, Any] | None = None
    all_four_gate_ready = False
    input_paths: list[Path] = []
    try:
        all_four = _load_json(all_four_path)
    except Exception as exc:
        failures.append(f"all_four_json_load_failed:{exc.__class__.__name__}:{exc}")
    if all_four is not None:
        input_paths, all_four_failures = _check_all_four_gate(
            all_four,
            all_four_path=all_four_path,
            min_source_count=int(args.min_source_count),
            min_row_count=int(args.min_row_count),
        )
        all_four_gate_ready = not all_four_failures
        failures.extend(all_four_failures)

    native_report: dict[str, Any] | None = None
    native_wall_ms: float | None = None
    stub_payload: dict[str, Any] | None = None
    input_manifest = _input_manifest(input_paths) if input_paths else {
        "input_json_count": 0,
        "input_manifest_sha256": None,
        "input_manifest_entries": [],
    }
    if all_four is not None and input_paths and not failures:
        try:
            native_report, native_wall_ms = _run_native(args, input_paths=input_paths)
        except Exception as exc:  # pragma: no cover - covered by tests via failure path
            failures.append(
                f"kernel_side_consumer_path_native_exception:"
                f"{exc.__class__.__name__}:{exc}"
            )
        else:
            stub_path = output_dir / "kernel_side_consumer_path_typed_consumer_stub.json"
            try:
                stub_payload = _load_json(stub_path)
            except Exception as exc:
                failures.append(
                    f"kernel_side_consumer_path_stub_load_failed:"
                    f"{exc.__class__.__name__}:{exc}"
                )
            if stub_payload is not None:
                failures.extend(
                    _check_native_report(
                        native_report,
                        stub_payload,
                        input_paths=input_paths,
                        input_manifest=input_manifest,
                        all_four=all_four,
                        min_source_count=int(args.min_source_count),
                        min_row_count=int(args.min_row_count),
                    )
                )
    elif not failures:
        failures.append("kernel_side_consumer_path_no_inputs")

    native_json = output_dir / "kernel_side_consumer_path_native_runner.json"
    merged_json = output_dir / "kernel_side_consumer_path_merged_input.json"
    stub_json = output_dir / "kernel_side_consumer_path_typed_consumer_stub.json"
    row_count = (
        native_report.get("merged_row_count")
        if native_report is not None
        else (all_four or {}).get("row_count")
    )
    source_count = (
        native_report.get("selected_source_count")
        if native_report is not None
        else (all_four or {}).get("source_count")
    )
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "kernel_side_typed_consumer_path_name": PATH_NAME,
        "kernel_side_typed_consumer_path_mode": PATH_MODE,
        "kernel_side_typed_consumer_path_source": PATH_SOURCE,
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "passed": passed,
        "failures": failures,
        "all_four_json": str(all_four_path),
        "all_four_sha256": _sha256(all_four_path) if all_four_path.exists() else None,
        "all_four_gate_ready": all_four is not None and all_four_gate_ready,
        "input_json_count": len(input_paths),
        "selected_input_manifest_sha256": input_manifest["input_manifest_sha256"],
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": native_report.get("dispatch_active_rows") if native_report else None,
        "native_consumer_json": str(native_json),
        "native_consumer_sha256": _sha256(native_json) if native_json.exists() else None,
        "merged_input_json": str(merged_json),
        "merged_input_sha256": _sha256(merged_json) if merged_json.exists() else None,
        "stub_output_json": str(stub_json),
        "stub_output_sha256": _sha256(stub_json) if stub_json.exists() else None,
        "native_consumer_executed": native_report is not None,
        "native_consumer_passed": native_report is not None and native_report.get("passed") is True,
        "native_consumer_outer_wall_ms": native_wall_ms,
        "native_consumer_wall_ms_observed_only": True,
        "future_wna16_kernel_side_consumer_execution_checked": (
            stub_payload.get("future_wna16_kernel_side_consumer_execution_checked")
            if stub_payload
            else None
        ),
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": (
            native_report.get(
                "future_wna16_kernel_side_consumer_execution_all_handle_fields_read"
            )
            if native_report
            else None
        ),
        "future_wna16_kernel_side_consumer_execution_row_count": (
            native_report.get("future_wna16_kernel_side_consumer_execution_row_count")
            if native_report
            else None
        ),
        "future_wna16_kernel_side_consumer_execution_row_ok_count": (
            native_report.get("future_wna16_kernel_side_consumer_execution_row_ok_count")
            if native_report
            else None
        ),
        "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator": (
            native_report.get(
                "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator"
            )
            if native_report
            else None
        ),
        "wna16_side_consumer_variant_execution_checked": (
            stub_payload.get("wna16_side_consumer_variant_execution_checked")
            if stub_payload
            else None
        ),
        "wna16_side_consumer_variant_execution_all_handle_fields_read": (
            native_report.get("wna16_side_consumer_variant_execution_all_handle_fields_read")
            if native_report
            else None
        ),
        "wna16_side_consumer_variant_execution_row_count": (
            native_report.get("wna16_side_consumer_variant_execution_row_count")
            if native_report
            else None
        ),
        "wna16_side_consumer_variant_execution_row_ok_count": (
            native_report.get("wna16_side_consumer_variant_execution_row_ok_count")
            if native_report
            else None
        ),
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
            native_report.get(
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
            )
            if native_report
            else None
        ),
        "independent_kernel_side_consumer_path": True,
        "explicit_typed_abi_slot": True,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    _write_json(output_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-four-json", type=Path, default=DEFAULT_ALL_FOUR_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-inputs", type=int, default=128)
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
    report = run_kernel_side_typed_consumer_path(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_pass and not report.get("passed"):
        return 1
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
