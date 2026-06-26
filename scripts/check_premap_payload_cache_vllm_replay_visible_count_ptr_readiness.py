#!/usr/bin/env python3
"""Check future vLLM replay-visible native count-pointer readiness.

This checker is intentionally separate from
``check_premap_payload_cache_vllm_replay_visible_native_producer.py``.  The
existing positive contract validates the current host-scalar
``session_update_v1`` boundary.  This checker validates only the observational
readiness surface for the future ``session_update_count_ptr_v1`` ABI where
``num_tokens_post_padded`` remains a device scalar int32 pointer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONTRACT_MODE = "payload_cache_vllm_replay_visible_native_count_ptr_readiness"
CONTRACT_BOUNDARY = "future_session_update_count_ptr_v1_prelaunch_probe"
INPUT_MODE = "payload_cache_vllm_replay_visible_native_producer_contract"
INPUT_CONTRACT_BOUNDARY = "inprocess_vllm_replay_visible_native_producer_op"
INPUT_SOURCE_KIND = "vllm_prelaunch_inprocess_native_producer"
INPUT_EXPERT_PTR_SOURCE_KINDS = {
    "vllm_prelaunch_device_tensor",
    "vllm_prelaunch_native_device_tensor",
}
SAFETY_FALSE_FIELDS = (
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def check_contract(payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    payload_bytes = _int_metric(payload, "payload_bytes")
    expected_packet_count = _int_metric(payload, "expected_packet_count")
    prelaunch_probe_count = _int_metric(payload, "prelaunch_probe_count")
    prelaunch_device_tensor_count = _int_metric(payload, "prelaunch_device_tensor_count")
    prelaunch_int32_count = _int_metric(payload, "prelaunch_int32_count")
    prelaunch_host_tensor_count = _int_metric(payload, "prelaunch_host_tensor_count")
    prelaunch_dtype_mismatch_count = _int_metric(
        payload,
        "prelaunch_dtype_mismatch_count",
    )
    prelaunch_current_count_host_scalar_available_count = _int_metric(
        payload,
        "prelaunch_current_count_host_scalar_available_count",
    )
    prelaunch_current_count_device_tensor_count = _int_metric(
        payload,
        "prelaunch_current_count_device_tensor_count",
    )
    prelaunch_current_count_device_scalar_int32_count = _int_metric(
        payload,
        "prelaunch_current_count_device_scalar_int32_count",
    )
    prelaunch_count_ptr_ready_count = _int_metric(
        payload,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count",
    )
    prelaunch_count_ptr_blocked_count = _int_metric(
        payload,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count",
    )
    expected_packet_count_source = payload.get("expected_packet_count_source")
    graph_visible_expected_packet_count_present = payload.get(
        "graph_visible_expected_packet_count_present"
    )
    prelaunch_probe_summary_scope = payload.get("prelaunch_probe_summary_scope")
    prelaunch_probe_summary_run_sample_count = payload.get(
        "prelaunch_probe_summary_run_sample_count"
    )

    if payload.get("mode") != INPUT_MODE:
        failures.append("mode_mismatch")
    if payload.get("contract_boundary") != INPUT_CONTRACT_BOUNDARY:
        failures.append("contract_boundary_mismatch")
    if payload.get("source_kind") != INPUT_SOURCE_KIND:
        failures.append("source_kind_mismatch")
    if payload.get("current_expert_ptr_source_kind") not in INPUT_EXPERT_PTR_SOURCE_KINDS:
        failures.append("current_expert_ptr_source_kind_mismatch")
    if payload.get("source_is_online_stream_contract") is not True:
        failures.append("source_is_online_stream_contract_mismatch")
    if payload.get("source_is_raw_vllm_performance_summary") is not False:
        failures.append("source_is_raw_vllm_performance_summary_mismatch")
    if payload_bytes is None or payload_bytes != 0:
        failures.append("payload_bytes_mismatch")
    for key in SAFETY_FALSE_FIELDS:
        if payload.get(key) is not False:
            failures.append(f"{key}_not_false")
    if expected_packet_count is None or expected_packet_count <= 0:
        failures.append("expected_packet_count_invalid")
    if prelaunch_probe_count is None or prelaunch_probe_count <= 0:
        failures.append("prelaunch_probe_count_invalid")
    elif expected_packet_count is not None and prelaunch_probe_count != expected_packet_count:
        failures.append("prelaunch_probe_count_mismatch")
    for key, value in (
        ("prelaunch_device_tensor_count", prelaunch_device_tensor_count),
        ("prelaunch_int32_count", prelaunch_int32_count),
        (
            "prelaunch_current_count_device_tensor_count",
            prelaunch_current_count_device_tensor_count,
        ),
        (
            "prelaunch_current_count_device_scalar_int32_count",
            prelaunch_current_count_device_scalar_int32_count,
        ),
        (
            "prelaunch_native_session_update_count_ptr_v1_abi_ready_count",
            prelaunch_count_ptr_ready_count,
        ),
    ):
        if value is None or value <= 0:
            failures.append(f"{key}_invalid")
        elif expected_packet_count is not None and value != expected_packet_count:
            failures.append(f"{key}_mismatch")
    if prelaunch_count_ptr_blocked_count is None or prelaunch_count_ptr_blocked_count != 0:
        failures.append(
            "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count_mismatch"
        )
    if prelaunch_host_tensor_count is None or prelaunch_host_tensor_count != 0:
        failures.append("prelaunch_host_tensor_count_mismatch")
    if prelaunch_dtype_mismatch_count is None or prelaunch_dtype_mismatch_count != 0:
        failures.append("prelaunch_dtype_mismatch_count_mismatch")
    if (
        prelaunch_current_count_host_scalar_available_count is None
        or prelaunch_current_count_host_scalar_available_count != 0
    ):
        failures.append(
            "prelaunch_current_count_host_scalar_available_count_mismatch"
        )
    if payload.get("prelaunch_last_count_ptr_block_reason") is not None:
        failures.append("prelaunch_last_count_ptr_block_reason_mismatch")
    if (
        payload.get("prelaunch_last_current_count_source_kind")
        != "num_tokens_post_padded_device_tensor"
    ):
        failures.append("prelaunch_last_current_count_source_kind_mismatch")
    if payload.get("prelaunch_native_session_update_count_ptr_v1_abi_ready") is not True:
        failures.append("prelaunch_native_session_update_count_ptr_v1_abi_ready_mismatch")
    if expected_packet_count_source not in {
        "graph_visible_producer_contract",
        "prelaunch_probe_count",
    }:
        failures.append("expected_packet_count_source_invalid")
    if type(graph_visible_expected_packet_count_present) is not bool:
        failures.append("graph_visible_expected_packet_count_present_invalid")
    if prelaunch_probe_summary_scope not in {
        "recorder_current_window",
        "last_router_sample",
        "run_aggregate",
    }:
        failures.append("prelaunch_probe_summary_scope_invalid")
    if (
        isinstance(prelaunch_probe_summary_run_sample_count, bool)
        or not isinstance(prelaunch_probe_summary_run_sample_count, int)
        or int(prelaunch_probe_summary_run_sample_count) < 0
    ):
        failures.append("prelaunch_probe_summary_run_sample_count_invalid")

    passed = not failures
    return {
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "mode": CONTRACT_MODE,
        "contract_boundary": CONTRACT_BOUNDARY,
        "input_mode": payload.get("mode"),
        "input_contract_boundary": payload.get("contract_boundary"),
        "source_kind": payload.get("source_kind"),
        "expected_packet_count_source": payload.get("expected_packet_count_source"),
        "graph_visible_expected_packet_count_present": payload.get(
            "graph_visible_expected_packet_count_present"
        ),
        "prelaunch_probe_summary_scope": payload.get(
            "prelaunch_probe_summary_scope"
        ),
        "prelaunch_probe_summary_run_sample_count": payload.get(
            "prelaunch_probe_summary_run_sample_count"
        ),
        "prelaunch_last_current_count_source_kind": payload.get(
            "prelaunch_last_current_count_source_kind"
        ),
        "expected_packet_count": int(expected_packet_count or 0),
        "prelaunch_probe_count": int(prelaunch_probe_count or 0),
        "prelaunch_current_count_device_scalar_int32_count": int(
            prelaunch_current_count_device_scalar_int32_count or 0
        ),
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": int(
            prelaunch_count_ptr_ready_count or 0
        ),
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": int(
            prelaunch_count_ptr_blocked_count or 0
        ),
        "ready_for_future_count_ptr_native_session": bool(passed),
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", required=True, type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    result = check_contract(_load_json(args.input_json))
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
