#!/usr/bin/env python3
"""Run the independent future WNA16 typed-slot execution gate.

This stage consumes the payloadless execution artifact and can rerun the
independent native typed-slot consumer as a stronger execution proof.  It still
does not pass current WNA16 fused-MoE arguments, does not dereference payloads,
and does not measure vLLM latency or TPOT.
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

from scripts import (
    run_future_wna16_typed_slot_kernel_timing_stub as timing_runner,
)
from scripts import (
    run_future_wna16_typed_slot_kernel_variant_payloadless_execution
    as payloadless_runner,
)


DEFAULT_PAYLOADLESS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_payloadless_execution_entry_args_ptr_native_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_execution_entry_args_ptr_native_v1.json"
)

EXECUTION_NAME = "premap_future_wna16_typed_slot_kernel_variant_execution_v1"
EXECUTION_MODE = "independent_future_wna16_typed_slot_kernel_variant_execution"
EXECUTION_SOURCE = "premap_future_wna16_typed_slot_payloadless_execution_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
KERNEL_SIDE_TYPED_PATH_PREFIX = "future_wna16_kernel_side_typed_consumer_path"

EXPECTED_PAYLOADLESS_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_variant_payloadless_execution",
    "passed": True,
    "payloadless_execution_ready": True,
    "payloadless_execution_gate_ready": True,
    "payloadless_execution_native_requested": True,
    "payloadless_execution_native_executed": True,
    "payloadless_execution_native_passed": True,
    "payloadless_execution_native_artifact_ready": True,
    "payloadless_execution_lab_preflight_ready": True,
    "all_four_field_consumer_ready": True,
    "all_four_field_consumer_fields_read": True,
    "all_four_field_consumer_hashes_valid": True,
    "future_wna16_kernel_side_typed_consumer_path_ready": True,
    "future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
    "entry_args_ptr_required": True,
    "entry_args_ptr_sweep_device": 1,
    "entry_args_ptr_sweep_window_size": 512,
    "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
    "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
    "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
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


def _check_payloadless(
    payloadless: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
    min_repeat_count: int,
) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_PAYLOADLESS_FLAGS.items():
        if payloadless.get(key) != expected:
            failures.append(
                f"payloadless_{key}_mismatch:"
                f"{payloadless.get(key)!r}!={expected!r}"
            )
    if payloadless.get("failures") != []:
        failures.append("payloadless_failures_not_empty")
    source_count = _int_metric(payloadless, "source_count")
    row_count = _int_metric(payloadless, "row_count")
    row_ok_count = _int_metric(payloadless, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("payloadless_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("payloadless_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("payloadless_row_ok_count_mismatch")
    if payloadless.get("field_names") != list(HANDLE_FIELDS):
        failures.append("payloadless_field_names_mismatch")
    row_ok_counts = payloadless.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("payloadless_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = payloadless.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("payloadless_field_read_hashes_missing")
        field_hashes = {}
    if set(row_ok_counts) != set(HANDLE_FIELDS):
        failures.append("payloadless_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != set(HANDLE_FIELDS):
        failures.append("payloadless_field_read_hashes_keys_mismatch")
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"payloadless_{field}_read_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"payloadless_{field}_read_hash_invalid")
    for key in (
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
        "fourth_field_handoff_field_read_hash",
        "fourth_field_handoff_runner_hash",
    ):
        if not _is_hex_u64(payloadless.get(key)):
            failures.append(f"payloadless_{key}_invalid")
    loaded_children: dict[str, dict[str, Any]] = {}
    for path_key, sha_key in (
        ("benchmark_json", "benchmark_sha256"),
        (
            "payloadless_execution_timing_stub_json",
            "payloadless_execution_timing_stub_sha256",
        ),
        ("payloadless_execution_runner_json", "payloadless_execution_runner_sha256"),
    ):
        path_value = payloadless.get(path_key)
        sha_value = payloadless.get(sha_key)
        if not isinstance(path_value, str) or not path_value:
            failures.append(f"payloadless_{path_key}_missing")
            continue
        if not _is_sha256_hex(sha_value):
            failures.append(f"payloadless_{sha_key}_invalid")
            continue
        resolved = _resolve(path_value)
        if not resolved.exists():
            failures.append(f"payloadless_{path_key}_not_found")
            continue
        if _sha256(resolved) != sha_value:
            failures.append(f"payloadless_{sha_key}_mismatch")
            continue
        try:
            loaded_children[path_key] = _load_json(resolved)
        except Exception as exc:
            failures.append(
                f"payloadless_{path_key}_json_invalid:{exc.__class__.__name__}:{exc}"
            )
    benchmark = loaded_children.get("benchmark_json")
    if benchmark is None:
        failures.append("payloadless_benchmark_json_not_validated")
    else:
        failures.extend(
            "payloadless_benchmark_" + item
            for item in payloadless_runner._check_benchmark(  # noqa: SLF001
                benchmark,
                min_source_count=min_source_count,
                min_row_count=min_row_count,
                min_repeat_count=min_repeat_count,
            )
        )
        repeat_failures, timing_stub_seed = (
            payloadless_runner._check_benchmark_repeat_artifacts(  # noqa: SLF001
                benchmark,
                min_source_count=min_source_count,
                min_row_count=min_row_count,
                min_repeat_count=min_repeat_count,
            )
        )
        failures.extend("payloadless_benchmark_" + item for item in repeat_failures)
        if timing_stub_seed is None:
            failures.append("payloadless_benchmark_timing_stub_seed_missing")
        else:
            timing_stub_child = loaded_children.get(
                "payloadless_execution_timing_stub_json"
            )
            if timing_stub_child is None:
                failures.append("payloadless_timing_stub_json_not_validated")
            else:
                failures.extend(
                    "payloadless_timing_stub_"
                    + item
                    for item in payloadless_runner._check_execution_timing_stub(  # noqa: SLF001
                        timing_stub_child,
                        seed=timing_stub_seed,
                        min_source_count=min_source_count,
                        min_row_count=min_row_count,
                    )
                )
                stable_timing_keys = (
                    "source_count",
                    "row_count",
                    "row_ok_count",
                    "field_names",
                    "field_read_row_ok_counts",
                    "field_read_hashes",
                    "row_hash_accumulator",
                    "handle_projection_hash_accumulator",
                    "fourth_field_handoff_ready",
                    "fourth_field_handoff_evidence_path",
                    "fourth_field_handoff_evidence_sha256",
                    "fourth_field_handoff_source_count",
                    "fourth_field_handoff_row_count",
                    "fourth_field_handoff_row_ok_count",
                    "fourth_field_handoff_field_read_hash",
                    "fourth_field_handoff_runner_hash",
                    "all_four_field_consumer_ready",
                    "all_four_field_consumer_fields_read",
                    "all_four_field_consumer_hashes_valid",
                    "all_four_field_consumer_source_count",
                    "all_four_field_consumer_row_count",
                    "all_four_field_consumer_row_ok_count",
                    "all_four_field_consumer_fourth_field_path_label",
                    "all_four_field_consumer_fourth_field_sha256",
                    "future_wna16_kernel_side_typed_consumer_path_ready",
                    "future_wna16_kernel_side_typed_consumer_path_hashes_valid",
                    "future_wna16_kernel_side_typed_consumer_path_evidence_path",
                    "future_wna16_kernel_side_typed_consumer_path_evidence_sha256",
                    "future_wna16_kernel_side_typed_consumer_path_source_count",
                    "future_wna16_kernel_side_typed_consumer_path_input_json_count",
                    "future_wna16_kernel_side_typed_consumer_path_row_count",
                    "future_wna16_kernel_side_typed_consumer_path_row_ok_count",
                    "future_wna16_kernel_side_typed_consumer_path_all_four_sha256",
                    "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256",
                    "entry_args_ptr_required",
                    "entry_args_ptr_sweep_json",
                    "entry_args_ptr_sweep_sha256",
                    "entry_args_ptr_sweep_check_json",
                    "entry_args_ptr_sweep_check_sha256",
                    "entry_args_ptr_sweep_row_count",
                    "entry_args_ptr_sweep_check_row_count",
                    "entry_args_ptr_sweep_device",
                    "entry_args_ptr_sweep_window_size",
                    "entry_args_ptr_sweep_mirror_fields",
                    "entry_args_ptr_sweep_require_kernel_arg_packet_abi",
                    "entry_args_ptr_sweep_require_kernel_entry_args_abi",
                    "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi",
                )
                for key in stable_timing_keys:
                    if timing_stub_child.get(key) != timing_stub_seed.get(key):
                        failures.append(f"payloadless_timing_stub_{key}_mismatch")
                runner_json = payloadless.get("payloadless_execution_runner_json")
                runner_sha256 = payloadless.get("payloadless_execution_runner_sha256")
                if timing_stub_child.get("runner_json") != runner_json:
                    failures.append("payloadless_timing_stub_runner_json_mismatch")
                if timing_stub_child.get("runner_sha256") != runner_sha256:
                    failures.append("payloadless_timing_stub_runner_sha256_mismatch")
                if timing_stub_seed.get("runner_sha256") != runner_sha256:
                    failures.append("payloadless_seed_runner_sha256_mismatch")
    runner_child = loaded_children.get("payloadless_execution_runner_json")
    if runner_child is None:
        failures.append("payloadless_runner_json_not_validated")
    else:
        input_jsons = runner_child.get("online_prelaunch_input_jsons")
        if not isinstance(input_jsons, list) or not input_jsons:
            input_jsons = runner_child.get("input_jsons")
        if not isinstance(input_jsons, list) or not input_jsons:
            failures.append("payloadless_runner_input_jsons_missing")
        if "passed" in runner_child and runner_child.get("passed") is not True:
            failures.append("payloadless_runner_passed_mismatch")
        if "failures" in runner_child and runner_child.get("failures") != []:
            failures.append("payloadless_runner_failures_not_empty")
        optional_safety = {
            "no_payload": True,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
        }
        for key, expected in optional_safety.items():
            if key in runner_child and runner_child.get(key) != expected:
                failures.append(f"payloadless_runner_{key}_mismatch")
        for key in (
            "source_count",
            "row_count",
            "row_ok_count",
            "field_names",
            "field_read_row_ok_counts",
            "field_read_hashes",
            "row_hash_accumulator",
            "handle_projection_hash_accumulator",
            "fourth_field_handoff_ready",
            "fourth_field_handoff_evidence_path",
            "fourth_field_handoff_evidence_sha256",
            "fourth_field_handoff_source_count",
            "fourth_field_handoff_row_count",
            "fourth_field_handoff_row_ok_count",
            "fourth_field_handoff_field_read_hash",
            "fourth_field_handoff_runner_hash",
            "all_four_field_consumer_ready",
            "all_four_field_consumer_fields_read",
            "all_four_field_consumer_hashes_valid",
            "all_four_field_consumer_source_count",
            "all_four_field_consumer_row_count",
            "all_four_field_consumer_row_ok_count",
            "all_four_field_consumer_fourth_field_path_label",
            "all_four_field_consumer_fourth_field_sha256",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_ready",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_hashes_valid",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_path",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_sha256",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_source_count",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_input_json_count",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_row_count",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_row_ok_count",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_sha256",
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_selected_input_manifest_sha256",
            "entry_args_ptr_required",
            "entry_args_ptr_sweep_json",
            "entry_args_ptr_sweep_sha256",
            "entry_args_ptr_sweep_check_json",
            "entry_args_ptr_sweep_check_sha256",
            "entry_args_ptr_sweep_row_count",
            "entry_args_ptr_sweep_check_row_count",
            "entry_args_ptr_sweep_device",
            "entry_args_ptr_sweep_window_size",
            "entry_args_ptr_sweep_mirror_fields",
            "entry_args_ptr_sweep_require_kernel_arg_packet_abi",
            "entry_args_ptr_sweep_require_kernel_entry_args_abi",
            "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi",
        ):
            if payloadless.get(key) != benchmark.get(key):
                failures.append(f"payloadless_benchmark_{key}_mismatch")
    if payloadless.get("entry_args_ptr_sweep_mirror_fields") != list(HANDLE_FIELDS):
        failures.append("payloadless_entry_args_ptr_sweep_mirror_fields_mismatch")
    if _int_metric(payloadless, "entry_args_ptr_sweep_row_count") is None:
        failures.append("payloadless_entry_args_ptr_sweep_row_count_invalid")
    if _int_metric(payloadless, "entry_args_ptr_sweep_check_row_count") is None:
        failures.append("payloadless_entry_args_ptr_sweep_check_row_count_invalid")
    return failures


def _build_timing_args(
    args: argparse.Namespace,
    *,
    payloadless: dict[str, Any],
    output_dir: Path,
) -> argparse.Namespace:
    timing_stub_json = _resolve(payloadless["payloadless_execution_timing_stub_json"])
    timing_stub = _load_json(timing_stub_json)
    entrypoint_json = timing_stub.get("entrypoint_json")
    runner_json = payloadless.get("payloadless_execution_runner_json")
    argv = [
        "--entrypoint-json",
        str(entrypoint_json),
        "--runner-json",
        str(runner_json),
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
        str(output_dir / "future_wna16_variant_execution_timing_stub.json"),
        "--canary-output-json",
        str(output_dir / "future_wna16_variant_execution_canary.json"),
        "--source-manifest-json",
        str(output_dir / "future_wna16_variant_execution_source_manifest.json"),
        "--merged-output-json",
        str(output_dir / "future_wna16_variant_execution_merged_input.json"),
        "--stub-output-json",
        str(output_dir / "future_wna16_variant_execution_typed_consumer_stub.json"),
    ]
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.force_build:
        argv.append("--force-build")
    return timing_runner.build_parser().parse_args(argv)


def _run_native_execution(
    args: argparse.Namespace,
    *,
    payloadless: dict[str, Any],
    output_dir: Path,
) -> tuple[dict[str, Any], float]:
    timing_args = _build_timing_args(args, payloadless=payloadless, output_dir=output_dir)
    start_ns = time.perf_counter_ns()
    report = timing_runner.run_timing_stub(timing_args)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def _check_native_execution(
    report: dict[str, Any],
    *,
    payloadless: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "passed": True,
        "native_stub_requested": True,
        "native_stub_executed": True,
        "native_stub_passed": True,
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
    for key, value in expected.items():
        if report.get(key) != value:
            failures.append(
                f"native_execution_{key}_mismatch:{report.get(key)!r}!={value!r}"
            )
    for key in ("source_count", "row_count", "row_ok_count"):
        if report.get(key) != payloadless.get(key):
            failures.append(f"native_execution_{key}_mismatch")
    if report.get("field_names") != list(HANDLE_FIELDS):
        failures.append("native_execution_field_names_mismatch")
    for field in HANDLE_FIELDS:
        expected_count = payloadless.get("row_count")
        if report.get("field_read_row_ok_counts", {}).get(field) != expected_count:
            failures.append(f"native_execution_{field}_row_ok_count_mismatch")
        expected_hash = payloadless.get("field_read_hashes", {}).get(field)
        if report.get("field_read_hashes", {}).get(field) != expected_hash:
            failures.append(f"native_execution_{field}_hash_mismatch")
    return failures


def run_variant_execution(args: argparse.Namespace) -> dict[str, Any]:
    payloadless_path = _resolve(args.payloadless_json)
    output_path = _resolve(args.output_json)
    output_dir = (
        _resolve(args.execution_output_dir)
        if args.execution_output_dir
        else output_path.parent / output_path.stem
    )
    failures: list[str] = []
    payloadless: dict[str, Any] = {}
    try:
        payloadless = _load_json(payloadless_path)
    except Exception as exc:
        failures.append(
            f"payloadless_json_load_failed:{exc.__class__.__name__}:{exc}"
        )
    payloadless_failures: list[str] = []
    if payloadless:
        payloadless_failures = _check_payloadless(
            payloadless,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
            min_repeat_count=args.min_repeat_count,
        )
        failures.extend(payloadless_failures)
    gate_ready = bool(payloadless) and not payloadless_failures
    native_report: dict[str, Any] | None = None
    native_outer_wall_ms: float | None = None
    if args.run_native_execution and gate_ready:
        try:
            native_report, native_outer_wall_ms = _run_native_execution(
                args,
                payloadless=payloadless,
                output_dir=output_dir,
            )
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(
                "future_variant_execution_exception:"
                f"{exc.__class__.__name__}:{exc}"
            )
        if native_report is not None:
            failures.extend(
                _check_native_execution(native_report, payloadless=payloadless)
            )
    elif args.run_native_execution:
        failures.append("future_variant_execution_skipped_due_to_gate_failure")
    if args.require_native_execution and native_report is None:
        failures.append("future_variant_execution_required_but_not_executed")
    payloadless_sha: str | None = None
    if payloadless_path.exists():
        payloadless_sha = _sha256(payloadless_path)
    native_output = output_dir / "future_wna16_variant_execution_timing_stub.json"
    native_output_sha: str | None = None
    if native_report is not None and native_output.exists():
        native_output_sha = _sha256(native_output)
    passed = not failures
    native_artifact_ready = (
        native_report is not None
        and native_report.get("passed") is True
        and native_output_sha is not None
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
        "execution_name": EXECUTION_NAME,
        "execution_mode": EXECUTION_MODE,
        "execution_source": EXECUTION_SOURCE,
        "passed": passed,
        "failures": failures,
        "payloadless_json": str(payloadless_path),
        "payloadless_sha256": payloadless_sha,
        "source_count": payloadless.get("source_count"),
        "row_count": payloadless.get("row_count"),
        "row_ok_count": payloadless.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": payloadless.get("field_read_row_ok_counts"),
        "field_read_hashes": payloadless.get("field_read_hashes"),
        "row_hash_accumulator": payloadless.get("row_hash_accumulator"),
        "handle_projection_hash_accumulator": payloadless.get(
            "handle_projection_hash_accumulator"
        ),
        "payloadless_gate_ready": gate_ready,
        "future_wna16_variant_execution_ready": passed,
        "future_wna16_variant_execution_native_requested": bool(
            args.run_native_execution
        ),
        "future_wna16_variant_execution_native_executed": native_report is not None,
        "future_wna16_variant_execution_native_passed": (
            native_report.get("passed") if native_report else None
        ),
        "future_wna16_variant_execution_native_artifact_ready": native_artifact_ready,
        "future_wna16_variant_execution_native_host_wall_ms": (
            native_report.get("native_stub_host_wall_ms") if native_report else None
        ),
        "future_wna16_variant_execution_outer_wall_ms": native_outer_wall_ms,
        "future_wna16_variant_execution_native_json": str(native_output),
        "future_wna16_variant_execution_native_sha256": native_output_sha,
        "future_wna16_variant_execution_scope": (
            "independent_native_typed_slot_kernel_variant_execution"
        ),
        "future_wna16_variant_execution_not_current_wna16_kernel": True,
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
        "device": int(args.device),
        "block_threads": int(args.block_threads),
        "offload_arch": str(args.offload_arch),
        "hip_visible_devices": args.hip_visible_devices,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot kernel variant execution failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and optionally run the independent future WNA16 "
            "typed-slot kernel variant execution path. This does not pass "
            "current WNA16 fused-MoE kernel args and does not move payload."
        )
    )
    parser.add_argument("--payloadless-json", default=str(DEFAULT_PAYLOADLESS_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--execution-output-dir")
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
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
    report = run_variant_execution(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
