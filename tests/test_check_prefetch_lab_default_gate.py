from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.check_prefetch_lab_default_gate import (
    check_prefetch_lab_default_gate,
    main,
)

_FULL_FETCH_DECISION_NOOP_FIELDS = {
    "payload_bytes": 0,
    "issued_payload_count": 0,
    "live_payload_runtime_enabled": False,
    "payload_transfer_enabled": False,
    "payload_transfer_runtime_enabled": False,
    "payload_deref_allowed": False,
    "payload_deref_runtime_allowed": False,
    "full_fetch_runtime_allowed": False,
    "ready_credit": False,
    "ready_before_demand_credit": False,
    "real_ready_credit_granted": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
    "wna16_benchmark_ready": False,
    "measures_tpot": False,
    "measures_vllm_latency": False,
    "live_runtime_instantiated": False,
}


def _write_fixture(tmp_path: Path, *, allow_full_fetch: bool = False) -> Path:
    ready = tmp_path / "ready_gate.json"
    ready.write_text(
        json.dumps({"passed": True, "allow_full_fetch": allow_full_fetch}),
        encoding="utf-8",
    )
    measured_copy = tmp_path / "copy.json"
    measured_copy.write_text('{"rows": []}\n', encoding="utf-8")
    direct_snapshot = tmp_path / "ready_time_direct_snapshot.json"
    direct_snapshot.write_text(
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": False,
                "decision_reason": "full_fetch_threshold_not_met",
                "threshold_failures": ["used_per_issued_fetch_below_threshold"],
                "metrics": {
                    "mode": "ready_time",
                    "manager_count": 1,
                    "demand_count": 100,
                    "demand_hit_count": 25,
                    "demand_hit_rate": 0.25,
                    "ready_late_miss_count": 30,
                    "ready_late_miss_rate": 0.30,
                    "issued_fetch_count": 8,
                    "used_fetch_count": 0,
                    "used_per_issued_fetch": 0.0,
                    "queue_batch_size": 8,
                    "queue_deadline_us": 1000.0,
                    "measured_copy_path": str(measured_copy),
                    "measured_copy_us_per_issue": 100.0,
                    "direct_snapshot_present": True,
                    "direct_manager_mode": "ready_time",
                    "direct_demand_count": 100,
                    "direct_demand_hit_count": 25,
                    "direct_ready_late_miss_count": 30,
                    "direct_issued_fetch_count": 8,
                    "direct_used_fetch_count": 0,
                    "direct_queue_batch_size": 8,
                    "direct_queue_deadline_us": 1000.0,
                    "direct_snapshot_runtime_stage": (
                        "online_ready_time_payload_cache_accounting_only"
                    ),
                    "direct_snapshot_payload_bytes": 0,
                    "direct_snapshot_ready_credit": False,
                    "direct_snapshot_real_ready_credit_granted": False,
                    "direct_snapshot_full_fetch_runtime_allowed": False,
                    "direct_snapshot_payload_transfer_runtime_enabled": False,
                    "direct_snapshot_changes_kernel_launch_args": False,
                    "direct_snapshot_demand_on_consumer": True,
                    "direct_snapshot_issue_sources": [
                        "prelaunch_observed_transition_premap_shadow"
                    ],
                    "direct_snapshot_runtime_participation_present": True,
                    "direct_snapshot_runtime_participation_stage": (
                        "online_ready_time_payload_cache_runtime_participation_dry_run"
                    ),
                    "direct_snapshot_runtime_participation_status": (
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_participation_consumes_manager_snapshot": (
                        True
                    ),
                    "direct_snapshot_runtime_participation_payload_bytes": 0,
                    "direct_snapshot_runtime_participation_ready_credit": False,
                    "direct_snapshot_runtime_participation_real_ready_credit_granted": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_kernel_arg_pass_allowed": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_changes_kernel_launch_args": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_full_fetch_runtime_allowed": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_payload_transfer_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_participation_issue_sources": [
                        "prelaunch_observed_transition_premap_shadow"
                    ],
                    "direct_snapshot_runtime_participation_candidate_reason": (
                        "no_used_fetch"
                    ),
                    "direct_snapshot_runtime_plan_present": True,
                    "direct_snapshot_runtime_plan_stage": (
                        "payload_cache_runtime_plan_lab_gate_dry_run"
                    ),
                    "direct_snapshot_runtime_plan_status": (
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_plan_consumes_participation": True,
                    "direct_snapshot_runtime_plan_participation_status": (
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_plan_live_payload_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_plan_planned_issue_count": 0,
                    "direct_snapshot_runtime_plan_payload_bytes": 0,
                    "direct_snapshot_runtime_plan_ready_credit": False,
                    "direct_snapshot_runtime_plan_kernel_arg_pass_allowed": False,
                    "direct_snapshot_runtime_plan_changes_kernel_launch_args": False,
                    "direct_snapshot_runtime_plan_full_fetch_runtime_allowed": False,
                    "direct_snapshot_runtime_execution_present": True,
                    "direct_snapshot_runtime_execution_stage": (
                        "payload_cache_runtime_execution_lab_gate_dry_run"
                    ),
                    "direct_snapshot_runtime_execution_status": (
                        "blocked_by_runtime_plan:"
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_execution_consumes_plan": True,
                    "direct_snapshot_runtime_execution_plan_status": (
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_execution_decision": "blocked",
                    "direct_snapshot_runtime_execution_block_reason": (
                        "participation_not_full_fetch_candidate:"
                        "accounting_only_no_used_fetch"
                    ),
                    "direct_snapshot_runtime_execution_execution_mode": (
                        "payloadless_lab_gate_dry_run"
                    ),
                    "direct_snapshot_runtime_execution_live_payload_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_payload_transfer_runtime_enabled": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_issued_payload_count": 0,
                    "direct_snapshot_runtime_execution_payload_bytes": 0,
                    "direct_snapshot_runtime_execution_ready_credit": False,
                    "direct_snapshot_runtime_execution_real_ready_credit_granted": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_kernel_arg_pass_allowed": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_changes_kernel_launch_args": (
                        False
                    ),
                    "direct_snapshot_runtime_execution_full_fetch_runtime_allowed": (
                        False
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_stream_lookahead",
                "current_lookahead_us": 0.0,
                "required_stream_lookahead_us": 2400000.0,
                "lookahead_deficit_us": 2400000.0,
                "first_model_passing_lookahead_us": 2400000.0,
                "required_shifted_issue_accounting": {
                    "shifted_issue_accounting_enabled": True,
                    "shifted_issue_lead_tokens": 32,
                    "shifted_issue_clamped_issue_count": 12,
                    "shifted_issue_duplicate_issue_key_count": 12,
                    "shifted_issue_unique_issue_key_count": 16,
                    "shifted_issue_accounted_packet_count": 28,
                    "shifted_issue_invalid_export_count": 0,
                    "shifted_issue_row_shift_mismatch_count": 0,
                    "shifted_issue_row_clamp_mismatch_count": 0,
                },
                "metadata_premap_runtime_preferred": True,
                "descriptor_prep_runtime_preferred": True,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_feasibility = tmp_path / "stream_feasibility.json"
    stream_feasibility.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_feasibility",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "current_runtime_satisfies_model": False,
                "feasible_within_configured_token_window": True,
                "min_required_lead_tokens": 24,
                "max_required_lead_tokens": 48,
                "min_deficit_lead_tokens": 24,
                "max_deficit_lead_tokens": 48,
                "max_candidate_lead_tokens": 64,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_lead = tmp_path / "stream_lead.json"
    stream_lead.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_lead_token_sweep",
                "passed": True,
                "full_fetch_allowed": False,
                "full_fetch_runtime_allowed": False,
                "event_timing_mode": "token_index",
                "token_timing_enabled": True,
                "decode_token_us": 75000.0,
                "first_model_passing_lead_tokens": 32,
                "first_model_passing_lookahead_us": 2400000.0,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_shifted = tmp_path / "stream_shifted_issue_contract.json"
    stream_shifted.write_text(
        json.dumps(
            {
                "artifact_kind": (
                    "premap_payload_cache_stream_shifted_issue_replay_contract"
                ),
                "passed": True,
                "failures": [],
                "issue_lead_tokens": 32,
                "packet_count": 5,
                "schedulable_packet_count": 4,
                "empty_issue_exempt_count": 1,
                "clamped_issue_count": 2,
                "duplicate_demand_key_count": 0,
                "duplicate_issue_key_count": 2,
                "unique_demand_key_count": 4,
                "unique_issue_key_count": 2,
                "total_issue_candidates": 32,
                "issue_hash_count": 4,
                "allow_clamped_issue_tokens": True,
                "allow_duplicate_issue_keys": True,
                "full_fetch_runtime_allowed": False,
                "full_fetch_allowed": False,
                "current_wna16_arg_compatible": False,
                "requires_wna16_arg_reinterpretation": False,
                "wna16_benchmark_ready": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
                "rows": [
                    {
                        "packet_index": index,
                        "sample_idx": 0,
                        "record_id": "record-0",
                        "sequence_id": 0,
                        "layer_id": 0,
                        "demand_token_index": demand,
                        "issue_token_index": max(0, demand - 32),
                        "issue_clamped_to_zero": demand < 32,
                    }
                    for index, demand in enumerate([8, 16, 32, 48])
                ],
            }
        ),
        encoding="utf-8",
    )
    stream_queue_budget = tmp_path / "stream_queue_budget.json"
    stream_queue_budget.write_text(
        json.dumps(
            {
                "artifact_kind": (
                    "premap_payload_cache_issue_stream_executor_queue_budget_sweep"
                ),
                "passed": True,
                "failures": [],
                "event_timing_mode": "token_index",
                "cell_count": 1,
                "cells": [
                    {
                        "capacity": 4096,
                        "cell_index": 0,
                        "model_passed": True,
                        "passed": True,
                        "queue_deadline_us": 100.0,
                        "first_model_passing_issue_lead_tokens": 32,
                        "first_model_passing_lookahead_us": 2400000.0,
                        "first_model_passing_shifted_issue_accounting": {
                            "shifted_issue_accounting_enabled": True,
                            "shifted_issue_lead_tokens": 32,
                            "shifted_issue_clamped_issue_count": 12,
                            "shifted_issue_duplicate_issue_key_count": 12,
                            "shifted_issue_unique_issue_key_count": 16,
                            "shifted_issue_accounted_packet_count": 28,
                            "shifted_issue_invalid_export_count": 0,
                            "shifted_issue_row_shift_mismatch_count": 0,
                            "shifted_issue_row_clamp_mismatch_count": 0,
                        },
                    },
                ],
                "first_model_passing_cell": {
                    "capacity": 4096,
                    "cell_index": 0,
                    "issue_lead_tokens": 32,
                    "lookahead_us": 2400000.0,
                    "queue_deadline_us": 100.0,
                    "shifted_issue_accounting": {
                        "shifted_issue_accounting_enabled": True,
                        "shifted_issue_lead_tokens": 32,
                        "shifted_issue_clamped_issue_count": 12,
                        "shifted_issue_duplicate_issue_key_count": 12,
                        "shifted_issue_unique_issue_key_count": 16,
                        "shifted_issue_accounted_packet_count": 28,
                        "shifted_issue_invalid_export_count": 0,
                        "shifted_issue_row_shift_mismatch_count": 0,
                        "shifted_issue_row_clamp_mismatch_count": 0,
                    },
                },
                "full_fetch_allowed": False,
                "full_fetch_block_reason": "real_payload_runtime_not_enabled",
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    summary = tmp_path / "metadata_premap.json"
    summary.write_text(
        json.dumps(
            {
                "ok": True,
                "metadata_positive_count": 0,
                "premap_positive_count": 4,
            }
        ),
        encoding="utf-8",
    )
    capacity = tmp_path / "capacity.yaml"
    capacity.write_text(
        yaml.safe_dump(
            {
                "capacity_gate": {
                    "recommended_capacity_entries": 12288,
                    "no_eviction_capacity_entries": 12288,
                }
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "gate.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "gate_id": "test-gate",
                "full_fetch": {
                    "default_enabled": False,
                    "ready_time_gate_report": str(ready),
                    "ready_time_direct_snapshot_report": str(direct_snapshot),
                    "stream_decision_gate_report": str(stream_decision),
                    "stream_earlier_issue_feasibility_report": str(
                        stream_feasibility
                    ),
                    "stream_earlier_issue_lead_token_sweep_report": str(stream_lead),
                    "stream_shifted_issue_replay_contract_report": str(
                        stream_shifted
                    ),
                    "stream_queue_budget_report": str(stream_queue_budget),
                    "stream_shifted_issue_replay_required_lead_tokens": 32,
                    "stream_shifted_issue_replay_min_schedulable_packets": 4,
                },
                "metadata": {
                    "default_enabled": False,
                    "summary": str(summary),
                    "max_default_positive_count": 0,
                },
                "premap": {
                    "default_enabled": True,
                    "summary": str(summary),
                    "min_positive_count": 4,
                    "capacity_gate": str(capacity),
                    "min_capacity_entries": 12288,
                },
            }
        ),
        encoding="utf-8",
    )
    return config


def test_prefetch_lab_default_gate_passes_low_risk_premap_path(tmp_path: Path):
    result = check_prefetch_lab_default_gate(_write_fixture(tmp_path), root=tmp_path)

    assert result["passed"] is True
    assert result["decisions"] == {
        "full_fetch": "blocked_by_ready_time_measured_copy",
        "metadata": "shadow_only",
        "premap": "lab_enabled_descriptor_prep_only",
    }
    assert result["sections"]["premap"]["recommended_capacity_entries"] == 12288
    full_fetch = result["sections"]["full_fetch"]
    assert full_fetch["ready_time_direct_snapshot_report_present"] is True
    assert full_fetch["ready_time_direct_snapshot_report_passed"] is True
    assert full_fetch["ready_time_direct_snapshot_report_recheck_passed"] is True
    assert full_fetch["ready_time_direct_snapshot_report_recheck_failures"] == []
    assert full_fetch["ready_time_direct_snapshot_present"] is True
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_stage"]
        == "online_ready_time_payload_cache_accounting_only"
    )
    assert full_fetch["ready_time_direct_snapshot_payload_bytes"] == 0
    assert full_fetch["ready_time_direct_snapshot_full_fetch_runtime_allowed"] is False
    assert full_fetch["ready_time_direct_snapshot_changes_kernel_launch_args"] is False
    assert full_fetch["ready_time_direct_snapshot_issue_sources"] == [
        "prelaunch_observed_transition_premap_shadow"
    ]
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_participation_present"] is True
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_participation_stage"]
        == "online_ready_time_payload_cache_runtime_participation_dry_run"
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_participation_status"]
        == "accounting_only_no_used_fetch"
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_participation_consumes_manager_snapshot"
        ]
        is True
    )
    assert full_fetch[
        "ready_time_direct_snapshot_runtime_participation_payload_bytes"
    ] == 0
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_participation_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_participation_issue_sources"
        ]
        == ["prelaunch_observed_transition_premap_shadow"]
    )
    assert full_fetch["ready_time_direct_snapshot_runtime_plan_present"] is True
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_plan_stage"]
        == "payload_cache_runtime_plan_lab_gate_dry_run"
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_plan_status"]
        == "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_plan_consumes_participation"
        ]
        is True
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_plan_live_payload_runtime_enabled"
        ]
        is False
    )
    assert full_fetch["ready_time_direct_snapshot_runtime_plan_planned_issue_count"] == 0
    assert full_fetch["ready_time_direct_snapshot_runtime_plan_payload_bytes"] == 0
    assert full_fetch["ready_time_direct_snapshot_runtime_plan_ready_credit"] is False
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_plan_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_plan_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_plan_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert full_fetch["ready_time_direct_snapshot_runtime_execution_present"] is True
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_stage"]
        == "payload_cache_runtime_execution_lab_gate_dry_run"
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_status"]
        == "blocked_by_runtime_plan:"
        "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_plan_status"]
        == full_fetch["ready_time_direct_snapshot_runtime_plan_status"]
    )
    assert full_fetch["ready_time_direct_snapshot_runtime_execution_decision"] == "blocked"
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_block_reason"]
        == full_fetch["ready_time_direct_snapshot_runtime_plan_status"]
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_execution_mode"]
        == "payloadless_lab_gate_dry_run"
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_consumes_plan"]
        is True
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_execution_live_payload_runtime_enabled"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_execution_payload_transfer_runtime_enabled"
        ]
        is False
    )
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_issued_payload_count"]
        == 0
    )
    assert full_fetch["ready_time_direct_snapshot_runtime_execution_payload_bytes"] == 0
    assert (
        full_fetch["ready_time_direct_snapshot_runtime_execution_ready_credit"]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_execution_real_ready_credit_granted"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_execution_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_execution_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        full_fetch[
            "ready_time_direct_snapshot_runtime_execution_full_fetch_runtime_allowed"
        ]
        is False
    )
    assert full_fetch["stream_shifted_issue_replay_contract_present"] is True
    assert full_fetch["stream_shifted_issue_replay_contract_passed"] is True
    assert full_fetch["stream_shifted_issue_replay_issue_lead_tokens"] == 32
    assert full_fetch["stream_shifted_issue_replay_schedulable_packet_count"] == 4
    assert full_fetch["stream_shifted_issue_replay_row_shift_mismatch_count"] == 0
    assert full_fetch["stream_shifted_issue_replay_source_payload_bytes"] == 0
    assert full_fetch["stream_shifted_issue_replay_full_fetch_runtime_allowed"] is False
    assert full_fetch["stream_queue_budget_present"] is True
    assert full_fetch["stream_queue_budget_passed"] is True
    assert full_fetch["stream_queue_budget_cell_count"] == 1
    assert (
        full_fetch["stream_queue_budget_first_model_passing_issue_lead_tokens"] == 32
    )
    assert full_fetch["stream_queue_budget_first_model_passing_capacity"] == 4096
    assert (
        full_fetch["stream_queue_budget_first_shifted_issue_accounted_packet_count"]
        == 28
    )
    prefix = "stream_queue_budget_live_runtime_adapter_payload_issue_request_blocked_canary"
    assert full_fetch[f"{prefix}_request_source"] == "queue_budget_first_model_passing_cell"
    assert full_fetch[f"{prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{prefix}_payload_transfer_runtime_enabled"] is False
    plan_prefix = "stream_queue_budget_live_runtime_adapter_payload_issue_plan_dry_run"
    assert full_fetch[f"{plan_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{plan_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{plan_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{plan_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{plan_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{plan_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{plan_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{plan_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{plan_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{plan_prefix}_payload_transfer_runtime_enabled"] is False
    assert full_fetch[f"{plan_prefix}_kernel_arg_pass_allowed"] is False
    assert full_fetch[f"{plan_prefix}_passed_to_kernel"] is False
    executor_prefix = (
        "stream_queue_budget_live_runtime_adapter_payload_issue_executor_dry_run"
    )
    assert full_fetch[f"{executor_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{executor_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{executor_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{executor_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{executor_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{executor_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{executor_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{executor_prefix}_scheduled_issue_count"] == 0
    assert full_fetch[f"{executor_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{executor_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{executor_prefix}_payload_transfer_runtime_enabled"] is False
    assert full_fetch[f"{executor_prefix}_kernel_arg_pass_allowed"] is False
    assert full_fetch[f"{executor_prefix}_passed_to_kernel"] is False
    queue_entry_prefix = (
        "stream_queue_budget_live_runtime_adapter_payload_issue_queue_entry_dry_run"
    )
    assert full_fetch[f"{queue_entry_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{queue_entry_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{queue_entry_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{queue_entry_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{queue_entry_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{queue_entry_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{queue_entry_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{queue_entry_prefix}_scheduled_issue_count"] == 0
    assert full_fetch[f"{queue_entry_prefix}_queued_issue_count"] == 0
    assert full_fetch[f"{queue_entry_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{queue_entry_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{queue_entry_prefix}_queue_entry_enqueued"] is False
    assert full_fetch[f"{queue_entry_prefix}_queue_submit_allowed"] is False
    assert full_fetch[f"{queue_entry_prefix}_payload_transfer_runtime_enabled"] is False
    assert full_fetch[f"{queue_entry_prefix}_kernel_arg_pass_allowed"] is False
    assert full_fetch[f"{queue_entry_prefix}_passed_to_kernel"] is False
    queue_submit_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_queue_submit_blocked_canary"
    )
    assert full_fetch[f"{queue_submit_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{queue_submit_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{queue_submit_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{queue_submit_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{queue_submit_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{queue_submit_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{queue_submit_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_scheduled_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_queued_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_submitted_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{queue_submit_prefix}_queue_submit_checked"] is True
    assert full_fetch[f"{queue_submit_prefix}_queue_submit_rejected"] is True
    assert full_fetch[f"{queue_submit_prefix}_queue_submit_allowed"] is False
    assert full_fetch[f"{queue_submit_prefix}_queue_entry_enqueued"] is False
    assert full_fetch[f"{queue_submit_prefix}_payload_transfer_runtime_enabled"] is False
    assert full_fetch[f"{queue_submit_prefix}_kernel_arg_pass_allowed"] is False
    assert full_fetch[f"{queue_submit_prefix}_passed_to_kernel"] is False
    inflight_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_inflight_admission_blocked_canary"
    )
    assert full_fetch[f"{inflight_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{inflight_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{inflight_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{inflight_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{inflight_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{inflight_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{inflight_prefix}_submitted_issue_count"] == 0
    assert full_fetch[f"{inflight_prefix}_inflight_issue_count"] == 0
    assert full_fetch[f"{inflight_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{inflight_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{inflight_prefix}_inflight_admission_checked"] is True
    assert full_fetch[f"{inflight_prefix}_inflight_admission_rejected"] is True
    assert full_fetch[f"{inflight_prefix}_inflight_admission_allowed"] is False
    assert full_fetch[f"{inflight_prefix}_inflight_queue_enqueued"] is False
    assert full_fetch[f"{inflight_prefix}_passed_to_kernel"] is False
    dispatch_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_scheduler_dispatch_blocked_canary"
    )
    assert full_fetch[f"{dispatch_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{dispatch_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{dispatch_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{dispatch_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{dispatch_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{dispatch_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{dispatch_prefix}_submitted_issue_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_inflight_issue_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_dispatched_issue_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_checked"] is True
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_rejected"] is True
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_allowed"] is False
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_enqueued"] is False
    assert full_fetch[f"{dispatch_prefix}_passed_to_kernel"] is False
    packet_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_command_packet_dry_run"
    )
    assert full_fetch[f"{packet_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{packet_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{packet_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{packet_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{packet_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{packet_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{packet_prefix}_dispatched_issue_count"] == 0
    assert full_fetch[f"{packet_prefix}_command_packet_count"] == 0
    assert full_fetch[f"{packet_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{packet_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{packet_prefix}_command_packet_shape_checked"] is True
    assert full_fetch[f"{packet_prefix}_command_packet_submitted"] is False
    assert full_fetch[f"{packet_prefix}_command_packet_executed"] is False
    assert full_fetch[f"{packet_prefix}_passed_to_kernel"] is False
    transport_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_transport_enqueue_blocked_canary"
    )
    assert full_fetch[f"{transport_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{transport_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{transport_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{transport_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{transport_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{transport_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{transport_prefix}_command_packet_count"] == 0
    assert full_fetch[f"{transport_prefix}_transport_work_count"] == 0
    assert full_fetch[f"{transport_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{transport_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{transport_prefix}_transport_enqueue_checked"] is True
    assert full_fetch[f"{transport_prefix}_transport_enqueue_rejected"] is True
    assert full_fetch[f"{transport_prefix}_transport_enqueue_allowed"] is False
    assert full_fetch[f"{transport_prefix}_transport_work_enqueued"] is False
    assert full_fetch[f"{transport_prefix}_passed_to_kernel"] is False
    worker_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_transport_worker_dispatch_blocked_canary"
    )
    assert full_fetch[f"{worker_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{worker_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{worker_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{worker_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{worker_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{worker_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{worker_prefix}_transport_work_count"] == 0
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_count"] == 0
    assert full_fetch[f"{worker_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{worker_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_checked"] is True
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_rejected"] is True
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_allowed"] is False
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatched"] is False
    assert full_fetch[f"{worker_prefix}_passed_to_kernel"] is False
    descriptor_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_dry_run"
    )
    assert full_fetch[f"{descriptor_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{descriptor_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{descriptor_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{descriptor_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{descriptor_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{descriptor_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{descriptor_prefix}_transport_work_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_transport_worker_dispatch_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_shape_checked"] is True
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_executed"] is False
    assert full_fetch[f"{descriptor_prefix}_passed_to_kernel"] is False
    submit_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_submit_blocked_canary"
    )
    assert full_fetch[f"{submit_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{submit_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{submit_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{submit_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{submit_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{submit_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{submit_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{submit_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{submit_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submit_checked"] is True
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submit_rejected"] is True
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submit_allowed"] is False
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{submit_prefix}_copy_descriptor_executed"] is False
    assert full_fetch[f"{submit_prefix}_passed_to_kernel"] is False
    dispatch_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_dispatch_blocked_canary"
    )
    assert full_fetch[f"{dispatch_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{dispatch_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{dispatch_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{dispatch_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{dispatch_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{dispatch_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatch_checked"] is True
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatch_rejected"] is True
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatch_allowed"] is False
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatched"] is False
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_executed"] is False
    assert full_fetch[f"{dispatch_prefix}_passed_to_kernel"] is False
    execute_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_execution_blocked_canary"
    )
    assert full_fetch[f"{execute_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{execute_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{execute_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{execute_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{execute_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{execute_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{execute_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{execute_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{execute_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{execute_prefix}_copy_descriptor_execution_checked"] is True
    assert full_fetch[f"{execute_prefix}_copy_descriptor_execution_rejected"] is True
    assert full_fetch[f"{execute_prefix}_copy_descriptor_execution_allowed"] is False
    assert full_fetch[f"{execute_prefix}_copy_descriptor_dispatched"] is False
    assert full_fetch[f"{execute_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{execute_prefix}_copy_descriptor_executed"] is False
    assert full_fetch[f"{execute_prefix}_passed_to_kernel"] is False
    completion_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_completion_blocked_canary"
    )
    assert full_fetch[f"{completion_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{completion_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{completion_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{completion_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{completion_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{completion_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{completion_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{completion_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{completion_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{completion_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{completion_prefix}_copy_completion_checked"] is True
    assert full_fetch[f"{completion_prefix}_copy_completion_rejected"] is True
    assert full_fetch[f"{completion_prefix}_copy_completion_allowed"] is False
    assert full_fetch[f"{completion_prefix}_copy_completed"] is False
    assert full_fetch[f"{completion_prefix}_ready_credit"] is False
    assert full_fetch[f"{completion_prefix}_real_ready_credit_granted"] is False
    assert full_fetch[f"{completion_prefix}_passed_to_kernel"] is False
    ready_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_ready_credit_blocked_canary"
    )
    assert full_fetch[f"{ready_prefix}_request_source"] == "queue_budget_first_model_passing_cell"
    assert full_fetch[f"{ready_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{ready_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{ready_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{ready_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{ready_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{ready_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{ready_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{ready_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{ready_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{ready_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{ready_prefix}_ready_credit_checked"] is True
    assert full_fetch[f"{ready_prefix}_ready_credit_rejected"] is True
    assert full_fetch[f"{ready_prefix}_ready_credit_allowed"] is False
    assert full_fetch[f"{ready_prefix}_ready_credit_granted"] is False
    assert full_fetch[f"{ready_prefix}_ready_before_demand_credit_granted"] is False
    assert full_fetch[f"{ready_prefix}_real_payload_ready"] is False
    assert full_fetch[f"{ready_prefix}_ready_credit"] is False
    assert full_fetch[f"{ready_prefix}_real_ready_credit_granted"] is False
    assert full_fetch[f"{ready_prefix}_passed_to_kernel"] is False
    residency_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_residency_update_blocked_canary"
    )
    assert full_fetch[f"{residency_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{residency_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{residency_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{residency_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{residency_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{residency_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{residency_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{residency_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{residency_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{residency_prefix}_residency_update_count"] == 0
    assert full_fetch[f"{residency_prefix}_resident_payload_count"] == 0
    assert full_fetch[f"{residency_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{residency_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{residency_prefix}_resident_payload_bytes"] == 0
    assert full_fetch[f"{residency_prefix}_residency_update_checked"] is True
    assert full_fetch[f"{residency_prefix}_residency_update_rejected"] is True
    assert full_fetch[f"{residency_prefix}_residency_update_allowed"] is False
    assert full_fetch[f"{residency_prefix}_residency_updated"] is False
    assert full_fetch[f"{residency_prefix}_payload_marked_resident"] is False
    assert full_fetch[f"{residency_prefix}_resident_payload_ready"] is False
    assert full_fetch[f"{residency_prefix}_ready_credit"] is False
    assert full_fetch[f"{residency_prefix}_real_ready_credit_granted"] is False
    assert full_fetch[f"{residency_prefix}_passed_to_kernel"] is False
    deref_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_payload_deref_blocked_canary"
    )
    assert full_fetch[f"{deref_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{deref_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{deref_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{deref_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{deref_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{deref_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{deref_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{deref_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{deref_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{deref_prefix}_residency_update_count"] == 0
    assert full_fetch[f"{deref_prefix}_resident_payload_count"] == 0
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_count"] == 0
    assert full_fetch[f"{deref_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{deref_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{deref_prefix}_resident_payload_bytes"] == 0
    assert full_fetch[f"{deref_prefix}_dereferenced_payload_bytes"] == 0
    assert full_fetch[f"{deref_prefix}_payload_deref_checked"] is True
    assert full_fetch[f"{deref_prefix}_payload_deref_rejected"] is True
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_checked"] is True
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_rejected"] is True
    assert full_fetch[f"{deref_prefix}_payload_deref_allowed_for_resident_payload"] is False
    assert full_fetch[f"{deref_prefix}_payload_deref_attempted"] is False
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_attempted"] is False
    assert full_fetch[f"{deref_prefix}_payload_marked_resident"] is False
    assert full_fetch[f"{deref_prefix}_resident_payload_ready"] is False
    assert full_fetch[f"{deref_prefix}_payload_deref_allowed"] is False
    assert full_fetch[f"{deref_prefix}_payload_deref_runtime_allowed"] is False
    assert full_fetch[f"{deref_prefix}_ready_credit"] is False
    assert full_fetch[f"{deref_prefix}_real_ready_credit_granted"] is False
    assert full_fetch[f"{deref_prefix}_passed_to_kernel"] is False
    demand_hit_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_demand_hit_publication_blocked_canary"
    )
    assert full_fetch[f"{demand_hit_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{demand_hit_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{demand_hit_prefix}_source_issue_unique_key_count"] == 16
    assert full_fetch[f"{demand_hit_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{demand_hit_prefix}_source_issue_lead_tokens"] == 32
    assert full_fetch[f"{demand_hit_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{demand_hit_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_residency_update_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_resident_payload_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_payload_handle_deref_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_consumer_visible_payload_hit_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_resident_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_dereferenced_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_checked"] is True
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_rejected"] is True
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_allowed"] is False
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_published"] is False
    assert full_fetch[f"{demand_hit_prefix}_consumer_visible_payload_hit"] is False
    assert full_fetch[f"{demand_hit_prefix}_prefetched_demand_hit"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_deref_attempted"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_handle_deref_attempted"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_marked_resident"] is False
    assert full_fetch[f"{demand_hit_prefix}_resident_payload_ready"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_deref_allowed"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_deref_runtime_allowed"] is False
    assert full_fetch[f"{demand_hit_prefix}_ready_credit"] is False
    assert full_fetch[f"{demand_hit_prefix}_real_ready_credit_granted"] is False
    assert full_fetch[f"{demand_hit_prefix}_passed_to_kernel"] is False
    assert full_fetch["stream_queue_budget_runtime_envelope_present"] is True
    assert (
        full_fetch["stream_queue_budget_runtime_envelope_stage"]
        == "payload_cache_queue_budget_runtime_envelope_lab_gate"
    )
    assert (
        full_fetch["stream_queue_budget_runtime_envelope_status"]
        == "model_queue_budget_satisfied_runtime_disabled"
    )
    assert (
        full_fetch["stream_queue_budget_runtime_envelope_execution_mode"]
        == "payloadless_queue_budget_lab_gate"
    )
    assert full_fetch["stream_queue_budget_runtime_envelope_payload_bytes"] == 0
    assert (
        full_fetch["stream_queue_budget_runtime_envelope_kernel_arg_pass_allowed"]
        is False
    )
    assert full_fetch["stream_queue_budget_live_payload_stage_present"] is True
    assert (
        full_fetch["stream_queue_budget_live_payload_stage_status"]
        == (
            "blocked_by_queue_budget_runtime_envelope:"
            "model_queue_budget_satisfied_runtime_disabled"
        )
    )
    assert (
        full_fetch["stream_queue_budget_live_payload_stage_execution_mode"]
        == "payloadless_live_payload_stage_preflight"
    )
    assert full_fetch["stream_queue_budget_live_payload_stage_payload_bytes"] == 0
    assert (
        full_fetch[
            "stream_queue_budget_live_payload_stage_live_payload_runtime_enabled"
        ]
        is False
    )
    assert (
        full_fetch["stream_queue_budget_live_payload_stage_payload_deref_allowed"]
        is False
    )
    assert (
        full_fetch[
            "stream_queue_budget_live_payload_stage_payload_deref_runtime_allowed"
        ]
        is False
    )
    assert (
        full_fetch["stream_queue_budget_live_payload_stage_kernel_arg_pass_allowed"]
        is False
    )
    assert full_fetch["stream_queue_budget_live_payload_runtime_present"] is True
    assert (
        full_fetch["stream_queue_budget_live_payload_runtime_status"]
        == (
            "blocked_by_live_payload_stage:"
            "blocked_by_queue_budget_runtime_envelope:"
            "model_queue_budget_satisfied_runtime_disabled"
        )
    )
    assert (
        full_fetch["stream_queue_budget_live_payload_runtime_execution_mode"]
        == "payloadless_live_payload_runtime_disabled_canary"
    )
    assert full_fetch["stream_queue_budget_live_payload_runtime_payload_bytes"] == 0
    assert (
        full_fetch["stream_queue_budget_live_payload_runtime_payload_deref_allowed"]
        is False
    )
    assert (
        full_fetch[
            "stream_queue_budget_live_payload_runtime_payload_deref_runtime_allowed"
        ]
        is False
    )
    assert (
        full_fetch["stream_queue_budget_live_payload_runtime_kernel_arg_pass_allowed"]
        is False
    )
    assert full_fetch["stream_queue_budget_manager_artifact_present"] is True
    assert (
        full_fetch["stream_queue_budget_manager_artifact_status"]
        == (
            "blocked_by_live_payload_runtime:"
            "blocked_by_live_payload_stage:"
            "blocked_by_queue_budget_runtime_envelope:"
            "model_queue_budget_satisfied_runtime_disabled"
        )
    )
    assert (
        full_fetch["stream_queue_budget_manager_artifact_manager_backend"]
        == "ReadyTimeExpertCacheManager"
    )
    assert (
        full_fetch["stream_queue_budget_manager_artifact_manager_contract"]
        == "event_driven_queue_budget_cache_manager_v1"
    )
    assert full_fetch["stream_queue_budget_manager_artifact_capacity_entries"] == 4096
    assert full_fetch["stream_queue_budget_manager_artifact_payload_bytes"] == 0
    assert (
        full_fetch["stream_queue_budget_manager_artifact_payload_deref_allowed"]
        is False
    )
    assert (
        full_fetch["stream_queue_budget_manager_artifact_kernel_arg_pass_allowed"]
        is False
    )
    assert full_fetch["stream_queue_budget_manager_runtime_skeleton_present"] is True
    assert (
        full_fetch["stream_queue_budget_manager_runtime_skeleton_status"]
        == (
            "blocked_by_manager_artifact:"
            "blocked_by_live_payload_runtime:"
            "blocked_by_live_payload_stage:"
            "blocked_by_queue_budget_runtime_envelope:"
            "model_queue_budget_satisfied_runtime_disabled"
        )
    )
    assert (
        full_fetch[
            "stream_queue_budget_manager_runtime_skeleton_manager_runtime_contract"
        ]
        == "ready_time_issue_demand_skeleton_v1"
    )
    assert (
        full_fetch["stream_queue_budget_manager_runtime_skeleton_manager_runtime_mode"]
        == "ready_time_payload_cache_skeleton"
    )
    assert full_fetch["stream_queue_budget_manager_runtime_skeleton_capacity_entries"] == 4096
    assert (
        full_fetch["stream_queue_budget_manager_runtime_skeleton_runtime_instantiated"]
        is False
    )
    assert full_fetch["stream_queue_budget_manager_runtime_skeleton_payload_bytes"] == 0
    assert (
        full_fetch["stream_queue_budget_manager_runtime_skeleton_payload_deref_allowed"]
        is False
    )
    assert (
        full_fetch[
            "stream_queue_budget_manager_runtime_skeleton_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        full_fetch["stream_queue_budget_manager_runtime_skeleton_measures_tpot"]
        is False
    )
    assert full_fetch["stream_queue_budget_payload_bytes"] == 0
    assert full_fetch["stream_queue_budget_issued_payload_count"] == 0
    assert full_fetch["stream_queue_budget_live_payload_runtime_enabled"] is False
    assert full_fetch["stream_queue_budget_payload_transfer_enabled"] is False
    assert full_fetch["stream_queue_budget_payload_transfer_runtime_enabled"] is False
    assert full_fetch["stream_queue_budget_payload_deref_allowed"] is False
    assert full_fetch["stream_queue_budget_payload_deref_runtime_allowed"] is False
    assert full_fetch["stream_queue_budget_full_fetch_allowed"] is False
    assert full_fetch["stream_queue_budget_full_fetch_runtime_allowed"] is False
    assert full_fetch["stream_queue_budget_ready_before_demand_credit"] is False
    assert full_fetch["stream_queue_budget_real_ready_credit_granted"] is False
    assert full_fetch["stream_queue_budget_kernel_arg_pass_allowed"] is False
    assert full_fetch["stream_queue_budget_passed_to_kernel"] is False
    assert full_fetch["stream_queue_budget_changes_kernel_launch_args"] is False
    assert full_fetch["stream_queue_budget_uses_current_wna16_args"] is False
    assert full_fetch["stream_queue_budget_passes_current_wna16_args"] is False
    assert full_fetch["stream_queue_budget_measures_tpot"] is False
    assert full_fetch["stream_queue_budget_measures_vllm_latency"] is False
    assert full_fetch["stream_queue_budget_live_runtime_instantiated"] is False


def test_prefetch_lab_default_gate_rejects_queue_budget_first_cell_mismatch(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_path = Path(payload["full_fetch"]["stream_queue_budget_report"])
    stream = json.loads(stream_path.read_text(encoding="utf-8"))
    stream["cells"][0]["first_model_passing_issue_lead_tokens"] = 48
    stream_path.write_text(json.dumps(stream), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert (
        "full_fetch:stream_queue_budget_first_cell_issue_lead_tokens_mismatch"
        in result["failures"]
    )
    assert (
        "full_fetch:stream_queue_budget_runtime_envelope_skipped_due_to_failures"
        in result["failures"]
    )
    full_fetch = result["sections"]["full_fetch"]
    assert full_fetch["stream_queue_budget_runtime_envelope_present"] is None
    assert full_fetch["stream_queue_budget_live_payload_stage_present"] is None
    assert full_fetch["stream_queue_budget_live_payload_runtime_present"] is None


def test_prefetch_lab_default_gate_accepts_queue_budget_early_first_lead(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_path = Path(payload["full_fetch"]["stream_queue_budget_report"])
    stream = json.loads(stream_path.read_text(encoding="utf-8"))
    shifted_issue = {
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_lead_tokens": 8,
        "shifted_issue_clamped_issue_count": 0,
        "shifted_issue_duplicate_issue_key_count": 0,
        "shifted_issue_unique_issue_key_count": 28,
        "shifted_issue_accounted_packet_count": 28,
        "shifted_issue_invalid_export_count": 0,
        "shifted_issue_row_shift_mismatch_count": 0,
        "shifted_issue_row_clamp_mismatch_count": 0,
    }
    stream["first_model_passing_cell"]["issue_lead_tokens"] = 8
    stream["first_model_passing_cell"]["lookahead_us"] = 600000.0
    stream["first_model_passing_cell"]["shifted_issue_accounting"] = shifted_issue
    stream["cells"][0]["first_model_passing_issue_lead_tokens"] = 8
    stream["cells"][0]["first_model_passing_lookahead_us"] = 600000.0
    stream["cells"][0]["first_model_passing_shifted_issue_accounting"] = shifted_issue
    stream_path.write_text(json.dumps(stream), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is True
    full_fetch = result["sections"]["full_fetch"]
    assert full_fetch["stream_shifted_issue_replay_contract_required_lead_tokens"] == 32
    assert full_fetch["stream_queue_budget_first_model_passing_issue_lead_tokens"] == 8
    assert (
        full_fetch["stream_queue_budget_first_shifted_issue_accounted_packet_count"]
        == 28
    )
    prefix = "stream_queue_budget_live_runtime_adapter_payload_issue_request_blocked_canary"
    assert full_fetch[f"{prefix}_request_source"] == "queue_budget_first_model_passing_cell"
    assert full_fetch[f"{prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{prefix}_payload_transfer_runtime_enabled"] is False
    plan_prefix = "stream_queue_budget_live_runtime_adapter_payload_issue_plan_dry_run"
    assert full_fetch[f"{plan_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{plan_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{plan_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{plan_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{plan_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{plan_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{plan_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{plan_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{plan_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{plan_prefix}_payload_transfer_runtime_enabled"] is False
    assert full_fetch[f"{plan_prefix}_kernel_arg_pass_allowed"] is False
    assert full_fetch[f"{plan_prefix}_passed_to_kernel"] is False
    executor_prefix = (
        "stream_queue_budget_live_runtime_adapter_payload_issue_executor_dry_run"
    )
    assert full_fetch[f"{executor_prefix}_request_source"] == (
        "queue_budget_first_model_passing_cell"
    )
    assert full_fetch[f"{executor_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{executor_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{executor_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{executor_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{executor_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{executor_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{executor_prefix}_scheduled_issue_count"] == 0
    assert full_fetch[f"{executor_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{executor_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{executor_prefix}_payload_transfer_runtime_enabled"] is False
    assert full_fetch[f"{executor_prefix}_kernel_arg_pass_allowed"] is False
    assert full_fetch[f"{executor_prefix}_passed_to_kernel"] is False
    queue_entry_prefix = (
        "stream_queue_budget_live_runtime_adapter_payload_issue_queue_entry_dry_run"
    )
    assert full_fetch[f"{queue_entry_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{queue_entry_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{queue_entry_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{queue_entry_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{queue_entry_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{queue_entry_prefix}_queued_issue_count"] == 0
    assert full_fetch[f"{queue_entry_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{queue_entry_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{queue_entry_prefix}_queue_entry_enqueued"] is False
    assert full_fetch[f"{queue_entry_prefix}_queue_submit_allowed"] is False
    queue_submit_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_queue_submit_blocked_canary"
    )
    assert full_fetch[f"{queue_submit_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{queue_submit_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{queue_submit_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{queue_submit_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{queue_submit_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{queue_submit_prefix}_planned_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_scheduled_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_queued_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_submitted_issue_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{queue_submit_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{queue_submit_prefix}_queue_submit_checked"] is True
    assert full_fetch[f"{queue_submit_prefix}_queue_submit_rejected"] is True
    assert full_fetch[f"{queue_submit_prefix}_queue_submit_allowed"] is False
    assert full_fetch[f"{queue_submit_prefix}_queue_entry_enqueued"] is False
    inflight_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_inflight_admission_blocked_canary"
    )
    assert full_fetch[f"{inflight_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{inflight_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{inflight_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{inflight_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{inflight_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{inflight_prefix}_submitted_issue_count"] == 0
    assert full_fetch[f"{inflight_prefix}_inflight_issue_count"] == 0
    assert full_fetch[f"{inflight_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{inflight_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{inflight_prefix}_inflight_admission_checked"] is True
    assert full_fetch[f"{inflight_prefix}_inflight_admission_rejected"] is True
    assert full_fetch[f"{inflight_prefix}_inflight_admission_allowed"] is False
    assert full_fetch[f"{inflight_prefix}_inflight_queue_enqueued"] is False
    dispatch_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_scheduler_dispatch_blocked_canary"
    )
    assert full_fetch[f"{dispatch_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{dispatch_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{dispatch_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{dispatch_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{dispatch_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{dispatch_prefix}_submitted_issue_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_inflight_issue_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_dispatched_issue_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_checked"] is True
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_rejected"] is True
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_allowed"] is False
    assert full_fetch[f"{dispatch_prefix}_scheduler_dispatch_enqueued"] is False
    packet_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_command_packet_dry_run"
    )
    assert full_fetch[f"{packet_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{packet_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{packet_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{packet_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{packet_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{packet_prefix}_dispatched_issue_count"] == 0
    assert full_fetch[f"{packet_prefix}_command_packet_count"] == 0
    assert full_fetch[f"{packet_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{packet_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{packet_prefix}_command_packet_shape_checked"] is True
    assert full_fetch[f"{packet_prefix}_command_packet_submitted"] is False
    assert full_fetch[f"{packet_prefix}_command_packet_executed"] is False
    transport_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_transport_enqueue_blocked_canary"
    )
    assert full_fetch[f"{transport_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{transport_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{transport_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{transport_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{transport_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{transport_prefix}_command_packet_count"] == 0
    assert full_fetch[f"{transport_prefix}_transport_work_count"] == 0
    assert full_fetch[f"{transport_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{transport_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{transport_prefix}_transport_enqueue_checked"] is True
    assert full_fetch[f"{transport_prefix}_transport_enqueue_rejected"] is True
    assert full_fetch[f"{transport_prefix}_transport_enqueue_allowed"] is False
    assert full_fetch[f"{transport_prefix}_transport_work_enqueued"] is False
    worker_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_transport_worker_dispatch_blocked_canary"
    )
    assert full_fetch[f"{worker_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{worker_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{worker_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{worker_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{worker_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{worker_prefix}_transport_work_count"] == 0
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_count"] == 0
    assert full_fetch[f"{worker_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{worker_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_checked"] is True
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_rejected"] is True
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatch_allowed"] is False
    assert full_fetch[f"{worker_prefix}_transport_worker_dispatched"] is False
    descriptor_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_dry_run"
    )
    assert full_fetch[f"{descriptor_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{descriptor_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{descriptor_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{descriptor_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{descriptor_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{descriptor_prefix}_transport_work_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_transport_worker_dispatch_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{descriptor_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_shape_checked"] is True
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{descriptor_prefix}_copy_descriptor_executed"] is False
    submit_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_submit_blocked_canary"
    )
    assert full_fetch[f"{submit_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{submit_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{submit_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{submit_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{submit_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{submit_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{submit_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{submit_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submit_checked"] is True
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submit_rejected"] is True
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submit_allowed"] is False
    assert full_fetch[f"{submit_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{submit_prefix}_copy_descriptor_executed"] is False
    dispatch_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_dispatch_blocked_canary"
    )
    assert full_fetch[f"{dispatch_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{dispatch_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{dispatch_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{dispatch_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{dispatch_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{dispatch_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatch_checked"] is True
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatch_rejected"] is True
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatch_allowed"] is False
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_dispatched"] is False
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{dispatch_prefix}_copy_descriptor_executed"] is False
    execute_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_descriptor_execution_blocked_canary"
    )
    assert full_fetch[f"{execute_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{execute_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{execute_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{execute_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{execute_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{execute_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{execute_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{execute_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{execute_prefix}_copy_descriptor_execution_checked"] is True
    assert full_fetch[f"{execute_prefix}_copy_descriptor_execution_rejected"] is True
    assert full_fetch[f"{execute_prefix}_copy_descriptor_execution_allowed"] is False
    assert full_fetch[f"{execute_prefix}_copy_descriptor_dispatched"] is False
    assert full_fetch[f"{execute_prefix}_copy_descriptor_submitted"] is False
    assert full_fetch[f"{execute_prefix}_copy_descriptor_executed"] is False
    completion_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_copy_completion_blocked_canary"
    )
    assert full_fetch[f"{completion_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{completion_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{completion_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{completion_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{completion_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{completion_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{completion_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{completion_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{completion_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{completion_prefix}_copy_completion_checked"] is True
    assert full_fetch[f"{completion_prefix}_copy_completion_rejected"] is True
    assert full_fetch[f"{completion_prefix}_copy_completion_allowed"] is False
    assert full_fetch[f"{completion_prefix}_copy_completed"] is False
    assert full_fetch[f"{completion_prefix}_ready_credit"] is False
    assert full_fetch[f"{completion_prefix}_real_ready_credit_granted"] is False
    ready_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_ready_credit_blocked_canary"
    )
    assert full_fetch[f"{ready_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{ready_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{ready_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{ready_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{ready_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{ready_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{ready_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{ready_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{ready_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{ready_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{ready_prefix}_ready_credit_checked"] is True
    assert full_fetch[f"{ready_prefix}_ready_credit_rejected"] is True
    assert full_fetch[f"{ready_prefix}_ready_credit_allowed"] is False
    assert full_fetch[f"{ready_prefix}_ready_credit_granted"] is False
    assert full_fetch[f"{ready_prefix}_ready_before_demand_credit_granted"] is False
    assert full_fetch[f"{ready_prefix}_real_payload_ready"] is False
    assert full_fetch[f"{ready_prefix}_ready_credit"] is False
    assert full_fetch[f"{ready_prefix}_real_ready_credit_granted"] is False
    residency_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_residency_update_blocked_canary"
    )
    assert full_fetch[f"{residency_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{residency_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{residency_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{residency_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{residency_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{residency_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{residency_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{residency_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{residency_prefix}_residency_update_count"] == 0
    assert full_fetch[f"{residency_prefix}_resident_payload_count"] == 0
    assert full_fetch[f"{residency_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{residency_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{residency_prefix}_resident_payload_bytes"] == 0
    assert full_fetch[f"{residency_prefix}_residency_update_checked"] is True
    assert full_fetch[f"{residency_prefix}_residency_update_rejected"] is True
    assert full_fetch[f"{residency_prefix}_residency_update_allowed"] is False
    assert full_fetch[f"{residency_prefix}_residency_updated"] is False
    assert full_fetch[f"{residency_prefix}_payload_marked_resident"] is False
    assert full_fetch[f"{residency_prefix}_resident_payload_ready"] is False
    assert full_fetch[f"{residency_prefix}_ready_credit"] is False
    assert full_fetch[f"{residency_prefix}_real_ready_credit_granted"] is False
    deref_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_payload_deref_blocked_canary"
    )
    assert full_fetch[f"{deref_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{deref_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{deref_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{deref_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{deref_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{deref_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{deref_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{deref_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{deref_prefix}_residency_update_count"] == 0
    assert full_fetch[f"{deref_prefix}_resident_payload_count"] == 0
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_count"] == 0
    assert full_fetch[f"{deref_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{deref_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{deref_prefix}_resident_payload_bytes"] == 0
    assert full_fetch[f"{deref_prefix}_dereferenced_payload_bytes"] == 0
    assert full_fetch[f"{deref_prefix}_payload_deref_checked"] is True
    assert full_fetch[f"{deref_prefix}_payload_deref_rejected"] is True
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_checked"] is True
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_rejected"] is True
    assert full_fetch[f"{deref_prefix}_payload_deref_allowed_for_resident_payload"] is False
    assert full_fetch[f"{deref_prefix}_payload_deref_attempted"] is False
    assert full_fetch[f"{deref_prefix}_payload_handle_deref_attempted"] is False
    assert full_fetch[f"{deref_prefix}_payload_marked_resident"] is False
    assert full_fetch[f"{deref_prefix}_resident_payload_ready"] is False
    assert full_fetch[f"{deref_prefix}_payload_deref_allowed"] is False
    assert full_fetch[f"{deref_prefix}_payload_deref_runtime_allowed"] is False
    assert full_fetch[f"{deref_prefix}_ready_credit"] is False
    assert full_fetch[f"{deref_prefix}_real_ready_credit_granted"] is False
    demand_hit_prefix = (
        "stream_queue_budget_live_runtime_adapter_"
        "payload_issue_demand_hit_publication_blocked_canary"
    )
    assert full_fetch[f"{demand_hit_prefix}_source_issue_packet_count"] == 28
    assert full_fetch[f"{demand_hit_prefix}_source_issue_unique_key_count"] == 28
    assert full_fetch[f"{demand_hit_prefix}_source_queue_budget_capacity"] == 4096
    assert full_fetch[f"{demand_hit_prefix}_source_issue_lead_tokens"] == 8
    assert full_fetch[f"{demand_hit_prefix}_source_queue_deadline_us"] == 100.0
    assert full_fetch[f"{demand_hit_prefix}_copy_descriptor_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_copy_completion_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_ready_credit_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_residency_update_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_resident_payload_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_payload_handle_deref_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_consumer_visible_payload_hit_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_issued_payload_count"] == 0
    assert full_fetch[f"{demand_hit_prefix}_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_resident_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_dereferenced_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_payload_bytes"] == 0
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_checked"] is True
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_rejected"] is True
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_publication_allowed"] is False
    assert full_fetch[f"{demand_hit_prefix}_demand_hit_published"] is False
    assert full_fetch[f"{demand_hit_prefix}_consumer_visible_payload_hit"] is False
    assert full_fetch[f"{demand_hit_prefix}_prefetched_demand_hit"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_deref_attempted"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_handle_deref_attempted"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_marked_resident"] is False
    assert full_fetch[f"{demand_hit_prefix}_resident_payload_ready"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_deref_allowed"] is False
    assert full_fetch[f"{demand_hit_prefix}_payload_deref_runtime_allowed"] is False
    assert full_fetch[f"{demand_hit_prefix}_ready_credit"] is False
    assert full_fetch[f"{demand_hit_prefix}_real_ready_credit_granted"] is False


def test_prefetch_lab_default_gate_rejects_queue_budget_string_cell_index(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_path = Path(payload["full_fetch"]["stream_queue_budget_report"])
    stream = json.loads(stream_path.read_text(encoding="utf-8"))
    stream["first_model_passing_cell"]["cell_index"] = "0"
    stream_path.write_text(json.dumps(stream), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_queue_budget_first_cell_index_missing" in result[
        "failures"
    ]


def test_prefetch_lab_default_gate_rechecks_direct_snapshot_report(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    direct_path = Path(payload["full_fetch"]["ready_time_direct_snapshot_report"])
    direct = json.loads(direct_path.read_text(encoding="utf-8"))
    direct["metrics"]["direct_snapshot_payload_bytes"] = False
    direct_path.write_text(json.dumps(direct), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert (
        "full_fetch:ready_time_direct_snapshot_report_recheck_failed"
        in result["failures"]
    )
    full_fetch = result["sections"]["full_fetch"]
    assert full_fetch["ready_time_direct_snapshot_report_recheck_passed"] is False
    assert (
        "direct_snapshot_runtime_shadow_premap_payload_cache_direct_payload_bytes_mismatch"
        in full_fetch["ready_time_direct_snapshot_report_recheck_failures"]
    )
    assert full_fetch["stream_shifted_issue_replay_source_full_fetch_runtime_allowed"] is False
    assert full_fetch["stream_shifted_issue_replay_kernel_arg_pass_allowed"] is False
    assert full_fetch["stream_shifted_issue_replay_source_kernel_arg_pass_allowed"] is False
    assert full_fetch["stream_shifted_issue_replay_source_uses_current_wna16_args"] is False
    assert full_fetch["stream_shifted_issue_replay_source_current_wna16_arg_compatible"] is False
    assert full_fetch["stream_shifted_issue_replay_source_requires_wna16_arg_reinterpretation"] is False
    assert full_fetch["stream_shifted_issue_replay_source_wna16_benchmark_ready"] is False
    assert full_fetch["stream_shifted_issue_replay_source_measures_tpot"] is False


def test_prefetch_lab_default_gate_rejects_full_fetch_allow_report(tmp_path: Path):
    result = check_prefetch_lab_default_gate(
        _write_fixture(tmp_path, allow_full_fetch=True),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_allows_full_fetch" in result["failures"]


def test_prefetch_lab_default_gate_rejects_missing_stream_reports(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["full_fetch"].pop("stream_decision_gate_report")
    payload["full_fetch"].pop("stream_earlier_issue_feasibility_report")
    payload["full_fetch"].pop("stream_earlier_issue_lead_token_sweep_report")
    payload["full_fetch"].pop("stream_shifted_issue_replay_contract_report")
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_report_missing" in result["failures"]
    assert "full_fetch:stream_feasibility_report_missing" in result["failures"]
    assert "full_fetch:stream_lead_token_sweep_report_missing" in result["failures"]
    assert (
        "full_fetch:stream_shifted_issue_replay_contract_report_missing"
        in result["failures"]
    )
    full_fetch = result["sections"]["full_fetch"]
    assert full_fetch["stream_required_shifted_issue_accounting_enabled"] is None
    assert full_fetch["stream_required_shifted_issue_lead_tokens"] is None
    assert full_fetch["stream_required_shifted_issue_clamped_issue_count"] is None
    assert (
        full_fetch["stream_required_shifted_issue_duplicate_issue_key_count"]
        is None
    )
    assert full_fetch["stream_required_shifted_issue_unique_issue_key_count"] is None
    assert (
        full_fetch["stream_required_shifted_issue_accounted_packet_count"]
        is None
    )
    assert full_fetch["stream_required_shifted_issue_invalid_export_count"] is None
    assert (
        full_fetch["stream_required_shifted_issue_row_shift_mismatch_count"]
        is None
    )
    assert (
        full_fetch["stream_required_shifted_issue_row_clamp_mismatch_count"]
        is None
    )


def test_prefetch_lab_default_gate_accepts_full_fetch_decision_gate(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_ready_time_and_lookahead",
                "current_deadline_us": 200.0,
                "current_lookahead_us": 0.0,
                "first_model_passing_deadline_us": 4000.0,
                "first_model_passing_lookahead_us": 3800.0,
                "required_lookahead_slack_us": 4000.0,
                "required_issue_to_demand_lookahead_us": 3800.0,
                "slack_deficit_us": 3800.0,
                "lookahead_deficit_us": 3800.0,
                "ready_time_model_slack_satisfied": False,
                "ready_time_model_lookahead_satisfied": False,
                "ready_time_any_model_route_satisfied": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)
    full_fetch = result["sections"]["full_fetch"]

    assert result["passed"] is True
    assert full_fetch["ready_time_allow_full_fetch"] is False
    assert (
        full_fetch["ready_time_decision_reason"]
        == "insufficient_ready_time_and_lookahead"
    )
    assert full_fetch["ready_time_current_deadline_us"] == 200.0
    assert full_fetch["ready_time_current_lookahead_us"] == 0.0
    assert full_fetch["ready_time_first_model_passing_deadline_us"] == 4000.0
    assert full_fetch["ready_time_first_model_passing_lookahead_us"] == 3800.0
    assert full_fetch["ready_time_required_lookahead_slack_us"] == 4000.0
    assert (
        full_fetch["ready_time_required_issue_to_demand_lookahead_us"] == 3800.0
    )
    assert full_fetch["ready_time_slack_deficit_us"] == 3800.0
    assert full_fetch["ready_time_lookahead_deficit_us"] == 3800.0
    assert full_fetch["ready_time_model_slack_satisfied"] is False
    assert full_fetch["ready_time_model_lookahead_satisfied"] is False
    assert full_fetch["ready_time_any_model_route_satisfied"] is False


def test_prefetch_lab_default_gate_accepts_stream_full_fetch_block_evidence(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))

    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_stream_lookahead",
                "current_lookahead_us": 0.0,
                "required_stream_lookahead_us": 2400000.0,
                "lookahead_deficit_us": 2400000.0,
                "first_model_passing_lookahead_us": 2400000.0,
                "required_shifted_issue_accounting": {
                    "shifted_issue_accounting_enabled": True,
                    "shifted_issue_lead_tokens": 32,
                    "shifted_issue_clamped_issue_count": 12,
                    "shifted_issue_duplicate_issue_key_count": 12,
                    "shifted_issue_unique_issue_key_count": 16,
                    "shifted_issue_accounted_packet_count": 28,
                    "shifted_issue_invalid_export_count": 0,
                    "shifted_issue_row_shift_mismatch_count": 0,
                    "shifted_issue_row_clamp_mismatch_count": 0,
                },
                "metadata_premap_runtime_preferred": True,
                "descriptor_prep_runtime_preferred": True,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_feasibility = tmp_path / "stream_feasibility.json"
    stream_feasibility.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_feasibility",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "current_runtime_satisfies_model": False,
                "feasible_within_configured_token_window": True,
                "min_required_lead_tokens": 24,
                "max_required_lead_tokens": 48,
                "min_deficit_lead_tokens": 24,
                "max_deficit_lead_tokens": 48,
                "max_candidate_lead_tokens": 64,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_lead = tmp_path / "stream_lead.json"
    stream_lead.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_lead_token_sweep",
                "passed": True,
                "full_fetch_allowed": False,
                "full_fetch_runtime_allowed": False,
                "event_timing_mode": "token_index",
                "token_timing_enabled": True,
                "decode_token_us": 75000.0,
                "first_model_passing_lead_tokens": 32,
                "first_model_passing_lookahead_us": 2400000.0,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"].update(
        {
            "stream_decision_gate_report": str(stream_decision),
            "stream_earlier_issue_feasibility_report": str(stream_feasibility),
            "stream_earlier_issue_lead_token_sweep_report": str(stream_lead),
        }
    )
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)
    full_fetch = result["sections"]["full_fetch"]

    assert result["passed"] is True
    assert full_fetch["stream_decision_gate_present"] is True
    assert full_fetch["stream_decision_gate_passed"] is True
    assert full_fetch["stream_full_fetch_runtime_allowed"] is False
    assert full_fetch["stream_decision"] == (
        "block_full_fetch_insufficient_stream_lookahead"
    )
    assert full_fetch["stream_required_lookahead_us"] == 2400000.0
    assert full_fetch["stream_feasibility_passed"] is True
    assert full_fetch["stream_current_runtime_satisfies_model"] is False
    assert full_fetch["stream_max_required_lead_tokens"] == 48
    assert full_fetch["stream_lead_token_sweep_passed"] is True
    assert full_fetch["stream_lead_token_sweep_event_timing_mode"] == "token_index"
    assert full_fetch["stream_lead_token_sweep_token_timing_enabled"] is True
    assert full_fetch["stream_first_model_passing_lead_tokens"] == 32
    assert full_fetch["stream_required_shifted_issue_accounting_enabled"] is True
    assert full_fetch["stream_required_shifted_issue_lead_tokens"] == 32
    assert full_fetch["stream_required_shifted_issue_clamped_issue_count"] == 12
    assert full_fetch["stream_required_shifted_issue_duplicate_issue_key_count"] == 12
    assert full_fetch["stream_required_shifted_issue_unique_issue_key_count"] == 16
    assert full_fetch["stream_required_shifted_issue_accounted_packet_count"] == 28
    assert full_fetch["stream_required_shifted_issue_invalid_export_count"] == 0
    assert full_fetch["stream_required_shifted_issue_row_shift_mismatch_count"] == 0
    assert full_fetch["stream_required_shifted_issue_row_clamp_mismatch_count"] == 0


def test_prefetch_lab_default_gate_rejects_missing_required_shifted_issue(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert (
        "full_fetch:stream_decision_gate_required_shifted_issue_missing"
        in result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_wrong_required_shifted_issue(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                "required_shifted_issue_accounting": {
                    "shifted_issue_accounting_enabled": True,
                    "shifted_issue_lead_tokens": 16,
                    "shifted_issue_clamped_issue_count": 12,
                    "shifted_issue_duplicate_issue_key_count": 12,
                    "shifted_issue_unique_issue_key_count": 16,
                    "shifted_issue_accounted_packet_count": 28,
                    "shifted_issue_invalid_export_count": 1,
                    "shifted_issue_row_shift_mismatch_count": 0,
                    "shifted_issue_row_clamp_mismatch_count": 0,
                },
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert (
        "full_fetch:stream_decision_gate_required_shifted_issue_shifted_issue_lead_tokens_mismatch"
        in result["failures"]
    )
    assert (
        "full_fetch:stream_decision_gate_required_shifted_issue_shifted_issue_invalid_export_count_mismatch"
        in result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_unsafe_stream_evidence(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = Path(payload["full_fetch"]["stream_decision_gate_report"])
    stream_payload = json.loads(stream_decision.read_text(encoding="utf-8"))
    stream_payload["full_fetch_runtime_allowed"] = True
    stream_payload["payload_transfer_enabled"] = True
    stream_decision.write_text(json.dumps(stream_payload), encoding="utf-8")
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_allows_full_fetch" in result["failures"]
    assert "full_fetch:stream_decision_gate_payload_transfer_enabled_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_stream_wna16_arg_usage(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = Path(payload["full_fetch"]["stream_decision_gate_report"])
    stream_payload = json.loads(stream_decision.read_text(encoding="utf-8"))
    stream_payload["uses_current_wna16_args"] = True
    stream_decision.write_text(json.dumps(stream_payload), encoding="utf-8")
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_uses_current_wna16_args_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_stream_current_wna16_pass(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = Path(payload["full_fetch"]["stream_decision_gate_report"])
    stream_payload = json.loads(stream_decision.read_text(encoding="utf-8"))
    stream_payload["passes_current_wna16_args"] = True
    stream_decision.write_text(json.dumps(stream_payload), encoding="utf-8")
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_passes_current_wna16_args_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_stream_current_wna16_compat(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = Path(payload["full_fetch"]["stream_decision_gate_report"])
    stream_payload = json.loads(stream_decision.read_text(encoding="utf-8"))
    stream_payload["current_wna16_arg_compatible"] = True
    stream_decision.write_text(json.dumps(stream_payload), encoding="utf-8")
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert (
        "full_fetch:stream_decision_gate_current_wna16_arg_compatible_not_false"
        in result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_bad_shifted_issue_contract(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_shifted = Path(
        payload["full_fetch"]["stream_shifted_issue_replay_contract_report"]
    )
    shifted_payload = json.loads(stream_shifted.read_text(encoding="utf-8"))
    shifted_payload["rows"][1]["issue_token_index"] = 16
    stream_shifted.write_text(json.dumps(shifted_payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_shifted_issue_replay_contract_not_passed" in (
        result["failures"]
    )
    assert (
        "full_fetch:stream_shifted_issue_replay_contract_row_1_issue_token_shift_mismatch"
        in result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_stream_passed_non_bool(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": "true",
                "full_fetch_runtime_allowed": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_passed_not_bool" in result["failures"]
    assert "full_fetch:stream_decision_gate_not_passed" in result["failures"]


def test_prefetch_lab_default_gate_rejects_malformed_full_fetch_decision_gate(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "wrong_kind",
                "passed": True,
                "full_fetch_runtime_allowed": True,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_artifact_kind_mismatch" in result[
        "failures"
    ]


def test_prefetch_lab_default_gate_rejects_decision_gate_missing_runtime_allow(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                key: value
                for key, value in {
                    "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
                    "passed": True,
                    "allow_full_fetch": False,
                    **_FULL_FETCH_DECISION_NOOP_FIELDS,
                }.items()
                if key != "full_fetch_runtime_allowed"
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_missing_full_fetch_runtime_allowed" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_decision_gate_payload_or_kernel_side_effect(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    fields = dict(_FULL_FETCH_DECISION_NOOP_FIELDS)
    fields["payload_transfer_enabled"] = True
    fields["kernel_arg_pass_allowed"] = True
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                **fields,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_payload_transfer_enabled_not_false" in (
        result["failures"]
    )
    assert "full_fetch:ready_time_gate_report_kernel_arg_pass_allowed_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_sanitizes_malformed_ready_time_diagnostics(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": False,
                "decision_reason": "full_fetch_threshold_not_met",
                "threshold_failures": "not-a-list",
                "metrics": {
                    "demand_hit_rate": True,
                    "ready_late_miss_rate": False,
                    "used_per_issued_fetch": "0.0",
                    "issued_fetch_count": True,
                    "used_fetch_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)
    full_fetch = result["sections"]["full_fetch"]

    assert result["passed"] is True
    assert full_fetch["ready_time_threshold_failures"] == []
    assert full_fetch["ready_time_demand_hit_rate"] is None
    assert full_fetch["ready_time_ready_late_miss_rate"] is None
    assert full_fetch["ready_time_used_per_issued_fetch"] == 0.0
    assert full_fetch["ready_time_issued_fetch_count"] is None
    assert full_fetch["ready_time_used_fetch_count"] == 0


def test_prefetch_lab_default_gate_rejects_under_capacity_premap(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    capacity = Path(payload["premap"]["capacity_gate"])
    capacity.write_text(
        yaml.safe_dump(
            {
                "capacity_gate": {
                    "recommended_capacity_entries": 8192,
                    "no_eviction_capacity_entries": 12288,
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "premap:recommended_capacity_below_min:8192" in result["failures"]
    assert "premap:no_eviction_capacity_above_recommended:12288>8192" in result[
        "failures"
    ]


def test_prefetch_lab_default_gate_rejects_metadata_default_enabled(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["metadata"]["default_enabled"] = True
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "metadata:metadata_default_enabled" in result["failures"]


def test_prefetch_lab_default_gate_reports_missing_capacity_gate(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["premap"]["capacity_gate"] = str(tmp_path / "missing.yaml")
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "premap:capacity_gate_load_failed:FileNotFoundError" in result["failures"]


def test_prefetch_lab_default_gate_cli_writes_report(tmp_path: Path):
    config = _write_fixture(tmp_path)
    output = tmp_path / "report.json"

    exit_code = main([str(config), "--root", str(tmp_path), "--output-json", str(output)])

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True
