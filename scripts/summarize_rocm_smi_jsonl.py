#!/usr/bin/env python3
"""Summarize rocm-smi JSONL samples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct / 100.0
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "min": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    return {
        "count": len(values),
        "mean": mean(values),
        "min": min(values),
        "p50": _percentile(values, 50.0),
        "p95": _percentile(values, 95.0),
        "p99": _percentile(values, 99.0),
        "max": max(values),
    }


def summarize(
    path: Path,
    *,
    elapsed_min_s: float | None = None,
    elapsed_max_s: float | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    if elapsed_min_s is not None:
        rows = [
            row
            for row in rows
            if float(row.get("elapsed_s", 0.0)) >= elapsed_min_s
        ]
    if elapsed_max_s is not None:
        rows = [
            row
            for row in rows
            if float(row.get("elapsed_s", 0.0)) <= elapsed_max_s
        ]
    ok_rows = [row for row in rows if row.get("ok")]
    fields = [
        "gpu_use_pct",
        "vram_allocated_pct",
        "mem_rw_activity_pct",
        "avg_graphics_power_w",
    ]
    result: dict[str, Any] = {
        "path": str(path),
        "row_count": len(rows),
        "ok_count": len(ok_rows),
        "elapsed_filter_min_s": elapsed_min_s,
        "elapsed_filter_max_s": elapsed_max_s,
        "elapsed_s_min": min((row.get("elapsed_s", 0.0) for row in rows), default=None),
        "elapsed_s_max": max((row.get("elapsed_s", 0.0) for row in rows), default=None),
        "fields": {},
    }
    for field in fields:
        values = [
            float(row[field])
            for row in ok_rows
            if row.get(field) is not None
        ]
        result["fields"][field] = _summary(values)
    return result


def _write_markdown(summary: dict[str, Any], output: Path) -> None:
    lines = [
        "# ROCm SMI Summary",
        "",
        f"path: `{summary['path']}`",
        f"rows: `{summary['row_count']}`",
        f"ok rows: `{summary['ok_count']}`",
        f"elapsed_s: `{summary['elapsed_s_min']}` to `{summary['elapsed_s_max']}`",
        "",
        "| field | count | mean | p50 | p95 | p99 | max |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for field, stats in summary["fields"].items():
        lines.append(
            "| {field} | {count} | {mean} | {p50} | {p95} | {p99} | {max} |".format(
                field=field,
                count=stats["count"],
                mean=_fmt(stats["mean"]),
                p50=_fmt(stats["p50"]),
                p95=_fmt(stats["p95"]),
                p99=_fmt(stats["p99"]),
                max=_fmt(stats["max"]),
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--elapsed-min-s", type=float)
    parser.add_argument("--elapsed-max-s", type=float)
    args = parser.parse_args()
    summary = summarize(
        args.jsonl,
        elapsed_min_s=args.elapsed_min_s,
        elapsed_max_s=args.elapsed_max_s,
    )
    if args.output_json:
        args.output_json.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.output_md:
        _write_markdown(summary, args.output_md)
    if not args.output_json and not args.output_md:
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
