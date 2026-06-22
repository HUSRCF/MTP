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
            "default_kernel_consumer_future_wna16_payloadless_execution_evidence_path": "outputs/reports/premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_payloadless_execution_entry_args_ptr_native_v1.json",
            "default_kernel_consumer_future_wna16_payloadless_execution_evidence_sha256": HEX,
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


def _enable_variant_execution_ready(
    summary: dict[str, object],
    *,
    row_count: int | None = None,
    source_count: int = 128,
) -> None:
    row_count = row_count or int(
        summary["default_kernel_consumer_future_wna16_payloadless_execution_row_count"]
    )
    summary.update(
        {
            "default_kernel_consumer_future_wna16_variant_execution_evidence_passed": True,
            "default_kernel_consumer_future_wna16_variant_execution_ready": True,
            "default_kernel_consumer_future_wna16_variant_execution_gate_ready": True,
            "default_kernel_consumer_future_wna16_variant_execution_payloadless_gate_ready": True,
            "default_kernel_consumer_future_wna16_variant_execution_native_requested": True,
            "default_kernel_consumer_future_wna16_variant_execution_native_executed": True,
            "default_kernel_consumer_future_wna16_variant_execution_native_passed": True,
            "default_kernel_consumer_future_wna16_variant_execution_native_artifact_ready": True,
            "default_kernel_consumer_future_wna16_variant_execution_not_current_wna16_kernel": True,
            "default_kernel_consumer_future_wna16_variant_execution_artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
            "default_kernel_consumer_future_wna16_variant_execution_name": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
            "default_kernel_consumer_future_wna16_variant_execution_mode": "independent_future_wna16_typed_slot_kernel_variant_execution",
            "default_kernel_consumer_future_wna16_variant_execution_source": "premap_future_wna16_typed_slot_payloadless_execution_v1",
            "default_kernel_consumer_future_wna16_variant_execution_scope": "independent_native_typed_slot_kernel_variant_execution",
            "default_kernel_consumer_future_wna16_variant_execution_source_count": source_count,
            "default_kernel_consumer_future_wna16_variant_execution_row_count": row_count,
            "default_kernel_consumer_future_wna16_variant_execution_row_ok_count": row_count,
            "default_kernel_consumer_future_wna16_variant_execution_evidence_path": "outputs/reports/premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_execution_entry_args_ptr_native_v1.json",
            "default_kernel_consumer_future_wna16_variant_execution_evidence_sha256": HEX,
            "default_kernel_consumer_future_wna16_variant_execution_payloadless_json": summary[
                "default_kernel_consumer_future_wna16_payloadless_execution_evidence_path"
            ],
            "default_kernel_consumer_future_wna16_variant_execution_payloadless_sha256": summary[
                "default_kernel_consumer_future_wna16_payloadless_execution_evidence_sha256"
            ],
            "default_kernel_consumer_future_wna16_variant_execution_native_json": "outputs/reports/premap_kernel_consumer/future_wna16_variant_execution_timing_stub.json",
            "default_kernel_consumer_future_wna16_variant_execution_native_sha256": HEX,
            "default_kernel_consumer_future_wna16_variant_execution_native_host_wall_ms": 12.0,
            "default_kernel_consumer_future_wna16_variant_execution_outer_wall_ms": 13.0,
            "default_kernel_consumer_future_wna16_variant_execution_payload_bytes": 0,
            "default_kernel_consumer_future_wna16_variant_execution_payload_deref_allowed": False,
            "default_kernel_consumer_future_wna16_variant_execution_kernel_arg_pass_allowed": False,
            "default_kernel_consumer_future_wna16_variant_execution_passed_to_kernel": False,
            "default_kernel_consumer_future_wna16_variant_execution_changes_kernel_launch_args": False,
            "default_kernel_consumer_future_wna16_variant_execution_current_wna16_arg_compatible": False,
            "default_kernel_consumer_future_wna16_variant_execution_uses_current_wna16_args": False,
            "default_kernel_consumer_future_wna16_variant_execution_passes_current_wna16_args": False,
            "default_kernel_consumer_future_wna16_variant_execution_requires_wna16_arg_reinterpretation": False,
            "default_kernel_consumer_future_wna16_variant_execution_measures_tpot": False,
            "default_kernel_consumer_future_wna16_variant_execution_measures_vllm_latency": False,
            "default_kernel_consumer_future_wna16_variant_execution_wna16_benchmark_ready": False,
        }
    )


def _enable_useful_consumer_ready(
    summary: dict[str, object],
    *,
    row_count: int | None = None,
    source_count: int = 128,
) -> None:
    row_count = row_count or int(
        summary["default_kernel_consumer_future_wna16_variant_execution_row_count"]
    )
    fields = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    prefix = "default_kernel_consumer_future_wna16_useful_consumer"
    summary.update(
        {
            f"{prefix}_evidence_passed": True,
            f"{prefix}_ready": True,
            f"{prefix}_gate_ready": True,
            f"{prefix}_native_stub_checked": True,
            f"{prefix}_artifact_kind": (
                "future_wna16_typed_slot_kernel_variant_useful_consumer"
            ),
            f"{prefix}_name": "premap_future_wna16_typed_slot_useful_consumer_v1",
            f"{prefix}_mode": "independent_wna16_side_typed_slot_useful_consumer",
            f"{prefix}_source": (
                "premap_future_wna16_typed_slot_kernel_variant_execution_v1"
            ),
            f"{prefix}_semantics": "wna16_side_variant_all_four_field_projection",
            f"{prefix}_source_count": source_count,
            f"{prefix}_row_count": row_count,
            f"{prefix}_row_ok_count": row_count,
            f"{prefix}_rows_consumed": row_count,
            f"{prefix}_fields_consumed": fields,
            f"{prefix}_hash": HEX,
            f"{prefix}_evidence_path": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_typed_slot_kernel_variant_useful_consumer_entry_args_ptr_native_v1.json"
            ),
            f"{prefix}_evidence_sha256": HEX,
            f"{prefix}_execution_json": summary[
                "default_kernel_consumer_future_wna16_variant_execution_evidence_path"
            ],
            f"{prefix}_execution_sha256": summary[
                "default_kernel_consumer_future_wna16_variant_execution_evidence_sha256"
            ],
            f"{prefix}_native_timing_json": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_variant_execution_timing_stub.json"
            ),
            f"{prefix}_native_timing_sha256": HEX,
            f"{prefix}_native_stub_json": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_variant_execution_typed_consumer_stub.json"
            ),
            f"{prefix}_native_stub_sha256": HEX,
            f"{prefix}_timing_native_stub_json": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_variant_execution_typed_consumer_stub.json"
            ),
            f"{prefix}_timing_native_stub_sha256": HEX,
            f"{prefix}_payload_bytes": 0,
            f"{prefix}_payload_deref_allowed": False,
            f"{prefix}_kernel_arg_pass_allowed": False,
            f"{prefix}_passed_to_kernel": False,
            f"{prefix}_changes_kernel_launch_args": False,
            f"{prefix}_current_wna16_arg_compatible": False,
            f"{prefix}_uses_current_wna16_args": False,
            f"{prefix}_passes_current_wna16_args": False,
            f"{prefix}_requires_wna16_arg_reinterpretation": False,
            f"{prefix}_measures_tpot": False,
            f"{prefix}_measures_vllm_latency": False,
            f"{prefix}_wna16_benchmark_ready": False,
            f"{prefix}_wna16_side_hash": "aaaaaaaaaaaaaaaa",
            f"{prefix}_wna16_side_handle_projection_hash": "bbbbbbbbbbbbbbbb",
        }
    )
    for idx, field in enumerate(fields, start=1):
        summary[f"{prefix}_{field}_row_ok_count"] = row_count
        summary[f"{prefix}_{field}_field_hash"] = f"{idx:016x}"
        summary[f"{prefix}_{field}_useful_hash"] = f"{idx + 10:016x}"


def _enable_payloadless_useful_execution_ready(
    summary: dict[str, object],
    *,
    row_count: int | None = None,
    source_count: int = 128,
) -> None:
    row_count = row_count or int(
        summary["default_kernel_consumer_future_wna16_useful_consumer_row_count"]
    )
    fields = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    prefix = "default_kernel_consumer_future_wna16_payloadless_useful_execution"
    useful_prefix = "default_kernel_consumer_future_wna16_useful_consumer"
    summary.update(
        {
            f"{prefix}_evidence_passed": True,
            f"{prefix}_ready": True,
            f"{prefix}_gate_ready": True,
            f"{prefix}_chain_checked": True,
            f"{prefix}_native_stub_checked": True,
            f"{prefix}_artifact_kind": (
                "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
            ),
            f"{prefix}_name": (
                "premap_future_wna16_typed_slot_payloadless_useful_execution_v1"
            ),
            f"{prefix}_mode": (
                "independent_future_wna16_typed_slot_payloadless_useful_execution"
            ),
            f"{prefix}_source": (
                "premap_future_wna16_typed_slot_kernel_variant_useful_consumer_v1"
            ),
            f"{prefix}_source_count": source_count,
            f"{prefix}_row_count": row_count,
            f"{prefix}_row_ok_count": row_count,
            f"{prefix}_rows_consumed": row_count,
            f"{prefix}_evidence_path": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_entry_args_ptr_native_v1.json"
            ),
            f"{prefix}_evidence_sha256": HEX,
            f"{prefix}_useful_consumer_json": summary[
                f"{useful_prefix}_evidence_path"
            ],
            f"{prefix}_useful_consumer_sha256": summary[
                f"{useful_prefix}_evidence_sha256"
            ],
            f"{prefix}_execution_json": summary[f"{useful_prefix}_execution_json"],
            f"{prefix}_execution_sha256": summary[f"{useful_prefix}_execution_sha256"],
            f"{prefix}_native_timing_json": summary[
                f"{useful_prefix}_native_timing_json"
            ],
            f"{prefix}_native_timing_sha256": summary[
                f"{useful_prefix}_native_timing_sha256"
            ],
            f"{prefix}_native_stub_json": summary[f"{useful_prefix}_native_stub_json"],
            f"{prefix}_native_stub_sha256": summary[
                f"{useful_prefix}_native_stub_sha256"
            ],
            f"{prefix}_chain_hash": HEX,
            f"{prefix}_payload_bytes": 0,
            f"{prefix}_payload_deref_allowed": False,
            f"{prefix}_kernel_arg_pass_allowed": False,
            f"{prefix}_passed_to_kernel": False,
            f"{prefix}_changes_kernel_launch_args": False,
            f"{prefix}_current_wna16_arg_compatible": False,
            f"{prefix}_uses_current_wna16_args": False,
            f"{prefix}_passes_current_wna16_args": False,
            f"{prefix}_requires_wna16_arg_reinterpretation": False,
            f"{prefix}_measures_tpot": False,
            f"{prefix}_measures_vllm_latency": False,
            f"{prefix}_wna16_benchmark_ready": False,
        }
    )
    for field in fields:
        summary[f"{prefix}_{field}_row_ok_count"] = row_count
        summary[f"{prefix}_{field}_field_hash"] = summary[
            f"{useful_prefix}_{field}_field_hash"
        ]


def _enable_payloadless_useful_repeat_benchmark_ready(
    summary: dict[str, object],
    *,
    row_count: int | None = None,
    source_count: int = 128,
    repeat_count: int = 3,
) -> None:
    row_count = row_count or int(
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_row_count"
        ]
    )
    prefix = (
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark"
    )
    summary.update(
        {
            f"{prefix}_evidence_passed": True,
            f"{prefix}_ready": True,
            f"{prefix}_artifact_kind": (
                "future_wna16_typed_slot_payloadless_useful_repeat_benchmark"
            ),
            f"{prefix}_name": (
                "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1"
            ),
            f"{prefix}_mode": "payloadless_useful_native_stub_repeat_benchmark",
            f"{prefix}_source": (
                "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1"
            ),
            f"{prefix}_scope": "payloadless_useful_independent_native_stub_host_wall",
            f"{prefix}_source_count": source_count,
            f"{prefix}_row_count": row_count,
            f"{prefix}_row_ok_count": row_count,
            f"{prefix}_rows_consumed": row_count,
            f"{prefix}_repeat_count_requested": repeat_count,
            f"{prefix}_repeat_count_measured": repeat_count,
            f"{prefix}_measurement_source": (
                "repeated_independent_native_typed_slot_timing_stub"
            ),
            f"{prefix}_seed_only": False,
            f"{prefix}_evidence_path": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_entry_args_ptr_repeat3_gpu1_v1.json"
            ),
            f"{prefix}_evidence_sha256": HEX,
            f"{prefix}_harness_json": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_typed_slot_payloadless_useful_benchmark_harness_entry_args_ptr_v1.json"
            ),
            f"{prefix}_harness_sha256": HEX,
            f"{prefix}_native_timing_seed_json": (
                "outputs/reports/premap_kernel_consumer/"
                "future_wna16_variant_execution_timing_stub.json"
            ),
            f"{prefix}_native_timing_seed_sha256": HEX,
            f"{prefix}_native_stub_host_wall_ms_min": 10.0,
            f"{prefix}_native_stub_host_wall_ms_median": 11.0,
            f"{prefix}_native_stub_host_wall_ms_mean": 11.0,
            f"{prefix}_native_stub_host_wall_ms_max": 12.0,
            f"{prefix}_payload_bytes": 0,
            f"{prefix}_payload_deref_allowed": False,
            f"{prefix}_kernel_arg_pass_allowed": False,
            f"{prefix}_passed_to_kernel": False,
            f"{prefix}_changes_kernel_launch_args": False,
            f"{prefix}_current_wna16_arg_compatible": False,
            f"{prefix}_uses_current_wna16_args": False,
            f"{prefix}_passes_current_wna16_args": False,
            f"{prefix}_requires_wna16_arg_reinterpretation": False,
            f"{prefix}_measures_tpot": False,
            f"{prefix}_measures_vllm_latency": False,
            f"{prefix}_wna16_benchmark_ready": False,
            f"{prefix}_next_runtime_stage": (
                "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
            ),
        }
    )
    execution_prefix = (
        "default_kernel_consumer_future_wna16_payloadless_useful_execution"
    )
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        summary[f"{prefix}_{field}_field_hash"] = summary[
            f"{execution_prefix}_{field}_field_hash"
        ]


