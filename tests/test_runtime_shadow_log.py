from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
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
    ShadowPremapPayloadCacheManagerEvent,
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
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_checked_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode"
        ]
        == ""
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode_missing_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode_mismatch_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count_max"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count_min"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash"
        ]
        == ""
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash"
        ]
        == ""
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_count"
        ]
        == 0
    )
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
        descriptor_prep_real_handle_count=2,
        descriptor_prep_real_handle_miss_count=0,
        descriptor_prep_real_handle_backed=True,
        descriptor_prep_real_handle_hash="prep-real-hash",
        descriptor_prep_handle_hash="prep-hash",
        descriptor_prep_consumer_object_count=2,
        descriptor_prep_consumer_object_hash="prep-consumer-object-hash",
        descriptor_prep_consumer_object_read_lookup_count=2,
        descriptor_prep_consumer_object_read_hit_count=2,
        descriptor_prep_consumer_object_read_miss_count=0,
        descriptor_prep_consumer_object_stale_count=0,
        descriptor_prep_consumer_object_read_hash="prep-consumer-object-hash",
        descriptor_prep_consumer_object_read_ok=True,
        descriptor_prep_consumer_shim_mode="readonly_prelaunch_consumer_shim",
        descriptor_prep_consumer_shim_object_count=2,
        descriptor_prep_consumer_shim_object_hash="prep-consumer-object-hash",
        descriptor_prep_consumer_shim_handle_table_row_count=2,
        descriptor_prep_consumer_shim_handle_table_column_count=4,
        descriptor_prep_consumer_shim_handle_table_schema_hash="schema-hash",
        descriptor_prep_consumer_shim_handle_table_read_ok=True,
        descriptor_prep_consumer_shim_handle_table_lifecycle_ok=True,
        descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count=2,
        descriptor_prep_consumer_shim_handle_table_row_miss_count=0,
        descriptor_prep_consumer_shim_handle_table_stale_row_count=0,
        descriptor_prep_consumer_shim_handle_table_passed_to_kernel=False,
        descriptor_prep_consumer_shim_handle_table_payload_bytes=0,
        descriptor_prep_consumer_shim_handle_table_consume_ok=True,
        descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok=True,
        descriptor_prep_consumer_shim_handle_table_consume_row_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_column_count=4,
        descriptor_prep_consumer_shim_handle_table_consume_schema_hash="schema-hash",
        descriptor_prep_consumer_shim_handle_table_consume_mode=(
            "readonly_consume_kernel_arg_shadow_table"
        ),
        descriptor_prep_consumer_shim_handle_table_consume_source=(
            "canonical_address_key_order"
        ),
        descriptor_prep_consumer_shim_handle_table_consume_row_order_hash=(
            "row-order-hash"
        ),
        descriptor_prep_consumer_shim_handle_table_consume_ordered_row_hash=(
            "ordered-row-hash"
        ),
        descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_row_miss_count=0,
        descriptor_prep_consumer_shim_handle_table_consume_stale_row_count=0,
        descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count=8,
        descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count=6,
        descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count=0,
        descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count=2,
        descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count=0,
        descriptor_prep_consumer_shim_handle_table_consume_source_hit_counts={
            "descriptor_ptr": 2,
            "packed_weight_descriptor": 2,
            "scale_metadata_handle": 2,
            "aux_metadata_handle": 0,
        },
        descriptor_prep_consumer_shim_handle_table_consume_source_miss_counts={
            "descriptor_ptr": 0,
            "packed_weight_descriptor": 0,
            "scale_metadata_handle": 0,
            "aux_metadata_handle": 2,
        },
        descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel=False,
        descriptor_prep_consumer_shim_handle_table_consume_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode=(
            "readonly_kernel_arg_handoff_dry_run"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count=4,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count=6,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode=(
            "readonly_kernel_arg_handoff_shadow_slot"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash="slot-hash",
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count=4,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count=6,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode=(
            "readonly_kernel_arg_handoff_mirror"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash="mirror-hash",
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash="slot-hash",
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count=4,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count=6,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode=(
            "readonly_kernel_arg_handoff_launch_schema_mirror"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash=(
            "launch-mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash=(
            "mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash=(
            "slot-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count=4,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name=(
            PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash=(
            PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count=len(
            PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count=6,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count=8,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode=(
            "readonly_kernel_arg_semantic_handle_adapter"
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash=(
            "semantic-adapter-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash=(
            "launch-mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_row_count=2,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count=4,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name=(
            PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash=(
            PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_field_count=len(
            PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS
        ),
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_hit_count=6,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_miss_count=0,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_hit_count=0,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_miss_count=2,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_handle_field_read_count=8,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args=False,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mode=(
            "readonly_single_field_handle_handoff_canary"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready=True,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_hash=(
            "single-field-canary-hash"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_name=(
            "scale_metadata_handle"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_source=(
            "semantic_handle_table"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_mode=(
            "readonly_scale_metadata_handle_mirror"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_ready=True,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_field_name=(
            "scale_metadata_handle"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_source=(
            "semantic_handle_table"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_table_object_hash=(
            "table-hash"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_adapter_hash=(
            "semantic-hash"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_row_count=2,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_count=2,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_nonzero_count=2,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_zero_count=0,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_hash=(
            "scale-field-hash"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_semantic_field_hash=(
            "scale-field-hash"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_handle_hash=(
            "scale-field-hash"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_schema_hash=(
            PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_ok_count=2,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_mismatch_count=0,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible=True,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_current_wna16_arg_compatible=False,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_enabled=False,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_blocked=True,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_block_reason=(
            "single_field_handoff_live_disabled"
        ),
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_payload_bytes=0,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready_credit=False,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_passed_to_kernel=False,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_compatible_with_current_wna16_args=False,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode=(
            "readonly_kernel_side_consumer_schema_adapter"
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_ready=True,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash=(
            "kernel-side-adapter-hash"
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash=(
            "semantic-adapter-hash"
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_launch_schema_mirror_hash=(
            "launch-mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_row_count=2,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count=4,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_schema_hash=(
            PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name=(
            PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash=(
            PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_field_count=len(
            PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_hit_count=6,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_miss_count=0,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_hit_count=0,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_optional_source_miss_count=2,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_handle_field_read_count=8,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_schema_present=True,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected=False,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled=False,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_eligible=False,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_blocked=True,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason=(
            "kernel_side_consumer_live_disabled"
        ),
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode=(
            "readonly_kernel_arg_handoff_attempt"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash="attempt-hash",
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash=(
            "mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash="slot-hash",
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count=2,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count=4,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason=(
            "kernel_arg_handoff_disabled_noop_gate"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode=(
            "readonly_kernel_arg_handoff_live_toggle"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash="live-hash",
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash=(
            "attempt-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_live_disabled"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode=(
            "readonly_kernel_arg_handoff_live_noop_integration"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash=(
            "live-noop-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash=(
            "live-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash=(
            "launch-mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason=(
            "kernel_arg_handoff_live_disabled"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode=(
            "readonly_kernel_arg_handoff_live_consumer_adapter"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash=(
            "live-adapter-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash=(
            "live-noop-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash=(
            "launch-mirror-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason=(
            "kernel_arg_handoff_live_disabled"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked=True,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason=(
            "kernel_arg_handoff_live_disabled"
        ),
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes=0,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel=False,
        descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_mode=(
            "readonly_native_typed_consumer_bridge_check"
        ),
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_checked=True,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_ok=True,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_input_hash=(
            "native-input-hash"
        ),
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_row_count=2,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_column_count=4,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_nonzero_count=6,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_zero_count=0,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_nonzero_count=0,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_optional_handle_zero_count=2,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_valid_count=2,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_expert_id_invalid_count=0,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_nonzero_count=2,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_address_key_hash_zero_count=0,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_failure_count=0,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_failures=(),
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_payload_bytes=0,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_ready_credit=False,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_router=False,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_descriptor_order=False,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_passed_to_kernel=False,
        descriptor_prep_consumer_shim_native_typed_consumer_bridge_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_native_stub_online_invocation_mode=(
            "readonly_native_stub_online_invocation_canary"
        ),
        descriptor_prep_consumer_shim_native_stub_online_invocation_checked=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_ready=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_ok=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_native_checker_invoked=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_native_bridge_ok=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_package_hash=(
            "native-stub-package-hash"
        ),
        descriptor_prep_consumer_shim_native_stub_online_invocation_input_hash=(
            "native-input-hash"
        ),
        descriptor_prep_consumer_shim_native_stub_online_invocation_table_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_native_stub_online_invocation_schema_hash=(
            PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
        ),
        descriptor_prep_consumer_shim_native_stub_online_invocation_row_count=2,
        descriptor_prep_consumer_shim_native_stub_online_invocation_column_count=4,
        descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_nonzero_count=6,
        descriptor_prep_consumer_shim_native_stub_online_invocation_required_handle_zero_count=0,
        descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_nonzero_count=0,
        descriptor_prep_consumer_shim_native_stub_online_invocation_optional_handle_zero_count=2,
        descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_valid_count=2,
        descriptor_prep_consumer_shim_native_stub_online_invocation_expert_id_invalid_count=0,
        descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_nonzero_count=2,
        descriptor_prep_consumer_shim_native_stub_online_invocation_address_key_hash_zero_count=0,
        descriptor_prep_consumer_shim_native_stub_online_invocation_requested=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_native_stub_invoked=False,
        descriptor_prep_consumer_shim_native_stub_online_invocation_blocked=True,
        descriptor_prep_consumer_shim_native_stub_online_invocation_block_reason=(
            "native_stub_live_disabled"
        ),
        descriptor_prep_consumer_shim_native_stub_online_invocation_failure_count=0,
        descriptor_prep_consumer_shim_native_stub_online_invocation_failures=(),
        descriptor_prep_consumer_shim_native_stub_online_invocation_payload_bytes=0,
        descriptor_prep_consumer_shim_native_stub_online_invocation_ready_credit=False,
        descriptor_prep_consumer_shim_native_stub_online_invocation_changes_router=False,
        descriptor_prep_consumer_shim_native_stub_online_invocation_changes_descriptor_order=False,
        descriptor_prep_consumer_shim_native_stub_online_invocation_passed_to_kernel=False,
        descriptor_prep_consumer_shim_native_stub_online_invocation_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_prep_execution_dry_run_mode=(
            "readonly_descriptor_address_prep_execution_dry_run"
        ),
        descriptor_prep_consumer_shim_prep_execution_dry_run_source=(
            "kernel_arg_shadow_table_object"
        ),
        descriptor_prep_consumer_shim_prep_execution_dry_run_ok=True,
        descriptor_prep_consumer_shim_prep_execution_dry_run_row_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_column_count=4,
        descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash="schema-hash",
        descriptor_prep_consumer_shim_prep_execution_dry_run_object_hash=(
            "table-object-hash"
        ),
        descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok=True,
        descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count=0,
        descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count=8,
        descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count=6,
        descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count=0,
        descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count=2,
        descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count=0,
        descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel=False,
        descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes=0,
        descriptor_prep_consumer_shim_ok=True,
        descriptor_prep_consumer_shim_changes_kernel_launch_args=False,
        descriptor_prep_kernel_arg_shadow_table_mode=(
            "readonly_kernel_arg_shadow_table"
        ),
        descriptor_prep_kernel_arg_shadow_table_row_order_source=(
            "canonical_address_key_order"
        ),
        descriptor_prep_kernel_arg_shadow_table_row_count=2,
        descriptor_prep_kernel_arg_shadow_table_column_count=4,
        descriptor_prep_kernel_arg_shadow_table_schema_hash="kernel-schema-hash",
        descriptor_prep_kernel_arg_shadow_table_row_order_hash="row-order-hash",
        descriptor_prep_kernel_arg_shadow_table_ordered_row_hash="ordered-row-hash",
        descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count=2,
        descriptor_prep_kernel_arg_shadow_table_row_miss_count=0,
        descriptor_prep_kernel_arg_shadow_table_stale_row_count=0,
        descriptor_prep_kernel_arg_shadow_table_lifecycle_ok=True,
        descriptor_prep_kernel_arg_shadow_table_ok=True,
        descriptor_prep_kernel_arg_shadow_table_payload_bytes=0,
        descriptor_prep_kernel_arg_shadow_table_ready_credit=False,
        descriptor_prep_kernel_arg_shadow_table_changes_router=False,
        descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order=False,
        descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args=False,
        descriptor_prep_kernel_arg_shadow_table_passed_to_kernel=False,
        prelaunch_boundary_source="fused_moe_prepare_expert_assignment",
        prelaunch_handle_available=True,
        prelaunch_block_count=2,
        prelaunch_block_size=16,
        prelaunch_expert_order_hash="prelaunch-order-hash",
        prelaunch_expert_multiset_hash="prelaunch-multiset-hash",
        prelaunch_unique_expert_count=2,
        prelaunch_boundary_aligned=True,
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
    assert rows[0]["premap_consumer_prelaunch_boundary_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert rows[0]["premap_consumer_prelaunch_handle_available"] is True
    assert rows[0]["premap_consumer_prelaunch_block_count"] == 2
    assert rows[0]["premap_consumer_prelaunch_block_size"] == 16
    assert rows[0]["premap_consumer_prelaunch_boundary_aligned"] is True
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
    assert aggregate["premap_consumer_prelaunch_boundary_checked_count"] == 1
    assert aggregate["premap_consumer_prelaunch_boundary_aligned_count"] == 1
    assert aggregate["premap_consumer_prelaunch_boundary_aligned_rate"] == 1.0
    assert aggregate["premap_consumer_prelaunch_handle_available_count"] == 1
    assert aggregate["premap_consumer_prelaunch_handle_available_rate"] == 1.0
    assert aggregate["premap_consumer_prelaunch_block_count"] == 2
    assert aggregate["premap_consumer_prelaunch_block_size_max"] == 16
    assert aggregate["premap_consumer_prelaunch_unique_expert_count"] == 2
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
    assert (
        rows[0]["premap_consumer_descriptor_prep_real_handle_hash"]
        == "prep-real-hash"
    )
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
    assert aggregate["premap_consumer_descriptor_prep_real_handle_count"] == 2
    assert aggregate["premap_consumer_descriptor_prep_real_handle_miss_count"] == 0
    assert aggregate["premap_consumer_descriptor_prep_real_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_descriptor_prep_real_handle_backed_count"] == 1
    assert aggregate["premap_consumer_descriptor_prep_real_handle_backed_rate"] == 1.0
    assert aggregate["premap_consumer_descriptor_prep_consumer_object_count"] == 2
    assert aggregate["premap_consumer_descriptor_prep_consumer_object_rate"] == 1.0
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_object_read_lookup_count"
        ]
        == 2
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_object_read_hit_count"]
        == 2
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_object_read_miss_count"]
        == 0
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_object_stale_count"]
        == 0
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_object_read_hit_rate"]
        == 1.0
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_object_stale_rate"]
        == 0.0
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_object_read_ok_rate"]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_executed_count"
        ]
        == 1
    )
    assert aggregate["premap_consumer_descriptor_prep_consumer_shim_ok_count"] == 1
    assert aggregate["premap_consumer_descriptor_prep_consumer_shim_ok_rate"] == 1.0
    assert (
        aggregate["premap_consumer_descriptor_prep_consumer_shim_object_count"]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate"
        ]
        == 0.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
        ]
        == "schema-hash"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
        ]
        == "readonly_consume_kernel_arg_shadow_table"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
        ]
        == "canonical_address_key_order"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
        ]
        == 8
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_hit_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_hit_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_miss_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count"
        ]
        == 0
    )
    native_bridge_prefix = (
        "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge"
    )
    assert rows[0][f"{native_bridge_prefix}_mode"] == (
        "readonly_native_typed_consumer_bridge_check"
    )
    assert aggregate[f"{native_bridge_prefix}_checked_count"] == 1
    assert aggregate[f"{native_bridge_prefix}_ok_count"] == 1
    assert aggregate[f"{native_bridge_prefix}_mode"] == (
        "readonly_native_typed_consumer_bridge_check"
    )
    assert aggregate[f"{native_bridge_prefix}_input_hash_checked_count"] == 1
    assert aggregate[f"{native_bridge_prefix}_table_object_hash_checked_count"] == 1
    assert (
        aggregate[f"{native_bridge_prefix}_schema_hash"]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert aggregate[f"{native_bridge_prefix}_schema_hash_mismatch_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_row_count"] == 2
    assert aggregate[f"{native_bridge_prefix}_column_count_max"] == 4
    assert aggregate[f"{native_bridge_prefix}_required_handle_nonzero_count"] == 6
    assert aggregate[f"{native_bridge_prefix}_required_handle_zero_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_optional_handle_nonzero_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_optional_handle_zero_count"] == 2
    assert aggregate[f"{native_bridge_prefix}_expert_id_valid_count"] == 2
    assert aggregate[f"{native_bridge_prefix}_expert_id_invalid_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_address_key_hash_nonzero_count"] == 2
    assert aggregate[f"{native_bridge_prefix}_address_key_hash_zero_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_failure_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_payload_bytes"] == 0
    assert aggregate[f"{native_bridge_prefix}_payload_violation_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_ready_credit_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_changes_router_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_changes_descriptor_order_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_passed_to_kernel_count"] == 0
    assert aggregate[f"{native_bridge_prefix}_kernel_arg_violation_count"] == 0
    native_stub_prefix = (
        "premap_consumer_descriptor_prep_consumer_shim_native_stub_online_invocation"
    )
    assert rows[0][f"{native_stub_prefix}_mode"] == (
        "readonly_native_stub_online_invocation_canary"
    )
    assert aggregate[f"{native_stub_prefix}_checked_count"] == 1
    assert aggregate[f"{native_stub_prefix}_ready_count"] == 1
    assert aggregate[f"{native_stub_prefix}_ok_count"] == 1
    assert aggregate[f"{native_stub_prefix}_mode"] == (
        "readonly_native_stub_online_invocation_canary"
    )
    assert aggregate[f"{native_stub_prefix}_package_hash_checked_count"] == 1
    assert aggregate[f"{native_stub_prefix}_input_hash_checked_count"] == 1
    assert aggregate[f"{native_stub_prefix}_table_object_hash_checked_count"] == 1
    assert (
        aggregate[f"{native_stub_prefix}_schema_hash"]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert aggregate[f"{native_stub_prefix}_schema_hash_mismatch_count"] == 0
    assert aggregate[f"{native_stub_prefix}_block_reason"] == (
        "native_stub_live_disabled"
    )
    assert aggregate[f"{native_stub_prefix}_block_reason_mismatch_count"] == 0
    assert aggregate[f"{native_stub_prefix}_row_count"] == 2
    assert aggregate[f"{native_stub_prefix}_column_count_max"] == 4
    assert aggregate[f"{native_stub_prefix}_required_handle_nonzero_count"] == 6
    assert aggregate[f"{native_stub_prefix}_required_handle_zero_count"] == 0
    assert aggregate[f"{native_stub_prefix}_optional_handle_nonzero_count"] == 0
    assert aggregate[f"{native_stub_prefix}_optional_handle_zero_count"] == 2
    assert aggregate[f"{native_stub_prefix}_expert_id_valid_count"] == 2
    assert aggregate[f"{native_stub_prefix}_expert_id_invalid_count"] == 0
    assert aggregate[f"{native_stub_prefix}_address_key_hash_nonzero_count"] == 2
    assert aggregate[f"{native_stub_prefix}_address_key_hash_zero_count"] == 0
    assert aggregate[f"{native_stub_prefix}_native_checker_invoked_count"] == 1
    assert aggregate[f"{native_stub_prefix}_native_bridge_ok_count"] == 1
    assert aggregate[f"{native_stub_prefix}_requested_count"] == 1
    assert aggregate[f"{native_stub_prefix}_native_stub_invoked_count"] == 0
    assert aggregate[f"{native_stub_prefix}_blocked_count"] == 1
    assert aggregate[f"{native_stub_prefix}_failure_count"] == 0
    assert aggregate[f"{native_stub_prefix}_payload_bytes"] == 0
    assert aggregate[f"{native_stub_prefix}_payload_violation_count"] == 0
    assert aggregate[f"{native_stub_prefix}_ready_credit_count"] == 0
    assert aggregate[f"{native_stub_prefix}_changes_router_count"] == 0
    assert aggregate[f"{native_stub_prefix}_changes_descriptor_order_count"] == 0
    assert aggregate[f"{native_stub_prefix}_passed_to_kernel_count"] == 0
    assert aggregate[f"{native_stub_prefix}_kernel_arg_violation_count"] == 0
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
        ]
        == "readonly_kernel_arg_handoff_dry_run"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
        ]
        == "readonly_kernel_arg_handoff_shadow_slot"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
        ]
        == "readonly_kernel_arg_handoff_mirror"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode"
        ]
        == "readonly_kernel_arg_handoff_launch_schema_mirror"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name"
        ]
        == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash"
        ]
        == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count"
        ]
        == len(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS)
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count"
        ]
        == 8
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_object_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_mode"
        ]
        == "readonly_kernel_arg_semantic_handle_adapter"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_table_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_name"
        ]
        == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_schema_hash"
        ]
        == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_semantic_field_count"
        ]
        == len(PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS)
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_hit_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_required_source_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_optional_source_miss_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_handle_field_read_count"
        ]
        == 8
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mode"
        ]
        == "readonly_single_field_handle_handoff_canary"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_name"
        ]
        == "scale_metadata_handle"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_source"
        ]
        == "semantic_handle_table"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_mode"
        ]
        == "readonly_scale_metadata_handle_mirror"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_field_name"
        ]
        == "scale_metadata_handle"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_source"
        ]
        == "semantic_handle_table"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_handle_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_mirror_schema_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_nonzero_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_field_handle_zero_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_ok_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_parity_mismatch_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_current_wna16_arg_compatible_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_live_enabled_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_block_reason"
        ]
        == "single_field_handoff_live_disabled"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_ready_credit_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_single_field_handle_handoff_canary_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_semantic_adapter_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_mode"
        ]
        == "readonly_kernel_side_consumer_schema_adapter"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_table_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_name"
        ]
        == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_schema_hash"
        ]
        == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_side_field_count"
        ]
        == len(PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS)
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_hit_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_required_source_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_handle_field_read_count"
        ]
        == 8
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_schema_present_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason"
        ]
        == "kernel_side_consumer_live_disabled"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
        ]
        == "readonly_kernel_arg_handoff_attempt"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
        ]
        == "kernel_arg_handoff_disabled_noop_gate"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
        ]
        == "readonly_kernel_arg_handoff_live_toggle"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode"
        ]
        == "readonly_kernel_arg_handoff_live_noop_integration"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode"
        ]
        == "readonly_kernel_arg_handoff_live_consumer_adapter"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
        ]
        == "schema-hash"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count"
        ]
        == 1
    )
    for field in (
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count",
    ):
        assert aggregate[field] == 2
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
        ]
        == 8
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
        ]
        == 6
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count"
        ]
        == 0
    )
    for field in (
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count",
    ):
        assert aggregate[field] == 2
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
        ]
        == 1
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count"]
        == 1
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate"]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate"
        ]
        == 1.0
    )
    assert (
        aggregate["premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
        ]
        == "kernel-schema-hash"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
        ]
        == 2
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        rows[0]["premap_consumer_descriptor_prep_consumer_object_hash"]
        == "prep-consumer-object-hash"
    )
    assert (
        rows[0]["premap_consumer_descriptor_prep_consumer_object_read_hash"]
        == "prep-consumer-object-hash"
    )
    assert (
        rows[0]["premap_consumer_descriptor_prep_consumer_object_read_ok"]
        is True
    )
    assert rows[0]["premap_consumer_descriptor_prep_consumer_shim_mode"] == (
        "readonly_prelaunch_consumer_shim"
    )
    assert rows[0]["premap_consumer_descriptor_prep_consumer_shim_ok"] is True
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
        ]
        == 2
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count"
        ]
        == 4
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
        ]
        == 0
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok"
        ]
        is True
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok"
        ]
        is True
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
        ]
        == 2
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel"
        ]
        is False
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok"
        ]
        is True
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
        ]
        == 2
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count"
        ]
        == 4
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
        ]
        == "schema-hash"
    )
    assert rows[0][
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
    ] == "readonly_consume_kernel_arg_shadow_table"
    assert rows[0][
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
    ] == "canonical_address_key_order"
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ordered_row_hash"
        ]
        == "ordered-row-hash"
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel"
        ]
        is False
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_consumer_shim_changes_kernel_launch_args"
        ]
        is False
    )
    assert rows[0]["premap_consumer_descriptor_prep_kernel_arg_shadow_table_mode"] == (
        "readonly_kernel_arg_shadow_table"
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_source"
        ]
        == "canonical_address_key_order"
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
        ]
        == 2
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count"
        ]
        == 4
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
        ]
        == "kernel-schema-hash"
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_order_hash"
        ]
        == "row-order-hash"
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ordered_row_hash"
        ]
        == "ordered-row-hash"
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
        ]
        == 2
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count"
        ]
        == 0
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count"
        ]
        == 0
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok"
        ]
        is True
    )
    assert (
        rows[0]["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok"]
        is True
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes"
        ]
        == 0
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit"
        ]
        is False
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_router"
        ]
        is False
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_descriptor_order"
        ]
        is False
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        rows[0][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel"
        ]
        is False
    )
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


