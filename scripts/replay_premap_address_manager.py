#!/usr/bin/env python3
"""Replay premap descriptor/address preparation through a bounded address shim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import (  # noqa: E402
    group_premap_descriptors_by_sample_layer,
    load_premap_descriptor_jsonl,
    replay_premap_address_manager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("descriptors_jsonl", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--capacity",
        type=str,
        nargs="+",
        required=True,
        help="Address-cache capacities to sweep. Use 'unbounded' for no capacity limit.",
    )
    parser.add_argument("--descriptor-bytes", type=int, default=4_096)
    parser.add_argument("--address-namespace", default="expert_weight_descriptor")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    descriptors = load_premap_descriptor_jsonl(args.descriptors_jsonl)
    groups = group_premap_descriptors_by_sample_layer(descriptors)
    capacities = [_parse_capacity(value) for value in args.capacity]
    reports = [
        replay_premap_address_manager(
            groups,
            capacity=capacity,
            descriptor_bytes=int(args.descriptor_bytes),
            address_namespace=str(args.address_namespace),
        ).as_dict()
        for capacity in capacities
    ]
    summary = {
        "ok": True,
        "descriptors_jsonl": str(args.descriptors_jsonl),
        "descriptor_bytes": int(args.descriptor_bytes),
        "address_namespace": str(args.address_namespace),
        "event_count": len(groups),
        "descriptor_count": len(descriptors),
        "reports": reports,
        "best_reuse_rate": max((float(row["reuse_rate"]) for row in reports), default=0.0),
        "min_eviction_pressure": min(
            (float(row["eviction_pressure"]) for row in reports),
            default=0.0,
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(_render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


def _parse_capacity(value: str) -> int | None:
    normalized = str(value).strip().lower()
    if normalized in {"none", "inf", "infinite", "unbounded"}:
        return None
    return int(normalized)


def _render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Premap Address Manager Replay",
        "",
        "Boundary: descriptor/address preparation only. Payload bytes must remain zero.",
        "",
        f"- descriptors: `{summary['descriptors_jsonl']}`",
        f"- descriptor bytes: `{summary['descriptor_bytes']}`",
        f"- events: `{summary['event_count']}`",
        f"- descriptors: `{summary['descriptor_count']}`",
        f"- best reuse rate: `{float(summary['best_reuse_rate']):.6f}`",
        f"- min eviction pressure: `{float(summary['min_eviction_pressure']):.6f}`",
        "- payload bytes: `0` by contract; this replay prepares descriptor/address handles only.",
        "",
        "| capacity | events | descriptors | reuse_rate | resident_addr | resident_bytes | max_resident_bytes | evicted | eviction_pressure | payload_bytes |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["reports"]:  # type: ignore[index]
        capacity = row["capacity"] if row["capacity"] is not None else "unbounded"
        lines.append(
            "| "
            f"{capacity} | "
            f"{row['event_count']} | "
            f"{row['descriptor_count']} | "
            f"{float(row['reuse_rate']):.6f} | "
            f"{row['resident_address_count']} | "
            f"{row['resident_descriptor_bytes']} | "
            f"{row['max_resident_descriptor_bytes']} | "
            f"{row['evicted_address_count']} | "
            f"{float(row['eviction_pressure']):.6f} | "
            f"{row['payload_bytes']} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
