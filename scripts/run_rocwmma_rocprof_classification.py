#!/usr/bin/env python3
"""Profile rocWMMA tile-stage modes and classify B-tile reload pressure.

This harness intentionally uses legacy ``rocprof`` rather than
``rocprof-compute`` because the latter may not be installed with its Python UI
dependencies on the local W7900 nodes.  The goal is not to prove speedup from a
single counter run; it is to collect enough raw counter evidence to decide
whether the target path is fragment-reuse-like or reload-per-row-like.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import run_rocwmma_tile_stage as tile_stage


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "reports" / "rocwmma_smoke" / "rocprof_classification"
DEFAULT_MODES = ["global_frag_reuse", "global_reload_per_row", "lds_hit", "lds_miss_overwrite"]
DEFAULT_METRICS = [
    "FETCH_SIZE",
    "L2CacheHit",
    "Wavefronts",
    "VALUInsts",
    "LDSBankConflict",
    "OccupancyPercent",
]
DEFAULT_METRIC_GROUPS = [
    # Legacy rocprof cannot collect all derived metrics in one HW pass on
    # gfx1100.  This grouping follows the split suggested by rocprof when the
    # full list exceeds HW limits.
    ["FETCH_SIZE", "VALUInsts", "LDSBankConflict", "OccupancyPercent", "Wavefronts"],
    ["L2CacheHit"],
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_optional(cmd: list[str]) -> dict[str, Any]:
    try:
        completed = run(cmd)
        return {
            "cmd": cmd,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "error": None,
        }
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return {
            "cmd": cmd,
            "returncode": getattr(exc, "returncode", None),
            "stdout": getattr(exc, "stdout", "") or "",
            "stderr": getattr(exc, "stderr", "") or "",
            "error": str(exc),
        }


def collect_discovery(*, devices: list[int], metrics: list[str], skip: bool) -> dict[str, Any]:
    env_keys = [
        "HIP_VISIBLE_DEVICES",
        "ROCR_VISIBLE_DEVICES",
        "CUDA_VISIBLE_DEVICES",
        "HSA_VISIBLE_DEVICES",
    ]
    discovery: dict[str, Any] = {
        "env": {key: os.environ.get(key) for key in env_keys if os.environ.get(key) is not None},
        "skipped": skip,
    }
    if skip:
        return discovery
    discovery["agents"] = run_optional(["rocprofv3-avail", "list", "--agent"])
    discovery["devices"] = {}
    for device in devices:
        discovery["devices"][str(device)] = {
            "pmc_list": run_optional(["rocprofv3-avail", "-d", str(device), "list", "--pmc"]),
            "pmc_check": run_optional(["rocprofv3-avail", "-d", str(device), "pmc-check", *metrics]),
        }
    return discovery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiler", choices=["rocprof", "rocprofv3"], default="rocprofv3")
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--mode", action="append", default=None, choices=DEFAULT_MODES)
    parser.add_argument("--metric", action="append", default=None)
    parser.add_argument("--consumer-rows", type=int, default=16)
    parser.add_argument("--validate-iters", type=int, default=0)
    parser.add_argument("--num-cta", type=int, default=256)
    parser.add_argument("--b-pool-tiles", type=int, default=1024)
    parser.add_argument("--tile-stride", type=int, default=17)
    parser.add_argument("--cache-flush-elems", type=int, default=1_048_576)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--iters", type=int, default=1)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-discovery", action="store_true")
    parser.add_argument(
        "--agent-index",
        choices=["absolute", "relative", "type-relative"],
        default=None,
        help="Optional rocprofv3 -A/--agent-index mode for agent-index A/B checks.",
    )
    return parser.parse_args()


def metric_groups(metrics: list[str], *, use_default_grouping: bool) -> list[list[str]]:
    if use_default_grouping and metrics == DEFAULT_METRICS:
        return DEFAULT_METRIC_GROUPS
    # Custom metric lists are safer as one metric per pass because legacy
    # rocprof aborts when a derived metric expands past the per-block limits.
    return [[metric] for metric in metrics]


def write_rocprof_input(path: Path, *, groups: list[list[str]], device: int) -> None:
    lines = ["# Generated by scripts/run_rocwmma_rocprof_classification.py"]
    for group in groups:
        lines.append("pmc : " + " ".join(group))
    lines.extend([f"gpu: {device}", "kernel: rocwmma_tile_stage_kernel", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def binary_command(args: argparse.Namespace, *, device: int, mode: str) -> list[str]:
    return [
        str(tile_stage.BIN),
        "--device",
        str(device),
        "--mode",
        mode,
        "--consumer-rows",
        str(args.consumer_rows),
        "--validate-iters",
        str(args.validate_iters),
        "--num-cta",
        str(args.num_cta),
        "--b-pool-tiles",
        str(args.b_pool_tiles),
        "--tile-stride",
        str(args.tile_stride),
        "--cache-flush-elems",
        str(args.cache_flush_elems),
        "--warmup",
        str(args.warmup),
        "--iters",
        str(args.iters),
    ]


def profile_command(
    args: argparse.Namespace,
    *,
    input_file: Path,
    csv_file: Path,
    mode: str,
    device: int,
    metrics_for_run: list[str],
) -> list[str]:
    if args.profiler == "rocprofv3":
        cmd = [
            "rocprofv3",
            "--pmc",
            *metrics_for_run,
            "--kernel-include-regex",
            "rocwmma_tile_stage_kernel",
            "--output-format",
            "csv",
            "-d",
            str(csv_file.parent / f"{csv_file.stem}_data"),
            "-o",
            csv_file.stem,
            "--",
            *binary_command(args, device=device, mode=mode),
        ]
        if args.agent_index is not None:
            cmd[1:1] = ["--agent-index", args.agent_index]
        return cmd
    return [
        "rocprof",
        "--basenames",
        "on",
        "--stats",
        "-i",
        str(input_file),
        "-o",
        str(csv_file),
        "-d",
        str(csv_file.parent / f"{csv_file.stem}_data"),
        *binary_command(args, device=device, mode=mode),
    ]


def expected_counter_csv(args: argparse.Namespace, csv_file: Path) -> Path:
    if args.profiler == "rocprofv3":
        return csv_file.parent / f"{csv_file.stem}_data" / f"{csv_file.stem}_counter_collection.csv"
    return csv_file


def parse_program_json(stdout: str) -> dict[str, Any] | None:
    stdout = stdout.strip()
    if not stdout:
        return None
    if not stdout.startswith("{"):
        start = stdout.rfind("\n{")
        if start >= 0:
            stdout = stdout[start + 1 :]
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        value_f = float(text)
    except ValueError:
        return None
    if math.isnan(value_f) or math.isinf(value_f):
        return None
    return value_f


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        content = handle.read().splitlines()
    data_lines = [line for line in content if line.strip() and not line.lstrip().startswith("#")]
    if not data_lines:
        return []
    reader = csv.DictReader(data_lines)
    return [dict(row) for row in reader if row]


def fallback_result_rows(csv_file: Path) -> list[dict[str, str]]:
    # When rocprof is interrupted or the final CSV merge is unavailable, the
    # per-pass result files can still contain parseable counter output.  Keep
    # this narrow and best-effort; the raw files are preserved for inspection.
    rows: list[dict[str, str]] = []
    data_dir = csv_file.parent / f"{csv_file.stem}_data"
    if not data_dir.exists():
        return rows
    for path in sorted(data_dir.glob("rpl_data_*/input*_results_*/*results*.txt")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            if "rocwmma_tile_stage_kernel" not in line:
                continue
            # Some rocprof versions use CSV-like result lines here.
            if "," in line:
                parts = [part.strip() for part in line.split(",")]
                row: dict[str, str] = {"KernelName": line}
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        row[key.strip()] = value.strip()
                rows.append(row)
    return rows


def row_matches_kernel(row: dict[str, str]) -> bool:
    joined = " ".join(str(value) for value in row.values())
    return "rocwmma_tile_stage_kernel" in joined


def extract_metrics(rows: list[dict[str, str]], metrics: list[str]) -> dict[str, float | None]:
    selected = [row for row in rows if row_matches_kernel(row)] or rows
    out: dict[str, float | None] = {}
    for metric in metrics:
        values = []
        for row in selected:
            if row.get("Counter_Name") == metric:
                parsed = as_float(row.get("Counter_Value"))
                if parsed is not None:
                    values.append(parsed)
            elif metric in row:
                parsed = as_float(row.get(metric))
                if parsed is not None:
                    values.append(parsed)
        out[metric] = sum(values) if values else None
    return out


def metric_completeness(metrics: dict[str, float | None]) -> dict[str, Any]:
    available = {name: value for name, value in metrics.items() if value is not None}
    nonzero = {name: value for name, value in available.items() if abs(value) > 0.0}
    return {
        "available_count": len(available),
        "nonzero_count": len(nonzero),
        "available_metrics": sorted(available),
        "nonzero_metrics": sorted(nonzero),
        "counter_values_are_informative": len(nonzero) >= 2,
    }


def theoretical_min_b_bytes(*, num_cta: int, b_pool_tiles: int, tile_stride: int) -> int:
    used_tiles = {((block * tile_stride) % b_pool_tiles) for block in range(num_cta)}
    # One 16x16 fp16 B tile per distinct selected tile.
    return len(used_tiles) * 16 * 16 * 2


def estimated_reload_b_bytes(*, num_cta: int, consumer_rows: int) -> int:
    # Reload-per-row baseline loads one 16x16 fp16 B tile for each consumer row.
    return num_cta * consumer_rows * 16 * 16 * 2


def compute_derived(
    *,
    program: dict[str, Any] | None,
    metrics: dict[str, float | None],
    args: argparse.Namespace,
) -> dict[str, Any]:
    fetch_kb = metrics.get("FETCH_SIZE")
    measured_fetch_bytes = fetch_kb * 1024.0 if fetch_kb is not None else None
    min_b_bytes = theoretical_min_b_bytes(
        num_cta=args.num_cta,
        b_pool_tiles=args.b_pool_tiles,
        tile_stride=args.tile_stride,
    )
    reload_b_bytes = estimated_reload_b_bytes(num_cta=args.num_cta, consumer_rows=args.consumer_rows)
    b_reload_ratio_min = (
        measured_fetch_bytes / float(min_b_bytes) if measured_fetch_bytes is not None and min_b_bytes > 0 else None
    )
    b_reload_ratio_reload = (
        measured_fetch_bytes / float(reload_b_bytes)
        if measured_fetch_bytes is not None and reload_b_bytes > 0
        else None
    )
    return {
        "wall_ms_mean": program.get("wall_ms_mean") if program else None,
        "wall_us_per_output_tile": program.get("wall_us_per_output_tile") if program else None,
        "measured_fetch_bytes": measured_fetch_bytes,
        "theoretical_min_b_tile_bytes": min_b_bytes,
        "theoretical_reload_per_row_b_bytes": reload_b_bytes,
        "b_reload_ratio_vs_min_b": b_reload_ratio_min,
        "b_reload_ratio_vs_reload_b": b_reload_ratio_reload,
    }


def classify_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode = {str(row["mode"]): row for row in rows}
    frag = by_mode.get("global_frag_reuse")
    reload = by_mode.get("global_reload_per_row")
    classification: dict[str, Any] = {
        "note": "FETCH_SIZE includes all kernel memory traffic, not only B tiles; use ratios as classification proxies.",
        "has_frag_reuse": frag is not None,
        "has_reload_per_row": reload is not None,
    }
    if frag and reload:
        frag_fetch = frag["derived"].get("measured_fetch_bytes")
        reload_fetch = reload["derived"].get("measured_fetch_bytes")
        if frag_fetch is not None and reload_fetch is not None and frag_fetch > 0:
            classification["reload_fetch_over_frag_fetch"] = reload_fetch / frag_fetch
        frag_ratio = frag["derived"].get("b_reload_ratio_vs_min_b")
        reload_ratio = reload["derived"].get("b_reload_ratio_vs_min_b")
        if frag_ratio is not None and reload_ratio is not None:
            classification["frag_ratio_vs_min_b"] = frag_ratio
            classification["reload_ratio_vs_min_b"] = reload_ratio
            classification["ratio_gap_reload_minus_frag"] = reload_ratio - frag_ratio
    return classification


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# rocWMMA rocprof Classification",
        "",
        "This report classifies whether the rocWMMA tile-stage benchmark behaves closer to a",
        "`global_frag_reuse` path or a `global_reload_per_row` path.  `FETCH_SIZE` is a proxy",
        "for total fetched bytes and includes non-B traffic, so B reload ratios should be read",
        "as classification signals rather than exact B-only byte counts.",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(report["config"], indent=2, sort_keys=True),
        "```",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(report["summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Per-Mode Table",
        "",
        "| device | mode | wall ms | FETCH_SIZE KB | B reload ratio vs min | B ratio vs reload | LDS bank conflict | occupancy % | L2 hit % |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["results"]:
        metrics = row["metrics"]
        derived = row["derived"]
        lines.append(
            "| {device} | {mode} | {wall} | {fetch} | {ratio_min} | {ratio_reload} | {lds_conflict} | {occ} | {l2} |".format(
                device=row["device"],
                mode=row["mode"],
                wall=_fmt(derived.get("wall_ms_mean")),
                fetch=_fmt(metrics.get("FETCH_SIZE")),
                ratio_min=_fmt(derived.get("b_reload_ratio_vs_min_b")),
                ratio_reload=_fmt(derived.get("b_reload_ratio_vs_reload_b")),
                lds_conflict=_fmt(metrics.get("LDSBankConflict")),
                occ=_fmt(metrics.get("OccupancyPercent")),
                l2=_fmt(metrics.get("L2CacheHit")),
            )
        )
    lines.append("")
    lines.extend(
        [
            "## Counter Completeness",
            "",
            "| device | mode | available | nonzero | informative | nonzero metrics |",
            "|---:|---|---:|---:|---|---|",
        ]
    )
    for row in report["results"]:
        completeness = row.get("metric_completeness", {})
        lines.append(
            "| {device} | {mode} | {available} | {nonzero} | {informative} | {metrics} |".format(
                device=row["device"],
                mode=row["mode"],
                available=completeness.get("available_count", "n/a"),
                nonzero=completeness.get("nonzero_count", "n/a"),
                informative=completeness.get("counter_values_are_informative", "n/a"),
                metrics=", ".join(completeness.get("nonzero_metrics", [])) or "none",
            )
        )
    lines.append("")
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    parsed = as_float(value)
    if parsed is None:
        return "n/a"
    return f"{parsed:.4f}"


def main() -> None:
    args = parse_args()
    devices = sorted(set(args.device or [0]))
    modes = args.mode or DEFAULT_MODES
    metrics = args.metric or DEFAULT_METRICS
    groups = metric_groups(metrics, use_default_grouping=args.metric is None)
    run_groups = [[metric] for metric in metrics] if args.profiler == "rocprofv3" else [metrics]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tile_stage.build(force=args.force_build, offload_arch=args.offload_arch)

    results: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    for device in devices:
        input_file = args.output_dir / f"rocprof_input_gpu{device}.txt"
        write_rocprof_input(input_file, groups=groups, device=device)
        for mode in modes:
            stem = f"gpu{device}_{mode}_rows{args.consumer_rows}_cta{args.num_cta}"
            all_csv_rows: list[dict[str, str]] = []
            stdout = ""
            stderr = ""
            returncode = 0
            error = None
            run_csv_files: list[str] = []
            for group_idx, group in enumerate(run_groups):
                group_suffix = f"_g{group_idx}" if args.profiler == "rocprofv3" else ""
                requested_csv_file = args.output_dir / f"{stem}{group_suffix}.csv"
                cmd = profile_command(
                    args,
                    input_file=input_file,
                    csv_file=requested_csv_file,
                    mode=mode,
                    device=device,
                    metrics_for_run=group,
                )
                csv_file = expected_counter_csv(args, requested_csv_file)
                commands.append({"device": device, "mode": mode, "metrics": group, "cmd": cmd})
                if args.dry_run:
                    continue
                try:
                    completed = run(cmd)
                    stdout = stdout or completed.stdout
                    stderr += completed.stderr
                except subprocess.CalledProcessError as exc:
                    returncode = exc.returncode
                    stdout = stdout or (exc.stdout or "")
                    stderr += exc.stderr or ""
                    error = str(exc)
                    break
                run_csv_files.append(str(csv_file))
                csv_rows = load_csv_rows(csv_file)
                if not csv_rows:
                    csv_rows = fallback_result_rows(csv_file)
                all_csv_rows.extend(csv_rows)
            if args.dry_run:
                continue
            csv_rows = all_csv_rows
            parsed_metrics = extract_metrics(csv_rows, metrics)
            completeness = metric_completeness(parsed_metrics)
            program_json = parse_program_json(stdout)
            results.append(
                {
                    "device": device,
                    "mode": mode,
                    "returncode": returncode,
                    "error": error,
                    "stdout_json": program_json,
                    "stderr_tail": stderr[-4000:] if stderr else "",
                    "csv": run_csv_files[0] if run_csv_files else None,
                    "csv_files": run_csv_files,
                    "csv_rows": len(csv_rows),
                    "metrics": parsed_metrics,
                    "metric_completeness": completeness,
                    "derived": compute_derived(program=program_json, metrics=parsed_metrics, args=args),
                }
            )

    report = {
        "ok": (args.dry_run or all(row["returncode"] == 0 for row in results)),
        "tool": args.profiler,
        "rocprof_compute_available": False,
        "config": {
            "devices": devices,
            "modes": modes,
            "metrics": metrics,
            "metric_groups": groups,
            "consumer_rows": args.consumer_rows,
            "validate_iters": args.validate_iters,
            "num_cta": args.num_cta,
            "b_pool_tiles": args.b_pool_tiles,
            "tile_stride": args.tile_stride,
            "cache_flush_elems": args.cache_flush_elems,
            "warmup": args.warmup,
            "iters": args.iters,
            "binary": str(tile_stage.BIN),
            "source": str(tile_stage.SRC),
            "dry_run": args.dry_run,
            "profiler": args.profiler,
            "discovery_enabled": not args.skip_discovery,
            "agent_index": args.agent_index,
        },
        "discovery": collect_discovery(devices=devices, metrics=metrics, skip=args.skip_discovery),
        "commands": commands,
        "results": results,
        "summary": classify_rows(results) if results else {},
    }
    json_path = args.output_dir / "rocwmma_rocprof_classification.json"
    md_path = args.output_dir / "rocwmma_rocprof_classification.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
