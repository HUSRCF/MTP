from __future__ import annotations

import json

from scripts import check_premap_payload_cache_native_producer_evidence_ladder as checker


def _runtime_disabled_fields() -> dict[str, object]:
    return {
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _boundary_gap() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_online_native_producer_boundary_gap_report",
        "native_packet_count": 2560,
        "native_issue_candidate_count": 20160,
        "native_expected_issue_candidate_count": 20160,
        "online_graph_expected_packet_count": 2560,
        "online_graph_expected_issue_candidate_count": 20160,
        "online_tensor_producer_passed": False,
        "online_capture_once_per_layer_suspected": True,
        "online_replay_update_status": "capture_once_per_layer_no_replay_updates",
        "ready_for_inprocess_native_op_work": True,
        "ready_for_lab_runtime_gate": False,
        "runtime_passed": False,
        "lab_gate_passed": False,
        "next_required_boundary": "inprocess_vllm_replay_visible_native_producer_op",
        **_runtime_disabled_fields(),
        "payload_bytes": 0,
        "current_wna16_arg_compatible": False,
    }


def _native_graph_replay() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "native_graph_replay": True,
        "inprocess_native_op": True,
        "packet_count": 2560,
        "issue_candidate_count": 20160,
        "payload_bytes": 0,
        **_runtime_disabled_fields(),
    }


def _packet_stream() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "packet_stream_input": True,
        "current_expert_ptr_source": "packet_stream_torch_device_tensor",
        "ready_for_vllm_prelaunch_canary": False,
        **_runtime_disabled_fields(),
    }


def _packet_stream_wrapper() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_producer_state_packet_stream_native_canary",
        "payload_bytes": 0,
        **_runtime_disabled_fields(),
        "native": {
            "passed": True,
            "ok": True,
            "failures": [],
            **_runtime_disabled_fields(),
        },
    }


def _session_contract() -> dict[str, object]:
    return {
        "passed": True,
        "ok": True,
        "failures": [],
        "mode": "payload_cache_producer_state_inprocess_native_session_online_contract",
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "source_kind": "derived_payload_cache_producer_state_stream_online_contract",
        "source_stream_online_contract_passed": True,
        "source_stream_online_contract_failures": [],
        "inprocess_native_op": True,
        "current_expert_ptr_source": "native_generated_device_scratch",
        "current_expert_ptr_source_kind": "native_scratch_smoke",
        "external_current_expert_ptr_source": False,
        "ready_for_vllm_prelaunch_canary": False,
        "payload_bytes": 0,
        **_runtime_disabled_fields(),
    }


def test_native_producer_evidence_ladder_accepts_layered_gap(tmp_path):
    boundary = tmp_path / "boundary.json"
    native = tmp_path / "native.json"
    packet_stream = tmp_path / "packet_stream.json"
    session = tmp_path / "session.json"
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    native.write_text(json.dumps(_native_graph_replay()), encoding="utf-8")
    packet_stream.write_text(json.dumps(_packet_stream()), encoding="utf-8")
    session.write_text(json.dumps(_session_contract()), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        native_graph_replay_json=native,
        packet_stream_native_canary_json=packet_stream,
        session_online_contract_json=session,
    )

    assert payload["passed"] is True
    assert payload["native_issue_candidate_count"] == 20160
    assert payload["native_packet_count"] == 2560
    assert payload["native_graph_replay_passed"] is True
    assert payload["packet_stream_native_canary_passed"] is True
    assert payload["session_online_contract_passed"] is True
    assert payload["online_capture_once_gap_acknowledged"] is True
    assert payload["runtime_ready"] is False
    assert payload["lab_gate_passed"] is False
    assert payload["next_required_boundary"] == (
        "inprocess_vllm_replay_visible_native_producer_op"
    )
    assert payload["payload_bytes"] == 0
    assert payload["kernel_arg_pass"] is False
    assert payload["passed_to_kernel"] is False


