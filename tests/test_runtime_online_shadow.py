from mtp_expert_prefetch.runtime import OnlineShadowLogger
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
    read_shadow_jsonl,
)


def test_online_shadow_logger_writes_and_aggregates_schema_events(tmp_path):
    event_id = ShadowEventId("req", 0, 3, 2)
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
        policy_reason="normal_envelope",
        allow_full_mtp_fetch=True,
        allow_mtp_metadata=True,
        allow_mtp_premap=True,
    )
    summary = ShadowSummaryEvent(
        event_id=event_id,
        policy=policy,
        transition_topk_count=32,
        mtp_requested_count=64,
        full_fetch_count=2,
        metadata_count=1,
        premap_count=1,
        skip_count=60,
        full_fetch_payload_bytes=3_300_000,
        metadata_actual_bytes=65_536,
        premap_actual_bytes=4_096,
        decision_us=1.5,
    )
    outcome = ShadowOutcomeEvent(
        event_id=event_id,
        true_topk_experts=[5, 7],
        true_topk_weights=[0.8, 0.2],
        full_fetch_used_count=1,
        metadata_later_used_count=1,
        premap_later_used_count=0,
        skip_would_have_used_count=0,
        covered_mass=0.8,
        miss_mass=0.2,
        top1_ready=True,
        weighted_top1_miss=0.0,
    )
    path = tmp_path / "online_shadow.jsonl"

    with OnlineShadowLogger(path, flush_every=2) as logger:
        logger.write_summary(summary)
        logger.write_outcome(outcome)
        aggregate = logger.aggregate()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["summary", "outcome"]
    assert rows[0]["shadow_event_id"] == "req:0:3:2"
    assert aggregate["summary_count"] == 1
    assert aggregate["outcome_count"] == 1
    assert aggregate["full_fetch_count"] == 2
    assert aggregate["metadata_later_used_count"] == 1
    assert aggregate["top1_ready_rate"] == 1.0
    assert aggregate["decision_us_mean"] == 1.5
