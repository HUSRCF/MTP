#!/usr/bin/env python3
"""Run a same-multiset descriptor consumer micro-runtime on vLLM traces.

This is the first execution-facing descriptor-order MVP.  It rebuilds the
current-router token/row TileRequest stream from an online vLLM trace directory,
constructs two visitation orders over the same descriptor multiset, and feeds
both orders into the same HIP consumer:

  - no_order: original current-router visitation order
  - layer_prior_frequency: calibrated per-layer B-tile group order

The benchmark does not patch vLLM kernels yet.  It verifies the execution-side
question under a controlled consumer: does changing only descriptor/tile order
alter timing while preserving the tile multiset?
"""

from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    TileRequest,
    evaluate_ordered_tile_requests,
    load_layer_tile_prior,
    order_tile_requests_with_layer_prior,
)
from replay_vllm_descriptor_order_shadow import load_vllm_tile_requests  # noqa: E402
from run_descriptor_order_builder_bench import (  # noqa: E402
    BIN as BUILDER_BIN,
    build as build_descriptor_builder,
    write_inputs as write_builder_inputs,
    write_prior_order,
)
from run_tile_order_cache_bench import (  # noqa: E402
    BIN,
    build,
    hash_ints,
    run,
    stats,
    write_tile_ids,
)


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--prior-json", type=Path, required=True)
    parser.add_argument("--token-window-size", type=int, default=64)
    parser.add_argument("--topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument(
        "--max-windows",
        type=int,
        default=512,
        help="Consume only the first N complete windows from the online trace stream.",
    )
    parser.add_argument("--top-utility-override", type=int, default=0)
    parser.add_argument("--device", type=int, action="append", default=None)
    parser.add_argument("--tile-elems", type=int, action="append", default=None)
    parser.add_argument("--tiles-per-cta", type=int, action="append", default=None)
    parser.add_argument("--cache-flush-elems", type=int, action="append", default=None)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument(
        "--build-repeat",
        type=int,
        default=3,
        help="Repeat host-side order construction timing this many times.",
    )
    parser.add_argument(
        "--measure-cpp-builder",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Measure C++ layer-prior plan/materialized builder overhead on the same stream.",
    )
    parser.add_argument("--builder-warmup", type=int, default=5)
    parser.add_argument("--builder-iters", type=int, default=50)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "tile_order_cache"
        / "descriptor_consumer_micro_runtime.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=REPO_ROOT
        / "outputs"
        / "reports"
        / "tile_order_cache"
        / "descriptor_consumer_micro_runtime.md",
    )
    return parser.parse_args()


def _filter_first_windows(
    requests: Sequence[TileRequest],
    *,
    max_windows: int,
) -> tuple[list[TileRequest], dict[str, Any]]:
    if max_windows <= 0:
        return list(requests), {
            "selected_window_count": len({item.window_id for item in requests}),
            "selected_request_count": len(requests),
        }
    selected_ids = set(sorted({int(item.window_id) for item in requests})[: int(max_windows)])
    selected: list[TileRequest] = []
    for new_id, item in enumerate(requests):
        if int(item.window_id) not in selected_ids:
            continue
        selected.append(
            TileRequest(
                window_id=int(item.window_id),
                request_id=int(new_id),
                tile_id=int(item.tile_id),
                expert_id=int(item.expert_id),
                transition_score=float(item.transition_score),
                mtp_score=float(item.mtp_score),
                utility_score=float(item.utility_score),
                sample_idx=item.sample_idx,
                token_index=item.token_index,
                layer_idx=item.layer_idx,
                row_id=item.row_id,
                weight=item.weight,
                source_policy=item.source_policy,
                split=item.split,
            )
        )
    return selected, {
        "selected_window_count": len(selected_ids),
        "selected_request_count": len(selected),
    }


def _time_build(build_fn: Any, *, repeat: int) -> tuple[list[TileRequest], dict[str, Any]]:
    ordered = build_fn()
    timings: list[float] = []
    for _ in range(max(1, int(repeat))):
        start_ns = time.perf_counter_ns()
        build_fn()
        timings.append((time.perf_counter_ns() - start_ns) / 1000.0)
    return ordered, stats(timings)


