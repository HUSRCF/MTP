from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("sample_count", "expected_event_count"),
    [
        (128, 326_240),
        (512, 1_301_880),
    ],
)
def test_dolly_longrun_audit_summaries_are_premap_safe(
    sample_count: int, expected_event_count: int
) -> None:
    summary_path = (
        PROJECT_ROOT
        / "data/traces"
        / f"external_prompt_gate_dolly_{sample_count}_awq_vllm_gpu1_decode_gen64_longrun_audit"
        / "longrun_audit_summary.json"
    )
    if not summary_path.exists():
        pytest.skip(f"long-run audit artifact is not present: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["event_counts"] == {
        "descriptor_summary_min": expected_event_count,
        "outcome_aggregate": expected_event_count,
        "premap_summary": expected_event_count,
    }
    aggregate = summary["aggregate"]
    assert aggregate["premap_summary_payload_bytes"] == 0
    assert aggregate["premap_address_evicted_count"] == 0
    assert aggregate["premap_address_resident_count_max"] < 12_288
    assert aggregate["premap_address_resident_descriptor_bytes_max"] > 0
    assert aggregate["premap_address_new_count"] > 0
    assert aggregate["premap_address_reused_count"] > 0
