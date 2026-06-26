from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from scripts import (
    build_premap_payload_cache_producer_state_stream_online_contract as contract,
)


def _summary() -> dict[str, object]:
    prefix = "runtime_shadow_premap_payload_cache_direct_"
    return {
        "sample_count": 32,
        "requested_output_token_count": 2048,
        f"{prefix}transition_state_owner": "producer",
        f"{prefix}transition_native_packet_count": 2560,
        f"{prefix}transition_native_packet_unique_layer_count": 40,
        f"{prefix}transition_producer_update_count": 2560,
        f"{prefix}transition_native_packet_ready_count": 2560,
        f"{prefix}transition_native_packet_previous_nonempty_count": 2520,
        f"{prefix}transition_native_packet_issue_candidate_count": 20160,
        f"{prefix}transition_native_packet_last_issue_candidate_count": 8,
        f"{prefix}transition_native_packet_last_issue_candidate_first_expert": 0,
        f"{prefix}transition_native_packet_last_issue_candidate_last_expert": 220,
        f"{prefix}transition_native_packet_last_issue_candidate_hash": "22488eda926276f7",
        f"{prefix}transition_native_packet_last_current_count": 225,
        f"{prefix}transition_issue_previous_nonempty_count": 0,
        f"{prefix}transition_issue_descriptor_count": 0,
        f"{prefix}transition_issue_last_candidate_count": 0,
        f"{prefix}transition_issue_last_candidate_first_expert": -1,
        f"{prefix}transition_issue_last_candidate_last_expert": -1,
        f"{prefix}transition_issue_last_candidate_hash": None,
    }


def _summary_with_embedded_contract() -> dict[str, object]:
    summary = _summary()
    prefix = "runtime_shadow_premap_payload_cache_direct_online_stream_contract_"
    summary.update(
        {
            f"{prefix}present": True,
            f"{prefix}passed": True,
            f"{prefix}failures": [],
            f"{prefix}steps": 64,
            f"{prefix}layers": 40,
            f"{prefix}experts_per_layer": 225,
            f"{prefix}packet_count": 2560,
            f"{prefix}observed_packet_count": 2560,
            f"{prefix}expected_packet_count": 2560,
            f"{prefix}packet_count_matches_expected": True,
            f"{prefix}previous_nonempty_packet_count": 2520,
            f"{prefix}observed_previous_nonempty_packet_count": 2520,
            f"{prefix}expected_previous_nonempty_packet_count": 2520,
            f"{prefix}expected_issue_candidate_count": 20160,
            f"{prefix}issue_candidate_count": 20160,
            f"{prefix}observed_issue_candidate_count": 20160,
            f"{prefix}issue_last_candidate_present": True,
            f"{prefix}issue_last_candidate_count": 8,
            f"{prefix}issue_last_candidate_first_expert": 0,
            f"{prefix}issue_last_candidate_last_expert": 220,
            f"{prefix}issue_last_candidate_hash": "22488eda926276f7",
            f"{prefix}payload_bytes": 0,
            f"{prefix}ready_credit": False,
            f"{prefix}ready_before_demand_credit": False,
            f"{prefix}real_ready_credit_granted": False,
            f"{prefix}payload_transfer_enabled": False,
            f"{prefix}payload_deref_allowed": False,
            f"{prefix}kernel_arg_pass": False,
            f"{prefix}kernel_arg_pass_allowed": False,
            f"{prefix}passed_to_kernel": False,
            f"{prefix}changes_kernel_launch_args": False,
            f"{prefix}current_wna16_arg_compatible": False,
            f"{prefix}uses_current_wna16_args": False,
            f"{prefix}passes_current_wna16_args": False,
            f"{prefix}measures_tpot": False,
            f"{prefix}measures_vllm_latency": False,
        }
    )
    return summary


def _graph_once_per_layer_summary() -> dict[str, object]:
    summary = _summary()
    prefix = "runtime_shadow_premap_payload_cache_direct_"
    summary.update(
        {
            f"{prefix}transition_native_packet_count": 40,
            f"{prefix}transition_producer_update_count": 40,
            f"{prefix}transition_native_packet_ready_count": 40,
            f"{prefix}transition_native_packet_previous_nonempty_count": 0,
            f"{prefix}transition_native_packet_issue_candidate_count": 0,
            f"{prefix}transition_native_packet_last_issue_candidate_count": 0,
            f"{prefix}transition_native_packet_last_issue_candidate_first_expert": -1,
            f"{prefix}transition_native_packet_last_issue_candidate_last_expert": -1,
            f"{prefix}transition_native_packet_last_issue_candidate_hash": None,
        }
    )
    return summary


