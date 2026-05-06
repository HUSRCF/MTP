from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from typing import Any, Sequence

from mtp_expert_prefetch.runtime.premap import ExpertPrefetchDescriptor
from mtp_expert_prefetch.runtime.tile_order import (
    LayerTilePrior,
    TileRequest,
    evaluate_ordered_tile_requests,
    evaluate_tile_order_policy,
    order_tile_requests,
    order_tile_requests_with_layer_prior,
)


@dataclass(frozen=True)
class DescriptorOrderReport:
    policy: str
    descriptor_count: int
    tile_multiset_hash: str
    order_hash: str
    order_build_us: float
    metrics: dict[str, Any]
    prior_id: str | None = None
    prior_hash: str | None = None
    top_utility_override: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "policy": self.policy,
            "descriptor_count": int(self.descriptor_count),
            "tile_multiset_hash": self.tile_multiset_hash,
            "order_hash": self.order_hash,
            "order_build_us": float(self.order_build_us),
            "metrics": self.metrics,
        }
        if self.prior_id is not None:
            payload["prior_id"] = self.prior_id
        if self.prior_hash is not None:
            payload["prior_hash"] = self.prior_hash
        if self.top_utility_override is not None:
            payload["top_utility_override"] = int(self.top_utility_override)
        return payload


def order_prefetch_descriptors(
    descriptors: Sequence[ExpertPrefetchDescriptor],
    *,
    policy: str = "utility_tile_grouped",
    tiles_per_expert: int = 1,
    cache_sizes: Sequence[int] = (8, 16, 32),
    tile_order_top_k: int = 8,
    seed: int = 0,
) -> tuple[list[ExpertPrefetchDescriptor], DescriptorOrderReport]:
    """Reorder descriptors without changing the descriptor multiset.

    This is the runtime-safe descriptor-order action: true router output and
    candidate membership are unchanged; only visitation order changes.
    """

    start_ns = time.perf_counter_ns()
    requests = descriptors_to_tile_requests(
        descriptors,
        tiles_per_expert=tiles_per_expert,
    )
    ordered_requests = order_tile_requests(requests, policy=policy, seed=seed)
    by_request_id = {request.request_id: descriptor for request, descriptor in zip(
        requests, descriptors, strict=True
    )}
    ordered_descriptors = [by_request_id[request.request_id] for request in ordered_requests]
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
    metrics = evaluate_tile_order_policy(
        requests,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=tile_order_top_k,
        seed=seed,
    )
    order_ids = [request.tile_id for request in ordered_requests]
    multiset_ids = sorted(request.tile_id for request in requests)
    report = DescriptorOrderReport(
        policy=policy,
        descriptor_count=len(descriptors),
        tile_multiset_hash=hash_ints(multiset_ids),
        order_hash=hash_ints(order_ids),
        order_build_us=elapsed_us,
        metrics=metrics,
    )
    return ordered_descriptors, report


def order_tile_request_stream(
    requests: Sequence[TileRequest],
    *,
    policy: str = "utility_tile_grouped",
    cache_sizes: Sequence[int] = (8, 16, 32),
    tile_order_top_k: int = 8,
    seed: int = 0,
) -> tuple[list[TileRequest], DescriptorOrderReport]:
    """Reorder a token/row-level tile stream without changing its multiset."""

    start_ns = time.perf_counter_ns()
    ordered_requests = order_tile_requests(requests, policy=policy, seed=seed)
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
    metrics = evaluate_tile_order_policy(
        requests,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=tile_order_top_k,
        seed=seed,
    )
    order_ids = [request.tile_id for request in ordered_requests]
    multiset_ids = sorted(request.tile_id for request in requests)
    report = DescriptorOrderReport(
        policy=policy,
        descriptor_count=len(requests),
        tile_multiset_hash=hash_ints(multiset_ids),
        order_hash=hash_ints(order_ids),
        order_build_us=elapsed_us,
        metrics=metrics,
    )
    return ordered_requests, report


def order_tile_request_stream_with_layer_prior(
    requests: Sequence[TileRequest],
    *,
    prior: LayerTilePrior,
    prior_id: str | None = None,
    prior_hash: str | None = None,
    top_utility_override: int = 0,
    cache_sizes: Sequence[int] = (8, 16, 32),
    tile_order_top_k: int = 8,
) -> tuple[list[TileRequest], DescriptorOrderReport]:
    """Apply a calibrated layer-prior group order to a token/row tile stream."""

    start_ns = time.perf_counter_ns()
    ordered_requests = order_tile_requests_with_layer_prior(
        requests,
        prior=prior,
        top_utility_override=top_utility_override,
    )
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
    policy = f"layer_prior_{prior.score_name}"
    if top_utility_override:
        policy = f"{policy}_top{int(top_utility_override)}_utility_override"
    metrics = evaluate_ordered_tile_requests(
        requests,
        ordered_requests,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=tile_order_top_k,
    )
    order_ids = [request.tile_id for request in ordered_requests]
    multiset_ids = sorted(request.tile_id for request in requests)
    report = DescriptorOrderReport(
        policy=policy,
        descriptor_count=len(requests),
        tile_multiset_hash=hash_ints(multiset_ids),
        order_hash=hash_ints(order_ids),
        order_build_us=elapsed_us,
        metrics=metrics,
        prior_id=prior_id or str(prior.metadata.get("experiment_id") or prior.score_name),
        prior_hash=prior_hash,
        top_utility_override=int(top_utility_override),
    )
    return ordered_requests, report


def descriptors_to_tile_requests(
    descriptors: Sequence[ExpertPrefetchDescriptor],
    *,
    tiles_per_expert: int = 1,
) -> list[TileRequest]:
    window_ids: dict[tuple[int, int], int] = {}
    requests: list[TileRequest] = []
    for request_id, descriptor in enumerate(descriptors):
        key = (int(descriptor.sample_idx), int(descriptor.layer_idx))
        if key not in window_ids:
            window_ids[key] = len(window_ids)
        tile_id = int(descriptor.expert_id) * int(tiles_per_expert)
        score = float(descriptor.score)
        transition_score = score if descriptor.source.startswith("transition") else 0.0
        mtp_score = score if descriptor.source.startswith("mtp") else 0.0
        requests.append(
            TileRequest(
                window_id=window_ids[key],
                request_id=request_id,
                tile_id=tile_id,
                expert_id=int(descriptor.expert_id),
                transition_score=transition_score,
                mtp_score=mtp_score,
                utility_score=score,
            )
        )
    return requests


def hash_ints(values: Sequence[int]) -> str:
    payload = ",".join(str(int(value)) for value in values).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def hash_layer_tile_prior(prior: LayerTilePrior) -> str:
    encoded = json_dumps_canonical(prior.as_dict()).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def json_dumps_canonical(payload: Any) -> str:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