def test_shadow_log_premap_descriptor_prep_real_hit_rate_counts_missing_handles():
    event = ShadowPremapConsumerMappingEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=2),
        mapping_mode="noop_assertion",
        mapping_source="fused_moe_prepare_expert_assignment",
        address_namespace="expert_weight_descriptor",
        consumer_expert_count=2,
        consumer_unique_expert_count=2,
        address_hit_count=1,
        address_miss_count=1,
        address_hit_rate=0.5,
        all_hit=False,
        parity_ok=False,
        consumer_key_hash="consumer-hash",
        descriptor_handle_hit_count=1,
        descriptor_handle_miss_count=1,
        descriptor_handle_parity_ok=False,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_lookup_count=2,
        descriptor_prep_handle_count=1,
        descriptor_prep_missing_handle_count=1,
        descriptor_prep_descriptor_ptr_count=1,
        descriptor_prep_packed_weight_descriptor_count=1,
        descriptor_prep_scale_metadata_handle_count=1,
        descriptor_prep_real_handle_count=1,
        descriptor_prep_real_handle_miss_count=0,
        descriptor_prep_real_handle_backed=True,
        descriptor_prep_execution_ok=False,
    )

    aggregate = aggregate_shadow_events([event.as_dict()])

    assert aggregate["premap_consumer_descriptor_prep_real_handle_count"] == 1
    assert aggregate["premap_consumer_descriptor_prep_real_handle_miss_count"] == 0
    assert aggregate["premap_consumer_descriptor_prep_missing_handle_count"] == 1
    assert aggregate["premap_consumer_descriptor_prep_real_handle_hit_rate"] == 0.5


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


