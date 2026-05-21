from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    TileRequest,
    build_shadow_summary_from_descriptor_order,
    order_tile_request_stream,
)
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowDescriptorSummaryMinEvent,
    ShadowEventId,
    ShadowOutcomeAggregateEvent,
    ShadowOutcomeEvent,
    ShadowPolicyConfig,
    ShadowPremapConsumerMappingEvent,
    ShadowPremapSummaryEvent,
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
        descriptor_order_prior_id="prior-v1",
        descriptor_order_prior_hash="hash-v1",
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
        descriptor_order_prior_id="prior-v1",
        descriptor_order_prior_hash="hash-v1",
        descriptor_tile_multiset_hash="same-tiles",
        descriptor_order_hash="ordered-tiles",
        descriptor_order_metrics={"lru_hit_rate": {"8": 0.8}, "tile_order_hit_rate": 0.5},
        descriptor_tile_request_count=17,
        descriptor_unique_b_tiles=9,
        descriptor_same_multiset=True,
        descriptor_order_changed=True,
        descriptor_order_lru_at_8=0.8,
        descriptor_order_hit_rate=0.5,
        descriptor_reuse_distance_mean=3.0,
        descriptor_unique_tiles_per_window_mean=2.0,
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
    assert rows[0]["descriptor_order_prior_id"] == "prior-v1"
    assert rows[0]["descriptor_order_prior_hash"] == "hash-v1"
    assert rows[0]["descriptor_tile_multiset_hash"] == "same-tiles"
    assert rows[0]["descriptor_order_hash"] == "ordered-tiles"
    assert rows[0]["descriptor_order_metrics"]["lru_hit_rate"]["8"] == 0.8
    assert rows[0]["descriptor_tile_request_count"] == 17
    assert rows[0]["descriptor_unique_b_tiles"] == 9
    assert rows[0]["descriptor_same_multiset"] is True
    assert rows[0]["descriptor_order_changed"] is True
    assert rows[0]["descriptor_order_lru_at_8"] == 0.8
    assert rows[0]["descriptor_order_hit_rate"] == 0.5
    assert rows[0]["descriptor_reuse_distance_mean"] == 3.0
    assert rows[0]["descriptor_unique_tiles_per_window_mean"] == 2.0
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
    assert aggregate["descriptor_order_lru_at_8_mean"] == 0.8
    assert aggregate["descriptor_order_hit_rate_mean"] == 0.5
    assert aggregate["descriptor_reuse_distance_mean"] == 3.0
    assert aggregate["descriptor_unique_tiles_per_window_mean"] == 2.0
    assert aggregate["descriptor_tile_request_count"] == 17
    assert aggregate["descriptor_unique_b_tiles_mean"] == 9.0
    assert aggregate["descriptor_same_multiset_count"] == 1
    assert aggregate["descriptor_order_changed_count"] == 1


