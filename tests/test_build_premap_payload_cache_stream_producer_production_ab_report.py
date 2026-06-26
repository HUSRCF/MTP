from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pytest

from scripts import (
    build_premap_payload_cache_stream_producer_production_ab_report as report,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _args(tmp_path: Path, baseline: Path, candidate: Path, contract: Path) -> argparse.Namespace:
    return argparse.Namespace(
        baseline_summary=baseline,
        candidate_summary=candidate,
        online_contract=contract,
        output_json=tmp_path / "report.json",
        max_overhead_ratio=0.02,
    )


def _valid_contract_fields() -> dict[str, object]:
    return {
        "passed": True,
        "contract_expected_issue_candidate_count": 20160,
        "native_stream_issue_candidate_count": 20160,
        "native_stream_issue_candidate_hash": "22488eda926276f7",
        "native_stream_persistent_state_on_device": True,
        "native_stream_issue_generation_on_device": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
    }


def test_production_ab_report_accepts_low_overhead_contract(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(
        baseline,
        {
            "generate_seconds_per_requested_output_token": 0.00326,
            "sample_count": 32,
            "requested_output_token_count": 2048,
        },
    )
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 0.003265,
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "runtime_shadow_premap_payload_cache_direct_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
            "runtime_shadow_premap_payload_cache_direct_transition_native_packet_count": 40,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_descriptor_count": 0,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_previous_nonempty_count": 0,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_last_candidate_count": 0,
            "runtime_shadow_premap_payload_cache_direct_transition_issue_last_candidate_hash": None,
        },
    )
    _write_json(
        contract,
        {
            "passed": True,
            "contract_steps": 64,
            "contract_layers": 40,
            "contract_experts_per_layer": 225,
            "contract_expected_issue_candidate_count": 20160,
            "online_transition_issue_last_candidate_present": False,
            "online_transition_issue_last_candidate_source": "performance_summary",
            "online_transition_issue_last_candidate_count": 0,
            "online_transition_issue_last_candidate_first_expert": -1,
            "online_transition_issue_last_candidate_last_expert": -1,
            "online_transition_issue_last_candidate_hash": None,
            "native_stream_issue_candidate_count": 20160,
            "native_stream_first_issue_expert": 0,
            "native_stream_last_issue_expert": 220,
            "native_stream_issue_candidate_hash": "22488eda926276f7",
            "native_stream_previous_nonempty_packet_count": 2520,
            "native_stream_persistent_state_on_device": True,
            "native_stream_issue_generation_on_device": True,
            "native_stream_vectorized_copy_used": False,
            "native_stream_graph_replay_required": True,
            "native_stream_graph_replay": True,
            "native_stream_requested_graph_replay": True,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "native_stream_is_current_wna16_fused_moe": False,
            "native_stream_measures_tpot": False,
        },
    )

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is True
    assert payload["candidate_overhead_percent"] < 2.0
    assert payload["online_contract_passed"] is True
    assert payload["online_transition_issue_last_candidate_present"] is False
    assert payload["online_transition_issue_last_candidate_source"] == (
        "performance_summary"
    )
    assert payload["online_transition_issue_last_candidate_count"] == 0
    assert payload["native_stream_issue_candidate_count"] == 20160
    assert payload["native_stream_first_issue_expert"] == 0
    assert payload["native_stream_last_issue_expert"] == 220
    assert payload["native_stream_issue_candidate_hash"] == "22488eda926276f7"
    assert payload["benchmark_is_current_wna16_fused_moe"] is True
    assert payload["measures_tpot"] is True
    assert payload["native_stream_graph_replay_required"] is True
    assert payload["native_stream_graph_replay"] is True
    assert payload["native_stream_requested_graph_replay"] is True
    assert payload["native_stream_is_current_wna16_fused_moe"] is False
    assert payload["native_stream_measures_tpot"] is False
    assert payload["payload_bytes"] == 0
    assert payload["passed_to_kernel"] is False
    assert payload["uses_current_wna16_args"] is False


