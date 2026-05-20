import torch
import pytest

from mtp_expert_prefetch.runtime import (
    AdmissionDecisionMasks,
    DescriptorOrderExecutionEvidence,
    DescriptorOrderRuntimeGate,
    OnlineShadowLogger,
    RuntimeShadowController,
    TileRequest,
    build_layer_tile_prior,
    build_premap_shadow_summary,
    hash_layer_tile_prior,
)
from mtp_expert_prefetch.runtime.shadow_log import (
    ShadowEventId,
    ShadowPolicyConfig,
    read_shadow_jsonl,
)
from mtp_expert_prefetch.tracing.vllm_router_trace import VllmRouterRecorder
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    SharedExpertFusedGateUnsupportedError,
    _shared_expert_fused_gate_fallbackable,
    _run_shared_expert_output_gate_default_postprocess,
    _shared_expert_custom_gate_enabled,
    _shared_expert_fused_gate_unsupported,
    _unwrap_vllm_projection_output,
    set_active_runtime_shadow_controller,
    write_active_runtime_shadow_action_summary,
)


class _Sink:
    def __init__(self) -> None:
        self.events = []

    def write_outcome(self, event) -> None:
        self.events.append(event)

    def write_outcome_aggregate(self, event) -> None:
        self.events.append(event)

    def write_descriptor_order_min_summary(self, event) -> None:
        self.events.append(event)

    def write_premap_summary_from_descriptors(self, **kwargs):
        event = build_premap_shadow_summary(**kwargs)
        self.events.append(event)
        return event

    def write_premap_consumer_mapping(self, event) -> None:
        self.events.append(event)

    def write_descriptor_layer_timing(self, event) -> None:
        self.events.append(event)


class _OutcomeOnlySink:
    def __init__(self) -> None:
        self.events = []

    def write_outcome(self, event) -> None:
        self.events.append(event)


class _ExpertGate(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.ones(1, 2))

    def forward(self, hidden_states: torch.Tensor):
        return hidden_states @ self.weight.t(), None


class _FakeAwqConsumerLayer(torch.nn.Module):
    def __init__(self, num_experts: int = 6) -> None:
        super().__init__()
        self.register_buffer("expert_map", torch.arange(num_experts, dtype=torch.int32))
        self.register_buffer(
            "w13_weight_packed",
            torch.arange(num_experts * 4, dtype=torch.int32).reshape(num_experts, 4),
        )
        self.register_buffer(
            "w2_weight_packed",
            torch.arange(num_experts * 4, dtype=torch.int32).reshape(num_experts, 4),
        )
        self.register_buffer(
            "w13_weight_scale",
            torch.arange(num_experts * 2, dtype=torch.float32).reshape(num_experts, 2),
        )
        self.register_buffer(
            "w2_weight_scale",
            torch.arange(num_experts * 2, dtype=torch.float32).reshape(num_experts, 2),
        )


def test_vllm_router_recorder_shadow_sink_is_optional():
    recorder = VllmRouterRecorder(top_k=2)
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(recorder.calls) == 1


def test_shared_expert_custom_gate_enabled_in_minimal_modes() -> None:
    default_recorder = VllmRouterRecorder(top_k=2)
    assert _shared_expert_custom_gate_enabled(default_recorder) is False

    inplace_recorder = VllmRouterRecorder(
        top_k=2,
        shadow_shared_expert_output_gate_postprocess="inplace",
    )
    assert _shared_expert_custom_gate_enabled(inplace_recorder) is True

    fused_recorder = VllmRouterRecorder(
        top_k=2,
        shadow_shared_expert_output_gate_postprocess="fused_triton",
    )
    assert _shared_expert_custom_gate_enabled(fused_recorder) is True


def test_shared_expert_default_postprocess_inplace_matches_default() -> None:
    hidden = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    out = torch.tensor([[2.0, 3.0], [4.0, 5.0]])
    gate = _ExpertGate()

    expected = _run_shared_expert_output_gate_default_postprocess(
        hidden_states=hidden,
        out=out.clone(),
        expert_gate=gate,
        postprocess="default",
    )
    actual = _run_shared_expert_output_gate_default_postprocess(
        hidden_states=hidden,
        out=out.clone(),
        expert_gate=gate,
        postprocess="inplace",
    )

    torch.testing.assert_close(actual, expected)


def test_shared_expert_default_postprocess_accepts_tensor_gate_output() -> None:
    hidden = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    out = torch.tensor([[2.0, 3.0], [4.0, 5.0]])
    gate = torch.nn.Linear(2, 1, bias=False)
    torch.nn.init.ones_(gate.weight)

    expected_gate = torch.sigmoid(hidden @ gate.weight.t())
    expected = out * expected_gate
    actual = _run_shared_expert_output_gate_default_postprocess(
        hidden_states=hidden,
        out=out.clone(),
        expert_gate=gate,
        postprocess="default",
    )

    torch.testing.assert_close(actual, expected)


