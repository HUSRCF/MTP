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


def _int_metric(summary: dict[str, Any], key: str) -> int | None:
    value = summary.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def check_premap_lab_preflight_summary(
    summary: dict[str, Any],
    *,
    min_source_count: int = 32,
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
    if device != 1:
        failures.append("online_merged_device_not_gpu1")
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

    if summary.get("default_kernel_consumer_schema_row_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("schema_row_field_names_mismatch")
    if summary.get("default_kernel_consumer_schema_row_metadata_names") != REQUIRED_ROW_METADATA:
        failures.append("schema_row_metadata_names_mismatch")

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
        "online_merged_mirror_field": summary.get(
            "default_kernel_consumer_online_merged_multiprogram_mirror_field"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--min-source-count", type=int, default=32)
    parser.add_argument("--output-json", type=Path)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = check_premap_lab_preflight_summary(
        _load_json(args.summary_json),
        min_source_count=args.min_source_count,
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
