#!/usr/bin/env python3
"""Run read-only preflight checks for the premap lab gate artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.check_premap_kernel_consumer_schema import (
    check_kernel_consumer_schema_artifact,
)
from scripts.check_gate_evidence_paths import check_gate_evidence_paths
from scripts.check_runtime_gate_evidence_paths import scan_runtime_gate_evidence_paths
from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
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
    "single_field_handle_handoff_canary_required": True,
    "single_field_handle_handoff_canary_mode": (
        "readonly_single_field_handle_handoff_canary"
    ),
    "single_field_handle_handoff_canary_field": "scale_metadata_handle",
    "single_field_handle_handoff_canary_source": "semantic_handle_table",
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
    "strict_single_field_handle_handoff_canary_128_gate_json",
    "strict_native_typed_consumer_bridge_128_gate_json",
    "native_typed_consumer_bridge_smoke_json",
    "strict_native_stub_online_invocation_canary_128_gate_json",
    "native_typed_consumer_stub_gpu1_canary_json",
    "native_typed_consumer_stub_online_prelaunch_input_canary_json",
    "native_typed_consumer_online_prelaunch_canary_runner_json",
}
ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL = (
    "native_typed_consumer_online_prelaunch_canary_runner_json"
)

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


def _int_metric(metrics: dict[str, Any], key: str) -> int | None:
    value = metrics.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


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


def _validate_single_field_canary_evidence(metrics: dict[str, Any]) -> list[str]:
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
        "field_name": "scale_metadata_handle",
        "source": "semantic_handle_table",
        "block_reason": "single_field_handoff_live_disabled",
    }
    for suffix, expected in expected_values.items():
        failures.extend(_check_metric_equals(metrics, f"{prefix}{suffix}", expected))
    return failures


def _validate_required_evidence_payload(
    evidence_label: str,
    evidence: dict[str, Any],
    *,
    evidence_paths: dict[str, Any] | None = None,
    root: Path | None = None,
) -> list[str]:
    metrics = evidence.get("metrics")
    if evidence_label not in {
        "strict_native_typed_consumer_bridge_128_gate_json",
        "strict_single_field_handle_handoff_canary_128_gate_json",
        "strict_native_stub_online_invocation_canary_128_gate_json",
        "native_typed_consumer_stub_gpu1_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_canary_json",
        "native_typed_consumer_online_prelaunch_canary_runner_json",
    }:
        return []
    if evidence_label == "native_typed_consumer_online_prelaunch_canary_runner_json":
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
        preflight_summary = evidence.get("preflight_summary")
        if not isinstance(preflight_summary, dict):
            failures.append("runner_preflight_summary_missing")
        else:
            if preflight_summary.get("passed") is not True:
                failures.append("runner_preflight_summary_not_passed")
            if preflight_summary.get("failures") != []:
                failures.append("runner_preflight_summary_failures_not_empty")
        return [f"{evidence_label}:{failure}" for failure in failures]
    if evidence_label in {
        "native_typed_consumer_stub_gpu1_canary_json",
        "native_typed_consumer_stub_online_prelaunch_input_canary_json",
    }:
        expected_input_path = None
        if isinstance(evidence_paths, dict):
            input_label = (
                "native_typed_consumer_online_prelaunch_input_json"
                if evidence_label
                == "native_typed_consumer_stub_online_prelaunch_input_canary_json"
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
                == "native_typed_consumer_stub_online_prelaunch_input_canary_json"
                else None
            )
        return [
            f"{evidence_label}:{failure}"
            for failure in _validate_native_typed_consumer_stub_evidence(
                evidence,
                expected_input_path=expected_input_path,
                export_performance_path=export_performance_path,
                root=root,
                require_extended_noop_meta=(
                    evidence_label
                    == "native_typed_consumer_stub_online_prelaunch_input_canary_json"
                ),
                require_online_export_context=(
                    evidence_label
                    == "native_typed_consumer_stub_online_prelaunch_input_canary_json"
                ),
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
    for macro in (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
        "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
    ):
        if macros.get(macro) is not True:
            failures.append(f"native_typed_consumer_stub_{macro}_not_enabled")
    for forbidden in (
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
    ):
        if macros.get(forbidden):
            failures.append(f"native_typed_consumer_stub_{forbidden}_enabled")
    return failures
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
        }
    contract = ((payload or {}).get("contract") or {})
    for key, expected in REQUIRED_DEFAULT_GATE_CONTRACT.items():
        actual = contract.get(key)
        if actual != expected:
            failures.append(f"{key}_mismatch")
    return {
        "gate_path": label,
        "passed": not failures,
        "failures": failures,
        "required_contract": dict(REQUIRED_DEFAULT_GATE_CONTRACT),
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
            defer_online_prelaunch_runner_evidence
            and evidence_label == ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL
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
        if not isinstance(evidence, dict):
            failures.append(f"{evidence_label}:json_not_object")
            row["failure"] = "json_not_object"
        elif evidence.get("passed") is not True:
            failures.append(f"{evidence_label}:not_passed")
            row["failure"] = "not_passed"
        elif evidence.get("failures") != []:
            failures.append(f"{evidence_label}:failures_not_empty")
            row["failure"] = "failures_not_empty"
        else:
            content_failures = _validate_required_evidence_payload(
                evidence_label,
                evidence,
                evidence_paths=evidence_paths,
                root=root,
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
        "deferred_labels": (
            [ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL]
            if defer_online_prelaunch_runner_evidence
            else []
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
        is_passed = (
            is_present
            and row.get("valid_json") is True
            and row.get("passed_value") is True
            and row.get("failures_value") == []
            and "failure" not in row
        )
        present_count += int(is_present)
        passed_count += int(is_passed)
        evidence[label] = {
            "path": row.get("path"),
            "path_label": row.get("path_label"),
            "present": is_present,
            "passed": is_passed,
            "failure": row.get("failure"),
        }
    required_labels = check.get("required_labels")
    required_count = (
        len(required_labels) if isinstance(required_labels, list) else len(rows)
    )
    return {
        "passed": bool(check.get("passed", False)),
        "required_count": required_count,
        "present_count": present_count,
        "passed_count": passed_count,
        "evidence": evidence,
    }


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
    default_gate_contract_check = _check_default_gate_contract(
        default_readonly_gate,
        root=root,
    )
    default_kernel_consumer_schema_check = _check_default_kernel_consumer_schema(
        default_readonly_gate,
        root=root,
    )
    default_gate_required_evidence_check = _check_required_default_gate_evidence_json(
        default_readonly_gate,
        root=root,
        allow_missing=allow_missing_evidence,
        defer_online_prelaunch_runner_evidence=(
            defer_online_prelaunch_runner_evidence
        ),
    )
    deferred_evidence_labels = (
        {ONLINE_PRELAUNCH_RUNNER_EVIDENCE_LABEL}
        if defer_online_prelaunch_runner_evidence
        else set()
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
    lab_gate_status_summary = {
        "passed": not failures,
        "default_readonly_gate_path": default_gate_path,
        "canary_gate_path": canary_gate_path,
        "default_contract_passed": bool(
            default_gate_contract_check.get("passed", False)
        ),
        "default_kernel_consumer_schema_passed": bool(
            default_kernel_consumer_schema_check.get("passed", False)
        ),
        "default_required_evidence_passed": bool(
            default_gate_required_evidence_check.get("passed", False)
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
        "deferred_online_prelaunch_runner_evidence": bool(
            defer_online_prelaunch_runner_evidence
        ),
        "native_typed_consumer_bridge_required": (
            REQUIRED_DEFAULT_GATE_CONTRACT["native_typed_consumer_bridge_required"]
        ),
        "native_stub_online_invocation_canary_required": (
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "native_stub_online_invocation_canary_required"
            ]
        ),
        "single_field_handle_handoff_canary_required": (
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "single_field_handle_handoff_canary_required"
            ]
        ),
        "payload_bytes_required": REQUIRED_DEFAULT_GATE_CONTRACT[
            "native_typed_consumer_bridge_payload_bytes_required"
        ],
        "passed_to_kernel_required": REQUIRED_DEFAULT_GATE_CONTRACT[
            "native_typed_consumer_bridge_passed_to_kernel_required"
        ],
        "changes_kernel_launch_args_required": (
            REQUIRED_DEFAULT_GATE_CONTRACT[
                "native_typed_consumer_bridge_changes_kernel_launch_args_required"
            ]
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