def test_unwrap_vllm_projection_output_accepts_tensor_or_tuple() -> None:
    value = torch.tensor([[1.0]])
    assert _unwrap_vllm_projection_output(value) is value
    assert _unwrap_vllm_projection_output((value, None)) is value

    with pytest.raises(TypeError):
        _unwrap_vllm_projection_output((None, value))


def test_shared_expert_fused_unsupported_error_is_detected() -> None:
    assert _shared_expert_fused_gate_unsupported(
        SharedExpertFusedGateUnsupportedError(
            "fused shared gate requires a bias-free weight parameter"
        )
    )
    assert not _shared_expert_fused_gate_unsupported(
        RuntimeError("fused shared gate requires a bias-free weight parameter")
    )
    assert not _shared_expert_fused_gate_unsupported(RuntimeError("other failure"))


def test_shared_expert_fused_gate_runtime_errors_are_fallbackable_except_oom() -> None:
    assert _shared_expert_fused_gate_fallbackable(
        SharedExpertFusedGateUnsupportedError("unsupported")
    )
    assert _shared_expert_fused_gate_fallbackable(
        RuntimeError("triton launch failed")
    )
    assert not _shared_expert_fused_gate_fallbackable(
        RuntimeError("HIP error: out of memory")
    )


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


def test_decoder_component_handoff_aggregate_flushes_per_layer_phase_bucket():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=15.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=4,
        component="attention_linear_handoff_out_proj",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention",
        elapsed_us=50.0,
        num_tokens=1,
        phase="decode",
    )

    assert len(sink.events) == 1
    assert sink.events[0]["event_type"] == "decoder_component_timing"
    recorder.flush_decoder_component_aggregates()

    aggregate_events = [
        event for event in sink.events if event["event_type"] == "decoder_component_aggregate"
    ]
    assert len(aggregate_events) == 2
    by_layer = {event["layer"]: event for event in aggregate_events}
    layer3 = by_layer[3]
    layer4 = by_layer[4]
    assert layer3["shadow_event_id"] == "req:7:-1:3"
    assert layer3["decoder_component_aggregate_count"] == 2
    assert layer3["decoder_component_aggregate_components"][
        "attention_linear_handoff_norm"
    ] == {"sum_us": 25.0, "count": 2}
    assert layer4["decoder_component_aggregate_components"][
        "attention_linear_handoff_out_proj"
    ] == {"sum_us": 20.0, "count": 1}

    recorder.flush_decoder_component_aggregates()
    assert len(
        [
            event
            for event in sink.events
            if event["event_type"] == "decoder_component_aggregate"
        ]
    ) == 2


def test_decoder_component_handoff_counter_only_flushes_fixed_component_payload():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=15.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_out_proj",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
    )

    recorder.flush_decoder_component_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "decoder_component_aggregate"
    assert event["decoder_component_aggregate_mode"] == "attention_handoff_counter_only"
    assert event["decoder_component_aggregate_count"] == 3
    assert event["decoder_component_aggregate_components"][
        "attention_linear_handoff_norm"
    ] == {"sum_us": 25.0, "count": 2}
    assert event["decoder_component_aggregate_components"][
        "attention_linear_handoff_out_proj"
    ] == {"sum_us": 20.0, "count": 1}


def test_decoder_component_handoff_no_write_drops_aggregates_on_flush():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert sink.events == []


def test_decoder_component_handoff_aggregate_no_write_drops_aggregates_on_flush():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_aggregate_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_norm",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert len(sink.events) == 1
    assert sink.events[0]["event_type"] == "decoder_component_timing"
    assert sink.events[0]["decoder_component"] == "attention"


def test_decoder_component_handoff_counter_only_falls_back_for_unknown_handoff():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_new_component",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "decoder_component_timing"
    assert event["decoder_component"] == "attention_linear_handoff_new_component"
    assert event["decoder_component_logging_fallback"] == "unknown_handoff_component"


def test_decoder_component_handoff_counter_no_write_drops_unknown_handoff():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_decoder_component_timing=True,
        shadow_decoder_component_logging_mode="attention_handoff_counter_only_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    recorder.write_decoder_component_timing(
        layer_id=3,
        component="attention_linear_handoff_new_component",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
    )
    recorder.flush_decoder_component_aggregates()

    assert sink.events == []


