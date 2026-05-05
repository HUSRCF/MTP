import torch

from mtp_expert_prefetch.runtime import (
    AdmissionDecisionMasks,
    OnlineShadowLogger,
    RuntimeShadowController,
    build_shadow_summary_from_decisions,
)
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


def test_build_shadow_summary_from_decisions_counts_actions_and_reasons():
    shape = (1, 1, 1, 5)
    full_fetch = torch.zeros(shape, dtype=torch.bool)
    full_fetch[..., 1] = True
    metadata = torch.zeros(shape, dtype=torch.bool)
    metadata[..., 2] = True
    premap = torch.zeros(shape, dtype=torch.bool)
    premap[..., 3] = True
    skipped = torch.zeros(shape, dtype=torch.bool)
    skipped[..., 4] = True
    empty = torch.zeros(shape, dtype=torch.bool)
    decisions = AdmissionDecisionMasks(
        admitted_full_fetch=full_fetch,
        admitted_metadata=metadata,
        admitted_premap=premap,
        skipped_not_novel=empty,
        skipped_rank_cap=empty,
        skipped_below_threshold=skipped,
        skipped_invalid_score=empty,
        skipped_policy=empty,
    )
    event = build_shadow_summary_from_decisions(
        event_id=ShadowEventId("req", 0, 1, 2),
        policy=ShadowPolicyConfig(
            policy_mode="default",
            optimization_goal="stall_reduction",
            action_keep_fraction=0.5,
            metadata_score_ratio=0.95,
            full_fetch_max_extra=4,
            metadata_max_extra=1,
            premap_max_extra=1,
        ),
        decisions=decisions,
        decision_us=2.0,
    )
    payload = event.as_dict()

    assert payload["full_fetch_count"] == 1
    assert payload["metadata_count"] == 1
    assert payload["premap_count"] == 1
    assert payload["skip_count"] == 1
    assert payload["full_fetch_payload_bytes"] == 1_650_000
    assert payload["metadata_actual_bytes"] == 65_536
    assert payload["premap_actual_bytes"] == 4_096
    assert payload["reason_counts"]["admitted_score_gate"] == 1
    assert payload["reason_counts"]["admitted_metadata"] == 1
    assert payload["reason_counts"]["admitted_premap"] == 1
    assert payload["reason_counts"]["skipped_below_threshold"] == 1
    assert payload["action_reason_counts"]["admitted_score_gate"]["full_fetch"] == 1
    assert payload["action_reason_counts"]["skipped_below_threshold"]["skip"] == 1


def test_online_shadow_logger_write_action_summary_uses_adapter(tmp_path):
    shape = (1, 1, 1, 3)
    full_fetch = torch.zeros(shape, dtype=torch.bool)
    full_fetch[..., 1] = True
    empty = torch.zeros(shape, dtype=torch.bool)
    decisions = AdmissionDecisionMasks(
        admitted_full_fetch=full_fetch,
        admitted_metadata=empty,
        admitted_premap=empty,
        skipped_not_novel=empty,
        skipped_rank_cap=empty,
        skipped_below_threshold=empty,
        skipped_invalid_score=empty,
        skipped_policy=empty,
    )
    path = tmp_path / "summary_only.jsonl"

    with OnlineShadowLogger(path) as logger:
        event = logger.write_action_summary(
            event_id=ShadowEventId("req", 1, 2, 3),
            policy=ShadowPolicyConfig(
                policy_mode="default",
                optimization_goal="stall_reduction",
                action_keep_fraction=0.5,
                metadata_score_ratio=0.95,
                full_fetch_max_extra=4,
                metadata_max_extra=1,
                premap_max_extra=1,
            ),
            decisions=decisions,
            decision_us=3.0,
        )
        aggregate = logger.aggregate()

    assert event.full_fetch_count == 1
    assert aggregate["summary_count"] == 1
    assert aggregate["full_fetch_count"] == 1
    assert aggregate["decision_us_mean"] == 3.0


def test_runtime_shadow_controller_joins_action_summary_and_router_outcome(tmp_path):
    shape = (1, 1, 1, 6)
    full_fetch = torch.zeros(shape, dtype=torch.bool)
    full_fetch[..., 1] = True
    metadata = torch.zeros(shape, dtype=torch.bool)
    metadata[..., 2] = True
    premap = torch.zeros(shape, dtype=torch.bool)
    premap[..., 3] = True
    skipped = torch.zeros(shape, dtype=torch.bool)
    skipped[..., 4] = True
    empty = torch.zeros(shape, dtype=torch.bool)
    ready = torch.zeros(shape, dtype=torch.bool)
    ready[..., 0] = True
    ready[..., 1] = True
    decisions = AdmissionDecisionMasks(
        admitted_full_fetch=full_fetch,
        admitted_metadata=metadata,
        admitted_premap=premap,
        skipped_not_novel=empty,
        skipped_rank_cap=empty,
        skipped_below_threshold=skipped,
        skipped_invalid_score=empty,
        skipped_policy=empty,
    )
    event_id = ShadowEventId("req", 0, 7, 4)
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
    )
    path = tmp_path / "joined_shadow.jsonl"

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        controller.write_action_summary(
            event_id=event_id,
            policy=policy,
            decisions=decisions,
            ready_mask=ready,
        )
        controller.write_router_outcome(
            event_id=event_id,
            true_topk_experts=[1, 2, 4, 5],
            true_topk_weights=[0.6, 0.25, 0.1, 0.05],
        )
        aggregate = controller.aggregate()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["summary", "outcome"]
    outcome = rows[1]
    assert outcome["shadow_event_id"] == "req:0:7:4"
    assert outcome["full_fetch_used_count"] == 1
    assert outcome["metadata_later_used_count"] == 1
    assert outcome["premap_later_used_count"] == 0
    assert outcome["skip_would_have_used_count"] == 1
    assert outcome["covered_mass"] == 0.6
    assert outcome["miss_mass"] == 0.4
    assert outcome["top1_ready"] is True
    assert outcome["weighted_top1_miss"] == 0.0
    assert aggregate["summary_count"] == 1
    assert aggregate["outcome_count"] == 1
    assert aggregate["full_fetch_used_count"] == 1
    assert aggregate["metadata_later_used_count"] == 1
    assert aggregate["top1_ready_rate"] == 1.0


def test_runtime_shadow_controller_preserves_outcome_when_summary_missing(tmp_path):
    event_id = ShadowEventId("req", 0, 8, 5)
    path = tmp_path / "fallback_shadow.jsonl"
    event = ShadowOutcomeEvent(
        event_id=event_id,
        true_topk_experts=[3],
        true_topk_weights=[1.0],
        full_fetch_used_count=0,
        metadata_later_used_count=0,
        premap_later_used_count=0,
        skip_would_have_used_count=0,
        covered_mass=0.0,
        miss_mass=1.0,
        top1_ready=False,
        weighted_top1_miss=1.0,
    )

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        controller.write_outcome(event)

    rows = read_shadow_jsonl(path)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "outcome"
    assert rows[0]["shadow_event_id"] == "req:0:8:5"
    assert rows[0]["miss_mass"] == 1.0
