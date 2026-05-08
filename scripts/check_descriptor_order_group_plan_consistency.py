#!/usr/bin/env python3
"""Audit online descriptor-order two-level group-plan telemetry.

The runtime shadow path emits compact per sample/layer descriptor summaries.
This script checks that those summaries carry the producer-side fields needed by
the two-level descriptor consumer MVP, and optionally projects the observed
groups/CTA setting onto a measured consumer gate table.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence


REQUIRED_GROUP_PLAN_FIELDS = (
    "descriptor_order_execution_mode",
    "descriptor_group_plan_groups_per_cta",
    "descriptor_group_plan_group_count",
    "descriptor_group_plan_avg_group_size",
    "descriptor_group_plan_p95_group_size",
    "descriptor_group_plan_max_group_size",
    "descriptor_group_plan_cta_count",
)


def parse_csv_ints(value: str | None) -> list[int] | None:
    if value is None:
        return None
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-shadow-jsonl", type=Path, required=True)
    parser.add_argument("--gate-json", type=Path, default=None)
    parser.add_argument("--tile-elems", type=parse_csv_ints, default=None)
    parser.add_argument("--groups-per-cta", type=parse_csv_ints, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def _read_descriptor_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            event = json.loads(stripped)
            if not isinstance(event, dict):
                raise TypeError(f"line {line_number} is not a JSON object")
            if event.get("event_type") in {"descriptor_summary", "descriptor_summary_min"}:
                events.append(event)
    return events


def _number_values(events: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for event in events:
        value = event.get(key)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * float(q)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _stats(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "sum": None,
            "mean": None,
            "median": None,
            "p95": None,
            "max": None,
        }
    return {
        "count": int(len(values)),
        "sum": float(sum(values)),
        "mean": float(mean(values)),
        "median": float(median(values)),
        "p95": _percentile(values, 0.95),
        "max": float(max(values)),
    }


def _counter(events: Iterable[Mapping[str, Any]], key: str) -> dict[str, int]:
    return {
        str(value): int(count)
        for value, count in sorted(Counter(event.get(key) for event in events).items())
    }


def _missing_field_counts(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        field: sum(1 for event in events if event.get(field) is None)
        for field in REQUIRED_GROUP_PLAN_FIELDS
    }


def _gate_rows(
    gate_json: Path | None,
    *,
    groups_per_cta: Sequence[int] | None,
    tile_elems: Sequence[int] | None,
) -> list[dict[str, Any]]:
    if gate_json is None:
        return []
    gate = json.loads(gate_json.read_text(encoding="utf-8"))
    rows = gate.get("rows", [])
    if not isinstance(rows, list):
        return []
    group_filter = set(int(value) for value in groups_per_cta) if groups_per_cta else None
    tile_filter = set(int(value) for value in tile_elems) if tile_elems else None
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if group_filter is not None and int(row.get("groups_per_cta", -1)) not in group_filter:
            continue
        if tile_filter is not None and int(row.get("tile_elems", -1)) not in tile_filter:
            continue
        selected.append(dict(row))
    return selected


def _gate_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"row_count": 0, "allowed_count": 0, "allowed_by_tile": {}}
    allowed_by_tile: dict[str, dict[str, int]] = {}
    for row in rows:
        tile = str(row.get("tile_elems"))
        item = allowed_by_tile.setdefault(tile, {"rows": 0, "allowed": 0})
        item["rows"] += 1
        if bool(row.get("allow_two_level_descriptor_order")):
            item["allowed"] += 1
    return {
        "row_count": int(len(rows)),
        "allowed_count": sum(
            1 for row in rows if bool(row.get("allow_two_level_descriptor_order"))
        ),
        "allowed_by_tile": allowed_by_tile,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _render(report: Mapping[str, Any]) -> str:
    stats = report["field_stats"]
    gate = report["gate_summary"]
    lines = [
        "# Descriptor Group-Plan Online Consistency",
        "",
        f"- Runtime shadow: `{report['runtime_shadow_jsonl']}`",
        f"- Descriptor events: `{report['descriptor_event_count']}`",
        f"- Missing required fields: `{report['missing_required_field_total']}`",
        f"- Execution modes: `{report['execution_mode_counts']}`",
        f"- Groups/CTA counts: `{report['groups_per_cta_counts']}`",
        "",
        "## Producer Group Stats",
        "",
        "| field | count | sum | mean | median | p95 | max |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in (
        "descriptor_tile_request_count",
        "descriptor_unique_b_tiles",
        "descriptor_window_count",
        "descriptor_group_plan_group_count",
        "descriptor_group_plan_avg_group_size",
        "descriptor_group_plan_p95_group_size",
        "descriptor_group_plan_max_group_size",
        "descriptor_group_plan_cta_count",
        "descriptor_order_build_us",
        "candidate_construction_us",
        "decision_us",
        "counter_update_us",
    ):
        item = stats.get(key, {})
        lines.append(
            "| "
            + " | ".join(
                [
                    key,
                    _fmt(item.get("count")),
                    _fmt(item.get("sum")),
                    _fmt(item.get("mean")),
                    _fmt(item.get("median")),
                    _fmt(item.get("p95")),
                    _fmt(item.get("max")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Gate Projection",
            "",
            f"- Gate rows: `{gate.get('row_count', 0)}`",
            f"- Allowed rows: `{gate.get('allowed_count', 0)}`",
        ]
    )
    allowed_by_tile = gate.get("allowed_by_tile", {})
    if allowed_by_tile:
        lines.extend(
            [
                "",
                "| tile_elems | allowed | rows |",
                "|---:|---:|---:|",
            ]
        )
        for tile, item in sorted(allowed_by_tile.items(), key=lambda kv: int(kv[0])):
            lines.append(f"| {tile} | {item['allowed']} | {item['rows']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    events = _read_descriptor_events(args.runtime_shadow_jsonl)
    missing = _missing_field_counts(events)
    groups_per_cta_values = [
        int(value)
        for value in _number_values(events, "descriptor_group_plan_groups_per_cta")
    ]
    group_filter = args.groups_per_cta or sorted(set(groups_per_cta_values))
    gate_rows = _gate_rows(
        args.gate_json,
        groups_per_cta=group_filter,
        tile_elems=args.tile_elems,
    )
    fields = (
        "descriptor_tile_request_count",
        "descriptor_unique_b_tiles",
        "descriptor_window_count",
        "descriptor_group_plan_group_count",
        "descriptor_group_plan_avg_group_size",
        "descriptor_group_plan_p95_group_size",
        "descriptor_group_plan_max_group_size",
        "descriptor_group_plan_cta_count",
        "descriptor_order_build_us",
        "candidate_construction_us",
        "decision_us",
        "counter_update_us",
    )
    report = {
        "runtime_shadow_jsonl": str(args.runtime_shadow_jsonl),
        "gate_json": str(args.gate_json) if args.gate_json is not None else None,
        "tile_elems_filter": args.tile_elems,
        "groups_per_cta_filter": group_filter,
        "descriptor_event_count": int(len(events)),
        "execution_mode_counts": _counter(events, "descriptor_order_execution_mode"),
        "groups_per_cta_counts": _counter(events, "descriptor_group_plan_groups_per_cta"),
        "missing_required_fields": missing,
        "missing_required_field_total": int(sum(missing.values())),
        "field_stats": {
            field: _stats(_number_values(events, field)) for field in fields
        },
        "gate_rows": gate_rows,
        "gate_summary": _gate_summary(gate_rows),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(_render(report), encoding="utf-8")
    print(_render(report))


if __name__ == "__main__":
    main()