def _args(tmp_path: Path, perf: Path) -> argparse.Namespace:
    return argparse.Namespace(
        performance_summary=perf,
        output_json=tmp_path / "contract.json",
        native_output_json=tmp_path / "native.json",
        device=0,
        hip_visible_devices=None,
        offload_arch="gfx1100",
        force_build=False,
        steps=None,
        layers=None,
        experts_per_layer=None,
        transition_topk_count=8,
        max_num_experts=256,
        step_shift=1,
        layer_stride=17,
        state_hash_base=0x8A45D2C91FE01237,
        disable_vectorized_copy=False,
        graph_replay=True,
    )


def _native_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": True,
        "passed": True,
        "failures": [],
        "issue_candidate_count": 20160,
        "previous_nonempty_packet_count": 2520,
        "packet_count": 2560,
        "native_graph_replay": True,
        "requested_graph_replay": True,
        "vectorized_copy_used": False,
        "persistent_state_on_device": True,
        "issue_generation_on_device": True,
        "gpu_elapsed_ms": 1.25,
        "first_issue_expert": 0,
        "last_issue_expert": 220,
        "issue_candidate_hash": "22488eda926276f7",
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


def _parse_args(*extra: str) -> argparse.Namespace:
    return contract._build_parser().parse_args(
        [
            "--performance-summary",
            "performance_summary.json",
            "--output-json",
            "contract.json",
            "--native-output-json",
            "native.json",
            *extra,
        ]
    )


def test_online_contract_parser_defaults_to_graph_replay() -> None:
    assert _parse_args().graph_replay is True
    assert _parse_args("--graph-replay").graph_replay is True
    assert _parse_args("--no-graph-replay").graph_replay is False
    assert (
        _parse_args("--no-graph-replay", "--graph-replay").graph_replay is True
    )
    assert (
        _parse_args("--graph-replay", "--no-graph-replay").graph_replay is False
    )


def test_online_contract_derives_stream_dimensions() -> None:
    summary = _summary()

    assert contract._steps_from_summary(summary, override=None) == 64
    assert contract._layers_from_summary(summary, override=None) == 40
    assert contract._experts_per_layer_from_summary(summary, override=None) == 225


def test_online_contract_builds_payloadless_native_stream_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())

    def fake_run_stub(args):
        assert args.steps == 64
        assert args.layers == 40
        assert args.experts_per_layer == 225
        assert args.graph_replay is True
        return _native_payload()

    monkeypatch.setattr(contract.stream_stub, "run_stub", fake_run_stub)

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is True
    native_sidecar = tmp_path / "native.json"
    assert native_sidecar.exists()
    assert json.loads(native_sidecar.read_text(encoding="utf-8")) == _native_payload()
    assert payload["online_python_prelaunch_state_empty"] is True
    assert payload["contract_steps"] == 64
    assert payload["contract_layers"] == 40
    assert payload["contract_experts_per_layer"] == 225
    assert payload["contract_expected_packet_count"] == 2560
    assert payload["contract_expected_previous_nonempty_packet_count"] == 2520
    assert payload["contract_expected_issue_candidate_count"] == 20160
    assert payload["contract_dimension_sources"]["all_layer_sources_match"] is True
    assert payload["contract_dimension_consistency_failures"] == []
    assert payload["online_observed_packet_count"] == 2560
    assert payload["online_observed_previous_nonempty_packet_count"] == 2520
    assert payload["online_observed_issue_candidate_count"] == 20160
    assert payload["online_transition_issue_last_candidate_present"] is True
    assert payload["online_transition_issue_last_candidate_source"] == (
        "performance_summary"
    )
    assert payload["online_transition_issue_last_candidate_count"] == 8
    assert payload["online_transition_issue_last_candidate_hash"] == "22488eda926276f7"
    assert payload["native_stream_issue_candidate_count"] == 20160
    assert payload["native_stream_first_issue_expert"] == 0
    assert payload["native_stream_last_issue_expert"] == 220
    assert payload["native_stream_issue_candidate_hash"] == "22488eda926276f7"
    assert payload["native_stream_graph_replay_required"] is True
    assert payload["native_stream_graph_replay"] is True
    assert payload["native_stream_requested_graph_replay"] is True
    assert payload["native_stream_persistent_state_on_device"] is True
    assert payload["native_stream_issue_generation_on_device"] is True
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["payload_transfer_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["kernel_arg_pass"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["current_wna16_arg_compatible"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["production_like_ab_ready"] is True
    assert payload["benchmark_is_current_wna16_fused_moe"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_online_contract_prefers_embedded_stream_dimensions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _summary_with_embedded_contract(),
    )

    def fake_run_stub(args):
        assert args.steps == 64
        assert args.layers == 40
        assert args.experts_per_layer == 225
        assert args.graph_replay is True
        return _native_payload()

    monkeypatch.setattr(contract.stream_stub, "run_stub", fake_run_stub)

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is True
    assert payload["embedded_online_stream_contract_present"] is True
    assert payload["embedded_online_stream_contract_passed"] is True
    assert payload["embedded_online_stream_contract_expected_issue_candidate_count"] == 20160
    assert payload["embedded_online_stream_contract_observed_packet_count"] == 2560
    assert (
        payload[
            "embedded_online_stream_contract_observed_previous_nonempty_packet_count"
        ]
        == 2520
    )
    assert (
        payload["embedded_online_stream_contract_observed_issue_candidate_count"]
        == 20160
    )
    assert payload["online_transition_issue_last_candidate_source"] == (
        "embedded_online_stream_contract"
    )
    assert payload["contract_dimension_sources"]["layer_sources"][
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_layers"
    ] == 40


def test_online_contract_rejects_embedded_issue_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary_with_embedded_contract()
    summary[
        "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_issue_candidate_count"
    ] = 1
    summary[
        "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_issue_candidate_first_expert"
    ] = 2
    summary[
        "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_issue_candidate_last_expert"
    ] = 2
    summary[
        "runtime_shadow_premap_payload_cache_direct_transition_native_packet_last_issue_candidate_hash"
    ] = "0123456789abcdef"
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_issue_last_candidate_count"
    ] = 1
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_issue_last_candidate_first_expert"
    ] = 2
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_issue_last_candidate_last_expert"
    ] = 3
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_issue_last_candidate_hash"
    ] = "fedcba9876543210"
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 20160,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "embedded_issue_last_candidate_last_expert_mismatch" in payload["failures"]
    assert "embedded_issue_last_candidate_hash_mismatch" in payload["failures"]