def test_shadow_log_aggregates_live_consumer_adapter_gate_branches() -> None:
    def _aggregate_adapter(
        *,
        enabled: bool,
        lab_gate_passed: bool,
        live_eligible: bool,
        block_reason: str,
        changes_kernel_launch_args: bool = False,
    ) -> dict[str, object]:
        event = ShadowPremapConsumerMappingEvent(
            event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
            mapping_mode="noop_assertion",
            mapping_source="unit",
            address_namespace="expert_weight_descriptor",
            consumer_expert_count=1,
            consumer_unique_expert_count=1,
            address_hit_count=1,
            address_miss_count=0,
            address_hit_rate=1.0,
            all_hit=True,
            parity_ok=True,
            consumer_key_hash="consumer-key-hash",
            descriptor_prep_consumer_shim_mode="readonly_prelaunch_consumer_shim",
            descriptor_prep_consumer_shim_handle_table_consume_ok=True,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode=(
                "readonly_kernel_arg_handoff_live_noop_integration"
            ),
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode=(
                "readonly_kernel_arg_handoff_live_consumer_adapter"
            ),
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready=True,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash=(
                "adapter-hash"
            ),
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash=(
                "live-noop-hash"
            ),
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash=(
                "launch-mirror-hash"
            ),
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash=(
                "table-object-hash"
            ),
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled=enabled,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed=lab_gate_passed,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready=True,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked=True,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason=block_reason,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present=True,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected=False,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible=live_eligible,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked=True,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason=block_reason,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes=0,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel=False,
            descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args=changes_kernel_launch_args,
        )
        return aggregate_shadow_events([event.as_dict()])

    without_gate = _aggregate_adapter(
        enabled=True,
        lab_gate_passed=False,
        live_eligible=False,
        block_reason="kernel_arg_handoff_lab_gate_not_passed",
    )
    assert (
        without_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count"
        ]
        == 1
    )
    assert (
        without_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count"
        ]
        == 1
    )
    assert (
        without_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count"
        ]
        == 1
    )
    assert (
        without_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count"
        ]
        == 0
    )
    assert (
        without_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count"
        ]
        == 0
    )
    assert (
        without_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
        ]
        == "kernel_arg_handoff_lab_gate_not_passed"
    )

    with_gate = _aggregate_adapter(
        enabled=True,
        lab_gate_passed=True,
        live_eligible=True,
        block_reason="kernel_arg_handoff_kernel_consumer_not_connected",
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count"
        ]
        == 1
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count"
        ]
        == 1
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count"
        ]
        == 1
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
        ]
        == 0
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count"
        ]
        == 0
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        with_gate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
        ]
        == "kernel_arg_handoff_kernel_consumer_not_connected"
    )

    changed_kernel_args = _aggregate_adapter(
        enabled=True,
        lab_gate_passed=True,
        live_eligible=True,
        block_reason="kernel_arg_handoff_kernel_consumer_not_connected",
        changes_kernel_launch_args=True,
    )
    assert (
        changed_kernel_args[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count"
        ]
        == 1
    )
    assert (
        changed_kernel_args[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 1
    )


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


def test_shadow_log_aggregates_premap_payload_cache_manager_snapshot_deltas(tmp_path):
    issue = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
        premap_policy="premap_only",
        premap_descriptor_count=2,
        premap_unique_experts=2,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=128,
        premap_descriptor_hash="desc-1",
        premap_address_hash="addr-1",
        premap_payload_cache_manager_capacity=4,
        premap_payload_cache_resident_count=2,
        premap_payload_cache_issued_fetch_count=2,
        premap_payload_cache_used_fetch_count=0,
        premap_payload_cache_unused_fetch_count=2,
        premap_payload_cache_demand_count=0,
        premap_payload_cache_demand_hit_count=0,
        premap_payload_cache_demand_miss_count=0,
        premap_payload_cache_evicted_before_use_count=0,
        premap_payload_cache_demand_hit_rate=0.0,
        premap_payload_cache_used_fetch_rate=0.0,
        premap_payload_cache_eviction_pressure=0.0,
    )
    consume = ShadowPremapConsumerMappingEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
        mapping_mode="noop_assertion",
        mapping_source="fused_moe_prepare_expert_assignment",
        address_namespace="expert_weight_descriptor",
        consumer_expert_count=2,
        consumer_unique_expert_count=2,
        address_hit_count=2,
        address_miss_count=0,
        address_hit_rate=1.0,
        all_hit=True,
        parity_ok=True,
        consumer_key_hash="keys",
        premap_payload_cache_manager_capacity=4,
        premap_payload_cache_resident_count=2,
        premap_payload_cache_issued_fetch_count=2,
        premap_payload_cache_used_fetch_count=2,
        premap_payload_cache_unused_fetch_count=0,
        premap_payload_cache_demand_count=2,
        premap_payload_cache_demand_hit_count=2,
        premap_payload_cache_demand_miss_count=0,
        premap_payload_cache_evicted_before_use_count=0,
        premap_payload_cache_demand_hit_rate=1.0,
        premap_payload_cache_used_fetch_rate=1.0,
        premap_payload_cache_eviction_pressure=0.0,
    )
    reset = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req2", sequence_id=1, token_index=-1, layer=0),
        premap_policy="premap_only",
        premap_descriptor_count=1,
        premap_unique_experts=1,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=64,
        premap_descriptor_hash="desc-2",
        premap_address_hash="addr-2",
        premap_payload_cache_manager_capacity=4,
        premap_payload_cache_resident_count=1,
        premap_payload_cache_issued_fetch_count=1,
        premap_payload_cache_used_fetch_count=0,
        premap_payload_cache_unused_fetch_count=1,
        premap_payload_cache_demand_count=0,
        premap_payload_cache_demand_hit_count=0,
        premap_payload_cache_demand_miss_count=0,
        premap_payload_cache_evicted_before_use_count=0,
        premap_payload_cache_demand_hit_rate=0.0,
        premap_payload_cache_used_fetch_rate=0.0,
        premap_payload_cache_eviction_pressure=0.0,
    )

    output = write_shadow_jsonl(
        [issue, consume, reset],
        tmp_path / "premap_payload_cache_mgr.jsonl",
    )
    aggregate = aggregate_shadow_events(read_shadow_jsonl(output))

    assert aggregate["premap_payload_cache_manager_count"] == 3
    assert aggregate["premap_payload_cache_issued_fetch_count"] == 3
    assert aggregate["premap_payload_cache_used_fetch_count"] == 2
    assert aggregate["premap_payload_cache_demand_count"] == 2
    assert aggregate["premap_payload_cache_demand_hit_count"] == 2
    assert aggregate["premap_payload_cache_demand_miss_count"] == 0
    assert aggregate["premap_payload_cache_evicted_before_use_count"] == 0
    assert aggregate["premap_payload_cache_resident_count_max"] == 2
    assert aggregate["premap_payload_cache_unused_fetch_count_max"] == 2
    assert aggregate["premap_payload_cache_demand_hit_rate_mean"] == (1.0 / 3)
    assert aggregate["premap_payload_cache_used_fetch_rate_mean"] == (1.0 / 3)


