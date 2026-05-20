from __future__ import annotations

import torch

from mtp_expert_prefetch.runtime import TileRequest, build_layer_tile_prior
from mtp_expert_prefetch.runtime.descriptor_order_gate import (
    DescriptorOrderExecutionEvidence,
    DescriptorOrderRuntimeGate,
)
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    VllmRouterRecorder,
    _load_runtime_shadow_descriptor_order_layer_allowlist,
    get_active_moe_assignment_context,
    set_active_moe_assignment_context,
)


class _DescriptorMinSink:
    def __init__(self) -> None:
        self.events = []
        self.timing_events = []

    def write_descriptor_order_min_summary(self, event) -> None:
        self.events.append(event)

    def write_descriptor_layer_timing(self, event) -> None:
        self.timing_events.append(event)


def test_descriptor_order_layer_allowlist_artifact_loader(tmp_path) -> None:
    artifact = tmp_path / "allowlist.yaml"
    artifact.write_text(
        "\n".join(
            [
                "id: test-allowlist",
                "source_max_tokens: 2",
                "source_split:",
                "  sample_start: 0",
                "  sample_count: 128",
                "threshold:",
                "  criterion: test",
                "evidence_paths:",
                "  heldout: outputs/example",
                "layers: [1, 3, 5]",
            ]
        ),
        encoding="utf-8",
    )

    layers, metadata = _load_runtime_shadow_descriptor_order_layer_allowlist(
        options={
            "descriptor_order_reorder_mvp_layer_allowlist_artifact_path": artifact,
            "descriptor_order_reorder_mvp_layer_allowlist": [1, 3, 5],
        },
        project_root=tmp_path,
    )

    assert layers == (1, 3, 5)
    assert metadata is not None
    assert metadata["id"] == "test-allowlist"
    assert metadata["source_max_tokens"] == 2
    assert metadata["hash"]
    assert metadata["evidence_paths"] == {"heldout": "outputs/example"}


def test_vllm_recorder_writes_engine_substage_timing() -> None:
    sink = _DescriptorMinSink()
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_emit_engine_timing=True,
        request_id="req",
        sequence_id=7,
    )

    recorder.write_engine_substage_timing(
        substage="engine_sampler_forward",
        elapsed_us=12.5,
    )

    assert len(sink.timing_events) == 1
    event = sink.timing_events[0]
    assert event["event_type"] == "engine_substage_timing"
    assert event["shadow_event_id"] == "req:7:-1:-1"
    assert event["engine_substage"] == "engine_sampler_forward"
    assert event["engine_substage_elapsed_us"] == 12.5


def test_vllm_recorder_suppresses_engine_substage_timing_by_default() -> None:
    sink = _DescriptorMinSink()
    recorder = VllmRouterRecorder(top_k=2, shadow_outcome_sink=sink)

    recorder.write_engine_substage_timing(
        substage="engine_sampler_forward",
        elapsed_us=12.5,
    )

    assert sink.timing_events == []


def test_descriptor_order_layer_allowlist_artifact_rejects_mismatch(tmp_path) -> None:
    artifact = tmp_path / "allowlist.yaml"
    artifact.write_text("layers: [1, 3, 5]\n", encoding="utf-8")

    try:
        _load_runtime_shadow_descriptor_order_layer_allowlist(
            options={
                "descriptor_order_reorder_mvp_layer_allowlist_artifact_path": artifact,
                "descriptor_order_reorder_mvp_layer_allowlist": [1, 2, 5],
            },
            project_root=tmp_path,
        )
    except ValueError as exc:
        assert "does not match artifact layers" in str(exc)
    else:
        raise AssertionError("expected mismatched inline/artifact allowlist to fail")


def test_vllm_recorder_wna16_runtime_override_preserves_dynamic_nk() -> None:
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={
            "BLOCK_SIZE_M": 32,
            "GROUP_SIZE_M": 4,
            "SPLIT_K": 1,
            "num_warps": 2,
            "num_stages": 3,
        },
        shadow_wna16_config_override_preserve_dynamic_nk=True,
    )

    patched = recorder.apply_wna16_runtime_config_override(
        {
            "BLOCK_SIZE_M": 16,
            "GROUP_SIZE_M": 1,
            "SPLIT_K": 1,
            "BLOCK_SIZE_N": 64,
            "BLOCK_SIZE_K": 32,
        },
        num_tokens=1,
        top_k=8,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )

    assert patched["BLOCK_SIZE_M"] == 32
    assert patched["GROUP_SIZE_M"] == 4
    assert patched["SPLIT_K"] == 1
    assert patched["num_warps"] == 2
    assert patched["num_stages"] == 3
    assert patched["BLOCK_SIZE_N"] == 64
    assert patched["BLOCK_SIZE_K"] == 32


