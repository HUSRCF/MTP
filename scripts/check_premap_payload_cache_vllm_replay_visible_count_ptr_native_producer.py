#!/usr/bin/env python3
"""Validate the count-pointer vLLM replay-visible native producer path.

The broader vLLM replay-visible producer checker intentionally accepts both the
legacy host-scalar update ABI and the newer device count-pointer update ABI.
This stricter checker is the production-like producer boundary: the current
expert row and current-count scalar must both be device-side inputs, while the
native session generates issue candidates without payload movement or WNA16
kernel argument mutation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import check_premap_payload_cache_vllm_replay_visible_native_producer as base


CONTRACT_MODE = "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract"
CONTRACT_BOUNDARY = "inprocess_vllm_prelaunch_native_count_ptr_producer_op"


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _matches_exact(value: Any, expected: Any) -> bool:
    return type(value) is type(expected) and value == expected


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


NOOP_SAFETY_FIELDS: tuple[tuple[str, object], ...] = (
    ("payload_bytes", 0),
    ("ready", False),
    ("payload_transfer_enabled", False),
    ("payload_deref_allowed", False),
    ("ready_credit", False),
    ("ready_before_demand_credit", False),
    ("real_ready_credit_granted", False),
    ("kernel_arg_pass", False),
    ("kernel_arg_pass_allowed", False),
    ("passed_to_kernel", False),
    ("changes_kernel_launch_args", False),
    ("current_wna16_arg_compatible", False),
    ("uses_current_wna16_args", False),
    ("passes_current_wna16_args", False),
    ("measures_tpot", False),
    ("measures_vllm_latency", False),
)


def check_contract(payload: dict[str, Any]) -> dict[str, Any]:
    base_result = base.check_contract(payload)
    failures = [f"base:{failure}" for failure in base_result.get("failures", [])]

    expected_packet_count = _int_metric(payload, "expected_packet_count")
    packet_count = _int_metric(payload, "packet_count")
    prelaunch_probe_count = _int_metric(payload, "prelaunch_probe_count")
    device_tensor_count = _int_metric(
        payload,
        "prelaunch_current_count_device_tensor_count",
    )
    device_scalar_int32_count = _int_metric(
        payload,
        "prelaunch_current_count_device_scalar_int32_count",
    )
    host_scalar_count = _int_metric(
        payload,
        "prelaunch_current_count_host_scalar_available_count",
    )
    count_ptr_ready_count = _int_metric(
        payload,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count",
    )
    count_ptr_blocked_count = _int_metric(
        payload,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count",
    )
    legacy_ready_count = _int_metric(payload, "prelaunch_abi_ready_count")
    legacy_blocked_count = _int_metric(payload, "prelaunch_abi_blocked_count")

    if base_result.get("passed") is not True:
        failures.append("base_contract_not_passed")
    if expected_packet_count is None or expected_packet_count <= 0:
        failures.append("expected_packet_count_invalid")
    if packet_count != expected_packet_count:
        failures.append("packet_count_mismatch")
    if prelaunch_probe_count != expected_packet_count:
        failures.append("prelaunch_probe_count_mismatch")
    if device_tensor_count != expected_packet_count:
        failures.append("device_count_tensor_count_mismatch")
    if device_scalar_int32_count != expected_packet_count:
        failures.append("device_count_scalar_int32_count_mismatch")
    if host_scalar_count != 0:
        failures.append("host_scalar_count_unexpectedly_available")
    if count_ptr_ready_count != expected_packet_count:
        failures.append("count_ptr_ready_count_mismatch")
    if count_ptr_blocked_count != 0:
        failures.append("count_ptr_blocked_count_nonzero")
    if payload.get("prelaunch_native_session_update_count_ptr_v1_abi_ready") is not True:
        failures.append("count_ptr_abi_ready_not_true")
    if payload.get("prelaunch_native_session_update_v1_abi_ready") is not False:
        failures.append("legacy_host_scalar_abi_unexpectedly_ready")
    if legacy_ready_count != 0:
        failures.append("legacy_host_scalar_ready_count_nonzero")
    if legacy_blocked_count is None or legacy_blocked_count < 0:
        failures.append("legacy_host_scalar_blocked_count_invalid")
    if payload.get("prelaunch_last_current_count_source_kind") != (
        "num_tokens_post_padded_device_tensor"
    ):
        failures.append("current_count_source_kind_mismatch")
    if payload.get("prelaunch_last_count_ptr_block_reason") is not None:
        failures.append("count_ptr_last_block_reason_not_none")
    if payload.get("current_expert_ptr_source_kind") not in {
        "vllm_prelaunch_device_tensor",
        "vllm_prelaunch_native_device_tensor",
    }:
        failures.append("current_expert_ptr_source_kind_mismatch")
    if payload.get("python_transition_skipped") is not True:
        failures.append("python_transition_not_skipped")
    if payload.get("native_runtime") is not True:
        failures.append("native_runtime_not_true")
    if payload.get("inprocess_native_op") is not True:
        failures.append("inprocess_native_op_not_true")
    if payload.get("vllm_replay_visible") is not True:
        failures.append("vllm_replay_visible_not_true")
    for key, expected in NOOP_SAFETY_FIELDS:
        if not _matches_exact(payload.get(key), expected):
            failures.append(f"{key}_mismatch")

    passed = not failures
    result = {
        "ok": passed,
        "passed": passed,
        "failures": failures,
        "mode": CONTRACT_MODE,
        "contract_boundary": CONTRACT_BOUNDARY,
        "input_mode": payload.get("mode"),
        "input_contract_boundary": payload.get("contract_boundary"),
        "base_contract_passed": bool(base_result.get("passed")),
        "expected_packet_count": int(expected_packet_count or 0),
        "packet_count": int(packet_count or 0),
        "prelaunch_probe_count": int(prelaunch_probe_count or 0),
        "count_ptr_ready_count": int(count_ptr_ready_count or 0),
        "count_ptr_blocked_count": int(count_ptr_blocked_count or 0),
        "device_count_tensor_count": int(device_tensor_count or 0),
        "device_count_scalar_int32_count": int(device_scalar_int32_count or 0),
        "host_scalar_count": int(host_scalar_count or 0),
        "legacy_host_scalar_ready_count": int(legacy_ready_count or 0),
        "legacy_host_scalar_blocked_count": int(legacy_blocked_count or 0),
        "current_count_source_kind": payload.get(
            "prelaunch_last_current_count_source_kind"
        ),
        "current_expert_ptr_source_kind": payload.get(
            "current_expert_ptr_source_kind"
        ),
        "python_transition_skipped": bool(payload.get("python_transition_skipped")),
        "native_runtime": bool(payload.get("native_runtime")),
        "inprocess_native_op": bool(payload.get("inprocess_native_op")),
        "vllm_replay_visible": bool(payload.get("vllm_replay_visible")),
        "ready_for_payload_cache_runtime_lab_gate": bool(passed),
        "next_boundary": "production_like_payload_cache_manager_or_payload_runtime_canary",
    }
    for key, expected in NOOP_SAFETY_FIELDS:
        result[key] = payload.get(key) if _matches_exact(payload.get(key), expected) else payload.get(key)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    result = check_contract(_load_json(args.input_json))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
