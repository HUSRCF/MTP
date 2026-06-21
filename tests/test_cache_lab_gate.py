from __future__ import annotations

import pytest

from mtp_expert_prefetch.runtime import (
    CacheLabGateConfig,
    CacheLabGateDecision,
    CacheLabRuntimeSignals,
    PayloadCacheRuntimeExecutionDryRun,
    PayloadCacheQueueBudgetRuntimeEnvelope,
    PayloadCacheRuntimeParticipation,
    PayloadCacheRuntimePlan,
    build_payload_cache_queue_budget_runtime_envelope,
    build_payload_cache_runtime_execution_dry_run,
    build_payload_cache_runtime_participation,
    build_payload_cache_runtime_plan,
    runtime_plan_status_from_participation,
    select_cache_lab_prefetch_gate,
)


def _signals(**overrides) -> CacheLabRuntimeSignals:
    values = {
        "payload_capacity": 10240,
        "overlap_factor": 0.5,
        "manager_us_per_issue": 50.0,
        "bandwidth_gbps": 6.589,
        "stress_fallback_active": False,
    }
    values.update(overrides)
    return CacheLabRuntimeSignals(**values)


def test_cache_lab_gate_allows_calibrated_normal_envelope() -> None:
    decision = select_cache_lab_prefetch_gate(_signals())

    assert decision.allow_full_fetch_mtp is True
    assert decision.reason == "cache_lab_envelope_allowed"
    assert decision.as_dict()["payload_capacity"] == 10240
    assert decision.as_dict()["ready_time_allow_full_fetch"] is None


def test_cache_lab_gate_ready_time_block_overrides_replay_envelope() -> None:
    decision = select_cache_lab_prefetch_gate(
        _signals(ready_time_allow_full_fetch=False)
    )

    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "ready_time_payload_cache_gate_blocked"


def test_cache_lab_gate_ready_time_allow_still_requires_replay_envelope() -> None:
    allowed = select_cache_lab_prefetch_gate(
        _signals(ready_time_allow_full_fetch=True)
    )
    below_capacity = select_cache_lab_prefetch_gate(
        _signals(payload_capacity=8192, ready_time_allow_full_fetch=True)
    )

    assert allowed.allow_full_fetch_mtp is True
    assert allowed.reason == "cache_lab_envelope_allowed"
    assert below_capacity.allow_full_fetch_mtp is False
    assert below_capacity.reason == "payload_capacity_below_gate"


def test_cache_lab_gate_decision_new_field_defaults_to_none() -> None:
    decision = CacheLabGateDecision(
        allow_full_fetch_mtp=True,
        reason="cache_lab_envelope_allowed",
        payload_capacity=10240,
        overlap_factor=0.5,
        manager_us_per_issue=50.0,
        bandwidth_gbps=6.589,
        stress_fallback_active=False,
    )

    assert decision.ready_time_allow_full_fetch is None


def test_cache_lab_gate_rejects_below_positive_capacity() -> None:
    decision = select_cache_lab_prefetch_gate(_signals(payload_capacity=8192))

    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "payload_capacity_below_gate"


def test_cache_lab_gate_rejects_low_overlap() -> None:
    decision = select_cache_lab_prefetch_gate(_signals(overlap_factor=0.49))

    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "overlap_below_gate"


def test_cache_lab_gate_rejects_high_manager_overhead() -> None:
    decision = select_cache_lab_prefetch_gate(_signals(manager_us_per_issue=50.1))

    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "manager_overhead_above_gate"


def test_cache_lab_gate_rejects_outside_bandwidth_calibration_range() -> None:
    low = select_cache_lab_prefetch_gate(_signals(bandwidth_gbps=2.9))
    high = select_cache_lab_prefetch_gate(_signals(bandwidth_gbps=12.1))

    assert low.allow_full_fetch_mtp is False
    assert low.reason == "bandwidth_below_calibrated_range"
    assert high.allow_full_fetch_mtp is False
    assert high.reason == "bandwidth_above_calibrated_range"


def test_cache_lab_gate_rejects_stress_fallback_when_required() -> None:
    decision = select_cache_lab_prefetch_gate(_signals(stress_fallback_active=True))

    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "stress_fallback_active"


