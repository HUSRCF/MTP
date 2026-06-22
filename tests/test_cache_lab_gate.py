from __future__ import annotations

import pytest

from mtp_expert_prefetch.runtime import (
    CacheLabGateConfig,
    CacheLabGateDecision,
    CacheLabRuntimeSignals,
    PayloadCacheLivePayloadRuntimeDisabledCanary,
    PayloadCacheLivePayloadStagePreflight,
    PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary,
    PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary,
    PayloadCacheLiveRuntimeAdapterMaterializationPreflight,
    PayloadCacheLiveRuntimeAdapterInstantiationCanary,
    PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight,
    PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan,
    PayloadCacheLiveRuntimeAdapterObjectShellEvidence,
    PayloadCacheLiveRuntimeAdapterOperationRejectionCanary,
    PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary,
    PayloadCacheLiveRuntimeAdapterPayloadTransferToggleDisabledCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueRequestBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssuePlanDryRun,
    PayloadCacheLiveRuntimeAdapterPayloadIssueExecutorDryRun,
    PayloadCacheLiveRuntimeAdapterPayloadIssueQueueEntryDryRun,
    PayloadCacheLiveRuntimeAdapterPayloadIssueQueueSubmitBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueInflightAdmissionBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueSchedulerDispatchBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueCommandPacketDryRun,
    PayloadCacheLiveRuntimeAdapterPayloadIssueTransportEnqueueBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueTransportWorkerDispatchBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDryRun,
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorSubmitBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDispatchBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorExecutionBlockedCanary,
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyCompletionBlockedCanary,
    PayloadCacheLiveRuntimeAdapterStateObjectPreflight,
    PayloadCacheLiveRuntimeAdapterStateValidationArtifact,
    PayloadCacheLiveRuntimeAdapterStateValidationPreflight,
    PayloadCacheLiveRuntimeObjectAdapterPreflight,
    PayloadCacheLiveRuntimeObjectConstructionPreflight,
    PayloadCacheLiveRuntimeStateShapeCheck,
    PayloadCacheManagerImplementationArtifact,
    PayloadCacheManagerRuntimeSnapshotArtifact,
    PayloadCacheManagerRuntimeSkeleton,
    PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary,
    PayloadCacheSnapshotBackedLiveRuntimePreflight,
    PayloadCacheRuntimeExecutionDryRun,
    PayloadCacheQueueBudgetRuntimeEnvelope,
    PayloadCacheRuntimeParticipation,
    PayloadCacheRuntimePlan,
    build_payload_cache_manager_implementation_artifact,
    build_payload_cache_manager_runtime_snapshot_artifact,
    build_payload_cache_manager_runtime_skeleton,
    build_payload_cache_live_runtime_adapter_materialization_preflight,
    build_payload_cache_live_runtime_adapter_instantiation_canary,
    build_payload_cache_live_runtime_adapter_constructor_binding_preflight,
    build_payload_cache_live_runtime_adapter_instance_construction_plan,
    build_payload_cache_live_runtime_adapter_object_shell_evidence,
    build_payload_cache_live_runtime_adapter_operation_rejection_canary,
    build_payload_cache_live_runtime_adapter_state_object_preflight,
    build_payload_cache_live_runtime_adapter_state_validation_artifact,
    build_payload_cache_live_runtime_adapter_state_validation_preflight,
    build_payload_cache_live_runtime_object_adapter_preflight,
    build_payload_cache_live_runtime_object_construction_preflight,
    build_payload_cache_live_runtime_state_shape_check,
    build_payload_cache_snapshot_backed_live_runtime_disabled_canary,
    build_payload_cache_snapshot_backed_live_runtime_preflight,
    build_payload_cache_live_payload_runtime_disabled_canary,
    build_payload_cache_live_payload_stage_preflight,
    build_payload_cache_live_runtime_adapter_accounting_dry_run_canary,
    build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary,
    build_payload_cache_live_runtime_adapter_payloadless_instance_canary,
    build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary,
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


def test_payload_cache_live_payload_stage_preflight_consumes_envelope() -> None:
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

    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    payload = preflight.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_payload_stage_preflight"
    assert payload["status"] == (
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    assert payload["queue_budget_envelope_status"] == envelope.status
    assert payload["consumes_queue_budget_runtime_envelope"] is True
    assert payload["queue_budget_capacity_entries"] == 4096
    assert payload["queue_budget_issue_lead_tokens"] == 32
    assert payload["queue_budget_queue_deadline_us"] == 100.0
    assert payload["queue_budget_lookahead_us"] == 2_400_000.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_payload_runtime_disabled"
    assert payload["execution_mode"] == "payloadless_live_payload_stage_preflight"
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def _live_payload_stage_preflight_kwargs() -> dict[str, object]:
    status = "model_queue_budget_satisfied_runtime_disabled"
    return {
        "present": True,
        "stage": "payload_cache_live_payload_stage_preflight",
        "status": f"blocked_by_queue_budget_runtime_envelope:{status}",
        "consumes_queue_budget_runtime_envelope": True,
        "queue_budget_envelope_status": status,
        "queue_budget_capacity_entries": 4096,
        "queue_budget_issue_lead_tokens": 32,
        "queue_budget_queue_deadline_us": 100.0,
        "queue_budget_lookahead_us": 2_400_000.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }


def test_payload_cache_live_payload_stage_preflight_rejects_side_effects() -> None:
    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLivePayloadStagePreflight(
            **_live_payload_stage_preflight_kwargs(),
            payload_bytes=1,
        )

    with pytest.raises(ValueError, match="decision"):
        PayloadCacheLivePayloadStagePreflight(
            **_live_payload_stage_preflight_kwargs(),
            decision="execute",
        )

    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheLivePayloadStagePreflight(
            **_live_payload_stage_preflight_kwargs(),
            kernel_arg_pass_allowed=True,
        )

    with pytest.raises(ValueError, match="payload_deref_allowed"):
        PayloadCacheLivePayloadStagePreflight(
            **_live_payload_stage_preflight_kwargs(),
            payload_deref_allowed=True,
        )

    with pytest.raises(ValueError, match="queue_budget_capacity_entries"):
        PayloadCacheLivePayloadStagePreflight(
            **{
                **_live_payload_stage_preflight_kwargs(),
                "queue_budget_capacity_entries": 0,
            },
        )

    with pytest.raises(TypeError, match="envelope"):
        build_payload_cache_live_payload_stage_preflight(object())  # type: ignore[arg-type]


def _live_payload_runtime_canary_kwargs() -> dict[str, object]:
    live_status = (
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    return {
        "present": True,
        "stage": "payload_cache_live_payload_runtime_disabled_canary",
        "status": f"blocked_by_live_payload_stage:{live_status}",
        "consumes_live_payload_stage_preflight": True,
        "live_payload_stage_status": live_status,
        "queue_budget_capacity_entries": 4096,
        "queue_budget_issue_lead_tokens": 32,
        "queue_budget_queue_deadline_us": 100.0,
        "queue_budget_lookahead_us": 2_400_000.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }


def test_payload_cache_live_payload_runtime_disabled_canary_consumes_preflight() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)

    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_payload_runtime_disabled_canary"
    assert payload["status"] == f"blocked_by_live_payload_stage:{preflight.status}"
    assert payload["consumes_live_payload_stage_preflight"] is True
    assert payload["live_payload_stage_status"] == preflight.status
    assert payload["queue_budget_capacity_entries"] == 4096
    assert payload["queue_budget_issue_lead_tokens"] == 32
    assert payload["queue_budget_queue_deadline_us"] == 100.0
    assert payload["queue_budget_lookahead_us"] == 2_400_000.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_payload_runtime_disabled"
    assert payload["execution_mode"] == "payloadless_live_payload_runtime_disabled_canary"
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_payload_cache_live_payload_runtime_disabled_canary_rejects_side_effects() -> None:
    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **_live_payload_runtime_canary_kwargs(),
            payload_bytes=1,
        )

    with pytest.raises(ValueError, match="payload_deref_allowed"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **_live_payload_runtime_canary_kwargs(),
            payload_deref_allowed=True,
        )

    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **_live_payload_runtime_canary_kwargs(),
            kernel_arg_pass_allowed=True,
        )

    with pytest.raises(ValueError, match="consume"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **{
                **_live_payload_runtime_canary_kwargs(),
                "consumes_live_payload_stage_preflight": False,
            },
        )

    with pytest.raises(ValueError, match="status"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **{
                **_live_payload_runtime_canary_kwargs(),
                "status": "blocked_by_live_payload_stage:stale_status",
            },
        )

    with pytest.raises(ValueError, match="queue_budget_capacity_entries"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **{
                **_live_payload_runtime_canary_kwargs(),
                "queue_budget_capacity_entries": 0,
            },
        )

    with pytest.raises(ValueError, match="shifted issue accounting"):
        PayloadCacheLivePayloadRuntimeDisabledCanary(
            **{
                **_live_payload_runtime_canary_kwargs(),
                "shifted_issue_accounting_enabled": False,
            },
        )

    with pytest.raises(TypeError, match="preflight"):
        build_payload_cache_live_payload_runtime_disabled_canary(
            object(),  # type: ignore[arg-type]
            build_payload_cache_queue_budget_runtime_envelope(
                cell_count=16,
                event_timing_mode="token_index",
                first_model_passing_capacity=4096,
                first_model_passing_issue_lead_tokens=32,
                first_model_passing_queue_deadline_us=100.0,
                first_model_passing_lookahead_us=2_400_000.0,
                shifted_issue_accounting_enabled=True,
                shifted_issue_accounted_packet_count=28,
                shifted_issue_unique_issue_key_count=16,
            ),
        )

    with pytest.raises(TypeError, match="envelope"):
        build_payload_cache_live_payload_runtime_disabled_canary(
            PayloadCacheLivePayloadStagePreflight(**_live_payload_stage_preflight_kwargs()),
            object(),  # type: ignore[arg-type]
        )


def test_payload_cache_live_payload_runtime_disabled_canary_rejects_status_mismatch() -> None:
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
    preflight = PayloadCacheLivePayloadStagePreflight(
        **{
            **_live_payload_stage_preflight_kwargs(),
            "status": "blocked_by_queue_budget_runtime_envelope:other_status",
            "queue_budget_envelope_status": "other_status",
        },
    )

    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_payload_runtime_disabled_canary(preflight, envelope)

    mismatched_preflight = PayloadCacheLivePayloadStagePreflight(
        **{
            **_live_payload_stage_preflight_kwargs(),
            "queue_budget_capacity_entries": 8192,
        },
    )

    with pytest.raises(ValueError, match="capacity mismatch"):
        build_payload_cache_live_payload_runtime_disabled_canary(
            mismatched_preflight,
            envelope,
        )


def test_payload_cache_manager_implementation_artifact_rejects_cross_chain() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = PayloadCacheLivePayloadRuntimeDisabledCanary(
        **{
            **_live_payload_runtime_canary_kwargs(),
            "queue_budget_capacity_entries": 8192,
        },
    )

    with pytest.raises(ValueError, match="capacity mismatch"):
        build_payload_cache_manager_implementation_artifact(canary, envelope)

    stale_status_canary = PayloadCacheLivePayloadRuntimeDisabledCanary(
        **{
            **_live_payload_runtime_canary_kwargs(),
            "status": (
                "blocked_by_live_payload_stage:"
                "blocked_by_queue_budget_runtime_envelope:stale_queue_budget_status"
            ),
            "live_payload_stage_status": (
                "blocked_by_queue_budget_runtime_envelope:stale_queue_budget_status"
            ),
        },
    )

    with pytest.raises(ValueError, match="live-stage status mismatch"):
        build_payload_cache_manager_implementation_artifact(
            stale_status_canary,
            envelope,
        )

    valid_canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    other_envelope = build_payload_cache_queue_budget_runtime_envelope(
        cell_count=16,
        event_timing_mode="token_index",
        first_model_passing_capacity=8192,
        first_model_passing_issue_lead_tokens=32,
        first_model_passing_queue_deadline_us=100.0,
        first_model_passing_lookahead_us=2_400_000.0,
        shifted_issue_accounting_enabled=True,
        shifted_issue_accounted_packet_count=28,
        shifted_issue_unique_issue_key_count=16,
    )

    with pytest.raises(ValueError, match="capacity mismatch"):
        build_payload_cache_manager_implementation_artifact(valid_canary, other_envelope)


