#!/usr/bin/env python3
"""Check the premap-only long-run audit gate.

The gate validates the read-only descriptor/address preparation contract.  It
does not claim payload prefetch or endpoint latency improvement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_EVENT_TYPES = {"premap_summary", "premap_consumer_mapping"}


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def check_summary(
    summary: dict[str, Any],
    *,
    max_capacity: int = 12_288,
    min_reuse_rate: float = 0.98,
) -> dict[str, Any]:
    event_counts = {
        str(key): int(value) for key, value in summary.get("event_counts", {}).items()
    }
    aggregate = summary.get("aggregate", {})
    failures: list[str] = []

    unknown_events = sorted(set(event_counts) - REQUIRED_EVENT_TYPES)
    missing_events = sorted(event for event in REQUIRED_EVENT_TYPES if event_counts.get(event, 0) <= 0)
    if unknown_events:
        failures.append(f"unexpected_event_types={unknown_events}")
    if missing_events:
        failures.append(f"missing_event_types={missing_events}")

    premap_count = _as_int(event_counts.get("premap_summary"))
    consumer_count = _as_int(event_counts.get("premap_consumer_mapping"))
    if premap_count != consumer_count:
        failures.append(
            f"premap_consumer_count_mismatch={premap_count}!={consumer_count}"
        )
    if _as_int(summary.get("row_count")) != premap_count + consumer_count:
        failures.append("row_count_does_not_match_event_counts")

    if _as_int(aggregate.get("premap_summary_payload_bytes")) != 0:
        failures.append("premap_payload_bytes_nonzero")
    if _as_int(aggregate.get("premap_address_evicted_count")) != 0:
        failures.append("premap_address_evicted_count_nonzero")
    if _as_float(aggregate.get("premap_address_eviction_pressure_mean")) != 0.0:
        failures.append("premap_address_eviction_pressure_nonzero")

    resident_count = _as_int(aggregate.get("premap_address_resident_count_max"))
    if resident_count > int(max_capacity):
        failures.append(f"resident_count_exceeds_capacity={resident_count}>{max_capacity}")
    if _as_float(aggregate.get("premap_address_reuse_rate_mean")) < float(min_reuse_rate):
        failures.append("premap_address_reuse_rate_below_threshold")

    for field in (
        "premap_consumer_address_hit_rate",
        "premap_consumer_descriptor_handle_hit_rate",
        "premap_consumer_real_descriptor_handle_hit_rate",
        "premap_consumer_lookup_after_prepare_rate",
    ):
        if _as_float(aggregate.get(field)) != 1.0:
            failures.append(f"{field}_not_one")

    if _as_int(
        aggregate.get("premap_consumer_real_descriptor_handle_binding_mismatch_count")
    ) != 0:
        failures.append("real_descriptor_handle_binding_mismatch_nonzero")
    if _as_int(aggregate.get("premap_consumer_error_count")) != 0:
        failures.append("premap_consumer_error_count_nonzero")

    metrics = {
        "row_count": _as_int(summary.get("row_count")),
        "premap_summary_count": premap_count,
        "premap_consumer_mapping_count": consumer_count,
        "premap_address_resident_count_max": resident_count,
        "premap_address_reuse_rate_mean": _as_float(
            aggregate.get("premap_address_reuse_rate_mean")
        ),
        "premap_address_eviction_pressure_mean": _as_float(
            aggregate.get("premap_address_eviction_pressure_mean")
        ),
        "premap_consumer_address_hit_rate": _as_float(
            aggregate.get("premap_consumer_address_hit_rate")
        ),
        "premap_consumer_real_descriptor_handle_hit_rate": _as_float(
            aggregate.get("premap_consumer_real_descriptor_handle_hit_rate")
        ),
    }
    return {
        "passed": not failures,
        "failures": failures,
        "metrics": metrics,
        "max_capacity": int(max_capacity),
        "min_reuse_rate": float(min_reuse_rate),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--max-capacity", type=int, default=12_288)
    parser.add_argument("--min-reuse-rate", type=float, default=0.98)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
    result = check_summary(
        summary,
        max_capacity=args.max_capacity,
        min_reuse_rate=args.min_reuse_rate,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
