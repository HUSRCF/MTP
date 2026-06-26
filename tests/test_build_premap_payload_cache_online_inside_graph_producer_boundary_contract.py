from __future__ import annotations

import json

from scripts import (
    build_premap_payload_cache_online_inside_graph_producer_boundary_contract
    as boundary_contract,
)


PREFIX = "runtime_shadow_premap_payload_cache_direct_"
GRAPH_PREFIX = f"{PREFIX}graph_visible_producer_contract_"
BOUNDARY_PREFIX = f"{PREFIX}online_inside_graph_producer_boundary_contract_"


def _performance_summary() -> dict[str, object]:
    return {
        f"{GRAPH_PREFIX}enabled": True,
        f"{GRAPH_PREFIX}present": True,
        f"{GRAPH_PREFIX}passed": True,
        f"{GRAPH_PREFIX}capture_once_per_layer_suspected": False,
        f"{GRAPH_PREFIX}replay_update_status": "complete_replay_updates_observed",
        f"{GRAPH_PREFIX}observed_packet_count": 8,
        f"{GRAPH_PREFIX}expected_packet_count": 8,
        f"{GRAPH_PREFIX}observed_previous_nonempty_packet_count": 6,
        f"{GRAPH_PREFIX}expected_previous_nonempty_packet_count": 6,
        f"{GRAPH_PREFIX}observed_issue_candidate_count": 12,
        f"{GRAPH_PREFIX}expected_issue_candidate_count": 12,
        f"{GRAPH_PREFIX}last_issue_candidate_count": 2,
        f"{GRAPH_PREFIX}last_issue_candidate_first_expert": 1,
        f"{GRAPH_PREFIX}last_issue_candidate_last_expert": 7,
        f"{GRAPH_PREFIX}issue_candidate_expert_sum": 42,
        f"{BOUNDARY_PREFIX}passed": True,
        f"{BOUNDARY_PREFIX}failures": [],
        f"{BOUNDARY_PREFIX}contract_boundary": "online_inside_graph_tensor_producer",
        f"{BOUNDARY_PREFIX}transition_state_on_device": True,
        f"{BOUNDARY_PREFIX}issue_generation_on_device": True,
        f"{BOUNDARY_PREFIX}python_transition_skipped": True,
        f"{BOUNDARY_PREFIX}native_runtime": False,
        f"{BOUNDARY_PREFIX}inprocess_native_op": False,
        f"{BOUNDARY_PREFIX}post_export_native_replay": False,
        f"{BOUNDARY_PREFIX}payload_bytes": 0,
        f"{BOUNDARY_PREFIX}payload_transfer_enabled": False,
        f"{BOUNDARY_PREFIX}payload_deref_allowed": False,
        f"{BOUNDARY_PREFIX}ready_credit": False,
        f"{BOUNDARY_PREFIX}ready_before_demand_credit": False,
        f"{BOUNDARY_PREFIX}real_ready_credit_granted": False,
        f"{BOUNDARY_PREFIX}kernel_arg_pass": False,
        f"{BOUNDARY_PREFIX}kernel_arg_pass_allowed": False,
        f"{BOUNDARY_PREFIX}passed_to_kernel": False,
        f"{BOUNDARY_PREFIX}changes_kernel_launch_args": False,
        f"{BOUNDARY_PREFIX}current_wna16_arg_compatible": False,
        f"{BOUNDARY_PREFIX}uses_current_wna16_args": False,
        f"{BOUNDARY_PREFIX}passes_current_wna16_args": False,
        f"{BOUNDARY_PREFIX}measures_tpot": False,
        f"{BOUNDARY_PREFIX}measures_vllm_latency": False,
    }


