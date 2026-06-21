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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_premap_payload_cache_stream_shifted_issue_replay_contract import (  # noqa: E402
    check_shifted_issue_replay_contract,
)
from scripts.check_premap_payload_cache_ready_time_gate import (  # noqa: E402
    check_summary as check_ready_time_summary,
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
    if not isinstance(runtime_participation_status, str) or not runtime_participation_status:
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
            str(runtime_participation_status)
            if runtime_participation_status is not None
            else None
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
