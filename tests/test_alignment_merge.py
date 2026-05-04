from __future__ import annotations

import pytest
import torch

from mtp_expert_prefetch.training.alignment_merge import merge_mtp_source_with_router_targets
from mtp_expert_prefetch.training.mtp_alignment import build_mtp_router_alignment


def test_merge_mtp_source_with_vllm_targets_truncates_to_common_prefix():
    mtp_payload = {
        "input_ids": torch.tensor([[1, 2, 3, 4]]),
        "native_mtp_router_topk": torch.tensor([[[10, 11], [12, 13], [14, 15], [16, 17]]]),
        "native_mtp_router_weights": torch.tensor(
            [[[0.7, 0.3], [0.6, 0.4], [0.5, 0.5], [0.4, 0.6]]]
        ),
    }
    target_payload = {
        "backend": "vllm",
        "input_ids": torch.tensor([[1, 2, 3]]),
        "router_topk": {
            "model.language_model.layers.0.mlp.gate": [
                torch.tensor([[1, 2], [11, 12], [21, 22]])
            ],
            "model.language_model.layers.1.mlp.gate": [
                torch.tensor([[101, 102], [111, 112], [121, 122]])
            ],
        },
        "vllm_routed_experts": torch.zeros((3, 2, 2), dtype=torch.int16),
    }

    result = merge_mtp_source_with_router_targets(mtp_payload, target_payload)

    assert result.num_tokens == 3
    assert result.mtp_num_tokens == 4
    assert result.target_num_tokens == 3
    assert result.payload["input_ids"].shape == (1, 3)
    assert result.payload["native_mtp_router_topk"].shape == (1, 3, 2)
    assert result.payload["vllm_routed_experts"].shape == (3, 2, 2)

    alignment = build_mtp_router_alignment(result.payload, future_window=1)

    assert alignment.mtp_expert_ids.shape == (2, 2)
    assert alignment.target_expert_ids.shape == (2, 1, 2, 2)
    assert torch.equal(alignment.target_expert_ids[0, 0, 0], torch.tensor([11, 12]))


def test_merge_rejects_non_matching_prefix():
    mtp_payload = {
        "input_ids": torch.tensor([[1, 99, 3]]),
        "native_mtp_router_topk": torch.zeros((1, 3, 2), dtype=torch.int16),
        "native_mtp_router_weights": torch.zeros((1, 3, 2)),
    }
    target_payload = {
        "input_ids": torch.tensor([[1, 2, 3]]),
        "router_topk": {"model.language_model.layers.0.mlp.gate": [torch.zeros((3, 2))]},
    }

    with pytest.raises(ValueError, match="common prefix"):
        merge_mtp_source_with_router_targets(mtp_payload, target_payload)
