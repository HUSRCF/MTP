from __future__ import annotations

import json
from types import SimpleNamespace

import torch

from mtp_expert_prefetch.tracing.vllm_router_trace import (
    VllmRouterRecorder,
    _moe_substage_allowed,
    _moe_source_timing_level,
    _shared_expert_source_timing_enabled,
    _write_vllm_sample_trace,
    vllm_routed_experts_to_router_topk,
)
from mtp_expert_prefetch.training.mtp_alignment import stack_backbone_router_topk


def test_vllm_routed_experts_to_router_topk_matches_alignment_shape():
    routed = torch.tensor(
        [
            [[1, 2, 3], [11, 12, 13]],
            [[4, 5, 6], [14, 15, 16]],
            [[7, 8, 9], [17, 18, 19]],
        ],
        dtype=torch.int16,
    )

    router_topk = vllm_routed_experts_to_router_topk(routed)

    assert sorted(router_topk) == [
        "model.language_model.layers.0.mlp.gate",
        "model.language_model.layers.1.mlp.gate",
    ]
    assert router_topk["model.language_model.layers.0.mlp.gate"][0] == [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]

    stacked, layer_ids = stack_backbone_router_topk({"router_topk": router_topk})

    assert stacked.shape == (2, 3, 3)
    assert torch.equal(layer_ids, torch.tensor([0, 1]))
    assert torch.equal(stacked[1, 2], torch.tensor([17, 18, 19]))


def test_vllm_router_recorder_payload_keeps_non_uniform_topk_weights():
    recorder = VllmRouterRecorder(top_k=2)
    recorder.record(
        layer_id=3,
        router_logits=torch.tensor(
            [
                [4.0, 1.0, 0.0, -1.0],
                [0.0, 3.0, 2.0, -2.0],
            ]
        ),
    )

    payload = recorder.to_payload(module_prefix="model.language_model")

    module_name = "model.language_model.layers.3.mlp.gate"
    assert sorted(payload["router_topk"]) == [module_name]
    topk = torch.as_tensor(payload["router_topk"][module_name][0])
    weights = torch.as_tensor(payload["router_weights"][module_name][0])

    assert topk.shape == (2, 2)
    assert weights.shape == (2, 2)
    assert torch.equal(topk[0], torch.tensor([0, 1]))
    assert torch.equal(topk[1], torch.tensor([1, 2]))
    assert float(weights.std()) > 0.0
    assert payload["router_call_meta"][0]["source"] == "vllm_router_logits_recorder"


def test_vllm_router_recorder_payload_keeps_same_token_oracle_topk():
    recorder = VllmRouterRecorder(top_k=2, capture_router_input_hidden=True)
    hidden = torch.randn(2, 4)
    logits = torch.tensor(
        [
            [4.0, 1.0, 0.0, -1.0],
            [0.0, 3.0, 2.0, -2.0],
        ]
    )
    weights = torch.softmax(logits, dim=-1)
    topk_weights, topk_ids = torch.topk(weights, k=2, dim=-1)

    recorder.record_topk(
        layer_id=5,
        topk_ids=topk_ids,
        topk_weights=topk_weights,
        oracle_router_logits=logits,
        router_input_hidden=hidden,
    )
    payload = recorder.to_payload(module_prefix="model.language_model")

    module_name = "model.language_model.layers.5.mlp.gate"
    assert torch.equal(
        torch.as_tensor(payload["router_oracle_topk"][module_name][0]),
        torch.as_tensor(payload["router_topk"][module_name][0]),
    )
    assert payload["router_oracle_summary"]["mean_exact_match_rate"] == 1.0
    assert payload["router_call_meta"][0]["has_router_input_hidden"]
    assert torch.as_tensor(payload["router_input_hidden"][module_name][0]).shape == (2, 4)


