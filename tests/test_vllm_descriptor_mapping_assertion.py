from __future__ import annotations

import torch

from mtp_expert_prefetch.runtime import TileRequest, build_layer_tile_prior
from mtp_expert_prefetch.tracing.vllm_router_trace import VllmRouterRecorder


class _DescriptorMinSink:
    def __init__(self) -> None:
        self.events = []

    def write_descriptor_order_min_summary(self, event) -> None:
        self.events.append(event)


def test_vllm_recorder_emits_noop_descriptor_mapping_assertion() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
            TileRequest(0, 2, 3, 3, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prior_id="prior-test",
        shadow_descriptor_order_prior_hash="prior-hash",
        shadow_descriptor_order_metrics_mode="none",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_mapping_assertion_mode="router_topk_tile_stream",
        shadow_descriptor_order_mapping_source="base_router_select_experts_topk",
        shadow_descriptor_order_token_window_size=1,
    )

    recorder.record_topk(
        layer_id=0,
        topk_ids=torch.tensor([[1, 2], [2, 3]], dtype=torch.long),
        topk_weights=torch.tensor([[0.4, 0.6], [0.7, 0.3]], dtype=torch.float32),
    )

    assert len(sink.events) == 1
    payload = sink.events[0].as_dict()
    assert payload["event_type"] == "descriptor_summary_min"
    assert payload["descriptor_order_mapping_assertion_mode"] == "router_topk_tile_stream"
    assert payload["descriptor_order_mapping_source"] == "base_router_select_experts_topk"
    assert payload["descriptor_order_mapping_same_multiset"] is True
    assert payload["descriptor_order_mapping_counts_match"] is True
    assert (
        payload["descriptor_order_mapping_tile_multiset_hash"]
        == payload["descriptor_order_mapping_plan_tile_multiset_hash"]
    )
    assert payload["descriptor_order_mapping_request_count"] == 4
    assert payload["descriptor_order_mapping_plan_request_count"] == 4
    assert payload["descriptor_order_mapping_group_count"] == 4
    assert payload["descriptor_order_mapping_plan_group_count"] == 4
    assert "descriptor_order_mapping_error" not in payload


def test_vllm_recorder_does_not_claim_same_multiset_without_plan_hash() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_metrics_mode="count_only",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_mapping_assertion_mode="router_topk_tile_stream",
        shadow_descriptor_order_token_window_size=1,
    )

    recorder.record_topk(
        layer_id=0,
        topk_ids=torch.tensor([[1, 2], [2, 3]], dtype=torch.long),
        topk_weights=torch.tensor([[0.4, 0.6], [0.7, 0.3]], dtype=torch.float32),
    )

    payload = sink.events[0].as_dict()
    assert payload["descriptor_order_mapping_counts_match"] is True
    assert payload["descriptor_order_mapping_same_multiset"] is False
    assert payload["descriptor_order_mapping_error"] == "plan_tile_multiset_hash_missing"
    assert "descriptor_order_mapping_plan_tile_multiset_hash" not in payload