def test_moe_substage_aggregate_flushes_per_layer_phase_bucket():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_direct_layer",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_direct_layer",
        elapsed_us=15.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_output_gate",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="fallback",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="quant_method_apply",
        elapsed_us=50.0,
        num_tokens=1,
        phase="decode",
        status="not_shared",
    )

    assert sink.events == []
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "moe_substage_aggregate"
    assert event["shadow_event_id"] == "req:7:-1:3"
    assert event["moe_substage_aggregate_count"] == 3
    assert event["moe_substage_aggregate_component_count"] == 3
    assert event["moe_substage_aggregate_count_match"] is True
    assert event["moe_substage_aggregate_components"][
        "experts_shared_direct_layer"
    ] == {
        "sum_us": 25.0,
        "raw_sum_us": 25.0,
        "count": 2,
        "estimated_count": 2,
        "status_counts": {"ok": 2},
        "estimated_status_counts": {"ok": 2},
        "sample_period": 1,
    }
    assert event["moe_substage_aggregate_components"][
        "experts_shared_output_gate"
    ] == {
        "sum_us": 20.0,
        "raw_sum_us": 20.0,
        "count": 1,
        "estimated_count": 1,
        "status_counts": {"fallback": 1},
        "estimated_status_counts": {"fallback": 1},
        "sample_period": 1,
    }
    assert "quant_method_apply" not in event["moe_substage_aggregate_components"]


def test_moe_substage_shared_body_mode_only_records_direct_layer():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body",
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    for substage in (
        "experts_shared_determine_order",
        "experts_shared_w1",
        "experts_shared_direct_layer",
        "experts_shared_output_gate",
        "quant_method_apply",
    ):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage=substage,
            elapsed_us=10.0,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "moe_substage_aggregate"
    assert event["moe_substage_aggregate_count"] == 1
    assert event["moe_substage_aggregate_component_count"] == 1
    assert event["moe_substage_aggregate_count_match"] is True
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_direct_layer",
    }


def test_moe_substage_shared_body_regions_records_only_body_buckets():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body_regions",
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    for substage in (
        "experts_shared_determine_order",
        "experts_shared_direct_layer",
        "experts_shared_body_core",
        "experts_shared_body_gate_proj",
        "experts_shared_body_gate_apply",
        "experts_shared_body_gate_fused",
        "experts_shared_w1",
        "experts_shared_output_gate",
        "quant_method_apply",
    ):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage=substage,
            elapsed_us=10.0,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["event_type"] == "moe_substage_aggregate"
    assert event["moe_substage_aggregate_count"] == 5
    assert event["moe_substage_aggregate_component_count"] == 5
    assert event["moe_substage_aggregate_count_match"] is True
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_direct_layer",
        "experts_shared_body_core",
        "experts_shared_body_gate_proj",
        "experts_shared_body_gate_apply",
        "experts_shared_body_gate_fused",
    }


@pytest.mark.parametrize("mode", ["shared_direct", "shared_coarse"])
def test_moe_substage_shared_body_aliases_only_record_direct_layer(mode: str):
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode=mode,
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_w1",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_direct_layer",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["moe_substage_aggregate_count"] == 1
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_direct_layer",
    }


@pytest.mark.parametrize("mode", ["shared_direct_regions", "shared_coarse_regions"])
def test_moe_substage_shared_body_regions_aliases_record_body_buckets(mode: str):
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode=mode,
        shadow_moe_substage_logging_mode="aggregate",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_w1",
        elapsed_us=10.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_core",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_gate_apply",
        elapsed_us=30.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event["moe_substage_aggregate_count"] == 2
    assert set(event["moe_substage_aggregate_components"]) == {
        "experts_shared_body_core",
        "experts_shared_body_gate_apply",
    }


def test_moe_substage_aggregate_no_write_drops_flushed_payloads():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body_regions",
        shadow_moe_substage_logging_mode="aggregate_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_core",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert sink.events == []


def test_moe_substage_shared_aggregate_no_write_drops_flushed_payloads():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared_body_regions",
        shadow_moe_substage_logging_mode="shared_aggregate_no_write",
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=42,
    )

    recorder.write_moe_substage_timing(
        layer_id=3,
        substage="experts_shared_body_core",
        elapsed_us=20.0,
        num_tokens=1,
        phase="decode",
        status="ok",
    )
    recorder.flush_moe_substage_aggregates()

    assert sink.events == []


def test_moe_substage_sampled_aggregate_scales_decode_samples():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="sampled_aggregate",
        shadow_moe_substage_sample_period=2,
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    for elapsed_us in (10.0, 20.0, 30.0):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage="experts_shared_direct_layer",
            elapsed_us=elapsed_us,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    component = event["moe_substage_aggregate_components"][
        "experts_shared_direct_layer"
    ]
    assert event["moe_substage_aggregate_count"] == 2
    assert event["moe_substage_sample_period"] == 2
    assert component["count"] == 2
    assert component["estimated_count"] == 4
    assert component["raw_sum_us"] == 40.0
    assert component["sum_us"] == 80.0
    assert component["sample_period"] == 2
    assert component["status_counts"] == {"ok": 2}
    assert component["estimated_status_counts"] == {"ok": 4}


