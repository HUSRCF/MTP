from __future__ import annotations

import json

import torch

from mtp_expert_prefetch.tracing import (
    resolve_trace_sample,
    select_router_topk,
    select_trace_hidden_token,
)


def test_select_router_topk_uses_layer_and_softmax_scores():
    payload = {
        "router_topk": {
            "model.language_model.layers.3.mlp.gate": [
                [
                    [
                        [7, 3, 1],
                        [2, 4, 6],
                    ]
                ]
            ],
            "model.language_model.layers.4.mlp.gate": [[[[9, 8, 7]]]],
        },
        "router_scores": {
            "model.language_model.layers.3.mlp.gate": [
                [
                    [
                        [0.0, 2.0, -1.0],
                        [3.0, 1.0, 0.0],
                    ]
                ]
            ],
        },
    }

    selection = select_router_topk(
        payload,
        layer=3,
        batch_index=0,
        token_index=1,
        top_k=2,
    )

    assert selection.module_name == "model.language_model.layers.3.mlp.gate"
    assert torch.equal(selection.expert_ids, torch.tensor([2, 4]))
    assert torch.allclose(selection.expert_weights, torch.softmax(torch.tensor([3.0, 1.0]), dim=-1))


def test_select_router_topk_falls_back_to_uniform_weights():
    payload = {
        "router_topk": {
            "model.language_model.layers.0.mlp.gate": [[[[1, 2, 3, 4]]]],
        },
    }

    selection = select_router_topk(payload, layer=0, top_k=4)

    assert torch.equal(selection.expert_ids, torch.tensor([1, 2, 3, 4]))
    assert torch.allclose(selection.expert_weights, torch.full((4,), 0.25))
    assert selection.raw_scores is None


def test_select_trace_hidden_token_preserves_batch_and_token_axes():
    hidden = torch.arange(2 * 4 * 6, dtype=torch.float32).reshape(2, 4, 6)
    payload = {"last_hidden_state": hidden}

    token = select_trace_hidden_token(payload, batch_index=1, token_index=2)

    assert token.shape == (1, 1, 6)
    assert torch.equal(token[0, 0], hidden[1, 2])


def test_resolve_trace_sample_from_manifest(tmp_path):
    sample = tmp_path / "sample_000000.pt"
    sample.write_bytes(b"placeholder")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps({"path": sample.name}) + "\n", encoding="utf-8")

    assert resolve_trace_sample(manifest_path=manifest) == sample.resolve()