def _summary() -> dict[str, object]:
    summary = {
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
        "prefetch_lab_default_ready_time_direct_snapshot_report_present": True,
        "prefetch_lab_default_ready_time_direct_snapshot_report_passed": True,
        "prefetch_lab_default_ready_time_direct_snapshot_report_recheck_passed": True,
        "prefetch_lab_default_ready_time_direct_snapshot_present": True,
        "prefetch_lab_default_ready_time_direct_snapshot_runtime_stage": (
            "online_ready_time_payload_cache_accounting_only"
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_payload_bytes": 0,
        "prefetch_lab_default_ready_time_direct_snapshot_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_ready_time_direct_snapshot_changes_kernel_launch_args": False,
        "prefetch_lab_default_ready_time_direct_snapshot_issue_sources": [
            "prelaunch_observed_transition_premap_shadow"
        ],
        "prefetch_lab_default_payload_cache_runtime_participation_present": True,
        "prefetch_lab_default_payload_cache_runtime_participation_stage": (
            "online_ready_time_payload_cache_runtime_participation_dry_run"
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_status": (
            "accounting_only_no_used_fetch"
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_consumes_direct_snapshot": (
            True
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes": 0,
        "prefetch_lab_default_payload_cache_runtime_participation_ready_credit": False,
        "prefetch_lab_default_payload_cache_runtime_participation_real_ready_credit_granted": False,
        "prefetch_lab_default_payload_cache_runtime_participation_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_payload_cache_runtime_participation_changes_kernel_launch_args": False,
        "prefetch_lab_default_payload_cache_runtime_participation_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_payload_cache_runtime_participation_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_payload_cache_runtime_participation_issue_sources": [
            "prelaunch_observed_transition_premap_shadow"
        ],
        "prefetch_lab_default_payload_cache_runtime_plan_present": True,
        "prefetch_lab_default_payload_cache_runtime_plan_stage": (
            "payload_cache_runtime_plan_lab_gate_dry_run"
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_status": (
            "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_consumes_participation": True,
        "prefetch_lab_default_payload_cache_runtime_plan_live_payload_runtime_enabled": False,
        "prefetch_lab_default_payload_cache_runtime_plan_planned_issue_count": 0,
        "prefetch_lab_default_payload_cache_runtime_plan_payload_bytes": 0,
        "prefetch_lab_default_payload_cache_runtime_plan_ready_credit": False,
        "prefetch_lab_default_payload_cache_runtime_plan_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_payload_cache_runtime_plan_changes_kernel_launch_args": False,
        "prefetch_lab_default_payload_cache_runtime_plan_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_payload_cache_runtime_execution_present": True,
        "prefetch_lab_default_payload_cache_runtime_execution_stage": (
            "payload_cache_runtime_execution_lab_gate_dry_run"
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_status": (
            "blocked_by_runtime_plan:"
            "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_consumes_plan": True,
        "prefetch_lab_default_payload_cache_runtime_execution_plan_status": (
            "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_decision": "blocked",
        "prefetch_lab_default_payload_cache_runtime_execution_block_reason": (
            "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_execution_mode": (
            "payloadless_lab_gate_dry_run"
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_live_payload_runtime_enabled": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_payload_transfer_runtime_enabled": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_issued_payload_count": 0,
        "prefetch_lab_default_payload_cache_runtime_execution_payload_bytes": 0,
        "prefetch_lab_default_payload_cache_runtime_execution_ready_credit": False,
        "prefetch_lab_default_payload_cache_runtime_execution_real_ready_credit_granted": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_changes_kernel_launch_args": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_full_fetch_runtime_allowed": (
            False
        ),
        "prefetch_lab_default_stream_decision_gate_present": True,
        "prefetch_lab_default_stream_decision_gate_passed": True,
        "prefetch_lab_default_stream_decision": (
            "block_full_fetch_insufficient_stream_lookahead"
        ),
        "prefetch_lab_default_stream_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_full_fetch_block_reason": (
            "insufficient_stream_lookahead"
        ),
        "prefetch_lab_default_stream_current_lookahead_us": 0.0,
        "prefetch_lab_default_stream_required_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_lookahead_deficit_us": 2400000.0,
        "prefetch_lab_default_stream_first_model_passing_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_metadata_premap_runtime_preferred": True,
        "prefetch_lab_default_stream_descriptor_prep_runtime_preferred": True,
        "prefetch_lab_default_stream_required_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_required_shifted_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_required_shifted_issue_clamped_issue_count": 12,
        "prefetch_lab_default_stream_required_shifted_issue_duplicate_issue_key_count": 12,
        "prefetch_lab_default_stream_required_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_required_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_required_shifted_issue_invalid_export_count": 0,
        "prefetch_lab_default_stream_required_shifted_issue_row_shift_mismatch_count": 0,
        "prefetch_lab_default_stream_required_shifted_issue_row_clamp_mismatch_count": 0,
        "prefetch_lab_default_stream_feasibility_present": True,
        "prefetch_lab_default_stream_feasibility_passed": True,
        "prefetch_lab_default_stream_current_runtime_satisfies_model": False,
        "prefetch_lab_default_stream_feasible_within_configured_token_window": True,
        "prefetch_lab_default_stream_min_required_lead_tokens": 24,
        "prefetch_lab_default_stream_max_required_lead_tokens": 48,
        "prefetch_lab_default_stream_max_candidate_lead_tokens": 64,
        "prefetch_lab_default_stream_lead_token_sweep_present": True,
        "prefetch_lab_default_stream_lead_token_sweep_passed": True,
        "prefetch_lab_default_stream_lead_token_sweep_event_timing_mode": (
            "token_index"
        ),
        "prefetch_lab_default_stream_lead_token_sweep_token_timing_enabled": True,
        "prefetch_lab_default_stream_lead_token_sweep_decode_token_us": 75000.0,
        "prefetch_lab_default_stream_first_model_passing_lead_tokens": 32,
        "prefetch_lab_default_stream_lead_token_sweep_first_model_passing_lookahead_us": (
            2400000.0
        ),
        "prefetch_lab_default_stream_queue_budget_present": True,
        "prefetch_lab_default_stream_queue_budget_passed": True,
        "prefetch_lab_default_stream_queue_budget_cell_count": 16,
        "prefetch_lab_default_stream_queue_budget_event_timing_mode": "token_index",
        "prefetch_lab_default_stream_queue_budget_first_model_passing_capacity": 4096,
        "prefetch_lab_default_stream_queue_budget_first_model_passing_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_first_model_passing_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_first_model_passing_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_present": True,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_stage": "payload_cache_queue_budget_runtime_envelope_lab_gate",
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_status": "model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_execution_mode": "payloadless_queue_budget_lab_gate",
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_consumes_queue_budget_sweep": True,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_transfer_enabled": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_full_fetch_allowed": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_live_runtime_instantiated": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_present": True,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_stage": "payload_cache_live_payload_stage_preflight",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_status": "blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_consumes_queue_budget_runtime_envelope": True,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_envelope_status": "model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_capacity_entries": 4096,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_decision": "blocked",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_block_reason": "live_payload_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_execution_mode": "payloadless_live_payload_stage_preflight",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_present": True,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_stage": "payload_cache_live_payload_runtime_disabled_canary",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_status": "blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_consumes_live_payload_stage_preflight": True,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_live_payload_stage_status": "blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_capacity_entries": 4096,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_decision": "blocked",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_block_reason": "live_payload_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_execution_mode": "payloadless_live_payload_runtime_disabled_canary",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_present": True,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_stage": "payload_cache_manager_implementation_artifact",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_status": "blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_consumes_live_payload_runtime_canary": True,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_live_payload_runtime_status": "blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_manager_backend": "ReadyTimeExpertCacheManager",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_manager_contract": "event_driven_queue_budget_cache_manager_v1",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_capacity_entries": 4096,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_decision": "blocked",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_block_reason": "implementation_artifact_default_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_execution_mode": "payload_cache_manager_implementation_artifact_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_manager_artifact_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_present": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_stage": "payload_cache_manager_runtime_skeleton",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_status": "blocked_by_manager_artifact:blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_consumes_manager_implementation_artifact": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_artifact_status": "blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_backend": "ReadyTimeExpertCacheManager",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_contract": "event_driven_queue_budget_cache_manager_v1",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_capacity_entries": 4096,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_runtime_instantiated": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_decision": "blocked",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_block_reason": "runtime_skeleton_default_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_execution_mode": "payload_cache_manager_runtime_skeleton_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_present": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_stage": "payload_cache_manager_runtime_snapshot_artifact",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_status": "blocked_by_runtime_skeleton:blocked_by_manager_artifact:blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_consumes_runtime_skeleton": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_runtime_skeleton_status": "blocked_by_manager_artifact:blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_manager_backend": "ReadyTimeExpertCacheManager",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_snapshot_source": "ReadyTimeExpertCacheManager.empty_snapshot",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_accounting_snapshot_instantiated": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_live_runtime_instantiated": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_capacity_entries": 4096,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_batch_size": 1,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_resident_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_issued_fetch_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_used_fetch_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_unused_fetch_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_demand_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_demand_hit_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_demand_miss_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_evicted_before_use_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_ready_late_miss_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_late_completion_unused_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_batch_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_service_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_total_span_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_wait_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_max_delay_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_decision": "blocked",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_block_reason": "runtime_snapshot_default_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_execution_mode": "payload_cache_manager_runtime_snapshot_disabled",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_present": True,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_stage": "payload_cache_snapshot_backed_live_runtime_preflight",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_status": "blocked_by_runtime_snapshot:blocked_by_runtime_skeleton:blocked_by_manager_artifact:blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_consumes_runtime_snapshot": True,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_runtime_snapshot_status": "blocked_by_runtime_skeleton:blocked_by_manager_artifact:blocked_by_live_payload_runtime:blocked_by_live_payload_stage:blocked_by_queue_budget_runtime_envelope:model_queue_budget_satisfied_runtime_disabled",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_backend": "ReadyTimeExpertCacheManager",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_snapshot_source": "PayloadCacheManagerRuntimeSnapshotArtifact",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_preflight_instantiated": True,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_accounting_snapshot_instantiated": True,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_instantiated": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_capacity_entries": 4096,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_deadline_us": 100.0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_lookahead_us": 2400000.0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_size": 1,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_resident_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_fetch_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_used_fetch_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_unused_fetch_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_hit_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_miss_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_evicted_before_use_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_late_miss_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_late_completion_unused_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_service_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_total_span_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_wait_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_max_delay_us": 0.0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounting_enabled": True,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounted_packet_count": 28,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_unique_issue_key_count": 16,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_decision": "blocked",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_block_reason": "snapshot_backed_live_runtime_preflight_disabled",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_execution_mode": "payload_cache_snapshot_backed_live_runtime_preflight_disabled",
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_payload_bytes": 0,
        "prefetch_lab_default_stream_queue_budget_issued_payload_count": 0,
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_payload_transfer_enabled": False,
        "prefetch_lab_default_stream_queue_budget_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_stream_queue_budget_payload_deref_allowed": False,
        "prefetch_lab_default_stream_queue_budget_payload_deref_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_full_fetch_allowed": False,
        "prefetch_lab_default_stream_queue_budget_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_queue_budget_ready_credit": False,
        "prefetch_lab_default_stream_queue_budget_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_queue_budget_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_queue_budget_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_queue_budget_passed_to_kernel": False,
        "prefetch_lab_default_stream_queue_budget_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_queue_budget_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_queue_budget_measures_tpot": False,
        "prefetch_lab_default_stream_queue_budget_measures_vllm_latency": False,
        "prefetch_lab_default_stream_queue_budget_live_runtime_instantiated": False,
        "prefetch_lab_default_stream_shifted_issue_replay_contract_present": True,
        "prefetch_lab_default_stream_shifted_issue_replay_contract_passed": True,
        "prefetch_lab_default_stream_shifted_issue_replay_contract_required_lead_tokens": 32,
        "prefetch_lab_default_stream_shifted_issue_replay_contract_min_schedulable_packets": 28,
        "prefetch_lab_default_stream_shifted_issue_replay_issue_lead_tokens": 32,
        "prefetch_lab_default_stream_shifted_issue_replay_schedulable_packet_count": 28,
        "prefetch_lab_default_stream_shifted_issue_replay_clamped_issue_count": 12,
        "prefetch_lab_default_stream_shifted_issue_replay_duplicate_issue_key_count": 12,
        "prefetch_lab_default_stream_shifted_issue_replay_row_shift_mismatch_count": 0,
        "prefetch_lab_default_stream_shifted_issue_replay_row_clamp_mismatch_count": 0,
        "prefetch_lab_default_stream_shifted_issue_replay_payload_bytes": 0,
        "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_ready_credit": False,
        "prefetch_lab_default_stream_shifted_issue_replay_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_shifted_issue_replay_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_shifted_issue_replay_payload_transfer_enabled": False,
        "prefetch_lab_default_stream_shifted_issue_replay_payload_deref_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_passed_to_kernel": False,
        "prefetch_lab_default_stream_shifted_issue_replay_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_bytes": 0,
        "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_ready_credit": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_ready_before_demand_credit": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_real_ready_credit_granted": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_transfer_enabled": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_deref_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_passed_to_kernel": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_changes_kernel_launch_args": False,
        "prefetch_lab_default_stream_shifted_issue_replay_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_shifted_issue_replay_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_shifted_issue_replay_current_wna16_arg_compatible": False,
        "prefetch_lab_default_stream_shifted_issue_replay_requires_wna16_arg_reinterpretation": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_uses_current_wna16_args": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_passes_current_wna16_args": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_current_wna16_arg_compatible": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation": False,
        "prefetch_lab_default_stream_shifted_issue_replay_wna16_benchmark_ready": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_wna16_benchmark_ready": False,
        "prefetch_lab_default_stream_shifted_issue_replay_measures_tpot": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_measures_tpot": False,
        "prefetch_lab_default_stream_shifted_issue_replay_measures_vllm_latency": False,
        "prefetch_lab_default_stream_shifted_issue_replay_source_measures_vllm_latency": False,
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
    live_preflight_status = str(
        summary[
            "prefetch_lab_default_stream_queue_budget_"
            "snapshot_backed_live_runtime_preflight_status"
        ],
    )
    prefix = "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_canary"
    summary.update(
        {
            f"{prefix}_present": True,
            f"{prefix}_stage": "payload_cache_snapshot_backed_live_runtime_disabled_canary",
            f"{prefix}_status": f"blocked_by_live_runtime_preflight:{live_preflight_status}",
            f"{prefix}_consumes_live_runtime_preflight": True,
            f"{prefix}_live_runtime_preflight_status": live_preflight_status,
            f"{prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{prefix}_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
            f"{prefix}_manager_runtime_mode": "ready_time_payload_cache_skeleton",
            f"{prefix}_live_runtime_canary_instantiated": True,
            f"{prefix}_live_runtime_preflight_instantiated": True,
            f"{prefix}_accounting_snapshot_instantiated": True,
            f"{prefix}_live_runtime_instantiated": False,
            f"{prefix}_capacity_entries": 4096,
            f"{prefix}_issue_lead_tokens": 32,
            f"{prefix}_queue_deadline_us": 100.0,
            f"{prefix}_lookahead_us": 2400000.0,
            f"{prefix}_queue_batch_size": 1,
            f"{prefix}_shifted_issue_accounting_enabled": True,
            f"{prefix}_shifted_issue_accounted_packet_count": 28,
            f"{prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{prefix}_decision": "blocked",
            f"{prefix}_block_reason": "snapshot_backed_live_runtime_canary_disabled",
            f"{prefix}_execution_mode": (
                "payload_cache_snapshot_backed_live_runtime_canary_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{prefix}_{key}"] = False
    state_prefix = "prefetch_lab_default_stream_queue_budget_live_runtime_state_shape"
    canary_status = str(
        summary[
            "prefetch_lab_default_stream_queue_budget_"
            "snapshot_backed_live_runtime_canary_status"
        ],
    )
    summary.update(
        {
            f"{state_prefix}_present": True,
            f"{state_prefix}_stage": "payload_cache_live_runtime_state_shape_check",
            f"{state_prefix}_status": f"blocked_by_live_runtime_canary:{canary_status}",
            f"{state_prefix}_consumes_live_runtime_canary": True,
            f"{state_prefix}_live_runtime_canary_status": canary_status,
            f"{state_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{state_prefix}_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
            f"{state_prefix}_manager_runtime_mode": "ready_time_payload_cache_skeleton",
            f"{state_prefix}_state_shape_schema": "ready_time_issue_demand_state_shape_v1",
            f"{state_prefix}_live_runtime_state_shape_checked": True,
            f"{state_prefix}_issue_queue_shape_checked": True,
            f"{state_prefix}_demand_state_shape_checked": True,
            f"{state_prefix}_resident_index_shape_checked": True,
            f"{state_prefix}_queue_timing_shape_checked": True,
            f"{state_prefix}_live_runtime_instantiated": False,
            f"{state_prefix}_capacity_entries": 4096,
            f"{state_prefix}_issue_lead_tokens": 32,
            f"{state_prefix}_queue_deadline_us": 100.0,
            f"{state_prefix}_lookahead_us": 2400000.0,
            f"{state_prefix}_queue_batch_size": 1,
            f"{state_prefix}_shifted_issue_accounting_enabled": True,
            f"{state_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{state_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{state_prefix}_decision": "blocked",
            f"{state_prefix}_block_reason": "live_runtime_state_shape_only",
            f"{state_prefix}_execution_mode": (
                "payload_cache_live_runtime_state_shape_check_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{state_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{state_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{state_prefix}_{key}"] = False
    object_prefix = "prefetch_lab_default_stream_queue_budget_live_runtime_object_preflight"
    state_status = str(summary[f"{state_prefix}_status"])
    summary.update(
        {
            f"{object_prefix}_present": True,
            f"{object_prefix}_stage": (
                "payload_cache_live_runtime_object_construction_preflight"
            ),
            f"{object_prefix}_status": f"blocked_by_state_shape_check:{state_status}",
            f"{object_prefix}_consumes_state_shape_check": True,
            f"{object_prefix}_state_shape_status": state_status,
            f"{object_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{object_prefix}_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
            f"{object_prefix}_manager_runtime_mode": "ready_time_payload_cache_skeleton",
            f"{object_prefix}_state_shape_schema": "ready_time_issue_demand_state_shape_v1",
            f"{object_prefix}_object_construction_preflight_instantiated": True,
            f"{object_prefix}_typed_issue_queue_container_declared": True,
            f"{object_prefix}_typed_demand_state_container_declared": True,
            f"{object_prefix}_typed_resident_index_container_declared": True,
            f"{object_prefix}_typed_queue_timing_container_declared": True,
            f"{object_prefix}_live_runtime_instantiated": False,
            f"{object_prefix}_capacity_entries": 4096,
            f"{object_prefix}_issue_lead_tokens": 32,
            f"{object_prefix}_queue_deadline_us": 100.0,
            f"{object_prefix}_lookahead_us": 2400000.0,
            f"{object_prefix}_queue_batch_size": 1,
            f"{object_prefix}_shifted_issue_accounting_enabled": True,
            f"{object_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{object_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{object_prefix}_decision": "blocked",
            f"{object_prefix}_block_reason": (
                "live_runtime_object_construction_preflight_only"
            ),
            f"{object_prefix}_execution_mode": (
                "payload_cache_live_runtime_object_construction_preflight_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{object_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{object_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{object_prefix}_{key}"] = False
    adapter_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_object_adapter_preflight"
    )
    object_status = str(summary[f"{object_prefix}_status"])
    summary.update(
        {
            f"{adapter_prefix}_present": True,
            f"{adapter_prefix}_stage": (
                "payload_cache_live_runtime_object_adapter_preflight"
            ),
            f"{adapter_prefix}_status": (
                f"blocked_by_object_construction_preflight:{object_status}"
            ),
            f"{adapter_prefix}_consumes_object_construction_preflight": True,
            f"{adapter_prefix}_object_preflight_status": object_status,
            f"{adapter_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{adapter_prefix}_manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
            f"{adapter_prefix}_manager_runtime_mode": "ready_time_payload_cache_skeleton",
            f"{adapter_prefix}_state_shape_schema": "ready_time_issue_demand_state_shape_v1",
            f"{adapter_prefix}_runtime_adapter_schema": (
                "ready_time_payload_cache_runtime_adapter_v1"
            ),
            f"{adapter_prefix}_object_construction_preflight_instantiated": True,
            f"{adapter_prefix}_runtime_object_adapter_declared": True,
            f"{adapter_prefix}_issue_queue_adapter_bound": True,
            f"{adapter_prefix}_demand_state_adapter_bound": True,
            f"{adapter_prefix}_resident_index_adapter_bound": True,
            f"{adapter_prefix}_queue_timing_adapter_bound": True,
            f"{adapter_prefix}_live_runtime_instantiated": False,
            f"{adapter_prefix}_capacity_entries": 4096,
            f"{adapter_prefix}_issue_lead_tokens": 32,
            f"{adapter_prefix}_queue_deadline_us": 100.0,
            f"{adapter_prefix}_lookahead_us": 2400000.0,
            f"{adapter_prefix}_queue_batch_size": 1,
            f"{adapter_prefix}_shifted_issue_accounting_enabled": True,
            f"{adapter_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{adapter_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{adapter_prefix}_decision": "blocked",
            f"{adapter_prefix}_block_reason": (
                "live_runtime_object_adapter_preflight_only"
            ),
            f"{adapter_prefix}_execution_mode": (
                "payload_cache_live_runtime_object_adapter_preflight_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{adapter_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{adapter_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{adapter_prefix}_{key}"] = False
    materialization_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_materialization_preflight"
    )
    adapter_status = str(summary[f"{adapter_prefix}_status"])
    summary.update(
        {
            f"{materialization_prefix}_present": True,
            f"{materialization_prefix}_stage": (
                "payload_cache_live_runtime_adapter_materialization_preflight"
            ),
            f"{materialization_prefix}_status": (
                f"blocked_by_object_adapter_preflight:{adapter_status}"
            ),
            f"{materialization_prefix}_consumes_object_adapter_preflight": True,
            f"{materialization_prefix}_object_adapter_status": adapter_status,
            f"{materialization_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{materialization_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{materialization_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{materialization_prefix}_state_shape_schema": (
                "ready_time_issue_demand_state_shape_v1"
            ),
            f"{materialization_prefix}_runtime_adapter_schema": (
                "ready_time_payload_cache_runtime_adapter_v1"
            ),
            f"{materialization_prefix}_object_construction_preflight_instantiated": True,
            f"{materialization_prefix}_adapter_materialization_preflight_instantiated": True,
            f"{materialization_prefix}_runtime_object_adapter_declared": True,
            f"{materialization_prefix}_issue_queue_materialization_checked": True,
            f"{materialization_prefix}_demand_state_materialization_checked": True,
            f"{materialization_prefix}_resident_index_materialization_checked": True,
            f"{materialization_prefix}_queue_timing_materialization_checked": True,
            f"{materialization_prefix}_live_runtime_instantiated": False,
            f"{materialization_prefix}_capacity_entries": 4096,
            f"{materialization_prefix}_issue_lead_tokens": 32,
            f"{materialization_prefix}_queue_deadline_us": 100.0,
            f"{materialization_prefix}_lookahead_us": 2400000.0,
            f"{materialization_prefix}_queue_batch_size": 1,
            f"{materialization_prefix}_shifted_issue_accounting_enabled": True,
            f"{materialization_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{materialization_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{materialization_prefix}_decision": "blocked",
            f"{materialization_prefix}_block_reason": (
                "live_runtime_adapter_materialization_preflight_only"
            ),
            f"{materialization_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_materialization_preflight_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{materialization_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{materialization_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{materialization_prefix}_{key}"] = False
    state_object_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_state_object_preflight"
    )
    materialization_status = str(summary[f"{materialization_prefix}_status"])
    summary.update(
        {
            f"{state_object_prefix}_present": True,
            f"{state_object_prefix}_stage": (
                "payload_cache_live_runtime_adapter_state_object_preflight"
            ),
            f"{state_object_prefix}_status": (
                f"blocked_by_adapter_materialization_preflight:"
                f"{materialization_status}"
            ),
            f"{state_object_prefix}_consumes_adapter_materialization_preflight": True,
            f"{state_object_prefix}_adapter_materialization_status": (
                materialization_status
            ),
            f"{state_object_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{state_object_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{state_object_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{state_object_prefix}_state_shape_schema": (
                "ready_time_issue_demand_state_shape_v1"
            ),
            f"{state_object_prefix}_runtime_adapter_schema": (
                "ready_time_payload_cache_runtime_adapter_v1"
            ),
            f"{state_object_prefix}_adapter_state_object_schema": (
                "ready_time_payload_cache_adapter_state_v1"
            ),
            f"{state_object_prefix}_adapter_materialization_preflight_instantiated": True,
            f"{state_object_prefix}_adapter_state_object_declared": True,
            f"{state_object_prefix}_issue_queue_state_object_declared": True,
            f"{state_object_prefix}_demand_state_object_declared": True,
            f"{state_object_prefix}_resident_index_state_object_declared": True,
            f"{state_object_prefix}_queue_timing_state_object_declared": True,
            f"{state_object_prefix}_live_runtime_instantiated": False,
            f"{state_object_prefix}_capacity_entries": 4096,
            f"{state_object_prefix}_issue_lead_tokens": 32,
            f"{state_object_prefix}_queue_deadline_us": 100.0,
            f"{state_object_prefix}_lookahead_us": 2400000.0,
            f"{state_object_prefix}_queue_batch_size": 1,
            f"{state_object_prefix}_shifted_issue_accounting_enabled": True,
            f"{state_object_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{state_object_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{state_object_prefix}_decision": "blocked",
            f"{state_object_prefix}_block_reason": (
                "live_runtime_adapter_state_object_preflight_only"
            ),
            f"{state_object_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_state_object_preflight_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{state_object_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{state_object_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{state_object_prefix}_{key}"] = False
    state_validation_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_state_validation_preflight"
    )
    state_object_status = str(summary[f"{state_object_prefix}_status"])
    summary.update(
        {
            f"{state_validation_prefix}_present": True,
            f"{state_validation_prefix}_stage": (
                "payload_cache_live_runtime_adapter_state_validation_preflight"
            ),
            f"{state_validation_prefix}_status": (
                f"blocked_by_adapter_state_object_preflight:{state_object_status}"
            ),
            f"{state_validation_prefix}_consumes_adapter_state_object_preflight": True,
            f"{state_validation_prefix}_adapter_state_object_status": (
                state_object_status
            ),
            f"{state_validation_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{state_validation_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{state_validation_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{state_validation_prefix}_state_shape_schema": (
                "ready_time_issue_demand_state_shape_v1"
            ),
            f"{state_validation_prefix}_runtime_adapter_schema": (
                "ready_time_payload_cache_runtime_adapter_v1"
            ),
            f"{state_validation_prefix}_adapter_state_object_schema": (
                "ready_time_payload_cache_adapter_state_v1"
            ),
            f"{state_validation_prefix}_adapter_state_validation_schema": (
                "ready_time_payload_cache_adapter_state_validation_v1"
            ),
            f"{state_validation_prefix}_adapter_state_object_declared": True,
            f"{state_validation_prefix}_adapter_state_validation_preflight_instantiated": (
                True
            ),
            f"{state_validation_prefix}_issue_queue_state_object_validated": True,
            f"{state_validation_prefix}_demand_state_object_validated": True,
            f"{state_validation_prefix}_resident_index_state_object_validated": True,
            f"{state_validation_prefix}_queue_timing_state_object_validated": True,
            f"{state_validation_prefix}_live_runtime_instantiated": False,
            f"{state_validation_prefix}_capacity_entries": 4096,
            f"{state_validation_prefix}_issue_lead_tokens": 32,
            f"{state_validation_prefix}_queue_deadline_us": 100.0,
            f"{state_validation_prefix}_lookahead_us": 2400000.0,
            f"{state_validation_prefix}_queue_batch_size": 1,
            f"{state_validation_prefix}_shifted_issue_accounting_enabled": True,
            f"{state_validation_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{state_validation_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{state_validation_prefix}_decision": "blocked",
            f"{state_validation_prefix}_block_reason": (
                "live_runtime_adapter_state_validation_preflight_only"
            ),
            f"{state_validation_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_state_validation_preflight_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{state_validation_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{state_validation_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{state_validation_prefix}_{key}"] = False
    state_validation_artifact_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_state_validation_artifact"
    )
    state_validation_status = str(summary[f"{state_validation_prefix}_status"])
    summary.update(
        {
            f"{state_validation_artifact_prefix}_present": True,
            f"{state_validation_artifact_prefix}_stage": (
                "payload_cache_live_runtime_adapter_state_validation_artifact"
            ),
            f"{state_validation_artifact_prefix}_status": (
                f"blocked_by_adapter_state_validation_preflight:"
                f"{state_validation_status}"
            ),
            f"{state_validation_artifact_prefix}_consumes_adapter_state_validation_preflight": (
                True
            ),
            f"{state_validation_artifact_prefix}_adapter_state_validation_status": (
                state_validation_status
            ),
            f"{state_validation_artifact_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{state_validation_artifact_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{state_validation_artifact_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{state_validation_artifact_prefix}_state_shape_schema": (
                "ready_time_issue_demand_state_shape_v1"
            ),
            f"{state_validation_artifact_prefix}_runtime_adapter_schema": (
                "ready_time_payload_cache_runtime_adapter_v1"
            ),
            f"{state_validation_artifact_prefix}_adapter_state_object_schema": (
                "ready_time_payload_cache_adapter_state_v1"
            ),
            f"{state_validation_artifact_prefix}_adapter_state_validation_schema": (
                "ready_time_payload_cache_adapter_state_validation_v1"
            ),
            f"{state_validation_artifact_prefix}_validated_state_artifact_schema": (
                "ready_time_payload_cache_validated_adapter_state_artifact_v1"
            ),
            f"{state_validation_artifact_prefix}_adapter_state_validation_preflight_instantiated": (
                True
            ),
            f"{state_validation_artifact_prefix}_adapter_state_validation_artifact_instantiated": (
                True
            ),
            f"{state_validation_artifact_prefix}_issue_queue_state_object_ready_for_runtime_adapter": (
                True
            ),
            f"{state_validation_artifact_prefix}_demand_state_object_ready_for_runtime_adapter": (
                True
            ),
            f"{state_validation_artifact_prefix}_resident_index_state_object_ready_for_runtime_adapter": (
                True
            ),
            f"{state_validation_artifact_prefix}_queue_timing_state_object_ready_for_runtime_adapter": (
                True
            ),
            f"{state_validation_artifact_prefix}_live_runtime_instantiated": False,
            f"{state_validation_artifact_prefix}_capacity_entries": 4096,
            f"{state_validation_artifact_prefix}_issue_lead_tokens": 32,
            f"{state_validation_artifact_prefix}_queue_deadline_us": 100.0,
            f"{state_validation_artifact_prefix}_lookahead_us": 2400000.0,
            f"{state_validation_artifact_prefix}_queue_batch_size": 1,
            f"{state_validation_artifact_prefix}_shifted_issue_accounting_enabled": True,
            f"{state_validation_artifact_prefix}_shifted_issue_accounted_packet_count": (
                28
            ),
            f"{state_validation_artifact_prefix}_shifted_issue_unique_issue_key_count": (
                16
            ),
            f"{state_validation_artifact_prefix}_decision": "blocked",
            f"{state_validation_artifact_prefix}_block_reason": (
                "live_runtime_adapter_state_validation_artifact_only"
            ),
            f"{state_validation_artifact_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_state_validation_artifact_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{state_validation_artifact_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{state_validation_artifact_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{state_validation_artifact_prefix}_{key}"] = False
    instantiation_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_instantiation_canary"
    )
    state_validation_artifact_status = str(
        summary[f"{state_validation_artifact_prefix}_status"],
    )
    summary.update(
        {
            f"{instantiation_prefix}_present": True,
            f"{instantiation_prefix}_stage": (
                "payload_cache_live_runtime_adapter_instantiation_canary"
            ),
            f"{instantiation_prefix}_status": (
                f"blocked_by_state_validation_artifact:"
                f"{state_validation_artifact_status}"
            ),
            f"{instantiation_prefix}_consumes_state_validation_artifact": True,
            f"{instantiation_prefix}_state_validation_artifact_status": (
                state_validation_artifact_status
            ),
            f"{instantiation_prefix}_manager_backend": "ReadyTimeExpertCacheManager",
            f"{instantiation_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{instantiation_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{instantiation_prefix}_validated_state_artifact_schema": (
                "ready_time_payload_cache_validated_adapter_state_artifact_v1"
            ),
            f"{instantiation_prefix}_runtime_adapter_instantiation_schema": (
                "ready_time_payload_cache_runtime_adapter_instantiation_v1"
            ),
            f"{instantiation_prefix}_adapter_factory_declared": True,
            f"{instantiation_prefix}_adapter_constructor_resolved": True,
            f"{instantiation_prefix}_adapter_instance_created": False,
            f"{instantiation_prefix}_live_runtime_instantiated": False,
            f"{instantiation_prefix}_capacity_entries": 4096,
            f"{instantiation_prefix}_issue_lead_tokens": 32,
            f"{instantiation_prefix}_queue_deadline_us": 100.0,
            f"{instantiation_prefix}_lookahead_us": 2400000.0,
            f"{instantiation_prefix}_queue_batch_size": 1,
            f"{instantiation_prefix}_shifted_issue_accounting_enabled": True,
            f"{instantiation_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{instantiation_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{instantiation_prefix}_decision": "blocked",
            f"{instantiation_prefix}_block_reason": (
                "live_runtime_adapter_instantiation_canary_only"
            ),
            f"{instantiation_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_instantiation_canary_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{instantiation_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{instantiation_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{instantiation_prefix}_{key}"] = False
    constructor_binding_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_constructor_binding_preflight"
    )
    instantiation_status = str(summary[f"{instantiation_prefix}_status"])
    summary.update(
        {
            f"{constructor_binding_prefix}_present": True,
            f"{constructor_binding_prefix}_stage": (
                "payload_cache_live_runtime_adapter_constructor_binding_preflight"
            ),
            f"{constructor_binding_prefix}_status": (
                f"blocked_by_instantiation_canary:{instantiation_status}"
            ),
            f"{constructor_binding_prefix}_consumes_instantiation_canary": True,
            f"{constructor_binding_prefix}_instantiation_canary_status": (
                instantiation_status
            ),
            f"{constructor_binding_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{constructor_binding_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{constructor_binding_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{constructor_binding_prefix}_runtime_adapter_instantiation_schema": (
                "ready_time_payload_cache_runtime_adapter_instantiation_v1"
            ),
            f"{constructor_binding_prefix}_constructor_binding_schema": (
                "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
            ),
            f"{constructor_binding_prefix}_adapter_factory_declared": True,
            f"{constructor_binding_prefix}_adapter_constructor_resolved": True,
            f"{constructor_binding_prefix}_constructor_inputs_bound": True,
            f"{constructor_binding_prefix}_binds_validated_state_artifact": True,
            f"{constructor_binding_prefix}_binds_queue_budget_parameters": True,
            f"{constructor_binding_prefix}_binds_shifted_issue_accounting": True,
            f"{constructor_binding_prefix}_adapter_instance_created": False,
            f"{constructor_binding_prefix}_live_runtime_instantiated": False,
            f"{constructor_binding_prefix}_capacity_entries": 4096,
            f"{constructor_binding_prefix}_issue_lead_tokens": 32,
            f"{constructor_binding_prefix}_queue_deadline_us": 100.0,
            f"{constructor_binding_prefix}_lookahead_us": 2400000.0,
            f"{constructor_binding_prefix}_queue_batch_size": 1,
            f"{constructor_binding_prefix}_shifted_issue_accounting_enabled": True,
            f"{constructor_binding_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{constructor_binding_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{constructor_binding_prefix}_decision": "blocked",
            f"{constructor_binding_prefix}_block_reason": (
                "live_runtime_adapter_constructor_binding_preflight_only"
            ),
            f"{constructor_binding_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_constructor_binding_preflight_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{constructor_binding_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{constructor_binding_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{constructor_binding_prefix}_{key}"] = False
    instance_plan_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_instance_construction_plan"
    )
    constructor_binding_status = str(summary[f"{constructor_binding_prefix}_status"])
    summary.update(
        {
            f"{instance_plan_prefix}_present": True,
            f"{instance_plan_prefix}_stage": (
                "payload_cache_live_runtime_adapter_instance_construction_plan"
            ),
            f"{instance_plan_prefix}_status": (
                "blocked_by_constructor_binding_preflight:"
                f"{constructor_binding_status}"
            ),
            f"{instance_plan_prefix}_consumes_constructor_binding_preflight": True,
            f"{instance_plan_prefix}_constructor_binding_status": (
                constructor_binding_status
            ),
            f"{instance_plan_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{instance_plan_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{instance_plan_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{instance_plan_prefix}_constructor_binding_schema": (
                "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
            ),
            f"{instance_plan_prefix}_instance_construction_plan_schema": (
                "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
            ),
            f"{instance_plan_prefix}_constructor_inputs_bound": True,
            f"{instance_plan_prefix}_construction_plan_sealed": True,
            f"{instance_plan_prefix}_adapter_constructor_call_prepared": True,
            f"{instance_plan_prefix}_adapter_instance_construction_planned": True,
            f"{instance_plan_prefix}_adapter_instance_created": False,
            f"{instance_plan_prefix}_live_runtime_instantiated": False,
            f"{instance_plan_prefix}_capacity_entries": 4096,
            f"{instance_plan_prefix}_issue_lead_tokens": 32,
            f"{instance_plan_prefix}_queue_deadline_us": 100.0,
            f"{instance_plan_prefix}_lookahead_us": 2400000.0,
            f"{instance_plan_prefix}_queue_batch_size": 1,
            f"{instance_plan_prefix}_shifted_issue_accounting_enabled": True,
            f"{instance_plan_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{instance_plan_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{instance_plan_prefix}_decision": "blocked",
            f"{instance_plan_prefix}_block_reason": (
                "live_runtime_adapter_instance_construction_plan_only"
            ),
            f"{instance_plan_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_instance_construction_plan_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{instance_plan_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{instance_plan_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{instance_plan_prefix}_{key}"] = False
    object_shell_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_object_shell_evidence"
    )
    instance_plan_status = str(summary[f"{instance_plan_prefix}_status"])
    summary.update(
        {
            f"{object_shell_prefix}_present": True,
            f"{object_shell_prefix}_stage": (
                "payload_cache_live_runtime_adapter_object_shell_evidence"
            ),
            f"{object_shell_prefix}_status": (
                f"blocked_by_instance_construction_plan:{instance_plan_status}"
            ),
            f"{object_shell_prefix}_consumes_instance_construction_plan": True,
            f"{object_shell_prefix}_instance_construction_plan_status": (
                instance_plan_status
            ),
            f"{object_shell_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{object_shell_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{object_shell_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{object_shell_prefix}_instance_construction_plan_schema": (
                "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
            ),
            f"{object_shell_prefix}_adapter_object_shell_created": True,
            f"{object_shell_prefix}_disabled_adapter_shell_snapshot_created": True,
            f"{object_shell_prefix}_shell_enabled": False,
            f"{object_shell_prefix}_adapter_instance_created": False,
            f"{object_shell_prefix}_live_runtime_instantiated": False,
            f"{object_shell_prefix}_capacity_entries": 4096,
            f"{object_shell_prefix}_issue_lead_tokens": 32,
            f"{object_shell_prefix}_queue_deadline_us": 100.0,
            f"{object_shell_prefix}_lookahead_us": 2400000.0,
            f"{object_shell_prefix}_queue_batch_size": 1,
            f"{object_shell_prefix}_shifted_issue_accounting_enabled": True,
            f"{object_shell_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{object_shell_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{object_shell_prefix}_decision": "blocked",
            f"{object_shell_prefix}_block_reason": (
                "live_runtime_adapter_object_shell_evidence_only"
            ),
            f"{object_shell_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_object_shell_evidence_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{object_shell_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{object_shell_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{object_shell_prefix}_{key}"] = False
    operation_rejection_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_operation_rejection_canary"
    )
    object_shell_status = str(summary[f"{object_shell_prefix}_status"])
    summary.update(
        {
            f"{operation_rejection_prefix}_present": True,
            f"{operation_rejection_prefix}_stage": (
                "payload_cache_live_runtime_adapter_operation_rejection_canary"
            ),
            f"{operation_rejection_prefix}_status": (
                f"blocked_by_object_shell_evidence:{object_shell_status}"
            ),
            f"{operation_rejection_prefix}_consumes_object_shell_evidence": True,
            f"{operation_rejection_prefix}_object_shell_evidence_status": (
                object_shell_status
            ),
            f"{operation_rejection_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{operation_rejection_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{operation_rejection_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{operation_rejection_prefix}_operation_rejection_schema": (
                "ready_time_payload_cache_runtime_adapter_operation_rejection_canary_v1"
            ),
            f"{operation_rejection_prefix}_adapter_object_shell_created": True,
            f"{operation_rejection_prefix}_operation_rejection_canary_ran": True,
            f"{operation_rejection_prefix}_issue_prefetch_rejected": True,
            f"{operation_rejection_prefix}_demand_rejected": True,
            f"{operation_rejection_prefix}_shell_enabled": False,
            f"{operation_rejection_prefix}_adapter_instance_created": False,
            f"{operation_rejection_prefix}_live_runtime_instantiated": False,
            f"{operation_rejection_prefix}_capacity_entries": 4096,
            f"{operation_rejection_prefix}_issue_lead_tokens": 32,
            f"{operation_rejection_prefix}_queue_deadline_us": 100.0,
            f"{operation_rejection_prefix}_lookahead_us": 2400000.0,
            f"{operation_rejection_prefix}_queue_batch_size": 1,
            f"{operation_rejection_prefix}_shifted_issue_accounting_enabled": True,
            f"{operation_rejection_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{operation_rejection_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{operation_rejection_prefix}_decision": "blocked",
            f"{operation_rejection_prefix}_block_reason": (
                "live_runtime_adapter_operation_rejection_canary_only"
            ),
            f"{operation_rejection_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_operation_rejection_canary_disabled"
            ),
        },
    )
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{operation_rejection_prefix}_{key}"] = 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{operation_rejection_prefix}_{key}"] = 0.0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{operation_rejection_prefix}_{key}"] = False
    accounting_dry_run_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_accounting_dry_run_canary"
    )
    operation_rejection_status = str(summary[f"{operation_rejection_prefix}_status"])
    summary.update(
        {
            f"{accounting_dry_run_prefix}_present": True,
            f"{accounting_dry_run_prefix}_stage": (
                "payload_cache_live_runtime_adapter_accounting_dry_run_canary"
            ),
            f"{accounting_dry_run_prefix}_status": (
                f"blocked_by_operation_rejection_canary:{operation_rejection_status}"
            ),
            f"{accounting_dry_run_prefix}_consumes_operation_rejection_canary": True,
            f"{accounting_dry_run_prefix}_operation_rejection_canary_status": (
                operation_rejection_status
            ),
            f"{accounting_dry_run_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{accounting_dry_run_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{accounting_dry_run_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{accounting_dry_run_prefix}_accounting_dry_run_schema": (
                "ready_time_payload_cache_runtime_adapter_accounting_dry_run_canary_v1"
            ),
            f"{accounting_dry_run_prefix}_accounting_dry_run_adapter_created": True,
            f"{accounting_dry_run_prefix}_accounting_dry_run_operations_ran": True,
            f"{accounting_dry_run_prefix}_accounting_dry_run_enabled": True,
            f"{accounting_dry_run_prefix}_issue_prefetch_accepted": True,
            f"{accounting_dry_run_prefix}_duplicate_issue_suppressed": True,
            f"{accounting_dry_run_prefix}_demand_hit": True,
            f"{accounting_dry_run_prefix}_live_adapter_instance_created": False,
            f"{accounting_dry_run_prefix}_live_runtime_instantiated": False,
            f"{accounting_dry_run_prefix}_capacity_entries": 4096,
            f"{accounting_dry_run_prefix}_issue_lead_tokens": 32,
            f"{accounting_dry_run_prefix}_queue_deadline_us": 100.0,
            f"{accounting_dry_run_prefix}_lookahead_us": 2400000.0,
            f"{accounting_dry_run_prefix}_queue_batch_size": 1,
            f"{accounting_dry_run_prefix}_resident_count": 1,
            f"{accounting_dry_run_prefix}_issued_fetch_count": 1,
            f"{accounting_dry_run_prefix}_used_fetch_count": 1,
            f"{accounting_dry_run_prefix}_unused_fetch_count": 0,
            f"{accounting_dry_run_prefix}_demand_count": 1,
            f"{accounting_dry_run_prefix}_demand_hit_count": 1,
            f"{accounting_dry_run_prefix}_demand_miss_count": 0,
            f"{accounting_dry_run_prefix}_evicted_before_use_count": 0,
            f"{accounting_dry_run_prefix}_ready_late_miss_count": 0,
            f"{accounting_dry_run_prefix}_late_completion_unused_count": 0,
            f"{accounting_dry_run_prefix}_queue_batch_count": 1,
            f"{accounting_dry_run_prefix}_shifted_issue_accounting_enabled": True,
            f"{accounting_dry_run_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{accounting_dry_run_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{accounting_dry_run_prefix}_decision": "blocked",
            f"{accounting_dry_run_prefix}_block_reason": (
                "live_runtime_adapter_accounting_dry_run_canary_only"
            ),
            f"{accounting_dry_run_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_accounting_dry_run_canary_payloadless"
            ),
        },
    )
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{accounting_dry_run_prefix}_{key}"] = 0.0
    for key in (
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{accounting_dry_run_prefix}_{key}"] = 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{accounting_dry_run_prefix}_{key}"] = False
    mixed_outcome_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_mixed_outcome_dry_run_canary"
    )
    accounting_dry_run_status = str(summary[f"{accounting_dry_run_prefix}_status"])
    summary.update(
        {
            f"{mixed_outcome_prefix}_present": True,
            f"{mixed_outcome_prefix}_stage": (
                "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary"
            ),
            f"{mixed_outcome_prefix}_status": (
                f"blocked_by_accounting_dry_run_canary:{accounting_dry_run_status}"
            ),
            f"{mixed_outcome_prefix}_consumes_accounting_dry_run_canary": True,
            f"{mixed_outcome_prefix}_accounting_dry_run_canary_status": (
                accounting_dry_run_status
            ),
            f"{mixed_outcome_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{mixed_outcome_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{mixed_outcome_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{mixed_outcome_prefix}_mixed_outcome_schema": (
                "ready_time_payload_cache_runtime_adapter_mixed_outcome_dry_run_canary_v1"
            ),
            f"{mixed_outcome_prefix}_mixed_outcome_adapter_created": True,
            f"{mixed_outcome_prefix}_mixed_outcome_operations_ran": True,
            f"{mixed_outcome_prefix}_accounting_dry_run_enabled": True,
            f"{mixed_outcome_prefix}_issue_prefetch_accepted": True,
            f"{mixed_outcome_prefix}_duplicate_issue_suppressed": True,
            f"{mixed_outcome_prefix}_prefetched_demand_hit": True,
            f"{mixed_outcome_prefix}_unprefetched_demand_hit": False,
            f"{mixed_outcome_prefix}_unprefetched_demand_missed": True,
            f"{mixed_outcome_prefix}_live_adapter_instance_created": False,
            f"{mixed_outcome_prefix}_live_runtime_instantiated": False,
            f"{mixed_outcome_prefix}_capacity_entries": 4096,
            f"{mixed_outcome_prefix}_issue_lead_tokens": 32,
            f"{mixed_outcome_prefix}_queue_deadline_us": 100.0,
            f"{mixed_outcome_prefix}_lookahead_us": 2400000.0,
            f"{mixed_outcome_prefix}_queue_batch_size": 1,
            f"{mixed_outcome_prefix}_resident_count": 2,
            f"{mixed_outcome_prefix}_issued_fetch_count": 1,
            f"{mixed_outcome_prefix}_used_fetch_count": 1,
            f"{mixed_outcome_prefix}_unused_fetch_count": 0,
            f"{mixed_outcome_prefix}_demand_count": 2,
            f"{mixed_outcome_prefix}_demand_hit_count": 1,
            f"{mixed_outcome_prefix}_demand_miss_count": 1,
            f"{mixed_outcome_prefix}_evicted_before_use_count": 0,
            f"{mixed_outcome_prefix}_ready_late_miss_count": 0,
            f"{mixed_outcome_prefix}_late_completion_unused_count": 0,
            f"{mixed_outcome_prefix}_queue_batch_count": 1,
            f"{mixed_outcome_prefix}_shifted_issue_accounting_enabled": True,
            f"{mixed_outcome_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{mixed_outcome_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{mixed_outcome_prefix}_decision": "blocked",
            f"{mixed_outcome_prefix}_block_reason": (
                "live_runtime_adapter_mixed_outcome_dry_run_canary_only"
            ),
            f"{mixed_outcome_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary_payloadless"
            ),
        },
    )
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{mixed_outcome_prefix}_{key}"] = 0.0
    for key in (
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{mixed_outcome_prefix}_{key}"] = 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{mixed_outcome_prefix}_{key}"] = False
    payloadless_instance_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payloadless_instance_canary"
    )
    mixed_outcome_status = str(summary[f"{mixed_outcome_prefix}_status"])
    summary.update(
        {
            f"{payloadless_instance_prefix}_present": True,
            f"{payloadless_instance_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payloadless_instance_canary"
            ),
            f"{payloadless_instance_prefix}_status": (
                f"blocked_by_mixed_outcome_dry_run_canary:{mixed_outcome_status}"
            ),
            f"{payloadless_instance_prefix}_consumes_mixed_outcome_dry_run_canary": True,
            f"{payloadless_instance_prefix}_mixed_outcome_dry_run_canary_status": (
                mixed_outcome_status
            ),
            f"{payloadless_instance_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{payloadless_instance_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{payloadless_instance_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{payloadless_instance_prefix}_payloadless_instance_schema": (
                "ready_time_payload_cache_runtime_adapter_payloadless_instance_canary_v1"
            ),
            f"{payloadless_instance_prefix}_payloadless_live_adapter_created": True,
            f"{payloadless_instance_prefix}_payloadless_live_operations_ran": True,
            f"{payloadless_instance_prefix}_accounting_dry_run_enabled": True,
            f"{payloadless_instance_prefix}_issue_prefetch_accepted": True,
            f"{payloadless_instance_prefix}_duplicate_issue_suppressed": True,
            f"{payloadless_instance_prefix}_prefetched_demand_hit": True,
            f"{payloadless_instance_prefix}_unprefetched_demand_hit": False,
            f"{payloadless_instance_prefix}_unprefetched_demand_missed": True,
            f"{payloadless_instance_prefix}_live_adapter_instance_created": True,
            f"{payloadless_instance_prefix}_live_runtime_instantiated": False,
            f"{payloadless_instance_prefix}_capacity_entries": 4096,
            f"{payloadless_instance_prefix}_issue_lead_tokens": 32,
            f"{payloadless_instance_prefix}_queue_deadline_us": 100.0,
            f"{payloadless_instance_prefix}_lookahead_us": 2400000.0,
            f"{payloadless_instance_prefix}_queue_batch_size": 1,
            f"{payloadless_instance_prefix}_resident_count": 2,
            f"{payloadless_instance_prefix}_issued_fetch_count": 1,
            f"{payloadless_instance_prefix}_used_fetch_count": 1,
            f"{payloadless_instance_prefix}_unused_fetch_count": 0,
            f"{payloadless_instance_prefix}_demand_count": 2,
            f"{payloadless_instance_prefix}_demand_hit_count": 1,
            f"{payloadless_instance_prefix}_demand_miss_count": 1,
            f"{payloadless_instance_prefix}_evicted_before_use_count": 0,
            f"{payloadless_instance_prefix}_ready_late_miss_count": 0,
            f"{payloadless_instance_prefix}_late_completion_unused_count": 0,
            f"{payloadless_instance_prefix}_queue_batch_count": 1,
            f"{payloadless_instance_prefix}_shifted_issue_accounting_enabled": True,
            f"{payloadless_instance_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{payloadless_instance_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{payloadless_instance_prefix}_decision": "blocked",
            f"{payloadless_instance_prefix}_block_reason": (
                "live_runtime_adapter_payloadless_instance_canary_only"
            ),
            f"{payloadless_instance_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payloadless_instance_canary_payloadless"
            ),
        },
    )
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{payloadless_instance_prefix}_{key}"] = 0.0
    for key in (
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{payloadless_instance_prefix}_{key}"] = 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{payloadless_instance_prefix}_{key}"] = False
    payload_transfer_toggle_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_transfer_toggle_disabled_canary"
    )
    payloadless_instance_status = str(summary[f"{payloadless_instance_prefix}_status"])
    summary.update(
        {
            f"{payload_transfer_toggle_prefix}_present": True,
            f"{payload_transfer_toggle_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary"
            ),
            f"{payload_transfer_toggle_prefix}_status": (
                f"blocked_by_payloadless_instance_canary:{payloadless_instance_status}"
            ),
            f"{payload_transfer_toggle_prefix}_consumes_payloadless_instance_canary": True,
            f"{payload_transfer_toggle_prefix}_payloadless_instance_canary_status": (
                payloadless_instance_status
            ),
            f"{payload_transfer_toggle_prefix}_manager_backend": (
                "ReadyTimeExpertCacheManager"
            ),
            f"{payload_transfer_toggle_prefix}_manager_runtime_contract": (
                "ready_time_issue_demand_skeleton_v1"
            ),
            f"{payload_transfer_toggle_prefix}_manager_runtime_mode": (
                "ready_time_payload_cache_skeleton"
            ),
            f"{payload_transfer_toggle_prefix}_payload_transfer_toggle_schema": (
                "ready_time_payload_cache_runtime_payload_transfer_toggle_disabled_canary_v1"
            ),
            f"{payload_transfer_toggle_prefix}_payload_transfer_toggle_created": True,
            f"{payload_transfer_toggle_prefix}_payload_issue_rejected": True,
            f"{payload_transfer_toggle_prefix}_payloadless_live_adapter_created": True,
            f"{payload_transfer_toggle_prefix}_payloadless_live_operations_ran": True,
            f"{payload_transfer_toggle_prefix}_live_adapter_instance_created": True,
            f"{payload_transfer_toggle_prefix}_live_runtime_instantiated": False,
            f"{payload_transfer_toggle_prefix}_capacity_entries": 4096,
            f"{payload_transfer_toggle_prefix}_issue_lead_tokens": 32,
            f"{payload_transfer_toggle_prefix}_queue_deadline_us": 100.0,
            f"{payload_transfer_toggle_prefix}_lookahead_us": 2400000.0,
            f"{payload_transfer_toggle_prefix}_queue_batch_size": 1,
            f"{payload_transfer_toggle_prefix}_resident_count": 2,
            f"{payload_transfer_toggle_prefix}_issued_fetch_count": 1,
            f"{payload_transfer_toggle_prefix}_used_fetch_count": 1,
            f"{payload_transfer_toggle_prefix}_unused_fetch_count": 0,
            f"{payload_transfer_toggle_prefix}_demand_count": 2,
            f"{payload_transfer_toggle_prefix}_demand_hit_count": 1,
            f"{payload_transfer_toggle_prefix}_demand_miss_count": 1,
            f"{payload_transfer_toggle_prefix}_evicted_before_use_count": 0,
            f"{payload_transfer_toggle_prefix}_ready_late_miss_count": 0,
            f"{payload_transfer_toggle_prefix}_late_completion_unused_count": 0,
            f"{payload_transfer_toggle_prefix}_queue_batch_count": 1,
            f"{payload_transfer_toggle_prefix}_shifted_issue_accounting_enabled": True,
            f"{payload_transfer_toggle_prefix}_shifted_issue_accounted_packet_count": 28,
            f"{payload_transfer_toggle_prefix}_shifted_issue_unique_issue_key_count": 16,
            f"{payload_transfer_toggle_prefix}_decision": "blocked",
            f"{payload_transfer_toggle_prefix}_block_reason": (
                "live_runtime_adapter_payload_transfer_toggle_disabled_canary_only"
            ),
            f"{payload_transfer_toggle_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary_payloadless"
            ),
        },
    )
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        summary[f"{payload_transfer_toggle_prefix}_{key}"] = 0.0
    for key in (
        "issued_payload_count",
        "payload_bytes",
    ):
        summary[f"{payload_transfer_toggle_prefix}_{key}"] = 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        summary[f"{payload_transfer_toggle_prefix}_{key}"] = False
    payload_issue_request_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_request_blocked_canary"
    )
    payload_transfer_toggle_status = str(
        summary[f"{payload_transfer_toggle_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_request_prefix}_present": True,
            f"{payload_issue_request_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary"
            ),
            f"{payload_issue_request_prefix}_status": (
                "blocked_by_payload_transfer_toggle_disabled_canary:"
                f"{payload_transfer_toggle_status}"
            ),
            f"{payload_issue_request_prefix}_consumes_payload_transfer_toggle_disabled_canary": True,
            f"{payload_issue_request_prefix}_payload_transfer_toggle_disabled_canary_status": (
                payload_transfer_toggle_status
            ),
            f"{payload_issue_request_prefix}_payload_issue_request_schema": (
                "payload_cache_runtime_payload_issue_request_v1"
            ),
            f"{payload_issue_request_prefix}_payload_issue_request_created": True,
            f"{payload_issue_request_prefix}_payload_issue_rejected": True,
            f"{payload_issue_request_prefix}_request_layer_idx": 0,
            f"{payload_issue_request_prefix}_request_expert_idx": 0,
            f"{payload_issue_request_prefix}_requested_payload_bytes": 64,
            f"{payload_issue_request_prefix}_request_source": (
                "queue_budget_first_model_passing_cell"
            ),
            f"{payload_issue_request_prefix}_source_issue_packet_count": summary[
                "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count"
            ],
            f"{payload_issue_request_prefix}_source_issue_unique_key_count": summary[
                "prefetch_lab_default_stream_queue_budget_first_shifted_issue_unique_issue_key_count"
            ],
            f"{payload_issue_request_prefix}_source_queue_budget_capacity": summary[
                "prefetch_lab_default_stream_queue_budget_first_model_passing_capacity"
            ],
            f"{payload_issue_request_prefix}_source_issue_lead_tokens": summary[
                "prefetch_lab_default_stream_queue_budget_first_model_passing_issue_lead_tokens"
            ],
            f"{payload_issue_request_prefix}_source_queue_deadline_us": summary[
                "prefetch_lab_default_stream_queue_budget_first_model_passing_queue_deadline_us"
            ],
            f"{payload_issue_request_prefix}_issued_payload_count": 0,
            f"{payload_issue_request_prefix}_payload_bytes": 0,
            f"{payload_issue_request_prefix}_decision": "blocked",
            f"{payload_issue_request_prefix}_block_reason": (
                "live_runtime_adapter_payload_issue_request_blocked_canary_only"
            ),
            f"{payload_issue_request_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary_payloadless"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_request_prefix}_{key}"] = False
    payload_issue_plan_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_plan_dry_run"
    )
    payload_issue_request_status = str(summary[f"{payload_issue_request_prefix}_status"])
    summary.update(
        {
            f"{payload_issue_plan_prefix}_present": True,
            f"{payload_issue_plan_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payload_issue_plan_dry_run"
            ),
            f"{payload_issue_plan_prefix}_status": (
                "blocked_by_payload_issue_request_blocked_canary:"
                f"{payload_issue_request_status}"
            ),
            f"{payload_issue_plan_prefix}_consumes_payload_issue_request_blocked_canary": True,
            f"{payload_issue_plan_prefix}_payload_issue_request_blocked_canary_status": (
                payload_issue_request_status
            ),
            f"{payload_issue_plan_prefix}_request_source": summary[
                f"{payload_issue_request_prefix}_request_source"
            ],
            f"{payload_issue_plan_prefix}_request_layer_idx": summary[
                f"{payload_issue_request_prefix}_request_layer_idx"
            ],
            f"{payload_issue_plan_prefix}_request_expert_idx": summary[
                f"{payload_issue_request_prefix}_request_expert_idx"
            ],
            f"{payload_issue_plan_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_request_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_plan_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_request_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_plan_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_request_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_plan_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_request_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_plan_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_request_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_plan_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_request_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_plan_prefix}_planned_issue_count": 0,
            f"{payload_issue_plan_prefix}_issued_payload_count": 0,
            f"{payload_issue_plan_prefix}_payload_bytes": 0,
            f"{payload_issue_plan_prefix}_decision": "blocked",
            f"{payload_issue_plan_prefix}_block_reason": "payload_transfer_disabled",
            f"{payload_issue_plan_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payload_issue_plan_dry_run"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_plan_prefix}_{key}"] = False
    payload_issue_executor_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_executor_dry_run"
    )
    payload_issue_plan_status = str(summary[f"{payload_issue_plan_prefix}_status"])
    summary.update(
        {
            f"{payload_issue_executor_prefix}_present": True,
            f"{payload_issue_executor_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payload_issue_executor_dry_run"
            ),
            f"{payload_issue_executor_prefix}_status": (
                "blocked_by_payload_issue_plan_dry_run:"
                f"{payload_issue_plan_status}"
            ),
            f"{payload_issue_executor_prefix}_consumes_payload_issue_plan_dry_run": True,
            f"{payload_issue_executor_prefix}_payload_issue_plan_status": (
                payload_issue_plan_status
            ),
            f"{payload_issue_executor_prefix}_payload_issue_executor_schema": (
                "payload_cache_runtime_payload_issue_executor_v1"
            ),
            f"{payload_issue_executor_prefix}_payload_issue_executor_created": True,
            f"{payload_issue_executor_prefix}_payload_issue_plan_consumed": True,
            f"{payload_issue_executor_prefix}_request_source": summary[
                f"{payload_issue_plan_prefix}_request_source"
            ],
            f"{payload_issue_executor_prefix}_request_layer_idx": summary[
                f"{payload_issue_plan_prefix}_request_layer_idx"
            ],
            f"{payload_issue_executor_prefix}_request_expert_idx": summary[
                f"{payload_issue_plan_prefix}_request_expert_idx"
            ],
            f"{payload_issue_executor_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_plan_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_executor_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_plan_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_executor_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_plan_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_executor_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_plan_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_executor_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_plan_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_executor_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_plan_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_executor_prefix}_planned_issue_count": 0,
            f"{payload_issue_executor_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_executor_prefix}_issued_payload_count": 0,
            f"{payload_issue_executor_prefix}_payload_bytes": 0,
            f"{payload_issue_executor_prefix}_decision": "blocked",
            f"{payload_issue_executor_prefix}_block_reason": "payload_transfer_disabled",
            f"{payload_issue_executor_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payload_issue_executor_dry_run"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_executor_prefix}_{key}"] = False
    payload_issue_queue_entry_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_queue_entry_dry_run"
    )
    payload_issue_executor_status = str(summary[f"{payload_issue_executor_prefix}_status"])
    summary.update(
        {
            f"{payload_issue_queue_entry_prefix}_present": True,
            f"{payload_issue_queue_entry_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run"
            ),
            f"{payload_issue_queue_entry_prefix}_status": (
                "blocked_by_payload_issue_executor_dry_run:"
                f"{payload_issue_executor_status}"
            ),
            f"{payload_issue_queue_entry_prefix}_consumes_payload_issue_executor_dry_run": True,
            f"{payload_issue_queue_entry_prefix}_payload_issue_executor_status": (
                payload_issue_executor_status
            ),
            f"{payload_issue_queue_entry_prefix}_payload_issue_queue_entry_schema": (
                "payload_cache_runtime_payload_issue_queue_entry_v1"
            ),
            f"{payload_issue_queue_entry_prefix}_payload_issue_queue_entry_created": True,
            f"{payload_issue_queue_entry_prefix}_payload_issue_executor_consumed": True,
            f"{payload_issue_queue_entry_prefix}_queue_entry_shape_checked": True,
            f"{payload_issue_queue_entry_prefix}_queue_entry_enqueued": False,
            f"{payload_issue_queue_entry_prefix}_queue_submit_allowed": False,
            f"{payload_issue_queue_entry_prefix}_request_source": summary[
                f"{payload_issue_executor_prefix}_request_source"
            ],
            f"{payload_issue_queue_entry_prefix}_request_layer_idx": summary[
                f"{payload_issue_executor_prefix}_request_layer_idx"
            ],
            f"{payload_issue_queue_entry_prefix}_request_expert_idx": summary[
                f"{payload_issue_executor_prefix}_request_expert_idx"
            ],
            f"{payload_issue_queue_entry_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_executor_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_queue_entry_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_executor_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_queue_entry_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_executor_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_queue_entry_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_executor_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_queue_entry_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_executor_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_queue_entry_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_executor_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_queue_entry_prefix}_planned_issue_count": 0,
            f"{payload_issue_queue_entry_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_queue_entry_prefix}_queued_issue_count": 0,
            f"{payload_issue_queue_entry_prefix}_issued_payload_count": 0,
            f"{payload_issue_queue_entry_prefix}_payload_bytes": 0,
            f"{payload_issue_queue_entry_prefix}_decision": "blocked",
            f"{payload_issue_queue_entry_prefix}_block_reason": "payload_transfer_disabled",
            f"{payload_issue_queue_entry_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_queue_entry_prefix}_{key}"] = False
    payload_issue_queue_submit_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_queue_submit_blocked_canary"
    )
    payload_issue_queue_entry_status = str(
        summary[f"{payload_issue_queue_entry_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_queue_submit_prefix}_present": True,
            f"{payload_issue_queue_submit_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_queue_submit_blocked_canary"
            ),
            f"{payload_issue_queue_submit_prefix}_status": (
                "blocked_by_payload_issue_queue_entry_dry_run:"
                f"{payload_issue_queue_entry_status}"
            ),
            f"{payload_issue_queue_submit_prefix}_consumes_payload_issue_queue_entry_dry_run": True,
            f"{payload_issue_queue_submit_prefix}_payload_issue_queue_entry_status": (
                payload_issue_queue_entry_status
            ),
            f"{payload_issue_queue_submit_prefix}_payload_issue_queue_submit_schema": (
                "payload_cache_runtime_payload_issue_queue_submit_v1"
            ),
            f"{payload_issue_queue_submit_prefix}_payload_issue_queue_submit_canary_created": True,
            f"{payload_issue_queue_submit_prefix}_payload_issue_queue_entry_consumed": True,
            f"{payload_issue_queue_submit_prefix}_queue_submit_checked": True,
            f"{payload_issue_queue_submit_prefix}_queue_submit_rejected": True,
            f"{payload_issue_queue_submit_prefix}_queue_submit_allowed": False,
            f"{payload_issue_queue_submit_prefix}_queue_entry_enqueued": False,
            f"{payload_issue_queue_submit_prefix}_request_source": summary[
                f"{payload_issue_queue_entry_prefix}_request_source"
            ],
            f"{payload_issue_queue_submit_prefix}_request_layer_idx": summary[
                f"{payload_issue_queue_entry_prefix}_request_layer_idx"
            ],
            f"{payload_issue_queue_submit_prefix}_request_expert_idx": summary[
                f"{payload_issue_queue_entry_prefix}_request_expert_idx"
            ],
            f"{payload_issue_queue_submit_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_queue_entry_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_queue_submit_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_queue_entry_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_queue_submit_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_queue_entry_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_queue_submit_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_queue_entry_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_queue_submit_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_queue_entry_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_queue_submit_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_queue_entry_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_queue_submit_prefix}_planned_issue_count": 0,
            f"{payload_issue_queue_submit_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_queue_submit_prefix}_queued_issue_count": 0,
            f"{payload_issue_queue_submit_prefix}_submitted_issue_count": 0,
            f"{payload_issue_queue_submit_prefix}_issued_payload_count": 0,
            f"{payload_issue_queue_submit_prefix}_payload_bytes": 0,
            f"{payload_issue_queue_submit_prefix}_decision": "blocked",
            f"{payload_issue_queue_submit_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_queue_submit_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_queue_submit_blocked_canary"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_queue_submit_prefix}_{key}"] = False
    payload_issue_inflight_admission_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_inflight_admission_blocked_canary"
    )
    payload_issue_queue_submit_status = str(
        summary[f"{payload_issue_queue_submit_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_inflight_admission_prefix}_present": True,
            f"{payload_issue_inflight_admission_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_inflight_admission_blocked_canary"
            ),
            f"{payload_issue_inflight_admission_prefix}_status": (
                "blocked_by_payload_issue_queue_submit_blocked_canary:"
                f"{payload_issue_queue_submit_status}"
            ),
            f"{payload_issue_inflight_admission_prefix}_consumes_payload_issue_queue_submit_blocked_canary": True,
            f"{payload_issue_inflight_admission_prefix}_payload_issue_queue_submit_status": (
                payload_issue_queue_submit_status
            ),
            f"{payload_issue_inflight_admission_prefix}_payload_issue_inflight_admission_schema": (
                "payload_cache_runtime_payload_issue_inflight_admission_v1"
            ),
            f"{payload_issue_inflight_admission_prefix}_payload_issue_inflight_admission_canary_created": True,
            f"{payload_issue_inflight_admission_prefix}_payload_issue_queue_submit_consumed": True,
            f"{payload_issue_inflight_admission_prefix}_inflight_admission_checked": True,
            f"{payload_issue_inflight_admission_prefix}_inflight_admission_rejected": True,
            f"{payload_issue_inflight_admission_prefix}_inflight_admission_allowed": False,
            f"{payload_issue_inflight_admission_prefix}_inflight_queue_enqueued": False,
            f"{payload_issue_inflight_admission_prefix}_request_source": summary[
                f"{payload_issue_queue_submit_prefix}_request_source"
            ],
            f"{payload_issue_inflight_admission_prefix}_request_layer_idx": summary[
                f"{payload_issue_queue_submit_prefix}_request_layer_idx"
            ],
            f"{payload_issue_inflight_admission_prefix}_request_expert_idx": summary[
                f"{payload_issue_queue_submit_prefix}_request_expert_idx"
            ],
            f"{payload_issue_inflight_admission_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_queue_submit_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_inflight_admission_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_queue_submit_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_inflight_admission_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_queue_submit_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_inflight_admission_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_queue_submit_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_inflight_admission_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_queue_submit_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_inflight_admission_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_queue_submit_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_inflight_admission_prefix}_planned_issue_count": 0,
            f"{payload_issue_inflight_admission_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_inflight_admission_prefix}_queued_issue_count": 0,
            f"{payload_issue_inflight_admission_prefix}_submitted_issue_count": 0,
            f"{payload_issue_inflight_admission_prefix}_inflight_issue_count": 0,
            f"{payload_issue_inflight_admission_prefix}_issued_payload_count": 0,
            f"{payload_issue_inflight_admission_prefix}_payload_bytes": 0,
            f"{payload_issue_inflight_admission_prefix}_decision": "blocked",
            f"{payload_issue_inflight_admission_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_inflight_admission_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_inflight_admission_blocked_canary"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_inflight_admission_prefix}_{key}"] = False
    payload_issue_scheduler_dispatch_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary"
    )
    payload_issue_inflight_admission_status = str(
        summary[f"{payload_issue_inflight_admission_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_scheduler_dispatch_prefix}_present": True,
            f"{payload_issue_scheduler_dispatch_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_scheduler_dispatch_blocked_canary"
            ),
            f"{payload_issue_scheduler_dispatch_prefix}_status": (
                "blocked_by_payload_issue_inflight_admission_blocked_canary:"
                f"{payload_issue_inflight_admission_status}"
            ),
            f"{payload_issue_scheduler_dispatch_prefix}_consumes_payload_issue_inflight_admission_blocked_canary": True,
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_inflight_admission_status": (
                payload_issue_inflight_admission_status
            ),
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_scheduler_dispatch_schema": (
                "payload_cache_runtime_payload_issue_scheduler_dispatch_v1"
            ),
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_scheduler_dispatch_canary_created": True,
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_inflight_admission_consumed": True,
            f"{payload_issue_scheduler_dispatch_prefix}_scheduler_dispatch_checked": True,
            f"{payload_issue_scheduler_dispatch_prefix}_scheduler_dispatch_rejected": True,
            f"{payload_issue_scheduler_dispatch_prefix}_scheduler_dispatch_allowed": False,
            f"{payload_issue_scheduler_dispatch_prefix}_scheduler_dispatch_enqueued": False,
            f"{payload_issue_scheduler_dispatch_prefix}_request_source": summary[
                f"{payload_issue_inflight_admission_prefix}_request_source"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_request_layer_idx": summary[
                f"{payload_issue_inflight_admission_prefix}_request_layer_idx"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_request_expert_idx": summary[
                f"{payload_issue_inflight_admission_prefix}_request_expert_idx"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_inflight_admission_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_inflight_admission_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_inflight_admission_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_inflight_admission_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_inflight_admission_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_inflight_admission_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_scheduler_dispatch_prefix}_planned_issue_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_queued_issue_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_submitted_issue_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_inflight_issue_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_dispatched_issue_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_issued_payload_count": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_payload_bytes": 0,
            f"{payload_issue_scheduler_dispatch_prefix}_decision": "blocked",
            f"{payload_issue_scheduler_dispatch_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_scheduler_dispatch_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_scheduler_dispatch_blocked_canary"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_scheduler_dispatch_prefix}_{key}"] = False
    payload_issue_command_packet_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_command_packet_dry_run"
    )
    payload_issue_scheduler_dispatch_status = str(
        summary[f"{payload_issue_scheduler_dispatch_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_command_packet_prefix}_present": True,
            f"{payload_issue_command_packet_prefix}_stage": (
                "payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run"
            ),
            f"{payload_issue_command_packet_prefix}_status": (
                "blocked_by_payload_issue_scheduler_dispatch_blocked_canary:"
                f"{payload_issue_scheduler_dispatch_status}"
            ),
            f"{payload_issue_command_packet_prefix}_consumes_payload_issue_scheduler_dispatch_blocked_canary": True,
            f"{payload_issue_command_packet_prefix}_payload_issue_scheduler_dispatch_status": (
                payload_issue_scheduler_dispatch_status
            ),
            f"{payload_issue_command_packet_prefix}_payload_issue_command_packet_schema": (
                "payload_cache_runtime_payload_issue_command_packet_v1"
            ),
            f"{payload_issue_command_packet_prefix}_payload_issue_command_packet_created": True,
            f"{payload_issue_command_packet_prefix}_payload_issue_scheduler_dispatch_consumed": True,
            f"{payload_issue_command_packet_prefix}_command_packet_shape_checked": True,
            f"{payload_issue_command_packet_prefix}_command_packet_submitted": False,
            f"{payload_issue_command_packet_prefix}_command_packet_executed": False,
            f"{payload_issue_command_packet_prefix}_request_source": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_request_source"
            ],
            f"{payload_issue_command_packet_prefix}_request_layer_idx": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_request_layer_idx"
            ],
            f"{payload_issue_command_packet_prefix}_request_expert_idx": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_request_expert_idx"
            ],
            f"{payload_issue_command_packet_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_command_packet_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_command_packet_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_command_packet_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_command_packet_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_command_packet_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_scheduler_dispatch_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_command_packet_prefix}_planned_issue_count": 0,
            f"{payload_issue_command_packet_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_command_packet_prefix}_queued_issue_count": 0,
            f"{payload_issue_command_packet_prefix}_submitted_issue_count": 0,
            f"{payload_issue_command_packet_prefix}_inflight_issue_count": 0,
            f"{payload_issue_command_packet_prefix}_dispatched_issue_count": 0,
            f"{payload_issue_command_packet_prefix}_command_packet_count": 0,
            f"{payload_issue_command_packet_prefix}_issued_payload_count": 0,
            f"{payload_issue_command_packet_prefix}_payload_bytes": 0,
            f"{payload_issue_command_packet_prefix}_decision": "blocked",
            f"{payload_issue_command_packet_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_command_packet_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_command_packet_prefix}_{key}"] = False
    payload_issue_transport_enqueue_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary"
    )
    payload_issue_command_packet_status = str(
        summary[f"{payload_issue_command_packet_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_transport_enqueue_prefix}_present": True,
            f"{payload_issue_transport_enqueue_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_transport_enqueue_blocked_canary"
            ),
            f"{payload_issue_transport_enqueue_prefix}_status": (
                "blocked_by_payload_issue_command_packet_dry_run:"
                f"{payload_issue_command_packet_status}"
            ),
            f"{payload_issue_transport_enqueue_prefix}_consumes_payload_issue_command_packet_dry_run": True,
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_command_packet_status": (
                payload_issue_command_packet_status
            ),
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_transport_enqueue_schema": (
                "payload_cache_runtime_payload_issue_transport_enqueue_v1"
            ),
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_transport_enqueue_canary_created": True,
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_command_packet_consumed": True,
            f"{payload_issue_transport_enqueue_prefix}_transport_enqueue_checked": True,
            f"{payload_issue_transport_enqueue_prefix}_transport_enqueue_rejected": True,
            f"{payload_issue_transport_enqueue_prefix}_transport_enqueue_allowed": False,
            f"{payload_issue_transport_enqueue_prefix}_transport_work_enqueued": False,
            f"{payload_issue_transport_enqueue_prefix}_request_source": summary[
                f"{payload_issue_command_packet_prefix}_request_source"
            ],
            f"{payload_issue_transport_enqueue_prefix}_request_layer_idx": summary[
                f"{payload_issue_command_packet_prefix}_request_layer_idx"
            ],
            f"{payload_issue_transport_enqueue_prefix}_request_expert_idx": summary[
                f"{payload_issue_command_packet_prefix}_request_expert_idx"
            ],
            f"{payload_issue_transport_enqueue_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_command_packet_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_transport_enqueue_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_command_packet_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_transport_enqueue_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_command_packet_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_transport_enqueue_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_command_packet_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_transport_enqueue_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_command_packet_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_transport_enqueue_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_command_packet_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_transport_enqueue_prefix}_planned_issue_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_queued_issue_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_submitted_issue_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_inflight_issue_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_dispatched_issue_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_command_packet_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_transport_work_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_issued_payload_count": 0,
            f"{payload_issue_transport_enqueue_prefix}_payload_bytes": 0,
            f"{payload_issue_transport_enqueue_prefix}_decision": "blocked",
            f"{payload_issue_transport_enqueue_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_transport_enqueue_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_transport_enqueue_blocked_canary"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_transport_enqueue_prefix}_{key}"] = False
    payload_issue_transport_worker_dispatch_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary"
    )
    payload_issue_transport_enqueue_status = str(
        summary[f"{payload_issue_transport_enqueue_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_transport_worker_dispatch_prefix}_present": True,
            f"{payload_issue_transport_worker_dispatch_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_transport_worker_dispatch_blocked_canary"
            ),
            f"{payload_issue_transport_worker_dispatch_prefix}_status": (
                "blocked_by_payload_issue_transport_enqueue_blocked_canary:"
                f"{payload_issue_transport_enqueue_status}"
            ),
            f"{payload_issue_transport_worker_dispatch_prefix}_consumes_payload_issue_transport_enqueue_blocked_canary": True,
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_enqueue_status": (
                payload_issue_transport_enqueue_status
            ),
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_worker_dispatch_schema": (
                "payload_cache_runtime_payload_issue_transport_worker_dispatch_v1"
            ),
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_worker_dispatch_canary_created": True,
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_enqueue_consumed": True,
            f"{payload_issue_transport_worker_dispatch_prefix}_transport_worker_dispatch_checked": True,
            f"{payload_issue_transport_worker_dispatch_prefix}_transport_worker_dispatch_rejected": True,
            f"{payload_issue_transport_worker_dispatch_prefix}_transport_worker_dispatch_allowed": False,
            f"{payload_issue_transport_worker_dispatch_prefix}_transport_worker_dispatched": False,
            f"{payload_issue_transport_worker_dispatch_prefix}_request_source": summary[
                f"{payload_issue_transport_enqueue_prefix}_request_source"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_request_layer_idx": summary[
                f"{payload_issue_transport_enqueue_prefix}_request_layer_idx"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_request_expert_idx": summary[
                f"{payload_issue_transport_enqueue_prefix}_request_expert_idx"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_transport_enqueue_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_transport_enqueue_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_transport_enqueue_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_transport_enqueue_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_transport_enqueue_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_transport_enqueue_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_transport_worker_dispatch_prefix}_planned_issue_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_queued_issue_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_submitted_issue_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_inflight_issue_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_dispatched_issue_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_command_packet_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_transport_work_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_transport_worker_dispatch_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_issued_payload_count": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_bytes": 0,
            f"{payload_issue_transport_worker_dispatch_prefix}_decision": "blocked",
            f"{payload_issue_transport_worker_dispatch_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_transport_worker_dispatch_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_transport_worker_dispatch_blocked_canary"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_transport_worker_dispatch_prefix}_{key}"] = False
    payload_issue_copy_descriptor_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_copy_descriptor_dry_run"
    )
    payload_issue_transport_worker_dispatch_status = str(
        summary[f"{payload_issue_transport_worker_dispatch_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_copy_descriptor_prefix}_present": True,
            f"{payload_issue_copy_descriptor_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_copy_descriptor_dry_run"
            ),
            f"{payload_issue_copy_descriptor_prefix}_status": (
                "blocked_by_payload_issue_transport_worker_dispatch_blocked_canary:"
                f"{payload_issue_transport_worker_dispatch_status}"
            ),
            f"{payload_issue_copy_descriptor_prefix}_consumes_payload_issue_transport_worker_dispatch_blocked_canary": True,
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_transport_worker_dispatch_status": (
                payload_issue_transport_worker_dispatch_status
            ),
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_copy_descriptor_schema": (
                "payload_cache_runtime_payload_issue_copy_descriptor_v1"
            ),
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_copy_descriptor_created": True,
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_transport_worker_dispatch_consumed": True,
            f"{payload_issue_copy_descriptor_prefix}_copy_descriptor_shape_checked": True,
            f"{payload_issue_copy_descriptor_prefix}_copy_descriptor_submitted": False,
            f"{payload_issue_copy_descriptor_prefix}_copy_descriptor_executed": False,
            f"{payload_issue_copy_descriptor_prefix}_request_source": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_request_source"
            ],
            f"{payload_issue_copy_descriptor_prefix}_request_layer_idx": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_request_layer_idx"
            ],
            f"{payload_issue_copy_descriptor_prefix}_request_expert_idx": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_request_expert_idx"
            ],
            f"{payload_issue_copy_descriptor_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_copy_descriptor_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_copy_descriptor_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_copy_descriptor_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_copy_descriptor_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_copy_descriptor_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_transport_worker_dispatch_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_copy_descriptor_prefix}_planned_issue_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_queued_issue_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_submitted_issue_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_inflight_issue_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_dispatched_issue_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_command_packet_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_transport_work_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_transport_worker_dispatch_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_copy_descriptor_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_issued_payload_count": 0,
            f"{payload_issue_copy_descriptor_prefix}_payload_bytes": 0,
            f"{payload_issue_copy_descriptor_prefix}_decision": "blocked",
            f"{payload_issue_copy_descriptor_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_copy_descriptor_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_copy_descriptor_dry_run"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_copy_descriptor_prefix}_{key}"] = False
    payload_issue_copy_descriptor_submit_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary"
    )
    payload_issue_copy_descriptor_status = str(
        summary[f"{payload_issue_copy_descriptor_prefix}_status"],
    )
    summary.update(
        {
            f"{payload_issue_copy_descriptor_submit_prefix}_present": True,
            f"{payload_issue_copy_descriptor_submit_prefix}_stage": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_copy_descriptor_submit_blocked_canary"
            ),
            f"{payload_issue_copy_descriptor_submit_prefix}_status": (
                "blocked_by_payload_issue_copy_descriptor_dry_run:"
                f"{payload_issue_copy_descriptor_status}"
            ),
            f"{payload_issue_copy_descriptor_submit_prefix}_consumes_payload_issue_copy_descriptor_dry_run": True,
            f"{payload_issue_copy_descriptor_submit_prefix}_payload_issue_copy_descriptor_status": (
                payload_issue_copy_descriptor_status
            ),
            f"{payload_issue_copy_descriptor_submit_prefix}_payload_issue_copy_descriptor_submit_schema": (
                "payload_cache_runtime_payload_issue_copy_descriptor_submit_v1"
            ),
            f"{payload_issue_copy_descriptor_submit_prefix}_payload_issue_copy_descriptor_submit_canary_created": True,
            f"{payload_issue_copy_descriptor_submit_prefix}_payload_issue_copy_descriptor_consumed": True,
            f"{payload_issue_copy_descriptor_submit_prefix}_copy_descriptor_submit_checked": True,
            f"{payload_issue_copy_descriptor_submit_prefix}_copy_descriptor_submit_rejected": True,
            f"{payload_issue_copy_descriptor_submit_prefix}_copy_descriptor_submit_allowed": False,
            f"{payload_issue_copy_descriptor_submit_prefix}_copy_descriptor_submitted": False,
            f"{payload_issue_copy_descriptor_submit_prefix}_copy_descriptor_executed": False,
            f"{payload_issue_copy_descriptor_submit_prefix}_request_source": summary[
                f"{payload_issue_copy_descriptor_prefix}_request_source"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_request_layer_idx": summary[
                f"{payload_issue_copy_descriptor_prefix}_request_layer_idx"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_request_expert_idx": summary[
                f"{payload_issue_copy_descriptor_prefix}_request_expert_idx"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_requested_payload_bytes": summary[
                f"{payload_issue_copy_descriptor_prefix}_requested_payload_bytes"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_source_issue_packet_count": summary[
                f"{payload_issue_copy_descriptor_prefix}_source_issue_packet_count"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_source_issue_unique_key_count": summary[
                f"{payload_issue_copy_descriptor_prefix}_source_issue_unique_key_count"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_source_queue_budget_capacity": summary[
                f"{payload_issue_copy_descriptor_prefix}_source_queue_budget_capacity"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_source_issue_lead_tokens": summary[
                f"{payload_issue_copy_descriptor_prefix}_source_issue_lead_tokens"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_source_queue_deadline_us": summary[
                f"{payload_issue_copy_descriptor_prefix}_source_queue_deadline_us"
            ],
            f"{payload_issue_copy_descriptor_submit_prefix}_planned_issue_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_scheduled_issue_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_queued_issue_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_submitted_issue_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_inflight_issue_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_dispatched_issue_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_command_packet_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_transport_work_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_transport_worker_dispatch_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_copy_descriptor_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_issued_payload_count": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_payload_bytes": 0,
            f"{payload_issue_copy_descriptor_submit_prefix}_decision": "blocked",
            f"{payload_issue_copy_descriptor_submit_prefix}_block_reason": (
                "payload_transfer_disabled"
            ),
            f"{payload_issue_copy_descriptor_submit_prefix}_execution_mode": (
                "payload_cache_live_runtime_adapter_"
                "payload_issue_copy_descriptor_submit_blocked_canary"
            ),
        },
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        summary[f"{payload_issue_copy_descriptor_submit_prefix}_{key}"] = False
    return summary


