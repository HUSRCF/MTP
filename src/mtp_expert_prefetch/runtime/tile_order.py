"""Cache-locality metrics for grouped-GEMM tile visitation order.

This module is intentionally payload-free.  It evaluates whether a proposed
expert/B-tile order improves reuse structure before we spend GPU time on a
rocWMMA or persistent grouped-GEMM implementation.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
import random
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TileRequest:
    window_id: int
    request_id: int
    tile_id: int
    expert_id: int
    transition_score: float = 0.0
    mtp_score: float = 0.0
    utility_score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "request_id": self.request_id,
            "tile_id": self.tile_id,
            "expert_id": self.expert_id,
            "transition_score": self.transition_score,
            "mtp_score": self.mtp_score,
            "utility_score": self.utility_score,
        }


def _score(record: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    if key in record and record[key] is not None:
        return float(record[key])
    scores = record.get("scores")
    if isinstance(scores, Mapping) and key in scores and scores[key] is not None:
        return float(scores[key])
    return default


def tile_request_from_mapping(record: Mapping[str, Any], *, fallback_request_id: int = 0) -> TileRequest:
    expert_id = int(record.get("expert_id", record.get("expert", 0)))
    if "tile_id" in record:
        tile_id = int(record["tile_id"])
    elif "b_tile_id" in record:
        tile_id = int(record["b_tile_id"])
    else:
        tile_id = expert_id
    return TileRequest(
        window_id=int(record.get("window_id", record.get("window", 0))),
        request_id=int(record.get("request_id", record.get("idx", fallback_request_id))),
        tile_id=tile_id,
        expert_id=expert_id,
        transition_score=_score(record, "transition_score"),
        mtp_score=_score(record, "mtp_score"),
        utility_score=_score(record, "utility_score"),
    )


def load_tile_requests_json(payload: Any) -> list[TileRequest]:
    if isinstance(payload, Mapping):
        raw_requests = payload.get("requests", payload.get("tile_requests"))
        if raw_requests is None:
            raise ValueError("tile-order JSON must contain 'requests' or 'tile_requests'")
    else:
        raw_requests = payload
    if not isinstance(raw_requests, list):
        raise TypeError("tile-order requests must be a JSON list")
    return [
        tile_request_from_mapping(record, fallback_request_id=index)
        for index, record in enumerate(raw_requests)
    ]


def generate_synthetic_tile_requests(
    *,
    num_windows: int,
    requests_per_window: int,
    num_experts: int,
    tiles_per_expert: int,
    hot_experts: int,
    novelty_experts: int,
    seed: int,
) -> list[TileRequest]:
    """Generate a deterministic locality trace with transition and MTP signals.

    Transition scores favor stable hot experts.  MTP scores favor a small
    novelty tail.  True demand is mostly transition-hot with a controlled
    novelty component so ordering policies can be compared under equal demand.
    """

    rng = random.Random(seed)
    hot_experts = max(1, min(int(hot_experts), int(num_experts)))
    novelty_experts = max(0, min(int(novelty_experts), int(num_experts) - hot_experts))
    transition_hot = list(range(hot_experts))
    novelty_hot = list(range(hot_experts, hot_experts + novelty_experts))
    cold = list(range(hot_experts + novelty_experts, num_experts))

    requests: list[TileRequest] = []
    request_id = 0
    for window_id in range(num_windows):
        window_phase = window_id % max(1, hot_experts)
        for _ in range(requests_per_window):
            draw = rng.random()
            if draw < 0.68 or not novelty_hot:
                expert = transition_hot[(window_phase + rng.randrange(hot_experts)) % hot_experts]
            elif draw < 0.86:
                expert = novelty_hot[rng.randrange(len(novelty_hot))]
            else:
                expert = cold[rng.randrange(len(cold))] if cold else rng.randrange(num_experts)
            local_tile = rng.randrange(tiles_per_expert)
            tile_id = expert * tiles_per_expert + local_tile
            transition_rank = transition_hot.index(expert) if expert in transition_hot else hot_experts
            novelty_rank = novelty_hot.index(expert) if expert in novelty_hot else novelty_experts
            transition_score = 1.0 / (1.0 + transition_rank) if expert in transition_hot else 0.02
            mtp_score = 1.0 / (1.0 + novelty_rank) if expert in novelty_hot else 0.05
            if expert in transition_hot:
                mtp_score += 0.10 * rng.random()
            utility_score = 0.75 * transition_score + 0.55 * mtp_score + 0.05 * rng.random()
            requests.append(
                TileRequest(
                    window_id=window_id,
                    request_id=request_id,
                    tile_id=tile_id,
                    expert_id=expert,
                    transition_score=transition_score,
                    mtp_score=mtp_score,
                    utility_score=utility_score,
                )
            )
            request_id += 1
    return requests


def group_by_window(requests: Sequence[TileRequest]) -> list[list[TileRequest]]:
    groups: dict[int, list[TileRequest]] = {}
    for request in requests:
        groups.setdefault(request.window_id, []).append(request)
    return [groups[key] for key in sorted(groups)]


def order_window(
    requests: Sequence[TileRequest],
    *,
    policy: str,
    rng: random.Random,
) -> list[TileRequest]:
    if policy == "linear":
        return list(requests)
    if policy == "random":
        ordered = list(requests)
        rng.shuffle(ordered)
        return ordered
    if policy == "expert_major":
        return sorted(requests, key=lambda item: (item.expert_id, item.tile_id, item.request_id))
    if policy == "b_tile_grouped":
        return sorted(requests, key=lambda item: (item.tile_id, item.expert_id, item.request_id))
    if policy == "transition_hot_first":
        return sorted(
            requests,
            key=lambda item: (-item.transition_score, item.tile_id, item.expert_id, item.request_id),
        )
    if policy == "mtp_transition_hot_first":
        return sorted(
            requests,
            key=lambda item: (
                -(item.transition_score + item.mtp_score),
                -item.mtp_score,
                item.tile_id,
                item.request_id,
            ),
        )
    if policy == "utility_hot_first":
        return sorted(
            requests,
            key=lambda item: (-item.utility_score, item.tile_id, item.expert_id, item.request_id),
        )
    if policy == "oracle_cache_aware":
        counts = Counter(item.tile_id for item in requests)
        return sorted(
            requests,
            key=lambda item: (-counts[item.tile_id], item.tile_id, item.expert_id, item.request_id),
        )
    raise ValueError(f"unknown tile-order policy: {policy}")


def order_tile_requests(
    requests: Sequence[TileRequest],
    *,
    policy: str,
    seed: int = 0,
) -> list[TileRequest]:
    rng = random.Random(seed)
    ordered: list[TileRequest] = []
    for window in group_by_window(requests):
        ordered.extend(order_window(window, policy=policy, rng=rng))
    return ordered


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


def reuse_distances(tile_ids: Sequence[int]) -> list[int]:
    last_seen: dict[int, int] = {}
    distances: list[int] = []
    for index, tile_id in enumerate(tile_ids):
        previous = last_seen.get(tile_id)
        if previous is not None:
            distances.append(len(set(tile_ids[previous + 1 : index])))
        last_seen[tile_id] = index
    return distances


def simulate_lru_hit_rate(tile_ids: Iterable[int], *, cache_size: int) -> float:
    if cache_size <= 0:
        return 0.0
    cache: OrderedDict[int, None] = OrderedDict()
    hits = 0
    total = 0
    for tile_id in tile_ids:
        total += 1
        if tile_id in cache:
            hits += 1
            cache.move_to_end(tile_id)
        else:
            cache[tile_id] = None
            if len(cache) > cache_size:
                cache.popitem(last=False)
    return hits / total if total else 0.0


def consecutive_run_stats(tile_ids: Sequence[int]) -> dict[str, float | int]:
    if not tile_ids:
        return {"mean": 0.0, "max": 0}
    runs: list[int] = []
    current = tile_ids[0]
    length = 1
    for tile_id in tile_ids[1:]:
        if tile_id == current:
            length += 1
        else:
            runs.append(length)
            current = tile_id
            length = 1
    runs.append(length)
    return {"mean": float(mean(runs)), "max": max(runs)}


def tile_order_hit_rate(
    original_windows: Sequence[Sequence[TileRequest]],
    ordered_windows: Sequence[Sequence[TileRequest]],
    *,
    top_k: int,
) -> float:
    rates: list[float] = []
    for original, ordered in zip(original_windows, ordered_windows, strict=True):
        counts = Counter(item.tile_id for item in original)
        true_hot = [tile for tile, _ in counts.most_common(top_k)]
        if not true_hot:
            continue
        first_unique: list[int] = []
        seen: set[int] = set()
        for item in ordered:
            if item.tile_id not in seen:
                first_unique.append(item.tile_id)
                seen.add(item.tile_id)
            if len(first_unique) >= len(true_hot):
                break
        rates.append(len(set(true_hot) & set(first_unique)) / len(true_hot))
    return float(mean(rates)) if rates else 0.0


def unique_tiles_per_window(windows: Sequence[Sequence[TileRequest]]) -> dict[str, float | int]:
    values = [len({item.tile_id for item in window}) for window in windows]
    if not values:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0}
    return {
        "mean": float(mean(values)),
        "p50": float(_percentile(values, 0.50) or 0.0),
        "p95": float(_percentile(values, 0.95) or 0.0),
        "max": max(values),
    }


def evaluate_tile_order_policy(
    requests: Sequence[TileRequest],
    *,
    policy: str,
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
    seed: int = 0,
) -> dict[str, Any]:
    original_windows = group_by_window(requests)
    ordered = order_tile_requests(requests, policy=policy, seed=seed)
    ordered_windows = group_by_window(ordered)
    tile_ids = [item.tile_id for item in ordered]
    distances = reuse_distances(tile_ids)
    return {
        "policy": policy,
        "request_count": len(ordered),
        "window_count": len(ordered_windows),
        "unique_tiles_total": len(set(tile_ids)),
        "unique_tiles_per_window": unique_tiles_per_window(ordered_windows),
        "reuse_distance": {
            "count": len(distances),
            "mean": float(mean(distances)) if distances else None,
            "p50": _percentile(distances, 0.50),
            "p95": _percentile(distances, 0.95),
            "max": max(distances) if distances else None,
        },
        "lru_hit_rate": {
            str(size): simulate_lru_hit_rate(tile_ids, cache_size=int(size))
            for size in cache_sizes
        },
        "consecutive_same_tile_run": consecutive_run_stats(tile_ids),
        "tile_order_hit_rate": tile_order_hit_rate(
            original_windows,
            ordered_windows,
            top_k=tile_order_top_k,
        ),
        "first_tiles": tile_ids[: min(16, len(tile_ids))],
    }


def evaluate_tile_order_policies(
    requests: Sequence[TileRequest],
    *,
    policies: Sequence[str],
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
    seed: int = 0,
) -> dict[str, Any]:
    policy_reports = [
        evaluate_tile_order_policy(
            requests,
            policy=policy,
            cache_sizes=cache_sizes,
            tile_order_top_k=tile_order_top_k,
            seed=seed,
        )
        for policy in policies
    ]
    best_by_cache = {}
    for size in cache_sizes:
        key = str(size)
        best = max(policy_reports, key=lambda row: row["lru_hit_rate"][key])
        best_by_cache[key] = {
            "policy": best["policy"],
            "lru_hit_rate": best["lru_hit_rate"][key],
        }
    best_reuse = min(
        policy_reports,
        key=lambda row: (
            float("inf")
            if row["reuse_distance"]["mean"] is None
            else row["reuse_distance"]["mean"]
        ),
    )
    return {
        "request_count": len(requests),
        "window_count": len(group_by_window(requests)),
        "policies": policy_reports,
        "best_by_cache_size": best_by_cache,
        "best_reuse_distance_policy": best_reuse["policy"],
    }