def test_online_contract_rejects_native_kernel_arg_pass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: _native_payload(
            kernel_arg_pass=True,
            kernel_arg_pass_allowed=True,
        ),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_kernel_arg_pass_mismatch" in payload["failures"]
    assert "native_kernel_arg_pass_allowed_mismatch" in payload["failures"]


def test_online_contract_rejects_native_missing_kernel_arg_pass_allowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())
    native = _native_payload()
    native.pop("kernel_arg_pass_allowed")
    monkeypatch.setattr(contract.stream_stub, "run_stub", lambda args: native)

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_kernel_arg_pass_allowed_mismatch" in payload["failures"]


def test_online_contract_rejects_native_payload_transfer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: _native_payload(payload_transfer_enabled=True),
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_payload_transfer_enabled_mismatch" in payload["failures"]


def test_online_contract_rejects_performance_summary_safety_true(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary()
    summary["kernel_arg_pass_allowed"] = True
    summary["payload_bytes"] = 16
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(contract.stream_stub, "run_stub", lambda args: _native_payload())

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "performance_summary_kernel_arg_pass_allowed_mismatch" in payload["failures"]
    assert "performance_summary_payload_bytes_mismatch" in payload["failures"]


def test_online_contract_rejects_prefixed_performance_summary_safety_true(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary()
    summary["runtime_shadow_premap_payload_cache_direct_payload_bytes"] = 16
    summary[
        "runtime_shadow_premap_payload_cache_direct_payload_transfer_enabled"
    ] = True
    summary[
        "runtime_shadow_premap_payload_cache_direct_payload_transfer_runtime_enabled"
    ] = True
    summary[
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes"
    ] = 32
    summary[
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count"
    ] = 1
    summary[
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_runtime_enabled"
    ] = True
    summary[
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_full_fetch_runtime_allowed"
    ] = True
    summary[
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed"
    ] = True
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(contract.stream_stub, "run_stub", lambda args: _native_payload())

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "performance_summary_direct_payload_bytes_mismatch" in payload["failures"]
    assert (
        "performance_summary_direct_payload_transfer_enabled_mismatch"
        in payload["failures"]
    )
    assert (
        "performance_summary_direct_payload_transfer_runtime_enabled_mismatch"
        in payload["failures"]
    )
    assert (
        "performance_summary_runtime_execution_payload_bytes_mismatch"
        in payload["failures"]
    )
    assert (
        "performance_summary_runtime_execution_issued_payload_count_mismatch"
        in payload["failures"]
    )
    assert (
        "performance_summary_runtime_execution_payload_transfer_runtime_enabled_mismatch"
        in payload["failures"]
    )
    assert (
        "performance_summary_runtime_execution_full_fetch_runtime_allowed_mismatch"
        in payload["failures"]
    )
    assert (
        "performance_summary_runtime_execution_kernel_arg_pass_allowed_mismatch"
        in payload["failures"]
    )


def test_online_contract_rejects_embedded_safety_true(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary_with_embedded_contract()
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_payload_transfer_enabled"
    ] = True
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_kernel_arg_pass_allowed"
    ] = True
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(contract.stream_stub, "run_stub", lambda args: _native_payload())

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "embedded_online_stream_contract_payload_transfer_enabled_mismatch" in payload["failures"]
    assert "embedded_online_stream_contract_kernel_arg_pass_allowed_mismatch" in payload["failures"]


def test_online_contract_rejects_embedded_missing_safety_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary_with_embedded_contract()
    summary.pop(
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_kernel_arg_pass_allowed"
    )
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(contract.stream_stub, "run_stub", lambda args: _native_payload())

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "embedded_online_stream_contract_kernel_arg_pass_allowed_missing" in payload["failures"]


def test_online_contract_rejects_embedded_issue_count_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary_with_embedded_contract()
    summary[
        "runtime_shadow_premap_payload_cache_direct_online_stream_contract_issue_candidate_count"
    ] = 7
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 20160,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "embedded_issue_candidate_count_mismatch" in payload["failures"]


def test_online_contract_rejects_graph_once_per_layer_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        contract,
        "_load_json_object",
        lambda path: _graph_once_per_layer_summary(),
    )
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 20160,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert payload["online_observed_packet_count"] == 40
    assert payload["contract_expected_packet_count"] == 2560
    assert "online_observed_packet_count_mismatch" in payload["failures"]
    assert "online_previous_nonempty_packet_count_mismatch" in payload["failures"]
    assert "online_issue_candidate_count_mismatch" in payload["failures"]


