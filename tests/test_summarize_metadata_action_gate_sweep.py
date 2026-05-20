from __future__ import annotations

from scripts.summarize_metadata_action_gate_sweep import _summarize


def test_summarize_tracks_premap_positive_independently_from_metadata():
    rows = [
        {
            "policy": "transition_top32_plus_gated_score_keep_top_0.500",
            "metadata_ratio": 0.5,
            "overlap_factor": 0.0,
            "metadata_count": 0,
            "metadata_later_used_rate": 0.0,
            "metadata_net_setup_benefit_ms": 0.0,
            "metadata_overlap_adjusted_net_setup_benefit_ms": 0.0,
            "metadata_setup_saved_ms": 0.0,
            "premap_budget_max_extra": 1,
            "premap_count": 10,
            "premap_later_used_rate": 0.1,
            "premap_overlap_adjusted_net_setup_benefit_ms": -1.0,
            "stall_reduction_ratio_vs_transition": 0.0,
        },
        {
            "policy": "transition_top32_plus_gated_score_keep_top_0.500",
            "metadata_ratio": 0.5,
            "overlap_factor": 0.5,
            "metadata_count": 0,
            "metadata_later_used_rate": 0.0,
            "metadata_net_setup_benefit_ms": 0.0,
            "metadata_overlap_adjusted_net_setup_benefit_ms": 0.0,
            "metadata_setup_saved_ms": 0.0,
            "premap_budget_max_extra": 1,
            "premap_count": 10,
            "premap_later_used_rate": 0.1,
            "premap_overlap_adjusted_net_setup_benefit_ms": 2.0,
            "stall_reduction_ratio_vs_transition": 0.0,
        },
    ]

    summary = _summarize(rows)

    assert len(summary) == 1
    assert summary[0]["first_positive_overlap"] is None
    assert summary[0]["best_overlap"] == 0.0
    assert summary[0]["premap_first_positive_overlap"] == 0.5
    assert summary[0]["premap_best_overlap"] == 0.5
    assert summary[0]["premap_best_net_ms"] == 2.0