def test_check_premap_lab_preflight_summary_accepts_valid_summary() -> None:
    result = check_premap_lab_preflight_summary(_summary())

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["online_merged_source_count"] == 32
    assert result["online_merged_row_count"] == 1841
    assert result["online_merged_device"] == 1
    assert result["expected_online_merged_device"] == 1
    assert result["online_merged_mirror_field"] == "scale_metadata_handle"


def test_check_premap_lab_preflight_summary_accepts_queue_budget_early_first_lead() -> None:
    summary = _summary()
    for key in tuple(summary):
        if key.startswith("prefetch_lab_default_stream_queue_budget_"):
            if key.endswith("issue_lead_tokens"):
                summary[key] = 8
            elif key.endswith("lookahead_us"):
                summary[key] = 600000.0

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_accepts_stream_model_satisfied_runtime_disabled() -> None:
    summary = _summary()
    summary.update(
        {
            "prefetch_lab_default_stream_decision": (
                "model_stream_ready_time_satisfied_runtime_still_disabled"
            ),
            "prefetch_lab_default_stream_full_fetch_block_reason": (
                "real_payload_runtime_not_enabled"
            ),
            "prefetch_lab_default_stream_current_runtime_satisfies_model": True,
            "prefetch_lab_default_stream_metadata_premap_runtime_preferred": False,
            "prefetch_lab_default_stream_current_lookahead_us": 2400000.0,
            "prefetch_lab_default_stream_required_lookahead_us": 2400000.0,
            "prefetch_lab_default_stream_lookahead_deficit_us": 0.0,
        }
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


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


def test_check_premap_lab_preflight_summary_accepts_variant_execution_next_stage() -> None:
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
    _enable_variant_execution_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_accepts_useful_consumer_next_stage() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_accepts_payloadless_useful_execution_next_stage() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    _enable_payloadless_useful_execution_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_accepts_payloadless_useful_repeat_next_stage() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    _enable_payloadless_useful_execution_ready(summary)
    _enable_payloadless_useful_repeat_benchmark_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_gate_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_premap_lab_preflight_summary_rejects_payloadless_useful_repeat_hash_mismatch() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    _enable_payloadless_useful_execution_ready(summary)
    _enable_payloadless_useful_repeat_benchmark_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_gate_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
    )
    summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_descriptor_ptr_field_hash"
    ] = "ffffffffffffffff"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "future_wna16_payloadless_useful_repeat_benchmark_ready_reported_without_valid_evidence"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_descriptor_ptr_execution_field_hash_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_payloadless_useful_unbound_paths() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    _enable_payloadless_useful_execution_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
    )
    summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_useful_consumer_json"
    ] = "outputs/reports/premap_kernel_consumer/other_useful.json"
    summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_json"
    ] = "outputs/reports/premap_kernel_consumer/other_stub.json"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "future_wna16_payloadless_useful_execution_ready_reported_without_valid_evidence"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_useful_consumer_json_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_json_useful_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_useful_consumer_without_field_coverage() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
    )
    summary.pop(
        "default_kernel_consumer_future_wna16_useful_consumer_descriptor_ptr_field_hash"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "future_wna16_useful_consumer_ready_reported_without_valid_evidence"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_future_wna16_useful_consumer_descriptor_ptr_field_hash_invalid"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_useful_consumer_unbound_timing_stub() -> None:
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
    _enable_variant_execution_ready(summary)
    _enable_useful_consumer_ready(summary)
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
    )
    summary[
        "default_kernel_consumer_future_wna16_useful_consumer_native_timing_json"
    ] = "outputs/reports/premap_kernel_consumer/other_timing.json"
    summary[
        "default_kernel_consumer_future_wna16_useful_consumer_native_stub_json"
    ] = "outputs/reports/premap_kernel_consumer/other_stub.json"

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "future_wna16_useful_consumer_ready_reported_without_valid_evidence"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_future_wna16_useful_consumer_native_timing_json_mismatch"
        in result["failures"]
    )
    assert (
        "default_kernel_consumer_future_wna16_useful_consumer_native_stub_json_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_variant_execution_without_payloadless_chain() -> None:
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
    _enable_variant_execution_ready(summary)
    summary["default_kernel_consumer_future_wna16_payloadless_execution_ready"] = False
    summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = True
    summary["default_kernel_consumer_next_runtime_stage"] = (
        "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "future_wna16_variant_execution_ready_reported_without_valid_evidence"
        in result["failures"]
    )
    assert (
        "payloadless_chain_ready_reported_without_valid_evidence"
        in result["failures"]
    )


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


def test_check_premap_lab_preflight_summary_rejects_direct_snapshot_source_mismatch() -> None:
    summary = _summary()
    summary[
        "prefetch_lab_default_ready_time_direct_snapshot_issue_sources"
    ] = [
        "prelaunch_observed_transition_premap_shadow",
        "current_router_topk_premap_shadow",
    ]

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_ready_time_direct_snapshot_issue_sources_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_direct_snapshot_bool_as_int() -> None:
    summary = _summary()
    summary["prefetch_lab_default_ready_time_direct_snapshot_report_present"] = 1

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_ready_time_direct_snapshot_report_present_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_direct_snapshot_int_as_bool() -> None:
    summary = _summary()
    summary["prefetch_lab_default_ready_time_direct_snapshot_payload_bytes"] = False

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_ready_time_direct_snapshot_payload_bytes_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_participation_source_mismatch() -> None:
    summary = _summary()
    summary[
        "prefetch_lab_default_payload_cache_runtime_participation_issue_sources"
    ] = [
        "previous_token_transition_premap_shadow",
    ]

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_participation_issue_sources_do_not_match_direct_snapshot"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_participation_int_as_bool() -> None:
    summary = _summary()
    summary[
        "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes"
    ] = False

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_non_ready_time_participation_status() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_participation_status"] = (
        "accounting_only_not_ready_time_manager:resident"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_participation_status_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_plan_payload_int_as_bool() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_plan_payload_bytes"] = False

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_payload_bytes_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_plan_issue_count_int_as_bool() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_plan_planned_issue_count"] = (
        False
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_planned_issue_count_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_plan_side_effects() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_plan_ready_credit"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_ready_credit_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_ready_credit_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_non_ready_time_runtime_plan_status() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_plan_status"] = (
        "participation_not_full_fetch_candidate:accounting_only_not_ready_time_manager:resident"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_status_type_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_plan_status_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_plan_status"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    summary["prefetch_lab_default_payload_cache_runtime_execution_plan_status"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    summary["prefetch_lab_default_payload_cache_runtime_execution_block_reason"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    summary["prefetch_lab_default_payload_cache_runtime_execution_status"] = (
        "blocked_by_runtime_plan:"
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_status_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_accepts_runtime_plan_lab_gate_block_status() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_participation_status"] = (
        "ready_time_candidate_requires_lab_gate"
    )
    summary["prefetch_lab_default_payload_cache_runtime_plan_status"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    summary["prefetch_lab_default_payload_cache_runtime_execution_plan_status"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    summary["prefetch_lab_default_payload_cache_runtime_execution_block_reason"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    summary["prefetch_lab_default_payload_cache_runtime_execution_status"] = (
        "blocked_by_runtime_plan:"
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True


def test_check_premap_lab_preflight_summary_rejects_runtime_execution_status_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_execution_status"] = (
        "blocked_by_runtime_plan:"
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_status_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_execution_plan_status_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_execution_plan_status"] = (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_plan_status_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_execution_decision_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_execution_decision"] = None

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_decision_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_execution_block_reason_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_execution_block_reason"] = (
        "stale_reason"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_block_reason_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_execution_execution_mode_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_execution_execution_mode"] = (
        "payloadful_runtime"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_execution_mode_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_execution_side_effects() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_execution_payload_bytes"] = 1
    summary["prefetch_lab_default_payload_cache_runtime_execution_ready_credit"] = True
    summary[
        "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_ready_credit_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_runtime_plan_candidate_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_payload_cache_runtime_participation_status"] = (
        "ready_time_candidate_requires_lab_gate"
    )
    summary["prefetch_lab_default_payload_cache_runtime_plan_status"] = (
        "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_payload_cache_runtime_plan_status_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_accepts_ready_time_decision_gate_block() -> None:
    summary = _summary()
    summary.update(
        {
            "prefetch_lab_default_ready_time_decision_reason": (
                "insufficient_ready_time_and_lookahead"
            ),
            "prefetch_lab_default_ready_time_threshold_failures": [],
            "prefetch_lab_default_ready_time_demand_hit_rate": None,
            "prefetch_lab_default_ready_time_ready_late_miss_rate": None,
            "prefetch_lab_default_ready_time_used_per_issued_fetch": None,
            "prefetch_lab_default_ready_time_issued_fetch_count": None,
            "prefetch_lab_default_ready_time_used_fetch_count": None,
            "prefetch_lab_default_ready_time_current_deadline_us": 200.0,
            "prefetch_lab_default_ready_time_current_lookahead_us": 0.0,
            "prefetch_lab_default_ready_time_first_model_passing_deadline_us": 4000.0,
            "prefetch_lab_default_ready_time_first_model_passing_lookahead_us": 3800.0,
            "prefetch_lab_default_ready_time_required_lookahead_slack_us": 4000.0,
            "prefetch_lab_default_ready_time_required_issue_to_demand_lookahead_us": (
                3800.0
            ),
            "prefetch_lab_default_ready_time_slack_deficit_us": 3800.0,
            "prefetch_lab_default_ready_time_lookahead_deficit_us": 3800.0,
            "prefetch_lab_default_ready_time_model_slack_satisfied": False,
            "prefetch_lab_default_ready_time_model_lookahead_satisfied": False,
            "prefetch_lab_default_ready_time_any_model_route_satisfied": False,
        }
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is True


def test_check_premap_lab_preflight_summary_rejects_ready_time_deficit_mismatch() -> None:
    summary = _summary()
    summary.update(
        {
            "prefetch_lab_default_ready_time_decision_reason": (
                "insufficient_ready_time_and_lookahead"
            ),
            "prefetch_lab_default_ready_time_threshold_failures": [],
            "prefetch_lab_default_ready_time_demand_hit_rate": None,
            "prefetch_lab_default_ready_time_ready_late_miss_rate": None,
            "prefetch_lab_default_ready_time_used_per_issued_fetch": None,
            "prefetch_lab_default_ready_time_issued_fetch_count": None,
            "prefetch_lab_default_ready_time_used_fetch_count": None,
            "prefetch_lab_default_ready_time_current_deadline_us": 200.0,
            "prefetch_lab_default_ready_time_current_lookahead_us": 0.0,
            "prefetch_lab_default_ready_time_first_model_passing_deadline_us": 4000.0,
            "prefetch_lab_default_ready_time_first_model_passing_lookahead_us": 3800.0,
            "prefetch_lab_default_ready_time_required_lookahead_slack_us": 4000.0,
            "prefetch_lab_default_ready_time_required_issue_to_demand_lookahead_us": (
                3800.0
            ),
            "prefetch_lab_default_ready_time_slack_deficit_us": 1.0,
            "prefetch_lab_default_ready_time_lookahead_deficit_us": 3800.0,
            "prefetch_lab_default_ready_time_model_slack_satisfied": False,
            "prefetch_lab_default_ready_time_model_lookahead_satisfied": False,
            "prefetch_lab_default_ready_time_any_model_route_satisfied": False,
        }
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_ready_time_slack_deficit_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_stream_full_fetch_allow() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_full_fetch_runtime_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_stream_full_fetch_runtime_allowed_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_stream_wrong_timing_mode() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_lead_token_sweep_event_timing_mode"] = (
        "packet_index"
    )

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_stream_lead_token_sweep_event_timing_mode_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_stream_required_shifted_issue_gap() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_required_shifted_issue_lead_tokens"] = 16
    summary["prefetch_lab_default_stream_required_shifted_issue_invalid_export_count"] = 1
    summary[
        "prefetch_lab_default_stream_required_shifted_issue_row_shift_mismatch_count"
    ] = 1

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_stream_required_shifted_issue_lead_tokens_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_required_shifted_issue_invalid_export_count_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_required_shifted_issue_row_shift_mismatch_count_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_required_shifted_issue_lead_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_shifted_issue_contract_gap() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_shifted_issue_replay_contract_passed"] = False
    summary["prefetch_lab_default_stream_shifted_issue_replay_schedulable_packet_count"] = 27
    summary["prefetch_lab_default_stream_shifted_issue_replay_row_shift_mismatch_count"] = 1
    summary["prefetch_lab_default_stream_shifted_issue_replay_row_clamp_mismatch_count"] = 1

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_contract_passed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_schedulable_packet_count_below_min"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_row_shift_mismatch_count_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_row_clamp_mismatch_count_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_shifted_issue_payload_or_wna16() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_shifted_issue_replay_payload_bytes"] = 64
    summary["prefetch_lab_default_stream_shifted_issue_replay_source_payload_bytes"] = 64
    summary[
        "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_runtime_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_allowed"
    ] = True
    summary["prefetch_lab_default_stream_shifted_issue_replay_uses_current_wna16_args"] = True
    summary["prefetch_lab_default_stream_shifted_issue_replay_current_wna16_arg_compatible"] = True
    summary[
        "prefetch_lab_default_stream_shifted_issue_replay_requires_wna16_arg_reinterpretation"
    ] = True
    summary["prefetch_lab_default_stream_shifted_issue_replay_source_uses_current_wna16_args"] = True
    summary[
        "prefetch_lab_default_stream_shifted_issue_replay_source_current_wna16_arg_compatible"
    ] = True
    summary[
        "prefetch_lab_default_stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation"
    ] = True
    summary["prefetch_lab_default_stream_shifted_issue_replay_wna16_benchmark_ready"] = True
    summary["prefetch_lab_default_stream_shifted_issue_replay_source_wna16_benchmark_ready"] = True
    summary["prefetch_lab_default_stream_shifted_issue_replay_measures_tpot"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_runtime_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_uses_current_wna16_args_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_current_wna16_arg_compatible_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_requires_wna16_arg_reinterpretation_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_source_uses_current_wna16_args_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_source_current_wna16_arg_compatible_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_wna16_benchmark_ready_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_source_wna16_benchmark_ready_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_measures_tpot_mismatch"
        in result["failures"]
    )


def test_check_premap_lab_preflight_summary_rejects_stream_queue_budget_mismatch() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_queue_budget_passed"] = False
    summary["prefetch_lab_default_stream_queue_budget_payload_bytes"] = 64
    summary["prefetch_lab_default_stream_queue_budget_issued_payload_count"] = 1
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_enabled"
    ] = True
    summary["prefetch_lab_default_stream_queue_budget_payload_transfer_enabled"] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_payload_transfer_runtime_enabled"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_payload_deref_runtime_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_present"
    ] = False
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_bytes"
    ] = 64
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_issued_payload_count"
    ] = 1
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_live_payload_runtime_enabled"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_transfer_runtime_enabled"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_deref_runtime_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_full_fetch_runtime_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_live_runtime_instantiated"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_present"
    ] = False
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_bytes"
    ] = 64
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_live_payload_runtime_enabled"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_capacity_entries"
    ] = 8192
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_present"
    ] = False
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_bytes"
    ] = 64
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_artifact_present"
    ] = False
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_artifact_capacity_entries"
    ] = 8192
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_bytes"
    ] = 64
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_deref_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_present"
    ] = False
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_capacity_entries"
    ] = 8192
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_runtime_instantiated"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_bytes"
    ] = 64
    summary[
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed"
    ] = True
    summary["prefetch_lab_default_stream_queue_budget_full_fetch_allowed"] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_full_fetch_runtime_allowed"
    ] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_first_model_passing_issue_lead_tokens"
    ] = 0
    summary[
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count"
    ] = 27
    summary["prefetch_lab_default_stream_queue_budget_measures_tpot"] = True
    summary[
        "prefetch_lab_default_stream_queue_budget_live_runtime_instantiated"
    ] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert "prefetch_lab_default_stream_queue_budget_passed_mismatch" in result[
        "failures"
    ]
    assert "prefetch_lab_default_stream_queue_budget_payload_bytes_mismatch" in result[
        "failures"
    ]
    assert (
        "prefetch_lab_default_stream_queue_budget_payload_transfer_enabled_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_issued_payload_count_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_enabled_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_payload_transfer_runtime_enabled_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_payload_deref_runtime_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_present_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_issued_payload_count_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_live_payload_runtime_enabled_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_transfer_runtime_enabled_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_deref_runtime_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_full_fetch_runtime_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_live_runtime_instantiated_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_present_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_live_payload_runtime_enabled_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_capacity_entries_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_present_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_artifact_present_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_artifact_capacity_entries_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_deref_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_present_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_capacity_entries_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_runtime_instantiated_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed_mismatch"
        in result["failures"]
    )
    assert "prefetch_lab_default_stream_queue_budget_full_fetch_allowed_mismatch" in result[
        "failures"
    ]
    assert (
        "prefetch_lab_default_stream_queue_budget_full_fetch_runtime_allowed_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_live_runtime_instantiated_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_first_model_passing_issue_lead_tokens_invalid"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count_mismatch"
        in result["failures"]
    )
    assert "prefetch_lab_default_stream_queue_budget_measures_tpot_mismatch" in result[
        "failures"
    ]


