from __future__ import annotations

import pytest

from scripts.summarize_cache_manager_prototype import render_markdown, summarize_case


def test_summarize_case_extracts_gate_and_manager_fields() -> None:
    payload = {
        "cache_lab_gate_decision": {
            "allow_full_fetch_mtp": True,
            "reason": "cache_lab_envelope_allowed",
            "payload_capacity": 10240,
            "overlap_factor": 0.5,
            "manager_us_per_issue": 50.0,
            "bandwidth_gbps": 6.589,
        },
        "metadata": {
            "dataset": "dolly",
            "split": "smoke",
            "run_tag": "allowed",
        },
        "config": {
            "transition_topk": 32,
        },
        "rows": [
            {
                "policy": "transition_top32",
                "issued_fetch_count": 10,
                "used_fetch_count": 9,
            },
            {
                "policy": "transition_top32_plus_utility_keep50",
                "net_saved_us_vs_transition": 123.5,
                "issued_fetch_count": 12,
                "used_fetch_count": 11,
                "unused_fetch_count": 1,
                "evicted_before_use_count": 0,
                "stress_shutdown_count": 0,
                "cache_manager_snapshot": {
                    "capacity": 10240,
                    "demand_count": 20,
                },
            },
        ],
    }

    case = summarize_case(
        payload, source_path="smoke.json", policy_suffix="_plus_utility_keep50"
    )

    assert case["source_path"] == "smoke.json"
    assert case["allow_full_fetch_mtp"] is True
    assert case["gate_reason"] == "cache_lab_envelope_allowed"
    assert case["payload_capacity"] == 10240
    assert case["transition_policy"] == "transition_top32"
    assert case["transition_found"] is True
    assert case["candidate_expected_policy"] == "transition_top32_plus_utility_keep50"
    assert case["candidate_found"] is True
    assert case["candidate_net_saved_us_vs_transition"] == 123.5
    assert case["candidate_issued_fetch_count"] == 12
    assert case["transition_issued_fetch_count"] == 10
    assert case["manager_snapshot"]["demand_count"] == 20


def test_summarize_case_uses_configured_transition_topk() -> None:
    payload = {
        "cache_lab_gate_decision": {
            "allow_full_fetch_mtp": False,
            "reason": "payload_capacity_below_gate",
        },
        "config": {
            "transition_topk": 16,
            "cache_capacity": 4096,
        },
        "rows": [
            {
                "policy": "transition_top16",
                "issued_fetch_count": 4,
                "used_fetch_count": 3,
            },
            {
                "policy": "transition_top16_plus_utility_keep50",
                "net_saved_us_vs_transition": 0.0,
                "issued_fetch_count": 4,
                "used_fetch_count": 3,
                "unused_fetch_count": 1,
                "stress_shutdown_count": 8,
            },
        ],
    }

    case = summarize_case(
        payload, source_path="smoke.json", policy_suffix="_plus_utility_keep50"
    )

    assert case["payload_capacity"] == 4096
    assert case["transition_policy"] == "transition_top16"
    assert case["candidate_policy"] == "transition_top16_plus_utility_keep50"
    assert case["transition_issued_fetch_count"] == 4
    assert case["candidate_stress_shutdown_count"] == 8


def test_summarize_case_marks_missing_gate_as_unknown() -> None:
    payload = {
        "config": {
            "transition_topk": 32,
            "cache_capacity": 10240,
        },
        "rows": [
            {"policy": "transition_top32"},
            {
                "policy": "transition_top32_plus_utility_keep50",
                "net_saved_us_vs_transition": 1.0,
            },
        ],
    }

    case = summarize_case(
        payload, source_path="smoke.json", policy_suffix="_plus_utility_keep50"
    )

    assert case["allow_full_fetch_mtp"] is None
    assert case["gate_reason"] == "gate_decision_missing"
    assert case["payload_capacity"] == 10240


def test_summarize_case_marks_missing_transition_or_candidate() -> None:
    payload = {
        "config": {
            "transition_topk": 32,
        },
        "rows": [],
    }

    case = summarize_case(
        payload, source_path="smoke.json", policy_suffix="_plus_utility_keep50"
    )

    assert case["transition_found"] is False
    assert case["candidate_found"] is False
    assert case["candidate_expected_policy"] == "transition_top32_plus_utility_keep50"


def test_summarize_case_rejects_duplicate_exact_candidate() -> None:
    payload = {
        "config": {
            "transition_topk": 32,
        },
        "rows": [
            {"policy": "transition_top32"},
            {"policy": "transition_top32_plus_utility_keep50"},
            {"policy": "transition_top32_plus_utility_keep50"},
        ],
    }

    with pytest.raises(ValueError, match="Expected one row"):
        summarize_case(
            payload, source_path="smoke.json", policy_suffix="_plus_utility_keep50"
        )


def test_render_markdown_includes_boundary_and_cases() -> None:
    markdown = render_markdown(
        {
            "boundary": "prototype only",
            "policy_suffix": "_plus_utility_keep50",
            "cases": [
                {
                    "dataset": "dolly",
                    "split": "smoke",
                    "run_tag": "capacity_blocked",
                    "allow_full_fetch_mtp": False,
                    "gate_reason": "payload_capacity_below_gate",
                    "payload_capacity": 8192,
                    "overlap_factor": 0.8,
                    "manager_us_per_issue": 0.0,
                    "bandwidth_gbps": 6.589,
                    "candidate_net_saved_us_vs_transition": 0.0,
                    "candidate_issued_fetch_count": 10,
                    "candidate_used_fetch_count": 9,
                    "candidate_unused_fetch_count": 1,
                    "candidate_stress_shutdown_count": 42,
                }
            ],
        }
    )

    assert "Controlled Cache-Manager Prototype Summary" in markdown
    assert "prototype only" in markdown
    assert "payload_capacity_below_gate" in markdown
    assert "dolly/smoke/capacity_blocked" in markdown
