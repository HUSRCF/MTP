from __future__ import annotations

import json
import subprocess
import sys
import hashlib
from pathlib import Path

from scripts.check_premap_lab_preflight_summary import (
    check_premap_lab_preflight_summary,
)


HEX = "a" * 64


def _request_all_field_handoff(
    prefix: str,
    *,
    row_count: int = 1841,
    field_hash: str,
) -> dict[str, object]:
    fields = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    values: dict[str, object] = {
        f"{prefix}_all_field_handoff_checked": True,
        f"{prefix}_all_field_handoff_field_names": fields,
        f"{prefix}_all_field_handoff_source": (
            "native_request_summary_field_read_counts"
        ),
        f"{prefix}_all_field_handoff_row_count": row_count,
        f"{prefix}_all_field_handoff_row_ok_count": row_count,
        f"{prefix}_all_field_handoff_error_count": 0,
        f"{prefix}_all_field_handoff_hash_accumulator": field_hash,
        f"{prefix}_all_field_handoff_payload_bytes": 0,
        f"{prefix}_all_field_handoff_passed_to_kernel": False,
        f"{prefix}_all_field_handoff_changes_kernel_launch_args": False,
        f"{prefix}_all_field_handoff_current_wna16_arg_compatible": False,
        f"{prefix}_all_field_handoff_requires_wna16_arg_reinterpretation": False,
    }
    for field_name in fields:
        values[f"{prefix}_all_field_handoff_{field_name}_row_ok_count"] = row_count
    return values



def _enable_wna16_kernel_side_execution_ready(
    summary: dict[str, object],
    *,
    row_count: int | None = None,
) -> None:
    row_count = row_count or int(
        summary["default_kernel_consumer_wna16_side_variant_row_count"]
    )
    summary.update(
        {
            "default_kernel_consumer_wna16_kernel_side_execution_ready": True,
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
            "default_kernel_consumer_wna16_kernel_side_execution_row_count": row_count,
            "default_kernel_consumer_wna16_kernel_side_execution_row_ok_count": row_count,
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
            "default_kernel_consumer_wna16_kernel_side_execution_hash_accumulator": "1112131415161718",
            "default_kernel_consumer_wna16_kernel_side_execution_handle_projection_hash_accumulator": "2122232425262728",
            "default_kernel_consumer_wna16_kernel_side_execution_descriptor_ptr_read_hash_accumulator": "3132333435363738",
            "default_kernel_consumer_wna16_kernel_side_execution_packed_weight_descriptor_read_hash_accumulator": "4142434445464748",
            "default_kernel_consumer_wna16_kernel_side_execution_scale_metadata_handle_read_hash_accumulator": "5152535455565758",
            "default_kernel_consumer_wna16_kernel_side_execution_aux_metadata_handle_read_hash_accumulator": "6162636465666768",
        }
    )
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        summary[
            f"default_kernel_consumer_wna16_kernel_side_execution_{field}_read_row_ok_count"
        ] = row_count


def _enable_payloadless_chain_ready(
    summary: dict[str, object],
    *,
    row_count: int | None = None,
    source_count: int = 128,
) -> None:
    row_count = row_count or int(
        summary["default_kernel_consumer_wna16_side_variant_row_count"]
    )
    summary.update(
        {
            "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_passed": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_artifact_kind": "future_wna16_kernel_side_typed_consumer_path",
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_name": "premap_future_wna16_kernel_side_typed_consumer_path_v1",
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_mode": "independent_future_wna16_kernel_side_typed_consumer_path",
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_source": "premap_future_wna16_typed_slot_all_four_field_consumer_v1",
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_stage_type": "lab_gate",
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_bench_semantics": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_gate_ready": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_native_executed": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_native_passed": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_independent_path": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_explicit_typed_abi_slot": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_future_kernel_side_checked": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_future_kernel_side_all_fields_read": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_side_checked": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_side_all_fields_read": True,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_source_count": source_count,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_input_json_count": source_count,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_count": row_count,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_sha256": HEX,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_sha256": HEX,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_selected_input_manifest_sha256": HEX,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_path": "outputs/reports/premap_kernel_consumer/future_wna16_kernel_side_typed_consumer_path_v1.json",
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_path_label": "outputs/reports/premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default.json",
            "default_kernel_consumer_future_wna16_all_four_field_consumer_ready": True,
            "default_kernel_consumer_future_wna16_all_four_field_consumer_fields_read": True,
            "default_kernel_consumer_future_wna16_all_four_field_consumer_hashes_valid": True,
            "default_kernel_consumer_future_wna16_all_four_consumer_evidence_passed": True,
            "default_kernel_consumer_future_wna16_all_four_consumer_artifact_kind": "future_wna16_typed_slot_kernel_variant_all_four_field_consumer",
            "default_kernel_consumer_future_wna16_all_four_consumer_stage_type": "lab_gate",
            "default_kernel_consumer_future_wna16_all_four_consumer_bench_semantics": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_native_executed": True,
            "default_kernel_consumer_future_wna16_all_four_consumer_native_passed": True,
            "default_kernel_consumer_future_wna16_all_four_consumer_future_kernel_side_all_fields_read": True,
            "default_kernel_consumer_future_wna16_all_four_consumer_wna16_side_all_fields_read": True,
            "default_kernel_consumer_future_wna16_all_four_consumer_evidence_path": "outputs/reports/premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default.json",
            "default_kernel_consumer_future_wna16_all_four_consumer_evidence_sha256": HEX,
            "default_kernel_consumer_future_wna16_all_four_consumer_source_count": source_count,
            "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_count": source_count,
            "default_kernel_consumer_future_wna16_all_four_consumer_row_count": row_count,
            "default_kernel_consumer_future_wna16_all_four_consumer_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_sha256": HEX,
            "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_manifest_sha256": HEX,
            "default_kernel_consumer_future_wna16_all_four_consumer_post_native_input_manifest_sha256": HEX,
            "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_path_label": "outputs/reports/premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_entry_args_ptr_default.json",
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_path": "outputs/reports/premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_entry_args_ptr_default.json",
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_sha256": HEX,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_passed": True,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_previous_gate_ready": True,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_ready": True,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_source_count": source_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_previous_source_count": source_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_row_count": row_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_count": row_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_fourth_field": "descriptor_ptr",
            "default_kernel_consumer_future_wna16_fourth_field_handoff_native_requested": True,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_native_executed": True,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_native_passed": True,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_bytes": 0,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_expected_payload_bytes": 0,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_deref_allowed": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_kernel_arg_pass_allowed": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_passed_to_kernel": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_changes_kernel_launch_args": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_current_wna16_arg_compatible": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_requires_wna16_arg_reinterpretation": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_passes_current_wna16_args": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_uses_current_wna16_args": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_measures_tpot": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_measures_vllm_latency": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_wna16_benchmark_ready": False,
            "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_hash": "1111222233334444",
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_hash": "5555666677778888",
            "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field_read_hash": "9999aaaabbbbcccc",
            "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field_native_hash": "ddddeeeeffff0000",
            "default_kernel_consumer_future_wna16_all_four_consumer_payload_bytes": 0,
            "default_kernel_consumer_future_wna16_all_four_consumer_payload_deref_allowed": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_kernel_arg_pass_allowed": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_passed_to_kernel": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_changes_kernel_launch_args": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_current_wna16_arg_compatible": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_requires_wna16_arg_reinterpretation": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_measures_tpot": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_measures_vllm_latency": False,
            "default_kernel_consumer_future_wna16_all_four_consumer_wna16_benchmark_ready": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_payload_bytes": 0,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_payload_deref_allowed": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_kernel_arg_pass_allowed": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_passed_to_kernel": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_changes_kernel_launch_args": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_current_wna16_arg_compatible": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_requires_wna16_arg_reinterpretation": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_uses_current_wna16_args": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_measures_tpot": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_measures_vllm_latency": False,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_benchmark_ready": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_evidence_passed": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_ready": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_gate_ready": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_lab_preflight_ready": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_native_ready": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_native_requested": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_native_executed": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_native_passed": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_all_four_ready": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_all_four_fields_read": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_kernel_side_ready": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_kernel_side_hashes_valid": True,
            "default_kernel_consumer_future_wna16_payloadless_execution_source_count": source_count,
            "default_kernel_consumer_future_wna16_payloadless_execution_row_count": row_count,
            "default_kernel_consumer_future_wna16_payloadless_execution_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_payloadless_execution_benchmark_repeat_count": 3,
            "default_kernel_consumer_future_wna16_payloadless_execution_payload_bytes": 0,
            "default_kernel_consumer_future_wna16_payloadless_execution_payload_deref_allowed": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_kernel_arg_pass_allowed": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_passed_to_kernel": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_changes_kernel_launch_args": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_current_wna16_arg_compatible": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_uses_current_wna16_args": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_measures_tpot": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_measures_vllm_latency": False,
            "default_kernel_consumer_future_wna16_payloadless_execution_wna16_benchmark_ready": False,
        }
    )


