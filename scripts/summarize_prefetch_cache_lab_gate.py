#!/usr/bin/env python3
"""Build a compact gate summary from prefetch cache-lab sweep summaries."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capacity-summary", type=Path, required=True)
    parser.add_argument("--overlap-summary", type=Path, required=True)
    parser.add_argument("--manager-summary", type=Path, required=True)
    parser.add_argument("--bandwidth-summary", type=Path, required=True)
    parser.add_argument("--policy-suffix", default="_plus_utility_keep50")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--md-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = {
        "boundary": (
            "Bounded-cache lab replay gate only; not endpoint TPOT and not a "
            "real vLLM cache-manager implementation."
        ),
        "policy_suffix": args.policy_suffix,
        "first_positive_capacity": first_positive_capacity(
            _load_rows(args.capacity_summary), policy_suffix=args.policy_suffix
        ),
        "first_positive_overlap": first_positive_overlap(
            _load_rows(args.overlap_summary), policy_suffix=args.policy_suffix
        ),
        "manager_sensitivity": all_positive_by_group(
            _load_rows(args.manager_summary),
            policy_suffix=args.policy_suffix,
            variable="manager_us_per_issue",
        ),
        "bandwidth_sensitivity": all_positive_by_group(
            _load_rows(args.bandwidth_summary),
            policy_suffix=args.policy_suffix,
            variable="bandwidth_gbps",
        ),
    }
    markdown = render_markdown(payload)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.md_output is not None:
        args.md_output.parent.mkdir(parents=True, exist_ok=True)
        args.md_output.write_text(markdown, encoding="utf-8")
    print(markdown)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise TypeError(f"{path} must contain a list of summary rows.")
    return [row for row in rows if isinstance(row, dict)]


def _is_policy(row: dict[str, Any], *, policy_suffix: str) -> bool:
    return str(row.get("policy", "")).endswith(policy_suffix)


def _key(row: dict[str, Any]) -> str:
    return "/".join(
        str(part)
        for part in (row.get("dataset"), row.get("split"))
        if part not in (None, "")
    )


def _net(row: dict[str, Any]) -> float:
    return float(row.get("net_saved_ms_vs_transition") or 0.0)


def first_positive_capacity(
    rows: list[dict[str, Any]], *, policy_suffix: str
) -> list[dict[str, Any]]:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _is_policy(row, policy_suffix=policy_suffix):
            by_key[_key(row)].append(row)
    result = []
    for key, group in sorted(by_key.items()):
        ordered = sorted(group, key=lambda row: int(row.get("cache_capacity") or 0))
        first = next((row for row in ordered if _net(row) > 0.0), None)
        result.append(
            {
                "dataset_split": key,
                "first_positive_capacity": (
                    int(first["cache_capacity"]) if first is not None else None
                ),
                "first_positive_net_saved_ms": (
                    _net(first) if first is not None else None
                ),
                "tested": [
                    {
                        "capacity": int(row.get("cache_capacity") or 0),
                        "net_saved_ms_vs_transition": _net(row),
                    }
                    for row in ordered
                ],
            }
        )
    return result


def first_positive_overlap(
    rows: list[dict[str, Any]], *, policy_suffix: str
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _is_policy(row, policy_suffix=policy_suffix):
            by_key[(_key(row), int(row.get("cache_capacity") or 0))].append(row)
    result = []
    for (key, capacity), group in sorted(by_key.items()):
        ordered = sorted(group, key=lambda row: float(row.get("overlap_factor") or 0.0))
        first = next((row for row in ordered if _net(row) > 0.0), None)
        result.append(
            {
                "dataset_split": key,
                "cache_capacity": capacity,
                "first_positive_overlap": (
                    float(first["overlap_factor"]) if first is not None else None
                ),
                "first_positive_net_saved_ms": (
                    _net(first) if first is not None else None
                ),
                "tested": [
                    {
                        "overlap_factor": float(row.get("overlap_factor") or 0.0),
                        "net_saved_ms_vs_transition": _net(row),
                    }
                    for row in ordered
                ],
            }
        )
    return result


def all_positive_by_group(
    rows: list[dict[str, Any]], *, policy_suffix: str, variable: str
) -> list[dict[str, Any]]:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _is_policy(row, policy_suffix=policy_suffix):
            by_key[_key(row)].append(row)
    result = []
    for key, group in sorted(by_key.items()):
        ordered = sorted(group, key=lambda row: float(row.get(variable) or 0.0))
        result.append(
            {
                "dataset_split": key,
                "variable": variable,
                "all_positive": all(_net(row) > 0.0 for row in ordered),
                "min_net_saved_ms": min((_net(row) for row in ordered), default=0.0),
                "tested": [
                    {
                        variable: float(row.get(variable) or 0.0),
                        "net_saved_ms_vs_transition": _net(row),
                    }
                    for row in ordered
                ],
            }
        )
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prefetch Cache Lab Gate Summary",
        "",
        "Boundary:",
        "",
        "```text",
        str(payload["boundary"]),
        "```",
        "",
        f"Policy suffix: `{payload['policy_suffix']}`",
        "",
        "## First Positive Capacity",
        "",
        "| dataset/split | first positive capacity | net saved ms |",
        "|---|---:|---:|",
    ]
    for row in payload["first_positive_capacity"]:
        lines.append(
            "| {dataset_split} | {capacity} | {net} |".format(
                dataset_split=row["dataset_split"],
                capacity=_fmt_optional(row["first_positive_capacity"]),
                net=_fmt_optional(row["first_positive_net_saved_ms"]),
            )
        )
    lines.extend(
        [
            "",
            "## First Positive Overlap",
            "",
            "| dataset/split | capacity | first positive overlap | net saved ms |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in payload["first_positive_overlap"]:
        lines.append(
            "| {dataset_split} | {capacity} | {overlap} | {net} |".format(
                dataset_split=row["dataset_split"],
                capacity=row["cache_capacity"],
                overlap=_fmt_optional(row["first_positive_overlap"]),
                net=_fmt_optional(row["first_positive_net_saved_ms"]),
            )
        )
    lines.extend(
        [
            "",
            "## Sensitivity Checks",
            "",
            "| sweep | dataset/split | all positive | min net saved ms |",
            "|---|---|---:|---:|",
        ]
    )
    for section in ("manager_sensitivity", "bandwidth_sensitivity"):
        for row in payload[section]:
            lines.append(
                "| {section} | {dataset_split} | {all_positive} | {min_net} |".format(
                    section=section,
                    dataset_split=row["dataset_split"],
                    all_positive=row["all_positive"],
                    min_net=f"{float(row['min_net_saved_ms']):.3f}",
                )
            )
    lines.append("")
    return "\n".join(lines)


def _fmt_optional(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


if __name__ == "__main__":
    main()
