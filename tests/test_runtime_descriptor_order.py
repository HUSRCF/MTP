from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    ExpertPrefetchDescriptor,
    TileRequest,
    order_tile_request_stream,
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


def test_order_tile_request_stream_preserves_token_row_metadata():
    requests = [
        TileRequest(
            window_id=0,
            request_id=0,
            tile_id=1,
            expert_id=1,
            utility_score=0.1,
            token_index=7,
            layer_idx=2,
            row_id=0,
            source_policy="target_topk",
        ),
        TileRequest(
            window_id=0,
            request_id=1,
            tile_id=2,
            expert_id=2,
            utility_score=0.9,
            token_index=7,
            layer_idx=2,
            row_id=1,
            source_policy="target_topk",
        ),
        TileRequest(
            window_id=0,
            request_id=2,
            tile_id=1,
            expert_id=1,
            utility_score=0.2,
            token_index=8,
            layer_idx=2,
            row_id=0,
            source_policy="target_topk",
        ),
    ]

    ordered, report = order_tile_request_stream(requests, policy="utility_tile_grouped")

    assert sorted(tuple(item.as_dict().items()) for item in ordered) == sorted(
        tuple(item.as_dict().items()) for item in requests
    )
    assert [item.tile_id for item in ordered] == [2, 1, 1]
    assert ordered[0].token_index == 7
    assert ordered[0].layer_idx == 2
    assert ordered[0].row_id == 1
    assert report.descriptor_count == len(requests)
    assert report.tile_multiset_hash
    assert report.order_hash
