#!/usr/bin/env python3
"""Check no-op vLLM prelaunch pointer-source observer evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_BOOL_KEYS = (
    "runtime_shadow_premap_live_config_without_router_recorder_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected",
    "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_trust_producer_refs",
    "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled",
)

REQUIRED_INT_KEYS = (
    "sample_count",
    "requested_output_token_count",
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
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_seen_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_available_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_unavailable_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_vllm_device_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_non_device_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_ready_source_mismatch_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_seen_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_available_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_unavailable_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_launch_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_fallback_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_minimal_identity_envelope_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes",
    "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes",
    "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_kernel_variant_launch_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_kernel_variant_fallback_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_slim_kernel_variant_launch_count",
    "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_slim_kernel_variant_fallback_count",
)

EXPECTED_TRUE_BOOL_KEYS = frozenset(
    {
        "runtime_shadow_premap_live_config_without_router_recorder_enabled",
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled",
    }
)
ALLOWED_TRUE_HANDOFF_BOOL_KEYS = frozenset(
    {
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled",
    }
)

ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS = frozenset(
    {
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count",
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count",
    }
)
LIVE_MUTATION_COUNTER_PREFIX = "runtime_shadow_premap_kernel_arg_live_mutation_"
HANDOFF_BOOL_PREFIX = "runtime_shadow_premap_kernel_arg_handoff_"

ZERO_INT_KEYS = tuple(
    key
    for key in REQUIRED_INT_KEYS
    if key
    not in {
        "sample_count",
        "requested_output_token_count",
        *ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS,
    }
)


def _read_bool(
    payload: dict[str, Any],
    key: str,
    failures: list[str],
) -> bool:
    if key not in payload:
        failures.append(f"{key}:missing")
        return False
    value = payload[key]
    if not isinstance(value, bool):
        failures.append(f"{key}:not_bool")
        return False
    return value


def _read_int(
    payload: dict[str, Any],
    key: str,
    failures: list[str],
) -> int:
    if key not in payload:
        failures.append(f"{key}:missing")
        return 0
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        failures.append(f"{key}:not_int")
        return 0
    return int(value)


def check_premap_prelaunch_pointer_source_observer(
    payload: dict[str, Any],
    *,
    min_seen: int = 1,
    expected_trace_mode: str | None = None,
    min_sample_count: int = 0,
    min_requested_output_tokens: int = 0,
) -> dict[str, Any]:
    failures: list[str] = []
    trace_mode = str(payload.get("mode", ""))
    bool_values = {
        key: _read_bool(payload, key, failures) for key in REQUIRED_BOOL_KEYS
    }
    int_values = {key: _read_int(payload, key, failures) for key in REQUIRED_INT_KEYS}
    handoff_bool_values: dict[str, bool] = {}
    for key, value in payload.items():
        if not key.startswith(HANDOFF_BOOL_PREFIX):
            continue
        if not isinstance(value, bool):
            continue
        handoff_bool_values[key] = bool(value)

    live_mutation_counter_values: dict[str, int] = {}
    for key, value in payload.items():
        if not key.startswith(LIVE_MUTATION_COUNTER_PREFIX):
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            failures.append(f"{key}:not_int")
            continue
        live_mutation_counter_values[key] = int(value)

    for key, value in bool_values.items():
        if key in EXPECTED_TRUE_BOOL_KEYS:
            if not value:
                failures.append(f"{key}:not_true")
        elif value:
            failures.append(f"{key}:true")

    for key, value in handoff_bool_values.items():
        if key not in ALLOWED_TRUE_HANDOFF_BOOL_KEYS and value:
            failures.append(f"{key}:true")

    for key, value in live_mutation_counter_values.items():
        if key not in ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS and value != 0:
            failures.append(f"{key}:nonzero")

    sample_count = int_values["sample_count"]
    requested_output_token_count = int_values["requested_output_token_count"]
    if expected_trace_mode is not None and trace_mode != str(expected_trace_mode):
        failures.append("trace_mode_mismatch")
    if sample_count < int(min_sample_count):
        failures.append("sample_count_below_min")
    if requested_output_token_count < int(min_requested_output_tokens):
        failures.append("requested_output_token_count_below_min")

    live_config_enabled = bool_values[
        "runtime_shadow_premap_live_config_without_router_recorder_enabled"
    ]
    canary_enabled = bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled"
    ]
    live_enabled = bool_values["runtime_shadow_premap_kernel_arg_handoff_live_enabled"]
    live_consumer_connected = bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected"
    ]
    kernel_arg_pass_enabled = bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    ]
    real_mutation_enabled = bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"
    ]
    producer_envelope_enabled = bool_values[
        "runtime_shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled"
    ]

    observer_seen = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count"
    ]
    observer_available = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count"
    ]
    observer_unavailable = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_unavailable_count"
    ]
    observer_vllm_device = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count"
    ]
    observer_non_device = int_values[
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_non_device_count"
    ]

    if not live_config_enabled:
        failures.append("live_config_without_router_recorder_disabled")
    if not canary_enabled:
        failures.append("prelaunch_pointer_source_canary_disabled")
    if live_enabled:
        failures.append("live_handoff_enabled")
    if live_consumer_connected:
        failures.append("live_consumer_connected")
    if kernel_arg_pass_enabled:
        failures.append("kernel_arg_pass_enabled")
    if real_mutation_enabled:
        failures.append("real_kernel_arg_mutation_enabled")
    if producer_envelope_enabled:
        failures.append("producer_gpu_assignment_envelope_enabled")
    if observer_seen < int(min_seen):
        failures.append("observer_seen_below_min")
    if observer_available != observer_seen:
        failures.append("observer_available_mismatch")
    if observer_vllm_device != observer_seen:
        failures.append("observer_vllm_device_mismatch")
    if observer_unavailable != 0:
        failures.append("observer_unavailable_nonzero")
    if observer_non_device != 0:
        failures.append("observer_non_device_nonzero")
    for key in ZERO_INT_KEYS:
        if int_values[key] != 0:
            failures.append(f"{key}:nonzero")

    return {
        "schema_version": 1,
        "mode": "premap_prelaunch_pointer_source_observer_check",
        "passed": not failures,
        "failures": failures,
        "min_seen": int(min_seen),
        "expected_trace_mode": expected_trace_mode,
        "trace_mode": trace_mode,
        "min_sample_count": int(min_sample_count),
        "sample_count": sample_count,
        "min_requested_output_tokens": int(min_requested_output_tokens),
        "requested_output_token_count": requested_output_token_count,
        "live_config_without_router_recorder_enabled": live_config_enabled,
        "prelaunch_pointer_source_canary_enabled": canary_enabled,
        "live_handoff_enabled": live_enabled,
        "live_consumer_connected": live_consumer_connected,
        "kernel_arg_pass_enabled": kernel_arg_pass_enabled,
        "real_kernel_arg_mutation_enabled": real_mutation_enabled,
        "producer_gpu_assignment_envelope_enabled": producer_envelope_enabled,
        "observer_seen": observer_seen,
        "observer_available": observer_available,
        "observer_unavailable": observer_unavailable,
        "observer_vllm_device": observer_vllm_device,
        "observer_non_device": observer_non_device,
        "zero_counter_values": {key: int_values[key] for key in ZERO_INT_KEYS},
        "live_mutation_counter_values": live_mutation_counter_values,
        "allowed_nonzero_live_mutation_counter_keys": sorted(
            ALLOWED_NONZERO_LIVE_MUTATION_COUNTER_KEYS
        ),
        "handoff_bool_values": handoff_bool_values,
        "allowed_true_handoff_bool_keys": sorted(ALLOWED_TRUE_HANDOFF_BOOL_KEYS),
        "required_bool_values": bool_values,
        "required_int_values": int_values,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--performance-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--min-seen", type=int, default=1)
    parser.add_argument("--expected-trace-mode", default=None)
    parser.add_argument("--min-sample-count", type=int, default=0)
    parser.add_argument("--min-requested-output-tokens", type=int, default=0)
    args = parser.parse_args()

    payload = json.loads(args.performance_json.read_text())
    result = check_premap_prelaunch_pointer_source_observer(
        payload,
        min_seen=int(args.min_seen),
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
