from __future__ import annotations

from scripts import check_premap_payload_cache_vllm_replay_visible_native_producer as checker


def _payload() -> dict[str, object]:
    return {
        "ok": True,
        "passed": True,
        "failures": [],
        "mode": "payload_cache_vllm_replay_visible_native_producer_contract",
        "contract_boundary": "inprocess_vllm_replay_visible_native_producer_op",
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
        "packet_count": 2560,
        "expected_packet_count": 2560,
        "issue_candidate_count": 20160,
        "expected_issue_candidate_count": 20160,
        "producer_update_count": 2560,
        "replay_visible_update_count": 2560,
        "prelaunch_probe_count": 2560,
        "prelaunch_abi_ready_count": 2560,
        "prelaunch_abi_blocked_count": 0,
        "prelaunch_device_tensor_count": 2560,
        "prelaunch_host_tensor_count": 0,
        "prelaunch_int32_count": 2560,
        "prelaunch_dtype_mismatch_count": 0,
        "prelaunch_current_count_host_scalar_available_count": 2560,
        "prelaunch_native_session_update_v1_abi_ready": True,
        "source_kind": "vllm_prelaunch_inprocess_native_producer",
        "current_expert_ptr_source_kind": "vllm_prelaunch_device_tensor",
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
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


def test_vllm_replay_visible_native_producer_accepts_valid_contract():
    result = checker.check_contract(_payload())

    assert result["passed"] is True
    assert result["ready_for_payload_cache_runtime_lab_gate"] is True
    assert result["packet_count"] == 2560
    assert result["issue_candidate_count"] == 20160
    assert result["prelaunch_probe_count"] == 2560
    assert result["prelaunch_abi_blocked_count"] == 0
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass"] is False
    assert result["passed_to_kernel"] is False


def test_vllm_replay_visible_native_producer_rejects_boundary_gap_artifact():
    payload = _payload()
    payload.update(
        {
            "mode": "payload_cache_online_native_producer_boundary_gap_report",
            "contract_boundary": "online_inside_graph_tensor_producer",
            "native_runtime": False,
            "inprocess_native_op": False,
            "vllm_replay_visible": False,
            "source_kind": "captured_torch_tensor_issue_generation",
        }
    )

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "mode_mismatch" in result["failures"]
    assert "contract_boundary_mismatch" in result["failures"]
    assert "inprocess_native_op_mismatch" in result["failures"]
    assert "vllm_replay_visible_mismatch" in result["failures"]
    assert result["input_mode"] == "payload_cache_online_native_producer_boundary_gap_report"
    assert result["input_contract_boundary"] == "online_inside_graph_tensor_producer"


def test_vllm_replay_visible_native_producer_rejects_payload_or_kernel_side_effect():
    payload = _payload()
    payload["payload_bytes"] = 4096
    payload["kernel_arg_pass"] = True

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "payload_bytes_mismatch" in result["failures"]
    assert "kernel_arg_pass_not_false" in result["failures"]
    assert result["ready_for_payload_cache_runtime_lab_gate"] is False


def test_vllm_replay_visible_native_producer_rejects_count_mismatch():
    payload = _payload()
    payload["producer_update_count"] = 40
    payload["replay_visible_update_count"] = 40

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "producer_update_count_mismatch" in result["failures"]
    assert "replay_visible_update_count_mismatch" in result["failures"]


def test_vllm_replay_visible_native_producer_rejects_prelaunch_abi_blocker():
    payload = _payload()
    payload["prelaunch_abi_ready_count"] = 0
    payload["prelaunch_abi_blocked_count"] = 2560
    payload["prelaunch_native_session_update_v1_abi_ready"] = False

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "prelaunch_abi_ready_count_invalid" in result["failures"]
    assert "prelaunch_abi_blocked_count_mismatch" in result["failures"]
    assert "prelaunch_native_session_update_v1_abi_ready_mismatch" in result[
        "failures"
    ]


def test_vllm_replay_visible_native_producer_rejects_wrong_source_kind():
    payload = _payload()
    payload["current_expert_ptr_source_kind"] = "native_scratch_smoke"
    payload["source_is_raw_vllm_performance_summary"] = True

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "current_expert_ptr_source_kind_mismatch" in result["failures"]
    assert "source_is_raw_vllm_performance_summary_mismatch" in result["failures"]


def test_vllm_replay_visible_native_producer_rejects_numeric_bool_standins():
    payload = _payload()
    payload["native_runtime"] = 1
    payload["inprocess_native_op"] = 1
    payload["vllm_replay_visible"] = 1
    payload["native_graph_replay"] = 0

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "native_runtime_mismatch" in result["failures"]
    assert "inprocess_native_op_mismatch" in result["failures"]
    assert "vllm_replay_visible_mismatch" in result["failures"]
    assert "native_graph_replay_mismatch" in result["failures"]