def test_vllm_recorder_wna16_runtime_override_can_keep_existing_nk() -> None:
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_M": 32},
        shadow_wna16_config_override_preserve_dynamic_nk=False,
    )

    patched = recorder.apply_wna16_runtime_config_override(
        {"BLOCK_SIZE_M": 16, "BLOCK_SIZE_N": 64, "BLOCK_SIZE_K": 32},
        num_tokens=1,
        top_k=8,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )

    assert patched["BLOCK_SIZE_M"] == 32
    assert patched["BLOCK_SIZE_N"] == 64
    assert patched["BLOCK_SIZE_K"] == 32


def test_vllm_recorder_wna16_runtime_override_rejects_nk_override() -> None:
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_N": 64},
    )

    try:
        recorder.apply_wna16_runtime_config_override(
            {"BLOCK_SIZE_M": 16},
            num_tokens=1,
            top_k=8,
            use_int4_w4a16=True,
            block_shape=[0, 128],
        )
    except ValueError as exc:
        assert "Unsupported WNA16 runtime override keys" in str(exc)
        assert "BLOCK_SIZE_N" in str(exc)
    else:
        raise AssertionError("expected BLOCK_SIZE_N override to fail fast")


def test_vllm_recorder_wna16_runtime_override_can_skip_prefill_shape() -> None:
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_M": 32},
        shadow_wna16_config_override_max_tokens=8,
    )
    config = {"BLOCK_SIZE_M": 16, "GROUP_SIZE_M": 1}

    patched = recorder.apply_wna16_runtime_config_override(config, num_tokens=128)

    assert patched is config
    assert patched["BLOCK_SIZE_M"] == 16


def test_vllm_recorder_wna16_runtime_override_requires_awq_decode_shape() -> None:
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_M": 32},
        shadow_wna16_config_override_max_tokens=8,
        shadow_wna16_config_override_route_product=8,
    )
    config = {"BLOCK_SIZE_M": 16, "GROUP_SIZE_M": 1}

    w1 = recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=1,
        top_k=8,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )
    w2 = recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=8,
        top_k=1,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )
    wrong_route = recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=4,
        top_k=8,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )
    wrong_quant = recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=1,
        top_k=8,
        use_int4_w4a16=False,
        use_int8_w8a16=False,
        block_shape=[0, 128],
    )

    assert w1["BLOCK_SIZE_M"] == 32
    assert w2["BLOCK_SIZE_M"] == 32
    assert wrong_route is config
    assert wrong_quant is config


def test_vllm_recorder_wna16_runtime_override_target_top_k_requires_top_k() -> None:
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_M": 32},
        shadow_wna16_config_override_target_top_k=8,
    )
    config = {"BLOCK_SIZE_M": 16, "GROUP_SIZE_M": 1}

    patched = recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=1,
        top_k=None,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )

    assert patched is config


def test_vllm_recorder_wna16_runtime_override_can_target_w1_or_w2() -> None:
    config = {"BLOCK_SIZE_M": 16, "GROUP_SIZE_M": 1}
    w1_recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_M": 32},
        shadow_wna16_config_override_target_top_k=8,
    )
    w2_recorder = VllmRouterRecorder(
        top_k=2,
        shadow_wna16_config_override={"BLOCK_SIZE_M": 64},
        shadow_wna16_config_override_target_top_k=1,
    )

    w1_hit = w1_recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=1,
        top_k=8,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )
    w1_skip = w1_recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=8,
        top_k=1,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )
    w2_hit = w2_recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=8,
        top_k=1,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )
    w2_skip = w2_recorder.apply_wna16_runtime_config_override(
        config,
        num_tokens=1,
        top_k=8,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )

    assert w1_hit["BLOCK_SIZE_M"] == 32
    assert w1_skip is config
    assert w2_hit["BLOCK_SIZE_M"] == 64
    assert w2_skip is config


