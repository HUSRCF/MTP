#!/usr/bin/env python3
"""Replay descriptor-order permutation-cache reuse on token/row tile streams."""

from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
import hashlib
import json
from pathlib import Path
import sys
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    group_by_window,
    load_tile_requests_jsonl,
    tile_requests_from_tensor_cache,
)


DEFAULT_POLICIES = [
    "utility_tile_grouped_bucket",
    "utility_tile_grouped_top16",
    "utility_tile_grouped_top32",
]
KEY_MODES = ["exact_multiset", "tile_set", "layer_only", "global"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-jsonl", type=Path, default=None)
    source.add_argument("--tensor-cache", type=Path, default=None)
    parser.add_argument("--policy", action="append", choices=DEFAULT_POLICIES, default=None)
    parser.add_argument("--key-mode", action="append", choices=KEY_MODES, default=None)
    parser.add_argument("--builder-json", type=Path, default=None)
    parser.add_argument("--cache-capacity", type=int, action="append", default=None)
    parser.add_argument("--lookup-us", type=float, default=0.1)
    parser.add_argument("--apply-us", type=float, default=0.0)
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--tensor-max-examples", type=int, default=None)
    parser.add_argument("--tensor-start-example", type=int, default=0)
    parser.add_argument("--split-name", default=None)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/descriptor_order_cache_replay.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/descriptor_order_cache_replay.md"),
    )
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def stats(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p90": None, "p99": None, "max": None}
    return {
        "count": len(values),
        "mean": float(mean(values)),
        "p50": percentile([float(value) for value in values], 0.50),
        "p90": percentile([float(value) for value in values], 0.90),
        "p99": percentile([float(value) for value in values], 0.99),
        "max": max(values),
    }


def load_requests(args: argparse.Namespace) -> tuple[list[Any], dict[str, Any]]:
    if args.input_jsonl is not None:
        return load_tile_requests_jsonl(args.input_jsonl), {
            "type": "input_jsonl",
            "path": str(args.input_jsonl),
        }
    import torch

    cache = torch.load(args.tensor_cache, map_location="cpu")
    requests, source = tile_requests_from_tensor_cache(
        cache,
        window_size=args.tensor_window_size,
        topk=args.tensor_topk,
        tiles_per_expert=args.tiles_per_expert,
        max_examples=args.tensor_max_examples,
        start_example=args.tensor_start_example,
        split_name=args.split_name,
    )
    source["type"] = "tensor_cache"
    source["path"] = str(args.tensor_cache)
    source["max_examples"] = args.tensor_max_examples
    source["start_example"] = args.tensor_start_example
    source["split_name"] = args.split_name
    return requests, source


def multiset_hash(tile_ids: list[int]) -> str:
    payload = ",".join(str(tile_id) for tile_id in sorted(tile_ids)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def tile_set_hash(tile_ids: list[int]) -> str:
    payload = ",".join(str(tile_id) for tile_id in sorted(set(tile_ids))).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def layer_id_for_window(window: list[Any]) -> int:
    layers = {request.layer_idx for request in window if request.layer_idx is not None}
    if len(layers) == 1:
        return int(next(iter(layers)))
    return int(window[0].window_id)


def policy_config_hash(policy: str) -> str:
    return hashlib.sha256(f"descriptor_order:{policy}:v1".encode("ascii")).hexdigest()[:16]


def load_builder_costs(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    costs = {}
    for row in payload.get("policies", []):
        policy = str(row["policy"])
        if "cpp_build_us_per_window_median" in row:
            costs[policy] = float(row["cpp_build_us_per_window_median"])
        elif "order_build_us" in row and isinstance(row["order_build_us"], dict):
            costs[policy] = float(row["order_build_us"]["median"])
    return costs


def _safe_cache_value(key_mode: str) -> str:
    if key_mode == "exact_multiset":
        return "full_permutation_or_group_order"
    if key_mode == "tile_set":
        return "group_order_only"
    if key_mode == "layer_only":
        return "heuristic_group_order_only"
    if key_mode == "global":
        return "heuristic_global_order_only"
    return "unknown"


def replay_unbounded(keys: list[str]) -> dict[str, Any]:
    counts = Counter(keys)
    seen: set[str] = set()
    hits = 0
    for key in keys:
        if key in seen:
            hits += 1
        else:
            seen.add(key)
    reuse_counts = list(counts.values())
    return {
        "window_count": len(keys),
        "unique_keys": len(counts),
        "hit_count": hits,
        "miss_count": len(counts),
        "hit_rate": hits / len(keys) if keys else 0.0,
        "reuse_count": stats(reuse_counts),
        "keys_reused_at_least_2": sum(1 for value in reuse_counts if value >= 2),
        "keys_reused_at_least_8": sum(1 for value in reuse_counts if value >= 8),
        "keys_reused_at_least_32": sum(1 for value in reuse_counts if value >= 32),
        "keys_reused_at_least_73": sum(1 for value in reuse_counts if value >= 73),
    }


def replay_lru(keys: list[str], *, capacity: int) -> dict[str, Any]:
    cache: OrderedDict[str, None] = OrderedDict()
    hits = 0
    misses = 0
    for key in keys:
        if key in cache:
            hits += 1
            cache.move_to_end(key)
        else:
            misses += 1
            cache[key] = None
            if len(cache) > capacity:
                cache.popitem(last=False)
    return {
        "capacity": int(capacity),
        "hit_count": hits,
        "miss_count": misses,
        "hit_rate": hits / len(keys) if keys else 0.0,
    }


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Descriptor-Order Permutation Cache Replay",
        "",
        "This replay estimates whether descriptor-order permutations repeat often",
        "enough to amortize builder cost. It does not change execution order.",
        "",
        f"- Windows: `{report['window_count']}`",
        f"- Source: `{report['source']}`",
        "",
        "| policy | key_mode | exact_hit | unique_keys | reuse_p50 | reuse_p90 | reuse_max | build_us/window | amortized_us/window | expected_us/window | safe_value |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["policies"]:
        reuse = row["exact"]["reuse_count"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["policy"],
                    row["key_mode"],
                    fmt(row["exact"]["hit_rate"]),
                    fmt(row["exact"]["unique_keys"]),
                    fmt(reuse["p50"]),
                    fmt(reuse["p90"]),
                    fmt(reuse["max"]),
                    fmt(row["builder_us_per_window"]),
                    fmt(row["amortized_build_us_per_window"]),
                    fmt(row["expected_cache_cost_us_per_window"]),
                    row["safe_cache_value"],
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    requests, source = load_requests(args)
    windows = group_by_window(requests)
    window_key_parts = []
    for window in windows:
        tile_ids = [int(request.tile_id) for request in window]
        layer = layer_id_for_window(window)
        window_key_parts.append(
            {
                "layer": layer,
                "exact_multiset": f"layer={layer}:multiset={multiset_hash(tile_ids)}",
                "tile_set": f"layer={layer}:tile_set={tile_set_hash(tile_ids)}",
                "layer_only": f"layer={layer}",
                "global": "global",
            }
        )

    builder_costs = load_builder_costs(args.builder_json)
    policies = args.policy or DEFAULT_POLICIES
    key_modes = args.key_mode or ["exact_multiset", "tile_set"]
    cache_capacities = args.cache_capacity or [16, 64, 256, 1024]
    rows = []
    for policy in policies:
        config_hash = policy_config_hash(policy)
        for key_mode in key_modes:
            keys = [
                f"{parts[key_mode]}:policy={config_hash}"
                for parts in window_key_parts
            ]
            exact = replay_unbounded(keys)
            lru = [replay_lru(keys, capacity=capacity) for capacity in cache_capacities]
            builder_us_per_window = builder_costs.get(policy)
            amortized = (
                builder_us_per_window * exact["miss_count"] / exact["window_count"]
                if builder_us_per_window is not None and exact["window_count"]
                else None
            )
            expected = (
                float(args.lookup_us)
                + float(args.apply_us)
                + (
                    builder_us_per_window * exact["miss_count"] / exact["window_count"]
                    if builder_us_per_window is not None and exact["window_count"]
                    else 0.0
                )
            )
            rows.append(
                {
                    "policy": policy,
                    "key_mode": key_mode,
                    "policy_config_hash": config_hash,
                    "exact": exact,
                    "lru": lru,
                    "builder_us_per_window": builder_us_per_window,
                    "lookup_us": args.lookup_us,
                    "apply_us": args.apply_us,
                    "amortized_build_us_per_window": amortized,
                    "expected_cache_cost_us_per_window": expected,
                    "safe_cache_value": _safe_cache_value(key_mode),
                }
            )

    report = {
        "ok": True,
        "schema_version": 1,
        "source": source,
        "window_count": len(windows),
        "request_count": len(requests),
        "builder_json": str(args.builder_json) if args.builder_json is not None else None,
        "cache_capacities": cache_capacities,
        "key_modes": key_modes,
        "policies": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))


if __name__ == "__main__":
    main()
