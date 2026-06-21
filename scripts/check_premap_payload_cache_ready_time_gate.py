#!/usr/bin/env python3
"""Check the ready-time payload-cache gate.

This gate validates the accounting evidence for a future full-payload cache
manager.  It does not claim endpoint latency improvement and it does not
require full_fetch to be enabled.  A valid measured-copy run may deliberately
produce a blocked decision when payloads are not ready before demand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


_DIRECT_SNAPSHOT_TRANSITION_ISSUE_SOURCES = frozenset(
    {
        "previous_token_transition_premap_shadow",
        "prelaunch_observed_transition_premap_shadow",
    }
)
_DIRECT_RUNTIME_PARTICIPATION_ALLOWED_STATUSES = frozenset(
    {
        "ready_time_candidate_requires_lab_gate",
        "accounting_only_no_issued_fetch",
        "accounting_only_no_used_fetch",
        "accounting_only_all_demands_ready_late",
    }
)
_DIRECT_RUNTIME_PLAN_ALLOWED_STATUSES = frozenset(
    {
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch",
        "participation_not_full_fetch_candidate:accounting_only_no_issued_fetch",
        "participation_not_full_fetch_candidate:accounting_only_no_used_fetch",
        "participation_not_full_fetch_candidate:accounting_only_all_demands_ready_late",
    }
)
_DIRECT_RUNTIME_PLAN_RAW_FIELDS = (
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_present",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_stage",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_status",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_consumes_participation",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_participation_status",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_live_payload_runtime_enabled",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_planned_issue_count",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_payload_bytes",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_ready_credit",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_kernel_arg_pass_allowed",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_changes_kernel_launch_args",
    "runtime_shadow_premap_payload_cache_direct_runtime_plan_full_fetch_runtime_allowed",
)
_DIRECT_RUNTIME_EXECUTION_RAW_FIELDS = (
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_present",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_stage",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_status",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_consumes_plan",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_plan_status",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_decision",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_live_payload_runtime_enabled",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_runtime_enabled",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_full_fetch_runtime_allowed",
)


def _runtime_plan_status_from_participation(status: str) -> str:
    if status == "ready_time_candidate_requires_lab_gate":
        return "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    return f"participation_not_full_fetch_candidate:{status}"


def check_summary(
    summary: dict[str, Any],
    *,
    root: Path,
    require_measured_copy: bool = True,
    min_demand_hit_rate: float = 0.10,
    max_ready_late_miss_rate: float = 0.20,
    min_used_per_issued_fetch: float = 0.10,
    min_manager_rows: int = 1,
    min_demand_count: int = 1,
) -> dict[str, Any]:
    metrics = _normalize_summary(summary)
    failures: list[str] = []

    mode = str(
        metrics.get("runtime_shadow_premap_payload_cache_manager_mode")
        or metrics.get("premap_payload_cache_manager_mode")
        or ""
    )
    if mode != "ready_time":
        failures.append(f"mode_not_ready_time:{mode or '<missing>'}")

    direct_snapshot_present = bool(
        metrics.get("runtime_shadow_premap_payload_cache_direct_snapshot_present")
    )
    if direct_snapshot_present:
        _validate_direct_snapshot(metrics, failures)

    manager_count = _as_int(
        _first_present(
            metrics.get("runtime_shadow_aggregate_premap_payload_cache_manager_count"),
            metrics.get("premap_payload_cache_manager_count"),
            1 if direct_snapshot_present else None,
        )
    )
    demand_count = _as_int(
        _first_present(
            metrics.get("runtime_shadow_aggregate_premap_payload_cache_demand_count"),
            metrics.get("premap_payload_cache_demand_count"),
            metrics.get("runtime_shadow_premap_payload_cache_direct_demand_count"),
        )
    )
    demand_hit_count = _as_int(
        _first_present(
            metrics.get(
                "runtime_shadow_aggregate_premap_payload_cache_demand_hit_count"
            ),
            metrics.get("premap_payload_cache_demand_hit_count"),
            metrics.get("runtime_shadow_premap_payload_cache_direct_demand_hit_count"),
        )
    )
    ready_late_miss_count = _as_int(
        _first_present(
            metrics.get(
                "runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count"
            ),
            metrics.get("premap_payload_cache_ready_late_miss_count"),
            metrics.get(
                "runtime_shadow_premap_payload_cache_direct_ready_late_miss_count"
            ),
        )
    )
    issued_fetch_count = _as_int(
        _first_present(
            metrics.get(
                "runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count"
            ),
            metrics.get("premap_payload_cache_issued_fetch_count"),
            metrics.get(
                "runtime_shadow_premap_payload_cache_direct_issued_fetch_count"
            ),
        )
    )
    used_fetch_count = _as_int(
        _first_present(
            metrics.get("runtime_shadow_aggregate_premap_payload_cache_used_fetch_count"),
            metrics.get("premap_payload_cache_used_fetch_count"),
            metrics.get("runtime_shadow_premap_payload_cache_direct_used_fetch_count"),
        )
    )
    queue_batch_size = _as_int(
        _first_present(
            metrics.get("runtime_shadow_premap_payload_cache_manager_queue_batch_size"),
            metrics.get(
                "runtime_shadow_aggregate_premap_payload_cache_queue_batch_size_max"
            ),
            metrics.get("premap_payload_cache_queue_batch_size_max"),
            metrics.get("runtime_shadow_premap_payload_cache_direct_queue_batch_size"),
        )
    )
    queue_deadline_us = _as_float(
        _first_present(
            metrics.get("runtime_shadow_premap_payload_cache_manager_queue_deadline_us"),
            metrics.get(
                "runtime_shadow_aggregate_premap_payload_cache_queue_deadline_us_max"
            ),
            metrics.get("premap_payload_cache_queue_deadline_us_max"),
            metrics.get("runtime_shadow_premap_payload_cache_direct_queue_deadline_us"),
        )
    )
    measured_copy_path = metrics.get(
        "runtime_shadow_premap_payload_cache_manager_measured_copy_path"
    )
    measured_copy_effective_gbps = _as_float(
        metrics.get(
            "runtime_shadow_premap_payload_cache_manager_measured_copy_effective_gbps"
        )
    )
    measured_copy_us_per_issue = _as_float(
        metrics.get(
            "runtime_shadow_premap_payload_cache_manager_measured_copy_us_per_issue"
        )
        or metrics.get("runtime_shadow_premap_payload_cache_manager_service_us_per_issue")
    )

    if manager_count < int(min_manager_rows):
        failures.append(f"manager_rows_too_low:{manager_count}")
    if demand_count < int(min_demand_count):
        failures.append(f"demand_count_too_low:{demand_count}")
    if require_measured_copy:
        if not measured_copy_path:
            failures.append("measured_copy_path_missing")
        else:
            path = Path(str(measured_copy_path)).expanduser()
            if not path.is_absolute():
                path = root / path
            if not path.exists():
                failures.append(f"measured_copy_path_missing_on_disk:{path}")
        if measured_copy_us_per_issue <= 0.0:
            failures.append(
                f"measured_copy_us_per_issue_nonpositive:{measured_copy_us_per_issue}"
            )
    if queue_batch_size <= 0:
        failures.append(f"queue_batch_size_nonpositive:{queue_batch_size}")
    if queue_deadline_us <= 0.0:
        failures.append(f"queue_deadline_us_nonpositive:{queue_deadline_us}")

    demand_hit_rate = (
        float(demand_hit_count) / float(demand_count) if demand_count > 0 else 0.0
    )
    ready_late_miss_rate = (
        float(ready_late_miss_count) / float(demand_count)
        if demand_count > 0
        else 0.0
    )
    used_per_issued_fetch = (
        float(used_fetch_count) / float(issued_fetch_count)
        if issued_fetch_count > 0
        else 0.0
    )
    allow_full_fetch = (
        not failures
        and demand_hit_rate >= float(min_demand_hit_rate)
        and ready_late_miss_rate <= float(max_ready_late_miss_rate)
        and used_per_issued_fetch >= float(min_used_per_issued_fetch)
    )
    threshold_failures: list[str] = []
    if not failures and demand_hit_rate < float(min_demand_hit_rate):
        threshold_failures.append("demand_hit_rate_below_threshold")
    if not failures and ready_late_miss_rate > float(max_ready_late_miss_rate):
        threshold_failures.append("ready_late_miss_rate_above_threshold")
    if not failures and used_per_issued_fetch < float(min_used_per_issued_fetch):
        threshold_failures.append("used_per_issued_fetch_below_threshold")
    decision_reason = (
        "allow"
        if allow_full_fetch
        else ("invalid_evidence" if failures else "full_fetch_threshold_not_met")
    )

    return {
        "passed": not failures,
        "failures": failures,
        "allow_full_fetch": allow_full_fetch,
        "decision_reason": decision_reason,
        "threshold_failures": threshold_failures,
        "boundary": (
            "ready-time payload-cache accounting gate only; not endpoint TPOT "
            "and not a real payload-transfer runtime claim"
        ),
        "metrics": {
            "mode": mode,
            "manager_count": manager_count,
            "demand_count": demand_count,
            "demand_hit_count": demand_hit_count,
            "demand_hit_rate": demand_hit_rate,
            "ready_late_miss_count": ready_late_miss_count,
            "ready_late_miss_rate": ready_late_miss_rate,
            "issued_fetch_count": issued_fetch_count,
            "used_fetch_count": used_fetch_count,
            "used_per_issued_fetch": used_per_issued_fetch,
            "queue_batch_size": queue_batch_size,
            "queue_deadline_us": queue_deadline_us,
            "measured_copy_path": measured_copy_path,
            "measured_copy_effective_gbps": measured_copy_effective_gbps,
            "measured_copy_us_per_issue": measured_copy_us_per_issue,
            "min_demand_hit_rate": float(min_demand_hit_rate),
            "max_ready_late_miss_rate": float(max_ready_late_miss_rate),
            "min_used_per_issued_fetch": float(min_used_per_issued_fetch),
            "direct_snapshot_present": direct_snapshot_present,
            "direct_manager_mode": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_manager_mode"
            ),
            "direct_demand_count": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_demand_count"
            ),
            "direct_demand_hit_count": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_demand_hit_count"
            ),
            "direct_ready_late_miss_count": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_ready_late_miss_count"
            ),
            "direct_issued_fetch_count": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_issued_fetch_count"
            ),
            "direct_used_fetch_count": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_used_fetch_count"
            ),
            "direct_queue_batch_size": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_queue_batch_size"
            ),
            "direct_queue_deadline_us": metrics.get(
                "runtime_shadow_premap_payload_cache_direct_queue_deadline_us"
            ),
            **_direct_snapshot_report_metrics(metrics),
        },
    }


def _normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary.get("metrics")
    if isinstance(metrics, dict):
        return _with_gate_metric_aliases(metrics)
    return dict(summary)


def _with_gate_metric_aliases(metrics: dict[str, Any]) -> dict[str, Any]:
    """Accept both raw performance summaries and checker-report metrics.

    Checker reports intentionally store normalized metric names such as
    ``demand_count``.  Raw runtime summaries use longer
    ``runtime_shadow_*`` keys.  The checker may be run on either artifact, so
    normalize report-style names back into the raw-key namespace used by the
    validation code above.
    """

    aliases = {
        "mode": "runtime_shadow_premap_payload_cache_manager_mode",
        "manager_count": "runtime_shadow_aggregate_premap_payload_cache_manager_count",
        "demand_count": "runtime_shadow_aggregate_premap_payload_cache_demand_count",
        "demand_hit_count": (
            "runtime_shadow_aggregate_premap_payload_cache_demand_hit_count"
        ),
        "ready_late_miss_count": (
            "runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count"
        ),
        "issued_fetch_count": (
            "runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count"
        ),
        "used_fetch_count": (
            "runtime_shadow_aggregate_premap_payload_cache_used_fetch_count"
        ),
        "queue_batch_size": (
            "runtime_shadow_premap_payload_cache_manager_queue_batch_size"
        ),
        "queue_deadline_us": (
            "runtime_shadow_premap_payload_cache_manager_queue_deadline_us"
        ),
        "measured_copy_path": (
            "runtime_shadow_premap_payload_cache_manager_measured_copy_path"
        ),
        "measured_copy_effective_gbps": (
            "runtime_shadow_premap_payload_cache_manager_measured_copy_effective_gbps"
        ),
        "measured_copy_us_per_issue": (
            "runtime_shadow_premap_payload_cache_manager_measured_copy_us_per_issue"
        ),
        "direct_snapshot_present": (
            "runtime_shadow_premap_payload_cache_direct_snapshot_present"
        ),
        "direct_manager_mode": (
            "runtime_shadow_premap_payload_cache_direct_manager_mode"
        ),
        "direct_demand_count": (
            "runtime_shadow_premap_payload_cache_direct_demand_count"
        ),
        "direct_demand_hit_count": (
            "runtime_shadow_premap_payload_cache_direct_demand_hit_count"
        ),
        "direct_ready_late_miss_count": (
            "runtime_shadow_premap_payload_cache_direct_ready_late_miss_count"
        ),
        "direct_issued_fetch_count": (
            "runtime_shadow_premap_payload_cache_direct_issued_fetch_count"
        ),
        "direct_used_fetch_count": (
            "runtime_shadow_premap_payload_cache_direct_used_fetch_count"
        ),
        "direct_queue_batch_size": (
            "runtime_shadow_premap_payload_cache_direct_queue_batch_size"
        ),
        "direct_queue_deadline_us": (
            "runtime_shadow_premap_payload_cache_direct_queue_deadline_us"
        ),
        "direct_snapshot_runtime_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_stage"
        ),
        "direct_snapshot_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_payload_bytes"
        ),
        "direct_snapshot_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_ready_credit"
        ),
        "direct_snapshot_real_ready_credit_granted": (
            "runtime_shadow_premap_payload_cache_direct_real_ready_credit_granted"
        ),
        "direct_snapshot_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_changes_kernel_launch_args"
        ),
        "direct_snapshot_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_full_fetch_runtime_allowed"
        ),
        "direct_snapshot_payload_transfer_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_payload_transfer_runtime_enabled"
        ),
        "direct_snapshot_demand_on_consumer": (
            "runtime_shadow_premap_payload_cache_direct_demand_on_consumer"
        ),
        "direct_snapshot_issue_sources": (
            "runtime_shadow_premap_payload_cache_direct_issue_sources"
        ),
        "direct_snapshot_runtime_participation_present": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_present"
        ),
        "direct_snapshot_runtime_participation_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_stage"
        ),
        "direct_snapshot_runtime_participation_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_status"
        ),
        "direct_snapshot_runtime_participation_consumes_manager_snapshot": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_consumes_manager_snapshot"
        ),
        "direct_snapshot_runtime_participation_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_payload_bytes"
        ),
        "direct_snapshot_runtime_participation_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_ready_credit"
        ),
        "direct_snapshot_runtime_participation_real_ready_credit_granted": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_real_ready_credit_granted"
        ),
        "direct_snapshot_runtime_participation_kernel_arg_pass_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_kernel_arg_pass_allowed"
        ),
        "direct_snapshot_runtime_participation_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_changes_kernel_launch_args"
        ),
        "direct_snapshot_runtime_participation_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_full_fetch_runtime_allowed"
        ),
        "direct_snapshot_runtime_participation_payload_transfer_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_payload_transfer_runtime_enabled"
        ),
        "direct_snapshot_runtime_participation_issue_sources": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_issue_sources"
        ),
        "direct_snapshot_runtime_participation_candidate_reason": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_candidate_reason"
        ),
        "direct_snapshot_runtime_plan_present": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_present"
        ),
        "direct_snapshot_runtime_plan_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_stage"
        ),
        "direct_snapshot_runtime_plan_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_status"
        ),
        "direct_snapshot_runtime_plan_consumes_participation": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_consumes_participation"
        ),
        "direct_snapshot_runtime_plan_participation_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_participation_status"
        ),
        "direct_snapshot_runtime_plan_live_payload_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_live_payload_runtime_enabled"
        ),
        "direct_snapshot_runtime_plan_planned_issue_count": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_planned_issue_count"
        ),
        "direct_snapshot_runtime_plan_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_payload_bytes"
        ),
        "direct_snapshot_runtime_plan_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_ready_credit"
        ),
        "direct_snapshot_runtime_plan_kernel_arg_pass_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_kernel_arg_pass_allowed"
        ),
        "direct_snapshot_runtime_plan_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_changes_kernel_launch_args"
        ),
        "direct_snapshot_runtime_plan_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_full_fetch_runtime_allowed"
        ),
        "direct_snapshot_runtime_execution_present": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_present"
        ),
        "direct_snapshot_runtime_execution_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_stage"
        ),
        "direct_snapshot_runtime_execution_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_status"
        ),
        "direct_snapshot_runtime_execution_consumes_plan": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_consumes_plan"
        ),
        "direct_snapshot_runtime_execution_plan_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_plan_status"
        ),
        "direct_snapshot_runtime_execution_decision": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_decision"
        ),
        "direct_snapshot_runtime_execution_block_reason": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason"
        ),
        "direct_snapshot_runtime_execution_execution_mode": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode"
        ),
        "direct_snapshot_runtime_execution_live_payload_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_live_payload_runtime_enabled"
        ),
        "direct_snapshot_runtime_execution_payload_transfer_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_runtime_enabled"
        ),
        "direct_snapshot_runtime_execution_issued_payload_count": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count"
        ),
        "direct_snapshot_runtime_execution_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes"
        ),
        "direct_snapshot_runtime_execution_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit"
        ),
        "direct_snapshot_runtime_execution_real_ready_credit_granted": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted"
        ),
        "direct_snapshot_runtime_execution_kernel_arg_pass_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed"
        ),
        "direct_snapshot_runtime_execution_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args"
        ),
        "direct_snapshot_runtime_execution_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_full_fetch_runtime_allowed"
        ),
    }
    normalized = dict(metrics)
    for short_key, raw_key in aliases.items():
        if raw_key not in normalized and short_key in metrics:
            normalized[raw_key] = metrics[short_key]
    return normalized


def _direct_snapshot_report_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    names = {
        "runtime_stage": "runtime_shadow_premap_payload_cache_direct_runtime_stage",
        "payload_bytes": "runtime_shadow_premap_payload_cache_direct_payload_bytes",
        "ready_credit": "runtime_shadow_premap_payload_cache_direct_ready_credit",
        "real_ready_credit_granted": (
            "runtime_shadow_premap_payload_cache_direct_real_ready_credit_granted"
        ),
        "changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_changes_kernel_launch_args"
        ),
        "full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_full_fetch_runtime_allowed"
        ),
        "payload_transfer_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_payload_transfer_runtime_enabled"
        ),
        "demand_on_consumer": (
            "runtime_shadow_premap_payload_cache_direct_demand_on_consumer"
        ),
        "issue_sources": "runtime_shadow_premap_payload_cache_direct_issue_sources",
        "runtime_participation_present": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_present"
        ),
        "runtime_participation_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_stage"
        ),
        "runtime_participation_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_status"
        ),
        "runtime_participation_consumes_manager_snapshot": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_consumes_manager_snapshot"
        ),
        "runtime_participation_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_payload_bytes"
        ),
        "runtime_participation_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_ready_credit"
        ),
        "runtime_participation_real_ready_credit_granted": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_real_ready_credit_granted"
        ),
        "runtime_participation_kernel_arg_pass_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_kernel_arg_pass_allowed"
        ),
        "runtime_participation_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_changes_kernel_launch_args"
        ),
        "runtime_participation_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_full_fetch_runtime_allowed"
        ),
        "runtime_participation_payload_transfer_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_payload_transfer_runtime_enabled"
        ),
        "runtime_participation_issue_sources": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_issue_sources"
        ),
        "runtime_participation_candidate_reason": (
            "runtime_shadow_premap_payload_cache_direct_runtime_participation_candidate_reason"
        ),
        "runtime_plan_present": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_present"
        ),
        "runtime_plan_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_stage"
        ),
        "runtime_plan_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_status"
        ),
        "runtime_plan_consumes_participation": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_consumes_participation"
        ),
        "runtime_plan_participation_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_participation_status"
        ),
        "runtime_plan_live_payload_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_live_payload_runtime_enabled"
        ),
        "runtime_plan_planned_issue_count": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_planned_issue_count"
        ),
        "runtime_plan_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_payload_bytes"
        ),
        "runtime_plan_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_ready_credit"
        ),
        "runtime_plan_kernel_arg_pass_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_kernel_arg_pass_allowed"
        ),
        "runtime_plan_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_changes_kernel_launch_args"
        ),
        "runtime_plan_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_plan_full_fetch_runtime_allowed"
        ),
        "runtime_execution_present": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_present"
        ),
        "runtime_execution_stage": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_stage"
        ),
        "runtime_execution_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_status"
        ),
        "runtime_execution_consumes_plan": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_consumes_plan"
        ),
        "runtime_execution_plan_status": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_plan_status"
        ),
        "runtime_execution_decision": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_decision"
        ),
        "runtime_execution_block_reason": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason"
        ),
        "runtime_execution_execution_mode": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode"
        ),
        "runtime_execution_live_payload_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_live_payload_runtime_enabled"
        ),
        "runtime_execution_payload_transfer_runtime_enabled": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_runtime_enabled"
        ),
        "runtime_execution_issued_payload_count": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count"
        ),
        "runtime_execution_payload_bytes": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes"
        ),
        "runtime_execution_ready_credit": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit"
        ),
        "runtime_execution_real_ready_credit_granted": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted"
        ),
        "runtime_execution_kernel_arg_pass_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed"
        ),
        "runtime_execution_changes_kernel_launch_args": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args"
        ),
        "runtime_execution_full_fetch_runtime_allowed": (
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_full_fetch_runtime_allowed"
        ),
    }
    return {
        f"direct_snapshot_{name}": metrics.get(raw_key)
        for name, raw_key in names.items()
        if raw_key in metrics
    }


def _validate_direct_snapshot(metrics: dict[str, Any], failures: list[str]) -> None:
    direct_mode = str(
        metrics.get("runtime_shadow_premap_payload_cache_direct_manager_mode") or ""
    )
    if direct_mode != "ready_time":
        failures.append(
            f"direct_snapshot_mode_not_ready_time:{direct_mode or '<missing>'}"
        )
    required_fields = (
        "runtime_shadow_premap_payload_cache_direct_demand_count",
        "runtime_shadow_premap_payload_cache_direct_demand_hit_count",
        "runtime_shadow_premap_payload_cache_direct_ready_late_miss_count",
        "runtime_shadow_premap_payload_cache_direct_issued_fetch_count",
        "runtime_shadow_premap_payload_cache_direct_used_fetch_count",
        "runtime_shadow_premap_payload_cache_direct_queue_batch_size",
        "runtime_shadow_premap_payload_cache_direct_queue_deadline_us",
    )
    for field in required_fields:
        if metrics.get(field) is None:
            failures.append(f"direct_snapshot_field_missing:{field}")
    expected_values = {
        "runtime_shadow_premap_payload_cache_direct_runtime_stage": (
            "online_ready_time_payload_cache_accounting_only"
        ),
        "runtime_shadow_premap_payload_cache_direct_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_ready_credit": False,
        "runtime_shadow_premap_payload_cache_direct_real_ready_credit_granted": False,
        "runtime_shadow_premap_payload_cache_direct_changes_kernel_launch_args": False,
        "runtime_shadow_premap_payload_cache_direct_full_fetch_runtime_allowed": False,
        "runtime_shadow_premap_payload_cache_direct_payload_transfer_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_demand_on_consumer": True,
    }
    for field, expected in expected_values.items():
        if not _direct_snapshot_value_matches(metrics.get(field), expected):
            failures.append(f"direct_snapshot_{field}_mismatch")
    issue_sources = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_issue_sources"
    )
    if not isinstance(issue_sources, list):
        failures.append("direct_snapshot_issue_sources_missing_or_invalid")
    else:
        observed_sources = {str(value) for value in issue_sources}
        if not observed_sources:
            failures.append("direct_snapshot_issue_sources_missing_transition_source")
        elif not observed_sources.issubset(_DIRECT_SNAPSHOT_TRANSITION_ISSUE_SOURCES):
            failures.append("direct_snapshot_issue_sources_contains_non_transition_source")

    _validate_direct_runtime_participation(metrics, failures, issue_sources)
    if any(field in metrics for field in _DIRECT_RUNTIME_PLAN_RAW_FIELDS):
        _validate_direct_runtime_plan(metrics, failures)
    if any(field in metrics for field in _DIRECT_RUNTIME_EXECUTION_RAW_FIELDS):
        _validate_direct_runtime_execution(metrics, failures)


def _validate_direct_runtime_participation(
    metrics: dict[str, Any],
    failures: list[str],
    direct_issue_sources: Any,
) -> None:
    expected_values = {
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_present": True,
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_stage": (
            "online_ready_time_payload_cache_runtime_participation_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_consumes_manager_snapshot": (
            True
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_ready_credit": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_real_ready_credit_granted": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_kernel_arg_pass_allowed": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_changes_kernel_launch_args": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_full_fetch_runtime_allowed": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_payload_transfer_runtime_enabled": (
            False
        ),
    }
    for field, expected in expected_values.items():
        if not _direct_snapshot_value_matches(metrics.get(field), expected):
            failures.append(f"direct_runtime_participation_{field}_mismatch")
    status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_status"
    )
    if not isinstance(status, str) or not status:
        failures.append("direct_runtime_participation_status_missing_or_invalid")
    elif status not in _DIRECT_RUNTIME_PARTICIPATION_ALLOWED_STATUSES:
        failures.append("direct_runtime_participation_status_unsupported")
    issue_sources = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_issue_sources"
    )
    if not isinstance(issue_sources, list):
        failures.append("direct_runtime_participation_issue_sources_missing_or_invalid")
    else:
        observed_sources = {str(value) for value in issue_sources}
        if not observed_sources:
            failures.append("direct_runtime_participation_issue_sources_empty")
        elif not observed_sources.issubset(_DIRECT_SNAPSHOT_TRANSITION_ISSUE_SOURCES):
            failures.append(
                "direct_runtime_participation_issue_sources_contains_non_transition_source"
            )
        if isinstance(direct_issue_sources, list) and (
            observed_sources != {str(value) for value in direct_issue_sources}
        ):
            failures.append(
                "direct_runtime_participation_issue_sources_do_not_match_direct_snapshot"
            )


def _validate_direct_runtime_plan(
    metrics: dict[str, Any],
    failures: list[str],
) -> None:
    expected_values = {
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_present": True,
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_stage": (
            "payload_cache_runtime_plan_lab_gate_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_consumes_participation": (
            True
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_live_payload_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_planned_issue_count": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_ready_credit": False,
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_kernel_arg_pass_allowed": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_changes_kernel_launch_args": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_full_fetch_runtime_allowed": (
            False
        ),
    }
    for field, expected in expected_values.items():
        if not _direct_snapshot_value_matches(metrics.get(field), expected):
            failures.append(f"direct_runtime_plan_{field}_mismatch")

    participation_status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_status"
    )
    plan_participation_status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_participation_status"
    )
    if not isinstance(plan_participation_status, str) or not plan_participation_status:
        failures.append("direct_runtime_plan_participation_status_missing_or_invalid")
    elif plan_participation_status != participation_status:
        failures.append("direct_runtime_plan_participation_status_mismatch")

    status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_status"
    )
    if not isinstance(status, str) or not status:
        failures.append("direct_runtime_plan_status_missing_or_invalid")
    elif status not in _DIRECT_RUNTIME_PLAN_ALLOWED_STATUSES:
        failures.append("direct_runtime_plan_status_unsupported")
    elif isinstance(participation_status, str):
        expected_status = _runtime_plan_status_from_participation(
            participation_status
        )
        if status != expected_status:
            failures.append("direct_runtime_plan_status_mismatch")


def _validate_direct_runtime_execution(
    metrics: dict[str, Any],
    failures: list[str],
) -> None:
    expected_values = {
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_present": True,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_stage": (
            "payload_cache_runtime_execution_lab_gate_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_consumes_plan": (
            True
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_live_payload_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit": False,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_full_fetch_runtime_allowed": (
            False
        ),
    }
    for field, expected in expected_values.items():
        if not _direct_snapshot_value_matches(metrics.get(field), expected):
            failures.append(f"direct_runtime_execution_{field}_mismatch")

    plan_status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_status"
    )
    execution_plan_status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_plan_status"
    )
    if not isinstance(execution_plan_status, str) or not execution_plan_status:
        failures.append("direct_runtime_execution_plan_status_missing_or_invalid")
    elif execution_plan_status != plan_status:
        failures.append("direct_runtime_execution_plan_status_mismatch")

    status = metrics.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_status"
    )
    if not isinstance(status, str) or not status:
        failures.append("direct_runtime_execution_status_missing_or_invalid")
    elif isinstance(plan_status, str):
        expected_status = f"blocked_by_runtime_plan:{plan_status}"
        if status != expected_status:
            failures.append("direct_runtime_execution_status_mismatch")
    decision_key = (
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_decision"
    )
    decision = metrics.get(decision_key)
    if decision_key in metrics and decision != "blocked":
        failures.append("direct_runtime_execution_decision_mismatch")
    block_reason_key = (
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason"
    )
    block_reason = metrics.get(block_reason_key)
    if block_reason_key in metrics and block_reason != plan_status:
        failures.append("direct_runtime_execution_block_reason_mismatch")
    execution_mode_key = (
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode"
    )
    execution_mode = metrics.get(execution_mode_key)
    if (
        execution_mode_key in metrics
        and execution_mode != "payloadless_lab_gate_dry_run"
    ):
        failures.append("direct_runtime_execution_execution_mode_mismatch")


def _direct_snapshot_value_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return type(value) is bool and value is expected
    if isinstance(expected, int):
        return type(value) is int and value == expected
    if isinstance(expected, str):
        return type(value) is str and value == expected
    return value == expected


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("performance_summary", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--expect",
        choices=("any", "allow", "block"),
        default="any",
        help="Optional decision expectation in addition to evidence validity.",
    )
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.10)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.20)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.10)
    parser.add_argument("--min-manager-rows", type=int, default=1)
    parser.add_argument("--min-demand-count", type=int, default=1)
    parser.add_argument("--allow-unmeasured-copy", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = json.loads(args.performance_summary.read_text(encoding="utf-8"))
    result = check_summary(
        summary,
        root=args.root,
        require_measured_copy=not bool(args.allow_unmeasured_copy),
        min_demand_hit_rate=float(args.min_demand_hit_rate),
        max_ready_late_miss_rate=float(args.max_ready_late_miss_rate),
        min_used_per_issued_fetch=float(args.min_used_per_issued_fetch),
        min_manager_rows=int(args.min_manager_rows),
        min_demand_count=int(args.min_demand_count),
    )
    if args.expect == "allow" and not result["allow_full_fetch"]:
        result["passed"] = False
        result["failures"].append("expected_allow_but_blocked")
    if args.expect == "block" and result["allow_full_fetch"]:
        result["passed"] = False
        result["failures"].append("expected_block_but_allowed")
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