def test_vllm_recorder_writes_wna16_kernel_timing_event() -> None:
    sink = _DescriptorMinSink()
    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_outcome_sink=sink,
        request_id="req",
        sequence_id=3,
        shadow_emit_wna16_kernel_timing=True,
    )

    recorder.write_wna16_kernel_timing(
        layer_id=4,
        elapsed_us=12.5,
        gpu_elapsed_us=10.0,
        num_tokens=1,
        top_k=8,
        config={
            "BLOCK_SIZE_M": 16,
            "BLOCK_SIZE_N": 64,
            "BLOCK_SIZE_K": 32,
            "GROUP_SIZE_M": 1,
            "SPLIT_K": 1,
            "num_warps": 2,
            "num_stages": 2,
        },
        override_applied=True,
        variant="original",
        status="ok",
        use_int8_w8a16=False,
        use_int4_w4a16=True,
        block_shape=[0, 128],
    )

    assert len(sink.timing_events) == 1
    payload = sink.timing_events[0]
    assert payload["event_type"] == "wna16_kernel_timing"
    assert payload["wna16_bucket"] == "w1"
    assert payload["wna16_kernel_elapsed_us"] == 12.5
    assert payload["wna16_kernel_gpu_elapsed_us"] == 10.0
    assert payload["wna16_kernel_timing_mode"] == "host"
    assert payload["wna16_kernel_timing_kind"] == "gpu_event_synchronized"
    assert payload["wna16_config_override_applied"] is True
    assert payload["wna16_route_product"] == 8
    assert payload["wna16_block_size_n"] == 64
    assert payload["layer"] == 4


def test_vllm_recorder_emits_noop_descriptor_mapping_assertion() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
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
            TileRequest(0, 1, 2, 2, layer_idx=0),
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


def test_vllm_recorder_emits_prelaunch_assertion_against_router_mapping() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
            TileRequest(0, 2, 3, 3, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []

    def write_descriptor_prelaunch_assertion(event) -> None:
        sink.prelaunch_events.append(event)

    sink.write_descriptor_prelaunch_assertion = write_descriptor_prelaunch_assertion
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_outcome_logging_mode="off",
        shadow_emit_descriptor_order_summary=True,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_metrics_mode="none",
        shadow_descriptor_order_event_mode="minimal",
        shadow_descriptor_order_mapping_assertion_mode="router_topk_tile_stream",
        shadow_descriptor_order_prelaunch_assertion_mode="moe_runner_prelaunch_topk",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_token_window_size=1,
    )
    topk_ids = torch.tensor([[1, 2], [2, 3]], dtype=torch.long)

    recorder.record_topk(
        layer_id=0,
        topk_ids=topk_ids,
        topk_weights=torch.tensor([[0.4, 0.6], [0.7, 0.3]], dtype=torch.float32),
    )
    recorder.write_prelaunch_descriptor_assertion(layer_id=0, topk_ids=topk_ids)

    assert len(sink.prelaunch_events) == 1
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["event_type"] == "descriptor_prelaunch_assertion"
    assert payload["descriptor_order_prelaunch_same_multiset"] is True
    assert payload["descriptor_order_prelaunch_counts_match"] is True
    assert (
        payload["descriptor_order_prelaunch_tile_multiset_hash"]
        == payload["descriptor_order_prelaunch_router_derived_tile_multiset_hash"]
    )
    assert payload["descriptor_order_reorder_mvp_requested"] is True
    assert payload["descriptor_order_reorder_mvp_selected_policy"] == "no_order"
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == "gate_missing"
    assert "descriptor_order_prelaunch_error" not in payload


