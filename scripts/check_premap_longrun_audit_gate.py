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
    require_readonly_consumer: bool = False,
    require_descriptor_prep: bool = False,
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

    required_rate_fields = [
        "premap_consumer_address_hit_rate",
        "premap_consumer_descriptor_handle_hit_rate",
        "premap_consumer_real_descriptor_handle_hit_rate",
        "premap_consumer_lookup_after_prepare_rate",
    ]
    readonly_fields_present = any(
        key in aggregate
        for key in (
            "premap_consumer_readonly_lookup_count",
            "premap_consumer_readonly_handle_hit_rate",
            "premap_consumer_readonly_handle_parity_ok_rate",
            "premap_consumer_readonly_evicted_before_consume_count",
            "premap_consumer_readonly_stale_handle_count",
        )
    )
    if require_readonly_consumer or readonly_fields_present:
        required_rate_fields.extend(
            [
                "premap_consumer_readonly_handle_hit_rate",
                "premap_consumer_readonly_handle_parity_ok_rate",
            ]
        )
    for field in required_rate_fields:
        if _as_float(aggregate.get(field)) != 1.0:
            failures.append(f"{field}_not_one")

    if _as_int(
        aggregate.get("premap_consumer_real_descriptor_handle_binding_mismatch_count")
    ) != 0:
        failures.append("real_descriptor_handle_binding_mismatch_nonzero")
    for field in (
        "premap_consumer_payload_violation_count",
        "premap_consumer_router_change_violation_count",
        "premap_consumer_descriptor_order_change_violation_count",
        "premap_consumer_ready_credit_violation_count",
    ):
        count = _as_int(aggregate.get(field))
        if count != 0:
            failures.append(f"{field}_nonzero={count}")
    if require_readonly_consumer and not readonly_fields_present:
        failures.append("readonly_consumer_fields_missing")
    if require_readonly_consumer or readonly_fields_present:
        if _as_int(aggregate.get("premap_consumer_readonly_lookup_count")) <= 0:
            failures.append("readonly_lookup_count_missing_or_zero")
        if _as_int(aggregate.get("premap_consumer_readonly_evicted_before_consume_count")) != 0:
            failures.append("readonly_evicted_before_consume_nonzero")
        if _as_int(aggregate.get("premap_consumer_readonly_stale_handle_count")) != 0:
            failures.append("readonly_stale_handle_nonzero")

    descriptor_prep_active = any(
        _as_int(aggregate.get(key)) > 0
        for key in (
            "premap_consumer_descriptor_prep_attempted_count",
            "premap_consumer_descriptor_prep_executed_count",
            "premap_consumer_descriptor_prep_lookup_count",
            "premap_consumer_descriptor_prep_handle_count",
            "premap_consumer_descriptor_prep_blocked_count",
        )
    )
    if require_descriptor_prep and not descriptor_prep_active:
        failures.append("descriptor_prep_fields_missing")
    if require_descriptor_prep or descriptor_prep_active:
        attempted = _as_int(
            aggregate.get("premap_consumer_descriptor_prep_attempted_count")
        )
        executed = _as_int(
            aggregate.get("premap_consumer_descriptor_prep_executed_count")
        )
        lookup_count = _as_int(
            aggregate.get("premap_consumer_descriptor_prep_lookup_count")
        )
        handle_count = _as_int(
            aggregate.get("premap_consumer_descriptor_prep_handle_count")
        )
        missing_count = _as_int(
            aggregate.get("premap_consumer_descriptor_prep_missing_handle_count")
        )
        if attempted <= 0:
            failures.append("descriptor_prep_attempted_count_missing_or_zero")
        if attempted != consumer_count:
            failures.append(
                f"descriptor_prep_attempted_count_mismatch={attempted}!={consumer_count}"
            )
        if executed != attempted:
            failures.append(f"descriptor_prep_executed_count_mismatch={executed}!={attempted}")
        if lookup_count <= 0:
            failures.append("descriptor_prep_lookup_count_missing_or_zero")
        if missing_count != 0:
            failures.append(f"descriptor_prep_missing_handle_count_nonzero={missing_count}")
        if handle_count != lookup_count:
            failures.append(f"descriptor_prep_handle_count_mismatch={handle_count}!={lookup_count}")
        for field in (
            "premap_consumer_descriptor_prep_handle_hit_rate",
            "premap_consumer_descriptor_prep_execution_ok_rate",
            "premap_consumer_descriptor_prep_execution_ok_attempted_rate",
        ):
            if _as_float(aggregate.get(field)) != 1.0:
                failures.append(f"{field}_not_one")
        if _as_int(aggregate.get("premap_consumer_descriptor_prep_blocked_count")) != 0:
            failures.append("descriptor_prep_blocked_count_nonzero")
        if _as_float(
            aggregate.get("premap_consumer_descriptor_prep_blocked_attempted_rate")
        ) != 0.0:
            failures.append("descriptor_prep_blocked_attempted_rate_nonzero")
        for field in (
            "premap_consumer_descriptor_prep_descriptor_ptr_count",
            "premap_consumer_descriptor_prep_packed_weight_descriptor_count",
            "premap_consumer_descriptor_prep_scale_metadata_handle_count",
        ):
            if _as_int(aggregate.get(field)) != lookup_count:
                failures.append(f"{field}_mismatch={_as_int(aggregate.get(field))}!={lookup_count}")
    real_handle_hits = _as_int(
        aggregate.get("premap_consumer_real_descriptor_handle_hit_count")
    )
    if real_handle_hits <= 0:
        failures.append("real_descriptor_handle_hit_count_missing_or_zero")
    for source in ("packed_weight", "scale_metadata", "aux_metadata"):
        hit_count = _as_int(
            aggregate.get(f"premap_consumer_real_descriptor_handle_{source}_hit_count")
        )
        miss_count = _as_int(
            aggregate.get(f"premap_consumer_real_descriptor_handle_{source}_miss_count")
        )
        if hit_count != real_handle_hits:
            failures.append(
                f"real_descriptor_handle_{source}_hit_count_mismatch="
                f"{hit_count}!={real_handle_hits}"
            )
        if miss_count != 0:
            failures.append(
                f"real_descriptor_handle_{source}_miss_count_nonzero={miss_count}"
            )
    for reason in (
        "resolver_disabled",
        "consumer_layer_missing",
        "expert_map_miss",
        "no_handle_parts",
    ):
        count = _as_int(
            aggregate.get(f"premap_consumer_real_descriptor_handle_{reason}_count")
        )
        if count != 0:
            failures.append(
                f"real_descriptor_handle_{reason}_count_nonzero={count}"
            )
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
        "premap_consumer_real_descriptor_handle_hit_count": real_handle_hits,
        "premap_consumer_real_descriptor_handle_packed_weight_hit_count": _as_int(
            aggregate.get("premap_consumer_real_descriptor_handle_packed_weight_hit_count")
        ),
        "premap_consumer_real_descriptor_handle_scale_metadata_hit_count": _as_int(
            aggregate.get("premap_consumer_real_descriptor_handle_scale_metadata_hit_count")
        ),
        "premap_consumer_real_descriptor_handle_aux_metadata_hit_count": _as_int(
            aggregate.get("premap_consumer_real_descriptor_handle_aux_metadata_hit_count")
        ),
        "premap_consumer_readonly_lookup_count": _as_int(
            aggregate.get("premap_consumer_readonly_lookup_count")
        ),
        "premap_consumer_readonly_handle_hit_rate": _as_float(
            aggregate.get("premap_consumer_readonly_handle_hit_rate")
        ),
        "premap_consumer_readonly_evicted_before_consume_count": _as_int(
            aggregate.get("premap_consumer_readonly_evicted_before_consume_count")
        ),
        "premap_consumer_readonly_stale_handle_count": _as_int(
            aggregate.get("premap_consumer_readonly_stale_handle_count")
        ),
        "premap_consumer_readonly_handle_parity_ok_rate": _as_float(
            aggregate.get("premap_consumer_readonly_handle_parity_ok_rate")
        ),
        "premap_consumer_descriptor_prep_attempted_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_attempted_count")
        ),
        "premap_consumer_descriptor_prep_executed_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_executed_count")
        ),
        "premap_consumer_descriptor_prep_lookup_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_lookup_count")
        ),
        "premap_consumer_descriptor_prep_handle_hit_rate": _as_float(
            aggregate.get("premap_consumer_descriptor_prep_handle_hit_rate")
        ),
        "premap_consumer_descriptor_prep_execution_ok_attempted_rate": _as_float(
            aggregate.get("premap_consumer_descriptor_prep_execution_ok_attempted_rate")
        ),
        "premap_consumer_descriptor_prep_blocked_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_blocked_count")
        ),
        "premap_consumer_descriptor_prep_blocked_attempted_rate": _as_float(
            aggregate.get("premap_consumer_descriptor_prep_blocked_attempted_rate")
        ),
    }
    return {
        "passed": not failures,
        "failures": failures,
        "metrics": metrics,
        "max_capacity": int(max_capacity),
        "min_reuse_rate": float(min_reuse_rate),
        "require_readonly_consumer": bool(require_readonly_consumer),
        "require_descriptor_prep": bool(require_descriptor_prep),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--max-capacity", type=int, default=12_288)
    parser.add_argument("--min-reuse-rate", type=float, default=0.98)
    parser.add_argument(
        "--require-readonly-consumer",
        action="store_true",
        help=(
            "Require readonly-consumer lifecycle counters.  Leave disabled "
            "when checking legacy summaries that predate these fields."
        ),
    )
    parser.add_argument(
        "--require-descriptor-prep",
        action="store_true",
        help=(
            "Require readonly-gated descriptor/address prep execution counters. "
            "This is the stricter lab gate used before real descriptor/address "
            "prep integration."
        ),
    )
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
    result = check_summary(
        summary,
        max_capacity=args.max_capacity,
        min_reuse_rate=args.min_reuse_rate,
        require_readonly_consumer=args.require_readonly_consumer,
        require_descriptor_prep=args.require_descriptor_prep,
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