def test_shadow_log_aggregates_payload_cache_only_event_without_mapping_count(tmp_path):
    event = ShadowPremapPayloadCacheManagerEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
        cache_mode="accounting_only",
        source="fused_moe_prepare_expert_assignment",
        consumer_expert_count=4,
        consumer_unique_expert_count=2,
        premap_payload_cache_manager_id="mgr-1",
        premap_payload_cache_manager_capacity=8,
        premap_payload_cache_resident_count=2,
        premap_payload_cache_issued_fetch_count=0,
        premap_payload_cache_used_fetch_count=0,
        premap_payload_cache_unused_fetch_count=0,
        premap_payload_cache_demand_count=2,
        premap_payload_cache_demand_hit_count=0,
        premap_payload_cache_demand_miss_count=2,
        premap_payload_cache_evicted_before_use_count=0,
        premap_payload_cache_demand_hit_rate=0.0,
        premap_payload_cache_used_fetch_rate=0.0,
        premap_payload_cache_eviction_pressure=0.0,
    )

    output = write_shadow_jsonl([event], tmp_path / "premap_payload_only.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["event_type"] == "premap_payload_cache_manager"
    assert rows[0]["premap_payload_cache_payload_bytes"] == 0
    assert rows[0]["premap_payload_cache_ready_credit"] is False
    assert rows[0]["premap_payload_cache_changes_kernel_launch_args"] is False
    assert aggregate["premap_payload_cache_manager_count"] == 1
    assert aggregate["premap_payload_cache_demand_count"] == 2
    assert aggregate["premap_payload_cache_demand_miss_count"] == 2
    assert aggregate["premap_consumer_mapping_count"] == 0


def test_shadow_log_aggregates_ready_time_payload_cache_fields(tmp_path):
    first = ShadowPremapPayloadCacheManagerEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
        cache_mode="ready_time_accounting_only",
        source="fused_moe_prepare_expert_assignment",
        consumer_expert_count=1,
        consumer_unique_expert_count=1,
        premap_payload_cache_manager_id="mgr-ready",
        premap_payload_cache_manager_capacity=8,
        premap_payload_cache_resident_count=1,
        premap_payload_cache_issued_fetch_count=1,
        premap_payload_cache_used_fetch_count=0,
        premap_payload_cache_unused_fetch_count=1,
        premap_payload_cache_demand_count=0,
        premap_payload_cache_demand_hit_count=0,
        premap_payload_cache_demand_miss_count=0,
        premap_payload_cache_evicted_before_use_count=0,
        premap_payload_cache_ready_late_miss_count=0,
        premap_payload_cache_late_completion_unused_count=0,
        premap_payload_cache_queue_batch_count=1,
        premap_payload_cache_queue_service_us=5.0,
        premap_payload_cache_queue_wait_us=0.0,
        premap_payload_cache_queue_max_delay_us=5.0,
        premap_payload_cache_queue_total_span_us=5.0,
        premap_payload_cache_queue_deadline_us=4.0,
        premap_payload_cache_queue_batch_size=1,
        premap_payload_cache_demand_hit_rate=0.0,
        premap_payload_cache_used_fetch_rate=0.0,
        premap_payload_cache_eviction_pressure=0.0,
    )
    second = ShadowPremapPayloadCacheManagerEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=1),
        cache_mode="ready_time_accounting_only",
        source="fused_moe_prepare_expert_assignment",
        consumer_expert_count=1,
        consumer_unique_expert_count=1,
        premap_payload_cache_manager_id="mgr-ready",
        premap_payload_cache_manager_capacity=8,
        premap_payload_cache_resident_count=1,
        premap_payload_cache_issued_fetch_count=1,
        premap_payload_cache_used_fetch_count=0,
        premap_payload_cache_unused_fetch_count=1,
        premap_payload_cache_demand_count=1,
        premap_payload_cache_demand_hit_count=0,
        premap_payload_cache_demand_miss_count=1,
        premap_payload_cache_evicted_before_use_count=0,
        premap_payload_cache_ready_late_miss_count=1,
        premap_payload_cache_late_completion_unused_count=1,
        premap_payload_cache_queue_batch_count=2,
        premap_payload_cache_queue_service_us=8.0,
        premap_payload_cache_queue_wait_us=2.0,
        premap_payload_cache_queue_max_delay_us=7.0,
        premap_payload_cache_queue_total_span_us=9.0,
        premap_payload_cache_queue_deadline_us=4.0,
        premap_payload_cache_queue_batch_size=1,
        premap_payload_cache_demand_hit_rate=0.0,
        premap_payload_cache_used_fetch_rate=0.0,
        premap_payload_cache_eviction_pressure=0.0,
    )

    output = write_shadow_jsonl([first, second], tmp_path / "ready_time.jsonl")
    rows = read_shadow_jsonl(output)
    aggregate = aggregate_shadow_events(rows)

    assert rows[0]["premap_payload_cache_queue_service_us"] == 5.0
    assert rows[1]["premap_payload_cache_ready_late_miss_count"] == 1
    assert aggregate["premap_payload_cache_ready_late_miss_count"] == 1
    assert aggregate["premap_payload_cache_late_completion_unused_count"] == 1
    assert aggregate["premap_payload_cache_queue_batch_count"] == 2
    assert aggregate["premap_payload_cache_queue_service_us"] == 8.0
    assert aggregate["premap_payload_cache_queue_wait_us"] == 2.0
    assert aggregate["premap_payload_cache_queue_max_delay_us_max"] == 7.0
    assert aggregate["premap_payload_cache_queue_total_span_us_max"] == 9.0
    assert aggregate["premap_payload_cache_queue_deadline_us_max"] == 4.0
    assert aggregate["premap_payload_cache_queue_batch_size_max"] == 1


