from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_prefetch_claim_gate.py"
    )
    spec = importlib.util.spec_from_file_location("summarize_prefetch_claim_gate", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_rows_includes_action_counts_and_outcomes() -> None:
    module = _load_module()
    payload = {
        "bandwidth_gbps": 3.0,
        "layer_ms": 1.0,
        "mtp_delay_ms": 2.0,
        "gated_policies": {"action_cost_overlap_factor": 0.0},
        "policies": {
            "transition_ready": {
                "ready_pool_mass_coverage": 0.8,
                "ready_top1_hit_rate": 0.9,
                "weighted_top1_supplemental_miss": 0.02,
            },
            "transition_top32_plus_gated_utility_keep_top_0.500": {
                "ready_mass_fraction": 0.82,
                "ready_top1_hit_rate": 0.92,
                "weighted_top1_supplemental_miss": 0.018,
                "stall_reduction_ratio_vs_transition": 0.07,
                "saved_supplemental_fetch_count_vs_transition": 12,
                "delta_issued_bytes_vs_transition": 2_000_000_000_000.0,
                "delta_used_bytes_per_extra_issued_byte": 0.1,
                "delta_unused_bytes_per_extra_issued_byte": 0.8,
                "admission_action_counters": {
                    "full_fetch": {"count": 3},
                    "metadata": 5,
                    "premap": 7,
                    "skip": 11,
                },
                "admission_action_outcomes": {
                    "metadata": {
                        "later_used_rate": 0.4,
                        "overlap_adjusted_net_setup_benefit_ms": -2.5,
                    },
                    "premap": {
                        "later_used_count": 2,
                        "overlap_adjusted_net_setup_benefit_ms": 1.25,
                    },
                },
            },
        },
    }

    rows = module._extract_rows(Path("report.json"), payload, strict=True)

    by_policy = {row["policy"]: row for row in rows}
    assert by_policy["transition_ready"]["ready_mass"] == 0.8
    utility = by_policy["transition_top32_plus_gated_utility_keep_top_0.500"]
    assert utility["overlap_factor"] == 0.0
    assert utility["delta_issued_tb"] == 2.0
    assert utility["full_fetch_count"] == 3
    assert utility["metadata_count"] == 5
    assert utility["premap_count"] == 7
    assert utility["skip_count"] == 11
    assert utility["metadata_later_used_rate"] == 0.4
    assert utility["premap_later_used_rate"] == 2 / 7
    assert utility["metadata_net_setup_ms"] == -2.5
    assert utility["premap_net_setup_ms"] == 1.25


def test_strict_mode_rejects_missing_delta_fields() -> None:
    module = _load_module()
    payload = {
        "policies": {
            "transition_top32_plus_ready_mtp_extra1": {
                "ready_mass_fraction": 0.82,
                "ready_top1_hit_rate": 0.91,
                "weighted_top1_supplemental_miss": 0.02,
            }
        }
    }

    with pytest.raises(KeyError, match="stall_reduction_ratio"):
        module._extract_rows(Path("bad.json"), payload, strict=True)
