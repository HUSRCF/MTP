import torch
import pytest

from mtp_expert_prefetch.runtime import (
    AdmissionDecisionMasks,
    OnlineShadowLogger,
    RuntimeShadowController,
    TileRequest,
    build_layer_tile_prior,
    hash_layer_tile_prior,
)
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowPolicyConfig,
    read_shadow_jsonl,
)
from mtp_expert_prefetch.tracing.vllm_router_trace import VllmRouterRecorder
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    set_active_runtime_shadow_controller,
    write_active_runtime_shadow_action_summary,
)


class _Sink:
    def __init__(self) -> None:
        self.events = []

    def write_outcome(self, event) -> None:
        self.events.append(event)


def test_vllm_router_recorder_shadow_sink_is_optional():
    recorder = VllmRouterRecorder(top_k=2)
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(recorder.calls) == 1


def test_vllm_router_recorder_writes_shadow_outcome_events():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(sink.events) == 2
    first = sink.events[0].as_dict()
    second = sink.events[1].as_dict()
    assert first["event_type"] == "outcome"
    assert first["shadow_event_id"] == "req:5:10:3"
    assert first["true_topk_experts"] == [1, 2]
    assert first["true_topk_weights"] == pytest.approx([0.8, 0.2])
    assert first["top1_ready"] is False
    assert first["weighted_top1_miss"] == pytest.approx(0.8)
    assert second["shadow_event_id"] == "req:5:11:3"
    assert second["true_topk_experts"] == [3, 4]


def test_active_runtime_shadow_hook_joins_with_vllm_router_outcome(tmp_path):
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
    ready = torch.zeros(shape, dtype=torch.bool)
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
    event_id = ShadowEventId("req", 5, 10, 3)
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
    )
    path = tmp_path / "runtime_shadow.jsonl"

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        set_active_runtime_shadow_controller(controller)
        try:
            summary = write_active_runtime_shadow_action_summary(
                event_id=event_id,
                policy=policy,
                decisions=decisions,
                ready_mask=ready,
            )
        finally:
            set_active_runtime_shadow_controller(None)
        assert summary is not None
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            request_id="req",
            sequence_id=5,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["summary", "outcome"]
    outcome = rows[1]
    assert outcome["join_status"] == "joined"
    assert outcome["full_fetch_used_count"] == 1
    assert outcome["metadata_later_used_count"] == 1
    assert outcome["covered_mass"] == pytest.approx(0.8)
    assert outcome["top1_ready"] is True


def test_vllm_router_recorder_emits_previous_token_transition_summaries(tmp_path):
    path = tmp_path / "transition_shadow.jsonl"
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_num_experts=6,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=1,
            topk_ids=torch.tensor([[1, 2], [2, 3], [4, 5]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3], [0.6, 0.4]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == [
        "outcome",
        "summary",
        "outcome",
        "summary",
        "outcome",
    ]
    assert rows[0]["shadow_event_id"] == "req:0:0:1"
    assert rows[0]["join_status"] == "outcome_only"
    assert rows[1]["shadow_event_id"] == "req:0:1:1"
    assert rows[1]["policy_mode"] == "transition_only_shadow"
    assert rows[1]["transition_topk_count"] == 2
    assert rows[2]["shadow_event_id"] == "req:0:1:1"
    assert rows[2]["join_status"] == "joined"
    assert rows[2]["covered_mass"] == pytest.approx(0.7)
    assert rows[2]["top1_ready"] is True
    assert rows[4]["join_status"] == "joined"


def test_vllm_router_recorder_emits_matrix_topk_transition_summaries(tmp_path):
    path = tmp_path / "matrix_transition_shadow.jsonl"
    transition = torch.zeros(1, 1, 6, 6)
    transition[0, 0, 1, 4] = 10.0
    transition[0, 0, 2, 5] = 9.0
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_num_experts=6,
            shadow_transition_topk_count=2,
            shadow_transition_summary_mode="matrix_topk",
            shadow_transition_matrix=transition,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [4, 5]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome", "summary", "outcome"]
    assert rows[1]["policy_reason"] == "matrix_topk_transition_summary"
    assert rows[2]["join_status"] == "joined"
    assert rows[2]["covered_mass"] == pytest.approx(1.0)
    assert rows[2]["top1_ready"] is True


def test_vllm_router_recorder_emits_descriptor_order_summary(tmp_path):
    path = tmp_path / "descriptor_order_shadow.jsonl"
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

    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_descriptor_order_summary=True,
            shadow_descriptor_order_prior=prior,
            shadow_descriptor_order_prior_id="prior-v1",
            shadow_descriptor_order_prior_hash=prior_hash,
            shadow_descriptor_order_tiles_per_expert=1,
            request_id="req",
            sequence_id=0,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2], [1, 3]]),
            topk_weights=torch.tensor([[0.7, 0.3], [0.6, 0.4]]),
        )
        aggregate = controller.aggregate()

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome", "outcome", "summary"]
    summary = rows[-1]
    assert summary["shadow_event_id"] == "req:0:-1:0"
    assert summary["policy_mode"] == "descriptor_order_shadow"
    assert summary["descriptor_order_policy"] == "layer_prior_frequency"
    assert summary["descriptor_order_prior_id"] == "prior-v1"
    assert summary["descriptor_order_prior_hash"] == prior_hash
    assert summary["descriptor_tile_request_count"] == 4
    assert summary["descriptor_same_multiset"] is True
    assert summary["descriptor_order_changed"] is True
    assert summary["candidate_construction_us"] >= 0.0
    assert summary["descriptor_order_build_us"] >= 0.0
    assert summary["decision_us"] >= summary["candidate_construction_us"]
    assert aggregate["descriptor_order_summary_count"] == 1
    assert aggregate["controller_stats"]["written_summary_count"] == 1


def test_vllm_descriptor_order_summary_is_noop_without_prior(tmp_path):
    path = tmp_path / "descriptor_order_missing_prior.jsonl"
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_descriptor_order_summary=True,
            request_id="req",
            sequence_id=0,
            token_offset=10,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.7, 0.3]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome"]


def test_vllm_matrix_topk_transition_is_weighted_and_stable(tmp_path):
    path = tmp_path / "matrix_transition_weighted_shadow.jsonl"
    transition = torch.zeros(1, 1, 6, 6)
    transition[0, 0, 1, 4] = 1.0
    transition[0, 0, 2, 5] = 10.0
    transition[0, 0, 1, 0] = 0.5
    transition[0, 0, 2, 0] = 0.5
    transition[0, 0, 1, 3] = 0.5
    transition[0, 0, 2, 3] = 0.5
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=3,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_num_experts=6,
            shadow_transition_topk_count=3,
            shadow_transition_summary_mode="matrix_topk",
            shadow_transition_matrix=transition,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2, 0], [4, 0, 3]]),
            topk_weights=torch.tensor([[8.0, 2.0, 0.0], [0.6, 0.3, 0.1]]),
        )

    rows = read_shadow_jsonl(path)
    assert rows[1]["full_fetch_count"] == 0
    assert rows[2]["join_status"] == "joined"
    # Weight renormalization makes expert 4 outrank expert 5. Experts 0 and 3
    # tie, so expert-id ascending tie-break includes expert 0 for top3.
    assert rows[2]["covered_mass"] == pytest.approx(0.9)
    assert rows[2]["top1_ready"] is True