def test_vllm_recorder_records_consumer_handle_noop_assertion() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="dry_run",
    )

    sorted_token_ids, expert_ids, num_post = (
        recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=0,
            sorted_token_ids=torch.arange(8, dtype=torch.int32),
            expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
            num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
            block_size=2,
        )
    )

    assert sorted_token_ids.tolist() == list(range(8))
    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert num_post.tolist() == [8]
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_consumer_handle_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert payload["descriptor_order_consumer_handle_available"] is True
    assert payload["descriptor_order_consumer_handle_block_count"] == 4
    assert payload["descriptor_order_consumer_handle_block_size"] == 2
    assert payload["descriptor_order_consumer_handle_would_reorder"] is True
    assert payload["descriptor_order_consumer_handle_same_multiset"] is True
    assert payload["descriptor_order_consumer_handle_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == "gate_missing"


def test_vllm_recorder_applies_gated_consumer_handle_reorder() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_require_profitable=True,
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )

    sorted_token_ids, expert_ids, _ = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.arange(8, dtype=torch.int32),
        expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
        block_size=2,
    )

    assert expert_ids.tolist() == [2, 2, 1, 1]
    assert sorted_token_ids.tolist() == [4, 5, 6, 7, 0, 1, 2, 3]
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_gate_allow"] is True
    assert payload["descriptor_order_reorder_mvp_selected_policy"] == (
        "layer_prior_frequency_two_level"
    )
    assert payload["descriptor_order_reorder_mvp_applied"] is True
    assert payload["descriptor_order_consumer_handle_applied"] is True
    assert payload["descriptor_order_consumer_handle_attribution_mode"] == "full"
    assert "descriptor_order_reorder_mvp_fallback_reason" not in payload


def test_vllm_recorder_attribution_mode_does_not_apply_reorder() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="index_select_only",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )

    sorted_token_ids, expert_ids, _ = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.arange(8, dtype=torch.int32),
        expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
        block_size=2,
    )

    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_gate_allow"] is True
    assert payload["descriptor_order_consumer_handle_attribution_mode"] == (
        "index_select_only"
    )
    assert payload["descriptor_order_consumer_handle_applied"] is False
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == (
        "attribution_index_select_only"
    )
    assert "descriptor_order_consumer_handle_index_select_us" in payload


def test_vllm_recorder_indirect_plan_attribution_does_not_materialize_reorder() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="indirect_plan_only",
        shadow_descriptor_order_groups_per_cta=2,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(2,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 2, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )

    sorted_token_ids, expert_ids, _ = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.arange(12, dtype=torch.int32),
        expert_ids=torch.tensor([1, 2, 1, 2, 3, 3], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([12], dtype=torch.int32),
        block_size=2,
    )

    assert expert_ids.tolist() == [1, 2, 1, 2, 3, 3]
    assert sorted_token_ids.tolist() == list(range(12))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_gate_allow"] is True
    assert payload["descriptor_order_consumer_handle_attribution_mode"] == (
        "indirect_plan_only"
    )
    assert payload["descriptor_order_consumer_handle_applied"] is False
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == (
        "attribution_indirect_plan_only"
    )
    assert payload["descriptor_order_consumer_handle_plan_group_count"] == 3
    assert payload["descriptor_order_consumer_handle_plan_max_group_size"] == 2
    assert payload["descriptor_order_consumer_handle_plan_cta_count"] == 2
    assert "descriptor_order_consumer_handle_plan_build_us" in payload
    assert "descriptor_order_consumer_handle_plan_group_order_hash" in payload
    assert "descriptor_order_consumer_handle_plan_group_offsets_hash" in payload
    assert "descriptor_order_consumer_handle_clone_us" not in payload
    assert "descriptor_order_consumer_handle_index_select_us" not in payload


def test_vllm_recorder_builds_source_block_ids_kernel_plan() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="source_block_ids_kernel",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    set_active_moe_assignment_context({"recorder": recorder, "layer_id": 0})
    try:
        sorted_token_ids, expert_ids, _ = (
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=0,
                sorted_token_ids=torch.arange(8, dtype=torch.int32),
                expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
                num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
                block_size=2,
            )
        )
        context = get_active_moe_assignment_context()
        assert context is not None
        plan = context["descriptor_order_wna16_indirect_plan"]
    finally:
        set_active_moe_assignment_context(None)

    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    assert plan["variant"] == "source_block_ids"
    assert plan["source_block_ids"].cpu().tolist() == [2, 3, 0, 1]
    assert plan["source_block_ids_packed"] is False
    assert plan["source_block_count"] == 4
    assert plan["active_block_count"] == 4
    assert "packed_source_block_ids" not in plan
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_selected_policy"] == (
        "layer_prior_frequency_source_block_ids_kernel"
    )
    assert payload["descriptor_order_reorder_mvp_applied"] is True
    assert payload["descriptor_order_consumer_handle_applied"] is True


