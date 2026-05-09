import torch

from mtp_expert_prefetch.runtime import (
    AdmissionDecisionMasks,
    OnlineShadowLogger,
    RuntimeShadowController,
    TileRequest,
    build_layer_tile_prior,
    build_shadow_summary_from_decisions,
    hash_layer_tile_prior,
    order_tile_request_stream_with_layer_prior,
)
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowDescriptorPrelaunchAssertEvent,
    ShadowDescriptorSummaryMinEvent,
    ShadowEventId,
    ShadowOutcomeAggregateEvent,
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


def test_online_shadow_logger_batched_writer_defers_jsonl_until_flush(tmp_path):
    event_id = ShadowEventId("req", 0, 3, 2)
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
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
    )
    path = tmp_path / "batched_shadow.jsonl"

    with OnlineShadowLogger(
        path,
        flush_every=10,
        writer_mode="jsonl_batched",
    ) as logger:
        logger.write_summary(summary)
        assert read_shadow_jsonl(path) == []
        logger.flush()
        rows = read_shadow_jsonl(path)

    assert [row["event_type"] for row in rows] == ["summary"]
    assert rows[0]["shadow_event_id"] == "req:0:3:2"


def test_runtime_shadow_controller_writes_descriptor_order_min_summary(tmp_path):
    path = tmp_path / "descriptor_min_shadow.jsonl"
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
        descriptor_order_mapping_assertion_mode="router_topk_tile_stream",
        descriptor_order_mapping_source="base_router_select_experts_topk",
        descriptor_order_mapping_same_multiset=True,
        descriptor_order_mapping_counts_match=True,
        descriptor_order_mapping_tile_multiset_hash="tile-hash",
        descriptor_order_mapping_plan_tile_multiset_hash="tile-hash",
        descriptor_order_mapping_request_count=16,
        descriptor_order_mapping_plan_request_count=16,
        descriptor_order_mapping_group_count=8,
        descriptor_order_mapping_plan_group_count=8,
        descriptor_order_build_us=2.0,
        decision_us=6.0,
    )

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        controller.write_descriptor_order_min_summary(event)
        stats = controller.stats_dict()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["descriptor_summary_min"]
    assert rows[0]["descriptor_tile_request_count"] == 16
    assert rows[0]["descriptor_group_plan_group_count"] == 8
    assert rows[0]["descriptor_group_plan_cta_count"] == 2
    assert rows[0]["descriptor_order_mapping_same_multiset"] is True
    assert rows[0]["descriptor_order_mapping_counts_match"] is True
    assert rows[0]["descriptor_order_mapping_tile_multiset_hash"] == "tile-hash"
    assert rows[0]["descriptor_order_mapping_plan_tile_multiset_hash"] == "tile-hash"
    assert rows[0]["descriptor_order_mapping_source"] == "base_router_select_experts_topk"
    assert rows[0]["descriptor_order_mapping_request_count"] == 16
    assert stats["written_summary_count"] == 1


def test_runtime_shadow_controller_writes_descriptor_prelaunch_assertion(tmp_path):
    path = tmp_path / "prelaunch_shadow.jsonl"
    event = ShadowDescriptorPrelaunchAssertEvent(
        event_id=ShadowEventId("req", sequence_id=0, token_index=-1, layer=3),
        assertion_mode="moe_runner_prelaunch_topk",
        mapping_source="moe_runner_quant_method_apply_topk",
        router_mapping_source="base_router_select_experts_topk",
        same_multiset=True,
        counts_match=True,
        prelaunch_tile_multiset_hash="hash-v1",
        router_derived_tile_multiset_hash="hash-v1",
        prelaunch_request_count=16,
        router_derived_request_count=16,
        prelaunch_group_count=8,
        router_derived_group_count=8,
        dump_us=3.0,
        reorder_mvp_requested=True,
        reorder_mvp_gate_allow=True,
        reorder_mvp_gate_reason="allowed",
        reorder_mvp_candidate_policy="layer_prior_frequency_two_level",
        reorder_mvp_candidate_speedup_median_vs_no_order=1.2,
        reorder_mvp_selected_policy="no_order",
        reorder_mvp_applied=False,
        reorder_mvp_fallback_reason="dry_run_no_vllm_descriptor_consumer_patch",
    )

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        controller.write_descriptor_prelaunch_assertion(event)
        stats = controller.stats_dict()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["descriptor_prelaunch_assertion"]
    assert rows[0]["descriptor_order_prelaunch_same_multiset"] is True
    assert rows[0]["descriptor_order_prelaunch_tile_multiset_hash"] == "hash-v1"
    assert rows[0]["descriptor_order_reorder_mvp_requested"] is True
    assert rows[0]["descriptor_order_reorder_mvp_applied"] is False
    assert rows[0]["descriptor_order_reorder_mvp_fallback_reason"] == (
        "dry_run_no_vllm_descriptor_consumer_patch"
    )
    assert stats["written_descriptor_prelaunch_assertion_count"] == 1


