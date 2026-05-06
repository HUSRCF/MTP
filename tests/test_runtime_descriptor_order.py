from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    ExpertPrefetchDescriptor,
    order_prefetch_descriptors,
)


def test_order_prefetch_descriptors_preserves_descriptor_multiset():
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.1),
        ExpertPrefetchDescriptor(0, 0, 2, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 1, 4, "mtp_token_extra_head", 0.2),
        ExpertPrefetchDescriptor(0, 0, 3, 4, "mtp_token_extra_head", 0.7),
    ]

    ordered, report = order_prefetch_descriptors(
        descriptors,
        policy="utility_tile_grouped",
        cache_sizes=[1, 2],
    )

    assert sorted(tuple(item.as_dict().items()) for item in ordered) == sorted(
        tuple(item.as_dict().items()) for item in descriptors
    )
    assert [item.expert_id for item in ordered] == [2, 3, 1, 1]
    assert report.descriptor_count == len(descriptors)
    assert report.tile_multiset_hash
    assert report.order_hash
    assert report.metrics["lru_hit_rate"]["1"] == 0.25


def test_descriptor_order_policy_changes_order_hash_not_multiset_hash():
    descriptors = [
        ExpertPrefetchDescriptor(0, 0, 1, 2, "transition_head", 0.1),
        ExpertPrefetchDescriptor(0, 0, 2, 2, "transition_head", 0.9),
        ExpertPrefetchDescriptor(0, 0, 1, 4, "mtp_token_extra_head", 0.2),
    ]

    _, linear = order_prefetch_descriptors(descriptors, policy="linear")
    _, utility = order_prefetch_descriptors(descriptors, policy="utility_tile_grouped")

    assert linear.tile_multiset_hash == utility.tile_multiset_hash
    assert linear.order_hash != utility.order_hash
