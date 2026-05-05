import torch
import pytest

from mtp_expert_prefetch.tracing.vllm_router_trace import VllmRouterRecorder


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
