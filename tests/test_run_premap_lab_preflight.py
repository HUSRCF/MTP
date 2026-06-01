from __future__ import annotations

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
from scripts.run_premap_lab_preflight import main, run_premap_lab_preflight
from scripts.run_premap_lab_preflight import _program_iteration_hash
from scripts.check_premap_kernel_consumer_schema import (
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


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
            "_arg_slot_32input_alias_rowstats_hashchain_projection_nodefer.json"
        ), label
        assert "_32input.json" not in path, label
    for label in artifact_labels:
        path = evidence[label]
        assert path.endswith(
            "_artifact_check_arg_slot_32input_alias_rowstats_hashchain_projection_nodefer.json"
        ), label
        assert "_32input.json" not in path, label
        assert "artifact_check" in path


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


def _runner_future_kernel_args_summary() -> dict[str, object]:
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
            "future_kernel_consumer_args_payload_bytes": 0,
            "future_kernel_consumer_args_passed_to_kernel": False,
            "future_kernel_consumer_args_changes_kernel_launch_args": False,
            "future_kernel_consumer_args_current_wna16_arg_compatible": False,
            "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
            "future_kernel_consumer_args_field_mask": 15,
            "future_kernel_consumer_args_required_field_mask": 7,
            "future_kernel_consumer_args_single_field_mirror_checked": True,
            "future_kernel_consumer_args_single_field_mirror_field_name": (
                "scale_metadata_handle"
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
        }
    )
    payload.update(_RUNNER_NATIVE_LAYOUT_SUMMARY)
    payload.update(_RUNNER_LAUNCH_LAYOUT_SUMMARY)
    payload.update(_RUNNER_DISPATCH_LAYOUT_SUMMARY)
    payload.update(_RUNNER_DISPATCH_PTR_LAYOUT_SUMMARY)
    payload.update(_RUNNER_ARG_SLOT_LAYOUT_SUMMARY)
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
        },
    }


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
    native_bridge_input_path = f"reports/{name}_native_bridge_input.json"
    native_online_input_path = f"reports/{name}_native_online_prelaunch_input.json"
    native_online_stub_path = (
        f"reports/{name}_native_typed_consumer_stub_online_prelaunch_input_canary.json"
    )
    native_online_perf_path = (
        f"reports/{name}_native_online_prelaunch_export_performance.json"
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
            root / native_online_stub_path,
            json.dumps(_native_stub_evidence_payload(native_online_input_path)) + "\n",
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
        "  future_kernel_native_dispatch_consumer_full_table_required: true\n"
        "  future_kernel_native_dispatch_ptr_consumer_required: true\n"
        "  future_kernel_native_dispatch_consumer_program_iteration_required: true\n"
        "  future_kernel_native_dispatch_consumer_row_assignment_formula: row_offset + program_id * rows_per_program + lane_id\n"
        "  future_kernel_native_arg_slot_online_total_mirror_coverage_required: true\n"
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
            "  native_typed_consumer_bridge_input_json: "
            f"{native_bridge_input_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_canary_json: "
            f"{native_online_stub_path}\n"
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
            "optional_evidence_paths:\n"
            "  aux_metadata_single_field_handle_handoff_canary_smoke_json: "
            f"{aux_metadata_single_field_canary_path}\n"
            "  future_kernel_native_arg_slot_aux_metadata_mirror_canary_json: "
            f"{standalone_arg_slot_aux_metadata_canary_path}\n"
            "  future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json: "
            f"{standalone_arg_slot_descriptor_ptr_canary_path}\n"
            "  future_kernel_native_arg_slot_packed_weight_mirror_canary_json: "
            f"{standalone_arg_slot_packed_weight_canary_path}\n"
            "  descriptor_ptr_single_field_handle_handoff_canary_smoke_json: "
            f"{descriptor_ptr_single_field_canary_path}\n"
            "  native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json: "
            f"{native_online_per_field_stub_path}\n"
            "  packed_weight_single_field_handle_handoff_canary_smoke_json: "
            f"{packed_weight_single_field_canary_path}\n"
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
    assert result["runtime_gate_evidence_scan"]["gate_count"] == 3
    assert result["runtime_gate_evidence_scan"]["evidence_path_count"] == 50
    assert result["default_readonly_gate_required_evidence_check"]["passed"] is True
    summary = result["lab_gate_status_summary"]
    assert summary["passed"] is True
    assert summary["default_readonly_gate_path"] == default_gate
    assert summary["default_contract_passed"] is True
    assert (
        summary["default_kernel_consumer_schema_name"]
        == "fused_moe_awq_wna16_kernel_side_typed_consumer_object_v1"
    )
    assert summary["default_kernel_consumer_schema_row_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
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
    assert summary["default_kernel_consumer_arg_slot_optional_mirror_field_coverage"] == [
        "aux_metadata_handle",
        "descriptor_ptr",
        "packed_weight_descriptor",
    ]
    assert summary["default_kernel_consumer_arg_slot_optional_mirror_evidence_labels"] == [
        "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
        "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
    ]
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
    assert summary["required_evidence"]["required_count"] == 15
    assert summary["required_evidence"]["present_count"] == 15
    assert summary["required_evidence"]["passed_count"] == 15
    assert summary["optional_evidence"]["required_count"] == 13
    assert summary["optional_evidence"]["present_count"] == 13
    assert summary["optional_evidence"]["passed_count"] == 13
    assert (
        summary["optional_evidence"]["evidence"][
            "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
            "packed_weight_single_field_handle_handoff_canary_smoke_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
            "future_kernel_native_arg_slot_packed_weight_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
            "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
            "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
            "aux_metadata_single_field_handle_handoff_canary_smoke_json"
        ]["passed"]
        is True
    )
    assert (
        summary["optional_evidence"]["evidence"][
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


def _run_preflight_with_modified_default_runner(
    tmp_path: Path,
    mutate_runner: Callable[[dict[str, object]], None],
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


def test_premap_lab_preflight_allows_missing_optional_per_field_canary(
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
    assert result["passed"] is True
    assert summary["required_evidence"]["passed_count"] == 15
    assert summary["default_optional_evidence_passed"] is True
    assert summary["optional_evidence"]["present_count"] == 6
    assert summary["optional_evidence"]["passed_count"] == 6


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
    assert "default_readonly_gate_optional_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_optional_evidence_check"]["failures"]
    assert (
        "packed_weight_single_field_handle_handoff_canary_smoke_json:"
        "premap_consumer_descriptor_prep_consumer_shim_"
        "single_field_handle_handoff_canary_field_name_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_optional_arg_slot_packed_weight_mismatch(
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
    assert "default_readonly_gate_optional_evidence_check_failed" in result["failures"]
    failures = result["default_readonly_gate_optional_evidence_check"]["failures"]
    assert (
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json:"
        "standalone_arg_slot_packed_weight_"
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name_mismatch"
    ) in failures


def test_premap_lab_preflight_rejects_optional_arg_slot_missing_field_macros(
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
        assert (
            "default_readonly_gate_optional_evidence_check_failed"
            in result["failures"]
        )
        failures = result["default_readonly_gate_optional_evidence_check"]["failures"]
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
        "kernel_side_typed_consumer_object_required_mismatch"
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
            "native_typed_consumer_online_prelaunch_canary_runner_json:missing_evidence_path",
            "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json:missing_evidence_path",
            "future_kernel_native_dispatch_consumer_online_runner_32_128export_json:missing_evidence_path",
            "future_kernel_native_dispatch_ptr_standalone_canary_json:missing_evidence_path",
            "future_kernel_native_arg_slot_standalone_canary_json:missing_evidence_path",
            "strict_live_connected_readonly_128_gate_json:missing_evidence_path",
        "strict_native_typed_consumer_bridge_128_gate_json:missing_evidence_path",
        "strict_kernel_side_typed_consumer_object_128_gate_json:missing_evidence_path",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:missing_evidence_path",
        "strict_kernel_side_typed_row_consumer_path_128_gate_json:missing_evidence_path",
        "strict_single_field_handle_handoff_canary_128_gate_json:missing_evidence_path",
    }


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
    assert summary["required_evidence"]["required_count"] == 15
    assert summary["required_evidence"]["present_count"] == 13
    assert summary["required_evidence"]["passed_count"] == 13
    assert summary["optional_evidence"]["passed_count"] == 10
    for label in (
        "future_kernel_native_consumer_online_artifact_check_16_128export_json",
        "future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json",
        "future_kernel_native_launch_consumer_online_artifact_check_16_128export_json",
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
        result["lab_gate_status_summary"]["required_evidence"]["passed_count"]
        == 15
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
    assert result["required_evidence"]["passed_count"] == 15
    assert result["optional_evidence"]["passed_count"] == 13
    assert "lab_gate_status_summary" not in result
