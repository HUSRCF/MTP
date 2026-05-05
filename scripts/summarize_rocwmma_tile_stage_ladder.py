#!/usr/bin/env python3
"""Summarize rocWMMA mode-specialized timing ladder reports."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-md", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--top-k", type=int, default=12)
    return parser.parse_args()


def key_of(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["device"],
        row["consumer_rows"],
        row["num_cta"],
        row["b_pool_tiles"],
        row.get("tile_stride", 1),
        row.get("row_tile_stride", 1),
        row["cache_flush_elems"],
        row["validate_iters"],
    )


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def summarize(report: dict[str, Any], *, top_k: int) -> dict[str, Any]:
    by_key: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in report["results"]:
        by_key[key_of(row)][str(row["mode"])] = row

    rows: list[dict[str, Any]] = []
    for key, modes in sorted(by_key.items()):
        frag = modes.get("global_frag_reuse")
        reload_same = modes.get("global_reload_per_row")
        reload_distinct = modes.get("global_reload_distinct_per_row")
        lds_hit = modes.get("lds_hit")
        lds_miss = modes.get("lds_miss_overwrite")
        if not (frag and reload_same and reload_distinct and lds_hit and lds_miss):
            continue
        frag_ms = float(frag["wall_ms_mean"])
        reload_ms = float(reload_same["wall_ms_mean"])
        distinct_ms = float(reload_distinct["wall_ms_mean"])
        hit_ms = float(lds_hit["wall_ms_mean"])
        miss_ms = float(lds_miss["wall_ms_mean"])
        item = {
            "device": key[0],
            "consumer_rows": key[1],
            "num_cta": key[2],
            "b_pool_tiles": key[3],
            "tile_stride": key[4],
            "row_tile_stride": key[5],
            "cache_flush_elems": key[6],
            "validate_iters": key[7],
            "frag_ms": frag_ms,
            "reload_ms": reload_ms,
            "distinct_ms": distinct_ms,
            "lds_hit_ms": hit_ms,
            "lds_miss_ms": miss_ms,
            "reload_gap_vs_frag_ms": reload_ms - frag_ms,
            "distinct_gap_vs_frag_ms": distinct_ms - frag_ms,
            "distinct_gap_vs_reload_ms": distinct_ms - reload_ms,
            "hit_delta_vs_frag_ms": hit_ms - frag_ms,
            "hit_delta_vs_reload_ms": hit_ms - reload_ms,
            "hit_delta_vs_distinct_ms": hit_ms - distinct_ms,
            "hit_beats_frag": hit_ms < frag_ms,
            "hit_beats_reload": hit_ms < reload_ms,
            "hit_beats_distinct": hit_ms < distinct_ms,
            "miss_beats_distinct": miss_ms < distinct_ms,
        }
        rows.append(item)

    p_min_status = Counter()
    p_min_status_by_baseline: dict[str, Counter[str]] = defaultdict(Counter)
    finite_pmin_by_baseline: dict[str, list[float]] = defaultdict(list)
    for row in report.get("summary", {}).get("p_min", []):
        baseline = str(row["baseline"])
        status = str(row["status"])
        p_min_status[status] += 1
        p_min_status_by_baseline[baseline][status] += 1
        if row.get("p_min_hit_rate") is not None:
            finite_pmin_by_baseline[baseline].append(float(row["p_min_hit_rate"]))

    aggregates = {
        "config_count": len(rows),
        "hit_beats_frag_count": sum(bool(row["hit_beats_frag"]) for row in rows),
        "hit_beats_reload_count": sum(bool(row["hit_beats_reload"]) for row in rows),
        "hit_beats_distinct_count": sum(bool(row["hit_beats_distinct"]) for row in rows),
        "miss_beats_distinct_count": sum(bool(row["miss_beats_distinct"]) for row in rows),
        "p_min_status": dict(p_min_status),
        "p_min_status_by_baseline": {
            baseline: dict(counter) for baseline, counter in sorted(p_min_status_by_baseline.items())
        },
        "finite_pmin_by_baseline": {
            baseline: {
                "count": len(values),
                "min": min(values) if values else None,
                "median": sorted(values)[len(values) // 2] if values else None,
                "max": max(values) if values else None,
            }
            for baseline, values in sorted(finite_pmin_by_baseline.items())
        },
    }

    best_vs_distinct = sorted(rows, key=lambda row: row["hit_delta_vs_distinct_ms"])[:top_k]
    worst_vs_distinct = sorted(rows, key=lambda row: row["hit_delta_vs_distinct_ms"], reverse=True)[:top_k]
    strongest_reload_pressure = sorted(rows, key=lambda row: row["distinct_gap_vs_frag_ms"], reverse=True)[:top_k]
    return {
        "ok": bool(report.get("ok", False)),
        "source_config": report.get("config", {}),
        "aggregates": aggregates,
        "rows": rows,
        "best_vs_distinct": best_vs_distinct,
        "worst_vs_distinct": worst_vs_distinct,
        "strongest_reload_pressure": strongest_reload_pressure,
    }


def render_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(col)) for col in columns) + " |")
    return lines


def write_markdown(summary: dict[str, Any]) -> str:
    agg = summary["aggregates"]
    lines = [
        "# rocWMMA Tile-Stage Ladder Summary",
        "",
        "This summarizes mode-specialized timing rows. Hardware traffic counters are",
        "not used here; this is timing classification plus p_min status.",
        "",
        "## Aggregates",
        "",
        f"- Config rows: `{agg['config_count']}`",
        f"- LDS hit beats frag: `{agg['hit_beats_frag_count']}`",
        f"- LDS hit beats reload: `{agg['hit_beats_reload_count']}`",
        f"- LDS hit beats distinct reload: `{agg['hit_beats_distinct_count']}`",
        f"- LDS miss beats distinct reload: `{agg['miss_beats_distinct_count']}`",
        f"- p_min status: `{agg['p_min_status']}`",
        f"- p_min by baseline: `{agg['p_min_status_by_baseline']}`",
        f"- finite p_min by baseline: `{agg['finite_pmin_by_baseline']}`",
        "",
        "## Strongest Distinct-Reload Pressure",
        "",
    ]
    columns = [
        "device",
        "consumer_rows",
        "num_cta",
        "b_pool_tiles",
        "cache_flush_elems",
        "frag_ms",
        "distinct_ms",
        "distinct_gap_vs_frag_ms",
        "lds_hit_ms",
        "hit_delta_vs_distinct_ms",
    ]
    lines.extend(render_table(summary["strongest_reload_pressure"], columns))
    lines.extend(["", "## Best LDS Hit vs Distinct Reload", ""])
    lines.extend(render_table(summary["best_vs_distinct"], columns))
    lines.extend(["", "## Worst LDS Hit vs Distinct Reload", ""])
    lines.extend(render_table(summary["worst_vs_distinct"], columns))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    summary = summarize(report, top_k=args.top_k)
    text = write_markdown(summary)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
