from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from scripts import (
    build_premap_payload_cache_inprocess_native_session_online_contract as contract,
)


def _online_stream_contract(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "passed": True,
        "failures": [],
        "mode": "payload_cache_producer_state_stream_online_contract",
        "sample_count": 32,
        "requested_output_token_count": 2048,
        "contract_steps": 64,
        "contract_layers": 40,
        "contract_experts_per_layer": 225,
        "contract_transition_topk_count": 8,
        "contract_expected_packet_count": 2560,
        "contract_expected_previous_nonempty_packet_count": 2520,
        "contract_expected_issue_candidate_count": 20160,
        "contract_dimension_sources": {
            "all_layer_sources_match": True,
            "all_expert_sources_match": True,
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
        "native_stream_packet_count": 2560,
        "native_stream_previous_nonempty_packet_count": 2520,
        "native_stream_issue_candidate_count": 20160,
    }
    payload.update(overrides)
    return payload


def _raw_summary() -> dict[str, object]:
    prefix = "runtime_shadow_premap_payload_cache_direct_"
    return {
        "sample_count": 32,
        "requested_output_token_count": 2048,
        f"{prefix}transition_native_packet_count": 2560,
        f"{prefix}transition_native_packet_unique_layer_count": 40,
        f"{prefix}transition_producer_update_count": 2560,
        f"{prefix}transition_native_packet_previous_nonempty_count": 2520,
        f"{prefix}transition_native_packet_issue_candidate_count": 20160,
        f"{prefix}transition_native_packet_last_current_count": 225,
    }


def _native_session_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": True,
        "passed": True,
        "failures": [],
        "mode": "payload_cache_producer_state_inprocess_native_session_canary",
        "native_stub_invoked": True,
        "current_expert_ptr_source": "native_generated_device_scratch",
        "current_expert_ptr_source_kind": "native_scratch_smoke",
        "external_current_expert_ptr_source": False,
        "ready_for_native_session_smoke": True,
        "ready_for_external_pointer_smoke": False,
        "ready_for_vllm_prelaunch_canary": False,
        "issue_candidate_count": 20160,
        "expected_issue_candidate_count": 20160,
        "previous_nonempty_packet_count": 2520,
        "packet_count": 2560,
        "gpu_elapsed_ms": 1.25,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    payload.update(overrides)
    return payload


def _args(tmp_path: Path, perf: Path) -> argparse.Namespace:
    return argparse.Namespace(
        performance_summary=perf,
        output_json=tmp_path / "contract.json",
        native_output_json=tmp_path / "native.json",
        device=0,
        offload_arch="gfx1100",
        force_build=False,
        steps=None,
        layers=None,
        experts_per_layer=None,
        transition_topk_count=None,
        max_num_experts=256,
        step_shift=1,
        layer_stride=17,
        disable_vectorized_copy=False,
        native_generated_current=True,
    )


def test_session_online_contract_builds_payloadless_native_session_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(),
    )

    def fake_run_session_stub(args: argparse.Namespace) -> dict[str, object]:
        assert args.steps == 64
        assert args.layers == 40
        assert args.experts_per_layer == 225
        assert args.transition_topk_count == 8
        assert args.native_generated_current is True
        return _native_session_payload()

    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        fake_run_session_stub,
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is True
    assert payload["source_kind"] == (
        "derived_payload_cache_producer_state_stream_online_contract"
    )
    assert payload["source_is_online_stream_contract"] is True
    assert payload["source_stream_online_contract_passed"] is True
    assert payload["contract_steps"] == 64
    assert payload["contract_layers"] == 40
    assert payload["contract_experts_per_layer"] == 225
    assert payload["online_observed_packet_count"] == 2560
    assert payload["online_observed_previous_nonempty_packet_count"] == 2520
    assert payload["online_observed_issue_candidate_count"] == 20160
    assert payload["native_session_issue_candidate_count"] == 20160
    assert payload["native_session_previous_nonempty_packet_count"] == 2520
    assert payload["current_expert_ptr_source"] == "native_generated_device_scratch"
    assert payload["current_expert_ptr_source_kind"] == "native_scratch_smoke"
    assert payload["external_current_expert_ptr_source"] is False
    assert payload["ready_for_external_pointer_smoke"] is False
    assert payload["ready_for_vllm_prelaunch_canary"] is False
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False

    native_sidecar = tmp_path / "native.json"
    assert native_sidecar.exists()
    assert json.loads(native_sidecar.read_text(encoding="utf-8")) == (
        _native_session_payload()
    )


