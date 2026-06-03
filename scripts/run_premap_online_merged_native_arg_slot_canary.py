#!/usr/bin/env python3
"""Run a merged online prelaunch typed-consumer arg-slot canary.

This runner turns the existing online prelaunch native-input exports into a
single multiprogram native-stub input, then runs the future native arg-slot
consumer stub against that merged input.

It is still a no-op bridge:

* no payload dereference,
* no ready credit,
* no router or descriptor-order mutation,
* no current WNA16 kernel-argument pass.

The merged table is diagnostic evidence only.  It is explicitly not a single
vLLM launch table; it exists to prove that the future typed ABI can iterate a
real online-derived row stream across multiple native programs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.materialize_premap_online_merged_typed_consumer_input import (  # noqa: E402
    input_paths_from_runner_artifact,
    materialize_merged_input,
)
from scripts.run_premap_typed_consumer_stub import run_stub, validate_macros  # noqa: E402


DEFAULT_SOURCE_RUNNER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json"
)
DEFAULT_MERGED_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_prelaunch_typed_consumer_input_arg_slot_32tables.json"
)
DEFAULT_STUB_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_merged_future_native_arg_slot_32tables_canary.json"
)
DEFAULT_REPORT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_canary_runner.json"
)
LAB_DEFAULT_GPU_DEVICE = 1

ARG_SLOT_BASE_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
MIRROR_FIELD_MACRO = {
    "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "packed_weight_descriptor": (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD"
    ),
    "scale_metadata_handle": (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD"
    ),
    "aux_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
}
ARG_SLOT_HANDLE_PROJECTION_FIELDS = tuple(MIRROR_FIELD_MACRO)
ARG_SLOT_FIELD_READ_FIELDS = ARG_SLOT_HANDLE_PROJECTION_FIELDS
ARG_SLOT_MACROS = [
    *ARG_SLOT_BASE_MACROS,
    MIRROR_FIELD_MACRO["scale_metadata_handle"],
]
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
    "future_kernel_native_consumer_kernel_arg_packet",
)
_HANDLE_PROJECTION_HASH_PREFIXES = (
    "future_kernel_native_dispatch_consumer",
    "future_kernel_native_dispatch_ptr_consumer",
    "future_kernel_native_arg_slot_consumer",
    "future_kernel_native_consumer_view",
    "future_kernel_native_consumer_program_view",
)

STUB_SUMMARY_KEYS = (
    "passed",
    "ok",
    "row_count",
    "row_ok_count",
    "error_count",
    "input_json",
    "input_source",
    "payload_bytes",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
    "requested_macros",
    "future_kernel_native_consumer_checked",
    "future_kernel_native_consumer_row_count",
    "future_kernel_native_consumer_row_ok_count",
    "future_kernel_native_consumer_field_mask",
    "future_kernel_native_consumer_required_field_mask",
    "future_kernel_native_launch_consumer_checked",
    "future_kernel_native_launch_consumer_row_count",
    "future_kernel_native_launch_consumer_row_ok_count",
    "future_kernel_native_launch_consumer_field_mask",
    "future_kernel_native_launch_consumer_required_field_mask",
    "future_kernel_native_dispatch_consumer_checked",
    "future_kernel_native_dispatch_consumer_grid_x",
    "future_kernel_native_dispatch_consumer_block_x",
    "future_kernel_native_dispatch_consumer_active_rows",
    "future_kernel_native_dispatch_consumer_row_offset",
    "future_kernel_native_dispatch_consumer_row_limit",
    "future_kernel_native_dispatch_consumer_rows_per_program",
    "future_kernel_native_dispatch_consumer_program_count",
    "future_kernel_native_dispatch_consumer_full_program_count",
    "future_kernel_native_dispatch_consumer_last_program_active_rows",
    "future_kernel_native_dispatch_consumer_inactive_lane_count",
    "future_kernel_native_dispatch_consumer_first_program_row_offset",
    "future_kernel_native_dispatch_consumer_last_program_row_offset",
    "future_kernel_native_dispatch_consumer_program_iteration_hash",
    "future_kernel_native_dispatch_consumer_program_iteration_checked",
    "future_kernel_native_dispatch_consumer_launch_covers_active_rows",
    "future_kernel_native_dispatch_consumer_launch_minimal_cover",
    "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_dispatch_consumer_field_mask",
    "future_kernel_native_dispatch_consumer_required_field_mask",
    "future_kernel_native_dispatch_ptr_consumer_checked",
    "future_kernel_native_dispatch_ptr_consumer_packet_visible",
    "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible",
    "future_kernel_native_dispatch_ptr_consumer_row_count",
    "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
    "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_dispatch_ptr_consumer_field_mask",
    "future_kernel_native_dispatch_ptr_consumer_required_field_mask",
    "future_kernel_native_arg_slot_consumer_checked",
    "future_kernel_native_arg_slot_consumer_slot_visible",
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible",
    "future_kernel_native_arg_slot_consumer_dispatch_packet_visible",
    "future_kernel_native_arg_slot_consumer_packet_chain_depth",
    "future_kernel_native_arg_slot_consumer_row_count",
    "future_kernel_native_arg_slot_consumer_row_ok_count",
    "future_kernel_native_arg_slot_consumer_error_count",
    "future_kernel_native_arg_slot_consumer_payload_bytes",
    "future_kernel_native_arg_slot_consumer_passed_to_kernel",
    "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args",
    "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible",
    "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_checked",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_kind",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
    "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count",
    "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count",
    "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count",
    "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count",
    "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator",
    "future_kernel_native_arg_slot_consumer_field_mask",
    "future_kernel_native_arg_slot_consumer_required_field_mask",
    "future_kernel_native_consumer_view_checked",
    "future_kernel_native_consumer_view_source",
    "future_kernel_native_consumer_view_source_packet_chain_depth",
    "future_kernel_native_consumer_view_row_count",
    "future_kernel_native_consumer_view_row_ok_count",
    "future_kernel_native_consumer_view_error_count",
    "future_kernel_native_consumer_view_row_offset",
    "future_kernel_native_consumer_view_row_limit",
    "future_kernel_native_consumer_view_rows_per_program",
    "future_kernel_native_consumer_view_payload_bytes",
    "future_kernel_native_consumer_view_passed_to_kernel",
    "future_kernel_native_consumer_view_changes_kernel_launch_args",
    "future_kernel_native_consumer_view_current_wna16_arg_compatible",
    "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_view_hash_accumulator",
    "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    "future_kernel_native_consumer_view_descriptor_ptr_read_row_count",
    "future_kernel_native_consumer_view_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_view_descriptor_ptr_read_error_count",
    "future_kernel_native_consumer_view_descriptor_ptr_read_hash_accumulator",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_count",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_error_count",
    "future_kernel_native_consumer_view_packed_weight_descriptor_read_hash_accumulator",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_row_count",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_error_count",
    "future_kernel_native_consumer_view_scale_metadata_handle_read_hash_accumulator",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_row_count",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_error_count",
    "future_kernel_native_consumer_view_aux_metadata_handle_read_hash_accumulator",
    "future_kernel_native_consumer_view_field_mask",
    "future_kernel_native_consumer_view_required_field_mask",
    "future_kernel_native_consumer_program_view_checked",
    "future_kernel_native_consumer_program_view_source",
    "future_kernel_native_consumer_program_view_row_count",
    "future_kernel_native_consumer_program_view_row_ok_count",
    "future_kernel_native_consumer_program_view_error_count",
    "future_kernel_native_consumer_program_view_program_count",
    "future_kernel_native_consumer_program_view_full_program_count",
    "future_kernel_native_consumer_program_view_last_program_active_rows",
    "future_kernel_native_consumer_program_view_inactive_lane_count",
    "future_kernel_native_consumer_program_view_first_program_row_offset",
    "future_kernel_native_consumer_program_view_last_program_row_offset",
    "future_kernel_native_consumer_program_view_program_iteration_hash",
    "future_kernel_native_consumer_program_view_row_assignment_formula",
    "future_kernel_native_consumer_program_view_hash_accumulator",
    "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator",
    "future_kernel_native_consumer_program_view_payload_bytes",
    "future_kernel_native_consumer_program_view_passed_to_kernel",
    "future_kernel_native_consumer_program_view_changes_kernel_launch_args",
    "future_kernel_native_consumer_program_view_current_wna16_arg_compatible",
    "future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_program_view_field_mask",
    "future_kernel_native_consumer_program_view_required_field_mask",
    "future_kernel_native_consumer_program_view_ptr_checked",
    "future_kernel_native_consumer_program_view_ptr_source",
    "future_kernel_native_consumer_program_view_ptr_row_count",
    "future_kernel_native_consumer_program_view_ptr_row_ok_count",
    "future_kernel_native_consumer_program_view_ptr_error_count",
    "future_kernel_native_consumer_program_view_ptr_hash_accumulator",
    "future_kernel_native_consumer_program_view_ptr_payload_bytes",
    "future_kernel_native_consumer_program_view_ptr_passed_to_kernel",
    "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args",
    "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible",
    "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_program_view_ptr_field_mask",
    "future_kernel_native_consumer_program_view_ptr_required_field_mask",
    "future_kernel_native_consumer_kernel_arg_packet_checked",
    "future_kernel_native_consumer_kernel_arg_packet_source",
    "future_kernel_native_consumer_kernel_arg_packet_row_count",
    "future_kernel_native_consumer_kernel_arg_packet_row_ok_count",
    "future_kernel_native_consumer_kernel_arg_packet_error_count",
    "future_kernel_native_consumer_kernel_arg_packet_hash_accumulator",
    "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_count",
    "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_error_count",
    "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_count",
    "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_error_count",
    "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_count",
    "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_error_count",
    "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_count",
    "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_error_count",
    "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_arg_packet_payload_bytes",
    "future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel",
    "future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args",
    "future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible",
    "future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_kernel_arg_packet_field_mask",
    "future_kernel_native_consumer_kernel_arg_packet_required_field_mask",
    "future_kernel_native_consumer_kernel_entry_summary_checked",
    "future_kernel_native_consumer_kernel_entry_summary_mode",
    "future_kernel_native_consumer_kernel_entry_summary_source",
    "future_kernel_native_consumer_kernel_entry_summary_field_read_path",
    "future_kernel_native_consumer_kernel_entry_summary_packet_chain_depth",
    "future_kernel_native_consumer_kernel_entry_summary_packet_valid",
    "future_kernel_native_consumer_kernel_entry_summary_row_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_summary_error_count",
    "future_kernel_native_consumer_kernel_entry_summary_field_mask",
    "future_kernel_native_consumer_kernel_entry_summary_payload_bytes",
    "future_kernel_native_consumer_kernel_entry_summary_passed_to_kernel",
    "future_kernel_native_consumer_kernel_entry_summary_changes_kernel_launch_args",
    "future_kernel_native_consumer_kernel_entry_summary_current_wna16_arg_compatible",
    "future_kernel_native_consumer_kernel_entry_summary_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_args_checked",
    "future_kernel_native_consumer_kernel_entry_args_mode",
    "future_kernel_native_consumer_kernel_entry_args_source",
    "future_kernel_native_consumer_kernel_entry_args_field_read_path",
    "future_kernel_native_consumer_kernel_entry_args_packet_chain_depth",
    "future_kernel_native_consumer_kernel_entry_args_version",
    "future_kernel_native_consumer_kernel_entry_args_struct_size",
    "future_kernel_native_consumer_kernel_entry_args_struct_align",
    "future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet",
    "future_kernel_native_consumer_kernel_entry_args_offset_summary",
    "future_kernel_native_consumer_kernel_entry_args_offset_abi_version",
    "future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet_struct_size",
    "future_kernel_native_consumer_kernel_entry_args_offset_summary_struct_size",
    "future_kernel_native_consumer_kernel_entry_args_offset_payload_bytes",
    "future_kernel_native_consumer_kernel_entry_args_offset_flags",
    "future_kernel_native_consumer_kernel_entry_args_kernel_arg_packet_struct_size",
    "future_kernel_native_consumer_kernel_entry_args_summary_struct_size",
    "future_kernel_native_consumer_kernel_entry_args_summary_packet_valid",
    "future_kernel_native_consumer_kernel_entry_args_summary_row_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_expert_id_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_address_key_hash_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_error_count",
    "future_kernel_native_consumer_kernel_entry_args_summary_field_mask",
    "future_kernel_native_consumer_kernel_entry_args_payload_bytes",
    "future_kernel_native_consumer_kernel_entry_args_passed_to_kernel",
    "future_kernel_native_consumer_kernel_entry_args_changes_kernel_launch_args",
    "future_kernel_native_consumer_kernel_entry_args_current_wna16_arg_compatible",
    "future_kernel_native_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation",
    "future_kernel_native_consumer_kernel_entry_args_summary_row_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_args_summary_field_read_hash_accumulator",
    "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in STUB_SUMMARY_KEYS if key in payload}


def _program_count(row_count: int, block_threads: int) -> int:
    return (int(row_count) + int(block_threads) - 1) // int(block_threads)


def _future_field_mask_expectations() -> dict[str, int]:
    expectations: dict[str, int] = {}
    for prefix in _FUTURE_KERNEL_FIELD_MASK_PREFIXES:
        expectations[f"{prefix}_field_mask"] = _FUTURE_KERNEL_ALL_FIELD_MASK
        expectations[f"{prefix}_required_field_mask"] = (
            _FUTURE_KERNEL_REQUIRED_FIELD_MASK
        )
    return expectations


def _check_future_field_masks(stub: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for prefix in _FUTURE_KERNEL_FIELD_MASK_PREFIXES:
        field_key = f"{prefix}_field_mask"
        required_key = f"{prefix}_required_field_mask"
        field_mask = stub.get(field_key)
        required_mask = stub.get(required_key)
        if field_mask is None:
            failures.append(f"{field_key}_missing")
            continue
        if required_mask is None:
            failures.append(f"{required_key}_missing")
            continue
        if (
            not isinstance(field_mask, int)
            or isinstance(field_mask, bool)
            or not isinstance(required_mask, int)
            or isinstance(required_mask, bool)
        ):
            failures.append(f"{prefix}_field_mask_type_mismatch")
            continue
        if required_mask != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
            failures.append(f"{required_key}_mismatch")
        if field_mask != _FUTURE_KERNEL_ALL_FIELD_MASK:
            failures.append(f"{field_key}_not_all_fields")
    return failures


def _parse_hex64(value: object) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = int(value, 16)
    except ValueError:
        return None
    if parsed < 0 or parsed > 0xFFFFFFFFFFFFFFFF:
        return None
    return parsed


def _check_prefixed_field_reads(
    stub: dict[str, Any],
    *,
    active_rows: int,
    prefix_root: str,
) -> list[str]:
    failures: list[str] = []
    for field in ARG_SLOT_FIELD_READ_FIELDS:
        prefix = f"{prefix_root}_{field}_read"
        expected = {
            f"{prefix}_row_count": int(active_rows),
            f"{prefix}_row_ok_count": int(active_rows),
            f"{prefix}_error_count": 0,
        }
        for key, value in expected.items():
            if stub.get(key) != value:
                failures.append(f"{key}_mismatch:{stub.get(key)!r}!={value!r}")
        hash_key = f"{prefix}_hash_accumulator"
        hash_value = stub.get(hash_key)
        if not isinstance(hash_value, str) or not hash_value:
            failures.append(f"{hash_key}_missing")
    return failures


def _check_arg_slot_field_reads(
    stub: dict[str, Any],
    *,
    active_rows: int,
) -> list[str]:
    return _check_prefixed_field_reads(
        stub,
        active_rows=active_rows,
        prefix_root="future_kernel_native_arg_slot_consumer",
    )


def _check_consumer_view_field_reads(
    stub: dict[str, Any],
    *,
    active_rows: int,
) -> list[str]:
    failures: list[str] = []
    if stub.get("future_kernel_native_consumer_view_checked") is not True:
        failures.append("future_kernel_native_consumer_view_checked_mismatch")
    if stub.get("future_kernel_native_consumer_view_source_packet_chain_depth") != 3:
        failures.append("future_kernel_native_consumer_view_source_packet_chain_depth_mismatch")
    failures.extend(
        _check_prefixed_field_reads(
            stub,
            active_rows=active_rows,
            prefix_root="future_kernel_native_consumer_view",
        )
    )
    return failures


def _check_kernel_arg_packet_field_reads(
    stub: dict[str, Any],
    *,
    active_rows: int,
) -> list[str]:
    failures: list[str] = []
    if stub.get("future_kernel_native_consumer_kernel_arg_packet_checked") is not True:
        failures.append("future_kernel_native_consumer_kernel_arg_packet_checked_mismatch")
    failures.extend(
        _check_prefixed_field_reads(
            stub,
            active_rows=active_rows,
            prefix_root="future_kernel_native_consumer_kernel_arg_packet",
        )
    )
    return failures


def _check_kernel_entry_summary(
    stub: dict[str, Any],
    *,
    active_rows: int,
) -> list[str]:
    failures: list[str] = []
    prefix = "future_kernel_native_consumer_kernel_entry_summary"
    expected = {
        f"{prefix}_checked": True,
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_kernel_entry_summary_abi",
        f"{prefix}_source": "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1",
        f"{prefix}_field_read_path": "kernel_entry_summary_to_kernel_arg_packet_to_program_view_rows",
        f"{prefix}_packet_chain_depth": 4,
        f"{prefix}_packet_valid": 1,
        f"{prefix}_row_count": int(active_rows),
        f"{prefix}_row_ok_count": int(active_rows),
        f"{prefix}_descriptor_ptr_read_row_ok_count": int(active_rows),
        f"{prefix}_packed_weight_descriptor_read_row_ok_count": int(active_rows),
        f"{prefix}_scale_metadata_handle_read_row_ok_count": int(active_rows),
        f"{prefix}_aux_metadata_handle_read_row_ok_count": int(active_rows),
        f"{prefix}_expert_id_read_row_ok_count": int(active_rows),
        f"{prefix}_address_key_hash_read_row_ok_count": int(active_rows),
        f"{prefix}_row_metadata_read_row_ok_count": int(active_rows),
        f"{prefix}_error_count": 0,
        f"{prefix}_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    for key, value in expected.items():
        if stub.get(key) != value:
            failures.append(f"{key}_mismatch:{stub.get(key)!r}!={value!r}")
    for hash_key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
    ):
        hash_value = stub.get(hash_key)
        if not isinstance(hash_value, str) or not hash_value:
            failures.append(f"{hash_key}_missing")
    return failures


def _check_kernel_entry_args(
    stub: dict[str, Any],
    *,
    active_rows: int,
) -> list[str]:
    failures: list[str] = []
    prefix = "future_kernel_native_consumer_kernel_entry_args"
    expected = {
        f"{prefix}_checked": True,
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_kernel_entry_args_abi",
        f"{prefix}_source": "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1",
        f"{prefix}_field_read_path": "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows",
        f"{prefix}_packet_chain_depth": 5,
        f"{prefix}_version": 1,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_count": int(active_rows),
        f"{prefix}_summary_row_ok_count": int(active_rows),
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_expert_id_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_address_key_hash_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_row_metadata_read_row_ok_count": int(active_rows),
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    for key, value in expected.items():
        if stub.get(key) != value:
            failures.append(f"{key}_mismatch:{stub.get(key)!r}!={value!r}")
    for hash_key in (
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        hash_value = stub.get(hash_key)
        if not isinstance(hash_value, str) or not hash_value:
            failures.append(f"{hash_key}_missing")
    for size_key in (
        f"{prefix}_struct_size",
        f"{prefix}_struct_align",
        f"{prefix}_kernel_arg_packet_struct_size",
        f"{prefix}_summary_struct_size",
    ):
        value = stub.get(size_key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            failures.append(f"{size_key}_invalid")
    if stub.get(f"{prefix}_offset_kernel_arg_packet") != 0:
        failures.append(f"{prefix}_offset_kernel_arg_packet_mismatch")
    return failures


def arg_slot_macros(mirror_field: str) -> list[str]:
    try:
        mirror_macro = MIRROR_FIELD_MACRO[mirror_field]
    except KeyError as exc:
        raise ValueError(f"unsupported mirror field: {mirror_field}") from exc
    return validate_macros([*ARG_SLOT_BASE_MACROS, mirror_macro])


def _dispatch_bounds(
    *,
    row_count: int,
    dispatch_row_offset: int,
    dispatch_row_limit: int | None,
    tail_window_size: int | None,
) -> tuple[int, int]:
    if tail_window_size is not None:
        if tail_window_size <= 0:
            raise ValueError("tail-window-size must be positive when provided")
        if dispatch_row_offset != 0 or dispatch_row_limit is not None:
            raise ValueError(
                "tail-window-size cannot be combined with explicit dispatch row bounds"
            )
        limit = int(row_count)
        offset = max(0, limit - int(tail_window_size))
    else:
        offset = int(dispatch_row_offset)
        limit = int(dispatch_row_limit) if dispatch_row_limit is not None else int(row_count)
    if offset < 0:
        raise ValueError("dispatch-row-offset must be non-negative")
    if limit <= offset or limit > int(row_count):
        raise ValueError("dispatch row bounds must satisfy 0 <= offset < limit <= row_count")
    return offset, limit


def _validate_stub(
    stub: dict[str, Any],
    *,
    merged_input: dict[str, Any],
    merged_output_json: Path,
    block_threads: int,
    dispatch_row_offset: int,
    dispatch_row_limit: int,
    mirror_field: str,
) -> list[str]:
    failures: list[str] = []
    row_count = int(merged_input["_meta"]["row_count"])
    active_rows = int(dispatch_row_limit) - int(dispatch_row_offset)
    expected_program_count = _program_count(active_rows, block_threads)
    expected_full_program_count = int(active_rows) // int(block_threads)
    expected_launched_lanes = int(expected_program_count) * int(block_threads)
    expected_inactive_lane_count = expected_launched_lanes - int(active_rows)
    expected_previous_program_lanes = max(0, int(expected_program_count) - 1) * int(
        block_threads
    )
    expected_last_program_active_rows = int(active_rows) - expected_previous_program_lanes
    expected_first_program_row_offset = int(dispatch_row_offset)
    expected_last_program_row_offset = (
        int(dispatch_row_offset) + expected_previous_program_lanes
    )
    expected_input_json = str(merged_output_json)
    if stub.get("input_json") != expected_input_json:
        failures.append("stub_input_json_mismatch")
    expected_scalars: dict[str, Any] = {
        "passed": True,
        "ok": True,
        "row_count": row_count,
        "row_ok_count": row_count,
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "future_kernel_native_arg_slot_consumer_checked": True,
        "future_kernel_native_arg_slot_consumer_row_count": active_rows,
        "future_kernel_native_arg_slot_consumer_row_ok_count": active_rows,
        "future_kernel_native_arg_slot_consumer_error_count": 0,
        "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
        "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
        "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": mirror_field,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": active_rows,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": active_rows,
        "future_kernel_native_dispatch_consumer_checked": True,
        "future_kernel_native_dispatch_consumer_grid_x": expected_program_count,
        "future_kernel_native_dispatch_consumer_block_x": int(block_threads),
        "future_kernel_native_dispatch_consumer_row_offset": int(dispatch_row_offset),
        "future_kernel_native_dispatch_consumer_row_limit": int(dispatch_row_limit),
        "future_kernel_native_dispatch_consumer_active_rows": active_rows,
        "future_kernel_native_dispatch_consumer_row_count": active_rows,
        "future_kernel_native_dispatch_consumer_row_ok_count": active_rows,
        "future_kernel_native_dispatch_consumer_rows_per_program": int(block_threads),
        "future_kernel_native_dispatch_consumer_program_count": expected_program_count,
        "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
        "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
        "future_kernel_native_dispatch_ptr_consumer_checked": True,
        "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
        "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
        "future_kernel_native_dispatch_ptr_consumer_row_count": active_rows,
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count": active_rows,
        "future_kernel_native_arg_slot_consumer_slot_visible": True,
        "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible": True,
        "future_kernel_native_arg_slot_consumer_dispatch_packet_visible": True,
        "future_kernel_native_arg_slot_consumer_packet_chain_depth": 3,
        "future_kernel_native_consumer_view_checked": True,
        "future_kernel_native_consumer_view_source_packet_chain_depth": 3,
        "future_kernel_native_consumer_view_row_count": active_rows,
        "future_kernel_native_consumer_view_row_ok_count": active_rows,
        "future_kernel_native_consumer_view_error_count": 0,
        "future_kernel_native_consumer_view_row_offset": int(dispatch_row_offset),
        "future_kernel_native_consumer_view_row_limit": int(dispatch_row_limit),
        "future_kernel_native_consumer_view_rows_per_program": int(block_threads),
        "future_kernel_native_consumer_view_payload_bytes": 0,
        "future_kernel_native_consumer_view_passed_to_kernel": False,
        "future_kernel_native_consumer_view_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_view_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_consumer_program_view_checked": True,
        "future_kernel_native_consumer_program_view_source": (
            "premap_future_kernel_native_consumer_view_abi_v1"
        ),
        "future_kernel_native_consumer_program_view_row_count": active_rows,
        "future_kernel_native_consumer_program_view_row_ok_count": active_rows,
        "future_kernel_native_consumer_program_view_error_count": 0,
        "future_kernel_native_consumer_program_view_program_count": expected_program_count,
        "future_kernel_native_consumer_program_view_full_program_count": (
            expected_full_program_count
        ),
        "future_kernel_native_consumer_program_view_last_program_active_rows": (
            expected_last_program_active_rows
        ),
        "future_kernel_native_consumer_program_view_inactive_lane_count": (
            expected_inactive_lane_count
        ),
        "future_kernel_native_consumer_program_view_first_program_row_offset": (
            expected_first_program_row_offset
        ),
        "future_kernel_native_consumer_program_view_last_program_row_offset": (
            expected_last_program_row_offset
        ),
        "future_kernel_native_consumer_program_view_row_assignment_formula": (
            "program_id * rows_per_program + lane_id + row_offset"
        ),
        "future_kernel_native_consumer_program_view_payload_bytes": 0,
        "future_kernel_native_consumer_program_view_passed_to_kernel": False,
        "future_kernel_native_consumer_program_view_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_program_view_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_consumer_program_view_ptr_checked": True,
        "future_kernel_native_consumer_program_view_ptr_source": (
            "premap_future_kernel_native_consumer_program_view_abi_v1"
        ),
        "future_kernel_native_consumer_program_view_ptr_row_count": active_rows,
        "future_kernel_native_consumer_program_view_ptr_row_ok_count": active_rows,
        "future_kernel_native_consumer_program_view_ptr_error_count": 0,
        "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
        "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
        "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_consumer_kernel_arg_packet_checked": True,
        "future_kernel_native_consumer_kernel_arg_packet_source": (
            "premap_future_kernel_native_consumer_program_view_ptr_abi_v1"
        ),
        "future_kernel_native_consumer_kernel_arg_packet_row_count": active_rows,
        "future_kernel_native_consumer_kernel_arg_packet_row_ok_count": active_rows,
        "future_kernel_native_consumer_kernel_arg_packet_error_count": 0,
        "future_kernel_native_consumer_kernel_arg_packet_payload_bytes": 0,
        "future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel": False,
        "future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation": False,
    }
    for key, expected in expected_scalars.items():
        if stub.get(key) != expected:
            failures.append(f"{key}_mismatch:{stub.get(key)!r}!={expected!r}")
    macros = stub.get("requested_macros")
    if macros != arg_slot_macros(mirror_field):
        failures.append("requested_macros_mismatch")
    projection_values: list[int] = []
    for prefix in _HANDLE_PROJECTION_HASH_PREFIXES:
        key = f"{prefix}_handle_projection_hash_accumulator"
        value = _parse_hex64(stub.get(key))
        if value is None:
            failures.append(f"{key}_missing")
        else:
            projection_values.append(value)
    if len(projection_values) != len(_HANDLE_PROJECTION_HASH_PREFIXES) or len(
        set(projection_values)
    ) != 1:
        failures.append("handle_projection_hash_accumulator_mismatch")
    dispatch_iteration_hash = stub.get(
        "future_kernel_native_dispatch_consumer_program_iteration_hash"
    )
    program_view_iteration_hash = stub.get(
        "future_kernel_native_consumer_program_view_program_iteration_hash"
    )
    if (
        not isinstance(dispatch_iteration_hash, str)
        or not dispatch_iteration_hash
        or dispatch_iteration_hash != program_view_iteration_hash
    ):
        failures.append("consumer_program_view_iteration_hash_mismatch")
    failures.extend(_check_future_field_masks(stub))
    failures.extend(_check_arg_slot_field_reads(stub, active_rows=active_rows))
    failures.extend(_check_consumer_view_field_reads(stub, active_rows=active_rows))
    failures.extend(
        _check_kernel_arg_packet_field_reads(stub, active_rows=active_rows)
    )
    failures.extend(_check_kernel_entry_summary(stub, active_rows=active_rows))
    failures.extend(_check_kernel_entry_args(stub, active_rows=active_rows))
    return failures


def _handle_projection_hash_values(stub: dict[str, Any]) -> tuple[int | None, ...]:
    return tuple(
        _parse_hex64(stub.get(f"{prefix}_handle_projection_hash_accumulator"))
        for prefix in _HANDLE_PROJECTION_HASH_PREFIXES
    )


def _handle_projection_hashchain_equal(stub: dict[str, Any]) -> bool:
    values = _handle_projection_hash_values(stub)
    return all(value is not None for value in values) and len(set(values)) == 1


def _stub_namespace(args: argparse.Namespace, *, input_json: Path) -> SimpleNamespace:
    # Bounds are validated after the merged input is materialized; this namespace
    # is filled in run_canary once the row count is known.
    return SimpleNamespace(
        macro=arg_slot_macros(args.mirror_field),
        offload_arch=args.offload_arch,
        force_build=bool(args.force_build),
        rows=0,
        input_json=input_json,
        dispatch_row_offset=int(args._resolved_dispatch_row_offset),
        dispatch_row_limit=int(args._resolved_dispatch_row_limit),
        block_threads=int(args.block_threads),
        device=int(args.device),
        omit_aux_pointer=False,
        hip_visible_devices=args.hip_visible_devices,
    )


def run_canary(args: argparse.Namespace) -> dict[str, Any]:
    input_paths: list[Path] = []
    if args.runner_json is not None:
        input_paths.extend(input_paths_from_runner_artifact(_resolve(args.runner_json)))
    input_paths.extend(_resolve(path) for path in (args.input_json or []))
    if len(input_paths) < int(args.min_source_count):
        raise ValueError(
            f"need at least {args.min_source_count} online input JSONs; "
            f"got {len(input_paths)}"
        )

    merged_output_json = _resolve(args.merged_output_json)
    stub_output_json = _resolve(args.stub_output_json)
    report_json = _resolve(args.output_json)
    merged_input = materialize_merged_input(
        input_paths,
        max_inputs=int(args.max_inputs) if args.max_inputs else None,
        min_total_rows=int(args.min_total_rows),
        block_threads=int(args.block_threads),
    )
    source_count = int(merged_input["_merge_context"]["source_count"])
    if source_count < int(args.min_source_count):
        raise ValueError(
            f"selected source_count {source_count} is below required "
            f"{args.min_source_count}"
        )
    _write_json(merged_output_json, merged_input)
    row_count = int(merged_input["_meta"]["row_count"])
    dispatch_row_offset, dispatch_row_limit = _dispatch_bounds(
        row_count=row_count,
        dispatch_row_offset=int(args.dispatch_row_offset),
        dispatch_row_limit=(
            int(args.dispatch_row_limit)
            if args.dispatch_row_limit is not None
            else None
        ),
        tail_window_size=(
            int(args.tail_window_size) if args.tail_window_size is not None else None
        ),
    )
    args._resolved_dispatch_row_offset = dispatch_row_offset
    args._resolved_dispatch_row_limit = dispatch_row_limit
    active_rows = dispatch_row_limit - dispatch_row_offset

    if args.dry_run:
        program_count = _program_count(active_rows, int(args.block_threads))
        full_program_count = int(active_rows) // int(args.block_threads)
        previous_program_lanes = max(0, int(program_count) - 1) * int(
            args.block_threads
        )
        last_program_active_rows = int(active_rows) - previous_program_lanes
        inactive_lane_count = int(program_count) * int(args.block_threads) - int(
            active_rows
        )
        last_program_row_offset = int(dispatch_row_offset) + previous_program_lanes
        stub_payload: dict[str, Any] = {
            "passed": True,
            "ok": True,
            "dry_run": True,
            "row_count": row_count,
            "row_ok_count": row_count,
            "error_count": 0,
            "input_json": str(merged_output_json),
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "requested_macros": arg_slot_macros(args.mirror_field),
            "mirror_field": args.mirror_field,
            **_future_field_mask_expectations(),
            "future_kernel_native_arg_slot_consumer_checked": True,
            "future_kernel_native_arg_slot_consumer_row_count": active_rows,
            "future_kernel_native_arg_slot_consumer_row_ok_count": active_rows,
            "future_kernel_native_arg_slot_consumer_error_count": 0,
            "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
            "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
            "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": args.mirror_field,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator": "dry",
            "future_kernel_native_arg_slot_consumer_single_field_mirror_kind": (
                "future_kernel_native_arg_slot_single_field_mirror"
            ),
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": active_rows,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": active_rows,
            "future_kernel_native_dispatch_consumer_checked": True,
            "future_kernel_native_dispatch_consumer_grid_x": program_count,
            "future_kernel_native_dispatch_consumer_block_x": int(args.block_threads),
            "future_kernel_native_dispatch_consumer_row_offset": dispatch_row_offset,
            "future_kernel_native_dispatch_consumer_row_limit": dispatch_row_limit,
            "future_kernel_native_dispatch_consumer_active_rows": active_rows,
            "future_kernel_native_dispatch_consumer_row_count": active_rows,
            "future_kernel_native_dispatch_consumer_row_ok_count": active_rows,
            "future_kernel_native_dispatch_consumer_rows_per_program": int(args.block_threads),
            "future_kernel_native_dispatch_consumer_program_count": program_count,
            "future_kernel_native_dispatch_consumer_full_program_count": full_program_count,
            "future_kernel_native_dispatch_consumer_last_program_active_rows": (
                last_program_active_rows
            ),
            "future_kernel_native_dispatch_consumer_inactive_lane_count": (
                inactive_lane_count
            ),
            "future_kernel_native_dispatch_consumer_first_program_row_offset": (
                dispatch_row_offset
            ),
            "future_kernel_native_dispatch_consumer_last_program_row_offset": (
                last_program_row_offset
            ),
            "future_kernel_native_dispatch_consumer_program_iteration_hash": "d",
            "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
            "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
            "future_kernel_native_dispatch_consumer_program_iteration_checked": True,
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": "d",
            "future_kernel_native_dispatch_ptr_consumer_checked": True,
            "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
            "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
            "future_kernel_native_dispatch_ptr_consumer_row_count": active_rows,
            "future_kernel_native_dispatch_ptr_consumer_row_ok_count": active_rows,
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": "d",
            "future_kernel_native_arg_slot_consumer_slot_visible": True,
            "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible": True,
            "future_kernel_native_arg_slot_consumer_dispatch_packet_visible": True,
            "future_kernel_native_arg_slot_consumer_packet_chain_depth": 3,
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": "d",
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count": active_rows,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count": active_rows,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator": "dry",
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count": active_rows,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count": active_rows,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator": "dry",
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count": active_rows,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator": "dry",
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count": active_rows,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_view_checked": True,
            "future_kernel_native_consumer_view_source_packet_chain_depth": 3,
            "future_kernel_native_consumer_view_row_count": active_rows,
            "future_kernel_native_consumer_view_row_ok_count": active_rows,
            "future_kernel_native_consumer_view_error_count": 0,
            "future_kernel_native_consumer_view_row_offset": dispatch_row_offset,
            "future_kernel_native_consumer_view_row_limit": dispatch_row_limit,
            "future_kernel_native_consumer_view_rows_per_program": int(args.block_threads),
            "future_kernel_native_consumer_view_payload_bytes": 0,
            "future_kernel_native_consumer_view_passed_to_kernel": False,
            "future_kernel_native_consumer_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_view_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_view_hash_accumulator": "dry",
            "future_kernel_native_consumer_view_handle_projection_hash_accumulator": "d",
            "future_kernel_native_consumer_view_descriptor_ptr_read_row_count": active_rows,
            "future_kernel_native_consumer_view_descriptor_ptr_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_view_descriptor_ptr_read_error_count": 0,
            "future_kernel_native_consumer_view_descriptor_ptr_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_count": active_rows,
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_error_count": 0,
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_count": active_rows,
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_view_scale_metadata_handle_read_error_count": 0,
            "future_kernel_native_consumer_view_scale_metadata_handle_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_view_aux_metadata_handle_read_row_count": active_rows,
            "future_kernel_native_consumer_view_aux_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_view_aux_metadata_handle_read_error_count": 0,
            "future_kernel_native_consumer_view_aux_metadata_handle_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_program_view_checked": True,
            "future_kernel_native_consumer_program_view_source": (
                "premap_future_kernel_native_consumer_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_row_count": active_rows,
            "future_kernel_native_consumer_program_view_row_ok_count": active_rows,
            "future_kernel_native_consumer_program_view_error_count": 0,
            "future_kernel_native_consumer_program_view_program_count": program_count,
            "future_kernel_native_consumer_program_view_full_program_count": (
                full_program_count
            ),
            "future_kernel_native_consumer_program_view_last_program_active_rows": (
                last_program_active_rows
            ),
            "future_kernel_native_consumer_program_view_inactive_lane_count": (
                inactive_lane_count
            ),
            "future_kernel_native_consumer_program_view_first_program_row_offset": (
                dispatch_row_offset
            ),
            "future_kernel_native_consumer_program_view_last_program_row_offset": (
                last_program_row_offset
            ),
            "future_kernel_native_consumer_program_view_program_iteration_hash": "d",
            "future_kernel_native_consumer_program_view_row_assignment_formula": (
                "program_id * rows_per_program + lane_id + row_offset"
            ),
            "future_kernel_native_consumer_program_view_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_program_view_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation": (
                False
            ),
            "future_kernel_native_consumer_program_view_hash_accumulator": "dry",
            "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator": (
                "d"
            ),
            "future_kernel_native_consumer_program_view_ptr_checked": True,
            "future_kernel_native_consumer_program_view_ptr_source": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_row_count": active_rows,
            "future_kernel_native_consumer_program_view_ptr_row_ok_count": active_rows,
            "future_kernel_native_consumer_program_view_ptr_error_count": 0,
            "future_kernel_native_consumer_program_view_ptr_hash_accumulator": "dry",
            "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": (
                False
            ),
            "future_kernel_native_consumer_kernel_arg_packet_checked": True,
            "future_kernel_native_consumer_kernel_arg_packet_source": (
                "premap_future_kernel_native_consumer_program_view_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_row_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_error_count": 0,
            "future_kernel_native_consumer_kernel_arg_packet_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_error_count": 0,
            "future_kernel_native_consumer_kernel_arg_packet_descriptor_ptr_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_error_count": 0,
            "future_kernel_native_consumer_kernel_arg_packet_packed_weight_descriptor_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_error_count": 0,
            "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_error_count": 0,
            "future_kernel_native_consumer_kernel_arg_packet_aux_metadata_handle_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_arg_packet_payload_bytes": 0,
            "future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel": False,
            "future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation": (
                False
            ),
            "future_kernel_native_consumer_kernel_entry_summary_checked": True,
            "future_kernel_native_consumer_kernel_entry_summary_mode": (
                "readonly_future_kernel_native_consumer_kernel_entry_summary_abi"
            ),
            "future_kernel_native_consumer_kernel_entry_summary_source": (
                "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            ),
            "future_kernel_native_consumer_kernel_entry_summary_field_read_path": (
                "kernel_entry_summary_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_kernel_entry_summary_packet_chain_depth": 4,
            "future_kernel_native_consumer_kernel_entry_summary_packet_valid": 1,
            "future_kernel_native_consumer_kernel_entry_summary_row_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
            "future_kernel_native_consumer_kernel_entry_summary_payload_bytes": 0,
            "future_kernel_native_consumer_kernel_entry_summary_passed_to_kernel": False,
            "future_kernel_native_consumer_kernel_entry_summary_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_kernel_entry_summary_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_kernel_entry_summary_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_entry_args_checked": True,
            "future_kernel_native_consumer_kernel_entry_args_mode": (
                "readonly_future_kernel_native_consumer_kernel_entry_args_abi"
            ),
            "future_kernel_native_consumer_kernel_entry_args_source": (
                "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            ),
            "future_kernel_native_consumer_kernel_entry_args_field_read_path": (
                "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_kernel_entry_args_packet_chain_depth": 5,
            "future_kernel_native_consumer_kernel_entry_args_version": 1,
            "future_kernel_native_consumer_kernel_entry_args_struct_size": 40,
            "future_kernel_native_consumer_kernel_entry_args_struct_align": 8,
            "future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet": 0,
            "future_kernel_native_consumer_kernel_entry_args_offset_summary": 8,
            "future_kernel_native_consumer_kernel_entry_args_offset_abi_version": 16,
            "future_kernel_native_consumer_kernel_entry_args_offset_kernel_arg_packet_struct_size": 20,
            "future_kernel_native_consumer_kernel_entry_args_offset_summary_struct_size": 24,
            "future_kernel_native_consumer_kernel_entry_args_offset_payload_bytes": 28,
            "future_kernel_native_consumer_kernel_entry_args_offset_flags": 32,
            "future_kernel_native_consumer_kernel_entry_args_kernel_arg_packet_struct_size": 32,
            "future_kernel_native_consumer_kernel_entry_args_summary_struct_size": 104,
            "future_kernel_native_consumer_kernel_entry_args_summary_packet_valid": 1,
            "future_kernel_native_consumer_kernel_entry_args_summary_row_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_expert_id_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_address_key_hash_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count": active_rows,
            "future_kernel_native_consumer_kernel_entry_args_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_args_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
            "future_kernel_native_consumer_kernel_entry_args_payload_bytes": 0,
            "future_kernel_native_consumer_kernel_entry_args_passed_to_kernel": False,
            "future_kernel_native_consumer_kernel_entry_args_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_kernel_entry_args_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_kernel_entry_args_summary_row_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_entry_args_summary_field_read_hash_accumulator": "dry",
            "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator": "dry",
        }
    else:
        stub_payload = run_stub(_stub_namespace(args, input_json=merged_output_json))
    stub_payload.setdefault("passed", bool(stub_payload.get("ok", False)))
    stub_payload.setdefault(
        "failures", [] if bool(stub_payload.get("ok", False)) else ["stub_not_ok"]
    )
    _write_json(stub_output_json, stub_payload)

    failures = _validate_stub(
        stub_payload,
        merged_input=merged_input,
        merged_output_json=merged_output_json,
        block_threads=int(args.block_threads),
        dispatch_row_offset=dispatch_row_offset,
        dispatch_row_limit=dispatch_row_limit,
        mirror_field=args.mirror_field,
    )
    report: dict[str, Any] = {
        "passed": not failures,
        "failures": failures,
        "source": "online_merged_future_native_arg_slot_canary_runner",
        "runner_json": str(args.runner_json) if args.runner_json is not None else None,
        "input_jsons": [str(path) for path in input_paths],
        "selected_source_count": source_count,
        "min_source_count": int(args.min_source_count),
        "merged_output_json": str(merged_output_json),
        "stub_output_json": str(stub_output_json),
        "merged_row_count": int(merged_input["_meta"]["row_count"]),
        "merged_expected_program_count": int(
            merged_input["_merge_context"]["expected_program_count"]
        ),
        "dispatch_row_offset": dispatch_row_offset,
        "dispatch_row_limit": dispatch_row_limit,
        "dispatch_active_rows": active_rows,
        "dispatch_expected_program_count": _program_count(
            active_rows, int(args.block_threads)
        ),
        "tail_window_size": args.tail_window_size,
        "mirror_field": args.mirror_field,
        "block_threads": int(args.block_threads),
        "device": int(args.device),
        "hip_visible_devices": args.hip_visible_devices,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_field_names": list(ARG_SLOT_HANDLE_PROJECTION_FIELDS),
        "arg_slot_field_read_field_names": list(ARG_SLOT_FIELD_READ_FIELDS),
        "arg_slot_all_handle_fields_read": not _check_arg_slot_field_reads(
            stub_payload, active_rows=active_rows
        ),
        "consumer_view_field_read_field_names": list(ARG_SLOT_FIELD_READ_FIELDS),
        "consumer_view_all_handle_fields_read": not _check_consumer_view_field_reads(
            stub_payload, active_rows=active_rows
        ),
        "kernel_arg_packet_field_read_field_names": list(ARG_SLOT_FIELD_READ_FIELDS),
        "kernel_arg_packet_all_handle_fields_read": (
            not _check_kernel_arg_packet_field_reads(
                stub_payload, active_rows=active_rows
            )
        ),
        "kernel_entry_summary_checked": (
            stub_payload.get(
                "future_kernel_native_consumer_kernel_entry_summary_checked"
            )
            is True
        ),
        "kernel_entry_summary_packet_valid": stub_payload.get(
            "future_kernel_native_consumer_kernel_entry_summary_packet_valid"
        ),
        "kernel_entry_summary_error_count": stub_payload.get(
            "future_kernel_native_consumer_kernel_entry_summary_error_count"
        ),
        "kernel_entry_summary_all_handle_fields_read": (
            not _check_kernel_entry_summary(stub_payload, active_rows=active_rows)
        ),
        "kernel_entry_args_checked": (
            stub_payload.get(
                "future_kernel_native_consumer_kernel_entry_args_checked"
            )
            is True
        ),
        "kernel_entry_args_error_count": stub_payload.get(
            "future_kernel_native_consumer_kernel_entry_args_summary_error_count"
        ),
        "kernel_entry_args_all_handle_fields_read": (
            not _check_kernel_entry_args(stub_payload, active_rows=active_rows)
        ),
        "consumer_view_source_packet_chain_depth": stub_payload.get(
            "future_kernel_native_consumer_view_source_packet_chain_depth"
        ),
        "handle_projection_hashchain_equal": _handle_projection_hashchain_equal(
            stub_payload
        ),
        "handle_projection_all_handle_fields_checked": (
            _handle_projection_hashchain_equal(stub_payload)
            and set(ARG_SLOT_HANDLE_PROJECTION_FIELDS) == set(MIRROR_FIELD_MACRO)
        ),
        "stub_summary": _summary(stub_payload),
    }
    _write_json(report_json, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-json", type=Path, default=DEFAULT_SOURCE_RUNNER_JSON)
    parser.add_argument("--input-json", type=Path, action="append", default=[])
    parser.add_argument("--max-inputs", type=int, default=32)
    parser.add_argument("--min-source-count", type=int, default=32)
    parser.add_argument("--min-total-rows", type=int, default=257)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--dispatch-row-offset", type=int, default=0)
    parser.add_argument("--dispatch-row-limit", type=int)
    parser.add_argument("--tail-window-size", type=int)
    parser.add_argument(
        "--mirror-field",
        choices=sorted(MIRROR_FIELD_MACRO),
        default="scale_metadata_handle",
        help="single typed handle field mirrored by the future arg-slot canary",
    )
    parser.add_argument("--device", type=int, default=LAB_DEFAULT_GPU_DEVICE)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--merged-output-json", type=Path, default=DEFAULT_MERGED_OUTPUT_JSON)
    parser.add_argument("--stub-output-json", type=Path, default=DEFAULT_STUB_OUTPUT_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_REPORT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_canary(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
