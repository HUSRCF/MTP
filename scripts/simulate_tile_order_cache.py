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
    TileRequest,
    evaluate_tile_order_policies,
    generate_synthetic_tile_requests,
    load_tile_requests_json,
)


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
    "oracle_cache_aware",
]


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input-json", type=Path, default=None)
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


def load_tensor_cache_requests(
    path: Path,
    *,
    window_size: int,
    topk: int,
    tiles_per_expert: int,
    max_examples: int | None,
) -> tuple[list[TileRequest], dict[str, Any]]:
    import torch

    cache = torch.load(path, map_location="cpu")
    target_mass = cache["target_mass"].float()
    transition_scores = cache["transition_scores"].float()
    mtp_scores = cache["mtp_scores"].float()
    if target_mass.ndim != 4:
        raise ValueError(f"expected target_mass [N,D,L,E], got shape {tuple(target_mass.shape)}")
    num_examples, depth, num_layers, num_experts = target_mass.shape
    if depth != 1:
        target_mass = target_mass[:, :1]
        transition_scores = transition_scores[:, :1]
        mtp_scores = mtp_scores[:, :1]
    if max_examples is not None:
        num_examples = min(num_examples, int(max_examples))
        target_mass = target_mass[:num_examples]
        transition_scores = transition_scores[:num_examples]
        mtp_scores = mtp_scores[:num_examples]

    requests: list[TileRequest] = []
    request_id = 0
    windows_per_layer = (num_examples + window_size - 1) // window_size
    for layer in range(num_layers):
        for example_idx in range(num_examples):
            window_id = layer * windows_per_layer + example_idx // window_size
            mass = target_mass[example_idx, 0, layer]
            values, experts = torch.topk(mass, k=min(topk, num_experts))
            for value, expert_tensor in zip(values.tolist(), experts.tolist(), strict=True):
                if value <= 0:
                    continue
                expert = int(expert_tensor)
                for tile_local in range(tiles_per_expert):
                    tile_id = expert * tiles_per_expert + tile_local
                    transition_score = float(transition_scores[example_idx, 0, layer, expert])
                    mtp_score = float(mtp_scores[example_idx, 0, layer, expert])
                    utility_score = 0.75 * transition_score + 0.55 * mtp_score
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
    return requests, {
        "type": "tensor_cache",
        "path": str(path),
        "num_examples": num_examples,
        "num_layers": num_layers,
        "num_experts": num_experts,
        "window_size": window_size,
        "topk": topk,
        "tiles_per_expert": tiles_per_expert,
        "max_examples": max_examples,
        "schema_version": cache.get("schema_version"),
        "eval_split": cache.get("eval_split"),
    }


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
    elif args.tensor_cache is not None:
        requests, source = load_tensor_cache_requests(
            args.tensor_cache,
            window_size=args.tensor_window_size,
            topk=args.tensor_topk,
            tiles_per_expert=args.tiles_per_expert,
            max_examples=args.tensor_max_examples,
        )
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
