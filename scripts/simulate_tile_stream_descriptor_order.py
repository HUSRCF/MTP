#!/usr/bin/env python3
"""Apply descriptor-order shadow summaries to token/row tile streams."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from statistics import mean, median
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    OnlineShadowLogger,
    ShadowEventId,
    ShadowPolicyConfig,
    aggregate_shadow_events,
    load_tile_requests_jsonl,
    order_tile_requests,
    order_tile_request_stream,
    read_shadow_jsonl,
    tile_requests_from_tensor_cache,
)


DEFAULT_POLICIES = [
    "linear",
    "b_tile_grouped",
    "utility_hot_first",
    "utility_tile_grouped",
    "oracle_cache_aware",
]


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
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--tensor-window-size", type=int, default=64)
    parser.add_argument("--tensor-topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--tensor-max-examples", type=int, default=None)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_stream_descriptor_order.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/tile_stream_descriptor_order.md"),
    )
    parser.add_argument("--shadow-jsonl", type=Path, default=None)
    return parser.parse_args()


def stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": float(mean(values)),
        "median": float(median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


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


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tile-Stream Descriptor-Order Shadow",
        "",
        "This report applies descriptor-order policies to the same token/row-level",
        "tile stream used by the simulator and timing bench. It changes order only,",
        "not the descriptor multiset or true-router demand.",
        "",
        f"- Requests: `{report['request_count']}`",
        f"- Source: `{report['source']}`",
        f"- Repeat: `{report['config']['repeat']}`",
        "",
        "| policy | build_us_median | LRU@8 | LRU@16 | reuse_mean | order_hit | same_multiset | order_changed | multiset_hash | order_hash |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for row in report["policies"]:
        metrics = row["metrics"]
        lru = metrics["lru_hit_rate"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["policy"],
                    fmt(row["order_build_us"]["median"]),
                    fmt(lru.get("8")),
                    fmt(lru.get("16")),
                    fmt(metrics["reuse_distance"]["mean"]),
                    fmt(metrics["tile_order_hit_rate"]),
                    str(row["same_multiset"]),
                    str(row["order_changed"]),
                    row["tile_multiset_hash"][:12],
                    row["order_hash"][:12],
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
    requests, source = load_requests(args)
    policies = args.policy or DEFAULT_POLICIES

    rows: list[dict[str, Any]] = []
    reports_by_policy = {}
    ordered_by_policy = {}
    for policy in policies:
        ordered, descriptor_report = order_tile_request_stream(
            requests,
            policy=policy,
            cache_sizes=args.cache_sizes,
            tile_order_top_k=args.tile_order_top_k,
            seed=args.seed,
        )
        reports_by_policy[policy] = descriptor_report
        ordered_by_policy[policy] = ordered

    baseline = reports_by_policy.get("linear")
    baseline_multiset_hash = baseline.tile_multiset_hash if baseline is not None else None
    baseline_order_hash = baseline.order_hash if baseline is not None else None

    for policy in policies:
        report = reports_by_policy[policy]
        build_values = []
        for _ in range(args.repeat):
            start_ns = time.perf_counter_ns()
            order_tile_requests(requests, policy=policy, seed=args.seed)
            build_values.append((time.perf_counter_ns() - start_ns) / 1000.0)
        rows.append(
            {
                **report.as_dict(),
                "order_build_us": stats(build_values),
                "same_multiset": (
                    report.tile_multiset_hash == baseline_multiset_hash
                    if baseline_multiset_hash is not None
                    else True
                ),
                "order_changed": (
                    report.order_hash != baseline_order_hash
                    if baseline_order_hash is not None
                    else None
                ),
                "ordered_preview": [item.as_dict() for item in ordered_by_policy[policy][:8]],
            }
        )

    report_payload = {
        "ok": True,
        "schema_version": 1,
        "source": source,
        "request_count": len(requests),
        "policies": rows,
        "config": {
            "policies": policies,
            "cache_sizes": args.cache_sizes,
            "tile_order_top_k": args.tile_order_top_k,
            "repeat": args.repeat,
            "seed": args.seed,
        },
    }

    if args.shadow_jsonl is not None:
        if args.shadow_jsonl.exists():
            args.shadow_jsonl.unlink()
        with OnlineShadowLogger(args.shadow_jsonl, flush_every=64) as logger:
            for index, policy_name in enumerate(policies):
                descriptor_report = reports_by_policy[policy_name]
                policy = ShadowPolicyConfig(
                    policy_mode="descriptor_order_shadow",
                    optimization_goal="cache_locality",
                    action_keep_fraction=0.0,
                    metadata_score_ratio=0.0,
                    full_fetch_max_extra=0,
                    metadata_max_extra=0,
                    premap_max_extra=0,
                    descriptor_order_policy=policy_name,
                )
                logger.write_descriptor_order_summary(
                    event_id=ShadowEventId(
                        request_id="tile_stream_descriptor_order",
                        sequence_id=0,
                        token_index=index,
                        layer=0,
                    ),
                    policy=policy,
                    descriptor_report=descriptor_report,
                    baseline_order_hash=baseline_order_hash,
                )
        report_payload["shadow_jsonl"] = str(args.shadow_jsonl)
        report_payload["shadow_aggregate"] = aggregate_shadow_events(
            read_shadow_jsonl(args.shadow_jsonl)
        )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report_payload), encoding="utf-8")
    print(render_markdown(report_payload))


if __name__ == "__main__":
    main()
