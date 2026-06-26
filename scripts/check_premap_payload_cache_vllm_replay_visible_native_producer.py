#!/usr/bin/env python3
"""Check the future vLLM replay-visible native producer boundary.

This is the positive contract for the next payload-cache producer boundary.
It must only pass when the producer update happens as an in-process native op
from the vLLM online/prelaunch path.  Standalone native replay and the current
capture-once tensor canary are intentionally rejected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONTRACT_MODE = "payload_cache_vllm_replay_visible_native_producer_contract"
CONTRACT_BOUNDARY = "inprocess_vllm_replay_visible_native_producer_op"
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


def _matches_expected(value: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return value is expected
    return value == expected


def check_contract(payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    expected_values = {
        "ok": True,
        "passed": True,
        "failures": [],
        "mode": CONTRACT_MODE,
        "contract_boundary": CONTRACT_BOUNDARY,
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
        "payload_bytes": 0,
    }
    for key, expected in expected_values.items():
        if not _matches_expected(payload.get(key), expected):
            failures.append(f"{key}_mismatch")
    for key in SAFETY_FALSE_FIELDS:
        if payload.get(key) is not False:
            failures.append(f"{key}_not_false")

    packet_count = _int_metric(payload, "packet_count")
    expected_packet_count = _int_metric(payload, "expected_packet_count")
    issue_count = _int_metric(payload, "issue_candidate_count")
    expected_issue_count = _int_metric(payload, "expected_issue_candidate_count")
    update_count = _int_metric(payload, "producer_update_count")
    replay_update_count = _int_metric(payload, "replay_visible_update_count")
    for key, value in (
        ("packet_count", packet_count),
        ("expected_packet_count", expected_packet_count),
        ("issue_candidate_count", issue_count),
        ("expected_issue_candidate_count", expected_issue_count),
        ("producer_update_count", update_count),
        ("replay_visible_update_count", replay_update_count),
    ):
        if value is None or value <= 0:
            failures.append(f"{key}_invalid")
    if (
        packet_count is not None
        and expected_packet_count is not None
        and packet_count != expected_packet_count
    ):
        failures.append("packet_count_mismatch")
    if (
        issue_count is not None
        and expected_issue_count is not None
        and issue_count != expected_issue_count
    ):
        failures.append("issue_candidate_count_mismatch")
    if (
        update_count is not None
        and expected_packet_count is not None
        and update_count != expected_packet_count
    ):
        failures.append("producer_update_count_mismatch")
    if (
        replay_update_count is not None
        and expected_packet_count is not None
        and replay_update_count != expected_packet_count
    ):
        failures.append("replay_visible_update_count_mismatch")

    source_kind = payload.get("source_kind")
    if source_kind != "vllm_prelaunch_inprocess_native_producer":
        failures.append("source_kind_mismatch")
    if payload.get("current_expert_ptr_source_kind") not in {
        "vllm_prelaunch_device_tensor",
        "vllm_prelaunch_native_device_tensor",
    }:
        failures.append("current_expert_ptr_source_kind_mismatch")
    if payload.get("source_is_online_stream_contract") is not True:
        failures.append("source_is_online_stream_contract_mismatch")
    if payload.get("source_is_raw_vllm_performance_summary") is not False:
        failures.append("source_is_raw_vllm_performance_summary_mismatch")

    passed = not failures
    return {
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "mode": CONTRACT_MODE,
        "contract_boundary": CONTRACT_BOUNDARY,
        "input_mode": payload.get("mode"),
        "input_contract_boundary": payload.get("contract_boundary"),
        "packet_count": int(packet_count or 0),
        "expected_packet_count": int(expected_packet_count or 0),
        "issue_candidate_count": int(issue_count or 0),
        "expected_issue_candidate_count": int(expected_issue_count or 0),
        "producer_update_count": int(update_count or 0),
        "replay_visible_update_count": int(replay_update_count or 0),
        "ready_for_payload_cache_runtime_lab_gate": bool(passed),
        "next_boundary": "payload_cache_manager_payloadless_ab_or_full_fetch_canary",
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
