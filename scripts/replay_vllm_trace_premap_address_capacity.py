#!/usr/bin/env python3
"""Replay current-router premap address capacity from vLLM trace samples.

This reuses the vLLM trace contract directly: each router_call_meta entry is one
online premap event, and each event prepares one descriptor/address handle per
unique routed expert in that token/layer call.  It therefore preserves the
token/layer stream shape used by online shadow counters, unlike the offline
sample/layer descriptor artifact replay.
"""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
import sys
from typing import Any

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    ControlledPremapAddressManager,
    ExpertPrefetchDescriptor,
    prepare_premap_address_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_jsonl", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--capacity",
        type=str,
        nargs="+",
        required=True,
        help="Address-cache capacities to sweep. Use 'unbounded' for no cap.",
    )
    parser.add_argument("--descriptor-bytes", type=int, default=4_096)
    parser.add_argument("--address-namespace", default="expert_weight_descriptor")
    parser.add_argument("--limit-samples", type=int)
    parser.add_argument(
        "--fast-address-only",
        action="store_true",
        help=(
            "Use a single-pass LRU address replay over (layer, expert) keys. "
            "This skips PremapPreparedPlan hashing and is intended for capacity sweeps."
        ),
    )
    return parser.parse_args()


def _parse_capacity(value: str) -> int | None:
    normalized = str(value).strip().lower()
    if normalized in {"none", "inf", "infinite", "unbounded"}:
        return None
    return int(normalized)


