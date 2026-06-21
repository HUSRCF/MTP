from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_payload_cache_ready_time_gate import (
    _DIRECT_RUNTIME_EXECUTION_RAW_FIELDS,
    check_summary,
    main,
)


def _summary(tmp_path: Path, **overrides):
    measured = tmp_path / "copy.json"
    measured.write_text('{"rows": []}\n', encoding="utf-8")
    values = {
        "runtime_shadow_premap_payload_cache_manager_mode": "ready_time",
        "runtime_shadow_premap_payload_cache_manager_measured_copy_path": str(measured),
        "runtime_shadow_premap_payload_cache_manager_measured_copy_us_per_issue": 100.0,
        "runtime_shadow_premap_payload_cache_manager_measured_copy_effective_gbps": 1.0,
        "runtime_shadow_premap_payload_cache_manager_queue_batch_size": 8,
        "runtime_shadow_premap_payload_cache_manager_queue_deadline_us": 1000.0,
        "runtime_shadow_aggregate_premap_payload_cache_manager_count": 10,
        "runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count": 8,
        "runtime_shadow_aggregate_premap_payload_cache_used_fetch_count": 0,
        "runtime_shadow_aggregate_premap_payload_cache_demand_count": 100,
        "runtime_shadow_aggregate_premap_payload_cache_demand_hit_count": 0,
        "runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count": 90,
    }
    values.update(overrides)
    return values


