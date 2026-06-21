from __future__ import annotations

import pytest

from mtp_expert_prefetch.runtime import (
    CacheLabGateConfig,
    CacheLabGateDecision,
    CacheLabRuntimeSignals,
    PayloadCacheRuntimeParticipation,
    build_payload_cache_runtime_participation,
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
