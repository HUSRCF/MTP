from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_payload_cache_ready_time_gate import check_summary, main


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
        ),
        root=tmp_path,
    )

    assert result["passed"] is True
    assert result["allow_full_fetch"] is False
    assert result["decision_reason"] == "full_fetch_threshold_not_met"
    assert result["metrics"]["manager_count"] == 1
    assert result["metrics"]["demand_count"] == 100
    assert result["metrics"]["demand_hit_count"] == 25
    assert result["metrics"]["ready_late_miss_count"] == 30
    assert result["metrics"]["used_per_issued_fetch"] == 0.25


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
