from __future__ import annotations

from scripts import (
    check_premap_payload_cache_vllm_replay_visible_count_ptr_readiness as checker,
)


def _payload() -> dict[str, object]:
    return {
        "mode": "payload_cache_vllm_replay_visible_native_producer_contract",
        "contract_boundary": "inprocess_vllm_replay_visible_native_producer_op",
        "source_kind": "vllm_prelaunch_inprocess_native_producer",
        "current_expert_ptr_source_kind": "vllm_prelaunch_device_tensor",
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "expected_packet_count": 8,
        "prelaunch_probe_count": 8,
        "prelaunch_device_tensor_count": 8,
        "prelaunch_host_tensor_count": 0,
        "prelaunch_int32_count": 8,
        "prelaunch_dtype_mismatch_count": 0,
        "prelaunch_current_count_host_scalar_available_count": 0,
        "prelaunch_current_count_device_tensor_count": 8,
        "prelaunch_current_count_device_scalar_int32_count": 8,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": 8,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": 0,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready": True,
        "prelaunch_last_count_ptr_block_reason": None,
        "prelaunch_last_current_count_source_kind": (
            "num_tokens_post_padded_device_tensor"
        ),
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


def test_count_ptr_readiness_accepts_device_scalar_int32_surface() -> None:
    result = checker.check_contract(_payload())

    assert result["passed"] is True
    assert result["ready_for_future_count_ptr_native_session"] is True
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass"] is False


def test_count_ptr_readiness_rejects_host_scalar_legacy_surface() -> None:
    payload = _payload()
    payload["prelaunch_current_count_device_tensor_count"] = 0
    payload["prelaunch_current_count_device_scalar_int32_count"] = 0
    payload["prelaunch_native_session_update_count_ptr_v1_abi_ready_count"] = 0
    payload["prelaunch_native_session_update_count_ptr_v1_abi_blocked_count"] = 8
    payload["prelaunch_native_session_update_count_ptr_v1_abi_ready"] = False

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "prelaunch_current_count_device_tensor_count_invalid" in result["failures"]
    assert (
        "prelaunch_current_count_device_scalar_int32_count_invalid"
        in result["failures"]
    )
    assert (
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_mismatch"
        in result["failures"]
    )


def test_count_ptr_readiness_rejects_payload_or_kernel_enablement() -> None:
    payload = _payload()
    payload["payload_bytes"] = 4096
    payload["payload_transfer_enabled"] = True
    payload["kernel_arg_pass"] = True

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "payload_bytes_mismatch" in result["failures"]
    assert "payload_transfer_enabled_not_false" in result["failures"]
    assert "kernel_arg_pass_not_false" in result["failures"]


def test_count_ptr_readiness_rejects_wrong_provenance() -> None:
    payload = _payload()
    payload["contract_boundary"] = "standalone_native_replay"
    payload["source_kind"] = "raw_vllm_performance_summary"
    payload["source_is_online_stream_contract"] = False
    payload["source_is_raw_vllm_performance_summary"] = True

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "contract_boundary_mismatch" in result["failures"]
    assert "source_kind_mismatch" in result["failures"]
    assert "source_is_online_stream_contract_mismatch" in result["failures"]
    assert "source_is_raw_vllm_performance_summary_mismatch" in result["failures"]


def test_count_ptr_readiness_rejects_contradictory_negative_counters() -> None:
    payload = _payload()
    payload["prelaunch_host_tensor_count"] = 1
    payload["prelaunch_dtype_mismatch_count"] = 1
    payload["prelaunch_current_count_host_scalar_available_count"] = 1
    payload["prelaunch_last_count_ptr_block_reason"] = "current_count_host_scalar"

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "prelaunch_host_tensor_count_mismatch" in result["failures"]
    assert "prelaunch_dtype_mismatch_count_mismatch" in result["failures"]
    assert (
        "prelaunch_current_count_host_scalar_available_count_mismatch"
        in result["failures"]
    )
    assert "prelaunch_last_count_ptr_block_reason_mismatch" in result["failures"]


def test_count_ptr_readiness_rejects_wrong_current_count_source_kind() -> None:
    payload = _payload()
    payload["prelaunch_last_current_count_source_kind"] = (
        "num_tokens_post_padded_host_tensor"
    )

    result = checker.check_contract(payload)

    assert result["passed"] is False
    assert "prelaunch_last_current_count_source_kind_mismatch" in result["failures"]
