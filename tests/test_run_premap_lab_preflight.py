from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import yaml

from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
)
from scripts.run_premap_lab_preflight import (
    _build_parser,
    main,
    run_premap_lab_preflight,
)
from scripts import (
    check_premap_payload_cache_vllm_replay_visible_count_ptr_native_producer
    as count_ptr_native_producer_checker,
)
from scripts.run_premap_lab_preflight import _program_iteration_hash
from scripts.run_premap_lab_preflight import (
    _source_context_identities_from_merged_output,
    _source_identity_subset,
    _validate_required_evidence_payload,
    _validate_payload_cache_packet_export_manifest_evidence,
    _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence,
    _validate_payload_cache_producer_state_native_canary_evidence,
    _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence,
    _validate_payload_cache_producer_state_packet_stream_native_canary_evidence,
    _validate_payload_cache_producer_state_inprocess_native_canary_evidence,
    _validate_payload_cache_producer_state_inprocess_native_online_contract_evidence,
    _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence,
    _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence,
    _validate_payload_cache_producer_state_stream_native_canary_evidence,
    _validate_payload_cache_producer_state_stream_online_contract_evidence,
    _validate_payload_cache_online_inside_graph_producer_boundary_contract_evidence,
    _validate_payload_cache_online_native_producer_boundary_gap_evidence,
    _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence,
    _validate_payload_cache_demand_hit_shadow_publication_gate_evidence,
    _validate_prelaunch_pointer_source_observer_check_evidence,
    _validate_readonly_live_trusted_refs_check_evidence,
    _validate_payload_cache_stream_producer_production_ab_bridge_evidence,
    _validate_payload_cache_stream_producer_production_ab_bridge_check_evidence,
)
from scripts.run_payload_cache_consumer_visible_hit_blocked_gate import (
    build_report as _payload_cache_consumer_visible_hit_blocked_gate_payload,
)
from scripts.check_premap_prelaunch_pointer_source_observer import (
    HANDOFF_BOOL_PREFIX as PRELAUNCH_POINTER_SOURCE_OBSERVER_HANDOFF_BOOL_PREFIX,
    LIVE_MUTATION_COUNTER_PREFIX as PRELAUNCH_POINTER_SOURCE_OBSERVER_LIVE_MUTATION_COUNTER_PREFIX,
    REQUIRED_BOOL_KEYS as PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_BOOL_KEYS,
    REQUIRED_INT_KEYS as PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_INT_KEYS,
    ZERO_INT_KEYS as PRELAUNCH_POINTER_SOURCE_OBSERVER_ZERO_INT_KEYS,
)
from scripts.check_premap_readonly_live_trusted_refs import (
    ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS as READONLY_LIVE_TRUSTED_REFS_ALLOWED_NONZERO_COUNTERS,
    EXPECTED_STRING_VALUES as READONLY_LIVE_TRUSTED_REFS_EXPECTED_STRING_VALUES,
    EXPECTED_TRUE_BOOL_KEYS as READONLY_LIVE_TRUSTED_REFS_EXPECTED_TRUE_BOOL_KEYS,
    REQUIRED_FALSE_BOOL_KEYS as READONLY_LIVE_TRUSTED_REFS_REQUIRED_FALSE_BOOL_KEYS,
    REQUIRED_INT_KEYS as READONLY_LIVE_TRUSTED_REFS_REQUIRED_INT_KEYS,
)
from scripts.check_premap_kernel_consumer_schema import (
    FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED,
    FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_premap_lab_preflight_parser_defaults_to_gpu1_prefetch_gate() -> None:
    args = _build_parser().parse_args([])

    assert args.prefetch_lab_default_gate == (
        "configs/runtime/prefetch_lab_default_gate_gpu1.yaml"
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_default_lab_gate_uses_strict_nodefer_online_native_evidence() -> None:
    gate_path = (
        REPO_ROOT
        / "configs/runtime/"
        "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml"
    )
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    evidence = gate["evidence_paths"]
    runner_labels = {
        "native_typed_consumer_online_prelaunch_canary_runner_json",
        "future_kernel_native_consumer_online_runner_16_128export_json",
        "future_kernel_native_launch_consumer_online_runner_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_runner_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json",
    }
    artifact_labels = {
        "future_kernel_native_consumer_online_artifact_check_16_128export_json",
        "future_kernel_native_launch_consumer_online_artifact_check_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json",
    }

    for label in runner_labels:
        path = evidence[label]
        assert path.endswith(
            "_arg_slot_32input_hard_hashchain_preflight_32tables.json"
        ), label
        assert "_32input.json" not in path, label
    for label in artifact_labels:
        path = evidence[label]
        assert path.endswith(
            "_artifact_check_arg_slot_32input_hard_hashchain_preflight_32tables.json"
        ), label
        assert "_32input.json" not in path, label
        assert "artifact_check" in path
    assert (
        evidence["future_kernel_native_consumer_online_runner_16_128export_json"]
        == evidence["future_kernel_native_dispatch_consumer_online_runner_32_128export_json"]
    )
    assert (
        evidence[
            "future_kernel_native_launch_consumer_online_runner_16_128export_json"
        ]
        == evidence[
            "future_kernel_native_dispatch_consumer_online_runner_32_128export_json"
        ]
    )
    assert (
        evidence[
            "future_kernel_native_consumer_online_artifact_check_16_128export_json"
        ]
        == evidence[
            "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json"
        ]
    )
    assert (
        evidence[
            "future_kernel_native_launch_consumer_online_artifact_check_16_128export_json"
        ]
        == evidence[
            "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json"
        ]
    )


def test_default_lab_gate_uses_entry_args_future_wna16_four_field_evidence() -> None:
    gate_path = (
        REPO_ROOT
        / "configs/runtime/"
        "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml"
    )
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    evidence = gate["evidence_paths"]

    assert evidence["future_wna16_typed_slot_fourth_field_handoff_canary_json"].endswith(
        "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_entry_args_ptr_default.json"
    )
    assert evidence["future_wna16_typed_slot_all_four_field_consumer_json"].endswith(
        "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default.json"
    )
    assert evidence["future_wna16_kernel_side_typed_consumer_path_json"].endswith(
        "future_wna16_kernel_side_typed_consumer_path_v1.json"
    )
    assert evidence["future_wna16_typed_slot_payloadless_execution_json"].endswith(
        "future_wna16_typed_slot_kernel_variant_payloadless_execution_entry_args_ptr_native_v1.json"
    )
    assert evidence["future_wna16_typed_slot_kernel_variant_execution_json"].endswith(
        "future_wna16_typed_slot_kernel_variant_execution_entry_args_ptr_native_v1.json"
    )


def test_default_lab_gate_requires_payload_cache_manager_preflight() -> None:
    gate_path = (
        REPO_ROOT
        / "configs/runtime/"
        "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml"
    )
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    contract = gate["contract"]
    evidence = gate["evidence_paths"]

    assert contract["payload_cache_manager_useful_work_ab_gate_required"] is True
    assert contract["payload_cache_manager_production_ab_preflight_required"] is True
    assert (
        contract["payload_cache_manager_production_ab_preflight_max_envelope_overhead_ratio"]
        == 0.05
    )
    assert evidence["payload_cache_manager_useful_work_ab_gate_json"].endswith(
        "payload_cache_manager_useful_work_ab_gate.json"
    )
    assert evidence["payload_cache_manager_production_ab_preflight_json"].endswith(
        "payload_cache_manager_production_ab_preflight.json"
    )


def _valid_schema_payload() -> dict:
    row_fields = []
    required_by_name = {
        "descriptor_ptr": True,
        "packed_weight_descriptor": True,
        "scale_metadata_handle": True,
        "aux_metadata_handle": False,
    }
    for name in PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS:
        row = {
            "name": name,
            "source_column": name,
            "abi_dtype": "uint64",
            "semantic": f"{name}_semantic",
            "shape": ["row_count"],
            "required": required_by_name[name],
            "payload_deref_allowed": False,
            "device_ownership": "model_weight_device",
            "lifetime": "model_load_epoch",
        }
        if name == "aux_metadata_handle":
            row["null_allowed"] = True
        row_fields.append(row)
    return {
        "schema_version": 1,
        "artifact_id": "premap_kernel_side_typed_consumer_schema_v1",
        "artifact_kind": "premap_kernel_consumer_schema",
        "status": "readonly_shadow_only",
        "schema": {
            "name": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
            "hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
            "target_runtime": "vllm_awq_wna16_fused_moe",
            "native_consumer_mode": "typed_shadow_object",
        },
        "source_contract": {
            "handle_table_columns": list(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
            "handle_table_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "semantic_schema_name": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
            "semantic_schema_hash": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
            "kernel_side_adapter_schema_name": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
            "kernel_side_adapter_schema_hash": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
        },
        "native_consumer_abi": {
            "abi_name": "premap_kernel_side_typed_consumer_abi_v1",
            "cpp_header": "microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h",
            "cpp_struct": "PremapKernelSideTypedConsumerAbiV1",
            "handle_column_count": 4,
            "payload_bytes_allowed": False,
            "kernel_arg_pass_allowed": False,
            "adapter_name": "premap_kernel_side_typed_consumer_adapter_v1",
            "adapter_header": (
                "microbench/premap_kernel_consumer/"
                "premap_typed_consumer_adapter_v1.h"
            ),
            "adapter_row_struct": "PremapKernelSideTypedConsumerRowV1",
            "adapter_payload_deref_allowed": False,
            "adapter_kernel_arg_pass_allowed": False,
            "launch_envelope_name": "premap_kernel_side_typed_consumer_launch_envelope_v1",
            "launch_envelope_struct": "PremapKernelSideTypedConsumerLaunchEnvelopeV1",
            "launch_envelope_default_enabled": False,
            "launch_envelope_payload_bytes_required": 0,
            "launch_envelope_passed_to_kernel_required": False,
            "future_kernel_consumer_args_name": "premap_future_kernel_side_consumer_args_v1",
            "future_kernel_consumer_args_struct": "PremapFutureKernelSideConsumerArgsV1",
            "future_kernel_consumer_args_mode": "readonly_future_kernel_consumer_args",
            "future_kernel_consumer_args_default_enabled": False,
            "future_kernel_consumer_args_payload_bytes_required": 0,
            "future_kernel_consumer_args_passed_to_kernel_required": False,
            "future_kernel_consumer_args_current_wna16_arg_compatible": False,
            "future_kernel_consumer_args_layout_reported": True,
            "future_kernel_consumer_args_layout_fields": list(
                FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_FIELDS
            ),
            "future_kernel_consumer_args_layout_expected": dict(
                FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED
            ),
            "future_kernel_args_compatible_consumer_path_name": (
                "premap_future_kernel_args_compatible_consumer_path_v1"
            ),
            "future_kernel_args_compatible_consumer_path_struct": (
                "PremapFutureKernelArgsCompatibleConsumerPathResultV1"
            ),
            "future_kernel_args_compatible_consumer_path_mode": (
                "readonly_future_kernel_args_to_compatible_consumer_path"
            ),
            "future_kernel_args_compatible_consumer_path_default_enabled": False,
            "future_kernel_args_compatible_consumer_path_payload_bytes_required": 0,
            "future_kernel_args_compatible_consumer_path_passed_to_kernel_required": False,
            "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_abi_name": (
                "premap_future_kernel_native_consumer_abi_v1"
            ),
            "future_kernel_native_consumer_abi_struct": (
                "PremapFutureKernelNativeConsumerParamsV1"
            ),
            "future_kernel_native_consumer_abi_result_struct": (
                "PremapFutureKernelNativeConsumerResultV1"
            ),
            "future_kernel_native_consumer_abi_mode": (
                "readonly_future_kernel_native_consumer_abi"
            ),
            "future_kernel_native_consumer_abi_source": (
                "premap_typed_handle_table_soa_fields"
            ),
            "future_kernel_native_consumer_abi_default_enabled": False,
            "future_kernel_native_consumer_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_launch_abi_name": (
                "premap_future_kernel_native_consumer_launch_abi_v1"
            ),
            "future_kernel_native_consumer_launch_abi_struct": (
                "PremapFutureKernelNativeConsumerLaunchV1"
            ),
            "future_kernel_native_consumer_launch_abi_result_struct": (
                "PremapFutureKernelNativeConsumerLaunchResultV1"
            ),
            "future_kernel_native_consumer_launch_abi_mode": (
                "readonly_future_kernel_native_consumer_launch_abi"
            ),
            "future_kernel_native_consumer_launch_abi_source": (
                "premap_future_kernel_native_consumer_abi_v1"
            ),
            "future_kernel_native_consumer_launch_abi_default_enabled": False,
            "future_kernel_native_consumer_launch_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_launch_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_launch_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_dispatch_abi_name": (
                "premap_future_kernel_native_consumer_dispatch_abi_v1"
            ),
            "future_kernel_native_consumer_dispatch_abi_struct": (
                "PremapFutureKernelNativeConsumerDispatchV1"
            ),
            "future_kernel_native_consumer_dispatch_abi_result_struct": (
                "PremapFutureKernelNativeConsumerDispatchResultV1"
            ),
            "future_kernel_native_consumer_dispatch_abi_mode": (
                "readonly_future_kernel_native_consumer_dispatch_abi"
            ),
            "future_kernel_native_consumer_dispatch_abi_source": (
                "premap_future_kernel_native_consumer_launch_abi_v1"
            ),
            "future_kernel_native_consumer_dispatch_abi_default_enabled": False,
            "future_kernel_native_consumer_dispatch_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_dispatch_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_dispatch_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_dispatch_abi_launch_geometry_required": True,
            "future_kernel_native_consumer_dispatch_abi_row_window_required": True,
            "future_kernel_native_consumer_dispatch_abi_minimal_cover_required": True,
            "future_kernel_native_consumer_dispatch_abi_rows_per_program_source": "block_x",
            "future_kernel_native_consumer_dispatch_abi_program_iteration_required": True,
            "future_kernel_native_consumer_dispatch_abi_row_assignment_formula": (
                "row_offset + program_id * rows_per_program + lane_id"
            ),
            "future_kernel_native_consumer_dispatch_abi_program_count_source": "grid_x",
            "future_kernel_native_consumer_dispatch_abi_last_program_active_rows_source": (
                "active_rows - (grid_x - 1) * rows_per_program"
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_name": (
                "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_struct": (
                "PremapFutureKernelNativeConsumerDispatchPtrV1"
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_result_struct": (
                "PremapFutureKernelNativeConsumerDispatchResultV1"
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_mode": (
                "readonly_future_kernel_native_consumer_dispatch_ptr_abi"
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_source": (
                "premap_future_kernel_native_consumer_dispatch_abi_v1"
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_default_enabled": False,
            "future_kernel_native_consumer_dispatch_ptr_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_dispatch_ptr_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_arg_slot_abi_name": (
                "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            ),
            "future_kernel_native_consumer_arg_slot_abi_struct": (
                "PremapFutureKernelNativeConsumerArgSlotV1"
            ),
            "future_kernel_native_consumer_arg_slot_abi_result_struct": (
                "PremapFutureKernelNativeConsumerDispatchResultV1"
            ),
            "future_kernel_native_consumer_arg_slot_abi_mode": (
                "readonly_future_kernel_native_consumer_arg_slot_abi"
            ),
            "future_kernel_native_consumer_arg_slot_abi_source": (
                "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_arg_slot_abi_default_enabled": False,
            "future_kernel_native_consumer_arg_slot_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_arg_slot_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_arg_slot_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_view_abi_name": (
                "premap_future_kernel_native_consumer_view_abi_v1"
            ),
            "future_kernel_native_consumer_view_abi_struct": (
                "PremapFutureKernelNativeConsumerViewV1"
            ),
            "future_kernel_native_consumer_view_abi_result_struct": (
                "PremapFutureKernelNativeConsumerViewResultV1"
            ),
            "future_kernel_native_consumer_view_abi_mode": (
                "readonly_future_kernel_native_consumer_view_abi"
            ),
            "future_kernel_native_consumer_view_abi_source": (
                "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            ),
            "future_kernel_native_consumer_view_abi_default_enabled": False,
            "future_kernel_native_consumer_view_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_view_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_view_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_view_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_view_abi_source_packet_chain_depth_required": 3,
            "future_kernel_native_consumer_program_view_abi_name": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_abi_struct": (
                "PremapFutureKernelNativeConsumerProgramViewV1"
            ),
            "future_kernel_native_consumer_program_view_abi_result_struct": (
                "PremapFutureKernelNativeConsumerProgramViewResultV1"
            ),
            "future_kernel_native_consumer_program_view_abi_mode": (
                "readonly_future_kernel_native_consumer_program_view_abi"
            ),
            "future_kernel_native_consumer_program_view_abi_source": (
                "premap_future_kernel_native_consumer_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_abi_default_enabled": False,
            "future_kernel_native_consumer_program_view_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_program_view_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_program_view_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_program_view_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_program_view_abi_row_assignment_formula": (
                "program_id * rows_per_program + lane_id + row_offset"
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_name": (
                "premap_future_kernel_native_consumer_program_view_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_struct": (
                "PremapFutureKernelNativeConsumerProgramViewPtrV1"
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_result_struct": (
                "PremapFutureKernelNativeConsumerProgramViewPtrResultV1"
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_mode": (
                "readonly_future_kernel_native_consumer_program_view_ptr_abi"
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_source": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_default_enabled": False,
            "future_kernel_native_consumer_program_view_ptr_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_program_view_ptr_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_program_view_ptr_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_program_view_ptr_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_kernel_arg_packet_abi_name": (
                "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_struct": (
                "PremapFutureKernelNativeConsumerKernelArgPacketV1"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_result_struct": (
                "PremapFutureKernelNativeConsumerKernelArgPacketResultV1"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_mode": (
                "readonly_future_kernel_native_consumer_kernel_arg_packet_abi"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_source": (
                "premap_future_kernel_native_consumer_program_view_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_default_enabled": False,
            "future_kernel_native_consumer_kernel_arg_packet_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_kernel_arg_packet_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_kernel_arg_packet_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_kernel_arg_packet_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_ptr_abi_name": (
                "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_ptr_abi_struct": (
                "PremapFutureKernelNativeConsumerRequestPtrV1"
            ),
            "future_kernel_native_consumer_request_ptr_abi_result_struct": (
                "PremapFutureKernelNativeConsumerKernelEntrySummaryV1"
            ),
            "future_kernel_native_consumer_request_ptr_abi_mode": (
                "readonly_future_kernel_native_consumer_request_ptr_abi"
            ),
            "future_kernel_native_consumer_request_ptr_abi_source": (
                "premap_future_kernel_native_consumer_kernel_arg_packet_abi_v1"
            ),
            "future_kernel_native_consumer_request_ptr_abi_default_enabled": False,
            "future_kernel_native_consumer_request_ptr_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_request_ptr_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_request_ptr_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_ptr_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_ptr_abi_field_read_path": (
                "request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_ptr_abi_packet_chain_depth_required": 4,
            "future_kernel_native_consumer_request_launch_abi_name": (
                "premap_future_kernel_native_consumer_request_launch_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_abi_struct": (
                "PremapFutureKernelNativeConsumerRequestLaunchV1"
            ),
            "future_kernel_native_consumer_request_launch_abi_result_struct": (
                "PremapFutureKernelNativeConsumerKernelEntrySummaryV1"
            ),
            "future_kernel_native_consumer_request_launch_abi_mode": (
                "readonly_future_kernel_native_consumer_request_launch_abi"
            ),
            "future_kernel_native_consumer_request_launch_abi_source": (
                "premap_future_kernel_native_consumer_request_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_abi_default_enabled": False,
            "future_kernel_native_consumer_request_launch_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_request_launch_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_request_launch_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_launch_abi_field_read_path": (
                "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_launch_abi_packet_chain_depth_required": 5,
            "future_kernel_native_consumer_request_launch_abi_launch_geometry_required": True,
            "future_kernel_native_consumer_request_launch_abi_row_window_required": True,
            "future_kernel_native_consumer_request_launch_ptr_abi_name": (
                "premap_future_kernel_native_consumer_request_launch_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_struct": (
                "PremapFutureKernelNativeConsumerRequestLaunchPtrV1"
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_result_struct": (
                "PremapFutureKernelNativeConsumerKernelEntrySummaryV1"
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_mode": (
                "readonly_future_kernel_native_consumer_request_launch_ptr_abi"
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_source": (
                "premap_future_kernel_native_consumer_request_launch_abi_v1"
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_default_enabled": False,
            "future_kernel_native_consumer_request_launch_ptr_abi_payload_bytes_required": 0,
            "future_kernel_native_consumer_request_launch_ptr_abi_passed_to_kernel_required": False,
            "future_kernel_native_consumer_request_launch_ptr_abi_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_ptr_abi_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_launch_ptr_abi_field_read_path": (
                "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_packet_chain_depth_required": 6,
            "future_kernel_native_consumer_abi_layout_reported": True,
            "future_kernel_native_consumer_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_launch_abi_layout_reported": True,
            "future_kernel_native_consumer_launch_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_launch_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_dispatch_abi_layout_reported": True,
            "future_kernel_native_consumer_dispatch_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_dispatch_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_layout_reported": True,
            "future_kernel_native_consumer_dispatch_ptr_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_dispatch_ptr_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_arg_slot_abi_layout_reported": True,
            "future_kernel_native_consumer_arg_slot_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_arg_slot_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_view_abi_layout_reported": True,
            "future_kernel_native_consumer_view_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_view_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_layout_reported": True,
            "future_kernel_native_consumer_program_view_ptr_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_program_view_ptr_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_layout_reported": True,
            "future_kernel_native_consumer_kernel_arg_packet_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_kernel_arg_packet_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_kernel_entry_summary_abi_layout_reported": True,
            "future_kernel_native_consumer_kernel_entry_summary_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_kernel_entry_summary_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_kernel_entry_args_abi_layout_reported": True,
            "future_kernel_native_consumer_kernel_entry_args_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_kernel_entry_args_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_request_ptr_abi_layout_reported": True,
            "future_kernel_native_consumer_request_ptr_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_request_ptr_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_request_launch_abi_layout_reported": True,
            "future_kernel_native_consumer_request_launch_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_request_launch_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI_LAYOUT_EXPECTED
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_layout_reported": True,
            "future_kernel_native_consumer_request_launch_ptr_abi_layout_fields": list(
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI_LAYOUT_FIELDS
            ),
            "future_kernel_native_consumer_request_launch_ptr_abi_layout_expected": dict(
                FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI_LAYOUT_EXPECTED
            ),
            "layout": "struct_of_arrays",
            "row_order": "vllm_prelaunch_sorted_token_ids_order",
            "row_count_source": "consumer_row_count",
            "row_fields": row_fields,
            "row_metadata": [
                {
                    "name": "layer_id",
                    "abi_dtype": "int32",
                    "shape": "scalar",
                    "source": "prelaunch_layer_context",
                    "required": True,
                },
                {
                    "name": "expert_id",
                    "abi_dtype": "int32",
                    "shape": ["row_count"],
                    "source": "address_key.layer_expert",
                    "required": True,
                },
                {
                    "name": "address_key_hash",
                    "abi_dtype": "uint64",
                    "shape": ["row_count"],
                    "source": "address_key",
                    "required": True,
                },
                {
                    "name": "row_order_hash",
                    "abi_dtype": "uint64",
                    "shape": "scalar",
                    "source": "prepared_handle_table",
                    "required": True,
                },
                {
                    "name": "ordered_row_hash",
                    "abi_dtype": "uint64",
                    "shape": "scalar",
                    "source": "prepared_handle_table",
                    "required": True,
                },
            ],
        },
        "safety_contract": {
            "payload_bytes_required": 0,
            "ready_credit_required": False,
            "changes_router_required": False,
            "changes_descriptor_order_required": False,
            "changes_kernel_launch_args_required": False,
            "passed_to_kernel_required": False,
            "live_compatible_with_current_wna16_args_required": False,
            "current_status": "native_stub_pending",
        },
        "required_gate_checks": {
            "consumer_view_required": True,
            "consumer_view_row_layout_required": True,
            "consumer_view_handle_projection_required": True,
            "consumer_view_all_handle_fields_required": True,
            "consumer_view_source_packet_chain_depth_required": 3,
            "consumer_program_view_required": True,
            "consumer_program_view_row_assignment_formula": (
                "program_id * rows_per_program + lane_id + row_offset"
            ),
            "consumer_program_view_ptr_required": True,
            "request_launch_all_handle_fields_required": True,
            "request_launch_ptr_all_handle_fields_required": True,
            "kernel_entry_summary_row_metadata_required": True,
            "kernel_entry_args_row_metadata_required": True,
            "payload_bytes_required": 0,
            "passed_to_kernel_required": False,
            "changes_kernel_launch_args_required": False,
            "current_wna16_arg_compatible_required": False,
        },
        "debug_macro_ladder": {
            "compile_guard_macro": "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1",
            "flags": [
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": (
                        "MTP_PREMAP_TYPED_CONSUMER_CHECK_"
                        "FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI"
                    ),
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
                    "default": "disabled",
                    "individually_enableable": False,
                    "forbidden_in_lab_default": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
                    "default": "disabled",
                    "individually_enableable": False,
                    "forbidden_in_lab_default": True,
                },
            ],
        },
    }


def _write_valid_schema(root: Path) -> str:
    schema_path = "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    _write(root / schema_path, json.dumps(_valid_schema_payload()) + "\n")
    return schema_path


def _lab_evidence_metrics(
    *,
    single_field_name: str = "scale_metadata_handle",
) -> dict[str, object]:
    bridge = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "native_typed_consumer_bridge_"
    )
    stub = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "native_stub_online_invocation_"
    )
    single = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_"
    )
    typed_row = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "kernel_side_typed_row_consumer_path_"
    )
    metrics: dict[str, object] = {
        f"{bridge}checked_count": 3,
        f"{bridge}ok_count": 3,
        f"{bridge}mode": "readonly_native_typed_consumer_bridge_check",
        f"{bridge}failure_count": 0,
        f"{bridge}payload_bytes": 0,
        f"{bridge}payload_violation_count": 0,
        f"{bridge}ready_credit_count": 0,
        f"{bridge}changes_router_count": 0,
        f"{bridge}changes_descriptor_order_count": 0,
        f"{bridge}passed_to_kernel_count": 0,
        f"{bridge}kernel_arg_violation_count": 0,
        f"{bridge}required_handle_zero_count": 0,
        f"{bridge}expert_id_invalid_count": 0,
        f"{bridge}address_key_hash_zero_count": 0,
        f"{stub}checked_count": 3,
        f"{stub}ready_count": 3,
        f"{stub}ok_count": 3,
        f"{stub}requested_count": 3,
        f"{stub}blocked_count": 3,
        f"{stub}native_checker_invoked_count": 3,
        f"{stub}native_bridge_ok_count": 3,
        f"{stub}mode": "readonly_native_stub_online_invocation_canary",
        f"{stub}block_reason": "native_stub_live_disabled",
        f"{stub}failure_count": 0,
        f"{stub}payload_bytes": 0,
        f"{stub}payload_violation_count": 0,
        f"{stub}ready_credit_count": 0,
        f"{stub}changes_router_count": 0,
        f"{stub}changes_descriptor_order_count": 0,
        f"{stub}passed_to_kernel_count": 0,
        f"{stub}kernel_arg_violation_count": 0,
        f"{stub}native_stub_invoked_count": 0,
        f"{stub}required_handle_zero_count": 0,
        f"{stub}expert_id_invalid_count": 0,
        f"{stub}address_key_hash_zero_count": 0,
        f"{single}checked_count": 3,
        f"{single}ready_count": 3,
        f"{single}hash_checked_count": 3,
        f"{single}hash_missing_count": 0,
        f"{single}table_object_hash_checked_count": 3,
        f"{single}table_object_hash_missing_count": 0,
        f"{single}semantic_adapter_hash_checked_count": 3,
        f"{single}semantic_adapter_hash_missing_count": 0,
        f"{single}field_handle_hash_checked_count": 3,
        f"{single}field_handle_hash_missing_count": 0,
        f"{single}semantic_field_hash_checked_count": 3,
        f"{single}semantic_field_hash_missing_count": 0,
        f"{single}mirror_handle_hash_checked_count": 3,
        f"{single}mirror_handle_hash_missing_count": 0,
        f"{single}mirror_schema_hash_checked_count": 3,
        f"{single}mirror_schema_hash_missing_count": 0,
        f"{single}mode": "readonly_single_field_handle_handoff_canary",
        f"{single}mode_checked_count": 3,
        f"{single}mode_missing_count": 0,
        f"{single}mode_mismatch_count": 0,
        f"{single}field_name": single_field_name,
        f"{single}field_name_checked_count": 3,
        f"{single}field_name_missing_count": 0,
        f"{single}field_name_mismatch_count": 0,
        f"{single}source": "semantic_handle_table",
        f"{single}source_checked_count": 3,
        f"{single}source_missing_count": 0,
        f"{single}source_mismatch_count": 0,
        f"{single}mirror_mode": f"readonly_{single_field_name}_mirror",
        f"{single}mirror_mode_checked_count": 3,
        f"{single}mirror_mode_missing_count": 0,
        f"{single}mirror_mode_mismatch_count": 0,
        f"{single}mirror_ready_count": 3,
        f"{single}mirror_field_name": single_field_name,
        f"{single}mirror_field_name_checked_count": 3,
        f"{single}mirror_field_name_missing_count": 0,
        f"{single}mirror_field_name_mismatch_count": 0,
        f"{single}mirror_source": "semantic_handle_table",
        f"{single}mirror_source_checked_count": 3,
        f"{single}mirror_source_missing_count": 0,
        f"{single}mirror_source_mismatch_count": 0,
        f"{single}block_reason": "single_field_handoff_live_disabled",
        f"{single}block_reason_checked_count": 3,
        f"{single}block_reason_missing_count": 0,
        f"{single}block_reason_mismatch_count": 0,
        f"{single}row_count": 6,
        f"{single}field_handle_count": 6,
        f"{single}field_handle_nonzero_count": 6,
        f"{single}field_handle_zero_count": 0,
        f"{single}parity_ok_count": 6,
        f"{single}parity_mismatch_count": 0,
        f"{single}live_enabled_count": 0,
        f"{single}blocked_count": 3,
        f"{single}payload_bytes": 0,
        f"{single}payload_violation_count": 0,
        f"{single}ready_credit_count": 0,
        f"{single}passed_to_kernel_count": 0,
        f"{single}changes_kernel_launch_args_count": 0,
        f"{single}kernel_arg_violation_count": 0,
        f"{single}live_compatible_with_current_wna16_args_count": 0,
        f"{single}kernel_side_typed_consumer_compatible_count": 3,
        f"{single}current_wna16_arg_compatible_count": 0,
        f"{typed_row}checked_count": 3,
        f"{typed_row}ready_count": 3,
        f"{typed_row}mode": "readonly_typed_row_consumer_path",
        f"{typed_row}name": "premap_kernel_side_typed_consumer_path_v1",
        f"{typed_row}source": "vllm_prelaunch_prepared_handle_table",
        f"{typed_row}schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        f"{typed_row}row_count": 6,
        f"{typed_row}row_ok_count": 6,
        f"{typed_row}column_count_max": 4,
        f"{typed_row}column_count_min": 4,
        f"{typed_row}error_count": 0,
        f"{typed_row}failure_count": 0,
        f"{typed_row}payload_bytes": 0,
        f"{typed_row}payload_violation_count": 0,
        f"{typed_row}passed_to_kernel_count": 0,
        f"{typed_row}kernel_arg_violation_count": 0,
        f"{typed_row}current_wna16_arg_compatible_count": 0,
    }
    return metrics


def _native_bridge_input_payload() -> dict[str, object]:
    return {
        "_meta": {
            "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            "table_object_hash": "table-object-hash",
            "row_count": 2,
            "column_count": 4,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "descriptor_ptr": [101, 102],
        "packed_weight_descriptor": [201, 202],
        "scale_metadata_handle": [301, 302],
        "aux_metadata_handle": [0, 0],
        "expert_id": [3, 7],
        "address_key_hash": [401, 402],
    }


def _native_online_prelaunch_input_payload() -> dict[str, object]:
    payload = _native_bridge_input_payload()
    meta = dict(payload["_meta"])
    meta.update(
        {
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
        }
    )
    payload["_meta"] = meta
    payload["_export_context"] = {
        "source": "vllm_prelaunch_premap_kernel_arg_shadow_table_object",
        "row_count": 2,
        "column_count": 4,
        "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        "table_object_hash": "table-object-hash",
        "payload_bytes": 0,
        "ready_credit": False,
        "changes_router": False,
        "changes_descriptor_order": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    return payload


def _native_stub_evidence_payload(input_json: str) -> dict[str, object]:
    return {
        "passed": True,
        "failures": [],
        "ok": True,
        "row_count": 2,
        "row_ok_count": 2,
        "error_count": 0,
        "column_count": 4,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "input_source": "binary_prefix",
        "input_json": input_json,
        "expected_schema_hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
        "compiled_macros": {
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA": True,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION": True,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY": True,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME": True,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS": False,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH": False,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI": False,
            "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR": True,
        },
    }


def _native_stub_endpoint_ptr_evidence_payload(
    input_json: str,
    *,
    field_mask: int = 7,
    aux_read_count: int = 0,
) -> dict[str, object]:
    payload = _native_stub_evidence_payload(input_json)
    payload.update(
        {
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
            "future_kernel_native_consumer_endpoint_ptr_summary_row_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_error_count": 0,
            "future_kernel_native_consumer_endpoint_ptr_summary_field_mask": field_mask,
            "future_kernel_native_consumer_endpoint_ptr_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_aux_metadata_handle_read_row_ok_count": aux_read_count,
            "future_kernel_native_consumer_endpoint_ptr_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_endpoint_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_endpoint_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_endpoint_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_endpoint_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_endpoint_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_endpoint_summary_field_mask": field_mask,
            "future_kernel_native_consumer_endpoint_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_summary_aux_metadata_handle_read_row_ok_count": aux_read_count,
            "future_kernel_native_consumer_endpoint_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_endpoint_summary_row_hash_accumulator": (
                "endpoint-row-hash"
            ),
            "future_kernel_native_consumer_endpoint_ptr_summary_row_hash_accumulator": (
                "endpoint-row-hash"
            ),
        }
    )
    payload["compiled_macros"] = {
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME": True,
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ENVELOPE_ARGS_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_DESCRIPTOR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF": False,
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS": False,
    }
    return payload


def _native_stub_request_ptr_evidence_payload(input_json: str) -> dict[str, object]:
    payload = _native_stub_evidence_payload(input_json)
    row_hash = "1234567890abcdef"
    field_read_hash = "0fedcba987654321"
    row_metadata_hash = "55aa55aa55aa55aa"
    payload.update(
        {
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
            "future_kernel_native_consumer_request_ptr_summary_row_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_error_count": 0,
            "future_kernel_native_consumer_request_ptr_summary_field_mask": 15,
            "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator": row_metadata_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_summary_field_mask": 15,
            "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }
    )
    payload["compiled_macros"] = {
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME": True,
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_PTR_ABI": True,
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF": False,
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS": False,
    }
    return payload


def _native_stub_request_launch_evidence_payload(input_json: str) -> dict[str, object]:
    payload = _native_stub_request_ptr_evidence_payload(input_json)
    row_hash = "1234567890abcdef"
    field_read_hash = "0fedcba987654321"
    row_metadata_hash = "55aa55aa55aa55aa"
    payload.update(
        {
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
            "future_kernel_native_consumer_request_launch_request_id": 1,
            "future_kernel_native_consumer_request_launch_device_ordinal": 0,
            "future_kernel_native_consumer_request_launch_stream_domain": 0,
            "future_kernel_native_consumer_request_launch_grid_x": 1,
            "future_kernel_native_consumer_request_launch_block_x": 256,
            "future_kernel_native_consumer_request_launch_row_offset": 0,
            "future_kernel_native_consumer_request_launch_row_limit": 2,
            "future_kernel_native_consumer_request_launch_rows_per_program": 256,
            "future_kernel_native_consumer_request_launch_row_count": 2,
            "future_kernel_native_consumer_request_launch_payload_bytes": 0,
            "future_kernel_native_consumer_request_launch_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_launch_passed_to_kernel": False,
            "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_launch_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_launch_summary_row_count": 2,
            "future_kernel_native_consumer_request_launch_summary_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_error_count": 0,
            "future_kernel_native_consumer_request_launch_summary_field_mask": 15,
            "future_kernel_native_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_launch_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_launch_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }
    )
    payload["compiled_macros"][
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_ABI"
    ] = True
    return payload


def _native_stub_request_launch_ptr_evidence_payload(input_json: str) -> dict[str, object]:
    payload = _native_stub_request_launch_evidence_payload(input_json)
    row_hash = "1234567890abcdef"
    field_read_hash = "0fedcba987654321"
    row_metadata_hash = "55aa55aa55aa55aa"
    payload.update(
        {
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
            "future_kernel_native_consumer_request_launch_ptr_request_id": 1,
            "future_kernel_native_consumer_request_launch_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_request_launch_ptr_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_launch_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_request_launch_ptr_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_launch_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_launch_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_launch_ptr_summary_row_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_error_count": 0,
            "future_kernel_native_consumer_request_launch_ptr_summary_field_mask": 15,
            "future_kernel_native_consumer_request_launch_ptr_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_ptr_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_launch_ptr_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }
    )
    payload["compiled_macros"][
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_REQUEST_LAUNCH_PTR_ABI"
    ] = True
    return payload


def _native_stub_per_field_evidence_payload(input_json: str) -> dict[str, object]:
    payload = _native_stub_evidence_payload(input_json)
    payload.update(
        {
            "abi_name": "premap_kernel_side_typed_consumer_abi_v1",
            "abi_handle_column_count": 4,
            "abi_payload_bytes_allowed": False,
            "abi_kernel_arg_pass_allowed": False,
            "abi_header": (
                "/tmp/repo/microbench/premap_kernel_consumer/"
                "premap_typed_consumer_abi_v1.h"
            ),
            "adapter_name": "premap_kernel_side_typed_consumer_adapter_v1",
            "adapter_payload_deref_allowed": False,
            "adapter_kernel_arg_pass_allowed": False,
            "adapter_header": (
                "/tmp/repo/microbench/premap_kernel_consumer/"
                "premap_typed_consumer_adapter_v1.h"
            ),
            "single_field_mirror_checked": True,
            "single_field_mirror_mode": "readonly_scale_metadata_handle_abi_row_mirror",
            "single_field_mirror_field_name": "scale_metadata_handle",
            "single_field_mirror_source": "typed_consumer_abi_row_adapter_v1",
            "single_field_mirror_row_count": 2,
            "single_field_mirror_row_ok_count": 2,
            "single_field_mirror_error_count": 0,
            "single_field_mirror_hash_accumulator": "mirror-hash",
            "single_field_mirror_payload_bytes": 0,
            "single_field_mirror_passed_to_kernel": False,
            "single_field_mirror_changes_kernel_launch_args": False,
            "single_field_mirror_kernel_side_typed_consumer_compatible": True,
            "single_field_mirror_current_wna16_arg_compatible": False,
        }
    )
    payload["compiled_macros"] = {
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME": True,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH": False,
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI": False,
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR": True,
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF": False,
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS": False,
    }
    return payload


def _runner_stub_summary() -> dict[str, object]:
    return {
        "passed": True,
        "failures": [],
        "ok": True,
        "row_count": 2,
        "row_ok_count": 2,
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "kernel_side_consumer_path_checked": True,
        "kernel_side_consumer_path_name": "premap_kernel_side_typed_consumer_path_v1",
        "kernel_side_consumer_path_row_count": 2,
        "kernel_side_consumer_path_row_ok_count": 2,
        "kernel_side_consumer_path_error_count": 0,
        "kernel_side_consumer_path_payload_bytes": 0,
        "kernel_side_consumer_path_passed_to_kernel": False,
        "kernel_side_consumer_path_changes_kernel_launch_args": False,
        "kernel_side_consumer_path_current_wna16_arg_compatible": False,
    }


_RUNNER_NATIVE_LAYOUT_SUMMARY: dict[str, object] = {
    "future_kernel_native_consumer_params_struct_size": 112,
    "future_kernel_native_consumer_params_struct_align": 8,
    "future_kernel_native_consumer_result_struct_size": 56,
    "future_kernel_native_consumer_result_struct_align": 8,
    "future_kernel_native_consumer_params_offset_descriptor_ptr": 0,
    "future_kernel_native_consumer_params_offset_packed_weight_descriptor": 8,
    "future_kernel_native_consumer_params_offset_scale_metadata_handle": 16,
    "future_kernel_native_consumer_params_offset_aux_metadata_handle": 24,
    "future_kernel_native_consumer_params_offset_expert_id": 32,
    "future_kernel_native_consumer_params_offset_address_key_hash": 40,
    "future_kernel_native_consumer_params_offset_row_count": 80,
    "future_kernel_native_consumer_params_offset_field_mask": 92,
    "future_kernel_native_consumer_params_offset_payload_bytes": 100,
    "future_kernel_native_consumer_params_offset_flags": 104,
}
_RUNNER_LAUNCH_LAYOUT_SUMMARY: dict[str, object] = {
    "future_kernel_native_launch_consumer_launch_struct_size": 136,
    "future_kernel_native_launch_consumer_launch_struct_align": 8,
    "future_kernel_native_launch_consumer_params_struct_size": 112,
    "future_kernel_native_launch_consumer_params_struct_align": 8,
    "future_kernel_native_launch_consumer_result_struct_size": 64,
    "future_kernel_native_launch_consumer_result_struct_align": 8,
    "future_kernel_native_launch_consumer_offset_params": 0,
    "future_kernel_native_launch_consumer_offset_abi_version": 112,
    "future_kernel_native_launch_consumer_offset_params_struct_size": 116,
    "future_kernel_native_launch_consumer_offset_result_struct_size": 120,
    "future_kernel_native_launch_consumer_offset_row_stride": 124,
    "future_kernel_native_launch_consumer_offset_payload_bytes": 128,
    "future_kernel_native_launch_consumer_offset_flags": 132,
}
_RUNNER_DISPATCH_LAYOUT_SUMMARY: dict[str, object] = {
    "future_kernel_native_dispatch_consumer_dispatch_struct_size": 176,
    "future_kernel_native_dispatch_consumer_dispatch_struct_align": 8,
    "future_kernel_native_dispatch_consumer_result_struct_size": 72,
    "future_kernel_native_dispatch_consumer_result_struct_align": 8,
    "future_kernel_native_dispatch_consumer_offset_launch": 0,
    "future_kernel_native_dispatch_consumer_offset_dispatch_version": 136,
    "future_kernel_native_dispatch_consumer_offset_grid_x": 140,
    "future_kernel_native_dispatch_consumer_offset_block_x": 144,
    "future_kernel_native_dispatch_consumer_offset_shared_mem_bytes": 148,
    "future_kernel_native_dispatch_consumer_offset_row_offset": 152,
    "future_kernel_native_dispatch_consumer_offset_row_limit": 156,
    "future_kernel_native_dispatch_consumer_offset_rows_per_program": 160,
    "future_kernel_native_dispatch_consumer_offset_payload_bytes": 164,
    "future_kernel_native_dispatch_consumer_offset_flags": 168,
}
_RUNNER_DISPATCH_PTR_LAYOUT_SUMMARY: dict[str, object] = {
    "future_kernel_native_dispatch_ptr_consumer_packet_struct_size": 32,
    "future_kernel_native_dispatch_ptr_consumer_packet_struct_align": 8,
    "future_kernel_native_dispatch_ptr_consumer_dispatch_struct_size": 176,
    "future_kernel_native_dispatch_ptr_consumer_result_struct_size": 72,
    "future_kernel_native_dispatch_ptr_consumer_offset_dispatch": 0,
    "future_kernel_native_dispatch_ptr_consumer_offset_abi_version": 8,
    "future_kernel_native_dispatch_ptr_consumer_offset_dispatch_struct_size": 12,
    "future_kernel_native_dispatch_ptr_consumer_offset_result_struct_size": 16,
    "future_kernel_native_dispatch_ptr_consumer_offset_payload_bytes": 20,
    "future_kernel_native_dispatch_ptr_consumer_offset_flags": 24,
}
_RUNNER_ARG_SLOT_LAYOUT_SUMMARY: dict[str, object] = {
    "future_kernel_native_arg_slot_consumer_slot_struct_size": 32,
    "future_kernel_native_arg_slot_consumer_slot_struct_align": 8,
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_struct_size": 32,
    "future_kernel_native_arg_slot_consumer_result_struct_size": 72,
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr": 0,
    "future_kernel_native_arg_slot_consumer_offset_abi_version": 8,
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr_struct_size": 12,
    "future_kernel_native_arg_slot_consumer_offset_result_struct_size": 16,
    "future_kernel_native_arg_slot_consumer_offset_payload_bytes": 20,
    "future_kernel_native_arg_slot_consumer_offset_flags": 24,
}
_RUNNER_CONSUMER_VIEW_LAYOUT_SUMMARY: dict[str, object] = {
    "future_kernel_native_consumer_view_struct_size": 208,
    "future_kernel_native_consumer_view_struct_align": 8,
    "future_kernel_native_consumer_view_params_struct_size": 112,
    "future_kernel_native_consumer_view_params_struct_align": 8,
    "future_kernel_native_consumer_view_result_struct_size": 80,
    "future_kernel_native_consumer_view_result_struct_align": 8,
    "future_kernel_native_consumer_view_row_struct_size": 56,
    "future_kernel_native_consumer_view_row_struct_align": 8,
    "future_kernel_native_consumer_view_row_offset_descriptor_ptr": 0,
    "future_kernel_native_consumer_view_row_offset_packed_weight_descriptor": 8,
    "future_kernel_native_consumer_view_row_offset_scale_metadata_handle": 16,
    "future_kernel_native_consumer_view_row_offset_aux_metadata_handle": 24,
    "future_kernel_native_consumer_view_row_offset_expert_id": 32,
    "future_kernel_native_consumer_view_row_offset_address_key_hash": 40,
    "future_kernel_native_consumer_view_row_offset_row_index": 48,
    "future_kernel_native_consumer_view_offset_params": 0,
    "future_kernel_native_consumer_view_offset_abi_version": 112,
    "future_kernel_native_consumer_view_offset_source_packet_chain_depth": 116,
    "future_kernel_native_consumer_view_offset_row_offset": 120,
    "future_kernel_native_consumer_view_offset_row_limit": 124,
    "future_kernel_native_consumer_view_offset_rows_per_program": 128,
    "future_kernel_native_consumer_view_offset_payload_bytes": 132,
    "future_kernel_native_consumer_view_offset_flags": 136,
}


def _runner_kernel_side_compatible_summary() -> dict[str, object]:
    payload = _runner_stub_summary()
    payload.update(
        {
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
            "kernel_side_compatible_consumer_row_count": 2,
            "kernel_side_compatible_consumer_row_ok_count": 2,
            "kernel_side_compatible_consumer_error_count": 0,
            "kernel_side_compatible_consumer_payload_bytes": 0,
            "kernel_side_compatible_consumer_passed_to_kernel": False,
            "kernel_side_compatible_consumer_changes_kernel_launch_args": False,
            "kernel_side_compatible_consumer_current_wna16_arg_compatible": False,
        }
    )
    return payload


def _runner_future_kernel_args_summary(
    field_name: str = "scale_metadata_handle",
) -> dict[str, object]:
    payload = _runner_stub_summary()
    payload.update(
        {
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
            "future_kernel_consumer_args_row_count": 2,
            "future_kernel_consumer_args_row_ok_count": 2,
            "future_kernel_consumer_args_error_count": 0,
            "future_kernel_consumer_args_struct_size": 160,
            "future_kernel_consumer_args_struct_align": 8,
            "future_kernel_consumer_args_result_struct_size": 56,
            "future_kernel_consumer_args_result_struct_align": 8,
            "future_kernel_consumer_args_offset_envelope": 0,
            "future_kernel_consumer_args_offset_field_mask": 144,
            "future_kernel_consumer_args_offset_single_field_mirror_kind": 148,
            "future_kernel_consumer_args_offset_payload_bytes": 152,
            "future_kernel_consumer_args_offset_flags": 156,
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
            "future_kernel_consumer_args_single_field_mirror_row_count": 2,
            "future_kernel_consumer_args_single_field_mirror_row_ok_count": 2,
            "future_kernel_consumer_args_single_field_mirror_error_count": 0,
        }
    )
    return payload


def _runner_future_kernel_args_compatible_path_summary() -> dict[str, object]:
    payload = _runner_future_kernel_args_summary()
    payload.update(
        {
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
            "future_kernel_args_compatible_consumer_path_row_count": 2,
            "future_kernel_args_compatible_consumer_path_row_ok_count": 2,
            "future_kernel_args_compatible_consumer_path_error_count": 0,
            "future_kernel_args_compatible_consumer_path_payload_bytes": 0,
            "future_kernel_args_compatible_consumer_path_passed_to_kernel": False,
            "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args": False,
            "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible": False,
            "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation": False,
        }
    )
    return payload


def _runner_future_kernel_native_consumer_summary(
    field_name: str = "scale_metadata_handle",
) -> dict[str, object]:
    payload = _runner_stub_summary()
    payload.update(
        {
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
            "future_kernel_native_consumer_row_count": 2,
            "future_kernel_native_consumer_row_ok_count": 2,
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
            "future_kernel_native_consumer_single_field_mirror_row_count": 2,
            "future_kernel_native_consumer_single_field_mirror_row_ok_count": 2,
            "future_kernel_native_consumer_single_field_mirror_error_count": 0,
        }
    )
    payload.update(_RUNNER_NATIVE_LAYOUT_SUMMARY)
    return payload


def _runner_future_kernel_native_launch_consumer_summary(
    field_name: str = "scale_metadata_handle",
) -> dict[str, object]:
    payload = _runner_future_kernel_native_consumer_summary(field_name=field_name)
    payload.update(
        {
            "future_kernel_native_consumer_checked": True,
            "future_kernel_native_consumer_row_count": 2,
            "future_kernel_native_consumer_row_ok_count": 2,
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
            "future_kernel_native_launch_consumer_version": 1,
            "future_kernel_native_launch_consumer_row_count": 2,
            "future_kernel_native_launch_consumer_row_ok_count": 2,
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
            "future_kernel_native_launch_consumer_single_field_mirror_row_count": 2,
            "future_kernel_native_launch_consumer_single_field_mirror_row_ok_count": 2,
            "future_kernel_native_launch_consumer_single_field_mirror_error_count": 0,
        }
    )
    payload.update(_RUNNER_NATIVE_LAYOUT_SUMMARY)
    payload.update(_RUNNER_LAUNCH_LAYOUT_SUMMARY)
    return payload


def _runner_future_kernel_native_dispatch_consumer_summary(
    field_name: str = "scale_metadata_handle",
) -> dict[str, object]:
    payload = _runner_future_kernel_native_launch_consumer_summary(
        field_name=field_name
    )
    payload.update(
        {
            "future_kernel_native_consumer_checked": True,
            "future_kernel_native_consumer_row_count": 2,
            "future_kernel_native_consumer_row_ok_count": 2,
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
            "future_kernel_native_dispatch_consumer_version": 1,
            "future_kernel_native_dispatch_consumer_row_count": 2,
            "future_kernel_native_dispatch_consumer_row_ok_count": 2,
            "future_kernel_native_dispatch_consumer_hash_accumulator": "abc123",
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": "481d",
            "future_kernel_native_dispatch_consumer_active_rows": 2,
            "future_kernel_native_dispatch_consumer_row_offset": 0,
            "future_kernel_native_dispatch_consumer_row_limit": 2,
            "future_kernel_native_dispatch_consumer_grid_x": 1,
            "future_kernel_native_dispatch_consumer_block_x": 256,
            "future_kernel_native_dispatch_consumer_launch_threads": 256,
            "future_kernel_native_dispatch_consumer_rows_per_program": 256,
            "future_kernel_native_dispatch_consumer_shared_mem_bytes": 0,
            "future_kernel_native_dispatch_consumer_program_iteration_checked": True,
            "future_kernel_native_dispatch_consumer_row_assignment_formula": (
                "row_offset + program_id * rows_per_program + lane_id"
            ),
            "future_kernel_native_dispatch_consumer_program_count": 1,
            "future_kernel_native_dispatch_consumer_full_program_count": 0,
            "future_kernel_native_dispatch_consumer_last_program_active_rows": 2,
            "future_kernel_native_dispatch_consumer_inactive_lane_count": 254,
            "future_kernel_native_dispatch_consumer_first_program_row_offset": 0,
            "future_kernel_native_dispatch_consumer_last_program_row_offset": 0,
            "future_kernel_native_dispatch_consumer_program_iteration_hash": (
                f"{_program_iteration_hash(grid_x=1, block_x=256, row_offset=0, row_limit=2, last_program_active_rows=2, inactive_lane_count=254):x}"
            ),
            "future_kernel_native_dispatch_consumer_launch_geometry_checked": True,
            "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
            "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
            "future_kernel_native_dispatch_consumer_error_count": 0,
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
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_count": 2,
            "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count": 2,
            "future_kernel_native_dispatch_consumer_single_field_mirror_error_count": 0,
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
            "future_kernel_native_dispatch_ptr_consumer_row_count": 2,
            "future_kernel_native_dispatch_ptr_consumer_row_ok_count": 2,
            "future_kernel_native_dispatch_ptr_consumer_error_count": 0,
            "future_kernel_native_dispatch_ptr_consumer_hash_accumulator": "def456",
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": "481d",
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
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_count": 2,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_row_ok_count": 2,
            "future_kernel_native_dispatch_ptr_consumer_single_field_mirror_error_count": 0,
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
            "future_kernel_native_arg_slot_consumer_row_count": 2,
            "future_kernel_native_arg_slot_consumer_row_ok_count": 2,
            "future_kernel_native_arg_slot_consumer_error_count": 0,
            "future_kernel_native_arg_slot_consumer_hash_accumulator": "fedcba",
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": "481d",
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count": 2,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator": "d35c1",
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count": 2,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator": "d35c2",
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count": 2,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator": "d35c3",
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count": 2,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator": "d35c4",
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
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": 2,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": 2,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_error_count": 0,
            "future_kernel_native_consumer_view_checked": True,
            "future_kernel_native_consumer_view_abi_name": (
                "premap_future_kernel_native_consumer_view_abi_v1"
            ),
            "future_kernel_native_consumer_view_mode": (
                "readonly_future_kernel_native_consumer_view_abi"
            ),
            "future_kernel_native_consumer_view_source": (
                "premap_future_kernel_native_consumer_arg_slot_abi_v1"
            ),
            "future_kernel_native_consumer_view_version": 1,
            "future_kernel_native_consumer_view_row_count": 2,
            "future_kernel_native_consumer_view_row_ok_count": 2,
            "future_kernel_native_consumer_view_error_count": 0,
            "future_kernel_native_consumer_view_hash_accumulator": "0fedcb",
            "future_kernel_native_consumer_view_handle_projection_hash_accumulator": "481d",
            "future_kernel_native_consumer_view_descriptor_ptr_read_row_count": 2,
            "future_kernel_native_consumer_view_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_view_descriptor_ptr_read_error_count": 0,
            "future_kernel_native_consumer_view_descriptor_ptr_read_hash_accumulator": "c35c1",
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_count": 2,
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_error_count": 0,
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_hash_accumulator": "c35c2",
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_count": 2,
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_view_scale_metadata_handle_read_error_count": 0,
            "future_kernel_native_consumer_view_scale_metadata_handle_read_hash_accumulator": "c35c3",
            "future_kernel_native_consumer_view_aux_metadata_handle_read_row_count": 2,
            "future_kernel_native_consumer_view_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_view_aux_metadata_handle_read_error_count": 0,
            "future_kernel_native_consumer_view_aux_metadata_handle_read_hash_accumulator": "c35c4",
            "future_kernel_native_consumer_view_packet_chain_depth": 3,
            "future_kernel_native_consumer_view_source_packet_chain_depth": 3,
            "future_kernel_native_consumer_view_row_offset": 0,
            "future_kernel_native_consumer_view_row_limit": 2,
            "future_kernel_native_consumer_view_rows_per_program": 256,
            "future_kernel_native_consumer_view_payload_bytes": 0,
            "future_kernel_native_consumer_view_passed_to_kernel": False,
            "future_kernel_native_consumer_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_view_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_view_field_mask": 15,
            "future_kernel_native_consumer_view_required_field_mask": 7,
            "future_kernel_native_consumer_view_single_field_mirror_checked": True,
            "future_kernel_native_consumer_view_single_field_mirror_field_name": (
                field_name
            ),
            "future_kernel_native_consumer_view_single_field_mirror_row_count": 2,
            "future_kernel_native_consumer_view_single_field_mirror_row_ok_count": 2,
            "future_kernel_native_consumer_view_single_field_mirror_error_count": 0,
            "future_kernel_native_consumer_program_view_checked": True,
            "future_kernel_native_consumer_program_view_abi_name": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_mode": (
                "readonly_future_kernel_native_consumer_program_view_abi"
            ),
            "future_kernel_native_consumer_program_view_source": (
                "premap_future_kernel_native_consumer_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_version": 1,
            "future_kernel_native_consumer_program_view_row_count": 2,
            "future_kernel_native_consumer_program_view_row_ok_count": 2,
            "future_kernel_native_consumer_program_view_error_count": 0,
            "future_kernel_native_consumer_program_view_hash_accumulator": "0abcde",
            "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator": (
                "481d"
            ),
            "future_kernel_native_consumer_program_view_program_count": 1,
            "future_kernel_native_consumer_program_view_full_program_count": 0,
            "future_kernel_native_consumer_program_view_last_program_active_rows": 2,
            "future_kernel_native_consumer_program_view_inactive_lane_count": 254,
            "future_kernel_native_consumer_program_view_first_program_row_offset": 0,
            "future_kernel_native_consumer_program_view_last_program_row_offset": 0,
            "future_kernel_native_consumer_program_view_program_iteration_hash": (
                f"{_program_iteration_hash(grid_x=1, block_x=256, row_offset=0, row_limit=2, last_program_active_rows=2, inactive_lane_count=254):x}"
            ),
            "future_kernel_native_consumer_program_view_row_assignment_formula": (
                "program_id * rows_per_program + lane_id + row_offset"
            ),
            "future_kernel_native_consumer_program_view_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_program_view_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_program_view_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_program_view_field_mask": 15,
            "future_kernel_native_consumer_program_view_required_field_mask": 7,
            "future_kernel_native_consumer_program_view_ptr_checked": True,
            "future_kernel_native_consumer_program_view_ptr_abi_name": (
                "premap_future_kernel_native_consumer_program_view_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_mode": (
                "readonly_future_kernel_native_consumer_program_view_ptr_abi"
            ),
            "future_kernel_native_consumer_program_view_ptr_source": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_version": 1,
            "future_kernel_native_consumer_program_view_ptr_row_count": 2,
            "future_kernel_native_consumer_program_view_ptr_row_ok_count": 2,
            "future_kernel_native_consumer_program_view_ptr_error_count": 0,
            "future_kernel_native_consumer_program_view_ptr_hash_accumulator": (
                "0c053"
            ),
            "future_kernel_native_consumer_program_view_ptr_field_mask": 15,
            "future_kernel_native_consumer_program_view_ptr_required_field_mask": 7,
            "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": False,
        }
    )
    payload.update(_RUNNER_NATIVE_LAYOUT_SUMMARY)
    payload.update(_RUNNER_LAUNCH_LAYOUT_SUMMARY)
    payload.update(_RUNNER_DISPATCH_LAYOUT_SUMMARY)
    payload.update(_RUNNER_DISPATCH_PTR_LAYOUT_SUMMARY)
    payload.update(_RUNNER_ARG_SLOT_LAYOUT_SUMMARY)
    payload.update(_RUNNER_CONSUMER_VIEW_LAYOUT_SUMMARY)
    return payload


def _runner_future_kernel_native_request_ptr_summary() -> dict[str, object]:
    row_hash = "1234567890abcdef"
    field_read_hash = "0fedcba987654321"
    row_metadata_hash = "55aa55aa55aa55aa"
    payload = _runner_stub_summary()
    payload.update(
        {
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
            "future_kernel_native_consumer_request_ptr_summary_row_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_error_count": 0,
            "future_kernel_native_consumer_request_ptr_summary_field_mask": 15,
            "future_kernel_native_consumer_request_ptr_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator": row_metadata_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_summary_field_mask": 15,
            "future_kernel_native_consumer_kernel_entry_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_kernel_entry_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_kernel_entry_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }
    )
    return payload


def _runner_future_kernel_native_request_launch_summary() -> dict[str, object]:
    row_hash = "1234567890abcdef"
    field_read_hash = "0fedcba987654321"
    row_metadata_hash = "55aa55aa55aa55aa"
    payload = _runner_future_kernel_native_request_ptr_summary()
    payload.update(
        {
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
            "future_kernel_native_consumer_request_launch_request_id": 1,
            "future_kernel_native_consumer_request_launch_device_ordinal": 0,
            "future_kernel_native_consumer_request_launch_stream_domain": 0,
            "future_kernel_native_consumer_request_launch_grid_x": 1,
            "future_kernel_native_consumer_request_launch_block_x": 256,
            "future_kernel_native_consumer_request_launch_row_offset": 0,
            "future_kernel_native_consumer_request_launch_row_limit": 2,
            "future_kernel_native_consumer_request_launch_rows_per_program": 256,
            "future_kernel_native_consumer_request_launch_row_count": 2,
            "future_kernel_native_consumer_request_launch_payload_bytes": 0,
            "future_kernel_native_consumer_request_launch_payload_deref_allowed": False,
            "future_kernel_native_consumer_request_launch_passed_to_kernel": False,
            "future_kernel_native_consumer_request_launch_kernel_arg_pass_allowed": False,
            "future_kernel_native_consumer_request_launch_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_request_launch_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_request_launch_requires_wna16_arg_reinterpretation": False,
            "future_kernel_native_consumer_request_launch_summary_row_count": 2,
            "future_kernel_native_consumer_request_launch_summary_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_error_count": 0,
            "future_kernel_native_consumer_request_launch_summary_field_mask": 15,
            "future_kernel_native_consumer_request_launch_summary_descriptor_ptr_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_packed_weight_descriptor_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_scale_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_aux_metadata_handle_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_expert_id_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_address_key_hash_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_row_metadata_read_row_ok_count": 2,
            "future_kernel_native_consumer_request_launch_summary_row_hash_accumulator": row_hash,
            "future_kernel_native_consumer_request_launch_summary_field_read_hash_accumulator": field_read_hash,
            "future_kernel_native_consumer_request_launch_summary_row_metadata_hash_accumulator": row_metadata_hash,
        }
    )
    return payload


def _standalone_dispatch_ptr_canary_payload() -> dict[str, object]:
    payload = _runner_future_kernel_native_dispatch_consumer_summary()
    payload.update(
        {
            "failures": [],
            "input_source": "synthetic",
            "expected_schema_hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
            "compiled_macros": {
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME": True,
                "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI": True,
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI": True,
                "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF": False,
                "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS": False,
            },
        }
    )
    return payload


def _standalone_arg_slot_canary_payload(
    *,
    mirror_field: str = "scale_metadata_handle",
) -> dict[str, object]:
    payload = _standalone_dispatch_ptr_canary_payload()
    compiled_macros = dict(payload["compiled_macros"])
    compiled_macros[
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI"
    ] = True
    compiled_macros[
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_VIEW_ABI"
    ] = True
    compiled_macros[
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_PROGRAM_VIEW_ABI"
    ] = True
    mirror_macro_by_field = {
        "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
        "scale_metadata_handle": (
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD"
        ),
        "packed_weight_descriptor": (
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD"
        ),
        "aux_metadata_handle": (
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD"
        ),
    }
    handle_macro_by_field = {
        "descriptor_ptr": "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
        "scale_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
        "packed_weight_descriptor": "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
        "aux_metadata_handle": "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    }
    compiled_macros[handle_macro_by_field[mirror_field]] = True
    compiled_macros[mirror_macro_by_field[mirror_field]] = True
    payload["compiled_macros"] = compiled_macros
    payload[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
    ] = mirror_field
    return payload


def _wna16_adjacent_typed_slot_stub_metrics(row_count: int) -> dict[str, object]:
    prefix = "future_kernel_native_consumer_wna16_adjacent_typed_slot"
    return {
        f"{prefix}_abi_name": "premap_wna16_adjacent_typed_consumer_slot_v1",
        f"{prefix}_mode": "readonly_wna16_adjacent_typed_consumer_slot",
        f"{prefix}_source": (
            "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
        ),
        f"{prefix}_checked": True,
        f"{prefix}_packet_chain_depth": 14,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_explicit_typed_abi_slot": True,
        f"{prefix}_reuses_current_wna16_arg_slot": False,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_count": row_count,
        f"{prefix}_summary_row_ok_count": row_count,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": 15,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
        f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
        f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
        f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
        f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
    }


def _standalone_wna16_adjacent_typed_slot_canary_payload() -> dict[str, object]:
    payload = _standalone_arg_slot_canary_payload()
    compiled_macros = dict(payload["compiled_macros"])
    compiled_macros.update(
        {
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI": True,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI": True,
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_WNA16_ADJACENT_TYPED_SLOT_ABI": True,
            "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF": False,
            "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS": False,
        }
    )
    payload["compiled_macros"] = compiled_macros
    row_count = int(payload["row_count"])
    prefix = "future_kernel_native_consumer_wna16_adjacent_typed_slot"
    payload["future_kernel_native_consumer_endpoint_ptr_packet_chain_depth"] = 13
    payload.update(
        {
            f"{prefix}_abi_name": "premap_wna16_adjacent_typed_consumer_slot_v1",
            f"{prefix}_mode": "readonly_wna16_adjacent_typed_consumer_slot",
            f"{prefix}_source": (
                "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
            ),
            f"{prefix}_checked": True,
            f"{prefix}_packet_chain_depth": 14,
            f"{prefix}_payload_bytes": 0,
            f"{prefix}_payload_deref_allowed": False,
            f"{prefix}_passed_to_kernel": False,
            f"{prefix}_kernel_arg_pass_allowed": False,
            f"{prefix}_changes_kernel_launch_args": False,
            f"{prefix}_current_wna16_arg_compatible": False,
            f"{prefix}_requires_wna16_arg_reinterpretation": False,
            f"{prefix}_explicit_typed_abi_slot": True,
            f"{prefix}_reuses_current_wna16_arg_slot": False,
            f"{prefix}_summary_packet_valid": 1,
            f"{prefix}_summary_row_count": row_count,
            f"{prefix}_summary_row_ok_count": row_count,
            f"{prefix}_summary_error_count": 0,
            f"{prefix}_summary_field_mask": 15,
            f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
            f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
            f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
            f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
            f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
            f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
            f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
            f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
            f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
            f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
        }
    )
    return payload


def _payload_cache_producer_state_native_canary_payload() -> dict[str, object]:
    return {
        "abi_field_count": 9,
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "changes_kernel_launch_args": False,
        "checked": True,
        "current_count": 2,
        "current_nonempty": 1,
        "current_valid_count": 2,
        "current_wna16_arg_compatible": False,
        "error_count": 0,
        "failures": [],
        "input_source": "semantic_packet_json",
        "issue_candidate_count": 2,
        "issue_candidate_first_expert": 0,
        "issue_candidate_hash": "d949aa186c0c4928",
        "issue_candidate_last_expert": 1,
        "layer_id": 0,
        "mode": "readonly_payload_cache_producer_transition_state_native_canary",
        "native_returncode": 0,
        "native_stub_invoked": True,
        "ok": True,
        "online_configured_export_count": 1,
        "online_configured_export_enabled": True,
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "online_packet_export_first_nonempty_issue_count": 2,
        "online_packet_export_first_nonempty_issue_hash": "d949aa186c0c4928",
        "online_packet_export_first_nonempty_issue_index": 0,
        "online_packet_export_first_nonempty_issue_path": (
            "reports/premap_payload_cache_producer_state_packet.json"
        ),
        "online_packet_export_nonempty_issue_count": 1,
        "online_packet_export_count": 1,
        "online_packet_export_paths": [
            "reports/premap_payload_cache_producer_state_packet.json",
        ],
        "online_packet_export_scan_error_count": 0,
        "overlap_count": 1,
        "packet_json": "reports/premap_payload_cache_producer_state_packet.json",
        "packet_layer_id": 0,
        "packet_ready": True,
        "packet_state_hash": (
            "3ec369d6571e4ec9720415f232deb5aba64bb29206f84f7bad190d4420bff902"
        ),
        "passed": True,
        "passed_to_kernel": False,
        "payload_bytes": 0,
        "previous_count": 2,
        "previous_nonempty": 1,
        "previous_valid_count": 2,
        "ready": True,
        "ready_credit": False,
        "requested_current_count": 2,
        "requested_current_offset": 4,
        "requested_layer_id": 0,
        "requested_previous_count": 2,
        "requested_transition_topk_count": 4,
        "expected_issue_candidate_count": 2,
        "expected_issue_candidate_first_expert": 0,
        "expected_issue_candidate_hash": "d949aa186c0c4928",
        "expected_issue_candidate_last_expert": 1,
        "selected_packet_index": 0,
        "selected_packet_json": (
            "reports/premap_payload_cache_producer_state_packet.json"
        ),
        "selected_packet_selection_mode": "summary_first_nonempty_issue",
        "state_hash": "3ec369d6571e4ec9",
        "transition_topk_count": 4,
    }


def _payload_cache_producer_state_nonempty_issue_stub_payload() -> dict[str, object]:
    payload = dict(_payload_cache_producer_state_native_canary_payload())
    for key in (
        "online_configured_export_count",
        "online_configured_export_enabled",
        "online_export_source",
        "online_packet_export_count",
        "online_packet_export_paths",
        "online_packet_export_first_nonempty_issue_count",
        "online_packet_export_first_nonempty_issue_hash",
        "online_packet_export_first_nonempty_issue_index",
        "online_packet_export_first_nonempty_issue_path",
        "online_packet_export_nonempty_issue_count",
        "online_packet_export_scan_error_count",
        "selected_packet_index",
        "selected_packet_json",
        "selected_packet_selection_mode",
    ):
        payload.pop(key, None)
    return payload


def _payload_cache_producer_state_stream_native_canary_payload() -> dict[str, object]:
    return {
        "abi_field_count": 9,
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "changes_kernel_launch_args": False,
        "current_nonempty_packet_count": 2560,
        "current_wna16_arg_compatible": False,
        "error_count": 0,
        "expected_issue_candidate_count": 20160,
        "experts_per_layer": 8,
        "failures": [],
        "first_issue_expert": 0,
        "gpu_elapsed_ms": 12.189861,
        "issue_candidate_count": 20160,
        "issue_candidate_hash": "22488eda926276f7",
        "issue_generation_on_device": True,
        "last_issue_expert": 220,
        "layers": 40,
        "mode": "payload_cache_producer_transition_state_stream_native_canary",
        "native_graph_replay": True,
        "native_returncode": 0,
        "native_stub_invoked": True,
        "ok": True,
        "packet_count": 2560,
        "passed": True,
        "passed_to_kernel": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "persistent_state_on_device": True,
        "previous_nonempty_packet_count": 2520,
        "ready_credit": False,
        "ready_layer_count": 40,
        "requested_disable_vectorized_copy": False,
        "requested_graph_replay": True,
        "requested_experts_per_layer": 8,
        "requested_layers": 40,
        "requested_steps": 64,
        "requested_transition_topk_count": 8,
        "steps": 64,
        "transition_topk_count": 8,
        "uses_current_wna16_args": False,
        "vectorized_copy_requested": True,
        "vectorized_copy_used": True,
    }


def _payload_cache_producer_state_inprocess_native_canary_payload() -> dict[str, object]:
    return {
        "abi_field_count": 9,
        "abi_header": "microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h",
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "changes_kernel_launch_args": False,
        "current_nonempty_packet_count": 2560,
        "current_wna16_arg_compatible": False,
        "error_count": 0,
        "expected_issue_candidate_count": 20160,
        "experts_per_layer": 8,
        "failures": [],
        "first_issue_expert": 0,
        "gpu_elapsed_ms": 4.25,
        "inprocess_native_op": True,
        "issue_candidate_count": 20160,
        "issue_candidate_hash": "22488eda926276f7",
        "issue_generation_on_device": True,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "last_issue_expert": 220,
        "layers": 40,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "mode": "payload_cache_producer_transition_state_inprocess_native_canary",
        "native_graph_replay": True,
        "native_result_returncode": 0,
        "native_returncode": 0,
        "native_runtime": True,
        "native_shared_library": True,
        "native_stub_invoked": True,
        "ok": True,
        "packet_count": 2560,
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "persistent_state_on_device": True,
        "previous_nonempty_packet_count": 2520,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "ready_for_vllm_prelaunch_canary": True,
        "ready_layer_count": 40,
        "real_ready_credit_granted": False,
        "requested_disable_vectorized_copy": False,
        "requested_graph_replay": True,
        "requested_experts_per_layer": 8,
        "requested_layers": 40,
        "requested_steps": 64,
        "requested_transition_topk_count": 8,
        "shared_library": "microbench/premap_kernel_consumer/build/inprocess.so",
        "source": (
            "microbench/premap_kernel_consumer/"
            "premap_payload_cache_inprocess_native_producer_stub.hip"
        ),
        "steps": 64,
        "torch_graph_replay_visible": False,
        "transition_topk_count": 8,
        "uses_current_wna16_args": False,
        "vectorized_copy_requested": True,
        "vectorized_copy_used": True,
        "vllm_replay_visible": False,
    }


def _payload_cache_producer_state_inprocess_native_online_contract_payload() -> dict[str, object]:
    native = _payload_cache_producer_state_inprocess_native_canary_payload()
    return {
        "changes_kernel_launch_args": False,
        "contract_dimension_consistency_failures": [],
        "contract_dimension_sources": {
            "all_expert_sources_match": True,
            "all_layer_sources_match": True,
            "expert_source_count": 2,
            "expert_sources": {
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_experts_per_layer": 8,
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_current_count": 8,
            },
            "layer_source_count": 2,
            "layer_sources": {
                "decoder_layer_count": 40,
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_unique_layer_count": 40,
            },
            "optional_expert_source_keys": [
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_experts_per_layer"
            ],
            "optional_layer_source_keys": [
                "decoder_layer_count",
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_layers",
            ],
            "required_expert_source_keys": [
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_current_count"
            ],
            "required_layer_source_keys": [
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_unique_layer_count"
            ],
        },
        "contract_expected_issue_candidate_count": 20160,
        "contract_expected_packet_count": 2560,
        "contract_expected_previous_nonempty_packet_count": 2520,
        "contract_experts_per_layer": 8,
        "contract_layers": 40,
        "contract_steps": 64,
        "contract_transition_topk_count": 8,
        "current_wna16_arg_compatible": False,
        "embedded_online_stream_contract_issue_candidate_count": 20160,
        "embedded_online_stream_contract_passed": True,
        "embedded_online_stream_contract_present": True,
        "failures": [],
        "inprocess_native_op": True,
        "issue_generation_on_device": True,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "mode": "payload_cache_producer_state_inprocess_native_online_contract",
        "native": native,
        "native_graph_replay": True,
        "native_graph_replay_required": True,
        "native_inprocess_expected_issue_candidate_count": 20160,
        "native_inprocess_gpu_elapsed_ms": 4.25,
        "native_inprocess_issue_candidate_count": 20160,
        "native_inprocess_output_json": "reports/inprocess_native.json",
        "native_inprocess_packet_count": 2560,
        "native_inprocess_previous_nonempty_packet_count": 2520,
        "native_runtime": True,
        "native_shared_library": True,
        "native_stub_invoked": True,
        "ok": True,
        "online_observed_issue_candidate_count": 20160,
        "online_observed_packet_count": 2560,
        "online_observed_previous_nonempty_packet_count": 2520,
        "online_producer_update_count": 2560,
        "online_transition_state_owner": "producer",
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "performance_summary": "reports/performance_summary.json",
        "persistent_state_on_device": True,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "ready_for_vllm_prelaunch_native_op": True,
        "real_ready_credit_granted": False,
        "requested_output_token_count": 2048,
        "sample_count": 32,
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "source_kind": "derived_payload_cache_producer_state_stream_online_contract",
        "source_stream_online_contract_failures": [],
        "source_stream_online_contract_passed": True,
        "torch_graph_replay_visible": False,
        "uses_current_wna16_args": False,
        "vllm_replay_visible": False,
    }


def _payload_cache_producer_state_inprocess_native_session_canary_payload() -> dict[str, object]:
    return {
        "abi_field_count": 9,
        "abi_header": "microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h",
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "changes_kernel_launch_args": False,
        "create_returncode": 0,
        "current_count_device_ptr_passed": False,
        "current_count_host_scalar_passed": True,
        "current_count_source_kind": "host_scalar_uint32",
        "current_expert_ptr_passed": True,
        "current_expert_ptr_source": "torch_device_tensor",
        "current_expert_ptr_source_kind": "external_torch_device_tensor_smoke",
        "current_stream_on_device": True,
        "current_wna16_arg_compatible": False,
        "destroy_returncode": 0,
        "error_count": 0,
        "external_current_expert_ptr_source": True,
        "expected_issue_candidate_count": 20160,
        "expected_previous_nonempty_packet_count": 2520,
        "experts_per_layer": 8,
        "failures": [],
        "first_issue_expert": 0,
        "gpu_elapsed_ms": 4.25,
        "graph_visible": False,
        "inprocess_native_op": True,
        "issue_candidate_count": 20160,
        "issue_candidate_hash": "22488eda926276f7",
        "issue_generation_on_device": True,
        "last_issue_expert": 220,
        "layers": 40,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "mode": "payload_cache_producer_state_inprocess_native_session_canary",
        "native_graph_replay": False,
        "native_runtime": True,
        "native_shared_library": True,
        "native_stub_invoked": True,
        "native_update_returncodes": [0],
        "ok": True,
        "packet_stream_input": False,
        "packet_stream_state_override_count": 0,
        "packet_stream_state_restore_count": 0,
        "packet_stream_state_restore_returncodes": [],
        "packet_stream_state_restore_supported": True,
        "packet_count": 2560,
        "passed": True,
        "passed_to_kernel": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "persistent_state_on_device": True,
        "prelaunch_callable_native_session": True,
        "previous_nonempty_packet_count": 2520,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "ready_for_native_session_smoke": True,
        "ready_for_external_pointer_smoke": True,
        "ready_for_vllm_prelaunch_canary": False,
        "ready_update_count": 2560,
        "real_ready_credit_granted": False,
        "requested_disable_vectorized_copy": False,
        "requested_device_current_count": False,
        "requested_experts_per_layer": 8,
        "requested_layers": 40,
        "requested_steps": 64,
        "requested_transition_topk_count": 8,
        "session_handle_nonzero": True,
        "shared_library": "microbench/premap_kernel_consumer/build/session.so",
        "source": (
            "microbench/premap_kernel_consumer/"
            "premap_payload_cache_inprocess_native_producer_stub.hip"
        ),
        "steps": 64,
        "torch_graph_replay_visible": False,
        "transition_topk_count": 8,
        "uses_current_wna16_args": False,
        "vectorized_copy_requested": True,
        "vectorized_copy_used": True,
        "vllm_replay_visible": False,
    }


def _payload_cache_producer_state_inprocess_native_session_packet_stream_payload() -> dict[str, object]:
    return {
        **_payload_cache_producer_state_inprocess_native_session_canary_payload(),
        "current_expert_ptr_source": "packet_stream_torch_device_tensor",
        "current_expert_ptr_source_kind": "online_packet_stream_device_tensor_smoke",
        "external_current_expert_ptr_source": False,
        "ready_for_external_pointer_smoke": False,
        "packet_stream_input": True,
        "packet_stream_bin": "reports/shifted_packets.bin",
        "packet_stream_state_override_count": 31,
        "packet_stream_state_restore_count": 31,
        "packet_stream_state_restore_returncodes": [0],
        "steps": 32,
        "layers": 1,
        "experts_per_layer": 174,
        "transition_topk_count": 8,
        "packet_count": 32,
        "previous_nonempty_packet_count": 28,
        "expected_previous_nonempty_packet_count": 28,
        "issue_candidate_count": 224,
        "expected_issue_candidate_count": 224,
        "issue_candidate_hash": "0affb14eca44e751",
        "ready_update_count": 32,
        "requested_steps": 32,
        "requested_layers": 1,
        "requested_experts_per_layer": 174,
        "requested_transition_topk_count": 8,
        "vectorized_copy_used": False,
    }


def _payload_cache_producer_state_inprocess_native_session_online_contract_payload() -> dict[str, object]:
    native = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    return {
        "changes_kernel_launch_args": False,
        "contract_dimension_consistency_failures": [],
        "contract_dimension_sources": {
            "all_expert_sources_match": True,
            "all_layer_sources_match": True,
        },
        "contract_expected_issue_candidate_count": 20160,
        "contract_expected_packet_count": 2560,
        "contract_expected_previous_nonempty_packet_count": 2520,
        "contract_experts_per_layer": 8,
        "contract_layers": 40,
        "contract_steps": 64,
        "contract_transition_topk_count": 8,
        "current_expert_ptr_source": "torch_device_tensor",
        "current_expert_ptr_source_kind": "external_torch_device_tensor_smoke",
        "current_wna16_arg_compatible": False,
        "embedded_online_stream_contract_issue_candidate_count": 20160,
        "embedded_online_stream_contract_passed": True,
        "embedded_online_stream_contract_present": True,
        "external_current_expert_ptr_source": True,
        "failures": [],
        "graph_visible": False,
        "inprocess_native_op": True,
        "issue_generation_on_device": True,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "mode": "payload_cache_producer_state_inprocess_native_session_online_contract",
        "native": native,
        "native_graph_replay": False,
        "native_runtime": True,
        "native_session_expected_issue_candidate_count": 20160,
        "native_session_gpu_elapsed_ms": 4.25,
        "native_session_issue_candidate_count": 20160,
        "native_session_output_json": "reports/native_session.json",
        "native_session_packet_count": 2560,
        "native_session_previous_nonempty_packet_count": 2520,
        "native_shared_library": True,
        "native_stub_invoked": True,
        "ok": True,
        "online_observed_issue_candidate_count": 20160,
        "online_observed_packet_count": 2560,
        "online_observed_previous_nonempty_packet_count": 2520,
        "online_producer_update_count": 2560,
        "online_transition_state_owner": "producer",
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "performance_summary": "reports/stream_online_contract.json",
        "persistent_state_on_device": True,
        "prelaunch_callable_native_session": True,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "ready_for_native_session_smoke": True,
        "ready_for_external_pointer_smoke": True,
        "ready_for_vllm_prelaunch_canary": False,
        "real_ready_credit_granted": False,
        "requested_output_token_count": 2048,
        "sample_count": 32,
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "source_kind": "derived_payload_cache_producer_state_stream_online_contract",
        "source_stream_online_contract_failures": [],
        "source_stream_online_contract_passed": True,
        "torch_graph_replay_visible": False,
        "uses_current_wna16_args": False,
        "vllm_replay_visible": False,
    }


def _payload_cache_producer_state_packet_stream_native_canary_payload() -> dict[str, object]:
    native = {
        "abi_field_count": 9,
        "abi_name": "premap_payload_cache_producer_transition_state_abi_v1",
        "changes_kernel_launch_args": False,
        "current_nonempty_packet_count": 32,
        "current_wna16_arg_compatible": False,
        "error_count": 0,
        "expected_issue_candidate_count": 224,
        "expected_state_override_count": 31,
        "experts_per_layer": 174,
        "failures": [],
        "gpu_elapsed_ms": 13.548086,
        "issue_candidate_count": 224,
        "issue_candidate_hash": "83a1a8065edf2ddd",
        "issue_expert_mismatch_count": 0,
        "issue_generation_on_device": True,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "layers": 1,
        "max_experts_per_packet": 174,
        "max_num_experts": 256,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "mode": "payload_cache_producer_transition_state_packet_stream_native_canary",
        "native_graph_replay": True,
        "native_returncode": 0,
        "native_stub_invoked": True,
        "ok": True,
        "packet_count": 32,
        "packet_stream_input": True,
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "persistent_state_on_device": True,
        "previous_nonempty_packet_count": 28,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "real_ready_credit_granted": False,
        "state_mismatch_count": 0,
        "state_override_count": 31,
        "steps": 32,
        "transition_topk_count": 8,
        "uses_current_wna16_args": False,
    }
    return {
        "changes_kernel_launch_args": False,
        "comparisons": {
            "expected_issue_candidate_count_match": True,
            "issue_candidate_count_match": True,
            "issue_candidate_hash_match": True,
            "issue_expert_mismatch_count_zero": True,
            "packet_count_match": True,
            "previous_nonempty_packet_count_match": True,
            "state_mismatch_count_zero": True,
            "state_override_count_match": True,
        },
        "current_wna16_arg_compatible": False,
        "failures": [],
        "materialized": {
            "expected_issue_candidate_count": 224,
            "expected_issue_candidate_hash": "83a1a8065edf2ddd",
            "expected_previous_nonempty_packet_count": 28,
            "failures": [],
            "layer_count": 1,
            "max_experts_per_packet": 174,
            "max_num_experts": 256,
            "packet_count": 32,
            "passed": True,
            "state_override_count": 31,
            "transition_topk_count": 8,
        },
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "mode": "payload_cache_producer_state_packet_stream_native_canary",
        "native": native,
        "ok": True,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "real_ready_credit_granted": False,
        "uses_current_wna16_args": False,
    }


def _payload_cache_producer_state_packet_stream_native_canary_check_payload() -> dict[str, object]:
    return {
        "changes_kernel_launch_args": False,
        "expected_issue_candidate_count": 224,
        "expected_issue_candidate_hash": "83a1a8065edf2ddd",
        "failures": [],
        "issue_candidate_count": 224,
        "issue_candidate_hash": "83a1a8065edf2ddd",
        "issue_expert_mismatch_count": 0,
        "materialized_expected_issue_candidate_count": 224,
        "materialized_expected_issue_candidate_hash": "83a1a8065edf2ddd",
        "materialized_expected_previous_nonempty_packet_count": 28,
        "materialized_packet_count": 32,
        "materialized_state_override_count": 31,
        "min_issue_candidate_count": 1,
        "min_packet_count": 1,
        "mode": "premap_payload_cache_packet_stream_native_canary_check",
        "native_graph_replay": True,
        "native_runtime_blocked": None,
        "packet_count": 32,
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "payload_bytes": 0,
        "previous_nonempty_packet_count": 28,
        "ready_credit": False,
        "state_mismatch_count": 0,
        "state_override_count": 31,
        "uses_current_wna16_args": False,
    }


def _payload_cache_producer_state_stream_online_contract_payload() -> dict[str, object]:
    expected_issue_count = 20160
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_producer_state_stream_online_contract",
        "performance_summary": "reports/performance_summary.json",
        "native_stream_output_json": "reports/native_stream.json",
        "sample_count": 32,
        "requested_output_token_count": 2048,
        "online_transition_state_owner": "producer",
        "online_transition_native_packet_count": 40,
        "online_transition_native_packet_ready_count": 40,
        "online_transition_native_packet_last_current_count": 8,
        "online_transition_issue_previous_nonempty_count": 0,
        "online_transition_issue_descriptor_count": 0,
        "online_python_prelaunch_state_empty": True,
        "contract_steps": 64,
        "contract_layers": 40,
        "contract_experts_per_layer": 8,
        "contract_transition_topk_count": 8,
        "contract_expected_issue_candidate_count": expected_issue_count,
        "embedded_online_stream_contract_present": True,
        "embedded_online_stream_contract_passed": True,
        "embedded_online_stream_contract_failures": [],
        "embedded_online_stream_contract_expected_issue_candidate_count": (
            expected_issue_count
        ),
        "embedded_online_stream_contract_issue_candidate_count": expected_issue_count,
        "contract_dimension_sources": {
            "layer_sources": {
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_unique_layer_count": 40,
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_layers": 40,
            },
            "expert_sources": {
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_current_count": 8,
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_experts_per_layer": 8,
            },
            "required_layer_source_keys": [
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_unique_layer_count",
            ],
            "required_expert_source_keys": [
                "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_current_count",
            ],
            "optional_layer_source_keys": [
                "decoder_layer_count",
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_layers",
            ],
            "optional_expert_source_keys": [
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_experts_per_layer",
            ],
            "all_layer_sources_match": True,
            "all_expert_sources_match": True,
        },
        "contract_dimension_consistency_failures": [],
        "native_stream_issue_candidate_count": expected_issue_count,
        "native_stream_previous_nonempty_packet_count": 2520,
        "native_stream_packet_count": 2560,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "native_stream_vectorized_copy_used": True,
        "native_stream_persistent_state_on_device": True,
        "native_stream_issue_generation_on_device": True,
        "native_stream_gpu_elapsed_ms": 12.0,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "production_like_ab_ready": True,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_tpot": False,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
    }


def _payload_cache_online_inside_graph_producer_boundary_contract_payload() -> (
    dict[str, object]
):
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_online_inside_graph_producer_boundary_contract",
        "performance_summary": "reports/performance_summary.json",
        "embedded_graph_visible_contract_passed": True,
        "embedded_graph_visible_contract_enabled": True,
        "embedded_graph_visible_contract_present": True,
        "embedded_graph_visible_contract_capture_once_per_layer_suspected": False,
        "embedded_graph_visible_contract_replay_update_status": (
            "complete_replay_updates_observed"
        ),
        "embedded_inside_graph_boundary_contract_passed": True,
        "embedded_inside_graph_boundary_contract_failures": [],
        "contract_boundary": "online_inside_graph_tensor_producer",
        "transition_state_on_device": True,
        "issue_generation_on_device": True,
        "python_transition_skipped": True,
        "graph_observed_packet_count": 2560,
        "graph_expected_packet_count": 2560,
        "graph_observed_previous_nonempty_packet_count": 2520,
        "graph_expected_previous_nonempty_packet_count": 2520,
        "graph_observed_issue_candidate_count": 20160,
        "graph_expected_issue_candidate_count": 20160,
        "graph_last_issue_candidate_count": 8,
        "graph_last_issue_candidate_first_expert": 1,
        "graph_last_issue_candidate_last_expert": 7,
        "graph_issue_candidate_expert_sum": 123456,
        "native_runtime": False,
        "inprocess_native_op": False,
        "post_export_native_replay": False,
        "payload_bytes": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _payload_cache_online_native_producer_boundary_gap_payload() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_online_native_producer_boundary_gap_report",
        "native_graph_replay_json": "reports/native_graph_replay.json",
        "online_inside_graph_contract_json": "reports/online_capture_only.json",
        "native_graph_replay_passed": True,
        "native_persistent_state_on_device": True,
        "native_issue_generation_on_device": True,
        "native_packet_count": 8,
        "native_issue_candidate_count": 48,
        "native_expected_issue_candidate_count": 48,
        "online_graph_expected_packet_count": 8,
        "online_graph_expected_issue_candidate_count": 48,
        "online_tensor_producer_passed": False,
        "online_capture_once_per_layer_suspected": True,
        "online_replay_update_status": "capture_once_per_layer_no_replay_updates",
        "ready_for_inprocess_native_op_work": True,
        "ready_for_lab_runtime_gate": False,
        "runtime_passed": False,
        "lab_gate_passed": False,
        "next_required_boundary": "inprocess_vllm_replay_visible_native_producer_op",
        "payload_bytes": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def test_payload_cache_online_native_producer_boundary_gap_evidence_accepts_boundary_report():
    failures = _validate_payload_cache_online_native_producer_boundary_gap_evidence(
        _payload_cache_online_native_producer_boundary_gap_payload()
    )

    assert failures == []


def test_payload_cache_online_native_producer_boundary_gap_evidence_rejects_lab_gate_pass():
    payload = _payload_cache_online_native_producer_boundary_gap_payload()
    payload["ready_for_lab_runtime_gate"] = True
    payload["lab_gate_passed"] = True

    failures = _validate_payload_cache_online_native_producer_boundary_gap_evidence(
        payload
    )

    assert (
        "payload_cache_online_native_producer_boundary_gap_ready_for_lab_runtime_gate_mismatch"
        in failures
    )
    assert (
        "payload_cache_online_native_producer_boundary_gap_lab_gate_passed_mismatch"
        in failures
    )


def test_payload_cache_online_native_producer_boundary_gap_evidence_rejects_extra_runtime_positive_fields():
    payload = _payload_cache_online_native_producer_boundary_gap_payload()
    payload["kernel_arg_pass_allowed"] = True
    payload["kernel_arg_pass"] = True
    payload["payload_transfer_enabled"] = True

    failures = _validate_payload_cache_online_native_producer_boundary_gap_evidence(
        payload
    )

    assert (
        "payload_cache_online_native_producer_boundary_gap_kernel_arg_pass_allowed_unexpectedly_enabled"
        in failures
    )
    assert "payload_cache_online_native_producer_boundary_gap_kernel_arg_pass_mismatch" in failures
    assert (
        "payload_cache_online_native_producer_boundary_gap_payload_transfer_enabled_unexpectedly_enabled"
        in failures
    )


def test_payload_cache_online_native_producer_boundary_gap_evidence_rejects_scale_mismatch():
    payload = _payload_cache_online_native_producer_boundary_gap_payload()
    payload["online_graph_expected_packet_count"] = 2560
    payload["online_graph_expected_issue_candidate_count"] = 20160

    failures = _validate_payload_cache_online_native_producer_boundary_gap_evidence(
        payload
    )

    assert (
        "payload_cache_online_native_producer_boundary_gap_native_online_packet_count_mismatch"
        in failures
    )
    assert (
        "payload_cache_online_native_producer_boundary_gap_native_online_issue_candidate_count_mismatch"
        in failures
    )
    assert (
        "payload_cache_online_native_producer_boundary_gap_native_expected_online_issue_candidate_count_mismatch"
        in failures
    )


def test_payload_cache_online_native_producer_boundary_gap_evidence_rejects_missing_scale_fields():
    payload = _payload_cache_online_native_producer_boundary_gap_payload()
    payload.pop("native_packet_count")
    payload.pop("online_graph_expected_packet_count")
    payload.pop("online_graph_expected_issue_candidate_count")

    failures = _validate_payload_cache_online_native_producer_boundary_gap_evidence(
        payload
    )

    assert (
        "payload_cache_online_native_producer_boundary_gap_native_packet_count_invalid"
        in failures
    )
    assert (
        "payload_cache_online_native_producer_boundary_gap_online_graph_expected_packet_count_invalid"
        in failures
    )
    assert (
        "payload_cache_online_native_producer_boundary_gap_online_graph_expected_issue_candidate_count_invalid"
        in failures
    )


def _payload_cache_stream_producer_production_ab_bridge_payload() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_stream_producer_production_like_ab_report",
        "baseline_tpot_s": 0.0032532496713867185,
        "candidate_tpot_s": 0.003245981701171875,
        "candidate_overhead_ratio": -0.0022340646888455717,
        "max_overhead_ratio": 0.02,
        "online_contract_passed": True,
        "benchmark_is_current_wna16_fused_moe": True,
        "measures_tpot": True,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
        "payload_bytes": 0,
        "candidate_payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "candidate_kernel_arg_pass": False,
        "candidate_changes_kernel_launch_args": False,
        "online_contract_expected_issue_candidate_count": 20160,
        "native_stream_issue_candidate_count": 20160,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "native_stream_persistent_state_on_device": True,
        "native_stream_issue_generation_on_device": True,
    }


def _payload_cache_stream_producer_production_ab_bridge_check_payload() -> dict[str, object]:
    return {
        "passed": True,
        "failures": [],
        "mode": "premap_payload_cache_stream_producer_ab_bridge_check",
        "candidate_overhead_ratio": -0.0022340646888455717,
        "max_overhead_ratio": 0.02,
        "native_stream_issue_candidate_count": 20160,
        "online_contract_expected_issue_candidate_count": 20160,
        "payload_bytes": 0,
        "candidate_payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "candidate_kernel_arg_pass": False,
        "candidate_changes_kernel_launch_args": False,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "native_stream_persistent_state_on_device": True,
        "native_stream_issue_generation_on_device": True,
    }


def _payload_cache_manager_useful_work_ab_gate_payload() -> dict[str, object]:
    return {
        "artifact_kind": "premap_payload_cache_manager_useful_work_ab_gate",
        "mode": "payload_cache_manager_useful_work_ab_precondition",
        "passed": True,
        "ok": True,
        "failures": [],
        "manager_useful_work_ab_ready": True,
        "payload_runtime_ready": False,
        "performance_claim_ready": False,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "issued_payload_count_source": "legacy_missing",
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "issued_prefetch_count": 133,
        "used_fetch_count": 108,
        "unused_fetch_count": 25,
        "requested_issue_count": 224,
        "demand_count": 224,
        "demand_hit_count": 199,
        "demand_hit_rate": 199 / 224,
        "used_per_issued_fetch": 108 / 133,
        "ready_late_miss_rate": 25 / 224,
        "queue_batch_size": 8,
        "producer_expected_packet_count": 160,
        "consumer_requested_payload_bytes": 64,
        "payload_runtime_block_reason": "payload_transfer_disabled",
        "next_stage": "production_like_payload_cache_manager_ab_harness",
        "useful_work_readiness_json": (
            "outputs/reports/premap_payload_cache/"
            "payload_cache_useful_work_readiness_gate.json"
        ),
        "issue_stream_executor_json": (
            "outputs/reports/premap_kernel_consumer/"
            "premap_payload_cache_issue_stream_executor_token_provenance_"
            "smoke_v3_lead32_shifted_accounting_v1.json"
        ),
    }


def _payload_cache_manager_production_ab_preflight_payload(
    *,
    manager_gate_json: str,
) -> dict[str, object]:
    return {
        "artifact_kind": "premap_payload_cache_manager_production_ab_preflight",
        "artifact_scope": "preflight_smoke_only",
        "mode": "payload_cache_manager_production_like_ab_preflight",
        "passed": True,
        "ok": True,
        "failures": [],
        "production_like_manager_ab_harness_ready": True,
        "payload_runtime_ready": False,
        "performance_claim_ready": False,
        "final_production_result_ready": False,
        "consumes_tpot_summary_for_envelope": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "candidate_manager_counter_enabled": True,
        "candidate_manager_mode": "ready_time",
        "candidate_producer_contract_passed": True,
        "manager_accounting_source": "payload_cache_manager_useful_work_ab_gate",
        "manager_gate_json": manager_gate_json,
        "manager_issued_prefetch_count": 133,
        "manager_used_fetch_count": 108,
        "manager_unused_fetch_count": 25,
        "manager_demand_count": 224,
        "manager_demand_hit_count": 199,
        "manager_demand_hit_rate": 199 / 224,
        "manager_used_per_issued_fetch": 108 / 133,
        "baseline_summary": "reports/baseline/performance_summary.json",
        "candidate_summary": "reports/candidate/performance_summary.json",
        "baseline_tpot_s": 0.008248904412109376,
        "candidate_tpot_s": 0.008297677388671874,
        "candidate_envelope_overhead_ratio": 0.005912661139690245,
        "candidate_envelope_overhead_percent": 0.5912661139690245,
        "max_envelope_overhead_ratio": 0.05,
        "sample_count": 8,
        "requested_output_token_count": 512,
        "next_stage": "run_production_like_payload_cache_manager_ab",
    }


def _payload_cache_shifted_issue_runtime_shadow_gate_payload() -> dict[str, object]:
    return {
        "artifact_kind": "premap_payload_cache_shifted_issue_runtime_shadow_gate",
        "boundary": (
            "online shifted-issue runtime shadow gate only; no payload movement, "
            "ready credit, kernel arg pass, or endpoint latency"
        ),
        "changes_kernel_launch_args": False,
        "clamped_issue_count": 0,
        "duplicate_demand_key_count": 0,
        "duplicate_issue_key_count": 0,
        "empty_issue_exempt_count": 4,
        "failures": [],
        "full_fetch_runtime_allowed": False,
        "invalid_packet_count": 0,
        "issue_hash_count": 28,
        "issue_hash_unique_count": 27,
        "issue_lead_tokens": 1,
        "kernel_arg_pass_allowed": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "packet_count": 32,
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "performance_summary": "reports/shifted_issue/performance_summary.json",
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "real_ready_credit_granted": False,
        "safe_packet_count": 32,
        "scan_error_count": 0,
        "schedulable_packet_count": 28,
        "total_issue_candidates": 224,
        "unique_demand_key_count": 28,
        "unique_issue_key_count": 28,
        "unsafe_packet_count": 0,
        "uses_current_wna16_args": False,
    }


def _payload_cache_packet_export_manifest_payload() -> dict[str, object]:
    first_path = "reports/packet_0001.json"
    return {
        "allow_config_token_source": False,
        "allow_empty_config_packets": True,
        "artifact_kind": "premap_payload_cache_packet_export_manifest",
        "changes_kernel_launch_args": False,
        "checked_nonempty_packet_count": 28,
        "checked_packet_count": 32,
        "checked_packet_export_first_nonempty_issue_count": 8,
        "checked_packet_export_first_nonempty_issue_hash": "f3f1208c1026d557",
        "checked_packet_export_first_nonempty_issue_index": 1,
        "checked_packet_export_first_nonempty_issue_path": first_path,
        "failures": [],
        "kernel_arg_pass_allowed": False,
        "manifest_name": "premap_payload_cache_packet_export_manifest_v1",
        "manifest_source": "runtime_shadow_performance_summary",
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "next_runtime_stage": "payload_cache_issue_stream_executor",
        "ok": True,
        "online_configured_export_count": 32,
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "online_nonempty_issue_count": 28,
        "online_packet_export_count": 32,
        "online_packet_export_first_nonempty_issue_count": 8,
        "online_packet_export_first_nonempty_issue_hash": "f3f1208c1026d557",
        "online_packet_export_first_nonempty_issue_index": 1,
        "online_packet_export_first_nonempty_issue_path": first_path,
        "online_packet_export_nonempty_issue_count": 28,
        "online_packet_export_paths": [
            f"reports/packet_{index:04d}.json" for index in range(32)
        ],
        "online_packet_export_scan_error_count": 0,
        "online_performance_summary": "reports/shifted_issue/performance_summary.json",
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "ready": True,
        "ready_before_demand_credit": False,
        "ready_credit": False,
        "real_ready_credit_granted": False,
        "shifted_issue_clamped_issue_count": 0,
        "shifted_issue_duplicate_demand_key_count": 0,
        "shifted_issue_duplicate_issue_key_count": 0,
        "shifted_issue_empty_issue_exempt_count": 4,
        "shifted_issue_enabled": True,
        "shifted_issue_invalid_packet_count": 0,
        "shifted_issue_issue_hash_count": 28,
        "shifted_issue_issue_hash_unique_count": 27,
        "shifted_issue_lead_tokens": 1,
        "shifted_issue_packet_count": 32,
        "shifted_issue_runtime_shadow_enabled": True,
        "shifted_issue_runtime_shadow_required": True,
        "shifted_issue_safe_packet_count": 32,
        "shifted_issue_scan_error_count": 0,
        "shifted_issue_schedulable_packet_count": 28,
        "shifted_issue_total_issue_candidates": 224,
        "shifted_issue_unique_demand_key_count": 28,
        "shifted_issue_unique_issue_key_count": 28,
        "shifted_issue_unsafe_packet_count": 0,
        "summary_packet_export_first_nonempty_issue_count": 8,
        "summary_packet_export_first_nonempty_issue_hash": "f3f1208c1026d557",
        "summary_packet_export_first_nonempty_issue_index": 1,
        "summary_packet_export_first_nonempty_issue_path": first_path,
        "uses_current_wna16_args": False,
    }


def _kernel_launch_context_metrics(
    *,
    prefix: str,
    row_count: int,
    device_ordinal: int = 0,
    include_all_handle_fields_read: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": (
            "premap_future_kernel_native_consumer_kernel_launch_context_abi_v1"
        ),
        f"{prefix}_mode": (
            "readonly_future_kernel_native_consumer_kernel_launch_context_abi"
        ),
        f"{prefix}_source": (
            "premap_future_kernel_native_consumer_kernel_launch_descriptor_abi_v1"
        ),
        f"{prefix}_version": 1,
        f"{prefix}_field_read_path": (
            "kernel_launch_context_to_kernel_launch_descriptor_to_"
            "launch_envelope_args_ptr_to_launch_envelope_args_to_"
            "entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_"
            "program_view_rows"
        ),
        f"{prefix}_packet_chain_depth": 10,
        f"{prefix}_error_count": 0,
        f"{prefix}_struct_size": 64,
        f"{prefix}_struct_align": 8,
        f"{prefix}_launch_descriptor_struct_size": 80,
        f"{prefix}_summary_struct_size": 104,
        f"{prefix}_pointer_size": 8,
        f"{prefix}_device_ordinal": device_ordinal,
        f"{prefix}_stream_domain": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_summary_row_count": row_count,
        f"{prefix}_summary_row_ok_count": row_count,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
        f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": 15,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_struct_size": 104,
        f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
        f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
        f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
    }
    if include_all_handle_fields_read:
        payload[f"{prefix}_all_handle_fields_read"] = True
        payload[f"{prefix}_row_hash_accumulator"] = "c4b51a0fa5ba88c4"
        payload[f"{prefix}_field_read_hash_accumulator"] = "c2e4ae7fa9bc3227"
        payload[f"{prefix}_row_metadata_hash_accumulator"] = "1a11b42afa9e8576"
    return payload


def _invocation_metrics(
    *,
    prefix: str,
    row_count: int,
    device_ordinal: int = 0,
    include_all_handle_fields_read: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": "premap_future_kernel_native_consumer_invocation_abi_v1",
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_invocation_abi",
        f"{prefix}_source": (
            "premap_future_kernel_native_consumer_kernel_launch_context_abi_v1"
        ),
        f"{prefix}_version": 1,
        f"{prefix}_field_read_path": (
            "invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_"
            "launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_"
            "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
        ),
        f"{prefix}_packet_chain_depth": 11,
        f"{prefix}_error_count": 0,
        f"{prefix}_struct_size": 72,
        f"{prefix}_struct_align": 8,
        f"{prefix}_context_struct_size": 64,
        f"{prefix}_summary_struct_size": 104,
        f"{prefix}_pointer_size": 8,
        f"{prefix}_id": 1,
        f"{prefix}_device_ordinal": device_ordinal,
        f"{prefix}_stream_domain": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_summary_row_count": row_count,
        f"{prefix}_summary_row_ok_count": row_count,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
        f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": 15,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
        f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
        f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
    }
    if include_all_handle_fields_read:
        payload[f"{prefix}_all_handle_fields_read"] = True
        payload[f"{prefix}_row_hash_accumulator"] = "c4b51a0fa5ba88c4"
        payload[f"{prefix}_field_read_hash_accumulator"] = "c2e4ae7fa9bc3227"
        payload[f"{prefix}_row_metadata_hash_accumulator"] = "1a11b42afa9e8576"
    return payload


def _invocation_entry_metrics(
    *,
    prefix: str,
    row_count: int,
    include_all_handle_fields_read: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": (
            "premap_future_kernel_native_consumer_invocation_entry_abi_v1"
        ),
        f"{prefix}_mode": (
            "readonly_future_kernel_native_consumer_invocation_entry_abi"
        ),
        f"{prefix}_source": (
            "premap_future_kernel_native_consumer_invocation_abi_v1_by_value"
        ),
        f"{prefix}_field_read_path": (
            "by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_"
            "launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_"
            "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
        ),
        f"{prefix}_packet_chain_depth": 11,
        f"{prefix}_error_count": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_summary_row_count": row_count,
        f"{prefix}_summary_row_ok_count": row_count,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
        f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": 15,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
        f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
        f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
    }
    if include_all_handle_fields_read:
        payload[f"{prefix}_all_handle_fields_read"] = True
        payload[f"{prefix}_row_hash_accumulator"] = "c4b51a0fa5ba88c4"
        payload[f"{prefix}_field_read_hash_accumulator"] = "c2e4ae7fa9bc3227"
        payload[f"{prefix}_row_metadata_hash_accumulator"] = "1a11b42afa9e8576"
    return payload


def _endpoint_metrics(
    *,
    prefix: str,
    row_count: int,
    include_all_handle_fields_read: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": "premap_future_kernel_native_consumer_endpoint_abi_v1",
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_endpoint_abi",
        f"{prefix}_source": (
            "premap_future_kernel_native_consumer_invocation_entry_abi_v1"
        ),
        f"{prefix}_field_read_path": (
            "endpoint_to_by_value_invocation_to_kernel_launch_context_to_"
            "kernel_launch_descriptor_to_launch_envelope_args_ptr_to_"
            "launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_"
            "kernel_arg_packet_to_program_view_rows"
        ),
        f"{prefix}_packet_chain_depth": 12,
        f"{prefix}_error_count": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_summary_row_count": row_count,
        f"{prefix}_summary_row_ok_count": row_count,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
        f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": 15,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
        f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
        f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
    }
    if include_all_handle_fields_read:
        payload[f"{prefix}_all_handle_fields_read"] = True
        payload[f"{prefix}_row_hash_accumulator"] = "c4b51a0fa5ba88c4"
        payload[f"{prefix}_field_read_hash_accumulator"] = "c2e4ae7fa9bc3227"
        payload[f"{prefix}_row_metadata_hash_accumulator"] = "1a11b42afa9e8576"
    return payload


def _endpoint_ptr_metrics(
    *,
    prefix: str,
    row_count: int,
    include_all_handle_fields_read: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": (
            "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
        ),
        f"{prefix}_mode": "readonly_future_kernel_native_consumer_endpoint_ptr_abi",
        f"{prefix}_source": "premap_future_kernel_native_consumer_endpoint_abi_v1",
        f"{prefix}_field_read_path": (
            "endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_"
            "kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_"
            "entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
        ),
        f"{prefix}_packet_chain_depth": 13,
        f"{prefix}_error_count": 0,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_summary_row_count": row_count,
        f"{prefix}_summary_row_ok_count": row_count,
        f"{prefix}_summary_descriptor_ptr_read_row_ok_count": row_count,
        f"{prefix}_summary_packed_weight_descriptor_read_row_ok_count": row_count,
        f"{prefix}_summary_scale_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_aux_metadata_handle_read_row_ok_count": row_count,
        f"{prefix}_summary_expert_id_read_row_ok_count": row_count,
        f"{prefix}_summary_address_key_hash_read_row_ok_count": row_count,
        f"{prefix}_summary_row_metadata_read_row_ok_count": row_count,
        f"{prefix}_summary_error_count": 0,
        f"{prefix}_summary_field_mask": 15,
        f"{prefix}_summary_packet_valid": 1,
        f"{prefix}_summary_row_hash_accumulator": "c4b51a0fa5ba88c4",
        f"{prefix}_summary_field_read_hash_accumulator": "c2e4ae7fa9bc3227",
        f"{prefix}_summary_row_metadata_hash_accumulator": "1a11b42afa9e8576",
    }
    if include_all_handle_fields_read:
        payload[f"{prefix}_all_handle_fields_read"] = True
        payload[f"{prefix}_row_hash_accumulator"] = "c4b51a0fa5ba88c4"
        payload[f"{prefix}_field_read_hash_accumulator"] = "c2e4ae7fa9bc3227"
        payload[f"{prefix}_row_metadata_hash_accumulator"] = "1a11b42afa9e8576"
    return payload


def _standalone_arg_slot_multiprogram_canary_payload(
    *,
    mirror_field: str = "scale_metadata_handle",
) -> dict[str, object]:
    row_count = 520
    block_x = 256
    grid_x = 3
    full_program_count = 2
    last_program_active_rows = 8
    inactive_lane_count = 248
    program_iteration_hash = _program_iteration_hash(
        grid_x=grid_x,
        block_x=block_x,
        row_offset=0,
        row_limit=row_count,
        last_program_active_rows=last_program_active_rows,
        inactive_lane_count=inactive_lane_count,
    )
    payload = _standalone_arg_slot_canary_payload(mirror_field=mirror_field)
    payload.update(
        {
            "row_count": row_count,
            "row_ok_count": row_count,
            "hash_accumulator": "a0725e89da1555b8",
            "future_kernel_native_consumer_row_count": row_count,
            "future_kernel_native_consumer_row_ok_count": row_count,
            "future_kernel_native_consumer_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
            "future_kernel_native_launch_consumer_row_count": row_count,
            "future_kernel_native_launch_consumer_row_ok_count": row_count,
            "future_kernel_native_launch_consumer_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
            "future_kernel_native_dispatch_consumer_row_count": row_count,
            "future_kernel_native_dispatch_consumer_row_ok_count": row_count,
            "future_kernel_native_dispatch_consumer_active_rows": row_count,
            "future_kernel_native_dispatch_consumer_row_limit": row_count,
            "future_kernel_native_dispatch_consumer_grid_x": grid_x,
            "future_kernel_native_dispatch_consumer_block_x": block_x,
            "future_kernel_native_dispatch_consumer_launch_threads": grid_x * block_x,
            "future_kernel_native_dispatch_consumer_program_count": grid_x,
            "future_kernel_native_dispatch_consumer_full_program_count": (
                full_program_count
            ),
            "future_kernel_native_dispatch_consumer_last_program_active_rows": (
                last_program_active_rows
            ),
            "future_kernel_native_dispatch_consumer_inactive_lane_count": (
                inactive_lane_count
            ),
            "future_kernel_native_dispatch_consumer_rows_per_program": block_x,
            "future_kernel_native_dispatch_consumer_row_offset": 0,
            "future_kernel_native_dispatch_consumer_last_program_row_offset": 512,
            "future_kernel_native_dispatch_consumer_launch_geometry_checked": True,
            "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
            "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
            "future_kernel_native_dispatch_consumer_program_iteration_checked": True,
            "future_kernel_native_dispatch_consumer_program_iteration_hash": (
                f"{program_iteration_hash:x}"
            ),
            "future_kernel_native_dispatch_consumer_row_assignment_formula": (
                "row_offset + program_id * rows_per_program + lane_id"
            ),
            "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
            "future_kernel_native_dispatch_ptr_consumer_row_count": row_count,
            "future_kernel_native_dispatch_ptr_consumer_row_ok_count": row_count,
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
            "future_kernel_native_arg_slot_consumer_row_count": row_count,
            "future_kernel_native_arg_slot_consumer_row_ok_count": row_count,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator": (
                "d35c1"
            ),
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator": (
                "d35c2"
            ),
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator": (
                "d35c3"
            ),
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count": 0,
            "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator": (
                "d35c4"
            ),
            "future_kernel_native_consumer_view_row_count": row_count,
            "future_kernel_native_consumer_view_row_ok_count": row_count,
            "future_kernel_native_consumer_view_row_offset": 0,
            "future_kernel_native_consumer_view_row_limit": row_count,
            "future_kernel_native_consumer_view_rows_per_program": block_x,
            "future_kernel_native_consumer_view_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
            "future_kernel_native_consumer_view_descriptor_ptr_read_row_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_descriptor_ptr_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_packed_weight_descriptor_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_aux_metadata_handle_read_row_count": (
                row_count
            ),
            "future_kernel_native_consumer_view_aux_metadata_handle_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_program_view_checked": True,
            "future_kernel_native_consumer_program_view_source": (
                "premap_future_kernel_native_consumer_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_row_count": row_count,
            "future_kernel_native_consumer_program_view_row_ok_count": row_count,
            "future_kernel_native_consumer_program_view_error_count": 0,
            "future_kernel_native_consumer_program_view_hash_accumulator": (
                "bbaa998877665544"
            ),
            "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator": (
                "12201358096b98ac"
            ),
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
            "future_kernel_native_consumer_program_view_first_program_row_offset": 0,
            "future_kernel_native_consumer_program_view_last_program_row_offset": 512,
            "future_kernel_native_consumer_program_view_program_iteration_hash": (
                f"{program_iteration_hash:x}"
            ),
            "future_kernel_native_consumer_program_view_row_assignment_formula": (
                "program_id * rows_per_program + lane_id + row_offset"
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
            "future_kernel_native_consumer_program_view_ptr_checked": True,
            "future_kernel_native_consumer_program_view_ptr_source": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_row_count": row_count,
            "future_kernel_native_consumer_program_view_ptr_row_ok_count": row_count,
            "future_kernel_native_consumer_program_view_ptr_error_count": 0,
            "future_kernel_native_consumer_program_view_ptr_hash_accumulator": (
                "c053998877665544"
            ),
            "future_kernel_native_consumer_program_view_ptr_field_mask": 15,
            "future_kernel_native_consumer_program_view_ptr_required_field_mask": 7,
            "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": (
                False
            ),
            "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": (
                False
            ),
            "future_kernel_native_consumer_kernel_entry_args_checked": True,
            "future_kernel_native_consumer_kernel_entry_args_field_read_path": (
                "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
            ),
            "future_kernel_native_consumer_kernel_entry_args_packet_chain_depth": 5,
            "future_kernel_native_consumer_kernel_entry_args_summary_row_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_descriptor_ptr_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_packed_weight_descriptor_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_aux_metadata_handle_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count": (
                row_count
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_error_count": 0,
            "future_kernel_native_consumer_kernel_entry_args_summary_field_mask": 15,
            "future_kernel_native_consumer_kernel_entry_args_summary_row_hash_accumulator": (
                "c4b51a0fa5ba88c4"
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_field_read_hash_accumulator": (
                "c2e4ae7fa9bc3227"
            ),
            "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator": (
                "1a11b42afa9e8576"
            ),
            "future_kernel_native_consumer_kernel_entry_args_payload_bytes": 0,
            "future_kernel_native_consumer_kernel_entry_args_passed_to_kernel": False,
            "future_kernel_native_consumer_kernel_entry_args_changes_kernel_launch_args": (
                False
            ),
            "future_kernel_native_consumer_kernel_entry_args_current_wna16_arg_compatible": (
                False
            ),
            "future_kernel_native_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation": (
                False
            ),
        }
    )
    payload.update(
        _kernel_launch_context_metrics(
            prefix="future_kernel_native_consumer_kernel_launch_context",
            row_count=row_count,
        )
    )
    payload.update(
        _invocation_metrics(
            prefix="future_kernel_native_consumer_invocation",
            row_count=row_count,
        )
    )
    payload.update(_wna16_adjacent_typed_slot_stub_metrics(row_count))
    return payload


def _online_merged_arg_slot_multiprogram_input_payload() -> dict[str, object]:
    row_count = 520
    source_count = 32
    source_rows = [17] * 8 + [16] * 24
    row_spans = []
    source_contexts = []
    cursor = 0
    for idx, span_rows in enumerate(source_rows):
        row_spans.append(
            {
                "source_index": idx,
                "path": f"reports/online_input_{idx:04d}.json",
                "row_start": cursor,
                "row_count": span_rows,
                "row_end": cursor + span_rows,
                "source_table_object_hash": f"table-{idx}",
                "source_schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            }
        )
        source_contexts.append(
            {
                "source_index": idx,
                "export_index": idx,
                "layer_id": idx % 40,
                "request_id": f"req-{idx}",
                "sequence_id": "seq0",
                "token_index": -1,
                "row_count": span_rows,
            }
        )
        cursor += span_rows
    assert cursor == row_count
    return {
        "descriptor_ptr": [1000 + idx for idx in range(row_count)],
        "packed_weight_descriptor": [2000 + idx for idx in range(row_count)],
        "scale_metadata_handle": [3000 + idx for idx in range(row_count)],
        "aux_metadata_handle": [4000 + idx for idx in range(row_count)],
        "expert_id": [idx % 8 for idx in range(row_count)],
        "address_key_hash": [5000 + idx for idx in range(row_count)],
        "_meta": {
            "schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            "row_count": row_count,
            "column_count": 4,
            "row_order_hash": "row-order-hash",
            "ordered_row_hash": "ordered-row-hash",
            "table_object_hash": "merged-table-object-hash",
            "payload_bytes": 0,
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "_merge_context": {
            "source": "merged_vllm_prelaunch_typed_consumer_inputs",
            "source_count": source_count,
            "row_count": row_count,
            "row_spans": row_spans,
            "source_contexts": source_contexts,
            "block_threads": 256,
            "expected_program_count": 3,
            "payload_bytes": 0,
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "not_a_single_vllm_launch_table": True,
        },
    }


def _wna16_side_arg_slot_multiprogram_input_payload() -> dict[str, object]:
    payload = _online_merged_arg_slot_multiprogram_input_payload()
    merge_context = payload["_merge_context"]
    row_spans = merge_context["row_spans"]
    source_contexts = merge_context["source_contexts"]
    row_count = merge_context["row_count"]
    for idx in range(len(source_contexts), 128):
        row_spans.append(
            {
                "source_index": idx,
                "path": f"reports/wna16_extra_input_{idx:04d}.json",
                "row_start": row_count,
                "row_count": 0,
                "row_end": row_count,
                "source_table_object_hash": f"table-{idx}",
                "source_schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
            }
        )
        source_contexts.append(
            {
                "source_index": idx,
                "export_index": idx,
                "layer_id": idx % 40,
                "request_id": f"req-extra-{idx}",
                "sequence_id": "seq0",
                "token_index": -1,
                "row_count": 0,
            }
        )
    merge_context["source_count"] = 128
    return payload


def _online_merged_arg_slot_multiprogram_canary_payload(
    input_path: str,
    *,
    mirror_field: str = "scale_metadata_handle",
) -> dict[str, object]:
    payload = _standalone_arg_slot_multiprogram_canary_payload(
        mirror_field=mirror_field
    )
    payload["input_json"] = input_path
    payload["input_source"] = "binary_prefix"
    return payload


def test_source_context_identity_uses_opaque_sequence_and_table_hash(tmp_path: Path):
    payload = _online_merged_arg_slot_multiprogram_input_payload()
    child_path = tmp_path / "child.json"
    parent_path = tmp_path / "parent.json"
    child_path.write_text(json.dumps(payload), encoding="utf-8")
    parent_path.write_text(json.dumps(payload), encoding="utf-8")

    child = _source_context_identities_from_merged_output(
        {"merged_output_json": str(child_path)},
        root=tmp_path,
    )
    parent = _source_context_identities_from_merged_output(
        {"merged_output_json": str(parent_path)},
        root=tmp_path,
    )
    subset, missing_count = _source_identity_subset(child, parent)

    assert len(child) == 32
    assert subset is True
    assert missing_count == 0
    assert "seq0" in child[0]
    assert "table-0" in child[0]
    assert PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH in child[0]
    assert child[0].startswith("[")


def test_source_context_identity_requires_sequence_id(tmp_path: Path):
    payload = _online_merged_arg_slot_multiprogram_input_payload()
    payload["_merge_context"]["source_contexts"][0].pop("sequence_id")
    path = tmp_path / "missing_sequence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    identities = _source_context_identities_from_merged_output(
        {"merged_output_json": str(path)},
        root=tmp_path,
    )

    assert len(identities) == 31


def test_source_context_identity_rejects_same_context_with_different_table_hash(
    tmp_path: Path,
):
    child_payload = _online_merged_arg_slot_multiprogram_input_payload()
    parent_payload = _online_merged_arg_slot_multiprogram_input_payload()
    parent_payload["_merge_context"]["row_spans"][0][
        "source_table_object_hash"
    ] = "different-table"
    child_path = tmp_path / "child.json"
    parent_path = tmp_path / "parent.json"
    child_path.write_text(json.dumps(child_payload), encoding="utf-8")
    parent_path.write_text(json.dumps(parent_payload), encoding="utf-8")

    child = _source_context_identities_from_merged_output(
        {"merged_output_json": str(child_path)},
        root=tmp_path,
    )
    parent = _source_context_identities_from_merged_output(
        {"merged_output_json": str(parent_path)},
        root=tmp_path,
    )
    subset, missing_count = _source_identity_subset(child, parent)

    assert len(child) == 32
    assert len(parent) == 32
    assert subset is False
    assert missing_count == 1


def _future_wna16_single_field_handoff_all_fields_summary_payload(
    *,
    row_count: int = 520,
    selected_source_count: int = 128,
) -> dict[str, object]:
    field_specs = {
        "descriptor_ptr": (1, 1, "c973e1eb866b06e8"),
        "packed_weight_descriptor": (2, 2, "a42c4f17c82346d1"),
        "scale_metadata_handle": (3, 4, "94c3d701dd5a27b3"),
        "aux_metadata_handle": (4, 8, "c069d5202855935e"),
    }
    fields: dict[str, object] = {}
    for field_name, (field_kind, field_mask, hash_accumulator) in field_specs.items():
        fields[field_name] = {
            "artifact": (
                "reports/online_merged_future_wna16_single_field_handoff_"
                f"{field_name}_128strict_preflight_runner.json"
            ),
            "passed": True,
            "selected_source_count": selected_source_count,
            "merged_row_count": row_count,
            "dispatch_active_rows": row_count,
            "abi_name": "premap_future_wna16_single_field_handoff_canary_v1",
            "mode": "readonly_future_wna16_single_field_handoff_canary",
            "source": "premap_future_wna16_kernel_side_consumer_execution_v1",
            "field_read_path": (
                "future_wna16_single_field_handoff_to_"
                "future_wna16_kernel_side_execution_to_"
                "accepted_typed_slot_to_program_view_rows"
            ),
            "field_name": field_name,
            "field_kind": field_kind,
            "field_mask": field_mask,
            "row_count": row_count,
            "row_ok_count": row_count,
            "error_count": 0,
            "hash_accumulator": hash_accumulator,
            "payload_bytes": 0,
            "live_enabled": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "requires_wna16_arg_reinterpretation": False,
            "explicit_typed_abi_slot": True,
            "reuses_current_wna16_arg_slot": False,
        }
    return {
        "summary_name": "future_wna16_single_field_handoff_all_fields_128strict",
        "passed": True,
        "failures": [],
        "field_count": len(field_specs),
        "fields": fields,
        "safety_contract": {
            "payload_bytes": 0,
            "live_enabled": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "requires_wna16_arg_reinterpretation": False,
            "explicit_typed_abi_slot": True,
            "reuses_current_wna16_arg_slot": False,
        },
    }


def _future_wna16_typed_slot_fourth_field_handoff_canary_payload(
    *,
    row_count: int = 520,
    source_count: int = 128,
) -> dict[str, object]:
    return {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
        ),
        "schema_version": 1,
        "passed": True,
        "failures": [],
        "device": 1,
        "source_count": source_count,
        "max_inputs": source_count,
        "previous_field_input_json_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "first_field_name": "scale_metadata_handle",
        "second_field_name": "aux_metadata_handle",
        "third_field_name": "packed_weight_descriptor",
        "fourth_field_name": "descriptor_ptr",
        "fourth_field_kind": 1,
        "fourth_field_mask": 1,
        "previous_field_gate_ready": True,
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
        "fourth_field_handoff_block_reason": "fourth_field_handoff_live_disabled",
        "fourth_field_handoff_live_enabled": False,
        "fourth_field_handoff_field_read_row_ok_count": row_count,
        "fourth_field_handoff_field_read_hash": "6e08db27babecb6a",
        "fourth_field_handoff_canary_runner_hash": "ba2e219a8ff9ccfe",
        "fourth_field_handoff_canary_runner_row_count": row_count,
        "fourth_field_handoff_canary_runner_row_ok_count": row_count,
        "fourth_field_handoff_canary_native_requested": True,
        "fourth_field_handoff_canary_native_executed": True,
        "fourth_field_handoff_canary_native_passed": True,
        "third_field_read_hash": "c5ca7b791f2fef98",
        "third_field_native_hash": "ca4ed3ab740d3ae6",
        "fourth_field_underlying_json": (
            "/home/husrcf/Code/ProtBind/MTP/outputs/reports/"
            "premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_"
            "fourth_field_handoff_canary/fourth_field_native_canary_runner.json"
        ),
        "fourth_field_underlying_sha256": "1" * 64,
        "payloadless_execution_json": (
            "/home/husrcf/Code/ProtBind/MTP/outputs/reports/"
            "premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_"
            "payloadless_execution_v1_native_run.json"
        ),
        "payloadless_execution_sha256": "2" * 64,
        "previous_field_json": (
            "/home/husrcf/Code/ProtBind/MTP/outputs/reports/"
            "premap_kernel_consumer/future_wna16_typed_slot_kernel_variant_"
            "third_field_handoff_canary_v1.json"
        ),
        "previous_field_sha256": "3" * 64,
        "payload_bytes": 0,
        "expected_payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
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
        "next_runtime_stage": (
            "promote_future_wna16_typed_slot_all_four_field_handoff_gate_to_lab_preflight"
        ),
    }


def _future_wna16_all_four_field_consumer_payload(
    *,
    row_count: int = 520,
    source_count: int = 128,
    fourth_field_json: str = "reports/default_gate_future_wna16_typed_slot_fourth_field_handoff_canary.json",
    fourth_field_sha256: str = "7" * 64,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_all_four_field_consumer",
        "schema_version": 1,
        "passed": True,
        "failures": [],
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "all_four_field_consumer_name": (
            "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
        ),
        "all_four_field_consumer_mode": (
            "readonly_future_wna16_typed_slot_all_four_field_consumer"
        ),
        "all_four_field_consumer_source": (
            "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
        ),
        "source_count": source_count,
        "input_json_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "selected_input_json_count": source_count,
        "selected_input_manifest_sha256": "4" * 64,
        "post_native_input_manifest_sha256": "4" * 64,
        "fourth_field_json": fourth_field_json,
        "fourth_field_sha256": fourth_field_sha256,
        "native_consumer_json": "reports/all_four_field_native_runner.json",
        "native_consumer_sha256": "8" * 64,
        "merged_input_json": "reports/all_four_field_merged_input.json",
        "merged_input_sha256": "9" * 64,
        "stub_output_json": "reports/all_four_field_typed_consumer_stub.json",
        "stub_output_sha256": "a" * 64,
        "native_consumer_executed": True,
        "native_consumer_passed": True,
        "field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "future_wna16_typed_slot_kernel_variant_all_handle_fields_read": True,
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
    }
    hashes = {
        "hash_accumulator": "1111111111111111",
        "handle_projection_hash_accumulator": "2222222222222222",
        "descriptor_ptr_read_hash_accumulator": "3333333333333333",
        "packed_weight_descriptor_read_hash_accumulator": "4444444444444444",
        "scale_metadata_handle_read_hash_accumulator": "5555555555555555",
        "aux_metadata_handle_read_hash_accumulator": "6666666666666666",
    }
    for prefix in (
        "future_wna16_kernel_side_consumer_execution",
        "wna16_side_consumer_variant_execution",
    ):
        for key, value in hashes.items():
            payload[f"{prefix}_{key}"] = value
        for field in (
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ):
            payload[f"{prefix}_{field}_read_row_ok_count"] = row_count
    return payload


def _future_wna16_kernel_side_typed_consumer_path_payload(
    *,
    all_four_json: str,
    all_four_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
) -> dict[str, object]:
    return {
        "all_four_gate_ready": True,
        "all_four_json": all_four_json,
        "all_four_sha256": all_four_sha256,
        "artifact_kind": "future_wna16_kernel_side_typed_consumer_path",
        "bench_semantics": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "explicit_typed_abi_slot": True,
        "failures": [],
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "future_wna16_kernel_side_consumer_execution_checked": True,
        "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator": (
            "1111111111111111"
        ),
        "future_wna16_kernel_side_consumer_execution_row_count": row_count,
        "future_wna16_kernel_side_consumer_execution_row_ok_count": row_count,
        "independent_kernel_side_consumer_path": True,
        "input_json_count": source_count,
        "kernel_arg_pass_allowed": False,
        "kernel_side_typed_consumer_path_mode": (
            "independent_future_wna16_kernel_side_typed_consumer_path"
        ),
        "kernel_side_typed_consumer_path_name": (
            "premap_future_wna16_kernel_side_typed_consumer_path_v1"
        ),
        "kernel_side_typed_consumer_path_source": (
            "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
        ),
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "merged_input_json": "reports/kernel_side_path_merged_input.json",
        "merged_input_sha256": "2" * 64,
        "native_consumer_executed": True,
        "native_consumer_json": "reports/kernel_side_path_native_runner.json",
        "native_consumer_passed": True,
        "native_consumer_sha256": "3" * 64,
        "passed": True,
        "passed_to_kernel": False,
        "passes_current_wna16_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "requires_wna16_arg_reinterpretation": False,
        "row_count": row_count,
        "row_ok_count": row_count,
        "schema_version": 1,
        "selected_input_manifest_sha256": "4" * 64,
        "source_count": source_count,
        "stage_type": "lab_gate",
        "stub_output_json": "reports/kernel_side_path_typed_consumer_stub.json",
        "stub_output_sha256": "5" * 64,
        "uses_current_wna16_args": False,
        "wna16_benchmark_ready": False,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_checked": True,
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
            "6666666666666666"
        ),
        "wna16_side_consumer_variant_execution_row_count": row_count,
        "wna16_side_consumer_variant_execution_row_ok_count": row_count,
    }


def _future_wna16_payloadless_execution_payload(
    *,
    kernel_side_path_json: str,
    kernel_side_path_sha256: str,
    kernel_side_all_four_sha256: str,
    kernel_side_selected_input_manifest_sha256: str,
    fourth_field_json: str,
    fourth_field_sha256: str,
    runner_json: str,
    runner_sha256: str,
    timing_stub_json: str,
    timing_stub_sha256: str,
    benchmark_json: str,
    benchmark_sha256: str,
    sweep_json: str,
    sweep_sha256: str,
    sweep_check_json: str,
    sweep_check_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
) -> dict[str, object]:
    return {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_payloadless_execution"
        ),
        "passed": True,
        "failures": [],
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
        "payloadless_execution_ready": True,
        "payloadless_execution_gate_ready": True,
        "payloadless_execution_lab_preflight_ready": True,
        "payloadless_execution_native_artifact_ready": True,
        "payloadless_execution_native_requested": True,
        "payloadless_execution_native_executed": True,
        "payloadless_execution_native_passed": True,
        "payloadless_execution_native_host_wall_ms": 12.0,
        "payloadless_execution_outer_wall_ms": 13.0,
        "payloadless_execution_runner_json": runner_json,
        "payloadless_execution_runner_sha256": runner_sha256,
        "payloadless_execution_timing_stub_json": timing_stub_json,
        "payloadless_execution_timing_stub_sha256": timing_stub_sha256,
        "payloadless_execution_canary_json": "reports/payloadless_canary.json",
        "all_four_field_consumer_ready": True,
        "all_four_field_consumer_fields_read": True,
        "all_four_field_consumer_hashes_valid": True,
        "all_four_field_consumer_source_count": source_count,
        "all_four_field_consumer_row_count": row_count,
        "all_four_field_consumer_row_ok_count": row_count,
        "all_four_field_consumer_fourth_field_path_label": (
            fourth_field_json
        ),
        "all_four_field_consumer_fourth_field_sha256": fourth_field_sha256,
        "future_wna16_kernel_side_typed_consumer_path_ready": True,
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        "future_wna16_kernel_side_typed_consumer_path_evidence_path": (
            kernel_side_path_json
        ),
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256": (
            kernel_side_path_sha256
        ),
        "future_wna16_kernel_side_typed_consumer_path_source_count": source_count,
        "future_wna16_kernel_side_typed_consumer_path_input_json_count": source_count,
        "future_wna16_kernel_side_typed_consumer_path_row_count": row_count,
        "future_wna16_kernel_side_typed_consumer_path_row_ok_count": row_count,
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256": (
            kernel_side_all_four_sha256
        ),
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": (
            kernel_side_selected_input_manifest_sha256
        ),
        "benchmark_json": benchmark_json,
        "benchmark_sha256": benchmark_sha256,
        "benchmark_is_current_wna16_fused_moe": False,
        "benchmark_repeat_count_measured": 3,
        "benchmark_native_stub_host_wall_ms_stats": {
            "count": 3,
            "max_ms": 12.0,
            "mean_ms": 11.0,
            "median_ms": 11.0,
            "min_ms": 10.0,
            "p10_ms": 10.0,
            "p90_ms": 12.0,
        },
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "field_read_row_ok_counts": {
            field: row_count for field in _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        },
        "field_read_hashes": {
            "descriptor_ptr": "3333333333333333",
            "packed_weight_descriptor": "4444444444444444",
            "scale_metadata_handle": "5555555555555555",
            "aux_metadata_handle": "6666666666666666",
        },
        "fourth_field_handoff_ready": True,
        "fourth_field_handoff_source_count": source_count,
        "fourth_field_handoff_row_count": row_count,
        "fourth_field_handoff_row_ok_count": row_count,
        "fourth_field_handoff_field_read_hash": "6e08db27babecb6a",
        "fourth_field_handoff_runner_hash": "ba2e219a8ff9ccfe",
        "fourth_field_handoff_evidence_path": fourth_field_json,
        "fourth_field_handoff_evidence_sha256": fourth_field_sha256,
        "entry_args_ptr_required": True,
        "entry_args_ptr_sweep_json": sweep_json,
        "entry_args_ptr_sweep_sha256": sweep_sha256,
        "entry_args_ptr_sweep_check_json": sweep_check_json,
        "entry_args_ptr_sweep_check_sha256": sweep_check_sha256,
        "entry_args_ptr_sweep_row_count": 1841,
        "entry_args_ptr_sweep_check_row_count": 1841,
        "entry_args_ptr_sweep_device": 1,
        "entry_args_ptr_sweep_window_size": 512,
        "entry_args_ptr_sweep_mirror_fields": list(
            _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        ),
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
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


_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]


def _future_wna16_variant_execution_payload(
    *,
    payloadless_json: str,
    payloadless_sha256: str,
    native_json: str,
    native_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
) -> dict[str, object]:
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
        "passed": True,
        "failures": [],
        "execution_name": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        "execution_mode": "independent_future_wna16_typed_slot_kernel_variant_execution",
        "execution_source": "premap_future_wna16_typed_slot_payloadless_execution_v1",
        "future_wna16_variant_execution_scope": (
            "independent_native_typed_slot_kernel_variant_execution"
        ),
        "payloadless_gate_ready": True,
        "future_wna16_variant_execution_ready": True,
        "future_wna16_variant_execution_native_requested": True,
        "future_wna16_variant_execution_native_executed": True,
        "future_wna16_variant_execution_native_passed": True,
        "future_wna16_variant_execution_native_artifact_ready": True,
        "future_wna16_variant_execution_not_current_wna16_kernel": True,
        "future_wna16_variant_execution_native_host_wall_ms": 12.0,
        "future_wna16_variant_execution_outer_wall_ms": 13.0,
        "future_wna16_variant_execution_native_json": native_json,
        "future_wna16_variant_execution_native_sha256": native_sha256,
        "payloadless_json": payloadless_json,
        "payloadless_sha256": payloadless_sha256,
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "field_read_row_ok_counts": {
            field: row_count for field in _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        },
        "field_read_hashes": {
            "descriptor_ptr": "3333333333333333",
            "packed_weight_descriptor": "4444444444444444",
            "scale_metadata_handle": "5555555555555555",
            "aux_metadata_handle": "6666666666666666",
        },
        "row_hash_accumulator": "7777777777777777",
        "handle_projection_hash_accumulator": "8888888888888888",
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


def _future_wna16_useful_consumer_payload(
    *,
    execution_json: str,
    execution_sha256: str,
    native_timing_json: str,
    native_timing_sha256: str,
    native_stub_json: str,
    native_stub_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
) -> dict[str, object]:
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_useful_consumer",
        "passed": True,
        "failures": [],
        "useful_consumer_name": "premap_future_wna16_typed_slot_useful_consumer_v1",
        "useful_consumer_mode": "independent_wna16_side_typed_slot_useful_consumer",
        "useful_consumer_source": (
            "premap_future_wna16_typed_slot_kernel_variant_execution_v1"
        ),
        "useful_consumer_semantics": "wna16_side_variant_all_four_field_projection",
        "useful_consumer_ready": True,
        "useful_consumer_native_stub_checked": True,
        "execution_json": execution_json,
        "execution_sha256": execution_sha256,
        "native_timing_json": native_timing_json,
        "native_timing_sha256": native_timing_sha256,
        "native_stub_json": native_stub_json,
        "native_stub_sha256": native_stub_sha256,
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "field_read_row_ok_counts": {
            field: row_count for field in _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        },
        "field_read_hashes": {
            "descriptor_ptr": "3333333333333333",
            "packed_weight_descriptor": "4444444444444444",
            "scale_metadata_handle": "5555555555555555",
            "aux_metadata_handle": "6666666666666666",
        },
        "useful_consumer_rows_consumed": row_count,
        "useful_consumer_fields_consumed": list(
            _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        ),
        "useful_consumer_field_read_hashes": {
            "descriptor_ptr": "7777777777777771",
            "packed_weight_descriptor": "7777777777777772",
            "scale_metadata_handle": "7777777777777773",
            "aux_metadata_handle": "7777777777777774",
        },
        "useful_consumer_hash": "9999999999999999999999999999999999999999999999999999999999999999",
        "wna16_side_consumer_variant_execution_checked": True,
        "wna16_side_consumer_variant_execution_row_count": row_count,
        "wna16_side_consumer_variant_execution_row_ok_count": row_count,
        "wna16_side_consumer_variant_execution_hash_accumulator": "aaaaaaaaaaaaaaaa",
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
            "bbbbbbbbbbbbbbbb"
        ),
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
            "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
        ),
    }


def _future_wna16_payloadless_useful_execution_payload(
    *,
    useful_consumer_json: str,
    useful_consumer_sha256: str,
    execution_json: str,
    execution_sha256: str,
    native_timing_json: str,
    native_timing_sha256: str,
    native_stub_json: str,
    native_stub_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
        ),
        "passed": True,
        "failures": [],
        "payloadless_useful_execution_name": (
            "premap_future_wna16_typed_slot_payloadless_useful_execution_v1"
        ),
        "payloadless_useful_execution_mode": (
            "independent_future_wna16_typed_slot_payloadless_useful_execution"
        ),
        "payloadless_useful_execution_source": (
            "premap_future_wna16_typed_slot_kernel_variant_useful_consumer_v1"
        ),
        "payloadless_useful_execution_ready": True,
        "payloadless_useful_execution_gate_ready": True,
        "payloadless_useful_execution_chain_checked": True,
        "payloadless_useful_execution_native_stub_checked": True,
        "payloadless_useful_execution_rows_consumed": row_count,
        "payloadless_useful_execution_field_count": len(
            _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        ),
        "payloadless_useful_execution_fields_per_row": len(
            _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        ),
        "payloadless_useful_execution_useful_work_units": row_count
        * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "payloadless_useful_execution_expected_useful_work_units": row_count
        * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "payloadless_useful_execution_useful_work_coverage": 1.0,
        "payloadless_useful_execution_useful_work_kind": (
            "native_typed_slot_four_field_row_projection"
        ),
        "payloadless_useful_execution_native_consumer_has_useful_work": True,
        "payloadless_useful_execution_chain_hash": (
            "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
        ),
        "useful_consumer_json": useful_consumer_json,
        "useful_consumer_sha256": useful_consumer_sha256,
        "execution_json": execution_json,
        "execution_sha256": execution_sha256,
        "native_timing_json": native_timing_json,
        "native_timing_sha256": native_timing_sha256,
        "native_stub_json": native_stub_json,
        "native_stub_sha256": native_stub_sha256,
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "field_read_row_ok_counts": {
            field: row_count for field in _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        },
        "field_read_hashes": {
            "descriptor_ptr": "3333333333333333",
            "packed_weight_descriptor": "4444444444444444",
            "scale_metadata_handle": "5555555555555555",
            "aux_metadata_handle": "6666666666666666",
        },
        "useful_consumer_fields_consumed": list(
            _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        ),
        "useful_consumer_field_read_hashes": {
            "descriptor_ptr": "7777777777777771",
            "packed_weight_descriptor": "7777777777777772",
            "scale_metadata_handle": "7777777777777773",
            "aux_metadata_handle": "7777777777777774",
        },
        "useful_consumer_hash": (
            "9999999999999999999999999999999999999999999999999999999999999999"
        ),
        "wna16_side_consumer_variant_execution_hash_accumulator": (
            "aaaaaaaaaaaaaaaa"
        ),
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
            "bbbbbbbbbbbbbbbb"
        ),
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


def _future_wna16_payloadless_useful_repeat_benchmark_payload(
    *,
    harness_json: str,
    harness_sha256: str,
    native_timing_seed_json: str,
    native_timing_seed_sha256: str,
    repeat_output_prefix: str = "repeat",
    row_count: int = 520,
    source_count: int = 128,
    repeat_count: int = 3,
) -> dict[str, object]:
    return {
        "schema_version": 1,
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
        "repeat_count_requested": repeat_count,
        "repeat_count_measured": repeat_count,
        "harness_json": harness_json,
        "harness_sha256": harness_sha256,
        "native_timing_seed_json": native_timing_seed_json,
        "native_timing_seed_sha256": native_timing_seed_sha256,
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "rows_consumed": row_count,
        "field_count": len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "fields_per_row": len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "useful_work_units": row_count * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "expected_useful_work_units": (
            row_count * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
        ),
        "useful_work_coverage": 1.0,
        "useful_work_kind": "native_typed_slot_four_field_row_projection",
        "native_consumer_has_useful_work": True,
        "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "field_read_hashes": {
            "descriptor_ptr": "3333333333333333",
            "packed_weight_descriptor": "4444444444444444",
            "scale_metadata_handle": "5555555555555555",
            "aux_metadata_handle": "6666666666666666",
        },
        "native_stub_host_wall_ms_values": [10.0, 11.0, 12.0],
        "native_stub_host_wall_ms_stats": {
            "count": repeat_count,
            "max_ms": 12.0,
            "mean_ms": 11.0,
            "median_ms": 11.0,
            "min_ms": 10.0,
        },
        "repeat_output_jsons": [
            f"reports/{repeat_output_prefix}_repeat_{idx:03d}.json"
            for idx in range(repeat_count)
        ],
        "repeat_output_sha256s": ["a" * 64 for _ in range(repeat_count)],
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


def _future_wna16_payloadless_useful_runtime_ablation_payload(
    *,
    repeat_benchmark_json: str,
    repeat_benchmark_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
    repeat_count: int = 3,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_runtime_ablation",
        "ablation_name": (
            "premap_future_wna16_typed_slot_payloadless_useful_runtime_ablation_v1"
        ),
        "ablation_mode": "payloadless_useful_native_stub_repeat_stability_ablation",
        "ablation_source": (
            "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1"
        ),
        "passed": True,
        "failures": [],
        "runtime_ablation_ready": True,
        "payloadless_useful_runtime_ablation_ready": True,
        "repeat_benchmark_json": repeat_benchmark_json,
        "repeat_benchmark_sha256": repeat_benchmark_sha256,
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "rows_consumed": row_count,
        "repeat_count_measured": repeat_count,
        "field_count": len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "fields_per_row": len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "useful_work_units": row_count * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "expected_useful_work_units": (
            row_count * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
        ),
        "useful_work_coverage": 1.0,
        "useful_work_kind": "native_typed_slot_four_field_row_projection",
        "native_consumer_has_useful_work": True,
        "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "field_read_hashes": {
            "descriptor_ptr": "3333333333333333",
            "packed_weight_descriptor": "4444444444444444",
            "scale_metadata_handle": "5555555555555555",
            "aux_metadata_handle": "6666666666666666",
        },
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
            "implement_future_wna16_typed_slot_payloadless_useful_production_like_timing"
        ),
    }


def _future_wna16_payloadless_useful_production_like_timing_gate_payload(
    *,
    runtime_ablation_json: str,
    runtime_ablation_sha256: str,
    row_count: int = 520,
    source_count: int = 128,
    repeat_count: int = 3,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "artifact_kind": (
            "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate"
        ),
        "timing_gate_name": (
            "premap_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_v1"
        ),
        "timing_gate_mode": "production_like_config_readiness_gate",
        "timing_gate_source": (
            "premap_future_wna16_typed_slot_payloadless_useful_runtime_ablation_v1"
        ),
        "passed": True,
        "failures": [],
        "production_like_timing_ready": True,
        "runtime_ablation_ready": True,
        "payloadless_useful_runtime_ablation_ready": True,
        "runtime_ablation_json": runtime_ablation_json,
        "runtime_ablation_sha256": runtime_ablation_sha256,
        "trace_config_is_production_like": True,
        "payloadless_live_config_performance_claim_frozen": True,
        "payloadless_production_tpot_allowed": False,
        "will_measure_tpot_next": False,
        "current_artifact_is_tpot_benchmark": False,
        "source_count": source_count,
        "row_count": row_count,
        "repeat_count_measured": repeat_count,
        "field_count": len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "fields_per_row": len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "useful_work_units": row_count * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "expected_useful_work_units": (
            row_count * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
        ),
        "useful_work_coverage": 1.0,
        "useful_work_kind": "native_typed_slot_four_field_row_projection",
        "native_consumer_has_useful_work": True,
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
        "bound_runtime_ablation_safety": {
            "benchmark_is_current_wna16_fused_moe": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "kernel_arg_pass_allowed": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
            "passed_to_kernel": False,
            "passes_current_wna16_args": False,
            "payload_bytes": 0,
            "payload_deref_allowed": False,
            "requires_wna16_arg_reinterpretation": False,
            "uses_current_wna16_args": False,
            "wna16_benchmark_ready": False,
        },
        "next_runtime_stage": "future_typed_slot_useful_consumer_or_payload_cache_manager",
    }


def _future_native_arg_slot_all_field_entry_args_ptr_sweep_payload(
    *,
    check_json: str,
    row_count: int = 1841,
) -> dict[str, object]:
    return {
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
        "passed": True,
        "failures": [],
        "device": 1,
        "dry_run": False,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "window_size": 512,
        "block_threads": 256,
        "mirror_fields": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "require_program_view_ptr_abi": True,
        "require_kernel_arg_packet_abi": True,
        "require_kernel_entry_args_abi": True,
        "require_kernel_entry_args_ptr_abi": True,
        "row_counts": {
            field: row_count for field in _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        },
        "field_reports": {
            field: {
                "passed": True,
                "sweep_failures": [],
                "check_failures": [],
                "row_count": row_count,
                "window_size": 512,
                "windows_checked": ["full", "head", "middle", "tail"],
                "sweep_json": f"reports/{field}_entry_args_ptr_window_sweep.json",
                "check_json": f"reports/{field}_entry_args_ptr_window_check.json",
            }
            for field in _ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS
        },
        "check_json": check_json,
    }


def _future_native_arg_slot_all_field_entry_args_ptr_sweep_check_payload(
    *,
    sweep_json: str,
    row_count: int = 1841,
) -> dict[str, object]:
    return {
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
        "passed": True,
        "failures": [],
        "all_field_window_sweep_json": sweep_json,
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
        "mirror_fields_checked": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
        "row_count": row_count,
    }


def _wna16_side_consumer_variant_execution_runner_payload(
    input_path: str,
    stub_path: str,
    *,
    row_count: int = 520,
    selected_source_count: int = 128,
) -> dict[str, object]:
    payload = _online_merged_arg_slot_multiprogram_runner_payload(
        input_path,
        stub_path,
        require_wna16_adjacent_typed_slot=True,
    )
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    payload.update(
        {
            "selected_source_count": selected_source_count,
            "merged_row_count": row_count,
            "merged_expected_program_count": 3,
            "dispatch_row_limit": row_count,
            "dispatch_active_rows": row_count,
            "dispatch_expected_program_count": 3,
            "require_wna16_side_consumer_variant_execution": True,
            "future_wna16_typed_slot_kernel_variant_packet_chain_depth": 15,
            "wna16_side_consumer_variant_execution_checked": True,
            "wna16_side_consumer_variant_execution_name": (
                "premap_wna16_side_consumer_variant_execution_v1"
            ),
            "wna16_side_consumer_variant_execution_mode": (
                "readonly_wna16_side_consumer_variant_execution"
            ),
            "wna16_side_consumer_variant_execution_source": (
                "premap_future_wna16_typed_slot_kernel_variant_v1"
            ),
            "wna16_side_consumer_variant_execution_row_count": row_count,
            "wna16_side_consumer_variant_execution_row_ok_count": row_count,
            "wna16_side_consumer_variant_execution_error_count": 0,
            "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
            "wna16_side_consumer_variant_execution_packet_chain_depth": 16,
            "wna16_side_consumer_variant_execution_payload_bytes": 0,
            "wna16_side_consumer_variant_execution_passed_to_kernel": False,
            "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
            "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
            "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
            "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
            "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
                "e9a06475ca6a56d0"
            ),
        }
    )
    stub_summary.update(
        {
            "wna16_side_consumer_variant_execution_checked": True,
            "wna16_side_consumer_variant_execution_abi_name": (
                "premap_wna16_side_consumer_variant_execution_v1"
            ),
            "wna16_side_consumer_variant_execution_mode": (
                "readonly_wna16_side_consumer_variant_execution"
            ),
            "wna16_side_consumer_variant_execution_source": (
                "premap_future_wna16_typed_slot_kernel_variant_v1"
            ),
            "wna16_side_consumer_variant_execution_row_count": row_count,
            "wna16_side_consumer_variant_execution_row_ok_count": row_count,
            "wna16_side_consumer_variant_execution_error_count": 0,
            "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count": row_count,
            "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_row_ok_count": row_count,
            "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_ok_count": row_count,
            "wna16_side_consumer_variant_execution_aux_metadata_handle_read_row_ok_count": row_count,
            "wna16_side_consumer_variant_execution_hash_accumulator": (
                "4ff003ba01541147"
            ),
            "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
                "e9a06475ca6a56d0"
            ),
            "wna16_side_consumer_variant_execution_descriptor_ptr_read_hash_accumulator": (
                "f21873c80428f9c9"
            ),
            "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_hash_accumulator": (
                "cdd0b1ee1ecc961f"
            ),
            "wna16_side_consumer_variant_execution_scale_metadata_handle_read_hash_accumulator": (
                "f79958eb1fbdf45c"
            ),
            "wna16_side_consumer_variant_execution_aux_metadata_handle_read_hash_accumulator": (
                "47d5c9d76d4decc7"
            ),
            "wna16_side_consumer_variant_execution_payload_bytes": 0,
            "wna16_side_consumer_variant_execution_passed_to_kernel": False,
            "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
            "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
            "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
            "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
            "wna16_side_consumer_variant_execution_explicit_typed_abi_slot": True,
        }
    )
    return payload


def _online_merged_arg_slot_multiprogram_runner_payload(
    input_path: str,
    stub_path: str,
    *,
    mirror_field: str = "scale_metadata_handle",
    require_wna16_adjacent_typed_slot: bool = False,
) -> dict[str, object]:
    stub_summary = _online_merged_arg_slot_multiprogram_canary_payload(
        input_path,
        mirror_field=mirror_field,
    )
    payload = {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_canary_runner",
        "runner_json": "reports/native_online_prelaunch_canary_runner_32.json",
        "selected_source_count": 32,
        "min_source_count": 32,
        "merged_output_json": input_path,
        "stub_output_json": stub_path,
        "merged_row_count": 520,
        "merged_expected_program_count": 3,
        "dispatch_row_offset": 0,
        "dispatch_row_limit": 520,
        "dispatch_active_rows": 520,
        "dispatch_expected_program_count": 3,
        "block_threads": 256,
        "device": 0,
        "hip_visible_devices": "1",
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_field_names": [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ],
        "handle_projection_hashchain_equal": True,
        "handle_projection_all_handle_fields_checked": True,
        "mirror_field": mirror_field,
        "stub_summary": stub_summary,
    }
    payload.update(
        {
            "require_kernel_launch_context_abi": True,
            "require_kernel_launch_descriptor_abi": True,
            "require_launch_envelope_args_abi": True,
            "require_launch_envelope_args_ptr_abi": True,
            "require_kernel_invocation_abi": True,
            "require_kernel_invocation_entry_abi": True,
            "require_kernel_endpoint_abi": True,
            "require_kernel_endpoint_ptr_abi": True,
        }
    )
    payload.update(
        _kernel_launch_context_metrics(
            prefix="kernel_launch_context",
            row_count=520,
            include_all_handle_fields_read=True,
        )
    )
    payload.update(
        _invocation_metrics(
            prefix="kernel_invocation",
            row_count=520,
            include_all_handle_fields_read=True,
        )
    )
    payload.update(
        _invocation_entry_metrics(
            prefix="kernel_invocation_entry",
            row_count=520,
            include_all_handle_fields_read=True,
        )
    )
    payload.update(
        _endpoint_metrics(
            prefix="kernel_endpoint",
            row_count=520,
            include_all_handle_fields_read=True,
        )
    )
    payload.update(
        _endpoint_ptr_metrics(
            prefix="kernel_endpoint_ptr",
            row_count=520,
            include_all_handle_fields_read=True,
        )
    )
    if require_wna16_adjacent_typed_slot:
        payload.update(
            {
                "require_wna16_adjacent_typed_slot": True,
                "wna16_adjacent_typed_slot_checked": True,
                "wna16_adjacent_typed_slot_name": (
                    "premap_wna16_adjacent_typed_consumer_slot_v1"
                ),
                "wna16_adjacent_typed_slot_mode": (
                    "readonly_wna16_adjacent_typed_consumer_slot"
                ),
                "wna16_adjacent_typed_slot_source": (
                    "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
                ),
                "wna16_adjacent_typed_slot_row_count": 520,
                "wna16_adjacent_typed_slot_row_ok_count": 520,
                "wna16_adjacent_typed_slot_error_count": 0,
                "wna16_adjacent_typed_slot_all_handle_fields_read": True,
                "wna16_adjacent_typed_slot_packet_chain_depth": 14,
                "wna16_adjacent_typed_slot_payload_bytes": 0,
                "wna16_adjacent_typed_slot_passed_to_kernel": False,
                "wna16_adjacent_typed_slot_changes_kernel_launch_args": False,
                "wna16_adjacent_typed_slot_current_wna16_arg_compatible": False,
                "wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation": False,
                "wna16_adjacent_typed_slot_explicit_typed_abi_slot": True,
                "wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot": False,
                "wna16_adjacent_typed_slot_row_hash_accumulator": (
                    "c4b51a0fa5ba88c4"
                ),
                "wna16_adjacent_typed_slot_field_read_hash_accumulator": (
                    "c2e4ae7fa9bc3227"
                ),
                "wna16_adjacent_typed_slot_row_metadata_hash_accumulator": (
                    "1a11b42afa9e8576"
                ),
            }
        )
        stub_summary.update(
            {
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_checked": True,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_abi_name": (
                    "premap_wna16_adjacent_typed_consumer_slot_v1"
                ),
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_mode": (
                    "readonly_wna16_adjacent_typed_consumer_slot"
                ),
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_source": (
                    "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
                ),
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_packet_chain_depth": 14,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_error_count": 0,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_field_mask": 15,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_descriptor_ptr_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_packed_weight_descriptor_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_scale_metadata_handle_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_aux_metadata_handle_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_expert_id_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_address_key_hash_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_metadata_read_row_ok_count": 520,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_payload_bytes": 0,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_passed_to_kernel": False,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_changes_kernel_launch_args": False,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_current_wna16_arg_compatible": False,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation": False,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_explicit_typed_abi_slot": True,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot": False,
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_hash_accumulator": (
                    "c4b51a0fa5ba88c4"
                ),
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_field_read_hash_accumulator": (
                    "c2e4ae7fa9bc3227"
                ),
                "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_metadata_hash_accumulator": (
                    "1a11b42afa9e8576"
                ),
            }
        )
    stub_summary.update(
        _invocation_entry_metrics(
            prefix="future_kernel_native_consumer_invocation_entry",
            row_count=520,
        )
    )
    stub_summary.update(
        _endpoint_metrics(
            prefix="future_kernel_native_consumer_endpoint",
            row_count=520,
        )
    )
    stub_summary.update(
        _endpoint_ptr_metrics(
            prefix="future_kernel_native_consumer_endpoint_ptr",
            row_count=520,
        )
    )
    # The online runner embeds a compact stub_summary.  The full stub artifact
    # still carries ABI identity/layout fields, but the embedded summary keeps
    # only the runtime safety fields plus summary_* counters.
    for compact_key in (
        "future_kernel_native_consumer_invocation_entry_abi_name",
        "future_kernel_native_consumer_invocation_entry_error_count",
        "future_kernel_native_consumer_endpoint_abi_name",
        "future_kernel_native_consumer_endpoint_error_count",
    ):
        stub_summary.pop(compact_key, None)
    return payload


def _runner_mirror_summary(field_name: str) -> dict[str, object]:
    payload = _runner_stub_summary()
    payload.update(
        {
            "single_field_mirror_checked": True,
            "single_field_mirror_field_name": field_name,
            "single_field_mirror_row_count": 2,
            "single_field_mirror_row_ok_count": 2,
            "single_field_mirror_error_count": 0,
        }
    )
    if field_name == "scale_metadata_handle":
        payload.update(
            {
                "kernel_consumer_envelope_checked": True,
                "kernel_consumer_envelope_payload_bytes": 0,
                "kernel_consumer_envelope_passed_to_kernel": False,
            }
        )
    return payload


def _runner_extra_input_summary(index: int = 1) -> dict[str, object]:
    return {
        "input_index": index,
        "input_json": f"reports/native_online_prelaunch_input_{index:04d}.json",
        "passed": True,
        "failures": [],
        "outputs": {
            "native_stub": {"summary": _runner_stub_summary()},
            "native_stub_per_field": {"summary": _runner_stub_summary()},
            "native_stub_kernel_envelope_mirror": {
                "summary": _runner_mirror_summary("scale_metadata_handle")
            },
            "native_stub_packed_weight_mirror": {
                "summary": _runner_mirror_summary("packed_weight_descriptor")
            },
            "native_stub_aux_metadata_mirror": {
                "summary": _runner_mirror_summary("aux_metadata_handle")
            },
            "native_stub_descriptor_ptr_mirror": {
                "summary": _runner_mirror_summary("descriptor_ptr")
            },
            "native_stub_kernel_side_compatible_consumer_abi": {
                "summary": _runner_kernel_side_compatible_summary()
            },
            "native_stub_future_kernel_consumer_args": {
                "summary": _runner_future_kernel_args_summary()
            },
            "native_stub_future_kernel_args_compatible_consumer_path": {
                "summary": _runner_future_kernel_args_compatible_path_summary()
            },
            "native_stub_future_kernel_native_consumer_abi": {
                "summary": _runner_future_kernel_native_consumer_summary()
            },
            "native_stub_future_kernel_native_consumer_descriptor_ptr_mirror": {
                "summary": _runner_future_kernel_native_consumer_summary(
                    "descriptor_ptr"
                )
            },
            "native_stub_future_kernel_native_consumer_packed_weight_mirror": {
                "summary": _runner_future_kernel_native_consumer_summary(
                    "packed_weight_descriptor"
                )
            },
            "native_stub_future_kernel_native_consumer_aux_metadata_mirror": {
                "summary": _runner_future_kernel_native_consumer_summary(
                    "aux_metadata_handle"
                )
            },
            "native_stub_future_kernel_native_consumer_launch_abi": {
                "summary": _runner_future_kernel_native_launch_consumer_summary()
            },
            "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror": {
                "summary": _runner_future_kernel_native_launch_consumer_summary(
                    "descriptor_ptr"
                )
            },
            "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror": {
                "summary": _runner_future_kernel_native_launch_consumer_summary(
                    "packed_weight_descriptor"
                )
            },
            "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror": {
                "summary": _runner_future_kernel_native_launch_consumer_summary(
                    "aux_metadata_handle"
                )
            },
            "native_stub_future_kernel_native_consumer_dispatch_abi": {
                "summary": _runner_future_kernel_native_dispatch_consumer_summary()
            },
            "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror": {
                "summary": _runner_future_kernel_native_dispatch_consumer_summary(
                    "descriptor_ptr"
                )
            },
            "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror": {
                "summary": _runner_future_kernel_native_dispatch_consumer_summary(
                    "packed_weight_descriptor"
                )
            },
            "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror": {
                "summary": _runner_future_kernel_native_dispatch_consumer_summary(
                    "aux_metadata_handle"
                )
            },
            "native_stub_future_kernel_native_consumer_request_ptr_abi": {
                "summary": _runner_future_kernel_native_request_ptr_summary()
            },
            "native_stub_future_kernel_native_consumer_request_launch_abi": {
                "summary": _runner_future_kernel_native_request_launch_summary()
            },
        },
    }


def _write_prefetch_lab_default_gate(root: Path) -> str:
    ready_time_report = (
        "outputs/reports/prefetch_cache_manager/"
        "measured_ready_time_gate_gpu1_dolly8_gen4.json"
    )
    ready_time_direct_snapshot_report = (
        "outputs/reports/premap_kernel_consumer/"
        "premap_payload_cache_ready_time_direct_snapshot_boundary_test.json"
    )
    metadata_premap_summary = (
        "outputs/reports/prefetch_action_replay/"
        "metadata_premap_gate_summary.json"
    )
    stream_decision_gate = (
        "outputs/reports/premap_kernel_consumer/"
        "premap_payload_cache_stream_full_fetch_decision_gate_token_index_test.json"
    )
    stream_feasibility = (
        "outputs/reports/premap_kernel_consumer/"
        "premap_payload_cache_stream_earlier_issue_feasibility_token_index_test.json"
    )
    stream_lead_sweep = (
        "outputs/reports/premap_kernel_consumer/"
        "premap_payload_cache_stream_earlier_issue_lead_tokens_token_index_test.json"
    )
    stream_shifted_issue_contract = (
        "outputs/reports/premap_kernel_consumer/"
        "premap_payload_cache_stream_shifted_issue_replay_contract_token_index_test.json"
    )
    stream_queue_budget = (
        "outputs/reports/premap_kernel_consumer/"
        "premap_payload_cache_issue_stream_executor_queue_budget_token_index_test.json"
    )
    capacity_gate = (
        "configs/runtime/"
        "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
    )
    gate_path = "configs/runtime/prefetch_lab_default_gate_gpu1.yaml"
    _write(
        root / ready_time_report,
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": False,
                "decision_reason": "full_fetch_threshold_not_met",
                "decision": "block_full_fetch",
                "threshold_failures": ["used_per_issued_fetch_below_threshold"],
                "metrics": {
                    "demand_hit_rate": 0.9672,
                    "ready_late_miss_rate": 0.000036,
                    "issued_fetch_count": 12,
                    "used_fetch_count": 0,
                    "used_per_issued_fetch": 0.0,
                },
            },
            sort_keys=True,
        )
        + "\n",
    )
    measured_copy_path = "configs/runtime/premap_payload_cache_gpu1_h2d_smoke_measured_copy.json"
    _write(root / measured_copy_path, '{"rows": []}\n')
    _write(
        root / ready_time_direct_snapshot_report,
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": False,
                "decision_reason": "full_fetch_threshold_not_met",
                "threshold_failures": ["used_per_issued_fetch_below_threshold"],
                "metrics": {
                    "mode": "ready_time",
                    "manager_count": 1,
                    "demand_count": 10594,
                    "demand_hit_count": 3261,
                    "demand_hit_rate": 0.30781574476118556,
                    "ready_late_miss_count": 0,
                    "ready_late_miss_rate": 0.0,
                    "issued_fetch_count": 0,
                    "used_fetch_count": 0,
                    "used_per_issued_fetch": 0.0,
                    "queue_batch_size": 8,
                    "queue_deadline_us": 1000.0,
                    "measured_copy_path": measured_copy_path,
                    "measured_copy_us_per_issue": 1832.6639936503852,
                    "direct_snapshot_present": True,
                    "direct_manager_mode": "ready_time",
                    "direct_demand_count": 10594,
                    "direct_demand_hit_count": 3261,
                    "direct_ready_late_miss_count": 0,
                    "direct_issued_fetch_count": 0,
                    "direct_used_fetch_count": 0,
                    "direct_queue_batch_size": 8,
                    "direct_queue_deadline_us": 1000.0,
                    "direct_snapshot_runtime_stage": (
                        "online_ready_time_payload_cache_accounting_only"
                    ),
                    "direct_snapshot_payload_bytes": 0,
                    "direct_snapshot_ready_credit": False,
                    "direct_snapshot_real_ready_credit_granted": False,
                    "direct_snapshot_full_fetch_runtime_allowed": False,
                    "direct_snapshot_payload_transfer_runtime_enabled": False,
                    "direct_snapshot_changes_kernel_launch_args": False,
                    "direct_snapshot_demand_on_consumer": True,
                    "direct_snapshot_issue_sources": [
                        "prelaunch_observed_transition_premap_shadow"
                    ],
                    "direct_snapshot_runtime_participation_present": True,
                    "direct_snapshot_runtime_participation_stage": (
                        "online_ready_time_payload_cache_runtime_participation_dry_run"
                    ),
                    "direct_snapshot_runtime_participation_status": (
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_participation_consumes_manager_snapshot": (
                        True
                    ),
                    "direct_snapshot_runtime_participation_payload_bytes": 0,
                    "direct_snapshot_runtime_participation_ready_credit": False,
                    "direct_snapshot_runtime_participation_real_ready_credit_granted": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_kernel_arg_pass_allowed": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_changes_kernel_launch_args": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_full_fetch_runtime_allowed": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_payload_transfer_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_issue_sources": [
                        "prelaunch_observed_transition_premap_shadow"
                    ],
                    "direct_snapshot_runtime_participation_candidate_reason": (
                        "no_used_fetch"
                    ),
                    "direct_snapshot_runtime_plan_present": True,
                    "direct_snapshot_runtime_plan_stage": (
                        "payload_cache_runtime_plan_lab_gate_dry_run"
                    ),
                    "direct_snapshot_runtime_plan_status": (
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_plan_consumes_participation": True,
                    "direct_snapshot_runtime_plan_participation_status": (
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_plan_live_payload_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_plan_planned_issue_count": 0,
                    "direct_snapshot_runtime_plan_payload_bytes": 0,
                    "direct_snapshot_runtime_plan_ready_credit": False,
                    "direct_snapshot_runtime_plan_kernel_arg_pass_allowed": False,
                    "direct_snapshot_runtime_plan_changes_kernel_launch_args": False,
                    "direct_snapshot_runtime_plan_full_fetch_runtime_allowed": False,
                    "direct_snapshot_runtime_execution_present": True,
                    "direct_snapshot_runtime_execution_stage": (
                        "payload_cache_runtime_execution_lab_gate_dry_run"
                    ),
                    "direct_snapshot_runtime_execution_status": (
                        "blocked_by_runtime_plan:"
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_execution_consumes_plan": True,
                    "direct_snapshot_runtime_execution_plan_status": (
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_execution_decision": "blocked",
                    "direct_snapshot_runtime_execution_block_reason": (
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_execution_execution_mode": (
                        "payloadless_lab_gate_dry_run"
                    ),
                    "direct_snapshot_runtime_execution_live_payload_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_payload_transfer_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_issued_payload_count": 0,
                    "direct_snapshot_runtime_execution_payload_bytes": 0,
                    "direct_snapshot_runtime_execution_ready_credit": False,
                    "direct_snapshot_runtime_execution_real_ready_credit_granted": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_kernel_arg_pass_allowed": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_changes_kernel_launch_args": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_full_fetch_runtime_allowed": (
                        False
                    ),
                },
            },
            sort_keys=True,
        )
        + "\n",
    )
    no_op_fields = {
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "live_payload_runtime_enabled": False,
        "payload_transfer_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "full_fetch_runtime_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "wna16_benchmark_ready": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "live_runtime_instantiated": False,
    }
    _write(
        root / stream_decision_gate,
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_stream_lookahead",
                "current_lookahead_us": 0.0,
                "required_stream_lookahead_us": 2400000.0,
                "lookahead_deficit_us": 2400000.0,
                "first_model_passing_lookahead_us": 2400000.0,
                "required_shifted_issue_accounting": {
                    "shifted_issue_accounting_enabled": True,
                    "shifted_issue_lead_tokens": 32,
                    "shifted_issue_clamped_issue_count": 12,
                    "shifted_issue_duplicate_issue_key_count": 12,
                    "shifted_issue_unique_issue_key_count": 16,
                    "shifted_issue_accounted_packet_count": 28,
                    "shifted_issue_invalid_export_count": 0,
                    "shifted_issue_row_shift_mismatch_count": 0,
                    "shifted_issue_row_clamp_mismatch_count": 0,
                },
                "metadata_premap_runtime_preferred": True,
                "descriptor_prep_runtime_preferred": True,
                **no_op_fields,
            },
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        root / stream_feasibility,
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_feasibility",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "current_runtime_satisfies_model": False,
                "feasible_within_configured_token_window": True,
                "min_required_lead_tokens": 24,
                "max_required_lead_tokens": 48,
                "min_deficit_lead_tokens": 24,
                "max_deficit_lead_tokens": 48,
                "max_candidate_lead_tokens": 64,
                **no_op_fields,
            },
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        root / stream_lead_sweep,
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_lead_token_sweep",
                "passed": True,
                "full_fetch_allowed": False,
                "full_fetch_runtime_allowed": False,
                "event_timing_mode": "token_index",
                "token_timing_enabled": True,
                "decode_token_us": 75000.0,
                "first_model_passing_lead_tokens": 32,
                "first_model_passing_lookahead_us": 2400000.0,
                **no_op_fields,
            },
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        root / stream_shifted_issue_contract,
        json.dumps(
            {
                "artifact_kind": (
                    "premap_payload_cache_stream_shifted_issue_replay_contract"
                ),
                "passed": True,
                "failures": [],
                "issue_lead_tokens": 32,
                "packet_count": 5,
                "schedulable_packet_count": 4,
                "empty_issue_exempt_count": 1,
                "clamped_issue_count": 2,
                "duplicate_demand_key_count": 0,
                "duplicate_issue_key_count": 2,
                "unique_demand_key_count": 4,
                "unique_issue_key_count": 2,
                "total_issue_candidates": 32,
                "issue_hash_count": 4,
                "allow_clamped_issue_tokens": True,
                "allow_duplicate_issue_keys": True,
                "full_fetch_runtime_allowed": False,
                "full_fetch_allowed": False,
                **no_op_fields,
                "rows": [
                    {
                        "packet_index": index,
                        "sample_idx": 0,
                        "record_id": "record-0",
                        "sequence_id": 0,
                        "layer_id": 0,
                        "demand_token_index": demand,
                        "issue_token_index": max(0, demand - 32),
                        "issue_clamped_to_zero": demand < 32,
                    }
                    for index, demand in enumerate([8, 16, 32, 48])
                ],
            },
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        root / stream_queue_budget,
        json.dumps(
            {
                "artifact_kind": (
                    "premap_payload_cache_issue_stream_executor_queue_budget_sweep"
                ),
                "passed": True,
                "failures": [],
                "event_timing_mode": "token_index",
                "cell_count": 1,
                "cells": [
                    {
                        "capacity": 4096,
                        "cell_index": 0,
                        "model_passed": True,
                        "passed": True,
                        "queue_deadline_us": 100.0,
                        "first_model_passing_issue_lead_tokens": 32,
                        "first_model_passing_lookahead_us": 2400000.0,
                        "first_model_passing_shifted_issue_accounting": {
                            "shifted_issue_accounting_enabled": True,
                            "shifted_issue_lead_tokens": 32,
                            "shifted_issue_clamped_issue_count": 12,
                            "shifted_issue_duplicate_issue_key_count": 12,
                            "shifted_issue_unique_issue_key_count": 16,
                            "shifted_issue_accounted_packet_count": 28,
                            "shifted_issue_invalid_export_count": 0,
                            "shifted_issue_row_shift_mismatch_count": 0,
                            "shifted_issue_row_clamp_mismatch_count": 0,
                        },
                    },
                ],
                "first_model_passing_cell": {
                    "capacity": 4096,
                    "cell_index": 0,
                    "issue_lead_tokens": 32,
                    "lookahead_us": 2400000.0,
                    "queue_deadline_us": 100.0,
                    "shifted_issue_accounting": {
                        "shifted_issue_accounting_enabled": True,
                        "shifted_issue_lead_tokens": 32,
                        "shifted_issue_clamped_issue_count": 12,
                        "shifted_issue_duplicate_issue_key_count": 12,
                        "shifted_issue_unique_issue_key_count": 16,
                        "shifted_issue_accounted_packet_count": 28,
                        "shifted_issue_invalid_export_count": 0,
                        "shifted_issue_row_shift_mismatch_count": 0,
                        "shifted_issue_row_clamp_mismatch_count": 0,
                    },
                },
                "full_fetch_allowed": False,
                "full_fetch_block_reason": "real_payload_runtime_not_enabled",
                **no_op_fields,
            },
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        root / metadata_premap_summary,
        json.dumps(
            {
                "metadata_positive_count": 0,
                "premap_positive_count": 4,
            },
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        root / capacity_gate,
        "schema_version: 1\n"
        "capacity_gate:\n"
        "  recommended_capacity_entries: 12288\n"
        "  no_eviction_capacity_entries: 12288\n",
    )
    _write(
        root / gate_path,
        "schema_version: 1\n"
        "gate_id: prefetch_lab_default_gpu1_test\n"
        "full_fetch:\n"
        "  default_enabled: false\n"
        f"  ready_time_gate_report: {ready_time_report}\n"
        f"  ready_time_direct_snapshot_report: {ready_time_direct_snapshot_report}\n"
        f"  stream_decision_gate_report: {stream_decision_gate}\n"
        f"  stream_earlier_issue_feasibility_report: {stream_feasibility}\n"
        f"  stream_earlier_issue_lead_token_sweep_report: {stream_lead_sweep}\n"
        f"  stream_shifted_issue_replay_contract_report: {stream_shifted_issue_contract}\n"
        f"  stream_queue_budget_report: {stream_queue_budget}\n"
        "  stream_shifted_issue_replay_required_lead_tokens: 32\n"
        "  stream_shifted_issue_replay_min_schedulable_packets: 4\n"
        "metadata:\n"
        "  default_enabled: false\n"
        f"  summary: {metadata_premap_summary}\n"
        "  max_default_positive_count: 0\n"
        "premap:\n"
        "  default_enabled: true\n"
        f"  summary: {metadata_premap_summary}\n"
        "  min_positive_count: 4\n"
        f"  capacity_gate: {capacity_gate}\n"
        "  min_capacity_entries: 12288\n",
    )
    return gate_path


def _write_gate(
    root: Path,
    name: str,
    evidence_json: str,
    *,
    typed_consumer_required: bool = True,
    canary: bool | None = None,
    lab_default: bool | None = None,
    include_lab_evidence: bool = True,
    lab_evidence_passed: bool = True,
    lab_evidence_failures: list[str] | None = None,
    include_schema_artifact: bool = True,
    live_connected_readonly: bool = True,
) -> str:
    _write_prefetch_lab_default_gate(root)
    schema_path = _write_valid_schema(root)
    evidence_path = f"reports/{evidence_json}"
    _write(root / evidence_path, '{"passed": true}\n')
    lab_gate_path = f"reports/{name}_typed_consumer_gate.json"
    lab_selfcheck_path = f"reports/{name}_typed_consumer_selfcheck.json"
    typed_row_path = f"reports/{name}_typed_row_consumer_path_gate.json"
    single_field_canary_path = f"reports/{name}_single_field_handle_handoff_canary_gate.json"
    lab_live_connected_path = f"reports/{name}_live_connected_readonly_gate.json"
    lab_native_bridge_path = f"reports/{name}_native_bridge_online_gate.json"
    native_bridge_path = f"reports/{name}_native_bridge_smoke.json"
    lab_native_stub_path = f"reports/{name}_native_stub_online_invocation_canary_gate.json"
    native_typed_stub_path = f"reports/{name}_native_typed_consumer_stub_gpu1_canary.json"
    native_typed_endpoint_ptr_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_endpoint_ptr_canary.json"
    )
    native_bridge_input_path = f"reports/{name}_native_bridge_input.json"
    native_online_input_path = f"reports/{name}_native_online_prelaunch_input.json"
    native_online_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_canary.json"
    )
    native_online_endpoint_ptr_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary.json"
    )
    native_online_request_ptr_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    native_online_request_launch_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_request_launch_canary.json"
    )
    native_online_request_launch_ptr_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary.json"
    )
    native_online_perf_path = (
        f"reports/{name}_native_online_prelaunch_export_performance.json"
    )
    prelaunch_pointer_source_observer_check_path = (
        f"reports/{name}_prelaunch_pointer_source_observer_check.json"
    )
    readonly_live_trusted_refs_check_path = (
        f"reports/{name}_readonly_live_trusted_refs_check.json"
    )
    native_online_runner_path = (
        f"reports/{name}_native_online_prelaunch_canary_runner.json"
    )
    native_online_artifact_check_path = (
        f"reports/{name}_native_online_prelaunch_canary_artifact_check.json"
    )
    native_online_runner_32_path = (
        f"reports/{name}_native_online_prelaunch_canary_runner_32.json"
    )
    native_online_artifact_check_32_path = (
        f"reports/{name}_native_online_prelaunch_canary_artifact_check_32.json"
    )
    standalone_dispatch_ptr_canary_path = (
        f"reports/{name}_future_native_dispatch_ptr_standalone_canary.json"
    )
    standalone_arg_slot_canary_path = (
        f"reports/{name}_future_native_arg_slot_standalone_canary.json"
    )
    standalone_arg_slot_packed_weight_canary_path = (
        f"reports/{name}_future_native_arg_slot_packed_weight_canary.json"
    )
    standalone_arg_slot_aux_metadata_canary_path = (
        f"reports/{name}_future_native_arg_slot_aux_metadata_canary.json"
    )
    standalone_arg_slot_descriptor_ptr_canary_path = (
        f"reports/{name}_future_native_arg_slot_descriptor_ptr_canary.json"
    )
    standalone_arg_slot_multiprogram_canary_path = (
        f"reports/{name}_future_native_arg_slot_multiprogram_canary.json"
    )
    online_merged_arg_slot_multiprogram_input_path = (
        f"reports/{name}_online_merged_arg_slot_multiprogram_input.json"
    )
    online_merged_arg_slot_multiprogram_canary_path = (
        f"reports/{name}_online_merged_future_native_endpoint_canary.json"
    )
    online_merged_arg_slot_multiprogram_runner_path = (
        f"reports/{name}_online_merged_future_native_endpoint_runner.json"
    )
    online_merged_wna16_adjacent_typed_slot_runner_path = (
        f"reports/{name}_online_merged_wna16_adjacent_typed_slot_runner.json"
    )
    online_merged_wna16_adjacent_typed_slot_stub_path = (
        f"reports/{name}_typed_consumer_stub_gpu1_online_merged_"
        "wna16_adjacent_slot_native_bridge.json"
    )
    future_wna16_single_field_handoff_all_fields_summary_path = (
        f"reports/{name}_future_wna16_single_field_handoff_all_fields_128strict_summary.json"
    )
    future_wna16_typed_slot_fourth_field_handoff_canary_path = (
        f"reports/{name}_future_wna16_typed_slot_fourth_field_handoff_canary.json"
    )
    future_wna16_typed_slot_all_four_field_consumer_path = (
        f"reports/{name}_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    future_wna16_kernel_side_typed_consumer_path = (
        f"reports/{name}_future_wna16_kernel_side_typed_consumer_path.json"
    )
    future_wna16_typed_slot_payloadless_execution_path = (
        f"reports/{name}_future_wna16_typed_slot_payloadless_execution.json"
    )
    future_wna16_typed_slot_kernel_variant_execution_path = (
        f"reports/{name}_future_wna16_typed_slot_kernel_variant_execution.json"
    )
    future_wna16_typed_slot_kernel_variant_execution_native_path = (
        f"reports/{name}_future_wna16_typed_slot_kernel_variant_execution_native.json"
    )
    future_wna16_typed_slot_kernel_variant_execution_native_stub_path = (
        f"reports/{name}_future_wna16_typed_slot_kernel_variant_execution_native_stub.json"
    )
    future_wna16_typed_slot_kernel_variant_useful_consumer_path = (
        f"reports/{name}_future_wna16_typed_slot_kernel_variant_useful_consumer.json"
    )
    future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_path = (
        f"reports/{name}_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.json"
    )
    future_wna16_typed_slot_payloadless_useful_repeat_benchmark_path = (
        f"reports/{name}_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    future_wna16_typed_slot_payloadless_useful_runtime_ablation_path = (
        f"reports/{name}_future_wna16_typed_slot_payloadless_useful_runtime_ablation.json"
    )
    future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_path = (
        f"reports/{name}_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate.json"
    )
    future_wna16_typed_slot_payloadless_timing_stub_path = (
        f"reports/{name}_future_wna16_typed_slot_payloadless_timing_stub.json"
    )
    future_wna16_typed_slot_payloadless_benchmark_path = (
        f"reports/{name}_future_wna16_typed_slot_payloadless_benchmark.json"
    )
    future_native_arg_slot_all_field_entry_args_ptr_sweep_path = (
        f"reports/{name}_future_native_arg_slot_all_field_entry_args_ptr_sweep.json"
    )
    future_native_arg_slot_all_field_entry_args_ptr_sweep_check_path = (
        f"reports/{name}_future_native_arg_slot_all_field_entry_args_ptr_sweep_check.json"
    )
    wna16_side_consumer_variant_execution_input_path = (
        f"reports/{name}_wna16_side_consumer_variant_execution_input.json"
    )
    wna16_side_consumer_variant_execution_stub_path = (
        f"reports/{name}_wna16_side_consumer_variant_execution_stub.json"
    )
    wna16_side_consumer_variant_execution_runner_path = (
        f"reports/{name}_wna16_side_consumer_variant_execution_128strict_runner.json"
    )
    payload_cache_producer_state_native_canary_path = (
        f"reports/{name}_payload_cache_producer_state_native_canary.json"
    )
    payload_cache_shifted_issue_runtime_shadow_gate_path = (
        f"reports/{name}_payload_cache_shifted_issue_runtime_shadow_gate.json"
    )
    payload_cache_packet_export_manifest_path = (
        f"reports/{name}_payload_cache_packet_export_manifest.json"
    )
    payload_cache_producer_state_nonempty_issue_stub_path = (
        f"reports/{name}_payload_cache_producer_state_nonempty_issue_stub.json"
    )
    payload_cache_producer_state_stream_native_canary_path = (
        f"reports/{name}_payload_cache_producer_state_stream_native_canary.json"
    )
    payload_cache_producer_state_packet_stream_native_canary_path = (
        f"reports/{name}_payload_cache_producer_state_packet_stream_native_canary.json"
    )
    payload_cache_producer_state_packet_stream_native_canary_check_path = (
        f"reports/{name}_payload_cache_producer_state_packet_stream_native_canary_check.json"
    )
    payload_cache_producer_state_stream_online_contract_path = (
        f"reports/{name}_payload_cache_producer_state_stream_online_contract.json"
    )
    payload_cache_producer_state_inprocess_native_session_online_contract_path = (
        f"reports/{name}_payload_cache_producer_state_inprocess_native_session_online_contract.json"
    )
    payload_cache_stream_producer_production_ab_bridge_path = (
        f"reports/{name}_payload_cache_stream_producer_production_ab_bridge.json"
    )
    payload_cache_stream_producer_production_ab_bridge_check_path = (
        f"reports/{name}_payload_cache_stream_producer_production_ab_bridge_check.json"
    )
    payload_cache_online_native_producer_boundary_gap_path = (
        f"reports/{name}_payload_cache_online_native_producer_boundary_gap.json"
    )
    payload_cache_demand_hit_shadow_publication_gate_path = (
        f"reports/{name}_payload_cache_demand_hit_shadow_publication_gate.json"
    )
    payload_cache_consumer_visible_hit_blocked_gate_path = (
        f"reports/{name}_payload_cache_consumer_visible_hit_blocked_gate.json"
    )
    payload_cache_vllm_replay_visible_native_producer_contract_path = (
        f"reports/{name}_payload_cache_vllm_replay_visible_native_producer_contract.json"
    )
    payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_path = (
        f"reports/{name}_payload_cache_vllm_replay_visible_count_ptr_native_producer_contract.json"
    )
    payload_cache_vllm_replay_visible_count_ptr_readiness_path = (
        f"reports/{name}_payload_cache_vllm_replay_visible_count_ptr_readiness.json"
    )
    payload_cache_manager_useful_work_ab_gate_path = (
        f"reports/{name}_payload_cache_manager_useful_work_ab_gate.json"
    )
    payload_cache_manager_production_ab_preflight_path = (
        f"reports/{name}_payload_cache_manager_production_ab_preflight.json"
    )
    standalone_wna16_adjacent_typed_slot_canary_path = (
        f"reports/{name}_future_native_wna16_adjacent_typed_slot_standalone_canary.json"
    )
    online_merged_arg_slot_descriptor_ptr_runner_path = (
        f"reports/{name}_online_merged_future_native_arg_slot_descriptor_ptr_runner.json"
    )
    online_merged_arg_slot_descriptor_ptr_canary_path = (
        f"reports/{name}_online_merged_future_native_arg_slot_descriptor_ptr_canary.json"
    )
    online_merged_arg_slot_packed_weight_runner_path = (
        f"reports/{name}_online_merged_future_native_arg_slot_packed_weight_runner.json"
    )
    online_merged_arg_slot_packed_weight_canary_path = (
        f"reports/{name}_online_merged_future_native_arg_slot_packed_weight_descriptor_canary.json"
    )
    online_merged_arg_slot_aux_metadata_runner_path = (
        f"reports/{name}_online_merged_future_native_arg_slot_aux_metadata_runner.json"
    )
    online_merged_arg_slot_aux_metadata_canary_path = (
        f"reports/{name}_online_merged_future_native_arg_slot_aux_metadata_handle_canary.json"
    )
    future_kernel_args_descriptor_ptr_canary_path = (
        f"reports/{name}_future_kernel_args_descriptor_ptr_canary.json"
    )
    future_kernel_args_packed_weight_canary_path = (
        f"reports/{name}_future_kernel_args_packed_weight_canary.json"
    )
    future_kernel_args_aux_metadata_canary_path = (
        f"reports/{name}_future_kernel_args_aux_metadata_canary.json"
    )
    future_kernel_args_compatible_path_canary_path = (
        f"reports/{name}_future_kernel_args_compatible_path_canary.json"
    )
    future_kernel_args_compatible_path_artifact_check_path = (
        f"reports/{name}_future_kernel_args_compatible_path_artifact_check.json"
    )
    future_kernel_args_field_refresh_flatten_check_path = (
        f"reports/{name}_future_kernel_args_field_refresh_flatten_check.json"
    )
    future_kernel_args_field_refresh_artifact_check_path = (
        f"reports/{name}_future_kernel_args_field_refresh_artifact_check.json"
    )
    future_kernel_native_consumer_scale_canary_path = (
        f"reports/{name}_future_kernel_native_consumer_scale_canary.json"
    )
    future_kernel_native_consumer_descriptor_ptr_canary_path = (
        f"reports/{name}_future_kernel_native_consumer_descriptor_ptr_canary.json"
    )
    future_kernel_native_consumer_packed_weight_canary_path = (
        f"reports/{name}_future_kernel_native_consumer_packed_weight_canary.json"
    )
    future_kernel_native_consumer_aux_metadata_canary_path = (
        f"reports/{name}_future_kernel_native_consumer_aux_metadata_canary.json"
    )
    future_kernel_native_consumer_launch_scale_canary_path = (
        f"reports/{name}_future_kernel_native_consumer_launch_scale_canary.json"
    )
    native_online_per_field_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_per_field_canary.json"
    )
    packed_weight_single_field_canary_path = (
        f"reports/{name}_packed_weight_single_field_handle_handoff_canary_smoke.json"
    )
    aux_metadata_single_field_canary_path = (
        f"reports/{name}_aux_metadata_single_field_handle_handoff_canary_smoke.json"
    )
    descriptor_ptr_single_field_canary_path = (
        f"reports/{name}_descriptor_ptr_single_field_handle_handoff_canary_smoke.json"
    )
    lab_payload = {
        "passed": lab_evidence_passed,
        "failures": [] if lab_evidence_failures is None else lab_evidence_failures,
        "metrics": _lab_evidence_metrics(),
    }
    if include_lab_evidence:
        _write(root / lab_gate_path, json.dumps(lab_payload) + "\n")
        _write(root / lab_selfcheck_path, json.dumps(lab_payload) + "\n")
        _write(root / typed_row_path, json.dumps(lab_payload) + "\n")
        _write(root / single_field_canary_path, json.dumps(lab_payload) + "\n")
        _write(
            root / packed_weight_single_field_canary_path,
            json.dumps(
                {
                    "passed": lab_evidence_passed,
                    "failures": (
                        []
                        if lab_evidence_failures is None
                        else lab_evidence_failures
                    ),
                    "metrics": _lab_evidence_metrics(
                        single_field_name="packed_weight_descriptor"
                    ),
                }
            )
            + "\n",
        )
        _write(
            root / aux_metadata_single_field_canary_path,
            json.dumps(
                {
                    "passed": lab_evidence_passed,
                    "failures": (
                        []
                        if lab_evidence_failures is None
                        else lab_evidence_failures
                    ),
                    "metrics": _lab_evidence_metrics(
                        single_field_name="aux_metadata_handle"
                    ),
                }
            )
            + "\n",
        )
        _write(
            root / descriptor_ptr_single_field_canary_path,
            json.dumps(
                {
                    "passed": lab_evidence_passed,
                    "failures": (
                        []
                        if lab_evidence_failures is None
                        else lab_evidence_failures
                    ),
                    "metrics": _lab_evidence_metrics(
                        single_field_name="descriptor_ptr"
                    ),
                }
            )
            + "\n",
        )
        _write(root / lab_live_connected_path, json.dumps(lab_payload) + "\n")
        _write(root / lab_native_bridge_path, json.dumps(lab_payload) + "\n")
        _write(root / native_bridge_path, json.dumps(lab_payload) + "\n")
        _write(root / lab_native_stub_path, json.dumps(lab_payload) + "\n")
        _write(
            root / prelaunch_pointer_source_observer_check_path,
            json.dumps(_prelaunch_pointer_source_observer_check_payload()) + "\n",
        )
        _write(
            root / readonly_live_trusted_refs_check_path,
            json.dumps(_readonly_live_trusted_refs_check_payload()) + "\n",
        )
        _write(
            root / payload_cache_demand_hit_shadow_publication_gate_path,
            json.dumps(_payload_cache_demand_hit_shadow_publication_gate_payload()) + "\n",
        )
        _write(
            root / payload_cache_consumer_visible_hit_blocked_gate_path,
            json.dumps(_payload_cache_consumer_visible_hit_blocked_gate_payload()) + "\n",
        )
        _write(
            root / native_bridge_input_path,
            json.dumps(_native_bridge_input_payload()) + "\n",
        )
        _write(
            root / native_online_input_path,
            json.dumps(_native_online_prelaunch_input_payload()) + "\n",
        )
        _write(
            root / native_typed_stub_path,
            json.dumps(_native_stub_evidence_payload(native_bridge_input_path)) + "\n",
        )
        _write(
            root / native_typed_endpoint_ptr_stub_path,
            json.dumps(
                _native_stub_endpoint_ptr_evidence_payload(native_bridge_input_path)
            )
            + "\n",
        )
        _write(
            root / native_online_stub_path,
            json.dumps(_native_stub_evidence_payload(native_online_input_path)) + "\n",
        )
        _write(
            root / native_online_endpoint_ptr_stub_path,
            json.dumps(
                _native_stub_endpoint_ptr_evidence_payload(
                    native_online_input_path,
                    field_mask=15,
                    aux_read_count=2,
                )
            )
            + "\n",
        )
        _write(
            root / native_online_request_ptr_stub_path,
            json.dumps(
                _native_stub_request_ptr_evidence_payload(native_online_input_path)
            )
            + "\n",
        )
        _write(
            root / native_online_request_launch_stub_path,
            json.dumps(
                _native_stub_request_launch_evidence_payload(native_online_input_path)
            )
            + "\n",
        )
        _write(
            root / native_online_request_launch_ptr_stub_path,
            json.dumps(
                _native_stub_request_launch_ptr_evidence_payload(
                    native_online_input_path
                )
            )
            + "\n",
        )
        _write(
            root / native_online_per_field_stub_path,
            json.dumps(
                _native_stub_per_field_evidence_payload(native_online_input_path)
            )
            + "\n",
        )
        _write(
            root / native_online_perf_path,
            json.dumps(
                {
                    "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                    "runtime_shadow_premap_native_typed_consumer_input_export_count": 16,
                    "runtime_shadow_premap_native_typed_consumer_input_export_first_path": native_online_input_path,
                    "runtime_shadow_premap_native_typed_consumer_input_export_paths": [
                        native_online_input_path,
                        *[
                            f"reports/{name}_native_online_prelaunch_input_{idx:04d}.json"
                            for idx in range(1, 16)
                        ],
                    ],
                }
            )
            + "\n",
        )
        def _runner_payload(input_count: int) -> dict[str, object]:
            extra_count = input_count - 1
            return {
                "passed": True,
                "failures": [],
                "online_prelaunch_input_json": native_online_input_path,
                "online_prelaunch_input_check_count": input_count,
                "online_prelaunch_input_extra_check_count": extra_count,
                "online_prelaunch_input_extra_check_passed_count": extra_count,
                "extra_online_input_check_summaries": [
                    _runner_extra_input_summary(idx)
                    for idx in range(1, input_count)
                ],
                "native_stub_output_json": native_online_stub_path,
                "preflight_output_json": f"reports/{name}_preflight.json",
                "stub_summary": _runner_stub_summary(),
                "descriptor_ptr_mirror_stub_summary": (
                    _runner_mirror_summary("descriptor_ptr")
                ),
                "packed_weight_mirror_stub_summary": (
                    _runner_mirror_summary("packed_weight_descriptor")
                ),
                "kernel_envelope_mirror_stub_summary": (
                    _runner_mirror_summary("scale_metadata_handle")
                ),
                "aux_metadata_mirror_stub_summary": (
                    _runner_mirror_summary("aux_metadata_handle")
                ),
                "kernel_side_compatible_stub_summary": (
                    _runner_kernel_side_compatible_summary()
                ),
                "future_kernel_args_stub_summary": (
                    _runner_future_kernel_args_summary()
                ),
                "future_kernel_args_compatible_path_stub_summary": (
                    _runner_future_kernel_args_compatible_path_summary()
                ),
                "future_kernel_native_consumer_stub_summary": (
                    _runner_future_kernel_native_consumer_summary()
                ),
                "future_kernel_native_consumer_descriptor_ptr_stub_summary": (
                    _runner_future_kernel_native_consumer_summary("descriptor_ptr")
                ),
                "future_kernel_native_consumer_packed_weight_stub_summary": (
                    _runner_future_kernel_native_consumer_summary(
                        "packed_weight_descriptor"
                    )
                ),
                "future_kernel_native_consumer_aux_metadata_stub_summary": (
                    _runner_future_kernel_native_consumer_summary(
                        "aux_metadata_handle"
                    )
                ),
                "future_kernel_native_consumer_launch_stub_summary": (
                    _runner_future_kernel_native_launch_consumer_summary()
                ),
                "future_kernel_native_consumer_launch_descriptor_ptr_stub_summary": (
                    _runner_future_kernel_native_launch_consumer_summary(
                        "descriptor_ptr"
                    )
                ),
                "future_kernel_native_consumer_launch_packed_weight_stub_summary": (
                    _runner_future_kernel_native_launch_consumer_summary(
                        "packed_weight_descriptor"
                    )
                ),
                "future_kernel_native_consumer_launch_aux_metadata_stub_summary": (
                    _runner_future_kernel_native_launch_consumer_summary(
                        "aux_metadata_handle"
                    )
                ),
                "future_kernel_native_consumer_dispatch_stub_summary": (
                    _runner_future_kernel_native_dispatch_consumer_summary()
                ),
                "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary": (
                    _runner_future_kernel_native_dispatch_consumer_summary(
                        "descriptor_ptr"
                    )
                ),
                "future_kernel_native_consumer_dispatch_packed_weight_stub_summary": (
                    _runner_future_kernel_native_dispatch_consumer_summary(
                        "packed_weight_descriptor"
                    )
                ),
                "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary": (
                    _runner_future_kernel_native_dispatch_consumer_summary(
                        "aux_metadata_handle"
                    )
                ),
                "future_kernel_native_consumer_request_ptr_stub_summary": (
                    _runner_future_kernel_native_request_ptr_summary()
                ),
                "future_kernel_native_consumer_request_launch_stub_summary": (
                    _runner_future_kernel_native_request_launch_summary()
                ),
                "preflight_summary": {
                    "passed": True,
                    "failures": [],
                },
                "final_preflight_status_summary": {
                    "passed": True,
                    "strict_default_gate_evidence_deferred_count": 0,
                    "runtime_gate_evidence_deferred_count": 0,
                },
                "artifact_check_summary": _artifact_check_payload(input_count),
            }

        def _artifact_check_payload(input_count: int) -> dict[str, object]:
            extra_count = input_count - 1
            row_counts = [4] if input_count <= 1 else [4] + [2] * (input_count - 1)
            return {
                "passed": True,
                "failures": [],
                "bootstrap_preflight_allowed": False,
                "final_deferred_count": 0,
                "require_all_field_mirror_stubs": True,
                "min_online_inputs": input_count,
                "runner_online_prelaunch_input_check_count": input_count,
                "runner_online_prelaunch_input_row_counts": row_counts,
                "runner_online_prelaunch_input_row_count_min": min(row_counts),
                "runner_online_prelaunch_input_row_count_max": max(row_counts),
                "runner_online_prelaunch_input_row_count_sum": sum(row_counts),
                "runner_online_prelaunch_input_row_count_diverse": (
                    min(row_counts) < max(row_counts)
                ),
                "runner_online_prelaunch_input_extra_check_count": extra_count,
                "runner_online_prelaunch_input_extra_check_passed_count": extra_count,
                "runner_descriptor_ptr_mirror_stub_row_count": 2,
                "runner_descriptor_ptr_mirror_stub_row_ok_count": 2,
                "runner_packed_weight_mirror_stub_row_count": 2,
                "runner_packed_weight_mirror_stub_row_ok_count": 2,
                "runner_kernel_envelope_mirror_stub_row_count": 2,
                "runner_kernel_envelope_mirror_stub_row_ok_count": 2,
                "runner_aux_metadata_mirror_stub_row_count": 2,
                "runner_aux_metadata_mirror_stub_row_ok_count": 2,
                "runner_kernel_side_compatible_stub_row_count": 2,
                "runner_kernel_side_compatible_stub_row_ok_count": 2,
                "runner_future_kernel_args_stub_row_count": 2,
                "runner_future_kernel_args_stub_row_ok_count": 2,
                "runner_future_kernel_args_compatible_path_stub_row_count": 2,
                "runner_future_kernel_args_compatible_path_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_stub_row_count": 2,
                "runner_future_kernel_native_consumer_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count": 2,
                "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_packed_weight_stub_row_count": 2,
                "runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_aux_metadata_stub_row_count": 2,
                "runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_launch_stub_row_count": 2,
                "runner_future_kernel_native_consumer_launch_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count": 2,
                "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count": 2,
                "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count": 2,
                "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_dispatch_stub_row_count": 2,
                "runner_future_kernel_native_consumer_dispatch_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count": 2,
                "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count": 2,
                "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count": 2,
                "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_request_ptr_stub_row_count": 2,
                "runner_future_kernel_native_consumer_request_ptr_stub_row_ok_count": 2,
                "runner_future_kernel_native_consumer_request_launch_stub_row_count": 2,
                "runner_future_kernel_native_consumer_request_launch_stub_row_ok_count": 2,
            }

        _write(root / native_online_runner_path, json.dumps(_runner_payload(16)) + "\n")
        _write(
            root / native_online_artifact_check_path,
            json.dumps(_artifact_check_payload(16)) + "\n",
        )
        _write(
            root / native_online_runner_32_path,
            json.dumps(_runner_payload(32)) + "\n",
        )
        _write(
            root / native_online_artifact_check_32_path,
            json.dumps(_artifact_check_payload(32)) + "\n",
        )
        _write(
            root / standalone_dispatch_ptr_canary_path,
            json.dumps(_standalone_dispatch_ptr_canary_payload()) + "\n",
        )
        _write(
            root / standalone_arg_slot_canary_path,
            json.dumps(_standalone_arg_slot_canary_payload()) + "\n",
        )
        _write(
            root / standalone_arg_slot_packed_weight_canary_path,
            json.dumps(
                _standalone_arg_slot_canary_payload(
                    mirror_field="packed_weight_descriptor"
                )
            )
            + "\n",
        )
        _write(
            root / standalone_arg_slot_aux_metadata_canary_path,
            json.dumps(
                _standalone_arg_slot_canary_payload(
                    mirror_field="aux_metadata_handle"
                )
            )
            + "\n",
        )
        _write(
            root / standalone_arg_slot_descriptor_ptr_canary_path,
            json.dumps(
                _standalone_arg_slot_canary_payload(mirror_field="descriptor_ptr")
            )
            + "\n",
        )
        _write(
            root / standalone_arg_slot_multiprogram_canary_path,
            json.dumps(_standalone_arg_slot_multiprogram_canary_payload()) + "\n",
        )
        _write(
            root / standalone_wna16_adjacent_typed_slot_canary_path,
            json.dumps(_standalone_wna16_adjacent_typed_slot_canary_payload()) + "\n",
        )
        _write(
            root / online_merged_arg_slot_multiprogram_input_path,
            json.dumps(_online_merged_arg_slot_multiprogram_input_payload()) + "\n",
        )
        _write(
            root / online_merged_arg_slot_multiprogram_canary_path,
            json.dumps(
                _online_merged_arg_slot_multiprogram_canary_payload(
                    online_merged_arg_slot_multiprogram_input_path
                )
            )
            + "\n",
        )
        _write(
            root / online_merged_wna16_adjacent_typed_slot_stub_path,
            json.dumps(
                _online_merged_arg_slot_multiprogram_canary_payload(
                    online_merged_arg_slot_multiprogram_input_path
                )
            )
            + "\n",
        )
        _write(
            root / online_merged_arg_slot_multiprogram_runner_path,
            json.dumps(
                _online_merged_arg_slot_multiprogram_runner_payload(
                    online_merged_arg_slot_multiprogram_input_path,
                    online_merged_arg_slot_multiprogram_canary_path,
                )
            )
            + "\n",
        )
        _write(
            root / online_merged_wna16_adjacent_typed_slot_runner_path,
            json.dumps(
                _online_merged_arg_slot_multiprogram_runner_payload(
                    online_merged_arg_slot_multiprogram_input_path,
                    online_merged_wna16_adjacent_typed_slot_stub_path,
                    require_wna16_adjacent_typed_slot=True,
                )
            )
            + "\n",
        )
        _write(
            root / future_wna16_single_field_handoff_all_fields_summary_path,
            json.dumps(_future_wna16_single_field_handoff_all_fields_summary_payload())
            + "\n",
        )
        _write(
            root / future_wna16_typed_slot_fourth_field_handoff_canary_path,
            json.dumps(
                _future_wna16_typed_slot_fourth_field_handoff_canary_payload()
            )
            + "\n",
        )
        fourth_field_handoff_canary_sha256 = hashlib.sha256(
            (root / future_wna16_typed_slot_fourth_field_handoff_canary_path).read_bytes()
        ).hexdigest()
        _write(
            root / future_wna16_typed_slot_all_four_field_consumer_path,
            json.dumps(
                _future_wna16_all_four_field_consumer_payload(
                    fourth_field_json=future_wna16_typed_slot_fourth_field_handoff_canary_path,
                    fourth_field_sha256=fourth_field_handoff_canary_sha256,
                )
            )
            + "\n",
        )
        all_four_field_consumer_sha256 = hashlib.sha256(
            (root / future_wna16_typed_slot_all_four_field_consumer_path).read_bytes()
        ).hexdigest()
        _write(
            root / future_wna16_kernel_side_typed_consumer_path,
            json.dumps(
                _future_wna16_kernel_side_typed_consumer_path_payload(
                    all_four_json=future_wna16_typed_slot_all_four_field_consumer_path,
                    all_four_sha256=all_four_field_consumer_sha256,
                )
            )
            + "\n",
        )
        _write(
            root / future_native_arg_slot_all_field_entry_args_ptr_sweep_path,
            json.dumps(
                _future_native_arg_slot_all_field_entry_args_ptr_sweep_payload(
                    check_json=(
                        future_native_arg_slot_all_field_entry_args_ptr_sweep_check_path
                    )
                )
            )
            + "\n",
        )
        _write(
            root / future_native_arg_slot_all_field_entry_args_ptr_sweep_check_path,
            json.dumps(
                _future_native_arg_slot_all_field_entry_args_ptr_sweep_check_payload(
                    sweep_json=future_native_arg_slot_all_field_entry_args_ptr_sweep_path
                )
            )
            + "\n",
        )
        future_native_arg_slot_all_field_entry_args_ptr_sweep_sha256 = hashlib.sha256(
            (root / future_native_arg_slot_all_field_entry_args_ptr_sweep_path).read_bytes()
        ).hexdigest()
        future_native_arg_slot_all_field_entry_args_ptr_sweep_check_sha256 = hashlib.sha256(
            (root / future_native_arg_slot_all_field_entry_args_ptr_sweep_check_path).read_bytes()
        ).hexdigest()
        _write(
            root / wna16_side_consumer_variant_execution_input_path,
            json.dumps(_wna16_side_arg_slot_multiprogram_input_payload()) + "\n",
        )
        _write(
            root / wna16_side_consumer_variant_execution_stub_path,
            json.dumps(
                _online_merged_arg_slot_multiprogram_canary_payload(
                    wna16_side_consumer_variant_execution_input_path
                )
            )
            + "\n",
        )
        _write(
            root / wna16_side_consumer_variant_execution_runner_path,
            json.dumps(
                _wna16_side_consumer_variant_execution_runner_payload(
                    wna16_side_consumer_variant_execution_input_path,
                    wna16_side_consumer_variant_execution_stub_path,
                )
            )
            + "\n",
        )
        wna16_side_consumer_variant_execution_runner_sha256 = hashlib.sha256(
            (root / wna16_side_consumer_variant_execution_runner_path).read_bytes()
        ).hexdigest()
        _write(
            root / future_wna16_typed_slot_payloadless_timing_stub_path,
            json.dumps({"artifact_kind": "payloadless_timing_stub_fixture"})
            + "\n",
        )
        _write(
            root / future_wna16_typed_slot_payloadless_benchmark_path,
            json.dumps(
                {
                    "artifact_kind": (
                        "future_wna16_typed_slot_payloadless_useful_benchmark_harness"
                    ),
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
                    "passed": True,
                    "failures": [],
                    "benchmark_harness_ready": True,
                    "payloadless_useful_benchmark_harness_ready": True,
                    "source_count": 128,
                    "row_count": 520,
                    "row_ok_count": 520,
                    "rows_consumed": 520,
                    "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
                    "field_read_hashes": {
                        "descriptor_ptr": "3333333333333333",
                        "packed_weight_descriptor": "4444444444444444",
                        "scale_metadata_handle": "5555555555555555",
                        "aux_metadata_handle": "6666666666666666",
                    },
                    "benchmark_is_current_wna16_fused_moe": False,
                    "measures_native_stub_host_wall_time": True,
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
                }
            )
            + "\n",
        )
        kernel_side_typed_consumer_sha256 = hashlib.sha256(
            (root / future_wna16_kernel_side_typed_consumer_path).read_bytes()
        ).hexdigest()
        future_wna16_typed_slot_payloadless_timing_stub_sha256 = hashlib.sha256(
            (root / future_wna16_typed_slot_payloadless_timing_stub_path).read_bytes()
        ).hexdigest()
        future_wna16_typed_slot_payloadless_benchmark_sha256 = hashlib.sha256(
            (root / future_wna16_typed_slot_payloadless_benchmark_path).read_bytes()
        ).hexdigest()
        _write(
            root / future_wna16_typed_slot_payloadless_execution_path,
            json.dumps(
                _future_wna16_payloadless_execution_payload(
                    kernel_side_path_json=future_wna16_kernel_side_typed_consumer_path,
                    kernel_side_path_sha256=kernel_side_typed_consumer_sha256,
                    kernel_side_all_four_sha256=all_four_field_consumer_sha256,
                    kernel_side_selected_input_manifest_sha256="4" * 64,
                    fourth_field_json=future_wna16_typed_slot_fourth_field_handoff_canary_path,
                    fourth_field_sha256=fourth_field_handoff_canary_sha256,
                    runner_json=wna16_side_consumer_variant_execution_runner_path,
                    runner_sha256=wna16_side_consumer_variant_execution_runner_sha256,
                    timing_stub_json=(
                        future_wna16_typed_slot_payloadless_timing_stub_path
                    ),
                    timing_stub_sha256=(
                        future_wna16_typed_slot_payloadless_timing_stub_sha256
                    ),
                    benchmark_json=future_wna16_typed_slot_payloadless_benchmark_path,
                    benchmark_sha256=(
                        future_wna16_typed_slot_payloadless_benchmark_sha256
                    ),
                    sweep_json=future_native_arg_slot_all_field_entry_args_ptr_sweep_path,
                    sweep_sha256=(
                        future_native_arg_slot_all_field_entry_args_ptr_sweep_sha256
                    ),
                    sweep_check_json=(
                        future_native_arg_slot_all_field_entry_args_ptr_sweep_check_path
                    ),
                    sweep_check_sha256=(
                        future_native_arg_slot_all_field_entry_args_ptr_sweep_check_sha256
                    ),
                )
            )
            + "\n",
        )
        future_wna16_typed_slot_payloadless_execution_sha256 = hashlib.sha256(
            (root / future_wna16_typed_slot_payloadless_execution_path).read_bytes()
        ).hexdigest()
        _write(
            root / future_wna16_typed_slot_kernel_variant_execution_native_stub_path,
            json.dumps(
                {
                    "artifact_kind": "future_wna16_typed_slot_kernel_variant_native_stub",
                    "passed": True,
                    "failures": [],
                    "payload_bytes": 0,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                    "current_wna16_arg_compatible": False,
                    "wna16_side_consumer_variant_execution_row_count": 520,
                    "wna16_side_consumer_variant_execution_row_ok_count": 520,
                    "wna16_side_consumer_variant_execution_error_count": 0,
                    "wna16_side_consumer_variant_execution_payload_bytes": 0,
                    "wna16_side_consumer_variant_execution_payload_deref_allowed": False,
                    "wna16_side_consumer_variant_execution_kernel_arg_pass_allowed": False,
                    "wna16_side_consumer_variant_execution_passed_to_kernel": False,
                    "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
                    "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
                    "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
                    "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
                    "wna16_side_consumer_variant_execution_hash_accumulator": (
                        "aaaaaaaaaaaaaaaa"
                    ),
                    "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
                        "bbbbbbbbbbbbbbbb"
                    ),
                    "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_count": 520,
                    "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count": 520,
                    "wna16_side_consumer_variant_execution_descriptor_ptr_read_error_count": 0,
                    "wna16_side_consumer_variant_execution_descriptor_ptr_read_hash_accumulator": (
                        "7777777777777771"
                    ),
                    "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_row_count": 520,
                    "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_row_ok_count": 520,
                    "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_error_count": 0,
                    "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_hash_accumulator": (
                        "7777777777777772"
                    ),
                    "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_count": 520,
                    "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_ok_count": 520,
                    "wna16_side_consumer_variant_execution_scale_metadata_handle_read_error_count": 0,
                    "wna16_side_consumer_variant_execution_scale_metadata_handle_read_hash_accumulator": (
                        "7777777777777773"
                    ),
                    "wna16_side_consumer_variant_execution_aux_metadata_handle_read_row_count": 520,
                    "wna16_side_consumer_variant_execution_aux_metadata_handle_read_row_ok_count": 520,
                    "wna16_side_consumer_variant_execution_aux_metadata_handle_read_error_count": 0,
                    "wna16_side_consumer_variant_execution_aux_metadata_handle_read_hash_accumulator": (
                        "7777777777777774"
                    ),
                }
            )
            + "\n",
        )
        future_wna16_typed_slot_kernel_variant_execution_native_stub_sha256 = (
            hashlib.sha256(
                (
                    root
                    / future_wna16_typed_slot_kernel_variant_execution_native_stub_path
                ).read_bytes()
            ).hexdigest()
        )
        _write(
            root / future_wna16_typed_slot_kernel_variant_execution_native_path,
            json.dumps(
                {
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
                    "passed": True,
                    "failures": [],
                    "timing_stub_ready": True,
                    "native_stub_requested": True,
                    "native_stub_executed": True,
                    "native_stub_passed": True,
                    "native_stub_host_wall_ms": 12.0,
                    "native_stub_output_json": (
                        future_wna16_typed_slot_kernel_variant_execution_native_stub_path
                    ),
                    "native_stub_output_sha256": (
                        future_wna16_typed_slot_kernel_variant_execution_native_stub_sha256
                    ),
                    "payload_bytes": 0,
                    "payload_deref_allowed": False,
                    "kernel_arg_pass_allowed": False,
                    "passed_to_kernel": False,
                    "changes_kernel_launch_args": False,
                    "uses_current_wna16_args": False,
                    "passes_current_wna16_args": False,
                    "current_wna16_arg_compatible": False,
                    "requires_wna16_arg_reinterpretation": False,
                    "measures_native_stub_host_wall_time": True,
                    "measures_tpot": False,
                    "measures_vllm_latency": False,
                    "wna16_benchmark_ready": False,
                    "source_count": 128,
                    "row_count": 520,
                    "row_ok_count": 520,
                    "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
                    "field_read_hashes": {
                        "descriptor_ptr": "3333333333333333",
                        "packed_weight_descriptor": "4444444444444444",
                        "scale_metadata_handle": "5555555555555555",
                        "aux_metadata_handle": "6666666666666666",
                    },
                }
            )
            + "\n",
        )
        future_wna16_typed_slot_kernel_variant_execution_native_sha256 = (
            hashlib.sha256(
                (
                    root / future_wna16_typed_slot_kernel_variant_execution_native_path
                ).read_bytes()
            ).hexdigest()
        )
        _write(
            root / future_wna16_typed_slot_kernel_variant_execution_path,
            json.dumps(
                _future_wna16_variant_execution_payload(
                    payloadless_json=future_wna16_typed_slot_payloadless_execution_path,
                    payloadless_sha256=(
                        future_wna16_typed_slot_payloadless_execution_sha256
                    ),
                    native_json=(
                        future_wna16_typed_slot_kernel_variant_execution_native_path
                    ),
                    native_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_native_sha256
                    ),
                )
            )
            + "\n",
        )
        future_wna16_typed_slot_kernel_variant_execution_sha256 = hashlib.sha256(
            (root / future_wna16_typed_slot_kernel_variant_execution_path).read_bytes()
        ).hexdigest()
        _write(
            root / future_wna16_typed_slot_kernel_variant_useful_consumer_path,
            json.dumps(
                _future_wna16_useful_consumer_payload(
                    execution_json=(
                        future_wna16_typed_slot_kernel_variant_execution_path
                    ),
                    execution_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_sha256
                    ),
                    native_timing_json=(
                        future_wna16_typed_slot_kernel_variant_execution_native_path
                    ),
                    native_timing_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_native_sha256
                    ),
                    native_stub_json=(
                        future_wna16_typed_slot_kernel_variant_execution_native_stub_path
                    ),
                    native_stub_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_native_stub_sha256
                    ),
                )
            )
            + "\n",
        )
        future_wna16_typed_slot_kernel_variant_useful_consumer_sha256 = (
            hashlib.sha256(
                (
                    root / future_wna16_typed_slot_kernel_variant_useful_consumer_path
                ).read_bytes()
            ).hexdigest()
        )
        _write(
            root
            / future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_path,
            json.dumps(
                _future_wna16_payloadless_useful_execution_payload(
                    useful_consumer_json=(
                        future_wna16_typed_slot_kernel_variant_useful_consumer_path
                    ),
                    useful_consumer_sha256=(
                        future_wna16_typed_slot_kernel_variant_useful_consumer_sha256
                    ),
                    execution_json=(
                        future_wna16_typed_slot_kernel_variant_execution_path
                    ),
                    execution_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_sha256
                    ),
                    native_timing_json=(
                        future_wna16_typed_slot_kernel_variant_execution_native_path
                    ),
                    native_timing_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_native_sha256
                    ),
                    native_stub_json=(
                        future_wna16_typed_slot_kernel_variant_execution_native_stub_path
                    ),
                    native_stub_sha256=(
                        future_wna16_typed_slot_kernel_variant_execution_native_stub_sha256
                    ),
                )
            )
            + "\n",
        )
        repeat_payload = _future_wna16_payloadless_useful_repeat_benchmark_payload(
            harness_json=future_wna16_typed_slot_payloadless_benchmark_path,
            harness_sha256=future_wna16_typed_slot_payloadless_benchmark_sha256,
            native_timing_seed_json=(
                future_wna16_typed_slot_kernel_variant_execution_native_path
            ),
            native_timing_seed_sha256=(
                future_wna16_typed_slot_kernel_variant_execution_native_sha256
            ),
            repeat_output_prefix=name,
        )
        repeat_output_sha256s = []
        for idx, repeat_json in enumerate(repeat_payload["repeat_output_jsons"]):
            repeat_child = {
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
                "passed": True,
                "failures": [],
                "timing_stub_ready": True,
                "native_stub_requested": True,
                "native_stub_executed": True,
                "native_stub_passed": True,
                "native_stub_host_wall_ms": repeat_payload[
                    "native_stub_host_wall_ms_values"
                ][idx],
                "native_stub_output_json": (
                    future_wna16_typed_slot_kernel_variant_execution_native_stub_path
                ),
                "native_stub_output_sha256": (
                    future_wna16_typed_slot_kernel_variant_execution_native_stub_sha256
                ),
                "source_count": 128,
                "row_count": 520,
                "row_ok_count": 520,
                "field_names": list(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS),
                "field_read_hashes": repeat_payload["field_read_hashes"],
                "payload_bytes": 0,
                "payload_deref_allowed": False,
                "kernel_arg_pass_allowed": False,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
                "uses_current_wna16_args": False,
                "passes_current_wna16_args": False,
                "current_wna16_arg_compatible": False,
                "requires_wna16_arg_reinterpretation": False,
                "measures_native_stub_host_wall_time": True,
                "measures_tpot": False,
                "measures_vllm_latency": False,
                "wna16_benchmark_ready": False,
            }
            _write(root / str(repeat_json), json.dumps(repeat_child) + "\n")
            repeat_output_sha256s.append(
                hashlib.sha256((root / str(repeat_json)).read_bytes()).hexdigest()
            )
        repeat_payload["repeat_output_sha256s"] = repeat_output_sha256s
        _write(
            root / future_wna16_typed_slot_payloadless_useful_repeat_benchmark_path,
            json.dumps(repeat_payload) + "\n",
        )
        future_wna16_typed_slot_payloadless_useful_repeat_benchmark_sha256 = (
            hashlib.sha256(
                (
                    root
                    / future_wna16_typed_slot_payloadless_useful_repeat_benchmark_path
                ).read_bytes()
            ).hexdigest()
        )
        _write(
            root / future_wna16_typed_slot_payloadless_useful_runtime_ablation_path,
            json.dumps(
                _future_wna16_payloadless_useful_runtime_ablation_payload(
                    repeat_benchmark_json=(
                        future_wna16_typed_slot_payloadless_useful_repeat_benchmark_path
                    ),
                    repeat_benchmark_sha256=(
                        future_wna16_typed_slot_payloadless_useful_repeat_benchmark_sha256
                    ),
                )
            )
            + "\n",
        )
        future_wna16_typed_slot_payloadless_useful_runtime_ablation_sha256 = (
            hashlib.sha256(
                (
                    root / future_wna16_typed_slot_payloadless_useful_runtime_ablation_path
                ).read_bytes()
            ).hexdigest()
        )
        _write(
            root
            / future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_path,
            json.dumps(
                _future_wna16_payloadless_useful_production_like_timing_gate_payload(
                    runtime_ablation_json=(
                        future_wna16_typed_slot_payloadless_useful_runtime_ablation_path
                    ),
                    runtime_ablation_sha256=(
                        future_wna16_typed_slot_payloadless_useful_runtime_ablation_sha256
                    ),
                )
            )
            + "\n",
        )
        _write(
            root / payload_cache_producer_state_native_canary_path,
            json.dumps(_payload_cache_producer_state_native_canary_payload()) + "\n",
        )
        _write(
            root / payload_cache_shifted_issue_runtime_shadow_gate_path,
            json.dumps(_payload_cache_shifted_issue_runtime_shadow_gate_payload())
            + "\n",
        )
        _write(
            root / payload_cache_packet_export_manifest_path,
            json.dumps(_payload_cache_packet_export_manifest_payload()) + "\n",
        )
        for index in range(32):
            _write(root / f"reports/packet_{index:04d}.json", "{}\n")
        _write(
            root / payload_cache_producer_state_nonempty_issue_stub_path,
            json.dumps(_payload_cache_producer_state_nonempty_issue_stub_payload())
            + "\n",
        )
        _write(
            root / payload_cache_producer_state_stream_native_canary_path,
            json.dumps(_payload_cache_producer_state_stream_native_canary_payload())
            + "\n",
        )
        _write(
            root / payload_cache_producer_state_packet_stream_native_canary_path,
            json.dumps(
                _payload_cache_producer_state_packet_stream_native_canary_payload()
            )
            + "\n",
        )
        _write(
            root / payload_cache_producer_state_packet_stream_native_canary_check_path,
            json.dumps(
                _payload_cache_producer_state_packet_stream_native_canary_check_payload()
            )
            + "\n",
        )
        _write(
            root / payload_cache_producer_state_stream_online_contract_path,
            json.dumps(_payload_cache_producer_state_stream_online_contract_payload())
            + "\n",
        )
        _write(
            root / payload_cache_producer_state_inprocess_native_session_online_contract_path,
            json.dumps(
                _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
            )
            + "\n",
        )
        _write(
            root / payload_cache_stream_producer_production_ab_bridge_path,
            json.dumps(_payload_cache_stream_producer_production_ab_bridge_payload())
            + "\n",
        )
        _write(
            root / payload_cache_stream_producer_production_ab_bridge_check_path,
            json.dumps(
                _payload_cache_stream_producer_production_ab_bridge_check_payload()
            )
            + "\n",
        )
        _write(
            root / payload_cache_online_native_producer_boundary_gap_path,
            json.dumps(_payload_cache_online_native_producer_boundary_gap_payload())
            + "\n",
        )
        _write(
            root / payload_cache_vllm_replay_visible_native_producer_contract_path,
            json.dumps(_vllm_replay_visible_native_producer_payload()) + "\n",
        )
        _write(
            root
            / payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_path,
            json.dumps(
                count_ptr_native_producer_checker.check_contract(
                    _vllm_replay_visible_native_producer_payload()
                )
            )
            + "\n",
        )
        _write(
            root / payload_cache_vllm_replay_visible_count_ptr_readiness_path,
            json.dumps(_vllm_replay_visible_count_ptr_readiness_payload()) + "\n",
        )
        _write(
            root / payload_cache_manager_useful_work_ab_gate_path,
            json.dumps(_payload_cache_manager_useful_work_ab_gate_payload()) + "\n",
        )
        _write(
            root / payload_cache_manager_production_ab_preflight_path,
            json.dumps(
                _payload_cache_manager_production_ab_preflight_payload(
                    manager_gate_json=payload_cache_manager_useful_work_ab_gate_path,
                )
            )
            + "\n",
        )
        for mirror_field, runner_path in (
            ("descriptor_ptr", online_merged_arg_slot_descriptor_ptr_runner_path),
            (
                "packed_weight_descriptor",
                online_merged_arg_slot_packed_weight_runner_path,
            ),
            ("aux_metadata_handle", online_merged_arg_slot_aux_metadata_runner_path),
        ):
            stub_path = (
                online_merged_arg_slot_aux_metadata_canary_path
                if mirror_field == "aux_metadata_handle"
                else online_merged_arg_slot_packed_weight_canary_path
                if mirror_field == "packed_weight_descriptor"
                else online_merged_arg_slot_descriptor_ptr_canary_path
                if mirror_field == "descriptor_ptr"
                else (
                    f"reports/{name}_online_merged_future_native_arg_slot_"
                    f"{mirror_field}_canary.json"
                )
            )
            _write(
                root / stub_path,
                json.dumps(
                    _online_merged_arg_slot_multiprogram_canary_payload(
                        online_merged_arg_slot_multiprogram_input_path,
                        mirror_field=mirror_field,
                    )
                )
                + "\n",
            )
            _write(
                root / runner_path,
                json.dumps(
                    _online_merged_arg_slot_multiprogram_runner_payload(
                        online_merged_arg_slot_multiprogram_input_path,
                        stub_path,
                        mirror_field=mirror_field,
                    )
                )
                + "\n",
            )
        for mirror_field, canary_path in (
            ("descriptor_ptr", future_kernel_args_descriptor_ptr_canary_path),
            ("packed_weight_descriptor", future_kernel_args_packed_weight_canary_path),
            ("aux_metadata_handle", future_kernel_args_aux_metadata_canary_path),
        ):
            _write(
                root / canary_path,
                json.dumps(_runner_future_kernel_args_summary(mirror_field)) + "\n",
            )
        _write(
            root / future_kernel_args_compatible_path_canary_path,
            json.dumps(_runner_future_kernel_args_compatible_path_summary()) + "\n",
        )
        for canary_path in (
            future_kernel_args_compatible_path_artifact_check_path,
            future_kernel_args_field_refresh_flatten_check_path,
            future_kernel_args_field_refresh_artifact_check_path,
        ):
            _write(
                root / canary_path,
                json.dumps({"passed": True, "failures": []}) + "\n",
            )
        for mirror_field, canary_path in (
            ("scale_metadata_handle", future_kernel_native_consumer_scale_canary_path),
            ("descriptor_ptr", future_kernel_native_consumer_descriptor_ptr_canary_path),
            (
                "packed_weight_descriptor",
                future_kernel_native_consumer_packed_weight_canary_path,
            ),
            ("aux_metadata_handle", future_kernel_native_consumer_aux_metadata_canary_path),
        ):
            _write(
                root / canary_path,
                json.dumps(_runner_future_kernel_native_consumer_summary(mirror_field))
                + "\n",
            )
        _write(
            root / future_kernel_native_consumer_launch_scale_canary_path,
            json.dumps(
                _runner_future_kernel_native_launch_consumer_summary(
                    "scale_metadata_handle"
                )
            )
            + "\n",
        )
    gate_path = f"configs/runtime/{name}.yaml"
    metadata_lines = ""
    if canary is not None:
        metadata_lines += f"canary: {str(canary).lower()}\n"
    if lab_default is not None:
        metadata_lines += f"lab_default: {str(lab_default).lower()}\n"
    live_block_reason = (
        "kernel_side_typed_consumer_kernel_arg_pass_disabled"
        if live_connected_readonly
        else "kernel_side_typed_consumer_live_disabled"
    )
    _write(
        root / gate_path,
        "schema_version: 1\n"
        f"{metadata_lines}"
        + (
            "schema_artifacts:\n"
            f"  kernel_side_typed_consumer_schema_yaml: {schema_path}\n"
            if include_schema_artifact
            else ""
        )
        +
        "contract:\n"
        f"  kernel_side_typed_consumer_object_required: {str(typed_consumer_required).lower()}\n"
        f"  kernel_arg_handoff_live_toggle_enabled_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_arg_handoff_live_noop_integration_enabled_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_arg_handoff_live_noop_integration_consumer_connected_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_arg_handoff_live_consumer_adapter_enabled_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_arg_handoff_live_consumer_adapter_consumer_connected_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_side_consumer_schema_adapter_consumer_connected_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_side_consumer_schema_adapter_live_enabled_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_side_consumer_schema_adapter_live_eligible_required: {str(live_connected_readonly).lower()}\n"
        "  kernel_side_typed_consumer_object_payload_bytes_required: 0\n"
        "  kernel_side_typed_consumer_object_passed_to_kernel_required: false\n"
        "  kernel_side_typed_consumer_object_changes_kernel_launch_args_required: false\n"
        f"  kernel_side_typed_consumer_object_consumer_connected_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_side_typed_consumer_object_live_enabled_required: {str(live_connected_readonly).lower()}\n"
        f"  kernel_side_typed_consumer_object_live_eligible_required: {str(live_connected_readonly).lower()}\n"
        "  kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args_required: false\n"
        f"  kernel_side_typed_consumer_object_block_reason: {live_block_reason}\n"
        "  kernel_side_typed_row_consumer_path_required: true\n"
        "  kernel_side_typed_row_consumer_path_mode: readonly_typed_row_consumer_path\n"
        "  kernel_side_typed_row_consumer_path_name: premap_kernel_side_typed_consumer_path_v1\n"
        "  kernel_side_typed_row_consumer_path_source: vllm_prelaunch_prepared_handle_table\n"
        "  kernel_side_typed_row_consumer_path_payload_bytes_required: 0\n"
        "  kernel_side_typed_row_consumer_path_passed_to_kernel_required: false\n"
        "  kernel_side_typed_row_consumer_path_changes_kernel_launch_args_required: false\n"
        "  kernel_side_typed_row_consumer_path_current_wna16_arg_compatible_required: false\n"
        "  future_kernel_consumer_args_required: true\n"
        "  future_kernel_consumer_args_name: premap_future_kernel_side_consumer_args_v1\n"
        "  future_kernel_consumer_args_mode: readonly_future_kernel_consumer_args\n"
        "  future_kernel_consumer_args_source: premap_kernel_side_typed_consumer_launch_envelope_v1\n"
        "  future_kernel_consumer_args_payload_bytes_required: 0\n"
        "  future_kernel_consumer_args_passed_to_kernel_required: false\n"
        "  future_kernel_consumer_args_changes_kernel_launch_args_required: false\n"
        "  future_kernel_consumer_args_current_wna16_arg_compatible_required: false\n"
        "  future_kernel_consumer_args_single_field_mirror_required: true\n"
        "  future_kernel_consumer_args_single_field_mirror_field: scale_metadata_handle\n"
        "  future_kernel_consumer_args_total_mirror_coverage_required: true\n"
        "  future_kernel_args_compatible_consumer_path_required: true\n"
        "  future_kernel_native_dispatch_consumer_full_table_required: true\n"
        "  future_kernel_native_dispatch_ptr_consumer_required: true\n"
        "  future_kernel_native_dispatch_consumer_program_iteration_required: true\n"
        "  future_kernel_native_dispatch_consumer_row_assignment_formula: row_offset + program_id * rows_per_program + lane_id\n"
        "  consumer_program_view_required: true\n"
        "  consumer_program_view_row_assignment_formula: program_id * rows_per_program + lane_id + row_offset\n"
        "  consumer_program_view_ptr_required: true\n"
        "  request_launch_all_handle_fields_required: true\n"
        "  request_launch_ptr_all_handle_fields_required: true\n"
        "  wna16_adjacent_typed_slot_required: true\n"
        "  wna16_adjacent_typed_slot_mode: readonly_wna16_adjacent_typed_consumer_slot\n"
        "  wna16_adjacent_typed_slot_source: premap_future_kernel_native_consumer_endpoint_ptr_abi_v1\n"
        "  wna16_adjacent_typed_slot_payload_bytes_required: 0\n"
        "  wna16_adjacent_typed_slot_passed_to_kernel_required: false\n"
        "  wna16_adjacent_typed_slot_changes_kernel_launch_args_required: false\n"
        "  wna16_adjacent_typed_slot_current_wna16_arg_compatible_required: false\n"
        "  wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation_required: false\n"
        "  wna16_adjacent_typed_slot_explicit_typed_abi_slot_required: true\n"
        "  wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot_required: false\n"
        "  future_kernel_native_arg_slot_online_total_mirror_coverage_required: true\n"
        "  future_wna16_single_field_handoff_all_fields_required: true\n"
        "  future_wna16_single_field_handoff_all_fields_min_source_count: 128\n"
        "  future_wna16_typed_slot_fourth_field_handoff_canary_required: true\n"
        "  future_wna16_typed_slot_fourth_field_handoff_canary_field: descriptor_ptr\n"
        "  future_wna16_typed_slot_fourth_field_handoff_canary_min_source_count: 128\n"
        "  future_wna16_typed_slot_all_four_field_consumer_required: true\n"
        "  future_wna16_typed_slot_all_four_field_consumer_min_source_count: 128\n"
        "  future_wna16_kernel_side_typed_consumer_path_required: true\n"
        "  future_wna16_kernel_side_typed_consumer_path_min_source_count: 128\n"
        "  future_wna16_typed_slot_payloadless_execution_required: true\n"
        "  future_wna16_typed_slot_payloadless_execution_min_source_count: 128\n"
        "  future_wna16_typed_slot_kernel_variant_execution_required: true\n"
        "  future_wna16_typed_slot_kernel_variant_execution_min_source_count: 128\n"
        "  future_wna16_typed_slot_kernel_variant_useful_consumer_required: true\n"
        "  future_wna16_typed_slot_kernel_variant_useful_consumer_min_source_count: 128\n"
        "  future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_required: true\n"
        "  future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_min_source_count: 128\n"
        "  future_wna16_typed_slot_payloadless_useful_repeat_benchmark_required: true\n"
        "  future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_source_count: 128\n"
        "  future_wna16_typed_slot_payloadless_useful_repeat_benchmark_min_repeat_count: 3\n"
        "  future_wna16_typed_slot_payloadless_useful_runtime_ablation_required: true\n"
        "  future_wna16_typed_slot_payloadless_useful_runtime_ablation_min_source_count: 128\n"
        "  future_wna16_typed_slot_payloadless_useful_runtime_ablation_min_repeat_count: 3\n"
        "  future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_required: true\n"
        "  future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_min_source_count: 128\n"
        "  future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_min_repeat_count: 3\n"
        "  payload_cache_manager_useful_work_ab_gate_required: true\n"
        "  payload_cache_manager_production_ab_preflight_required: true\n"
        "  payload_cache_manager_production_ab_preflight_max_envelope_overhead_ratio: 0.05\n"
        "  wna16_side_consumer_variant_execution_required: true\n"
        "  wna16_side_consumer_variant_execution_min_source_count: 128\n"
        "  single_field_handle_handoff_canary_required: true\n"
        "  single_field_handle_handoff_canary_mode: readonly_single_field_handle_handoff_canary\n"
        "  single_field_handle_handoff_canary_field: scale_metadata_handle\n"
        "  single_field_handle_handoff_canary_source: semantic_handle_table\n"
        "  single_field_handle_handoff_canary_mirror_mode: readonly_scale_metadata_handle_mirror\n"
        "  single_field_handle_handoff_canary_mirror_field: scale_metadata_handle\n"
        "  single_field_handle_handoff_canary_mirror_source: semantic_handle_table\n"
        "  single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible_required: true\n"
        "  single_field_handle_handoff_canary_current_wna16_arg_compatible_required: false\n"
        "  single_field_handle_handoff_canary_block_reason: single_field_handoff_live_disabled\n"
        "  single_field_handle_handoff_canary_payload_bytes_required: 0\n"
        "  single_field_handle_handoff_canary_ready_credit_required: false\n"
        "  single_field_handle_handoff_canary_passed_to_kernel_required: false\n"
        "  single_field_handle_handoff_canary_changes_kernel_launch_args_required: false\n"
        "  single_field_handle_handoff_canary_live_enabled_required: false\n"
        "  single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required: false\n"
        "  aux_metadata_single_field_handle_handoff_canary_smoke_required: true\n"
        "  aux_metadata_single_field_handle_handoff_canary_mode: readonly_single_field_handle_handoff_canary\n"
        "  aux_metadata_single_field_handle_handoff_canary_field: aux_metadata_handle\n"
        "  aux_metadata_single_field_handle_handoff_canary_source: semantic_handle_table\n"
        "  aux_metadata_single_field_handle_handoff_canary_mirror_mode: readonly_aux_metadata_handle_mirror\n"
        "  aux_metadata_single_field_handle_handoff_canary_mirror_field: aux_metadata_handle\n"
        "  aux_metadata_single_field_handle_handoff_canary_mirror_source: semantic_handle_table\n"
        "  aux_metadata_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible_required: true\n"
        "  aux_metadata_single_field_handle_handoff_canary_current_wna16_arg_compatible_required: false\n"
        "  aux_metadata_single_field_handle_handoff_canary_block_reason: single_field_handoff_live_disabled\n"
        "  aux_metadata_single_field_handle_handoff_canary_payload_bytes_required: 0\n"
        "  aux_metadata_single_field_handle_handoff_canary_ready_credit_required: false\n"
        "  aux_metadata_single_field_handle_handoff_canary_passed_to_kernel_required: false\n"
        "  aux_metadata_single_field_handle_handoff_canary_changes_kernel_launch_args_required: false\n"
        "  aux_metadata_single_field_handle_handoff_canary_live_enabled_required: false\n"
        "  aux_metadata_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required: false\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_smoke_required: true\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_field: descriptor_ptr\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_source: semantic_handle_table\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_payload_bytes_required: 0\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_ready_credit_required: false\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_passed_to_kernel_required: false\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_changes_kernel_launch_args_required: false\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_live_enabled_required: false\n"
        "  descriptor_ptr_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required: false\n"
        "  packed_weight_single_field_handle_handoff_canary_smoke_required: true\n"
        "  packed_weight_single_field_handle_handoff_canary_field: packed_weight_descriptor\n"
        "  packed_weight_single_field_handle_handoff_canary_source: semantic_handle_table\n"
        "  packed_weight_single_field_handle_handoff_canary_payload_bytes_required: 0\n"
        "  packed_weight_single_field_handle_handoff_canary_ready_credit_required: false\n"
        "  packed_weight_single_field_handle_handoff_canary_passed_to_kernel_required: false\n"
        "  packed_weight_single_field_handle_handoff_canary_changes_kernel_launch_args_required: false\n"
        "  packed_weight_single_field_handle_handoff_canary_live_enabled_required: false\n"
        "  packed_weight_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args_required: false\n"
        "  native_typed_consumer_bridge_required: true\n"
        "  native_typed_consumer_bridge_payload_bytes_required: 0\n"
        "  native_typed_consumer_bridge_ready_credit_required: false\n"
        "  native_typed_consumer_bridge_changes_router_required: false\n"
        "  native_typed_consumer_bridge_changes_descriptor_order_required: false\n"
        "  native_typed_consumer_bridge_passed_to_kernel_required: false\n"
        "  native_typed_consumer_bridge_changes_kernel_launch_args_required: false\n"
        "  native_stub_online_invocation_canary_required: true\n"
        "  native_stub_online_invocation_canary_mode: readonly_native_stub_online_invocation_canary\n"
        "  native_stub_online_invocation_canary_block_reason: native_stub_live_disabled\n"
        "  native_stub_online_invocation_canary_payload_bytes_required: 0\n"
        "  native_stub_online_invocation_canary_ready_credit_required: false\n"
        "  native_stub_online_invocation_canary_changes_router_required: false\n"
        "  native_stub_online_invocation_canary_changes_descriptor_order_required: false\n"
        "  native_stub_online_invocation_canary_passed_to_kernel_required: false\n"
        "  native_stub_online_invocation_canary_changes_kernel_launch_args_required: false\n"
        "  native_stub_online_invocation_canary_native_stub_invoked_required: false\n"
        "  native_stub_online_invocation_canary_blocked_required: true\n"
        "  native_typed_consumer_stub_canary_required: true\n"
        "  native_typed_consumer_stub_payload_bytes_required: 0\n"
        "  native_typed_consumer_stub_passed_to_kernel_required: false\n"
        "  native_typed_consumer_stub_changes_kernel_launch_args_required: false\n"
        "evidence_paths:\n"
        f"  gate_json: {evidence_path}\n"
        + (
            "  strict_kernel_side_typed_consumer_object_128_gate_json: "
            f"{lab_gate_path}\n"
            "  strict_kernel_side_typed_consumer_object_128_selfcheck_json: "
            f"{lab_selfcheck_path}\n"
            "  strict_kernel_side_typed_row_consumer_path_128_gate_json: "
            f"{typed_row_path}\n"
            "  strict_single_field_handle_handoff_canary_128_gate_json: "
            f"{single_field_canary_path}\n"
            "  aux_metadata_single_field_handle_handoff_canary_smoke_json: "
            f"{aux_metadata_single_field_canary_path}\n"
            "  descriptor_ptr_single_field_handle_handoff_canary_smoke_json: "
            f"{descriptor_ptr_single_field_canary_path}\n"
            "  packed_weight_single_field_handle_handoff_canary_smoke_json: "
            f"{packed_weight_single_field_canary_path}\n"
            "  strict_live_connected_readonly_128_gate_json: "
            f"{lab_live_connected_path}\n"
            "  strict_native_typed_consumer_bridge_128_gate_json: "
            f"{lab_native_bridge_path}\n"
            "  native_typed_consumer_bridge_smoke_json: "
            f"{native_bridge_path}\n"
            "  strict_native_stub_online_invocation_canary_128_gate_json: "
            f"{lab_native_stub_path}\n"
            "  native_typed_consumer_stub_gpu1_canary_json: "
            f"{native_typed_stub_path}\n"
            "  native_typed_consumer_stub_endpoint_ptr_canary_json: "
            f"{native_typed_endpoint_ptr_stub_path}\n"
            "  native_typed_consumer_bridge_input_json: "
            f"{native_bridge_input_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_canary_json: "
            f"{native_online_stub_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json: "
            f"{native_online_endpoint_ptr_stub_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json: "
            f"{native_online_request_ptr_stub_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json: "
            f"{native_online_request_launch_stub_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json: "
            f"{native_online_request_launch_ptr_stub_path}\n"
            "  native_typed_consumer_online_prelaunch_input_json: "
            f"{native_online_input_path}\n"
            "  native_typed_consumer_online_prelaunch_export_performance_json: "
            f"{native_online_perf_path}\n"
            "  native_typed_consumer_online_prelaunch_canary_runner_json: "
            f"{native_online_runner_32_path}\n"
            "  future_kernel_native_consumer_online_runner_16_128export_json: "
            f"{native_online_runner_32_path}\n"
            "  future_kernel_native_consumer_online_artifact_check_16_128export_json: "
            f"{native_online_artifact_check_32_path}\n"
            "  future_kernel_native_launch_consumer_online_runner_16_128export_json: "
            f"{native_online_runner_32_path}\n"
            "  future_kernel_native_launch_consumer_online_artifact_check_16_128export_json: "
            f"{native_online_artifact_check_32_path}\n"
            "  future_kernel_native_dispatch_consumer_online_runner_16_128export_json: "
            f"{native_online_runner_32_path}\n"
            "  future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json: "
            f"{native_online_artifact_check_32_path}\n"
            "  future_kernel_native_dispatch_consumer_online_runner_32_128export_json: "
            f"{native_online_runner_32_path}\n"
            "  future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json: "
            f"{native_online_artifact_check_32_path}\n"
            "  future_kernel_native_dispatch_ptr_standalone_canary_json: "
            f"{standalone_dispatch_ptr_canary_path}\n"
            "  future_kernel_native_arg_slot_standalone_canary_json: "
            f"{standalone_arg_slot_canary_path}\n"
            "  future_kernel_native_arg_slot_aux_metadata_mirror_canary_json: "
            f"{standalone_arg_slot_aux_metadata_canary_path}\n"
            "  future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json: "
            f"{standalone_arg_slot_descriptor_ptr_canary_path}\n"
            "  future_kernel_native_arg_slot_packed_weight_mirror_canary_json: "
            f"{standalone_arg_slot_packed_weight_canary_path}\n"
            "  future_kernel_native_arg_slot_multiprogram_canary_json: "
            f"{standalone_arg_slot_multiprogram_canary_path}\n"
            "  future_kernel_native_arg_slot_online_merged_multiprogram_runner_json: "
            f"{online_merged_arg_slot_multiprogram_runner_path}\n"
            "  future_kernel_native_arg_slot_online_merged_multiprogram_canary_json: "
            f"{online_merged_arg_slot_multiprogram_canary_path}\n"
            "  future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_canary_json: "
            f"{online_merged_arg_slot_aux_metadata_canary_path}\n"
            "  future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json: "
            f"{online_merged_arg_slot_aux_metadata_runner_path}\n"
            "  future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_canary_json: "
            f"{online_merged_arg_slot_descriptor_ptr_canary_path}\n"
            "  future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json: "
            f"{online_merged_arg_slot_descriptor_ptr_runner_path}\n"
            "  future_kernel_native_arg_slot_online_merged_packed_weight_mirror_canary_json: "
            f"{online_merged_arg_slot_packed_weight_canary_path}\n"
            "  future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json: "
            f"{online_merged_arg_slot_packed_weight_runner_path}\n"
            "  future_kernel_wna16_adjacent_typed_slot_canary_json: "
            f"{online_merged_wna16_adjacent_typed_slot_runner_path}\n"
            "  future_kernel_wna16_adjacent_typed_slot_stub_json: "
            f"{online_merged_wna16_adjacent_typed_slot_stub_path}\n"
            "  future_wna16_single_field_handoff_all_fields_128strict_summary_json: "
            f"{future_wna16_single_field_handoff_all_fields_summary_path}\n"
            "  future_wna16_typed_slot_fourth_field_handoff_canary_json: "
            f"{future_wna16_typed_slot_fourth_field_handoff_canary_path}\n"
            "  future_wna16_typed_slot_all_four_field_consumer_json: "
            f"{future_wna16_typed_slot_all_four_field_consumer_path}\n"
            "  future_wna16_kernel_side_typed_consumer_path_json: "
            f"{future_wna16_kernel_side_typed_consumer_path}\n"
            "  future_wna16_typed_slot_payloadless_execution_json: "
            f"{future_wna16_typed_slot_payloadless_execution_path}\n"
            "  future_wna16_typed_slot_kernel_variant_execution_json: "
            f"{future_wna16_typed_slot_kernel_variant_execution_path}\n"
            "  future_wna16_typed_slot_kernel_variant_useful_consumer_json: "
            f"{future_wna16_typed_slot_kernel_variant_useful_consumer_path}\n"
            "  future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json: "
            f"{future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_path}\n"
            "  future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json: "
            f"{future_wna16_typed_slot_payloadless_useful_repeat_benchmark_path}\n"
            "  future_wna16_typed_slot_payloadless_useful_runtime_ablation_json: "
            f"{future_wna16_typed_slot_payloadless_useful_runtime_ablation_path}\n"
            "  future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_json: "
            f"{future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_path}\n"
            "  future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json: "
            f"{future_native_arg_slot_all_field_entry_args_ptr_sweep_path}\n"
            "  future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json: "
            f"{future_native_arg_slot_all_field_entry_args_ptr_sweep_check_path}\n"
            "  wna16_side_consumer_variant_execution_128strict_runner_json: "
            f"{wna16_side_consumer_variant_execution_runner_path}\n"
            "  payload_cache_producer_state_native_canary_json: "
            f"{payload_cache_producer_state_native_canary_path}\n"
            "  payload_cache_shifted_issue_runtime_shadow_gate_json: "
            f"{payload_cache_shifted_issue_runtime_shadow_gate_path}\n"
            "  payload_cache_packet_export_manifest_json: "
            f"{payload_cache_packet_export_manifest_path}\n"
            "  payload_cache_producer_state_online_nonempty_issue_canary_json: "
            f"{payload_cache_producer_state_native_canary_path}\n"
            "  payload_cache_producer_state_nonempty_issue_stub_json: "
            f"{payload_cache_producer_state_nonempty_issue_stub_path}\n"
            "  payload_cache_producer_state_stream_native_canary_json: "
            f"{payload_cache_producer_state_stream_native_canary_path}\n"
            "  payload_cache_producer_state_packet_stream_native_canary_json: "
            f"{payload_cache_producer_state_packet_stream_native_canary_path}\n"
            "  payload_cache_producer_state_packet_stream_native_canary_check_json: "
            f"{payload_cache_producer_state_packet_stream_native_canary_check_path}\n"
            "  payload_cache_producer_state_inprocess_native_session_online_contract_json: "
            f"{payload_cache_producer_state_inprocess_native_session_online_contract_path}\n"
            "  payload_cache_online_native_producer_boundary_gap_json: "
            f"{payload_cache_online_native_producer_boundary_gap_path}\n"
            "  payload_cache_demand_hit_shadow_publication_gate_json: "
            f"{payload_cache_demand_hit_shadow_publication_gate_path}\n"
            "  payload_cache_consumer_visible_hit_blocked_gate_json: "
            f"{payload_cache_consumer_visible_hit_blocked_gate_path}\n"
            "  payload_cache_vllm_replay_visible_native_producer_contract_json: "
            f"{payload_cache_vllm_replay_visible_native_producer_contract_path}\n"
            "  payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json: "
            f"{payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_path}\n"
            "  payload_cache_vllm_replay_visible_count_ptr_readiness_json: "
            f"{payload_cache_vllm_replay_visible_count_ptr_readiness_path}\n"
            "  payload_cache_manager_useful_work_ab_gate_json: "
            f"{payload_cache_manager_useful_work_ab_gate_path}\n"
            "  payload_cache_manager_production_ab_preflight_json: "
            f"{payload_cache_manager_production_ab_preflight_path}\n"
            "  future_kernel_wna16_adjacent_typed_slot_standalone_canary_json: "
            f"{standalone_wna16_adjacent_typed_slot_canary_path}\n"
            "  prelaunch_pointer_source_observer_check_json: "
            f"{prelaunch_pointer_source_observer_check_path}\n"
            "  readonly_live_trusted_refs_check_json: "
            f"{readonly_live_trusted_refs_check_path}\n"
            "diagnostic_evidence_paths:\n"
            "  payload_cache_producer_state_stream_online_contract_json: "
            f"{payload_cache_producer_state_stream_online_contract_path}\n"
            "  payload_cache_stream_producer_production_ab_bridge_json: "
            f"{payload_cache_stream_producer_production_ab_bridge_path}\n"
            "  payload_cache_stream_producer_production_ab_bridge_check_json: "
            f"{payload_cache_stream_producer_production_ab_bridge_check_path}\n"
            "optional_evidence_paths:\n"
            "  future_kernel_args_aux_metadata_mirror_canary_json: "
            f"{future_kernel_args_aux_metadata_canary_path}\n"
            "  future_kernel_args_compatible_path_16_128export_artifact_check_json: "
            f"{future_kernel_args_compatible_path_artifact_check_path}\n"
            "  future_kernel_args_compatible_path_canary_json: "
            f"{future_kernel_args_compatible_path_canary_path}\n"
            "  future_kernel_args_descriptor_ptr_mirror_canary_json: "
            f"{future_kernel_args_descriptor_ptr_canary_path}\n"
            "  future_kernel_args_field_refresh_16_128export_artifact_check_json: "
            f"{future_kernel_args_field_refresh_artifact_check_path}\n"
            "  future_kernel_args_field_refresh_flatten_check_json: "
            f"{future_kernel_args_field_refresh_flatten_check_path}\n"
            "  future_kernel_args_packed_weight_mirror_canary_json: "
            f"{future_kernel_args_packed_weight_canary_path}\n"
            "  future_kernel_native_consumer_aux_metadata_mirror_canary_json: "
            f"{future_kernel_native_consumer_aux_metadata_canary_path}\n"
            "  future_kernel_native_consumer_descriptor_ptr_mirror_canary_json: "
            f"{future_kernel_native_consumer_descriptor_ptr_canary_path}\n"
            "  future_kernel_native_consumer_launch_scale_mirror_canary_json: "
            f"{future_kernel_native_consumer_launch_scale_canary_path}\n"
            "  future_kernel_native_consumer_packed_weight_mirror_canary_json: "
            f"{future_kernel_native_consumer_packed_weight_canary_path}\n"
            "  future_kernel_native_consumer_scale_mirror_canary_json: "
            f"{future_kernel_native_consumer_scale_canary_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json: "
            f"{native_online_per_field_stub_path}\n"
            if include_lab_evidence
            else ""
        ),
    )
    return gate_path


def _write_trace_config(
    root: Path,
    name: str,
    *,
    readonly_gate_path: str,
    live_enabled: bool = True,
    live_consumer_connected: bool = True,
    kernel_arg_pass_enabled: bool = False,
    real_kernel_arg_mutation_enabled: bool = False,
    single_field_dry_run_enabled: bool = False,
    single_field_live_enabled: bool = False,
    risky_trace_canary: bool = False,
    risky_trace_canary_scope: str | None = None,
) -> str:
    config_path = f"configs/trace/{name}.yaml"
    canary_lines = ""
    if risky_trace_canary:
        canary_lines += "    premap_risky_trace_canary: true\n"
    if risky_trace_canary_scope is not None:
        canary_lines += (
            f"    premap_risky_trace_canary_scope: {risky_trace_canary_scope}\n"
        )
    _write(
        root / config_path,
        "trace:\n"
        "  runtime_shadow:\n"
        "    premap_consumer_require_readonly_gate: true\n"
        f"    premap_consumer_readonly_gate_path: {readonly_gate_path}\n"
        f"    premap_kernel_arg_handoff_live_enabled: {str(live_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_live_consumer_connected: {str(live_consumer_connected).lower()}\n"
        f"    premap_kernel_arg_handoff_kernel_arg_pass_enabled: {str(kernel_arg_pass_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled: {str(real_kernel_arg_mutation_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled: {str(single_field_dry_run_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_single_field_replacement_live_enabled: {str(single_field_live_enabled).lower()}\n"
        f"{canary_lines}",
    )
    return config_path


def test_premap_lab_preflight_accepts_default_readonly_wiring(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["runtime_gate_evidence_scan"]["gate_count"] == 5
    assert result["runtime_gate_evidence_scan"]["evidence_path_count"] == 162
    assert result["default_readonly_gate_required_evidence_check"]["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["passed"] is True
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_field_count"
        ]
        == len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_fields_per_row"
        ]
        == len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
    )

    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_useful_work_units"
        ]
        == 520 * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_expected_useful_work_units"
        ]
        == 520 * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_useful_work_coverage"
        ]
        == 1.0
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_useful_work_kind"
        ]
        == "native_typed_slot_four_field_row_projection"
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_native_consumer_has_useful_work"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_runtime_ablation_gate_ready"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_runtime_ablation_useful_work_units"
        ]
        == 520 * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_production_like_timing_gate_gate_ready"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_production_like_timing_gate_useful_work_units"
        ]
        == 520 * len(_ALL_FIELD_ENTRY_ARGS_PTR_MIRROR_FIELDS)
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_production_like_timing_gate_production_tpot_allowed"
        ]
        is False
    )
    assert summary["default_readonly_gate_path"] == default_gate
    assert summary["default_readonly_gate_sha256"] == hashlib.sha256(
        (tmp_path / default_gate).read_bytes()
    ).hexdigest()
    assert summary["canary_gate_sha256"] == hashlib.sha256(
        (tmp_path / canary_gate).read_bytes()
    ).hexdigest()
    assert summary["default_contract_passed"] is True
    assert summary["prefetch_lab_default_gate_passed"] is True
    assert summary["prefetch_lab_default_gate_decision_status"] == "passed"
    assert summary["prefetch_lab_default_gate_failures"] == []
    assert summary["prefetch_lab_default_gate_id"] == "prefetch_lab_default_gpu1_test"
    assert (
        summary["prefetch_lab_default_full_fetch_decision"]
        == "blocked_by_ready_time_measured_copy"
    )
    assert summary["prefetch_lab_default_full_fetch_passed"] is True
    assert summary["prefetch_lab_default_full_fetch_failures"] == []
    assert summary["prefetch_lab_default_ready_time_report_passed"] is True
    assert summary["prefetch_lab_default_ready_time_allow_full_fetch"] is False
    assert (
        summary["prefetch_lab_default_ready_time_decision_reason"]
        == "full_fetch_threshold_not_met"
    )
    assert summary["prefetch_lab_default_ready_time_threshold_failures"] == [
        "used_per_issued_fetch_below_threshold"
    ]
    assert summary["prefetch_lab_default_ready_time_demand_hit_rate"] == 0.9672
    assert (
        summary["prefetch_lab_default_ready_time_ready_late_miss_rate"]
        == 0.000036
    )
    assert summary["prefetch_lab_default_ready_time_issued_fetch_count"] == 12
    assert summary["prefetch_lab_default_ready_time_used_fetch_count"] == 0
    assert summary["prefetch_lab_default_ready_time_used_per_issued_fetch"] == 0.0
    assert summary["prefetch_lab_default_ready_time_current_deadline_us"] is None
    assert summary["prefetch_lab_default_ready_time_current_lookahead_us"] is None
    assert (
        summary["prefetch_lab_default_ready_time_first_model_passing_deadline_us"]
        is None
    )
    assert (
        summary["prefetch_lab_default_ready_time_first_model_passing_lookahead_us"]
        is None
    )
    assert (
        summary["prefetch_lab_default_ready_time_required_lookahead_slack_us"]
        is None
    )
    assert (
        summary[
            "prefetch_lab_default_ready_time_required_issue_to_demand_lookahead_us"
        ]
        is None
    )
    assert summary["prefetch_lab_default_ready_time_slack_deficit_us"] is None
    assert summary["prefetch_lab_default_ready_time_lookahead_deficit_us"] is None
    assert summary["prefetch_lab_default_ready_time_model_slack_satisfied"] is None
    assert (
        summary["prefetch_lab_default_ready_time_model_lookahead_satisfied"] is None
    )
    assert (
        summary["prefetch_lab_default_ready_time_any_model_route_satisfied"] is None
    )
    assert (
        summary[
            "prefetch_lab_default_ready_time_direct_snapshot_report_present"
        ]
        is True
    )
    assert (
        summary[
            "prefetch_lab_default_ready_time_direct_snapshot_report_passed"
        ]
        is True
    )
    assert (
        summary[
            "prefetch_lab_default_ready_time_direct_snapshot_report_recheck_passed"
        ]
        is True
    )
    assert (
        summary["prefetch_lab_default_ready_time_direct_snapshot_present"] is True
    )
    assert (
        summary["prefetch_lab_default_ready_time_direct_snapshot_runtime_stage"]
        == "online_ready_time_payload_cache_accounting_only"
    )
    assert (
        summary["prefetch_lab_default_ready_time_direct_snapshot_payload_bytes"] == 0
    )
    assert (
        summary[
            "prefetch_lab_default_ready_time_direct_snapshot_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_ready_time_direct_snapshot_changes_kernel_launch_args"
        ]
        is False
    )
    assert summary[
        "prefetch_lab_default_ready_time_direct_snapshot_issue_sources"
    ] == [
        "prelaunch_observed_transition_premap_shadow",
    ]
    assert summary[
        "prefetch_lab_default_payload_cache_runtime_participation_present"
    ] is True
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_participation_stage"]
        == "online_ready_time_payload_cache_runtime_participation_dry_run"
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_participation_status"]
        == "accounting_only_no_used_fetch"
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_participation_consumes_direct_snapshot"
        ]
        is True
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_participation_payload_bytes"]
        == 0
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_participation_ready_credit"]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_participation_real_ready_credit_granted"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_participation_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_participation_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_participation_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_participation_payload_transfer_runtime_enabled"
        ]
        is False
    )
    assert summary[
        "prefetch_lab_default_payload_cache_runtime_participation_issue_sources"
    ] == [
        "prelaunch_observed_transition_premap_shadow",
    ]
    assert summary["prefetch_lab_default_payload_cache_runtime_plan_present"] is True
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_plan_stage"]
        == "payload_cache_runtime_plan_lab_gate_dry_run"
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_plan_status"]
        == "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_plan_consumes_participation"
        ]
        is True
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_plan_live_payload_runtime_enabled"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_plan_planned_issue_count"]
        == 0
    )
    assert summary["prefetch_lab_default_payload_cache_runtime_plan_payload_bytes"] == 0
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_plan_ready_credit"]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_plan_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_plan_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_plan_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_present"]
        is True
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_stage"]
        == "payload_cache_runtime_execution_lab_gate_dry_run"
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_status"]
        == "blocked_by_runtime_plan:"
        "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_plan_status"]
        == summary["prefetch_lab_default_payload_cache_runtime_plan_status"]
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_decision"]
        == "blocked"
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_block_reason"]
        == summary["prefetch_lab_default_payload_cache_runtime_plan_status"]
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_execution_mode"]
        == "payloadless_lab_gate_dry_run"
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_consumes_plan"]
        is True
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_live_payload_runtime_enabled"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_payload_transfer_runtime_enabled"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_issued_payload_count"
        ]
        == 0
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_payload_bytes"]
        == 0
    )
    assert (
        summary["prefetch_lab_default_payload_cache_runtime_execution_ready_credit"]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_real_ready_credit_granted"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_payload_cache_runtime_execution_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert summary["prefetch_lab_default_stream_decision_gate_present"] is True
    assert summary["prefetch_lab_default_stream_decision_gate_passed"] is True
    assert (
        summary["prefetch_lab_default_stream_decision"]
        == "block_full_fetch_insufficient_stream_lookahead"
    )
    assert summary["prefetch_lab_default_stream_full_fetch_runtime_allowed"] is False
    assert (
        summary["prefetch_lab_default_stream_full_fetch_block_reason"]
        == "insufficient_stream_lookahead"
    )
    assert summary["prefetch_lab_default_stream_current_lookahead_us"] == 0.0
    assert summary["prefetch_lab_default_stream_required_lookahead_us"] == 2400000.0
    assert summary["prefetch_lab_default_stream_lookahead_deficit_us"] == 2400000.0
    assert (
        summary["prefetch_lab_default_stream_required_shifted_issue_accounting_enabled"]
        is True
    )
    assert summary["prefetch_lab_default_stream_required_shifted_issue_lead_tokens"] == 32
    assert (
        summary["prefetch_lab_default_stream_required_shifted_issue_clamped_issue_count"]
        == 12
    )
    assert (
        summary[
            "prefetch_lab_default_stream_required_shifted_issue_duplicate_issue_key_count"
        ]
        == 12
    )
    assert (
        summary["prefetch_lab_default_stream_required_shifted_issue_unique_issue_key_count"]
        == 16
    )
    assert (
        summary[
            "prefetch_lab_default_stream_required_shifted_issue_accounted_packet_count"
        ]
        == 28
    )
    assert (
        summary["prefetch_lab_default_stream_required_shifted_issue_invalid_export_count"]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_required_shifted_issue_row_shift_mismatch_count"
        ]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_required_shifted_issue_row_clamp_mismatch_count"
        ]
        == 0
    )
    assert summary["prefetch_lab_default_stream_feasibility_passed"] is True
    assert summary["prefetch_lab_default_stream_current_runtime_satisfies_model"] is False
    assert summary["prefetch_lab_default_stream_max_required_lead_tokens"] == 48
    assert summary["prefetch_lab_default_stream_lead_token_sweep_passed"] is True
    assert (
        summary["prefetch_lab_default_stream_lead_token_sweep_event_timing_mode"]
        == "token_index"
    )
    assert (
        summary["prefetch_lab_default_stream_lead_token_sweep_token_timing_enabled"]
        is True
    )
    assert summary["prefetch_lab_default_stream_first_model_passing_lead_tokens"] == 32
    assert (
        summary["prefetch_lab_default_stream_shifted_issue_replay_contract_passed"]
        is True
    )
    assert summary["prefetch_lab_default_stream_queue_budget_present"] is True
    assert summary["prefetch_lab_default_stream_queue_budget_passed"] is True
    assert summary["prefetch_lab_default_stream_queue_budget_cell_count"] == 1
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_first_model_passing_issue_lead_tokens"
        ]
        == 32
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_first_model_passing_capacity"]
        == 4096
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_first_shifted_issue_accounted_packet_count"
        ]
        == 28
    )
    assert summary["prefetch_lab_default_stream_queue_budget_payload_bytes"] == 0
    assert (
        summary["prefetch_lab_default_stream_queue_budget_runtime_envelope_present"]
        is True
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_runtime_envelope_stage"]
        == "payload_cache_queue_budget_runtime_envelope_lab_gate"
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_runtime_envelope_status"]
        == "model_queue_budget_satisfied_runtime_disabled"
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_runtime_envelope_execution_mode"
        ]
        == "payloadless_queue_budget_lab_gate"
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_runtime_envelope_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_live_payload_stage_present"]
        is True
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_live_payload_stage_status"]
        == (
            "blocked_by_queue_budget_runtime_envelope:"
            "model_queue_budget_satisfied_runtime_disabled"
        )
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_stage_execution_mode"
        ]
        == "payloadless_live_payload_stage_preflight"
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_stage_live_payload_runtime_enabled"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_stage_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_present"
        ]
        is True
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_status"
        ]
        == (
            "blocked_by_live_payload_stage:"
            "blocked_by_queue_budget_runtime_envelope:"
            "model_queue_budget_satisfied_runtime_disabled"
        )
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_execution_mode"
        ]
        == "payloadless_live_payload_runtime_disabled_canary"
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_payload_deref_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_issued_payload_count"]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_live_payload_runtime_enabled"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_payload_transfer_enabled"]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_payload_transfer_runtime_enabled"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_payload_deref_allowed"]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_payload_deref_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_queue_budget_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_ready_before_demand_credit"]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_real_ready_credit_granted"]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_kernel_arg_pass_allowed"]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_passed_to_kernel"] is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_changes_kernel_launch_args"]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_uses_current_wna16_args"]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_passes_current_wna16_args"]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_queue_budget_live_runtime_instantiated"]
        is False
    )
    payload_deref_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_payload_deref_blocked_canary"
    )
    assert summary[f"{payload_deref_prefix}_present"] is True
    assert summary[f"{payload_deref_prefix}_stage"] == (
        "payload_cache_live_runtime_adapter_payload_issue_payload_deref_blocked_canary"
    )
    assert summary[f"{payload_deref_prefix}_payload_issue_payload_deref_schema"] == (
        "payload_cache_runtime_payload_issue_payload_deref_v1"
    )
    assert summary[f"{payload_deref_prefix}_payload_deref_checked"] is True
    assert summary[f"{payload_deref_prefix}_payload_deref_rejected"] is True
    assert summary[f"{payload_deref_prefix}_payload_handle_deref_checked"] is True
    assert summary[f"{payload_deref_prefix}_payload_handle_deref_rejected"] is True
    assert summary[f"{payload_deref_prefix}_payload_deref_attempted"] is False
    assert summary[f"{payload_deref_prefix}_payload_handle_deref_attempted"] is False
    assert summary[f"{payload_deref_prefix}_copy_descriptor_count"] == 0
    assert summary[f"{payload_deref_prefix}_copy_completion_count"] == 0
    assert summary[f"{payload_deref_prefix}_ready_credit_count"] == 0
    assert summary[f"{payload_deref_prefix}_residency_update_count"] == 0
    assert summary[f"{payload_deref_prefix}_resident_payload_count"] == 0
    assert summary[f"{payload_deref_prefix}_payload_handle_deref_count"] == 0
    assert summary[f"{payload_deref_prefix}_issued_payload_count"] == 0
    assert summary[f"{payload_deref_prefix}_payload_bytes"] == 0
    assert summary[f"{payload_deref_prefix}_resident_payload_bytes"] == 0
    assert summary[f"{payload_deref_prefix}_dereferenced_payload_bytes"] == 0
    assert summary[f"{payload_deref_prefix}_payload_deref_allowed"] is False
    assert summary[f"{payload_deref_prefix}_payload_deref_runtime_allowed"] is False
    assert summary[f"{payload_deref_prefix}_ready_credit"] is False
    assert summary[f"{payload_deref_prefix}_passed_to_kernel"] is False
    assert summary[f"{payload_deref_prefix}_changes_kernel_launch_args"] is False
    demand_hit_prefix = (
        "prefetch_lab_default_stream_queue_budget_"
        "live_runtime_adapter_payload_issue_demand_hit_publication_blocked_canary"
    )
    assert summary[f"{demand_hit_prefix}_present"] is True
    assert summary[f"{demand_hit_prefix}_stage"] == (
        "payload_cache_live_runtime_adapter_payload_issue_demand_hit_publication_blocked_canary"
    )
    assert summary[f"{demand_hit_prefix}_payload_issue_demand_hit_publication_schema"] == (
        "payload_cache_runtime_payload_issue_demand_hit_publication_v1"
    )
    assert summary[f"{demand_hit_prefix}_demand_hit_publication_checked"] is True
    assert summary[f"{demand_hit_prefix}_demand_hit_publication_rejected"] is True
    assert summary[f"{demand_hit_prefix}_demand_hit_publication_allowed"] is False
    assert summary[f"{demand_hit_prefix}_demand_hit_published"] is False
    assert summary[f"{demand_hit_prefix}_consumer_visible_payload_hit"] is False
    assert summary[f"{demand_hit_prefix}_prefetched_demand_hit"] is False
    assert summary[f"{demand_hit_prefix}_payload_deref_attempted"] is False
    assert summary[f"{demand_hit_prefix}_payload_handle_deref_attempted"] is False
    assert summary[f"{demand_hit_prefix}_payload_marked_resident"] is False
    assert summary[f"{demand_hit_prefix}_resident_payload_ready"] is False
    assert summary[f"{demand_hit_prefix}_copy_descriptor_count"] == 0
    assert summary[f"{demand_hit_prefix}_copy_completion_count"] == 0
    assert summary[f"{demand_hit_prefix}_ready_credit_count"] == 0
    assert summary[f"{demand_hit_prefix}_residency_update_count"] == 0
    assert summary[f"{demand_hit_prefix}_resident_payload_count"] == 0
    assert summary[f"{demand_hit_prefix}_payload_handle_deref_count"] == 0
    assert summary[f"{demand_hit_prefix}_demand_hit_publication_count"] == 0
    assert summary[f"{demand_hit_prefix}_consumer_visible_payload_hit_count"] == 0
    assert summary[f"{demand_hit_prefix}_demand_hit_count"] == 0
    assert summary[f"{demand_hit_prefix}_issued_payload_count"] == 0
    assert summary[f"{demand_hit_prefix}_payload_bytes"] == 0
    assert summary[f"{demand_hit_prefix}_resident_payload_bytes"] == 0
    assert summary[f"{demand_hit_prefix}_dereferenced_payload_bytes"] == 0
    assert summary[f"{demand_hit_prefix}_demand_hit_payload_bytes"] == 0
    assert summary[f"{demand_hit_prefix}_payload_deref_allowed"] is False
    assert summary[f"{demand_hit_prefix}_payload_deref_runtime_allowed"] is False
    assert summary[f"{demand_hit_prefix}_ready_credit"] is False
    assert summary[f"{demand_hit_prefix}_passed_to_kernel"] is False
    assert summary[f"{demand_hit_prefix}_changes_kernel_launch_args"] is False
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_contract_required_lead_tokens"
        ]
        == 32
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_schedulable_packet_count"
        ]
        == 4
    )
    assert (
        summary["prefetch_lab_default_stream_shifted_issue_replay_clamped_issue_count"]
        == 2
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_duplicate_issue_key_count"
        ]
        == 2
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_row_shift_mismatch_count"
        ]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_row_clamp_mismatch_count"
        ]
        == 0
    )
    assert (
        summary["prefetch_lab_default_stream_shifted_issue_replay_source_payload_bytes"]
        == 0
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_source_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_source_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_source_uses_current_wna16_args"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_source_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "prefetch_lab_default_stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert (
        summary["prefetch_lab_default_stream_shifted_issue_replay_source_measures_tpot"]
        is False
    )
    assert summary["prefetch_lab_default_metadata_decision"] == "shadow_only"
    assert summary["prefetch_lab_default_metadata_passed"] is True
    assert summary["prefetch_lab_default_metadata_failures"] == []
    assert (
        summary["prefetch_lab_default_premap_decision"]
        == "lab_enabled_descriptor_prep_only"
    )
    assert summary["prefetch_lab_default_premap_passed"] is True
    assert summary["prefetch_lab_default_premap_failures"] == []
    assert summary["prefetch_lab_default_premap_positive_count"] == 4
    assert (
        summary["prefetch_lab_default_premap_recommended_capacity_entries"]
        == 12288
    )
    assert (
        summary["prefetch_lab_default_premap_no_eviction_capacity_entries"]
        == 12288
    )
    assert summary["default_kernel_consumer_wna16_side_variant_evidence_passed"] is True
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_passed"
        ]
        is True
    )
    assert (
        summary["default_kernel_consumer_future_wna16_fourth_field_handoff_ready"]
        is True
    )
    assert (
        summary["default_kernel_consumer_future_wna16_fourth_field_handoff_first_field"]
        == "scale_metadata_handle"
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_second_field"
        ]
        == "aux_metadata_handle"
    )
    assert (
        summary["default_kernel_consumer_future_wna16_fourth_field_handoff_third_field"]
        == "packed_weight_descriptor"
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_fourth_field"
        ]
        == "descriptor_ptr"
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_source_count"
        ]
        == 128
    )
    fourth_field_row_count = summary[
        "default_kernel_consumer_future_wna16_fourth_field_handoff_row_count"
    ]
    assert fourth_field_row_count == 520
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_row_ok_count"
        ]
        == fourth_field_row_count
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_row_ok_count"
        ]
        == fourth_field_row_count
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_count"
        ]
        == fourth_field_row_count
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_runner_row_ok_count"
        ]
        == fourth_field_row_count
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_hash"
        ]
        == "6e08db27babecb6a"
    )
    assert (
        summary["default_kernel_consumer_future_wna16_fourth_field_handoff_runner_hash"]
        == "ba2e219a8ff9ccfe"
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_expected_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_passed_to_kernel"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_measures_tpot"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_measures_vllm_latency"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_fourth_field_handoff_wna16_benchmark_ready"
        ]
        is False
    )
    assert summary["default_kernel_consumer_wna16_side_variant_required"] is True
    assert summary["default_kernel_consumer_wna16_side_variant_checked"] is True
    assert summary["default_kernel_consumer_wna16_side_variant_source_count"] == 128
    assert summary["default_kernel_consumer_wna16_side_variant_row_count"] == 520
    assert summary["default_kernel_consumer_wna16_side_variant_row_ok_count"] == 520
    assert summary["default_kernel_consumer_wna16_side_variant_error_count"] == 0
    assert (
        summary["default_kernel_consumer_wna16_side_variant_all_handle_fields_read"]
        is True
    )
    assert summary["default_kernel_consumer_wna16_side_variant_payload_bytes"] == 0
    assert summary["default_kernel_consumer_wna16_side_variant_passed_to_kernel"] is False
    assert (
        summary["default_kernel_consumer_wna16_side_variant_changes_kernel_launch_args"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_wna16_side_variant_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_wna16_side_variant_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_wna16_side_variant_reuses_current_wna16_arg_slot"]
        is False
    )
    assert summary["default_kernel_consumer_wna16_side_variant_base_ready"] is True
    assert summary["default_kernel_consumer_wna16_side_variant_ready"] is True
    assert summary["default_kernel_consumer_wna16_benchmark_ready"] is False
    assert summary["payload_cache_manager_useful_work_ab_gate_gate_ready"] is True
    assert summary["payload_cache_manager_useful_work_ab_gate_issued_prefetch_count"] == 133
    assert summary["payload_cache_manager_useful_work_ab_gate_used_fetch_count"] == 108
    assert summary["payload_cache_manager_useful_work_ab_gate_unused_fetch_count"] == 25
    assert summary["payload_cache_manager_useful_work_ab_gate_demand_count"] == 224
    assert summary["payload_cache_manager_useful_work_ab_gate_demand_hit_count"] == 199
    assert summary["payload_cache_manager_useful_work_ab_gate_payload_bytes"] == 0
    assert (
        summary["payload_cache_manager_useful_work_ab_gate_kernel_arg_pass_allowed"]
        is False
    )
    assert summary["payload_cache_manager_useful_work_ab_gate_passed_to_kernel"] is False
    assert summary["payload_cache_manager_production_ab_preflight_gate_ready"] is True
    assert (
        summary["payload_cache_manager_production_ab_preflight_artifact_scope"]
        == "preflight_smoke_only"
    )
    assert (
        summary[
            "payload_cache_manager_production_ab_preflight_final_production_result_ready"
        ]
        is False
    )
    assert (
        summary["payload_cache_manager_production_ab_preflight_performance_claim_ready"]
        is False
    )
    assert summary["payload_cache_manager_production_ab_preflight_payload_bytes"] == 0
    assert (
        summary[
            "payload_cache_manager_production_ab_preflight_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        summary["payload_cache_manager_production_ab_preflight_passed_to_kernel"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
        ]
        is True
    )
    assert (
        summary["default_kernel_consumer_next_runtime_stage"]
        == "future_typed_slot_useful_consumer_or_payload_cache_manager"
    )
    assert (
        summary["default_kernel_consumer_schema_name"]
        == "fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1"
    )
    assert summary["default_kernel_consumer_schema_artifact_sha256"] == hashlib.sha256(
        (
            tmp_path
            / "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
        ).read_bytes()
    ).hexdigest()
    assert summary["default_kernel_consumer_schema_row_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert summary["default_kernel_consumer_required_gate_checks"] == {
        "consumer_view_required": True,
        "consumer_view_row_layout_required": True,
        "consumer_view_handle_projection_required": True,
        "consumer_view_all_handle_fields_required": True,
        "consumer_view_source_packet_chain_depth_required": 3,
        "consumer_program_view_required": True,
        "consumer_program_view_row_assignment_formula": (
            "program_id * rows_per_program + lane_id + row_offset"
        ),
        "consumer_program_view_ptr_required": True,
        "request_launch_all_handle_fields_required": True,
        "request_launch_ptr_all_handle_fields_required": True,
        "kernel_entry_summary_row_metadata_required": True,
        "kernel_entry_args_row_metadata_required": True,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
        "current_wna16_arg_compatible_required": False,
    }
    assert summary["default_kernel_consumer_consumer_view_required"] is True
    assert summary["default_kernel_consumer_consumer_view_row_layout_required"] is True
    assert (
        summary["default_kernel_consumer_consumer_view_handle_projection_required"]
        is True
    )
    assert (
        summary["default_kernel_consumer_consumer_view_all_handle_fields_required"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_consumer_view_source_packet_chain_depth_required"
        ]
        == 3
    )
    assert summary["default_kernel_consumer_consumer_program_view_required"] is True
    assert (
        summary[
            "default_kernel_consumer_consumer_program_view_row_assignment_formula_required"
        ]
        == "program_id * rows_per_program + lane_id + row_offset"
    )
    assert (
        summary["default_kernel_consumer_request_launch_all_handle_fields_required"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_all_handle_fields_required"
        ]
        is True
    )
    assert summary["default_kernel_consumer_required_gate_payload_bytes_required"] == 0
    assert (
        summary["default_kernel_consumer_required_gate_passed_to_kernel_required"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_required_gate_changes_kernel_launch_args_required"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_required_gate_current_wna16_arg_compatible_required"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_future_kernel_args_layout_reported"]
        is True
    )
    assert (
        summary["default_kernel_consumer_future_kernel_args_layout_expected"]
        == FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED
    )
    assert (
        summary["default_kernel_consumer_future_kernel_args_struct_size"]
        == FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED[
            "future_kernel_consumer_args_struct_size"
        ]
    )
    assert (
        summary["default_kernel_consumer_future_kernel_args_offset_field_mask"]
        == FUTURE_KERNEL_CONSUMER_ARGS_LAYOUT_EXPECTED[
            "future_kernel_consumer_args_offset_field_mask"
        ]
    )
    assert (
        summary["default_kernel_consumer_kernel_arg_packet_layout_reported"]
        is True
    )
    assert (
        summary["default_kernel_consumer_kernel_arg_packet_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_EXPECTED
    )
    assert (
        summary["default_kernel_consumer_kernel_arg_packet_struct_size"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_consumer_kernel_arg_packet_struct_size"
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_kernel_arg_packet_offset_program_view_ptr"
        ]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ARG_PACKET_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_consumer_kernel_arg_packet_offset_program_view_ptr"
        ]
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_summary_layout_reported"]
        is True
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_summary_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_EXPECTED
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_summary_struct_size"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_consumer_kernel_entry_summary_struct_size"
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator"
        ]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_SUMMARY_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_consumer_kernel_entry_summary_offset_row_hash_accumulator"
        ]
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_args_layout_reported"]
        is True
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_args_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_EXPECTED
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_args_struct_size"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_consumer_kernel_entry_args_struct_size"
        ]
    )
    assert (
        summary["default_kernel_consumer_kernel_entry_args_offset_summary"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_ABI_LAYOUT_EXPECTED[
            "future_kernel_native_consumer_kernel_entry_args_offset_summary"
        ]
    )
    assert summary["default_kernel_consumer_kernel_entry_args_checked"] is True
    assert (
        summary["default_kernel_consumer_kernel_entry_args_field_read_path"]
        == "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert summary["default_kernel_consumer_kernel_entry_args_packet_chain_depth"] == 5
    assert summary["default_kernel_consumer_kernel_entry_args_all_handle_fields_read"] is True
    entry_args_row_count = summary[
        "default_kernel_consumer_kernel_entry_args_summary_row_count"
    ]
    assert entry_args_row_count == 520
    assert (
        summary["default_kernel_consumer_kernel_entry_args_summary_row_ok_count"]
        == entry_args_row_count
    )
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        assert (
            summary[
                "default_kernel_consumer_kernel_entry_args_summary_"
                f"{field}_read_row_ok_count"
            ]
            == entry_args_row_count
        )
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count"
        ]
        == entry_args_row_count
    )
    assert summary["default_kernel_consumer_kernel_entry_args_summary_error_count"] == 0
    assert summary["default_kernel_consumer_kernel_entry_args_summary_field_mask"] == 15
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_args_summary_row_hash_accumulator"
        ]
        == "c4b51a0fa5ba88c4"
    )
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator"
        ]
        == "c2e4ae7fa9bc3227"
    )
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator"
        ]
        == "1a11b42afa9e8576"
    )
    assert summary["default_kernel_consumer_kernel_entry_args_payload_bytes"] == 0
    assert summary["default_kernel_consumer_kernel_entry_args_passed_to_kernel"] is False
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_args_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_kernel_entry_args_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_dispatch_abi_name"]
        == "premap_future_kernel_native_consumer_dispatch_abi_v1"
    )
    assert (
        summary["default_kernel_consumer_dispatch_abi_mode"]
        == "readonly_future_kernel_native_consumer_dispatch_abi"
    )
    assert (
        summary["default_kernel_consumer_dispatch_abi_row_assignment_formula"]
        == "row_offset + program_id * rows_per_program + lane_id"
    )
    assert (
        summary["default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible"]
        is False
    )
    assert summary["default_kernel_consumer_dispatch_full_table_required"] is True
    assert (
        summary["default_kernel_consumer_dispatch_runner_evidence_label"]
        == "future_kernel_native_dispatch_consumer_online_runner_32_128export_json"
    )
    assert summary["default_kernel_consumer_dispatch_runner_evidence_present"] is True
    assert summary["default_kernel_consumer_dispatch_runner_evidence_passed"] is True
    assert summary["default_kernel_consumer_dispatch_runner_evidence_failure"] is None
    assert (
        summary["default_kernel_consumer_dispatch_runner_artifact_evidence_label"]
        == "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json"
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_artifact_evidence_present"]
        is True
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_artifact_evidence_passed"]
        is True
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_artifact_evidence_failure"]
        is None
    )
    assert summary["default_kernel_consumer_dispatch_runner_online_input_count"] == 32
    assert (
        summary["default_kernel_consumer_dispatch_runner_online_extra_input_count"]
        == 31
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_online_extra_input_passed_count"
        ]
        == 31
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_artifact_check_passed"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_min_online_inputs"
        ]
        == 32
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_row_count_min"
        ]
        == 2
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_row_count_max"
        ]
        == 4
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_row_count_sum"
        ]
        == 66
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_row_count_diverse"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_final_deferred_count"
        ]
        == 0
    )
    assert (
        summary["default_kernel_consumer_online_merged_multiprogram_evidence_label"]
        == "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json"
    )
    assert (
        summary["default_kernel_consumer_online_merged_multiprogram_evidence_passed"]
        is True
    )
    assert (
        summary["default_kernel_consumer_online_merged_multiprogram_source_count"]
        == 32
    )
    assert summary["default_kernel_consumer_online_merged_multiprogram_row_count"] == 520
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset"
        ]
        == 0
    )
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit"
        ]
        == 520
    )
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows"
        ]
        == 520
    )
    assert (
        summary["default_kernel_consumer_online_merged_multiprogram_hashchain_equal"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked"
        ]
        is True
    )
    assert (
        summary["default_kernel_consumer_online_merged_multiprogram_no_payload"]
        is True
    )
    assert (
        summary["default_kernel_consumer_online_merged_multiprogram_passed_to_kernel"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is True
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_dispatch_hash_accumulator"]
        == "abc123"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_dispatch_ptr_hash_accumulator"
        ]
        == "def456"
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_arg_slot_hash_accumulator"]
        == "fedcba"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_dispatch_handle_projection_hash_accumulator"
        ]
        == "481d"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_dispatch_ptr_handle_projection_hash_accumulator"
        ]
        == "481d"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_arg_slot_handle_projection_hash_accumulator"
        ]
        == "481d"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_consumer_view_handle_projection_hash_accumulator"
        ]
        == "481d"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_field_names"
        ]
        == [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_schema_covered"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_checked"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_row_count"
        ]
        == 2
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_row_ok_count"
        ]
        == 2
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_passed_to_kernel"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_checked"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_required"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_row_count"
        ]
        == 2
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_row_ok_count"
        ]
        == 2
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_passed_to_kernel"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_compatible_path_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_mirror_field_coverage"
        ]
        == ["scale_metadata_handle"]
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_optional_mirror_field_coverage"
        ]
        == [
            "aux_metadata_handle",
            "descriptor_ptr",
            "packed_weight_descriptor",
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_optional_mirror_evidence_labels"
        ]
        == [
            "future_kernel_args_aux_metadata_mirror_canary_json",
            "future_kernel_args_descriptor_ptr_mirror_canary_json",
            "future_kernel_args_packed_weight_mirror_canary_json",
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_field_coverage"
        ]
        == [
            "aux_metadata_handle",
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_total_full_field_mirror_coverage"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_coverage_required"
        ]
        is True
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_final_preflight_passed"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count"
        ]
        == 0
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count"
        ]
        == 0
    )
    assert summary["default_kernel_consumer_dispatch_checked"] is True
    assert summary["default_kernel_consumer_dispatch_row_count"] == 2
    assert summary["default_kernel_consumer_dispatch_row_ok_count"] == 2
    assert summary["default_kernel_consumer_dispatch_active_rows"] == 2
    assert summary["default_kernel_consumer_dispatch_row_offset"] == 0
    assert summary["default_kernel_consumer_dispatch_row_limit"] == 2
    assert summary["default_kernel_consumer_dispatch_payload_bytes"] == 0
    assert summary["default_kernel_consumer_dispatch_passed_to_kernel"] is False
    assert summary["default_kernel_consumer_dispatch_changes_kernel_launch_args"] is False
    assert (
        summary["default_kernel_consumer_dispatch_current_wna16_arg_compatible"]
        is False
    )
    assert summary["default_kernel_consumer_dispatch_full_table_checked"] is True
    assert (
        summary["default_kernel_consumer_dispatch_ptr_abi_name"]
        == "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_abi_struct"]
        == "PremapFutureKernelNativeConsumerDispatchPtrV1"
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_abi_mode"]
        == "readonly_future_kernel_native_consumer_dispatch_ptr_abi"
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_abi_source"]
        == "premap_future_kernel_native_consumer_dispatch_abi_v1"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible"
        ]
        is False
    )
    assert summary["default_kernel_consumer_dispatch_ptr_required"] is True
    assert summary["default_kernel_consumer_dispatch_ptr_checked"] is True
    assert summary["default_kernel_consumer_dispatch_ptr_row_count"] == 2
    assert summary["default_kernel_consumer_dispatch_ptr_row_ok_count"] == 2
    assert summary["default_kernel_consumer_dispatch_ptr_error_count"] == 0
    assert summary["default_kernel_consumer_dispatch_ptr_payload_bytes"] == 0
    assert summary["default_kernel_consumer_dispatch_ptr_passed_to_kernel"] is False
    assert (
        summary["default_kernel_consumer_dispatch_ptr_changes_kernel_launch_args"]
        is False
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_current_wna16_arg_compatible"]
        is False
    )
    assert summary["default_kernel_consumer_dispatch_ptr_mirror_row_count"] == 2
    assert summary["default_kernel_consumer_dispatch_ptr_mirror_row_ok_count"] == 2
    assert (
        summary["default_kernel_consumer_arg_slot_abi_name"]
        == "premap_future_kernel_native_consumer_arg_slot_abi_v1"
    )
    assert (
        summary["default_kernel_consumer_arg_slot_abi_struct"]
        == "PremapFutureKernelNativeConsumerArgSlotV1"
    )
    assert (
        summary["default_kernel_consumer_arg_slot_abi_mode"]
        == "readonly_future_kernel_native_consumer_arg_slot_abi"
    )
    assert (
        summary["default_kernel_consumer_arg_slot_abi_source"]
        == "premap_future_kernel_native_consumer_dispatch_ptr_abi_v1"
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_abi_current_wna16_arg_compatible"
        ]
        is False
    )
    assert summary["default_kernel_consumer_arg_slot_checked"] is True
    assert summary["default_kernel_consumer_arg_slot_row_count"] == 2
    assert summary["default_kernel_consumer_arg_slot_row_ok_count"] == 2
    assert summary["default_kernel_consumer_arg_slot_error_count"] == 0
    assert summary["default_kernel_consumer_arg_slot_field_read_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert summary["default_kernel_consumer_arg_slot_field_read_row_count"] == 520
    assert summary["default_kernel_consumer_arg_slot_all_handle_fields_read"] is True
    assert summary["default_kernel_consumer_arg_slot_field_read_row_ok_counts"] == {
        "descriptor_ptr": 520,
        "packed_weight_descriptor": 520,
        "scale_metadata_handle": 520,
        "aux_metadata_handle": 520,
    }
    assert summary["default_kernel_consumer_arg_slot_field_read_error_counts"] == {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 0,
        "aux_metadata_handle": 0,
    }
    assert (
        summary["default_kernel_consumer_consumer_view_field_read_field_names"]
        == [
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
            "aux_metadata_handle",
        ]
    )
    assert (
        summary["default_kernel_consumer_consumer_view_field_read_row_count"] == 520
    )
    assert (
        summary["default_kernel_consumer_consumer_view_all_handle_fields_read"]
        is True
    )
    assert summary[
        "default_kernel_consumer_consumer_view_field_read_row_ok_counts"
    ] == {
        "descriptor_ptr": 520,
        "packed_weight_descriptor": 520,
        "scale_metadata_handle": 520,
        "aux_metadata_handle": 520,
    }
    assert summary[
        "default_kernel_consumer_consumer_view_field_read_error_counts"
    ] == {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 0,
        "aux_metadata_handle": 0,
    }
    assert (
        summary["default_kernel_consumer_consumer_view_status_source"]
        == "online_merged_arg_slot_summary"
    )
    assert (
        summary["default_kernel_consumer_consumer_view_row_window_source"]
        == "online_merged_arg_slot_summary"
    )
    assert (
        summary["default_kernel_consumer_consumer_view_source"]
        == "premap_future_kernel_native_consumer_arg_slot_abi_v1"
    )
    assert (
        summary["default_kernel_consumer_consumer_view_source_expected"]
        == "premap_future_kernel_native_consumer_arg_slot_abi_v1"
    )
    assert (
        summary["default_kernel_consumer_consumer_view_source_matches_schema"]
        is True
    )
    assert (
        summary["default_kernel_consumer_consumer_view_source_packet_chain_depth"]
        == 3
    )
    assert summary["default_kernel_consumer_dispatch_row_window"] == {
        "row_offset": 0,
        "row_limit": 520,
        "rows_per_program": 256,
    }
    assert summary["default_kernel_consumer_consumer_view_row_window"] == {
        "row_offset": 0,
        "row_limit": 520,
        "rows_per_program": 256,
    }
    assert (
        summary[
            "default_kernel_consumer_consumer_view_row_window_matches_dispatch"
        ]
        is True
    )
    assert summary["default_kernel_consumer_consumer_view_row_offset"] == 0
    assert summary["default_kernel_consumer_consumer_view_row_limit"] == 520
    assert summary["default_kernel_consumer_consumer_view_rows_per_program"] == 256
    assert summary["default_kernel_consumer_consumer_view_payload_bytes"] == 0
    assert summary["default_kernel_consumer_consumer_view_passed_to_kernel"] is False
    assert (
        summary["default_kernel_consumer_consumer_view_changes_kernel_launch_args"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_consumer_view_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_consumer_view_safety_matches_required"
        ]
        is True
    )
    assert summary["default_kernel_consumer_arg_slot_payload_bytes"] == 0
    assert summary["default_kernel_consumer_arg_slot_passed_to_kernel"] is False
    assert (
        summary["default_kernel_consumer_arg_slot_changes_kernel_launch_args"]
        is False
    )
    assert (
        summary["default_kernel_consumer_arg_slot_current_wna16_arg_compatible"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert summary["default_kernel_consumer_native_field_mask"] == 15
    assert summary["default_kernel_consumer_native_required_field_mask"] == 7
    assert summary["default_kernel_consumer_launch_field_mask"] == 15
    assert summary["default_kernel_consumer_launch_required_field_mask"] == 7
    assert summary["default_kernel_consumer_dispatch_field_mask"] == 15
    assert summary["default_kernel_consumer_dispatch_required_field_mask"] == 7
    assert summary["default_kernel_consumer_dispatch_ptr_field_mask"] == 15
    assert summary["default_kernel_consumer_dispatch_ptr_required_field_mask"] == 7
    assert summary["default_kernel_consumer_arg_slot_field_mask"] == 15
    assert summary["default_kernel_consumer_arg_slot_required_field_mask"] == 7
    assert summary["default_kernel_consumer_arg_slot_mirror_checked"] is True
    assert (
        summary["default_kernel_consumer_arg_slot_mirror_field_name"]
        == "scale_metadata_handle"
    )
    assert summary["default_kernel_consumer_arg_slot_online_mirror_field_coverage"] == [
        "scale_metadata_handle"
    ]
    assert (
        summary["default_kernel_consumer_arg_slot_online_full_field_mirror_coverage"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_diagnostic_mirror_field_coverage"
        ]
        == [
            "aux_metadata_handle",
            "descriptor_ptr",
            "packed_weight_descriptor",
        ]
    )
    assert summary["default_kernel_consumer_arg_slot_online_diagnostic_summary_keys"] == [
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary",
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary",
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary",
    ]
    assert summary["default_kernel_consumer_arg_slot_online_total_mirror_field_coverage"] == [
        "aux_metadata_handle",
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
    ]
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_total_mirror_coverage_required"
        ]
        is True
    )
    assert summary["default_kernel_consumer_arg_slot_required_mirror_field_coverage"] == [
        "aux_metadata_handle",
        "descriptor_ptr",
        "packed_weight_descriptor",
    ]
    assert summary["default_kernel_consumer_arg_slot_required_mirror_evidence_labels"] == [
        "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
        "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
    ]
    assert summary["default_kernel_consumer_arg_slot_optional_mirror_field_coverage"] == []
    assert summary["default_kernel_consumer_arg_slot_optional_mirror_evidence_labels"] == []
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_merged_required_mirror_field_coverage"
        ]
        == ["aux_metadata_handle", "descriptor_ptr", "packed_weight_descriptor"]
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_merged_required_mirror_evidence_labels"
        ]
        == [
            "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json",
            "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json",
            "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json",
        ]
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_merged_optional_mirror_field_coverage"
        ]
        == []
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_online_merged_optional_mirror_evidence_labels"
        ]
        == []
    )
    assert summary["default_kernel_consumer_arg_slot_total_mirror_field_coverage"] == [
        "aux_metadata_handle",
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
    ]
    assert (
        summary["default_kernel_consumer_arg_slot_total_full_field_mirror_coverage"]
        is True
    )
    assert summary["default_kernel_consumer_arg_slot_all_mirror_fields"] == list(
        PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
    )
    assert summary["default_kernel_consumer_arg_slot_mirror_row_count"] == 2
    assert summary["default_kernel_consumer_arg_slot_mirror_row_ok_count"] == 2
    assert summary["default_kernel_consumer_arg_slot_mirror_error_count"] == 0
    assert summary["default_kernel_consumer_arg_slot_slot_struct_size"] == 32
    assert summary["default_kernel_consumer_arg_slot_slot_struct_align"] == 8
    assert (
        summary["default_kernel_consumer_arg_slot_dispatch_ptr_struct_size"] == 32
    )
    assert summary["default_kernel_consumer_arg_slot_result_struct_size"] == 72
    assert summary["default_kernel_consumer_arg_slot_offset_dispatch_ptr"] == 0
    assert summary["default_kernel_consumer_arg_slot_offset_flags"] == 24
    assert (
        summary["default_kernel_consumer_arg_slot_status_source"]
        == "online_dispatch_runner_summary"
    )
    assert (
        summary["default_kernel_consumer_arg_slot_status_evidence_label"]
        == "future_kernel_native_dispatch_consumer_online_runner_32_128export_json"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_ptr_standalone_evidence_label"
        ]
        == "future_kernel_native_dispatch_ptr_standalone_canary_json"
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_standalone_evidence_present"]
        is True
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_standalone_evidence_passed"]
        is True
    )
    assert summary["default_kernel_consumer_dispatch_ptr_standalone_input_source"] == (
        "synthetic"
    )
    assert summary["default_kernel_consumer_dispatch_ptr_standalone_checked"] is True
    assert summary["default_kernel_consumer_dispatch_ptr_standalone_row_count"] == 2
    assert (
        summary["default_kernel_consumer_dispatch_ptr_standalone_row_ok_count"] == 2
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_standalone_payload_bytes"] == 0
    )
    assert (
        summary["default_kernel_consumer_dispatch_ptr_standalone_passed_to_kernel"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_ptr_standalone_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_ptr_standalone_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_arg_slot_standalone_evidence_label"]
        == "future_kernel_native_arg_slot_standalone_canary_json"
    )
    assert (
        summary["default_kernel_consumer_arg_slot_standalone_evidence_present"]
        is True
    )
    assert (
        summary["default_kernel_consumer_arg_slot_standalone_evidence_passed"]
        is True
    )
    assert summary["default_kernel_consumer_arg_slot_standalone_input_source"] == (
        "synthetic"
    )
    assert (
        summary["default_kernel_consumer_arg_slot_standalone_status_source"]
        == "standalone_native_stub_artifact"
    )
    assert summary["default_kernel_consumer_arg_slot_standalone_checked"] is True
    assert summary["default_kernel_consumer_arg_slot_standalone_row_count"] == 2
    assert summary["default_kernel_consumer_arg_slot_standalone_row_ok_count"] == 2
    assert summary["default_kernel_consumer_arg_slot_standalone_payload_bytes"] == 0
    assert (
        summary["default_kernel_consumer_arg_slot_standalone_passed_to_kernel"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_standalone_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_standalone_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_arg_slot_standalone_mirror_field_coverage"]
        == ["scale_metadata_handle"]
    )
    assert (
        summary[
            "default_kernel_consumer_arg_slot_standalone_full_field_mirror_coverage"
        ]
        is False
    )
    assert summary["default_kernel_consumer_request_launch_checked"] is True
    assert (
        summary["default_kernel_consumer_request_launch_field_read_path"]
        == "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
    )
    assert summary["default_kernel_consumer_request_launch_packet_chain_depth"] == 5
    assert summary["default_kernel_consumer_request_launch_device_ordinal"] == 0
    assert summary["default_kernel_consumer_request_launch_grid_x"] == 1
    assert summary["default_kernel_consumer_request_launch_block_x"] == 256
    assert summary["default_kernel_consumer_request_launch_row_offset"] == 0
    assert summary["default_kernel_consumer_request_launch_row_limit"] == 2
    assert summary["default_kernel_consumer_request_launch_rows_per_program"] == 256
    request_launch_row_count = summary[
        "default_kernel_consumer_request_launch_summary_row_count"
    ]
    assert request_launch_row_count == 2
    assert (
        summary["default_kernel_consumer_request_launch_summary_row_ok_count"]
        == request_launch_row_count
    )
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        assert (
            summary[
                "default_kernel_consumer_request_launch_summary_"
                f"{field}_read_row_ok_count"
            ]
            == request_launch_row_count
        )
    assert (
        summary[
            "default_kernel_consumer_request_launch_summary_row_metadata_read_row_ok_count"
        ]
        == request_launch_row_count
    )
    assert summary["default_kernel_consumer_request_launch_summary_error_count"] == 0
    assert summary["default_kernel_consumer_request_launch_summary_field_mask"] == 15
    assert (
        summary[
            "default_kernel_consumer_request_launch_summary_row_hash_accumulator"
        ]
        == "1234567890abcdef"
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_summary_field_read_hash_accumulator"
        ]
        == "0fedcba987654321"
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_summary_row_metadata_hash_accumulator"
        ]
        == "55aa55aa55aa55aa"
    )
    assert summary["default_kernel_consumer_request_launch_all_handle_fields_read"] is True
    assert summary["default_kernel_consumer_request_launch_payload_bytes"] == 0
    assert summary["default_kernel_consumer_request_launch_passed_to_kernel"] is False
    assert (
        summary["default_kernel_consumer_request_launch_changes_kernel_launch_args"]
        is False
    )
    assert (
        summary["default_kernel_consumer_request_launch_current_wna16_arg_compatible"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert summary["default_kernel_consumer_request_launch_ptr_checked"] is True
    assert (
        summary["default_kernel_consumer_request_launch_ptr_field_read_path"]
        == "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
    )
    assert summary["default_kernel_consumer_request_launch_ptr_packet_chain_depth"] == 6
    request_launch_ptr_row_count = summary[
        "default_kernel_consumer_request_launch_ptr_summary_row_count"
    ]
    assert request_launch_ptr_row_count == 2
    assert (
        summary["default_kernel_consumer_request_launch_ptr_summary_row_ok_count"]
        == request_launch_ptr_row_count
    )
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        assert (
            summary[
                "default_kernel_consumer_request_launch_ptr_summary_"
                f"{field}_read_row_ok_count"
            ]
            == request_launch_ptr_row_count
        )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_summary_row_metadata_read_row_ok_count"
        ]
        == request_launch_ptr_row_count
    )
    assert summary["default_kernel_consumer_request_launch_ptr_summary_error_count"] == 0
    assert summary["default_kernel_consumer_request_launch_ptr_summary_field_mask"] == 15
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_summary_row_hash_accumulator"
        ]
        == "1234567890abcdef"
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_summary_field_read_hash_accumulator"
        ]
        == "0fedcba987654321"
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_summary_row_metadata_hash_accumulator"
        ]
        == "55aa55aa55aa55aa"
    )
    assert (
        summary["default_kernel_consumer_request_launch_ptr_all_handle_fields_read"]
        is True
    )
    assert summary["default_kernel_consumer_request_launch_ptr_payload_bytes"] == 0
    assert (
        summary["default_kernel_consumer_request_launch_ptr_passed_to_kernel"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_request_launch_ptr_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert summary["default_required_evidence_passed"] is True
    assert summary["default_optional_evidence_passed"] is True
    assert summary["runtime_gate_evidence_deferred_count"] == 0
    assert summary["strict_default_gate_evidence_deferred_count"] == 0
    assert summary["native_typed_consumer_bridge_required"] is True
    assert summary["native_stub_online_invocation_canary_required"] is True
    assert summary["kernel_side_typed_row_consumer_path_required"] is True
    assert summary["payload_bytes_required"] == 0
    assert summary["passed_to_kernel_required"] is False
    assert summary["changes_kernel_launch_args_required"] is False
    assert summary["required_evidence"]["required_count"] == 71
    assert summary["required_evidence"]["present_count"] == 71
    assert summary["required_evidence"]["passed_count"] == 71
    assert summary["optional_evidence"]["required_count"] == 15
    assert summary["optional_evidence"]["present_count"] == 13
    assert summary["optional_evidence"]["passed_count"] == 13
    assert summary["payload_cache_online_native_producer_boundary_gap_required"] is True
    assert (
        summary["payload_cache_online_native_producer_boundary_gap_acknowledged"]
        is True
    )
    assert (
        summary[
            "payload_cache_online_native_producer_boundary_gap_ready_for_lab_runtime_gate"
        ]
        is False
    )
    assert (
        summary["payload_cache_online_native_producer_boundary_gap_runtime_passed"]
        is False
    )
    assert (
        summary["payload_cache_online_native_producer_boundary_gap_lab_gate_passed"]
        is False
    )
    assert (
        summary[
            "payload_cache_online_native_producer_boundary_gap_next_required_boundary"
        ]
        == "inprocess_vllm_replay_visible_native_producer_op"
    )
    assert (
        summary["payload_cache_vllm_replay_visible_native_producer_required"]
        is True
    )
    assert (
        summary["payload_cache_vllm_replay_visible_native_producer_present"]
        is True
    )
    assert (
        summary["payload_cache_vllm_replay_visible_native_producer_passed"]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_native_producer_ready_for_lab_gate"
        ]
        is True
    )
    assert (
        summary["payload_cache_vllm_replay_visible_native_producer_source_kind"]
        == "vllm_prelaunch_inprocess_native_producer"
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_native_producer_contract_boundary"
        ]
        == "inprocess_vllm_replay_visible_native_producer_op"
    )
    assert summary["payload_cache_vllm_replay_visible_native_producer_packet_count"] == 8
    assert (
        summary[
            "payload_cache_vllm_replay_visible_native_producer_issue_candidate_count"
        ]
        == 64
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_native_producer_prelaunch_callable_native_session"
        ]
        is True
    )
    assert summary["payload_cache_vllm_replay_visible_native_producer_payload_bytes"] == 0
    assert (
        summary["payload_cache_vllm_replay_visible_native_producer_kernel_arg_pass"]
        is False
    )
    assert (
        summary["payload_cache_vllm_replay_visible_native_producer_passed_to_kernel"]
        is False
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_native_producer_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_required"
        ]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_present"
        ]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_passed"
        ]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_ready_for_lab_gate"
        ]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_boundary"
        ]
        == "inprocess_vllm_prelaunch_native_count_ptr_producer_op"
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_current_count_source_kind"
        ]
        == "num_tokens_post_padded_device_tensor"
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_current_expert_ptr_source_kind"
        ]
        == "vllm_prelaunch_device_tensor"
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_expected_packet_count"
        ]
        == 8
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_count_ptr_ready_count"
        ]
        == 8
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_count_ptr_blocked_count"
        ]
        == 0
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_host_scalar_count"
        ]
        == 0
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_kernel_arg_pass"
        ]
        is False
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_passed_to_kernel"
        ]
        is False
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_native_producer_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary["payload_cache_vllm_replay_visible_count_ptr_readiness_required"]
        is True
    )
    assert (
        summary["payload_cache_vllm_replay_visible_count_ptr_readiness_present"]
        is True
    )
    assert (
        summary["payload_cache_vllm_replay_visible_count_ptr_readiness_passed"]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_future_count_ptr_session_ready"
        ]
        is True
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_contract_boundary"
        ]
        == "future_session_update_count_ptr_v1_prelaunch_probe"
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_expected_packet_count"
        ]
        == 8
    )
    assert (
        summary["payload_cache_vllm_replay_visible_count_ptr_readiness_ready_count"]
        == 8
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_blocked_count"
        ]
        == 0
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_payload_bytes"
        ]
        == 0
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_kernel_arg_pass"
        ]
        is False
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_passed_to_kernel"
        ]
        is False
    )
    assert (
        summary[
            "payload_cache_vllm_replay_visible_count_ptr_readiness_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        summary["required_evidence"]["evidence"][
            "prelaunch_pointer_source_observer_check_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "readonly_live_trusted_refs_check_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_multiprogram_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
            "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "payload_cache_online_native_producer_boundary_gap_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "payload_cache_producer_state_inprocess_native_session_online_contract_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "payload_cache_producer_state_online_nonempty_issue_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "payload_cache_producer_state_nonempty_issue_stub_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json"
        ]["passed"]
        is True
    )
    online_merged_runner_sha = hashlib.sha256(
        (
            tmp_path
            / summary["required_evidence"]["evidence"][
                "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json"
            ]["path"]
        ).read_bytes()
    ).hexdigest()
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json"
        ]["sha256"]
        == online_merged_runner_sha
    )
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_evidence_sha256"
        ]
        == online_merged_runner_sha
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "packed_weight_single_field_handle_handoff_canary_smoke_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_packed_weight_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "aux_metadata_single_field_handle_handoff_canary_smoke_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "descriptor_ptr_single_field_handle_handoff_canary_smoke_json"
        ]["passed"]
        is True
    )
    assert (
        summary["required_evidence"]["evidence"][
            "strict_native_typed_consumer_bridge_128_gate_json"
        ]["passed"]
        is True
    )
    assert result["trace_config_checks"][0]["passed"] is True
    assert result["trace_config_checks"][0]["readonly_gate_path_label"] == default_gate


def test_premap_lab_preflight_requires_prelaunch_pointer_source_observer_check(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    gate_text = gate_path.read_text(encoding="utf-8")
    gate_text = gate_text.replace(
        "  prelaunch_pointer_source_observer_check_json: "
        "reports/default_gate_prelaunch_pointer_source_observer_check.json\n",
        "",
    )
    gate_path.write_text(gate_text, encoding="utf-8")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "prelaunch_pointer_source_observer_check_json:missing_evidence_path"
        in result["default_readonly_gate_required_evidence_check"]["failures"]
    )


def test_premap_lab_preflight_requires_readonly_live_trusted_refs_check(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    gate_text = gate_path.read_text(encoding="utf-8")
    gate_text = gate_text.replace(
        "  readonly_live_trusted_refs_check_json: "
        "reports/default_gate_readonly_live_trusted_refs_check.json\n",
        "",
    )
    gate_path.write_text(gate_text, encoding="utf-8")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "readonly_live_trusted_refs_check_json:missing_evidence_path"
        in result["default_readonly_gate_required_evidence_check"]["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_useful_repeat_seed_only(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    repeat_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    payload = json.loads(repeat_path.read_text(encoding="utf-8"))
    payload["seed_only"] = True
    repeat_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:seed_only_mismatch"
        in result["default_readonly_gate_required_evidence_check"]["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_useful_runtime_ablation_kind_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    ablation_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_runtime_ablation.json"
    )
    payload = json.loads(ablation_path.read_text(encoding="utf-8"))
    payload["artifact_kind"] = "fake_runtime_ablation"
    ablation_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_runtime_ablation_json:"
        "artifact_kind_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payloadless_useful_timing_gate_tpot_allowed(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    timing_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate.json"
    )
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    payload["payloadless_production_tpot_allowed"] = True
    timing_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_json:"
        "payloadless_production_tpot_allowed_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payloadless_useful_timing_gate_bound_kernel_arg(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    timing_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate.json"
    )
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    payload["bound_runtime_ablation_safety"]["kernel_arg_pass_allowed"] = True
    timing_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_json:"
        "bound_runtime_ablation_safety_kernel_arg_pass_allowed_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payloadless_useful_timing_gate_bad_row_coverage(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    timing_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate.json"
    )
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    payload["row_ok_count"] = payload["row_count"] - 1
    payload["rows_consumed"] = payload["row_count"]
    timing_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_json:"
        "row_ok_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_incomplete_payloadless_useful_work(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    execution_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.json"
    )
    payload = json.loads(execution_path.read_text(encoding="utf-8"))
    payload["payloadless_useful_execution_fields_per_row"] = 3
    payload["payloadless_useful_execution_useful_work_units"] = (
        payload["payloadless_useful_execution_rows_consumed"] * 3
    )
    payload["payloadless_useful_execution_useful_work_coverage"] = 0.75
    payload["payloadless_useful_execution_native_consumer_has_useful_work"] = False
    execution_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json:"
        "payloadless_useful_execution_fields_per_row_mismatch"
    ) in failures
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_gate_ready"
        ]
        is False
    )
    assert (
        "default_kernel_consumer_future_wna16_payloadless_useful_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_useful_repeat_child_sha_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    repeat_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    payload = json.loads(repeat_path.read_text(encoding="utf-8"))
    payload["repeat_output_sha256s"][0] = "0" * 64
    repeat_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:repeat_0_sha256_mismatch"
        in result["default_readonly_gate_required_evidence_check"]["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_useful_repeat_child_wna16_arg_use(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    repeat_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    child_path = tmp_path / "reports/default_gate_repeat_000.json"
    child_payload = json.loads(child_path.read_text(encoding="utf-8"))
    child_payload["uses_current_wna16_args"] = True
    child_path.write_text(json.dumps(child_payload) + "\n", encoding="utf-8")
    repeat_payload = json.loads(repeat_path.read_text(encoding="utf-8"))
    repeat_payload["repeat_output_sha256s"][0] = hashlib.sha256(
        child_path.read_bytes()
    ).hexdigest()
    repeat_path.write_text(json.dumps(repeat_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "repeat_0_uses_current_wna16_args_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payloadless_useful_repeat_harness_identity(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    repeat_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    harness_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_benchmark.json"
    )
    harness_payload = json.loads(harness_path.read_text(encoding="utf-8"))
    harness_payload["artifact_kind"] = "fake_payloadless_harness"
    harness_path.write_text(json.dumps(harness_payload) + "\n", encoding="utf-8")
    repeat_payload = json.loads(repeat_path.read_text(encoding="utf-8"))
    repeat_payload["harness_sha256"] = hashlib.sha256(
        harness_path.read_bytes()
    ).hexdigest()
    repeat_path.write_text(json.dumps(repeat_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "harness_artifact_kind_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payloadless_useful_repeat_native_stub_payload(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    repeat_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    native_stub_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution_native_stub.json"
    )
    native_stub_payload = json.loads(native_stub_path.read_text(encoding="utf-8"))
    native_stub_payload["payload_bytes"] = 8
    native_stub_payload["wna16_side_consumer_variant_execution_payload_bytes"] = 8
    native_stub_path.write_text(
        json.dumps(native_stub_payload) + "\n",
        encoding="utf-8",
    )
    native_stub_sha = hashlib.sha256(native_stub_path.read_bytes()).hexdigest()

    timing_seed_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution_native.json"
    )
    timing_seed_payload = json.loads(timing_seed_path.read_text(encoding="utf-8"))
    timing_seed_payload["native_stub_output_sha256"] = native_stub_sha
    timing_seed_path.write_text(
        json.dumps(timing_seed_payload) + "\n",
        encoding="utf-8",
    )
    timing_seed_sha = hashlib.sha256(timing_seed_path.read_bytes()).hexdigest()

    repeat_payload = json.loads(repeat_path.read_text(encoding="utf-8"))
    repeat_payload["native_timing_seed_sha256"] = timing_seed_sha
    for idx, repeat_child_label in enumerate(repeat_payload["repeat_output_jsons"]):
        repeat_child_path = tmp_path / str(repeat_child_label)
        repeat_child_payload = json.loads(
            repeat_child_path.read_text(encoding="utf-8")
        )
        repeat_child_payload["native_stub_output_sha256"] = native_stub_sha
        repeat_child_path.write_text(
            json.dumps(repeat_child_payload) + "\n",
            encoding="utf-8",
        )
        repeat_payload["repeat_output_sha256s"][idx] = hashlib.sha256(
            repeat_child_path.read_bytes()
        ).hexdigest()
    repeat_path.write_text(json.dumps(repeat_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "native_timing_seed_native_stub_payload_bytes_mismatch"
    ) in failures
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "native_timing_seed_native_stub_wna16_side_consumer_variant_execution_payload_bytes_mismatch"
    ) in failures
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "repeat_0_native_stub_payload_bytes_mismatch"
    ) in failures
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "repeat_0_native_stub_wna16_side_consumer_variant_execution_payload_bytes_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payloadless_useful_repeat_native_stub_field_hash(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    repeat_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.json"
    )
    native_stub_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution_native_stub.json"
    )
    native_stub_payload = json.loads(native_stub_path.read_text(encoding="utf-8"))
    native_stub_payload[
        "wna16_side_consumer_variant_execution_descriptor_ptr_read_hash_accumulator"
    ] = "0000000000000000"
    native_stub_path.write_text(
        json.dumps(native_stub_payload) + "\n",
        encoding="utf-8",
    )
    native_stub_sha = hashlib.sha256(native_stub_path.read_bytes()).hexdigest()

    timing_seed_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution_native.json"
    )
    timing_seed_payload = json.loads(timing_seed_path.read_text(encoding="utf-8"))
    timing_seed_payload["native_stub_output_sha256"] = native_stub_sha
    timing_seed_path.write_text(
        json.dumps(timing_seed_payload) + "\n",
        encoding="utf-8",
    )
    timing_seed_sha = hashlib.sha256(timing_seed_path.read_bytes()).hexdigest()

    repeat_payload = json.loads(repeat_path.read_text(encoding="utf-8"))
    repeat_payload["native_timing_seed_sha256"] = timing_seed_sha
    for idx, repeat_child_label in enumerate(repeat_payload["repeat_output_jsons"]):
        repeat_child_path = tmp_path / str(repeat_child_label)
        repeat_child_payload = json.loads(
            repeat_child_path.read_text(encoding="utf-8")
        )
        repeat_child_payload["native_stub_output_sha256"] = native_stub_sha
        repeat_child_path.write_text(
            json.dumps(repeat_child_payload) + "\n",
            encoding="utf-8",
        )
        repeat_payload["repeat_output_sha256s"][idx] = hashlib.sha256(
            repeat_child_path.read_bytes()
        ).hexdigest()
    repeat_path.write_text(json.dumps(repeat_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "native_timing_seed_native_stub_descriptor_ptr_hash_mismatch"
    ) in failures
    assert (
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:"
        "repeat_0_native_stub_descriptor_ptr_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_downgrades_wna16_ready_on_source_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    mismatched_input_path = (
        tmp_path / "reports/default_gate_wna16_source_mismatch_input.json"
    )
    mismatched_payload = _online_merged_arg_slot_multiprogram_input_payload()
    mismatched_payload["_merge_context"]["row_spans"][0][
        "source_table_object_hash"
    ] = "different-table"
    mismatched_input_path.write_text(
        json.dumps(mismatched_payload) + "\n",
        encoding="utf-8",
    )
    runner_path = (
        tmp_path
        / "reports/default_gate_wna16_side_consumer_variant_execution_128strict_runner.json"
    )
    runner_payload = json.loads(runner_path.read_text(encoding="utf-8"))
    runner_payload["merged_output_json"] = (
        "reports/default_gate_wna16_source_mismatch_input.json"
    )
    runner_path.write_text(json.dumps(runner_payload) + "\n", encoding="utf-8")
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payloadless_payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    payloadless_payload["payloadless_execution_runner_sha256"] = hashlib.sha256(
        runner_path.read_bytes()
    ).hexdigest()
    payloadless_path.write_text(
        json.dumps(payloadless_payload) + "\n",
        encoding="utf-8",
    )
    variant_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution.json"
    )
    variant_payload = json.loads(variant_path.read_text(encoding="utf-8"))
    variant_payload["payloadless_sha256"] = hashlib.sha256(
        payloadless_path.read_bytes()
    ).hexdigest()
    variant_path.write_text(json.dumps(variant_payload) + "\n", encoding="utf-8")
    useful_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_useful_consumer.json"
    )
    useful_payload = json.loads(useful_path.read_text(encoding="utf-8"))
    useful_payload["execution_sha256"] = hashlib.sha256(
        variant_path.read_bytes()
    ).hexdigest()
    useful_path.write_text(json.dumps(useful_payload) + "\n", encoding="utf-8")
    payloadless_useful_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.json"
    )
    payloadless_useful_payload = json.loads(
        payloadless_useful_path.read_text(encoding="utf-8")
    )
    payloadless_useful_payload["execution_sha256"] = hashlib.sha256(
        variant_path.read_bytes()
    ).hexdigest()
    payloadless_useful_payload["useful_consumer_sha256"] = hashlib.sha256(
        useful_path.read_bytes()
    ).hexdigest()
    payloadless_useful_path.write_text(
        json.dumps(payloadless_useful_payload) + "\n",
        encoding="utf-8",
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["default_kernel_consumer_wna16_side_variant_base_ready"] is True
    assert summary["default_kernel_consumer_wna16_side_variant_ready"] is False
    assert (
        summary[
            "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count"
        ]
        == 1
    )
    assert (
        summary["default_kernel_consumer_next_runtime_stage"]
        == "refresh_wna16_side_variant_source_provenance"
    )


def test_premap_lab_preflight_downgrades_wna16_ready_on_unprovable_source(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    online_input_path = (
        tmp_path / "reports/default_gate_online_merged_arg_slot_multiprogram_input.json"
    )
    online_payload = json.loads(online_input_path.read_text(encoding="utf-8"))
    online_payload["_merge_context"]["source_contexts"][0].pop("sequence_id")
    online_input_path.write_text(json.dumps(online_payload) + "\n", encoding="utf-8")
    wna16_input_path = (
        tmp_path / "reports/default_gate_wna16_side_consumer_variant_execution_input.json"
    )
    wna16_payload = json.loads(wna16_input_path.read_text(encoding="utf-8"))
    wna16_payload["_merge_context"]["source_contexts"][0].pop("sequence_id")
    wna16_input_path.write_text(json.dumps(wna16_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["default_kernel_consumer_wna16_side_variant_base_ready"] is True
    assert summary["default_kernel_consumer_wna16_side_variant_ready"] is False
    assert (
        summary[
            "default_kernel_consumer_online_merged_multiprogram_source_identity_coverage"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_wna16_side_variant_source_identity_coverage"]
        is False
    )
    assert (
        summary["default_kernel_consumer_next_runtime_stage"]
        == "refresh_wna16_side_variant_source_provenance"
    )


def test_premap_lab_preflight_requires_prefetch_lab_default_gate(
    tmp_path: Path,
) -> None:
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    ready_report = (
        tmp_path
        / "outputs/reports/prefetch_cache_manager/"
        "measured_ready_time_gate_gpu1_dolly8_gen4.json"
    )
    ready_report.write_text(
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": True,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "prefetch_lab_default_gate_check_failed" in result["failures"]
    check = result["prefetch_lab_default_gate_check"]
    assert check["passed"] is False
    assert (
        "full_fetch:ready_time_gate_report_allows_full_fetch"
        in check["failures"]
    )
    summary = result["lab_gate_status_summary"]
    assert summary["prefetch_lab_default_gate_passed"] is False
    assert summary["prefetch_lab_default_gate_decision_status"] == "failed"
    assert (
        "full_fetch:ready_time_gate_report_allows_full_fetch"
        in summary["prefetch_lab_default_gate_failures"]
    )
    assert summary["prefetch_lab_default_full_fetch_passed"] is False
    assert summary["prefetch_lab_default_full_fetch_failures"] == [
        "ready_time_gate_report_allows_full_fetch"
    ]
    assert summary["prefetch_lab_default_metadata_passed"] is True
    assert summary["prefetch_lab_default_metadata_failures"] == []
    assert summary["prefetch_lab_default_premap_passed"] is True
    assert summary["prefetch_lab_default_premap_failures"] == []
    assert (
        summary["prefetch_lab_default_full_fetch_decision"]
        == "blocked_by_ready_time_measured_copy"
    )


def test_premap_lab_preflight_accepts_program_view_ptr_strict_requirement(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        require_program_view_ptr_abi=True,
    )

    assert result["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["default_kernel_consumer_program_view_ptr_required"] is True
    assert summary["default_kernel_consumer_program_view_ptr_checked"] is True
    assert (
        summary["default_kernel_consumer_program_view_ptr_source_matches_schema"]
        is True
    )
    assert (
        summary["default_kernel_consumer_program_view_ptr_row_count_matches_dispatch"]
        is True
    )
    assert (
        summary["default_kernel_consumer_program_view_ptr_required_fields_visible"]
        is True
    )
    assert (
        summary["default_kernel_consumer_program_view_ptr_safety_matches_required"]
        is True
    )


def test_premap_lab_preflight_rejects_program_view_ptr_strict_row_count_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_consumer_program_view_ptr_row_ok_count"] = 519
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        require_program_view_ptr_abi=True,
    )

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_program_view_ptr_row_count_mismatch"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_request_launch_ptr_all_field_read_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_launch_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary.json"
    )
    payload = json.loads(request_launch_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_request_launch_ptr_summary_aux_metadata_handle_read_row_ok_count"
    ] = 519
    _write(request_launch_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_request_launch_ptr_all_handle_fields_unchecked"
        in result["failures"]
    )


def _run_preflight_with_modified_default_runner(
    tmp_path: Path,
    mutate_runner: Callable[[dict[str, object]], None],
    **preflight_kwargs: object,
) -> dict[str, object]:
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    runner = json.loads(runner_path.read_text(encoding="utf-8"))
    mutate_runner(runner)
    _write(runner_path, json.dumps(runner) + "\n")

    return run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        **preflight_kwargs,
    )


def test_premap_lab_preflight_summary_marks_invalid_row_hashchain(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch[
            "future_kernel_native_dispatch_ptr_consumer_hash_accumulator"
        ] = "not_hex"

    result = _run_preflight_with_modified_default_runner(tmp_path, _mutate)
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is True
    )


def test_premap_lab_preflight_summary_marks_projection_hash_mismatch(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch[
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator"
        ] = "4820"

    result = _run_preflight_with_modified_default_runner(tmp_path, _mutate)
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked"
        ]
        is False
    )


def test_premap_lab_preflight_summary_marks_consumer_view_projection_hash_mismatch(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch[
            "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
        ] = "4820"

    result = _run_preflight_with_modified_default_runner(tmp_path, _mutate)
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_consumer_view_handle_projection_hash_accumulator"
        ]
        == "4820"
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked"
        ]
        is False
    )


def test_premap_lab_preflight_summary_rejects_invalid_consumer_view_projection_hash(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch[
            "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
        ] = "not_hex"

    result = _run_preflight_with_modified_default_runner(tmp_path, _mutate)
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_consumer_view_handle_projection_hash_accumulator"
        ]
        is None
    )


def test_premap_lab_preflight_summary_allows_missing_consumer_view_projection_hash(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch.pop(
            "future_kernel_native_consumer_view_handle_projection_hash_accumulator",
            None,
        )

    result = _run_preflight_with_modified_default_runner(tmp_path, _mutate)
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is True
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_consumer_view_handle_projection_hash_accumulator"
        ]
        is None
    )


def test_premap_lab_preflight_summary_defers_hashchain_hard_failures(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch[
            "future_kernel_native_dispatch_ptr_consumer_hash_accumulator"
        ] = "not_hex"
        dispatch[
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator"
        ] = "4820"

    result = _run_preflight_with_modified_default_runner(
        tmp_path,
        _mutate,
        defer_online_prelaunch_runner_evidence=True,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is True
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is False
    )


def test_premap_lab_preflight_summary_allows_missing_hashchain_hard_failures(
    tmp_path: Path,
):
    def _mutate(runner: dict[str, object]) -> None:
        dispatch = runner["future_kernel_native_consumer_dispatch_stub_summary"]
        assert isinstance(dispatch, dict)
        dispatch[
            "future_kernel_native_dispatch_ptr_consumer_hash_accumulator"
        ] = "not_hex"
        dispatch[
            "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator"
        ] = "4820"

    result = _run_preflight_with_modified_default_runner(
        tmp_path,
        _mutate,
        allow_missing_evidence=True,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is True
    assert (
        summary["default_kernel_consumer_dispatch_runner_row_hashchain_all_valid"]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_missing_optional_future_args_coverage(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    gate_path = tmp_path / default_gate
    gate_text = gate_path.read_text(encoding="utf-8")
    gate_text = gate_text.split("optional_evidence_paths:\n", maxsplit=1)[0]
    gate_path.write_text(gate_text, encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    assert result["passed"] is False
    assert (
        "default_kernel_consumer_future_kernel_args_total_mirror_coverage_incomplete"
        in result["failures"]
    )
    assert summary["required_evidence"]["passed_count"] == 71
    assert summary["default_optional_evidence_passed"] is True
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_total_full_field_mirror_coverage"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_32input_runner_backed_by_16input_artifact(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    gate_path = tmp_path / default_gate
    gate_text = gate_path.read_text(encoding="utf-8")
    gate_text = gate_text.replace(
        "reports/default_gate_native_online_prelaunch_canary_runner_32.json",
        "reports/default_gate_native_online_prelaunch_canary_runner.json",
    )
    gate_path.write_text(gate_text, encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_online_input_check_count_invalid"
    ) in failures


def test_premap_lab_preflight_rejects_32input_artifact_check_backed_by_16input_artifact(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    gate_path = tmp_path / default_gate
    gate_text = gate_path.read_text(encoding="utf-8")
    gate_text = gate_text.replace(
        "reports/default_gate_native_online_prelaunch_canary_artifact_check_32.json",
        "reports/default_gate_native_online_prelaunch_canary_artifact_check.json",
    )
    gate_path.write_text(gate_text, encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_min_online_inputs_invalid"
    ) in failures
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_online_input_check_count_invalid"
    ) in failures


def test_premap_lab_preflight_rejects_32input_artifact_check_missing_count_fields(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    artifact_path = (
        tmp_path
        / "reports/default_gate_native_online_prelaunch_canary_artifact_check_32.json"
    )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    payload.pop("min_online_inputs")
    payload.pop("runner_online_prelaunch_input_check_count")
    artifact_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_min_online_inputs_missing"
    ) in failures
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_online_input_check_count_missing"
    ) in failures


def test_premap_lab_preflight_rejects_present_optional_per_field_canary_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    optional_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_per_field_canary.json"
    )
    payload = json.loads(optional_path.read_text(encoding="utf-8"))
    payload["compiled_macros"][
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR"
    ] = False
    optional_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_optional_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_optional_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json:"
        "native_typed_consumer_stub_MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_not_enabled"
    ) in failures


def test_premap_lab_preflight_rejects_present_optional_packed_weight_canary_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    optional_path = (
        tmp_path
        / "reports/default_gate_packed_weight_single_field_handle_handoff_canary_smoke.json"
    )
    payload = json.loads(optional_path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    prefix = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_"
    )
    metrics[f"{prefix}field_name"] = "scale_metadata_handle"
    optional_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "packed_weight_single_field_handle_handoff_canary_smoke_json:"
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_field_name_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_future_wna16_single_field_all_fields_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    summary_path = (
        tmp_path
        / "reports/default_gate_future_wna16_single_field_handoff_all_fields_128strict_summary.json"
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["fields"]["packed_weight_descriptor"]["row_ok_count"] = 519
    summary_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_wna16_single_field_handoff_all_fields_128strict_summary_json:"
        "packed_weight_descriptor_row_ok_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_future_wna16_fourth_field_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_fourth_field_handoff_canary.json"
    )
    payload = json.loads(canary_path.read_text(encoding="utf-8"))
    payload["fourth_field_name"] = "scale_metadata_handle"
    canary_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_wna16_typed_slot_fourth_field_handoff_canary_json:"
        "fourth_field_name_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_future_wna16_fourth_field_expected_unsafe_flag(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_fourth_field_handoff_canary.json"
    )
    payload = json.loads(canary_path.read_text(encoding="utf-8"))
    payload["expected_kernel_arg_pass_allowed"] = True
    canary_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_wna16_typed_slot_fourth_field_handoff_canary_json:"
        "expected_kernel_arg_pass_allowed_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_arg_slot_source_count(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    merged_input_path = (
        tmp_path / "reports/default_gate_online_merged_arg_slot_multiprogram_input.json"
    )
    payload = json.loads(merged_input_path.read_text(encoding="utf-8"))
    payload["_merge_context"]["source_count"] = 1
    merged_input_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:"
        "online_merged_multiprogram_arg_slot_source_count_too_small"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_source_context_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    merged_input_path = (
        tmp_path / "reports/default_gate_online_merged_arg_slot_multiprogram_input.json"
    )
    payload = json.loads(merged_input_path.read_text(encoding="utf-8"))
    payload["_merge_context"]["source_contexts"][0]["row_count"] = 1
    merged_input_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:"
        "online_merged_multiprogram_arg_slot_source_context_0_row_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_window(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["dispatch_row_offset"] = 256
    payload["dispatch_active_rows"] = 264
    payload["dispatch_expected_program_count"] = 2
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_dispatch_offset_not_zero"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_without_projection_coverage(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["handle_projection_all_handle_fields_checked"] = False
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_handle_projection_all_fields_unchecked"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_mirror_runner_stub_path_mismatch(
    tmp_path: Path,
):
    cases = (
        (
            "aux_metadata_handle",
            "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json",
            "reports/default_gate_online_merged_future_native_arg_slot_aux_metadata_runner.json",
        ),
        (
            "descriptor_ptr",
            "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json",
            "reports/default_gate_online_merged_future_native_arg_slot_descriptor_ptr_runner.json",
        ),
        (
            "packed_weight_descriptor",
            "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json",
            "reports/default_gate_online_merged_future_native_arg_slot_packed_weight_runner.json",
        ),
    )
    for field, evidence_label, runner_relpath in cases:
        root = tmp_path / field
        default_gate = _write_gate(root, "default_gate", "default_gate.json")
        runner_path = root / runner_relpath
        payload = json.loads(runner_path.read_text(encoding="utf-8"))
        payload["stub_output_json"] = (
            "reports/default_gate_online_merged_future_native_endpoint_canary.json"
        )
        runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        canary_gate = _write_gate(root, "canary_gate", "canary_gate.json")
        trace_config = _write_trace_config(
            root,
            "longrun",
            readonly_gate_path=default_gate,
        )

        result = run_premap_lab_preflight(
            root=root,
            runtime_pattern="configs/runtime/*.yaml",
            trace_configs=[trace_config],
            default_readonly_gate=default_gate,
            canary_gate=canary_gate,
        )

        assert result["passed"] is False
        assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
        failures = result["default_readonly_gate_required_evidence_check"]["failures"]
        assert (
            f"{evidence_label}:"
            "online_merged_multiprogram_arg_slot_runner_stub_output_path_mismatch"
        ) in failures


def test_premap_lab_preflight_rejects_required_wna16_adjacent_runner_bad_stub_output(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_wna16_adjacent_typed_slot_runner.json"
    )
    runner_payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_output = runner_payload["stub_output_json"]
    assert isinstance(stub_output, str)
    stub_path = tmp_path / stub_output
    stub_payload = json.loads(stub_path.read_text(encoding="utf-8"))
    stub_payload[
        "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_error_count"
    ] = 1
    stub_path.write_text(json.dumps(stub_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_wna16_adjacent_typed_slot_canary_json:"
        "online_merged_multiprogram_arg_slot_runner_stub:"
        "wna16_adjacent_typed_slot_"
        "future_kernel_native_consumer_wna16_adjacent_typed_slot_"
        "summary_error_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_wna16_adjacent_runner_stub_path_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_wna16_adjacent_typed_slot_runner.json"
    )
    runner_payload = json.loads(runner_path.read_text(encoding="utf-8"))
    runner_payload["stub_output_json"] = (
        "reports/default_gate_future_native_arg_slot_multiprogram_canary.json"
    )
    runner_path.write_text(json.dumps(runner_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_wna16_adjacent_typed_slot_canary_json:"
        "online_merged_multiprogram_arg_slot_runner_stub_output_path_mismatch"
    ) in failures
    assert not any("stub_output_read_failed" in failure for failure in failures)


def test_premap_lab_preflight_rejects_required_online_merged_runner_without_kernel_launch_context(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["require_kernel_launch_context_abi"] = False
    payload["kernel_launch_context_checked"] = False
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_require_kernel_launch_context_abi_missing"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_kernel_launch_context_checked_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_without_invocation(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["require_kernel_invocation_abi"] = False
    payload["kernel_invocation_checked"] = False
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_require_kernel_invocation_abi_missing"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_kernel_invocation_checked_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_without_invocation_entry(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["require_kernel_invocation_entry_abi"] = False
    payload["kernel_invocation_entry_checked"] = False
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_require_kernel_invocation_entry_abi_missing"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_kernel_invocation_entry_checked_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_without_endpoint(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["require_kernel_endpoint_abi"] = False
    payload["kernel_endpoint_checked"] = False
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_require_kernel_endpoint_abi_missing"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_kernel_endpoint_checked_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_compact_summary_error_count_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_consumer_invocation_entry_error_count"] = 0
    stub_summary[
        "future_kernel_native_consumer_invocation_entry_summary_error_count"
    ] = 1
    stub_summary["future_kernel_native_consumer_endpoint_error_count"] = 0
    stub_summary["future_kernel_native_consumer_endpoint_summary_error_count"] = 1
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_stub_summary_"
        "future_kernel_native_consumer_invocation_entry_summary_error_count_inconsistent"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_stub_summary_"
        "future_kernel_native_consumer_endpoint_summary_error_count_inconsistent"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_runner_invocation_cross_layer_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary[
        "future_kernel_native_consumer_invocation_summary_row_hash_accumulator"
    ] = "0000000000000004"
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_invocation_stub_summary_row_hash_accumulator_mismatch"
    ) in failures


def test_premap_lab_preflight_allows_required_descriptor_online_merged_runner_without_kernel_launch_context(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_arg_slot_descriptor_ptr_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload.pop("require_kernel_launch_context_abi", None)
    payload.pop("require_kernel_launch_descriptor_abi", None)
    payload.pop("require_launch_envelope_args_abi", None)
    payload.pop("require_launch_envelope_args_ptr_abi", None)
    for key in list(payload):
        if key.startswith("kernel_launch_context_"):
            payload.pop(key)
    stub_summary = payload.get("stub_summary")
    assert isinstance(stub_summary, dict)
    for key in list(stub_summary):
        if "kernel_launch_context" in key:
            stub_summary.pop(key)
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["default_required_evidence_passed"] is True
    assert (
        "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_kernel_launch_context_checked_mismatch"
    ) not in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_required_online_merged_runner_invalid_consumer_view_projection_hash(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    stub_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_canary.json"
    )
    payload = json.loads(stub_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator"
    ] = "not_hex"
    stub_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_stub:"
        "multiprogram_arg_slot_handle_projection_hash_missing"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:"
        "multiprogram_arg_slot_handle_projection_hash_missing"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_program_view_row_count_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    stub_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_canary.json"
    )
    payload = json.loads(stub_path.read_text(encoding="utf-8"))
    payload["future_kernel_native_consumer_program_view_row_count"] = 519
    stub_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_stub:"
        "multiprogram_arg_slot_"
        "future_kernel_native_consumer_program_view_row_count_mismatch"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:"
        "multiprogram_arg_slot_"
        "future_kernel_native_consumer_program_view_row_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_online_merged_program_view_iteration_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    stub_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_canary.json"
    )
    payload = json.loads(stub_path.read_text(encoding="utf-8"))
    payload["future_kernel_native_consumer_program_view_program_iteration_hash"] = (
        "0000000000000000"
    )
    stub_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_stub:"
        "multiprogram_arg_slot_program_view_iteration_hash_mismatch"
    ) in failures
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:"
        "multiprogram_arg_slot_program_view_iteration_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_consumer_view_row_window_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_consumer_view_row_offset"] = 1
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_consumer_view_row_window_mismatch"
        in result["failures"]
    )
    assert summary["default_kernel_consumer_dispatch_row_window"] == {
        "row_offset": 0,
        "row_limit": 520,
        "rows_per_program": 256,
    }
    assert summary["default_kernel_consumer_consumer_view_row_window"] == {
        "row_offset": 1,
        "row_limit": 520,
        "rows_per_program": 256,
    }
    assert (
        summary[
            "default_kernel_consumer_consumer_view_row_window_matches_dispatch"
        ]
        is False
    )


def test_premap_lab_preflight_marks_consumer_view_row_window_fallback_source(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_dispatch_consumer_checked"] = False
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_missing_evidence=True,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is True
    assert (
        summary["default_kernel_consumer_consumer_view_status_source"]
        == "online_merged_arg_slot_summary"
    )
    assert (
        summary["default_kernel_consumer_consumer_view_row_window_source"]
        == "dispatch_runner_summary"
    )
    assert summary["default_kernel_consumer_consumer_view_row_window"] == {
        "row_offset": 0,
        "row_limit": 2,
        "rows_per_program": 256,
    }


def test_premap_lab_preflight_rejects_consumer_view_safety_contract_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_consumer_view_passed_to_kernel"] = True
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_consumer_view_safety_contract_mismatch"
        in result["failures"]
    )
    assert (
        summary[
            "default_kernel_consumer_consumer_view_safety_matches_required"
        ]
        is False
    )
    assert summary["default_kernel_consumer_consumer_view_passed_to_kernel"] is True


def test_premap_lab_preflight_rejects_consumer_program_view_safety_contract_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_consumer_program_view_passed_to_kernel"] = True
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_consumer_program_view_safety_contract_mismatch"
        in result["failures"]
    )
    assert (
        summary[
            "default_kernel_consumer_consumer_program_view_safety_matches_required"
        ]
        is False
    )
    assert (
        summary["default_kernel_consumer_consumer_program_view_passed_to_kernel"]
        is True
    )


def test_premap_lab_preflight_rejects_missing_consumer_view_source(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary.pop("future_kernel_native_consumer_view_source")
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_consumer_view_safety_contract_mismatch"
        in result["failures"]
    )
    assert summary["default_kernel_consumer_consumer_view_source"] is None
    assert (
        summary["default_kernel_consumer_consumer_view_source_matches_schema"]
        is False
    )


def test_premap_lab_preflight_allows_consumer_view_row_window_mismatch_when_missing_evidence_allowed(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary["future_kernel_native_consumer_view_row_offset"] = 1
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_missing_evidence=True,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is True
    assert (
        summary[
            "default_kernel_consumer_consumer_view_row_window_matches_dispatch"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_required_online_merged_runner_not_targeting_gpu1(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_online_merged_future_native_endpoint_runner.json"
    )
    payload = json.loads(runner_path.read_text(encoding="utf-8"))
    payload["device"] = 0
    payload["hip_visible_devices"] = None
    runner_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:"
        "online_merged_multiprogram_arg_slot_runner_device_not_gpu1"
    ) in failures


def test_premap_lab_preflight_rejects_required_arg_slot_packed_weight_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    optional_path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_packed_weight_canary.json"
    )
    payload = json.loads(optional_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    optional_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json:"
        "standalone_arg_slot_packed_weight_"
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_arg_slot_missing_field_macros(
    tmp_path: Path,
):
    cases = (
        (
            "descriptor_ptr",
            "future_native_arg_slot_descriptor_ptr_canary",
            "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
            "standalone_arg_slot_descriptor_ptr_",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
        ),
        (
            "packed_weight_descriptor",
            "future_native_arg_slot_packed_weight_canary",
            "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
            "standalone_arg_slot_packed_weight_",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
        ),
        (
            "aux_metadata_handle",
            "future_native_arg_slot_aux_metadata_canary",
            "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
            "standalone_arg_slot_aux_metadata_",
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
        ),
    )
    for field, path_suffix, evidence_label, failure_prefix, handle_macro in cases:
        root = tmp_path / field
        default_gate = _write_gate(root, "default_gate", "default_gate.json")
        optional_path = root / f"reports/default_gate_{path_suffix}.json"
        payload = json.loads(optional_path.read_text(encoding="utf-8"))
        payload["compiled_macros"][handle_macro] = False
        optional_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        canary_gate = _write_gate(root, "canary_gate", "canary_gate.json")
        trace_config = _write_trace_config(
            root,
            "longrun",
            readonly_gate_path=default_gate,
        )

        result = run_premap_lab_preflight(
            root=root,
            runtime_pattern="configs/runtime/*.yaml",
            trace_configs=[trace_config],
            default_readonly_gate=default_gate,
            canary_gate=canary_gate,
        )

        assert result["passed"] is False
        assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
        failures = result["default_readonly_gate_required_evidence_check"]["failures"]
        assert (
            f"{evidence_label}:{failure_prefix}{handle_macro}_not_enabled"
        ) in failures


def test_premap_lab_preflight_rejects_default_gate_without_typed_consumer_contract(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        typed_consumer_required=False,
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert result["default_readonly_gate_contract_check"]["failures"] == [
        "kernel_side_typed_consumer_object_required_mismatch",
    ]


def test_premap_lab_preflight_rejects_default_gate_without_dispatch_ptr_contract(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    text = gate_path.read_text()
    text = text.replace(
        "  future_kernel_native_dispatch_ptr_consumer_required: true\n",
        "  future_kernel_native_dispatch_ptr_consumer_required: false\n",
    )
    _write(gate_path, text)
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert (
        "future_kernel_native_dispatch_ptr_consumer_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )


def test_premap_lab_preflight_conditions_online_arg_slot_coverage_on_contract(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    text = gate_path.read_text()
    text = text.replace(
        "  future_kernel_native_arg_slot_online_total_mirror_coverage_required: true\n",
        "  future_kernel_native_arg_slot_online_total_mirror_coverage_required: false\n",
    )
    _write(gate_path, text)
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    descriptor_summary = payload[
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary"
    ]
    descriptor_summary[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert (
        "future_kernel_native_arg_slot_online_total_mirror_coverage_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )
    assert (
        "default_kernel_consumer_arg_slot_online_total_mirror_coverage_incomplete"
        not in result["failures"]
    )
    summary = result["lab_gate_status_summary"]
    assert (
        summary["default_kernel_consumer_arg_slot_online_total_mirror_coverage_required"]
        is False
    )
    assert (
        summary["default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage"]
        is False
    )


def test_premap_lab_preflight_rejects_incomplete_future_kernel_args_mirror_coverage(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    text = gate_path.read_text()
    text = text.replace(
        "  future_kernel_args_descriptor_ptr_mirror_canary_json: "
        "reports/default_gate_future_kernel_args_descriptor_ptr_canary.json\n",
        "",
    )
    _write(gate_path, text)
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_future_kernel_args_total_mirror_coverage_incomplete"
        in result["failures"]
    )
    summary = result["lab_gate_status_summary"]
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_total_mirror_coverage_required"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_future_kernel_args_total_full_field_mirror_coverage"
        ]
        is False
    )


def test_premap_lab_preflight_reports_observed_contract_requirement_fields(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    text = gate_path.read_text()
    text = text.replace(
        "  kernel_side_typed_row_consumer_path_required: true\n",
        "  kernel_side_typed_row_consumer_path_required: false\n",
    )
    text = text.replace(
        "  future_kernel_native_dispatch_consumer_full_table_required: true\n",
        "  future_kernel_native_dispatch_consumer_full_table_required: false\n",
    )
    text = text.replace(
        "  future_kernel_native_dispatch_ptr_consumer_required: true\n",
        "  future_kernel_native_dispatch_ptr_consumer_required: false\n",
    )
    text = text.replace(
        "  native_typed_consumer_bridge_passed_to_kernel_required: false\n",
        "  native_typed_consumer_bridge_passed_to_kernel_required: true\n",
    )
    _write(gate_path, text)
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert (
        "kernel_side_typed_row_consumer_path_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )
    assert (
        "future_kernel_native_dispatch_consumer_full_table_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )
    assert (
        "future_kernel_native_dispatch_ptr_consumer_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )
    assert (
        "native_typed_consumer_bridge_passed_to_kernel_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )
    summary = result["lab_gate_status_summary"]
    assert summary["kernel_side_typed_row_consumer_path_required"] is False
    assert summary["default_kernel_consumer_dispatch_full_table_required"] is False
    assert summary["default_kernel_consumer_dispatch_ptr_required"] is False
    assert summary["passed_to_kernel_required"] is True


def test_premap_lab_preflight_reports_missing_observed_contract_field_as_unknown(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    text = gate_path.read_text()
    text = text.replace(
        "  native_typed_consumer_bridge_required: true\n",
        "",
    )
    _write(gate_path, text)
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_bridge_required_mismatch"
        in result["default_readonly_gate_contract_check"]["failures"]
    )
    summary = result["lab_gate_status_summary"]
    assert summary["default_contract_observed_available"] is True
    assert summary["native_typed_consumer_bridge_required"] is None


def test_premap_lab_preflight_rejects_non_mapping_default_gate_contract(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    payload = yaml.safe_load(gate_path.read_text())
    payload["contract"] = "broken"
    _write(gate_path, yaml.safe_dump(payload, sort_keys=False))
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert result["default_readonly_gate_contract_check"]["failures"] == [
        "contract_type_mismatch"
    ]
    summary = result["lab_gate_status_summary"]
    assert summary["default_contract_observed_available"] is False
    assert summary["native_typed_consumer_bridge_required"] is None


def test_premap_lab_preflight_reports_bad_contract_value_type_as_unknown(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    payload = yaml.safe_load(gate_path.read_text())
    payload["contract"]["native_typed_consumer_bridge_required"] = "true"
    payload["contract"]["native_typed_consumer_bridge_payload_bytes_required"] = "0"
    _write(gate_path, yaml.safe_dump(payload, sort_keys=False))
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    failures = result["default_readonly_gate_contract_check"]["failures"]
    assert "native_typed_consumer_bridge_required_mismatch" in failures
    assert "native_typed_consumer_bridge_payload_bytes_required_mismatch" in failures
    summary = result["lab_gate_status_summary"]
    assert summary["default_contract_observed_available"] is True
    assert summary["native_typed_consumer_bridge_required"] is None
    assert summary["payload_bytes_required"] is None


def test_premap_lab_preflight_rejects_bool_int_contract_aliasing(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    payload = yaml.safe_load(gate_path.read_text())
    payload["contract"]["native_typed_consumer_bridge_required"] = 1
    payload["contract"]["native_typed_consumer_bridge_payload_bytes_required"] = False
    _write(gate_path, yaml.safe_dump(payload, sort_keys=False))
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    failures = result["default_readonly_gate_contract_check"]["failures"]
    assert "native_typed_consumer_bridge_required_mismatch" in failures
    assert "native_typed_consumer_bridge_payload_bytes_required_mismatch" in failures


def test_premap_lab_preflight_rejects_bool_int_required_metric_aliasing(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    canary_path = (
        tmp_path
        / "reports/default_gate_aux_metadata_single_field_handle_handoff_canary_smoke.json"
    )
    payload = json.loads(canary_path.read_text())
    metrics = payload["metrics"]
    metrics[
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_passed_to_kernel_count"
    ] = False
    _write(canary_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "aux_metadata_single_field_handle_handoff_canary_smoke_json:"
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_passed_to_kernel_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_single_field_changes_kernel_launch_args(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    canary_path = (
        tmp_path
        / "reports/default_gate_descriptor_ptr_single_field_handle_handoff_canary_smoke.json"
    )
    payload = json.loads(canary_path.read_text())
    metrics = payload["metrics"]
    metrics[
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_changes_kernel_launch_args_count"
    ] = 1
    _write(canary_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "descriptor_ptr_single_field_handle_handoff_canary_smoke_json:"
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_changes_kernel_launch_args_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_default_gate_with_bad_schema_artifact(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    schema_path = tmp_path / "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    payload = _valid_schema_payload()
    payload["debug_macro_ladder"]["flags"][0]["default"] = "enabled"
    _write(schema_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    assert (
        "schema_check:debug_macro_default_not_disabled:"
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA"
    ) in result["default_kernel_consumer_schema_check"]["failures"]


def test_premap_lab_preflight_rejects_bad_required_schema_gate_check(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    schema_path = tmp_path / "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    payload = _valid_schema_payload()
    payload["required_gate_checks"]["passed_to_kernel_required"] = True
    _write(schema_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    assert (
        "schema_check:required_gate_checks.passed_to_kernel_required_mismatch:"
        "True!=False"
    ) in result["default_kernel_consumer_schema_check"]["failures"]


def test_premap_lab_preflight_rejects_non_mapping_required_schema_gate_checks(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    schema_path = tmp_path / "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    payload = _valid_schema_payload()
    payload["required_gate_checks"] = "not-a-mapping"
    _write(schema_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    failures = result["default_kernel_consumer_schema_check"]["failures"]
    assert "schema_check:required_gate_checks_not_mapping:str" in failures
    assert (
        "schema_check:required_gate_checks.consumer_view_required_mismatch:"
        "None!=True"
    ) in failures


def test_premap_lab_preflight_marks_projection_uncovered_when_schema_lacks_field(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    schema_path = tmp_path / "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    payload = _valid_schema_payload()
    native_consumer_abi = payload["native_consumer_abi"]
    assert isinstance(native_consumer_abi, dict)
    row_fields = native_consumer_abi["row_fields"]
    assert isinstance(row_fields, list)
    native_consumer_abi["row_fields"] = [
        row for row in row_fields if row.get("name") != "aux_metadata_handle"
    ]
    _write(schema_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )
    summary = result["lab_gate_status_summary"]

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    assert (
        "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_unchecked"
        in result["failures"]
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_hashchain_equal"
        ]
        is True
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_schema_covered"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_handle_projection_all_handle_fields_checked"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_default_gate_without_schema_artifact(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        include_schema_artifact=False,
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    assert result["default_kernel_consumer_schema_check"]["failures"] == [
        "schema_artifacts_missing_or_not_mapping"
    ]


def test_premap_lab_preflight_rejects_default_gate_without_typed_evidence(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        include_lab_evidence=False,
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert set(result["default_readonly_gate_required_evidence_check"]["failures"]) == {
        "native_typed_consumer_bridge_smoke_json:missing_evidence_path",
        "strict_native_stub_online_invocation_canary_128_gate_json:missing_evidence_path",
        "native_typed_consumer_stub_gpu1_canary_json:missing_evidence_path",
        "native_typed_consumer_stub_online_prelaunch_input_canary_json:missing_evidence_path",
        "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json:missing_evidence_path",
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:missing_evidence_path",
        "native_typed_consumer_stub_online_prelaunch_input_request_launch_canary_json:missing_evidence_path",
        "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json:missing_evidence_path",
        "native_typed_consumer_online_prelaunch_canary_runner_json:missing_evidence_path",
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:missing_evidence_path",
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:missing_evidence_path",
        "future_kernel_native_dispatch_ptr_standalone_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_standalone_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_multiprogram_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_canary_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json:missing_evidence_path",
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json:missing_evidence_path",
        "future_kernel_wna16_adjacent_typed_slot_canary_json:missing_evidence_path",
        "future_kernel_wna16_adjacent_typed_slot_stub_json:missing_evidence_path",
        "future_kernel_wna16_adjacent_typed_slot_standalone_canary_json:missing_evidence_path",
        "future_wna16_single_field_handoff_all_fields_128strict_summary_json:missing_evidence_path",
        "future_wna16_typed_slot_fourth_field_handoff_canary_json:missing_evidence_path",
        "future_wna16_typed_slot_all_four_field_consumer_json:missing_evidence_path",
        "future_wna16_kernel_side_typed_consumer_path_json:missing_evidence_path",
        "future_wna16_typed_slot_payloadless_execution_json:missing_evidence_path",
        "future_wna16_typed_slot_kernel_variant_execution_json:missing_evidence_path",
        "future_wna16_typed_slot_kernel_variant_useful_consumer_json:missing_evidence_path",
        "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_json:missing_evidence_path",
        "future_wna16_typed_slot_payloadless_useful_repeat_benchmark_json:missing_evidence_path",
        "future_wna16_typed_slot_payloadless_useful_runtime_ablation_json:missing_evidence_path",
        "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_json:missing_evidence_path",
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json:missing_evidence_path",
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json:missing_evidence_path",
        "wna16_side_consumer_variant_execution_128strict_runner_json:missing_evidence_path",
        "payload_cache_producer_state_native_canary_json:missing_evidence_path",
        "payload_cache_shifted_issue_runtime_shadow_gate_json:missing_evidence_path",
        "payload_cache_packet_export_manifest_json:missing_evidence_path",
        "payload_cache_producer_state_online_nonempty_issue_canary_json:missing_evidence_path",
        "payload_cache_producer_state_nonempty_issue_stub_json:missing_evidence_path",
        "payload_cache_producer_state_stream_native_canary_json:missing_evidence_path",
        "payload_cache_producer_state_packet_stream_native_canary_json:missing_evidence_path",
        "payload_cache_producer_state_packet_stream_native_canary_check_json:missing_evidence_path",
        "payload_cache_producer_state_inprocess_native_session_online_contract_json:missing_evidence_path",
        "payload_cache_online_native_producer_boundary_gap_json:missing_evidence_path",
        "payload_cache_demand_hit_shadow_publication_gate_json:missing_evidence_path",
        "payload_cache_consumer_visible_hit_blocked_gate_json:missing_evidence_path",
        "payload_cache_vllm_replay_visible_native_producer_contract_json:missing_evidence_path",
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json:missing_evidence_path",
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:missing_evidence_path",
        "payload_cache_manager_useful_work_ab_gate_json:missing_evidence_path",
        "payload_cache_manager_production_ab_preflight_json:missing_evidence_path",
        "strict_live_connected_readonly_128_gate_json:missing_evidence_path",
        "strict_native_typed_consumer_bridge_128_gate_json:missing_evidence_path",
        "strict_kernel_side_typed_consumer_object_128_gate_json:missing_evidence_path",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:missing_evidence_path",
        "strict_kernel_side_typed_row_consumer_path_128_gate_json:missing_evidence_path",
        "strict_single_field_handle_handoff_canary_128_gate_json:missing_evidence_path",
        "aux_metadata_single_field_handle_handoff_canary_smoke_json:missing_evidence_path",
        "descriptor_ptr_single_field_handle_handoff_canary_smoke_json:missing_evidence_path",
        "packed_weight_single_field_handle_handoff_canary_smoke_json:missing_evidence_path",
        "native_typed_consumer_stub_endpoint_ptr_canary_json:missing_evidence_path",
        "prelaunch_pointer_source_observer_check_json:missing_evidence_path",
        "readonly_live_trusted_refs_check_json:missing_evidence_path",
    }


def test_premap_lab_preflight_rejects_unbound_useful_consumer_child_chain(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    useful_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_useful_consumer.json"
    )
    useful_payload = json.loads(useful_path.read_text(encoding="utf-8"))
    useful_payload["native_timing_json"] = (
        "reports/default_gate_future_wna16_typed_slot_kernel_variant_useful_consumer.json"
    )
    useful_path.write_text(json.dumps(useful_payload) + "\n", encoding="utf-8")
    useful_payload["native_timing_sha256"] = hashlib.sha256(
        useful_path.read_bytes()
    ).hexdigest()
    useful_path.write_text(json.dumps(useful_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_kernel_variant_useful_consumer_json:"
        "native_timing_json_chain_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_useful_consumer_hash_not_backed_by_stub(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    useful_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_useful_consumer.json"
    )
    useful_payload = json.loads(useful_path.read_text(encoding="utf-8"))
    useful_hashes = useful_payload["useful_consumer_field_read_hashes"]
    assert isinstance(useful_hashes, dict)
    useful_hashes["descriptor_ptr"] = "1111111111111111"
    useful_path.write_text(json.dumps(useful_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_kernel_variant_useful_consumer_json:"
        "native_stub_descriptor_ptr_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_useful_consumer_stub_missing_safety_field(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    stub_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution_native_stub.json"
    )
    stub_payload = json.loads(stub_path.read_text(encoding="utf-8"))
    stub_payload.pop("wna16_side_consumer_variant_execution_payload_bytes")
    stub_path.write_text(json.dumps(stub_payload) + "\n", encoding="utf-8")
    stub_sha = hashlib.sha256(stub_path.read_bytes()).hexdigest()
    timing_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution_native.json"
    )
    timing_payload = json.loads(timing_path.read_text(encoding="utf-8"))
    timing_payload["native_stub_output_sha256"] = stub_sha
    timing_path.write_text(json.dumps(timing_payload) + "\n", encoding="utf-8")
    timing_sha = hashlib.sha256(timing_path.read_bytes()).hexdigest()
    variant_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_execution.json"
    )
    variant_payload = json.loads(variant_path.read_text(encoding="utf-8"))
    variant_payload["future_wna16_variant_execution_native_sha256"] = timing_sha
    variant_path.write_text(json.dumps(variant_payload) + "\n", encoding="utf-8")
    variant_sha = hashlib.sha256(variant_path.read_bytes()).hexdigest()
    useful_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_kernel_variant_useful_consumer.json"
    )
    useful_payload = json.loads(useful_path.read_text(encoding="utf-8"))
    useful_payload["execution_sha256"] = variant_sha
    useful_payload["native_timing_sha256"] = timing_sha
    useful_payload["native_stub_sha256"] = stub_sha
    useful_path.write_text(json.dumps(useful_payload) + "\n", encoding="utf-8")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "future_wna16_typed_slot_kernel_variant_useful_consumer_json:"
        "native_stub_wna16_payload_bytes_mismatch"
    ) in failures


def test_premap_lab_preflight_blocks_wna16_side_variant_when_reusing_current_arg_slot(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    wna16_runner = (
        tmp_path
        / "reports/default_gate_wna16_side_consumer_variant_execution_128strict_runner.json"
    )
    payload = json.loads(wna16_runner.read_text(encoding="utf-8"))
    payload["wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot"] = (
        True
    )
    stub_summary = payload["stub_summary"]
    assert isinstance(stub_summary, dict)
    stub_summary[
        "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot"
    ] = True
    wna16_runner.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert summary["default_kernel_consumer_typed_noop_ready"] is True
    assert summary["default_kernel_consumer_wna16_side_variant_ready"] is False
    assert summary["default_kernel_consumer_wna16_benchmark_ready"] is False
    assert (
        summary["default_kernel_consumer_next_runtime_stage"]
        == "implement_wna16_typed_slot_kernel_variant"
    )


def test_premap_lab_preflight_rejects_all_four_consumer_payload_mutation(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    all_four_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    payload = json.loads(all_four_path.read_text(encoding="utf-8"))
    payload["payload_bytes"] = 8
    all_four_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "default_kernel_consumer_future_wna16_all_four_field_consumer_not_ready"
        in result["failures"]
    )
    assert (
        "future_wna16_typed_slot_all_four_field_consumer_json:payload_bytes_mismatch"
        in required_failures
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_all_four_field_consumer_ready"
        ]
        is False
    )
    assert summary["default_kernel_consumer_wna16_benchmark_ready"] is False


def test_premap_lab_preflight_rejects_payloadless_execution_payload_mutation(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    payload["payload_bytes"] = 8
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:payload_bytes_mismatch"
        in required_failures
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_payloadless_execution_gate_ready"
        ]
        is False
    )
    assert summary["default_kernel_consumer_wna16_benchmark_ready"] is False


def test_premap_lab_preflight_rejects_payloadless_execution_child_sha_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    payload["payloadless_execution_timing_stub_sha256"] = "f" * 64
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "payloadless_execution_timing_stub_sha256_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_execution_sweep_path_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    real_sweep = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep.json"
    )
    alternate_sweep = tmp_path / "reports/default_gate_alternate_entry_args_ptr_sweep.json"
    alternate_sweep.write_bytes(real_sweep.read_bytes())
    payload["entry_args_ptr_sweep_json"] = "reports/default_gate_alternate_entry_args_ptr_sweep.json"
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "entry_args_ptr_sweep_json_required_evidence_path_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_execution_out_of_root_suffix_spoof(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    expected_sweep = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep.json"
    )
    spoof_sweep = (
        tmp_path.parent
        / "spoof_root"
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep.json"
    )
    spoof_sweep.parent.mkdir(parents=True, exist_ok=True)
    spoof_sweep.write_bytes(expected_sweep.read_bytes())
    payload["entry_args_ptr_sweep_json"] = str(spoof_sweep)
    payload["entry_args_ptr_sweep_sha256"] = hashlib.sha256(
        expected_sweep.read_bytes()
    ).hexdigest()
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "entry_args_ptr_sweep_json_required_evidence_path_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_execution_field_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    field_hashes = payload["field_read_hashes"]
    assert isinstance(field_hashes, dict)
    field_hashes["descriptor_ptr"] = "1234567890abcdef"
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "descriptor_ptr_field_hash_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_execution_inherited_fourth_sha_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    payload["all_four_field_consumer_fourth_field_sha256"] = "f" * 64
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "all_four_fourth_field_sha256_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_execution_inherited_kernel_manifest_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    payload[
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"
    ] = "f" * 64
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "kernel_side_selected_input_manifest_sha256_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_payloadless_execution_inherited_kernel_all_four_sha_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    payloadless_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_payloadless_execution.json"
    )
    payload = json.loads(payloadless_path.read_text(encoding="utf-8"))
    payload["future_wna16_kernel_side_typed_consumer_path_all_four_sha256"] = "f" * 64
    payloadless_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_payloadless_execution_json:"
        "kernel_side_all_four_sha256_mismatch"
    ) in required_failures
    assert (
        "default_kernel_consumer_future_wna16_payloadless_execution_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_all_four_consumer_manifest_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    all_four_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    payload = json.loads(all_four_path.read_text(encoding="utf-8"))
    payload["post_native_input_manifest_sha256"] = "5" * 64
    all_four_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_all_four_field_consumer_json:post_native_input_manifest_sha256_mismatch"
        in required_failures
    )
    assert (
        "default_kernel_consumer_future_wna16_all_four_field_consumer_not_ready"
        in result["failures"]
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_all_four_field_consumer_ready"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_all_four_consumer_fourth_sha_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    all_four_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    payload = json.loads(all_four_path.read_text(encoding="utf-8"))
    payload["fourth_field_sha256"] = "6" * 64
    all_four_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    assert result["passed"] is False
    assert (
        "default_kernel_consumer_future_wna16_all_four_field_consumer_not_ready"
        in result["failures"]
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_all_four_field_consumer_ready"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_all_four_consumer_fourth_path_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    all_four_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    real_fourth_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_fourth_field_handoff_canary.json"
    )
    wrong_fourth_path = tmp_path / "reports/default_gate_wrong_fourth_field.json"
    wrong_fourth_path.write_bytes(real_fourth_path.read_bytes())
    payload = json.loads(all_four_path.read_text(encoding="utf-8"))
    payload["fourth_field_json"] = "reports/default_gate_wrong_fourth_field.json"
    all_four_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_all_four_field_consumer_json:fourth_field_json_path_mismatch"
        in required_failures
    )
    assert (
        "default_kernel_consumer_future_wna16_all_four_field_consumer_not_ready"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_all_four_consumer_field_read_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    all_four_path = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    payload = json.loads(all_four_path.read_text(encoding="utf-8"))
    payload[
        "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count"
    ] = 1
    all_four_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    summary = result["lab_gate_status_summary"]
    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_typed_slot_all_four_field_consumer_json:wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count_mismatch"
        in required_failures
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_all_four_field_consumer_fields_read"
        ]
        is False
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_all_four_field_consumer_ready"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_kernel_side_path_payload_mutation(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_wna16_kernel_side_typed_consumer_path.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["payload_bytes"] = 8
    payload["kernel_arg_pass_allowed"] = True
    payload["measures_tpot"] = True
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    summary = result["lab_gate_status_summary"]
    assert result["passed"] is False
    assert (
        "future_wna16_kernel_side_typed_consumer_path_json:payload_bytes_mismatch"
        in required_failures
    )
    assert (
        "future_wna16_kernel_side_typed_consumer_path_json:kernel_arg_pass_allowed_mismatch"
        in required_failures
    )
    assert (
        "future_wna16_kernel_side_typed_consumer_path_json:measures_tpot_mismatch"
        in required_failures
    )
    assert (
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_not_ready"
        in result["failures"]
    )
    assert (
        summary[
            "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
        ]
        is False
    )


def test_premap_lab_preflight_rejects_kernel_side_path_all_four_path_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_wna16_kernel_side_typed_consumer_path.json"
    )
    real_all_four = (
        tmp_path
        / "reports/default_gate_future_wna16_typed_slot_all_four_field_consumer.json"
    )
    wrong_all_four = tmp_path / "reports/default_gate_wrong_all_four.json"
    wrong_all_four.write_bytes(real_all_four.read_bytes())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["all_four_json"] = "reports/default_gate_wrong_all_four.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_kernel_side_typed_consumer_path_json:all_four_json_path_mismatch"
        in required_failures
    )


def test_premap_lab_preflight_rejects_kernel_side_path_all_four_sha_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_wna16_kernel_side_typed_consumer_path.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["all_four_sha256"] = "8" * 64
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_kernel_side_typed_consumer_path_json:all_four_json_sha256_mismatch"
        in required_failures
    )


def test_premap_lab_preflight_rejects_kernel_side_path_manifest_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_wna16_kernel_side_typed_consumer_path.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["selected_input_manifest_sha256"] = "9" * 64
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_wna16_kernel_side_typed_consumer_path_json:selected_input_manifest_sha256_mismatch"
        in required_failures
    )


def test_premap_lab_preflight_rejects_all_field_entry_args_ptr_sweep_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["row_counts"]["aux_metadata_handle"] = 17
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json:"
        "field_row_counts_not_equal"
    ) in required_failures


def test_premap_lab_preflight_rejects_all_field_entry_args_ptr_wrong_device(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["device"] = 0
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json:"
        "device_not_gpu1"
    ) in required_failures


def test_premap_lab_preflight_rejects_all_field_entry_args_ptr_check_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep_check.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["require_child_kernel_entry_args_ptr_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json:"
        "require_child_kernel_entry_args_ptr_abi_mismatch"
    ) in required_failures


def test_premap_lab_preflight_rejects_all_field_entry_args_ptr_check_row_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_all_field_entry_args_ptr_sweep_check.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["row_count"] = 512
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    required_failures = result["default_readonly_gate_required_evidence_check"][
        "failures"
    ]
    assert result["passed"] is False
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json:"
        "sweep_check_row_count_mismatch"
    ) in required_failures
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json:"
        "row_count_not_larger_than_window_size"
    ) in required_failures


def test_premap_lab_preflight_rejects_failed_typed_evidence(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        lab_evidence_passed=False,
        lab_evidence_failures=["typed_gate_failed"],
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert set(result["default_readonly_gate_required_evidence_check"]["failures"]) == {
        "native_typed_consumer_bridge_smoke_json:not_passed",
        "strict_native_stub_online_invocation_canary_128_gate_json:not_passed",
        "strict_live_connected_readonly_128_gate_json:not_passed",
        "strict_native_typed_consumer_bridge_128_gate_json:not_passed",
        "strict_kernel_side_typed_consumer_object_128_gate_json:not_passed",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:not_passed",
        "strict_kernel_side_typed_row_consumer_path_128_gate_json:not_passed",
        "strict_single_field_handle_handoff_canary_128_gate_json:not_passed",
        "aux_metadata_single_field_handle_handoff_canary_smoke_json:not_passed",
        "descriptor_ptr_single_field_handle_handoff_canary_smoke_json:not_passed",
        "packed_weight_single_field_handle_handoff_canary_smoke_json:not_passed",
    }


def test_premap_lab_preflight_rejects_typed_evidence_with_failures(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        lab_evidence_passed=True,
        lab_evidence_failures=["unexpected_failure"],
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert set(result["default_readonly_gate_required_evidence_check"]["failures"]) == {
        "native_typed_consumer_bridge_smoke_json:failures_not_empty",
        "strict_native_stub_online_invocation_canary_128_gate_json:failures_not_empty",
        "strict_live_connected_readonly_128_gate_json:failures_not_empty",
        "strict_native_typed_consumer_bridge_128_gate_json:failures_not_empty",
        "strict_kernel_side_typed_consumer_object_128_gate_json:failures_not_empty",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:failures_not_empty",
        "strict_kernel_side_typed_row_consumer_path_128_gate_json:failures_not_empty",
        "strict_single_field_handle_handoff_canary_128_gate_json:failures_not_empty",
        "aux_metadata_single_field_handle_handoff_canary_smoke_json:failures_not_empty",
        "descriptor_ptr_single_field_handle_handoff_canary_smoke_json:failures_not_empty",
        "packed_weight_single_field_handle_handoff_canary_smoke_json:failures_not_empty",
    }


def test_premap_lab_preflight_rejects_wrong_native_stub_evidence_content(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    native_stub_path = (
        tmp_path
        / "reports/default_gate_native_stub_online_invocation_canary_gate.json"
    )
    payload = {
        "passed": True,
        "failures": [],
        "metrics": _lab_evidence_metrics(),
    }
    prefix = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "native_stub_online_invocation_"
    )
    payload["metrics"][f"{prefix}native_stub_invoked_count"] = 1
    _write(native_stub_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "strict_native_stub_online_invocation_canary_128_gate_json:"
        f"{prefix}native_stub_invoked_count_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_unbound_native_typed_stub_input(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    typed_stub_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_gpu1_canary.json"
    )
    payload = _native_stub_evidence_payload("reports/wrong_native_bridge_input.json")
    _write(typed_stub_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_gpu1_canary_json:"
        "native_typed_consumer_stub_input_json_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_endpoint_ptr_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    endpoint_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_endpoint_ptr_canary.json"
    )
    payload = json.loads(endpoint_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_endpoint_ptr_summary_row_hash_accumulator"
    ] = "wrong-endpoint-ptr-hash"
    _write(endpoint_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_endpoint_ptr_canary_json:"
        "native_typed_consumer_stub_endpoint_ptr_summary_row_hash_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_endpoint_ptr_aux_read_count(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    endpoint_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_endpoint_ptr_canary.json"
    )
    payload = json.loads(endpoint_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_endpoint_ptr_summary_aux_metadata_handle_read_row_ok_count"
    ] = 1
    _write(endpoint_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_endpoint_ptr_canary_json:"
        "native_typed_consumer_stub_"
        "future_kernel_native_consumer_endpoint_ptr_summary_"
        "aux_metadata_handle_read_row_ok_count_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_endpoint_ptr_field_mask(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    endpoint_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary.json"
    )
    payload = json.loads(endpoint_ptr_path.read_text(encoding="utf-8"))
    payload["future_kernel_native_consumer_endpoint_ptr_summary_field_mask"] = 7
    _write(endpoint_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json:"
        "native_typed_consumer_stub_"
        "future_kernel_native_consumer_endpoint_ptr_summary_field_mask_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_endpoint_ptr_input_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    endpoint_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary.json"
    )
    payload = json.loads(endpoint_ptr_path.read_text(encoding="utf-8"))
    payload["input_json"] = "reports/default_gate_native_bridge_input.json"
    _write(endpoint_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_endpoint_ptr_canary_json:"
        "native_typed_consumer_stub_input_json_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_ptr_field_mask(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    payload = json.loads(request_ptr_path.read_text(encoding="utf-8"))
    payload["future_kernel_native_consumer_request_ptr_summary_field_mask"] = 7
    _write(request_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:"
        "native_typed_consumer_stub_request_ptr_summary_field_mask_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_ptr_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    payload = json.loads(request_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_request_ptr_summary_row_hash_accumulator"
    ] = "1111111111111111"
    _write(request_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:"
        "native_typed_consumer_stub_request_ptr_summary_row_hash_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_ptr_field_hash_not_hex(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    payload = json.loads(request_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_request_ptr_summary_field_read_hash_accumulator"
    ] = "not-a-hex-hash"
    _write(request_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:"
        "native_typed_consumer_stub_request_ptr_summary_field_read_hash_missing"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_ptr_row_metadata_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    payload = json.loads(request_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_request_ptr_summary_row_metadata_hash_accumulator"
    ] = "1111111111111111"
    _write(request_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:"
        "native_typed_consumer_stub_request_ptr_summary_row_metadata_hash_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_ptr_pointer_size(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    payload = json.loads(request_ptr_path.read_text(encoding="utf-8"))
    payload["future_kernel_native_consumer_request_ptr_pointer_size"] = 4
    _write(request_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:"
        "native_typed_consumer_stub_request_ptr_pointer_size_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_ptr_kernel_entry_field_mask(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary.json"
    )
    payload = json.loads(request_ptr_path.read_text(encoding="utf-8"))
    payload["future_kernel_native_consumer_kernel_entry_summary_field_mask"] = 7
    _write(request_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_ptr_canary_json:"
        "native_typed_consumer_stub_kernel_entry_summary_field_mask_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_online_request_launch_ptr_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    request_launch_ptr_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary.json"
    )
    payload = json.loads(request_launch_ptr_path.read_text(encoding="utf-8"))
    payload[
        "future_kernel_native_consumer_request_launch_ptr_summary_row_hash_accumulator"
    ] = "1111111111111111"
    _write(request_launch_ptr_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_request_launch_ptr_canary_json:"
        "native_typed_consumer_stub_request_launch_ptr_summary_row_hash_request_launch_mismatch"
    ) in result["default_readonly_gate_required_evidence_check"]["failures"]


def test_premap_lab_preflight_rejects_unbound_online_prelaunch_stub_input(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    typed_stub_path = (
        tmp_path
        / "reports/default_gate_native_typed_consumer_stub_online_prelaunch_input_canary.json"
    )
    payload = _native_stub_evidence_payload("reports/wrong_online_prelaunch_input.json")
    _write(typed_stub_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_canary_json:"
        "native_typed_consumer_stub_input_json_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_online_prelaunch_noop_meta_mutation(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    online_input_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_input.json"
    )
    payload = _native_online_prelaunch_input_payload()
    payload["_meta"]["ready_credit"] = True
    _write(online_input_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_canary_json:"
        "native_typed_consumer_stub_input_ready_credit_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_online_prelaunch_export_summary_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    perf_path = (
        tmp_path
        / "reports/default_gate_native_online_prelaunch_export_performance.json"
    )
    _write(
        perf_path,
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 1,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": "reports/wrong_online_prelaunch_input.json",
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [
                    "reports/wrong_online_prelaunch_input.json"
                ],
            }
        )
        + "\n",
    )
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_canary_json:"
        "native_typed_consumer_stub_export_performance_first_path_mismatch"
    ) in failures
    assert (
        "native_typed_consumer_stub_online_prelaunch_input_canary_json:"
        "native_typed_consumer_stub_export_performance_path_not_listed"
    ) in failures


def test_premap_lab_preflight_rejects_future_native_runner_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    payload["future_kernel_native_consumer_descriptor_ptr_stub_summary"][
        "future_kernel_native_consumer_single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    payload["extra_online_input_check_summaries"][0]["outputs"].pop(
        "native_stub_future_kernel_native_consumer_aux_metadata_mirror"
    )
    payload["future_kernel_native_consumer_launch_stub_summary"][
        "future_kernel_native_launch_consumer_single_field_mirror_field_name"
    ] = "descriptor_ptr"
    payload["future_kernel_native_consumer_dispatch_stub_summary"][
        "future_kernel_native_dispatch_consumer_active_rows"
    ] = 1
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_descriptor_ptr_stub_summary_"
        "future_kernel_native_consumer_single_field_mirror_field_name_mismatch"
    ) in failures
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_extra_input_0001_"
        "native_stub_future_kernel_native_consumer_aux_metadata_mirror_missing"
    ) in failures
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_launch_stub_summary_"
        "future_kernel_native_launch_consumer_single_field_mirror_field_name_mismatch"
    ) in failures
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_consumer_active_rows_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_dispatch_tail_window_for_full_table(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    payload["future_native_dispatch_tail_window_size"] = None
    _write(runner_path, json.dumps(payload) + "\n")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload_32 = json.loads(runner_32_path.read_text())
    payload_32["future_native_dispatch_tail_window_size"] = 4
    _write(runner_32_path, json.dumps(payload_32) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_native_dispatch_tail_window_unexpected"
    ) in failures
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_future_native_dispatch_tail_window_unexpected"
    ) in failures


def test_premap_lab_preflight_rejects_incomplete_online_arg_slot_coverage(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    descriptor_summary = payload[
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary"
    ]
    descriptor_summary[
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
    ] = "scale_metadata_handle"
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert (
        "default_kernel_consumer_arg_slot_online_total_mirror_coverage_incomplete"
        in result["failures"]
    )
    summary = result["lab_gate_status_summary"]
    assert summary["default_kernel_consumer_arg_slot_online_mirror_field_coverage"] == [
        "scale_metadata_handle"
    ]
    assert summary[
        "default_kernel_consumer_arg_slot_online_diagnostic_mirror_field_coverage"
    ] == [
        "aux_metadata_handle",
        "packed_weight_descriptor",
    ]
    assert (
        summary["default_kernel_consumer_arg_slot_online_total_full_field_mirror_coverage"]
        is False
    )


def test_premap_lab_preflight_rejects_dispatch_non_full_window(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_row_offset"] = 1
    dispatch["future_kernel_native_dispatch_consumer_row_limit"] = 1
    dispatch["future_kernel_native_dispatch_consumer_active_rows"] = 0
    dispatch["future_kernel_native_dispatch_consumer_row_count"] = 0
    dispatch["future_kernel_native_dispatch_consumer_row_ok_count"] = 0
    dispatch[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_count"
    ] = 0
    dispatch[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count"
    ] = 0
    _write(runner_path, json.dumps(payload) + "\n")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload_32 = json.loads(runner_32_path.read_text())
    dispatch_32 = payload_32["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch_32["future_kernel_native_dispatch_consumer_row_offset"] = 1
    dispatch_32["future_kernel_native_dispatch_consumer_row_limit"] = 1
    dispatch_32["future_kernel_native_dispatch_consumer_active_rows"] = 0
    dispatch_32["future_kernel_native_dispatch_consumer_row_count"] = 0
    dispatch_32["future_kernel_native_dispatch_consumer_row_ok_count"] = 0
    dispatch_32[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_count"
    ] = 0
    dispatch_32[
        "future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count"
    ] = 0
    _write(runner_32_path, json.dumps(payload_32) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    summary = result["lab_gate_status_summary"]
    assert summary["default_kernel_consumer_dispatch_runner_evidence_present"] is True
    assert summary["default_kernel_consumer_dispatch_runner_evidence_passed"] is False
    assert summary["default_kernel_consumer_dispatch_full_table_checked"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_consumer_full_offset_mismatch"
    ) in failures
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_consumer_full_limit_mismatch"
    ) in failures
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_consumer_full_active_rows_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_runner_embedded_artifact_defer(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_32_path.read_text())
    payload["artifact_check_summary"]["final_deferred_count"] = 1
    _write(runner_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_artifact_check_final_deferred_count_nonzero"
    ) in failures


def test_premap_lab_preflight_rejects_runner_embedded_artifact_nondiverse_rows(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_32_path.read_text())
    artifact = payload["artifact_check_summary"]
    artifact["runner_online_prelaunch_input_row_counts"] = [4] * 32
    artifact["runner_online_prelaunch_input_row_count_min"] = 4
    artifact["runner_online_prelaunch_input_row_count_max"] = 4
    artifact["runner_online_prelaunch_input_row_count_sum"] = 128
    artifact["runner_online_prelaunch_input_row_count_diverse"] = False
    _write(runner_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_artifact_check_online_input_row_count_not_diverse"
    ) in failures
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_artifact_check_online_input_row_count_min_max_invalid"
    ) in failures


def test_premap_lab_preflight_rejects_artifact_check_missing_row_stats(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    artifact_32_path = (
        tmp_path
        / "reports/default_gate_native_online_prelaunch_canary_artifact_check_32.json"
    )
    payload = json.loads(artifact_32_path.read_text())
    payload.pop("runner_online_prelaunch_input_row_count_min")
    _write(artifact_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_online_input_row_count_min_missing"
    ) in failures


def test_premap_lab_preflight_rejects_artifact_check_bad_row_sum(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    artifact_32_path = (
        tmp_path
        / "reports/default_gate_native_online_prelaunch_canary_artifact_check_32.json"
    )
    payload = json.loads(artifact_32_path.read_text())
    payload["runner_online_prelaunch_input_row_count_sum"] = 65
    _write(artifact_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_online_input_row_count_sum_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_runner_missing_final_status(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_32_path.read_text())
    payload.pop("final_preflight_status_summary")
    _write(runner_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    summary = result["lab_gate_status_summary"]
    assert (
        summary["default_kernel_consumer_dispatch_runner_final_preflight_passed"]
        is False
    )
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_final_preflight_status_summary_missing"
    ) in failures


def test_premap_lab_preflight_allows_runner_self_finalization(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_32_path.read_text())
    payload["artifact_check_bootstrap_summary"] = dict(
        payload.pop("artifact_check_summary")
    )
    payload["artifact_check_bootstrap_summary"]["bootstrap_preflight_allowed"] = True
    payload["artifact_check_bootstrap_summary"]["final_deferred_count"] = None
    payload.pop("final_preflight_status_summary")
    _write(runner_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_online_runner_self_finalization=True,
    )

    assert result["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["online_runner_self_finalization_allowed"] is True


def test_premap_lab_preflight_self_finalization_requires_bootstrap_summary(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_32_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_32_path.read_text())
    payload["artifact_check_bootstrap_summary"] = dict(
        payload.pop("artifact_check_summary")
    )
    payload["artifact_check_bootstrap_summary"]["bootstrap_preflight_allowed"] = False
    payload["artifact_check_bootstrap_summary"]["final_deferred_count"] = None
    payload.pop("final_preflight_status_summary")
    _write(runner_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_online_runner_self_finalization=True,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:"
        "runner_artifact_check_bootstrap_summary_not_bootstrap"
    ) in failures


def test_premap_lab_preflight_rejects_artifact_check_defer(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    artifact_32_path = (
        tmp_path
        / "reports/default_gate_native_online_prelaunch_canary_artifact_check_32.json"
    )
    payload = json.loads(artifact_32_path.read_text())
    payload["final_deferred_count"] = 1
    _write(artifact_32_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    summary = result["lab_gate_status_summary"]
    assert (
        summary[
            "default_kernel_consumer_dispatch_runner_artifact_check_final_deferred_count"
        ]
        == 1
    )
    assert (
        summary["default_kernel_consumer_dispatch_runner_artifact_check_passed"]
        is False
    )
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:"
        "artifact_final_deferred_count_nonzero"
    ) in failures


def test_premap_lab_preflight_rejects_tail_window_contract_keys_for_full_table(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    gate_path = tmp_path / default_gate
    text = gate_path.read_text()
    text = text.replace(
        "  future_kernel_native_dispatch_consumer_full_table_required: true\n",
        (
            "  future_kernel_native_dispatch_consumer_full_table_required: true\n"
            "  future_kernel_native_dispatch_consumer_tail_window_required: true\n"
            "  future_kernel_native_dispatch_consumer_tail_window_size: 4\n"
        ),
    )
    _write(gate_path, text)
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_contract_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_consumer_tail_window_required_unexpected"
    ) in failures
    assert (
        "future_kernel_native_dispatch_consumer_tail_window_size_unexpected"
    ) in failures


def test_premap_lab_preflight_rejects_dispatch_program_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_consumer_program_iteration_hash"] = "0"
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_consumer_program_iteration_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_dispatch_program_hash_missing(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch.pop("future_kernel_native_dispatch_consumer_program_iteration_hash")
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_consumer_program_iteration_hash_missing"
    ) in failures


def test_premap_lab_preflight_rejects_missing_dispatch_ptr_packet_summary(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    for key in list(dispatch):
        if key.startswith("future_kernel_native_dispatch_ptr_consumer_"):
            dispatch.pop(key)
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_ptr_consumer_checked_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_runner_dispatch_ptr_chain_invisible(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_packet_chain_depth"] = 1
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_ptr_consumer_packet_chain_depth_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_runner_dispatch_packet_invisible(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible"] = (
        False
    )
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_runner_arg_slot_chain_invisible(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_slot_visible"] = False
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_arg_slot_consumer_slot_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_runner_arg_slot_dispatch_ptr_invisible(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    runner_path = (
        tmp_path / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    payload = json.loads(runner_path.read_text())
    dispatch = payload["future_kernel_native_consumer_dispatch_stub_summary"]
    dispatch["future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible"] = (
        False
    )
    _write(runner_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "native_typed_consumer_online_prelaunch_canary_runner_json:"
        "runner_future_kernel_native_consumer_dispatch_stub_summary_"
        "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_dispatch_ptr_schema_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_dispatch_ptr_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["expected_schema_hash"] = "bad-schema-hash"
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_ptr_standalone_canary_json:"
        "standalone_dispatch_ptr_expected_schema_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_dispatch_ptr_row_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_dispatch_ptr_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["future_kernel_native_dispatch_ptr_consumer_row_ok_count"] = 1
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_ptr_standalone_canary_json:"
        "standalone_dispatch_ptr_future_kernel_native_dispatch_ptr_consumer_"
        "row_ok_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_dispatch_ptr_struct_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_dispatch_ptr_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["future_kernel_native_dispatch_ptr_consumer_packet_struct_size"] = -1
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_ptr_standalone_canary_json:"
        "standalone_dispatch_ptr_packet_struct_size_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_dispatch_ptr_chain_invisible(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_dispatch_ptr_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible"] = False
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_ptr_standalone_canary_json:"
        "standalone_dispatch_ptr_future_kernel_native_dispatch_ptr_consumer_"
        "dispatch_packet_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_dispatch_ptr_unsafe_macro(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_dispatch_ptr_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["compiled_macros"][
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS"
    ] = True
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_dispatch_ptr_standalone_canary_json:"
        "standalone_dispatch_ptr_"
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS_enabled"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_payload_mutation(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["payload_bytes"] = 8
    payload["passed_to_kernel"] = True
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_payload_bytes_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_passed_to_kernel_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_wna16_compat(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["current_wna16_arg_compatible"] = True
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_"
        "current_wna16_arg_compatible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_missing_requested_counts(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload.pop("requested_previous_count")
    payload.pop("requested_current_count")
    payload.pop("requested_transition_topk_count")
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    for field in (
        "requested_previous_count",
        "requested_current_count",
        "requested_transition_topk_count",
    ):
        assert (
            "payload_cache_producer_state_native_canary_json:"
            f"payload_cache_producer_state_native_canary_{field}_invalid"
        ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_missing_current_offset(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload.pop("requested_current_offset")
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_requested_current_offset_invalid"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["state_hash"] = "8a45d2c91fe01237"
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_state_hash_packet_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_layer_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["packet_layer_id"] = 1
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_packet_layer_id_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_layer_id_packet_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_issue_hash_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["issue_candidate_hash"] = "0000000000000001"
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_issue_candidate_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_nonempty_issue_stub():
    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        _payload_cache_producer_state_nonempty_issue_stub_payload(),
        failure_prefix="payload_cache_producer_state_nonempty_issue_stub",
        require_online_export=False,
        require_nonempty_issue=True,
    )

    assert failures == []


def test_premap_lab_preflight_accepts_payload_cache_producer_state_stream_native_canary():
    failures = _validate_payload_cache_producer_state_stream_native_canary_evidence(
        _payload_cache_producer_state_stream_native_canary_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_stream_native_canary():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_native_canary_json",
        _payload_cache_producer_state_stream_native_canary_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_stream_without_vectorized_copy():
    payload = _payload_cache_producer_state_stream_native_canary_payload()
    payload["vectorized_copy_used"] = False

    failures = _validate_payload_cache_producer_state_stream_native_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_stream_native_canary_"
        "vectorized_copy_expected_but_not_used"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_stream_without_graph_replay():
    payload = _payload_cache_producer_state_stream_native_canary_payload()
    payload["native_graph_replay"] = False
    payload["requested_graph_replay"] = False

    failures = _validate_payload_cache_producer_state_stream_native_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_stream_native_canary_"
        "native_graph_replay_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_stream_native_canary_"
        "requested_graph_replay_not_enabled"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_stream_issue_mismatch():
    payload = _payload_cache_producer_state_stream_native_canary_payload()
    payload["issue_candidate_count"] = 1

    failures = _validate_payload_cache_producer_state_stream_native_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_stream_native_canary_"
        "issue_candidate_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_stream_issue_formula_mismatch():
    payload = _payload_cache_producer_state_stream_native_canary_payload()
    payload["issue_candidate_count"] = 8
    payload["expected_issue_candidate_count"] = 8

    failures = _validate_payload_cache_producer_state_stream_native_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_stream_native_canary_"
        "expected_issue_candidate_count_formula_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_stream_native_canary_"
        "issue_candidate_count_formula_mismatch"
    ) in failures


def test_premap_lab_preflight_dispatch_rejects_payload_cache_producer_state_stream_payload_mutation():
    payload = _payload_cache_producer_state_stream_native_canary_payload()
    payload["payload_bytes"] = 4

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_native_canary_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_stream_native_canary_json:"
        "payload_cache_producer_state_stream_native_canary_payload_bytes_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_native_canary():
    failures = _validate_payload_cache_producer_state_inprocess_native_canary_evidence(
        _payload_cache_producer_state_inprocess_native_canary_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_inprocess_native_canary():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_canary_json",
        _payload_cache_producer_state_inprocess_native_canary_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_without_graph_replay():
    payload = _payload_cache_producer_state_inprocess_native_canary_payload()
    payload["native_graph_replay"] = False
    payload["requested_graph_replay"] = False

    failures = _validate_payload_cache_producer_state_inprocess_native_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_canary_"
        "native_graph_replay_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_canary_"
        "requested_graph_replay_not_enabled"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_kernel_arg_pass():
    payload = _payload_cache_producer_state_inprocess_native_canary_payload()
    payload["passed_to_kernel"] = True
    payload["changes_kernel_launch_args"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_canary_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_canary_json:"
        "payload_cache_producer_state_inprocess_native_canary_"
        "passed_to_kernel_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_canary_json:"
        "payload_cache_producer_state_inprocess_native_canary_"
        "changes_kernel_launch_args_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_bool_int_type_confusion():
    payload = _payload_cache_producer_state_inprocess_native_canary_payload()
    payload["payload_bytes"] = False
    payload["passed_to_kernel"] = 0
    payload["vllm_replay_visible"] = 0
    payload["native_graph_replay"] = 1

    failures = _validate_payload_cache_producer_state_inprocess_native_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_canary_payload_bytes_mismatch"
        in failures
    )
    assert (
        "payload_cache_producer_state_inprocess_native_canary_passed_to_kernel_mismatch"
        in failures
    )
    assert (
        "payload_cache_producer_state_inprocess_native_canary_vllm_replay_visible_mismatch"
        in failures
    )
    assert (
        "payload_cache_producer_state_inprocess_native_canary_native_graph_replay_mismatch"
        in failures
    )


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_online_contract():
    failures = _validate_payload_cache_producer_state_inprocess_native_online_contract_evidence(
        _payload_cache_producer_state_inprocess_native_online_contract_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_inprocess_online_contract():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_online_contract_json",
        _payload_cache_producer_state_inprocess_native_online_contract_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_inprocess_online_contract_vllm_replay_visible():
    payload = _payload_cache_producer_state_inprocess_native_online_contract_payload()
    payload["vllm_replay_visible"] = True
    payload["native"]["vllm_replay_visible"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "vllm_replay_visible_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_online_contract_native_"
        "vllm_replay_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_inprocess_online_contract_kernel_arg_pass():
    payload = _payload_cache_producer_state_inprocess_native_online_contract_payload()
    payload["passed_to_kernel"] = True
    payload["changes_kernel_launch_args"] = True
    payload["native"]["passed_to_kernel"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "passed_to_kernel_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "changes_kernel_launch_args_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_online_contract_native_"
        "passed_to_kernel_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_inprocess_online_contract_issue_mismatch():
    payload = _payload_cache_producer_state_inprocess_native_online_contract_payload()
    payload["online_observed_issue_candidate_count"] = 1
    payload["native_inprocess_issue_candidate_count"] = 2

    failures = _validate_payload_cache_producer_state_inprocess_native_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "online_observed_issue_candidate_count_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "native_inprocess_issue_candidate_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_inprocess_online_contract_unpassed_source():
    payload = _payload_cache_producer_state_inprocess_native_online_contract_payload()
    payload["source_stream_online_contract_passed"] = False
    payload["source_stream_online_contract_failures"] = ["source_failed"]

    failures = _validate_payload_cache_producer_state_inprocess_native_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "source_stream_online_contract_passed_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "source_stream_online_contract_failures_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_inprocess_online_contract_raw_summary_source_kind():
    payload = _payload_cache_producer_state_inprocess_native_online_contract_payload()
    payload["source_kind"] = "raw_vllm_performance_summary"
    payload["source_is_online_stream_contract"] = False
    payload["source_is_raw_vllm_performance_summary"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "source_kind_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "source_is_online_stream_contract_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_online_contract_"
        "source_is_raw_vllm_performance_summary_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_session_canary():
    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        _payload_cache_producer_state_inprocess_native_session_canary_payload()
    )

    assert failures == []


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_session_packet_stream_restore():
    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_packet_stream_restore_count_mismatch():
    payload = _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    payload["packet_stream_state_restore_count"] = 30

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "packet_stream_state_restore_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_packet_stream_restore_returncode():
    payload = _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    payload["packet_stream_state_restore_returncodes"] = [0, 262]

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "packet_stream_state_restore_returncodes_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_packet_source_without_input_flag():
    payload = _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    payload["packet_stream_input"] = False

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "packet_stream_input_required"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_packet_issue_count_mismatch():
    payload = _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    payload["issue_candidate_count"] = 1

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "issue_candidate_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_packet_issue_hash_mismatch():
    payload = _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    payload["expected_issue_candidate_hash"] = "ffffffffffffffff"

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "issue_candidate_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_torch_smoke_claiming_vllm_prelaunch():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["current_expert_ptr_source"] = "torch_device_tensor"
    payload["current_expert_ptr_source_kind"] = "external_torch_device_tensor_smoke"
    payload["external_current_expert_ptr_source"] = True
    payload["ready_for_external_pointer_smoke"] = True
    payload["ready_for_vllm_prelaunch_canary"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "ready_for_vllm_prelaunch_canary_mismatch"
    ) in failures


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_inprocess_session_canary():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_canary_json",
        _payload_cache_producer_state_inprocess_native_session_canary_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_graph_visible():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["graph_visible"] = True
    payload["torch_graph_replay_visible"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "graph_visible_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "torch_graph_replay_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_session_native_generated_current():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["current_expert_ptr_source"] = "native_generated_device_scratch"
    payload["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    payload["current_count_source_kind"] = "native_generated_internal_scalar"
    payload["current_count_device_ptr_passed"] = False
    payload["current_count_host_scalar_passed"] = False
    payload["external_current_expert_ptr_source"] = False
    payload["ready_for_external_pointer_smoke"] = False
    payload["ready_for_vllm_prelaunch_canary"] = False

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert failures == []


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_session_device_count():
    payload = _payload_cache_producer_state_inprocess_native_session_packet_stream_payload()
    payload["current_count_source_kind"] = "device_tensor_int32_bits_as_uint32"
    payload["current_count_device_ptr_passed"] = True
    payload["current_count_host_scalar_passed"] = False
    payload["requested_device_current_count"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_native_count_mislabel():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["current_expert_ptr_source"] = "packet_stream_torch_device_tensor"
    payload["current_expert_ptr_source_kind"] = "online_packet_stream_device_tensor_smoke"
    payload["packet_stream_input"] = True
    payload["external_current_expert_ptr_source"] = False
    payload["ready_for_external_pointer_smoke"] = False
    payload["current_count_source_kind"] = "native_generated_internal_scalar"
    payload["current_count_device_ptr_passed"] = False
    payload["current_count_host_scalar_passed"] = False

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "current_count_native_source_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_host_count_requested_device():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["requested_device_current_count"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "requested_device_current_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_native_count_requested_device():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["current_expert_ptr_source"] = "native_generated_device_scratch"
    payload["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    payload["current_count_source_kind"] = "native_generated_internal_scalar"
    payload["current_count_device_ptr_passed"] = False
    payload["current_count_host_scalar_passed"] = False
    payload["requested_device_current_count"] = True
    payload["external_current_expert_ptr_source"] = False
    payload["ready_for_external_pointer_smoke"] = False
    payload["ready_for_vllm_prelaunch_canary"] = False

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "requested_device_current_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_native_generated_claims_vllm_pointer():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["current_expert_ptr_source"] = "native_generated_device_scratch"
    payload["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    payload["current_count_source_kind"] = "native_generated_internal_scalar"
    payload["current_count_device_ptr_passed"] = False
    payload["current_count_host_scalar_passed"] = False
    payload["external_current_expert_ptr_source"] = True
    payload["ready_for_external_pointer_smoke"] = True
    payload["ready_for_vllm_prelaunch_canary"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "external_current_expert_ptr_source_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "ready_for_vllm_prelaunch_canary_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_kernel_arg_pass():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["passed_to_kernel"] = True
    payload["changes_kernel_launch_args"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_canary_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_json:"
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "passed_to_kernel_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_json:"
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "changes_kernel_launch_args_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_issue_count_mismatch():
    payload = _payload_cache_producer_state_inprocess_native_session_canary_payload()
    payload["issue_candidate_count"] = 1

    failures = _validate_payload_cache_producer_state_inprocess_native_session_canary_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_canary_"
        "issue_count_formula_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_session_online_contract():
    failures = _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence(
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_torch_smoke_claiming_vllm_prelaunch():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["current_expert_ptr_source"] = "torch_device_tensor"
    payload["current_expert_ptr_source_kind"] = "external_torch_device_tensor_smoke"
    payload["external_current_expert_ptr_source"] = True
    payload["ready_for_external_pointer_smoke"] = True
    payload["ready_for_vllm_prelaunch_canary"] = True
    native = payload["native"]
    assert isinstance(native, dict)
    native["current_expert_ptr_source"] = "torch_device_tensor"
    native["current_expert_ptr_source_kind"] = "external_torch_device_tensor_smoke"
    native["external_current_expert_ptr_source"] = True
    native["ready_for_external_pointer_smoke"] = True
    native["ready_for_vllm_prelaunch_canary"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "ready_for_vllm_prelaunch_canary_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "native_ready_for_vllm_prelaunch_canary_mismatch"
    ) in failures


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_inprocess_session_online_contract():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_online_contract_json",
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_kernel_arg_pass():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["kernel_arg_pass"] = True
    payload["kernel_arg_pass_allowed"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "kernel_arg_pass_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "kernel_arg_pass_allowed_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_missing_kernel_arg_pass_allowed():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload.pop("kernel_arg_pass_allowed")

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "kernel_arg_pass_allowed_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_raw_summary_source():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["source_kind"] = "raw_vllm_performance_summary"
    payload["source_is_online_stream_contract"] = False
    payload["source_is_raw_vllm_performance_summary"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "source_kind_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "source_is_online_stream_contract_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "source_is_raw_vllm_performance_summary_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_unpassed_source():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["source_stream_online_contract_passed"] = False
    payload["source_stream_online_contract_failures"] = ["source_failed"]

    failures = _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "source_stream_online_contract_passed_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "source_stream_online_contract_failures_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_inprocess_session_online_contract_native_generated_current():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["current_expert_ptr_source"] = "native_generated_device_scratch"
    payload["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    payload["external_current_expert_ptr_source"] = False
    payload["ready_for_external_pointer_smoke"] = False
    payload["ready_for_vllm_prelaunch_canary"] = False
    native = payload["native"]
    assert isinstance(native, dict)
    native["current_expert_ptr_source"] = "native_generated_device_scratch"
    native["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    native["external_current_expert_ptr_source"] = False
    native["ready_for_external_pointer_smoke"] = False
    native["ready_for_vllm_prelaunch_canary"] = False

    failures = _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence(
        payload
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_native_generated_claims_vllm_pointer():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["current_expert_ptr_source"] = "native_generated_device_scratch"
    payload["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    payload["external_current_expert_ptr_source"] = True
    payload["ready_for_external_pointer_smoke"] = True
    payload["ready_for_vllm_prelaunch_canary"] = True
    native = payload["native"]
    assert isinstance(native, dict)
    native["current_expert_ptr_source"] = "native_generated_device_scratch"
    native["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    native["external_current_expert_ptr_source"] = True
    native["ready_for_external_pointer_smoke"] = True
    native["ready_for_vllm_prelaunch_canary"] = True

    failures = _validate_payload_cache_producer_state_inprocess_native_session_online_contract_evidence(
        payload
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "external_current_expert_ptr_source_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "ready_for_vllm_prelaunch_canary_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "native_external_current_expert_ptr_source_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_issue_count_mismatch():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["native_session_issue_candidate_count"] = 1

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "native_session_issue_candidate_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_inprocess_session_online_contract_native_dimension_mismatch_under_topk_cap():
    payload = (
        _payload_cache_producer_state_inprocess_native_session_online_contract_payload()
    )
    payload["contract_experts_per_layer"] = 225
    native = payload["native"]
    assert isinstance(native, dict)
    native["experts_per_layer"] = 8
    native["requested_experts_per_layer"] = 8
    # With topk=8, both 8 and 225 experts/layer produce the same issue count.
    # The gate must still reject the native session because it did not run the
    # same envelope as the online contract.
    assert payload["contract_expected_issue_candidate_count"] == (
        payload["native_session_issue_candidate_count"]
    )

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_inprocess_native_session_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_inprocess_native_session_online_contract_json:"
        "payload_cache_producer_state_inprocess_native_session_online_contract_"
        "native_experts_per_layer_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_packet_stream_native_canary():
    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_evidence(
            _payload_cache_producer_state_packet_stream_native_canary_payload()
        )
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_packet_stream_native_canary():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_packet_stream_native_canary_json",
        _payload_cache_producer_state_packet_stream_native_canary_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_runtime_blocked():
    payload = _payload_cache_producer_state_packet_stream_native_canary_payload()
    payload["native_runtime_blocked"] = True
    payload["passed"] = False
    payload["failures"] = ["native_runtime_blocked"]

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_native_runtime_blocked"
        in failures
    )


def test_premap_lab_preflight_dispatch_rejects_payload_cache_producer_state_packet_stream_native_canary_runtime_blocked():
    payload = _payload_cache_producer_state_packet_stream_native_canary_payload()
    payload["native_runtime_blocked"] = True
    payload["passed"] = False
    payload["failures"] = ["native_runtime_blocked"]

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_packet_stream_native_canary_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_json:"
        "payload_cache_producer_state_packet_stream_native_canary_native_runtime_blocked"
        in failures
    )


def test_premap_lab_preflight_accepts_payload_cache_producer_state_packet_stream_native_canary_check():
    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            _payload_cache_producer_state_packet_stream_native_canary_check_payload()
        )
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_packet_stream_native_canary_check():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_packet_stream_native_canary_check_json",
        _payload_cache_producer_state_packet_stream_native_canary_check_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_check_count_mismatch():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    payload["issue_candidate_count"] = 223

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "issue_candidate_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_check_hash_mismatch():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    payload["issue_candidate_hash"] = "0000000000000001"

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "issue_candidate_hash_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "materialized_issue_candidate_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_check_wrong_hash_kind():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    sha_like = "f" * 64
    payload["issue_candidate_hash"] = sha_like
    payload["expected_issue_candidate_hash"] = sha_like
    payload["materialized_expected_issue_candidate_hash"] = sha_like

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "issue_candidate_hash_invalid"
    ) in failures
    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "expected_issue_candidate_hash_invalid"
    ) in failures
    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "materialized_expected_issue_candidate_hash_invalid"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_check_bool_payload_bytes():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    payload["payload_bytes"] = False

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "payload_bytes_type_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_check_bool_zero_counts():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    payload["state_mismatch_count"] = False
    payload["issue_expert_mismatch_count"] = False

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "state_mismatch_count_type_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "issue_expert_mismatch_count_type_mismatch"
    ) in failures


def test_premap_lab_preflight_dispatch_rejects_payload_cache_producer_state_packet_stream_native_canary_check_count_mismatch():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    payload["issue_candidate_count"] = 223

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_packet_stream_native_canary_check_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_json:"
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "issue_candidate_count_mismatch"
        in failures
    )


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_stream_native_canary_check_previous_nonempty_mismatch():
    payload = _payload_cache_producer_state_packet_stream_native_canary_check_payload()
    payload["previous_nonempty_packet_count"] = 27

    failures = (
        _validate_payload_cache_producer_state_packet_stream_native_canary_check_evidence(
            payload
        )
    )

    assert (
        "payload_cache_producer_state_packet_stream_native_canary_check_"
        "materialized_previous_nonempty_packet_count_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_stream_online_contract():
    failures = _validate_payload_cache_producer_state_stream_online_contract_evidence(
        _payload_cache_producer_state_stream_online_contract_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_producer_state_stream_online_contract():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_online_contract_json",
        _payload_cache_producer_state_stream_online_contract_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_accepts_payload_cache_online_inside_graph_boundary_contract():
    failures = _validate_payload_cache_online_inside_graph_producer_boundary_contract_evidence(
        _payload_cache_online_inside_graph_producer_boundary_contract_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_online_inside_graph_boundary_contract():
    failures = _validate_required_evidence_payload(
        "payload_cache_online_inside_graph_producer_boundary_contract_json",
        _payload_cache_online_inside_graph_producer_boundary_contract_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_accepts_payload_cache_online_inside_graph_boundary_contract_with_empty_issue_candidates():
    payload = _payload_cache_online_inside_graph_producer_boundary_contract_payload()
    payload["graph_observed_previous_nonempty_packet_count"] = 0
    payload["graph_expected_previous_nonempty_packet_count"] = 0
    payload["graph_observed_issue_candidate_count"] = 0
    payload["graph_expected_issue_candidate_count"] = 0
    payload["graph_last_issue_candidate_count"] = 0
    payload["graph_last_issue_candidate_first_expert"] = -1
    payload["graph_last_issue_candidate_last_expert"] = -1
    payload["graph_issue_candidate_expert_sum"] = 0

    failures = _validate_required_evidence_payload(
        "payload_cache_online_inside_graph_producer_boundary_contract_json",
        payload,
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_online_inside_graph_boundary_contract_without_skip():
    payload = _payload_cache_online_inside_graph_producer_boundary_contract_payload()
    payload["python_transition_skipped"] = False

    failures = _validate_required_evidence_payload(
        "payload_cache_online_inside_graph_producer_boundary_contract_json",
        payload,
    )

    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "python_transition_skipped_mismatch"
    ) in failures
    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "python_transition_not_skipped"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_inside_graph_boundary_contract_capture_only():
    payload = _payload_cache_online_inside_graph_producer_boundary_contract_payload()
    payload["embedded_graph_visible_contract_capture_once_per_layer_suspected"] = True
    payload["embedded_graph_visible_contract_replay_update_status"] = (
        "capture_once_per_layer_no_replay_updates"
    )

    failures = _validate_required_evidence_payload(
        "payload_cache_online_inside_graph_producer_boundary_contract_json",
        payload,
    )

    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "embedded_graph_visible_contract_capture_once_per_layer_suspected_mismatch"
    ) in failures
    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "capture_once_per_layer_suspected"
    ) in failures
    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "replay_updates_not_complete"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_inside_graph_boundary_contract_wna16_arg_pass():
    payload = _payload_cache_online_inside_graph_producer_boundary_contract_payload()
    payload["passes_current_wna16_args"] = True
    payload["passed_to_kernel"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_online_inside_graph_producer_boundary_contract_json",
        payload,
    )

    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "passes_current_wna16_args_mismatch"
    ) in failures
    assert (
        "payload_cache_online_inside_graph_producer_boundary_contract_json:"
        "payload_cache_online_inside_graph_producer_boundary_contract_"
        "passed_to_kernel_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_contract_issue_mismatch():
    payload = _payload_cache_producer_state_stream_online_contract_payload()
    payload["native_stream_issue_candidate_count"] = 1

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_issue_candidate_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_contract_native_stream_wna16_or_tpot():
    payload = _payload_cache_producer_state_stream_online_contract_payload()
    payload["native_stream_is_current_wna16_fused_moe"] = True
    payload["native_stream_measures_tpot"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_stream_is_current_wna16_fused_moe_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_stream_measures_tpot_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_contract_kernel_arg_pass():
    payload = _payload_cache_producer_state_stream_online_contract_payload()
    payload["kernel_arg_pass"] = True
    payload["kernel_arg_pass_allowed"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "kernel_arg_pass_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "kernel_arg_pass_allowed_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_contract_missing_native_stream_flags():
    payload = _payload_cache_producer_state_stream_online_contract_payload()
    payload.pop("native_stream_is_current_wna16_fused_moe")
    payload.pop("native_stream_measures_tpot")

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_stream_is_current_wna16_fused_moe_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_stream_measures_tpot_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_online_contract_without_graph_replay():
    payload = _payload_cache_producer_state_stream_online_contract_payload()
    payload["native_stream_graph_replay"] = False
    payload["native_stream_requested_graph_replay"] = False

    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_stream_online_contract_json",
        payload,
    )

    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_stream_graph_replay_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_stream_online_contract_json:"
        "payload_cache_producer_state_stream_online_contract_"
        "native_stream_requested_graph_replay_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_stream_producer_ab_bridge():
    failures = _validate_payload_cache_stream_producer_production_ab_bridge_evidence(
        _payload_cache_stream_producer_production_ab_bridge_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_stream_producer_ab_bridge():
    failures = _validate_required_evidence_payload(
        "payload_cache_stream_producer_production_ab_bridge_json",
        _payload_cache_stream_producer_production_ab_bridge_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_stream_producer_ab_payload():
    payload = _payload_cache_stream_producer_production_ab_bridge_payload()
    payload["candidate_payload_bytes"] = 1

    failures = _validate_required_evidence_payload(
        "payload_cache_stream_producer_production_ab_bridge_json",
        payload,
    )

    assert (
        "payload_cache_stream_producer_production_ab_bridge_json:"
        "payload_cache_stream_producer_production_ab_bridge_"
        "candidate_payload_bytes_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_stream_producer_ab_without_graph_replay():
    payload = _payload_cache_stream_producer_production_ab_bridge_payload()
    payload["native_stream_graph_replay"] = False
    payload["native_stream_requested_graph_replay"] = False

    failures = _validate_required_evidence_payload(
        "payload_cache_stream_producer_production_ab_bridge_json",
        payload,
    )

    assert (
        "payload_cache_stream_producer_production_ab_bridge_json:"
        "payload_cache_stream_producer_production_ab_bridge_"
        "native_stream_graph_replay_mismatch"
    ) in failures
    assert (
        "payload_cache_stream_producer_production_ab_bridge_json:"
        "payload_cache_stream_producer_production_ab_bridge_"
        "native_stream_requested_graph_replay_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_stream_producer_ab_bridge_check():
    failures = (
        _validate_payload_cache_stream_producer_production_ab_bridge_check_evidence(
            _payload_cache_stream_producer_production_ab_bridge_check_payload()
        )
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_stream_producer_ab_bridge_check():
    failures = _validate_required_evidence_payload(
        "payload_cache_stream_producer_production_ab_bridge_check_json",
        _payload_cache_stream_producer_production_ab_bridge_check_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_stream_producer_ab_bridge_check_without_graph_replay():
    payload = _payload_cache_stream_producer_production_ab_bridge_check_payload()
    payload["native_stream_graph_replay"] = False
    payload["native_stream_requested_graph_replay"] = False

    failures = _validate_required_evidence_payload(
        "payload_cache_stream_producer_production_ab_bridge_check_json",
        payload,
    )

    assert (
        "payload_cache_stream_producer_production_ab_bridge_check_json:"
        "payload_cache_stream_producer_production_ab_bridge_check_"
        "native_stream_graph_replay_mismatch"
    ) in failures
    assert (
        "payload_cache_stream_producer_production_ab_bridge_check_json:"
        "payload_cache_stream_producer_production_ab_bridge_check_"
        "native_stream_requested_graph_replay_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_online_nonempty_issue_canary():
    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        _payload_cache_producer_state_native_canary_payload(),
        failure_prefix="payload_cache_producer_state_online_nonempty_issue_canary",
        require_online_export=True,
        require_nonempty_issue=True,
        require_summary_first_nonempty_issue=True,
    )

    assert failures == []


def test_premap_lab_preflight_rejects_online_nonempty_issue_without_summary_first_mode():
    payload = _payload_cache_producer_state_native_canary_payload()
    payload["selected_packet_selection_mode"] = "first_nonempty_issue"

    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        payload,
        failure_prefix="payload_cache_producer_state_online_nonempty_issue_canary",
        require_online_export=True,
        require_nonempty_issue=True,
        require_summary_first_nonempty_issue=True,
    )

    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "selected_packet_selection_mode_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_online_nonempty_issue_scan_errors():
    payload = _payload_cache_producer_state_native_canary_payload()
    payload["online_packet_export_scan_error_count"] = 1

    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        payload,
        failure_prefix="payload_cache_producer_state_online_nonempty_issue_canary",
        require_online_export=True,
        require_nonempty_issue=True,
        require_summary_first_nonempty_issue=True,
    )

    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "online_packet_export_scan_error_count_nonzero"
    ) in failures


def test_premap_lab_preflight_rejects_online_nonempty_issue_summary_hash_mismatch():
    payload = _payload_cache_producer_state_native_canary_payload()
    payload["online_packet_export_first_nonempty_issue_hash"] = "0000000000000000"

    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        payload,
        failure_prefix="payload_cache_producer_state_online_nonempty_issue_canary",
        require_online_export=True,
        require_nonempty_issue=True,
        require_summary_first_nonempty_issue=True,
    )

    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "online_packet_export_first_nonempty_issue_hash_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_issue_bounds_mismatch():
    payload = _payload_cache_producer_state_native_canary_payload()
    payload["issue_candidate_last_expert"] = 7

    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        payload,
        failure_prefix="payload_cache_producer_state_online_nonempty_issue_canary",
        require_online_export=True,
        require_nonempty_issue=True,
        require_summary_first_nonempty_issue=True,
    )

    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "issue_candidate_last_expert_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_empty_issue_bounds():
    payload = _payload_cache_producer_state_nonempty_issue_stub_payload()
    payload.update(
        {
            "previous_count": 0,
            "previous_valid_count": 0,
            "previous_nonempty": 0,
            "overlap_count": 0,
            "issue_candidate_count": 0,
            "issue_candidate_first_expert": -1,
            "issue_candidate_last_expert": -1,
            "expected_issue_candidate_count": 0,
            "expected_issue_candidate_first_expert": -1,
            "expected_issue_candidate_last_expert": -1,
            "issue_candidate_hash": "af63bd4c8601b7df",
            "expected_issue_candidate_hash": "af63bd4c8601b7df",
            "requested_previous_count": 0,
        }
    )

    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        payload,
        failure_prefix="payload_cache_producer_state_native_canary",
        require_online_export=False,
        require_nonempty_issue=False,
    )

    assert failures == []


def test_premap_lab_preflight_rejects_payload_cache_producer_state_online_nonempty_without_export():
    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        _payload_cache_producer_state_nonempty_issue_stub_payload(),
        failure_prefix="payload_cache_producer_state_online_nonempty_issue_canary",
        require_online_export=True,
        require_nonempty_issue=True,
        require_summary_first_nonempty_issue=True,
    )

    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "online_export_source_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "online_packet_export_paths_missing"
    ) in failures


def test_premap_lab_preflight_dispatch_rejects_payload_cache_producer_state_online_nonempty_without_export():
    failures = _validate_required_evidence_payload(
        "payload_cache_producer_state_online_nonempty_issue_canary_json",
        _payload_cache_producer_state_nonempty_issue_stub_payload(),
    )

    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_json:"
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "online_export_source_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_online_nonempty_issue_canary_json:"
        "payload_cache_producer_state_online_nonempty_issue_canary_"
        "online_packet_export_paths_missing"
    ) in failures


def test_premap_lab_preflight_accepts_shifted_issue_runtime_shadow_gate():
    failures = _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence(
        _payload_cache_shifted_issue_runtime_shadow_gate_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_rejects_shifted_issue_runtime_shadow_kernel_pass():
    payload = _payload_cache_shifted_issue_runtime_shadow_gate_payload()
    payload["passed_to_kernel"] = True
    payload["changes_kernel_launch_args"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_shifted_issue_runtime_shadow_gate_json",
        payload,
    )

    assert (
        "payload_cache_shifted_issue_runtime_shadow_gate_json:"
        "payload_cache_shifted_issue_runtime_shadow_gate_passed_to_kernel_mismatch"
    ) in failures
    assert (
        "payload_cache_shifted_issue_runtime_shadow_gate_json:"
        "payload_cache_shifted_issue_runtime_shadow_gate_changes_kernel_launch_args_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_shifted_issue_runtime_shadow_bool_payload_bytes():
    payload = _payload_cache_shifted_issue_runtime_shadow_gate_payload()
    payload["payload_bytes"] = False

    failures = _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence(
        payload
    )

    assert (
        "payload_cache_shifted_issue_runtime_shadow_gate_payload_bytes_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_shifted_issue_runtime_shadow_int_false_flag():
    payload = _payload_cache_shifted_issue_runtime_shadow_gate_payload()
    payload["ready_credit"] = 0

    failures = _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence(
        payload
    )

    assert (
        "payload_cache_shifted_issue_runtime_shadow_gate_ready_credit_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_shifted_issue_runtime_shadow_int_passed():
    payload = _payload_cache_shifted_issue_runtime_shadow_gate_payload()
    payload["passed"] = 1

    failures = _validate_payload_cache_shifted_issue_runtime_shadow_gate_evidence(
        payload
    )

    assert (
        "payload_cache_shifted_issue_runtime_shadow_gate_passed_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_packet_export_manifest():
    failures = _validate_payload_cache_packet_export_manifest_evidence(
        _payload_cache_packet_export_manifest_payload()
    )

    assert failures == []


def test_premap_lab_preflight_dispatch_accepts_payload_cache_packet_export_manifest():
    failures = _validate_required_evidence_payload(
        "payload_cache_packet_export_manifest_json",
        _payload_cache_packet_export_manifest_payload(),
    )

    assert failures == []


def test_premap_lab_preflight_rejects_packet_export_manifest_kernel_pass():
    payload = _payload_cache_packet_export_manifest_payload()
    payload["passed_to_kernel"] = True
    payload["changes_kernel_launch_args"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_packet_export_manifest_json",
        payload,
    )

    assert (
        "payload_cache_packet_export_manifest_json:"
        "payload_cache_packet_export_manifest_passed_to_kernel_mismatch"
    ) in failures
    assert (
        "payload_cache_packet_export_manifest_json:"
        "payload_cache_packet_export_manifest_changes_kernel_launch_args_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_packet_export_manifest_checked_count_mismatch():
    payload = _payload_cache_packet_export_manifest_payload()
    payload["checked_nonempty_packet_count"] = 27

    failures = _validate_payload_cache_packet_export_manifest_evidence(payload)

    assert (
        "payload_cache_packet_export_manifest_checked_nonempty_packet_count_too_small"
        in failures
    )
    assert (
        "payload_cache_packet_export_manifest_online_nonempty_count_mismatch"
        in failures
    )


def test_premap_lab_preflight_rejects_packet_export_manifest_first_nonempty_mismatch():
    payload = _payload_cache_packet_export_manifest_payload()
    payload["summary_packet_export_first_nonempty_issue_hash"] = "0000000000000000"

    failures = _validate_payload_cache_packet_export_manifest_evidence(payload)

    assert "payload_cache_packet_export_manifest_first_nonempty_hash_mismatch" in failures


def test_premap_lab_preflight_rejects_packet_export_manifest_path_outside_root(
    tmp_path: Path,
):
    external_packet = tmp_path.parent / f"{tmp_path.name}_outside_packet.json"
    external_packet.write_text("{}\n", encoding="utf-8")
    payload = _payload_cache_packet_export_manifest_payload()
    external_path = str(external_packet)
    payload["online_packet_export_paths"] = [external_path for _ in range(32)]
    for prefix in (
        "summary_packet_export_first_nonempty_issue_",
        "checked_packet_export_first_nonempty_issue_",
        "online_packet_export_first_nonempty_issue_",
    ):
        payload[f"{prefix}path"] = external_path

    failures = _validate_payload_cache_packet_export_manifest_evidence(
        payload,
        root=tmp_path,
    )

    assert "payload_cache_packet_export_manifest_online_packet_export_path_0_outside_root" in failures


def test_premap_lab_preflight_rejects_packet_export_manifest_negative_first_index():
    payload = _payload_cache_packet_export_manifest_payload()
    for prefix in (
        "summary_packet_export_first_nonempty_issue_",
        "checked_packet_export_first_nonempty_issue_",
        "online_packet_export_first_nonempty_issue_",
    ):
        payload[f"{prefix}index"] = -1

    failures = _validate_payload_cache_packet_export_manifest_evidence(payload)

    assert (
        "payload_cache_packet_export_manifest_checked_first_nonempty_index_invalid"
        in failures
    )


def test_premap_lab_preflight_rejects_packet_export_manifest_zero_first_count():
    payload = _payload_cache_packet_export_manifest_payload()
    for prefix in (
        "summary_packet_export_first_nonempty_issue_",
        "checked_packet_export_first_nonempty_issue_",
        "online_packet_export_first_nonempty_issue_",
    ):
        payload[f"{prefix}count"] = 0

    failures = _validate_payload_cache_packet_export_manifest_evidence(payload)

    assert (
        "payload_cache_packet_export_manifest_checked_first_nonempty_count_invalid"
        in failures
    )


def test_premap_lab_preflight_rejects_payload_cache_producer_state_empty_issue_stub():
    payload = _payload_cache_producer_state_nonempty_issue_stub_payload()
    payload["previous_count"] = 0
    payload["previous_valid_count"] = 0
    payload["previous_nonempty"] = 0
    payload["issue_candidate_count"] = 0

    failures = _validate_payload_cache_producer_state_native_canary_evidence(
        payload,
        failure_prefix="payload_cache_producer_state_nonempty_issue_stub",
        require_online_export=False,
        require_nonempty_issue=True,
    )

    assert (
        "payload_cache_producer_state_nonempty_issue_stub_previous_count_empty"
        in failures
    )
    assert (
        "payload_cache_producer_state_nonempty_issue_stub_issue_candidate_count_empty"
        in failures
    )


def test_premap_lab_preflight_rejects_payload_cache_producer_state_disabled_online_export(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["online_configured_export_enabled"] = False
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_"
        "online_configured_export_enabled_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_online_source_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["online_export_source"] = "manual_packet_json"
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_online_export_source_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_empty_online_export(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["online_packet_export_count"] = 0
    payload["online_configured_export_count"] = 0
    payload["online_packet_export_paths"] = []
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_online_packet_export_count_empty"
    ) in failures
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_online_configured_export_count_empty"
    ) in failures
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_online_packet_export_paths_missing"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_export_path_count_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["online_packet_export_count"] = 2
    payload["online_configured_export_count"] = 2
    payload["online_packet_export_paths"] = [
        "reports/premap_payload_cache_producer_state_packet.json",
    ]
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_"
        "online_packet_export_paths_count_mismatch"
    ) in failures
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_"
        "online_configured_export_paths_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_packet_not_exported(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["packet_json"] = "reports/manual_packet.json"
    payload["selected_packet_json"] = "reports/manual_packet.json"
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_packet_json_not_in_online_paths"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_selected_packet_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["selected_packet_json"] = "reports/other_packet.json"
    payload["online_packet_export_paths"] = [
        "reports/premap_payload_cache_producer_state_packet.json",
        "reports/other_packet.json",
    ]
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_selected_packet_json_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_selected_packet_oob(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["online_packet_export_count"] = 1
    payload["selected_packet_index"] = 1
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_selected_packet_index_out_of_range"
    ) in failures


def test_premap_lab_preflight_rejects_payload_cache_producer_state_selected_index_path_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["online_packet_export_count"] = 2
    payload["online_configured_export_count"] = 2
    payload["online_packet_export_paths"] = [
        "reports/other_packet.json",
        "reports/premap_payload_cache_producer_state_packet.json",
    ]
    payload["selected_packet_index"] = 0
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "payload_cache_producer_state_native_canary_json:"
        "payload_cache_producer_state_native_canary_"
        "selected_packet_index_path_mismatch"
    ) in failures


def test_premap_lab_preflight_accepts_payload_cache_producer_state_uncapped_topk(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    producer_state_path = (
        tmp_path / "reports/default_gate_payload_cache_producer_state_native_canary.json"
    )
    payload = json.loads(producer_state_path.read_text())
    payload["transition_topk_count"] = 0
    payload["requested_transition_topk_count"] = 0
    payload["issue_candidate_count"] = payload["previous_count"]
    _write(producer_state_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["default_readonly_gate_required_evidence_check"]["passed"] is True


def test_premap_lab_preflight_rejects_standalone_arg_slot_row_mismatch(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["future_kernel_native_arg_slot_consumer_row_ok_count"] = 1
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_standalone_canary_json:"
        "standalone_arg_slot_future_kernel_native_arg_slot_consumer_"
        "row_ok_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_arg_slot_chain_invisible(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible"] = False
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_standalone_canary_json:"
        "standalone_arg_slot_future_kernel_native_arg_slot_consumer_"
        "dispatch_ptr_packet_visible_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_arg_slot_missing_mirror_macro(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["compiled_macros"][
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD"
    ] = False
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_standalone_canary_json:"
        "standalone_arg_slot_"
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD_not_enabled"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_arg_slot_multiple_mirror_macros(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["compiled_macros"][
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD"
    ] = True
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_standalone_canary_json:"
        "standalone_arg_slot_"
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD_enabled"
    ) in failures


def test_premap_lab_preflight_rejects_standalone_arg_slot_kernel_arg_pass(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    standalone_path = (
        tmp_path
        / "reports/default_gate_future_native_arg_slot_standalone_canary.json"
    )
    payload = json.loads(standalone_path.read_text())
    payload["future_kernel_native_arg_slot_consumer_passed_to_kernel"] = True
    _write(standalone_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_standalone_canary_json:"
        "standalone_arg_slot_"
        "future_kernel_native_arg_slot_consumer_passed_to_kernel_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_required_arg_slot_multiprogram_single_program(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    multiprogram_path = (
        tmp_path / "reports/default_gate_future_native_arg_slot_multiprogram_canary.json"
    )
    payload = json.loads(multiprogram_path.read_text())
    payload["future_kernel_native_dispatch_consumer_grid_x"] = 1
    payload["future_kernel_native_dispatch_consumer_program_count"] = 1
    payload["future_kernel_native_dispatch_consumer_launch_threads"] = 256
    _write(multiprogram_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_multiprogram_canary_json:"
        "multiprogram_arg_slot_grid_x_not_multiprogram"
    ) in failures


def test_premap_lab_preflight_rejects_required_arg_slot_multiprogram_missing_launch_threads(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    multiprogram_path = (
        tmp_path / "reports/default_gate_future_native_arg_slot_multiprogram_canary.json"
    )
    payload = json.loads(multiprogram_path.read_text())
    payload.pop("future_kernel_native_dispatch_consumer_launch_threads")
    _write(multiprogram_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_multiprogram_canary_json:"
        "multiprogram_arg_slot_launch_threads_missing"
    ) in failures


def test_premap_lab_preflight_rejects_required_arg_slot_multiprogram_bad_full_program_count(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    multiprogram_path = (
        tmp_path / "reports/default_gate_future_native_arg_slot_multiprogram_canary.json"
    )
    payload = json.loads(multiprogram_path.read_text())
    payload["future_kernel_native_dispatch_consumer_full_program_count"] = 1
    _write(multiprogram_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    failures = result["default_readonly_gate_required_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_multiprogram_canary_json:"
        "multiprogram_arg_slot_full_program_count_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_missing_typed_evidence_file(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    (tmp_path / "reports/default_gate_typed_consumer_gate.json").unlink()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:missing_file"
    ]


def test_premap_lab_preflight_can_defer_self_referential_runner_evidence(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    runner_path = (
        tmp_path
        / "reports/default_gate_native_online_prelaunch_canary_runner_32.json"
    )
    runner_path.unlink()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        defer_online_prelaunch_runner_evidence=True,
    )

    evidence_check = result["default_readonly_gate_required_evidence_check"]
    summary = result["lab_gate_status_summary"]
    assert result["passed"] is True
    assert evidence_check["passed"] is True
    assert evidence_check["deferred_labels"] == [
        "future_kernel_native_consumer_online_runner_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_runner_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_runner_32_128export_json",
        "future_kernel_native_launch_consumer_online_runner_16_128export_json",
        "native_typed_consumer_online_prelaunch_canary_runner_json",
    ]
    assert summary["deferred_online_prelaunch_runner_evidence"] is True
    assert summary["deferred_online_prelaunch_artifact_evidence"] is False
    assert summary["runtime_gate_evidence_deferred_count"] == 10
    assert summary["strict_default_gate_evidence_deferred_count"] == 5
    assert summary["required_evidence"]["required_count"] == 71
    assert summary["required_evidence"]["present_count"] == 69
    assert summary["required_evidence"]["passed_count"] == 69
    assert summary["optional_evidence"]["passed_count"] == 13
    for label in (
        "future_kernel_args_compatible_path_16_128export_artifact_check_json",
        "future_kernel_args_field_refresh_16_128export_artifact_check_json",
        "future_kernel_args_field_refresh_flatten_check_json",
    ):
        row = summary["optional_evidence"]["evidence"][label]
        assert row["present"] is True
        assert row["passed"] is True


def test_premap_lab_preflight_rejects_artifact_defer_without_runner_defer(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        defer_online_prelaunch_artifact_evidence=True,
    )

    summary = result["lab_gate_status_summary"]
    assert result["passed"] is False
    assert (
        "defer_online_prelaunch_artifact_evidence_requires_runner_defer"
        in result["failures"]
    )
    assert summary["deferred_online_prelaunch_runner_evidence"] is False
    assert summary["deferred_online_prelaunch_artifact_evidence"] is True


def test_premap_lab_preflight_rejects_runner_and_artifact_defer(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        defer_online_prelaunch_runner_evidence=True,
        defer_online_prelaunch_artifact_evidence=True,
    )

    summary = result["lab_gate_status_summary"]
    assert result["passed"] is False
    assert (
        "defer_online_prelaunch_runner_and_artifact_evidence_not_allowed"
        in result["failures"]
    )
    assert summary["deferred_online_prelaunch_runner_evidence"] is True
    assert summary["deferred_online_prelaunch_artifact_evidence"] is True


def test_premap_lab_preflight_allows_missing_typed_evidence_file_when_requested(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    (tmp_path / "reports/default_gate_typed_consumer_gate.json").unlink()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_missing_evidence=True,
    )

    assert result["passed"] is True
    row = next(
        item
        for item in result["default_readonly_gate_required_evidence_check"]["rows"]
        if item["label"] == "strict_kernel_side_typed_consumer_object_128_gate_json"
    )
    assert row["failure"] == "missing_file"
    assert row["allowed_missing"] is True


def test_premap_lab_preflight_allows_missing_required_multiprogram_evidence_when_requested(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    (
        tmp_path / "reports/default_gate_future_native_arg_slot_multiprogram_canary.json"
    ).unlink()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_missing_evidence=True,
    )

    assert result["passed"] is True
    row = next(
        item
        for item in result["default_readonly_gate_required_evidence_check"]["rows"]
        if item["label"] == "future_kernel_native_arg_slot_multiprogram_canary_json"
    )
    assert row["failure"] == "missing_file"
    assert row["allowed_missing"] is True


def test_premap_lab_preflight_rejects_directory_typed_evidence_path(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    gate_path = tmp_path / "reports/default_gate_typed_consumer_gate.json"
    gate_path.unlink()
    gate_path.mkdir()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:not_file"
    ]


def test_premap_lab_preflight_accepts_absolute_readonly_gate_path(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    absolute_default_gate = str((tmp_path / default_gate).resolve())
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=absolute_default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["trace_config_checks"][0]["readonly_gate_path"] == absolute_default_gate
    assert result["trace_config_checks"][0]["readonly_gate_path_label"] == default_gate


def test_premap_lab_preflight_rejects_kernel_arg_pass_in_default_config(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
        kernel_arg_pass_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["trace_config_checks"][0]["failures"] == ["kernel_arg_pass_enabled"]


def test_premap_lab_preflight_rejects_canary_gate_equal_to_default_gate(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=default_gate,
    )

    assert result["passed"] is False
    assert result["gate_pair_failures"] == [
        "default_readonly_gate_equals_canary_gate"
    ]
    assert "default_readonly_gate_equals_canary_gate" in result["failures"]


def test_premap_lab_preflight_accepts_risky_canary_metadata(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is True
    assert result["risky_canary_metadata_checks"][risky_gate]["passed"] is True


def test_premap_lab_preflight_rejects_risky_canary_without_metadata(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(tmp_path, "risky_gate", "risky_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_canary_metadata_checks"][risky_gate]["failures"] == [
        "canary_mismatch",
        "lab_default_mismatch",
    ]
    assert f"{risky_gate}:risky_canary_metadata_check_failed" in result["failures"]


def test_premap_lab_preflight_accepts_risky_trace_with_canary_gate_and_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    trace_config = _write_trace_config(
        tmp_path,
        "strict_name_without_canary",
        readonly_gate_path=risky_gate,
        live_enabled=True,
        kernel_arg_pass_enabled=True,
        risky_trace_canary=True,
        risky_trace_canary_scope="explicit_test_canary",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["passed"] is True
    assert result["trace_config_checks"][0]["failures"] == [
        "readonly_gate_path_mismatch",
        "kernel_arg_pass_enabled",
    ]


def test_premap_lab_preflight_rejects_risky_trace_without_canary_gate_metadata(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(tmp_path, "risky_gate", "risky_gate.json")
    _write_trace_config(
        tmp_path,
        "danger_canary",
        readonly_gate_path=risky_gate,
        live_enabled=True,
        kernel_arg_pass_enabled=True,
        risky_trace_canary=True,
        risky_trace_canary_scope="explicit_test_canary",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_gate_canary_mismatch",
        "risky_gate_lab_default_mismatch",
    ]
    assert (
        "configs/trace/danger_canary.yaml:risky_trace_config_check_failed"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_risky_trace_without_canary_label_or_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    _write_trace_config(
        tmp_path,
        "strict_name_without_marker",
        readonly_gate_path=risky_gate,
        live_enabled=True,
        kernel_arg_pass_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_trace_canary_marker_missing"
    ]


def test_premap_lab_preflight_rejects_named_canary_trace_without_explicit_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    _write_trace_config(
        tmp_path,
        "danger_canary",
        readonly_gate_path=risky_gate,
        live_enabled=True,
        kernel_arg_pass_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_trace_canary_marker_missing"
    ]


def test_premap_lab_preflight_all_risky_flags_require_explicit_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    flag_kwargs = [
        {"kernel_arg_pass_enabled": True},
        {"real_kernel_arg_mutation_enabled": True},
        {"single_field_dry_run_enabled": True},
        {"single_field_live_enabled": True},
    ]
    for index, kwargs in enumerate(flag_kwargs):
        _write_trace_config(
            tmp_path,
            f"risky_{index}",
            readonly_gate_path=risky_gate,
            **kwargs,
        )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    failures = {
        item["config_path"]: item["failures"]
        for item in result["risky_trace_config_checks"]
        if item["enabled_risky_flags"]
    }
    assert failures == {
        f"configs/trace/risky_{index}.yaml": ["risky_trace_canary_marker_missing"]
        for index in range(4)
    }


def test_premap_lab_preflight_rejects_truthy_string_canary_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    config_path = "configs/trace/risky_truthy_marker.yaml"
    _write(
        tmp_path / config_path,
        "trace:\n"
        "  runtime_shadow:\n"
        "    premap_consumer_require_readonly_gate: true\n"
        f"    premap_consumer_readonly_gate_path: {risky_gate}\n"
        "    premap_kernel_arg_handoff_live_enabled: true\n"
        "    premap_kernel_arg_handoff_kernel_arg_pass_enabled: true\n"
        "    premap_risky_trace_canary: 'true'\n"
        "    premap_risky_trace_canary_scope: malformed_truthy_string\n",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_trace_canary_marker_missing"
    ]


def test_premap_lab_preflight_reports_missing_trace_config(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=["configs/trace/missing.yaml"],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["trace_config_checks"][0]["config_path"] == "configs/trace/missing.yaml"
    assert result["trace_config_checks"][0]["failures"][0].startswith(
        "FileNotFoundError:"
    )


def test_premap_lab_preflight_cli_writes_summary(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    output = tmp_path / "preflight.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runtime-pattern",
            "configs/runtime/*.yaml",
            "--trace-config",
            trace_config,
            "--default-readonly-gate",
            default_gate,
            "--canary-gate",
            canary_gate,
            "--output-json",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["runtime_gate_evidence_scan"]["passed"] is True
    assert result["lab_gate_status_summary"]["passed"] is True
    assert (
        result["lab_gate_status_summary"]["required_evidence"]["passed_count"] == 71
    )


def test_premap_lab_preflight_cli_summary_only_writes_status_block(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    output = tmp_path / "preflight_status.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runtime-pattern",
            "configs/runtime/*.yaml",
            "--trace-config",
            trace_config,
            "--default-readonly-gate",
            default_gate,
            "--canary-gate",
            canary_gate,
            "--summary-only",
            "--output-json",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["default_readonly_gate_path"] == default_gate
    assert result["required_evidence"]["passed_count"] == 71
    assert result["optional_evidence"]["passed_count"] == 13
    assert "lab_gate_status_summary" not in result


def test_premap_lab_preflight_cli_summary_only_reports_prefetch_gate_failure(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    ready_report = (
        tmp_path
        / "outputs/reports/prefetch_cache_manager/"
        "measured_ready_time_gate_gpu1_dolly8_gen4.json"
    )
    ready_report.write_text(
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": True,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "preflight_status_failed.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runtime-pattern",
            "configs/runtime/*.yaml",
            "--trace-config",
            trace_config,
            "--default-readonly-gate",
            default_gate,
            "--canary-gate",
            canary_gate,
            "--summary-only",
            "--output-json",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert result["passed"] is False
    assert result["prefetch_lab_default_gate_passed"] is False
    assert result["prefetch_lab_default_gate_decision_status"] == "failed"
    assert (
        "full_fetch:ready_time_gate_report_allows_full_fetch"
        in result["prefetch_lab_default_gate_failures"]
    )
    assert result["prefetch_lab_default_full_fetch_failures"] == [
        "ready_time_gate_report_allows_full_fetch"
    ]


def _prelaunch_pointer_source_observer_check_payload(**overrides) -> dict:
    required_bool_values = {
        key: False for key in PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_BOOL_KEYS
    }
    required_bool_values[
        "runtime_shadow_premap_live_config_without_router_recorder_enabled"
    ] = True
    required_bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled"
    ] = True

    required_int_values = {
        key: 0 for key in PRELAUNCH_POINTER_SOURCE_OBSERVER_REQUIRED_INT_KEYS
    }
    required_int_values["sample_count"] = 16
    required_int_values["requested_output_token_count"] = 1024
    required_int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count"
    ] = 2560
    required_int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count"
    ] = 2560
    required_int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count"
    ] = 2560

    handoff_bool_values = {
        key: value
        for key, value in required_bool_values.items()
        if key.startswith(PRELAUNCH_POINTER_SOURCE_OBSERVER_HANDOFF_BOOL_PREFIX)
    }
    live_mutation_counter_values = {
        key: value
        for key, value in required_int_values.items()
        if key.startswith(
            PRELAUNCH_POINTER_SOURCE_OBSERVER_LIVE_MUTATION_COUNTER_PREFIX
        )
    }
    zero_counter_values = {
        key: required_int_values[key]
        for key in PRELAUNCH_POINTER_SOURCE_OBSERVER_ZERO_INT_KEYS
    }
    payload = {
        "mode": "premap_prelaunch_pointer_source_observer_check",
        "passed": True,
        "failures": [],
        "min_seen": 128,
        "observer_seen": 2560,
        "observer_available": 2560,
        "observer_vllm_device": 2560,
        "observer_unavailable": 0,
        "observer_non_device": 0,
        "min_sample_count": 16,
        "sample_count": 16,
        "min_requested_output_tokens": 1024,
        "requested_output_token_count": 1024,
        "live_handoff_enabled": False,
        "live_consumer_connected": False,
        "kernel_arg_pass_enabled": False,
        "real_kernel_arg_mutation_enabled": False,
        "producer_gpu_assignment_envelope_enabled": False,
        "live_config_without_router_recorder_enabled": True,
        "prelaunch_pointer_source_canary_enabled": True,
        "handoff_bool_values": handoff_bool_values,
        "live_mutation_counter_values": live_mutation_counter_values,
        "zero_counter_values": zero_counter_values,
        "required_bool_values": required_bool_values,
        "required_int_values": required_int_values,
    }
    payload.update(overrides)
    return payload


def _readonly_live_trusted_refs_check_payload(**overrides) -> dict:
    required_bool_values = {
        key: False
        for key in (
            READONLY_LIVE_TRUSTED_REFS_EXPECTED_TRUE_BOOL_KEYS
            | READONLY_LIVE_TRUSTED_REFS_REQUIRED_FALSE_BOOL_KEYS
        )
    }
    for key in READONLY_LIVE_TRUSTED_REFS_EXPECTED_TRUE_BOOL_KEYS:
        required_bool_values[key] = True

    handoff_bool_values = {
        key: value
        for key, value in required_bool_values.items()
        if key.startswith("runtime_shadow_premap_kernel_arg_handoff_")
    }
    live_mutation_counter_values = {
        key: 0
        for key in READONLY_LIVE_TRUSTED_REFS_REQUIRED_INT_KEYS
        if key.startswith("runtime_shadow_premap_kernel_arg_live_mutation_")
    }
    package_seen = 5120
    for key in READONLY_LIVE_TRUSTED_REFS_ALLOWED_NONZERO_COUNTERS:
        if key in live_mutation_counter_values:
            live_mutation_counter_values[key] = package_seen
    live_mutation_counter_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count"
    ] = package_seen // 2
    live_mutation_counter_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count"
    ] = package_seen // 2

    payload = {
        "schema_version": 1,
        "mode": "premap_readonly_live_trusted_refs_check",
        "passed": True,
        "failures": [],
        "min_package_seen": 128,
        "package_seen": package_seen,
        "package_pass_through": package_seen,
        "producer_future_typed_slot_envelope_count": package_seen // 2,
        "producer_gpu_assignment_envelope_count": package_seen // 2,
        "gpu_assignment_envelope_seen": package_seen,
        "trusted_refs_seen": package_seen,
        "trusted_refs_available": package_seen,
        "trusted_refs_unavailable": 0,
        "trusted_ptr_seen": package_seen,
        "trusted_ptr_available": package_seen,
        "trusted_ptr_vllm_device": package_seen,
        "trusted_ptr_mismatch": 0,
        "observer_seen": package_seen,
        "observer_available": package_seen,
        "observer_vllm_device": package_seen,
        "min_sample_count": 16,
        "sample_count": 16,
        "min_requested_output_tokens": 1024,
        "requested_output_token_count": 1024,
        "required_bool_values": required_bool_values,
        "handoff_bool_values": handoff_bool_values,
        "string_values": dict(READONLY_LIVE_TRUSTED_REFS_EXPECTED_STRING_VALUES),
        "live_mutation_counter_values": live_mutation_counter_values,
        "allowed_nonzero_live_mutation_counter_keys": sorted(
            READONLY_LIVE_TRUSTED_REFS_ALLOWED_NONZERO_COUNTERS
        ),
    }
    payload.update(overrides)
    return payload


def _payload_cache_demand_hit_shadow_publication_gate_payload(**overrides) -> dict:
    canary = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_demand_hit_shadow_publication_canary",
        "status": (
            "blocked_by_payloadless_instance_canary:"
            "blocked_by_mixed_outcome_dry_run_canary:"
            "blocked_by_accounting_dry_run_canary:test"
        ),
        "consumes_payloadless_instance_canary": True,
        "payloadless_instance_canary_status": (
            "blocked_by_mixed_outcome_dry_run_canary:"
            "blocked_by_accounting_dry_run_canary:test"
        ),
        "publication_schema": "payload_cache_demand_hit_shadow_publication_v1",
        "publication_scope": "shadow_only",
        "source_manager_contract": "ready_time_issue_demand_skeleton_v1",
        "shadow_publication_created": True,
        "shadow_publication_consumed_payloadless_instance": True,
        "demand_hit_shadow_publication_allowed": True,
        "demand_hit_published_to_shadow": True,
        "consumer_visible_payload_hit": False,
        "prefetched_demand_hit": True,
        "unprefetched_demand_hit": False,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "demand_hit_rate": 0.5,
        "payload_bytes": 0,
        "demand_hit_payload_bytes": 0,
        "payload_deref_attempted": False,
        "payload_handle_deref_attempted": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "live_runtime_instantiated": False,
        "decision": "blocked",
        "block_reason": "shadow_only_not_consumer_visible_payload_hit",
    }
    payload = {
        "source": "payload_cache_demand_hit_shadow_publication_gate",
        "artifact_kind": "payload_cache_demand_hit_shadow_publication_gate",
        "passed": True,
        "failures": [],
        "demand_hit_shadow_publication_allowed": True,
        "demand_hit_published_to_shadow": True,
        "consumer_visible_payload_hit": False,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "demand_hit_rate": 0.5,
        "payload_bytes": 0,
        "demand_hit_payload_bytes": 0,
        "payload_deref_attempted": False,
        "payload_handle_deref_attempted": False,
        "ready_credit": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "canary": canary,
    }
    payload.update(overrides)
    return payload


def test_payload_cache_demand_hit_shadow_publication_gate_rejects_runtime_extras():
    payload = _payload_cache_demand_hit_shadow_publication_gate_payload(
        live_payload_runtime_enabled=True,
        current_wna16_arg_compatible=True,
        issued_payload_count=1,
    )
    payload["canary"]["payload_transfer_runtime_enabled"] = True
    payload["canary"]["payload_deref_allowed"] = True
    payload["canary"]["issued_payload_count"] = 1

    failures = _validate_payload_cache_demand_hit_shadow_publication_gate_evidence(
        payload
    )

    assert (
        "payload_cache_demand_hit_shadow_publication_gate_live_payload_runtime_enabled_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_demand_hit_shadow_publication_gate_current_wna16_arg_compatible_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_demand_hit_shadow_publication_gate_issued_payload_count_unexpectedly_nonzero"
        in failures
    )
    assert (
        "payload_cache_demand_hit_shadow_publication_gate_canary_payload_transfer_runtime_enabled_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_demand_hit_shadow_publication_gate_canary_payload_deref_allowed_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_demand_hit_shadow_publication_gate_canary_issued_payload_count_unexpectedly_nonzero"
        in failures
    )


def test_payload_cache_demand_hit_shadow_publication_gate_rejects_bad_chain():
    payload = _payload_cache_demand_hit_shadow_publication_gate_payload()
    payload["canary"]["consumes_payloadless_instance_canary"] = False
    payload["canary"]["status"] += ":runtime_enabled"

    failures = _validate_payload_cache_demand_hit_shadow_publication_gate_evidence(
        payload
    )

    assert (
        "payload_cache_demand_hit_shadow_publication_gate_canary_consumes_payloadless_instance_canary_mismatch"
        in failures
    )
    assert (
        "payload_cache_demand_hit_shadow_publication_gate_canary_status_unsafe_marker:runtime_enabled"
        in failures
    )


def test_payload_cache_consumer_visible_hit_blocked_gate_accepts_strict_noop():
    failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        _payload_cache_consumer_visible_hit_blocked_gate_payload()
    )

    assert failures == []


def test_payload_cache_consumer_visible_hit_blocked_gate_rejects_runtime_extras():
    payload = _payload_cache_consumer_visible_hit_blocked_gate_payload()
    payload["consumer_visible_payload_hit"] = True
    payload["payload_bytes"] = 1
    payload["uses_current_wna16_args"] = True
    payload["event_timing_mode"] = "wall_time"
    payload["request_layer_idx"] = 1
    payload["request_expert_idx"] = 2
    payload["canary"]["request_layer_idx"] = 7
    payload["canary"]["request_expert_idx"] = 9
    payload["canary"]["planned_issue_count"] = 1
    payload["canary"]["copy_descriptor_count"] = 1
    payload["canary"]["ready_credit_count"] = 1
    payload["canary"]["demand_hit_published"] = True
    payload["canary"]["demand_hit_payload_bytes"] = 1

    failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        payload
    )

    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_consumer_visible_payload_hit_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_payload_bytes_unexpectedly_nonzero"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_uses_current_wna16_args_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_event_timing_mode_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_request_layer_idx_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_request_expert_idx_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_request_layer_idx_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_request_expert_idx_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_planned_issue_count_unexpectedly_nonzero"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_copy_descriptor_count_unexpectedly_nonzero"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_ready_credit_count_unexpectedly_nonzero"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_demand_hit_published_unexpectedly_enabled"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_demand_hit_payload_bytes_unexpectedly_nonzero"
        in failures
    )


def test_payload_cache_consumer_visible_hit_blocked_gate_requires_production_preflight():
    payload = _payload_cache_consumer_visible_hit_blocked_gate_payload()
    payload["production_preflight_ready"] = False
    payload["production_preflight_payload_bytes"] = 1
    payload["production_preflight_payload_transfer_enabled"] = True
    payload["production_preflight_kernel_arg_pass_allowed"] = True
    payload["production_preflight_passed_to_kernel"] = True
    payload["production_preflight_candidate_envelope_overhead_ratio"] = float("nan")
    payload["production_preflight_manager_demand_hit_rate"] = 2.0

    failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        payload
    )

    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_ready_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_payload_bytes_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_payload_transfer_enabled_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_kernel_arg_pass_allowed_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_passed_to_kernel_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_candidate_envelope_overhead_ratio_invalid"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_production_preflight_manager_demand_hit_rate_invalid"
        in failures
    )


def test_payload_cache_consumer_visible_hit_blocked_gate_rejects_bool_zero_counter():
    payload = _payload_cache_consumer_visible_hit_blocked_gate_payload()
    payload["canary"]["planned_issue_count"] = False

    failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        payload
    )

    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_planned_issue_count_unexpectedly_nonzero"
        in failures
    )


def test_payload_cache_consumer_visible_hit_blocked_gate_rejects_missing_canary_issue_counter():
    payload = _payload_cache_consumer_visible_hit_blocked_gate_payload()
    del payload["canary"]["planned_issue_count"]
    del payload["canary"]["copy_completion_count"]

    failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        payload
    )

    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_planned_issue_count_missing"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_copy_completion_count_missing"
        in failures
    )


def test_payload_cache_consumer_visible_hit_blocked_gate_rejects_bad_binding_and_chain():
    payload = _payload_cache_consumer_visible_hit_blocked_gate_payload()
    payload["request_matches_envelope_source_binding"] = False
    payload["source_issue_unique_key_count"] = 28
    payload["canary"]["consumes_payload_issue_payload_deref_blocked_canary"] = False
    payload["canary"]["payload_issue_payload_deref_status"] = "passed"
    payload["canary"]["status"] = "passed"

    failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        payload
    )

    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_request_matches_envelope_source_binding_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_source_issue_unique_key_count_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_consumes_payload_issue_payload_deref_blocked_canary_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_payload_issue_payload_deref_status_mismatch"
        in failures
    )
    assert (
        "payload_cache_consumer_visible_hit_blocked_gate_canary_status_mismatch"
        in failures
    )


def test_payload_cache_manager_production_preflight_rejects_nan_overhead(tmp_path: Path):
    manager_path = "reports/payload_cache_manager_useful_work_ab_gate.json"
    _write(
        tmp_path / manager_path,
        json.dumps(_payload_cache_manager_useful_work_ab_gate_payload()) + "\n",
    )
    payload = _payload_cache_manager_production_ab_preflight_payload(
        manager_gate_json=manager_path,
    )
    payload["candidate_envelope_overhead_ratio"] = float("nan")

    failures = _validate_required_evidence_payload(
        "payload_cache_manager_production_ab_preflight_json",
        payload,
        evidence_paths={
            "payload_cache_manager_useful_work_ab_gate_json": manager_path,
        },
        root=tmp_path,
    )

    assert (
        "payload_cache_manager_production_ab_preflight_json:"
        "payload_cache_manager_production_ab_preflight_"
        "candidate_envelope_overhead_ratio_invalid"
    ) in failures


def test_payload_cache_manager_production_preflight_rejects_manager_gate_mismatch(
    tmp_path: Path,
):
    manager_path = "reports/payload_cache_manager_useful_work_ab_gate.json"
    _write(
        tmp_path / manager_path,
        json.dumps(_payload_cache_manager_useful_work_ab_gate_payload()) + "\n",
    )
    payload = _payload_cache_manager_production_ab_preflight_payload(
        manager_gate_json=manager_path,
    )
    payload["manager_demand_hit_count"] = 198

    failures = _validate_required_evidence_payload(
        "payload_cache_manager_production_ab_preflight_json",
        payload,
        evidence_paths={
            "payload_cache_manager_useful_work_ab_gate_json": manager_path,
        },
        root=tmp_path,
    )

    assert (
        "payload_cache_manager_production_ab_preflight_json:"
        "payload_cache_manager_production_ab_preflight_"
        "manager_demand_hit_count_manager_gate_mismatch"
    ) in failures


def test_payload_cache_manager_production_preflight_rejects_missing_manager_gate(
    tmp_path: Path,
):
    manager_path = "reports/missing_payload_cache_manager_useful_work_ab_gate.json"
    payload = _payload_cache_manager_production_ab_preflight_payload(
        manager_gate_json=manager_path,
    )

    failures = _validate_required_evidence_payload(
        "payload_cache_manager_production_ab_preflight_json",
        payload,
        evidence_paths={
            "payload_cache_manager_useful_work_ab_gate_json": manager_path,
        },
        root=tmp_path,
    )

    assert (
        "payload_cache_manager_production_ab_preflight_json:"
        "payload_cache_manager_production_ab_preflight_"
        "manager_gate_payload_unreadable"
    ) in failures
    assert (
        "payload_cache_manager_production_ab_preflight_json:"
        "payload_cache_manager_production_ab_preflight_"
        "manager_issued_prefetch_count_manager_gate_mismatch"
    ) in failures


def test_payload_cache_manager_production_preflight_rejects_unsafe_flags(
    tmp_path: Path,
):
    manager_path = "reports/payload_cache_manager_useful_work_ab_gate.json"
    _write(
        tmp_path / manager_path,
        json.dumps(_payload_cache_manager_useful_work_ab_gate_payload()) + "\n",
    )
    unsafe_fields = (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "real_ready_credit_granted",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
    )

    for unsafe_field in unsafe_fields:
        payload = _payload_cache_manager_production_ab_preflight_payload(
            manager_gate_json=manager_path,
        )
        payload[unsafe_field] = True

        failures = _validate_required_evidence_payload(
            "payload_cache_manager_production_ab_preflight_json",
            payload,
            evidence_paths={
                "payload_cache_manager_useful_work_ab_gate_json": manager_path,
            },
            root=tmp_path,
        )

        assert (
            "payload_cache_manager_production_ab_preflight_json:"
            "payload_cache_manager_production_ab_preflight_"
            f"{unsafe_field}_mismatch"
        ) in failures


def test_prelaunch_pointer_source_observer_check_evidence_accepts_strict_noop():
    failures = _validate_prelaunch_pointer_source_observer_check_evidence(
        _prelaunch_pointer_source_observer_check_payload()
    )

    assert failures == []


def test_prelaunch_pointer_source_observer_check_evidence_rejects_handoff_bool_true():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload["handoff_bool_values"][
        "runtime_shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled"
    ] = True

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_handoff_bool_true" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_live_counter_nonzero():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload["live_mutation_counter_values"][
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_native_row_fill_count"
    ] = 1

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_live_counter_nonzero" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_truncated_handoff_map():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload["handoff_bool_values"] = {}

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_handoff_bool_map_truncated" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_missing_required_bools():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload.pop("required_bool_values")

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_required_bools_missing" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_missing_required_ints():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload.pop("required_int_values")

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_required_ints_missing" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_truncated_live_counter_map():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload["live_mutation_counter_values"] = {}

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_live_counter_map_truncated" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_truncated_zero_values():
    payload = _prelaunch_pointer_source_observer_check_payload()
    payload["zero_counter_values"] = {}

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_zero_values_truncated" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_zero_bool():
    payload = _prelaunch_pointer_source_observer_check_payload()
    key = next(iter(payload["zero_counter_values"]))
    payload["zero_counter_values"][key] = False

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_zero_value_not_int" in failures


def test_prelaunch_pointer_source_observer_check_evidence_rejects_zero_float():
    payload = _prelaunch_pointer_source_observer_check_payload()
    key = next(iter(payload["zero_counter_values"]))
    payload["zero_counter_values"][key] = 0.0

    failures = _validate_prelaunch_pointer_source_observer_check_evidence(payload)

    assert "prelaunch_pointer_source_observer_zero_value_not_int" in failures


def test_readonly_live_trusted_refs_check_evidence_accepts_strict_noop():
    failures = _validate_readonly_live_trusted_refs_check_evidence(
        _readonly_live_trusted_refs_check_payload()
    )

    assert failures == []


def test_readonly_live_trusted_refs_check_evidence_rejects_kernel_arg_pass():
    payload = _readonly_live_trusted_refs_check_payload()
    key = "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    payload["required_bool_values"][key] = True
    payload["handoff_bool_values"][key] = True

    failures = _validate_readonly_live_trusted_refs_check_evidence(payload)

    assert "readonly_live_trusted_refs_required_bool_true" in failures


def test_readonly_live_trusted_refs_check_evidence_rejects_truncated_false_handoff_map():
    payload = _readonly_live_trusted_refs_check_payload()
    key = "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    assert payload["required_bool_values"][key] is False
    del payload["handoff_bool_values"][key]

    failures = _validate_readonly_live_trusted_refs_check_evidence(payload)

    assert "readonly_live_trusted_refs_handoff_bool_map_truncated" in failures
    assert "readonly_live_trusted_refs_handoff_bool_mismatch" in failures


def test_readonly_live_trusted_refs_check_evidence_rejects_live_kernel_pass_counter():
    payload = _readonly_live_trusted_refs_check_payload()
    payload["live_mutation_counter_values"][
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count"
    ] = 1

    failures = _validate_readonly_live_trusted_refs_check_evidence(payload)

    assert "readonly_live_trusted_refs_live_counter_nonzero" in failures


def test_readonly_live_trusted_refs_check_evidence_rejects_package_mismatch():
    payload = _readonly_live_trusted_refs_check_payload(
        package_pass_through=5119,
    )

    failures = _validate_readonly_live_trusted_refs_check_evidence(payload)

    assert "readonly_live_trusted_refs_package_pass_through_mismatch" in failures


def test_readonly_live_trusted_refs_check_evidence_rejects_nested_counter_mismatch():
    payload = _readonly_live_trusted_refs_check_payload()
    payload["live_mutation_counter_values"][
        "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count"
    ] = 0

    failures = _validate_readonly_live_trusted_refs_check_evidence(payload)

    assert "readonly_live_trusted_refs_live_counter_summary_mismatch" in failures


def _vllm_replay_visible_native_producer_payload() -> dict[str, object]:
    return {
        "ok": True,
        "enabled": True,
        "present": True,
        "passed": True,
        "failures": [],
        "mode": "payload_cache_vllm_replay_visible_native_producer_contract",
        "contract_boundary": "inprocess_vllm_replay_visible_native_producer_op",
        "native_runtime": True,
        "inprocess_native_op": True,
        "vllm_replay_visible": True,
        "prelaunch_callable_native_session": True,
        "post_export_native_replay": False,
        "standalone_native_replay": False,
        "native_graph_replay": False,
        "transition_state_on_device": True,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "python_transition_skipped": True,
        "packet_count": 8,
        "expected_packet_count": 8,
        "issue_candidate_count": 64,
        "expected_issue_candidate_count": 64,
        "expected_issue_candidate_count_source": "graph_visible_producer_contract",
        "producer_update_count": 8,
        "replay_visible_update_count": 8,
        "prelaunch_probe_count": 8,
        "prelaunch_abi_ready_count": 0,
        "prelaunch_abi_blocked_count": 8,
        "prelaunch_device_tensor_count": 8,
        "prelaunch_host_tensor_count": 0,
        "prelaunch_int32_count": 8,
        "prelaunch_dtype_mismatch_count": 0,
        "prelaunch_current_count_device_tensor_count": 8,
        "prelaunch_current_count_device_scalar_int32_count": 8,
        "prelaunch_current_count_host_scalar_available_count": 0,
        "prelaunch_native_session_update_v1_abi_ready": False,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": 8,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": 0,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready": True,
        "prelaunch_last_current_count_source_kind": (
            "num_tokens_post_padded_device_tensor"
        ),
        "prelaunch_last_count_ptr_block_reason": None,
        "prelaunch_last_block_reason": "current_count_host_scalar_not_available",
        "source_kind": "vllm_prelaunch_inprocess_native_producer",
        "current_expert_ptr_source_kind": "vllm_prelaunch_device_tensor",
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "ready_for_payload_cache_runtime_lab_gate": True,
        "payload_bytes": 0,
        "ready": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def test_vllm_replay_visible_native_producer_contract_evidence_accepts_online_session_gate():
    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_native_producer_contract_json",
        _vllm_replay_visible_native_producer_payload(),
    )

    assert failures == []


def test_vllm_replay_visible_native_producer_contract_evidence_rejects_kernel_pass():
    payload = _vllm_replay_visible_native_producer_payload()
    payload["passed_to_kernel"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_native_producer_contract_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_native_producer_contract_json:"
        "payload_cache_vllm_replay_visible_native_producer_contract_"
        "passed_to_kernel_not_false"
    ) in failures


def test_vllm_replay_visible_count_ptr_native_producer_evidence_accepts_checker_artifact():
    payload = count_ptr_native_producer_checker.check_contract(
        _vllm_replay_visible_native_producer_payload()
    )

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json",
        payload,
    )

    assert failures == []


def test_vllm_replay_visible_count_ptr_native_producer_evidence_rejects_host_scalar_artifact():
    source = _vllm_replay_visible_native_producer_payload()
    source["prelaunch_current_count_host_scalar_available_count"] = 8
    source["prelaunch_native_session_update_count_ptr_v1_abi_ready_count"] = 0
    source["prelaunch_native_session_update_count_ptr_v1_abi_blocked_count"] = 8
    source["prelaunch_native_session_update_count_ptr_v1_abi_ready"] = False
    payload = count_ptr_native_producer_checker.check_contract(source)

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json:"
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_"
        "passed_mismatch"
    ) in failures


def test_vllm_replay_visible_count_ptr_native_producer_evidence_rejects_artifact_unsafe_flags():
    payload = count_ptr_native_producer_checker.check_contract(
        _vllm_replay_visible_native_producer_payload()
    )
    payload["ready"] = True
    payload["payload_transfer_enabled"] = True
    payload["kernel_arg_pass_allowed"] = True
    payload["uses_current_wna16_args"] = True
    payload["measures_tpot"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json:"
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_"
        "ready_mismatch"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json:"
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_"
        "payload_transfer_enabled_mismatch"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_json:"
        "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract_"
        "uses_current_wna16_args_mismatch"
    ) in failures


def _vllm_replay_visible_count_ptr_readiness_payload() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_vllm_replay_visible_native_count_ptr_readiness",
        "contract_boundary": "future_session_update_count_ptr_v1_prelaunch_probe",
        "input_mode": "payload_cache_vllm_replay_visible_native_producer_contract",
        "input_contract_boundary": "inprocess_vllm_replay_visible_native_producer_op",
        "source_kind": "vllm_prelaunch_inprocess_native_producer",
        "prelaunch_last_current_count_source_kind": (
            "num_tokens_post_padded_device_tensor"
        ),
        "expected_packet_count": 8,
        "expected_packet_count_source": "prelaunch_probe_count",
        "graph_visible_expected_packet_count_present": False,
        "prelaunch_probe_count": 8,
        "prelaunch_probe_summary_scope": "last_router_sample",
        "prelaunch_probe_summary_run_sample_count": 1,
        "prelaunch_current_count_device_scalar_int32_count": 8,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": 8,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": 0,
        "ready_for_future_count_ptr_native_session": True,
        "payload_bytes": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def test_vllm_replay_visible_count_ptr_readiness_evidence_accepts_noop_gate():
    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json",
        _vllm_replay_visible_count_ptr_readiness_payload(),
    )

    assert failures == []


def test_vllm_replay_visible_count_ptr_readiness_evidence_rejects_kernel_pass():
    payload = _vllm_replay_visible_count_ptr_readiness_payload()
    payload["kernel_arg_pass"] = True

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:kernel_arg_pass_mismatch"
        in failures
    )


def test_vllm_replay_visible_count_ptr_readiness_evidence_rejects_count_mismatch():
    payload = _vllm_replay_visible_count_ptr_readiness_payload()
    payload["prelaunch_native_session_update_count_ptr_v1_abi_ready_count"] = 7

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count_mismatch"
    ) in failures


def test_vllm_replay_visible_count_ptr_readiness_evidence_rejects_missing_provenance():
    payload = _vllm_replay_visible_count_ptr_readiness_payload()
    payload.pop("expected_packet_count_source")
    payload.pop("graph_visible_expected_packet_count_present")
    payload.pop("prelaunch_probe_summary_scope")
    payload.pop("prelaunch_probe_summary_run_sample_count")

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "expected_packet_count_source_invalid"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "graph_visible_expected_packet_count_present_invalid"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "prelaunch_probe_summary_scope_invalid"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "prelaunch_probe_summary_run_sample_count_invalid"
    ) in failures


def test_vllm_replay_visible_count_ptr_readiness_evidence_rejects_wrong_input_source():
    payload = _vllm_replay_visible_count_ptr_readiness_payload()
    payload["input_contract_boundary"] = "standalone_native_replay"
    payload["source_kind"] = "raw_vllm_performance_summary"

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "input_contract_boundary_mismatch"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "source_kind_mismatch"
    ) in failures


def test_vllm_replay_visible_count_ptr_readiness_evidence_rejects_lab_pass_claim():
    payload = _vllm_replay_visible_count_ptr_readiness_payload()
    payload["lab_gate_passed"] = 1
    payload["runtime_ready"] = 0

    failures = _validate_required_evidence_payload(
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json",
        payload,
    )

    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "lab_gate_passed_unexpectedly_true"
    ) in failures
    assert (
        "payload_cache_vllm_replay_visible_count_ptr_readiness_json:"
        "runtime_ready_unexpectedly_true"
    ) in failures
