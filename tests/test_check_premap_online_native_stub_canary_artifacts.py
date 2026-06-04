from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_online_native_stub_canary_artifacts import (
    _program_iteration_hash,
    check_online_native_stub_canary_artifacts,
    check_standalone_native_stub_artifact,
    main,
)
from scripts.check_premap_kernel_consumer_schema import (
    FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _arg_slot_required_macros(
    field_name: str = "scale_metadata_handle",
    *,
    include_all_handle_macros: bool = True,
) -> dict[str, bool]:
    macros = {
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR": include_all_handle_macros,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR": (
            include_all_handle_macros
        ),
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE": include_all_handle_macros,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE": include_all_handle_macros,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME": True,
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD": False,
    }
    mirror_by_field = {
        "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
        "scale_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
        "packed_weight_descriptor": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
        "aux_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    }
    handle_by_field = {
        "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
        "scale_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
        "packed_weight_descriptor": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
        "aux_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    }
    macros[handle_by_field[field_name]] = True
    macros[mirror_by_field[field_name]] = True
    return macros


def _extra_input_summary(row_count: int = 4) -> dict:
    def stub_summary() -> dict:
        return {
            "passed": True,
            "ok": True,
            "row_count": row_count,
            "row_ok_count": row_count,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "kernel_side_consumer_path_checked": True,
            "kernel_side_consumer_path_name": "premap_kernel_side_typed_consumer_path_v1",
            "kernel_side_consumer_path_row_count": row_count,
            "kernel_side_consumer_path_row_ok_count": row_count,
            "kernel_side_consumer_path_error_count": 0,
            "kernel_side_consumer_path_payload_bytes": 0,
            "kernel_side_consumer_path_passed_to_kernel": False,
            "kernel_side_consumer_path_changes_kernel_launch_args": False,
            "kernel_side_consumer_path_current_wna16_arg_compatible": False,
        }

    def mirror_summary(field_name: str, *, envelope: bool = False) -> dict:
        payload = {
            **stub_summary(),
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": field_name,
            "single_field_mirror_row_count": row_count,
            "single_field_mirror_row_ok_count": row_count,
            "single_field_mirror_error_count": 0,
        }
        if envelope:
            payload.update(
                {
                    "kernel_consumer_envelope_checked": True,
                    "kernel_consumer_envelope_payload_bytes": 0,
                    "kernel_consumer_envelope_passed_to_kernel": False,
                }
            )
        return payload

    def compatible_summary() -> dict:
        payload = {
            **stub_summary(),
            "kernel_side_compatible_consumer_checked": True,
            "kernel_side_compatible_consumer_name": (
                "premap_kernel_side_compatible_consumer_abi_v1"
            ),
            "kernel_side_compatible_consumer_mode": (
                "readonly_kernel_side_compatible_consumer_abi"
            ),
            "kernel_side_compatible_consumer_source": (
                "premap_kernel_side_typed_consumer_launch_envelope_v1"
            ),
            "kernel_side_compatible_consumer_row_count": row_count,
            "kernel_side_compatible_consumer_row_ok_count": row_count,
            "kernel_side_compatible_consumer_error_count": 0,
            "kernel_side_compatible_consumer_payload_bytes": 0,
            "kernel_side_compatible_consumer_passed_to_kernel": False,
            "kernel_side_compatible_consumer_changes_kernel_launch_args": False,
            "kernel_side_compatible_consumer_current_wna16_arg_compatible": False,
        }
        return payload

    def future_args_summary(field_name: str = "scale_metadata_handle") -> dict:
        payload = {
            **stub_summary(),
            "future_kernel_consumer_args_checked": True,
            "future_kernel_consumer_args_name": (
                "premap_future_kernel_side_consumer_args_v1"
            ),
            "future_kernel_consumer_args_mode": (
                "readonly_future_kernel_consumer_args"
            ),
            "future_kernel_consumer_args_source": (
                "premap_kernel_side_typed_consumer_launch_envelope_v1"
            ),
            "future_kernel_consumer_args_row_count": row_count,
            "future_kernel_consumer_args_row_ok_count": row_count,
            "future_kernel_consumer_args_error_count": 0,
            **FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED,
            "future_kernel_consumer_args_payload_bytes": 0,
            "future_kernel_consumer_args_passed_to_kernel": False,
            "future_kernel_consumer_args_changes_kernel_launch_args": False,
            "future_kernel_consumer_args_current_wna16_arg_compatible": False,
            "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
            "future_kernel_consumer_args_field_mask": 15,
            "future_kernel_consumer_args_required_field_mask": 7,
            "future_kernel_consumer_args_single_field_mirror_checked": True,
            "future_kernel_consumer_args_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_consumer_args_single_field_mirror_row_count": row_count,
            "future_kernel_consumer_args_single_field_mirror_row_ok_count": row_count,
            "future_kernel_consumer_args_single_field_mirror_error_count": 0,
        }
        return payload

    def future_args_compatible_path_summary() -> dict:
        return {
            **future_args_summary(),
            "future_kernel_consumer_args_single_field_mirror_checked": False,
            "future_kernel_consumer_args_single_field_mirror_field_name": "none",
            "future_kernel_consumer_args_single_field_mirror_row_count": 0,
            "future_kernel_consumer_args_single_field_mirror_row_ok_count": 0,
            "future_kernel_consumer_args_single_field_mirror_error_count": 0,
            "future_kernel_args_compatible_consumer_path_checked": True,
            "future_kernel_args_compatible_consumer_path_name": (
                "premap_future_kernel_args_compatible_consumer_path_v1"
            ),
            "future_kernel_args_compatible_consumer_path_mode": (
                "readonly_future_kernel_args_to_compatible_consumer_path"
            ),
            "future_kernel_args_compatible_consumer_path_source": (
                "premap_future_kernel_side_consumer_args_v1"
            ),
            "future_kernel_args_compatible_consumer_path_row_count": row_count,
            "future_kernel_args_compatible_consumer_path_row_ok_count": row_count,
            "future_kernel_args_compatible_consumer_path_error_count": 0,
            "future_kernel_args_compatible_consumer_path_payload_bytes": 0,
            "future_kernel_args_compatible_consumer_path_passed_to_kernel": False,
            "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args": False,
            "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible": False,
            "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation": False,
        }

    def future_native_summary(field_name: str = "scale_metadata_handle") -> dict:
        return {
            **stub_summary(),
            "future_kernel_native_consumer_checked": True,
            "future_kernel_native_consumer_abi_name": (
                "premap_future_kernel_native_consumer_abi_v1"
            ),
            "future_kernel_native_consumer_mode": (
                "readonly_future_kernel_native_consumer_abi"
            ),
            "future_kernel_native_consumer_source": (
                "premap_typed_handle_table_soa_fields"
            ),
            **FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_consumer_row_count": row_count,
            "future_kernel_native_consumer_row_ok_count": row_count,
            "future_kernel_native_consumer_error_count": 0,
            "future_kernel_native_consumer_payload_bytes": 0,
            "future_kernel_native_consumer_passed_to_kernel": False,
            "future_kernel_native_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_field_mask": 15,
            "future_kernel_native_consumer_required_field_mask": 7,
            "future_kernel_native_consumer_single_field_mirror_checked": True,
            "future_kernel_native_consumer_single_field_mirror_field_name": field_name,
            "future_kernel_native_consumer_single_field_mirror_row_count": row_count,
            "future_kernel_native_consumer_single_field_mirror_row_ok_count": row_count,
            "future_kernel_native_consumer_single_field_mirror_error_count": 0,
        }

    def future_native_launch_summary(
        field_name: str = "scale_metadata_handle",
    ) -> dict:
        return {
            **stub_summary(),
            "future_kernel_native_consumer_checked": True,
            "future_kernel_native_consumer_row_count": row_count,
            "future_kernel_native_consumer_row_ok_count": row_count,
            "future_kernel_native_consumer_error_count": 0,
            **FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_launch_consumer_checked": True,
            "future_kernel_native_launch_consumer_abi_name": (
                "premap_future_kernel_native_consumer_launch_abi_v1"
            ),
            "future_kernel_native_launch_consumer_mode": (
                "readonly_future_kernel_native_consumer_launch_abi"
            ),
            "future_kernel_native_launch_consumer_source": (
                "premap_future_kernel_native_consumer_abi_v1"
            ),
            "future_kernel_native_launch_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_launch_consumer_row_stride": 1,
            "future_kernel_native_launch_consumer_row_count": row_count,
            "future_kernel_native_launch_consumer_row_ok_count": row_count,
            "future_kernel_native_launch_consumer_error_count": 0,
            "future_kernel_native_launch_consumer_payload_bytes": 0,
            "future_kernel_native_launch_consumer_passed_to_kernel": False,
            "future_kernel_native_launch_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_launch_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_launch_consumer_field_mask": 15,
            "future_kernel_native_launch_consumer_required_field_mask": 7,
            "future_kernel_native_launch_consumer_single_field_mirror_checked": True,
            "future_kernel_native_launch_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_launch_consumer_single_field_mirror_row_count": (
                row_count
            ),
            "future_kernel_native_launch_consumer_single_field_mirror_row_ok_count": (
                row_count
            ),
            "future_kernel_native_launch_consumer_single_field_mirror_error_count": 0,
        }

    def future_native_dispatch_summary(
        field_name: str = "scale_metadata_handle",
    ) -> dict:
        return {
            **future_native_launch_summary(field_name),
            "future_kernel_native_dispatch_consumer_checked": True,
            "future_kernel_native_dispatch_consumer_abi_name": (
                "premap_future_kernel_native_consumer_dispatch_abi_v1"
            ),
            "future_kernel_native_dispatch_consumer_mode": (
                "readonly_future_kernel_native_consumer_dispatch_abi"
            ),
            "future_kernel_native_dispatch_consumer_source": (
                "premap_future_kernel_native_consumer_launch_abi_v1"
            ),
            "future_kernel_native_dispatch_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_dispatch_consumer_grid_x": 1,
            "future_kernel_native_dispatch_consumer_block_x": 256,
            "future_kernel_native_dispatch_consumer_shared_mem_bytes": 0,
            "future_kernel_native_dispatch_consumer_row_offset": 0,
            "future_kernel_native_dispatch_consumer_row_limit": row_count,
            "future_kernel_native_dispatch_consumer_rows_per_program": 256,
            "future_kernel_native_dispatch_consumer_active_rows": row_count,
            "future_kernel_native_dispatch_consumer_launch_threads": 256,
            "future_kernel_native_dispatch_consumer_program_iteration_checked": True,
            "future_kernel_native_dispatch_consumer_row_assignment_formula": (
                "row_offset + program_id * rows_per_program + lane_id"
            ),
            "future_kernel_native_dispatch_consumer_program_count": 1,
            "future_kernel_native_dispatch_consumer_full_program_count": 0,
            "future_kernel_native_dispatch_consumer_last_program_active_rows": (
                row_count
            ),
            "future_kernel_native_dispatch_consumer_inactive_lane_count": (
                256 - row_count
            ),
            "future_kernel_native_dispatch_consumer_first_program_row_offset": 0,
            "future_kernel_native_dispatch_consumer_last_program_row_offset": 0,
            "future_kernel_native_dispatch_consumer_program_iteration_hash": (
                f"{_program_iteration_hash(grid_x=1, block_x=256, row_offset=0, row_limit=row_count, last_program_active_rows=row_count, inactive_lane_count=256 - row_count):x}"
            ),
            "future_kernel_native_dispatch_consumer_launch_geometry_checked": True,
            "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
            "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
            "future_kernel_native_dispatch_consumer_row_count": row_count,
            "future_kernel_native_dispatch_consumer_row_ok_count": row_count,
            "future_kernel_native_dispatch_consumer_error_count": 0,
            "future_kernel_native_dispatch_consumer_hash_accumulator": "abc123",
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_dispatch_consumer_payload_bytes": 0,
            "future_kernel_native_dispatch_consumer_passed_to_kernel": False,
            "future_kernel_native_dispatch_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_dispatch_consumer_field_mask": 15,
            "future_kernel_native_dispatch_consumer_required_field_mask": 7,
            "future_kernel_native_dispatch_consumer_single_field_mirror_checked": True,
            "future_kernel_native_dispatch_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_count": (
                row_count
            ),
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count": (
                row_count
            ),
            "future_kernel_native_dispatch_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_dispatch_consumer_single_field_mirror_hash_accumulator": (
                "def456"
            ),
            "future_kernel_native_dispatch_ptr_consumer_checked": True,
            "future_kernel_native_dispatch_ptr_consumer_abi_name": (
                "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            ),
            "future_kernel_native_dispatch_ptr_consumer_mode": (
                "readonly_future_kernel_native_consumer_dispatch_ptr_abi"
            ),
            "future_kernel_native_dispatch_ptr_consumer_source": (
                "premap_future_kernel_native_consumer_dispatch_abi_v1"
            ),
            "future_kernel_native_dispatch_ptr_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_dispatch_ptr_consumer_row_count": row_count,
            "future_kernel_native_dispatch_ptr_consumer_row_ok_count": row_count,
            "future_kernel_native_dispatch_ptr_consumer_error_count": 0,
            "future_kernel_native_dispatch_ptr_consumer_hash_accumulator": "abc123",
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
            "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
            "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth": 2,
            "future_kernel_native_dispatch_ptr_consumer_payload_bytes": 0,
            "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel": False,
            "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_dispatch_ptr_consumer_field_mask": 15,
            "future_kernel_native_dispatch_ptr_consumer_required_field_mask": 7,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_checked": True,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count": (
                row_count
            ),
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count": (
                row_count
            ),
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_hash_accumulator": (
                "def456"
            ),
            "future_kernel_native_arg_slot_consumer_checked": True,
            "future_kernel_native_arg_slot_consumer_abi_name": (
                "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            ),
            "future_kernel_native_arg_slot_consumer_mode": (
                "readonly_future_kernel_native_consumer_arg_slot_abi"
            ),
            "future_kernel_native_arg_slot_consumer_source": (
                "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            ),
            "future_kernel_native_arg_slot_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_arg_slot_consumer_row_count": row_count,
            "future_kernel_native_arg_slot_consumer_row_ok_count": row_count,
            "future_kernel_native_arg_slot_consumer_error_count": 0,
            "future_kernel_native_arg_slot_consumer_hash_accumulator": "abc123",
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_arg_slot_consumer_slot_visible": True,
            "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible": True,
            "future_kernel_native_arg_slot_consumer_dispatch_packet_visible": True,
            "future_kernel_native_arg_slot_consumer_packet_chain_depth": 3,
            "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
            "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
            "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_arg_slot_consumer_field_mask": 15,
            "future_kernel_native_arg_slot_consumer_required_field_mask": 7,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator": (
                "def456"
            ),
        }

    def future_native_request_ptr_summary() -> dict:
        row_hash = "abc123"
        field_read_hash = "def456"
        row_metadata_hash = "fedcba"
        return {
            **stub_summary(),
            "future_kernel_native_consumer_request_ptr_abi_name": (
                "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_ptr_mode": (
                "readonly_future_kernel_native_consumer_request_ptr_abi"
            ),
            "future_kernel_native_consumer_request_ptr_source": (
                "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            ),
            "future_kernel_native_consumer_request_ptr_field_read_path": (
                "request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_ptr_checked": True,
            "future_kernel_native_consumer_request_ptr_version": 1,
            "future_kernel_native_consumer_request_ptr_packet_chain_depth": 4,
            "future_kernel_native_consumer_request_ptr_pointer_size": 8,
            "future_kernel_native_consumer_request_ptr_request_id": 1,
            "future_kernel_native_consumer_request_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_request_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_ptr_summary_row_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_error_count": 0,
            "future_kernel_native_consumer_request_ptr_summary_field_mask": 15,
            "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count": row_count,
            "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator": row_metadata_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_summary_field_mask": 15,
            "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count": row_count,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }

    return {
        "input_index": 1,
        "input_json": "input1.json",
        "passed": True,
        "failures": [],
        "outputs": {
            "native_stub": {"summary": stub_summary()},
            "native_stub_per_field": {"summary": stub_summary()},
            "native_stub_kernel_envelope_mirror": {
                "summary": mirror_summary("scale_metadata_handle", envelope=True)
            },
            "native_stub_packed_weight_mirror": {
                "summary": mirror_summary("packed_weight_descriptor")
            },
            "native_stub_aux_metadata_mirror": {
                "summary": mirror_summary("aux_metadata_handle")
            },
            "native_stub_descriptor_ptr_mirror": {
                "summary": mirror_summary("descriptor_ptr")
            },
            "native_stub_kernel_side_compatible_consumer_abi": {
                "summary": compatible_summary()
            },
            "native_stub_future_kernel_consumer_args": {
                "summary": future_args_summary()
            },
            "native_stub_future_kernel_args_descriptor_ptr_mirror": {
                "summary": future_args_summary("descriptor_ptr")
            },
            "native_stub_future_kernel_args_packed_weight_mirror": {
                "summary": future_args_summary("packed_weight_descriptor")
            },
            "native_stub_future_kernel_args_aux_metadata_mirror": {
                "summary": future_args_summary("aux_metadata_handle")
            },
            "native_stub_future_kernel_args_compatible_consumer_path": {
                "summary": future_args_compatible_path_summary()
            },
            "native_stub_future_kernel_native_consumer_abi": {
                "summary": future_native_summary()
            },
            "native_stub_future_kernel_native_consumer_descriptor_ptr_mirror": {
                "summary": future_native_summary("descriptor_ptr")
            },
            "native_stub_future_kernel_native_consumer_packed_weight_mirror": {
                "summary": future_native_summary("packed_weight_descriptor")
            },
            "native_stub_future_kernel_native_consumer_aux_metadata_mirror": {
                "summary": future_native_summary("aux_metadata_handle")
            },
            "native_stub_future_kernel_native_consumer_launch_abi": {
                "summary": future_native_launch_summary()
            },
            "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror": {
                "summary": future_native_launch_summary("descriptor_ptr")
            },
            "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror": {
                "summary": future_native_launch_summary("packed_weight_descriptor")
            },
            "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror": {
                "summary": future_native_launch_summary("aux_metadata_handle")
            },
            "native_stub_future_kernel_native_consumer_dispatch_abi": {
                "summary": future_native_dispatch_summary()
            },
            "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror": {
                "summary": future_native_dispatch_summary("descriptor_ptr")
            },
            "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror": {
                "summary": future_native_dispatch_summary("packed_weight_descriptor")
            },
            "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror": {
                "summary": future_native_dispatch_summary("aux_metadata_handle")
            },
            "native_stub_future_kernel_native_consumer_request_ptr_abi": {
                "summary": future_native_request_ptr_summary()
            },
        },
    }


def _payloads(root: Path) -> tuple[Path, Path, Path]:
    runner_path = root / "runner.json"
    preflight_path = root / "preflight.json"
    status_path = root / "status.json"
    stage1 = {
        "passed": True,
        "required_evidence_present_count": 9,
        "required_evidence_passed_count": 9,
        "required_evidence_required_count": 10,
        "optional_evidence_present_count": 1,
        "optional_evidence_passed_count": 1,
        "optional_evidence_required_count": 1,
        "optional_evidence_passed": True,
        "runtime_gate_evidence_deferred_count": 1,
        "strict_default_gate_evidence_deferred_count": 1,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    final = {
        "passed": True,
        "required_evidence_present_count": 10,
        "required_evidence_passed_count": 10,
        "required_evidence_required_count": 10,
        "optional_evidence_present_count": 1,
        "optional_evidence_passed_count": 1,
        "optional_evidence_required_count": 1,
        "optional_evidence_passed": True,
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }

    def future_args_summary(field_name: str = "scale_metadata_handle") -> dict:
        return {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "future_kernel_consumer_args_checked": True,
            "future_kernel_consumer_args_name": (
                "premap_future_kernel_side_consumer_args_v1"
            ),
            "future_kernel_consumer_args_mode": (
                "readonly_future_kernel_consumer_args"
            ),
            "future_kernel_consumer_args_source": (
                "premap_kernel_side_typed_consumer_launch_envelope_v1"
            ),
            "future_kernel_consumer_args_row_count": 4,
            "future_kernel_consumer_args_row_ok_count": 4,
            "future_kernel_consumer_args_error_count": 0,
            **FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED,
            "future_kernel_consumer_args_payload_bytes": 0,
            "future_kernel_consumer_args_passed_to_kernel": False,
            "future_kernel_consumer_args_changes_kernel_launch_args": False,
            "future_kernel_consumer_args_current_wna16_arg_compatible": False,
            "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
            "future_kernel_consumer_args_field_mask": 15,
            "future_kernel_consumer_args_required_field_mask": 7,
            "future_kernel_consumer_args_single_field_mirror_checked": True,
            "future_kernel_consumer_args_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_consumer_args_single_field_mirror_row_count": 4,
            "future_kernel_consumer_args_single_field_mirror_row_ok_count": 4,
            "future_kernel_consumer_args_single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        }

    def future_args_compatible_path_summary() -> dict:
        return {
            **future_args_summary(),
            "future_kernel_consumer_args_single_field_mirror_checked": False,
            "future_kernel_consumer_args_single_field_mirror_field_name": "none",
            "future_kernel_consumer_args_single_field_mirror_row_count": 0,
            "future_kernel_consumer_args_single_field_mirror_row_ok_count": 0,
            "future_kernel_consumer_args_single_field_mirror_error_count": 0,
            "future_kernel_args_compatible_consumer_path_checked": True,
            "future_kernel_args_compatible_consumer_path_name": (
                "premap_future_kernel_args_compatible_consumer_path_v1"
            ),
            "future_kernel_args_compatible_consumer_path_mode": (
                "readonly_future_kernel_args_to_compatible_consumer_path"
            ),
            "future_kernel_args_compatible_consumer_path_source": (
                "premap_future_kernel_side_consumer_args_v1"
            ),
            "future_kernel_args_compatible_consumer_path_row_count": 4,
            "future_kernel_args_compatible_consumer_path_row_ok_count": 4,
            "future_kernel_args_compatible_consumer_path_error_count": 0,
            "future_kernel_args_compatible_consumer_path_payload_bytes": 0,
            "future_kernel_args_compatible_consumer_path_passed_to_kernel": False,
            "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args": False,
            "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible": False,
            "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation": False,
        }

    def future_native_summary(field_name: str = "scale_metadata_handle") -> dict:
        return {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "future_kernel_native_consumer_checked": True,
            "future_kernel_native_consumer_abi_name": (
                "premap_future_kernel_native_consumer_abi_v1"
            ),
            "future_kernel_native_consumer_mode": (
                "readonly_future_kernel_native_consumer_abi"
            ),
            "future_kernel_native_consumer_source": (
                "premap_typed_handle_table_soa_fields"
            ),
            **FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_consumer_row_count": 4,
            "future_kernel_native_consumer_row_ok_count": 4,
            "future_kernel_native_consumer_error_count": 0,
            "future_kernel_native_consumer_payload_bytes": 0,
            "future_kernel_native_consumer_passed_to_kernel": False,
            "future_kernel_native_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_field_mask": 15,
            "future_kernel_native_consumer_required_field_mask": 7,
            "future_kernel_native_consumer_single_field_mirror_checked": True,
            "future_kernel_native_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_consumer_single_field_mirror_row_count": 4,
            "future_kernel_native_consumer_single_field_mirror_row_ok_count": 4,
            "future_kernel_native_consumer_single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        }

    def future_native_launch_summary(
        field_name: str = "scale_metadata_handle",
    ) -> dict:
        return {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "future_kernel_native_consumer_checked": True,
            "future_kernel_native_consumer_row_count": 4,
            "future_kernel_native_consumer_row_ok_count": 4,
            "future_kernel_native_consumer_error_count": 0,
            **FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_launch_consumer_checked": True,
            "future_kernel_native_launch_consumer_abi_name": (
                "premap_future_kernel_native_consumer_launch_abi_v1"
            ),
            "future_kernel_native_launch_consumer_mode": (
                "readonly_future_kernel_native_consumer_launch_abi"
            ),
            "future_kernel_native_launch_consumer_source": (
                "premap_future_kernel_native_consumer_abi_v1"
            ),
            "future_kernel_native_launch_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_launch_consumer_row_stride": 1,
            "future_kernel_native_launch_consumer_row_count": 4,
            "future_kernel_native_launch_consumer_row_ok_count": 4,
            "future_kernel_native_launch_consumer_error_count": 0,
            "future_kernel_native_launch_consumer_payload_bytes": 0,
            "future_kernel_native_launch_consumer_passed_to_kernel": False,
            "future_kernel_native_launch_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_launch_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_launch_consumer_field_mask": 15,
            "future_kernel_native_launch_consumer_required_field_mask": 7,
            "future_kernel_native_launch_consumer_single_field_mirror_checked": True,
            "future_kernel_native_launch_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_launch_consumer_single_field_mirror_row_count": 4,
            "future_kernel_native_launch_consumer_single_field_mirror_row_ok_count": 4,
            "future_kernel_native_launch_consumer_single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        }

    def future_native_dispatch_summary(
        field_name: str = "scale_metadata_handle",
    ) -> dict:
        return {
            **future_native_launch_summary(field_name),
            "future_kernel_native_dispatch_consumer_checked": True,
            "future_kernel_native_dispatch_consumer_abi_name": (
                "premap_future_kernel_native_consumer_dispatch_abi_v1"
            ),
            "future_kernel_native_dispatch_consumer_mode": (
                "readonly_future_kernel_native_consumer_dispatch_abi"
            ),
            "future_kernel_native_dispatch_consumer_source": (
                "premap_future_kernel_native_consumer_launch_abi_v1"
            ),
            "future_kernel_native_dispatch_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_dispatch_consumer_grid_x": 1,
            "future_kernel_native_dispatch_consumer_block_x": 256,
            "future_kernel_native_dispatch_consumer_shared_mem_bytes": 0,
            "future_kernel_native_dispatch_consumer_row_offset": 0,
            "future_kernel_native_dispatch_consumer_row_limit": 4,
            "future_kernel_native_dispatch_consumer_rows_per_program": 256,
            "future_kernel_native_dispatch_consumer_active_rows": 4,
            "future_kernel_native_dispatch_consumer_launch_threads": 256,
            "future_kernel_native_dispatch_consumer_program_iteration_checked": True,
            "future_kernel_native_dispatch_consumer_row_assignment_formula": (
                "row_offset + program_id * rows_per_program + lane_id"
            ),
            "future_kernel_native_dispatch_consumer_program_count": 1,
            "future_kernel_native_dispatch_consumer_full_program_count": 0,
            "future_kernel_native_dispatch_consumer_last_program_active_rows": 4,
            "future_kernel_native_dispatch_consumer_inactive_lane_count": 252,
            "future_kernel_native_dispatch_consumer_first_program_row_offset": 0,
            "future_kernel_native_dispatch_consumer_last_program_row_offset": 0,
            "future_kernel_native_dispatch_consumer_program_iteration_hash": (
                f"{_program_iteration_hash(grid_x=1, block_x=256, row_offset=0, row_limit=4, last_program_active_rows=4, inactive_lane_count=252):x}"
            ),
            "future_kernel_native_dispatch_consumer_launch_geometry_checked": True,
            "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
            "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
            "future_kernel_native_dispatch_consumer_row_count": 4,
            "future_kernel_native_dispatch_consumer_row_ok_count": 4,
            "future_kernel_native_dispatch_consumer_error_count": 0,
            "future_kernel_native_dispatch_consumer_hash_accumulator": "abc123",
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_dispatch_consumer_payload_bytes": 0,
            "future_kernel_native_dispatch_consumer_passed_to_kernel": False,
            "future_kernel_native_dispatch_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_dispatch_consumer_field_mask": 15,
            "future_kernel_native_dispatch_consumer_required_field_mask": 7,
            "future_kernel_native_dispatch_consumer_single_field_mirror_checked": True,
            "future_kernel_native_dispatch_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_count": 4,
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count": 4,
            "future_kernel_native_dispatch_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_dispatch_consumer_single_field_mirror_hash_accumulator": (
                "def456"
            ),
            "future_kernel_native_dispatch_ptr_consumer_checked": True,
            "future_kernel_native_dispatch_ptr_consumer_abi_name": (
                "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            ),
            "future_kernel_native_dispatch_ptr_consumer_mode": (
                "readonly_future_kernel_native_consumer_dispatch_ptr_abi"
            ),
            "future_kernel_native_dispatch_ptr_consumer_source": (
                "premap_future_kernel_native_consumer_dispatch_abi_v1"
            ),
            "future_kernel_native_dispatch_ptr_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_dispatch_ptr_consumer_row_count": 4,
            "future_kernel_native_dispatch_ptr_consumer_row_ok_count": 4,
            "future_kernel_native_dispatch_ptr_consumer_error_count": 0,
            "future_kernel_native_dispatch_ptr_consumer_hash_accumulator": "abc123",
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
            "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
            "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth": 2,
            "future_kernel_native_dispatch_ptr_consumer_payload_bytes": 0,
            "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel": False,
            "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_dispatch_ptr_consumer_field_mask": 15,
            "future_kernel_native_dispatch_ptr_consumer_required_field_mask": 7,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_checked": True,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count": 4,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count": 4,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_hash_accumulator": (
                "def456"
            ),
            "future_kernel_native_arg_slot_consumer_checked": True,
            "future_kernel_native_arg_slot_consumer_abi_name": (
                "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            ),
            "future_kernel_native_arg_slot_consumer_mode": (
                "readonly_future_kernel_native_consumer_arg_slot_abi"
            ),
            "future_kernel_native_arg_slot_consumer_source": (
                "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            ),
            "future_kernel_native_arg_slot_consumer_version": 1,
            **FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
            "future_kernel_native_arg_slot_consumer_row_count": 4,
            "future_kernel_native_arg_slot_consumer_row_ok_count": 4,
            "future_kernel_native_arg_slot_consumer_error_count": 0,
            "future_kernel_native_arg_slot_consumer_hash_accumulator": "abc123",
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_arg_slot_consumer_slot_visible": True,
            "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible": True,
            "future_kernel_native_arg_slot_consumer_dispatch_packet_visible": True,
            "future_kernel_native_arg_slot_consumer_packet_chain_depth": 3,
            "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
            "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
            "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_arg_slot_consumer_field_mask": 15,
            "future_kernel_native_arg_slot_consumer_required_field_mask": 7,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": 4,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": 4,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator": (
                "def456"
            ),
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        }

    def future_native_request_ptr_summary() -> dict[str, object]:
        row_hash = "abc123"
        field_read_hash = "def456"
        row_metadata_hash = "fedcba"
        return {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_ptr_abi_name": (
                "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_ptr_mode": (
                "readonly_future_kernel_native_consumer_request_ptr_abi"
            ),
            "future_kernel_native_consumer_request_ptr_source": (
                "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            ),
            "future_kernel_native_consumer_request_ptr_field_read_path": (
                "request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_ptr_checked": True,
            "future_kernel_native_consumer_request_ptr_version": 1,
            "future_kernel_native_consumer_request_ptr_packet_chain_depth": 4,
            "future_kernel_native_consumer_request_ptr_pointer_size": 8,
            "future_kernel_native_consumer_request_ptr_request_id": 1,
            "future_kernel_native_consumer_request_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_request_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_ptr_summary_row_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_error_count": 0,
            "future_kernel_native_consumer_request_ptr_summary_field_mask": 15,
            "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count": 4,
            "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator": row_metadata_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_summary_field_mask": 15,
            "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }

    runner = {
        "passed": True,
        "failures": [],
        "preflight_output_json": str(preflight_path),
        "preflight_status_output_json": str(status_path),
        "online_prelaunch_input_check_count": 1,
        "online_prelaunch_input_row_counts": [4],
        "online_prelaunch_input_row_count_min": 4,
        "online_prelaunch_input_row_count_max": 4,
        "online_prelaunch_input_row_count_sum": 4,
        "online_prelaunch_input_extra_check_count": 0,
        "online_prelaunch_input_extra_check_passed_count": 0,
        "preflight_status_summary": stage1,
        "final_preflight_status_summary": final,
        "stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "kernel_side_consumer_path_checked": True,
            "kernel_side_consumer_path_name": "premap_kernel_side_typed_consumer_path_v1",
            "kernel_side_consumer_path_row_count": 4,
            "kernel_side_consumer_path_row_ok_count": 4,
            "kernel_side_consumer_path_error_count": 0,
            "kernel_side_consumer_path_payload_bytes": 0,
            "kernel_side_consumer_path_passed_to_kernel": False,
            "kernel_side_consumer_path_changes_kernel_launch_args": False,
            "kernel_side_consumer_path_current_wna16_arg_compatible": False,
        },
        "per_field_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "kernel_envelope_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "kernel_consumer_envelope_checked": True,
            "kernel_consumer_envelope_payload_bytes": 0,
            "kernel_consumer_envelope_passed_to_kernel": False,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "scale_metadata_handle",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "packed_weight_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "packed_weight_descriptor",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "aux_metadata_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "aux_metadata_handle",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "descriptor_ptr_mirror_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": "descriptor_ptr",
            "single_field_mirror_row_count": 4,
            "single_field_mirror_row_ok_count": 4,
            "single_field_mirror_error_count": 0,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "kernel_side_compatible_stub_summary": {
            "passed": True,
            "ok": True,
            "row_count": 4,
            "row_ok_count": 4,
            "error_count": 0,
            "kernel_side_compatible_consumer_checked": True,
            "kernel_side_compatible_consumer_name": (
                "premap_kernel_side_compatible_consumer_abi_v1"
            ),
            "kernel_side_compatible_consumer_mode": (
                "readonly_kernel_side_compatible_consumer_abi"
            ),
            "kernel_side_compatible_consumer_source": (
                "premap_kernel_side_typed_consumer_launch_envelope_v1"
            ),
            "kernel_side_compatible_consumer_row_count": 4,
            "kernel_side_compatible_consumer_row_ok_count": 4,
            "kernel_side_compatible_consumer_error_count": 0,
            "kernel_side_compatible_consumer_payload_bytes": 0,
            "kernel_side_compatible_consumer_passed_to_kernel": False,
            "kernel_side_compatible_consumer_changes_kernel_launch_args": False,
            "kernel_side_compatible_consumer_current_wna16_arg_compatible": False,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "future_kernel_args_stub_summary": future_args_summary(),
        "future_kernel_args_descriptor_ptr_stub_summary": {
            **future_args_summary("descriptor_ptr"),
        },
        "future_kernel_args_packed_weight_stub_summary": {
            **future_args_summary("packed_weight_descriptor"),
        },
        "future_kernel_args_aux_metadata_stub_summary": {
            **future_args_summary("aux_metadata_handle"),
        },
        "future_kernel_args_compatible_path_stub_summary": (
            future_args_compatible_path_summary()
        ),
        "future_kernel_native_consumer_stub_summary": future_native_summary(),
        "future_kernel_native_consumer_descriptor_ptr_stub_summary": (
            future_native_summary("descriptor_ptr")
        ),
        "future_kernel_native_consumer_packed_weight_stub_summary": (
            future_native_summary("packed_weight_descriptor")
        ),
        "future_kernel_native_consumer_aux_metadata_stub_summary": (
            future_native_summary("aux_metadata_handle")
        ),
        "future_kernel_native_consumer_launch_stub_summary": (
            future_native_launch_summary()
        ),
        "future_kernel_native_consumer_launch_descriptor_ptr_stub_summary": (
            future_native_launch_summary("descriptor_ptr")
        ),
        "future_kernel_native_consumer_launch_packed_weight_stub_summary": (
            future_native_launch_summary("packed_weight_descriptor")
        ),
        "future_kernel_native_consumer_launch_aux_metadata_stub_summary": (
            future_native_launch_summary("aux_metadata_handle")
        ),
        "future_kernel_native_consumer_dispatch_stub_summary": (
            future_native_dispatch_summary()
        ),
        "future_kernel_native_consumer_dispatch_arg_slot_stub_summary": (
            future_native_dispatch_summary()
        ),
        "future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary": (
            future_native_dispatch_summary()
        ),
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary": (
            future_native_dispatch_summary("descriptor_ptr")
        ),
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary": (
            future_native_dispatch_summary("packed_weight_descriptor")
        ),
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary": (
            future_native_dispatch_summary("aux_metadata_handle")
        ),
        "future_kernel_native_consumer_request_ptr_stub_summary": (
            future_native_request_ptr_summary()
        ),
    }
    _write_json(runner_path, runner)
    _write_json(
        preflight_path,
        {
            "passed": True,
            "failures": [],
            "runtime_gate_evidence_scan": {"deferred_count": 0},
            "strict_gate_evidence_checks": {
                "default_readonly_gate": {"deferred_count": 0, "rows": []}
            },
        },
    )
    _write_json(
        status_path,
        {
            "passed": True,
            "runtime_gate_evidence_deferred_count": 0,
            "strict_default_gate_evidence_deferred_count": 0,
            "payload_bytes_required": 0,
            "passed_to_kernel_required": False,
            "changes_kernel_launch_args_required": False,
            "required_evidence": {
                "passed": True,
                "present_count": 10,
                "passed_count": 10,
                "required_count": 10,
            },
            "optional_evidence": {
                "passed": True,
                "present_count": 1,
                "passed_count": 1,
                "required_count": 1,
            },
        },
    )
    return runner_path, preflight_path, status_path


def _sync_arg_slot_projection_from_dispatch(runner: dict) -> None:
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    projection_keys = [
        key
        for key in dispatch
        if key.startswith("future_kernel_native_arg_slot_consumer_")
    ]
    projection_keys.extend(
        ["payload_bytes", "passed_to_kernel", "changes_kernel_launch_args"]
    )
    for target_key in (
        "future_kernel_native_consumer_dispatch_arg_slot_stub_summary",
        "future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary",
    ):
        target = runner[target_key]
        for key in projection_keys:
            target[key] = dispatch[key]


def test_check_standalone_native_stub_artifact_accepts_future_arg_slot(
    tmp_path: Path,
):
    payload = _extra_input_summary(row_count=4)["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["summary"]
    payload["compiled_macros"] = _arg_slot_required_macros()
    stub_path = tmp_path / "standalone_stub.json"
    _write_json(stub_path, payload)

    result = check_standalone_native_stub_artifact(
        root=tmp_path,
        stub_json=stub_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["row_count"] == 4
    assert result["row_ok_count"] == 4
    assert result["arg_slot_checked"] is True
    assert result["arg_slot_row_count"] == 4
    assert result["arg_slot_row_ok_count"] == 4
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["current_wna16_arg_compatible"] is False


def test_check_standalone_native_stub_artifact_rejects_missing_required_macro(
    tmp_path: Path,
):
    payload = _extra_input_summary(row_count=4)["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["summary"]
    compiled_macros = _arg_slot_required_macros()
    compiled_macros[
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
    ] = False
    payload["compiled_macros"] = compiled_macros
    stub_path = tmp_path / "standalone_stub.json"
    _write_json(stub_path, payload)

    result = check_standalone_native_stub_artifact(
        root=tmp_path,
        stub_json=stub_path,
    )

    assert result["passed"] is False
    assert (
        "standalone_stub_required_macro_disabled:"
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
    ) in result["failures"]


def test_check_standalone_native_stub_artifact_allows_field_specific_handle_macro(
    tmp_path: Path,
):
    payload = _extra_input_summary(row_count=4)["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror"
    ]["summary"]
    payload["compiled_macros"] = _arg_slot_required_macros(
        "descriptor_ptr",
        include_all_handle_macros=False,
    )
    stub_path = tmp_path / "standalone_stub.json"
    _write_json(stub_path, payload)

    result = check_standalone_native_stub_artifact(
        root=tmp_path,
        stub_json=stub_path,
        expected_field_name="descriptor_ptr",
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["expected_field_name"] == "descriptor_ptr"
    assert result["row_count"] == 4


def test_check_standalone_native_stub_artifact_rejects_top_level_kernel_mutation(
    tmp_path: Path,
):
    payload = _extra_input_summary(row_count=4)["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["summary"]
    payload["compiled_macros"] = _arg_slot_required_macros()
    payload["passed_to_kernel"] = True
    stub_path = tmp_path / "standalone_stub.json"
    _write_json(stub_path, payload)

    result = check_standalone_native_stub_artifact(
        root=tmp_path,
        stub_json=stub_path,
    )

    assert result["passed"] is False
    assert "standalone_stub_passed_to_kernel_not_false" in result["failures"]


def test_check_standalone_native_stub_artifact_cli_writes_json(tmp_path: Path):
    payload = _extra_input_summary(row_count=4)["outputs"][
        "native_stub_future_kernel_native_consumer_dispatch_abi"
    ]["summary"]
    payload["compiled_macros"] = _arg_slot_required_macros()
    stub_path = tmp_path / "standalone_stub.json"
    output_path = tmp_path / "standalone_check.json"
    _write_json(stub_path, payload)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--standalone-stub-json",
            str(stub_path),
            "--output-json",
            str(output_path),
        ]
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["expected_field_name"] == "scale_metadata_handle"
    assert result["arg_slot_row_count"] == 4


def test_check_online_native_stub_canary_artifacts_accepts_consistent_payloads(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["stage1_deferred_count"] == 1
    assert result["final_deferred_count"] == 0
    assert result["status_deferred_count"] == 0
    assert result["require_all_field_mirror_stubs"] is False
    assert result["min_online_inputs"] == 1
    assert result["runner_online_prelaunch_input_check_count"] == 1


def test_check_online_native_stub_canary_artifacts_uses_runner_recorded_paths(
    tmp_path: Path,
):
    runner_path, _preflight_path, _status_path = _payloads(tmp_path)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["preflight_json_source"] == "runner_recorded"
    assert result["status_json_source"] == "runner_recorded"


def test_check_online_native_stub_canary_artifacts_accepts_stage1_extra_optional_defer(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))

    runner["preflight_status_summary"].update(
        {
            "optional_evidence_present_count": 4,
            "optional_evidence_passed_count": 4,
            "optional_evidence_required_count": 10,
            "runtime_gate_evidence_deferred_count": 7,
            "strict_default_gate_evidence_deferred_count": 7,
        }
    )
    runner["final_preflight_status_summary"].update(
        {
            "optional_evidence_present_count": 7,
            "optional_evidence_passed_count": 7,
            "optional_evidence_required_count": 10,
            "runtime_gate_evidence_deferred_count": 3,
            "strict_default_gate_evidence_deferred_count": 3,
        }
    )
    status.update(
        {
            "runtime_gate_evidence_deferred_count": 3,
            "strict_default_gate_evidence_deferred_count": 3,
            "optional_evidence": {
                "passed": True,
                "present_count": 7,
                "passed_count": 7,
                "required_count": 10,
                "evidence": {
                    **{
                        f"present_{idx}": {
                            "present": True,
                            "passed": True,
                            "failure": None,
                        }
                        for idx in range(7)
                    },
                    **{
                        f"deferred_{idx}": {
                            "present": False,
                            "passed": False,
                            "failure": None,
                        }
                        for idx in range(3)
                    },
                },
            },
        }
    )
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["runtime_gate_evidence_scan"] = {"deferred_count": 3}
    preflight["strict_gate_evidence_checks"] = {
        "default_readonly_gate": {
            "deferred_count": 3,
            "rows": [
                {"label": f"deferred_{idx}", "deferred": True}
                for idx in range(3)
            ],
        }
    }
    _write_json(runner_path, runner)
    _write_json(preflight_path, preflight)
    _write_json(status_path, status)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["stage1_deferred_count"] == 7
    assert result["final_deferred_count"] == 3
    assert result["status_deferred_count"] == 3


def test_check_online_native_stub_canary_artifacts_rejects_missing_preflight_scan(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    _write_json(preflight_path, {"passed": True, "failures": []})

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "preflight_runtime_gate_evidence_scan_missing" in result["failures"]
    assert "preflight_strict_gate_evidence_checks_missing" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_missing_preflight_deferred_count(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["runtime_gate_evidence_scan"] = {}
    preflight["strict_gate_evidence_checks"] = {"default_readonly_gate": {"rows": []}}
    _write_json(preflight_path, preflight)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "preflight_runtime_gate_evidence_deferred_count_missing"
        in result["failures"]
    )
    assert (
        "preflight_strict_default_gate_evidence_deferred_count_missing"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_non_list_preflight_rows(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["strict_gate_evidence_checks"] = {
        "default_readonly_gate": {"deferred_count": 0, "rows": {"bad": "shape"}}
    }
    _write_json(preflight_path, preflight)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert result["failures"] == [
        "preflight_strict_default_gate_evidence_rows_missing"
    ]


def test_check_online_native_stub_canary_artifacts_rejects_preflight_deferred_label_count_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["runtime_gate_evidence_scan"] = {"deferred_count": 2}
    preflight["strict_gate_evidence_checks"] = {
        "default_readonly_gate": {
            "deferred_count": 2,
            "rows": [{"label": "deferred_a", "deferred": True}],
        }
    }
    _write_json(preflight_path, preflight)

    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["runtime_gate_evidence_deferred_count"] = 2
    status["strict_default_gate_evidence_deferred_count"] = 2
    status["required_evidence"]["present_count"] = 8
    status["required_evidence"]["passed_count"] = 8
    status["required_evidence"]["evidence"] = {
        **{
            f"present_{idx}": {"present": True, "passed": True, "failure": None}
            for idx in range(8)
        },
        "deferred_a": {"present": False, "passed": False, "failure": None},
        "deferred_b": {"present": False, "passed": False, "failure": None},
    }
    _write_json(status_path, status)

    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["final_preflight_status_summary"].update(
        {
            "required_evidence_present_count": 8,
            "required_evidence_passed_count": 8,
            "runtime_gate_evidence_deferred_count": 2,
            "strict_default_gate_evidence_deferred_count": 2,
        }
    )
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert result["failures"] == [
        "preflight_strict_default_gate_evidence_deferred_labels_count_mismatch"
    ]


def test_check_online_native_stub_canary_artifacts_rejects_preflight_deferred_label_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["runtime_gate_evidence_scan"] = {"deferred_count": 1}
    preflight["strict_gate_evidence_checks"] = {
        "default_readonly_gate": {
            "deferred_count": 1,
            "rows": [{"label": "wrong_label", "deferred": True}],
        }
    }
    _write_json(preflight_path, preflight)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["runtime_gate_evidence_deferred_count"] = 1
    status["strict_default_gate_evidence_deferred_count"] = 1
    status["required_evidence"]["present_count"] = 9
    status["required_evidence"]["passed_count"] = 9
    status["required_evidence"]["evidence"] = {
        **{
            f"present_{idx}": {"present": True, "passed": True, "failure": None}
            for idx in range(9)
        },
        "expected_label": {"present": False, "passed": False, "failure": None},
    }
    _write_json(status_path, status)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["final_preflight_status_summary"].update(
        {
            "required_evidence_present_count": 9,
            "required_evidence_passed_count": 9,
            "runtime_gate_evidence_deferred_count": 1,
            "strict_default_gate_evidence_deferred_count": 1,
        }
    )
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "preflight_strict_default_gate_evidence_deferred_labels_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_requires_all_field_mirrors(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner.pop("aux_metadata_mirror_stub_summary")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        require_all_field_mirror_stubs=True,
    )

    assert result["passed"] is False
    assert result["require_all_field_mirror_stubs"] is True
    assert "runner_aux_metadata_mirror_stub_summary_required" in result["failures"]

    runner, _, _ = _payloads(tmp_path / "future")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_args_aux_metadata_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "future",
        runner_json=runner,
        preflight_json=tmp_path / "future" / "preflight.json",
        status_json=tmp_path / "future" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_args_aux_metadata_stub_summary_required"
        in result["failures"]
    )

    runner, _, _ = _payloads(tmp_path / "native")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_native_consumer_aux_metadata_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "native",
        runner_json=runner,
        preflight_json=tmp_path / "native" / "preflight.json",
        status_json=tmp_path / "native" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_aux_metadata_stub_summary_required"
        in result["failures"]
    )

    runner, _, _ = _payloads(tmp_path / "native_launch")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_native_consumer_launch_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "native_launch",
        runner_json=runner,
        preflight_json=tmp_path / "native_launch" / "preflight.json",
        status_json=tmp_path / "native_launch" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_launch_stub_summary_required"
        in result["failures"]
    )

    runner, _, _ = _payloads(tmp_path / "native_launch_aux")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_native_consumer_launch_aux_metadata_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "native_launch_aux",
        runner_json=runner,
        preflight_json=tmp_path / "native_launch_aux" / "preflight.json",
        status_json=tmp_path / "native_launch_aux" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_launch_aux_metadata_stub_summary_required"
        in result["failures"]
    )

    runner, _, _ = _payloads(tmp_path / "native_dispatch_aux")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_native_consumer_dispatch_aux_metadata_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "native_dispatch_aux",
        runner_json=runner,
        preflight_json=tmp_path / "native_dispatch_aux" / "preflight.json",
        status_json=tmp_path / "native_dispatch_aux" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_summary_required"
        in result["failures"]
    )

    runner, _, _ = _payloads(tmp_path / "native_dispatch_arg_slot")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_native_consumer_dispatch_arg_slot_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "native_dispatch_arg_slot",
        runner_json=runner,
        preflight_json=tmp_path / "native_dispatch_arg_slot" / "preflight.json",
        status_json=tmp_path / "native_dispatch_arg_slot" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_summary_required"
        in result["failures"]
    )

    runner, _, _ = _payloads(tmp_path / "native_dispatch_arg_slot_mirror")
    payload = json.loads(runner.read_text(encoding="utf-8"))
    payload.pop("future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary")
    _write_json(runner, payload)
    result = check_online_native_stub_canary_artifacts(
        root=tmp_path / "native_dispatch_arg_slot_mirror",
        runner_json=runner,
        preflight_json=tmp_path / "native_dispatch_arg_slot_mirror" / "preflight.json",
        status_json=tmp_path / "native_dispatch_arg_slot_mirror" / "status.json",
        require_all_field_mirror_stubs=True,
    )
    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_summary_required"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_requires_min_online_inputs(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["online_prelaunch_input_check_count"] = 2
    runner["online_prelaunch_input_row_counts"] = [4, 6]
    runner["online_prelaunch_input_row_count_min"] = 4
    runner["online_prelaunch_input_row_count_max"] = 6
    runner["online_prelaunch_input_row_count_sum"] = 10
    runner["online_prelaunch_input_extra_check_count"] = 1
    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [_extra_input_summary()]
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )

    assert result["passed"] is True
    assert result["min_online_inputs"] == 2
    assert result["runner_online_prelaunch_input_check_count"] == 2
    assert result["runner_online_prelaunch_input_row_count_min"] == 4
    assert result["runner_online_prelaunch_input_row_count_max"] == 6
    assert result["runner_online_prelaunch_input_row_count_sum"] == 10
    assert result["runner_online_prelaunch_input_row_count_diverse"] is True

    runner["online_prelaunch_input_row_count_max"] = 5
    _write_json(runner_path, runner)
    failed_rows = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )
    assert failed_rows["passed"] is False
    assert (
        "runner_online_prelaunch_input_row_count_max_mismatch"
        in failed_rows["failures"]
    )
    runner["online_prelaunch_input_row_count_max"] = 6

    runner["online_prelaunch_input_row_counts"] = [4, 4]
    runner["online_prelaunch_input_row_count_min"] = 4
    runner["online_prelaunch_input_row_count_max"] = 4
    runner["online_prelaunch_input_row_count_sum"] = 8
    _write_json(runner_path, runner)
    failed_diversity = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )
    assert failed_diversity["passed"] is False
    assert (
        "runner_online_prelaunch_input_row_count_not_diverse"
        in failed_diversity["failures"]
    )
    runner["online_prelaunch_input_row_counts"] = [4, 6]
    runner["online_prelaunch_input_row_count_min"] = 4
    runner["online_prelaunch_input_row_count_max"] = 6
    runner["online_prelaunch_input_row_count_sum"] = 10

    runner["online_prelaunch_input_extra_check_passed_count"] = 0
    _write_json(runner_path, runner)
    failed = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )
    assert failed["passed"] is False
    assert (
        "runner_online_prelaunch_input_extra_check_passed_count_mismatch"
        in failed["failures"]
    )

    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [
        {**_extra_input_summary(), "passed": False}
    ]
    _write_json(runner_path, runner)
    failed_summary = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )
    assert failed_summary["passed"] is False
    assert "runner_extra_input_0001_not_passed" in failed_summary["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_negative_min_online_inputs(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=-1,
    )

    assert result["passed"] is False
    assert "min_online_inputs_invalid" in result["failures"]


def test_check_online_native_stub_canary_artifacts_requires_multi_input_row_counts(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["online_prelaunch_input_check_count"] = 2
    runner["online_prelaunch_input_extra_check_count"] = 1
    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [_extra_input_summary()]
    runner.pop("online_prelaunch_input_row_counts")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )

    assert result["passed"] is False
    assert "runner_online_prelaunch_input_row_counts_missing" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_non_integer_row_counts(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["online_prelaunch_input_check_count"] = 2
    runner["online_prelaunch_input_row_counts"] = [4, "6"]
    runner["online_prelaunch_input_row_count_min"] = 4
    runner["online_prelaunch_input_row_count_max"] = 6
    runner["online_prelaunch_input_row_count_sum"] = 10
    runner["online_prelaunch_input_extra_check_count"] = 1
    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [_extra_input_summary()]
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )

    assert result["passed"] is False
    assert (
        "runner_online_prelaunch_input_row_counts_0001_invalid"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_row_count_min_sum_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["online_prelaunch_input_check_count"] = 2
    runner["online_prelaunch_input_row_counts"] = [4, 6]
    runner["online_prelaunch_input_row_count_min"] = 5
    runner["online_prelaunch_input_row_count_max"] = 6
    runner["online_prelaunch_input_row_count_sum"] = 11
    runner["online_prelaunch_input_extra_check_count"] = 1
    runner["online_prelaunch_input_extra_check_passed_count"] = 1
    runner["extra_online_input_check_summaries"] = [_extra_input_summary()]
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        min_online_inputs=2,
    )

    assert result["passed"] is False
    assert "runner_online_prelaunch_input_row_count_min_mismatch" in result["failures"]
    assert "runner_online_prelaunch_input_row_count_sum_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_stale_status_path(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["preflight_status_output_json"] = str(tmp_path / "old_status.json")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "runner_preflight_status_output_json_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_final_defer(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["runtime_gate_evidence_deferred_count"] = 1
    _write_json(status_path, status)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_final_runtime_gate_evidence_deferred_count_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_cli_writes_json(tmp_path: Path):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    output = tmp_path / "check.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runner-json",
            str(runner_path),
            "--preflight-json",
            str(preflight_path),
            "--status-json",
            str(status_path),
            "--output-json",
            str(output),
            "--require-all-field-mirror-stubs",
            "--min-online-inputs",
            "1",
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["runner_stub_row_count"] == 4
    assert result["runner_per_field_stub_row_count"] == 4
    assert result["runner_kernel_envelope_mirror_stub_row_count"] == 4
    assert result["runner_packed_weight_mirror_stub_row_count"] == 4
    assert result["runner_aux_metadata_mirror_stub_row_count"] == 4
    assert result["runner_descriptor_ptr_mirror_stub_row_count"] == 4
    assert result["runner_kernel_side_compatible_stub_row_count"] == 4
    assert result["runner_future_kernel_args_stub_row_count"] == 4
    assert result["runner_future_kernel_args_descriptor_ptr_stub_row_count"] == 4
    assert result["runner_future_kernel_args_packed_weight_stub_row_count"] == 4
    assert result["runner_future_kernel_args_aux_metadata_stub_row_count"] == 4
    assert result["runner_future_kernel_args_compatible_path_stub_row_count"] == 4
    assert result["runner_future_kernel_native_consumer_stub_row_count"] == 4
    assert (
        result[
            "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_packed_weight_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_aux_metadata_stub_row_count"
        ]
        == 4
    )
    assert result["runner_future_kernel_native_consumer_launch_stub_row_count"] == 4
    assert (
        result[
            "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count"
        ]
        == 4
    )
    assert result["runner_future_kernel_native_consumer_dispatch_stub_row_count"] == 4
    assert (
        result[
            "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_count"
        ]
        == 4
    )
    assert (
        result[
            "runner_future_kernel_native_consumer_dispatch_arg_slot_mirror_stub_row_count"
        ]
        == 4
    )
    assert result["require_all_field_mirror_stubs"] is True
    assert result["min_online_inputs"] == 1
    assert result["runner_online_prelaunch_input_check_count"] == 1


def test_check_online_native_stub_canary_artifacts_rejects_per_field_stub_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["per_field_stub_summary"]["row_ok_count"] = 3
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "runner_per_field_stub_row_ok_count_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_packed_mirror_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["packed_weight_mirror_stub_summary"][
        "single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_packed_weight_mirror_stub_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_aux_mirror_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["aux_metadata_mirror_stub_summary"][
        "single_field_mirror_field_name"
    ] = "packed_weight_descriptor"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_aux_metadata_mirror_stub_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_descriptor_mirror_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["descriptor_ptr_mirror_stub_summary"][
        "single_field_mirror_field_name"
    ] = "aux_metadata_handle"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_descriptor_ptr_mirror_stub_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_future_args_field_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["future_kernel_args_descriptor_ptr_stub_summary"][
        "future_kernel_consumer_args_single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        require_all_field_mirror_stubs=True,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_args_descriptor_ptr_stub_"
        "future_kernel_consumer_args_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_future_native_field_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    runner["future_kernel_native_consumer_descriptor_ptr_stub_summary"][
        "future_kernel_native_consumer_single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
        require_all_field_mirror_stubs=True,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_descriptor_ptr_stub_"
        "future_kernel_native_consumer_single_field_mirror_field_name_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_accepts_dispatch_row_window(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_row_offset"] = 1
    dispatch["future_kernel_native_dispatch_consumer_row_limit"] = 4
    dispatch["future_kernel_native_dispatch_consumer_active_rows"] = 3
    dispatch["future_kernel_native_dispatch_consumer_row_count"] = 3
    dispatch["future_kernel_native_dispatch_consumer_row_ok_count"] = 3
    dispatch[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_count"
    ] = 3
    dispatch[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count"
    ] = 3
    dispatch["future_kernel_native_dispatch_ptr_consumer_row_count"] = 3
    dispatch["future_kernel_native_dispatch_ptr_consumer_row_ok_count"] = 3
    dispatch[
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count"
    ] = 3
    dispatch[
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count"
    ] = 3
    dispatch["future_kernel_native_arg_slot_consumer_row_count"] = 3
    dispatch["future_kernel_native_arg_slot_consumer_row_ok_count"] = 3
    dispatch[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count"
    ] = 3
    dispatch[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count"
    ] = 3
    dispatch["future_kernel_native_dispatch_consumer_last_program_active_rows"] = 3
    dispatch["future_kernel_native_dispatch_consumer_inactive_lane_count"] = 253
    dispatch["future_kernel_native_dispatch_consumer_first_program_row_offset"] = 1
    dispatch["future_kernel_native_dispatch_consumer_last_program_row_offset"] = 1
    dispatch["future_kernel_native_dispatch_consumer_program_iteration_hash"] = (
        f"{_program_iteration_hash(grid_x=1, block_x=256, row_offset=1, row_limit=4, last_program_active_rows=3, inactive_lane_count=253):x}"
    )
    _sync_arg_slot_projection_from_dispatch(runner)
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_online_native_stub_canary_artifacts_accepts_large_rows_tail_dispatch_window(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["row_count"] = 1024
    dispatch["row_ok_count"] = 1024
    dispatch["future_kernel_native_consumer_row_count"] = 1024
    dispatch["future_kernel_native_consumer_row_ok_count"] = 1024
    dispatch["future_kernel_native_launch_consumer_row_count"] = 1024
    dispatch["future_kernel_native_launch_consumer_row_ok_count"] = 1024
    dispatch["future_kernel_native_dispatch_consumer_row_offset"] = 1020
    dispatch["future_kernel_native_dispatch_consumer_row_limit"] = 1024
    dispatch["future_kernel_native_dispatch_consumer_active_rows"] = 4
    dispatch["future_kernel_native_dispatch_consumer_row_count"] = 4
    dispatch["future_kernel_native_dispatch_consumer_row_ok_count"] = 4
    dispatch[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_count"
    ] = 4
    dispatch[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count"
    ] = 4
    dispatch["future_kernel_native_dispatch_ptr_consumer_row_count"] = 4
    dispatch["future_kernel_native_dispatch_ptr_consumer_row_ok_count"] = 4
    dispatch[
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count"
    ] = 4
    dispatch[
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count"
    ] = 4
    dispatch["future_kernel_native_arg_slot_consumer_row_count"] = 4
    dispatch["future_kernel_native_arg_slot_consumer_row_ok_count"] = 4
    dispatch[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count"
    ] = 4
    dispatch[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count"
    ] = 4
    dispatch["future_kernel_native_dispatch_consumer_program_count"] = 1
    dispatch["future_kernel_native_dispatch_consumer_full_program_count"] = 0
    dispatch["future_kernel_native_dispatch_consumer_last_program_active_rows"] = 4
    dispatch["future_kernel_native_dispatch_consumer_inactive_lane_count"] = 252
    dispatch["future_kernel_native_dispatch_consumer_first_program_row_offset"] = 1020
    dispatch["future_kernel_native_dispatch_consumer_last_program_row_offset"] = 1020
    dispatch["future_kernel_native_dispatch_consumer_program_iteration_hash"] = (
        f"{_program_iteration_hash(grid_x=1, block_x=256, row_offset=1020, row_limit=1024, last_program_active_rows=4, inactive_lane_count=252):x}"
    )
    _sync_arg_slot_projection_from_dispatch(runner)
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_online_native_stub_canary_artifacts_accepts_multi_program_dispatch_window(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    for key in (
        "row_count",
        "row_ok_count",
        "future_kernel_native_consumer_row_count",
        "future_kernel_native_consumer_row_ok_count",
        "future_kernel_native_launch_consumer_row_count",
        "future_kernel_native_launch_consumer_row_ok_count",
        "future_kernel_native_dispatch_consumer_row_count",
        "future_kernel_native_dispatch_consumer_row_ok_count",
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_count",
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count",
        "future_kernel_native_dispatch_ptr_consumer_row_count",
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count",
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count",
        "future_kernel_native_arg_slot_consumer_row_count",
        "future_kernel_native_arg_slot_consumer_row_ok_count",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    ):
        dispatch[key] = 520
    dispatch["future_kernel_native_dispatch_consumer_grid_x"] = 3
    dispatch["future_kernel_native_dispatch_consumer_block_x"] = 256
    dispatch["future_kernel_native_dispatch_consumer_row_offset"] = 0
    dispatch["future_kernel_native_dispatch_consumer_row_limit"] = 520
    dispatch["future_kernel_native_dispatch_consumer_rows_per_program"] = 256
    dispatch["future_kernel_native_dispatch_consumer_active_rows"] = 520
    dispatch["future_kernel_native_dispatch_consumer_launch_threads"] = 768
    dispatch["future_kernel_native_dispatch_consumer_program_count"] = 3
    dispatch["future_kernel_native_dispatch_consumer_full_program_count"] = 2
    dispatch["future_kernel_native_dispatch_consumer_last_program_active_rows"] = 8
    dispatch["future_kernel_native_dispatch_consumer_inactive_lane_count"] = 248
    dispatch["future_kernel_native_dispatch_consumer_first_program_row_offset"] = 0
    dispatch["future_kernel_native_dispatch_consumer_last_program_row_offset"] = 512
    dispatch["future_kernel_native_dispatch_consumer_program_iteration_hash"] = (
        f"{_program_iteration_hash(grid_x=3, block_x=256, row_offset=0, row_limit=520, last_program_active_rows=8, inactive_lane_count=248):x}"
    )
    _sync_arg_slot_projection_from_dispatch(runner)
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_online_native_stub_canary_artifacts_accepts_multi_program_offset_window(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    source_rows = 1024
    active_rows = 520
    row_offset = 17
    row_limit = row_offset + active_rows
    grid_x = 3
    block_x = 256
    for key in (
        "row_count",
        "row_ok_count",
        "future_kernel_native_consumer_row_count",
        "future_kernel_native_consumer_row_ok_count",
        "future_kernel_native_launch_consumer_row_count",
        "future_kernel_native_launch_consumer_row_ok_count",
    ):
        dispatch[key] = source_rows
    for key in (
        "future_kernel_native_dispatch_consumer_row_count",
        "future_kernel_native_dispatch_consumer_row_ok_count",
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_count",
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count",
        "future_kernel_native_dispatch_ptr_consumer_row_count",
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count",
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count",
        "future_kernel_native_arg_slot_consumer_row_count",
        "future_kernel_native_arg_slot_consumer_row_ok_count",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    ):
        dispatch[key] = active_rows
    dispatch["future_kernel_native_dispatch_consumer_grid_x"] = grid_x
    dispatch["future_kernel_native_dispatch_consumer_block_x"] = block_x
    dispatch["future_kernel_native_dispatch_consumer_row_offset"] = row_offset
    dispatch["future_kernel_native_dispatch_consumer_row_limit"] = row_limit
    dispatch["future_kernel_native_dispatch_consumer_rows_per_program"] = block_x
    dispatch["future_kernel_native_dispatch_consumer_active_rows"] = active_rows
    dispatch["future_kernel_native_dispatch_consumer_launch_threads"] = (
        grid_x * block_x
    )
    dispatch["future_kernel_native_dispatch_consumer_program_count"] = grid_x
    dispatch["future_kernel_native_dispatch_consumer_full_program_count"] = 2
    dispatch["future_kernel_native_dispatch_consumer_last_program_active_rows"] = 8
    dispatch["future_kernel_native_dispatch_consumer_inactive_lane_count"] = 248
    dispatch["future_kernel_native_dispatch_consumer_first_program_row_offset"] = (
        row_offset
    )
    dispatch["future_kernel_native_dispatch_consumer_last_program_row_offset"] = (
        row_offset + 2 * block_x
    )
    dispatch["future_kernel_native_dispatch_consumer_program_iteration_hash"] = (
        f"{_program_iteration_hash(grid_x=grid_x, block_x=block_x, row_offset=row_offset, row_limit=row_limit, last_program_active_rows=8, inactive_lane_count=248):x}"
    )
    _sync_arg_slot_projection_from_dispatch(runner)
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_active_rows_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_active_rows"] = 3
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_native_dispatch_active_rows_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_program_hash_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_program_iteration_hash"] = "0"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_native_dispatch_program_iteration_hash_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_program_hash_missing(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch.pop("future_kernel_native_dispatch_consumer_program_iteration_hash")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_native_dispatch_program_iteration_hash_missing"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_allows_path_specific_row_hashes(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_hash_accumulator"] = "bad"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_row_hash_missing(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch.pop("future_kernel_native_dispatch_ptr_consumer_hash_accumulator")
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_"
        "hash_accumulator_missing_or_invalid"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_row_hash_invalid(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_hash_accumulator"] = "not_hex"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_"
        "hash_accumulator_missing_or_invalid"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_handle_projection_hash_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch[
        "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator"
    ] = "4820"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_"
        "handle_projection_hash_accumulator_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_consumer_view_handle_projection_hash_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch[
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
    ] = "4820"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_consumer_view_"
        "handle_projection_hash_accumulator_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_handle_projection_hash_invalid(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch[
        "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator"
    ] = "not_hex"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_"
        "handle_projection_hash_accumulator_missing_or_invalid"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_mirror_hash_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator"
    ] = "bad"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_"
        "single_field_mirror_hash_accumulator_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_mirror_hash_invalid(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_hash_accumulator"
    ] = "not_hex"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_"
        "single_field_mirror_hash_accumulator_missing_or_invalid"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_metadata_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_version"] = 2
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_version_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_layout_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_packet_struct_size"] = 40
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert any(
        failure.startswith(
            "runner_future_kernel_native_consumer_dispatch_stub_"
            "future_kernel_native_dispatch_ptr_consumer_packet_struct_size_mismatch"
        )
        for failure in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_safety_flag(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_passed_to_kernel"] = True
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_chain_visibility(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_packet_visible"] = False
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_packet_visible_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_ptr_chain_depth(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_packet_chain_depth"] = 1
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_safety_flag(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_passed_to_kernel"] = True
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_passed_to_kernel_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_chain_visibility(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_dispatch_packet_visible"] = False
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_dispatch_packet_visible_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_chain_depth(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_packet_chain_depth"] = 2
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_packet_chain_depth_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_projection_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    projection = runner["future_kernel_native_consumer_dispatch_arg_slot_stub_summary"]
    projection["future_kernel_native_arg_slot_consumer_row_count"] = 3
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_row_count_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_projection_safety_flag(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    projection = runner["future_kernel_native_consumer_dispatch_arg_slot_stub_summary"]
    projection["future_kernel_native_arg_slot_consumer_passed_to_kernel"] = True
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_arg_slot_stub_"
        "future_kernel_native_arg_slot_consumer_passed_to_kernel_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_layout_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_slot_struct_size"] = 40
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert any(
        failure.startswith(
            "runner_future_kernel_native_consumer_dispatch_stub_"
            "future_kernel_native_arg_slot_consumer_slot_struct_size_mismatch"
        )
        for failure in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_source_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_source"] = "wrong_source"
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_source_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_field_mask_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_field_mask"] = 1
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_required_field_mask_not_covered"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_arg_slot_required_field_mask_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_required_field_mask"] = 1
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_kernel_native_arg_slot_consumer_required_field_mask_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_runtime_deferred_count_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["runtime_gate_evidence_scan"] = {"deferred_count": 0}
    _write_json(preflight_path, preflight)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["runtime_gate_evidence_deferred_count"] = 3
    _write_json(status_path, status)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert "status_runtime_gate_evidence_deferred_count_mismatch" in result["failures"]


def test_check_online_native_stub_canary_artifacts_rejects_strict_deferred_count_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["strict_gate_evidence_checks"] = {
        "default_readonly_gate": {"deferred_count": 0}
    }
    _write_json(preflight_path, preflight)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["strict_default_gate_evidence_deferred_count"] = 3
    _write_json(status_path, status)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "status_strict_default_gate_evidence_deferred_count_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_launch_threads_mismatch(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_launch_threads"] = 128
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_native_dispatch_launch_threads_mismatch"
        in result["failures"]
    )


def test_check_online_native_stub_canary_artifacts_rejects_dispatch_non_minimal_cover(
    tmp_path: Path,
):
    runner_path, preflight_path, status_path = _payloads(tmp_path)
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_grid_x"] = 2
    dispatch["future_kernel_native_dispatch_consumer_launch_threads"] = 512
    _write_json(runner_path, runner)

    result = check_online_native_stub_canary_artifacts(
        root=tmp_path,
        runner_json=runner_path,
        preflight_json=preflight_path,
        status_json=status_path,
    )

    assert result["passed"] is False
    assert (
        "runner_future_kernel_native_consumer_dispatch_stub_"
        "future_native_dispatch_launch_not_minimal_cover"
        in result["failures"]
    )
