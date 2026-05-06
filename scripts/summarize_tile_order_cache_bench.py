#!/usr/bin/env python3
"""Summarize tile-order timing stability reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-md", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    stability = list(report.get("summary", {}).get("stability", []))
    configs: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}
    for row in stability:
        key = (
            int(row["device"]),
            int(row["tile_elems"]),
            int(row["tiles_per_cta"]),
            int(row["cache_flush_elems"]),
        )
        configs.setdefault(key, []).append(row)

    config_summaries = []
    for key, rows in sorted(configs.items()):
        rows = sorted(rows, key=lambda row: float(row["us_per_tile"]["median"]))
        by_policy = {row["policy"]: row for row in rows}
        utility_grouped = by_policy.get("utility_tile_grouped")
        utility_hot = by_policy.get("utility_hot_first")
        b_grouped = by_policy.get("b_tile_grouped")
        linear = by_policy.get("linear")
        item = {
            "device": key[0],
            "tile_elems": key[1],
            "tiles_per_cta": key[2],
            "cache_flush_elems": key[3],
            "best_policy": rows[0]["policy"] if rows else None,
            "best_us_per_tile_median": rows[0]["us_per_tile"]["median"] if rows else None,
            "rows": rows,
        }
        if utility_grouped and linear:
            item["utility_tile_grouped_speedup_vs_linear"] = utility_grouped[
                "speedup_median_vs_linear"
            ]
        if utility_grouped and utility_hot:
            item["utility_tile_grouped_speedup_vs_utility_hot"] = (
                float(utility_hot["us_per_tile"]["median"])
                / float(utility_grouped["us_per_tile"]["median"])
            )
        if utility_grouped and b_grouped:
            item["utility_tile_grouped_speedup_vs_b_grouped"] = (
                float(b_grouped["us_per_tile"]["median"])
                / float(utility_grouped["us_per_tile"]["median"])
            )
            item["utility_tile_grouped_order_hit_gain_vs_b_grouped"] = (
                float(utility_grouped["tile_order_hit_rate"])
                - float(b_grouped["tile_order_hit_rate"])
            )
        config_summaries.append(item)

    return {
        "ok": bool(report.get("ok", False)),
        "source": report.get("source", {}),
        "config": report.get("config", {}),
        "config_count": len(config_summaries),
        "configs": config_summaries,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Tile-Order Timing Summary",
        "",
        "This is a no-LDS direct/global-fragment timing summary. Sorting cost is",
        "excluded; the HIP kernel consumes precomputed tile-id orders.",
        "",
        "## Configs",
        "",
        "| device | tile_elems | flush | best | best us/tile | util_group speedup vs linear | util_group vs hot | util_group vs B-grouped | order-hit gain vs B-grouped |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for item in summary["configs"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    fmt(item["device"]),
                    fmt(item["tile_elems"]),
                    fmt(item["cache_flush_elems"]),
                    fmt(item["best_policy"]),
                    fmt(item["best_us_per_tile_median"]),
                    fmt(item.get("utility_tile_grouped_speedup_vs_linear")),
                    fmt(item.get("utility_tile_grouped_speedup_vs_utility_hot")),
                    fmt(item.get("utility_tile_grouped_speedup_vs_b_grouped")),
                    fmt(item.get("utility_tile_grouped_order_hit_gain_vs_b_grouped")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Per-Policy Rows", ""])
    for item in summary["configs"]:
        lines.extend(
            [
                f"### device={item['device']} tile={item['tile_elems']} flush={item['cache_flush_elems']}",
                "",
                "| policy | median us/tile | p10 | p90 | CV | speedup vs linear | LRU@8 | order_hit |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in item["rows"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        fmt(row["policy"]),
                        fmt(row["us_per_tile"]["median"]),
                        fmt(row["us_per_tile"]["p10"]),
                        fmt(row["us_per_tile"]["p90"]),
                        fmt(row["us_per_tile"]["cv"]),
                        fmt(row.get("speedup_median_vs_linear")),
                        fmt(row["lru_hit_rate"].get("8")),
                        fmt(row["tile_order_hit_rate"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    summary = summarize(report)
    text = render_markdown(summary)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

