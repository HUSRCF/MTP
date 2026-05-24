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

from mtp_expert_prefetch.runtime import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
)


REQUIRED_EVENT_TYPES = {"premap_summary", "premap_consumer_mapping"}
EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT = len(
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
)


def _normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Accept both longrun audit summaries and trace performance summaries."""
    if "aggregate" in summary and "event_counts" in summary:
        return summary
    aggregate = summary.get("runtime_shadow_aggregate")
    if not isinstance(aggregate, dict):
        return summary
    event_counts = {
        "premap_summary": _as_int(aggregate.get("premap_summary_count")),
        "premap_consumer_mapping": _as_int(
            aggregate.get("premap_consumer_mapping_count")
        ),
    }
    return {
        "row_count": sum(event_counts.values()),
        "event_counts": event_counts,
        "aggregate": aggregate,
    }


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
    require_real_descriptor_prep: bool = False,
    require_kernel_arg_shadow_table: bool = False,
    require_consumer_shim_table_read: bool = False,
    require_consumer_shim_table_consume: bool = False,
    require_consumer_shim_table_object: bool = False,
    require_consumer_shim_prep_execution: bool = False,
    require_kernel_arg_handoff_attempt: bool = False,
) -> dict[str, Any]:
    summary = _normalize_summary(summary)
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
    kernel_arg_shadow_table_active = any(
        key in aggregate
        for key in (
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count",
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate",
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate",
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count",
        )
    )
    if require_kernel_arg_shadow_table and not kernel_arg_shadow_table_active:
        failures.append("kernel_arg_shadow_table_fields_missing")
    if require_kernel_arg_shadow_table and not descriptor_prep_active:
        failures.append("kernel_arg_shadow_table_requires_descriptor_prep_fields")
    consumer_shim_table_read_active = any(
        key in aggregate
        for key in (
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count",
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate",
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate",
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count",
        )
    )
    if require_consumer_shim_table_read and not consumer_shim_table_read_active:
        failures.append("consumer_shim_table_read_fields_missing")
    if require_consumer_shim_table_read and not descriptor_prep_active:
        failures.append("consumer_shim_table_read_requires_descriptor_prep_fields")
    if require_consumer_shim_table_read and not kernel_arg_shadow_table_active:
        failures.append("consumer_shim_table_read_requires_kernel_arg_shadow_table_fields")
    consumer_shim_table_consume_checked_count = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
        )
    )
    # Aggregate schemas may include zero-valued consume counters even for legacy
    # or mixed diagnostic summaries. Treat consume as active only after at least
    # one shim table was actually consumed, unless the caller explicitly requires
    # the consume contract.
    consumer_shim_table_consume_active = consumer_shim_table_consume_checked_count > 0
    kernel_arg_handoff_attempt_active = any(
        key in aggregate
        for key in (
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason",
        )
    )
    if require_consumer_shim_table_consume and not consumer_shim_table_consume_active:
        failures.append("consumer_shim_table_consume_fields_missing")
    if require_consumer_shim_table_consume and not consumer_shim_table_read_active:
        failures.append("consumer_shim_table_consume_requires_table_read_fields")
    if require_kernel_arg_handoff_attempt and not kernel_arg_handoff_attempt_active:
        failures.append("consumer_shim_kernel_arg_handoff_attempt_fields_missing")
    if require_kernel_arg_handoff_attempt and not consumer_shim_table_consume_active:
        failures.append("consumer_shim_kernel_arg_handoff_attempt_requires_table_consume_fields")
    consumer_shim_table_object_checked_count = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
        )
    )
    consumer_shim_table_object_active = consumer_shim_table_object_checked_count > 0
    if require_consumer_shim_table_object and not consumer_shim_table_object_active:
        failures.append("consumer_shim_table_object_fields_missing")
    if require_consumer_shim_table_object and not consumer_shim_table_consume_active:
        failures.append("consumer_shim_table_object_requires_table_consume_fields")
    consumer_shim_prep_execution_checked_count = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
        )
    )
    consumer_shim_prep_execution_active = (
        consumer_shim_prep_execution_checked_count > 0
    )
    prelaunch_boundary_checked_count = _as_int(
        aggregate.get("premap_consumer_prelaunch_boundary_checked_count")
    )
    prelaunch_boundary_active = prelaunch_boundary_checked_count > 0
    if require_consumer_shim_prep_execution and not consumer_shim_prep_execution_active:
        failures.append("consumer_shim_prep_execution_fields_missing")
    if require_consumer_shim_prep_execution and not consumer_shim_table_object_active:
        failures.append("consumer_shim_prep_execution_requires_table_object_fields")
    if require_consumer_shim_prep_execution and not prelaunch_boundary_active:
        failures.append("prelaunch_boundary_fields_missing")
    descriptor_prep_real_active = any(
        key in aggregate
        for key in (
            "premap_consumer_descriptor_prep_real_handle_count",
            "premap_consumer_descriptor_prep_real_handle_miss_count",
            "premap_consumer_descriptor_prep_real_handle_hit_rate",
            "premap_consumer_descriptor_prep_real_handle_backed_rate",
        )
    )
    if (
        require_descriptor_prep
        or require_real_descriptor_prep
        or require_kernel_arg_shadow_table
        or require_kernel_arg_handoff_attempt
        or descriptor_prep_active
    ):
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
        if require_real_descriptor_prep or descriptor_prep_real_active:
            real_prep_count = _as_int(
                aggregate.get("premap_consumer_descriptor_prep_real_handle_count")
            )
            real_prep_miss = _as_int(
                aggregate.get("premap_consumer_descriptor_prep_real_handle_miss_count")
            )
            if require_real_descriptor_prep and not descriptor_prep_real_active:
                failures.append("descriptor_prep_real_handle_fields_missing")
            if real_prep_count != lookup_count:
                failures.append(
                    f"descriptor_prep_real_handle_count_mismatch={real_prep_count}!={lookup_count}"
                )
            if real_prep_miss != 0:
                failures.append(
                    f"descriptor_prep_real_handle_miss_count_nonzero={real_prep_miss}"
                )
            for field in (
                "premap_consumer_descriptor_prep_real_handle_hit_rate",
                "premap_consumer_descriptor_prep_real_handle_backed_rate",
            ):
                if _as_float(aggregate.get(field)) != 1.0:
                    failures.append(f"{field}_not_one")
        if require_kernel_arg_shadow_table or kernel_arg_shadow_table_active:
            table_executed = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
                )
            )
            table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
                )
            )
            table_parity_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
                )
            )
            table_column_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
                )
            )
            table_column_count_min = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
                )
            )
            table_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
                )
                or ""
            )
            table_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count"
                )
            )
            table_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count"
                )
            )
            table_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count"
                )
            )
            if table_executed != executed:
                failures.append(
                    "kernel_arg_shadow_table_executed_count_mismatch="
                    f"{table_executed}!={executed}"
                )
            if table_row_count != lookup_count:
                failures.append(
                    "kernel_arg_shadow_table_row_count_mismatch="
                    f"{table_row_count}!={lookup_count}"
                )
            if table_parity_count != table_row_count:
                failures.append(
                    "kernel_arg_shadow_table_parity_count_mismatch="
                    f"{table_parity_count}!={table_row_count}"
                )
            if table_column_count != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "kernel_arg_shadow_table_column_count_max_mismatch="
                    f"{table_column_count}!={EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if table_column_count_min != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "kernel_arg_shadow_table_column_count_min_mismatch="
                    f"{table_column_count_min}!={EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if table_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append("kernel_arg_shadow_table_schema_hash_mismatch")
            if table_schema_hash_checked_count != table_executed:
                failures.append(
                    "kernel_arg_shadow_table_schema_hash_checked_count_mismatch="
                    f"{table_schema_hash_checked_count}!={table_executed}"
                )
            if table_schema_hash_missing_count != 0:
                failures.append(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_"
                    "schema_hash_missing_count_nonzero="
                    f"{table_schema_hash_missing_count}"
                )
            if table_schema_hash_mismatch_count != 0:
                failures.append(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_"
                    "schema_hash_mismatch_count_nonzero="
                    f"{table_schema_hash_mismatch_count}"
                )
            for field in (
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate",
            ):
                if _as_float(aggregate.get(field)) != 1.0:
                    failures.append(f"{field}_not_one")
            for field in (
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count",
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count",
            ):
                count = _as_int(aggregate.get(field))
                if count != 0:
                    failures.append(f"{field}_nonzero={count}")
        if require_consumer_shim_table_read or consumer_shim_table_read_active:
            shim_executed = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_executed_count"
                )
            )
            shim_ok_rate = _as_float(
                aggregate.get("premap_consumer_descriptor_prep_consumer_shim_ok_rate")
            )
            read_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
                )
            )
            read_not_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
                )
            )
            read_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count"
                )
            )
            read_lifecycle_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count"
                )
            )
            read_parity_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
                )
            )
            shim_table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
                )
            )
            shim_table_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
                )
            )
            table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
                )
            )
            if shim_executed != executed:
                failures.append(
                    "consumer_shim_executed_count_mismatch="
                    f"{shim_executed}!={executed}"
                )
            if read_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_table_read_checked_count_mismatch="
                    f"{read_checked_count}!={shim_executed}"
                )
            if read_not_checked_count != 0:
                failures.append(
                    "consumer_shim_table_read_not_checked_count_nonzero="
                    f"{read_not_checked_count}"
                )
            if read_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_table_read_ok_count_mismatch="
                    f"{read_ok_count}!={shim_executed}"
                )
            if read_lifecycle_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_table_read_lifecycle_ok_count_mismatch="
                    f"{read_lifecycle_ok_count}!={shim_executed}"
                )
            if shim_table_row_count != table_row_count:
                failures.append(
                    "consumer_shim_table_row_count_mismatch="
                    f"{shim_table_row_count}!={table_row_count}"
                )
            if (
                shim_table_column_count_max
                != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
            ):
                failures.append(
                    "consumer_shim_table_column_count_max_mismatch="
                    f"{shim_table_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if read_parity_count != shim_table_row_count:
                failures.append(
                    "consumer_shim_table_read_parity_count_mismatch="
                    f"{read_parity_count}!={shim_table_row_count}"
                )
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_ok_rate",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate",
            ):
                if _as_float(aggregate.get(field)) != 1.0:
                    failures.append(f"{field}_not_one")
            if _as_float(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate"
                )
            ) != 0.0:
                failures.append("consumer_shim_table_read_not_checked_rate_nonzero")
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count",
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count",
            ):
                count = _as_int(aggregate.get(field))
                if count != 0:
                    failures.append(f"{field}_nonzero={count}")
        if (
            require_consumer_shim_table_consume
            or require_kernel_arg_handoff_attempt
            or consumer_shim_table_consume_active
        ):
            shim_executed = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_executed_count"
                )
            )
            consume_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
                )
            )
            consume_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count"
                )
            )
            consume_lifecycle_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count"
                )
            )
            consume_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
                )
            )
            consume_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max"
                )
            )
            consume_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
                )
                or ""
            )
            consume_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count"
                )
            )
            consume_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count"
                )
            )
            consume_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count"
                )
            )
            consume_mode = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
                )
                or ""
            )
            consume_mode_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count"
                )
            )
            consume_mode_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count"
                )
            )
            consume_mode_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count"
                )
            )
            consume_source = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
                )
                or ""
            )
            consume_source_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count"
                )
            )
            consume_source_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count"
                )
            )
            consume_source_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count"
                )
            )
            consume_parity_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count"
                )
            )
            consume_handle_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
                )
            )
            consume_required_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
                )
            )
            consume_optional_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count"
                )
            )
            consume_descriptor_ptr_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count"
                )
            )
            consume_packed_weight_descriptor_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count"
                )
            )
            consume_scale_metadata_handle_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count"
                )
            )
            consume_aux_metadata_handle_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count"
                )
            )
            consume_descriptor_ptr_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count"
                )
            )
            consume_packed_weight_descriptor_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count"
                )
            )
            consume_scale_metadata_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count"
                )
            )
            consume_aux_metadata_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count"
                )
            )
            consume_descriptor_ptr_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count"
                )
            )
            consume_descriptor_ptr_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_miss_count"
                )
            )
            consume_packed_weight_descriptor_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_hit_count"
                )
            )
            consume_packed_weight_descriptor_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count"
                )
            )
            consume_scale_metadata_handle_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_hit_count"
                )
            )
            consume_scale_metadata_handle_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_miss_count"
                )
            )
            consume_aux_metadata_handle_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count"
                )
            )
            consume_aux_metadata_handle_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_miss_count"
                )
            )
            handoff_dry_run_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count"
                )
            )
            handoff_dry_run_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count"
                )
            )
            handoff_dry_run_mode = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
                )
                or ""
            )
            handoff_dry_run_mode_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count"
                )
            )
            handoff_dry_run_mode_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count"
                )
            )
            handoff_dry_run_mode_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count"
                )
            )
            handoff_dry_run_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count"
                )
            )
            handoff_dry_run_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
                )
            )
            handoff_dry_run_column_count_min = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
                )
            )
            handoff_dry_run_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
                )
                or ""
            )
            handoff_dry_run_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count"
                )
            )
            handoff_dry_run_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count"
                )
            )
            handoff_dry_run_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count"
                )
            )
            handoff_dry_run_required_source_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count"
                )
            )
            handoff_dry_run_required_source_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count"
                )
            )
            handoff_dry_run_optional_source_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count"
                )
            )
            handoff_dry_run_optional_source_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count"
                )
            )
            handoff_dry_run_payload_bytes = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes"
                )
            )
            handoff_dry_run_payload_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count"
                )
            )
            handoff_dry_run_passed_to_kernel_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count"
                )
            )
            slot_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count"
                )
            )
            slot_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count"
                )
            )
            slot_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count"
                )
            )
            slot_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count"
                )
            )
            slot_mode = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
                )
                or ""
            )
            slot_mode_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count"
                )
            )
            slot_mode_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count"
                )
            )
            slot_mode_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count"
                )
            )
            slot_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count"
                )
            )
            slot_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max"
                )
            )
            slot_column_count_min = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min"
                )
            )
            slot_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
                )
                or ""
            )
            slot_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count"
                )
            )
            slot_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count"
                )
            )
            slot_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count"
                )
            )
            slot_required_source_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count"
                )
            )
            slot_required_source_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count"
                )
            )
            slot_optional_source_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count"
                )
            )
            slot_optional_source_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count"
                )
            )
            slot_payload_bytes = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes"
                )
            )
            slot_payload_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count"
                )
            )
            slot_passed_to_kernel_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count"
                )
            )
            slot_kernel_arg_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count"
                )
            )
            mirror_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count"
                )
            )
            mirror_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count"
                )
            )
            mirror_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count"
                )
            )
            mirror_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_missing_count"
                )
            )
            mirror_slot_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count"
                )
            )
            mirror_slot_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count"
                )
            )
            mirror_mode = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
                )
                or ""
            )
            mirror_mode_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_checked_count"
                )
            )
            mirror_mode_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_missing_count"
                )
            )
            mirror_mode_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count"
                )
            )
            mirror_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count"
                )
            )
            mirror_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max"
                )
            )
            mirror_column_count_min = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min"
                )
            )
            mirror_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
                )
                or ""
            )
            mirror_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count"
                )
            )
            mirror_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count"
                )
            )
            mirror_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count"
                )
            )
            mirror_required_source_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count"
                )
            )
            mirror_required_source_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count"
                )
            )
            mirror_optional_source_hit_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count"
                )
            )
            mirror_optional_source_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count"
                )
            )
            mirror_payload_bytes = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes"
                )
            )
            mirror_payload_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_violation_count"
                )
            )
            mirror_passed_to_kernel_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count"
                )
            )
            mirror_kernel_arg_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count"
                )
            )
            attempt_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count"
                )
            )
            attempt_record_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count"
                )
            )
            attempt_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count"
                )
            )
            attempt_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_missing_count"
                )
            )
            attempt_mirror_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count"
                )
            )
            attempt_mirror_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count"
                )
            )
            attempt_slot_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count"
                )
            )
            attempt_slot_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count"
                )
            )
            attempt_mode = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
                )
                or ""
            )
            attempt_mode_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_checked_count"
                )
            )
            attempt_mode_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_missing_count"
                )
            )
            attempt_mode_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count"
                )
            )
            attempt_block_reason = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
                )
                or ""
            )
            attempt_block_reason_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count"
                )
            )
            attempt_block_reason_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count"
                )
            )
            attempt_block_reason_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count"
                )
            )
            attempt_mirror_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count"
                )
            )
            attempt_gate_allowed_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count"
                )
            )
            attempt_blocked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count"
                )
            )
            attempt_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count"
                )
            )
            attempt_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max"
                )
            )
            attempt_column_count_min = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min"
                )
            )
            attempt_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
                )
                or ""
            )
            attempt_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count"
                )
            )
            attempt_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count"
                )
            )
            attempt_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count"
                )
            )
            attempt_payload_bytes = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes"
                )
            )
            attempt_payload_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_violation_count"
                )
            )
            attempt_passed_to_kernel_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count"
                )
            )
            attempt_kernel_arg_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count"
                )
            )
            shim_table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
                )
            )
            attempt_key_present = any(
                key in aggregate
                for key in (
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count",
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count",
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count",
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode",
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason",
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count",
                )
            )
            attempt_active = bool(
                attempt_key_present
                or
                attempt_checked_count
                or attempt_record_ready_count
                or attempt_hash_checked_count
                or attempt_mirror_hash_checked_count
                or attempt_slot_hash_checked_count
                or attempt_mode
                or attempt_mode_checked_count
                or attempt_block_reason
                or attempt_block_reason_checked_count
                or attempt_blocked_count
                or attempt_schema_hash_checked_count
            )
            if not attempt_active:
                if require_kernel_arg_handoff_attempt:
                    failures.append("consumer_shim_kernel_arg_handoff_attempt_fields_missing")
                # Older summaries predate the no-op handoff-attempt record. Keep
                # the table-consume gate backward-compatible unless those fields
                # are present, while new long-run artifacts remain strictly gated.
                attempt_checked_count = shim_executed
                attempt_record_ready_count = shim_executed
                attempt_hash_checked_count = shim_executed
                attempt_hash_missing_count = 0
                attempt_mirror_hash_checked_count = shim_executed
                attempt_mirror_hash_missing_count = 0
                attempt_slot_hash_checked_count = shim_executed
                attempt_slot_hash_missing_count = 0
                attempt_mode = "readonly_kernel_arg_handoff_attempt"
                attempt_mode_checked_count = shim_executed
                attempt_mode_missing_count = 0
                attempt_mode_mismatch_count = 0
                attempt_block_reason = "kernel_arg_handoff_disabled_noop_gate"
                attempt_block_reason_checked_count = shim_executed
                attempt_block_reason_missing_count = 0
                attempt_block_reason_mismatch_count = 0
                attempt_mirror_ready_count = shim_executed
                attempt_gate_allowed_count = 0
                attempt_blocked_count = shim_executed
                attempt_row_count = consume_row_count
                attempt_column_count_max = EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
                attempt_column_count_min = EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
                attempt_schema_hash = PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
                attempt_schema_hash_checked_count = shim_executed
                attempt_schema_hash_missing_count = 0
                attempt_schema_hash_mismatch_count = 0
                attempt_payload_bytes = 0
                attempt_payload_violation_count = 0
                attempt_passed_to_kernel_count = 0
                attempt_kernel_arg_violation_count = 0
            if consume_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_table_consume_checked_count_mismatch="
                    f"{consume_checked_count}!={shim_executed}"
                )
            if consume_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_table_consume_ok_count_mismatch="
                    f"{consume_ok_count}!={shim_executed}"
                )
            if consume_lifecycle_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_table_consume_lifecycle_ok_count_mismatch="
                    f"{consume_lifecycle_ok_count}!={shim_executed}"
                )
            if consume_row_count != shim_table_row_count:
                failures.append(
                    "consumer_shim_table_consume_row_count_mismatch="
                    f"{consume_row_count}!={shim_table_row_count}"
                )
            if (
                consume_column_count_max
                != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
            ):
                failures.append(
                    "consumer_shim_table_consume_column_count_max_mismatch="
                    f"{consume_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if consume_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append("consumer_shim_table_consume_schema_hash_mismatch")
            if consume_schema_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_table_consume_schema_hash_checked_count_mismatch="
                    f"{consume_schema_hash_checked_count}!={shim_executed}"
                )
            if consume_schema_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_table_consume_schema_hash_missing_count_nonzero="
                    f"{consume_schema_hash_missing_count}"
                )
            if consume_schema_hash_mismatch_count != 0:
                failures.append(
                    "consumer_shim_table_consume_schema_hash_mismatch_count_nonzero="
                    f"{consume_schema_hash_mismatch_count}"
                )
            if consume_mode != "readonly_consume_kernel_arg_shadow_table":
                failures.append("consumer_shim_table_consume_mode_mismatch")
            if consume_mode_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_table_consume_mode_checked_count_mismatch="
                    f"{consume_mode_checked_count}!={shim_executed}"
                )
            if consume_mode_missing_count != 0:
                failures.append(
                    "consumer_shim_table_consume_mode_missing_count_nonzero="
                    f"{consume_mode_missing_count}"
                )
            if consume_mode_mismatch_count != 0:
                failures.append(
                    "consumer_shim_table_consume_mode_mismatch_count_nonzero="
                    f"{consume_mode_mismatch_count}"
                )
            if not consume_source:
                failures.append("consumer_shim_table_consume_source_missing")
            if consume_source_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_table_consume_source_checked_count_mismatch="
                    f"{consume_source_checked_count}!={shim_executed}"
                )
            if consume_source_missing_count != 0:
                failures.append(
                    "consumer_shim_table_consume_source_missing_count_nonzero="
                    f"{consume_source_missing_count}"
                )
            if consume_source_mismatch_count != 0:
                failures.append(
                    "consumer_shim_table_consume_source_mismatch_count_nonzero="
                    f"{consume_source_mismatch_count}"
                )
            if consume_parity_count != consume_row_count:
                failures.append(
                    "consumer_shim_table_consume_parity_count_mismatch="
                    f"{consume_parity_count}!={consume_row_count}"
                )
            expected_consume_field_reads = (
                consume_row_count * EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
            )
            expected_consume_required_fields = consume_row_count * 3
            if consume_handle_field_read_count != expected_consume_field_reads:
                failures.append(
                    "consumer_shim_table_consume_handle_field_read_count_mismatch="
                    f"{consume_handle_field_read_count}!={expected_consume_field_reads}"
                )
            if (
                consume_required_handle_field_available_count
                != expected_consume_required_fields
            ):
                failures.append(
                    "consumer_shim_table_consume_required_handle_field_available_count_mismatch="
                    f"{consume_required_handle_field_available_count}!="
                    f"{expected_consume_required_fields}"
                )
            for name, count in (
                (
                    "descriptor_ptr_field_read_count",
                    consume_descriptor_ptr_field_read_count,
                ),
                (
                    "packed_weight_descriptor_field_read_count",
                    consume_packed_weight_descriptor_field_read_count,
                ),
                (
                    "scale_metadata_handle_field_read_count",
                    consume_scale_metadata_handle_field_read_count,
                ),
                (
                    "aux_metadata_handle_field_read_count",
                    consume_aux_metadata_handle_field_read_count,
                ),
                (
                    "descriptor_ptr_field_available_count",
                    consume_descriptor_ptr_field_available_count,
                ),
                (
                    "packed_weight_descriptor_field_available_count",
                    consume_packed_weight_descriptor_field_available_count,
                ),
                (
                    "scale_metadata_handle_field_available_count",
                    consume_scale_metadata_handle_field_available_count,
                ),
            ):
                if count != consume_row_count:
                    failures.append(
                        f"consumer_shim_table_consume_{name}_mismatch="
                        f"{count}!={consume_row_count}"
                    )
            if consume_optional_handle_field_available_count < 0:
                failures.append(
                    "consumer_shim_table_consume_optional_handle_field_available_count_negative"
                )
            if consume_optional_handle_field_available_count > consume_row_count:
                failures.append(
                    "consumer_shim_table_consume_optional_handle_field_available_count_exceeds_rows="
                    f"{consume_optional_handle_field_available_count}>{consume_row_count}"
                )
            if consume_aux_metadata_handle_field_available_count < 0:
                failures.append(
                    "consumer_shim_table_consume_aux_metadata_handle_field_available_count_negative"
                )
            if consume_aux_metadata_handle_field_available_count > consume_row_count:
                failures.append(
                    "consumer_shim_table_consume_aux_metadata_handle_field_available_count_exceeds_rows="
                    f"{consume_aux_metadata_handle_field_available_count}>{consume_row_count}"
                )
            for name, hit_count, miss_count in (
                (
                    "descriptor_ptr",
                    consume_descriptor_ptr_hit_count,
                    consume_descriptor_ptr_miss_count,
                ),
                (
                    "packed_weight_descriptor",
                    consume_packed_weight_descriptor_hit_count,
                    consume_packed_weight_descriptor_miss_count,
                ),
                (
                    "scale_metadata_handle",
                    consume_scale_metadata_handle_hit_count,
                    consume_scale_metadata_handle_miss_count,
                ),
            ):
                if hit_count != consume_row_count:
                    failures.append(
                        f"consumer_shim_table_consume_{name}_hit_count_mismatch="
                        f"{hit_count}!={consume_row_count}"
                    )
                if miss_count != 0:
                    failures.append(
                        f"consumer_shim_table_consume_{name}_miss_count_nonzero="
                        f"{miss_count}"
                    )
            if (
                consume_aux_metadata_handle_hit_count
                != consume_aux_metadata_handle_field_available_count
            ):
                failures.append(
                    "consumer_shim_table_consume_aux_metadata_handle_hit_count_mismatch="
                    f"{consume_aux_metadata_handle_hit_count}!="
                    f"{consume_aux_metadata_handle_field_available_count}"
                )
            if (
                consume_aux_metadata_handle_hit_count
                + consume_aux_metadata_handle_miss_count
                != consume_row_count
            ):
                failures.append(
                    "consumer_shim_table_consume_aux_metadata_handle_hit_miss_total_mismatch="
                    f"{consume_aux_metadata_handle_hit_count}+"
                    f"{consume_aux_metadata_handle_miss_count}!={consume_row_count}"
                )
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate",
            ):
                if _as_float(aggregate.get(field)) != 1.0:
                    failures.append(f"{field}_not_one")
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count",
            ):
                count = _as_int(aggregate.get(field))
                if count != 0:
                    failures.append(f"{field}_nonzero={count}")
            if handoff_dry_run_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_checked_count_mismatch="
                    f"{handoff_dry_run_checked_count}!={shim_executed}"
                )
            if handoff_dry_run_ready_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_ready_count_mismatch="
                    f"{handoff_dry_run_ready_count}!={shim_executed}"
                )
            if handoff_dry_run_mode != "readonly_kernel_arg_handoff_dry_run":
                failures.append("consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch")
            if handoff_dry_run_mode_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count_mismatch="
                    f"{handoff_dry_run_mode_checked_count}!={shim_executed}"
                )
            if handoff_dry_run_mode_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count_nonzero="
                    f"{handoff_dry_run_mode_missing_count}"
                )
            if handoff_dry_run_mode_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count_nonzero="
                    f"{handoff_dry_run_mode_mismatch_count}"
                )
            if handoff_dry_run_row_count != consume_row_count:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_row_count_mismatch="
                    f"{handoff_dry_run_row_count}!={consume_row_count}"
                )
            if (
                handoff_dry_run_column_count_max
                != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
            ):
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_column_count_max_mismatch="
                    f"{handoff_dry_run_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if (
                handoff_dry_run_column_count_min
                != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
            ):
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_column_count_min_mismatch="
                    f"{handoff_dry_run_column_count_min}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if handoff_dry_run_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch"
                )
            if handoff_dry_run_schema_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count_mismatch="
                    f"{handoff_dry_run_schema_hash_checked_count}!={shim_executed}"
                )
            if handoff_dry_run_schema_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count_nonzero="
                    f"{handoff_dry_run_schema_hash_missing_count}"
                )
            if handoff_dry_run_schema_hash_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count_nonzero="
                    f"{handoff_dry_run_schema_hash_mismatch_count}"
                )
            if (
                handoff_dry_run_required_source_hit_count
                != expected_consume_required_fields
            ):
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count_mismatch="
                    f"{handoff_dry_run_required_source_hit_count}!="
                    f"{expected_consume_required_fields}"
                )
            if handoff_dry_run_required_source_miss_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count_nonzero="
                    f"{handoff_dry_run_required_source_miss_count}"
                )
            if (
                handoff_dry_run_optional_source_hit_count
                + handoff_dry_run_optional_source_miss_count
                != consume_row_count
            ):
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_optional_source_total_mismatch="
                    f"{handoff_dry_run_optional_source_hit_count}+"
                    f"{handoff_dry_run_optional_source_miss_count}!={consume_row_count}"
                )
            if handoff_dry_run_payload_bytes != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_payload_bytes_nonzero="
                    f"{handoff_dry_run_payload_bytes}"
                )
            if handoff_dry_run_payload_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count_nonzero="
                    f"{handoff_dry_run_payload_violation_count}"
                )
            if handoff_dry_run_passed_to_kernel_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count_nonzero="
                    f"{handoff_dry_run_passed_to_kernel_count}"
                )
            if slot_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_checked_count_mismatch="
                    f"{slot_checked_count}!={shim_executed}"
                )
            if slot_ready_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_ready_count_mismatch="
                    f"{slot_ready_count}!={shim_executed}"
                )
            if slot_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count_mismatch="
                    f"{slot_hash_checked_count}!={shim_executed}"
                )
            if slot_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count_nonzero="
                    f"{slot_hash_missing_count}"
                )
            if slot_mode != "readonly_kernel_arg_handoff_shadow_slot":
                failures.append("consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch")
            if slot_mode_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count_mismatch="
                    f"{slot_mode_checked_count}!={shim_executed}"
                )
            if slot_mode_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count_nonzero="
                    f"{slot_mode_missing_count}"
                )
            if slot_mode_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count_nonzero="
                    f"{slot_mode_mismatch_count}"
                )
            if slot_row_count != consume_row_count:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_row_count_mismatch="
                    f"{slot_row_count}!={consume_row_count}"
                )
            if slot_column_count_max != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max_mismatch="
                    f"{slot_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if slot_column_count_min != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min_mismatch="
                    f"{slot_column_count_min}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if slot_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch"
                )
            if slot_schema_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count_mismatch="
                    f"{slot_schema_hash_checked_count}!={shim_executed}"
                )
            if slot_schema_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count_nonzero="
                    f"{slot_schema_hash_missing_count}"
                )
            if slot_schema_hash_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count_nonzero="
                    f"{slot_schema_hash_mismatch_count}"
                )
            if slot_required_source_hit_count != expected_consume_required_fields:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count_mismatch="
                    f"{slot_required_source_hit_count}!={expected_consume_required_fields}"
                )
            if slot_required_source_miss_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count_nonzero="
                    f"{slot_required_source_miss_count}"
                )
            if slot_optional_source_hit_count + slot_optional_source_miss_count != consume_row_count:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_total_mismatch="
                    f"{slot_optional_source_hit_count}+"
                    f"{slot_optional_source_miss_count}!={consume_row_count}"
                )
            if slot_payload_bytes != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes_nonzero="
                    f"{slot_payload_bytes}"
                )
            if slot_payload_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count_nonzero="
                    f"{slot_payload_violation_count}"
                )
            if slot_passed_to_kernel_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count_nonzero="
                    f"{slot_passed_to_kernel_count}"
                )
            if slot_kernel_arg_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count_nonzero="
                    f"{slot_kernel_arg_violation_count}"
                )
            if mirror_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_checked_count_mismatch="
                    f"{mirror_checked_count}!={shim_executed}"
                )
            if mirror_ready_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_ready_count_mismatch="
                    f"{mirror_ready_count}!={shim_executed}"
                )
            if mirror_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_hash_checked_count_mismatch="
                    f"{mirror_hash_checked_count}!={shim_executed}"
                )
            if mirror_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_hash_missing_count_nonzero="
                    f"{mirror_hash_missing_count}"
                )
            if mirror_slot_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count_mismatch="
                    f"{mirror_slot_hash_checked_count}!={shim_executed}"
                )
            if mirror_slot_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count_nonzero="
                    f"{mirror_slot_hash_missing_count}"
                )
            if mirror_mode != "readonly_kernel_arg_handoff_mirror":
                failures.append("consumer_shim_kernel_arg_handoff_mirror_mode_mismatch")
            if mirror_mode_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_mode_checked_count_mismatch="
                    f"{mirror_mode_checked_count}!={shim_executed}"
                )
            if mirror_mode_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_mode_missing_count_nonzero="
                    f"{mirror_mode_missing_count}"
                )
            if mirror_mode_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count_nonzero="
                    f"{mirror_mode_mismatch_count}"
                )
            if mirror_row_count != consume_row_count:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_row_count_mismatch="
                    f"{mirror_row_count}!={consume_row_count}"
                )
            if mirror_column_count_max != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_column_count_max_mismatch="
                    f"{mirror_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if mirror_column_count_min != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_column_count_min_mismatch="
                    f"{mirror_column_count_min}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if mirror_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append("consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch")
            if mirror_schema_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count_mismatch="
                    f"{mirror_schema_hash_checked_count}!={shim_executed}"
                )
            if mirror_schema_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count_nonzero="
                    f"{mirror_schema_hash_missing_count}"
                )
            if mirror_schema_hash_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count_nonzero="
                    f"{mirror_schema_hash_mismatch_count}"
                )
            if mirror_required_source_hit_count != expected_consume_required_fields:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count_mismatch="
                    f"{mirror_required_source_hit_count}!={expected_consume_required_fields}"
                )
            if mirror_required_source_miss_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count_nonzero="
                    f"{mirror_required_source_miss_count}"
                )
            if mirror_optional_source_hit_count + mirror_optional_source_miss_count != consume_row_count:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_optional_source_total_mismatch="
                    f"{mirror_optional_source_hit_count}+"
                    f"{mirror_optional_source_miss_count}!={consume_row_count}"
                )
            if mirror_payload_bytes != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_payload_bytes_nonzero="
                    f"{mirror_payload_bytes}"
                )
            if mirror_payload_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_payload_violation_count_nonzero="
                    f"{mirror_payload_violation_count}"
                )
            if mirror_passed_to_kernel_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count_nonzero="
                    f"{mirror_passed_to_kernel_count}"
                )
            if mirror_kernel_arg_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count_nonzero="
                    f"{mirror_kernel_arg_violation_count}"
                )
            if attempt_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_checked_count_mismatch="
                    f"{attempt_checked_count}!={shim_executed}"
                )
            if attempt_record_ready_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_record_ready_count_mismatch="
                    f"{attempt_record_ready_count}!={shim_executed}"
                )
            if attempt_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_hash_checked_count_mismatch="
                    f"{attempt_hash_checked_count}!={shim_executed}"
                )
            if attempt_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_hash_missing_count_nonzero="
                    f"{attempt_hash_missing_count}"
                )
            if attempt_mirror_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count_mismatch="
                    f"{attempt_mirror_hash_checked_count}!={shim_executed}"
                )
            if attempt_mirror_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count_nonzero="
                    f"{attempt_mirror_hash_missing_count}"
                )
            if attempt_slot_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count_mismatch="
                    f"{attempt_slot_hash_checked_count}!={shim_executed}"
                )
            if attempt_slot_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count_nonzero="
                    f"{attempt_slot_hash_missing_count}"
                )
            if attempt_mode != "readonly_kernel_arg_handoff_attempt":
                failures.append("consumer_shim_kernel_arg_handoff_attempt_mode_mismatch")
            if attempt_mode_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_mode_checked_count_mismatch="
                    f"{attempt_mode_checked_count}!={shim_executed}"
                )
            if attempt_mode_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_mode_missing_count_nonzero="
                    f"{attempt_mode_missing_count}"
                )
            if attempt_mode_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count_nonzero="
                    f"{attempt_mode_mismatch_count}"
                )
            if attempt_block_reason != "kernel_arg_handoff_disabled_noop_gate":
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch"
                )
            if attempt_block_reason_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count_mismatch="
                    f"{attempt_block_reason_checked_count}!={shim_executed}"
                )
            if attempt_block_reason_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count_nonzero="
                    f"{attempt_block_reason_missing_count}"
                )
            if attempt_block_reason_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count_nonzero="
                    f"{attempt_block_reason_mismatch_count}"
                )
            if attempt_mirror_ready_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count_mismatch="
                    f"{attempt_mirror_ready_count}!={shim_executed}"
                )
            if attempt_gate_allowed_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count_nonzero="
                    f"{attempt_gate_allowed_count}"
                )
            if attempt_blocked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_blocked_count_mismatch="
                    f"{attempt_blocked_count}!={shim_executed}"
                )
            if attempt_row_count != consume_row_count:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_row_count_mismatch="
                    f"{attempt_row_count}!={consume_row_count}"
                )
            if attempt_column_count_max != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_column_count_max_mismatch="
                    f"{attempt_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if attempt_column_count_min != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_column_count_min_mismatch="
                    f"{attempt_column_count_min}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if attempt_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch"
                )
            if attempt_schema_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count_mismatch="
                    f"{attempt_schema_hash_checked_count}!={shim_executed}"
                )
            if attempt_schema_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count_nonzero="
                    f"{attempt_schema_hash_missing_count}"
                )
            if attempt_schema_hash_mismatch_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count_nonzero="
                    f"{attempt_schema_hash_mismatch_count}"
                )
            if attempt_payload_bytes != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_payload_bytes_nonzero="
                    f"{attempt_payload_bytes}"
                )
            if attempt_payload_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_payload_violation_count_nonzero="
                    f"{attempt_payload_violation_count}"
                )
            if attempt_passed_to_kernel_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count_nonzero="
                    f"{attempt_passed_to_kernel_count}"
                )
            if attempt_kernel_arg_violation_count != 0:
                failures.append(
                    "consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count_nonzero="
                    f"{attempt_kernel_arg_violation_count}"
                )
        if require_consumer_shim_table_object or consumer_shim_table_object_active:
            shim_executed = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_executed_count"
                )
            )
            table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
                )
            )
            object_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
                )
            )
            object_consumed_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count"
                )
            )
            object_lifecycle_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count"
                )
            )
            object_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count"
                )
            )
            if object_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_table_object_checked_count_mismatch="
                    f"{object_checked_count}!={shim_executed}"
                )
            if object_consumed_count != shim_executed:
                failures.append(
                    "consumer_shim_table_object_consumed_count_mismatch="
                    f"{object_consumed_count}!={shim_executed}"
                )
            if object_lifecycle_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_table_object_lifecycle_ok_count_mismatch="
                    f"{object_lifecycle_ok_count}!={shim_executed}"
                )
            if object_row_count != table_row_count:
                failures.append(
                    "consumer_shim_table_object_row_count_mismatch="
                    f"{object_row_count}!={table_row_count}"
                )
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate",
            ):
                if _as_float(aggregate.get(field)) != 1.0:
                    failures.append(f"{field}_not_one")
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_violation_count",
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count",
            ):
                count = _as_int(aggregate.get(field))
                if count != 0:
                    failures.append(f"{field}_nonzero={count}")
        if require_consumer_shim_prep_execution or consumer_shim_prep_execution_active:
            shim_executed = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_executed_count"
                )
            )
            mapping_count = _as_int(
                aggregate.get("premap_consumer_mapping_count"),
                default=consumer_count,
            )
            prelaunch_aligned_count = _as_int(
                aggregate.get("premap_consumer_prelaunch_boundary_aligned_count")
            )
            prelaunch_available_count = _as_int(
                aggregate.get("premap_consumer_prelaunch_handle_available_count")
            )
            prelaunch_block_count = _as_int(
                aggregate.get("premap_consumer_prelaunch_block_count")
            )
            prelaunch_unique_expert_count = _as_int(
                aggregate.get("premap_consumer_prelaunch_unique_expert_count")
            )
            table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
                )
            )
            if require_consumer_shim_prep_execution or prelaunch_boundary_active:
                if prelaunch_boundary_checked_count != mapping_count:
                    failures.append(
                        "prelaunch_boundary_checked_count_mismatch="
                        f"{prelaunch_boundary_checked_count}!={mapping_count}"
                    )
                if prelaunch_aligned_count != mapping_count:
                    failures.append(
                        "prelaunch_boundary_aligned_count_mismatch="
                        f"{prelaunch_aligned_count}!={mapping_count}"
                    )
                if prelaunch_available_count != mapping_count:
                    failures.append(
                        "prelaunch_handle_available_count_mismatch="
                        f"{prelaunch_available_count}!={mapping_count}"
                    )
                if prelaunch_block_count < prelaunch_unique_expert_count:
                    failures.append(
                        "prelaunch_block_count_lt_unique_expert_count="
                        f"{prelaunch_block_count}<{prelaunch_unique_expert_count}"
                    )
            dry_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
                )
            )
            dry_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count"
                )
            )
            dry_lifecycle_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count"
                )
            )
            dry_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count"
                )
            )
            dry_column_count_max = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max"
                )
            )
            dry_schema_hash = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
                )
                or ""
            )
            dry_schema_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count"
                )
            )
            dry_schema_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_missing_count"
                )
            )
            dry_schema_hash_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_mismatch_count"
                )
            )
            dry_row_handle_parity_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count"
                )
            )
            dry_descriptor_ptr_parity_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count"
                )
            )
            dry_packed_weight_descriptor_parity_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count"
                )
            )
            dry_scale_metadata_handle_parity_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count"
                )
            )
            dry_aux_metadata_handle_parity_ok_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count"
                )
            )
            dry_handle_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
                )
            )
            dry_required_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
                )
            )
            dry_optional_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count"
                )
            )
            dry_descriptor_ptr_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count"
                )
            )
            dry_packed_weight_descriptor_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count"
                )
            )
            dry_scale_metadata_handle_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count"
                )
            )
            dry_aux_metadata_handle_field_read_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count"
                )
            )
            dry_descriptor_ptr_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count"
                )
            )
            dry_packed_weight_descriptor_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count"
                )
            )
            dry_scale_metadata_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count"
                )
            )
            dry_aux_metadata_handle_field_available_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count"
                )
            )
            dry_row_handle_miss_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count"
                )
            )
            if dry_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_prep_execution_checked_count_mismatch="
                    f"{dry_checked_count}!={shim_executed}"
                )
            if dry_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_prep_execution_ok_count_mismatch="
                    f"{dry_ok_count}!={shim_executed}"
                )
            if dry_lifecycle_ok_count != shim_executed:
                failures.append(
                    "consumer_shim_prep_execution_lifecycle_ok_count_mismatch="
                    f"{dry_lifecycle_ok_count}!={shim_executed}"
                )
            if dry_row_count != table_row_count:
                failures.append(
                    "consumer_shim_prep_execution_row_count_mismatch="
                    f"{dry_row_count}!={table_row_count}"
                )
            if dry_column_count_max != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                failures.append(
                    "consumer_shim_prep_execution_column_count_max_mismatch="
                    f"{dry_column_count_max}!="
                    f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                )
            if dry_schema_hash != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH:
                failures.append("consumer_shim_prep_execution_schema_hash_mismatch")
            if dry_schema_hash_checked_count != shim_executed:
                failures.append(
                    "consumer_shim_prep_execution_schema_hash_checked_count_mismatch="
                    f"{dry_schema_hash_checked_count}!={shim_executed}"
                )
            if dry_schema_hash_missing_count != 0:
                failures.append(
                    "consumer_shim_prep_execution_schema_hash_missing_count_nonzero="
                    f"{dry_schema_hash_missing_count}"
                )
            if dry_schema_hash_mismatch_count != 0:
                failures.append(
                    "consumer_shim_prep_execution_schema_hash_mismatch_count_nonzero="
                    f"{dry_schema_hash_mismatch_count}"
                )
            for name, count in (
                (
                    "row_handle_parity_ok_count",
                    dry_row_handle_parity_ok_count,
                ),
                (
                    "descriptor_ptr_parity_ok_count",
                    dry_descriptor_ptr_parity_ok_count,
                ),
                (
                    "packed_weight_descriptor_parity_ok_count",
                    dry_packed_weight_descriptor_parity_ok_count,
                ),
                (
                    "scale_metadata_handle_parity_ok_count",
                    dry_scale_metadata_handle_parity_ok_count,
                ),
                (
                    "aux_metadata_handle_parity_ok_count",
                    dry_aux_metadata_handle_parity_ok_count,
                ),
            ):
                if count != dry_row_count:
                    failures.append(
                        f"consumer_shim_prep_execution_{name}_mismatch="
                        f"{count}!={dry_row_count}"
                    )
            expected_field_reads = (
                dry_row_count * EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
            )
            expected_required_fields = dry_row_count * 3
            if dry_handle_field_read_count != expected_field_reads:
                failures.append(
                    "consumer_shim_prep_execution_handle_field_read_count_mismatch="
                    f"{dry_handle_field_read_count}!={expected_field_reads}"
                )
            if (
                dry_required_handle_field_available_count
                != expected_required_fields
            ):
                failures.append(
                    "consumer_shim_prep_execution_required_handle_field_available_count_mismatch="
                    f"{dry_required_handle_field_available_count}!="
                    f"{expected_required_fields}"
                )
            if dry_optional_handle_field_available_count < 0:
                failures.append(
                    "consumer_shim_prep_execution_optional_handle_field_available_count_negative"
                )
            if dry_optional_handle_field_available_count > dry_row_count:
                failures.append(
                    "consumer_shim_prep_execution_optional_handle_field_available_count_exceeds_rows="
                    f"{dry_optional_handle_field_available_count}>{dry_row_count}"
                )
            for name, count in (
                (
                    "descriptor_ptr_field_read_count",
                    dry_descriptor_ptr_field_read_count,
                ),
                (
                    "packed_weight_descriptor_field_read_count",
                    dry_packed_weight_descriptor_field_read_count,
                ),
                (
                    "scale_metadata_handle_field_read_count",
                    dry_scale_metadata_handle_field_read_count,
                ),
                (
                    "aux_metadata_handle_field_read_count",
                    dry_aux_metadata_handle_field_read_count,
                ),
                (
                    "descriptor_ptr_field_available_count",
                    dry_descriptor_ptr_field_available_count,
                ),
                (
                    "packed_weight_descriptor_field_available_count",
                    dry_packed_weight_descriptor_field_available_count,
                ),
                (
                    "scale_metadata_handle_field_available_count",
                    dry_scale_metadata_handle_field_available_count,
                ),
            ):
                if count != dry_row_count:
                    failures.append(
                        f"consumer_shim_prep_execution_{name}_mismatch="
                        f"{count}!={dry_row_count}"
                    )
            if dry_aux_metadata_handle_field_available_count < 0:
                failures.append(
                    "consumer_shim_prep_execution_aux_metadata_handle_field_available_count_negative"
                )
            if dry_aux_metadata_handle_field_available_count > dry_row_count:
                failures.append(
                    "consumer_shim_prep_execution_aux_metadata_handle_field_available_count_exceeds_rows="
                    f"{dry_aux_metadata_handle_field_available_count}>{dry_row_count}"
                )
            if dry_row_handle_miss_count != 0:
                failures.append(
                    "consumer_shim_prep_execution_row_handle_miss_count_nonzero="
                    f"{dry_row_handle_miss_count}"
                )
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate",
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate",
            ):
                if _as_float(aggregate.get(field)) != 1.0:
                    failures.append(f"{field}_not_one")
            for field in (
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes",
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count",
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count",
            ):
                count = _as_int(aggregate.get(field))
                if count != 0:
                    failures.append(f"{field}_nonzero={count}")
    real_handle_hits = _as_int(
        aggregate.get("premap_consumer_real_descriptor_handle_hit_count")
    )
    if real_handle_hits <= 0:
        failures.append("real_descriptor_handle_hit_count_missing_or_zero")
    for source in ("packed_weight", "scale_metadata"):
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
        "premap_consumer_descriptor_prep_real_handle_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_real_handle_count")
        ),
        "premap_consumer_descriptor_prep_real_handle_miss_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_real_handle_miss_count")
        ),
        "premap_consumer_descriptor_prep_real_handle_hit_rate": _as_float(
            aggregate.get("premap_consumer_descriptor_prep_real_handle_hit_rate")
        ),
        "premap_consumer_descriptor_prep_real_handle_backed_rate": _as_float(
            aggregate.get("premap_consumer_descriptor_prep_real_handle_backed_rate")
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count")
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count")
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count")
        ),
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_executed_count": _as_int(
            aggregate.get("premap_consumer_descriptor_prep_consumer_shim_executed_count")
        ),
        "premap_consumer_descriptor_prep_consumer_shim_ok_rate": _as_float(
            aggregate.get("premap_consumer_descriptor_prep_consumer_shim_ok_rate")
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count"
            )
        ),
        "premap_consumer_prelaunch_boundary_checked_count": _as_int(
            aggregate.get("premap_consumer_prelaunch_boundary_checked_count")
        ),
        "premap_consumer_prelaunch_boundary_aligned_rate": _as_float(
            aggregate.get("premap_consumer_prelaunch_boundary_aligned_rate")
        ),
        "premap_consumer_prelaunch_handle_available_rate": _as_float(
            aggregate.get("premap_consumer_prelaunch_handle_available_rate")
        ),
        "premap_consumer_prelaunch_block_count": _as_int(
            aggregate.get("premap_consumer_prelaunch_block_count")
        ),
        "premap_consumer_prelaunch_unique_expert_count": _as_int(
            aggregate.get("premap_consumer_prelaunch_unique_expert_count")
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate": _as_float(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes"
            )
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
        "require_real_descriptor_prep": bool(require_real_descriptor_prep),
        "require_kernel_arg_shadow_table": bool(require_kernel_arg_shadow_table),
        "require_consumer_shim_table_read": bool(require_consumer_shim_table_read),
        "require_consumer_shim_table_consume": bool(require_consumer_shim_table_consume),
        "require_consumer_shim_table_object": bool(require_consumer_shim_table_object),
        "require_consumer_shim_prep_execution": bool(
            require_consumer_shim_prep_execution
        ),
        "require_kernel_arg_handoff_attempt": bool(
            require_kernel_arg_handoff_attempt
        ),
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
    parser.add_argument(
        "--require-real-descriptor-prep",
        action="store_true",
        help=(
            "Require descriptor prep to be backed by live packed-weight/scale "
            "runtime handle signatures.  This is the final safety gate before "
            "real descriptor/address prep integration."
        ),
    )
    parser.add_argument(
        "--require-kernel-arg-shadow-table",
        action="store_true",
        help=(
            "Require the readonly descriptor-prep kernel-argument shadow table "
            "contract: all rows parity-ok, no misses/stale rows, no payload, "
            "and no ready/router/order/kernel-arg side effects."
        ),
    )
    parser.add_argument(
        "--require-consumer-shim-table-read",
        action="store_true",
        help=(
            "Require the descriptor-prep consumer shim to read the kernel-arg "
            "shadow table object: all reads checked/ok/lifecycle-ok, all rows "
            "parity-ok, no missing/stale rows, no payload, and no kernel handoff."
        ),
    )
    parser.add_argument(
        "--require-consumer-shim-table-consume",
        action="store_true",
        help=(
            "Require the descriptor-prep consumer shim to consume the prepared "
            "handle table object in readonly dry-run mode. The table must have "
            "stable shape/schema/row parity and must not be passed to a kernel."
        ),
    )
    parser.add_argument(
        "--require-consumer-shim-table-object",
        action="store_true",
        help=(
            "Require the descriptor-prep consumer shim to read the actual "
            "in-memory shadow table object, not just the table result hashes. "
            "The object must remain lifecycle-ok, zero-payload, and not passed "
            "to a kernel."
        ),
    )
    parser.add_argument(
        "--require-consumer-shim-prep-execution",
        action="store_true",
        help=(
            "Require the descriptor-prep consumer shim to validate the prepared "
            "descriptor/address table as an execution dry-run object. This "
            "still forbids payload movement and kernel argument handoff."
        ),
    )
    parser.add_argument(
        "--require-kernel-arg-handoff-attempt",
        action="store_true",
        help=(
            "Require the readonly kernel-argument handoff attempt record. The "
            "attempt must be ready but blocked by the no-op gate, with zero "
            "payload and no kernel argument handoff."
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
        require_real_descriptor_prep=args.require_real_descriptor_prep,
        require_kernel_arg_shadow_table=args.require_kernel_arg_shadow_table,
        require_consumer_shim_table_read=args.require_consumer_shim_table_read,
        require_consumer_shim_table_consume=args.require_consumer_shim_table_consume,
        require_consumer_shim_table_object=args.require_consumer_shim_table_object,
        require_consumer_shim_prep_execution=(
            args.require_consumer_shim_prep_execution
        ),
        require_kernel_arg_handoff_attempt=(
            args.require_kernel_arg_handoff_attempt
        ),
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
