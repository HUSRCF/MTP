from __future__ import annotations

import pytest
import torch

from mtp_expert_prefetch.evaluation.prefetch_shadow import (
    capacity_guarded_mask,
    enabled_sample_layer_fraction,
    lead_time_ready_mask,
    mask_metrics,
    novel_mtp_extra_mask,
    novel_mtp_extra_rank_mask,
    policy_working_set_summary,
    priority_admission_mask,
    priority_tier_metrics,
    queue_aware_ready_mask,
    score_threshold_mtp_extra_decision_masks,
    score_threshold_mtp_extra_mask,
    tail_swap_mtp_extra_mask,
    topk_mask,
)
from mtp_expert_prefetch.runtime import build_mtp_extra_utility_scores


def test_novel_mtp_extra_mask_keeps_transition_pool_protected():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.1, 0.0, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.2, 0.1, 0.95, 0.7, 0.6, 0.5]]]])
    base = topk_mask(transition_scores, k=2)

    extra = novel_mtp_extra_mask(base, mtp_scores, mtp_topk=4, max_extra=2)
    pool = base | extra

    assert base[0, 0, 0].tolist() == [True, True, False, False, False, False]
    assert extra[0, 0, 0].tolist() == [False, False, True, True, False, False]
    assert pool[0, 0, 0].tolist() == [True, True, True, True, False, False]


def test_novel_mtp_extra_rank_mask_selects_one_based_novel_rank():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.1, 0.0, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.2, 0.1, 0.95, 0.7, 0.6, 0.5]]]])
    base = topk_mask(transition_scores, k=2)

    rank1 = novel_mtp_extra_rank_mask(base, mtp_scores, mtp_topk=6, rank=1)
    rank3 = novel_mtp_extra_rank_mask(base, mtp_scores, mtp_topk=6, rank=3)

    assert rank1[0, 0, 0].tolist() == [False, False, True, False, False, False]
    assert rank3[0, 0, 0].tolist() == [False, False, False, False, True, False]


def test_score_threshold_mtp_extra_mask_filters_within_max_extra():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.1, 0.0, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.2, 0.1, 0.95, 0.7, 0.6, 0.5]]]])
    base = topk_mask(transition_scores, k=2)

    extra = score_threshold_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=6,
        max_extra=4,
        score_threshold=0.65,
    )

    assert extra[0, 0, 0].tolist() == [False, False, True, True, False, False]


def test_score_threshold_mtp_extra_mask_preserves_transition_contracts():
    transition_scores = torch.tensor(
        [[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0, 0.0, 0.0]]]]
    )
    mtp_scores = torch.tensor(
        [[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85, 0.75, 0.65]]]]
    )
    base = topk_mask(transition_scores, k=4)
    extra = score_threshold_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=8,
        max_extra=3,
        score_threshold=0.7,
    )
    final = base | extra

    assert final[base].all()
    assert not (extra & base).any()
    assert extra.float().sum(dim=-1).max().item() <= 3


def test_score_threshold_mtp_extra_mask_is_monotonic_with_threshold():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.0, 0.0, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.1, 0.2, 0.95, 0.7, 0.6, 0.5]]]])
    base = topk_mask(transition_scores, k=2)

    low = score_threshold_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=6,
        max_extra=4,
        score_threshold=0.55,
    )
    high = score_threshold_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=6,
        max_extra=4,
        score_threshold=0.75,
    )

    assert (high & ~low).any().item() is False


def test_score_threshold_mtp_extra_mask_rejects_nan_and_inf_scores():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.0, 0.0, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.1, 0.2, float("nan"), float("inf"), 0.7, 0.6]]]])
    base = topk_mask(transition_scores, k=2)

    extra = score_threshold_mtp_extra_mask(
        base,
        mtp_scores,
        mtp_topk=6,
        max_extra=4,
        score_threshold=0.5,
    )

    assert extra[0, 0, 0].tolist() == [False, False, False, False, True, True]


