#!/usr/bin/env python3
"""Build and run rocWMMA global-vs-LDS tile staging smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "microbench" / "rocwmma_smoke" / "rocwmma_tile_stage.hip"
BUILD_DIR = REPO_ROOT / "microbench" / "rocwmma_smoke" / "build"
BIN = BUILD_DIR / "rocwmma_tile_stage"
DEFAULT_MODES = ["global_frag_reuse", "global_reload_per_row", "lds_hit", "lds_miss_overwrite"]


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
    cmd = [
        "hipcc",
        "-O3",
        "--std=c++17",
        f"--offload-arch={offload_arch}",
        str(SRC),
        "-o",
        str(BIN),
    ]
    result = run(cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--mode", action="append", default=None, choices=DEFAULT_MODES)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--iters", type=int, default=200)
    parser.add_argument("--consumer-rows", type=int, action="append", default=None)
    parser.add_argument("--validate-iters", type=int, action="append", default=None)
    parser.add_argument("--num-cta", type=int, action="append", default=None)
    parser.add_argument("--b-pool-tiles", type=int, action="append", default=None)
    parser.add_argument("--tile-stride", type=int, action="append", default=None)
    parser.add_argument("--cache-flush-elems", type=int, action="append", default=None)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "rocwmma_smoke" / "rocwmma_tile_stage.json",
    )
    return parser.parse_args()


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_config: dict[tuple[int, int, int, int, int, int, int], dict[str, dict[str, Any]]] = {}
    for row in results:
        key = (
            int(row["device"]),
            int(row["consumer_rows"]),
            int(row["validate_iters"]),
            int(row["num_cta"]),
            int(row["b_pool_tiles"]),
            int(row["tile_stride"]),
            int(row["cache_flush_elems"]),
        )
        by_config.setdefault(key, {})[str(row["mode"])] = row

    comparisons: list[dict[str, Any]] = []
    p_min_rows: list[dict[str, Any]] = []
    for key, rows in sorted(by_config.items()):
        device, consumer_rows, validate_iters, num_cta, b_pool_tiles, tile_stride, cache_flush_elems = key
        for baseline_name in ("global_frag_reuse", "global_reload_per_row"):
            baseline = rows.get(baseline_name)
            if not baseline:
                continue
            base_ms = float(baseline["wall_ms_mean"])
            for mode in ("lds_hit", "lds_miss_overwrite"):
                row = rows.get(mode)
                if not row:
                    continue
                mode_ms = float(row["wall_ms_mean"])
                comparisons.append(
                    {
                        "device": device,
                        "consumer_rows": consumer_rows,
                        "validate_iters": validate_iters,
                        "num_cta": num_cta,
                        "b_pool_tiles": b_pool_tiles,
                        "tile_stride": tile_stride,
                        "cache_flush_elems": cache_flush_elems,
                        "baseline": baseline_name,
                        "mode": mode,
                        "delta_vs_baseline_ms": mode_ms - base_ms,
                        "speedup_vs_baseline": base_ms / mode_ms if mode_ms > 0 else None,
                    }
                )
            hit = rows.get("lds_hit")
            miss = rows.get("lds_miss_overwrite")
            if hit and miss:
                hit_ms = float(hit["wall_ms_mean"])
                miss_ms = float(miss["wall_ms_mean"])
                if hit_ms >= base_ms and miss_ms >= base_ms:
                    p_min = None
                    status = "not_profitable_even_at_full_hit"
                elif miss_ms <= base_ms:
                    p_min = 0.0
                    status = "profitable_for_any_hit_rate"
                elif miss_ms <= hit_ms:
                    p_min = None
                    status = "invalid_timing_order"
                else:
                    p_min = (miss_ms - base_ms) / (miss_ms - hit_ms)
                    p_min = max(0.0, min(1.0, p_min))
                    status = "profitable_if_hit_rate_exceeds_p_min"
                p_min_rows.append(
                    {
                        "device": device,
                        "consumer_rows": consumer_rows,
                        "validate_iters": validate_iters,
                        "num_cta": num_cta,
                        "b_pool_tiles": b_pool_tiles,
                        "tile_stride": tile_stride,
                        "cache_flush_elems": cache_flush_elems,
                        "baseline": baseline_name,
                        "global_ms": base_ms,
                        "hit_ms": hit_ms,
                        "miss_ms": miss_ms,
                        "p_min_hit_rate": p_min,
                        "status": status,
                    }
                )
    return {"comparisons": comparisons, "p_min": p_min_rows}


def main() -> None:
    args = parse_args()
    devices = sorted(set(args.device or [0]))
    modes = args.mode or DEFAULT_MODES
    consumer_rows_values = sorted(set(args.consumer_rows or [1]))
    validate_iters_values = sorted(set(args.validate_iters or [0]))
    num_cta_values = sorted(set(args.num_cta or [1]))
    b_pool_tiles_values = sorted(set(args.b_pool_tiles or [1]))
    tile_stride_values = sorted(set(args.tile_stride or [1]))
    cache_flush_values = sorted(set(args.cache_flush_elems or [0]))
    build(force=args.force_build, offload_arch=args.offload_arch)
    results: list[dict[str, Any]] = []
    for device in devices:
        for consumer_rows in consumer_rows_values:
            for validate_iters in validate_iters_values:
                for num_cta in num_cta_values:
                    for b_pool_tiles in b_pool_tiles_values:
                        for tile_stride in tile_stride_values:
                            for cache_flush_elems in cache_flush_values:
                                for mode in modes:
                                    result = run(
                                        [
                                            str(BIN),
                                            "--device",
                                            str(device),
                                            "--mode",
                                            mode,
                                            "--consumer-rows",
                                            str(consumer_rows),
                                            "--validate-iters",
                                            str(validate_iters),
                                            "--num-cta",
                                            str(num_cta),
                                            "--b-pool-tiles",
                                            str(b_pool_tiles),
                                            "--tile-stride",
                                            str(tile_stride),
                                            "--cache-flush-elems",
                                            str(cache_flush_elems),
                                            "--warmup",
                                            str(args.warmup),
                                            "--iters",
                                            str(args.iters),
                                        ]
                                    )
                                    payload = json.loads(result.stdout)
                                    if result.stderr:
                                        payload["stderr"] = result.stderr
                                    results.append(payload)
    report = {
        "ok": all(bool(row.get("ok")) for row in results),
        "config": {
            "devices": devices,
            "modes": modes,
            "consumer_rows": consumer_rows_values,
            "validate_iters": validate_iters_values,
            "num_cta": num_cta_values,
            "b_pool_tiles": b_pool_tiles_values,
            "tile_stride": tile_stride_values,
            "cache_flush_elems": cache_flush_values,
            "warmup": args.warmup,
            "iters": args.iters,
            "offload_arch": args.offload_arch,
            "binary": str(BIN),
            "source": str(SRC),
        },
        "results": results,
        "summary": summarize(results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