def test_session_online_contract_rejects_unpassed_stream_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(passed=False, failures=["source_failed"]),
    )
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "source_stream_online_contract_not_passed" in payload["failures"]
    assert "source_stream_online_contract_failures_not_empty" in payload["failures"]


def test_session_online_contract_rejects_raw_summary_source_even_with_matching_counts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _raw_summary())
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert payload["source_kind"] == "raw_vllm_performance_summary"
    assert payload["source_is_online_stream_contract"] is False
    assert "source_stream_online_contract_required" in payload["failures"]


def test_session_online_contract_rejects_upstream_stream_contract_kernel_arg_pass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(
            kernel_arg_pass=True,
            kernel_arg_pass_allowed=True,
        ),
    )
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "source_stream_online_contract_kernel_arg_pass_mismatch" in payload[
        "failures"
    ]
    assert "source_stream_online_contract_kernel_arg_pass_allowed_mismatch" in payload[
        "failures"
    ]


def test_session_online_contract_rejects_upstream_stream_contract_missing_safety_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    stream = _online_stream_contract()
    stream.pop("payload_transfer_enabled")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: stream)
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "source_stream_online_contract_payload_transfer_enabled_mismatch" in payload[
        "failures"
    ]


def test_session_online_contract_rejects_native_issue_count_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(),
    )
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(issue_candidate_count=1),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_session_issue_candidate_count_mismatch" in payload["failures"]


def test_session_online_contract_rejects_native_kernel_arg_pass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(),
    )
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(
            kernel_arg_pass=True,
            kernel_arg_pass_allowed=True,
        ),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_session_kernel_arg_pass_mismatch" in payload["failures"]
    assert "native_session_kernel_arg_pass_allowed_mismatch" in payload["failures"]


def test_session_online_contract_uses_source_transition_topk_not_cli_default_under_cap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(
            contract_experts_per_layer=8,
            contract_transition_topk_count=16,
            contract_expected_issue_candidate_count=20160,
            native_stream_issue_candidate_count=20160,
        ),
    )

    def fake_run_session_stub(args: argparse.Namespace) -> dict[str, object]:
        assert args.experts_per_layer == 8
        assert args.transition_topk_count == 16
        return _native_session_payload(
            experts_per_layer=8,
            requested_experts_per_layer=8,
            transition_topk_count=16,
            requested_transition_topk_count=16,
        )

    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        fake_run_session_stub,
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is True
    assert payload["contract_experts_per_layer"] == 8
    assert payload["contract_transition_topk_count"] == 16
    assert payload["native"]["transition_topk_count"] == 16


def test_session_online_contract_rejects_cli_transition_topk_override_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(
            contract_experts_per_layer=8,
            contract_transition_topk_count=16,
            contract_expected_issue_candidate_count=20160,
            native_stream_issue_candidate_count=20160,
        ),
    )
    args = _args(tmp_path, perf)
    args.transition_topk_count = 8
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda native_args: _native_session_payload(
            transition_topk_count=16,
            requested_transition_topk_count=16,
        ),
    )

    payload = contract.build_contract(args)

    assert payload["passed"] is False
    assert (
        "contract_transition_topk_count_cli_override_mismatch"
        in payload["failures"]
    )


def test_session_online_contract_rejects_native_generated_current_claiming_vllm_prelaunch_pointer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(),
    )
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(
            external_current_expert_ptr_source=True,
            ready_for_external_pointer_smoke=True,
            ready_for_vllm_prelaunch_canary=True,
        ),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_session_external_source_mismatch" in payload["failures"]
    assert "native_session_vllm_prelaunch_ready_unexpected" in payload["failures"]


def test_session_online_contract_rejects_torch_external_smoke_claiming_vllm_prelaunch_pointer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "stream_contract.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _online_stream_contract(),
    )
    monkeypatch.setattr(
        contract.session_stub,
        "run_session_stub",
        lambda args: _native_session_payload(
            current_expert_ptr_source="torch_device_tensor",
            current_expert_ptr_source_kind="external_torch_device_tensor_smoke",
            external_current_expert_ptr_source=True,
            ready_for_external_pointer_smoke=True,
            ready_for_vllm_prelaunch_canary=True,
        ),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_session_vllm_prelaunch_ready_unexpected" in payload["failures"]
