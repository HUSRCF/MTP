#!/usr/bin/env python3
"""Check readonly-live trusted-refs prelaunch package evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HANDOFF_BOOL_PREFIX = "runtime_shadow_premap_kernel_arg_handoff_"
LIVE_MUTATION_COUNTER_PREFIX = "runtime_shadow_premap_kernel_arg_live_mutation_"

EXPECTED_TRUE_BOOL_KEYS = frozenset(
    {
        "runtime_shadow_premap_live_config_without_router_recorder_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected",
        "runtime_shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled",
    }
)

REQUIRED_FALSE_BOOL_KEYS = frozenset(
    {
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live",
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_trust_producer_refs",
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_strict_native_only",
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_require_prepared_device_source",
    }
)

EXPECTED_STRING_VALUES = {
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_validation_mode": (
        "trusted_refs"
    ),
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
        "original_kernel_arg_identity"
    ),
    "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": (
        "off"
    ),
}

REQUIRED_INT_KEYS = frozenset(
    {
        "sample_count",
        "requested_output_token_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_missing_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_layer_mismatch_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_block_reason_mismatch_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_unavailable_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_unavailable_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_vllm_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_non_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_ready_source_mismatch_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_unavailable_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_non_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_unavailable_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_vllm_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_non_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_attached_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_attached_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_attached_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes",
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes",
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_kernel_variant_launch_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_kernel_variant_fallback_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_slim_kernel_variant_launch_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_slim_kernel_variant_fallback_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_launch_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_fallback_count",
    }
)

ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS = frozenset(
    {
        "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_vllm_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_vllm_device_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_attached_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_attached_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_attached_count",
    }
)


def _read_bool(payload: dict[str, Any], key: str, failures: list[str]) -> bool:
    if key not in payload:
        failures.append(f"{key}:missing")
        return False
    value = payload[key]
    if not isinstance(value, bool):
        failures.append(f"{key}:not_bool")
        return False
    return bool(value)


def _read_int(payload: dict[str, Any], key: str, failures: list[str]) -> int:
    if key not in payload:
        failures.append(f"{key}:missing")
        return 0
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        failures.append(f"{key}:not_int")
        return 0
    return int(value)


def check_premap_readonly_live_trusted_refs(
    payload: dict[str, Any],
    *,
    min_package_seen: int = 1,
    expected_trace_mode: str | None = None,
    min_sample_count: int = 0,
    min_requested_output_tokens: int = 0,
) -> dict[str, Any]:
    failures: list[str] = []
    trace_mode = str(payload.get("mode", ""))
    bool_values: dict[str, bool] = {}
    for key in sorted(EXPECTED_TRUE_BOOL_KEYS | REQUIRED_FALSE_BOOL_KEYS):
        bool_values[key] = _read_bool(payload, key, failures)
    int_values = {
        key: _read_int(payload, key, failures) for key in sorted(REQUIRED_INT_KEYS)
    }
    string_values: dict[str, str] = {}
    for key, expected in EXPECTED_STRING_VALUES.items():
        value = str(payload.get(key, ""))
        string_values[key] = value
        if value != expected:
            failures.append(f"{key}:expected_{expected}")

    handoff_bool_values: dict[str, bool] = {}
    for key, value in payload.items():
        if not key.startswith(HANDOFF_BOOL_PREFIX):
            continue
        if not isinstance(value, bool):
            continue
        handoff_bool_values[key] = bool(value)
        if key in EXPECTED_TRUE_BOOL_KEYS:
            if not value:
                failures.append(f"{key}:not_true")
        elif value:
            failures.append(f"{key}:true")

    live_mutation_counter_values: dict[str, int] = {}
    for key, value in payload.items():
        if not key.startswith(LIVE_MUTATION_COUNTER_PREFIX):
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            failures.append(f"{key}:not_int")
            continue
        live_mutation_counter_values[key] = int(value)
        if key not in ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS and int(value) != 0:
            failures.append(f"{key}:nonzero")

    for key in EXPECTED_TRUE_BOOL_KEYS:
        if not bool_values.get(key, False):
            failures.append(f"{key}:not_true")
    for key in REQUIRED_FALSE_BOOL_KEYS:
        if bool_values.get(key, False):
            failures.append(f"{key}:true")

    if expected_trace_mode is not None and trace_mode != str(expected_trace_mode):
        failures.append("trace_mode_mismatch")

    sample_count = int_values["sample_count"]
    requested_output_token_count = int_values["requested_output_token_count"]
    if sample_count < int(min_sample_count):
        failures.append("sample_count_below_min")
    if requested_output_token_count < int(min_requested_output_tokens):
        failures.append("requested_output_token_count_below_min")

    package_seen = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count"
    ]
    package_pass_through = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count"
    ]
    producer_future = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count"
    ]
    producer_gpu = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count"
    ]
    envelope_seen = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count"
    ]
    trusted_refs_seen = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_seen_count"
    ]
    trusted_refs_available = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_available_count"
    ]
    trusted_refs_unavailable = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_unavailable_count"
    ]
    trusted_ptr_seen = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_seen_count"
    ]
    trusted_ptr_available = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_available_count"
    ]
    trusted_ptr_unavailable = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_unavailable_count"
    ]
    trusted_ptr_vllm = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_vllm_device_count"
    ]
    trusted_ptr_non_device = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_non_device_count"
    ]
    trusted_ptr_mismatch = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_ready_source_mismatch_count"
    ]
    observer_seen = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count"
    ]
    observer_available = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count"
    ]
    observer_vllm = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count"
    ]

    if package_seen < int(min_package_seen):
        failures.append("package_seen_below_min")
    if producer_future <= 0:
        failures.append("producer_future_typed_slot_envelope_missing")
    if producer_gpu <= 0:
        failures.append("producer_gpu_assignment_envelope_missing")
    if producer_future != producer_gpu:
        failures.append("producer_envelope_count_mismatch")
    if package_pass_through != package_seen:
        failures.append("package_pass_through_mismatch")
    if envelope_seen != package_seen:
        failures.append("gpu_assignment_envelope_seen_mismatch")
    if trusted_refs_seen != package_seen:
        failures.append("trusted_refs_seen_mismatch")
    if trusted_refs_available != trusted_refs_seen:
        failures.append("trusted_refs_available_mismatch")
    if trusted_refs_unavailable != 0:
        failures.append("trusted_refs_unavailable_nonzero")
    if trusted_ptr_seen != trusted_refs_seen:
        failures.append("trusted_ptr_seen_mismatch")
    if trusted_ptr_available != trusted_ptr_seen:
        failures.append("trusted_ptr_available_mismatch")
    if trusted_ptr_vllm != trusted_ptr_seen:
        failures.append("trusted_ptr_vllm_device_mismatch")
    if trusted_ptr_unavailable != 0:
        failures.append("trusted_ptr_unavailable_nonzero")
    if trusted_ptr_non_device != 0:
        failures.append("trusted_ptr_non_device_nonzero")
    if trusted_ptr_mismatch != 0:
        failures.append("trusted_ptr_ready_source_mismatch_nonzero")
    if observer_seen <= 0:
        failures.append("observer_seen_nonpositive")
    if observer_available != observer_seen:
        failures.append("observer_available_mismatch")
    if observer_vllm != observer_seen:
        failures.append("observer_vllm_device_mismatch")

    return {
        "schema_version": 1,
        "mode": "premap_readonly_live_trusted_refs_check",
        "passed": not failures,
        "failures": failures,
        "min_package_seen": int(min_package_seen),
        "expected_trace_mode": expected_trace_mode,
        "trace_mode": trace_mode,
        "min_sample_count": int(min_sample_count),
        "sample_count": sample_count,
        "min_requested_output_tokens": int(min_requested_output_tokens),
        "requested_output_token_count": requested_output_token_count,
        "package_seen": package_seen,
        "package_pass_through": package_pass_through,
        "producer_future_typed_slot_envelope_count": producer_future,
        "producer_gpu_assignment_envelope_count": producer_gpu,
        "gpu_assignment_envelope_seen": envelope_seen,
        "trusted_refs_seen": trusted_refs_seen,
        "trusted_refs_available": trusted_refs_available,
        "trusted_refs_unavailable": trusted_refs_unavailable,
        "trusted_ptr_seen": trusted_ptr_seen,
        "trusted_ptr_available": trusted_ptr_available,
        "trusted_ptr_vllm_device": trusted_ptr_vllm,
        "trusted_ptr_mismatch": trusted_ptr_mismatch,
        "observer_seen": observer_seen,
        "observer_available": observer_available,
        "observer_vllm_device": observer_vllm,
        "required_bool_values": bool_values,
        "handoff_bool_values": handoff_bool_values,
        "string_values": string_values,
        "live_mutation_counter_values": live_mutation_counter_values,
        "allowed_nonzero_live_mutation_counter_keys": sorted(
            ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--performance-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--min-package-seen", type=int, default=1)
    parser.add_argument("--expected-trace-mode", default=None)
    parser.add_argument("--min-sample-count", type=int, default=0)
    parser.add_argument("--min-requested-output-tokens", type=int, default=0)
    args = parser.parse_args()

    payload = json.loads(args.performance_json.read_text())
    result = check_premap_readonly_live_trusted_refs(
        payload,
        min_package_seen=int(args.min_package_seen),
        expected_trace_mode=args.expected_trace_mode,
        min_sample_count=int(args.min_sample_count),
        min_requested_output_tokens=int(args.min_requested_output_tokens),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
