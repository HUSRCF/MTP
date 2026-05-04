from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_summary_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "summarize_prefetch_pareto.py"
    spec = importlib.util.spec_from_file_location("summarize_prefetch_pareto", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_rows_parses_fixed_and_gated_policies() -> None:
    module = _load_summary_module()
    payload = {
        "policies": {
            "transition_ready": {},
            "transition_top32_plus_ready_mtp_extra4": {
                "delta_issued_bytes_vs_transition": 2_000_000_000_000.0,
                "stall_reduction_ratio_vs_transition": 0.125,
                "stall_saved_ms_per_extra_issued_gb": 9.0,
                "saved_supplemental_fetch_count_vs_transition": 10,
                "delta_used_bytes_per_extra_issued_byte": 0.25,
                "delta_unused_bytes_per_extra_issued_byte": 0.5,
                "weighted_top1_supplemental_miss": 0.02,
            },
            "transition_top32_plus_gated_score_keep_top_0.500": {
                "delta_issued_bytes_vs_transition": 1_000_000_000_000.0,
                "stall_reduction_ratio_vs_transition": 0.08,
            },
            "transition_top32_plus_gated_utility_keep_top_0.250": {
                "delta_issued_bytes_vs_transition": 500_000_000_000.0,
                "stall_reduction_ratio_vs_transition": 0.05,
            },
        }
    }

    rows = module._extract_rows(payload)

    by_policy = {row["policy"]: row for row in rows}
    assert by_policy["fixed_extra4"]["kind"] == "fixed"
    assert by_policy["fixed_extra4"]["max_extra"] == 4
    assert by_policy["fixed_extra4"]["extra_issued_tb"] == 2.0
    assert by_policy["fixed_extra4"]["stall_reduction_pct"] == 12.5
    assert by_policy["score_keep_top_0.500"]["kind"] == "score"
    assert by_policy["score_keep_top_0.500"]["keep_fraction"] == 0.5
    assert by_policy["utility_keep_top_0.250"]["kind"] == "utility"
    assert by_policy["utility_keep_top_0.250"]["keep_fraction"] == 0.25
