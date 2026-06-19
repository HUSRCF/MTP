#!/usr/bin/env python3
"""Validate a compact premap lab preflight summary artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_ROW_FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]
REQUIRED_ROW_METADATA = [
    "layer_id",
    "expert_id",
    "address_key_hash",
    "row_order_hash",
    "ordered_row_hash",
]
REQUIRED_SHA_FIELDS = [
    "default_readonly_gate_sha256",
    "canary_gate_sha256",
    "default_kernel_consumer_schema_artifact_sha256",
    "default_kernel_consumer_dispatch_runner_evidence_sha256",
    "default_kernel_consumer_dispatch_runner_artifact_evidence_sha256",
    "default_kernel_consumer_online_merged_multiprogram_evidence_sha256",
    "default_kernel_consumer_dispatch_ptr_standalone_evidence_sha256",
    "default_kernel_consumer_arg_slot_standalone_evidence_sha256",
    "default_kernel_consumer_wna16_side_variant_evidence_sha256",
]
REQUIRED_LAYOUT_CHECKS = {
    "default_kernel_consumer_kernel_arg_packet_layout_reported": True,
    "default_kernel_consumer_kernel_entry_summary_layout_reported": True,
    "default_kernel_consumer_kernel_entry_args_layout_reported": True,
    "default_kernel_consumer_kernel_arg_packet_struct_size": 32,
    "default_kernel_consumer_kernel_arg_packet_offset_program_view_ptr": 0,
    "default_kernel_consumer_kernel_entry_summary_struct_size": 104,
    "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator": 80,
    "default_kernel_consumer_kernel_entry_args_struct_size": 40,
    "default_kernel_consumer_kernel_entry_args_offset_summary": 8,
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"summary JSON must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 <= parsed <= 0xFFFFFFFFFFFFFFFF


def _int_metric(summary: dict[str, Any], key: str) -> int | None:
    value = summary.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _float_metric(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _payloadless_execution_ready(summary: dict[str, Any], failures: list[str]) -> bool:
    prefix = "default_kernel_consumer_future_wna16_payloadless_execution"
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_ready": True,
        f"{prefix}_gate_ready": True,
        f"{prefix}_lab_preflight_ready": True,
        f"{prefix}_native_ready": True,
        f"{prefix}_native_requested": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_all_four_ready": True,
        f"{prefix}_all_four_fields_read": True,
        f"{prefix}_kernel_side_ready": True,
        f"{prefix}_kernel_side_hashes_valid": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    benchmark_repeat_count = _int_metric(summary, f"{prefix}_benchmark_repeat_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    if benchmark_repeat_count != 3:
        failures.append(f"{prefix}_benchmark_repeat_count_mismatch")
        ready = False
    return ready


def _future_kernel_side_typed_path_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    all_four_failures: list[str] = []
    all_four_ready = _future_wna16_all_four_consumer_ready(
        summary,
        all_four_failures,
    )
    prefix = "default_kernel_consumer_future_wna16_kernel_side_typed_path"
    expected_values = {
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready": True,
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        f"{prefix}_evidence_passed": True,
        f"{prefix}_artifact_kind": "future_wna16_kernel_side_typed_consumer_path",
        f"{prefix}_name": "premap_future_wna16_kernel_side_typed_consumer_path_v1",
        f"{prefix}_mode": "independent_future_wna16_kernel_side_typed_consumer_path",
        f"{prefix}_source": "premap_future_wna16_typed_slot_all_four_field_consumer_v1",
        f"{prefix}_stage_type": "lab_gate",
        f"{prefix}_bench_semantics": False,
        f"{prefix}_all_four_gate_ready": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_independent_path": True,
        f"{prefix}_explicit_typed_abi_slot": True,
        f"{prefix}_future_kernel_side_checked": True,
        f"{prefix}_future_kernel_side_all_fields_read": True,
        f"{prefix}_wna16_side_checked": True,
        f"{prefix}_wna16_side_all_fields_read": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    if not all_four_ready:
        failures.append("future_wna16_all_four_consumer_not_ready")
        failures.extend(all_four_failures)
        ready = False
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    input_count = _int_metric(summary, f"{prefix}_input_json_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if input_count != source_count:
        failures.append(f"{prefix}_input_json_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_all_four_sha256",
        f"{prefix}_selected_input_manifest_sha256",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    all_four_path = summary.get(
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_path"
    )
    if not isinstance(all_four_path, str) or not all_four_path:
        failures.append(f"{prefix}_all_four_consumer_evidence_path_missing")
        ready = False
    elif summary.get(f"{prefix}_all_four_path_label") != all_four_path:
        failures.append(f"{prefix}_all_four_path_label_mismatch")
        ready = False
    all_four_sha = summary.get(
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_sha256"
    )
    if not _is_hex64(all_four_sha):
        failures.append(f"{prefix}_all_four_consumer_evidence_sha256_invalid")
        ready = False
    elif summary.get(f"{prefix}_all_four_sha256") != all_four_sha:
        failures.append(f"{prefix}_all_four_sha256_mismatch")
        ready = False
    all_four_source_count = _int_metric(
        summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_source_count",
    )
    all_four_row_count = _int_metric(
        summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_row_count",
    )
    if source_count is not None and all_four_source_count != source_count:
        failures.append(f"{prefix}_all_four_source_count_mismatch")
        ready = False
    if row_count is not None and all_four_row_count != row_count:
        failures.append(f"{prefix}_all_four_row_count_mismatch")
        ready = False
    path_value = summary.get(f"{prefix}_evidence_path")
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{prefix}_evidence_path_missing")
        ready = False
    return ready


def _future_wna16_fourth_field_handoff_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    prefix = "default_kernel_consumer_future_wna16_fourth_field_handoff"
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_previous_gate_ready": True,
        f"{prefix}_ready": True,
        f"{prefix}_fourth_field": "descriptor_ptr",
        f"{prefix}_native_requested": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_expected_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_passes_current_wna16_args": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    previous_source_count = _int_metric(summary, f"{prefix}_previous_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if previous_source_count is None or previous_source_count < 128:
        failures.append(f"{prefix}_previous_source_count_invalid")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    else:
        for suffix in (
            "row_ok_count",
            "field_read_row_ok_count",
            "runner_row_count",
            "runner_row_ok_count",
        ):
            if _int_metric(summary, f"{prefix}_{suffix}") != row_count:
                failures.append(f"{prefix}_{suffix}_mismatch")
                ready = False
    for suffix in (
        "field_read_hash",
        "runner_hash",
        "third_field_read_hash",
        "third_field_native_hash",
    ):
        if not _is_hex_u64(summary.get(f"{prefix}_{suffix}")):
            failures.append(f"{prefix}_{suffix}_invalid")
            ready = False
    if not _is_hex64(summary.get(f"{prefix}_evidence_sha256")):
        failures.append(f"{prefix}_evidence_sha256_invalid")
        ready = False
    path_value = summary.get(f"{prefix}_evidence_path")
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{prefix}_evidence_path_missing")
        ready = False
    return ready


def _future_wna16_all_four_consumer_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    fourth_handoff_failures: list[str] = []
    fourth_handoff_ready = _future_wna16_fourth_field_handoff_ready(
        summary,
        fourth_handoff_failures,
    )
    prefix = "default_kernel_consumer_future_wna16_all_four_consumer"
    expected_values = {
        "default_kernel_consumer_future_wna16_all_four_field_consumer_ready": True,
        "default_kernel_consumer_future_wna16_all_four_field_consumer_fields_read": True,
        "default_kernel_consumer_future_wna16_all_four_field_consumer_hashes_valid": True,
        f"{prefix}_evidence_passed": True,
        f"{prefix}_artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_all_four_field_consumer"
        ),
        f"{prefix}_stage_type": "lab_gate",
        f"{prefix}_bench_semantics": False,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_future_kernel_side_all_fields_read": True,
        f"{prefix}_wna16_side_all_fields_read": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    if not fourth_handoff_ready:
        failures.append("future_wna16_fourth_field_handoff_not_ready")
        failures.extend(fourth_handoff_failures)
        ready = False
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    selected_count = _int_metric(summary, f"{prefix}_selected_input_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if selected_count != source_count:
        failures.append(f"{prefix}_selected_input_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_fourth_field_sha256",
        f"{prefix}_selected_input_manifest_sha256",
        f"{prefix}_post_native_input_manifest_sha256",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    for key in (f"{prefix}_evidence_path", f"{prefix}_fourth_field_path_label"):
        value = summary.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
            ready = False
    fourth_handoff_prefix = (
        "default_kernel_consumer_future_wna16_fourth_field_handoff"
    )
    fourth_handoff_path = summary.get(f"{fourth_handoff_prefix}_evidence_path")
    fourth_handoff_sha = summary.get(f"{fourth_handoff_prefix}_evidence_sha256")
    fourth_handoff_source_count = _int_metric(
        summary, f"{fourth_handoff_prefix}_source_count"
    )
    fourth_handoff_row_count = _int_metric(
        summary, f"{fourth_handoff_prefix}_row_count"
    )
    fourth_handoff_row_ok_count = _int_metric(
        summary, f"{fourth_handoff_prefix}_row_ok_count"
    )
    if not isinstance(fourth_handoff_path, str) or not fourth_handoff_path:
        failures.append(f"{fourth_handoff_prefix}_evidence_path_missing")
        ready = False
    elif summary.get(f"{prefix}_fourth_field_path_label") != fourth_handoff_path:
        failures.append(f"{prefix}_fourth_field_path_label_mismatch")
        ready = False
    if not _is_hex64(fourth_handoff_sha):
        failures.append(f"{fourth_handoff_prefix}_evidence_sha256_invalid")
        ready = False
    elif summary.get(f"{prefix}_fourth_field_sha256") != fourth_handoff_sha:
        failures.append(f"{prefix}_fourth_field_sha256_mismatch")
        ready = False
    if fourth_handoff_source_count != source_count:
        failures.append(f"{prefix}_fourth_field_source_count_mismatch")
        ready = False
    if fourth_handoff_row_count != row_count:
        failures.append(f"{prefix}_fourth_field_row_count_mismatch")
        ready = False
    if fourth_handoff_row_ok_count != row_count:
        failures.append(f"{prefix}_fourth_field_row_ok_count_mismatch")
        ready = False
    if (
        _is_hex64(summary.get(f"{prefix}_selected_input_manifest_sha256"))
        and summary.get(f"{prefix}_post_native_input_manifest_sha256")
        != summary.get(f"{prefix}_selected_input_manifest_sha256")
    ):
        failures.append(f"{prefix}_post_native_input_manifest_sha256_mismatch")
        ready = False
    return ready


def _check_kernel_consumer_handle_summary(
    summary: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
    label: str,
    expected_field_read_path: str,
    expected_packet_chain_depth: int,
) -> None:
    if summary.get(f"{prefix}_checked") is not True:
        failures.append(f"{label}_checked_mismatch")
    if summary.get(f"{prefix}_field_read_path") != expected_field_read_path:
        failures.append(f"{label}_field_read_path_mismatch")
    if summary.get(f"{prefix}_packet_chain_depth") != int(expected_packet_chain_depth):
        failures.append(f"{label}_packet_chain_depth_mismatch")
    row_count = _int_metric(summary, f"{prefix}_summary_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_summary_row_ok_count")
    if row_count is None or row_count <= 0:
        failures.append(f"{label}_summary_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append(f"{label}_summary_row_ok_count_mismatch")
    for field in REQUIRED_ROW_FIELDS:
        key = f"{prefix}_summary_{field}_read_row_ok_count"
        if row_count is not None and _int_metric(summary, key) != row_count:
            failures.append(f"{label}_{field}_read_row_ok_count_mismatch")
    if (
        row_count is not None
        and _int_metric(summary, f"{prefix}_summary_row_metadata_read_row_ok_count")
        != row_count
    ):
        failures.append(f"{label}_row_metadata_read_row_ok_count_mismatch")
    if _int_metric(summary, f"{prefix}_summary_error_count") != 0:
        failures.append(f"{label}_summary_error_count_mismatch")
    if _int_metric(summary, f"{prefix}_summary_field_mask") != 15:
        failures.append(f"{label}_summary_field_mask_mismatch")
    for suffix in (
        "summary_row_hash_accumulator",
        "summary_field_read_hash_accumulator",
        "summary_row_metadata_hash_accumulator",
    ):
        key = f"{prefix}_{suffix}"
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")
    if summary.get(f"{prefix}_all_handle_fields_read") is not True:
        failures.append(f"{label}_all_handle_fields_read_mismatch")
    if _int_metric(summary, f"{prefix}_payload_bytes") != 0:
        failures.append(f"{label}_payload_bytes_mismatch")
    if summary.get(f"{prefix}_passed_to_kernel") is not False:
        failures.append(f"{label}_passed_to_kernel_mismatch")
    if summary.get(f"{prefix}_kernel_arg_pass_allowed") is not False:
        failures.append(f"{label}_kernel_arg_pass_allowed_mismatch")
    if summary.get(f"{prefix}_changes_kernel_launch_args") is not False:
        failures.append(f"{label}_changes_kernel_launch_args_mismatch")
    if summary.get(f"{prefix}_current_wna16_arg_compatible") is not False:
        failures.append(f"{label}_current_wna16_arg_compatible_mismatch")
    if summary.get(f"{prefix}_requires_wna16_arg_reinterpretation") is not False:
        failures.append(f"{label}_requires_wna16_arg_reinterpretation_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_checked") is not True:
        failures.append(f"{label}_single_field_handoff_checked_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_field_name") != "scale_metadata_handle":
        failures.append(f"{label}_single_field_handoff_field_name_mismatch")
    if (
        summary.get(f"{prefix}_single_field_handoff_source")
        != "native_request_summary_field_read_counts"
    ):
        failures.append(f"{label}_single_field_handoff_source_mismatch")
    if row_count is not None:
        if _int_metric(summary, f"{prefix}_single_field_handoff_row_count") != row_count:
            failures.append(f"{label}_single_field_handoff_row_count_mismatch")
        if (
            _int_metric(summary, f"{prefix}_single_field_handoff_row_ok_count")
            != row_count
        ):
            failures.append(f"{label}_single_field_handoff_row_ok_count_mismatch")
    if _int_metric(summary, f"{prefix}_single_field_handoff_error_count") != 0:
        failures.append(f"{label}_single_field_handoff_error_count_mismatch")
    if not _is_hex_u64(summary.get(f"{prefix}_single_field_handoff_hash_accumulator")):
        failures.append(f"{prefix}_single_field_handoff_hash_accumulator_invalid")
    if _int_metric(summary, f"{prefix}_single_field_handoff_payload_bytes") != 0:
        failures.append(f"{label}_single_field_handoff_payload_bytes_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_passed_to_kernel") is not False:
        failures.append(f"{label}_single_field_handoff_passed_to_kernel_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_changes_kernel_launch_args") is not False:
        failures.append(
            f"{label}_single_field_handoff_changes_kernel_launch_args_mismatch"
        )
    if (
        summary.get(f"{prefix}_single_field_handoff_current_wna16_arg_compatible")
        is not False
    ):
        failures.append(
            f"{label}_single_field_handoff_current_wna16_arg_compatible_mismatch"
        )
    if (
        summary.get(
            f"{prefix}_single_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is not False
    ):
        failures.append(
            f"{label}_single_field_handoff_requires_wna16_arg_reinterpretation_mismatch"
        )
    expected_handoff_fields = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    if summary.get(f"{prefix}_all_field_handoff_checked") is not True:
        failures.append(f"{label}_all_field_handoff_checked_mismatch")
    if summary.get(f"{prefix}_all_field_handoff_field_names") != expected_handoff_fields:
        failures.append(f"{label}_all_field_handoff_field_names_mismatch")
    if (
        summary.get(f"{prefix}_all_field_handoff_source")
        != "native_request_summary_field_read_counts"
    ):
        failures.append(f"{label}_all_field_handoff_source_mismatch")
    if row_count is not None:
        if _int_metric(summary, f"{prefix}_all_field_handoff_row_count") != row_count:
            failures.append(f"{label}_all_field_handoff_row_count_mismatch")
        if _int_metric(summary, f"{prefix}_all_field_handoff_row_ok_count") != row_count:
            failures.append(f"{label}_all_field_handoff_row_ok_count_mismatch")
        for field_name in expected_handoff_fields:
            if (
                _int_metric(
                    summary,
                    f"{prefix}_all_field_handoff_{field_name}_row_ok_count",
                )
                != row_count
            ):
                failures.append(
                    f"{label}_all_field_handoff_{field_name}_row_ok_count_mismatch"
                )
    if _int_metric(summary, f"{prefix}_all_field_handoff_error_count") != 0:
        failures.append(f"{label}_all_field_handoff_error_count_mismatch")
    if not _is_hex_u64(summary.get(f"{prefix}_all_field_handoff_hash_accumulator")):
        failures.append(f"{label}_all_field_handoff_hash_accumulator_invalid")
    if _int_metric(summary, f"{prefix}_all_field_handoff_payload_bytes") != 0:
        failures.append(f"{label}_all_field_handoff_payload_bytes_mismatch")
    if summary.get(f"{prefix}_all_field_handoff_passed_to_kernel") is not False:
        failures.append(f"{label}_all_field_handoff_passed_to_kernel_mismatch")
    if summary.get(f"{prefix}_all_field_handoff_changes_kernel_launch_args") is not False:
        failures.append(
            f"{label}_all_field_handoff_changes_kernel_launch_args_mismatch"
        )
    if (
        summary.get(f"{prefix}_all_field_handoff_current_wna16_arg_compatible")
        is not False
    ):
        failures.append(
            f"{label}_all_field_handoff_current_wna16_arg_compatible_mismatch"
        )
    if (
        summary.get(
            f"{prefix}_all_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is not False
    ):
        failures.append(
            f"{label}_all_field_handoff_requires_wna16_arg_reinterpretation_mismatch"
        )


def _check_request_launch_geometry(
    summary: dict[str, Any],
    failures: list[str],
) -> None:
    row_count = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_summary_row_count",
    )
    grid_x = _int_metric(summary, "default_kernel_consumer_request_launch_grid_x")
    block_x = _int_metric(summary, "default_kernel_consumer_request_launch_block_x")
    row_offset = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_row_offset",
    )
    row_limit = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_row_limit",
    )
    rows_per_program = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_rows_per_program",
    )
    if row_count is None or row_count <= 0:
        failures.append("request_launch_geometry_row_count_invalid")
        return
    if grid_x is None or grid_x <= 0:
        failures.append("request_launch_geometry_grid_x_invalid")
        return
    if block_x is None or block_x <= 0:
        failures.append("request_launch_geometry_block_x_invalid")
        return
    if row_offset != 0:
        failures.append("request_launch_geometry_row_offset_mismatch")
    if row_limit != row_count:
        failures.append("request_launch_geometry_row_limit_mismatch")
    if rows_per_program != block_x:
        failures.append("request_launch_geometry_rows_per_program_mismatch")
    launched_lanes = grid_x * block_x
    previous_grid_lanes = (grid_x - 1) * block_x
    if launched_lanes < row_count:
        failures.append("request_launch_geometry_under_covers_rows")
    if previous_grid_lanes >= row_count:
        failures.append("request_launch_geometry_overprovisioned_grid")


def check_premap_lab_preflight_summary(
    summary: dict[str, Any],
    *,
    min_source_count: int = 32,
    expected_online_merged_device: int = 1,
) -> dict[str, Any]:
    failures: list[str] = []

    for key, expected in {
        "passed": True,
        "default_contract_passed": True,
        "prefetch_lab_default_gate_passed": True,
        "prefetch_lab_default_gate_decision_status": "passed",
        "prefetch_lab_default_full_fetch_decision": (
            "blocked_by_ready_time_measured_copy"
        ),
        "prefetch_lab_default_full_fetch_passed": True,
        "prefetch_lab_default_ready_time_report_passed": True,
        "prefetch_lab_default_ready_time_allow_full_fetch": False,
        "prefetch_lab_default_ready_time_decision_reason": (
            "full_fetch_threshold_not_met"
        ),
        "prefetch_lab_default_ready_time_threshold_failures": [
            "used_per_issued_fetch_below_threshold"
        ],
        "prefetch_lab_default_metadata_decision": "shadow_only",
        "prefetch_lab_default_metadata_passed": True,
        "prefetch_lab_default_premap_decision": (
            "lab_enabled_descriptor_prep_only"
        ),
        "prefetch_lab_default_premap_passed": True,
        "default_required_evidence_passed": True,
        "default_optional_evidence_passed": True,
        "default_kernel_consumer_schema_passed": True,
        "default_kernel_consumer_online_merged_multiprogram_evidence_passed": True,
        "default_kernel_consumer_online_merged_multiprogram_hashchain_equal": True,
        "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked": True,
        "default_kernel_consumer_online_merged_multiprogram_no_payload": True,
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel": False,
        "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args": False,
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table": True,
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible": False,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_entry_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_ptr_abi": True,
        "default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_arg_slot_all_handle_fields_read": True,
        "default_kernel_consumer_consumer_view_all_handle_fields_read": True,
        "default_kernel_consumer_consumer_view_payload_bytes": 0,
        "default_kernel_consumer_consumer_view_passed_to_kernel": False,
        "default_kernel_consumer_consumer_view_changes_kernel_launch_args": False,
        "default_kernel_consumer_consumer_view_current_wna16_arg_compatible": False,
        "default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_entry_args_checked": True,
        "default_kernel_consumer_kernel_entry_args_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_entry_args_payload_bytes": 0,
        "default_kernel_consumer_kernel_entry_args_passed_to_kernel": False,
        "default_kernel_consumer_kernel_entry_args_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_entry_args_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_invocation_checked": True,
        "default_kernel_consumer_kernel_invocation_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_invocation_payload_bytes": 0,
        "default_kernel_consumer_kernel_invocation_passed_to_kernel": False,
        "default_kernel_consumer_kernel_invocation_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_invocation_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_invocation_entry_checked": True,
        "default_kernel_consumer_kernel_invocation_entry_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_invocation_entry_payload_bytes": 0,
        "default_kernel_consumer_kernel_invocation_entry_passed_to_kernel": False,
        "default_kernel_consumer_kernel_invocation_entry_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_invocation_entry_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_checked": True,
        "default_kernel_consumer_kernel_endpoint_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_endpoint_payload_bytes": 0,
        "default_kernel_consumer_kernel_endpoint_passed_to_kernel": False,
        "default_kernel_consumer_kernel_endpoint_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_endpoint_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_endpoint_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_endpoint_ptr_checked": True,
        "default_kernel_consumer_kernel_endpoint_ptr_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_endpoint_ptr_payload_bytes": 0,
        "default_kernel_consumer_kernel_endpoint_ptr_passed_to_kernel": False,
        "default_kernel_consumer_kernel_endpoint_ptr_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_endpoint_ptr_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_wna16_side_variant_evidence_label": (
            "wna16_side_consumer_variant_execution_128strict_runner_json"
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_passed": True,
        "default_kernel_consumer_wna16_side_variant_required": True,
        "default_kernel_consumer_wna16_side_variant_checked": True,
        "default_kernel_consumer_wna16_side_variant_name": (
            "premap_wna16_side_consumer_variant_execution_v1"
        ),
        "default_kernel_consumer_wna16_side_variant_mode": (
            "readonly_wna16_side_consumer_variant_execution"
        ),
        "default_kernel_consumer_wna16_side_variant_source": (
            "premap_future_wna16_typed_slot_kernel_variant_v1"
        ),
        "default_kernel_consumer_wna16_side_variant_all_handle_fields_read": True,
        "default_kernel_consumer_wna16_side_variant_error_count": 0,
        "default_kernel_consumer_wna16_side_variant_packet_chain_depth": 16,
        "default_kernel_consumer_wna16_side_variant_payload_bytes": 0,
        "default_kernel_consumer_wna16_side_variant_passed_to_kernel": False,
        "default_kernel_consumer_wna16_side_variant_changes_kernel_launch_args": False,
        "default_kernel_consumer_wna16_side_variant_current_wna16_arg_compatible": False,
        "default_kernel_consumer_wna16_side_variant_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_wna16_side_variant_explicit_typed_abi_slot": True,
        "default_kernel_consumer_wna16_side_variant_reuses_current_wna16_arg_slot": False,
        "default_kernel_consumer_typed_noop_ready": True,
        "default_kernel_consumer_wna16_side_variant_base_ready": True,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")

    for key in (
        "prefetch_lab_default_gate_failures",
        "prefetch_lab_default_full_fetch_failures",
        "prefetch_lab_default_metadata_failures",
        "prefetch_lab_default_premap_failures",
    ):
        if summary.get(key) != []:
            failures.append(f"{key}_not_empty")
    premap_positive = _int_metric(
        summary,
        "prefetch_lab_default_premap_positive_count",
    )
    recommended_capacity = _int_metric(
        summary,
        "prefetch_lab_default_premap_recommended_capacity_entries",
    )
    no_eviction_capacity = _int_metric(
        summary,
        "prefetch_lab_default_premap_no_eviction_capacity_entries",
    )
    if premap_positive is None or premap_positive < 4:
        failures.append("prefetch_lab_default_premap_positive_count_below_min")
    if recommended_capacity is None or recommended_capacity < 12288:
        failures.append(
            "prefetch_lab_default_premap_recommended_capacity_entries_below_min"
        )
    if no_eviction_capacity is None or no_eviction_capacity < 12288:
        failures.append(
            "prefetch_lab_default_premap_no_eviction_capacity_entries_below_min"
        )
    if (
        recommended_capacity is not None
        and no_eviction_capacity is not None
        and no_eviction_capacity > recommended_capacity
    ):
        failures.append(
            "prefetch_lab_default_premap_no_eviction_capacity_above_recommended"
        )
    ready_time_issued = _int_metric(
        summary,
        "prefetch_lab_default_ready_time_issued_fetch_count",
    )
    ready_time_used = _int_metric(
        summary,
        "prefetch_lab_default_ready_time_used_fetch_count",
    )
    ready_time_used_per_issued = _float_metric(
        summary,
        "prefetch_lab_default_ready_time_used_per_issued_fetch",
    )
    ready_time_demand_hit = _float_metric(
        summary,
        "prefetch_lab_default_ready_time_demand_hit_rate",
    )
    ready_time_late_miss = _float_metric(
        summary,
        "prefetch_lab_default_ready_time_ready_late_miss_rate",
    )
    if ready_time_issued is None or ready_time_issued <= 0:
        failures.append("prefetch_lab_default_ready_time_issued_fetch_count_invalid")
    if ready_time_used != 0:
        failures.append("prefetch_lab_default_ready_time_used_fetch_count_mismatch")
    if ready_time_used_per_issued != 0.0:
        failures.append(
            "prefetch_lab_default_ready_time_used_per_issued_fetch_mismatch"
        )
    if ready_time_demand_hit is None or not (0.0 <= ready_time_demand_hit <= 1.0):
        failures.append("prefetch_lab_default_ready_time_demand_hit_rate_invalid")
    if ready_time_late_miss is None or not (0.0 <= ready_time_late_miss <= 1.0):
        failures.append(
            "prefetch_lab_default_ready_time_ready_late_miss_rate_invalid"
        )

    for key in (
        "runtime_gate_evidence_deferred_count",
        "strict_default_gate_evidence_deferred_count",
        "default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count",
        "default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count",
    ):
        value = _int_metric(summary, key)
        if value != 0:
            failures.append(f"{key}_not_zero")

    source_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_source_count",
    )
    row_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_row_count",
    )
    dispatch_offset = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset",
    )
    dispatch_limit = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit",
    )
    active_rows = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows",
    )
    if source_count is None or source_count < min_source_count:
        failures.append("online_merged_source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("online_merged_row_count_invalid")
    if dispatch_offset != 0:
        failures.append("online_merged_dispatch_offset_not_zero")
    if row_count is not None and dispatch_limit != row_count:
        failures.append("online_merged_dispatch_limit_not_full_table")
    if row_count is not None and active_rows != row_count:
        failures.append("online_merged_dispatch_active_rows_mismatch")
    device = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_device",
    )
    hip_visible_devices = summary.get(
        "default_kernel_consumer_online_merged_multiprogram_hip_visible_devices"
    )
    logical_gpu1 = (
        int(expected_online_merged_device) == 1
        and device == 0
        and str(hip_visible_devices) == "1"
    )
    if device != int(expected_online_merged_device) and not logical_gpu1:
        if int(expected_online_merged_device) == 1:
            failures.append("online_merged_device_not_gpu1")
        else:
            failures.append("online_merged_device_mismatch")
    if (
        summary.get("default_kernel_consumer_online_merged_multiprogram_mirror_field")
        != "scale_metadata_handle"
    ):
        failures.append("online_merged_mirror_field_mismatch")
    wna16_side_evidence_path = summary.get(
        "default_kernel_consumer_wna16_side_variant_evidence_path"
    )
    if not isinstance(wna16_side_evidence_path, str) or not wna16_side_evidence_path:
        failures.append("wna16_side_variant_evidence_path_missing")
    wna16_side_source_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_source_count",
    )
    online_source_context_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_source_context_count",
    )
    online_source_identity_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_source_identity_count",
    )
    online_source_context_matches_source_count = summary.get(
        "default_kernel_consumer_online_merged_multiprogram_source_context_matches_source_count"
    )
    online_source_identity_coverage = summary.get(
        "default_kernel_consumer_online_merged_multiprogram_source_identity_coverage"
    )
    wna16_side_source_context_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_source_context_count",
    )
    wna16_side_source_identity_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_source_identity_count",
    )
    wna16_side_source_context_matches_source_count = summary.get(
        "default_kernel_consumer_wna16_side_variant_source_context_matches_source_count"
    )
    wna16_side_source_identity_coverage = summary.get(
        "default_kernel_consumer_wna16_side_variant_source_identity_coverage"
    )
    wna16_side_missing_source_identity_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count",
    )
    wna16_side_source_identity_subset = summary.get(
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    )
    wna16_side_row_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_row_count",
    )
    wna16_side_row_ok_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_row_ok_count",
    )
    wna16_kernel_side_execution_ready = summary.get(
        "default_kernel_consumer_wna16_kernel_side_execution_ready"
    )
    wna16_kernel_side_execution_row_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_kernel_side_execution_row_count",
    )
    wna16_kernel_side_execution_row_ok_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_kernel_side_execution_row_ok_count",
    )
    if wna16_side_source_count is None or wna16_side_source_count < 128:
        failures.append("wna16_side_variant_source_count_invalid")
    if online_source_context_count is None or online_source_context_count <= 0:
        failures.append("online_merged_source_context_count_invalid")
    if online_source_identity_count is None or online_source_identity_count <= 0:
        failures.append("online_merged_source_identity_count_invalid")
    if (
        source_count is not None
        and online_source_context_count is not None
        and online_source_context_count != source_count
    ):
        failures.append("online_merged_source_context_count_mismatch")
    if online_source_context_matches_source_count is not True:
        failures.append("online_merged_source_context_matches_source_count_mismatch")
    if (
        online_source_context_count is not None
        and online_source_identity_count is not None
        and online_source_identity_count != online_source_context_count
    ):
        failures.append("online_merged_source_identity_count_mismatch")
    if online_source_identity_coverage is not True:
        failures.append("online_merged_source_identity_coverage_mismatch")
    if wna16_side_source_context_count is None or wna16_side_source_context_count <= 0:
        failures.append("wna16_side_variant_source_context_count_invalid")
    if (
        wna16_side_source_count is not None
        and wna16_side_source_context_count is not None
        and wna16_side_source_context_count != wna16_side_source_count
    ):
        failures.append("wna16_side_variant_source_context_count_mismatch")
    if wna16_side_source_context_matches_source_count is not True:
        failures.append("wna16_side_variant_source_context_matches_source_count_mismatch")
    if (
        wna16_side_source_identity_count is None
        or wna16_side_source_identity_count <= 0
    ):
        failures.append("wna16_side_variant_source_identity_count_invalid")
    if (
        wna16_side_source_context_count is not None
        and wna16_side_source_identity_count is not None
        and wna16_side_source_identity_count != wna16_side_source_context_count
    ):
        failures.append("wna16_side_variant_source_identity_count_mismatch")
    if wna16_side_source_identity_coverage is not True:
        failures.append("wna16_side_variant_source_identity_coverage_mismatch")
    if summary.get(
        "default_kernel_consumer_wna16_benchmark_prerequisites_ready"
    ) is True:
        failures.append("wna16_benchmark_prerequisites_ready_not_allowed")
    for key in (
        "default_kernel_consumer_online_merged_multiprogram_source_identity_digest",
        "default_kernel_consumer_wna16_side_variant_source_identity_digest",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
    if wna16_side_source_identity_subset is True:
        if wna16_side_missing_source_identity_count != 0:
            failures.append("wna16_side_variant_source_identity_missing_count_mismatch")
        if summary.get("default_kernel_consumer_wna16_side_variant_ready") is not True:
            failures.append("wna16_side_variant_ready_mismatch")
        if wna16_kernel_side_execution_ready is True:
            if (
                wna16_kernel_side_execution_row_count is None
                or wna16_kernel_side_execution_row_count <= 0
            ):
                failures.append("wna16_kernel_side_execution_row_count_invalid")
            if (
                wna16_kernel_side_execution_row_count is not None
                and wna16_kernel_side_execution_row_ok_count
                != wna16_kernel_side_execution_row_count
            ):
                failures.append("wna16_kernel_side_execution_row_ok_count_mismatch")
            if (
                row_count is not None
                and wna16_kernel_side_execution_row_count is not None
                and wna16_kernel_side_execution_row_count < row_count
            ):
                failures.append("wna16_kernel_side_execution_row_count_below_online_merged")
            expected_kernel_side = {
                "default_kernel_consumer_wna16_kernel_side_execution_required": True,
                "default_kernel_consumer_wna16_kernel_side_execution_checked": True,
                "default_kernel_consumer_wna16_kernel_side_execution_name": (
                    "premap_future_wna16_kernel_side_consumer_execution_v1"
                ),
                "default_kernel_consumer_wna16_kernel_side_execution_mode": (
                    "readonly_future_wna16_kernel_side_consumer_execution"
                ),
                "default_kernel_consumer_wna16_kernel_side_execution_source": (
                    "premap_future_wna16_kernel_accept_typed_slot_v1"
                ),
                "default_kernel_consumer_wna16_kernel_side_execution_packet_chain_depth": 16,
                "default_kernel_consumer_wna16_kernel_side_execution_all_handle_fields_read": True,
                "default_kernel_consumer_wna16_kernel_side_execution_error_count": 0,
                "default_kernel_consumer_wna16_kernel_side_execution_payload_bytes": 0,
                "default_kernel_consumer_wna16_kernel_side_execution_payload_deref_allowed": False,
                "default_kernel_consumer_wna16_kernel_side_execution_kernel_arg_pass_allowed": False,
                "default_kernel_consumer_wna16_kernel_side_execution_passed_to_kernel": False,
                "default_kernel_consumer_wna16_kernel_side_execution_changes_kernel_launch_args": False,
                "default_kernel_consumer_wna16_kernel_side_execution_current_wna16_arg_compatible": False,
                "default_kernel_consumer_wna16_kernel_side_execution_requires_wna16_arg_reinterpretation": False,
                "default_kernel_consumer_wna16_kernel_side_execution_explicit_typed_abi_slot": True,
                "default_kernel_consumer_wna16_kernel_side_execution_reuses_current_wna16_arg_slot": False,
            }
            for key, expected_value in expected_kernel_side.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{key}_mismatch")
            for field in REQUIRED_ROW_FIELDS:
                key = (
                    "default_kernel_consumer_wna16_kernel_side_execution_"
                    f"{field}_read_row_ok_count"
                )
                if (
                    wna16_kernel_side_execution_row_count is not None
                    and _int_metric(summary, key)
                    != wna16_kernel_side_execution_row_count
                ):
                    failures.append(
                        f"wna16_kernel_side_execution_{field}_read_row_ok_count_mismatch"
                    )
            for key in (
                "default_kernel_consumer_wna16_kernel_side_execution_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_handle_projection_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_descriptor_ptr_read_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_packed_weight_descriptor_read_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_scale_metadata_handle_read_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_aux_metadata_handle_read_hash_accumulator",
            ):
                if not _is_hex_u64(summary.get(key)):
                    failures.append(f"{key}_invalid")
        elif wna16_kernel_side_execution_ready not in (False, None):
            failures.append("wna16_kernel_side_execution_ready_invalid")
        wna16_benchmark_ready = (
            summary.get("default_kernel_consumer_wna16_benchmark_ready") is True
        )
        if wna16_benchmark_ready:
            failures.append("wna16_benchmark_ready_not_allowed_in_no_mutation_gate")
        payloadless_ready_failures: list[str] = []
        payloadless_execution_ready = _payloadless_execution_ready(
            summary,
            payloadless_ready_failures,
        )
        typed_path_failures: list[str] = []
        future_kernel_side_typed_path_ready = _future_kernel_side_typed_path_ready(
            summary,
            typed_path_failures,
        )
        if (
            summary.get(
                "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
            )
            is True
            or summary.get(
                "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid"
            )
            is True
        ) and not future_kernel_side_typed_path_ready:
            failures.append("future_kernel_side_typed_path_reported_without_valid_evidence")
            failures.extend(typed_path_failures)
        chain_consistency_failures: list[str] = []
        typed_path_source_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_source_count",
        )
        typed_path_row_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_count",
        )
        payloadless_source_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_payloadless_execution_source_count",
        )
        payloadless_row_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_payloadless_execution_row_count",
        )
        if (
            typed_path_source_count is not None
            and payloadless_source_count is not None
            and typed_path_source_count != payloadless_source_count
        ):
            chain_consistency_failures.append(
                "payloadless_typed_path_source_count_mismatch"
            )
        if (
            typed_path_row_count is not None
            and payloadless_row_count is not None
            and typed_path_row_count != payloadless_row_count
        ):
            chain_consistency_failures.append(
                "payloadless_typed_path_row_count_mismatch"
            )
        chain_consistent = not chain_consistency_failures
        computed_payloadless_chain_ready = (
            summary.get("default_kernel_consumer_wna16_side_variant_ready") is True
            and future_kernel_side_typed_path_ready
            and payloadless_execution_ready
            and chain_consistent
        )
        reported_payloadless_chain_ready = summary.get(
            "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
        )
        if reported_payloadless_chain_ready is True and not computed_payloadless_chain_ready:
            failures.append("payloadless_chain_ready_reported_without_valid_evidence")
            failures.extend(typed_path_failures)
            failures.extend(payloadless_ready_failures)
            failures.extend(chain_consistency_failures)
        elif computed_payloadless_chain_ready and reported_payloadless_chain_ready is not True:
            failures.append("payloadless_chain_ready_not_reported")
        elif reported_payloadless_chain_ready not in (False, None, True):
            failures.append("payloadless_chain_ready_invalid")
        expected_stage = (
            "implement_future_wna16_typed_slot_kernel_variant_execution"
            if computed_payloadless_chain_ready
            else (
                "implement_wna16_typed_slot_benchmark_harness"
                if wna16_kernel_side_execution_ready is True
                else "implement_real_wna16_typed_slot_kernel_variant"
            )
        )
        if summary.get("default_kernel_consumer_next_runtime_stage") != expected_stage:
            failures.append("wna16_side_variant_next_stage_mismatch")
    elif wna16_side_source_identity_subset is False:
        if (
            wna16_side_missing_source_identity_count is None
            or wna16_side_missing_source_identity_count <= 0
        ):
            failures.append("wna16_side_variant_source_identity_missing_count_invalid")
        if summary.get("default_kernel_consumer_wna16_side_variant_ready") is not False:
            failures.append("wna16_side_variant_ready_mismatch")
        if summary.get("default_kernel_consumer_wna16_benchmark_ready") is not False:
            failures.append("wna16_side_variant_benchmark_ready_mismatch")
        if wna16_kernel_side_execution_ready is True:
            failures.append("wna16_kernel_side_execution_ready_without_source_subset")
        elif wna16_kernel_side_execution_ready not in (False, None):
            failures.append("wna16_kernel_side_execution_ready_invalid")
        if (
            summary.get("default_kernel_consumer_next_runtime_stage")
            != "refresh_wna16_side_variant_source_provenance"
        ):
            failures.append("wna16_side_variant_next_stage_mismatch")
    else:
        failures.append("wna16_side_variant_source_identity_subset_invalid")
    if wna16_side_row_count is None or wna16_side_row_count <= 0:
        failures.append("wna16_side_variant_row_count_invalid")
    if wna16_side_row_count is not None and wna16_side_row_ok_count != wna16_side_row_count:
        failures.append("wna16_side_variant_row_ok_count_mismatch")
    if (
        row_count is not None
        and wna16_side_row_count is not None
        and wna16_side_row_count < row_count
    ):
        failures.append("wna16_side_variant_row_count_below_online_merged")
    for field in REQUIRED_ROW_FIELDS:
        key = f"default_kernel_consumer_wna16_side_variant_{field}_read_row_ok_count"
        if (
            wna16_side_row_count is not None
            and _int_metric(summary, key) != wna16_side_row_count
        ):
            failures.append(f"wna16_side_variant_{field}_read_row_ok_count_mismatch")
    for key in (
        "default_kernel_consumer_wna16_side_variant_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_handle_projection_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_hash_accumulator",
    ):
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")

    if summary.get("default_kernel_consumer_arg_slot_field_read_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("arg_slot_field_read_field_names_mismatch")
    arg_slot_read_row_count = _int_metric(
        summary,
        "default_kernel_consumer_arg_slot_field_read_row_count",
    )
    row_ok_counts = summary.get(
        "default_kernel_consumer_arg_slot_field_read_row_ok_counts"
    )
    error_counts = summary.get(
        "default_kernel_consumer_arg_slot_field_read_error_counts"
    )
    read_hashes = summary.get("default_kernel_consumer_arg_slot_field_read_hashes")
    if not isinstance(row_ok_counts, dict):
        failures.append("arg_slot_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    if not isinstance(error_counts, dict):
        failures.append("arg_slot_field_read_error_counts_missing")
        error_counts = {}
    if not isinstance(read_hashes, dict):
        failures.append("arg_slot_field_read_hashes_missing")
        read_hashes = {}
    if arg_slot_read_row_count is not None:
        for field in REQUIRED_ROW_FIELDS:
            if row_ok_counts.get(field) != arg_slot_read_row_count:
                failures.append(f"arg_slot_{field}_read_row_ok_count_mismatch")
            if error_counts.get(field) != 0:
                failures.append(f"arg_slot_{field}_read_error_count_mismatch")
            if not isinstance(read_hashes.get(field), str) or not read_hashes.get(field):
                failures.append(f"arg_slot_{field}_read_hash_missing")

    if summary.get("default_kernel_consumer_consumer_view_field_read_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("consumer_view_field_read_field_names_mismatch")
    consumer_view_read_row_count = _int_metric(
        summary,
        "default_kernel_consumer_consumer_view_field_read_row_count",
    )
    view_row_ok_counts = summary.get(
        "default_kernel_consumer_consumer_view_field_read_row_ok_counts"
    )
    view_error_counts = summary.get(
        "default_kernel_consumer_consumer_view_field_read_error_counts"
    )
    view_read_hashes = summary.get(
        "default_kernel_consumer_consumer_view_field_read_hashes"
    )
    if not isinstance(view_row_ok_counts, dict):
        failures.append("consumer_view_field_read_row_ok_counts_missing")
        view_row_ok_counts = {}
    if not isinstance(view_error_counts, dict):
        failures.append("consumer_view_field_read_error_counts_missing")
        view_error_counts = {}
    if not isinstance(view_read_hashes, dict):
        failures.append("consumer_view_field_read_hashes_missing")
        view_read_hashes = {}
    if consumer_view_read_row_count is not None:
        for field in REQUIRED_ROW_FIELDS:
            if view_row_ok_counts.get(field) != consumer_view_read_row_count:
                failures.append(f"consumer_view_{field}_read_row_ok_count_mismatch")
            if view_error_counts.get(field) != 0:
                failures.append(f"consumer_view_{field}_read_error_count_mismatch")
            if not isinstance(view_read_hashes.get(field), str) or not view_read_hashes.get(field):
                failures.append(f"consumer_view_{field}_read_hash_missing")
    if summary.get("default_kernel_consumer_consumer_view_source_packet_chain_depth") != 3:
        failures.append("consumer_view_source_packet_chain_depth_mismatch")
    if (
        summary.get("default_kernel_consumer_kernel_entry_args_field_read_path")
        != "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    ):
        failures.append("kernel_entry_args_field_read_path_mismatch")
    if summary.get("default_kernel_consumer_kernel_entry_args_packet_chain_depth") != 5:
        failures.append("kernel_entry_args_packet_chain_depth_mismatch")
    entry_row_count = _int_metric(
        summary,
        "default_kernel_consumer_kernel_entry_args_summary_row_count",
    )
    entry_row_ok_count = _int_metric(
        summary,
        "default_kernel_consumer_kernel_entry_args_summary_row_ok_count",
    )
    if entry_row_count is None or entry_row_count <= 0:
        failures.append("kernel_entry_args_summary_row_count_invalid")
    if entry_row_count is not None and entry_row_ok_count != entry_row_count:
        failures.append("kernel_entry_args_summary_row_ok_count_mismatch")
    for field in REQUIRED_ROW_FIELDS:
        key = (
            "default_kernel_consumer_kernel_entry_args_summary_"
            f"{field}_read_row_ok_count"
        )
        if entry_row_count is not None and _int_metric(summary, key) != entry_row_count:
            failures.append(f"kernel_entry_args_{field}_read_row_ok_count_mismatch")
    if (
        entry_row_count is not None
        and _int_metric(
            summary,
            "default_kernel_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count",
        )
        != entry_row_count
    ):
        failures.append("kernel_entry_args_row_metadata_read_row_ok_count_mismatch")
    if (
        _int_metric(
            summary,
            "default_kernel_consumer_kernel_entry_args_summary_error_count",
        )
        != 0
    ):
        failures.append("kernel_entry_args_summary_error_count_mismatch")
    if (
        _int_metric(
            summary,
            "default_kernel_consumer_kernel_entry_args_summary_field_mask",
        )
        != 15
    ):
        failures.append("kernel_entry_args_summary_field_mask_mismatch")
    for key in (
        "default_kernel_consumer_kernel_entry_args_summary_row_hash_accumulator",
        "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator",
        "default_kernel_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator",
    ):
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")
    _check_kernel_consumer_handle_summary(
        summary,
        failures,
        prefix="default_kernel_consumer_request_ptr",
        label="request_ptr",
        expected_field_read_path=(
            "request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        expected_packet_chain_depth=4,
    )
    _check_kernel_consumer_handle_summary(
        summary,
        failures,
        prefix="default_kernel_consumer_request_launch",
        label="request_launch",
        expected_field_read_path=(
            "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        expected_packet_chain_depth=5,
    )
    _check_request_launch_geometry(summary, failures)
    _check_kernel_consumer_handle_summary(
        summary,
        failures,
        prefix="default_kernel_consumer_request_launch_ptr",
        label="request_launch_ptr",
        expected_field_read_path=(
            "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        expected_packet_chain_depth=6,
    )
    for prefix in (
        "default_kernel_consumer_kernel_invocation",
        "default_kernel_consumer_kernel_invocation_entry",
        "default_kernel_consumer_kernel_endpoint",
        "default_kernel_consumer_kernel_endpoint_ptr",
    ):
        if prefix.endswith("endpoint_ptr"):
            expected_depth = 13
        elif prefix.endswith("endpoint"):
            expected_depth = 12
        else:
            expected_depth = 11
        if summary.get(f"{prefix}_packet_chain_depth") != expected_depth:
            failures.append(f"{prefix}_packet_chain_depth_mismatch")
        for suffix in (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        ):
            key = f"{prefix}_{suffix}"
            if not _is_hex_u64(summary.get(key)):
                failures.append(f"{key}_invalid")

    if summary.get("default_kernel_consumer_schema_row_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("schema_row_field_names_mismatch")
    if summary.get("default_kernel_consumer_schema_row_metadata_names") != REQUIRED_ROW_METADATA:
        failures.append("schema_row_metadata_names_mismatch")

    for key, expected in REQUIRED_LAYOUT_CHECKS.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")

    for key in REQUIRED_SHA_FIELDS:
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")

    required = summary.get("required_evidence")
    if not isinstance(required, dict):
        failures.append("required_evidence_missing")
    else:
        required_count = _int_metric(required, "required_count")
        present_count = _int_metric(required, "present_count")
        passed_count = _int_metric(required, "passed_count")
        if required_count is None or required_count <= 0:
            failures.append("required_evidence_required_count_invalid")
        if required_count is not None and present_count != required_count:
            failures.append("required_evidence_present_count_mismatch")
        if required_count is not None and passed_count != required_count:
            failures.append("required_evidence_passed_count_mismatch")

    optional = summary.get("optional_evidence")
    if not isinstance(optional, dict):
        failures.append("optional_evidence_missing")
    else:
        required_count = _int_metric(optional, "required_count")
        present_count = _int_metric(optional, "present_count")
        passed_count = _int_metric(optional, "passed_count")
        if required_count is None or required_count <= 0:
            failures.append("optional_evidence_required_count_invalid")
        if required_count is not None and present_count != required_count:
            failures.append("optional_evidence_present_count_mismatch")
        if required_count is not None and passed_count != required_count:
            failures.append("optional_evidence_passed_count_mismatch")

    return {
        "passed": not failures,
        "failures": failures,
        "source": "premap_lab_preflight_summary_check",
        "min_source_count": int(min_source_count),
        "online_merged_source_count": source_count,
        "online_merged_row_count": row_count,
        "online_merged_dispatch_active_rows": active_rows,
        "online_merged_device": device,
        "online_merged_hip_visible_devices": hip_visible_devices,
        "expected_online_merged_device": int(expected_online_merged_device),
        "online_merged_mirror_field": summary.get(
            "default_kernel_consumer_online_merged_multiprogram_mirror_field"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--min-source-count", type=int, default=32)
    parser.add_argument("--expected-online-merged-device", type=int, default=1)
    parser.add_argument("--output-json", type=Path)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    checked_path = args.summary_json.resolve()
    result = check_premap_lab_preflight_summary(
        _load_json(args.summary_json),
        min_source_count=args.min_source_count,
        expected_online_merged_device=args.expected_online_merged_device,
    )
    result["checked_preflight_json"] = str(checked_path)
    result["checked_preflight_json_raw"] = str(args.summary_json)
    result["checked_preflight_sha256"] = _sha256(args.summary_json)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
