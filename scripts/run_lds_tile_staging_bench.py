#!/usr/bin/env python3
"""Build and run the speculative LDS tile-staging HIP microbench."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = REPO_ROOT / "microbench" / "lds_tile_staging"
SRC = BENCH_DIR / "lds_tile_staging_bench.hip"
BUILD_DIR = BENCH_DIR / "build"
BIN = BUILD_DIR / "lds_tile_staging_bench"


DEFAULT_MODES = ["reactive", "oracle", "spec_hit", "spec_miss", "mixed"]
CONTROL_MODES = ["dummy_lds_store", "wrong_no_consume", "global_no_lds"]
ALL_MODES = DEFAULT_MODES + CONTROL_MODES


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build(force: bool = False) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if BIN.exists() and not force and BIN.stat().st_mtime >= SRC.stat().st_mtime:
        return
    cmd = [
        "hipcc",
        "-O3",
        "--std=c++17",
        str(SRC),
        "-o",
        str(BIN),
    ]
    result = run(cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")


def bench_one(args: argparse.Namespace, mode: str) -> dict[str, Any]:
    cmd = [
        str(BIN),
        "--mode",
        mode,
        "--device",
        str(args.device),
        "--requests",
        str(args.requests),
        "--experts",
        str(args.experts),
        "--tile-elems",
        str(args.tile_elems),
        "--block-threads",
        str(args.block_threads),
        "--warmup",
        str(args.warmup),
        "--iters",
        str(args.iters),
        "--validate-iters",
        str(args.validate_iters),
        "--metadata-tokens",
        str(args.metadata_tokens),
        "--compute-iters",
        str(args.compute_iters),
        "--interference-iters",
        str(args.interference_iters),
        "--interference-elems",
        str(args.interference_elems),
        "--miss-rate",
        str(args.miss_rate),
        "--seed",
        str(args.seed),
    ]
    env = os.environ.copy()
    if args.hip_visible_devices is not None:
        env["HIP_VISIBLE_DEVICES"] = args.hip_visible_devices
    result = run(cmd, env=env)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"benchmark did not emit JSON for mode={mode}:\n{result.stdout}") from exc
    if result.stderr:
        payload["stderr"] = result.stderr
    return payload


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode = {r["mode"]: r for r in results}
    reactive = by_mode.get("reactive")
    summary: dict[str, Any] = {
        "results": results,
        "derived": {},
    }
    if reactive:
        reactive_first = float(reactive["first_fma_cycles_p50"])
        reactive_wall = float(reactive["wall_ms_mean"])
        reactive_wait = float(reactive.get("metadata_wait_cycles_p50", 0.0))
        reactive_load = float(reactive.get("overwrite_cycles_p50_all", 0.0))
        reactive_overlap_model = reactive_wait + reactive_load
        for mode, row in by_mode.items():
            first = float(row["first_fma_cycles_p50"])
            wall = float(row["wall_ms_mean"])
            stage = float(row.get("stage_cycles_p50", 0.0))
            wait = float(row.get("metadata_wait_cycles_p50", 0.0))
            miss_fraction = float(row.get("observed_miss_fraction", 0.0))
            miss_overwrite = float(row.get("overwrite_cycles_p50_miss", 0.0))
            if mode == "reactive":
                overlap_model = reactive_overlap_model
            else:
                overlap_model = max(stage, wait) + miss_fraction * miss_overwrite
            summary["derived"][mode] = {
                "first_fma_cycles_delta_vs_reactive": first - reactive_first,
                "first_fma_cycles_speedup_vs_reactive": (
                    reactive_first / first if first > 0 else None
                ),
                "wall_ms_delta_vs_reactive": wall - reactive_wall,
                "wall_ms_speedup_vs_reactive": reactive_wall / wall if wall > 0 else None,
                "overlap_model_cycles_p50": overlap_model,
                "overlap_model_delta_vs_reactive": overlap_model - reactive_overlap_model,
                "overlap_model_speedup_vs_reactive": (
                    reactive_overlap_model / overlap_model if overlap_model > 0 else None
                ),
            }
        if "spec_hit" in by_mode and "spec_miss" in by_mode:
            hit_t = float(summary["derived"]["spec_hit"]["overlap_model_cycles_p50"])
            miss_t = float(summary["derived"]["spec_miss"]["overlap_model_cycles_p50"])
            base_t = float(summary["derived"]["reactive"]["overlap_model_cycles_p50"])
            denom = miss_t - hit_t
            if denom > 0.0:
                p_min = (miss_t - base_t) / denom
            else:
                p_min = None
            summary["break_even"] = {
                "base_cycles": base_t,
                "hit_cycles": hit_t,
                "miss_cycles": miss_t,
                "p_min_hit_rate": p_min,
                "profitable_for_any_positive_hit_rate": miss_t < base_t,
                "hit_better_than_base": hit_t < base_t,
                "miss_better_than_base": miss_t < base_t,
            }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=ALL_MODES + ["all", "controls"], default="all")
    parser.add_argument(
        "--include-controls",
        action="store_true",
        help="Include anti-artifact control modes when --mode=all.",
    )
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument(
        "--hip-visible-devices",
        default=None,
        help="Optional HIP_VISIBLE_DEVICES override. Useful for pinning physical GPU selection.",
    )
    parser.add_argument("--requests", type=int, default=4096)
    parser.add_argument("--experts", type=int, default=256)
    parser.add_argument("--tile-elems", type=int, default=1024)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--validate-iters", type=int, default=256)
    parser.add_argument(
        "--metadata-tokens",
        type=int,
        default=0,
        help="Synthetic same-kernel router/metadata tokens per request. 0 keeps spin-only wait.",
    )
    parser.add_argument(
        "--compute-iters",
        type=int,
        default=1,
        help="Number of FMA passes over the staged tile; >1 is a grouped-GEMM compute mock.",
    )
    parser.add_argument("--interference-iters", type=int, default=0)
    parser.add_argument("--interference-elems", type=int, default=1 << 20)
    parser.add_argument("--miss-rate", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "lds_tile_staging" / "smoke.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(force=args.force_build)
    if args.mode == "all":
        modes = ALL_MODES if args.include_controls else DEFAULT_MODES
    elif args.mode == "controls":
        modes = CONTROL_MODES
    else:
        modes = [args.mode]
    results = [bench_one(args, mode) for mode in modes]
    payload = summarize(results)
    payload["config"] = {
        "device": args.device,
        "hip_visible_devices": args.hip_visible_devices,
        "requests": args.requests,
        "experts": args.experts,
        "tile_elems": args.tile_elems,
        "block_threads": args.block_threads,
        "warmup": args.warmup,
        "iters": args.iters,
        "validate_iters": args.validate_iters,
        "metadata_tokens": args.metadata_tokens,
        "compute_iters": args.compute_iters,
        "interference_iters": args.interference_iters,
        "interference_elems": args.interference_elems,
        "miss_rate": args.miss_rate,
        "seed": args.seed,
        "binary": str(BIN),
        "source": str(SRC),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
