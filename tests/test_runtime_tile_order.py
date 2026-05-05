from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    TileRequest,
    evaluate_tile_order_policies,
    order_tile_requests,
    simulate_lru_hit_rate,
)


def test_b_tile_grouped_improves_tiny_lru_hit_rate():
    requests = [
        TileRequest(0, 0, 1, 1),
        TileRequest(0, 1, 2, 2),
        TileRequest(0, 2, 1, 1),
        TileRequest(0, 3, 2, 2),
    ]

    linear = [item.tile_id for item in order_tile_requests(requests, policy="linear")]
    grouped = [item.tile_id for item in order_tile_requests(requests, policy="b_tile_grouped")]

    assert linear == [1, 2, 1, 2]
    assert grouped == [1, 1, 2, 2]
    assert simulate_lru_hit_rate(linear, cache_size=1) == 0.0
    assert simulate_lru_hit_rate(grouped, cache_size=1) == 0.5


def test_transition_hot_first_uses_transition_score_before_mtp_score():
    requests = [
        TileRequest(0, 0, 10, 10, transition_score=0.1, mtp_score=10.0),
        TileRequest(0, 1, 20, 20, transition_score=0.9, mtp_score=0.0),
        TileRequest(0, 2, 30, 30, transition_score=0.5, mtp_score=1.0),
    ]

    ordered = order_tile_requests(requests, policy="transition_hot_first")

    assert [item.tile_id for item in ordered] == [20, 30, 10]


def test_utility_tile_grouped_keeps_tile_runs_while_ordering_hot_groups():
    requests = [
        TileRequest(0, 0, 1, 1, utility_score=0.1),
        TileRequest(0, 1, 2, 2, utility_score=0.9),
        TileRequest(0, 2, 1, 1, utility_score=0.2),
        TileRequest(0, 3, 2, 2, utility_score=0.8),
        TileRequest(0, 4, 3, 3, utility_score=0.7),
    ]

    ordered = order_tile_requests(requests, policy="utility_tile_grouped")

    assert [item.tile_id for item in ordered] == [2, 2, 3, 1, 1]


def test_tile_order_report_identifies_oracle_reuse_policy():
    requests = [
        TileRequest(0, 0, 1, 1, utility_score=0.2),
        TileRequest(0, 1, 2, 2, utility_score=0.1),
        TileRequest(0, 2, 1, 1, utility_score=0.3),
        TileRequest(0, 3, 3, 3, utility_score=0.9),
        TileRequest(0, 4, 1, 1, utility_score=0.4),
    ]

    report = evaluate_tile_order_policies(
        requests,
        policies=["linear", "utility_hot_first", "oracle_cache_aware"],
        cache_sizes=[1, 2],
        tile_order_top_k=1,
    )

    by_policy = {row["policy"]: row for row in report["policies"]}
    assert by_policy["oracle_cache_aware"]["first_tiles"][:3] == [1, 1, 1]
    assert by_policy["oracle_cache_aware"]["lru_hit_rate"]["1"] >= by_policy["linear"][
        "lru_hit_rate"
    ]["1"]
    assert report["best_by_cache_size"]["1"]["lru_hit_rate"] == by_policy["oracle_cache_aware"][
        "lru_hit_rate"
    ]["1"]
