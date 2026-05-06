#!/usr/bin/env python3
"""Apply runtime descriptor-order policies to premap descriptor JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    load_descriptor_jsonl,
    order_prefetch_descriptors,
)


DEFAULT_POLICIES = [
    "linear",
    "b_tile_grouped",
    "transition_tile_grouped",
    "mtp_transition_tile_grouped",
    "utility_tile_grouped",
    "oracle_cache_aware",
]


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("descriptors", type=Path)
    parser.add_argument("--policy", action="append", choices=DEFAULT_POLICIES, default=None)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32])
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--tile-order-top-k", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/descriptor_order_smoke.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/descriptor_order_smoke.md"),
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
        "# Descriptor-Order Simulation",
        "",
        "This report reorders an existing descriptor multiset only. It does not",
        "change router outputs, candidate membership, or expert execution.",
        "",
        f"- Descriptors: `{report['descriptor_count']}`",
        f"- Source: `{report['descriptor_path']}`",
        "",
        "| policy | build_us | LRU@8 | LRU@16 | reuse_mean | order_hit | multiset_hash | order_hash |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report["policies"]:
        metrics = row["metrics"]
        lru = metrics["lru_hit_rate"]
        lines.append(
            "| "
            + " | ".join(
                [
                    fmt(row["policy"]),
                    fmt(row["order_build_us"]),
                    fmt(lru.get("8")),
                    fmt(lru.get("16")),
                    fmt(metrics["reuse_distance"]["mean"]),
                    fmt(metrics["tile_order_hit_rate"]),
                    row["tile_multiset_hash"][:12],
                    row["order_hash"][:12],
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    descriptors = load_descriptor_jsonl(args.descriptors)
    rows = []
    ordered_preview = {}
    for policy in args.policy or DEFAULT_POLICIES:
        ordered, descriptor_report = order_prefetch_descriptors(
            descriptors,
            policy=policy,
            tiles_per_expert=args.tiles_per_expert,
            cache_sizes=args.cache_sizes,
            tile_order_top_k=args.tile_order_top_k,
            seed=args.seed,
        )
        rows.append(descriptor_report.as_dict())
        ordered_preview[policy] = [item.as_dict() for item in ordered[:16]]
    report = {
        "ok": True,
        "descriptor_path": str(args.descriptors),
        "descriptor_count": len(descriptors),
        "policies": rows,
        "ordered_preview": ordered_preview,
        "config": {
            "cache_sizes": args.cache_sizes,
            "tiles_per_expert": args.tiles_per_expert,
            "tile_order_top_k": args.tile_order_top_k,
            "seed": args.seed,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))


if __name__ == "__main__":
    main()

