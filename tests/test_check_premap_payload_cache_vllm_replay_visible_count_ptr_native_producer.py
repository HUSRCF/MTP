from __future__ import annotations

from scripts import (
    check_premap_payload_cache_vllm_replay_visible_count_ptr_native_producer
    as checker,
)


def _payload() -> dict[str, object]:
    return {
        "ok": True,
        "enabled": True,
        "present": True,
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
        "packet_count": 160,
        "expected_packet_count": 160,
        "issue_candidate_count": 640,
        "expected_issue_candidate_count": 640,
        "expected_issue_candidate_count_source": (
            "prelaunch_independent_previous_nonempty_issue_candidate_count"
        ),
        "prelaunch_independent_previous_nonempty_packet_count": 80,
        "prelaunch_independent_previous_nonempty_issue_candidate_count": 640,
        "native_session_previous_nonempty_packet_count": 80,
        "producer_update_count": 160,
        "replay_visible_update_count": 160,
        "prelaunch_probe_count": 160,
        "prelaunch_abi_ready_count": 0,
        "prelaunch_abi_blocked_count": 160,
        "prelaunch_device_tensor_count": 160,
        "prelaunch_host_tensor_count": 0,
        "prelaunch_int32_count": 160,
        "prelaunch_dtype_mismatch_count": 0,
        "prelaunch_current_count_device_tensor_count": 160,
        "prelaunch_current_count_device_scalar_int32_count": 160,
        "prelaunch_current_count_host_scalar_available_count": 0,
        "prelaunch_native_session_update_v1_abi_ready": False,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": 160,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": 0,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready": True,
        "prelaunch_last_current_count_source_kind": (
            "num_tokens_post_padded_device_tensor"
        ),
        "prelaunch_last_count_ptr_block_reason": None,
        "prelaunch_last_block_reason": "current_count_host_scalar_not_available",
        "source_kind": "vllm_prelaunch_inprocess_native_producer",
        "current_expert_ptr_source_kind": "vllm_prelaunch_device_tensor",
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "ready_for_payload_cache_runtime_lab_gate": True,
        "payload_bytes": 0,
        "ready": False,
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


def test_count_ptr_native_producer_accepts_strict_device_count_path():
    result = checker.check_contract(_payload())

    assert result["passed"] is True
    assert result["ready_for_payload_cache_runtime_lab_gate"] is True
    assert result["count_ptr_ready_count"] == 160
    assert result["host_scalar_count"] == 0
    assert result["legacy_host_scalar_ready_count"] == 0
    assert result["ready"] is False
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["measures_tpot"] is False
    assert result["kernel_arg_pass"] is False
    assert result["passed_to_kernel"] is False


def test_count_ptr_native_producer_rejects_legacy_host_scalar_update_path():
    payload = _payload()
    payload["prelaunch_abi_ready_count"] = 160
    payload["prelaunch_abi_blocked_count"] = 0
    payload["prelaunch_current_count_device_tensor_count"] = 0
    payload["prelaunch_current_count_device_scalar_int32_count"] = 0
    payload["prelaunch_current_count_host_scalar_available_count"] = 160
    payload["prelaunch_native_session_update_v1_abi_ready"] = True
    payload["prelaunch_native_session_update_count_ptr_v1_abi_ready_count"] = 0
    payload["prelaunch_native_session_update_count_ptr_v1_abi_ready"] = False
    payload["prelaunch_last_current_count_source_kind"] = (
        "num_tokens_post_padded_host_tensor"
    )
    payload["prelaunch_last_block_reason"] = None

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "device_count_tensor_count_mismatch" in result["failures"]
    assert "host_scalar_count_unexpectedly_available" in result["failures"]
    assert "count_ptr_ready_count_mismatch" in result["failures"]
    assert "legacy_host_scalar_abi_unexpectedly_ready" in result["failures"]


def test_count_ptr_native_producer_rejects_payload_or_kernel_mutation():
    payload = _payload()
    payload["payload_bytes"] = 64
    payload["ready"] = True
    payload["kernel_arg_pass"] = True
    payload["passed_to_kernel"] = True

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "payload_bytes_mismatch" in result["failures"]
    assert "ready_mismatch" in result["failures"]
    assert "kernel_arg_pass_mismatch" in result["failures"]
    assert "passed_to_kernel_mismatch" in result["failures"]


def test_count_ptr_native_producer_rejects_payload_bytes_bool_standin():
    payload = _payload()
    payload["payload_bytes"] = False

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "payload_bytes_mismatch" in result["failures"]


def test_count_ptr_native_producer_rejects_python_transition_fallback():
    payload = _payload()
    payload["python_transition_skipped"] = False

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "python_transition_not_skipped" in result["failures"]


def test_count_ptr_native_producer_accepts_no_legacy_host_scalar_probe():
    payload = _payload()
    payload["prelaunch_abi_blocked_count"] = 0
    payload["prelaunch_last_block_reason"] = None

    result = checker.check_contract(payload)

    assert result["passed"] is True
    assert result["legacy_host_scalar_blocked_count"] == 0
