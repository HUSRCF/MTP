#!/usr/bin/env python3
"""Check the default lab gate for prefetch/premap experiments.

This checker combines the current evidence boundary:

* full payload fetch is blocked by measured-copy ready-time evidence;
* metadata is not default-enabled without positive setup evidence;
* premap may be used as a lab path only when setup evidence and address
  capacity evidence both pass.

It is a lab preflight checker, not an endpoint latency benchmark.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.check_premap_payload_cache_stream_shifted_issue_replay_contract import (  # noqa: E402
    check_shifted_issue_replay_contract,
)
from scripts.check_premap_payload_cache_ready_time_gate import (  # noqa: E402
    check_summary as check_ready_time_summary,
)
from mtp_expert_prefetch.runtime import (  # noqa: E402
    build_payload_cache_live_payload_runtime_disabled_canary,
    build_payload_cache_live_payload_stage_preflight,
    build_payload_cache_live_runtime_adapter_accounting_dry_run_canary,
    build_payload_cache_live_runtime_adapter_constructor_binding_preflight,
    build_payload_cache_live_runtime_adapter_instance_construction_plan,
    build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary,
    build_payload_cache_live_runtime_adapter_object_shell_evidence,
    build_payload_cache_live_runtime_adapter_operation_rejection_canary,
    build_payload_cache_live_runtime_adapter_payloadless_instance_canary,
    build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary,
    build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run,
    build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run,
    build_payload_cache_live_runtime_adapter_instantiation_canary,
    build_payload_cache_manager_implementation_artifact,
    build_payload_cache_manager_runtime_snapshot_artifact,
    build_payload_cache_manager_runtime_skeleton,
    build_payload_cache_live_runtime_adapter_materialization_preflight,
    build_payload_cache_live_runtime_adapter_state_object_preflight,
    build_payload_cache_live_runtime_adapter_state_validation_artifact,
    build_payload_cache_live_runtime_adapter_state_validation_preflight,
    build_payload_cache_live_runtime_object_adapter_preflight,
    build_payload_cache_live_runtime_object_construction_preflight,
    build_payload_cache_live_runtime_state_shape_check,
    build_payload_cache_snapshot_backed_live_runtime_disabled_canary,
    build_payload_cache_snapshot_backed_live_runtime_preflight,
    build_payload_cache_queue_budget_runtime_envelope,
)


def check_prefetch_lab_default_gate(path: Path, *, root: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    failures: list[str] = []

    full_fetch = _check_full_fetch(config.get("full_fetch") or {}, root=root)
    metadata = _check_metadata(config.get("metadata") or {}, root=root)
    premap = _check_premap(config.get("premap") or {}, root=root)
    for section_name, section in (
        ("full_fetch", full_fetch),
        ("metadata", metadata),
        ("premap", premap),
    ):
        for failure in section["failures"]:
            failures.append(f"{section_name}:{failure}")

    return {
        "passed": not failures,
        "failures": failures,
        "boundary": (
            "Lab default preflight only; not endpoint TPOT and not a real "
            "vLLM payload/cache-manager performance claim."
        ),
        "gate_id": config.get("gate_id"),
        "decisions": {
            "full_fetch": full_fetch["decision"],
            "metadata": metadata["decision"],
            "premap": premap["decision"],
        },
        "sections": {
            "full_fetch": full_fetch,
            "metadata": metadata,
            "premap": premap,
        },
    }


def _prefixed_payload(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": payload.get(key) for key in payload}


def _check_full_fetch(section: dict[str, Any], *, root: Path) -> dict[str, Any]:
    failures: list[str] = []
    expected_default = bool(section.get("default_enabled", False))
    report_path = _resolve(section.get("ready_time_gate_report"), root=root)
    report = _load_json(report_path, failures, label="ready_time_gate_report")
    passed = bool(report.get("passed", False)) if isinstance(report, dict) else False
    allow = _ready_time_allow_full_fetch(report, failures)
    metrics = report.get("metrics") if isinstance(report, dict) else None
    metrics = metrics if isinstance(metrics, dict) else {}
    stream_decision = _check_optional_stream_decision_gate(section, root, failures)
    stream_feasibility = _check_optional_stream_feasibility(section, root, failures)
    stream_lead_sweep = _check_optional_stream_lead_token_sweep(section, root, failures)
    stream_shifted_issue = _check_stream_shifted_issue_replay_contract(
        section,
        root,
        failures,
    )
    stream_queue_budget = _check_optional_stream_queue_budget_sweep(
        section,
        root,
        failures,
    )
    direct_snapshot = _check_ready_time_direct_snapshot_gate(
        section,
        root,
        failures,
    )
    if not passed:
        failures.append("ready_time_gate_report_not_passed")
    if allow:
        failures.append("ready_time_gate_report_allows_full_fetch")
    if expected_default:
        failures.append("full_fetch_default_enabled_despite_ready_time_block")
    return {
        "decision": "blocked_by_ready_time_measured_copy",
        "failures": failures,
        "default_enabled": expected_default,
        "ready_time_gate_report": str(report_path),
        "ready_time_report_passed": passed,
        "ready_time_allow_full_fetch": allow,
        "ready_time_decision_reason": (
            _ready_time_decision_reason(report) if isinstance(report, dict) else None
        ),
        "ready_time_threshold_failures": _string_list(
            report.get("threshold_failures") if isinstance(report, dict) else None
        ),
        "ready_time_demand_hit_rate": _optional_float(metrics, "demand_hit_rate"),
        "ready_time_ready_late_miss_rate": _optional_float(
            metrics,
            "ready_late_miss_rate",
        ),
        "ready_time_used_per_issued_fetch": _optional_float(
            metrics,
            "used_per_issued_fetch",
        ),
        "ready_time_issued_fetch_count": _optional_int(
            metrics,
            "issued_fetch_count",
        ),
        "ready_time_used_fetch_count": _optional_int(metrics, "used_fetch_count"),
        "ready_time_current_deadline_us": _optional_float(
            report,
            "current_deadline_us",
        ),
        "ready_time_current_lookahead_us": _optional_float(
            report,
            "current_lookahead_us",
        ),
        "ready_time_first_model_passing_deadline_us": _optional_float(
            report,
            "first_model_passing_deadline_us",
        ),
        "ready_time_first_model_passing_lookahead_us": _optional_float(
            report,
            "first_model_passing_lookahead_us",
        ),
        "ready_time_required_lookahead_slack_us": _optional_float(
            report,
            "required_lookahead_slack_us",
        ),
        "ready_time_required_issue_to_demand_lookahead_us": _optional_float(
            report,
            "required_issue_to_demand_lookahead_us",
        ),
        "ready_time_slack_deficit_us": _optional_float(report, "slack_deficit_us"),
        "ready_time_lookahead_deficit_us": _optional_float(
            report,
            "lookahead_deficit_us",
        ),
        "ready_time_model_slack_satisfied": _optional_bool(
            report,
            "ready_time_model_slack_satisfied",
        ),
        "ready_time_model_lookahead_satisfied": _optional_bool(
            report,
            "ready_time_model_lookahead_satisfied",
        ),
        "ready_time_any_model_route_satisfied": _optional_bool(
            report,
            "ready_time_any_model_route_satisfied",
        ),
        **stream_feasibility,
        **stream_decision,
        **stream_lead_sweep,
        **stream_shifted_issue,
        **stream_queue_budget,
        **direct_snapshot,
    }


def _check_ready_time_direct_snapshot_gate(
    section: dict[str, Any],
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    path_value = section.get("ready_time_direct_snapshot_report")
    if path_value in (None, ""):
        failures.append("ready_time_direct_snapshot_report_missing")
        return {
            "ready_time_direct_snapshot_report_present": False,
            "ready_time_direct_snapshot_report": None,
            "ready_time_direct_snapshot_report_passed": None,
        }
    report_path = _resolve(path_value, root=root)
    report = _load_json(
        report_path,
        failures,
        label="ready_time_direct_snapshot_report",
    )
    recheck = (
        check_ready_time_summary(report, root=root)
        if isinstance(report, dict)
        else {"passed": False, "failures": ["ready_time_direct_snapshot_report_invalid"]}
    )
    metrics = report.get("metrics") if isinstance(report, dict) else None
    metrics = metrics if isinstance(metrics, dict) else {}
    passed = bool(report.get("passed", False)) if isinstance(report, dict) else False
    allow = bool(report.get("allow_full_fetch", False)) if isinstance(report, dict) else False
    recheck_passed = bool(recheck.get("passed", False))
    recheck_failures = _string_list(recheck.get("failures"))
    direct_present = _optional_bool(metrics, "direct_snapshot_present")
    runtime_stage = metrics.get("direct_snapshot_runtime_stage")
    payload_bytes = _optional_int(metrics, "direct_snapshot_payload_bytes")
    issue_sources = metrics.get("direct_snapshot_issue_sources")
    runtime_participation_present = _optional_bool(
        metrics,
        "direct_snapshot_runtime_participation_present",
    )
    runtime_participation_stage = metrics.get(
        "direct_snapshot_runtime_participation_stage"
    )
    runtime_participation_status = metrics.get(
        "direct_snapshot_runtime_participation_status"
    )
    runtime_participation_payload_bytes = _optional_int(
        metrics,
        "direct_snapshot_runtime_participation_payload_bytes",
    )
    runtime_participation_issue_sources = metrics.get(
        "direct_snapshot_runtime_participation_issue_sources"
    )
    runtime_participation_status_label = (
        runtime_participation_status
        if isinstance(runtime_participation_status, str)
        else None
    )
    if runtime_participation_status_label == "ready_time_candidate_requires_lab_gate":
        runtime_plan_status = "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    else:
        runtime_plan_status = (
            f"participation_not_full_fetch_candidate:{runtime_participation_status_label}"
        )
    runtime_execution_present = _optional_bool(
        metrics,
        "direct_snapshot_runtime_execution_present",
    )
    runtime_execution_stage = metrics.get("direct_snapshot_runtime_execution_stage")
    runtime_execution_status = metrics.get("direct_snapshot_runtime_execution_status")
    runtime_execution_plan_status = metrics.get(
        "direct_snapshot_runtime_execution_plan_status"
    )
    runtime_execution_decision = metrics.get(
        "direct_snapshot_runtime_execution_decision"
    )
    runtime_execution_block_reason = metrics.get(
        "direct_snapshot_runtime_execution_block_reason"
    )
    runtime_execution_execution_mode = metrics.get(
        "direct_snapshot_runtime_execution_execution_mode"
    )
    runtime_execution_payload_bytes = _optional_int(
        metrics,
        "direct_snapshot_runtime_execution_payload_bytes",
    )
    runtime_execution_issued_payload_count = _optional_int(
        metrics,
        "direct_snapshot_runtime_execution_issued_payload_count",
    )
    runtime_execution_status_label = (
        runtime_execution_status if isinstance(runtime_execution_status, str) else None
    )
    if not passed:
        failures.append("ready_time_direct_snapshot_report_not_passed")
    if not recheck_passed:
        failures.append("ready_time_direct_snapshot_report_recheck_failed")
    if allow:
        failures.append("ready_time_direct_snapshot_report_allows_full_fetch")
    if direct_present is not True:
        failures.append("ready_time_direct_snapshot_not_present")
    if runtime_stage != "online_ready_time_payload_cache_accounting_only":
        failures.append("ready_time_direct_snapshot_runtime_stage_mismatch")
    if payload_bytes != 0:
        failures.append("ready_time_direct_snapshot_payload_bytes_mismatch")
    if metrics.get("direct_snapshot_full_fetch_runtime_allowed") is not False:
        failures.append("ready_time_direct_snapshot_full_fetch_runtime_allowed")
    if metrics.get("direct_snapshot_changes_kernel_launch_args") is not False:
        failures.append("ready_time_direct_snapshot_changes_kernel_launch_args")
    if runtime_participation_present is not True:
        failures.append("ready_time_direct_snapshot_runtime_participation_not_present")
    if (
        runtime_participation_stage
        != "online_ready_time_payload_cache_runtime_participation_dry_run"
    ):
        failures.append("ready_time_direct_snapshot_runtime_participation_stage_mismatch")
    if (
        not isinstance(runtime_participation_status, str)
        or not runtime_participation_status
    ):
        failures.append("ready_time_direct_snapshot_runtime_participation_status_invalid")
    if runtime_participation_payload_bytes != 0:
        failures.append(
            "ready_time_direct_snapshot_runtime_participation_payload_bytes_mismatch"
        )
    if metrics.get("direct_snapshot_runtime_participation_ready_credit") is not False:
        failures.append("ready_time_direct_snapshot_runtime_participation_ready_credit")
    if (
        metrics.get("direct_snapshot_runtime_participation_real_ready_credit_granted")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_participation_real_ready_credit_granted"
        )
    if (
        metrics.get("direct_snapshot_runtime_participation_kernel_arg_pass_allowed")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_participation_kernel_arg_pass_allowed"
        )
    if (
        metrics.get("direct_snapshot_runtime_participation_changes_kernel_launch_args")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_participation_changes_kernel_launch_args"
        )
    if (
        metrics.get("direct_snapshot_runtime_participation_full_fetch_runtime_allowed")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_participation_full_fetch_runtime_allowed"
        )
    if (
        metrics.get(
            "direct_snapshot_runtime_participation_payload_transfer_runtime_enabled"
        )
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_participation_payload_transfer_runtime_enabled"
        )
    if runtime_execution_present is not True:
        failures.append("ready_time_direct_snapshot_runtime_execution_not_present")
    if runtime_execution_stage != "payload_cache_runtime_execution_lab_gate_dry_run":
        failures.append("ready_time_direct_snapshot_runtime_execution_stage_mismatch")
    if runtime_execution_plan_status != runtime_plan_status:
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_plan_status_mismatch"
        )
    expected_runtime_execution_status = f"blocked_by_runtime_plan:{runtime_plan_status}"
    if runtime_execution_status != expected_runtime_execution_status:
        failures.append("ready_time_direct_snapshot_runtime_execution_status_mismatch")
    if (
        metrics.get("direct_snapshot_runtime_execution_consumes_plan")
        is not True
    ):
        failures.append("ready_time_direct_snapshot_runtime_execution_consumes_plan")
    if (
        metrics.get("direct_snapshot_runtime_execution_live_payload_runtime_enabled")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_live_payload_runtime_enabled"
        )
    if (
        metrics.get(
            "direct_snapshot_runtime_execution_payload_transfer_runtime_enabled"
        )
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_payload_transfer_runtime_enabled"
        )
    if runtime_execution_issued_payload_count != 0:
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_issued_payload_count_mismatch"
        )
    if runtime_execution_payload_bytes != 0:
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_payload_bytes_mismatch"
        )
    if metrics.get("direct_snapshot_runtime_execution_ready_credit") is not False:
        failures.append("ready_time_direct_snapshot_runtime_execution_ready_credit")
    if (
        metrics.get("direct_snapshot_runtime_execution_real_ready_credit_granted")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_real_ready_credit_granted"
        )
    if (
        metrics.get("direct_snapshot_runtime_execution_kernel_arg_pass_allowed")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_kernel_arg_pass_allowed"
        )
    if (
        metrics.get("direct_snapshot_runtime_execution_changes_kernel_launch_args")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_changes_kernel_launch_args"
        )
    if (
        metrics.get("direct_snapshot_runtime_execution_full_fetch_runtime_allowed")
        is not False
    ):
        failures.append(
            "ready_time_direct_snapshot_runtime_execution_full_fetch_runtime_allowed"
        )
    return {
        "ready_time_direct_snapshot_report_present": True,
        "ready_time_direct_snapshot_report": str(report_path),
        "ready_time_direct_snapshot_report_passed": passed,
        "ready_time_direct_snapshot_report_recheck_passed": recheck_passed,
        "ready_time_direct_snapshot_report_recheck_failures": recheck_failures,
        "ready_time_direct_snapshot_allow_full_fetch": allow,
        "ready_time_direct_snapshot_decision_reason": report.get("decision_reason"),
        "ready_time_direct_snapshot_threshold_failures": _string_list(
            report.get("threshold_failures")
        ),
        "ready_time_direct_snapshot_present": direct_present,
        "ready_time_direct_snapshot_runtime_stage": (
            str(runtime_stage) if runtime_stage is not None else None
        ),
        "ready_time_direct_snapshot_payload_bytes": payload_bytes,
        "ready_time_direct_snapshot_full_fetch_runtime_allowed": _optional_bool(
            metrics,
            "direct_snapshot_full_fetch_runtime_allowed",
        ),
        "ready_time_direct_snapshot_changes_kernel_launch_args": _optional_bool(
            metrics,
            "direct_snapshot_changes_kernel_launch_args",
        ),
        "ready_time_direct_snapshot_issue_sources": _string_list(issue_sources),
        "ready_time_direct_snapshot_runtime_participation_present": (
            runtime_participation_present
        ),
        "ready_time_direct_snapshot_runtime_participation_stage": (
            str(runtime_participation_stage)
            if runtime_participation_stage is not None
            else None
        ),
        "ready_time_direct_snapshot_runtime_participation_status": (
            runtime_participation_status_label
        ),
        "ready_time_direct_snapshot_runtime_participation_consumes_manager_snapshot": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_consumes_manager_snapshot",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_payload_bytes": (
            runtime_participation_payload_bytes
        ),
        "ready_time_direct_snapshot_runtime_participation_ready_credit": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_ready_credit",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_real_ready_credit_granted": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_real_ready_credit_granted",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_kernel_arg_pass_allowed": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_kernel_arg_pass_allowed",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_changes_kernel_launch_args": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_changes_kernel_launch_args",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_full_fetch_runtime_allowed": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_full_fetch_runtime_allowed",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_payload_transfer_runtime_enabled": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_participation_payload_transfer_runtime_enabled",
            )
        ),
        "ready_time_direct_snapshot_runtime_participation_issue_sources": (
            _string_list(runtime_participation_issue_sources)
        ),
        "ready_time_direct_snapshot_runtime_plan_present": (
            runtime_participation_present
        ),
        "ready_time_direct_snapshot_runtime_plan_stage": (
            "payload_cache_runtime_plan_lab_gate_dry_run"
        ),
        "ready_time_direct_snapshot_runtime_plan_status": runtime_plan_status,
        "ready_time_direct_snapshot_runtime_plan_consumes_participation": (
            runtime_participation_present
        ),
        "ready_time_direct_snapshot_runtime_plan_live_payload_runtime_enabled": (
            False
        ),
        "ready_time_direct_snapshot_runtime_plan_planned_issue_count": 0,
        "ready_time_direct_snapshot_runtime_plan_payload_bytes": 0,
        "ready_time_direct_snapshot_runtime_plan_ready_credit": False,
        "ready_time_direct_snapshot_runtime_plan_kernel_arg_pass_allowed": False,
        "ready_time_direct_snapshot_runtime_plan_changes_kernel_launch_args": False,
        "ready_time_direct_snapshot_runtime_plan_full_fetch_runtime_allowed": False,
        "ready_time_direct_snapshot_runtime_execution_present": (
            runtime_execution_present
        ),
        "ready_time_direct_snapshot_runtime_execution_stage": (
            str(runtime_execution_stage)
            if runtime_execution_stage is not None
            else None
        ),
        "ready_time_direct_snapshot_runtime_execution_status": (
            runtime_execution_status_label
        ),
        "ready_time_direct_snapshot_runtime_execution_consumes_plan": (
            _optional_bool(metrics, "direct_snapshot_runtime_execution_consumes_plan")
        ),
        "ready_time_direct_snapshot_runtime_execution_plan_status": (
            str(runtime_execution_plan_status)
            if runtime_execution_plan_status is not None
            else None
        ),
        "ready_time_direct_snapshot_runtime_execution_decision": (
            str(runtime_execution_decision)
            if runtime_execution_decision is not None
            else None
        ),
        "ready_time_direct_snapshot_runtime_execution_block_reason": (
            str(runtime_execution_block_reason)
            if runtime_execution_block_reason is not None
            else None
        ),
        "ready_time_direct_snapshot_runtime_execution_execution_mode": (
            str(runtime_execution_execution_mode)
            if runtime_execution_execution_mode is not None
            else None
        ),
        "ready_time_direct_snapshot_runtime_execution_live_payload_runtime_enabled": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_execution_live_payload_runtime_enabled",
            )
        ),
        "ready_time_direct_snapshot_runtime_execution_payload_transfer_runtime_enabled": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_execution_payload_transfer_runtime_enabled",
            )
        ),
        "ready_time_direct_snapshot_runtime_execution_issued_payload_count": (
            runtime_execution_issued_payload_count
        ),
        "ready_time_direct_snapshot_runtime_execution_payload_bytes": (
            runtime_execution_payload_bytes
        ),
        "ready_time_direct_snapshot_runtime_execution_ready_credit": (
            _optional_bool(metrics, "direct_snapshot_runtime_execution_ready_credit")
        ),
        "ready_time_direct_snapshot_runtime_execution_real_ready_credit_granted": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_execution_real_ready_credit_granted",
            )
        ),
        "ready_time_direct_snapshot_runtime_execution_kernel_arg_pass_allowed": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_execution_kernel_arg_pass_allowed",
            )
        ),
        "ready_time_direct_snapshot_runtime_execution_changes_kernel_launch_args": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_execution_changes_kernel_launch_args",
            )
        ),
        "ready_time_direct_snapshot_runtime_execution_full_fetch_runtime_allowed": (
            _optional_bool(
                metrics,
                "direct_snapshot_runtime_execution_full_fetch_runtime_allowed",
            )
        ),
    }


def _ready_time_allow_full_fetch(
    report: dict[str, Any],
    failures: list[str],
) -> bool:
    artifact_kind = report.get("artifact_kind")
    runtime_allow = report.get("full_fetch_runtime_allowed")
    if artifact_kind == "premap_payload_cache_full_fetch_decision_gate":
        if not isinstance(runtime_allow, bool):
            failures.append("ready_time_gate_report_missing_full_fetch_runtime_allowed")
            return False
        _check_full_fetch_decision_gate_noop_safety(report, failures)
        return runtime_allow
    if isinstance(runtime_allow, bool):
        if artifact_kind != "premap_payload_cache_full_fetch_decision_gate":
            failures.append("ready_time_gate_report_artifact_kind_mismatch")
            return False
        return runtime_allow
    return bool(report.get("allow_full_fetch", False))


def _check_full_fetch_decision_gate_noop_safety(
    report: dict[str, Any],
    failures: list[str],
) -> None:
    if report.get("payload_bytes") != 0:
        failures.append("ready_time_gate_report_payload_bytes_nonzero")
    for field in (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if report.get(field) is not False:
            failures.append(f"ready_time_gate_report_{field}_not_false")


def _check_optional_stream_decision_gate(
    section: dict[str, Any],
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    path_value = section.get("stream_decision_gate_report")
    if path_value in (None, ""):
        failures.append("stream_decision_gate_report_missing")
        return {
            "stream_decision_gate_present": False,
            "stream_decision_gate_report": None,
            "stream_decision_gate_passed": None,
            "stream_full_fetch_runtime_allowed": None,
            "stream_required_shifted_issue_accounting_enabled": None,
            "stream_required_shifted_issue_lead_tokens": None,
            "stream_required_shifted_issue_clamped_issue_count": None,
            "stream_required_shifted_issue_duplicate_issue_key_count": None,
            "stream_required_shifted_issue_unique_issue_key_count": None,
            "stream_required_shifted_issue_accounted_packet_count": None,
            "stream_required_shifted_issue_invalid_export_count": None,
            "stream_required_shifted_issue_row_shift_mismatch_count": None,
            "stream_required_shifted_issue_row_clamp_mismatch_count": None,
        }
    path = _resolve(path_value, root=root)
    report = _load_json(path, failures, label="stream_decision_gate_report")
    if report.get("artifact_kind") != "premap_payload_cache_stream_full_fetch_decision_gate":
        failures.append("stream_decision_gate_artifact_kind_mismatch")
    passed = _strict_passed(report, failures, label="stream_decision_gate")
    if not passed:
        failures.append("stream_decision_gate_not_passed")
    if report.get("full_fetch_runtime_allowed") is not False:
        failures.append("stream_decision_gate_allows_full_fetch")
    _check_stream_noop_safety(report, failures, label="stream_decision_gate")
    required_shifted_issue = report.get("required_shifted_issue_accounting")
    required_shifted_issue = (
        required_shifted_issue
        if isinstance(required_shifted_issue, dict)
        else {}
    )
    _check_required_shifted_issue_accounting(
        required_shifted_issue,
        failures,
        label="stream_decision_gate_required_shifted_issue",
    )
    result = {
        "stream_decision_gate_present": True,
        "stream_decision_gate_report": str(path),
        "stream_decision_gate_passed": passed,
        "stream_decision": (
            report.get("decision") if isinstance(report.get("decision"), str) else None
        ),
        "stream_full_fetch_runtime_allowed": _optional_bool(
            report,
            "full_fetch_runtime_allowed",
        ),
        "stream_full_fetch_block_reason": (
            report.get("full_fetch_block_reason")
            if isinstance(report.get("full_fetch_block_reason"), str)
            else None
        ),
        "stream_current_lookahead_us": _optional_float(
            report,
            "current_lookahead_us",
        ),
        "stream_required_lookahead_us": _optional_float(
            report,
            "required_stream_lookahead_us",
        ),
        "stream_lookahead_deficit_us": _optional_float(
            report,
            "lookahead_deficit_us",
        ),
        "stream_first_model_passing_lookahead_us": _optional_float(
            report,
            "first_model_passing_lookahead_us",
        ),
        "stream_metadata_premap_runtime_preferred": _optional_bool(
            report,
            "metadata_premap_runtime_preferred",
        ),
        "stream_descriptor_prep_runtime_preferred": _optional_bool(
            report,
            "descriptor_prep_runtime_preferred",
        ),
        "stream_required_shifted_issue_accounting_enabled": _optional_bool(
            required_shifted_issue,
            "shifted_issue_accounting_enabled",
        ),
        "stream_required_shifted_issue_lead_tokens": _optional_int(
            required_shifted_issue,
            "shifted_issue_lead_tokens",
        ),
        "stream_required_shifted_issue_clamped_issue_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_clamped_issue_count",
        ),
        "stream_required_shifted_issue_duplicate_issue_key_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_duplicate_issue_key_count",
        ),
        "stream_required_shifted_issue_unique_issue_key_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_unique_issue_key_count",
        ),
        "stream_required_shifted_issue_accounted_packet_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_accounted_packet_count",
        ),
        "stream_required_shifted_issue_invalid_export_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_invalid_export_count",
        ),
        "stream_required_shifted_issue_row_shift_mismatch_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_row_shift_mismatch_count",
        ),
        "stream_required_shifted_issue_row_clamp_mismatch_count": _optional_int(
            required_shifted_issue,
            "shifted_issue_row_clamp_mismatch_count",
        ),
    }
    if "current_row_model_passed" in report:
        result["stream_current_runtime_satisfies_model"] = _optional_bool(
            report,
            "current_row_model_passed",
        )
    return result


def _check_required_shifted_issue_accounting(
    payload: dict[str, Any],
    failures: list[str],
    *,
    label: str,
) -> None:
    if not payload:
        failures.append(f"{label}_missing")
        return
    if _optional_bool(payload, "shifted_issue_accounting_enabled") is not True:
        failures.append(f"{label}_enabled_mismatch")
    expected_counts = {
        "shifted_issue_lead_tokens": 32,
        "shifted_issue_clamped_issue_count": 12,
        "shifted_issue_duplicate_issue_key_count": 12,
        "shifted_issue_unique_issue_key_count": 16,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_invalid_export_count": 0,
        "shifted_issue_row_shift_mismatch_count": 0,
        "shifted_issue_row_clamp_mismatch_count": 0,
    }
    for key, expected in expected_counts.items():
        if _optional_int(payload, key) != expected:
            failures.append(f"{label}_{key}_mismatch")


def _check_queue_budget_shifted_issue_accounting(
    payload: dict[str, Any],
    failures: list[str],
    *,
    expected_lead_tokens: int | None,
    label: str,
) -> None:
    if not payload:
        failures.append(f"{label}_missing")
        return
    if _optional_bool(payload, "shifted_issue_accounting_enabled") is not True:
        failures.append(f"{label}_enabled_mismatch")
    lead_tokens = _optional_int(payload, "shifted_issue_lead_tokens")
    if expected_lead_tokens is None:
        if lead_tokens is None or lead_tokens <= 0:
            failures.append(f"{label}_shifted_issue_lead_tokens_invalid")
    elif lead_tokens != expected_lead_tokens:
        failures.append(f"{label}_shifted_issue_lead_tokens_mismatch")
    for key in (
        "shifted_issue_unique_issue_key_count",
        "shifted_issue_accounted_packet_count",
    ):
        value = _optional_int(payload, key)
        if value is None or value <= 0:
            failures.append(f"{label}_{key}_invalid")
    for key in (
        "shifted_issue_clamped_issue_count",
        "shifted_issue_duplicate_issue_key_count",
    ):
        value = _optional_int(payload, key)
        if value is None or value < 0:
            failures.append(f"{label}_{key}_invalid")
    for key in (
        "shifted_issue_invalid_export_count",
        "shifted_issue_row_shift_mismatch_count",
        "shifted_issue_row_clamp_mismatch_count",
    ):
        if _optional_int(payload, key) != 0:
            failures.append(f"{label}_{key}_mismatch")


def _check_optional_stream_feasibility(
    section: dict[str, Any],
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    path_value = section.get("stream_earlier_issue_feasibility_report")
    if path_value in (None, ""):
        failures.append("stream_feasibility_report_missing")
        return {
            "stream_feasibility_present": False,
            "stream_feasibility_report": None,
            "stream_feasibility_passed": None,
        }
    path = _resolve(path_value, root=root)
    report = _load_json(path, failures, label="stream_feasibility_report")
    if report.get("artifact_kind") != "premap_payload_cache_stream_earlier_issue_feasibility":
        failures.append("stream_feasibility_artifact_kind_mismatch")
    passed = _strict_passed(report, failures, label="stream_feasibility")
    if not passed:
        failures.append("stream_feasibility_not_passed")
    if report.get("full_fetch_runtime_allowed") is not False:
        failures.append("stream_feasibility_allows_full_fetch")
    if report.get("current_runtime_satisfies_model") is not False:
        failures.append("stream_feasibility_current_runtime_satisfies_model")
    _check_stream_noop_safety(report, failures, label="stream_feasibility")
    return {
        "stream_feasibility_present": True,
        "stream_feasibility_report": str(path),
        "stream_feasibility_passed": passed,
        "stream_current_runtime_satisfies_model": _optional_bool(
            report,
            "current_runtime_satisfies_model",
        ),
        "stream_feasible_within_configured_token_window": _optional_bool(
            report,
            "feasible_within_configured_token_window",
        ),
        "stream_min_required_lead_tokens": _optional_int(
            report,
            "min_required_lead_tokens",
        ),
        "stream_max_required_lead_tokens": _optional_int(
            report,
            "max_required_lead_tokens",
        ),
        "stream_min_deficit_lead_tokens": _optional_int(
            report,
            "min_deficit_lead_tokens",
        ),
        "stream_max_deficit_lead_tokens": _optional_int(
            report,
            "max_deficit_lead_tokens",
        ),
        "stream_max_candidate_lead_tokens": _optional_int(
            report,
            "max_candidate_lead_tokens",
        ),
    }


def _check_optional_stream_lead_token_sweep(
    section: dict[str, Any],
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    path_value = section.get("stream_earlier_issue_lead_token_sweep_report")
    if path_value in (None, ""):
        failures.append("stream_lead_token_sweep_report_missing")
        return {
            "stream_lead_token_sweep_present": False,
            "stream_lead_token_sweep_report": None,
            "stream_lead_token_sweep_passed": None,
        }
    path = _resolve(path_value, root=root)
    report = _load_json(path, failures, label="stream_lead_token_sweep_report")
    if report.get("artifact_kind") != "premap_payload_cache_stream_earlier_issue_lead_token_sweep":
        failures.append("stream_lead_token_sweep_artifact_kind_mismatch")
    passed = _strict_passed(report, failures, label="stream_lead_token_sweep")
    if not passed:
        failures.append("stream_lead_token_sweep_not_passed")
    if report.get("full_fetch_runtime_allowed") is not False:
        failures.append("stream_lead_token_sweep_allows_full_fetch_runtime")
    if report.get("full_fetch_allowed") is not False:
        failures.append("stream_lead_token_sweep_allows_full_fetch")
    if report.get("event_timing_mode") != "token_index":
        failures.append("stream_lead_token_sweep_event_timing_mode_mismatch")
    if report.get("token_timing_enabled") is not True:
        failures.append("stream_lead_token_sweep_token_timing_not_enabled")
    _check_stream_noop_safety(report, failures, label="stream_lead_token_sweep")
    return {
        "stream_lead_token_sweep_present": True,
        "stream_lead_token_sweep_report": str(path),
        "stream_lead_token_sweep_passed": passed,
        "stream_lead_token_sweep_event_timing_mode": (
            report.get("event_timing_mode")
            if isinstance(report.get("event_timing_mode"), str)
            else None
        ),
        "stream_lead_token_sweep_token_timing_enabled": _optional_bool(
            report,
            "token_timing_enabled",
        ),
        "stream_lead_token_sweep_decode_token_us": _optional_float(
            report,
            "decode_token_us",
        ),
        "stream_first_model_passing_lead_tokens": _optional_int(
            report,
            "first_model_passing_lead_tokens",
        ),
        "stream_lead_token_sweep_first_model_passing_lookahead_us": _optional_float(
            report,
            "first_model_passing_lookahead_us",
        ),
    }


def _check_stream_shifted_issue_replay_contract(
    section: dict[str, Any],
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    path_value = section.get("stream_shifted_issue_replay_contract_report")
    if path_value in (None, ""):
        failures.append("stream_shifted_issue_replay_contract_report_missing")
        return {
            "stream_shifted_issue_replay_contract_present": False,
            "stream_shifted_issue_replay_contract_report": None,
            "stream_shifted_issue_replay_contract_passed": None,
        }
    path = _resolve(path_value, root=root)
    report = _load_json(
        path,
        failures,
        label="stream_shifted_issue_replay_contract_report",
    )
    required_lead = int(
        section.get("stream_shifted_issue_replay_required_lead_tokens", 32)
    )
    min_schedulable = int(
        section.get("stream_shifted_issue_replay_min_schedulable_packets", 1)
    )
    check = check_shifted_issue_replay_contract(
        report,
        required_issue_lead_tokens=required_lead,
        min_schedulable_packet_count=min_schedulable,
        require_bootstrap_clamp=True,
        require_issue_key_coalescing=True,
    )
    if not bool(check.get("passed")):
        failures.append("stream_shifted_issue_replay_contract_not_passed")
        for failure in _string_list(check.get("failures")):
            failures.append(f"stream_shifted_issue_replay_contract_{failure}")
    return {
        "stream_shifted_issue_replay_contract_present": True,
        "stream_shifted_issue_replay_contract_report": str(path),
        "stream_shifted_issue_replay_contract_passed": _optional_bool(
            check,
            "passed",
        ),
        "stream_shifted_issue_replay_contract_required_lead_tokens": required_lead,
        "stream_shifted_issue_replay_contract_min_schedulable_packets": (
            min_schedulable
        ),
        "stream_shifted_issue_replay_issue_lead_tokens": _optional_int(
            check,
            "issue_lead_tokens",
        ),
        "stream_shifted_issue_replay_schedulable_packet_count": _optional_int(
            check,
            "schedulable_packet_count",
        ),
        "stream_shifted_issue_replay_clamped_issue_count": _optional_int(
            check,
            "clamped_issue_count",
        ),
        "stream_shifted_issue_replay_duplicate_issue_key_count": _optional_int(
            check,
            "duplicate_issue_key_count",
        ),
        "stream_shifted_issue_replay_row_shift_mismatch_count": _optional_int(
            check,
            "row_shift_relation_mismatch_count",
        ),
        "stream_shifted_issue_replay_row_clamp_mismatch_count": _optional_int(
            check,
            "row_clamp_relation_mismatch_count",
        ),
        "stream_shifted_issue_replay_payload_bytes": _optional_int(
            check,
            "payload_bytes",
        ),
        "stream_shifted_issue_replay_full_fetch_runtime_allowed": _optional_bool(
            check,
            "full_fetch_runtime_allowed",
        ),
        "stream_shifted_issue_replay_full_fetch_allowed": _optional_bool(
            check,
            "full_fetch_allowed",
        ),
        "stream_shifted_issue_replay_ready_credit": _optional_bool(
            check,
            "ready_credit",
        ),
        "stream_shifted_issue_replay_ready_before_demand_credit": _optional_bool(
            check,
            "ready_before_demand_credit",
        ),
        "stream_shifted_issue_replay_real_ready_credit_granted": _optional_bool(
            check,
            "real_ready_credit_granted",
        ),
        "stream_shifted_issue_replay_payload_transfer_enabled": _optional_bool(
            check,
            "payload_transfer_enabled",
        ),
        "stream_shifted_issue_replay_payload_deref_allowed": _optional_bool(
            check,
            "payload_deref_allowed",
        ),
        "stream_shifted_issue_replay_kernel_arg_pass_allowed": _optional_bool(
            check,
            "kernel_arg_pass_allowed",
        ),
        "stream_shifted_issue_replay_passed_to_kernel": _optional_bool(
            check,
            "passed_to_kernel",
        ),
        "stream_shifted_issue_replay_changes_kernel_launch_args": _optional_bool(
            check,
            "changes_kernel_launch_args",
        ),
        "stream_shifted_issue_replay_source_payload_bytes": _optional_int(
            check,
            "source_payload_bytes",
        ),
        "stream_shifted_issue_replay_source_full_fetch_runtime_allowed": _optional_bool(
            check,
            "source_full_fetch_runtime_allowed",
        ),
        "stream_shifted_issue_replay_source_full_fetch_allowed": _optional_bool(
            check,
            "source_full_fetch_allowed",
        ),
        "stream_shifted_issue_replay_source_ready_credit": _optional_bool(
            check,
            "source_ready_credit",
        ),
        "stream_shifted_issue_replay_source_ready_before_demand_credit": _optional_bool(
            check,
            "source_ready_before_demand_credit",
        ),
        "stream_shifted_issue_replay_source_real_ready_credit_granted": _optional_bool(
            check,
            "source_real_ready_credit_granted",
        ),
        "stream_shifted_issue_replay_source_payload_transfer_enabled": _optional_bool(
            check,
            "source_payload_transfer_enabled",
        ),
        "stream_shifted_issue_replay_source_payload_deref_allowed": _optional_bool(
            check,
            "source_payload_deref_allowed",
        ),
        "stream_shifted_issue_replay_source_kernel_arg_pass_allowed": _optional_bool(
            check,
            "source_kernel_arg_pass_allowed",
        ),
        "stream_shifted_issue_replay_source_passed_to_kernel": _optional_bool(
            check,
            "source_passed_to_kernel",
        ),
        "stream_shifted_issue_replay_source_changes_kernel_launch_args": _optional_bool(
            check,
            "source_changes_kernel_launch_args",
        ),
        "stream_shifted_issue_replay_uses_current_wna16_args": _optional_bool(
            check,
            "uses_current_wna16_args",
        ),
        "stream_shifted_issue_replay_passes_current_wna16_args": _optional_bool(
            check,
            "passes_current_wna16_args",
        ),
        "stream_shifted_issue_replay_current_wna16_arg_compatible": _optional_bool(
            check,
            "current_wna16_arg_compatible",
        ),
        "stream_shifted_issue_replay_requires_wna16_arg_reinterpretation": _optional_bool(
            check,
            "requires_wna16_arg_reinterpretation",
        ),
        "stream_shifted_issue_replay_source_uses_current_wna16_args": _optional_bool(
            check,
            "source_uses_current_wna16_args",
        ),
        "stream_shifted_issue_replay_source_passes_current_wna16_args": _optional_bool(
            check,
            "source_passes_current_wna16_args",
        ),
        "stream_shifted_issue_replay_source_current_wna16_arg_compatible": _optional_bool(
            check,
            "source_current_wna16_arg_compatible",
        ),
        "stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation": _optional_bool(
            check,
            "source_requires_wna16_arg_reinterpretation",
        ),
        "stream_shifted_issue_replay_wna16_benchmark_ready": _optional_bool(
            check,
            "wna16_benchmark_ready",
        ),
        "stream_shifted_issue_replay_source_wna16_benchmark_ready": _optional_bool(
            check,
            "source_wna16_benchmark_ready",
        ),
        "stream_shifted_issue_replay_measures_tpot": _optional_bool(
            check,
            "measures_tpot",
        ),
        "stream_shifted_issue_replay_source_measures_tpot": _optional_bool(
            check,
            "source_measures_tpot",
        ),
        "stream_shifted_issue_replay_measures_vllm_latency": _optional_bool(
            check,
            "measures_vllm_latency",
        ),
        "stream_shifted_issue_replay_source_measures_vllm_latency": _optional_bool(
            check,
            "source_measures_vllm_latency",
        ),
    }


def _check_optional_stream_queue_budget_sweep(
    section: dict[str, Any],
    root: Path,
    failures: list[str],
) -> dict[str, Any]:
    queue_failure_base = len(failures)
    path_value = section.get("stream_queue_budget_report")
    if path_value in (None, ""):
        failures.append("stream_queue_budget_report_missing")
        return {
            "stream_queue_budget_present": False,
            "stream_queue_budget_report": None,
            "stream_queue_budget_passed": None,
        }
    path = _resolve(path_value, root=root)
    report = _load_json(path, failures, label="stream_queue_budget_report")
    if report.get("artifact_kind") != "premap_payload_cache_issue_stream_executor_queue_budget_sweep":
        failures.append("stream_queue_budget_artifact_kind_mismatch")
    passed = _strict_passed(report, failures, label="stream_queue_budget")
    if not passed:
        failures.append("stream_queue_budget_not_passed")
    if report.get("full_fetch_allowed") is not False:
        failures.append("stream_queue_budget_allows_full_fetch")
    _check_stream_queue_budget_noop_safety(
        report,
        failures,
        label="stream_queue_budget",
    )
    if report.get("event_timing_mode") != "token_index":
        failures.append("stream_queue_budget_event_timing_mode_mismatch")
    cell_count = _strict_int(report, "cell_count")
    if cell_count is None or cell_count <= 0:
        failures.append("stream_queue_budget_cell_count_invalid")
    cells = report.get("cells")
    if not isinstance(cells, list) or not cells:
        failures.append("stream_queue_budget_cells_missing")
    elif cell_count is not None and len(cells) != cell_count:
        failures.append("stream_queue_budget_cell_count_mismatch")
    first_cell = report.get("first_model_passing_cell")
    first_cell = first_cell if isinstance(first_cell, dict) else {}
    if not first_cell:
        failures.append("stream_queue_budget_first_model_passing_cell_missing")
    first_capacity = _strict_int(first_cell, "capacity")
    first_lead = _strict_int(first_cell, "issue_lead_tokens")
    first_queue_deadline_us = _optional_float(first_cell, "queue_deadline_us")
    first_lookahead_us = _optional_float(first_cell, "lookahead_us")
    if first_capacity is None or first_capacity <= 0:
        failures.append("stream_queue_budget_first_capacity_invalid")
    if first_lead is None or first_lead <= 0:
        failures.append("stream_queue_budget_first_issue_lead_tokens_invalid")
    if first_queue_deadline_us is None or first_queue_deadline_us <= 0.0:
        failures.append("stream_queue_budget_first_queue_deadline_us_invalid")
    if first_lookahead_us is None or first_lookahead_us <= 0.0:
        failures.append("stream_queue_budget_first_lookahead_us_invalid")
    first_index = _strict_int(first_cell, "cell_index")
    first_cell_from_rows = None
    if not isinstance(cells, list) or first_index is None:
        failures.append("stream_queue_budget_first_cell_index_missing")
    elif first_index < 0 or first_index >= len(cells):
        failures.append("stream_queue_budget_first_cell_index_invalid")
    else:
        first_cell_from_rows = cells[first_index]
        if not isinstance(first_cell_from_rows, dict):
            failures.append("stream_queue_budget_first_cell_index_not_object")
            first_cell_from_rows = None
    if first_cell_from_rows is not None:
        if first_cell_from_rows.get("model_passed") is not True:
            failures.append("stream_queue_budget_first_cell_model_passed_mismatch")
        for field, expected in (
            ("cell_index", first_index),
            ("capacity", first_capacity),
            ("queue_deadline_us", first_queue_deadline_us),
        ):
            if first_cell_from_rows.get(field) != expected:
                failures.append(f"stream_queue_budget_first_cell_{field}_mismatch")
        if first_cell_from_rows.get("first_model_passing_issue_lead_tokens") != first_lead:
            failures.append("stream_queue_budget_first_cell_issue_lead_tokens_mismatch")
        if first_cell_from_rows.get("first_model_passing_lookahead_us") != first_lookahead_us:
            failures.append("stream_queue_budget_first_cell_lookahead_us_mismatch")
    shifted_issue = first_cell.get("shifted_issue_accounting")
    shifted_issue = shifted_issue if isinstance(shifted_issue, dict) else {}
    if first_cell_from_rows is not None:
        row_shifted_issue = first_cell_from_rows.get(
            "first_model_passing_shifted_issue_accounting",
        )
        if row_shifted_issue != shifted_issue:
            failures.append("stream_queue_budget_first_shifted_issue_cell_mismatch")
    _check_queue_budget_shifted_issue_accounting(
        shifted_issue,
        failures,
        expected_lead_tokens=first_lead,
        label="stream_queue_budget_first_shifted_issue",
    )
    envelope_payload: dict[str, Any] = {}
    live_payload_stage_payload: dict[str, Any] = {}
    live_payload_runtime_payload: dict[str, Any] = {}
    manager_artifact_payload: dict[str, Any] = {}
    manager_runtime_skeleton_payload: dict[str, Any] = {}
    manager_runtime_snapshot_payload: dict[str, Any] = {}
    snapshot_backed_live_runtime_preflight_payload: dict[str, Any] = {}
    snapshot_backed_live_runtime_canary_payload: dict[str, Any] = {}
    live_runtime_state_shape_payload: dict[str, Any] = {}
    live_runtime_object_preflight_payload: dict[str, Any] = {}
    live_runtime_object_adapter_preflight_payload: dict[str, Any] = {}
    live_runtime_adapter_materialization_preflight_payload: dict[str, Any] = {}
    live_runtime_adapter_state_object_preflight_payload: dict[str, Any] = {}
    live_runtime_adapter_state_validation_preflight_payload: dict[str, Any] = {}
    live_runtime_adapter_state_validation_artifact_payload: dict[str, Any] = {}
    live_runtime_adapter_instantiation_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_constructor_binding_preflight_payload: dict[str, Any] = {}
    live_runtime_adapter_instance_construction_plan_payload: dict[str, Any] = {}
    live_runtime_adapter_object_shell_evidence_payload: dict[str, Any] = {}
    live_runtime_adapter_operation_rejection_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_accounting_dry_run_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_mixed_outcome_dry_run_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_payloadless_instance_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_payload_transfer_toggle_disabled_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_payload_issue_request_blocked_canary_payload: dict[str, Any] = {}
    live_runtime_adapter_payload_issue_plan_dry_run_payload: dict[str, Any] = {}
    live_runtime_adapter_payload_issue_executor_dry_run_payload: dict[str, Any] = {}
    if len(failures) == queue_failure_base:
        try:
            envelope = build_payload_cache_queue_budget_runtime_envelope(
                cell_count=cell_count,
                event_timing_mode=report.get("event_timing_mode"),
                first_model_passing_capacity=first_capacity,
                first_model_passing_issue_lead_tokens=first_lead,
                first_model_passing_queue_deadline_us=first_queue_deadline_us,
                first_model_passing_lookahead_us=first_lookahead_us,
                shifted_issue_accounting_enabled=shifted_issue.get(
                    "shifted_issue_accounting_enabled",
                ),
                shifted_issue_accounted_packet_count=shifted_issue.get(
                    "shifted_issue_accounted_packet_count",
                ),
                shifted_issue_unique_issue_key_count=shifted_issue.get(
                    "shifted_issue_unique_issue_key_count",
                ),
            )
            envelope_payload = envelope.as_dict()
            live_payload_stage = build_payload_cache_live_payload_stage_preflight(
                envelope,
            )
            live_payload_stage_payload = live_payload_stage.as_dict()
            live_payload_runtime = build_payload_cache_live_payload_runtime_disabled_canary(
                live_payload_stage,
                envelope,
            )
            live_payload_runtime_payload = live_payload_runtime.as_dict()
            manager_artifact = build_payload_cache_manager_implementation_artifact(
                live_payload_runtime,
                envelope,
            )
            manager_artifact_payload = manager_artifact.as_dict()
            manager_runtime_skeleton = build_payload_cache_manager_runtime_skeleton(
                manager_artifact,
            )
            manager_runtime_skeleton_payload = manager_runtime_skeleton.as_dict()
            manager_runtime_snapshot = (
                build_payload_cache_manager_runtime_snapshot_artifact(
                    manager_runtime_skeleton,
                )
            )
            manager_runtime_snapshot_payload = manager_runtime_snapshot.as_dict()
            snapshot_backed_live_runtime_preflight = (
                build_payload_cache_snapshot_backed_live_runtime_preflight(
                    manager_runtime_snapshot,
                )
            )
            snapshot_backed_live_runtime_preflight_payload = (
                snapshot_backed_live_runtime_preflight.as_dict()
            )
            snapshot_backed_live_runtime_canary = (
                build_payload_cache_snapshot_backed_live_runtime_disabled_canary(
                    snapshot_backed_live_runtime_preflight,
                )
            )
            snapshot_backed_live_runtime_canary_payload = (
                snapshot_backed_live_runtime_canary.as_dict()
            )
            live_runtime_state_shape = build_payload_cache_live_runtime_state_shape_check(
                snapshot_backed_live_runtime_canary,
            )
            live_runtime_state_shape_payload = live_runtime_state_shape.as_dict()
            live_runtime_object_preflight = (
                build_payload_cache_live_runtime_object_construction_preflight(
                    live_runtime_state_shape,
                )
            )
            live_runtime_object_preflight_payload = (
                live_runtime_object_preflight.as_dict()
            )
            live_runtime_object_adapter_preflight = (
                build_payload_cache_live_runtime_object_adapter_preflight(
                    live_runtime_object_preflight,
                )
            )
            live_runtime_object_adapter_preflight_payload = (
                live_runtime_object_adapter_preflight.as_dict()
            )
            live_runtime_adapter_materialization_preflight = (
                build_payload_cache_live_runtime_adapter_materialization_preflight(
                    live_runtime_object_adapter_preflight,
                )
            )
            live_runtime_adapter_materialization_preflight_payload = (
                live_runtime_adapter_materialization_preflight.as_dict()
            )
            live_runtime_adapter_state_object_preflight = (
                build_payload_cache_live_runtime_adapter_state_object_preflight(
                    live_runtime_adapter_materialization_preflight,
                )
            )
            live_runtime_adapter_state_object_preflight_payload = (
                live_runtime_adapter_state_object_preflight.as_dict()
            )
            live_runtime_adapter_state_validation_preflight = (
                build_payload_cache_live_runtime_adapter_state_validation_preflight(
                    live_runtime_adapter_state_object_preflight,
                )
            )
            live_runtime_adapter_state_validation_preflight_payload = (
                live_runtime_adapter_state_validation_preflight.as_dict()
            )
            live_runtime_adapter_state_validation_artifact = (
                build_payload_cache_live_runtime_adapter_state_validation_artifact(
                    live_runtime_adapter_state_validation_preflight,
                )
            )
            live_runtime_adapter_state_validation_artifact_payload = (
                live_runtime_adapter_state_validation_artifact.as_dict()
            )
            live_runtime_adapter_instantiation_canary = (
                build_payload_cache_live_runtime_adapter_instantiation_canary(
                    live_runtime_adapter_state_validation_artifact,
                )
            )
            live_runtime_adapter_instantiation_canary_payload = (
                live_runtime_adapter_instantiation_canary.as_dict()
            )
            live_runtime_adapter_constructor_binding_preflight = (
                build_payload_cache_live_runtime_adapter_constructor_binding_preflight(
                    live_runtime_adapter_instantiation_canary,
                )
            )
            live_runtime_adapter_constructor_binding_preflight_payload = (
                live_runtime_adapter_constructor_binding_preflight.as_dict()
            )
            live_runtime_adapter_instance_construction_plan = (
                build_payload_cache_live_runtime_adapter_instance_construction_plan(
                    live_runtime_adapter_constructor_binding_preflight,
                )
            )
            live_runtime_adapter_instance_construction_plan_payload = (
                live_runtime_adapter_instance_construction_plan.as_dict()
            )
            live_runtime_adapter_object_shell_evidence = (
                build_payload_cache_live_runtime_adapter_object_shell_evidence(
                    live_runtime_adapter_instance_construction_plan,
                )
            )
            live_runtime_adapter_object_shell_evidence_payload = (
                live_runtime_adapter_object_shell_evidence.as_dict()
            )
            live_runtime_adapter_operation_rejection_canary = (
                build_payload_cache_live_runtime_adapter_operation_rejection_canary(
                    live_runtime_adapter_object_shell_evidence,
                )
            )
            live_runtime_adapter_operation_rejection_canary_payload = (
                live_runtime_adapter_operation_rejection_canary.as_dict()
            )
            live_runtime_adapter_accounting_dry_run_canary = (
                build_payload_cache_live_runtime_adapter_accounting_dry_run_canary(
                    live_runtime_adapter_operation_rejection_canary,
                )
            )
            live_runtime_adapter_accounting_dry_run_canary_payload = (
                live_runtime_adapter_accounting_dry_run_canary.as_dict()
            )
            live_runtime_adapter_mixed_outcome_dry_run_canary = (
                build_payload_cache_live_runtime_adapter_mixed_outcome_dry_run_canary(
                    live_runtime_adapter_accounting_dry_run_canary,
                )
            )
            live_runtime_adapter_mixed_outcome_dry_run_canary_payload = (
                live_runtime_adapter_mixed_outcome_dry_run_canary.as_dict()
            )
            live_runtime_adapter_payloadless_instance_canary = (
                build_payload_cache_live_runtime_adapter_payloadless_instance_canary(
                    live_runtime_adapter_mixed_outcome_dry_run_canary,
                )
            )
            live_runtime_adapter_payloadless_instance_canary_payload = (
                live_runtime_adapter_payloadless_instance_canary.as_dict()
            )
            live_runtime_adapter_payload_transfer_toggle_disabled_canary = (
                build_payload_cache_live_runtime_adapter_payload_transfer_toggle_disabled_canary(
                    live_runtime_adapter_payloadless_instance_canary,
                )
            )
            live_runtime_adapter_payload_transfer_toggle_disabled_canary_payload = (
                live_runtime_adapter_payload_transfer_toggle_disabled_canary.as_dict()
            )
            live_runtime_adapter_payload_issue_request_blocked_canary = (
                build_payload_cache_live_runtime_adapter_payload_issue_request_blocked_canary(
                    live_runtime_adapter_payload_transfer_toggle_disabled_canary,
                    request_source="queue_budget_first_model_passing_cell",
                    source_issue_packet_count=int(
                        _optional_int(
                            shifted_issue,
                            "shifted_issue_accounted_packet_count",
                        )
                        or 0
                    ),
                    source_issue_unique_key_count=int(
                        _optional_int(
                            shifted_issue,
                            "shifted_issue_unique_issue_key_count",
                        )
                        or 0
                    ),
                    source_queue_budget_capacity=int(first_capacity or 0),
                    source_issue_lead_tokens=int(first_lead or 0),
                    source_queue_deadline_us=float(first_queue_deadline_us or 0.0),
                )
            )
            live_runtime_adapter_payload_issue_request_blocked_canary_payload = (
                live_runtime_adapter_payload_issue_request_blocked_canary.as_dict()
            )
            live_runtime_adapter_payload_issue_plan_dry_run = (
                build_payload_cache_live_runtime_adapter_payload_issue_plan_dry_run(
                    live_runtime_adapter_payload_issue_request_blocked_canary,
                )
            )
            live_runtime_adapter_payload_issue_plan_dry_run_payload = (
                live_runtime_adapter_payload_issue_plan_dry_run.as_dict()
            )
            live_runtime_adapter_payload_issue_executor_dry_run = (
                build_payload_cache_live_runtime_adapter_payload_issue_executor_dry_run(
                    live_runtime_adapter_payload_issue_plan_dry_run,
                )
            )
            live_runtime_adapter_payload_issue_executor_dry_run_payload = (
                live_runtime_adapter_payload_issue_executor_dry_run.as_dict()
            )
        except (TypeError, ValueError) as exc:
            if live_runtime_adapter_payload_issue_plan_dry_run_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "payload_issue_executor_dry_run_invalid"
                )
            elif live_runtime_adapter_payload_issue_request_blocked_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "payload_issue_plan_dry_run_invalid"
                )
            elif live_runtime_adapter_payload_transfer_toggle_disabled_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "payload_issue_request_blocked_canary_invalid"
                )
            elif live_runtime_adapter_payloadless_instance_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "payload_transfer_toggle_disabled_canary_invalid"
                )
            elif live_runtime_adapter_mixed_outcome_dry_run_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "payloadless_instance_canary_invalid"
                )
            elif live_runtime_adapter_accounting_dry_run_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "mixed_outcome_dry_run_canary_invalid"
                )
            elif live_runtime_adapter_operation_rejection_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "accounting_dry_run_canary_invalid"
                )
            elif live_runtime_adapter_object_shell_evidence_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "operation_rejection_canary_invalid"
                )
            elif live_runtime_adapter_instance_construction_plan_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "object_shell_evidence_invalid"
                )
            elif live_runtime_adapter_constructor_binding_preflight_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "instance_construction_plan_invalid"
                )
            elif live_runtime_adapter_instantiation_canary_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "constructor_binding_preflight_invalid"
                )
            elif live_runtime_adapter_state_validation_artifact_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "instantiation_canary_invalid"
                )
            elif live_runtime_adapter_state_validation_preflight_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "state_validation_artifact_invalid"
                )
            elif live_runtime_adapter_state_object_preflight_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "state_validation_preflight_invalid"
                )
            elif live_runtime_adapter_materialization_preflight_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "state_object_preflight_invalid"
                )
            elif live_runtime_object_adapter_preflight_payload:
                label = (
                    "stream_queue_budget_live_runtime_adapter_"
                    "materialization_preflight_invalid"
                )
            elif live_runtime_object_preflight_payload:
                label = "stream_queue_budget_live_runtime_object_adapter_preflight_invalid"
            elif live_runtime_state_shape_payload:
                label = "stream_queue_budget_live_runtime_object_preflight_invalid"
            elif snapshot_backed_live_runtime_canary_payload:
                label = "stream_queue_budget_live_runtime_state_shape_invalid"
            elif snapshot_backed_live_runtime_preflight_payload:
                label = "stream_queue_budget_snapshot_backed_live_runtime_canary_invalid"
            elif manager_runtime_snapshot_payload:
                label = (
                    "stream_queue_budget_snapshot_backed_live_runtime_preflight_invalid"
                )
            elif manager_runtime_skeleton_payload:
                label = "stream_queue_budget_manager_runtime_snapshot_invalid"
            elif manager_artifact_payload:
                label = "stream_queue_budget_manager_runtime_skeleton_invalid"
            elif live_payload_runtime_payload:
                label = "stream_queue_budget_manager_artifact_invalid"
            elif live_payload_stage_payload:
                label = "stream_queue_budget_live_payload_runtime_invalid"
            elif envelope_payload:
                label = "stream_queue_budget_live_payload_stage_invalid"
            else:
                label = "stream_queue_budget_runtime_envelope_invalid"
            failures.append(
                f"{label}:{type(exc).__name__}:{exc}",
            )
    else:
        failures.append("stream_queue_budget_runtime_envelope_skipped_due_to_failures")
    return {
        "stream_queue_budget_present": True,
        "stream_queue_budget_report": str(path),
        "stream_queue_budget_passed": passed,
        "stream_queue_budget_cell_count": cell_count,
        "stream_queue_budget_event_timing_mode": (
            report.get("event_timing_mode")
            if isinstance(report.get("event_timing_mode"), str)
            else None
        ),
        "stream_queue_budget_first_model_passing_capacity": first_capacity,
        "stream_queue_budget_first_model_passing_issue_lead_tokens": first_lead,
        "stream_queue_budget_first_model_passing_queue_deadline_us": (
            first_queue_deadline_us
        ),
        "stream_queue_budget_first_model_passing_lookahead_us": first_lookahead_us,
        "stream_queue_budget_first_shifted_issue_accounting_enabled": (
            _optional_bool(shifted_issue, "shifted_issue_accounting_enabled")
        ),
        "stream_queue_budget_first_shifted_issue_accounted_packet_count": (
            _optional_int(shifted_issue, "shifted_issue_accounted_packet_count")
        ),
        "stream_queue_budget_first_shifted_issue_unique_issue_key_count": (
            _optional_int(shifted_issue, "shifted_issue_unique_issue_key_count")
        ),
        "stream_queue_budget_runtime_envelope_present": envelope_payload.get(
            "present",
        ),
        "stream_queue_budget_runtime_envelope_stage": envelope_payload.get("stage"),
        "stream_queue_budget_runtime_envelope_status": envelope_payload.get("status"),
        "stream_queue_budget_runtime_envelope_execution_mode": envelope_payload.get(
            "execution_mode",
        ),
        "stream_queue_budget_runtime_envelope_consumes_queue_budget_sweep": (
            envelope_payload.get("consumes_queue_budget_sweep")
        ),
        "stream_queue_budget_runtime_envelope_payload_bytes": envelope_payload.get(
            "payload_bytes",
        ),
        "stream_queue_budget_runtime_envelope_issued_payload_count": (
            envelope_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_runtime_envelope_live_payload_runtime_enabled": (
            envelope_payload.get("live_payload_runtime_enabled")
        ),
        "stream_queue_budget_runtime_envelope_payload_transfer_enabled": (
            envelope_payload.get("payload_transfer_enabled")
        ),
        "stream_queue_budget_runtime_envelope_payload_transfer_runtime_enabled": (
            envelope_payload.get("payload_transfer_runtime_enabled")
        ),
        "stream_queue_budget_runtime_envelope_payload_deref_allowed": (
            envelope_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_runtime_envelope_payload_deref_runtime_allowed": (
            envelope_payload.get("payload_deref_runtime_allowed")
        ),
        "stream_queue_budget_runtime_envelope_full_fetch_allowed": (
            envelope_payload.get("full_fetch_allowed")
        ),
        "stream_queue_budget_runtime_envelope_full_fetch_runtime_allowed": (
            envelope_payload.get("full_fetch_runtime_allowed")
        ),
        "stream_queue_budget_runtime_envelope_ready_credit": envelope_payload.get(
            "ready_credit",
        ),
        "stream_queue_budget_runtime_envelope_ready_before_demand_credit": (
            envelope_payload.get("ready_before_demand_credit")
        ),
        "stream_queue_budget_runtime_envelope_real_ready_credit_granted": (
            envelope_payload.get("real_ready_credit_granted")
        ),
        "stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed": (
            envelope_payload.get("kernel_arg_pass_allowed")
        ),
        "stream_queue_budget_runtime_envelope_passed_to_kernel": envelope_payload.get(
            "passed_to_kernel",
        ),
        "stream_queue_budget_runtime_envelope_changes_kernel_launch_args": (
            envelope_payload.get("changes_kernel_launch_args")
        ),
        "stream_queue_budget_runtime_envelope_uses_current_wna16_args": (
            envelope_payload.get("uses_current_wna16_args")
        ),
        "stream_queue_budget_runtime_envelope_passes_current_wna16_args": (
            envelope_payload.get("passes_current_wna16_args")
        ),
        "stream_queue_budget_runtime_envelope_measures_tpot": envelope_payload.get(
            "measures_tpot",
        ),
        "stream_queue_budget_runtime_envelope_measures_vllm_latency": (
            envelope_payload.get("measures_vllm_latency")
        ),
        "stream_queue_budget_runtime_envelope_live_runtime_instantiated": (
            envelope_payload.get("live_runtime_instantiated")
        ),
        "stream_queue_budget_live_payload_stage_present": (
            live_payload_stage_payload.get("present")
        ),
        "stream_queue_budget_live_payload_stage_stage": live_payload_stage_payload.get(
            "stage",
        ),
        "stream_queue_budget_live_payload_stage_status": live_payload_stage_payload.get(
            "status",
        ),
        "stream_queue_budget_live_payload_stage_consumes_queue_budget_runtime_envelope": (
            live_payload_stage_payload.get("consumes_queue_budget_runtime_envelope")
        ),
        "stream_queue_budget_live_payload_stage_queue_budget_envelope_status": (
            live_payload_stage_payload.get("queue_budget_envelope_status")
        ),
        "stream_queue_budget_live_payload_stage_queue_budget_capacity_entries": (
            live_payload_stage_payload.get("queue_budget_capacity_entries")
        ),
        "stream_queue_budget_live_payload_stage_queue_budget_issue_lead_tokens": (
            live_payload_stage_payload.get("queue_budget_issue_lead_tokens")
        ),
        "stream_queue_budget_live_payload_stage_queue_budget_queue_deadline_us": (
            live_payload_stage_payload.get("queue_budget_queue_deadline_us")
        ),
        "stream_queue_budget_live_payload_stage_queue_budget_lookahead_us": (
            live_payload_stage_payload.get("queue_budget_lookahead_us")
        ),
        "stream_queue_budget_live_payload_stage_shifted_issue_accounting_enabled": (
            live_payload_stage_payload.get("shifted_issue_accounting_enabled")
        ),
        "stream_queue_budget_live_payload_stage_shifted_issue_accounted_packet_count": (
            live_payload_stage_payload.get("shifted_issue_accounted_packet_count")
        ),
        "stream_queue_budget_live_payload_stage_shifted_issue_unique_issue_key_count": (
            live_payload_stage_payload.get("shifted_issue_unique_issue_key_count")
        ),
        "stream_queue_budget_live_payload_stage_decision": live_payload_stage_payload.get(
            "decision",
        ),
        "stream_queue_budget_live_payload_stage_block_reason": (
            live_payload_stage_payload.get("block_reason")
        ),
        "stream_queue_budget_live_payload_stage_execution_mode": (
            live_payload_stage_payload.get("execution_mode")
        ),
        "stream_queue_budget_live_payload_stage_live_payload_runtime_enabled": (
            live_payload_stage_payload.get("live_payload_runtime_enabled")
        ),
        "stream_queue_budget_live_payload_stage_payload_transfer_runtime_enabled": (
            live_payload_stage_payload.get("payload_transfer_runtime_enabled")
        ),
        "stream_queue_budget_live_payload_stage_payload_deref_allowed": (
            live_payload_stage_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed": (
            live_payload_stage_payload.get("payload_deref_runtime_allowed")
        ),
        "stream_queue_budget_live_payload_stage_issued_payload_count": (
            live_payload_stage_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_live_payload_stage_payload_bytes": (
            live_payload_stage_payload.get("payload_bytes")
        ),
        "stream_queue_budget_live_payload_stage_ready_credit": (
            live_payload_stage_payload.get("ready_credit")
        ),
        "stream_queue_budget_live_payload_stage_ready_before_demand_credit": (
            live_payload_stage_payload.get("ready_before_demand_credit")
        ),
        "stream_queue_budget_live_payload_stage_real_ready_credit_granted": (
            live_payload_stage_payload.get("real_ready_credit_granted")
        ),
        "stream_queue_budget_live_payload_stage_kernel_arg_pass_allowed": (
            live_payload_stage_payload.get("kernel_arg_pass_allowed")
        ),
        "stream_queue_budget_live_payload_stage_passed_to_kernel": (
            live_payload_stage_payload.get("passed_to_kernel")
        ),
        "stream_queue_budget_live_payload_stage_changes_kernel_launch_args": (
            live_payload_stage_payload.get("changes_kernel_launch_args")
        ),
        "stream_queue_budget_live_payload_stage_full_fetch_runtime_allowed": (
            live_payload_stage_payload.get("full_fetch_runtime_allowed")
        ),
        "stream_queue_budget_live_payload_stage_uses_current_wna16_args": (
            live_payload_stage_payload.get("uses_current_wna16_args")
        ),
        "stream_queue_budget_live_payload_stage_passes_current_wna16_args": (
            live_payload_stage_payload.get("passes_current_wna16_args")
        ),
        "stream_queue_budget_live_payload_stage_measures_tpot": (
            live_payload_stage_payload.get("measures_tpot")
        ),
        "stream_queue_budget_live_payload_stage_measures_vllm_latency": (
            live_payload_stage_payload.get("measures_vllm_latency")
        ),
        "stream_queue_budget_live_payload_runtime_present": (
            live_payload_runtime_payload.get("present")
        ),
        "stream_queue_budget_live_payload_runtime_stage": (
            live_payload_runtime_payload.get("stage")
        ),
        "stream_queue_budget_live_payload_runtime_status": (
            live_payload_runtime_payload.get("status")
        ),
        "stream_queue_budget_live_payload_runtime_consumes_live_payload_stage_preflight": (
            live_payload_runtime_payload.get("consumes_live_payload_stage_preflight")
        ),
        "stream_queue_budget_live_payload_runtime_live_payload_stage_status": (
            live_payload_runtime_payload.get("live_payload_stage_status")
        ),
        "stream_queue_budget_live_payload_runtime_queue_budget_capacity_entries": (
            live_payload_runtime_payload.get("queue_budget_capacity_entries")
        ),
        "stream_queue_budget_live_payload_runtime_queue_budget_issue_lead_tokens": (
            live_payload_runtime_payload.get("queue_budget_issue_lead_tokens")
        ),
        "stream_queue_budget_live_payload_runtime_queue_budget_queue_deadline_us": (
            live_payload_runtime_payload.get("queue_budget_queue_deadline_us")
        ),
        "stream_queue_budget_live_payload_runtime_queue_budget_lookahead_us": (
            live_payload_runtime_payload.get("queue_budget_lookahead_us")
        ),
        "stream_queue_budget_live_payload_runtime_shifted_issue_accounting_enabled": (
            live_payload_runtime_payload.get("shifted_issue_accounting_enabled")
        ),
        "stream_queue_budget_live_payload_runtime_shifted_issue_accounted_packet_count": (
            live_payload_runtime_payload.get("shifted_issue_accounted_packet_count")
        ),
        "stream_queue_budget_live_payload_runtime_shifted_issue_unique_issue_key_count": (
            live_payload_runtime_payload.get("shifted_issue_unique_issue_key_count")
        ),
        "stream_queue_budget_live_payload_runtime_decision": (
            live_payload_runtime_payload.get("decision")
        ),
        "stream_queue_budget_live_payload_runtime_block_reason": (
            live_payload_runtime_payload.get("block_reason")
        ),
        "stream_queue_budget_live_payload_runtime_execution_mode": (
            live_payload_runtime_payload.get("execution_mode")
        ),
        "stream_queue_budget_live_payload_runtime_live_payload_runtime_enabled": (
            live_payload_runtime_payload.get("live_payload_runtime_enabled")
        ),
        "stream_queue_budget_live_payload_runtime_payload_transfer_runtime_enabled": (
            live_payload_runtime_payload.get("payload_transfer_runtime_enabled")
        ),
        "stream_queue_budget_live_payload_runtime_payload_deref_allowed": (
            live_payload_runtime_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_live_payload_runtime_payload_deref_runtime_allowed": (
            live_payload_runtime_payload.get("payload_deref_runtime_allowed")
        ),
        "stream_queue_budget_live_payload_runtime_issued_payload_count": (
            live_payload_runtime_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_live_payload_runtime_payload_bytes": (
            live_payload_runtime_payload.get("payload_bytes")
        ),
        "stream_queue_budget_live_payload_runtime_ready_credit": (
            live_payload_runtime_payload.get("ready_credit")
        ),
        "stream_queue_budget_live_payload_runtime_ready_before_demand_credit": (
            live_payload_runtime_payload.get("ready_before_demand_credit")
        ),
        "stream_queue_budget_live_payload_runtime_real_ready_credit_granted": (
            live_payload_runtime_payload.get("real_ready_credit_granted")
        ),
        "stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed": (
            live_payload_runtime_payload.get("kernel_arg_pass_allowed")
        ),
        "stream_queue_budget_live_payload_runtime_passed_to_kernel": (
            live_payload_runtime_payload.get("passed_to_kernel")
        ),
        "stream_queue_budget_live_payload_runtime_changes_kernel_launch_args": (
            live_payload_runtime_payload.get("changes_kernel_launch_args")
        ),
        "stream_queue_budget_live_payload_runtime_full_fetch_runtime_allowed": (
            live_payload_runtime_payload.get("full_fetch_runtime_allowed")
        ),
        "stream_queue_budget_live_payload_runtime_uses_current_wna16_args": (
            live_payload_runtime_payload.get("uses_current_wna16_args")
        ),
        "stream_queue_budget_live_payload_runtime_passes_current_wna16_args": (
            live_payload_runtime_payload.get("passes_current_wna16_args")
        ),
        "stream_queue_budget_live_payload_runtime_measures_tpot": (
            live_payload_runtime_payload.get("measures_tpot")
        ),
        "stream_queue_budget_live_payload_runtime_measures_vllm_latency": (
            live_payload_runtime_payload.get("measures_vllm_latency")
        ),
        "stream_queue_budget_manager_artifact_present": (
            manager_artifact_payload.get("present")
        ),
        "stream_queue_budget_manager_artifact_stage": (
            manager_artifact_payload.get("stage")
        ),
        "stream_queue_budget_manager_artifact_status": (
            manager_artifact_payload.get("status")
        ),
        "stream_queue_budget_manager_artifact_consumes_live_payload_runtime_canary": (
            manager_artifact_payload.get("consumes_live_payload_runtime_canary")
        ),
        "stream_queue_budget_manager_artifact_live_payload_runtime_status": (
            manager_artifact_payload.get("live_payload_runtime_status")
        ),
        "stream_queue_budget_manager_artifact_manager_backend": (
            manager_artifact_payload.get("manager_backend")
        ),
        "stream_queue_budget_manager_artifact_manager_contract": (
            manager_artifact_payload.get("manager_contract")
        ),
        "stream_queue_budget_manager_artifact_capacity_entries": (
            manager_artifact_payload.get("capacity_entries")
        ),
        "stream_queue_budget_manager_artifact_issue_lead_tokens": (
            manager_artifact_payload.get("issue_lead_tokens")
        ),
        "stream_queue_budget_manager_artifact_queue_deadline_us": (
            manager_artifact_payload.get("queue_deadline_us")
        ),
        "stream_queue_budget_manager_artifact_lookahead_us": (
            manager_artifact_payload.get("lookahead_us")
        ),
        "stream_queue_budget_manager_artifact_shifted_issue_accounting_enabled": (
            manager_artifact_payload.get("shifted_issue_accounting_enabled")
        ),
        "stream_queue_budget_manager_artifact_shifted_issue_accounted_packet_count": (
            manager_artifact_payload.get("shifted_issue_accounted_packet_count")
        ),
        "stream_queue_budget_manager_artifact_shifted_issue_unique_issue_key_count": (
            manager_artifact_payload.get("shifted_issue_unique_issue_key_count")
        ),
        "stream_queue_budget_manager_artifact_decision": (
            manager_artifact_payload.get("decision")
        ),
        "stream_queue_budget_manager_artifact_block_reason": (
            manager_artifact_payload.get("block_reason")
        ),
        "stream_queue_budget_manager_artifact_execution_mode": (
            manager_artifact_payload.get("execution_mode")
        ),
        "stream_queue_budget_manager_artifact_live_payload_runtime_enabled": (
            manager_artifact_payload.get("live_payload_runtime_enabled")
        ),
        "stream_queue_budget_manager_artifact_payload_transfer_runtime_enabled": (
            manager_artifact_payload.get("payload_transfer_runtime_enabled")
        ),
        "stream_queue_budget_manager_artifact_payload_deref_allowed": (
            manager_artifact_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_manager_artifact_payload_deref_runtime_allowed": (
            manager_artifact_payload.get("payload_deref_runtime_allowed")
        ),
        "stream_queue_budget_manager_artifact_issued_payload_count": (
            manager_artifact_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_manager_artifact_payload_bytes": (
            manager_artifact_payload.get("payload_bytes")
        ),
        "stream_queue_budget_manager_artifact_ready_credit": (
            manager_artifact_payload.get("ready_credit")
        ),
        "stream_queue_budget_manager_artifact_ready_before_demand_credit": (
            manager_artifact_payload.get("ready_before_demand_credit")
        ),
        "stream_queue_budget_manager_artifact_real_ready_credit_granted": (
            manager_artifact_payload.get("real_ready_credit_granted")
        ),
        "stream_queue_budget_manager_artifact_kernel_arg_pass_allowed": (
            manager_artifact_payload.get("kernel_arg_pass_allowed")
        ),
        "stream_queue_budget_manager_artifact_passed_to_kernel": (
            manager_artifact_payload.get("passed_to_kernel")
        ),
        "stream_queue_budget_manager_artifact_changes_kernel_launch_args": (
            manager_artifact_payload.get("changes_kernel_launch_args")
        ),
        "stream_queue_budget_manager_artifact_full_fetch_runtime_allowed": (
            manager_artifact_payload.get("full_fetch_runtime_allowed")
        ),
        "stream_queue_budget_manager_artifact_uses_current_wna16_args": (
            manager_artifact_payload.get("uses_current_wna16_args")
        ),
        "stream_queue_budget_manager_artifact_passes_current_wna16_args": (
            manager_artifact_payload.get("passes_current_wna16_args")
        ),
        "stream_queue_budget_manager_artifact_measures_tpot": (
            manager_artifact_payload.get("measures_tpot")
        ),
        "stream_queue_budget_manager_artifact_measures_vllm_latency": (
            manager_artifact_payload.get("measures_vllm_latency")
        ),
        "stream_queue_budget_manager_runtime_skeleton_present": (
            manager_runtime_skeleton_payload.get("present")
        ),
        "stream_queue_budget_manager_runtime_skeleton_stage": (
            manager_runtime_skeleton_payload.get("stage")
        ),
        "stream_queue_budget_manager_runtime_skeleton_status": (
            manager_runtime_skeleton_payload.get("status")
        ),
        "stream_queue_budget_manager_runtime_skeleton_consumes_manager_implementation_artifact": (
            manager_runtime_skeleton_payload.get(
                "consumes_manager_implementation_artifact",
            )
        ),
        "stream_queue_budget_manager_runtime_skeleton_manager_artifact_status": (
            manager_runtime_skeleton_payload.get("manager_artifact_status")
        ),
        "stream_queue_budget_manager_runtime_skeleton_manager_backend": (
            manager_runtime_skeleton_payload.get("manager_backend")
        ),
        "stream_queue_budget_manager_runtime_skeleton_manager_contract": (
            manager_runtime_skeleton_payload.get("manager_contract")
        ),
        "stream_queue_budget_manager_runtime_skeleton_manager_runtime_contract": (
            manager_runtime_skeleton_payload.get("manager_runtime_contract")
        ),
        "stream_queue_budget_manager_runtime_skeleton_manager_runtime_mode": (
            manager_runtime_skeleton_payload.get("manager_runtime_mode")
        ),
        "stream_queue_budget_manager_runtime_skeleton_capacity_entries": (
            manager_runtime_skeleton_payload.get("capacity_entries")
        ),
        "stream_queue_budget_manager_runtime_skeleton_issue_lead_tokens": (
            manager_runtime_skeleton_payload.get("issue_lead_tokens")
        ),
        "stream_queue_budget_manager_runtime_skeleton_queue_deadline_us": (
            manager_runtime_skeleton_payload.get("queue_deadline_us")
        ),
        "stream_queue_budget_manager_runtime_skeleton_lookahead_us": (
            manager_runtime_skeleton_payload.get("lookahead_us")
        ),
        "stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounting_enabled": (
            manager_runtime_skeleton_payload.get("shifted_issue_accounting_enabled")
        ),
        "stream_queue_budget_manager_runtime_skeleton_shifted_issue_accounted_packet_count": (
            manager_runtime_skeleton_payload.get(
                "shifted_issue_accounted_packet_count",
            )
        ),
        "stream_queue_budget_manager_runtime_skeleton_shifted_issue_unique_issue_key_count": (
            manager_runtime_skeleton_payload.get(
                "shifted_issue_unique_issue_key_count",
            )
        ),
        "stream_queue_budget_manager_runtime_skeleton_runtime_instantiated": (
            manager_runtime_skeleton_payload.get("runtime_instantiated")
        ),
        "stream_queue_budget_manager_runtime_skeleton_decision": (
            manager_runtime_skeleton_payload.get("decision")
        ),
        "stream_queue_budget_manager_runtime_skeleton_block_reason": (
            manager_runtime_skeleton_payload.get("block_reason")
        ),
        "stream_queue_budget_manager_runtime_skeleton_execution_mode": (
            manager_runtime_skeleton_payload.get("execution_mode")
        ),
        "stream_queue_budget_manager_runtime_skeleton_live_payload_runtime_enabled": (
            manager_runtime_skeleton_payload.get("live_payload_runtime_enabled")
        ),
        "stream_queue_budget_manager_runtime_skeleton_payload_transfer_runtime_enabled": (
            manager_runtime_skeleton_payload.get("payload_transfer_runtime_enabled")
        ),
        "stream_queue_budget_manager_runtime_skeleton_payload_deref_allowed": (
            manager_runtime_skeleton_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_manager_runtime_skeleton_payload_deref_runtime_allowed": (
            manager_runtime_skeleton_payload.get("payload_deref_runtime_allowed")
        ),
        "stream_queue_budget_manager_runtime_skeleton_issued_payload_count": (
            manager_runtime_skeleton_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_manager_runtime_skeleton_payload_bytes": (
            manager_runtime_skeleton_payload.get("payload_bytes")
        ),
        "stream_queue_budget_manager_runtime_skeleton_ready_credit": (
            manager_runtime_skeleton_payload.get("ready_credit")
        ),
        "stream_queue_budget_manager_runtime_skeleton_ready_before_demand_credit": (
            manager_runtime_skeleton_payload.get("ready_before_demand_credit")
        ),
        "stream_queue_budget_manager_runtime_skeleton_real_ready_credit_granted": (
            manager_runtime_skeleton_payload.get("real_ready_credit_granted")
        ),
        "stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed": (
            manager_runtime_skeleton_payload.get("kernel_arg_pass_allowed")
        ),
        "stream_queue_budget_manager_runtime_skeleton_passed_to_kernel": (
            manager_runtime_skeleton_payload.get("passed_to_kernel")
        ),
        "stream_queue_budget_manager_runtime_skeleton_changes_kernel_launch_args": (
            manager_runtime_skeleton_payload.get("changes_kernel_launch_args")
        ),
        "stream_queue_budget_manager_runtime_skeleton_full_fetch_runtime_allowed": (
            manager_runtime_skeleton_payload.get("full_fetch_runtime_allowed")
        ),
        "stream_queue_budget_manager_runtime_skeleton_uses_current_wna16_args": (
            manager_runtime_skeleton_payload.get("uses_current_wna16_args")
        ),
        "stream_queue_budget_manager_runtime_skeleton_passes_current_wna16_args": (
            manager_runtime_skeleton_payload.get("passes_current_wna16_args")
        ),
        "stream_queue_budget_manager_runtime_skeleton_measures_tpot": (
            manager_runtime_skeleton_payload.get("measures_tpot")
        ),
        "stream_queue_budget_manager_runtime_skeleton_measures_vllm_latency": (
            manager_runtime_skeleton_payload.get("measures_vllm_latency")
        ),
        "stream_queue_budget_manager_runtime_snapshot_present": (
            manager_runtime_snapshot_payload.get("present")
        ),
        "stream_queue_budget_manager_runtime_snapshot_stage": (
            manager_runtime_snapshot_payload.get("stage")
        ),
        "stream_queue_budget_manager_runtime_snapshot_status": (
            manager_runtime_snapshot_payload.get("status")
        ),
        "stream_queue_budget_manager_runtime_snapshot_consumes_runtime_skeleton": (
            manager_runtime_snapshot_payload.get("consumes_runtime_skeleton")
        ),
        "stream_queue_budget_manager_runtime_snapshot_runtime_skeleton_status": (
            manager_runtime_snapshot_payload.get("runtime_skeleton_status")
        ),
        "stream_queue_budget_manager_runtime_snapshot_manager_backend": (
            manager_runtime_snapshot_payload.get("manager_backend")
        ),
        "stream_queue_budget_manager_runtime_snapshot_manager_runtime_contract": (
            manager_runtime_snapshot_payload.get("manager_runtime_contract")
        ),
        "stream_queue_budget_manager_runtime_snapshot_manager_runtime_mode": (
            manager_runtime_snapshot_payload.get("manager_runtime_mode")
        ),
        "stream_queue_budget_manager_runtime_snapshot_snapshot_source": (
            manager_runtime_snapshot_payload.get("snapshot_source")
        ),
        "stream_queue_budget_manager_runtime_snapshot_accounting_snapshot_instantiated": (
            manager_runtime_snapshot_payload.get("accounting_snapshot_instantiated")
        ),
        "stream_queue_budget_manager_runtime_snapshot_live_runtime_instantiated": (
            manager_runtime_snapshot_payload.get("live_runtime_instantiated")
        ),
        "stream_queue_budget_manager_runtime_snapshot_capacity_entries": (
            manager_runtime_snapshot_payload.get("capacity_entries")
        ),
        "stream_queue_budget_manager_runtime_snapshot_issue_lead_tokens": (
            manager_runtime_snapshot_payload.get("issue_lead_tokens")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_deadline_us": (
            manager_runtime_snapshot_payload.get("queue_deadline_us")
        ),
        "stream_queue_budget_manager_runtime_snapshot_lookahead_us": (
            manager_runtime_snapshot_payload.get("lookahead_us")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_batch_size": (
            manager_runtime_snapshot_payload.get("queue_batch_size")
        ),
        "stream_queue_budget_manager_runtime_snapshot_resident_count": (
            manager_runtime_snapshot_payload.get("resident_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_issued_fetch_count": (
            manager_runtime_snapshot_payload.get("issued_fetch_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_used_fetch_count": (
            manager_runtime_snapshot_payload.get("used_fetch_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_unused_fetch_count": (
            manager_runtime_snapshot_payload.get("unused_fetch_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_demand_count": (
            manager_runtime_snapshot_payload.get("demand_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_demand_hit_count": (
            manager_runtime_snapshot_payload.get("demand_hit_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_demand_miss_count": (
            manager_runtime_snapshot_payload.get("demand_miss_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_evicted_before_use_count": (
            manager_runtime_snapshot_payload.get("evicted_before_use_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_ready_late_miss_count": (
            manager_runtime_snapshot_payload.get("ready_late_miss_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_late_completion_unused_count": (
            manager_runtime_snapshot_payload.get("late_completion_unused_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_batch_count": (
            manager_runtime_snapshot_payload.get("queue_batch_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_service_us": (
            manager_runtime_snapshot_payload.get("queue_service_us")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_total_span_us": (
            manager_runtime_snapshot_payload.get("queue_total_span_us")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_wait_us": (
            manager_runtime_snapshot_payload.get("queue_wait_us")
        ),
        "stream_queue_budget_manager_runtime_snapshot_queue_max_delay_us": (
            manager_runtime_snapshot_payload.get("queue_max_delay_us")
        ),
        "stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounting_enabled": (
            manager_runtime_snapshot_payload.get("shifted_issue_accounting_enabled")
        ),
        "stream_queue_budget_manager_runtime_snapshot_shifted_issue_accounted_packet_count": (
            manager_runtime_snapshot_payload.get(
                "shifted_issue_accounted_packet_count",
            )
        ),
        "stream_queue_budget_manager_runtime_snapshot_shifted_issue_unique_issue_key_count": (
            manager_runtime_snapshot_payload.get(
                "shifted_issue_unique_issue_key_count",
            )
        ),
        "stream_queue_budget_manager_runtime_snapshot_decision": (
            manager_runtime_snapshot_payload.get("decision")
        ),
        "stream_queue_budget_manager_runtime_snapshot_block_reason": (
            manager_runtime_snapshot_payload.get("block_reason")
        ),
        "stream_queue_budget_manager_runtime_snapshot_execution_mode": (
            manager_runtime_snapshot_payload.get("execution_mode")
        ),
        "stream_queue_budget_manager_runtime_snapshot_live_payload_runtime_enabled": (
            manager_runtime_snapshot_payload.get("live_payload_runtime_enabled")
        ),
        "stream_queue_budget_manager_runtime_snapshot_payload_transfer_runtime_enabled": (
            manager_runtime_snapshot_payload.get("payload_transfer_runtime_enabled")
        ),
        "stream_queue_budget_manager_runtime_snapshot_payload_deref_allowed": (
            manager_runtime_snapshot_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_manager_runtime_snapshot_payload_deref_runtime_allowed": (
            manager_runtime_snapshot_payload.get("payload_deref_runtime_allowed")
        ),
        "stream_queue_budget_manager_runtime_snapshot_issued_payload_count": (
            manager_runtime_snapshot_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_manager_runtime_snapshot_payload_bytes": (
            manager_runtime_snapshot_payload.get("payload_bytes")
        ),
        "stream_queue_budget_manager_runtime_snapshot_ready_credit": (
            manager_runtime_snapshot_payload.get("ready_credit")
        ),
        "stream_queue_budget_manager_runtime_snapshot_ready_before_demand_credit": (
            manager_runtime_snapshot_payload.get("ready_before_demand_credit")
        ),
        "stream_queue_budget_manager_runtime_snapshot_real_ready_credit_granted": (
            manager_runtime_snapshot_payload.get("real_ready_credit_granted")
        ),
        "stream_queue_budget_manager_runtime_snapshot_kernel_arg_pass_allowed": (
            manager_runtime_snapshot_payload.get("kernel_arg_pass_allowed")
        ),
        "stream_queue_budget_manager_runtime_snapshot_passed_to_kernel": (
            manager_runtime_snapshot_payload.get("passed_to_kernel")
        ),
        "stream_queue_budget_manager_runtime_snapshot_changes_kernel_launch_args": (
            manager_runtime_snapshot_payload.get("changes_kernel_launch_args")
        ),
        "stream_queue_budget_manager_runtime_snapshot_full_fetch_runtime_allowed": (
            manager_runtime_snapshot_payload.get("full_fetch_runtime_allowed")
        ),
        "stream_queue_budget_manager_runtime_snapshot_uses_current_wna16_args": (
            manager_runtime_snapshot_payload.get("uses_current_wna16_args")
        ),
        "stream_queue_budget_manager_runtime_snapshot_passes_current_wna16_args": (
            manager_runtime_snapshot_payload.get("passes_current_wna16_args")
        ),
        "stream_queue_budget_manager_runtime_snapshot_measures_tpot": (
            manager_runtime_snapshot_payload.get("measures_tpot")
        ),
        "stream_queue_budget_manager_runtime_snapshot_measures_vllm_latency": (
            manager_runtime_snapshot_payload.get("measures_vllm_latency")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_present": (
            snapshot_backed_live_runtime_preflight_payload.get("present")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_stage": (
            snapshot_backed_live_runtime_preflight_payload.get("stage")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_status": (
            snapshot_backed_live_runtime_preflight_payload.get("status")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_consumes_runtime_snapshot": (
            snapshot_backed_live_runtime_preflight_payload.get("consumes_runtime_snapshot")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_runtime_snapshot_status": (
            snapshot_backed_live_runtime_preflight_payload.get("runtime_snapshot_status")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_backend": (
            snapshot_backed_live_runtime_preflight_payload.get("manager_backend")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_contract": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "manager_runtime_contract",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_manager_runtime_mode": (
            snapshot_backed_live_runtime_preflight_payload.get("manager_runtime_mode")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_snapshot_source": (
            snapshot_backed_live_runtime_preflight_payload.get("snapshot_source")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_preflight_instantiated": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "live_runtime_preflight_instantiated",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_accounting_snapshot_instantiated": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "accounting_snapshot_instantiated",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_live_runtime_instantiated": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "live_runtime_instantiated",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_capacity_entries": (
            snapshot_backed_live_runtime_preflight_payload.get("capacity_entries")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_issue_lead_tokens": (
            snapshot_backed_live_runtime_preflight_payload.get("issue_lead_tokens")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_deadline_us": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_deadline_us")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_lookahead_us": (
            snapshot_backed_live_runtime_preflight_payload.get("lookahead_us")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_size": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_batch_size")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_resident_count": (
            snapshot_backed_live_runtime_preflight_payload.get("resident_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_fetch_count": (
            snapshot_backed_live_runtime_preflight_payload.get("issued_fetch_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_used_fetch_count": (
            snapshot_backed_live_runtime_preflight_payload.get("used_fetch_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_unused_fetch_count": (
            snapshot_backed_live_runtime_preflight_payload.get("unused_fetch_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_count": (
            snapshot_backed_live_runtime_preflight_payload.get("demand_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_hit_count": (
            snapshot_backed_live_runtime_preflight_payload.get("demand_hit_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_demand_miss_count": (
            snapshot_backed_live_runtime_preflight_payload.get("demand_miss_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_evicted_before_use_count": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "evicted_before_use_count",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_late_miss_count": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "ready_late_miss_count",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_late_completion_unused_count": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "late_completion_unused_count",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_batch_count": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_batch_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_service_us": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_service_us")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_total_span_us": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_total_span_us")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_wait_us": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_wait_us")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_queue_max_delay_us": (
            snapshot_backed_live_runtime_preflight_payload.get("queue_max_delay_us")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounting_enabled": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "shifted_issue_accounting_enabled",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_accounted_packet_count": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "shifted_issue_accounted_packet_count",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_shifted_issue_unique_issue_key_count": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "shifted_issue_unique_issue_key_count",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_decision": (
            snapshot_backed_live_runtime_preflight_payload.get("decision")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_block_reason": (
            snapshot_backed_live_runtime_preflight_payload.get("block_reason")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_execution_mode": (
            snapshot_backed_live_runtime_preflight_payload.get("execution_mode")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_live_payload_runtime_enabled": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "live_payload_runtime_enabled",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_transfer_runtime_enabled": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "payload_transfer_runtime_enabled",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_allowed": (
            snapshot_backed_live_runtime_preflight_payload.get("payload_deref_allowed")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_deref_runtime_allowed": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "payload_deref_runtime_allowed",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_issued_payload_count": (
            snapshot_backed_live_runtime_preflight_payload.get("issued_payload_count")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_payload_bytes": (
            snapshot_backed_live_runtime_preflight_payload.get("payload_bytes")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_credit": (
            snapshot_backed_live_runtime_preflight_payload.get("ready_credit")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_ready_before_demand_credit": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "ready_before_demand_credit",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_real_ready_credit_granted": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "real_ready_credit_granted",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_kernel_arg_pass_allowed": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "kernel_arg_pass_allowed",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_passed_to_kernel": (
            snapshot_backed_live_runtime_preflight_payload.get("passed_to_kernel")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_changes_kernel_launch_args": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "changes_kernel_launch_args",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_full_fetch_runtime_allowed": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "full_fetch_runtime_allowed",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_uses_current_wna16_args": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "uses_current_wna16_args",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_passes_current_wna16_args": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "passes_current_wna16_args",
            )
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_tpot": (
            snapshot_backed_live_runtime_preflight_payload.get("measures_tpot")
        ),
        "stream_queue_budget_snapshot_backed_live_runtime_preflight_measures_vllm_latency": (
            snapshot_backed_live_runtime_preflight_payload.get(
                "measures_vllm_latency",
            )
        ),
        **_prefixed_payload(
            "stream_queue_budget_snapshot_backed_live_runtime_canary",
            snapshot_backed_live_runtime_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_state_shape",
            live_runtime_state_shape_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_object_preflight",
            live_runtime_object_preflight_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_object_adapter_preflight",
            live_runtime_object_adapter_preflight_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_materialization_preflight",
            live_runtime_adapter_materialization_preflight_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_state_object_preflight",
            live_runtime_adapter_state_object_preflight_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_state_validation_preflight",
            live_runtime_adapter_state_validation_preflight_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_state_validation_artifact",
            live_runtime_adapter_state_validation_artifact_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_instantiation_canary",
            live_runtime_adapter_instantiation_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_constructor_binding_preflight",
            live_runtime_adapter_constructor_binding_preflight_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_instance_construction_plan",
            live_runtime_adapter_instance_construction_plan_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_object_shell_evidence",
            live_runtime_adapter_object_shell_evidence_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_operation_rejection_canary",
            live_runtime_adapter_operation_rejection_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_accounting_dry_run_canary",
            live_runtime_adapter_accounting_dry_run_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_mixed_outcome_dry_run_canary",
            live_runtime_adapter_mixed_outcome_dry_run_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_payloadless_instance_canary",
            live_runtime_adapter_payloadless_instance_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_payload_transfer_toggle_disabled_canary",
            live_runtime_adapter_payload_transfer_toggle_disabled_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_payload_issue_request_blocked_canary",
            live_runtime_adapter_payload_issue_request_blocked_canary_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_payload_issue_plan_dry_run",
            live_runtime_adapter_payload_issue_plan_dry_run_payload,
        ),
        **_prefixed_payload(
            "stream_queue_budget_live_runtime_adapter_payload_issue_executor_dry_run",
            live_runtime_adapter_payload_issue_executor_dry_run_payload,
        ),
        "stream_queue_budget_issued_payload_count": _optional_int(
            report,
            "issued_payload_count",
        ),
        "stream_queue_budget_payload_bytes": _optional_int(report, "payload_bytes"),
        "stream_queue_budget_live_payload_runtime_enabled": _optional_bool(
            report,
            "live_payload_runtime_enabled",
        ),
        "stream_queue_budget_payload_transfer_enabled": _optional_bool(
            report,
            "payload_transfer_enabled",
        ),
        "stream_queue_budget_payload_transfer_runtime_enabled": _optional_bool(
            report,
            "payload_transfer_runtime_enabled",
        ),
        "stream_queue_budget_payload_deref_allowed": _optional_bool(
            report,
            "payload_deref_allowed",
        ),
        "stream_queue_budget_payload_deref_runtime_allowed": _optional_bool(
            report,
            "payload_deref_runtime_allowed",
        ),
        "stream_queue_budget_full_fetch_allowed": _optional_bool(
            report,
            "full_fetch_allowed",
        ),
        "stream_queue_budget_full_fetch_runtime_allowed": _optional_bool(
            report,
            "full_fetch_runtime_allowed",
        ),
        "stream_queue_budget_ready_credit": _optional_bool(report, "ready_credit"),
        "stream_queue_budget_ready_before_demand_credit": _optional_bool(
            report,
            "ready_before_demand_credit",
        ),
        "stream_queue_budget_real_ready_credit_granted": _optional_bool(
            report,
            "real_ready_credit_granted",
        ),
        "stream_queue_budget_kernel_arg_pass_allowed": _optional_bool(
            report,
            "kernel_arg_pass_allowed",
        ),
        "stream_queue_budget_passed_to_kernel": _optional_bool(
            report,
            "passed_to_kernel",
        ),
        "stream_queue_budget_changes_kernel_launch_args": _optional_bool(
            report,
            "changes_kernel_launch_args",
        ),
        "stream_queue_budget_uses_current_wna16_args": _optional_bool(
            report,
            "uses_current_wna16_args",
        ),
        "stream_queue_budget_passes_current_wna16_args": _optional_bool(
            report,
            "passes_current_wna16_args",
        ),
        "stream_queue_budget_measures_tpot": _optional_bool(
            report,
            "measures_tpot",
        ),
        "stream_queue_budget_measures_vllm_latency": _optional_bool(
            report,
            "measures_vllm_latency",
        ),
        "stream_queue_budget_live_runtime_instantiated": _optional_bool(
            report,
            "live_runtime_instantiated",
        ),
    }


def _check_stream_noop_safety(
    report: dict[str, Any],
    failures: list[str],
    *,
    label: str,
) -> None:
    if report.get("payload_bytes") != 0:
        failures.append(f"{label}_payload_bytes_nonzero")
    for field in (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if report.get(field) is not False:
            failures.append(f"{label}_{field}_not_false")
    for field in (
        "current_wna16_arg_compatible",
        "requires_wna16_arg_reinterpretation",
        "wna16_benchmark_ready",
    ):
        if field in report and report.get(field) is not False:
            failures.append(f"{label}_{field}_not_false")


def _check_stream_queue_budget_noop_safety(
    report: dict[str, Any],
    failures: list[str],
    *,
    label: str,
) -> None:
    _check_stream_noop_safety(report, failures, label=label)
    if report.get("issued_payload_count") != 0:
        failures.append(f"{label}_issued_payload_count_nonzero")
    for field in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_runtime_allowed",
        "full_fetch_runtime_allowed",
        "live_runtime_instantiated",
    ):
        if report.get(field) is not False:
            failures.append(f"{label}_{field}_not_false")


def _strict_passed(
    report: dict[str, Any],
    failures: list[str],
    *,
    label: str,
) -> bool:
    value = report.get("passed")
    if not isinstance(value, bool):
        failures.append(f"{label}_passed_not_bool")
        return False
    return value


def _ready_time_decision_reason(report: dict[str, Any]) -> str | None:
    reason = report.get("full_fetch_block_reason")
    if isinstance(reason, str):
        return reason
    reason = report.get("decision_reason")
    return reason if isinstance(reason, str) else None


def _check_metadata(section: dict[str, Any], *, root: Path) -> dict[str, Any]:
    failures: list[str] = []
    default_enabled = bool(section.get("default_enabled", False))
    summary_path = _resolve(section.get("summary"), root=root)
    summary = _load_json(summary_path, failures, label="summary")
    metadata_positive_count = (
        int(summary.get("metadata_positive_count", 0) or 0)
        if isinstance(summary, dict)
        else 0
    )
    max_default_positive = int(section.get("max_default_positive_count", 0) or 0)
    if default_enabled:
        failures.append("metadata_default_enabled")
    if default_enabled and metadata_positive_count <= max_default_positive:
        failures.append("metadata_default_enabled_without_positive_evidence")
    return {
        "decision": "shadow_only",
        "failures": failures,
        "default_enabled": default_enabled,
        "summary": str(summary_path),
        "metadata_positive_count": metadata_positive_count,
        "max_default_positive_count": max_default_positive,
    }


def _check_premap(section: dict[str, Any], *, root: Path) -> dict[str, Any]:
    failures: list[str] = []
    default_enabled = bool(section.get("default_enabled", False))
    summary_path = _resolve(section.get("summary"), root=root)
    summary = _load_json(summary_path, failures, label="summary")
    premap_positive_count = (
        int(summary.get("premap_positive_count", 0) or 0)
        if isinstance(summary, dict)
        else 0
    )
    min_positive_count = int(section.get("min_positive_count", 1) or 1)
    if premap_positive_count < min_positive_count:
        failures.append(f"premap_positive_count_too_low:{premap_positive_count}")

    capacity_path = _resolve(section.get("capacity_gate"), root=root)
    capacity = _load_yaml_or_failure(capacity_path, failures, label="capacity_gate")
    capacity_gate = capacity.get("capacity_gate") or {}
    recommended = int(capacity_gate.get("recommended_capacity_entries", 0) or 0)
    no_eviction = int(capacity_gate.get("no_eviction_capacity_entries", 0) or 0)
    min_capacity = int(section.get("min_capacity_entries", 1) or 1)
    if recommended < min_capacity:
        failures.append(f"recommended_capacity_below_min:{recommended}")
    if no_eviction <= 0:
        failures.append("no_eviction_capacity_missing")
    if no_eviction > recommended:
        failures.append(
            f"no_eviction_capacity_above_recommended:{no_eviction}>{recommended}"
        )
    if not default_enabled:
        failures.append("premap_default_disabled")
    return {
        "decision": "lab_enabled_descriptor_prep_only",
        "failures": failures,
        "default_enabled": default_enabled,
        "summary": str(summary_path),
        "capacity_gate": str(capacity_path),
        "premap_positive_count": premap_positive_count,
        "min_positive_count": min_positive_count,
        "recommended_capacity_entries": recommended,
        "no_eviction_capacity_entries": no_eviction,
        "min_capacity_entries": min_capacity,
    }


def _resolve(value: Any, *, root: Path) -> Path:
    if value in (None, ""):
        return Path("<missing>")
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else root / path


def _load_json(path: Path, failures: list[str], *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}_load_failed:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{label}_not_object")
        return {}
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object.")
    return payload


def _load_yaml_or_failure(
    path: Path,
    failures: list[str],
    *,
    label: str,
) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        failures.append(f"{label}_load_failed:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{label}_not_object")
        return {}
    return payload


def _optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _strict_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    return value if type(value) is int else None


def _optional_bool(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_prefetch_lab_default_gate(args.config, root=args.root)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
