from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    PrefetchPriority,
    RuntimeSignals,
    ScoreThresholdMetadata,
    priority_name,
    select_runtime_prefetch_policy,
)


def test_select_runtime_prefetch_policy_defaults_to_extra4():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.95,
            cache_pressure=0.70,
            queue_pressure=0.70,
            effective_capacity=144,
            mtp_delay_ms=2.0,
        )
    )

    assert policy.mode == "default"
    assert policy.max_extra == 4
    assert policy.tail_swap_count == 0
    assert policy.allow_full_mtp_fetch is True
    assert policy.reason == "normal_envelope"


def test_select_runtime_prefetch_policy_uses_high_budget_when_idle():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.98,
            cache_pressure=0.30,
            queue_pressure=0.20,
            effective_capacity=192,
            mtp_delay_ms=1.0,
        )
    )

    assert policy.mode == "high_budget"
    assert policy.max_extra == 8
    assert policy.tail_swap_count == 0
    assert policy.reason == "capacity_and_queue_idle"


def test_select_runtime_prefetch_policy_uses_extra2_for_bandwidth_efficiency():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.98,
            cache_pressure=0.30,
            queue_pressure=0.20,
            effective_capacity=192,
            mtp_delay_ms=1.0,
        ),
        optimization_goal="bandwidth_efficiency",
    )

    assert policy.mode == "low_budget"
    assert policy.max_extra == 2
    assert policy.tail_swap_count == 2
    assert policy.reason == "bandwidth_efficiency_extra2_tail_swap2"


def test_select_runtime_prefetch_policy_uses_extra1_for_bandwidth_efficiency_under_pressure():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.98,
            cache_pressure=0.84,
            queue_pressure=0.82,
            effective_capacity=192,
            mtp_delay_ms=1.0,
        ),
        optimization_goal="bandwidth_efficiency",
    )

    assert policy.mode == "low_budget"
    assert policy.max_extra == 1
    assert policy.tail_swap_count == 1
    assert policy.reason == "bandwidth_efficiency_extra1_tail_swap1"


def test_select_runtime_prefetch_policy_keeps_extra8_off_at_capacity_160():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.98,
            cache_pressure=0.30,
            queue_pressure=0.20,
            effective_capacity=160,
            mtp_delay_ms=1.0,
        )
    )

    assert policy.mode == "default"
    assert policy.max_extra == 4
    assert policy.reason == "normal_envelope"


def test_select_runtime_prefetch_policy_degrades_to_extra2_under_moderate_pressure():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.95,
            cache_pressure=0.84,
            queue_pressure=0.82,
            effective_capacity=144,
            mtp_delay_ms=2.0,
        )
    )

    assert policy.mode == "low_budget"
    assert policy.max_extra == 2
    assert policy.tail_swap_count == 2
    assert policy.allow_full_mtp_fetch is True
    assert policy.reason == "pressure_degraded_extra2_tail_swap2"


def test_select_runtime_prefetch_policy_degrades_to_extra1_under_high_pressure():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.95,
            cache_pressure=0.89,
            queue_pressure=0.86,
            effective_capacity=144,
            mtp_delay_ms=2.0,
        )
    )

    assert policy.mode == "low_budget"
    assert policy.max_extra == 1
    assert policy.tail_swap_count == 1
    assert policy.allow_full_mtp_fetch is True
    assert policy.reason == "pressure_degraded_extra1_tail_swap1"


def test_select_runtime_prefetch_policy_falls_back_under_extreme_pressure():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.95,
            cache_pressure=0.91,
            queue_pressure=0.20,
            effective_capacity=144,
            mtp_delay_ms=2.0,
        )
    )

    assert policy.mode == "fallback"
    assert policy.max_extra == 0
    assert policy.allow_full_mtp_fetch is False
    assert policy.reason == "resource_pressure"


def test_select_runtime_prefetch_policy_falls_back_when_transition_not_ready():
    policy = select_runtime_prefetch_policy(
        RuntimeSignals(
            transition_ready_rate=0.70,
            cache_pressure=0.10,
            queue_pressure=0.10,
            effective_capacity=192,
            mtp_delay_ms=0.0,
        )
    )

    assert policy.mode == "fallback"
    assert policy.max_extra == 0
    assert policy.allow_full_mtp_fetch is False
    assert policy.allow_mtp_metadata is True
    assert policy.reason == "transition_not_ready"


def test_priority_name_matches_runtime_tiers():
    assert priority_name(PrefetchPriority.TRANSITION_HEAD) == "transition_head"
    assert priority_name(4) == "mtp_extra_head"


def test_score_threshold_metadata_round_trips_to_dict():
    metadata = ScoreThresholdMetadata(
        threshold=0.5,
        threshold_type="calibrated_absolute",
        optimization_goal="stall_reduction",
        target_budget="extra4_equivalent",
        metric="stall_saved_ms_per_extra_issued_gb",
        calibration_split="samples_0_127",
        heldout_split="samples_128_255",
        prefc_fixed=True,
        base_policy="transition_top32",
        max_extra=4,
        score_source="mtp_token_top64_prior_score",
    )

    payload = metadata.as_dict()
    assert payload["threshold"] == 0.5
    assert payload["threshold_type"] == "calibrated_absolute"
    assert payload["target_budget"] == "extra4_equivalent"
    assert payload["schema_version"] == "score_threshold_metadata.v1"
    assert payload["prefc_fixed"] is True
    assert payload["base_policy"] == "transition_top32"
    assert payload["max_extra"] == 4
    assert payload["score_source"] == "mtp_token_top64_prior_score"
