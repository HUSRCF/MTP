#!/usr/bin/env python3
"""Replay descriptor-order execution evidence onto online shadow events.

Online vLLM shadow intentionally keeps descriptor-order execution gated closed
unless it receives explicit same-multiset/checksum evidence.  The independent
HIP descriptor consumer can provide that evidence for a measured
device/tile/group configuration.  This script joins the two artifacts:

  runtime_shadow.jsonl descriptor_summary_min rows
  + descriptor_consumer_micro_runtime.json evidence rows
  -> replay gate allow/reason distribution

The input shadow log is not modified in place.  When requested, an enriched
JSONL is written with additional ``descriptor_order_gate_replay_*`` fields.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mtp_expert_prefetch.runtime.descriptor_order_gate import (  # noqa: E402
    DescriptorOrderRuntimeGate,
    load_descriptor_order_consumer_evidence,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-shadow-jsonl", type=Path, required=True)
    parser.add_argument("--consumer-report-json", type=Path, required=True)
    parser.add_argument("--gate-config", type=Path, required=True)
    parser.add_argument(
        "--evidence-policy",
        default="layer_prior_frequency_two_level",
        help="Consumer-report policy row that supplies execution evidence.",
    )
    parser.add_argument(
        "--cache-flush-elems",
        type=int,
        default=0,
        help="Select the consumer evidence cell with this cache flush setting.",
    )
    parser.add_argument(
        "--checksum-tolerance",
        type=float,
        default=0.0,
        help="Accept checksum deltas up to this value as parity evidence.",
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise TypeError(f"{path}:{line_number} is not a JSON object")
            rows.append(row)
    return rows


def _descriptor_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("event_type") in {"descriptor_summary_min", "summary"}
        and (
            "descriptor_group_plan_groups_per_cta" in row
            or "descriptor_order_gate_tile_elems" in row
        )
    ]


def _load_evidence(
    path: Path,
    *,
    policy: str,
    cache_flush_elems: int,
    checksum_tolerance: float,
) -> dict[tuple[int, int, int, int], dict[str, Any]]:
    return {
        key: value.as_dict()
        for key, value in load_descriptor_order_consumer_evidence(
            path,
            evidence_policy=policy,
            cache_flush_elems=cache_flush_elems,
            checksum_tolerance=checksum_tolerance,
        ).items()
    }


def _event_key(
    event: Mapping[str, Any],
    *,
    cache_flush_elems: int,
) -> tuple[int, int, int, int] | None:
    device = event.get("descriptor_order_gate_device")
    tile_elems = event.get("descriptor_order_gate_tile_elems")
    groups_per_cta = event.get("descriptor_group_plan_groups_per_cta")
    if device is None or tile_elems is None or groups_per_cta is None:
        return None
    return (
        int(device),
        int(tile_elems),
        int(groups_per_cta),
        int(cache_flush_elems),
    )


def _replay(
    rows: list[dict[str, Any]],
    *,
    gate: DescriptorOrderRuntimeGate,
    evidence: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
    cache_flush_elems: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    descriptor_rows = _descriptor_events(rows)
    enriched_rows: list[dict[str, Any]] = []
    replay_allow = Counter()
    replay_reason = Counter()
    original_allow = Counter()
    original_reason = Counter()
    evidence_found = 0
    missing_key_count = 0

    descriptor_by_id = {id(row): row for row in descriptor_rows}
    for row in rows:
        if id(row) not in descriptor_by_id:
            enriched_rows.append(dict(row))
            continue
        item = dict(row)
        original_allow[item.get("descriptor_order_gate_allow")] += 1
        original_reason[item.get("descriptor_order_gate_reason")] += 1
        key = _event_key(item, cache_flush_elems=cache_flush_elems)
        ev = evidence.get(key) if key is not None else None
        if key is None:
            missing_key_count += 1
        if ev is not None:
            evidence_found += 1
        decision = gate.decide(
            tile_elems=int(item.get("descriptor_order_gate_tile_elems", 0) or 0),
            groups_per_cta=int(item.get("descriptor_group_plan_groups_per_cta", 0) or 0),
            device=(
                int(item["descriptor_order_gate_device"])
                if item.get("descriptor_order_gate_device") is not None
                else None
            ),
            execution_mode=str(
                item.get("descriptor_order_execution_mode", gate.execution_mode)
            ),
            group_count=_optional_int(item.get("descriptor_group_plan_group_count")),
            avg_group_size=_optional_float(item.get("descriptor_group_plan_avg_group_size")),
            p95_group_size=_optional_float(item.get("descriptor_group_plan_p95_group_size")),
            max_group_size=_optional_int(item.get("descriptor_group_plan_max_group_size")),
            same_multiset=(
                bool(ev["same_multiset"]) if ev is not None else None
            ),
            checksum_delta=(
                float(ev["checksum_delta"])
                if ev is not None and ev.get("checksum_delta") is not None
                else None
            ),
        )
        replay_allow[decision.allow] += 1
        replay_reason[decision.reason] += 1
        item["descriptor_order_gate_replay_allow"] = bool(decision.allow)
        item["descriptor_order_gate_replay_reason"] = decision.reason
        item["descriptor_order_gate_replay_cache_flush_elems"] = int(cache_flush_elems)
        item["descriptor_order_gate_replay_evidence_found"] = ev is not None
        if ev is not None:
            item["descriptor_order_gate_replay_same_multiset"] = bool(ev["same_multiset"])
            item["descriptor_order_gate_replay_checksum_delta"] = ev["checksum_delta"]
            item["descriptor_order_gate_replay_speedup_median_vs_no_order"] = ev.get(
                "speedup_median_vs_no_order"
            )
        enriched_rows.append(item)

    report = {
        "descriptor_event_count": int(len(descriptor_rows)),
        "evidence_found_count": int(evidence_found),
        "missing_event_key_count": int(missing_key_count),
        "original_gate_allow_counts": _counter_dict(original_allow),
        "original_gate_reason_counts": _counter_dict(original_reason),
        "replay_gate_allow_counts": _counter_dict(replay_allow),
        "replay_gate_reason_counts": _counter_dict(replay_reason),
    }
    return enriched_rows, report


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _counter_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda kv: str(kv[0]))}


def _render(report: Mapping[str, Any]) -> str:
    lines = [
        "# Descriptor-Order Gate Evidence Replay",
        "",
        f"- Runtime shadow: `{report['runtime_shadow_jsonl']}`",
        f"- Consumer evidence: `{report['consumer_report_json']}`",
        f"- Gate config: `{report['gate_config']}`",
        f"- Evidence policy: `{report['evidence_policy']}`",
        f"- Cache flush elems: `{report['cache_flush_elems']}`",
        f"- Descriptor events: `{report['descriptor_event_count']}`",
        f"- Evidence found: `{report['evidence_found_count']}`",
        f"- Missing event keys: `{report['missing_event_key_count']}`",
        "",
        "## Gate Counts",
        "",
        f"- Original allow: `{report['original_gate_allow_counts']}`",
        f"- Original reason: `{report['original_gate_reason_counts']}`",
        f"- Replay allow: `{report['replay_gate_allow_counts']}`",
        f"- Replay reason: `{report['replay_gate_reason_counts']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    gate = DescriptorOrderRuntimeGate.from_config(args.gate_config, base_dir=REPO_ROOT)
    rows = _read_jsonl(args.runtime_shadow_jsonl)
    evidence = _load_evidence(
        args.consumer_report_json,
        policy=str(args.evidence_policy),
        cache_flush_elems=int(args.cache_flush_elems),
        checksum_tolerance=float(args.checksum_tolerance),
    )
    enriched, replay_report = _replay(
        rows,
        gate=gate,
        evidence=evidence,
        cache_flush_elems=int(args.cache_flush_elems),
    )
    report = {
        "runtime_shadow_jsonl": str(args.runtime_shadow_jsonl),
        "consumer_report_json": str(args.consumer_report_json),
        "gate_config": str(args.gate_config),
        "evidence_policy": str(args.evidence_policy),
        "cache_flush_elems": int(args.cache_flush_elems),
        "checksum_tolerance": float(args.checksum_tolerance),
        "evidence_cell_count": int(len(evidence)),
        **replay_report,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.output_jsonl is not None:
        args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.output_jsonl.open("w", encoding="utf-8") as handle:
            for row in enriched:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(_render(report), encoding="utf-8")
    print(_render(report))


if __name__ == "__main__":
    main()