def test_shadow_log_aggregates_outcome_aggregate_events(tmp_path):
    event = ShadowOutcomeAggregateEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=10, layer=3),
        token_start=10,
        token_end=12,
        token_count=2,
        top_k=2,
        topk_entry_count=4,
        routed_expert_count=3,
        topk_weight_mass_sum=2.0,
        top1_weight_sum=1.4,
        top1_weight_mean=0.7,
    )

    output = write_shadow_jsonl([event], tmp_path / "aggregate_shadow.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["event_type"] == "outcome_aggregate"
    assert rows[0]["shadow_event_id"] == "req:0:10:3"
    assert aggregate["outcome_aggregate_count"] == 1
    assert aggregate["outcome_aggregate_token_count"] == 2
    assert aggregate["outcome_aggregate_topk_entry_count"] == 4
    assert aggregate["outcome_aggregate_routed_expert_count_sum"] == 3
    assert aggregate["outcome_aggregate_routed_expert_count_mean"] == 3.0
    assert aggregate["outcome_aggregate_topk_weight_mass_sum"] == 2.0
    assert aggregate["outcome_aggregate_top1_weight_sum"] == 1.4
    assert aggregate["outcome_aggregate_top1_weight_mean"] == 0.7


def test_shadow_log_aggregates_descriptor_summary_min_events(tmp_path):
    event = ShadowDescriptorSummaryMinEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=3),
        descriptor_order_policy="layer_prior_frequency",
        descriptor_order_prior_id="prior-v1",
        descriptor_order_prior_hash="hash-v1",
        descriptor_order_metrics_mode="count_only",
        descriptor_tile_request_count=16,
        descriptor_unique_b_tiles=4,
        descriptor_window_count=2,
        descriptor_order_execution_mode="two_level_group_plan",
        descriptor_group_plan_groups_per_cta=4,
        descriptor_group_plan_group_count=8,
        descriptor_group_plan_avg_group_size=2.0,
        descriptor_group_plan_p95_group_size=3.0,
        descriptor_group_plan_max_group_size=4,
        descriptor_group_plan_cta_count=2,
        descriptor_order_gate_allow=False,
        descriptor_order_gate_reason="same_multiset_missing",
        descriptor_order_gate_tile_elems=1024,
        descriptor_order_gate_device=1,
        descriptor_order_gate_evidence_found=False,
        descriptor_order_gate_checksum_delta=None,
        candidate_construction_us=1.0,
        descriptor_order_build_us=2.0,
        counter_update_us=3.0,
        decision_us=6.0,
    )

    output = write_shadow_jsonl([event], tmp_path / "descriptor_min_shadow.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["event_type"] == "descriptor_summary_min"
    assert rows[0]["descriptor_order_metrics_mode"] == "count_only"
    assert rows[0]["descriptor_order_execution_mode"] == "two_level_group_plan"
    assert rows[0]["descriptor_group_plan_group_count"] == 8
    assert rows[0]["descriptor_group_plan_cta_count"] == 2
    assert rows[0]["descriptor_order_gate_allow"] is False
    assert rows[0]["descriptor_order_gate_reason"] == "same_multiset_missing"
    assert rows[0]["descriptor_order_gate_tile_elems"] == 1024
    assert rows[0]["descriptor_order_gate_device"] == 1
    assert rows[0]["descriptor_order_gate_evidence_found"] is False
    assert "full_fetch_count" not in rows[0]
    assert aggregate["descriptor_summary_min_count"] == 1
    assert aggregate["descriptor_summary_full_count"] == 0
    assert aggregate["descriptor_order_summary_count"] == 1
    assert aggregate["descriptor_tile_request_count"] == 16
    assert aggregate["descriptor_unique_b_tiles_mean"] == 4.0
    assert aggregate["descriptor_window_count_mean"] == 2.0
    assert aggregate["descriptor_group_plan_group_count_mean"] == 8.0
    assert aggregate["descriptor_group_plan_avg_group_size_mean"] == 2.0
    assert aggregate["descriptor_group_plan_p95_group_size_mean"] == 3.0
    assert aggregate["descriptor_group_plan_max_group_size_max"] == 4
    assert aggregate["descriptor_group_plan_cta_count_mean"] == 2.0
    assert aggregate["descriptor_order_gate_allow_count"] == 0
    assert aggregate["descriptor_order_gate_evidence_found_count"] == 0
    assert aggregate["decision_summary_count"] == 1
    assert aggregate["decision_us_mean"] == 6.0
    assert aggregate["candidate_construction_us_mean"] == 1.0
    assert aggregate["counter_update_us_mean"] == 3.0


def test_shadow_log_aggregates_premap_summary_without_payload_or_order_effects(tmp_path):
    event = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=4, layer=2),
        premap_policy="premap_only",
        premap_mode="shadow_only",
        premap_source="mtp_extra_premap_gate",
        premap_descriptor_count=5,
        premap_unique_experts=3,
        premap_unique_layers=2,
        premap_unique_sample_layers=2,
        premap_actual_bytes=20_480,
        premap_descriptor_hash="desc-hash",
        premap_address_hash="addr-hash",
        premap_build_us=7.0,
        decision_us=8.0,
        candidate_construction_us=2.0,
        counter_update_us=1.0,
        logging_us=0.5,
    )

    output = write_shadow_jsonl([event], tmp_path / "premap_shadow.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["event_type"] == "premap_summary"
    assert rows[0]["policy_mode"] == "premap_shadow"
    assert rows[0]["optimization_goal"] == "descriptor_address_prep"
    assert rows[0]["premap_payload_bytes"] == 0
    assert rows[0]["premap_full_fetch_count"] == 0
    assert rows[0]["premap_metadata_count"] == 0
    assert rows[0]["premap_changes_router"] is False
    assert rows[0]["premap_changes_descriptor_order"] is False
    assert rows[0]["premap_ready_credit"] is False
    assert rows[0]["premap_descriptor_hash"] == "desc-hash"
    assert rows[0]["premap_address_hash"] == "addr-hash"
    assert "descriptor_order_policy" not in rows[0]
    assert "full_fetch_payload_bytes" not in rows[0]
    assert aggregate["premap_summary_count"] == 1
    assert aggregate["premap_summary_descriptor_count"] == 5
    assert aggregate["premap_summary_actual_bytes"] == 20_480
    assert aggregate["premap_summary_payload_bytes"] == 0
    assert aggregate["premap_summary_unique_experts_mean"] == 3.0
    assert aggregate["premap_summary_unique_layers_mean"] == 2.0
    assert aggregate["premap_summary_unique_sample_layers_mean"] == 2.0
    assert aggregate["premap_summary_build_us_mean"] == 7.0
    assert aggregate["premap_summary_payload_violation_count"] == 0
    assert aggregate["premap_summary_full_fetch_violation_count"] == 0
    assert aggregate["premap_summary_metadata_violation_count"] == 0
    assert aggregate["premap_summary_router_change_violation_count"] == 0
    assert aggregate["premap_summary_descriptor_order_change_violation_count"] == 0
    assert aggregate["premap_summary_ready_credit_violation_count"] == 0
    assert aggregate["descriptor_order_summary_count"] == 0
    assert aggregate["decision_summary_count"] == 1
    assert aggregate["decision_us_mean"] == 8.0
    assert aggregate["candidate_construction_us_mean"] == 2.0
    assert aggregate["counter_update_us_mean"] == 1.0
    assert aggregate["logging_us_mean"] == 0.5


def test_shadow_log_aggregates_premap_consumer_mapping_without_side_effects(tmp_path):
    event = ShadowPremapConsumerMappingEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=2),
        mapping_mode="noop_assertion",
        mapping_source="fused_moe_prepare_expert_assignment",
        address_namespace="expert_weight_descriptor",
        readonly_gate_required=True,
        readonly_gate_id="readonly-gate",
        readonly_gate_path="configs/runtime/readonly.yaml",
        readonly_gate_passed=True,
        consumer_expert_count=4,
        consumer_unique_expert_count=2,
        address_hit_count=2,
        address_miss_count=0,
        address_hit_rate=1.0,
        all_hit=True,
        parity_ok=True,
        consumer_key_hash="consumer-hash",
        descriptor_handle_hit_count=2,
        descriptor_handle_miss_count=0,
        descriptor_handle_hash="handle-hash",
        expected_descriptor_handle_hash="handle-hash",
        descriptor_handle_parity_ok=True,
        expected_prepare_plan_count=7,
        observed_prepare_plan_count=7,
        expected_prepare_record_count=11,
        observed_prepare_record_count=13,
        lookup_after_prepare=True,
        real_descriptor_handle_hit_count=2,
        real_descriptor_handle_miss_count=0,
        real_descriptor_handle_hash="real-handle-hash",
        real_descriptor_handle_available=True,
        real_descriptor_handle_source_hashes={
            "packed_weight": "packed-hash",
            "scale_metadata": "scale-hash",
        },
        real_descriptor_handle_source_hit_counts={
            "packed_weight": 2,
            "scale_metadata": 2,
            "aux_metadata": 0,
        },
        real_descriptor_handle_source_miss_counts={
            "packed_weight": 0,
            "scale_metadata": 0,
            "aux_metadata": 2,
        },
        real_descriptor_handle_miss_reason_counts={"no_handle_parts": 0},
        real_descriptor_handle_new_binding_count=1,
        real_descriptor_handle_reused_binding_count=1,
        real_descriptor_handle_binding_mismatch_count=0,
        real_descriptor_handle_for_address_miss_count=0,
        readonly_consumer_lookup_count=2,
        readonly_consumer_handle_hit_count=2,
        readonly_consumer_handle_miss_count=0,
        readonly_consumer_evicted_before_consume_count=0,
        readonly_consumer_stale_handle_count=0,
        readonly_consumer_handle_parity_ok=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_lookup_count=2,
        descriptor_prep_handle_count=2,
        descriptor_prep_missing_handle_count=0,
        descriptor_prep_descriptor_ptr_count=2,
        descriptor_prep_packed_weight_descriptor_count=2,
        descriptor_prep_scale_metadata_handle_count=2,
        descriptor_prep_handle_hash="prep-hash",
        descriptor_prep_execution_ok=True,
        expected_key_hash="consumer-hash",
        resident_address_count=4,
        lookup_us=3.5,
    )

    output = write_shadow_jsonl([event], tmp_path / "premap_consumer.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["event_type"] == "premap_consumer_mapping"
    assert rows[0]["policy_mode"] == "premap_shadow"
    assert rows[0]["premap_consumer_mapping_mode"] == "noop_assertion"
    assert rows[0]["premap_consumer_readonly_gate_required"] is True
    assert rows[0]["premap_consumer_readonly_gate_id"] == "readonly-gate"
    assert rows[0]["premap_consumer_readonly_gate_path"] == (
        "configs/runtime/readonly.yaml"
    )
    assert rows[0]["premap_consumer_readonly_gate_passed"] is True
    assert rows[0]["premap_consumer_payload_bytes"] == 0
    assert rows[0]["premap_consumer_changes_router"] is False
    assert rows[0]["premap_consumer_changes_descriptor_order"] is False
    assert rows[0]["premap_consumer_ready_credit"] is False
    assert aggregate["premap_consumer_mapping_count"] == 1
    assert aggregate["premap_consumer_address_hit_count"] == 2
    assert aggregate["premap_consumer_address_miss_count"] == 0
    assert aggregate["premap_consumer_address_hit_rate"] == 1.0
    assert aggregate["premap_consumer_descriptor_handle_hit_count"] == 2
    assert aggregate["premap_consumer_descriptor_handle_miss_count"] == 0
    assert aggregate["premap_consumer_descriptor_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_all_hit_rate"] == 1.0
    assert aggregate["premap_consumer_parity_ok_rate"] == 1.0
    assert aggregate["premap_consumer_descriptor_handle_parity_ok_rate"] == 1.0
    assert aggregate["premap_consumer_lookup_after_prepare_rate"] == 1.0
    assert aggregate["premap_consumer_real_descriptor_handle_hit_count"] == 2
    assert aggregate["premap_consumer_real_descriptor_handle_miss_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_real_descriptor_handle_available_rate"] == 1.0
    assert rows[0]["premap_consumer_real_descriptor_handle_source_hashes"] == {
        "packed_weight": "packed-hash",
        "scale_metadata": "scale-hash",
    }
    assert rows[0]["premap_consumer_real_descriptor_handle_source_hit_counts"] == {
        "packed_weight": 2,
        "scale_metadata": 2,
        "aux_metadata": 0,
    }
    assert rows[0]["premap_consumer_real_descriptor_handle_source_miss_counts"] == {
        "packed_weight": 0,
        "scale_metadata": 0,
        "aux_metadata": 2,
    }
    assert rows[0]["premap_consumer_real_descriptor_handle_miss_reason_counts"] == {
        "no_handle_parts": 0,
    }
    assert (
        aggregate[
            "premap_consumer_real_descriptor_handle_packed_weight_hit_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_real_descriptor_handle_scale_metadata_hit_count"
        ]
        == 2
    )
    assert (
        aggregate["premap_consumer_real_descriptor_handle_aux_metadata_miss_count"]
        == 2
    )
    assert aggregate["premap_consumer_real_descriptor_handle_no_handle_parts_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_expert_map_miss_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_new_binding_count"] == 1
    assert aggregate["premap_consumer_real_descriptor_handle_reused_binding_count"] == 1
    assert aggregate["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_for_address_miss_count"] == 0
    assert aggregate["premap_consumer_readonly_lookup_count"] == 2
    assert aggregate["premap_consumer_readonly_handle_hit_count"] == 2
    assert aggregate["premap_consumer_readonly_handle_miss_count"] == 0
    assert aggregate["premap_consumer_readonly_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_readonly_evicted_before_consume_count"] == 0
    assert aggregate["premap_consumer_readonly_evicted_before_consume_rate"] == 0.0
    assert aggregate["premap_consumer_readonly_stale_handle_count"] == 0
    assert aggregate["premap_consumer_readonly_stale_handle_rate"] == 0.0
    assert aggregate["premap_consumer_readonly_handle_parity_ok_rate"] == 1.0
    assert rows[0]["premap_consumer_descriptor_prep_execution_mode"] == (
        "readonly_descriptor_address_object"
    )
    assert rows[0]["premap_consumer_descriptor_prep_handle_hash"] == "prep-hash"
    assert aggregate["premap_consumer_descriptor_prep_lookup_count"] == 2
    assert aggregate["premap_consumer_descriptor_prep_attempted_count"] == 1
    assert aggregate["premap_consumer_descriptor_prep_executed_count"] == 1
    assert aggregate["premap_consumer_descriptor_prep_handle_count"] == 2
    assert aggregate["premap_consumer_descriptor_prep_missing_handle_count"] == 0
    assert aggregate["premap_consumer_descriptor_prep_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_descriptor_prep_descriptor_ptr_count"] == 2
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_packed_weight_descriptor_count"
        ]
        == 2
    )
    assert aggregate["premap_consumer_descriptor_prep_scale_metadata_handle_count"] == 2
    assert aggregate["premap_consumer_descriptor_prep_execution_ok_rate"] == 1.0
    assert (
        aggregate["premap_consumer_descriptor_prep_execution_ok_attempted_rate"]
        == 1.0
    )
    assert aggregate["premap_consumer_descriptor_prep_blocked_count"] == 0
    assert aggregate["premap_consumer_descriptor_prep_blocked_attempted_rate"] == 0.0
    assert aggregate["premap_consumer_lookup_us_mean"] == 3.5
    assert aggregate["premap_consumer_payload_violation_count"] == 0
    assert aggregate["premap_consumer_router_change_violation_count"] == 0
    assert aggregate["premap_consumer_descriptor_order_change_violation_count"] == 0
    assert aggregate["premap_consumer_ready_credit_violation_count"] == 0


