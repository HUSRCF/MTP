from __future__ import annotations

import pytest
import torch

from mtp_expert_prefetch.runtime import (
    build_premap_descriptors,
    build_priority_masks,
    descriptor_summary,
)


def test_build_priority_masks_are_disjoint_and_ordered():
    transition = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85]]]])

    masks = build_priority_masks(transition, mtp, transition_topk=4, mtp_topk=4, max_extra=2)

    assert masks["P2_transition_top16"][0, 0, 0].tolist() == [
        True,
        True,
        True,
        True,
        False,
        False,
    ]
    assert not masks["P3_transition_top17_to_4"].any()
    assert masks["P4_mtp_extra1_to_4"][0, 0, 0].tolist() == [
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    assert not masks["P5_mtp_extra5_to_4"].any()


def test_build_premap_descriptors_deduplicates_by_best_priority():
    transition = torch.zeros((2, 1, 1, 8))
    mtp = torch.zeros_like(transition)
    transition[0, 0, 0, [0, 1, 2, 3]] = torch.tensor([0.9, 0.8, 0.7, 0.6])
    transition[1, 0, 0, [0, 1, 4, 5]] = torch.tensor([0.95, 0.75, 0.5, 0.4])
    mtp[:, 0, 0, [6, 7, 1, 2]] = torch.tensor([0.99, 0.88, 0.77, 0.66])
    sample_ids = torch.tensor([42, 42])

    descriptors = build_premap_descriptors(
        transition,
        mtp,
        sample_ids,
        transition_topk=4,
        mtp_topk=4,
        max_extra=2,
    )

    by_expert = {item.expert_id: item for item in descriptors}
    assert by_expert[0].priority == 2
    assert by_expert[1].priority == 2
    assert by_expert[6].priority == 4
    assert by_expert[7].priority == 4
    assert 2 in by_expert
    assert 6 in by_expert
    assert len(descriptors) == len(by_expert)

    summary = descriptor_summary(descriptors, expert_bytes=100)
    assert summary["num_descriptors"] == len(descriptors)
    assert summary["by_priority"]["2"] == 6
    assert summary["by_priority"]["4"] == 2
    assert summary["per_sample_layer_count"]["max"] == pytest.approx(8.0)
    assert summary["total_descriptor_bytes"] == 800
    assert summary["per_sample_layer_bytes"]["max"] == pytest.approx(800.0)