def _policy_orders(
    requests: Sequence[TileRequest],
    *,
    prior_path: Path,
    top_utility_override: int,
    build_repeat: int,
) -> list[tuple[str, list[TileRequest], dict[str, Any]]]:
    prior = load_layer_tile_prior(prior_path)
    layer_prior_name = f"layer_prior_{prior.score_name}"
    if top_utility_override:
        layer_prior_name = (
            f"{layer_prior_name}_top{int(top_utility_override)}_utility_override"
        )
    no_order, no_order_build_us = _time_build(lambda: list(requests), repeat=build_repeat)
    layer_prior, layer_prior_build_us = _time_build(
        lambda: order_tile_requests_with_layer_prior(
            requests,
            prior=prior,
            top_utility_override=int(top_utility_override),
        ),
        repeat=build_repeat,
    )
    return [
        ("no_order", no_order, no_order_build_us),
        (layer_prior_name, layer_prior, layer_prior_build_us),
    ]


def _write_tile_ids(path: Path, ordered: Sequence[TileRequest]) -> dict[str, Any]:
    start_ns = time.perf_counter_ns()
    tile_ids = [int(item.tile_id) for item in ordered]
    write_tile_ids(path, tile_ids)
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0
    return {
        "order_path": str(path),
        "order_hash": hash_ints(tile_ids),
        "tile_multiset_hash": hash_ints(sorted(tile_ids)),
        "tile_count": len(tile_ids),
        "unique_tiles": len(set(tile_ids)),
        "order_export_us": float(elapsed_us),
    }


def _run_consumer(
    *,
    order_path: Path,
    tile_count: int,
    device: int,
    tile_elems: int,
    tiles_per_cta: int,
    cache_flush_elems: int,
    warmup: int,
    iters: int,
) -> dict[str, Any]:
    completed = run(
        [
            str(BIN),
            "--device",
            str(device),
            "--tile-ids-bin",
            str(order_path),
            "--tile-count",
            str(tile_count),
            "--tile-elems",
            str(tile_elems),
            "--tiles-per-cta",
            str(tiles_per_cta),
            "--cache-flush-elems",
            str(cache_flush_elems),
            "--warmup",
            str(warmup),
            "--iters",
            str(iters),
        ]
    )
    row = json.loads(completed.stdout)
    row["stderr"] = completed.stderr
    return row


def _run_cpp_builder(
    *,
    requests: Sequence[TileRequest],
    prior_path: Path,
    output_dir: Path,
    num_tiles: int,
    warmup: int,
    iters: int,
    top_utility_override: int,
    cxx: str,
) -> dict[str, Any]:
    build_descriptor_builder(force=False, cxx=cxx)
    input_dir = output_dir / "builder_inputs"
    input_paths = write_builder_inputs(list(requests), input_dir)
    prior = load_layer_tile_prior(prior_path)
    num_layers = max(
        1,
        max(
            int(request.layer_idx) if request.layer_idx is not None else 0
            for request in requests
        )
        + 1,
    )
    prior_order_path = write_prior_order(
        prior,
        num_tiles=int(num_tiles),
        num_layers=int(num_layers),
        path=input_dir / f"{prior_path.stem}_prior_order.i32",
    )
    rows: dict[str, Any] = {}
    for mode in ("layer_prior_plan", "layer_prior_materialized"):
        cmd = [
            str(BUILDER_BIN),
            "--tile-ids-bin",
            str(input_paths["tile_ids"]),
            "--window-ids-bin",
            str(input_paths["window_ids"]),
            "--utility-scores-bin",
            str(input_paths["utility_scores"]),
            "--layer-ids-bin",
            str(input_paths["layer_ids"]),
            "--prior-order-bin",
            str(prior_order_path),
            "--count",
            str(len(requests)),
            "--num-tiles",
            str(num_tiles),
            "--num-layers",
            str(num_layers),
            "--top-utility-override",
            str(top_utility_override),
            "--mode",
            mode,
            "--warmup",
            str(warmup),
            "--iters",
            str(iters),
        ]
        completed = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            row = json.loads(completed.stdout)
        except json.JSONDecodeError:
            row = {
                "ok": False,
                "error": "failed to parse descriptor_order_builder_bench stdout",
                "stdout": completed.stdout,
            }
        row["returncode"] = int(completed.returncode)
        row["stderr"] = completed.stderr
        row["command"] = cmd
        if completed.returncode != 0:
            row["ok"] = False
            row.setdefault("error", completed.stderr.strip() or completed.stdout.strip())
        rows[mode] = row
    return {
        "ok": all(bool(row.get("ok")) for row in rows.values()),
        "input_dir": str(input_dir),
        "prior_order_bin": str(prior_order_path),
        "num_layers": int(num_layers),
        "num_tiles": int(num_tiles),
        "top_utility_override": int(top_utility_override),
        "modes": rows,
    }