def test_shadow_log_ready_time_payload_cache_deltas_are_per_manager(tmp_path):
    events = [
        ShadowPremapPayloadCacheManagerEvent(
            event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
            cache_mode="ready_time_accounting_only",
            source="manager-a",
            consumer_expert_count=1,
            consumer_unique_expert_count=1,
            premap_payload_cache_manager_id="mgr-a",
            premap_payload_cache_resident_count=0,
            premap_payload_cache_queue_batch_count=1,
            premap_payload_cache_queue_service_us=5.0,
            premap_payload_cache_queue_wait_us=1.0,
        ),
        ShadowPremapPayloadCacheManagerEvent(
            event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=1),
            cache_mode="ready_time_accounting_only",
            source="manager-b",
            consumer_expert_count=1,
            consumer_unique_expert_count=1,
            premap_payload_cache_manager_id="mgr-b",
            premap_payload_cache_resident_count=0,
            premap_payload_cache_queue_batch_count=1,
            premap_payload_cache_queue_service_us=3.0,
            premap_payload_cache_queue_wait_us=2.0,
        ),
        ShadowPremapPayloadCacheManagerEvent(
            event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=2),
            cache_mode="ready_time_accounting_only",
            source="manager-a",
            consumer_expert_count=1,
            consumer_unique_expert_count=1,
            premap_payload_cache_manager_id="mgr-a",
            premap_payload_cache_resident_count=0,
            premap_payload_cache_queue_batch_count=2,
            premap_payload_cache_queue_service_us=8.0,
            premap_payload_cache_queue_wait_us=4.0,
        ),
    ]

    output = write_shadow_jsonl(events, tmp_path / "ready_time_multi_manager.jsonl")
    aggregate = aggregate_shadow_events(read_shadow_jsonl(output))

    assert aggregate["premap_payload_cache_queue_batch_count"] == 3
    assert aggregate["premap_payload_cache_queue_service_us"] == 11.0
    assert aggregate["premap_payload_cache_queue_wait_us"] == 6.0


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