def test_vllm_recorder_builds_packed_source_block_ids_kernel_plan() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode=(
            "source_block_ids_packed_kernel"
        ),
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    set_active_moe_assignment_context({"recorder": recorder, "layer_id": 0})
    try:
        recorder.maybe_reorder_prepared_expert_assignment(
            layer_id=0,
            sorted_token_ids=torch.arange(8, dtype=torch.int32),
            expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
            num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
            block_size=2,
        )
        context = get_active_moe_assignment_context()
        assert context is not None
        plan = context["descriptor_order_wna16_indirect_plan"]
    finally:
        set_active_moe_assignment_context(None)

    assert plan["source_block_ids"].cpu().tolist() == [2, 3, 0, 1]
    assert plan["source_block_ids_packed"] is True
    assert plan["source_block_count"] == 4
    assert plan["active_block_count"] == 4
    assert plan["packed_source_block_ids"].cpu().tolist() == [
        (2 << 10) | 2,
        (3 << 10) | 2,
        (0 << 10) | 1,
        (1 << 10) | 1,
    ]


def test_vllm_recorder_builds_two_level_group_plan_kernel_plan() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
            TileRequest(0, 3, 3, 3, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="group_plan_kernel",
        shadow_descriptor_order_groups_per_cta=2,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(2,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 2, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    set_active_moe_assignment_context({"recorder": recorder, "layer_id": 0})
    try:
        sorted_token_ids, expert_ids, _ = (
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=0,
                sorted_token_ids=torch.arange(12, dtype=torch.int32),
                expert_ids=torch.tensor([1, 1, 2, 2, 3, 3], dtype=torch.int32),
                num_tokens_post_padded=torch.tensor([12], dtype=torch.int32),
                block_size=2,
            )
        )
        context = get_active_moe_assignment_context()
        assert context is not None
        plan = context["descriptor_order_wna16_indirect_plan"]
    finally:
        set_active_moe_assignment_context(None)

    assert expert_ids.tolist() == [1, 1, 2, 2, 3, 3]
    assert sorted_token_ids.tolist() == list(range(12))
    assert plan["variant"] == "group_plan"
    assert plan["group_order"].cpu().tolist() == [2, 1, 3]
    assert plan["group_offsets"].cpu().tolist() == [0, 2, 4, 6]
    assert plan["group_source_starts"].cpu().tolist() == [2, 0, 4]
    assert plan["max_group_blocks"] == 2
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_selected_policy"] == (
        "layer_prior_frequency_group_plan_kernel"
    )
    assert payload["descriptor_order_reorder_mvp_applied"] is True
    assert payload["descriptor_order_consumer_handle_plan_group_count"] == 3
    assert payload["descriptor_order_consumer_handle_plan_cta_count"] == 2


def test_vllm_recorder_fused_decode_producer_orders_by_prior() -> None:
    if not torch.cuda.is_available():
        return
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
            TileRequest(0, 2, 3, 3, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=3,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="fused_producer",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )

    prepared = recorder.maybe_prepare_decode_expert_assignment_layer_prior(
        layer_id=0,
        topk_ids=torch.tensor([[1, 2, 3]], dtype=torch.int32, device="cuda"),
        config={"BLOCK_SIZE_M": 4},
        num_tokens=1,
        top_k_num=3,
        global_num_experts=8,
        expert_map=None,
        use_int8_w8a16=False,
        use_int4_w4a16=True,
        block_shape=[0, 128],
        ignore_invalid_experts=False,
    )

    assert prepared is not None
    sorted_token_ids, expert_ids, num_tokens_post_padded = prepared
    assert expert_ids.cpu().tolist() == [2, 1, 3]
    assert num_tokens_post_padded.cpu().tolist() == [12]
    assert sorted_token_ids.cpu().view(3, 4).tolist() == [
        [1, 3, 3, 3],
        [0, 3, 3, 3],
        [2, 3, 3, 3],
    ]
    handle = recorder._last_descriptor_consumer_handle_by_layer[0]
    assert handle["selected_policy"] == "layer_prior_frequency_fused_producer"
    assert handle["applied"] is True


