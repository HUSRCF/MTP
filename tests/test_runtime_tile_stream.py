from __future__ import annotations

import torch
import pytest

from mtp_expert_prefetch.runtime import tile_requests_from_tensor_cache


def test_tile_requests_from_tensor_cache_emits_token_row_descriptors():
    target_mass = torch.zeros((2, 1, 1, 4), dtype=torch.float32)
    target_mass[0, 0, 0, 1] = 0.7
    target_mass[0, 0, 0, 3] = 0.2
    target_mass[1, 0, 0, 2] = 0.5

    transition_scores = torch.zeros_like(target_mass)
    transition_scores[0, 0, 0, 1] = 0.6
    transition_scores[0, 0, 0, 3] = 0.1
    transition_scores[1, 0, 0, 2] = 0.4

    mtp_scores = torch.zeros_like(target_mass)
    mtp_scores[0, 0, 0, 1] = 0.2
    mtp_scores[0, 0, 0, 3] = 0.8
    mtp_scores[1, 0, 0, 2] = 0.3

    cache = {
        "target_mass": target_mass,
        "transition_scores": transition_scores,
        "mtp_scores": mtp_scores,
        "token_sample_indices": torch.tensor([42, 43]),
        "schema_version": 3,
        "eval_split": "unit",
    }

    requests, metadata = tile_requests_from_tensor_cache(
        cache,
        window_size=1,
        topk=2,
        tiles_per_expert=2,
    )

    assert metadata["num_examples"] == 2
    assert metadata["num_layers"] == 1
    assert metadata["num_experts"] == 4
    assert metadata["schema_version"] == 3
    assert metadata["eval_split"] == "unit"
    assert len(requests) == 6

    first = requests[0]
    assert first.window_id == 0
    assert first.request_id == 0
    assert first.tile_id == 2
    assert first.expert_id == 1
    assert first.transition_score == pytest.approx(0.6)
    assert first.mtp_score == pytest.approx(0.2)
    assert first.utility_score == pytest.approx(0.56)
    assert first.sample_idx == 42
    assert first.token_index == 0
    assert first.layer_idx == 0
    assert first.row_id == 0
    assert first.weight == pytest.approx(0.7)
    assert first.source_policy == "target_topk"
    assert [request.tile_id for request in requests[:4]] == [2, 3, 6, 7]
    assert {request.sample_idx for request in requests} == {42, 43}
    assert {request.source_policy for request in requests} == {"target_topk"}


def test_tile_requests_from_tensor_cache_respects_max_examples():
    target_mass = torch.zeros((2, 1, 1, 4), dtype=torch.float32)
    target_mass[:, 0, 0, 1] = 1.0
    cache = {
        "target_mass": target_mass,
        "transition_scores": torch.zeros_like(target_mass),
        "mtp_scores": torch.zeros_like(target_mass),
    }

    requests, metadata = tile_requests_from_tensor_cache(
        cache,
        window_size=4,
        topk=1,
        tiles_per_expert=1,
        max_examples=1,
    )

    assert metadata["num_examples"] == 1
    assert len(requests) == 1
    assert requests[0].token_index == 0
    assert requests[0].sample_idx == 0
