#!/usr/bin/env python3
"""Check an online-merged future-native arg-slot row-window sweep artifact.

This is a static artifact checker.  It verifies that a previously generated
window sweep covers full/head/middle/tail row slices with the strict no-op
kernel boundary intact.  It does not refresh GPU/native canaries.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_premap_online_merged_native_arg_slot_window_sweep import (  # noqa: E402
    DEFAULT_OUTPUT_JSON,
    EXPECTED_KERNEL_ARG_PACKET_ABI_SOURCE,
    EXPECTED_PROGRAM_VIEW_PTR_ABI_SOURCE,
    _window_bounds,
)


REQUIRED_WINDOWS = ("full", "head", "middle", "tail")
SAFETY_FALSE_FIELDS = (
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
)
_FUTURE_KERNEL_REQUIRED_FIELD_MASK = 0x7
_FUTURE_KERNEL_ALL_FIELD_MASK = 0xF
_FUTURE_KERNEL_FIELD_MASK_PREFIXES = (
    "future_kernel_native_consumer",
    "future_kernel_native_launch_consumer",
    "future_kernel_native_dispatch_consumer",
    "future_kernel_native_dispatch_ptr_consumer",
    "future_kernel_native_arg_slot_consumer",
    "future_kernel_native_consumer_view",
    "future_kernel_native_consumer_program_view",
    "future_kernel_native_consumer_program_view_ptr",
)
_FUTURE_KERNEL_ARG_PACKET_FIELD_MASK_PREFIX = (
    "future_kernel_native_consumer_kernel_arg_packet"
)
HANDLE_FIELD_READ_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
_CONSUMER_VIEW_LAYOUT_INT_FIELDS = (
    "future_kernel_native_consumer_view_struct_size",
    "future_kernel_native_consumer_view_struct_align",
    "future_kernel_native_consumer_view_params_struct_size",
    "future_kernel_native_consumer_view_params_struct_align",
    "future_kernel_native_consumer_view_result_struct_size",
    "future_kernel_native_consumer_view_result_struct_align",
    "future_kernel_native_consumer_view_offset_params",
    "future_kernel_native_consumer_view_offset_abi_version",
    "future_kernel_native_consumer_view_offset_source_packet_chain_depth",
    "future_kernel_native_consumer_view_offset_row_offset",
    "future_kernel_native_consumer_view_offset_row_limit",
    "future_kernel_native_consumer_view_offset_rows_per_program",
    "future_kernel_native_consumer_view_offset_payload_bytes",
    "future_kernel_native_consumer_view_offset_flags",
)
_CONSUMER_VIEW_ROW_LAYOUT_INT_FIELDS = (
    "future_kernel_native_consumer_view_row_struct_size",
    "future_kernel_native_consumer_view_row_struct_align",
    "future_kernel_native_consumer_view_row_offset_descriptor_ptr",
    "future_kernel_native_consumer_view_row_offset_packed_weight_descriptor",
    "future_kernel_native_consumer_view_row_offset_scale_metadata_handle",
    "future_kernel_native_consumer_view_row_offset_aux_metadata_handle",
    "future_kernel_native_consumer_view_row_offset_expert_id",
    "future_kernel_native_consumer_view_row_offset_address_key_hash",
    "future_kernel_native_consumer_view_row_offset_row_index",
)
_KERNEL_ENTRY_ARGS_LAYOUT_EXPECTED = {
    "future_kernel_native_consumer_kernel_entry_args_struct_size": 40,
    "future_kernel_native_consumer_kernel_entry_args_struct_align": 8,
    "future_kernel_native_consumer_kernel_entry_args_kernel_arg_packet_struct_size": 32,
    "future_kernel_native_consumer_kernel_entry_args_summary_struct_size": 104,
    "future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet": 0,
    "future_kernel_native_consumer_kernel_entry_args_offset_summary": 8,
    "future_kernel_native_consumer_kernel_entry_args_offset_abi_version": 16,
    "future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet_struct_size": 20,
    "future_kernel_native_consumer_kernel_entry_args_offset_summary_struct_size": 24,
    "future_kernel_native_consumer_kernel_entry_args_offset_payload_bytes": 28,
    "future_kernel_native_consumer_kernel_entry_args_offset_flags": 32,
}
_KERNEL_ENTRY_SUMMARY_LAYOUT_EXPECTED = {
    "future_kernel_native_consumer_kernel_entry_summary_struct_size": 104,
    "future_kernel_native_consumer_kernel_entry_summary_struct_align": 8,
    "future_kernel_native_consumer_kernel_entry_summary_offset_abi_version": 0,
    "future_kernel_native_consumer_kernel_entry_summary_offset_packet_valid": 4,
    "future_kernel_native_consumer_kernel_entry_summary_offset_row_count": 8,
    "future_kernel_native_consumer_kernel_entry_summary_offset_row_ok_count": 12,
    "future_kernel_native_consumer_kernel_entry_summary_offset_descriptor_ptr_read_ok_count": 16,
    "future_kernel_native_consumer_kernel_entry_summary_offset_packed_weight_descriptor_read_ok_count": 20,
    "future_kernel_native_consumer_kernel_entry_summary_offset_scale_metadata_handle_read_ok_count": 24,
    "future_kernel_native_consumer_kernel_entry_summary_offset_aux_metadata_handle_read_ok_count": 28,
    "future_kernel_native_consumer_kernel_entry_summary_offset_expert_id_read_ok_count": 32,
    "future_kernel_native_consumer_kernel_entry_summary_offset_address_key_hash_read_ok_count": 36,
    "future_kernel_native_consumer_kernel_entry_summary_offset_row_metadata_read_ok_count": 40,
    "future_kernel_native_consumer_kernel_entry_summary_offset_error_count": 44,
    "future_kernel_native_consumer_kernel_entry_summary_offset_field_mask": 48,
    "future_kernel_native_consumer_kernel_entry_summary_offset_payload_bytes": 52,
    "future_kernel_native_consumer_kernel_entry_summary_offset_passed_to_kernel": 56,
    "future_kernel_native_consumer_kernel_entry_summary_offset_changes_kernel_launch_args": 60,
    "future_kernel_native_consumer_kernel_entry_summary_offset_current_wna16_arg_compatible": 64,
    "future_kernel_native_consumer_kernel_entry_summary_offset_requires_wna16_arg_reinterpretation": 68,
    "future_kernel_native_consumer_kernel_entry_summary_offset_reserved": 72,
    "future_kernel_native_consumer_kernel_entry_summary_offset_row_hash_accumulator": 80,
    "future_kernel_native_consumer_kernel_entry_summary_offset_field_read_hash_accumulator": 88,
    "future_kernel_native_consumer_kernel_entry_summary_offset_row_metadata_hash_accumulator": 96,
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON must contain an object")
    return payload


def _safe_load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _load_json(path), None
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return None, type(exc).__name__


def _resolve_child_path(value: object, *, parent: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return parent / path


def _check_future_field_masks(
    summary: dict[str, Any],
    *,
    label: str,
    require_child_kernel_arg_packet_abi: bool = False,
) -> list[str]:
    failures: list[str] = []
    prefixes = list(_FUTURE_KERNEL_FIELD_MASK_PREFIXES)
    if require_child_kernel_arg_packet_abi:
        prefixes.append(_FUTURE_KERNEL_ARG_PACKET_FIELD_MASK_PREFIX)
    for prefix in prefixes:
        field_key = f"{prefix}_field_mask"
        required_key = f"{prefix}_required_field_mask"
        field_mask = summary.get(field_key)
        required_mask = summary.get(required_key)
        if field_mask is None:
            failures.append(f"{label}_child_stub_{field_key}_missing")
            continue
        if required_mask is None:
            failures.append(f"{label}_child_stub_{required_key}_missing")
            continue
        if (
            not isinstance(field_mask, int)
            or isinstance(field_mask, bool)
            or not isinstance(required_mask, int)
            or isinstance(required_mask, bool)
        ):
            failures.append(f"{label}_child_stub_{prefix}_field_mask_type_mismatch")
            continue
        if required_mask != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
            failures.append(f"{label}_child_stub_{required_key}_mismatch")
        if field_mask != _FUTURE_KERNEL_ALL_FIELD_MASK:
            failures.append(f"{label}_child_stub_{field_key}_not_all_fields")
    return failures


def _check_field_reads(
    summary: dict[str, Any],
    *,
    label: str,
    prefix: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    for field in HANDLE_FIELD_READ_FIELDS:
        field_prefix = f"{prefix}_{field}_read"
        for suffix, expected in (
            ("row_count", expected_active),
            ("row_ok_count", expected_active),
            ("error_count", 0),
        ):
            key = f"{field_prefix}_{suffix}"
            if summary.get(key) != expected:
                failures.append(f"{label}_child_stub_{key}_mismatch")
        hash_key = f"{field_prefix}_hash_accumulator"
        hash_value = summary.get(hash_key)
        if not isinstance(hash_value, str) or not hash_value:
            failures.append(f"{label}_child_stub_{hash_key}_missing")
    return failures


def _check_consumer_view_handle_projection(
    summary: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    chain_keys = (
        "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator",
        "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator",
        "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    )
    values: list[str] = []
    for key in chain_keys:
        value = summary.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{label}_child_stub_{key}_missing")
            continue
        values.append(value)
    if failures:
        return failures
    if len(set(values)) != 1:
        failures.append(f"{label}_child_stub_consumer_view_handle_projection_mismatch")
    return failures


def _check_program_view_ptr_abi(
    summary: dict[str, Any],
    *,
    label: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    if "future_kernel_native_consumer_program_view_ptr_checked" not in summary:
        return [
            f"{label}_program_view_ptr_evidence_missing_or_dry_run_unsupported"
        ]
    for key, expected in {
        "future_kernel_native_consumer_program_view_ptr_checked": True,
        "future_kernel_native_consumer_program_view_ptr_source": (
            EXPECTED_PROGRAM_VIEW_PTR_ABI_SOURCE
        ),
        "future_kernel_native_consumer_program_view_ptr_row_count": (
            expected_active
        ),
        "future_kernel_native_consumer_program_view_ptr_row_ok_count": (
            expected_active
        ),
        "future_kernel_native_consumer_program_view_ptr_error_count": 0,
        "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
        "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
        "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": (
            False
        ),
        "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": (
            False
        ),
        "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": (
            False
        ),
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    field_mask = summary.get("future_kernel_native_consumer_program_view_ptr_field_mask")
    required_field_mask = summary.get(
        "future_kernel_native_consumer_program_view_ptr_required_field_mask"
    )
    if (
        not isinstance(field_mask, int)
        or isinstance(field_mask, bool)
        or not isinstance(required_field_mask, int)
        or isinstance(required_field_mask, bool)
        or (field_mask & required_field_mask) != required_field_mask
    ):
        failures.append(f"{label}_program_view_ptr_field_mask_mismatch")
    return failures


def _check_kernel_arg_packet_abi(
    summary: dict[str, Any],
    *,
    label: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    if "future_kernel_native_consumer_kernel_arg_packet_checked" not in summary:
        return [
            f"{label}_kernel_arg_packet_evidence_missing_or_dry_run_unsupported"
        ]
    for key, expected in {
        "future_kernel_native_consumer_kernel_arg_packet_checked": True,
        "future_kernel_native_consumer_kernel_arg_packet_source": (
            EXPECTED_KERNEL_ARG_PACKET_ABI_SOURCE
        ),
        "future_kernel_native_consumer_kernel_arg_packet_row_count": (
            expected_active
        ),
        "future_kernel_native_consumer_kernel_arg_packet_row_ok_count": (
            expected_active
        ),
        "future_kernel_native_consumer_kernel_arg_packet_error_count": 0,
        "future_kernel_native_consumer_kernel_arg_packet_payload_bytes": 0,
        "future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel": False,
        "future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args": (
            False
        ),
        "future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible": (
            False
        ),
        "future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation": (
            False
        ),
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    field_mask = summary.get(
        "future_kernel_native_consumer_kernel_arg_packet_field_mask"
    )
    required_field_mask = summary.get(
        "future_kernel_native_consumer_kernel_arg_packet_required_field_mask"
    )
    if (
        not isinstance(field_mask, int)
        or isinstance(field_mask, bool)
        or not isinstance(required_field_mask, int)
        or isinstance(required_field_mask, bool)
        or (field_mask & required_field_mask) != required_field_mask
    ):
        failures.append(f"{label}_kernel_arg_packet_field_mask_mismatch")
    failures.extend(
        _check_field_reads(
            summary,
            label=label,
            prefix="future_kernel_native_consumer_kernel_arg_packet",
            expected_active=expected_active,
        )
    )
    failures.extend(
        _check_kernel_entry_summary(
            summary,
            label=label,
            expected_active=expected_active,
        )
    )
    failures.extend(
        _check_kernel_entry_args(
            summary,
            label=label,
            expected_active=expected_active,
        )
    )
    return failures


def _check_kernel_entry_summary(
    summary: dict[str, Any],
    *,
    label: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    prefix = "future_kernel_native_consumer_kernel_entry_summary"
    if f"{prefix}_checked" not in summary:
        return [f"{label}_kernel_entry_summary_missing_or_dry_run_unsupported"]
    for key, expected in {
        f"{prefix}_checked": True,
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_kernel_entry_summary_abi",
        f"{prefix}_source": "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1",
        f"{prefix}_field_read_path": "kernel_entry_summary_to_kernel_arg_packet_to_program_view_rows",
        f"{prefix}_packet_chain_depth": 4,
        f"{prefix}_packet_valid": 1,
        f"{prefix}_row_count": expected_active,
        f"{prefix}_row_ok_count": expected_active,
        f"{prefix}_descriptor_ptr_read_row_ok_count": expected_active,
        f"{prefix}_packed_weight_descriptor_read_row_ok_count": expected_active,
        f"{prefix}_scale_metadata_handle_read_row_ok_count": expected_active,
        f"{prefix}_aux_metadata_handle_read_row_ok_count": expected_active,
        f"{prefix}_expert_id_read_row_ok_count": expected_active,
        f"{prefix}_address_key_hash_read_row_ok_count": expected_active,
        f"{prefix}_row_metadata_read_row_ok_count": expected_active,
        f"{prefix}_error_count": 0,
        f"{prefix}_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    for hash_key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
    ):
        value = summary.get(hash_key)
        if not isinstance(value, str) or not value:
            failures.append(f"{label}_{hash_key}_missing")
    for key, expected in _KERNEL_ENTRY_SUMMARY_LAYOUT_EXPECTED.items():
        value = summary.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            failures.append(f"{label}_{key}_invalid")
            continue
        if value != expected:
            failures.append(f"{label}_{key}_mismatch")
    return failures


def _check_kernel_entry_args(
    summary: dict[str, Any],
    *,
    label: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    prefix = "future_kernel_native_consumer_kernel_entry_args"
    if f"{prefix}_checked" not in summary:
        return [f"{label}_kernel_entry_args_missing_or_dry_run_unsupported"]
    for key, expected in {
        f"{prefix}_checked": True,
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_kernel_entry_args_abi",
        f"{prefix}_source": "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1",
        f"{prefix}_field_read_path": "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows",
        f"{prefix}_packet_chain_depth": 5,
        f"{prefix}_version": 1,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_count": expected_active,
        f"{prefix}_summary_row_ok_count": expected_active,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": expected_active,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": expected_active,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": expected_active,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": expected_active,
        f"{prefix}_summary_expert_id_read_row_ok_count": expected_active,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": expected_active,
        f"{prefix}_summary_row_metadata_read_row_ok_count": expected_active,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    for hash_key in (
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        value = summary.get(hash_key)
        if not isinstance(value, str) or not value:
            failures.append(f"{label}_{hash_key}_missing")
    for key, expected in _KERNEL_ENTRY_ARGS_LAYOUT_EXPECTED.items():
        value = summary.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            failures.append(f"{label}_{key}_invalid")
            continue
        if value != expected:
            failures.append(f"{label}_{key}_mismatch")
    return failures


def _check_kernel_entry_args_ptr(
    summary: dict[str, Any],
    *,
    label: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    prefix = "future_kernel_native_consumer_kernel_entry_args_ptr"
    if f"{prefix}_checked" not in summary:
        return [f"{label}_kernel_entry_args_ptr_missing_or_dry_run_unsupported"]
    for key, expected in {
        f"{prefix}_checked": True,
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_kernel_entry_args_ptr_abi",
        f"{prefix}_source": "premap_future_kernel_native_consumer_kernel_entry_args_abi_v1",
        f"{prefix}_field_read_path": "kernel_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows",
        f"{prefix}_packet_chain_depth": 6,
        f"{prefix}_version": 1,
        f"{prefix}_pointer_size": 8,
        f"{prefix}_entry_args_struct_size": 40,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_count": expected_active,
        f"{prefix}_summary_row_ok_count": expected_active,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": expected_active,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": expected_active,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": expected_active,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": expected_active,
        f"{prefix}_summary_expert_id_read_row_ok_count": expected_active,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": expected_active,
        f"{prefix}_summary_row_metadata_read_row_ok_count": expected_active,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    for hash_key in (
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        value = summary.get(hash_key)
        if not isinstance(value, str) or not value:
            failures.append(f"{label}_{hash_key}_missing")
    return failures


def _int_value(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _check_consumer_view_layout(
    summary: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    values: dict[str, int] = {}
    for key in _CONSUMER_VIEW_LAYOUT_INT_FIELDS:
        value = _int_value(summary, key)
        if value is None:
            failures.append(f"{label}_{key}_missing_or_non_int")
            continue
        values[key] = value
    if failures:
        return failures

    struct_size = values["future_kernel_native_consumer_view_struct_size"]
    struct_align = values["future_kernel_native_consumer_view_struct_align"]
    params_size = values["future_kernel_native_consumer_view_params_struct_size"]
    params_align = values["future_kernel_native_consumer_view_params_struct_align"]
    result_size = values["future_kernel_native_consumer_view_result_struct_size"]
    result_align = values["future_kernel_native_consumer_view_result_struct_align"]
    if struct_size <= 0:
        failures.append(f"{label}_consumer_view_struct_size_invalid")
    if result_size <= 0:
        failures.append(f"{label}_consumer_view_result_struct_size_invalid")
    if struct_align < 4 or params_align < 4 or result_align < 4:
        failures.append(f"{label}_consumer_view_align_invalid")
    if values["future_kernel_native_consumer_view_offset_params"] != 0:
        failures.append(f"{label}_consumer_view_offset_params_mismatch")
    if values["future_kernel_native_consumer_view_offset_abi_version"] != params_size:
        failures.append(
            f"{label}_consumer_view_offset_abi_version_mismatch"
        )

    expected_next = values["future_kernel_native_consumer_view_offset_abi_version"]
    for field in (
        "future_kernel_native_consumer_view_offset_source_packet_chain_depth",
        "future_kernel_native_consumer_view_offset_row_offset",
        "future_kernel_native_consumer_view_offset_row_limit",
        "future_kernel_native_consumer_view_offset_rows_per_program",
        "future_kernel_native_consumer_view_offset_payload_bytes",
        "future_kernel_native_consumer_view_offset_flags",
    ):
        expected_next += 4
        if values[field] != expected_next:
            failures.append(f"{label}_{field}_layout_mismatch")
    if values["future_kernel_native_consumer_view_offset_flags"] + 4 > struct_size:
        failures.append(f"{label}_consumer_view_flags_outside_struct")
    if struct_size % struct_align != 0:
        failures.append(f"{label}_consumer_view_struct_align_mismatch")
    if result_size % result_align != 0:
        failures.append(f"{label}_consumer_view_result_align_mismatch")
    return failures


def _check_consumer_view_row_layout(
    summary: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    values: dict[str, int] = {}
    for key in _CONSUMER_VIEW_ROW_LAYOUT_INT_FIELDS:
        value = _int_value(summary, key)
        if value is None:
            failures.append(f"{label}_{key}_missing_or_non_int")
            continue
        values[key] = value
    if failures:
        return failures

    struct_size = values["future_kernel_native_consumer_view_row_struct_size"]
    struct_align = values["future_kernel_native_consumer_view_row_struct_align"]
    expected_offsets = {
        "future_kernel_native_consumer_view_row_offset_descriptor_ptr": 0,
        "future_kernel_native_consumer_view_row_offset_packed_weight_descriptor": 8,
        "future_kernel_native_consumer_view_row_offset_scale_metadata_handle": 16,
        "future_kernel_native_consumer_view_row_offset_aux_metadata_handle": 24,
        "future_kernel_native_consumer_view_row_offset_expert_id": 32,
        "future_kernel_native_consumer_view_row_offset_address_key_hash": 40,
        "future_kernel_native_consumer_view_row_offset_row_index": 48,
    }
    for key, expected in expected_offsets.items():
        if values[key] != expected:
            failures.append(f"{label}_{key}_layout_mismatch")
    if struct_size != 56:
        failures.append(f"{label}_consumer_view_row_struct_size_mismatch")
    if struct_align != 8:
        failures.append(f"{label}_consumer_view_row_struct_align_mismatch")
    if struct_align <= 0 or struct_size % struct_align != 0:
        failures.append(f"{label}_consumer_view_row_struct_align_invalid")
    return failures


def _check_child_stub_artifact(
    child: dict[str, Any],
    *,
    label: str,
    parent: Path,
    expected_offset: int,
    expected_limit: int,
    expected_active: int,
    expected_block_threads: int,
    require_child_program_view_ptr_abi: bool,
    require_child_kernel_arg_packet_abi: bool,
    require_child_kernel_entry_args_abi: bool,
    require_child_kernel_entry_args_ptr_abi: bool,
) -> list[str]:
    failures: list[str] = []
    stub_path = _resolve_child_path(child.get("stub_output_json"), parent=parent)
    if stub_path is None:
        return [f"{label}_child_stub_output_json_missing"]
    stub_payload, stub_error = _safe_load_json(stub_path)
    if stub_payload is None:
        return [f"{label}_child_stub_output_json_read_failed:{stub_error}"]
    for key, expected in {
        "passed": True,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "future_kernel_native_consumer_view_checked": True,
        "future_kernel_native_consumer_view_row_count": expected_active,
        "future_kernel_native_consumer_view_row_ok_count": expected_active,
        "future_kernel_native_consumer_view_error_count": 0,
        "future_kernel_native_consumer_view_row_offset": expected_offset,
        "future_kernel_native_consumer_view_row_limit": expected_limit,
        "future_kernel_native_consumer_view_rows_per_program": expected_block_threads,
        "future_kernel_native_consumer_view_source_packet_chain_depth": 3,
        "future_kernel_native_consumer_view_payload_bytes": 0,
        "future_kernel_native_consumer_view_passed_to_kernel": False,
        "future_kernel_native_consumer_view_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_view_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation": False,
    }.items():
        if stub_payload.get(key) != expected:
            failures.append(f"{label}_child_stub_artifact_{key}_mismatch")
    failures.extend(
        _check_field_reads(
            stub_payload,
            label=f"{label}_child_stub_artifact",
            prefix="future_kernel_native_consumer_view",
            expected_active=expected_active,
        )
    )
    failures.extend(
        _check_consumer_view_handle_projection(
            stub_payload,
            label=f"{label}_child_stub_artifact",
        )
    )
    failures.extend(
        _check_consumer_view_layout(
            stub_payload,
            label=f"{label}_child_stub_artifact",
        )
    )
    failures.extend(
        _check_consumer_view_row_layout(
            stub_payload,
            label=f"{label}_child_stub_artifact",
        )
    )
    if require_child_program_view_ptr_abi:
        failures.extend(
            _check_program_view_ptr_abi(
                stub_payload,
                label=f"{label}_child_stub_artifact",
                expected_active=expected_active,
            )
        )
    if require_child_kernel_arg_packet_abi:
        failures.extend(
            _check_kernel_arg_packet_abi(
                stub_payload,
                label=f"{label}_child_stub_artifact",
                expected_active=expected_active,
            )
        )
    if require_child_kernel_entry_args_abi:
        if not require_child_kernel_arg_packet_abi:
            failures.extend(
                _check_kernel_entry_summary(
                    stub_payload,
                    label=f"{label}_child_stub_artifact",
                    expected_active=expected_active,
                )
            )
        failures.extend(
            _check_kernel_entry_args(
                stub_payload,
                label=f"{label}_child_stub_artifact",
                expected_active=expected_active,
            )
        )
    if require_child_kernel_entry_args_ptr_abi:
        failures.extend(
            _check_kernel_entry_args_ptr(
                stub_payload,
                label=f"{label}_child_stub_artifact",
                expected_active=expected_active,
            )
        )
    return failures


def _check_child_artifact(
    child: dict[str, Any],
    *,
    label: str,
    parent: Path,
    expected_offset: int,
    expected_limit: int,
    expected_active: int,
    expected_programs: int,
    expected_block_threads: int,
    expected_merged_row_count: int,
    expected_mirror_field: str | None,
    require_child_program_view_ptr_abi: bool,
    require_child_kernel_arg_packet_abi: bool,
    require_child_kernel_entry_args_abi: bool,
    require_child_kernel_entry_args_ptr_abi: bool,
) -> list[str]:
    failures: list[str] = []
    expected_pairs: dict[str, Any] = {
        "passed": True,
        "failures": [],
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "handle_projection_hashchain_equal": True,
        "dispatch_row_offset": expected_offset,
        "dispatch_row_limit": expected_limit,
        "dispatch_active_rows": expected_active,
        "dispatch_expected_program_count": expected_programs,
        "block_threads": expected_block_threads,
        "merged_row_count": expected_merged_row_count,
    }
    if expected_mirror_field is not None:
        expected_pairs["mirror_field"] = expected_mirror_field
    for key, expected in expected_pairs.items():
        if child.get(key) != expected:
            failures.append(f"{label}_child_{key}_mismatch")
    stub_summary = child.get("stub_summary")
    if not isinstance(stub_summary, dict):
        failures.append(f"{label}_child_stub_summary_missing")
    else:
        for key, expected in {
            "passed": True,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_row_count": expected_active,
            "future_kernel_native_arg_slot_consumer_row_ok_count": expected_active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": expected_active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": expected_active,
            "future_kernel_native_dispatch_consumer_program_count": expected_programs,
            "future_kernel_native_dispatch_consumer_block_x": expected_block_threads,
            "future_kernel_native_dispatch_consumer_row_limit": expected_limit,
            "future_kernel_native_consumer_view_checked": True,
            "future_kernel_native_consumer_view_row_count": expected_active,
            "future_kernel_native_consumer_view_row_ok_count": expected_active,
            "future_kernel_native_consumer_view_error_count": 0,
            "future_kernel_native_consumer_view_source_packet_chain_depth": 3,
            "future_kernel_native_consumer_view_payload_bytes": 0,
            "future_kernel_native_consumer_view_passed_to_kernel": False,
            "future_kernel_native_consumer_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_view_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation": False,
        }.items():
            if stub_summary.get(key) != expected:
                failures.append(f"{label}_child_stub_{key}_mismatch")
        if expected_mirror_field is not None and stub_summary.get(
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
        ) != expected_mirror_field:
            failures.append(
                f"{label}_child_stub_single_field_mirror_field_name_mismatch"
            )
        failures.extend(
            _check_future_field_masks(
                stub_summary,
                label=label,
                require_child_kernel_arg_packet_abi=(
                    require_child_kernel_arg_packet_abi
                ),
            )
        )
        failures.extend(
            _check_field_reads(
                stub_summary,
                label=label,
                prefix="future_kernel_native_arg_slot_consumer",
                expected_active=expected_active,
            )
        )
        failures.extend(
            _check_field_reads(
                stub_summary,
                label=label,
                prefix="future_kernel_native_consumer_view",
                expected_active=expected_active,
            )
        )
        failures.extend(
            _check_consumer_view_handle_projection(stub_summary, label=label)
        )
        if require_child_program_view_ptr_abi:
            failures.extend(
                _check_program_view_ptr_abi(
                    stub_summary,
                    label=label,
                    expected_active=expected_active,
                )
            )
        if require_child_kernel_arg_packet_abi:
            failures.extend(
                _check_kernel_arg_packet_abi(
                    stub_summary,
                    label=label,
                    expected_active=expected_active,
                )
            )
        if require_child_kernel_entry_args_abi:
            if not require_child_kernel_arg_packet_abi:
                failures.extend(
                    _check_kernel_entry_summary(
                        stub_summary,
                        label=label,
                        expected_active=expected_active,
                    )
                )
            failures.extend(
                _check_kernel_entry_args(
                    stub_summary,
                    label=label,
                    expected_active=expected_active,
                )
            )
        if require_child_kernel_entry_args_ptr_abi:
            failures.extend(
                _check_kernel_entry_args_ptr(
                    stub_summary,
                    label=label,
                    expected_active=expected_active,
                )
            )
    failures.extend(
        _check_child_stub_artifact(
            child,
            label=label,
            parent=parent,
            expected_offset=expected_offset,
            expected_limit=expected_limit,
            expected_active=expected_active,
            expected_block_threads=expected_block_threads,
            require_child_program_view_ptr_abi=require_child_program_view_ptr_abi,
            require_child_kernel_arg_packet_abi=require_child_kernel_arg_packet_abi,
            require_child_kernel_entry_args_abi=(
                require_child_kernel_entry_args_abi
            ),
            require_child_kernel_entry_args_ptr_abi=(
                require_child_kernel_entry_args_ptr_abi
            ),
        )
    )
    return failures


def check_window_sweep_artifact(
    path: Path,
    *,
    expected_window_size: int = 512,
    expected_block_threads: int = 256,
    min_row_count: int = 257,
    expected_mirror_field: str | None = "scale_metadata_handle",
    require_child_artifacts: bool = True,
    require_non_degenerate_windows: bool = True,
    require_child_program_view_ptr_abi: bool = False,
    require_child_kernel_arg_packet_abi: bool = False,
    require_child_kernel_entry_args_abi: bool = False,
    require_child_kernel_entry_args_ptr_abi: bool = False,
) -> dict[str, Any]:
    sweep_path = path.resolve()
    payload, error = _safe_load_json(sweep_path)
    if payload is None:
        return {
            "passed": False,
            "failures": [f"window_sweep_json_read_failed:{error}"],
            "source": "online_merged_future_native_arg_slot_window_sweep_check",
            "window_sweep_json": str(sweep_path),
        }

    failures: list[str] = []
    if require_child_kernel_entry_args_ptr_abi and not require_child_kernel_entry_args_abi:
        failures.append("require_child_kernel_entry_args_ptr_requires_entry_args_abi")
    if payload.get("source") != "online_merged_future_native_arg_slot_window_sweep_runner":
        failures.append("source_mismatch")
    if payload.get("passed") is not True:
        failures.append("window_sweep_not_passed")
    if payload.get("failures") != []:
        failures.append("window_sweep_failures_not_empty")
    if payload.get("payload_bytes") != 0:
        failures.append("payload_bytes_mismatch")
    for field in ("passed_to_kernel", "changes_kernel_launch_args"):
        if payload.get(field) is not False:
            failures.append(f"{field}_mismatch")
    if payload.get("window_size") != int(expected_window_size):
        failures.append("window_size_mismatch")
    if expected_mirror_field is not None and payload.get("mirror_field") != expected_mirror_field:
        failures.append("mirror_field_mismatch")

    try:
        row_count = int(payload.get("row_count"))
    except (TypeError, ValueError):
        row_count = -1
        failures.append("row_count_invalid")
    if row_count < int(min_row_count):
        failures.append("row_count_below_min")
    if require_non_degenerate_windows and row_count <= int(expected_window_size):
        failures.append("row_count_not_larger_than_window_size")

    windows = payload.get("windows")
    if not isinstance(windows, dict):
        failures.append("windows_missing")
        windows = {}

    if row_count > 0:
        expected_bounds = {
            "full": (0, row_count),
            **_window_bounds(row_count, int(expected_window_size)),
        }
    else:
        expected_bounds = {}

    for label in REQUIRED_WINDOWS:
        window = windows.get(label)
        if not isinstance(window, dict):
            failures.append(f"{label}_window_missing")
            continue
        expected_offset, expected_limit = expected_bounds.get(label, (-1, -1))
        expected_active = expected_limit - expected_offset
        if window.get("passed") is not True:
            failures.append(f"{label}_window_not_passed")
        if window.get("merged_row_count") != row_count:
            failures.append(f"{label}_merged_row_count_mismatch")
        if window.get("dispatch_row_offset") != expected_offset:
            failures.append(f"{label}_dispatch_row_offset_mismatch")
        if window.get("dispatch_row_limit") != expected_limit:
            failures.append(f"{label}_dispatch_row_limit_mismatch")
        if window.get("dispatch_active_rows") != expected_active:
            failures.append(f"{label}_dispatch_active_rows_mismatch")
        expected_programs = int(math.ceil(expected_active / int(expected_block_threads)))
        if window.get("dispatch_expected_program_count") != expected_programs:
            failures.append(f"{label}_dispatch_expected_program_count_mismatch")

        if require_child_artifacts:
            child_path = _resolve_child_path(window.get("output_json"), parent=sweep_path.parent)
            if child_path is None:
                failures.append(f"{label}_child_output_json_missing")
                continue
            child, child_error = _safe_load_json(child_path)
            if child is None:
                failures.append(f"{label}_child_output_json_read_failed:{child_error}")
                continue
            failures.extend(
                _check_child_artifact(
                    child,
                    label=label,
                    parent=child_path.parent,
                    expected_offset=expected_offset,
                    expected_limit=expected_limit,
                    expected_active=expected_active,
                    expected_programs=expected_programs,
                    expected_block_threads=int(expected_block_threads),
                    expected_merged_row_count=row_count,
                    expected_mirror_field=expected_mirror_field,
                    require_child_program_view_ptr_abi=bool(
                        require_child_program_view_ptr_abi
                    ),
                    require_child_kernel_arg_packet_abi=bool(
                        require_child_kernel_arg_packet_abi
                    ),
                    require_child_kernel_entry_args_abi=bool(
                        require_child_kernel_entry_args_abi
                    ),
                    require_child_kernel_entry_args_ptr_abi=bool(
                        require_child_kernel_entry_args_ptr_abi
                    ),
                )
            )

    return {
        "passed": not failures,
        "failures": failures,
        "source": "online_merged_future_native_arg_slot_window_sweep_check",
        "window_sweep_json": str(sweep_path),
        "expected_window_size": int(expected_window_size),
        "expected_block_threads": int(expected_block_threads),
        "min_row_count": int(min_row_count),
        "expected_mirror_field": expected_mirror_field,
        "require_child_artifacts": bool(require_child_artifacts),
        "require_non_degenerate_windows": bool(require_non_degenerate_windows),
        "require_child_field_masks": bool(require_child_artifacts),
        "require_child_consumer_view": bool(require_child_artifacts),
        "require_child_consumer_view_layout": bool(require_child_artifacts),
        "require_child_consumer_view_row_layout": bool(require_child_artifacts),
        "require_child_consumer_view_handle_projection": bool(require_child_artifacts),
        "require_child_program_view_ptr_abi": bool(
            require_child_program_view_ptr_abi
        ),
        "require_child_kernel_arg_packet_abi": bool(
            require_child_kernel_arg_packet_abi
        ),
        "require_child_kernel_entry_args_abi": bool(
            require_child_kernel_entry_args_abi
        ),
        "require_child_kernel_entry_args_ptr_abi": bool(
            require_child_kernel_entry_args_ptr_abi
        ),
        "require_child_kernel_entry_row_metadata": bool(
            require_child_kernel_entry_args_abi
            or require_child_kernel_entry_args_ptr_abi
        ),
        "row_count": row_count,
        "windows_checked": list(REQUIRED_WINDOWS),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window_sweep_json", nargs="?", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--expected-window-size", type=int, default=512)
    parser.add_argument("--expected-block-threads", type=int, default=256)
    parser.add_argument("--min-row-count", type=int, default=257)
    parser.add_argument("--expected-mirror-field", default="scale_metadata_handle")
    parser.add_argument("--no-require-child-artifacts", action="store_true")
    parser.add_argument("--allow-degenerate-windows", action="store_true")
    parser.add_argument("--require-child-program-view-ptr-abi", action="store_true")
    parser.add_argument("--require-child-kernel-arg-packet-abi", action="store_true")
    parser.add_argument("--require-child-kernel-entry-args-abi", action="store_true")
    parser.add_argument("--require-child-kernel-entry-args-ptr-abi", action="store_true")
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_window_sweep_artifact(
        args.window_sweep_json,
        expected_window_size=int(args.expected_window_size),
        expected_block_threads=int(args.expected_block_threads),
        min_row_count=int(args.min_row_count),
        expected_mirror_field=args.expected_mirror_field,
        require_child_artifacts=not bool(args.no_require_child_artifacts),
        require_non_degenerate_windows=not bool(args.allow_degenerate_windows),
        require_child_program_view_ptr_abi=bool(
            args.require_child_program_view_ptr_abi
        ),
        require_child_kernel_arg_packet_abi=bool(
            args.require_child_kernel_arg_packet_abi
        ),
        require_child_kernel_entry_args_abi=bool(
            args.require_child_kernel_entry_args_abi
        ),
        require_child_kernel_entry_args_ptr_abi=bool(
            args.require_child_kernel_entry_args_ptr_abi
        ),
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
