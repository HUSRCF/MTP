#!/usr/bin/env python3
"""Combine descriptor-order build cost with tile-order timing results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--order-json", type=Path, required=True)
    parser.add_argument("--timing-json", type=Path, required=True)
    parser.add_argument("--baseline-policy", default="linear")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_order_overhead_pareto.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_order_overhead_pareto.md"),
    )
    return parser.parse_args()


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def config_key(row: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(row["device"]),
        int(row["tile_elems"]),
        int(row["tiles_per_cta"]),
        int(row["cache_flush_elems"]),
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tile-Order Overhead Pareto",
        "",
        "This report subtracts descriptor-order build cost from measured kernel",
        "timing savings. It is a conservative accounting bridge; it does not",
        "change the descriptor multiset or router outputs.",
        "",
        f"- Baseline policy: `{report['baseline_policy']}`",
        f"- Order report: `{report['order_json']}`",
        f"- Timing report: `{report['timing_json']}`",
        "",
        "| device | tile_elems | flush | policy | build_us | kernel_saved_us | net_saved_us | raw_speedup | net_speedup | LRU@8 | order_hit |",
        "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    fmt(row["device"]),
                    fmt(row["tile_elems"]),
                    fmt(row["cache_flush_elems"]),
                    row["policy"],
                    fmt(row["order_build_us_median"]),
                    fmt(row["kernel_saved_us"]),
                    fmt(row["net_saved_us"]),
                    fmt(row["raw_speedup_vs_baseline"]),
                    fmt(row["net_speedup_vs_baseline"]),
                    fmt(row["lru_at_8"]),
                    fmt(row["tile_order_hit_rate"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    order_report = json.loads(args.order_json.read_text(encoding="utf-8"))
    timing_report = json.loads(args.timing_json.read_text(encoding="utf-8"))

    build_by_policy = {
        row["policy"]: float(row["order_build_us"]["median"])
        for row in order_report["policies"]
    }
    timing_rows = timing_report.get("summary", {}).get("stability", [])
    baselines: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    for row in timing_rows:
        if row["policy"] == args.baseline_policy:
            baselines[config_key(row)] = row

    rows = []
    for row in timing_rows:
        key = config_key(row)
        baseline = baselines.get(key)
        if baseline is None:
            continue
        policy = row["policy"]
        order_build_us = build_by_policy.get(policy)
        if order_build_us is None:
            continue
        if policy == args.baseline_policy:
            order_build_us = 0.0
        baseline_wall_us = float(baseline["wall_ms"]["median"]) * 1000.0
        policy_wall_us = float(row["wall_ms"]["median"]) * 1000.0
        kernel_saved_us = baseline_wall_us - policy_wall_us
        net_saved_us = kernel_saved_us - float(order_build_us)
        raw_speedup = (
            baseline_wall_us / policy_wall_us if policy_wall_us > 0 else None
        )
        net_time_us = policy_wall_us + float(order_build_us)
        net_speedup = baseline_wall_us / net_time_us if net_time_us > 0 else None
        lru = row.get("lru_hit_rate", {})
        rows.append(
            {
                "device": key[0],
                "tile_elems": key[1],
                "tiles_per_cta": key[2],
                "cache_flush_elems": key[3],
                "policy": policy,
                "order_build_us_median": float(order_build_us),
                "baseline_wall_us": baseline_wall_us,
                "policy_wall_us": policy_wall_us,
                "kernel_saved_us": kernel_saved_us,
                "net_saved_us": net_saved_us,
                "raw_speedup_vs_baseline": raw_speedup,
                "net_speedup_vs_baseline": net_speedup,
                "lru_at_8": lru.get("8"),
                "tile_order_hit_rate": row.get("tile_order_hit_rate"),
                "order_hash": row.get("order_hash"),
                "tile_multiset_hash": row.get("tile_multiset_hash"),
            }
        )

    report = {
        "ok": bool(rows),
        "schema_version": 1,
        "baseline_policy": args.baseline_policy,
        "order_json": str(args.order_json),
        "timing_json": str(args.timing_json),
        "rows": rows,
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
