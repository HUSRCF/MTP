#!/usr/bin/env python3
"""Validate a compact premap lab preflight summary artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_ROW_FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]
REQUIRED_ROW_METADATA = [
    "layer_id",
    "expert_id",
    "address_key_hash",
    "row_order_hash",
    "ordered_row_hash",
]
REQUIRED_SHA_FIELDS = [
    "default_readonly_gate_sha256",
    "canary_gate_sha256",
    "default_kernel_consumer_schema_artifact_sha256",
    "default_kernel_consumer_dispatch_runner_evidence_sha256",
    "default_kernel_consumer_dispatch_runner_artifact_evidence_sha256",
    "default_kernel_consumer_online_merged_multiprogram_evidence_sha256",
    "default_kernel_consumer_dispatch_ptr_standalone_evidence_sha256",
    "default_kernel_consumer_arg_slot_standalone_evidence_sha256",
    "default_kernel_consumer_wna16_side_variant_evidence_sha256",
]
REQUIRED_LAYOUT_CHECKS = {
    "default_kernel_consumer_kernel_arg_packet_layout_reported": True,
    "default_kernel_consumer_kernel_entry_summary_layout_reported": True,
    "default_kernel_consumer_kernel_entry_args_layout_reported": True,
    "default_kernel_consumer_kernel_arg_packet_struct_size": 32,
    "default_kernel_consumer_kernel_arg_packet_offset_program_view_ptr": 0,
    "default_kernel_consumer_kernel_entry_summary_struct_size": 104,
    "default_kernel_consumer_kernel_entry_summary_offset_row_hash_accumulator": 80,
    "default_kernel_consumer_kernel_entry_args_struct_size": 40,
    "default_kernel_consumer_kernel_entry_args_offset_summary": 8,
}
PAYLOAD_CACHE_RUNTIME_PARTICIPATION_ALLOWED_STATUSES = frozenset(
    {
        "ready_time_candidate_requires_lab_gate",
        "accounting_only_no_issued_fetch",
        "accounting_only_no_used_fetch",
        "accounting_only_all_demands_ready_late",
    }
)
PAYLOAD_CACHE_RUNTIME_PLAN_ALLOWED_STATUSES = frozenset(
    {
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch",
        "participation_not_full_fetch_candidate:accounting_only_no_issued_fetch",
        "participation_not_full_fetch_candidate:accounting_only_no_used_fetch",
        "participation_not_full_fetch_candidate:accounting_only_all_demands_ready_late",
    }
)
PAYLOAD_CACHE_RUNTIME_EXECUTION_ALLOWED_STATUSES = frozenset(
    f"blocked_by_runtime_plan:{status}"
    for status in PAYLOAD_CACHE_RUNTIME_PLAN_ALLOWED_STATUSES
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"summary JSON must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_hex64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 <= parsed <= 0xFFFFFFFFFFFFFFFF


def _path_label(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute():
        try:
            return path.resolve(strict=False).relative_to(Path.cwd()).as_posix()
        except ValueError:
            return path.resolve(strict=False).as_posix()
    return path.as_posix()


def _same_path_label(lhs: Any, rhs: Any) -> bool:
    lhs_label = _path_label(lhs)
    rhs_label = _path_label(rhs)
    return lhs_label is not None and lhs_label == rhs_label


def _int_metric(summary: dict[str, Any], key: str) -> int | None:
    value = summary.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _float_metric(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _payloadless_execution_ready(summary: dict[str, Any], failures: list[str]) -> bool:
    prefix = "default_kernel_consumer_future_wna16_payloadless_execution"
    expected_values = {
        "default_kernel_consumer_wna16_side_variant_ready": True,
        f"{prefix}_evidence_passed": True,
        f"{prefix}_ready": True,
        f"{prefix}_gate_ready": True,
        f"{prefix}_lab_preflight_ready": True,
        f"{prefix}_native_ready": True,
        f"{prefix}_native_requested": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_all_four_ready": True,
        f"{prefix}_all_four_fields_read": True,
        f"{prefix}_kernel_side_ready": True,
        f"{prefix}_kernel_side_hashes_valid": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    benchmark_repeat_count = _int_metric(summary, f"{prefix}_benchmark_repeat_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    if benchmark_repeat_count != 3:
        failures.append(f"{prefix}_benchmark_repeat_count_mismatch")
        ready = False
    return ready


def _future_wna16_variant_execution_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    prefix = "default_kernel_consumer_future_wna16_variant_execution"
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_ready": True,
        f"{prefix}_gate_ready": True,
        f"{prefix}_payloadless_gate_ready": True,
        f"{prefix}_native_requested": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_native_artifact_ready": True,
        f"{prefix}_not_current_wna16_kernel": True,
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
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    for key, expected in {
        f"{prefix}_artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
        f"{prefix}_name": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        f"{prefix}_mode": "independent_future_wna16_typed_slot_kernel_variant_execution",
        f"{prefix}_source": "premap_future_wna16_typed_slot_payloadless_execution_v1",
        f"{prefix}_scope": "independent_native_typed_slot_kernel_variant_execution",
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    payloadless_source_count = _int_metric(
        summary,
        "default_kernel_consumer_future_wna16_payloadless_execution_source_count",
    )
    payloadless_row_count = _int_metric(
        summary,
        "default_kernel_consumer_future_wna16_payloadless_execution_row_count",
    )
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if payloadless_source_count is not None and source_count != payloadless_source_count:
        failures.append(f"{prefix}_payloadless_source_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    if payloadless_row_count is not None and row_count != payloadless_row_count:
        failures.append(f"{prefix}_payloadless_row_count_mismatch")
        ready = False
    payloadless_path = summary.get(
        "default_kernel_consumer_future_wna16_payloadless_execution_evidence_path"
    )
    payloadless_sha = summary.get(
        "default_kernel_consumer_future_wna16_payloadless_execution_evidence_sha256"
    )
    if summary.get(f"{prefix}_payloadless_json") != payloadless_path:
        failures.append(f"{prefix}_payloadless_json_mismatch")
        ready = False
    if summary.get(f"{prefix}_payloadless_sha256") != payloadless_sha:
        failures.append(f"{prefix}_payloadless_sha256_mismatch")
        ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_payloadless_sha256",
        f"{prefix}_native_sha256",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    for key in (
        f"{prefix}_evidence_path",
        f"{prefix}_payloadless_json",
        f"{prefix}_native_json",
    ):
        if not isinstance(summary.get(key), str) or not summary.get(key):
            failures.append(f"{key}_missing")
            ready = False
    for key in (
        f"{prefix}_native_host_wall_ms",
        f"{prefix}_outer_wall_ms",
    ):
        value = _float_metric(summary, key)
        if value is None or value <= 0:
            failures.append(f"{key}_invalid")
            ready = False
    return ready


def _future_wna16_useful_consumer_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    prefix = "default_kernel_consumer_future_wna16_useful_consumer"
    variant_prefix = "default_kernel_consumer_future_wna16_variant_execution"
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_ready": True,
        f"{prefix}_gate_ready": True,
        f"{prefix}_native_stub_checked": True,
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
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    for key, expected in {
        f"{prefix}_artifact_kind": "future_wna16_typed_slot_kernel_variant_useful_consumer",
        f"{prefix}_name": "premap_future_wna16_typed_slot_useful_consumer_v1",
        f"{prefix}_mode": "independent_wna16_side_typed_slot_useful_consumer",
        f"{prefix}_source": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        f"{prefix}_semantics": "wna16_side_variant_all_four_field_projection",
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    rows_consumed = _int_metric(summary, f"{prefix}_rows_consumed")
    variant_source_count = _int_metric(summary, f"{variant_prefix}_source_count")
    variant_row_count = _int_metric(summary, f"{variant_prefix}_row_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if variant_source_count is not None and source_count != variant_source_count:
        failures.append(f"{prefix}_variant_source_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count or rows_consumed != row_count:
        failures.append(f"{prefix}_row_coverage_mismatch")
        ready = False
    if variant_row_count is not None and row_count != variant_row_count:
        failures.append(f"{prefix}_variant_row_count_mismatch")
        ready = False
    if summary.get(f"{prefix}_fields_consumed") != REQUIRED_ROW_FIELDS:
        failures.append(f"{prefix}_fields_consumed_mismatch")
        ready = False
    for field in REQUIRED_ROW_FIELDS:
        if row_count is not None and summary.get(
            f"{prefix}_{field}_row_ok_count"
        ) != row_count:
            failures.append(f"{prefix}_{field}_row_ok_count_mismatch")
            ready = False
        if not _is_hex_u64(summary.get(f"{prefix}_{field}_field_hash")):
            failures.append(f"{prefix}_{field}_field_hash_invalid")
            ready = False
        if not _is_hex_u64(summary.get(f"{prefix}_{field}_useful_hash")):
            failures.append(f"{prefix}_{field}_useful_hash_invalid")
            ready = False
    for key in (
        f"{prefix}_wna16_side_hash",
        f"{prefix}_wna16_side_handle_projection_hash",
    ):
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    if summary.get(f"{prefix}_execution_json") != summary.get(
        f"{variant_prefix}_evidence_path"
    ):
        failures.append(f"{prefix}_execution_json_mismatch")
        ready = False
    if summary.get(f"{prefix}_execution_sha256") != summary.get(
        f"{variant_prefix}_evidence_sha256"
    ):
        failures.append(f"{prefix}_execution_sha256_mismatch")
        ready = False
    if summary.get(f"{prefix}_native_timing_json") != summary.get(
        f"{variant_prefix}_native_json"
    ):
        failures.append(f"{prefix}_native_timing_json_mismatch")
        ready = False
    if summary.get(f"{prefix}_native_timing_sha256") != summary.get(
        f"{variant_prefix}_native_sha256"
    ):
        failures.append(f"{prefix}_native_timing_sha256_mismatch")
        ready = False
    if summary.get(f"{prefix}_native_stub_json") != summary.get(
        f"{prefix}_timing_native_stub_json"
    ):
        failures.append(f"{prefix}_native_stub_json_mismatch")
        ready = False
    if summary.get(f"{prefix}_native_stub_sha256") != summary.get(
        f"{prefix}_timing_native_stub_sha256"
    ):
        failures.append(f"{prefix}_native_stub_sha256_mismatch")
        ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_execution_sha256",
        f"{prefix}_native_timing_sha256",
        f"{prefix}_native_stub_sha256",
        f"{prefix}_timing_native_stub_sha256",
        f"{prefix}_hash",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    for key in (
        f"{prefix}_evidence_path",
        f"{prefix}_execution_json",
        f"{prefix}_native_timing_json",
        f"{prefix}_native_stub_json",
        f"{prefix}_timing_native_stub_json",
    ):
        if not isinstance(summary.get(key), str) or not summary.get(key):
            failures.append(f"{key}_missing")
            ready = False
    return ready


def _future_wna16_payloadless_useful_execution_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    prefix = "default_kernel_consumer_future_wna16_payloadless_useful_execution"
    useful_prefix = "default_kernel_consumer_future_wna16_useful_consumer"
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_ready": True,
        f"{prefix}_gate_ready": True,
        f"{prefix}_chain_checked": True,
        f"{prefix}_native_stub_checked": True,
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
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    for key, expected in {
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
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    rows_consumed = _int_metric(summary, f"{prefix}_rows_consumed")
    useful_source_count = _int_metric(summary, f"{useful_prefix}_source_count")
    useful_row_count = _int_metric(summary, f"{useful_prefix}_row_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if useful_source_count is not None and source_count != useful_source_count:
        failures.append(f"{prefix}_useful_source_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count or rows_consumed != row_count:
        failures.append(f"{prefix}_row_coverage_mismatch")
        ready = False
    if useful_row_count is not None and row_count != useful_row_count:
        failures.append(f"{prefix}_useful_row_count_mismatch")
        ready = False
    for field in REQUIRED_ROW_FIELDS:
        if row_count is not None and summary.get(
            f"{prefix}_{field}_row_ok_count"
        ) != row_count:
            failures.append(f"{prefix}_{field}_row_ok_count_mismatch")
            ready = False
        if not _is_hex_u64(summary.get(f"{prefix}_{field}_field_hash")):
            failures.append(f"{prefix}_{field}_field_hash_invalid")
            ready = False
        if summary.get(f"{prefix}_{field}_field_hash") != summary.get(
            f"{useful_prefix}_{field}_field_hash"
        ):
            failures.append(f"{prefix}_{field}_useful_field_hash_mismatch")
            ready = False
    if summary.get(f"{prefix}_useful_consumer_sha256") != summary.get(
        f"{useful_prefix}_evidence_sha256"
    ):
        failures.append(f"{prefix}_useful_consumer_sha256_mismatch")
        ready = False
    if not _same_path_label(
        summary.get(f"{prefix}_useful_consumer_json"),
        summary.get(f"{useful_prefix}_evidence_path"),
    ):
        failures.append(f"{prefix}_useful_consumer_json_mismatch")
        ready = False
    for child, useful_key in {
        "execution_sha256": "execution_sha256",
        "native_timing_sha256": "native_timing_sha256",
        "native_stub_sha256": "native_stub_sha256",
    }.items():
        if summary.get(f"{prefix}_{child}") != summary.get(f"{useful_prefix}_{useful_key}"):
            failures.append(f"{prefix}_{child}_useful_mismatch")
            ready = False
    for child, useful_key in {
        "execution_json": "execution_json",
        "native_timing_json": "native_timing_json",
        "native_stub_json": "native_stub_json",
    }.items():
        if not _same_path_label(
            summary.get(f"{prefix}_{child}"),
            summary.get(f"{useful_prefix}_{useful_key}"),
        ):
            failures.append(f"{prefix}_{child}_useful_mismatch")
            ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_useful_consumer_sha256",
        f"{prefix}_execution_sha256",
        f"{prefix}_native_timing_sha256",
        f"{prefix}_native_stub_sha256",
        f"{prefix}_chain_hash",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    for key in (
        f"{prefix}_evidence_path",
        f"{prefix}_useful_consumer_json",
        f"{prefix}_execution_json",
        f"{prefix}_native_timing_json",
        f"{prefix}_native_stub_json",
    ):
        if not isinstance(summary.get(key), str) or not summary.get(key):
            failures.append(f"{key}_missing")
            ready = False
    return ready


def _future_wna16_payloadless_useful_repeat_benchmark_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    prefix = (
        "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark"
    )
    execution_prefix = (
        "default_kernel_consumer_future_wna16_payloadless_useful_execution"
    )
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_ready": True,
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
        f"{prefix}_seed_only": False,
    }
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    for key, expected in {
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
        f"{prefix}_measurement_source": (
            "repeated_independent_native_typed_slot_timing_stub"
        ),
        f"{prefix}_next_runtime_stage": (
            "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
        ),
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    rows_consumed = _int_metric(summary, f"{prefix}_rows_consumed")
    repeat_requested = _int_metric(summary, f"{prefix}_repeat_count_requested")
    repeat_measured = _int_metric(summary, f"{prefix}_repeat_count_measured")
    execution_source_count = _int_metric(summary, f"{execution_prefix}_source_count")
    execution_row_count = _int_metric(summary, f"{execution_prefix}_row_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if execution_source_count is not None and source_count != execution_source_count:
        failures.append(f"{prefix}_execution_source_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count or rows_consumed != row_count:
        failures.append(f"{prefix}_row_coverage_mismatch")
        ready = False
    if execution_row_count is not None and row_count != execution_row_count:
        failures.append(f"{prefix}_execution_row_count_mismatch")
        ready = False
    if (
        repeat_requested is None
        or repeat_requested < 3
        or repeat_measured != repeat_requested
    ):
        failures.append(f"{prefix}_repeat_count_invalid")
        ready = False
    for field in REQUIRED_ROW_FIELDS:
        if not _is_hex_u64(summary.get(f"{prefix}_{field}_field_hash")):
            failures.append(f"{prefix}_{field}_field_hash_invalid")
            ready = False
        if summary.get(f"{prefix}_{field}_field_hash") != summary.get(
            f"{execution_prefix}_{field}_field_hash"
        ):
            failures.append(f"{prefix}_{field}_execution_field_hash_mismatch")
            ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_harness_sha256",
        f"{prefix}_native_timing_seed_sha256",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    for key in (
        f"{prefix}_evidence_path",
        f"{prefix}_harness_json",
        f"{prefix}_native_timing_seed_json",
    ):
        if not isinstance(summary.get(key), str) or not summary.get(key):
            failures.append(f"{key}_missing")
            ready = False
    if summary.get(f"{prefix}_native_timing_seed_sha256") != summary.get(
        f"{execution_prefix}_native_timing_sha256"
    ):
        failures.append(f"{prefix}_native_timing_seed_sha256_execution_mismatch")
        ready = False
    if not _same_path_label(
        summary.get(f"{prefix}_native_timing_seed_json"),
        summary.get(f"{execution_prefix}_native_timing_json"),
    ):
        failures.append(f"{prefix}_native_timing_seed_json_execution_mismatch")
        ready = False
    for key in ("min", "median", "mean", "max"):
        value = summary.get(f"{prefix}_native_stub_host_wall_ms_{key}")
        if not isinstance(value, (int, float)) or value <= 0:
            failures.append(f"{prefix}_native_stub_host_wall_ms_{key}_invalid")
            ready = False
    return ready


def _future_kernel_side_typed_path_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    all_four_failures: list[str] = []
    all_four_ready = _future_wna16_all_four_consumer_ready(
        summary,
        all_four_failures,
    )
    prefix = "default_kernel_consumer_future_wna16_kernel_side_typed_path"
    expected_values = {
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready": True,
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        f"{prefix}_evidence_passed": True,
        f"{prefix}_artifact_kind": "future_wna16_kernel_side_typed_consumer_path",
        f"{prefix}_name": "premap_future_wna16_kernel_side_typed_consumer_path_v1",
        f"{prefix}_mode": "independent_future_wna16_kernel_side_typed_consumer_path",
        f"{prefix}_source": "premap_future_wna16_typed_slot_all_four_field_consumer_v1",
        f"{prefix}_stage_type": "lab_gate",
        f"{prefix}_bench_semantics": False,
        f"{prefix}_all_four_gate_ready": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_independent_path": True,
        f"{prefix}_explicit_typed_abi_slot": True,
        f"{prefix}_future_kernel_side_checked": True,
        f"{prefix}_future_kernel_side_all_fields_read": True,
        f"{prefix}_wna16_side_checked": True,
        f"{prefix}_wna16_side_all_fields_read": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    if not all_four_ready:
        failures.append("future_wna16_all_four_consumer_not_ready")
        failures.extend(all_four_failures)
        ready = False
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    input_count = _int_metric(summary, f"{prefix}_input_json_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if input_count != source_count:
        failures.append(f"{prefix}_input_json_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_all_four_sha256",
        f"{prefix}_selected_input_manifest_sha256",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    all_four_path = summary.get(
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_path"
    )
    if not isinstance(all_four_path, str) or not all_four_path:
        failures.append(f"{prefix}_all_four_consumer_evidence_path_missing")
        ready = False
    elif summary.get(f"{prefix}_all_four_path_label") != all_four_path:
        failures.append(f"{prefix}_all_four_path_label_mismatch")
        ready = False
    all_four_sha = summary.get(
        "default_kernel_consumer_future_wna16_all_four_consumer_evidence_sha256"
    )
    if not _is_hex64(all_four_sha):
        failures.append(f"{prefix}_all_four_consumer_evidence_sha256_invalid")
        ready = False
    elif summary.get(f"{prefix}_all_four_sha256") != all_four_sha:
        failures.append(f"{prefix}_all_four_sha256_mismatch")
        ready = False
    all_four_source_count = _int_metric(
        summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_source_count",
    )
    all_four_row_count = _int_metric(
        summary,
        "default_kernel_consumer_future_wna16_all_four_consumer_row_count",
    )
    if source_count is not None and all_four_source_count != source_count:
        failures.append(f"{prefix}_all_four_source_count_mismatch")
        ready = False
    if row_count is not None and all_four_row_count != row_count:
        failures.append(f"{prefix}_all_four_row_count_mismatch")
        ready = False
    path_value = summary.get(f"{prefix}_evidence_path")
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{prefix}_evidence_path_missing")
        ready = False
    return ready


def _future_wna16_fourth_field_handoff_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    prefix = "default_kernel_consumer_future_wna16_fourth_field_handoff"
    expected_values = {
        f"{prefix}_evidence_passed": True,
        f"{prefix}_previous_gate_ready": True,
        f"{prefix}_ready": True,
        f"{prefix}_fourth_field": "descriptor_ptr",
        f"{prefix}_native_requested": True,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_expected_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_passes_current_wna16_args": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    previous_source_count = _int_metric(summary, f"{prefix}_previous_source_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if previous_source_count is None or previous_source_count < 128:
        failures.append(f"{prefix}_previous_source_count_invalid")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    else:
        for suffix in (
            "row_ok_count",
            "field_read_row_ok_count",
            "runner_row_count",
            "runner_row_ok_count",
        ):
            if _int_metric(summary, f"{prefix}_{suffix}") != row_count:
                failures.append(f"{prefix}_{suffix}_mismatch")
                ready = False
    for suffix in (
        "field_read_hash",
        "runner_hash",
        "third_field_read_hash",
        "third_field_native_hash",
    ):
        if not _is_hex_u64(summary.get(f"{prefix}_{suffix}")):
            failures.append(f"{prefix}_{suffix}_invalid")
            ready = False
    if not _is_hex64(summary.get(f"{prefix}_evidence_sha256")):
        failures.append(f"{prefix}_evidence_sha256_invalid")
        ready = False
    path_value = summary.get(f"{prefix}_evidence_path")
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{prefix}_evidence_path_missing")
        ready = False
    return ready


def _future_wna16_all_four_consumer_ready(
    summary: dict[str, Any],
    failures: list[str],
) -> bool:
    fourth_handoff_failures: list[str] = []
    fourth_handoff_ready = _future_wna16_fourth_field_handoff_ready(
        summary,
        fourth_handoff_failures,
    )
    prefix = "default_kernel_consumer_future_wna16_all_four_consumer"
    expected_values = {
        "default_kernel_consumer_future_wna16_all_four_field_consumer_ready": True,
        "default_kernel_consumer_future_wna16_all_four_field_consumer_fields_read": True,
        "default_kernel_consumer_future_wna16_all_four_field_consumer_hashes_valid": True,
        f"{prefix}_evidence_passed": True,
        f"{prefix}_artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_all_four_field_consumer"
        ),
        f"{prefix}_stage_type": "lab_gate",
        f"{prefix}_bench_semantics": False,
        f"{prefix}_native_executed": True,
        f"{prefix}_native_passed": True,
        f"{prefix}_future_kernel_side_all_fields_read": True,
        f"{prefix}_wna16_side_all_fields_read": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
    }
    ready = True
    if not fourth_handoff_ready:
        failures.append("future_wna16_fourth_field_handoff_not_ready")
        failures.extend(fourth_handoff_failures)
        ready = False
    for key, expected in expected_values.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")
            ready = False
    source_count = _int_metric(summary, f"{prefix}_source_count")
    selected_count = _int_metric(summary, f"{prefix}_selected_input_count")
    row_count = _int_metric(summary, f"{prefix}_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_row_ok_count")
    if source_count is None or source_count < 128:
        failures.append(f"{prefix}_source_count_invalid")
        ready = False
    if selected_count != source_count:
        failures.append(f"{prefix}_selected_input_count_mismatch")
        ready = False
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
        ready = False
    elif row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
        ready = False
    for key in (
        f"{prefix}_evidence_sha256",
        f"{prefix}_fourth_field_sha256",
        f"{prefix}_selected_input_manifest_sha256",
        f"{prefix}_post_native_input_manifest_sha256",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
            ready = False
    for key in (f"{prefix}_evidence_path", f"{prefix}_fourth_field_path_label"):
        value = summary.get(key)
        if not isinstance(value, str) or not value:
            failures.append(f"{key}_missing")
            ready = False
    fourth_handoff_prefix = (
        "default_kernel_consumer_future_wna16_fourth_field_handoff"
    )
    fourth_handoff_path = summary.get(f"{fourth_handoff_prefix}_evidence_path")
    fourth_handoff_sha = summary.get(f"{fourth_handoff_prefix}_evidence_sha256")
    fourth_handoff_source_count = _int_metric(
        summary, f"{fourth_handoff_prefix}_source_count"
    )
    fourth_handoff_row_count = _int_metric(
        summary, f"{fourth_handoff_prefix}_row_count"
    )
    fourth_handoff_row_ok_count = _int_metric(
        summary, f"{fourth_handoff_prefix}_row_ok_count"
    )
    if not isinstance(fourth_handoff_path, str) or not fourth_handoff_path:
        failures.append(f"{fourth_handoff_prefix}_evidence_path_missing")
        ready = False
    elif summary.get(f"{prefix}_fourth_field_path_label") != fourth_handoff_path:
        failures.append(f"{prefix}_fourth_field_path_label_mismatch")
        ready = False
    if not _is_hex64(fourth_handoff_sha):
        failures.append(f"{fourth_handoff_prefix}_evidence_sha256_invalid")
        ready = False
    elif summary.get(f"{prefix}_fourth_field_sha256") != fourth_handoff_sha:
        failures.append(f"{prefix}_fourth_field_sha256_mismatch")
        ready = False
    if fourth_handoff_source_count != source_count:
        failures.append(f"{prefix}_fourth_field_source_count_mismatch")
        ready = False
    if fourth_handoff_row_count != row_count:
        failures.append(f"{prefix}_fourth_field_row_count_mismatch")
        ready = False
    if fourth_handoff_row_ok_count != row_count:
        failures.append(f"{prefix}_fourth_field_row_ok_count_mismatch")
        ready = False
    if (
        _is_hex64(summary.get(f"{prefix}_selected_input_manifest_sha256"))
        and summary.get(f"{prefix}_post_native_input_manifest_sha256")
        != summary.get(f"{prefix}_selected_input_manifest_sha256")
    ):
        failures.append(f"{prefix}_post_native_input_manifest_sha256_mismatch")
        ready = False
    return ready


def _check_kernel_consumer_handle_summary(
    summary: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
    label: str,
    expected_field_read_path: str,
    expected_packet_chain_depth: int,
) -> None:
    if summary.get(f"{prefix}_checked") is not True:
        failures.append(f"{label}_checked_mismatch")
    if summary.get(f"{prefix}_field_read_path") != expected_field_read_path:
        failures.append(f"{label}_field_read_path_mismatch")
    if summary.get(f"{prefix}_packet_chain_depth") != int(expected_packet_chain_depth):
        failures.append(f"{label}_packet_chain_depth_mismatch")
    row_count = _int_metric(summary, f"{prefix}_summary_row_count")
    row_ok_count = _int_metric(summary, f"{prefix}_summary_row_ok_count")
    if row_count is None or row_count <= 0:
        failures.append(f"{label}_summary_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append(f"{label}_summary_row_ok_count_mismatch")
    for field in REQUIRED_ROW_FIELDS:
        key = f"{prefix}_summary_{field}_read_row_ok_count"
        if row_count is not None and _int_metric(summary, key) != row_count:
            failures.append(f"{label}_{field}_read_row_ok_count_mismatch")
    if (
        row_count is not None
        and _int_metric(summary, f"{prefix}_summary_row_metadata_read_row_ok_count")
        != row_count
    ):
        failures.append(f"{label}_row_metadata_read_row_ok_count_mismatch")
    if _int_metric(summary, f"{prefix}_summary_error_count") != 0:
        failures.append(f"{label}_summary_error_count_mismatch")
    if _int_metric(summary, f"{prefix}_summary_field_mask") != 15:
        failures.append(f"{label}_summary_field_mask_mismatch")
    for suffix in (
        "summary_row_hash_accumulator",
        "summary_field_read_hash_accumulator",
        "summary_row_metadata_hash_accumulator",
    ):
        key = f"{prefix}_{suffix}"
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")
    if summary.get(f"{prefix}_all_handle_fields_read") is not True:
        failures.append(f"{label}_all_handle_fields_read_mismatch")
    if _int_metric(summary, f"{prefix}_payload_bytes") != 0:
        failures.append(f"{label}_payload_bytes_mismatch")
    if summary.get(f"{prefix}_passed_to_kernel") is not False:
        failures.append(f"{label}_passed_to_kernel_mismatch")
    if summary.get(f"{prefix}_kernel_arg_pass_allowed") is not False:
        failures.append(f"{label}_kernel_arg_pass_allowed_mismatch")
    if summary.get(f"{prefix}_changes_kernel_launch_args") is not False:
        failures.append(f"{label}_changes_kernel_launch_args_mismatch")
    if summary.get(f"{prefix}_current_wna16_arg_compatible") is not False:
        failures.append(f"{label}_current_wna16_arg_compatible_mismatch")
    if summary.get(f"{prefix}_requires_wna16_arg_reinterpretation") is not False:
        failures.append(f"{label}_requires_wna16_arg_reinterpretation_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_checked") is not True:
        failures.append(f"{label}_single_field_handoff_checked_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_field_name") != "scale_metadata_handle":
        failures.append(f"{label}_single_field_handoff_field_name_mismatch")
    if (
        summary.get(f"{prefix}_single_field_handoff_source")
        != "native_request_summary_field_read_counts"
    ):
        failures.append(f"{label}_single_field_handoff_source_mismatch")
    if row_count is not None:
        if _int_metric(summary, f"{prefix}_single_field_handoff_row_count") != row_count:
            failures.append(f"{label}_single_field_handoff_row_count_mismatch")
        if (
            _int_metric(summary, f"{prefix}_single_field_handoff_row_ok_count")
            != row_count
        ):
            failures.append(f"{label}_single_field_handoff_row_ok_count_mismatch")
    if _int_metric(summary, f"{prefix}_single_field_handoff_error_count") != 0:
        failures.append(f"{label}_single_field_handoff_error_count_mismatch")
    if not _is_hex_u64(summary.get(f"{prefix}_single_field_handoff_hash_accumulator")):
        failures.append(f"{prefix}_single_field_handoff_hash_accumulator_invalid")
    if _int_metric(summary, f"{prefix}_single_field_handoff_payload_bytes") != 0:
        failures.append(f"{label}_single_field_handoff_payload_bytes_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_passed_to_kernel") is not False:
        failures.append(f"{label}_single_field_handoff_passed_to_kernel_mismatch")
    if summary.get(f"{prefix}_single_field_handoff_changes_kernel_launch_args") is not False:
        failures.append(
            f"{label}_single_field_handoff_changes_kernel_launch_args_mismatch"
        )
    if (
        summary.get(f"{prefix}_single_field_handoff_current_wna16_arg_compatible")
        is not False
    ):
        failures.append(
            f"{label}_single_field_handoff_current_wna16_arg_compatible_mismatch"
        )
    if (
        summary.get(
            f"{prefix}_single_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is not False
    ):
        failures.append(
            f"{label}_single_field_handoff_requires_wna16_arg_reinterpretation_mismatch"
        )
    expected_handoff_fields = [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    if summary.get(f"{prefix}_all_field_handoff_checked") is not True:
        failures.append(f"{label}_all_field_handoff_checked_mismatch")
    if summary.get(f"{prefix}_all_field_handoff_field_names") != expected_handoff_fields:
        failures.append(f"{label}_all_field_handoff_field_names_mismatch")
    if (
        summary.get(f"{prefix}_all_field_handoff_source")
        != "native_request_summary_field_read_counts"
    ):
        failures.append(f"{label}_all_field_handoff_source_mismatch")
    if row_count is not None:
        if _int_metric(summary, f"{prefix}_all_field_handoff_row_count") != row_count:
            failures.append(f"{label}_all_field_handoff_row_count_mismatch")
        if _int_metric(summary, f"{prefix}_all_field_handoff_row_ok_count") != row_count:
            failures.append(f"{label}_all_field_handoff_row_ok_count_mismatch")
        for field_name in expected_handoff_fields:
            if (
                _int_metric(
                    summary,
                    f"{prefix}_all_field_handoff_{field_name}_row_ok_count",
                )
                != row_count
            ):
                failures.append(
                    f"{label}_all_field_handoff_{field_name}_row_ok_count_mismatch"
                )
    if _int_metric(summary, f"{prefix}_all_field_handoff_error_count") != 0:
        failures.append(f"{label}_all_field_handoff_error_count_mismatch")
    if not _is_hex_u64(summary.get(f"{prefix}_all_field_handoff_hash_accumulator")):
        failures.append(f"{label}_all_field_handoff_hash_accumulator_invalid")
    if _int_metric(summary, f"{prefix}_all_field_handoff_payload_bytes") != 0:
        failures.append(f"{label}_all_field_handoff_payload_bytes_mismatch")
    if summary.get(f"{prefix}_all_field_handoff_passed_to_kernel") is not False:
        failures.append(f"{label}_all_field_handoff_passed_to_kernel_mismatch")
    if summary.get(f"{prefix}_all_field_handoff_changes_kernel_launch_args") is not False:
        failures.append(
            f"{label}_all_field_handoff_changes_kernel_launch_args_mismatch"
        )
    if (
        summary.get(f"{prefix}_all_field_handoff_current_wna16_arg_compatible")
        is not False
    ):
        failures.append(
            f"{label}_all_field_handoff_current_wna16_arg_compatible_mismatch"
        )
    if (
        summary.get(
            f"{prefix}_all_field_handoff_requires_wna16_arg_reinterpretation"
        )
        is not False
    ):
        failures.append(
            f"{label}_all_field_handoff_requires_wna16_arg_reinterpretation_mismatch"
        )


def _check_request_launch_geometry(
    summary: dict[str, Any],
    failures: list[str],
) -> None:
    row_count = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_summary_row_count",
    )
    grid_x = _int_metric(summary, "default_kernel_consumer_request_launch_grid_x")
    block_x = _int_metric(summary, "default_kernel_consumer_request_launch_block_x")
    row_offset = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_row_offset",
    )
    row_limit = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_row_limit",
    )
    rows_per_program = _int_metric(
        summary,
        "default_kernel_consumer_request_launch_rows_per_program",
    )
    if row_count is None or row_count <= 0:
        failures.append("request_launch_geometry_row_count_invalid")
        return
    if grid_x is None or grid_x <= 0:
        failures.append("request_launch_geometry_grid_x_invalid")
        return
    if block_x is None or block_x <= 0:
        failures.append("request_launch_geometry_block_x_invalid")
        return
    if row_offset != 0:
        failures.append("request_launch_geometry_row_offset_mismatch")
    if row_limit != row_count:
        failures.append("request_launch_geometry_row_limit_mismatch")
    if rows_per_program != block_x:
        failures.append("request_launch_geometry_rows_per_program_mismatch")
    launched_lanes = grid_x * block_x
    previous_grid_lanes = (grid_x - 1) * block_x
    if launched_lanes < row_count:
        failures.append("request_launch_geometry_under_covers_rows")
    if previous_grid_lanes >= row_count:
        failures.append("request_launch_geometry_overprovisioned_grid")


def _check_ready_time_decision_gate_block(
    summary: dict[str, Any],
    failures: list[str],
) -> None:
    prefix = "prefetch_lab_default_ready_time"
    current_deadline = _float_metric(summary, f"{prefix}_current_deadline_us")
    current_lookahead = _float_metric(summary, f"{prefix}_current_lookahead_us")
    first_deadline = _float_metric(
        summary,
        f"{prefix}_first_model_passing_deadline_us",
    )
    first_lookahead = _float_metric(
        summary,
        f"{prefix}_first_model_passing_lookahead_us",
    )
    required_slack = _float_metric(summary, f"{prefix}_required_lookahead_slack_us")
    required_lookahead = _float_metric(
        summary,
        f"{prefix}_required_issue_to_demand_lookahead_us",
    )
    slack_deficit = _float_metric(summary, f"{prefix}_slack_deficit_us")
    lookahead_deficit = _float_metric(summary, f"{prefix}_lookahead_deficit_us")

    for key, value in (
        ("current_deadline_us", current_deadline),
        ("current_lookahead_us", current_lookahead),
        ("first_model_passing_deadline_us", first_deadline),
        ("first_model_passing_lookahead_us", first_lookahead),
        ("required_lookahead_slack_us", required_slack),
        ("required_issue_to_demand_lookahead_us", required_lookahead),
        ("slack_deficit_us", slack_deficit),
        ("lookahead_deficit_us", lookahead_deficit),
    ):
        if value is None or value < 0.0:
            failures.append(f"{prefix}_{key}_invalid")

    if first_deadline is not None and required_slack is not None:
        if abs(first_deadline - required_slack) > 1e-6:
            failures.append(f"{prefix}_first_deadline_required_slack_mismatch")
    if first_lookahead is not None and required_lookahead is not None:
        if abs(first_lookahead - required_lookahead) > 1e-6:
            failures.append(f"{prefix}_first_lookahead_required_lookahead_mismatch")
    if (
        current_deadline is not None
        and required_slack is not None
        and slack_deficit is not None
    ):
        expected_slack_deficit = max(0.0, required_slack - current_deadline)
        if abs(slack_deficit - expected_slack_deficit) > 1e-6:
            failures.append(f"{prefix}_slack_deficit_mismatch")
    if (
        current_lookahead is not None
        and required_lookahead is not None
        and lookahead_deficit is not None
    ):
        expected_lookahead_deficit = max(0.0, required_lookahead - current_lookahead)
        if abs(lookahead_deficit - expected_lookahead_deficit) > 1e-6:
            failures.append(f"{prefix}_lookahead_deficit_mismatch")
    if slack_deficit is not None and slack_deficit <= 0.0:
        failures.append(f"{prefix}_slack_deficit_not_positive")
    if lookahead_deficit is not None and lookahead_deficit <= 0.0:
        failures.append(f"{prefix}_lookahead_deficit_not_positive")

    for key in (
        "model_slack_satisfied",
        "model_lookahead_satisfied",
        "any_model_route_satisfied",
    ):
        if summary.get(f"{prefix}_{key}") is not False:
            failures.append(f"{prefix}_{key}_mismatch")


def _check_stream_full_fetch_block(
    summary: dict[str, Any],
    failures: list[str],
) -> None:
    prefix = "prefetch_lab_default_stream"
    decision = summary.get(f"{prefix}_decision")
    full_fetch_block_reason = summary.get(f"{prefix}_full_fetch_block_reason")
    runtime_disabled_after_model_pass = (
        decision == "model_stream_ready_time_satisfied_runtime_still_disabled"
    )
    for key, expected in {
        "decision_gate_present": True,
        "decision_gate_passed": True,
        "full_fetch_runtime_allowed": False,
        "descriptor_prep_runtime_preferred": True,
        "feasibility_present": True,
        "feasibility_passed": True,
        "feasible_within_configured_token_window": True,
        "lead_token_sweep_present": True,
        "lead_token_sweep_passed": True,
        "lead_token_sweep_event_timing_mode": "token_index",
        "lead_token_sweep_token_timing_enabled": True,
    }.items():
        if summary.get(f"{prefix}_{key}") != expected:
            failures.append(f"{prefix}_{key}_mismatch")

    if runtime_disabled_after_model_pass:
        if full_fetch_block_reason != "real_payload_runtime_not_enabled":
            failures.append(f"{prefix}_full_fetch_block_reason_mismatch")
        if summary.get(f"{prefix}_metadata_premap_runtime_preferred") is not False:
            failures.append(f"{prefix}_metadata_premap_runtime_preferred_mismatch")
        if summary.get(f"{prefix}_current_runtime_satisfies_model") is not True:
            failures.append(f"{prefix}_current_runtime_satisfies_model_mismatch")
    else:
        if full_fetch_block_reason != "insufficient_stream_lookahead":
            failures.append(f"{prefix}_full_fetch_block_reason_mismatch")
        if summary.get(f"{prefix}_metadata_premap_runtime_preferred") is not True:
            failures.append(f"{prefix}_metadata_premap_runtime_preferred_mismatch")
        if summary.get(f"{prefix}_current_runtime_satisfies_model") is not False:
            failures.append(f"{prefix}_current_runtime_satisfies_model_mismatch")

    if decision not in {
        "block_full_fetch_insufficient_stream_lookahead",
        "model_stream_ready_time_satisfied_runtime_still_disabled",
    }:
        failures.append(f"{prefix}_decision_mismatch")

    current_lookahead = _float_metric(summary, f"{prefix}_current_lookahead_us")
    required_lookahead = _float_metric(summary, f"{prefix}_required_lookahead_us")
    deficit = _float_metric(summary, f"{prefix}_lookahead_deficit_us")
    first_passing_lookahead = _float_metric(
        summary,
        f"{prefix}_first_model_passing_lookahead_us",
    )
    lead_sweep_first_passing_lookahead = _float_metric(
        summary,
        f"{prefix}_lead_token_sweep_first_model_passing_lookahead_us",
    )
    decode_token_us = _float_metric(summary, f"{prefix}_lead_token_sweep_decode_token_us")
    min_required_lead = _int_metric(summary, f"{prefix}_min_required_lead_tokens")
    max_required_lead = _int_metric(summary, f"{prefix}_max_required_lead_tokens")
    max_candidate_lead = _int_metric(summary, f"{prefix}_max_candidate_lead_tokens")
    first_passing_lead = _int_metric(
        summary,
        f"{prefix}_first_model_passing_lead_tokens",
    )
    required_shifted_issue_enabled = summary.get(
        f"{prefix}_required_shifted_issue_accounting_enabled"
    )
    required_shifted_issue_lead = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_lead_tokens",
    )
    required_shifted_issue_clamped = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_clamped_issue_count",
    )
    required_shifted_issue_duplicate = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_duplicate_issue_key_count",
    )
    required_shifted_issue_unique = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_unique_issue_key_count",
    )
    required_shifted_issue_accounted = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_accounted_packet_count",
    )
    required_shifted_issue_invalid_export = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_invalid_export_count",
    )
    required_shifted_issue_row_shift_mismatch = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_row_shift_mismatch_count",
    )
    required_shifted_issue_row_clamp_mismatch = _int_metric(
        summary,
        f"{prefix}_required_shifted_issue_row_clamp_mismatch_count",
    )

    for key, value in (
        ("current_lookahead_us", current_lookahead),
        ("required_lookahead_us", required_lookahead),
        ("lookahead_deficit_us", deficit),
        ("first_model_passing_lookahead_us", first_passing_lookahead),
        (
            "lead_token_sweep_first_model_passing_lookahead_us",
            lead_sweep_first_passing_lookahead,
        ),
        ("lead_token_sweep_decode_token_us", decode_token_us),
    ):
        if value is None or value < 0.0:
            failures.append(f"{prefix}_{key}_invalid")

    if (
        current_lookahead is not None
        and required_lookahead is not None
        and deficit is not None
    ):
        expected_deficit = max(0.0, required_lookahead - current_lookahead)
        if abs(deficit - expected_deficit) > 1e-6:
            failures.append(f"{prefix}_lookahead_deficit_mismatch")
        if runtime_disabled_after_model_pass:
            if deficit != 0.0:
                failures.append(f"{prefix}_lookahead_deficit_not_zero")
        elif deficit <= 0.0:
            failures.append(f"{prefix}_lookahead_deficit_not_positive")
    if (
        required_lookahead is not None
        and first_passing_lookahead is not None
        and abs(required_lookahead - first_passing_lookahead) > 1e-6
    ):
        failures.append(f"{prefix}_required_first_passing_lookahead_mismatch")
    if (
        required_lookahead is not None
        and lead_sweep_first_passing_lookahead is not None
        and abs(required_lookahead - lead_sweep_first_passing_lookahead) > 1e-6
    ):
        failures.append(f"{prefix}_lead_sweep_lookahead_mismatch")

    for key, value in (
        ("min_required_lead_tokens", min_required_lead),
        ("max_required_lead_tokens", max_required_lead),
        ("max_candidate_lead_tokens", max_candidate_lead),
        ("first_model_passing_lead_tokens", first_passing_lead),
    ):
        if value is None or value <= 0:
            failures.append(f"{prefix}_{key}_invalid")
    if (
        min_required_lead is not None
        and max_required_lead is not None
        and min_required_lead > max_required_lead
    ):
        failures.append(f"{prefix}_required_lead_range_invalid")
    if (
        max_required_lead is not None
        and max_candidate_lead is not None
        and max_required_lead > max_candidate_lead
    ):
        failures.append(f"{prefix}_max_required_lead_above_candidate")
    if (
        first_passing_lead is not None
        and max_candidate_lead is not None
        and first_passing_lead > max_candidate_lead
    ):
        failures.append(f"{prefix}_first_passing_lead_above_candidate")
    if required_shifted_issue_enabled is not True:
        failures.append(f"{prefix}_required_shifted_issue_accounting_enabled_mismatch")
    expected_required_shifted_counts = {
        "lead_tokens": 32,
        "clamped_issue_count": 12,
        "duplicate_issue_key_count": 12,
        "unique_issue_key_count": 16,
        "accounted_packet_count": 28,
        "invalid_export_count": 0,
        "row_shift_mismatch_count": 0,
        "row_clamp_mismatch_count": 0,
    }
    observed_required_shifted_counts = {
        "lead_tokens": required_shifted_issue_lead,
        "clamped_issue_count": required_shifted_issue_clamped,
        "duplicate_issue_key_count": required_shifted_issue_duplicate,
        "unique_issue_key_count": required_shifted_issue_unique,
        "accounted_packet_count": required_shifted_issue_accounted,
        "invalid_export_count": required_shifted_issue_invalid_export,
        "row_shift_mismatch_count": required_shifted_issue_row_shift_mismatch,
        "row_clamp_mismatch_count": required_shifted_issue_row_clamp_mismatch,
    }
    for key, expected in expected_required_shifted_counts.items():
        if observed_required_shifted_counts[key] != expected:
            failures.append(f"{prefix}_required_shifted_issue_{key}_mismatch")
    if (
        first_passing_lead is not None
        and required_shifted_issue_lead is not None
        and first_passing_lead != required_shifted_issue_lead
    ):
        failures.append(f"{prefix}_required_shifted_issue_lead_mismatch")


def _check_stream_shifted_issue_replay_contract(
    summary: dict[str, Any],
    failures: list[str],
) -> None:
    prefix = "prefetch_lab_default_stream_shifted_issue_replay"
    for key in ("contract_present", "contract_passed"):
        if summary.get(f"{prefix}_{key}") is not True:
            failures.append(f"{prefix}_{key}_mismatch")

    for key in (
        "full_fetch_runtime_allowed",
        "full_fetch_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "source_full_fetch_runtime_allowed",
        "source_full_fetch_allowed",
        "source_ready_credit",
        "source_ready_before_demand_credit",
        "source_real_ready_credit_granted",
        "source_payload_transfer_enabled",
        "source_payload_deref_allowed",
        "source_kernel_arg_pass_allowed",
        "source_passed_to_kernel",
        "source_changes_kernel_launch_args",
        "uses_current_wna16_args",
        "source_uses_current_wna16_args",
        "passes_current_wna16_args",
        "current_wna16_arg_compatible",
        "requires_wna16_arg_reinterpretation",
        "source_passes_current_wna16_args",
        "source_current_wna16_arg_compatible",
        "source_requires_wna16_arg_reinterpretation",
        "wna16_benchmark_ready",
        "source_wna16_benchmark_ready",
        "measures_tpot",
        "source_measures_tpot",
        "measures_vllm_latency",
        "source_measures_vllm_latency",
    ):
        if summary.get(f"{prefix}_{key}") is not False:
            failures.append(f"{prefix}_{key}_mismatch")

    for key in ("payload_bytes", "source_payload_bytes"):
        if _int_metric(summary, f"{prefix}_{key}") != 0:
            failures.append(f"{prefix}_{key}_mismatch")

    required_lead = _int_metric(summary, f"{prefix}_contract_required_lead_tokens")
    min_schedulable = _int_metric(
        summary,
        f"{prefix}_contract_min_schedulable_packets",
    )
    issue_lead = _int_metric(summary, f"{prefix}_issue_lead_tokens")
    schedulable = _int_metric(summary, f"{prefix}_schedulable_packet_count")
    clamped = _int_metric(summary, f"{prefix}_clamped_issue_count")
    duplicates = _int_metric(summary, f"{prefix}_duplicate_issue_key_count")
    row_shift_mismatch = _int_metric(summary, f"{prefix}_row_shift_mismatch_count")
    row_clamp_mismatch = _int_metric(summary, f"{prefix}_row_clamp_mismatch_count")

    if required_lead != 32:
        failures.append(f"{prefix}_contract_required_lead_tokens_mismatch")
    if min_schedulable != 28:
        failures.append(f"{prefix}_contract_min_schedulable_packets_mismatch")
    if issue_lead != required_lead:
        failures.append(f"{prefix}_issue_lead_tokens_mismatch")
    if schedulable is None or min_schedulable is None or schedulable < min_schedulable:
        failures.append(f"{prefix}_schedulable_packet_count_below_min")
    if clamped is None or clamped <= 0:
        failures.append(f"{prefix}_clamped_issue_count_not_positive")
    if duplicates is None or duplicates <= 0:
        failures.append(f"{prefix}_duplicate_issue_key_count_not_positive")
    if row_shift_mismatch != 0:
        failures.append(f"{prefix}_row_shift_mismatch_count_mismatch")
    if row_clamp_mismatch != 0:
        failures.append(f"{prefix}_row_clamp_mismatch_count_mismatch")


def _check_stream_queue_budget(summary: dict[str, Any], failures: list[str]) -> None:
    prefix = "prefetch_lab_default_stream_queue_budget"
    for key in ("present", "passed"):
        if summary.get(f"{prefix}_{key}") is not True:
            failures.append(f"{prefix}_{key}_mismatch")
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "full_fetch_allowed",
        "full_fetch_runtime_allowed",
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
        "live_runtime_instantiated",
    ):
        if summary.get(f"{prefix}_{key}") is not False:
            failures.append(f"{prefix}_{key}_mismatch")
    if _int_metric(summary, f"{prefix}_payload_bytes") != 0:
        failures.append(f"{prefix}_payload_bytes_mismatch")
    if _int_metric(summary, f"{prefix}_issued_payload_count") != 0:
        failures.append(f"{prefix}_issued_payload_count_mismatch")
    if summary.get(f"{prefix}_event_timing_mode") != "token_index":
        failures.append(f"{prefix}_event_timing_mode_mismatch")

    cell_count = _int_metric(summary, f"{prefix}_cell_count")
    first_capacity = _int_metric(summary, f"{prefix}_first_model_passing_capacity")
    first_lead = _int_metric(
        summary,
        f"{prefix}_first_model_passing_issue_lead_tokens",
    )
    first_deadline = _float_metric(
        summary,
        f"{prefix}_first_model_passing_queue_deadline_us",
    )
    first_lookahead = _float_metric(
        summary,
        f"{prefix}_first_model_passing_lookahead_us",
    )
    first_shifted_enabled = summary.get(
        f"{prefix}_first_shifted_issue_accounting_enabled",
    )
    first_shifted_packet_count = _int_metric(
        summary,
        f"{prefix}_first_shifted_issue_accounted_packet_count",
    )
    first_shifted_unique_count = _int_metric(
        summary,
        f"{prefix}_first_shifted_issue_unique_issue_key_count",
    )
    if cell_count is None or cell_count <= 0:
        failures.append(f"{prefix}_cell_count_invalid")
    if first_capacity is None or first_capacity <= 0:
        failures.append(f"{prefix}_first_model_passing_capacity_invalid")
    if first_capacity != 4096:
        failures.append(f"{prefix}_first_model_passing_capacity_mismatch")
    if first_lead is None or first_lead <= 0:
        failures.append(f"{prefix}_first_model_passing_issue_lead_tokens_invalid")
    if first_deadline is None or first_deadline <= 0.0:
        failures.append(f"{prefix}_first_model_passing_queue_deadline_us_invalid")
    if first_deadline != 100.0:
        failures.append(f"{prefix}_first_model_passing_queue_deadline_us_mismatch")
    if first_lookahead is None or first_lookahead <= 0.0:
        failures.append(f"{prefix}_first_model_passing_lookahead_us_invalid")
    if first_lookahead is not None and first_lead is not None:
        expected_lookahead = float(first_lead) * 75_000.0
        if first_lookahead != expected_lookahead:
            failures.append(f"{prefix}_first_model_passing_lookahead_us_mismatch")

    envelope_prefix = f"{prefix}_runtime_envelope"
    if summary.get(f"{envelope_prefix}_present") is not True:
        failures.append(f"{envelope_prefix}_present_mismatch")
    if (
        summary.get(f"{envelope_prefix}_stage")
        != "payload_cache_queue_budget_runtime_envelope_lab_gate"
    ):
        failures.append(f"{envelope_prefix}_stage_mismatch")
    if (
        summary.get(f"{envelope_prefix}_status")
        != "model_queue_budget_satisfied_runtime_disabled"
    ):
        failures.append(f"{envelope_prefix}_status_mismatch")
    if (
        summary.get(f"{envelope_prefix}_execution_mode")
        != "payloadless_queue_budget_lab_gate"
    ):
        failures.append(f"{envelope_prefix}_execution_mode_mismatch")
    if summary.get(f"{envelope_prefix}_consumes_queue_budget_sweep") is not True:
        failures.append(f"{envelope_prefix}_consumes_queue_budget_sweep_mismatch")
    if _int_metric(summary, f"{envelope_prefix}_payload_bytes") != 0:
        failures.append(f"{envelope_prefix}_payload_bytes_mismatch")
    if _int_metric(summary, f"{envelope_prefix}_issued_payload_count") != 0:
        failures.append(f"{envelope_prefix}_issued_payload_count_mismatch")
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "full_fetch_allowed",
        "full_fetch_runtime_allowed",
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
        "live_runtime_instantiated",
    ):
        if summary.get(f"{envelope_prefix}_{key}") is not False:
            failures.append(f"{envelope_prefix}_{key}_mismatch")

    live_prefix = f"{prefix}_live_payload_stage"
    if summary.get(f"{live_prefix}_present") is not True:
        failures.append(f"{live_prefix}_present_mismatch")
    if summary.get(f"{live_prefix}_stage") != "payload_cache_live_payload_stage_preflight":
        failures.append(f"{live_prefix}_stage_mismatch")
    expected_envelope_status = "model_queue_budget_satisfied_runtime_disabled"
    if (
        summary.get(f"{live_prefix}_status")
        != f"blocked_by_queue_budget_runtime_envelope:{expected_envelope_status}"
    ):
        failures.append(f"{live_prefix}_status_mismatch")
    if summary.get(f"{live_prefix}_consumes_queue_budget_runtime_envelope") is not True:
        failures.append(f"{live_prefix}_consumes_queue_budget_runtime_envelope_mismatch")
    if summary.get(f"{live_prefix}_queue_budget_envelope_status") != expected_envelope_status:
        failures.append(f"{live_prefix}_queue_budget_envelope_status_mismatch")
    if _int_metric(summary, f"{live_prefix}_queue_budget_capacity_entries") != first_capacity:
        failures.append(f"{live_prefix}_queue_budget_capacity_entries_mismatch")
    if _int_metric(summary, f"{live_prefix}_queue_budget_issue_lead_tokens") != first_lead:
        failures.append(f"{live_prefix}_queue_budget_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{live_prefix}_queue_budget_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{live_prefix}_queue_budget_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{live_prefix}_queue_budget_lookahead_us") != first_lookahead:
        failures.append(f"{live_prefix}_queue_budget_lookahead_us_mismatch")
    if (
        summary.get(f"{live_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{live_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{live_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(f"{live_prefix}_shifted_issue_accounted_packet_count_mismatch")
    if (
        _int_metric(summary, f"{live_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(f"{live_prefix}_shifted_issue_unique_issue_key_count_mismatch")
    if summary.get(f"{live_prefix}_decision") != "blocked":
        failures.append(f"{live_prefix}_decision_mismatch")
    if summary.get(f"{live_prefix}_block_reason") != "live_payload_runtime_disabled":
        failures.append(f"{live_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{live_prefix}_execution_mode")
        != "payloadless_live_payload_stage_preflight"
    ):
        failures.append(f"{live_prefix}_execution_mode_mismatch")
    if _int_metric(summary, f"{live_prefix}_issued_payload_count") != 0:
        failures.append(f"{live_prefix}_issued_payload_count_mismatch")
    if _int_metric(summary, f"{live_prefix}_payload_bytes") != 0:
        failures.append(f"{live_prefix}_payload_bytes_mismatch")
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
        if summary.get(f"{live_prefix}_{key}") is not False:
            failures.append(f"{live_prefix}_{key}_mismatch")

    runtime_prefix = f"{prefix}_live_payload_runtime"
    expected_live_status = (
        f"blocked_by_queue_budget_runtime_envelope:{expected_envelope_status}"
    )
    if summary.get(f"{runtime_prefix}_present") is not True:
        failures.append(f"{runtime_prefix}_present_mismatch")
    if (
        summary.get(f"{runtime_prefix}_stage")
        != "payload_cache_live_payload_runtime_disabled_canary"
    ):
        failures.append(f"{runtime_prefix}_stage_mismatch")
    if (
        summary.get(f"{runtime_prefix}_status")
        != f"blocked_by_live_payload_stage:{expected_live_status}"
    ):
        failures.append(f"{runtime_prefix}_status_mismatch")
    if summary.get(f"{runtime_prefix}_consumes_live_payload_stage_preflight") is not True:
        failures.append(f"{runtime_prefix}_consumes_live_payload_stage_preflight_mismatch")
    if summary.get(f"{runtime_prefix}_live_payload_stage_status") != expected_live_status:
        failures.append(f"{runtime_prefix}_live_payload_stage_status_mismatch")
    if _int_metric(summary, f"{runtime_prefix}_queue_budget_capacity_entries") != first_capacity:
        failures.append(f"{runtime_prefix}_queue_budget_capacity_entries_mismatch")
    if _int_metric(summary, f"{runtime_prefix}_queue_budget_issue_lead_tokens") != first_lead:
        failures.append(f"{runtime_prefix}_queue_budget_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{runtime_prefix}_queue_budget_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{runtime_prefix}_queue_budget_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{runtime_prefix}_queue_budget_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{runtime_prefix}_queue_budget_lookahead_us_mismatch")
    if (
        summary.get(f"{runtime_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{runtime_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{runtime_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(f"{runtime_prefix}_shifted_issue_accounted_packet_count_mismatch")
    if (
        _int_metric(summary, f"{runtime_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(f"{runtime_prefix}_shifted_issue_unique_issue_key_count_mismatch")
    if summary.get(f"{runtime_prefix}_decision") != "blocked":
        failures.append(f"{runtime_prefix}_decision_mismatch")
    if summary.get(f"{runtime_prefix}_block_reason") != "live_payload_runtime_disabled":
        failures.append(f"{runtime_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{runtime_prefix}_execution_mode")
        != "payloadless_live_payload_runtime_disabled_canary"
    ):
        failures.append(f"{runtime_prefix}_execution_mode_mismatch")
    if _int_metric(summary, f"{runtime_prefix}_issued_payload_count") != 0:
        failures.append(f"{runtime_prefix}_issued_payload_count_mismatch")
    if _int_metric(summary, f"{runtime_prefix}_payload_bytes") != 0:
        failures.append(f"{runtime_prefix}_payload_bytes_mismatch")
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
        if summary.get(f"{runtime_prefix}_{key}") is not False:
            failures.append(f"{runtime_prefix}_{key}_mismatch")

    manager_prefix = f"{prefix}_manager_artifact"
    expected_runtime_status = f"blocked_by_live_payload_stage:{expected_live_status}"
    if summary.get(f"{manager_prefix}_present") is not True:
        failures.append(f"{manager_prefix}_present_mismatch")
    if summary.get(f"{manager_prefix}_stage") != "payload_cache_manager_implementation_artifact":
        failures.append(f"{manager_prefix}_stage_mismatch")
    if (
        summary.get(f"{manager_prefix}_status")
        != f"blocked_by_live_payload_runtime:{expected_runtime_status}"
    ):
        failures.append(f"{manager_prefix}_status_mismatch")
    if summary.get(f"{manager_prefix}_consumes_live_payload_runtime_canary") is not True:
        failures.append(f"{manager_prefix}_consumes_live_payload_runtime_canary_mismatch")
    if summary.get(f"{manager_prefix}_live_payload_runtime_status") != expected_runtime_status:
        failures.append(f"{manager_prefix}_live_payload_runtime_status_mismatch")
    if summary.get(f"{manager_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{manager_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{manager_prefix}_manager_contract")
        != "event_driven_queue_budget_cache_manager_v1"
    ):
        failures.append(f"{manager_prefix}_manager_contract_mismatch")
    if _int_metric(summary, f"{manager_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{manager_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{manager_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{manager_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{manager_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{manager_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{manager_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{manager_prefix}_lookahead_us_mismatch")
    if (
        summary.get(f"{manager_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{manager_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{manager_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(f"{manager_prefix}_shifted_issue_accounted_packet_count_mismatch")
    if (
        _int_metric(summary, f"{manager_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(f"{manager_prefix}_shifted_issue_unique_issue_key_count_mismatch")
    if summary.get(f"{manager_prefix}_decision") != "blocked":
        failures.append(f"{manager_prefix}_decision_mismatch")
    if (
        summary.get(f"{manager_prefix}_block_reason")
        != "implementation_artifact_default_disabled"
    ):
        failures.append(f"{manager_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{manager_prefix}_execution_mode")
        != "payload_cache_manager_implementation_artifact_disabled"
    ):
        failures.append(f"{manager_prefix}_execution_mode_mismatch")
    if _int_metric(summary, f"{manager_prefix}_issued_payload_count") != 0:
        failures.append(f"{manager_prefix}_issued_payload_count_mismatch")
    if _int_metric(summary, f"{manager_prefix}_payload_bytes") != 0:
        failures.append(f"{manager_prefix}_payload_bytes_mismatch")
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
        if summary.get(f"{manager_prefix}_{key}") is not False:
            failures.append(f"{manager_prefix}_{key}_mismatch")

    skeleton_prefix = f"{prefix}_manager_runtime_skeleton"
    expected_manager_status = f"blocked_by_live_payload_runtime:{expected_runtime_status}"
    if summary.get(f"{skeleton_prefix}_present") is not True:
        failures.append(f"{skeleton_prefix}_present_mismatch")
    if summary.get(f"{skeleton_prefix}_stage") != "payload_cache_manager_runtime_skeleton":
        failures.append(f"{skeleton_prefix}_stage_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_status")
        != f"blocked_by_manager_artifact:{expected_manager_status}"
    ):
        failures.append(f"{skeleton_prefix}_status_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_consumes_manager_implementation_artifact")
        is not True
    ):
        failures.append(
            f"{skeleton_prefix}_consumes_manager_implementation_artifact_mismatch",
        )
    if summary.get(f"{skeleton_prefix}_manager_artifact_status") != expected_manager_status:
        failures.append(f"{skeleton_prefix}_manager_artifact_status_mismatch")
    if summary.get(f"{skeleton_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{skeleton_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_manager_contract")
        != "event_driven_queue_budget_cache_manager_v1"
    ):
        failures.append(f"{skeleton_prefix}_manager_contract_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{skeleton_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{skeleton_prefix}_manager_runtime_mode_mismatch")
    if _int_metric(summary, f"{skeleton_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{skeleton_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{skeleton_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{skeleton_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{skeleton_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{skeleton_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{skeleton_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{skeleton_prefix}_lookahead_us_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{skeleton_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{skeleton_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(
            f"{skeleton_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(summary, f"{skeleton_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(
            f"{skeleton_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{skeleton_prefix}_runtime_instantiated") is not False:
        failures.append(f"{skeleton_prefix}_runtime_instantiated_mismatch")
    if summary.get(f"{skeleton_prefix}_decision") != "blocked":
        failures.append(f"{skeleton_prefix}_decision_mismatch")
    if summary.get(f"{skeleton_prefix}_block_reason") != "runtime_skeleton_default_disabled":
        failures.append(f"{skeleton_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{skeleton_prefix}_execution_mode")
        != "payload_cache_manager_runtime_skeleton_disabled"
    ):
        failures.append(f"{skeleton_prefix}_execution_mode_mismatch")
    if _int_metric(summary, f"{skeleton_prefix}_issued_payload_count") != 0:
        failures.append(f"{skeleton_prefix}_issued_payload_count_mismatch")
    if _int_metric(summary, f"{skeleton_prefix}_payload_bytes") != 0:
        failures.append(f"{skeleton_prefix}_payload_bytes_mismatch")
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
        if summary.get(f"{skeleton_prefix}_{key}") is not False:
            failures.append(f"{skeleton_prefix}_{key}_mismatch")

    snapshot_prefix = f"{prefix}_manager_runtime_snapshot"
    expected_skeleton_status = f"blocked_by_manager_artifact:{expected_manager_status}"
    expected_snapshot_status = f"blocked_by_runtime_skeleton:{expected_skeleton_status}"
    if summary.get(f"{snapshot_prefix}_present") is not True:
        failures.append(f"{snapshot_prefix}_present_mismatch")
    if (
        summary.get(f"{snapshot_prefix}_stage")
        != "payload_cache_manager_runtime_snapshot_artifact"
    ):
        failures.append(f"{snapshot_prefix}_stage_mismatch")
    if summary.get(f"{snapshot_prefix}_status") != expected_snapshot_status:
        failures.append(f"{snapshot_prefix}_status_mismatch")
    if summary.get(f"{snapshot_prefix}_consumes_runtime_skeleton") is not True:
        failures.append(f"{snapshot_prefix}_consumes_runtime_skeleton_mismatch")
    if summary.get(f"{snapshot_prefix}_runtime_skeleton_status") != expected_skeleton_status:
        failures.append(f"{snapshot_prefix}_runtime_skeleton_status_mismatch")
    if summary.get(f"{snapshot_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{snapshot_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{snapshot_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{snapshot_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{snapshot_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{snapshot_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{snapshot_prefix}_snapshot_source")
        != "ReadyTimeExpertCacheManager.empty_snapshot"
    ):
        failures.append(f"{snapshot_prefix}_snapshot_source_mismatch")
    if summary.get(f"{snapshot_prefix}_accounting_snapshot_instantiated") is not True:
        failures.append(f"{snapshot_prefix}_accounting_snapshot_instantiated_mismatch")
    if summary.get(f"{snapshot_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{snapshot_prefix}_live_runtime_instantiated_mismatch")
    if _int_metric(summary, f"{snapshot_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{snapshot_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{snapshot_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{snapshot_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{snapshot_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{snapshot_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{snapshot_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{snapshot_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{snapshot_prefix}_queue_batch_size") != 1:
        failures.append(f"{snapshot_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{snapshot_prefix}_{key}") != 0:
            failures.append(f"{snapshot_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{snapshot_prefix}_{key}") != 0.0:
            failures.append(f"{snapshot_prefix}_{key}_mismatch")
    if (
        summary.get(f"{snapshot_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{snapshot_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{snapshot_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(
            f"{snapshot_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(summary, f"{snapshot_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(
            f"{snapshot_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{snapshot_prefix}_decision") != "blocked":
        failures.append(f"{snapshot_prefix}_decision_mismatch")
    if summary.get(f"{snapshot_prefix}_block_reason") != "runtime_snapshot_default_disabled":
        failures.append(f"{snapshot_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{snapshot_prefix}_execution_mode")
        != "payload_cache_manager_runtime_snapshot_disabled"
    ):
        failures.append(f"{snapshot_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{snapshot_prefix}_{key}") is not False:
            failures.append(f"{snapshot_prefix}_{key}_mismatch")

    live_preflight_prefix = f"{prefix}_snapshot_backed_live_runtime_preflight"
    expected_live_preflight_status = (
        f"blocked_by_runtime_snapshot:{expected_snapshot_status}"
    )
    if summary.get(f"{live_preflight_prefix}_present") is not True:
        failures.append(f"{live_preflight_prefix}_present_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_stage")
        != "payload_cache_snapshot_backed_live_runtime_preflight"
    ):
        failures.append(f"{live_preflight_prefix}_stage_mismatch")
    if summary.get(f"{live_preflight_prefix}_status") != expected_live_preflight_status:
        failures.append(f"{live_preflight_prefix}_status_mismatch")
    if summary.get(f"{live_preflight_prefix}_consumes_runtime_snapshot") is not True:
        failures.append(f"{live_preflight_prefix}_consumes_runtime_snapshot_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_runtime_snapshot_status")
        != expected_snapshot_status
    ):
        failures.append(f"{live_preflight_prefix}_runtime_snapshot_status_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{live_preflight_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{live_preflight_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{live_preflight_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_snapshot_source")
        != "PayloadCacheManagerRuntimeSnapshotArtifact"
    ):
        failures.append(f"{live_preflight_prefix}_snapshot_source_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_live_runtime_preflight_instantiated")
        is not True
    ):
        failures.append(
            f"{live_preflight_prefix}_live_runtime_preflight_instantiated_mismatch",
        )
    if (
        summary.get(f"{live_preflight_prefix}_accounting_snapshot_instantiated")
        is not True
    ):
        failures.append(
            f"{live_preflight_prefix}_accounting_snapshot_instantiated_mismatch",
        )
    if summary.get(f"{live_preflight_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{live_preflight_prefix}_live_runtime_instantiated_mismatch")
    if _int_metric(summary, f"{live_preflight_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{live_preflight_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{live_preflight_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{live_preflight_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{live_preflight_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{live_preflight_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{live_preflight_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{live_preflight_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{live_preflight_prefix}_queue_batch_size") != 1:
        failures.append(f"{live_preflight_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{live_preflight_prefix}_{key}") != 0:
            failures.append(f"{live_preflight_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{live_preflight_prefix}_{key}") != 0.0:
            failures.append(f"{live_preflight_prefix}_{key}_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{live_preflight_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{live_preflight_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{live_preflight_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{live_preflight_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{live_preflight_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{live_preflight_prefix}_decision") != "blocked":
        failures.append(f"{live_preflight_prefix}_decision_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_block_reason")
        != "snapshot_backed_live_runtime_preflight_disabled"
    ):
        failures.append(f"{live_preflight_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{live_preflight_prefix}_execution_mode")
        != "payload_cache_snapshot_backed_live_runtime_preflight_disabled"
    ):
        failures.append(f"{live_preflight_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{live_preflight_prefix}_{key}") is not False:
            failures.append(f"{live_preflight_prefix}_{key}_mismatch")

    live_canary_prefix = f"{prefix}_snapshot_backed_live_runtime_canary"
    expected_live_canary_status = (
        f"blocked_by_live_runtime_preflight:{expected_live_preflight_status}"
    )
    if summary.get(f"{live_canary_prefix}_present") is not True:
        failures.append(f"{live_canary_prefix}_present_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_stage")
        != "payload_cache_snapshot_backed_live_runtime_disabled_canary"
    ):
        failures.append(f"{live_canary_prefix}_stage_mismatch")
    if summary.get(f"{live_canary_prefix}_status") != expected_live_canary_status:
        failures.append(f"{live_canary_prefix}_status_mismatch")
    if summary.get(f"{live_canary_prefix}_consumes_live_runtime_preflight") is not True:
        failures.append(
            f"{live_canary_prefix}_consumes_live_runtime_preflight_mismatch",
        )
    if (
        summary.get(f"{live_canary_prefix}_live_runtime_preflight_status")
        != expected_live_preflight_status
    ):
        failures.append(f"{live_canary_prefix}_live_runtime_preflight_status_mismatch")
    if summary.get(f"{live_canary_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{live_canary_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{live_canary_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{live_canary_prefix}_manager_runtime_mode_mismatch")
    if summary.get(f"{live_canary_prefix}_live_runtime_canary_instantiated") is not True:
        failures.append(f"{live_canary_prefix}_live_runtime_canary_instantiated_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_live_runtime_preflight_instantiated")
        is not True
    ):
        failures.append(
            f"{live_canary_prefix}_live_runtime_preflight_instantiated_mismatch",
        )
    if (
        summary.get(f"{live_canary_prefix}_accounting_snapshot_instantiated")
        is not True
    ):
        failures.append(
            f"{live_canary_prefix}_accounting_snapshot_instantiated_mismatch",
        )
    if summary.get(f"{live_canary_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{live_canary_prefix}_live_runtime_instantiated_mismatch")
    if _int_metric(summary, f"{live_canary_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{live_canary_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{live_canary_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{live_canary_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{live_canary_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{live_canary_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{live_canary_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{live_canary_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{live_canary_prefix}_queue_batch_size") != 1:
        failures.append(f"{live_canary_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{live_canary_prefix}_{key}") != 0:
            failures.append(f"{live_canary_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{live_canary_prefix}_{key}") != 0.0:
            failures.append(f"{live_canary_prefix}_{key}_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{live_canary_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{live_canary_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{live_canary_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{live_canary_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{live_canary_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{live_canary_prefix}_decision") != "blocked":
        failures.append(f"{live_canary_prefix}_decision_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_block_reason")
        != "snapshot_backed_live_runtime_canary_disabled"
    ):
        failures.append(f"{live_canary_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{live_canary_prefix}_execution_mode")
        != "payload_cache_snapshot_backed_live_runtime_canary_disabled"
    ):
        failures.append(f"{live_canary_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{live_canary_prefix}_{key}") is not False:
            failures.append(f"{live_canary_prefix}_{key}_mismatch")

    state_shape_prefix = f"{prefix}_live_runtime_state_shape"
    expected_state_shape_status = (
        f"blocked_by_live_runtime_canary:{expected_live_canary_status}"
    )
    if summary.get(f"{state_shape_prefix}_present") is not True:
        failures.append(f"{state_shape_prefix}_present_mismatch")
    if (
        summary.get(f"{state_shape_prefix}_stage")
        != "payload_cache_live_runtime_state_shape_check"
    ):
        failures.append(f"{state_shape_prefix}_stage_mismatch")
    if summary.get(f"{state_shape_prefix}_status") != expected_state_shape_status:
        failures.append(f"{state_shape_prefix}_status_mismatch")
    if summary.get(f"{state_shape_prefix}_consumes_live_runtime_canary") is not True:
        failures.append(f"{state_shape_prefix}_consumes_live_runtime_canary_mismatch")
    if summary.get(f"{state_shape_prefix}_live_runtime_canary_status") != expected_live_canary_status:
        failures.append(f"{state_shape_prefix}_live_runtime_canary_status_mismatch")
    if summary.get(f"{state_shape_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{state_shape_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{state_shape_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{state_shape_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{state_shape_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{state_shape_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{state_shape_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{state_shape_prefix}_state_shape_schema_mismatch")
    for key in (
        "live_runtime_state_shape_checked",
        "issue_queue_shape_checked",
        "demand_state_shape_checked",
        "resident_index_shape_checked",
        "queue_timing_shape_checked",
    ):
        if summary.get(f"{state_shape_prefix}_{key}") is not True:
            failures.append(f"{state_shape_prefix}_{key}_mismatch")
    if summary.get(f"{state_shape_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{state_shape_prefix}_live_runtime_instantiated_mismatch")
    if _int_metric(summary, f"{state_shape_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{state_shape_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{state_shape_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{state_shape_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{state_shape_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{state_shape_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{state_shape_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{state_shape_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{state_shape_prefix}_queue_batch_size") != 1:
        failures.append(f"{state_shape_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{state_shape_prefix}_{key}") != 0:
            failures.append(f"{state_shape_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{state_shape_prefix}_{key}") != 0.0:
            failures.append(f"{state_shape_prefix}_{key}_mismatch")
    if (
        summary.get(f"{state_shape_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{state_shape_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(
            summary,
            f"{state_shape_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{state_shape_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_shape_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{state_shape_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{state_shape_prefix}_decision") != "blocked":
        failures.append(f"{state_shape_prefix}_decision_mismatch")
    if summary.get(f"{state_shape_prefix}_block_reason") != "live_runtime_state_shape_only":
        failures.append(f"{state_shape_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{state_shape_prefix}_execution_mode")
        != "payload_cache_live_runtime_state_shape_check_disabled"
    ):
        failures.append(f"{state_shape_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{state_shape_prefix}_{key}") is not False:
            failures.append(f"{state_shape_prefix}_{key}_mismatch")

    object_prefix = f"{prefix}_live_runtime_object_preflight"
    expected_object_status = f"blocked_by_state_shape_check:{expected_state_shape_status}"
    if summary.get(f"{object_prefix}_present") is not True:
        failures.append(f"{object_prefix}_present_mismatch")
    if (
        summary.get(f"{object_prefix}_stage")
        != "payload_cache_live_runtime_object_construction_preflight"
    ):
        failures.append(f"{object_prefix}_stage_mismatch")
    if summary.get(f"{object_prefix}_status") != expected_object_status:
        failures.append(f"{object_prefix}_status_mismatch")
    if summary.get(f"{object_prefix}_consumes_state_shape_check") is not True:
        failures.append(f"{object_prefix}_consumes_state_shape_check_mismatch")
    if summary.get(f"{object_prefix}_state_shape_status") != expected_state_shape_status:
        failures.append(f"{object_prefix}_state_shape_status_mismatch")
    if summary.get(f"{object_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{object_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{object_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{object_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{object_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{object_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{object_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{object_prefix}_state_shape_schema_mismatch")
    for key in (
        "object_construction_preflight_instantiated",
        "typed_issue_queue_container_declared",
        "typed_demand_state_container_declared",
        "typed_resident_index_container_declared",
        "typed_queue_timing_container_declared",
    ):
        if summary.get(f"{object_prefix}_{key}") is not True:
            failures.append(f"{object_prefix}_{key}_mismatch")
    if summary.get(f"{object_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{object_prefix}_live_runtime_instantiated_mismatch")
    if _int_metric(summary, f"{object_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{object_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{object_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{object_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{object_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{object_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{object_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{object_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{object_prefix}_queue_batch_size") != 1:
        failures.append(f"{object_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{object_prefix}_{key}") != 0:
            failures.append(f"{object_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{object_prefix}_{key}") != 0.0:
            failures.append(f"{object_prefix}_{key}_mismatch")
    if (
        summary.get(f"{object_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{object_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{object_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(f"{object_prefix}_shifted_issue_accounted_packet_count_mismatch")
    if (
        _int_metric(summary, f"{object_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(f"{object_prefix}_shifted_issue_unique_issue_key_count_mismatch")
    if summary.get(f"{object_prefix}_decision") != "blocked":
        failures.append(f"{object_prefix}_decision_mismatch")
    if (
        summary.get(f"{object_prefix}_block_reason")
        != "live_runtime_object_construction_preflight_only"
    ):
        failures.append(f"{object_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{object_prefix}_execution_mode")
        != "payload_cache_live_runtime_object_construction_preflight_disabled"
    ):
        failures.append(f"{object_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{object_prefix}_{key}") is not False:
            failures.append(f"{object_prefix}_{key}_mismatch")

    adapter_prefix = f"{prefix}_live_runtime_object_adapter_preflight"
    expected_adapter_status = (
        f"blocked_by_object_construction_preflight:{expected_object_status}"
    )
    if summary.get(f"{adapter_prefix}_present") is not True:
        failures.append(f"{adapter_prefix}_present_mismatch")
    if (
        summary.get(f"{adapter_prefix}_stage")
        != "payload_cache_live_runtime_object_adapter_preflight"
    ):
        failures.append(f"{adapter_prefix}_stage_mismatch")
    if summary.get(f"{adapter_prefix}_status") != expected_adapter_status:
        failures.append(f"{adapter_prefix}_status_mismatch")
    if (
        summary.get(f"{adapter_prefix}_consumes_object_construction_preflight")
        is not True
    ):
        failures.append(
            f"{adapter_prefix}_consumes_object_construction_preflight_mismatch",
        )
    if summary.get(f"{adapter_prefix}_object_preflight_status") != expected_object_status:
        failures.append(f"{adapter_prefix}_object_preflight_status_mismatch")
    if summary.get(f"{adapter_prefix}_manager_backend") != "ReadyTimeExpertCacheManager":
        failures.append(f"{adapter_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{adapter_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{adapter_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{adapter_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{adapter_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{adapter_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{adapter_prefix}_state_shape_schema_mismatch")
    if (
        summary.get(f"{adapter_prefix}_runtime_adapter_schema")
        != "ready_time_payload_cache_runtime_adapter_v1"
    ):
        failures.append(f"{adapter_prefix}_runtime_adapter_schema_mismatch")
    for key in (
        "object_construction_preflight_instantiated",
        "runtime_object_adapter_declared",
        "issue_queue_adapter_bound",
        "demand_state_adapter_bound",
        "resident_index_adapter_bound",
        "queue_timing_adapter_bound",
    ):
        if summary.get(f"{adapter_prefix}_{key}") is not True:
            failures.append(f"{adapter_prefix}_{key}_mismatch")
    if summary.get(f"{adapter_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{adapter_prefix}_live_runtime_instantiated_mismatch")
    if _int_metric(summary, f"{adapter_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{adapter_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{adapter_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{adapter_prefix}_issue_lead_tokens_mismatch")
    if _float_metric(summary, f"{adapter_prefix}_queue_deadline_us") != first_deadline:
        failures.append(f"{adapter_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{adapter_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{adapter_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{adapter_prefix}_queue_batch_size") != 1:
        failures.append(f"{adapter_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{adapter_prefix}_{key}") != 0:
            failures.append(f"{adapter_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{adapter_prefix}_{key}") != 0.0:
            failures.append(f"{adapter_prefix}_{key}_mismatch")
    if (
        summary.get(f"{adapter_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{adapter_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(summary, f"{adapter_prefix}_shifted_issue_accounted_packet_count")
        != first_shifted_packet_count
    ):
        failures.append(f"{adapter_prefix}_shifted_issue_accounted_packet_count_mismatch")
    if (
        _int_metric(summary, f"{adapter_prefix}_shifted_issue_unique_issue_key_count")
        != first_shifted_unique_count
    ):
        failures.append(f"{adapter_prefix}_shifted_issue_unique_issue_key_count_mismatch")
    if summary.get(f"{adapter_prefix}_decision") != "blocked":
        failures.append(f"{adapter_prefix}_decision_mismatch")
    if (
        summary.get(f"{adapter_prefix}_block_reason")
        != "live_runtime_object_adapter_preflight_only"
    ):
        failures.append(f"{adapter_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{adapter_prefix}_execution_mode")
        != "payload_cache_live_runtime_object_adapter_preflight_disabled"
    ):
        failures.append(f"{adapter_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{adapter_prefix}_{key}") is not False:
            failures.append(f"{adapter_prefix}_{key}_mismatch")

    materialization_prefix = f"{prefix}_live_runtime_adapter_materialization_preflight"
    expected_materialization_status = (
        f"blocked_by_object_adapter_preflight:{expected_adapter_status}"
    )
    if summary.get(f"{materialization_prefix}_present") is not True:
        failures.append(f"{materialization_prefix}_present_mismatch")
    if (
        summary.get(f"{materialization_prefix}_stage")
        != "payload_cache_live_runtime_adapter_materialization_preflight"
    ):
        failures.append(f"{materialization_prefix}_stage_mismatch")
    if summary.get(f"{materialization_prefix}_status") != expected_materialization_status:
        failures.append(f"{materialization_prefix}_status_mismatch")
    if (
        summary.get(f"{materialization_prefix}_consumes_object_adapter_preflight")
        is not True
    ):
        failures.append(
            f"{materialization_prefix}_consumes_object_adapter_preflight_mismatch",
        )
    if (
        summary.get(f"{materialization_prefix}_object_adapter_status")
        != expected_adapter_status
    ):
        failures.append(f"{materialization_prefix}_object_adapter_status_mismatch")
    if (
        summary.get(f"{materialization_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{materialization_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{materialization_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{materialization_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{materialization_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{materialization_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{materialization_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{materialization_prefix}_state_shape_schema_mismatch")
    if (
        summary.get(f"{materialization_prefix}_runtime_adapter_schema")
        != "ready_time_payload_cache_runtime_adapter_v1"
    ):
        failures.append(f"{materialization_prefix}_runtime_adapter_schema_mismatch")
    for key in (
        "object_construction_preflight_instantiated",
        "adapter_materialization_preflight_instantiated",
        "runtime_object_adapter_declared",
        "issue_queue_materialization_checked",
        "demand_state_materialization_checked",
        "resident_index_materialization_checked",
        "queue_timing_materialization_checked",
    ):
        if summary.get(f"{materialization_prefix}_{key}") is not True:
            failures.append(f"{materialization_prefix}_{key}_mismatch")
    if summary.get(f"{materialization_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{materialization_prefix}_live_runtime_instantiated_mismatch")
    if (
        _int_metric(summary, f"{materialization_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{materialization_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{materialization_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{materialization_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{materialization_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{materialization_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{materialization_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{materialization_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{materialization_prefix}_queue_batch_size") != 1:
        failures.append(f"{materialization_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{materialization_prefix}_{key}") != 0:
            failures.append(f"{materialization_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{materialization_prefix}_{key}") != 0.0:
            failures.append(f"{materialization_prefix}_{key}_mismatch")
    if (
        summary.get(f"{materialization_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{materialization_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{materialization_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{materialization_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{materialization_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{materialization_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{materialization_prefix}_decision") != "blocked":
        failures.append(f"{materialization_prefix}_decision_mismatch")
    if (
        summary.get(f"{materialization_prefix}_block_reason")
        != "live_runtime_adapter_materialization_preflight_only"
    ):
        failures.append(f"{materialization_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{materialization_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_materialization_preflight_disabled"
    ):
        failures.append(f"{materialization_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{materialization_prefix}_{key}") is not False:
            failures.append(f"{materialization_prefix}_{key}_mismatch")

    state_object_prefix = f"{prefix}_live_runtime_adapter_state_object_preflight"
    expected_state_object_status = (
        f"blocked_by_adapter_materialization_preflight:"
        f"{expected_materialization_status}"
    )
    if summary.get(f"{state_object_prefix}_present") is not True:
        failures.append(f"{state_object_prefix}_present_mismatch")
    if (
        summary.get(f"{state_object_prefix}_stage")
        != "payload_cache_live_runtime_adapter_state_object_preflight"
    ):
        failures.append(f"{state_object_prefix}_stage_mismatch")
    if summary.get(f"{state_object_prefix}_status") != expected_state_object_status:
        failures.append(f"{state_object_prefix}_status_mismatch")
    if (
        summary.get(f"{state_object_prefix}_consumes_adapter_materialization_preflight")
        is not True
    ):
        failures.append(
            f"{state_object_prefix}_consumes_adapter_materialization_preflight_mismatch",
        )
    if (
        summary.get(f"{state_object_prefix}_adapter_materialization_status")
        != expected_materialization_status
    ):
        failures.append(f"{state_object_prefix}_adapter_materialization_status_mismatch")
    if (
        summary.get(f"{state_object_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{state_object_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{state_object_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{state_object_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{state_object_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{state_object_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{state_object_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{state_object_prefix}_state_shape_schema_mismatch")
    if (
        summary.get(f"{state_object_prefix}_runtime_adapter_schema")
        != "ready_time_payload_cache_runtime_adapter_v1"
    ):
        failures.append(f"{state_object_prefix}_runtime_adapter_schema_mismatch")
    if (
        summary.get(f"{state_object_prefix}_adapter_state_object_schema")
        != "ready_time_payload_cache_adapter_state_v1"
    ):
        failures.append(f"{state_object_prefix}_adapter_state_object_schema_mismatch")
    for key in (
        "adapter_materialization_preflight_instantiated",
        "adapter_state_object_declared",
        "issue_queue_state_object_declared",
        "demand_state_object_declared",
        "resident_index_state_object_declared",
        "queue_timing_state_object_declared",
    ):
        if summary.get(f"{state_object_prefix}_{key}") is not True:
            failures.append(f"{state_object_prefix}_{key}_mismatch")
    if summary.get(f"{state_object_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{state_object_prefix}_live_runtime_instantiated_mismatch")
    if (
        _int_metric(summary, f"{state_object_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{state_object_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{state_object_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{state_object_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{state_object_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{state_object_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{state_object_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{state_object_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{state_object_prefix}_queue_batch_size") != 1:
        failures.append(f"{state_object_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{state_object_prefix}_{key}") != 0:
            failures.append(f"{state_object_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{state_object_prefix}_{key}") != 0.0:
            failures.append(f"{state_object_prefix}_{key}_mismatch")
    if (
        summary.get(f"{state_object_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{state_object_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_object_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{state_object_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_object_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{state_object_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{state_object_prefix}_decision") != "blocked":
        failures.append(f"{state_object_prefix}_decision_mismatch")
    if (
        summary.get(f"{state_object_prefix}_block_reason")
        != "live_runtime_adapter_state_object_preflight_only"
    ):
        failures.append(f"{state_object_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{state_object_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_state_object_preflight_disabled"
    ):
        failures.append(f"{state_object_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{state_object_prefix}_{key}") is not False:
            failures.append(f"{state_object_prefix}_{key}_mismatch")

    state_validation_prefix = (
        f"{prefix}_live_runtime_adapter_state_validation_preflight"
    )
    expected_state_validation_status = (
        f"blocked_by_adapter_state_object_preflight:{expected_state_object_status}"
    )
    if summary.get(f"{state_validation_prefix}_present") is not True:
        failures.append(f"{state_validation_prefix}_present_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_stage")
        != "payload_cache_live_runtime_adapter_state_validation_preflight"
    ):
        failures.append(f"{state_validation_prefix}_stage_mismatch")
    if summary.get(f"{state_validation_prefix}_status") != expected_state_validation_status:
        failures.append(f"{state_validation_prefix}_status_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_consumes_adapter_state_object_preflight")
        is not True
    ):
        failures.append(
            f"{state_validation_prefix}_consumes_adapter_state_object_preflight_mismatch",
        )
    if (
        summary.get(f"{state_validation_prefix}_adapter_state_object_status")
        != expected_state_object_status
    ):
        failures.append(f"{state_validation_prefix}_adapter_state_object_status_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{state_validation_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{state_validation_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{state_validation_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{state_validation_prefix}_state_shape_schema_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_runtime_adapter_schema")
        != "ready_time_payload_cache_runtime_adapter_v1"
    ):
        failures.append(f"{state_validation_prefix}_runtime_adapter_schema_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_adapter_state_object_schema")
        != "ready_time_payload_cache_adapter_state_v1"
    ):
        failures.append(f"{state_validation_prefix}_adapter_state_object_schema_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_adapter_state_validation_schema")
        != "ready_time_payload_cache_adapter_state_validation_v1"
    ):
        failures.append(
            f"{state_validation_prefix}_adapter_state_validation_schema_mismatch",
        )
    for key in (
        "adapter_state_object_declared",
        "adapter_state_validation_preflight_instantiated",
        "issue_queue_state_object_validated",
        "demand_state_object_validated",
        "resident_index_state_object_validated",
        "queue_timing_state_object_validated",
    ):
        if summary.get(f"{state_validation_prefix}_{key}") is not True:
            failures.append(f"{state_validation_prefix}_{key}_mismatch")
    if summary.get(f"{state_validation_prefix}_live_runtime_instantiated") is not False:
        failures.append(f"{state_validation_prefix}_live_runtime_instantiated_mismatch")
    if (
        _int_metric(summary, f"{state_validation_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{state_validation_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{state_validation_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{state_validation_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{state_validation_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{state_validation_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{state_validation_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{state_validation_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{state_validation_prefix}_queue_batch_size") != 1:
        failures.append(f"{state_validation_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{state_validation_prefix}_{key}") != 0:
            failures.append(f"{state_validation_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{state_validation_prefix}_{key}") != 0.0:
            failures.append(f"{state_validation_prefix}_{key}_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{state_validation_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_validation_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{state_validation_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_validation_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{state_validation_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{state_validation_prefix}_decision") != "blocked":
        failures.append(f"{state_validation_prefix}_decision_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_block_reason")
        != "live_runtime_adapter_state_validation_preflight_only"
    ):
        failures.append(f"{state_validation_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{state_validation_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_state_validation_preflight_disabled"
    ):
        failures.append(f"{state_validation_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{state_validation_prefix}_{key}") is not False:
            failures.append(f"{state_validation_prefix}_{key}_mismatch")

    state_validation_artifact_prefix = (
        f"{prefix}_live_runtime_adapter_state_validation_artifact"
    )
    expected_state_validation_artifact_status = (
        f"blocked_by_adapter_state_validation_preflight:"
        f"{expected_state_validation_status}"
    )
    if summary.get(f"{state_validation_artifact_prefix}_present") is not True:
        failures.append(f"{state_validation_artifact_prefix}_present_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_stage")
        != "payload_cache_live_runtime_adapter_state_validation_artifact"
    ):
        failures.append(f"{state_validation_artifact_prefix}_stage_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_status")
        != expected_state_validation_artifact_status
    ):
        failures.append(f"{state_validation_artifact_prefix}_status_mismatch")
    if (
        summary.get(
            f"{state_validation_artifact_prefix}_consumes_adapter_state_validation_preflight",
        )
        is not True
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_consumes_adapter_state_validation_preflight_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_adapter_state_validation_status")
        != expected_state_validation_status
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_adapter_state_validation_status_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{state_validation_artifact_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_manager_runtime_contract_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_manager_runtime_mode_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_state_shape_schema")
        != "ready_time_issue_demand_state_shape_v1"
    ):
        failures.append(f"{state_validation_artifact_prefix}_state_shape_schema_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_runtime_adapter_schema")
        != "ready_time_payload_cache_runtime_adapter_v1"
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_runtime_adapter_schema_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_adapter_state_object_schema")
        != "ready_time_payload_cache_adapter_state_v1"
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_adapter_state_object_schema_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_adapter_state_validation_schema")
        != "ready_time_payload_cache_adapter_state_validation_v1"
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_adapter_state_validation_schema_mismatch",
        )
    if (
        summary.get(f"{state_validation_artifact_prefix}_validated_state_artifact_schema")
        != "ready_time_payload_cache_validated_adapter_state_artifact_v1"
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_validated_state_artifact_schema_mismatch",
        )
    for key in (
        "adapter_state_validation_preflight_instantiated",
        "adapter_state_validation_artifact_instantiated",
        "issue_queue_state_object_ready_for_runtime_adapter",
        "demand_state_object_ready_for_runtime_adapter",
        "resident_index_state_object_ready_for_runtime_adapter",
        "queue_timing_state_object_ready_for_runtime_adapter",
    ):
        if summary.get(f"{state_validation_artifact_prefix}_{key}") is not True:
            failures.append(f"{state_validation_artifact_prefix}_{key}_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_live_runtime_instantiated")
        is not False
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_live_runtime_instantiated_mismatch",
        )
    if (
        _int_metric(summary, f"{state_validation_artifact_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{state_validation_artifact_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{state_validation_artifact_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{state_validation_artifact_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{state_validation_artifact_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{state_validation_artifact_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{state_validation_artifact_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{state_validation_artifact_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{state_validation_artifact_prefix}_queue_batch_size") != 1:
        failures.append(f"{state_validation_artifact_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{state_validation_artifact_prefix}_{key}") != 0:
            failures.append(f"{state_validation_artifact_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{state_validation_artifact_prefix}_{key}") != 0.0:
            failures.append(f"{state_validation_artifact_prefix}_{key}_mismatch")
    if (
        summary.get(
            f"{state_validation_artifact_prefix}_shifted_issue_accounting_enabled",
        )
        is not first_shifted_enabled
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_validation_artifact_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{state_validation_artifact_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{state_validation_artifact_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{state_validation_artifact_prefix}_decision") != "blocked":
        failures.append(f"{state_validation_artifact_prefix}_decision_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_block_reason")
        != "live_runtime_adapter_state_validation_artifact_only"
    ):
        failures.append(f"{state_validation_artifact_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{state_validation_artifact_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_state_validation_artifact_disabled"
    ):
        failures.append(f"{state_validation_artifact_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{state_validation_artifact_prefix}_{key}") is not False:
            failures.append(f"{state_validation_artifact_prefix}_{key}_mismatch")

    instantiation_prefix = f"{prefix}_live_runtime_adapter_instantiation_canary"
    expected_instantiation_status = (
        f"blocked_by_state_validation_artifact:"
        f"{expected_state_validation_artifact_status}"
    )
    if summary.get(f"{instantiation_prefix}_present") is not True:
        failures.append(f"{instantiation_prefix}_present_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_stage")
        != "payload_cache_live_runtime_adapter_instantiation_canary"
    ):
        failures.append(f"{instantiation_prefix}_stage_mismatch")
    if summary.get(f"{instantiation_prefix}_status") != expected_instantiation_status:
        failures.append(f"{instantiation_prefix}_status_mismatch")
    if summary.get(f"{instantiation_prefix}_consumes_state_validation_artifact") is not True:
        failures.append(
            f"{instantiation_prefix}_consumes_state_validation_artifact_mismatch",
        )
    if (
        summary.get(f"{instantiation_prefix}_state_validation_artifact_status")
        != expected_state_validation_artifact_status
    ):
        failures.append(f"{instantiation_prefix}_state_validation_artifact_status_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{instantiation_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{instantiation_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{instantiation_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_validated_state_artifact_schema")
        != "ready_time_payload_cache_validated_adapter_state_artifact_v1"
    ):
        failures.append(f"{instantiation_prefix}_validated_state_artifact_schema_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_runtime_adapter_instantiation_schema")
        != "ready_time_payload_cache_runtime_adapter_instantiation_v1"
    ):
        failures.append(
            f"{instantiation_prefix}_runtime_adapter_instantiation_schema_mismatch",
        )
    for key in (
        "adapter_factory_declared",
        "adapter_constructor_resolved",
    ):
        if summary.get(f"{instantiation_prefix}_{key}") is not True:
            failures.append(f"{instantiation_prefix}_{key}_mismatch")
    for key in (
        "adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{instantiation_prefix}_{key}") is not False:
            failures.append(f"{instantiation_prefix}_{key}_mismatch")
    if _int_metric(summary, f"{instantiation_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{instantiation_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{instantiation_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{instantiation_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{instantiation_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{instantiation_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{instantiation_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{instantiation_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{instantiation_prefix}_queue_batch_size") != 1:
        failures.append(f"{instantiation_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{instantiation_prefix}_{key}") != 0:
            failures.append(f"{instantiation_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{instantiation_prefix}_{key}") != 0.0:
            failures.append(f"{instantiation_prefix}_{key}_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{instantiation_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{instantiation_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{instantiation_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{instantiation_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{instantiation_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{instantiation_prefix}_decision") != "blocked":
        failures.append(f"{instantiation_prefix}_decision_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_block_reason")
        != "live_runtime_adapter_instantiation_canary_only"
    ):
        failures.append(f"{instantiation_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{instantiation_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_instantiation_canary_disabled"
    ):
        failures.append(f"{instantiation_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{instantiation_prefix}_{key}") is not False:
            failures.append(f"{instantiation_prefix}_{key}_mismatch")

    constructor_binding_prefix = (
        f"{prefix}_live_runtime_adapter_constructor_binding_preflight"
    )
    expected_constructor_binding_status = (
        f"blocked_by_instantiation_canary:{expected_instantiation_status}"
    )
    if summary.get(f"{constructor_binding_prefix}_present") is not True:
        failures.append(f"{constructor_binding_prefix}_present_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_stage")
        != "payload_cache_live_runtime_adapter_constructor_binding_preflight"
    ):
        failures.append(f"{constructor_binding_prefix}_stage_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_status")
        != expected_constructor_binding_status
    ):
        failures.append(f"{constructor_binding_prefix}_status_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_consumes_instantiation_canary")
        is not True
    ):
        failures.append(
            f"{constructor_binding_prefix}_consumes_instantiation_canary_mismatch",
        )
    if (
        summary.get(f"{constructor_binding_prefix}_instantiation_canary_status")
        != expected_instantiation_status
    ):
        failures.append(
            f"{constructor_binding_prefix}_instantiation_canary_status_mismatch",
        )
    if (
        summary.get(f"{constructor_binding_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{constructor_binding_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(
            f"{constructor_binding_prefix}_manager_runtime_contract_mismatch",
        )
    if (
        summary.get(f"{constructor_binding_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{constructor_binding_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_runtime_adapter_instantiation_schema")
        != "ready_time_payload_cache_runtime_adapter_instantiation_v1"
    ):
        failures.append(
            f"{constructor_binding_prefix}_runtime_adapter_instantiation_schema_mismatch",
        )
    if (
        summary.get(f"{constructor_binding_prefix}_constructor_binding_schema")
        != "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
    ):
        failures.append(f"{constructor_binding_prefix}_constructor_binding_schema_mismatch")
    for key in (
        "adapter_factory_declared",
        "adapter_constructor_resolved",
        "constructor_inputs_bound",
        "binds_validated_state_artifact",
        "binds_queue_budget_parameters",
        "binds_shifted_issue_accounting",
    ):
        if summary.get(f"{constructor_binding_prefix}_{key}") is not True:
            failures.append(f"{constructor_binding_prefix}_{key}_mismatch")
    for key in (
        "adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{constructor_binding_prefix}_{key}") is not False:
            failures.append(f"{constructor_binding_prefix}_{key}_mismatch")
    if (
        _int_metric(summary, f"{constructor_binding_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{constructor_binding_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{constructor_binding_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{constructor_binding_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{constructor_binding_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{constructor_binding_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{constructor_binding_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{constructor_binding_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{constructor_binding_prefix}_queue_batch_size") != 1:
        failures.append(f"{constructor_binding_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{constructor_binding_prefix}_{key}") != 0:
            failures.append(f"{constructor_binding_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{constructor_binding_prefix}_{key}") != 0.0:
            failures.append(f"{constructor_binding_prefix}_{key}_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{constructor_binding_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{constructor_binding_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{constructor_binding_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{constructor_binding_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{constructor_binding_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{constructor_binding_prefix}_decision") != "blocked":
        failures.append(f"{constructor_binding_prefix}_decision_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_block_reason")
        != "live_runtime_adapter_constructor_binding_preflight_only"
    ):
        failures.append(f"{constructor_binding_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{constructor_binding_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_constructor_binding_preflight_disabled"
    ):
        failures.append(f"{constructor_binding_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{constructor_binding_prefix}_{key}") is not False:
            failures.append(f"{constructor_binding_prefix}_{key}_mismatch")

    instance_plan_prefix = (
        f"{prefix}_live_runtime_adapter_instance_construction_plan"
    )
    expected_instance_plan_status = (
        f"blocked_by_constructor_binding_preflight:"
        f"{expected_constructor_binding_status}"
    )
    if summary.get(f"{instance_plan_prefix}_present") is not True:
        failures.append(f"{instance_plan_prefix}_present_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_stage")
        != "payload_cache_live_runtime_adapter_instance_construction_plan"
    ):
        failures.append(f"{instance_plan_prefix}_stage_mismatch")
    if summary.get(f"{instance_plan_prefix}_status") != expected_instance_plan_status:
        failures.append(f"{instance_plan_prefix}_status_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_consumes_constructor_binding_preflight")
        is not True
    ):
        failures.append(
            f"{instance_plan_prefix}_consumes_constructor_binding_preflight_mismatch",
        )
    if (
        summary.get(f"{instance_plan_prefix}_constructor_binding_status")
        != expected_constructor_binding_status
    ):
        failures.append(f"{instance_plan_prefix}_constructor_binding_status_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{instance_plan_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{instance_plan_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{instance_plan_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_constructor_binding_schema")
        != "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
    ):
        failures.append(f"{instance_plan_prefix}_constructor_binding_schema_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_instance_construction_plan_schema")
        != "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
    ):
        failures.append(
            f"{instance_plan_prefix}_instance_construction_plan_schema_mismatch",
        )
    for key in (
        "constructor_inputs_bound",
        "construction_plan_sealed",
        "adapter_constructor_call_prepared",
        "adapter_instance_construction_planned",
    ):
        if summary.get(f"{instance_plan_prefix}_{key}") is not True:
            failures.append(f"{instance_plan_prefix}_{key}_mismatch")
    for key in (
        "adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{instance_plan_prefix}_{key}") is not False:
            failures.append(f"{instance_plan_prefix}_{key}_mismatch")
    if _int_metric(summary, f"{instance_plan_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{instance_plan_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{instance_plan_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{instance_plan_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{instance_plan_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{instance_plan_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{instance_plan_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{instance_plan_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{instance_plan_prefix}_queue_batch_size") != 1:
        failures.append(f"{instance_plan_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{instance_plan_prefix}_{key}") != 0:
            failures.append(f"{instance_plan_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{instance_plan_prefix}_{key}") != 0.0:
            failures.append(f"{instance_plan_prefix}_{key}_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{instance_plan_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{instance_plan_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{instance_plan_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{instance_plan_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{instance_plan_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{instance_plan_prefix}_decision") != "blocked":
        failures.append(f"{instance_plan_prefix}_decision_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_block_reason")
        != "live_runtime_adapter_instance_construction_plan_only"
    ):
        failures.append(f"{instance_plan_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{instance_plan_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_instance_construction_plan_disabled"
    ):
        failures.append(f"{instance_plan_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{instance_plan_prefix}_{key}") is not False:
            failures.append(f"{instance_plan_prefix}_{key}_mismatch")

    object_shell_prefix = f"{prefix}_live_runtime_adapter_object_shell_evidence"
    expected_object_shell_status = (
        f"blocked_by_instance_construction_plan:{expected_instance_plan_status}"
    )
    if summary.get(f"{object_shell_prefix}_present") is not True:
        failures.append(f"{object_shell_prefix}_present_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_stage")
        != "payload_cache_live_runtime_adapter_object_shell_evidence"
    ):
        failures.append(f"{object_shell_prefix}_stage_mismatch")
    if summary.get(f"{object_shell_prefix}_status") != expected_object_shell_status:
        failures.append(f"{object_shell_prefix}_status_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_consumes_instance_construction_plan")
        is not True
    ):
        failures.append(
            f"{object_shell_prefix}_consumes_instance_construction_plan_mismatch",
        )
    if (
        summary.get(f"{object_shell_prefix}_instance_construction_plan_status")
        != expected_instance_plan_status
    ):
        failures.append(f"{object_shell_prefix}_instance_construction_plan_status_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{object_shell_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{object_shell_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{object_shell_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_instance_construction_plan_schema")
        != "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
    ):
        failures.append(f"{object_shell_prefix}_instance_construction_plan_schema_mismatch")
    for key in (
        "adapter_object_shell_created",
        "disabled_adapter_shell_snapshot_created",
    ):
        if summary.get(f"{object_shell_prefix}_{key}") is not True:
            failures.append(f"{object_shell_prefix}_{key}_mismatch")
    for key in (
        "shell_enabled",
        "adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{object_shell_prefix}_{key}") is not False:
            failures.append(f"{object_shell_prefix}_{key}_mismatch")
    if _int_metric(summary, f"{object_shell_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{object_shell_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{object_shell_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{object_shell_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{object_shell_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{object_shell_prefix}_queue_deadline_us_mismatch")
    if _float_metric(summary, f"{object_shell_prefix}_lookahead_us") != first_lookahead:
        failures.append(f"{object_shell_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{object_shell_prefix}_queue_batch_size") != 1:
        failures.append(f"{object_shell_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{object_shell_prefix}_{key}") != 0:
            failures.append(f"{object_shell_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{object_shell_prefix}_{key}") != 0.0:
            failures.append(f"{object_shell_prefix}_{key}_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(f"{object_shell_prefix}_shifted_issue_accounting_enabled_mismatch")
    if (
        _int_metric(
            summary,
            f"{object_shell_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{object_shell_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{object_shell_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{object_shell_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{object_shell_prefix}_decision") != "blocked":
        failures.append(f"{object_shell_prefix}_decision_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_block_reason")
        != "live_runtime_adapter_object_shell_evidence_only"
    ):
        failures.append(f"{object_shell_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{object_shell_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_object_shell_evidence_disabled"
    ):
        failures.append(f"{object_shell_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{object_shell_prefix}_{key}") is not False:
            failures.append(f"{object_shell_prefix}_{key}_mismatch")

    operation_rejection_prefix = (
        f"{prefix}_live_runtime_adapter_operation_rejection_canary"
    )
    expected_operation_rejection_status = (
        f"blocked_by_object_shell_evidence:{expected_object_shell_status}"
    )
    if summary.get(f"{operation_rejection_prefix}_present") is not True:
        failures.append(f"{operation_rejection_prefix}_present_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_stage")
        != "payload_cache_live_runtime_adapter_operation_rejection_canary"
    ):
        failures.append(f"{operation_rejection_prefix}_stage_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_status")
        != expected_operation_rejection_status
    ):
        failures.append(f"{operation_rejection_prefix}_status_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_consumes_object_shell_evidence")
        is not True
    ):
        failures.append(
            f"{operation_rejection_prefix}_consumes_object_shell_evidence_mismatch",
        )
    if (
        summary.get(f"{operation_rejection_prefix}_object_shell_evidence_status")
        != expected_object_shell_status
    ):
        failures.append(
            f"{operation_rejection_prefix}_object_shell_evidence_status_mismatch",
        )
    if (
        summary.get(f"{operation_rejection_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{operation_rejection_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(
            f"{operation_rejection_prefix}_manager_runtime_contract_mismatch",
        )
    if (
        summary.get(f"{operation_rejection_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{operation_rejection_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_operation_rejection_schema")
        != "ready_time_payload_cache_runtime_adapter_operation_rejection_canary_v1"
    ):
        failures.append(
            f"{operation_rejection_prefix}_operation_rejection_schema_mismatch",
        )
    for key in (
        "adapter_object_shell_created",
        "operation_rejection_canary_ran",
        "issue_prefetch_rejected",
        "demand_rejected",
    ):
        if summary.get(f"{operation_rejection_prefix}_{key}") is not True:
            failures.append(f"{operation_rejection_prefix}_{key}_mismatch")
    for key in (
        "shell_enabled",
        "adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{operation_rejection_prefix}_{key}") is not False:
            failures.append(f"{operation_rejection_prefix}_{key}_mismatch")
    if (
        _int_metric(summary, f"{operation_rejection_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{operation_rejection_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{operation_rejection_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{operation_rejection_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{operation_rejection_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{operation_rejection_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{operation_rejection_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{operation_rejection_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{operation_rejection_prefix}_queue_batch_size") != 1:
        failures.append(f"{operation_rejection_prefix}_queue_batch_size_mismatch")
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
        if _int_metric(summary, f"{operation_rejection_prefix}_{key}") != 0:
            failures.append(f"{operation_rejection_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{operation_rejection_prefix}_{key}") != 0.0:
            failures.append(f"{operation_rejection_prefix}_{key}_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{operation_rejection_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{operation_rejection_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{operation_rejection_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{operation_rejection_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{operation_rejection_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{operation_rejection_prefix}_decision") != "blocked":
        failures.append(f"{operation_rejection_prefix}_decision_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_block_reason")
        != "live_runtime_adapter_operation_rejection_canary_only"
    ):
        failures.append(f"{operation_rejection_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{operation_rejection_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_operation_rejection_canary_disabled"
    ):
        failures.append(f"{operation_rejection_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{operation_rejection_prefix}_{key}") is not False:
            failures.append(f"{operation_rejection_prefix}_{key}_mismatch")

    accounting_dry_run_prefix = (
        f"{prefix}_live_runtime_adapter_accounting_dry_run_canary"
    )
    expected_accounting_dry_run_status = (
        f"blocked_by_operation_rejection_canary:{expected_operation_rejection_status}"
    )
    if summary.get(f"{accounting_dry_run_prefix}_present") is not True:
        failures.append(f"{accounting_dry_run_prefix}_present_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_stage")
        != "payload_cache_live_runtime_adapter_accounting_dry_run_canary"
    ):
        failures.append(f"{accounting_dry_run_prefix}_stage_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_status")
        != expected_accounting_dry_run_status
    ):
        failures.append(f"{accounting_dry_run_prefix}_status_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_consumes_operation_rejection_canary")
        is not True
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_consumes_operation_rejection_canary_mismatch",
        )
    if (
        summary.get(f"{accounting_dry_run_prefix}_operation_rejection_canary_status")
        != expected_operation_rejection_status
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_operation_rejection_canary_status_mismatch",
        )
    if (
        summary.get(f"{accounting_dry_run_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{accounting_dry_run_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_manager_runtime_contract_mismatch",
        )
    if (
        summary.get(f"{accounting_dry_run_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{accounting_dry_run_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_accounting_dry_run_schema")
        != "ready_time_payload_cache_runtime_adapter_accounting_dry_run_canary_v1"
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_accounting_dry_run_schema_mismatch",
        )
    for key in (
        "accounting_dry_run_adapter_created",
        "accounting_dry_run_operations_ran",
        "accounting_dry_run_enabled",
        "issue_prefetch_accepted",
        "duplicate_issue_suppressed",
        "demand_hit",
    ):
        if summary.get(f"{accounting_dry_run_prefix}_{key}") is not True:
            failures.append(f"{accounting_dry_run_prefix}_{key}_mismatch")
    for key in (
        "live_adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{accounting_dry_run_prefix}_{key}") is not False:
            failures.append(f"{accounting_dry_run_prefix}_{key}_mismatch")
    if (
        _int_metric(summary, f"{accounting_dry_run_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{accounting_dry_run_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{accounting_dry_run_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{accounting_dry_run_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{accounting_dry_run_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{accounting_dry_run_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{accounting_dry_run_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{accounting_dry_run_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{accounting_dry_run_prefix}_queue_batch_size") != 1:
        failures.append(f"{accounting_dry_run_prefix}_queue_batch_size_mismatch")
    for key, expected in {
        "resident_count": 1,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 1,
        "demand_hit_count": 1,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{accounting_dry_run_prefix}_{key}") != expected:
            failures.append(f"{accounting_dry_run_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{accounting_dry_run_prefix}_{key}") != 0.0:
            failures.append(f"{accounting_dry_run_prefix}_{key}_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{accounting_dry_run_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{accounting_dry_run_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{accounting_dry_run_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{accounting_dry_run_prefix}_decision") != "blocked":
        failures.append(f"{accounting_dry_run_prefix}_decision_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_block_reason")
        != "live_runtime_adapter_accounting_dry_run_canary_only"
    ):
        failures.append(f"{accounting_dry_run_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{accounting_dry_run_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_accounting_dry_run_canary_payloadless"
    ):
        failures.append(f"{accounting_dry_run_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{accounting_dry_run_prefix}_{key}") is not False:
            failures.append(f"{accounting_dry_run_prefix}_{key}_mismatch")

    mixed_outcome_prefix = (
        f"{prefix}_live_runtime_adapter_mixed_outcome_dry_run_canary"
    )
    expected_mixed_outcome_status = (
        f"blocked_by_accounting_dry_run_canary:{expected_accounting_dry_run_status}"
    )
    if summary.get(f"{mixed_outcome_prefix}_present") is not True:
        failures.append(f"{mixed_outcome_prefix}_present_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_stage")
        != "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary"
    ):
        failures.append(f"{mixed_outcome_prefix}_stage_mismatch")
    if summary.get(f"{mixed_outcome_prefix}_status") != expected_mixed_outcome_status:
        failures.append(f"{mixed_outcome_prefix}_status_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_consumes_accounting_dry_run_canary")
        is not True
    ):
        failures.append(
            f"{mixed_outcome_prefix}_consumes_accounting_dry_run_canary_mismatch",
        )
    if (
        summary.get(f"{mixed_outcome_prefix}_accounting_dry_run_canary_status")
        != expected_accounting_dry_run_status
    ):
        failures.append(
            f"{mixed_outcome_prefix}_accounting_dry_run_canary_status_mismatch",
        )
    if (
        summary.get(f"{mixed_outcome_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{mixed_outcome_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(f"{mixed_outcome_prefix}_manager_runtime_contract_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{mixed_outcome_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_mixed_outcome_schema")
        != "ready_time_payload_cache_runtime_adapter_mixed_outcome_dry_run_canary_v1"
    ):
        failures.append(f"{mixed_outcome_prefix}_mixed_outcome_schema_mismatch")
    for key in (
        "mixed_outcome_adapter_created",
        "mixed_outcome_operations_ran",
        "accounting_dry_run_enabled",
        "issue_prefetch_accepted",
        "duplicate_issue_suppressed",
        "prefetched_demand_hit",
        "unprefetched_demand_missed",
    ):
        if summary.get(f"{mixed_outcome_prefix}_{key}") is not True:
            failures.append(f"{mixed_outcome_prefix}_{key}_mismatch")
    for key in (
        "unprefetched_demand_hit",
        "live_adapter_instance_created",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{mixed_outcome_prefix}_{key}") is not False:
            failures.append(f"{mixed_outcome_prefix}_{key}_mismatch")
    if _int_metric(summary, f"{mixed_outcome_prefix}_capacity_entries") != first_capacity:
        failures.append(f"{mixed_outcome_prefix}_capacity_entries_mismatch")
    if _int_metric(summary, f"{mixed_outcome_prefix}_issue_lead_tokens") != first_lead:
        failures.append(f"{mixed_outcome_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{mixed_outcome_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{mixed_outcome_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{mixed_outcome_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{mixed_outcome_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{mixed_outcome_prefix}_queue_batch_size") != 1:
        failures.append(f"{mixed_outcome_prefix}_queue_batch_size_mismatch")
    for key, expected in {
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{mixed_outcome_prefix}_{key}") != expected:
            failures.append(f"{mixed_outcome_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{mixed_outcome_prefix}_{key}") != 0.0:
            failures.append(f"{mixed_outcome_prefix}_{key}_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{mixed_outcome_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{mixed_outcome_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{mixed_outcome_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{mixed_outcome_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{mixed_outcome_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{mixed_outcome_prefix}_decision") != "blocked":
        failures.append(f"{mixed_outcome_prefix}_decision_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_block_reason")
        != "live_runtime_adapter_mixed_outcome_dry_run_canary_only"
    ):
        failures.append(f"{mixed_outcome_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{mixed_outcome_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary_payloadless"
    ):
        failures.append(f"{mixed_outcome_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{mixed_outcome_prefix}_{key}") is not False:
            failures.append(f"{mixed_outcome_prefix}_{key}_mismatch")

    payloadless_instance_prefix = (
        f"{prefix}_live_runtime_adapter_payloadless_instance_canary"
    )
    expected_payloadless_instance_status = (
        f"blocked_by_mixed_outcome_dry_run_canary:{expected_mixed_outcome_status}"
    )
    if summary.get(f"{payloadless_instance_prefix}_present") is not True:
        failures.append(f"{payloadless_instance_prefix}_present_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payloadless_instance_canary"
    ):
        failures.append(f"{payloadless_instance_prefix}_stage_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_status")
        != expected_payloadless_instance_status
    ):
        failures.append(f"{payloadless_instance_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payloadless_instance_prefix}_consumes_mixed_outcome_dry_run_canary",
        )
        is not True
    ):
        failures.append(
            f"{payloadless_instance_prefix}_consumes_mixed_outcome_dry_run_canary_mismatch",
        )
    if (
        summary.get(f"{payloadless_instance_prefix}_mixed_outcome_dry_run_canary_status")
        != expected_mixed_outcome_status
    ):
        failures.append(
            f"{payloadless_instance_prefix}_mixed_outcome_dry_run_canary_status_mismatch",
        )
    if (
        summary.get(f"{payloadless_instance_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{payloadless_instance_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(
            f"{payloadless_instance_prefix}_manager_runtime_contract_mismatch",
        )
    if (
        summary.get(f"{payloadless_instance_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{payloadless_instance_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_payloadless_instance_schema")
        != "ready_time_payload_cache_runtime_adapter_payloadless_instance_canary_v1"
    ):
        failures.append(
            f"{payloadless_instance_prefix}_payloadless_instance_schema_mismatch",
        )
    for key in (
        "payloadless_live_adapter_created",
        "payloadless_live_operations_ran",
        "accounting_dry_run_enabled",
        "issue_prefetch_accepted",
        "duplicate_issue_suppressed",
        "prefetched_demand_hit",
        "unprefetched_demand_missed",
        "live_adapter_instance_created",
    ):
        if summary.get(f"{payloadless_instance_prefix}_{key}") is not True:
            failures.append(f"{payloadless_instance_prefix}_{key}_mismatch")
    for key in (
        "unprefetched_demand_hit",
        "live_runtime_instantiated",
    ):
        if summary.get(f"{payloadless_instance_prefix}_{key}") is not False:
            failures.append(f"{payloadless_instance_prefix}_{key}_mismatch")
    if (
        _int_metric(summary, f"{payloadless_instance_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{payloadless_instance_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{payloadless_instance_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{payloadless_instance_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{payloadless_instance_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payloadless_instance_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{payloadless_instance_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{payloadless_instance_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{payloadless_instance_prefix}_queue_batch_size") != 1:
        failures.append(f"{payloadless_instance_prefix}_queue_batch_size_mismatch")
    for key, expected in {
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payloadless_instance_prefix}_{key}") != expected:
            failures.append(f"{payloadless_instance_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{payloadless_instance_prefix}_{key}") != 0.0:
            failures.append(f"{payloadless_instance_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{payloadless_instance_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{payloadless_instance_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{payloadless_instance_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{payloadless_instance_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{payloadless_instance_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{payloadless_instance_prefix}_decision") != "blocked":
        failures.append(f"{payloadless_instance_prefix}_decision_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_block_reason")
        != "live_runtime_adapter_payloadless_instance_canary_only"
    ):
        failures.append(f"{payloadless_instance_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payloadless_instance_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payloadless_instance_canary_payloadless"
    ):
        failures.append(f"{payloadless_instance_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payloadless_instance_prefix}_{key}") is not False:
            failures.append(f"{payloadless_instance_prefix}_{key}_mismatch")

    payload_transfer_toggle_prefix = (
        f"{prefix}_live_runtime_adapter_payload_transfer_toggle_disabled_canary"
    )
    expected_payload_transfer_toggle_status = (
        f"blocked_by_payloadless_instance_canary:{expected_payloadless_instance_status}"
    )
    if summary.get(f"{payload_transfer_toggle_prefix}_present") is not True:
        failures.append(f"{payload_transfer_toggle_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary"
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_status")
        != expected_payload_transfer_toggle_status
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_transfer_toggle_prefix}_consumes_payloadless_instance_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_consumes_payloadless_instance_canary_mismatch",
        )
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_payloadless_instance_canary_status")
        != expected_payloadless_instance_status
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_payloadless_instance_canary_status_mismatch",
        )
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_manager_backend")
        != "ReadyTimeExpertCacheManager"
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_manager_backend_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_manager_runtime_contract")
        != "ready_time_issue_demand_skeleton_v1"
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_manager_runtime_contract_mismatch",
        )
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_manager_runtime_mode")
        != "ready_time_payload_cache_skeleton"
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_manager_runtime_mode_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_payload_transfer_toggle_schema")
        != "ready_time_payload_cache_runtime_payload_transfer_toggle_disabled_canary_v1"
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_payload_transfer_toggle_schema_mismatch",
        )
    for key in (
        "payload_transfer_toggle_created",
        "payload_issue_rejected",
        "payloadless_live_adapter_created",
        "payloadless_live_operations_ran",
        "live_adapter_instance_created",
    ):
        if summary.get(f"{payload_transfer_toggle_prefix}_{key}") is not True:
            failures.append(f"{payload_transfer_toggle_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_live_runtime_instantiated")
        is not False
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_live_runtime_instantiated_mismatch",
        )
    if (
        _int_metric(summary, f"{payload_transfer_toggle_prefix}_capacity_entries")
        != first_capacity
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_capacity_entries_mismatch")
    if (
        _int_metric(summary, f"{payload_transfer_toggle_prefix}_issue_lead_tokens")
        != first_lead
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_issue_lead_tokens_mismatch")
    if (
        _float_metric(summary, f"{payload_transfer_toggle_prefix}_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_queue_deadline_us_mismatch")
    if (
        _float_metric(summary, f"{payload_transfer_toggle_prefix}_lookahead_us")
        != first_lookahead
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_lookahead_us_mismatch")
    if _int_metric(summary, f"{payload_transfer_toggle_prefix}_queue_batch_size") != 1:
        failures.append(f"{payload_transfer_toggle_prefix}_queue_batch_size_mismatch")
    for key, expected in {
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_transfer_toggle_prefix}_{key}") != expected:
            failures.append(f"{payload_transfer_toggle_prefix}_{key}_mismatch")
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        if _float_metric(summary, f"{payload_transfer_toggle_prefix}_{key}") != 0.0:
            failures.append(f"{payload_transfer_toggle_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_shifted_issue_accounting_enabled")
        is not first_shifted_enabled
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_shifted_issue_accounting_enabled_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{payload_transfer_toggle_prefix}_shifted_issue_accounted_packet_count",
        )
        != first_shifted_packet_count
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_shifted_issue_accounted_packet_count_mismatch",
        )
    if (
        _int_metric(
            summary,
            f"{payload_transfer_toggle_prefix}_shifted_issue_unique_issue_key_count",
        )
        != first_shifted_unique_count
    ):
        failures.append(
            f"{payload_transfer_toggle_prefix}_shifted_issue_unique_issue_key_count_mismatch",
        )
    if summary.get(f"{payload_transfer_toggle_prefix}_decision") != "blocked":
        failures.append(f"{payload_transfer_toggle_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_block_reason")
        != "live_runtime_adapter_payload_transfer_toggle_disabled_canary_only"
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_transfer_toggle_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary_payloadless"
    ):
        failures.append(f"{payload_transfer_toggle_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_transfer_toggle_prefix}_{key}") is not False:
            failures.append(f"{payload_transfer_toggle_prefix}_{key}_mismatch")

    payload_issue_request_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_request_blocked_canary"
    )
    expected_payload_issue_request_status = (
        "blocked_by_payload_transfer_toggle_disabled_canary:"
        f"{expected_payload_transfer_toggle_status}"
    )
    if summary.get(f"{payload_issue_request_prefix}_present") is not True:
        failures.append(f"{payload_issue_request_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_request_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary"
    ):
        failures.append(f"{payload_issue_request_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_request_prefix}_status")
        != expected_payload_issue_request_status
    ):
        failures.append(f"{payload_issue_request_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_request_prefix}_consumes_payload_transfer_toggle_disabled_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_request_prefix}_consumes_payload_transfer_toggle_disabled_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_request_prefix}_payload_transfer_toggle_disabled_canary_status",
        )
        != expected_payload_transfer_toggle_status
    ):
        failures.append(
            f"{payload_issue_request_prefix}_payload_transfer_toggle_disabled_canary_status_mismatch",
        )
    if (
        summary.get(f"{payload_issue_request_prefix}_payload_issue_request_schema")
        != "payload_cache_runtime_payload_issue_request_v1"
    ):
        failures.append(
            f"{payload_issue_request_prefix}_payload_issue_request_schema_mismatch",
        )
    for key in ("payload_issue_request_created", "payload_issue_rejected"):
        if summary.get(f"{payload_issue_request_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_request_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_request_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_request_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_request_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_request_prefix}_request_source_mismatch")
    if (
        _float_metric(summary, f"{payload_issue_request_prefix}_source_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payload_issue_request_prefix}_source_queue_deadline_us_mismatch")
    if summary.get(f"{payload_issue_request_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_request_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_request_prefix}_block_reason")
        != "live_runtime_adapter_payload_issue_request_blocked_canary_only"
    ):
        failures.append(f"{payload_issue_request_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_request_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary_payloadless"
    ):
        failures.append(f"{payload_issue_request_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_request_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_request_prefix}_{key}_mismatch")

    payload_issue_plan_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_plan_dry_run"
    )
    expected_payload_issue_plan_status = (
        "blocked_by_payload_issue_request_blocked_canary:"
        f"{expected_payload_issue_request_status}"
    )
    if summary.get(f"{payload_issue_plan_prefix}_present") is not True:
        failures.append(f"{payload_issue_plan_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_plan_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_plan_dry_run"
    ):
        failures.append(f"{payload_issue_plan_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_plan_prefix}_status")
        != expected_payload_issue_plan_status
    ):
        failures.append(f"{payload_issue_plan_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_plan_prefix}_consumes_payload_issue_request_blocked_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_plan_prefix}_consumes_payload_issue_request_blocked_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_plan_prefix}_payload_issue_request_blocked_canary_status",
        )
        != expected_payload_issue_request_status
    ):
        failures.append(
            f"{payload_issue_plan_prefix}_payload_issue_request_blocked_canary_status_mismatch",
        )
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_plan_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_plan_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_plan_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_plan_prefix}_request_source_mismatch")
    if (
        _float_metric(summary, f"{payload_issue_plan_prefix}_source_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payload_issue_plan_prefix}_source_queue_deadline_us_mismatch")
    if summary.get(f"{payload_issue_plan_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_plan_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_plan_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_plan_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_plan_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_plan_dry_run"
    ):
        failures.append(f"{payload_issue_plan_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_plan_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_plan_prefix}_{key}_mismatch")

    payload_issue_executor_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_executor_dry_run"
    )
    expected_payload_issue_executor_status = (
        "blocked_by_payload_issue_plan_dry_run:"
        f"{expected_payload_issue_plan_status}"
    )
    if summary.get(f"{payload_issue_executor_prefix}_present") is not True:
        failures.append(f"{payload_issue_executor_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_executor_dry_run"
    ):
        failures.append(f"{payload_issue_executor_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_status")
        != expected_payload_issue_executor_status
    ):
        failures.append(f"{payload_issue_executor_prefix}_status_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_consumes_payload_issue_plan_dry_run")
        is not True
    ):
        failures.append(
            f"{payload_issue_executor_prefix}_consumes_payload_issue_plan_dry_run_mismatch",
        )
    if (
        summary.get(f"{payload_issue_executor_prefix}_payload_issue_plan_status")
        != expected_payload_issue_plan_status
    ):
        failures.append(f"{payload_issue_executor_prefix}_payload_issue_plan_status_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_payload_issue_executor_schema")
        != "payload_cache_runtime_payload_issue_executor_v1"
    ):
        failures.append(f"{payload_issue_executor_prefix}_payload_issue_executor_schema_mismatch")
    for key in ("payload_issue_executor_created", "payload_issue_plan_consumed"):
        if summary.get(f"{payload_issue_executor_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_executor_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_executor_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_executor_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_executor_prefix}_request_source_mismatch")
    if (
        _float_metric(summary, f"{payload_issue_executor_prefix}_source_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payload_issue_executor_prefix}_source_queue_deadline_us_mismatch")
    if summary.get(f"{payload_issue_executor_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_executor_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_executor_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_executor_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_executor_dry_run"
    ):
        failures.append(f"{payload_issue_executor_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_executor_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_executor_prefix}_{key}_mismatch")

    payload_issue_queue_entry_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_queue_entry_dry_run"
    )
    expected_payload_issue_queue_entry_status = (
        "blocked_by_payload_issue_executor_dry_run:"
        f"{expected_payload_issue_executor_status}"
    )
    if summary.get(f"{payload_issue_queue_entry_prefix}_present") is not True:
        failures.append(f"{payload_issue_queue_entry_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run"
    ):
        failures.append(f"{payload_issue_queue_entry_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_status")
        != expected_payload_issue_queue_entry_status
    ):
        failures.append(f"{payload_issue_queue_entry_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_queue_entry_prefix}_consumes_payload_issue_executor_dry_run",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_queue_entry_prefix}_consumes_payload_issue_executor_dry_run_mismatch",
        )
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_payload_issue_executor_status")
        != expected_payload_issue_executor_status
    ):
        failures.append(
            f"{payload_issue_queue_entry_prefix}_payload_issue_executor_status_mismatch",
        )
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_payload_issue_queue_entry_schema")
        != "payload_cache_runtime_payload_issue_queue_entry_v1"
    ):
        failures.append(
            f"{payload_issue_queue_entry_prefix}_payload_issue_queue_entry_schema_mismatch",
        )
    for key in (
        "payload_issue_queue_entry_created",
        "payload_issue_executor_consumed",
        "queue_entry_shape_checked",
    ):
        if summary.get(f"{payload_issue_queue_entry_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_queue_entry_prefix}_{key}_mismatch")
    for key in ("queue_entry_enqueued", "queue_submit_allowed"):
        if summary.get(f"{payload_issue_queue_entry_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_queue_entry_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_queue_entry_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_queue_entry_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_queue_entry_prefix}_request_source_mismatch")
    if (
        _float_metric(summary, f"{payload_issue_queue_entry_prefix}_source_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payload_issue_queue_entry_prefix}_source_queue_deadline_us_mismatch")
    if summary.get(f"{payload_issue_queue_entry_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_queue_entry_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_queue_entry_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_queue_entry_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run"
    ):
        failures.append(f"{payload_issue_queue_entry_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_queue_entry_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_queue_entry_prefix}_{key}_mismatch")

    payload_issue_queue_submit_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_queue_submit_blocked_canary"
    )
    expected_payload_issue_queue_submit_status = (
        "blocked_by_payload_issue_queue_entry_dry_run:"
        f"{expected_payload_issue_queue_entry_status}"
    )
    if summary.get(f"{payload_issue_queue_submit_prefix}_present") is not True:
        failures.append(f"{payload_issue_queue_submit_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary"
    ):
        failures.append(f"{payload_issue_queue_submit_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_status")
        != expected_payload_issue_queue_submit_status
    ):
        failures.append(f"{payload_issue_queue_submit_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_queue_submit_prefix}_consumes_payload_issue_queue_entry_dry_run",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_queue_submit_prefix}_consumes_payload_issue_queue_entry_dry_run_mismatch",
        )
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_payload_issue_queue_entry_status")
        != expected_payload_issue_queue_entry_status
    ):
        failures.append(
            f"{payload_issue_queue_submit_prefix}_payload_issue_queue_entry_status_mismatch",
        )
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_payload_issue_queue_submit_schema")
        != "payload_cache_runtime_payload_issue_queue_submit_v1"
    ):
        failures.append(
            f"{payload_issue_queue_submit_prefix}_payload_issue_queue_submit_schema_mismatch",
        )
    for key in (
        "payload_issue_queue_submit_canary_created",
        "payload_issue_queue_entry_consumed",
        "queue_submit_checked",
        "queue_submit_rejected",
    ):
        if summary.get(f"{payload_issue_queue_submit_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_queue_submit_prefix}_{key}_mismatch")
    for key in ("queue_submit_allowed", "queue_entry_enqueued"):
        if summary.get(f"{payload_issue_queue_submit_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_queue_submit_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_queue_submit_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_queue_submit_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_queue_submit_prefix}_request_source_mismatch")
    if (
        _float_metric(summary, f"{payload_issue_queue_submit_prefix}_source_queue_deadline_us")
        != first_deadline
    ):
        failures.append(f"{payload_issue_queue_submit_prefix}_source_queue_deadline_us_mismatch")
    if summary.get(f"{payload_issue_queue_submit_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_queue_submit_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_queue_submit_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_queue_submit_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary"
    ):
        failures.append(f"{payload_issue_queue_submit_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_queue_submit_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_queue_submit_prefix}_{key}_mismatch")

    payload_issue_inflight_admission_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary"
    )
    expected_payload_issue_inflight_admission_status = (
        "blocked_by_payload_issue_queue_submit_blocked_canary:"
        f"{expected_payload_issue_queue_submit_status}"
    )
    if summary.get(f"{payload_issue_inflight_admission_prefix}_present") is not True:
        failures.append(f"{payload_issue_inflight_admission_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_inflight_admission_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary"
    ):
        failures.append(f"{payload_issue_inflight_admission_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_inflight_admission_prefix}_status")
        != expected_payload_issue_inflight_admission_status
    ):
        failures.append(f"{payload_issue_inflight_admission_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_inflight_admission_prefix}_consumes_payload_issue_queue_submit_blocked_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_inflight_admission_prefix}_consumes_payload_issue_queue_submit_blocked_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_inflight_admission_prefix}_payload_issue_queue_submit_status",
        )
        != expected_payload_issue_queue_submit_status
    ):
        failures.append(
            f"{payload_issue_inflight_admission_prefix}_payload_issue_queue_submit_status_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_inflight_admission_prefix}_payload_issue_inflight_admission_schema",
        )
        != "payload_cache_runtime_payload_issue_inflight_admission_v1"
    ):
        failures.append(
            f"{payload_issue_inflight_admission_prefix}_payload_issue_inflight_admission_schema_mismatch",
        )
    for key in (
        "payload_issue_inflight_admission_canary_created",
        "payload_issue_queue_submit_consumed",
        "inflight_admission_checked",
        "inflight_admission_rejected",
    ):
        if summary.get(f"{payload_issue_inflight_admission_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_inflight_admission_prefix}_{key}_mismatch")
    for key in ("inflight_admission_allowed", "inflight_queue_enqueued"):
        if summary.get(f"{payload_issue_inflight_admission_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_inflight_admission_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "inflight_issue_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_inflight_admission_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_inflight_admission_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_inflight_admission_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_inflight_admission_prefix}_request_source_mismatch")
    if (
        _float_metric(
            summary,
            f"{payload_issue_inflight_admission_prefix}_source_queue_deadline_us",
        )
        != first_deadline
    ):
        failures.append(
            f"{payload_issue_inflight_admission_prefix}_source_queue_deadline_us_mismatch",
        )
    if summary.get(f"{payload_issue_inflight_admission_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_inflight_admission_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_inflight_admission_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_inflight_admission_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_inflight_admission_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary"
    ):
        failures.append(f"{payload_issue_inflight_admission_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_inflight_admission_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_inflight_admission_prefix}_{key}_mismatch")

    payload_issue_scheduler_dispatch_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary"
    )
    expected_payload_issue_scheduler_dispatch_status = (
        "blocked_by_payload_issue_inflight_admission_blocked_canary:"
        f"{expected_payload_issue_inflight_admission_status}"
    )
    if summary.get(f"{payload_issue_scheduler_dispatch_prefix}_present") is not True:
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_scheduler_dispatch_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary"
    ):
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_scheduler_dispatch_prefix}_status")
        != expected_payload_issue_scheduler_dispatch_status
    ):
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_scheduler_dispatch_prefix}_consumes_payload_issue_inflight_admission_blocked_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_scheduler_dispatch_prefix}_consumes_payload_issue_inflight_admission_blocked_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_inflight_admission_status",
        )
        != expected_payload_issue_inflight_admission_status
    ):
        failures.append(
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_inflight_admission_status_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_scheduler_dispatch_schema",
        )
        != "payload_cache_runtime_payload_issue_scheduler_dispatch_v1"
    ):
        failures.append(
            f"{payload_issue_scheduler_dispatch_prefix}_payload_issue_scheduler_dispatch_schema_mismatch",
        )
    for key in (
        "payload_issue_scheduler_dispatch_canary_created",
        "payload_issue_inflight_admission_consumed",
        "scheduler_dispatch_checked",
        "scheduler_dispatch_rejected",
    ):
        if summary.get(f"{payload_issue_scheduler_dispatch_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_scheduler_dispatch_prefix}_{key}_mismatch")
    for key in ("scheduler_dispatch_allowed", "scheduler_dispatch_enqueued"):
        if summary.get(f"{payload_issue_scheduler_dispatch_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_scheduler_dispatch_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "inflight_issue_count": 0,
        "dispatched_issue_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_scheduler_dispatch_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_scheduler_dispatch_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_scheduler_dispatch_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_request_source_mismatch")
    if (
        _float_metric(
            summary,
            f"{payload_issue_scheduler_dispatch_prefix}_source_queue_deadline_us",
        )
        != first_deadline
    ):
        failures.append(
            f"{payload_issue_scheduler_dispatch_prefix}_source_queue_deadline_us_mismatch",
        )
    if summary.get(f"{payload_issue_scheduler_dispatch_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_scheduler_dispatch_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_scheduler_dispatch_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary"
    ):
        failures.append(f"{payload_issue_scheduler_dispatch_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_scheduler_dispatch_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_scheduler_dispatch_prefix}_{key}_mismatch")

    payload_issue_command_packet_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_command_packet_dry_run"
    )
    expected_payload_issue_command_packet_status = (
        "blocked_by_payload_issue_scheduler_dispatch_blocked_canary:"
        f"{expected_payload_issue_scheduler_dispatch_status}"
    )
    if summary.get(f"{payload_issue_command_packet_prefix}_present") is not True:
        failures.append(f"{payload_issue_command_packet_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_command_packet_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run"
    ):
        failures.append(f"{payload_issue_command_packet_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_command_packet_prefix}_status")
        != expected_payload_issue_command_packet_status
    ):
        failures.append(f"{payload_issue_command_packet_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_command_packet_prefix}_consumes_payload_issue_scheduler_dispatch_blocked_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_command_packet_prefix}_consumes_payload_issue_scheduler_dispatch_blocked_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_command_packet_prefix}_payload_issue_scheduler_dispatch_status",
        )
        != expected_payload_issue_scheduler_dispatch_status
    ):
        failures.append(
            f"{payload_issue_command_packet_prefix}_payload_issue_scheduler_dispatch_status_mismatch",
        )
    if (
        summary.get(f"{payload_issue_command_packet_prefix}_payload_issue_command_packet_schema")
        != "payload_cache_runtime_payload_issue_command_packet_v1"
    ):
        failures.append(
            f"{payload_issue_command_packet_prefix}_payload_issue_command_packet_schema_mismatch",
        )
    for key in (
        "payload_issue_command_packet_created",
        "payload_issue_scheduler_dispatch_consumed",
        "command_packet_shape_checked",
    ):
        if summary.get(f"{payload_issue_command_packet_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_command_packet_prefix}_{key}_mismatch")
    for key in ("command_packet_submitted", "command_packet_executed"):
        if summary.get(f"{payload_issue_command_packet_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_command_packet_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "inflight_issue_count": 0,
        "dispatched_issue_count": 0,
        "command_packet_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_command_packet_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_command_packet_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_command_packet_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_command_packet_prefix}_request_source_mismatch")
    if (
        _float_metric(
            summary,
            f"{payload_issue_command_packet_prefix}_source_queue_deadline_us",
        )
        != first_deadline
    ):
        failures.append(
            f"{payload_issue_command_packet_prefix}_source_queue_deadline_us_mismatch",
        )
    if summary.get(f"{payload_issue_command_packet_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_command_packet_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_command_packet_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_command_packet_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_command_packet_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run"
    ):
        failures.append(f"{payload_issue_command_packet_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_command_packet_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_command_packet_prefix}_{key}_mismatch")

    payload_issue_transport_enqueue_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary"
    )
    expected_payload_issue_transport_enqueue_status = (
        "blocked_by_payload_issue_command_packet_dry_run:"
        f"{expected_payload_issue_command_packet_status}"
    )
    if summary.get(f"{payload_issue_transport_enqueue_prefix}_present") is not True:
        failures.append(f"{payload_issue_transport_enqueue_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_transport_enqueue_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary"
    ):
        failures.append(f"{payload_issue_transport_enqueue_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_transport_enqueue_prefix}_status")
        != expected_payload_issue_transport_enqueue_status
    ):
        failures.append(f"{payload_issue_transport_enqueue_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_transport_enqueue_prefix}_consumes_payload_issue_command_packet_dry_run",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_transport_enqueue_prefix}_consumes_payload_issue_command_packet_dry_run_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_command_packet_status",
        )
        != expected_payload_issue_command_packet_status
    ):
        failures.append(
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_command_packet_status_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_transport_enqueue_schema",
        )
        != "payload_cache_runtime_payload_issue_transport_enqueue_v1"
    ):
        failures.append(
            f"{payload_issue_transport_enqueue_prefix}_payload_issue_transport_enqueue_schema_mismatch",
        )
    for key in (
        "payload_issue_transport_enqueue_canary_created",
        "payload_issue_command_packet_consumed",
        "transport_enqueue_checked",
        "transport_enqueue_rejected",
    ):
        if summary.get(f"{payload_issue_transport_enqueue_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_transport_enqueue_prefix}_{key}_mismatch")
    for key in ("transport_enqueue_allowed", "transport_work_enqueued"):
        if summary.get(f"{payload_issue_transport_enqueue_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_transport_enqueue_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "inflight_issue_count": 0,
        "dispatched_issue_count": 0,
        "command_packet_count": 0,
        "transport_work_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_transport_enqueue_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_transport_enqueue_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_transport_enqueue_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_transport_enqueue_prefix}_request_source_mismatch")
    if (
        _float_metric(
            summary,
            f"{payload_issue_transport_enqueue_prefix}_source_queue_deadline_us",
        )
        != first_deadline
    ):
        failures.append(
            f"{payload_issue_transport_enqueue_prefix}_source_queue_deadline_us_mismatch",
        )
    if summary.get(f"{payload_issue_transport_enqueue_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_transport_enqueue_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_transport_enqueue_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_transport_enqueue_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_transport_enqueue_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary"
    ):
        failures.append(f"{payload_issue_transport_enqueue_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_transport_enqueue_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_transport_enqueue_prefix}_{key}_mismatch")

    payload_issue_transport_worker_dispatch_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary"
    )
    expected_payload_issue_transport_worker_dispatch_status = (
        "blocked_by_payload_issue_transport_enqueue_blocked_canary:"
        f"{expected_payload_issue_transport_enqueue_status}"
    )
    if summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_present") is not True:
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary"
    ):
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_status")
        != expected_payload_issue_transport_worker_dispatch_status
    ):
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_transport_worker_dispatch_prefix}_consumes_payload_issue_transport_enqueue_blocked_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_transport_worker_dispatch_prefix}_consumes_payload_issue_transport_enqueue_blocked_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_enqueue_status",
        )
        != expected_payload_issue_transport_enqueue_status
    ):
        failures.append(
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_enqueue_status_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_worker_dispatch_schema",
        )
        != "payload_cache_runtime_payload_issue_transport_worker_dispatch_v1"
    ):
        failures.append(
            f"{payload_issue_transport_worker_dispatch_prefix}_payload_issue_transport_worker_dispatch_schema_mismatch",
        )
    for key in (
        "payload_issue_transport_worker_dispatch_canary_created",
        "payload_issue_transport_enqueue_consumed",
        "transport_worker_dispatch_checked",
        "transport_worker_dispatch_rejected",
    ):
        if summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_{key}_mismatch")
    for key in ("transport_worker_dispatch_allowed", "transport_worker_dispatched"):
        if summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "inflight_issue_count": 0,
        "dispatched_issue_count": 0,
        "command_packet_count": 0,
        "transport_work_count": 0,
        "transport_worker_dispatch_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if (
            _int_metric(summary, f"{payload_issue_transport_worker_dispatch_prefix}_{key}")
            != expected
        ):
            failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_request_source_mismatch")
    if (
        _float_metric(
            summary,
            f"{payload_issue_transport_worker_dispatch_prefix}_source_queue_deadline_us",
        )
        != first_deadline
    ):
        failures.append(
            f"{payload_issue_transport_worker_dispatch_prefix}_source_queue_deadline_us_mismatch",
        )
    if summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary"
    ):
        failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_transport_worker_dispatch_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_transport_worker_dispatch_prefix}_{key}_mismatch")

    payload_issue_copy_descriptor_prefix = (
        f"{prefix}_live_runtime_adapter_payload_issue_copy_descriptor_dry_run"
    )
    expected_payload_issue_copy_descriptor_status = (
        "blocked_by_payload_issue_transport_worker_dispatch_blocked_canary:"
        f"{expected_payload_issue_transport_worker_dispatch_status}"
    )
    if summary.get(f"{payload_issue_copy_descriptor_prefix}_present") is not True:
        failures.append(f"{payload_issue_copy_descriptor_prefix}_present_mismatch")
    if (
        summary.get(f"{payload_issue_copy_descriptor_prefix}_stage")
        != "payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run"
    ):
        failures.append(f"{payload_issue_copy_descriptor_prefix}_stage_mismatch")
    if (
        summary.get(f"{payload_issue_copy_descriptor_prefix}_status")
        != expected_payload_issue_copy_descriptor_status
    ):
        failures.append(f"{payload_issue_copy_descriptor_prefix}_status_mismatch")
    if (
        summary.get(
            f"{payload_issue_copy_descriptor_prefix}_consumes_payload_issue_transport_worker_dispatch_blocked_canary",
        )
        is not True
    ):
        failures.append(
            f"{payload_issue_copy_descriptor_prefix}_consumes_payload_issue_transport_worker_dispatch_blocked_canary_mismatch",
        )
    if (
        summary.get(
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_transport_worker_dispatch_status",
        )
        != expected_payload_issue_transport_worker_dispatch_status
    ):
        failures.append(
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_transport_worker_dispatch_status_mismatch",
        )
    if (
        summary.get(f"{payload_issue_copy_descriptor_prefix}_payload_issue_copy_descriptor_schema")
        != "payload_cache_runtime_payload_issue_copy_descriptor_v1"
    ):
        failures.append(
            f"{payload_issue_copy_descriptor_prefix}_payload_issue_copy_descriptor_schema_mismatch",
        )
    for key in (
        "payload_issue_copy_descriptor_created",
        "payload_issue_transport_worker_dispatch_consumed",
        "copy_descriptor_shape_checked",
    ):
        if summary.get(f"{payload_issue_copy_descriptor_prefix}_{key}") is not True:
            failures.append(f"{payload_issue_copy_descriptor_prefix}_{key}_mismatch")
    for key in ("copy_descriptor_submitted", "copy_descriptor_executed"):
        if summary.get(f"{payload_issue_copy_descriptor_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_copy_descriptor_prefix}_{key}_mismatch")
    for key, expected in {
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": first_shifted_packet_count,
        "source_issue_unique_key_count": first_shifted_unique_count,
        "source_queue_budget_capacity": first_capacity,
        "source_issue_lead_tokens": first_lead,
        "planned_issue_count": 0,
        "scheduled_issue_count": 0,
        "queued_issue_count": 0,
        "submitted_issue_count": 0,
        "inflight_issue_count": 0,
        "dispatched_issue_count": 0,
        "command_packet_count": 0,
        "transport_work_count": 0,
        "transport_worker_dispatch_count": 0,
        "copy_descriptor_count": 0,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }.items():
        if _int_metric(summary, f"{payload_issue_copy_descriptor_prefix}_{key}") != expected:
            failures.append(f"{payload_issue_copy_descriptor_prefix}_{key}_mismatch")
    if (
        summary.get(f"{payload_issue_copy_descriptor_prefix}_request_source")
        != "queue_budget_first_model_passing_cell"
    ):
        failures.append(f"{payload_issue_copy_descriptor_prefix}_request_source_mismatch")
    if (
        _float_metric(
            summary,
            f"{payload_issue_copy_descriptor_prefix}_source_queue_deadline_us",
        )
        != first_deadline
    ):
        failures.append(
            f"{payload_issue_copy_descriptor_prefix}_source_queue_deadline_us_mismatch",
        )
    if summary.get(f"{payload_issue_copy_descriptor_prefix}_decision") != "blocked":
        failures.append(f"{payload_issue_copy_descriptor_prefix}_decision_mismatch")
    if (
        summary.get(f"{payload_issue_copy_descriptor_prefix}_block_reason")
        != "payload_transfer_disabled"
    ):
        failures.append(f"{payload_issue_copy_descriptor_prefix}_block_reason_mismatch")
    if (
        summary.get(f"{payload_issue_copy_descriptor_prefix}_execution_mode")
        != "payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run"
    ):
        failures.append(f"{payload_issue_copy_descriptor_prefix}_execution_mode_mismatch")
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
        if summary.get(f"{payload_issue_copy_descriptor_prefix}_{key}") is not False:
            failures.append(f"{payload_issue_copy_descriptor_prefix}_{key}_mismatch")

    if first_shifted_enabled is not True:
        failures.append(f"{prefix}_first_shifted_issue_accounting_enabled_mismatch")
    if first_shifted_packet_count != 28:
        failures.append(
            f"{prefix}_first_shifted_issue_accounted_packet_count_mismatch"
        )
    if first_shifted_unique_count is None or first_shifted_unique_count <= 0:
        failures.append(f"{prefix}_first_shifted_issue_unique_issue_key_count_invalid")


def check_premap_lab_preflight_summary(
    summary: dict[str, Any],
    *,
    min_source_count: int = 32,
    expected_online_merged_device: int = 1,
) -> dict[str, Any]:
    failures: list[str] = []

    for key, expected in {
        "passed": True,
        "default_contract_passed": True,
        "prefetch_lab_default_gate_passed": True,
        "prefetch_lab_default_gate_decision_status": "passed",
        "prefetch_lab_default_full_fetch_decision": (
            "blocked_by_ready_time_measured_copy"
        ),
        "prefetch_lab_default_full_fetch_passed": True,
        "prefetch_lab_default_ready_time_report_passed": True,
        "prefetch_lab_default_ready_time_allow_full_fetch": False,
        "prefetch_lab_default_ready_time_direct_snapshot_report_present": True,
        "prefetch_lab_default_ready_time_direct_snapshot_report_passed": True,
        "prefetch_lab_default_ready_time_direct_snapshot_report_recheck_passed": True,
        "prefetch_lab_default_ready_time_direct_snapshot_present": True,
        "prefetch_lab_default_ready_time_direct_snapshot_runtime_stage": (
            "online_ready_time_payload_cache_accounting_only"
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_payload_bytes": 0,
        "prefetch_lab_default_ready_time_direct_snapshot_full_fetch_runtime_allowed": (
            False
        ),
        "prefetch_lab_default_ready_time_direct_snapshot_changes_kernel_launch_args": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_present": True,
        "prefetch_lab_default_payload_cache_runtime_participation_stage": (
            "online_ready_time_payload_cache_runtime_participation_dry_run"
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_consumes_direct_snapshot": (
            True
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes": 0,
        "prefetch_lab_default_payload_cache_runtime_participation_ready_credit": False,
        "prefetch_lab_default_payload_cache_runtime_participation_real_ready_credit_granted": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_kernel_arg_pass_allowed": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_changes_kernel_launch_args": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_full_fetch_runtime_allowed": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_participation_payload_transfer_runtime_enabled": (
            False
        ),
        "prefetch_lab_default_payload_cache_runtime_plan_present": True,
        "prefetch_lab_default_payload_cache_runtime_plan_stage": (
            "payload_cache_runtime_plan_lab_gate_dry_run"
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
        "prefetch_lab_default_payload_cache_runtime_execution_decision": "blocked",
        "prefetch_lab_default_payload_cache_runtime_execution_execution_mode": (
            "payloadless_lab_gate_dry_run"
        ),
        "prefetch_lab_default_payload_cache_runtime_execution_consumes_plan": True,
        "prefetch_lab_default_payload_cache_runtime_execution_live_payload_runtime_enabled": False,
        "prefetch_lab_default_payload_cache_runtime_execution_payload_transfer_runtime_enabled": False,
        "prefetch_lab_default_payload_cache_runtime_execution_issued_payload_count": 0,
        "prefetch_lab_default_payload_cache_runtime_execution_payload_bytes": 0,
        "prefetch_lab_default_payload_cache_runtime_execution_ready_credit": False,
        "prefetch_lab_default_payload_cache_runtime_execution_real_ready_credit_granted": False,
        "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed": False,
        "prefetch_lab_default_payload_cache_runtime_execution_changes_kernel_launch_args": False,
        "prefetch_lab_default_payload_cache_runtime_execution_full_fetch_runtime_allowed": False,
        "prefetch_lab_default_metadata_decision": "shadow_only",
        "prefetch_lab_default_metadata_passed": True,
        "prefetch_lab_default_premap_decision": (
            "lab_enabled_descriptor_prep_only"
        ),
        "prefetch_lab_default_premap_passed": True,
        "default_required_evidence_passed": True,
        "default_optional_evidence_passed": True,
        "default_kernel_consumer_schema_passed": True,
        "default_kernel_consumer_online_merged_multiprogram_evidence_passed": True,
        "default_kernel_consumer_online_merged_multiprogram_hashchain_equal": True,
        "default_kernel_consumer_online_merged_multiprogram_all_handle_fields_checked": True,
        "default_kernel_consumer_online_merged_multiprogram_no_payload": True,
        "default_kernel_consumer_online_merged_multiprogram_passed_to_kernel": False,
        "default_kernel_consumer_online_merged_multiprogram_changes_kernel_launch_args": False,
        "default_kernel_consumer_online_merged_multiprogram_not_single_launch_table": True,
        "default_kernel_consumer_online_merged_multiprogram_current_wna16_arg_compatible": False,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_invocation_entry_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_abi": True,
        "default_kernel_consumer_online_merged_multiprogram_require_kernel_endpoint_ptr_abi": True,
        "default_kernel_consumer_dispatch_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_dispatch_ptr_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_abi_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_current_wna16_arg_compatible": False,
        "default_kernel_consumer_arg_slot_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_arg_slot_all_handle_fields_read": True,
        "default_kernel_consumer_consumer_view_all_handle_fields_read": True,
        "default_kernel_consumer_consumer_view_payload_bytes": 0,
        "default_kernel_consumer_consumer_view_passed_to_kernel": False,
        "default_kernel_consumer_consumer_view_changes_kernel_launch_args": False,
        "default_kernel_consumer_consumer_view_current_wna16_arg_compatible": False,
        "default_kernel_consumer_consumer_view_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_entry_args_checked": True,
        "default_kernel_consumer_kernel_entry_args_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_entry_args_payload_bytes": 0,
        "default_kernel_consumer_kernel_entry_args_passed_to_kernel": False,
        "default_kernel_consumer_kernel_entry_args_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_entry_args_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_entry_args_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_invocation_checked": True,
        "default_kernel_consumer_kernel_invocation_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_invocation_payload_bytes": 0,
        "default_kernel_consumer_kernel_invocation_passed_to_kernel": False,
        "default_kernel_consumer_kernel_invocation_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_invocation_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_invocation_entry_checked": True,
        "default_kernel_consumer_kernel_invocation_entry_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_invocation_entry_payload_bytes": 0,
        "default_kernel_consumer_kernel_invocation_entry_passed_to_kernel": False,
        "default_kernel_consumer_kernel_invocation_entry_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_invocation_entry_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_checked": True,
        "default_kernel_consumer_kernel_endpoint_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_endpoint_payload_bytes": 0,
        "default_kernel_consumer_kernel_endpoint_passed_to_kernel": False,
        "default_kernel_consumer_kernel_endpoint_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_endpoint_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_endpoint_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_kernel_endpoint_ptr_checked": True,
        "default_kernel_consumer_kernel_endpoint_ptr_all_handle_fields_read": True,
        "default_kernel_consumer_kernel_endpoint_ptr_payload_bytes": 0,
        "default_kernel_consumer_kernel_endpoint_ptr_passed_to_kernel": False,
        "default_kernel_consumer_kernel_endpoint_ptr_kernel_arg_pass_allowed": False,
        "default_kernel_consumer_kernel_endpoint_ptr_changes_kernel_launch_args": False,
        "default_kernel_consumer_kernel_endpoint_ptr_current_wna16_arg_compatible": False,
        "default_kernel_consumer_kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_wna16_side_variant_evidence_label": (
            "wna16_side_consumer_variant_execution_128strict_runner_json"
        ),
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
        "default_kernel_consumer_wna16_side_variant_all_handle_fields_read": True,
        "default_kernel_consumer_wna16_side_variant_error_count": 0,
        "default_kernel_consumer_wna16_side_variant_packet_chain_depth": 16,
        "default_kernel_consumer_wna16_side_variant_payload_bytes": 0,
        "default_kernel_consumer_wna16_side_variant_passed_to_kernel": False,
        "default_kernel_consumer_wna16_side_variant_changes_kernel_launch_args": False,
        "default_kernel_consumer_wna16_side_variant_current_wna16_arg_compatible": False,
        "default_kernel_consumer_wna16_side_variant_requires_wna16_arg_reinterpretation": False,
        "default_kernel_consumer_wna16_side_variant_explicit_typed_abi_slot": True,
        "default_kernel_consumer_wna16_side_variant_reuses_current_wna16_arg_slot": False,
        "default_kernel_consumer_typed_noop_ready": True,
        "default_kernel_consumer_wna16_side_variant_base_ready": True,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")

    for key in (
        "prefetch_lab_default_ready_time_direct_snapshot_report_present",
        "prefetch_lab_default_ready_time_direct_snapshot_report_passed",
        "prefetch_lab_default_ready_time_direct_snapshot_report_recheck_passed",
        "prefetch_lab_default_ready_time_direct_snapshot_present",
    ):
        if summary.get(key) is not True:
            failures.append(f"{key}_type_mismatch")

    for key in (
        "prefetch_lab_default_ready_time_direct_snapshot_full_fetch_runtime_allowed",
        "prefetch_lab_default_ready_time_direct_snapshot_changes_kernel_launch_args",
    ):
        if summary.get(key) is not False:
            failures.append(f"{key}_type_mismatch")

    direct_snapshot_runtime_stage = summary.get(
        "prefetch_lab_default_ready_time_direct_snapshot_runtime_stage"
    )
    if (
        not isinstance(direct_snapshot_runtime_stage, str)
        or direct_snapshot_runtime_stage
        != "online_ready_time_payload_cache_accounting_only"
    ):
        failures.append(
            "prefetch_lab_default_ready_time_direct_snapshot_runtime_stage_type_mismatch"
        )
    if (
        _int_metric(
            summary,
            "prefetch_lab_default_ready_time_direct_snapshot_payload_bytes",
        )
        != 0
    ):
        failures.append(
            "prefetch_lab_default_ready_time_direct_snapshot_payload_bytes_type_mismatch"
        )

    for key in (
        "prefetch_lab_default_payload_cache_runtime_participation_present",
        "prefetch_lab_default_payload_cache_runtime_participation_consumes_direct_snapshot",
    ):
        if summary.get(key) is not True:
            failures.append(f"{key}_type_mismatch")
    for key in (
        "prefetch_lab_default_payload_cache_runtime_participation_ready_credit",
        "prefetch_lab_default_payload_cache_runtime_participation_real_ready_credit_granted",
        "prefetch_lab_default_payload_cache_runtime_participation_kernel_arg_pass_allowed",
        "prefetch_lab_default_payload_cache_runtime_participation_changes_kernel_launch_args",
        "prefetch_lab_default_payload_cache_runtime_participation_full_fetch_runtime_allowed",
        "prefetch_lab_default_payload_cache_runtime_participation_payload_transfer_runtime_enabled",
    ):
        if summary.get(key) is not False:
            failures.append(f"{key}_type_mismatch")
    runtime_participation_stage = summary.get(
        "prefetch_lab_default_payload_cache_runtime_participation_stage"
    )
    if (
        not isinstance(runtime_participation_stage, str)
        or runtime_participation_stage
        != "online_ready_time_payload_cache_runtime_participation_dry_run"
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_participation_stage_type_mismatch"
        )
    runtime_participation_status = summary.get(
        "prefetch_lab_default_payload_cache_runtime_participation_status"
    )
    if (
        not isinstance(runtime_participation_status, str)
        or runtime_participation_status
        not in PAYLOAD_CACHE_RUNTIME_PARTICIPATION_ALLOWED_STATUSES
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_participation_status_type_mismatch"
        )
    if (
        _int_metric(
            summary,
            "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes",
        )
        != 0
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_participation_payload_bytes_type_mismatch"
        )

    for key in (
        "prefetch_lab_default_payload_cache_runtime_plan_present",
        "prefetch_lab_default_payload_cache_runtime_plan_consumes_participation",
    ):
        if summary.get(key) is not True:
            failures.append(f"{key}_type_mismatch")
    for key in (
        "prefetch_lab_default_payload_cache_runtime_plan_live_payload_runtime_enabled",
        "prefetch_lab_default_payload_cache_runtime_plan_ready_credit",
        "prefetch_lab_default_payload_cache_runtime_plan_kernel_arg_pass_allowed",
        "prefetch_lab_default_payload_cache_runtime_plan_changes_kernel_launch_args",
        "prefetch_lab_default_payload_cache_runtime_plan_full_fetch_runtime_allowed",
    ):
        if summary.get(key) is not False:
            failures.append(f"{key}_type_mismatch")
    runtime_plan_stage = summary.get(
        "prefetch_lab_default_payload_cache_runtime_plan_stage"
    )
    if (
        not isinstance(runtime_plan_stage, str)
        or runtime_plan_stage != "payload_cache_runtime_plan_lab_gate_dry_run"
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_plan_stage_type_mismatch"
        )
    runtime_plan_status = summary.get(
        "prefetch_lab_default_payload_cache_runtime_plan_status"
    )
    if (
        not isinstance(runtime_plan_status, str)
        or runtime_plan_status not in PAYLOAD_CACHE_RUNTIME_PLAN_ALLOWED_STATUSES
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_plan_status_type_mismatch"
        )
    elif isinstance(runtime_participation_status, str):
        if runtime_participation_status == "ready_time_candidate_requires_lab_gate":
            expected_runtime_plan_status = (
                "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
            )
        else:
            expected_runtime_plan_status = (
                f"participation_not_full_fetch_candidate:{runtime_participation_status}"
            )
        if runtime_plan_status != expected_runtime_plan_status:
            failures.append(
                "prefetch_lab_default_payload_cache_runtime_plan_status_mismatch"
            )
    for key in (
        "prefetch_lab_default_payload_cache_runtime_plan_planned_issue_count",
        "prefetch_lab_default_payload_cache_runtime_plan_payload_bytes",
    ):
        if _int_metric(summary, key) != 0:
            failures.append(f"{key}_type_mismatch")

    for key in (
        "prefetch_lab_default_payload_cache_runtime_execution_present",
        "prefetch_lab_default_payload_cache_runtime_execution_consumes_plan",
    ):
        if summary.get(key) is not True:
            failures.append(f"{key}_type_mismatch")
    for key in (
        "prefetch_lab_default_payload_cache_runtime_execution_live_payload_runtime_enabled",
        "prefetch_lab_default_payload_cache_runtime_execution_payload_transfer_runtime_enabled",
        "prefetch_lab_default_payload_cache_runtime_execution_ready_credit",
        "prefetch_lab_default_payload_cache_runtime_execution_real_ready_credit_granted",
        "prefetch_lab_default_payload_cache_runtime_execution_kernel_arg_pass_allowed",
        "prefetch_lab_default_payload_cache_runtime_execution_changes_kernel_launch_args",
        "prefetch_lab_default_payload_cache_runtime_execution_full_fetch_runtime_allowed",
    ):
        if summary.get(key) is not False:
            failures.append(f"{key}_type_mismatch")
    runtime_execution_stage = summary.get(
        "prefetch_lab_default_payload_cache_runtime_execution_stage"
    )
    if (
        not isinstance(runtime_execution_stage, str)
        or runtime_execution_stage
        != "payload_cache_runtime_execution_lab_gate_dry_run"
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_execution_stage_type_mismatch"
        )
    runtime_execution_status = summary.get(
        "prefetch_lab_default_payload_cache_runtime_execution_status"
    )
    if (
        not isinstance(runtime_execution_status, str)
        or runtime_execution_status
        not in PAYLOAD_CACHE_RUNTIME_EXECUTION_ALLOWED_STATUSES
    ):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_execution_status_type_mismatch"
        )
    elif isinstance(runtime_plan_status, str):
        expected_runtime_execution_status = (
            f"blocked_by_runtime_plan:{runtime_plan_status}"
        )
        if runtime_execution_status != expected_runtime_execution_status:
            failures.append(
                "prefetch_lab_default_payload_cache_runtime_execution_status_mismatch"
            )
    runtime_execution_plan_status = summary.get(
        "prefetch_lab_default_payload_cache_runtime_execution_plan_status"
    )
    if runtime_execution_plan_status != runtime_plan_status:
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_execution_plan_status_mismatch"
        )
    runtime_execution_decision = summary.get(
        "prefetch_lab_default_payload_cache_runtime_execution_decision"
    )
    if runtime_execution_decision != "blocked":
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_execution_decision_mismatch"
        )
    runtime_execution_block_reason = summary.get(
        "prefetch_lab_default_payload_cache_runtime_execution_block_reason"
    )
    if runtime_execution_block_reason != runtime_plan_status:
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_execution_block_reason_mismatch"
        )
    runtime_execution_execution_mode = summary.get(
        "prefetch_lab_default_payload_cache_runtime_execution_execution_mode"
    )
    if runtime_execution_execution_mode != "payloadless_lab_gate_dry_run":
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_execution_execution_mode_mismatch"
        )
    for key in (
        "prefetch_lab_default_payload_cache_runtime_execution_issued_payload_count",
        "prefetch_lab_default_payload_cache_runtime_execution_payload_bytes",
    ):
        if _int_metric(summary, key) != 0:
            failures.append(f"{key}_type_mismatch")

    for key in (
        "prefetch_lab_default_gate_failures",
        "prefetch_lab_default_full_fetch_failures",
        "prefetch_lab_default_metadata_failures",
        "prefetch_lab_default_premap_failures",
    ):
        if summary.get(key) != []:
            failures.append(f"{key}_not_empty")
    premap_positive = _int_metric(
        summary,
        "prefetch_lab_default_premap_positive_count",
    )
    recommended_capacity = _int_metric(
        summary,
        "prefetch_lab_default_premap_recommended_capacity_entries",
    )
    no_eviction_capacity = _int_metric(
        summary,
        "prefetch_lab_default_premap_no_eviction_capacity_entries",
    )
    if premap_positive is None or premap_positive < 4:
        failures.append("prefetch_lab_default_premap_positive_count_below_min")
    if recommended_capacity is None or recommended_capacity < 12288:
        failures.append(
            "prefetch_lab_default_premap_recommended_capacity_entries_below_min"
        )
    if no_eviction_capacity is None or no_eviction_capacity < 12288:
        failures.append(
            "prefetch_lab_default_premap_no_eviction_capacity_entries_below_min"
        )
    if (
        recommended_capacity is not None
        and no_eviction_capacity is not None
        and no_eviction_capacity > recommended_capacity
    ):
        failures.append(
            "prefetch_lab_default_premap_no_eviction_capacity_above_recommended"
        )
    ready_time_issued = _int_metric(
        summary,
        "prefetch_lab_default_ready_time_issued_fetch_count",
    )
    ready_time_used = _int_metric(
        summary,
        "prefetch_lab_default_ready_time_used_fetch_count",
    )
    ready_time_used_per_issued = _float_metric(
        summary,
        "prefetch_lab_default_ready_time_used_per_issued_fetch",
    )
    ready_time_demand_hit = _float_metric(
        summary,
        "prefetch_lab_default_ready_time_demand_hit_rate",
    )
    ready_time_late_miss = _float_metric(
        summary,
        "prefetch_lab_default_ready_time_ready_late_miss_rate",
    )
    ready_time_decision_reason = summary.get(
        "prefetch_lab_default_ready_time_decision_reason"
    )
    ready_time_threshold_failures = summary.get(
        "prefetch_lab_default_ready_time_threshold_failures"
    )
    if ready_time_decision_reason == "full_fetch_threshold_not_met":
        if ready_time_threshold_failures != ["used_per_issued_fetch_below_threshold"]:
            failures.append(
                "prefetch_lab_default_ready_time_threshold_failures_mismatch"
            )
        if ready_time_issued is None or ready_time_issued <= 0:
            failures.append("prefetch_lab_default_ready_time_issued_fetch_count_invalid")
        if ready_time_used != 0:
            failures.append("prefetch_lab_default_ready_time_used_fetch_count_mismatch")
        if ready_time_used_per_issued != 0.0:
            failures.append(
                "prefetch_lab_default_ready_time_used_per_issued_fetch_mismatch"
            )
        if ready_time_demand_hit is None or not (0.0 <= ready_time_demand_hit <= 1.0):
            failures.append("prefetch_lab_default_ready_time_demand_hit_rate_invalid")
        if ready_time_late_miss is None or not (0.0 <= ready_time_late_miss <= 1.0):
            failures.append(
                "prefetch_lab_default_ready_time_ready_late_miss_rate_invalid"
            )
    elif ready_time_decision_reason == "insufficient_ready_time_and_lookahead":
        if ready_time_threshold_failures != []:
            failures.append(
                "prefetch_lab_default_ready_time_threshold_failures_mismatch"
            )
        _check_ready_time_decision_gate_block(summary, failures)
    else:
        failures.append("prefetch_lab_default_ready_time_decision_reason_mismatch")
    direct_issue_sources = summary.get(
        "prefetch_lab_default_ready_time_direct_snapshot_issue_sources"
    )
    allowed_direct_issue_sources = {
        "previous_token_transition_premap_shadow",
        "prelaunch_observed_transition_premap_shadow",
    }
    if not isinstance(direct_issue_sources, list):
        failures.append(
            "prefetch_lab_default_ready_time_direct_snapshot_issue_sources_invalid"
        )
    else:
        observed_sources = {str(value) for value in direct_issue_sources}
        if (
            not observed_sources
            or not observed_sources.issubset(allowed_direct_issue_sources)
        ):
            failures.append(
                "prefetch_lab_default_ready_time_direct_snapshot_issue_sources_mismatch"
            )
    runtime_participation_issue_sources = summary.get(
        "prefetch_lab_default_payload_cache_runtime_participation_issue_sources"
    )
    if not isinstance(runtime_participation_issue_sources, list):
        failures.append(
            "prefetch_lab_default_payload_cache_runtime_participation_issue_sources_invalid"
        )
    else:
        observed_sources = {str(value) for value in runtime_participation_issue_sources}
        if (
            not observed_sources
            or not observed_sources.issubset(allowed_direct_issue_sources)
        ):
            failures.append(
                "prefetch_lab_default_payload_cache_runtime_participation_issue_sources_mismatch"
            )
        if isinstance(direct_issue_sources, list) and (
            observed_sources != {str(value) for value in direct_issue_sources}
        ):
            failures.append(
                "prefetch_lab_default_payload_cache_runtime_participation_issue_sources_do_not_match_direct_snapshot"
            )
    _check_stream_full_fetch_block(summary, failures)
    _check_stream_shifted_issue_replay_contract(summary, failures)
    _check_stream_queue_budget(summary, failures)

    for key in (
        "runtime_gate_evidence_deferred_count",
        "strict_default_gate_evidence_deferred_count",
        "default_kernel_consumer_dispatch_runner_final_runtime_gate_evidence_deferred_count",
        "default_kernel_consumer_dispatch_runner_final_strict_default_gate_evidence_deferred_count",
    ):
        value = _int_metric(summary, key)
        if value != 0:
            failures.append(f"{key}_not_zero")

    source_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_source_count",
    )
    row_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_row_count",
    )
    dispatch_offset = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_offset",
    )
    dispatch_limit = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_row_limit",
    )
    active_rows = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_dispatch_active_rows",
    )
    if source_count is None or source_count < min_source_count:
        failures.append("online_merged_source_count_invalid")
    if row_count is None or row_count <= 0:
        failures.append("online_merged_row_count_invalid")
    if dispatch_offset != 0:
        failures.append("online_merged_dispatch_offset_not_zero")
    if row_count is not None and dispatch_limit != row_count:
        failures.append("online_merged_dispatch_limit_not_full_table")
    if row_count is not None and active_rows != row_count:
        failures.append("online_merged_dispatch_active_rows_mismatch")
    device = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_device",
    )
    hip_visible_devices = summary.get(
        "default_kernel_consumer_online_merged_multiprogram_hip_visible_devices"
    )
    logical_gpu1 = (
        int(expected_online_merged_device) == 1
        and device == 0
        and str(hip_visible_devices) == "1"
    )
    if device != int(expected_online_merged_device) and not logical_gpu1:
        if int(expected_online_merged_device) == 1:
            failures.append("online_merged_device_not_gpu1")
        else:
            failures.append("online_merged_device_mismatch")
    if (
        summary.get("default_kernel_consumer_online_merged_multiprogram_mirror_field")
        != "scale_metadata_handle"
    ):
        failures.append("online_merged_mirror_field_mismatch")
    wna16_side_evidence_path = summary.get(
        "default_kernel_consumer_wna16_side_variant_evidence_path"
    )
    if not isinstance(wna16_side_evidence_path, str) or not wna16_side_evidence_path:
        failures.append("wna16_side_variant_evidence_path_missing")
    wna16_side_source_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_source_count",
    )
    online_source_context_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_source_context_count",
    )
    online_source_identity_count = _int_metric(
        summary,
        "default_kernel_consumer_online_merged_multiprogram_source_identity_count",
    )
    online_source_context_matches_source_count = summary.get(
        "default_kernel_consumer_online_merged_multiprogram_source_context_matches_source_count"
    )
    online_source_identity_coverage = summary.get(
        "default_kernel_consumer_online_merged_multiprogram_source_identity_coverage"
    )
    wna16_side_source_context_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_source_context_count",
    )
    wna16_side_source_identity_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_source_identity_count",
    )
    wna16_side_source_context_matches_source_count = summary.get(
        "default_kernel_consumer_wna16_side_variant_source_context_matches_source_count"
    )
    wna16_side_source_identity_coverage = summary.get(
        "default_kernel_consumer_wna16_side_variant_source_identity_coverage"
    )
    wna16_side_missing_source_identity_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_online_source_identity_missing_count",
    )
    wna16_side_source_identity_subset = summary.get(
        "default_kernel_consumer_wna16_side_variant_online_source_identity_subset"
    )
    wna16_side_row_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_row_count",
    )
    wna16_side_row_ok_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_side_variant_row_ok_count",
    )
    wna16_kernel_side_execution_ready = summary.get(
        "default_kernel_consumer_wna16_kernel_side_execution_ready"
    )
    wna16_kernel_side_execution_row_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_kernel_side_execution_row_count",
    )
    wna16_kernel_side_execution_row_ok_count = _int_metric(
        summary,
        "default_kernel_consumer_wna16_kernel_side_execution_row_ok_count",
    )
    if wna16_side_source_count is None or wna16_side_source_count < 128:
        failures.append("wna16_side_variant_source_count_invalid")
    if online_source_context_count is None or online_source_context_count <= 0:
        failures.append("online_merged_source_context_count_invalid")
    if online_source_identity_count is None or online_source_identity_count <= 0:
        failures.append("online_merged_source_identity_count_invalid")
    if (
        source_count is not None
        and online_source_context_count is not None
        and online_source_context_count != source_count
    ):
        failures.append("online_merged_source_context_count_mismatch")
    if online_source_context_matches_source_count is not True:
        failures.append("online_merged_source_context_matches_source_count_mismatch")
    if (
        online_source_context_count is not None
        and online_source_identity_count is not None
        and online_source_identity_count != online_source_context_count
    ):
        failures.append("online_merged_source_identity_count_mismatch")
    if online_source_identity_coverage is not True:
        failures.append("online_merged_source_identity_coverage_mismatch")
    if wna16_side_source_context_count is None or wna16_side_source_context_count <= 0:
        failures.append("wna16_side_variant_source_context_count_invalid")
    if (
        wna16_side_source_count is not None
        and wna16_side_source_context_count is not None
        and wna16_side_source_context_count != wna16_side_source_count
    ):
        failures.append("wna16_side_variant_source_context_count_mismatch")
    if wna16_side_source_context_matches_source_count is not True:
        failures.append("wna16_side_variant_source_context_matches_source_count_mismatch")
    if (
        wna16_side_source_identity_count is None
        or wna16_side_source_identity_count <= 0
    ):
        failures.append("wna16_side_variant_source_identity_count_invalid")
    if (
        wna16_side_source_context_count is not None
        and wna16_side_source_identity_count is not None
        and wna16_side_source_identity_count != wna16_side_source_context_count
    ):
        failures.append("wna16_side_variant_source_identity_count_mismatch")
    if wna16_side_source_identity_coverage is not True:
        failures.append("wna16_side_variant_source_identity_coverage_mismatch")
    if summary.get(
        "default_kernel_consumer_wna16_benchmark_prerequisites_ready"
    ) is True:
        failures.append("wna16_benchmark_prerequisites_ready_not_allowed")
    for key in (
        "default_kernel_consumer_online_merged_multiprogram_source_identity_digest",
        "default_kernel_consumer_wna16_side_variant_source_identity_digest",
    ):
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")
    if wna16_side_source_identity_subset is True:
        if wna16_side_missing_source_identity_count != 0:
            failures.append("wna16_side_variant_source_identity_missing_count_mismatch")
        if summary.get("default_kernel_consumer_wna16_side_variant_ready") is not True:
            failures.append("wna16_side_variant_ready_mismatch")
        if wna16_kernel_side_execution_ready is True:
            if (
                wna16_kernel_side_execution_row_count is None
                or wna16_kernel_side_execution_row_count <= 0
            ):
                failures.append("wna16_kernel_side_execution_row_count_invalid")
            if (
                wna16_kernel_side_execution_row_count is not None
                and wna16_kernel_side_execution_row_ok_count
                != wna16_kernel_side_execution_row_count
            ):
                failures.append("wna16_kernel_side_execution_row_ok_count_mismatch")
            if (
                row_count is not None
                and wna16_kernel_side_execution_row_count is not None
                and wna16_kernel_side_execution_row_count < row_count
            ):
                failures.append("wna16_kernel_side_execution_row_count_below_online_merged")
            expected_kernel_side = {
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
            }
            for key, expected_value in expected_kernel_side.items():
                if summary.get(key) != expected_value:
                    failures.append(f"{key}_mismatch")
            for field in REQUIRED_ROW_FIELDS:
                key = (
                    "default_kernel_consumer_wna16_kernel_side_execution_"
                    f"{field}_read_row_ok_count"
                )
                if (
                    wna16_kernel_side_execution_row_count is not None
                    and _int_metric(summary, key)
                    != wna16_kernel_side_execution_row_count
                ):
                    failures.append(
                        f"wna16_kernel_side_execution_{field}_read_row_ok_count_mismatch"
                    )
            for key in (
                "default_kernel_consumer_wna16_kernel_side_execution_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_handle_projection_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_descriptor_ptr_read_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_packed_weight_descriptor_read_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_scale_metadata_handle_read_hash_accumulator",
                "default_kernel_consumer_wna16_kernel_side_execution_aux_metadata_handle_read_hash_accumulator",
            ):
                if not _is_hex_u64(summary.get(key)):
                    failures.append(f"{key}_invalid")
        elif wna16_kernel_side_execution_ready not in (False, None):
            failures.append("wna16_kernel_side_execution_ready_invalid")
        wna16_benchmark_ready = (
            summary.get("default_kernel_consumer_wna16_benchmark_ready") is True
        )
        if wna16_benchmark_ready:
            failures.append("wna16_benchmark_ready_not_allowed_in_no_mutation_gate")
        payloadless_ready_failures: list[str] = []
        payloadless_execution_ready = _payloadless_execution_ready(
            summary,
            payloadless_ready_failures,
        )
        variant_execution_failures: list[str] = []
        variant_execution_structural_ready = (
            _future_wna16_variant_execution_ready(
                summary,
                variant_execution_failures,
            )
        )
        typed_path_failures: list[str] = []
        future_kernel_side_typed_path_ready = _future_kernel_side_typed_path_ready(
            summary,
            typed_path_failures,
        )
        if (
            summary.get(
                "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
            )
            is True
            or summary.get(
                "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid"
            )
            is True
        ) and not future_kernel_side_typed_path_ready:
            failures.append("future_kernel_side_typed_path_reported_without_valid_evidence")
            failures.extend(typed_path_failures)
        chain_consistency_failures: list[str] = []
        typed_path_source_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_source_count",
        )
        typed_path_row_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_kernel_side_typed_path_row_count",
        )
        payloadless_source_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_payloadless_execution_source_count",
        )
        payloadless_row_count = _int_metric(
            summary,
            "default_kernel_consumer_future_wna16_payloadless_execution_row_count",
        )
        if (
            typed_path_source_count is not None
            and payloadless_source_count is not None
            and typed_path_source_count != payloadless_source_count
        ):
            chain_consistency_failures.append(
                "payloadless_typed_path_source_count_mismatch"
            )
        if (
            typed_path_row_count is not None
            and payloadless_row_count is not None
            and typed_path_row_count != payloadless_row_count
        ):
            chain_consistency_failures.append(
                "payloadless_typed_path_row_count_mismatch"
            )
        chain_consistent = not chain_consistency_failures
        computed_payloadless_chain_ready = (
            summary.get("default_kernel_consumer_wna16_side_variant_ready") is True
            and future_kernel_side_typed_path_ready
            and payloadless_execution_ready
            and chain_consistent
        )
        future_wna16_variant_execution_ready = (
            computed_payloadless_chain_ready and variant_execution_structural_ready
        )
        useful_consumer_failures: list[str] = []
        useful_consumer_structural_ready = _future_wna16_useful_consumer_ready(
            summary,
            useful_consumer_failures,
        )
        future_wna16_useful_consumer_ready = (
            future_wna16_variant_execution_ready
            and useful_consumer_structural_ready
        )
        payloadless_useful_execution_failures: list[str] = []
        payloadless_useful_execution_structural_ready = (
            _future_wna16_payloadless_useful_execution_ready(
                summary,
                payloadless_useful_execution_failures,
            )
        )
        future_wna16_payloadless_useful_execution_ready = (
            future_wna16_useful_consumer_ready
            and payloadless_useful_execution_structural_ready
        )
        payloadless_useful_repeat_benchmark_failures: list[str] = []
        payloadless_useful_repeat_benchmark_structural_ready = (
            _future_wna16_payloadless_useful_repeat_benchmark_ready(
                summary,
                payloadless_useful_repeat_benchmark_failures,
            )
        )
        future_wna16_payloadless_useful_repeat_benchmark_ready = (
            future_wna16_payloadless_useful_execution_ready
            and payloadless_useful_repeat_benchmark_structural_ready
        )
        reported_payloadless_chain_ready = summary.get(
            "default_kernel_consumer_independent_typed_slot_payloadless_chain_ready"
        )
        if reported_payloadless_chain_ready is True and not computed_payloadless_chain_ready:
            failures.append("payloadless_chain_ready_reported_without_valid_evidence")
            failures.extend(typed_path_failures)
            failures.extend(payloadless_ready_failures)
            failures.extend(chain_consistency_failures)
        elif computed_payloadless_chain_ready and reported_payloadless_chain_ready is not True:
            failures.append("payloadless_chain_ready_not_reported")
        elif reported_payloadless_chain_ready not in (False, None, True):
            failures.append("payloadless_chain_ready_invalid")
        reported_variant_execution_ready = summary.get(
            "default_kernel_consumer_future_wna16_variant_execution_gate_ready"
        )
        if (
            reported_variant_execution_ready is True
            and not future_wna16_variant_execution_ready
        ):
            failures.append(
                "future_wna16_variant_execution_ready_reported_without_valid_evidence"
            )
            failures.extend(variant_execution_failures)
            if not computed_payloadless_chain_ready:
                failures.extend(typed_path_failures)
                failures.extend(payloadless_ready_failures)
                failures.extend(chain_consistency_failures)
        elif (
            future_wna16_variant_execution_ready
            and reported_variant_execution_ready is not True
        ):
            failures.append("future_wna16_variant_execution_ready_not_reported")
        elif reported_variant_execution_ready not in (False, None, True):
            failures.append("future_wna16_variant_execution_ready_invalid")
        reported_useful_consumer_ready = summary.get(
            "default_kernel_consumer_future_wna16_useful_consumer_gate_ready"
        )
        if reported_useful_consumer_ready is True and not future_wna16_useful_consumer_ready:
            failures.append(
                "future_wna16_useful_consumer_ready_reported_without_valid_evidence"
            )
            failures.extend(useful_consumer_failures)
            if not future_wna16_variant_execution_ready:
                failures.extend(variant_execution_failures)
        elif (
            future_wna16_useful_consumer_ready
            and reported_useful_consumer_ready is not True
        ):
            failures.append("future_wna16_useful_consumer_ready_not_reported")
        elif reported_useful_consumer_ready not in (False, None, True):
            failures.append("future_wna16_useful_consumer_ready_invalid")
        reported_payloadless_useful_execution_ready = summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_execution_gate_ready"
        )
        if (
            reported_payloadless_useful_execution_ready is True
            and not future_wna16_payloadless_useful_execution_ready
        ):
            failures.append(
                "future_wna16_payloadless_useful_execution_ready_reported_without_valid_evidence"
            )
            failures.extend(payloadless_useful_execution_failures)
            if not future_wna16_useful_consumer_ready:
                failures.extend(useful_consumer_failures)
        elif (
            future_wna16_payloadless_useful_execution_ready
            and reported_payloadless_useful_execution_ready is not True
        ):
            failures.append("future_wna16_payloadless_useful_execution_ready_not_reported")
        elif reported_payloadless_useful_execution_ready not in (False, None, True):
            failures.append("future_wna16_payloadless_useful_execution_ready_invalid")
        reported_payloadless_useful_repeat_benchmark_ready = summary.get(
            "default_kernel_consumer_future_wna16_payloadless_useful_repeat_benchmark_gate_ready"
        )
        if (
            reported_payloadless_useful_repeat_benchmark_ready is True
            and not future_wna16_payloadless_useful_repeat_benchmark_ready
        ):
            failures.append(
                "future_wna16_payloadless_useful_repeat_benchmark_ready_reported_without_valid_evidence"
            )
            failures.extend(payloadless_useful_repeat_benchmark_failures)
            if not future_wna16_payloadless_useful_execution_ready:
                failures.extend(payloadless_useful_execution_failures)
        elif (
            future_wna16_payloadless_useful_repeat_benchmark_ready
            and reported_payloadless_useful_repeat_benchmark_ready is not True
        ):
            failures.append(
                "future_wna16_payloadless_useful_repeat_benchmark_ready_not_reported"
            )
        elif reported_payloadless_useful_repeat_benchmark_ready not in (
            False,
            None,
            True,
        ):
            failures.append(
                "future_wna16_payloadless_useful_repeat_benchmark_ready_invalid"
            )
        expected_stage = (
            "implement_future_wna16_typed_slot_payloadless_useful_runtime_ablation"
            if future_wna16_payloadless_useful_repeat_benchmark_ready
            else "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
            if future_wna16_payloadless_useful_execution_ready
            else "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
            if future_wna16_useful_consumer_ready
            else "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
            if future_wna16_variant_execution_ready
            else "implement_future_wna16_typed_slot_kernel_variant_execution"
            if computed_payloadless_chain_ready
            else (
                "implement_wna16_typed_slot_benchmark_harness"
                if wna16_kernel_side_execution_ready is True
                else "implement_real_wna16_typed_slot_kernel_variant"
            )
        )
        if summary.get("default_kernel_consumer_next_runtime_stage") != expected_stage:
            failures.append("wna16_side_variant_next_stage_mismatch")
    elif wna16_side_source_identity_subset is False:
        if (
            wna16_side_missing_source_identity_count is None
            or wna16_side_missing_source_identity_count <= 0
        ):
            failures.append("wna16_side_variant_source_identity_missing_count_invalid")
        if summary.get("default_kernel_consumer_wna16_side_variant_ready") is not False:
            failures.append("wna16_side_variant_ready_mismatch")
        if summary.get("default_kernel_consumer_wna16_benchmark_ready") is not False:
            failures.append("wna16_side_variant_benchmark_ready_mismatch")
        if wna16_kernel_side_execution_ready is True:
            failures.append("wna16_kernel_side_execution_ready_without_source_subset")
        elif wna16_kernel_side_execution_ready not in (False, None):
            failures.append("wna16_kernel_side_execution_ready_invalid")
        if (
            summary.get("default_kernel_consumer_next_runtime_stage")
            != "refresh_wna16_side_variant_source_provenance"
        ):
            failures.append("wna16_side_variant_next_stage_mismatch")
    else:
        failures.append("wna16_side_variant_source_identity_subset_invalid")
    if wna16_side_row_count is None or wna16_side_row_count <= 0:
        failures.append("wna16_side_variant_row_count_invalid")
    if wna16_side_row_count is not None and wna16_side_row_ok_count != wna16_side_row_count:
        failures.append("wna16_side_variant_row_ok_count_mismatch")
    if (
        row_count is not None
        and wna16_side_row_count is not None
        and wna16_side_row_count < row_count
    ):
        failures.append("wna16_side_variant_row_count_below_online_merged")
    for field in REQUIRED_ROW_FIELDS:
        key = f"default_kernel_consumer_wna16_side_variant_{field}_read_row_ok_count"
        if (
            wna16_side_row_count is not None
            and _int_metric(summary, key) != wna16_side_row_count
        ):
            failures.append(f"wna16_side_variant_{field}_read_row_ok_count_mismatch")
    for key in (
        "default_kernel_consumer_wna16_side_variant_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_handle_projection_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_descriptor_ptr_read_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_packed_weight_descriptor_read_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_scale_metadata_handle_read_hash_accumulator",
        "default_kernel_consumer_wna16_side_variant_aux_metadata_handle_read_hash_accumulator",
    ):
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")

    if summary.get("default_kernel_consumer_arg_slot_field_read_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("arg_slot_field_read_field_names_mismatch")
    arg_slot_read_row_count = _int_metric(
        summary,
        "default_kernel_consumer_arg_slot_field_read_row_count",
    )
    row_ok_counts = summary.get(
        "default_kernel_consumer_arg_slot_field_read_row_ok_counts"
    )
    error_counts = summary.get(
        "default_kernel_consumer_arg_slot_field_read_error_counts"
    )
    read_hashes = summary.get("default_kernel_consumer_arg_slot_field_read_hashes")
    if not isinstance(row_ok_counts, dict):
        failures.append("arg_slot_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    if not isinstance(error_counts, dict):
        failures.append("arg_slot_field_read_error_counts_missing")
        error_counts = {}
    if not isinstance(read_hashes, dict):
        failures.append("arg_slot_field_read_hashes_missing")
        read_hashes = {}
    if arg_slot_read_row_count is not None:
        for field in REQUIRED_ROW_FIELDS:
            if row_ok_counts.get(field) != arg_slot_read_row_count:
                failures.append(f"arg_slot_{field}_read_row_ok_count_mismatch")
            if error_counts.get(field) != 0:
                failures.append(f"arg_slot_{field}_read_error_count_mismatch")
            if not isinstance(read_hashes.get(field), str) or not read_hashes.get(field):
                failures.append(f"arg_slot_{field}_read_hash_missing")

    if summary.get("default_kernel_consumer_consumer_view_field_read_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("consumer_view_field_read_field_names_mismatch")
    consumer_view_read_row_count = _int_metric(
        summary,
        "default_kernel_consumer_consumer_view_field_read_row_count",
    )
    view_row_ok_counts = summary.get(
        "default_kernel_consumer_consumer_view_field_read_row_ok_counts"
    )
    view_error_counts = summary.get(
        "default_kernel_consumer_consumer_view_field_read_error_counts"
    )
    view_read_hashes = summary.get(
        "default_kernel_consumer_consumer_view_field_read_hashes"
    )
    if not isinstance(view_row_ok_counts, dict):
        failures.append("consumer_view_field_read_row_ok_counts_missing")
        view_row_ok_counts = {}
    if not isinstance(view_error_counts, dict):
        failures.append("consumer_view_field_read_error_counts_missing")
        view_error_counts = {}
    if not isinstance(view_read_hashes, dict):
        failures.append("consumer_view_field_read_hashes_missing")
        view_read_hashes = {}
    if consumer_view_read_row_count is not None:
        for field in REQUIRED_ROW_FIELDS:
            if view_row_ok_counts.get(field) != consumer_view_read_row_count:
                failures.append(f"consumer_view_{field}_read_row_ok_count_mismatch")
            if view_error_counts.get(field) != 0:
                failures.append(f"consumer_view_{field}_read_error_count_mismatch")
            if not isinstance(view_read_hashes.get(field), str) or not view_read_hashes.get(field):
                failures.append(f"consumer_view_{field}_read_hash_missing")
    if summary.get("default_kernel_consumer_consumer_view_source_packet_chain_depth") != 3:
        failures.append("consumer_view_source_packet_chain_depth_mismatch")
    if (
        summary.get("default_kernel_consumer_kernel_entry_args_field_read_path")
        != "kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    ):
        failures.append("kernel_entry_args_field_read_path_mismatch")
    if summary.get("default_kernel_consumer_kernel_entry_args_packet_chain_depth") != 5:
        failures.append("kernel_entry_args_packet_chain_depth_mismatch")
    entry_row_count = _int_metric(
        summary,
        "default_kernel_consumer_kernel_entry_args_summary_row_count",
    )
    entry_row_ok_count = _int_metric(
        summary,
        "default_kernel_consumer_kernel_entry_args_summary_row_ok_count",
    )
    if entry_row_count is None or entry_row_count <= 0:
        failures.append("kernel_entry_args_summary_row_count_invalid")
    if entry_row_count is not None and entry_row_ok_count != entry_row_count:
        failures.append("kernel_entry_args_summary_row_ok_count_mismatch")
    for field in REQUIRED_ROW_FIELDS:
        key = (
            "default_kernel_consumer_kernel_entry_args_summary_"
            f"{field}_read_row_ok_count"
        )
        if entry_row_count is not None and _int_metric(summary, key) != entry_row_count:
            failures.append(f"kernel_entry_args_{field}_read_row_ok_count_mismatch")
    if (
        entry_row_count is not None
        and _int_metric(
            summary,
            "default_kernel_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count",
        )
        != entry_row_count
    ):
        failures.append("kernel_entry_args_row_metadata_read_row_ok_count_mismatch")
    if (
        _int_metric(
            summary,
            "default_kernel_consumer_kernel_entry_args_summary_error_count",
        )
        != 0
    ):
        failures.append("kernel_entry_args_summary_error_count_mismatch")
    if (
        _int_metric(
            summary,
            "default_kernel_consumer_kernel_entry_args_summary_field_mask",
        )
        != 15
    ):
        failures.append("kernel_entry_args_summary_field_mask_mismatch")
    for key in (
        "default_kernel_consumer_kernel_entry_args_summary_row_hash_accumulator",
        "default_kernel_consumer_kernel_entry_args_summary_field_read_hash_accumulator",
        "default_kernel_consumer_kernel_entry_args_summary_row_metadata_hash_accumulator",
    ):
        if not _is_hex_u64(summary.get(key)):
            failures.append(f"{key}_invalid")
    _check_kernel_consumer_handle_summary(
        summary,
        failures,
        prefix="default_kernel_consumer_request_ptr",
        label="request_ptr",
        expected_field_read_path=(
            "request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        expected_packet_chain_depth=4,
    )
    _check_kernel_consumer_handle_summary(
        summary,
        failures,
        prefix="default_kernel_consumer_request_launch",
        label="request_launch",
        expected_field_read_path=(
            "request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        expected_packet_chain_depth=5,
    )
    _check_request_launch_geometry(summary, failures)
    _check_kernel_consumer_handle_summary(
        summary,
        failures,
        prefix="default_kernel_consumer_request_launch_ptr",
        label="request_launch_ptr",
        expected_field_read_path=(
            "request_launch_ptr_to_request_launch_to_request_ptr_to_kernel_arg_packet_to_program_view_rows"
        ),
        expected_packet_chain_depth=6,
    )
    for prefix in (
        "default_kernel_consumer_kernel_invocation",
        "default_kernel_consumer_kernel_invocation_entry",
        "default_kernel_consumer_kernel_endpoint",
        "default_kernel_consumer_kernel_endpoint_ptr",
    ):
        if prefix.endswith("endpoint_ptr"):
            expected_depth = 13
        elif prefix.endswith("endpoint"):
            expected_depth = 12
        else:
            expected_depth = 11
        if summary.get(f"{prefix}_packet_chain_depth") != expected_depth:
            failures.append(f"{prefix}_packet_chain_depth_mismatch")
        for suffix in (
            "row_hash_accumulator",
            "field_read_hash_accumulator",
            "row_metadata_hash_accumulator",
        ):
            key = f"{prefix}_{suffix}"
            if not _is_hex_u64(summary.get(key)):
                failures.append(f"{key}_invalid")

    if summary.get("default_kernel_consumer_schema_row_field_names") != REQUIRED_ROW_FIELDS:
        failures.append("schema_row_field_names_mismatch")
    if summary.get("default_kernel_consumer_schema_row_metadata_names") != REQUIRED_ROW_METADATA:
        failures.append("schema_row_metadata_names_mismatch")

    for key, expected in REQUIRED_LAYOUT_CHECKS.items():
        if summary.get(key) != expected:
            failures.append(f"{key}_mismatch")

    for key in REQUIRED_SHA_FIELDS:
        if not _is_hex64(summary.get(key)):
            failures.append(f"{key}_invalid")

    required = summary.get("required_evidence")
    if not isinstance(required, dict):
        failures.append("required_evidence_missing")
    else:
        required_count = _int_metric(required, "required_count")
        present_count = _int_metric(required, "present_count")
        passed_count = _int_metric(required, "passed_count")
        if required_count is None or required_count <= 0:
            failures.append("required_evidence_required_count_invalid")
        if required_count is not None and present_count != required_count:
            failures.append("required_evidence_present_count_mismatch")
        if required_count is not None and passed_count != required_count:
            failures.append("required_evidence_passed_count_mismatch")

    optional = summary.get("optional_evidence")
    if not isinstance(optional, dict):
        failures.append("optional_evidence_missing")
    else:
        required_count = _int_metric(optional, "required_count")
        present_count = _int_metric(optional, "present_count")
        passed_count = _int_metric(optional, "passed_count")
        if required_count is None or required_count <= 0:
            failures.append("optional_evidence_required_count_invalid")
        if required_count is not None and present_count != required_count:
            failures.append("optional_evidence_present_count_mismatch")
        if required_count is not None and passed_count != required_count:
            failures.append("optional_evidence_passed_count_mismatch")

    return {
        "passed": not failures,
        "failures": failures,
        "source": "premap_lab_preflight_summary_check",
        "min_source_count": int(min_source_count),
        "online_merged_source_count": source_count,
        "online_merged_row_count": row_count,
        "online_merged_dispatch_active_rows": active_rows,
        "online_merged_device": device,
        "online_merged_hip_visible_devices": hip_visible_devices,
        "expected_online_merged_device": int(expected_online_merged_device),
        "online_merged_mirror_field": summary.get(
            "default_kernel_consumer_online_merged_multiprogram_mirror_field"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--min-source-count", type=int, default=32)
    parser.add_argument("--expected-online-merged-device", type=int, default=1)
    parser.add_argument("--output-json", type=Path)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    checked_path = args.summary_json.resolve()
    result = check_premap_lab_preflight_summary(
        _load_json(args.summary_json),
        min_source_count=args.min_source_count,
        expected_online_merged_device=args.expected_online_merged_device,
    )
    result["checked_preflight_json"] = str(checked_path)
    result["checked_preflight_json_raw"] = str(args.summary_json)
    result["checked_preflight_sha256"] = _sha256(args.summary_json)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