def test_payload_cache_manager_implementation_artifact_binds_queue_budget() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )

    artifact = build_payload_cache_manager_implementation_artifact(canary, envelope)
    payload = artifact.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_manager_implementation_artifact"
    assert payload["status"] == f"blocked_by_live_payload_runtime:{canary.status}"
    assert payload["consumes_live_payload_runtime_canary"] is True
    assert payload["live_payload_runtime_status"] == canary.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_contract"] == "event_driven_queue_budget_cache_manager_v1"
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "implementation_artifact_default_disabled"
    assert payload["execution_mode"] == (
        "payload_cache_manager_implementation_artifact_disabled"
    )
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["payload_bytes"] == 0
    assert payload["ready_before_demand_credit"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["measures_tpot"] is False


def test_payload_cache_manager_implementation_artifact_rejects_side_effects() -> None:
    runtime_status = (
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    with pytest.raises(ValueError, match="manager backend"):
        PayloadCacheManagerImplementationArtifact(
            present=True,
            stage="payload_cache_manager_implementation_artifact",
            status=f"blocked_by_live_payload_runtime:{runtime_status}",
            consumes_live_payload_runtime_canary=True,
            live_payload_runtime_status=runtime_status,
            manager_backend="OtherManager",
            manager_contract="event_driven_queue_budget_cache_manager_v1",
            capacity_entries=4096,
            issue_lead_tokens=32,
            queue_deadline_us=100.0,
            lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
        )

    with pytest.raises(ValueError, match="payload_deref_allowed"):
        PayloadCacheManagerImplementationArtifact(
            present=True,
            stage="payload_cache_manager_implementation_artifact",
            status=f"blocked_by_live_payload_runtime:{runtime_status}",
            consumes_live_payload_runtime_canary=True,
            live_payload_runtime_status=runtime_status,
            manager_backend="ReadyTimeExpertCacheManager",
            manager_contract="event_driven_queue_budget_cache_manager_v1",
            capacity_entries=4096,
            issue_lead_tokens=32,
            queue_deadline_us=100.0,
            lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
            payload_deref_allowed=True,
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheManagerImplementationArtifact(
            present=True,
            stage="payload_cache_manager_implementation_artifact",
            status=f"blocked_by_live_payload_runtime:{runtime_status}",
            consumes_live_payload_runtime_canary=True,
            live_payload_runtime_status=runtime_status,
            manager_backend="ReadyTimeExpertCacheManager",
            manager_contract="event_driven_queue_budget_cache_manager_v1",
            capacity_entries=4096,
            issue_lead_tokens=32,
            queue_deadline_us=100.0,
            lookahead_us=2_400_000.0,
            shifted_issue_accounting_enabled=True,
            shifted_issue_accounted_packet_count=28,
            shifted_issue_unique_issue_key_count=16,
            payload_bytes=1,
        )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_manager_implementation_artifact(
            object(),  # type: ignore[arg-type]
            build_payload_cache_queue_budget_runtime_envelope(
                cell_count=16,
                event_timing_mode="token_index",
                first_model_passing_capacity=4096,
                first_model_passing_issue_lead_tokens=32,
                first_model_passing_queue_deadline_us=100.0,
                first_model_passing_lookahead_us=2_400_000.0,
                shifted_issue_accounting_enabled=True,
                shifted_issue_accounted_packet_count=28,
                shifted_issue_unique_issue_key_count=16,
            ),
        )


def test_payload_cache_manager_runtime_skeleton_consumes_artifact() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    artifact = build_payload_cache_manager_implementation_artifact(canary, envelope)

    skeleton = build_payload_cache_manager_runtime_skeleton(artifact)
    payload = skeleton.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_manager_runtime_skeleton"
    assert payload["status"] == f"blocked_by_manager_artifact:{artifact.status}"
    assert payload["consumes_manager_implementation_artifact"] is True
    assert payload["manager_artifact_status"] == artifact.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_contract"] == "event_driven_queue_budget_cache_manager_v1"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["runtime_instantiated"] is False
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "runtime_skeleton_default_disabled"
    assert payload["execution_mode"] == "payload_cache_manager_runtime_skeleton_disabled"
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_payload_cache_manager_runtime_skeleton_rejects_side_effects() -> None:
    artifact_status = (
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_manager_runtime_skeleton",
        "status": f"blocked_by_manager_artifact:{artifact_status}",
        "consumes_manager_implementation_artifact": True,
        "manager_artifact_status": artifact_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_contract": "event_driven_queue_budget_cache_manager_v1",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="runtime"):
        PayloadCacheManagerRuntimeSkeleton(
            **{
                **base_kwargs,
                "runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheManagerRuntimeSkeleton(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheManagerRuntimeSkeleton(
            **{
                **base_kwargs,
                "kernel_arg_pass_allowed": True,
            },
        )

    with pytest.raises(TypeError, match="artifact"):
        build_payload_cache_manager_runtime_skeleton(object())  # type: ignore[arg-type]


def test_payload_cache_manager_runtime_snapshot_artifact_consumes_skeleton() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    artifact = build_payload_cache_manager_implementation_artifact(canary, envelope)
    skeleton = build_payload_cache_manager_runtime_skeleton(artifact)

    snapshot = build_payload_cache_manager_runtime_snapshot_artifact(skeleton)
    payload = snapshot.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_manager_runtime_snapshot_artifact"
    assert payload["status"] == f"blocked_by_runtime_skeleton:{skeleton.status}"
    assert payload["consumes_runtime_skeleton"] is True
    assert payload["runtime_skeleton_status"] == skeleton.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["snapshot_source"] == "ReadyTimeExpertCacheManager.empty_snapshot"
    assert payload["accounting_snapshot_instantiated"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "runtime_snapshot_default_disabled"
    assert payload["execution_mode"] == "payload_cache_manager_runtime_snapshot_disabled"
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_payload_cache_manager_runtime_snapshot_artifact_rejects_side_effects() -> None:
    skeleton_status = (
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_manager_runtime_snapshot_artifact",
        "status": f"blocked_by_runtime_skeleton:{skeleton_status}",
        "consumes_runtime_skeleton": True,
        "runtime_skeleton_status": skeleton_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "snapshot_source": "ReadyTimeExpertCacheManager.empty_snapshot",
        "accounting_snapshot_instantiated": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheManagerRuntimeSnapshotArtifact(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="issued_fetch_count"):
        PayloadCacheManagerRuntimeSnapshotArtifact(
            **{
                **base_kwargs,
                "issued_fetch_count": 1,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheManagerRuntimeSnapshotArtifact(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheManagerRuntimeSnapshotArtifact(
            **{
                **base_kwargs,
                "kernel_arg_pass_allowed": True,
            },
        )

    with pytest.raises(TypeError, match="skeleton"):
        build_payload_cache_manager_runtime_snapshot_artifact(object())  # type: ignore[arg-type]


def test_snapshot_backed_live_runtime_preflight_consumes_snapshot() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    artifact = build_payload_cache_manager_implementation_artifact(canary, envelope)
    skeleton = build_payload_cache_manager_runtime_skeleton(artifact)
    snapshot = build_payload_cache_manager_runtime_snapshot_artifact(skeleton)

    live_preflight = build_payload_cache_snapshot_backed_live_runtime_preflight(
        snapshot,
    )
    payload = live_preflight.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_snapshot_backed_live_runtime_preflight"
    assert payload["status"] == f"blocked_by_runtime_snapshot:{snapshot.status}"
    assert payload["consumes_runtime_snapshot"] is True
    assert payload["runtime_snapshot_status"] == snapshot.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["snapshot_source"] == "PayloadCacheManagerRuntimeSnapshotArtifact"
    assert payload["live_runtime_preflight_instantiated"] is True
    assert payload["accounting_snapshot_instantiated"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "snapshot_backed_live_runtime_preflight_disabled"
    assert (
        payload["execution_mode"]
        == "payload_cache_snapshot_backed_live_runtime_preflight_disabled"
    )
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_snapshot_backed_live_runtime_preflight_rejects_side_effects() -> None:
    snapshot_status = (
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_snapshot_backed_live_runtime_preflight",
        "status": f"blocked_by_runtime_snapshot:{snapshot_status}",
        "consumes_runtime_snapshot": True,
        "runtime_snapshot_status": snapshot_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "snapshot_source": "PayloadCacheManagerRuntimeSnapshotArtifact",
        "live_runtime_preflight_instantiated": True,
        "accounting_snapshot_instantiated": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheSnapshotBackedLiveRuntimePreflight(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="used_fetch_count"):
        PayloadCacheSnapshotBackedLiveRuntimePreflight(
            **{
                **base_kwargs,
                "used_fetch_count": 1,
            },
        )

    with pytest.raises(ValueError, match="ready_credit"):
        PayloadCacheSnapshotBackedLiveRuntimePreflight(
            **{
                **base_kwargs,
                "ready_credit": True,
            },
        )

    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheSnapshotBackedLiveRuntimePreflight(
            **{
                **base_kwargs,
                "kernel_arg_pass_allowed": True,
            },
        )

    with pytest.raises(TypeError, match="snapshot"):
        build_payload_cache_snapshot_backed_live_runtime_preflight(object())  # type: ignore[arg-type]


def test_snapshot_backed_live_runtime_disabled_canary_consumes_preflight() -> None:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    artifact = build_payload_cache_manager_implementation_artifact(canary, envelope)
    skeleton = build_payload_cache_manager_runtime_skeleton(artifact)
    snapshot = build_payload_cache_manager_runtime_snapshot_artifact(skeleton)
    live_preflight = build_payload_cache_snapshot_backed_live_runtime_preflight(
        snapshot,
    )

    live_canary = build_payload_cache_snapshot_backed_live_runtime_disabled_canary(
        live_preflight,
    )
    payload = live_canary.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_snapshot_backed_live_runtime_disabled_canary"
    assert payload["status"] == f"blocked_by_live_runtime_preflight:{live_preflight.status}"
    assert payload["consumes_live_runtime_preflight"] is True
    assert payload["live_runtime_preflight_status"] == live_preflight.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["live_runtime_canary_instantiated"] is True
    assert payload["live_runtime_preflight_instantiated"] is True
    assert payload["accounting_snapshot_instantiated"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "snapshot_backed_live_runtime_canary_disabled"
    assert (
        payload["execution_mode"]
        == "payload_cache_snapshot_backed_live_runtime_canary_disabled"
    )
    assert payload["live_payload_runtime_enabled"] is False
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["full_fetch_runtime_allowed"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_snapshot_backed_live_runtime_disabled_canary_rejects_side_effects() -> None:
    preflight_status = (
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_snapshot_backed_live_runtime_disabled_canary",
        "status": f"blocked_by_live_runtime_preflight:{preflight_status}",
        "consumes_live_runtime_preflight": True,
        "live_runtime_preflight_status": preflight_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "live_runtime_canary_instantiated": True,
        "live_runtime_preflight_instantiated": True,
        "accounting_snapshot_instantiated": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="demand_count"):
        PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary(
            **{
                **base_kwargs,
                "demand_count": 1,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    with pytest.raises(ValueError, match="passed_to_kernel"):
        PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary(
            **{
                **base_kwargs,
                "passed_to_kernel": True,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="preflight"):
        build_payload_cache_snapshot_backed_live_runtime_disabled_canary(object())  # type: ignore[arg-type]


def _build_snapshot_backed_live_runtime_canary(
) -> PayloadCacheSnapshotBackedLiveRuntimeDisabledCanary:
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
    preflight = build_payload_cache_live_payload_stage_preflight(envelope)
    canary = build_payload_cache_live_payload_runtime_disabled_canary(
        preflight,
        envelope,
    )
    artifact = build_payload_cache_manager_implementation_artifact(canary, envelope)
    skeleton = build_payload_cache_manager_runtime_skeleton(artifact)
    snapshot = build_payload_cache_manager_runtime_snapshot_artifact(skeleton)
    live_preflight = build_payload_cache_snapshot_backed_live_runtime_preflight(
        snapshot,
    )
    return build_payload_cache_snapshot_backed_live_runtime_disabled_canary(
        live_preflight,
    )


def test_live_runtime_state_shape_check_consumes_disabled_canary() -> None:
    canary = _build_snapshot_backed_live_runtime_canary()

    state_shape = build_payload_cache_live_runtime_state_shape_check(canary)
    payload = state_shape.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_state_shape_check"
    assert payload["status"] == f"blocked_by_live_runtime_canary:{canary.status}"
    assert payload["consumes_live_runtime_canary"] is True
    assert payload["live_runtime_canary_status"] == canary.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["live_runtime_state_shape_checked"] is True
    assert payload["issue_queue_shape_checked"] is True
    assert payload["demand_state_shape_checked"] is True
    assert payload["resident_index_shape_checked"] is True
    assert payload["queue_timing_shape_checked"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_state_shape_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_state_shape_check_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_state_shape_check_rejects_side_effects() -> None:
    canary_status = (
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_state_shape_check",
        "status": f"blocked_by_live_runtime_canary:{canary_status}",
        "consumes_live_runtime_canary": True,
        "live_runtime_canary_status": canary_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "live_runtime_state_shape_checked": True,
        "issue_queue_shape_checked": True,
        "demand_state_shape_checked": True,
        "resident_index_shape_checked": True,
        "queue_timing_shape_checked": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeStateShapeCheck(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="issue_queue_shape_checked"):
        PayloadCacheLiveRuntimeStateShapeCheck(
            **{
                **base_kwargs,
                "issue_queue_shape_checked": False,
            },
        )

    with pytest.raises(ValueError, match="demand_count"):
        PayloadCacheLiveRuntimeStateShapeCheck(
            **{
                **base_kwargs,
                "demand_count": 1,
            },
        )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeStateShapeCheck(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_state_shape_check(object())  # type: ignore[arg-type]


def _build_live_runtime_state_shape_check() -> PayloadCacheLiveRuntimeStateShapeCheck:
    return build_payload_cache_live_runtime_state_shape_check(
        _build_snapshot_backed_live_runtime_canary(),
    )


def test_live_runtime_object_construction_preflight_consumes_state_shape() -> None:
    state_shape = _build_live_runtime_state_shape_check()

    preflight = build_payload_cache_live_runtime_object_construction_preflight(
        state_shape,
    )
    payload = preflight.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_object_construction_preflight"
    assert payload["status"] == f"blocked_by_state_shape_check:{state_shape.status}"
    assert payload["consumes_state_shape_check"] is True
    assert payload["state_shape_status"] == state_shape.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["object_construction_preflight_instantiated"] is True
    assert payload["typed_issue_queue_container_declared"] is True
    assert payload["typed_demand_state_container_declared"] is True
    assert payload["typed_resident_index_container_declared"] is True
    assert payload["typed_queue_timing_container_declared"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_object_construction_preflight_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_object_construction_preflight_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_object_construction_preflight_rejects_side_effects() -> None:
    state_shape_status = (
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_object_construction_preflight",
        "status": f"blocked_by_state_shape_check:{state_shape_status}",
        "consumes_state_shape_check": True,
        "state_shape_status": state_shape_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "object_construction_preflight_instantiated": True,
        "typed_issue_queue_container_declared": True,
        "typed_demand_state_container_declared": True,
        "typed_resident_index_container_declared": True,
        "typed_queue_timing_container_declared": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeObjectConstructionPreflight(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="typed_issue_queue_container_declared"):
        PayloadCacheLiveRuntimeObjectConstructionPreflight(
            **{
                **base_kwargs,
                "typed_issue_queue_container_declared": False,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeObjectConstructionPreflight(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeObjectConstructionPreflight(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="state_shape"):
        build_payload_cache_live_runtime_object_construction_preflight(object())  # type: ignore[arg-type]


def test_live_runtime_object_construction_preflight_builder_rejects_bad_state_shape() -> None:
    state_shape = _build_live_runtime_state_shape_check()

    object.__setattr__(state_shape, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_object_construction_preflight(state_shape)

    state_shape = _build_live_runtime_state_shape_check()
    object.__setattr__(state_shape, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_object_construction_preflight(state_shape)

    state_shape = _build_live_runtime_state_shape_check()
    object.__setattr__(state_shape, "ready_credit", True)
    with pytest.raises(ValueError, match="ready_credit"):
        build_payload_cache_live_runtime_object_construction_preflight(state_shape)


def _build_live_runtime_object_construction_preflight() -> (
    PayloadCacheLiveRuntimeObjectConstructionPreflight
):
    return build_payload_cache_live_runtime_object_construction_preflight(
        _build_live_runtime_state_shape_check(),
    )


def test_live_runtime_object_adapter_preflight_consumes_object_preflight() -> None:
    object_preflight = _build_live_runtime_object_construction_preflight()

    adapter = build_payload_cache_live_runtime_object_adapter_preflight(
        object_preflight,
    )
    payload = adapter.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_object_adapter_preflight"
    assert (
        payload["status"]
        == f"blocked_by_object_construction_preflight:{object_preflight.status}"
    )
    assert payload["consumes_object_construction_preflight"] is True
    assert payload["object_preflight_status"] == object_preflight.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["runtime_adapter_schema"] == "ready_time_payload_cache_runtime_adapter_v1"
    assert payload["object_construction_preflight_instantiated"] is True
    assert payload["runtime_object_adapter_declared"] is True
    assert payload["issue_queue_adapter_bound"] is True
    assert payload["demand_state_adapter_bound"] is True
    assert payload["resident_index_adapter_bound"] is True
    assert payload["queue_timing_adapter_bound"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_object_adapter_preflight_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_object_adapter_preflight_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_object_adapter_preflight_rejects_side_effects() -> None:
    object_status = (
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_object_adapter_preflight",
        "status": f"blocked_by_object_construction_preflight:{object_status}",
        "consumes_object_construction_preflight": True,
        "object_preflight_status": object_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "runtime_adapter_schema": "ready_time_payload_cache_runtime_adapter_v1",
        "object_construction_preflight_instantiated": True,
        "runtime_object_adapter_declared": True,
        "issue_queue_adapter_bound": True,
        "demand_state_adapter_bound": True,
        "resident_index_adapter_bound": True,
        "queue_timing_adapter_bound": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="runtime_object_adapter_declared"):
        PayloadCacheLiveRuntimeObjectAdapterPreflight(
            **{
                **base_kwargs,
                "runtime_object_adapter_declared": False,
            },
        )

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeObjectAdapterPreflight(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeObjectAdapterPreflight(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "passes_current_wna16_args",
        "measures_vllm_latency",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeObjectAdapterPreflight(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="object_preflight"):
        build_payload_cache_live_runtime_object_adapter_preflight(object())  # type: ignore[arg-type]


def test_live_runtime_object_adapter_preflight_builder_rejects_bad_object() -> None:
    object_preflight = _build_live_runtime_object_construction_preflight()

    object.__setattr__(object_preflight, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_object_adapter_preflight(object_preflight)

    object_preflight = _build_live_runtime_object_construction_preflight()
    object.__setattr__(object_preflight, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_object_adapter_preflight(object_preflight)

    object_preflight = _build_live_runtime_object_construction_preflight()
    object.__setattr__(object_preflight, "kernel_arg_pass_allowed", True)
    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        build_payload_cache_live_runtime_object_adapter_preflight(object_preflight)


def _build_live_runtime_object_adapter_preflight() -> (
    PayloadCacheLiveRuntimeObjectAdapterPreflight
):
    return build_payload_cache_live_runtime_object_adapter_preflight(
        _build_live_runtime_object_construction_preflight(),
    )


def test_live_runtime_adapter_materialization_preflight_consumes_adapter() -> None:
    object_adapter = _build_live_runtime_object_adapter_preflight()

    preflight = build_payload_cache_live_runtime_adapter_materialization_preflight(
        object_adapter,
    )
    payload = preflight.as_dict()

    assert payload["present"] is True
    assert (
        payload["stage"]
        == "payload_cache_live_runtime_adapter_materialization_preflight"
    )
    assert payload["status"] == f"blocked_by_object_adapter_preflight:{object_adapter.status}"
    assert payload["consumes_object_adapter_preflight"] is True
    assert payload["object_adapter_status"] == object_adapter.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["runtime_adapter_schema"] == "ready_time_payload_cache_runtime_adapter_v1"
    assert payload["object_construction_preflight_instantiated"] is True
    assert payload["adapter_materialization_preflight_instantiated"] is True
    assert payload["runtime_object_adapter_declared"] is True
    assert payload["issue_queue_materialization_checked"] is True
    assert payload["demand_state_materialization_checked"] is True
    assert payload["resident_index_materialization_checked"] is True
    assert payload["queue_timing_materialization_checked"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_adapter_materialization_preflight_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_materialization_preflight_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_materialization_preflight_rejects_side_effects() -> None:
    object_adapter_status = (
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_materialization_preflight",
        "status": f"blocked_by_object_adapter_preflight:{object_adapter_status}",
        "consumes_object_adapter_preflight": True,
        "object_adapter_status": object_adapter_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "runtime_adapter_schema": "ready_time_payload_cache_runtime_adapter_v1",
        "object_construction_preflight_instantiated": True,
        "adapter_materialization_preflight_instantiated": True,
        "runtime_object_adapter_declared": True,
        "issue_queue_materialization_checked": True,
        "demand_state_materialization_checked": True,
        "resident_index_materialization_checked": True,
        "queue_timing_materialization_checked": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="adapter_materialization"):
        PayloadCacheLiveRuntimeAdapterMaterializationPreflight(
            **{
                **base_kwargs,
                "adapter_materialization_preflight_instantiated": False,
            },
        )

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeAdapterMaterializationPreflight(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterMaterializationPreflight(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterMaterializationPreflight(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="object_adapter"):
        build_payload_cache_live_runtime_adapter_materialization_preflight(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_materialization_preflight_builder_rejects_bad_adapter() -> None:
    object_adapter = _build_live_runtime_object_adapter_preflight()

    object.__setattr__(object_adapter, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_materialization_preflight(
            object_adapter,
        )

    object_adapter = _build_live_runtime_object_adapter_preflight()
    object.__setattr__(object_adapter, "object_construction_preflight_instantiated", False)
    with pytest.raises(ValueError, match="object_construction_preflight_instantiated"):
        build_payload_cache_live_runtime_adapter_materialization_preflight(
            object_adapter,
        )

    object_adapter = _build_live_runtime_object_adapter_preflight()
    object.__setattr__(object_adapter, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_materialization_preflight(
            object_adapter,
        )

    object_adapter = _build_live_runtime_object_adapter_preflight()
    object.__setattr__(object_adapter, "passed_to_kernel", True)
    with pytest.raises(ValueError, match="passed_to_kernel"):
        build_payload_cache_live_runtime_adapter_materialization_preflight(
            object_adapter,
        )


def _build_live_runtime_adapter_materialization_preflight() -> (
    PayloadCacheLiveRuntimeAdapterMaterializationPreflight
):
    return build_payload_cache_live_runtime_adapter_materialization_preflight(
        _build_live_runtime_object_adapter_preflight(),
    )


def test_live_runtime_adapter_state_object_preflight_consumes_materialization() -> None:
    materialization = _build_live_runtime_adapter_materialization_preflight()

    preflight = build_payload_cache_live_runtime_adapter_state_object_preflight(
        materialization,
    )
    payload = preflight.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_adapter_state_object_preflight"
    assert (
        payload["status"]
        == f"blocked_by_adapter_materialization_preflight:{materialization.status}"
    )
    assert payload["consumes_adapter_materialization_preflight"] is True
    assert payload["adapter_materialization_status"] == materialization.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["runtime_adapter_schema"] == "ready_time_payload_cache_runtime_adapter_v1"
    assert payload["adapter_state_object_schema"] == "ready_time_payload_cache_adapter_state_v1"
    assert payload["adapter_materialization_preflight_instantiated"] is True
    assert payload["adapter_state_object_declared"] is True
    assert payload["issue_queue_state_object_declared"] is True
    assert payload["demand_state_object_declared"] is True
    assert payload["resident_index_state_object_declared"] is True
    assert payload["queue_timing_state_object_declared"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_adapter_state_object_preflight_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_state_object_preflight_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_state_object_preflight_rejects_side_effects() -> None:
    materialization_status = (
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_state_object_preflight",
        "status": f"blocked_by_adapter_materialization_preflight:{materialization_status}",
        "consumes_adapter_materialization_preflight": True,
        "adapter_materialization_status": materialization_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "runtime_adapter_schema": "ready_time_payload_cache_runtime_adapter_v1",
        "adapter_state_object_schema": "ready_time_payload_cache_adapter_state_v1",
        "adapter_materialization_preflight_instantiated": True,
        "adapter_state_object_declared": True,
        "issue_queue_state_object_declared": True,
        "demand_state_object_declared": True,
        "resident_index_state_object_declared": True,
        "queue_timing_state_object_declared": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="adapter_state_object_declared"):
        PayloadCacheLiveRuntimeAdapterStateObjectPreflight(
            **{
                **base_kwargs,
                "adapter_state_object_declared": False,
            },
        )

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeAdapterStateObjectPreflight(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterStateObjectPreflight(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "passes_current_wna16_args",
        "measures_vllm_latency",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterStateObjectPreflight(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="materialization"):
        build_payload_cache_live_runtime_adapter_state_object_preflight(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_state_object_preflight_builder_rejects_bad_materialization() -> None:
    materialization = _build_live_runtime_adapter_materialization_preflight()

    object.__setattr__(materialization, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_state_object_preflight(
            materialization,
        )

    materialization = _build_live_runtime_adapter_materialization_preflight()
    object.__setattr__(materialization, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_state_object_preflight(
            materialization,
        )

    materialization = _build_live_runtime_adapter_materialization_preflight()
    object.__setattr__(materialization, "block_reason", "runtime_enabled")
    with pytest.raises(ValueError, match="block reason"):
        build_payload_cache_live_runtime_adapter_state_object_preflight(
            materialization,
        )

    materialization = _build_live_runtime_adapter_materialization_preflight()
    object.__setattr__(materialization, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_state_object_preflight(
            materialization,
        )

    materialization = _build_live_runtime_adapter_materialization_preflight()
    object.__setattr__(materialization, "adapter_materialization_preflight_instantiated", False)
    with pytest.raises(ValueError, match="adapter_materialization_preflight_instantiated"):
        build_payload_cache_live_runtime_adapter_state_object_preflight(
            materialization,
        )


def _build_live_runtime_adapter_state_object_preflight() -> (
    PayloadCacheLiveRuntimeAdapterStateObjectPreflight
):
    return build_payload_cache_live_runtime_adapter_state_object_preflight(
        _build_live_runtime_adapter_materialization_preflight(),
    )


def test_live_runtime_adapter_state_validation_preflight_consumes_state_object() -> None:
    state_object = _build_live_runtime_adapter_state_object_preflight()

    preflight = build_payload_cache_live_runtime_adapter_state_validation_preflight(
        state_object,
    )
    payload = preflight.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_adapter_state_validation_preflight"
    assert payload["status"] == f"blocked_by_adapter_state_object_preflight:{state_object.status}"
    assert payload["consumes_adapter_state_object_preflight"] is True
    assert payload["adapter_state_object_status"] == state_object.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["runtime_adapter_schema"] == "ready_time_payload_cache_runtime_adapter_v1"
    assert payload["adapter_state_object_schema"] == "ready_time_payload_cache_adapter_state_v1"
    assert (
        payload["adapter_state_validation_schema"]
        == "ready_time_payload_cache_adapter_state_validation_v1"
    )
    assert payload["adapter_state_object_declared"] is True
    assert payload["adapter_state_validation_preflight_instantiated"] is True
    assert payload["issue_queue_state_object_validated"] is True
    assert payload["demand_state_object_validated"] is True
    assert payload["resident_index_state_object_validated"] is True
    assert payload["queue_timing_state_object_validated"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_adapter_state_validation_preflight_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_state_validation_preflight_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_state_validation_preflight_rejects_side_effects() -> None:
    state_object_status = (
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_state_validation_preflight",
        "status": f"blocked_by_adapter_state_object_preflight:{state_object_status}",
        "consumes_adapter_state_object_preflight": True,
        "adapter_state_object_status": state_object_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "runtime_adapter_schema": "ready_time_payload_cache_runtime_adapter_v1",
        "adapter_state_object_schema": "ready_time_payload_cache_adapter_state_v1",
        "adapter_state_validation_schema": (
            "ready_time_payload_cache_adapter_state_validation_v1"
        ),
        "adapter_state_object_declared": True,
        "adapter_state_validation_preflight_instantiated": True,
        "issue_queue_state_object_validated": True,
        "demand_state_object_validated": True,
        "resident_index_state_object_validated": True,
        "queue_timing_state_object_validated": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="adapter_state_object_declared"):
        PayloadCacheLiveRuntimeAdapterStateValidationPreflight(
            **{
                **base_kwargs,
                "adapter_state_object_declared": False,
            },
        )

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeAdapterStateValidationPreflight(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterStateValidationPreflight(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterStateValidationPreflight(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="state_object"):
        build_payload_cache_live_runtime_adapter_state_validation_preflight(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_state_validation_preflight_builder_rejects_bad_state_object() -> None:
    state_object = _build_live_runtime_adapter_state_object_preflight()

    object.__setattr__(state_object, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_state_validation_preflight(
            state_object,
        )

    state_object = _build_live_runtime_adapter_state_object_preflight()
    object.__setattr__(state_object, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_state_validation_preflight(
            state_object,
        )

    state_object = _build_live_runtime_adapter_state_object_preflight()
    object.__setattr__(state_object, "adapter_materialization_status", "stale")
    object.__setattr__(
        state_object,
        "status",
        "blocked_by_adapter_materialization_preflight:stale",
    )
    with pytest.raises(ValueError, match="materialization status chain"):
        build_payload_cache_live_runtime_adapter_state_validation_preflight(
            state_object,
        )

    state_object = _build_live_runtime_adapter_state_object_preflight()
    object.__setattr__(state_object, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_state_validation_preflight(
            state_object,
        )

    state_object = _build_live_runtime_adapter_state_object_preflight()
    object.__setattr__(state_object, "adapter_state_object_declared", False)
    with pytest.raises(ValueError, match="adapter_state_object_declared"):
        build_payload_cache_live_runtime_adapter_state_validation_preflight(
            state_object,
        )


def _build_live_runtime_adapter_state_validation_preflight() -> (
    PayloadCacheLiveRuntimeAdapterStateValidationPreflight
):
    return build_payload_cache_live_runtime_adapter_state_validation_preflight(
        _build_live_runtime_adapter_state_object_preflight(),
    )


def test_live_runtime_adapter_state_validation_artifact_consumes_preflight() -> None:
    state_validation = _build_live_runtime_adapter_state_validation_preflight()

    artifact = build_payload_cache_live_runtime_adapter_state_validation_artifact(
        state_validation,
    )
    payload = artifact.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_adapter_state_validation_artifact"
    assert (
        payload["status"]
        == f"blocked_by_adapter_state_validation_preflight:{state_validation.status}"
    )
    assert payload["consumes_adapter_state_validation_preflight"] is True
    assert payload["adapter_state_validation_status"] == state_validation.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["state_shape_schema"] == "ready_time_issue_demand_state_shape_v1"
    assert payload["runtime_adapter_schema"] == "ready_time_payload_cache_runtime_adapter_v1"
    assert payload["adapter_state_object_schema"] == "ready_time_payload_cache_adapter_state_v1"
    assert (
        payload["adapter_state_validation_schema"]
        == "ready_time_payload_cache_adapter_state_validation_v1"
    )
    assert (
        payload["validated_state_artifact_schema"]
        == "ready_time_payload_cache_validated_adapter_state_artifact_v1"
    )
    assert payload["adapter_state_validation_preflight_instantiated"] is True
    assert payload["adapter_state_validation_artifact_instantiated"] is True
    assert payload["issue_queue_state_object_ready_for_runtime_adapter"] is True
    assert payload["demand_state_object_ready_for_runtime_adapter"] is True
    assert payload["resident_index_state_object_ready_for_runtime_adapter"] is True
    assert payload["queue_timing_state_object_ready_for_runtime_adapter"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_adapter_state_validation_artifact_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_state_validation_artifact_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_state_validation_artifact_rejects_side_effects() -> None:
    state_validation_status = (
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_state_validation_artifact",
        "status": (
            f"blocked_by_adapter_state_validation_preflight:"
            f"{state_validation_status}"
        ),
        "consumes_adapter_state_validation_preflight": True,
        "adapter_state_validation_status": state_validation_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "state_shape_schema": "ready_time_issue_demand_state_shape_v1",
        "runtime_adapter_schema": "ready_time_payload_cache_runtime_adapter_v1",
        "adapter_state_object_schema": "ready_time_payload_cache_adapter_state_v1",
        "adapter_state_validation_schema": (
            "ready_time_payload_cache_adapter_state_validation_v1"
        ),
        "validated_state_artifact_schema": (
            "ready_time_payload_cache_validated_adapter_state_artifact_v1"
        ),
        "adapter_state_validation_preflight_instantiated": True,
        "adapter_state_validation_artifact_instantiated": True,
        "issue_queue_state_object_ready_for_runtime_adapter": True,
        "demand_state_object_ready_for_runtime_adapter": True,
        "resident_index_state_object_ready_for_runtime_adapter": True,
        "queue_timing_state_object_ready_for_runtime_adapter": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="validated_state_artifact_schema"):
        PayloadCacheLiveRuntimeAdapterStateValidationArtifact(
            **{
                **base_kwargs,
                "validated_state_artifact_schema": "stale",
            },
        )

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeAdapterStateValidationArtifact(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterStateValidationArtifact(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterStateValidationArtifact(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="state_validation"):
        build_payload_cache_live_runtime_adapter_state_validation_artifact(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_state_validation_artifact_builder_rejects_bad_preflight() -> None:
    state_validation = _build_live_runtime_adapter_state_validation_preflight()

    object.__setattr__(state_validation, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_state_validation_artifact(
            state_validation,
        )

    state_validation = _build_live_runtime_adapter_state_validation_preflight()
    object.__setattr__(state_validation, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_state_validation_artifact(
            state_validation,
        )

    state_validation = _build_live_runtime_adapter_state_validation_preflight()
    object.__setattr__(state_validation, "adapter_state_object_status", "stale")
    object.__setattr__(
        state_validation,
        "status",
        "blocked_by_adapter_state_object_preflight:stale",
    )
    with pytest.raises(ValueError, match="state-object chain"):
        build_payload_cache_live_runtime_adapter_state_validation_artifact(
            state_validation,
        )

    state_validation = _build_live_runtime_adapter_state_validation_preflight()
    object.__setattr__(state_validation, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_state_validation_artifact(
            state_validation,
        )

    state_validation = _build_live_runtime_adapter_state_validation_preflight()
    object.__setattr__(
        state_validation,
        "queue_timing_state_object_validated",
        False,
    )
    with pytest.raises(ValueError, match="queue_timing_state_object_validated"):
        build_payload_cache_live_runtime_adapter_state_validation_artifact(
            state_validation,
        )


def _build_live_runtime_adapter_state_validation_artifact() -> (
    PayloadCacheLiveRuntimeAdapterStateValidationArtifact
):
    return build_payload_cache_live_runtime_adapter_state_validation_artifact(
        _build_live_runtime_adapter_state_validation_preflight(),
    )


def test_live_runtime_adapter_instantiation_canary_consumes_artifact() -> None:
    artifact = _build_live_runtime_adapter_state_validation_artifact()

    canary = build_payload_cache_live_runtime_adapter_instantiation_canary(artifact)
    payload = canary.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_adapter_instantiation_canary"
    assert payload["status"] == f"blocked_by_state_validation_artifact:{artifact.status}"
    assert payload["consumes_state_validation_artifact"] is True
    assert payload["state_validation_artifact_status"] == artifact.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["validated_state_artifact_schema"]
        == "ready_time_payload_cache_validated_adapter_state_artifact_v1"
    )
    assert (
        payload["runtime_adapter_instantiation_schema"]
        == "ready_time_payload_cache_runtime_adapter_instantiation_v1"
    )
    assert payload["adapter_factory_declared"] is True
    assert payload["adapter_constructor_resolved"] is True
    assert payload["adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_adapter_instantiation_canary_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_instantiation_canary_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_instantiation_canary_rejects_side_effects() -> None:
    artifact_status = (
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_instantiation_canary",
        "status": f"blocked_by_state_validation_artifact:{artifact_status}",
        "consumes_state_validation_artifact": True,
        "state_validation_artifact_status": artifact_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "validated_state_artifact_schema": (
            "ready_time_payload_cache_validated_adapter_state_artifact_v1"
        ),
        "runtime_adapter_instantiation_schema": (
            "ready_time_payload_cache_runtime_adapter_instantiation_v1"
        ),
        "adapter_factory_declared": True,
        "adapter_constructor_resolved": True,
        "adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="adapter instance"):
        PayloadCacheLiveRuntimeAdapterInstantiationCanary(
            **{
                **base_kwargs,
                "adapter_instance_created": True,
            },
        )

    with pytest.raises(ValueError, match="live runtime"):
        PayloadCacheLiveRuntimeAdapterInstantiationCanary(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterInstantiationCanary(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterInstantiationCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="artifact"):
        build_payload_cache_live_runtime_adapter_instantiation_canary(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_instantiation_canary_builder_rejects_bad_artifact() -> None:
    artifact = _build_live_runtime_adapter_state_validation_artifact()

    object.__setattr__(artifact, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_instantiation_canary(artifact)

    artifact = _build_live_runtime_adapter_state_validation_artifact()
    object.__setattr__(artifact, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_instantiation_canary(artifact)

    artifact = _build_live_runtime_adapter_state_validation_artifact()
    object.__setattr__(artifact, "adapter_state_validation_status", "stale")
    object.__setattr__(
        artifact,
        "status",
        "blocked_by_adapter_state_validation_preflight:stale",
    )
    with pytest.raises(ValueError, match="status chain"):
        build_payload_cache_live_runtime_adapter_instantiation_canary(artifact)

    artifact = _build_live_runtime_adapter_state_validation_artifact()
    object.__setattr__(artifact, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_instantiation_canary(artifact)

    artifact = _build_live_runtime_adapter_state_validation_artifact()
    object.__setattr__(
        artifact,
        "queue_timing_state_object_ready_for_runtime_adapter",
        False,
    )
    with pytest.raises(ValueError, match="queue_timing_state_object_ready"):
        build_payload_cache_live_runtime_adapter_instantiation_canary(artifact)


def _build_live_runtime_adapter_instantiation_canary() -> (
    PayloadCacheLiveRuntimeAdapterInstantiationCanary
):
    return build_payload_cache_live_runtime_adapter_instantiation_canary(
        _build_live_runtime_adapter_state_validation_artifact(),
    )


def test_live_runtime_adapter_constructor_binding_preflight_consumes_canary() -> None:
    canary = _build_live_runtime_adapter_instantiation_canary()

    preflight = build_payload_cache_live_runtime_adapter_constructor_binding_preflight(
        canary,
    )
    payload = preflight.as_dict()

    assert payload["present"] is True
    assert (
        payload["stage"]
        == "payload_cache_live_runtime_adapter_constructor_binding_preflight"
    )
    assert payload["status"] == f"blocked_by_instantiation_canary:{canary.status}"
    assert payload["consumes_instantiation_canary"] is True
    assert payload["instantiation_canary_status"] == canary.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["runtime_adapter_instantiation_schema"]
        == "ready_time_payload_cache_runtime_adapter_instantiation_v1"
    )
    assert (
        payload["constructor_binding_schema"]
        == "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
    )
    assert payload["adapter_factory_declared"] is True
    assert payload["adapter_constructor_resolved"] is True
    assert payload["constructor_inputs_bound"] is True
    assert payload["binds_validated_state_artifact"] is True
    assert payload["binds_queue_budget_parameters"] is True
    assert payload["binds_shifted_issue_accounting"] is True
    assert payload["adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert (
        payload["block_reason"]
        == "live_runtime_adapter_constructor_binding_preflight_only"
    )
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_constructor_binding_preflight_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_constructor_binding_preflight_rejects_side_effects() -> None:
    canary_status = (
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_constructor_binding_preflight",
        "status": f"blocked_by_instantiation_canary:{canary_status}",
        "consumes_instantiation_canary": True,
        "instantiation_canary_status": canary_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "runtime_adapter_instantiation_schema": (
            "ready_time_payload_cache_runtime_adapter_instantiation_v1"
        ),
        "constructor_binding_schema": (
            "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
        ),
        "adapter_factory_declared": True,
        "adapter_constructor_resolved": True,
        "constructor_inputs_bound": True,
        "binds_validated_state_artifact": True,
        "binds_queue_budget_parameters": True,
        "binds_shifted_issue_accounting": True,
        "adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="constructor_inputs_bound"):
        PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight(
            **{
                **base_kwargs,
                "constructor_inputs_bound": False,
            },
        )

    with pytest.raises(ValueError, match="adapter instance"):
        PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight(
            **{
                **base_kwargs,
                "adapter_instance_created": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_constructor_binding_preflight(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_constructor_binding_preflight_builder_rejects_bad_canary() -> None:
    canary = _build_live_runtime_adapter_instantiation_canary()

    object.__setattr__(canary, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_constructor_binding_preflight(canary)

    canary = _build_live_runtime_adapter_instantiation_canary()
    object.__setattr__(canary, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_constructor_binding_preflight(canary)

    canary = _build_live_runtime_adapter_instantiation_canary()
    object.__setattr__(canary, "state_validation_artifact_status", "stale")
    object.__setattr__(canary, "status", "blocked_by_state_validation_artifact:stale")
    with pytest.raises(ValueError, match="artifact status chain"):
        build_payload_cache_live_runtime_adapter_constructor_binding_preflight(canary)

    canary = _build_live_runtime_adapter_instantiation_canary()
    object.__setattr__(canary, "adapter_instance_created", True)
    with pytest.raises(ValueError, match="must not create instance"):
        build_payload_cache_live_runtime_adapter_constructor_binding_preflight(canary)

    canary = _build_live_runtime_adapter_instantiation_canary()
    object.__setattr__(canary, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_constructor_binding_preflight(canary)


def _build_live_runtime_adapter_constructor_binding_preflight() -> (
    PayloadCacheLiveRuntimeAdapterConstructorBindingPreflight
):
    return build_payload_cache_live_runtime_adapter_constructor_binding_preflight(
        _build_live_runtime_adapter_instantiation_canary(),
    )


def test_live_runtime_adapter_instance_construction_plan_consumes_binding() -> None:
    binding = _build_live_runtime_adapter_constructor_binding_preflight()

    plan = build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)
    payload = plan.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_adapter_instance_construction_plan"
    assert (
        payload["status"]
        == f"blocked_by_constructor_binding_preflight:{binding.status}"
    )
    assert payload["consumes_constructor_binding_preflight"] is True
    assert payload["constructor_binding_status"] == binding.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["constructor_binding_schema"]
        == "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
    )
    assert (
        payload["instance_construction_plan_schema"]
        == "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
    )
    assert payload["constructor_inputs_bound"] is True
    assert payload["construction_plan_sealed"] is True
    assert payload["adapter_constructor_call_prepared"] is True
    assert payload["adapter_instance_construction_planned"] is True
    assert payload["adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert (
        payload["block_reason"]
        == "live_runtime_adapter_instance_construction_plan_only"
    )
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_instance_construction_plan_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_instance_construction_plan_rejects_side_effects() -> None:
    binding_status = (
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_instance_construction_plan",
        "status": f"blocked_by_constructor_binding_preflight:{binding_status}",
        "consumes_constructor_binding_preflight": True,
        "constructor_binding_status": binding_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "constructor_binding_schema": (
            "ready_time_payload_cache_runtime_adapter_constructor_binding_v1"
        ),
        "instance_construction_plan_schema": (
            "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
        ),
        "constructor_inputs_bound": True,
        "construction_plan_sealed": True,
        "adapter_constructor_call_prepared": True,
        "adapter_instance_construction_planned": True,
        "adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="construction_plan_sealed"):
        PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan(
            **{
                **base_kwargs,
                "construction_plan_sealed": False,
            },
        )

    with pytest.raises(ValueError, match="adapter instance"):
        PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan(
            **{
                **base_kwargs,
                "adapter_instance_created": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="binding"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_instance_construction_plan_builder_rejects_bad_binding() -> None:
    binding = _build_live_runtime_adapter_constructor_binding_preflight()

    object.__setattr__(binding, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)

    binding = _build_live_runtime_adapter_constructor_binding_preflight()
    object.__setattr__(binding, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)

    binding = _build_live_runtime_adapter_constructor_binding_preflight()
    object.__setattr__(binding, "instantiation_canary_status", "stale")
    object.__setattr__(binding, "status", "blocked_by_instantiation_canary:stale")
    with pytest.raises(ValueError, match="canary status chain"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)

    binding = _build_live_runtime_adapter_constructor_binding_preflight()
    object.__setattr__(binding, "adapter_instance_created", True)
    with pytest.raises(ValueError, match="must not create instance"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)

    binding = _build_live_runtime_adapter_constructor_binding_preflight()
    object.__setattr__(binding, "adapter_constructor_resolved", False)
    with pytest.raises(ValueError, match="adapter_constructor_resolved"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)

    binding = _build_live_runtime_adapter_constructor_binding_preflight()
    object.__setattr__(binding, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_instance_construction_plan(binding)


def _build_live_runtime_adapter_instance_construction_plan() -> (
    PayloadCacheLiveRuntimeAdapterInstanceConstructionPlan
):
    return build_payload_cache_live_runtime_adapter_instance_construction_plan(
        _build_live_runtime_adapter_constructor_binding_preflight(),
    )


def test_live_runtime_adapter_object_shell_evidence_consumes_plan() -> None:
    plan = _build_live_runtime_adapter_instance_construction_plan()

    evidence = build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)
    payload = evidence.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == "payload_cache_live_runtime_adapter_object_shell_evidence"
    assert payload["status"] == f"blocked_by_instance_construction_plan:{plan.status}"
    assert payload["consumes_instance_construction_plan"] is True
    assert payload["instance_construction_plan_status"] == plan.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["instance_construction_plan_schema"]
        == "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
    )
    assert payload["adapter_object_shell_created"] is True
    assert payload["disabled_adapter_shell_snapshot_created"] is True
    assert payload["shell_enabled"] is False
    assert payload["adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == "live_runtime_adapter_object_shell_evidence_only"
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_object_shell_evidence_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_object_shell_evidence_rejects_side_effects() -> None:
    plan_status = (
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_object_shell_evidence",
        "status": f"blocked_by_instance_construction_plan:{plan_status}",
        "consumes_instance_construction_plan": True,
        "instance_construction_plan_status": plan_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "instance_construction_plan_schema": (
            "ready_time_payload_cache_runtime_adapter_instance_construction_plan_v1"
        ),
        "adapter_object_shell_created": True,
        "disabled_adapter_shell_snapshot_created": True,
        "shell_enabled": False,
        "adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="disabled"):
        PayloadCacheLiveRuntimeAdapterObjectShellEvidence(
            **{
                **base_kwargs,
                "shell_enabled": True,
            },
        )

    with pytest.raises(ValueError, match="adapter instance"):
        PayloadCacheLiveRuntimeAdapterObjectShellEvidence(
            **{
                **base_kwargs,
                "adapter_instance_created": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterObjectShellEvidence(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterObjectShellEvidence(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="plan"):
        build_payload_cache_live_runtime_adapter_object_shell_evidence(object())  # type: ignore[arg-type]


def test_live_runtime_adapter_object_shell_evidence_builder_rejects_bad_plan() -> None:
    plan = _build_live_runtime_adapter_instance_construction_plan()

    object.__setattr__(plan, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)

    plan = _build_live_runtime_adapter_instance_construction_plan()
    object.__setattr__(plan, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)

    plan = _build_live_runtime_adapter_instance_construction_plan()
    object.__setattr__(plan, "constructor_binding_status", "stale")
    object.__setattr__(
        plan,
        "status",
        "blocked_by_constructor_binding_preflight:stale",
    )
    with pytest.raises(ValueError, match="binding status chain"):
        build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)

    plan = _build_live_runtime_adapter_instance_construction_plan()
    object.__setattr__(plan, "adapter_instance_created", True)
    with pytest.raises(ValueError, match="must not create instance"):
        build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)

    plan = _build_live_runtime_adapter_instance_construction_plan()
    object.__setattr__(plan, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_object_shell_evidence(plan)


def _build_live_runtime_adapter_object_shell_evidence() -> (
    PayloadCacheLiveRuntimeAdapterObjectShellEvidence
):
    return build_payload_cache_live_runtime_adapter_object_shell_evidence(
        _build_live_runtime_adapter_instance_construction_plan(),
    )


def test_live_runtime_adapter_operation_rejection_canary_consumes_object_shell() -> None:
    evidence = _build_live_runtime_adapter_object_shell_evidence()

    canary = build_payload_cache_live_runtime_adapter_operation_rejection_canary(
        evidence,
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert (
        payload["stage"]
        == "payload_cache_live_runtime_adapter_operation_rejection_canary"
    )
    assert payload["status"] == f"blocked_by_object_shell_evidence:{evidence.status}"
    assert payload["consumes_object_shell_evidence"] is True
    assert payload["object_shell_evidence_status"] == evidence.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["operation_rejection_schema"]
        == "ready_time_payload_cache_runtime_adapter_operation_rejection_canary_v1"
    )
    assert payload["adapter_object_shell_created"] is True
    assert payload["operation_rejection_canary_ran"] is True
    assert payload["issue_prefetch_rejected"] is True
    assert payload["demand_rejected"] is True
    assert payload["shell_enabled"] is False
    assert payload["adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "unused_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "evicted_before_use_count",
        "ready_late_miss_count",
        "late_completion_unused_count",
        "queue_batch_count",
    ):
        assert payload[key] == 0
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert (
        payload["block_reason"]
        == "live_runtime_adapter_operation_rejection_canary_only"
    )
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_operation_rejection_canary_disabled"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_operation_rejection_canary_rejects_side_effects() -> None:
    object_shell_status = (
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_operation_rejection_canary",
        "status": f"blocked_by_object_shell_evidence:{object_shell_status}",
        "consumes_object_shell_evidence": True,
        "object_shell_evidence_status": object_shell_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "operation_rejection_schema": (
            "ready_time_payload_cache_runtime_adapter_operation_rejection_canary_v1"
        ),
        "adapter_object_shell_created": True,
        "operation_rejection_canary_ran": True,
        "issue_prefetch_rejected": True,
        "demand_rejected": True,
        "shell_enabled": False,
        "adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 0,
        "issued_fetch_count": 0,
        "used_fetch_count": 0,
        "unused_fetch_count": 0,
        "demand_count": 0,
        "demand_hit_count": 0,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 0,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="issue_prefetch_rejected"):
        PayloadCacheLiveRuntimeAdapterOperationRejectionCanary(
            **{
                **base_kwargs,
                "issue_prefetch_rejected": False,
            },
        )

    with pytest.raises(ValueError, match="demand_rejected"):
        PayloadCacheLiveRuntimeAdapterOperationRejectionCanary(
            **{
                **base_kwargs,
                "demand_rejected": False,
            },
        )

    with pytest.raises(ValueError, match="disabled"):
        PayloadCacheLiveRuntimeAdapterOperationRejectionCanary(
            **{
                **base_kwargs,
                "shell_enabled": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterOperationRejectionCanary(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterOperationRejectionCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="evidence"):
        build_payload_cache_live_runtime_adapter_operation_rejection_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_operation_rejection_canary_builder_rejects_bad_evidence() -> None:
    evidence = _build_live_runtime_adapter_object_shell_evidence()

    object.__setattr__(evidence, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_operation_rejection_canary(evidence)

    evidence = _build_live_runtime_adapter_object_shell_evidence()
    object.__setattr__(evidence, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_operation_rejection_canary(evidence)

    evidence = _build_live_runtime_adapter_object_shell_evidence()
    object.__setattr__(evidence, "instance_construction_plan_status", "stale")
    object.__setattr__(
        evidence,
        "status",
        "blocked_by_instance_construction_plan:stale",
    )
    with pytest.raises(ValueError, match="plan status chain"):
        build_payload_cache_live_runtime_adapter_operation_rejection_canary(evidence)

    evidence = _build_live_runtime_adapter_object_shell_evidence()
    object.__setattr__(evidence, "adapter_instance_created", True)
    with pytest.raises(ValueError, match="must not create adapter instance"):
        build_payload_cache_live_runtime_adapter_operation_rejection_canary(evidence)

    evidence = _build_live_runtime_adapter_object_shell_evidence()
    object.__setattr__(evidence, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_operation_rejection_canary(evidence)


def _build_live_runtime_adapter_operation_rejection_canary() -> (
    PayloadCacheLiveRuntimeAdapterOperationRejectionCanary
):
    return build_payload_cache_live_runtime_adapter_operation_rejection_canary(
        _build_live_runtime_adapter_object_shell_evidence(),
    )


def test_live_runtime_adapter_accounting_dry_run_canary_consumes_rejection_canary() -> None:
    rejection = _build_live_runtime_adapter_operation_rejection_canary()

    canary = build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(
        rejection,
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert (
        payload["stage"]
        == "payload_cache_live_runtime_adapter_accounting_dry_run_canary"
    )
    assert payload["status"] == (
        f"blocked_by_operation_rejection_canary:{rejection.status}"
    )
    assert payload["consumes_operation_rejection_canary"] is True
    assert payload["operation_rejection_canary_status"] == rejection.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["accounting_dry_run_schema"]
        == "ready_time_payload_cache_runtime_adapter_accounting_dry_run_canary_v1"
    )
    assert payload["accounting_dry_run_adapter_created"] is True
    assert payload["accounting_dry_run_operations_ran"] is True
    assert payload["accounting_dry_run_enabled"] is True
    assert payload["issue_prefetch_accepted"] is True
    assert payload["duplicate_issue_suppressed"] is True
    assert payload["demand_hit"] is True
    assert payload["live_adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    assert payload["resident_count"] == 1
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["unused_fetch_count"] == 0
    assert payload["demand_count"] == 1
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 0
    assert payload["evicted_before_use_count"] == 0
    assert payload["ready_late_miss_count"] == 0
    assert payload["late_completion_unused_count"] == 0
    assert payload["queue_batch_count"] == 1
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert (
        payload["block_reason"]
        == "live_runtime_adapter_accounting_dry_run_canary_only"
    )
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_accounting_dry_run_canary_payloadless"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_accounting_dry_run_canary_rejects_side_effects() -> None:
    rejection_status = (
        "blocked_by_object_shell_evidence:"
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_accounting_dry_run_canary",
        "status": f"blocked_by_operation_rejection_canary:{rejection_status}",
        "consumes_operation_rejection_canary": True,
        "operation_rejection_canary_status": rejection_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "accounting_dry_run_schema": (
            "ready_time_payload_cache_runtime_adapter_accounting_dry_run_canary_v1"
        ),
        "accounting_dry_run_adapter_created": True,
        "accounting_dry_run_operations_ran": True,
        "accounting_dry_run_enabled": True,
        "issue_prefetch_accepted": True,
        "duplicate_issue_suppressed": True,
        "demand_hit": True,
        "live_adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 1,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 1,
        "demand_hit_count": 1,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="accounting_dry_run_enabled"):
        PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary(
            **{
                **base_kwargs,
                "accounting_dry_run_enabled": False,
            },
        )

    with pytest.raises(ValueError, match="resident_count"):
        PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary(
            **{
                **base_kwargs,
                "resident_count": 0,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    with pytest.raises(ValueError, match="live adapter instance"):
        PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary(
            **{
                **base_kwargs,
                "live_adapter_instance_created": True,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_accounting_dry_run_canary_builder_rejects_bad_rejection_canary() -> None:
    rejection = _build_live_runtime_adapter_operation_rejection_canary()

    object.__setattr__(rejection, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(rejection)

    rejection = _build_live_runtime_adapter_operation_rejection_canary()
    object.__setattr__(rejection, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(rejection)

    rejection = _build_live_runtime_adapter_operation_rejection_canary()
    object.__setattr__(rejection, "object_shell_evidence_status", "stale")
    object.__setattr__(
        rejection,
        "status",
        "blocked_by_object_shell_evidence:stale",
    )
    with pytest.raises(ValueError, match="object-shell status chain"):
        build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(rejection)

    rejection = _build_live_runtime_adapter_operation_rejection_canary()
    object.__setattr__(rejection, "issue_prefetch_rejected", False)
    with pytest.raises(ValueError, match="issue_prefetch_rejected"):
        build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(rejection)

    rejection = _build_live_runtime_adapter_operation_rejection_canary()
    object.__setattr__(rejection, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(rejection)


def _build_live_runtime_adapter_accounting_dry_run_canary() -> (
    PayloadCacheLiveRuntimeAdapterAccountingDryRunCanary
):
    return build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(
        _build_live_runtime_adapter_operation_rejection_canary(),
    )


def test_live_runtime_adapter_mixed_outcome_dry_run_canary_consumes_accounting_canary() -> None:
    accounting = _build_live_runtime_adapter_accounting_dry_run_canary()

    canary = build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(
        accounting,
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert (
        payload["stage"]
        == "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary"
    )
    assert payload["status"] == (
        f"blocked_by_accounting_dry_run_canary:{accounting.status}"
    )
    assert payload["consumes_accounting_dry_run_canary"] is True
    assert payload["accounting_dry_run_canary_status"] == accounting.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert (
        payload["mixed_outcome_schema"]
        == "ready_time_payload_cache_runtime_adapter_mixed_outcome_dry_run_canary_v1"
    )
    assert payload["mixed_outcome_adapter_created"] is True
    assert payload["mixed_outcome_operations_ran"] is True
    assert payload["accounting_dry_run_enabled"] is True
    assert payload["issue_prefetch_accepted"] is True
    assert payload["duplicate_issue_suppressed"] is True
    assert payload["prefetched_demand_hit"] is True
    assert payload["unprefetched_demand_hit"] is False
    assert payload["unprefetched_demand_missed"] is True
    assert payload["live_adapter_instance_created"] is False
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    assert payload["resident_count"] == 2
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["unused_fetch_count"] == 0
    assert payload["demand_count"] == 2
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 1
    assert payload["evicted_before_use_count"] == 0
    assert payload["ready_late_miss_count"] == 0
    assert payload["late_completion_unused_count"] == 0
    assert payload["queue_batch_count"] == 1
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert (
        payload["block_reason"]
        == "live_runtime_adapter_mixed_outcome_dry_run_canary_only"
    )
    assert (
        payload["execution_mode"]
        == "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary_payloadless"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_mixed_outcome_dry_run_canary_rejects_side_effects() -> None:
    accounting_status = (
        "blocked_by_operation_rejection_canary:"
        "blocked_by_object_shell_evidence:"
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary",
        "status": f"blocked_by_accounting_dry_run_canary:{accounting_status}",
        "consumes_accounting_dry_run_canary": True,
        "accounting_dry_run_canary_status": accounting_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "mixed_outcome_schema": (
            "ready_time_payload_cache_runtime_adapter_mixed_outcome_dry_run_canary_v1"
        ),
        "mixed_outcome_adapter_created": True,
        "mixed_outcome_operations_ran": True,
        "accounting_dry_run_enabled": True,
        "issue_prefetch_accepted": True,
        "duplicate_issue_suppressed": True,
        "prefetched_demand_hit": True,
        "unprefetched_demand_hit": False,
        "unprefetched_demand_missed": True,
        "live_adapter_instance_created": False,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="unprefetched demand"):
        PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
            **{
                **base_kwargs,
                "unprefetched_demand_hit": True,
            },
        )

    with pytest.raises(ValueError, match="unprefetched_demand_missed"):
        PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
            **{
                **base_kwargs,
                "unprefetched_demand_missed": False,
            },
        )

    with pytest.raises(ValueError, match="demand_miss_count"):
        PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
            **{
                **base_kwargs,
                "demand_miss_count": 0,
            },
        )

    with pytest.raises(ValueError, match="live adapter instance"):
        PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
            **{
                **base_kwargs,
                "live_adapter_instance_created": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_mixed_outcome_dry_run_canary_builder_rejects_bad_accounting_canary() -> None:
    accounting = _build_live_runtime_adapter_accounting_dry_run_canary()

    object.__setattr__(accounting, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(accounting)

    accounting = _build_live_runtime_adapter_accounting_dry_run_canary()
    object.__setattr__(accounting, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(accounting)

    accounting = _build_live_runtime_adapter_accounting_dry_run_canary()
    object.__setattr__(accounting, "operation_rejection_canary_status", "stale")
    object.__setattr__(
        accounting,
        "status",
        "blocked_by_operation_rejection_canary:stale",
    )
    with pytest.raises(ValueError, match="rejection status chain"):
        build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(accounting)

    accounting = _build_live_runtime_adapter_accounting_dry_run_canary()
    object.__setattr__(accounting, "resident_count", 0)
    with pytest.raises(ValueError, match="resident_count"):
        build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(accounting)

    accounting = _build_live_runtime_adapter_accounting_dry_run_canary()
    object.__setattr__(accounting, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(accounting)


def _build_live_runtime_adapter_mixed_outcome_dry_run_canary() -> (
    PayloadCacheLiveRuntimeAdapterMixedOutcomeDryRunCanary
):
    return build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(
        _build_live_runtime_adapter_accounting_dry_run_canary(),
    )


def test_live_runtime_adapter_payloadless_instance_canary_consumes_mixed_outcome_canary() -> None:
    mixed = _build_live_runtime_adapter_mixed_outcome_dry_run_canary()

    canary = build_payload_cache_live_runtime_adapter_payloadless_instance_canary(
        mixed,
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == (
        "payload_cache_live_runtime_adapter_payloadless_instance_canary"
    )
    assert payload["status"] == (
        f"blocked_by_mixed_outcome_dry_run_canary:{mixed.status}"
    )
    assert payload["consumes_mixed_outcome_dry_run_canary"] is True
    assert payload["mixed_outcome_dry_run_canary_status"] == mixed.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["payloadless_instance_schema"] == (
        "ready_time_payload_cache_runtime_adapter_payloadless_instance_canary_v1"
    )
    assert payload["payloadless_live_adapter_created"] is True
    assert payload["payloadless_live_operations_ran"] is True
    assert payload["accounting_dry_run_enabled"] is True
    assert payload["issue_prefetch_accepted"] is True
    assert payload["duplicate_issue_suppressed"] is True
    assert payload["prefetched_demand_hit"] is True
    assert payload["unprefetched_demand_hit"] is False
    assert payload["unprefetched_demand_missed"] is True
    assert payload["live_adapter_instance_created"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    assert payload["resident_count"] == 2
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["unused_fetch_count"] == 0
    assert payload["demand_count"] == 2
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 1
    assert payload["evicted_before_use_count"] == 0
    assert payload["ready_late_miss_count"] == 0
    assert payload["late_completion_unused_count"] == 0
    assert payload["queue_batch_count"] == 1
    for key in (
        "queue_service_us",
        "queue_total_span_us",
        "queue_wait_us",
        "queue_max_delay_us",
    ):
        assert payload[key] == 0.0
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert (
        payload["block_reason"]
        == "live_runtime_adapter_payloadless_instance_canary_only"
    )
    assert payload["execution_mode"] == (
        "payload_cache_live_runtime_adapter_payloadless_instance_canary_payloadless"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_payloadless_instance_canary_rejects_side_effects() -> None:
    mixed_status = (
        "blocked_by_accounting_dry_run_canary:"
        "blocked_by_operation_rejection_canary:"
        "blocked_by_object_shell_evidence:"
        "blocked_by_instance_construction_plan:"
        "blocked_by_constructor_binding_preflight:"
        "blocked_by_instantiation_canary:"
        "blocked_by_state_validation_artifact:"
        "blocked_by_adapter_state_validation_preflight:"
        "blocked_by_adapter_state_object_preflight:"
        "blocked_by_adapter_materialization_preflight:"
        "blocked_by_object_adapter_preflight:"
        "blocked_by_object_construction_preflight:"
        "blocked_by_state_shape_check:"
        "blocked_by_live_runtime_canary:"
        "blocked_by_live_runtime_preflight:"
        "blocked_by_runtime_snapshot:"
        "blocked_by_runtime_skeleton:"
        "blocked_by_manager_artifact:"
        "blocked_by_live_payload_runtime:"
        "blocked_by_live_payload_stage:"
        "blocked_by_queue_budget_runtime_envelope:"
        "model_queue_budget_satisfied_runtime_disabled"
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payloadless_instance_canary",
        "status": f"blocked_by_mixed_outcome_dry_run_canary:{mixed_status}",
        "consumes_mixed_outcome_dry_run_canary": True,
        "mixed_outcome_dry_run_canary_status": mixed_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "payloadless_instance_schema": (
            "ready_time_payload_cache_runtime_adapter_payloadless_instance_canary_v1"
        ),
        "payloadless_live_adapter_created": True,
        "payloadless_live_operations_ran": True,
        "accounting_dry_run_enabled": True,
        "issue_prefetch_accepted": True,
        "duplicate_issue_suppressed": True,
        "prefetched_demand_hit": True,
        "unprefetched_demand_hit": False,
        "unprefetched_demand_missed": True,
        "live_adapter_instance_created": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="live_runtime_instantiated"):
        PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_payloadless_instance_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payloadless_instance_canary_builder_rejects_bad_mixed_outcome_canary() -> None:
    mixed = _build_live_runtime_adapter_mixed_outcome_dry_run_canary()

    object.__setattr__(mixed, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payloadless_instance_canary(mixed)

    mixed = _build_live_runtime_adapter_mixed_outcome_dry_run_canary()
    object.__setattr__(mixed, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_payloadless_instance_canary(mixed)

    mixed = _build_live_runtime_adapter_mixed_outcome_dry_run_canary()
    object.__setattr__(mixed, "accounting_dry_run_canary_status", "stale")
    object.__setattr__(
        mixed,
        "status",
        "blocked_by_accounting_dry_run_canary:stale",
    )
    with pytest.raises(ValueError, match="accounting status chain"):
        build_payload_cache_live_runtime_adapter_payloadless_instance_canary(mixed)

    mixed = _build_live_runtime_adapter_mixed_outcome_dry_run_canary()
    object.__setattr__(mixed, "live_adapter_instance_created", True)
    with pytest.raises(ValueError, match="must not create live adapter"):
        build_payload_cache_live_runtime_adapter_payloadless_instance_canary(mixed)

    mixed = _build_live_runtime_adapter_mixed_outcome_dry_run_canary()
    object.__setattr__(mixed, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_payloadless_instance_canary(mixed)


def _build_live_runtime_adapter_payloadless_instance_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadlessInstanceCanary
):
    return build_payload_cache_live_runtime_adapter_payloadless_instance_canary(
        _build_live_runtime_adapter_mixed_outcome_dry_run_canary(),
    )


def test_live_runtime_adapter_payload_transfer_toggle_disabled_canary_consumes_payloadless_instance() -> None:
    payloadless = _build_live_runtime_adapter_payloadless_instance_canary()

    canary = (
        build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
            payloadless,
        )
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == (
        "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary"
    )
    assert payload["status"] == (
        f"blocked_by_payloadless_instance_canary:{payloadless.status}"
    )
    assert payload["consumes_payloadless_instance_canary"] is True
    assert payload["payloadless_instance_canary_status"] == payloadless.status
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_runtime_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["manager_runtime_mode"] == "ready_time_payload_cache_skeleton"
    assert payload["payload_transfer_toggle_schema"] == (
        "ready_time_payload_cache_runtime_payload_transfer_toggle_disabled_canary_v1"
    )
    assert payload["payload_transfer_toggle_created"] is True
    assert payload["payload_issue_rejected"] is True
    assert payload["payloadless_live_adapter_created"] is True
    assert payload["payloadless_live_operations_ran"] is True
    assert payload["live_adapter_instance_created"] is True
    assert payload["live_runtime_instantiated"] is False
    assert payload["capacity_entries"] == 4096
    assert payload["issue_lead_tokens"] == 32
    assert payload["queue_deadline_us"] == 100.0
    assert payload["lookahead_us"] == 2_400_000.0
    assert payload["queue_batch_size"] == 1
    assert payload["resident_count"] == 2
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["unused_fetch_count"] == 0
    assert payload["demand_count"] == 2
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 1
    assert payload["evicted_before_use_count"] == 0
    assert payload["ready_late_miss_count"] == 0
    assert payload["late_completion_unused_count"] == 0
    assert payload["queue_batch_count"] == 1
    assert payload["shifted_issue_accounting_enabled"] is True
    assert payload["shifted_issue_accounted_packet_count"] == 28
    assert payload["shifted_issue_unique_issue_key_count"] == 16
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == (
        "live_runtime_adapter_payload_transfer_toggle_disabled_canary_only"
    )
    assert payload["execution_mode"] == (
        "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary_payloadless"
    )
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_payload_transfer_toggle_disabled_canary_rejects_side_effects() -> None:
    payloadless_status = _build_live_runtime_adapter_payloadless_instance_canary().status
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary",
        "status": f"blocked_by_payloadless_instance_canary:{payloadless_status}",
        "consumes_payloadless_instance_canary": True,
        "payloadless_instance_canary_status": payloadless_status,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_runtime_contract": "ready_time_issue_demand_skeleton_v1",
        "manager_runtime_mode": "ready_time_payload_cache_skeleton",
        "payload_transfer_toggle_schema": (
            "ready_time_payload_cache_runtime_payload_transfer_toggle_disabled_canary_v1"
        ),
        "payload_transfer_toggle_created": True,
        "payload_issue_rejected": True,
        "payloadless_live_adapter_created": True,
        "payloadless_live_operations_ran": True,
        "live_adapter_instance_created": True,
        "live_runtime_instantiated": False,
        "capacity_entries": 4096,
        "issue_lead_tokens": 32,
        "queue_deadline_us": 100.0,
        "lookahead_us": 2_400_000.0,
        "queue_batch_size": 1,
        "resident_count": 2,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_unique_issue_key_count": 16,
    }

    with pytest.raises(ValueError, match="payload_issue_rejected"):
        PayloadCacheLiveRuntimeAdapterPayloadTransferToggleDisabledCanary(
            **{
                **base_kwargs,
                "payload_issue_rejected": False,
            },
        )

    with pytest.raises(ValueError, match="live_runtime_instantiated"):
        PayloadCacheLiveRuntimeAdapterPayloadTransferToggleDisabledCanary(
            **{
                **base_kwargs,
                "live_runtime_instantiated": True,
            },
        )

    for field_name in ("issued_payload_count", "payload_bytes"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadTransferToggleDisabledCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadTransferToggleDisabledCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_transfer_toggle_disabled_canary_builder_rejects_bad_payloadless_instance() -> None:
    payloadless = _build_live_runtime_adapter_payloadless_instance_canary()

    object.__setattr__(payloadless, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
            payloadless,
        )

    payloadless = _build_live_runtime_adapter_payloadless_instance_canary()
    object.__setattr__(payloadless, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
            payloadless,
        )

    payloadless = _build_live_runtime_adapter_payloadless_instance_canary()
    object.__setattr__(payloadless, "mixed_outcome_dry_run_canary_status", "stale")
    object.__setattr__(
        payloadless,
        "status",
        "blocked_by_mixed_outcome_dry_run_canary:stale",
    )
    with pytest.raises(ValueError, match="ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
            payloadless,
        )

    payloadless = _build_live_runtime_adapter_payloadless_instance_canary()
    object.__setattr__(payloadless, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
            payloadless,
        )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
            object(),  # type: ignore[arg-type]
        )


def _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadTransferToggleDisabledCanary
):
    return build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
        _build_live_runtime_adapter_payloadless_instance_canary(),
    )


def _build_source_bound_payload_issue_request_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueRequestBlockedCanary
):
    return build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
        _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary(),
        request_source="queue_budget_first_model_passing_cell",
        source_issue_packet_count=28,
        source_issue_unique_key_count=28,
        source_queue_budget_capacity=4096,
        source_issue_lead_tokens=8,
        source_queue_deadline_us=100.0,
    )


def _build_payload_issue_scheduler_dispatch_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueSchedulerDispatchBlockedCanary
):
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )
    return build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary(
        admission,
    )


def _build_payload_issue_command_packet_dry_run() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueCommandPacketDryRun
):
    return build_payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run(
        _build_payload_issue_scheduler_dispatch_blocked_canary(),
    )


def _build_payload_issue_transport_enqueue_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueTransportEnqueueBlockedCanary
):
    return build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary(
        _build_payload_issue_command_packet_dry_run(),
    )


def _build_payload_issue_transport_worker_dispatch_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueTransportWorkerDispatchBlockedCanary
):
    return build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary(
        _build_payload_issue_transport_enqueue_blocked_canary(),
    )


def _build_payload_issue_copy_descriptor_dry_run() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDryRun
):
    return build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run(
        _build_payload_issue_transport_worker_dispatch_blocked_canary(),
    )


def _build_payload_issue_copy_descriptor_submit_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorSubmitBlockedCanary
):
    return build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary(
        _build_payload_issue_copy_descriptor_dry_run(),
    )


def _build_payload_issue_copy_descriptor_dispatch_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDispatchBlockedCanary
):
    return build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary(
        _build_payload_issue_copy_descriptor_submit_blocked_canary(),
    )


def _build_payload_issue_copy_descriptor_execution_blocked_canary() -> (
    PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorExecutionBlockedCanary
):
    return build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary(
        _build_payload_issue_copy_descriptor_dispatch_blocked_canary(),
    )


def test_live_runtime_adapter_payload_issue_request_blocked_canary_consumes_disabled_toggle() -> None:
    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
        toggle,
    )
    payload = canary.as_dict()

    assert payload["present"] is True
    assert payload["stage"] == (
        "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary"
    )
    assert payload["status"] == (
        f"blocked_by_payload_transfer_toggle_disabled_canary:{toggle.status}"
    )
    assert payload["consumes_payload_transfer_toggle_disabled_canary"] is True
    assert payload["payload_transfer_toggle_disabled_canary_status"] == toggle.status
    assert payload["payload_issue_request_schema"] == (
        "payload_cache_runtime_payload_issue_request_v1"
    )
    assert payload["payload_issue_request_created"] is True
    assert payload["payload_issue_rejected"] is True
    assert payload["request_layer_idx"] == 0
    assert payload["request_expert_idx"] == 0
    assert payload["requested_payload_bytes"] == 64
    assert payload["request_source"] == "synthetic_payload_issue_request"
    assert payload["source_issue_packet_count"] == 0
    assert payload["source_issue_unique_key_count"] == 0
    assert payload["source_queue_budget_capacity"] == 0
    assert payload["source_issue_lead_tokens"] == 0
    assert payload["source_queue_deadline_us"] == 0.0
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    assert payload["decision"] == "blocked"
    assert payload["block_reason"] == (
        "live_runtime_adapter_payload_issue_request_blocked_canary_only"
    )
    assert payload["execution_mode"] == (
        "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary_payloadless"
    )
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False


def test_live_runtime_adapter_payload_issue_request_blocked_canary_rejects_side_effects() -> None:
    toggle_status = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary().status
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary",
        "status": f"blocked_by_payload_transfer_toggle_disabled_canary:{toggle_status}",
        "consumes_payload_transfer_toggle_disabled_canary": True,
        "payload_transfer_toggle_disabled_canary_status": toggle_status,
        "payload_issue_request_schema": "payload_cache_runtime_payload_issue_request_v1",
        "payload_issue_request_created": True,
        "payload_issue_rejected": True,
        "request_layer_idx": 0,
        "request_expert_idx": 0,
        "requested_payload_bytes": 64,
    }

    for field_name in ("issued_payload_count", "payload_bytes"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueRequestBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "payload_issue_request_created",
        "payload_issue_rejected",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueRequestBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: False,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueRequestBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_issue_request_blocked_canary_builder_rejects_bad_toggle() -> None:
    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()

    object.__setattr__(toggle, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            toggle,
        )

    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()
    object.__setattr__(toggle, "status", "passed")
    with pytest.raises(ValueError, match="status mismatch"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            toggle,
        )

    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()
    object.__setattr__(toggle, "payload_issue_rejected", False)
    with pytest.raises(ValueError, match="reject issue"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            toggle,
        )

    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()
    object.__setattr__(toggle, "payload_bytes", 1)
    with pytest.raises(ValueError, match="payload_bytes"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            toggle,
        )

    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()
    object.__setattr__(toggle, "consumes_payloadless_instance_canary", False)
    with pytest.raises(ValueError, match="consume payloadless"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            toggle,
        )

    toggle = _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary()
    object.__setattr__(toggle, "payloadless_instance_canary_status", "stale")
    object.__setattr__(
        toggle,
        "status",
        "blocked_by_payloadless_instance_canary:stale",
    )
    with pytest.raises(ValueError, match="ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            toggle,
        )

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_plan_dry_run_consumes_source_bound_request() -> None:
    request = _build_source_bound_payload_issue_request_blocked_canary()

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    assert plan.present is True
    assert plan.stage == "payload_cache_live_runtime_adapter_payload_issue_plan_dry_run"
    assert (
        plan.status
        == f"blocked_by_payload_issue_request_blocked_canary:{request.status}"
    )
    assert plan.consumes_payload_issue_request_blocked_canary is True
    assert plan.payload_issue_request_blocked_canary_status == request.status
    assert plan.request_source == "queue_budget_first_model_passing_cell"
    assert plan.source_issue_packet_count == 28
    assert plan.source_issue_unique_key_count == 28
    assert plan.source_queue_budget_capacity == 4096
    assert plan.source_issue_lead_tokens == 8
    assert plan.source_queue_deadline_us == 100.0
    assert plan.request_layer_idx == 0
    assert plan.request_expert_idx == 0
    assert plan.requested_payload_bytes == 64
    assert plan.planned_issue_count == 0
    assert plan.issued_payload_count == 0
    assert plan.payload_bytes == 0
    assert plan.decision == "blocked"
    assert plan.block_reason == "payload_transfer_disabled"
    assert plan.payload_transfer_runtime_enabled is False
    assert plan.kernel_arg_pass_allowed is False
    assert plan.passed_to_kernel is False
    assert plan.changes_kernel_launch_args is False
    assert plan.full_fetch_runtime_allowed is False


def test_live_runtime_adapter_payload_issue_plan_dry_run_rejects_side_effects() -> None:
    request = _build_source_bound_payload_issue_request_blocked_canary()
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_plan_dry_run",
        "status": f"blocked_by_payload_issue_request_blocked_canary:{request.status}",
        "consumes_payload_issue_request_blocked_canary": True,
        "payload_issue_request_blocked_canary_status": request.status,
        "request_source": request.request_source,
        "request_layer_idx": request.request_layer_idx,
        "request_expert_idx": request.request_expert_idx,
        "requested_payload_bytes": request.requested_payload_bytes,
        "source_issue_packet_count": request.source_issue_packet_count,
        "source_issue_unique_key_count": request.source_issue_unique_key_count,
        "source_queue_budget_capacity": request.source_queue_budget_capacity,
        "source_issue_lead_tokens": request.source_issue_lead_tokens,
        "source_queue_deadline_us": request.source_queue_deadline_us,
    }

    for field_name in ("planned_issue_count", "issued_payload_count", "payload_bytes"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssuePlanDryRun(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssuePlanDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_issue_plan_dry_run_builder_rejects_bad_request() -> None:
    request = _build_source_bound_payload_issue_request_blocked_canary()

    object.__setattr__(request, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    request = _build_source_bound_payload_issue_request_blocked_canary()
    object.__setattr__(request, "payload_transfer_runtime_enabled", True)
    with pytest.raises(ValueError, match="payload_transfer_runtime_enabled"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    request = _build_source_bound_payload_issue_request_blocked_canary()
    object.__setattr__(request, "source_queue_budget_capacity", -1)
    with pytest.raises(ValueError, match="source_queue_budget_capacity"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    request = build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
        _build_live_runtime_adapter_payload_transfer_toggle_disabled_canary(),
    )
    with pytest.raises(ValueError, match="source-bound queue-budget request"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    request = _build_source_bound_payload_issue_request_blocked_canary()
    object.__setattr__(
        request,
        "payload_transfer_toggle_disabled_canary_status",
        "blocked_by_payloadless_instance_canary:stale",
    )
    object.__setattr__(
        request,
        "status",
        "blocked_by_payload_transfer_toggle_disabled_canary:"
        "blocked_by_payloadless_instance_canary:stale",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    request = _build_source_bound_payload_issue_request_blocked_canary()
    stale_toggle_status = request.payload_transfer_toggle_disabled_canary_status.replace(
        "model_queue_budget_satisfied_runtime_disabled",
        "stale_queue_budget_status",
    )
    object.__setattr__(
        request,
        "payload_transfer_toggle_disabled_canary_status",
        stale_toggle_status,
    )
    object.__setattr__(
        request,
        "status",
        f"blocked_by_payload_transfer_toggle_disabled_canary:{stale_toggle_status}",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    request = _build_source_bound_payload_issue_request_blocked_canary()
    injected_stale_status = request.payload_transfer_toggle_disabled_canary_status.replace(
        "blocked_by_queue_budget_runtime_envelope:",
        "blocked_by_queue_budget_runtime_envelope:stale:",
    )
    object.__setattr__(
        request,
        "payload_transfer_toggle_disabled_canary_status",
        injected_stale_status,
    )
    object.__setattr__(
        request,
        "status",
        f"blocked_by_payload_transfer_toggle_disabled_canary:{injected_stale_status}",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(request)

    with pytest.raises(TypeError, match="canary"):
        build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_executor_dry_run_consumes_plan() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )

    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )

    assert executor.present is True
    assert executor.stage == "payload_cache_live_runtime_adapter_payload_issue_executor_dry_run"
    assert executor.status == f"blocked_by_payload_issue_plan_dry_run:{plan.status}"
    assert executor.consumes_payload_issue_plan_dry_run is True
    assert executor.payload_issue_plan_status == plan.status
    assert executor.payload_issue_executor_schema == (
        "payload_cache_runtime_payload_issue_executor_v1"
    )
    assert executor.payload_issue_executor_created is True
    assert executor.payload_issue_plan_consumed is True
    assert executor.request_source == "queue_budget_first_model_passing_cell"
    assert executor.source_issue_packet_count == 28
    assert executor.source_issue_unique_key_count == 28
    assert executor.source_queue_budget_capacity == 4096
    assert executor.source_issue_lead_tokens == 8
    assert executor.source_queue_deadline_us == 100.0
    assert executor.planned_issue_count == 0
    assert executor.scheduled_issue_count == 0
    assert executor.issued_payload_count == 0
    assert executor.payload_bytes == 0
    assert executor.payload_transfer_runtime_enabled is False
    assert executor.ready_credit is False
    assert executor.kernel_arg_pass_allowed is False
    assert executor.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_executor_dry_run_rejects_side_effects() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_executor_dry_run",
        "status": f"blocked_by_payload_issue_plan_dry_run:{plan.status}",
        "consumes_payload_issue_plan_dry_run": True,
        "payload_issue_plan_status": plan.status,
        "payload_issue_executor_schema": "payload_cache_runtime_payload_issue_executor_v1",
        "payload_issue_executor_created": True,
        "payload_issue_plan_consumed": True,
        "request_source": plan.request_source,
        "request_layer_idx": plan.request_layer_idx,
        "request_expert_idx": plan.request_expert_idx,
        "requested_payload_bytes": plan.requested_payload_bytes,
        "source_issue_packet_count": plan.source_issue_packet_count,
        "source_issue_unique_key_count": plan.source_issue_unique_key_count,
        "source_queue_budget_capacity": plan.source_queue_budget_capacity,
        "source_issue_lead_tokens": plan.source_issue_lead_tokens,
        "source_queue_deadline_us": plan.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueExecutorDryRun(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueExecutorDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_issue_executor_dry_run_builder_rejects_bad_plan() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )

    object.__setattr__(plan, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    object.__setattr__(plan, "planned_issue_count", 1)
    with pytest.raises(ValueError, match="planned_issue_count"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    object.__setattr__(plan, "payload_transfer_runtime_enabled", True)
    with pytest.raises(ValueError, match="payload_transfer_runtime_enabled"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    object.__setattr__(plan, "source_issue_packet_count", 0)
    with pytest.raises(ValueError, match="source_issue_packet_count"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    object.__setattr__(
        plan,
        "payload_issue_request_blocked_canary_status",
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    object.__setattr__(
        plan,
        "status",
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    stale_request_status = plan.payload_issue_request_blocked_canary_status.replace(
        "model_queue_budget_satisfied_runtime_disabled",
        "stale_queue_budget_status",
    )
    object.__setattr__(
        plan,
        "payload_issue_request_blocked_canary_status",
        stale_request_status,
    )
    object.__setattr__(
        plan,
        "status",
        f"blocked_by_payload_issue_request_blocked_canary:{stale_request_status}",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    injected_stale_request_status = plan.payload_issue_request_blocked_canary_status.replace(
        "blocked_by_queue_budget_runtime_envelope:",
        "blocked_by_queue_budget_runtime_envelope:stale:",
    )
    object.__setattr__(
        plan,
        "payload_issue_request_blocked_canary_status",
        injected_stale_request_status,
    )
    object.__setattr__(
        plan,
        "status",
        f"blocked_by_payload_issue_request_blocked_canary:{injected_stale_request_status}",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(plan)

    with pytest.raises(TypeError, match="plan"):
        build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_queue_entry_dry_run_consumes_executor() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )

    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )

    assert entry.present is True
    assert (
        entry.stage
        == "payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run"
    )
    assert entry.status == f"blocked_by_payload_issue_executor_dry_run:{executor.status}"
    assert entry.consumes_payload_issue_executor_dry_run is True
    assert entry.payload_issue_executor_status == executor.status
    assert entry.payload_issue_queue_entry_schema == (
        "payload_cache_runtime_payload_issue_queue_entry_v1"
    )
    assert entry.payload_issue_queue_entry_created is True
    assert entry.payload_issue_executor_consumed is True
    assert entry.queue_entry_shape_checked is True
    assert entry.queue_entry_enqueued is False
    assert entry.queue_submit_allowed is False
    assert entry.request_source == "queue_budget_first_model_passing_cell"
    assert entry.source_issue_packet_count == 28
    assert entry.source_issue_unique_key_count == 28
    assert entry.source_queue_budget_capacity == 4096
    assert entry.source_issue_lead_tokens == 8
    assert entry.source_queue_deadline_us == 100.0
    assert entry.planned_issue_count == 0
    assert entry.scheduled_issue_count == 0
    assert entry.queued_issue_count == 0
    assert entry.issued_payload_count == 0
    assert entry.payload_bytes == 0
    assert entry.payload_transfer_runtime_enabled is False
    assert entry.ready_credit is False
    assert entry.kernel_arg_pass_allowed is False
    assert entry.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_queue_entry_dry_run_rejects_side_effects() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run",
        "status": f"blocked_by_payload_issue_executor_dry_run:{executor.status}",
        "consumes_payload_issue_executor_dry_run": True,
        "payload_issue_executor_status": executor.status,
        "payload_issue_queue_entry_schema": (
            "payload_cache_runtime_payload_issue_queue_entry_v1"
        ),
        "payload_issue_queue_entry_created": True,
        "payload_issue_executor_consumed": True,
        "queue_entry_shape_checked": True,
        "queue_entry_enqueued": False,
        "queue_submit_allowed": False,
        "request_source": executor.request_source,
        "request_layer_idx": executor.request_layer_idx,
        "request_expert_idx": executor.request_expert_idx,
        "requested_payload_bytes": executor.requested_payload_bytes,
        "source_issue_packet_count": executor.source_issue_packet_count,
        "source_issue_unique_key_count": executor.source_issue_unique_key_count,
        "source_queue_budget_capacity": executor.source_queue_budget_capacity,
        "source_issue_lead_tokens": executor.source_issue_lead_tokens,
        "source_queue_deadline_us": executor.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueQueueEntryDryRun(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("queue_entry_enqueued", "queue_submit_allowed"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueQueueEntryDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(ValueError, match="upstream ancestry status"):
        PayloadCacheLiveRuntimeAdapterPayloadIssueQueueEntryDryRun(
            **{
                **base_kwargs,
                "payload_issue_executor_status": (
                    "blocked_by_payload_issue_plan_dry_run:"
                    "blocked_by_payload_issue_request_blocked_canary:"
                    "blocked_by_payload_transfer_toggle_disabled_canary:stale"
                ),
                "status": (
                    "blocked_by_payload_issue_executor_dry_run:"
                    "blocked_by_payload_issue_plan_dry_run:"
                    "blocked_by_payload_issue_request_blocked_canary:"
                    "blocked_by_payload_transfer_toggle_disabled_canary:stale"
                ),
            },
        )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueQueueEntryDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_issue_queue_entry_dry_run_builder_rejects_bad_executor() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )

    object.__setattr__(executor, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
            executor,
        )

    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    object.__setattr__(executor, "scheduled_issue_count", 1)
    with pytest.raises(ValueError, match="scheduled_issue_count"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
            executor,
        )

    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    object.__setattr__(executor, "payload_transfer_runtime_enabled", True)
    with pytest.raises(ValueError, match="payload_transfer_runtime_enabled"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
            executor,
        )

    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    object.__setattr__(
        executor,
        "payload_issue_plan_status",
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    object.__setattr__(
        executor,
        "status",
        "blocked_by_payload_issue_plan_dry_run:"
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
            executor,
        )

    with pytest.raises(TypeError, match="executor"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_queue_submit_blocked_canary_consumes_entry() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )

    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )

    assert submit.present is True
    assert (
        submit.stage
        == "payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary"
    )
    assert submit.status == f"blocked_by_payload_issue_queue_entry_dry_run:{entry.status}"
    assert submit.consumes_payload_issue_queue_entry_dry_run is True
    assert submit.payload_issue_queue_entry_status == entry.status
    assert submit.payload_issue_queue_submit_schema == (
        "payload_cache_runtime_payload_issue_queue_submit_v1"
    )
    assert submit.payload_issue_queue_submit_canary_created is True
    assert submit.payload_issue_queue_entry_consumed is True
    assert submit.queue_submit_checked is True
    assert submit.queue_submit_rejected is True
    assert submit.queue_submit_allowed is False
    assert submit.queue_entry_enqueued is False
    assert submit.request_source == "queue_budget_first_model_passing_cell"
    assert submit.source_issue_packet_count == 28
    assert submit.source_issue_unique_key_count == 28
    assert submit.source_queue_budget_capacity == 4096
    assert submit.source_issue_lead_tokens == 8
    assert submit.source_queue_deadline_us == 100.0
    assert submit.planned_issue_count == 0
    assert submit.scheduled_issue_count == 0
    assert submit.queued_issue_count == 0
    assert submit.submitted_issue_count == 0
    assert submit.issued_payload_count == 0
    assert submit.payload_bytes == 0
    assert submit.payload_transfer_runtime_enabled is False
    assert submit.ready_credit is False
    assert submit.kernel_arg_pass_allowed is False
    assert submit.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_queue_submit_blocked_canary_rejects_side_effects() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary",
        "status": f"blocked_by_payload_issue_queue_entry_dry_run:{entry.status}",
        "consumes_payload_issue_queue_entry_dry_run": True,
        "payload_issue_queue_entry_status": entry.status,
        "payload_issue_queue_submit_schema": (
            "payload_cache_runtime_payload_issue_queue_submit_v1"
        ),
        "payload_issue_queue_submit_canary_created": True,
        "payload_issue_queue_entry_consumed": True,
        "queue_submit_checked": True,
        "queue_submit_rejected": True,
        "queue_submit_allowed": False,
        "queue_entry_enqueued": False,
        "request_source": entry.request_source,
        "request_layer_idx": entry.request_layer_idx,
        "request_expert_idx": entry.request_expert_idx,
        "requested_payload_bytes": entry.requested_payload_bytes,
        "source_issue_packet_count": entry.source_issue_packet_count,
        "source_issue_unique_key_count": entry.source_issue_unique_key_count,
        "source_queue_budget_capacity": entry.source_queue_budget_capacity,
        "source_issue_lead_tokens": entry.source_issue_lead_tokens,
        "source_queue_deadline_us": entry.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueQueueSubmitBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("queue_submit_allowed", "queue_entry_enqueued"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueQueueSubmitBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueQueueSubmitBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_issue_queue_submit_blocked_canary_builder_rejects_bad_entry() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )

    object.__setattr__(entry, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )

    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    object.__setattr__(entry, "queued_issue_count", 1)
    with pytest.raises(ValueError, match="queued_issue_count"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )

    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    object.__setattr__(entry, "queue_entry_enqueued", True)
    with pytest.raises(ValueError, match="queue_entry_enqueued"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )

    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    object.__setattr__(
        entry,
        "payload_issue_executor_status",
        "blocked_by_payload_issue_plan_dry_run:"
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    object.__setattr__(
        entry,
        "status",
        "blocked_by_payload_issue_executor_dry_run:"
        "blocked_by_payload_issue_plan_dry_run:"
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )

    with pytest.raises(TypeError, match="entry"):
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary_consumes_submit() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )

    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )

    assert admission.present is True
    assert admission.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_inflight_admission_blocked_canary"
    )
    assert admission.status == (
        f"blocked_by_payload_issue_queue_submit_blocked_canary:{submit.status}"
    )
    assert admission.consumes_payload_issue_queue_submit_blocked_canary is True
    assert admission.payload_issue_queue_submit_status == submit.status
    assert admission.payload_issue_inflight_admission_schema == (
        "payload_cache_runtime_payload_issue_inflight_admission_v1"
    )
    assert admission.payload_issue_inflight_admission_canary_created is True
    assert admission.payload_issue_queue_submit_consumed is True
    assert admission.inflight_admission_checked is True
    assert admission.inflight_admission_rejected is True
    assert admission.inflight_admission_allowed is False
    assert admission.inflight_queue_enqueued is False
    assert admission.request_source == "queue_budget_first_model_passing_cell"
    assert admission.source_issue_packet_count == 28
    assert admission.source_issue_unique_key_count == 28
    assert admission.source_queue_budget_capacity == 4096
    assert admission.source_issue_lead_tokens == 8
    assert admission.source_queue_deadline_us == 100.0
    assert admission.planned_issue_count == 0
    assert admission.scheduled_issue_count == 0
    assert admission.queued_issue_count == 0
    assert admission.submitted_issue_count == 0
    assert admission.inflight_issue_count == 0
    assert admission.issued_payload_count == 0
    assert admission.payload_bytes == 0
    assert admission.ready_credit is False
    assert admission.kernel_arg_pass_allowed is False
    assert admission.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary_rejects_side_effects() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_inflight_admission_blocked_canary"
        ),
        "status": (
            f"blocked_by_payload_issue_queue_submit_blocked_canary:{submit.status}"
        ),
        "consumes_payload_issue_queue_submit_blocked_canary": True,
        "payload_issue_queue_submit_status": submit.status,
        "payload_issue_inflight_admission_schema": (
            "payload_cache_runtime_payload_issue_inflight_admission_v1"
        ),
        "payload_issue_inflight_admission_canary_created": True,
        "payload_issue_queue_submit_consumed": True,
        "inflight_admission_checked": True,
        "inflight_admission_rejected": True,
        "inflight_admission_allowed": False,
        "inflight_queue_enqueued": False,
        "request_source": submit.request_source,
        "request_layer_idx": submit.request_layer_idx,
        "request_expert_idx": submit.request_expert_idx,
        "requested_payload_bytes": submit.requested_payload_bytes,
        "source_issue_packet_count": submit.source_issue_packet_count,
        "source_issue_unique_key_count": submit.source_issue_unique_key_count,
        "source_queue_budget_capacity": submit.source_queue_budget_capacity,
        "source_issue_lead_tokens": submit.source_issue_lead_tokens,
        "source_queue_deadline_us": submit.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueInflightAdmissionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("inflight_admission_allowed", "inflight_queue_enqueued"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueInflightAdmissionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueInflightAdmissionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary_builder_rejects_bad_submit() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )

    object.__setattr__(submit, "decision", "allow")
    with pytest.raises(ValueError, match="must stay blocked"):
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )

    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    object.__setattr__(submit, "submitted_issue_count", 1)
    with pytest.raises(ValueError, match="submitted_issue_count"):
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )

    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    object.__setattr__(submit, "queue_submit_allowed", True)
    with pytest.raises(ValueError, match="queue_submit_allowed"):
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )

    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    object.__setattr__(
        submit,
        "payload_issue_queue_entry_status",
        "blocked_by_payload_issue_executor_dry_run:"
        "blocked_by_payload_issue_plan_dry_run:"
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    object.__setattr__(
        submit,
        "status",
        "blocked_by_payload_issue_queue_entry_dry_run:"
        "blocked_by_payload_issue_executor_dry_run:"
        "blocked_by_payload_issue_plan_dry_run:"
        "blocked_by_payload_issue_request_blocked_canary:"
        "blocked_by_payload_transfer_toggle_disabled_canary:stale",
    )
    with pytest.raises(ValueError, match="upstream ancestry status chain"):
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )

    with pytest.raises(TypeError, match="submit"):
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary_consumes_admission() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )

    dispatch = (
        build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary(
            admission,
        )
    )

    assert dispatch.present is True
    assert dispatch.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_scheduler_dispatch_blocked_canary"
    )
    assert dispatch.status == (
        f"blocked_by_payload_issue_inflight_admission_blocked_canary:{admission.status}"
    )
    assert dispatch.consumes_payload_issue_inflight_admission_blocked_canary is True
    assert dispatch.payload_issue_inflight_admission_status == admission.status
    assert dispatch.payload_issue_scheduler_dispatch_schema == (
        "payload_cache_runtime_payload_issue_scheduler_dispatch_v1"
    )
    assert dispatch.payload_issue_scheduler_dispatch_canary_created is True
    assert dispatch.payload_issue_inflight_admission_consumed is True
    assert dispatch.scheduler_dispatch_checked is True
    assert dispatch.scheduler_dispatch_rejected is True
    assert dispatch.scheduler_dispatch_allowed is False
    assert dispatch.scheduler_dispatch_enqueued is False
    assert dispatch.request_source == "queue_budget_first_model_passing_cell"
    assert dispatch.source_issue_packet_count == 28
    assert dispatch.source_issue_unique_key_count == 28
    assert dispatch.source_queue_budget_capacity == 4096
    assert dispatch.source_issue_lead_tokens == 8
    assert dispatch.source_queue_deadline_us == 100.0
    assert dispatch.planned_issue_count == 0
    assert dispatch.scheduled_issue_count == 0
    assert dispatch.queued_issue_count == 0
    assert dispatch.submitted_issue_count == 0
    assert dispatch.inflight_issue_count == 0
    assert dispatch.dispatched_issue_count == 0
    assert dispatch.issued_payload_count == 0
    assert dispatch.payload_bytes == 0
    assert dispatch.ready_credit is False
    assert dispatch.kernel_arg_pass_allowed is False
    assert dispatch.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary_rejects_side_effects() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_scheduler_dispatch_blocked_canary"
        ),
        "status": (
            "blocked_by_payload_issue_inflight_admission_blocked_canary:"
            f"{admission.status}"
        ),
        "consumes_payload_issue_inflight_admission_blocked_canary": True,
        "payload_issue_inflight_admission_status": admission.status,
        "payload_issue_scheduler_dispatch_schema": (
            "payload_cache_runtime_payload_issue_scheduler_dispatch_v1"
        ),
        "payload_issue_scheduler_dispatch_canary_created": True,
        "payload_issue_inflight_admission_consumed": True,
        "scheduler_dispatch_checked": True,
        "scheduler_dispatch_rejected": True,
        "scheduler_dispatch_allowed": False,
        "scheduler_dispatch_enqueued": False,
        "request_source": admission.request_source,
        "request_layer_idx": admission.request_layer_idx,
        "request_expert_idx": admission.request_expert_idx,
        "requested_payload_bytes": admission.requested_payload_bytes,
        "source_issue_packet_count": admission.source_issue_packet_count,
        "source_issue_unique_key_count": admission.source_issue_unique_key_count,
        "source_queue_budget_capacity": admission.source_queue_budget_capacity,
        "source_issue_lead_tokens": admission.source_issue_lead_tokens,
        "source_queue_deadline_us": admission.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueSchedulerDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("scheduler_dispatch_allowed", "scheduler_dispatch_enqueued"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueSchedulerDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueSchedulerDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="admission"):
        build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_command_packet_dry_run_consumes_dispatch() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )
    dispatch = (
        build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary(
            admission,
        )
    )

    packet = build_payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run(
        dispatch,
    )

    assert packet.present is True
    assert packet.stage == "payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run"
    assert packet.status == (
        f"blocked_by_payload_issue_scheduler_dispatch_blocked_canary:{dispatch.status}"
    )
    assert packet.consumes_payload_issue_scheduler_dispatch_blocked_canary is True
    assert packet.payload_issue_scheduler_dispatch_status == dispatch.status
    assert packet.payload_issue_command_packet_schema == (
        "payload_cache_runtime_payload_issue_command_packet_v1"
    )
    assert packet.payload_issue_command_packet_created is True
    assert packet.payload_issue_scheduler_dispatch_consumed is True
    assert packet.command_packet_shape_checked is True
    assert packet.command_packet_submitted is False
    assert packet.command_packet_executed is False
    assert packet.request_source == "queue_budget_first_model_passing_cell"
    assert packet.source_issue_packet_count == 28
    assert packet.source_issue_unique_key_count == 28
    assert packet.source_queue_budget_capacity == 4096
    assert packet.source_issue_lead_tokens == 8
    assert packet.planned_issue_count == 0
    assert packet.scheduled_issue_count == 0
    assert packet.queued_issue_count == 0
    assert packet.submitted_issue_count == 0
    assert packet.inflight_issue_count == 0
    assert packet.dispatched_issue_count == 0
    assert packet.command_packet_count == 0
    assert packet.issued_payload_count == 0
    assert packet.payload_bytes == 0
    assert packet.ready_credit is False
    assert packet.kernel_arg_pass_allowed is False
    assert packet.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_command_packet_dry_run_rejects_side_effects() -> None:
    plan = build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
        _build_source_bound_payload_issue_request_blocked_canary(),
    )
    executor = build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
        plan,
    )
    entry = build_payload_cache_live_runtime_adapter_payload_issue_queue_entry_dry_run(
        executor,
    )
    submit = (
        build_payload_cache_live_runtime_adapter_payload_issue_queue_submit_blocked_canary(
            entry,
        )
    )
    admission = (
        build_payload_cache_live_runtime_adapter_payload_issue_inflight_admission_blocked_canary(
            submit,
        )
    )
    dispatch = (
        build_payload_cache_live_runtime_adapter_payload_issue_scheduler_dispatch_blocked_canary(
            admission,
        )
    )
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run",
        "status": (
            f"blocked_by_payload_issue_scheduler_dispatch_blocked_canary:{dispatch.status}"
        ),
        "consumes_payload_issue_scheduler_dispatch_blocked_canary": True,
        "payload_issue_scheduler_dispatch_status": dispatch.status,
        "payload_issue_command_packet_schema": (
            "payload_cache_runtime_payload_issue_command_packet_v1"
        ),
        "payload_issue_command_packet_created": True,
        "payload_issue_scheduler_dispatch_consumed": True,
        "command_packet_shape_checked": True,
        "command_packet_submitted": False,
        "command_packet_executed": False,
        "request_source": dispatch.request_source,
        "request_layer_idx": dispatch.request_layer_idx,
        "request_expert_idx": dispatch.request_expert_idx,
        "requested_payload_bytes": dispatch.requested_payload_bytes,
        "source_issue_packet_count": dispatch.source_issue_packet_count,
        "source_issue_unique_key_count": dispatch.source_issue_unique_key_count,
        "source_queue_budget_capacity": dispatch.source_queue_budget_capacity,
        "source_issue_lead_tokens": dispatch.source_issue_lead_tokens,
        "source_queue_deadline_us": dispatch.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCommandPacketDryRun(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("command_packet_submitted", "command_packet_executed"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCommandPacketDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCommandPacketDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="dispatch"):
        build_payload_cache_live_runtime_adapter_payload_issue_command_packet_dry_run(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary_consumes_packet() -> None:
    packet = _build_payload_issue_command_packet_dry_run()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary(
        packet,
    )

    assert canary.present is True
    assert canary.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_transport_enqueue_blocked_canary"
    )
    assert canary.status == f"blocked_by_payload_issue_command_packet_dry_run:{packet.status}"
    assert canary.consumes_payload_issue_command_packet_dry_run is True
    assert canary.payload_issue_command_packet_status == packet.status
    assert canary.payload_issue_transport_enqueue_schema == (
        "payload_cache_runtime_payload_issue_transport_enqueue_v1"
    )
    assert canary.payload_issue_transport_enqueue_canary_created is True
    assert canary.payload_issue_command_packet_consumed is True
    assert canary.transport_enqueue_checked is True
    assert canary.transport_enqueue_rejected is True
    assert canary.transport_enqueue_allowed is False
    assert canary.transport_work_enqueued is False
    assert canary.request_source == "queue_budget_first_model_passing_cell"
    assert canary.source_issue_packet_count == 28
    assert canary.source_issue_unique_key_count == 28
    assert canary.source_queue_budget_capacity == 4096
    assert canary.source_issue_lead_tokens == 8
    assert canary.planned_issue_count == 0
    assert canary.scheduled_issue_count == 0
    assert canary.queued_issue_count == 0
    assert canary.submitted_issue_count == 0
    assert canary.inflight_issue_count == 0
    assert canary.dispatched_issue_count == 0
    assert canary.command_packet_count == 0
    assert canary.transport_work_count == 0
    assert canary.issued_payload_count == 0
    assert canary.payload_bytes == 0
    assert canary.decision == "blocked"
    assert canary.block_reason == "payload_transfer_disabled"
    assert canary.ready_credit is False
    assert canary.kernel_arg_pass_allowed is False
    assert canary.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary_rejects_side_effects() -> None:
    packet = _build_payload_issue_command_packet_dry_run()
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_transport_enqueue_blocked_canary"
        ),
        "status": f"blocked_by_payload_issue_command_packet_dry_run:{packet.status}",
        "consumes_payload_issue_command_packet_dry_run": True,
        "payload_issue_command_packet_status": packet.status,
        "payload_issue_transport_enqueue_schema": (
            "payload_cache_runtime_payload_issue_transport_enqueue_v1"
        ),
        "payload_issue_transport_enqueue_canary_created": True,
        "payload_issue_command_packet_consumed": True,
        "transport_enqueue_checked": True,
        "transport_enqueue_rejected": True,
        "transport_enqueue_allowed": False,
        "transport_work_enqueued": False,
        "request_source": packet.request_source,
        "request_layer_idx": packet.request_layer_idx,
        "request_expert_idx": packet.request_expert_idx,
        "requested_payload_bytes": packet.requested_payload_bytes,
        "source_issue_packet_count": packet.source_issue_packet_count,
        "source_issue_unique_key_count": packet.source_issue_unique_key_count,
        "source_queue_budget_capacity": packet.source_queue_budget_capacity,
        "source_issue_lead_tokens": packet.source_issue_lead_tokens,
        "source_queue_deadline_us": packet.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueTransportEnqueueBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("transport_enqueue_allowed", "transport_work_enqueued"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueTransportEnqueueBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueTransportEnqueueBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="packet"):
        build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_transport_enqueue_builder_rejects_mutated_packet() -> None:
    packet = _build_payload_issue_command_packet_dry_run()

    object.__setattr__(packet, "command_packet_submitted", True)

    with pytest.raises(ValueError, match="command_packet_submitted"):
        build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary(
            packet,
        )

    packet = _build_payload_issue_command_packet_dry_run()
    object.__setattr__(packet, "payload_issue_scheduler_dispatch_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_transport_enqueue_blocked_canary(
            packet,
        )


def test_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary_consumes_enqueue() -> None:
    enqueue = _build_payload_issue_transport_enqueue_blocked_canary()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary(
        enqueue,
    )

    assert canary.present is True
    assert canary.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_transport_worker_dispatch_blocked_canary"
    )
    assert canary.status == (
        f"blocked_by_payload_issue_transport_enqueue_blocked_canary:{enqueue.status}"
    )
    assert canary.consumes_payload_issue_transport_enqueue_blocked_canary is True
    assert canary.payload_issue_transport_enqueue_status == enqueue.status
    assert canary.payload_issue_transport_worker_dispatch_schema == (
        "payload_cache_runtime_payload_issue_transport_worker_dispatch_v1"
    )
    assert canary.payload_issue_transport_worker_dispatch_canary_created is True
    assert canary.payload_issue_transport_enqueue_consumed is True
    assert canary.transport_worker_dispatch_checked is True
    assert canary.transport_worker_dispatch_rejected is True
    assert canary.transport_worker_dispatch_allowed is False
    assert canary.transport_worker_dispatched is False
    assert canary.source_issue_packet_count == 28
    assert canary.source_issue_unique_key_count == 28
    assert canary.source_queue_budget_capacity == 4096
    assert canary.source_issue_lead_tokens == 8
    assert canary.command_packet_count == 0
    assert canary.transport_work_count == 0
    assert canary.transport_worker_dispatch_count == 0
    assert canary.issued_payload_count == 0
    assert canary.payload_bytes == 0
    assert canary.ready_credit is False
    assert canary.kernel_arg_pass_allowed is False
    assert canary.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary_rejects_side_effects() -> None:
    enqueue = _build_payload_issue_transport_enqueue_blocked_canary()
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_transport_worker_dispatch_blocked_canary"
        ),
        "status": f"blocked_by_payload_issue_transport_enqueue_blocked_canary:{enqueue.status}",
        "consumes_payload_issue_transport_enqueue_blocked_canary": True,
        "payload_issue_transport_enqueue_status": enqueue.status,
        "payload_issue_transport_worker_dispatch_schema": (
            "payload_cache_runtime_payload_issue_transport_worker_dispatch_v1"
        ),
        "payload_issue_transport_worker_dispatch_canary_created": True,
        "payload_issue_transport_enqueue_consumed": True,
        "transport_worker_dispatch_checked": True,
        "transport_worker_dispatch_rejected": True,
        "transport_worker_dispatch_allowed": False,
        "transport_worker_dispatched": False,
        "request_source": enqueue.request_source,
        "request_layer_idx": enqueue.request_layer_idx,
        "request_expert_idx": enqueue.request_expert_idx,
        "requested_payload_bytes": enqueue.requested_payload_bytes,
        "source_issue_packet_count": enqueue.source_issue_packet_count,
        "source_issue_unique_key_count": enqueue.source_issue_unique_key_count,
        "source_queue_budget_capacity": enqueue.source_queue_budget_capacity,
        "source_issue_lead_tokens": enqueue.source_issue_lead_tokens,
        "source_queue_deadline_us": enqueue.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueTransportWorkerDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("transport_worker_dispatch_allowed", "transport_worker_dispatched"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueTransportWorkerDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueTransportWorkerDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="enqueue"):
        build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_transport_worker_dispatch_builder_rejects_mutated_enqueue() -> None:
    enqueue = _build_payload_issue_transport_enqueue_blocked_canary()

    object.__setattr__(enqueue, "transport_enqueue_allowed", True)

    with pytest.raises(ValueError, match="transport_enqueue_allowed"):
        build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary(
            enqueue,
        )

    enqueue = _build_payload_issue_transport_enqueue_blocked_canary()
    object.__setattr__(enqueue, "payload_issue_command_packet_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_transport_worker_dispatch_blocked_canary(
            enqueue,
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_dry_run_consumes_worker_dispatch() -> None:
    dispatch = _build_payload_issue_transport_worker_dispatch_blocked_canary()

    descriptor = build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run(
        dispatch,
    )

    assert descriptor.present is True
    assert descriptor.stage == "payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run"
    assert descriptor.status == (
        f"blocked_by_payload_issue_transport_worker_dispatch_blocked_canary:{dispatch.status}"
    )
    assert descriptor.consumes_payload_issue_transport_worker_dispatch_blocked_canary is True
    assert descriptor.payload_issue_transport_worker_dispatch_status == dispatch.status
    assert descriptor.payload_issue_copy_descriptor_schema == (
        "payload_cache_runtime_payload_issue_copy_descriptor_v1"
    )
    assert descriptor.payload_issue_copy_descriptor_created is True
    assert descriptor.payload_issue_transport_worker_dispatch_consumed is True
    assert descriptor.copy_descriptor_shape_checked is True
    assert descriptor.copy_descriptor_submitted is False
    assert descriptor.copy_descriptor_executed is False
    assert descriptor.source_issue_packet_count == 28
    assert descriptor.source_issue_unique_key_count == 28
    assert descriptor.source_queue_budget_capacity == 4096
    assert descriptor.source_issue_lead_tokens == 8
    assert descriptor.transport_work_count == 0
    assert descriptor.transport_worker_dispatch_count == 0
    assert descriptor.copy_descriptor_count == 0
    assert descriptor.issued_payload_count == 0
    assert descriptor.payload_bytes == 0
    assert descriptor.ready_credit is False
    assert descriptor.kernel_arg_pass_allowed is False
    assert descriptor.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_copy_descriptor_dry_run_rejects_side_effects() -> None:
    dispatch = _build_payload_issue_transport_worker_dispatch_blocked_canary()
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run",
        "status": (
            f"blocked_by_payload_issue_transport_worker_dispatch_blocked_canary:{dispatch.status}"
        ),
        "consumes_payload_issue_transport_worker_dispatch_blocked_canary": True,
        "payload_issue_transport_worker_dispatch_status": dispatch.status,
        "payload_issue_copy_descriptor_schema": (
            "payload_cache_runtime_payload_issue_copy_descriptor_v1"
        ),
        "payload_issue_copy_descriptor_created": True,
        "payload_issue_transport_worker_dispatch_consumed": True,
        "copy_descriptor_shape_checked": True,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "request_source": dispatch.request_source,
        "request_layer_idx": dispatch.request_layer_idx,
        "request_expert_idx": dispatch.request_expert_idx,
        "requested_payload_bytes": dispatch.requested_payload_bytes,
        "source_issue_packet_count": dispatch.source_issue_packet_count,
        "source_issue_unique_key_count": dispatch.source_issue_unique_key_count,
        "source_queue_budget_capacity": dispatch.source_queue_budget_capacity,
        "source_issue_lead_tokens": dispatch.source_issue_lead_tokens,
        "source_queue_deadline_us": dispatch.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "copy_descriptor_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDryRun(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in ("copy_descriptor_submitted", "copy_descriptor_executed"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDryRun(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="dispatch"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_builder_rejects_mutated_dispatch() -> None:
    dispatch = _build_payload_issue_transport_worker_dispatch_blocked_canary()

    object.__setattr__(dispatch, "transport_worker_dispatched", True)

    with pytest.raises(ValueError, match="transport_worker_dispatched"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run(
            dispatch,
        )

    dispatch = _build_payload_issue_transport_worker_dispatch_blocked_canary()
    object.__setattr__(dispatch, "payload_issue_transport_enqueue_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dry_run(
            dispatch,
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary_consumes_descriptor() -> None:
    descriptor = _build_payload_issue_copy_descriptor_dry_run()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary(
        descriptor,
    )

    assert canary.present is True
    assert canary.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_copy_descriptor_submit_blocked_canary"
    )
    assert canary.status == f"blocked_by_payload_issue_copy_descriptor_dry_run:{descriptor.status}"
    assert canary.consumes_payload_issue_copy_descriptor_dry_run is True
    assert canary.payload_issue_copy_descriptor_status == descriptor.status
    assert canary.payload_issue_copy_descriptor_submit_schema == (
        "payload_cache_runtime_payload_issue_copy_descriptor_submit_v1"
    )
    assert canary.payload_issue_copy_descriptor_submit_canary_created is True
    assert canary.payload_issue_copy_descriptor_consumed is True
    assert canary.copy_descriptor_submit_checked is True
    assert canary.copy_descriptor_submit_rejected is True
    assert canary.copy_descriptor_submit_allowed is False
    assert canary.copy_descriptor_submitted is False
    assert canary.copy_descriptor_executed is False
    assert canary.source_issue_packet_count == 28
    assert canary.source_issue_unique_key_count == 28
    assert canary.source_queue_budget_capacity == 4096
    assert canary.source_issue_lead_tokens == 8
    assert canary.copy_descriptor_count == 0
    assert canary.issued_payload_count == 0
    assert canary.payload_bytes == 0
    assert canary.ready_credit is False
    assert canary.kernel_arg_pass_allowed is False
    assert canary.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary_rejects_side_effects() -> None:
    descriptor = _build_payload_issue_copy_descriptor_dry_run()
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_copy_descriptor_submit_blocked_canary"
        ),
        "status": f"blocked_by_payload_issue_copy_descriptor_dry_run:{descriptor.status}",
        "consumes_payload_issue_copy_descriptor_dry_run": True,
        "payload_issue_copy_descriptor_status": descriptor.status,
        "payload_issue_copy_descriptor_submit_schema": (
            "payload_cache_runtime_payload_issue_copy_descriptor_submit_v1"
        ),
        "payload_issue_copy_descriptor_submit_canary_created": True,
        "payload_issue_copy_descriptor_consumed": True,
        "copy_descriptor_submit_checked": True,
        "copy_descriptor_submit_rejected": True,
        "copy_descriptor_submit_allowed": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "request_source": descriptor.request_source,
        "request_layer_idx": descriptor.request_layer_idx,
        "request_expert_idx": descriptor.request_expert_idx,
        "requested_payload_bytes": descriptor.requested_payload_bytes,
        "source_issue_packet_count": descriptor.source_issue_packet_count,
        "source_issue_unique_key_count": descriptor.source_issue_unique_key_count,
        "source_queue_budget_capacity": descriptor.source_queue_budget_capacity,
        "source_issue_lead_tokens": descriptor.source_issue_lead_tokens,
        "source_queue_deadline_us": descriptor.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "copy_descriptor_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorSubmitBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "copy_descriptor_submit_allowed",
        "copy_descriptor_submitted",
        "copy_descriptor_executed",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorSubmitBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorSubmitBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="descriptor"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_submit_builder_rejects_mutated_descriptor() -> None:
    descriptor = _build_payload_issue_copy_descriptor_dry_run()

    object.__setattr__(descriptor, "copy_descriptor_submitted", True)

    with pytest.raises(ValueError, match="copy_descriptor_submitted"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary(
            descriptor,
        )

    descriptor = _build_payload_issue_copy_descriptor_dry_run()
    object.__setattr__(descriptor, "payload_issue_transport_worker_dispatch_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_submit_blocked_canary(
            descriptor,
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary_consumes_submit() -> None:
    submit = _build_payload_issue_copy_descriptor_submit_blocked_canary()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary(
        submit,
    )

    assert canary.present is True
    assert canary.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_copy_descriptor_dispatch_blocked_canary"
    )
    assert canary.status == (
        f"blocked_by_payload_issue_copy_descriptor_submit_blocked_canary:{submit.status}"
    )
    assert canary.consumes_payload_issue_copy_descriptor_submit_blocked_canary is True
    assert canary.payload_issue_copy_descriptor_submit_status == submit.status
    assert canary.payload_issue_copy_descriptor_dispatch_schema == (
        "payload_cache_runtime_payload_issue_copy_descriptor_dispatch_v1"
    )
    assert canary.payload_issue_copy_descriptor_dispatch_canary_created is True
    assert canary.payload_issue_copy_descriptor_submit_consumed is True
    assert canary.copy_descriptor_dispatch_checked is True
    assert canary.copy_descriptor_dispatch_rejected is True
    assert canary.copy_descriptor_dispatch_allowed is False
    assert canary.copy_descriptor_dispatched is False
    assert canary.copy_descriptor_submitted is False
    assert canary.copy_descriptor_executed is False
    assert canary.source_issue_packet_count == 28
    assert canary.source_issue_unique_key_count == 28
    assert canary.source_queue_budget_capacity == 4096
    assert canary.source_issue_lead_tokens == 8
    assert canary.copy_descriptor_count == 0
    assert canary.issued_payload_count == 0
    assert canary.payload_bytes == 0
    assert canary.ready_credit is False
    assert canary.kernel_arg_pass_allowed is False
    assert canary.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary_rejects_side_effects() -> None:
    submit = _build_payload_issue_copy_descriptor_submit_blocked_canary()
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_copy_descriptor_dispatch_blocked_canary"
        ),
        "status": (
            f"blocked_by_payload_issue_copy_descriptor_submit_blocked_canary:{submit.status}"
        ),
        "consumes_payload_issue_copy_descriptor_submit_blocked_canary": True,
        "payload_issue_copy_descriptor_submit_status": submit.status,
        "payload_issue_copy_descriptor_dispatch_schema": (
            "payload_cache_runtime_payload_issue_copy_descriptor_dispatch_v1"
        ),
        "payload_issue_copy_descriptor_dispatch_canary_created": True,
        "payload_issue_copy_descriptor_submit_consumed": True,
        "copy_descriptor_dispatch_checked": True,
        "copy_descriptor_dispatch_rejected": True,
        "copy_descriptor_dispatch_allowed": False,
        "copy_descriptor_dispatched": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "request_source": submit.request_source,
        "request_layer_idx": submit.request_layer_idx,
        "request_expert_idx": submit.request_expert_idx,
        "requested_payload_bytes": submit.requested_payload_bytes,
        "source_issue_packet_count": submit.source_issue_packet_count,
        "source_issue_unique_key_count": submit.source_issue_unique_key_count,
        "source_queue_budget_capacity": submit.source_queue_budget_capacity,
        "source_issue_lead_tokens": submit.source_issue_lead_tokens,
        "source_queue_deadline_us": submit.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "copy_descriptor_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "copy_descriptor_dispatch_allowed",
        "copy_descriptor_dispatched",
        "copy_descriptor_submitted",
        "copy_descriptor_executed",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorDispatchBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="submit"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_builder_rejects_mutated_submit() -> None:
    submit = _build_payload_issue_copy_descriptor_submit_blocked_canary()

    object.__setattr__(submit, "copy_descriptor_submitted", True)

    with pytest.raises(ValueError, match="copy_descriptor_submitted"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary(
            submit,
        )

    submit = _build_payload_issue_copy_descriptor_submit_blocked_canary()
    object.__setattr__(submit, "payload_issue_copy_descriptor_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_dispatch_blocked_canary(
            submit,
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary_consumes_dispatch() -> None:
    dispatch = _build_payload_issue_copy_descriptor_dispatch_blocked_canary()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary(
        dispatch,
    )

    assert canary.present is True
    assert canary.stage == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_copy_descriptor_execution_blocked_canary"
    )
    assert canary.status == (
        f"blocked_by_payload_issue_copy_descriptor_dispatch_blocked_canary:{dispatch.status}"
    )
    assert canary.consumes_payload_issue_copy_descriptor_dispatch_blocked_canary is True
    assert canary.payload_issue_copy_descriptor_dispatch_status == dispatch.status
    assert canary.payload_issue_copy_descriptor_execution_schema == (
        "payload_cache_runtime_payload_issue_copy_descriptor_execution_v1"
    )
    assert canary.payload_issue_copy_descriptor_execution_canary_created is True
    assert canary.payload_issue_copy_descriptor_dispatch_consumed is True
    assert canary.copy_descriptor_execution_checked is True
    assert canary.copy_descriptor_execution_rejected is True
    assert canary.copy_descriptor_execution_allowed is False
    assert canary.copy_descriptor_dispatched is False
    assert canary.copy_descriptor_submitted is False
    assert canary.copy_descriptor_executed is False
    assert canary.source_issue_packet_count == 28
    assert canary.source_issue_unique_key_count == 28
    assert canary.source_queue_budget_capacity == 4096
    assert canary.source_issue_lead_tokens == 8
    assert canary.copy_descriptor_count == 0
    assert canary.issued_payload_count == 0
    assert canary.payload_bytes == 0
    assert canary.ready_credit is False
    assert canary.kernel_arg_pass_allowed is False
    assert canary.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary_rejects_side_effects() -> None:
    dispatch = _build_payload_issue_copy_descriptor_dispatch_blocked_canary()
    base_kwargs = {
        "present": True,
        "stage": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_copy_descriptor_execution_blocked_canary"
        ),
        "status": (
            f"blocked_by_payload_issue_copy_descriptor_dispatch_blocked_canary:{dispatch.status}"
        ),
        "consumes_payload_issue_copy_descriptor_dispatch_blocked_canary": True,
        "payload_issue_copy_descriptor_dispatch_status": dispatch.status,
        "payload_issue_copy_descriptor_execution_schema": (
            "payload_cache_runtime_payload_issue_copy_descriptor_execution_v1"
        ),
        "payload_issue_copy_descriptor_execution_canary_created": True,
        "payload_issue_copy_descriptor_dispatch_consumed": True,
        "copy_descriptor_execution_checked": True,
        "copy_descriptor_execution_rejected": True,
        "copy_descriptor_execution_allowed": False,
        "copy_descriptor_dispatched": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "request_source": dispatch.request_source,
        "request_layer_idx": dispatch.request_layer_idx,
        "request_expert_idx": dispatch.request_expert_idx,
        "requested_payload_bytes": dispatch.requested_payload_bytes,
        "source_issue_packet_count": dispatch.source_issue_packet_count,
        "source_issue_unique_key_count": dispatch.source_issue_unique_key_count,
        "source_queue_budget_capacity": dispatch.source_queue_budget_capacity,
        "source_issue_lead_tokens": dispatch.source_issue_lead_tokens,
        "source_queue_deadline_us": dispatch.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "copy_descriptor_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorExecutionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "copy_descriptor_execution_allowed",
        "copy_descriptor_dispatched",
        "copy_descriptor_submitted",
        "copy_descriptor_executed",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorExecutionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyDescriptorExecutionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="dispatch"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_copy_descriptor_execution_builder_rejects_mutated_dispatch() -> None:
    dispatch = _build_payload_issue_copy_descriptor_dispatch_blocked_canary()

    object.__setattr__(dispatch, "copy_descriptor_dispatched", True)

    with pytest.raises(ValueError, match="copy_descriptor_dispatched"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary(
            dispatch,
        )

    dispatch = _build_payload_issue_copy_descriptor_dispatch_blocked_canary()
    object.__setattr__(dispatch, "payload_issue_copy_descriptor_submit_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_descriptor_execution_blocked_canary(
            dispatch,
        )


def test_live_runtime_adapter_payload_issue_copy_completion_blocked_canary_consumes_execution() -> None:
    execution = _build_payload_issue_copy_descriptor_execution_blocked_canary()

    canary = build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary(
        execution,
    )

    assert canary.present is True
    assert canary.stage == (
        "payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary"
    )
    assert canary.status == (
        f"blocked_by_payload_issue_copy_descriptor_execution_blocked_canary:{execution.status}"
    )
    assert canary.consumes_payload_issue_copy_descriptor_execution_blocked_canary is True
    assert canary.payload_issue_copy_descriptor_execution_status == execution.status
    assert canary.payload_issue_copy_completion_schema == (
        "payload_cache_runtime_payload_issue_copy_completion_v1"
    )
    assert canary.payload_issue_copy_completion_canary_created is True
    assert canary.payload_issue_copy_descriptor_execution_consumed is True
    assert canary.copy_completion_checked is True
    assert canary.copy_completion_rejected is True
    assert canary.copy_completion_allowed is False
    assert canary.copy_completed is False
    assert canary.copy_descriptor_dispatched is False
    assert canary.copy_descriptor_submitted is False
    assert canary.copy_descriptor_executed is False
    assert canary.copy_descriptor_count == 0
    assert canary.copy_completion_count == 0
    assert canary.issued_payload_count == 0
    assert canary.payload_bytes == 0
    assert canary.ready_credit is False
    assert canary.real_ready_credit_granted is False
    assert canary.passed_to_kernel is False


def test_live_runtime_adapter_payload_issue_copy_completion_blocked_canary_rejects_side_effects() -> None:
    execution = _build_payload_issue_copy_descriptor_execution_blocked_canary()
    base_kwargs = {
        "present": True,
        "stage": "payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary",
        "status": (
            f"blocked_by_payload_issue_copy_descriptor_execution_blocked_canary:{execution.status}"
        ),
        "consumes_payload_issue_copy_descriptor_execution_blocked_canary": True,
        "payload_issue_copy_descriptor_execution_status": execution.status,
        "payload_issue_copy_completion_schema": (
            "payload_cache_runtime_payload_issue_copy_completion_v1"
        ),
        "payload_issue_copy_completion_canary_created": True,
        "payload_issue_copy_descriptor_execution_consumed": True,
        "copy_completion_checked": True,
        "copy_completion_rejected": True,
        "copy_completion_allowed": False,
        "copy_completed": False,
        "copy_descriptor_dispatched": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "request_source": execution.request_source,
        "request_layer_idx": execution.request_layer_idx,
        "request_expert_idx": execution.request_expert_idx,
        "requested_payload_bytes": execution.requested_payload_bytes,
        "source_issue_packet_count": execution.source_issue_packet_count,
        "source_issue_unique_key_count": execution.source_issue_unique_key_count,
        "source_queue_budget_capacity": execution.source_queue_budget_capacity,
        "source_issue_lead_tokens": execution.source_issue_lead_tokens,
        "source_queue_deadline_us": execution.source_queue_deadline_us,
    }

    for field_name in (
        "planned_issue_count",
        "scheduled_issue_count",
        "queued_issue_count",
        "submitted_issue_count",
        "inflight_issue_count",
        "dispatched_issue_count",
        "command_packet_count",
        "transport_work_count",
        "transport_worker_dispatch_count",
        "copy_descriptor_count",
        "copy_completion_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyCompletionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "copy_completion_allowed",
        "copy_completed",
        "copy_descriptor_dispatched",
        "copy_descriptor_submitted",
        "copy_descriptor_executed",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyCompletionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheLiveRuntimeAdapterPayloadIssueCopyCompletionBlockedCanary(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    with pytest.raises(TypeError, match="execution"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary(
            object(),  # type: ignore[arg-type]
        )


def test_live_runtime_adapter_payload_issue_copy_completion_builder_rejects_mutated_execution() -> None:
    execution = _build_payload_issue_copy_descriptor_execution_blocked_canary()

    object.__setattr__(execution, "copy_descriptor_executed", True)

    with pytest.raises(ValueError, match="copy_descriptor_executed"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary(
            execution,
        )

    execution = _build_payload_issue_copy_descriptor_execution_blocked_canary()
    object.__setattr__(execution, "payload_issue_copy_descriptor_dispatch_status", "stale")

    with pytest.raises(ValueError, match="ancestry"):
        build_payload_cache_live_runtime_adapter_payload_issue_copy_completion_blocked_canary(
            execution,
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
