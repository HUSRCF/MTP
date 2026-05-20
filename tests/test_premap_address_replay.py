from __future__ import annotations

import json

from mtp_expert_prefetch.runtime import (
    ExpertPrefetchDescriptor,
    group_premap_descriptors_by_sample_layer,
    load_premap_descriptor_jsonl,
    replay_premap_address_manager,
)


def test_premap_address_replay_reports_reuse_and_eviction():
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 2, 2, "transition_head", 0.8),
        ExpertPrefetchDescriptor(1, 0, 2, 2, "transition_head", 0.7),
        ExpertPrefetchDescriptor(1, 0, 3, 2, "transition_head", 0.6),
    ]
    groups = group_premap_descriptors_by_sample_layer(descriptors)

    report = replay_premap_address_manager(
        groups,
        capacity=2,
        descriptor_bytes=64,
    )

    assert report.event_count == 2
    assert report.descriptor_count == 4
    assert report.new_address_count == 3
    assert report.reused_address_count == 1
    assert report.reuse_rate == 0.25
    assert report.evicted_address_count == 1
    assert report.eviction_pressure == 1 / 3
    assert report.resident_address_count == 2
    assert report.resident_descriptor_bytes == 128
    assert report.max_resident_descriptor_bytes == 128
    assert report.prepared_descriptor_actual_bytes == 256
    assert report.payload_bytes == 0


def test_premap_address_replay_unbounded_keeps_all_addresses():
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 1, 2, 2, "transition_head", 0.8),
        ExpertPrefetchDescriptor(1, 0, 1, 2, "transition_head", 0.7),
    ]

    report = replay_premap_address_manager(
        group_premap_descriptors_by_sample_layer(descriptors),
        capacity=None,
        descriptor_bytes=32,
    )

    assert report.capacity is None
    assert report.new_address_count == 2
    assert report.reused_address_count == 1
    assert report.evicted_address_count == 0
    assert report.eviction_pressure == 0.0
    assert report.resident_descriptor_bytes == 64
    assert report.payload_bytes == 0


def test_load_premap_descriptor_jsonl(tmp_path):
    path = tmp_path / "descriptors.jsonl"
    rows = [
        {
            "sample_idx": 0,
            "layer_idx": 1,
            "expert_id": 7,
            "priority": 2,
            "source": "transition_head",
            "score": 0.9,
        },
        {
            "sample_idx": 0,
            "layer_idx": 2,
            "expert_id": 8,
            "priority": 4,
            "source": "mtp_token_extra_head",
            "score": 0.7,
        },
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    descriptors = load_premap_descriptor_jsonl(path)

    assert len(descriptors) == 2
    assert descriptors[0].sample_idx == 0
    assert descriptors[0].layer_idx == 1
    assert descriptors[0].expert_id == 7
    assert descriptors[1].source == "mtp_token_extra_head"


def test_group_premap_descriptors_preserves_input_event_order():
    descriptors = [
        ExpertPrefetchDescriptor(1, 1, 9, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.8),
        ExpertPrefetchDescriptor(1, 1, 8, 2, "transition_head", 0.7),
        ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.6),
    ]

    groups = group_premap_descriptors_by_sample_layer(descriptors)

    assert [(group[0].sample_idx, group[0].layer_idx) for group in groups] == [
        (1, 1),
        (0, 0),
        (0, 1),
    ]
    assert [descriptor.expert_id for descriptor in groups[0]] == [9, 8]