def test_vllm_recorder_fused_decode_producer_filters_invalid_expert_map() -> None:
    if not torch.cuda.is_available():
        return
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
            TileRequest(0, 3, 3, 3, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=3,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="fused_producer",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )

    prepared = recorder.maybe_prepare_decode_expert_assignment_layer_prior(
        layer_id=0,
        topk_ids=torch.tensor([[1, 2, 3]], dtype=torch.int32, device="cuda"),
        config={"BLOCK_SIZE_M": 4},
        num_tokens=1,
        top_k_num=3,
        global_num_experts=8,
        expert_map=torch.tensor(
            [0, 1, -1, 3, 4, 5, 6, 7],
            dtype=torch.int32,
            device="cuda",
        ),
        use_int8_w8a16=False,
        use_int4_w4a16=True,
        block_shape=[0, 128],
        ignore_invalid_experts=True,
    )

    assert prepared is not None
    sorted_token_ids, expert_ids, num_tokens_post_padded = prepared
    assert expert_ids.cpu().tolist()[:2] == [1, 3]
    assert num_tokens_post_padded.cpu().tolist() == [8]
    assert sorted_token_ids.cpu()[:8].view(2, 4).tolist() == [
        [0, 3, 3, 3],
        [2, 3, 3, 3],
    ]
    handle = recorder._last_descriptor_consumer_handle_by_layer[0]
    assert handle["block_count"] == 2
    assert handle["plan_group_count"] == 2
    assert handle["fallback_reason"] is None


def test_vllm_recorder_fused_decode_producer_filters_positive_oob_expert() -> None:
    if not torch.cuda.is_available():
        return
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=3,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="fused_producer",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )

    prepared = recorder.maybe_prepare_decode_expert_assignment_layer_prior(
        layer_id=0,
        topk_ids=torch.tensor([[1, 9, 2]], dtype=torch.int32, device="cuda"),
        config={"BLOCK_SIZE_M": 4},
        num_tokens=1,
        top_k_num=3,
        global_num_experts=8,
        expert_map=None,
        use_int8_w8a16=False,
        use_int4_w4a16=True,
        block_shape=[0, 128],
        ignore_invalid_experts=False,
    )

    assert prepared is not None
    sorted_token_ids, expert_ids, num_tokens_post_padded = prepared
    assert expert_ids.cpu().tolist()[:2] == [2, 1]
    assert num_tokens_post_padded.cpu().tolist() == [8]
    assert sorted_token_ids.cpu()[:8].view(2, 4).tolist() == [
        [2, 3, 3, 3],
        [0, 3, 3, 3],
    ]
    handle = recorder._last_descriptor_consumer_handle_by_layer[0]
    assert handle["block_count"] == 2
    assert handle["plan_group_count"] == 2


def test_vllm_recorder_direct_topk_sets_indirect_launch_plan() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
            TileRequest(0, 3, 3, 3, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=3,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="direct_topk_kernel",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    context = {"recorder": recorder, "layer_id": 0}
    set_active_moe_assignment_context(context)
    try:
        prepared = recorder.maybe_prepare_decode_expert_assignment_layer_prior(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2, 3]], dtype=torch.int32),
            config={"BLOCK_SIZE_M": 4},
            num_tokens=1,
            top_k_num=3,
            global_num_experts=8,
            expert_map=None,
            use_int8_w8a16=False,
            use_int4_w4a16=True,
            block_shape=[0, 128],
            ignore_invalid_experts=False,
        )
    finally:
        set_active_moe_assignment_context(None)

    assert prepared is not None
    sorted_token_ids, expert_ids, num_tokens_post_padded = prepared
    assert sorted_token_ids.numel() == 12
    assert expert_ids.numel() == 3
    assert num_tokens_post_padded.numel() == 1
    plan = context["descriptor_order_wna16_indirect_plan"]
    assert plan["variant"] == "direct_topk_layer_prior"
    assert plan["topk_ids"].tolist() == [[1, 2, 3]]
    assert plan["prior_rank"].shape == (8,)
    handle = recorder._last_descriptor_consumer_handle_by_layer[0]
    assert handle["source"] == "direct_topk_layer_prior_consumer"
    assert handle["selected_policy"] == "layer_prior_frequency_direct_topk_kernel"
    assert handle["applied"] is True


