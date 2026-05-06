"""Cache-locality metrics for grouped-GEMM tile visitation order.

This module is intentionally payload-free.  It evaluates whether a proposed
expert/B-tile order improves reuse structure before we spend GPU time on a
rocWMMA or persistent grouped-GEMM implementation.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
import json
from pathlib import Path
import random
from statistics import mean
from typing import Any, Callable, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TileRequest:
    window_id: int
    request_id: int
    tile_id: int
    expert_id: int
    transition_score: float = 0.0
    mtp_score: float = 0.0
    utility_score: float = 0.0
    sample_idx: int | None = None
    token_index: int | None = None
    layer_idx: int | None = None
    row_id: int | None = None
    weight: float | None = None
    source_policy: str | None = None
    split: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "window_id": self.window_id,
            "request_id": self.request_id,
            "tile_id": self.tile_id,
            "expert_id": self.expert_id,
            "transition_score": self.transition_score,
            "mtp_score": self.mtp_score,
            "utility_score": self.utility_score,
        }
        if self.sample_idx is not None:
            payload["sample_idx"] = int(self.sample_idx)
        if self.token_index is not None:
            payload["token_index"] = int(self.token_index)
        if self.layer_idx is not None:
            payload["layer_idx"] = int(self.layer_idx)
        if self.row_id is not None:
            payload["row_id"] = int(self.row_id)
        if self.weight is not None:
            payload["weight"] = float(self.weight)
        if self.source_policy is not None:
            payload["source_policy"] = self.source_policy
        if self.split is not None:
            payload["split"] = self.split
        return payload


@dataclass(frozen=True)
class LayerTilePrior:
    """A calibrated per-layer B-tile group order.

    This is intentionally weaker than an exact permutation cache.  Runtime
    still uses the current true-router descriptor multiset; the prior only
    ranks the present B-tile groups for visitation.
    """

    layer_orders: dict[int, list[int]]
    score_name: str
    group_scores: dict[int, dict[int, float]]
    metadata: dict[str, Any]

    def order_for_layer(self, layer_idx: int | None) -> list[int]:
        key = int(layer_idx) if layer_idx is not None else -1
        return self.layer_orders.get(key, self.layer_orders.get(-1, []))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "score_name": self.score_name,
            "layer_orders": {
                str(layer): [int(tile_id) for tile_id in order]
                for layer, order in sorted(self.layer_orders.items())
            },
            "group_scores": {
                str(layer): {
                    str(tile_id): float(score)
                    for tile_id, score in sorted(scores.items())
                }
                for layer, scores in sorted(self.group_scores.items())
            },
            "metadata": self.metadata,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "LayerTilePrior":
        raw_orders = payload.get("layer_orders")
        if not isinstance(raw_orders, Mapping):
            raise ValueError("layer prior JSON must contain 'layer_orders'")
        layer_orders = {
            int(layer): [int(tile_id) for tile_id in order]
            for layer, order in raw_orders.items()
        }
        raw_scores = payload.get("group_scores", {})
        if not isinstance(raw_scores, Mapping):
            raw_scores = {}
        group_scores = {
            int(layer): {
                int(tile_id): float(score)
                for tile_id, score in scores.items()
            }
            for layer, scores in raw_scores.items()
            if isinstance(scores, Mapping)
        }
        metadata = payload.get("metadata", {})
        return cls(
            layer_orders=layer_orders,
            score_name=str(payload.get("score_name", metadata.get("score_name", "unknown"))),
            group_scores=group_scores,
            metadata=dict(metadata) if isinstance(metadata, Mapping) else {},
        )


def load_layer_tile_prior(path: str | Path) -> LayerTilePrior:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("layer prior artifact must be a JSON object")
    return LayerTilePrior.from_mapping(payload)


def write_layer_tile_prior(prior: LayerTilePrior, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(prior.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        sample_idx=(
            int(record["sample_idx"]) if record.get("sample_idx") is not None else None
        ),
        token_index=(
            int(record["token_index"]) if record.get("token_index") is not None else None
        ),
        layer_idx=int(record["layer_idx"]) if record.get("layer_idx") is not None else None,
        row_id=int(record["row_id"]) if record.get("row_id") is not None else None,
        weight=float(record["weight"]) if record.get("weight") is not None else None,
        source_policy=(
            str(record["source_policy"]) if record.get("source_policy") is not None else None
        ),
        split=str(record["split"]) if record.get("split") is not None else None,
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


def load_tile_requests_jsonl(path: str | Path) -> list[TileRequest]:
    """Load one token/row-level tile request per JSONL line."""

    requests: list[TileRequest] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, Mapping):
                raise TypeError(f"JSONL line {index + 1} is not an object")
            requests.append(tile_request_from_mapping(record, fallback_request_id=index))
    return requests


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


def _request_layer_idx(item: TileRequest) -> int:
    return int(item.layer_idx) if item.layer_idx is not None else -1


def _layer_prior_score(item: TileRequest, score_name: str) -> float:
    if score_name == "frequency":
        return 1.0
    if score_name == "utility":
        return float(item.utility_score)
    if score_name == "transition":
        return float(item.transition_score)
    if score_name == "mtp":
        return float(item.mtp_score)
    if score_name == "weighted_utility":
        weight = 1.0 if item.weight is None else float(item.weight)
        return float(item.utility_score) * weight
    if score_name == "weighted_frequency":
        return 1.0 if item.weight is None else float(item.weight)
    raise ValueError(f"unknown layer prior score: {score_name}")


def build_layer_tile_prior(
    requests: Sequence[TileRequest],
    *,
    score_name: str,
    metadata: Mapping[str, Any] | None = None,
) -> LayerTilePrior:
    """Calibrate a per-layer tile-group order from a request stream.

    The artifact is a compact group-order prior.  It is not tied to a future
    exact descriptor multiset and can therefore be applied to held-out windows.
    """

    layer_scores: dict[int, dict[int, float]] = {}
    layer_counts: dict[int, dict[int, int]] = {}
    for item in requests:
        layer = _request_layer_idx(item)
        tile = int(item.tile_id)
        scores = layer_scores.setdefault(layer, {})
        counts = layer_counts.setdefault(layer, {})
        scores[tile] = scores.get(tile, 0.0) + _layer_prior_score(item, score_name)
        counts[tile] = counts.get(tile, 0) + 1

    layer_orders: dict[int, list[int]] = {}
    for layer, scores in layer_scores.items():
        counts = layer_counts[layer]
        layer_orders[layer] = sorted(
            scores,
            key=lambda tile: (-scores[tile], -counts[tile], tile),
        )

    prior_metadata = dict(metadata or {})
    prior_metadata.update(
        {
            "score_name": score_name,
            "request_count": int(len(requests)),
            "layer_count": int(len(layer_orders)),
            "tile_count": int(len({item.tile_id for item in requests})),
        }
    )
    return LayerTilePrior(
        layer_orders=layer_orders,
        score_name=score_name,
        group_scores=layer_scores,
        metadata=prior_metadata,
    )


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
    if policy == "transition_tile_grouped":
        return _order_tile_groups_by_score(requests, lambda item: item.transition_score)
    if policy == "mtp_transition_tile_grouped":
        return _order_tile_groups_by_score(
            requests,
            lambda item: item.transition_score + item.mtp_score,
        )
    if policy == "utility_tile_grouped":
        return _order_tile_groups_by_score(requests, lambda item: item.utility_score)
    if policy == "utility_tile_grouped_bucket":
        return _order_tile_groups_by_score_bucketed(
            requests,
            lambda item: item.utility_score,
        )
    if policy == "utility_tile_grouped_top16":
        return _order_tile_groups_by_score_bucketed(
            requests,
            lambda item: item.utility_score,
            top_groups=16,
        )
    if policy == "utility_tile_grouped_top32":
        return _order_tile_groups_by_score_bucketed(
            requests,
            lambda item: item.utility_score,
            top_groups=32,
        )
    if policy == "oracle_cache_aware":
        counts = Counter(item.tile_id for item in requests)
        return sorted(
            requests,
            key=lambda item: (-counts[item.tile_id], item.tile_id, item.expert_id, item.request_id),
        )
    raise ValueError(f"unknown tile-order policy: {policy}")


def order_window_with_layer_prior(
    requests: Sequence[TileRequest],
    *,
    prior: LayerTilePrior | Mapping[int, Sequence[int]],
    top_utility_override: int = 0,
) -> list[TileRequest]:
    """Order one window by calibrated layer-prior tile groups.

    The current request multiset is preserved exactly.  If ``top_utility_override``
    is positive, the current window's hottest tile groups are emitted first and
    the remaining groups follow the layer prior.
    """

    if not requests:
        return []
    layer = next((_request_layer_idx(item) for item in requests if item.layer_idx is not None), -1)
    if isinstance(prior, LayerTilePrior):
        prior_order = prior.order_for_layer(layer)
    else:
        prior_order = [int(tile) for tile in prior.get(layer, prior.get(-1, []))]

    max_tile_id = max(int(item.tile_id) for item in requests)
    if prior_order:
        max_tile_id = max(max_tile_id, max(int(tile) for tile in prior_order))
    if 0 <= max_tile_id <= 1_000_000:
        return _order_window_with_layer_prior_bucketed(
            requests,
            prior_order=prior_order,
            top_utility_override=top_utility_override,
            max_tile_id=max_tile_id,
        )

    groups: dict[int, list[TileRequest]] = {}
    max_scores: dict[int, float] = {}
    total_scores: dict[int, float] = {}
    counts: dict[int, int] = {}
    for item in requests:
        tile = int(item.tile_id)
        groups.setdefault(tile, []).append(item)
        score = float(item.utility_score)
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

    for tile in prior_order:
        tile_id = int(tile)
        if tile_id in active_tiles and tile_id not in selected:
            ordered_tiles.append(tile_id)
            selected.add(tile_id)

    for tile_id in sorted(active_tiles - selected):
        ordered_tiles.append(tile_id)

    ordered: list[TileRequest] = []
    for tile_id in ordered_tiles:
        ordered.extend(groups[tile_id])
    return ordered


def _order_window_with_layer_prior_bucketed(
    requests: Sequence[TileRequest],
    *,
    prior_order: Sequence[int],
    top_utility_override: int,
    max_tile_id: int,
) -> list[TileRequest]:
    groups: list[list[TileRequest] | None] = [None] * (max_tile_id + 1)
    max_scores = [float("-inf")] * (max_tile_id + 1)
    total_scores = [0.0] * (max_tile_id + 1)
    counts = [0] * (max_tile_id + 1)
    present = [False] * (max_tile_id + 1)
    active_tile_ids: list[int] = []

    for item in requests:
        tile = int(item.tile_id)
        group = groups[tile]
        if group is None:
            group = []
            groups[tile] = group
            present[tile] = True
            active_tile_ids.append(tile)
        group.append(item)
        score = float(item.utility_score)
        if score > max_scores[tile]:
            max_scores[tile] = score
        total_scores[tile] += score
        counts[tile] += 1

    ordered_tiles: list[int] = []
    selected = [False] * (max_tile_id + 1)
    if top_utility_override > 0:
        ranked = sorted(
            active_tile_ids,
            key=lambda tile: (-max_scores[tile], -total_scores[tile], -counts[tile], tile),
        )
        for tile in ranked[: int(top_utility_override)]:
            ordered_tiles.append(tile)
            selected[tile] = True

    for tile in prior_order:
        tile_id = int(tile)
        if 0 <= tile_id <= max_tile_id and present[tile_id] and not selected[tile_id]:
            ordered_tiles.append(tile_id)
            selected[tile_id] = True

    for tile_id in sorted(active_tile_ids):
        if not selected[tile_id]:
            ordered_tiles.append(tile_id)

    ordered: list[TileRequest] = []
    for tile_id in ordered_tiles:
        group = groups[tile_id]
        if group is not None:
            ordered.extend(group)
    return ordered


def _order_tile_groups_by_score(
    requests: Sequence[TileRequest],
    score_fn: Callable[[TileRequest], float],
) -> list[TileRequest]:
    groups: dict[int, list[TileRequest]] = {}
    for item in requests:
        groups.setdefault(item.tile_id, []).append(item)
    group_items = []
    for tile_id, items in groups.items():
        max_score = max(score_fn(item) for item in items)
        total_score = sum(score_fn(item) for item in items)
        group_items.append((tile_id, max_score, total_score, len(items), items))
    ordered_groups = sorted(
        group_items,
        key=lambda row: (-row[1], -row[2], -row[3], row[0]),
    )
    ordered: list[TileRequest] = []
    for _, _, _, _, items in ordered_groups:
        ordered.extend(sorted(items, key=lambda item: (item.expert_id, item.request_id)))
    return ordered


def _order_tile_groups_by_score_bucketed(
    requests: Sequence[TileRequest],
    score_fn: Callable[[TileRequest], float],
    *,
    top_groups: int | None = None,
) -> list[TileRequest]:
    """Bucket by tile id, then rank only the small active group set.

    This keeps the runtime shape closer to a descriptor builder: O(N) bucket
    fill plus O(G log G) tile-group ranking, where G is the active B-tile count.
    Group members retain original row order.
    """

    if not requests:
        return []
    max_tile_id = max(int(item.tile_id) for item in requests)
    if max_tile_id < 0 or max_tile_id > 1_000_000:
        return _order_tile_groups_by_score(requests, score_fn)

    groups: list[list[TileRequest] | None] = [None] * (max_tile_id + 1)
    max_scores = [float("-inf")] * (max_tile_id + 1)
    total_scores = [0.0] * (max_tile_id + 1)
    counts = [0] * (max_tile_id + 1)
    active_tile_ids: list[int] = []

    for item in requests:
        tile_id = int(item.tile_id)
        group = groups[tile_id]
        if group is None:
            group = []
            groups[tile_id] = group
            active_tile_ids.append(tile_id)
        group.append(item)
        score = float(score_fn(item))
        if score > max_scores[tile_id]:
            max_scores[tile_id] = score
        total_scores[tile_id] += score
        counts[tile_id] += 1

    ranked = sorted(
        active_tile_ids,
        key=lambda tile_id: (
            -max_scores[tile_id],
            -total_scores[tile_id],
            -counts[tile_id],
            tile_id,
        ),
    )
    if top_groups is not None:
        top_n = max(0, int(top_groups))
        selected = set(ranked[:top_n])
        ranked = ranked[:top_n] + sorted(
            (tile_id for tile_id in active_tile_ids if tile_id not in selected)
        )

    ordered: list[TileRequest] = []
    for tile_id in ranked:
        group = groups[tile_id]
        if group is not None:
            ordered.extend(group)
    return ordered


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


def order_tile_requests_with_layer_prior(
    requests: Sequence[TileRequest],
    *,
    prior: LayerTilePrior | Mapping[int, Sequence[int]],
    top_utility_override: int = 0,
) -> list[TileRequest]:
    ordered: list[TileRequest] = []
    for window in group_by_window(requests):
        ordered.extend(
            order_window_with_layer_prior(
                window,
                prior=prior,
                top_utility_override=top_utility_override,
            )
        )
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
    ordered = order_tile_requests(requests, policy=policy, seed=seed)
    return evaluate_ordered_tile_requests(
        requests,
        ordered,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=tile_order_top_k,
    )


def evaluate_ordered_tile_requests(
    requests: Sequence[TileRequest],
    ordered: Sequence[TileRequest],
    *,
    policy: str,
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
) -> dict[str, Any]:
    original_windows = group_by_window(requests)
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
