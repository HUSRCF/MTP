#!/usr/bin/env python3
"""Build a gate table for descriptor-order HIP consumer reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--policy-substring", default="two_level")
    parser.add_argument("--min-speedup", type=float, default=1.0)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _rows(report: dict[str, Any], *, policy_substring: str, min_speedup: float) -> list[dict[str, Any]]:
    policy_substring = str(policy_substring)
    output = []
    for row in report.get("summary", {}).get("stability", []):
        policy = str(row.get("policy", ""))
        if policy_substring and policy_substring not in policy:
            continue
        speedup = row.get("speedup_median_vs_no_order")
        checksum_delta = row.get("checksum_delta_abs_vs_no_order")
        allowed = (
            speedup is not None
            and float(speedup) >= float(min_speedup)
            and float(checksum_delta or 0.0) == 0.0
        )
        output.append(
            {
                "device": int(row["device"]),
                "tile_elems": int(row["tile_elems"]),
                "groups_per_cta": int(row["tiles_per_cta"]),
                "cache_flush_elems": int(row["cache_flush_elems"]),
                "policy": policy,
                "speedup_median_vs_no_order": speedup,
                "consumer_saved_us": row.get("consumer_saved_us_median_vs_no_order"),
                "checksum_delta": checksum_delta,
                "allow_two_level_descriptor_order": bool(allowed),
                "reason": (
                    "profitable_checksum_ok"
                    if allowed
                    else "not_profitable_or_checksum_mismatch"
                ),
            }
        )
    return sorted(
        output,
        key=lambda item: (
            item["device"],
            item["tile_elems"],
            item["groups_per_cta"],
            item["cache_flush_elems"],
        ),
    )


def _render(report: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    group_plan = report.get("two_level_group_plan") or {}
    lines = [
        "# Descriptor Consumer Gate Table",
        "",
        f"- Source report: `{report.get('config', {}).get('trace_dir', 'n/a')}`",
        f"- Selected windows: `{report.get('selection', {}).get('selected_window_count', 'n/a')}`",
        f"- Selected requests: `{report.get('selection', {}).get('selected_request_count', 'n/a')}`",
        "",
    ]
    if group_plan:
        lines.extend(
            [
                "## Group-Plan Stats",
                "",
                f"- group_count: `{group_plan.get('group_count')}`",
                f"- avg_group_size: `{_fmt(group_plan.get('avg_group_size'))}`",
                f"- p95_group_size: `{_fmt(group_plan.get('p95_group_size'))}`",
                f"- max_group_size: `{group_plan.get('max_group_size')}`",
                f"- avg_groups_per_window: `{_fmt(group_plan.get('avg_groups_per_window'))}`",
                f"- p95_groups_per_window: `{_fmt(group_plan.get('p95_groups_per_window'))}`",
                f"- max_groups_per_window: `{group_plan.get('max_groups_per_window')}`",
                "",
            ]
        )
    allowed = sum(1 for row in rows if row["allow_two_level_descriptor_order"])
    lines.extend(
        [
            "## Gate Rows",
            "",
            f"- Allowed rows: `{allowed}/{len(rows)}`",
            "",
            "| device | tile_elems | groups/CTA | flush | speedup | saved_us | checksum_delta | allow | reason |",
            "|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["device"]),
                    str(row["tile_elems"]),
                    str(row["groups_per_cta"]),
                    str(row["cache_flush_elems"]),
                    _fmt(row["speedup_median_vs_no_order"]),
                    _fmt(row["consumer_saved_us"]),
                    _fmt(row["checksum_delta"]),
                    str(row["allow_two_level_descriptor_order"]),
                    row["reason"],
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    report = json.loads(args.input_json.read_text(encoding="utf-8"))
    rows = _rows(
        report,
        policy_substring=str(args.policy_substring),
        min_speedup=float(args.min_speedup),
    )
    payload = {
        "input_json": str(args.input_json),
        "policy_substring": str(args.policy_substring),
        "min_speedup": float(args.min_speedup),
        "rows": rows,
        "allowed_count": sum(1 for row in rows if row["allow_two_level_descriptor_order"]),
        "row_count": len(rows),
        "two_level_group_plan": report.get("two_level_group_plan"),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(_render(report, rows), encoding="utf-8")
    print(_render(report, rows))


if __name__ == "__main__":
    main()