def _load_manifest(path: Path, *, limit_samples: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.expanduser().open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit_samples is not None and len(rows) >= int(limit_samples):
                break
    return rows


def _event_descriptors_from_sample(
    sample_path: Path,
    *,
    sample_idx: int,
    source: str,
) -> list[list[ExpertPrefetchDescriptor]]:
    sample = torch.load(sample_path, map_location="cpu")
    router_topk = sample["router_topk"]
    router_weights = sample.get("router_weights", {})
    call_meta = sample["router_call_meta"]
    per_module_call_index: dict[str, int] = {}
    events: list[list[ExpertPrefetchDescriptor]] = []
    for meta in call_meta:
        module_name = str(meta["module_name"])
        layer_idx = int(meta["layer_id"])
        local_call_idx = int(per_module_call_index.get(module_name, 0))
        per_module_call_index[module_name] = local_call_idx + 1
        topk_rows = router_topk[module_name][local_call_idx]
        weight_rows = router_weights.get(module_name, [None] * (local_call_idx + 1))[
            local_call_idx
        ]
        expert_scores: dict[int, float] = {}
        for row_idx, expert_row in enumerate(topk_rows):
            weights = (
                weight_rows[row_idx]
                if weight_rows is not None and row_idx < len(weight_rows)
                else None
            )
            for expert_pos, expert in enumerate(expert_row):
                expert_id = int(expert)
                score = 0.0
                if weights is not None and expert_pos < len(weights):
                    score = float(weights[expert_pos])
                expert_scores[expert_id] = max(float(expert_scores.get(expert_id, 0.0)), score)
        events.append(
            [
                ExpertPrefetchDescriptor(
                    sample_idx=int(sample_idx),
                    layer_idx=layer_idx,
                    expert_id=expert_id,
                    priority=2,
                    source=source,
                    score=score,
                )
                for expert_id, score in sorted(expert_scores.items())
            ]
        )
    return events


def _event_address_keys_from_sample(sample_path: Path) -> list[list[tuple[int, int]]]:
    sample = torch.load(sample_path, map_location="cpu")
    router_topk = sample["router_topk"]
    call_meta = sample["router_call_meta"]
    per_module_call_index: dict[str, int] = {}
    events: list[list[tuple[int, int]]] = []
    for meta in call_meta:
        module_name = str(meta["module_name"])
        layer_idx = int(meta["layer_id"])
        local_call_idx = int(per_module_call_index.get(module_name, 0))
        per_module_call_index[module_name] = local_call_idx + 1
        topk_rows = router_topk[module_name][local_call_idx]
        expert_ids = sorted({int(expert) for row in topk_rows for expert in row})
        events.append([(layer_idx, expert_id) for expert_id in expert_ids])
    return events


def _load_address_events(
    manifest_rows: list[dict[str, Any]],
    *,
    trace_dir: Path,
) -> list[list[tuple[int, int]]]:
    events: list[list[tuple[int, int]]] = []
    for row in manifest_rows:
        events.extend(_event_address_keys_from_sample(trace_dir / str(row["path"])))
    return events


def _fast_replay_capacities(
    events: list[list[tuple[int, int]]],
    *,
    capacities: list[int | None],
    descriptor_bytes: int,
) -> list[dict[str, Any]]:
    states: dict[int | None, OrderedDict[tuple[int, int], None]] = {
        capacity: OrderedDict() for capacity in capacities
    }
    counters: dict[int | None, dict[str, int]] = {
        capacity: {
            "new": 0,
            "reused": 0,
            "evicted": 0,
            "max_resident": 0,
        }
        for capacity in capacities
    }
    descriptor_count = 0
    for event in events:
        descriptor_count += len(event)
        for capacity in capacities:
            state = states[capacity]
            count = counters[capacity]
            for key in event:
                if key in state:
                    count["reused"] += 1
                    state.move_to_end(key)
                    continue
                count["new"] += 1
                state[key] = None
                if capacity is not None:
                    while len(state) > int(capacity):
                        state.popitem(last=False)
                        count["evicted"] += 1
                count["max_resident"] = max(count["max_resident"], len(state))
    reports: list[dict[str, Any]] = []
    for capacity in capacities:
        state = states[capacity]
        count = counters[capacity]
        new_count = int(count["new"])
        evicted = int(count["evicted"])
        reports.append(
            {
                "capacity": capacity,
                "event_count": len(events),
                "descriptor_count": descriptor_count,
                "new_address_count": new_count,
                "reused_address_count": int(count["reused"]),
                "reuse_rate": (
                    float(count["reused"]) / float(descriptor_count)
                    if descriptor_count
                    else 0.0
                ),
                "evicted_address_count": evicted,
                "eviction_pressure": (
                    float(evicted) / float(max(1, new_count)) if new_count else 0.0
                ),
                "resident_address_count": len(state),
                "resident_descriptor_bytes": len(state) * int(descriptor_bytes),
                "prepared_descriptor_actual_bytes": descriptor_count
                * int(descriptor_bytes),
                "payload_bytes": 0,
                "max_resident_address_count": int(count["max_resident"]),
                "max_resident_descriptor_bytes": int(count["max_resident"])
                * int(descriptor_bytes),
            }
        )
    return reports


def _replay(
    events: list[list[ExpertPrefetchDescriptor]],
    *,
    capacity: int | None,
    descriptor_bytes: int,
    address_namespace: str,
) -> dict[str, Any]:
    manager = ControlledPremapAddressManager(capacity=capacity)
    max_resident_address_count = 0
    max_resident_descriptor_bytes = 0
    for event in events:
        plan = prepare_premap_address_plan(
            event,
            descriptor_bytes=int(descriptor_bytes),
            address_namespace=str(address_namespace),
        )
        snapshot = manager.prepare(plan)
        max_resident_address_count = max(
            max_resident_address_count,
            int(snapshot.resident_address_count),
        )
        max_resident_descriptor_bytes = max(
            max_resident_descriptor_bytes,
            int(snapshot.resident_descriptor_bytes),
        )
    final = manager.snapshot()
    descriptor_count = int(final.prepared_record_count)
    reuse_rate = (
        float(final.reused_address_count) / float(descriptor_count)
        if descriptor_count
        else 0.0
    )
    eviction_pressure = (
        float(final.evicted_address_count) / float(max(1, final.new_address_count))
        if int(final.new_address_count) > 0
        else 0.0
    )
    return {
        "capacity": capacity,
        "event_count": len(events),
        "descriptor_count": descriptor_count,
        "new_address_count": int(final.new_address_count),
        "reused_address_count": int(final.reused_address_count),
        "reuse_rate": reuse_rate,
        "evicted_address_count": int(final.evicted_address_count),
        "eviction_pressure": eviction_pressure,
        "resident_address_count": int(final.resident_address_count),
        "resident_descriptor_bytes": int(final.resident_descriptor_bytes),
        "prepared_descriptor_actual_bytes": int(final.prepared_descriptor_actual_bytes),
        "payload_bytes": int(final.payload_bytes),
        "max_resident_address_count": max_resident_address_count,
        "max_resident_descriptor_bytes": max_resident_descriptor_bytes,
    }


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# vLLM Trace Premap Address Capacity Replay",
        "",
        "Boundary: current-router descriptor/address preparation only. No payload transfer.",
        "",
        f"- manifest: `{summary['manifest_jsonl']}`",
        f"- samples: `{summary['sample_count']}`",
        f"- events: `{summary['event_count']}`",
        f"- descriptors: `{summary['descriptor_count']}`",
        f"- descriptor bytes: `{summary['descriptor_bytes']}`",
        f"- payload bytes: `0` by contract",
        "",
        "| capacity | events | descriptors | reuse_rate | resident_addr | resident_MB | max_resident_MB | evicted | eviction_pressure | payload_bytes |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["reports"]:
        capacity = row["capacity"] if row["capacity"] is not None else "unbounded"
        resident_mb = float(row["resident_descriptor_bytes"]) / 1024.0 / 1024.0
        max_resident_mb = float(row["max_resident_descriptor_bytes"]) / 1024.0 / 1024.0
        lines.append(
            "| "
            f"{capacity} | "
            f"{row['event_count']} | "
            f"{row['descriptor_count']} | "
            f"{float(row['reuse_rate']):.6f} | "
            f"{row['resident_address_count']} | "
            f"{resident_mb:.3f} | "
            f"{max_resident_mb:.3f} | "
            f"{row['evicted_address_count']} | "
            f"{float(row['eviction_pressure']):.6f} | "
            f"{row['payload_bytes']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest_jsonl.expanduser()
    manifest_rows = _load_manifest(manifest_path, limit_samples=args.limit_samples)
    trace_dir = manifest_path.parent
    capacities = [_parse_capacity(capacity) for capacity in args.capacity]
    if args.fast_address_only:
        address_events = _load_address_events(manifest_rows, trace_dir=trace_dir)
        reports = _fast_replay_capacities(
            address_events,
            capacities=capacities,
            descriptor_bytes=int(args.descriptor_bytes),
        )
        event_count = len(address_events)
        descriptor_count = sum(len(event) for event in address_events)
        replay_mode = "fast_address_only"
    else:
        events: list[list[ExpertPrefetchDescriptor]] = []
        for row in manifest_rows:
            sample_idx = int(row["sample_idx"])
            sample_path = trace_dir / str(row["path"])
            events.extend(
                _event_descriptors_from_sample(
                    sample_path,
                    sample_idx=sample_idx,
                    source="current_router_topk_premap_shadow",
                )
            )
        reports = [
            _replay(
                events,
                capacity=capacity,
                descriptor_bytes=int(args.descriptor_bytes),
                address_namespace=str(args.address_namespace),
            )
            for capacity in capacities
        ]
        event_count = len(events)
        descriptor_count = sum(len(event) for event in events)
        replay_mode = "prepared_plan"
    summary = {
        "ok": True,
        "manifest_jsonl": str(manifest_path),
        "sample_count": len(manifest_rows),
        "event_count": event_count,
        "descriptor_count": descriptor_count,
        "descriptor_bytes": int(args.descriptor_bytes),
        "address_namespace": str(args.address_namespace),
        "replay_mode": replay_mode,
        "reports": reports,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(_render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