def test_no_topk_recorder_trace_writer_allows_empty_router_payload(tmp_path):
    recorder = VllmRouterRecorder(top_k=2, shadow_record_router_topk=False)
    recorder.record(
        layer_id=3,
        router_logits=torch.tensor(
            [
                [4.0, 1.0, 0.0, -1.0],
                [0.0, 3.0, 2.0, -2.0],
            ]
        ),
    )
    assert recorder.calls == []

    manifest_path = tmp_path / "manifest.jsonl"
    request_output = SimpleNamespace(
        outputs=[SimpleNamespace(text="decoded")],
    )

    with manifest_path.open("w", encoding="utf-8") as manifest:
        _write_vllm_sample_trace(
            manifest=manifest,
            output_dir=tmp_path,
            sample_idx=7,
            record={"id": "sample-7"},
            input_ids=[1, 2, 3],
            request_output=request_output,
            module_prefix="model.language_model",
            recorder=recorder,
        )

    row = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = torch.load(tmp_path / "sample_000007.pt", weights_only=False)
    assert row["trace_source"] == "vllm_router_logits_recorder_no_topk"
    assert row["num_router_calls"] == 0
    assert row["has_vllm_router_logits"] is False
    assert payload["trace_source"] == "vllm_router_logits_recorder_no_topk"
    assert payload["router_topk"] == {}
    assert payload["router_call_meta"] == []


def test_capture_only_router_topk_does_not_persist_heavy_payload(tmp_path):
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_record_router_topk=False,
        shadow_capture_router_topk=True,
    )
    recorder.record(
        layer_id=3,
        router_logits=torch.tensor(
            [
                [4.0, 1.0, 0.0, -1.0],
                [0.0, 3.0, 2.0, -2.0],
            ]
        ),
    )
    assert len(recorder.calls) == 1
    assert recorder.calls[0].oracle_topk_ids is None

    payload = recorder.to_payload(module_prefix="model.language_model")
    assert payload["router_topk"] == {}
    assert payload["router_weights"] == {}
    assert payload["router_call_meta"] == []

    manifest_path = tmp_path / "manifest.jsonl"
    request_output = SimpleNamespace(outputs=[SimpleNamespace(text="decoded")])
    with manifest_path.open("w", encoding="utf-8") as manifest:
        _write_vllm_sample_trace(
            manifest=manifest,
            output_dir=tmp_path,
            sample_idx=9,
            record={"id": "sample-9"},
            input_ids=[1, 2, 3],
            request_output=request_output,
            module_prefix="model.language_model",
            recorder=recorder,
        )

    row = json.loads(manifest_path.read_text(encoding="utf-8"))
    sample = torch.load(tmp_path / "sample_000009.pt", weights_only=False)
    assert row["trace_source"] == "vllm_router_topk_capture_only"
    assert row["has_vllm_router_logits"] is False
    assert row["has_vllm_router_topk_capture"] is True
    assert row["num_router_calls"] == 0
    assert sample["trace_source"] == "vllm_router_topk_capture_only"
    assert sample["router_topk"] == {}
    assert sample["router_call_meta"] == []


def test_shared_expert_source_timing_is_separate_from_fused_source_level():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
    )

    assert _moe_source_timing_level(recorder) == 0
    assert _shared_expert_source_timing_enabled(recorder) is True

    recorder.shadow_moe_source_timing_mode = "outer"
    assert _moe_source_timing_level(recorder) == 1
    assert _shared_expert_source_timing_enabled(recorder) is True

    recorder.shadow_moe_source_timing_mode = "off"
    assert _moe_source_timing_level(recorder) == 0
    assert _shared_expert_source_timing_enabled(recorder) is False

    recorder.shadow_moe_source_timing_mode = "shared"
    recorder.shadow_emit_moe_substage_timing = False
    assert _moe_source_timing_level(recorder) == 0
    assert _shared_expert_source_timing_enabled(recorder) is False


def test_shared_moe_source_mode_filters_non_shared_substages():
    recorder = VllmRouterRecorder(
        top_k=2,
        shadow_emit_decoder_layer_timing=True,
        shadow_emit_moe_substage_timing=True,
        shadow_moe_source_timing_mode="shared",
    )

    assert _moe_substage_allowed(recorder, "experts_shared_w1") is True
    assert _moe_substage_allowed(recorder, "experts_shared_output_gate") is True
    assert _moe_substage_allowed(recorder, "quant_method_apply") is False
    assert _moe_substage_allowed(recorder, "apply_dispatch_w1_host") is False

    recorder.shadow_moe_source_timing_mode = "outer"
    assert _moe_substage_allowed(recorder, "quant_method_apply") is True