def test_premap_consumer_readonly_gate_passed_false_is_serialized():
    event = ShadowPremapConsumerMappingEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=2),
        mapping_mode="noop_assertion",
        mapping_source="fused_moe_prepare_expert_assignment",
        address_namespace="expert_weight_descriptor",
        readonly_gate_required=True,
        readonly_gate_id="readonly-gate",
        readonly_gate_path="configs/runtime/readonly.yaml",
        readonly_gate_passed=False,
        consumer_expert_count=1,
        consumer_unique_expert_count=1,
        address_hit_count=0,
        address_miss_count=1,
        address_hit_rate=0.0,
        all_hit=False,
        parity_ok=False,
        consumer_key_hash="consumer-hash",
    )

    row = event.as_dict()

    assert row["premap_consumer_readonly_gate_required"] is True
    assert row["premap_consumer_readonly_gate_passed"] is False


def test_premap_consumer_readonly_gate_passed_none_is_omitted():
    event = ShadowPremapConsumerMappingEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=2),
        mapping_mode="noop_assertion",
        mapping_source="fused_moe_prepare_expert_assignment",
        address_namespace="expert_weight_descriptor",
        readonly_gate_required=False,
        readonly_gate_passed=None,
        consumer_expert_count=1,
        consumer_unique_expert_count=1,
        address_hit_count=0,
        address_miss_count=1,
        address_hit_rate=0.0,
        all_hit=False,
        parity_ok=False,
        consumer_key_hash="consumer-hash",
    )

    row = event.as_dict()

    assert row["premap_consumer_readonly_gate_required"] is False
    assert "premap_consumer_readonly_gate_passed" not in row


