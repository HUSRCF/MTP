#!/usr/bin/env python3
"""Build a readiness artifact for the future WNA16 typed-slot benchmark harness.

This is intentionally not a WNA16 fused-MoE benchmark.  It consumes the strict
premap lab preflight artifact plus the online merged future WNA16 typed-slot
consumer runner artifact, then verifies that the no-mutation typed ABI evidence
is coherent enough to start a separate future-kernel benchmark harness.

The safety envelope remains closed:

* no payload dereference,
* no current WNA16 kernel-argument pass,
* no current WNA16 arg reinterpretation,
* no kernel launch mutation.
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


DEFAULT_PREFLIGHT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_default_strict_20260619_entry_args_ptr_required_abs_python_portable.json"
)
DEFAULT_PREFLIGHT_CHECK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_strict_future_wna16_kernel_side_path_gate.check.json"
)
DEFAULT_RUNNER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_wna16_real_typed_slot_consumer_same_source_128strict_preflight_runner.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "wna16_typed_slot_benchmark_harness_entry_args_ptr_preflight_v1.json"
)
DEFAULT_MIN_ENTRY_ARGS_PTR_ROW_COUNT = 513

HARNESS_NAME = "premap_wna16_typed_slot_benchmark_harness_v1"
HARNESS_MODE = "readonly_future_wna16_typed_slot_benchmark_harness"
EXPECTED_PREFLIGHT_STAGE = "implement_wna16_typed_slot_benchmark_harness"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_kernel_variant_entrypoint"
WNA16_EXECUTION_PREFIX = "future_wna16_kernel_side_consumer_execution"
PREFLIGHT_EXECUTION_PREFIX = (
    "default_kernel_consumer_wna16_kernel_side_execution"
)
PREFLIGHT_FOURTH_FIELD_PREFIX = (
    "default_kernel_consumer_future_wna16_fourth_field_handoff"
)
PREFLIGHT_ALL_FOUR_READY_PREFIX = (
    "default_kernel_consumer_future_wna16_all_four_field_consumer"
)
PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX = (
    "default_kernel_consumer_future_wna16_all_four_consumer"
)
PREFLIGHT_KERNEL_SIDE_TYPED_PATH_READY_KEY = (
    "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
)
PREFLIGHT_KERNEL_SIDE_TYPED_PATH_HASHES_READY_KEY = (
    "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid"
)
PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX = (
    "default_kernel_consumer_future_wna16_kernel_side_typed_path"
)
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
ENTRY_ARGS_PTR_SWEEP_LABEL = (
    "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json"
)
ENTRY_ARGS_PTR_SWEEP_CHECK_LABEL = (
    "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json"
)
ENTRY_ARGS_PTR_SWEEP_SUFFIX = (
    "outputs/reports/premap_kernel_consumer/"
    "online_merged_future_native_arg_slot_all_field_window_sweep_kernel_entry_args_ptr_strict_20260619.json"
)
ENTRY_ARGS_PTR_SWEEP_CHECK_SUFFIX = (
    "outputs/reports/premap_kernel_consumer/"
    "online_merged_future_native_arg_slot_all_field_window_sweep_kernel_entry_args_ptr_strict_20260619.check.json"
)
ENTRY_ARGS_PTR_SWEEP_SOURCE = (
    "online_merged_future_native_arg_slot_all_field_window_sweep_runner"
)
ENTRY_ARGS_PTR_SWEEP_CHECK_SOURCE = (
    "online_merged_future_native_arg_slot_all_field_window_sweep_check"
)
EXPECTED_RUNNER_FLAGS: dict[str, Any] = {
    f"{WNA16_EXECUTION_PREFIX}_checked": True,
    f"{WNA16_EXECUTION_PREFIX}_abi_name": (
        "premap_future_wna16_kernel_side_consumer_execution_v1"
    ),
    f"{WNA16_EXECUTION_PREFIX}_mode": (
        "readonly_future_wna16_kernel_side_consumer_execution"
    ),
    f"{WNA16_EXECUTION_PREFIX}_source": (
        "premap_future_wna16_kernel_accept_typed_slot_v1"
    ),
    f"{WNA16_EXECUTION_PREFIX}_packet_chain_depth": 16,
    f"{WNA16_EXECUTION_PREFIX}_all_handle_fields_read": True,
    f"{WNA16_EXECUTION_PREFIX}_error_count": 0,
    f"{WNA16_EXECUTION_PREFIX}_payload_bytes": 0,
    f"{WNA16_EXECUTION_PREFIX}_payload_deref_allowed": False,
    f"{WNA16_EXECUTION_PREFIX}_kernel_arg_pass_allowed": False,
    f"{WNA16_EXECUTION_PREFIX}_passed_to_kernel": False,
    f"{WNA16_EXECUTION_PREFIX}_changes_kernel_launch_args": False,
    f"{WNA16_EXECUTION_PREFIX}_current_wna16_arg_compatible": False,
    f"{WNA16_EXECUTION_PREFIX}_requires_wna16_arg_reinterpretation": False,
    f"{WNA16_EXECUTION_PREFIX}_explicit_typed_abi_slot": True,
    f"{WNA16_EXECUTION_PREFIX}_reuses_current_wna16_arg_slot": False,
}
EXPECTED_PREFLIGHT_FLAGS: dict[str, Any] = {
    "passed": True,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_ready": True,
    "default_kernel_consumer_wna16_kernel_side_execution_ready": True,
    "default_kernel_consumer_wna16_benchmark_ready": False,
    "default_kernel_consumer_next_runtime_stage": EXPECTED_PREFLIGHT_STAGE,
    "default_kernel_consumer_wna16_benchmark_prerequisites_ready": False,
}
EXPECTED_PREFLIGHT_FOURTH_FIELD_FLAGS: dict[str, Any] = {
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_evidence_passed": True,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_first_field": "scale_metadata_handle",
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_second_field": "aux_metadata_handle",
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_third_field": "packed_weight_descriptor",
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_fourth_field": "descriptor_ptr",
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_fourth_field_kind": 1,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_fourth_field_mask": 1,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_previous_gate_ready": True,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_native_requested": True,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_native_executed": True,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_native_passed": True,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_live_enabled": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_block_reason": (
        "fourth_field_handoff_live_disabled"
    ),
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_payload_bytes": 0,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_expected_payload_bytes": 0,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_payload_deref_allowed": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_kernel_arg_pass_allowed": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_passed_to_kernel": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_changes_kernel_launch_args": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_current_wna16_arg_compatible": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_requires_wna16_arg_reinterpretation": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_uses_current_wna16_args": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_passes_current_wna16_args": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_measures_tpot": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_measures_vllm_latency": False,
    f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_wna16_benchmark_ready": False,
}
EXPECTED_PREFLIGHT_ALL_FOUR_FLAGS: dict[str, Any] = {
    f"{PREFLIGHT_ALL_FOUR_READY_PREFIX}_ready": True,
    f"{PREFLIGHT_ALL_FOUR_READY_PREFIX}_fields_read": True,
    f"{PREFLIGHT_ALL_FOUR_READY_PREFIX}_hashes_valid": True,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_evidence_passed": True,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_stage_type": "lab_gate",
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_bench_semantics": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_native_executed": True,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_native_passed": True,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_future_kernel_side_all_fields_read": True,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_wna16_side_all_fields_read": True,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_payload_bytes": 0,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_payload_deref_allowed": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_kernel_arg_pass_allowed": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_passed_to_kernel": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_changes_kernel_launch_args": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_current_wna16_arg_compatible": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_requires_wna16_arg_reinterpretation": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_measures_tpot": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_measures_vllm_latency": False,
    f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_wna16_benchmark_ready": False,
}
EXPECTED_PREFLIGHT_EXECUTION_FLAGS: dict[str, Any] = {
    f"{PREFLIGHT_EXECUTION_PREFIX}_required": True,
    f"{PREFLIGHT_EXECUTION_PREFIX}_checked": True,
    f"{PREFLIGHT_EXECUTION_PREFIX}_name": (
        "premap_future_wna16_kernel_side_consumer_execution_v1"
    ),
    f"{PREFLIGHT_EXECUTION_PREFIX}_mode": (
        "readonly_future_wna16_kernel_side_consumer_execution"
    ),
    f"{PREFLIGHT_EXECUTION_PREFIX}_source": (
        "premap_future_wna16_kernel_accept_typed_slot_v1"
    ),
    f"{PREFLIGHT_EXECUTION_PREFIX}_packet_chain_depth": 16,
    f"{PREFLIGHT_EXECUTION_PREFIX}_all_handle_fields_read": True,
    f"{PREFLIGHT_EXECUTION_PREFIX}_error_count": 0,
    f"{PREFLIGHT_EXECUTION_PREFIX}_payload_bytes": 0,
    f"{PREFLIGHT_EXECUTION_PREFIX}_payload_deref_allowed": False,
    f"{PREFLIGHT_EXECUTION_PREFIX}_kernel_arg_pass_allowed": False,
    f"{PREFLIGHT_EXECUTION_PREFIX}_passed_to_kernel": False,
    f"{PREFLIGHT_EXECUTION_PREFIX}_changes_kernel_launch_args": False,
    f"{PREFLIGHT_EXECUTION_PREFIX}_current_wna16_arg_compatible": False,
    f"{PREFLIGHT_EXECUTION_PREFIX}_requires_wna16_arg_reinterpretation": False,
    f"{PREFLIGHT_EXECUTION_PREFIX}_explicit_typed_abi_slot": True,
    f"{PREFLIGHT_EXECUTION_PREFIX}_reuses_current_wna16_arg_slot": False,
}
EXPECTED_PREFLIGHT_KERNEL_SIDE_TYPED_PATH_FLAGS: dict[str, Any] = {
    PREFLIGHT_KERNEL_SIDE_TYPED_PATH_READY_KEY: True,
    PREFLIGHT_KERNEL_SIDE_TYPED_PATH_HASHES_READY_KEY: True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_passed": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_artifact_kind": (
        "future_wna16_kernel_side_typed_consumer_path"
    ),
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_name": (
        "premap_future_wna16_kernel_side_typed_consumer_path_v1"
    ),
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_mode": (
        "independent_future_wna16_kernel_side_typed_consumer_path"
    ),
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_source": (
        "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
    ),
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_stage_type": "lab_gate",
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_bench_semantics": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_gate_ready": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_native_executed": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_native_passed": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_independent_path": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_explicit_typed_abi_slot": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_future_kernel_side_checked": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_future_kernel_side_all_fields_read": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_wna16_side_checked": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_wna16_side_all_fields_read": True,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_payload_bytes": 0,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_payload_deref_allowed": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_kernel_arg_pass_allowed": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_passed_to_kernel": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_changes_kernel_launch_args": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_current_wna16_arg_compatible": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_requires_wna16_arg_reinterpretation": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_uses_current_wna16_args": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_measures_tpot": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_measures_vllm_latency": False,
    f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_wna16_benchmark_ready": False,
}
HASH_KEYS = (
    f"{WNA16_EXECUTION_PREFIX}_hash_accumulator",
    f"{WNA16_EXECUTION_PREFIX}_handle_projection_hash_accumulator",
    f"{WNA16_EXECUTION_PREFIX}_descriptor_ptr_read_hash_accumulator",
    f"{WNA16_EXECUTION_PREFIX}_packed_weight_descriptor_read_hash_accumulator",
    f"{WNA16_EXECUTION_PREFIX}_scale_metadata_handle_read_hash_accumulator",
    f"{WNA16_EXECUTION_PREFIX}_aux_metadata_handle_read_hash_accumulator",
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _runner_key_values(runner: dict[str, Any], key: str) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    top_keys = [key]
    if key == f"{WNA16_EXECUTION_PREFIX}_abi_name":
        top_keys.append(f"{WNA16_EXECUTION_PREFIX}_name")
    for top_key in top_keys:
        if top_key in runner:
            values.append((f"runner.{top_key}", runner[top_key]))
    stub_summary = runner.get("stub_summary")
    if isinstance(stub_summary, dict) and key in stub_summary:
        values.append(("stub_summary", stub_summary[key]))
    return values


def _runner_value(runner: dict[str, Any], key: str) -> Any:
    values = _runner_key_values(runner, key)
    return values[0][1] if values else None


def _runner_int_metric(runner: dict[str, Any], key: str) -> int | None:
    value = _runner_value(runner, key)
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


def _path_label_matches(value: Any, expected_suffix: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    normalized_value = value.replace("\\", "/")
    normalized_expected = expected_suffix.replace("\\", "/")
    return normalized_value == normalized_expected or normalized_value.endswith(
        "/" + normalized_expected
    )


def _required_evidence_rows(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    check = preflight.get("default_readonly_gate_required_evidence_check")
    if not isinstance(check, dict):
        return []
    rows = check.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _find_evidence_row(rows: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("label") == label:
            return row
    return None


def _check_evidence_row(
    row: dict[str, Any] | None,
    failures: list[str],
    *,
    label: str,
    expected_suffix: str,
) -> Path | None:
    if row is None:
        failures.append(f"{label}_required_evidence_row_missing")
        return None
    if row.get("exists") is not True:
        failures.append(f"{label}_required_evidence_missing")
    if row.get("valid_json") is not True:
        failures.append(f"{label}_required_evidence_invalid_json")
    if row.get("passed_value") is not True:
        failures.append(f"{label}_required_evidence_not_passed")
    if row.get("failures_value") not in ([], None):
        failures.append(f"{label}_required_evidence_failures_not_empty")
    if not _is_sha256_hex(row.get("sha256")):
        failures.append(f"{label}_required_evidence_sha256_invalid")
    path_label = row.get("path_label") or row.get("path")
    if not _path_label_matches(path_label, expected_suffix):
        failures.append(f"{label}_required_evidence_path_mismatch")
    path_value = row.get("path")
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{label}_required_evidence_path_missing")
        return None
    return _resolve(path_value)


def _check_artifact_sha(
    path: Path,
    row: dict[str, Any] | None,
    failures: list[str],
    *,
    label: str,
) -> str | None:
    try:
        actual_sha = _sha256(path)
    except OSError:
        failures.append(f"{label}_artifact_sha256_unreadable")
        return None
    expected_sha = row.get("sha256") if isinstance(row, dict) else None
    if not _is_sha256_hex(expected_sha):
        failures.append(f"{label}_required_evidence_sha256_invalid")
    elif actual_sha != expected_sha:
        failures.append(f"{label}_artifact_sha256_mismatch")
    return actual_sha


def _check_entry_args_ptr_sweep_payload(
    payload: dict[str, Any],
    failures: list[str],
    *,
    min_row_count: int,
) -> int | None:
    if payload.get("passed") is not True:
        failures.append("entry_args_ptr_sweep_not_passed")
    if payload.get("source") != ENTRY_ARGS_PTR_SWEEP_SOURCE:
        failures.append("entry_args_ptr_sweep_source_mismatch")
    if payload.get("device") != 1:
        failures.append("entry_args_ptr_sweep_device_mismatch")
    if payload.get("window_size") != 512:
        failures.append("entry_args_ptr_sweep_window_size_mismatch")
    if payload.get("mirror_fields") != list(HANDLE_FIELDS):
        failures.append("entry_args_ptr_sweep_mirror_fields_mismatch")
    for key in (
        "require_kernel_arg_packet_abi",
        "require_kernel_entry_args_abi",
        "require_kernel_entry_args_ptr_abi",
    ):
        if payload.get(key) is not True:
            failures.append(f"entry_args_ptr_sweep_{key}_not_required")
    for key, expected in (
        ("payload_bytes", 0),
        ("passed_to_kernel", False),
        ("changes_kernel_launch_args", False),
    ):
        if payload.get(key) != expected:
            failures.append(f"entry_args_ptr_sweep_{key}_mismatch")
    optional_safety_fields = {
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
    }
    for key, expected in optional_safety_fields.items():
        if key in payload and payload.get(key) != expected:
            failures.append(f"entry_args_ptr_sweep_{key}_mismatch")
    row_counts = payload.get("row_counts")
    if not isinstance(row_counts, dict):
        failures.append("entry_args_ptr_sweep_row_counts_missing")
        return None
    counts: list[int] = []
    for field in HANDLE_FIELDS:
        count = row_counts.get(field)
        if not isinstance(count, int) or isinstance(count, bool):
            failures.append(f"entry_args_ptr_sweep_{field}_row_count_invalid")
        else:
            counts.append(count)
    if not counts:
        return None
    row_count = counts[0]
    if any(count != row_count for count in counts):
        failures.append("entry_args_ptr_sweep_row_count_mismatch")
    window_size = _int_metric(payload, "window_size")
    if window_size is not None and row_count <= window_size:
        failures.append("entry_args_ptr_sweep_row_count_not_above_window")
    if row_count < min_row_count:
        failures.append("entry_args_ptr_sweep_row_count_too_small")
    field_reports = payload.get("field_reports")
    if not isinstance(field_reports, dict):
        failures.append("entry_args_ptr_sweep_field_reports_missing")
    else:
        for field in HANDLE_FIELDS:
            report = field_reports.get(field)
            if not isinstance(report, dict):
                failures.append(f"entry_args_ptr_sweep_{field}_field_report_missing")
                continue
            if report.get("passed") is not True:
                failures.append(f"entry_args_ptr_sweep_{field}_field_report_not_passed")
            if report.get("row_count") != row_count:
                failures.append(f"entry_args_ptr_sweep_{field}_field_report_row_count_mismatch")
            if report.get("windows_checked") != ["full", "head", "middle", "tail"]:
                failures.append(f"entry_args_ptr_sweep_{field}_windows_checked_mismatch")
            if report.get("check_failures") not in ([], None):
                failures.append(f"entry_args_ptr_sweep_{field}_check_failures_not_empty")
            if report.get("sweep_failures") not in ([], None):
                failures.append(f"entry_args_ptr_sweep_{field}_sweep_failures_not_empty")
    return row_count


def _check_entry_args_ptr_sweep_check_payload(
    payload: dict[str, Any],
    failures: list[str],
    *,
    sweep_path: Path | None,
    sweep_row_count: int | None,
    min_row_count: int,
) -> int | None:
    if payload.get("passed") is not True:
        failures.append("entry_args_ptr_sweep_check_not_passed")
    if payload.get("source") != ENTRY_ARGS_PTR_SWEEP_CHECK_SOURCE:
        failures.append("entry_args_ptr_sweep_check_source_mismatch")
    if payload.get("require_child_kernel_arg_packet_abi") is not True:
        failures.append("entry_args_ptr_sweep_check_requires_child_kernel_arg_packet_missing")
    if payload.get("require_child_kernel_entry_args_abi") is not True:
        failures.append("entry_args_ptr_sweep_check_requires_child_kernel_entry_args_missing")
    if payload.get("require_child_kernel_entry_args_ptr_abi") is not True:
        failures.append("entry_args_ptr_sweep_check_requires_child_kernel_entry_args_ptr_missing")
    if payload.get("mirror_fields_checked") != list(HANDLE_FIELDS):
        failures.append("entry_args_ptr_sweep_check_mirror_fields_mismatch")
    if payload.get("expected_window_size") != 512:
        failures.append("entry_args_ptr_sweep_check_window_size_mismatch")
    observed_sweep = payload.get("all_field_window_sweep_json")
    if sweep_path is not None and not _path_label_matches(
        observed_sweep,
        str(sweep_path.relative_to(REPO_ROOT))
        if sweep_path.is_relative_to(REPO_ROOT)
        else str(sweep_path),
    ):
        failures.append("entry_args_ptr_sweep_check_child_path_mismatch")
    row_count = _int_metric(payload, "row_count")
    if row_count is None:
        failures.append("entry_args_ptr_sweep_check_row_count_invalid")
        return None
    if row_count < min_row_count:
        failures.append("entry_args_ptr_sweep_check_row_count_too_small")
    expected_window_size = _int_metric(payload, "expected_window_size")
    if expected_window_size is not None and row_count <= expected_window_size:
        failures.append("entry_args_ptr_sweep_check_row_count_not_above_window")
    if sweep_row_count is not None and row_count != sweep_row_count:
        failures.append("entry_args_ptr_sweep_check_row_count_mismatch")
    return row_count


def _check_entry_args_ptr_required_evidence(
    preflight: dict[str, Any],
    failures: list[str],
    *,
    min_row_count: int,
) -> dict[str, Any]:
    rows = _required_evidence_rows(preflight)
    sweep_row = _find_evidence_row(rows, ENTRY_ARGS_PTR_SWEEP_LABEL)
    check_row = _find_evidence_row(rows, ENTRY_ARGS_PTR_SWEEP_CHECK_LABEL)
    sweep_path = _check_evidence_row(
        sweep_row,
        failures,
        label=ENTRY_ARGS_PTR_SWEEP_LABEL,
        expected_suffix=ENTRY_ARGS_PTR_SWEEP_SUFFIX,
    )
    check_path = _check_evidence_row(
        check_row,
        failures,
        label=ENTRY_ARGS_PTR_SWEEP_CHECK_LABEL,
        expected_suffix=ENTRY_ARGS_PTR_SWEEP_CHECK_SUFFIX,
    )
    sweep_payload: dict[str, Any] | None = None
    check_payload: dict[str, Any] | None = None
    sweep_actual_sha: str | None = None
    check_actual_sha: str | None = None
    if sweep_path is not None:
        if not sweep_path.exists():
            failures.append("entry_args_ptr_sweep_artifact_not_found")
        else:
            sweep_actual_sha = _check_artifact_sha(
                sweep_path,
                sweep_row,
                failures,
                label=ENTRY_ARGS_PTR_SWEEP_LABEL,
            )
            try:
                sweep_payload = _load_json(sweep_path)
            except (OSError, json.JSONDecodeError, ValueError):
                failures.append("entry_args_ptr_sweep_artifact_invalid_json")
    if check_path is not None:
        if not check_path.exists():
            failures.append("entry_args_ptr_sweep_check_artifact_not_found")
        else:
            check_actual_sha = _check_artifact_sha(
                check_path,
                check_row,
                failures,
                label=ENTRY_ARGS_PTR_SWEEP_CHECK_LABEL,
            )
            try:
                check_payload = _load_json(check_path)
            except (OSError, json.JSONDecodeError, ValueError):
                failures.append("entry_args_ptr_sweep_check_artifact_invalid_json")
    sweep_row_count = (
        _check_entry_args_ptr_sweep_payload(
            sweep_payload,
            failures,
            min_row_count=min_row_count,
        )
        if sweep_payload is not None
        else None
    )
    check_row_count = (
        _check_entry_args_ptr_sweep_check_payload(
            check_payload,
            failures,
            sweep_path=sweep_path,
            sweep_row_count=sweep_row_count,
            min_row_count=min_row_count,
        )
        if check_payload is not None
        else None
    )
    return {
        "entry_args_ptr_required": True,
        "entry_args_ptr_sweep_json": str(sweep_path) if sweep_path is not None else None,
        "entry_args_ptr_sweep_sha256": sweep_row.get("sha256")
        if isinstance(sweep_row, dict)
        else None,
        "entry_args_ptr_sweep_actual_sha256": sweep_actual_sha,
        "entry_args_ptr_sweep_check_json": str(check_path)
        if check_path is not None
        else None,
        "entry_args_ptr_sweep_check_sha256": check_row.get("sha256")
        if isinstance(check_row, dict)
        else None,
        "entry_args_ptr_sweep_check_actual_sha256": check_actual_sha,
        "entry_args_ptr_sweep_row_count": sweep_row_count,
        "entry_args_ptr_sweep_check_row_count": check_row_count,
        "entry_args_ptr_sweep_device": sweep_payload.get("device")
        if isinstance(sweep_payload, dict)
        else None,
        "entry_args_ptr_sweep_window_size": sweep_payload.get("window_size")
        if isinstance(sweep_payload, dict)
        else None,
        "entry_args_ptr_sweep_mirror_fields": sweep_payload.get("mirror_fields")
        if isinstance(sweep_payload, dict)
        else None,
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": (
            sweep_payload.get("require_kernel_arg_packet_abi")
            if isinstance(sweep_payload, dict)
            else None
        ),
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": (
            sweep_payload.get("require_kernel_entry_args_abi")
            if isinstance(sweep_payload, dict)
            else None
        ),
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": (
            sweep_payload.get("require_kernel_entry_args_ptr_abi")
            if isinstance(sweep_payload, dict)
            else None
        ),
    }


def _summary_payload(preflight: dict[str, Any]) -> dict[str, Any]:
    nested = preflight.get("lab_gate_status_summary")
    if isinstance(nested, dict):
        merged = dict(nested)
        conflicts: list[str] = []
        for key, value in preflight.items():
            if key == "lab_gate_status_summary":
                continue
            if key in merged and merged[key] != value:
                conflicts.append(key)
                continue
            merged[key] = value
        if conflicts:
            merged["__lab_gate_status_summary_conflicts__"] = conflicts
        return merged
    return preflight


def _require_equal(
    payload: dict[str, Any],
    failures: list[str],
    *,
    key: str,
    expected: Any,
    label: str,
) -> None:
    if payload.get(key) != expected:
        failures.append(f"{label}_{key}_mismatch:{payload.get(key)!r}!={expected!r}")


def _require_runner_equal(
    runner: dict[str, Any],
    failures: list[str],
    *,
    key: str,
    expected: Any,
) -> None:
    value = _runner_value(runner, key)
    if value != expected:
        failures.append(f"runner_{key}_mismatch:{value!r}!={expected!r}")


def _check_preflight(
    preflight: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    summary = _summary_payload(preflight)
    conflicts = summary.get("__lab_gate_status_summary_conflicts__")
    if isinstance(conflicts, list) and conflicts:
        failures.append(
            "preflight_summary_top_level_conflict:" + ",".join(map(str, conflicts))
        )
    for key, expected in EXPECTED_PREFLIGHT_FLAGS.items():
        _require_equal(summary, failures, key=key, expected=expected, label="preflight")
    for key, expected in EXPECTED_PREFLIGHT_FOURTH_FIELD_FLAGS.items():
        _require_equal(summary, failures, key=key, expected=expected, label="preflight")
    for key, expected in EXPECTED_PREFLIGHT_ALL_FOUR_FLAGS.items():
        _require_equal(summary, failures, key=key, expected=expected, label="preflight")
    source_count = _int_metric(summary, f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_source_count")
    previous_source_count = _int_metric(
        summary,
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_previous_source_count",
    )
    if source_count is None or source_count < min_source_count:
        failures.append("preflight_fourth_field_handoff_source_count_invalid")
    if previous_source_count is None or previous_source_count < min_source_count:
        failures.append("preflight_fourth_field_handoff_previous_source_count_invalid")
    fourth_row_count = _int_metric(summary, f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_row_count")
    fourth_row_ok_count = _int_metric(
        summary,
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_row_ok_count",
    )
    if fourth_row_count is None or fourth_row_count < min_row_count:
        failures.append("preflight_fourth_field_handoff_row_count_invalid")
    elif fourth_row_ok_count != fourth_row_count:
        failures.append("preflight_fourth_field_handoff_row_ok_count_mismatch")
    for suffix in (
        "field_read_row_ok_count",
        "runner_row_count",
        "runner_row_ok_count",
    ):
        if (
            fourth_row_count is not None
            and _int_metric(summary, f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_{suffix}")
            != fourth_row_count
        ):
            failures.append(f"preflight_fourth_field_handoff_{suffix}_mismatch")
    for suffix in (
        "field_read_hash",
        "runner_hash",
        "third_field_read_hash",
        "third_field_native_hash",
    ):
        if not _is_hex_u64(summary.get(f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_{suffix}")):
            failures.append(f"preflight_fourth_field_handoff_{suffix}_invalid")
    for key, expected in EXPECTED_PREFLIGHT_EXECUTION_FLAGS.items():
        _require_equal(summary, failures, key=key, expected=expected, label="preflight")
    for key, expected in EXPECTED_PREFLIGHT_KERNEL_SIDE_TYPED_PATH_FLAGS.items():
        _require_equal(summary, failures, key=key, expected=expected, label="preflight")
    row_count = _int_metric(summary, f"{PREFLIGHT_EXECUTION_PREFIX}_row_count")
    row_ok_count = _int_metric(summary, f"{PREFLIGHT_EXECUTION_PREFIX}_row_ok_count")
    if row_count is None or row_count < min_row_count:
        failures.append("preflight_wna16_kernel_side_execution_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("preflight_wna16_kernel_side_execution_row_ok_count_mismatch")
    for field in HANDLE_FIELDS:
        key = f"{PREFLIGHT_EXECUTION_PREFIX}_{field}_read_row_ok_count"
        if row_count is not None and _int_metric(summary, key) != row_count:
            failures.append(f"preflight_{field}_read_row_ok_count_mismatch")
    for key in (
        f"{PREFLIGHT_EXECUTION_PREFIX}_hash_accumulator",
        f"{PREFLIGHT_EXECUTION_PREFIX}_handle_projection_hash_accumulator",
        f"{PREFLIGHT_EXECUTION_PREFIX}_descriptor_ptr_read_hash_accumulator",
        f"{PREFLIGHT_EXECUTION_PREFIX}_packed_weight_descriptor_read_hash_accumulator",
        f"{PREFLIGHT_EXECUTION_PREFIX}_scale_metadata_handle_read_hash_accumulator",
        f"{PREFLIGHT_EXECUTION_PREFIX}_aux_metadata_handle_read_hash_accumulator",
    ):
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"preflight_{key}_invalid")
    descriptor_hash = summary.get(
        f"{PREFLIGHT_EXECUTION_PREFIX}_descriptor_ptr_read_hash_accumulator"
    )
    packed_hash = summary.get(
        f"{PREFLIGHT_EXECUTION_PREFIX}_packed_weight_descriptor_read_hash_accumulator"
    )
    fourth_descriptor_hash = summary.get(
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_field_read_hash"
    )
    fourth_packed_hash = summary.get(
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_third_field_read_hash"
    )
    if (
        fourth_row_count is not None
        and row_count is not None
        and fourth_row_count != row_count
    ):
        failures.append("preflight_fourth_field_handoff_wna16_row_count_mismatch")
    all_four_source_count = _int_metric(
        summary,
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_source_count",
    )
    all_four_selected_input_count = _int_metric(
        summary,
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_selected_input_count",
    )
    all_four_row_count = _int_metric(
        summary,
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_row_count",
    )
    all_four_row_ok_count = _int_metric(
        summary,
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_row_ok_count",
    )
    if all_four_source_count is None or all_four_source_count < min_source_count:
        failures.append("preflight_all_four_source_count_invalid")
    if (
        all_four_source_count is not None
        and all_four_selected_input_count != all_four_source_count
    ):
        failures.append("preflight_all_four_selected_input_count_mismatch")
    if (
        source_count is not None
        and all_four_source_count is not None
        and all_four_source_count != source_count
    ):
        failures.append("preflight_all_four_fourth_source_count_mismatch")
    if all_four_row_count is None or all_four_row_count < min_row_count:
        failures.append("preflight_all_four_row_count_invalid")
    elif all_four_row_ok_count != all_four_row_count:
        failures.append("preflight_all_four_row_ok_count_mismatch")
    if (
        fourth_row_count is not None
        and all_four_row_count is not None
        and all_four_row_count != fourth_row_count
    ):
        failures.append("preflight_all_four_fourth_row_count_mismatch")
    if (
        row_count is not None
        and all_four_row_count is not None
        and all_four_row_count != row_count
    ):
        failures.append("preflight_all_four_wna16_row_count_mismatch")
    selected_manifest = summary.get(
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_selected_input_manifest_sha256"
    )
    post_manifest = summary.get(
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_post_native_input_manifest_sha256"
    )
    if not _is_sha256_hex(selected_manifest):
        failures.append("preflight_all_four_selected_input_manifest_invalid")
    if not _is_sha256_hex(post_manifest):
        failures.append("preflight_all_four_post_native_input_manifest_invalid")
    elif post_manifest != selected_manifest:
        failures.append("preflight_all_four_post_native_input_manifest_mismatch")
    all_four_fourth_sha = summary.get(
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_fourth_field_sha256"
    )
    fourth_evidence_sha = summary.get(f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_evidence_sha256")
    if not _is_sha256_hex(all_four_fourth_sha):
        failures.append("preflight_all_four_fourth_sha_invalid")
    if not _is_sha256_hex(fourth_evidence_sha):
        failures.append("preflight_fourth_field_evidence_sha_invalid")
    if all_four_fourth_sha != fourth_evidence_sha:
        failures.append("preflight_all_four_fourth_sha_mismatch")
    all_four_fourth_path = summary.get(
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_fourth_field_path_label"
    )
    fourth_evidence_path = summary.get(f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_evidence_path")
    if not isinstance(all_four_fourth_path, str) or not all_four_fourth_path:
        failures.append("preflight_all_four_fourth_path_missing")
    if not isinstance(fourth_evidence_path, str) or not fourth_evidence_path:
        failures.append("preflight_fourth_field_evidence_path_missing")
    if all_four_fourth_path != fourth_evidence_path:
        failures.append("preflight_all_four_fourth_path_mismatch")
    if fourth_descriptor_hash != descriptor_hash:
        failures.append("preflight_fourth_field_handoff_descriptor_hash_mismatch")
    if fourth_packed_hash != packed_hash:
        failures.append("preflight_fourth_field_handoff_packed_weight_hash_mismatch")
    kernel_side_evidence_path = summary.get(
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_path"
    )
    kernel_side_evidence_sha = summary.get(
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_sha256"
    )
    if not isinstance(kernel_side_evidence_path, str) or not kernel_side_evidence_path:
        failures.append("preflight_kernel_side_typed_path_evidence_path_missing")
    if not _is_sha256_hex(kernel_side_evidence_sha):
        failures.append("preflight_kernel_side_typed_path_evidence_sha256_invalid")
    kernel_side_path_source_count = _int_metric(
        summary,
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_source_count",
    )
    kernel_side_path_input_count = _int_metric(
        summary,
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_input_json_count",
    )
    kernel_side_path_row_count = _int_metric(
        summary,
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_row_count",
    )
    kernel_side_path_row_ok_count = _int_metric(
        summary,
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_row_ok_count",
    )
    if kernel_side_path_source_count is None or kernel_side_path_source_count < min_source_count:
        failures.append("preflight_kernel_side_typed_path_source_count_invalid")
    if (
        kernel_side_path_source_count is not None
        and kernel_side_path_input_count != kernel_side_path_source_count
    ):
        failures.append("preflight_kernel_side_typed_path_input_json_count_mismatch")
    if kernel_side_path_row_count is None or kernel_side_path_row_count < min_row_count:
        failures.append("preflight_kernel_side_typed_path_row_count_invalid")
    elif kernel_side_path_row_ok_count != kernel_side_path_row_count:
        failures.append("preflight_kernel_side_typed_path_row_ok_count_mismatch")
    if (
        all_four_source_count is not None
        and kernel_side_path_source_count is not None
        and kernel_side_path_source_count != all_four_source_count
    ):
        failures.append("preflight_kernel_side_typed_path_all_four_source_count_mismatch")
    if (
        all_four_row_count is not None
        and kernel_side_path_row_count is not None
        and kernel_side_path_row_count != all_four_row_count
    ):
        failures.append("preflight_kernel_side_typed_path_all_four_row_count_mismatch")
    kernel_side_all_four_path = summary.get(
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_path_label"
    )
    kernel_side_all_four_sha = summary.get(
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_sha256"
    )
    all_four_evidence_path = summary.get(
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_evidence_path"
    )
    all_four_evidence_sha = summary.get(
        f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_evidence_sha256"
    )
    if kernel_side_all_four_path != all_four_evidence_path:
        failures.append("preflight_kernel_side_typed_path_all_four_path_mismatch")
    if kernel_side_all_four_sha != all_four_evidence_sha:
        failures.append("preflight_kernel_side_typed_path_all_four_sha_mismatch")
    kernel_side_manifest = summary.get(
        f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_selected_input_manifest_sha256"
    )
    if not _is_sha256_hex(kernel_side_manifest):
        failures.append("preflight_kernel_side_typed_path_selected_manifest_invalid")
    elif selected_manifest != kernel_side_manifest:
        failures.append("preflight_kernel_side_typed_path_selected_manifest_mismatch")
    return summary, failures


def _check_runner_duplicate_consistency(
    runner: dict[str, Any],
    failures: list[str],
    *,
    key: str,
) -> None:
    values = _runner_key_values(runner, key)
    if len(values) < 2:
        return
    first_location, first_value = values[0]
    for location, value in values[1:]:
        if value != first_value:
            failures.append(
                f"runner_{key}_duplicate_mismatch:"
                f"{first_location}={first_value!r}!={location}={value!r}"
            )


def _check_runner_cross_hashes(
    runner: dict[str, Any],
    preflight_summary: dict[str, Any],
    failures: list[str],
) -> None:
    suffixes = (
        "hash_accumulator",
        "handle_projection_hash_accumulator",
        "descriptor_ptr_read_hash_accumulator",
        "packed_weight_descriptor_read_hash_accumulator",
        "scale_metadata_handle_read_hash_accumulator",
        "aux_metadata_handle_read_hash_accumulator",
    )
    for suffix in suffixes:
        preflight_key = f"{PREFLIGHT_EXECUTION_PREFIX}_{suffix}"
        runner_key = f"{WNA16_EXECUTION_PREFIX}_{suffix}"
        preflight_value = preflight_summary.get(preflight_key)
        runner_value = _runner_value(runner, runner_key)
        if preflight_value != runner_value:
            failures.append(
                f"runner_preflight_{suffix}_mismatch:"
                f"{runner_value!r}!={preflight_value!r}"
            )


def _check_preflight_check(
    payload: dict[str, Any],
    failures: list[str],
    *,
    preflight_path: Path,
    preflight_sha256: str,
) -> None:
    if payload.get("passed") is not True:
        failures.append("preflight_check_not_passed")
    result = payload.get("result")
    if isinstance(result, dict) and result.get("passed") is not True:
        failures.append("preflight_check_result_not_passed")
    checked_json = payload.get("checked_preflight_json") or payload.get(
        "preflight_json"
    )
    if checked_json is None:
        failures.append("preflight_check_json_target_missing")
    else:
        try:
            checked_path = _resolve(str(checked_json)).resolve()
        except OSError:
            failures.append("preflight_check_json_target_unresolvable")
        else:
            if checked_path != preflight_path.resolve():
                failures.append("preflight_check_json_target_mismatch")
    checked_sha = payload.get("checked_preflight_sha256") or payload.get(
        "preflight_sha256"
    )
    if checked_sha is None:
        failures.append("preflight_check_sha256_missing")
    elif checked_sha != preflight_sha256:
        failures.append("preflight_check_sha256_mismatch")


def _check_runner(
    runner: dict[str, Any],
    *,
    preflight_summary: dict[str, Any],
    preflight_row_count: int | None,
    min_source_count: int,
    min_row_count: int,
) -> tuple[int | None, list[str]]:
    failures: list[str] = []
    if runner.get("passed") is not True:
        failures.append("runner_not_passed")
    source_count = _int_metric(runner, "selected_source_count")
    if source_count is None or source_count < min_source_count:
        failures.append("runner_selected_source_count_invalid")
    preflight_source_count = _int_metric(
        preflight_summary,
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_source_count",
    )
    if (
        source_count is not None
        and preflight_source_count is not None
        and source_count != preflight_source_count
    ):
        failures.append("runner_fourth_field_handoff_source_count_mismatch")
    row_count = _int_metric(runner, "merged_row_count")
    if row_count is None or row_count < min_row_count:
        failures.append("runner_merged_row_count_invalid")
    if (
        preflight_row_count is not None
        and row_count is not None
        and row_count != preflight_row_count
    ):
        failures.append("runner_preflight_row_count_mismatch")
    fourth_row_count = _int_metric(
        preflight_summary,
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_row_count",
    )
    if (
        fourth_row_count is not None
        and row_count is not None
        and row_count != fourth_row_count
    ):
        failures.append("runner_fourth_field_handoff_row_count_mismatch")
    execution_row_count = _runner_int_metric(
        runner,
        f"{WNA16_EXECUTION_PREFIX}_row_count",
    )
    execution_row_ok_count = _runner_int_metric(
        runner,
        f"{WNA16_EXECUTION_PREFIX}_row_ok_count",
    )
    if row_count is not None and execution_row_count != row_count:
        failures.append("runner_execution_row_count_mismatch")
    if row_count is not None and execution_row_ok_count != row_count:
        failures.append("runner_execution_row_ok_count_mismatch")
    duplicate_keys = [
        f"{WNA16_EXECUTION_PREFIX}_row_count",
        f"{WNA16_EXECUTION_PREFIX}_row_ok_count",
        *EXPECTED_RUNNER_FLAGS,
        *(
            f"{WNA16_EXECUTION_PREFIX}_{field}_read_row_ok_count"
            for field in HANDLE_FIELDS
        ),
        *HASH_KEYS,
    ]
    for key in duplicate_keys:
        _check_runner_duplicate_consistency(runner, failures, key=key)
    for key, expected in EXPECTED_RUNNER_FLAGS.items():
        _require_runner_equal(runner, failures, key=key, expected=expected)
    for field in HANDLE_FIELDS:
        key = f"{WNA16_EXECUTION_PREFIX}_{field}_read_row_ok_count"
        if row_count is not None and _runner_int_metric(runner, key) != row_count:
            failures.append(f"runner_{field}_read_row_ok_count_mismatch")
    for key in HASH_KEYS:
        if not _is_hex_u64(_runner_value(runner, key)):
            failures.append(f"runner_{key}_invalid")
    _check_runner_cross_hashes(runner, preflight_summary, failures)
    fourth_descriptor_hash = preflight_summary.get(
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_field_read_hash"
    )
    fourth_packed_hash = preflight_summary.get(
        f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_third_field_read_hash"
    )
    runner_descriptor_hash = _runner_value(
        runner,
        f"{WNA16_EXECUTION_PREFIX}_descriptor_ptr_read_hash_accumulator",
    )
    runner_packed_hash = _runner_value(
        runner,
        f"{WNA16_EXECUTION_PREFIX}_packed_weight_descriptor_read_hash_accumulator",
    )
    if fourth_descriptor_hash != runner_descriptor_hash:
        failures.append("runner_fourth_field_handoff_descriptor_hash_mismatch")
    if fourth_packed_hash != runner_packed_hash:
        failures.append("runner_fourth_field_handoff_packed_weight_hash_mismatch")
    return row_count, failures


def run_harness(args: argparse.Namespace) -> dict[str, Any]:
    preflight_path = _resolve(args.preflight_json)
    preflight_check_path = _resolve(args.preflight_check_json)
    runner_path = _resolve(args.runner_json)
    output_path = _resolve(args.output_json)

    preflight = _load_json(preflight_path)
    runner = _load_json(runner_path)
    preflight_sha256 = _sha256(preflight_path)
    failures: list[str] = []
    preflight_summary, preflight_failures = _check_preflight(
        preflight,
        min_source_count=args.min_source_count,
        min_row_count=args.min_row_count,
    )
    failures.extend(preflight_failures)
    preflight_row_count = _int_metric(
        preflight_summary,
        f"{PREFLIGHT_EXECUTION_PREFIX}_row_count",
    )
    if args.require_preflight_check:
        if not preflight_check_path.exists():
            failures.append("preflight_check_json_missing")
        else:
            _check_preflight_check(
                _load_json(preflight_check_path),
                failures,
                preflight_path=preflight_path,
                preflight_sha256=preflight_sha256,
            )
    entry_args_ptr_status = _check_entry_args_ptr_required_evidence(
        preflight,
        failures,
        min_row_count=args.min_row_count,
    )
    row_count, runner_failures = _check_runner(
        runner,
        preflight_summary=preflight_summary,
        preflight_row_count=preflight_row_count,
        min_source_count=args.min_source_count,
        min_row_count=args.min_row_count,
    )
    failures.extend(runner_failures)

    field_read_hashes = {
        field: _runner_value(
            runner,
            f"{WNA16_EXECUTION_PREFIX}_{field}_read_hash_accumulator",
        )
        for field in HANDLE_FIELDS
    }
    field_read_row_ok_counts = {
        field: _runner_value(
            runner,
            f"{WNA16_EXECUTION_PREFIX}_{field}_read_row_ok_count",
        )
        for field in HANDLE_FIELDS
    }
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "wna16_typed_slot_benchmark_harness",
        "harness_name": HARNESS_NAME,
        "harness_mode": HARNESS_MODE,
        "passed": passed,
        "failures": failures,
        "preflight_json": str(preflight_path),
        "preflight_sha256": preflight_sha256,
        "preflight_check_json": str(preflight_check_path),
        "preflight_check_required": bool(args.require_preflight_check),
        "preflight_check_sha256": (
            _sha256(preflight_check_path) if preflight_check_path.exists() else None
        ),
        "runner_json": str(runner_path),
        "runner_sha256": _sha256(runner_path),
        "min_source_count": int(args.min_source_count),
        "min_row_count": int(args.min_row_count),
        "source_count": runner.get("selected_source_count"),
        "row_count": row_count,
        "row_ok_count": _runner_value(
            runner,
            f"{WNA16_EXECUTION_PREFIX}_row_ok_count",
        ),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": field_read_row_ok_counts,
        "field_read_hashes": field_read_hashes,
        "fourth_field_handoff_ready": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_ready"
        ),
        "fourth_field_handoff_evidence_path": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_evidence_path"
        ),
        "fourth_field_handoff_evidence_sha256": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_evidence_sha256"
        ),
        "fourth_field_handoff_source_count": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_source_count"
        ),
        "fourth_field_handoff_row_count": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_row_count"
        ),
        "fourth_field_handoff_row_ok_count": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_row_ok_count"
        ),
        "fourth_field_handoff_field_read_hash": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_field_read_hash"
        ),
        "fourth_field_handoff_runner_hash": preflight_summary.get(
            f"{PREFLIGHT_FOURTH_FIELD_PREFIX}_runner_hash"
        ),
        "all_four_field_consumer_ready": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_READY_PREFIX}_ready"
        ),
        "all_four_field_consumer_fields_read": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_READY_PREFIX}_fields_read"
        ),
        "all_four_field_consumer_hashes_valid": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_READY_PREFIX}_hashes_valid"
        ),
        "all_four_field_consumer_source_count": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_source_count"
        ),
        "all_four_field_consumer_row_count": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_row_count"
        ),
        "all_four_field_consumer_row_ok_count": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_row_ok_count"
        ),
        "all_four_field_consumer_fourth_field_sha256": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_fourth_field_sha256"
        ),
        "all_four_field_consumer_fourth_field_path_label": preflight_summary.get(
            f"{PREFLIGHT_ALL_FOUR_CONSUMER_PREFIX}_fourth_field_path_label"
        ),
        "future_wna16_kernel_side_typed_consumer_path_ready": preflight_summary.get(
            PREFLIGHT_KERNEL_SIDE_TYPED_PATH_READY_KEY
        ),
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": preflight_summary.get(
            PREFLIGHT_KERNEL_SIDE_TYPED_PATH_HASHES_READY_KEY
        ),
        "future_wna16_kernel_side_typed_consumer_path_evidence_path": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_path"
        ),
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_sha256"
        ),
        "future_wna16_kernel_side_typed_consumer_path_source_count": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_source_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_input_json_count": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_input_json_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_row_count": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_row_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_row_ok_count": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_row_ok_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_sha256"
        ),
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": preflight_summary.get(
            f"{PREFLIGHT_KERNEL_SIDE_TYPED_PATH_PREFIX}_selected_input_manifest_sha256"
        ),
        **entry_args_ptr_status,
        "row_hash_accumulator": _runner_value(
            runner,
            f"{WNA16_EXECUTION_PREFIX}_hash_accumulator"
        ),
        "handle_projection_hash_accumulator": _runner_value(
            runner,
            f"{WNA16_EXECUTION_PREFIX}_handle_projection_hash_accumulator"
        ),
        "benchmark_harness_ready": passed,
        "benchmark_harness_kind": "future_typed_slot_consumer_harness",
        "measures_latency": False,
        "wna16_kernel_side_execution_ready": (
            preflight_summary.get(
                "default_kernel_consumer_wna16_kernel_side_execution_ready"
            )
            is True
        ),
        "wna16_benchmark_ready": False,
        "current_wna16_arg_pass": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "explicit_typed_abi_slot": True,
        "reuses_current_wna16_arg_slot": False,
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
            "WNA16 typed-slot benchmark harness preflight failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate strict preflight evidence before starting the future WNA16 "
            "typed-slot benchmark harness."
        )
    )
    parser.add_argument("--preflight-json", default=str(DEFAULT_PREFLIGHT_JSON))
    parser.add_argument(
        "--preflight-check-json",
        default=str(DEFAULT_PREFLIGHT_CHECK_JSON),
    )
    parser.add_argument("--runner-json", default=str(DEFAULT_RUNNER_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument(
        "--min-row-count",
        type=int,
        default=DEFAULT_MIN_ENTRY_ARGS_PTR_ROW_COUNT,
    )
    parser.add_argument("--require-preflight-check", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_harness(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
