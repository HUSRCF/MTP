#!/usr/bin/env python3
"""Run rocprofv3 positive-control kernels for counter validation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from run_rocwmma_rocprof_classification import (
    as_float,
    collect_discovery,
    extract_metrics,
    load_csv_rows,
    metric_completeness,
    parse_program_json,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "microbench" / "rocwmma_smoke" / "rocprof_positive_controls.hip"
BUILD_DIR = REPO_ROOT / "microbench" / "rocwmma_smoke" / "build"
BIN = BUILD_DIR / "rocprof_positive_controls"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "reports" / "rocwmma_smoke" / "rocprof_positive_controls"
DEFAULT_MODES = ["global_load", "lds_heavy"]
DEFAULT_METRICS = ["SQ_WAVES", "SQ_INSTS_LDS", "SQ_INSTS_TEX_LOAD", "FETCH_SIZE"]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build(*, force: bool = False, offload_arch: str = "gfx1100") -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if BIN.exists() and not force and BIN.stat().st_mtime >= SRC.stat().st_mtime:
        return
    run(["hipcc", "-O3", "--std=c++17", f"--offload-arch={offload_arch}", str(SRC), "-o", str(BIN)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--mode", action="append", choices=DEFAULT_MODES, default=None)
    parser.add_argument("--metric", action="append", default=None)
    parser.add_argument("--blocks", type=int, default=256)
    parser.add_argument("--threads", type=int, default=256)
    parser.add_argument("--elems", type=int, default=1 << 22)
    parser.add_argument("--inner-iters", type=int, default=64)
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


def binary_command(args: argparse.Namespace, *, device: int, mode: str) -> list[str]:
    return [
        str(BIN),
        "--device",
        str(device),
        "--mode",
        mode,
        "--blocks",
        str(args.blocks),
        "--threads",
        str(args.threads),
        "--elems",
        str(args.elems),
        "--inner-iters",
        str(args.inner_iters),
        "--warmup",
        str(args.warmup),
        "--iters",
        str(args.iters),
    ]


def profile_command(args: argparse.Namespace, *, device: int, mode: str, metric: str, out_prefix: Path) -> list[str]:
    kernel_regex = "global_load_heavy_kernel" if mode == "global_load" else "lds_heavy_kernel"
    cmd = [
        "rocprofv3",
        "--pmc",
        metric,
        "--kernel-include-regex",
        kernel_regex,
        "--output-format",
        "csv",
        "-d",
        str(out_prefix.parent / f"{out_prefix.name}_{metric}_data"),
        "-o",
        f"{out_prefix.name}_{metric}",
        "--",
        *binary_command(args, device=device, mode=mode),
    ]
    if args.agent_index is not None:
        cmd[1:1] = ["--agent-index", args.agent_index]
    return cmd


def counter_csv(out_prefix: Path, metric: str) -> Path:
    return out_prefix.parent / f"{out_prefix.name}_{metric}_data" / f"{out_prefix.name}_{metric}_counter_collection.csv"


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# rocprofv3 Positive Controls",
        "",
        "These kernels validate whether the local profiler path can observe obvious",
        "global-load-heavy and LDS-heavy traffic before using counters to classify rocWMMA.",
        "",
        "## Results",
        "",
        "| device | mode | wall ms | available | nonzero | informative | nonzero metrics |",
        "|---:|---|---:|---:|---:|---|---|",
    ]
    for row in report["results"]:
        comp = row["metric_completeness"]
        lines.append(
            "| {device} | {mode} | {wall} | {available} | {nonzero} | {informative} | {metrics} |".format(
                device=row["device"],
                mode=row["mode"],
                wall=_fmt(row["program"].get("wall_ms_mean") if row["program"] else None),
                available=comp["available_count"],
                nonzero=comp["nonzero_count"],
                informative=comp["counter_values_are_informative"],
                metrics=", ".join(comp["nonzero_metrics"]) or "none",
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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    build(force=args.force_build, offload_arch=args.offload_arch)

    commands: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for device in devices:
        for mode in modes:
            rows = []
            stdout = ""
            stderr = ""
            csv_files = []
            returncode = 0
            error = None
            out_prefix = args.output_dir / f"gpu{device}_{mode}"
            for metric in metrics:
                cmd = profile_command(args, device=device, mode=mode, metric=metric, out_prefix=out_prefix)
                commands.append({"device": device, "mode": mode, "metric": metric, "cmd": cmd})
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
                path = counter_csv(out_prefix, metric)
                csv_files.append(str(path))
                rows.extend(load_csv_rows(path))
            if args.dry_run:
                continue
            parsed_metrics = extract_metrics(rows, metrics)
            results.append(
                {
                    "device": device,
                    "mode": mode,
                    "returncode": returncode,
                    "error": error,
                    "program": parse_program_json(stdout),
                    "stderr_tail": stderr[-4000:] if stderr else "",
                    "csv_files": csv_files,
                    "metrics": parsed_metrics,
                    "metric_completeness": metric_completeness(parsed_metrics),
                }
            )

    report = {
        "ok": args.dry_run or all(row["returncode"] == 0 for row in results),
        "tool": "rocprofv3",
        "config": {
            "devices": devices,
            "modes": modes,
            "metrics": metrics,
            "blocks": args.blocks,
            "threads": args.threads,
            "elems": args.elems,
            "inner_iters": args.inner_iters,
            "warmup": args.warmup,
            "iters": args.iters,
            "binary": str(BIN),
            "source": str(SRC),
            "dry_run": args.dry_run,
            "discovery_enabled": not args.skip_discovery,
            "agent_index": args.agent_index,
        },
        "discovery": collect_discovery(devices=devices, metrics=metrics, skip=args.skip_discovery),
        "commands": commands,
        "results": results,
    }
    json_path = args.output_dir / "rocprof_positive_controls.json"
    md_path = args.output_dir / "rocprof_positive_controls.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
