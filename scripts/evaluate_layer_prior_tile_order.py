#!/usr/bin/env python3
"""Evaluate calibrated layer-prior tile-group ordering on held-out streams."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from statistics import mean, median
import time
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    TileRequest,
    evaluate_ordered_tile_requests,
    load_layer_tile_prior,
    load_tile_requests_jsonl,
    order_tile_requests,
    order_tile_requests_with_layer_prior,
)


BASELINE_POLICIES = [
    "linear",
    "b_tile_grouped",
    "utility_hot_first",
    "utility_tile_grouped_bucket",
    "utility_tile_grouped_top16",
    "utility_tile_grouped_top32",
    "oracle_cache_aware",
]


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--prior-json", type=Path, action="append", required=True)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32])
    parser.add_argument("--tile-order-top-k", type=int, default=8)
    parser.add_argument("--policy", action="append", choices=BASELINE_POLICIES, default=None)
    parser.add_argument("--top-utility-override", type=int, action="append", default=[0, 16, 32])
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument(
        "--kernel-saved-us",
        type=float,
        default=None,
        help="Optional timing-envelope saved_us used to estimate net_saved_us.",
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, default=None)
    return parser.parse_args()


def stats(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": float(mean(values)),
        "median": float(median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def hash_request_multiset(requests: Sequence[TileRequest]) -> str:
    rows = sorted((item.request_id, item.tile_id, item.expert_id) for item in requests)
    payload = ";".join(f"{request}:{tile}:{expert}" for request, tile, expert in rows)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def hash_request_order(requests: Sequence[TileRequest]) -> str:
    payload = ";".join(str(int(item.request_id)) for item in requests)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def time_ordering(
    build_fn: Callable[[], list[TileRequest]],
    *,
    repeat: int,
) -> tuple[list[TileRequest], dict[str, float | int | None]]:
    ordered = build_fn()
    timings = []
    for _ in range(max(1, int(repeat))):
        start_ns = time.perf_counter_ns()
        build_fn()
        timings.append((time.perf_counter_ns() - start_ns) / 1000.0)
    return ordered, stats(timings)


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def make_policy_row(
    *,
    requests: Sequence[TileRequest],
    ordered: Sequence[TileRequest],
    policy_name: str,
    build_us: dict[str, float | int | None],
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
    baseline_multiset_hash: str,
    baseline_order_hash: str,
    kernel_saved_us: float | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = evaluate_ordered_tile_requests(
        requests,
        ordered,
        policy=policy_name,
        cache_sizes=cache_sizes,
        tile_order_top_k=tile_order_top_k,
    )
    multiset_hash = hash_request_multiset(ordered)
    order_hash = hash_request_order(ordered)
    build_median = build_us.get("median")
    net_saved_us = None
    if kernel_saved_us is not None and build_median is not None:
        net_saved_us = float(kernel_saved_us) - float(build_median)
    row = {
        "policy": policy_name,
        "metrics": metrics,
        "order_build_us": build_us,
        "request_multiset_hash": multiset_hash,
        "request_order_hash": order_hash,
        "same_multiset": multiset_hash == baseline_multiset_hash,
        "order_changed": order_hash != baseline_order_hash,
        "kernel_saved_us": kernel_saved_us,
        "net_saved_us": net_saved_us,
    }
    if extra:
        row.update(extra)
    return row


def render_markdown(report: dict[str, Any]) -> str:
    cache_keys = sorted(report["config"]["cache_sizes"])
    lines = [
        "# Layer-Prior Tile-Order Heldout Evaluation",
        "",
        "This evaluates calibrated per-layer B-tile group-order priors on a held-out",
        "token/row-level tile stream. These policies preserve the current descriptor",
        "multiset and only change visitation order.",
        "",
        f"- Requests: `{report['request_count']}`",
        f"- Priors: `{[prior['path'] for prior in report['priors']]}`",
        f"- Repeat: `{report['config']['repeat']}`",
        "",
    ]
    columns = [
        "policy",
        "build_us_median",
        "net_saved_us",
        "LRU@8",
        "LRU@16",
        "reuse_mean",
        "order_hit",
        "same_multiset",
        "order_changed",
    ]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    for row in report["policies"]:
        lru = row["metrics"]["lru_hit_rate"]
        values = [
            row["policy"],
            row["order_build_us"]["median"],
            row.get("net_saved_us"),
            lru.get("8", lru.get(str(cache_keys[0]))),
            lru.get("16"),
            row["metrics"]["reuse_distance"]["mean"],
            row["metrics"]["tile_order_hit_rate"],
            row["same_multiset"],
            row["order_changed"],
        ]
        lines.append("| " + " | ".join(fmt(value) for value in values) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if args.repeat <= 0:
        raise ValueError("--repeat must be positive")
    requests = load_tile_requests_jsonl(args.input_jsonl)
    baseline_multiset_hash = hash_request_multiset(requests)
    baseline_order_hash = hash_request_order(requests)

    policies = args.policy or BASELINE_POLICIES
    rows: list[dict[str, Any]] = []
    for policy in policies:
        ordered, build_us = time_ordering(
            lambda policy=policy: order_tile_requests(requests, policy=policy),
            repeat=args.repeat,
        )
        rows.append(
            make_policy_row(
                requests=requests,
                ordered=ordered,
                policy_name=policy,
                build_us=build_us,
                cache_sizes=args.cache_sizes,
                tile_order_top_k=args.tile_order_top_k,
                baseline_multiset_hash=baseline_multiset_hash,
                baseline_order_hash=baseline_order_hash,
                kernel_saved_us=args.kernel_saved_us,
            )
        )

    prior_metadata = []
    for prior_path in args.prior_json:
        prior = load_layer_tile_prior(prior_path)
        prior_metadata.append(
            {
                "path": str(prior_path),
                "score_name": prior.score_name,
                "metadata": prior.metadata,
            }
        )
        base_name = f"layer_prior_{prior.score_name}"
        for top_h in sorted(set(int(value) for value in args.top_utility_override)):
            suffix = "" if top_h == 0 else f"_top{top_h}_utility_override"
            policy_name = f"{base_name}{suffix}"
            ordered, build_us = time_ordering(
                lambda prior=prior, top_h=top_h: order_tile_requests_with_layer_prior(
                    requests,
                    prior=prior,
                    top_utility_override=top_h,
                ),
                repeat=args.repeat,
            )
            rows.append(
                make_policy_row(
                    requests=requests,
                    ordered=ordered,
                    policy_name=policy_name,
                    build_us=build_us,
                    cache_sizes=args.cache_sizes,
                    tile_order_top_k=args.tile_order_top_k,
                    baseline_multiset_hash=baseline_multiset_hash,
                    baseline_order_hash=baseline_order_hash,
                    kernel_saved_us=args.kernel_saved_us,
                    extra={
                        "prior_path": str(prior_path),
                        "prior_score_name": prior.score_name,
                        "top_utility_override": top_h,
                    },
                )
            )

    report = {
        "ok": True,
        "schema_version": 1,
        "source": {"type": "input_jsonl", "path": str(args.input_jsonl)},
        "request_count": len(requests),
        "window_count": len({request.window_id for request in requests}),
        "priors": prior_metadata,
        "policies": rows,
        "config": {
            "cache_sizes": args.cache_sizes,
            "tile_order_top_k": args.tile_order_top_k,
            "repeat": args.repeat,
            "kernel_saved_us": args.kernel_saved_us,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))


if __name__ == "__main__":
    main()
