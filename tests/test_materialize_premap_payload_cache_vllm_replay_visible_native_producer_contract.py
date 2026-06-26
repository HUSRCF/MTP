from __future__ import annotations

import json
from pathlib import Path

from scripts import (
    check_premap_payload_cache_vllm_replay_visible_native_producer as checker,
)
from scripts import (
    materialize_premap_payload_cache_vllm_replay_visible_native_producer_contract
    as materializer,
)


PREFIX = (
    "runtime_shadow_premap_payload_cache_direct_"
    "vllm_replay_visible_native_producer_contract_"
)


def _prefixed(payload: dict[str, object]) -> dict[str, object]:
    return {f"{PREFIX}{key}": value for key, value in payload.items()}


def _valid_contract() -> dict[str, object]:
    return {
        "enabled": True,
        "present": True,
        "passed": True,
        "failures": [],
        "mode": "payload_cache_vllm_replay_visible_native_producer_contract",
        "contract_boundary": "inprocess_vllm_replay_visible_native_producer_op",
        "source_kind": "vllm_prelaunch_inprocess_native_producer",
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
        "current_expert_ptr_source_kind": "vllm_prelaunch_device_tensor",
        "source_is_online_stream_contract": True,
        "source_is_raw_vllm_performance_summary": False,
        "ready_for_payload_cache_runtime_lab_gate": True,
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
        "prelaunch_probe_count": 2560,
        "prelaunch_abi_ready_count": 2560,
        "prelaunch_abi_blocked_count": 0,
        "prelaunch_device_tensor_count": 2560,
        "prelaunch_host_tensor_count": 0,
        "prelaunch_int32_count": 2560,
        "prelaunch_dtype_mismatch_count": 0,
        "prelaunch_current_count_device_tensor_count": 0,
        "prelaunch_current_count_host_scalar_available_count": 2560,
        "prelaunch_native_session_update_v1_abi_ready": True,
        "prelaunch_last_block_reason": None,
        "prelaunch_last_expert_dtype": "torch.int32",
        "prelaunch_last_expert_device": "cuda:0",
        "prelaunch_last_expert_ndim": 1,
        "prelaunch_last_expert_numel": 8,
        "prelaunch_last_block_size": 16,
        "prelaunch_last_current_count_source_kind": (
            "num_tokens_post_padded_host_tensor"
        ),
    }


def _fail_closed_contract() -> dict[str, object]:
    payload = _valid_contract()
    payload.update(
        {
            "enabled": True,
            "present": False,
            "passed": False,
            "failures": [
                "native_runtime_not_connected",
                "inprocess_native_op_not_connected",
                "vllm_replay_visible_updates_missing",
            ],
            "source_kind": "missing_vllm_prelaunch_inprocess_native_producer",
            "native_runtime": False,
            "inprocess_native_op": False,
            "vllm_replay_visible": False,
            "prelaunch_callable_native_session": False,
            "transition_state_on_device": False,
            "persistent_state_on_device": False,
            "issue_generation_on_device": False,
            "python_transition_skipped": False,
            "packet_count": 0,
            "issue_candidate_count": 0,
            "producer_update_count": 0,
            "replay_visible_update_count": 0,
            "current_expert_ptr_source_kind": None,
            "source_is_online_stream_contract": False,
            "ready_for_payload_cache_runtime_lab_gate": False,
            "prelaunch_probe_count": 8,
            "prelaunch_abi_ready_count": 0,
            "prelaunch_abi_blocked_count": 8,
            "prelaunch_device_tensor_count": 0,
            "prelaunch_host_tensor_count": 8,
            "prelaunch_int32_count": 0,
            "prelaunch_dtype_mismatch_count": 8,
            "prelaunch_current_count_device_tensor_count": 0,
            "prelaunch_current_count_host_scalar_available_count": 8,
            "prelaunch_native_session_update_v1_abi_ready": False,
            "prelaunch_last_block_reason": (
                "current_expert_not_device_tensor;current_expert_dtype_not_int32"
            ),
            "prelaunch_last_expert_dtype": "torch.int64",
            "prelaunch_last_expert_device": "cpu",
            "prelaunch_last_expert_ndim": 1,
            "prelaunch_last_expert_numel": 2,
            "prelaunch_last_block_size": 1,
            "prelaunch_last_current_count_source_kind": (
                "num_tokens_post_padded_host_tensor"
            ),
        }
    )
    return payload


def test_materializer_extracts_fail_closed_contract_but_checker_rejects() -> None:
    result = materializer.materialize_contract(_prefixed(_fail_closed_contract()))

    assert result["materializer_passed"] is True
    assert result["ok"] is False
    assert result["passed"] is False
    assert result["mode"] == "payload_cache_vllm_replay_visible_native_producer_contract"
    assert result["contract_boundary"] == "inprocess_vllm_replay_visible_native_producer_op"
    assert result["native_runtime"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass"] is False
    assert result["prelaunch_probe_count"] == 8
    assert result["prelaunch_abi_blocked_count"] == 8
    assert result["prelaunch_last_expert_dtype"] == "torch.int64"

    checked = checker.check_contract(result)
    assert checked["passed"] is False
    assert "ok_mismatch" in checked["failures"]
    assert "native_runtime_mismatch" in checked["failures"]
    assert "source_kind_mismatch" in checked["failures"]


def test_materializer_extracts_future_positive_contract_for_checker() -> None:
    result = materializer.materialize_contract(_prefixed(_valid_contract()))

    assert result["materializer_passed"] is True
    assert result["ok"] is True
    assert result["passed"] is True
    assert result["failures"] == []
    assert result["prelaunch_probe_count"] == 2560
    assert result["prelaunch_native_session_update_v1_abi_ready"] is True

    checked = checker.check_contract(result)
    assert checked["passed"] is True
    assert checked["ready_for_payload_cache_runtime_lab_gate"] is True


def test_materializer_reports_missing_prefixed_surface(tmp_path: Path) -> None:
    performance_summary = tmp_path / "performance_summary.json"
    output_json = tmp_path / "contract.json"
    performance_summary.write_text(json.dumps({"sample_count": 1}), encoding="utf-8")

    args = materializer.build_parser().parse_args(
        [
            "--performance-summary",
            str(performance_summary),
            "--output-json",
            str(output_json),
        ]
    )
    exit_code = materializer.main(
        [
            "--performance-summary",
            str(performance_summary),
            "--output-json",
            str(output_json),
        ]
    )

    assert args.performance_summary == performance_summary
    assert exit_code == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["materializer_passed"] is False
    assert "mode_missing" in payload["materializer_failures"]
    assert payload["ok"] is False


def test_materializer_cli_accepts_complete_fail_closed_surface(tmp_path: Path) -> None:
    performance_summary = tmp_path / "performance_summary.json"
    output_json = tmp_path / "contract.json"
    performance_summary.write_text(
        json.dumps(_prefixed(_fail_closed_contract())),
        encoding="utf-8",
    )

    exit_code = materializer.main(
        [
            "--performance-summary",
            str(performance_summary),
            "--output-json",
            str(output_json),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["materializer_passed"] is True
    assert payload["passed"] is False
    assert payload["ok"] is False
    assert "native_runtime_not_connected" in payload["failures"]