def test_moe_substage_shared_sampled_aggregate_scales_decode_samples():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="shared_sampled_aggregate",
        shadow_moe_substage_sample_period=2,
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    for elapsed_us in (10.0, 20.0, 30.0):
        recorder.write_moe_substage_timing(
            layer_id=3,
            substage="experts_shared_direct_layer",
            elapsed_us=elapsed_us,
            num_tokens=1,
            phase="decode",
            status="ok",
        )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    component = event["moe_substage_aggregate_components"][
        "experts_shared_direct_layer"
    ]
    assert event["moe_substage_aggregate_mode"] == "shared_sampled_aggregate"
    assert event["moe_substage_aggregate_count"] == 2
    assert event["moe_substage_aggregate_component_count"] == 2
    assert event["moe_substage_aggregate_count_match"] is True
    assert event["moe_substage_sample_period"] == 2
    assert component["count"] == 2
    assert component["estimated_count"] == 4
    assert component["raw_sum_us"] == 40.0
    assert component["sum_us"] == 80.0
    assert component["sample_period"] == 2


def test_moe_substage_shared_sampled_aggregate_samples_per_substage():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
        shadow_moe_substage_logging_mode="shared_sampled_aggregate",
        shadow_moe_substage_sample_period=2,
        request_id="req",
        sequence_id=7,
        shadow_descriptor_order_event_token_index=-1,
    )

    for substage, base_us in (
        ("experts_shared_direct_layer", 10.0),
        ("experts_shared_output_gate", 100.0),
    ):
        for i in range(3):
            recorder.write_moe_substage_timing(
                layer_id=3,
                substage=substage,
                elapsed_us=base_us + float(i),
                num_tokens=1,
                phase="decode",
                status="ok",
            )
    recorder.flush_moe_substage_aggregates()

    assert len(sink.events) == 1
    event = sink.events[0]
    components = event["moe_substage_aggregate_components"]
    assert event["moe_substage_aggregate_count"] == 4
    assert event["moe_substage_aggregate_component_count"] == 4
    assert event["moe_substage_aggregate_count_match"] is True
    assert event["moe_substage_sample_period"] == 2
    direct = components["experts_shared_direct_layer"]
    gate = components["experts_shared_output_gate"]
    assert direct["count"] == 2
    assert direct["estimated_count"] == 4
    assert direct["raw_sum_us"] == 22.0
    assert direct["sum_us"] == 44.0
    assert gate["count"] == 2
    assert gate["estimated_count"] == 4
    assert gate["raw_sum_us"] == 202.0
    assert gate["sum_us"] == 404.0


def test_vllm_router_recorder_writes_aggregate_shadow_outcome():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="aggregate",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "outcome_aggregate"
    assert row["shadow_event_id"] == "req:5:10:3"
    assert row["token_start"] == 10
    assert row["token_end"] == 12
    assert row["token_count"] == 2
    assert row["top_k"] == 2
    assert row["topk_entry_count"] == 4
    assert row["routed_expert_count"] == 3
    assert row["top1_weight_mean"] == pytest.approx(0.7)


def test_vllm_router_recorder_aggregate_requires_aggregate_sink():
    sink = _OutcomeOnlySink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="aggregate",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    with pytest.raises(TypeError, match="write_outcome_aggregate"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )


def test_vllm_router_recorder_can_disable_shadow_outcomes():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )
    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [3, 4]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.6, 0.4]]),
    )

    assert sink.events == []


def test_vllm_router_recorder_premap_summary_works_with_outcomes_off():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_num_experts=6,
        shadow_premap_descriptor_bytes=64,
        shadow_premap_policy="premap_only",
        shadow_premap_source="current_router_topk_premap_shadow",
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 7], [-1, 3]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3], [0.1, 0.6]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "premap_summary"
    assert row["request_id"] == "req"
    assert row["sequence_id"] == 5
    assert row["token_index"] == -1
    assert row["layer"] == 3
    assert row["premap_policy"] == "premap_only"
    assert row["premap_source"] == "current_router_topk_premap_shadow"
    assert row["premap_descriptor_count"] == 3
    assert row["premap_unique_experts"] == 3
    assert row["premap_actual_bytes"] == 3 * 64
    assert row["premap_payload_bytes"] == 0
    assert row["premap_full_fetch_count"] == 0
    assert row["premap_metadata_count"] == 0
    assert row["premap_changes_router"] is False
    assert row["premap_changes_descriptor_order"] is False
    assert row["premap_ready_credit"] is False


