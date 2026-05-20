from __future__ import annotations

import pytest
import torch

from mtp_expert_prefetch.runtime import (
    ControlledPremapAddressManager,
    ExpertPrefetchDescriptor,
    build_premap_descriptors,
    build_priority_masks,
    descriptor_summary,
    prepare_premap_address_plan,
)


def test_build_priority_masks_are_disjoint_and_ordered():
    transition = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85]]]])

    masks = build_priority_masks(transition, mtp, transition_topk=4, mtp_topk=4, max_extra=2)

    assert masks["P2_transition_top16"][0, 0, 0].tolist() == [
        True,
        True,
        True,
        True,
        False,
        False,
    ]
    assert not masks["P3_transition_top17_to_4"].any()
    assert masks["P4_mtp_extra1_to_4"][0, 0, 0].tolist() == [
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    assert not masks["P5_mtp_extra5_to_4"].any()


def test_build_premap_descriptors_deduplicates_by_best_priority():
    transition = torch.zeros((2, 1, 1, 8))
    mtp = torch.zeros_like(transition)
    transition[0, 0, 0, [0, 1, 2, 3]] = torch.tensor([0.9, 0.8, 0.7, 0.6])
    transition[1, 0, 0, [0, 1, 4, 5]] = torch.tensor([0.95, 0.75, 0.5, 0.4])
    mtp[:, 0, 0, [6, 7, 1, 2]] = torch.tensor([0.99, 0.88, 0.77, 0.66])
    sample_ids = torch.tensor([42, 42])

    descriptors = build_premap_descriptors(
        transition,
        mtp,
        sample_ids,
        transition_topk=4,
        mtp_topk=4,
        max_extra=2,
    )

    by_expert = {item.expert_id: item for item in descriptors}
    assert by_expert[0].priority == 2
    assert by_expert[1].priority == 2
    assert by_expert[6].priority == 4
    assert by_expert[7].priority == 4
    assert 2 in by_expert
    assert 6 in by_expert
    assert len(descriptors) == len(by_expert)

    summary = descriptor_summary(descriptors, expert_bytes=100)
    assert summary["num_descriptors"] == len(descriptors)
    assert summary["by_priority"]["2"] == 6
    assert summary["by_priority"]["4"] == 2
    assert summary["per_sample_layer_count"]["max"] == pytest.approx(8.0)
    assert summary["total_descriptor_bytes"] == 800
    assert summary["per_sample_layer_bytes"]["max"] == pytest.approx(800.0)


def test_prepare_premap_address_plan_builds_zero_payload_address_handles():
    descriptors = [
        ExpertPrefetchDescriptor(0, 2, 7, 3, "transition_tail", 0.50),
        ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
        ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
    ]

    plan = prepare_premap_address_plan(
        descriptors,
        descriptor_bytes=128,
        address_namespace="awq_descriptor",
    )
    repeated = prepare_premap_address_plan(
        list(reversed(descriptors)),
        descriptor_bytes=128,
        address_namespace="awq_descriptor",
    )
    other_namespace = prepare_premap_address_plan(
        descriptors,
        descriptor_bytes=128,
        address_namespace="other_descriptor",
    )

    assert plan.descriptor_count == 3
    assert plan.unique_experts == 2
    assert plan.unique_layers == 2
    assert plan.unique_sample_layers == 2
    assert plan.actual_bytes == 384
    assert plan.payload_bytes == 0
    assert [record.descriptor_slot for record in plan.records] == [0, 1, 2]
    assert [record.expert_id for record in plan.records] == [3, 7, 7]
    assert all(record.payload_bytes == 0 for record in plan.records)
    assert plan.records[0].address_key == "awq_descriptor:l1:e3"
    assert plan.by_priority == {"2": 1, "3": 1, "4": 1}
    assert plan.by_source["transition_head"] == 1
    assert plan.descriptor_hash == repeated.descriptor_hash
    assert plan.address_hash == repeated.address_hash
    assert plan.address_hash != other_namespace.address_hash


def test_prepare_premap_address_plan_rejects_negative_descriptor_bytes():
    with pytest.raises(ValueError, match="descriptor_bytes"):
        prepare_premap_address_plan([], descriptor_bytes=-1)


def test_premap_address_hash_changes_with_plan_semantics_but_key_reuses_address():
    transition = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 7, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    mtp = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75)],
        descriptor_bytes=64,
    )

    assert transition.records[0].address_key == mtp.records[0].address_key
    assert transition.descriptor_hash != mtp.descriptor_hash
    assert transition.address_hash != mtp.address_hash


def test_controlled_premap_address_manager_tracks_address_reuse_without_payload():
    first = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    second = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
            ExpertPrefetchDescriptor(0, 2, 9, 3, "transition_tail", 0.50),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=2)

    first_snapshot = manager.prepare(first)
    second_snapshot = manager.prepare(second)

    assert first_snapshot.prepared_plan_count == 1
    assert first_snapshot.prepared_record_count == 2
    assert first_snapshot.new_address_count == 2
    assert first_snapshot.reused_address_count == 0
    assert first_snapshot.prepared_descriptor_actual_bytes == 128
    assert first_snapshot.resident_descriptor_bytes == 128
    assert first_snapshot.payload_bytes == 0

    assert second_snapshot.prepared_plan_count == 2
    assert second_snapshot.prepared_record_count == 4
    assert second_snapshot.new_address_count == 3
    assert second_snapshot.reused_address_count == 1
    assert second_snapshot.resident_address_count == 2
    assert second_snapshot.evicted_address_count == 1
    assert second_snapshot.prepared_descriptor_actual_bytes == 256
    assert second_snapshot.resident_descriptor_bytes == 128
    assert second_snapshot.payload_bytes == 0
    assert manager.contains_address_key("expert_weight_descriptor:l1:e7")
    assert manager.contains_layer_expert(layer_idx=2, expert_id=9)
    assert not manager.contains_layer_expert(layer_idx=1, expert_id=3)
    handle = manager.resolve_layer_expert(layer_idx=2, expert_id=9)
    assert handle is not None
    assert handle.address_key == "expert_weight_descriptor:l2:e9"
    assert handle.descriptor_ptr == "descriptor://expert_weight_descriptor:l2:e9"
    assert handle.packed_weight_descriptor == (
        "packed_weight_descriptor://expert_weight_descriptor:l2:e9"
    )
    assert handle.scale_metadata_handle == (
        "scale_metadata://expert_weight_descriptor:l2:e9"
    )
    assert handle.payload_bytes == 0
    assert handle.handle_hash


def test_controlled_premap_address_manager_zero_capacity_counts_requests_only():
    plan = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=0)

    snapshot = manager.prepare(plan)

    assert snapshot.prepared_plan_count == 1
    assert snapshot.prepared_record_count == 1
    assert snapshot.new_address_count == 1
    assert snapshot.reused_address_count == 0
    assert snapshot.resident_address_count == 0
    assert snapshot.evicted_address_count == 1
    assert snapshot.prepared_descriptor_actual_bytes == 64
    assert snapshot.resident_descriptor_bytes == 0
    assert snapshot.payload_bytes == 0


def test_controlled_premap_address_manager_refreshes_reused_descriptor_bytes():
    small = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    large = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=128,
    )
    manager = ControlledPremapAddressManager(capacity=4)

    manager.prepare(small)
    snapshot = manager.prepare(large)

    assert snapshot.new_address_count == 1
    assert snapshot.reused_address_count == 1
    assert snapshot.prepared_descriptor_actual_bytes == 192
    assert snapshot.resident_descriptor_bytes == 128
    assert snapshot.payload_bytes == 0
