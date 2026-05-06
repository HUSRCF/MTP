#!/usr/bin/env python3
"""Evaluate cache-aware B-tile visitation orders before GPU kernel work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime.tile_order import (  # noqa: E402
    evaluate_tile_order_policies,
    generate_synthetic_tile_requests,
    load_tile_requests_json,
    load_tile_requests_jsonl,
)
from mtp_expert_prefetch.runtime.tile_stream import tile_requests_from_tensor_cache  # noqa: E402


DEFAULT_POLICIES = [
    "linear",
    "random",
    "expert_major",
    "b_tile_grouped",
    "transition_hot_first",
    "mtp_transition_hot_first",
    "utility_hot_first",
    "transition_tile_grouped",
    "mtp_transition_tile_grouped",
    "utility_tile_grouped",
    "utility_tile_grouped_bucket",
    "utility_tile_grouped_top16",
    "utility_tile_grouped_top32",
    "oracle_cache_aware",
]


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input-json", type=Path, default=None)
    source.add_argument("--input-jsonl", type=Path, default=None)
    source.add_argument("--tensor-cache", type=Path, default=None)
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--policy", action="append", choices=DEFAULT_POLICIES, default=None)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32, 64])
    parser.add_argument("--tile-order-top-k", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)

    parser.add_argument("--num-windows", type=int, default=64)
    parser.add_argument("--requests-per-window", type=int, default=128)
    parser.add_argument("--num-experts", type=int, default=256)
    parser.add_argument("--tiles-per-expert", type=int, default=4)
    parser.add_argument("--hot-experts", type=int, default=32)
    parser.add_argument("--novelty-experts", type=int, default=16)
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tensor-max-examples", type=int, default=None)
    parser.add_argument("--tensor-start-example", type=int, default=0)
    parser.add_argument("--split-name", default=None)

    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_order_cache_smoke.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_order_cache_smoke.md"),
    )
    return parser.parse_args()


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tile-Order Cache Simulation",
        "",
        "This is a trace-level scheduler/locality diagnostic. It does not claim",
        "kernel speedup; it filters which tile-order policies deserve HIP/rocWMMA",
        "measurement.",
        "",
        "## Summary",
        "",
        f"- Requests: `{report['request_count']}`",
        f"- Windows: `{report['window_count']}`",
        f"- Best reuse-distance policy: `{report['best_reuse_distance_policy']}`",
        f"- Best by cache size: `{report['best_by_cache_size']}`",
        "",
        "## Policies",
        "",
    ]
    cache_keys = sorted(
        report["policies"][0]["lru_hit_rate"],
        key=lambda item: int(item),
    )
    columns = [
        "policy",
        "reuse_mean",
        "reuse_p95",
        "unique/window",
        "run_mean",
        "order_hit",
        *[f"lru@{key}" for key in cache_keys],
    ]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    for row in report["policies"]:
        values = [
            row["policy"],
            row["reuse_distance"]["mean"],
            row["reuse_distance"]["p95"],
            row["unique_tiles_per_window"]["mean"],
            row["consecutive_same_tile_run"]["mean"],
            row["tile_order_hit_rate"],
            *[row["lru_hit_rate"][key] for key in cache_keys],
        ]
        lines.append("| " + " | ".join(fmt(value) for value in values) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if args.input_json is not None:
        payload = json.loads(args.input_json.read_text(encoding="utf-8"))
        requests = load_tile_requests_json(payload)
        source = {"type": "input_json", "path": str(args.input_json)}
    elif args.input_jsonl is not None:
        requests = load_tile_requests_jsonl(args.input_jsonl)
        source = {"type": "input_jsonl", "path": str(args.input_jsonl)}
    elif args.tensor_cache is not None:
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
    else:
        requests = generate_synthetic_tile_requests(
            num_windows=args.num_windows,
            requests_per_window=args.requests_per_window,
            num_experts=args.num_experts,
            tiles_per_expert=args.tiles_per_expert,
            hot_experts=args.hot_experts,
            novelty_experts=args.novelty_experts,
            seed=args.seed,
        )
        source = {
            "type": "synthetic",
            "num_windows": args.num_windows,
            "requests_per_window": args.requests_per_window,
            "num_experts": args.num_experts,
            "tiles_per_expert": args.tiles_per_expert,
            "hot_experts": args.hot_experts,
            "novelty_experts": args.novelty_experts,
            "seed": args.seed,
        }

    report = evaluate_tile_order_policies(
        requests,
        policies=args.policy or DEFAULT_POLICIES,
        cache_sizes=args.cache_sizes,
        tile_order_top_k=args.tile_order_top_k,
        seed=args.seed,
    )
    report["ok"] = True
    report["source"] = source
    report["cache_sizes"] = args.cache_sizes
    report["tile_order_top_k"] = args.tile_order_top_k
    report["schema_version"] = 1

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))


if __name__ == "__main__":
    main()