def test_kernel_arg_shadow_table_aggregate_detects_mixed_column_and_schema_rows():
    aggregate = aggregate_shadow_events(
        [
            {
                "event_type": "premap_consumer_mapping",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_mode": (
                    "readonly_kernel_arg_shadow_table"
                ),
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok": True,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok": True,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count": 2,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count": 4,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash": (
                    "kernel-schema-hash"
                ),
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count": 2,
            },
            {
                "event_type": "premap_consumer_mapping",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_mode": (
                    "readonly_kernel_arg_shadow_table"
                ),
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok": True,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok": True,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count": 1,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count": 3,
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count": 1,
            },
        ]
    )

    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
        ]
        == 4
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
        ]
        == 3
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
        ]
        == "kernel-schema-hash"
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count"
        ]
        == 0
    )


def test_consumer_shim_table_read_aggregate_reports_not_checked_rows():
    aggregate = aggregate_shadow_events(
        [
            {
                "event_type": "premap_consumer_mapping",
                "premap_consumer_descriptor_prep_consumer_shim_mode": (
                    "readonly_prelaunch_consumer_shim"
                ),
                "premap_consumer_descriptor_prep_consumer_shim_ok": False,
                "premap_consumer_descriptor_prep_consumer_shim_object_count": 2,
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count": 2,
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count": 4,
            }
        ]
    )

    assert aggregate["premap_consumer_descriptor_prep_consumer_shim_executed_count"] == 1
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
        ]
        == 0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate"
        ]
        == 1.0
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
        ]
        == 0.0
    )


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