def test_vllm_router_recorder_premap_summary_can_be_sampled_without_skipping_manager():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_premap_summary_sample_period=3,
        shadow_premap_address_manager_capacity=8,
        shadow_premap_descriptor_bytes=64,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    for _ in range(4):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )

    rows = [event.as_dict() for event in sink.events]
    premap_rows = [row for row in rows if row["event_type"] == "premap_summary"]
    assert len(premap_rows) == 2
    assert premap_rows[0]["premap_address_new_count"] == 2
    # Unsampled calls still update the address manager, so the second sampled
    # event observes the fourth prepare call rather than call two.
    assert premap_rows[1]["premap_address_reused_count"] == 6
    assert recorder._last_premap_address_mapping_by_layer[3]["prepare_plan_count"] == 4
    assert recorder._last_premap_address_mapping_by_layer[3]["prepare_record_count"] == 8


def test_vllm_router_recorder_premap_summary_can_emit_address_manager_counters():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_premap_address_manager_capacity=4,
        shadow_num_experts=6,
        shadow_premap_descriptor_bytes=64,
        request_id="req",
        sequence_id=5,
    )

    for _ in range(2):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )

    rows = [event.as_dict() for event in sink.events]
    assert len(rows) == 2
    assert rows[0]["premap_address_manager_capacity"] == 4
    assert rows[0]["premap_address_new_count"] == 2
    assert rows[0]["premap_address_reused_count"] == 0
    assert rows[0]["premap_address_resident_count"] == 2
    assert rows[0]["premap_address_resident_descriptor_bytes"] == 128
    assert rows[0]["premap_payload_bytes"] == 0

    assert rows[1]["premap_address_new_count"] == 2
    assert rows[1]["premap_address_reused_count"] == 2
    assert rows[1]["premap_address_resident_count"] == 2
    assert rows[1]["premap_address_reuse_rate"] == 0.5
    assert rows[1]["premap_address_eviction_pressure"] == 0.0
    assert rows[1]["premap_payload_bytes"] == 0