def test_vllm_recorder_direct_topk_identity_sets_plan_without_prior() -> None:
    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_descriptor_order_prior=None,
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="direct_topk_identity_kernel",
    )
    context = {"recorder": recorder, "layer_id": 0}
    set_active_moe_assignment_context(context)
    try:
        prepared = recorder.maybe_prepare_decode_expert_assignment_layer_prior(
            layer_id=0,
            topk_ids=torch.tensor([[7, 3, 2, 5, 4, 1, 0, 6]], dtype=torch.int32),
            config={"BLOCK_SIZE_M": 4},
            num_tokens=1,
            top_k_num=8,
            global_num_experts=8,
            expert_map=None,
            use_int8_w8a16=False,
            use_int4_w4a16=True,
            block_shape=[0, 128],
            ignore_invalid_experts=False,
        )
    finally:
        set_active_moe_assignment_context(None)

    assert prepared is not None
    sorted_token_ids, expert_ids, num_tokens_post_padded = prepared
    assert sorted_token_ids.numel() == 32
    assert expert_ids.numel() == 8
    assert num_tokens_post_padded.numel() == 1
    plan = context["descriptor_order_wna16_indirect_plan"]
    assert plan["variant"] == "direct_topk_identity"
    assert plan["topk_ids"].tolist() == [[7, 3, 2, 5, 4, 1, 0, 6]]
    assert "prior_rank" not in plan
    handle = recorder._last_descriptor_consumer_handle_by_layer[0]
    assert handle["source"] == "direct_topk_identity_consumer"
    assert handle["selected_policy"] == "direct_topk_identity_kernel"
    assert handle["would_reorder"] is False
    assert handle["gate_reason"] == "identity_no_reorder"
    assert handle["applied"] is True


def test_vllm_recorder_direct_topk_respects_layer_allowlist() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="direct_topk_kernel",
        shadow_descriptor_order_reorder_mvp_layer_allowlist=(1,),
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    context = {"recorder": recorder, "layer_id": 0}
    set_active_moe_assignment_context(context)
    try:
        prepared = recorder.maybe_prepare_decode_expert_assignment_layer_prior(
            layer_id=0,
            topk_ids=torch.tensor([[1, 2]], dtype=torch.int32),
            config={"BLOCK_SIZE_M": 4},
            num_tokens=1,
            top_k_num=2,
            global_num_experts=8,
            expert_map=None,
            use_int8_w8a16=False,
            use_int4_w4a16=True,
            block_shape=[0, 128],
            ignore_invalid_experts=False,
        )
    finally:
        set_active_moe_assignment_context(None)

    assert prepared is None
    assert context["descriptor_order_fused_producer_skip_reason"] == (
        "layer_not_allowed"
    )
    assert 0 not in recorder._last_descriptor_consumer_handle_by_layer


def test_vllm_recorder_source_block_kernel_requires_active_context() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="source_block_ids_kernel",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    set_active_moe_assignment_context(None)

    sorted_token_ids, expert_ids, _ = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.arange(8, dtype=torch.int32),
        expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
        block_size=2,
    )

    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == (
        "missing_assignment_context"
    )


def test_vllm_recorder_source_block_kernel_rejects_block_count_mismatch() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="source_block_ids_kernel",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    recorder._descriptor_order_expert_block_permutation = (  # type: ignore[method-assign]
        lambda *, layer_id, expert_ids: [0, 1]
    )
    set_active_moe_assignment_context({"recorder": recorder, "layer_id": 0})
    try:
        sorted_token_ids, expert_ids, _ = (
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=0,
                sorted_token_ids=torch.arange(8, dtype=torch.int32),
                expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
                num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
                block_size=2,
            )
        )
        context = get_active_moe_assignment_context()
        assert context is not None
        assert "descriptor_order_wna16_indirect_plan" not in context
    finally:
        set_active_moe_assignment_context(None)

    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == (
        "consumer_handle_source_block_count_mismatch"
    )


