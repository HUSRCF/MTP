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
    "future_kernel_native_arg_slot_online_total_mirror_coverage_required": True,
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
    "strict_native_typed_consumer_bridge_128_gate_json",
    "native_typed_consumer_bridge_smoke_json",
    "strict_native_stub_online_invocation_canary_128_gate_json",
    "native_typed_consumer_stub_gpu1_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_canary_json",
    "native_typed_consumer_online_prelaunch_canary_runner_json",
    "future_kernel_native_dispatch_ptr_standalone_canary_json",
    "future_kernel_native_arg_slot_standalone_canary_json",
    "future_kernel_native_arg_slot_multiprogram_canary_json",
    "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json",
    "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json",
    "future_kernel_native_dispatch_consumer_online_artifact_check_32_128export_json",
    "future_kernel_native_dispatch_consumer_online_runner_32_128export_json",
}
OPTIONAL_DEFAULT_GATE_EVIDENCE_JSON_LABELS = {
    "aux_metadata_single_field_handle_handoff_canary_smoke_json",
    "descriptor_ptr_single_field_handle_handoff_canary_smoke_json",
    "future_kernel_native_consumer_online_artifact_check_16_128export_json",
    "future_kernel_native_consumer_online_runner_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_artifact_check_16_128export_json",
    "future_kernel_native_dispatch_consumer_online_runner_16_128export_json",
    "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
    "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
    "future_kernel_native_arg_slot_online_merged_aux_metadata_mirror_runner_json",
    "future_kernel_native_arg_slot_online_merged_descriptor_ptr_mirror_runner_json",
    "future_kernel_native_arg_slot_online_merged_packed_weight_mirror_runner_json",
    "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
    "future_kernel_args_aux_metadata_mirror_canary_json",
    "future_kernel_args_descriptor_ptr_mirror_canary_json",
    "future_kernel_args_packed_weight_mirror_canary_json",
    "future_kernel_native_launch_consumer_online_artifact_check_16_128export_json",
    "future_kernel_native_launch_consumer_online_runner_16_128export_json",
    "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
    "packed_weight_single_field_handle_handoff_canary_smoke_json",
}
ARG_SLOT_MIRROR_FIELDS = tuple(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
ARG_SLOT_OPTIONAL_MIRROR_LABEL_BY_FIELD = {
    "aux_metadata_handle": "future_kernel_native_arg_slot_aux_metadata_mirror_canary_json",
    "descriptor_ptr": "future_kernel_native_arg_slot_descriptor_ptr_mirror_canary_json",
    "packed_weight_descriptor": (
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json"
    ),
}
ARG_SLOT_ONLINE_MERGED_OPTIONAL_MIRROR_RUNNER_LABEL_BY_FIELD = {
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
_FUTURE_KERNEL_ALL_FIELD_MASK = 0xF
_FUTURE_KERNEL_AUX_FIELD_MASK = 0x8
_UINT64_MASK = (1 << 64) - 1
_PROGRAM_ITERATION_HASH_FORMULA = (
    "mix64(grid_x + 0xd15c2001) ^ mix64(block_x + 0xd15c2002) ^ "
    "mix64(row_offset + 0xd15c2003) ^ mix64(row_limit + 0xd15c2004) ^ "
    "mix64(last_program_active_rows + 0xd15c2005) ^ "
    "mix64(inactive_lane_count + 0xd15c2006)"
)


def _int_metric(metrics: dict[str, Any], key: str) -> int | None:
    value = metrics.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _bool_metric(metrics: dict[str, Any], key: str) -> bool | None:
    value = metrics.get(key)
    return value if isinstance(value, bool) else None


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
    return [] if actual == expected else [f"{key}_mismatch"]


def _check_metric_equals_if_present(
    metrics: dict[str, Any],
    key: str,
    expected: Any,
) -> list[str]:
    return [] if key not in metrics else _check_metric_equals(metrics, key, expected)


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
        "native_typed_consumer_stub_online_prelaunch_input_canary_json",
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
        "future_kernel_native_arg_slot_packed_weight_mirror_canary_json",
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
    if evidence_label == "future_kernel_native_arg_slot_online_merged_multiprogram_runner_json":
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
                evidence,
                root=root,
                evidence_paths=evidence_paths,
            )
        ]
    for (
        field,
        label,
    ) in ARG_SLOT_ONLINE_MERGED_OPTIONAL_MIRROR_RUNNER_LABEL_BY_FIELD.items():
        if evidence_label == label:
            return [
                f"{evidence_label}:{failure}"
                for failure in _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
                    evidence,
                    root=root,
                    evidence_paths=evidence_paths,
                    expected_stub_output_label=None,
                    arg_slot_mirror_field=field,
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
                    "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
                }
                else None
            )
        is_online_prelaunch_stub = evidence_label in {
            "native_typed_consumer_stub_online_prelaunch_input_canary_json",
            "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json",
        }
        is_per_field_stub = (
            evidence_label
            == "native_typed_consumer_stub_online_prelaunch_input_per_field_canary_json"
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
                    else None
                ),
                required_disabled_macros=(
                    ("MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",)
                    if is_per_field_stub
                    else ()
                ),
                require_kernel_side_abi_meta=is_per_field_stub,
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
    if consumer_view_projection_hash is not None:
        projection_hashes.append(consumer_view_projection_hash)
    if any(value is None for value in projection_hashes):
        failures.append(f"{failure_prefix}_handle_projection_hash_missing")
    elif len(set(projection_hashes)) != 1:
        failures.append(f"{failure_prefix}_handle_projection_hash_mismatch")
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


