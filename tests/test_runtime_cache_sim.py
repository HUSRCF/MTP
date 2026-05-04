from __future__ import annotations

import json

import pytest

from mtp_expert_prefetch.runtime import (
    ExpertPrefetchDescriptor,
    load_descriptor_jsonl,
    simulate_descriptor_lru_cache,
    simulate_descriptor_priority_cache,
    write_descriptor_cache_report,
)


def test_simulate_descriptor_lru_cache_tracks_hits_misses_and_evictions(tmp_path):
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 2, 2, "transition_head", 0.8),
        ExpertPrefetchDescriptor(0, 0, 1, 3, "transition_tail", 0.7),
        ExpertPrefetchDescriptor(0, 0, 3, 4, "mtp_token_extra_head", 0.6),
        ExpertPrefetchDescriptor(0, 1, 1, 2, "transition_head", 0.5),
    ]

    report = simulate_descriptor_lru_cache(
        descriptors,
        capacity_per_layer=2,
        expert_bytes=100,
    )

    assert report.num_descriptors == 5
    assert report.hits == 1
    assert report.misses == 4
    assert report.evictions == 1
    assert report.skipped == 0
    assert report.hit_rate == pytest.approx(0.2)
    assert report.load_bytes == 400
    assert report.skipped_bytes == 0
    assert report.by_priority["2"]["misses"] == 3
    assert report.by_priority["3"]["hits"] == 1
    assert report.by_priority["4"]["evictions"] == 1

    output = write_descriptor_cache_report(report, tmp_path / "cache.json")
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["load_bytes"] == 400


def test_simulate_descriptor_lru_cache_respects_transfer_budget():
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 2, 2, "transition_head", 0.8),
        ExpertPrefetchDescriptor(0, 0, 3, 4, "mtp_token_extra_head", 0.7),
        ExpertPrefetchDescriptor(0, 1, 1, 2, "transition_head", 0.6),
    ]

    report = simulate_descriptor_lru_cache(
        descriptors,
        capacity_per_layer=8,
        expert_bytes=100,
        transfer_budget_bytes_per_sample_layer=200,
    )

    assert report.misses == 3
    assert report.skipped == 1
    assert report.load_bytes == 300
    assert report.skipped_bytes == 100
    assert report.by_priority["4"]["skipped"] == 1
    assert report.by_priority["4"]["admitted_rate"] == pytest.approx(0.0)
    assert report.by_priority["4"]["total"] == 1


def test_simulate_descriptor_priority_cache_does_not_evict_transition_for_mtp_extra():
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 2, 3, "transition_tail", 0.8),
        ExpertPrefetchDescriptor(0, 0, 3, 4, "mtp_token_extra_head", 0.7),
    ]

    lru_report = simulate_descriptor_lru_cache(
        descriptors,
        capacity_per_layer=2,
        expert_bytes=100,
    )
    protected_report = simulate_descriptor_priority_cache(
        descriptors,
        capacity_per_layer=2,
        expert_bytes=100,
    )

    assert lru_report.evictions == 1
    assert lru_report.by_priority["4"]["misses"] == 1
    assert protected_report.evictions == 0
    assert protected_report.skipped == 1
    assert protected_report.by_priority["4"]["skipped"] == 1


def test_load_descriptor_jsonl_round_trip(tmp_path):
    path = tmp_path / "descriptors.jsonl"
    descriptor = ExpertPrefetchDescriptor(2, 3, 4, 5, "mtp_token_extra_tail", 0.25)
    path.write_text(json.dumps(descriptor.as_dict()) + "\n", encoding="utf-8")

    loaded = load_descriptor_jsonl(path)

    assert loaded == [descriptor]
