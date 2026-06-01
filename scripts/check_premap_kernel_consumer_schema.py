#!/usr/bin/env python3
"""Validate the readonly premap kernel-side typed consumer schema artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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


REQUIRED_ROW_FIELDS = {
    "descriptor_ptr": {"required": True, "null_allowed": False},
    "packed_weight_descriptor": {"required": True, "null_allowed": False},
    "scale_metadata_handle": {"required": True, "null_allowed": False},
    "aux_metadata_handle": {"required": False, "null_allowed": True},
}
REQUIRED_ROW_METADATA = {
    "layer_id": {
        "abi_dtype": "int32",
        "shape": "scalar",
        "source": "prelaunch_layer_context",
        "required": True,
    },
    "expert_id": {
        "abi_dtype": "int32",
        "shape": ["row_count"],
        "source": "address_key.layer_expert",
        "required": True,
    },
    "address_key_hash": {
        "abi_dtype": "uint64",
        "shape": ["row_count"],
        "source": "address_key",
        "required": True,
    },
    "row_order_hash": {
        "abi_dtype": "uint64",
        "shape": "scalar",
        "source": "prepared_handle_table",
        "required": True,
    },
    "ordered_row_hash": {
        "abi_dtype": "uint64",
        "shape": "scalar",
        "source": "prepared_handle_table",
        "required": True,
    },
}
FORBIDDEN_LAB_DEFAULT_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
    "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
}
REQUIRED_STEPWISE_DEBUG_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_CONSUMER_PATH",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_SIDE_COMPATIBLE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_CONSUMER_ARGS",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_ARGS_COMPATIBLE_CONSUMER_PATH",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI",
}
ALLOWED_CURRENT_STATUS = {
    "native_stub_pending",
    "native_stub_online_canary_passed",
}
FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS = [
    "future_kernel_native_consumer_params_struct_size",
    "future_kernel_native_consumer_params_struct_align",
    "future_kernel_native_consumer_result_struct_size",
    "future_kernel_native_consumer_result_struct_align",
    "future_kernel_native_consumer_params_offset_descriptor_ptr",
    "future_kernel_native_consumer_params_offset_packed_weight_descriptor",
    "future_kernel_native_consumer_params_offset_scale_metadata_handle",
    "future_kernel_native_consumer_params_offset_aux_metadata_handle",
    "future_kernel_native_consumer_params_offset_expert_id",
    "future_kernel_native_consumer_params_offset_address_key_hash",
    "future_kernel_native_consumer_params_offset_row_count",
    "future_kernel_native_consumer_params_offset_field_mask",
    "future_kernel_native_consumer_params_offset_payload_bytes",
    "future_kernel_native_consumer_params_offset_flags",
]
FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS = [
    "future_kernel_native_launch_consumer_launch_struct_size",
    "future_kernel_native_launch_consumer_launch_struct_align",
    "future_kernel_native_launch_consumer_params_struct_size",
    "future_kernel_native_launch_consumer_params_struct_align",
    "future_kernel_native_launch_consumer_result_struct_size",
    "future_kernel_native_launch_consumer_result_struct_align",
    "future_kernel_native_launch_consumer_offset_params",
    "future_kernel_native_launch_consumer_offset_abi_version",
    "future_kernel_native_launch_consumer_offset_params_struct_size",
    "future_kernel_native_launch_consumer_offset_result_struct_size",
    "future_kernel_native_launch_consumer_offset_row_stride",
    "future_kernel_native_launch_consumer_offset_payload_bytes",
    "future_kernel_native_launch_consumer_offset_flags",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS = [
    "future_kernel_native_dispatch_consumer_dispatch_struct_size",
    "future_kernel_native_dispatch_consumer_dispatch_struct_align",
    "future_kernel_native_dispatch_consumer_result_struct_size",
    "future_kernel_native_dispatch_consumer_result_struct_align",
    "future_kernel_native_dispatch_consumer_offset_launch",
    "future_kernel_native_dispatch_consumer_offset_dispatch_version",
    "future_kernel_native_dispatch_consumer_offset_grid_x",
    "future_kernel_native_dispatch_consumer_offset_block_x",
    "future_kernel_native_dispatch_consumer_offset_shared_mem_bytes",
    "future_kernel_native_dispatch_consumer_offset_row_offset",
    "future_kernel_native_dispatch_consumer_offset_row_limit",
    "future_kernel_native_dispatch_consumer_offset_rows_per_program",
    "future_kernel_native_dispatch_consumer_offset_payload_bytes",
    "future_kernel_native_dispatch_consumer_offset_flags",
]
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS = [
    "future_kernel_native_dispatch_ptr_consumer_packet_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_packet_struct_align",
    "future_kernel_native_dispatch_ptr_consumer_dispatch_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_result_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_offset_dispatch",
    "future_kernel_native_dispatch_ptr_consumer_offset_abi_version",
    "future_kernel_native_dispatch_ptr_consumer_offset_dispatch_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_offset_result_struct_size",
    "future_kernel_native_dispatch_ptr_consumer_offset_payload_bytes",
    "future_kernel_native_dispatch_ptr_consumer_offset_flags",
]
FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS = [
    "future_kernel_native_arg_slot_consumer_slot_struct_size",
    "future_kernel_native_arg_slot_consumer_slot_struct_align",
    "future_kernel_native_arg_slot_consumer_dispatch_ptr_struct_size",
    "future_kernel_native_arg_slot_consumer_result_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr",
    "future_kernel_native_arg_slot_consumer_offset_abi_version",
    "future_kernel_native_arg_slot_consumer_offset_dispatch_ptr_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_result_struct_size",
    "future_kernel_native_arg_slot_consumer_offset_payload_bytes",
    "future_kernel_native_arg_slot_consumer_offset_flags",
]
FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED = {
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
FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED = {
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
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED = {
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
FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED = {
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
FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED = {
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


def _check_layout_field_contract(
    *,
    native_abi: dict[str, Any],
    failures: list[str],
    reported_key: str,
    fields_key: str,
    expected_fields: list[str],
) -> list[str]:
    if native_abi.get(reported_key) is not True:
        failures.append(f"native_consumer_abi.{reported_key}_not_true")
    observed = native_abi.get(fields_key)
    if observed != expected_fields:
        failures.append(
            f"native_consumer_abi.{fields_key}_mismatch:{observed!r}!={expected_fields!r}"
        )
    return observed if isinstance(observed, list) else []


def _check_layout_expected_contract(
    *,
    native_abi: dict[str, Any],
    failures: list[str],
    expected_key: str,
    expected_values: dict[str, int],
) -> dict[str, Any]:
    observed = native_abi.get(expected_key)
    if observed != expected_values:
        failures.append(
            f"native_consumer_abi.{expected_key}_mismatch:{observed!r}!={expected_values!r}"
        )
    return observed if isinstance(observed, dict) else {}


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_kernel_consumer_schema_artifact(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return {
            "path": str(path),
            "passed": False,
            "failures": [f"load_failed:{type(exc).__name__}:{exc}"],
            "rows": rows,
        }
    if not isinstance(payload, dict):
        return {
            "path": str(path),
            "passed": False,
            "failures": ["schema_not_mapping"],
            "rows": rows,
        }

    schema = payload.get("schema") or {}
    source_contract = payload.get("source_contract") or {}
    native_abi = payload.get("native_consumer_abi") or {}
    safety = payload.get("safety_contract") or {}
    macro_ladder = payload.get("debug_macro_ladder") or {}

    expected_scalars = {
        "schema_version": 1,
        "artifact_id": "premap_kernel_side_typed_consumer_schema_v1",
        "artifact_kind": "premap_kernel_consumer_schema",
        "status": "readonly_shadow_only",
    }
    for key, expected in expected_scalars.items():
        observed = payload.get(key)
        if observed != expected:
            failures.append(f"{key}_mismatch:{observed!r}!={expected!r}")

    expected_schema = {
        "name": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
        "hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
        "target_runtime": "vllm_awq_wna16_fused_moe",
        "native_consumer_mode": "typed_shadow_object",
    }
    for key, expected in expected_schema.items():
        observed = schema.get(key)
        if observed != expected:
            failures.append(f"schema.{key}_mismatch:{observed!r}!={expected!r}")

    expected_source = {
        "handle_table_columns": list(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
        "handle_table_schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        "semantic_schema_name": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
        "semantic_schema_hash": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
        "kernel_side_adapter_schema_name": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
        "kernel_side_adapter_schema_hash": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    }
    for key, expected in expected_source.items():
        observed = source_contract.get(key)
        if observed != expected:
            failures.append(f"source_contract.{key}_mismatch")

    if native_abi.get("layout") != "struct_of_arrays":
        failures.append("native_consumer_abi.layout_mismatch")
    expected_native_abi = {
        "abi_name": "premap_kernel_side_typed_consumer_abi_v1",
        "cpp_header": "microbench/premap_kernel_consumer/premap_typed_consumer_abi_v1.h",
        "cpp_struct": "PremapKernelSideTypedConsumerAbiV1",
        "handle_column_count": 4,
        "payload_bytes_allowed": False,
        "kernel_arg_pass_allowed": False,
        "adapter_name": "premap_kernel_side_typed_consumer_adapter_v1",
        "adapter_header": "microbench/premap_kernel_consumer/premap_typed_consumer_adapter_v1.h",
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
    }
    for key, expected in expected_native_abi.items():
        observed = native_abi.get(key)
        if observed != expected:
            failures.append(
                f"native_consumer_abi.{key}_mismatch:{observed!r}!={expected!r}"
            )
    if native_abi.get("row_order") != "vllm_prelaunch_sorted_token_ids_order":
        failures.append("native_consumer_abi.row_order_mismatch")
    if native_abi.get("row_count_source") != "consumer_row_count":
        failures.append("native_consumer_abi.row_count_source_mismatch")
    native_layout_fields = _check_layout_field_contract(
        native_abi=native_abi,
        failures=failures,
        reported_key="future_kernel_native_consumer_abi_layout_reported",
        fields_key="future_kernel_native_consumer_abi_layout_fields",
        expected_fields=FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS,
    )
    launch_layout_fields = _check_layout_field_contract(
        native_abi=native_abi,
        failures=failures,
        reported_key="future_kernel_native_consumer_launch_abi_layout_reported",
        fields_key="future_kernel_native_consumer_launch_abi_layout_fields",
        expected_fields=FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS,
    )
    dispatch_layout_fields = _check_layout_field_contract(
        native_abi=native_abi,
        failures=failures,
        reported_key="future_kernel_native_consumer_dispatch_abi_layout_reported",
        fields_key="future_kernel_native_consumer_dispatch_abi_layout_fields",
        expected_fields=FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS,
    )
    dispatch_ptr_layout_fields = _check_layout_field_contract(
        native_abi=native_abi,
        failures=failures,
        reported_key="future_kernel_native_consumer_dispatch_ptr_abi_layout_reported",
        fields_key="future_kernel_native_consumer_dispatch_ptr_abi_layout_fields",
        expected_fields=FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS,
    )
    arg_slot_layout_fields = _check_layout_field_contract(
        native_abi=native_abi,
        failures=failures,
        reported_key="future_kernel_native_consumer_arg_slot_abi_layout_reported",
        fields_key="future_kernel_native_consumer_arg_slot_abi_layout_fields",
        expected_fields=FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_FIELDS,
    )
    native_layout_expected = _check_layout_expected_contract(
        native_abi=native_abi,
        failures=failures,
        expected_key="future_kernel_native_consumer_abi_layout_expected",
        expected_values=FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
    )
    launch_layout_expected = _check_layout_expected_contract(
        native_abi=native_abi,
        failures=failures,
        expected_key="future_kernel_native_consumer_launch_abi_layout_expected",
        expected_values=FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
    )
    dispatch_layout_expected = _check_layout_expected_contract(
        native_abi=native_abi,
        failures=failures,
        expected_key="future_kernel_native_consumer_dispatch_abi_layout_expected",
        expected_values=FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
    )
    dispatch_ptr_layout_expected = _check_layout_expected_contract(
        native_abi=native_abi,
        failures=failures,
        expected_key="future_kernel_native_consumer_dispatch_ptr_abi_layout_expected",
        expected_values=FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
    )
    arg_slot_layout_expected = _check_layout_expected_contract(
        native_abi=native_abi,
        failures=failures,
        expected_key="future_kernel_native_consumer_arg_slot_abi_layout_expected",
        expected_values=FUTURE_KERNEL_NATIVE_CONSUMER_ARG_SLOT_ABI_LAYOUT_EXPECTED,
    )

    row_fields = native_abi.get("row_fields")
    row_fields = row_fields if isinstance(row_fields, list) else []
    row_field_names = [
        item.get("name") if isinstance(item, dict) else None for item in row_fields
    ]
    expected_row_field_names = list(REQUIRED_ROW_FIELDS)
    if row_field_names != expected_row_field_names:
        failures.append(
            "row_field_order_or_count_mismatch:"
            f"{row_field_names!r}!={expected_row_field_names!r}"
        )
    duplicate_row_fields = sorted(
        {name for name in row_field_names if name is not None and row_field_names.count(name) > 1}
    )
    failures.extend(f"row_field_duplicate:{name}" for name in duplicate_row_fields)
    fields_by_name = {
        item.get("name"): item for item in row_fields if isinstance(item, dict)
    }
    for name, expected_field in REQUIRED_ROW_FIELDS.items():
        field = fields_by_name.get(name)
        row: dict[str, Any] = {
            "field": name,
            "present": field is not None,
            "required": expected_field["required"],
        }
        if field is None:
            failures.append(f"row_field_missing:{name}")
            rows.append(row)
            continue
        row.update(
            {
                "abi_dtype": field.get("abi_dtype"),
                "shape": field.get("shape"),
                "payload_deref_allowed": field.get("payload_deref_allowed"),
                "device_ownership": field.get("device_ownership"),
                "lifetime": field.get("lifetime"),
            }
        )
        if field.get("source_column") != name:
            failures.append(f"row_field_source_column_mismatch:{name}")
        if field.get("abi_dtype") != "uint64":
            failures.append(f"row_field_dtype_mismatch:{name}")
        if field.get("shape") != ["row_count"]:
            failures.append(f"row_field_shape_mismatch:{name}")
        if field.get("required") is not expected_field["required"]:
            failures.append(f"row_field_required_mismatch:{name}")
        if field.get("null_allowed", False) is not expected_field["null_allowed"]:
            failures.append(f"row_field_null_allowed_mismatch:{name}")
        if field.get("payload_deref_allowed") is not False:
            failures.append(f"row_field_payload_deref_allowed:{name}")
        if field.get("device_ownership") != "model_weight_device":
            failures.append(f"row_field_device_ownership_mismatch:{name}")
        if field.get("lifetime") != "model_load_epoch":
            failures.append(f"row_field_lifetime_mismatch:{name}")
        rows.append(row)

    metadata = native_abi.get("row_metadata")
    metadata = metadata if isinstance(metadata, list) else []
    metadata_names = [
        item.get("name") if isinstance(item, dict) else None for item in metadata
    ]
    expected_metadata_names = list(REQUIRED_ROW_METADATA)
    if metadata_names != expected_metadata_names:
        failures.append(
            "row_metadata_order_or_count_mismatch:"
            f"{metadata_names!r}!={expected_metadata_names!r}"
        )
    duplicate_metadata = sorted(
        {name for name in metadata_names if name is not None and metadata_names.count(name) > 1}
    )
    failures.extend(f"row_metadata_duplicate:{name}" for name in duplicate_metadata)
    metadata_by_name = {
        item.get("name"): item for item in metadata if isinstance(item, dict)
    }
    for name, expected in REQUIRED_ROW_METADATA.items():
        item = metadata_by_name.get(name)
        if item is None:
            failures.append(f"row_metadata_missing:{name}")
            continue
        for key, expected_value in expected.items():
            if item.get(key) != expected_value:
                failures.append(f"row_metadata_{key}_mismatch:{name}")

    expected_safety = {
        "payload_bytes_required": 0,
        "ready_credit_required": False,
        "changes_router_required": False,
        "changes_descriptor_order_required": False,
        "changes_kernel_launch_args_required": False,
        "passed_to_kernel_required": False,
        "live_compatible_with_current_wna16_args_required": False,
    }
    for key, expected in expected_safety.items():
        observed = safety.get(key)
        if observed != expected:
            failures.append(f"safety_contract.{key}_mismatch:{observed!r}")
    current_status = safety.get("current_status")
    if current_status not in ALLOWED_CURRENT_STATUS:
        failures.append(f"safety_contract.current_status_mismatch:{current_status!r}")

    flags = macro_ladder.get("flags")
    flags = flags if isinstance(flags, list) else []
    if macro_ladder.get("compile_guard_macro") != "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1":
        failures.append("debug_macro_compile_guard_mismatch")
    flags_by_name = {
        item.get("name"): item for item in flags if isinstance(item, dict)
    }
    for name in sorted(REQUIRED_STEPWISE_DEBUG_MACROS):
        flag = flags_by_name.get(name)
        if flag is None:
            failures.append(f"debug_macro_missing:{name}")
            continue
        if flag.get("default") != "disabled":
            failures.append(f"debug_macro_default_not_disabled:{name}")
        if flag.get("individually_enableable") is not True:
            failures.append(f"debug_macro_not_individual:{name}")
    for name in sorted(FORBIDDEN_LAB_DEFAULT_MACROS):
        flag = flags_by_name.get(name)
        if flag is None:
            failures.append(f"debug_macro_missing:{name}")
            continue
        if flag.get("default") != "disabled":
            failures.append(f"forbidden_macro_default_not_disabled:{name}")
        if flag.get("individually_enableable") is not False:
            failures.append(f"forbidden_macro_individually_enableable:{name}")
        if flag.get("forbidden_in_lab_default") is not True:
            failures.append(f"forbidden_macro_not_marked:{name}")

    return {
        "path": str(path),
        "passed": not failures,
        "failures": failures,
        "schema_name": schema.get("name"),
        "schema_hash": schema.get("hash"),
        "row_field_count": len(row_fields),
        "row_field_names": row_field_names,
        "row_metadata_count": len(metadata),
        "row_metadata_names": metadata_names,
        "macro_count": len(flags),
        "future_kernel_native_consumer_dispatch_abi_name": native_abi.get(
            "future_kernel_native_consumer_dispatch_abi_name"
        ),
        "future_kernel_native_consumer_dispatch_abi_struct": native_abi.get(
            "future_kernel_native_consumer_dispatch_abi_struct"
        ),
        "future_kernel_native_consumer_dispatch_abi_mode": native_abi.get(
            "future_kernel_native_consumer_dispatch_abi_mode"
        ),
        "future_kernel_native_consumer_dispatch_abi_row_assignment_formula": (
            native_abi.get(
                "future_kernel_native_consumer_dispatch_abi_row_assignment_formula"
            )
        ),
        "future_kernel_native_consumer_dispatch_abi_current_wna16_arg_compatible": (
            native_abi.get(
                "future_kernel_native_consumer_dispatch_abi_current_wna16_arg_compatible"
            )
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_name": native_abi.get(
            "future_kernel_native_consumer_dispatch_ptr_abi_name"
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_struct": native_abi.get(
            "future_kernel_native_consumer_dispatch_ptr_abi_struct"
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_mode": native_abi.get(
            "future_kernel_native_consumer_dispatch_ptr_abi_mode"
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_source": native_abi.get(
            "future_kernel_native_consumer_dispatch_ptr_abi_source"
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": (
            native_abi.get(
                "future_kernel_native_consumer_dispatch_ptr_abi_current_wna16_arg_compatible"
            )
        ),
        "future_kernel_native_consumer_arg_slot_abi_name": native_abi.get(
            "future_kernel_native_consumer_arg_slot_abi_name"
        ),
        "future_kernel_native_consumer_arg_slot_abi_struct": native_abi.get(
            "future_kernel_native_consumer_arg_slot_abi_struct"
        ),
        "future_kernel_native_consumer_arg_slot_abi_mode": native_abi.get(
            "future_kernel_native_consumer_arg_slot_abi_mode"
        ),
        "future_kernel_native_consumer_arg_slot_abi_source": native_abi.get(
            "future_kernel_native_consumer_arg_slot_abi_source"
        ),
        "future_kernel_native_consumer_arg_slot_abi_current_wna16_arg_compatible": (
            native_abi.get(
                "future_kernel_native_consumer_arg_slot_abi_current_wna16_arg_compatible"
            )
        ),
        "future_kernel_native_consumer_abi_layout_reported": native_abi.get(
            "future_kernel_native_consumer_abi_layout_reported"
        ),
        "future_kernel_native_consumer_abi_layout_fields": native_layout_fields,
        "future_kernel_native_consumer_abi_layout_expected": native_layout_expected,
        "future_kernel_native_consumer_launch_abi_layout_reported": native_abi.get(
            "future_kernel_native_consumer_launch_abi_layout_reported"
        ),
        "future_kernel_native_consumer_launch_abi_layout_fields": launch_layout_fields,
        "future_kernel_native_consumer_launch_abi_layout_expected": (
            launch_layout_expected
        ),
        "future_kernel_native_consumer_dispatch_abi_layout_reported": native_abi.get(
            "future_kernel_native_consumer_dispatch_abi_layout_reported"
        ),
        "future_kernel_native_consumer_dispatch_abi_layout_fields": dispatch_layout_fields,
        "future_kernel_native_consumer_dispatch_abi_layout_expected": (
            dispatch_layout_expected
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_layout_reported": native_abi.get(
            "future_kernel_native_consumer_dispatch_ptr_abi_layout_reported"
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_layout_fields": (
            dispatch_ptr_layout_fields
        ),
        "future_kernel_native_consumer_dispatch_ptr_abi_layout_expected": (
            dispatch_ptr_layout_expected
        ),
        "future_kernel_native_consumer_arg_slot_abi_layout_reported": native_abi.get(
            "future_kernel_native_consumer_arg_slot_abi_layout_reported"
        ),
        "future_kernel_native_consumer_arg_slot_abi_layout_fields": (
            arg_slot_layout_fields
        ),
        "future_kernel_native_consumer_arg_slot_abi_layout_expected": (
            arg_slot_layout_expected
        ),
        "rows": rows,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema_path", type=Path)
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_kernel_consumer_schema_artifact(args.schema_path)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
