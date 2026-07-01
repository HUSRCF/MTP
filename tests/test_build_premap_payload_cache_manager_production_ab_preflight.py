from __future__ import annotations

import json
from pathlib import Path

from scripts import build_premap_payload_cache_manager_production_ab_preflight as gate


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _manager_gate_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_manager_useful_work_ab_gate",
        "mode": "payload_cache_manager_useful_work_ab_precondition",
        "passed": True,
        "manager_useful_work_ab_ready": True,
        "payload_runtime_ready": False,
        "performance_claim_ready": False,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "issued_prefetch_count": 133,
        "used_fetch_count": 108,
        "unused_fetch_count": 25,
        "demand_count": 224,
        "demand_hit_count": 199,
        "demand_hit_rate": 0.8883928571428571,
        "used_per_issued_fetch": 0.8120300751879699,
        "source_binding_status": "same_packet_budget",
        "source_binding_same_packet_budget": True,
        "source_binding_producer_expected_packet_count": 224,
        "source_binding_executor_requested_issue_count": 224,
    }
    payload.update(overrides)
    return payload


def _summary_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "generate_seconds_per_requested_output_token": 0.01,
        "sample_count": 8,
        "requested_output_token_count": 512,
        "runtime_shadow_emit_premap_payload_cache_manager_counters": True,
        "runtime_shadow_premap_payload_cache_direct_manager_mode": "ready_time",
        "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed": (
            True
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": (
            False
        ),
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_live_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": (
            False
        ),
    }
    payload.update(overrides)
    return payload


def _run(
    tmp_path: Path,
    manager: dict[str, object],
    baseline: dict[str, object],
    candidate: dict[str, object],
    *,
    require_same_source_packet_budget: bool = False,
) -> dict[str, object]:
    manager_path = tmp_path / "manager.json"
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    _write_json(manager_path, manager)
    _write_json(baseline_path, baseline)
    _write_json(candidate_path, candidate)
    return gate.build_preflight(
        manager_gate_json=manager_path,
        baseline_summary=baseline_path,
        candidate_summary=candidate_path,
        min_sample_count=8,
        max_envelope_overhead_ratio=0.05,
        require_same_source_packet_budget=require_same_source_packet_budget,
    )


def test_manager_production_ab_preflight_accepts_payloadless_harness_ready(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
    )

    assert result["passed"] is True
    assert result["production_like_manager_ab_harness_ready"] is True
    assert result["payload_runtime_ready"] is False
    assert result["performance_claim_ready"] is False
    assert result["manager_used_fetch_count"] == 108
    assert result["manager_source_binding_status"] == "same_packet_budget"
    assert result["manager_source_binding_same_packet_budget"] is True
    assert result["manager_source_binding_require_same_packet_budget"] is False
    assert result["manager_source_binding_producer_expected_packet_count"] == 224
    assert result["manager_source_binding_executor_requested_issue_count"] == 224
    assert result["candidate_manager_counter_enabled"] is True
    assert result["candidate_envelope_overhead_ratio"] > 0
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False


def test_manager_production_ab_preflight_accepts_mixed_source_by_default(
    tmp_path: Path,
) -> None:
    manager = _manager_gate_payload(
        source_binding_status="mixed_source_accounting_only",
        source_binding_same_packet_budget=False,
        source_binding_producer_expected_packet_count=2560,
        source_binding_executor_requested_issue_count=224,
    )
    result = _run(
        tmp_path,
        manager,
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
    )

    assert result["passed"] is True
    assert result["manager_source_binding_status"] == "mixed_source_accounting_only"
    assert result["manager_source_binding_same_packet_budget"] is False
    assert result["manager_source_binding_require_same_packet_budget"] is False
    assert result["manager_source_binding_producer_expected_packet_count"] == 2560
    assert result["manager_source_binding_executor_requested_issue_count"] == 224


def test_manager_production_ab_preflight_accepts_legacy_missing_source_binding_by_default(
    tmp_path: Path,
) -> None:
    manager = _manager_gate_payload()
    for key in (
        "source_binding_status",
        "source_binding_same_packet_budget",
        "source_binding_producer_expected_packet_count",
        "source_binding_executor_requested_issue_count",
    ):
        del manager[key]

    result = _run(
        tmp_path,
        manager,
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
    )

    assert result["passed"] is True
    assert result["manager_source_binding_status"] == "unknown"
    assert result["manager_source_binding_same_packet_budget"] is False
    assert result["manager_source_binding_producer_expected_packet_count"] == 0
    assert result["manager_source_binding_executor_requested_issue_count"] == 0


def test_manager_production_ab_preflight_accepts_required_same_source_budget(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
        require_same_source_packet_budget=True,
    )

    assert result["passed"] is True
    assert result["manager_source_binding_status"] == "same_packet_budget"
    assert result["manager_source_binding_same_packet_budget"] is True
    assert result["manager_source_binding_require_same_packet_budget"] is True


def test_manager_production_ab_preflight_can_require_same_source_budget(
    tmp_path: Path,
) -> None:
    manager = _manager_gate_payload(
        source_binding_status="mixed_source_accounting_only",
        source_binding_same_packet_budget=False,
        source_binding_producer_expected_packet_count=2560,
        source_binding_executor_requested_issue_count=224,
    )
    result = _run(
        tmp_path,
        manager,
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
        require_same_source_packet_budget=True,
    )

    assert result["passed"] is False
    assert "manager_gate_source_binding_same_packet_budget_mismatch" in result[
        "failures"
    ]
    assert "manager_gate_source_binding_status_mismatch" in result["failures"]
    assert result["manager_source_binding_require_same_packet_budget"] is True


