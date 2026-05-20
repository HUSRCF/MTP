#!/usr/bin/env python3
"""Summarize repeated AWQ/vLLM telemetry ladder runs.

This helper intentionally reports only metrics that are present in the ladder
`results.json`.  Per-sample p95/p99 latency is not inferred from endpoint TPOT.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any


def _load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return [row for row in data["results"] if isinstance(row, dict)]
    raise ValueError(f"Unsupported results format in {path}")


def _tpot(row: dict[str, Any]) -> float | None:
    value = row.get("generate_seconds_per_requested_output_token")
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _parse_returncode(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _summarize_values(values: list[float]) -> dict[str, Any]:
    values_sorted = sorted(values)
    out: dict[str, Any] = {
        "count": len(values_sorted),
        "values": values_sorted,
        "median": statistics.median(values_sorted),
        "mean": statistics.mean(values_sorted),
        "min": min(values_sorted),
        "max": max(values_sorted),
    }
    out["stdev"] = statistics.stdev(values_sorted) if len(values_sorted) > 1 else 0.0
    return out


def _quantile_nearest_rank(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile of empty values")
    values_sorted = sorted(values)
    index = max(0, min(len(values_sorted) - 1, math.ceil(q * len(values_sorted)) - 1))
    return values_sorted[index]


def _load_sample_timing_tpots(
    trace_dir_value: Any,
) -> tuple[list[float], list[dict[str, Any]]]:
    if not trace_dir_value:
        return [], []
    path = Path(str(trace_dir_value)) / "sample_timing.jsonl"
    if not path.exists():
        return [], []
    values: list[float] = []
    invalid_rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                invalid_rows.append(
                    {
                        "reason": "invalid_sample_timing_json",
                        "path": str(path),
                        "line_no": line_no,
                    }
                )
                continue
            if not isinstance(row, dict):
                invalid_rows.append(
                    {
                        "reason": "invalid_sample_timing_row",
                        "path": str(path),
                        "line_no": line_no,
                    }
                )
                continue
            if row.get("scope") != "sample":
                continue
            if row.get("status", "ok") != "ok":
                invalid_rows.append(
                    {
                        "reason": "sample_timing_status_not_ok",
                        "path": str(path),
                        "line_no": line_no,
                        "status": row.get("status"),
                    }
                )
                continue
            tokens = _parse_int(row.get("requested_output_tokens"))
            elapsed = _tpot({"generate_seconds_per_requested_output_token": row.get("generate_elapsed_us")})
            if tokens is None:
                invalid_rows.append(
                    {
                        "reason": "invalid_sample_timing_tokens",
                        "path": str(path),
                        "line_no": line_no,
                        "value": row.get("requested_output_tokens"),
                    }
                )
                continue
            if tokens <= 0:
                invalid_rows.append(
                    {
                        "reason": "nonpositive_sample_timing_tokens",
                        "path": str(path),
                        "line_no": line_no,
                        "value": tokens,
                    }
                )
                continue
            if elapsed is None:
                invalid_rows.append(
                    {
                        "reason": "invalid_sample_timing_elapsed_us",
                        "path": str(path),
                        "line_no": line_no,
                        "value": row.get("generate_elapsed_us"),
                    }
                )
                continue
            if elapsed <= 0:
                invalid_rows.append(
                    {
                        "reason": "nonpositive_sample_timing_elapsed_us",
                        "path": str(path),
                        "line_no": line_no,
                        "value": elapsed,
                    }
                )
                continue
            values.append((elapsed / 1_000_000.0) / float(tokens))
    return values, invalid_rows


def _summarize_tail_values(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"available": False, "count": 0}
    return {
        "available": True,
        "count": len(values),
        "p50": _quantile_nearest_rank(values, 0.50),
        "p95": _quantile_nearest_rank(values, 0.95),
        "p99": _quantile_nearest_rank(values, 0.99),
        "min": min(values),
        "max": max(values),
    }


def build_summary(
    rows: list[dict[str, Any]],
    *,
    baseline_mode: str,
    min_median_improvement_pct: float,
    min_repeats: int = 3,
    min_tail_samples: int = 30,
    require_parity: bool = False,
    parity_available: bool = False,
) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {}
    sample_timing_tpots: dict[str, list[float]] = {}
    returncodes: dict[str, list[int | None]] = {}
    excluded_failed_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    context_fields = (
        "sample_count",
        "requested_output_token_count",
    )
    context_values: dict[str, set[Any]] = {field: set() for field in context_fields}
    for row in rows:
        mode_value = row.get("mode")
        if not isinstance(mode_value, str) or not mode_value.strip():
            invalid_rows.append(
                {
                    "reason": "invalid_mode",
                    "mode": mode_value,
                    "repeat": row.get("repeat"),
                    "returncode": row.get("returncode"),
                }
            )
            continue
        mode = mode_value
        raw_code = row.get("returncode")
        if raw_code is None:
            invalid_rows.append(
                {
                    "reason": "missing_returncode",
                    "mode": mode,
                    "repeat": row.get("repeat"),
                    "returncode": None,
                }
            )
            continue
        code = _parse_returncode(raw_code)
        if code is None:
            invalid_rows.append(
                {
                    "reason": "invalid_returncode",
                    "mode": mode,
                    "repeat": row.get("repeat"),
                    "returncode": raw_code,
                }
            )
            continue
        if code is not None and code != 0:
            excluded_failed_rows.append(
                {
                    "mode": mode,
                    "repeat": row.get("repeat"),
                    "returncode": code,
                }
            )
            continue
        value = _tpot(row)
        if value is None:
            invalid_rows.append(
                {
                    "reason": "missing_tpot",
                    "mode": mode,
                    "repeat": row.get("repeat"),
                    "returncode": code,
                }
            )
            continue

        parsed_context: dict[str, int] = {}
        invalid_context = False
        for field in context_fields:
            if field not in row or row.get(field) is None:
                invalid_rows.append(
                    {
                        "reason": "missing_context_field",
                        "mode": mode,
                        "repeat": row.get("repeat"),
                        "field": field,
                    }
                )
                invalid_context = True
                break
            parsed_value = _parse_int(row.get(field))
            if parsed_value is None:
                invalid_rows.append(
                    {
                        "reason": "invalid_context_value",
                        "mode": mode,
                        "repeat": row.get("repeat"),
                        "field": field,
                        "value": row.get(field),
                    }
                )
                invalid_context = True
                break
            parsed_context[field] = parsed_value
        if invalid_context:
            continue

        grouped.setdefault(mode, []).append(value)
        timing_values, timing_invalid_rows = _load_sample_timing_tpots(
            row.get("trace_dir")
        )
        sample_timing_tpots.setdefault(mode, []).extend(timing_values)
        invalid_rows.extend(timing_invalid_rows)
        returncodes.setdefault(mode, []).append(code)
        for field in context_fields:
            context_values[field].add(parsed_context[field])

    if baseline_mode not in grouped:
        raise ValueError(f"Baseline mode {baseline_mode!r} not found")

    modes = {mode: _summarize_values(values) for mode, values in sorted(grouped.items())}
    for mode, codes in returncodes.items():
        modes[mode]["returncodes"] = codes
    for mode in modes:
        modes[mode]["sample_timing_tpot"] = _summarize_tail_values(
            sample_timing_tpots.get(mode, [])
        )

    baseline = modes[baseline_mode]
    baseline_median = float(baseline["median"])
    baseline_mean = float(baseline["mean"])
    context_summary = {
        field: sorted(values)
        for field, values in context_values.items()
        if values
    }
    context_consistent = all(len(values) <= 1 for values in context_summary.values())

    comparisons: dict[str, dict[str, Any]] = {}
    for mode, stats in modes.items():
        if mode == baseline_mode:
            continue
        median = float(stats["median"])
        mean = float(stats["mean"])
        median_delta_pct = (median / baseline_median - 1.0) * 100.0
        mean_delta_pct = (mean / baseline_mean - 1.0) * 100.0
        baseline_count = int(baseline["count"])
        candidate_count = int(stats["count"])
        repeat_count_gate_pass = (
            baseline_count >= int(min_repeats)
            and candidate_count >= int(min_repeats)
        )
        tail_available = (
            bool(baseline["sample_timing_tpot"]["available"])
            and bool(stats["sample_timing_tpot"]["available"])
        )
        tail_count_gate_pass = False
        tail_gate_pass = None
        p95_delta_pct = None
        p99_delta_pct = None
        if tail_available:
            baseline_tail = baseline["sample_timing_tpot"]
            candidate_tail = stats["sample_timing_tpot"]
            tail_count_gate_pass = (
                int(baseline_tail["count"]) >= int(min_tail_samples)
                and int(candidate_tail["count"]) >= int(min_tail_samples)
            )
            p95_delta_pct = (
                float(candidate_tail["p95"]) / float(baseline_tail["p95"]) - 1.0
            ) * 100.0
            p99_delta_pct = (
                float(candidate_tail["p99"]) / float(baseline_tail["p99"]) - 1.0
            ) * 100.0
            tail_gate_pass = p95_delta_pct <= 0.0 and p99_delta_pct <= 0.0
        median_gate_pass = median_delta_pct <= -float(min_median_improvement_pct)
        if not context_consistent:
            final_gate_reason = "context_inconsistent"
        elif not repeat_count_gate_pass:
            final_gate_reason = "insufficient_repeats"
        elif not median_gate_pass:
            final_gate_reason = "median_not_improved"
        elif not tail_available:
            final_gate_reason = "missing_sample_timing"
        elif not tail_count_gate_pass:
            final_gate_reason = "insufficient_tail_samples"
        elif not bool(tail_gate_pass):
            final_gate_reason = "tail_latency_regression"
        elif bool(require_parity) and not bool(parity_available):
            final_gate_reason = "parity_not_available"
        else:
            final_gate_reason = "passed"
        final_gate_pass = final_gate_reason == "passed"
        comparisons[mode] = {
            "baseline_mode": baseline_mode,
            "baseline_repeat_count": baseline_count,
            "candidate_repeat_count": candidate_count,
            "min_repeats": int(min_repeats),
            "repeat_count_gate_pass": repeat_count_gate_pass,
            "median_delta_pct": median_delta_pct,
            "mean_delta_pct": mean_delta_pct,
            "median_improvement_pct": -median_delta_pct,
            "mean_improvement_pct": -mean_delta_pct,
            "median_gate_pass": median_gate_pass,
            "context_consistent": context_consistent,
            "tail_latency_available": tail_available,
            "min_tail_samples": int(min_tail_samples),
            "tail_count_gate_pass": tail_count_gate_pass,
            "tail_latency_gate_pass": tail_gate_pass,
            "p95_delta_pct": p95_delta_pct,
            "p99_delta_pct": p99_delta_pct,
            "require_parity": bool(require_parity),
            "parity_available": bool(parity_available),
            "final_gate_pass": final_gate_pass,
            "final_gate_reason": final_gate_reason,
        }

    return {
        "baseline_mode": baseline_mode,
        "min_median_improvement_pct": float(min_median_improvement_pct),
        "min_repeats": int(min_repeats),
        "min_tail_samples": int(min_tail_samples),
        "require_parity": bool(require_parity),
        "parity_available": bool(parity_available),
        "modes": modes,
        "comparisons": comparisons,
        "excluded_failed_rows": excluded_failed_rows,
        "invalid_rows": invalid_rows,
        "context_values": context_summary,
        "context_consistent": context_consistent,
        "tail_latency_available": any(
            bool(stats["sample_timing_tpot"]["available"])
            for stats in modes.values()
        ),
        "tail_latency_note": (
            "sample_timing.jsonl is used when present; older artifacts without "
            "that file remain tail-latency unavailable"
        ),
    }


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Telemetry Ladder Repeat Summary",
        "",
        f"baseline_mode: `{summary['baseline_mode']}`",
        f"min_median_improvement_pct: `{summary['min_median_improvement_pct']}`",
        f"min_repeats: `{summary['min_repeats']}`",
        f"min_tail_samples: `{summary['min_tail_samples']}`",
        f"require_parity: `{str(bool(summary.get('require_parity', False))).lower()}`",
        f"parity_available: `{str(bool(summary.get('parity_available', False))).lower()}`",
        f"context_consistent: `{str(bool(summary['context_consistent'])).lower()}`",
        "",
        "## Modes",
        "",
        "| mode | count | median TPOT | mean TPOT | min | max | stdev | sample_timing_count | sample_p50 | sample_p95 | sample_p99 | values |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for mode, stats in summary["modes"].items():
        values = ", ".join(f"{float(v):.6f}" for v in stats["values"])
        tail = stats["sample_timing_tpot"]
        lines.append(
            "| {mode} | {count} | {median:.6f} | {mean:.6f} | {min:.6f} | "
            "{max:.6f} | {stdev:.6f} | {tail_count} | {tail_p50} | "
            "{tail_p95} | {tail_p99} | {values} |".format(
                mode=mode,
                count=int(stats["count"]),
                median=float(stats["median"]),
                mean=float(stats["mean"]),
                min=float(stats["min"]),
                max=float(stats["max"]),
                stdev=float(stats["stdev"]),
                tail_count=int(tail["count"]),
                tail_p50=(
                    f"{float(tail['p50']):.6f}" if tail.get("available") else "n/a"
                ),
                tail_p95=(
                    f"{float(tail['p95']):.6f}" if tail.get("available") else "n/a"
                ),
                tail_p99=(
                    f"{float(tail['p99']):.6f}" if tail.get("available") else "n/a"
                ),
                values=values,
            )
        )

    lines.extend(
        [
            "",
            "## Comparisons",
            "",
            "| mode | median_delta_vs_baseline | mean_delta_vs_baseline | p95_delta | p99_delta | median_gate_pass | tail_count_gate_pass | tail_gate_pass | final_gate_pass | reason |",
            "|---|---:|---:|---:|---:|---|---|---|---|---|",
        ]
    )
    for mode, comp in summary["comparisons"].items():
        lines.append(
            "| {mode} | {median_delta} | {mean_delta} | {p95_delta} | {p99_delta} | {median_gate} | {tail_count_gate} | {tail_gate} | {final_gate} | {reason} |".format(
                mode=mode,
                median_delta=_format_pct(float(comp["median_delta_pct"])),
                mean_delta=_format_pct(float(comp["mean_delta_pct"])),
                p95_delta=_format_pct(
                    float(comp["p95_delta_pct"])
                    if comp["p95_delta_pct"] is not None
                    else None
                ),
                p99_delta=_format_pct(
                    float(comp["p99_delta_pct"])
                    if comp["p99_delta_pct"] is not None
                    else None
                ),
                median_gate=str(bool(comp["median_gate_pass"])).lower(),
                tail_count_gate=str(bool(comp["tail_count_gate_pass"])).lower(),
                tail_gate=(
                    "n/a"
                    if comp["tail_latency_gate_pass"] is None
                    else str(bool(comp["tail_latency_gate_pass"])).lower()
                ),
                final_gate=str(bool(comp["final_gate_pass"])).lower(),
                reason=comp["final_gate_reason"],
            )
        )

    lines.extend(
        [
            "",
            "## Context",
            "",
            "```json",
            json.dumps(summary["context_values"], indent=2),
            "```",
            "",
            "## Excluded Failed Rows",
            "",
            "```json",
            json.dumps(summary["excluded_failed_rows"], indent=2),
            "```",
            "",
            "## Invalid Rows",
            "",
            "```json",
            json.dumps(summary["invalid_rows"], indent=2),
            "```",
            "",
            "## Tail Latency",
            "",
            str(summary["tail_latency_note"]),
            "",
        ]
    )
    path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_json", type=Path)
    parser.add_argument("--baseline-mode", default="production_like")
    parser.add_argument("--min-median-improvement-pct", type=float, default=1.0)
    parser.add_argument("--min-repeats", type=int, default=3)
    parser.add_argument("--min-tail-samples", type=int, default=30)
    parser.add_argument(
        "--require-parity",
        action="store_true",
        help=(
            "Require external output/logit parity evidence before final_gate_pass "
            "can become true. The helper does not infer parity from timing rows."
        ),
    )
    parser.add_argument(
        "--parity-available",
        action="store_true",
        help="Mark external parity evidence as available for this summary.",
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    summary = build_summary(
        _load_rows(args.results_json),
        baseline_mode=args.baseline_mode,
        min_median_improvement_pct=args.min_median_improvement_pct,
        min_repeats=args.min_repeats,
        min_tail_samples=args.min_tail_samples,
        require_parity=args.require_parity,
        parity_available=args.parity_available,
    )

    text = json.dumps(summary, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text)
    else:
        print(text, end="")

    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, args.output_md)


if __name__ == "__main__":
    main()
