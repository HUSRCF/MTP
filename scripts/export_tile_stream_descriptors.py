#!/usr/bin/env python3
"""Export token/row-level B-tile descriptor streams from a tensor cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime.tile_order import evaluate_tile_order_policies  # noqa: E402
from mtp_expert_prefetch.runtime.tile_stream import tile_requests_from_tensor_cache  # noqa: E402


DEFAULT_POLICIES = [
    "linear",
    "b_tile_grouped",
    "utility_hot_first",
    "utility_tile_grouped",
]


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tensor_cache", type=Path)
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--tensor-max-examples", type=int, default=None)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32])
    parser.add_argument("--tile-order-top-k", type=int, default=8)
    parser.add_argument("--policy", action="append", choices=DEFAULT_POLICIES, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_stream_descriptors.jsonl"),
    )
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--summary-md", type=Path, default=None)
    return parser.parse_args()


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Token/Row Tile Stream Export",
        "",
        "This artifact is a token/row-level descriptor stream for tile-order",
        "simulation and timing benches. It preserves true-router demand rows and",
        "does not claim kernel speedup by itself.",
        "",
        "## Summary",
        "",
        f"- Requests: `{report['request_count']}`",
        f"- Windows: `{report['window_count']}`",
        f"- Unique B tiles: `{report['unique_tiles_total']}`",
        f"- Output JSONL: `{report['output_jsonl']}`",
        "",
        "## Policy Diagnostics",
        "",
    ]
    policy_reports = report["diagnostics"]["policies"]
    if policy_reports:
        cache_keys = sorted(policy_reports[0]["lru_hit_rate"], key=lambda item: int(item))
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
        for row in policy_reports:
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
    import torch

    cache = torch.load(args.tensor_cache, map_location="cpu")
    requests, source = tile_requests_from_tensor_cache(
        cache,
        window_size=args.tensor_window_size,
        topk=args.tensor_topk,
        tiles_per_expert=args.tiles_per_expert,
        max_examples=args.tensor_max_examples,
    )
    source["type"] = "tensor_cache"
    source["path"] = str(args.tensor_cache)
    source["max_examples"] = args.tensor_max_examples

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as handle:
        for request in requests:
            handle.write(json.dumps(request.as_dict(), sort_keys=True) + "\n")

    diagnostics = evaluate_tile_order_policies(
        requests,
        policies=args.policy or DEFAULT_POLICIES,
        cache_sizes=args.cache_sizes,
        tile_order_top_k=args.tile_order_top_k,
        seed=args.seed,
    )
    tile_ids = [request.tile_id for request in requests]
    report = {
        "ok": True,
        "schema_version": 1,
        "source": source,
        "output_jsonl": str(args.output_jsonl),
        "request_count": len(requests),
        "window_count": diagnostics["window_count"],
        "unique_tiles_total": len(set(tile_ids)),
        "first_records": [request.as_dict() for request in requests[:5]],
        "config": {
            "cache_sizes": args.cache_sizes,
            "tile_order_top_k": args.tile_order_top_k,
            "policies": args.policy or DEFAULT_POLICIES,
            "seed": args.seed,
        },
        "diagnostics": diagnostics,
    }

    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.summary_md is not None:
        args.summary_md.parent.mkdir(parents=True, exist_ok=True)
        args.summary_md.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))


if __name__ == "__main__":
    main()