def _validate_future_native_arg_slot_online_merged_multiprogram_runner_evidence(
    evidence: dict[str, Any],
    *,
    root: Path | None = None,
    evidence_paths: dict[str, Any] | None = None,
    expected_stub_output_label: str | None = (
        "future_kernel_native_arg_slot_online_merged_multiprogram_canary_json"
    ),
    arg_slot_mirror_field: str = "scale_metadata_handle",
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

    stub_output = evidence.get("stub_output_json")
    if not isinstance(stub_output, str) or not stub_output:
        failures.append(f"{failure_prefix}_stub_output_json_missing")
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
        if actual != expected:
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
    risky_canary_gates: list[str] | None = None,
    allow_missing_evidence: bool = False,
    defer_online_prelaunch_runner_evidence: bool = False,
    defer_online_prelaunch_artifact_evidence: bool = False,
    allow_bootstrap_preflight: bool = False,
    allow_online_runner_self_finalization: bool = False,
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
    arg_slot_standalone_mirror_field_coverage = _arg_slot_mirror_field_coverage(
        arg_slot_standalone_payload
    )
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
        | set(arg_slot_optional_mirror_field_coverage)
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
    consumer_view_summary = (
        online_merged_arg_slot_summary
        if online_merged_arg_slot_summary.get(
            "future_kernel_native_consumer_view_checked"
        )
        is True
        else dispatch_runner_summary
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

    def _hex_metric_text(metrics: dict[str, Any], key: str) -> str | None:
        value = metrics.get(key)
        return (
            value
            if isinstance(value, str) and _hex64_metric(metrics, key) is not None
            else None
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
    if consumer_view_projection_value is not None:
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
        and not consumer_view_all_handle_fields_read
    ):
        failures.append(
            "default_kernel_consumer_consumer_view_all_handle_fields_read_unchecked"
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
        "default_kernel_consumer_consumer_view_source_packet_chain_depth": (
            _int_metric(
                consumer_view_summary,
                "future_kernel_native_consumer_view_source_packet_chain_depth",
            )
        ),
        "default_kernel_consumer_consumer_view_payload_bytes": (
            _int_metric(
                consumer_view_summary,
                "future_kernel_native_consumer_view_payload_bytes",
            )
        ),
        "default_kernel_consumer_consumer_view_passed_to_kernel": (
            _bool_metric(
                consumer_view_summary,
                "future_kernel_native_consumer_view_passed_to_kernel",
            )
        ),
        "default_kernel_consumer_consumer_view_changes_kernel_launch_args": (
            _bool_metric(
                consumer_view_summary,
                "future_kernel_native_consumer_view_changes_kernel_launch_args",
            )
        ),
        "default_kernel_consumer_consumer_view_current_wna16_arg_compatible": (
            _bool_metric(
                consumer_view_summary,
                "future_kernel_native_consumer_view_current_wna16_arg_compatible",
            )
        ),
        "default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation": (
            _bool_metric(
                consumer_view_summary,
                "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation",
            )
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
        "default_kernel_consumer_arg_slot_optional_mirror_field_coverage": (
            sorted(arg_slot_optional_mirror_field_coverage)
        ),
        "default_kernel_consumer_arg_slot_optional_mirror_evidence_labels": (
            sorted(arg_slot_optional_mirror_evidence_labels)
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

    return {
        "passed": not failures,
        "failures": failures,
        "lab_gate_status_summary": lab_gate_status_summary,
        "gate_pair_failures": gate_pair_failures,
        "default_readonly_gate_contract_check": default_gate_contract_check,
        "default_kernel_consumer_schema_check": (
            default_kernel_consumer_schema_check
        ),
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
