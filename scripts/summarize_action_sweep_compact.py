#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize action-level event-stall reports as compact tables."
    )
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--csv-output", type=Path, default=None)
    parser.add_argument("--md-output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    for report in args.reports:
        payload = json.loads(report.read_text(encoding="utf-8"))
        rows.extend(_extract_rows(report, payload))
    if args.csv_output is not None:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(args.csv_output, rows)
    markdown = _format_markdown(rows)
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def _extract_rows(report: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for policy, metrics in payload["policies"].items():
        if not _include_policy(policy):
            continue
        outcomes = metrics.get("admission_action_outcomes", {})
        metadata = outcomes.get("metadata", {})
        premap = outcomes.get("premap", {})
        rows.append(
            {
                "report": report.name,
                "bandwidth_gbps": payload.get("bandwidth_gbps"),
                "layer_ms": payload.get("layer_ms"),
                "mtp_delay_ms": payload.get("mtp_delay_ms"),
                "policy": policy,
                "ready_mass": float(metrics.get("ready_mass_fraction", 0.0)),
                "top1_hit": float(metrics.get("ready_top1_hit_rate", 0.0)),
                "weighted_miss": float(
                    metrics.get("weighted_top1_supplemental_miss", 0.0)
                ),
                "stall_reduction": float(
                    metrics.get("stall_reduction_ratio_vs_transition", 0.0)
                ),
                "delta_issued_tb": float(
                    metrics.get("delta_issued_bytes_vs_transition", 0.0)
                )
                / 1e12,
                "metadata_later_used": int(metadata.get("later_used_count", 0)),
                "premap_later_used": int(premap.get("later_used_count", 0)),
                "setup_saved_ms": float(metrics.get("metadata_premap_setup_saved_ms", 0.0)),
                "ready_extra_fraction": float(metrics.get("queue_ready_extra_fraction", 0.0)),
            }
        )
    return rows


def _include_policy(name: str) -> bool:
    return (
        name == "transition_ready"
        or "ready_mtp_extra" in name
        or "gated_score" in name
        or "gated_utility" in name
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "report",
        "bandwidth_gbps",
        "layer_ms",
        "mtp_delay_ms",
        "policy",
        "ready_mass",
        "top1_hit",
        "weighted_miss",
        "stall_reduction",
        "delta_issued_tb",
        "metadata_later_used",
        "premap_later_used",
        "setup_saved_ms",
        "ready_extra_fraction",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| report | policy | bw | layer ms | delay ms | ready mass | top1 | weighted miss | stall red. | issued TB | metadata used | premap used | setup saved ms | ready extra |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {report} | {policy} | {bandwidth_gbps} | {layer_ms} | {mtp_delay_ms} | "
            "{ready_mass:.4f} | {top1_hit:.4f} | {weighted_miss:.4f} | "
            "{stall_reduction:.4f} | {delta_issued_tb:.3f} | "
            "{metadata_later_used} | {premap_later_used} | {setup_saved_ms:.2f} | "
            "{ready_extra_fraction:.4f} |".format(**row)
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
