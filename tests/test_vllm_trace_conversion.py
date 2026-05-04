from __future__ import annotations

import torch

from mtp_expert_prefetch.tracing.vllm_router_trace import (
    VllmRouterRecorder,
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
