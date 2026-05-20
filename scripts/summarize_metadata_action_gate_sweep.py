#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize metadata action-gate sweep break-even points."
    )
    parser.add_argument("sweep", type=Path, help="JSON or CSV from sweep_metadata_action_gate.py")
    parser.add_argument("--csv-output", type=Path, default=None)
    parser.add_argument("--md-output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _read_rows(args.sweep)
    summary_rows = _summarize(rows)
    if args.csv_output is not None:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(args.csv_output, summary_rows)
    markdown = _format_markdown(summary_rows)
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(row) for row in payload["rows"]]


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(_short_policy(str(row["policy"])), float(row["metadata_ratio"]))].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (policy, metadata_ratio), group in grouped.items():
        sorted_group = sorted(group, key=lambda row: float(row["overlap_factor"]))
        positives = [
            row
            for row in sorted_group
            if float(row["metadata_overlap_adjusted_net_setup_benefit_ms"]) > 0.0
        ]
        first_positive = positives[0] if positives else None
        best = max(
            sorted_group,
            key=lambda row: float(row["metadata_overlap_adjusted_net_setup_benefit_ms"]),
        )
        premap_positives = [
            row
            for row in sorted_group
            if float(row.get("premap_overlap_adjusted_net_setup_benefit_ms", 0.0))
            > 0.0
        ]
        first_positive_premap = premap_positives[0] if premap_positives else None
        premap_best = max(
            sorted_group,
            key=lambda row: float(
                row.get("premap_overlap_adjusted_net_setup_benefit_ms", 0.0)
            ),
        )
        serial = min(sorted_group, key=lambda row: float(row["overlap_factor"]))
        summary_rows.append(
            {
                "policy": policy,
                "metadata_ratio": metadata_ratio,
                "metadata_count": int(float(best["metadata_count"])),
                "later_used_rate": float(best["metadata_later_used_rate"]),
                "serial_net_ms": float(serial["metadata_net_setup_benefit_ms"]),
                "first_positive_overlap": (
                    float(first_positive["overlap_factor"])
                    if first_positive is not None
                    else None
                ),
                "first_positive_net_ms": (
                    float(first_positive["metadata_overlap_adjusted_net_setup_benefit_ms"])
                    if first_positive is not None
                    else None
                ),
                "best_overlap": float(best["overlap_factor"]),
                "best_net_ms": float(best["metadata_overlap_adjusted_net_setup_benefit_ms"]),
                "setup_saved_ms": float(best["metadata_setup_saved_ms"]),
                "premap_budget_max_extra": int(
                    float(premap_best.get("premap_budget_max_extra", 0.0))
                ),
                "premap_count": int(float(premap_best.get("premap_count", 0.0))),
                "premap_later_used_rate": float(
                    premap_best.get("premap_later_used_rate", 0.0)
                ),
                "premap_first_positive_overlap": (
                    float(first_positive_premap["overlap_factor"])
                    if first_positive_premap is not None
                    else None
                ),
                "premap_first_positive_net_ms": (
                    float(
                        first_positive_premap[
                            "premap_overlap_adjusted_net_setup_benefit_ms"
                        ]
                    )
                    if first_positive_premap is not None
                    else None
                ),
                "premap_best_overlap": float(premap_best["overlap_factor"]),
                "premap_best_net_ms": float(
                    premap_best.get("premap_overlap_adjusted_net_setup_benefit_ms", 0.0)
                ),
                "stall_reduction_pct": 100.0
                * float(best["stall_reduction_ratio_vs_transition"]),
            }
        )
    return sorted(
        summary_rows,
        key=lambda row: (
            row["policy"],
            row["first_positive_overlap"] is None,
            row["first_positive_overlap"] if row["first_positive_overlap"] is not None else 99.0,
            row["metadata_ratio"],
        ),
    )


def _short_policy(name: str) -> str:
    return (
        name.replace("transition_top32_plus_gated_", "")
        .replace("keep_top_", "keep")
        .replace("0.500", "50")
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "policy",
        "metadata_ratio",
        "metadata_count",
        "later_used_rate",
        "serial_net_ms",
        "first_positive_overlap",
        "first_positive_net_ms",
        "best_overlap",
        "best_net_ms",
        "setup_saved_ms",
        "premap_budget_max_extra",
        "premap_count",
        "premap_later_used_rate",
        "premap_first_positive_overlap",
        "premap_first_positive_net_ms",
        "premap_best_overlap",
        "premap_best_net_ms",
        "stall_reduction_pct",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| policy | metadata ratio | metadata later-used % | serial net ms | first positive overlap | best overlap | metadata best net ms | premap max | premap later-used % | premap first positive overlap | premap best overlap | premap best net ms | stall reduction % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        first_positive = row["first_positive_overlap"]
        first_positive_text = (
            f"{first_positive:.2f}" if first_positive is not None else "none"
        )
        premap_first_positive = row["premap_first_positive_overlap"]
        premap_first_positive_text = (
            f"{premap_first_positive:.2f}"
            if premap_first_positive is not None
            else "none"
        )
        lines.append(
            "| {policy} | {metadata_ratio:.2f} | {later_used_rate:.2%} | "
            "{serial_net_ms:.1f} | {first_positive} | {best_overlap:.2f} | "
            "{best_net_ms:.1f} | {premap_budget_max_extra:d} | "
            "{premap_later_used_rate:.2%} | {premap_first_positive} | "
            "{premap_best_overlap:.2f} | {premap_best_net_ms:.1f} | "
            "{stall_reduction_pct:.2f} |".format(
                **row,
                first_positive=first_positive_text,
                premap_first_positive=premap_first_positive_text,
            )
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
