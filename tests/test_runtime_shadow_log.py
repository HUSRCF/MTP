from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    TileRequest,
    build_shadow_summary_from_descriptor_order,
    order_tile_request_stream,
)
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
        policy_reason="normal_envelope",
        allow_full_mtp_fetch=True,
        allow_mtp_metadata=True,
        allow_mtp_premap=True,
        descriptor_order_policy="utility_tile_grouped",
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
        candidate_construction_us=3.0,
        admission_decision_us=5.0,
        counter_update_us=2.0,
        logging_us=1.0,
        transition_ready_rate=0.95,
        mtp_ready_fraction=0.50,
        bandwidth_gbps=6.589,
        layer_ms=1.0,
        descriptor_order_build_us=4.0,
        descriptor_tile_multiset_hash="same-tiles",
        descriptor_order_hash="ordered-tiles",
        descriptor_order_metrics={"lru_hit_rate": {"8": 0.8}, "tile_order_hit_rate": 0.5},
        descriptor_tile_request_count=17,
        descriptor_unique_b_tiles=9,
        descriptor_same_multiset=True,
        descriptor_order_changed=True,
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
    assert rows[0]["policy_reason"] == "normal_envelope"
    assert rows[0]["allow_full_mtp_fetch"] is True
    assert rows[0]["descriptor_order_policy"] == "utility_tile_grouped"
    assert rows[0]["descriptor_tile_multiset_hash"] == "same-tiles"
    assert rows[0]["descriptor_order_hash"] == "ordered-tiles"
    assert rows[0]["descriptor_order_metrics"]["lru_hit_rate"]["8"] == 0.8
    assert rows[0]["descriptor_tile_request_count"] == 17
    assert rows[0]["descriptor_unique_b_tiles"] == 9
    assert rows[0]["descriptor_same_multiset"] is True
    assert rows[0]["descriptor_order_changed"] is True
    assert rows[0]["full_fetch_count"] == 3
    assert rows[0]["transition_ready_rate"] == 0.95
    assert rows[0]["mtp_ready_fraction"] == 0.50
    assert rows[0]["bandwidth_gbps"] == 6.589
    assert rows[1]["true_top1_expert"] == 5
    assert aggregate["summary_count"] == 1
    assert aggregate["outcome_count"] == 1
    assert aggregate["full_fetch_count"] == 3
    assert aggregate["metadata_count"] == 1
    assert aggregate["premap_count"] == 1
    assert aggregate["full_fetch_used_count"] == 2
    assert aggregate["metadata_later_used_count"] == 1
    assert aggregate["top1_ready_rate"] == 1.0
    assert aggregate["decision_us_mean"] == 12.5
    assert aggregate["candidate_construction_us_mean"] == 3.0
    assert aggregate["admission_decision_us_mean"] == 5.0
    assert aggregate["counter_update_us_mean"] == 2.0
    assert aggregate["logging_us_mean"] == 1.0
    assert aggregate["descriptor_order_build_us_mean"] == 4.0
    assert aggregate["descriptor_tile_request_count"] == 17
    assert aggregate["descriptor_unique_b_tiles_mean"] == 9.0
    assert aggregate["descriptor_same_multiset_count"] == 1
    assert aggregate["descriptor_order_changed_count"] == 1


def test_descriptor_order_shadow_summary_builder():
    event_id = ShadowEventId("req", sequence_id=0, token_index=1, layer=2)
    policy = ShadowPolicyConfig(
        policy_mode="descriptor_order_shadow",
        optimization_goal="cache_locality",
        action_keep_fraction=0.0,
        metadata_score_ratio=0.0,
        full_fetch_max_extra=0,
        metadata_max_extra=0,
        premap_max_extra=0,
        descriptor_order_policy="utility_tile_grouped",
    )
    requests = [
        TileRequest(0, 0, 1, 1, utility_score=0.1),
        TileRequest(0, 1, 2, 2, utility_score=0.9),
        TileRequest(0, 2, 1, 1, utility_score=0.2),
    ]
    _, linear = order_tile_request_stream(requests, policy="linear")
    _, ordered = order_tile_request_stream(requests, policy="utility_tile_grouped")

    summary = build_shadow_summary_from_descriptor_order(
        event_id=event_id,
        policy=policy,
        descriptor_report=ordered,
        baseline_order_hash=linear.order_hash,
    )
    payload = summary.as_dict()

    assert payload["descriptor_order_policy"] == "utility_tile_grouped"
    assert payload["descriptor_tile_request_count"] == 3
    assert payload["descriptor_unique_b_tiles"] == 2
    assert payload["descriptor_same_multiset"] is True
    assert payload["descriptor_order_changed"] is True
    assert payload["full_fetch_count"] == 0
    assert payload["metadata_count"] == 0
    assert payload["premap_count"] == 0