def _summary() -> dict[str, object]:
    return {
        "passed": True,
        "default_contract_passed": True,
        "default_required_evidence_passed": True,
        "default_optional_evidence_passed": True,
        "default_kernel_consumer_schema_passed": True,
        "default_kernel_consumer_schema_row_field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "default_kernel_consumer_schema_row_metadata_names": [
            "layer_id",
            "expert_id",
            "address_key_hash",
            "row_order_hash",
            "ordered_row_hash",
        ],
        "default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_online_merged_multiprogram_evidence_passed": True,
        "default_kernel_consumer_online_merged_multiprogram_source_count": 32,
        "default_kernel_consumer_online_merged_multiprogram_source_context_count": 32,
        "default_kernel_consumer_online_merged_multiprogram_source_context_matches_source_count": True,
        "default_kernel_consumer_online_merged_multiprogram_source_identity_count": 32,
        "default_kernel_consumer_online_merged_multiprogram_source_identity_coverage": True,
        "default_kernel_consumer_online_merged_multiprogram_source_identity_digest": HEX,
        "default_kernel_consumer_online_merged_multiprogram_row_count": 1841,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset": 0,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit": 1841,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows": 1841,
        "default_kernel_consumer_online_merged_multiprogram_device": 1,
        "default_kernel_consumer_online_merged_multiprogram_hip_visible_devices": None,
        "default_kernel_consumer_online_merged_multiprogram_mirror_field": (
            "scale_metadata_handle"
        ),
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table": True,
        "default_kernel_consumer_online_merged_multiprogram_hashchain_equal": True,
        "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked": True,
        "default_kernel_consumer_online_merged_multiprogram_no_payload": True,
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel": False,
        "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args": False,
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible": False,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_entry_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_ptr_abi": True,
        "default_kernel_consumer_arg_slot_all_handle_fields_read": True,
        "default_kernel_consumer_arg_slot_field_read_field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "default_kernel_consumer_arg_slot_field_read_row_count": 1841,
        "default_kernel_consumer_arg_slot_field_read_row_ok_counts": {
            "descriptor_ptr": 1841,
            "packed_weight_descriptor": 1841,
            "scale_metadata_handle": 1841,
            "aux_metadata_handle": 1841,
        },
        "default_kernel_consumer_arg_slot_field_read_error_counts": {
            "descriptor_ptr": 0,
            "packed_weight_descriptor": 0,
            "scale_metadata_handle": 0,
            "aux_metadata_handle": 0,
        },
        "default_kernel_consumer_arg_slot_field_read_hashes": {
            "descriptor_ptr": "d35c1",
            "packed_weight_descriptor": "d35c2",
            "scale_metadata_handle": "d35c3",
            "aux_metadata_handle": "d35c4",
        },
        "default_kernel_consumer_consumer_view_all_handle_fields_read": True,
        "default_kernel_consumer_consumer_view_field_read_field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "default_kernel_consumer_consumer_view_field_read_row_count": 1841,
        "default_kernel_consumer_consumer_view_field_read_row_ok_counts": {
            "descriptor_ptr": 1841,
            "packed_weight_descriptor": 1841,
            "scale_metadata_handle": 1841,
            "aux_metadata_handle": 1841,
        },
        "default_kernel_consumer_consumer_view_field_read_error_counts": {
            "descriptor_ptr": 0,
            "packed_weight_descriptor": 0,
            "scale_metadata_handle": 0,
            "aux_metadata_handle": 0,
        },
        "default_kernel_consumer_consumer_view_field_read_hashes": {
            "descriptor_ptr": "c0511",
            "packed_weight_descriptor": "c0512",
            "scale_metadata_handle": "c0513",
            "aux_metadata_handle": "c0514",
        },
        "default_kernel_consumer_consumer_view_source_packet_chain_depth": 3,
        "default_kernel_consumer_consumer_view_payload_bytes": 0,
        "default_kernel_consumer_consumer_view_passed_to_kernel": False,
        "default_kernel_consumer_consumer_view_changes_kernel_launch_args": False,
        "default_kernel_consumer_consumer_view_current_wna16_arg_compatible": False,
        "default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_arg_packet_layout_reported": True,
        "default_kernel_consumer_kernel_arg_packet_struct_size": 32,
        "default_kernel_consumer_kernel_arg_packet_offset_program_view_ptr": 0,
        "default_kernel_consumer_kernel_entry_summary_layout_reported": True,
        "default_kernel_consumer_kernel_entry_summary_struct_size": 104,
        "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator": 80,
        "default_kernel_consumer_kernel_entry_args_layout_reported": True,
        "default_kernel_consumer_kernel_entry_args_struct_size": 40,
        "default_kernel_consumer_kernel_entry_args_offset_summary": 8,
        "default_kernel_consumer_kernel_entry_args_checked": True,
        "default_kernel_consumer_kernel_entry_args_field_read_path": (
            "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
        ),
        "default_kernel_consumer_kernel_entry_args_packet_chain_depth": 5,
        "default_kernel_consumer_kernel_entry_args_summary_row_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_row_ok_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count": 1841,
        "default_kernel_consumer_kernel_entry_args_summary_error_count": 0,
        "default_kernel_consumer_kernel_entry_args_summary_field_mask": 15,
        "default_kernel_consumer_kernel_entry_args_summary_row_hash_accumulator": (
            "c4b51a0fa5ba88c4"
        ),
        "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator": (
            "c2e4ae7fa9bc3227"
        ),
        "default_kernel_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator": (
            "1a11b42afa9e8576"
        ),
        "default_kernel_consumer_kernel_entry_args_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_entry_args_payload_bytes": 0,
        "default_kernel_consumer_kernel_entry_args_passed_to_kernel": False,
        "default_kernel_consumer_kernel_entry_args_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_entry_args_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_invocation_checked": True,
        "default_kernel_consumer_kernel_invocation_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_invocation_packet_chain_depth": 11,
        "default_kernel_consumer_kernel_invocation_payload_bytes": 0,
        "default_kernel_consumer_kernel_invocation_passed_to_kernel": False,
        "default_kernel_consumer_kernel_invocation_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_invocation_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_invocation_row_hash_accumulator": (
            "0f0d0c0b0a090807"
        ),
        "default_kernel_consumer_kernel_invocation_field_read_hash_accumulator": (
            "0102030405060708"
        ),
        "default_kernel_consumer_kernel_invocation_row_metadata_hash_accumulator": (
            "1112131415161718"
        ),
        "default_kernel_consumer_kernel_invocation_entry_checked": True,
        "default_kernel_consumer_kernel_invocation_entry_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_invocation_entry_packet_chain_depth": 11,
        "default_kernel_consumer_kernel_invocation_entry_payload_bytes": 0,
        "default_kernel_consumer_kernel_invocation_entry_passed_to_kernel": False,
        "default_kernel_consumer_kernel_invocation_entry_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_invocation_entry_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_invocation_entry_row_hash_accumulator": (
            "2122232425262728"
        ),
        "default_kernel_consumer_kernel_invocation_entry_field_read_hash_accumulator": (
            "3132333435363738"
        ),
        "default_kernel_consumer_kernel_invocation_entry_row_metadata_hash_accumulator": (
            "4142434445464748"
        ),
        "default_kernel_consumer_kernel_endpoint_checked": True,
        "default_kernel_consumer_kernel_endpoint_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_endpoint_packet_chain_depth": 12,
        "default_kernel_consumer_kernel_endpoint_payload_bytes": 0,
        "default_kernel_consumer_kernel_endpoint_passed_to_kernel": False,
        "default_kernel_consumer_kernel_endpoint_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_endpoint_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_endpoint_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_endpoint_row_hash_accumulator": (
            "5152535455565758"
        ),
        "default_kernel_consumer_kernel_endpoint_field_read_hash_accumulator": (
            "6162636465666768"
        ),
        "default_kernel_consumer_kernel_endpoint_row_metadata_hash_accumulator": (
            "7172737475767778"
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_checked": True,
        "default_kernel_consumer_kernel_endpoint_ptr_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_endpoint_ptr_packet_chain_depth": 13,
        "default_kernel_consumer_kernel_endpoint_ptr_payload_bytes": 0,
        "default_kernel_consumer_kernel_endpoint_ptr_passed_to_kernel": False,
        "default_kernel_consumer_kernel_endpoint_ptr_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_endpoint_ptr_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_endpoint_ptr_row_hash_accumulator": (
            "8182838485868788"
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_field_read_hash_accumulator": (
            "9192939495969798"
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_row_metadata_hash_accumulator": (
            "a1a2a3a4a5a6a7a8"
        ),
        "default_kernel_consumer_request_ptr_checked": True,
        "default_kernel_consumer_request_ptr_field_read_path": (
            "request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        "default_kernel_consumer_request_ptr_packet_chain_depth": 4,
        "default_kernel_consumer_request_ptr_summary_row_count": 1841,
        "default_kernel_consumer_request_ptr_summary_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_summary_row_metadata_read_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_summary_error_count": 0,
        "default_kernel_consumer_request_ptr_summary_field_mask": 15,
        "default_kernel_consumer_request_ptr_summary_row_hash_accumulator": (
            "7172737475767778"
        ),
        "default_kernel_consumer_request_ptr_summary_field_read_hash_accumulator": (
            "8182838485868788"
        ),
        "default_kernel_consumer_request_ptr_summary_row_metadata_hash_accumulator": (
            "9192939495969798"
        ),
        "default_kernel_consumer_request_ptr_all_handle_fields_read": True,
        "default_kernel_consumer_request_ptr_payload_bytes": 0,
        "default_kernel_consumer_request_ptr_passed_to_kernel": False,
        "default_kernel_consumer_request_ptr_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_request_ptr_changes_kernel_launch_args": False,
        "default_kernel_consumer_request_ptr_current_wna16_arg_compatible": False,
        "default_kernel_consumer_request_ptr_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_request_ptr_single_field_handoff_checked": True,
        "default_kernel_consumer_request_ptr_single_field_handoff_field_name": (
            "scale_metadata_handle"
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_source": (
            "native_request_summary_field_read_counts"
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_row_count": 1841,
        "default_kernel_consumer_request_ptr_single_field_handoff_row_ok_count": 1841,
        "default_kernel_consumer_request_ptr_single_field_handoff_error_count": 0,
        "default_kernel_consumer_request_ptr_single_field_handoff_hash_accumulator": (
            "8182838485868788"
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_payload_bytes": 0,
        "default_kernel_consumer_request_ptr_single_field_handoff_passed_to_kernel": False,
        "default_kernel_consumer_request_ptr_single_field_handoff_changes_kernel_launch_args": False,
        "default_kernel_consumer_request_ptr_single_field_handoff_current_wna16_arg_compatible": False,
        "default_kernel_consumer_request_ptr_single_field_handoff_requires_wna16_arg_reinterpretation": False,
        **_request_all_field_handoff(
            "default_kernel_consumer_request_ptr",
            field_hash="8182838485868788",
        ),
        "default_kernel_consumer_request_launch_checked": True,
        "default_kernel_consumer_request_launch_field_read_path": (
            "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        "default_kernel_consumer_request_launch_packet_chain_depth": 5,
        "default_kernel_consumer_request_launch_device_ordinal": 1,
        "default_kernel_consumer_request_launch_grid_x": 8,
        "default_kernel_consumer_request_launch_block_x": 256,
        "default_kernel_consumer_request_launch_row_offset": 0,
        "default_kernel_consumer_request_launch_row_limit": 1841,
        "default_kernel_consumer_request_launch_rows_per_program": 256,
        "default_kernel_consumer_request_launch_summary_row_count": 1841,
        "default_kernel_consumer_request_launch_summary_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_summary_row_metadata_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_summary_error_count": 0,
        "default_kernel_consumer_request_launch_summary_field_mask": 15,
        "default_kernel_consumer_request_launch_summary_row_hash_accumulator": (
            "8182838485868788"
        ),
        "default_kernel_consumer_request_launch_summary_field_read_hash_accumulator": (
            "9192939495969798"
        ),
        "default_kernel_consumer_request_launch_summary_row_metadata_hash_accumulator": (
            "a1a2a3a4a5a6a7a8"
        ),
        "default_kernel_consumer_request_launch_all_handle_fields_read": True,
        "default_kernel_consumer_request_launch_payload_bytes": 0,
        "default_kernel_consumer_request_launch_passed_to_kernel": False,
        "default_kernel_consumer_request_launch_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_request_launch_changes_kernel_launch_args": False,
        "default_kernel_consumer_request_launch_current_wna16_arg_compatible": False,
        "default_kernel_consumer_request_launch_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_request_launch_single_field_handoff_checked": True,
        "default_kernel_consumer_request_launch_single_field_handoff_field_name": (
            "scale_metadata_handle"
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_source": (
            "native_request_summary_field_read_counts"
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_row_count": 1841,
        "default_kernel_consumer_request_launch_single_field_handoff_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_single_field_handoff_error_count": 0,
        "default_kernel_consumer_request_launch_single_field_handoff_hash_accumulator": (
            "9192939495969798"
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_payload_bytes": 0,
        "default_kernel_consumer_request_launch_single_field_handoff_passed_to_kernel": False,
        "default_kernel_consumer_request_launch_single_field_handoff_changes_kernel_launch_args": False,
        "default_kernel_consumer_request_launch_single_field_handoff_current_wna16_arg_compatible": False,
        "default_kernel_consumer_request_launch_single_field_handoff_requires_wna16_arg_reinterpretation": False,
        **_request_all_field_handoff(
            "default_kernel_consumer_request_launch",
            field_hash="9192939495969798",
        ),
        "default_kernel_consumer_request_launch_ptr_checked": True,
        "default_kernel_consumer_request_launch_ptr_field_read_path": (
            "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        "default_kernel_consumer_request_launch_ptr_packet_chain_depth": 6,
        "default_kernel_consumer_request_launch_ptr_summary_row_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_descriptor_ptr_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_summary_error_count": 0,
        "default_kernel_consumer_request_launch_ptr_summary_field_mask": 15,
        "default_kernel_consumer_request_launch_ptr_summary_row_hash_accumulator": (
            "b1b2b3b4b5b6b7b8"
        ),
        "default_kernel_consumer_request_launch_ptr_summary_field_read_hash_accumulator": (
            "c1c2c3c4c5c6c7c8"
        ),
        "default_kernel_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator": (
            "d1d2d3d4d5d6d7d8"
        ),
        "default_kernel_consumer_request_launch_ptr_all_handle_fields_read": True,
        "default_kernel_consumer_request_launch_ptr_payload_bytes": 0,
        "default_kernel_consumer_request_launch_ptr_passed_to_kernel": False,
        "default_kernel_consumer_request_launch_ptr_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_request_launch_ptr_changes_kernel_launch_args": False,
        "default_kernel_consumer_request_launch_ptr_current_wna16_arg_compatible": False,
        "default_kernel_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_checked": True,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_field_name": (
            "scale_metadata_handle"
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_source": (
            "native_request_summary_field_read_counts"
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_row_count": 1841,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_row_ok_count": 1841,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_error_count": 0,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_hash_accumulator": (
            "c1c2c3c4c5c6c7c8"
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_payload_bytes": 0,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_passed_to_kernel": False,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_changes_kernel_launch_args": False,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_current_wna16_arg_compatible": False,
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_requires_wna16_arg_reinterpretation": False,
        **_request_all_field_handoff(
            "default_kernel_consumer_request_launch_ptr",
            field_hash="c1c2c3c4c5c6c7c8",
        ),
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count": 0,
        "default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count": 0,
        "prefetch_lab_default_gate_passed": True,
        "prefetch_lab_default_gate_decision_status": "passed",
        "prefetch_lab_default_gate_failures": [],
        "prefetch_lab_default_full_fetch_decision": (
            "blocked_by_ready_time_measured_copy"
        ),
        "prefetch_lab_default_full_fetch_passed": True,
        "prefetch_lab_default_full_fetch_failures": [],
        "prefetch_lab_default_ready_time_report_passed": True,
        "prefetch_lab_default_ready_time_allow_full_fetch": False,
        "prefetch_lab_default_ready_time_decision_reason": (
            "full_fetch_threshold_not_met"
        ),
        "prefetch_lab_default_ready_time_threshold_failures": [
            "used_per_issued_fetch_below_threshold"
        ],
        "prefetch_lab_default_ready_time_demand_hit_rate": 0.9672,
        "prefetch_lab_default_ready_time_ready_late_miss_rate": 0.000036,
        "prefetch_lab_default_ready_time_used_per_issued_fetch": 0.0,
        "prefetch_lab_default_ready_time_issued_fetch_count": 12,
        "prefetch_lab_default_ready_time_used_fetch_count": 0,
        "prefetch_lab_default_metadata_decision": "shadow_only",
        "prefetch_lab_default_metadata_passed": True,
        "prefetch_lab_default_metadata_failures": [],
        "prefetch_lab_default_premap_decision": "lab_enabled_descriptor_prep_only",
        "prefetch_lab_default_premap_passed": True,
        "prefetch_lab_default_premap_failures": [],
        "prefetch_lab_default_premap_positive_count": 4,
        "prefetch_lab_default_premap_recommended_capacity_entries": 12288,
        "prefetch_lab_default_premap_no_eviction_capacity_entries": 12288,
        "default_kernel_consumer_wna16_side_variant_evidence_label": (
            "wna16_side_consumer_variant_execution_128strict_runner_json"
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_path": (
            "outputs/reports/premap_kernel_consumer/"
            "online_merged_wna16_side_consumer_variant_execution_lab_gate_runner.json"
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_sha256": HEX,
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
        "default_kernel_consumer_wna16_side_variant_source_count": 128,
        "default_kernel_consumer_wna16_side_variant_source_context_count": 128,
        "default_kernel_consumer_wna16_side_variant_source_context_matches_source_count": True,
        "default_kernel_consumer_wna16_side_variant_source_identity_count": 128,
        "default_kernel_consumer_wna16_side_variant_source_identity_coverage": True,
        "default_kernel_consumer_wna16_side_variant_source_identity_digest": HEX,
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset": False,
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count": 28,
        "default_kernel_consumer_wna16_side_variant_row_count": 1841,
        "default_kernel_consumer_wna16_side_variant_row_ok_count": 1841,
        "default_kernel_consumer_wna16_side_variant_error_count": 0,
        "default_kernel_consumer_wna16_side_variant_all_handle_fields_read": True,
        "default_kernel_consumer_wna16_side_variant_packet_chain_depth": 16,
        "default_kernel_consumer_wna16_side_variant_payload_bytes": 0,
        "default_kernel_consumer_wna16_side_variant_passed_to_kernel": False,
        "default_kernel_consumer_wna16_side_variant_changes_kernel_launch_args": False,
        "default_kernel_consumer_wna16_side_variant_current_wna16_arg_compatible": False,
        "default_kernel_consumer_wna16_side_variant_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_wna16_side_variant_explicit_typed_abi_slot": True,
        "default_kernel_consumer_wna16_side_variant_reuses_current_wna16_arg_slot": False,
        "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_row_ok_count": 1841,
        "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_row_ok_count": 1841,
        "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_row_ok_count": 1841,
        "default_kernel_consumer_wna16_side_variant_hash_accumulator": (
            "1112131415161718"
        ),
        "default_kernel_consumer_wna16_side_variant_handle_projection_hash_accumulator": (
            "2122232425262728"
        ),
        "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_hash_accumulator": (
            "3132333435363738"
        ),
        "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_hash_accumulator": (
            "4142434445464748"
        ),
        "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_hash_accumulator": (
            "5152535455565758"
        ),
        "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_hash_accumulator": (
            "6162636465666768"
        ),
        "default_kernel_consumer_typed_noop_ready": True,
        "default_kernel_consumer_wna16_benchmark_ready": False,
        "default_kernel_consumer_wna16_side_variant_base_ready": True,
        "default_kernel_consumer_wna16_side_variant_ready": False,
        "default_kernel_consumer_next_runtime_stage": (
            "refresh_wna16_side_variant_source_provenance"
        ),
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
        "default_readonly_gate_sha256": HEX,
        "canary_gate_sha256": HEX,
        "default_kernel_consumer_schema_artifact_sha256": HEX,
        "default_kernel_consumer_dispatch_runner_evidence_sha256": HEX,
        "default_kernel_consumer_dispatch_runner_artifact_evidence_sha256": HEX,
        "default_kernel_consumer_online_merged_multiprogram_evidence_sha256": HEX,
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_sha256": HEX,
        "default_kernel_consumer_arg_slot_standalone_evidence_sha256": HEX,
        "required_evidence": {
            "required_count": 18,
            "present_count": 18,
            "passed_count": 18,
            "evidence": {},
        },
        "optional_evidence": {
            "required_count": 19,
            "present_count": 19,
            "passed_count": 19,
            "evidence": {},
        },
    }


def test_check_premap_lab_preflight_summary_accepts_valid_summary() -> None:
    result = check_premap_lab_preflight_summary(_summary())

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["online_merged_source_count"] == 32
    assert result["online_merged_row_count"] == 1841
    assert result["online_merged_device"] == 1
    assert result["expected_online_merged_device"] == 1
    assert result["online_merged_mirror_field"] == "scale_metadata_handle"


def test_check_premap_lab_preflight_summary_accepts_wna16_side_same_source_gate() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_real_wna16_typed_slot_kernel_variant"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_accepts_wna16_kernel_side_execution_gate() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_wna16_typed_slot_benchmark_harness"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_accepts_payloadless_chain_next_stage() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_rejects_payloadless_chain_flag_without_evidence() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "payloadless_chain_ready_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_ready_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_payloadless_chain_flag_without_typed_path() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary[
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
    ] = False
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "payloadless_chain_ready_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert "wna16_side_variant_next_stage_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payloadless_typed_path_row_mismatch() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary["default_kernel_consumer_future_wna16_payloadless_execution_row_count"] = 1
    summary["default_kernel_consumer_future_wna16_payloadless_execution_row_ok_count"] = 1
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "payloadless_chain_ready_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert "payloadless_typed_path_row_count_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_typed_path_all_four_binding_mismatch() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary[
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_path_label"
    ] = "outputs/reports/premap_kernel_consumer/other_all_four.json"
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "future_kernel_side_typed_path_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert (
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_path_label_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_all_four_payload_open_in_payloadless_chain() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary["default_kernel_consumer_future_wna16_all_four_consumer_payload_bytes"] = 8
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "future_kernel_side_typed_path_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert (
        "default_kernel_consumer_future_wna16_all_four_consumer_payload_bytes_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_all_four_fourth_field_binding_mismatch() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary[
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_sha256"
    ] = "f" * 64
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "future_kernel_side_typed_path_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert (
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_sha256_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_all_four_when_fourth_handoff_payload_open() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    _enable_payloadless_chain_ready(summary)
    summary["default_kernel_consumer_future_wna16_fourth_field_handoff_payload_bytes"] = 8
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "future_kernel_side_typed_path_reported_without_valid_evidence" in result[
        "failures"
    ]
    assert "future_wna16_fourth_field_handoff_not_ready" in result["failures"]
    assert (
        "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_bytes_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_new_stage_without_payloadless_chain() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "wna16_side_variant_next_stage_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_wna16_benchmark_stage_before_launch_mutation_gate() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary[
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible"
    ] = True
    summary[
        "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible"
    ] = True
    summary["default_kernel_consumer_wna16_benchmark_ready"] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "run_wna16_typed_slot_benchmark"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_wna16_benchmark_without_kernel_side_gate() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    summary["default_kernel_consumer_wna16_benchmark_ready"] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "run_wna16_typed_slot_benchmark"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "wna16_benchmark_ready_not_allowed_in_no_mutation_gate" in result[
        "failures"
    ]


def test_check_premap_lab_preflight_summary_rejects_wna16_benchmark_prerequisites_diagnostic_true() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary["default_kernel_consumer_wna16_benchmark_prerequisites_ready"] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_wna16_typed_slot_benchmark_harness"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "wna16_benchmark_prerequisites_ready_not_allowed" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_wna16_benchmark_prerequisites_true_without_same_source() -> None:
    summary = _summary()
    summary["default_kernel_consumer_wna16_benchmark_prerequisites_ready"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "wna16_benchmark_prerequisites_ready_not_allowed" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_wna16_kernel_side_wrong_path_identity() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_wna16_typed_slot_benchmark_harness"
    )
    summary["default_kernel_consumer_wna16_kernel_side_execution_name"] = "wrong"
    summary["default_kernel_consumer_wna16_kernel_side_execution_mode"] = "wrong"
    summary["default_kernel_consumer_wna16_kernel_side_execution_source"] = "wrong"
    summary["default_kernel_consumer_wna16_kernel_side_execution_packet_chain_depth"] = 15

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    for field in ("name", "mode", "source", "packet_chain_depth"):
        assert (
            f"default_kernel_consumer_wna16_kernel_side_execution_{field}_mismatch"
            in result["failures"]
        )


def test_check_premap_lab_preflight_summary_rejects_wna16_kernel_side_open_payload_or_kernel_arg() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    ] = True
    summary[
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
    ] = 0
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    _enable_wna16_kernel_side_execution_ready(summary)
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_wna16_typed_slot_benchmark_harness"
    )
    summary[
        "default_kernel_consumer_wna16_kernel_side_execution_payload_deref_allowed"
    ] = True
    summary[
        "default_kernel_consumer_wna16_kernel_side_execution_kernel_arg_pass_allowed"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_wna16_kernel_side_execution_payload_deref_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_wna16_kernel_side_execution_kernel_arg_pass_allowed_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_wrong_wna16_source_stage() -> None:
    summary = _summary()
    summary["default_kernel_consumer_wna16_side_variant_ready"] = True
    summary["default_kernel_consumer_wna16_benchmark_ready"] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_real_wna16_typed_slot_kernel_variant"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "wna16_side_variant_ready_mismatch" in result["failures"]
    assert "wna16_side_variant_benchmark_ready_mismatch" in result["failures"]
    assert "wna16_side_variant_next_stage_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_accepts_wna16_side_superset_rows() -> None:
    summary = _summary()
    online_rows = summary["default_kernel_consumer_online_merged_multiprogram_row_count"]
    wna16_rows = online_rows + 1577
    summary["default_kernel_consumer_wna16_side_variant_row_count"] = wna16_rows
    summary["default_kernel_consumer_wna16_side_variant_row_ok_count"] = wna16_rows
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        summary[
            f"default_kernel_consumer_wna16_side_variant_{field}_read_row_ok_count"
        ] = wna16_rows

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_rejects_wna16_side_subset_rows() -> None:
    summary = _summary()
    online_rows = summary["default_kernel_consumer_online_merged_multiprogram_row_count"]
    wna16_rows = online_rows - 1
    summary["default_kernel_consumer_wna16_side_variant_row_count"] = wna16_rows
    summary["default_kernel_consumer_wna16_side_variant_row_ok_count"] = wna16_rows
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        summary[
            f"default_kernel_consumer_wna16_side_variant_{field}_read_row_ok_count"
        ] = wna16_rows

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "wna16_side_variant_row_count_below_online_merged" in result["failures"]


def test_check_premap_lab_preflight_summary_accepts_visible_device_zero() -> None:
    summary = _summary()
    summary["default_kernel_consumer_online_merged_multiprogram_device"] = 0

    result = check_premap_lab_preflight_summary(
        summary,
        expected_online_merged_device=0,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["online_merged_device"] == 0
    assert result["expected_online_merged_device"] == 0


def test_check_premap_lab_preflight_summary_accepts_gpu1_visible_device_zero() -> None:
    summary = _summary()
    summary["default_kernel_consumer_online_merged_multiprogram_device"] = 0
    summary[
        "default_kernel_consumer_online_merged_multiprogram_hip_visible_devices"
    ] = "1"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["online_merged_device"] == 0
    assert result["online_merged_hip_visible_devices"] == "1"
    assert result["expected_online_merged_device"] == 1


def test_check_premap_lab_preflight_summary_rejects_missing_sha() -> None:
    summary = _summary()
    summary["default_readonly_gate_sha256"] = "not-a-sha"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "default_readonly_gate_sha256_invalid" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_defer_and_kernel_mutation() -> None:
    summary = _summary()
    summary["strict_default_gate_evidence_deferred_count"] = 1
    summary["default_kernel_consumer_online_merged_multiprogram_passed_to_kernel"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "strict_default_gate_evidence_deferred_count_not_zero" in result["failures"]
    assert (
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_prefetch_gate_failure() -> None:
    summary = _summary()
    summary["prefetch_lab_default_gate_passed"] = False
    summary["prefetch_lab_default_gate_decision_status"] = "failed"
    summary["prefetch_lab_default_gate_failures"] = [
        "full_fetch:ready_time_gate_report_allows_full_fetch"
    ]
    summary["prefetch_lab_default_full_fetch_passed"] = False
    summary["prefetch_lab_default_full_fetch_failures"] = [
        "ready_time_gate_report_allows_full_fetch"
    ]

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "prefetch_lab_default_gate_passed_mismatch" in result["failures"]
    assert "prefetch_lab_default_gate_decision_status_mismatch" in result["failures"]
    assert "prefetch_lab_default_gate_failures_not_empty" in result["failures"]
    assert "prefetch_lab_default_full_fetch_passed_mismatch" in result["failures"]
    assert "prefetch_lab_default_full_fetch_failures_not_empty" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_missing_ready_time_detail() -> None:
    summary = _summary()
    del summary["prefetch_lab_default_ready_time_used_per_issued_fetch"]

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_ready_time_used_per_issued_fetch_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_prefetch_capacity_gap() -> None:
    summary = _summary()
    summary["prefetch_lab_default_premap_recommended_capacity_entries"] = 8192

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_premap_recommended_capacity_entries_below_min"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_accepts_larger_prefetch_capacity() -> None:
    summary = _summary()
    summary["prefetch_lab_default_premap_positive_count"] = 8
    summary["prefetch_lab_default_premap_recommended_capacity_entries"] = 16384
    summary["prefetch_lab_default_premap_no_eviction_capacity_entries"] = 16384

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_rejects_no_eviction_above_recommended() -> None:
    summary = _summary()
    summary["prefetch_lab_default_premap_recommended_capacity_entries"] = 12288
    summary["prefetch_lab_default_premap_no_eviction_capacity_entries"] = 16384

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_premap_no_eviction_capacity_above_recommended"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_arg_slot_field_read_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_arg_slot_all_handle_fields_read"] = False
    summary["default_kernel_consumer_arg_slot_field_read_row_ok_counts"] = {
        "descriptor_ptr": 1841,
        "packed_weight_descriptor": 1841,
        "scale_metadata_handle": 1840,
        "aux_metadata_handle": 1841,
    }
    summary["default_kernel_consumer_arg_slot_field_read_error_counts"] = {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 1,
        "aux_metadata_handle": 0,
    }

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "default_kernel_consumer_arg_slot_all_handle_fields_read_mismatch" in result[
        "failures"
    ]
    assert "arg_slot_scale_metadata_handle_read_row_ok_count_mismatch" in result[
        "failures"
    ]
    assert "arg_slot_scale_metadata_handle_read_error_count_mismatch" in result[
        "failures"
    ]


def test_check_premap_lab_preflight_summary_rejects_consumer_view_field_read_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_consumer_view_all_handle_fields_read"] = False
    summary["default_kernel_consumer_consumer_view_field_read_row_ok_counts"] = {
        "descriptor_ptr": 1841,
        "packed_weight_descriptor": 1841,
        "scale_metadata_handle": 1841,
        "aux_metadata_handle": 1840,
    }
    summary["default_kernel_consumer_consumer_view_field_read_error_counts"] = {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 0,
        "aux_metadata_handle": 1,
    }

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "default_kernel_consumer_consumer_view_all_handle_fields_read_mismatch" in result[
        "failures"
    ]
    assert "consumer_view_aux_metadata_handle_read_row_ok_count_mismatch" in result[
        "failures"
    ]
    assert "consumer_view_aux_metadata_handle_read_error_count_mismatch" in result[
        "failures"
    ]


def test_check_premap_lab_preflight_summary_rejects_arg_slot_runner_boundary() -> None:
    summary = _summary()
    summary["default_kernel_consumer_online_merged_multiprogram_device"] = 0
    summary["default_kernel_consumer_online_merged_multiprogram_mirror_field"] = (
        "packed_weight_descriptor"
    )
    summary[
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table"
    ] = False
    summary[
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "online_merged_device_not_gpu1" in result["failures"]
    assert "online_merged_mirror_field_mismatch" in result["failures"]
    assert (
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_visible_device_mismatch() -> None:
    summary = _summary()
    summary["default_kernel_consumer_online_merged_multiprogram_device"] = 1

    result = check_premap_lab_preflight_summary(
        summary,
        expected_online_merged_device=0,
    )

    assert result["passed"] is False
    assert "online_merged_device_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_kernel_entry_layout_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_kernel_entry_args_struct_size"] = 48
    summary[
        "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator"
    ] = 88

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_kernel_entry_args_struct_size_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_kernel_entry_read_gap() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count"
    ] = 1840
    summary["default_kernel_consumer_kernel_entry_args_summary_error_count"] = 1
    summary["default_kernel_consumer_kernel_entry_args_all_handle_fields_read"] = False

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_kernel_entry_args_all_handle_fields_read_mismatch"
        in result["failures"]
    )
    assert (
        "kernel_entry_args_scale_metadata_handle_read_row_ok_count_mismatch"
        in result["failures"]
    )
    assert "kernel_entry_args_summary_error_count_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_kernel_entry_hash_gap() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator"
    ] = "not-hex"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator_invalid"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_missing_invocation_gate() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_abi"
    ] = False
    summary[
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_entry_abi"
    ] = False
    summary["default_kernel_consumer_kernel_invocation_checked"] = False

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_abi_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_entry_abi_mismatch"
        in result["failures"]
    )
    assert "default_kernel_consumer_kernel_invocation_checked_mismatch" in result[
        "failures"
    ]


def test_check_premap_lab_preflight_summary_rejects_invocation_entry_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_kernel_invocation_entry_all_handle_fields_read"] = (
        False
    )
    summary["default_kernel_consumer_kernel_invocation_entry_packet_chain_depth"] = 10
    summary["default_kernel_consumer_kernel_invocation_entry_payload_bytes"] = 1
    summary["default_kernel_consumer_kernel_invocation_entry_passed_to_kernel"] = True
    summary[
        "default_kernel_consumer_kernel_invocation_entry_field_read_hash_accumulator"
    ] = "not-hex"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_kernel_invocation_entry_all_handle_fields_read_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_kernel_invocation_entry_packet_chain_depth_mismatch"
        in result["failures"]
    )
    assert "default_kernel_consumer_kernel_invocation_entry_payload_bytes_mismatch" in result[
        "failures"
    ]
    assert "default_kernel_consumer_kernel_invocation_entry_passed_to_kernel_mismatch" in result[
        "failures"
    ]
    assert (
        "default_kernel_consumer_kernel_invocation_entry_field_read_hash_accumulator_invalid"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_endpoint_gap() -> None:
    summary = _summary()
    summary[
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_abi"
    ] = False
    summary["default_kernel_consumer_kernel_endpoint_all_handle_fields_read"] = False
    summary["default_kernel_consumer_kernel_endpoint_packet_chain_depth"] = 11
    summary["default_kernel_consumer_kernel_endpoint_payload_bytes"] = 1
    summary["default_kernel_consumer_kernel_endpoint_passed_to_kernel"] = True
    summary["default_kernel_consumer_kernel_endpoint_changes_kernel_launch_args"] = True
    summary[
        "default_kernel_consumer_kernel_endpoint_requires_wna16_arg_reinterpretation"
    ] = True
    summary[
        "default_kernel_consumer_kernel_endpoint_field_read_hash_accumulator"
    ] = "not-hex"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_abi_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_kernel_endpoint_all_handle_fields_read_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_kernel_endpoint_packet_chain_depth_mismatch"
        in result["failures"]
    )
    assert "default_kernel_consumer_kernel_endpoint_payload_bytes_mismatch" in result[
        "failures"
    ]
    assert "default_kernel_consumer_kernel_endpoint_passed_to_kernel_mismatch" in result[
        "failures"
    ]
    assert "default_kernel_consumer_kernel_endpoint_changes_kernel_launch_args_mismatch" in result[
        "failures"
    ]
    assert "default_kernel_consumer_kernel_endpoint_requires_wna16_arg_reinterpretation_mismatch" in result[
        "failures"
    ]
    assert (
        "default_kernel_consumer_kernel_endpoint_field_read_hash_accumulator_invalid"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_request_launch_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_launch_checked"] = False
    summary["default_kernel_consumer_request_launch_packet_chain_depth"] = 4
    summary["default_kernel_consumer_request_launch_row_offset"] = 1
    summary["default_kernel_consumer_request_launch_row_limit"] = 1840
    summary["default_kernel_consumer_request_launch_rows_per_program"] = 128
    summary[
        "default_kernel_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count"
    ] = 1840
    summary["default_kernel_consumer_request_launch_summary_error_count"] = 1
    summary["default_kernel_consumer_request_launch_all_handle_fields_read"] = False
    summary[
        "default_kernel_consumer_request_launch_summary_field_read_hash_accumulator"
    ] = "not-hex"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_launch_checked_mismatch" in result["failures"]
    assert "request_launch_packet_chain_depth_mismatch" in result["failures"]
    assert "request_launch_scale_metadata_handle_read_row_ok_count_mismatch" in result[
        "failures"
    ]
    assert "request_launch_summary_error_count_mismatch" in result["failures"]
    assert "request_launch_all_handle_fields_read_mismatch" in result["failures"]
    assert "request_launch_geometry_row_offset_mismatch" in result["failures"]
    assert "request_launch_geometry_row_limit_mismatch" in result["failures"]
    assert "request_launch_geometry_rows_per_program_mismatch" in result["failures"]
    assert (
        "default_kernel_consumer_request_launch_summary_field_read_hash_accumulator_invalid"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_request_ptr_gap() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_ptr_checked"] = False
    summary["default_kernel_consumer_request_ptr_packet_chain_depth"] = 3
    summary[
        "default_kernel_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count"
    ] = 1840
    summary["default_kernel_consumer_request_ptr_summary_error_count"] = 1
    summary["default_kernel_consumer_request_ptr_all_handle_fields_read"] = False
    summary[
        "default_kernel_consumer_request_ptr_summary_row_hash_accumulator"
    ] = "not-hex"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_ptr_checked_mismatch" in result["failures"]
    assert "request_ptr_packet_chain_depth_mismatch" in result["failures"]
    assert "request_ptr_descriptor_ptr_read_row_ok_count_mismatch" in result[
        "failures"
    ]
    assert "request_ptr_summary_error_count_mismatch" in result["failures"]
    assert "request_ptr_all_handle_fields_read_mismatch" in result["failures"]
    assert (
        "default_kernel_consumer_request_ptr_summary_row_hash_accumulator_invalid"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_request_ptr_boundary() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_ptr_payload_bytes"] = 8
    summary["default_kernel_consumer_request_ptr_passed_to_kernel"] = True
    summary["default_kernel_consumer_request_ptr_kernel_arg_pass_allowed"] = True
    summary["default_kernel_consumer_request_ptr_changes_kernel_launch_args"] = True
    summary[
        "default_kernel_consumer_request_ptr_current_wna16_arg_compatible"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_ptr_payload_bytes_mismatch" in result["failures"]
    assert "request_ptr_passed_to_kernel_mismatch" in result["failures"]
    assert "request_ptr_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert "request_ptr_changes_kernel_launch_args_mismatch" in result["failures"]
    assert "request_ptr_current_wna16_arg_compatible_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_request_launch_boundary() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_launch_payload_bytes"] = 8
    summary["default_kernel_consumer_request_launch_passed_to_kernel"] = True
    summary["default_kernel_consumer_request_launch_kernel_arg_pass_allowed"] = True
    summary[
        "default_kernel_consumer_request_launch_changes_kernel_launch_args"
    ] = True
    summary[
        "default_kernel_consumer_request_launch_requires_wna16_arg_reinterpretation"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_launch_payload_bytes_mismatch" in result["failures"]
    assert "request_launch_passed_to_kernel_mismatch" in result["failures"]
    assert "request_launch_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert "request_launch_changes_kernel_launch_args_mismatch" in result["failures"]
    assert (
        "request_launch_requires_wna16_arg_reinterpretation_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_request_launch_grid_under_cover() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_launch_grid_x"] = 7

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_launch_geometry_under_covers_rows" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_request_launch_grid_overprovision() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_launch_grid_x"] = 9

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_launch_geometry_overprovisioned_grid" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_request_launch_ptr_boundary() -> None:
    summary = _summary()
    summary["default_kernel_consumer_request_launch_ptr_field_read_path"] = "wrong"
    summary["default_kernel_consumer_request_launch_ptr_payload_bytes"] = 8
    summary["default_kernel_consumer_request_launch_ptr_passed_to_kernel"] = True
    summary["default_kernel_consumer_request_launch_ptr_kernel_arg_pass_allowed"] = True
    summary[
        "default_kernel_consumer_request_launch_ptr_changes_kernel_launch_args"
    ] = True
    summary[
        "default_kernel_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "request_launch_ptr_field_read_path_mismatch" in result["failures"]
    assert "request_launch_ptr_payload_bytes_mismatch" in result["failures"]
    assert "request_launch_ptr_passed_to_kernel_mismatch" in result["failures"]
    assert "request_launch_ptr_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert "request_launch_ptr_changes_kernel_launch_args_mismatch" in result[
        "failures"
    ]
    assert (
        "request_launch_ptr_requires_wna16_arg_reinterpretation_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_cli_writes_output(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    output_path = tmp_path / "check.json"
    summary_path.write_text(json.dumps(_summary()) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/check_premap_lab_preflight_summary.py",
            str(summary_path),
            "--output-json",
            str(output_path),
        ],
        check=True,
    )

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["source"] == "premap_lab_preflight_summary_check"
    assert result["checked_preflight_json"] == str(summary_path.resolve())
    assert result["checked_preflight_json_raw"] == str(summary_path)
    assert result["checked_preflight_sha256"] == hashlib.sha256(
        summary_path.read_bytes()
    ).hexdigest()
