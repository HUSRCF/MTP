from __future__ import annotations

import json

from scripts import check_premap_payload_cache_online_native_producer_boundary as checker


def _native_passed() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "native_graph_replay": True,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "packet_count": 8,
        "issue_candidate_count": 48,
        "expected_issue_candidate_count": 48,
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


def _online_capture_only() -> dict[str, object]:
    return {
        "passed": False,
        "ok": False,
        "failures": [
            "graph_visible_producer_contract_not_passed",
            "graph_visible_producer_capture_once_per_layer_suspected",
            "graph_visible_producer_replay_updates_not_complete",
        ],
        "embedded_graph_visible_contract_enabled": True,
        "embedded_graph_visible_contract_present": True,
        "embedded_graph_visible_contract_capture_once_per_layer_suspected": True,
        "embedded_graph_visible_contract_replay_update_status": (
            "capture_once_per_layer_no_replay_updates"
        ),
        "embedded_inside_graph_boundary_contract_passed": False,
        "contract_boundary": "online_inside_graph_tensor_producer",
        "transition_state_on_device": True,
        "issue_generation_on_device": True,
        "python_transition_skipped": True,
        "native_runtime": False,
        "inprocess_native_op": False,
        "post_export_native_replay": False,
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


def test_online_native_producer_boundary_gap_accepts_expected_gap(tmp_path):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    native_path.write_text(json.dumps(_native_passed()), encoding="utf-8")
    online_path.write_text(json.dumps(_online_capture_only()), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is True
    assert payload["ready_for_inprocess_native_op_work"] is True
    assert payload["ready_for_lab_runtime_gate"] is False
    assert payload["runtime_passed"] is False
    assert payload["lab_gate_passed"] is False
    assert payload["native_graph_replay_passed"] is True
    assert payload["online_tensor_producer_passed"] is False
    assert payload["online_capture_once_per_layer_suspected"] is True
    assert payload["payload_bytes"] == 0
    assert payload["passed_to_kernel"] is False


def test_online_native_producer_boundary_gap_rejects_online_pass(tmp_path):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.json"
    online = _online_capture_only()
    online["passed"] = True
    online["ok"] = True
    online["embedded_graph_visible_contract_capture_once_per_layer_suspected"] = False
    online["embedded_graph_visible_contract_replay_update_status"] = (
        "complete_replay_updates_observed"
    )
    native_path.write_text(json.dumps(_native_passed()), encoding="utf-8")
    online_path.write_text(json.dumps(online), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "online_contract_unexpectedly_passed" in payload["failures"]
    assert "online_capture_once_not_reported" in payload["failures"]
    assert "online_replay_status_not_capture_only" in payload["failures"]


def test_online_native_producer_boundary_gap_rejects_online_kernel_arg_pass(tmp_path):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    online = _online_capture_only()
    online["kernel_arg_pass"] = True
    native_path.write_text(json.dumps(_native_passed()), encoding="utf-8")
    online_path.write_text(json.dumps(online), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "online_kernel_arg_pass_not_false" in payload["failures"]


def test_online_native_producer_boundary_gap_rejects_online_full_safety_forgery(
    tmp_path,
):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    online = _online_capture_only()
    forged_fields = (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "current_wna16_arg_compatible",
    )
    for field in forged_fields:
        online[field] = True
    native_path.write_text(json.dumps(_native_passed()), encoding="utf-8")
    online_path.write_text(json.dumps(online), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    for field in forged_fields:
        assert f"online_{field}_not_false" in payload["failures"]


def test_online_native_producer_boundary_gap_rejects_masked_kernel_arg_source_failure(
    tmp_path,
):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    online = _online_capture_only()
    online["failures"] = [
        *online["failures"],
        "kernel_arg_pass_missing",
    ]
    native_path.write_text(json.dumps(_native_passed()), encoding="utf-8")
    online_path.write_text(json.dumps(online), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "online_kernel_arg_pass_source_contract_failure" in payload["failures"]
    assert "kernel_arg_pass_missing" in payload["online_contract_failures"]


def test_online_native_producer_boundary_gap_rejects_missing_online_prerequisite(
    tmp_path,
):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    online = _online_capture_only()
    online["transition_state_on_device"] = False
    native_path.write_text(json.dumps(_native_passed()), encoding="utf-8")
    online_path.write_text(json.dumps(online), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "online_transition_state_on_device_mismatch" in payload["failures"]


def test_online_native_producer_boundary_gap_rejects_native_payload_transfer(
    tmp_path,
):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    native = _native_passed()
    native["payload_transfer_enabled"] = True
    native_path.write_text(json.dumps(native), encoding="utf-8")
    online_path.write_text(json.dumps(_online_capture_only()), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "native_payload_transfer_enabled_mismatch" in payload["failures"]


def test_online_native_producer_boundary_gap_rejects_native_kernel_arg_allowed(
    tmp_path,
):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    native = _native_passed()
    native["kernel_arg_pass_allowed"] = True
    native_path.write_text(json.dumps(native), encoding="utf-8")
    online_path.write_text(json.dumps(_online_capture_only()), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "native_kernel_arg_pass_allowed_mismatch" in payload["failures"]


def test_online_native_producer_boundary_gap_rejects_missing_native_kernel_arg_allowed(
    tmp_path,
):
    native_path = tmp_path / "native.json"
    online_path = tmp_path / "online.failed.json"
    native = _native_passed()
    native.pop("kernel_arg_pass_allowed")
    native_path.write_text(json.dumps(native), encoding="utf-8")
    online_path.write_text(json.dumps(_online_capture_only()), encoding="utf-8")

    payload = checker.check_boundary_gap(
        native_graph_replay_json=native_path,
        online_inside_graph_contract_json=online_path,
    )

    assert payload["passed"] is False
    assert "native_kernel_arg_pass_allowed_mismatch" in payload["failures"]
