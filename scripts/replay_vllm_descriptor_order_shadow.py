#!/usr/bin/env python3
"""Replay vLLM router traces with heldout-comparable descriptor-order windows."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from statistics import mean, median
from typing import Any, Sequence

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    TileRequest,
    aggregate_shadow_events,
    build_layer_tile_prior,
    evaluate_ordered_tile_requests,
    hash_layer_tile_prior,
    load_layer_tile_prior,
    order_tile_requests,
    order_tile_requests_with_layer_prior,
    read_shadow_jsonl,
)


DEFAULT_POLICIES = [
    "linear",
    "b_tile_grouped",
    "utility_tile_grouped_bucket",
    "layer_prior",
]


def parse_csv_ints(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--prior-json", type=Path, required=True)
    parser.add_argument("--prior-id", default=None)
    parser.add_argument(
        "--token-window-size",
        type=int,
        default=64,
        help=(
            "Token examples per layer/window. With topk=8, the default matches "
            "the heldout tile stream's 64*8=512 TileRequests per window."
        ),
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=None,
        help="Deprecated alias for --token-window-size.",
    )
    parser.add_argument("--topk", type=int, default=8)
    parser.add_argument("--tiles-per-expert", type=int, default=1)
    parser.add_argument("--cache-sizes", type=parse_csv_ints, default=[8, 16, 32])
    parser.add_argument("--tile-order-top-k", type=int, default=8)
    parser.add_argument("--policy", action="append", default=None)
    parser.add_argument("--top-utility-override", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--shadow-jsonl", type=Path, default=None)
    parser.add_argument("--heldout-json", type=Path, default=None)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument(
        "--calibration-sample-count",
        type=int,
        default=0,
        help=(
            "Optional vLLM-internal split: calibrate a layer-frequency prior on "
            "the first N sample ids and evaluate it on the remaining sample ids."
        ),
    )
    parser.add_argument("--calibrated-prior-output-json", type=Path, default=None)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("outputs/reports/tile_order_cache/vllm_descriptor_order_replay.json"),
    )
    parser.add_argument("--output-md", type=Path, default=None)
    return parser.parse_args()


def _stats(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": int(len(values)),
        "mean": float(mean(values)),
        "median": float(median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _sample_idx_from_payload(path: Path, payload: dict[str, Any], fallback: int) -> int:
    record = payload.get("record")
    if isinstance(record, dict):
        for key in ("sample_idx", "sample_id", "idx", "id"):
            value = record.get(key)
            if isinstance(value, int):
                return int(value)
            if isinstance(value, str) and value.isdigit():
                return int(value)
    stem = path.stem
    if stem.startswith("sample_"):
        suffix = stem.split("_", 1)[1]
        if suffix.isdigit():
            return int(suffix)
    return int(fallback)


def _module_call(
    payload: dict[str, Any],
    module_name: str,
    occurrence: int,
) -> tuple[Any, Any] | None:
    router_topk = payload.get("router_topk")
    router_weights = payload.get("router_weights")
    if not isinstance(router_topk, dict) or not isinstance(router_weights, dict):
        return None
    topk_calls = router_topk.get(module_name)
    weight_calls = router_weights.get(module_name)
    if not isinstance(topk_calls, list) or not isinstance(weight_calls, list):
        return None
    if occurrence >= len(topk_calls) or occurrence >= len(weight_calls):
        return None
    return topk_calls[occurrence], weight_calls[occurrence]


def load_vllm_tile_requests(
    trace_dir: Path,
    *,
    token_window_size: int,
    topk: int,
    tiles_per_expert: int,
) -> tuple[list[TileRequest], dict[str, Any]]:
    raw_requests: list[TileRequest] = []
    files = sorted(trace_dir.glob("sample_*.pt"))
    if not files:
        raise FileNotFoundError(f"no sample_*.pt files found under {trace_dir}")
    for sample_ordinal, path in enumerate(files):
        payload = torch.load(path, map_location="cpu")
        if not isinstance(payload, dict):
            continue
        sample_idx = _sample_idx_from_payload(path, payload, sample_ordinal)
        meta = payload.get("router_call_meta")
        if not isinstance(meta, list):
            continue
        occurrences: dict[str, int] = {}
        for row in sorted(meta, key=lambda item: int(item.get("call_index", 0))):
            if not isinstance(row, dict):
                continue
            layer_id = row.get("layer_id")
            module_name = row.get("module_name")
            if layer_id is None or not isinstance(module_name, str):
                continue
            occurrence = occurrences.get(module_name, 0)
            occurrences[module_name] = occurrence + 1
            call = _module_call(payload, module_name, occurrence)
            if call is None:
                continue
            ids = torch.as_tensor(call[0], dtype=torch.long)
            weights = torch.as_tensor(call[1], dtype=torch.float32)
            if ids.ndim != 2 or weights.shape != ids.shape:
                continue
            k = min(int(topk), int(ids.shape[1]))
            for token_idx in range(int(ids.shape[0])):
                for row_id in range(k):
                    expert = int(ids[token_idx, row_id].item())
                    if expert < 0:
                        continue
                    weight = float(weights[token_idx, row_id].item())
                    for tile_local in range(max(1, int(tiles_per_expert))):
                        tile_id = expert * int(tiles_per_expert) + int(tile_local)
                        raw_requests.append(
                            TileRequest(
                                window_id=0,
                                request_id=len(raw_requests),
                                tile_id=int(tile_id),
                                expert_id=int(expert),
                                transition_score=weight,
                                mtp_score=0.0,
                                utility_score=weight,
                                sample_idx=int(sample_idx),
                                token_index=int(token_idx),
                                layer_idx=int(layer_id),
                                row_id=int(row_id),
                                weight=weight,
                                source_policy="vllm_current_router_topk",
                            )
                        )
    layer_token_keys: dict[int, set[tuple[int | None, int | None]]] = {}
    for request in raw_requests:
        if request.layer_idx is None:
            continue
        layer_token_keys.setdefault(int(request.layer_idx), set()).add(
            (request.sample_idx, request.token_index)
        )
    windows_per_layer = (
        max(
            1,
            max(
                (len(keys) + int(token_window_size) - 1) // int(token_window_size)
                for keys in layer_token_keys.values()
            ),
        )
        if layer_token_keys
        else 1
    )
    positions_by_layer: dict[int, int] = {}
    token_positions_by_layer: dict[int, dict[tuple[int | None, int | None], int]] = {}
    requests: list[TileRequest] = []
    for request_id, request in enumerate(raw_requests):
        layer = int(request.layer_idx) if request.layer_idx is not None else -1
        token_key = (request.sample_idx, request.token_index)
        layer_positions = token_positions_by_layer.setdefault(layer, {})
        if token_key not in layer_positions:
            position = positions_by_layer.get(layer, 0)
            positions_by_layer[layer] = position + 1
            layer_positions[token_key] = position
        position = layer_positions[token_key]
        window_id = int(layer * windows_per_layer + position // int(token_window_size))
        requests.append(
            TileRequest(
                window_id=window_id,
                request_id=request_id,
                tile_id=int(request.tile_id),
                expert_id=int(request.expert_id),
                transition_score=float(request.transition_score),
                mtp_score=float(request.mtp_score),
                utility_score=float(request.utility_score),
                sample_idx=request.sample_idx,
                token_index=request.token_index,
                layer_idx=request.layer_idx,
                row_id=request.row_id,
                weight=request.weight,
                source_policy=request.source_policy,
            )
        )
    source = {
        "type": "vllm_trace_dir",
        "path": str(trace_dir),
        "sample_files": len(files),
        "token_window_size": int(token_window_size),
        "windows_per_layer": int(windows_per_layer),
        "topk": int(topk),
        "tiles_per_expert": int(tiles_per_expert),
    }
    return requests, source


def _time_order(build_fn: Any, repeat: int) -> tuple[list[TileRequest], dict[str, Any]]:
    ordered = build_fn()
    timings: list[float] = []
    for _ in range(max(1, int(repeat))):
        start_ns = time.perf_counter_ns()
        build_fn()
        timings.append((time.perf_counter_ns() - start_ns) / 1000.0)
    return ordered, _stats(timings)


def _row_for_policy(
    *,
    requests: Sequence[TileRequest],
    ordered: Sequence[TileRequest],
    policy: str,
    build_us: dict[str, Any],
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
) -> dict[str, Any]:
    metrics = evaluate_ordered_tile_requests(
        requests,
        ordered,
        policy=policy,
        cache_sizes=cache_sizes,
        tile_order_top_k=tile_order_top_k,
    )
    return {
        "policy": policy,
        "order_build_us": build_us,
        "metrics": metrics,
    }


def _heldout_reference(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = {}
    for row in payload.get("policies", []):
        policy = row.get("policy")
        if isinstance(policy, str):
            rows[policy] = {
                "metrics": row.get("metrics"),
                "order_build_us": row.get("order_build_us"),
            }
    return {
        "path": str(path),
        "request_count": payload.get("request_count"),
        "window_count": payload.get("window_count"),
        "policies": rows,
    }


def _shadow_reference(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    events = read_shadow_jsonl(path)
    aggregate = aggregate_shadow_events(events)
    descriptors = [event for event in events if event.get("descriptor_order_build_us") is not None]
    return {
        "path": str(path),
        "aggregate": aggregate,
        "descriptor_summary_count": len(descriptors),
        "descriptor_summary_event_keys": [
            event.get("shadow_event_id") for event in descriptors[:8]
        ],
    }


def _remap_windows(requests: Sequence[TileRequest], *, window_size: int) -> list[TileRequest]:
    layer_token_keys: dict[int, set[tuple[int | None, int | None]]] = {}
    for request in requests:
        if request.layer_idx is None:
            continue
        layer_token_keys.setdefault(int(request.layer_idx), set()).add(
            (request.sample_idx, request.token_index)
        )
    windows_per_layer = (
        max(
            1,
            max(
                (len(keys) + int(window_size) - 1) // int(window_size)
                for keys in layer_token_keys.values()
            ),
        )
        if layer_token_keys
        else 1
    )
    positions_by_layer: dict[int, int] = {}
    token_positions_by_layer: dict[int, dict[tuple[int | None, int | None], int]] = {}
    remapped: list[TileRequest] = []
    for request_id, request in enumerate(requests):
        layer = int(request.layer_idx) if request.layer_idx is not None else -1
        token_key = (request.sample_idx, request.token_index)
        layer_positions = token_positions_by_layer.setdefault(layer, {})
        if token_key not in layer_positions:
            position = positions_by_layer.get(layer, 0)
            positions_by_layer[layer] = position + 1
            layer_positions[token_key] = position
        position = layer_positions[token_key]
        remapped.append(
            TileRequest(
                window_id=int(layer * windows_per_layer + position // int(window_size)),
                request_id=int(request_id),
                tile_id=int(request.tile_id),
                expert_id=int(request.expert_id),
                transition_score=float(request.transition_score),
                mtp_score=float(request.mtp_score),
                utility_score=float(request.utility_score),
                sample_idx=request.sample_idx,
                token_index=request.token_index,
                layer_idx=request.layer_idx,
                row_id=request.row_id,
                weight=request.weight,
                source_policy=request.source_policy,
                split=request.split,
            )
        )
    return remapped


def _vllm_internal_calibration(
    requests: Sequence[TileRequest],
    *,
    calibration_sample_count: int,
    window_size: int,
    cache_sizes: Sequence[int],
    tile_order_top_k: int,
    repeat: int,
    calibrated_prior_output_json: Path | None,
) -> dict[str, Any] | None:
    if calibration_sample_count <= 0:
        return None
    sample_ids = sorted(
        {int(request.sample_idx) for request in requests if request.sample_idx is not None}
    )
    if len(sample_ids) <= calibration_sample_count:
        return {
            "ok": False,
            "reason": "not_enough_samples_for_heldout",
            "sample_count": len(sample_ids),
            "calibration_sample_count": int(calibration_sample_count),
        }
    calibration_ids = set(sample_ids[: int(calibration_sample_count)])
    heldout_ids = set(sample_ids[int(calibration_sample_count) :])
    calibration_requests = [
        request for request in requests if request.sample_idx is not None and int(request.sample_idx) in calibration_ids
    ]
    heldout_requests = _remap_windows(
        [
            request
            for request in requests
            if request.sample_idx is not None and int(request.sample_idx) in heldout_ids
        ],
        window_size=window_size,
    )
    if not calibration_requests or not heldout_requests:
        return {
            "ok": False,
            "reason": "empty_calibration_or_heldout",
            "calibration_request_count": len(calibration_requests),
            "heldout_request_count": len(heldout_requests),
        }
    prior = build_layer_tile_prior(
        calibration_requests,
        score_name="frequency",
        metadata={
            "source": "vllm_trace_internal_calibration",
            "calibration_sample_ids": sorted(calibration_ids),
            "heldout_sample_ids": sorted(heldout_ids),
            "window_size": int(window_size),
        },
    )
    if calibrated_prior_output_json is not None:
        from mtp_expert_prefetch.runtime import write_layer_tile_prior

        write_layer_tile_prior(prior, calibrated_prior_output_json)

    rows: list[dict[str, Any]] = []
    for policy, build_fn in (
        ("linear", lambda: list(heldout_requests)),
        ("b_tile_grouped", lambda: order_tile_requests(heldout_requests, policy="b_tile_grouped")),
        (
            "utility_tile_grouped_bucket",
            lambda: order_tile_requests(heldout_requests, policy="utility_tile_grouped_bucket"),
        ),
        (
            "vllm_calibrated_layer_prior_frequency",
            lambda: order_tile_requests_with_layer_prior(heldout_requests, prior=prior),
        ),
    ):
        ordered, build_us = _time_order(build_fn, repeat=repeat)
        rows.append(
            _row_for_policy(
                requests=heldout_requests,
                ordered=ordered,
                policy=policy,
                build_us=build_us,
                cache_sizes=cache_sizes,
                tile_order_top_k=tile_order_top_k,
            )
        )
    return {
        "ok": True,
        "calibration_sample_ids": sorted(calibration_ids),
        "heldout_sample_ids": sorted(heldout_ids),
        "calibration_request_count": int(len(calibration_requests)),
        "heldout_request_count": int(len(heldout_requests)),
        "heldout_window_count": int(len({request.window_id for request in heldout_requests})),
        "prior_hash": hash_layer_tile_prior(prior),
        "prior_output_json": (
            str(calibrated_prior_output_json) if calibrated_prior_output_json is not None else None
        ),
        "policies": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# vLLM Descriptor-Order Shadow Replay",
        "",
        "This rebuilds token/row TileRequests from vLLM router traces and applies",
        "the same 512-window descriptor-order metrics used by the heldout replay.",
        "",
        f"- Trace dir: `{report['source']['path']}`",
        f"- Requests: `{report['request_count']}`",
        f"- Windows: `{report['window_count']}`",
        f"- Unique B tiles: `{report['unique_tiles']}`",
        f"- Prior: `{report['prior']['path']}`",
        "",
        "| policy | build_us_median | LRU@8 | LRU@16 | reuse_mean | order_hit |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["policies"]:
        metrics = row["metrics"]
        lru = metrics["lru_hit_rate"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["policy"],
                    _fmt(row["order_build_us"]["median"]),
                    _fmt(lru.get("8")),
                    _fmt(lru.get("16")),
                    _fmt(metrics["reuse_distance"]["mean"]),
                    _fmt(metrics["tile_order_hit_rate"]),
                ]
            )
            + " |"
        )
    heldout = report.get("heldout_reference")
    if heldout:
        lines.extend(["", "## Heldout Reference", ""])
        for policy in ("layer_prior_frequency", "utility_tile_grouped_bucket", "linear"):
            row = heldout["policies"].get(policy)
            if not row:
                continue
            metrics = row["metrics"]
            lru = metrics["lru_hit_rate"]
            lines.append(
                f"- `{policy}`: LRU@8 `{_fmt(lru.get('8'))}`, "
                f"LRU@16 `{_fmt(lru.get('16'))}`, "
                f"reuse_mean `{_fmt(metrics['reuse_distance']['mean'])}`, "
                f"order_hit `{_fmt(metrics['tile_order_hit_rate'])}`"
            )
    shadow = report.get("online_shadow_summary")
    if shadow:
        aggregate = shadow["aggregate"]
        lines.extend(["", "## Online Shadow Summary", ""])
        lines.append(
            "- descriptor summaries: "
            f"`{shadow['descriptor_summary_count']}`, "
            f"LRU@8 mean `{_fmt(aggregate.get('descriptor_order_lru_at_8_mean'))}`, "
            f"LRU@16 mean `{_fmt(aggregate.get('descriptor_order_lru_at_16_mean'))}`, "
            f"order_hit mean `{_fmt(aggregate.get('descriptor_order_hit_rate_mean'))}`, "
            f"reuse_mean `{_fmt(aggregate.get('descriptor_reuse_distance_mean'))}`, "
            f"decision_us mean `{_fmt(aggregate.get('decision_us_mean'))}`, "
            "candidate_construction_us mean "
            f"`{_fmt(aggregate.get('candidate_construction_us_mean'))}`"
        )
    internal = report.get("vllm_internal_calibration")
    if internal:
        lines.extend(["", "## vLLM-Internal Calibration", ""])
        if not internal.get("ok"):
            lines.append(f"- skipped: `{internal.get('reason')}`")
        else:
            lines.append(
                f"- calibration samples: `{internal['calibration_sample_ids']}`, "
                f"heldout samples: `{internal['heldout_sample_ids']}`"
            )
            lines.append("")
            lines.append("| policy | LRU@8 | LRU@16 | reuse_mean | order_hit |")
            lines.append("|---|---:|---:|---:|---:|")
            for row in internal["policies"]:
                metrics = row["metrics"]
                lru = metrics["lru_hit_rate"]
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            row["policy"],
                            _fmt(lru.get("8")),
                            _fmt(lru.get("16")),
                            _fmt(metrics["reuse_distance"]["mean"]),
                            _fmt(metrics["tile_order_hit_rate"]),
                        ]
                    )
                    + " |"
                )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    token_window_size = int(args.window_size if args.window_size is not None else args.token_window_size)
    if token_window_size <= 0:
        raise ValueError("--token-window-size must be positive")
    requests, source = load_vllm_tile_requests(
        args.trace_dir,
        token_window_size=token_window_size,
        topk=args.topk,
        tiles_per_expert=args.tiles_per_expert,
    )
    if args.output_jsonl is not None:
        args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_jsonl.open("w", encoding="utf-8") as handle:
            for request in requests:
                handle.write(json.dumps(request.as_dict(), sort_keys=True) + "\n")
    prior = load_layer_tile_prior(args.prior_json)
    prior_hash = hash_layer_tile_prior(prior)
    prior_id = args.prior_id or str(prior.metadata.get("experiment_id") or prior.score_name)

    policies = args.policy or DEFAULT_POLICIES
    rows: list[dict[str, Any]] = []
    for policy in policies:
        if policy == "layer_prior":
            policy_name = f"layer_prior_{prior.score_name}"
            if args.top_utility_override:
                policy_name = f"{policy_name}_top{int(args.top_utility_override)}_utility_override"
            ordered, build_us = _time_order(
                lambda: order_tile_requests_with_layer_prior(
                    requests,
                    prior=prior,
                    top_utility_override=int(args.top_utility_override),
                ),
                repeat=args.repeat,
            )
        else:
            policy_name = policy
            ordered, build_us = _time_order(
                lambda policy=policy: order_tile_requests(requests, policy=policy),
                repeat=args.repeat,
            )
        rows.append(
            _row_for_policy(
                requests=requests,
                ordered=ordered,
                policy=policy_name,
                build_us=build_us,
                cache_sizes=args.cache_sizes,
                tile_order_top_k=args.tile_order_top_k,
            )
        )

    layer_counts = Counter(
        int(request.layer_idx) for request in requests if request.layer_idx is not None
    )
    report = {
        "ok": True,
        "schema_version": 1,
        "source": source,
        "request_count": int(len(requests)),
        "window_count": int(len({request.window_id for request in requests})),
        "unique_tiles": int(len({request.tile_id for request in requests})),
        "layer_count": int(len(layer_counts)),
        "layer_request_count_min": int(min(layer_counts.values())) if layer_counts else 0,
        "layer_request_count_max": int(max(layer_counts.values())) if layer_counts else 0,
        "prior": {
            "path": str(args.prior_json),
            "id": prior_id,
            "hash": prior_hash,
            "score_name": prior.score_name,
            "metadata": prior.metadata,
        },
        "policies": rows,
        "heldout_reference": _heldout_reference(args.heldout_json),
        "online_shadow_summary": _shadow_reference(args.shadow_jsonl),
        "vllm_internal_calibration": _vllm_internal_calibration(
            requests,
            calibration_sample_count=int(args.calibration_sample_count),
            window_size=int(token_window_size),
            cache_sizes=args.cache_sizes,
            tile_order_top_k=int(args.tile_order_top_k),
            repeat=int(args.repeat),
            calibrated_prior_output_json=args.calibrated_prior_output_json,
        ),
        "config": {
            "output_jsonl": str(args.output_jsonl) if args.output_jsonl is not None else None,
            "token_window_size": int(token_window_size),
            "topk": int(args.topk),
            "tiles_per_expert": int(args.tiles_per_expert),
            "cache_sizes": args.cache_sizes,
            "tile_order_top_k": int(args.tile_order_top_k),
            "repeat": int(args.repeat),
            "top_utility_override": int(args.top_utility_override),
        },
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