def test_shadow_log_aggregates_premap_address_manager_snapshot_deltas(tmp_path):
    first = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
        premap_policy="premap_only",
        premap_descriptor_count=2,
        premap_unique_experts=2,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=128,
        premap_descriptor_hash="desc-1",
        premap_address_hash="addr-1",
        premap_address_manager_capacity=4,
        premap_address_resident_count=2,
        premap_address_new_count=2,
        premap_address_reused_count=0,
        premap_address_evicted_count=0,
        premap_address_reuse_rate=0.0,
        premap_address_eviction_pressure=0.0,
        premap_address_resident_descriptor_bytes=128,
        premap_address_prepared_descriptor_actual_bytes=128,
    )
    second = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=1),
        premap_policy="premap_only",
        premap_descriptor_count=2,
        premap_unique_experts=2,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=128,
        premap_descriptor_hash="desc-2",
        premap_address_hash="addr-2",
        premap_address_manager_capacity=4,
        premap_address_resident_count=3,
        premap_address_new_count=3,
        premap_address_reused_count=1,
        premap_address_evicted_count=0,
        premap_address_reuse_rate=0.25,
        premap_address_eviction_pressure=0.0,
        premap_address_resident_descriptor_bytes=192,
        premap_address_prepared_descriptor_actual_bytes=256,
    )
    reset = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req2", sequence_id=1, token_index=-1, layer=0),
        premap_policy="premap_only",
        premap_descriptor_count=1,
        premap_unique_experts=1,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=64,
        premap_descriptor_hash="desc-3",
        premap_address_hash="addr-3",
        premap_address_manager_capacity=4,
        premap_address_resident_count=1,
        premap_address_new_count=1,
        premap_address_reused_count=0,
        premap_address_evicted_count=0,
        premap_address_reuse_rate=0.0,
        premap_address_eviction_pressure=0.0,
        premap_address_resident_descriptor_bytes=64,
        premap_address_prepared_descriptor_actual_bytes=64,
    )

    output = write_shadow_jsonl([first, second, reset], tmp_path / "premap_mgr.jsonl")
    aggregate = aggregate_shadow_events(read_shadow_jsonl(output))

    assert aggregate["premap_address_manager_count"] == 3
    assert aggregate["premap_address_new_count"] == 4
    assert aggregate["premap_address_reused_count"] == 1
    assert aggregate["premap_address_evicted_count"] == 0
    assert aggregate["premap_address_resident_count_max"] == 3
    assert aggregate["premap_address_resident_descriptor_bytes_max"] == 192
    assert aggregate["premap_address_prepared_descriptor_actual_bytes_max"] == 256
    assert aggregate["premap_address_reuse_rate_mean"] == (0.25 / 3)
    assert aggregate["premap_summary_payload_bytes"] == 0


