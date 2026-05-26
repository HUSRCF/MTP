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
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME,
)


REQUIRED_EVENT_TYPES = {"premap_summary", "premap_consumer_mapping"}
EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT = len(
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
)
EXPECTED_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELD_COUNT = len(
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS
)
KERNEL_ARG_HANDOFF_ATTEMPT_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_"
)
KERNEL_ARG_HANDOFF_LIVE_TOGGLE_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_"
)
KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_"
)
KERNEL_ARG_HANDOFF_LAUNCH_SCHEMA_MIRROR_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_"
)
KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX = (
    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_"
)


def _normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Accept audit summaries, trace performance summaries, and gate reports."""
    if "aggregate" in summary and "event_counts" in summary:
        return summary
    metrics = summary.get("metrics")
    if isinstance(metrics, dict):
        aggregate = dict(metrics)
        if summary.get("passed") is True and summary.get("failures") in (None, []):
            _backfill_gate_report_metrics(aggregate)
        event_counts = {
            "premap_summary": _as_int(aggregate.get("premap_summary_count")),
            "premap_consumer_mapping": _as_int(
                aggregate.get("premap_consumer_mapping_count")
            ),
        }
        return {
            "row_count": _as_int(
                aggregate.get("row_count"), sum(event_counts.values())
            ),
            "event_counts": event_counts,
            "aggregate": aggregate,
        }
    aggregate = summary.get("runtime_shadow_aggregate")
    if not isinstance(aggregate, dict):
        return summary
    aggregate = dict(aggregate)
    for key, value in summary.items():
        if str(key).startswith("runtime_shadow_premap_kernel_arg_live_mutation_"):
            aggregate[str(key)] = value
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


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off", ""}:
            return False
    return bool(value)


def _backfill_gate_report_metrics(aggregate: dict[str, Any]) -> None:
    """Make checker output self-checkable when used as a gate artifact.

    The gate report stores the checker-facing metric summary, not the original
    runtime aggregate.  Some strict checks need auxiliary counters that are
    losslessly implied by the already-passed report.  Backfill those only for a
    report that previously passed so the artifact can be revalidated directly.
    """

    def set_if_missing(key: str, value: Any) -> None:
        if key not in aggregate and value is not None:
            aggregate[key] = value

    def set_count_from_rate(key: str, rate_key: str, count_key: str) -> None:
        if key not in aggregate and _as_float(aggregate.get(rate_key)) == 1.0:
            aggregate[key] = _as_int(aggregate.get(count_key))

    lookup_count = _as_int(aggregate.get("premap_consumer_descriptor_prep_lookup_count"))
    prelaunch_checked = _as_int(
        aggregate.get("premap_consumer_prelaunch_boundary_checked_count")
    )
    prep_execution_checked = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count"
        )
    )
    launch_checked = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count"
        )
    )
    live_checked = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count"
        )
    )
    live_adapter_checked = _as_int(
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count"
        )
    )
    set_if_missing(
        f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}changes_kernel_launch_args_count",
        aggregate.get(
            f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}kernel_arg_violation_count"
        ),
    )
    set_if_missing(
        f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}changes_kernel_launch_args_count",
        aggregate.get(
            f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}kernel_arg_violation_count"
        ),
    )
    set_if_missing(
        "premap_consumer_descriptor_handle_hit_rate",
        aggregate.get("premap_consumer_real_descriptor_handle_hit_rate"),
    )
    set_if_missing(
        "premap_consumer_lookup_after_prepare_rate",
        aggregate.get("premap_consumer_descriptor_prep_execution_ok_attempted_rate"),
    )
    set_if_missing(
        "premap_consumer_descriptor_prep_handle_count",
        aggregate.get("premap_consumer_descriptor_prep_real_handle_count")
        or lookup_count,
    )
    set_if_missing(
        "premap_consumer_descriptor_prep_execution_ok_rate",
        aggregate.get("premap_consumer_descriptor_prep_execution_ok_attempted_rate"),
    )
    set_if_missing(
        "premap_consumer_descriptor_prep_descriptor_ptr_count",
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count"
        )
        or aggregate.get("premap_consumer_real_descriptor_handle_hit_count"),
    )
    set_if_missing(
        "premap_consumer_descriptor_prep_packed_weight_descriptor_count",
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count"
        )
        or aggregate.get("premap_consumer_real_descriptor_handle_packed_weight_hit_count"),
    )
    set_if_missing(
        "premap_consumer_descriptor_prep_scale_metadata_handle_count",
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count"
        )
        or aggregate.get("premap_consumer_real_descriptor_handle_scale_metadata_hit_count"),
    )

    set_count_from_rate(
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count",
    )
    set_count_from_rate(
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count",
    )
    set_count_from_rate(
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count",
    )
    set_count_from_rate(
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate",
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count",
    )
    set_count_from_rate(
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count",
    )
    set_count_from_rate(
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate",
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count",
    )

    if _as_float(aggregate.get("premap_consumer_prelaunch_boundary_aligned_rate")) == 1.0:
        set_if_missing("premap_consumer_prelaunch_boundary_aligned_count", prelaunch_checked)
    if _as_float(aggregate.get("premap_consumer_prelaunch_handle_available_rate")) == 1.0:
        set_if_missing("premap_consumer_prelaunch_handle_available_count", prelaunch_checked)

    set_if_missing(
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count",
        prep_execution_checked if aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash"
        ) else None,
    )
    for prefix, checked in (
        (
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror",
            launch_checked,
        ),
        (
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle",
            live_checked,
        ),
        (
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter",
            live_adapter_checked,
        ),
    ):
        for suffix in (
            "mode_checked_count",
            "table_schema_hash_checked_count",
            "launch_schema_name_checked_count",
            "launch_schema_hash_checked_count",
            "attempt_hash_checked_count",
            "table_object_hash_checked_count",
            "hash_checked_count",
            "live_noop_integration_hash_checked_count",
            "launch_schema_mirror_hash_checked_count",
            "block_reason_checked_count",
            "live_noop_integration_block_reason_checked_count",
        ):
            set_if_missing(f"{prefix}_{suffix}", checked)
    set_if_missing(
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min",
        aggregate.get(
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max"
        ),
    )


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
    require_kernel_arg_handoff_live_toggle: bool = False,
    require_kernel_arg_handoff_live_noop_integration: bool = False,
    require_kernel_arg_handoff_launch_schema_mirror: bool = False,
    require_kernel_arg_handoff_live_consumer_adapter: bool = False,
    allow_enabled_blocked_live_toggle: bool = False,
    allow_connected_blocked_consumer_adapter: bool = False,
    allow_kernel_arg_handoff_live_kernel_arg_pass: bool = False,
    allow_kernel_arg_handoff_live_real_kernel_arg_mutation: bool = False,
    allow_single_field_replacement_live: bool = False,
) -> dict[str, Any]:
    raw_kernel_arg_pass_enabled = summary.get(
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    )
    raw_real_kernel_arg_mutation_enabled = summary.get(
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"
    )
    raw_single_field_replacement_dry_run_enabled = summary.get(
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"
    )
    raw_single_field_replacement_live_enabled = summary.get(
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled"
    )
    raw_single_field_replacement_field = summary.get(
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field"
    )
    raw_metrics = summary.get("metrics")
    if isinstance(raw_metrics, dict):
        raw_single_field_replacement_dry_run_enabled = raw_metrics.get(
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
            raw_single_field_replacement_dry_run_enabled,
        )
        raw_single_field_replacement_field = raw_metrics.get(
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field",
            raw_single_field_replacement_field,
        )
        raw_single_field_replacement_live_enabled = raw_metrics.get(
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
            raw_single_field_replacement_live_enabled,
        )
    summary = _normalize_summary(summary)
    event_counts = {
        str(key): int(value) for key, value in summary.get("event_counts", {}).items()
    }
    aggregate = summary.get("aggregate", {})
    failures: list[str] = []
    if allow_connected_blocked_consumer_adapter and not allow_enabled_blocked_live_toggle:
        failures.append(
            "allow_connected_blocked_consumer_adapter_requires_allow_enabled_blocked_live_toggle"
        )
    if allow_kernel_arg_handoff_live_kernel_arg_pass and not (
        allow_enabled_blocked_live_toggle and allow_connected_blocked_consumer_adapter
    ):
        failures.append(
            "allow_kernel_arg_handoff_live_kernel_arg_pass_requires_connected_adapter"
        )
    if allow_kernel_arg_handoff_live_real_kernel_arg_mutation and not (
        allow_kernel_arg_handoff_live_kernel_arg_pass
    ):
        failures.append(
            "allow_kernel_arg_handoff_live_real_kernel_arg_mutation_requires_kernel_arg_pass"
        )
    kernel_arg_pass_enabled = aggregate.get(
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
        raw_kernel_arg_pass_enabled,
    )
    if _as_bool(kernel_arg_pass_enabled) and not allow_kernel_arg_handoff_live_kernel_arg_pass:
        failures.append("kernel_arg_handoff_kernel_arg_pass_enabled_true")
    if allow_kernel_arg_handoff_live_kernel_arg_pass and not _as_bool(
        kernel_arg_pass_enabled
    ):
        failures.append(
            "allow_kernel_arg_handoff_live_kernel_arg_pass_requires_runtime_flag_true"
        )
    real_kernel_arg_mutation_enabled = aggregate.get(
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
        raw_real_kernel_arg_mutation_enabled,
    )
    if _as_bool(real_kernel_arg_mutation_enabled) and not (
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation
    ):
        failures.append(
            "kernel_arg_handoff_real_kernel_arg_mutation_enabled_true"
        )
    if allow_kernel_arg_handoff_live_real_kernel_arg_mutation and not _as_bool(
        real_kernel_arg_mutation_enabled
    ):
        failures.append(
            "allow_kernel_arg_handoff_live_real_kernel_arg_mutation_requires_runtime_flag_true"
        )
    single_field_replacement_dry_run_enabled = aggregate.get(
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
        raw_single_field_replacement_dry_run_enabled,
    )
    single_field_replacement_live_enabled = aggregate.get(
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
        raw_single_field_replacement_live_enabled,
    )
    single_field_replacement_field = aggregate.get(
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field",
        raw_single_field_replacement_field,
    )
    if (
        _as_bool(single_field_replacement_live_enabled)
        and not allow_single_field_replacement_live
    ):
        failures.append("single_field_replacement_live_enabled_true")
    if (
        allow_single_field_replacement_live
        and not _as_bool(single_field_replacement_live_enabled)
    ):
        failures.append(
            "allow_single_field_replacement_live_requires_runtime_flag_true"
        )
    if _as_bool(single_field_replacement_live_enabled) and not _as_bool(
        single_field_replacement_dry_run_enabled
    ):
        failures.append("single_field_replacement_live_requires_dry_run_enabled")

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
        str(key).startswith(KERNEL_ARG_HANDOFF_ATTEMPT_PREFIX) for key in aggregate
    )
    kernel_arg_handoff_live_toggle_active = any(
        str(key).startswith(KERNEL_ARG_HANDOFF_LIVE_TOGGLE_PREFIX)
        for key in aggregate
    )
    live_noop_integration_checked_count = _as_int(
        aggregate.get(
            f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}checked_count"
        )
    )
    kernel_arg_handoff_live_noop_integration_active = (
        live_noop_integration_checked_count > 0
    )
    launch_schema_mirror_checked_count = _as_int(
        aggregate.get(
            f"{KERNEL_ARG_HANDOFF_LAUNCH_SCHEMA_MIRROR_PREFIX}checked_count"
        )
    )
    # Newer aggregate schemas may include zero-valued launch-schema mirror
    # counters even when the mirror record was not emitted.  Treat this contract
    # as active only once at least one mirror was actually checked.
    kernel_arg_handoff_launch_schema_mirror_active = (
        launch_schema_mirror_checked_count > 0
    )
    live_consumer_adapter_checked_count = _as_int(
        aggregate.get(
            f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}checked_count"
        )
    )
    kernel_arg_handoff_live_consumer_adapter_active = (
        live_consumer_adapter_checked_count > 0
    )
    if require_consumer_shim_table_consume and not consumer_shim_table_consume_active:
        failures.append("consumer_shim_table_consume_fields_missing")
    if require_consumer_shim_table_consume and not consumer_shim_table_read_active:
        failures.append("consumer_shim_table_consume_requires_table_read_fields")
    if require_kernel_arg_handoff_attempt and not kernel_arg_handoff_attempt_active:
        failures.append("consumer_shim_kernel_arg_handoff_attempt_fields_missing")
    if require_kernel_arg_handoff_attempt and not consumer_shim_table_consume_active:
        failures.append("consumer_shim_kernel_arg_handoff_attempt_requires_table_consume_fields")
    if require_kernel_arg_handoff_live_toggle and not kernel_arg_handoff_live_toggle_active:
        failures.append("consumer_shim_kernel_arg_handoff_live_toggle_fields_missing")
    if require_kernel_arg_handoff_live_toggle and not kernel_arg_handoff_attempt_active:
        failures.append("consumer_shim_kernel_arg_handoff_live_toggle_requires_handoff_attempt_fields")
    if (
        require_kernel_arg_handoff_live_noop_integration
        and not kernel_arg_handoff_live_noop_integration_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_live_noop_integration_fields_missing"
        )
    if (
        require_kernel_arg_handoff_live_noop_integration
        and not kernel_arg_handoff_live_toggle_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_live_noop_integration_requires_live_toggle_fields"
        )
    if (
        require_kernel_arg_handoff_live_noop_integration
        and not kernel_arg_handoff_launch_schema_mirror_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_live_noop_integration_requires_launch_schema_mirror_fields"
        )
    if (
        require_kernel_arg_handoff_launch_schema_mirror
        and not kernel_arg_handoff_launch_schema_mirror_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_launch_schema_mirror_fields_missing"
        )
    if (
        require_kernel_arg_handoff_launch_schema_mirror
        and not kernel_arg_handoff_attempt_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_launch_schema_mirror_requires_handoff_attempt_fields"
        )
    if (
        require_kernel_arg_handoff_live_consumer_adapter
        and not kernel_arg_handoff_live_consumer_adapter_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_live_consumer_adapter_fields_missing"
        )
    if (
        require_kernel_arg_handoff_live_consumer_adapter
        and not kernel_arg_handoff_live_noop_integration_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_live_consumer_adapter_requires_live_noop_integration_fields"
        )
    if (
        require_kernel_arg_handoff_live_consumer_adapter
        and not kernel_arg_handoff_launch_schema_mirror_active
    ):
        failures.append(
            "consumer_shim_kernel_arg_handoff_live_consumer_adapter_requires_launch_schema_mirror_fields"
        )
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
        or require_kernel_arg_handoff_live_toggle
        or require_kernel_arg_handoff_live_noop_integration
        or require_kernel_arg_handoff_launch_schema_mirror
        or require_kernel_arg_handoff_live_consumer_adapter
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
            or require_kernel_arg_handoff_launch_schema_mirror
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
            live_toggle_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count"
                )
            )
            live_toggle_record_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count"
                )
            )
            live_toggle_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count"
                )
            )
            live_toggle_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count"
                )
            )
            live_toggle_attempt_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_checked_count"
                )
            )
            live_toggle_attempt_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_missing_count"
                )
            )
            live_toggle_table_object_hash_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_checked_count"
                )
            )
            live_toggle_table_object_hash_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_missing_count"
                )
            )
            live_toggle_mode = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
                )
                or ""
            )
            live_toggle_mode_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count"
                )
            )
            live_toggle_mode_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_missing_count"
                )
            )
            live_toggle_mode_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_mismatch_count"
                )
            )
            live_toggle_block_reason = str(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
                )
                or ""
            )
            live_toggle_block_reason_checked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count"
                )
            )
            live_toggle_block_reason_missing_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_missing_count"
                )
            )
            live_toggle_block_reason_mismatch_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch_count"
                )
            )
            live_toggle_enabled_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
                )
            )
            live_toggle_lab_gate_passed_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count"
                )
            )
            live_toggle_attempt_record_ready_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count"
                )
            )
            live_toggle_live_eligible_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count"
                )
            )
            live_toggle_blocked_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count"
                )
            )
            live_toggle_payload_bytes = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes"
                )
            )
            live_toggle_payload_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count"
                )
            )
            live_toggle_passed_to_kernel_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
                )
            )
            live_toggle_kernel_arg_violation_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count"
                )
            )
            live_noop_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}checked_count"
                )
            )
            live_noop_record_ready_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}record_ready_count"
                )
            )
            live_noop_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}hash_checked_count"
                )
            )
            live_noop_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}hash_missing_count"
                )
            )
            live_noop_live_toggle_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_toggle_hash_checked_count"
                )
            )
            live_noop_live_toggle_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_toggle_hash_missing_count"
                )
            )
            live_noop_launch_schema_mirror_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}launch_schema_mirror_hash_checked_count"
                )
            )
            live_noop_launch_schema_mirror_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}launch_schema_mirror_hash_missing_count"
                )
            )
            live_noop_table_object_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}table_object_hash_checked_count"
                )
            )
            live_noop_table_object_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}table_object_hash_missing_count"
                )
            )
            live_noop_mode = str(
                aggregate.get(f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode")
                or ""
            )
            live_noop_mode_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode_checked_count"
                )
            )
            live_noop_mode_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode_missing_count"
                )
            )
            live_noop_mode_mismatch_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode_mismatch_count"
                )
            )
            live_noop_block_reason = str(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason"
                )
                or ""
            )
            live_noop_block_reason_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason_checked_count"
                )
            )
            live_noop_block_reason_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason_missing_count"
                )
            )
            live_noop_block_reason_mismatch_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason_mismatch_count"
                )
            )
            live_noop_enabled_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}enabled_count"
                )
            )
            live_noop_lab_gate_passed_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}lab_gate_passed_count"
                )
            )
            live_noop_live_toggle_record_ready_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_toggle_record_ready_count"
                )
            )
            live_noop_launch_schema_ready_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}launch_schema_ready_count"
                )
            )
            live_noop_live_eligible_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_eligible_count"
                )
            )
            live_noop_consumer_connected_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}consumer_connected_count"
                )
            )
            live_noop_blocked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}blocked_count"
                )
            )
            live_noop_payload_bytes = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}payload_bytes"
                )
            )
            live_noop_payload_violation_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}payload_violation_count"
                )
            )
            live_noop_passed_to_kernel_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}passed_to_kernel_count"
                )
            )
            live_noop_kernel_arg_violation_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}kernel_arg_violation_count"
                )
            )
            live_noop_changes_kernel_launch_args_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}changes_kernel_launch_args_count",
                    aggregate.get(
                        f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}kernel_arg_violation_count"
                    ),
                )
            )
            adapter_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}checked_count"
                )
            )
            adapter_record_ready_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}record_ready_count"
                )
            )
            adapter_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}hash_checked_count"
                )
            )
            adapter_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}hash_missing_count"
                )
            )
            adapter_live_noop_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_hash_checked_count"
                )
            )
            adapter_live_noop_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_hash_missing_count"
                )
            )
            adapter_launch_schema_mirror_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}launch_schema_mirror_hash_checked_count"
                )
            )
            adapter_launch_schema_mirror_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}launch_schema_mirror_hash_missing_count"
                )
            )
            adapter_table_object_hash_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}table_object_hash_checked_count"
                )
            )
            adapter_table_object_hash_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}table_object_hash_missing_count"
                )
            )
            adapter_mode = str(
                aggregate.get(f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode")
                or ""
            )
            adapter_mode_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode_checked_count"
                )
            )
            adapter_mode_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode_missing_count"
                )
            )
            adapter_mode_mismatch_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode_mismatch_count"
                )
            )
            adapter_block_reason = str(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason"
                )
                or ""
            )
            adapter_block_reason_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason_checked_count"
                )
            )
            adapter_block_reason_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason_missing_count"
                )
            )
            adapter_block_reason_mismatch_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason_mismatch_count"
                )
            )
            adapter_live_noop_block_reason = str(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason"
                )
                or ""
            )
            adapter_live_noop_block_reason_checked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason_checked_count"
                )
            )
            adapter_live_noop_block_reason_missing_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason_missing_count"
                )
            )
            adapter_live_noop_block_reason_mismatch_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason_mismatch_count"
                )
            )
            adapter_enabled_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}enabled_count"
                )
            )
            adapter_lab_gate_passed_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}lab_gate_passed_count"
                )
            )
            adapter_live_noop_record_ready_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_record_ready_count"
                )
            )
            adapter_live_noop_blocked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_blocked_count"
                )
            )
            adapter_consumer_adapter_present_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}consumer_adapter_present_count"
                )
            )
            adapter_consumer_connected_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}consumer_connected_count"
                )
            )
            adapter_live_eligible_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_eligible_count"
                )
            )
            adapter_blocked_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}blocked_count"
                )
            )
            adapter_payload_bytes = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}payload_bytes"
                )
            )
            adapter_payload_violation_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}payload_violation_count"
                )
            )
            adapter_passed_to_kernel_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}passed_to_kernel_count"
                )
            )
            adapter_kernel_arg_violation_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}kernel_arg_violation_count"
                )
            )
            adapter_changes_kernel_launch_args_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}changes_kernel_launch_args_count",
                    aggregate.get(
                        f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}kernel_arg_violation_count"
                    ),
                )
            )
            adapter_contract_live_pass_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}contract_live_pass_count"
                )
            )
            adapter_real_kernel_arg_handoff_count = _as_int(
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}real_kernel_arg_handoff_count"
                )
            )
            shim_table_row_count = _as_int(
                aggregate.get(
                    "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
                )
            )
            attempt_active = bool(
                kernel_arg_handoff_attempt_active
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
            if (
                require_kernel_arg_handoff_launch_schema_mirror
                or kernel_arg_handoff_launch_schema_mirror_active
            ):
                launch_prefix = (
                    "premap_consumer_descriptor_prep_consumer_shim_"
                    "kernel_arg_handoff_launch_schema_mirror_"
                )
                launch_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}checked_count")
                )
                launch_ready_count = _as_int(
                    aggregate.get(f"{launch_prefix}ready_count")
                )
                launch_hash_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}hash_checked_count")
                )
                launch_hash_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}hash_missing_count")
                )
                launch_handoff_mirror_hash_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}handoff_mirror_hash_checked_count")
                )
                launch_handoff_mirror_hash_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}handoff_mirror_hash_missing_count")
                )
                launch_slot_hash_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}slot_hash_checked_count")
                )
                launch_slot_hash_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}slot_hash_missing_count")
                )
                launch_mode = str(aggregate.get(f"{launch_prefix}mode") or "")
                launch_mode_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}mode_checked_count")
                )
                launch_mode_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}mode_missing_count")
                )
                launch_mode_mismatch_count = _as_int(
                    aggregate.get(f"{launch_prefix}mode_mismatch_count")
                )
                launch_row_count = _as_int(
                    aggregate.get(f"{launch_prefix}row_count")
                )
                launch_column_count_max = _as_int(
                    aggregate.get(f"{launch_prefix}column_count_max")
                )
                launch_column_count_min = _as_int(
                    aggregate.get(f"{launch_prefix}column_count_min")
                )
                launch_table_schema_hash = str(
                    aggregate.get(f"{launch_prefix}table_schema_hash") or ""
                )
                launch_table_schema_hash_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}table_schema_hash_checked_count")
                )
                launch_table_schema_hash_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}table_schema_hash_missing_count")
                )
                launch_table_schema_hash_mismatch_count = _as_int(
                    aggregate.get(f"{launch_prefix}table_schema_hash_mismatch_count")
                )
                launch_schema_name = str(
                    aggregate.get(f"{launch_prefix}launch_schema_name") or ""
                )
                launch_schema_name_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_schema_name_checked_count")
                )
                launch_schema_name_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_schema_name_missing_count")
                )
                launch_schema_name_mismatch_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_schema_name_mismatch_count")
                )
                launch_schema_hash = str(
                    aggregate.get(f"{launch_prefix}launch_schema_hash") or ""
                )
                launch_schema_hash_checked_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_schema_hash_checked_count")
                )
                launch_schema_hash_missing_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_schema_hash_missing_count")
                )
                launch_schema_hash_mismatch_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_schema_hash_mismatch_count")
                )
                launch_arg_field_count = _as_int(
                    aggregate.get(f"{launch_prefix}launch_arg_field_count")
                )
                launch_required_source_hit_count = _as_int(
                    aggregate.get(f"{launch_prefix}required_source_hit_count")
                )
                launch_required_source_miss_count = _as_int(
                    aggregate.get(f"{launch_prefix}required_source_miss_count")
                )
                launch_optional_source_hit_count = _as_int(
                    aggregate.get(f"{launch_prefix}optional_source_hit_count")
                )
                launch_optional_source_miss_count = _as_int(
                    aggregate.get(f"{launch_prefix}optional_source_miss_count")
                )
                launch_handle_field_read_count = _as_int(
                    aggregate.get(f"{launch_prefix}handle_field_read_count")
                )
                launch_payload_bytes = _as_int(
                    aggregate.get(f"{launch_prefix}payload_bytes")
                )
                launch_payload_violation_count = _as_int(
                    aggregate.get(f"{launch_prefix}payload_violation_count")
                )
                launch_passed_to_kernel_count = _as_int(
                    aggregate.get(f"{launch_prefix}passed_to_kernel_count")
                )
                launch_kernel_arg_violation_count = _as_int(
                    aggregate.get(f"{launch_prefix}kernel_arg_violation_count")
                )
                if launch_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count_mismatch="
                        f"{launch_checked_count}!={shim_executed}"
                    )
                if launch_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count_mismatch="
                        f"{launch_ready_count}!={shim_executed}"
                    )
                for name, value in (
                    ("hash_checked_count", launch_hash_checked_count),
                    (
                        "handoff_mirror_hash_checked_count",
                        launch_handoff_mirror_hash_checked_count,
                    ),
                    ("slot_hash_checked_count", launch_slot_hash_checked_count),
                ):
                    if value != shim_executed:
                        failures.append(
                            "consumer_shim_kernel_arg_handoff_launch_schema_mirror_"
                            f"{name}_mismatch={value}!={shim_executed}"
                        )
                for name, value in (
                    ("hash_missing_count", launch_hash_missing_count),
                    (
                        "handoff_mirror_hash_missing_count",
                        launch_handoff_mirror_hash_missing_count,
                    ),
                    ("slot_hash_missing_count", launch_slot_hash_missing_count),
                ):
                    if value != 0:
                        failures.append(
                            "consumer_shim_kernel_arg_handoff_launch_schema_mirror_"
                            f"{name}_nonzero={value}"
                        )
                if (
                    launch_mode
                    != "readonly_kernel_arg_handoff_launch_schema_mirror"
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_mismatch"
                    )
                if launch_mode_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_checked_count_mismatch="
                        f"{launch_mode_checked_count}!={shim_executed}"
                    )
                if launch_mode_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_missing_count_nonzero="
                        f"{launch_mode_missing_count}"
                    )
                if launch_mode_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_mismatch_count_nonzero="
                        f"{launch_mode_mismatch_count}"
                    )
                if launch_row_count != consume_row_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count_mismatch="
                        f"{launch_row_count}!={consume_row_count}"
                    )
                if launch_column_count_max != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max_mismatch="
                        f"{launch_column_count_max}!="
                        f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                    )
                if launch_column_count_min != EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min_mismatch="
                        f"{launch_column_count_min}!="
                        f"{EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                    )
                if (
                    launch_table_schema_hash
                    != PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_mismatch"
                    )
                if launch_table_schema_hash_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_checked_count_mismatch="
                        f"{launch_table_schema_hash_checked_count}!={shim_executed}"
                    )
                if launch_table_schema_hash_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_missing_count_nonzero="
                        f"{launch_table_schema_hash_missing_count}"
                    )
                if launch_table_schema_hash_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_mismatch_count_nonzero="
                        f"{launch_table_schema_hash_mismatch_count}"
                    )
                if launch_schema_name != PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_mismatch"
                    )
                if launch_schema_name_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_checked_count_mismatch="
                        f"{launch_schema_name_checked_count}!={shim_executed}"
                    )
                if launch_schema_name_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_missing_count_nonzero="
                        f"{launch_schema_name_missing_count}"
                    )
                if launch_schema_name_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_mismatch_count_nonzero="
                        f"{launch_schema_name_mismatch_count}"
                    )
                if launch_schema_hash != PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_mismatch"
                    )
                if launch_schema_hash_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_checked_count_mismatch="
                        f"{launch_schema_hash_checked_count}!={shim_executed}"
                    )
                if launch_schema_hash_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_missing_count_nonzero="
                        f"{launch_schema_hash_missing_count}"
                    )
                if launch_schema_hash_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_mismatch_count_nonzero="
                        f"{launch_schema_hash_mismatch_count}"
                    )
                expected_launch_arg_field_count = (
                    shim_executed
                    * EXPECTED_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELD_COUNT
                )
                if launch_arg_field_count != expected_launch_arg_field_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count_mismatch="
                        f"{launch_arg_field_count}!={expected_launch_arg_field_count}"
                    )
                if launch_required_source_hit_count != expected_consume_required_fields:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count_mismatch="
                        f"{launch_required_source_hit_count}!={expected_consume_required_fields}"
                    )
                if launch_required_source_miss_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count_nonzero="
                        f"{launch_required_source_miss_count}"
                    )
                if (
                    launch_optional_source_hit_count
                    + launch_optional_source_miss_count
                    != consume_row_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_total_mismatch="
                        f"{launch_optional_source_hit_count}+"
                        f"{launch_optional_source_miss_count}!={consume_row_count}"
                    )
                if (
                    launch_handle_field_read_count
                    != consume_row_count * EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count_mismatch="
                        f"{launch_handle_field_read_count}!="
                        f"{consume_row_count * EXPECTED_KERNEL_ARG_SHADOW_TABLE_COLUMN_COUNT}"
                    )
                if launch_payload_bytes != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes_nonzero="
                        f"{launch_payload_bytes}"
                    )
                if launch_payload_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_violation_count_nonzero="
                        f"{launch_payload_violation_count}"
                    )
                if launch_passed_to_kernel_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count_nonzero="
                        f"{launch_passed_to_kernel_count}"
                    )
                if launch_kernel_arg_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count_nonzero="
                        f"{launch_kernel_arg_violation_count}"
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
            if require_kernel_arg_handoff_live_toggle or kernel_arg_handoff_live_toggle_active:
                expected_live_toggle_block_reason = (
                    "kernel_arg_handoff_kernel_consumer_not_connected"
                    if allow_enabled_blocked_live_toggle
                    else "kernel_arg_handoff_live_disabled"
                )
                expected_live_toggle_enabled_count = (
                    shim_executed if allow_enabled_blocked_live_toggle else 0
                )
                expected_live_toggle_live_eligible_count = (
                    shim_executed if allow_enabled_blocked_live_toggle else 0
                )
                if live_toggle_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_checked_count_mismatch="
                        f"{live_toggle_checked_count}!={shim_executed}"
                    )
                if live_toggle_record_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count_mismatch="
                        f"{live_toggle_record_ready_count}!={shim_executed}"
                    )
                if live_toggle_hash_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count_mismatch="
                        f"{live_toggle_hash_checked_count}!={shim_executed}"
                    )
                if live_toggle_hash_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count_nonzero="
                        f"{live_toggle_hash_missing_count}"
                    )
                if live_toggle_attempt_hash_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_checked_count_mismatch="
                        f"{live_toggle_attempt_hash_checked_count}!={shim_executed}"
                    )
                if live_toggle_attempt_hash_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_missing_count_nonzero="
                        f"{live_toggle_attempt_hash_missing_count}"
                    )
                if live_toggle_table_object_hash_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_checked_count_mismatch="
                        f"{live_toggle_table_object_hash_checked_count}!={shim_executed}"
                    )
                if live_toggle_table_object_hash_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_missing_count_nonzero="
                        f"{live_toggle_table_object_hash_missing_count}"
                    )
                if live_toggle_mode != "readonly_kernel_arg_handoff_live_toggle":
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_mode_mismatch"
                    )
                if live_toggle_mode_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count_mismatch="
                        f"{live_toggle_mode_checked_count}!={shim_executed}"
                    )
                if live_toggle_mode_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_mode_missing_count_nonzero="
                        f"{live_toggle_mode_missing_count}"
                    )
                if live_toggle_mode_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_mode_mismatch_count_nonzero="
                        f"{live_toggle_mode_mismatch_count}"
                    )
                if live_toggle_block_reason != expected_live_toggle_block_reason:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch"
                    )
                if live_toggle_block_reason_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count_mismatch="
                        f"{live_toggle_block_reason_checked_count}!={shim_executed}"
                    )
                if live_toggle_block_reason_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_block_reason_missing_count_nonzero="
                        f"{live_toggle_block_reason_missing_count}"
                    )
                if live_toggle_block_reason_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch_count_nonzero="
                        f"{live_toggle_block_reason_mismatch_count}"
                    )
                if live_toggle_enabled_count != expected_live_toggle_enabled_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_enabled_count_mismatch="
                        f"{live_toggle_enabled_count}!={expected_live_toggle_enabled_count}"
                    )
                if live_toggle_lab_gate_passed_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count_mismatch="
                        f"{live_toggle_lab_gate_passed_count}!={shim_executed}"
                    )
                if live_toggle_attempt_record_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count_mismatch="
                        f"{live_toggle_attempt_record_ready_count}!={shim_executed}"
                    )
                if live_toggle_live_eligible_count != expected_live_toggle_live_eligible_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count_mismatch="
                        f"{live_toggle_live_eligible_count}!={expected_live_toggle_live_eligible_count}"
                    )
                if live_toggle_blocked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_blocked_count_mismatch="
                        f"{live_toggle_blocked_count}!={shim_executed}"
                    )
                if live_toggle_payload_bytes != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes_nonzero="
                        f"{live_toggle_payload_bytes}"
                    )
                if live_toggle_payload_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count_nonzero="
                        f"{live_toggle_payload_violation_count}"
                    )
                if live_toggle_passed_to_kernel_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count_nonzero="
                        f"{live_toggle_passed_to_kernel_count}"
                    )
                if live_toggle_kernel_arg_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count_nonzero="
                        f"{live_toggle_kernel_arg_violation_count}"
                    )
            if (
                require_kernel_arg_handoff_live_noop_integration
                or kernel_arg_handoff_live_noop_integration_active
            ):
                expected_live_noop_block_reason = (
                    "kernel_arg_handoff_kernel_arg_pass_disabled"
                    if allow_connected_blocked_consumer_adapter
                    else
                    "kernel_arg_handoff_kernel_consumer_not_connected"
                    if allow_enabled_blocked_live_toggle
                    else "kernel_arg_handoff_live_disabled"
                )
                expected_live_noop_enabled_count = (
                    shim_executed if allow_enabled_blocked_live_toggle else 0
                )
                expected_live_noop_live_eligible_count = (
                    shim_executed if allow_enabled_blocked_live_toggle else 0
                )
                expected_live_noop_consumer_connected_count = (
                    shim_executed if allow_connected_blocked_consumer_adapter else 0
                )
                if live_noop_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count_mismatch="
                        f"{live_noop_checked_count}!={shim_executed}"
                    )
                if live_noop_record_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count_mismatch="
                        f"{live_noop_record_ready_count}!={shim_executed}"
                    )
                for name, value in (
                    ("hash_checked_count", live_noop_hash_checked_count),
                    (
                        "live_toggle_hash_checked_count",
                        live_noop_live_toggle_hash_checked_count,
                    ),
                    (
                        "launch_schema_mirror_hash_checked_count",
                        live_noop_launch_schema_mirror_hash_checked_count,
                    ),
                    (
                        "table_object_hash_checked_count",
                        live_noop_table_object_hash_checked_count,
                    ),
                ):
                    if value != shim_executed:
                        failures.append(
                            "consumer_shim_kernel_arg_handoff_live_noop_integration_"
                            f"{name}_mismatch={value}!={shim_executed}"
                        )
                for name, value in (
                    ("hash_missing_count", live_noop_hash_missing_count),
                    (
                        "live_toggle_hash_missing_count",
                        live_noop_live_toggle_hash_missing_count,
                    ),
                    (
                        "launch_schema_mirror_hash_missing_count",
                        live_noop_launch_schema_mirror_hash_missing_count,
                    ),
                    (
                        "table_object_hash_missing_count",
                        live_noop_table_object_hash_missing_count,
                    ),
                ):
                    if value != 0:
                        failures.append(
                            "consumer_shim_kernel_arg_handoff_live_noop_integration_"
                            f"{name}_nonzero={value}"
                        )
                if live_noop_mode != "readonly_kernel_arg_handoff_live_noop_integration":
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_mode_mismatch"
                    )
                if live_noop_mode_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_mode_checked_count_mismatch="
                        f"{live_noop_mode_checked_count}!={shim_executed}"
                    )
                if live_noop_mode_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_mode_missing_count_nonzero="
                        f"{live_noop_mode_missing_count}"
                    )
                if live_noop_mode_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_mode_mismatch_count_nonzero="
                        f"{live_noop_mode_mismatch_count}"
                    )
                if live_noop_block_reason != expected_live_noop_block_reason:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_mismatch"
                    )
                if live_noop_block_reason_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_checked_count_mismatch="
                        f"{live_noop_block_reason_checked_count}!={shim_executed}"
                    )
                if live_noop_block_reason_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_missing_count_nonzero="
                        f"{live_noop_block_reason_missing_count}"
                    )
                if live_noop_block_reason_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_mismatch_count_nonzero="
                        f"{live_noop_block_reason_mismatch_count}"
                    )
                if live_noop_enabled_count != expected_live_noop_enabled_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count_mismatch="
                        f"{live_noop_enabled_count}!={expected_live_noop_enabled_count}"
                    )
                if live_noop_lab_gate_passed_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed_count_mismatch="
                        f"{live_noop_lab_gate_passed_count}!={shim_executed}"
                    )
                if live_noop_live_toggle_record_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_count_mismatch="
                        f"{live_noop_live_toggle_record_ready_count}!={shim_executed}"
                    )
                if live_noop_launch_schema_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count_mismatch="
                        f"{live_noop_launch_schema_ready_count}!={shim_executed}"
                    )
                if live_noop_live_eligible_count != expected_live_noop_live_eligible_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible_count_mismatch="
                        f"{live_noop_live_eligible_count}!={expected_live_noop_live_eligible_count}"
                    )
                if (
                    live_noop_consumer_connected_count
                    != expected_live_noop_consumer_connected_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count_mismatch="
                        f"{live_noop_consumer_connected_count}!={expected_live_noop_consumer_connected_count}"
                    )
                if live_noop_blocked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count_mismatch="
                        f"{live_noop_blocked_count}!={shim_executed}"
                    )
                if live_noop_payload_bytes != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes_nonzero="
                        f"{live_noop_payload_bytes}"
                    )
                if live_noop_payload_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_payload_violation_count_nonzero="
                        f"{live_noop_payload_violation_count}"
                    )
                if live_noop_passed_to_kernel_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count_nonzero="
                        f"{live_noop_passed_to_kernel_count}"
                    )
                if live_noop_kernel_arg_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_kernel_arg_violation_count_nonzero="
                        f"{live_noop_kernel_arg_violation_count}"
                    )
                if live_noop_changes_kernel_launch_args_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count_nonzero="
                        f"{live_noop_changes_kernel_launch_args_count}"
                    )
            if (
                require_kernel_arg_handoff_live_consumer_adapter
                or kernel_arg_handoff_live_consumer_adapter_active
            ):
                expected_adapter_block_reason = (
                    "kernel_arg_handoff_real_kernel_arg_mutation_live"
                    if allow_kernel_arg_handoff_live_real_kernel_arg_mutation
                    else "kernel_arg_handoff_kernel_arg_pass_live"
                    if allow_kernel_arg_handoff_live_kernel_arg_pass
                    else "kernel_arg_handoff_kernel_arg_pass_disabled"
                    if allow_connected_blocked_consumer_adapter
                    else
                    "kernel_arg_handoff_kernel_consumer_not_connected"
                    if allow_enabled_blocked_live_toggle
                    else "kernel_arg_handoff_live_disabled"
                )
                expected_adapter_live_noop_block_reason = (
                    "kernel_arg_handoff_kernel_arg_pass_disabled"
                    if allow_connected_blocked_consumer_adapter
                    else
                    "kernel_arg_handoff_kernel_consumer_not_connected"
                    if allow_enabled_blocked_live_toggle
                    else "kernel_arg_handoff_live_disabled"
                )
                expected_adapter_enabled_count = (
                    shim_executed if allow_enabled_blocked_live_toggle else 0
                )
                expected_adapter_live_eligible_count = (
                    shim_executed if allow_enabled_blocked_live_toggle else 0
                )
                expected_adapter_consumer_connected_count = (
                    shim_executed if allow_connected_blocked_consumer_adapter else 0
                )
                expected_adapter_blocked_count = (
                    0
                    if allow_kernel_arg_handoff_live_kernel_arg_pass
                    else shim_executed
                )
                expected_adapter_passed_to_kernel_count = (
                    shim_executed
                    if allow_kernel_arg_handoff_live_kernel_arg_pass
                    else 0
                )
                expected_adapter_changes_kernel_args_count = (
                    shim_executed
                    if allow_kernel_arg_handoff_live_kernel_arg_pass
                    else 0
                )
                expected_adapter_contract_live_pass_count = (
                    shim_executed
                    if allow_kernel_arg_handoff_live_kernel_arg_pass
                    else 0
                )
                expected_adapter_real_kernel_arg_handoff_count = (
                    shim_executed
                    if allow_kernel_arg_handoff_live_real_kernel_arg_mutation
                    else 0
                )
                if adapter_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count_mismatch="
                        f"{adapter_checked_count}!={shim_executed}"
                    )
                if adapter_record_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count_mismatch="
                        f"{adapter_record_ready_count}!={shim_executed}"
                    )
                for name, value in (
                    ("hash_checked_count", adapter_hash_checked_count),
                    (
                        "live_noop_integration_hash_checked_count",
                        adapter_live_noop_hash_checked_count,
                    ),
                    (
                        "launch_schema_mirror_hash_checked_count",
                        adapter_launch_schema_mirror_hash_checked_count,
                    ),
                    (
                        "table_object_hash_checked_count",
                        adapter_table_object_hash_checked_count,
                    ),
                ):
                    if value != shim_executed:
                        failures.append(
                            "consumer_shim_kernel_arg_handoff_live_consumer_adapter_"
                            f"{name}_mismatch={value}!={shim_executed}"
                        )
                for name, value in (
                    ("hash_missing_count", adapter_hash_missing_count),
                    (
                        "live_noop_integration_hash_missing_count",
                        adapter_live_noop_hash_missing_count,
                    ),
                    (
                        "launch_schema_mirror_hash_missing_count",
                        adapter_launch_schema_mirror_hash_missing_count,
                    ),
                    (
                        "table_object_hash_missing_count",
                        adapter_table_object_hash_missing_count,
                    ),
                ):
                    if value != 0:
                        failures.append(
                            "consumer_shim_kernel_arg_handoff_live_consumer_adapter_"
                            f"{name}_nonzero={value}"
                        )
                if adapter_mode != "readonly_kernel_arg_handoff_live_consumer_adapter":
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_mismatch"
                    )
                if adapter_mode_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_checked_count_mismatch="
                        f"{adapter_mode_checked_count}!={shim_executed}"
                    )
                if adapter_mode_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_missing_count_nonzero="
                        f"{adapter_mode_missing_count}"
                    )
                if adapter_mode_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_mismatch_count_nonzero="
                        f"{adapter_mode_mismatch_count}"
                    )
                if adapter_block_reason != expected_adapter_block_reason:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch"
                    )
                if adapter_block_reason_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_checked_count_mismatch="
                        f"{adapter_block_reason_checked_count}!={shim_executed}"
                    )
                if adapter_block_reason_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_missing_count_nonzero="
                        f"{adapter_block_reason_missing_count}"
                    )
                if adapter_block_reason_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch_count_nonzero="
                        f"{adapter_block_reason_mismatch_count}"
                    )
                if (
                    adapter_live_noop_block_reason
                    != expected_adapter_live_noop_block_reason
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_mismatch"
                    )
                if adapter_live_noop_block_reason_checked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_checked_count_mismatch="
                        f"{adapter_live_noop_block_reason_checked_count}!={shim_executed}"
                    )
                if adapter_live_noop_block_reason_missing_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_missing_count_nonzero="
                        f"{adapter_live_noop_block_reason_missing_count}"
                    )
                if adapter_live_noop_block_reason_mismatch_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_mismatch_count_nonzero="
                        f"{adapter_live_noop_block_reason_mismatch_count}"
                    )
                if adapter_enabled_count != expected_adapter_enabled_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count_mismatch="
                        f"{adapter_enabled_count}!={expected_adapter_enabled_count}"
                    )
                if adapter_lab_gate_passed_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count_mismatch="
                        f"{adapter_lab_gate_passed_count}!={shim_executed}"
                    )
                if adapter_live_noop_record_ready_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_count_mismatch="
                        f"{adapter_live_noop_record_ready_count}!={shim_executed}"
                    )
                if adapter_live_noop_blocked_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_count_mismatch="
                        f"{adapter_live_noop_blocked_count}!={shim_executed}"
                    )
                if adapter_consumer_adapter_present_count != shim_executed:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count_mismatch="
                        f"{adapter_consumer_adapter_present_count}!={shim_executed}"
                    )
                if (
                    adapter_consumer_connected_count
                    != expected_adapter_consumer_connected_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count_mismatch="
                        f"{adapter_consumer_connected_count}!={expected_adapter_consumer_connected_count}"
                    )
                if adapter_live_eligible_count != expected_adapter_live_eligible_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count_mismatch="
                        f"{adapter_live_eligible_count}!={expected_adapter_live_eligible_count}"
                    )
                if adapter_blocked_count != expected_adapter_blocked_count:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count_mismatch="
                        f"{adapter_blocked_count}!={expected_adapter_blocked_count}"
                    )
                if adapter_payload_bytes != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes_nonzero="
                        f"{adapter_payload_bytes}"
                    )
                if adapter_payload_violation_count != 0:
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_violation_count_nonzero="
                        f"{adapter_payload_violation_count}"
                    )
                if (
                    adapter_passed_to_kernel_count
                    != expected_adapter_passed_to_kernel_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count_mismatch="
                        f"{adapter_passed_to_kernel_count}!={expected_adapter_passed_to_kernel_count}"
                    )
                if (
                    adapter_kernel_arg_violation_count
                    != expected_adapter_changes_kernel_args_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count_mismatch="
                        f"{adapter_kernel_arg_violation_count}!={expected_adapter_changes_kernel_args_count}"
                    )
                if (
                    adapter_changes_kernel_launch_args_count
                    != expected_adapter_changes_kernel_args_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count_mismatch="
                        f"{adapter_changes_kernel_launch_args_count}!={expected_adapter_changes_kernel_args_count}"
                    )
                if (
                    adapter_contract_live_pass_count
                    != expected_adapter_contract_live_pass_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count_mismatch="
                        f"{adapter_contract_live_pass_count}!={expected_adapter_contract_live_pass_count}"
                    )
                if (
                    adapter_real_kernel_arg_handoff_count
                    != expected_adapter_real_kernel_arg_handoff_count
                ):
                    failures.append(
                        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count_mismatch="
                        f"{adapter_real_kernel_arg_handoff_count}!={expected_adapter_real_kernel_arg_handoff_count}"
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
    live_mutation_package_seen_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count"
        )
    )
    live_mutation_package_pass_through_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count"
        )
    )
    live_mutation_package_missing_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_package_missing_count"
        )
    )
    live_mutation_package_layer_mismatch_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_package_layer_mismatch_count"
        )
    )
    live_mutation_package_block_reason_mismatch_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_package_block_reason_mismatch_count"
        )
    )
    single_field_replacement_candidate_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_candidate_count"
        )
    )
    single_field_replacement_parity_ok_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_ok_count"
        )
    )
    single_field_replacement_parity_mismatch_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_mismatch_count"
        )
    )
    single_field_replacement_source_missing_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_source_missing_count"
        )
    )
    single_field_replacement_unsupported_field_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_unsupported_field_count"
        )
    )
    single_field_replacement_passed_to_kernel_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count"
        )
    )
    single_field_replacement_payload_bytes = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes"
        )
    )
    single_field_replacement_live_disabled_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_disabled_count"
        )
    )
    single_field_replacement_live_candidate_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_candidate_count"
        )
    )
    single_field_replacement_live_replaced_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_replaced_count"
        )
    )
    single_field_replacement_live_parity_ok_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_ok_count"
        )
    )
    single_field_replacement_live_parity_mismatch_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_mismatch_count"
        )
    )
    single_field_replacement_live_passed_to_kernel_count = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count"
        )
    )
    single_field_replacement_live_payload_bytes = _as_int(
        aggregate.get(
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes"
        )
    )
    if not _as_bool(single_field_replacement_live_enabled):
        if (
            not _as_bool(single_field_replacement_dry_run_enabled)
            and single_field_replacement_live_disabled_count != 0
        ):
            failures.append(
                "single_field_replacement_live_disabled_count_nonzero_without_dry_run="
                f"{single_field_replacement_live_disabled_count}"
            )
        for name, count in (
            ("candidate_count", single_field_replacement_live_candidate_count),
            ("replaced_count", single_field_replacement_live_replaced_count),
            ("parity_ok_count", single_field_replacement_live_parity_ok_count),
            (
                "parity_mismatch_count",
                single_field_replacement_live_parity_mismatch_count,
            ),
            (
                "passed_to_kernel_count",
                single_field_replacement_live_passed_to_kernel_count,
            ),
            ("payload_bytes", single_field_replacement_live_payload_bytes),
        ):
            if count != 0:
                failures.append(
                    f"single_field_replacement_live_{name}_nonzero={count}"
                )
    if allow_kernel_arg_handoff_live_real_kernel_arg_mutation:
        adapter_real_count = _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count"
            )
        )
        if live_mutation_package_pass_through_count <= 0:
            failures.append(
                "kernel_arg_live_mutation_package_pass_through_count_missing_or_zero"
            )
        if live_mutation_package_pass_through_count < adapter_real_count:
            failures.append(
                "kernel_arg_live_mutation_package_pass_through_count_below_adapter_real_count="
                f"{live_mutation_package_pass_through_count}<{adapter_real_count}"
            )
        if live_mutation_package_seen_count < live_mutation_package_pass_through_count:
            failures.append(
                "kernel_arg_live_mutation_package_seen_count_below_pass_through_count="
                f"{live_mutation_package_seen_count}<"
                f"{live_mutation_package_pass_through_count}"
            )
        for name, count in (
            ("layer_mismatch", live_mutation_package_layer_mismatch_count),
            (
                "block_reason_mismatch",
                live_mutation_package_block_reason_mismatch_count,
            ),
        ):
            if count != 0:
                failures.append(
                    f"kernel_arg_live_mutation_package_{name}_count_nonzero={count}"
                )
    if _as_bool(single_field_replacement_dry_run_enabled):
        if single_field_replacement_candidate_count <= 0:
            failures.append(
                "single_field_replacement_dry_run_candidate_count_missing_or_zero"
            )
        if (
            single_field_replacement_parity_ok_count
            != single_field_replacement_candidate_count
        ):
            failures.append(
                "single_field_replacement_dry_run_parity_ok_count_mismatch="
                f"{single_field_replacement_parity_ok_count}!="
                f"{single_field_replacement_candidate_count}"
            )
        for name, count in (
            ("parity_mismatch", single_field_replacement_parity_mismatch_count),
            ("source_missing", single_field_replacement_source_missing_count),
            ("unsupported_field", single_field_replacement_unsupported_field_count),
            ("passed_to_kernel", single_field_replacement_passed_to_kernel_count),
            ("payload_bytes", single_field_replacement_payload_bytes),
        ):
            if count != 0:
                failures.append(
                    f"single_field_replacement_dry_run_{name}_nonzero={count}"
                )
        if _as_bool(single_field_replacement_live_enabled):
            if not allow_single_field_replacement_live:
                failures.append(
                    "single_field_replacement_live_requires_explicit_allow"
                )
            if single_field_replacement_live_candidate_count <= 0:
                failures.append(
                    "single_field_replacement_live_candidate_count_missing_or_zero"
                )
            if (
                single_field_replacement_live_replaced_count
                != single_field_replacement_live_candidate_count
            ):
                failures.append(
                    "single_field_replacement_live_replaced_count_mismatch="
                    f"{single_field_replacement_live_replaced_count}!="
                    f"{single_field_replacement_live_candidate_count}"
                )
            if (
                single_field_replacement_live_parity_ok_count
                != single_field_replacement_live_candidate_count
            ):
                failures.append(
                    "single_field_replacement_live_parity_ok_count_mismatch="
                    f"{single_field_replacement_live_parity_ok_count}!="
                    f"{single_field_replacement_live_candidate_count}"
                )
            if (
                single_field_replacement_live_passed_to_kernel_count
                != single_field_replacement_live_candidate_count
            ):
                failures.append(
                    "single_field_replacement_live_passed_to_kernel_count_mismatch="
                    f"{single_field_replacement_live_passed_to_kernel_count}!="
                    f"{single_field_replacement_live_candidate_count}"
                )
            if single_field_replacement_live_parity_mismatch_count != 0:
                failures.append(
                    "single_field_replacement_live_parity_mismatch_nonzero="
                    f"{single_field_replacement_live_parity_mismatch_count}"
                )
            if single_field_replacement_live_payload_bytes != 0:
                failures.append(
                    "single_field_replacement_live_payload_bytes_nonzero="
                    f"{single_field_replacement_live_payload_bytes}"
                )
        else:
            if (
                single_field_replacement_live_disabled_count
                != single_field_replacement_candidate_count
            ):
                failures.append(
                    "single_field_replacement_live_disabled_count_mismatch="
                    f"{single_field_replacement_live_disabled_count}!="
                    f"{single_field_replacement_candidate_count}"
                )

    metrics = {
        "row_count": _as_int(summary.get("row_count")),
        "premap_summary_count": premap_count,
        "premap_consumer_mapping_count": consumer_count,
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled": _as_bool(
            kernel_arg_pass_enabled
        ),
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": _as_bool(
            real_kernel_arg_mutation_enabled
        ),
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": _as_bool(
            single_field_replacement_dry_run_enabled
        ),
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled": _as_bool(
            single_field_replacement_live_enabled
        ),
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field": (
            None
            if single_field_replacement_field is None
            else str(single_field_replacement_field)
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count": (
            live_mutation_package_seen_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count": (
            live_mutation_package_pass_through_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_package_missing_count": (
            live_mutation_package_missing_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_package_layer_mismatch_count": (
            live_mutation_package_layer_mismatch_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_package_block_reason_mismatch_count": (
            live_mutation_package_block_reason_mismatch_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_candidate_count": (
            single_field_replacement_candidate_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_ok_count": (
            single_field_replacement_parity_ok_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_mismatch_count": (
            single_field_replacement_parity_mismatch_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_source_missing_count": (
            single_field_replacement_source_missing_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_unsupported_field_count": (
            single_field_replacement_unsupported_field_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count": (
            single_field_replacement_passed_to_kernel_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes": (
            single_field_replacement_payload_bytes
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_disabled_count": (
            single_field_replacement_live_disabled_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_candidate_count": (
            single_field_replacement_live_candidate_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_replaced_count": (
            single_field_replacement_live_replaced_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_ok_count": (
            single_field_replacement_live_parity_ok_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_mismatch_count": (
            single_field_replacement_live_parity_mismatch_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count": (
            single_field_replacement_live_passed_to_kernel_count
        ),
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes": (
            single_field_replacement_live_payload_bytes
        ),
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
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count"
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
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason": str(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count": _as_int(
            aggregate.get(
                "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_toggle_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_toggle_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}launch_schema_mirror_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}launch_schema_mirror_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}table_object_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}table_object_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode": str(
            aggregate.get(f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode")
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_mismatch_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason": str(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_mismatch_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}block_reason_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}enabled_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}lab_gate_passed_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_toggle_record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}launch_schema_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}live_eligible_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}consumer_connected_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}blocked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_violation_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_kernel_arg_violation_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}kernel_arg_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}changes_kernel_launch_args_count",
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_NOOP_INTEGRATION_PREFIX}kernel_arg_violation_count"
                ),
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}launch_schema_mirror_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}launch_schema_mirror_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}table_object_hash_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}table_object_hash_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode": str(
            aggregate.get(f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode")
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_mismatch_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}mode_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason": str(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}block_reason_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason": str(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason"
            )
            or ""
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_checked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason_checked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_missing_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason_missing_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_mismatch_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_block_reason_mismatch_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}enabled_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}lab_gate_passed_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_record_ready_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_noop_integration_blocked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}consumer_adapter_present_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}consumer_connected_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}live_eligible_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}blocked_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}payload_bytes"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_violation_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}payload_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}passed_to_kernel_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}kernel_arg_violation_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}changes_kernel_launch_args_count",
                aggregate.get(
                    f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}kernel_arg_violation_count"
                ),
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}contract_live_pass_count"
            )
        ),
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count": _as_int(
            aggregate.get(
                f"{KERNEL_ARG_HANDOFF_LIVE_CONSUMER_ADAPTER_PREFIX}real_kernel_arg_handoff_count"
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
        "require_kernel_arg_handoff_live_toggle": bool(
            require_kernel_arg_handoff_live_toggle
        ),
        "require_kernel_arg_handoff_live_noop_integration": bool(
            require_kernel_arg_handoff_live_noop_integration
        ),
        "require_kernel_arg_handoff_launch_schema_mirror": bool(
            require_kernel_arg_handoff_launch_schema_mirror
        ),
        "require_kernel_arg_handoff_live_consumer_adapter": bool(
            require_kernel_arg_handoff_live_consumer_adapter
        ),
        "allow_enabled_blocked_live_toggle": bool(
            allow_enabled_blocked_live_toggle
        ),
        "allow_connected_blocked_consumer_adapter": bool(
            allow_connected_blocked_consumer_adapter
        ),
        "allow_kernel_arg_handoff_live_kernel_arg_pass": bool(
            allow_kernel_arg_handoff_live_kernel_arg_pass
        ),
        "allow_kernel_arg_handoff_live_real_kernel_arg_mutation": bool(
            allow_kernel_arg_handoff_live_real_kernel_arg_mutation
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
    parser.add_argument(
        "--require-kernel-arg-handoff-live-toggle",
        action="store_true",
        help=(
            "Require the default-disabled live kernel-argument handoff toggle "
            "record. The toggle must be lab-gated, blocked, zero-payload, and "
            "must not pass arguments to a kernel."
        ),
    )
    parser.add_argument(
        "--require-kernel-arg-handoff-live-noop-integration",
        action="store_true",
        help=(
            "Require the final no-op integration record after the live toggle. "
            "The record must join the live toggle with the launch-schema "
            "mirror, remain blocked, zero-payload, and not pass arguments to a "
            "kernel."
        ),
    )
    parser.add_argument(
        "--require-kernel-arg-handoff-launch-schema-mirror",
        action="store_true",
        help=(
            "Require the prelaunch launch-schema mirror of the future fused "
            "MoE/AWQ kernel argument package. The mirror must be ready, "
            "schema-stable, zero-payload, and not passed to a kernel."
        ),
    )
    parser.add_argument(
        "--require-kernel-arg-handoff-live-consumer-adapter",
        action="store_true",
        help=(
            "Require the default-disabled live consumer adapter envelope. The "
            "adapter must be present, checked, lab-gated, disconnected, "
            "blocked, zero-payload, and must not pass arguments to a kernel."
        ),
    )
    parser.add_argument(
        "--allow-enabled-blocked-live-toggle",
        action="store_true",
        help=(
            "Canary-only mode: allow the live handoff toggle to be enabled and "
            "live-eligible, but still require it to remain blocked with zero "
            "payload and no kernel argument handoff."
        ),
    )
    parser.add_argument(
        "--allow-connected-blocked-consumer-adapter",
        action="store_true",
        help=(
            "Canary-only mode: allow the prelaunch consumer adapter to report "
            "consumer_connected=true, while still requiring it to remain "
            "blocked with zero payload and no kernel argument mutation."
        ),
    )
    parser.add_argument(
        "--allow-kernel-arg-handoff-live-kernel-arg-pass",
        action="store_true",
        help=(
            "Experimental live mode: allow the prelaunch consumer adapter to "
            "accept the mirrored kernel-argument package. This still requires "
            "zero payload bytes and must be used only with the explicit lab "
            "gate that enables live kernel-arg pass."
        ),
    )
    parser.add_argument(
        "--allow-kernel-arg-handoff-live-real-kernel-arg-mutation",
        action="store_true",
        help=(
            "Experimental live mode: allow the original WNA16 kernel launch to "
            "take its pass-through arguments from the prelaunch handoff package. "
            "This still requires zero payload bytes and an explicit lab gate."
        ),
    )
    parser.add_argument(
        "--allow-single-field-replacement-live",
        action="store_true",
        help=(
            "Experimental live mode: allow one kernel-argument field to be "
            "replaced from the prepared shadow package. This is disabled by "
            "default and must be paired with an explicit runtime flag."
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
        require_kernel_arg_handoff_live_toggle=(
            args.require_kernel_arg_handoff_live_toggle
        ),
        require_kernel_arg_handoff_live_noop_integration=(
            args.require_kernel_arg_handoff_live_noop_integration
        ),
        require_kernel_arg_handoff_launch_schema_mirror=(
            args.require_kernel_arg_handoff_launch_schema_mirror
        ),
        require_kernel_arg_handoff_live_consumer_adapter=(
            args.require_kernel_arg_handoff_live_consumer_adapter
        ),
        allow_enabled_blocked_live_toggle=(
            args.allow_enabled_blocked_live_toggle
        ),
        allow_connected_blocked_consumer_adapter=(
            args.allow_connected_blocked_consumer_adapter
        ),
        allow_kernel_arg_handoff_live_kernel_arg_pass=(
            args.allow_kernel_arg_handoff_live_kernel_arg_pass
        ),
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=(
            args.allow_kernel_arg_handoff_live_real_kernel_arg_mutation
        ),
        allow_single_field_replacement_live=(
            args.allow_single_field_replacement_live
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
