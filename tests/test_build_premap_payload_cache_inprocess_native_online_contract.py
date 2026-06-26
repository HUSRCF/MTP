from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import build_premap_payload_cache_inprocess_native_online_contract as contract


PREFIX = "runtime_shadow_premap_payload_cache_direct_"


def _raw_summary() -> dict[str, object]:
    return {
        "sample_count": 1,
        "requested_output_token_count": 4,
        f"{PREFIX}transition_state_owner": "producer",
        f"{PREFIX}transition_native_packet_count": 8,
        f"{PREFIX}transition_producer_update_count": 8,
        f"{PREFIX}transition_native_packet_previous_nonempty_count": 6,
        f"{PREFIX}transition_native_packet_issue_candidate_count": 24,
        f"{PREFIX}transition_native_packet_unique_layer_count": 2,
        f"{PREFIX}transition_native_packet_last_current_count": 8,
    }


def _stream_summary() -> dict[str, object]:
    summary = _raw_summary()
    summary.update(
        {
            "mode": "payload_cache_producer_state_stream_online_contract",
            "passed": True,
            "failures": [],
            "contract_steps": 4,
            "contract_layers": 2,
            "contract_experts_per_layer": 8,
            "contract_transition_topk_count": 4,
            "contract_dimension_sources": {
                "layer_sources": {
                    f"{PREFIX}transition_native_packet_unique_layer_count": 2
                },
                "expert_sources": {
                    f"{PREFIX}transition_native_packet_last_current_count": 8
                },
            },
            "contract_dimension_consistency_failures": [],
            "payload_bytes": 0,
            "ready_credit": False,
            "ready_before_demand_credit": False,
            "real_ready_credit_granted": False,
            "payload_transfer_enabled": False,
            "payload_deref_allowed": False,
            "kernel_arg_pass": False,
            "kernel_arg_pass_allowed": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
            "native_stream_packet_count": 8,
            "native_stream_previous_nonempty_packet_count": 6,
            "native_stream_issue_candidate_count": 24,
        }
    )
    return summary


def _native_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "passed": True,
        "ok": True,
        "native_graph_replay": True,
        "native_stub_invoked": True,
        "vllm_replay_visible": False,
        "issue_candidate_count": 24,
        "expected_issue_candidate_count": 24,
        "previous_nonempty_packet_count": 6,
        "packet_count": 8,
        "gpu_elapsed_ms": 0.1,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
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
    payload.update(overrides)
    return payload


def _args(tmp_path: Path, performance_summary: Path) -> argparse.Namespace:
    return argparse.Namespace(
        performance_summary=performance_summary,
        output_json=tmp_path / "contract.json",
        native_output_json=tmp_path / "native.json",
        device=0,
        offload_arch="gfx1100",
        force_build=False,
        steps=None,
        layers=None,
        experts_per_layer=None,
        transition_topk_count=4,
        max_num_experts=256,
        step_shift=1,
        layer_stride=17,
        state_hash_base=0x8A45D2C91FE01237,
        disable_vectorized_copy=False,
        graph_replay=True,
    )


def test_inprocess_native_online_contract_rejects_raw_summary_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(_raw_summary()), encoding="utf-8")
    monkeypatch.setattr(
        contract.inprocess_stub,
        "run_stub",
        lambda args: _native_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, summary_path))

    assert payload["passed"] is False
    assert payload["source_is_raw_vllm_performance_summary"] is True
    assert "source_stream_online_contract_required" in payload["failures"]
    assert payload["ready_for_vllm_prelaunch_native_op"] is False


def test_inprocess_native_online_contract_accepts_stream_contract_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "stream_contract.json"
    summary_path.write_text(json.dumps(_stream_summary()), encoding="utf-8")
    monkeypatch.setattr(
        contract.inprocess_stub,
        "run_stub",
        lambda args: _native_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, summary_path))

    assert payload["passed"] is True
    assert payload["source_is_online_stream_contract"] is True
    assert payload["source_stream_online_contract_passed"] is True
    assert payload["ready_for_vllm_prelaunch_native_op"] is True


def test_inprocess_native_online_contract_rejects_upstream_kernel_arg_pass(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "stream_contract.json"
    stream = _stream_summary()
    stream["kernel_arg_pass"] = True
    stream["kernel_arg_pass_allowed"] = True
    summary_path.write_text(json.dumps(stream), encoding="utf-8")
    monkeypatch.setattr(
        contract.inprocess_stub,
        "run_stub",
        lambda args: _native_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, summary_path))

    assert payload["passed"] is False
    assert "source_stream_online_contract_kernel_arg_pass_mismatch" in payload[
        "failures"
    ]
    assert "source_stream_online_contract_kernel_arg_pass_allowed_mismatch" in payload[
        "failures"
    ]


def test_inprocess_native_online_contract_rejects_native_payload_transfer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "stream_contract.json"
    summary_path.write_text(json.dumps(_stream_summary()), encoding="utf-8")
    monkeypatch.setattr(
        contract.inprocess_stub,
        "run_stub",
        lambda args: _native_payload(payload_transfer_enabled=True),
    )

    payload = contract.build_contract(_args(tmp_path, summary_path))

    assert payload["passed"] is False
    assert "native_payload_transfer_enabled_mismatch" in payload["failures"]