def test_manager_production_ab_preflight_strict_rejects_bad_source_binding_counts(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(
            source_binding_producer_expected_packet_count=0,
            source_binding_executor_requested_issue_count=224,
        ),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
        require_same_source_packet_budget=True,
    )

    assert result["passed"] is False
    assert (
        "manager_gate_source_binding_producer_expected_packet_count_invalid"
        in result["failures"]
    )
    assert "manager_gate_source_binding_packet_count_mismatch" in result["failures"]


def test_manager_production_ab_preflight_rejects_invalid_source_binding_type(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(source_binding_same_packet_budget="false"),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
    )

    assert result["passed"] is False
    assert "manager_gate_source_binding_same_packet_budget_invalid" in result[
        "failures"
    ]


def test_manager_production_ab_preflight_rejects_invalid_source_binding_status_type(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(source_binding_status=True),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(generate_seconds_per_requested_output_token=0.0101),
    )

    assert result["passed"] is False
    assert "manager_gate_source_binding_status_invalid" in result["failures"]
    assert result["manager_source_binding_status"] == "unknown"


def test_manager_production_ab_preflight_rejects_unready_manager_gate(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(passed=False),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(),
    )

    assert result["passed"] is False
    assert "manager_gate_passed_mismatch" in result["failures"]


def test_manager_production_ab_preflight_rejects_payload_or_kernel_mutation(
    tmp_path: Path,
) -> None:
    candidate = _summary_payload(
        runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes=1,
        runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed=True,
    )

    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        candidate,
    )

    assert result["passed"] is False
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes_not_zero"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed_not_false"
        in result["failures"]
    )


def test_manager_production_ab_preflight_rejects_ready_and_current_arg_aliases(
    tmp_path: Path,
) -> None:
    candidate = _summary_payload(
        runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit=True,
        runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_enabled=True,
        runtime_shadow_premap_payload_cache_direct_runtime_execution_passed_to_kernel=True,
        runtime_shadow_premap_payload_cache_direct_runtime_execution_uses_current_wna16_args=True,
        runtime_shadow_premap_payload_cache_direct_runtime_execution_passes_current_wna16_args=True,
        runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count=1,
    )

    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        candidate,
    )

    assert result["passed"] is False
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_enabled_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_passed_to_kernel_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_uses_current_wna16_args_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_passes_current_wna16_args_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count_not_zero"
        in result["failures"]
    )


def test_manager_production_ab_preflight_rejects_contract_prefixed_safety_aliases(
    tmp_path: Path,
) -> None:
    candidate = _summary_payload(
        runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_ready_credit=True,
        runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_kernel_arg_pass=True,
        runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed_to_kernel=True,
        runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_uses_current_wna16_args=True,
        runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_payload_bytes=1,
        runtime_shadow_premap_payload_cache_direct_online_inside_graph_producer_boundary_contract_payload_transfer_enabled=True,
        runtime_shadow_premap_payload_cache_direct_online_stream_contract_measures_tpot=True,
    )

    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        candidate,
    )

    assert result["passed"] is False
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_ready_credit_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_kernel_arg_pass_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed_to_kernel_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_uses_current_wna16_args_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_payload_bytes_not_zero"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_online_inside_graph_producer_boundary_contract_payload_transfer_enabled_not_false"
        in result["failures"]
    )
    assert (
        "candidate_summary_runtime_shadow_premap_payload_cache_direct_online_stream_contract_measures_tpot_not_false"
        in result["failures"]
    )


def test_manager_production_ab_preflight_rejects_shape_mismatch(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(requested_output_token_count=1024),
    )

    assert result["passed"] is False
    assert "paired_requested_output_token_count_mismatch" in result["failures"]


def test_manager_production_ab_preflight_rejects_missing_candidate_manager_counters(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
    )

    assert result["passed"] is False
    assert "candidate_manager_counters_not_enabled" in result["failures"]


def test_manager_production_ab_preflight_rejects_missing_producer_contract(
    tmp_path: Path,
) -> None:
    candidate = _summary_payload()
    del candidate[
        "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed"
    ]

    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        candidate,
    )

    assert result["passed"] is False
    assert "candidate_producer_contract_missing" in result["failures"]
    assert "candidate_producer_contract_not_passed" in result["failures"]


def test_manager_production_ab_preflight_rejects_string_booleans(
    tmp_path: Path,
) -> None:
    candidate = _summary_payload(
        runtime_shadow_emit_premap_payload_cache_manager_counters="false",
        runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed="true",
    )

    result = _run(
        tmp_path,
        _manager_gate_payload(),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        candidate,
    )

    assert result["passed"] is False
    assert "candidate_manager_counters_not_enabled" in result["failures"]
    assert "candidate_producer_contract_not_passed" in result["failures"]


def test_manager_production_ab_preflight_rejects_bad_manager_gate_rates(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        _manager_gate_payload(demand_hit_rate="nan", used_per_issued_fetch=2.0),
        _summary_payload(runtime_shadow_emit_premap_payload_cache_manager_counters=False),
        _summary_payload(),
    )

    assert result["passed"] is False
    assert "manager_gate_demand_hit_rate_invalid" in result["failures"]
    assert "manager_gate_used_per_issued_fetch_invalid" in result["failures"]
