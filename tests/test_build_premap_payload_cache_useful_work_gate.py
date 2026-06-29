from __future__ import annotations

import json
from pathlib import Path

from scripts import build_premap_payload_cache_useful_work_gate as gate
from scripts import (
    check_premap_payload_cache_vllm_replay_visible_count_ptr_native_producer
    as count_ptr_checker,
)
from scripts.run_payload_cache_consumer_visible_hit_blocked_gate import (
    build_report as build_consumer_visible_hit_blocked_report,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _count_ptr_payload(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
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
        "packet_count": 8,
        "expected_packet_count": 8,
        "issue_candidate_count": 64,
        "expected_issue_candidate_count": 64,
        "expected_issue_candidate_count_source": "graph_visible_producer_contract",
        "producer_update_count": 8,
        "replay_visible_update_count": 8,
        "prelaunch_probe_count": 8,
        "prelaunch_abi_ready_count": 0,
        "prelaunch_abi_blocked_count": 8,
        "prelaunch_device_tensor_count": 8,
        "prelaunch_host_tensor_count": 0,
        "prelaunch_int32_count": 8,
        "prelaunch_dtype_mismatch_count": 0,
        "prelaunch_current_count_device_tensor_count": 8,
        "prelaunch_current_count_device_scalar_int32_count": 8,
        "prelaunch_current_count_host_scalar_available_count": 0,
        "prelaunch_native_session_update_v1_abi_ready": False,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready_count": 8,
        "prelaunch_native_session_update_count_ptr_v1_abi_blocked_count": 0,
        "prelaunch_native_session_update_count_ptr_v1_abi_ready": True,
        "prelaunch_last_current_count_source_kind": (
            "num_tokens_post_padded_device_tensor"
        ),
        "prelaunch_last_count_ptr_block_reason": None,
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
    raw.update(overrides)
    return count_ptr_checker.check_contract(raw)


def _consumer_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = build_consumer_visible_hit_blocked_report()
    payload["ready"] = False
    payload.update(overrides)
    return payload


def _run(tmp_path: Path, *, producer: dict[str, object], consumer: dict[str, object]):
    producer_path = tmp_path / "producer.json"
    consumer_path = tmp_path / "consumer.json"
    _write_json(producer_path, producer)
    _write_json(consumer_path, consumer)
    return gate.build_gate(
        count_ptr_native_producer_json=producer_path,
        consumer_visible_hit_blocked_json=consumer_path,
    )


def test_payload_cache_useful_work_gate_accepts_count_ptr_producer_and_blocked_consumer(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        producer=_count_ptr_payload(),
        consumer=_consumer_payload(),
    )

    assert result["passed"] is True
    assert result["producer_count_ptr_ready"] is True
    assert result["consumer_visible_blocked_ready"] is True
    assert result["native_producer_downshifted"] is True
    assert result["payload_cache_useful_work_ready"] is False
    assert result["payload_cache_useful_work_block_reason"] == "payload_transfer_disabled"
    assert result["producer_expected_packet_count"] == 8
    assert result["consumer_requested_payload_bytes"] == 64
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["measures_tpot"] is False


def test_payload_cache_useful_work_gate_rejects_legacy_host_scalar_producer(
    tmp_path: Path,
) -> None:
    producer = _count_ptr_payload(
        prelaunch_current_count_device_tensor_count=0,
        prelaunch_current_count_device_scalar_int32_count=0,
        prelaunch_current_count_host_scalar_available_count=8,
        prelaunch_native_session_update_count_ptr_v1_abi_ready_count=0,
        prelaunch_native_session_update_count_ptr_v1_abi_ready=False,
        prelaunch_last_current_count_source_kind="num_tokens_post_padded_host_tensor",
    )

    result = _run(tmp_path, producer=producer, consumer=_consumer_payload())

    assert result["passed"] is False
    assert "count_ptr_native_producer_passed_mismatch" in result["failures"]


def test_payload_cache_useful_work_gate_rejects_consumer_payload_publication(
    tmp_path: Path,
) -> None:
    consumer = _consumer_payload(
        demand_hit_published=True,
        consumer_visible_payload_hit=True,
        payload_bytes=64,
        demand_hit_count=1,
    )

    result = _run(tmp_path, producer=_count_ptr_payload(), consumer=consumer)

    assert result["passed"] is False
    assert "consumer_visible_hit_blocked_demand_hit_published_mismatch" in result[
        "failures"
    ]
    assert "consumer_visible_hit_blocked_payload_bytes_nonzero" in result["failures"]


def test_payload_cache_useful_work_gate_rejects_minimal_consumer_stub(
    tmp_path: Path,
) -> None:
    consumer = {
        "artifact_kind": "payload_cache_consumer_visible_hit_blocked_gate",
        "schema_version": 1,
        "source": "payload_cache_consumer_visible_hit_blocked_gate",
        "passed": True,
        "failures": [],
        "decision": "blocked",
        "block_reason": "payload_transfer_disabled",
        "request_matches_envelope_source_binding": True,
        "execution_mode": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_demand_hit_publication_blocked_canary"
        ),
        "demand_hit_publication_allowed": False,
        "demand_hit_published": False,
        "consumer_visible_payload_hit": False,
        "prefetched_demand_hit": False,
        "payload_deref_attempted": False,
        "payload_handle_deref_attempted": False,
        "ready": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "payload_bytes": 0,
        "resident_payload_bytes": 0,
        "dereferenced_payload_bytes": 0,
        "demand_hit_payload_bytes": 0,
        "issued_payload_count": 0,
        "resident_payload_count": 0,
        "demand_hit_count": 0,
        "demand_hit_publication_count": 0,
        "consumer_visible_payload_hit_count": 0,
        "requested_payload_bytes": 64,
        "source_issue_packet_count": 28,
        "source_issue_unique_key_count": 16,
        "source_queue_deadline_us": 100.0,
    }

    result = _run(tmp_path, producer=_count_ptr_payload(), consumer=consumer)

    assert result["passed"] is False
    assert any(
        failure.startswith("consumer_visible_hit_blocked_canary_")
        for failure in result["failures"]
    )


def test_payload_cache_useful_work_gate_rejects_ready_flag(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        producer=_count_ptr_payload(ready=True),
        consumer=_consumer_payload(ready=True),
    )

    assert result["passed"] is False
    assert "count_ptr_native_producer_passed_mismatch" in result["failures"]
    assert "consumer_visible_hit_blocked_ready_mismatch" in result["failures"]
