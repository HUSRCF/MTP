from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
import hashlib
from statistics import mean
import time
from typing import Any, Sequence

import torch

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
    tile_multiset_hash: str | None
    order_hash: str | None
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


def build_layer_prior_plan_report_from_router_topk(
    *,
    layer_id: int,
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
    prior: LayerTilePrior,
    prior_id: str | None = None,
    prior_hash: str | None = None,
    tiles_per_expert: int = 1,
    token_window_size: int = 0,
    top_utility_override: int = 0,
    cache_sizes: Sequence[int] = (8, 16, 32),
    tile_order_top_k: int = 8,
    metrics_mode: str = "full",
) -> tuple[DescriptorOrderReport | None, str | None]:
    """Build a descriptor-order report without materializing TileRequest objects.

    This mirrors the C++ ``layer_prior_plan`` benchmark path: the current true
    router multiset is bucketed by B tile, the calibrated per-layer group order
    is filtered to present groups, and only the visitation order is changed.
    The returned baseline hash is the original tile visitation order hash.
    """

    ids = topk_ids.detach().cpu().to(torch.long)
    weights = topk_weights.detach().cpu().to(torch.float32)
    if ids.ndim != 2 or weights.shape != ids.shape:
        return None, None

    tiles_per_expert = max(1, int(tiles_per_expert))
    token_window_size = int(token_window_size)
    prior_order = prior.order_for_layer(int(layer_id))
    policy = f"layer_prior_{prior.score_name}"
    if top_utility_override:
        policy = f"{policy}_top{int(top_utility_override)}_utility_override"

    if str(metrics_mode).strip().lower() in {"count_only", "counts", "audit_count"}:
        return _build_layer_prior_count_only_report_from_topk_tensor(
            ids=ids,
            prior=prior,
            prior_id=prior_id,
            prior_hash=prior_hash,
            tiles_per_expert=tiles_per_expert,
            token_window_size=token_window_size,
            policy=policy,
            top_utility_override=int(top_utility_override),
        )

    if tiles_per_expert == 1 and int(top_utility_override) == 0:
        return _build_layer_prior_plan_report_from_topk_tensor(
            layer_id=layer_id,
            ids=ids,
            prior=prior,
            prior_order=prior_order,
            prior_id=prior_id,
            prior_hash=prior_hash,
            token_window_size=token_window_size,
            cache_sizes=cache_sizes,
            tile_order_top_k=int(tile_order_top_k),
            metrics_mode=metrics_mode,
            policy=policy,
        )

    start_ns = time.perf_counter_ns()
    original_windows: list[list[int]] = []
    original_score_windows: list[list[float]] = []
    for token_idx in range(int(ids.shape[0])):
        window_id = 0
        if token_window_size > 0:
            window_id = int(token_idx // token_window_size)
        while len(original_windows) <= window_id:
            original_windows.append([])
            original_score_windows.append([])
        for expert_tensor, weight_tensor in zip(
            ids[token_idx].tolist(),
            weights[token_idx].tolist(),
            strict=True,
        ):
            expert = int(expert_tensor)
            if expert < 0:
                continue
            score = float(weight_tensor)
            for tile_local in range(tiles_per_expert):
                tile_id = expert * tiles_per_expert + int(tile_local)
                original_windows[window_id].append(tile_id)
                original_score_windows[window_id].append(score)

    if not any(original_windows):
        return None, None

    ordered_windows = [
        _order_tile_id_window_with_layer_prior_plan(
            tile_ids=window_tiles,
            utility_scores=window_scores,
            prior_order=prior_order,
            top_utility_override=int(top_utility_override),
        )
        for window_tiles, window_scores in zip(
            original_windows,
            original_score_windows,
            strict=True,
        )
    ]
    order_build_us = (time.perf_counter_ns() - start_ns) / 1000.0

    original_tile_ids = [tile for window in original_windows for tile in window]
    ordered_tile_ids = [tile for window in ordered_windows for tile in window]
    metrics = _evaluate_ordered_tile_id_windows(
        original_windows=original_windows,
        ordered_windows=ordered_windows,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=int(tile_order_top_k),
        metrics_mode=metrics_mode,
    )
    report = DescriptorOrderReport(
        policy=policy,
        descriptor_count=len(original_tile_ids),
        tile_multiset_hash=hash_ints(sorted(original_tile_ids)),
        order_hash=hash_ints(ordered_tile_ids),
        order_build_us=order_build_us,
        metrics=metrics,
        prior_id=prior_id or str(prior.metadata.get("experiment_id") or prior.score_name),
        prior_hash=prior_hash,
        top_utility_override=int(top_utility_override),
    )
    return report, hash_ints(original_tile_ids)


def _build_layer_prior_count_only_report_from_topk_tensor(
    *,
    ids: torch.Tensor,
    prior: LayerTilePrior,
    prior_id: str | None,
    prior_hash: str | None,
    tiles_per_expert: int,
    token_window_size: int,
    policy: str,
    top_utility_override: int,
) -> tuple[DescriptorOrderReport | None, str | None]:
    start_ns = time.perf_counter_ns()
    token_count = int(ids.shape[0])
    top_k = int(ids.shape[1])
    if token_count <= 0 or top_k <= 0:
        return None, None
    valid = ids[ids >= 0]
    if valid.numel() == 0:
        return None, None
    request_count = int(valid.numel()) * max(1, int(tiles_per_expert))
    window_size = token_count if token_window_size <= 0 else max(1, int(token_window_size))
    window_count = (token_count + window_size - 1) // window_size
    if int(tiles_per_expert) == 1:
        unique_tiles_total = int(torch.unique(valid).numel())
    else:
        unique_experts = int(torch.unique(valid).numel())
        unique_tiles_total = unique_experts * max(1, int(tiles_per_expert))
    order_build_us = (time.perf_counter_ns() - start_ns) / 1000.0
    metrics = {
        "policy": policy,
        "metrics_mode": "count_only",
        "request_count": request_count,
        "window_count": int(window_count),
        "unique_tiles_total": int(unique_tiles_total),
        "unique_tiles_per_window": {
            "mean": None,
            "p50": None,
            "p95": None,
            "max": None,
            "skipped_reason": "count_only_summary_mode",
        },
        "reuse_distance": {
            "count": None,
            "mean": None,
            "p50": None,
            "p95": None,
            "max": None,
            "skipped_reason": "count_only_summary_mode",
        },
        "lru_hit_rate": {},
        "consecutive_same_tile_run": {
            "mean": None,
            "max": None,
            "skipped_reason": "count_only_summary_mode",
        },
        "tile_order_hit_rate": None,
        "first_tiles": [],
        "hashes_skipped_reason": "count_only_summary_mode",
    }
    report = DescriptorOrderReport(
        policy=policy,
        descriptor_count=request_count,
        tile_multiset_hash=None,
        order_hash=None,
        order_build_us=order_build_us,
        metrics=metrics,
        prior_id=prior_id or str(prior.metadata.get("experiment_id") or prior.score_name),
        prior_hash=prior_hash,
        top_utility_override=int(top_utility_override),
    )
    return report, None


def _build_layer_prior_plan_report_from_topk_tensor(
    *,
    layer_id: int,
    ids: torch.Tensor,
    prior: LayerTilePrior,
    prior_order: Sequence[int],
    prior_id: str | None,
    prior_hash: str | None,
    token_window_size: int,
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
    metrics_mode: str,
    policy: str,
) -> tuple[DescriptorOrderReport | None, str | None]:
    start_ns = time.perf_counter_ns()
    token_count = int(ids.shape[0])
    top_k = int(ids.shape[1])
    if token_count <= 0 or top_k <= 0:
        return None, None

    valid_ids = ids
    if bool((valid_ids < 0).any().item()):
        return None, None

    max_seen = int(valid_ids.max().item()) if valid_ids.numel() else -1
    max_prior = max((int(tile) for tile in prior_order), default=-1)
    rank_size = max(max_seen, max_prior) + 1
    if rank_size <= 0:
        return None, None
    rank = torch.arange(rank_size, dtype=torch.long) + len(prior_order)
    for order_idx, tile_raw in enumerate(prior_order):
        tile = int(tile_raw)
        if 0 <= tile < rank_size:
            rank[tile] = int(order_idx)

    window_size = token_count if token_window_size <= 0 else max(1, int(token_window_size))
    original_windows: list[list[int]] = []
    ordered_windows: list[list[int]] = []
    for token_start in range(0, token_count, window_size):
        token_end = min(token_start + window_size, token_count)
        window = valid_ids[token_start:token_end].reshape(-1)
        if window.numel() == 0:
            original_windows.append([])
            ordered_windows.append([])
            continue
        original = [int(tile) for tile in window.tolist()]
        ranks = rank[window]
        try:
            order_indices = torch.argsort(ranks, stable=True)
        except TypeError:
            order_indices = torch.argsort(ranks)
        ordered = [int(tile) for tile in window[order_indices].tolist()]
        original_windows.append(original)
        ordered_windows.append(ordered)

    order_build_us = (time.perf_counter_ns() - start_ns) / 1000.0
    original_tile_ids = [tile for window in original_windows for tile in window]
    if not original_tile_ids:
        return None, None
    ordered_tile_ids = [tile for window in ordered_windows for tile in window]
    metrics = _evaluate_ordered_tile_id_windows(
        original_windows=original_windows,
        ordered_windows=ordered_windows,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=int(tile_order_top_k),
        metrics_mode=metrics_mode,
    )
    report = DescriptorOrderReport(
        policy=policy,
        descriptor_count=len(original_tile_ids),
        tile_multiset_hash=hash_ints(sorted(original_tile_ids)),
        order_hash=hash_ints(ordered_tile_ids),
        order_build_us=order_build_us,
        metrics=metrics,
        prior_id=prior_id or str(prior.metadata.get("experiment_id") or prior.score_name),
        prior_hash=prior_hash,
        top_utility_override=0,
    )
    return report, hash_ints(original_tile_ids)


def _order_tile_id_window_with_layer_prior_plan(
    *,
    tile_ids: Sequence[int],
    utility_scores: Sequence[float],
    prior_order: Sequence[int],
    top_utility_override: int,
) -> list[int]:
    if not tile_ids:
        return []
    groups: dict[int, list[int]] = {}
    max_scores: dict[int, float] = {}
    total_scores: dict[int, float] = {}
    counts: dict[int, int] = {}
    for tile_raw, score_raw in zip(tile_ids, utility_scores, strict=True):
        tile = int(tile_raw)
        score = float(score_raw)
        group = groups.setdefault(tile, [])
        group.append(tile)
        max_scores[tile] = max(max_scores.get(tile, float("-inf")), score)
        total_scores[tile] = total_scores.get(tile, 0.0) + score
        counts[tile] = counts.get(tile, 0) + 1

    active_tiles = set(groups)
    ordered_tiles: list[int] = []
    selected: set[int] = set()
    if top_utility_override > 0:
        ranked = sorted(
            active_tiles,
            key=lambda tile: (-max_scores[tile], -total_scores[tile], -counts[tile], tile),
        )
        for tile in ranked[: int(top_utility_override)]:
            ordered_tiles.append(tile)
            selected.add(tile)

    for tile_raw in prior_order:
        tile = int(tile_raw)
        if tile in active_tiles and tile not in selected:
            ordered_tiles.append(tile)
            selected.add(tile)

    for tile in sorted(active_tiles - selected):
        ordered_tiles.append(tile)

    ordered: list[int] = []
    for tile in ordered_tiles:
        ordered.extend(groups[tile])
    return ordered


def _evaluate_ordered_tile_id_windows(
    *,
    original_windows: Sequence[Sequence[int]],
    ordered_windows: Sequence[Sequence[int]],
    policy: str,
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
    metrics_mode: str = "full",
) -> dict[str, Any]:
    tile_ids = [tile for window in ordered_windows for tile in window]
    normalized_mode = str(metrics_mode).lower()
    minimal = normalized_mode in {"none", "minimal", "off"}
    compact = normalized_mode in {"compact", "light", "summary"}
    if minimal:
        return {
            "policy": policy,
            "metrics_mode": "none",
            "request_count": len(tile_ids),
            "window_count": len(ordered_windows),
            "unique_tiles_total": len(set(tile_ids)),
            "unique_tiles_per_window": {
                "mean": None,
                "p50": None,
                "p95": None,
                "max": None,
                "skipped_reason": "none_metrics_mode",
            },
            "reuse_distance": {
                "count": None,
                "mean": None,
                "p50": None,
                "p95": None,
                "max": None,
                "skipped_reason": "none_metrics_mode",
            },
            "lru_hit_rate": {},
            "consecutive_same_tile_run": {
                "mean": None,
                "max": None,
                "skipped_reason": "none_metrics_mode",
            },
            "tile_order_hit_rate": None,
            "first_tiles": [],
        }

    distances = [] if compact else _reuse_distances_fast(tile_ids)
    payload = {
        "policy": policy,
        "request_count": len(tile_ids),
        "window_count": len(ordered_windows),
        "unique_tiles_total": len(set(tile_ids)),
        "unique_tiles_per_window": _unique_tile_id_stats(ordered_windows),
        "reuse_distance": {
            "count": len(distances),
            "mean": float(mean(distances)) if distances else None,
            "p50": _percentile(distances, 0.50),
            "p95": _percentile(distances, 0.95),
            "max": max(distances) if distances else None,
        },
        "lru_hit_rate": {
            str(size): _simulate_lru_hit_rate(tile_ids, cache_size=int(size))
            for size in cache_sizes
        },
        "consecutive_same_tile_run": _consecutive_run_stats(tile_ids),
        "tile_order_hit_rate": _tile_order_hit_rate_from_ids(
            original_windows,
            ordered_windows,
            top_k=int(tile_order_top_k),
        ),
        "first_tiles": tile_ids[: min(16, len(tile_ids))],
    }
    if compact:
        payload["metrics_mode"] = "compact"
        payload["reuse_distance"] = {
            "count": None,
            "mean": None,
            "p50": None,
            "p95": None,
            "max": None,
            "skipped_reason": "compact_metrics_mode",
        }
    return payload


def _unique_tile_id_stats(windows: Sequence[Sequence[int]]) -> dict[str, float | int]:
    values = [len(set(int(tile) for tile in window)) for window in windows]
    if not values:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0}
    return {
        "mean": float(mean(values)),
        "p50": float(_percentile(values, 0.50) or 0.0),
        "p95": float(_percentile(values, 0.95) or 0.0),
        "max": max(values),
    }