def test_cache_lab_gate_can_disable_stress_fallback_guard_for_analysis() -> None:
    decision = select_cache_lab_prefetch_gate(
        _signals(stress_fallback_active=True),
        config=CacheLabGateConfig(require_stress_fallback_clear=False),
    )

    assert decision.allow_full_fetch_mtp is True


def test_payload_cache_runtime_participation_keeps_candidate_payloadless() -> None:
    participation = build_payload_cache_runtime_participation(
        manager_mode="ready_time",
        issue_sources=["prelaunch_observed_transition_premap_shadow"],
        demand_on_consumer=True,
        issued_fetch_count=12,
        used_fetch_count=5,
        demand_count=9,
        demand_hit_count=5,
        ready_late_miss_count=0,
        candidate_reason="candidate_requires_ready_time_gate",
        queue_batch_size=8,
        queue_deadline_us=1000.0,
    )

    payload = participation.as_dict()
    assert payload["present"] is True
    assert payload["stage"] == "online_ready_time_payload_cache_runtime_participation_dry_run"
    assert payload["status"] == "ready_time_candidate_requires_lab_gate"
    assert payload["consumes_manager_snapshot"] is True
    assert payload["issue_sources"] == ("prelaunch_observed_transition_premap_shadow",)
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["queue_batch_size"] == 8
    assert payload["queue_deadline_us"] == 1000.0


def test_payload_cache_runtime_participation_rejects_side_effectful_construction() -> None:
    with pytest.raises(ValueError, match="payloadless"):
        PayloadCacheRuntimeParticipation(
            present=True,
            stage="bad",
            status="bad",
            consumes_manager_snapshot=True,
            manager_mode="ready_time",
            issue_sources=(),
            demand_on_consumer=True,
            payload_bytes=1,
        )


def test_payload_cache_runtime_participation_marks_non_ready_time_accounting_only() -> None:
    participation = build_payload_cache_runtime_participation(
        manager_mode="resident",
        issue_sources=["previous_token_transition_premap_shadow"],
        demand_on_consumer=False,
        issued_fetch_count=1,
        used_fetch_count=0,
        demand_count=2,
        demand_hit_count=0,
        ready_late_miss_count=0,
        candidate_reason="not_ready_time_manager:resident",
    )

    assert participation.stage == "online_payload_cache_runtime_participation_dry_run"
    assert participation.status == "accounting_only_not_ready_time_manager:resident"
    assert participation.payload_bytes == 0
    assert participation.full_fetch_runtime_allowed is False


