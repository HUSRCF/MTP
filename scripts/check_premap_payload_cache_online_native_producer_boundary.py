#!/usr/bin/env python3
"""Check the gap between native replay and online vLLM producer insertion.

This report is intentionally not a lab-pass artifact.  It is a boundary report:
the standalone HIP producer-state stream canary must pass graph replay, while
the current vLLM online tensor producer is expected to fail as capture-only
until a true in-process replay-visible native producer op exists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _is_false(value: Any) -> bool:
    return value is False


def check_boundary_gap(
    *,
    native_graph_replay_json: Path,
    online_inside_graph_contract_json: Path,
) -> dict[str, Any]:
    native = _load_json(native_graph_replay_json)
    online = _load_json(online_inside_graph_contract_json)
    failures: list[str] = []

    native_expected = {
        "passed": True,
        "ok": True,
        "native_graph_replay": True,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_deref_allowed": False,
        "payload_transfer_enabled": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    for key, expected in native_expected.items():
        if native.get(key) != expected:
            failures.append(f"native_{key}_mismatch")
    if native.get("issue_candidate_count") != native.get("expected_issue_candidate_count"):
        failures.append("native_issue_candidate_count_mismatch")
    if not isinstance(native.get("packet_count"), int) or native.get("packet_count", 0) <= 0:
        failures.append("native_packet_count_empty")

    capture_only = (
        online.get("embedded_graph_visible_contract_capture_once_per_layer_suspected")
        is True
    )
    replay_status = online.get("embedded_graph_visible_contract_replay_update_status")
    online_positive_prerequisites = {
        "embedded_graph_visible_contract_enabled": True,
        "embedded_graph_visible_contract_present": True,
        "embedded_inside_graph_boundary_contract_passed": False,
        "transition_state_on_device": True,
        "issue_generation_on_device": True,
        "python_transition_skipped": True,
        "contract_boundary": "online_inside_graph_tensor_producer",
    }
    for key, expected in online_positive_prerequisites.items():
        if online.get(key) != expected:
            failures.append(f"online_{key}_mismatch")
    online_expected_false_fields = (
        "native_runtime",
        "inprocess_native_op",
        "post_export_native_replay",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "payload_transfer_enabled",
        "payload_deref_allowed",
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
    if online.get("passed") is not False or online.get("ok") is not False:
        failures.append("online_contract_unexpectedly_passed")
    if not capture_only:
        failures.append("online_capture_once_not_reported")
    if replay_status != "capture_once_per_layer_no_replay_updates":
        failures.append("online_replay_status_not_capture_only")
    if "graph_visible_producer_replay_updates_not_complete" not in online.get(
        "failures",
        [],
    ):
        failures.append("online_replay_failure_missing")
    online_contract_failures = online.get("failures", [])
    if not isinstance(online_contract_failures, list):
        online_contract_failures = ["online_failures_not_list"]
    if any(
        failure in online_contract_failures
        for failure in ("kernel_arg_pass_missing", "kernel_arg_pass_enabled")
    ):
        failures.append("online_kernel_arg_pass_source_contract_failure")
    if online.get("payload_bytes") != 0:
        failures.append("online_payload_bytes_nonzero")
    for key in online_expected_false_fields:
        if not _is_false(online.get(key)):
            failures.append(f"online_{key}_not_false")

    gap_identified = not failures
    return {
        "passed": gap_identified,
        "ok": gap_identified,
        "mode": "payload_cache_online_native_producer_boundary_gap_report",
        "failures": failures,
        "native_graph_replay_json": str(native_graph_replay_json),
        "online_inside_graph_contract_json": str(online_inside_graph_contract_json),
        "native_graph_replay_passed": native.get("passed") is True,
        "native_persistent_state_on_device": native.get("persistent_state_on_device")
        is True,
        "native_issue_generation_on_device": native.get("issue_generation_on_device")
        is True,
        "native_issue_candidate_count": int(native.get("issue_candidate_count", 0) or 0),
        "native_expected_issue_candidate_count": int(
            native.get("expected_issue_candidate_count", 0) or 0
        ),
        "online_tensor_producer_passed": online.get("passed") is True,
        "online_contract_failures": online_contract_failures,
        "online_capture_once_per_layer_suspected": bool(capture_only),
        "online_replay_update_status": replay_status,
        "ready_for_inprocess_native_op_work": bool(gap_identified),
        "ready_for_lab_runtime_gate": False,
        "runtime_passed": False,
        "lab_gate_passed": False,
        "next_required_boundary": "inprocess_vllm_replay_visible_native_producer_op",
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
    parser.add_argument("--native-graph-replay-json", type=Path, required=True)
    parser.add_argument("--online-inside-graph-contract-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = check_boundary_gap(
        native_graph_replay_json=args.native_graph_replay_json,
        online_inside_graph_contract_json=args.online_inside_graph_contract_json,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