def test_online_contract_rejects_embedded_steps_raw_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary_with_embedded_contract()
    summary["runtime_shadow_premap_payload_cache_direct_online_stream_contract_steps"] = (
        65
    )
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 20480,
            "previous_nonempty_packet_count": 2560,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert any(
        failure.startswith("raw_step_embedded_mismatch:")
        for failure in payload["failures"]
    )


def test_online_contract_rejects_layer_source_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary()
    summary["runtime_shadow_premap_payload_cache_direct_transition_producer_update_count"] = 41
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)

    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 20160,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "producer_update_count_mismatch" in payload["failures"]


def test_online_contract_rejects_missing_required_dimension_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    summary = _summary()
    summary.pop(
        "runtime_shadow_premap_payload_cache_direct_transition_producer_update_count"
    )
    monkeypatch.setattr(contract, "_load_json_object", lambda path: summary)
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 20160,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert (
        "packet_source_missing:"
        "runtime_shadow_premap_payload_cache_direct_transition_producer_update_count"
        in payload["failures"]
    )


def test_online_contract_rejects_expert_source_override_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())

    args = _args(tmp_path, perf)
    args.experts_per_layer = 224
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda stub_args: {
            "ok": True,
            "issue_candidate_count": 20160,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(args)

    assert payload["passed"] is False
    assert any(
        failure.startswith("expert_source_mismatch:")
        for failure in payload["failures"]
    )
    assert payload["contract_dimension_sources"]["all_layer_sources_match"] is True
    assert payload["contract_dimension_sources"]["all_expert_sources_match"] is False


def test_online_contract_rejects_non_divisible_requested_tokens() -> None:
    summary = _summary()
    summary["requested_output_token_count"] = 2050

    with pytest.raises(ValueError, match="divisible"):
        contract._steps_from_summary(summary, override=None)


def test_online_contract_rejects_native_issue_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())
    monkeypatch.setattr(
        contract.stream_stub,
        "run_stub",
        lambda args: {
            "ok": True,
            "issue_candidate_count": 1,
            "previous_nonempty_packet_count": 2520,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
        },
    )

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "issue_candidate_count_mismatch" in payload["failures"]


def test_online_contract_rejects_native_without_graph_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    perf = tmp_path / "performance_summary.json"
    perf.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(contract, "_load_json_object", lambda path: _summary())

    def fake_run_stub(args):
        assert args.graph_replay is True
        return _native_payload(native_graph_replay=False, requested_graph_replay=False)

    monkeypatch.setattr(contract.stream_stub, "run_stub", fake_run_stub)

    payload = contract.build_contract(_args(tmp_path, perf))

    assert payload["passed"] is False
    assert "native_graph_replay_not_enabled" in payload["failures"]
    assert "native_requested_graph_replay_not_enabled" in payload["failures"]
