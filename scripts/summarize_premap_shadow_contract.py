#!/usr/bin/env python3
"""Verify premap-only runtime shadow contract artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mtp_expert_prefetch.runtime import aggregate_shadow_events, read_shadow_jsonl


VIOLATION_KEYS = [
    "premap_summary_payload_violation_count",
    "premap_summary_full_fetch_violation_count",
    "premap_summary_metadata_violation_count",
    "premap_summary_router_change_violation_count",
    "premap_summary_descriptor_order_change_violation_count",
    "premap_summary_ready_credit_violation_count",
    "premap_summary_error_count",
]

FORBIDDEN_EVENT_COUNT_KEYS = [
    "descriptor_order_summary_count",
    "descriptor_prelaunch_assertion_count",
    "full_fetch_count",
    "metadata_count",
    "outcome_count",
    "outcome_aggregate_count",
]


def summarize(path: Path) -> dict[str, Any]:
    rows = read_shadow_jsonl(path)
    aggregate = aggregate_shadow_events(rows)
    event_types = sorted({str(row.get("event_type")) for row in rows})
    non_premap_event_total = sum(
        1 for row in rows if str(row.get("event_type")) != "premap_summary"
    )
    violation_total = sum(int(aggregate.get(key, 0) or 0) for key in VIOLATION_KEYS)
    forbidden_total = sum(
        int(aggregate.get(key, 0) or 0) for key in FORBIDDEN_EVENT_COUNT_KEYS
    )
    premap_count = int(aggregate.get("premap_summary_count", 0) or 0)
    ok = (
        premap_count > 0
        and non_premap_event_total == 0
        and violation_total == 0
        and forbidden_total == 0
    )
    return {
        "ok": bool(ok),
        "shadow_jsonl": str(path),
        "event_types": event_types,
        "premap_summary_count": premap_count,
        "premap_summary_descriptor_count": int(
            aggregate.get("premap_summary_descriptor_count", 0) or 0
        ),
        "premap_summary_actual_bytes": int(
            aggregate.get("premap_summary_actual_bytes", 0) or 0
        ),
        "premap_summary_payload_bytes": int(
            aggregate.get("premap_summary_payload_bytes", 0) or 0
        ),
        "violation_total": int(violation_total),
        "forbidden_event_total": int(forbidden_total),
        "non_premap_event_total": int(non_premap_event_total),
        "violations": {
            key: int(aggregate.get(key, 0) or 0) for key in VIOLATION_KEYS
        },
        "forbidden_events": {
            key: int(aggregate.get(key, 0) or 0) for key in FORBIDDEN_EVENT_COUNT_KEYS
        },
        "aggregate": aggregate,
        "boundary": (
            "Premap-only shadow contract verifier. A passing artifact may record "
            "descriptor/address preparation, but must not record full payload "
            "movement, router mutation, descriptor_order execution, or ready credit."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Premap-only Shadow Contract Verification",
        "",
        payload["boundary"],
        "",
        "## Verdict",
        "",
        f"- ok: `{str(payload['ok']).lower()}`",
        f"- shadow_jsonl: `{payload['shadow_jsonl']}`",
        f"- event_types: `{', '.join(payload['event_types'])}`",
        "",
        "## Counts",
        "",
        f"- premap_summary_count: {payload['premap_summary_count']}",
        f"- premap_summary_descriptor_count: {payload['premap_summary_descriptor_count']}",
        f"- premap_summary_actual_bytes: {payload['premap_summary_actual_bytes']}",
        f"- premap_summary_payload_bytes: {payload['premap_summary_payload_bytes']}",
        f"- violation_total: {payload['violation_total']}",
        f"- forbidden_event_total: {payload['forbidden_event_total']}",
        f"- non_premap_event_total: {payload['non_premap_event_total']}",
        "",
        "## Violations",
        "",
    ]
    for key, value in payload["violations"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Forbidden Event Counts", ""])
    for key, value in payload["forbidden_events"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shadow_jsonl", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    payload = summarize(args.shadow_jsonl)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
