from __future__ import annotations

from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
    aggregate_shadow_events,
    read_shadow_jsonl,
    write_shadow_jsonl,
)


def test_shadow_log_schema_round_trip_and_aggregate(tmp_path):
    event_id = ShadowEventId("req", sequence_id=0, token_index=7, layer=3)
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
        threshold_metadata_id="threshold-v1",
    )
    summary = ShadowSummaryEvent(
        event_id=event_id,
        policy=policy,
        transition_topk_count=32,
        mtp_requested_count=64,
        full_fetch_count=3,
        metadata_count=1,
        premap_count=1,
        skip_count=59,
        full_fetch_payload_bytes=4_950_000,
        metadata_actual_bytes=65_536,
        premap_actual_bytes=4_096,
        decision_us=12.5,
    )
    outcome = ShadowOutcomeEvent(
        event_id=event_id,
        true_topk_experts=[5, 7],
        true_topk_weights=[0.8, 0.2],
        full_fetch_used_count=2,
        metadata_later_used_count=1,
        premap_later_used_count=0,
        skip_would_have_used_count=1,
        covered_mass=0.8,
        miss_mass=0.2,
        top1_ready=True,
        weighted_top1_miss=0.0,
    )

    output = write_shadow_jsonl([summary, outcome], tmp_path / "shadow.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["shadow_event_id"] == "req:0:7:3"
    assert rows[0]["full_fetch_count"] == 3
    assert rows[1]["true_top1_expert"] == 5
    assert aggregate["summary_count"] == 1
    assert aggregate["outcome_count"] == 1
    assert aggregate["full_fetch_count"] == 3
    assert aggregate["metadata_count"] == 1
    assert aggregate["premap_count"] == 1
    assert aggregate["full_fetch_used_count"] == 2
    assert aggregate["metadata_later_used_count"] == 1
    assert aggregate["top1_ready_rate"] == 1.0