def test_online_shadow_logger_rejects_unknown_writer_mode(tmp_path):
    path = tmp_path / "bad_writer_shadow.jsonl"

    try:
        OnlineShadowLogger(path, writer_mode="bad_writer")
    except ValueError as exc:
        assert "writer_mode" in str(exc)
    else:
        raise AssertionError("OnlineShadowLogger accepted an unknown writer mode")


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
    assert outcome["join_status"] == "joined"
    assert aggregate["summary_count"] == 1
    assert aggregate["outcome_count"] == 1
    assert aggregate["full_fetch_used_count"] == 1
    assert aggregate["metadata_later_used_count"] == 1
    assert aggregate["top1_ready_rate"] == 1.0
    assert aggregate["joined_outcome_count"] == 1
    assert aggregate["controller_stats"]["joined_outcome_count"] == 1
    assert aggregate["controller_stats"]["pending_summary_count"] == 0


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
    assert rows[0]["join_status"] == "outcome_only"


def test_runtime_shadow_controller_can_suppress_outcome_writes(tmp_path):
    event_id = ShadowEventId("req", 0, 8, 5)
    path = tmp_path / "suppressed_outcome_shadow.jsonl"
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

    with RuntimeShadowController(
        OnlineShadowLogger(path),
        emit_outcomes=False,
    ) as controller:
        controller.write_outcome(event)
        stats = controller.stats_dict()

    rows = read_shadow_jsonl(path)
    assert rows == []
    assert stats["outcome_only_count"] == 1
    assert stats["written_outcome_count"] == 0
    assert stats["suppressed_outcome_count"] == 1


def test_runtime_shadow_controller_writes_and_suppresses_outcome_aggregate(tmp_path):
    event = ShadowOutcomeAggregateEvent(
        event_id=ShadowEventId("req", 0, 8, 5),
        token_start=8,
        token_end=10,
        token_count=2,
        top_k=2,
        topk_entry_count=4,
        routed_expert_count=3,
        topk_weight_mass_sum=2.0,
        top1_weight_sum=1.4,
        top1_weight_mean=0.7,
    )
    written_path = tmp_path / "written_aggregate_shadow.jsonl"
    suppressed_path = tmp_path / "suppressed_aggregate_shadow.jsonl"

    with RuntimeShadowController(OnlineShadowLogger(written_path)) as controller:
        controller.write_outcome_aggregate(event)
        written_stats = controller.stats_dict()

    rows = read_shadow_jsonl(written_path)
    assert [row["event_type"] for row in rows] == ["outcome_aggregate"]
    assert written_stats["written_outcome_aggregate_count"] == 1
    assert written_stats["suppressed_outcome_aggregate_count"] == 0

    with RuntimeShadowController(
        OnlineShadowLogger(suppressed_path),
        emit_outcomes=False,
    ) as controller:
        controller.write_outcome_aggregate(event)
        suppressed_stats = controller.stats_dict()

    assert read_shadow_jsonl(suppressed_path) == []
    assert suppressed_stats["written_outcome_aggregate_count"] == 0
    assert suppressed_stats["suppressed_outcome_aggregate_count"] == 1