def test_payload_cache_runtime_plan_blocks_ready_time_candidate() -> None:
    participation = build_payload_cache_runtime_participation(
        manager_mode="ready_time",
        issue_sources=["prelaunch_observed_transition_premap_shadow"],
        demand_on_consumer=True,
        issued_fetch_count=12,
        used_fetch_count=5,
        demand_count=9,
        demand_hit_count=5,
        ready_late_miss_count=0,
        candidate_reason="candidate_requires_ready_time_gate",
    )

    plan = build_payload_cache_runtime_plan(participation)
    payload = plan.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_runtime_plan_lab_gate_dry_run"
    assert payload["status"] == (
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    assert payload["participation_status"] == "ready_time_candidate_requires_lab_gate"
    assert payload["consumes_participation"] is True
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["planned_issue_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False


def test_payload_cache_runtime_plan_formats_accounting_only_status() -> None:
    participation = build_payload_cache_runtime_participation(
        manager_mode="ready_time",
        issue_sources=["prelaunch_observed_transition_premap_shadow"],
        demand_on_consumer=True,
        issued_fetch_count=12,
        used_fetch_count=0,
        demand_count=9,
        demand_hit_count=5,
        ready_late_miss_count=0,
        candidate_reason="no_used_fetch",
    )

    plan = build_payload_cache_runtime_plan(participation)

    assert plan.status == "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    assert (
        runtime_plan_status_from_participation(participation.status)
        == plan.status
    )


def test_payload_cache_runtime_plan_rejects_side_effectful_construction() -> None:
    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheRuntimePlan(
            present=True,
            stage="payload_cache_runtime_plan_lab_gate_dry_run",
            status="participation_not_full_fetch_candidate:accounting_only_no_used_fetch",
            consumes_participation=True,
            participation_status="accounting_only_no_used_fetch",
            payload_bytes=1,
        )

    with pytest.raises(ValueError, match="status"):
        PayloadCacheRuntimePlan(
            present=True,
            stage="payload_cache_runtime_plan_lab_gate_dry_run",
            status="participation_not_full_fetch_candidate:accounting_only_no_used_fetch",
            consumes_participation=True,
            participation_status="ready_time_candidate_requires_lab_gate",
        )

    with pytest.raises(ValueError, match="present"):
        PayloadCacheRuntimePlan(
            present=False,
            stage="payload_cache_runtime_plan_lab_gate_dry_run",
            status="participation_not_full_fetch_candidate:accounting_only_no_used_fetch",
            consumes_participation=True,
            participation_status="accounting_only_no_used_fetch",
        )


def test_payload_cache_queue_budget_runtime_envelope_keeps_payloadless_boundary() -> None:
    envelope = build_payload_cache_queue_budget_runtime_envelope(
        cell_count=16,
        event_timing_mode="token_index",
        first_model_passing_capacity=4096,
        first_model_passing_issue_lead_tokens=32,
        first_model_passing_queue_deadline_us=100.0,
        first_model_passing_lookahead_us=2_400_000.0,
        shifted_issue_accounting_enabled=True,
        shifted_issue_accounted_packet_count=28,
        shifted_issue_unique_issue_key_count=16,
    )
    payload = envelope.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_queue_budget_runtime_envelope_lab_gate"
    assert payload["status"] == "model_queue_budget_satisfied_runtime_disabled"
    assert payload["consumes_queue_budget_sweep"] is True
    assert payload["execution_mode"] == "payloadless_queue_budget_lab_gate"
    assert payload["event_timing_mode"] == "token_index"
    assert payload["cell_count"] == 16
    assert payload["first_model_passing_capacity"] == 4096
    assert payload["first_model_passing_issue_lead_tokens"] == 32
    assert payload["first_model_passing_queue_deadline_us"] == 100.0
    assert payload["first_model_passing_lookahead_us"] == 2_400_000.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["payload_bytes"] == 0
    assert payload["payload_transfer_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["full_fetch_allowed"] is False
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_payload_cache_queue_budget_runtime_envelope_rejects_side_effects() -> None:
    with pytest.raises(ValueError, match="payloadless"):
        PayloadCacheQueueBudgetRuntimeEnvelope(
            present=True,
            stage="payload_cache_queue_budget_runtime_envelope_lab_gate",
            status="model_queue_budget_satisfied_runtime_disabled",
            consumes_queue_budget_sweep=True,
            event_timing_mode="token_index",
            cell_count=16,
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
            payload_bytes=1,
        )

    with pytest.raises(ValueError, match="token_index"):
        PayloadCacheQueueBudgetRuntimeEnvelope(
            present=True,
            stage="payload_cache_queue_budget_runtime_envelope_lab_gate",
            status="model_queue_budget_satisfied_runtime_disabled",
            consumes_queue_budget_sweep=True,
            event_timing_mode="wall_time",
            cell_count=16,
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )

    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheQueueBudgetRuntimeEnvelope(
            present=True,
            stage="payload_cache_queue_budget_runtime_envelope_lab_gate",
            status="model_queue_budget_satisfied_runtime_disabled",
            consumes_queue_budget_sweep=True,
            event_timing_mode="token_index",
            cell_count=16,
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
            kernel_arg_pass_allowed=True,
        )


def test_payload_cache_queue_budget_runtime_envelope_builder_is_strict() -> None:
    with pytest.raises(TypeError, match="cell_count"):
        build_payload_cache_queue_budget_runtime_envelope(
            cell_count="16",  # type: ignore[arg-type]
            event_timing_mode="token_index",
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )

    with pytest.raises(TypeError, match="first_model_passing_capacity"):
        build_payload_cache_queue_budget_runtime_envelope(
            cell_count=16,
            event_timing_mode="token_index",
            first_model_passing_capacity=4096.5,  # type: ignore[arg-type]
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )

    with pytest.raises(TypeError, match="shifted_issue_accounting_enabled"):
        build_payload_cache_queue_budget_runtime_envelope(
            cell_count=16,
            event_timing_mode="token_index",
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled="true",  # type: ignore[arg-type]
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )

    with pytest.raises(ValueError, match="lookahead"):
        build_payload_cache_queue_budget_runtime_envelope(
            cell_count=16,
            event_timing_mode="token_index",
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=100.0,
            first_model_passing_lookahead_us=float("nan"),
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )

    with pytest.raises(ValueError, match="deadline"):
        PayloadCacheQueueBudgetRuntimeEnvelope(
            present=True,
            stage="payload_cache_queue_budget_runtime_envelope_lab_gate",
            status="model_queue_budget_satisfied_runtime_disabled",
            consumes_queue_budget_sweep=True,
            event_timing_mode="token_index",
            cell_count=16,
            first_model_passing_capacity=4096,
            first_model_passing_issue_lead_tokens=32,
            first_model_passing_queue_deadline_us=float("inf"),
            first_model_passing_lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )


def test_payload_cache_runtime_execution_dry_run_consumes_plan() -> None:
    participation = build_payload_cache_runtime_participation(
        manager_mode="ready_time",
        issue_sources=["prelaunch_observed_transition_premap_shadow"],
        demand_on_consumer=True,
        issued_fetch_count=12,
        used_fetch_count=5,
        demand_count=9,
        demand_hit_count=5,
        ready_late_miss_count=0,
        candidate_reason="candidate_requires_ready_time_gate",
    )
    plan = build_payload_cache_runtime_plan(participation)

    execution = build_payload_cache_runtime_execution_dry_run(plan)
    payload = execution.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_runtime_execution_lab_gate_dry_run"
    assert payload["status"] == f"blocked_by_runtime_plan:{plan.status}"
    assert payload["plan_status"] == plan.status
    assert payload["consumes_plan"] is True
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == plan.status
    assert payload["execution_mode"] == "payloadless_lab_gate_dry_run"
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False


def test_payload_cache_runtime_execution_dry_run_rejects_side_effects() -> None:
    plan_status = "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheRuntimeExecutionDryRun(
            present=True,
            stage="payload_cache_runtime_execution_lab_gate_dry_run",
            status=f"blocked_by_runtime_plan:{plan_status}",
            consumes_plan=True,
            plan_status=plan_status,
            payload_bytes=1,
        )

    with pytest.raises(ValueError, match="status"):
        PayloadCacheRuntimeExecutionDryRun(
            present=True,
            stage="payload_cache_runtime_execution_lab_gate_dry_run",
            status="not_blocked",
            consumes_plan=True,
            plan_status=plan_status,
        )

    with pytest.raises(ValueError, match="decision"):
        PayloadCacheRuntimeExecutionDryRun(
            present=True,
            stage="payload_cache_runtime_execution_lab_gate_dry_run",
            status=f"blocked_by_runtime_plan:{plan_status}",
            consumes_plan=True,
            plan_status=plan_status,
            decision="execute",
        )

    with pytest.raises(ValueError, match="block reason"):
        PayloadCacheRuntimeExecutionDryRun(
            present=True,
            stage="payload_cache_runtime_execution_lab_gate_dry_run",
            status=f"blocked_by_runtime_plan:{plan_status}",
            consumes_plan=True,
            plan_status=plan_status,
            block_reason="other",
        )

    with pytest.raises(TypeError, match="block_reason"):
        PayloadCacheRuntimeExecutionDryRun(
            present=True,
            stage="payload_cache_runtime_execution_lab_gate_dry_run",
            status=f"blocked_by_runtime_plan:{plan_status}",
            consumes_plan=True,
            plan_status=plan_status,
            block_reason=None,  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="mode"):
        PayloadCacheRuntimeExecutionDryRun(
            present=True,
            stage="payload_cache_runtime_execution_lab_gate_dry_run",
            status=f"blocked_by_runtime_plan:{plan_status}",
            consumes_plan=True,
            plan_status=plan_status,
            execution_mode="live",
        )