def test_check_premap_lab_preflight_summary_rejects_object_preflight_escape() -> None:
    summary = _summary()
    prefix = "prefetch_lab_default_stream_queue_budget_live_runtime_object_preflight"
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_object_adapter_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_object_adapter_preflight"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_materialization_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_materialization_preflight"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_state_object_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_state_object_preflight"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_state_validation_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_state_validation_preflight"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_state_validation_artifact_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_state_validation_artifact"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_instantiation_canary_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_instantiation_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_adapter_instance_created"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_constructor_binding_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_constructor_binding_preflight"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_constructor_inputs_bound"] = False
    summary[f"{prefix}_adapter_instance_created"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_constructor_inputs_bound_mismatch" in result["failures"]
    assert f"{prefix}_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_instance_construction_plan_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_instance_construction_plan"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_construction_plan_sealed"] = False
    summary[f"{prefix}_adapter_instance_created"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_construction_plan_sealed_mismatch" in result["failures"]
    assert f"{prefix}_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_object_shell_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_object_shell_evidence"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_shell_enabled"] = True
    summary[f"{prefix}_adapter_instance_created"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_shell_enabled_mismatch" in result["failures"]
    assert f"{prefix}_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_operation_rejection_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_operation_rejection_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_issue_prefetch_rejected"] = False
    summary[f"{prefix}_demand_rejected"] = False
    summary[f"{prefix}_shell_enabled"] = True
    summary[f"{prefix}_adapter_instance_created"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_issue_prefetch_rejected_mismatch" in result["failures"]
    assert f"{prefix}_demand_rejected_mismatch" in result["failures"]
    assert f"{prefix}_shell_enabled_mismatch" in result["failures"]
    assert f"{prefix}_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_accounting_dry_run_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_accounting_dry_run_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_accounting_dry_run_enabled"] = False
    summary[f"{prefix}_resident_count"] = 0
    summary[f"{prefix}_live_adapter_instance_created"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_accounting_dry_run_enabled_mismatch" in result["failures"]
    assert f"{prefix}_resident_count_mismatch" in result["failures"]
    assert f"{prefix}_live_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_mixed_outcome_dry_run_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_mixed_outcome_dry_run_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_unprefetched_demand_hit"] = True
    summary[f"{prefix}_unprefetched_demand_missed"] = False
    summary[f"{prefix}_demand_miss_count"] = 0
    summary[f"{prefix}_live_adapter_instance_created"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_measures_tpot"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_unprefetched_demand_hit_mismatch" in result["failures"]
    assert f"{prefix}_unprefetched_demand_missed_mismatch" in result["failures"]
    assert f"{prefix}_demand_miss_count_mismatch" in result["failures"]
    assert f"{prefix}_live_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payloadless_instance_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payloadless_instance_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payloadless_live_adapter_created"] = False
    summary[f"{prefix}_live_adapter_instance_created"] = False
    summary[f"{prefix}_live_runtime_instantiated"] = True
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payloadless_live_adapter_created_mismatch" in result["failures"]
    assert f"{prefix}_live_adapter_instance_created_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_transfer_toggle_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_transfer_toggle_disabled_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_transfer_toggle_created"] = False
    summary[f"{prefix}_payload_issue_rejected"] = False
    summary[f"{prefix}_live_runtime_instantiated"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_toggle_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_rejected_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_request_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_request_blocked_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_payload_issue_request_created"] = False
    summary[f"{prefix}_payload_issue_rejected"] = False
    summary[f"{prefix}_requested_payload_bytes"] = 0
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_request_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_rejected_mismatch" in result["failures"]
    assert f"{prefix}_requested_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_plan_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_plan_dry_run"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_request_blocked_canary"] = False
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_request_blocked_canary_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_executor_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_executor_dry_run"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_plan_dry_run"] = False
    summary[f"{prefix}_payload_issue_executor_created"] = False
    summary[f"{prefix}_payload_issue_plan_consumed"] = False
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_consumes_payload_issue_plan_dry_run_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_executor_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_plan_consumed_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_queue_entry_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_queue_entry_dry_run"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_executor_dry_run"] = False
    summary[f"{prefix}_payload_issue_queue_entry_created"] = False
    summary[f"{prefix}_payload_issue_executor_consumed"] = False
    summary[f"{prefix}_queue_entry_shape_checked"] = False
    summary[f"{prefix}_queue_entry_enqueued"] = True
    summary[f"{prefix}_queue_submit_allowed"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert f"{prefix}_consumes_payload_issue_executor_dry_run_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_queue_entry_created_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_executor_consumed_mismatch" in result["failures"]
    assert f"{prefix}_queue_entry_shape_checked_mismatch" in result["failures"]
    assert f"{prefix}_queue_entry_enqueued_mismatch" in result["failures"]
    assert f"{prefix}_queue_submit_allowed_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_queue_submit_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_queue_submit_blocked_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_queue_entry_dry_run"] = False
    summary[f"{prefix}_payload_issue_queue_entry_status"] = "stale"
    summary[f"{prefix}_payload_issue_queue_submit_schema"] = "payload_submit_v0"
    summary[f"{prefix}_payload_issue_queue_submit_canary_created"] = False
    summary[f"{prefix}_payload_issue_queue_entry_consumed"] = False
    summary[f"{prefix}_queue_submit_checked"] = False
    summary[f"{prefix}_queue_submit_rejected"] = False
    summary[f"{prefix}_queue_submit_allowed"] = True
    summary[f"{prefix}_queue_entry_enqueued"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_submit_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_queue_entry_dry_run_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_queue_entry_status_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_queue_submit_schema_mismatch" in result["failures"]
    assert (
        f"{prefix}_payload_issue_queue_submit_canary_created_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_queue_entry_consumed_mismatch" in result["failures"]
    assert f"{prefix}_queue_submit_checked_mismatch" in result["failures"]
    assert f"{prefix}_queue_submit_rejected_mismatch" in result["failures"]
    assert f"{prefix}_queue_submit_allowed_mismatch" in result["failures"]
    assert f"{prefix}_queue_entry_enqueued_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_inflight_admission_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_inflight_admission_blocked_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_queue_submit_blocked_canary"] = False
    summary[f"{prefix}_payload_issue_queue_submit_status"] = "stale"
    summary[f"{prefix}_payload_issue_inflight_admission_schema"] = "inflight_v0"
    summary[f"{prefix}_payload_issue_inflight_admission_canary_created"] = False
    summary[f"{prefix}_payload_issue_queue_submit_consumed"] = False
    summary[f"{prefix}_inflight_admission_checked"] = False
    summary[f"{prefix}_inflight_admission_rejected"] = False
    summary[f"{prefix}_inflight_admission_allowed"] = True
    summary[f"{prefix}_inflight_queue_enqueued"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_inflight_issue_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_inflight_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_queue_submit_blocked_canary_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_queue_submit_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_payload_issue_inflight_admission_schema_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_inflight_admission_canary_created_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_queue_submit_consumed_mismatch" in result["failures"]
    assert f"{prefix}_inflight_admission_checked_mismatch" in result["failures"]
    assert f"{prefix}_inflight_admission_rejected_mismatch" in result["failures"]
    assert f"{prefix}_inflight_admission_allowed_mismatch" in result["failures"]
    assert f"{prefix}_inflight_queue_enqueued_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_inflight_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_command_packet_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_command_packet_dry_run"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_scheduler_dispatch_blocked_canary"] = False
    summary[f"{prefix}_payload_issue_scheduler_dispatch_status"] = "stale"
    summary[f"{prefix}_payload_issue_command_packet_schema"] = "command_packet_v0"
    summary[f"{prefix}_payload_issue_command_packet_created"] = False
    summary[f"{prefix}_payload_issue_scheduler_dispatch_consumed"] = False
    summary[f"{prefix}_command_packet_shape_checked"] = False
    summary[f"{prefix}_command_packet_submitted"] = True
    summary[f"{prefix}_command_packet_executed"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_inflight_issue_count"] = 1
    summary[f"{prefix}_dispatched_issue_count"] = 1
    summary[f"{prefix}_command_packet_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_issue_command_packet_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_scheduler_dispatch_blocked_canary_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_scheduler_dispatch_status_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_command_packet_schema_mismatch" in result["failures"]
    assert f"{prefix}_payload_issue_command_packet_created_mismatch" in result["failures"]
    assert (
        f"{prefix}_payload_issue_scheduler_dispatch_consumed_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_command_packet_shape_checked_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_submitted_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_executed_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_inflight_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_dispatched_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_transport_enqueue_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_command_packet_dry_run"] = False
    summary[f"{prefix}_payload_issue_command_packet_status"] = "stale"
    summary[f"{prefix}_payload_issue_transport_enqueue_schema"] = "transport_v0"
    summary[f"{prefix}_payload_issue_transport_enqueue_canary_created"] = False
    summary[f"{prefix}_payload_issue_command_packet_consumed"] = False
    summary[f"{prefix}_transport_enqueue_checked"] = False
    summary[f"{prefix}_transport_enqueue_rejected"] = False
    summary[f"{prefix}_transport_enqueue_allowed"] = True
    summary[f"{prefix}_transport_work_enqueued"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_inflight_issue_count"] = 1
    summary[f"{prefix}_dispatched_issue_count"] = 1
    summary[f"{prefix}_command_packet_count"] = 1
    summary[f"{prefix}_transport_work_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_issue_transport_enqueue_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_command_packet_dry_run_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_command_packet_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_payload_issue_transport_enqueue_schema_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_transport_enqueue_canary_created_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_command_packet_consumed_mismatch" in result["failures"]
    assert f"{prefix}_transport_enqueue_checked_mismatch" in result["failures"]
    assert f"{prefix}_transport_enqueue_rejected_mismatch" in result["failures"]
    assert f"{prefix}_transport_enqueue_allowed_mismatch" in result["failures"]
    assert f"{prefix}_transport_work_enqueued_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_inflight_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_dispatched_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_work_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_transport_worker_dispatch_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_transport_enqueue_blocked_canary"] = False
    summary[f"{prefix}_payload_issue_transport_enqueue_status"] = "stale"
    summary[f"{prefix}_payload_issue_transport_worker_dispatch_schema"] = "worker_v0"
    summary[f"{prefix}_payload_issue_transport_worker_dispatch_canary_created"] = False
    summary[f"{prefix}_payload_issue_transport_enqueue_consumed"] = False
    summary[f"{prefix}_transport_worker_dispatch_checked"] = False
    summary[f"{prefix}_transport_worker_dispatch_rejected"] = False
    summary[f"{prefix}_transport_worker_dispatch_allowed"] = True
    summary[f"{prefix}_transport_worker_dispatched"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_inflight_issue_count"] = 1
    summary[f"{prefix}_dispatched_issue_count"] = 1
    summary[f"{prefix}_command_packet_count"] = 1
    summary[f"{prefix}_transport_work_count"] = 1
    summary[f"{prefix}_transport_worker_dispatch_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_issue_transport_worker_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_transport_enqueue_blocked_canary_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_transport_enqueue_status_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_transport_worker_dispatch_schema_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_transport_worker_dispatch_canary_created_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_transport_enqueue_consumed_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatch_checked_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatch_rejected_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatch_allowed_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatched_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_inflight_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_dispatched_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_work_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatch_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_copy_descriptor_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_copy_descriptor_dry_run"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[
        f"{prefix}_consumes_payload_issue_transport_worker_dispatch_blocked_canary"
    ] = False
    summary[f"{prefix}_payload_issue_transport_worker_dispatch_status"] = "stale"
    summary[f"{prefix}_payload_issue_copy_descriptor_schema"] = "copy_descriptor_v0"
    summary[f"{prefix}_payload_issue_copy_descriptor_created"] = False
    summary[f"{prefix}_payload_issue_transport_worker_dispatch_consumed"] = False
    summary[f"{prefix}_copy_descriptor_shape_checked"] = False
    summary[f"{prefix}_copy_descriptor_submitted"] = True
    summary[f"{prefix}_copy_descriptor_executed"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_request_layer_idx"] = 1
    summary[f"{prefix}_request_expert_idx"] = 1
    summary[f"{prefix}_requested_payload_bytes"] = 128
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_inflight_issue_count"] = 1
    summary[f"{prefix}_dispatched_issue_count"] = 1
    summary[f"{prefix}_command_packet_count"] = 1
    summary[f"{prefix}_transport_work_count"] = 1
    summary[f"{prefix}_transport_worker_dispatch_count"] = 1
    summary[f"{prefix}_copy_descriptor_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_issue_copy_descriptor_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_transport_worker_dispatch_blocked_canary_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_transport_worker_dispatch_status_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_copy_descriptor_schema_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_copy_descriptor_created_mismatch" in result["failures"]
    assert (
        f"{prefix}_payload_issue_transport_worker_dispatch_consumed_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_copy_descriptor_shape_checked_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_submitted_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_executed_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_request_layer_idx_mismatch" in result["failures"]
    assert f"{prefix}_request_expert_idx_mismatch" in result["failures"]
    assert f"{prefix}_requested_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_inflight_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_dispatched_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_work_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatch_count_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_payload_issue_copy_descriptor_submit_escape() -> None:
    summary = _summary()
    prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary"
    )
    summary[f"{prefix}_status"] = "passed"
    summary[f"{prefix}_consumes_payload_issue_copy_descriptor_dry_run"] = False
    summary[f"{prefix}_payload_issue_copy_descriptor_status"] = "stale"
    summary[f"{prefix}_payload_issue_copy_descriptor_submit_schema"] = "submit_v0"
    summary[f"{prefix}_payload_issue_copy_descriptor_submit_canary_created"] = False
    summary[f"{prefix}_payload_issue_copy_descriptor_consumed"] = False
    summary[f"{prefix}_copy_descriptor_submit_checked"] = False
    summary[f"{prefix}_copy_descriptor_submit_rejected"] = False
    summary[f"{prefix}_copy_descriptor_submit_allowed"] = True
    summary[f"{prefix}_copy_descriptor_submitted"] = True
    summary[f"{prefix}_copy_descriptor_executed"] = True
    summary[f"{prefix}_request_source"] = "synthetic_payload_issue_request"
    summary[f"{prefix}_request_layer_idx"] = 1
    summary[f"{prefix}_request_expert_idx"] = 1
    summary[f"{prefix}_requested_payload_bytes"] = 128
    summary[f"{prefix}_source_issue_packet_count"] = 0
    summary[f"{prefix}_source_issue_unique_key_count"] = 0
    summary[f"{prefix}_source_queue_budget_capacity"] = 0
    summary[f"{prefix}_source_issue_lead_tokens"] = 0
    summary[f"{prefix}_source_queue_deadline_us"] = 0.0
    summary[f"{prefix}_planned_issue_count"] = 1
    summary[f"{prefix}_scheduled_issue_count"] = 1
    summary[f"{prefix}_queued_issue_count"] = 1
    summary[f"{prefix}_submitted_issue_count"] = 1
    summary[f"{prefix}_inflight_issue_count"] = 1
    summary[f"{prefix}_dispatched_issue_count"] = 1
    summary[f"{prefix}_command_packet_count"] = 1
    summary[f"{prefix}_transport_work_count"] = 1
    summary[f"{prefix}_transport_worker_dispatch_count"] = 1
    summary[f"{prefix}_copy_descriptor_count"] = 1
    summary[f"{prefix}_issued_payload_count"] = 1
    summary[f"{prefix}_payload_bytes"] = 64
    summary[f"{prefix}_decision"] = "allow"
    summary[f"{prefix}_block_reason"] = "payload_transfer_enabled"
    summary[f"{prefix}_execution_mode"] = "payload_issue_copy_descriptor_submit_live"
    summary[f"{prefix}_live_payload_runtime_enabled"] = True
    summary[f"{prefix}_payload_transfer_runtime_enabled"] = True
    summary[f"{prefix}_payload_deref_allowed"] = True
    summary[f"{prefix}_payload_deref_runtime_allowed"] = True
    summary[f"{prefix}_ready_credit"] = True
    summary[f"{prefix}_ready_before_demand_credit"] = True
    summary[f"{prefix}_real_ready_credit_granted"] = True
    summary[f"{prefix}_kernel_arg_pass_allowed"] = True
    summary[f"{prefix}_passed_to_kernel"] = True
    summary[f"{prefix}_changes_kernel_launch_args"] = True
    summary[f"{prefix}_full_fetch_runtime_allowed"] = True
    summary[f"{prefix}_uses_current_wna16_args"] = True
    summary[f"{prefix}_passes_current_wna16_args"] = True
    summary[f"{prefix}_measures_tpot"] = True
    summary[f"{prefix}_measures_vllm_latency"] = True
    summary[f"{prefix}_live_runtime_instantiated"] = True

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert f"{prefix}_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_consumes_payload_issue_copy_descriptor_dry_run_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_copy_descriptor_status_mismatch" in result["failures"]
    assert (
        f"{prefix}_payload_issue_copy_descriptor_submit_schema_mismatch"
        in result["failures"]
    )
    assert (
        f"{prefix}_payload_issue_copy_descriptor_submit_canary_created_mismatch"
        in result["failures"]
    )
    assert f"{prefix}_payload_issue_copy_descriptor_consumed_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_submit_checked_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_submit_rejected_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_submit_allowed_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_submitted_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_executed_mismatch" in result["failures"]
    assert f"{prefix}_request_source_mismatch" in result["failures"]
    assert f"{prefix}_request_layer_idx_mismatch" in result["failures"]
    assert f"{prefix}_request_expert_idx_mismatch" in result["failures"]
    assert f"{prefix}_requested_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_unique_key_count_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_budget_capacity_mismatch" in result["failures"]
    assert f"{prefix}_source_issue_lead_tokens_mismatch" in result["failures"]
    assert f"{prefix}_source_queue_deadline_us_mismatch" in result["failures"]
    assert f"{prefix}_planned_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_scheduled_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_queued_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_submitted_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_inflight_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_dispatched_issue_count_mismatch" in result["failures"]
    assert f"{prefix}_command_packet_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_work_count_mismatch" in result["failures"]
    assert f"{prefix}_transport_worker_dispatch_count_mismatch" in result["failures"]
    assert f"{prefix}_copy_descriptor_count_mismatch" in result["failures"]
    assert f"{prefix}_issued_payload_count_mismatch" in result["failures"]
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_decision_mismatch" in result["failures"]
    assert f"{prefix}_block_reason_mismatch" in result["failures"]
    assert f"{prefix}_execution_mode_mismatch" in result["failures"]
    assert f"{prefix}_live_payload_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_transfer_runtime_enabled_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_allowed_mismatch" in result["failures"]
    assert f"{prefix}_payload_deref_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_ready_credit_mismatch" in result["failures"]
    assert f"{prefix}_ready_before_demand_credit_mismatch" in result["failures"]
    assert f"{prefix}_real_ready_credit_granted_mismatch" in result["failures"]
    assert f"{prefix}_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert f"{prefix}_passed_to_kernel_mismatch" in result["failures"]
    assert f"{prefix}_changes_kernel_launch_args_mismatch" in result["failures"]
    assert f"{prefix}_full_fetch_runtime_allowed_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_passes_current_wna16_args_mismatch" in result["failures"]
    assert f"{prefix}_measures_tpot_mismatch" in result["failures"]
    assert f"{prefix}_measures_vllm_latency_mismatch" in result["failures"]
    assert f"{prefix}_live_runtime_instantiated_mismatch" in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_queue_budget_summary_mixing() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_queue_budget_first_model_passing_capacity"] = 8192
    summary[
        "prefetch_lab_default_stream_queue_budget_first_model_passing_queue_deadline_us"
    ] = 200.0
    summary[
        "prefetch_lab_default_stream_queue_budget_first_model_passing_lookahead_us"
    ] = 1_200_000.0
    summary[
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count"
    ] = 32

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    for failure in (
        "prefetch_lab_default_stream_queue_budget_first_model_passing_capacity_mismatch",
        "prefetch_lab_default_stream_queue_budget_first_model_passing_queue_deadline_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_first_model_passing_lookahead_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_capacity_entries_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_queue_deadline_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_lookahead_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_accounted_packet_count_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_capacity_entries_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_queue_deadline_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_lookahead_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_accounted_packet_count_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_capacity_entries_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_queue_deadline_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_lookahead_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_accounted_packet_count_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_capacity_entries_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_queue_deadline_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_lookahead_us_mismatch",
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounted_packet_count_mismatch",
    ):
        assert failure in result["failures"]


def test_check_premap_lab_preflight_summary_rejects_shifted_issue_type_confusion() -> None:
    summary = _summary()
    summary["prefetch_lab_default_stream_shifted_issue_replay_payload_bytes"] = False
    summary["prefetch_lab_default_stream_shifted_issue_replay_contract_present"] = 1
    summary[
        "prefetch_lab_default_stream_shifted_issue_replay_uses_current_wna16_args"
    ] = 0

    result = check_premap_lab_preflight_summary(summary)

    assert result["passed"] is False
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_contract_present_mismatch"
        in result["failures"]
    )
    assert (
        "prefetch_lab_default_stream_shifted_issue_replay_uses_current_wna16_args_mismatch"
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