def test_score_threshold_decision_masks_report_disjoint_reasons():
    transition_scores = torch.tensor(
        [[[[0.9, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]]]
    )
    mtp_scores = torch.tensor(
        [[[[0.8, 0.7, 0.95, 0.9, 0.4, float("nan"), float("inf"), 0.3]]]]
    )
    base = topk_mask(transition_scores, k=2)

    decisions = score_threshold_mtp_extra_decision_masks(
        base,
        mtp_scores,
        mtp_topk=8,
        max_extra=2,
        score_threshold=0.85,
    )

    assert decisions.admitted_full_fetch[0, 0, 0].tolist() == [
        False,
        False,
        True,
        True,
        False,
        False,
        False,
        False,
    ]
    assert decisions.skipped_not_novel[0, 0, 0].tolist() == [
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    assert decisions.skipped_rank_cap[0, 0, 0].tolist() == [
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        True,
    ]
    assert decisions.skipped_invalid_score[0, 0, 0].tolist() == [
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
    ]

    reason_sum = torch.zeros_like(base, dtype=torch.int16)
    for mask in decisions.reason_masks().values():
        reason_sum += mask.to(torch.int16)
    assert reason_sum.max().item() == 1
    assert decisions.final_prefetch_mask(base)[base].all()


def test_score_threshold_decision_masks_report_policy_skips():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.1, 0.2, 0.95, 0.9]]]])
    base = topk_mask(transition_scores, k=2)
    policy_allowed = torch.ones_like(base)
    policy_allowed[..., 3] = False

    decisions = score_threshold_mtp_extra_decision_masks(
        base,
        mtp_scores,
        mtp_topk=4,
        max_extra=2,
        score_threshold=0.85,
        policy_allowed_mask=policy_allowed,
    )

    assert decisions.admitted_full_fetch[0, 0, 0].tolist() == [
        False,
        False,
        True,
        False,
    ]
    assert decisions.skipped_policy[0, 0, 0].tolist() == [
        False,
        False,
        False,
        True,
    ]


def test_tail_swap_mtp_extra_mask_replaces_transition_tail_only():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85, 0.75]]]])

    swapped = tail_swap_mtp_extra_mask(
        transition_scores,
        mtp_scores,
        transition_topk=4,
        mtp_topk=7,
        swap_count=2,
    )

    # Protect transition head {0,1}; replace tail {2,3} with novel MTP {4,5}.
    assert swapped[0, 0, 0].tolist() == [True, True, False, False, True, True, False]
    assert swapped.float().sum().item() == 4


def test_build_mtp_extra_utility_scores_applies_rank_layer_ready_factors():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.0, 0.0], [0.9, 0.8, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.1, 0.2, 0.8, 0.4], [0.1, 0.2, 0.8, 0.4]]]])
    base = topk_mask(transition_scores, k=2)
    layer_factors = torch.tensor([1.0, 0.5])
    ready_factors = torch.tensor([0.25, 1.0])

    utility = build_mtp_extra_utility_scores(
        base,
        mtp_scores,
        mtp_topk=4,
        rank_alpha=1.0,
        layer_factors=layer_factors,
        ready_factors=ready_factors,
    )

    # Novel rank 1 expert 2: score * 1/rank * layer * ready.
    assert utility[0, 0, 0, 2].item() == pytest.approx(0.8 * 1.0 * 1.0 * 0.25)
    assert utility[0, 0, 1, 2].item() == pytest.approx(0.8 * 1.0 * 0.5 * 1.0)
    # Novel rank 2 expert 3 is rank-decayed.
    assert utility[0, 0, 0, 3].item() == pytest.approx(0.4 * 0.5 * 1.0 * 0.25)


def test_mask_metrics_reports_added_mass_and_top1_risk():
    target_mass = torch.tensor([[[[0.7, 0.2, 0.1, 0.0]]]])
    base = torch.tensor([[[[False, True, False, False]]]])
    pool = torch.tensor([[[[True, True, False, False]]]])

    base_metrics = mask_metrics(base, target_mass)
    pool_metrics = mask_metrics(pool, target_mass, base_mask=base)

    assert base_metrics["pool_mass_coverage"] == pytest.approx(0.2)
    assert base_metrics["top1_hit_rate"] == pytest.approx(0.0)
    assert base_metrics["weighted_top1_miss"] == pytest.approx(0.7)
    assert pool_metrics["pool_mass_coverage"] == pytest.approx(0.9)
    assert pool_metrics["top1_hit_rate"] == pytest.approx(1.0)
    assert pool_metrics["introduced_mass_fraction"] == pytest.approx(0.7)


def test_priority_tier_metrics_are_disjoint_for_mtp_extras():
    transition_scores = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp_scores = torch.tensor([[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85]]]])
    target_mass = torch.tensor([[[[0.0, 0.2, 0.0, 0.1, 0.5, 0.2]]]])

    tiers = priority_tier_metrics(
        transition_scores,
        mtp_scores,
        target_mass,
        transition_topk=4,
        mtp_topk=4,
        max_extra=2,
    )

    assert tiers["P2_transition_top16"]["avg_count"] == pytest.approx(4.0)
    assert tiers["P4_mtp_extra1_to_4"]["avg_count"] == pytest.approx(2.0)
    assert tiers["P5_mtp_extra5_to_4"]["avg_count"] == pytest.approx(0.0)
    assert tiers["P4_mtp_extra1_to_4"]["mass_fraction"] == pytest.approx(0.7)