def _simulate_lru_hit_rate(tile_ids: Sequence[int], *, cache_size: int) -> float:
    if cache_size <= 0:
        return 0.0
    cache: OrderedDict[int, None] = OrderedDict()
    hits = 0
    total = 0
    for tile_raw in tile_ids:
        tile = int(tile_raw)
        total += 1
        if tile in cache:
            hits += 1
            cache.move_to_end(tile)
        else:
            cache[tile] = None
            if len(cache) > cache_size:
                cache.popitem(last=False)
    return hits / total if total else 0.0


def _consecutive_run_stats(tile_ids: Sequence[int]) -> dict[str, float | int]:
    if not tile_ids:
        return {"mean": 0.0, "max": 0}
    runs: list[int] = []
    current = int(tile_ids[0])
    length = 1
    for tile_raw in tile_ids[1:]:
        tile = int(tile_raw)
        if tile == current:
            length += 1
        else:
            runs.append(length)
            current = tile
            length = 1
    runs.append(length)
    return {"mean": float(mean(runs)), "max": max(runs)}


def _tile_order_hit_rate_from_ids(
    original_windows: Sequence[Sequence[int]],
    ordered_windows: Sequence[Sequence[int]],
    *,
    top_k: int,
) -> float:
    rates: list[float] = []
    for original, ordered in zip(original_windows, ordered_windows, strict=True):
        counts = Counter(int(tile) for tile in original)
        true_hot = [tile for tile, _ in counts.most_common(top_k)]
        if not true_hot:
            continue
        first_unique: list[int] = []
        seen: set[int] = set()
        for tile_raw in ordered:
            tile = int(tile_raw)
            if tile not in seen:
                first_unique.append(tile)
                seen.add(tile)
            if len(first_unique) >= len(true_hot):
                break
        rates.append(len(set(true_hot) & set(first_unique)) / len(true_hot))
    return float(mean(rates)) if rates else 0.0


def _percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _reuse_distances_fast(tile_ids: Sequence[int]) -> list[int]:
    if not tile_ids:
        return []
    last_seen: dict[int, int] = {}
    bit = [0] * (len(tile_ids) + 2)

    def add(index: int, delta: int) -> None:
        i = index + 1
        while i < len(bit):
            bit[i] += delta
            i += i & -i

    def prefix(index: int) -> int:
        if index < 0:
            return 0
        i = index + 1
        total = 0
        while i > 0:
            total += bit[i]
            i -= i & -i
        return total

    distances: list[int] = []
    for index, tile_raw in enumerate(tile_ids):
        tile = int(tile_raw)
        previous = last_seen.get(tile)
        if previous is not None:
            distances.append(prefix(index - 1) - prefix(previous))
            add(previous, -1)
        last_seen[tile] = index
        add(index, 1)
    return distances


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
