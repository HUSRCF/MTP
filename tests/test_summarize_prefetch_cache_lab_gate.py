from __future__ import annotations

from scripts.summarize_prefetch_cache_lab_gate import (
    all_positive_by_group,
    first_positive_capacity,
    first_positive_overlap,
)


def test_first_positive_capacity_and_overlap() -> None:
    rows = [
        {
            "dataset": "aya",
            "split": "heldout",
            "policy": "transition_top32_plus_utility_keep50",
            "cache_capacity": 2048,
            "overlap_factor": 0.5,
            "net_saved_ms_vs_transition": -1.0,
        },
        {
            "dataset": "aya",
            "split": "heldout",
            "policy": "transition_top32_plus_utility_keep50",
            "cache_capacity": 4096,
            "overlap_factor": 0.5,
            "net_saved_ms_vs_transition": 2.0,
        },
        {
            "dataset": "aya",
            "split": "heldout",
            "policy": "transition_top32_plus_score_keep50",
            "cache_capacity": 1024,
            "overlap_factor": 0.1,
            "net_saved_ms_vs_transition": 99.0,
        },
    ]

    capacity = first_positive_capacity(
        rows, policy_suffix="_plus_utility_keep50"
    )
    overlap = first_positive_overlap(rows, policy_suffix="_plus_utility_keep50")

    assert capacity[0]["dataset_split"] == "aya/heldout"
    assert capacity[0]["first_positive_capacity"] == 4096
    assert capacity[0]["first_positive_net_saved_ms"] == 2.0
    assert overlap[0]["cache_capacity"] == 2048
    assert overlap[0]["first_positive_overlap"] is None
    assert overlap[1]["cache_capacity"] == 4096
    assert overlap[1]["first_positive_overlap"] == 0.5


def test_all_positive_by_group_reports_min_margin() -> None:
    rows = [
        {
            "dataset": "dolly",
            "split": "heldout",
            "policy": "transition_top32_plus_utility_keep50",
            "manager_us_per_issue": 1.0,
            "net_saved_ms_vs_transition": 3.0,
        },
        {
            "dataset": "dolly",
            "split": "heldout",
            "policy": "transition_top32_plus_utility_keep50",
            "manager_us_per_issue": 50.0,
            "net_saved_ms_vs_transition": 1.5,
        },
    ]

    result = all_positive_by_group(
        rows,
        policy_suffix="_plus_utility_keep50",
        variable="manager_us_per_issue",
    )

    assert result == [
        {
            "dataset_split": "dolly/heldout",
            "variable": "manager_us_per_issue",
            "all_positive": True,
            "min_net_saved_ms": 1.5,
            "tested": [
                {
                    "manager_us_per_issue": 1.0,
                    "net_saved_ms_vs_transition": 3.0,
                },
                {
                    "manager_us_per_issue": 50.0,
                    "net_saved_ms_vs_transition": 1.5,
                },
            ],
        }
    ]
