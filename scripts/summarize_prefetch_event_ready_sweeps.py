#!/usr/bin/env python3
"""Summarize ready-time event queue cache-lab sweeps."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_entry(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError(
            f"Invalid entry {raw!r}; expected LABEL=PATH."
        )
    label, path = raw.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise argparse.ArgumentTypeError(
            f"Invalid entry {raw!r}; expected non-empty LABEL=PATH."
        )
    return label, Path(path)


def load_sweep(label: str, path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = list(payload.get("sweep_rows") or [])
    extra_rows = [
        row
        for row in rows
        if str(row.get("policy", "")).startswith("transition_top32_plus_")
        and int(row.get("extra_issued_vs_transition", 0) or 0) > 0
    ]
    best_extra = max(
        extra_rows,
        key=lambda row: float(row.get("net_saved_ms_vs_transition", float("-inf"))),
        default=None,
    )
    first_positive = payload.get("first_positive") or {}
    first_extra = payload.get("first_positive_mtp_extra_issued") or {}
    copy_scale = payload.get("copy_scale")
    if copy_scale is None:
        copy_scale = (payload.get("metadata") or {}).get("copy_scale", 1.0)
    return {
        "label": label,
        "path": path.as_posix(),
        "copy_scale": copy_scale,
        "queue_event_interval_us": (payload.get("base_config") or {}).get(
            "queue_event_interval_us"
        ),
        "max_inflight": payload.get("max_inflight") or [],
        "deadline_us": payload.get("deadline_us") or [],
        "first_positive": first_positive,
        "first_positive_mtp_extra_issued": first_extra,
        "has_positive_any": bool(first_positive),
        "has_positive_mtp_extra_issued": bool(first_extra),
        "best_extra_issued": _compact_row(best_extra),
    }


def _compact_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    return {
        "policy": row.get("policy"),
        "max_inflight": row.get("max_inflight"),
        "deadline_us": row.get("deadline_us"),
        "net_saved_ms_vs_transition": row.get("net_saved_ms_vs_transition"),
        "extra_issued_vs_transition": row.get("extra_issued_vs_transition"),
        "late_miss_count": row.get("late_miss_count"),
        "late_completion_unused_count": row.get("late_completion_unused_count"),
    }


def summarize(entries: list[tuple[str, Path]]) -> dict[str, Any]:
    rows = [load_sweep(label, path) for label, path in entries]
    return {
        "ok": True,
        "boundary": (
            "Ready-time event queue sweep summary only; prefetch hits require "
            "virtual H2D completion before the demand deadline. This is not "
            "endpoint TPOT and not a real vLLM DMA/cache manager."
        ),
        "rows": rows,
        "positive_mtp_extra_issued_count": sum(
            1 for row in rows if row["has_positive_mtp_extra_issued"]
        ),
        "positive_any_count": sum(1 for row in rows if row["has_positive_any"]),
    }


def write_csv(path: Path, payload: dict[str, Any]) -> None:
    fieldnames = [
        "label",
        "copy_scale",
        "queue_event_interval_us",
        "has_positive_any",
        "has_positive_mtp_extra_issued",
        "first_positive_summary",
        "first_positive_mtp_extra_summary",
        "best_extra_issued_summary",
        "path",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in payload["rows"]:
            writer.writerow(
                {
                    "label": row["label"],
                    "copy_scale": row["copy_scale"],
                    "queue_event_interval_us": row["queue_event_interval_us"],
                    "has_positive_any": row["has_positive_any"],
                    "has_positive_mtp_extra_issued": row[
                        "has_positive_mtp_extra_issued"
                    ],
                    "first_positive_summary": _format_first_positive(
                        row["first_positive"]
                    ),
                    "first_positive_mtp_extra_summary": _format_first_positive(
                        row["first_positive_mtp_extra_issued"]
                    ),
                    "best_extra_issued_summary": _format_row_summary(
                        row["best_extra_issued"]
                    ),
                    "path": row["path"],
                }
            )


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ready-Time Event Queue Sweep Sensitivity",
        "",
        payload["boundary"],
        "",
        "## Summary",
        "",
        f"- sweeps: {len(payload['rows'])}",
        f"- positive_any_count: {payload['positive_any_count']}",
        "- positive_mtp_extra_issued_count: "
        f"{payload['positive_mtp_extra_issued_count']}",
        "",
        "## Rows",
        "",
        "| sweep | copy_scale | event_interval_us | any positive | "
        "MTP-extra positive | first positive | first MTP-extra | best extra-issued |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['label']}` | {row['copy_scale']} | "
            f"{row['queue_event_interval_us']} | "
            f"{_yes_no(row['has_positive_any'])} | "
            f"{_yes_no(row['has_positive_mtp_extra_issued'])} | "
            f"{_format_first_positive(row['first_positive'])} | "
            f"{_format_first_positive(row['first_positive_mtp_extra_issued'])} | "
            f"{_format_row_summary(row['best_extra_issued'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Same-issued positive cells are tracked separately from MTP-extra "
            "full_fetch evidence.",
            "- `MTP-extra positive = no` means no `_plus_*` policy both improved net "
            "saved time and issued more payload than `transition_top32` in that "
            "sweep.",
            "- Under these sweeps, full_fetch extras should remain gated/fallback "
            "until admission, lookahead, or copy overlap changes produce a "
            "positive MTP-extra-issued cell.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_first_positive(items: dict[str, Any]) -> str:
    if not items:
        return "`{}`"
    parts = []
    for policy, row in sorted(items.items()):
        parts.append(f"{policy}: {_format_row_summary(row)}")
    return "<br>".join(parts)


def _format_row_summary(row: dict[str, Any]) -> str:
    if not row:
        return "`{}`"
    policy = row.get("policy")
    prefix = f"{policy}: " if policy else ""
    return (
        f"{prefix}inflight={row.get('max_inflight')}, "
        f"deadline={row.get('deadline_us')}, "
        f"net={_fmt_float(row.get('net_saved_ms_vs_transition'))}ms, "
        f"extra={row.get('extra_issued_vs_transition')}"
    )


def _fmt_float(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.3f}"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", action="append", type=parse_entry, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    payload = summarize(args.entry)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(args.output_csv, payload)


if __name__ == "__main__":
    main()