def _infer_num_tiles(requests: Sequence[TileRequest]) -> int:
    return max(1, max(int(item.tile_id) for item in requests) + 1)


def _summarize(
    rows: Sequence[dict[str, Any]],
    *,
    policy_meta: dict[str, dict[str, Any]],
    cpp_builder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_config: dict[tuple[int, int, int, int], dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        key = (
            int(row["device"]),
            int(row["tile_elems"]),
            int(row["tiles_per_cta"]),
            int(row["cache_flush_elems"]),
        )
        by_config.setdefault(key, {}).setdefault(str(row["policy"]), []).append(row)

    stability: list[dict[str, Any]] = []
    for key, by_policy in sorted(by_config.items()):
        baseline = by_policy.get("no_order", [])
        baseline_stats = stats([float(item["us_per_tile"]) for item in baseline])
        baseline_median = baseline_stats["median"]
        baseline_checksum = (
            float(baseline[0]["checksum"]) if baseline else None
        )
        for policy, policy_rows in sorted(by_policy.items()):
            meta = policy_meta.get(policy, {})
            same_multiset = bool(meta.get("same_multiset_as_no_order", True))
            us_stats = stats([float(item["us_per_tile"]) for item in policy_rows])
            wall_stats = stats([float(item["wall_ms_mean"]) for item in policy_rows])
            checksum = float(policy_rows[0]["checksum"]) if policy_rows else None
            speedup = None
            if baseline_median and us_stats["median"]:
                speedup = float(baseline_median) / float(us_stats["median"])
            consumer_saved_us = None
            net_saved_us_python = None
            if (
                same_multiset
                and baseline_median is not None
                and us_stats["median"] is not None
                and policy_rows
            ):
                tile_count = int(policy_rows[0].get("tile_count", 0) or 0)
                consumer_saved_us = (
                    float(baseline_median) - float(us_stats["median"])
                ) * float(tile_count)
                build_us = float((meta.get("order_build_us") or {}).get("median") or 0.0)
                export_us = float(meta.get("order_export_us") or 0.0)
                net_saved_us_python = consumer_saved_us - build_us - export_us
            net_saved_us_cpp_plan = None
            net_saved_us_cpp_materialized = None
            if policy.startswith("layer_prior_") and consumer_saved_us is not None and cpp_builder:
                modes = cpp_builder.get("modes", {})
                plan = modes.get("layer_prior_plan", {})
                materialized = modes.get("layer_prior_materialized", {})
                if plan.get("ok") and plan.get("build_us_median") is not None:
                    net_saved_us_cpp_plan = consumer_saved_us - float(plan["build_us_median"])
                if materialized.get("ok") and materialized.get("build_us_median") is not None:
                    net_saved_us_cpp_materialized = consumer_saved_us - float(
                        materialized["build_us_median"]
                    )
            checksum_delta = None
            if baseline_checksum is not None and checksum is not None:
                checksum_delta = abs(float(checksum) - float(baseline_checksum))
            stability.append(
                {
                    "device": key[0],
                    "tile_elems": key[1],
                    "tiles_per_cta": key[2],
                    "cache_flush_elems": key[3],
                    "policy": policy,
                    "us_per_tile": us_stats,
                    "wall_ms": wall_stats,
                    "speedup_median_vs_no_order": speedup,
                    "consumer_saved_us_median_vs_no_order": consumer_saved_us,
                    "net_saved_us_after_python_order_build": net_saved_us_python,
                    "net_saved_us_after_cpp_plan_build": net_saved_us_cpp_plan,
                    "net_saved_us_after_cpp_materialized_build": net_saved_us_cpp_materialized,
                    "checksum": checksum,
                    "checksum_delta_abs_vs_no_order": checksum_delta,
                }
            )
    return {"stability": stability}


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Descriptor Consumer Micro-Runtime",
        "",
        "This benchmark consumes a real online vLLM descriptor/tile stream with the",
        "same HIP consumer under two same-multiset visitation orders.",
        "",
        f"- Trace dir: `{report['source']['path']}`",
        f"- Selected windows: `{report['selection']['selected_window_count']}`",
        f"- Selected requests: `{report['selection']['selected_request_count']}`",
        f"- Unique tiles: `{report['unique_tiles']}`",
        "",
        "| device | tile_elems | tiles/CTA | flush | policy | us/tile median | speedup vs no_order | consumer saved us | net saved us Python | net saved us C++ plan | net saved us C++ materialized | checksum delta | LRU@8 | order_hit |",
        "|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    metrics_by_policy = {
        row["policy"]: row["trace_metrics"] for row in report["policies"]
    }
    for row in report["summary"]["stability"]:
        metrics = metrics_by_policy.get(row["policy"], {})
        lru = metrics.get("lru_hit_rate", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["device"]),
                    str(row["tile_elems"]),
                    str(row["tiles_per_cta"]),
                    str(row["cache_flush_elems"]),
                    row["policy"],
                    _fmt(row["us_per_tile"]["median"]),
                    _fmt(row["speedup_median_vs_no_order"]),
                    _fmt(row.get("consumer_saved_us_median_vs_no_order")),
                    _fmt(row.get("net_saved_us_after_python_order_build")),
                    _fmt(row.get("net_saved_us_after_cpp_plan_build")),
                    _fmt(row.get("net_saved_us_after_cpp_materialized_build")),
                    _fmt(row["checksum_delta_abs_vs_no_order"]),
                    _fmt(lru.get("8")),
                    _fmt(metrics.get("tile_order_hit_rate")),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if args.repeat <= 0:
        raise ValueError("--repeat must be positive")
    build(force=bool(args.force_build), offload_arch=str(args.offload_arch))
    requests_all, source = load_vllm_tile_requests(
        args.trace_dir,
        token_window_size=int(args.token_window_size),
        topk=int(args.topk),
        tiles_per_expert=int(args.tiles_per_expert),
    )
    requests, selection = _filter_first_windows(
        requests_all,
        max_windows=int(args.max_windows),
    )
    if not requests:
        raise ValueError("selected descriptor stream is empty")

    order_dir = args.output_json.parent / f"{args.output_json.stem}_orders"
    order_dir.mkdir(parents=True, exist_ok=True)
    devices = sorted(set(args.device or [0]))
    tile_elems_values = sorted(set(args.tile_elems or [1024]))
    tiles_per_cta_values = sorted(set(args.tiles_per_cta or [32]))
    cache_flush_values = sorted(set(args.cache_flush_elems or [0]))
    cpp_builder = None
    if bool(args.measure_cpp_builder):
        inferred_num_tiles = _infer_num_tiles(requests)
        try:
            cpp_builder = _run_cpp_builder(
                requests=requests,
                prior_path=args.prior_json,
                output_dir=args.output_json.parent / f"{args.output_json.stem}_builder",
                num_tiles=inferred_num_tiles,
                warmup=int(args.builder_warmup),
                iters=int(args.builder_iters),
                top_utility_override=int(args.top_utility_override),
                cxx=str(args.cxx),
            )
        except Exception as exc:  # pragma: no cover - exercised by integration failures.
            cpp_builder = {
                "ok": False,
                "error": str(exc),
                "num_tiles": inferred_num_tiles,
                "top_utility_override": int(args.top_utility_override),
                "modes": {},
            }

    policy_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    baseline_multiset_hash: str | None = None
    for policy, ordered, order_build_us in _policy_orders(
        requests,
        prior_path=args.prior_json,
        top_utility_override=int(args.top_utility_override),
        build_repeat=int(args.build_repeat),
    ):
        order_meta = _write_tile_ids(order_dir / f"{policy}.i32", ordered)
        if baseline_multiset_hash is None:
            baseline_multiset_hash = str(order_meta["tile_multiset_hash"])
        trace_metrics = evaluate_ordered_tile_requests(
            requests,
            ordered,
            policy=policy,
            cache_sizes=[8, 16, 32],
            tile_order_top_k=8,
        )
        policy_rows.append(
            {
                "policy": policy,
                "trace_metrics": trace_metrics,
                "order": order_meta,
                "order_build_us": order_build_us,
                "order_export_us": float(order_meta["order_export_us"]),
                "same_multiset_as_no_order": (
                    str(order_meta["tile_multiset_hash"]) == baseline_multiset_hash
                ),
            }
        )
        for device in devices:
            for tile_elems in tile_elems_values:
                for tiles_per_cta in tiles_per_cta_values:
                    for cache_flush_elems in cache_flush_values:
                        for repeat in range(int(args.repeat)):
                            timing = _run_consumer(
                                order_path=Path(str(order_meta["order_path"])),
                                tile_count=int(order_meta["tile_count"]),
                                device=int(device),
                                tile_elems=int(tile_elems),
                                tiles_per_cta=int(tiles_per_cta),
                                cache_flush_elems=int(cache_flush_elems),
                                warmup=int(args.warmup),
                                iters=int(args.iters),
                            )
                            timing.update(
                                {
                                    "policy": policy,
                                    "repeat": repeat,
                                    "tile_count": int(order_meta["tile_count"]),
                                    "order_hash": order_meta["order_hash"],
                                    "tile_multiset_hash": order_meta["tile_multiset_hash"],
                                }
                            )
                            timing_rows.append(timing)

    report = {
        "ok": all(row.get("ok") for row in timing_rows)
        and all(row["same_multiset_as_no_order"] for row in policy_rows),
        "source": source,
        "selection": selection,
        "request_count_total": int(len(requests_all)),
        "request_count_consumed": int(len(requests)),
        "unique_tiles": int(len({item.tile_id for item in requests})),
        "config": {
            "trace_dir": str(args.trace_dir),
            "prior_json": str(args.prior_json),
            "token_window_size": int(args.token_window_size),
            "topk": int(args.topk),
            "tiles_per_expert": int(args.tiles_per_expert),
            "max_windows": int(args.max_windows),
            "top_utility_override": int(args.top_utility_override),
            "devices": devices,
            "tile_elems": tile_elems_values,
            "tiles_per_cta": tiles_per_cta_values,
            "cache_flush_elems": cache_flush_values,
            "warmup": int(args.warmup),
            "iters": int(args.iters),
            "repeat": int(args.repeat),
            "build_repeat": int(args.build_repeat),
            "measure_cpp_builder": bool(args.measure_cpp_builder),
            "builder_warmup": int(args.builder_warmup),
            "builder_iters": int(args.builder_iters),
            "binary": str(BIN),
            "builder_binary": str(BUILDER_BIN),
        },
        "policies": policy_rows,
        "timing": timing_rows,
        "cpp_builder": cpp_builder,
        "summary": _summarize(
            timing_rows,
            policy_meta={row["policy"]: row for row in policy_rows},
            cpp_builder=cpp_builder,
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(_render_markdown(report), encoding="utf-8")
    print(_render_markdown(report))
    print(f"Wrote {args.output_json}")


if __name__ == "__main__":
    main()
