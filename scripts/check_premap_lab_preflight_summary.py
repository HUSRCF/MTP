#!/usr/bin/env python3
"""Validate a compact premap lab preflight summary artifact."""

from __future__ import annotations

import argparse
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
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")

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
    ):
        expected_depth = (
            12 if prefix == "default_kernel_consumer_kernel_endpoint" else 11
        )
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
    result = check_premap_lab_preflight_summary(
        _load_json(args.summary_json),
        min_source_count=args.min_source_count,
        expected_online_merged_device=args.expected_online_merged_device,
    )
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