def test_production_ab_report_rejects_high_overhead(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(candidate, {"generate_seconds_per_requested_output_token": 1.1})
    _write_json(contract, {"passed": True})

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "tpot_overhead_over_threshold" in payload["failures"]


def test_production_ab_report_rejects_contract_failure(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(candidate, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(contract, {"passed": False})

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "online_contract_failed" in payload["failures"]


def test_production_ab_report_rejects_non_bool_contract_passed(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(candidate, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(contract, {"passed": "true"})

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "online_contract_failed" in payload["failures"]


def test_production_ab_report_rejects_payload_or_kernel_arg_candidate(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 128,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": True,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": True,
        },
    )
    _write_json(contract, {"passed": True})

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "candidate_payload_bytes_nonzero" in payload["failures"]
    assert "candidate_kernel_arg_pass_enabled" in payload["failures"]
    assert "candidate_changes_kernel_launch_args" in payload["failures"]


def test_production_ab_report_rejects_missing_candidate_safety_fields(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(candidate, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(contract, {"passed": True})

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "candidate_payload_bytes_missing" in payload["failures"]
    assert "candidate_kernel_arg_pass_missing" in payload["failures"]
    assert "candidate_changes_kernel_launch_args_missing" in payload["failures"]


def test_production_ab_report_rejects_missing_contract_safety_fields(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    _write_json(contract, {"passed": True})

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "contract_payload_bytes_missing" in payload["failures"]
    assert "contract_ready_credit_missing" in payload["failures"]
    assert "contract_passed_to_kernel_missing" in payload["failures"]
    assert "contract_changes_kernel_launch_args_missing" in payload["failures"]
    assert "contract_uses_current_wna16_args_missing" in payload["failures"]
    assert "contract_passes_current_wna16_args_missing" in payload["failures"]
    assert "contract_native_stream_graph_replay_required_missing" in payload[
        "failures"
    ]
    assert "contract_native_stream_graph_replay_missing" in payload["failures"]
    assert "contract_native_stream_requested_graph_replay_missing" in payload[
        "failures"
    ]
    assert "contract_native_stream_is_current_wna16_fused_moe_missing" in payload[
        "failures"
    ]
    assert "contract_native_stream_measures_tpot_missing" in payload["failures"]


def test_production_ab_report_rejects_native_stream_wna16_or_tpot_contract(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    _write_json(
        contract,
        {
            "passed": True,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "native_stream_graph_replay_required": True,
            "native_stream_graph_replay": True,
            "native_stream_requested_graph_replay": True,
            "native_stream_is_current_wna16_fused_moe": True,
            "native_stream_measures_tpot": True,
        },
    )

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "contract_native_stream_is_current_wna16_fused_moe_not_false" in payload[
        "failures"
    ]
    assert "contract_native_stream_measures_tpot_not_false" in payload["failures"]


def test_production_ab_report_rejects_issue_stream_mismatch_or_missing_hash(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    contract_payload = _valid_contract_fields()
    contract_payload["native_stream_issue_candidate_count"] = 1
    contract_payload["native_stream_issue_candidate_hash"] = ""
    _write_json(contract, contract_payload)

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "contract_native_stream_issue_candidate_count_mismatch" in payload[
        "failures"
    ]
    assert "contract_native_stream_issue_candidate_hash_empty" in payload["failures"]


def test_production_ab_report_rejects_non_graph_replay_contract(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    _write_json(
        contract,
        {
            "passed": True,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "native_stream_graph_replay_required": True,
            "native_stream_graph_replay": False,
            "native_stream_requested_graph_replay": False,
            "native_stream_is_current_wna16_fused_moe": False,
            "native_stream_measures_tpot": False,
        },
    )

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert "contract_native_stream_graph_replay_not_true" in payload["failures"]
    assert "contract_native_stream_requested_graph_replay_not_true" in payload[
        "failures"
    ]


@pytest.mark.parametrize(
    ("field", "value", "expected_failure"),
    [
        (
            "native_stream_graph_replay_required",
            False,
            "contract_native_stream_graph_replay_required_not_true",
        ),
        (
            "native_stream_graph_replay_required",
            "true",
            "contract_native_stream_graph_replay_required_not_bool",
        ),
        (
            "native_stream_graph_replay",
            "true",
            "contract_native_stream_graph_replay_not_bool",
        ),
        (
            "native_stream_requested_graph_replay",
            1,
            "contract_native_stream_requested_graph_replay_not_bool",
        ),
    ],
)
def test_production_ab_report_rejects_invalid_graph_replay_contract_fields(
    tmp_path: Path,
    field: str,
    value: object,
    expected_failure: str,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    contract_payload = {
        "passed": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "native_stream_graph_replay_required": True,
        "native_stream_graph_replay": True,
        "native_stream_requested_graph_replay": True,
        "native_stream_is_current_wna16_fused_moe": False,
        "native_stream_measures_tpot": False,
    }
    contract_payload[field] = value
    _write_json(contract, contract_payload)

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert expected_failure in payload["failures"]


@pytest.mark.parametrize("bad_payload_bytes", [True, "0", -1, 0.5, math.inf])
def test_production_ab_report_rejects_invalid_integer_safety_fields(
    tmp_path: Path,
    bad_payload_bytes: object,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": bad_payload_bytes,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    _write_json(
        contract,
        {
            "passed": True,
            "payload_bytes": 0,
            "ready_credit": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "native_stream_graph_replay_required": True,
            "native_stream_graph_replay": True,
            "native_stream_requested_graph_replay": True,
            "native_stream_is_current_wna16_fused_moe": False,
            "native_stream_measures_tpot": False,
        },
    )

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is False
    assert any(
        failure.startswith("candidate_payload_bytes_")
        for failure in payload["failures"]
    )


def test_production_ab_report_accepts_integral_float_payload_bytes(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(baseline, {"generate_seconds_per_requested_output_token": 1.0})
    _write_json(
        candidate,
        {
            "generate_seconds_per_requested_output_token": 1.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0.0,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": False,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": False,
        },
    )
    _write_json(
        contract,
        {
            **_valid_contract_fields(),
            "payload_bytes": 0.0,
        },
    )

    payload = report.build_report(_args(tmp_path, baseline, candidate, contract))

    assert payload["passed"] is True
    assert payload["candidate_payload_bytes"] == 0
    assert payload["payload_bytes"] == 0


@pytest.mark.parametrize(
    ("baseline_tpot", "candidate_tpot", "match"),
    [
        (math.nan, 1.0, "baseline TPOT"),
        (1.0, math.nan, "candidate TPOT"),
        (math.inf, 1.0, "baseline TPOT"),
        (1.0, math.inf, "candidate TPOT"),
        (1.0, 0.0, "candidate TPOT"),
        (0.0, 1.0, "baseline TPOT"),
    ],
)
def test_production_ab_report_rejects_non_finite_or_non_positive_tpot(
    tmp_path: Path,
    baseline_tpot: float,
    candidate_tpot: float,
    match: str,
) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    contract = tmp_path / "contract.json"
    _write_json(
        baseline,
        {"generate_seconds_per_requested_output_token": baseline_tpot},
    )
    _write_json(
        candidate,
        {"generate_seconds_per_requested_output_token": candidate_tpot},
    )
    _write_json(contract, {"passed": True})

    with pytest.raises(ValueError, match=match):
        report.build_report(_args(tmp_path, baseline, candidate, contract))