def test_vllm_router_recorder_premap_consumer_mapping_hits_prepared_addresses():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_address_manager_capacity=4,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2]]),
    )
    recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=3,
        sorted_token_ids=torch.arange(4, dtype=torch.int32),
        expert_ids=torch.tensor([1, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([4], dtype=torch.int32),
        block_size=2,
    )

    rows = [event.as_dict() for event in sink.events]
    assert [row["event_type"] for row in rows] == [
        "premap_summary",
        "premap_consumer_mapping",
    ]
    consumer = rows[1]
    assert consumer["premap_consumer_mapping_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert consumer["premap_consumer_expert_count"] == 2
    assert consumer["premap_consumer_unique_expert_count"] == 2
    assert consumer["premap_consumer_address_hit_count"] == 2
    assert consumer["premap_consumer_address_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_handle_hit_count"] == 2
    assert consumer["premap_consumer_descriptor_handle_miss_count"] == 0
    assert consumer["premap_consumer_descriptor_handle_hash"]
    assert consumer["premap_consumer_expected_descriptor_handle_hash"] == (
        consumer["premap_consumer_descriptor_handle_hash"]
    )
    assert consumer["premap_consumer_descriptor_handle_parity_ok"] is True
    assert consumer["premap_consumer_expected_prepare_plan_count"] == 1
    assert consumer["premap_consumer_observed_prepare_plan_count"] == 1
    assert consumer["premap_consumer_expected_prepare_record_count"] == 2
    assert consumer["premap_consumer_observed_prepare_record_count"] == 2
    assert consumer["premap_consumer_lookup_after_prepare"] is True
    assert consumer["premap_consumer_all_hit"] is True
    assert consumer["premap_consumer_parity_ok"] is True
    assert consumer["premap_consumer_payload_bytes"] == 0
    assert consumer["premap_consumer_changes_router"] is False
    assert consumer["premap_consumer_changes_descriptor_order"] is False
    assert consumer["premap_consumer_ready_credit"] is False


def test_vllm_router_recorder_premap_consumer_real_handle_lifecycle_and_eviction():
    sink = _Sink()
    consumer_layer = _FakeAwqConsumerLayer(num_experts=6)
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        shadow_emit_premap_address_manager_counters=True,
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_address_manager_capacity=1,
        shadow_premap_consumer_resolve_real_handles=True,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2]]),
        topk_weights=torch.tensor([[0.8, 0.2]]),
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )

    rows = [event.as_dict() for event in sink.events]
    consumer_rows = [
        row for row in rows if row["event_type"] == "premap_consumer_mapping"
    ]
    assert len(consumer_rows) == 2

    first = consumer_rows[0]
    assert first["premap_consumer_address_hit_count"] == 1
    assert first["premap_consumer_address_miss_count"] == 1
    assert first["premap_consumer_descriptor_handle_hit_count"] == 1
    assert first["premap_consumer_descriptor_handle_miss_count"] == 1
    assert first["premap_consumer_real_descriptor_handle_hit_count"] == 2
    assert first["premap_consumer_real_descriptor_handle_miss_count"] == 0
    assert first["premap_consumer_real_descriptor_handle_available"] is True
    assert first["premap_consumer_real_descriptor_handle_new_binding_count"] == 2
    assert first["premap_consumer_real_descriptor_handle_reused_binding_count"] == 0
    assert first["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0
    assert first["premap_consumer_real_descriptor_handle_for_address_miss_count"] == 1
    assert first["premap_consumer_all_hit"] is False
    assert first["premap_consumer_parity_ok"] is False
    assert first["premap_consumer_payload_bytes"] == 0
    assert first["premap_consumer_changes_router"] is False
    assert first["premap_consumer_changes_descriptor_order"] is False
    assert first["premap_consumer_ready_credit"] is False

    second = consumer_rows[1]
    assert second["premap_consumer_real_descriptor_handle_new_binding_count"] == 0
    assert second["premap_consumer_real_descriptor_handle_reused_binding_count"] == 2
    assert second["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0
    assert second["premap_consumer_real_descriptor_handle_for_address_miss_count"] == 1


def test_vllm_router_recorder_premap_real_handle_binding_survives_clear():
    sink = _Sink()
    consumer_layer = _FakeAwqConsumerLayer(num_experts=6)
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_resolve_real_handles=True,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )
    recorder.clear()
    recorder._write_premap_consumer_mapping_from_experts(
        layer_id=3,
        active_experts=[1, 2],
        consumer_layer=consumer_layer,
    )

    rows = [event.as_dict() for event in sink.events]
    assert len(rows) == 2
    assert rows[0]["premap_consumer_real_descriptor_handle_new_binding_count"] == 2
    assert rows[0]["premap_consumer_real_descriptor_handle_reused_binding_count"] == 0
    assert rows[1]["premap_consumer_real_descriptor_handle_new_binding_count"] == 0
    assert rows[1]["premap_consumer_real_descriptor_handle_reused_binding_count"] == 2
    assert rows[1]["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0


def test_vllm_router_recorder_premap_consumer_mapping_can_be_sampled():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_consumer_mapping=True,
        shadow_premap_consumer_mapping_sample_period=3,
        shadow_num_experts=6,
        request_id="req",
        sequence_id=5,
    )

    for _ in range(7):
        recorder._write_premap_consumer_mapping_from_experts(
            layer_id=3,
            active_experts=[1, 2],
            consumer_layer=None,
        )

    rows = [event.as_dict() for event in sink.events]
    assert len(rows) == 3
    assert all(row["event_type"] == "premap_consumer_mapping" for row in rows)


def test_vllm_router_recorder_premap_summary_requires_supported_sink():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=_OutcomeOnlySink(),
        shadow_outcome_logging_mode="off",
        shadow_emit_premap_summary=True,
        request_id="req",
        sequence_id=5,
    )

    with pytest.raises(TypeError, match="write_premap_summary_from_descriptors"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )


def test_vllm_router_recorder_transition_premap_summary_works_with_outcomes_off():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        shadow_num_experts=6,
        shadow_transition_summary_mode="previous_topk",
        shadow_premap_descriptor_bytes=16,
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 3], [4, 5]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3], [0.6, 0.4]]),
    )

    assert len(sink.events) == 2
    rows = [event.as_dict() for event in sink.events]
    assert [row["event_type"] for row in rows] == ["premap_summary", "premap_summary"]
    assert [row["token_index"] for row in rows] == [11, 12]
    assert [row["premap_descriptor_count"] for row in rows] == [2, 2]
    assert [row["premap_actual_bytes"] for row in rows] == [32, 32]
    assert {row["premap_source"] for row in rows} == {
        "previous_token_transition_premap_shadow"
    }
    assert all(row["premap_payload_bytes"] == 0 for row in rows)
    assert all(row["premap_full_fetch_count"] == 0 for row in rows)
    assert all(row["premap_metadata_count"] == 0 for row in rows)
    assert all(row["premap_changes_router"] is False for row in rows)
    assert all(row["premap_changes_descriptor_order"] is False for row in rows)
    assert all(row["premap_ready_credit"] is False for row in rows)


def test_vllm_router_recorder_transition_premap_summary_requires_supported_sink():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=_OutcomeOnlySink(),
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        request_id="req",
        sequence_id=5,
    )

    with pytest.raises(TypeError, match="write_premap_summary_from_descriptors"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2], [2, 3]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
        )


