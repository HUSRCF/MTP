#!/usr/bin/env python3
"""Run read-only preflight checks for the premap lab gate artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.check_premap_kernel_consumer_schema import (
    FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED,
    FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS,
    check_kernel_consumer_schema_artifact,
)
from scripts.check_gate_evidence_paths import check_gate_evidence_paths
from scripts.check_prefetch_lab_default_gate import check_prefetch_lab_default_gate
from scripts.check_runtime_gate_evidence_paths import scan_runtime_gate_evidence_paths
from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_MODE,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_NAME,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_SOURCE,
)


DEFAULT_TRACE_CONFIGS = [
    "configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml",
    "configs/trace/router_mtp_trace_external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml",
]
DEFAULT_READONLY_GATE = (
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml"
)
DEFAULT_KERNEL_CONSUMER_SCHEMA_ARTIFACT = (
    "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
)
DEFAULT_CANARY_GATE = (
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml"
)
DEFAULT_PREFETCH_LAB_DEFAULT_GATE = (
    "configs/runtime/prefetch_lab_default_gate_gpu1.yaml"
)
RISKY_CANARY_GATES = [
    DEFAULT_CANARY_GATE,
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_kernel_arg_pass_canary.yaml",
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_real_kernel_arg_mutation_canary.yaml",
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_prepared_table_candidate_dry_run.yaml",
]
REQUIRED_DEFAULT_GATE_CONTRACT = {
    "kernel_arg_handoff_live_toggle_enabled_required": True,
    "kernel_arg_handoff_live_noop_integration_enabled_required": True,
    "kernel_arg_handoff_live_noop_integration_consumer_connected_required": True,
    "kernel_arg_handoff_live_consumer_adapter_enabled_required": True,
    "kernel_arg_handoff_live_consumer_adapter_consumer_connected_required": True,
    "kernel_side_consumer_schema_adapter_consumer_connected_required": True,
    "kernel_side_consumer_schema_adapter_live_enabled_required": True,
    "kernel_side_consumer_schema_adapter_live_eligible_required": True,
    "kernel_side_typed_consumer_object_required": True,
    "kernel_side_typed_consumer_object_payload_bytes_required": 0,
    "kernel_side_typed_consumer_object_passed_to_kernel_required": False,
    "kernel_side_typed_consumer_object_changes_kernel_launch_args_required": False,
    "kernel_side_typed_consumer_object_consumer_connected_required": True,
    "kernel_side_typed_consumer_object_live_enabled_required": True,
    "kernel_side_typed_consumer_object_live_eligible_required": True,
    "kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args_required": False,
    "kernel_side_typed_row_consumer_path_required": True,
    "kernel_side_typed_row_consumer_path_mode": "readonly_typed_row_consumer_path",
    "kernel_side_typed_row_consumer_path_name": (
        "premap_kernel_side_typed_consumer_path_v1"
    ),
    "kernel_side_typed_row_consumer_path_source": (
        "vllm_prelaunch_prepared_handle_table"
    ),
    "kernel_side_typed_row_consumer_path_payload_bytes_required": 0,
    "kernel_side_typed_row_consumer_path_passed_to_kernel_required": False,
    "kernel_side_typed_row_consumer_path_changes_kernel_launch_args_required": False,
    "kernel_side_typed_row_consumer_path_current_wna16_arg_compatible_required": False,
    "future_kernel_consumer_args_required": True,
    "future_kernel_consumer_args_name": "premap_future_kernel_side_consumer_args_v1",
    "future_kernel_consumer_args_mode": "readonly_future_kernel_consumer_args",
    "future_kernel_consumer_args_source": (
        "premap_kernel_side_typed_consumer_launch_envelope_v1"
    ),
    "future_kernel_consumer_args_payload_bytes_required": 0,
    "future_kernel_consumer_args_passed_to_kernel_required": False,
    "future_kernel_consumer_args_changes_kernel_launch_args_required": False,
    "future_kernel_consumer_args_current_wna16_arg_compatible_required": False,
    "future_kernel_consumer_args_single_field_mirror_required": True,
    "future_kernel_consumer_args_single_field_mirror_field": "scale_metadata_handle",
    "future_kernel_consumer_args_total_mirror_coverage_required": True,
    "future_kernel_args_compatible_consumer_path_required": True,
    "future_kernel_native_dispatch_consumer_full_table_required": True,
    "future_kernel_native_dispatch_ptr_consumer_required": True,
    "future_kernel_native_dispatch_consumer_program_iteration_required": True,
    "future_kernel_native_dispatch_consumer_row_assignment_formula": (
        "row_offset + program_id * rows_per_program + lane_id"
    ),
    "consumer_program_view_required": True,
    "consumer_program_view_row_assignment_formula": (
        "program_id * rows_per_program + lane_id + row_offset"
    ),
    "consumer_program_view_ptr_required": True,
    "request_launch_all_handle_fields_required": True,
    "request_launch_ptr_all_handle_fields_required": True,
    "future_kernel_native_arg_slot_online_total_mirror_coverage_required": True,
    "future_wna16_single_field_handoff_all_fields_required": True,
    "future_wna16_single_field_handoff_all_fields_min_source_count": 128,
    "future_wna16_typed_slot_fourth_field_handoff_canary_required": True,
    "future_wna16_typed_slot_fourth_field_handoff_canary_field": "descriptor_ptr",
    "future_wna16_typed_slot_fourth_field_handoff_canary_min_source_count": 128,
    "future_wna16_typed_slot_all_four_field_consumer_required": True,
    "future_wna16_typed_slot_all_four_field_consumer_min_source_count": 128,
    "future_wna16_kernel_side_typed_consumer_path_required": True,
    "future_wna16_kernel_side_typed_consumer_path_min_source_count": 128,
    "future_wna16_typed_slot_payloadless_execution_required": True,
    "future_wna16_typed_slot_payloadless_execution_min_source_count": 128,
    "future_wna16_typed_slot_kernel_variant_execution_required": True,
    "future_wna16_typed_slot_kernel_variant_execution_min_source_count": 128,
    "future_wna16_typed_slot_kernel_variant_useful_consumer_required": True,
    "future_wna16_typed_slot_kernel_variant_useful_consumer_min_source_count": 128,
    "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_required": True,
    "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_min_source_count": 128,
    "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_required": True,
    "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_source_count": 128,
    "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_repeat_count": 3,
    "wna16_side_consumer_variant_execution_required": True,
    "wna16_side_consumer_variant_execution_min_source_count": 128,
    "single_field_handle_handoff_canary_required": True,
    "single_field_handle_handoff_canary_mode": (
        "readonly_single_field_handle_handoff_canary"
    ),
    "single_field_handle_handoff_canary_field": "scale_metadata_handle",
    "single_field_handle_handoff_canary_source": "semantic_handle_table",
    "single_field_handle_handoff_canary_mirror_mode": (
        "readonly_scale_metadata_handle_mirror"
    ),
    "single_field_handle_handoff_canary_mirror_field": "scale_metadata_handle",
    "single_field_handle_handoff_canary_mirror_source": "semantic_handle_table",
    "single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible_required": True,
    "single_field_handle_handoff_canary_current_wna16_arg_compatible_required": False,
    "single_field_handle_handoff_canary_block_reason": (
        "single_field_handoff_live_disabled"
    ),
    "single_field_handle_handoff_canary_payload_bytes_required": 0,
    "single_field_handle_handoff_canary_ready_credit_required": False,
    "single_field_handle_handoff_canary_passed_to_kernel_required": False,
    "single_field_handle_handoff_canary_changes_kernel_launch_args_required": False,
    "single_field_handle_handoff_canary_live_enabled_required": False,
    "single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required": False,
    "aux_metadata_single_field_handle_handoff_canary_smoke_required": True,
    "aux_metadata_single_field_handle_handoff_canary_mode": (
        "readonly_single_field_handle_handoff_canary"
    ),
    "aux_metadata_single_field_handle_handoff_canary_field": "aux_metadata_handle",
    "aux_metadata_single_field_handle_handoff_canary_source": (
        "semantic_handle_table"
    ),
    "aux_metadata_single_field_handle_handoff_canary_mirror_mode": (
        "readonly_aux_metadata_handle_mirror"
    ),
    "aux_metadata_single_field_handle_handoff_canary_mirror_field": (
        "aux_metadata_handle"
    ),
    "aux_metadata_single_field_handle_handoff_canary_mirror_source": (
        "semantic_handle_table"
    ),
    "aux_metadata_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible_required": True,
    "aux_metadata_single_field_handle_handoff_canary_current_wna16_arg_compatible_required": False,
    "aux_metadata_single_field_handle_handoff_canary_block_reason": (
        "single_field_handoff_live_disabled"
    ),
    "aux_metadata_single_field_handle_handoff_canary_payload_bytes_required": 0,
    "aux_metadata_single_field_handle_handoff_canary_ready_credit_required": False,
    "aux_metadata_single_field_handle_handoff_canary_passed_to_kernel_required": False,
    "aux_metadata_single_field_handle_handoff_canary_changes_kernel_launch_args_required": False,
    "aux_metadata_single_field_handle_handoff_canary_live_enabled_required": False,
    "aux_metadata_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required": False,
    "descriptor_ptr_single_field_handle_handoff_canary_smoke_required": True,
    "descriptor_ptr_single_field_handle_handoff_canary_field": "descriptor_ptr",
    "descriptor_ptr_single_field_handle_handoff_canary_source": (
        "semantic_handle_table"
    ),
    "descriptor_ptr_single_field_handle_handoff_canary_payload_bytes_required": 0,
    "descriptor_ptr_single_field_handle_handoff_canary_ready_credit_required": False,
    "descriptor_ptr_single_field_handle_handoff_canary_passed_to_kernel_required": False,
    "descriptor_ptr_single_field_handle_handoff_canary_changes_kernel_launch_args_required": False,
    "descriptor_ptr_single_field_handle_handoff_canary_live_enabled_required": False,
    "descriptor_ptr_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required": False,
    "packed_weight_single_field_handle_handoff_canary_smoke_required": True,
    "packed_weight_single_field_handle_handoff_canary_field": (
        "packed_weight_descriptor"
    ),
    "packed_weight_single_field_handle_handoff_canary_source": (
        "semantic_handle_table"
    ),
    "packed_weight_single_field_handle_handoff_canary_payload_bytes_required": 0,
    "packed_weight_single_field_handle_handoff_canary_ready_credit_required": False,
    "packed_weight_single_field_handle_handoff_canary_passed_to_kernel_required": False,
    "packed_weight_single_field_handle_handoff_canary_changes_kernel_launch_args_required": False,
    "packed_weight_single_field_handle_handoff_canary_live_enabled_required": False,
    "packed_weight_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required": False,
    "native_typed_consumer_bridge_required": True,
    "native_typed_consumer_bridge_payload_bytes_required": 0,
    "native_typed_consumer_bridge_ready_credit_required": False,
    "native_typed_consumer_bridge_changes_router_required": False,
    "native_typed_consumer_bridge_changes_descriptor_order_required": False,
    "native_typed_consumer_bridge_passed_to_kernel_required": False,
    "native_typed_consumer_bridge_changes_kernel_launch_args_required": False,
    "native_stub_online_invocation_canary_required": True,
    "native_stub_online_invocation_canary_mode": (
        "readonly_native_stub_online_invocation_canary"
    ),
    "native_stub_online_invocation_canary_block_reason": (
        "native_stub_live_disabled"
    ),
    "native_stub_online_invocation_canary_payload_bytes_required": 0,
    "native_stub_online_invocation_canary_ready_credit_required": False,
    "native_stub_online_invocation_canary_changes_router_required": False,
    "native_stub_online_invocation_canary_changes_descriptor_order_required": False,
    "native_stub_online_invocation_canary_passed_to_kernel_required": False,
    "native_stub_online_invocation_canary_changes_kernel_launch_args_required": False,
    "native_stub_online_invocation_canary_native_stub_invoked_required": False,
    "native_stub_online_invocation_canary_blocked_required": True,
    "native_typed_consumer_stub_canary_required": True,
    "native_typed_consumer_stub_payload_bytes_required": 0,
    "native_typed_consumer_stub_passed_to_kernel_required": False,
    "native_typed_consumer_stub_changes_kernel_launch_args_required": False,
}
REQUIRED_RISKY_CANARY_METADATA = {
    "canary": True,
    "lab_default": False,
}
REQUIRED_DEFAULT_GATE_EVIDENCE_JSON_LABELS = {
    "strict_live_connected_readonly_128_gate_json",
    "strict_kernel_side_typed_consumer_object_128_gate_json",
    "strict_kernel_side_typed_consumer_object_128_selfcheck_json",
    "strict_kernel_side_typed_row_consumer_path_128_gate_json",
    "strict_single_field_handle_handoff_canary_128_gate_json",
    "aux_metadata_single_field_handle_handoff_canary_smoke_json",
    "descriptor_ptr_single_field_handle_handoff_canary_smoke_json",
    "packed_weight_single_field_handle_handoff_canary_smoke_json",
    "strict_native_typed_consumer_bridge_128_gate_json",
    "native_typed_consumer_bridge_smoke_json",
    "strict_native_stub_online_invocation_canary_128_gate_json",
    "native_typed_consumer_stub_gpu1_canary_json",
    "native_typed_consumer_stub_endpoint_ptr_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json",
    "native_typed_consumer_online_prelaunch_canary_runner_json",
    "future_kernel_native_dispatch_ptr_standalone_canary_json",
    "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
    "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
    "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
    "future_kernel_native_arg_slot_standalone_canary_json",
    "future_kernel_native_arg_slot_multiprogram_canary_json",
    "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_canary_json",
    "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json",
    "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_canary_json",
    "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json",
    "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_canary_json",
    "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json",
    "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json",
    "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json",
    "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json",
    "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json",
    "future_kernel_wna16_adjacent_typed_slot_canary_json",
    "future_kernel_wna16_adjacent_typed_slot_stub_json",
    "future_kernel_wna16_adjacent_typed_slot_standalone_canary_json",
    "future_wna16_single_field_handoff_all_fields_128strict_summary_json",
    "future_wna16_typed_slot_fourth_field_handoff_canary_json",
    "future_wna16_typed_slot_all_four_field_consumer_json",
    "future_wna16_kernel_side_typed_consumer_path_json",
    "future_wna16_typed_slot_payloadless_execution_json",
    "future_wna16_typed_slot_kernel_variant_execution_json",
    "future_wna16_typed_slot_kernel_variant_useful_consumer_json",
    "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json",
    "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json",
    "wna16_side_consumer_variant_execution_128strict_runner_json",
    "payload_cache_producer_state_native_canary_json",
    "payload_cache_shifted_issue_runtime_shadow_gate_json",
    "payload_cache_packet_export_manifest_json",
    "payload_cache_producer_state_online_nonempty_issue_canary_json",
    "payload_cache_producer_state_nonempty_issue_stub_json",
    "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json",
    "future_kernel_native_dispatch_consumer_online_runner_32_128export_json",
}
OPTIONAL_DEFAULT_GATE_EVIDENCE_JSON_LABELS = {
    "future_kernel_args_aux_metadata_mirror_canary_json",
    "future_kernel_args_compatible_path_16_128export_artifact_check_json",
    "future_kernel_args_compatible_path_canary_json",
    "future_kernel_args_descriptor_ptr_mirror_canary_json",
    "future_kernel_args_field_refresh_16_128export_artifact_check_json",
    "future_kernel_args_field_refresh_flatten_check_json",
    "future_kernel_args_packed_weight_mirror_canary_json",
    "future_kernel_native_consumer_aux_metadata_mirror_canary_json",
    "future_kernel_native_consumer_descriptor_ptr_mirror_canary_json",
    "future_kernel_native_consumer_launch_scale_mirror_canary_json",
    "future_kernel_native_consumer_packed_weight_mirror_canary_json",
    "future_kernel_native_consumer_scale_mirror_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
}
ARG_SLOT_MIRROR_FIELDS = tuple(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
ARG_SLOT_REQUIRED_MIRROR_LABEL_BY_FIELD = {
    "aux_metadata_handle": "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
    "descriptor_ptr": "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
    "packed_weight_descriptor": (
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json"
    ),
}
ARG_SLOT_OPTIONAL_MIRROR_LABEL_BY_FIELD: dict[str, str] = {}
ARG_SLOT_MIRROR_LABEL_BY_FIELD = {
    **ARG_SLOT_REQUIRED_MIRROR_LABEL_BY_FIELD,
    **ARG_SLOT_OPTIONAL_MIRROR_LABEL_BY_FIELD,
}
ARG_SLOT_ONLINE_MERGED_REQUIRED_MIRROR_RUNNER_LABEL_BY_FIELD = {
    "aux_metadata_handle": (
        "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json"
    ),
    "descriptor_ptr": (
        "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json"
    ),
    "packed_weight_descriptor": (
        "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json"
    ),
}
ARG_SLOT_ONLINE_MERGED_REQUIRED_MIRROR_STUB_LABEL_BY_FIELD = {
    "aux_metadata_handle": (
        "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_canary_json"
    ),
    "descriptor_ptr": (
        "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_canary_json"
    ),
    "packed_weight_descriptor": (
        "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_canary_json"
    ),
}
ARG_SLOT_ONLINE_MERGED_OPTIONAL_MIRROR_RUNNER_LABEL_BY_FIELD: dict[str, str] = {}
ARG_SLOT_ONLINE_MERGED_MIRROR_RUNNER_LABEL_BY_FIELD = {
    **ARG_SLOT_ONLINE_MERGED_REQUIRED_MIRROR_RUNNER_LABEL_BY_FIELD,
    **ARG_SLOT_ONLINE_MERGED_OPTIONAL_MIRROR_RUNNER_LABEL_BY_FIELD,
}
ARG_SLOT_ONLINE_MERGED_MIRROR_STUB_LABEL_BY_FIELD = {
    **ARG_SLOT_ONLINE_MERGED_REQUIRED_MIRROR_STUB_LABEL_BY_FIELD,
}
ARG_SLOT_ONLINE_DIAGNOSTIC_SUMMARY_KEY_BY_FIELD = {
    "aux_metadata_handle": (
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary"
    ),
    "descriptor_ptr": (
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary"
    ),
    "packed_weight_descriptor": (
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary"
    ),
}
FUTURE_KERNEL_ARGS_OPTIONAL_MIRROR_LABEL_BY_FIELD = {
    "aux_metadata_handle": "future_kernel_args_aux_metadata_mirror_canary_json",
    "descriptor_ptr": "future_kernel_args_descriptor_ptr_mirror_canary_json",
    "packed_weight_descriptor": "future_kernel_args_packed_weight_mirror_canary_json",
}
ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL = (
    "native_typed_consumer_online_prelaunch_canary_runner_json"
)
ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABELS = {
    ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL,
    "future_kernel_native_consumer_online_runner_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_runner_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_runner_32_128export_json",
    "future_kernel_native_launch_consumer_online_runner_16_128export_json",
}
DISPATCH_WINDOW_RUNNER_EVIDENCE_LABELS = {
    ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL,
    "future_kernel_native_dispatch_consumer_online_runner_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_runner_32_128export_json",
}
ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS = {
    "future_kernel_native_consumer_online_artifact_check_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json",
    "future_kernel_native_launch_consumer_online_artifact_check_16_128export_json",
}
ONLINE_PRELAUNCH_SELF_FINALIZATION_EVIDENCE_LABELS = (
    ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABELS | ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS
)
ONLINE_PRELAUNCH_MIN_INPUTS_BY_LABEL = {
    ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL: 32,
    "future_kernel_native_consumer_online_runner_16_128export_json": 32,
    "future_kernel_native_consumer_online_artifact_check_16_128export_json": 32,
    "future_kernel_native_launch_consumer_online_runner_16_128export_json": 32,
    "future_kernel_native_launch_consumer_online_artifact_check_16_128export_json": 32,
    "future_kernel_native_dispatch_consumer_online_runner_16_128export_json": 32,
    "future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json": 32,
    "future_kernel_native_dispatch_consumer_online_runner_32_128export_json": 32,
    "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json": 32,
}

_NATIVE_BRIDGE_METRIC_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_"
    "native_typed_consumer_bridge_"
)
_NATIVE_STUB_METRIC_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_"
    "native_stub_online_invocation_"
)
_SINGLE_FIELD_CANARY_METRIC_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_"
    "single_field_handle_handoff_canary_"
)
_TYPED_ROW_CONSUMER_PATH_METRIC_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_"
    "kernel_side_typed_row_consumer_path_"
)
_FUTURE_KERNEL_REQUIRED_FIELD_MASK = 0x7
_FUTURE_KERNEL_TYPED_SLOT_MIRROR_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
_FUTURE_KERNEL_ALL_FIELD_MASK = 0xF
_FUTURE_KERNEL_AUX_FIELD_MASK = 0x8
_FUTURE_WNA16_SINGLE_FIELD_HANDOFF_FIELDS = {
    "descriptor_ptr": (1, 1),
    "packed_weight_descriptor": (2, 2),
    "scale_metadata_handle": (3, 4),
    "aux_metadata_handle": (4, 8),
}
_FUTURE_WNA16_SINGLE_FIELD_HANDOFF_MODE = (
    "readonly_future_wna16_single_field_handoff_canary"
)
_FUTURE_WNA16_SINGLE_FIELD_HANDOFF_SOURCE = (
    "premap_future_wna16_kernel_side_consumer_execution_v1"
)
_FUTURE_WNA16_SINGLE_FIELD_HANDOFF_READ_PATH = (
    "future_wna16_single_field_handoff_to_"
    "future_wna16_kernel_side_execution_to_"
    "accepted_typed_slot_to_program_view_rows"
)
_UINT64_MASK = (1 << 64) - 1
_PROGRAM_ITERATION_HASH_FORMULA = (
    "mix64(grid_x + 0xd15c2001) ^ mix64(block_x + 0xd15c2002) ^ "
    "mix64(row_offset + 0xd15c2003) ^ mix64(row_limit + 0xd15c2004) ^ "
    "mix64(last_program_active_rows + 0xd15c2005) ^ "
    "mix64(inactive_lane_count + 0xd15c2006)"
)
_KERNEL_LAUNCH_CONTEXT_ABI_NAME = (
    "premap_future_kernel_native_consumer_kernel_launch_context_abi_v1"
)
_KERNEL_LAUNCH_CONTEXT_MODE = (
    "readonly_future_kernel_native_consumer_kernel_launch_context_abi"
)
_KERNEL_LAUNCH_CONTEXT_SOURCE = (
    "premap_future_kernel_native_consumer_kernel_launch_descriptor_abi_v1"
)
_KERNEL_LAUNCH_CONTEXT_PACKET_CHAIN_DEPTH = 10
_KERNEL_LAUNCH_CONTEXT_STRUCT_SIZE = 64
_KERNEL_LAUNCH_CONTEXT_STRUCT_ALIGN = 8
_KERNEL_LAUNCH_CONTEXT_LAUNCH_DESCRIPTOR_STRUCT_SIZE = 80
_KERNEL_LAUNCH_CONTEXT_SUMMARY_STRUCT_SIZE = 104
_KERNEL_LAUNCH_CONTEXT_POINTER_SIZE = 8
_INVOCATION_ABI_NAME = "premap_future_kernel_native_consumer_invocation_abi_v1"
_INVOCATION_MODE = "readonly_future_kernel_native_consumer_invocation_abi"
_INVOCATION_SOURCE = _KERNEL_LAUNCH_CONTEXT_ABI_NAME
_INVOCATION_PACKET_CHAIN_DEPTH = 11
_INVOCATION_STRUCT_SIZE = 72
_INVOCATION_STRUCT_ALIGN = 8
_INVOCATION_CONTEXT_STRUCT_SIZE = _KERNEL_LAUNCH_CONTEXT_STRUCT_SIZE
_INVOCATION_SUMMARY_STRUCT_SIZE = 104
_INVOCATION_POINTER_SIZE = 8
_INVOCATION_ENTRY_ABI_NAME = (
    "premap_future_kernel_native_consumer_invocation_entry_abi_v1"
)
_INVOCATION_ENTRY_MODE = (
    "readonly_future_kernel_native_consumer_invocation_entry_abi"
)
_INVOCATION_ENTRY_SOURCE = (
    "premap_future_kernel_native_consumer_invocation_abi_v1_by_value"
)
_INVOCATION_ENTRY_FIELD_READ_PATH = (
    "by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_"
    "launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_"
    "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
)
_INVOCATION_ENTRY_PACKET_CHAIN_DEPTH = 11
_ENDPOINT_ABI_NAME = "premap_future_kernel_native_consumer_endpoint_abi_v1"
_ENDPOINT_MODE = "readonly_future_kernel_native_consumer_endpoint_abi"
_ENDPOINT_SOURCE = "premap_future_kernel_native_consumer_invocation_entry_abi_v1"
_ENDPOINT_FIELD_READ_PATH = (
    "endpoint_to_by_value_invocation_to_kernel_launch_context_to_"
    "kernel_launch_descriptor_to_launch_envelope_args_ptr_to_"
    "launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_"
    "kernel_arg_packet_to_program_view_rows"
)
_ENDPOINT_PACKET_CHAIN_DEPTH = 12
_ENDPOINT_PTR_ABI_NAME = "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
_ENDPOINT_PTR_MODE = "readonly_future_kernel_native_consumer_endpoint_ptr_abi"
_ENDPOINT_PTR_SOURCE = "premap_future_kernel_native_consumer_endpoint_abi_v1"
_ENDPOINT_PTR_FIELD_READ_PATH = (
    "endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_"
    "kernel_launch_descriptor_to_launch_envelope_args_ptr_to_"
    "launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_"
    "kernel_arg_packet_to_program_view_rows"
)
_ENDPOINT_PTR_PACKET_CHAIN_DEPTH = 13


def _int_metric(metrics: dict[str, Any], key: str) -> int | None:
    value = metrics.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _float_metric(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _bool_metric(metrics: dict[str, Any], key: str) -> bool | None:
    value = metrics.get(key)
    return value if isinstance(value, bool) else None


STREAM_QUEUE_BUDGET_LIVE_RUNTIME_CANARY_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_live_runtime_preflight",
    "live_runtime_preflight_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "live_runtime_canary_instantiated",
    "live_runtime_preflight_instantiated",
    "accounting_snapshot_instantiated",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_STATE_SHAPE_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_live_runtime_canary",
    "live_runtime_canary_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "live_runtime_state_shape_checked",
    "issue_queue_shape_checked",
    "demand_state_shape_checked",
    "resident_index_shape_checked",
    "queue_timing_shape_checked",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_OBJECT_PREFLIGHT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_state_shape_check",
    "state_shape_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "object_construction_preflight_instantiated",
    "typed_issue_queue_container_declared",
    "typed_demand_state_container_declared",
    "typed_resident_index_container_declared",
    "typed_queue_timing_container_declared",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_OBJECT_ADAPTER_PREFLIGHT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_object_construction_preflight",
    "object_preflight_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "runtime_adapter_schema",
    "object_construction_preflight_instantiated",
    "runtime_object_adapter_declared",
    "issue_queue_adapter_bound",
    "demand_state_adapter_bound",
    "resident_index_adapter_bound",
    "queue_timing_adapter_bound",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_MATERIALIZATION_PREFLIGHT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_object_adapter_preflight",
    "object_adapter_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "runtime_adapter_schema",
    "object_construction_preflight_instantiated",
    "adapter_materialization_preflight_instantiated",
    "runtime_object_adapter_declared",
    "issue_queue_materialization_checked",
    "demand_state_materialization_checked",
    "resident_index_materialization_checked",
    "queue_timing_materialization_checked",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_STATE_OBJECT_PREFLIGHT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_adapter_materialization_preflight",
    "adapter_materialization_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "runtime_adapter_schema",
    "adapter_state_object_schema",
    "adapter_materialization_preflight_instantiated",
    "adapter_state_object_declared",
    "issue_queue_state_object_declared",
    "demand_state_object_declared",
    "resident_index_state_object_declared",
    "queue_timing_state_object_declared",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_STATE_VALIDATION_PREFLIGHT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_adapter_state_object_preflight",
    "adapter_state_object_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "runtime_adapter_schema",
    "adapter_state_object_schema",
    "adapter_state_validation_schema",
    "adapter_state_object_declared",
    "adapter_state_validation_preflight_instantiated",
    "issue_queue_state_object_validated",
    "demand_state_object_validated",
    "resident_index_state_object_validated",
    "queue_timing_state_object_validated",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_STATE_VALIDATION_ARTIFACT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_adapter_state_validation_preflight",
    "adapter_state_validation_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "state_shape_schema",
    "runtime_adapter_schema",
    "adapter_state_object_schema",
    "adapter_state_validation_schema",
    "validated_state_artifact_schema",
    "adapter_state_validation_preflight_instantiated",
    "adapter_state_validation_artifact_instantiated",
    "issue_queue_state_object_ready_for_runtime_adapter",
    "demand_state_object_ready_for_runtime_adapter",
    "resident_index_state_object_ready_for_runtime_adapter",
    "queue_timing_state_object_ready_for_runtime_adapter",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_INSTANTIATION_CANARY_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_state_validation_artifact",
    "state_validation_artifact_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "validated_state_artifact_schema",
    "runtime_adapter_instantiation_schema",
    "adapter_factory_declared",
    "adapter_constructor_resolved",
    "adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_CONSTRUCTOR_BINDING_PREFLIGHT_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_instantiation_canary",
    "instantiation_canary_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "runtime_adapter_instantiation_schema",
    "constructor_binding_schema",
    "adapter_factory_declared",
    "adapter_constructor_resolved",
    "constructor_inputs_bound",
    "binds_validated_state_artifact",
    "binds_queue_budget_parameters",
    "binds_shifted_issue_accounting",
    "adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_INSTANCE_CONSTRUCTION_PLAN_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_constructor_binding_preflight",
    "constructor_binding_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "constructor_binding_schema",
    "instance_construction_plan_schema",
    "constructor_inputs_bound",
    "construction_plan_sealed",
    "adapter_constructor_call_prepared",
    "adapter_instance_construction_planned",
    "adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_OBJECT_SHELL_EVIDENCE_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_instance_construction_plan",
    "instance_construction_plan_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "instance_construction_plan_schema",
    "adapter_object_shell_created",
    "disabled_adapter_shell_snapshot_created",
    "shell_enabled",
    "adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_OPERATION_REJECTION_CANARY_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_object_shell_evidence",
    "object_shell_evidence_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "operation_rejection_schema",
    "adapter_object_shell_created",
    "operation_rejection_canary_ran",
    "issue_prefetch_rejected",
    "demand_rejected",
    "shell_enabled",
    "adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_ACCOUNTING_DRY_RUN_CANARY_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_operation_rejection_canary",
    "operation_rejection_canary_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "accounting_dry_run_schema",
    "accounting_dry_run_adapter_created",
    "accounting_dry_run_operations_ran",
    "accounting_dry_run_enabled",
    "issue_prefetch_accepted",
    "duplicate_issue_suppressed",
    "demand_hit",
    "live_adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)
STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_MIXED_OUTCOME_DRY_RUN_CANARY_FIELDS = (
    "present",
    "stage",
    "status",
    "consumes_accounting_dry_run_canary",
    "accounting_dry_run_canary_status",
    "manager_backend",
    "manager_runtime_contract",
    "manager_runtime_mode",
    "mixed_outcome_schema",
    "mixed_outcome_adapter_created",
    "mixed_outcome_operations_ran",
    "accounting_dry_run_enabled",
    "issue_prefetch_accepted",
    "duplicate_issue_suppressed",
    "prefetched_demand_hit",
    "unprefetched_demand_hit",
    "unprefetched_demand_missed",
    "live_adapter_instance_created",
    "live_runtime_instantiated",
    "capacity_entries",
    "issue_lead_tokens",
    "queue_deadline_us",
    "lookahead_us",
    "queue_batch_size",
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
    "queue_service_us",
    "queue_total_span_us",
    "queue_wait_us",
    "queue_max_delay_us",
    "shifted_issue_accounting_enabled",
    "shifted_issue_accounted_packet_count",
    "shifted_issue_unique_issue_key_count",
    "decision",
    "block_reason",
    "execution_mode",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "issued_payload_count",
    "payload_bytes",
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
)


def _copy_metric_block(
    metrics: dict[str, Any],
    *,
    input_prefix: str,
    output_prefix: str,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        f"{output_prefix}_{field}": metrics.get(f"{input_prefix}_{field}")
        for field in fields
    }


def _targets_default_lab_gpu1(evidence: dict[str, Any]) -> bool:
    """Accept either physical GPU1 or logical GPU0 under HIP_VISIBLE_DEVICES=1."""

    device = _int_metric(evidence, "device")
    hip_visible_devices = evidence.get("hip_visible_devices")
    if device == 1:
        return True
    return device == 0 and str(hip_visible_devices) == "1"


def _validate_online_input_row_stats(
    metrics: dict[str, Any],
    *,
    expected_online_input_count: int,
    failure_prefix: str,
) -> list[str]:
    if expected_online_input_count <= 1:
        return []
    failures: list[str] = []
    row_counts = metrics.get("runner_online_prelaunch_input_row_counts")
    row_min = _int_metric(metrics, "runner_online_prelaunch_input_row_count_min")
    row_max = _int_metric(metrics, "runner_online_prelaunch_input_row_count_max")
    row_sum = _int_metric(metrics, "runner_online_prelaunch_input_row_count_sum")
    row_diverse = _bool_metric(
        metrics,
        "runner_online_prelaunch_input_row_count_diverse",
    )
    row_count_values: list[int] = []
    row_counts_valid = True
    if not isinstance(row_counts, list):
        failures.append(f"{failure_prefix}_row_counts_missing")
        row_counts_valid = False
    elif len(row_counts) != expected_online_input_count:
        failures.append(f"{failure_prefix}_row_counts_count_mismatch")
        row_counts_valid = False
    else:
        for index, value in enumerate(row_counts):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                failures.append(
                    f"{failure_prefix}_row_counts_{index:04d}_invalid"
                )
                row_counts_valid = False
                continue
            row_count_values.append(value)
    if row_min is None:
        failures.append(f"{failure_prefix}_row_count_min_missing")
    if row_max is None:
        failures.append(f"{failure_prefix}_row_count_max_missing")
    if row_sum is None:
        failures.append(f"{failure_prefix}_row_count_sum_missing")
    if row_diverse is not True:
        failures.append(f"{failure_prefix}_row_count_not_diverse")
    if row_min is not None and row_max is not None and row_min >= row_max:
        failures.append(f"{failure_prefix}_row_count_min_max_invalid")
    if row_counts_valid and row_count_values:
        if row_min != min(row_count_values):
            failures.append(f"{failure_prefix}_row_count_min_mismatch")
        if row_max != max(row_count_values):
            failures.append(f"{failure_prefix}_row_count_max_mismatch")
        if row_sum != sum(row_count_values):
            failures.append(f"{failure_prefix}_row_count_sum_mismatch")
        if row_diverse is not (min(row_count_values) < max(row_count_values)):
            failures.append(f"{failure_prefix}_row_count_diverse_mismatch")
    return failures


def _hex64_metric(metrics: dict[str, Any], key: str) -> int | None:
    value = metrics.get(key)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = int(value, 16)
    except ValueError:
        return None
    return parsed if 0 <= parsed <= _UINT64_MASK else None


def _sha256_hex_metric(metrics: dict[str, Any], key: str) -> str | None:
    value = metrics.get(key)
    if not isinstance(value, str) or len(value) != 64:
        return None
    try:
        int(value, 16)
    except ValueError:
        return None
    return value


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate_kernel_launch_context_runner_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str,
    failure_prefix: str,
    expected_device: int | None,
    require_error_count: bool = True,
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": _KERNEL_LAUNCH_CONTEXT_ABI_NAME,
        f"{prefix}_mode": _KERNEL_LAUNCH_CONTEXT_MODE,
        f"{prefix}_source": _KERNEL_LAUNCH_CONTEXT_SOURCE,
        f"{prefix}_version": 1,
        f"{prefix}_packet_chain_depth": _KERNEL_LAUNCH_CONTEXT_PACKET_CHAIN_DEPTH,
        f"{prefix}_struct_size": _KERNEL_LAUNCH_CONTEXT_STRUCT_SIZE,
        f"{prefix}_struct_align": _KERNEL_LAUNCH_CONTEXT_STRUCT_ALIGN,
        f"{prefix}_launch_descriptor_struct_size": (
            _KERNEL_LAUNCH_CONTEXT_LAUNCH_DESCRIPTOR_STRUCT_SIZE
        ),
        f"{prefix}_summary_struct_size": _KERNEL_LAUNCH_CONTEXT_SUMMARY_STRUCT_SIZE,
        f"{prefix}_pointer_size": _KERNEL_LAUNCH_CONTEXT_POINTER_SIZE,
        f"{prefix}_stream_domain": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    if require_error_count:
        expected_values[f"{prefix}_error_count"] = 0
    for key, expected in expected_values.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if expected_device is not None and metrics.get(f"{prefix}_device_ordinal") != expected_device:
        failures.append(f"{failure_prefix}_{prefix}_device_ordinal_mismatch")
    all_fields_key = f"{prefix}_all_handle_fields_read"
    if all_fields_key in metrics and metrics.get(all_fields_key) is not True:
        failures.append(f"{failure_prefix}_{all_fields_key}_mismatch")
    for key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
    ):
        if key in metrics and _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_kernel_launch_context_stub_summary_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str = "future_kernel_native_consumer_kernel_launch_context",
    failure_prefix: str,
    expected_rows: int | None,
    expected_device: int | None,
) -> list[str]:
    failures = _validate_kernel_launch_context_runner_metrics(
        metrics,
        prefix=prefix,
        failure_prefix=failure_prefix,
        expected_device=expected_device,
        require_error_count=False,
    )
    if (
        metrics.get(f"{prefix}_field_read_path")
        != (
            "kernel_launch_context_to_kernel_launch_descriptor_to_"
            "launch_envelope_args_ptr_to_launch_envelope_args_to_"
            "entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_"
            "program_view_rows"
        )
    ):
        failures.append(f"{failure_prefix}_{prefix}_field_read_path_mismatch")
    summary_expected: dict[str, Any] = {
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_struct_size": _KERNEL_LAUNCH_CONTEXT_SUMMARY_STRUCT_SIZE,
    }
    if expected_rows is not None:
        summary_expected.update(
            {
                f"{prefix}_summary_row_count": expected_rows,
                f"{prefix}_summary_row_ok_count": expected_rows,
                f"{prefix}_summary_descriptor_ptr_read_row_ok_count": expected_rows,
                f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": (
                    expected_rows
                ),
                f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": (
                    expected_rows
                ),
                f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": (
                    expected_rows
                ),
                f"{prefix}_summary_expert_id_read_row_ok_count": expected_rows,
                f"{prefix}_summary_address_key_hash_read_row_ok_count": expected_rows,
                f"{prefix}_summary_row_metadata_read_row_ok_count": expected_rows,
            }
        )
    for key, expected in summary_expected.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    for key in (
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        if _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_invocation_runner_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str,
    failure_prefix: str,
    expected_device: int | None,
    require_error_count: bool = True,
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": _INVOCATION_ABI_NAME,
        f"{prefix}_mode": _INVOCATION_MODE,
        f"{prefix}_source": _INVOCATION_SOURCE,
        f"{prefix}_version": 1,
        f"{prefix}_packet_chain_depth": _INVOCATION_PACKET_CHAIN_DEPTH,
        f"{prefix}_struct_size": _INVOCATION_STRUCT_SIZE,
        f"{prefix}_struct_align": _INVOCATION_STRUCT_ALIGN,
        f"{prefix}_context_struct_size": _INVOCATION_CONTEXT_STRUCT_SIZE,
        f"{prefix}_summary_struct_size": _INVOCATION_SUMMARY_STRUCT_SIZE,
        f"{prefix}_pointer_size": _INVOCATION_POINTER_SIZE,
        f"{prefix}_id": 1,
        f"{prefix}_stream_domain": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    if require_error_count:
        expected_values[f"{prefix}_error_count"] = 0
    for key, expected in expected_values.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if expected_device is not None and metrics.get(f"{prefix}_device_ordinal") != expected_device:
        failures.append(f"{failure_prefix}_{prefix}_device_ordinal_mismatch")
    all_fields_key = f"{prefix}_all_handle_fields_read"
    if all_fields_key in metrics and metrics.get(all_fields_key) is not True:
        failures.append(f"{failure_prefix}_{all_fields_key}_mismatch")
    for key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
    ):
        if key in metrics and _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_invocation_stub_summary_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str = "future_kernel_native_consumer_invocation",
    failure_prefix: str,
    expected_rows: int | None,
    expected_device: int | None,
) -> list[str]:
    failures = _validate_invocation_runner_metrics(
        metrics,
        prefix=prefix,
        failure_prefix=failure_prefix,
        expected_device=expected_device,
        require_error_count=False,
    )
    if (
        metrics.get(f"{prefix}_field_read_path")
        != (
            "invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_"
            "launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_"
            "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
        )
    ):
        failures.append(f"{failure_prefix}_{prefix}_field_read_path_mismatch")
    summary_expected: dict[str, Any] = {
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": _FUTURE_KERNEL_ALL_FIELD_MASK,
        f"{prefix}_summary_packet_valid": 1,
    }
    if expected_rows is not None:
        summary_expected.update(
            {
                f"{prefix}_summary_row_count": expected_rows,
                f"{prefix}_summary_row_ok_count": expected_rows,
                f"{prefix}_summary_descriptor_ptr_read_row_ok_count": expected_rows,
                f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": (
                    expected_rows
                ),
                f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": (
                    expected_rows
                ),
                f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": expected_rows,
                f"{prefix}_summary_expert_id_read_row_ok_count": expected_rows,
                f"{prefix}_summary_address_key_hash_read_row_ok_count": expected_rows,
                f"{prefix}_summary_row_metadata_read_row_ok_count": expected_rows,
            }
        )
    for key, expected in summary_expected.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    for key in (
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        if _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_invocation_cross_layer_metrics(
    runner_metrics: dict[str, Any],
    other_metrics: dict[str, Any],
    *,
    other_label: str,
    failure_prefix: str,
) -> list[str]:
    runner_prefix = "kernel_invocation"
    other_prefix = "future_kernel_native_consumer_invocation"
    pairs = (
        ("checked", "checked"),
        ("packet_chain_depth", "packet_chain_depth"),
        ("payload_bytes", "payload_bytes"),
        ("payload_deref_allowed", "payload_deref_allowed"),
        ("passed_to_kernel", "passed_to_kernel"),
        ("kernel_arg_pass_allowed", "kernel_arg_pass_allowed"),
        ("changes_kernel_launch_args", "changes_kernel_launch_args"),
        ("current_wna16_arg_compatible", "current_wna16_arg_compatible"),
        (
            "requires_wna16_arg_reinterpretation",
            "requires_wna16_arg_reinterpretation",
        ),
        ("row_hash_accumulator", "summary_row_hash_accumulator"),
        ("field_read_hash_accumulator", "summary_field_read_hash_accumulator"),
        (
            "row_metadata_hash_accumulator",
            "summary_row_metadata_hash_accumulator",
        ),
    )
    failures: list[str] = []
    for runner_suffix, other_suffix in pairs:
        runner_key = f"{runner_prefix}_{runner_suffix}"
        other_key = f"{other_prefix}_{other_suffix}"
        if runner_metrics.get(runner_key) != other_metrics.get(other_key):
            failures.append(
                f"{failure_prefix}_invocation_{other_label}_{runner_suffix}_mismatch"
            )
    return failures


def _validate_invocation_entry_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str,
    failure_prefix: str,
    expected_rows: int | None,
    compact_summary: bool = False,
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        f"{prefix}_checked": True,
        f"{prefix}_mode": _INVOCATION_ENTRY_MODE,
        f"{prefix}_source": _INVOCATION_ENTRY_SOURCE,
        f"{prefix}_packet_chain_depth": _INVOCATION_ENTRY_PACKET_CHAIN_DEPTH,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    if not compact_summary or f"{prefix}_abi_name" in metrics:
        expected_values[f"{prefix}_abi_name"] = _INVOCATION_ENTRY_ABI_NAME
    error_count_key = f"{prefix}_error_count"
    summary_error_count_key = f"{prefix}_summary_error_count"
    if compact_summary:
        if error_count_key not in metrics and summary_error_count_key not in metrics:
            failures.append(f"{failure_prefix}_{error_count_key}_missing")
        if error_count_key in metrics:
            expected_values[error_count_key] = 0
        if summary_error_count_key in metrics:
            expected_values[summary_error_count_key] = 0
        if (
            error_count_key in metrics
            and summary_error_count_key in metrics
            and metrics.get(error_count_key) != metrics.get(summary_error_count_key)
        ):
            failures.append(
                f"{failure_prefix}_{summary_error_count_key}_inconsistent"
            )
    else:
        expected_values[error_count_key] = 0
    all_fields_key = f"{prefix}_all_handle_fields_read"
    if all_fields_key in metrics:
        expected_values[all_fields_key] = True
    if expected_rows is not None:
        for suffix in ("summary_row_count", "summary_row_ok_count"):
            key = f"{prefix}_{suffix}"
            if key in metrics:
                expected_values[key] = expected_rows
        for suffix in (
            "summary_descriptor_ptr_read_row_ok_count",
            "summary_packed_weight_descriptor_read_row_ok_count",
            "summary_scale_metadata_handle_read_row_ok_count",
            "summary_aux_metadata_handle_read_row_ok_count",
            "summary_expert_id_read_row_ok_count",
            "summary_address_key_hash_read_row_ok_count",
            "summary_row_metadata_read_row_ok_count",
        ):
            if f"{prefix}_{suffix}" in metrics:
                expected_values[f"{prefix}_{suffix}"] = expected_rows
    for key, expected in expected_values.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if (
        f"{prefix}_field_read_path" in metrics
        and metrics.get(f"{prefix}_field_read_path")
        != _INVOCATION_ENTRY_FIELD_READ_PATH
    ):
        failures.append(f"{failure_prefix}_{prefix}_field_read_path_mismatch")
    for key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        if key in metrics and _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_endpoint_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str,
    failure_prefix: str,
    expected_rows: int | None,
    compact_summary: bool = False,
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        f"{prefix}_checked": True,
        f"{prefix}_mode": _ENDPOINT_MODE,
        f"{prefix}_source": _ENDPOINT_SOURCE,
        f"{prefix}_packet_chain_depth": _ENDPOINT_PACKET_CHAIN_DEPTH,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    if not compact_summary or f"{prefix}_abi_name" in metrics:
        expected_values[f"{prefix}_abi_name"] = _ENDPOINT_ABI_NAME
    error_count_key = f"{prefix}_error_count"
    summary_error_count_key = f"{prefix}_summary_error_count"
    if compact_summary:
        if error_count_key not in metrics and summary_error_count_key not in metrics:
            failures.append(f"{failure_prefix}_{error_count_key}_missing")
        if error_count_key in metrics:
            expected_values[error_count_key] = 0
        if summary_error_count_key in metrics:
            expected_values[summary_error_count_key] = 0
        if (
            error_count_key in metrics
            and summary_error_count_key in metrics
            and metrics.get(error_count_key) != metrics.get(summary_error_count_key)
        ):
            failures.append(
                f"{failure_prefix}_{summary_error_count_key}_inconsistent"
            )
    else:
        expected_values[error_count_key] = 0
    all_fields_key = f"{prefix}_all_handle_fields_read"
    if all_fields_key in metrics:
        expected_values[all_fields_key] = True
    if expected_rows is not None:
        for suffix in ("summary_row_count", "summary_row_ok_count"):
            key = f"{prefix}_{suffix}"
            if key in metrics:
                expected_values[key] = expected_rows
        for suffix in (
            "summary_descriptor_ptr_read_row_ok_count",
            "summary_packed_weight_descriptor_read_row_ok_count",
            "summary_scale_metadata_handle_read_row_ok_count",
            "summary_aux_metadata_handle_read_row_ok_count",
            "summary_expert_id_read_row_ok_count",
            "summary_address_key_hash_read_row_ok_count",
            "summary_row_metadata_read_row_ok_count",
        ):
            if f"{prefix}_{suffix}" in metrics:
                expected_values[f"{prefix}_{suffix}"] = expected_rows
    for key, expected in expected_values.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if (
        f"{prefix}_field_read_path" in metrics
        and metrics.get(f"{prefix}_field_read_path") != _ENDPOINT_FIELD_READ_PATH
    ):
        failures.append(f"{failure_prefix}_{prefix}_field_read_path_mismatch")
    for key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        if key in metrics and _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_endpoint_ptr_metrics(
    metrics: dict[str, Any],
    *,
    prefix: str,
    failure_prefix: str,
    expected_rows: int | None,
    compact_summary: bool = False,
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        f"{prefix}_checked": True,
        f"{prefix}_mode": _ENDPOINT_PTR_MODE,
        f"{prefix}_source": _ENDPOINT_PTR_SOURCE,
        f"{prefix}_packet_chain_depth": _ENDPOINT_PTR_PACKET_CHAIN_DEPTH,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
    }
    if not compact_summary or f"{prefix}_abi_name" in metrics:
        expected_values[f"{prefix}_abi_name"] = _ENDPOINT_PTR_ABI_NAME
    error_count_key = f"{prefix}_error_count"
    summary_error_count_key = f"{prefix}_summary_error_count"
    if compact_summary:
        if error_count_key not in metrics and summary_error_count_key not in metrics:
            failures.append(f"{failure_prefix}_{error_count_key}_missing")
        if error_count_key in metrics:
            expected_values[error_count_key] = 0
        if summary_error_count_key in metrics:
            expected_values[summary_error_count_key] = 0
        if (
            error_count_key in metrics
            and summary_error_count_key in metrics
            and metrics.get(error_count_key) != metrics.get(summary_error_count_key)
        ):
            failures.append(
                f"{failure_prefix}_{summary_error_count_key}_inconsistent"
            )
    else:
        expected_values[error_count_key] = 0
    all_fields_key = f"{prefix}_all_handle_fields_read"
    if all_fields_key in metrics:
        expected_values[all_fields_key] = True
    if expected_rows is not None:
        for suffix in ("summary_row_count", "summary_row_ok_count"):
            key = f"{prefix}_{suffix}"
            if key in metrics:
                expected_values[key] = expected_rows
        for suffix in (
            "summary_descriptor_ptr_read_row_ok_count",
            "summary_packed_weight_descriptor_read_row_ok_count",
            "summary_scale_metadata_handle_read_row_ok_count",
            "summary_aux_metadata_handle_read_row_ok_count",
            "summary_expert_id_read_row_ok_count",
            "summary_address_key_hash_read_row_ok_count",
            "summary_row_metadata_read_row_ok_count",
        ):
            key = f"{prefix}_{suffix}"
            if key in metrics:
                expected_values[key] = expected_rows
    for key, expected in expected_values.items():
        if metrics.get(key) != expected:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if (
        f"{prefix}_field_read_path" in metrics
        and metrics.get(f"{prefix}_field_read_path") != _ENDPOINT_PTR_FIELD_READ_PATH
    ):
        failures.append(f"{failure_prefix}_{prefix}_field_read_path_mismatch")
    for key in (
        f"{prefix}_row_hash_accumulator",
        f"{prefix}_field_read_hash_accumulator",
        f"{prefix}_row_metadata_hash_accumulator",
        f"{prefix}_summary_row_hash_accumulator",
        f"{prefix}_summary_field_read_hash_accumulator",
        f"{prefix}_summary_row_metadata_hash_accumulator",
    ):
        if key in metrics and _hex64_metric(metrics, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _mix64(value: int) -> int:
    x = value & _UINT64_MASK
    x ^= x >> 33
    x = (x * 0xFF51AFD7ED558CCD) & _UINT64_MASK
    x ^= x >> 33
    x = (x * 0xC4CEB9FE1A85EC53) & _UINT64_MASK
    x ^= x >> 33
    return x & _UINT64_MASK


def _program_iteration_hash(
    *,
    grid_x: int,
    block_x: int,
    row_offset: int,
    row_limit: int,
    last_program_active_rows: int,
    inactive_lane_count: int,
) -> int:
    return (
        _mix64(grid_x + 0xD15C2001)
        ^ _mix64(block_x + 0xD15C2002)
        ^ _mix64(row_offset + 0xD15C2003)
        ^ _mix64(row_limit + 0xD15C2004)
        ^ _mix64(last_program_active_rows + 0xD15C2005)
        ^ _mix64(inactive_lane_count + 0xD15C2006)
    ) & _UINT64_MASK


def _check_metric_equals(
    metrics: dict[str, Any],
    key: str,
    expected: Any,
) -> list[str]:
    actual = metrics.get(key)
    return [] if _strict_scalar_equal(actual, expected) else [f"{key}_mismatch"]


def _check_metric_equals_if_present(
    metrics: dict[str, Any],
    key: str,
    expected: Any,
) -> list[str]:
    return [] if key not in metrics else _check_metric_equals(metrics, key, expected)


def _strict_scalar_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return isinstance(actual, bool) and actual is expected
    if isinstance(expected, int):
        return (
            isinstance(actual, int)
            and not isinstance(actual, bool)
            and actual == expected
        )
    return actual == expected


def _check_future_field_mask_summary(
    summary: dict[str, Any],
    *,
    prefix: str,
    field_prefix: str,
    expected_field_name: str,
) -> list[str]:
    failures: list[str] = []
    field_mask = summary.get(f"{field_prefix}_field_mask")
    required_mask = summary.get(f"{field_prefix}_required_field_mask")
    if field_mask is None:
        return [f"{prefix}_{field_prefix}_field_mask_missing"]
    if required_mask is None:
        return [f"{prefix}_{field_prefix}_required_field_mask_missing"]
    if (
        not isinstance(field_mask, int)
        or isinstance(field_mask, bool)
        or not isinstance(required_mask, int)
        or isinstance(required_mask, bool)
    ):
        return [f"{prefix}_{field_prefix}_field_mask_type_mismatch"]
    if required_mask != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
        failures.append(f"{prefix}_{field_prefix}_required_field_mask_mismatch")
    if (
        field_mask & _FUTURE_KERNEL_REQUIRED_FIELD_MASK
        != _FUTURE_KERNEL_REQUIRED_FIELD_MASK
    ):
        failures.append(f"{prefix}_{field_prefix}_required_field_mask_not_covered")
    if field_mask & ~_FUTURE_KERNEL_ALL_FIELD_MASK:
        failures.append(f"{prefix}_{field_prefix}_field_mask_unknown_bits")
    if expected_field_name == "aux_metadata_handle" and not (
        field_mask & _FUTURE_KERNEL_AUX_FIELD_MASK
    ):
        failures.append(f"{prefix}_{field_prefix}_aux_field_mask_missing")
    return failures


def _check_layout_summary_fields(
    summary: dict[str, Any],
    *,
    prefix: str,
    fields: list[str],
    expected_values: dict[str, int],
    struct_size_key: str,
) -> list[str]:
    failures: list[str] = []
    for field in fields:
        value = summary.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            failures.append(f"{prefix}_{field}_missing_or_not_int")
            continue
        expected = expected_values.get(field)
        if expected is not None and value != expected:
            failures.append(f"{prefix}_{field}_mismatch:{value!r}!={expected!r}")
        if value < 0:
            failures.append(f"{prefix}_{field}_negative")
        if "offset" not in field and value <= 0:
            failures.append(f"{prefix}_{field}_not_positive")
        if "offset" in field:
            struct_size = summary.get(struct_size_key)
            if isinstance(struct_size, int) and not isinstance(struct_size, bool):
                if value >= struct_size:
                    failures.append(f"{prefix}_{field}_outside_struct")
    return failures


def _validate_native_bridge_evidence(metrics: dict[str, Any]) -> list[str]:
    prefix = _NATIVE_BRIDGE_METRIC_PREFIX
    failures: list[str] = []
    checked = _int_metric(metrics, f"{prefix}checked_count")
    if checked is None or checked <= 0:
        failures.append(f"{prefix}checked_count_invalid")
        checked = None
    ok = _int_metric(metrics, f"{prefix}ok_count")
    if checked is not None and ok != checked:
        failures.append(f"{prefix}ok_count_mismatch")
    for suffix in (
        "failure_count",
        "payload_bytes",
        "payload_violation_count",
        "ready_credit_count",
        "changes_router_count",
        "changes_descriptor_order_count",
        "passed_to_kernel_count",
        "kernel_arg_violation_count",
        "required_handle_zero_count",
        "expert_id_invalid_count",
        "address_key_hash_zero_count",
    ):
        failures.extend(_check_metric_equals(metrics, f"{prefix}{suffix}", 0))
    failures.extend(
        _check_metric_equals(
            metrics,
            f"{prefix}mode",
            "readonly_native_typed_consumer_bridge_check",
        )
    )
    return failures


def _validate_native_stub_evidence(metrics: dict[str, Any]) -> list[str]:
    prefix = _NATIVE_STUB_METRIC_PREFIX
    failures: list[str] = []
    checked = _int_metric(metrics, f"{prefix}checked_count")
    if checked is None or checked <= 0:
        failures.append(f"{prefix}checked_count_invalid")
        checked = None
    for suffix in ("ready_count", "ok_count", "requested_count", "blocked_count"):
        value = _int_metric(metrics, f"{prefix}{suffix}")
        if checked is not None and value != checked:
            failures.append(f"{prefix}{suffix}_mismatch")
    if checked is not None:
        for suffix in ("native_checker_invoked_count", "native_bridge_ok_count"):
            value = _int_metric(metrics, f"{prefix}{suffix}")
            if value != checked:
                failures.append(f"{prefix}{suffix}_mismatch")
    for suffix in (
        "failure_count",
        "payload_bytes",
        "payload_violation_count",
        "ready_credit_count",
        "changes_router_count",
        "changes_descriptor_order_count",
        "passed_to_kernel_count",
        "kernel_arg_violation_count",
        "native_stub_invoked_count",
        "required_handle_zero_count",
        "expert_id_invalid_count",
        "address_key_hash_zero_count",
    ):
        failures.extend(_check_metric_equals(metrics, f"{prefix}{suffix}", 0))
    failures.extend(
        _check_metric_equals(
            metrics,
            f"{prefix}mode",
            "readonly_native_stub_online_invocation_canary",
        )
    )
    failures.extend(
        _check_metric_equals(
            metrics,
            f"{prefix}block_reason",
            "native_stub_live_disabled",
        )
    )
    return failures


def _validate_single_field_canary_evidence(
    metrics: dict[str, Any],
    *,
    expected_field_name: str = "scale_metadata_handle",
) -> list[str]:
    prefix = _SINGLE_FIELD_CANARY_METRIC_PREFIX
    failures: list[str] = []
    checked = _int_metric(metrics, f"{prefix}checked_count")
    if checked is None or checked <= 0:
        failures.append(f"{prefix}checked_count_invalid")
        checked = None
    row_count = _int_metric(metrics, f"{prefix}row_count")
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}row_count_invalid")
        row_count = None
    for suffix in (
        "ready_count",
        "hash_checked_count",
        "table_object_hash_checked_count",
        "semantic_adapter_hash_checked_count",
        "field_handle_hash_checked_count",
        "semantic_field_hash_checked_count",
        "blocked_count",
    ):
        value = _int_metric(metrics, f"{prefix}{suffix}")
        if checked is not None and value != checked:
            failures.append(f"{prefix}{suffix}_mismatch")
    for suffix in (
        "mode_checked_count",
        "field_name_checked_count",
        "source_checked_count",
        "block_reason_checked_count",
    ):
        key = f"{prefix}{suffix}"
        if key in metrics:
            value = _int_metric(metrics, key)
            if checked is not None and value != checked:
                failures.append(f"{key}_mismatch")
    for suffix in (
        "field_handle_count",
        "field_handle_nonzero_count",
        "parity_ok_count",
    ):
        value = _int_metric(metrics, f"{prefix}{suffix}")
        if row_count is not None and value != row_count:
            failures.append(f"{prefix}{suffix}_mismatch")
    for suffix in (
        "hash_missing_count",
        "table_object_hash_missing_count",
        "semantic_adapter_hash_missing_count",
        "field_handle_hash_missing_count",
        "semantic_field_hash_missing_count",
        "mode_missing_count",
        "mode_mismatch_count",
        "field_name_missing_count",
        "field_name_mismatch_count",
        "source_missing_count",
        "source_mismatch_count",
        "block_reason_missing_count",
        "block_reason_mismatch_count",
        "field_handle_zero_count",
        "parity_mismatch_count",
        "live_enabled_count",
        "payload_bytes",
        "payload_violation_count",
        "ready_credit_count",
        "passed_to_kernel_count",
        "changes_kernel_launch_args_count",
        "kernel_arg_violation_count",
        "live_compatible_with_current_wna16_args_count",
    ):
        failures.extend(
            _check_metric_equals_if_present(metrics, f"{prefix}{suffix}", 0)
        )
    expected_values = {
        "mode": "readonly_single_field_handle_handoff_canary",
        "field_name": expected_field_name,
        "source": "semantic_handle_table",
        "block_reason": "single_field_handoff_live_disabled",
    }
    for suffix, expected in expected_values.items():
        failures.extend(_check_metric_equals(metrics, f"{prefix}{suffix}", expected))
    return failures


def _validate_typed_row_consumer_path_evidence(
    metrics: dict[str, Any],
) -> list[str]:
    prefix = _TYPED_ROW_CONSUMER_PATH_METRIC_PREFIX
    failures: list[str] = []
    checked = _int_metric(metrics, f"{prefix}checked_count")
    if checked is None or checked <= 0:
        failures.append(f"{prefix}checked_count_invalid")
        checked = None
    row_count = _int_metric(metrics, f"{prefix}row_count")
    row_ok = _int_metric(metrics, f"{prefix}row_ok_count")
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}row_count_invalid")
        row_count = None
    if row_count is not None and row_ok != row_count:
        failures.append(f"{prefix}row_ok_count_mismatch")
    for suffix in ("ready_count",):
        value = _int_metric(metrics, f"{prefix}{suffix}")
        if checked is not None and value != checked:
            failures.append(f"{prefix}{suffix}_mismatch")
    for suffix in (
        "error_count",
        "failure_count",
        "payload_bytes",
        "payload_violation_count",
        "passed_to_kernel_count",
        "kernel_arg_violation_count",
        "current_wna16_arg_compatible_count",
    ):
        failures.extend(_check_metric_equals_if_present(metrics, f"{prefix}{suffix}", 0))
    expected_values = {
        "mode": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_MODE,
        "name": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_NAME,
        "source": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_PATH_SOURCE,
        "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    }
    for suffix, expected in expected_values.items():
        failures.extend(_check_metric_equals(metrics, f"{prefix}{suffix}", expected))
    column_max = _int_metric(metrics, f"{prefix}column_count_max")
    column_min = _int_metric(metrics, f"{prefix}column_count_min")
    expected_columns = len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
    if column_max != expected_columns:
        failures.append(f"{prefix}column_count_max_mismatch")
    if column_min != expected_columns:
        failures.append(f"{prefix}column_count_min_mismatch")
    return failures


def _validate_future_wna16_single_field_handoff_all_fields_summary(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if evidence.get("passed") is not True:
        failures.append("summary_not_passed")
    if evidence.get("failures") not in ([], None):
        failures.append("summary_failures_not_empty")
    if evidence.get("summary_name") != (
        "future_wna16_single_field_handoff_all_fields_128strict"
    ):
        failures.append("summary_name_mismatch")
    if evidence.get("field_count") != len(_FUTURE_WNA16_SINGLE_FIELD_HANDOFF_FIELDS):
        failures.append("field_count_mismatch")

    safety = evidence.get("safety_contract")
    if not isinstance(safety, dict):
        failures.append("safety_contract_missing")
    else:
        expected_safety = {
            "payload_bytes": 0,
            "live_enabled": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "requires_wna16_arg_reinterpretation": False,
            "explicit_typed_abi_slot": True,
            "reuses_current_wna16_arg_slot": False,
        }
        for key, expected in expected_safety.items():
            if safety.get(key) != expected:
                failures.append(f"safety_contract_{key}_mismatch")

    fields = evidence.get("fields")
    if not isinstance(fields, dict):
        failures.append("fields_missing")
        return failures

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_single_field_handoff_all_fields_min_source_count"
        ]
    )
    row_count_ref: int | None = None
    for field, (expected_kind, expected_mask) in (
        _FUTURE_WNA16_SINGLE_FIELD_HANDOFF_FIELDS.items()
    ):
        record = fields.get(field)
        if not isinstance(record, dict):
            failures.append(f"{field}_record_missing")
            continue
        if record.get("passed") is not True:
            failures.append(f"{field}_not_passed")
        selected_source_count = _int_metric(record, "selected_source_count")
        if selected_source_count is None or selected_source_count < min_source_count:
            failures.append(f"{field}_selected_source_count_invalid")
        if record.get("abi_name") != "premap_future_wna16_single_field_handoff_canary_v1":
            failures.append(f"{field}_abi_name_mismatch")
        if record.get("mode") != _FUTURE_WNA16_SINGLE_FIELD_HANDOFF_MODE:
            failures.append(f"{field}_mode_mismatch")
        if record.get("source") != _FUTURE_WNA16_SINGLE_FIELD_HANDOFF_SOURCE:
            failures.append(f"{field}_source_mismatch")
        if record.get("field_read_path") != _FUTURE_WNA16_SINGLE_FIELD_HANDOFF_READ_PATH:
            failures.append(f"{field}_field_read_path_mismatch")
        if record.get("field_name") != field:
            failures.append(f"{field}_field_name_mismatch")
        if record.get("field_kind") != expected_kind:
            failures.append(f"{field}_field_kind_mismatch")
        if record.get("field_mask") != expected_mask:
            failures.append(f"{field}_field_mask_mismatch")

        row_count = _int_metric(record, "row_count")
        row_ok_count = _int_metric(record, "row_ok_count")
        error_count = _int_metric(record, "error_count")
        if row_count is None or row_count <= 0:
            failures.append(f"{field}_row_count_invalid")
        elif row_count_ref is None:
            row_count_ref = row_count
        elif row_count != row_count_ref:
            failures.append(f"{field}_row_count_mismatch")
        if row_count is not None and row_ok_count != row_count:
            failures.append(f"{field}_row_ok_count_mismatch")
        if error_count != 0:
            failures.append(f"{field}_error_count_mismatch")
        if _hex64_metric(record, "hash_accumulator") is None:
            failures.append(f"{field}_hash_accumulator_invalid")

        expected_record_safety = {
            "payload_bytes": 0,
            "live_enabled": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "requires_wna16_arg_reinterpretation": False,
            "explicit_typed_abi_slot": True,
            "reuses_current_wna16_arg_slot": False,
        }
        for key, expected in expected_record_safety.items():
            if record.get(key) != expected:
                failures.append(f"{field}_{key}_mismatch")
    return failures


def _validate_future_wna16_typed_slot_fourth_field_handoff_canary(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if evidence.get("passed") is not True:
        failures.append("canary_not_passed")
    if evidence.get("failures") not in ([], None):
        failures.append("canary_failures_not_empty")
    if not _targets_default_lab_gpu1(evidence):
        failures.append("device_not_gpu1")

    expected_values = {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
        ),
        "fourth_field_handoff_canary_name": (
            "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
        ),
        "fourth_field_handoff_canary_mode": (
            "readonly_future_wna16_typed_slot_fourth_field_handoff_canary"
        ),
        "fourth_field_handoff_canary_source": (
            "premap_future_wna16_typed_slot_third_field_handoff_canary_v1"
        ),
        "fourth_field_handoff_scope": (
            "independent_future_wna16_typed_slot_fourth_field_handoff_canary"
        ),
        "first_field_name": "scale_metadata_handle",
        "second_field_name": "aux_metadata_handle",
        "third_field_name": "packed_weight_descriptor",
        "fourth_field_name": (
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_fourth_field_handoff_canary_field"
            ]
        ),
        "fourth_field_kind": 1,
        "fourth_field_mask": 1,
        "fourth_field_handoff_block_reason": "fourth_field_handoff_live_disabled",
        "next_runtime_stage": (
            "promote_future_wna16_typed_slot_all_four_field_handoff_gate_to_lab_preflight"
        ),
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    expected_bools = {
        "previous_field_gate_ready": True,
        "fourth_field_handoff_canary_native_requested": True,
        "fourth_field_handoff_canary_native_executed": True,
        "fourth_field_handoff_canary_native_passed": True,
        "fourth_field_handoff_live_enabled": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "expected_measures_vllm_latency": False,
        "expected_measures_tpot": False,
        "expected_wna16_benchmark_ready": False,
        "expected_uses_current_wna16_args": False,
        "expected_passes_current_wna16_args": False,
        "expected_current_wna16_arg_compatible": False,
        "expected_requires_wna16_arg_reinterpretation": False,
        "expected_payload_deref_allowed": False,
        "expected_kernel_arg_pass_allowed": False,
        "expected_passed_to_kernel": False,
        "expected_changes_kernel_launch_args": False,
    }
    for key, expected in expected_bools.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    expected_zero_values = {
        "payload_bytes": 0,
        "expected_payload_bytes": 0,
    }
    for key, expected in expected_zero_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_fourth_field_handoff_canary_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    previous_source_count = _int_metric(evidence, "previous_field_input_json_count")
    max_inputs = _int_metric(evidence, "max_inputs")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    field_read_row_ok = _int_metric(
        evidence,
        "fourth_field_handoff_field_read_row_ok_count",
    )
    runner_row_count = _int_metric(
        evidence,
        "fourth_field_handoff_canary_runner_row_count",
    )
    runner_row_ok = _int_metric(
        evidence,
        "fourth_field_handoff_canary_runner_row_ok_count",
    )
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if previous_source_count is None or previous_source_count < min_source_count:
        failures.append("previous_field_input_json_count_invalid")
    if source_count is not None and max_inputs != source_count:
        failures.append("max_inputs_mismatch")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    else:
        for key, value in {
            "row_ok_count": row_ok_count,
            "fourth_field_handoff_field_read_row_ok_count": field_read_row_ok,
            "fourth_field_handoff_canary_runner_row_count": runner_row_count,
            "fourth_field_handoff_canary_runner_row_ok_count": runner_row_ok,
        }.items():
            if value != row_count:
                failures.append(f"{key}_mismatch")

    for key in (
        "fourth_field_handoff_field_read_hash",
        "fourth_field_handoff_canary_runner_hash",
        "third_field_read_hash",
        "third_field_native_hash",
    ):
        if _hex64_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    for key in (
        "fourth_field_underlying_sha256",
        "payloadless_execution_sha256",
        "previous_field_sha256",
    ):
        if _sha256_hex_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    for key in (
        "fourth_field_underlying_json",
        "payloadless_execution_json",
        "previous_field_json",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
    return failures


def _validate_future_wna16_typed_slot_all_four_field_consumer(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_all_four_field_consumer"
        ),
        "all_four_field_consumer_name": (
            "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
        ),
        "all_four_field_consumer_mode": (
            "readonly_future_wna16_typed_slot_all_four_field_consumer"
        ),
        "all_four_field_consumer_source": (
            "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
        ),
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "passed": True,
        "failures": [],
        "native_consumer_executed": True,
        "native_consumer_passed": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_all_four_field_consumer_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    input_count = _int_metric(evidence, "input_json_count")
    selected_input_count = _int_metric(evidence, "selected_input_json_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if input_count is not None and source_count is not None and input_count < source_count:
        failures.append("input_json_count_lt_source_count")
    if source_count is not None and selected_input_count != source_count:
        failures.append("selected_input_json_count_mismatch")
    selected_manifest = evidence.get("selected_input_manifest_sha256")
    post_manifest = evidence.get("post_native_input_manifest_sha256")
    if not _is_sha256_hex(selected_manifest):
        failures.append("selected_input_manifest_sha256_invalid")
    if not _is_sha256_hex(post_manifest):
        failures.append("post_native_input_manifest_sha256_invalid")
    elif post_manifest != selected_manifest:
        failures.append("post_native_input_manifest_sha256_mismatch")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")

    for path_key, sha_key in (
        ("fourth_field_json", "fourth_field_sha256"),
        ("native_consumer_json", "native_consumer_sha256"),
        ("merged_input_json", "merged_input_sha256"),
        ("stub_output_json", "stub_output_sha256"),
    ):
        value = evidence.get(path_key)
        if not isinstance(value, str) or not value:
            failures.append(f"{path_key}_missing")
        if not _is_sha256_hex(evidence.get(sha_key)):
            failures.append(f"{sha_key}_invalid")

    field_names = evidence.get("field_names")
    if field_names != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("field_names_mismatch")
    if row_count is not None:
        for prefix in (
            "future_wna16_kernel_side_consumer_execution",
            "wna16_side_consumer_variant_execution",
        ):
            if evidence.get(f"{prefix}_all_handle_fields_read") is not True:
                failures.append(f"{prefix}_all_handle_fields_read_mismatch")
            for key in (
                f"{prefix}_hash_accumulator",
                f"{prefix}_handle_projection_hash_accumulator",
            ):
                if _hex64_metric(evidence, key) is None:
                    failures.append(f"{key}_invalid")
            for field in ARG_SLOT_MIRROR_FIELDS:
                count_key = f"{prefix}_{field}_read_row_ok_count"
                hash_key = f"{prefix}_{field}_read_hash_accumulator"
                if _int_metric(evidence, count_key) != row_count:
                    failures.append(f"{count_key}_mismatch")
                if _hex64_metric(evidence, hash_key) is None:
                    failures.append(f"{hash_key}_invalid")
    return failures


def _validate_future_wna16_kernel_side_typed_consumer_path(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": "future_wna16_kernel_side_typed_consumer_path",
        "kernel_side_typed_consumer_path_name": (
            "premap_future_wna16_kernel_side_typed_consumer_path_v1"
        ),
        "kernel_side_typed_consumer_path_mode": (
            "independent_future_wna16_kernel_side_typed_consumer_path"
        ),
        "kernel_side_typed_consumer_path_source": (
            "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
        ),
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "passed": True,
        "failures": [],
        "all_four_gate_ready": True,
        "native_consumer_executed": True,
        "native_consumer_passed": True,
        "independent_kernel_side_consumer_path": True,
        "explicit_typed_abi_slot": True,
        "future_wna16_kernel_side_consumer_execution_checked": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_checked": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_kernel_side_typed_consumer_path_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    input_count = _int_metric(evidence, "input_json_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if input_count is None or input_count < min_source_count:
        failures.append("input_json_count_invalid")
    if source_count is not None and input_count != source_count:
        failures.append("input_json_count_mismatch")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    for prefix in (
        "future_wna16_kernel_side_consumer_execution",
        "wna16_side_consumer_variant_execution",
    ):
        prefix_row_count = _int_metric(evidence, f"{prefix}_row_count")
        prefix_row_ok_count = _int_metric(evidence, f"{prefix}_row_ok_count")
        if row_count is not None and prefix_row_count != row_count:
            failures.append(f"{prefix}_row_count_mismatch")
        if row_count is not None and prefix_row_ok_count != row_count:
            failures.append(f"{prefix}_row_ok_count_mismatch")
        if _hex64_metric(evidence, f"{prefix}_handle_projection_hash_accumulator") is None:
            failures.append(f"{prefix}_handle_projection_hash_invalid")

    if not _is_sha256_hex(evidence.get("selected_input_manifest_sha256")):
        failures.append("selected_input_manifest_sha256_invalid")
    for path_key, sha_key in (
        ("all_four_json", "all_four_sha256"),
        ("native_consumer_json", "native_consumer_sha256"),
        ("merged_input_json", "merged_input_sha256"),
        ("stub_output_json", "stub_output_sha256"),
    ):
        value = evidence.get(path_key)
        if not isinstance(value, str) or not value:
            failures.append(f"{path_key}_missing")
        if not _is_sha256_hex(evidence.get(sha_key)):
            failures.append(f"{sha_key}_invalid")
    return failures


def _validate_future_wna16_typed_slot_payloadless_execution(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_payloadless_execution",
        "payloadless_execution_name": (
            "premap_future_wna16_typed_slot_payloadless_execution_v1"
        ),
        "payloadless_execution_mode": (
            "independent_future_wna16_typed_slot_payloadless_execution"
        ),
        "payloadless_execution_source": (
            "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1"
        ),
        "payloadless_execution_scope": (
            "independent_native_typed_slot_payloadless_execution"
        ),
        "passed": True,
        "failures": [],
        "payloadless_execution_ready": True,
        "payloadless_execution_gate_ready": True,
        "payloadless_execution_lab_preflight_ready": True,
        "payloadless_execution_native_artifact_ready": True,
        "payloadless_execution_native_requested": True,
        "payloadless_execution_native_executed": True,
        "payloadless_execution_native_passed": True,
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
        "payload_bytes": 0,
        "expected_payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_payloadless_execution_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    if source_count is not None:
        for key in (
            "fourth_field_handoff_source_count",
            "all_four_field_consumer_source_count",
            "future_wna16_kernel_side_typed_consumer_path_source_count",
            "future_wna16_kernel_side_typed_consumer_path_input_json_count",
        ):
            if _int_metric(evidence, key) != source_count:
                failures.append(f"{key}_mismatch")
    if row_count is not None:
        for key in (
            "fourth_field_handoff_row_count",
            "fourth_field_handoff_row_ok_count",
            "all_four_field_consumer_row_count",
            "all_four_field_consumer_row_ok_count",
            "future_wna16_kernel_side_typed_consumer_path_row_count",
            "future_wna16_kernel_side_typed_consumer_path_row_ok_count",
        ):
            if _int_metric(evidence, key) != row_count:
                failures.append(f"{key}_mismatch")
        row_ok_counts = evidence.get("field_read_row_ok_counts")
        if not isinstance(row_ok_counts, dict):
            failures.append("field_read_row_ok_counts_missing")
        else:
            for field in ARG_SLOT_MIRROR_FIELDS:
                if row_ok_counts.get(field) != row_count:
                    failures.append(f"{field}_read_row_ok_count_mismatch")
    if evidence.get("field_names") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("field_names_mismatch")
    field_hashes = evidence.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("field_read_hashes_missing")
    else:
        for field in ARG_SLOT_MIRROR_FIELDS:
            if _hex64_metric(field_hashes, field) is None:
                failures.append(f"{field}_read_hash_invalid")
    for key in (
        "payloadless_execution_runner_sha256",
        "payloadless_execution_timing_stub_sha256",
        "benchmark_sha256",
        "fourth_field_handoff_evidence_sha256",
        "all_four_field_consumer_fourth_field_sha256",
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256",
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256",
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256",
        "entry_args_ptr_sweep_sha256",
        "entry_args_ptr_sweep_check_sha256",
    ):
        if _sha256_hex_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    for key in (
        "payloadless_execution_runner_json",
        "payloadless_execution_timing_stub_json",
        "payloadless_execution_canary_json",
        "benchmark_json",
        "fourth_field_handoff_evidence_path",
        "future_wna16_kernel_side_typed_consumer_path_evidence_path",
        "entry_args_ptr_sweep_json",
        "entry_args_ptr_sweep_check_json",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
    for key in (
        "payloadless_execution_native_host_wall_ms",
        "payloadless_execution_outer_wall_ms",
    ):
        value = evidence.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            failures.append(f"{key}_invalid")
    stats = evidence.get("benchmark_native_stub_host_wall_ms_stats")
    if not isinstance(stats, dict) or stats.get("count") != 3:
        failures.append("benchmark_native_stub_host_wall_ms_stats_invalid")
    if _int_metric(evidence, "benchmark_repeat_count_measured") != 3:
        failures.append("benchmark_repeat_count_measured_invalid")
    return failures


def _validate_future_wna16_typed_slot_kernel_variant_execution(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
        "execution_name": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        "execution_mode": "independent_future_wna16_typed_slot_kernel_variant_execution",
        "execution_source": "premap_future_wna16_typed_slot_payloadless_execution_v1",
        "future_wna16_variant_execution_scope": (
            "independent_native_typed_slot_kernel_variant_execution"
        ),
        "passed": True,
        "failures": [],
        "payloadless_gate_ready": True,
        "future_wna16_variant_execution_ready": True,
        "future_wna16_variant_execution_native_requested": True,
        "future_wna16_variant_execution_native_executed": True,
        "future_wna16_variant_execution_native_passed": True,
        "future_wna16_variant_execution_native_artifact_ready": True,
        "future_wna16_variant_execution_not_current_wna16_kernel": True,
        "benchmark_is_current_wna16_fused_moe": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
        ),
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_kernel_variant_execution_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    if evidence.get("field_names") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("field_names_mismatch")
    row_ok_counts = evidence.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = evidence.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("field_read_hashes_missing")
        field_hashes = {}
    for field in ARG_SLOT_MIRROR_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"{field}_read_row_ok_count_mismatch")
        if _hex64_metric(field_hashes, field) is None:
            failures.append(f"{field}_read_hash_invalid")
    for key in (
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
        "payloadless_sha256",
        "future_wna16_variant_execution_native_sha256",
    ):
        if key.endswith("_sha256"):
            if _sha256_hex_metric(evidence, key) is None:
                failures.append(f"{key}_invalid")
        elif _hex64_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    for key in (
        "payloadless_json",
        "future_wna16_variant_execution_native_json",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
    for key in (
        "future_wna16_variant_execution_native_host_wall_ms",
        "future_wna16_variant_execution_outer_wall_ms",
    ):
        value = evidence.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            failures.append(f"{key}_invalid")
    return failures


def _validate_future_wna16_typed_slot_kernel_variant_useful_consumer(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_useful_consumer",
        "useful_consumer_name": "premap_future_wna16_typed_slot_useful_consumer_v1",
        "useful_consumer_mode": "independent_wna16_side_typed_slot_useful_consumer",
        "useful_consumer_source": (
            "premap_future_wna16_typed_slot_kernel_variant_execution_v1"
        ),
        "useful_consumer_semantics": (
            "wna16_side_variant_all_four_field_projection"
        ),
        "passed": True,
        "failures": [],
        "useful_consumer_ready": True,
        "useful_consumer_native_stub_checked": True,
        "benchmark_is_current_wna16_fused_moe": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
        "wna16_side_consumer_variant_execution_checked": True,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
        ),
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_kernel_variant_useful_consumer_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    if _int_metric(evidence, "useful_consumer_rows_consumed") != row_count:
        failures.append("useful_consumer_rows_consumed_mismatch")
    if evidence.get("field_names") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("field_names_mismatch")
    if evidence.get("useful_consumer_fields_consumed") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("useful_consumer_fields_consumed_mismatch")
    row_ok_counts = evidence.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = evidence.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("field_read_hashes_missing")
        field_hashes = {}
    useful_hashes = evidence.get("useful_consumer_field_read_hashes")
    if not isinstance(useful_hashes, dict):
        failures.append("useful_consumer_field_read_hashes_missing")
        useful_hashes = {}
    for field in ARG_SLOT_MIRROR_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"{field}_read_row_ok_count_mismatch")
        if _hex64_metric(field_hashes, field) is None:
            failures.append(f"{field}_read_hash_invalid")
        if _hex64_metric(useful_hashes, field) is None:
            failures.append(f"useful_{field}_read_hash_invalid")
    for key in (
        "execution_sha256",
        "native_timing_sha256",
        "native_stub_sha256",
        "useful_consumer_hash",
    ):
        if _sha256_hex_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    for key in (
        "execution_json",
        "native_timing_json",
        "native_stub_json",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
    if _int_metric(
        evidence,
        "wna16_side_consumer_variant_execution_row_count",
    ) != row_count:
        failures.append("wna16_side_execution_row_count_mismatch")
    if _int_metric(
        evidence,
        "wna16_side_consumer_variant_execution_row_ok_count",
    ) != row_count:
        failures.append("wna16_side_execution_row_ok_count_mismatch")
    for key in (
        "wna16_side_consumer_variant_execution_hash_accumulator",
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator",
    ):
        if _hex64_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    return failures


def _validate_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
        ),
        "payloadless_useful_execution_name": (
            "premap_future_wna16_typed_slot_payloadless_useful_execution_v1"
        ),
        "payloadless_useful_execution_mode": (
            "independent_future_wna16_typed_slot_payloadless_useful_execution"
        ),
        "payloadless_useful_execution_source": (
            "premap_future_wna16_typed_slot_kernel_variant_useful_consumer_v1"
        ),
        "passed": True,
        "failures": [],
        "payloadless_useful_execution_ready": True,
        "payloadless_useful_execution_gate_ready": True,
        "payloadless_useful_execution_chain_checked": True,
        "payloadless_useful_execution_native_stub_checked": True,
        "benchmark_is_current_wna16_fused_moe": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": (
            "promote_future_wna16_typed_slot_payloadless_useful_execution_gate"
        ),
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    rows_consumed = _int_metric(evidence, "payloadless_useful_execution_rows_consumed")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    if row_count is not None and rows_consumed != row_count:
        failures.append("payloadless_useful_execution_rows_consumed_mismatch")
    if evidence.get("field_names") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("field_names_mismatch")
    if evidence.get("useful_consumer_fields_consumed") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("useful_consumer_fields_consumed_mismatch")
    row_ok_counts = evidence.get("field_read_row_ok_counts")
    field_hashes = evidence.get("field_read_hashes")
    useful_hashes = evidence.get("useful_consumer_field_read_hashes")
    if not isinstance(row_ok_counts, dict):
        failures.append("field_read_row_ok_counts_missing")
        row_ok_counts = {}
    if not isinstance(field_hashes, dict):
        failures.append("field_read_hashes_missing")
        field_hashes = {}
    if not isinstance(useful_hashes, dict):
        failures.append("useful_consumer_field_read_hashes_missing")
        useful_hashes = {}
    for field in ARG_SLOT_MIRROR_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"{field}_read_row_ok_count_mismatch")
        if _hex64_metric(field_hashes, field) is None:
            failures.append(f"{field}_read_hash_invalid")
        if _hex64_metric(useful_hashes, field) is None:
            failures.append(f"useful_{field}_read_hash_invalid")
    for key in (
        "useful_consumer_sha256",
        "execution_sha256",
        "native_timing_sha256",
        "native_stub_sha256",
        "useful_consumer_hash",
        "payloadless_useful_execution_chain_hash",
    ):
        if _sha256_hex_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    for key in (
        "useful_consumer_json",
        "execution_json",
        "native_timing_json",
        "native_stub_json",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
    for key in (
        "wna16_side_consumer_variant_execution_hash_accumulator",
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator",
    ):
        if _hex64_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    return failures


def _validate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_repeat_benchmark",
        "benchmark_name": (
            "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1"
        ),
        "benchmark_mode": "payloadless_useful_native_stub_repeat_benchmark",
        "benchmark_source": (
            "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1"
        ),
        "benchmark_scope": "payloadless_useful_independent_native_stub_host_wall",
        "passed": True,
        "failures": [],
        "payloadless_useful_repeat_benchmark_ready": True,
        "measurement_source": "repeated_independent_native_typed_slot_timing_stub",
        "seed_only": False,
        "benchmark_is_current_wna16_fused_moe": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
        ),
    }
    for key, expected in expected_values.items():
        failures.extend(_check_metric_equals(evidence, key, expected))

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_source_count"
        ]
    )
    min_repeat_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_repeat_count"
        ]
    )
    source_count = _int_metric(evidence, "source_count")
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    rows_consumed = _int_metric(evidence, "rows_consumed")
    repeat_count_requested = _int_metric(evidence, "repeat_count_requested")
    repeat_count_measured = _int_metric(evidence, "repeat_count_measured")
    if source_count is None or source_count < min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("row_count_invalid")
    elif row_ok_count != row_count or rows_consumed != row_count:
        failures.append("row_coverage_mismatch")
    if (
        repeat_count_requested is None
        or repeat_count_requested < min_repeat_count
        or repeat_count_measured != repeat_count_requested
    ):
        failures.append("repeat_count_invalid")
    if evidence.get("field_names") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append("field_names_mismatch")
    field_hashes = evidence.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("field_read_hashes_missing")
        field_hashes = {}
    for field in ARG_SLOT_MIRROR_FIELDS:
        if _hex64_metric(field_hashes, field) is None:
            failures.append(f"{field}_read_hash_invalid")
    stats = evidence.get("native_stub_host_wall_ms_stats")
    values = evidence.get("native_stub_host_wall_ms_values")
    if not isinstance(stats, dict):
        failures.append("native_stub_host_wall_ms_stats_missing")
        stats = {}
    if not isinstance(values, list):
        failures.append("native_stub_host_wall_ms_values_missing")
        values = []
    if repeat_count_measured is not None:
        if _int_metric(stats, "count") != repeat_count_measured:
            failures.append("native_stub_host_wall_ms_stats_count_mismatch")
        if len(values) != repeat_count_measured:
            failures.append("native_stub_host_wall_ms_values_count_mismatch")
    for key in ("min_ms", "median_ms", "mean_ms", "max_ms"):
        value = stats.get(key)
        if not isinstance(value, (int, float)) or value <= 0:
            failures.append(f"native_stub_host_wall_ms_stats_{key}_invalid")
    if any(not isinstance(value, (int, float)) or value <= 0 for value in values):
        failures.append("native_stub_host_wall_ms_values_invalid")
    for key in (
        "harness_sha256",
        "native_timing_seed_sha256",
    ):
        if _sha256_hex_metric(evidence, key) is None:
            failures.append(f"{key}_invalid")
    repeat_sha256s = evidence.get("repeat_output_sha256s")
    if not isinstance(repeat_sha256s, list):
        failures.append("repeat_output_sha256s_missing")
        repeat_sha256s = []
    if repeat_count_measured is not None and len(repeat_sha256s) != repeat_count_measured:
        failures.append("repeat_output_sha256s_count_mismatch")
    for idx, value in enumerate(repeat_sha256s):
        if not isinstance(value, str) or _sha256_hex_metric({"v": value}, "v") is None:
            failures.append(f"repeat_output_sha256_{idx}_invalid")
    for key in (
        "harness_json",
        "native_timing_seed_json",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
    repeat_jsons = evidence.get("repeat_output_jsons")
    if not isinstance(repeat_jsons, list):
        failures.append("repeat_output_jsons_missing")
        repeat_jsons = []
    if repeat_count_measured is not None and len(repeat_jsons) != repeat_count_measured:
        failures.append("repeat_output_jsons_count_mismatch")
    if any(not isinstance(value, str) or not value for value in repeat_jsons):
        failures.append("repeat_output_jsons_invalid")
    return failures


def _validate_future_native_arg_slot_all_field_entry_args_ptr_sweep(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
        "passed": True,
        "failures": [],
        "dry_run": False,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "window_size": 512,
        "block_threads": 256,
        "require_program_view_ptr_abi": True,
        "require_kernel_arg_packet_abi": True,
        "require_kernel_entry_args_abi": True,
        "require_kernel_entry_args_ptr_abi": True,
        "mirror_fields": list(_FUTURE_KERNEL_TYPED_SLOT_MIRROR_FIELDS),
    }
    for key, expected in expected_values.items():
        if evidence.get(key) != expected:
            failures.append(f"{key}_mismatch")
    if not _targets_default_lab_gpu1(evidence):
        failures.append("device_not_gpu1")

    row_counts = evidence.get("row_counts")
    if not isinstance(row_counts, dict):
        failures.append("row_counts_missing")
        row_counts = {}
    values: list[int] = []
    for field in _FUTURE_KERNEL_TYPED_SLOT_MIRROR_FIELDS:
        value = row_counts.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            failures.append(f"{field}_row_count_invalid")
            continue
        values.append(value)
    if values:
        row_count = values[0]
        if any(value != row_count for value in values):
            failures.append("field_row_counts_not_equal")
        if row_count <= 512:
            failures.append("row_count_not_larger_than_window_size")
    else:
        row_count = None

    reports = evidence.get("field_reports")
    if not isinstance(reports, dict):
        failures.append("field_reports_missing")
        reports = {}
    for field in _FUTURE_KERNEL_TYPED_SLOT_MIRROR_FIELDS:
        report = reports.get(field)
        if not isinstance(report, dict):
            failures.append(f"{field}_field_report_missing")
            continue
        expected_report_values = {
            "passed": True,
            "sweep_failures": [],
            "check_failures": [],
            "window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        }
        for key, expected in expected_report_values.items():
            if report.get(key) != expected:
                failures.append(f"{field}_{key}_mismatch")
        if row_count is not None and report.get("row_count") != row_count:
            failures.append(f"{field}_report_row_count_mismatch")
        if not isinstance(report.get("sweep_json"), str) or not report.get(
            "sweep_json"
        ):
            failures.append(f"{field}_sweep_json_missing")
        if not isinstance(report.get("check_json"), str) or not report.get(
            "check_json"
        ):
            failures.append(f"{field}_check_json_missing")
    return failures


def _validate_future_native_arg_slot_all_field_entry_args_ptr_sweep_check(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_values: dict[str, Any] = {
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
        "passed": True,
        "failures": [],
        "expected_window_size": 512,
        "expected_block_threads": 256,
        "min_row_count": 257,
        "require_child_checks": True,
        "require_child_field_masks": True,
        "require_child_consumer_view": True,
        "require_child_consumer_view_layout": True,
        "require_child_consumer_view_row_layout": True,
        "require_child_consumer_view_handle_projection": True,
        "require_child_program_view_ptr_abi": True,
        "require_child_kernel_arg_packet_abi": True,
        "require_child_kernel_entry_args_abi": True,
        "require_child_kernel_entry_args_ptr_abi": True,
        "require_child_kernel_entry_row_metadata": True,
        "mirror_fields_checked": list(_FUTURE_KERNEL_TYPED_SLOT_MIRROR_FIELDS),
    }
    for key, expected in expected_values.items():
        if evidence.get(key) != expected:
            failures.append(f"{key}_mismatch")
    row_count = evidence.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool):
        failures.append("row_count_invalid")
    elif row_count <= 512:
        failures.append("row_count_not_larger_than_window_size")
    if not isinstance(evidence.get("all_field_window_sweep_json"), str) or not evidence.get(
        "all_field_window_sweep_json"
    ):
        failures.append("all_field_window_sweep_json_missing")
    return failures


def _validate_wna16_side_consumer_variant_execution_runner(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if evidence.get("passed") is not True:
        failures.append("runner_not_passed")
    if evidence.get("failures") != []:
        failures.append("runner_failures_not_empty")
    if not _targets_default_lab_gpu1(evidence):
        failures.append("device_not_gpu1")
    if evidence.get("require_wna16_side_consumer_variant_execution") is not True:
        failures.append("require_wna16_side_consumer_variant_execution_missing")
    if evidence.get("require_wna16_adjacent_typed_slot") is not True:
        failures.append("require_wna16_adjacent_typed_slot_missing")
    if evidence.get("not_a_single_vllm_launch_table") is not True:
        failures.append("single_launch_flag_mismatch")
    if evidence.get("no_payload") is not True:
        failures.append("no_payload_flag_mismatch")
    for key, expected in {
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
    }.items():
        if evidence.get(key) != expected:
            failures.append(f"{key}_mismatch")

    min_source_count = int(
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "wna16_side_consumer_variant_execution_min_source_count"
        ]
    )
    source_count = _int_metric(evidence, "selected_source_count")
    merged_row_count = _int_metric(evidence, "merged_row_count")
    dispatch_active_rows = _int_metric(evidence, "dispatch_active_rows")
    dispatch_row_offset = _int_metric(evidence, "dispatch_row_offset")
    dispatch_row_limit = _int_metric(evidence, "dispatch_row_limit")
    block_threads = _int_metric(evidence, "block_threads")
    dispatch_program_count = _int_metric(evidence, "dispatch_expected_program_count")
    if source_count is None or source_count < min_source_count:
        failures.append("selected_source_count_invalid")
    if merged_row_count is None or merged_row_count <= 0:
        failures.append("merged_row_count_invalid")
    if dispatch_row_offset != 0:
        failures.append("dispatch_row_offset_mismatch")
    if merged_row_count is not None and dispatch_row_limit != merged_row_count:
        failures.append("dispatch_row_limit_mismatch")
    if merged_row_count is not None and dispatch_active_rows != merged_row_count:
        failures.append("dispatch_active_rows_mismatch")
    if block_threads is None or block_threads <= 0:
        failures.append("block_threads_invalid")
    if (
        dispatch_active_rows is not None
        and block_threads is not None
        and dispatch_program_count is not None
        and (dispatch_active_rows + block_threads - 1) // block_threads
        != dispatch_program_count
    ):
        failures.append("dispatch_program_count_mismatch")

    prefix = "wna16_side_consumer_variant_execution"
    expected_top = {
        f"{prefix}_checked": True,
        f"{prefix}_name": "premap_wna16_side_consumer_variant_execution_v1",
        f"{prefix}_mode": "readonly_wna16_side_consumer_variant_execution",
        f"{prefix}_source": "premap_future_wna16_typed_slot_kernel_variant_v1",
        f"{prefix}_all_handle_fields_read": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_reuses_current_wna16_arg_slot": False,
    }
    for key, expected in expected_top.items():
        if evidence.get(key) != expected:
            failures.append(f"{key}_mismatch")
    row_count = _int_metric(evidence, f"{prefix}_row_count")
    row_ok_count = _int_metric(evidence, f"{prefix}_row_ok_count")
    error_count = _int_metric(evidence, f"{prefix}_error_count")
    if dispatch_active_rows is not None and row_count != dispatch_active_rows:
        failures.append(f"{prefix}_row_count_mismatch")
    if dispatch_active_rows is not None and row_ok_count != dispatch_active_rows:
        failures.append(f"{prefix}_row_ok_count_mismatch")
    if error_count != 0:
        failures.append(f"{prefix}_error_count_mismatch")
    packet_chain_depth = _int_metric(evidence, f"{prefix}_packet_chain_depth")
    typed_slot_depth = _int_metric(
        evidence,
        "future_wna16_typed_slot_kernel_variant_packet_chain_depth",
    )
    if typed_slot_depth is not None and packet_chain_depth != typed_slot_depth + 1:
        failures.append(f"{prefix}_packet_chain_depth_mismatch")
    if _hex64_metric(evidence, f"{prefix}_handle_projection_hash_accumulator") is None:
        failures.append(f"{prefix}_handle_projection_hash_invalid")

    stub_summary = evidence.get("stub_summary")
    if not isinstance(stub_summary, dict):
        failures.append("stub_summary_missing")
        return failures
    for key, expected in {
        "passed": True,
        "ok": True,
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": "premap_wna16_side_consumer_variant_execution_v1",
        f"{prefix}_mode": "readonly_wna16_side_consumer_variant_execution",
        f"{prefix}_source": "premap_future_wna16_typed_slot_kernel_variant_v1",
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_reuses_current_wna16_arg_slot": False,
        f"{prefix}_explicit_typed_abi_slot": True,
    }.items():
        if stub_summary.get(key) != expected:
            failures.append(f"stub_summary_{key}_mismatch")
    if dispatch_active_rows is not None:
        for key in (
            f"{prefix}_row_count",
            f"{prefix}_row_ok_count",
            f"{prefix}_descriptor_ptr_read_row_ok_count",
            f"{prefix}_packed_weight_descriptor_read_row_ok_count",
            f"{prefix}_scale_metadata_handle_read_row_ok_count",
            f"{prefix}_aux_metadata_handle_read_row_ok_count",
        ):
            if _int_metric(stub_summary, key) != dispatch_active_rows:
                failures.append(f"stub_summary_{key}_mismatch")
    if _int_metric(stub_summary, f"{prefix}_error_count") != 0:
        failures.append(f"stub_summary_{prefix}_error_count_mismatch")
    for key in (
        f"{prefix}_hash_accumulator",
        f"{prefix}_handle_projection_hash_accumulator",
        f"{prefix}_descriptor_ptr_read_hash_accumulator",
        f"{prefix}_packed_weight_descriptor_read_hash_accumulator",
        f"{prefix}_scale_metadata_handle_read_hash_accumulator",
        f"{prefix}_aux_metadata_handle_read_hash_accumulator",
    ):
        if _hex64_metric(stub_summary, key) is None:
            failures.append(f"stub_summary_{key}_invalid")
    return failures


def _validate_required_evidence_payload(
    evidence_label: str,
    evidence: dict[str, Any],
    *,
    evidence_paths: dict[str, Any] | None = None,
    root: Path | None = None,
    allow_online_runner_self_finalization: bool = False,
) -> list[str]:
    metrics = evidence.get("metrics")
    known_stub_labels = {
        "native_typed_consumer_stub_gpu1_canary_json",
        "native_typed_consumer_stub_endpoint_ptr_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
    }
    expected_online_input_count = ONLINE_PRELAUNCH_MIN_INPUTS_BY_LABEL.get(
        evidence_label,
        16,
    )
    if evidence_label not in {
        "strict_native_typed_consumer_bridge_128_gate_json",
        "strict_single_field_handle_handoff_canary_128_gate_json",
        "strict_native_stub_online_invocation_canary_128_gate_json",
        "strict_kernel_side_typed_row_consumer_path_128_gate_json",
        "aux_metadata_single_field_handle_handoff_canary_smoke_json",
        "descriptor_ptr_single_field_handle_handoff_canary_smoke_json",
        "packed_weight_single_field_handle_handoff_canary_smoke_json",
        "native_typed_consumer_online_prelaunch_canary_runner_json",
        "future_kernel_native_dispatch_ptr_standalone_canary_json",
        "future_kernel_native_arg_slot_standalone_canary_json",
        "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
        "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
        "future_kernel_native_arg_slot_multiprogram_canary_json",
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json",
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json",
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json",
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json",
        "future_kernel_wna16_adjacent_typed_slot_canary_json",
        "future_kernel_wna16_adjacent_typed_slot_stub_json",
        "future_kernel_wna16_adjacent_typed_slot_standalone_canary_json",
        "future_wna16_single_field_handoff_all_fields_128strict_summary_json",
        "future_wna16_typed_slot_fourth_field_handoff_canary_json",
        "future_wna16_typed_slot_all_four_field_consumer_json",
        "future_wna16_kernel_side_typed_consumer_path_json",
        "future_wna16_typed_slot_payloadless_execution_json",
        "future_wna16_typed_slot_kernel_variant_execution_json",
        "future_wna16_typed_slot_kernel_variant_useful_consumer_json",
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json",
        "wna16_side_consumer_variant_execution_128strict_runner_json",
        "payload_cache_producer_state_native_canary_json",
        "payload_cache_shifted_issue_runtime_shadow_gate_json",
        "payload_cache_packet_export_manifest_json",
        "payload_cache_producer_state_nonempty_issue_stub_json",
        "payload_cache_producer_state_online_nonempty_issue_canary_json",
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
        *ARG_SLOT_ONLINE_MERGED_MIRROR_RUNNER_LABEL_BY_FIELD.values(),
        *ARG_SLOT_ONLINE_MERGED_MIRROR_STUB_LABEL_BY_FIELD.values(),
        *known_stub_labels,
    } and evidence_label not in DISPATCH_WINDOW_RUNNER_EVIDENCE_LABELS and (
        evidence_label not in ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS
    ):
        return []
    if evidence_label == "future_kernel_native_dispatch_ptr_standalone_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_dispatch_ptr_standalone_evidence(
                evidence
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_standalone_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_dispatch_ptr_standalone_evidence(
                evidence,
                require_arg_slot=True,
                arg_slot_mirror_field="scale_metadata_handle",
                failure_prefix="standalone_arg_slot",
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_packed_weight_mirror_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_dispatch_ptr_standalone_evidence(
                evidence,
                require_arg_slot=True,
                arg_slot_mirror_field="packed_weight_descriptor",
                failure_prefix="standalone_arg_slot_packed_weight",
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_dispatch_ptr_standalone_evidence(
                evidence,
                require_arg_slot=True,
                arg_slot_mirror_field="aux_metadata_handle",
                failure_prefix="standalone_arg_slot_aux_metadata",
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_dispatch_ptr_standalone_evidence(
                evidence,
                require_arg_slot=True,
                arg_slot_mirror_field="descriptor_ptr",
                failure_prefix="standalone_arg_slot_descriptor_ptr",
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_multiprogram_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_multiprogram_evidence(
                evidence
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_online_merged_multiprogram_evidence(
                evidence,
                root=root,
            )
        ]
    if evidence_label == "future_kernel_wna16_adjacent_typed_slot_stub_json":
        row_count = _int_metric(evidence, "row_count")
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_online_merged_multiprogram_evidence(
                evidence,
                root=root,
            )
        ]
        failures.extend(
            f"{evidence_label}:{failure}"
            for failure in _validate_wna16_adjacent_typed_slot_stub_metrics(
                evidence,
                failure_prefix="wna16_adjacent_typed_slot",
                expected_rows=row_count,
            )
        )
        return failures
    for (
        field,
        label,
    ) in ARG_SLOT_ONLINE_MERGED_MIRROR_STUB_LABEL_BY_FIELD.items():
        if evidence_label == label:
            return [
                f"{evidence_label}:{failure}"
                for failure in _validate_future_native_arg_slot_online_merged_multiprogram_evidence(
                    evidence,
                    root=root,
                    arg_slot_mirror_field=field,
                )
            ]
    if evidence_label == "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
                evidence,
                root=root,
                evidence_paths=evidence_paths,
            )
        ]
    if evidence_label == "future_kernel_wna16_adjacent_typed_slot_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
                evidence,
                root=root,
                evidence_paths=evidence_paths,
                require_wna16_adjacent_typed_slot=True,
                expected_stub_output_label=(
                    "future_kernel_wna16_adjacent_typed_slot_stub_json"
                ),
                validate_stub_output=True,
            )
        ]
    if evidence_label == "future_kernel_wna16_adjacent_typed_slot_standalone_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_wna16_adjacent_typed_slot_standalone_evidence(
                evidence
            )
        ]
    if evidence_label == "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json":
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_all_field_entry_args_ptr_sweep(
                evidence
            )
        ]
        if evidence_paths is not None and root is not None:
            check_path = evidence_paths.get(
                "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json"
            )
            if isinstance(check_path, str):
                try:
                    check_payload = _load_json_object_path(check_path, root=root)
                except (FileNotFoundError, ValueError, json.JSONDecodeError, OSError):
                    failures.append(f"{evidence_label}:sweep_check_json_read_failed")
                else:
                    observed_sweep = check_payload.get("all_field_window_sweep_json")
                    raw_sweep = evidence_paths.get(evidence_label)
                    if isinstance(observed_sweep, str) and isinstance(raw_sweep, str):
                        if not _path_labels_match(
                            observed_sweep,
                            raw_sweep,
                            root=root,
                        ):
                            failures.append(
                                f"{evidence_label}:sweep_check_path_mismatch"
                            )
                    else:
                        failures.append(
                            f"{evidence_label}:sweep_check_path_invalid"
                        )
                    row_counts = evidence.get("row_counts")
                    if isinstance(row_counts, dict):
                        field_row_counts = [
                            row_counts.get(field)
                            for field in _FUTURE_KERNEL_TYPED_SLOT_MIRROR_FIELDS
                        ]
                        if all(
                            isinstance(value, int) and not isinstance(value, bool)
                            for value in field_row_counts
                        ):
                            check_row_count = check_payload.get("row_count")
                            if check_row_count != field_row_counts[0]:
                                failures.append(
                                    f"{evidence_label}:sweep_check_row_count_mismatch"
                                )
                    observed_check_path = evidence.get("check_json")
                    if isinstance(observed_check_path, str) and observed_check_path:
                        if not _path_labels_match(
                            observed_check_path,
                            check_path,
                            root=root,
                        ):
                            failures.append(
                                f"{evidence_label}:check_json_path_mismatch"
                            )
            else:
                failures.append(f"{evidence_label}:sweep_check_path_missing")
        return failures
    if (
        evidence_label
        == "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json"
    ):
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_all_field_entry_args_ptr_sweep_check(
                evidence
            )
        ]
    if (
        evidence_label
        == "future_wna16_single_field_handoff_all_fields_128strict_summary_json"
    ):
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_single_field_handoff_all_fields_summary(
                evidence
            )
        ]
    if evidence_label == "future_wna16_typed_slot_fourth_field_handoff_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_fourth_field_handoff_canary(
                evidence
            )
        ]
    if evidence_label == "future_wna16_typed_slot_all_four_field_consumer_json":
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_all_four_field_consumer(
                evidence
            )
        ]
        if evidence_paths is not None and root is not None:
            expected_fourth_path = evidence_paths.get(
                "future_wna16_typed_slot_fourth_field_handoff_canary_json"
            )
            observed_fourth_path = evidence.get("fourth_field_json")
            if isinstance(expected_fourth_path, str) and isinstance(
                observed_fourth_path,
                str,
            ):
                expected_label = _path_label(
                    _path_for_label(expected_fourth_path, root),
                    root=root,
                )
                observed_label = _path_label(
                    _path_for_label(observed_fourth_path, root),
                    root=root,
                )
                if observed_label != expected_label:
                    failures.append(
                        f"{evidence_label}:fourth_field_json_path_mismatch"
                    )
                observed_sha = _path_label_sha256(observed_fourth_path, root=root)
                if observed_sha != evidence.get("fourth_field_sha256"):
                    failures.append(
                        f"{evidence_label}:fourth_field_json_sha256_mismatch"
                    )
            elif expected_fourth_path is not None or observed_fourth_path is not None:
                failures.append(f"{evidence_label}:fourth_field_json_path_invalid")
        return failures
    if evidence_label == "future_wna16_kernel_side_typed_consumer_path_json":
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_kernel_side_typed_consumer_path(
                evidence
            )
        ]
        if evidence_paths is not None and root is not None:
            expected_all_four_path = evidence_paths.get(
                "future_wna16_typed_slot_all_four_field_consumer_json"
            )
            observed_all_four_path = evidence.get("all_four_json")
            if isinstance(expected_all_four_path, str) and isinstance(
                observed_all_four_path,
                str,
            ):
                expected_label = _path_label(
                    _path_for_label(expected_all_four_path, root),
                    root=root,
                )
                observed_label = _path_label(
                    _path_for_label(observed_all_four_path, root),
                    root=root,
                )
                if observed_label != expected_label:
                    failures.append(
                        f"{evidence_label}:all_four_json_path_mismatch"
                    )
                observed_sha = _path_label_sha256(observed_all_four_path, root=root)
                if observed_sha != evidence.get("all_four_sha256"):
                    failures.append(
                        f"{evidence_label}:all_four_json_sha256_mismatch"
                    )
                all_four_payload = _load_json_object_path(
                    observed_all_four_path,
                    root=root,
                )
                expected_manifest = all_four_payload.get(
                    "selected_input_manifest_sha256"
                )
                observed_manifest = evidence.get("selected_input_manifest_sha256")
                if (
                    _is_sha256_hex(expected_manifest)
                    and observed_manifest != expected_manifest
                ):
                    failures.append(
                        f"{evidence_label}:selected_input_manifest_sha256_mismatch"
                    )
                elif not _is_sha256_hex(expected_manifest):
                    failures.append(
                        f"{evidence_label}:all_four_selected_input_manifest_sha256_invalid"
                    )
            elif expected_all_four_path is not None or observed_all_four_path is not None:
                failures.append(f"{evidence_label}:all_four_json_path_invalid")
        return failures
    if evidence_label == "future_wna16_typed_slot_payloadless_execution_json":
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_payloadless_execution(
                evidence
            )
        ]
        if evidence_paths is not None and root is not None:
            def _check_payloadless_path_sha(
                *,
                path_key: str,
                sha_key: str,
                expected_evidence_label: str | None = None,
            ) -> None:
                observed_path = evidence.get(path_key)
                if not isinstance(observed_path, str) or not observed_path:
                    failures.append(f"{evidence_label}:{path_key}_missing")
                    return
                sha_source_path = observed_path
                if expected_evidence_label is not None:
                    expected_path = evidence_paths.get(expected_evidence_label)
                    if isinstance(expected_path, str):
                        observed_label = _path_label(
                            _path_for_label(observed_path, root),
                            root=root,
                        )
                        expected_label = _path_label(
                            _path_for_label(expected_path, root),
                            root=root,
                        )
                        if observed_label != expected_label:
                            failures.append(
                                f"{evidence_label}:{path_key}_required_evidence_path_mismatch"
                            )
                        sha_source_path = expected_path
                    else:
                        failures.append(
                            f"{evidence_label}:{expected_evidence_label}_required_path_missing"
                        )
                actual_sha = _path_label_sha256(sha_source_path, root=root)
                if actual_sha is None:
                    failures.append(f"{evidence_label}:{path_key}_sha256_unreadable")
                elif actual_sha != evidence.get(sha_key):
                    failures.append(f"{evidence_label}:{sha_key}_mismatch")

            expected_kernel_side_path = evidence_paths.get(
                "future_wna16_kernel_side_typed_consumer_path_json"
            )
            observed_kernel_side_path = evidence.get(
                "future_wna16_kernel_side_typed_consumer_path_evidence_path"
            )
            if isinstance(expected_kernel_side_path, str) and isinstance(
                observed_kernel_side_path,
                str,
            ):
                expected_label = _path_label(
                    _path_for_label(expected_kernel_side_path, root),
                    root=root,
                )
                observed_label = _path_label(
                    _path_for_label(observed_kernel_side_path, root),
                    root=root,
                )
                if observed_label != expected_label:
                    failures.append(
                        f"{evidence_label}:kernel_side_typed_consumer_path_mismatch"
                    )
                observed_sha = _path_label_sha256(
                    observed_kernel_side_path,
                    root=root,
                )
                if observed_sha != evidence.get(
                    "future_wna16_kernel_side_typed_consumer_path_evidence_sha256"
                ):
                    failures.append(
                        f"{evidence_label}:kernel_side_typed_consumer_path_sha256_mismatch"
                    )
            elif (
                expected_kernel_side_path is not None
                or observed_kernel_side_path is not None
            ):
                failures.append(
                    f"{evidence_label}:kernel_side_typed_consumer_path_invalid"
                )
            _check_payloadless_path_sha(
                path_key="payloadless_execution_runner_json",
                sha_key="payloadless_execution_runner_sha256",
                expected_evidence_label=(
                    "wna16_side_consumer_variant_execution_128strict_runner_json"
                ),
            )
            _check_payloadless_path_sha(
                path_key="payloadless_execution_timing_stub_json",
                sha_key="payloadless_execution_timing_stub_sha256",
            )
            _check_payloadless_path_sha(
                path_key="benchmark_json",
                sha_key="benchmark_sha256",
            )
            _check_payloadless_path_sha(
                path_key="entry_args_ptr_sweep_json",
                sha_key="entry_args_ptr_sweep_sha256",
                expected_evidence_label=(
                    "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json"
                ),
            )
            _check_payloadless_path_sha(
                path_key="entry_args_ptr_sweep_check_json",
                sha_key="entry_args_ptr_sweep_check_sha256",
                expected_evidence_label=(
                    "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json"
                ),
            )
            expected_fourth_path = evidence_paths.get(
                "future_wna16_typed_slot_fourth_field_handoff_canary_json"
            )
            observed_fourth_path = evidence.get("fourth_field_handoff_evidence_path")
            if isinstance(expected_fourth_path, str) and isinstance(
                observed_fourth_path,
                str,
            ):
                expected_fourth_label = _path_label(
                    _path_for_label(expected_fourth_path, root),
                    root=root,
                )
                observed_fourth_label = _path_label(
                    _path_for_label(observed_fourth_path, root),
                    root=root,
                )
                if observed_fourth_label != expected_fourth_label:
                    failures.append(
                        f"{evidence_label}:fourth_field_handoff_path_mismatch"
                    )
                observed_fourth_sha = _path_label_sha256(
                    expected_fourth_path,
                    root=root,
                )
                if observed_fourth_sha != evidence.get(
                    "fourth_field_handoff_evidence_sha256"
                ):
                    failures.append(
                        f"{evidence_label}:fourth_field_handoff_sha256_mismatch"
                    )
            else:
                failures.append(f"{evidence_label}:fourth_field_handoff_path_invalid")
            expected_all_four_path = evidence_paths.get(
                "future_wna16_typed_slot_all_four_field_consumer_json"
            )
            if isinstance(expected_all_four_path, str):
                all_four_payload = _load_json_object_path(
                    expected_all_four_path,
                    root=root,
                )
                field_hashes = evidence.get("field_read_hashes")
                if not isinstance(field_hashes, dict):
                    failures.append(f"{evidence_label}:field_read_hashes_missing")
                else:
                    for field in ARG_SLOT_MIRROR_FIELDS:
                        expected_hash = all_four_payload.get(
                            f"future_wna16_kernel_side_consumer_execution_{field}_read_hash_accumulator"
                        )
                        if field_hashes.get(field) != expected_hash:
                            failures.append(
                                f"{evidence_label}:{field}_field_hash_mismatch"
                            )
                all_four_source = _int_metric(all_four_payload, "source_count")
                all_four_rows = _int_metric(all_four_payload, "row_count")
                if all_four_source != _int_metric(evidence, "source_count"):
                    failures.append(f"{evidence_label}:all_four_source_count_mismatch")
                if all_four_rows != _int_metric(evidence, "row_count"):
                    failures.append(f"{evidence_label}:all_four_row_count_mismatch")
                expected_fourth_sha = all_four_payload.get("fourth_field_sha256")
                if (
                    _is_sha256_hex(expected_fourth_sha)
                    and evidence.get("all_four_field_consumer_fourth_field_sha256")
                    != expected_fourth_sha
                ):
                    failures.append(
                        f"{evidence_label}:all_four_fourth_field_sha256_mismatch"
                    )
                elif not _is_sha256_hex(expected_fourth_sha):
                    failures.append(
                        f"{evidence_label}:all_four_fourth_field_sha256_invalid"
                    )
            else:
                failures.append(f"{evidence_label}:all_four_required_path_missing")
            if isinstance(expected_kernel_side_path, str):
                kernel_side_payload = _load_json_object_path(
                    expected_kernel_side_path,
                    root=root,
                )
                expected_all_four_sha = kernel_side_payload.get("all_four_sha256")
                if (
                    _is_sha256_hex(expected_all_four_sha)
                    and evidence.get(
                        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256"
                    )
                    != expected_all_four_sha
                ):
                    failures.append(
                        f"{evidence_label}:kernel_side_all_four_sha256_mismatch"
                    )
                elif not _is_sha256_hex(expected_all_four_sha):
                    failures.append(
                        f"{evidence_label}:kernel_side_all_four_sha256_invalid"
                    )
                expected_manifest_sha = kernel_side_payload.get(
                    "selected_input_manifest_sha256"
                )
                if (
                    _is_sha256_hex(expected_manifest_sha)
                    and evidence.get(
                        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"
                    )
                    != expected_manifest_sha
                ):
                    failures.append(
                        f"{evidence_label}:kernel_side_selected_input_manifest_sha256_mismatch"
                    )
                elif not _is_sha256_hex(expected_manifest_sha):
                    failures.append(
                        f"{evidence_label}:kernel_side_selected_input_manifest_sha256_invalid"
                    )
        return failures
    if evidence_label == "future_wna16_typed_slot_kernel_variant_execution_json":
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_kernel_variant_execution(
                evidence
            )
        ]
        if evidence_paths is not None and root is not None:
            expected_payloadless_path = evidence_paths.get(
                "future_wna16_typed_slot_payloadless_execution_json"
            )
            observed_payloadless_path = evidence.get("payloadless_json")
            if isinstance(expected_payloadless_path, str) and isinstance(
                observed_payloadless_path,
                str,
            ):
                expected_label = _path_label(
                    _path_for_label(expected_payloadless_path, root),
                    root=root,
                )
                observed_label = _path_label(
                    _path_for_label(observed_payloadless_path, root),
                    root=root,
                )
                if observed_label != expected_label:
                    failures.append(
                        f"{evidence_label}:payloadless_json_path_mismatch"
                    )
                expected_sha = _path_label_sha256(
                    expected_payloadless_path,
                    root=root,
                )
                if expected_sha != evidence.get("payloadless_sha256"):
                    failures.append(f"{evidence_label}:payloadless_sha256_mismatch")
            else:
                failures.append(f"{evidence_label}:payloadless_json_path_invalid")
            native_json = evidence.get("future_wna16_variant_execution_native_json")
            if isinstance(native_json, str) and native_json:
                native_sha = _path_label_sha256(native_json, root=root)
                if native_sha != evidence.get(
                    "future_wna16_variant_execution_native_sha256"
                ):
                    failures.append(
                        f"{evidence_label}:native_execution_sha256_mismatch"
                    )
            else:
                failures.append(f"{evidence_label}:native_execution_json_missing")
        return failures
    if evidence_label == "future_wna16_typed_slot_kernel_variant_useful_consumer_json":
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_kernel_variant_useful_consumer(
                evidence
            )
        ]
        row_count = _int_metric(evidence, "row_count")
        if evidence_paths is not None and root is not None:
            expected_execution_path = evidence_paths.get(
                "future_wna16_typed_slot_kernel_variant_execution_json"
            )
            observed_execution_path = evidence.get("execution_json")
            execution_payload: dict[str, Any] = {}
            if isinstance(expected_execution_path, str) and isinstance(
                observed_execution_path,
                str,
            ):
                expected_label = _path_label(
                    _path_for_label(expected_execution_path, root),
                    root=root,
                )
                observed_label = _path_label(
                    _path_for_label(observed_execution_path, root),
                    root=root,
                )
                if observed_label != expected_label:
                    failures.append(
                        f"{evidence_label}:execution_json_path_mismatch"
                    )
                expected_sha = _path_label_sha256(
                    expected_execution_path,
                    root=root,
                )
                if expected_sha != evidence.get("execution_sha256"):
                    failures.append(f"{evidence_label}:execution_sha256_mismatch")
                execution_payload = _load_json_object_path(
                    expected_execution_path,
                    root=root,
                )
            else:
                failures.append(f"{evidence_label}:execution_json_path_invalid")
            observed_timing_path = evidence.get("native_timing_json")
            timing_payload: dict[str, Any] = {}
            expected_timing_path = execution_payload.get(
                "future_wna16_variant_execution_native_json"
            )
            expected_timing_sha = execution_payload.get(
                "future_wna16_variant_execution_native_sha256"
            )
            if isinstance(observed_timing_path, str) and observed_timing_path:
                observed_timing_label = _path_label(
                    _path_for_label(observed_timing_path, root),
                    root=root,
                )
                if isinstance(expected_timing_path, str) and expected_timing_path:
                    expected_timing_label = _path_label(
                        _path_for_label(expected_timing_path, root),
                        root=root,
                    )
                    if observed_timing_label != expected_timing_label:
                        failures.append(
                            f"{evidence_label}:native_timing_json_chain_mismatch"
                        )
                    timing_sha = _path_label_sha256(expected_timing_path, root=root)
                    if timing_sha != evidence.get("native_timing_sha256"):
                        failures.append(
                            f"{evidence_label}:native_timing_sha256_mismatch"
                        )
                    if (
                        _is_sha256_hex(expected_timing_sha)
                        and evidence.get("native_timing_sha256")
                        != expected_timing_sha
                    ):
                        failures.append(
                            f"{evidence_label}:native_timing_execution_sha256_mismatch"
                        )
                    elif not _is_sha256_hex(expected_timing_sha):
                        failures.append(
                            f"{evidence_label}:execution_native_timing_sha256_invalid"
                        )
                    timing_payload = _load_json_object_path(
                        expected_timing_path,
                        root=root,
                    )
                else:
                    failures.append(
                        f"{evidence_label}:execution_native_timing_json_missing"
                    )
            else:
                failures.append(f"{evidence_label}:native_timing_json_missing")
            observed_stub_path = evidence.get("native_stub_json")
            expected_stub_path = timing_payload.get("native_stub_output_json")
            expected_stub_sha = timing_payload.get("native_stub_output_sha256")
            stub_payload: dict[str, Any] = {}
            if isinstance(observed_stub_path, str) and observed_stub_path:
                observed_stub_label = _path_label(
                    _path_for_label(observed_stub_path, root),
                    root=root,
                )
                if isinstance(expected_stub_path, str) and expected_stub_path:
                    expected_stub_label = _path_label(
                        _path_for_label(expected_stub_path, root),
                        root=root,
                    )
                    if observed_stub_label != expected_stub_label:
                        failures.append(
                            f"{evidence_label}:native_stub_json_chain_mismatch"
                        )
                    stub_sha = _path_label_sha256(expected_stub_path, root=root)
                    if stub_sha != evidence.get("native_stub_sha256"):
                        failures.append(
                            f"{evidence_label}:native_stub_sha256_mismatch"
                        )
                    if (
                        _is_sha256_hex(expected_stub_sha)
                        and evidence.get("native_stub_sha256") != expected_stub_sha
                    ):
                        failures.append(
                            f"{evidence_label}:native_stub_timing_sha256_mismatch"
                        )
                    elif not _is_sha256_hex(expected_stub_sha):
                        failures.append(
                            f"{evidence_label}:timing_native_stub_sha256_invalid"
                        )
                    stub_payload = _load_json_object_path(
                        expected_stub_path,
                        root=root,
                    )
                else:
                    failures.append(
                        f"{evidence_label}:timing_native_stub_json_missing"
                    )
            else:
                failures.append(f"{evidence_label}:native_stub_json_missing")
            for key, expected in {
                "passed": True,
                "failures": [],
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
            }.items():
                if stub_payload.get(key) != expected:
                    failures.append(f"{evidence_label}:native_stub_{key}_mismatch")
            if stub_payload.get(
                "wna16_side_consumer_variant_execution_payload_bytes"
            ) != 0:
                failures.append(
                    f"{evidence_label}:native_stub_wna16_payload_bytes_mismatch"
                )
            for key in (
                "wna16_side_consumer_variant_execution_passed_to_kernel",
                "wna16_side_consumer_variant_execution_changes_kernel_launch_args",
                "wna16_side_consumer_variant_execution_current_wna16_arg_compatible",
            ):
                if stub_payload.get(key) is not False:
                    failures.append(f"{evidence_label}:native_stub_{key}_mismatch")
            if _int_metric(
                stub_payload,
                "wna16_side_consumer_variant_execution_row_count",
            ) != row_count:
                failures.append(
                    f"{evidence_label}:native_stub_wna16_row_count_mismatch"
                )
            if _int_metric(
                stub_payload,
                "wna16_side_consumer_variant_execution_row_ok_count",
            ) != row_count:
                failures.append(
                    f"{evidence_label}:native_stub_wna16_row_ok_count_mismatch"
                )
            if _int_metric(
                stub_payload,
                "wna16_side_consumer_variant_execution_error_count",
            ) != 0:
                failures.append(
                    f"{evidence_label}:native_stub_wna16_error_count_mismatch"
                )
            if stub_payload.get(
                "wna16_side_consumer_variant_execution_hash_accumulator"
            ) != evidence.get("wna16_side_consumer_variant_execution_hash_accumulator"):
                failures.append(f"{evidence_label}:native_stub_wna16_hash_mismatch")
            if stub_payload.get(
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
            ) != evidence.get(
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
            ):
                failures.append(
                    f"{evidence_label}:native_stub_wna16_handle_projection_hash_mismatch"
                )
            useful_hashes = evidence.get("useful_consumer_field_read_hashes")
            if not isinstance(useful_hashes, dict):
                useful_hashes = {}
            for field in ARG_SLOT_MIRROR_FIELDS:
                field_prefix = f"wna16_side_consumer_variant_execution_{field}_read"
                if _int_metric(stub_payload, f"{field_prefix}_row_count") != row_count:
                    failures.append(
                        f"{evidence_label}:native_stub_{field}_row_count_mismatch"
                    )
                if _int_metric(
                    stub_payload,
                    f"{field_prefix}_row_ok_count",
                ) != row_count:
                    failures.append(
                        f"{evidence_label}:native_stub_{field}_row_ok_count_mismatch"
                    )
                if _int_metric(stub_payload, f"{field_prefix}_error_count") != 0:
                    failures.append(
                        f"{evidence_label}:native_stub_{field}_error_count_mismatch"
                    )
                if stub_payload.get(f"{field_prefix}_hash_accumulator") != useful_hashes.get(
                    field
                ):
                    failures.append(
                        f"{evidence_label}:native_stub_{field}_hash_mismatch"
                    )
        return failures
    if (
        evidence_label
        == "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json"
    ):
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution(
                evidence
            )
        ]
        if evidence_paths is not None and root is not None:
            expected_useful_path = evidence_paths.get(
                "future_wna16_typed_slot_kernel_variant_useful_consumer_json"
            )
            observed_useful_path = evidence.get("useful_consumer_json")
            useful_payload: dict[str, Any] = {}
            if isinstance(expected_useful_path, str) and isinstance(
                observed_useful_path,
                str,
            ):
                expected_label = _path_label(
                    _path_for_label(expected_useful_path, root),
                    root=root,
                )
                observed_label = _path_label(
                    _path_for_label(observed_useful_path, root),
                    root=root,
                )
                if observed_label != expected_label:
                    failures.append(
                        f"{evidence_label}:useful_consumer_json_path_mismatch"
                    )
                expected_sha = _path_label_sha256(expected_useful_path, root=root)
                if expected_sha != evidence.get("useful_consumer_sha256"):
                    failures.append(
                        f"{evidence_label}:useful_consumer_sha256_mismatch"
                    )
                useful_payload = _load_json_object_path(
                    expected_useful_path,
                    root=root,
                )
            else:
                failures.append(f"{evidence_label}:useful_consumer_json_path_invalid")
            for evidence_key, useful_key in {
                "execution_json": "execution_json",
                "native_timing_json": "native_timing_json",
                "native_stub_json": "native_stub_json",
                "execution_sha256": "execution_sha256",
                "native_timing_sha256": "native_timing_sha256",
                "native_stub_sha256": "native_stub_sha256",
                "field_read_hashes": "field_read_hashes",
                "field_read_row_ok_counts": "field_read_row_ok_counts",
                "useful_consumer_field_read_hashes": (
                    "useful_consumer_field_read_hashes"
                ),
            }.items():
                if evidence.get(evidence_key) != useful_payload.get(useful_key):
                    failures.append(
                        f"{evidence_label}:{evidence_key}_useful_mismatch"
                    )
            for key in ("source_count", "row_count", "row_ok_count"):
                if evidence.get(key) != useful_payload.get(key):
                    failures.append(f"{evidence_label}:{key}_useful_mismatch")
        return failures
    if (
        evidence_label
        == "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json"
    ):
        failures = [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark(
                evidence
            )
        ]
        if root is None:
            failures.append(f"{evidence_label}:root_missing_for_child_validation")
            return failures
        row_count = _int_metric(evidence, "row_count")
        source_count = _int_metric(evidence, "source_count")
        field_hashes = evidence.get("field_read_hashes")
        if not isinstance(field_hashes, dict):
            field_hashes = {}
        timing_seed_path = evidence.get("native_timing_seed_json")
        expected_wna16_field_hashes: dict[str, Any] = {}
        expected_wna16_hash_accumulator: Any = None
        expected_wna16_handle_projection_hash_accumulator: Any = None
        if evidence_paths is not None:
            execution_path = evidence_paths.get(
                "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json"
            )
            if isinstance(execution_path, str) and execution_path:
                execution_payload = _load_json_object_path(execution_path, root=root)
                if _int_metric(execution_payload, "source_count") != source_count:
                    failures.append(f"{evidence_label}:execution_source_count_mismatch")
                if _int_metric(execution_payload, "row_count") != row_count:
                    failures.append(f"{evidence_label}:execution_row_count_mismatch")
                if _int_metric(execution_payload, "row_ok_count") != row_count:
                    failures.append(f"{evidence_label}:execution_row_ok_count_mismatch")
                execution_hashes = execution_payload.get("field_read_hashes")
                if not isinstance(execution_hashes, dict):
                    failures.append(f"{evidence_label}:execution_field_hashes_missing")
                    execution_hashes = {}
                for field in ARG_SLOT_MIRROR_FIELDS:
                    if execution_hashes.get(field) != field_hashes.get(field):
                        failures.append(
                            f"{evidence_label}:execution_{field}_hash_mismatch"
                        )
                execution_timing_path = execution_payload.get("native_timing_json")
                execution_timing_sha = execution_payload.get("native_timing_sha256")
                if isinstance(execution_timing_path, str) and execution_timing_path:
                    if not isinstance(timing_seed_path, str) or not timing_seed_path:
                        failures.append(f"{evidence_label}:native_timing_seed_json_missing")
                    else:
                        execution_timing_label = _path_label(
                            _path_for_label(execution_timing_path, root),
                            root=root,
                        )
                        seed_timing_label = _path_label(
                            _path_for_label(timing_seed_path, root),
                            root=root,
                        )
                        if execution_timing_label != seed_timing_label:
                            failures.append(
                                f"{evidence_label}:native_timing_seed_json_execution_mismatch"
                            )
                else:
                    failures.append(f"{evidence_label}:execution_native_timing_json_missing")
                if evidence.get("native_timing_seed_sha256") != execution_timing_sha:
                    failures.append(
                        f"{evidence_label}:native_timing_seed_sha256_execution_mismatch"
                    )
                useful_hashes = execution_payload.get("useful_consumer_field_read_hashes")
                if isinstance(useful_hashes, dict):
                    expected_wna16_field_hashes = useful_hashes
                else:
                    failures.append(
                        f"{evidence_label}:execution_useful_consumer_field_hashes_missing"
                    )
                expected_wna16_hash_accumulator = execution_payload.get(
                    "wna16_side_consumer_variant_execution_hash_accumulator"
                )
                expected_wna16_handle_projection_hash_accumulator = execution_payload.get(
                    "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
                )
            else:
                failures.append(f"{evidence_label}:execution_json_path_missing")
        else:
            failures.append(f"{evidence_label}:evidence_paths_missing")

        def _check_child_payload(
            *,
            child_label: str,
            child_path: Any,
            child_sha: Any,
            payload: dict[str, Any],
            require_ready_key: str | None = None,
        ) -> None:
            if not isinstance(child_path, str) or not child_path:
                failures.append(f"{evidence_label}:{child_label}_json_missing")
                return
            if _path_label_sha256(child_path, root=root) != child_sha:
                failures.append(f"{evidence_label}:{child_label}_sha256_mismatch")
            for key, expected in {
                "passed": True,
                "failures": [],
                "payload_bytes": 0,
                "payload_deref_allowed": False,
                "kernel_arg_pass_allowed": False,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
                "uses_current_wna16_args": False,
                "passes_current_wna16_args": False,
                "current_wna16_arg_compatible": False,
                "requires_wna16_arg_reinterpretation": False,
                "measures_tpot": False,
                "measures_vllm_latency": False,
                "wna16_benchmark_ready": False,
            }.items():
                if payload.get(key) != expected:
                    failures.append(f"{evidence_label}:{child_label}_{key}_mismatch")
            if require_ready_key is not None and payload.get(require_ready_key) is not True:
                failures.append(f"{evidence_label}:{child_label}_{require_ready_key}_mismatch")
            if child_label == "harness":
                for key, expected in {
                    "artifact_kind": "future_wna16_typed_slot_payloadless_useful_benchmark_harness",
                    "harness_name": (
                        "premap_future_wna16_typed_slot_payloadless_useful_benchmark_harness_v1"
                    ),
                    "harness_mode": (
                        "independent_payloadless_useful_native_stub_benchmark_harness"
                    ),
                    "harness_source": (
                        "premap_future_wna16_typed_slot_payloadless_useful_runtime_gate_v1"
                    ),
                    "benchmark_harness_kind": (
                        "future_payloadless_useful_typed_slot_native_stub_harness"
                    ),
                    "benchmark_harness_ready": True,
                    "measures_native_stub_host_wall_time": True,
                }.items():
                    if payload.get(key) != expected:
                        failures.append(
                            f"{evidence_label}:{child_label}_{key}_mismatch"
                        )
            else:
                for key, expected in {
                    "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
                    "timing_stub_name": (
                        "premap_future_wna16_typed_slot_kernel_timing_stub_v1"
                    ),
                    "timing_stub_mode": (
                        "independent_future_wna16_typed_slot_native_stub_timing"
                    ),
                    "timing_stub_source": (
                        "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1"
                    ),
                    "native_stub_requested": True,
                    "native_stub_executed": True,
                    "native_stub_passed": True,
                    "measures_native_stub_host_wall_time": True,
                }.items():
                    if payload.get(key) != expected:
                        failures.append(
                            f"{evidence_label}:{child_label}_{key}_mismatch"
                        )
                stub_path = payload.get("native_stub_output_json")
                stub_sha = payload.get("native_stub_output_sha256")
                if not isinstance(stub_path, str) or not stub_path:
                    failures.append(f"{evidence_label}:{child_label}_native_stub_output_json_missing")
                elif _path_label_sha256(stub_path, root=root) != stub_sha:
                    failures.append(f"{evidence_label}:{child_label}_native_stub_output_sha256_mismatch")
                else:
                    stub_payload = _load_json_object_path(stub_path, root=root)
                    for key, expected in {
                        "passed": True,
                        "failures": [],
                        "payload_bytes": 0,
                        "passed_to_kernel": False,
                        "changes_kernel_launch_args": False,
                    }.items():
                        if stub_payload.get(key) != expected:
                            failures.append(
                                f"{evidence_label}:{child_label}_native_stub_{key}_mismatch"
                            )
                    for key, expected in {
                        "wna16_side_consumer_variant_execution_payload_bytes": 0,
                        "wna16_side_consumer_variant_execution_payload_deref_allowed": False,
                        "wna16_side_consumer_variant_execution_kernel_arg_pass_allowed": False,
                        "wna16_side_consumer_variant_execution_passed_to_kernel": False,
                        "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
                        "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
                        "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
                        "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
                    }.items():
                        if stub_payload.get(key) != expected:
                            failures.append(
                                f"{evidence_label}:{child_label}_native_stub_{key}_mismatch"
                            )
                    stub_row_count = _int_metric(stub_payload, "row_count")
                    if stub_row_count is None:
                        stub_row_count = _int_metric(
                            stub_payload,
                            "wna16_side_consumer_variant_execution_row_count",
                        )
                    stub_row_ok_count = _int_metric(stub_payload, "row_ok_count")
                    if stub_row_ok_count is None:
                        stub_row_ok_count = _int_metric(
                            stub_payload,
                            "wna16_side_consumer_variant_execution_row_ok_count",
                        )
                    if stub_row_count != row_count:
                        failures.append(
                            f"{evidence_label}:{child_label}_native_stub_row_count_mismatch"
                        )
                    if stub_row_ok_count != row_count:
                        failures.append(
                            f"{evidence_label}:{child_label}_native_stub_row_ok_count_mismatch"
                        )
                    if _int_metric(
                        stub_payload,
                        "wna16_side_consumer_variant_execution_error_count",
                    ) != 0:
                        failures.append(
                            f"{evidence_label}:{child_label}_native_stub_wna16_error_count_mismatch"
                        )
                    if (
                        expected_wna16_hash_accumulator is not None
                        and stub_payload.get(
                            "wna16_side_consumer_variant_execution_hash_accumulator"
                        )
                        != expected_wna16_hash_accumulator
                    ):
                        failures.append(
                            f"{evidence_label}:{child_label}_native_stub_wna16_hash_mismatch"
                        )
                    if (
                        expected_wna16_handle_projection_hash_accumulator is not None
                        and stub_payload.get(
                            "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
                        )
                        != expected_wna16_handle_projection_hash_accumulator
                    ):
                        failures.append(
                            f"{evidence_label}:{child_label}_native_stub_wna16_handle_projection_hash_mismatch"
                        )
                    for field in ARG_SLOT_MIRROR_FIELDS:
                        field_prefix = (
                            f"wna16_side_consumer_variant_execution_{field}_read"
                        )
                        if _int_metric(stub_payload, f"{field_prefix}_row_count") != row_count:
                            failures.append(
                                f"{evidence_label}:{child_label}_native_stub_{field}_row_count_mismatch"
                            )
                        if (
                            _int_metric(stub_payload, f"{field_prefix}_row_ok_count")
                            != row_count
                        ):
                            failures.append(
                                f"{evidence_label}:{child_label}_native_stub_{field}_row_ok_count_mismatch"
                            )
                        if _int_metric(stub_payload, f"{field_prefix}_error_count") != 0:
                            failures.append(
                                f"{evidence_label}:{child_label}_native_stub_{field}_error_count_mismatch"
                            )
                        observed_hash = stub_payload.get(
                            f"{field_prefix}_hash_accumulator"
                        )
                        if expected_wna16_field_hashes:
                            if observed_hash != expected_wna16_field_hashes.get(field):
                                failures.append(
                                    f"{evidence_label}:{child_label}_native_stub_{field}_hash_mismatch"
                                )
                        elif not isinstance(observed_hash, str) or _hex64_metric(
                            {"v": observed_hash},
                            "v",
                        ) is None:
                            failures.append(
                                f"{evidence_label}:{child_label}_native_stub_{field}_hash_invalid"
                            )
            if _int_metric(payload, "source_count") != source_count:
                failures.append(f"{evidence_label}:{child_label}_source_count_mismatch")
            if _int_metric(payload, "row_count") != row_count:
                failures.append(f"{evidence_label}:{child_label}_row_count_mismatch")
            if _int_metric(payload, "row_ok_count") != row_count:
                failures.append(f"{evidence_label}:{child_label}_row_ok_count_mismatch")
            payload_rows_consumed = _int_metric(payload, "rows_consumed")
            if payload_rows_consumed is not None and payload_rows_consumed != row_count:
                failures.append(f"{evidence_label}:{child_label}_rows_consumed_mismatch")
            if payload.get("field_names") != list(ARG_SLOT_MIRROR_FIELDS):
                failures.append(f"{evidence_label}:{child_label}_field_names_mismatch")
            payload_field_hashes = payload.get("field_read_hashes")
            if not isinstance(payload_field_hashes, dict):
                failures.append(f"{evidence_label}:{child_label}_field_hashes_missing")
                payload_field_hashes = {}
            for field in ARG_SLOT_MIRROR_FIELDS:
                if payload_field_hashes.get(field) != field_hashes.get(field):
                    failures.append(f"{evidence_label}:{child_label}_{field}_hash_mismatch")

        harness_path = evidence.get("harness_json")
        harness_payload = _load_json_object_path(harness_path, root=root)
        _check_child_payload(
            child_label="harness",
            child_path=harness_path,
            child_sha=evidence.get("harness_sha256"),
            payload=harness_payload,
            require_ready_key="payloadless_useful_benchmark_harness_ready",
        )
        timing_seed_payload = _load_json_object_path(timing_seed_path, root=root)
        _check_child_payload(
            child_label="native_timing_seed",
            child_path=timing_seed_path,
            child_sha=evidence.get("native_timing_seed_sha256"),
            payload=timing_seed_payload,
            require_ready_key="timing_stub_ready",
        )
        repeat_jsons = evidence.get("repeat_output_jsons")
        repeat_sha256s = evidence.get("repeat_output_sha256s")
        repeat_values = evidence.get("native_stub_host_wall_ms_values")
        if not isinstance(repeat_jsons, list):
            repeat_jsons = []
        if not isinstance(repeat_sha256s, list):
            repeat_sha256s = []
        if not isinstance(repeat_values, list):
            repeat_values = []
        for idx, child_path in enumerate(repeat_jsons):
            child_sha = repeat_sha256s[idx] if idx < len(repeat_sha256s) else None
            child_payload = _load_json_object_path(child_path, root=root)
            _check_child_payload(
                child_label=f"repeat_{idx}",
                child_path=child_path,
                child_sha=child_sha,
                payload=child_payload,
                require_ready_key="timing_stub_ready",
            )
            child_wall = child_payload.get("native_stub_host_wall_ms")
            expected_wall = repeat_values[idx] if idx < len(repeat_values) else None
            if child_wall != expected_wall:
                failures.append(f"{evidence_label}:repeat_{idx}_host_wall_mismatch")
        return failures
    if evidence_label == "wna16_side_consumer_variant_execution_128strict_runner_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_wna16_side_consumer_variant_execution_runner(
                evidence
            )
        ]
    if evidence_label == "payload_cache_producer_state_native_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_payload_cache_producer_state_native_canary_evidence(
                evidence
            )
        ]
    if evidence_label == "payload_cache_producer_state_nonempty_issue_stub_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_payload_cache_producer_state_native_canary_evidence(
                evidence,
                failure_prefix="payload_cache_producer_state_nonempty_issue_stub",
                require_online_export=False,
                require_nonempty_issue=True,
            )
        ]
    if evidence_label == "payload_cache_producer_state_online_nonempty_issue_canary_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_payload_cache_producer_state_native_canary_evidence(
                evidence,
                failure_prefix=(
                    "payload_cache_producer_state_online_nonempty_issue_canary"
                ),
                require_online_export=True,
                require_nonempty_issue=True,
                require_summary_first_nonempty_issue=True,
            )
        ]
    if evidence_label == "payload_cache_shifted_issue_runtime_shadow_gate_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence(
                evidence
            )
        ]
    if evidence_label == "payload_cache_packet_export_manifest_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_payload_cache_packet_export_manifest_evidence(
                evidence,
                root=root,
            )
        ]
    for (
        field,
        label,
    ) in ARG_SLOT_ONLINE_MERGED_MIRROR_RUNNER_LABEL_BY_FIELD.items():
        if evidence_label == label:
            return [
                f"{evidence_label}:{failure}"
                for failure in _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
                    evidence,
                    root=root,
                    evidence_paths=evidence_paths,
                    expected_stub_output_label=ARG_SLOT_ONLINE_MERGED_MIRROR_STUB_LABEL_BY_FIELD.get(
                        field
                    ),
                    arg_slot_mirror_field=field,
                    require_kernel_launch_context_abi=False,
                    require_kernel_invocation_abi=False,
                    require_kernel_invocation_entry_abi=False,
                    require_kernel_endpoint_abi=False,
                    require_kernel_endpoint_ptr_abi=False,
                )
            ]
    if evidence_label in ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS:
        failures: list[str] = []
        min_online_inputs = _int_metric(evidence, "min_online_inputs")
        if min_online_inputs is None:
            failures.append("artifact_min_online_inputs_missing")
        if (
            min_online_inputs is not None
            and min_online_inputs < expected_online_input_count
        ):
            failures.append("artifact_min_online_inputs_invalid")
        input_check_count = _int_metric(
            evidence,
            "runner_online_prelaunch_input_check_count",
        )
        if input_check_count is None:
            failures.append("artifact_online_input_check_count_missing")
        if (
            input_check_count is not None
            and input_check_count < expected_online_input_count
        ):
            failures.append("artifact_online_input_check_count_invalid")
        final_deferred_count = _int_metric(evidence, "final_deferred_count")
        if final_deferred_count is None:
            failures.append("artifact_final_deferred_count_missing")
        elif final_deferred_count != 0:
            failures.append("artifact_final_deferred_count_nonzero")
        extra_check_count = _int_metric(
            evidence,
            "runner_online_prelaunch_input_extra_check_count",
        )
        extra_passed_count = _int_metric(
            evidence,
            "runner_online_prelaunch_input_extra_check_passed_count",
        )
        if input_check_count is not None:
            expected_extra = max(input_check_count - 1, 0)
            if extra_check_count != expected_extra:
                failures.append("artifact_online_input_extra_check_count_mismatch")
            if extra_passed_count != expected_extra:
                failures.append(
                    "artifact_online_input_extra_check_passed_count_mismatch"
                )
        failures.extend(
            _validate_online_input_row_stats(
                evidence,
                expected_online_input_count=expected_online_input_count,
                failure_prefix="artifact_online_input",
            )
        )
        return [f"{evidence_label}:{failure}" for failure in failures]
    if evidence_label in ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABELS:
        failures: list[str] = []
        if evidence.get("passed") is not True:
            failures.append("runner_not_passed")
        if evidence.get("failures") != []:
            failures.append("runner_failures_not_empty")
        if evidence.get("online_prelaunch_input_json") is None:
            failures.append("runner_online_input_missing")
        if evidence.get("native_stub_output_json") is None:
            failures.append("runner_native_stub_output_missing")
        if evidence.get("preflight_output_json") is None:
            failures.append("runner_preflight_output_missing")
        stub_summary = evidence.get("stub_summary")
        if not isinstance(stub_summary, dict):
            failures.append("runner_stub_summary_missing")
        else:
            expected_stub = {
                "passed": True,
                "ok": True,
                "error_count": 0,
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
            }
            for key, expected_value in expected_stub.items():
                if stub_summary.get(key) != expected_value:
                    failures.append(f"runner_stub_summary_{key}_mismatch")
            row_count = _int_metric(stub_summary, "row_count")
            row_ok_count = _int_metric(stub_summary, "row_ok_count")
            if row_count is None or row_count <= 0:
                failures.append("runner_stub_summary_row_count_invalid")
            if row_count is not None and row_ok_count != row_count:
                failures.append("runner_stub_summary_row_ok_count_mismatch")
            for key, expected_value in {
                "kernel_side_consumer_path_checked": True,
                "kernel_side_consumer_path_error_count": 0,
                "kernel_side_consumer_path_payload_bytes": 0,
                "kernel_side_consumer_path_passed_to_kernel": False,
                "kernel_side_consumer_path_changes_kernel_launch_args": False,
                "kernel_side_consumer_path_current_wna16_arg_compatible": False,
            }.items():
                if stub_summary.get(key) != expected_value:
                    failures.append(f"runner_stub_summary_{key}_mismatch")
            if stub_summary.get("kernel_side_consumer_path_name") != (
                "premap_kernel_side_typed_consumer_path_v1"
            ):
                failures.append("runner_stub_summary_kernel_side_consumer_path_name_mismatch")
            path_row_count = _int_metric(
                stub_summary,
                "kernel_side_consumer_path_row_count",
            )
            path_row_ok_count = _int_metric(
                stub_summary,
                "kernel_side_consumer_path_row_ok_count",
            )
            if row_count is not None and path_row_count != row_count:
                failures.append(
                    "runner_stub_summary_kernel_side_consumer_path_row_count_mismatch"
                )
            if row_count is not None and path_row_ok_count != row_count:
                failures.append(
                    "runner_stub_summary_kernel_side_consumer_path_row_ok_count_mismatch"
                )
        preflight_summary = evidence.get("preflight_summary")
        if not isinstance(preflight_summary, dict):
            failures.append("runner_preflight_summary_missing")
        else:
            if preflight_summary.get("passed") is not True:
                failures.append("runner_preflight_summary_not_passed")
            if preflight_summary.get("failures") != []:
                failures.append("runner_preflight_summary_failures_not_empty")
        input_check_count = _int_metric(evidence, "online_prelaunch_input_check_count")
        extra_check_count = _int_metric(
            evidence,
            "online_prelaunch_input_extra_check_count",
        )
        extra_passed_count = _int_metric(
            evidence,
            "online_prelaunch_input_extra_check_passed_count",
        )
        if (
            input_check_count is None
            or input_check_count < expected_online_input_count
        ):
            failures.append("runner_online_input_check_count_invalid")
            input_check_count = 0
        expected_extra = max(input_check_count - 1, 0)
        if extra_check_count != expected_extra:
            failures.append("runner_online_input_extra_check_count_mismatch")
        if extra_passed_count != expected_extra:
            failures.append("runner_online_input_extra_check_passed_count_mismatch")
        dispatch_full_table_required = bool(
            REQUIRED_DEFAULT_GATE_CONTRACT.get(
                "future_kernel_native_dispatch_consumer_full_table_required",
                False,
            )
        )
        dispatch_tail_window_size = None
        if evidence_label in DISPATCH_WINDOW_RUNNER_EVIDENCE_LABELS:
            dispatch_tail_window_present = (
                "future_native_dispatch_tail_window_size" in evidence
            )
            dispatch_tail_window_size = _int_metric(
                evidence,
                "future_native_dispatch_tail_window_size",
            )
            if dispatch_full_table_required:
                if dispatch_tail_window_present:
                    failures.append(
                        "runner_future_native_dispatch_tail_window_unexpected"
                    )
                dispatch_tail_window_size = None
            elif REQUIRED_DEFAULT_GATE_CONTRACT.get(
                "future_kernel_native_dispatch_consumer_tail_window_required",
                False,
            ):
                expected_tail_window_size = int(
                    REQUIRED_DEFAULT_GATE_CONTRACT[
                        "future_kernel_native_dispatch_consumer_tail_window_size"
                    ]
                )
                if dispatch_tail_window_size != expected_tail_window_size:
                    failures.append(
                        "runner_future_native_dispatch_tail_window_size_mismatch"
                    )
            elif dispatch_tail_window_size is not None:
                failures.append(
                    "runner_future_native_dispatch_tail_window_unexpected"
                )

        def _check_runner_stub_summary(
            summary: Any,
            prefix: str,
            *,
            require_kernel_side_consumer_path: bool = False,
        ) -> None:
            if not isinstance(summary, dict):
                failures.append(f"{prefix}_missing")
                return
            for key, expected_value in {
                "passed": True,
                "ok": True,
                "error_count": 0,
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
            }.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            row_count_value = _int_metric(summary, "row_count")
            row_ok_count_value = _int_metric(summary, "row_ok_count")
            if row_count_value is None or row_count_value <= 0:
                failures.append(f"{prefix}_row_count_invalid")
            if row_count_value is not None and row_ok_count_value != row_count_value:
                failures.append(f"{prefix}_row_ok_count_mismatch")
            if require_kernel_side_consumer_path:
                for key, expected_value in {
                    "kernel_side_consumer_path_checked": True,
                    "kernel_side_consumer_path_error_count": 0,
                    "kernel_side_consumer_path_payload_bytes": 0,
                    "kernel_side_consumer_path_passed_to_kernel": False,
                    "kernel_side_consumer_path_changes_kernel_launch_args": False,
                    "kernel_side_consumer_path_current_wna16_arg_compatible": False,
                }.items():
                    if summary.get(key) != expected_value:
                        failures.append(f"{prefix}_{key}_mismatch")
                if summary.get("kernel_side_consumer_path_name") != (
                    "premap_kernel_side_typed_consumer_path_v1"
                ):
                    failures.append(f"{prefix}_kernel_side_consumer_path_name_mismatch")
                path_row_count = _int_metric(
                    summary,
                    "kernel_side_consumer_path_row_count",
                )
                path_row_ok_count = _int_metric(
                    summary,
                    "kernel_side_consumer_path_row_ok_count",
                )
                if row_count_value is not None and path_row_count != row_count_value:
                    failures.append(
                        f"{prefix}_kernel_side_consumer_path_row_count_mismatch"
                    )
                if row_count_value is not None and path_row_ok_count != row_count_value:
                    failures.append(
                        f"{prefix}_kernel_side_consumer_path_row_ok_count_mismatch"
                    )

        def _check_runner_mirror_summary(
            summary: Any,
            prefix: str,
            *,
            expected_field_name: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            if summary.get("single_field_mirror_checked") is not True:
                failures.append(f"{prefix}_single_field_mirror_checked_mismatch")
            if summary.get("single_field_mirror_field_name") != expected_field_name:
                failures.append(f"{prefix}_single_field_mirror_field_name_mismatch")
            row_count_value = _int_metric(summary, "row_count")
            mirror_row_count = _int_metric(summary, "single_field_mirror_row_count")
            mirror_row_ok_count = _int_metric(
                summary,
                "single_field_mirror_row_ok_count",
            )
            if row_count_value is not None and mirror_row_count != row_count_value:
                failures.append(f"{prefix}_single_field_mirror_row_count_mismatch")
            if row_count_value is not None and mirror_row_ok_count != row_count_value:
                failures.append(f"{prefix}_single_field_mirror_row_ok_count_mismatch")
            if summary.get("single_field_mirror_error_count") != 0:
                failures.append(f"{prefix}_single_field_mirror_error_count_mismatch")

        def _check_runner_kernel_side_compatible_summary(
            summary: Any,
            prefix: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
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
                "kernel_side_compatible_consumer_error_count": 0,
                "kernel_side_compatible_consumer_payload_bytes": 0,
                "kernel_side_compatible_consumer_passed_to_kernel": False,
                "kernel_side_compatible_consumer_changes_kernel_launch_args": False,
                "kernel_side_compatible_consumer_current_wna16_arg_compatible": False,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            row_count_value = _int_metric(summary, "row_count")
            compatible_row_count = _int_metric(
                summary,
                "kernel_side_compatible_consumer_row_count",
            )
            compatible_row_ok_count = _int_metric(
                summary,
                "kernel_side_compatible_consumer_row_ok_count",
            )
            if row_count_value is not None and compatible_row_count != row_count_value:
                failures.append(f"{prefix}_kernel_side_compatible_row_count_mismatch")
            if (
                row_count_value is not None
                and compatible_row_ok_count != row_count_value
            ):
                failures.append(f"{prefix}_kernel_side_compatible_row_ok_count_mismatch")

        def _check_runner_future_kernel_args_summary(
            summary: Any,
            prefix: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
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
                "future_kernel_consumer_args_error_count": 0,
                "future_kernel_consumer_args_payload_bytes": 0,
                "future_kernel_consumer_args_passed_to_kernel": False,
                "future_kernel_consumer_args_changes_kernel_launch_args": False,
                "future_kernel_consumer_args_current_wna16_arg_compatible": False,
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
                "future_kernel_consumer_args_single_field_mirror_checked": True,
                "future_kernel_consumer_args_single_field_mirror_field_name": (
                    "scale_metadata_handle"
                ),
                "future_kernel_consumer_args_single_field_mirror_error_count": 0,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            for key, expected_value in FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            failures.extend(
                _check_future_field_mask_summary(
                    summary,
                    prefix=prefix,
                    field_prefix="future_kernel_consumer_args",
                    expected_field_name="scale_metadata_handle",
                )
            )
            row_count_value = _int_metric(summary, "row_count")
            future_row_count = _int_metric(
                summary,
                "future_kernel_consumer_args_row_count",
            )
            future_row_ok_count = _int_metric(
                summary,
                "future_kernel_consumer_args_row_ok_count",
            )
            mirror_row_count = _int_metric(
                summary,
                "future_kernel_consumer_args_single_field_mirror_row_count",
            )
            mirror_row_ok_count = _int_metric(
                summary,
                "future_kernel_consumer_args_single_field_mirror_row_ok_count",
            )
            if row_count_value is not None and future_row_count != row_count_value:
                failures.append(f"{prefix}_future_kernel_args_row_count_mismatch")
            if row_count_value is not None and future_row_ok_count != row_count_value:
                failures.append(f"{prefix}_future_kernel_args_row_ok_count_mismatch")
            if row_count_value is not None and mirror_row_count != row_count_value:
                failures.append(f"{prefix}_future_kernel_args_mirror_row_count_mismatch")
            if row_count_value is not None and mirror_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_args_mirror_row_ok_count_mismatch"
                )

        def _check_runner_future_kernel_args_compatible_path_summary(
            summary: Any,
            prefix: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
                "future_kernel_consumer_args_checked": True,
                "future_kernel_consumer_args_error_count": 0,
                "future_kernel_consumer_args_payload_bytes": 0,
                "future_kernel_consumer_args_passed_to_kernel": False,
                "future_kernel_consumer_args_changes_kernel_launch_args": False,
                "future_kernel_consumer_args_current_wna16_arg_compatible": False,
                "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
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
                "future_kernel_args_compatible_consumer_path_error_count": 0,
                "future_kernel_args_compatible_consumer_path_payload_bytes": 0,
                "future_kernel_args_compatible_consumer_path_passed_to_kernel": False,
                "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args": False,
                "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible": False,
                "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation": False,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            for key, expected_value in FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            row_count_value = _int_metric(summary, "row_count")
            future_row_count = _int_metric(
                summary,
                "future_kernel_consumer_args_row_count",
            )
            future_row_ok_count = _int_metric(
                summary,
                "future_kernel_consumer_args_row_ok_count",
            )
            compatible_row_count = _int_metric(
                summary,
                "future_kernel_args_compatible_consumer_path_row_count",
            )
            compatible_row_ok_count = _int_metric(
                summary,
                "future_kernel_args_compatible_consumer_path_row_ok_count",
            )
            if row_count_value is not None and future_row_count != row_count_value:
                failures.append(f"{prefix}_future_kernel_args_row_count_mismatch")
            if row_count_value is not None and future_row_ok_count != row_count_value:
                failures.append(f"{prefix}_future_kernel_args_row_ok_count_mismatch")
            if row_count_value is not None and compatible_row_count != row_count_value:
                failures.append(f"{prefix}_compatible_path_row_count_mismatch")
            if (
                row_count_value is not None
                and compatible_row_ok_count != row_count_value
            ):
                failures.append(f"{prefix}_compatible_path_row_ok_count_mismatch")

        def _check_runner_future_kernel_native_consumer_summary(
            summary: Any,
            prefix: str,
            *,
            expected_field_name: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
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
                "future_kernel_native_consumer_error_count": 0,
                "future_kernel_native_consumer_payload_bytes": 0,
                "future_kernel_native_consumer_passed_to_kernel": False,
                "future_kernel_native_consumer_changes_kernel_launch_args": False,
                "future_kernel_native_consumer_current_wna16_arg_compatible": False,
                "future_kernel_native_consumer_requires_wna16_arg_reinterpretation": False,
                "future_kernel_native_consumer_single_field_mirror_checked": True,
                "future_kernel_native_consumer_single_field_mirror_field_name": (
                    expected_field_name
                ),
                "future_kernel_native_consumer_single_field_mirror_error_count": 0,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            failures.extend(
                _check_future_field_mask_summary(
                    summary,
                    prefix=prefix,
                    field_prefix="future_kernel_native_consumer",
                    expected_field_name=expected_field_name,
                )
            )
            failures.extend(
                _check_layout_summary_fields(
                    summary,
                    prefix=prefix,
                    fields=FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS,
                    expected_values=FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
                    struct_size_key="future_kernel_native_consumer_params_struct_size",
                )
            )
            row_count_value = _int_metric(summary, "row_count")
            native_row_count = _int_metric(
                summary,
                "future_kernel_native_consumer_row_count",
            )
            native_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_consumer_row_ok_count",
            )
            mirror_row_count = _int_metric(
                summary,
                "future_kernel_native_consumer_single_field_mirror_row_count",
            )
            mirror_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_consumer_single_field_mirror_row_ok_count",
            )
            if row_count_value is not None and native_row_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_row_count_mismatch"
                )
            if row_count_value is not None and native_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_row_ok_count_mismatch"
                )
            if row_count_value is not None and mirror_row_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_mirror_row_count_mismatch"
                )
            if row_count_value is not None and mirror_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_mirror_row_ok_count_mismatch"
                )

        def _check_runner_future_kernel_native_launch_consumer_summary(
            summary: Any,
            prefix: str,
            *,
            expected_field_name: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
                "future_kernel_native_consumer_checked": True,
                "future_kernel_native_consumer_error_count": 0,
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
                "future_kernel_native_launch_consumer_error_count": 0,
                "future_kernel_native_launch_consumer_payload_bytes": 0,
                "future_kernel_native_launch_consumer_passed_to_kernel": False,
                "future_kernel_native_launch_consumer_changes_kernel_launch_args": False,
                "future_kernel_native_launch_consumer_current_wna16_arg_compatible": False,
                "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation": False,
                "future_kernel_native_launch_consumer_single_field_mirror_checked": True,
                "future_kernel_native_launch_consumer_single_field_mirror_field_name": (
                    expected_field_name
                ),
                "future_kernel_native_launch_consumer_single_field_mirror_error_count": 0,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            failures.extend(
                _check_future_field_mask_summary(
                    summary,
                    prefix=prefix,
                    field_prefix="future_kernel_native_launch_consumer",
                    expected_field_name=expected_field_name,
                )
            )
            failures.extend(
                _check_layout_summary_fields(
                    summary,
                    prefix=prefix,
                    fields=FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS,
                    expected_values=(
                        FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED
                    ),
                    struct_size_key=(
                        "future_kernel_native_launch_consumer_launch_struct_size"
                    ),
                )
            )
            row_count_value = _int_metric(summary, "row_count")
            native_row_count = _int_metric(
                summary,
                "future_kernel_native_consumer_row_count",
            )
            native_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_consumer_row_ok_count",
            )
            launch_row_count = _int_metric(
                summary,
                "future_kernel_native_launch_consumer_row_count",
            )
            launch_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_launch_consumer_row_ok_count",
            )
            mirror_row_count = _int_metric(
                summary,
                "future_kernel_native_launch_consumer_single_field_mirror_row_count",
            )
            mirror_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_launch_consumer_single_field_mirror_row_ok_count",
            )
            if row_count_value is not None and native_row_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_row_count_mismatch"
                )
            if row_count_value is not None and native_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_row_ok_count_mismatch"
                )
            if row_count_value is not None and launch_row_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_launch_consumer_row_count_mismatch"
                )
            if row_count_value is not None and launch_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_launch_consumer_row_ok_count_mismatch"
                )
            if row_count_value is not None and mirror_row_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_launch_consumer_mirror_row_count_mismatch"
                )
            if row_count_value is not None and mirror_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_launch_consumer_mirror_row_ok_count_mismatch"
                )

        def _check_runner_future_kernel_native_dispatch_consumer_summary(
            summary: Any,
            prefix: str,
            *,
            expected_field_name: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
                "future_kernel_native_consumer_checked": True,
                "future_kernel_native_consumer_error_count": 0,
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
                "future_kernel_native_dispatch_consumer_error_count": 0,
                "future_kernel_native_dispatch_consumer_payload_bytes": 0,
                "future_kernel_native_dispatch_consumer_passed_to_kernel": False,
                "future_kernel_native_dispatch_consumer_changes_kernel_launch_args": False,
                "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible": False,
                "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation": False,
                "future_kernel_native_dispatch_consumer_single_field_mirror_checked": True,
                "future_kernel_native_dispatch_consumer_single_field_mirror_field_name": (
                    expected_field_name
                ),
                "future_kernel_native_dispatch_consumer_single_field_mirror_error_count": 0,
                "future_kernel_native_dispatch_consumer_launch_geometry_checked": True,
                "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
                "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            failures.extend(
                _check_future_field_mask_summary(
                    summary,
                    prefix=prefix,
                    field_prefix="future_kernel_native_dispatch_consumer",
                    expected_field_name=expected_field_name,
                )
            )
            failures.extend(
                _check_layout_summary_fields(
                    summary,
                    prefix=prefix,
                    fields=FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS,
                    expected_values=(
                        FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED
                    ),
                    struct_size_key=(
                        "future_kernel_native_dispatch_consumer_dispatch_struct_size"
                    ),
                )
            )
            row_count_value = _int_metric(summary, "row_count")
            native_row_count = _int_metric(
                summary,
                "future_kernel_native_consumer_row_count",
            )
            native_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_consumer_row_ok_count",
            )
            dispatch_row_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_row_count",
            )
            dispatch_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_row_ok_count",
            )
            dispatch_active_rows = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_active_rows",
            )
            dispatch_row_offset = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_row_offset",
            )
            dispatch_row_limit = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_row_limit",
            )
            dispatch_grid_x = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_grid_x",
            )
            dispatch_block_x = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_block_x",
            )
            dispatch_launch_threads = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_launch_threads",
            )
            dispatch_program_iteration_checked = summary.get(
                "future_kernel_native_dispatch_consumer_program_iteration_checked",
            )
            dispatch_program_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_program_count",
            )
            dispatch_full_program_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_full_program_count",
            )
            dispatch_last_program_active_rows = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_last_program_active_rows",
            )
            dispatch_inactive_lane_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_inactive_lane_count",
            )
            dispatch_first_program_row_offset = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_first_program_row_offset",
            )
            dispatch_last_program_row_offset = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_last_program_row_offset",
            )
            dispatch_row_assignment_formula = summary.get(
                "future_kernel_native_dispatch_consumer_row_assignment_formula",
            )
            dispatch_program_iteration_hash = _hex64_metric(
                summary,
                "future_kernel_native_dispatch_consumer_program_iteration_hash",
            )
            dispatch_rows_per_program = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_rows_per_program",
            )
            mirror_row_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_single_field_mirror_row_count",
            )
            mirror_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count",
            )
            if row_count_value is not None and native_row_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_row_count_mismatch"
                )
            if row_count_value is not None and native_row_ok_count != row_count_value:
                failures.append(
                    f"{prefix}_future_kernel_native_consumer_row_ok_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and dispatch_row_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_row_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and dispatch_row_ok_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_row_ok_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and mirror_row_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_mirror_row_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and mirror_row_ok_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_mirror_row_ok_count_mismatch"
                )
            if dispatch_row_offset is None or dispatch_row_offset < 0:
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_row_offset_invalid"
                )
            if (
                row_count_value is not None
                and (dispatch_row_limit is None or dispatch_row_limit > row_count_value)
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_row_limit_invalid"
                )
            if (
                dispatch_row_offset is not None
                and dispatch_row_limit is not None
                and dispatch_active_rows != dispatch_row_limit - dispatch_row_offset
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_active_rows_mismatch"
                )
            if dispatch_full_table_required and row_count_value is not None:
                if dispatch_row_offset != 0:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_full_offset_mismatch"
                    )
                if dispatch_row_limit != row_count_value:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_full_limit_mismatch"
                    )
                if dispatch_active_rows != row_count_value:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_full_active_rows_mismatch"
                    )
            elif dispatch_tail_window_size is not None and row_count_value is not None:
                expected_row_offset = max(0, row_count_value - dispatch_tail_window_size)
                if dispatch_row_offset != expected_row_offset:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_tail_offset_mismatch"
                    )
                if dispatch_row_limit != row_count_value:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_tail_limit_mismatch"
                    )
                expected_active_rows = row_count_value - expected_row_offset
                if dispatch_active_rows != expected_active_rows:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_tail_active_rows_mismatch"
                    )
            if (
                dispatch_grid_x is None
                or dispatch_block_x is None
                or dispatch_launch_threads != dispatch_grid_x * dispatch_block_x
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_launch_threads_mismatch"
                )
            if (
                dispatch_block_x is not None
                and dispatch_rows_per_program is not None
                and dispatch_rows_per_program != dispatch_block_x
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_rows_per_program_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and dispatch_launch_threads is not None
                and dispatch_launch_threads < dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_launch_undercoverage"
                )
            if (
                dispatch_active_rows is not None
                and dispatch_block_x is not None
                and dispatch_launch_threads is not None
                and dispatch_launch_threads - dispatch_active_rows >= dispatch_block_x
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_launch_non_minimal"
                )
            if dispatch_program_iteration_checked is not True:
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_program_iteration_not_checked"
                )
            if dispatch_grid_x is not None and dispatch_program_count != dispatch_grid_x:
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_program_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and dispatch_block_x is not None
                and dispatch_grid_x is not None
            ):
                expected_full_program_count = dispatch_active_rows // dispatch_block_x
                previous_program_threads = (dispatch_grid_x - 1) * dispatch_block_x
                expected_last_program_active_rows = (
                    dispatch_active_rows - previous_program_threads
                )
                expected_inactive_lane_count = (
                    dispatch_grid_x * dispatch_block_x - dispatch_active_rows
                )
                if dispatch_full_program_count != expected_full_program_count:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_full_program_count_mismatch"
                    )
                if (
                    dispatch_last_program_active_rows
                    != expected_last_program_active_rows
                ):
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_last_program_active_rows_mismatch"
                    )
                if dispatch_inactive_lane_count != expected_inactive_lane_count:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_inactive_lane_count_mismatch"
                    )
                if dispatch_program_iteration_hash is None:
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_program_iteration_hash_missing"
                    )
                elif dispatch_row_offset is not None and dispatch_row_limit is not None:
                    expected_program_iteration_hash = _program_iteration_hash(
                        grid_x=dispatch_grid_x,
                        block_x=dispatch_block_x,
                        row_offset=dispatch_row_offset,
                        row_limit=dispatch_row_limit,
                        last_program_active_rows=expected_last_program_active_rows,
                        inactive_lane_count=expected_inactive_lane_count,
                    )
                    if (
                        dispatch_program_iteration_hash
                        != expected_program_iteration_hash
                    ):
                        failures.append(
                            f"{prefix}_future_kernel_native_dispatch_consumer_program_iteration_hash_mismatch"
                        )
                if (
                    dispatch_row_offset is not None
                    and dispatch_first_program_row_offset != dispatch_row_offset
                ):
                    failures.append(
                        f"{prefix}_future_kernel_native_dispatch_consumer_first_program_row_offset_mismatch"
                    )
                if dispatch_row_offset is not None:
                    expected_last_program_row_offset = (
                        dispatch_row_offset + previous_program_threads
                    )
                    if (
                        dispatch_last_program_row_offset
                        != expected_last_program_row_offset
                    ):
                        failures.append(
                            f"{prefix}_future_kernel_native_dispatch_consumer_last_program_row_offset_mismatch"
                        )
            if dispatch_row_assignment_formula != (
                "row_offset + program_id * rows_per_program + lane_id"
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_consumer_row_assignment_formula_mismatch"
                )
            expected_ptr_values = {
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
                "future_kernel_native_dispatch_ptr_consumer_error_count": 0,
                "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
                "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
                "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth": 2,
                "future_kernel_native_dispatch_ptr_consumer_payload_bytes": 0,
                "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel": False,
                "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args": False,
                "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible": False,
                "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation": False,
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_checked": True,
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_field_name": (
                    expected_field_name
                ),
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count": 0,
            }
            for key, expected_value in expected_ptr_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            failures.extend(
                _check_future_field_mask_summary(
                    summary,
                    prefix=prefix,
                    field_prefix="future_kernel_native_dispatch_ptr_consumer",
                    expected_field_name=expected_field_name,
                )
            )
            failures.extend(
                _check_layout_summary_fields(
                    summary,
                    prefix=prefix,
                    fields=(
                        FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS
                    ),
                    expected_values=(
                        FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED
                    ),
                    struct_size_key=(
                        "future_kernel_native_dispatch_ptr_consumer_packet_struct_size"
                    ),
                )
            )
            ptr_dispatch_row_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_ptr_consumer_row_count",
            )
            ptr_dispatch_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
            )
            ptr_mirror_row_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count",
            )
            ptr_mirror_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count",
            )
            if (
                dispatch_active_rows is not None
                and ptr_dispatch_row_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_ptr_consumer_row_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and ptr_dispatch_row_ok_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_ptr_consumer_row_ok_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and ptr_mirror_row_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_ptr_consumer_mirror_row_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and ptr_mirror_row_ok_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_dispatch_ptr_consumer_mirror_row_ok_count_mismatch"
                )
            expected_arg_slot_values = {
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
                "future_kernel_native_arg_slot_consumer_error_count": 0,
                "future_kernel_native_arg_slot_consumer_slot_visible": True,
                "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible": True,
                "future_kernel_native_arg_slot_consumer_dispatch_packet_visible": True,
                "future_kernel_native_arg_slot_consumer_packet_chain_depth": 3,
                "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
                "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
                "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
                "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
                "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
                "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
                "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": (
                    expected_field_name
                ),
                "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count": 0,
            }
            for key, expected_value in expected_arg_slot_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            failures.extend(
                _check_future_field_mask_summary(
                    summary,
                    prefix=prefix,
                    field_prefix="future_kernel_native_arg_slot_consumer",
                    expected_field_name=expected_field_name,
                )
            )
            failures.extend(
                _check_layout_summary_fields(
                    summary,
                    prefix=prefix,
                    fields=FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS,
                    expected_values=(
                        FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED
                    ),
                    struct_size_key=(
                        "future_kernel_native_arg_slot_consumer_slot_struct_size"
                    ),
                )
            )
            arg_slot_row_count = _int_metric(
                summary,
                "future_kernel_native_arg_slot_consumer_row_count",
            )
            arg_slot_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_arg_slot_consumer_row_ok_count",
            )
            arg_slot_mirror_row_count = _int_metric(
                summary,
                "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
            )
            arg_slot_mirror_row_ok_count = _int_metric(
                summary,
                "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
            )
            if (
                dispatch_active_rows is not None
                and arg_slot_row_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_arg_slot_consumer_row_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and arg_slot_row_ok_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_arg_slot_consumer_row_ok_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and arg_slot_mirror_row_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_arg_slot_consumer_mirror_row_count_mismatch"
                )
            if (
                dispatch_active_rows is not None
                and arg_slot_mirror_row_ok_count != dispatch_active_rows
            ):
                failures.append(
                    f"{prefix}_future_kernel_native_arg_slot_consumer_mirror_row_ok_count_mismatch"
                )

        def _check_runner_future_kernel_native_request_ptr_summary(
            summary: Any,
            prefix: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
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
                "future_kernel_native_consumer_request_ptr_payload_bytes": 0,
                "future_kernel_native_consumer_request_ptr_payload_deref_allowed": False,
                "future_kernel_native_consumer_request_ptr_passed_to_kernel": False,
                "future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed": False,
                "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args": False,
                "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible": False,
                "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation": False,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            if (
                _int_metric(summary, "future_kernel_native_consumer_request_ptr_request_id")
                is None
            ):
                failures.append(f"{prefix}_request_id_missing")
            row_count_value = _int_metric(summary, "row_count")
            read_suffixes = (
                "descriptor_ptr_read_row_ok_count",
                "packed_weight_descriptor_read_row_ok_count",
                "scale_metadata_handle_read_row_ok_count",
                "aux_metadata_handle_read_row_ok_count",
                "expert_id_read_row_ok_count",
                "address_key_hash_read_row_ok_count",
                "row_metadata_read_row_ok_count",
            )
            for summary_prefix in (
                "future_kernel_native_consumer_request_ptr_summary",
                "future_kernel_native_consumer_kernel_entry_summary",
            ):
                if (
                    row_count_value is not None
                    and _int_metric(summary, f"{summary_prefix}_row_count")
                    != row_count_value
                ):
                    failures.append(f"{prefix}_{summary_prefix}_row_count_mismatch")
                if (
                    row_count_value is not None
                    and _int_metric(summary, f"{summary_prefix}_row_ok_count")
                    != row_count_value
                ):
                    failures.append(f"{prefix}_{summary_prefix}_row_ok_count_mismatch")
                if _int_metric(summary, f"{summary_prefix}_error_count") != 0:
                    failures.append(f"{prefix}_{summary_prefix}_error_count_mismatch")
                if _int_metric(summary, f"{summary_prefix}_field_mask") != 15:
                    failures.append(f"{prefix}_{summary_prefix}_field_mask_mismatch")
                for suffix in read_suffixes:
                    if (
                        row_count_value is not None
                        and _int_metric(summary, f"{summary_prefix}_{suffix}")
                        != row_count_value
                    ):
                        failures.append(f"{prefix}_{summary_prefix}_{suffix}_mismatch")
                if _hex64_metric(summary, f"{summary_prefix}_row_hash_accumulator") is None:
                    failures.append(f"{prefix}_{summary_prefix}_row_hash_missing")
                if (
                    _hex64_metric(summary, f"{summary_prefix}_field_read_hash_accumulator")
                    is None
                ):
                    failures.append(f"{prefix}_{summary_prefix}_field_read_hash_missing")
                if (
                    _hex64_metric(
                        summary,
                        f"{summary_prefix}_row_metadata_hash_accumulator",
                    )
                    is None
                ):
                    failures.append(
                        f"{prefix}_{summary_prefix}_row_metadata_hash_missing"
                    )
            for suffix, failure_label in (
                ("row_hash_accumulator", "row_hash"),
                ("field_read_hash_accumulator", "field_read_hash"),
                ("row_metadata_hash_accumulator", "row_metadata_hash"),
            ):
                request_hash = _hex64_metric(
                    summary,
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
                )
                kernel_entry_hash = _hex64_metric(
                    summary,
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
                )
                if (
                    request_hash is not None
                    and kernel_entry_hash is not None
                    and request_hash != kernel_entry_hash
                ):
                    failures.append(f"{prefix}_request_ptr_{failure_label}_mismatch")

        def _check_runner_future_kernel_native_request_launch_summary(
            summary: Any,
            prefix: str,
        ) -> None:
            _check_runner_stub_summary(summary, prefix)
            if not isinstance(summary, dict):
                return
            expected_values = {
                "future_kernel_native_consumer_request_launch_abi_name": (
                    "premap_future_kernel_native_consumer_request_launch_abi_v1"
                ),
                "future_kernel_native_consumer_request_launch_mode": (
                    "readonly_future_kernel_native_consumer_request_launch_abi"
                ),
                "future_kernel_native_consumer_request_launch_source": (
                    "premap_future_kernel_native_consumer_request_ptr_abi_v1"
                ),
                "future_kernel_native_consumer_request_launch_field_read_path": (
                    "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
                ),
                "future_kernel_native_consumer_request_launch_checked": True,
                "future_kernel_native_consumer_request_launch_version": 1,
                "future_kernel_native_consumer_request_launch_packet_chain_depth": 5,
                "future_kernel_native_consumer_request_launch_pointer_size": 8,
                "future_kernel_native_consumer_request_launch_stream_domain": 0,
                "future_kernel_native_consumer_request_launch_payload_bytes": 0,
                "future_kernel_native_consumer_request_launch_payload_deref_allowed": False,
                "future_kernel_native_consumer_request_launch_passed_to_kernel": False,
                "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed": False,
                "future_kernel_native_consumer_request_launch_changes_kernel_launch_args": False,
                "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible": False,
                "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation": False,
            }
            for key, expected_value in expected_values.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{prefix}_{key}_mismatch")
            if (
                _int_metric(
                    summary,
                    "future_kernel_native_consumer_request_launch_request_id",
                )
                is None
            ):
                failures.append(f"{prefix}_request_id_missing")
            summary_device = _int_metric(summary, "device")
            request_launch_device_ordinal = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_device_ordinal",
            )
            if request_launch_device_ordinal is None:
                failures.append(f"{prefix}_request_launch_device_ordinal_missing")
            elif request_launch_device_ordinal < 0:
                failures.append(f"{prefix}_request_launch_device_ordinal_invalid")
            elif (
                summary_device is not None
                and request_launch_device_ordinal != summary_device
            ):
                failures.append(f"{prefix}_request_launch_device_ordinal_mismatch")
            row_count_value = _int_metric(summary, "row_count")
            request_launch_row_count = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_row_count",
            )
            request_launch_row_offset = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_row_offset",
            )
            request_launch_row_limit = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_row_limit",
            )
            request_launch_grid_x = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_grid_x",
            )
            request_launch_block_x = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_block_x",
            )
            request_launch_rows_per_program = _int_metric(
                summary,
                "future_kernel_native_consumer_request_launch_rows_per_program",
            )
            if row_count_value is not None and request_launch_row_count != row_count_value:
                failures.append(f"{prefix}_request_launch_row_count_mismatch")
            if request_launch_row_offset != 0:
                failures.append(f"{prefix}_request_launch_row_offset_mismatch")
            if row_count_value is not None and request_launch_row_limit != row_count_value:
                failures.append(f"{prefix}_request_launch_row_limit_mismatch")
            if request_launch_block_x is None or request_launch_block_x <= 0:
                failures.append(f"{prefix}_request_launch_block_x_invalid")
            elif request_launch_rows_per_program != request_launch_block_x:
                failures.append(f"{prefix}_request_launch_rows_per_program_mismatch")
            if (
                row_count_value is not None
                and request_launch_block_x is not None
                and request_launch_block_x > 0
                and request_launch_grid_x
                != (row_count_value + request_launch_block_x - 1)
                // request_launch_block_x
            ):
                failures.append(f"{prefix}_request_launch_grid_x_mismatch")
            read_suffixes = (
                "descriptor_ptr_read_row_ok_count",
                "packed_weight_descriptor_read_row_ok_count",
                "scale_metadata_handle_read_row_ok_count",
                "aux_metadata_handle_read_row_ok_count",
                "expert_id_read_row_ok_count",
                "address_key_hash_read_row_ok_count",
                "row_metadata_read_row_ok_count",
            )
            for summary_prefix in (
                "future_kernel_native_consumer_request_launch_summary",
                "future_kernel_native_consumer_request_ptr_summary",
                "future_kernel_native_consumer_kernel_entry_summary",
            ):
                if (
                    row_count_value is not None
                    and _int_metric(summary, f"{summary_prefix}_row_count")
                    != row_count_value
                ):
                    failures.append(f"{prefix}_{summary_prefix}_row_count_mismatch")
                if (
                    row_count_value is not None
                    and _int_metric(summary, f"{summary_prefix}_row_ok_count")
                    != row_count_value
                ):
                    failures.append(f"{prefix}_{summary_prefix}_row_ok_count_mismatch")
                if _int_metric(summary, f"{summary_prefix}_error_count") != 0:
                    failures.append(f"{prefix}_{summary_prefix}_error_count_mismatch")
                if _int_metric(summary, f"{summary_prefix}_field_mask") != 15:
                    failures.append(f"{prefix}_{summary_prefix}_field_mask_mismatch")
                for suffix in read_suffixes:
                    if (
                        row_count_value is not None
                        and _int_metric(summary, f"{summary_prefix}_{suffix}")
                        != row_count_value
                    ):
                        failures.append(f"{prefix}_{summary_prefix}_{suffix}_mismatch")
                for suffix in (
                    "row_hash_accumulator",
                    "field_read_hash_accumulator",
                    "row_metadata_hash_accumulator",
                ):
                    if _hex64_metric(summary, f"{summary_prefix}_{suffix}") is None:
                        failures.append(f"{prefix}_{summary_prefix}_{suffix}_missing")
            for suffix, failure_label in (
                ("row_hash_accumulator", "row_hash"),
                ("field_read_hash_accumulator", "field_read_hash"),
                ("row_metadata_hash_accumulator", "row_metadata_hash"),
            ):
                request_launch_hash = _hex64_metric(
                    summary,
                    f"future_kernel_native_consumer_request_launch_summary_{suffix}",
                )
                request_ptr_hash = _hex64_metric(
                    summary,
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
                )
                kernel_entry_hash = _hex64_metric(
                    summary,
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
                )
                if (
                    request_launch_hash is not None
                    and request_ptr_hash is not None
                    and request_launch_hash != request_ptr_hash
                ):
                    failures.append(
                        f"{prefix}_request_launch_{failure_label}_request_ptr_mismatch"
                    )
                if (
                    request_launch_hash is not None
                    and kernel_entry_hash is not None
                    and request_launch_hash != kernel_entry_hash
                ):
                    failures.append(
                        f"{prefix}_request_launch_{failure_label}_kernel_entry_mismatch"
                    )

        for summary_key, expected_field_name in (
            ("descriptor_ptr_mirror_stub_summary", "descriptor_ptr"),
            ("packed_weight_mirror_stub_summary", "packed_weight_descriptor"),
            ("kernel_envelope_mirror_stub_summary", "scale_metadata_handle"),
            ("aux_metadata_mirror_stub_summary", "aux_metadata_handle"),
        ):
            _check_runner_mirror_summary(
                evidence.get(summary_key),
                f"runner_{summary_key}",
                expected_field_name=expected_field_name,
            )
        _check_runner_kernel_side_compatible_summary(
            evidence.get("kernel_side_compatible_stub_summary"),
            "runner_kernel_side_compatible_stub_summary",
        )
        _check_runner_future_kernel_args_summary(
            evidence.get("future_kernel_args_stub_summary"),
            "runner_future_kernel_args_stub_summary",
        )
        _check_runner_future_kernel_args_compatible_path_summary(
            evidence.get("future_kernel_args_compatible_path_stub_summary"),
            "runner_future_kernel_args_compatible_path_stub_summary",
        )
        for summary_key, expected_field_name in (
            ("future_kernel_native_consumer_stub_summary", "scale_metadata_handle"),
            (
                "future_kernel_native_consumer_descriptor_ptr_stub_summary",
                "descriptor_ptr",
            ),
            (
                "future_kernel_native_consumer_packed_weight_stub_summary",
                "packed_weight_descriptor",
            ),
            (
                "future_kernel_native_consumer_aux_metadata_stub_summary",
                "aux_metadata_handle",
            ),
        ):
            _check_runner_future_kernel_native_consumer_summary(
                evidence.get(summary_key),
                f"runner_{summary_key}",
                expected_field_name=expected_field_name,
            )
        _check_runner_future_kernel_native_launch_consumer_summary(
            evidence.get("future_kernel_native_consumer_launch_stub_summary"),
            "runner_future_kernel_native_consumer_launch_stub_summary",
            expected_field_name="scale_metadata_handle",
        )
        for summary_key, expected_field_name in (
            (
                "future_kernel_native_consumer_launch_descriptor_ptr_stub_summary",
                "descriptor_ptr",
            ),
            (
                "future_kernel_native_consumer_launch_packed_weight_stub_summary",
                "packed_weight_descriptor",
            ),
            (
                "future_kernel_native_consumer_launch_aux_metadata_stub_summary",
                "aux_metadata_handle",
            ),
        ):
            _check_runner_future_kernel_native_launch_consumer_summary(
                evidence.get(summary_key),
                f"runner_{summary_key}",
                expected_field_name=expected_field_name,
            )
        _check_runner_future_kernel_native_dispatch_consumer_summary(
            evidence.get("future_kernel_native_consumer_dispatch_stub_summary"),
            "runner_future_kernel_native_consumer_dispatch_stub_summary",
            expected_field_name="scale_metadata_handle",
        )
        for summary_key, expected_field_name in (
            (
                "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary",
                "descriptor_ptr",
            ),
            (
                "future_kernel_native_consumer_dispatch_packed_weight_stub_summary",
                "packed_weight_descriptor",
            ),
            (
                "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary",
                "aux_metadata_handle",
            ),
        ):
            _check_runner_future_kernel_native_dispatch_consumer_summary(
                evidence.get(summary_key),
                f"runner_{summary_key}",
                expected_field_name=expected_field_name,
            )
        _check_runner_future_kernel_native_request_ptr_summary(
            evidence.get("future_kernel_native_consumer_request_ptr_stub_summary"),
            "runner_future_kernel_native_consumer_request_ptr_stub_summary",
        )
        # The request-launch ABI was added after the 32-input online runner
        # artifact became a lab-default evidence source. Keep the old
        # long-run runner focused on multi-input dispatch/request-ptr stability;
        # require request-launch through its dedicated online prelaunch input
        # canary, and validate the runner summary only when a refreshed artifact
        # already carries it.
        request_launch_summary = evidence.get(
            "future_kernel_native_consumer_request_launch_stub_summary"
        )
        if request_launch_summary is not None:
            _check_runner_future_kernel_native_request_launch_summary(
                request_launch_summary,
                "runner_future_kernel_native_consumer_request_launch_stub_summary",
            )
        extra_summaries = evidence.get("extra_online_input_check_summaries")
        if not isinstance(extra_summaries, list):
            failures.append("runner_extra_online_input_check_summaries_missing")
            extra_summaries = []
        elif len(extra_summaries) != expected_extra:
            failures.append("runner_extra_online_input_check_summaries_count_mismatch")
        expected_extra_labels = {
            "native_stub": None,
            "native_stub_per_field": None,
            "native_stub_kernel_envelope_mirror": "scale_metadata_handle",
            "native_stub_packed_weight_mirror": "packed_weight_descriptor",
            "native_stub_aux_metadata_mirror": "aux_metadata_handle",
            "native_stub_descriptor_ptr_mirror": "descriptor_ptr",
            "native_stub_kernel_side_compatible_consumer_abi": "kernel_side_compatible",
            "native_stub_future_kernel_consumer_args": "future_kernel_args",
            "native_stub_future_kernel_args_compatible_consumer_path": (
                "future_kernel_args_compatible_path"
            ),
            "native_stub_future_kernel_native_consumer_abi": (
                "future_kernel_native_consumer:scale_metadata_handle"
            ),
            "native_stub_future_kernel_native_consumer_descriptor_ptr_mirror": (
                "future_kernel_native_consumer:descriptor_ptr"
            ),
            "native_stub_future_kernel_native_consumer_packed_weight_mirror": (
                "future_kernel_native_consumer:packed_weight_descriptor"
            ),
            "native_stub_future_kernel_native_consumer_aux_metadata_mirror": (
                "future_kernel_native_consumer:aux_metadata_handle"
            ),
            "native_stub_future_kernel_native_consumer_launch_abi": (
                "future_kernel_native_launch_consumer:scale_metadata_handle"
            ),
            "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror": (
                "future_kernel_native_launch_consumer:descriptor_ptr"
            ),
            "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror": (
                "future_kernel_native_launch_consumer:packed_weight_descriptor"
            ),
            "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror": (
                "future_kernel_native_launch_consumer:aux_metadata_handle"
            ),
            "native_stub_future_kernel_native_consumer_dispatch_abi": (
                "future_kernel_native_dispatch_consumer:scale_metadata_handle"
            ),
            "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror": (
                "future_kernel_native_dispatch_consumer:descriptor_ptr"
            ),
            "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror": (
                "future_kernel_native_dispatch_consumer:packed_weight_descriptor"
            ),
            "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror": (
                "future_kernel_native_dispatch_consumer:aux_metadata_handle"
            ),
            "native_stub_future_kernel_native_consumer_request_ptr_abi": (
                "future_kernel_native_request_ptr"
            ),
        }
        for index, suite in enumerate(extra_summaries[:expected_extra], start=1):
            suite_prefix = f"runner_extra_input_{index:04d}"
            if not isinstance(suite, dict):
                failures.append(f"{suite_prefix}_invalid")
                continue
            if suite.get("passed") is not True:
                failures.append(f"{suite_prefix}_not_passed")
            if suite.get("failures") != []:
                failures.append(f"{suite_prefix}_failures_not_empty")
            outputs = suite.get("outputs")
            if not isinstance(outputs, dict):
                failures.append(f"{suite_prefix}_outputs_missing")
                outputs = {}
            for label, expected_field_name in expected_extra_labels.items():
                entry = outputs.get(label)
                label_prefix = f"{suite_prefix}_{label}"
                if not isinstance(entry, dict):
                    failures.append(f"{label_prefix}_missing")
                    continue
                summary = entry.get("summary")
                if expected_field_name is None:
                    _check_runner_stub_summary(
                        summary,
                        label_prefix,
                        require_kernel_side_consumer_path=(label == "native_stub"),
                    )
                elif expected_field_name == "kernel_side_compatible":
                    _check_runner_kernel_side_compatible_summary(
                        summary,
                        label_prefix,
                    )
                elif expected_field_name == "future_kernel_args":
                    _check_runner_future_kernel_args_summary(
                        summary,
                        label_prefix,
                    )
                elif expected_field_name == "future_kernel_args_compatible_path":
                    _check_runner_future_kernel_args_compatible_path_summary(
                        summary,
                        label_prefix,
                    )
                elif expected_field_name.startswith(
                    "future_kernel_native_consumer:"
                ):
                    _check_runner_future_kernel_native_consumer_summary(
                        summary,
                        label_prefix,
                        expected_field_name=expected_field_name.split(":", 1)[1],
                    )
                elif expected_field_name.startswith(
                    "future_kernel_native_launch_consumer:"
                ):
                    _check_runner_future_kernel_native_launch_consumer_summary(
                        summary,
                        label_prefix,
                        expected_field_name=expected_field_name.split(":", 1)[1],
                    )
                elif expected_field_name.startswith(
                    "future_kernel_native_dispatch_consumer:"
                ):
                    _check_runner_future_kernel_native_dispatch_consumer_summary(
                        summary,
                        label_prefix,
                        expected_field_name=expected_field_name.split(":", 1)[1],
                    )
                elif expected_field_name == "future_kernel_native_request_ptr":
                    _check_runner_future_kernel_native_request_ptr_summary(
                        summary,
                        label_prefix,
                    )
                elif expected_field_name == "future_kernel_native_request_launch":
                    _check_runner_future_kernel_native_request_launch_summary(
                        summary,
                        label_prefix,
                    )
                else:
                    _check_runner_mirror_summary(
                        summary,
                        label_prefix,
                        expected_field_name=expected_field_name,
                    )
        artifact_check_summary = evidence.get("artifact_check_summary")
        using_bootstrap_artifact_summary = False
        if (
            not isinstance(artifact_check_summary, dict)
            and allow_online_runner_self_finalization
        ):
            bootstrap_summary = evidence.get("artifact_check_bootstrap_summary")
            if isinstance(bootstrap_summary, dict):
                if bootstrap_summary.get("bootstrap_preflight_allowed") is True:
                    artifact_check_summary = bootstrap_summary
                    using_bootstrap_artifact_summary = True
                else:
                    failures.append(
                        "runner_artifact_check_bootstrap_summary_not_bootstrap"
                    )
        if not isinstance(artifact_check_summary, dict):
            failures.append("runner_artifact_check_summary_missing")
            artifact_check_summary = {}
        if artifact_check_summary.get("passed") is not True:
            failures.append("runner_artifact_check_summary_not_passed")
        if artifact_check_summary.get("failures") != []:
            failures.append("runner_artifact_check_summary_failures_not_empty")
        artifact_min_inputs = _int_metric(
            artifact_check_summary,
            "min_online_inputs",
        )
        if artifact_min_inputs is None:
            failures.append("runner_artifact_check_min_online_inputs_missing")
        if (
            artifact_min_inputs is not None
            and artifact_min_inputs < expected_online_input_count
        ):
            failures.append("runner_artifact_check_min_online_inputs_invalid")
        artifact_final_deferred_count = _int_metric(
            artifact_check_summary,
            "final_deferred_count",
        )
        if artifact_final_deferred_count is None:
            if not (
                allow_online_runner_self_finalization
                and using_bootstrap_artifact_summary
            ):
                failures.append("runner_artifact_check_final_deferred_count_missing")
        elif artifact_final_deferred_count != 0:
            failures.append("runner_artifact_check_final_deferred_count_nonzero")
        artifact_input_check_count = _int_metric(
            artifact_check_summary,
            "runner_online_prelaunch_input_check_count",
        )
        if artifact_input_check_count is None:
            failures.append("runner_artifact_check_online_input_check_count_missing")
        if (
            artifact_input_check_count is not None
            and artifact_input_check_count < expected_online_input_count
        ):
            failures.append("runner_artifact_check_online_input_check_count_invalid")
        if (
            artifact_input_check_count is not None
            and artifact_input_check_count != input_check_count
        ):
            failures.append("runner_artifact_check_online_input_count_mismatch")
        artifact_extra_count = _int_metric(
            artifact_check_summary,
            "runner_online_prelaunch_input_extra_check_count",
        )
        artifact_extra_passed_count = _int_metric(
            artifact_check_summary,
            "runner_online_prelaunch_input_extra_check_passed_count",
        )
        if artifact_extra_count != extra_check_count:
            failures.append("runner_artifact_check_extra_count_mismatch")
        if artifact_extra_passed_count != extra_passed_count:
            failures.append("runner_artifact_check_extra_passed_count_mismatch")
        failures.extend(
            _validate_online_input_row_stats(
                artifact_check_summary,
                expected_online_input_count=expected_online_input_count,
                failure_prefix="runner_artifact_check_online_input",
            )
        )
        final_status_summary = evidence.get("final_preflight_status_summary")
        if not isinstance(final_status_summary, dict):
            if not allow_online_runner_self_finalization:
                failures.append("runner_final_preflight_status_summary_missing")
            final_status_summary = {}
        if (
            not allow_online_runner_self_finalization
            and final_status_summary.get("passed") is not True
        ):
            failures.append("runner_final_preflight_status_not_passed")
        final_strict_deferred = _int_metric(
            final_status_summary,
            "strict_default_gate_evidence_deferred_count",
        )
        final_runtime_deferred = _int_metric(
            final_status_summary,
            "runtime_gate_evidence_deferred_count",
        )
        if allow_online_runner_self_finalization:
            return [f"{evidence_label}:{failure}" for failure in failures]
        if final_strict_deferred is None:
            failures.append("runner_final_strict_deferred_count_missing")
        elif final_strict_deferred != 0:
            failures.append("runner_final_strict_deferred_count_nonzero")
        if final_runtime_deferred is None:
            failures.append("runner_final_runtime_deferred_count_missing")
        elif final_runtime_deferred != 0:
            failures.append("runner_final_runtime_deferred_count_nonzero")
        return [f"{evidence_label}:{failure}" for failure in failures]
    if evidence_label in known_stub_labels:
        expected_input_path = None
        if isinstance(evidence_paths, dict):
            input_label = (
                "native_typed_consumer_online_prelaunch_input_json"
                if evidence_label
                in {
                    "native_typed_consumer_stub_online_prelaunch_input_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
                }
                else "native_typed_consumer_bridge_input_json"
            )
            raw_input = evidence_paths.get(input_label)
            if isinstance(raw_input, str) and raw_input:
                expected_input_path = raw_input
            raw_export_performance = evidence_paths.get(
                "native_typed_consumer_online_prelaunch_export_performance_json"
            )
            export_performance_path = (
                raw_export_performance
                if isinstance(raw_export_performance, str)
                and raw_export_performance
                and evidence_label
                in {
                    "native_typed_consumer_stub_online_prelaunch_input_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json",
                    "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
                }
                else None
            )
        is_online_prelaunch_stub = evidence_label in {
            "native_typed_consumer_stub_online_prelaunch_input_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
        }
        is_per_field_stub = (
            evidence_label
            == "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json"
        )
        is_endpoint_ptr_stub = evidence_label in {
            "native_typed_consumer_stub_endpoint_ptr_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json",
        }
        is_request_ptr_stub = (
            evidence_label
            == "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json"
        )
        is_request_launch_stub = (
            evidence_label
            == "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json"
        )
        is_request_launch_ptr_stub = (
            evidence_label
            == "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json"
        )
        endpoint_ptr_expected_field_mask = (
            15
            if evidence_label
            == "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json"
            else 7
        )
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_native_typed_consumer_stub_evidence(
                evidence,
                expected_input_path=expected_input_path,
                export_performance_path=export_performance_path,
                root=root,
                require_extended_noop_meta=is_online_prelaunch_stub,
                require_online_export_context=is_online_prelaunch_stub,
                required_enabled_macros=(
                    (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
                        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
                    )
                    if is_per_field_stub
                    else (
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
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI",
                    )
                    if is_endpoint_ptr_stub
                    else (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI",
                    )
                    if is_request_ptr_stub
                    else (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI",
                    )
                    if is_request_launch_stub
                    else (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI",
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI",
                    )
                    if is_request_launch_ptr_stub
                    else None
                ),
                required_disabled_macros=(
                    ("MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",)
                    if is_per_field_stub
                    else ()
                ),
                require_kernel_side_abi_meta=is_per_field_stub,
                require_endpoint_ptr_abi_meta=is_endpoint_ptr_stub,
                endpoint_ptr_expected_field_mask=endpoint_ptr_expected_field_mask,
                require_request_ptr_abi_meta=is_request_ptr_stub,
                request_ptr_expected_field_mask=15,
                require_request_launch_abi_meta=is_request_launch_stub,
                request_launch_expected_field_mask=15,
                require_request_launch_ptr_abi_meta=is_request_launch_ptr_stub,
                request_launch_ptr_expected_field_mask=15,
            )
        ]
    if not isinstance(metrics, dict):
        return [f"{evidence_label}:metrics_missing_or_not_mapping"]
    if evidence_label == "strict_native_typed_consumer_bridge_128_gate_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_native_bridge_evidence(metrics)
        ]
    if evidence_label == "strict_single_field_handle_handoff_canary_128_gate_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_single_field_canary_evidence(metrics)
        ]
    if evidence_label == "packed_weight_single_field_handle_handoff_canary_smoke_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_single_field_canary_evidence(
                metrics,
                expected_field_name="packed_weight_descriptor",
            )
        ]
    if evidence_label == "aux_metadata_single_field_handle_handoff_canary_smoke_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_single_field_canary_evidence(
                metrics,
                expected_field_name="aux_metadata_handle",
            )
        ]
    if evidence_label == "descriptor_ptr_single_field_handle_handoff_canary_smoke_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_single_field_canary_evidence(
                metrics,
                expected_field_name="descriptor_ptr",
            )
        ]
    if evidence_label == "strict_kernel_side_typed_row_consumer_path_128_gate_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_typed_row_consumer_path_evidence(metrics)
        ]
    return [
        f"{evidence_label}:{failure}"
        for failure in _validate_native_stub_evidence(metrics)
    ]


def _validate_native_typed_consumer_stub_evidence(
    evidence: dict[str, Any],
    *,
    expected_input_path: str | None = None,
    export_performance_path: str | None = None,
    root: Path | None = None,
    require_extended_noop_meta: bool = False,
    require_online_export_context: bool = False,
    required_enabled_macros: tuple[str, ...] | None = None,
    required_disabled_macros: tuple[str, ...] = (),
    require_kernel_side_abi_meta: bool = False,
    require_endpoint_ptr_abi_meta: bool = False,
    endpoint_ptr_expected_field_mask: int = 7,
    require_request_ptr_abi_meta: bool = False,
    request_ptr_expected_field_mask: int = 15,
    require_request_launch_abi_meta: bool = False,
    request_launch_expected_field_mask: int = 15,
    require_request_launch_ptr_abi_meta: bool = False,
    request_launch_ptr_expected_field_mask: int = 15,
) -> list[str]:
    failures: list[str] = []
    row_count = _int_metric(evidence, "row_count")
    row_ok_count = _int_metric(evidence, "row_ok_count")
    if row_count is None or row_count <= 0:
        failures.append("native_typed_consumer_stub_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("native_typed_consumer_stub_row_ok_count_mismatch")
    expected = {
        "ok": True,
        "error_count": 0,
        "column_count": 4,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "input_source": "binary_prefix",
        "expected_schema_hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
    }
    for key, expected_value in expected.items():
        actual = evidence.get(key)
        if actual != expected_value:
            failures.append(f"native_typed_consumer_stub_{key}_mismatch")
    if require_kernel_side_abi_meta:
        expected_abi = {
            "abi_name": "premap_kernel_side_typed_consumer_abi_v1",
            "abi_handle_column_count": 4,
            "abi_payload_bytes_allowed": False,
            "abi_kernel_arg_pass_allowed": False,
            "adapter_name": "premap_kernel_side_typed_consumer_adapter_v1",
            "adapter_payload_deref_allowed": False,
            "adapter_kernel_arg_pass_allowed": False,
        }
        for key, expected_value in expected_abi.items():
            if evidence.get(key) != expected_value:
                failures.append(f"native_typed_consumer_stub_{key}_mismatch")
        abi_header = evidence.get("abi_header")
        if not isinstance(abi_header, str) or not abi_header.endswith(
            "premap_typed_consumer_abi_v1.h"
        ):
            failures.append("native_typed_consumer_stub_abi_header_mismatch")
        adapter_header = evidence.get("adapter_header")
        if not isinstance(adapter_header, str) or not adapter_header.endswith(
            "premap_typed_consumer_adapter_v1.h"
        ):
            failures.append("native_typed_consumer_stub_adapter_header_mismatch")
    if require_endpoint_ptr_abi_meta:
        expected_endpoint_ptr_values: dict[str, Any] = {
            "future_kernel_native_consumer_endpoint_ptr_abi_name": (
                "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_endpoint_ptr_mode": (
                "readonly_future_kernel_native_consumer_endpoint_ptr_abi"
            ),
            "future_kernel_native_consumer_endpoint_ptr_source": (
                "premap_future_kernel_native_consumer_endpoint_abi_v1"
            ),
            "future_kernel_native_consumer_endpoint_ptr_field_read_path": (
                "endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_endpoint_ptr_checked": True,
            "future_kernel_native_consumer_endpoint_ptr_version": 1,
            "future_kernel_native_consumer_endpoint_ptr_packet_chain_depth": 13,
            "future_kernel_native_consumer_endpoint_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_endpoint_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_endpoint_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_endpoint_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_endpoint_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_endpoint_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
        }
        for key, expected_value in expected_endpoint_ptr_values.items():
            if evidence.get(key) != expected_value:
                failures.append(f"native_typed_consumer_stub_{key}_mismatch")
        endpoint_ptr_row_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_endpoint_ptr_summary_row_count",
        )
        endpoint_ptr_row_ok_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_endpoint_ptr_summary_row_ok_count",
        )
        endpoint_ptr_error_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_endpoint_ptr_summary_error_count",
        )
        if row_count is not None and endpoint_ptr_row_count != row_count:
            failures.append(
                "native_typed_consumer_stub_endpoint_ptr_summary_row_count_mismatch"
            )
        if row_count is not None and endpoint_ptr_row_ok_count != row_count:
            failures.append(
                "native_typed_consumer_stub_endpoint_ptr_summary_row_ok_count_mismatch"
            )
        if endpoint_ptr_error_count != 0:
            failures.append(
                "native_typed_consumer_stub_endpoint_ptr_summary_error_count_mismatch"
            )
        endpoint_ptr_hash = evidence.get(
            "future_kernel_native_consumer_endpoint_ptr_summary_row_hash_accumulator"
        )
        endpoint_hash = evidence.get(
            "future_kernel_native_consumer_endpoint_summary_row_hash_accumulator"
        )
        for summary_prefix in (
            "future_kernel_native_consumer_endpoint_summary_",
            "future_kernel_native_consumer_endpoint_ptr_summary_",
        ):
            if (
                _int_metric(evidence, f"{summary_prefix}field_mask")
                != endpoint_ptr_expected_field_mask
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}field_mask_mismatch"
                )
            expected_aux_count = (
                row_count if endpoint_ptr_expected_field_mask & 8 else 0
            )
            read_count_expectations = {
                "descriptor_ptr_read_row_ok_count": row_count,
                "packed_weight_descriptor_read_row_ok_count": row_count,
                "scale_metadata_handle_read_row_ok_count": row_count,
                "aux_metadata_handle_read_row_ok_count": expected_aux_count,
                "expert_id_read_row_ok_count": row_count,
                "address_key_hash_read_row_ok_count": row_count,
                "row_metadata_read_row_ok_count": row_count,
            }
            for suffix, expected_value in read_count_expectations.items():
                if _int_metric(evidence, f"{summary_prefix}{suffix}") != expected_value:
                    failures.append(
                        f"native_typed_consumer_stub_{summary_prefix}{suffix}_mismatch"
                    )
        if not isinstance(endpoint_ptr_hash, str) or not endpoint_ptr_hash:
            failures.append(
                "native_typed_consumer_stub_endpoint_ptr_summary_row_hash_missing"
            )
        if not isinstance(endpoint_hash, str) or not endpoint_hash:
            failures.append(
                "native_typed_consumer_stub_endpoint_summary_row_hash_missing"
            )
        if (
            isinstance(endpoint_ptr_hash, str)
            and isinstance(endpoint_hash, str)
            and endpoint_ptr_hash != endpoint_hash
        ):
            failures.append(
                "native_typed_consumer_stub_endpoint_ptr_summary_row_hash_mismatch"
            )
    if require_request_ptr_abi_meta:
        expected_request_ptr_values: dict[str, Any] = {
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
            "future_kernel_native_consumer_request_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_request_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation": False,
        }
        for key, expected_value in expected_request_ptr_values.items():
            if evidence.get(key) != expected_value:
                failures.append(f"native_typed_consumer_stub_{key}_mismatch")
        if _int_metric(evidence, "future_kernel_native_consumer_request_ptr_request_id") is None:
            failures.append("native_typed_consumer_stub_request_ptr_request_id_missing")
        if _int_metric(evidence, "future_kernel_native_consumer_request_ptr_pointer_size") != 8:
            failures.append("native_typed_consumer_stub_request_ptr_pointer_size_mismatch")
        request_ptr_row_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_ptr_summary_row_count",
        )
        request_ptr_row_ok_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_ptr_summary_row_ok_count",
        )
        request_ptr_error_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_ptr_summary_error_count",
        )
        if row_count is not None and request_ptr_row_count != row_count:
            failures.append(
                "native_typed_consumer_stub_request_ptr_summary_row_count_mismatch"
            )
        if row_count is not None and request_ptr_row_ok_count != row_count:
            failures.append(
                "native_typed_consumer_stub_request_ptr_summary_row_ok_count_mismatch"
            )
        if request_ptr_error_count != 0:
            failures.append(
                "native_typed_consumer_stub_request_ptr_summary_error_count_mismatch"
            )
        if (
            _int_metric(evidence, "future_kernel_native_consumer_request_ptr_summary_field_mask")
            != request_ptr_expected_field_mask
        ):
            failures.append(
                "native_typed_consumer_stub_request_ptr_summary_field_mask_mismatch"
            )
        expected_aux_count = (
            row_count if request_ptr_expected_field_mask & 8 else 0
        )
        request_ptr_read_count_expectations = {
            "descriptor_ptr_read_row_ok_count": row_count,
            "packed_weight_descriptor_read_row_ok_count": row_count,
            "scale_metadata_handle_read_row_ok_count": row_count,
            "aux_metadata_handle_read_row_ok_count": expected_aux_count,
            "expert_id_read_row_ok_count": row_count,
            "address_key_hash_read_row_ok_count": row_count,
            "row_metadata_read_row_ok_count": row_count,
        }
        for suffix, expected_value in request_ptr_read_count_expectations.items():
            if (
                _int_metric(
                    evidence,
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
                )
                != expected_value
            ):
                failures.append(
                    "native_typed_consumer_stub_"
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}_mismatch"
                )
        kernel_entry_row_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_kernel_entry_summary_row_count",
        )
        kernel_entry_row_ok_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_kernel_entry_summary_row_ok_count",
        )
        kernel_entry_error_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_kernel_entry_summary_error_count",
        )
        if row_count is not None and kernel_entry_row_count != row_count:
            failures.append(
                "native_typed_consumer_stub_kernel_entry_summary_row_count_mismatch"
            )
        if row_count is not None and kernel_entry_row_ok_count != row_count:
            failures.append(
                "native_typed_consumer_stub_kernel_entry_summary_row_ok_count_mismatch"
            )
        if kernel_entry_error_count != 0:
            failures.append(
                "native_typed_consumer_stub_kernel_entry_summary_error_count_mismatch"
            )
        if (
            _int_metric(evidence, "future_kernel_native_consumer_kernel_entry_summary_field_mask")
            != request_ptr_expected_field_mask
        ):
            failures.append(
                "native_typed_consumer_stub_kernel_entry_summary_field_mask_mismatch"
            )
        for suffix, expected_value in request_ptr_read_count_expectations.items():
            if (
                _int_metric(
                    evidence,
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
                )
                != expected_value
            ):
                failures.append(
                    "native_typed_consumer_stub_"
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}_mismatch"
                )
        request_ptr_hash = _hex64_metric(
            evidence,
            "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator",
        )
        kernel_entry_hash = _hex64_metric(
            evidence,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator",
        )
        if _hex64_metric(
            evidence,
            "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator",
        ) is None:
            failures.append(
                "native_typed_consumer_stub_request_ptr_summary_row_hash_missing"
            )
        if _hex64_metric(
            evidence,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator",
        ) is None:
            failures.append(
                "native_typed_consumer_stub_kernel_entry_summary_row_hash_missing"
            )
        if (
            request_ptr_hash is not None
            and kernel_entry_hash is not None
            and request_ptr_hash != kernel_entry_hash
        ):
            failures.append(
                "native_typed_consumer_stub_request_ptr_summary_row_hash_mismatch"
            )
        for suffix in (
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        ):
            request_ptr_hash = _hex64_metric(
                evidence,
                f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
            )
            kernel_entry_hash = _hex64_metric(
                evidence,
                f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
            )
            failure_suffix = suffix.removesuffix("_accumulator")
            if (
                _hex64_metric(
                    evidence,
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
                )
                is None
            ):
                failures.append(
                    "native_typed_consumer_stub_request_ptr_summary_"
                    f"{failure_suffix}_missing"
                )
            if (
                _hex64_metric(
                    evidence,
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
                )
                is None
            ):
                failures.append(
                    "native_typed_consumer_stub_kernel_entry_summary_"
                    f"{failure_suffix}_missing"
                )
            if (
                request_ptr_hash is not None
                and kernel_entry_hash is not None
                and request_ptr_hash != kernel_entry_hash
            ):
                failures.append(
                    "native_typed_consumer_stub_request_ptr_summary_"
                    f"{failure_suffix}_mismatch"
                )
    if require_request_launch_abi_meta:
        expected_request_launch_values: dict[str, Any] = {
            "future_kernel_native_consumer_request_launch_abi_name": (
                "premap_future_kernel_native_consumer_request_launch_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_mode": (
                "readonly_future_kernel_native_consumer_request_launch_abi"
            ),
            "future_kernel_native_consumer_request_launch_source": (
                "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_field_read_path": (
                "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_launch_checked": True,
            "future_kernel_native_consumer_request_launch_version": 1,
            "future_kernel_native_consumer_request_launch_packet_chain_depth": 5,
            "future_kernel_native_consumer_request_launch_pointer_size": 8,
            "future_kernel_native_consumer_request_launch_stream_domain": 0,
            "future_kernel_native_consumer_request_launch_payload_bytes": 0,
            "future_kernel_native_consumer_request_launch_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_launch_passed_to_kernel": False,
            "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_launch_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation": False,
        }
        for key, expected_value in expected_request_launch_values.items():
            if evidence.get(key) != expected_value:
                failures.append(f"native_typed_consumer_stub_{key}_mismatch")
        if (
            _int_metric(
                evidence,
                "future_kernel_native_consumer_request_launch_request_id",
            )
            is None
        ):
            failures.append(
                "native_typed_consumer_stub_request_launch_request_id_missing"
            )
        evidence_device = _int_metric(evidence, "device")
        request_launch_device_ordinal = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_device_ordinal",
        )
        if request_launch_device_ordinal is None:
            failures.append(
                "native_typed_consumer_stub_request_launch_device_ordinal_missing"
            )
        elif request_launch_device_ordinal < 0:
            failures.append(
                "native_typed_consumer_stub_request_launch_device_ordinal_invalid"
            )
        elif (
            evidence_device is not None
            and request_launch_device_ordinal != evidence_device
        ):
            failures.append(
                "native_typed_consumer_stub_request_launch_device_ordinal_mismatch"
            )
        request_launch_row_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_summary_row_count",
        )
        if row_count is not None and request_launch_row_count != row_count:
            failures.append(
                "native_typed_consumer_stub_request_launch_summary_row_count_mismatch"
            )
        if (
            request_launch_row_count is not None
            and _int_metric(
                evidence,
                "future_kernel_native_consumer_request_launch_row_count",
            )
            != request_launch_row_count
        ):
            failures.append(
                "native_typed_consumer_stub_request_launch_row_count_mismatch"
            )
        request_launch_row_offset = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_row_offset",
        )
        request_launch_row_limit = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_row_limit",
        )
        if request_launch_row_offset != 0:
            failures.append(
                "native_typed_consumer_stub_request_launch_row_offset_mismatch"
            )
        if (
            request_launch_row_count is not None
            and request_launch_row_limit != request_launch_row_count
        ):
            failures.append(
                "native_typed_consumer_stub_request_launch_row_limit_mismatch"
            )
        request_launch_grid_x = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_grid_x",
        )
        request_launch_block_x = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_block_x",
        )
        request_launch_rows_per_program = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_rows_per_program",
        )
        if request_launch_block_x is None or request_launch_block_x <= 0:
            failures.append(
                "native_typed_consumer_stub_request_launch_block_x_invalid"
            )
        if request_launch_rows_per_program != request_launch_block_x:
            failures.append(
                "native_typed_consumer_stub_request_launch_rows_per_program_mismatch"
            )
        if (
            request_launch_row_count is not None
            and request_launch_block_x is not None
            and request_launch_block_x > 0
            and request_launch_grid_x
            != (request_launch_row_count + request_launch_block_x - 1)
            // request_launch_block_x
        ):
            failures.append(
                "native_typed_consumer_stub_request_launch_grid_x_mismatch"
            )
        expected_aux_count = (
            row_count if request_launch_expected_field_mask & 8 else 0
        )
        request_launch_read_count_expectations = {
            "descriptor_ptr_read_row_ok_count": row_count,
            "packed_weight_descriptor_read_row_ok_count": row_count,
            "scale_metadata_handle_read_row_ok_count": row_count,
            "aux_metadata_handle_read_row_ok_count": expected_aux_count,
            "expert_id_read_row_ok_count": row_count,
            "address_key_hash_read_row_ok_count": row_count,
            "row_metadata_read_row_ok_count": row_count,
        }
        for summary_prefix in (
            "future_kernel_native_consumer_request_launch_summary",
            "future_kernel_native_consumer_request_ptr_summary",
            "future_kernel_native_consumer_kernel_entry_summary",
        ):
            if (
                row_count is not None
                and _int_metric(evidence, f"{summary_prefix}_row_count") != row_count
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_row_count_mismatch"
                )
            if (
                row_count is not None
                and _int_metric(evidence, f"{summary_prefix}_row_ok_count")
                != row_count
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_row_ok_count_mismatch"
                )
            if _int_metric(evidence, f"{summary_prefix}_error_count") != 0:
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_error_count_mismatch"
                )
            if (
                _int_metric(evidence, f"{summary_prefix}_field_mask")
                != request_launch_expected_field_mask
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_field_mask_mismatch"
                )
            for suffix, expected_value in request_launch_read_count_expectations.items():
                if _int_metric(evidence, f"{summary_prefix}_{suffix}") != expected_value:
                    failures.append(
                        "native_typed_consumer_stub_"
                        f"{summary_prefix}_{suffix}_mismatch"
                    )
        for suffix in (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        ):
            request_launch_hash = _hex64_metric(
                evidence,
                f"future_kernel_native_consumer_request_launch_summary_{suffix}",
            )
            request_ptr_hash = _hex64_metric(
                evidence,
                f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
            )
            kernel_entry_hash = _hex64_metric(
                evidence,
                f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
            )
            failure_suffix = suffix.removesuffix("_accumulator")
            if request_launch_hash is None:
                failures.append(
                    "native_typed_consumer_stub_request_launch_summary_"
                    f"{failure_suffix}_missing"
                )
            if request_ptr_hash is None:
                failures.append(
                    "native_typed_consumer_stub_request_ptr_summary_"
                    f"{failure_suffix}_missing"
                )
            if kernel_entry_hash is None:
                failures.append(
                    "native_typed_consumer_stub_kernel_entry_summary_"
                    f"{failure_suffix}_missing"
                )
            if (
                request_launch_hash is not None
                and request_ptr_hash is not None
                and request_launch_hash != request_ptr_hash
            ):
                failures.append(
                    "native_typed_consumer_stub_request_launch_summary_"
                    f"{failure_suffix}_request_ptr_mismatch"
                )
            if (
                request_launch_hash is not None
                and kernel_entry_hash is not None
                and request_launch_hash != kernel_entry_hash
            ):
                failures.append(
                    "native_typed_consumer_stub_request_launch_summary_"
                    f"{failure_suffix}_kernel_entry_mismatch"
                )
    if require_request_launch_ptr_abi_meta:
        expected_request_launch_ptr_values: dict[str, Any] = {
            "future_kernel_native_consumer_request_launch_ptr_abi_name": (
                "premap_future_kernel_native_consumer_request_launch_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_ptr_mode": (
                "readonly_future_kernel_native_consumer_request_launch_ptr_abi"
            ),
            "future_kernel_native_consumer_request_launch_ptr_source": (
                "premap_future_kernel_native_consumer_request_launch_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_ptr_field_read_path": (
                "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_launch_ptr_checked": True,
            "future_kernel_native_consumer_request_launch_ptr_version": 1,
            "future_kernel_native_consumer_request_launch_ptr_packet_chain_depth": 6,
            "future_kernel_native_consumer_request_launch_ptr_pointer_size": 8,
            "future_kernel_native_consumer_request_launch_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_request_launch_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_launch_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation": False,
        }
        for key, expected_value in expected_request_launch_ptr_values.items():
            if evidence.get(key) != expected_value:
                failures.append(f"native_typed_consumer_stub_{key}_mismatch")
        if (
            _int_metric(
                evidence,
                "future_kernel_native_consumer_request_launch_ptr_request_id",
            )
            is None
        ):
            failures.append(
                "native_typed_consumer_stub_request_launch_ptr_request_id_missing"
            )
        request_launch_ptr_row_count = _int_metric(
            evidence,
            "future_kernel_native_consumer_request_launch_ptr_summary_row_count",
        )
        if row_count is not None and request_launch_ptr_row_count != row_count:
            failures.append(
                "native_typed_consumer_stub_request_launch_ptr_summary_row_count_mismatch"
            )
        request_launch_ptr_read_count_expectations = {
            "descriptor_ptr_read_row_ok_count": row_count,
            "packed_weight_descriptor_read_row_ok_count": row_count,
            "scale_metadata_handle_read_row_ok_count": row_count,
            "aux_metadata_handle_read_row_ok_count": (
                row_count if request_launch_ptr_expected_field_mask & 8 else 0
            ),
            "expert_id_read_row_ok_count": row_count,
            "address_key_hash_read_row_ok_count": row_count,
            "row_metadata_read_row_ok_count": row_count,
        }
        for summary_prefix in (
            "future_kernel_native_consumer_request_launch_ptr_summary",
            "future_kernel_native_consumer_request_launch_summary",
            "future_kernel_native_consumer_request_ptr_summary",
            "future_kernel_native_consumer_kernel_entry_summary",
        ):
            if (
                row_count is not None
                and _int_metric(evidence, f"{summary_prefix}_row_count") != row_count
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_row_count_mismatch"
                )
            if (
                row_count is not None
                and _int_metric(evidence, f"{summary_prefix}_row_ok_count")
                != row_count
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_row_ok_count_mismatch"
                )
            if _int_metric(evidence, f"{summary_prefix}_error_count") != 0:
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_error_count_mismatch"
                )
            if (
                _int_metric(evidence, f"{summary_prefix}_field_mask")
                != request_launch_ptr_expected_field_mask
            ):
                failures.append(
                    f"native_typed_consumer_stub_{summary_prefix}_field_mask_mismatch"
                )
            for suffix, expected_value in request_launch_ptr_read_count_expectations.items():
                if _int_metric(evidence, f"{summary_prefix}_{suffix}") != expected_value:
                    failures.append(
                        "native_typed_consumer_stub_"
                        f"{summary_prefix}_{suffix}_mismatch"
                    )
        for suffix in (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        ):
            hashes = {
                "request_launch_ptr": _hex64_metric(
                    evidence,
                    f"future_kernel_native_consumer_request_launch_ptr_summary_{suffix}",
                ),
                "request_launch": _hex64_metric(
                    evidence,
                    f"future_kernel_native_consumer_request_launch_summary_{suffix}",
                ),
                "request_ptr": _hex64_metric(
                    evidence,
                    f"future_kernel_native_consumer_request_ptr_summary_{suffix}",
                ),
                "kernel_entry": _hex64_metric(
                    evidence,
                    f"future_kernel_native_consumer_kernel_entry_summary_{suffix}",
                ),
            }
            failure_suffix = suffix.removesuffix("_accumulator")
            for name, value in hashes.items():
                if value is None:
                    failures.append(
                        "native_typed_consumer_stub_"
                        f"{name}_summary_{failure_suffix}_missing"
                    )
            ptr_hash = hashes["request_launch_ptr"]
            for name in ("request_launch", "request_ptr", "kernel_entry"):
                other_hash = hashes[name]
                if ptr_hash is not None and other_hash is not None and ptr_hash != other_hash:
                    failures.append(
                        "native_typed_consumer_stub_request_launch_ptr_summary_"
                        f"{failure_suffix}_{name}_mismatch"
                    )
    if expected_input_path is None:
        failures.append("native_typed_consumer_stub_expected_input_json_missing")
    else:
        observed_input = evidence.get("input_json")
        if not isinstance(observed_input, str) or not observed_input:
            failures.append("native_typed_consumer_stub_input_json_missing")
        elif root is not None:
            expected_label = _path_label(
                _path_for_label(expected_input_path, root),
                root=root,
            )
            observed_label = _path_label(
                _path_for_label(observed_input, root),
                root=root,
            )
            if observed_label != expected_label:
                failures.append("native_typed_consumer_stub_input_json_mismatch")
        else:
            expected_label = str(expected_input_path)
        if root is not None:
            input_path = _path_for_label(expected_input_path, root)
            try:
                native_input = json.loads(input_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
                failures.append(
                    f"native_typed_consumer_stub_input_json_read_failed:{type(exc).__name__}"
                )
                native_input = None
            except json.JSONDecodeError:
                failures.append("native_typed_consumer_stub_input_json_invalid_json")
                native_input = None
            if isinstance(native_input, dict):
                meta = native_input.get("_meta")
                if not isinstance(meta, dict):
                    failures.append("native_typed_consumer_stub_input_meta_missing")
                    meta = {}
                if meta.get("schema_hash") != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                    failures.append("native_typed_consumer_stub_input_schema_hash_mismatch")
                if meta.get("row_count") != row_count:
                    failures.append("native_typed_consumer_stub_input_row_count_mismatch")
                if meta.get("column_count") != evidence.get("column_count"):
                    failures.append("native_typed_consumer_stub_input_column_count_mismatch")
                expected_meta_values: dict[str, Any] = {
                    "payload_bytes": 0,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                }
                if require_extended_noop_meta:
                    expected_meta_values.update(
                        {
                            "ready_credit": False,
                            "changes_router": False,
                            "changes_descriptor_order": False,
                        }
                    )
                for key, expected_value in expected_meta_values.items():
                    if meta.get(key) != expected_value:
                        failures.append(
                            f"native_typed_consumer_stub_input_{key}_mismatch"
                        )
                if require_online_export_context:
                    export_context = native_input.get("_export_context")
                    if not isinstance(export_context, dict):
                        failures.append(
                            "native_typed_consumer_stub_input_export_context_missing"
                        )
                        export_context = {}
                    expected_context_values: dict[str, Any] = {
                        "source": "vllm_prelaunch_premap_kernel_arg_shadow_table_object",
                        "row_count": row_count,
                        "column_count": evidence.get("column_count"),
                        "schema_hash": meta.get("schema_hash"),
                        "table_object_hash": meta.get("table_object_hash"),
                        "payload_bytes": 0,
                        "ready_credit": False,
                        "changes_router": False,
                        "changes_descriptor_order": False,
                        "passed_to_kernel": False,
                        "changes_kernel_launch_args": False,
                    }
                    for key, expected_value in expected_context_values.items():
                        if export_context.get(key) != expected_value:
                            failures.append(
                                "native_typed_consumer_stub_input_"
                                f"export_context_{key}_mismatch"
                            )
                for field in (
                    *PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
                    "expert_id",
                    "address_key_hash",
                ):
                    value = native_input.get(field)
                    if not isinstance(value, list):
                        failures.append(
                            f"native_typed_consumer_stub_input_{field}_missing_or_not_list"
                        )
                    elif row_count is not None and len(value) != row_count:
                        failures.append(
                            f"native_typed_consumer_stub_input_{field}_length_mismatch"
                        )
    if require_online_export_context:
        if export_performance_path is None:
            failures.append(
                "native_typed_consumer_stub_export_performance_json_missing"
            )
        elif root is not None:
            perf_path = _path_for_label(export_performance_path, root)
            try:
                perf = json.loads(perf_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
                failures.append(
                    "native_typed_consumer_stub_export_performance_json_read_failed:"
                    f"{type(exc).__name__}"
                )
                perf = None
            except json.JSONDecodeError:
                failures.append(
                    "native_typed_consumer_stub_export_performance_json_invalid_json"
                )
                perf = None
            if isinstance(perf, dict):
                if (
                    perf.get(
                        "runtime_shadow_premap_native_typed_consumer_input_export_enabled"
                    )
                    is not True
                ):
                    failures.append(
                        "native_typed_consumer_stub_export_performance_export_not_enabled"
                    )
                export_count = perf.get(
                    "runtime_shadow_premap_native_typed_consumer_input_export_count"
                )
                if not isinstance(export_count, int) or isinstance(export_count, bool):
                    failures.append(
                        "native_typed_consumer_stub_export_performance_count_invalid"
                    )
                elif export_count <= 0:
                    failures.append(
                        "native_typed_consumer_stub_export_performance_count_zero"
                    )
                if expected_input_path is not None:
                    expected_perf_label = _path_label(
                        _path_for_label(expected_input_path, root),
                        root=root,
                    )
                    first_path = perf.get(
                        "runtime_shadow_premap_native_typed_consumer_input_export_first_path"
                    )
                    if not isinstance(first_path, str) or not first_path:
                        failures.append(
                            "native_typed_consumer_stub_export_performance_first_path_missing"
                        )
                    else:
                        first_label = _path_label(
                            _path_for_label(first_path, root),
                            root=root,
                        )
                        if first_label != expected_perf_label:
                            failures.append(
                                "native_typed_consumer_stub_export_performance_first_path_mismatch"
                            )
                    raw_paths = perf.get(
                        "runtime_shadow_premap_native_typed_consumer_input_export_paths"
                    )
                    if not isinstance(raw_paths, list) or not raw_paths:
                        failures.append(
                            "native_typed_consumer_stub_export_performance_paths_missing"
                        )
                    else:
                        path_labels = {
                            _path_label(_path_for_label(str(path), root), root=root)
                            for path in raw_paths
                            if isinstance(path, str) and path
                        }
                        if expected_perf_label not in path_labels:
                            failures.append(
                                "native_typed_consumer_stub_export_performance_path_not_listed"
                            )
    macros = evidence.get("compiled_macros")
    if not isinstance(macros, dict):
        failures.append("native_typed_consumer_stub_compiled_macros_missing")
        macros = {}
    if required_enabled_macros is None:
        required_enabled_macros = (
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
            "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
        )
    for macro in required_enabled_macros:
        if macros.get(macro) is not True:
            failures.append(f"native_typed_consumer_stub_{macro}_not_enabled")
    for macro in required_disabled_macros:
        if macros.get(macro) is not False:
            failures.append(f"native_typed_consumer_stub_{macro}_not_disabled")
    for forbidden in (
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
    ):
        if macros.get(forbidden):
            failures.append(f"native_typed_consumer_stub_{forbidden}_enabled")
    mirror_macro = None
    expected_mirror_mode = None
    expected_mirror_field = None
    if macros.get("MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD"):
        mirror_macro = "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD"
        expected_mirror_mode = "readonly_descriptor_ptr_abi_row_mirror"
        expected_mirror_field = "descriptor_ptr"
    if macros.get("MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD"):
        if mirror_macro is not None:
            failures.append("native_typed_consumer_stub_multiple_mirror_macros_enabled")
        mirror_macro = "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD"
        expected_mirror_mode = "readonly_scale_metadata_handle_abi_row_mirror"
        expected_mirror_field = "scale_metadata_handle"
    if macros.get("MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD"):
        if mirror_macro is not None:
            failures.append("native_typed_consumer_stub_multiple_mirror_macros_enabled")
        mirror_macro = "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD"
        expected_mirror_mode = "readonly_packed_weight_descriptor_abi_row_mirror"
        expected_mirror_field = "packed_weight_descriptor"
    if macros.get("MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD"):
        if mirror_macro is not None:
            failures.append("native_typed_consumer_stub_multiple_mirror_macros_enabled")
        mirror_macro = "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD"
        expected_mirror_mode = "readonly_aux_metadata_handle_abi_row_mirror"
        expected_mirror_field = "aux_metadata_handle"
    if mirror_macro is not None:
        expected_mirror = {
            "single_field_mirror_checked": True,
            "single_field_mirror_mode": expected_mirror_mode,
            "single_field_mirror_field_name": expected_mirror_field,
            "single_field_mirror_source": "typed_consumer_abi_row_adapter_v1",
            "single_field_mirror_payload_bytes": 0,
            "single_field_mirror_passed_to_kernel": False,
            "single_field_mirror_changes_kernel_launch_args": False,
            "single_field_mirror_kernel_side_typed_consumer_compatible": True,
            "single_field_mirror_current_wna16_arg_compatible": False,
        }
        for key, expected_value in expected_mirror.items():
            if evidence.get(key) != expected_value:
                failures.append(f"native_typed_consumer_stub_{key}_mismatch")
        mirror_row_count = _int_metric(evidence, "single_field_mirror_row_count")
        mirror_row_ok_count = _int_metric(
            evidence,
            "single_field_mirror_row_ok_count",
        )
        mirror_error_count = _int_metric(
            evidence,
            "single_field_mirror_error_count",
        )
        if row_count is not None and mirror_row_count != row_count:
            failures.append(
                "native_typed_consumer_stub_single_field_mirror_row_count_mismatch"
            )
        if row_count is not None and mirror_row_ok_count != row_count:
            failures.append(
                "native_typed_consumer_stub_single_field_mirror_row_ok_count_mismatch"
            )
        if mirror_error_count != 0:
            failures.append(
                "native_typed_consumer_stub_single_field_mirror_error_count_mismatch"
            )
        mirror_hash = evidence.get("single_field_mirror_hash_accumulator")
        if not isinstance(mirror_hash, str) or not mirror_hash:
            failures.append(
                "native_typed_consumer_stub_single_field_mirror_hash_missing"
            )
    return failures


def _validate_future_native_dispatch_ptr_standalone_evidence(
    evidence: dict[str, Any],
    *,
    require_arg_slot: bool = False,
    require_arg_slot_handle_macro: bool = True,
    arg_slot_mirror_field: str = "scale_metadata_handle",
    expected_input_source: str = "synthetic",
    require_pointer_visibility_macro: bool = True,
    failure_prefix: str = "standalone_dispatch_ptr",
) -> list[str]:
    failures: list[str] = []
    row_count = _int_metric(evidence, "row_count")
    if row_count is None or row_count <= 0:
        failures.append(f"{failure_prefix}_row_count_invalid")
    expected_values = {
        "passed": True,
        "ok": True,
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "input_source": expected_input_source,
        "expected_schema_hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
        "future_kernel_native_consumer_checked": True,
        "future_kernel_native_consumer_error_count": 0,
        "future_kernel_native_consumer_payload_bytes": 0,
        "future_kernel_native_consumer_passed_to_kernel": False,
        "future_kernel_native_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_launch_consumer_checked": True,
        "future_kernel_native_launch_consumer_error_count": 0,
        "future_kernel_native_launch_consumer_payload_bytes": 0,
        "future_kernel_native_launch_consumer_passed_to_kernel": False,
        "future_kernel_native_launch_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_launch_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_dispatch_consumer_checked": True,
        "future_kernel_native_dispatch_consumer_error_count": 0,
        "future_kernel_native_dispatch_consumer_payload_bytes": 0,
        "future_kernel_native_dispatch_consumer_passed_to_kernel": False,
        "future_kernel_native_dispatch_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_dispatch_ptr_consumer_checked": True,
        "future_kernel_native_dispatch_ptr_consumer_error_count": 0,
        "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
        "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
        "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth": 2,
        "future_kernel_native_dispatch_ptr_consumer_payload_bytes": 0,
        "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel": False,
        "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible": False,
    }
    for key, expected_value in expected_values.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    row_count_keys = (
        "row_ok_count",
        "future_kernel_native_consumer_row_count",
        "future_kernel_native_consumer_row_ok_count",
        "future_kernel_native_launch_consumer_row_count",
        "future_kernel_native_launch_consumer_row_ok_count",
        "future_kernel_native_dispatch_consumer_row_count",
        "future_kernel_native_dispatch_consumer_row_ok_count",
        "future_kernel_native_dispatch_consumer_active_rows",
        "future_kernel_native_dispatch_consumer_row_limit",
        "future_kernel_native_dispatch_ptr_consumer_row_count",
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
    )
    if row_count is not None:
        for key in row_count_keys:
            if _int_metric(evidence, key) != row_count:
                failures.append(f"{failure_prefix}_{key}_mismatch")
    if _int_metric(evidence, "future_kernel_native_dispatch_consumer_row_offset") != 0:
        failures.append(f"{failure_prefix}_dispatch_row_offset_mismatch")
    if (
        _int_metric(evidence, "future_kernel_native_dispatch_ptr_consumer_packet_struct_size")
        != FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_dispatch_ptr_consumer_packet_struct_size"
        ]
    ):
        failures.append(f"{failure_prefix}_packet_struct_size_mismatch")
    if (
        _int_metric(evidence, "future_kernel_native_dispatch_ptr_consumer_dispatch_struct_size")
        != FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_dispatch_ptr_consumer_dispatch_struct_size"
        ]
    ):
        failures.append(f"{failure_prefix}_dispatch_struct_size_mismatch")
    if (
        _int_metric(evidence, "future_kernel_native_dispatch_ptr_consumer_result_struct_size")
        != FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_dispatch_ptr_consumer_result_struct_size"
        ]
    ):
        failures.append(f"{failure_prefix}_result_struct_size_mismatch")
    if require_arg_slot:
        mirror_macro_by_field = {
            "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
            "scale_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "packed_weight_descriptor": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
            "aux_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
        }
        arg_slot_mirror_macro = mirror_macro_by_field.get(arg_slot_mirror_field)
        if arg_slot_mirror_macro is None:
            failures.append(f"{failure_prefix}_arg_slot_mirror_field_unknown")
            arg_slot_mirror_macro = ""
        expected_arg_slot = {
            "future_kernel_native_arg_slot_consumer_checked": True,
            "future_kernel_native_arg_slot_consumer_error_count": 0,
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
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": arg_slot_mirror_field,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count": 0,
        }
        for key, expected_value in expected_arg_slot.items():
            if evidence.get(key) != expected_value:
                failures.append(f"{failure_prefix}_{key}_mismatch")
        for key in (
            "future_kernel_native_arg_slot_consumer_row_count",
            "future_kernel_native_arg_slot_consumer_row_ok_count",
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
        ):
            if row_count is not None and _int_metric(evidence, key) != row_count:
                failures.append(f"{failure_prefix}_{key}_mismatch")
        for (
            key,
            expected_value,
        ) in FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED.items():
            if _int_metric(evidence, key) != expected_value:
                failures.append(f"{failure_prefix}_{key}_mismatch")
    macros = evidence.get("compiled_macros")
    if not isinstance(macros, dict):
        failures.append(f"{failure_prefix}_compiled_macros_missing")
        macros = {}
    always_required_enabled = (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    )
    if require_pointer_visibility_macro:
        always_required_enabled = (
            *always_required_enabled,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
        )
    field_macro_by_field = {
        "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
        "scale_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
        "packed_weight_descriptor": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
        "aux_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    }
    required_enabled = tuple(always_required_enabled)
    if require_arg_slot:
        arg_slot_field_macro = field_macro_by_field.get(arg_slot_mirror_field)
        if arg_slot_field_macro is None:
            failures.append(f"{failure_prefix}_arg_slot_field_macro_unknown")
            arg_slot_field_macro = ""
        required_enabled = (
            *required_enabled,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
            arg_slot_mirror_macro,
        )
        if require_arg_slot_handle_macro:
            required_enabled = (*required_enabled, arg_slot_field_macro)
    else:
        required_enabled = (
            *required_enabled,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
        )
    for macro in required_enabled:
        if macros.get(macro) is not True:
            failures.append(f"{failure_prefix}_{macro}_not_enabled")
    if require_arg_slot:
        for forbidden_mirror in (
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
        ):
            if forbidden_mirror == arg_slot_mirror_macro:
                continue
            if macros.get(forbidden_mirror):
                failures.append(f"{failure_prefix}_{forbidden_mirror}_enabled")
    for forbidden in (
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
    ):
        if macros.get(forbidden):
            failures.append(f"{failure_prefix}_{forbidden}_enabled")
    return failures


def _validate_payload_cache_producer_state_native_canary_evidence(
    evidence: dict[str, Any],
    *,
    failure_prefix: str = "payload_cache_producer_state_native_canary",
    require_online_export: bool = True,
    require_nonempty_issue: bool = False,
    require_summary_first_nonempty_issue: bool = False,
) -> list[str]:
    failures: list[str] = []
    expected_values = {
        "ok": True,
        "passed": True,
        "failures": [],
        "mode": "readonly_payload_cache_producer_transition_state_native_canary",
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "abi_field_count": 9,
        "checked": True,
        "ready": True,
        "input_source": "semantic_packet_json",
        "packet_ready": True,
        "native_stub_invoked": True,
        "native_returncode": 0,
        "payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "error_count": 0,
    }
    if require_online_export:
        expected_values.update(
            {
                "online_export_source": (
                    "runtime_shadow_premap_payload_cache_producer_state_packet_export"
                ),
                "online_configured_export_enabled": True,
            }
        )
    for key, expected_value in expected_values.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")

    previous_count = _int_metric(evidence, "previous_count")
    current_count = _int_metric(evidence, "current_count")
    previous_valid_count = _int_metric(evidence, "previous_valid_count")
    current_valid_count = _int_metric(evidence, "current_valid_count")
    previous_nonempty = _int_metric(evidence, "previous_nonempty")
    current_nonempty = _int_metric(evidence, "current_nonempty")
    overlap_count = _int_metric(evidence, "overlap_count")
    issue_candidate_count = _int_metric(evidence, "issue_candidate_count")
    issue_candidate_first_expert = _int_metric(
        evidence,
        "issue_candidate_first_expert",
    )
    issue_candidate_last_expert = _int_metric(
        evidence,
        "issue_candidate_last_expert",
    )
    expected_issue_candidate_count = _int_metric(
        evidence,
        "expected_issue_candidate_count",
    )
    expected_issue_candidate_first_expert = _int_metric(
        evidence,
        "expected_issue_candidate_first_expert",
    )
    expected_issue_candidate_last_expert = _int_metric(
        evidence,
        "expected_issue_candidate_last_expert",
    )
    transition_topk_count = _int_metric(evidence, "transition_topk_count")
    requested_previous_count = _int_metric(evidence, "requested_previous_count")
    requested_current_count = _int_metric(evidence, "requested_current_count")
    requested_transition_topk_count = _int_metric(
        evidence,
        "requested_transition_topk_count",
    )
    requested_current_offset = _int_metric(evidence, "requested_current_offset")
    layer_id = _int_metric(evidence, "layer_id")
    requested_layer_id = _int_metric(evidence, "requested_layer_id")
    packet_layer_id = _int_metric(evidence, "packet_layer_id")
    online_packet_export_count = (
        _int_metric(evidence, "online_packet_export_count")
        if require_online_export
        else None
    )
    online_configured_export_count = (
        _int_metric(evidence, "online_configured_export_count")
        if require_online_export
        else None
    )
    selected_packet_index = (
        _int_metric(evidence, "selected_packet_index")
        if require_online_export
        else None
    )
    online_packet_export_nonempty_issue_count = (
        _int_metric(evidence, "online_packet_export_nonempty_issue_count")
        if require_summary_first_nonempty_issue
        else None
    )
    online_packet_export_first_nonempty_issue_index = (
        _int_metric(evidence, "online_packet_export_first_nonempty_issue_index")
        if require_summary_first_nonempty_issue
        else None
    )
    online_packet_export_first_nonempty_issue_count = (
        _int_metric(evidence, "online_packet_export_first_nonempty_issue_count")
        if require_summary_first_nonempty_issue
        else None
    )
    online_packet_export_scan_error_count = (
        _int_metric(evidence, "online_packet_export_scan_error_count")
        if require_summary_first_nonempty_issue
        else None
    )

    for key, value in (
        ("previous_count", previous_count),
        ("current_count", current_count),
        ("previous_valid_count", previous_valid_count),
        ("current_valid_count", current_valid_count),
        ("previous_nonempty", previous_nonempty),
        ("current_nonempty", current_nonempty),
        ("overlap_count", overlap_count),
        ("issue_candidate_count", issue_candidate_count),
        ("expected_issue_candidate_count", expected_issue_candidate_count),
        ("transition_topk_count", transition_topk_count),
        ("requested_previous_count", requested_previous_count),
        ("requested_current_count", requested_current_count),
        ("requested_transition_topk_count", requested_transition_topk_count),
        ("requested_current_offset", requested_current_offset),
        ("layer_id", layer_id),
        ("requested_layer_id", requested_layer_id),
        ("packet_layer_id", packet_layer_id),
    ):
        if value is None or value < 0:
            failures.append(f"{failure_prefix}_{key}_invalid")
    if require_online_export:
        for key, value in (
            ("online_packet_export_count", online_packet_export_count),
            ("online_configured_export_count", online_configured_export_count),
            ("selected_packet_index", selected_packet_index),
        ):
            if value is None or value < 0:
                failures.append(f"{failure_prefix}_{key}_invalid")
        if online_packet_export_count is not None and online_packet_export_count <= 0:
            failures.append(f"{failure_prefix}_online_packet_export_count_empty")
        if (
            online_configured_export_count is not None
            and online_configured_export_count <= 0
        ):
            failures.append(f"{failure_prefix}_online_configured_export_count_empty")
        if (
            selected_packet_index is not None
            and online_packet_export_count is not None
            and selected_packet_index >= online_packet_export_count
        ):
            failures.append(f"{failure_prefix}_selected_packet_index_out_of_range")
    if require_summary_first_nonempty_issue:
        if evidence.get("selected_packet_selection_mode") != (
            "summary_first_nonempty_issue"
        ):
            failures.append(f"{failure_prefix}_selected_packet_selection_mode_mismatch")
        for key, value in (
            (
                "online_packet_export_nonempty_issue_count",
                online_packet_export_nonempty_issue_count,
            ),
            (
                "online_packet_export_first_nonempty_issue_index",
                online_packet_export_first_nonempty_issue_index,
            ),
            (
                "online_packet_export_first_nonempty_issue_count",
                online_packet_export_first_nonempty_issue_count,
            ),
            (
                "online_packet_export_scan_error_count",
                online_packet_export_scan_error_count,
            ),
        ):
            if value is None or value < 0:
                failures.append(f"{failure_prefix}_{key}_invalid")
        if (
            online_packet_export_nonempty_issue_count is not None
            and online_packet_export_nonempty_issue_count <= 0
        ):
            failures.append(
                f"{failure_prefix}_online_packet_export_nonempty_issue_count_empty"
            )
        if (
            online_packet_export_scan_error_count is not None
            and online_packet_export_scan_error_count != 0
        ):
            failures.append(
                f"{failure_prefix}_online_packet_export_scan_error_count_nonzero"
            )
        if (
            online_packet_export_first_nonempty_issue_index is not None
            and selected_packet_index is not None
            and online_packet_export_first_nonempty_issue_index != selected_packet_index
        ):
            failures.append(
                f"{failure_prefix}_online_packet_export_first_nonempty_issue_index_mismatch"
            )
        if (
            online_packet_export_first_nonempty_issue_count is not None
            and issue_candidate_count is not None
            and online_packet_export_first_nonempty_issue_count
            != issue_candidate_count
        ):
            failures.append(
                f"{failure_prefix}_online_packet_export_first_nonempty_issue_count_mismatch"
            )

    if (
        previous_count is not None
        and previous_valid_count is not None
        and previous_valid_count != previous_count
    ):
        failures.append(f"{failure_prefix}_previous_valid_count_mismatch")
    if (
        current_count is not None
        and current_valid_count is not None
        and current_valid_count != current_count
    ):
        failures.append(f"{failure_prefix}_current_valid_count_mismatch")
    if (
        previous_nonempty is not None
        and previous_count is not None
        and previous_nonempty > previous_count
    ):
        failures.append(f"{failure_prefix}_previous_nonempty_overflow")
    if (
        current_nonempty is not None
        and current_count is not None
        and current_nonempty > current_count
    ):
        failures.append(f"{failure_prefix}_current_nonempty_overflow")
    if (
        overlap_count is not None
        and previous_count is not None
        and current_count is not None
        and overlap_count > min(previous_count, current_count)
    ):
        failures.append(f"{failure_prefix}_overlap_count_overflow")
    if (
        issue_candidate_count is not None
        and previous_count is not None
        and issue_candidate_count > previous_count
    ):
        failures.append(f"{failure_prefix}_issue_candidate_count_overflow")
    if (
        issue_candidate_count is not None
        and transition_topk_count is not None
        and transition_topk_count > 0
        and issue_candidate_count > transition_topk_count
    ):
        failures.append(f"{failure_prefix}_issue_candidate_count_over_topk")
    if (
        issue_candidate_count is not None
        and expected_issue_candidate_count is not None
        and issue_candidate_count != expected_issue_candidate_count
    ):
        failures.append(f"{failure_prefix}_issue_candidate_count_mismatch")
    issue_prefix_bound_metrics = (
        ("issue_candidate_first_expert", issue_candidate_first_expert),
        ("issue_candidate_last_expert", issue_candidate_last_expert),
        (
            "expected_issue_candidate_first_expert",
            expected_issue_candidate_first_expert,
        ),
        (
            "expected_issue_candidate_last_expert",
            expected_issue_candidate_last_expert,
        ),
    )
    for key, value in issue_prefix_bound_metrics:
        if value is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    if issue_candidate_count is not None and issue_candidate_count <= 0:
        for key, value in issue_prefix_bound_metrics:
            if value is not None and value != -1:
                failures.append(f"{failure_prefix}_{key}_nonempty_for_empty_issue")
    elif issue_candidate_count is not None:
        for key, value in issue_prefix_bound_metrics:
            if value is not None and value < 0:
                failures.append(f"{failure_prefix}_{key}_negative_for_nonempty_issue")
    if (
        issue_candidate_first_expert is not None
        and expected_issue_candidate_first_expert is not None
        and issue_candidate_first_expert != expected_issue_candidate_first_expert
    ):
        failures.append(f"{failure_prefix}_issue_candidate_first_expert_mismatch")
    if (
        issue_candidate_last_expert is not None
        and expected_issue_candidate_last_expert is not None
        and issue_candidate_last_expert != expected_issue_candidate_last_expert
    ):
        failures.append(f"{failure_prefix}_issue_candidate_last_expert_mismatch")
    if require_nonempty_issue:
        if previous_count is not None and previous_count <= 0:
            failures.append(f"{failure_prefix}_previous_count_empty")
        if issue_candidate_count is not None and issue_candidate_count <= 0:
            failures.append(f"{failure_prefix}_issue_candidate_count_empty")
    issue_candidate_hash = _hex64_metric(evidence, "issue_candidate_hash")
    expected_issue_candidate_hash = _hex64_metric(
        evidence,
        "expected_issue_candidate_hash",
    )
    if issue_candidate_hash is None:
        failures.append(f"{failure_prefix}_issue_candidate_hash_invalid")
    if expected_issue_candidate_hash is None:
        failures.append(f"{failure_prefix}_expected_issue_candidate_hash_invalid")
    if (
        issue_candidate_hash is not None
        and expected_issue_candidate_hash is not None
        and issue_candidate_hash != expected_issue_candidate_hash
    ):
        failures.append(f"{failure_prefix}_issue_candidate_hash_mismatch")
    if (
        requested_previous_count is not None
        and previous_count is not None
        and requested_previous_count != previous_count
    ):
        failures.append(f"{failure_prefix}_requested_previous_count_mismatch")
    if (
        requested_current_count is not None
        and current_count is not None
        and requested_current_count != current_count
    ):
        failures.append(f"{failure_prefix}_requested_current_count_mismatch")
    if (
        requested_transition_topk_count is not None
        and transition_topk_count is not None
        and requested_transition_topk_count != transition_topk_count
    ):
        failures.append(f"{failure_prefix}_requested_transition_topk_count_mismatch")
    if (
        layer_id is not None
        and requested_layer_id is not None
        and layer_id != requested_layer_id
    ):
        failures.append(f"{failure_prefix}_requested_layer_id_mismatch")
    if (
        packet_layer_id is not None
        and requested_layer_id is not None
        and packet_layer_id != requested_layer_id
    ):
        failures.append(f"{failure_prefix}_packet_layer_id_mismatch")
    if (
        packet_layer_id is not None
        and layer_id is not None
        and packet_layer_id != layer_id
    ):
        failures.append(f"{failure_prefix}_layer_id_packet_mismatch")
    state_hash = _hex64_metric(evidence, "state_hash")
    if state_hash is None:
        failures.append(f"{failure_prefix}_state_hash_invalid")
    packet_state_hash = evidence.get("packet_state_hash")
    packet_state_hash_valid = isinstance(packet_state_hash, str) and (
        len(packet_state_hash) == 64
    ) and all(char in "0123456789abcdefABCDEF" for char in packet_state_hash)
    if (
        not packet_state_hash_valid
    ):
        failures.append(f"{failure_prefix}_packet_state_hash_invalid")
    elif state_hash is not None and state_hash != int(packet_state_hash[:16], 16):
        failures.append(f"{failure_prefix}_state_hash_packet_mismatch")
    packet_json = evidence.get("packet_json")
    if not isinstance(packet_json, str) or not packet_json:
        failures.append(f"{failure_prefix}_packet_json_missing")
    if require_online_export:
        selected_packet_json = evidence.get("selected_packet_json")
        if not isinstance(selected_packet_json, str) or not selected_packet_json:
            failures.append(f"{failure_prefix}_selected_packet_json_missing")
        elif (
            isinstance(packet_json, str)
            and packet_json
            and selected_packet_json != packet_json
        ):
            failures.append(f"{failure_prefix}_selected_packet_json_mismatch")
        online_paths = evidence.get("online_packet_export_paths")
        if not isinstance(online_paths, list) or not online_paths:
            failures.append(f"{failure_prefix}_online_packet_export_paths_missing")
        else:
            online_path_strings = {str(path) for path in online_paths}
            if (
                online_packet_export_count is not None
                and online_packet_export_count != len(online_paths)
            ):
                failures.append(
                    f"{failure_prefix}_online_packet_export_paths_count_mismatch"
                )
            if (
                online_configured_export_count is not None
                and online_configured_export_count != len(online_paths)
            ):
                failures.append(
                    f"{failure_prefix}_online_configured_export_paths_count_mismatch"
                )
            if (
                selected_packet_index is not None
                and selected_packet_index >= len(online_paths)
            ):
                failures.append(
                    f"{failure_prefix}_selected_packet_index_paths_out_of_range"
                )
            elif (
                isinstance(packet_json, str)
                and packet_json
                and selected_packet_index is not None
                and selected_packet_index >= 0
                and str(online_paths[selected_packet_index]) != packet_json
            ):
                failures.append(f"{failure_prefix}_selected_packet_index_path_mismatch")
            if isinstance(packet_json, str) and packet_json not in online_path_strings:
                failures.append(f"{failure_prefix}_packet_json_not_in_online_paths")
    if require_summary_first_nonempty_issue:
        first_nonempty_path = evidence.get(
            "online_packet_export_first_nonempty_issue_path"
        )
        if not isinstance(first_nonempty_path, str) or not first_nonempty_path:
            failures.append(
                f"{failure_prefix}_online_packet_export_first_nonempty_issue_path_missing"
            )
        elif isinstance(packet_json, str) and packet_json and first_nonempty_path != packet_json:
            failures.append(
                f"{failure_prefix}_online_packet_export_first_nonempty_issue_path_mismatch"
            )
        first_nonempty_hash = _hex64_metric(
            evidence,
            "online_packet_export_first_nonempty_issue_hash",
        )
        if first_nonempty_hash is None:
            failures.append(
                f"{failure_prefix}_online_packet_export_first_nonempty_issue_hash_invalid"
            )
        elif (
            issue_candidate_hash is not None
            and first_nonempty_hash != issue_candidate_hash
        ):
            failures.append(
                f"{failure_prefix}_online_packet_export_first_nonempty_issue_hash_mismatch"
            )
    return failures


def _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence(
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    failure_prefix = "payload_cache_shifted_issue_runtime_shadow_gate"
    expected_scalar_values = {
        "artifact_kind": "premap_payload_cache_shifted_issue_runtime_shadow_gate",
        "failures": [],
    }
    for key, expected_value in expected_scalar_values.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if evidence.get("passed") is not True:
        failures.append(f"{failure_prefix}_passed_mismatch")

    if _int_metric(evidence, "payload_bytes") != 0:
        failures.append(f"{failure_prefix}_payload_bytes_mismatch")
    expected_false_flags = (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "full_fetch_runtime_allowed",
        "measures_tpot",
        "measures_vllm_latency",
    )
    for key in expected_false_flags:
        if evidence.get(key) is not False:
            failures.append(f"{failure_prefix}_{key}_mismatch")

    count_keys = (
        "issue_lead_tokens",
        "packet_count",
        "schedulable_packet_count",
        "empty_issue_exempt_count",
        "safe_packet_count",
        "unsafe_packet_count",
        "invalid_packet_count",
        "scan_error_count",
        "clamped_issue_count",
        "duplicate_demand_key_count",
        "duplicate_issue_key_count",
        "unique_demand_key_count",
        "unique_issue_key_count",
        "issue_hash_count",
        "issue_hash_unique_count",
        "total_issue_candidates",
    )
    counts: dict[str, int | None] = {}
    for key in count_keys:
        value = _int_metric(evidence, key)
        counts[key] = value
        if value is None:
            failures.append(f"{failure_prefix}_{key}_missing_or_not_int")

    packet_count = counts.get("packet_count")
    schedulable_packet_count = counts.get("schedulable_packet_count")
    empty_issue_exempt_count = counts.get("empty_issue_exempt_count")
    safe_packet_count = counts.get("safe_packet_count")
    unique_demand_key_count = counts.get("unique_demand_key_count")
    unique_issue_key_count = counts.get("unique_issue_key_count")
    issue_hash_count = counts.get("issue_hash_count")
    issue_hash_unique_count = counts.get("issue_hash_unique_count")
    total_issue_candidates = counts.get("total_issue_candidates")

    if counts.get("issue_lead_tokens") != 1:
        failures.append(f"{failure_prefix}_issue_lead_tokens_mismatch")
    if packet_count is not None and packet_count < 32:
        failures.append(f"{failure_prefix}_packet_count_too_small")
    if schedulable_packet_count is not None and schedulable_packet_count < 28:
        failures.append(f"{failure_prefix}_schedulable_packet_count_too_small")
    if (
        packet_count is not None
        and schedulable_packet_count is not None
        and empty_issue_exempt_count is not None
        and schedulable_packet_count + empty_issue_exempt_count != packet_count
    ):
        failures.append(f"{failure_prefix}_schedulable_plus_empty_exempt_mismatch")
    if (
        safe_packet_count is not None
        and packet_count is not None
        and safe_packet_count != packet_count
    ):
        failures.append(f"{failure_prefix}_safe_packet_count_mismatch")
    for key in (
        "unsafe_packet_count",
        "invalid_packet_count",
        "scan_error_count",
        "clamped_issue_count",
        "duplicate_demand_key_count",
        "duplicate_issue_key_count",
    ):
        if counts.get(key) != 0:
            failures.append(f"{failure_prefix}_{key}_nonzero")
    if (
        unique_demand_key_count is not None
        and schedulable_packet_count is not None
        and unique_demand_key_count != schedulable_packet_count
    ):
        failures.append(f"{failure_prefix}_unique_demand_key_count_mismatch")
    if (
        unique_issue_key_count is not None
        and schedulable_packet_count is not None
        and unique_issue_key_count != schedulable_packet_count
    ):
        failures.append(f"{failure_prefix}_unique_issue_key_count_mismatch")
    if (
        issue_hash_count is not None
        and schedulable_packet_count is not None
        and issue_hash_count != schedulable_packet_count
    ):
        failures.append(f"{failure_prefix}_issue_hash_count_mismatch")
    if (
        issue_hash_unique_count is not None
        and issue_hash_count is not None
        and issue_hash_unique_count <= 0
    ):
        failures.append(f"{failure_prefix}_issue_hash_unique_count_nonpositive")
    if (
        issue_hash_unique_count is not None
        and issue_hash_count is not None
        and issue_hash_unique_count > issue_hash_count
    ):
        failures.append(f"{failure_prefix}_issue_hash_unique_count_too_large")
    if (
        total_issue_candidates is not None
        and schedulable_packet_count is not None
        and total_issue_candidates < schedulable_packet_count
    ):
        failures.append(f"{failure_prefix}_total_issue_candidates_too_small")

    if not isinstance(evidence.get("performance_summary"), str):
        failures.append(f"{failure_prefix}_performance_summary_missing")

    return failures


def _validate_payload_cache_packet_export_manifest_evidence(
    evidence: dict[str, Any],
    *,
    root: Path | None = None,
) -> list[str]:
    failures: list[str] = []
    failure_prefix = "payload_cache_packet_export_manifest"
    expected_scalar_values = {
        "artifact_kind": "premap_payload_cache_packet_export_manifest",
        "manifest_name": "premap_payload_cache_packet_export_manifest_v1",
        "manifest_source": "runtime_shadow_performance_summary",
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "failures": [],
        "allow_empty_config_packets": True,
        "allow_config_token_source": False,
        "shifted_issue_runtime_shadow_required": True,
        "shifted_issue_runtime_shadow_enabled": True,
        "shifted_issue_enabled": True,
    }
    for key, expected_value in expected_scalar_values.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    for key in ("ok", "ready", "passed"):
        if evidence.get(key) is not True:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if evidence.get("next_runtime_stage") != "payload_cache_issue_stream_executor":
        failures.append(f"{failure_prefix}_next_runtime_stage_mismatch")

    expected_false_flags = (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    )
    for key in expected_false_flags:
        if evidence.get(key) is not False:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if _int_metric(evidence, "payload_bytes") != 0:
        failures.append(f"{failure_prefix}_payload_bytes_mismatch")

    count_keys = (
        "online_packet_export_count",
        "online_configured_export_count",
        "online_packet_export_nonempty_issue_count",
        "online_packet_export_scan_error_count",
        "online_nonempty_issue_count",
        "checked_packet_count",
        "checked_nonempty_packet_count",
        "shifted_issue_packet_count",
        "shifted_issue_schedulable_packet_count",
        "shifted_issue_empty_issue_exempt_count",
        "shifted_issue_safe_packet_count",
        "shifted_issue_unsafe_packet_count",
        "shifted_issue_invalid_packet_count",
        "shifted_issue_scan_error_count",
        "shifted_issue_clamped_issue_count",
        "shifted_issue_duplicate_demand_key_count",
        "shifted_issue_duplicate_issue_key_count",
        "shifted_issue_unique_demand_key_count",
        "shifted_issue_unique_issue_key_count",
        "shifted_issue_total_issue_candidates",
        "shifted_issue_issue_hash_count",
        "shifted_issue_issue_hash_unique_count",
        "shifted_issue_lead_tokens",
    )
    counts: dict[str, int | None] = {}
    for key in count_keys:
        value = _int_metric(evidence, key)
        counts[key] = value
        if value is None:
            failures.append(f"{failure_prefix}_{key}_missing_or_not_int")

    online_count = counts.get("online_packet_export_count")
    online_scan_error_count = counts.get("online_packet_export_scan_error_count")
    configured_count = counts.get("online_configured_export_count")
    checked_count = counts.get("checked_packet_count")
    online_nonempty = counts.get("online_nonempty_issue_count")
    export_nonempty = counts.get("online_packet_export_nonempty_issue_count")
    checked_nonempty = counts.get("checked_nonempty_packet_count")
    shifted_packet_count = counts.get("shifted_issue_packet_count")
    shifted_schedulable = counts.get("shifted_issue_schedulable_packet_count")
    shifted_empty = counts.get("shifted_issue_empty_issue_exempt_count")
    shifted_safe = counts.get("shifted_issue_safe_packet_count")
    shifted_unique_demand = counts.get("shifted_issue_unique_demand_key_count")
    shifted_unique_issue = counts.get("shifted_issue_unique_issue_key_count")
    shifted_hash_count = counts.get("shifted_issue_issue_hash_count")
    shifted_hash_unique = counts.get("shifted_issue_issue_hash_unique_count")
    shifted_total_candidates = counts.get("shifted_issue_total_issue_candidates")

    if online_count is not None and online_count < 32:
        failures.append(f"{failure_prefix}_online_packet_export_count_too_small")
    if online_scan_error_count != 0:
        failures.append(f"{failure_prefix}_online_packet_export_scan_error_count_nonzero")
    if checked_count is not None and checked_count != online_count:
        failures.append(f"{failure_prefix}_checked_packet_count_mismatch")
    if configured_count is not None and configured_count != online_count:
        failures.append(f"{failure_prefix}_configured_packet_count_mismatch")
    if shifted_packet_count is not None and shifted_packet_count != online_count:
        failures.append(f"{failure_prefix}_shifted_packet_count_mismatch")
    if checked_nonempty is not None and checked_nonempty < 28:
        failures.append(f"{failure_prefix}_checked_nonempty_packet_count_too_small")
    if online_nonempty is not None and checked_nonempty != online_nonempty:
        failures.append(f"{failure_prefix}_online_nonempty_count_mismatch")
    if export_nonempty is not None and checked_nonempty != export_nonempty:
        failures.append(f"{failure_prefix}_export_nonempty_count_mismatch")
    if shifted_schedulable is not None and checked_nonempty != shifted_schedulable:
        failures.append(f"{failure_prefix}_shifted_schedulable_count_mismatch")
    if (
        shifted_schedulable is not None
        and shifted_empty is not None
        and shifted_packet_count is not None
        and shifted_schedulable + shifted_empty != shifted_packet_count
    ):
        failures.append(f"{failure_prefix}_shifted_accounting_mismatch")
    if shifted_safe is not None and shifted_packet_count is not None:
        if shifted_safe != shifted_packet_count:
            failures.append(f"{failure_prefix}_shifted_safe_packet_count_mismatch")
    for key in (
        "shifted_issue_unsafe_packet_count",
        "shifted_issue_invalid_packet_count",
        "shifted_issue_scan_error_count",
        "shifted_issue_clamped_issue_count",
        "shifted_issue_duplicate_demand_key_count",
        "shifted_issue_duplicate_issue_key_count",
    ):
        if counts.get(key) != 0:
            failures.append(f"{failure_prefix}_{key}_nonzero")
    if shifted_unique_demand is not None and shifted_unique_demand != shifted_schedulable:
        failures.append(f"{failure_prefix}_shifted_unique_demand_key_count_mismatch")
    if shifted_unique_issue is not None and shifted_unique_issue != shifted_schedulable:
        failures.append(f"{failure_prefix}_shifted_unique_issue_key_count_mismatch")
    if shifted_hash_count is not None and shifted_hash_count != shifted_schedulable:
        failures.append(f"{failure_prefix}_shifted_issue_hash_count_mismatch")
    if (
        shifted_hash_unique is not None
        and shifted_hash_count is not None
        and not (0 < shifted_hash_unique <= shifted_hash_count)
    ):
        failures.append(f"{failure_prefix}_shifted_issue_hash_unique_count_mismatch")
    if (
        shifted_total_candidates is not None
        and shifted_schedulable is not None
        and shifted_total_candidates < shifted_schedulable
    ):
        failures.append(f"{failure_prefix}_shifted_total_issue_candidates_too_small")
    if counts.get("shifted_issue_lead_tokens") != 1:
        failures.append(f"{failure_prefix}_shifted_issue_lead_tokens_mismatch")

    paths = evidence.get("online_packet_export_paths")
    if not isinstance(paths, list):
        failures.append(f"{failure_prefix}_online_packet_export_paths_missing")
    elif online_count is not None and len(paths) != online_count:
        failures.append(f"{failure_prefix}_online_packet_export_paths_count_mismatch")
    elif any(not isinstance(path, str) or not path for path in paths):
        failures.append(f"{failure_prefix}_online_packet_export_path_invalid")
    elif root is not None:
        resolved_root = root.resolve()
        for index, raw_path in enumerate(paths):
            resolved_path = _path_for_label(raw_path, root).resolve(strict=False)
            if not resolved_path.is_relative_to(resolved_root):
                failures.append(
                    f"{failure_prefix}_online_packet_export_path_{index}_outside_root"
                )
                continue
            if not resolved_path.is_file():
                failures.append(f"{failure_prefix}_online_packet_export_path_{index}_missing")

    summary_first_prefix = "summary_packet_export_first_nonempty_issue_"
    checked_first_prefix = "checked_packet_export_first_nonempty_issue_"
    online_first_prefix = "online_packet_export_first_nonempty_issue_"
    for suffix in ("index", "path", "count", "hash"):
        summary_value = evidence.get(f"{summary_first_prefix}{suffix}")
        checked_value = evidence.get(f"{checked_first_prefix}{suffix}")
        online_value = evidence.get(f"{online_first_prefix}{suffix}")
        if summary_value != checked_value:
            failures.append(f"{failure_prefix}_first_nonempty_{suffix}_mismatch")
        if online_value != checked_value:
            failures.append(f"{failure_prefix}_online_first_nonempty_{suffix}_mismatch")
    first_index = _int_metric(evidence, "checked_packet_export_first_nonempty_issue_index")
    first_count = _int_metric(evidence, "checked_packet_export_first_nonempty_issue_count")
    if first_index is None or first_index < 0:
        failures.append(f"{failure_prefix}_checked_first_nonempty_index_invalid")
    if first_count is None or first_count <= 0:
        failures.append(f"{failure_prefix}_checked_first_nonempty_count_invalid")
    first_path = evidence.get("checked_packet_export_first_nonempty_issue_path")
    if isinstance(paths, list) and first_index is not None and first_index >= 0:
        if first_index >= len(paths):
            failures.append(f"{failure_prefix}_checked_first_nonempty_index_out_of_range")
        elif first_path != paths[first_index]:
            failures.append(f"{failure_prefix}_checked_first_nonempty_path_index_mismatch")
    for key in (
        "checked_packet_export_first_nonempty_issue_path",
        "checked_packet_export_first_nonempty_issue_hash",
        "online_performance_summary",
    ):
        value = evidence.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{failure_prefix}_{key}_missing")

    return failures


def _validate_future_native_arg_slot_multiprogram_evidence(
    evidence: dict[str, Any],
    *,
    expected_input_source: str = "synthetic",
    require_pointer_visibility_macro: bool = True,
    arg_slot_mirror_field: str = "scale_metadata_handle",
) -> list[str]:
    failure_prefix = "multiprogram_arg_slot"
    failures = _validate_future_native_dispatch_ptr_standalone_evidence(
        evidence,
        require_arg_slot=True,
        require_arg_slot_handle_macro=False,
        arg_slot_mirror_field=arg_slot_mirror_field,
        expected_input_source=expected_input_source,
        require_pointer_visibility_macro=require_pointer_visibility_macro,
        failure_prefix=failure_prefix,
    )
    row_count = _int_metric(evidence, "row_count")
    active_rows = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_active_rows"
    )
    grid_x = _int_metric(evidence, "future_kernel_native_dispatch_consumer_grid_x")
    block_x = _int_metric(evidence, "future_kernel_native_dispatch_consumer_block_x")
    program_count = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_program_count"
    )
    full_program_count = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_full_program_count"
    )
    last_program_active_rows = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_last_program_active_rows"
    )
    inactive_lane_count = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_inactive_lane_count"
    )
    launch_threads = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_launch_threads"
    )
    row_offset = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_row_offset"
    )
    row_limit = _int_metric(evidence, "future_kernel_native_dispatch_consumer_row_limit")
    first_program_row_offset = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_first_program_row_offset"
    )
    last_program_row_offset = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_last_program_row_offset"
    )
    rows_per_program = _int_metric(
        evidence, "future_kernel_native_dispatch_consumer_rows_per_program"
    )
    if grid_x is None or grid_x <= 1:
        failures.append(f"{failure_prefix}_grid_x_not_multiprogram")
    if program_count is None or program_count <= 1:
        failures.append(f"{failure_prefix}_program_count_not_multiprogram")
    if (
        grid_x is not None
        and program_count is not None
        and grid_x != program_count
    ):
        failures.append(f"{failure_prefix}_program_count_grid_x_mismatch")
    if block_x is None or block_x <= 0:
        failures.append(f"{failure_prefix}_block_x_invalid")
    if rows_per_program is None or rows_per_program <= 0:
        failures.append(f"{failure_prefix}_rows_per_program_invalid")
    elif block_x is not None and rows_per_program != block_x:
        failures.append(f"{failure_prefix}_rows_per_program_block_x_mismatch")
    if row_count is not None and rows_per_program is not None:
        if row_count <= rows_per_program:
            failures.append(f"{failure_prefix}_row_count_single_program")
    if active_rows is None or active_rows <= 0:
        failures.append(f"{failure_prefix}_active_rows_invalid")
    elif row_count is not None and active_rows != row_count:
        failures.append(f"{failure_prefix}_active_rows_mismatch")
    if row_offset is None or row_offset != 0:
        failures.append(f"{failure_prefix}_row_offset_mismatch")
    if row_limit is None or row_limit <= 0:
        failures.append(f"{failure_prefix}_row_limit_invalid")
    elif row_count is not None and row_limit != row_count:
        failures.append(f"{failure_prefix}_row_limit_mismatch")
    if (
        row_offset is not None
        and row_limit is not None
        and active_rows is not None
        and active_rows != row_limit - row_offset
    ):
        failures.append(f"{failure_prefix}_row_limit_active_rows_mismatch")
    if full_program_count is None or full_program_count <= 0:
        failures.append(f"{failure_prefix}_full_program_count_invalid")
    if last_program_active_rows is None or last_program_active_rows <= 0:
        failures.append(f"{failure_prefix}_last_program_active_rows_invalid")
    elif block_x is not None and last_program_active_rows >= block_x:
        failures.append(f"{failure_prefix}_last_program_active_rows_not_partial")
    if inactive_lane_count is None or inactive_lane_count <= 0:
        failures.append(f"{failure_prefix}_inactive_lane_count_invalid")
    if launch_threads is None:
        failures.append(f"{failure_prefix}_launch_threads_missing")
    elif (
        grid_x is not None
        and block_x is not None
        and launch_threads != grid_x * block_x
    ):
        failures.append(f"{failure_prefix}_launch_threads_mismatch")
    if (
        active_rows is not None
        and launch_threads is not None
        and launch_threads < active_rows
    ):
        failures.append(f"{failure_prefix}_launch_undercoverage")
    if (
        active_rows is not None
        and block_x is not None
        and launch_threads is not None
        and launch_threads - active_rows >= block_x
    ):
        failures.append(f"{failure_prefix}_launch_non_minimal")
    if active_rows is not None and block_x is not None and grid_x is not None:
        expected_full_program_count = active_rows // block_x
        previous_program_threads = (grid_x - 1) * block_x
        expected_last_program_active_rows = active_rows - previous_program_threads
        expected_inactive_lane_count = grid_x * block_x - active_rows
        expected_last_program_row_offset = previous_program_threads
        if full_program_count != expected_full_program_count:
            failures.append(f"{failure_prefix}_full_program_count_mismatch")
        if last_program_active_rows != expected_last_program_active_rows:
            failures.append(f"{failure_prefix}_last_program_active_rows_mismatch")
        if inactive_lane_count != expected_inactive_lane_count:
            failures.append(f"{failure_prefix}_inactive_lane_count_mismatch")
        if first_program_row_offset != 0:
            failures.append(f"{failure_prefix}_first_program_row_offset_mismatch")
        if last_program_row_offset != expected_last_program_row_offset:
            failures.append(f"{failure_prefix}_last_program_row_offset_mismatch")
    for key in (
        "future_kernel_native_dispatch_consumer_launch_geometry_checked",
        "future_kernel_native_dispatch_consumer_launch_covers_active_rows",
        "future_kernel_native_dispatch_consumer_launch_minimal_cover",
        "future_kernel_native_dispatch_consumer_program_iteration_checked",
    ):
        if evidence.get(key) is not True:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if (
        evidence.get("future_kernel_native_dispatch_consumer_row_assignment_formula")
        != REQUIRED_DEFAULT_GATE_CONTRACT.get(
            "future_kernel_native_dispatch_consumer_row_assignment_formula"
        )
    ):
        failures.append(f"{failure_prefix}_row_assignment_formula_mismatch")
    expected_program_iteration_hash: int | None = None
    if (
        grid_x is not None
        and block_x is not None
        and row_offset is not None
        and row_limit is not None
        and active_rows is not None
    ):
        expected_last_program_active_rows = active_rows - (grid_x - 1) * block_x
        expected_inactive_lane_count = grid_x * block_x - active_rows
        expected_program_iteration_hash = _program_iteration_hash(
            grid_x=grid_x,
            block_x=block_x,
            row_offset=row_offset,
            row_limit=row_limit,
            last_program_active_rows=expected_last_program_active_rows,
            inactive_lane_count=expected_inactive_lane_count,
        )
    actual_program_iteration_hash = _hex64_metric(
        evidence, "future_kernel_native_dispatch_consumer_program_iteration_hash"
    )
    if actual_program_iteration_hash is None:
        failures.append(f"{failure_prefix}_program_iteration_hash_missing")
    elif (
        expected_program_iteration_hash is not None
        and actual_program_iteration_hash != expected_program_iteration_hash
    ):
        failures.append(f"{failure_prefix}_program_iteration_hash_mismatch")
    projection_hashes = [
        _hex64_metric(
            evidence,
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator",
        ),
        _hex64_metric(
            evidence,
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator",
        ),
        _hex64_metric(
            evidence,
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
        ),
    ]
    consumer_view_projection_hash = _hex64_metric(
        evidence,
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    )
    if (
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
        in evidence
    ):
        projection_hashes.append(consumer_view_projection_hash)
    consumer_program_view_projection_hash = _hex64_metric(
        evidence,
        "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator",
    )
    if (
        "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator"
        in evidence
    ):
        projection_hashes.append(consumer_program_view_projection_hash)
    if any(value is None for value in projection_hashes):
        failures.append(f"{failure_prefix}_handle_projection_hash_missing")
    elif len(set(projection_hashes)) != 1:
        failures.append(f"{failure_prefix}_handle_projection_hash_mismatch")
    if evidence.get("future_kernel_native_consumer_program_view_checked") is True:
        program_view_expected = {
            "future_kernel_native_consumer_program_view_row_count": active_rows,
            "future_kernel_native_consumer_program_view_row_ok_count": active_rows,
            "future_kernel_native_consumer_program_view_error_count": 0,
            "future_kernel_native_consumer_program_view_program_count": grid_x,
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
                first_program_row_offset
            ),
            "future_kernel_native_consumer_program_view_last_program_row_offset": (
                last_program_row_offset
            ),
            "future_kernel_native_consumer_program_view_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_program_view_current_wna16_arg_compatible": (
                False
            ),
            "future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation": (
                False
            ),
        }
        for key, expected in program_view_expected.items():
            if evidence.get(key) != expected:
                failures.append(f"{failure_prefix}_{key}_mismatch")
        if (
            evidence.get(
                "future_kernel_native_consumer_program_view_row_assignment_formula"
            )
            != "program_id * rows_per_program + lane_id + row_offset"
        ):
            failures.append(f"{failure_prefix}_program_view_formula_mismatch")
        program_view_iteration_hash = _hex64_metric(
            evidence,
            "future_kernel_native_consumer_program_view_program_iteration_hash",
        )
        if program_view_iteration_hash is None:
            failures.append(f"{failure_prefix}_program_view_iteration_hash_missing")
        elif (
            actual_program_iteration_hash is not None
            and program_view_iteration_hash != actual_program_iteration_hash
        ):
            failures.append(f"{failure_prefix}_program_view_iteration_hash_mismatch")
    return failures


def _validate_future_native_arg_slot_online_merged_multiprogram_evidence(
    evidence: dict[str, Any],
    *,
    root: Path | None = None,
    arg_slot_mirror_field: str = "scale_metadata_handle",
) -> list[str]:
    failure_prefix = "online_merged_multiprogram_arg_slot"
    failures = _validate_future_native_arg_slot_multiprogram_evidence(
        evidence,
        expected_input_source="binary_prefix",
        require_pointer_visibility_macro=False,
        arg_slot_mirror_field=arg_slot_mirror_field,
    )
    input_json = evidence.get("input_json")
    if not isinstance(input_json, str) or not input_json:
        failures.append(f"{failure_prefix}_input_json_missing")
        return failures
    if root is None:
        return failures
    input_path = _path_for_label(input_json, root)
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        failures.append(f"{failure_prefix}_input_json_read_failed:{type(exc).__name__}")
        return failures
    except json.JSONDecodeError:
        failures.append(f"{failure_prefix}_input_json_invalid_json")
        return failures
    if not isinstance(payload, dict):
        failures.append(f"{failure_prefix}_input_json_not_object")
        return failures
    meta = payload.get("_meta")
    if not isinstance(meta, dict):
        failures.append(f"{failure_prefix}_meta_missing")
        meta = {}
    merge_context = payload.get("_merge_context")
    if not isinstance(merge_context, dict):
        failures.append(f"{failure_prefix}_merge_context_missing")
        merge_context = {}
    row_count = _int_metric(evidence, "row_count")
    grid_x = _int_metric(evidence, "future_kernel_native_dispatch_consumer_grid_x")
    block_x = _int_metric(evidence, "future_kernel_native_dispatch_consumer_block_x")
    expected_program_count = merge_context.get("expected_program_count")
    block_threads = merge_context.get("block_threads")
    source_count = merge_context.get("source_count")
    if merge_context.get("source") != "merged_vllm_prelaunch_typed_consumer_inputs":
        failures.append(f"{failure_prefix}_source_mismatch")
    if merge_context.get("not_a_single_vllm_launch_table") is not True:
        failures.append(f"{failure_prefix}_single_launch_flag_mismatch")
    if not isinstance(source_count, int) or isinstance(source_count, bool):
        failures.append(f"{failure_prefix}_source_count_invalid")
    elif source_count < 32:
        failures.append(f"{failure_prefix}_source_count_too_small")
    if row_count is not None:
        if meta.get("row_count") != row_count:
            failures.append(f"{failure_prefix}_meta_row_count_mismatch")
        if merge_context.get("row_count") != row_count:
            failures.append(f"{failure_prefix}_merge_row_count_mismatch")
    if grid_x is not None and expected_program_count != grid_x:
        failures.append(f"{failure_prefix}_expected_program_count_mismatch")
    if not isinstance(block_threads, int) or isinstance(block_threads, bool):
        failures.append(f"{failure_prefix}_block_threads_invalid")
    elif block_threads <= 0:
        failures.append(f"{failure_prefix}_block_threads_invalid")
    elif block_x is not None and block_threads != block_x:
        failures.append(f"{failure_prefix}_block_threads_block_x_mismatch")
    for key, expected_value in {
        "payload_bytes": 0,
        "ready_credit": False,
        "changes_router": False,
        "changes_descriptor_order": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }.items():
        if meta.get(key) != expected_value:
            failures.append(f"{failure_prefix}_meta_{key}_mismatch")
        if merge_context.get(key) != expected_value:
            failures.append(f"{failure_prefix}_merge_{key}_mismatch")
    row_spans = merge_context.get("row_spans")
    normalized_row_spans: list[dict[str, Any]] = []
    if not isinstance(row_spans, list) or not row_spans:
        failures.append(f"{failure_prefix}_row_spans_missing")
    else:
        cursor = 0
        for idx, span in enumerate(row_spans):
            if not isinstance(span, dict):
                failures.append(f"{failure_prefix}_row_span_{idx}_invalid")
                continue
            if span.get("source_index") != idx:
                failures.append(f"{failure_prefix}_row_span_{idx}_source_index_mismatch")
            row_start = span.get("row_start")
            row_end = span.get("row_end")
            span_rows = span.get("row_count")
            if row_start != cursor:
                failures.append(f"{failure_prefix}_row_span_{idx}_start_mismatch")
            if (
                not isinstance(span_rows, int)
                or isinstance(span_rows, bool)
                or span_rows <= 0
            ):
                failures.append(f"{failure_prefix}_row_span_{idx}_row_count_invalid")
                continue
            cursor += span_rows
            if row_end != cursor:
                failures.append(f"{failure_prefix}_row_span_{idx}_end_mismatch")
            if not isinstance(span.get("path"), str) or not span.get("path"):
                failures.append(f"{failure_prefix}_row_span_{idx}_path_missing")
            normalized_row_spans.append(span)
        if row_count is not None and cursor != row_count:
            failures.append(f"{failure_prefix}_row_spans_total_mismatch")
        if isinstance(source_count, int) and len(row_spans) != source_count:
            failures.append(f"{failure_prefix}_row_spans_source_count_mismatch")
    source_contexts = merge_context.get("source_contexts")
    if not isinstance(source_contexts, list) or not source_contexts:
        failures.append(f"{failure_prefix}_source_contexts_missing")
    elif isinstance(source_count, int) and len(source_contexts) != source_count:
        failures.append(f"{failure_prefix}_source_contexts_source_count_mismatch")
    elif isinstance(source_contexts, list):
        for idx, context in enumerate(source_contexts):
            if not isinstance(context, dict):
                failures.append(f"{failure_prefix}_source_context_{idx}_invalid")
                continue
            if context.get("source_index") != idx:
                failures.append(
                    f"{failure_prefix}_source_context_{idx}_source_index_mismatch"
                )
            if not isinstance(context.get("request_id"), str) or not context.get("request_id"):
                failures.append(f"{failure_prefix}_source_context_{idx}_request_id_missing")
            if "layer_id" not in context:
                failures.append(f"{failure_prefix}_source_context_{idx}_layer_id_missing")
            if idx < len(normalized_row_spans):
                span = normalized_row_spans[idx]
                if context.get("row_count") != span.get("row_count"):
                    failures.append(
                        f"{failure_prefix}_source_context_{idx}_row_count_mismatch"
                    )
    return failures


def _validate_wna16_adjacent_typed_slot_standalone_evidence(
    evidence: dict[str, Any],
) -> list[str]:
    failure_prefix = "standalone_wna16_adjacent_typed_slot"
    failures: list[str] = []
    row_count = _int_metric(evidence, "row_count")
    slot_prefix = "future_kernel_native_consumer_wna16_adjacent_typed_slot"
    expected_values = {
        "passed": True,
        "ok": True,
        "failures": [],
        "input_source": "synthetic",
        "expected_schema_hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        f"{slot_prefix}_abi_name": "premap_wna16_adjacent_typed_consumer_slot_v1",
        f"{slot_prefix}_mode": "readonly_wna16_adjacent_typed_consumer_slot",
        f"{slot_prefix}_source": (
            "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
        ),
        f"{slot_prefix}_checked": True,
        f"{slot_prefix}_summary_error_count": 0,
        f"{slot_prefix}_packet_chain_depth": 14,
        f"{slot_prefix}_payload_bytes": 0,
        f"{slot_prefix}_payload_deref_allowed": False,
        f"{slot_prefix}_passed_to_kernel": False,
        f"{slot_prefix}_kernel_arg_pass_allowed": False,
        f"{slot_prefix}_changes_kernel_launch_args": False,
        f"{slot_prefix}_current_wna16_arg_compatible": False,
        f"{slot_prefix}_requires_wna16_arg_reinterpretation": False,
        f"{slot_prefix}_explicit_typed_abi_slot": True,
        f"{slot_prefix}_reuses_current_wna16_arg_slot": False,
    }
    for key, expected_value in expected_values.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    compiled_macros = evidence.get("compiled_macros")
    if not isinstance(compiled_macros, dict):
        failures.append(f"{failure_prefix}_compiled_macros_missing")
    else:
        for macro in (
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI",
        ):
            if compiled_macros.get(macro) is not True:
                failures.append(f"{failure_prefix}_{macro}_missing")
        for macro in (
            "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
            "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
        ):
            if compiled_macros.get(macro) is True:
                failures.append(f"{failure_prefix}_{macro}_forbidden")
    if row_count is None or row_count <= 0:
        failures.append(f"{failure_prefix}_row_count_invalid")
    else:
        for key in (
            f"{slot_prefix}_summary_row_count",
            f"{slot_prefix}_summary_row_ok_count",
            f"{slot_prefix}_summary_descriptor_ptr_read_row_ok_count",
            f"{slot_prefix}_summary_packed_weight_descriptor_read_row_ok_count",
            f"{slot_prefix}_summary_scale_metadata_handle_read_row_ok_count",
            f"{slot_prefix}_summary_aux_metadata_handle_read_row_ok_count",
            f"{slot_prefix}_summary_expert_id_read_row_ok_count",
            f"{slot_prefix}_summary_address_key_hash_read_row_ok_count",
            f"{slot_prefix}_summary_row_metadata_read_row_ok_count",
        ):
            if _int_metric(evidence, key) != row_count:
                failures.append(f"{failure_prefix}_{key}_mismatch")
    endpoint_chain_depth = _int_metric(
        evidence,
        "future_kernel_native_consumer_endpoint_ptr_packet_chain_depth",
    )
    slot_chain_depth = _int_metric(evidence, f"{slot_prefix}_packet_chain_depth")
    if endpoint_chain_depth is not None and slot_chain_depth != endpoint_chain_depth + 1:
        failures.append(f"{failure_prefix}_packet_chain_depth_mismatch")
    if _int_metric(evidence, f"{slot_prefix}_summary_field_mask") != 15:
        failures.append(f"{failure_prefix}_field_mask_mismatch")
    for key in (
        f"{slot_prefix}_summary_row_hash_accumulator",
        f"{slot_prefix}_summary_field_read_hash_accumulator",
        f"{slot_prefix}_summary_row_metadata_hash_accumulator",
    ):
        if _hex64_metric(evidence, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_wna16_adjacent_typed_slot_stub_metrics(
    evidence: dict[str, Any],
    *,
    failure_prefix: str,
    expected_rows: int | None,
) -> list[str]:
    failures: list[str] = []
    slot_prefix = "future_kernel_native_consumer_wna16_adjacent_typed_slot"
    expected_values = {
        f"{slot_prefix}_abi_name": "premap_wna16_adjacent_typed_consumer_slot_v1",
        f"{slot_prefix}_mode": "readonly_wna16_adjacent_typed_consumer_slot",
        f"{slot_prefix}_source": (
            "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
        ),
        f"{slot_prefix}_checked": True,
        f"{slot_prefix}_summary_error_count": 0,
        f"{slot_prefix}_payload_bytes": 0,
        f"{slot_prefix}_passed_to_kernel": False,
        f"{slot_prefix}_changes_kernel_launch_args": False,
        f"{slot_prefix}_current_wna16_arg_compatible": False,
        f"{slot_prefix}_requires_wna16_arg_reinterpretation": False,
        f"{slot_prefix}_explicit_typed_abi_slot": True,
        f"{slot_prefix}_reuses_current_wna16_arg_slot": False,
    }
    for key, expected_value in expected_values.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if expected_rows is not None:
        for key in (
            f"{slot_prefix}_summary_row_count",
            f"{slot_prefix}_summary_row_ok_count",
            f"{slot_prefix}_summary_descriptor_ptr_read_row_ok_count",
            f"{slot_prefix}_summary_packed_weight_descriptor_read_row_ok_count",
            f"{slot_prefix}_summary_scale_metadata_handle_read_row_ok_count",
            f"{slot_prefix}_summary_aux_metadata_handle_read_row_ok_count",
            f"{slot_prefix}_summary_expert_id_read_row_ok_count",
            f"{slot_prefix}_summary_address_key_hash_read_row_ok_count",
            f"{slot_prefix}_summary_row_metadata_read_row_ok_count",
        ):
            if _int_metric(evidence, key) != expected_rows:
                failures.append(f"{failure_prefix}_{key}_mismatch")
    endpoint_chain_depth = _int_metric(
        evidence,
        "future_kernel_native_consumer_endpoint_ptr_packet_chain_depth",
    )
    slot_chain_depth = _int_metric(evidence, f"{slot_prefix}_packet_chain_depth")
    if endpoint_chain_depth is not None and slot_chain_depth != endpoint_chain_depth + 1:
        failures.append(f"{failure_prefix}_{slot_prefix}_packet_chain_depth_mismatch")
    if _int_metric(evidence, f"{slot_prefix}_summary_field_mask") != 15:
        failures.append(f"{failure_prefix}_{slot_prefix}_field_mask_mismatch")
    for key in (
        f"{slot_prefix}_summary_row_hash_accumulator",
        f"{slot_prefix}_summary_field_read_hash_accumulator",
        f"{slot_prefix}_summary_row_metadata_hash_accumulator",
    ):
        if _hex64_metric(evidence, key) is None:
            failures.append(f"{failure_prefix}_{key}_invalid")
    return failures


def _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
    evidence: dict[str, Any],
    *,
    root: Path | None = None,
    evidence_paths: dict[str, Any] | None = None,
    expected_stub_output_label: str | None = (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json"
    ),
    arg_slot_mirror_field: str = "scale_metadata_handle",
    require_kernel_launch_context_abi: bool = True,
    require_kernel_invocation_abi: bool = True,
    require_kernel_invocation_entry_abi: bool = True,
    require_kernel_endpoint_abi: bool = True,
    require_kernel_endpoint_ptr_abi: bool = True,
    require_wna16_adjacent_typed_slot: bool = False,
    validate_stub_output: bool = True,
) -> list[str]:
    failure_prefix = "online_merged_multiprogram_arg_slot_runner"
    failures: list[str] = []
    if evidence.get("passed") is not True:
        failures.append(f"{failure_prefix}_not_passed")
    runner_failures = evidence.get("failures")
    if runner_failures != []:
        failures.append(f"{failure_prefix}_failures_not_empty")
    if evidence.get("source") != "online_merged_future_native_arg_slot_canary_runner":
        failures.append(f"{failure_prefix}_source_mismatch")
    if not _targets_default_lab_gpu1(evidence):
        failures.append(f"{failure_prefix}_device_not_gpu1")
    if evidence.get("mirror_field") != arg_slot_mirror_field:
        failures.append(f"{failure_prefix}_mirror_field_mismatch")
    if evidence.get("not_a_single_vllm_launch_table") is not True:
        failures.append(f"{failure_prefix}_single_launch_flag_mismatch")
    if evidence.get("handle_projection_hashchain_equal") is not True:
        failures.append(f"{failure_prefix}_handle_projection_hashchain_not_equal")
    if evidence.get("handle_projection_field_names") != list(ARG_SLOT_MIRROR_FIELDS):
        failures.append(f"{failure_prefix}_handle_projection_field_names_mismatch")
    if evidence.get("handle_projection_all_handle_fields_checked") is not True:
        failures.append(f"{failure_prefix}_handle_projection_all_fields_unchecked")
    for key, expected_value in {
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
    }.items():
        if evidence.get(key) != expected_value:
            failures.append(f"{failure_prefix}_{key}_mismatch")
    if require_kernel_launch_context_abi:
        for key in (
            "require_kernel_launch_context_abi",
            "require_kernel_launch_descriptor_abi",
            "require_launch_envelope_args_abi",
            "require_launch_envelope_args_ptr_abi",
        ):
            if evidence.get(key) is not True:
                failures.append(f"{failure_prefix}_{key}_missing")
    if require_kernel_invocation_abi and evidence.get("require_kernel_invocation_abi") is not True:
        failures.append(f"{failure_prefix}_require_kernel_invocation_abi_missing")
    if (
        require_kernel_invocation_entry_abi
        and evidence.get("require_kernel_invocation_entry_abi") is not True
    ):
        failures.append(
            f"{failure_prefix}_require_kernel_invocation_entry_abi_missing"
        )
    if (
        require_kernel_endpoint_abi
        and evidence.get("require_kernel_endpoint_abi") is not True
    ):
        failures.append(f"{failure_prefix}_require_kernel_endpoint_abi_missing")
    if (
        require_kernel_endpoint_ptr_abi
        and evidence.get("require_kernel_endpoint_ptr_abi") is not True
    ):
        failures.append(f"{failure_prefix}_require_kernel_endpoint_ptr_abi_missing")
    if require_wna16_adjacent_typed_slot:
        if evidence.get("require_wna16_adjacent_typed_slot") is not True:
            failures.append(
                f"{failure_prefix}_require_wna16_adjacent_typed_slot_missing"
            )
        if evidence.get("wna16_adjacent_typed_slot_checked") is not True:
            failures.append(f"{failure_prefix}_wna16_adjacent_typed_slot_unchecked")
        if evidence.get("wna16_adjacent_typed_slot_name") != (
            "premap_wna16_adjacent_typed_consumer_slot_v1"
        ):
            failures.append(f"{failure_prefix}_wna16_adjacent_typed_slot_name_mismatch")
        if evidence.get("wna16_adjacent_typed_slot_mode") != (
            "readonly_wna16_adjacent_typed_consumer_slot"
        ):
            failures.append(f"{failure_prefix}_wna16_adjacent_typed_slot_mode_mismatch")
        if evidence.get("wna16_adjacent_typed_slot_source") != (
            "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
        ):
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_source_mismatch"
            )

    source_count = _int_metric(evidence, "selected_source_count")
    merged_row_count = _int_metric(evidence, "merged_row_count")
    block_threads = _int_metric(evidence, "block_threads")
    merged_program_count = _int_metric(evidence, "merged_expected_program_count")
    dispatch_offset = _int_metric(evidence, "dispatch_row_offset")
    dispatch_limit = _int_metric(evidence, "dispatch_row_limit")
    dispatch_active_rows = _int_metric(evidence, "dispatch_active_rows")
    dispatch_program_count = _int_metric(evidence, "dispatch_expected_program_count")
    if source_count is None:
        failures.append(f"{failure_prefix}_source_count_missing")
    elif source_count < 32:
        failures.append(f"{failure_prefix}_source_count_too_small")
    if merged_row_count is None or merged_row_count <= 0:
        failures.append(f"{failure_prefix}_merged_row_count_invalid")
    if block_threads is None or block_threads <= 0:
        failures.append(f"{failure_prefix}_block_threads_invalid")
    if (
        merged_row_count is not None
        and block_threads is not None
        and merged_program_count is not None
        and (merged_row_count + block_threads - 1) // block_threads
        != merged_program_count
    ):
        failures.append(f"{failure_prefix}_merged_program_count_mismatch")
    # The default lab gate requires the runner artifact to cover the full merged
    # table.  Tail/window runners are valid supporting diagnostics but are not
    # the required default evidence.
    if dispatch_offset != 0:
        failures.append(f"{failure_prefix}_dispatch_offset_not_zero")
    if merged_row_count is not None and dispatch_limit != merged_row_count:
        failures.append(f"{failure_prefix}_dispatch_limit_not_full_table")
    if merged_row_count is not None and dispatch_active_rows != merged_row_count:
        failures.append(f"{failure_prefix}_dispatch_active_rows_mismatch")
    if (
        dispatch_active_rows is not None
        and block_threads is not None
        and dispatch_program_count is not None
        and (dispatch_active_rows + block_threads - 1) // block_threads
        != dispatch_program_count
    ):
        failures.append(f"{failure_prefix}_dispatch_program_count_mismatch")
    expected_device = _int_metric(evidence, "device")
    if require_kernel_launch_context_abi:
        failures.extend(
            _validate_kernel_launch_context_runner_metrics(
                evidence,
                prefix="kernel_launch_context",
                failure_prefix=failure_prefix,
                expected_device=expected_device,
            )
        )
    if require_kernel_invocation_abi:
        failures.extend(
            _validate_invocation_runner_metrics(
                evidence,
                prefix="kernel_invocation",
                failure_prefix=failure_prefix,
                expected_device=expected_device,
            )
        )
    if require_kernel_invocation_entry_abi:
        failures.extend(
            _validate_invocation_entry_metrics(
                evidence,
                prefix="kernel_invocation_entry",
                failure_prefix=failure_prefix,
                expected_rows=dispatch_active_rows,
            )
        )
    if require_kernel_endpoint_abi:
        failures.extend(
            _validate_endpoint_metrics(
                evidence,
                prefix="kernel_endpoint",
                failure_prefix=failure_prefix,
                expected_rows=dispatch_active_rows,
            )
        )
    if require_kernel_endpoint_ptr_abi:
        failures.extend(
            _validate_endpoint_ptr_metrics(
                evidence,
                prefix="kernel_endpoint_ptr",
                failure_prefix=failure_prefix,
                expected_rows=dispatch_active_rows,
            )
        )
    if require_wna16_adjacent_typed_slot:
        slot_row_count = _int_metric(evidence, "wna16_adjacent_typed_slot_row_count")
        slot_row_ok_count = _int_metric(
            evidence, "wna16_adjacent_typed_slot_row_ok_count"
        )
        slot_error_count = _int_metric(
            evidence, "wna16_adjacent_typed_slot_error_count"
        )
        slot_payload_bytes = _int_metric(
            evidence, "wna16_adjacent_typed_slot_payload_bytes"
        )
        slot_packet_chain_depth = _int_metric(
            evidence, "wna16_adjacent_typed_slot_packet_chain_depth"
        )
        endpoint_packet_chain_depth = _int_metric(
            evidence, "kernel_endpoint_ptr_packet_chain_depth"
        )
        if dispatch_active_rows is not None and slot_row_count != dispatch_active_rows:
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_row_count_mismatch"
            )
        if dispatch_active_rows is not None and slot_row_ok_count != dispatch_active_rows:
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_row_ok_count_mismatch"
            )
        if slot_error_count != 0:
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_error_count_mismatch"
            )
        if evidence.get("wna16_adjacent_typed_slot_all_handle_fields_read") is not True:
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_all_fields_unchecked"
            )
        if (
            endpoint_packet_chain_depth is not None
            and slot_packet_chain_depth != endpoint_packet_chain_depth + 1
        ):
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_packet_chain_depth_mismatch"
            )
        if slot_payload_bytes != 0:
            failures.append(
                f"{failure_prefix}_wna16_adjacent_typed_slot_payload_bytes_mismatch"
            )
        for key, expected_value in {
            "wna16_adjacent_typed_slot_passed_to_kernel": False,
            "wna16_adjacent_typed_slot_changes_kernel_launch_args": False,
            "wna16_adjacent_typed_slot_current_wna16_arg_compatible": False,
            "wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation": False,
            "wna16_adjacent_typed_slot_explicit_typed_abi_slot": True,
            "wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot": False,
        }.items():
            if evidence.get(key) is not expected_value:
                failures.append(f"{failure_prefix}_{key}_mismatch")
        for key in (
            "wna16_adjacent_typed_slot_row_hash_accumulator",
            "wna16_adjacent_typed_slot_field_read_hash_accumulator",
            "wna16_adjacent_typed_slot_row_metadata_hash_accumulator",
        ):
            if _hex64_metric(evidence, key) is None:
                failures.append(f"{failure_prefix}_{key}_invalid")

    stub_summary = evidence.get("stub_summary")
    if not isinstance(stub_summary, dict):
        failures.append(f"{failure_prefix}_stub_summary_missing")
        stub_summary = {}
    else:
        for key, expected_value in {
            "passed": True,
            "ok": True,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_checked": True,
            "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
            "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
            "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
        }.items():
            if stub_summary.get(key) != expected_value:
                failures.append(f"{failure_prefix}_stub_summary_{key}_mismatch")
        if (
            merged_row_count is not None
            and stub_summary.get("future_kernel_native_arg_slot_consumer_row_count")
            != merged_row_count
        ):
            failures.append(f"{failure_prefix}_stub_summary_arg_slot_row_count_mismatch")
        if (
            dispatch_program_count is not None
            and stub_summary.get("future_kernel_native_dispatch_consumer_grid_x")
            != dispatch_program_count
        ):
            failures.append(f"{failure_prefix}_stub_summary_dispatch_grid_mismatch")
        if require_kernel_launch_context_abi:
            failures.extend(
                _validate_kernel_launch_context_stub_summary_metrics(
                    stub_summary,
                    failure_prefix=f"{failure_prefix}_stub_summary",
                    expected_rows=merged_row_count,
                    expected_device=expected_device,
                )
            )
        if require_kernel_invocation_abi:
            failures.extend(
                _validate_invocation_stub_summary_metrics(
                    stub_summary,
                    failure_prefix=f"{failure_prefix}_stub_summary",
                    expected_rows=merged_row_count,
                    expected_device=expected_device,
                )
            )
            failures.extend(
                _validate_invocation_cross_layer_metrics(
                    evidence,
                    stub_summary,
                    other_label="stub_summary",
                    failure_prefix=failure_prefix,
                )
            )
        if require_kernel_invocation_entry_abi:
            failures.extend(
                _validate_invocation_entry_metrics(
                    stub_summary,
                    prefix="future_kernel_native_consumer_invocation_entry",
                    failure_prefix=f"{failure_prefix}_stub_summary",
                    expected_rows=merged_row_count,
                    compact_summary=True,
                )
            )
        if require_kernel_endpoint_abi:
            failures.extend(
                _validate_endpoint_metrics(
                    stub_summary,
                    prefix="future_kernel_native_consumer_endpoint",
                    failure_prefix=f"{failure_prefix}_stub_summary",
                    expected_rows=merged_row_count,
                    compact_summary=True,
                )
            )
        if require_kernel_endpoint_ptr_abi:
            failures.extend(
                _validate_endpoint_ptr_metrics(
                    stub_summary,
                    prefix="future_kernel_native_consumer_endpoint_ptr",
                    failure_prefix=f"{failure_prefix}_stub_summary",
                    expected_rows=merged_row_count,
                    compact_summary=True,
                )
            )
        if require_wna16_adjacent_typed_slot:
            failures.extend(
                _validate_wna16_adjacent_typed_slot_stub_metrics(
                    stub_summary,
                    failure_prefix=f"{failure_prefix}_stub_summary",
                    expected_rows=merged_row_count,
                )
            )

    stub_output = evidence.get("stub_output_json")
    if not isinstance(stub_output, str) or not stub_output:
        failures.append(f"{failure_prefix}_stub_output_json_missing")
        return failures
    if not validate_stub_output:
        return failures
    if evidence_paths is not None and expected_stub_output_label is not None:
        expected_stub_output = evidence_paths.get(expected_stub_output_label)
        if isinstance(expected_stub_output, str) and expected_stub_output:
            if root is not None:
                expected_path = _path_for_label(expected_stub_output, root).resolve()
                actual_path = _path_for_label(stub_output, root).resolve()
                if expected_path != actual_path:
                    failures.append(f"{failure_prefix}_stub_output_path_mismatch")
            elif expected_stub_output != stub_output:
                failures.append(f"{failure_prefix}_stub_output_path_mismatch")
    if root is None:
        return failures
    stub_path = _path_for_label(stub_output, root)
    try:
        stub_payload = json.loads(stub_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        failures.append(f"{failure_prefix}_stub_output_read_failed:{type(exc).__name__}")
        return failures
    except json.JSONDecodeError:
        failures.append(f"{failure_prefix}_stub_output_invalid_json")
        return failures
    if not isinstance(stub_payload, dict):
        failures.append(f"{failure_prefix}_stub_output_not_object")
        return failures
    failures.extend(
        f"{failure_prefix}_stub:{failure}"
        for failure in _validate_future_native_arg_slot_online_merged_multiprogram_evidence(
            stub_payload,
            root=root,
            arg_slot_mirror_field=arg_slot_mirror_field,
        )
    )
    if require_kernel_launch_context_abi:
        failures.extend(
            f"{failure_prefix}_stub:{failure}"
            for failure in _validate_kernel_launch_context_stub_summary_metrics(
                stub_payload,
                failure_prefix="kernel_launch_context",
                expected_rows=merged_row_count,
                expected_device=expected_device,
            )
        )
    if require_kernel_invocation_abi:
        failures.extend(
            f"{failure_prefix}_stub:{failure}"
            for failure in _validate_invocation_stub_summary_metrics(
                stub_payload,
                failure_prefix="kernel_invocation",
                expected_rows=merged_row_count,
                expected_device=expected_device,
            )
        )
        failures.extend(
            _validate_invocation_cross_layer_metrics(
                evidence,
                stub_payload,
                other_label="stub_payload",
                failure_prefix=failure_prefix,
            )
        )
    if require_wna16_adjacent_typed_slot:
        failures.extend(
            f"{failure_prefix}_stub:{failure}"
            for failure in _validate_wna16_adjacent_typed_slot_stub_metrics(
                stub_payload,
                failure_prefix="wna16_adjacent_typed_slot",
                expected_rows=merged_row_count,
            )
        )
    return failures


def _self_finalization_evidence_allowed(
    evidence_label: str,
    evidence: dict[str, Any],
) -> bool:
    if evidence_label not in ONLINE_PRELAUNCH_SELF_FINALIZATION_EVIDENCE_LABELS:
        return False
    if evidence_label in ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS:
        if evidence.get("bootstrap_preflight_allowed") is True:
            return True
        failures = evidence.get("failures")
        if not isinstance(failures, list):
            return False
        if set(failures) - {"runner_not_passed", "runner_failures_not_empty"}:
            return False
        min_inputs = ONLINE_PRELAUNCH_MIN_INPUTS_BY_LABEL.get(evidence_label, 1)
        input_count = _int_metric(evidence, "runner_online_prelaunch_input_check_count")
        if input_count is None or input_count < min_inputs:
            return False
        final_deferred = _int_metric(evidence, "final_deferred_count")
        status_deferred = _int_metric(evidence, "status_deferred_count")
        return (final_deferred in (None, 0)) and (status_deferred in (None, 0))
    bootstrap_summary = evidence.get("artifact_check_bootstrap_summary")
    return (
        isinstance(bootstrap_summary, dict)
        and bootstrap_summary.get("bootstrap_preflight_allowed") is True
    )


def _check_optional_default_gate_evidence_json(
    gate_path: str,
    *,
    root: Path,
    deferred_labels: set[str] | None = None,
    allow_online_runner_self_finalization: bool = False,
) -> dict[str, Any]:
    path = _path_for_label(gate_path, root)
    label = _path_label(path, root=root)
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "gate_path": label,
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "optional_labels": sorted(OPTIONAL_DEFAULT_GATE_EVIDENCE_JSON_LABELS),
            "rows": rows,
        }
    evidence_paths = ((payload or {}).get("evidence_paths") or {})
    optional_paths = ((payload or {}).get("optional_evidence_paths") or {})
    combined_paths: dict[str, Any] = {}
    if isinstance(evidence_paths, dict):
        combined_paths.update(evidence_paths)
    if isinstance(optional_paths, dict):
        combined_paths.update(optional_paths)
    else:
        optional_paths = {}
    deferred_labels = set(deferred_labels or ())

    for evidence_label in sorted(OPTIONAL_DEFAULT_GATE_EVIDENCE_JSON_LABELS):
        raw_path = combined_paths.get(evidence_label)
        row: dict[str, Any] = {
            "label": evidence_label,
            "path": raw_path,
            "exists": False,
            "valid_json": None,
            "passed_value": None,
            "failures_value": None,
            "optional": True,
        }
        if evidence_label in deferred_labels:
            row["deferred"] = True
            rows.append(row)
            continue
        if not isinstance(raw_path, str) or not raw_path:
            row["failure"] = "missing_optional_evidence_path"
            rows.append(row)
            continue
        evidence_path = _path_for_label(raw_path, root)
        row["path_label"] = _path_label(evidence_path, root=root)
        row["exists"] = evidence_path.exists()
        if not evidence_path.exists():
            row["failure"] = "missing_optional_file"
            rows.append(row)
            continue
        if not evidence_path.is_file():
            failures.append(f"{evidence_label}:not_file")
            row["failure"] = "not_file"
            rows.append(row)
            continue
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(f"{evidence_label}:read_failed")
            row["valid_json"] = False
            row["failure"] = f"read_failed:{type(exc).__name__}:{exc}"
            rows.append(row)
            continue
        except json.JSONDecodeError as exc:
            failures.append(f"{evidence_label}:invalid_json")
            row["valid_json"] = False
            row["failure"] = f"invalid_json:{exc.msg}"
            rows.append(row)
            continue
        row["valid_json"] = True
        row["passed_value"] = (
            evidence.get("passed") if isinstance(evidence, dict) else None
        )
        row["failures_value"] = (
            evidence.get("failures") if isinstance(evidence, dict) else None
        )
        self_finalization_allowed = (
            allow_online_runner_self_finalization
            and _self_finalization_evidence_allowed(evidence_label, evidence)
        )
        if not isinstance(evidence, dict):
            failures.append(f"{evidence_label}:json_not_object")
            row["failure"] = "json_not_object"
        elif evidence.get("passed") is not True and not self_finalization_allowed:
            failures.append(f"{evidence_label}:not_passed")
            row["failure"] = "not_passed"
        elif evidence.get("failures") != [] and not self_finalization_allowed:
            failures.append(f"{evidence_label}:failures_not_empty")
            row["failure"] = "failures_not_empty"
        elif self_finalization_allowed:
            row["self_finalization_allowed"] = True
            row["failure"] = None
        else:
            content_failures = _validate_required_evidence_payload(
                evidence_label,
                evidence,
                evidence_paths=combined_paths,
                root=root,
                allow_online_runner_self_finalization=(
                    allow_online_runner_self_finalization
                ),
            )
            if content_failures:
                failures.extend(content_failures)
                row["failure"] = "content_check_failed"
                row["content_failures"] = content_failures
        rows.append(row)
    return {
        "gate_path": label,
        "passed": not failures,
        "failures": failures,
        "optional_labels": sorted(OPTIONAL_DEFAULT_GATE_EVIDENCE_JSON_LABELS),
        "rows": rows,
    }
RISKY_TRACE_FLAGS = {
    "premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
    "premap_kernel_arg_handoff_single_field_replacement_live_enabled",
}


def _path_label(path: Path, *, root: Path) -> str:
    path = path.resolve()
    root = root.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def _path_labels_match(observed_raw: str, expected_raw: str, *, root: Path) -> bool:
    observed_label = _path_label(_path_for_label(observed_raw, root), root=root)
    expected_label = _path_label(_path_for_label(expected_raw, root), root=root)
    if observed_label == expected_label:
        return True
    observed_posix = Path(observed_raw).as_posix()
    expected_posix = Path(expected_raw).as_posix()
    return (
        observed_posix == expected_label
        or observed_posix.endswith(f"/{expected_label}")
        or expected_posix == observed_label
        or expected_posix.endswith(f"/{observed_label}")
    )


def _path_for_label(raw_path: str, root: Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else root / path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_label_sha256(raw_path: Any, *, root: Path) -> str | None:
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = _path_for_label(raw_path, root)
    if not path.is_file():
        return None
    try:
        return _file_sha256(path)
    except OSError:
        return None


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _check_trace_config(
    config_path: Path,
    *,
    root: Path,
    expected_readonly_gate: str,
) -> dict[str, Any]:
    config_path = config_path if config_path.is_absolute() else root / config_path
    label = _path_label(config_path, root=root)
    failures: list[str] = []
    try:
        config = _load_yaml(config_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "config_path": label,
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
        }
    shadow = ((config or {}).get("trace") or {}).get("runtime_shadow") or {}
    readonly_gate = shadow.get("premap_consumer_readonly_gate_path")
    readonly_gate_label = (
        _path_label(_path_for_label(readonly_gate, root), root=root)
        if isinstance(readonly_gate, str)
        else None
    )
    expected_readonly_gate_label = _path_label(
        _path_for_label(expected_readonly_gate, root),
        root=root,
    )
    kernel_arg_pass = bool(
        shadow.get("premap_kernel_arg_handoff_kernel_arg_pass_enabled", False)
    )
    live_enabled = bool(shadow.get("premap_kernel_arg_handoff_live_enabled", False))
    live_consumer_connected = bool(
        shadow.get("premap_kernel_arg_handoff_live_consumer_connected", False)
    )
    require_gate = bool(shadow.get("premap_consumer_require_readonly_gate", False))
    if readonly_gate_label != expected_readonly_gate_label:
        failures.append("readonly_gate_path_mismatch")
    if kernel_arg_pass:
        failures.append("kernel_arg_pass_enabled")
    if not live_enabled:
        failures.append("live_disabled_in_default_lab_config")
    if not live_consumer_connected:
        failures.append("live_consumer_disconnected_in_default_lab_config")
    if not require_gate:
        failures.append("readonly_gate_not_required")
    return {
        "config_path": label,
        "passed": not failures,
        "failures": failures,
        "readonly_gate_path": readonly_gate,
        "readonly_gate_path_label": readonly_gate_label,
        "expected_readonly_gate_path_label": expected_readonly_gate_label,
        "premap_consumer_require_readonly_gate": require_gate,
        "premap_kernel_arg_handoff_live_enabled": live_enabled,
        "premap_kernel_arg_handoff_live_consumer_connected": live_consumer_connected,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": kernel_arg_pass,
    }


def _check_default_gate_contract(
    gate_path: str,
    *,
    root: Path,
) -> dict[str, Any]:
    path = _path_for_label(gate_path, root)
    label = _path_label(path, root=root)
    failures: list[str] = []
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "gate_path": label,
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "observed_contract": {},
            "required_contract": dict(REQUIRED_DEFAULT_GATE_CONTRACT),
            "observed_contract_available": False,
        }
    contract = ((payload or {}).get("contract") or {})
    if not isinstance(contract, dict):
        return {
            "gate_path": label,
            "passed": False,
            "failures": ["contract_type_mismatch"],
            "observed_contract": {},
            "required_contract": dict(REQUIRED_DEFAULT_GATE_CONTRACT),
            "observed_contract_available": False,
        }
    for key, expected in REQUIRED_DEFAULT_GATE_CONTRACT.items():
        actual = contract.get(key)
        if not _strict_scalar_equal(actual, expected):
            failures.append(f"{key}_mismatch")
    if contract.get("future_kernel_native_dispatch_consumer_full_table_required") is True:
        for key in (
            "future_kernel_native_dispatch_consumer_tail_window_required",
            "future_kernel_native_dispatch_consumer_tail_window_size",
        ):
            if key in contract:
                failures.append(f"{key}_unexpected")
    return {
        "gate_path": label,
        "passed": not failures,
        "failures": failures,
        "observed_contract": dict(contract) if isinstance(contract, dict) else {},
        "required_contract": dict(REQUIRED_DEFAULT_GATE_CONTRACT),
        "observed_contract_available": isinstance(contract, dict),
    }


def _check_default_kernel_consumer_schema(
    gate_path: str,
    *,
    root: Path,
    default_schema_path: str = DEFAULT_KERNEL_CONSUMER_SCHEMA_ARTIFACT,
) -> dict[str, Any]:
    path = _path_for_label(gate_path, root)
    label = _path_label(path, root=root)
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "gate_path": label,
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "schema_path": None,
        }
    schema_artifacts = ((payload or {}).get("schema_artifacts") or None)
    if not isinstance(schema_artifacts, dict):
        return {
            "gate_path": label,
            "passed": False,
            "failures": ["schema_artifacts_missing_or_not_mapping"],
            "schema_path": None,
        }
    raw_schema_path = schema_artifacts.get("kernel_side_typed_consumer_schema_yaml")
    if not isinstance(raw_schema_path, str) or not raw_schema_path:
        return {
            "gate_path": label,
            "passed": False,
            "failures": ["kernel_side_typed_consumer_schema_path_missing"],
            "schema_path": raw_schema_path,
        }
    expected_label = _path_label(_path_for_label(default_schema_path, root), root=root)
    observed_label = _path_label(_path_for_label(raw_schema_path, root), root=root)
    if observed_label != expected_label:
        return {
            "gate_path": label,
            "passed": False,
            "failures": [
                f"kernel_side_typed_consumer_schema_path_mismatch:{observed_label}!={expected_label}"
            ],
            "schema_path": raw_schema_path,
            "schema_path_label": observed_label,
        }
    schema_path = _path_for_label(raw_schema_path, root)
    check = check_kernel_consumer_schema_artifact(schema_path)
    failures = [
        f"schema_check:{failure}"
        for failure in check.get("failures", [])
    ]
    return {
        "gate_path": label,
        "passed": bool(check.get("passed", False)) and not failures,
        "failures": failures,
        "schema_path": raw_schema_path,
        "schema_path_label": _path_label(schema_path, root=root),
        "schema_check": check,
    }


def _check_required_default_gate_evidence_json(
    gate_path: str,
    *,
    root: Path,
    allow_missing: bool = False,
    defer_online_prelaunch_runner_evidence: bool = False,
    defer_online_prelaunch_artifact_evidence: bool = False,
    allow_online_runner_self_finalization: bool = False,
) -> dict[str, Any]:
    path = _path_for_label(gate_path, root)
    label = _path_label(path, root=root)
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "gate_path": label,
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "required_labels": sorted(REQUIRED_DEFAULT_GATE_EVIDENCE_JSON_LABELS),
            "rows": rows,
        }
    evidence_paths = ((payload or {}).get("evidence_paths") or {})
    if not isinstance(evidence_paths, dict):
        evidence_paths = {}
    for evidence_label in sorted(REQUIRED_DEFAULT_GATE_EVIDENCE_JSON_LABELS):
        raw_path = evidence_paths.get(evidence_label)
        row: dict[str, Any] = {
            "label": evidence_label,
            "path": raw_path,
            "exists": False,
            "valid_json": None,
            "passed_value": None,
            "failures_value": None,
        }
        if (
            (
                defer_online_prelaunch_runner_evidence
                and evidence_label in ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABELS
            )
            or (
                defer_online_prelaunch_artifact_evidence
                and evidence_label in ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS
            )
        ):
            row["deferred"] = True
            row["failure"] = None
            rows.append(row)
            continue
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(f"{evidence_label}:missing_evidence_path")
            row["failure"] = "missing_evidence_path"
            rows.append(row)
            continue
        evidence_path = _path_for_label(raw_path, root)
        row["path_label"] = _path_label(evidence_path, root=root)
        row["exists"] = evidence_path.exists()
        if not evidence_path.exists():
            row["failure"] = "missing_file"
            row["allowed_missing"] = bool(allow_missing)
            if not allow_missing:
                failures.append(f"{evidence_label}:missing_file")
            rows.append(row)
            continue
        if not evidence_path.is_file():
            failures.append(f"{evidence_label}:not_file")
            row["failure"] = "not_file"
            rows.append(row)
            continue
        try:
            row["sha256"] = _file_sha256(evidence_path)
        except OSError as exc:
            failures.append(f"{evidence_label}:sha256_failed")
            row["failure"] = f"sha256_failed:{type(exc).__name__}:{exc}"
            rows.append(row)
            continue
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(f"{evidence_label}:read_failed")
            row["valid_json"] = False
            row["failure"] = f"read_failed:{type(exc).__name__}:{exc}"
            rows.append(row)
            continue
        except json.JSONDecodeError as exc:
            failures.append(f"{evidence_label}:invalid_json")
            row["valid_json"] = False
            row["failure"] = f"invalid_json:{exc.msg}"
            rows.append(row)
            continue
        row["valid_json"] = True
        row["passed_value"] = (
            evidence.get("passed") if isinstance(evidence, dict) else None
        )
        row["failures_value"] = (
            evidence.get("failures") if isinstance(evidence, dict) else None
        )
        self_finalization_allowed = (
            allow_online_runner_self_finalization
            and _self_finalization_evidence_allowed(evidence_label, evidence)
        )
        if not isinstance(evidence, dict):
            failures.append(f"{evidence_label}:json_not_object")
            row["failure"] = "json_not_object"
        elif evidence.get("passed") is not True and not self_finalization_allowed:
            failures.append(f"{evidence_label}:not_passed")
            row["failure"] = "not_passed"
        elif evidence.get("failures") != [] and not self_finalization_allowed:
            failures.append(f"{evidence_label}:failures_not_empty")
            row["failure"] = "failures_not_empty"
        elif self_finalization_allowed:
            row["self_finalization_allowed"] = True
            row["failure"] = None
        else:
            content_failures = _validate_required_evidence_payload(
                evidence_label,
                evidence,
                evidence_paths=evidence_paths,
                root=root,
                allow_online_runner_self_finalization=(
                    allow_online_runner_self_finalization
                ),
            )
            if content_failures:
                failures.extend(content_failures)
                row["failure"] = "content_check_failed"
                row["content_failures"] = content_failures
        rows.append(row)
    return {
        "gate_path": label,
        "passed": not failures,
        "failures": failures,
        "required_labels": sorted(REQUIRED_DEFAULT_GATE_EVIDENCE_JSON_LABELS),
        "deferred_labels": sorted(
            (
                ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABELS
                if defer_online_prelaunch_runner_evidence
                else set()
            )
            | (
                ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS
                if defer_online_prelaunch_artifact_evidence
                else set()
            )
        ),
        "rows": rows,
    }


def _summarize_required_evidence_check(
    check: dict[str, Any],
) -> dict[str, Any]:
    rows = check.get("rows")
    if not isinstance(rows, list):
        rows = []
    evidence: dict[str, Any] = {}
    passed_count = 0
    present_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = row.get("label")
        if not isinstance(label, str) or not label:
            continue
        is_present = row.get("exists") is True
        row_failure = row.get("failure")
        is_passed = (
            is_present
            and row.get("valid_json") is True
            and row.get("passed_value") is True
            and row.get("failures_value") == []
            and row_failure is None
        ) or (
            is_present
            and row.get("valid_json") is True
            and row.get("self_finalization_allowed") is True
            and row_failure is None
        )
        present_count += int(is_present)
        passed_count += int(is_passed)
        evidence[label] = {
            "path": row.get("path"),
            "path_label": row.get("path_label"),
            "sha256": row.get("sha256"),
            "present": is_present,
            "passed": is_passed,
            "failure": row_failure,
            "self_finalization_allowed": row.get("self_finalization_allowed"),
        }
    required_labels = check.get("required_labels")
    required_count = (
        len(required_labels) if isinstance(required_labels, list) else len(rows)
    )
    return {
        "passed": bool(check.get("passed", False)),
        "required_count": required_count,
        "label_count": required_count,
        "present_count": present_count,
        "passed_count": passed_count,
        "evidence": evidence,
    }


def _find_evidence_row(
    check: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    rows = check.get("rows")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict) and row.get("label") == label:
            return row
    return {}


def _evidence_row_passed(row: dict[str, Any]) -> bool:
    return (
        row.get("exists") is True
        and row.get("valid_json") is True
        and row.get("passed_value") is True
        and row.get("failures_value") == []
        and "failure" not in row
    )


def _evidence_row_sha256(row: dict[str, Any]) -> str | None:
    value = row.get("sha256")
    return value if isinstance(value, str) and len(value) == 64 else None


def _arg_slot_mirror_field_coverage(payload: dict[str, Any]) -> list[str]:
    field = payload.get(
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
    )
    if (
        payload.get("future_kernel_native_arg_slot_consumer_single_field_mirror_checked")
        is True
        and _int_metric(
            payload,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count",
        )
        == 0
        and isinstance(field, str)
        and field in ARG_SLOT_MIRROR_FIELDS
    ):
        return [field]
    return []


def _future_kernel_args_mirror_field_coverage(payload: dict[str, Any]) -> list[str]:
    field = payload.get("future_kernel_consumer_args_single_field_mirror_field_name")
    if (
        payload.get("future_kernel_consumer_args_single_field_mirror_checked") is True
        and _int_metric(
            payload,
            "future_kernel_consumer_args_single_field_mirror_error_count",
        )
        == 0
        and isinstance(field, str)
        and field in ARG_SLOT_MIRROR_FIELDS
    ):
        return [field]
    return []


def _load_evidence_payload_from_check(
    check: dict[str, Any],
    label: str,
    *,
    root: Path,
) -> dict[str, Any]:
    row = _find_evidence_row(check, label)
    raw_path = row.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return {}
    path = _path_for_label(raw_path, root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_json_object_path(raw_path: Any, *, root: Path) -> dict[str, Any]:
    if not isinstance(raw_path, str) or not raw_path:
        return {}
    path = _path_for_label(raw_path, root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_context_identity(
    context: dict[str, Any],
    *,
    row_span_by_source_index: dict[int, dict[str, Any]],
) -> str | None:
    request_id = context.get("request_id")
    sequence_id = context.get("sequence_id")
    token_index = context.get("token_index")
    layer_id = context.get("layer_id")
    row_count = context.get("row_count")
    if not isinstance(request_id, str) or not request_id:
        return None
    if sequence_id is None:
        return None
    source_index = context.get("source_index")
    try:
        source_index_int = int(source_index)
    except (TypeError, ValueError):
        return None
    row_span = row_span_by_source_index.get(source_index_int, {})
    source_schema_hash = row_span.get("source_schema_hash")
    source_table_object_hash = row_span.get("source_table_object_hash")
    if not isinstance(source_schema_hash, str) or not source_schema_hash:
        return None
    if not isinstance(source_table_object_hash, str) or not source_table_object_hash:
        return None
    try:
        return json.dumps(
            [
                str(request_id),
                str(sequence_id),
                int(token_index),
                int(layer_id),
                int(row_count),
                source_schema_hash,
                source_table_object_hash,
            ],
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return None


def _source_context_identities_from_merged_output(
    payload: dict[str, Any],
    *,
    root: Path,
) -> list[str]:
    merged = _load_json_object_path(payload.get("merged_output_json"), root=root)
    merge_context = merged.get("_merge_context")
    if not isinstance(merge_context, dict):
        return []
    raw_contexts = merge_context.get("source_contexts")
    if not isinstance(raw_contexts, list):
        return []
    raw_row_spans = merge_context.get("row_spans")
    row_span_by_source_index: dict[int, dict[str, Any]] = {}
    if isinstance(raw_row_spans, list):
        for row_span in raw_row_spans:
            if not isinstance(row_span, dict):
                continue
            try:
                source_index = int(row_span.get("source_index"))
            except (TypeError, ValueError):
                continue
            row_span_by_source_index[source_index] = row_span
    identities: list[str] = []
    for context in raw_contexts:
        if not isinstance(context, dict):
            continue
        identity = _source_context_identity(
            context,
            row_span_by_source_index=row_span_by_source_index,
        )
        if identity is not None:
            identities.append(identity)
    return identities


def _source_context_count_from_merged_output(
    payload: dict[str, Any],
    *,
    root: Path,
) -> int | None:
    merged = _load_json_object_path(payload.get("merged_output_json"), root=root)
    merge_context = merged.get("_merge_context")
    if not isinstance(merge_context, dict):
        return None
    raw_contexts = merge_context.get("source_contexts")
    if not isinstance(raw_contexts, list):
        return None
    return len([context for context in raw_contexts if isinstance(context, dict)])


def _source_identity_digest(identities: list[str]) -> str | None:
    if not identities:
        return None
    data = json.dumps(identities, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _source_identity_subset(
    child: list[str],
    parent: list[str],
) -> tuple[bool | None, int | None]:
    if not child or not parent:
        return None, None
    remaining: dict[str, int] = {}
    for identity in parent:
        remaining[identity] = remaining.get(identity, 0) + 1
    missing = 0
    for identity in child:
        count = remaining.get(identity, 0)
        if count <= 0:
            missing += 1
        else:
            remaining[identity] = count - 1
    return missing == 0, missing


def _check_risky_canary_gate_metadata(
    gate_path: str,
    *,
    root: Path,
) -> dict[str, Any]:
    path = _path_for_label(gate_path, root)
    label = _path_label(path, root=root)
    if not path.exists():
        return {
            "gate_path": label,
            "passed": True,
            "skipped": True,
            "failures": [],
            "required_metadata": dict(REQUIRED_RISKY_CANARY_METADATA),
        }
    failures: list[str] = []
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "gate_path": label,
            "passed": False,
            "skipped": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "required_metadata": dict(REQUIRED_RISKY_CANARY_METADATA),
        }
    payload = payload or {}
    for key, expected in REQUIRED_RISKY_CANARY_METADATA.items():
        actual = payload.get(key)
        if actual != expected:
            failures.append(f"{key}_mismatch")
    return {
        "gate_path": label,
        "passed": not failures,
        "skipped": False,
        "failures": failures,
        "required_metadata": dict(REQUIRED_RISKY_CANARY_METADATA),
    }


def _has_explicit_risky_trace_canary_marker(shadow: dict[str, Any]) -> bool:
    explicit_marker = shadow.get("premap_risky_trace_canary") is True
    explicit_scope = shadow.get("premap_risky_trace_canary_scope")
    return explicit_marker and isinstance(explicit_scope, str) and bool(explicit_scope)


def _check_risky_trace_config(
    config_path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    config_path = config_path if config_path.is_absolute() else root / config_path
    label = _path_label(config_path, root=root)
    failures: list[str] = []
    try:
        config = _load_yaml(config_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "config_path": label,
            "passed": False,
            "skipped": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
        }
    config = config or {}
    trace = (config.get("trace") or {}) if isinstance(config, dict) else {}
    shadow = trace.get("runtime_shadow") or {}
    risky_flags = {
        flag: bool(shadow.get(flag, False)) for flag in sorted(RISKY_TRACE_FLAGS)
    }
    enabled_flags = [flag for flag, enabled in risky_flags.items() if enabled]
    if not enabled_flags:
        return {
            "config_path": label,
            "passed": True,
            "skipped": True,
            "failures": [],
            "risky_flags": risky_flags,
            "enabled_risky_flags": enabled_flags,
        }

    readonly_gate = shadow.get("premap_consumer_readonly_gate_path")
    readonly_gate_label = None
    gate_metadata: dict[str, Any] | None = None
    if not isinstance(readonly_gate, str) or not readonly_gate:
        failures.append("risky_trace_missing_readonly_gate_path")
    else:
        gate_path = _path_for_label(readonly_gate, root)
        readonly_gate_label = _path_label(gate_path, root=root)
        try:
            gate_payload = _load_yaml(gate_path) or {}
        except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
            failures.append(f"risky_gate_load_failed:{type(exc).__name__}:{exc}")
            gate_payload = {}
        gate_metadata = {
            key: gate_payload.get(key) for key in REQUIRED_RISKY_CANARY_METADATA
        }
        for key, expected in REQUIRED_RISKY_CANARY_METADATA.items():
            if gate_payload.get(key) != expected:
                failures.append(f"risky_gate_{key}_mismatch")

    explicit_marker = shadow.get("premap_risky_trace_canary") is True
    explicit_scope = shadow.get("premap_risky_trace_canary_scope")
    if explicit_marker and not (isinstance(explicit_scope, str) and explicit_scope):
        failures.append("risky_trace_canary_scope_missing")
    if not _has_explicit_risky_trace_canary_marker(shadow):
        failures.append("risky_trace_canary_marker_missing")

    return {
        "config_path": label,
        "passed": not failures,
        "skipped": False,
        "failures": failures,
        "risky_flags": risky_flags,
        "enabled_risky_flags": enabled_flags,
        "readonly_gate_path": readonly_gate,
        "readonly_gate_path_label": readonly_gate_label,
        "required_gate_metadata": dict(REQUIRED_RISKY_CANARY_METADATA),
        "gate_metadata": gate_metadata,
        "premap_risky_trace_canary": explicit_marker,
        "premap_risky_trace_canary_scope": explicit_scope,
    }


def _check_risky_trace_configs(
    trace_pattern: str,
    *,
    root: Path,
) -> list[dict[str, Any]]:
    return [
        _check_risky_trace_config(path, root=root)
        for path in sorted(root.glob(trace_pattern))
        if path.is_file()
    ]


def run_premap_lab_preflight(
    *,
    root: Path,
    runtime_pattern: str = "configs/runtime/*.yaml",
    trace_pattern: str = "configs/trace/*.yaml",
    trace_configs: list[str] | None = None,
    default_readonly_gate: str = DEFAULT_READONLY_GATE,
    canary_gate: str = DEFAULT_CANARY_GATE,
    prefetch_lab_default_gate: str = DEFAULT_PREFETCH_LAB_DEFAULT_GATE,
    risky_canary_gates: list[str] | None = None,
    allow_missing_evidence: bool = False,
    defer_online_prelaunch_runner_evidence: bool = False,
    defer_online_prelaunch_artifact_evidence: bool = False,
    allow_bootstrap_preflight: bool = False,
    allow_online_runner_self_finalization: bool = False,
    require_program_view_ptr_abi: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    trace_configs = trace_configs or list(DEFAULT_TRACE_CONFIGS)
    risky_canary_gates = (
        list(RISKY_CANARY_GATES)
        if risky_canary_gates is None
        else list(risky_canary_gates)
    )
    gate_pair_failures: list[str] = []
    default_gate_path = _path_label(
        _path_for_label(default_readonly_gate, root),
        root=root,
    )
    canary_gate_path = _path_label(_path_for_label(canary_gate, root), root=root)
    if default_gate_path == canary_gate_path:
        gate_pair_failures.append("default_readonly_gate_equals_canary_gate")
    if (
        defer_online_prelaunch_artifact_evidence
        and not defer_online_prelaunch_runner_evidence
    ):
        gate_pair_failures.append(
            "defer_online_prelaunch_artifact_evidence_requires_runner_defer"
        )
    if (
        defer_online_prelaunch_runner_evidence
        and defer_online_prelaunch_artifact_evidence
        and not allow_bootstrap_preflight
    ):
        gate_pair_failures.append(
            "defer_online_prelaunch_runner_and_artifact_evidence_not_allowed"
        )
    default_gate_contract_check = _check_default_gate_contract(
        default_readonly_gate,
        root=root,
    )
    default_kernel_consumer_schema_check = _check_default_kernel_consumer_schema(
        default_readonly_gate,
        root=root,
    )
    try:
        prefetch_lab_default_gate_check = check_prefetch_lab_default_gate(
            _path_for_label(prefetch_lab_default_gate, root),
            root=root,
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        prefetch_lab_default_gate_check = {
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
            "gate_id": None,
            "decisions": {},
            "sections": {},
        }
    deferred_evidence_labels: set[str] = set()
    if defer_online_prelaunch_runner_evidence:
        deferred_evidence_labels.update(ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABELS)
    if defer_online_prelaunch_artifact_evidence:
        deferred_evidence_labels.update(ONLINE_PRELAUNCH_ARTIFACT_EVIDENCE_LABELS)

    default_gate_required_evidence_check = _check_required_default_gate_evidence_json(
        default_readonly_gate,
        root=root,
        allow_missing=allow_missing_evidence,
        defer_online_prelaunch_runner_evidence=(
            defer_online_prelaunch_runner_evidence
        ),
        defer_online_prelaunch_artifact_evidence=(
            defer_online_prelaunch_artifact_evidence
        ),
        allow_online_runner_self_finalization=(
            allow_online_runner_self_finalization
        ),
    )
    default_gate_optional_evidence_check = _check_optional_default_gate_evidence_json(
        default_readonly_gate,
        root=root,
        deferred_labels=deferred_evidence_labels,
        allow_online_runner_self_finalization=(
            allow_online_runner_self_finalization
        ),
    )
    risky_canary_metadata_checks = {
        _path_label(_path_for_label(raw_path, root), root=root): (
            _check_risky_canary_gate_metadata(raw_path, root=root)
        )
        for raw_path in risky_canary_gates
    }
    runtime_scan = scan_runtime_gate_evidence_paths(
        runtime_pattern,
        root=root,
        allow_missing=allow_missing_evidence,
        allow_missing_section=True,
        require_json=True,
        deferred_labels=deferred_evidence_labels,
    )
    strict_gate_checks: dict[str, Any] = {}
    for label, raw_path in {
        "default_readonly_gate": default_readonly_gate,
        "connected_blocked_canary_gate": canary_gate,
    }.items():
        try:
            strict_gate_checks[label] = check_gate_evidence_paths(
                Path(raw_path),
                root=root,
                allow_missing=allow_missing_evidence,
                allow_missing_section=False,
                require_json=True,
                deferred_labels=deferred_evidence_labels,
            )
        except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
            strict_gate_checks[label] = {
                "gate_path": _path_label(_path_for_label(raw_path, root), root=root),
                "passed": False,
                "failures": [f"{type(exc).__name__}:{exc}"],
            }

    trace_results = [
        _check_trace_config(
            Path(config_path),
            root=root,
            expected_readonly_gate=default_readonly_gate,
        )
        for config_path in trace_configs
    ]
    risky_trace_config_checks = _check_risky_trace_configs(
        trace_pattern,
        root=root,
    )
    failures: list[str] = []
    failures.extend(gate_pair_failures)
    if not runtime_scan.get("passed", False):
        failures.append("runtime_gate_evidence_scan_failed")
    if not default_gate_contract_check.get("passed", False):
        failures.append("default_readonly_gate_contract_check_failed")
    if not default_kernel_consumer_schema_check.get("passed", False):
        failures.append("default_kernel_consumer_schema_check_failed")
    if not prefetch_lab_default_gate_check.get("passed", False):
        failures.append("prefetch_lab_default_gate_check_failed")
    if not default_gate_required_evidence_check.get("passed", False):
        failures.append("default_readonly_gate_required_evidence_check_failed")
    if not default_gate_optional_evidence_check.get("passed", False):
        failures.append("default_readonly_gate_optional_evidence_check_failed")
    for label, result in risky_canary_metadata_checks.items():
        if not result.get("passed", False):
            failures.append(f"{label}:risky_canary_metadata_check_failed")
    for label, result in strict_gate_checks.items():
        if not result.get("passed", False):
            failures.append(f"{label}_evidence_check_failed")
    for result in trace_results:
        if not result.get("passed", False):
            failures.append(f"{result['config_path']}:trace_config_check_failed")
    for result in risky_trace_config_checks:
        if not result.get("passed", False):
            failures.append(f"{result['config_path']}:risky_trace_config_check_failed")

    evidence_summary = _summarize_required_evidence_check(
        default_gate_required_evidence_check
    )
    dispatch_runner_evidence_label = (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json"
    )
    dispatch_runner_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        dispatch_runner_evidence_label,
    )
    dispatch_runner_evidence_present = (
        dispatch_runner_evidence_row.get("exists") is True
    )
    dispatch_runner_evidence_passed = (
        dispatch_runner_evidence_present
        and dispatch_runner_evidence_row.get("valid_json") is True
        and dispatch_runner_evidence_row.get("passed_value") is True
        and dispatch_runner_evidence_row.get("failures_value") == []
        and "failure" not in dispatch_runner_evidence_row
    )
    dispatch_runner_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        dispatch_runner_evidence_label,
        root=root,
    )
    dispatch_runner_artifact_evidence_label = (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json"
    )
    dispatch_runner_artifact_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        dispatch_runner_artifact_evidence_label,
    )
    dispatch_runner_artifact_evidence_present = (
        dispatch_runner_artifact_evidence_row.get("exists") is True
    )
    dispatch_runner_artifact_evidence_passed = (
        dispatch_runner_artifact_evidence_present
        and dispatch_runner_artifact_evidence_row.get("valid_json") is True
        and dispatch_runner_artifact_evidence_row.get("passed_value") is True
        and dispatch_runner_artifact_evidence_row.get("failures_value") == []
        and "failure" not in dispatch_runner_artifact_evidence_row
    )
    dispatch_runner_artifact_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        dispatch_runner_artifact_evidence_label,
        root=root,
    )
    dispatch_ptr_standalone_evidence_label = (
        "future_kernel_native_dispatch_ptr_standalone_canary_json"
    )
    dispatch_ptr_standalone_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        dispatch_ptr_standalone_evidence_label,
    )
    dispatch_ptr_standalone_evidence_present = (
        dispatch_ptr_standalone_evidence_row.get("exists") is True
    )
    dispatch_ptr_standalone_evidence_passed = (
        dispatch_ptr_standalone_evidence_present
        and dispatch_ptr_standalone_evidence_row.get("valid_json") is True
        and dispatch_ptr_standalone_evidence_row.get("passed_value") is True
        and dispatch_ptr_standalone_evidence_row.get("failures_value") == []
        and "failure" not in dispatch_ptr_standalone_evidence_row
    )
    dispatch_ptr_standalone_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        dispatch_ptr_standalone_evidence_label,
        root=root,
    )
    arg_slot_standalone_evidence_label = (
        "future_kernel_native_arg_slot_standalone_canary_json"
    )
    arg_slot_standalone_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        arg_slot_standalone_evidence_label,
    )
    arg_slot_standalone_evidence_present = (
        arg_slot_standalone_evidence_row.get("exists") is True
    )
    arg_slot_standalone_evidence_passed = (
        arg_slot_standalone_evidence_present
        and arg_slot_standalone_evidence_row.get("valid_json") is True
        and arg_slot_standalone_evidence_row.get("passed_value") is True
        and arg_slot_standalone_evidence_row.get("failures_value") == []
        and "failure" not in arg_slot_standalone_evidence_row
    )
    arg_slot_standalone_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        arg_slot_standalone_evidence_label,
        root=root,
    )
    dispatch_runner_summary = dispatch_runner_payload.get(
        "future_kernel_native_consumer_dispatch_stub_summary",
    )
    if not isinstance(dispatch_runner_summary, dict):
        dispatch_runner_summary = {}
    arg_slot_online_mirror_field_coverage = _arg_slot_mirror_field_coverage(
        dispatch_runner_summary
    )
    arg_slot_online_diagnostic_mirror_field_coverage: list[str] = []
    arg_slot_online_diagnostic_summary_keys: list[str] = []
    for field, summary_key in ARG_SLOT_ONLINE_DIAGNOSTIC_SUMMARY_KEY_BY_FIELD.items():
        summary = dispatch_runner_payload.get(summary_key)
        if not isinstance(summary, dict):
            continue
        if _arg_slot_mirror_field_coverage(summary) == [field]:
            arg_slot_online_diagnostic_mirror_field_coverage.append(field)
            arg_slot_online_diagnostic_summary_keys.append(summary_key)
    arg_slot_online_total_mirror_field_coverage = sorted(
        set(arg_slot_online_mirror_field_coverage)
        | set(arg_slot_online_diagnostic_mirror_field_coverage)
    )
    arg_slot_online_merged_required_mirror_field_coverage: list[str] = []
    arg_slot_online_merged_required_mirror_evidence_labels: list[str] = []
    for (
        field,
        label,
    ) in ARG_SLOT_ONLINE_MERGED_REQUIRED_MIRROR_RUNNER_LABEL_BY_FIELD.items():
        row = _find_evidence_row(default_gate_required_evidence_check, label)
        if not _evidence_row_passed(row):
            continue
        payload = _load_evidence_payload_from_check(
            default_gate_required_evidence_check,
            label,
            root=root,
        )
        summary = payload.get("stub_summary")
        if not isinstance(summary, dict):
            continue
        if _arg_slot_mirror_field_coverage(summary) == [field]:
            arg_slot_online_merged_required_mirror_field_coverage.append(field)
            arg_slot_online_merged_required_mirror_evidence_labels.append(label)
    arg_slot_online_merged_optional_mirror_field_coverage: list[str] = []
    arg_slot_online_merged_optional_mirror_evidence_labels: list[str] = []
    for (
        field,
        label,
    ) in ARG_SLOT_ONLINE_MERGED_OPTIONAL_MIRROR_RUNNER_LABEL_BY_FIELD.items():
        row = _find_evidence_row(default_gate_optional_evidence_check, label)
        if not _evidence_row_passed(row):
            continue
        payload = _load_evidence_payload_from_check(
            default_gate_optional_evidence_check,
            label,
            root=root,
        )
        summary = payload.get("stub_summary")
        if not isinstance(summary, dict):
            continue
        if _arg_slot_mirror_field_coverage(summary) == [field]:
            arg_slot_online_merged_optional_mirror_field_coverage.append(field)
            arg_slot_online_merged_optional_mirror_evidence_labels.append(label)
    online_merged_multiprogram_runner_evidence_label = (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json"
    )
    online_merged_multiprogram_runner_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        online_merged_multiprogram_runner_evidence_label,
    )
    online_merged_multiprogram_runner_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        online_merged_multiprogram_runner_evidence_label,
        root=root,
    )
    wna16_adjacent_typed_slot_evidence_label = (
        "future_kernel_wna16_adjacent_typed_slot_canary_json"
    )
    wna16_adjacent_typed_slot_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        wna16_adjacent_typed_slot_evidence_label,
    )
    wna16_adjacent_typed_slot_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        wna16_adjacent_typed_slot_evidence_label,
        root=root,
    )
    wna16_side_variant_evidence_label = (
        "wna16_side_consumer_variant_execution_128strict_runner_json"
    )
    wna16_side_variant_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        wna16_side_variant_evidence_label,
    )
    wna16_side_variant_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        wna16_side_variant_evidence_label,
        root=root,
    )
    fourth_field_handoff_evidence_label = (
        "future_wna16_typed_slot_fourth_field_handoff_canary_json"
    )
    fourth_field_handoff_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        fourth_field_handoff_evidence_label,
    )
    fourth_field_handoff_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        fourth_field_handoff_evidence_label,
        root=root,
    )
    all_four_field_consumer_evidence_label = (
        "future_wna16_typed_slot_all_four_field_consumer_json"
    )
    all_four_field_consumer_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        all_four_field_consumer_evidence_label,
    )
    all_four_field_consumer_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        all_four_field_consumer_evidence_label,
        root=root,
    )
    future_wna16_kernel_side_path_evidence_label = (
        "future_wna16_kernel_side_typed_consumer_path_json"
    )
    future_wna16_kernel_side_path_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        future_wna16_kernel_side_path_evidence_label,
    )
    future_wna16_kernel_side_path_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        future_wna16_kernel_side_path_evidence_label,
        root=root,
    )
    future_wna16_payloadless_execution_evidence_label = (
        "future_wna16_typed_slot_payloadless_execution_json"
    )
    future_wna16_payloadless_execution_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        future_wna16_payloadless_execution_evidence_label,
    )
    future_wna16_payloadless_execution_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        future_wna16_payloadless_execution_evidence_label,
        root=root,
    )
    future_wna16_variant_execution_evidence_label = (
        "future_wna16_typed_slot_kernel_variant_execution_json"
    )
    future_wna16_variant_execution_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        future_wna16_variant_execution_evidence_label,
    )
    future_wna16_variant_execution_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        future_wna16_variant_execution_evidence_label,
        root=root,
    )
    future_wna16_useful_consumer_evidence_label = (
        "future_wna16_typed_slot_kernel_variant_useful_consumer_json"
    )
    future_wna16_useful_consumer_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        future_wna16_useful_consumer_evidence_label,
    )
    future_wna16_useful_consumer_payload = _load_evidence_payload_from_check(
        default_gate_required_evidence_check,
        future_wna16_useful_consumer_evidence_label,
        root=root,
    )
    future_wna16_useful_consumer_timing_payload: dict[str, Any] = {}
    future_wna16_useful_consumer_timing_json = (
        future_wna16_useful_consumer_payload.get("native_timing_json")
    )
    if (
        isinstance(future_wna16_useful_consumer_timing_json, str)
        and future_wna16_useful_consumer_timing_json
    ):
        future_wna16_useful_consumer_timing_payload = _load_json_object_path(
            future_wna16_useful_consumer_timing_json,
            root=root,
        )
    future_wna16_payloadless_useful_execution_evidence_label = (
        "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json"
    )
    future_wna16_payloadless_useful_execution_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        future_wna16_payloadless_useful_execution_evidence_label,
    )
    future_wna16_payloadless_useful_execution_payload = (
        _load_evidence_payload_from_check(
            default_gate_required_evidence_check,
            future_wna16_payloadless_useful_execution_evidence_label,
            root=root,
        )
    )
    future_wna16_payloadless_useful_repeat_benchmark_evidence_label = (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json"
    )
    future_wna16_payloadless_useful_repeat_benchmark_evidence_row = _find_evidence_row(
        default_gate_required_evidence_check,
        future_wna16_payloadless_useful_repeat_benchmark_evidence_label,
    )
    future_wna16_payloadless_useful_repeat_benchmark_payload = (
        _load_evidence_payload_from_check(
            default_gate_required_evidence_check,
            future_wna16_payloadless_useful_repeat_benchmark_evidence_label,
            root=root,
        )
    )
    all_four_field_consumer_fourth_field_json = (
        all_four_field_consumer_payload.get("fourth_field_json")
    )
    all_four_field_consumer_fourth_field_path_label = (
        _path_label(
            _path_for_label(all_four_field_consumer_fourth_field_json, root),
            root=root,
        )
        if isinstance(all_four_field_consumer_fourth_field_json, str)
        and all_four_field_consumer_fourth_field_json
        else None
    )
    future_wna16_kernel_side_path_all_four_json = (
        future_wna16_kernel_side_path_payload.get("all_four_json")
    )
    future_wna16_kernel_side_path_all_four_path_label = (
        _path_label(
            _path_for_label(future_wna16_kernel_side_path_all_four_json, root),
            root=root,
        )
        if isinstance(future_wna16_kernel_side_path_all_four_json, str)
        and future_wna16_kernel_side_path_all_four_json
        else None
    )
    wna16_side_variant_stub_summary = wna16_side_variant_payload.get("stub_summary")
    if not isinstance(wna16_side_variant_stub_summary, dict):
        wna16_side_variant_stub_summary = {}
    online_merged_multiprogram_source_context_count = (
        _source_context_count_from_merged_output(
            online_merged_multiprogram_runner_payload,
            root=root,
        )
    )
    wna16_side_variant_source_context_count = (
        _source_context_count_from_merged_output(
            wna16_side_variant_payload,
            root=root,
        )
    )
    online_merged_multiprogram_source_identities = (
        _source_context_identities_from_merged_output(
            online_merged_multiprogram_runner_payload,
            root=root,
        )
    )
    wna16_side_variant_source_identities = (
        _source_context_identities_from_merged_output(
            wna16_side_variant_payload,
            root=root,
        )
    )
    (
        wna16_side_variant_source_identity_subset,
        wna16_side_variant_source_identity_missing_count,
    ) = _source_identity_subset(
        online_merged_multiprogram_source_identities,
        wna16_side_variant_source_identities,
    )
    arg_slot_standalone_mirror_field_coverage = _arg_slot_mirror_field_coverage(
        arg_slot_standalone_payload
    )
    arg_slot_required_mirror_field_coverage: list[str] = []
    arg_slot_required_mirror_evidence_labels: list[str] = []
    for field, label in ARG_SLOT_REQUIRED_MIRROR_LABEL_BY_FIELD.items():
        row = _find_evidence_row(default_gate_required_evidence_check, label)
        if not _evidence_row_passed(row):
            continue
        payload = _load_evidence_payload_from_check(
            default_gate_required_evidence_check,
            label,
            root=root,
        )
        if _arg_slot_mirror_field_coverage(payload) == [field]:
            arg_slot_required_mirror_field_coverage.append(field)
            arg_slot_required_mirror_evidence_labels.append(label)
    arg_slot_optional_mirror_field_coverage: list[str] = []
    arg_slot_optional_mirror_evidence_labels: list[str] = []
    for field, label in ARG_SLOT_OPTIONAL_MIRROR_LABEL_BY_FIELD.items():
        row = _find_evidence_row(default_gate_optional_evidence_check, label)
        if not _evidence_row_passed(row):
            continue
        payload = _load_evidence_payload_from_check(
            default_gate_optional_evidence_check,
            label,
            root=root,
        )
        if _arg_slot_mirror_field_coverage(payload) == [field]:
            arg_slot_optional_mirror_field_coverage.append(field)
            arg_slot_optional_mirror_evidence_labels.append(label)
    arg_slot_total_mirror_field_coverage = sorted(
        set(arg_slot_standalone_mirror_field_coverage)
        | set(arg_slot_required_mirror_field_coverage)
        | set(arg_slot_optional_mirror_field_coverage)
        | set(arg_slot_online_merged_required_mirror_field_coverage)
        | set(arg_slot_online_merged_optional_mirror_field_coverage)
    )
    future_kernel_args_runner_summary = dispatch_runner_payload.get(
        "future_kernel_args_stub_summary",
    )
    if not isinstance(future_kernel_args_runner_summary, dict):
        future_kernel_args_runner_summary = {}
    future_kernel_args_mirror_field_coverage = (
        _future_kernel_args_mirror_field_coverage(future_kernel_args_runner_summary)
    )
    future_kernel_args_optional_mirror_field_coverage: list[str] = []
    future_kernel_args_optional_mirror_evidence_labels: list[str] = []
    for field, label in FUTURE_KERNEL_ARGS_OPTIONAL_MIRROR_LABEL_BY_FIELD.items():
        row = _find_evidence_row(default_gate_optional_evidence_check, label)
        if not _evidence_row_passed(row):
            continue
        payload = _load_evidence_payload_from_check(
            default_gate_optional_evidence_check,
            label,
            root=root,
        )
        if _future_kernel_args_mirror_field_coverage(payload) == [field]:
            future_kernel_args_optional_mirror_field_coverage.append(field)
            future_kernel_args_optional_mirror_evidence_labels.append(label)
    future_kernel_args_total_mirror_field_coverage = sorted(
        set(future_kernel_args_mirror_field_coverage)
        | set(future_kernel_args_optional_mirror_field_coverage)
    )
    observed_default_contract = default_gate_contract_check.get("observed_contract")
    if not isinstance(observed_default_contract, dict):
        observed_default_contract = {}

    def _observed_default_contract_value(key: str) -> Any | None:
        if key in observed_default_contract:
            value = observed_default_contract[key]
            expected = REQUIRED_DEFAULT_GATE_CONTRACT.get(key)
            if expected is None:
                return None
            if isinstance(expected, bool):
                return value if isinstance(value, bool) else None
            if isinstance(expected, int):
                return (
                    value
                    if isinstance(value, int) and not isinstance(value, bool)
                    else None
                )
            if isinstance(expected, str):
                return value if isinstance(value, str) else None
            return value
        return None

    arg_slot_online_total_mirror_coverage_required = (
        observed_default_contract.get(
            "future_kernel_native_arg_slot_online_total_mirror_coverage_required"
        )
        is True
    )
    future_kernel_args_total_mirror_coverage_required = (
        observed_default_contract.get(
            "future_kernel_consumer_args_total_mirror_coverage_required"
        )
        is True
    )
    if (
        arg_slot_online_total_mirror_coverage_required
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and set(arg_slot_online_total_mirror_field_coverage)
        != set(ARG_SLOT_MIRROR_FIELDS)
    ):
        failures.append(
            "default_kernel_consumer_arg_slot_online_total_mirror_coverage_incomplete"
        )
    if (
        future_kernel_args_total_mirror_coverage_required
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and set(future_kernel_args_total_mirror_field_coverage)
        != set(ARG_SLOT_MIRROR_FIELDS)
    ):
        failures.append(
            "default_kernel_consumer_future_kernel_args_total_mirror_coverage_incomplete"
        )
    dispatch_runner_final_status_summary = dispatch_runner_payload.get(
        "final_preflight_status_summary",
    )
    if not isinstance(dispatch_runner_final_status_summary, dict):
        dispatch_runner_final_status_summary = {}
    dispatch_row_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_row_count",
    )
    dispatch_row_ok_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_row_ok_count",
    )
    dispatch_active_rows = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_active_rows",
    )
    dispatch_row_offset = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_row_offset",
    )
    dispatch_row_limit = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_row_limit",
    )
    dispatch_full_table_checked = (
        dispatch_row_count is not None
        and dispatch_row_offset == 0
        and dispatch_row_limit == dispatch_row_count
        and dispatch_active_rows == dispatch_row_count
    )
    dispatch_ptr_row_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_ptr_consumer_row_count",
    )
    dispatch_ptr_row_ok_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
    )
    dispatch_ptr_mirror_row_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count",
    )
    dispatch_ptr_mirror_row_ok_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count",
    )
    arg_slot_row_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_arg_slot_consumer_row_count",
    )
    arg_slot_row_ok_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_arg_slot_consumer_row_ok_count",
    )
    arg_slot_mirror_row_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
    )
    arg_slot_mirror_row_ok_count = _int_metric(
        dispatch_runner_summary,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    )
    schema_summary = (
        default_kernel_consumer_schema_check.get("schema_check")
        if isinstance(default_kernel_consumer_schema_check.get("schema_check"), dict)
        else default_kernel_consumer_schema_check
    )
    schema_row_field_names = schema_summary.get("row_field_names")
    if not isinstance(schema_row_field_names, list):
        schema_row_field_names = []
    future_kernel_args_layout_expected = schema_summary.get(
        "future_kernel_consumer_args_layout_expected",
    )
    if not isinstance(future_kernel_args_layout_expected, dict):
        future_kernel_args_layout_expected = {}
    kernel_arg_packet_layout_expected = schema_summary.get(
        "future_kernel_native_consumer_kernel_arg_packet_abi_layout_expected",
    )
    if not isinstance(kernel_arg_packet_layout_expected, dict):
        kernel_arg_packet_layout_expected = {}
    kernel_entry_summary_layout_expected = schema_summary.get(
        "future_kernel_native_consumer_kernel_entry_summary_abi_layout_expected",
    )
    if not isinstance(kernel_entry_summary_layout_expected, dict):
        kernel_entry_summary_layout_expected = {}
    kernel_entry_args_layout_expected = schema_summary.get(
        "future_kernel_native_consumer_kernel_entry_args_abi_layout_expected",
    )
    if not isinstance(kernel_entry_args_layout_expected, dict):
        kernel_entry_args_layout_expected = {}
    required_gate_checks = schema_summary.get("required_gate_checks")
    if not isinstance(required_gate_checks, dict):
        required_gate_checks = {}
    online_merged_arg_slot_summary = online_merged_multiprogram_runner_payload.get(
        "stub_summary",
    )
    if not isinstance(online_merged_arg_slot_summary, dict):
        online_merged_arg_slot_summary = dispatch_runner_summary
    arg_slot_field_read_row_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_arg_slot_consumer_row_count",
    )
    arg_slot_field_read_row_ok_counts: dict[str, int | None] = {}
    arg_slot_field_read_error_counts: dict[str, int | None] = {}
    arg_slot_field_read_hashes: dict[str, str | None] = {}
    for field in ARG_SLOT_MIRROR_FIELDS:
        prefix = f"future_kernel_native_arg_slot_consumer_{field}_read"
        arg_slot_field_read_row_ok_counts[field] = _int_metric(
            online_merged_arg_slot_summary,
            f"{prefix}_row_ok_count",
        )
        arg_slot_field_read_error_counts[field] = _int_metric(
            online_merged_arg_slot_summary,
            f"{prefix}_error_count",
        )
        hash_key = f"{prefix}_hash_accumulator"
        hash_value = online_merged_arg_slot_summary.get(hash_key)
        arg_slot_field_read_hashes[field] = (
            hash_value
            if isinstance(hash_value, str)
            and _hex64_metric(online_merged_arg_slot_summary, hash_key) is not None
            else None
        )
    arg_slot_all_handle_fields_read = (
        arg_slot_field_read_row_count is not None
        and all(
            arg_slot_field_read_row_ok_counts.get(field) == arg_slot_field_read_row_count
            and arg_slot_field_read_error_counts.get(field) == 0
            and arg_slot_field_read_hashes.get(field) is not None
            for field in ARG_SLOT_MIRROR_FIELDS
        )
    )
    kernel_entry_args_summary_row_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_consumer_kernel_entry_args_summary_row_count",
    )
    kernel_entry_args_summary_row_ok_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_consumer_kernel_entry_args_summary_row_ok_count",
    )
    kernel_entry_args_summary_descriptor_ptr_read_row_ok_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count",
    )
    kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count = (
        _int_metric(
            online_merged_arg_slot_summary,
            "future_kernel_native_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count",
        )
    )
    kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count = (
        _int_metric(
            online_merged_arg_slot_summary,
            "future_kernel_native_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count",
        )
    )
    kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count",
    )
    kernel_entry_args_summary_row_metadata_read_row_ok_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count",
    )
    kernel_entry_args_summary_error_count = _int_metric(
        online_merged_arg_slot_summary,
        "future_kernel_native_consumer_kernel_entry_args_summary_error_count",
    )
    kernel_entry_args_all_handle_fields_read = (
        kernel_entry_args_summary_row_count is not None
        and kernel_entry_args_summary_row_ok_count == kernel_entry_args_summary_row_count
        and kernel_entry_args_summary_descriptor_ptr_read_row_ok_count
        == kernel_entry_args_summary_row_count
        and kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count
        == kernel_entry_args_summary_row_count
        and kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count
        == kernel_entry_args_summary_row_count
        and kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count
        == kernel_entry_args_summary_row_count
        and kernel_entry_args_summary_row_metadata_read_row_ok_count
        == kernel_entry_args_summary_row_count
        and kernel_entry_args_summary_error_count == 0
    )
    request_ptr_summary_source = online_merged_arg_slot_summary
    if (
        request_ptr_summary_source.get(
            "future_kernel_native_consumer_request_ptr_checked"
        )
        is not True
    ):
        request_ptr_evidence_label = (
            "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json"
        )
        request_ptr_evidence_row = _find_evidence_row(
            default_gate_required_evidence_check,
            request_ptr_evidence_label,
        )
        if _evidence_row_passed(request_ptr_evidence_row):
            request_ptr_payload = _load_evidence_payload_from_check(
                default_gate_required_evidence_check,
                request_ptr_evidence_label,
                root=root,
            )
            if isinstance(request_ptr_payload, dict):
                request_ptr_summary_source = request_ptr_payload
    def _with_request_single_field_handoff_alias(
        source: dict[str, object],
        *,
        consumer_prefix: str,
        summary_prefix: str,
    ) -> dict[str, object]:
        row_count = _int_metric(source, f"{summary_prefix}_row_count")
        row_ok_count = _int_metric(
            source,
            f"{summary_prefix}_scale_metadata_handle_read_row_ok_count",
        )
        error_count = _int_metric(source, f"{summary_prefix}_error_count")
        handoff_error_count = (
            0
            if (
                row_count is not None
                and row_count > 0
                and row_ok_count == row_count
                and error_count == 0
            )
            else 1
        )
        annotated = dict(source)
        if annotated.get(f"{consumer_prefix}_single_field_handoff_checked") is not True:
            annotated[f"{consumer_prefix}_single_field_handoff_checked"] = True
            annotated[f"{consumer_prefix}_single_field_handoff_field_name"] = (
                "scale_metadata_handle"
            )
            annotated[f"{consumer_prefix}_single_field_handoff_source"] = (
                "native_request_summary_field_read_counts"
            )
            annotated[f"{consumer_prefix}_single_field_handoff_row_count"] = row_count
            annotated[f"{consumer_prefix}_single_field_handoff_row_ok_count"] = row_ok_count
            annotated[f"{consumer_prefix}_single_field_handoff_error_count"] = (
                handoff_error_count
            )
            annotated[f"{consumer_prefix}_single_field_handoff_hash_accumulator"] = (
                source.get(f"{summary_prefix}_field_read_hash_accumulator")
            )
            annotated[f"{consumer_prefix}_single_field_handoff_payload_bytes"] = 0
            annotated[f"{consumer_prefix}_single_field_handoff_passed_to_kernel"] = False
            annotated[
                f"{consumer_prefix}_single_field_handoff_changes_kernel_launch_args"
            ] = False
            annotated[
                f"{consumer_prefix}_single_field_handoff_current_wna16_arg_compatible"
            ] = False
            annotated[
                f"{consumer_prefix}_single_field_handoff_requires_wna16_arg_reinterpretation"
            ] = False
        source = annotated
        row_count = _int_metric(source, f"{summary_prefix}_row_count")
        error_count = _int_metric(source, f"{summary_prefix}_error_count")
        handoff_fields = (
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        )
        all_row_ok_counts = {
            field_name: _int_metric(
                source,
                f"{summary_prefix}_{field_name}_read_row_ok_count",
            )
            for field_name in handoff_fields
        }
        all_field_error_count = (
            0
            if (
                row_count is not None
                and row_count > 0
                and error_count == 0
                and all(value == row_count for value in all_row_ok_counts.values())
            )
            else 1
        )
        annotated[f"{consumer_prefix}_all_field_handoff_checked"] = True
        annotated[f"{consumer_prefix}_all_field_handoff_field_names"] = list(
            handoff_fields
        )
        annotated[f"{consumer_prefix}_all_field_handoff_source"] = (
            "native_request_summary_field_read_counts"
        )
        annotated[f"{consumer_prefix}_all_field_handoff_row_count"] = row_count
        annotated[f"{consumer_prefix}_all_field_handoff_row_ok_count"] = (
            row_count if all_field_error_count == 0 else None
        )
        annotated[f"{consumer_prefix}_all_field_handoff_error_count"] = (
            all_field_error_count
        )
        annotated[f"{consumer_prefix}_all_field_handoff_hash_accumulator"] = (
            source.get(f"{summary_prefix}_field_read_hash_accumulator")
        )
        annotated[f"{consumer_prefix}_all_field_handoff_payload_bytes"] = 0
        annotated[f"{consumer_prefix}_all_field_handoff_passed_to_kernel"] = False
        annotated[
            f"{consumer_prefix}_all_field_handoff_changes_kernel_launch_args"
        ] = False
        annotated[
            f"{consumer_prefix}_all_field_handoff_current_wna16_arg_compatible"
        ] = False
        annotated[
            f"{consumer_prefix}_all_field_handoff_requires_wna16_arg_reinterpretation"
        ] = False
        for field_name, row_ok_count in all_row_ok_counts.items():
            annotated[
                f"{consumer_prefix}_all_field_handoff_{field_name}_row_ok_count"
            ] = row_ok_count
        return annotated

    request_ptr_summary_source = _with_request_single_field_handoff_alias(
        request_ptr_summary_source,
        consumer_prefix="future_kernel_native_consumer_request_ptr",
        summary_prefix="future_kernel_native_consumer_request_ptr_summary",
    )
    request_ptr_summary_row_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_row_count",
    )
    request_ptr_summary_row_ok_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_row_ok_count",
    )
    request_ptr_summary_descriptor_ptr_read_row_ok_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count",
    )
    request_ptr_summary_packed_weight_descriptor_read_row_ok_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count",
    )
    request_ptr_summary_scale_metadata_handle_read_row_ok_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count",
    )
    request_ptr_summary_aux_metadata_handle_read_row_ok_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count",
    )
    request_ptr_summary_row_metadata_read_row_ok_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count",
    )
    request_ptr_summary_error_count = _int_metric(
        request_ptr_summary_source,
        "future_kernel_native_consumer_request_ptr_summary_error_count",
    )
    request_ptr_all_handle_fields_read = (
        request_ptr_summary_row_count is not None
        and request_ptr_summary_row_ok_count == request_ptr_summary_row_count
        and request_ptr_summary_descriptor_ptr_read_row_ok_count
        == request_ptr_summary_row_count
        and request_ptr_summary_packed_weight_descriptor_read_row_ok_count
        == request_ptr_summary_row_count
        and request_ptr_summary_scale_metadata_handle_read_row_ok_count
        == request_ptr_summary_row_count
        and request_ptr_summary_aux_metadata_handle_read_row_ok_count
        == request_ptr_summary_row_count
        and request_ptr_summary_row_metadata_read_row_ok_count
        == request_ptr_summary_row_count
        and request_ptr_summary_error_count == 0
    )
    request_launch_summary_source = online_merged_arg_slot_summary
    if (
        request_launch_summary_source.get(
            "future_kernel_native_consumer_request_launch_checked"
        )
        is not True
    ):
        request_launch_evidence_label = (
            "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json"
        )
        request_launch_evidence_row = _find_evidence_row(
            default_gate_required_evidence_check,
            request_launch_evidence_label,
        )
        if _evidence_row_passed(request_launch_evidence_row):
            request_launch_payload = _load_evidence_payload_from_check(
                default_gate_required_evidence_check,
                request_launch_evidence_label,
                root=root,
            )
            if isinstance(request_launch_payload, dict):
                request_launch_summary_source = request_launch_payload
    request_launch_summary_source = _with_request_single_field_handoff_alias(
        request_launch_summary_source,
        consumer_prefix="future_kernel_native_consumer_request_launch",
        summary_prefix="future_kernel_native_consumer_request_launch_summary",
    )
    request_launch_summary_row_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_row_count",
    )
    request_launch_summary_row_ok_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_row_ok_count",
    )
    request_launch_summary_descriptor_ptr_read_row_ok_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count",
    )
    request_launch_summary_packed_weight_descriptor_read_row_ok_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count",
    )
    request_launch_summary_scale_metadata_handle_read_row_ok_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count",
    )
    request_launch_summary_aux_metadata_handle_read_row_ok_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count",
    )
    request_launch_summary_row_metadata_read_row_ok_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_row_metadata_read_row_ok_count",
    )
    request_launch_summary_error_count = _int_metric(
        request_launch_summary_source,
        "future_kernel_native_consumer_request_launch_summary_error_count",
    )
    request_launch_all_handle_fields_read = (
        request_launch_summary_row_count is not None
        and request_launch_summary_row_ok_count == request_launch_summary_row_count
        and request_launch_summary_descriptor_ptr_read_row_ok_count
        == request_launch_summary_row_count
        and request_launch_summary_packed_weight_descriptor_read_row_ok_count
        == request_launch_summary_row_count
        and request_launch_summary_scale_metadata_handle_read_row_ok_count
        == request_launch_summary_row_count
        and request_launch_summary_aux_metadata_handle_read_row_ok_count
        == request_launch_summary_row_count
        and request_launch_summary_row_metadata_read_row_ok_count
        == request_launch_summary_row_count
        and request_launch_summary_error_count == 0
    )
    request_launch_ptr_summary_source = online_merged_arg_slot_summary
    if (
        request_launch_ptr_summary_source.get(
            "future_kernel_native_consumer_request_launch_ptr_checked"
        )
        is not True
    ):
        request_launch_ptr_evidence_label = (
            "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json"
        )
        request_launch_ptr_evidence_row = _find_evidence_row(
            default_gate_required_evidence_check,
            request_launch_ptr_evidence_label,
        )
        if _evidence_row_passed(request_launch_ptr_evidence_row):
            request_launch_ptr_payload = _load_evidence_payload_from_check(
                default_gate_required_evidence_check,
                request_launch_ptr_evidence_label,
                root=root,
            )
            if isinstance(request_launch_ptr_payload, dict):
                request_launch_ptr_summary_source = request_launch_ptr_payload
    request_launch_ptr_summary_source = _with_request_single_field_handoff_alias(
        request_launch_ptr_summary_source,
        consumer_prefix="future_kernel_native_consumer_request_launch_ptr",
        summary_prefix="future_kernel_native_consumer_request_launch_ptr_summary",
    )
    request_launch_ptr_summary_row_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_row_count",
    )
    request_launch_ptr_summary_row_ok_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_row_ok_count",
    )
    request_launch_ptr_summary_descriptor_ptr_read_row_ok_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_descriptor_ptr_read_row_ok_count",
    )
    request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count",
    )
    request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count",
    )
    request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count",
    )
    request_launch_ptr_summary_row_metadata_read_row_ok_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count",
    )
    request_launch_ptr_summary_error_count = _int_metric(
        request_launch_ptr_summary_source,
        "future_kernel_native_consumer_request_launch_ptr_summary_error_count",
    )
    request_launch_ptr_all_handle_fields_read = (
        request_launch_ptr_summary_row_count is not None
        and request_launch_ptr_summary_row_ok_count
        == request_launch_ptr_summary_row_count
        and request_launch_ptr_summary_descriptor_ptr_read_row_ok_count
        == request_launch_ptr_summary_row_count
        and request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count
        == request_launch_ptr_summary_row_count
        and request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count
        == request_launch_ptr_summary_row_count
        and request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count
        == request_launch_ptr_summary_row_count
        and request_launch_ptr_summary_row_metadata_read_row_ok_count
        == request_launch_ptr_summary_row_count
        and request_launch_ptr_summary_error_count == 0
    )
    consumer_view_field_read_row_count = _int_metric(
        (
            online_merged_arg_slot_summary
            if online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_view_checked"
            )
            is True
            else dispatch_runner_summary
        ),
        "future_kernel_native_consumer_view_row_count",
    )
    online_merged_consumer_view_checked = (
        online_merged_arg_slot_summary.get(
            "future_kernel_native_consumer_view_checked"
        )
        is True
    )
    online_merged_dispatch_checked = (
        online_merged_arg_slot_summary.get(
            "future_kernel_native_dispatch_consumer_checked"
        )
        is True
    )
    consumer_view_summary = (
        online_merged_arg_slot_summary
        if online_merged_consumer_view_checked
        else dispatch_runner_summary
    )
    consumer_view_status_source = (
        "online_merged_arg_slot_summary"
        if online_merged_consumer_view_checked
        else "dispatch_runner_summary"
    )
    consumer_view_row_window_summary = (
        online_merged_arg_slot_summary
        if online_merged_consumer_view_checked and online_merged_dispatch_checked
        else dispatch_runner_summary
    )
    consumer_view_row_window_source = (
        "online_merged_arg_slot_summary"
        if online_merged_consumer_view_checked and online_merged_dispatch_checked
        else "dispatch_runner_summary"
    )

    def _hex_metric_text(metrics: dict[str, Any], key: str) -> str | None:
        value = metrics.get(key)
        return (
            value
            if isinstance(value, str) and _hex64_metric(metrics, key) is not None
            else None
        )

    dispatch_program_count = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_program_count",
    )
    dispatch_row_window_active_rows = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_active_rows",
    )
    dispatch_full_program_count = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_full_program_count",
    )
    dispatch_last_program_active_rows = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_last_program_active_rows",
    )
    dispatch_inactive_lane_count = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_inactive_lane_count",
    )
    dispatch_first_program_row_offset = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_first_program_row_offset",
    )
    dispatch_last_program_row_offset = _int_metric(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_last_program_row_offset",
    )
    dispatch_program_iteration_hash_text = _hex_metric_text(
        consumer_view_row_window_summary,
        "future_kernel_native_dispatch_consumer_program_iteration_hash",
    )
    consumer_view_field_read_row_ok_counts: dict[str, int | None] = {}
    consumer_view_field_read_error_counts: dict[str, int | None] = {}
    consumer_view_field_read_hashes: dict[str, str | None] = {}
    for field in ARG_SLOT_MIRROR_FIELDS:
        prefix = f"future_kernel_native_consumer_view_{field}_read"
        consumer_view_field_read_row_ok_counts[field] = _int_metric(
            consumer_view_summary,
            f"{prefix}_row_ok_count",
        )
        consumer_view_field_read_error_counts[field] = _int_metric(
            consumer_view_summary,
            f"{prefix}_error_count",
        )
        hash_key = f"{prefix}_hash_accumulator"
        hash_value = consumer_view_summary.get(hash_key)
        consumer_view_field_read_hashes[field] = (
            hash_value
            if isinstance(hash_value, str)
            and _hex64_metric(consumer_view_summary, hash_key) is not None
            else None
        )
    consumer_view_all_handle_fields_read = (
        consumer_view_field_read_row_count is not None
        and all(
            consumer_view_field_read_row_ok_counts.get(field)
            == consumer_view_field_read_row_count
            and consumer_view_field_read_error_counts.get(field) == 0
            and consumer_view_field_read_hashes.get(field) is not None
            for field in ARG_SLOT_MIRROR_FIELDS
        )
    )
    dispatch_row_window = {
        "row_offset": _int_metric(
            consumer_view_row_window_summary,
            "future_kernel_native_dispatch_consumer_row_offset",
        ),
        "row_limit": _int_metric(
            consumer_view_row_window_summary,
            "future_kernel_native_dispatch_consumer_row_limit",
        ),
        "rows_per_program": _int_metric(
            consumer_view_row_window_summary,
            "future_kernel_native_dispatch_consumer_rows_per_program",
        ),
    }
    consumer_view_row_window = {
        "row_offset": _int_metric(
            consumer_view_row_window_summary,
            "future_kernel_native_consumer_view_row_offset",
        ),
        "row_limit": _int_metric(
            consumer_view_row_window_summary,
            "future_kernel_native_consumer_view_row_limit",
        ),
        "rows_per_program": _int_metric(
            consumer_view_row_window_summary,
            "future_kernel_native_consumer_view_rows_per_program",
        ),
    }
    consumer_view_row_window_matches_dispatch = (
        all(value is not None for value in dispatch_row_window.values())
        and all(value is not None for value in consumer_view_row_window.values())
        and consumer_view_row_window == dispatch_row_window
    )
    consumer_view_source = consumer_view_summary.get(
        "future_kernel_native_consumer_view_source"
    )
    consumer_view_source = (
        consumer_view_source if isinstance(consumer_view_source, str) else None
    )
    expected_consumer_view_source = schema_summary.get(
        "future_kernel_native_consumer_view_abi_source"
    )
    expected_consumer_view_source = (
        expected_consumer_view_source
        if isinstance(expected_consumer_view_source, str)
        else None
    )
    consumer_view_source_matches_schema = (
        consumer_view_source is not None
        and expected_consumer_view_source is not None
        and consumer_view_source == expected_consumer_view_source
    )
    consumer_view_source_packet_chain_depth = _int_metric(
        consumer_view_summary,
        "future_kernel_native_consumer_view_source_packet_chain_depth",
    )
    consumer_view_payload_bytes = _int_metric(
        consumer_view_summary,
        "future_kernel_native_consumer_view_payload_bytes",
    )
    consumer_view_passed_to_kernel = _bool_metric(
        consumer_view_summary,
        "future_kernel_native_consumer_view_passed_to_kernel",
    )
    consumer_view_changes_kernel_launch_args = _bool_metric(
        consumer_view_summary,
        "future_kernel_native_consumer_view_changes_kernel_launch_args",
    )
    consumer_view_current_wna16_arg_compatible = _bool_metric(
        consumer_view_summary,
        "future_kernel_native_consumer_view_current_wna16_arg_compatible",
    )
    consumer_view_requires_wna16_arg_reinterpretation = _bool_metric(
        consumer_view_summary,
        "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation",
    )
    consumer_view_required_source_depth = required_gate_checks.get(
        "consumer_view_source_packet_chain_depth_required"
    )
    consumer_view_required_payload_bytes = required_gate_checks.get(
        "payload_bytes_required"
    )
    consumer_view_required_passed_to_kernel = required_gate_checks.get(
        "passed_to_kernel_required"
    )
    consumer_view_required_changes_kernel_launch_args = required_gate_checks.get(
        "changes_kernel_launch_args_required"
    )
    consumer_view_required_current_wna16_arg_compatible = required_gate_checks.get(
        "current_wna16_arg_compatible_required"
    )
    consumer_view_expected_requires_reinterpretation = schema_summary.get(
        "future_kernel_native_consumer_view_abi_requires_wna16_arg_reinterpretation"
    )
    consumer_view_reinterpretation_flags_valid = (
        isinstance(consumer_view_requires_wna16_arg_reinterpretation, bool)
        and isinstance(consumer_view_expected_requires_reinterpretation, bool)
    )
    consumer_view_safety_matches_required = (
        consumer_view_source_matches_schema
        and consumer_view_source_packet_chain_depth
        == consumer_view_required_source_depth
        and consumer_view_payload_bytes == consumer_view_required_payload_bytes
        and consumer_view_passed_to_kernel == consumer_view_required_passed_to_kernel
        and consumer_view_changes_kernel_launch_args
        == consumer_view_required_changes_kernel_launch_args
        and consumer_view_current_wna16_arg_compatible
        == consumer_view_required_current_wna16_arg_compatible
        and consumer_view_reinterpretation_flags_valid
        and consumer_view_requires_wna16_arg_reinterpretation
        == consumer_view_expected_requires_reinterpretation
    )
    consumer_view_projection_hash = _hex_metric_text(
        consumer_view_summary,
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    )
    online_merged_consumer_program_view_checked = (
        online_merged_arg_slot_summary.get(
            "future_kernel_native_consumer_program_view_checked"
        )
        is True
    )
    consumer_program_view_summary = (
        online_merged_arg_slot_summary
        if online_merged_consumer_program_view_checked
        else dispatch_runner_summary
    )
    consumer_program_view_status_source = (
        "online_merged_arg_slot_summary"
        if online_merged_consumer_program_view_checked
        else "dispatch_runner_summary"
    )
    consumer_program_view_checked = (
        consumer_program_view_summary.get(
            "future_kernel_native_consumer_program_view_checked"
        )
        is True
    )
    consumer_program_view_source = consumer_program_view_summary.get(
        "future_kernel_native_consumer_program_view_source"
    )
    consumer_program_view_source = (
        consumer_program_view_source
        if isinstance(consumer_program_view_source, str)
        else None
    )
    consumer_program_view_row_count = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_row_count",
    )
    consumer_program_view_row_ok_count = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_row_ok_count",
    )
    consumer_program_view_error_count = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_error_count",
    )
    consumer_program_view_program_count = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_program_count",
    )
    consumer_program_view_full_program_count = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_full_program_count",
    )
    consumer_program_view_last_program_active_rows = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_last_program_active_rows",
    )
    consumer_program_view_inactive_lane_count = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_inactive_lane_count",
    )
    consumer_program_view_first_program_row_offset = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_first_program_row_offset",
    )
    consumer_program_view_last_program_row_offset = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_last_program_row_offset",
    )
    consumer_program_view_program_iteration_hash = _hex_metric_text(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_program_iteration_hash",
    )
    consumer_program_view_projection_hash = _hex_metric_text(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator",
    )
    consumer_program_view_payload_bytes = _int_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_payload_bytes",
    )
    consumer_program_view_passed_to_kernel = _bool_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_passed_to_kernel",
    )
    consumer_program_view_changes_kernel_launch_args = _bool_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_changes_kernel_launch_args",
    )
    consumer_program_view_current_wna16_arg_compatible = _bool_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_current_wna16_arg_compatible",
    )
    consumer_program_view_requires_wna16_arg_reinterpretation = _bool_metric(
        consumer_program_view_summary,
        "future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation",
    )
    consumer_program_view_formula = consumer_program_view_summary.get(
        "future_kernel_native_consumer_program_view_row_assignment_formula"
    )
    consumer_program_view_formula = (
        consumer_program_view_formula
        if isinstance(consumer_program_view_formula, str)
        else None
    )
    consumer_program_view_row_count_matches_dispatch = (
        consumer_program_view_row_count is not None
        and dispatch_row_window_active_rows is not None
        and consumer_program_view_row_count == dispatch_row_window_active_rows
        and consumer_program_view_row_ok_count == dispatch_row_window_active_rows
        and consumer_program_view_error_count == 0
    )
    consumer_program_view_geometry_matches_dispatch = (
        consumer_program_view_program_count == dispatch_program_count
        and consumer_program_view_full_program_count == dispatch_full_program_count
        and consumer_program_view_last_program_active_rows
        == dispatch_last_program_active_rows
        and consumer_program_view_inactive_lane_count == dispatch_inactive_lane_count
        and consumer_program_view_first_program_row_offset
        == dispatch_first_program_row_offset
        and consumer_program_view_last_program_row_offset
        == dispatch_last_program_row_offset
    )
    consumer_program_view_hash_matches_dispatch = (
        consumer_program_view_program_iteration_hash is not None
        and dispatch_program_iteration_hash_text is not None
        and consumer_program_view_program_iteration_hash
        == dispatch_program_iteration_hash_text
    )
    consumer_program_view_projection_matches_view = (
        consumer_program_view_projection_hash is not None
        and consumer_view_projection_hash is not None
        and consumer_program_view_projection_hash == consumer_view_projection_hash
    )
    consumer_program_view_safety_matches_required = (
        consumer_program_view_payload_bytes
        == required_gate_checks.get("payload_bytes_required")
        and consumer_program_view_passed_to_kernel
        == required_gate_checks.get("passed_to_kernel_required")
        and consumer_program_view_changes_kernel_launch_args
        == required_gate_checks.get("changes_kernel_launch_args_required")
        and consumer_program_view_current_wna16_arg_compatible
        == required_gate_checks.get("current_wna16_arg_compatible_required")
        and consumer_program_view_requires_wna16_arg_reinterpretation is False
    )
    consumer_program_view_ptr_summary = online_merged_arg_slot_summary
    consumer_program_view_ptr_checked = (
        consumer_program_view_ptr_summary.get(
            "future_kernel_native_consumer_program_view_ptr_checked"
        )
        is True
    )
    consumer_program_view_ptr_source = consumer_program_view_ptr_summary.get(
        "future_kernel_native_consumer_program_view_ptr_source"
    )
    consumer_program_view_ptr_source = (
        consumer_program_view_ptr_source
        if isinstance(consumer_program_view_ptr_source, str)
        else None
    )
    expected_consumer_program_view_ptr_source = schema_summary.get(
        "future_kernel_native_consumer_program_view_ptr_abi_source"
    )
    expected_consumer_program_view_ptr_source = (
        expected_consumer_program_view_ptr_source
        if isinstance(expected_consumer_program_view_ptr_source, str)
        else None
    )
    consumer_program_view_ptr_source_matches_schema = (
        consumer_program_view_ptr_source is not None
        and expected_consumer_program_view_ptr_source is not None
        and consumer_program_view_ptr_source
        == expected_consumer_program_view_ptr_source
    )
    consumer_program_view_ptr_row_count = _int_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_row_count",
    )
    consumer_program_view_ptr_row_ok_count = _int_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_row_ok_count",
    )
    consumer_program_view_ptr_error_count = _int_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_error_count",
    )
    consumer_program_view_ptr_field_mask = _int_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_field_mask",
    )
    consumer_program_view_ptr_required_field_mask = _int_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_required_field_mask",
    )
    consumer_program_view_ptr_payload_bytes = _int_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_payload_bytes",
    )
    consumer_program_view_ptr_passed_to_kernel = _bool_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_passed_to_kernel",
    )
    consumer_program_view_ptr_changes_kernel_launch_args = _bool_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args",
    )
    consumer_program_view_ptr_current_wna16_arg_compatible = _bool_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible",
    )
    consumer_program_view_ptr_requires_wna16_arg_reinterpretation = _bool_metric(
        consumer_program_view_ptr_summary,
        "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation",
    )
    consumer_program_view_ptr_row_count_matches_dispatch = (
        consumer_program_view_ptr_row_count is not None
        and dispatch_row_window_active_rows is not None
        and consumer_program_view_ptr_row_count == dispatch_row_window_active_rows
        and consumer_program_view_ptr_row_ok_count == dispatch_row_window_active_rows
        and consumer_program_view_ptr_error_count == 0
    )
    consumer_program_view_ptr_required_fields_visible = (
        consumer_program_view_ptr_field_mask is not None
        and consumer_program_view_ptr_required_field_mask is not None
        and (
            consumer_program_view_ptr_field_mask
            & consumer_program_view_ptr_required_field_mask
        )
        == consumer_program_view_ptr_required_field_mask
    )
    consumer_program_view_ptr_safety_matches_required = (
        consumer_program_view_ptr_payload_bytes
        == required_gate_checks.get("payload_bytes_required")
        and consumer_program_view_ptr_passed_to_kernel
        == required_gate_checks.get("passed_to_kernel_required")
        and consumer_program_view_ptr_changes_kernel_launch_args
        == required_gate_checks.get("changes_kernel_launch_args_required")
        and consumer_program_view_ptr_current_wna16_arg_compatible
        == required_gate_checks.get("current_wna16_arg_compatible_required")
        and consumer_program_view_ptr_requires_wna16_arg_reinterpretation is False
    )
    effective_require_program_view_ptr_abi = (
        require_program_view_ptr_abi
        or required_gate_checks.get("consumer_program_view_ptr_required") is True
    )
    future_kernel_args_summary = dispatch_runner_payload.get(
        "future_kernel_args_stub_summary",
    )
    if not isinstance(future_kernel_args_summary, dict):
        future_kernel_args_summary = {}
    future_kernel_args_compatible_path_summary = dispatch_runner_payload.get(
        "future_kernel_args_compatible_path_stub_summary",
    )
    if not isinstance(future_kernel_args_compatible_path_summary, dict):
        future_kernel_args_compatible_path_summary = {}
    future_kernel_args_row_count = _int_metric(
        future_kernel_args_summary,
        "future_kernel_consumer_args_row_count",
    )
    future_kernel_args_row_ok_count = _int_metric(
        future_kernel_args_summary,
        "future_kernel_consumer_args_row_ok_count",
    )
    future_kernel_args_payload_bytes = _int_metric(
        future_kernel_args_summary,
        "future_kernel_consumer_args_payload_bytes",
    )
    future_kernel_args_compatible_row_count = _int_metric(
        future_kernel_args_compatible_path_summary,
        "future_kernel_args_compatible_consumer_path_row_count",
    )
    future_kernel_args_compatible_row_ok_count = _int_metric(
        future_kernel_args_compatible_path_summary,
        "future_kernel_args_compatible_consumer_path_row_ok_count",
    )
    future_kernel_args_compatible_payload_bytes = _int_metric(
        future_kernel_args_compatible_path_summary,
        "future_kernel_args_compatible_consumer_path_payload_bytes",
    )

    dispatch_row_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_hash_accumulator",
    )
    dispatch_ptr_row_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_ptr_consumer_hash_accumulator",
    )
    arg_slot_row_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_arg_slot_consumer_hash_accumulator",
    )
    dispatch_projection_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator",
    )
    dispatch_ptr_projection_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator",
    )
    arg_slot_projection_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
    )
    consumer_view_projection_hash = _hex_metric_text(
        dispatch_runner_summary,
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    )
    projection_hash_values = (
        _hex64_metric(
            dispatch_runner_summary,
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator",
        ),
        _hex64_metric(
            dispatch_runner_summary,
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator",
        ),
        _hex64_metric(
            dispatch_runner_summary,
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator",
        ),
    )
    consumer_view_projection_value = _hex64_metric(
        dispatch_runner_summary,
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
    )
    if (
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
        in dispatch_runner_summary
    ):
        projection_hash_values = (
            *projection_hash_values,
            consumer_view_projection_value,
        )
    row_hashchain_all_valid = all(
        value is not None
        for value in (dispatch_row_hash, dispatch_ptr_row_hash, arg_slot_row_hash)
    )
    projection_hashchain_equal = (
        all(value is not None for value in projection_hash_values)
        and len(set(projection_hash_values)) == 1
    )
    if not allow_missing_evidence and not defer_online_prelaunch_runner_evidence:
        if not row_hashchain_all_valid:
            failures.append(
                "default_kernel_consumer_dispatch_runner_row_hashchain_invalid"
            )
        if not projection_hashchain_equal:
            failures.append(
                "default_kernel_consumer_dispatch_runner_projection_hashchain_mismatch"
            )
    arg_slot_projection_field_names = list(ARG_SLOT_MIRROR_FIELDS)
    arg_slot_projection_all_handle_fields_schema_covered = set(
        arg_slot_projection_field_names
    ).issubset(set(schema_row_field_names))
    arg_slot_projection_all_handle_fields_checked = (
        projection_hashchain_equal
        and arg_slot_projection_hash is not None
        and arg_slot_projection_all_handle_fields_schema_covered
    )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not arg_slot_projection_all_handle_fields_checked
    ):
        failures.append(
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_unchecked"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not arg_slot_all_handle_fields_read
    ):
        failures.append(
            "default_kernel_consumer_arg_slot_all_handle_fields_read_unchecked"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_view_all_handle_fields_required")
        is True
        and not consumer_view_all_handle_fields_read
    ):
        failures.append(
            "default_kernel_consumer_consumer_view_all_handle_fields_read_unchecked"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_view_row_layout_required") is True
        and not consumer_view_row_window_matches_dispatch
    ):
        failures.append(
            "default_kernel_consumer_consumer_view_row_window_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_view_required") is True
        and not consumer_view_safety_matches_required
    ):
        failures.append(
            "default_kernel_consumer_consumer_view_safety_contract_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and not consumer_program_view_checked
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_missing"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and not consumer_program_view_row_count_matches_dispatch
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_row_count_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and not consumer_program_view_geometry_matches_dispatch
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_geometry_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and not consumer_program_view_hash_matches_dispatch
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_iteration_hash_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and not consumer_program_view_projection_matches_view
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_projection_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and consumer_program_view_formula
        != required_gate_checks.get("consumer_program_view_row_assignment_formula")
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_formula_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("consumer_program_view_required") is True
        and not consumer_program_view_safety_matches_required
    ):
        failures.append(
            "default_kernel_consumer_consumer_program_view_safety_contract_mismatch"
        )
    if (
        effective_require_program_view_ptr_abi
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not consumer_program_view_ptr_checked
    ):
        failures.append("default_kernel_consumer_program_view_ptr_missing")
    if (
        effective_require_program_view_ptr_abi
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not consumer_program_view_ptr_source_matches_schema
    ):
        failures.append("default_kernel_consumer_program_view_ptr_source_mismatch")
    if (
        effective_require_program_view_ptr_abi
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not consumer_program_view_ptr_row_count_matches_dispatch
    ):
        failures.append("default_kernel_consumer_program_view_ptr_row_count_mismatch")
    if (
        effective_require_program_view_ptr_abi
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not consumer_program_view_ptr_required_fields_visible
    ):
        failures.append("default_kernel_consumer_program_view_ptr_field_mask_mismatch")
    if (
        effective_require_program_view_ptr_abi
        and not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and not consumer_program_view_ptr_safety_matches_required
    ):
        failures.append(
            "default_kernel_consumer_program_view_ptr_safety_contract_mismatch"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("request_launch_all_handle_fields_required")
        is True
        and not request_launch_all_handle_fields_read
    ):
        failures.append(
            "default_kernel_consumer_request_launch_all_handle_fields_unchecked"
        )
    if (
        not allow_missing_evidence
        and not defer_online_prelaunch_runner_evidence
        and required_gate_checks.get("request_launch_ptr_all_handle_fields_required")
        is True
        and not request_launch_ptr_all_handle_fields_read
    ):
        failures.append(
            "default_kernel_consumer_request_launch_ptr_all_handle_fields_unchecked"
        )
    prefetch_lab_default_decisions = (
        prefetch_lab_default_gate_check.get("decisions") or {}
    )
    prefetch_lab_default_sections = (
        prefetch_lab_default_gate_check.get("sections") or {}
    )
    prefetch_lab_default_full_fetch = (
        prefetch_lab_default_sections.get("full_fetch") or {}
    )
    prefetch_lab_default_metadata = (
        prefetch_lab_default_sections.get("metadata") or {}
    )
    prefetch_lab_default_premap = (
        prefetch_lab_default_sections.get("premap") or {}
    )
    prefetch_lab_default_passed = bool(
        prefetch_lab_default_gate_check.get("passed", False)
    )

    lab_gate_status_summary = {
        "passed": not failures,
        "default_readonly_gate_path": default_gate_path,
        "default_readonly_gate_sha256": _path_label_sha256(
            default_readonly_gate,
            root=root,
        ),
        "canary_gate_path": canary_gate_path,
        "canary_gate_sha256": _path_label_sha256(canary_gate, root=root),
        "default_contract_passed": bool(
            default_gate_contract_check.get("passed", False)
        ),
        "default_contract_observed_available": bool(
            default_gate_contract_check.get("observed_contract_available", False)
        ),
        "default_kernel_consumer_schema_passed": bool(
            default_kernel_consumer_schema_check.get("passed", False)
        ),
        "prefetch_lab_default_gate_passed": prefetch_lab_default_passed,
        "prefetch_lab_default_gate_decision_status": (
            "passed" if prefetch_lab_default_passed else "failed"
        ),
        "prefetch_lab_default_gate_failures": list(
            prefetch_lab_default_gate_check.get("failures") or []
        ),
        "prefetch_lab_default_gate_id": (
            prefetch_lab_default_gate_check.get("gate_id")
        ),
        "prefetch_lab_default_full_fetch_decision": (
            prefetch_lab_default_decisions.get("full_fetch")
        ),
        "prefetch_lab_default_full_fetch_passed": (
            not bool(prefetch_lab_default_full_fetch.get("failures"))
        ),
        "prefetch_lab_default_full_fetch_failures": list(
            prefetch_lab_default_full_fetch.get("failures") or []
        ),
        "prefetch_lab_default_ready_time_report_passed": bool(
            prefetch_lab_default_full_fetch.get("ready_time_report_passed", False)
        ),
        "prefetch_lab_default_ready_time_allow_full_fetch": bool(
            prefetch_lab_default_full_fetch.get("ready_time_allow_full_fetch", False)
        ),
        "prefetch_lab_default_ready_time_decision_reason": (
            prefetch_lab_default_full_fetch.get("ready_time_decision_reason")
        ),
        "prefetch_lab_default_ready_time_threshold_failures": list(
            prefetch_lab_default_full_fetch.get("ready_time_threshold_failures") or []
        ),
        "prefetch_lab_default_ready_time_demand_hit_rate": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_demand_hit_rate",
        ),
        "prefetch_lab_default_ready_time_ready_late_miss_rate": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_ready_late_miss_rate",
        ),
        "prefetch_lab_default_ready_time_used_per_issued_fetch": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_used_per_issued_fetch",
        ),
        "prefetch_lab_default_ready_time_issued_fetch_count": _int_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_issued_fetch_count",
        ),
        "prefetch_lab_default_ready_time_used_fetch_count": _int_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_used_fetch_count",
        ),
        "prefetch_lab_default_ready_time_current_deadline_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_current_deadline_us",
        ),
        "prefetch_lab_default_ready_time_current_lookahead_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_current_lookahead_us",
        ),
        "prefetch_lab_default_ready_time_first_model_passing_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_first_model_passing_deadline_us",
            )
        ),
        "prefetch_lab_default_ready_time_first_model_passing_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_first_model_passing_lookahead_us",
            )
        ),
        "prefetch_lab_default_ready_time_required_lookahead_slack_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_required_lookahead_slack_us",
            )
        ),
        "prefetch_lab_default_ready_time_required_issue_to_demand_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_required_issue_to_demand_lookahead_us",
            )
        ),
        "prefetch_lab_default_ready_time_slack_deficit_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_slack_deficit_us",
        ),
        "prefetch_lab_default_ready_time_lookahead_deficit_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_lookahead_deficit_us",
        ),
        "prefetch_lab_default_ready_time_model_slack_satisfied": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_model_slack_satisfied",
        ),
        "prefetch_lab_default_ready_time_model_lookahead_satisfied": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_model_lookahead_satisfied",
        ),
        "prefetch_lab_default_ready_time_any_model_route_satisfied": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_any_model_route_satisfied",
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_report_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_report_present",
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_report_passed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_report_passed",
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_report_recheck_passed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_report_recheck_passed",
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_direct_snapshot_present",
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_runtime_stage": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_stage"
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_payload_bytes",
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_issue_sources": list(
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_issue_sources"
            )
            or []
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_present",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_stage": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_participation_stage"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_status": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_participation_status"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_consumes_direct_snapshot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_consumes_manager_snapshot",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_payload_bytes",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_ready_credit",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_participation_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_issue_sources": list(
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_participation_issue_sources"
            )
            or []
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_direct_snapshot_runtime_plan_present",
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_stage": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_plan_stage"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_status": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_plan_status"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_consumes_participation": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_consumes_participation",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_planned_issue_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_planned_issue_count",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_payload_bytes",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_ready_credit": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_direct_snapshot_runtime_plan_ready_credit",
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_plan_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "ready_time_direct_snapshot_runtime_execution_present",
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_stage": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_execution_stage"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_status": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_execution_status"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_consumes_plan": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_consumes_plan",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_plan_status": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_execution_plan_status"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_decision": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_execution_decision"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_execution_block_reason"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "ready_time_direct_snapshot_runtime_execution_execution_mode"
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_issued_payload_count",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_payload_bytes",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_ready_credit",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "ready_time_direct_snapshot_runtime_execution_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_decision_gate_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_decision_gate_present",
        ),
        "prefetch_lab_default_stream_decision_gate_passed": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_decision_gate_passed",
        ),
        "prefetch_lab_default_stream_decision": (
            prefetch_lab_default_full_fetch.get("stream_decision")
        ),
        "prefetch_lab_default_stream_full_fetch_runtime_allowed": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_full_fetch_runtime_allowed",
        ),
        "prefetch_lab_default_stream_full_fetch_block_reason": (
            prefetch_lab_default_full_fetch.get("stream_full_fetch_block_reason")
        ),
        "prefetch_lab_default_stream_current_lookahead_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "stream_current_lookahead_us",
        ),
        "prefetch_lab_default_stream_required_lookahead_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "stream_required_lookahead_us",
        ),
        "prefetch_lab_default_stream_lookahead_deficit_us": _float_metric(
            prefetch_lab_default_full_fetch,
            "stream_lookahead_deficit_us",
        ),
        "prefetch_lab_default_stream_first_model_passing_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_first_model_passing_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_metadata_premap_runtime_preferred": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_metadata_premap_runtime_preferred",
            )
        ),
        "prefetch_lab_default_stream_descriptor_prep_runtime_preferred": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_descriptor_prep_runtime_preferred",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_clamped_issue_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_clamped_issue_count",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_duplicate_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_duplicate_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_invalid_export_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_invalid_export_count",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_row_shift_mismatch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_row_shift_mismatch_count",
            )
        ),
        "prefetch_lab_default_stream_required_shifted_issue_row_clamp_mismatch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_required_shifted_issue_row_clamp_mismatch_count",
            )
        ),
        "prefetch_lab_default_stream_feasibility_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_feasibility_present",
        ),
        "prefetch_lab_default_stream_feasibility_passed": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_feasibility_passed",
        ),
        "prefetch_lab_default_stream_current_runtime_satisfies_model": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_current_runtime_satisfies_model",
            )
        ),
        "prefetch_lab_default_stream_feasible_within_configured_token_window": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_feasible_within_configured_token_window",
            )
        ),
        "prefetch_lab_default_stream_min_required_lead_tokens": _int_metric(
            prefetch_lab_default_full_fetch,
            "stream_min_required_lead_tokens",
        ),
        "prefetch_lab_default_stream_max_required_lead_tokens": _int_metric(
            prefetch_lab_default_full_fetch,
            "stream_max_required_lead_tokens",
        ),
        "prefetch_lab_default_stream_max_candidate_lead_tokens": _int_metric(
            prefetch_lab_default_full_fetch,
            "stream_max_candidate_lead_tokens",
        ),
        "prefetch_lab_default_stream_lead_token_sweep_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_lead_token_sweep_present",
        ),
        "prefetch_lab_default_stream_lead_token_sweep_passed": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_lead_token_sweep_passed",
        ),
        "prefetch_lab_default_stream_lead_token_sweep_event_timing_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_lead_token_sweep_event_timing_mode"
            )
        ),
        "prefetch_lab_default_stream_lead_token_sweep_token_timing_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_lead_token_sweep_token_timing_enabled",
            )
        ),
        "prefetch_lab_default_stream_lead_token_sweep_decode_token_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_lead_token_sweep_decode_token_us",
            )
        ),
        "prefetch_lab_default_stream_first_model_passing_lead_tokens": _int_metric(
            prefetch_lab_default_full_fetch,
            "stream_first_model_passing_lead_tokens",
        ),
        "prefetch_lab_default_stream_lead_token_sweep_first_model_passing_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_lead_token_sweep_first_model_passing_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_present": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_present",
        ),
        "prefetch_lab_default_stream_queue_budget_passed": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_passed",
        ),
        "prefetch_lab_default_stream_queue_budget_cell_count": _int_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_cell_count",
        ),
        "prefetch_lab_default_stream_queue_budget_event_timing_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_event_timing_mode"
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_model_passing_capacity": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_model_passing_capacity",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_model_passing_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_model_passing_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_model_passing_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_model_passing_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_model_passing_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_model_passing_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_first_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_first_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_runtime_envelope_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_runtime_envelope_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_runtime_envelope_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_consumes_queue_budget_sweep": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_consumes_queue_budget_sweep",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_transfer_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_payload_transfer_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_full_fetch_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_full_fetch_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_runtime_envelope_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_runtime_envelope_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_stage_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_stage_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_consumes_queue_budget_runtime_envelope": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_consumes_queue_budget_runtime_envelope",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_envelope_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_stage_queue_budget_envelope_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_capacity_entries": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_queue_budget_capacity_entries",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_queue_budget_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_queue_budget_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_queue_budget_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_queue_budget_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_decision": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_stage_decision",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_stage_block_reason",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_stage_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_issued_payload_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_stage_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_stage_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_runtime_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_runtime_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_consumes_live_payload_stage_preflight": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_consumes_live_payload_stage_preflight",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_live_payload_stage_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_runtime_live_payload_stage_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_capacity_entries": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_queue_budget_capacity_entries",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_queue_budget_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_queue_budget_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_queue_budget_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_queue_budget_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_decision": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_runtime_decision",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_runtime_block_reason",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_live_payload_runtime_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_payload_deref_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_issued_payload_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_live_payload_runtime_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_live_payload_runtime_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_consumes_live_payload_runtime_canary": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_consumes_live_payload_runtime_canary",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_live_payload_runtime_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_live_payload_runtime_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_manager_backend": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_manager_backend",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_manager_contract": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_manager_contract",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_capacity_entries": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_capacity_entries",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_decision": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_decision",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_block_reason",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_artifact_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_deref_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_payload_deref_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_issued_payload_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_artifact_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_artifact_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_consumes_manager_implementation_artifact": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_consumes_manager_implementation_artifact",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_artifact_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_manager_artifact_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_backend": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_manager_backend",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_contract": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_manager_contract",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_runtime_contract": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_manager_runtime_contract",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_manager_runtime_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_manager_runtime_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_capacity_entries": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_capacity_entries",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_runtime_instantiated": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_runtime_instantiated",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_decision": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_decision",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_block_reason",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_skeleton_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_deref_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_payload_deref_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_issued_payload_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_skeleton_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_skeleton_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_consumes_runtime_skeleton": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_consumes_runtime_skeleton",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_runtime_skeleton_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_runtime_skeleton_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_manager_backend": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_manager_backend",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_manager_runtime_contract": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_manager_runtime_contract",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_manager_runtime_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_manager_runtime_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_snapshot_source": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_snapshot_source",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_accounting_snapshot_instantiated": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_accounting_snapshot_instantiated",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_live_runtime_instantiated": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_live_runtime_instantiated",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_capacity_entries": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_capacity_entries",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_batch_size": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_batch_size",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_resident_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_resident_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_issued_fetch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_issued_fetch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_used_fetch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_used_fetch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_unused_fetch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_unused_fetch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_demand_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_demand_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_demand_hit_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_demand_hit_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_demand_miss_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_demand_miss_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_evicted_before_use_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_evicted_before_use_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_ready_late_miss_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_ready_late_miss_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_late_completion_unused_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_late_completion_unused_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_batch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_batch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_service_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_service_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_total_span_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_total_span_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_wait_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_wait_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_queue_max_delay_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_queue_max_delay_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_decision": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_decision",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_block_reason",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_manager_runtime_snapshot_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_deref_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_payload_deref_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_issued_payload_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_manager_runtime_snapshot_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_manager_runtime_snapshot_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_present",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_stage": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_stage",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_consumes_runtime_snapshot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_consumes_runtime_snapshot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_runtime_snapshot_status": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_runtime_snapshot_status",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_backend": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_backend",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_contract": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_contract",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_snapshot_source": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_snapshot_source",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_preflight_instantiated": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_preflight_instantiated",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_accounting_snapshot_instantiated": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_accounting_snapshot_instantiated",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_instantiated": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_instantiated",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_capacity_entries": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_capacity_entries",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_deadline_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_deadline_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_lookahead_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_lookahead_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_size": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_size",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_resident_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_resident_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_fetch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_fetch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_used_fetch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_used_fetch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_unused_fetch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_unused_fetch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_hit_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_hit_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_miss_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_miss_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_evicted_before_use_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_evicted_before_use_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_late_miss_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_late_miss_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_late_completion_unused_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_late_completion_unused_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_service_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_service_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_total_span_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_total_span_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_wait_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_wait_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_max_delay_us": (
            _float_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_max_delay_us",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounting_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounting_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounted_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounted_packet_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_unique_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_unique_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_decision": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_decision",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_block_reason": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_block_reason",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_execution_mode": (
            prefetch_lab_default_full_fetch.get(
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_execution_mode",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_live_payload_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_live_payload_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_transfer_runtime_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_transfer_runtime_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_payload_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_payload_count",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_vllm_latency",
            )
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix="stream_queue_budget_snapshot_backed_live_runtime_canary",
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "snapshot_backed_live_runtime_canary"
            ),
            fields=STREAM_QUEUE_BUDGET_LIVE_RUNTIME_CANARY_FIELDS,
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix="stream_queue_budget_live_runtime_state_shape",
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_state_shape"
            ),
            fields=STREAM_QUEUE_BUDGET_LIVE_RUNTIME_STATE_SHAPE_FIELDS,
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix="stream_queue_budget_live_runtime_object_preflight",
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_object_preflight"
            ),
            fields=STREAM_QUEUE_BUDGET_LIVE_RUNTIME_OBJECT_PREFLIGHT_FIELDS,
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_object_adapter_preflight"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_object_adapter_preflight"
            ),
            fields=STREAM_QUEUE_BUDGET_LIVE_RUNTIME_OBJECT_ADAPTER_PREFLIGHT_FIELDS,
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_materialization_preflight"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_materialization_preflight"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_MATERIALIZATION_PREFLIGHT_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_state_object_preflight"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_state_object_preflight"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_STATE_OBJECT_PREFLIGHT_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_state_validation_preflight"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_state_validation_preflight"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_STATE_VALIDATION_PREFLIGHT_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_state_validation_artifact"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_state_validation_artifact"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_STATE_VALIDATION_ARTIFACT_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_instantiation_canary"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_instantiation_canary"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_INSTANTIATION_CANARY_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_constructor_binding_preflight"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_constructor_binding_preflight"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_CONSTRUCTOR_BINDING_PREFLIGHT_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_instance_construction_plan"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_instance_construction_plan"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_INSTANCE_CONSTRUCTION_PLAN_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_object_shell_evidence"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_object_shell_evidence"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_OBJECT_SHELL_EVIDENCE_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_operation_rejection_canary"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_operation_rejection_canary"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_OPERATION_REJECTION_CANARY_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_accounting_dry_run_canary"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_accounting_dry_run_canary"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_ACCOUNTING_DRY_RUN_CANARY_FIELDS
            ),
        ),
        **_copy_metric_block(
            prefetch_lab_default_full_fetch,
            input_prefix=(
                "stream_queue_budget_live_runtime_adapter_mixed_outcome_dry_run_canary"
            ),
            output_prefix=(
                "prefetch_lab_default_stream_queue_budget_"
                "live_runtime_adapter_mixed_outcome_dry_run_canary"
            ),
            fields=(
                STREAM_QUEUE_BUDGET_LIVE_RUNTIME_ADAPTER_MIXED_OUTCOME_DRY_RUN_CANARY_FIELDS
            ),
        ),
        "prefetch_lab_default_stream_queue_budget_payload_bytes": _int_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_payload_bytes",
        ),
        "prefetch_lab_default_stream_queue_budget_payload_transfer_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_payload_transfer_enabled",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_full_fetch_allowed": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_full_fetch_allowed",
        ),
        "prefetch_lab_default_stream_queue_budget_ready_credit": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_ready_credit",
        ),
        "prefetch_lab_default_stream_queue_budget_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_passed_to_kernel": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_passed_to_kernel",
        ),
        "prefetch_lab_default_stream_queue_budget_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_queue_budget_measures_tpot": _bool_metric(
            prefetch_lab_default_full_fetch,
            "stream_queue_budget_measures_tpot",
        ),
        "prefetch_lab_default_stream_queue_budget_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_queue_budget_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_contract_present": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_contract_present",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_contract_passed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_contract_passed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_contract_required_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_contract_required_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_contract_min_schedulable_packets": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_contract_min_schedulable_packets",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_issue_lead_tokens": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_issue_lead_tokens",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_schedulable_packet_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_schedulable_packet_count",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_clamped_issue_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_clamped_issue_count",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_duplicate_issue_key_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_duplicate_issue_key_count",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_row_shift_mismatch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_row_shift_mismatch_count",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_row_clamp_mismatch_count": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_row_clamp_mismatch_count",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_full_fetch_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_payload_transfer_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_payload_transfer_enabled",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_bytes": (
            _int_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_payload_bytes",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_runtime_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_full_fetch_runtime_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_full_fetch_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_ready_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_ready_credit",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_ready_before_demand_credit": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_ready_before_demand_credit",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_real_ready_credit_granted": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_real_ready_credit_granted",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_transfer_enabled": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_payload_transfer_enabled",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_payload_deref_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_payload_deref_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_kernel_arg_pass_allowed": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_kernel_arg_pass_allowed",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_passed_to_kernel": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_passed_to_kernel",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_changes_kernel_launch_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_changes_kernel_launch_args",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_current_wna16_arg_compatible": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_current_wna16_arg_compatible",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_requires_wna16_arg_reinterpretation",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_uses_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_uses_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_passes_current_wna16_args": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_passes_current_wna16_args",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_current_wna16_arg_compatible": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_current_wna16_arg_compatible",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_wna16_benchmark_ready": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_wna16_benchmark_ready",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_wna16_benchmark_ready": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_wna16_benchmark_ready",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_measures_tpot": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_measures_tpot",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_stream_shifted_issue_replay_source_measures_vllm_latency": (
            _bool_metric(
                prefetch_lab_default_full_fetch,
                "stream_shifted_issue_replay_source_measures_vllm_latency",
            )
        ),
        "prefetch_lab_default_metadata_decision": (
            prefetch_lab_default_decisions.get("metadata")
        ),
        "prefetch_lab_default_metadata_passed": (
            not bool(prefetch_lab_default_metadata.get("failures"))
        ),
        "prefetch_lab_default_metadata_failures": list(
            prefetch_lab_default_metadata.get("failures") or []
        ),
        "prefetch_lab_default_premap_decision": (
            prefetch_lab_default_decisions.get("premap")
        ),
        "prefetch_lab_default_premap_passed": (
            not bool(prefetch_lab_default_premap.get("failures"))
        ),
        "prefetch_lab_default_premap_failures": list(
            prefetch_lab_default_premap.get("failures") or []
        ),
        "prefetch_lab_default_premap_positive_count": _int_metric(
            prefetch_lab_default_premap,
            "premap_positive_count",
        ),
        "prefetch_lab_default_premap_recommended_capacity_entries": _int_metric(
            prefetch_lab_default_premap,
            "recommended_capacity_entries",
        ),
        "prefetch_lab_default_premap_no_eviction_capacity_entries": _int_metric(
            prefetch_lab_default_premap,
            "no_eviction_capacity_entries",
        ),
        "default_kernel_consumer_schema_name": (
            schema_summary.get("schema_name")
        ),
        "default_kernel_consumer_schema_hash": (
            schema_summary.get("schema_hash")
        ),
        "default_kernel_consumer_schema_artifact_sha256": (
            _path_label_sha256(
                default_kernel_consumer_schema_check.get("schema_path"),
                root=root,
            )
        ),
        "default_kernel_consumer_schema_row_field_names": (
            schema_summary.get("row_field_names") or []
        ),
        "default_kernel_consumer_schema_row_metadata_names": (
            schema_summary.get("row_metadata_names") or []
        ),
        "default_kernel_consumer_required_gate_checks": required_gate_checks,
        "default_kernel_consumer_consumer_view_required": (
            required_gate_checks.get("consumer_view_required")
        ),
        "default_kernel_consumer_consumer_view_row_layout_required": (
            required_gate_checks.get("consumer_view_row_layout_required")
        ),
        "default_kernel_consumer_consumer_view_handle_projection_required": (
            required_gate_checks.get("consumer_view_handle_projection_required")
        ),
        "default_kernel_consumer_consumer_view_all_handle_fields_required": (
            required_gate_checks.get("consumer_view_all_handle_fields_required")
        ),
        "default_kernel_consumer_consumer_view_source_packet_chain_depth_required": (
            required_gate_checks.get("consumer_view_source_packet_chain_depth_required")
        ),
        "default_kernel_consumer_consumer_program_view_required": (
            required_gate_checks.get("consumer_program_view_required")
        ),
        "default_kernel_consumer_consumer_program_view_row_assignment_formula_required": (
            required_gate_checks.get("consumer_program_view_row_assignment_formula")
        ),
        "default_kernel_consumer_request_launch_all_handle_fields_required": (
            required_gate_checks.get("request_launch_all_handle_fields_required")
        ),
        "default_kernel_consumer_request_launch_ptr_all_handle_fields_required": (
            required_gate_checks.get("request_launch_ptr_all_handle_fields_required")
        ),
        "default_kernel_consumer_required_gate_payload_bytes_required": (
            required_gate_checks.get("payload_bytes_required")
        ),
        "default_kernel_consumer_required_gate_passed_to_kernel_required": (
            required_gate_checks.get("passed_to_kernel_required")
        ),
        "default_kernel_consumer_required_gate_changes_kernel_launch_args_required": (
            required_gate_checks.get("changes_kernel_launch_args_required")
        ),
        "default_kernel_consumer_required_gate_current_wna16_arg_compatible_required": (
            required_gate_checks.get("current_wna16_arg_compatible_required")
        ),
        "default_kernel_consumer_future_kernel_args_layout_reported": (
            schema_summary.get("future_kernel_consumer_args_layout_reported")
        ),
        "default_kernel_consumer_future_kernel_args_layout_expected": (
            future_kernel_args_layout_expected
        ),
        "default_kernel_consumer_future_kernel_args_struct_size": (
            future_kernel_args_layout_expected.get(
                "future_kernel_consumer_args_struct_size"
            )
        ),
        "default_kernel_consumer_future_kernel_args_offset_field_mask": (
            future_kernel_args_layout_expected.get(
                "future_kernel_consumer_args_offset_field_mask"
            )
        ),
        "default_kernel_consumer_kernel_arg_packet_layout_reported": (
            schema_summary.get(
                "future_kernel_native_consumer_kernel_arg_packet_abi_layout_reported"
            )
        ),
        "default_kernel_consumer_kernel_arg_packet_layout_expected": (
            kernel_arg_packet_layout_expected
        ),
        "default_kernel_consumer_kernel_arg_packet_struct_size": (
            kernel_arg_packet_layout_expected.get(
                "future_kernel_native_consumer_kernel_arg_packet_struct_size"
            )
        ),
        "default_kernel_consumer_kernel_arg_packet_offset_program_view_ptr": (
            kernel_arg_packet_layout_expected.get(
                "future_kernel_native_consumer_kernel_arg_packet_offset_program_view_ptr"
            )
        ),
        "default_kernel_consumer_kernel_entry_summary_layout_reported": (
            schema_summary.get(
                "future_kernel_native_consumer_kernel_entry_summary_abi_layout_reported"
            )
        ),
        "default_kernel_consumer_kernel_entry_summary_layout_expected": (
            kernel_entry_summary_layout_expected
        ),
        "default_kernel_consumer_kernel_entry_summary_struct_size": (
            kernel_entry_summary_layout_expected.get(
                "future_kernel_native_consumer_kernel_entry_summary_struct_size"
            )
        ),
        "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator": (
            kernel_entry_summary_layout_expected.get(
                "future_kernel_native_consumer_kernel_entry_summary_offset_row_hash_accumulator"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_layout_reported": (
            schema_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_abi_layout_reported"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_layout_expected": (
            kernel_entry_args_layout_expected
        ),
        "default_kernel_consumer_kernel_entry_args_struct_size": (
            kernel_entry_args_layout_expected.get(
                "future_kernel_native_consumer_kernel_entry_args_struct_size"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_offset_summary": (
            kernel_entry_args_layout_expected.get(
                "future_kernel_native_consumer_kernel_entry_args_offset_summary"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_checked": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_checked"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_field_read_path": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_field_read_path"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_packet_chain_depth": (
            _int_metric(
                online_merged_arg_slot_summary,
                "future_kernel_native_consumer_kernel_entry_args_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_kernel_entry_args_summary_row_count": (
            kernel_entry_args_summary_row_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_row_ok_count": (
            kernel_entry_args_summary_row_ok_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count": (
            kernel_entry_args_summary_descriptor_ptr_read_row_ok_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count": (
            kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count": (
            kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count": (
            kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count": (
            kernel_entry_args_summary_row_metadata_read_row_ok_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_error_count": (
            kernel_entry_args_summary_error_count
        ),
        "default_kernel_consumer_kernel_entry_args_summary_field_mask": (
            _int_metric(
                online_merged_arg_slot_summary,
                "future_kernel_native_consumer_kernel_entry_args_summary_field_mask",
            )
        ),
        "default_kernel_consumer_kernel_entry_args_summary_row_hash_accumulator": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_summary_row_hash_accumulator"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_summary_field_read_hash_accumulator"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_all_handle_fields_read": (
            kernel_entry_args_all_handle_fields_read
        ),
        "default_kernel_consumer_kernel_entry_args_payload_bytes": (
            _int_metric(
                online_merged_arg_slot_summary,
                "future_kernel_native_consumer_kernel_entry_args_payload_bytes",
            )
        ),
        "default_kernel_consumer_kernel_entry_args_passed_to_kernel": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_changes_kernel_launch_args": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_current_wna16_arg_compatible": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation": (
            online_merged_arg_slot_summary.get(
                "future_kernel_native_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_request_ptr_checked": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_checked"
            )
        ),
        "default_kernel_consumer_request_ptr_field_read_path": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_field_read_path"
            )
        ),
        "default_kernel_consumer_request_ptr_packet_chain_depth": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_request_ptr_summary_row_count": (
            request_ptr_summary_row_count
        ),
        "default_kernel_consumer_request_ptr_summary_row_ok_count": (
            request_ptr_summary_row_ok_count
        ),
        "default_kernel_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count": (
            request_ptr_summary_descriptor_ptr_read_row_ok_count
        ),
        "default_kernel_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count": (
            request_ptr_summary_packed_weight_descriptor_read_row_ok_count
        ),
        "default_kernel_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count": (
            request_ptr_summary_scale_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count": (
            request_ptr_summary_aux_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_request_ptr_summary_row_metadata_read_row_ok_count": (
            request_ptr_summary_row_metadata_read_row_ok_count
        ),
        "default_kernel_consumer_request_ptr_summary_error_count": (
            request_ptr_summary_error_count
        ),
        "default_kernel_consumer_request_ptr_summary_field_mask": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_summary_field_mask",
            )
        ),
        "default_kernel_consumer_request_ptr_summary_row_hash_accumulator": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_ptr_summary_field_read_hash_accumulator": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_ptr_summary_row_metadata_hash_accumulator": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_checked": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_checked"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_field_name": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_field_name"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_source": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_source"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_row_count": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_single_field_handoff_row_count",
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_row_ok_count": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_single_field_handoff_row_ok_count",
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_error_count": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_single_field_handoff_error_count",
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_hash_accumulator": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_payload_bytes": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_single_field_handoff_payload_bytes",
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_passed_to_kernel": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_changes_kernel_launch_args": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_current_wna16_arg_compatible": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_request_ptr_single_field_handoff_requires_wna16_arg_reinterpretation": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_single_field_handoff_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_request_ptr_all_handle_fields_read": (
            request_ptr_all_handle_fields_read
        ),
        "default_kernel_consumer_request_ptr_payload_bytes": (
            _int_metric(
                request_ptr_summary_source,
                "future_kernel_native_consumer_request_ptr_payload_bytes",
            )
        ),
        "default_kernel_consumer_request_ptr_passed_to_kernel": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_request_ptr_kernel_arg_pass_allowed": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_kernel_arg_pass_allowed"
            )
        ),
        "default_kernel_consumer_request_ptr_changes_kernel_launch_args": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_request_ptr_current_wna16_arg_compatible": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_request_ptr_requires_wna16_arg_reinterpretation": (
            request_ptr_summary_source.get(
                "future_kernel_native_consumer_request_ptr_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_request_launch_checked": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_checked"
            )
        ),
        "default_kernel_consumer_request_launch_field_read_path": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_field_read_path"
            )
        ),
        "default_kernel_consumer_request_launch_packet_chain_depth": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_request_launch_device_ordinal": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_device_ordinal",
            )
        ),
        "default_kernel_consumer_request_launch_grid_x": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_grid_x",
            )
        ),
        "default_kernel_consumer_request_launch_block_x": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_block_x",
            )
        ),
        "default_kernel_consumer_request_launch_row_offset": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_row_offset",
            )
        ),
        "default_kernel_consumer_request_launch_row_limit": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_row_limit",
            )
        ),
        "default_kernel_consumer_request_launch_rows_per_program": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_rows_per_program",
            )
        ),
        "default_kernel_consumer_request_launch_summary_row_count": (
            request_launch_summary_row_count
        ),
        "default_kernel_consumer_request_launch_summary_row_ok_count": (
            request_launch_summary_row_ok_count
        ),
        "default_kernel_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count": (
            request_launch_summary_descriptor_ptr_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count": (
            request_launch_summary_packed_weight_descriptor_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count": (
            request_launch_summary_scale_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count": (
            request_launch_summary_aux_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_summary_row_metadata_read_row_ok_count": (
            request_launch_summary_row_metadata_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_summary_error_count": (
            request_launch_summary_error_count
        ),
        "default_kernel_consumer_request_launch_summary_field_mask": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_summary_field_mask",
            )
        ),
        "default_kernel_consumer_request_launch_summary_row_hash_accumulator": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_summary_field_read_hash_accumulator": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_summary_field_read_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_summary_row_metadata_hash_accumulator": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_summary_row_metadata_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_checked": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_checked"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_field_name": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_field_name"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_source": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_source"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_row_count": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_single_field_handoff_row_count",
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_row_ok_count": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_single_field_handoff_row_ok_count",
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_error_count": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_single_field_handoff_error_count",
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_hash_accumulator": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_payload_bytes": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_single_field_handoff_payload_bytes",
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_passed_to_kernel": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_changes_kernel_launch_args": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_current_wna16_arg_compatible": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_request_launch_single_field_handoff_requires_wna16_arg_reinterpretation": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_single_field_handoff_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_request_launch_all_handle_fields_read": (
            request_launch_all_handle_fields_read
        ),
        "default_kernel_consumer_request_launch_payload_bytes": (
            _int_metric(
                request_launch_summary_source,
                "future_kernel_native_consumer_request_launch_payload_bytes",
            )
        ),
        "default_kernel_consumer_request_launch_passed_to_kernel": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_request_launch_kernel_arg_pass_allowed": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed"
            )
        ),
        "default_kernel_consumer_request_launch_changes_kernel_launch_args": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_request_launch_current_wna16_arg_compatible": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_request_launch_requires_wna16_arg_reinterpretation": (
            request_launch_summary_source.get(
                "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_checked": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_checked"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_field_read_path": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_field_read_path"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_packet_chain_depth": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_summary_row_count": (
            request_launch_ptr_summary_row_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_row_ok_count": (
            request_launch_ptr_summary_row_ok_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_descriptor_ptr_read_row_ok_count": (
            request_launch_ptr_summary_descriptor_ptr_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count": (
            request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count": (
            request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count": (
            request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count": (
            request_launch_ptr_summary_row_metadata_read_row_ok_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_error_count": (
            request_launch_ptr_summary_error_count
        ),
        "default_kernel_consumer_request_launch_ptr_summary_field_mask": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_summary_field_mask",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_summary_row_hash_accumulator": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_summary_row_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_summary_field_read_hash_accumulator": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_summary_field_read_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_checked": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_checked"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_field_name": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_field_name"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_source": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_source"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_row_count": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_row_count",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_row_ok_count": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_row_ok_count",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_error_count": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_error_count",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_hash_accumulator": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_hash_accumulator"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_payload_bytes": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_payload_bytes",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_passed_to_kernel": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_changes_kernel_launch_args": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_current_wna16_arg_compatible": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_single_field_handoff_requires_wna16_arg_reinterpretation": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_single_field_handoff_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_all_handle_fields_read": (
            request_launch_ptr_all_handle_fields_read
        ),
        "default_kernel_consumer_request_launch_ptr_payload_bytes": (
            _int_metric(
                request_launch_ptr_summary_source,
                "future_kernel_native_consumer_request_launch_ptr_payload_bytes",
            )
        ),
        "default_kernel_consumer_request_launch_ptr_passed_to_kernel": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_passed_to_kernel"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_kernel_arg_pass_allowed": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_changes_kernel_launch_args": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_current_wna16_arg_compatible": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation": (
            request_launch_ptr_summary_source.get(
                "future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation"
            )
        ),
        "default_kernel_consumer_dispatch_abi_name": (
            schema_summary.get("future_kernel_native_consumer_dispatch_abi_name")
        ),
        "default_kernel_consumer_dispatch_abi_struct": (
            schema_summary.get("future_kernel_native_consumer_dispatch_abi_struct")
        ),
        "default_kernel_consumer_dispatch_abi_mode": (
            schema_summary.get("future_kernel_native_consumer_dispatch_abi_mode")
        ),
        "default_kernel_consumer_dispatch_abi_row_assignment_formula": (
            schema_summary.get(
                "future_kernel_native_consumer_dispatch_abi_row_assignment_formula"
            )
        ),
        "default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible": (
            schema_summary.get(
                "future_kernel_native_consumer_dispatch_abi_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_dispatch_full_table_required": (
            _observed_default_contract_value(
                "future_kernel_native_dispatch_consumer_full_table_required"
            )
        ),
        "default_kernel_consumer_dispatch_runner_evidence_label": (
            dispatch_runner_evidence_label
        ),
        "default_kernel_consumer_dispatch_runner_evidence_path": (
            dispatch_runner_evidence_row.get("path")
        ),
        "default_kernel_consumer_dispatch_runner_evidence_sha256": (
            _evidence_row_sha256(dispatch_runner_evidence_row)
        ),
        "default_kernel_consumer_dispatch_runner_evidence_present": (
            dispatch_runner_evidence_present
        ),
        "default_kernel_consumer_dispatch_runner_evidence_passed": (
            dispatch_runner_evidence_passed
        ),
        "default_kernel_consumer_dispatch_runner_evidence_failure": (
            dispatch_runner_evidence_row.get("failure")
        ),
        "default_kernel_consumer_dispatch_runner_artifact_evidence_label": (
            dispatch_runner_artifact_evidence_label
        ),
        "default_kernel_consumer_dispatch_runner_artifact_evidence_path": (
            dispatch_runner_artifact_evidence_row.get("path")
        ),
        "default_kernel_consumer_dispatch_runner_artifact_evidence_sha256": (
            _evidence_row_sha256(dispatch_runner_artifact_evidence_row)
        ),
        "default_kernel_consumer_dispatch_runner_artifact_evidence_present": (
            dispatch_runner_artifact_evidence_present
        ),
        "default_kernel_consumer_dispatch_runner_artifact_evidence_passed": (
            dispatch_runner_artifact_evidence_passed
        ),
        "default_kernel_consumer_dispatch_runner_artifact_evidence_failure": (
            dispatch_runner_artifact_evidence_row.get("failure")
        ),
        "default_kernel_consumer_dispatch_runner_online_input_count": (
            _int_metric(dispatch_runner_payload, "online_prelaunch_input_check_count")
        ),
        "default_kernel_consumer_dispatch_runner_online_extra_input_count": (
            _int_metric(
                dispatch_runner_payload,
                "online_prelaunch_input_extra_check_count",
            )
        ),
        "default_kernel_consumer_dispatch_runner_online_extra_input_passed_count": (
            _int_metric(
                dispatch_runner_payload,
                "online_prelaunch_input_extra_check_passed_count",
            )
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_passed": (
            dispatch_runner_artifact_evidence_passed
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_min_online_inputs": (
            _int_metric(dispatch_runner_artifact_payload, "min_online_inputs")
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_row_count_min": (
            _int_metric(
                dispatch_runner_artifact_payload,
                "runner_online_prelaunch_input_row_count_min",
            )
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_row_count_max": (
            _int_metric(
                dispatch_runner_artifact_payload,
                "runner_online_prelaunch_input_row_count_max",
            )
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_row_count_sum": (
            _int_metric(
                dispatch_runner_artifact_payload,
                "runner_online_prelaunch_input_row_count_sum",
            )
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_row_count_diverse": (
            _bool_metric(
                dispatch_runner_artifact_payload,
                "runner_online_prelaunch_input_row_count_diverse",
            )
        ),
        "default_kernel_consumer_dispatch_runner_artifact_check_final_deferred_count": (
            _int_metric(dispatch_runner_artifact_payload, "final_deferred_count")
        ),
        "default_kernel_consumer_online_merged_multiprogram_evidence_label": (
            online_merged_multiprogram_runner_evidence_label
        ),
        "default_kernel_consumer_online_merged_multiprogram_evidence_path": (
            online_merged_multiprogram_runner_evidence_row.get("path")
        ),
        "default_kernel_consumer_online_merged_multiprogram_evidence_sha256": (
            _evidence_row_sha256(online_merged_multiprogram_runner_evidence_row)
        ),
        "default_kernel_consumer_online_merged_multiprogram_evidence_passed": (
            _evidence_row_passed(online_merged_multiprogram_runner_evidence_row)
        ),
        "default_kernel_consumer_online_merged_multiprogram_source_count": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "selected_source_count",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_source_context_count": (
            online_merged_multiprogram_source_context_count
        ),
        "default_kernel_consumer_online_merged_multiprogram_source_context_matches_source_count": (
            online_merged_multiprogram_source_context_count is not None
            and online_merged_multiprogram_source_context_count
            == _int_metric(
                online_merged_multiprogram_runner_payload, "selected_source_count"
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_source_identity_count": (
            len(online_merged_multiprogram_source_identities)
        ),
        "default_kernel_consumer_online_merged_multiprogram_source_identity_coverage": (
            online_merged_multiprogram_source_context_count is not None
            and len(online_merged_multiprogram_source_identities)
            == online_merged_multiprogram_source_context_count
        ),
        "default_kernel_consumer_online_merged_multiprogram_source_identity_digest": (
            _source_identity_digest(online_merged_multiprogram_source_identities)
        ),
        "default_kernel_consumer_online_merged_multiprogram_row_count": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "merged_row_count",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "dispatch_row_offset",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "dispatch_row_limit",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "dispatch_active_rows",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_device": (
            _int_metric(online_merged_multiprogram_runner_payload, "device")
        ),
        "default_kernel_consumer_online_merged_multiprogram_hip_visible_devices": (
            online_merged_multiprogram_runner_payload.get("hip_visible_devices")
            if isinstance(
                online_merged_multiprogram_runner_payload.get("hip_visible_devices"),
                str,
            )
            else None
        ),
        "default_kernel_consumer_online_merged_multiprogram_mirror_field": (
            online_merged_multiprogram_runner_payload.get("mirror_field")
            if isinstance(
                online_merged_multiprogram_runner_payload.get("mirror_field"),
                str,
            )
            else None
        ),
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "not_a_single_vllm_launch_table",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_hashchain_equal": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "handle_projection_hashchain_equal",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "handle_projection_all_handle_fields_checked",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_no_payload": (
            _bool_metric(online_merged_multiprogram_runner_payload, "no_payload")
        ),
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "passed_to_kernel",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_abi": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "require_kernel_invocation_abi",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_entry_abi": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "require_kernel_invocation_entry_abi",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_abi": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "require_kernel_endpoint_abi",
            )
        ),
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_ptr_abi": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "require_kernel_endpoint_ptr_abi",
            )
        ),
        "default_kernel_consumer_kernel_invocation_checked": (
            _bool_metric(online_merged_multiprogram_runner_payload, "kernel_invocation_checked")
        ),
        "default_kernel_consumer_kernel_invocation_all_handle_fields_read": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_kernel_invocation_packet_chain_depth": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_kernel_invocation_payload_bytes": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_payload_bytes",
            )
        ),
        "default_kernel_consumer_kernel_invocation_passed_to_kernel": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_kernel_invocation_kernel_arg_pass_allowed": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_kernel_invocation_current_wna16_arg_compatible": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_kernel_invocation_row_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_row_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_invocation_field_read_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_field_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_invocation_row_metadata_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_row_metadata_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_checked": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_checked",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_all_handle_fields_read": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_packet_chain_depth": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_payload_bytes": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_payload_bytes",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_passed_to_kernel": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_kernel_arg_pass_allowed": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_current_wna16_arg_compatible": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_row_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_row_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_field_read_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_field_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_invocation_entry_row_metadata_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_invocation_entry_row_metadata_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_checked": (
            _bool_metric(online_merged_multiprogram_runner_payload, "kernel_endpoint_checked")
        ),
        "default_kernel_consumer_kernel_endpoint_all_handle_fields_read": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_packet_chain_depth": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_payload_bytes": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_payload_bytes",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_passed_to_kernel": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_kernel_arg_pass_allowed": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_changes_kernel_launch_args": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_current_wna16_arg_compatible": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_row_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_row_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_field_read_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_field_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_row_metadata_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_row_metadata_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_checked": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_checked",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_all_handle_fields_read": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_packet_chain_depth": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_payload_bytes": (
            _int_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_payload_bytes",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_passed_to_kernel": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_kernel_arg_pass_allowed": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_changes_kernel_launch_args": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_row_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_row_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_field_read_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_field_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_kernel_endpoint_ptr_row_metadata_hash_accumulator": (
            _hex_metric_text(
                online_merged_multiprogram_runner_payload,
                "kernel_endpoint_ptr_row_metadata_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_evidence_present": (
            _evidence_row_passed(wna16_adjacent_typed_slot_evidence_row)
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_required": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "require_wna16_adjacent_typed_slot",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_checked": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_checked",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_name": (
            wna16_adjacent_typed_slot_payload.get("wna16_adjacent_typed_slot_name")
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_mode": (
            wna16_adjacent_typed_slot_payload.get("wna16_adjacent_typed_slot_mode")
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_source": (
            wna16_adjacent_typed_slot_payload.get("wna16_adjacent_typed_slot_source")
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_row_count": (
            _int_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_row_count",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_row_ok_count": (
            _int_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_error_count": (
            _int_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_error_count",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_all_handle_fields_read": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_packet_chain_depth": (
            _int_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_payload_bytes": (
            _int_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_payload_bytes",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_passed_to_kernel": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_changes_kernel_launch_args": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_current_wna16_arg_compatible": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_explicit_typed_abi_slot": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_explicit_typed_abi_slot",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot": (
            _bool_metric(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_row_hash_accumulator": (
            _hex_metric_text(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_row_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_field_read_hash_accumulator": (
            _hex_metric_text(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_field_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_adjacent_typed_slot_row_metadata_hash_accumulator": (
            _hex_metric_text(
                wna16_adjacent_typed_slot_payload,
                "wna16_adjacent_typed_slot_row_metadata_hash_accumulator",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_label": (
            fourth_field_handoff_evidence_label
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_path": (
            fourth_field_handoff_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_sha256": (
            _evidence_row_sha256(fourth_field_handoff_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_passed": (
            _evidence_row_passed(fourth_field_handoff_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_artifact_kind": (
            fourth_field_handoff_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_name": (
            fourth_field_handoff_payload.get("fourth_field_handoff_canary_name")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_mode": (
            fourth_field_handoff_payload.get("fourth_field_handoff_canary_mode")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_source": (
            fourth_field_handoff_payload.get("fourth_field_handoff_canary_source")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_first_field": (
            fourth_field_handoff_payload.get("first_field_name")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_second_field": (
            fourth_field_handoff_payload.get("second_field_name")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field": (
            fourth_field_handoff_payload.get("third_field_name")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_fourth_field": (
            fourth_field_handoff_payload.get("fourth_field_name")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_fourth_field_kind": (
            _int_metric(fourth_field_handoff_payload, "fourth_field_kind")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_fourth_field_mask": (
            _int_metric(fourth_field_handoff_payload, "fourth_field_mask")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_source_count": (
            _int_metric(fourth_field_handoff_payload, "source_count")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_previous_source_count": (
            _int_metric(fourth_field_handoff_payload, "previous_field_input_json_count")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_row_count": (
            _int_metric(fourth_field_handoff_payload, "row_count")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_row_ok_count": (
            _int_metric(fourth_field_handoff_payload, "row_ok_count")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_row_ok_count": (
            _int_metric(
                fourth_field_handoff_payload,
                "fourth_field_handoff_field_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_count": (
            _int_metric(
                fourth_field_handoff_payload,
                "fourth_field_handoff_canary_runner_row_count",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_ok_count": (
            _int_metric(
                fourth_field_handoff_payload,
                "fourth_field_handoff_canary_runner_row_ok_count",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_hash": (
            _hex_metric_text(
                fourth_field_handoff_payload,
                "fourth_field_handoff_field_read_hash",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_hash": (
            _hex_metric_text(
                fourth_field_handoff_payload,
                "fourth_field_handoff_canary_runner_hash",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field_read_hash": (
            _hex_metric_text(fourth_field_handoff_payload, "third_field_read_hash")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field_native_hash": (
            _hex_metric_text(fourth_field_handoff_payload, "third_field_native_hash")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_previous_gate_ready": (
            _bool_metric(fourth_field_handoff_payload, "previous_field_gate_ready")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_native_requested": (
            _bool_metric(
                fourth_field_handoff_payload,
                "fourth_field_handoff_canary_native_requested",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_native_executed": (
            _bool_metric(
                fourth_field_handoff_payload,
                "fourth_field_handoff_canary_native_executed",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_native_passed": (
            _bool_metric(
                fourth_field_handoff_payload,
                "fourth_field_handoff_canary_native_passed",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_live_enabled": (
            _bool_metric(fourth_field_handoff_payload, "fourth_field_handoff_live_enabled")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_block_reason": (
            fourth_field_handoff_payload.get("fourth_field_handoff_block_reason")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_bytes": (
            _int_metric(fourth_field_handoff_payload, "payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_expected_payload_bytes": (
            _int_metric(fourth_field_handoff_payload, "expected_payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_deref_allowed": (
            _bool_metric(fourth_field_handoff_payload, "payload_deref_allowed")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_kernel_arg_pass_allowed": (
            _bool_metric(fourth_field_handoff_payload, "kernel_arg_pass_allowed")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_passed_to_kernel": (
            _bool_metric(fourth_field_handoff_payload, "passed_to_kernel")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_changes_kernel_launch_args": (
            _bool_metric(fourth_field_handoff_payload, "changes_kernel_launch_args")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_current_wna16_arg_compatible": (
            _bool_metric(fourth_field_handoff_payload, "current_wna16_arg_compatible")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                fourth_field_handoff_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_uses_current_wna16_args": (
            _bool_metric(fourth_field_handoff_payload, "uses_current_wna16_args")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_passes_current_wna16_args": (
            _bool_metric(fourth_field_handoff_payload, "passes_current_wna16_args")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_measures_tpot": (
            _bool_metric(fourth_field_handoff_payload, "measures_tpot")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_measures_vllm_latency": (
            _bool_metric(fourth_field_handoff_payload, "measures_vllm_latency")
        ),
        "default_kernel_consumer_future_wna16_fourth_field_handoff_wna16_benchmark_ready": (
            _bool_metric(fourth_field_handoff_payload, "wna16_benchmark_ready")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_label": (
            all_four_field_consumer_evidence_label
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_path": (
            all_four_field_consumer_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_sha256": (
            _evidence_row_sha256(all_four_field_consumer_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_passed": (
            _evidence_row_passed(all_four_field_consumer_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_artifact_kind": (
            all_four_field_consumer_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_name": (
            all_four_field_consumer_payload.get("all_four_field_consumer_name")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_mode": (
            all_four_field_consumer_payload.get("all_four_field_consumer_mode")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_source": (
            all_four_field_consumer_payload.get("all_four_field_consumer_source")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_stage_type": (
            all_four_field_consumer_payload.get("stage_type")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_bench_semantics": (
            _bool_metric(all_four_field_consumer_payload, "bench_semantics")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_source_count": (
            _int_metric(all_four_field_consumer_payload, "source_count")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_row_count": (
            _int_metric(all_four_field_consumer_payload, "row_count")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_row_ok_count": (
            _int_metric(all_four_field_consumer_payload, "row_ok_count")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_count": (
            _int_metric(all_four_field_consumer_payload, "selected_input_json_count")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_manifest_sha256": (
            all_four_field_consumer_payload.get("selected_input_manifest_sha256")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_post_native_input_manifest_sha256": (
            all_four_field_consumer_payload.get("post_native_input_manifest_sha256")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_json": (
            all_four_field_consumer_payload.get("fourth_field_json")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_path_label": (
            all_four_field_consumer_fourth_field_path_label
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_sha256": (
            all_four_field_consumer_payload.get("fourth_field_sha256")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_native_executed": (
            _bool_metric(all_four_field_consumer_payload, "native_consumer_executed")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_native_passed": (
            _bool_metric(all_four_field_consumer_payload, "native_consumer_passed")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_future_kernel_side_all_fields_read": (
            _bool_metric(
                all_four_field_consumer_payload,
                "future_wna16_kernel_side_consumer_execution_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_wna16_side_all_fields_read": (
            _bool_metric(
                all_four_field_consumer_payload,
                "wna16_side_consumer_variant_execution_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_payload_bytes": (
            _int_metric(all_four_field_consumer_payload, "payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_payload_deref_allowed": (
            _bool_metric(all_four_field_consumer_payload, "payload_deref_allowed")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_kernel_arg_pass_allowed": (
            _bool_metric(all_four_field_consumer_payload, "kernel_arg_pass_allowed")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_passed_to_kernel": (
            _bool_metric(all_four_field_consumer_payload, "passed_to_kernel")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_changes_kernel_launch_args": (
            _bool_metric(all_four_field_consumer_payload, "changes_kernel_launch_args")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_current_wna16_arg_compatible": (
            _bool_metric(all_four_field_consumer_payload, "current_wna16_arg_compatible")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                all_four_field_consumer_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_measures_tpot": (
            _bool_metric(all_four_field_consumer_payload, "measures_tpot")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_measures_vllm_latency": (
            _bool_metric(all_four_field_consumer_payload, "measures_vllm_latency")
        ),
        "default_kernel_consumer_future_wna16_all_four_consumer_wna16_benchmark_ready": (
            _bool_metric(all_four_field_consumer_payload, "wna16_benchmark_ready")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_label": (
            future_wna16_kernel_side_path_evidence_label
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_path": (
            future_wna16_kernel_side_path_evidence_row.get("path_label")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_sha256": (
            future_wna16_kernel_side_path_evidence_row.get("sha256")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_passed": (
            _evidence_row_passed(future_wna16_kernel_side_path_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_artifact_kind": (
            future_wna16_kernel_side_path_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_name": (
            future_wna16_kernel_side_path_payload.get(
                "kernel_side_typed_consumer_path_name"
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_mode": (
            future_wna16_kernel_side_path_payload.get(
                "kernel_side_typed_consumer_path_mode"
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_source": (
            future_wna16_kernel_side_path_payload.get(
                "kernel_side_typed_consumer_path_source"
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_stage_type": (
            future_wna16_kernel_side_path_payload.get("stage_type")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_bench_semantics": (
            _bool_metric(future_wna16_kernel_side_path_payload, "bench_semantics")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_gate_ready": (
            _bool_metric(future_wna16_kernel_side_path_payload, "all_four_gate_ready")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_json": (
            future_wna16_kernel_side_path_all_four_json
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_path_label": (
            future_wna16_kernel_side_path_all_four_path_label
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_sha256": (
            future_wna16_kernel_side_path_payload.get("all_four_sha256")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_source_count": (
            _int_metric(future_wna16_kernel_side_path_payload, "source_count")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_input_json_count": (
            _int_metric(future_wna16_kernel_side_path_payload, "input_json_count")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_count": (
            _int_metric(future_wna16_kernel_side_path_payload, "row_count")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_ok_count": (
            _int_metric(future_wna16_kernel_side_path_payload, "row_ok_count")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_selected_input_manifest_sha256": (
            future_wna16_kernel_side_path_payload.get(
                "selected_input_manifest_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_native_executed": (
            _bool_metric(future_wna16_kernel_side_path_payload, "native_consumer_executed")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_native_passed": (
            _bool_metric(future_wna16_kernel_side_path_payload, "native_consumer_passed")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_independent_path": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "independent_kernel_side_consumer_path",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_explicit_typed_abi_slot": (
            _bool_metric(future_wna16_kernel_side_path_payload, "explicit_typed_abi_slot")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_future_kernel_side_checked": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "future_wna16_kernel_side_consumer_execution_checked",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_future_kernel_side_all_fields_read": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "future_wna16_kernel_side_consumer_execution_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_side_checked": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "wna16_side_consumer_variant_execution_checked",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_side_all_fields_read": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "wna16_side_consumer_variant_execution_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_payload_bytes": (
            _int_metric(future_wna16_kernel_side_path_payload, "payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_payload_deref_allowed": (
            _bool_metric(future_wna16_kernel_side_path_payload, "payload_deref_allowed")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_kernel_arg_pass_allowed": (
            _bool_metric(future_wna16_kernel_side_path_payload, "kernel_arg_pass_allowed")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_passed_to_kernel": (
            _bool_metric(future_wna16_kernel_side_path_payload, "passed_to_kernel")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_changes_kernel_launch_args": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_current_wna16_arg_compatible": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                future_wna16_kernel_side_path_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_uses_current_wna16_args": (
            _bool_metric(future_wna16_kernel_side_path_payload, "uses_current_wna16_args")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_measures_tpot": (
            _bool_metric(future_wna16_kernel_side_path_payload, "measures_tpot")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_measures_vllm_latency": (
            _bool_metric(future_wna16_kernel_side_path_payload, "measures_vllm_latency")
        ),
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_benchmark_ready": (
            _bool_metric(future_wna16_kernel_side_path_payload, "wna16_benchmark_ready")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_evidence_label": (
            future_wna16_payloadless_execution_evidence_label
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_evidence_path": (
            future_wna16_payloadless_execution_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_evidence_sha256": (
            _evidence_row_sha256(future_wna16_payloadless_execution_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_evidence_passed": (
            _evidence_row_passed(future_wna16_payloadless_execution_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_artifact_kind": (
            future_wna16_payloadless_execution_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_name": (
            future_wna16_payloadless_execution_payload.get("payloadless_execution_name")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_mode": (
            future_wna16_payloadless_execution_payload.get("payloadless_execution_mode")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_source": (
            future_wna16_payloadless_execution_payload.get("payloadless_execution_source")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_scope": (
            future_wna16_payloadless_execution_payload.get("payloadless_execution_scope")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_source_count": (
            _int_metric(future_wna16_payloadless_execution_payload, "source_count")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_row_count": (
            _int_metric(future_wna16_payloadless_execution_payload, "row_count")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_row_ok_count": (
            _int_metric(future_wna16_payloadless_execution_payload, "row_ok_count")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_gate_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_gate_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_lab_preflight_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_lab_preflight_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_native_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_native_artifact_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_native_requested": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_native_requested",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_native_executed": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_native_executed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_native_passed": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_native_passed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_native_host_wall_ms": (
            _float_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_native_host_wall_ms",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_outer_wall_ms": (
            _float_metric(
                future_wna16_payloadless_execution_payload,
                "payloadless_execution_outer_wall_ms",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_all_four_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "all_four_field_consumer_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_all_four_fields_read": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "all_four_field_consumer_fields_read",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_kernel_side_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "future_wna16_kernel_side_typed_consumer_path_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_kernel_side_hashes_valid": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "future_wna16_kernel_side_typed_consumer_path_hashes_valid",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_benchmark_repeat_count": (
            _int_metric(
                future_wna16_payloadless_execution_payload,
                "benchmark_repeat_count_measured",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_payload_bytes": (
            _int_metric(future_wna16_payloadless_execution_payload, "payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_payload_deref_allowed": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "payload_deref_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_kernel_arg_pass_allowed": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_passed_to_kernel": (
            _bool_metric(future_wna16_payloadless_execution_payload, "passed_to_kernel")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_changes_kernel_launch_args": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_current_wna16_arg_compatible": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_uses_current_wna16_args": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "uses_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_measures_tpot": (
            _bool_metric(future_wna16_payloadless_execution_payload, "measures_tpot")
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_measures_vllm_latency": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "measures_vllm_latency",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_execution_wna16_benchmark_ready": (
            _bool_metric(
                future_wna16_payloadless_execution_payload,
                "wna16_benchmark_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_evidence_label": (
            future_wna16_variant_execution_evidence_label
        ),
        "default_kernel_consumer_future_wna16_variant_execution_evidence_path": (
            future_wna16_variant_execution_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_evidence_sha256": (
            _evidence_row_sha256(future_wna16_variant_execution_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_variant_execution_evidence_passed": (
            _evidence_row_passed(future_wna16_variant_execution_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_variant_execution_artifact_kind": (
            future_wna16_variant_execution_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_name": (
            future_wna16_variant_execution_payload.get("execution_name")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_mode": (
            future_wna16_variant_execution_payload.get("execution_mode")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_source": (
            future_wna16_variant_execution_payload.get("execution_source")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_scope": (
            future_wna16_variant_execution_payload.get(
                "future_wna16_variant_execution_scope"
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_source_count": (
            _int_metric(future_wna16_variant_execution_payload, "source_count")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_row_count": (
            _int_metric(future_wna16_variant_execution_payload, "row_count")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_row_ok_count": (
            _int_metric(future_wna16_variant_execution_payload, "row_ok_count")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_ready": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_payloadless_gate_ready": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "payloadless_gate_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_requested": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_native_requested",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_executed": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_native_executed",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_passed": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_native_passed",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_artifact_ready": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_native_artifact_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_host_wall_ms": (
            _float_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_native_host_wall_ms",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_outer_wall_ms": (
            _float_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_outer_wall_ms",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_not_current_wna16_kernel": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "future_wna16_variant_execution_not_current_wna16_kernel",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_payload_bytes": (
            _int_metric(future_wna16_variant_execution_payload, "payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_payload_deref_allowed": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "payload_deref_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_kernel_arg_pass_allowed": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_passed_to_kernel": (
            _bool_metric(future_wna16_variant_execution_payload, "passed_to_kernel")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_changes_kernel_launch_args": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_current_wna16_arg_compatible": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_uses_current_wna16_args": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "uses_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_passes_current_wna16_args": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "passes_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_measures_tpot": (
            _bool_metric(future_wna16_variant_execution_payload, "measures_tpot")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_measures_vllm_latency": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "measures_vllm_latency",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_wna16_benchmark_ready": (
            _bool_metric(
                future_wna16_variant_execution_payload,
                "wna16_benchmark_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_payloadless_json": (
            _path_label(
                _path_for_label(
                    future_wna16_variant_execution_payload.get("payloadless_json"),
                    root,
                ),
                root=root,
            )
            if isinstance(
                future_wna16_variant_execution_payload.get("payloadless_json"),
                str,
            )
            and future_wna16_variant_execution_payload.get("payloadless_json")
            else future_wna16_variant_execution_payload.get("payloadless_json")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_payloadless_sha256": (
            future_wna16_variant_execution_payload.get("payloadless_sha256")
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_json": (
            _path_label(
                _path_for_label(
                    future_wna16_variant_execution_payload.get(
                        "future_wna16_variant_execution_native_json"
                    ),
                    root,
                ),
                root=root,
            )
            if isinstance(
                future_wna16_variant_execution_payload.get(
                    "future_wna16_variant_execution_native_json"
                ),
                str,
            )
            and future_wna16_variant_execution_payload.get(
                "future_wna16_variant_execution_native_json"
            )
            else future_wna16_variant_execution_payload.get(
                "future_wna16_variant_execution_native_json"
            )
        ),
        "default_kernel_consumer_future_wna16_variant_execution_native_sha256": (
            future_wna16_variant_execution_payload.get(
                "future_wna16_variant_execution_native_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_evidence_label": (
            future_wna16_useful_consumer_evidence_label
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_evidence_path": (
            future_wna16_useful_consumer_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_evidence_sha256": (
            _evidence_row_sha256(future_wna16_useful_consumer_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_evidence_passed": (
            _evidence_row_passed(future_wna16_useful_consumer_evidence_row)
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_artifact_kind": (
            future_wna16_useful_consumer_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_name": (
            future_wna16_useful_consumer_payload.get("useful_consumer_name")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_mode": (
            future_wna16_useful_consumer_payload.get("useful_consumer_mode")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_source": (
            future_wna16_useful_consumer_payload.get("useful_consumer_source")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_semantics": (
            future_wna16_useful_consumer_payload.get("useful_consumer_semantics")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_source_count": (
            _int_metric(future_wna16_useful_consumer_payload, "source_count")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_row_count": (
            _int_metric(future_wna16_useful_consumer_payload, "row_count")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_row_ok_count": (
            _int_metric(future_wna16_useful_consumer_payload, "row_ok_count")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_ready": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "useful_consumer_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_native_stub_checked": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "useful_consumer_native_stub_checked",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_rows_consumed": (
            _int_metric(
                future_wna16_useful_consumer_payload,
                "useful_consumer_rows_consumed",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_fields_consumed": (
            future_wna16_useful_consumer_payload.get(
                "useful_consumer_fields_consumed"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_descriptor_ptr_row_ok_count": (
            (
                future_wna16_useful_consumer_payload.get(
                    "field_read_row_ok_counts"
                )
                or {}
            ).get("descriptor_ptr")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_packed_weight_descriptor_row_ok_count": (
            (
                future_wna16_useful_consumer_payload.get(
                    "field_read_row_ok_counts"
                )
                or {}
            ).get("packed_weight_descriptor")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_scale_metadata_handle_row_ok_count": (
            (
                future_wna16_useful_consumer_payload.get(
                    "field_read_row_ok_counts"
                )
                or {}
            ).get("scale_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_aux_metadata_handle_row_ok_count": (
            (
                future_wna16_useful_consumer_payload.get(
                    "field_read_row_ok_counts"
                )
                or {}
            ).get("aux_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_descriptor_ptr_field_hash": (
            (future_wna16_useful_consumer_payload.get("field_read_hashes") or {}).get(
                "descriptor_ptr"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_packed_weight_descriptor_field_hash": (
            (future_wna16_useful_consumer_payload.get("field_read_hashes") or {}).get(
                "packed_weight_descriptor"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_scale_metadata_handle_field_hash": (
            (future_wna16_useful_consumer_payload.get("field_read_hashes") or {}).get(
                "scale_metadata_handle"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_aux_metadata_handle_field_hash": (
            (future_wna16_useful_consumer_payload.get("field_read_hashes") or {}).get(
                "aux_metadata_handle"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_descriptor_ptr_useful_hash": (
            (
                future_wna16_useful_consumer_payload.get(
                    "useful_consumer_field_read_hashes"
                )
                or {}
            ).get("descriptor_ptr")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_packed_weight_descriptor_useful_hash": (
            (
                future_wna16_useful_consumer_payload.get(
                    "useful_consumer_field_read_hashes"
                )
                or {}
            ).get("packed_weight_descriptor")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_scale_metadata_handle_useful_hash": (
            (
                future_wna16_useful_consumer_payload.get(
                    "useful_consumer_field_read_hashes"
                )
                or {}
            ).get("scale_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_aux_metadata_handle_useful_hash": (
            (
                future_wna16_useful_consumer_payload.get(
                    "useful_consumer_field_read_hashes"
                )
                or {}
            ).get("aux_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_hash": (
            future_wna16_useful_consumer_payload.get("useful_consumer_hash")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_execution_json": (
            _path_label(
                _path_for_label(
                    future_wna16_useful_consumer_payload.get("execution_json"),
                    root,
                ),
                root=root,
            )
            if isinstance(
                future_wna16_useful_consumer_payload.get("execution_json"),
                str,
            )
            and future_wna16_useful_consumer_payload.get("execution_json")
            else future_wna16_useful_consumer_payload.get("execution_json")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_execution_sha256": (
            future_wna16_useful_consumer_payload.get("execution_sha256")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_native_timing_json": (
            _path_label(
                _path_for_label(
                    future_wna16_useful_consumer_payload.get("native_timing_json"),
                    root,
                ),
                root=root,
            )
            if isinstance(
                future_wna16_useful_consumer_payload.get("native_timing_json"),
                str,
            )
            and future_wna16_useful_consumer_payload.get("native_timing_json")
            else future_wna16_useful_consumer_payload.get("native_timing_json")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_native_timing_sha256": (
            future_wna16_useful_consumer_payload.get("native_timing_sha256")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_native_stub_json": (
            _path_label(
                _path_for_label(
                    future_wna16_useful_consumer_payload.get("native_stub_json"),
                    root,
                ),
                root=root,
            )
            if isinstance(
                future_wna16_useful_consumer_payload.get("native_stub_json"),
                str,
            )
            and future_wna16_useful_consumer_payload.get("native_stub_json")
            else future_wna16_useful_consumer_payload.get("native_stub_json")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_native_stub_sha256": (
            future_wna16_useful_consumer_payload.get("native_stub_sha256")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_timing_native_stub_json": (
            _path_label(
                _path_for_label(
                    future_wna16_useful_consumer_timing_payload.get(
                        "native_stub_output_json"
                    ),
                    root,
                ),
                root=root,
            )
            if isinstance(
                future_wna16_useful_consumer_timing_payload.get(
                    "native_stub_output_json"
                ),
                str,
            )
            and future_wna16_useful_consumer_timing_payload.get(
                "native_stub_output_json"
            )
            else future_wna16_useful_consumer_timing_payload.get(
                "native_stub_output_json"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_timing_native_stub_sha256": (
            future_wna16_useful_consumer_timing_payload.get(
                "native_stub_output_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_payload_bytes": (
            _int_metric(future_wna16_useful_consumer_payload, "payload_bytes")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_payload_deref_allowed": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "payload_deref_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_kernel_arg_pass_allowed": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_passed_to_kernel": (
            _bool_metric(future_wna16_useful_consumer_payload, "passed_to_kernel")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_changes_kernel_launch_args": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_current_wna16_arg_compatible": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_uses_current_wna16_args": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "uses_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_passes_current_wna16_args": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "passes_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_measures_tpot": (
            _bool_metric(future_wna16_useful_consumer_payload, "measures_tpot")
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_measures_vllm_latency": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "measures_vllm_latency",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_wna16_benchmark_ready": (
            _bool_metric(
                future_wna16_useful_consumer_payload,
                "wna16_benchmark_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_wna16_side_hash": (
            future_wna16_useful_consumer_payload.get(
                "wna16_side_consumer_variant_execution_hash_accumulator"
            )
        ),
        "default_kernel_consumer_future_wna16_useful_consumer_wna16_side_handle_projection_hash": (
            future_wna16_useful_consumer_payload.get(
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_evidence_label": (
            future_wna16_payloadless_useful_execution_evidence_label
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_evidence_path": (
            future_wna16_payloadless_useful_execution_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_evidence_sha256": (
            _evidence_row_sha256(
                future_wna16_payloadless_useful_execution_evidence_row
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_evidence_passed": (
            _evidence_row_passed(
                future_wna16_payloadless_useful_execution_evidence_row
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_artifact_kind": (
            future_wna16_payloadless_useful_execution_payload.get("artifact_kind")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_name": (
            future_wna16_payloadless_useful_execution_payload.get(
                "payloadless_useful_execution_name"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_mode": (
            future_wna16_payloadless_useful_execution_payload.get(
                "payloadless_useful_execution_mode"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_source": (
            future_wna16_payloadless_useful_execution_payload.get(
                "payloadless_useful_execution_source"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_source_count": (
            _int_metric(
                future_wna16_payloadless_useful_execution_payload,
                "source_count",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_row_count": (
            _int_metric(
                future_wna16_payloadless_useful_execution_payload,
                "row_count",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_row_ok_count": (
            _int_metric(
                future_wna16_payloadless_useful_execution_payload,
                "row_ok_count",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_ready": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payloadless_useful_execution_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_gate_ready": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payloadless_useful_execution_gate_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_chain_checked": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payloadless_useful_execution_chain_checked",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_checked": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payloadless_useful_execution_native_stub_checked",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_rows_consumed": (
            _int_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payloadless_useful_execution_rows_consumed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_descriptor_ptr_row_ok_count": (
            _int_metric(
                (
                    future_wna16_payloadless_useful_execution_payload.get(
                        "field_read_row_ok_counts"
                    )
                    or {}
                ),
                "descriptor_ptr",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_packed_weight_descriptor_row_ok_count": (
            _int_metric(
                (
                    future_wna16_payloadless_useful_execution_payload.get(
                        "field_read_row_ok_counts"
                    )
                    or {}
                ),
                "packed_weight_descriptor",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_scale_metadata_handle_row_ok_count": (
            _int_metric(
                (
                    future_wna16_payloadless_useful_execution_payload.get(
                        "field_read_row_ok_counts"
                    )
                    or {}
                ),
                "scale_metadata_handle",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_aux_metadata_handle_row_ok_count": (
            _int_metric(
                (
                    future_wna16_payloadless_useful_execution_payload.get(
                        "field_read_row_ok_counts"
                    )
                    or {}
                ),
                "aux_metadata_handle",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_descriptor_ptr_field_hash": (
            (
                future_wna16_payloadless_useful_execution_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("descriptor_ptr")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_packed_weight_descriptor_field_hash": (
            (
                future_wna16_payloadless_useful_execution_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("packed_weight_descriptor")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_scale_metadata_handle_field_hash": (
            (
                future_wna16_payloadless_useful_execution_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("scale_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_aux_metadata_handle_field_hash": (
            (
                future_wna16_payloadless_useful_execution_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("aux_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_useful_consumer_json": (
            future_wna16_payloadless_useful_execution_payload.get(
                "useful_consumer_json"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_useful_consumer_sha256": (
            future_wna16_payloadless_useful_execution_payload.get(
                "useful_consumer_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_execution_json": (
            future_wna16_payloadless_useful_execution_payload.get("execution_json")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_execution_sha256": (
            future_wna16_payloadless_useful_execution_payload.get(
                "execution_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_timing_json": (
            future_wna16_payloadless_useful_execution_payload.get(
                "native_timing_json"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_timing_sha256": (
            future_wna16_payloadless_useful_execution_payload.get(
                "native_timing_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_json": (
            future_wna16_payloadless_useful_execution_payload.get(
                "native_stub_json"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_sha256": (
            future_wna16_payloadless_useful_execution_payload.get(
                "native_stub_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_chain_hash": (
            future_wna16_payloadless_useful_execution_payload.get(
                "payloadless_useful_execution_chain_hash"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_payload_bytes": (
            _int_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payload_bytes",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_payload_deref_allowed": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "payload_deref_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_kernel_arg_pass_allowed": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_passed_to_kernel": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "passed_to_kernel",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_changes_kernel_launch_args": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_current_wna16_arg_compatible": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_uses_current_wna16_args": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "uses_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_passes_current_wna16_args": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "passes_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_measures_tpot": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "measures_tpot",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_measures_vllm_latency": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "measures_vllm_latency",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_wna16_benchmark_ready": (
            _bool_metric(
                future_wna16_payloadless_useful_execution_payload,
                "wna16_benchmark_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_evidence_label": (
            future_wna16_payloadless_useful_repeat_benchmark_evidence_label
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_evidence_path": (
            future_wna16_payloadless_useful_repeat_benchmark_evidence_row.get("path")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_evidence_sha256": (
            _evidence_row_sha256(
                future_wna16_payloadless_useful_repeat_benchmark_evidence_row
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_evidence_passed": (
            _evidence_row_passed(
                future_wna16_payloadless_useful_repeat_benchmark_evidence_row
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_artifact_kind": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "artifact_kind"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_name": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "benchmark_name"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_mode": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "benchmark_mode"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_source": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "benchmark_source"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_scope": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "benchmark_scope"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_ready": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "payloadless_useful_repeat_benchmark_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_source_count": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "source_count",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_row_count": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "row_count",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_row_ok_count": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "row_ok_count",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_rows_consumed": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "rows_consumed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_repeat_count_requested": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "repeat_count_requested",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_repeat_count_measured": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "repeat_count_measured",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_measurement_source": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "measurement_source"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_seed_only": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "seed_only",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_stub_host_wall_ms_min": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "native_stub_host_wall_ms_stats"
                )
                or {}
            ).get("min_ms")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_stub_host_wall_ms_median": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "native_stub_host_wall_ms_stats"
                )
                or {}
            ).get("median_ms")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_stub_host_wall_ms_mean": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "native_stub_host_wall_ms_stats"
                )
                or {}
            ).get("mean_ms")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_stub_host_wall_ms_max": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "native_stub_host_wall_ms_stats"
                )
                or {}
            ).get("max_ms")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_descriptor_ptr_field_hash": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("descriptor_ptr")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_packed_weight_descriptor_field_hash": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("packed_weight_descriptor")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_scale_metadata_handle_field_hash": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("scale_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_aux_metadata_handle_field_hash": (
            (
                future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                    "field_read_hashes"
                )
                or {}
            ).get("aux_metadata_handle")
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_harness_json": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "harness_json"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_harness_sha256": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "harness_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_timing_seed_json": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "native_timing_seed_json"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_timing_seed_sha256": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "native_timing_seed_sha256"
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_payload_bytes": (
            _int_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "payload_bytes",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_payload_deref_allowed": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "payload_deref_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_kernel_arg_pass_allowed": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_passed_to_kernel": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "passed_to_kernel",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_changes_kernel_launch_args": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_current_wna16_arg_compatible": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_uses_current_wna16_args": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "uses_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_passes_current_wna16_args": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "passes_current_wna16_args",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_measures_tpot": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "measures_tpot",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_measures_vllm_latency": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "measures_vllm_latency",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_wna16_benchmark_ready": (
            _bool_metric(
                future_wna16_payloadless_useful_repeat_benchmark_payload,
                "wna16_benchmark_ready",
            )
        ),
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_next_runtime_stage": (
            future_wna16_payloadless_useful_repeat_benchmark_payload.get(
                "next_runtime_stage"
            )
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_label": (
            wna16_side_variant_evidence_label
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_path": (
            wna16_side_variant_evidence_row.get("path")
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_sha256": (
            _evidence_row_sha256(wna16_side_variant_evidence_row)
        ),
        "default_kernel_consumer_wna16_side_variant_evidence_passed": (
            _evidence_row_passed(wna16_side_variant_evidence_row)
        ),
        "default_kernel_consumer_wna16_side_variant_required": (
            _bool_metric(
                wna16_side_variant_payload,
                "require_wna16_side_consumer_variant_execution",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_checked": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_checked",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_name": (
            wna16_side_variant_payload.get(
                "wna16_side_consumer_variant_execution_name"
            )
        ),
        "default_kernel_consumer_wna16_side_variant_mode": (
            wna16_side_variant_payload.get(
                "wna16_side_consumer_variant_execution_mode"
            )
        ),
        "default_kernel_consumer_wna16_side_variant_source": (
            wna16_side_variant_payload.get(
                "wna16_side_consumer_variant_execution_source"
            )
        ),
        "default_kernel_consumer_wna16_side_variant_source_count": (
            _int_metric(wna16_side_variant_payload, "selected_source_count")
        ),
        "default_kernel_consumer_wna16_side_variant_source_context_count": (
            wna16_side_variant_source_context_count
        ),
        "default_kernel_consumer_wna16_side_variant_source_context_matches_source_count": (
            wna16_side_variant_source_context_count is not None
            and wna16_side_variant_source_context_count
            == _int_metric(wna16_side_variant_payload, "selected_source_count")
        ),
        "default_kernel_consumer_wna16_side_variant_source_identity_count": (
            len(wna16_side_variant_source_identities)
        ),
        "default_kernel_consumer_wna16_side_variant_source_identity_coverage": (
            wna16_side_variant_source_context_count is not None
            and len(wna16_side_variant_source_identities)
            == wna16_side_variant_source_context_count
        ),
        "default_kernel_consumer_wna16_side_variant_source_identity_digest": (
            _source_identity_digest(wna16_side_variant_source_identities)
        ),
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset": (
            wna16_side_variant_source_identity_subset
        ),
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count": (
            wna16_side_variant_source_identity_missing_count
        ),
        "default_kernel_consumer_wna16_side_variant_row_count": (
            _int_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_row_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_row_ok_count": (
            _int_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_error_count": (
            _int_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_error_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_all_handle_fields_read": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_packet_chain_depth": (
            _int_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_payload_bytes": (
            _int_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_payload_bytes",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_passed_to_kernel": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_changes_kernel_launch_args": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_current_wna16_arg_compatible": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_explicit_typed_abi_slot": (
            _bool_metric(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_explicit_typed_abi_slot",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_reuses_current_wna16_arg_slot": (
            _bool_metric(
                wna16_side_variant_payload,
                "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_aux_metadata_handle_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_handle_projection_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_descriptor_ptr_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_scale_metadata_handle_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "wna16_side_consumer_variant_execution_aux_metadata_handle_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_required": (
            _bool_metric(
                wna16_side_variant_payload,
                "require_future_wna16_kernel_side_consumer_execution",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_checked": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_checked",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_name": (
            wna16_side_variant_payload.get(
                "future_wna16_kernel_side_consumer_execution_name"
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_mode": (
            wna16_side_variant_payload.get(
                "future_wna16_kernel_side_consumer_execution_mode"
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_source": (
            wna16_side_variant_payload.get(
                "future_wna16_kernel_side_consumer_execution_source"
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_row_count": (
            _int_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_row_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_row_ok_count": (
            _int_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_error_count": (
            _int_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_error_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_all_handle_fields_read": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_all_handle_fields_read",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_packet_chain_depth": (
            _int_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_payload_bytes": (
            _int_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_payload_bytes",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_payload_deref_allowed": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_payload_deref_allowed",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_kernel_arg_pass_allowed": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_passed_to_kernel": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_changes_kernel_launch_args": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_current_wna16_arg_compatible": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_explicit_typed_abi_slot": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_explicit_typed_abi_slot",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_reuses_current_wna16_arg_slot": (
            _bool_metric(
                wna16_side_variant_payload,
                "future_wna16_kernel_side_consumer_execution_reuses_current_wna16_arg_slot",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_descriptor_ptr_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_descriptor_ptr_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_packed_weight_descriptor_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_packed_weight_descriptor_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_scale_metadata_handle_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_scale_metadata_handle_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_aux_metadata_handle_read_row_ok_count": (
            _int_metric(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_aux_metadata_handle_read_row_ok_count",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_handle_projection_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_descriptor_ptr_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_descriptor_ptr_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_packed_weight_descriptor_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_packed_weight_descriptor_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_scale_metadata_handle_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_scale_metadata_handle_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_wna16_kernel_side_execution_aux_metadata_handle_read_hash_accumulator": (
            _hex_metric_text(
                wna16_side_variant_stub_summary,
                "future_wna16_kernel_side_consumer_execution_aux_metadata_handle_read_hash_accumulator",
            )
        ),
        "default_kernel_consumer_dispatch_runner_row_hashchain_all_valid": (
            row_hashchain_all_valid
        ),
        "default_kernel_consumer_dispatch_runner_dispatch_hash_accumulator": (
            dispatch_row_hash
        ),
        "default_kernel_consumer_dispatch_runner_dispatch_ptr_hash_accumulator": (
            dispatch_ptr_row_hash
        ),
        "default_kernel_consumer_dispatch_runner_arg_slot_hash_accumulator": (
            arg_slot_row_hash
        ),
        "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal": (
            projection_hashchain_equal
        ),
        "default_kernel_consumer_dispatch_runner_dispatch_handle_projection_hash_accumulator": (
            dispatch_projection_hash
        ),
        "default_kernel_consumer_dispatch_runner_dispatch_ptr_handle_projection_hash_accumulator": (
            dispatch_ptr_projection_hash
        ),
        "default_kernel_consumer_dispatch_runner_arg_slot_handle_projection_hash_accumulator": (
            arg_slot_projection_hash
        ),
        "default_kernel_consumer_dispatch_runner_consumer_view_handle_projection_hash_accumulator": (
            consumer_view_projection_hash
        ),
        "default_kernel_consumer_dispatch_runner_consumer_program_view_handle_projection_hash_accumulator": (
            consumer_program_view_projection_hash
        ),
        "default_kernel_consumer_dispatch_runner_handle_projection_field_names": (
            arg_slot_projection_field_names
        ),
        "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_schema_covered": (
            arg_slot_projection_all_handle_fields_schema_covered
        ),
        "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked": (
            arg_slot_projection_all_handle_fields_checked
        ),
        "default_kernel_consumer_native_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_consumer_field_mask",
            )
        ),
        "default_kernel_consumer_native_required_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_consumer_required_field_mask",
            )
        ),
        "default_kernel_consumer_launch_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_launch_consumer_field_mask",
            )
        ),
        "default_kernel_consumer_launch_required_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_launch_consumer_required_field_mask",
            )
        ),
        "default_kernel_consumer_dispatch_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_field_mask",
            )
        ),
        "default_kernel_consumer_dispatch_required_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_required_field_mask",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_field_mask",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_required_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_required_field_mask",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_checked": (
            _bool_metric(
                future_kernel_args_summary,
                "future_kernel_consumer_args_checked",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_row_count": (
            future_kernel_args_row_count
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_row_ok_count": (
            future_kernel_args_row_ok_count
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_payload_bytes": (
            future_kernel_args_payload_bytes
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_passed_to_kernel": (
            _bool_metric(
                future_kernel_args_summary,
                "future_kernel_consumer_args_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_changes_kernel_launch_args": (
            _bool_metric(
                future_kernel_args_summary,
                "future_kernel_consumer_args_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_current_wna16_arg_compatible": (
            _bool_metric(
                future_kernel_args_summary,
                "future_kernel_consumer_args_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_checked": (
            _bool_metric(
                future_kernel_args_compatible_path_summary,
                "future_kernel_args_compatible_consumer_path_checked",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_required": (
            _observed_default_contract_value(
                "future_kernel_args_compatible_consumer_path_required"
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_row_count": (
            future_kernel_args_compatible_row_count
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_row_ok_count": (
            future_kernel_args_compatible_row_ok_count
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_payload_bytes": (
            future_kernel_args_compatible_payload_bytes
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_passed_to_kernel": (
            _bool_metric(
                future_kernel_args_compatible_path_summary,
                "future_kernel_args_compatible_consumer_path_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_changes_kernel_launch_args": (
            _bool_metric(
                future_kernel_args_compatible_path_summary,
                "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_current_wna16_arg_compatible": (
            _bool_metric(
                future_kernel_args_compatible_path_summary,
                "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_mirror_field_coverage": (
            future_kernel_args_mirror_field_coverage
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_optional_mirror_field_coverage": (
            sorted(future_kernel_args_optional_mirror_field_coverage)
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_optional_mirror_evidence_labels": (
            sorted(future_kernel_args_optional_mirror_evidence_labels)
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_field_coverage": (
            future_kernel_args_total_mirror_field_coverage
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_total_full_field_mirror_coverage": (
            set(future_kernel_args_total_mirror_field_coverage)
            == set(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_coverage_required": (
            future_kernel_args_total_mirror_coverage_required
        ),
        "default_kernel_consumer_dispatch_runner_final_preflight_passed": (
            _bool_metric(dispatch_runner_final_status_summary, "passed") is True
            and _int_metric(
                dispatch_runner_final_status_summary,
                "strict_default_gate_evidence_deferred_count",
            )
            == 0
            and _int_metric(
                dispatch_runner_final_status_summary,
                "runtime_gate_evidence_deferred_count",
            )
            == 0
        ),
        "default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count": (
            _int_metric(
                dispatch_runner_final_status_summary,
                "strict_default_gate_evidence_deferred_count",
            )
        ),
        "default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count": (
            _int_metric(
                dispatch_runner_final_status_summary,
                "runtime_gate_evidence_deferred_count",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_label": (
            dispatch_ptr_standalone_evidence_label
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_path": (
            dispatch_ptr_standalone_evidence_row.get("path")
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_sha256": (
            _evidence_row_sha256(dispatch_ptr_standalone_evidence_row)
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_present": (
            dispatch_ptr_standalone_evidence_present
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_passed": (
            dispatch_ptr_standalone_evidence_passed
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_evidence_failure": (
            dispatch_ptr_standalone_evidence_row.get("failure")
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_input_source": (
            dispatch_ptr_standalone_payload.get("input_source")
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_checked": (
            _bool_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_checked",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_row_count": (
            _int_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_row_count",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_row_ok_count": (
            _int_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_payload_bytes": (
            _int_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_payload_bytes",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_passed_to_kernel": (
            _bool_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_changes_kernel_launch_args": (
            _bool_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_standalone_current_wna16_arg_compatible": (
            _bool_metric(
                dispatch_ptr_standalone_payload,
                "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_evidence_label": (
            arg_slot_standalone_evidence_label
        ),
        "default_kernel_consumer_arg_slot_standalone_evidence_path": (
            arg_slot_standalone_evidence_row.get("path")
        ),
        "default_kernel_consumer_arg_slot_standalone_evidence_sha256": (
            _evidence_row_sha256(arg_slot_standalone_evidence_row)
        ),
        "default_kernel_consumer_arg_slot_standalone_evidence_present": (
            arg_slot_standalone_evidence_present
        ),
        "default_kernel_consumer_arg_slot_standalone_evidence_passed": (
            arg_slot_standalone_evidence_passed
        ),
        "default_kernel_consumer_arg_slot_standalone_evidence_failure": (
            arg_slot_standalone_evidence_row.get("failure")
        ),
        "default_kernel_consumer_arg_slot_standalone_input_source": (
            arg_slot_standalone_payload.get("input_source")
        ),
        "default_kernel_consumer_arg_slot_standalone_status_source": (
            "standalone_native_stub_artifact"
        ),
        "default_kernel_consumer_arg_slot_standalone_checked": (
            _bool_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_checked",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_row_count": (
            _int_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_row_count",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_row_ok_count": (
            _int_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_row_ok_count",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_payload_bytes": (
            _int_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_payload_bytes",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_passed_to_kernel": (
            _bool_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_changes_kernel_launch_args": (
            _bool_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_current_wna16_arg_compatible": (
            _bool_metric(
                arg_slot_standalone_payload,
                "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_arg_slot_standalone_mirror_field_coverage": (
            arg_slot_standalone_mirror_field_coverage
        ),
        "default_kernel_consumer_arg_slot_standalone_full_field_mirror_coverage": (
            set(arg_slot_standalone_mirror_field_coverage)
            == set(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_dispatch_checked": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_checked",
            )
        ),
        "default_kernel_consumer_dispatch_row_count": dispatch_row_count,
        "default_kernel_consumer_dispatch_row_ok_count": dispatch_row_ok_count,
        "default_kernel_consumer_dispatch_active_rows": dispatch_active_rows,
        "default_kernel_consumer_dispatch_row_offset": dispatch_row_offset,
        "default_kernel_consumer_dispatch_row_limit": dispatch_row_limit,
        "default_kernel_consumer_dispatch_payload_bytes": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_payload_bytes",
            )
        ),
        "default_kernel_consumer_dispatch_passed_to_kernel": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_dispatch_changes_kernel_launch_args": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_dispatch_current_wna16_arg_compatible": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_dispatch_full_table_checked": (
            dispatch_full_table_checked
        ),
        "default_kernel_consumer_dispatch_ptr_abi_name": (
            schema_summary.get("future_kernel_native_consumer_dispatch_ptr_abi_name")
        ),
        "default_kernel_consumer_dispatch_ptr_abi_struct": (
            schema_summary.get("future_kernel_native_consumer_dispatch_ptr_abi_struct")
        ),
        "default_kernel_consumer_dispatch_ptr_abi_mode": (
            schema_summary.get("future_kernel_native_consumer_dispatch_ptr_abi_mode")
        ),
        "default_kernel_consumer_dispatch_ptr_abi_source": (
            schema_summary.get("future_kernel_native_consumer_dispatch_ptr_abi_source")
        ),
        "default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": (
            schema_summary.get(
                "future_kernel_native_consumer_dispatch_ptr_abi_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_dispatch_ptr_required": (
            _observed_default_contract_value(
                "future_kernel_native_dispatch_ptr_consumer_required"
            )
        ),
        "default_kernel_consumer_dispatch_ptr_checked": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_checked",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_row_count": dispatch_ptr_row_count,
        "default_kernel_consumer_dispatch_ptr_row_ok_count": (
            dispatch_ptr_row_ok_count
        ),
        "default_kernel_consumer_dispatch_ptr_error_count": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_error_count",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_payload_bytes": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_payload_bytes",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_passed_to_kernel": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_changes_kernel_launch_args": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_current_wna16_arg_compatible": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_dispatch_ptr_mirror_row_count": (
            dispatch_ptr_mirror_row_count
        ),
        "default_kernel_consumer_dispatch_ptr_mirror_row_ok_count": (
            dispatch_ptr_mirror_row_ok_count
        ),
        "default_kernel_consumer_arg_slot_abi_name": (
            schema_summary.get("future_kernel_native_consumer_arg_slot_abi_name")
        ),
        "default_kernel_consumer_arg_slot_abi_struct": (
            schema_summary.get("future_kernel_native_consumer_arg_slot_abi_struct")
        ),
        "default_kernel_consumer_arg_slot_abi_mode": (
            schema_summary.get("future_kernel_native_consumer_arg_slot_abi_mode")
        ),
        "default_kernel_consumer_arg_slot_abi_source": (
            schema_summary.get("future_kernel_native_consumer_arg_slot_abi_source")
        ),
        "default_kernel_consumer_arg_slot_abi_current_wna16_arg_compatible": (
            schema_summary.get(
                "future_kernel_native_consumer_arg_slot_abi_current_wna16_arg_compatible"
            )
        ),
        "default_kernel_consumer_arg_slot_status_source": (
            "online_dispatch_runner_summary"
        ),
        "default_kernel_consumer_arg_slot_status_evidence_label": (
            dispatch_runner_evidence_label
        ),
        "default_kernel_consumer_arg_slot_status_evidence_path": (
            dispatch_runner_evidence_row.get("path")
        ),
        "default_kernel_consumer_arg_slot_checked": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_checked",
            )
        ),
        "default_kernel_consumer_arg_slot_row_count": arg_slot_row_count,
        "default_kernel_consumer_arg_slot_row_ok_count": arg_slot_row_ok_count,
        "default_kernel_consumer_arg_slot_field_read_field_names": (
            list(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_arg_slot_field_read_row_count": (
            arg_slot_field_read_row_count
        ),
        "default_kernel_consumer_arg_slot_all_handle_fields_read": (
            arg_slot_all_handle_fields_read
        ),
        "default_kernel_consumer_arg_slot_field_read_row_ok_counts": (
            arg_slot_field_read_row_ok_counts
        ),
        "default_kernel_consumer_arg_slot_field_read_error_counts": (
            arg_slot_field_read_error_counts
        ),
        "default_kernel_consumer_arg_slot_field_read_hashes": (
            arg_slot_field_read_hashes
        ),
        "default_kernel_consumer_consumer_view_field_read_field_names": (
            list(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_consumer_view_field_read_row_count": (
            consumer_view_field_read_row_count
        ),
        "default_kernel_consumer_consumer_view_all_handle_fields_read": (
            consumer_view_all_handle_fields_read
        ),
        "default_kernel_consumer_consumer_view_field_read_row_ok_counts": (
            consumer_view_field_read_row_ok_counts
        ),
        "default_kernel_consumer_consumer_view_field_read_error_counts": (
            consumer_view_field_read_error_counts
        ),
        "default_kernel_consumer_consumer_view_field_read_hashes": (
            consumer_view_field_read_hashes
        ),
        "default_kernel_consumer_consumer_view_status_source": (
            consumer_view_status_source
        ),
        "default_kernel_consumer_consumer_view_row_window_source": (
            consumer_view_row_window_source
        ),
        "default_kernel_consumer_consumer_view_source": consumer_view_source,
        "default_kernel_consumer_consumer_view_source_expected": (
            expected_consumer_view_source
        ),
        "default_kernel_consumer_consumer_view_source_matches_schema": (
            consumer_view_source_matches_schema
        ),
        "default_kernel_consumer_consumer_view_source_packet_chain_depth": (
            consumer_view_source_packet_chain_depth
        ),
        "default_kernel_consumer_dispatch_row_window": dispatch_row_window,
        "default_kernel_consumer_consumer_view_row_window": (
            consumer_view_row_window
        ),
        "default_kernel_consumer_consumer_view_row_window_matches_dispatch": (
            consumer_view_row_window_matches_dispatch
        ),
        "default_kernel_consumer_consumer_view_row_offset": (
            consumer_view_row_window.get("row_offset")
        ),
        "default_kernel_consumer_consumer_view_row_limit": (
            consumer_view_row_window.get("row_limit")
        ),
        "default_kernel_consumer_consumer_view_rows_per_program": (
            consumer_view_row_window.get("rows_per_program")
        ),
        "default_kernel_consumer_consumer_view_payload_bytes": (
            consumer_view_payload_bytes
        ),
        "default_kernel_consumer_consumer_view_passed_to_kernel": (
            consumer_view_passed_to_kernel
        ),
        "default_kernel_consumer_consumer_view_changes_kernel_launch_args": (
            consumer_view_changes_kernel_launch_args
        ),
        "default_kernel_consumer_consumer_view_current_wna16_arg_compatible": (
            consumer_view_current_wna16_arg_compatible
        ),
        "default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation": (
            consumer_view_requires_wna16_arg_reinterpretation
        ),
        "default_kernel_consumer_consumer_view_reinterpretation_flags_valid": (
            consumer_view_reinterpretation_flags_valid
        ),
        "default_kernel_consumer_consumer_view_safety_matches_required": (
            consumer_view_safety_matches_required
        ),
        "default_kernel_consumer_consumer_program_view_checked": (
            consumer_program_view_checked
        ),
        "default_kernel_consumer_consumer_program_view_status_source": (
            consumer_program_view_status_source
        ),
        "default_kernel_consumer_consumer_program_view_source": (
            consumer_program_view_source
        ),
        "default_kernel_consumer_consumer_program_view_row_count": (
            consumer_program_view_row_count
        ),
        "default_kernel_consumer_consumer_program_view_row_ok_count": (
            consumer_program_view_row_ok_count
        ),
        "default_kernel_consumer_consumer_program_view_error_count": (
            consumer_program_view_error_count
        ),
        "default_kernel_consumer_consumer_program_view_row_count_matches_dispatch": (
            consumer_program_view_row_count_matches_dispatch
        ),
        "default_kernel_consumer_consumer_program_view_program_count": (
            consumer_program_view_program_count
        ),
        "default_kernel_consumer_consumer_program_view_full_program_count": (
            consumer_program_view_full_program_count
        ),
        "default_kernel_consumer_consumer_program_view_last_program_active_rows": (
            consumer_program_view_last_program_active_rows
        ),
        "default_kernel_consumer_consumer_program_view_inactive_lane_count": (
            consumer_program_view_inactive_lane_count
        ),
        "default_kernel_consumer_consumer_program_view_first_program_row_offset": (
            consumer_program_view_first_program_row_offset
        ),
        "default_kernel_consumer_consumer_program_view_last_program_row_offset": (
            consumer_program_view_last_program_row_offset
        ),
        "default_kernel_consumer_consumer_program_view_geometry_matches_dispatch": (
            consumer_program_view_geometry_matches_dispatch
        ),
        "default_kernel_consumer_consumer_program_view_program_iteration_hash": (
            consumer_program_view_program_iteration_hash
        ),
        "default_kernel_consumer_consumer_program_view_program_iteration_hash_matches_dispatch": (
            consumer_program_view_hash_matches_dispatch
        ),
        "default_kernel_consumer_consumer_program_view_projection_matches_view": (
            consumer_program_view_projection_matches_view
        ),
        "default_kernel_consumer_consumer_program_view_row_assignment_formula": (
            consumer_program_view_formula
        ),
        "default_kernel_consumer_consumer_program_view_payload_bytes": (
            consumer_program_view_payload_bytes
        ),
        "default_kernel_consumer_consumer_program_view_passed_to_kernel": (
            consumer_program_view_passed_to_kernel
        ),
        "default_kernel_consumer_consumer_program_view_changes_kernel_launch_args": (
            consumer_program_view_changes_kernel_launch_args
        ),
        "default_kernel_consumer_consumer_program_view_current_wna16_arg_compatible": (
            consumer_program_view_current_wna16_arg_compatible
        ),
        "default_kernel_consumer_consumer_program_view_requires_wna16_arg_reinterpretation": (
            consumer_program_view_requires_wna16_arg_reinterpretation
        ),
        "default_kernel_consumer_consumer_program_view_safety_matches_required": (
            consumer_program_view_safety_matches_required
        ),
        "default_kernel_consumer_program_view_ptr_required": (
            effective_require_program_view_ptr_abi
        ),
        "default_kernel_consumer_program_view_ptr_checked": (
            consumer_program_view_ptr_checked
        ),
        "default_kernel_consumer_program_view_ptr_source": (
            consumer_program_view_ptr_source
        ),
        "default_kernel_consumer_program_view_ptr_source_expected": (
            expected_consumer_program_view_ptr_source
        ),
        "default_kernel_consumer_program_view_ptr_source_matches_schema": (
            consumer_program_view_ptr_source_matches_schema
        ),
        "default_kernel_consumer_program_view_ptr_row_count": (
            consumer_program_view_ptr_row_count
        ),
        "default_kernel_consumer_program_view_ptr_row_ok_count": (
            consumer_program_view_ptr_row_ok_count
        ),
        "default_kernel_consumer_program_view_ptr_error_count": (
            consumer_program_view_ptr_error_count
        ),
        "default_kernel_consumer_program_view_ptr_row_count_matches_dispatch": (
            consumer_program_view_ptr_row_count_matches_dispatch
        ),
        "default_kernel_consumer_program_view_ptr_field_mask": (
            consumer_program_view_ptr_field_mask
        ),
        "default_kernel_consumer_program_view_ptr_required_field_mask": (
            consumer_program_view_ptr_required_field_mask
        ),
        "default_kernel_consumer_program_view_ptr_required_fields_visible": (
            consumer_program_view_ptr_required_fields_visible
        ),
        "default_kernel_consumer_program_view_ptr_payload_bytes": (
            consumer_program_view_ptr_payload_bytes
        ),
        "default_kernel_consumer_program_view_ptr_passed_to_kernel": (
            consumer_program_view_ptr_passed_to_kernel
        ),
        "default_kernel_consumer_program_view_ptr_changes_kernel_launch_args": (
            consumer_program_view_ptr_changes_kernel_launch_args
        ),
        "default_kernel_consumer_program_view_ptr_current_wna16_arg_compatible": (
            consumer_program_view_ptr_current_wna16_arg_compatible
        ),
        "default_kernel_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": (
            consumer_program_view_ptr_requires_wna16_arg_reinterpretation
        ),
        "default_kernel_consumer_program_view_ptr_safety_matches_required": (
            consumer_program_view_ptr_safety_matches_required
        ),
        "default_kernel_consumer_arg_slot_error_count": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_error_count",
            )
        ),
        "default_kernel_consumer_arg_slot_payload_bytes": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_payload_bytes",
            )
        ),
        "default_kernel_consumer_arg_slot_passed_to_kernel": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_arg_slot_changes_kernel_launch_args": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_arg_slot_current_wna16_arg_compatible": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation",
            )
        ),
        "default_kernel_consumer_arg_slot_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_field_mask",
            )
        ),
        "default_kernel_consumer_arg_slot_required_field_mask": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_required_field_mask",
            )
        ),
        "default_kernel_consumer_arg_slot_mirror_checked": (
            _bool_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_single_field_mirror_checked",
            )
        ),
        "default_kernel_consumer_arg_slot_mirror_field_name": (
            dispatch_runner_summary.get(
                "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
            )
        ),
        "default_kernel_consumer_arg_slot_online_mirror_field_coverage": (
            arg_slot_online_mirror_field_coverage
        ),
        "default_kernel_consumer_arg_slot_online_full_field_mirror_coverage": (
            set(arg_slot_online_mirror_field_coverage) == set(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_arg_slot_online_diagnostic_mirror_field_coverage": (
            sorted(arg_slot_online_diagnostic_mirror_field_coverage)
        ),
        "default_kernel_consumer_arg_slot_online_diagnostic_summary_keys": (
            sorted(arg_slot_online_diagnostic_summary_keys)
        ),
        "default_kernel_consumer_arg_slot_online_total_mirror_field_coverage": (
            arg_slot_online_total_mirror_field_coverage
        ),
        "default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage": (
            set(arg_slot_online_total_mirror_field_coverage)
            == set(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_arg_slot_required_mirror_field_coverage": (
            sorted(arg_slot_required_mirror_field_coverage)
        ),
        "default_kernel_consumer_arg_slot_required_mirror_evidence_labels": (
            sorted(arg_slot_required_mirror_evidence_labels)
        ),
        "default_kernel_consumer_arg_slot_optional_mirror_field_coverage": (
            sorted(arg_slot_optional_mirror_field_coverage)
        ),
        "default_kernel_consumer_arg_slot_optional_mirror_evidence_labels": (
            sorted(arg_slot_optional_mirror_evidence_labels)
        ),
        "default_kernel_consumer_arg_slot_online_merged_required_mirror_field_coverage": (
            sorted(arg_slot_online_merged_required_mirror_field_coverage)
        ),
        "default_kernel_consumer_arg_slot_online_merged_required_mirror_evidence_labels": (
            sorted(arg_slot_online_merged_required_mirror_evidence_labels)
        ),
        "default_kernel_consumer_arg_slot_online_merged_optional_mirror_field_coverage": (
            sorted(arg_slot_online_merged_optional_mirror_field_coverage)
        ),
        "default_kernel_consumer_arg_slot_online_merged_optional_mirror_evidence_labels": (
            sorted(arg_slot_online_merged_optional_mirror_evidence_labels)
        ),
        "default_kernel_consumer_arg_slot_total_mirror_field_coverage": (
            arg_slot_total_mirror_field_coverage
        ),
        "default_kernel_consumer_arg_slot_total_full_field_mirror_coverage": (
            set(arg_slot_total_mirror_field_coverage) == set(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_arg_slot_online_total_mirror_coverage_required": (
            arg_slot_online_total_mirror_coverage_required
        ),
        "default_kernel_consumer_arg_slot_all_mirror_fields": (
            list(ARG_SLOT_MIRROR_FIELDS)
        ),
        "default_kernel_consumer_arg_slot_mirror_row_count": (
            arg_slot_mirror_row_count
        ),
        "default_kernel_consumer_arg_slot_mirror_row_ok_count": (
            arg_slot_mirror_row_ok_count
        ),
        "default_kernel_consumer_arg_slot_mirror_error_count": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count",
            )
        ),
        "default_kernel_consumer_arg_slot_slot_struct_size": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_slot_struct_size",
            )
        ),
        "default_kernel_consumer_arg_slot_slot_struct_align": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_slot_struct_align",
            )
        ),
        "default_kernel_consumer_arg_slot_dispatch_ptr_struct_size": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_dispatch_ptr_struct_size",
            )
        ),
        "default_kernel_consumer_arg_slot_result_struct_size": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_result_struct_size",
            )
        ),
        "default_kernel_consumer_arg_slot_offset_dispatch_ptr": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr",
            )
        ),
        "default_kernel_consumer_arg_slot_offset_flags": (
            _int_metric(
                dispatch_runner_summary,
                "future_kernel_native_arg_slot_consumer_offset_flags",
            )
        ),
        "default_required_evidence_passed": bool(
            default_gate_required_evidence_check.get("passed", False)
        ),
        "default_optional_evidence_passed": bool(
            default_gate_optional_evidence_check.get("passed", False)
        ),
        "runtime_gate_evidence_scan_passed": bool(
            runtime_scan.get("passed", False)
        ),
        "runtime_gate_evidence_deferred_count": int(
            runtime_scan.get("deferred_count", 0)
        ),
        "strict_default_gate_evidence_passed": bool(
            (strict_gate_checks.get("default_readonly_gate") or {}).get(
                "passed", False
            )
        ),
        "strict_default_gate_evidence_deferred_count": int(
            (strict_gate_checks.get("default_readonly_gate") or {}).get(
                "deferred_count", 0
            )
        ),
        "trace_config_count": len(trace_results),
        "trace_config_passed_count": sum(
            1 for result in trace_results if result.get("passed", False)
        ),
        "risky_trace_config_count": len(risky_trace_config_checks),
        "risky_trace_config_failed_count": sum(
            1
            for result in risky_trace_config_checks
            if not result.get("passed", False)
        ),
        "required_evidence": evidence_summary,
        "optional_evidence": _summarize_required_evidence_check(
            default_gate_optional_evidence_check
        ),
        "deferred_online_prelaunch_runner_evidence": bool(
            defer_online_prelaunch_runner_evidence
        ),
        "deferred_online_prelaunch_artifact_evidence": bool(
            defer_online_prelaunch_artifact_evidence
        ),
        "bootstrap_preflight_allowed": bool(allow_bootstrap_preflight),
        "online_runner_self_finalization_allowed": bool(
            allow_online_runner_self_finalization
        ),
        "native_typed_consumer_bridge_required": (
            _observed_default_contract_value("native_typed_consumer_bridge_required")
        ),
        "native_stub_online_invocation_canary_required": (
            _observed_default_contract_value(
                "native_stub_online_invocation_canary_required"
            )
        ),
        "single_field_handle_handoff_canary_required": (
            _observed_default_contract_value(
                "single_field_handle_handoff_canary_required"
            )
        ),
        "kernel_side_typed_row_consumer_path_required": (
            _observed_default_contract_value(
                "kernel_side_typed_row_consumer_path_required"
            )
        ),
        "payload_bytes_required": _observed_default_contract_value(
            "native_typed_consumer_bridge_payload_bytes_required"
        ),
        "passed_to_kernel_required": _observed_default_contract_value(
            "native_typed_consumer_bridge_passed_to_kernel_required"
        ),
        "changes_kernel_launch_args_required": (
            _observed_default_contract_value(
                "native_typed_consumer_bridge_changes_kernel_launch_args_required"
            )
        ),
    }

    def _flatten_request_all_field_handoff(
        *,
        out_prefix: str,
        source: dict[str, object],
        consumer_prefix: str,
    ) -> dict[str, object]:
        values: dict[str, object] = {
            f"{out_prefix}_all_field_handoff_checked": source.get(
                f"{consumer_prefix}_all_field_handoff_checked"
            ),
            f"{out_prefix}_all_field_handoff_field_names": source.get(
                f"{consumer_prefix}_all_field_handoff_field_names"
            ),
            f"{out_prefix}_all_field_handoff_source": source.get(
                f"{consumer_prefix}_all_field_handoff_source"
            ),
            f"{out_prefix}_all_field_handoff_row_count": _int_metric(
                source,
                f"{consumer_prefix}_all_field_handoff_row_count",
            ),
            f"{out_prefix}_all_field_handoff_row_ok_count": _int_metric(
                source,
                f"{consumer_prefix}_all_field_handoff_row_ok_count",
            ),
            f"{out_prefix}_all_field_handoff_error_count": _int_metric(
                source,
                f"{consumer_prefix}_all_field_handoff_error_count",
            ),
            f"{out_prefix}_all_field_handoff_hash_accumulator": source.get(
                f"{consumer_prefix}_all_field_handoff_hash_accumulator"
            ),
            f"{out_prefix}_all_field_handoff_payload_bytes": _int_metric(
                source,
                f"{consumer_prefix}_all_field_handoff_payload_bytes",
            ),
            f"{out_prefix}_all_field_handoff_passed_to_kernel": source.get(
                f"{consumer_prefix}_all_field_handoff_passed_to_kernel"
            ),
            f"{out_prefix}_all_field_handoff_changes_kernel_launch_args": source.get(
                f"{consumer_prefix}_all_field_handoff_changes_kernel_launch_args"
            ),
            f"{out_prefix}_all_field_handoff_current_wna16_arg_compatible": source.get(
                f"{consumer_prefix}_all_field_handoff_current_wna16_arg_compatible"
            ),
            f"{out_prefix}_all_field_handoff_requires_wna16_arg_reinterpretation": (
                source.get(
                    f"{consumer_prefix}_all_field_handoff_requires_wna16_arg_reinterpretation"
                )
            ),
        }
        for field_name in (
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ):
            values[
                f"{out_prefix}_all_field_handoff_{field_name}_row_ok_count"
            ] = _int_metric(
                source,
                f"{consumer_prefix}_all_field_handoff_{field_name}_row_ok_count",
            )
        return values

    lab_gate_status_summary.update(
        _flatten_request_all_field_handoff(
            out_prefix="default_kernel_consumer_request_ptr",
            source=request_ptr_summary_source,
            consumer_prefix="future_kernel_native_consumer_request_ptr",
        )
    )
    lab_gate_status_summary.update(
        _flatten_request_all_field_handoff(
            out_prefix="default_kernel_consumer_request_launch",
            source=request_launch_summary_source,
            consumer_prefix="future_kernel_native_consumer_request_launch",
        )
    )
    lab_gate_status_summary.update(
        _flatten_request_all_field_handoff(
            out_prefix="default_kernel_consumer_request_launch_ptr",
            source=request_launch_ptr_summary_source,
            consumer_prefix="future_kernel_native_consumer_request_launch_ptr",
        )
    )
    typed_noop_ready = (
        bool(lab_gate_status_summary.get("default_kernel_consumer_schema_passed"))
        and bool(
            lab_gate_status_summary.get(
                "default_kernel_consumer_online_merged_multiprogram_evidence_passed"
            )
        )
        and bool(
            lab_gate_status_summary.get(
                "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked"
            )
        )
        and bool(
            lab_gate_status_summary.get(
                "default_kernel_consumer_kernel_entry_args_checked"
            )
        )
        and bool(
            lab_gate_status_summary.get(
                "default_kernel_consumer_kernel_endpoint_ptr_checked"
            )
        )
        and bool(
            lab_gate_status_summary.get(
                "default_kernel_consumer_request_launch_ptr_all_handle_fields_read"
            )
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_entry_args_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_entry_args_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_entry_args_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_endpoint_ptr_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_endpoint_ptr_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_endpoint_ptr_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_request_launch_ptr_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_request_launch_ptr_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_request_launch_ptr_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_online_merged_multiprogram_no_payload"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args"
        )
        is False
    )
    wna16_side_variant_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_wna16_side_variant_source_count",
    )
    wna16_side_variant_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_wna16_side_variant_row_count",
    )
    wna16_side_variant_row_ok_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_wna16_side_variant_row_ok_count",
    )
    online_merged_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_online_merged_multiprogram_row_count",
    )
    wna16_side_variant_fields_read = (
        wna16_side_variant_row_count is not None
        and all(
            _int_metric(
                lab_gate_status_summary,
                f"default_kernel_consumer_wna16_side_variant_{field_name}_read_row_ok_count",
            )
            == wna16_side_variant_row_count
            for field_name in ARG_SLOT_MIRROR_FIELDS
        )
    )
    wna16_side_variant_hashes_valid = all(
        _hex64_metric(lab_gate_status_summary, key) is not None
        for key in (
            "default_kernel_consumer_wna16_side_variant_hash_accumulator",
            "default_kernel_consumer_wna16_side_variant_handle_projection_hash_accumulator",
            "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_hash_accumulator",
            "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_hash_accumulator",
            "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_hash_accumulator",
            "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_hash_accumulator",
        )
    )
    wna16_kernel_side_execution_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_wna16_kernel_side_execution_row_count",
    )
    wna16_kernel_side_execution_row_ok_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_wna16_kernel_side_execution_row_ok_count",
    )
    wna16_kernel_side_execution_fields_read = (
        wna16_kernel_side_execution_row_count is not None
        and all(
            _int_metric(
                lab_gate_status_summary,
                f"default_kernel_consumer_wna16_kernel_side_execution_{field_name}_read_row_ok_count",
            )
            == wna16_kernel_side_execution_row_count
            for field_name in ARG_SLOT_MIRROR_FIELDS
        )
    )
    wna16_kernel_side_execution_hashes_valid = all(
        _hex64_metric(lab_gate_status_summary, key) is not None
        for key in (
            "default_kernel_consumer_wna16_kernel_side_execution_hash_accumulator",
            "default_kernel_consumer_wna16_kernel_side_execution_handle_projection_hash_accumulator",
            "default_kernel_consumer_wna16_kernel_side_execution_descriptor_ptr_read_hash_accumulator",
            "default_kernel_consumer_wna16_kernel_side_execution_packed_weight_descriptor_read_hash_accumulator",
            "default_kernel_consumer_wna16_kernel_side_execution_scale_metadata_handle_read_hash_accumulator",
            "default_kernel_consumer_wna16_kernel_side_execution_aux_metadata_handle_read_hash_accumulator",
        )
    )
    fourth_field_handoff_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_fourth_field_handoff_source_count",
    )
    fourth_field_handoff_previous_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_fourth_field_handoff_previous_source_count",
    )
    fourth_field_handoff_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_fourth_field_handoff_row_count",
    )
    fourth_field_handoff_ready = (
        lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_previous_gate_ready"
        )
        is True
        and fourth_field_handoff_source_count is not None
        and fourth_field_handoff_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_fourth_field_handoff_canary_min_source_count"
            ]
        )
        and fourth_field_handoff_previous_source_count is not None
        and fourth_field_handoff_previous_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_fourth_field_handoff_canary_min_source_count"
            ]
        )
        and fourth_field_handoff_row_count is not None
        and fourth_field_handoff_row_count > 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_row_ok_count"
        )
        == fourth_field_handoff_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_row_ok_count"
        )
        == fourth_field_handoff_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_count"
        )
        == fourth_field_handoff_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_ok_count"
        )
        == fourth_field_handoff_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_fourth_field"
        )
        == REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_fourth_field_handoff_canary_field"
        ]
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_native_requested"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_native_executed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_native_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_expected_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is False
        and all(
            _hex64_metric(lab_gate_status_summary, key) is not None
            for key in (
                "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_hash",
                "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_hash",
                "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field_read_hash",
                "default_kernel_consumer_future_wna16_fourth_field_handoff_third_field_native_hash",
            )
        )
    )
    wna16_side_variant_base_ready = (
        typed_noop_ready
        and fourth_field_handoff_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_required"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_checked"
        )
        is True
        and wna16_side_variant_source_count is not None
        and wna16_side_variant_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "wna16_side_consumer_variant_execution_min_source_count"
            ]
        )
        and wna16_side_variant_row_count is not None
        and wna16_side_variant_row_count > 0
        and wna16_side_variant_row_ok_count == wna16_side_variant_row_count
        and (
            online_merged_row_count is None
            or wna16_side_variant_row_count >= online_merged_row_count
        )
        and wna16_side_variant_fields_read
        and wna16_side_variant_hashes_valid
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_all_handle_fields_read"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_error_count"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_reuses_current_wna16_arg_slot"
        )
        is False
    )
    wna16_side_variant_ready = (
        wna16_side_variant_base_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_online_merged_multiprogram_source_context_matches_source_count"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_online_merged_multiprogram_source_identity_coverage"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_source_context_matches_source_count"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_source_identity_coverage"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
        )
        == 0
    )
    wna16_kernel_side_execution_ready = (
        wna16_side_variant_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_required"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_checked"
        )
        is True
        and wna16_kernel_side_execution_row_count is not None
        and wna16_kernel_side_execution_row_count > 0
        and wna16_kernel_side_execution_row_ok_count
        == wna16_kernel_side_execution_row_count
        and (
            online_merged_row_count is None
            or wna16_kernel_side_execution_row_count >= online_merged_row_count
        )
        and wna16_kernel_side_execution_fields_read
        and wna16_kernel_side_execution_hashes_valid
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_all_handle_fields_read"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_error_count"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_explicit_typed_abi_slot"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_wna16_kernel_side_execution_reuses_current_wna16_arg_slot"
        )
        is False
    )
    all_four_consumer_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_source_count",
    )
    all_four_consumer_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_row_count",
    )
    all_four_consumer_row_ok_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_row_ok_count",
    )
    all_four_consumer_fields_read = (
        all_four_consumer_row_count is not None
        and all(
            _int_metric(
                all_four_field_consumer_payload,
                f"{prefix}_{field_name}_read_row_ok_count",
            )
            == all_four_consumer_row_count
            for prefix in (
                "future_wna16_kernel_side_consumer_execution",
                "wna16_side_consumer_variant_execution",
            )
            for field_name in ARG_SLOT_MIRROR_FIELDS
        )
    )
    all_four_consumer_hashes_valid = all(
        _hex64_metric(all_four_field_consumer_payload, key) is not None
        for key in (
            "future_wna16_kernel_side_consumer_execution_hash_accumulator",
            "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator",
            "future_wna16_kernel_side_consumer_execution_descriptor_ptr_read_hash_accumulator",
            "future_wna16_kernel_side_consumer_execution_packed_weight_descriptor_read_hash_accumulator",
            "future_wna16_kernel_side_consumer_execution_scale_metadata_handle_read_hash_accumulator",
            "future_wna16_kernel_side_consumer_execution_aux_metadata_handle_read_hash_accumulator",
            "wna16_side_consumer_variant_execution_hash_accumulator",
            "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator",
            "wna16_side_consumer_variant_execution_descriptor_ptr_read_hash_accumulator",
            "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_hash_accumulator",
            "wna16_side_consumer_variant_execution_scale_metadata_handle_read_hash_accumulator",
            "wna16_side_consumer_variant_execution_aux_metadata_handle_read_hash_accumulator",
        )
    )
    all_four_field_consumer_ready = (
        lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_stage_type"
        )
        == "lab_gate"
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_bench_semantics"
        )
        is False
        and all_four_consumer_source_count is not None
        and all_four_consumer_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_all_four_field_consumer_min_source_count"
            ]
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_count"
        )
        == all_four_consumer_source_count
        and _is_sha256_hex(
            lab_gate_status_summary.get(
                "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_manifest_sha256"
            )
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_post_native_input_manifest_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_selected_input_manifest_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_path_label"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_path"
        )
        and all_four_consumer_row_count is not None
        and all_four_consumer_row_count > 0
        and all_four_consumer_row_ok_count == all_four_consumer_row_count
        and all_four_consumer_source_count
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_source_count"
        )
        and all_four_consumer_row_count
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_fourth_field_handoff_row_count"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_native_executed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_native_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_future_kernel_side_all_fields_read"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_wna16_side_all_fields_read"
        )
        is True
        and all_four_consumer_fields_read
        and all_four_consumer_hashes_valid
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_wna16_benchmark_ready"
        )
        is False
    )
    future_wna16_kernel_side_path_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_source_count",
    )
    future_wna16_kernel_side_path_input_json_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_input_json_count",
    )
    future_wna16_kernel_side_path_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_count",
    )
    future_wna16_kernel_side_path_row_ok_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_ok_count",
    )
    future_wna16_kernel_side_path_hashes_valid = all(
        _hex64_metric(future_wna16_kernel_side_path_payload, key) is not None
        for key in (
            "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator",
            "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator",
        )
    )
    future_wna16_kernel_side_typed_consumer_path_ready = (
        all_four_field_consumer_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_stage_type"
        )
        == "lab_gate"
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_bench_semantics"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_gate_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_path_label"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_evidence_path"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_all_four_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_all_four_consumer_evidence_sha256"
        )
        and future_wna16_kernel_side_path_source_count is not None
        and future_wna16_kernel_side_path_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_kernel_side_typed_consumer_path_min_source_count"
            ]
        )
        and future_wna16_kernel_side_path_input_json_count
        == future_wna16_kernel_side_path_source_count
        and future_wna16_kernel_side_path_row_count is not None
        and future_wna16_kernel_side_path_row_count > 0
        and future_wna16_kernel_side_path_row_ok_count
        == future_wna16_kernel_side_path_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_native_executed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_native_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_independent_path"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_explicit_typed_abi_slot"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_future_kernel_side_checked"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_future_kernel_side_all_fields_read"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_side_checked"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_side_all_fields_read"
        )
        is True
        and future_wna16_kernel_side_path_hashes_valid
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_uses_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_wna16_benchmark_ready"
        )
        is False
    )
    future_wna16_payloadless_execution_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_payloadless_execution_source_count",
    )
    future_wna16_payloadless_execution_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_payloadless_execution_row_count",
    )
    future_wna16_payloadless_execution_ready = (
        future_wna16_kernel_side_typed_consumer_path_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_gate_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_lab_preflight_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_native_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_native_requested"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_native_executed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_native_passed"
        )
        is True
        and future_wna16_payloadless_execution_source_count is not None
        and future_wna16_payloadless_execution_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_payloadless_execution_min_source_count"
            ]
        )
        and future_wna16_payloadless_execution_source_count
        == future_wna16_kernel_side_path_source_count
        and future_wna16_payloadless_execution_row_count is not None
        and future_wna16_payloadless_execution_row_count > 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_row_ok_count"
        )
        == future_wna16_payloadless_execution_row_count
        and future_wna16_payloadless_execution_row_count
        == future_wna16_kernel_side_path_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_all_four_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_all_four_fields_read"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_kernel_side_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_kernel_side_hashes_valid"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_benchmark_repeat_count"
        )
        == 3
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_uses_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_wna16_benchmark_ready"
        )
        is False
    )
    future_wna16_variant_execution_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_variant_execution_source_count",
    )
    future_wna16_variant_execution_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_variant_execution_row_count",
    )
    future_wna16_variant_execution_ready = (
        wna16_side_variant_ready
        and future_wna16_payloadless_execution_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_payloadless_gate_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_native_requested"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_native_executed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_native_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_native_artifact_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_not_current_wna16_kernel"
        )
        is True
        and future_wna16_variant_execution_source_count is not None
        and future_wna16_variant_execution_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_kernel_variant_execution_min_source_count"
            ]
        )
        and future_wna16_variant_execution_source_count
        == future_wna16_payloadless_execution_source_count
        and future_wna16_variant_execution_row_count is not None
        and future_wna16_variant_execution_row_count > 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_row_ok_count"
        )
        == future_wna16_variant_execution_row_count
        and future_wna16_variant_execution_row_count
        == future_wna16_payloadless_execution_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_payloadless_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_execution_evidence_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_uses_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_passes_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_wna16_benchmark_ready"
        )
        is False
    )
    future_wna16_useful_consumer_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_useful_consumer_source_count",
    )
    future_wna16_useful_consumer_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_useful_consumer_row_count",
    )
    future_wna16_useful_consumer_ready = (
        future_wna16_variant_execution_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_native_stub_checked"
        )
        is True
        and future_wna16_useful_consumer_source_count is not None
        and future_wna16_useful_consumer_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_kernel_variant_useful_consumer_min_source_count"
            ]
        )
        and future_wna16_useful_consumer_source_count
        == future_wna16_variant_execution_source_count
        and future_wna16_useful_consumer_row_count is not None
        and future_wna16_useful_consumer_row_count > 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_row_ok_count"
        )
        == future_wna16_useful_consumer_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_rows_consumed"
        )
        == future_wna16_useful_consumer_row_count
        and future_wna16_useful_consumer_row_count
        == future_wna16_variant_execution_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_execution_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_evidence_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_uses_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_passes_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_wna16_benchmark_ready"
        )
        is False
    )
    future_wna16_payloadless_useful_execution_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_source_count",
    )
    future_wna16_payloadless_useful_execution_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_row_count",
    )
    future_wna16_payloadless_useful_execution_ready = (
        future_wna16_useful_consumer_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_gate_ready"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_chain_checked"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_checked"
        )
        is True
        and future_wna16_payloadless_useful_execution_source_count is not None
        and future_wna16_payloadless_useful_execution_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_min_source_count"
            ]
        )
        and future_wna16_payloadless_useful_execution_source_count
        == future_wna16_useful_consumer_source_count
        and future_wna16_payloadless_useful_execution_row_count is not None
        and future_wna16_payloadless_useful_execution_row_count > 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_row_ok_count"
        )
        == future_wna16_payloadless_useful_execution_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_rows_consumed"
        )
        == future_wna16_payloadless_useful_execution_row_count
        and future_wna16_payloadless_useful_execution_row_count
        == future_wna16_useful_consumer_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_useful_consumer_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_evidence_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_execution_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_evidence_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_timing_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_native_timing_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_native_stub_sha256"
        )
        == lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_native_stub_sha256"
        )
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_uses_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_passes_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_wna16_benchmark_ready"
        )
        is False
    )
    future_wna16_payloadless_useful_repeat_benchmark_source_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_source_count",
    )
    future_wna16_payloadless_useful_repeat_benchmark_row_count = _int_metric(
        lab_gate_status_summary,
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_row_count",
    )
    future_wna16_payloadless_useful_repeat_benchmark_repeat_count_requested = (
        _int_metric(
            lab_gate_status_summary,
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_repeat_count_requested",
        )
    )
    future_wna16_payloadless_useful_repeat_benchmark_repeat_count_measured = (
        _int_metric(
            lab_gate_status_summary,
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_repeat_count_measured",
        )
    )
    future_wna16_payloadless_useful_repeat_benchmark_ready = (
        future_wna16_payloadless_useful_execution_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_evidence_passed"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_ready"
        )
        is True
        and future_wna16_payloadless_useful_repeat_benchmark_source_count is not None
        and future_wna16_payloadless_useful_repeat_benchmark_source_count
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_source_count"
            ]
        )
        and future_wna16_payloadless_useful_repeat_benchmark_source_count
        == future_wna16_payloadless_useful_execution_source_count
        and future_wna16_payloadless_useful_repeat_benchmark_row_count is not None
        and future_wna16_payloadless_useful_repeat_benchmark_row_count > 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_row_ok_count"
        )
        == future_wna16_payloadless_useful_repeat_benchmark_row_count
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_rows_consumed"
        )
        == future_wna16_payloadless_useful_repeat_benchmark_row_count
        and future_wna16_payloadless_useful_repeat_benchmark_row_count
        == future_wna16_payloadless_useful_execution_row_count
        and future_wna16_payloadless_useful_repeat_benchmark_repeat_count_requested
        is not None
        and future_wna16_payloadless_useful_repeat_benchmark_repeat_count_requested
        >= int(
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_repeat_count"
            ]
        )
        and future_wna16_payloadless_useful_repeat_benchmark_repeat_count_measured
        == future_wna16_payloadless_useful_repeat_benchmark_repeat_count_requested
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_measurement_source"
        )
        == "repeated_independent_native_typed_slot_timing_stub"
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_seed_only"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_harness_sha256"
        )
        is not None
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_timing_seed_sha256"
        )
        is not None
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_payload_bytes"
        )
        == 0
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_payload_deref_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_kernel_arg_pass_allowed"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_passed_to_kernel"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_changes_kernel_launch_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_current_wna16_arg_compatible"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_uses_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_passes_current_wna16_args"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_requires_wna16_arg_reinterpretation"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_measures_tpot"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_measures_vllm_latency"
        )
        is False
        and lab_gate_status_summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_wna16_benchmark_ready"
        )
        is False
    )
    wna16_benchmark_prerequisites_ready = (
        all_four_field_consumer_ready
        and future_wna16_kernel_side_typed_consumer_path_ready
        and future_wna16_payloadless_execution_ready
        and lab_gate_status_summary.get(
            "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible"
        )
        is True
        and lab_gate_status_summary.get(
            "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible"
        )
        is True
    )
    # Current lab preflight is still a no-launch-mutation gate. A future gate may
    # relax the current-WNA16-arg compatibility contract; until then, do not
    # advertise benchmark readiness from this checker-compatible preflight.
    wna16_benchmark_ready = False
    independent_typed_slot_payloadless_chain_ready = (
        wna16_side_variant_ready
        and future_wna16_kernel_side_typed_consumer_path_ready
        and future_wna16_payloadless_execution_ready
    )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_all_four_field_consumer_required"
        ]
        and not all_four_field_consumer_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_all_four_field_consumer_not_ready"
        )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_kernel_side_typed_consumer_path_required"
        ]
        and not future_wna16_kernel_side_typed_consumer_path_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_not_ready"
        )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_payloadless_execution_required"
        ]
        and not future_wna16_payloadless_execution_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_kernel_variant_execution_required"
        ]
        and wna16_side_variant_ready
        and not future_wna16_variant_execution_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_variant_execution_not_ready"
        )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_kernel_variant_useful_consumer_required"
        ]
        and future_wna16_variant_execution_ready
        and not future_wna16_useful_consumer_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_useful_consumer_not_ready"
        )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_required"
        ]
        and future_wna16_useful_consumer_ready
        and not future_wna16_payloadless_useful_execution_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_not_ready"
        )
    if (
        REQUIRED_DEFAULT_GATE_CONTRACT[
            "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_required"
        ]
        and future_wna16_payloadless_useful_execution_ready
        and not future_wna16_payloadless_useful_repeat_benchmark_ready
    ):
        failures.append(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_not_ready"
        )
    if future_wna16_payloadless_useful_repeat_benchmark_ready:
        next_runtime_stage = (
            "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
        )
    elif future_wna16_payloadless_useful_execution_ready:
        next_runtime_stage = "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
    elif future_wna16_useful_consumer_ready:
        next_runtime_stage = (
            "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
        )
    elif future_wna16_variant_execution_ready:
        next_runtime_stage = (
            "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
        )
    elif independent_typed_slot_payloadless_chain_ready:
        next_runtime_stage = "implement_future_wna16_typed_slot_kernel_variant_execution"
    elif future_wna16_kernel_side_typed_consumer_path_ready and wna16_side_variant_ready:
        next_runtime_stage = "implement_wna16_typed_slot_benchmark_harness"
    elif wna16_kernel_side_execution_ready:
        next_runtime_stage = "promote_all_four_field_typed_slot_consumer_gate"
    elif wna16_side_variant_ready:
        next_runtime_stage = "implement_real_wna16_typed_slot_kernel_variant"
    elif wna16_side_variant_base_ready:
        next_runtime_stage = "refresh_wna16_side_variant_source_provenance"
    elif typed_noop_ready:
        next_runtime_stage = "implement_wna16_typed_slot_kernel_variant"
    else:
        next_runtime_stage = "fix_typed_noop_consumer_gate"
    lab_gate_status_summary["default_kernel_consumer_typed_noop_ready"] = (
        typed_noop_ready
    )
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_fourth_field_handoff_ready"
    ] = fourth_field_handoff_ready
    lab_gate_status_summary["default_kernel_consumer_wna16_benchmark_ready"] = (
        wna16_benchmark_ready
    )
    lab_gate_status_summary[
        "default_kernel_consumer_wna16_benchmark_prerequisites_ready"
    ] = wna16_benchmark_prerequisites_ready
    lab_gate_status_summary[
        "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
    ] = independent_typed_slot_payloadless_chain_ready
    lab_gate_status_summary[
        "default_kernel_consumer_wna16_kernel_side_execution_ready"
    ] = wna16_kernel_side_execution_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_all_four_field_consumer_ready"
    ] = all_four_field_consumer_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_all_four_field_consumer_fields_read"
    ] = all_four_consumer_fields_read
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_all_four_field_consumer_hashes_valid"
    ] = all_four_consumer_hashes_valid
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
    ] = future_wna16_kernel_side_typed_consumer_path_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid"
    ] = future_wna16_kernel_side_path_hashes_valid
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_payloadless_execution_gate_ready"
    ] = future_wna16_payloadless_execution_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_variant_execution_gate_ready"
    ] = future_wna16_variant_execution_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_useful_consumer_gate_ready"
    ] = future_wna16_useful_consumer_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_gate_ready"
    ] = future_wna16_payloadless_useful_execution_ready
    lab_gate_status_summary[
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_gate_ready"
    ] = future_wna16_payloadless_useful_repeat_benchmark_ready
    lab_gate_status_summary[
        "default_kernel_consumer_wna16_side_variant_ready"
    ] = wna16_side_variant_ready
    lab_gate_status_summary[
        "default_kernel_consumer_wna16_side_variant_base_ready"
    ] = wna16_side_variant_base_ready
    lab_gate_status_summary["default_kernel_consumer_next_runtime_stage"] = (
        next_runtime_stage
    )

    return {
        "passed": not failures,
        "failures": failures,
        "lab_gate_status_summary": lab_gate_status_summary,
        "gate_pair_failures": gate_pair_failures,
        "default_readonly_gate_contract_check": default_gate_contract_check,
        "default_kernel_consumer_schema_check": (
            default_kernel_consumer_schema_check
        ),
        "prefetch_lab_default_gate_check": prefetch_lab_default_gate_check,
        "default_readonly_gate_required_evidence_check": (
            default_gate_required_evidence_check
        ),
        "default_readonly_gate_optional_evidence_check": (
            default_gate_optional_evidence_check
        ),
        "risky_canary_metadata_checks": risky_canary_metadata_checks,
        "runtime_gate_evidence_scan": runtime_scan,
        "strict_gate_evidence_checks": strict_gate_checks,
        "trace_config_checks": trace_results,
        "risky_trace_config_checks": risky_trace_config_checks,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--runtime-pattern", default="configs/runtime/*.yaml")
    parser.add_argument("--trace-pattern", default="configs/trace/*.yaml")
    parser.add_argument("--trace-config", action="append", dest="trace_configs")
    parser.add_argument("--default-readonly-gate", default=DEFAULT_READONLY_GATE)
    parser.add_argument("--canary-gate", default=DEFAULT_CANARY_GATE)
    parser.add_argument(
        "--prefetch-lab-default-gate",
        default=DEFAULT_PREFETCH_LAB_DEFAULT_GATE,
        help=(
            "Default prefetch/premap lab gate. This preflight requires full "
            "payload fetch to remain blocked by ready-time evidence while "
            "premap descriptor/address prep may be lab-enabled."
        ),
    )
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help="Allow missing evidence paths while still checking schema and config wiring.",
    )
    parser.add_argument(
        "--defer-online-prelaunch-runner-evidence",
        action="store_true",
        help=(
            "Skip only the self-referential online-prelaunch runner evidence "
            "row. Intended for the runner's pre-write preflight; the normal "
            "lab preflight must still validate the runner artifact afterwards."
        ),
    )
    parser.add_argument(
        "--defer-online-prelaunch-artifact-evidence",
        action="store_true",
        help=(
            "Skip only the self-referential online-prelaunch artifact-check "
            "evidence rows. Intended for canary runner generation before the "
            "artifact check has been rewritten; do not use for normal lab "
            "preflight."
        ),
    )
    parser.add_argument(
        "--allow-bootstrap-preflight",
        action="store_true",
        help=(
            "Allow the runner to defer both self-referential runner and artifact "
            "evidence during stage-1 bootstrap. Final lab gates must not use this."
        ),
    )
    parser.add_argument(
        "--allow-online-runner-self-finalization",
        action="store_true",
        help=(
            "Allow an online-prelaunch runner artifact that already has bootstrap "
            "artifact evidence to generate its final no-defer preflight summary. "
            "The runner must rerun the strict preflight without this flag after "
            "writing the final artifact-check summary."
        ),
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help=(
            "Emit only the machine-readable lab_gate_status_summary while "
            "keeping the full preflight result for the exit code."
        ),
    )
    parser.add_argument(
        "--require-program-view-ptr-abi",
        action="store_true",
        help=(
            "Require the optional future-native program-view pointer ABI "
            "canary in the online merged runner evidence. This does not pass "
            "payloads or current WNA16 kernel args."
        ),
    )
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_premap_lab_preflight(
        root=args.root,
        runtime_pattern=args.runtime_pattern,
        trace_pattern=args.trace_pattern,
        trace_configs=args.trace_configs,
        default_readonly_gate=args.default_readonly_gate,
        canary_gate=args.canary_gate,
        prefetch_lab_default_gate=args.prefetch_lab_default_gate,
        allow_missing_evidence=args.allow_missing_evidence,
        defer_online_prelaunch_runner_evidence=(
            args.defer_online_prelaunch_runner_evidence
        ),
        defer_online_prelaunch_artifact_evidence=(
            args.defer_online_prelaunch_artifact_evidence
        ),
        allow_bootstrap_preflight=args.allow_bootstrap_preflight,
        allow_online_runner_self_finalization=(
            args.allow_online_runner_self_finalization
        ),
        require_program_view_ptr_abi=args.require_program_view_ptr_abi,
    )
    output_payload = (
        result["lab_gate_status_summary"] if args.summary_only else result
    )
    payload = json.dumps(output_payload, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