def test_policy_working_set_summary_unions_tokens_by_sample_and_layer():
    mask = torch.zeros((3, 1, 2, 5), dtype=torch.bool)
    mask[0, 0, 0, [0, 1]] = True
    mask[1, 0, 0, [1, 2]] = True
    mask[0, 0, 1, [3]] = True
    mask[1, 0, 1, [3, 4]] = True
    mask[2, 0, 0, [0]] = True
    mask[2, 0, 1, [4]] = True
    sample_ids = torch.tensor([7, 7, 8], dtype=torch.long)

    summary = policy_working_set_summary(mask, sample_ids, capacities=[1, 2, 3])

    # sample 7 has layer counts [3, 2]; sample 8 has [1, 1].
    assert summary["mean"] == pytest.approx(1.75)
    assert summary["max"] == pytest.approx(3.0)
    assert summary["fit_fraction_at_1"] == pytest.approx(0.5)
    assert summary["fit_fraction_at_2"] == pytest.approx(0.75)
    assert summary["fit_fraction_at_3"] == pytest.approx(1.0)


def test_capacity_guarded_mask_enables_candidate_only_when_layer_fits():
    base = torch.zeros((3, 1, 2, 5), dtype=torch.bool)
    candidate = base.clone()
    base[:, :, :, 0] = True
    candidate[:] = base
    candidate[0, 0, 0, [1, 2]] = True
    candidate[1, 0, 0, [2, 3]] = True
    candidate[0, 0, 1, [1]] = True
    candidate[1, 0, 1, [1]] = True
    candidate[2, 0, :, [1]] = True
    sample_ids = torch.tensor([0, 0, 1], dtype=torch.long)

    guarded = capacity_guarded_mask(base, candidate, sample_ids, capacity=2)

    # sample 0 layer 0 has union {0,1,2,3}, so it falls back to base.
    assert guarded[0, 0, 0].tolist() == [True, False, False, False, False]
    assert guarded[1, 0, 0].tolist() == [True, False, False, False, False]
    # sample 0 layer 1 and all sample 1 layers fit within capacity.
    assert guarded[0, 0, 1].tolist() == [True, True, False, False, False]
    assert guarded[2, 0, 0].tolist() == [True, True, False, False, False]
    assert enabled_sample_layer_fraction(candidate, sample_ids, capacity=2) == pytest.approx(0.75)


def test_priority_admission_mask_keeps_high_priority_under_capacity():
    transition = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85]]]])
    sample_ids = torch.tensor([0], dtype=torch.long)

    admitted = priority_admission_mask(
        transition,
        mtp,
        sample_ids,
        transition_topk=4,
        mtp_topk=4,
        max_extra=2,
        capacity=5,
    )

    # P2 contains transition top4 first; only one MTP extra fits.
    assert admitted[0, 0, 0].tolist() == [True, True, True, True, True, False]


def test_lead_time_ready_mask_drops_too_early_mtp_extras():
    transition = torch.tensor([[[[0.9, 0.8, 0.0, 0.0], [0.9, 0.8, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.0, 0.0, 0.9, 0.8], [0.0, 0.0, 0.9, 0.8]]]])

    ready, stats = lead_time_ready_mask(
        transition,
        mtp,
        transition_topk=2,
        mtp_topk=4,
        max_extra=2,
        num_layers=2,
        layer_ms=1.0,
        bandwidth_gbps=0.0001,
        expert_bytes=100,
    )

    # Layer 0 MTP lead is 0ms, so only transition candidates are ready.
    assert ready[0, 0, 0].tolist() == [True, True, False, False]
    # Layer 1 has enough lead for one MTP extra at this bandwidth.
    assert ready[0, 0, 1].tolist() == [True, True, True, False]
    assert stats["raw_extra_count"] == pytest.approx(4.0)
    assert stats["ready_extra_count"] == pytest.approx(1.0)
    assert stats["ready_extra_fraction"] == pytest.approx(0.25)


def test_queue_aware_ready_mask_prioritizes_transition_over_mtp():
    transition = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.0, 0.0, 0.0, 0.0, 0.95, 0.85]]]])

    ready, stats = queue_aware_ready_mask(
        transition,
        mtp,
        transition_topk=4,
        mtp_topk=6,
        max_extra=2,
        num_layers=1,
        layer_ms=1.0,
        bandwidth_gbps=0.0004,
        expert_bytes=100,
    )

    # Total transition capacity is four experts, while MTP has no earlier
    # window at layer 0, so transition candidates consume the queue first.
    assert ready[0, 0, 0].tolist() == [True, True, True, True, False, False]
    assert stats["ready_base_fraction"] == pytest.approx(1.0)
    assert stats["ready_extra_fraction"] == pytest.approx(0.0)