def test_consumer_shim_consume_source_requires_kernel_row_order_source():
    aggregate = aggregate_shadow_events(
        [
            {
                "event_type": "premap_consumer_mapping",
                "premap_consumer_descriptor_prep_consumer_shim_mode": (
                    "readonly_prelaunch_consumer_shim"
                ),
                "premap_consumer_descriptor_prep_consumer_shim_ok": True,
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok": True,
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode": (
                    "readonly_consume_kernel_arg_shadow_table"
                ),
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source": (
                    "canonical_address_key_order"
                ),
            }
        ]
    )

    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count"
        ]
        == 1
    )
    assert (
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count"
        ]
        == 1
    )


def test_premap_wna16_adjacent_typed_slot_event_is_aggregated():
    event = ShadowPremapConsumerMappingEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=0),
        mapping_mode="noop_assertion",
        mapping_source="unit",
        address_namespace="expert_weight_descriptor",
        consumer_expert_count=4,
        consumer_unique_expert_count=4,
        address_hit_count=4,
        address_miss_count=0,
        address_hit_rate=1.0,
        all_hit=True,
        parity_ok=True,
        consumer_key_hash="consumer-key-hash",
        descriptor_prep_consumer_shim_mode="readonly_prelaunch_consumer_shim",
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_name=(
            "premap_wna16_adjacent_typed_consumer_slot_v1"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_mode=(
            "readonly_wna16_adjacent_typed_consumer_slot"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_source=(
            "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_checked=True,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_ready=True,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_input_hash=(
            "input-hash"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_table_object_hash=(
            "table-hash"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_schema_hash=(
            "schema-hash"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_error_count=0,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_all_handle_fields_read=True,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packet_chain_depth=14,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_mask=15,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_descriptor_ptr_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_packed_weight_descriptor_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_scale_metadata_handle_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_aux_metadata_handle_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_expert_id_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_address_key_hash_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_read_row_ok_count=4,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_hash_accumulator=(
            "0000000000000001"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_field_read_hash_accumulator=(
            "0000000000000002"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_row_metadata_hash_accumulator=(
            "0000000000000003"
        ),
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_failure_count=0,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_payload_bytes=0,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_passed_to_kernel=False,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_changes_kernel_launch_args=False,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_current_wna16_arg_compatible=False,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation=False,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_explicit_typed_abi_slot=True,
        descriptor_prep_consumer_shim_wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot=False,
    )
    row = event.as_dict()
    prefix = "premap_consumer_descriptor_prep_consumer_shim_wna16_adjacent_typed_slot"
    assert row[f"{prefix}_mode"] == "readonly_wna16_adjacent_typed_consumer_slot"
    assert row[f"{prefix}_passed_to_kernel"] is False

    aggregate = aggregate_shadow_events([row])

    assert aggregate[f"{prefix}_checked_count"] == 1
    assert aggregate[f"{prefix}_ready_count"] == 1
    assert aggregate[f"{prefix}_name"] == "premap_wna16_adjacent_typed_consumer_slot_v1"
    assert aggregate[f"{prefix}_source"] == (
        "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
    )
    assert aggregate[f"{prefix}_row_count"] == 4
    assert aggregate[f"{prefix}_row_ok_count"] == 4
    assert aggregate[f"{prefix}_error_count"] == 0
    assert aggregate[f"{prefix}_all_handle_fields_read_count"] == 1
    assert aggregate[f"{prefix}_packet_chain_depth"] == 14
    assert aggregate[f"{prefix}_packet_chain_depth_mismatch_count"] == 0
    assert aggregate[f"{prefix}_field_mask"] == 15
    assert aggregate[f"{prefix}_field_mask_mismatch_count"] == 0
    assert aggregate[f"{prefix}_payload_bytes"] == 0
    assert aggregate[f"{prefix}_payload_violation_count"] == 0
    assert aggregate[f"{prefix}_passed_to_kernel_count"] == 0
    assert aggregate[f"{prefix}_kernel_arg_violation_count"] == 0
    assert aggregate[f"{prefix}_current_wna16_arg_compatible_count"] == 0
    assert aggregate[f"{prefix}_requires_wna16_arg_reinterpretation_count"] == 0
    assert aggregate[f"{prefix}_explicit_typed_abi_slot_count"] == 1
    assert aggregate[f"{prefix}_reuses_current_wna16_arg_slot_count"] == 0
