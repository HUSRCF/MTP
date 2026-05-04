from __future__ import annotations

import json

import pytest

from mtp_expert_prefetch.runtime import (
    ExpertPrefetchDescriptor,
    analyze_descriptor_lead_time,
    write_lead_time_report,
)


def test_analyze_descriptor_lead_time_separates_transition_and_mtp_windows(tmp_path):
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 2, 2, "transition_head", 0.8),
        ExpertPrefetchDescriptor(0, 0, 3, 4, "mtp_token_extra_head", 0.7),
        ExpertPrefetchDescriptor(0, 2, 4, 4, "mtp_token_extra_head", 0.6),
    ]

    report = analyze_descriptor_lead_time(
        descriptors,
        num_layers=4,
        layer_ms=1.0,
        sampling_ms=0.0,
        mtp_delay_ms=0.0,
        bandwidth_gbps=0.0001,
        expert_bytes=100,
    )

    assert report.num_descriptors == 4
    assert report.by_source["transition_head"]["mean_lead_ms"] == pytest.approx(4.0)
    assert report.by_source["transition_head"]["fetchable_fraction"] == pytest.approx(1.0)
    assert report.by_source["mtp_token_extra_head"]["min_lead_ms"] == pytest.approx(0.0)
    assert report.by_source["mtp_token_extra_head"]["fetchable_fraction"] == pytest.approx(0.5)
    assert report.by_priority["2"]["fetchable_fraction"] == pytest.approx(1.0)
    assert report.by_priority["4"]["fetchable_fraction"] == pytest.approx(0.5)

    output = write_lead_time_report(report, tmp_path / "lead.json")
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["by_source"]["mtp_token_extra_head"]["fetchable_experts"] == 1.0


def test_analyze_descriptor_lead_time_applies_mtp_delay():
    descriptors = [
        ExpertPrefetchDescriptor(0, 1, 1, 4, "mtp_token_extra_head", 0.7),
        ExpertPrefetchDescriptor(0, 3, 2, 4, "mtp_token_extra_head", 0.6),
    ]

    report = analyze_descriptor_lead_time(
        descriptors,
        num_layers=4,
        layer_ms=1.0,
        sampling_ms=0.0,
        mtp_delay_ms=1.0,
        bandwidth_gbps=0.0001,
        expert_bytes=100,
    )

    assert report.by_source["mtp_token_extra_head"]["min_lead_ms"] == pytest.approx(0.0)
    assert report.by_source["mtp_token_extra_head"]["p50_lead_ms"] == pytest.approx(1.0)
