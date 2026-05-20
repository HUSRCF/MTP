#!/usr/bin/env python3
"""Summarize vLLM/AWQ descriptor reorder attribution telemetry.

The runtime timing records include both prefill and decode MoE calls.  This
script defaults to decode-only summaries so prefill work cannot dilute the
performance attribution for descriptor-order apply paths.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"runtime shadow file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)


def _float_field(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _summarize_values(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": float(mean(values)) if values else None,
        "p50": float(median(values)) if values else None,
        "p90": _percentile(values, 0.90),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": max(values) if values else None,
    }


def _compact_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "layer_apply_us": "descriptor_order_layer_apply_us",
        "permutation_us": "descriptor_order_consumer_handle_permutation_us",
        "plan_build_us": "descriptor_order_consumer_handle_plan_build_us",
        "clone_us": "descriptor_order_consumer_handle_clone_us",
        "index_select_us": "descriptor_order_consumer_handle_index_select_us",
    }
    stats: dict[str, Any] = {}
    for name, key in fields.items():
        values = [value for row in rows if (value := _float_field(row, key)) is not None]
        stats[name] = _summarize_values(values)
    return stats


def summarize_shadow(path: Path, *, phase: str) -> dict[str, Any]:
    rows = list(_read_jsonl(path))
    timing_rows = [row for row in rows if row.get("event_type") == "descriptor_layer_timing"]
    phase_counts = Counter(
        str(row.get("descriptor_order_layer_phase") or "unknown") for row in timing_rows
    )
    if phase == "all":
        selected = list(timing_rows)
    else:
        selected = [
            row
            for row in timing_rows
            if str(row.get("descriptor_order_layer_phase") or "unknown") == phase
        ]
    selected_policy_counts = Counter(
        str(row.get("descriptor_order_reorder_mvp_selected_policy") or "unknown")
        for row in selected
    )
    apply_mode_counts = Counter(
        str(row.get("descriptor_order_reorder_mvp_apply_mode") or "unknown")
        for row in selected
    )
    fallback_counts = Counter(
        str(row.get("descriptor_order_reorder_mvp_fallback_reason") or "none")
        for row in selected
    )
    attribution_counts = Counter(
        str(row.get("descriptor_order_consumer_handle_attribution_mode") or "unknown")
        for row in selected
    )
    applied_count = sum(
        1
        for row in selected
        if bool(row.get("descriptor_order_consumer_handle_applied"))
    )
    would_reorder_count = sum(
        1
        for row in selected
        if bool(row.get("descriptor_order_consumer_handle_would_reorder"))
    )
    attribution_breakdown: dict[str, dict[str, Any]] = {}
    for attribution_mode in sorted(attribution_counts):
        mode_rows = [
            row
            for row in selected
            if str(row.get("descriptor_order_consumer_handle_attribution_mode") or "unknown")
            == attribution_mode
        ]
        attribution_breakdown[attribution_mode] = {
            "count": len(mode_rows),
            "applied_count": sum(
                1
                for row in mode_rows
                if bool(row.get("descriptor_order_consumer_handle_applied"))
            ),
            "would_reorder_count": sum(
                1
                for row in mode_rows
                if bool(row.get("descriptor_order_consumer_handle_would_reorder"))
            ),
            "selected_policy_counts": dict(
                sorted(
                    Counter(
                        str(
                            row.get("descriptor_order_reorder_mvp_selected_policy")
                            or "unknown"
                        )
                        for row in mode_rows
                    ).items()
                )
            ),
            "fallback_counts": dict(
                sorted(
                    Counter(
                        str(row.get("descriptor_order_reorder_mvp_fallback_reason") or "none")
                        for row in mode_rows
                    ).items()
                )
            ),
            "stats": _compact_stats(mode_rows),
        }
    apply_mode_breakdown: dict[str, dict[str, Any]] = {}
    for apply_mode in sorted(apply_mode_counts):
        mode_rows = [
            row
            for row in selected
            if str(row.get("descriptor_order_reorder_mvp_apply_mode") or "unknown")
            == apply_mode
        ]
        applied_in_mode = sum(
            1
            for row in mode_rows
            if bool(row.get("descriptor_order_consumer_handle_applied"))
        )
        would_reorder_in_mode = sum(
            1
            for row in mode_rows
            if bool(row.get("descriptor_order_consumer_handle_would_reorder"))
        )
        apply_mode_breakdown[apply_mode] = {
            "count": len(mode_rows),
            "applied_count": applied_in_mode,
            "applied_ratio": (
                float(applied_in_mode / len(mode_rows)) if mode_rows else None
            ),
            "would_reorder_count": would_reorder_in_mode,
            "would_reorder_ratio": (
                float(would_reorder_in_mode / len(mode_rows)) if mode_rows else None
            ),
            "selected_policy_counts": dict(
                sorted(
                    Counter(
                        str(
                            row.get("descriptor_order_reorder_mvp_selected_policy")
                            or "unknown"
                        )
                        for row in mode_rows
                    ).items()
                )
            ),
            "fallback_counts": dict(
                sorted(
                    Counter(
                        str(row.get("descriptor_order_reorder_mvp_fallback_reason") or "none")
                        for row in mode_rows
                    ).items()
                )
            ),
            "attribution_counts": dict(
                sorted(
                    Counter(
                        str(
                            row.get("descriptor_order_consumer_handle_attribution_mode")
                            or "unknown"
                        )
                        for row in mode_rows
                    ).items()
                )
            ),
            "stats": _compact_stats(mode_rows),
        }
    return {
        "path": str(path),
        "total_rows": len(rows),
        "descriptor_layer_timing_count": len(timing_rows),
        "phase_filter": phase,
        "phase_counts": dict(sorted(phase_counts.items())),
        "selected_phase_count": len(selected),
        "selected_phase_ratio": (
            float(len(selected) / len(timing_rows)) if timing_rows else None
        ),
        "apply_mode_counts": dict(sorted(apply_mode_counts.items())),
        "selected_policy_counts": dict(sorted(selected_policy_counts.items())),
        "fallback_counts": dict(sorted(fallback_counts.items())),
        "attribution_counts": dict(sorted(attribution_counts.items())),
        "applied_count": applied_count,
        "applied_ratio": float(applied_count / len(selected)) if selected else None,
        "would_reorder_count": would_reorder_count,
        "would_reorder_ratio": (
            float(would_reorder_count / len(selected)) if selected else None
        ),
        "attribution_breakdown": attribution_breakdown,
        "apply_mode_breakdown": apply_mode_breakdown,
        "stats": _compact_stats(selected),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decode-only descriptor reorder attribution summary."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="runtime_shadow.jsonl files or directories containing that file.",
    )
    parser.add_argument(
        "--phase",
        default="decode",
        choices=("decode", "prefill", "unknown", "all"),
        help=(
            "Phase to include in timing statistics. Defaults to decode. "
            "Use all only for observability/debug summaries, not decode performance."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path.",
    )
    args = parser.parse_args()

    summaries = []
    for raw_path in args.paths:
        path = raw_path
        if path.is_dir():
            path = path / "runtime_shadow.jsonl"
        summaries.append(summarize_shadow(path, phase=args.phase))

    payload = {"phase": args.phase, "runs": summaries}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
