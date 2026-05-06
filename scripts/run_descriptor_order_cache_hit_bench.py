#!/usr/bin/env python3
"""Benchmark descriptor-order permutation-cache lookup paths."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    group_by_window,
    load_tile_requests_jsonl,
    tile_requests_from_tensor_cache,
)


SRC = REPO_ROOT / "microbench" / "tile_order_cache" / "descriptor_order_cache_hit_bench.cpp"
BUILD_DIR = REPO_ROOT / "microbench" / "tile_order_cache" / "build"
BIN = BUILD_DIR / "descriptor_order_cache_hit_bench"
KEY_MODES = ["exact_multiset", "tile_set", "layer_only", "global"]
BENCH_MODES = ["warm_lookup", "replay_insert"]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build(*, force: bool, cxx: str) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if BIN.exists() and not force and BIN.stat().st_mtime >= SRC.stat().st_mtime:
        return
    completed = run([cxx, "-O3", "-std=c++17", str(SRC), "-o", str(BIN)])
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-jsonl", type=Path, default=None)
    source.add_argument("--tensor-cache", type=Path, default=None)
    parser.add_argument("--key-mode", action="append", choices=KEY_MODES, default=None)
    parser.add_argument("--bench-mode", action="append", choices=BENCH_MODES, default=None)
    parser.add_argument("--policy", default="utility_tile_grouped_bucket")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--iters", type=int, default=200)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--tensor-max-examples", type=int, default=None)
    parser.add_argument("--tensor-start-example", type=int, default=0)
    parser.add_argument("--split-name", default=None)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "tile_order_cache" / "descriptor_order_cache_hit_bench.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "tile_order_cache" / "descriptor_order_cache_hit_bench.md",
    )
    return parser.parse_args()


def load_requests(args: argparse.Namespace) -> tuple[list[Any], dict[str, Any]]:
    if args.input_jsonl is not None:
        return load_tile_requests_jsonl(args.input_jsonl), {
            "type": "input_jsonl",
            "path": str(args.input_jsonl),
        }
    import torch

    cache = torch.load(args.tensor_cache, map_location="cpu")
    requests, source = tile_requests_from_tensor_cache(
        cache,
        window_size=args.tensor_window_size,
        topk=args.tensor_topk,
        tiles_per_expert=args.tiles_per_expert,
        max_examples=args.tensor_max_examples,
        start_example=args.tensor_start_example,
        split_name=args.split_name,
    )
    source["type"] = "tensor_cache"
    source["path"] = str(args.tensor_cache)
    source["max_examples"] = args.tensor_max_examples
    source["start_example"] = args.tensor_start_example
    source["split_name"] = args.split_name
    return requests, source


def stable_u64(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("ascii")).digest()[:8], "little")


def layer_id_for_window(window: list[Any]) -> int:
    layers = {request.layer_idx for request in window if request.layer_idx is not None}
    if len(layers) == 1:
        return int(next(iter(layers)))
    return int(window[0].window_id)


def key_for_window(window: list[Any], *, key_mode: str, policy: str) -> int:
    tile_ids = [int(request.tile_id) for request in window]
    layer = layer_id_for_window(window)
    if key_mode == "exact_multiset":
        body = ",".join(str(tile_id) for tile_id in sorted(tile_ids))
        key = f"layer={layer}:multiset={body}:policy={policy}"
    elif key_mode == "tile_set":
        body = ",".join(str(tile_id) for tile_id in sorted(set(tile_ids)))
        key = f"layer={layer}:tile_set={body}:policy={policy}"
    elif key_mode == "layer_only":
        key = f"layer={layer}:policy={policy}"
    elif key_mode == "global":
        key = f"global:policy={policy}"
    else:
        raise ValueError(f"unknown key mode: {key_mode}")
    return stable_u64(key)


def write_keys(windows: list[list[Any]], *, key_mode: str, policy: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    keys = array("Q", [key_for_window(window, key_mode=key_mode, policy=policy) for window in windows])
    with output.open("wb") as handle:
        keys.tofile(handle)


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Descriptor-Order Cache Hit Bench",
        "",
        "This measures CPU hash lookup paths for descriptor-order cache keys.",
        "It does not apply or rebuild descriptors.",
        "",
        f"- Windows: `{report['window_count']}`",
        f"- Source: `{report['source']}`",
        "",
        "| key_mode | bench_mode | unique_keys | lookup_us | ns/key | hits | misses |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        timing = row["timing"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["key_mode"],
                    row["bench_mode"],
                    fmt(timing["unique_key_count"]),
                    fmt(timing["lookup_us_median"]),
                    fmt(timing["ns_per_key_median"]),
                    fmt(timing["hits_last_iter"]),
                    fmt(timing["misses_last_iter"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    build(force=args.force_build, cxx=args.cxx)
    requests, source = load_requests(args)
    windows = group_by_window(requests)
    key_modes = args.key_mode or ["exact_multiset", "tile_set", "layer_only"]
    bench_modes = args.bench_mode or BENCH_MODES
    key_dir = args.output_json.parent / (args.output_json.stem + "_keys")

    rows = []
    for key_mode in key_modes:
        key_path = key_dir / f"{key_mode}.u64"
        write_keys(windows, key_mode=key_mode, policy=args.policy, output=key_path)
        for bench_mode in bench_modes:
            completed = run(
                [
                    str(BIN),
                    "--keys-bin",
                    str(key_path),
                    "--count",
                    str(len(windows)),
                    "--mode",
                    bench_mode,
                    "--warmup",
                    str(args.warmup),
                    "--iters",
                    str(args.iters),
                ]
            )
            timing = json.loads(completed.stdout)
            timing["stderr"] = completed.stderr
            rows.append(
                {
                    "key_mode": key_mode,
                    "bench_mode": bench_mode,
                    "key_path": str(key_path),
                    "timing": timing,
                }
            )

    report = {
        "ok": all(row["timing"].get("ok") for row in rows),
        "schema_version": 1,
        "source": source,
        "policy": args.policy,
        "window_count": len(windows),
        "request_count": len(requests),
        "binary": str(BIN),
        "source_cpp": str(SRC),
        "config": {
            "key_modes": key_modes,
            "bench_modes": bench_modes,
            "warmup": args.warmup,
            "iters": args.iters,
        },
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))


if __name__ == "__main__":
    main()
