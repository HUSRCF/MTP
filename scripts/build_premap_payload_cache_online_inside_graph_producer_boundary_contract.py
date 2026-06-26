#!/usr/bin/env python3
"""Materialize the online inside-graph producer boundary contract.

This contract is for the payload-cache producer path where transition state and
issue-generation summaries are maintained in graph-visible device tensors.  It
is deliberately separate from the older online stream contract, because the
strict inside-graph mode may skip Python prelaunch packet extraction entirely.

The artifact remains payloadless and does not claim an in-process native HIP op:
- no payload bytes are moved,
- no ready credit is granted,
- no current WNA16 kernel arguments are passed or mutated,
- native_runtime/inprocess_native_op remain false until a real online native op
  exists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PREFIX = "runtime_shadow_premap_payload_cache_direct_"
GRAPH_PREFIX = f"{PREFIX}graph_visible_producer_contract_"
BOUNDARY_PREFIX = f"{PREFIX}online_inside_graph_producer_boundary_contract_"
BOUNDARY_REQUIRED_FALSE_FIELDS = (
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass_allowed",
    "current_wna16_arg_compatible",
    "measures_tpot",
    "measures_vllm_latency",
)


def _load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _bool_value(summary: dict[str, Any], key: str, default: bool = False) -> bool:
    value = summary.get(key, default)
    return bool(value)


def _int_value(summary: dict[str, Any], key: str, default: int = 0) -> int:
    value = summary.get(key, default)
    if isinstance(value, bool):
        return int(default)
    return int(value)


def _required_false_value(summary: dict[str, Any], key: str) -> tuple[bool, str | None]:
    if key not in summary:
        return False, "missing"
    if summary.get(key) is not False:
        return False, "enabled"
    return False, None


def build_contract(performance_summary: Path) -> dict[str, Any]:
    summary = _load_json_object(performance_summary)
    failures: list[str] = []

    graph_passed = _bool_value(summary, f"{GRAPH_PREFIX}passed")
    graph_enabled = _bool_value(summary, f"{GRAPH_PREFIX}enabled")
    graph_present = _bool_value(summary, f"{GRAPH_PREFIX}present")
    graph_capture_once_suspected = _bool_value(
        summary,
        f"{GRAPH_PREFIX}capture_once_per_layer_suspected",
    )
    graph_replay_update_status = str(
        summary.get(f"{GRAPH_PREFIX}replay_update_status", "missing")
    )
    boundary_passed = _bool_value(summary, f"{BOUNDARY_PREFIX}passed")
    boundary_failures = summary.get(f"{BOUNDARY_PREFIX}failures")
    if boundary_failures is None:
        boundary_failures = []
    if not isinstance(boundary_failures, list):
        boundary_failures = ["boundary_failures_not_list"]

    transition_state_on_device = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}transition_state_on_device",
    )
    issue_generation_on_device = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}issue_generation_on_device",
    )
    python_transition_skipped = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}python_transition_skipped",
    )
    native_runtime = _bool_value(summary, f"{BOUNDARY_PREFIX}native_runtime")
    inprocess_native_op = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}inprocess_native_op",
    )
    post_export_native_replay = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}post_export_native_replay",
    )
    payload_bytes = _int_value(summary, f"{BOUNDARY_PREFIX}payload_bytes", -1)
    ready_credit = _bool_value(summary, f"{BOUNDARY_PREFIX}ready_credit", True)
    kernel_arg_pass, kernel_arg_pass_error = _required_false_value(
        summary,
        f"{BOUNDARY_PREFIX}kernel_arg_pass",
    )
    passed_to_kernel = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}passed_to_kernel",
        True,
    )
    changes_kernel_launch_args = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}changes_kernel_launch_args",
        True,
    )
    uses_current_wna16_args = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}uses_current_wna16_args",
        True,
    )
    passes_current_wna16_args = _bool_value(
        summary,
        f"{BOUNDARY_PREFIX}passes_current_wna16_args",
        True,
    )
    required_false_values: dict[str, bool] = {}
    required_false_errors: dict[str, str | None] = {}
    for field in BOUNDARY_REQUIRED_FALSE_FIELDS:
        value, error = _required_false_value(summary, f"{BOUNDARY_PREFIX}{field}")
        required_false_values[field] = bool(value)
        required_false_errors[field] = error

    if not graph_enabled:
        failures.append("graph_visible_producer_disabled")
    if not graph_present:
        failures.append("graph_visible_producer_state_missing")
    if not graph_passed:
        failures.append("graph_visible_producer_contract_not_passed")
    if graph_capture_once_suspected:
        failures.append("graph_visible_producer_capture_once_per_layer_suspected")
    if graph_replay_update_status != "complete_replay_updates_observed":
        failures.append("graph_visible_producer_replay_updates_not_complete")
    if not boundary_passed:
        failures.append("inside_graph_boundary_contract_not_passed")
    if boundary_failures not in ([], None):
        failures.append("inside_graph_boundary_failures_not_empty")
    if not transition_state_on_device:
        failures.append("transition_state_not_on_device")
    if not issue_generation_on_device:
        failures.append("issue_generation_not_on_device")
    if not python_transition_skipped:
        failures.append("python_transition_not_skipped")
    if native_runtime:
        failures.append("native_runtime_unexpectedly_enabled")
    if inprocess_native_op:
        failures.append("inprocess_native_op_unexpectedly_enabled")
    if post_export_native_replay:
        failures.append("post_export_native_replay_unexpectedly_enabled")
    if payload_bytes != 0:
        failures.append("payload_bytes_nonzero")
    if ready_credit:
        failures.append("ready_credit_enabled")
    if kernel_arg_pass_error == "missing":
        failures.append("kernel_arg_pass_missing")
    elif kernel_arg_pass_error:
        failures.append("kernel_arg_pass_enabled")
    for field, error in required_false_errors.items():
        if error == "missing":
            failures.append(f"{field}_missing")
        elif error:
            failures.append(f"{field}_enabled")
    if passed_to_kernel:
        failures.append("passed_to_kernel_enabled")
    if changes_kernel_launch_args:
        failures.append("changes_kernel_launch_args_enabled")
    if uses_current_wna16_args:
        failures.append("uses_current_wna16_args_enabled")
    if passes_current_wna16_args:
        failures.append("passes_current_wna16_args_enabled")

    graph_observed_issue_count = _int_value(
        summary,
        f"{GRAPH_PREFIX}observed_issue_candidate_count",
    )
    graph_expected_issue_count = _int_value(
        summary,
        f"{GRAPH_PREFIX}expected_issue_candidate_count",
    )
    if graph_observed_issue_count != graph_expected_issue_count:
        failures.append("observed_issue_candidate_count_mismatch")

    passed = not failures
    return {
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "mode": "payload_cache_online_inside_graph_producer_boundary_contract",
        "performance_summary": str(performance_summary),
        "embedded_graph_visible_contract_passed": bool(graph_passed),
        "embedded_graph_visible_contract_enabled": bool(graph_enabled),
        "embedded_graph_visible_contract_present": bool(graph_present),
        "embedded_graph_visible_contract_capture_once_per_layer_suspected": bool(
            graph_capture_once_suspected
        ),
        "embedded_graph_visible_contract_replay_update_status": str(
            graph_replay_update_status
        ),
        "embedded_inside_graph_boundary_contract_passed": bool(boundary_passed),
        "embedded_inside_graph_boundary_contract_failures": boundary_failures,
        "contract_boundary": str(
            summary.get(
                f"{BOUNDARY_PREFIX}contract_boundary",
                "online_inside_graph_tensor_producer",
            )
        ),
        "transition_state_on_device": bool(transition_state_on_device),
        "issue_generation_on_device": bool(issue_generation_on_device),
        "python_transition_skipped": bool(python_transition_skipped),
        "graph_observed_packet_count": _int_value(
            summary,
            f"{GRAPH_PREFIX}observed_packet_count",
        ),
        "graph_expected_packet_count": _int_value(
            summary,
            f"{GRAPH_PREFIX}expected_packet_count",
        ),
        "graph_observed_previous_nonempty_packet_count": _int_value(
            summary,
            f"{GRAPH_PREFIX}observed_previous_nonempty_packet_count",
        ),
        "graph_expected_previous_nonempty_packet_count": _int_value(
            summary,
            f"{GRAPH_PREFIX}expected_previous_nonempty_packet_count",
        ),
        "graph_observed_issue_candidate_count": int(graph_observed_issue_count),
        "graph_expected_issue_candidate_count": int(graph_expected_issue_count),
        "graph_last_issue_candidate_count": _int_value(
            summary,
            f"{GRAPH_PREFIX}last_issue_candidate_count",
        ),
        "graph_last_issue_candidate_first_expert": _int_value(
            summary,
            f"{GRAPH_PREFIX}last_issue_candidate_first_expert",
            -1,
        ),
        "graph_last_issue_candidate_last_expert": _int_value(
            summary,
            f"{GRAPH_PREFIX}last_issue_candidate_last_expert",
            -1,
        ),
        "graph_issue_candidate_expert_sum": _int_value(
            summary,
            f"{GRAPH_PREFIX}issue_candidate_expert_sum",
        ),
        "native_runtime": False,
        "inprocess_native_op": False,
        "post_export_native_replay": False,
        "payload_bytes": 0,
        "payload_transfer_enabled": required_false_values["payload_transfer_enabled"],
        "payload_deref_allowed": required_false_values["payload_deref_allowed"],
        "ready_credit": False,
        "ready_before_demand_credit": required_false_values[
            "ready_before_demand_credit"
        ],
        "real_ready_credit_granted": required_false_values[
            "real_ready_credit_granted"
        ],
        "kernel_arg_pass": bool(kernel_arg_pass),
        "kernel_arg_pass_allowed": required_false_values["kernel_arg_pass_allowed"],
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": required_false_values[
            "current_wna16_arg_compatible"
        ],
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": required_false_values["measures_tpot"],
        "measures_vllm_latency": required_false_values["measures_vllm_latency"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--performance-summary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = build_contract(args.performance_summary_json)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