def test_vllm_router_recorder_matrix_topk_transition_premap_summary():
    sink = _Sink()
    transition = torch.zeros((1, 4, 6, 6), dtype=torch.float32)
    # Previous expert 1 predicts experts 4, 2, then 3 for layer 3.
    transition[0, 3, 1, 4] = 0.9
    transition[0, 3, 1, 2] = 0.8
    transition[0, 3, 1, 3] = 0.7
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        shadow_num_experts=6,
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=2,
        shadow_transition_matrix=transition,
        shadow_premap_policy="transition_matrix_top2_premap_only",
        shadow_transition_premap_source="matrix_topk_transition_premap_shadow",
        shadow_premap_descriptor_bytes=32,
        request_id="req",
        sequence_id=5,
        token_offset=10,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 0], [2, 3]]),
        topk_weights=torch.tensor([[1.0, 0.0], [0.7, 0.3]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "premap_summary"
    assert row["token_index"] == 11
    assert row["premap_policy"] == "transition_matrix_top2_premap_only"
    assert row["premap_source"] == "matrix_topk_transition_premap_shadow"
    assert row["premap_descriptor_count"] == 2
    assert row["premap_unique_experts"] == 2
    assert row["premap_actual_bytes"] == 64
    assert row["premap_payload_bytes"] == 0
    assert row["premap_ready_credit"] is False


def test_vllm_router_recorder_matrix_topk_transition_premap_ignores_oob_previous():
    sink = _Sink()
    transition = torch.zeros((1, 4, 6, 6), dtype=torch.float32)
    transition[0, 3, 1, 4] = 0.9
    transition[0, 3, 1, 2] = 0.8
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_transition_premap_summary=True,
        shadow_num_experts=6,
        shadow_transition_summary_mode="matrix_topk",
        shadow_transition_topk_count=2,
        shadow_transition_matrix=transition,
        shadow_premap_policy="transition_matrix_top2_premap_only",
        shadow_transition_premap_source="matrix_topk_transition_premap_shadow",
        request_id="req",
        sequence_id=5,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[99, 1], [2, 3]]),
        topk_weights=torch.tensor([[0.5, 0.5], [0.7, 0.3]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "premap_summary"
    assert row["premap_descriptor_count"] == 2
    assert "premap_error" not in row
    assert row["premap_payload_bytes"] == 0


def test_vllm_router_recorder_can_disable_descriptor_layer_timing():
    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_descriptor_layer_timing=False,
        request_id="req",
        sequence_id=5,
    )

    recorder.write_descriptor_layer_timing(
        layer_id=3,
        apply_us=10.0,
        num_tokens=1,
        phase="decode",
    )

    assert sink.events == []


def test_vllm_router_recorder_outcome_logging_mode_aliases_and_invalid():
    recorder = VllmRouterRecorder(top_k=2)

    recorder.shadow_outcome_logging_mode = " none "
    assert recorder._resolved_outcome_logging_mode() == "off"
    recorder.shadow_outcome_logging_mode = "FALSE"
    assert recorder._resolved_outcome_logging_mode() == "off"
    recorder.shadow_outcome_logging_mode = "1"
    assert recorder._resolved_outcome_logging_mode() == "full"

    sink = _Sink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="bad-mode",
    )
    with pytest.raises(ValueError, match="Unsupported shadow_outcome_logging_mode"):
        recorder.record_topk(
            layer_id=3,
            topk_ids=torch.tensor([[1, 2]]),
            topk_weights=torch.tensor([[0.8, 0.2]]),
        )


def test_transition_summary_forces_full_outcomes_when_outcome_mode_off(tmp_path):
    path = tmp_path / "transition_shadow_force_full.jsonl"
    with RuntimeShadowController(OnlineShadowLogger(path)) as controller:
        recorder = VllmRouterRecorder(
            top_k=2,
            shadow_outcome_sink=controller,
            shadow_emit_transition_summary=True,
            shadow_outcome_logging_mode="off",
            shadow_num_experts=6,
            request_id="req",
            sequence_id=0,
            token_offset=0,
        )
        recorder.record_topk(
            layer_id=1,
            topk_ids=torch.tensor([[1, 2], [2, 3]]),
            topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
        )

    rows = read_shadow_jsonl(path)
    assert [row["event_type"] for row in rows] == ["outcome", "summary", "outcome"]
    assert rows[2]["join_status"] == "joined"


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


