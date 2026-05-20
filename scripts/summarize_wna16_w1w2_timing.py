#!/usr/bin/env python3
"""Summarize WNA16 W1/W2 timing rows from a sweep output directory."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def _quantiles(values: list[float]) -> dict[str, float]:
    values = sorted(values)
    if not values:
        return {}

    def q(p: float) -> float:
        return values[min(len(values) - 1, int(round((len(values) - 1) * p)))]

    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "p50": q(0.50),
        "p95": q(0.95),
        "p99": q(0.99),
        "max": values[-1],
    }


def _read_timing(path: Path, bucket: str) -> dict[str, float]:
    host_values: list[float] = []
    gpu_values: list[float] = []
    override_values: list[float] = []
    if not path.exists():
        return {}
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("event_type") != "wna16_kernel_timing":
                continue
            if str(row.get("wna16_bucket")) != bucket:
                continue
            host = row.get("wna16_kernel_elapsed_us")
            gpu = row.get("wna16_kernel_gpu_elapsed_us")
            if host is not None:
                host_values.append(float(host))
            if gpu is not None:
                gpu_values.append(float(gpu))
                if row.get("wna16_config_override_applied"):
                    override_values.append(float(gpu))
    stats = {
        f"{bucket}_host": _quantiles(host_values),
        f"{bucket}_gpu": _quantiles(gpu_values),
        f"{bucket}_override_gpu": _quantiles(override_values),
    }
    return stats


def _load_perf(trace_dir: Path) -> dict[str, Any]:
    path = trace_dir / "performance_summary.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {
        "tpot": data.get("generate_seconds_per_requested_output_token"),
        "generate_wall_seconds": data.get("generate_wall_seconds"),
        "sample_count": data.get("sample_count"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sweep_root", type=Path)
    parser.add_argument("--bucket", choices=("w1", "w2"), default="w1")
    parser.add_argument("--min-p50-speedup", type=float, default=1.03)
    parser.add_argument("--max-p95-regression", type=float, default=1.0)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    bucket_dir = args.sweep_root / args.bucket
    results_path = bucket_dir / "results.json"
    if not results_path.exists():
        raise SystemExit(f"missing results: {results_path}")
    rows = json.loads(results_path.read_text())
    out: list[dict[str, Any]] = []
    baseline_gpu = None
    for row in rows:
        candidate = str(row.get("candidate"))
        trace_dir = bucket_dir / "traces" / candidate
        timing = _read_timing(trace_dir / "runtime_shadow.jsonl", args.bucket)
        perf = _load_perf(trace_dir)
        gpu = timing.get(f"{args.bucket}_gpu", {})
        if candidate == "baseline_no_tuned_config":
            baseline_gpu = gpu
        record = {
            "candidate": candidate,
            "bucket": args.bucket,
            "returncode": row.get("returncode"),
            **perf,
            **timing,
        }
        out.append(record)

    base_p50 = (baseline_gpu or {}).get("p50")
    base_p95 = (baseline_gpu or {}).get("p95")
    if not base_p50 or not base_p95:
        raise SystemExit(
            f"missing baseline GPU-event timing rows for bucket {args.bucket}; "
            "rerun with --emit-kernel-timing --kernel-timing-mode gpu_event"
        )
    for record in out:
        gpu = record.get(f"{args.bucket}_gpu", {})
        override_gpu = record.get(f"{args.bucket}_override_gpu", {})
        p50 = gpu.get("p50")
        p95 = gpu.get("p95")
        if base_p50 and p50:
            record["gpu_p50_speedup_vs_baseline"] = float(base_p50) / float(p50)
        if base_p95 and p95:
            record["gpu_p95_speedup_vs_baseline"] = float(base_p95) / float(p95)
        record["gpu_row_count"] = int(gpu.get("count") or 0)
        record["override_gpu_row_count"] = int(override_gpu.get("count") or 0)
        p50_speedup = record.get("gpu_p50_speedup_vs_baseline")
        p95_speedup = record.get("gpu_p95_speedup_vs_baseline")
        record["survivor"] = bool(
            record["candidate"] != "baseline_no_tuned_config"
            and int(record.get("gpu_row_count") or 0) > 0
            and int(record.get("override_gpu_row_count") or 0) > 0
            and int(record.get("override_gpu_row_count") or 0)
            == int(record.get("gpu_row_count") or -1)
            and p50_speedup is not None
            and p95_speedup is not None
            and float(p50_speedup) >= float(args.min_p50_speedup)
            and float(p95_speedup) >= float(args.max_p95_regression)
            and int(record.get("returncode") or 0) == 0
        )

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(out, indent=2) + "\n")
    lines = [
        f"# WNA16 {args.bucket.upper()} Timing Summary",
        "",
        f"sweep_root: `{args.sweep_root}`",
        f"survivor_rule: p50_speedup >= `{args.min_p50_speedup}`, p95_speedup >= `{args.max_p95_regression}`",
        "",
        "| candidate | GPU rows | override rows | GPU p50 | GPU p95 | p50 speedup | p95 speedup | TPOT | survivor |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in out:
        gpu = record.get(f"{args.bucket}_gpu", {})
        lines.append(
            "| {candidate} | {rows} | {override_rows} | {p50} | {p95} | {s50} | {s95} | {tpot} | {survivor} |".format(
                candidate=record["candidate"],
                rows=int(record.get("gpu_row_count") or 0),
                override_rows=int(record.get("override_gpu_row_count") or 0),
                p50=f"{float(gpu['p50']):.3f}" if gpu.get("p50") is not None else "",
                p95=f"{float(gpu['p95']):.3f}" if gpu.get("p95") is not None else "",
                s50=(
                    f"{float(record['gpu_p50_speedup_vs_baseline']):.4f}x"
                    if record.get("gpu_p50_speedup_vs_baseline") is not None
                    else ""
                ),
                s95=(
                    f"{float(record['gpu_p95_speedup_vs_baseline']):.4f}x"
                    if record.get("gpu_p95_speedup_vs_baseline") is not None
                    else ""
                ),
                tpot=f"{float(record['tpot']):.6f}" if record.get("tpot") else "",
                survivor="yes" if record.get("survivor") else "no",
            )
        )
    md_path = args.sweep_root / f"{args.bucket}_timing_summary.md"
    md_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