def test_shadow_log_descriptor_summary_min_does_not_dilute_full_metrics(tmp_path):
    event_id = ShadowEventId("req", sequence_id=0, token_index=-1, layer=3)
    policy = ShadowPolicyConfig(
        policy_mode="descriptor_order_shadow",
        optimization_goal="cache_locality",
        action_keep_fraction=0.0,
        metadata_score_ratio=0.0,
        full_fetch_max_extra=0,
        metadata_max_extra=0,
        premap_max_extra=0,
        descriptor_order_policy="layer_prior_frequency",
        descriptor_order_prior_id="prior-v1",
        descriptor_order_prior_hash="hash-v1",
    )
    full = ShadowSummaryEvent(
        event_id=event_id,
        policy=policy,
        transition_topk_count=0,
        mtp_requested_count=0,
        full_fetch_count=0,
        metadata_count=0,
        premap_count=0,
        skip_count=0,
        full_fetch_payload_bytes=0,
        metadata_actual_bytes=0,
        premap_actual_bytes=0,
        decision_us=10.0,
        candidate_construction_us=2.0,
        counter_update_us=1.0,
        descriptor_order_build_us=4.0,
        descriptor_tile_request_count=8,
        descriptor_unique_b_tiles=4,
        descriptor_same_multiset=True,
        descriptor_order_changed=True,
        descriptor_order_lru_at_8=0.8,
        descriptor_order_lru_at_16=0.9,
        descriptor_order_hit_rate=0.5,
        descriptor_reuse_distance_mean=3.0,
        descriptor_unique_tiles_per_window_mean=2.0,
    )
    minimal = ShadowDescriptorSummaryMinEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=4),
        descriptor_order_policy="layer_prior_frequency",
        descriptor_order_prior_id="prior-v1",
        descriptor_order_prior_hash="hash-v1",
        descriptor_order_metrics_mode="count_only",
        descriptor_tile_request_count=16,
        descriptor_unique_b_tiles=8,
        descriptor_window_count=4,
        candidate_construction_us=4.0,
        descriptor_order_build_us=6.0,
        counter_update_us=3.0,
        decision_us=20.0,
    )

    output = write_shadow_jsonl([full, minimal], tmp_path / "mixed_descriptor.jsonl")
    aggregate = aggregate_shadow_events(read_shadow_jsonl(output))

    assert aggregate["summary_count"] == 1
    assert aggregate["descriptor_summary_full_count"] == 1
    assert aggregate["descriptor_summary_min_count"] == 1
    assert aggregate["descriptor_order_summary_count"] == 2
    assert aggregate["decision_summary_count"] == 2
    assert aggregate["decision_us_mean"] == 15.0
    assert aggregate["candidate_construction_us_mean"] == 3.0
    assert aggregate["counter_update_us_mean"] == 2.0
    assert aggregate["descriptor_order_build_us_mean"] == 5.0
    assert aggregate["descriptor_unique_b_tiles_mean"] == 6.0
    assert aggregate["descriptor_window_count_mean"] == 2.0
    assert aggregate["descriptor_order_lru_at_8_count"] == 1
    assert aggregate["descriptor_order_lru_at_8_mean"] == 0.8
    assert aggregate["descriptor_order_lru_at_16_mean"] == 0.9
    assert aggregate["descriptor_order_hit_rate_mean"] == 0.5
    assert aggregate["descriptor_reuse_distance_mean"] == 3.0
    assert aggregate["descriptor_unique_tiles_per_window_mean"] == 2.0


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
        descriptor_order_prior_id="prior-v2",
        descriptor_order_prior_hash="hash-v2",
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
        prior_id="prior-v2",
        prior_hash="hash-v2",
    )
    payload = summary.as_dict()

    assert payload["descriptor_order_policy"] == "utility_tile_grouped"
    assert payload["descriptor_order_prior_id"] == "prior-v2"
    assert payload["descriptor_order_prior_hash"] == "hash-v2"
    assert payload["descriptor_tile_request_count"] == 3
    assert payload["descriptor_unique_b_tiles"] == 2
    assert payload["descriptor_same_multiset"] is True
    assert payload["descriptor_order_changed"] is True
    assert payload["descriptor_order_lru_at_8"] == ordered.metrics["lru_hit_rate"]["8"]
    assert payload["descriptor_order_hit_rate"] == ordered.metrics["tile_order_hit_rate"]
    assert payload["full_fetch_count"] == 0
    assert payload["metadata_count"] == 0
    assert payload["premap_count"] == 0
