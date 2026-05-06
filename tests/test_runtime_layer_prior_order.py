from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    TileRequest,
    build_layer_prior_plan_report_from_router_topk,
    build_layer_tile_prior,
    evaluate_ordered_tile_requests,
    hash_layer_tile_prior,
    order_tile_request_stream_with_layer_prior,
    order_tile_requests_with_layer_prior,
)
import torch


def _multiset(requests: list[TileRequest]) -> list[tuple[int, int, int]]:
    return sorted((item.request_id, item.tile_id, item.expert_id) for item in requests)


def test_layer_prior_orders_present_groups_without_changing_multiset():
    calibration = [
        TileRequest(0, 0, 2, 2, layer_idx=0),
        TileRequest(0, 1, 2, 2, layer_idx=0),
        TileRequest(0, 2, 1, 1, layer_idx=0),
        TileRequest(1, 3, 5, 5, layer_idx=1),
        TileRequest(1, 4, 4, 4, layer_idx=1),
        TileRequest(1, 5, 4, 4, layer_idx=1),
    ]
    prior = build_layer_tile_prior(calibration, score_name="frequency")
    heldout = [
        TileRequest(10, 10, 1, 1, layer_idx=0),
        TileRequest(10, 11, 3, 3, layer_idx=0),
        TileRequest(10, 12, 2, 2, layer_idx=0),
        TileRequest(10, 13, 1, 1, layer_idx=0),
    ]

    ordered = order_tile_requests_with_layer_prior(heldout, prior=prior)

    assert [item.tile_id for item in ordered] == [2, 1, 1, 3]
    assert _multiset(ordered) == _multiset(heldout)


def test_layer_prior_top_utility_override_moves_current_hot_group_first():
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 1, 1, layer_idx=0),
            TileRequest(0, 1, 1, 1, layer_idx=0),
            TileRequest(0, 2, 2, 2, layer_idx=0),
        ],
        score_name="frequency",
    )
    heldout = [
        TileRequest(10, 10, 1, 1, layer_idx=0, utility_score=0.1),
        TileRequest(10, 11, 3, 3, layer_idx=0, utility_score=0.9),
        TileRequest(10, 12, 1, 1, layer_idx=0, utility_score=0.2),
        TileRequest(10, 13, 2, 2, layer_idx=0, utility_score=0.3),
    ]

    ordered = order_tile_requests_with_layer_prior(
        heldout,
        prior=prior,
        top_utility_override=1,
    )

    assert [item.tile_id for item in ordered] == [3, 1, 1, 2]
    assert _multiset(ordered) == _multiset(heldout)


def test_layer_utility_prior_uses_calibrated_scores_and_evaluates_order():
    calibration = [
        TileRequest(0, 0, 1, 1, layer_idx=0, utility_score=0.1),
        TileRequest(0, 1, 2, 2, layer_idx=0, utility_score=0.8),
        TileRequest(0, 2, 1, 1, layer_idx=0, utility_score=0.1),
        TileRequest(0, 3, 3, 3, layer_idx=0, utility_score=0.5),
    ]
    prior = build_layer_tile_prior(calibration, score_name="utility")
    heldout = [
        TileRequest(1, 0, 1, 1, layer_idx=0),
        TileRequest(1, 1, 2, 2, layer_idx=0),
        TileRequest(1, 2, 3, 3, layer_idx=0),
        TileRequest(1, 3, 2, 2, layer_idx=0),
    ]

    ordered = order_tile_requests_with_layer_prior(heldout, prior=prior)
    report = evaluate_ordered_tile_requests(
        heldout,
        ordered,
        policy="layer_prior_utility",
        cache_sizes=[1, 2],
        tile_order_top_k=1,
    )

    assert [item.tile_id for item in ordered] == [2, 2, 3, 1]
    assert report["policy"] == "layer_prior_utility"
    assert report["request_count"] == len(heldout)


def test_layer_prior_descriptor_report_carries_prior_metadata():
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-exp"},
    )
    prior_hash = hash_layer_tile_prior(prior)
    requests = [
        TileRequest(1, 0, 1, 1, layer_idx=0),
        TileRequest(1, 1, 2, 2, layer_idx=0),
        TileRequest(1, 2, 1, 1, layer_idx=0),
    ]

    ordered, report = order_tile_request_stream_with_layer_prior(
        requests,
        prior=prior,
        prior_id="prior-exp",
        prior_hash=prior_hash,
    )

    assert [item.tile_id for item in ordered] == [2, 1, 1]
    assert report.policy == "layer_prior_frequency"
    assert report.prior_id == "prior-exp"
    assert report.prior_hash == prior_hash
    assert report.metrics["lru_hit_rate"]["8"] == 1 / 3


def test_layer_prior_plan_report_matches_tile_request_stream_metrics():
    prior = build_layer_tile_prior(
        [
            TileRequest(0, 0, 2, 2, layer_idx=0),
            TileRequest(0, 1, 2, 2, layer_idx=0),
            TileRequest(0, 2, 1, 1, layer_idx=0),
        ],
        score_name="frequency",
        metadata={"experiment_id": "prior-exp"},
    )
    prior_hash = hash_layer_tile_prior(prior)
    ids = torch.tensor([[1, 2], [1, 3], [2, 1]], dtype=torch.long)
    weights = torch.tensor([[0.7, 0.3], [0.6, 0.4], [0.9, 0.1]], dtype=torch.float32)
    requests: list[TileRequest] = []
    request_id = 0
    for token_idx in range(ids.shape[0]):
        for row_id in range(ids.shape[1]):
            expert = int(ids[token_idx, row_id])
            weight = float(weights[token_idx, row_id])
            requests.append(
                TileRequest(
                    window_id=token_idx // 2,
                    request_id=request_id,
                    tile_id=expert,
                    expert_id=expert,
                    transition_score=weight,
                    utility_score=weight,
                    layer_idx=0,
                )
            )
            request_id += 1

    _, object_report = order_tile_request_stream_with_layer_prior(
        requests,
        prior=prior,
        prior_id="prior-exp",
        prior_hash=prior_hash,
        cache_sizes=[1, 2, 8],
        tile_order_top_k=2,
    )
    plan_report, baseline_hash = build_layer_prior_plan_report_from_router_topk(
        layer_id=0,
        topk_ids=ids,
        topk_weights=weights,
        prior=prior,
        prior_id="prior-exp",
        prior_hash=prior_hash,
        token_window_size=2,
        cache_sizes=[1, 2, 8],
        tile_order_top_k=2,
    )

    assert plan_report is not None
    assert plan_report.policy == object_report.policy
    assert plan_report.descriptor_count == object_report.descriptor_count
    assert plan_report.tile_multiset_hash == object_report.tile_multiset_hash
    assert plan_report.order_hash == object_report.order_hash
    assert baseline_hash is not None
    assert plan_report.metrics == object_report.metrics