def test_inside_graph_boundary_contract_builder_accepts_valid_summary(tmp_path):
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(
        json.dumps(_performance_summary()),
        encoding="utf-8",
    )

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is True
    assert payload["ok"] is True
    assert payload["failures"] == []
    assert payload["mode"] == (
        "payload_cache_online_inside_graph_producer_boundary_contract"
    )
    assert payload["contract_boundary"] == "online_inside_graph_tensor_producer"
    assert payload["transition_state_on_device"] is True
    assert payload["issue_generation_on_device"] is True
    assert payload["python_transition_skipped"] is True
    assert payload["native_runtime"] is False
    assert payload["inprocess_native_op"] is False
    assert payload["post_export_native_replay"] is False
    assert payload["payload_bytes"] == 0
    assert payload["payload_transfer_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["current_wna16_arg_compatible"] is False


def test_inside_graph_boundary_contract_builder_rejects_python_transition(tmp_path):
    summary = _performance_summary()
    summary[f"{BOUNDARY_PREFIX}python_transition_skipped"] = False
    summary[f"{BOUNDARY_PREFIX}passed"] = False
    summary[f"{BOUNDARY_PREFIX}failures"] = [
        "python_transition_extraction_not_skipped"
    ]
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is False
    assert payload["ok"] is False
    assert "inside_graph_boundary_contract_not_passed" in payload["failures"]
    assert "inside_graph_boundary_failures_not_empty" in payload["failures"]
    assert "python_transition_not_skipped" in payload["failures"]


def test_inside_graph_boundary_contract_builder_rejects_missing_kernel_arg_pass(
    tmp_path,
):
    summary = _performance_summary()
    del summary[f"{BOUNDARY_PREFIX}kernel_arg_pass"]
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is False
    assert payload["ok"] is False
    assert "kernel_arg_pass_missing" in payload["failures"]
    assert payload["kernel_arg_pass"] is False


def test_inside_graph_boundary_contract_builder_rejects_kernel_arg_pass_true(
    tmp_path,
):
    summary = _performance_summary()
    summary[f"{BOUNDARY_PREFIX}kernel_arg_pass"] = True
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is False
    assert payload["ok"] is False
    assert "kernel_arg_pass_enabled" in payload["failures"]
    assert payload["kernel_arg_pass"] is False


def test_inside_graph_boundary_contract_builder_rejects_full_safety_field_forgery(
    tmp_path,
):
    summary = _performance_summary()
    forged_fields = (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "current_wna16_arg_compatible",
        "measures_tpot",
        "measures_vllm_latency",
    )
    for field in forged_fields:
        summary[f"{BOUNDARY_PREFIX}{field}"] = True
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is False
    for field in forged_fields:
        assert f"{field}_enabled" in payload["failures"]
        assert payload[field] is False


def test_inside_graph_boundary_contract_builder_rejects_missing_safety_field(
    tmp_path,
):
    summary = _performance_summary()
    del summary[f"{BOUNDARY_PREFIX}payload_transfer_enabled"]
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is False
    assert "payload_transfer_enabled_missing" in payload["failures"]


def test_inside_graph_boundary_contract_builder_rejects_capture_only_replay(
    tmp_path,
):
    summary = _performance_summary()
    summary[f"{GRAPH_PREFIX}passed"] = False
    summary[f"{GRAPH_PREFIX}capture_once_per_layer_suspected"] = True
    summary[f"{GRAPH_PREFIX}replay_update_status"] = (
        "capture_once_per_layer_no_replay_updates"
    )
    summary[f"{BOUNDARY_PREFIX}passed"] = False
    summary[f"{BOUNDARY_PREFIX}failures"] = [
        "graph_visible_producer_contract_not_passed"
    ]
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is False
    assert (
        "graph_visible_producer_capture_once_per_layer_suspected"
        in payload["failures"]
    )
    assert "graph_visible_producer_replay_updates_not_complete" in payload["failures"]
    assert payload[
        "embedded_graph_visible_contract_capture_once_per_layer_suspected"
    ] is True
    assert payload["embedded_graph_visible_contract_replay_update_status"] == (
        "capture_once_per_layer_no_replay_updates"
    )


def test_inside_graph_boundary_contract_builder_accepts_empty_issue_candidates(
    tmp_path,
):
    summary = _performance_summary()
    summary[f"{GRAPH_PREFIX}observed_previous_nonempty_packet_count"] = 0
    summary[f"{GRAPH_PREFIX}expected_previous_nonempty_packet_count"] = 0
    summary[f"{GRAPH_PREFIX}observed_issue_candidate_count"] = 0
    summary[f"{GRAPH_PREFIX}expected_issue_candidate_count"] = 0
    summary[f"{GRAPH_PREFIX}last_issue_candidate_count"] = 0
    summary[f"{GRAPH_PREFIX}last_issue_candidate_first_expert"] = -1
    summary[f"{GRAPH_PREFIX}last_issue_candidate_last_expert"] = -1
    summary[f"{GRAPH_PREFIX}issue_candidate_expert_sum"] = 0
    summary_path = tmp_path / "performance_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    payload = boundary_contract.build_contract(summary_path)

    assert payload["passed"] is True
    assert payload["failures"] == []
    assert payload["graph_observed_issue_candidate_count"] == 0
    assert payload["graph_expected_issue_candidate_count"] == 0