def _direct_snapshot_boundary(**overrides):
    direct_issue_sources = overrides.get(
        "runtime_shadow_premap_payload_cache_direct_issue_sources",
        ["previous_token_transition_premap_shadow"],
    )
    participation_issue_sources = overrides.get(
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_issue_sources",
        direct_issue_sources,
    )
    values = {
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
        "runtime_shadow_premap_payload_cache_direct_issue_sources": direct_issue_sources,
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_present": True,
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_stage": (
            "online_ready_time_payload_cache_runtime_participation_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_status": (
            "ready_time_candidate_requires_lab_gate"
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
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_issue_sources": (
            participation_issue_sources
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_participation_candidate_reason": (
            "candidate_requires_ready_time_gate"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_present": True,
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_stage": (
            "payload_cache_runtime_plan_lab_gate_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_status": (
            "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_consumes_participation": (
            True
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_participation_status": (
            "ready_time_candidate_requires_lab_gate"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_live_payload_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_plan_planned_issue_count": (
            0
        ),
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
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_present": True,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_stage": (
            "payload_cache_runtime_execution_lab_gate_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_status": (
            "blocked_by_runtime_plan:"
            "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_consumes_plan": (
            True
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_plan_status": (
            "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_decision": (
            "blocked"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason": (
            "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode": (
            "payloadless_lab_gate_dry_run"
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_live_payload_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_runtime_enabled": (
            False
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count": (
            0
        ),
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes": 0,
        "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit": (
            False
        ),
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
    values.update(overrides)
    return values


def _direct_snapshot_summary(tmp_path: Path, **overrides):
    values = _summary(
        tmp_path,
        runtime_shadow_aggregate_premap_payload_cache_manager_count=None,
        runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=None,
        runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=None,
        runtime_shadow_aggregate_premap_payload_cache_demand_count=None,
        runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=None,
        runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=None,
        runtime_shadow_premap_payload_cache_direct_snapshot_present=True,
        runtime_shadow_premap_payload_cache_direct_manager_mode="ready_time",
        runtime_shadow_premap_payload_cache_direct_demand_count=100,
        runtime_shadow_premap_payload_cache_direct_demand_hit_count=25,
        runtime_shadow_premap_payload_cache_direct_ready_late_miss_count=30,
        runtime_shadow_premap_payload_cache_direct_issued_fetch_count=8,
        runtime_shadow_premap_payload_cache_direct_used_fetch_count=2,
        runtime_shadow_premap_payload_cache_direct_queue_batch_size=8,
        runtime_shadow_premap_payload_cache_direct_queue_deadline_us=1000.0,
        **_direct_snapshot_boundary(),
    )
    values.update(overrides)
    return values


def test_ready_time_payload_cache_gate_blocks_valid_negative_evidence(tmp_path: Path):
    result = check_summary(_summary(tmp_path), root=tmp_path)

    assert result["passed"] is True
    assert result["allow_full_fetch"] is False
    assert result["decision_reason"] == "full_fetch_threshold_not_met"
    assert result["metrics"]["demand_hit_rate"] == 0.0
    assert result["metrics"]["ready_late_miss_rate"] == 0.9


def test_ready_time_payload_cache_gate_allows_ready_hits(tmp_path: Path):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=20,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=20,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=10,
        ),
        root=tmp_path,
        min_demand_hit_rate=0.10,
        max_ready_late_miss_rate=0.20,
    )

    assert result["passed"] is True
    assert result["allow_full_fetch"] is True
    assert result["decision_reason"] == "allow"


def test_ready_time_payload_cache_gate_accepts_metrics_report_input(tmp_path: Path):
    measured = tmp_path / "copy.json"
    measured.write_text('{"rows": []}\n', encoding="utf-8")
    result = check_summary(
        {
            "passed": True,
            "allow_full_fetch": False,
            "metrics": {
                "mode": "ready_time",
                "manager_count": 10,
                "demand_count": 100,
                "demand_hit_count": 0,
                "ready_late_miss_count": 90,
                "issued_fetch_count": 8,
                "used_fetch_count": 0,
                "queue_batch_size": 8,
                "queue_deadline_us": 1000.0,
                "measured_copy_path": str(measured),
                "measured_copy_us_per_issue": 100.0,
                "measured_copy_effective_gbps": 1.0,
            },
        },
        root=tmp_path,
    )

    assert result["passed"] is True
    assert result["allow_full_fetch"] is False
    assert result["metrics"]["demand_count"] == 100
    assert result["metrics"]["measured_copy_us_per_issue"] == 100.0


def test_ready_time_payload_cache_gate_accepts_direct_snapshot_input(tmp_path: Path):
    summary = _direct_snapshot_summary(tmp_path)
    result = check_summary(summary, root=tmp_path)

    assert result["passed"] is True
    assert result["allow_full_fetch"] is False
    assert result["decision_reason"] == "full_fetch_threshold_not_met"
    assert result["metrics"]["manager_count"] == 1
    assert result["metrics"]["demand_count"] == 100
    assert result["metrics"]["demand_hit_count"] == 25
    assert result["metrics"]["ready_late_miss_count"] == 30
    assert result["metrics"]["used_per_issued_fetch"] == 0.25
    assert result["metrics"]["direct_snapshot_issue_sources"] == [
        "previous_token_transition_premap_shadow"
    ]
    assert result["metrics"]["direct_snapshot_runtime_participation_present"] is True
    assert (
        result["metrics"]["direct_snapshot_runtime_participation_stage"]
        == "online_ready_time_payload_cache_runtime_participation_dry_run"
    )
    assert (
        result["metrics"]["direct_snapshot_runtime_participation_status"]
        == "ready_time_candidate_requires_lab_gate"
    )
    assert result["metrics"]["direct_snapshot_runtime_participation_payload_bytes"] == 0
    assert (
        result["metrics"][
            "direct_snapshot_runtime_participation_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert result["metrics"]["direct_snapshot_runtime_participation_issue_sources"] == [
        "previous_token_transition_premap_shadow"
    ]
    assert result["metrics"]["direct_snapshot_runtime_plan_present"] is True
    assert (
        result["metrics"]["direct_snapshot_runtime_plan_status"]
        == "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    assert (
        result["metrics"]["direct_snapshot_runtime_plan_participation_status"]
        == "ready_time_candidate_requires_lab_gate"
    )
    assert result["metrics"]["direct_snapshot_runtime_plan_payload_bytes"] == 0
    assert (
        result["metrics"]["direct_snapshot_runtime_plan_kernel_arg_pass_allowed"]
        is False
    )
    assert result["metrics"]["direct_snapshot_runtime_execution_present"] is True
    assert (
        result["metrics"]["direct_snapshot_runtime_execution_status"]
        == "blocked_by_runtime_plan:"
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    assert (
        result["metrics"]["direct_snapshot_runtime_execution_plan_status"]
        == result["metrics"]["direct_snapshot_runtime_plan_status"]
    )
    assert result["metrics"]["direct_snapshot_runtime_execution_decision"] == "blocked"
    assert (
        result["metrics"]["direct_snapshot_runtime_execution_block_reason"]
        == result["metrics"]["direct_snapshot_runtime_plan_status"]
    )
    assert (
        result["metrics"]["direct_snapshot_runtime_execution_execution_mode"]
        == "payloadless_lab_gate_dry_run"
    )
    assert result["metrics"]["direct_snapshot_runtime_execution_payload_bytes"] == 0
    assert (
        result["metrics"][
            "direct_snapshot_runtime_execution_real_ready_credit_granted"
        ]
        is False
    )
    assert (
        result["metrics"]["direct_snapshot_runtime_execution_kernel_arg_pass_allowed"]
        is False
    )


def test_ready_time_payload_cache_gate_accepts_own_direct_snapshot_report(
    tmp_path: Path,
):
    first = check_summary(_direct_snapshot_summary(tmp_path), root=tmp_path)
    second = check_summary(
        first,
        root=tmp_path,
    )

    assert first["passed"] is True
    assert second["passed"] is True
    assert second["metrics"]["direct_snapshot_payload_bytes"] == 0
    assert second["metrics"]["direct_snapshot_issue_sources"] == [
        "previous_token_transition_premap_shadow"
    ]
    assert (
        second["metrics"]["direct_snapshot_runtime_participation_status"]
        == "ready_time_candidate_requires_lab_gate"
    )
    assert (
        second["metrics"]["direct_snapshot_runtime_participation_issue_sources"]
        == ["previous_token_transition_premap_shadow"]
    )
    assert (
        second["metrics"]["direct_snapshot_runtime_plan_status"]
        == "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )
    assert (
        second["metrics"]["direct_snapshot_runtime_execution_status"]
        == "blocked_by_runtime_plan:"
        "lab_gate_blocked:ready_time_direct_snapshot_disallows_full_fetch"
    )


def test_ready_time_payload_cache_gate_rejects_direct_runtime_plan_status_mismatch(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_direct_runtime_plan_status=(
                "participation_not_full_fetch_candidate:accounting_only_no_used_fetch"
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "direct_runtime_plan_status_mismatch" in result["failures"]


def test_ready_time_payload_cache_gate_rejects_partial_direct_runtime_plan_fields(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_direct_runtime_plan_present=None,
            runtime_shadow_premap_payload_cache_direct_runtime_plan_payload_bytes=123,
            runtime_shadow_premap_payload_cache_direct_runtime_plan_ready_credit=True,
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert (
        "direct_runtime_plan_runtime_shadow_premap_payload_cache_direct_runtime_plan_present_mismatch"
        in result["failures"]
    )
    assert (
        "direct_runtime_plan_runtime_shadow_premap_payload_cache_direct_runtime_plan_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "direct_runtime_plan_runtime_shadow_premap_payload_cache_direct_runtime_plan_ready_credit_mismatch"
        in result["failures"]
    )


def test_ready_time_payload_cache_gate_rejects_direct_runtime_execution_status_mismatch(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_status=(
                "not_blocked"
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "direct_runtime_execution_status_mismatch" in result["failures"]


def test_ready_time_payload_cache_gate_rejects_direct_runtime_execution_envelope_mismatch(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_decision=(
                "execute"
            ),
            runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason=(
                "other"
            ),
            runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode=(
                "live"
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "direct_runtime_execution_decision_mismatch" in result["failures"]
    assert "direct_runtime_execution_block_reason_mismatch" in result["failures"]
    assert "direct_runtime_execution_execution_mode_mismatch" in result["failures"]


def test_ready_time_payload_cache_gate_rejects_direct_runtime_execution_envelope_nulls(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_decision=None,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason=None,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode=None,
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "direct_runtime_execution_decision_mismatch" in result["failures"]
    assert "direct_runtime_execution_block_reason_mismatch" in result["failures"]
    assert "direct_runtime_execution_execution_mode_mismatch" in result["failures"]


def test_ready_time_payload_cache_gate_rejects_null_only_direct_runtime_execution_envelope(
    tmp_path: Path,
):
    values = _direct_snapshot_summary(tmp_path)
    for field in _DIRECT_RUNTIME_EXECUTION_RAW_FIELDS:
        values.pop(field, None)
    values.update(
        {
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_decision": None,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_block_reason": None,
            "runtime_shadow_premap_payload_cache_direct_runtime_execution_execution_mode": None,
        }
    )

    result = check_summary(values, root=tmp_path)

    assert result["passed"] is False
    assert "direct_runtime_execution_status_missing_or_invalid" in result["failures"]
    assert "direct_runtime_execution_plan_status_missing_or_invalid" in result[
        "failures"
    ]
    assert "direct_runtime_execution_decision_mismatch" in result["failures"]
    assert "direct_runtime_execution_block_reason_mismatch" in result["failures"]
    assert "direct_runtime_execution_execution_mode_mismatch" in result["failures"]


def test_ready_time_payload_cache_gate_rejects_partial_direct_runtime_execution_fields(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_present=None,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes=1,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit=True,
            runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted=True,
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert (
        "direct_runtime_execution_runtime_shadow_premap_payload_cache_direct_runtime_execution_present_mismatch"
        in result["failures"]
    )
    assert (
        "direct_runtime_execution_runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "direct_runtime_execution_runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit_mismatch"
        in result["failures"]
    )
    assert (
        "direct_runtime_execution_runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted_mismatch"
        in result["failures"]
    )


def test_ready_time_payload_cache_gate_accepts_prelaunch_observed_issue_source(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            **_direct_snapshot_boundary(
                runtime_shadow_premap_payload_cache_direct_issue_sources=[
                    "prelaunch_observed_transition_premap_shadow"
                ],
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is True
    assert result["metrics"]["direct_snapshot_issue_sources"] == [
        "prelaunch_observed_transition_premap_shadow"
    ]


def test_ready_time_payload_cache_gate_revalidates_direct_snapshot_report(
    tmp_path: Path,
):
    first = check_summary(_direct_snapshot_summary(tmp_path), root=tmp_path)
    first["metrics"]["direct_snapshot_payload_bytes"] = False

    second = check_summary(first, root=tmp_path)

    assert second["passed"] is False
    assert (
        "direct_snapshot_runtime_shadow_premap_payload_cache_direct_payload_bytes_mismatch"
        in second["failures"]
    )


def test_ready_time_payload_cache_gate_rejects_incomplete_direct_snapshot(
    tmp_path: Path,
):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_manager_count=None,
            runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=None,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=None,
            runtime_shadow_premap_payload_cache_direct_snapshot_present=True,
            runtime_shadow_premap_payload_cache_direct_manager_mode="resident",
            runtime_shadow_premap_payload_cache_direct_demand_count=100,
            runtime_shadow_premap_payload_cache_direct_demand_hit_count=25,
            runtime_shadow_premap_payload_cache_direct_issued_fetch_count=8,
            runtime_shadow_premap_payload_cache_direct_used_fetch_count=2,
            runtime_shadow_premap_payload_cache_direct_queue_batch_size=8,
            runtime_shadow_premap_payload_cache_direct_queue_deadline_us=1000.0,
            **_direct_snapshot_boundary(),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert result["allow_full_fetch"] is False
    assert result["decision_reason"] == "invalid_evidence"
    assert "direct_snapshot_mode_not_ready_time:resident" in result["failures"]
    assert (
        "direct_snapshot_field_missing:"
        "runtime_shadow_premap_payload_cache_direct_ready_late_miss_count"
    ) in result["failures"]


def test_ready_time_payload_cache_gate_preserves_explicit_zero_priority(
    tmp_path: Path,
):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=95,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=1,
            runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=8,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=0,
            runtime_shadow_premap_payload_cache_direct_snapshot_present=True,
            runtime_shadow_premap_payload_cache_direct_manager_mode="ready_time",
            runtime_shadow_premap_payload_cache_direct_demand_count=100,
            runtime_shadow_premap_payload_cache_direct_demand_hit_count=95,
            runtime_shadow_premap_payload_cache_direct_ready_late_miss_count=1,
            runtime_shadow_premap_payload_cache_direct_issued_fetch_count=8,
            runtime_shadow_premap_payload_cache_direct_used_fetch_count=8,
            runtime_shadow_premap_payload_cache_direct_queue_batch_size=8,
            runtime_shadow_premap_payload_cache_direct_queue_deadline_us=1000.0,
            **_direct_snapshot_boundary(),
        ),
        root=tmp_path,
    )

    assert result["passed"] is True
    assert result["allow_full_fetch"] is False
    assert result["metrics"]["used_fetch_count"] == 0
    assert result["metrics"]["used_per_issued_fetch"] == 0.0
    assert result["threshold_failures"] == [
        "used_per_issued_fetch_below_threshold"
    ]


def test_ready_time_payload_cache_gate_rejects_direct_snapshot_payload_runtime(
    tmp_path: Path,
):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_manager_count=None,
            runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=None,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=None,
            runtime_shadow_premap_payload_cache_direct_snapshot_present=True,
            runtime_shadow_premap_payload_cache_direct_manager_mode="ready_time",
            runtime_shadow_premap_payload_cache_direct_demand_count=100,
            runtime_shadow_premap_payload_cache_direct_demand_hit_count=25,
            runtime_shadow_premap_payload_cache_direct_ready_late_miss_count=30,
            runtime_shadow_premap_payload_cache_direct_issued_fetch_count=8,
            runtime_shadow_premap_payload_cache_direct_used_fetch_count=2,
            runtime_shadow_premap_payload_cache_direct_queue_batch_size=8,
            runtime_shadow_premap_payload_cache_direct_queue_deadline_us=1000.0,
            **_direct_snapshot_boundary(
                runtime_shadow_premap_payload_cache_direct_payload_bytes=1,
                runtime_shadow_premap_payload_cache_direct_full_fetch_runtime_allowed=True,
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert (
        "direct_snapshot_runtime_shadow_premap_payload_cache_direct_payload_bytes_mismatch"
        in result["failures"]
    )
    assert (
        "direct_snapshot_runtime_shadow_premap_payload_cache_direct_full_fetch_runtime_allowed_mismatch"
        in result["failures"]
    )


def test_ready_time_payload_cache_gate_rejects_bool_payload_bytes(
    tmp_path: Path,
):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_manager_count=None,
            runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=None,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=None,
            runtime_shadow_premap_payload_cache_direct_snapshot_present=True,
            runtime_shadow_premap_payload_cache_direct_manager_mode="ready_time",
            runtime_shadow_premap_payload_cache_direct_demand_count=100,
            runtime_shadow_premap_payload_cache_direct_demand_hit_count=25,
            runtime_shadow_premap_payload_cache_direct_ready_late_miss_count=30,
            runtime_shadow_premap_payload_cache_direct_issued_fetch_count=8,
            runtime_shadow_premap_payload_cache_direct_used_fetch_count=2,
            runtime_shadow_premap_payload_cache_direct_queue_batch_size=8,
            runtime_shadow_premap_payload_cache_direct_queue_deadline_us=1000.0,
            **_direct_snapshot_boundary(
                runtime_shadow_premap_payload_cache_direct_payload_bytes=False,
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert (
        "direct_snapshot_runtime_shadow_premap_payload_cache_direct_payload_bytes_mismatch"
        in result["failures"]
    )


def test_ready_time_payload_cache_gate_rejects_non_ready_time_participation_status(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            **_direct_snapshot_boundary(
                runtime_shadow_premap_payload_cache_direct_runtime_participation_status=(
                    "accounting_only_not_ready_time_manager:resident"
                ),
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "direct_runtime_participation_status_unsupported" in result["failures"]


def test_ready_time_payload_cache_gate_rejects_missing_transition_issue_source(
    tmp_path: Path,
):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_manager_count=None,
            runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_count=None,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=None,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=None,
            runtime_shadow_premap_payload_cache_direct_snapshot_present=True,
            runtime_shadow_premap_payload_cache_direct_manager_mode="ready_time",
            runtime_shadow_premap_payload_cache_direct_demand_count=100,
            runtime_shadow_premap_payload_cache_direct_demand_hit_count=25,
            runtime_shadow_premap_payload_cache_direct_ready_late_miss_count=30,
            runtime_shadow_premap_payload_cache_direct_issued_fetch_count=8,
            runtime_shadow_premap_payload_cache_direct_used_fetch_count=2,
            runtime_shadow_premap_payload_cache_direct_queue_batch_size=8,
            runtime_shadow_premap_payload_cache_direct_queue_deadline_us=1000.0,
            **_direct_snapshot_boundary(
                runtime_shadow_premap_payload_cache_direct_issue_sources=[
                    "current_router_topk_premap_shadow"
                ],
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert (
        "direct_snapshot_issue_sources_contains_non_transition_source"
        in result["failures"]
    )


def test_ready_time_payload_cache_gate_rejects_mixed_non_transition_issue_source(
    tmp_path: Path,
):
    result = check_summary(
        _direct_snapshot_summary(
            tmp_path,
            **_direct_snapshot_boundary(
                runtime_shadow_premap_payload_cache_direct_issue_sources=[
                    "prelaunch_observed_transition_premap_shadow",
                    "current_router_topk_premap_shadow",
                ],
            ),
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert (
        "direct_snapshot_issue_sources_contains_non_transition_source"
        in result["failures"]
    )


def test_ready_time_payload_cache_gate_blocks_unused_prefetches(tmp_path: Path):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_aggregate_premap_payload_cache_demand_hit_count=95,
            runtime_shadow_aggregate_premap_payload_cache_ready_late_miss_count=1,
            runtime_shadow_aggregate_premap_payload_cache_issued_fetch_count=8,
            runtime_shadow_aggregate_premap_payload_cache_used_fetch_count=0,
        ),
        root=tmp_path,
    )

    assert result["passed"] is True
    assert result["allow_full_fetch"] is False
    assert result["decision_reason"] == "full_fetch_threshold_not_met"
    assert result["metrics"]["demand_hit_rate"] == 0.95
    assert result["metrics"]["ready_late_miss_rate"] == 0.01
    assert result["metrics"]["used_per_issued_fetch"] == 0.0


def test_ready_time_payload_cache_gate_reports_invalid_evidence(tmp_path: Path):
    result = check_summary(
        _summary(
            tmp_path,
            runtime_shadow_premap_payload_cache_manager_mode="resident",
        ),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert result["allow_full_fetch"] is False
    assert result["decision_reason"] == "invalid_evidence"
    assert result["failures"] == ["mode_not_ready_time:resident"]


def test_ready_time_payload_cache_gate_cli_expect_block(tmp_path: Path):
    summary = tmp_path / "summary.json"
    output = tmp_path / "gate.json"
    summary.write_text(json.dumps(_summary(tmp_path)), encoding="utf-8")

    exit_code = main(
        [
            str(summary),
            "--root",
            str(tmp_path),
            "--expect",
            "block",
            "--output-json",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["passed"] is True
    assert payload["allow_full_fetch"] is False


def test_ready_time_payload_cache_gate_cli_rejects_wrong_expectation(tmp_path: Path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(_summary(tmp_path)), encoding="utf-8")

    exit_code = main([str(summary), "--root", str(tmp_path), "--expect", "allow"])

    assert exit_code == 1
