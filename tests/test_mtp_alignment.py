from __future__ import annotations

import torch

from mtp_expert_prefetch.training import build_mtp_router_alignment


def test_build_mtp_router_alignment_pairs_mtp_with_future_backbone_router():
    payload = {
        "native_mtp_router_topk": torch.tensor([[[10, 11], [12, 13], [14, 15], [16, 17]]]),
        "native_mtp_router_weights": torch.tensor(
            [[[0.7, 0.3], [0.6, 0.4], [0.5, 0.5], [0.4, 0.6]]]
        ),
        "input_ids": torch.tensor([[1000, 1001, 1002, 1003]]),
        "router_topk": {
            "model.language_model.layers.1.mlp.gate": [
                torch.tensor([[[101, 102], [111, 112], [121, 122], [131, 132]]])
            ],
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[[1, 2], [11, 12], [21, 22], [31, 32]]])
            ],
        },
        "router_weights": {
            "model.language_model.layers.1.mlp.gate": [
                torch.tensor([[[0.9, 0.1], [0.8, 0.2], [0.7, 0.3], [0.6, 0.4]]])
            ],
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[[0.1, 0.9], [0.2, 0.8], [0.3, 0.7], [0.4, 0.6]]])
            ],
        },
    }

    batch = build_mtp_router_alignment(payload, future_window=2)

    assert batch.mtp_expert_ids.shape == (2, 2)
    assert batch.target_expert_ids.shape == (2, 2, 2, 2)
    assert torch.equal(batch.target_layer_ids, torch.tensor([0, 1]))
    assert torch.equal(batch.source_token_indices, torch.tensor([0, 1]))
    assert torch.equal(batch.target_token_indices, torch.tensor([[1, 2], [2, 3]]))
    assert torch.equal(batch.source_token_ids, torch.tensor([1000, 1001]))
    assert torch.equal(batch.target_token_ids, torch.tensor([[1001, 1002], [1002, 1003]]))
    assert torch.equal(batch.current_expert_ids[0, 0], torch.tensor([1, 2]))
    assert torch.equal(batch.current_expert_ids[0, 1], torch.tensor([101, 102]))
    assert torch.equal(batch.target_expert_ids[0, 0, 0], torch.tensor([11, 12]))
    assert torch.equal(batch.target_expert_ids[0, 0, 1], torch.tensor([111, 112]))
    assert torch.equal(batch.target_expert_ids[1, 1, 0], torch.tensor([31, 32]))
    assert batch.target_expert_weights is not None
    assert batch.current_expert_weights is not None
    assert torch.allclose(batch.current_expert_weights[0, 0], torch.tensor([0.1, 0.9]))
    assert torch.allclose(batch.target_expert_weights[0, 0, 0], torch.tensor([0.2, 0.8]))
    assert torch.allclose(batch.target_expert_weights[0, 0, 1], torch.tensor([0.8, 0.2]))


def test_build_mtp_router_alignment_derives_weights_from_router_scores():
    payload = {
        "native_mtp_router_topk": torch.tensor([[[10, 11], [12, 13], [14, 15]]]),
        "native_mtp_router_weights": torch.tensor([[[0.7, 0.3], [0.6, 0.4], [0.5, 0.5]]]),
        "router_topk": {
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[[1, 2], [11, 12], [21, 22]]])
            ],
        },
        "router_scores": {
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[[0.0, 2.0], [1.0, 3.0], [4.0, 0.0]]])
            ],
        },
    }

    batch = build_mtp_router_alignment(payload, future_window=1)

    assert batch.current_expert_weights is not None
    assert batch.target_expert_weights is not None
    assert torch.allclose(
        batch.current_expert_weights[0, 0],
        torch.softmax(torch.tensor([0.0, 2.0]), dim=-1),
    )
    assert torch.allclose(
        batch.target_expert_weights[0, 0, 0],
        torch.softmax(torch.tensor([1.0, 3.0]), dim=-1),
    )