def test_native_producer_evidence_ladder_rejects_runtime_passed_gap(tmp_path):
    boundary_payload = _boundary_gap()
    boundary_payload["runtime_passed"] = True
    boundary = tmp_path / "boundary.json"
    boundary.write_text(json.dumps(boundary_payload), encoding="utf-8")

    payload = checker.check_ladder(boundary_gap_json=boundary)

    assert payload["passed"] is False
    assert "boundary_gap_runtime_passed_not_false" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_native_scale_mismatch(tmp_path):
    boundary = tmp_path / "boundary.json"
    native = tmp_path / "native.json"
    native_payload = _native_graph_replay()
    native_payload["issue_candidate_count"] = 48
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    native.write_text(json.dumps(native_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        native_graph_replay_json=native,
    )

    assert payload["passed"] is False
    assert "native_graph_replay_issue_count_mismatch" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_native_failed_payload(tmp_path):
    boundary = tmp_path / "boundary.json"
    native = tmp_path / "native.json"
    native_payload = _native_graph_replay()
    native_payload["ok"] = False
    native_payload["failures"] = ["native_error"]
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    native.write_text(json.dumps(native_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        native_graph_replay_json=native,
    )

    assert payload["passed"] is False
    assert "native_graph_replay_not_passed" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_native_payload_bytes(tmp_path):
    boundary = tmp_path / "boundary.json"
    native = tmp_path / "native.json"
    native_payload = _native_graph_replay()
    native_payload["payload_bytes"] = 4096
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    native.write_text(json.dumps(native_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        native_graph_replay_json=native,
    )

    assert payload["passed"] is False
    assert payload["native_graph_replay_passed"] is False
    assert "native_graph_replay_payload_bytes_nonzero" in payload["failures"]


def test_native_producer_evidence_ladder_accepts_packet_stream_wrapper(tmp_path):
    boundary = tmp_path / "boundary.json"
    packet_stream = tmp_path / "packet_stream.json"
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    packet_stream.write_text(json.dumps(_packet_stream_wrapper()), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        packet_stream_native_canary_json=packet_stream,
    )

    assert payload["passed"] is True
    assert payload["packet_stream_native_canary_passed"] is True


def test_native_producer_evidence_ladder_rejects_packet_stream_wrapper_live_side_effect(
    tmp_path,
):
    boundary = tmp_path / "boundary.json"
    packet_stream = tmp_path / "packet_stream.json"
    packet_payload = _packet_stream_wrapper()
    packet_payload["payload_transfer_enabled"] = True
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    packet_stream.write_text(json.dumps(packet_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        packet_stream_native_canary_json=packet_stream,
    )

    assert payload["passed"] is False
    assert "packet_stream_payload_transfer_enabled_not_false" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_packet_stream_payload_bytes(
    tmp_path,
):
    boundary = tmp_path / "boundary.json"
    packet_stream = tmp_path / "packet_stream.json"
    packet_payload = _packet_stream()
    packet_payload["payload_bytes"] = 4096
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    packet_stream.write_text(json.dumps(packet_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        packet_stream_native_canary_json=packet_stream,
    )

    assert payload["passed"] is False
    assert payload["packet_stream_native_canary_passed"] is False
    assert "packet_stream_payload_bytes_nonzero" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_packet_wrapper_missing_native_failures(
    tmp_path,
):
    boundary = tmp_path / "boundary.json"
    packet_stream = tmp_path / "packet_stream.json"
    packet_payload = _packet_stream_wrapper()
    packet_payload["native"].pop("failures")
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    packet_stream.write_text(json.dumps(packet_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        packet_stream_native_canary_json=packet_stream,
    )

    assert payload["passed"] is False
    assert payload["packet_stream_native_canary_passed"] is False
    assert "packet_stream_native_canary_not_passed" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_wrapper_direct_packet_bypass(
    tmp_path,
):
    boundary = tmp_path / "boundary.json"
    packet_stream = tmp_path / "packet_stream.json"
    packet_payload = _packet_stream_wrapper()
    packet_payload["packet_stream_input"] = True
    packet_payload["native"].pop("failures")
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    packet_stream.write_text(json.dumps(packet_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        packet_stream_native_canary_json=packet_stream,
    )

    assert payload["passed"] is False
    assert payload["packet_stream_native_canary_passed"] is False
    assert "packet_stream_native_canary_not_passed" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_session_wrong_provenance(tmp_path):
    boundary = tmp_path / "boundary.json"
    session = tmp_path / "session.json"
    session_payload = _session_contract()
    session_payload["source_is_online_stream_contract"] = False
    session_payload["source_kind"] = "raw_vllm_performance_summary"
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    session.write_text(json.dumps(session_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        session_online_contract_json=session,
    )

    assert payload["passed"] is False
    assert payload["session_online_contract_passed"] is False
    assert "session_online_contract_not_passed" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_session_missing_source_failures(
    tmp_path,
):
    boundary = tmp_path / "boundary.json"
    session = tmp_path / "session.json"
    session_payload = _session_contract()
    session_payload.pop("source_stream_online_contract_failures")
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    session.write_text(json.dumps(session_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        session_online_contract_json=session,
    )

    assert payload["passed"] is False
    assert payload["session_online_contract_passed"] is False
    assert "session_online_contract_not_passed" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_session_payload_bytes(tmp_path):
    boundary = tmp_path / "boundary.json"
    session = tmp_path / "session.json"
    session_payload = _session_contract()
    session_payload["payload_bytes"] = 4096
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    session.write_text(json.dumps(session_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        session_online_contract_json=session,
    )

    assert payload["passed"] is False
    assert payload["session_online_contract_passed"] is False
    assert "session_online_contract_payload_bytes_nonzero" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_session_prelaunch_ready(tmp_path):
    boundary = tmp_path / "boundary.json"
    session = tmp_path / "session.json"
    session_payload = _session_contract()
    session_payload["ready_for_vllm_prelaunch_canary"] = True
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    session.write_text(json.dumps(session_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        session_online_contract_json=session,
    )

    assert payload["passed"] is False
    assert payload["session_online_contract_passed"] is False
    assert "session_online_contract_vllm_prelaunch_not_false" in payload["failures"]


def test_native_producer_evidence_ladder_rejects_session_native_missing_payload(
    tmp_path,
):
    boundary = tmp_path / "boundary.json"
    session = tmp_path / "session.json"
    session_payload = _session_contract()
    session_payload["native"] = {
        "passed": True,
        "ok": True,
        "failures": [],
        **_runtime_disabled_fields(),
    }
    boundary.write_text(json.dumps(_boundary_gap()), encoding="utf-8")
    session.write_text(json.dumps(session_payload), encoding="utf-8")

    payload = checker.check_ladder(
        boundary_gap_json=boundary,
        session_online_contract_json=session,
    )

    assert payload["passed"] is False
    assert payload["session_online_contract_passed"] is False
    assert "session_online_contract_native_payload_bytes_nonzero" in payload["failures"]