def test_vllm_router_recorder_descriptor_min_summary_records_gate_decision():
    sink = _Sink()
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=3),
            TileRequest(0, 1, 1, 1, layer_idx=3),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    gate = DescriptorOrderRuntimeGate(
        policy="layer_prior_frequency",
        execution_mode="two_level_group_plan",
        tile_elems=(1024,),
        groups_per_cta=(8,),
        devices=(0,),
        diagnostic_groups_per_cta=(16,),
        disable_groups_per_cta_min=64,
        prior_id="prior-test",
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prior_id="prior-test",
        shadow_descriptor_order_prior_hash="hash-test",
        shadow_descriptor_order_metrics_mode="count_only",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_runtime_gate=gate,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_device=0,
        request_id="req",
        sequence_id=0,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 3]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
    )

    assert len(sink.events) == 1
    row = sink.events[0].as_dict()
    assert row["event_type"] == "descriptor_summary_min"
    assert row["descriptor_order_execution_mode"] == "two_level_group_plan"
    assert row["descriptor_group_plan_groups_per_cta"] == 8
    assert row["descriptor_order_gate_allow"] is False
    assert row["descriptor_order_gate_reason"] == "same_multiset_missing"
    assert row["descriptor_order_gate_tile_elems"] == 1024
    assert row["descriptor_order_gate_device"] == 0


def test_vllm_router_recorder_descriptor_min_summary_uses_consumer_evidence():
    sink = _Sink()
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=3),
            TileRequest(0, 1, 1, 1, layer_idx=3),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    gate = DescriptorOrderRuntimeGate(
        policy="layer_prior_frequency",
        execution_mode="two_level_group_plan",
        tile_elems=(1024,),
        groups_per_cta=(8,),
        devices=(0,),
        diagnostic_groups_per_cta=(16,),
        disable_groups_per_cta_min=64,
        prior_id="prior-test",
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prior_id="prior-test",
        shadow_descriptor_order_prior_hash="hash-test",
        shadow_descriptor_order_metrics_mode="count_only",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_runtime_gate=gate,
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
        shadow_descriptor_order_evidence_cache_flush_elems=0,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_device=0,
        request_id="req",
        sequence_id=0,
    )

    recorder.record_topk(
        layer_id=3,
        topk_ids=torch.tensor([[1, 2], [2, 3]]),
        topk_weights=torch.tensor([[0.8, 0.2], [0.7, 0.3]]),
    )

    row = sink.events[0].as_dict()
    assert row["descriptor_order_gate_allow"] is True
    assert row["descriptor_order_gate_reason"] == "allowed"
    assert row["descriptor_order_gate_evidence_found"] is True
    assert row["descriptor_order_gate_checksum_delta"] == 0.0
    assert row["descriptor_order_gate_speedup_median_vs_no_order"] == pytest.approx(1.2)


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
            shadow_descriptor_order_token_window_size=1,
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
    assert summary["descriptor_order_metrics"]["window_count"] == 2
    assert summary["descriptor_same_multiset"] is True
    assert summary["descriptor_order_changed"] is True
    assert summary["candidate_construction_us"] >= 0.0
    assert summary["descriptor_order_build_us"] >= 0.0
    assert summary["decision_us"] >= summary["candidate_construction_us"]
    assert aggregate["descriptor_order_summary_count"] == 1
    assert aggregate["controller_stats"]["written_summary_count"] == 1


def test_vllm_router_recorder_emits_descriptor_order_min_summary(tmp_path):
    path = tmp_path / "descriptor_order_min_shadow.jsonl"
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
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
            shadow_descriptor_order_metrics_mode="count_only",
            shadow_descriptor_order_event_mode="minimal",
            shadow_descriptor_order_execution_mode="two_level_group_plan",
            shadow_descriptor_order_groups_per_cta=4,
            shadow_descriptor_order_token_window_size=1,
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
    assert [row["event_type"] for row in rows] == [
        "outcome",
        "outcome",
        "descriptor_summary_min",
    ]
    summary = rows[-1]
    assert summary["shadow_event_id"] == "req:0:-1:0"
    assert summary["descriptor_order_policy"] == "layer_prior_frequency"
    assert summary["descriptor_order_metrics_mode"] == "count_only"
    assert summary["descriptor_order_prior_hash"] == prior_hash
    assert summary["descriptor_tile_request_count"] == 4
    assert summary["descriptor_unique_b_tiles"] == 3
    assert summary["descriptor_window_count"] == 2
    assert summary["descriptor_order_execution_mode"] == "two_level_group_plan"
    assert summary["descriptor_group_plan_groups_per_cta"] == 4
    assert summary["descriptor_group_plan_group_count"] == 4
    assert summary["descriptor_group_plan_avg_group_size"] == 1.0
    assert summary["descriptor_group_plan_p95_group_size"] == 1.0
    assert summary["descriptor_group_plan_max_group_size"] == 1
    assert summary["descriptor_group_plan_cta_count"] == 1
    assert "descriptor_order_metrics" not in summary
    assert "full_fetch_count" not in summary
    assert aggregate["descriptor_summary_min_count"] == 1
    assert aggregate["descriptor_order_summary_count"] == 1


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