def test_runtime_shadow_controller_writes_descriptor_order_summary(tmp_path):
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-v1"},
    )
    prior_hash = hash_layer_tile_prior(prior)
    requests = [
        TileRequest(1, 0, 1, 1, layer_idx=0),
        TileRequest(1, 1, 2, 2, layer_idx=0),
        TileRequest(1, 2, 1, 1, layer_idx=0),
    ]
    _, report = order_tile_request_stream_with_layer_prior(
        requests,
        prior=prior,
        prior_id="prior-v1",
        prior_hash=prior_hash,
    )
    path = tmp_path / "descriptor_order_shadow.jsonl"

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        summary = controller.write_descriptor_order_summary(
            event_id=ShadowEventId("req", 0, 1, 0),
            policy=ShadowPolicyConfig(
                policy_mode="descriptor_order_shadow",
                optimization_goal="cache_locality",
                action_keep_fraction=0.0,
                metadata_score_ratio=0.0,
                full_fetch_max_extra=0,
                metadata_max_extra=0,
                premap_max_extra=0,
                descriptor_order_policy="layer_prior_frequency",
                descriptor_order_prior_id="prior-v1",
                descriptor_order_prior_hash=prior_hash,
            ),
            descriptor_report=report,
        )
        aggregate = controller.aggregate()

    rows = read_shadow_jsonl(path)
    assert summary.descriptor_order_prior_hash == prior_hash
    assert rows[0]["descriptor_order_policy"] == "layer_prior_frequency"
    assert rows[0]["descriptor_order_prior_hash"] == prior_hash
    assert rows[0]["descriptor_order_lru_at_8"] == report.metrics["lru_hit_rate"]["8"]
    assert rows[0]["descriptor_order_hit_rate"] == report.metrics["tile_order_hit_rate"]
    assert aggregate["descriptor_order_summary_count"] == 1
    assert aggregate["descriptor_order_lru_at_8_mean"] == report.metrics["lru_hit_rate"]["8"]
    assert aggregate["controller_stats"]["written_summary_count"] == 1


def test_runtime_shadow_controller_can_suppress_descriptor_summary_writes(tmp_path):
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
    )
    requests = [
        TileRequest(1, 0, 1, 1, layer_idx=0),
        TileRequest(1, 1, 2, 2, layer_idx=0),
    ]
    _, report = order_tile_request_stream_with_layer_prior(requests, prior=prior)
    path = tmp_path / "suppressed_descriptor_summary_shadow.jsonl"

    with RuntimeShadowController(
        OnlineShadowLogger(path),
        emit_summaries=False,
    ) as controller:
        summary = controller.write_descriptor_order_summary(
            event_id=ShadowEventId("req", 0, 1, 0),
            policy=ShadowPolicyConfig(
                policy_mode="descriptor_order_shadow",
                optimization_goal="cache_locality",
                action_keep_fraction=0.0,
                metadata_score_ratio=0.0,
                full_fetch_max_extra=0,
                metadata_max_extra=0,
                premap_max_extra=0,
            ),
            descriptor_report=report,
        )
        stats = controller.stats_dict()

    rows = read_shadow_jsonl(path)
    assert rows == []
    assert summary.descriptor_order_build_us == report.order_build_us
    assert stats["written_summary_count"] == 0
    assert stats["suppressed_summary_count"] == 1


def test_runtime_shadow_controller_reports_pending_timeouts_and_evictions(tmp_path):
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
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
    )
    path = tmp_path / "timeout_shadow.jsonl"

    with RuntimeShadowController(OnlineShadowLogger(path), max_pending=1) as controller:
        controller.write_action_summary(
            event_id=ShadowEventId("req", 0, 1, 0),
            policy=policy,
            decisions=decisions,
        )
        controller.write_action_summary(
            event_id=ShadowEventId("req", 0, 2, 0),
            policy=policy,
            decisions=decisions,
        )
        assert controller.stats_dict()["evicted_summary_count"] == 1
        timeout_count = controller.flush_pending_as_timeouts()
        aggregate = controller.aggregate()

    rows = read_shadow_jsonl(path)
    assert timeout_count == 1
    assert rows[-1]["event_type"] == "outcome"
    assert rows[-1]["join_status"] == "summary_only_timeout"
    assert aggregate["summary_only_timeout_count"] == 1
    assert aggregate["controller_stats"]["evicted_summary_count"] == 1
    assert aggregate["controller_stats"]["summary_only_timeout_count"] == 1
