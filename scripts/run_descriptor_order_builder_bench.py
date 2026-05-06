#!/usr/bin/env python3
"""Benchmark low-overhead bucketed descriptor-order builders on tile streams."""

from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    evaluate_tile_order_policy,
    load_tile_requests_jsonl,
    order_tile_request_stream,
    tile_requests_from_tensor_cache,
)


SRC = REPO_ROOT / "microbench" / "tile_order_cache" / "descriptor_order_builder_bench.cpp"
BUILD_DIR = REPO_ROOT / "microbench" / "tile_order_cache" / "build"
BIN = BUILD_DIR / "descriptor_order_builder_bench"
DEFAULT_POLICIES = [
    "linear",
    "utility_tile_grouped_bucket",
    "utility_tile_grouped_top16",
    "utility_tile_grouped_top32",
]
POLICY_TO_MODE = {
    "linear": "linear",
    "utility_tile_grouped_bucket": "bucket",
    "utility_tile_grouped_top16": "top16",
    "utility_tile_grouped_top32": "top32",
}


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


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-jsonl", type=Path, default=None)
    source.add_argument("--tensor-cache", type=Path, default=None)
    parser.add_argument("--policy", action="append", choices=DEFAULT_POLICIES, default=None)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32])
    parser.add_argument("--tile-order-top-k", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num-tiles", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--iters", type=int, default=100)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--tensor-max-examples", type=int, default=None)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "tile_order_cache" / "descriptor_order_builder_bench.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=REPO_ROOT / "outputs" / "reports" / "tile_order_cache" / "descriptor_order_builder_bench.md",
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
    )
    source["type"] = "tensor_cache"
    source["path"] = str(args.tensor_cache)
    source["max_examples"] = args.tensor_max_examples
    return requests, source


def write_inputs(requests: list[Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tile_ids = array("i", [int(request.tile_id) for request in requests])
    window_ids = array("i", [int(request.window_id) for request in requests])
    utility_scores = array("f", [float(request.utility_score) for request in requests])
    paths = {
        "tile_ids": output_dir / "tile_ids.i32",
        "window_ids": output_dir / "window_ids.i32",
        "utility_scores": output_dir / "utility_scores.f32",
    }
    with paths["tile_ids"].open("wb") as handle:
        tile_ids.tofile(handle)
    with paths["window_ids"].open("wb") as handle:
        window_ids.tofile(handle)
    with paths["utility_scores"].open("wb") as handle:
        utility_scores.tofile(handle)
    return paths


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Descriptor-Order Builder Bench",
        "",
        "This measures a C++ bucketed builder over the token/row tile stream.",
        "It is still a standalone builder microbench, not an online runtime hook.",
        "",
        f"- Requests: `{report['request_count']}`",
        f"- Source: `{report['source']}`",
        "",
        "| policy | cpp_build_us_median | cpp_us/window | python_build_us | LRU@8 | LRU@16 | reuse_mean | order_hit | same_multiset | order_changed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report["policies"]:
        metrics = row["metrics"]
        lru = metrics["lru_hit_rate"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["policy"],
                    fmt(row["cpp_timing"]["build_us_median"]),
                    fmt(row["cpp_build_us_per_window_median"]),
                    fmt(row["python_order_build_us"]),
                    fmt(lru.get("8")),
                    fmt(lru.get("16")),
                    fmt(metrics["reuse_distance"]["mean"]),
                    fmt(metrics["tile_order_hit_rate"]),
                    str(row["same_multiset"]),
                    str(row["order_changed"]),
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
    policies = args.policy or DEFAULT_POLICIES
    input_dir = args.output_json.parent / (args.output_json.stem + "_inputs")
    input_paths = write_inputs(requests, input_dir)

    rows = []
    reports = {}
    for policy in policies:
        _, descriptor_report = order_tile_request_stream(
            requests,
            policy=policy,
            cache_sizes=args.cache_sizes,
            tile_order_top_k=args.tile_order_top_k,
            seed=args.seed,
        )
        reports[policy] = descriptor_report

    baseline = reports.get("linear")
    baseline_multiset_hash = baseline.tile_multiset_hash if baseline is not None else None
    baseline_order_hash = baseline.order_hash if baseline is not None else None

    for policy in policies:
        mode = POLICY_TO_MODE[policy]
        completed = run(
            [
                str(BIN),
                "--tile-ids-bin",
                str(input_paths["tile_ids"]),
                "--window-ids-bin",
                str(input_paths["window_ids"]),
                "--utility-scores-bin",
                str(input_paths["utility_scores"]),
                "--count",
                str(len(requests)),
                "--num-tiles",
                str(args.num_tiles),
                "--mode",
                mode,
                "--warmup",
                str(args.warmup),
                "--iters",
                str(args.iters),
            ]
        )
        timing = json.loads(completed.stdout)
        timing["stderr"] = completed.stderr
        descriptor_report = reports[policy]
        window_count = max(1, int(descriptor_report.metrics.get("window_count", 1) or 1))
        rows.append(
            {
                **descriptor_report.as_dict(),
                "policy": policy,
                "builder_mode": mode,
                "order_build_us": {
                    "count": int(timing["iters"]),
                    "mean": float(timing["build_us_mean"]),
                    "median": float(timing["build_us_median"]),
                    "p10": float(timing["build_us_p10"]),
                    "p90": float(timing["build_us_p90"]),
                    "min": float(timing["build_us_min"]),
                    "max": float(timing["build_us_max"]),
                },
                "python_order_build_us": descriptor_report.order_build_us,
                "cpp_build_us_per_window_median": (
                    float(timing["build_us_median"]) / float(window_count)
                ),
                "cpp_timing": timing,
                "same_multiset": (
                    descriptor_report.tile_multiset_hash == baseline_multiset_hash
                    if baseline_multiset_hash is not None
                    else True
                ),
                "order_changed": (
                    descriptor_report.order_hash != baseline_order_hash
                    if baseline_order_hash is not None
                    else None
                ),
            }
        )

    report = {
        "ok": all(row["cpp_timing"].get("ok") for row in rows),
        "schema_version": 1,
        "source": source,
        "request_count": len(requests),
        "binary": str(BIN),
        "source_cpp": str(SRC),
        "input_dir": str(input_dir),
        "config": {
            "policies": policies,
            "cache_sizes": args.cache_sizes,
            "tile_order_top_k": args.tile_order_top_k,
            "num_tiles": args.num_tiles,
            "warmup": args.warmup,
            "iters": args.iters,
            "seed": args.seed,
        },
        "policies": rows,
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
