#!/usr/bin/env python3
"""Run a no-LDS direct/global tile-order timing bench."""

from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime.tile_order import (  # noqa: E402
    evaluate_tile_order_policy,
    generate_synthetic_tile_requests,
    load_tile_requests_json,
    order_tile_requests,
)
from scripts.simulate_tile_order_cache import load_tensor_cache_requests  # noqa: E402

SRC = REPO_ROOT / "microbench" / "tile_order_cache" / "tile_order_cache_bench.hip"
BUILD_DIR = REPO_ROOT / "microbench" / "tile_order_cache" / "build"
BIN = BUILD_DIR / "tile_order_cache_bench"
DEFAULT_POLICIES = [
    "linear",
    "random",
    "b_tile_grouped",
    "utility_hot_first",
    "utility_tile_grouped",
    "oracle_cache_aware",
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


def build(*, force: bool, offload_arch: str) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if BIN.exists() and not force and BIN.stat().st_mtime >= SRC.stat().st_mtime:
        return
    result = run(
        [
            "hipcc",
            "-O3",
            "--std=c++17",
            f"--offload-arch={offload_arch}",
            str(SRC),
            "-o",
            str(BIN),
        ]
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input-json", type=Path, default=None)
    source.add_argument("--tensor-cache", type=Path, default=None)
    source.add_argument("--synthetic", action="store_true")
    parser.add_argument("--policy", action="append", choices=DEFAULT_POLICIES, default=None)
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32])
    parser.add_argument("--seed", type=int, default=0)

    parser.add_argument("--num-windows", type=int, default=16)
    parser.add_argument("--requests-per-window", type=int, default=128)
    parser.add_argument("--num-experts", type=int, default=256)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--hot-experts", type=int, default=32)
    parser.add_argument("--novelty-experts", type=int, default=16)
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tensor-max-examples", type=int, default=512)

    parser.add_argument("--tile-elems", type=int, action="append", default=None)
    parser.add_argument("--tiles-per-cta", type=int, action="append", default=None)
    parser.add_argument("--cache-flush-elems", type=int, action="append", default=None)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=50)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "tile_order_cache" / "tile_order_cache_bench.json",
    )
    return parser.parse_args()


def load_requests(args: argparse.Namespace):
    if args.input_json is not None:
        payload = json.loads(args.input_json.read_text(encoding="utf-8"))
        return load_tile_requests_json(payload), {"type": "input_json", "path": str(args.input_json)}
    if args.tensor_cache is not None:
        return load_tensor_cache_requests(
            args.tensor_cache,
            window_size=args.tensor_window_size,
            topk=args.tensor_topk,
            tiles_per_expert=args.tiles_per_expert,
            max_examples=args.tensor_max_examples,
        )
    requests = generate_synthetic_tile_requests(
        num_windows=args.num_windows,
        requests_per_window=args.requests_per_window,
        num_experts=args.num_experts,
        tiles_per_expert=args.tiles_per_expert,
        hot_experts=args.hot_experts,
        novelty_experts=args.novelty_experts,
        seed=args.seed,
    )
    return requests, {
        "type": "synthetic",
        "num_windows": args.num_windows,
        "requests_per_window": args.requests_per_window,
        "num_experts": args.num_experts,
        "tiles_per_expert": args.tiles_per_expert,
        "hot_experts": args.hot_experts,
        "novelty_experts": args.novelty_experts,
        "seed": args.seed,
    }


def write_tile_ids(path: Path, tile_ids: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    values = array("i", tile_ids)
    with path.open("wb") as handle:
        values.tofile(handle)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for row in results:
        merged = dict(row["trace_metrics"])
        merged.update(row["timing"])
        rows.append(merged)
    best_time = min(rows, key=lambda row: row["us_per_tile"]) if rows else None
    by_policy = {}
    for row in rows:
        policy = row["policy"]
        current = by_policy.get(policy)
        if current is None or row["us_per_tile"] < current["us_per_tile"]:
            by_policy[policy] = row
    return {
        "best_time": best_time,
        "best_time_by_policy": by_policy,
    }


def main() -> None:
    args = parse_args()
    build(force=args.force_build, offload_arch=args.offload_arch)
    requests, source = load_requests(args)
    policies = args.policy or DEFAULT_POLICIES
    devices = sorted(set(args.device or [0]))
    tile_elems_values = sorted(set(args.tile_elems or [256]))
    tiles_per_cta_values = sorted(set(args.tiles_per_cta or [32]))
    cache_flush_values = sorted(set(args.cache_flush_elems or [0]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    order_dir = args.output.parent / (args.output.stem + "_orders")
    results: list[dict[str, Any]] = []
    for policy in policies:
        ordered = order_tile_requests(requests, policy=policy, seed=args.seed)
        tile_ids = [item.tile_id for item in ordered]
        order_path = order_dir / f"{policy}.i32"
        write_tile_ids(order_path, tile_ids)
        trace_metrics = evaluate_tile_order_policy(
            requests,
            policy=policy,
            cache_sizes=args.cache_sizes,
            tile_order_top_k=8,
            seed=args.seed,
        )
        for device in devices:
            for tile_elems in tile_elems_values:
                for tiles_per_cta in tiles_per_cta_values:
                    for cache_flush_elems in cache_flush_values:
                        completed = run(
                            [
                                str(BIN),
                                "--device",
                                str(device),
                                "--tile-ids-bin",
                                str(order_path),
                                "--tile-count",
                                str(len(tile_ids)),
                                "--tile-elems",
                                str(tile_elems),
                                "--tiles-per-cta",
                                str(tiles_per_cta),
                                "--cache-flush-elems",
                                str(cache_flush_elems),
                                "--warmup",
                                str(args.warmup),
                                "--iters",
                                str(args.iters),
                            ]
                        )
                        timing = json.loads(completed.stdout)
                        timing["stderr"] = completed.stderr
                        timing["policy"] = policy
                        timing["order_path"] = str(order_path)
                        results.append(
                            {
                                "policy": policy,
                                "trace_metrics": trace_metrics,
                                "timing": timing,
                            }
                        )
    report = {
        "ok": all(row["timing"].get("ok") for row in results),
        "source": source,
        "config": {
            "policies": policies,
            "devices": devices,
            "tile_elems": tile_elems_values,
            "tiles_per_cta": tiles_per_cta_values,
            "cache_flush_elems": cache_flush_values,
            "warmup": args.warmup,
            "iters": args.iters,
            "binary": str(BIN),
            "source": str(SRC),
        },
        "results": results,
        "summary": summarize(results),
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