def test_vllm_recorder_rejects_permutation_index_oob() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="source_block_ids_kernel",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    recorder._descriptor_order_expert_block_permutation = (  # type: ignore[method-assign]
        lambda *, layer_id, expert_ids: [0, 1, 2, 9]
    )
    set_active_moe_assignment_context({"recorder": recorder, "layer_id": 0})
    try:
        sorted_token_ids, expert_ids, _ = (
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=0,
                sorted_token_ids=torch.arange(8, dtype=torch.int32),
                expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
                num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
                block_size=2,
            )
        )
        context = get_active_moe_assignment_context()
        assert context is not None
        assert "descriptor_order_wna16_indirect_plan" not in context
    finally:
        set_active_moe_assignment_context(None)

    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == (
        "consumer_handle_permutation_index_oob"
    )


def test_vllm_recorder_group_plan_kernel_rejects_noncontiguous_blocks() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_attribution_mode="group_plan_kernel",
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=1.2,
            )
        },
    )
    set_active_moe_assignment_context({"recorder": recorder, "layer_id": 0})
    try:
        sorted_token_ids, expert_ids, _ = (
            recorder.maybe_reorder_prepared_expert_assignment(
                layer_id=0,
                sorted_token_ids=torch.arange(8, dtype=torch.int32),
                expert_ids=torch.tensor([1, 2, 1, 2], dtype=torch.int32),
                num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
                block_size=2,
            )
        )
        context = get_active_moe_assignment_context()
        assert context is not None
        assert "descriptor_order_wna16_indirect_plan" not in context
    finally:
        set_active_moe_assignment_context(None)

    assert expert_ids.tolist() == [1, 2, 1, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == (
        "consumer_handle_noncontiguous_expert_blocks"
    )


def test_vllm_recorder_rejects_unprofitable_consumer_handle_reorder() -> None:
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-test"},
    )
    sink = _DescriptorMinSink()
    sink.prelaunch_events = []
    sink.write_descriptor_prelaunch_assertion = sink.prelaunch_events.append
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_outcome_sink=sink,
        shadow_descriptor_order_prior=prior,
        shadow_descriptor_order_prelaunch_assertion_mode="consumer_handle",
        shadow_descriptor_order_reorder_mvp_enabled=True,
        shadow_descriptor_order_reorder_mvp_apply_mode="apply",
        shadow_descriptor_order_reorder_mvp_require_profitable=True,
        shadow_descriptor_order_groups_per_cta=8,
        shadow_descriptor_order_tile_elems=1024,
        shadow_descriptor_order_device=0,
        shadow_descriptor_order_runtime_gate=DescriptorOrderRuntimeGate(
            policy="layer_prior_frequency",
            execution_mode="two_level_group_plan",
            tile_elems=(1024,),
            groups_per_cta=(8,),
            devices=(0,),
            diagnostic_groups_per_cta=(),
            disable_groups_per_cta_min=None,
            checksum_delta_required=0.0,
        ),
        shadow_descriptor_order_evidence={
            (0, 1024, 8, 0): DescriptorOrderExecutionEvidence(
                source_policy="layer_prior_frequency_two_level",
                same_multiset=True,
                checksum_delta=0.0,
                speedup_median_vs_no_order=0.9,
            )
        },
    )

    sorted_token_ids, expert_ids, _ = recorder.maybe_reorder_prepared_expert_assignment(
        layer_id=0,
        sorted_token_ids=torch.arange(8, dtype=torch.int32),
        expert_ids=torch.tensor([1, 1, 2, 2], dtype=torch.int32),
        num_tokens_post_padded=torch.tensor([8], dtype=torch.int32),
        block_size=2,
    )

    assert expert_ids.tolist() == [1, 1, 2, 2]
    assert sorted_token_ids.tolist() == list(range(8))
    payload = sink.prelaunch_events[0].as_dict()
    assert payload["descriptor_order_reorder_mvp_gate_allow"] is True
    assert payload["descriptor_order_consumer_handle_would_reorder"] is True
    assert payload["descriptor_order_consumer_handle_same_multiset"] is True
    assert payload["descriptor_order_consumer_handle_applied"] is False
    assert payload["descriptor_order_reorder_mvp_selected_policy"] == "no_order"
    assert payload["descriptor_order_reorder_mvp_applied"] is False
    assert payload["descriptor_order_reorder_mvp_fallback_reason"] == "not_profitable"
