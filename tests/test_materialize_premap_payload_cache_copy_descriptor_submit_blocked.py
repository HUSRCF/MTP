from __future__ import annotations

import json
from pathlib import Path

from scripts import materialize_premap_payload_cache_copy_descriptor_submit_blocked as submit


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _copy_descriptor_plan_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_copy_descriptor_plan",
        "schema_name": "payload_cache_issue_copy_descriptor_plan_v1",
        "row_schema_name": "payload_cache_issue_copy_descriptor_row_v1",
        "passed": True,
        "failures": [],
        "copy_descriptor_plan_ready": True,
        "packet_count": 8,
        "nonempty_packet_count": 8,
        "packet_error_count": 0,
        "requested_issue_count": 24,
        "issued_prefetch_count": 11,
        "copy_descriptor_count": 11,
        "copy_descriptor_shape_checked": True,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "copy_descriptor_row_hash": "a" * 64,
        "copy_descriptor_packet_hash": "b" * 64,
        "planned_payload_bytes_per_issue": 64,
        "planned_payload_bytes": 704,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "live_runtime_instantiated": False,
        "requires_payload_runtime": False,
    }
    payload.update(overrides)
    return payload


def test_copy_descriptor_submit_blocked_consumes_plan_rows(tmp_path: Path) -> None:
    plan_path = tmp_path / "copy_descriptor_plan.json"
    output_path = tmp_path / "submit_blocked.json"
    _write_json(plan_path, _copy_descriptor_plan_payload())

    result = submit.build_submit_blocked_artifact(
        copy_descriptor_plan_json=plan_path,
        output_json=output_path,
        queue_capacity=16,
    )

    assert result["passed"] is True
    assert result["copy_descriptor_submit_blocked_ready"] is True
    assert result["copy_descriptor_count"] == 11
    assert result["submit_queue_row_count"] == 11
    assert result["submit_queue_capacity"] == 16
    assert result["submit_queue_shape_checked"] is True
    assert result["planned_payload_bytes"] == 704
    assert result["submit_queue_planned_payload_bytes"] == 704
    assert result["copy_descriptor_submit_checked"] is True
    assert result["copy_descriptor_submit_rejected"] is True
    assert result["copy_descriptor_submit_allowed"] is False
    assert result["copy_descriptor_submitted"] is False
    assert result["copy_descriptor_dispatched"] is False
    assert result["copy_descriptor_executed"] is False
    assert result["payload_bytes"] == 0
    assert result["issued_payload_count"] == 0
    assert result["ready_credit"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["uses_current_wna16_args"] is False
    assert output_path.exists()


def test_copy_descriptor_submit_blocked_rejects_payload_runtime_enabled(
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "copy_descriptor_plan.json"
    _write_json(
        plan_path,
        _copy_descriptor_plan_payload(live_payload_runtime_enabled=True),
    )

    result = submit.build_submit_blocked_artifact(
        copy_descriptor_plan_json=plan_path,
        output_json=tmp_path / "submit_blocked.json",
        queue_capacity=11,
    )

    assert result["passed"] is False
    assert "source_live_payload_runtime_enabled_mismatch" in result["failures"]


def test_copy_descriptor_submit_blocked_rejects_small_queue_capacity(
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "copy_descriptor_plan.json"
    _write_json(plan_path, _copy_descriptor_plan_payload())

    result = submit.build_submit_blocked_artifact(
        copy_descriptor_plan_json=plan_path,
        output_json=tmp_path / "submit_blocked.json",
        queue_capacity=10,
    )

    assert result["passed"] is False
    assert "submit_queue_capacity_too_small" in result["failures"]


def test_copy_descriptor_submit_blocked_rejects_non_hex_source_hash(
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "copy_descriptor_plan.json"
    _write_json(
        plan_path,
        _copy_descriptor_plan_payload(copy_descriptor_packet_hash="z" * 64),
    )

    result = submit.build_submit_blocked_artifact(
        copy_descriptor_plan_json=plan_path,
        output_json=tmp_path / "submit_blocked.json",
        queue_capacity=11,
    )

    assert result["passed"] is False
    assert "source_copy_descriptor_packet_hash_invalid" in result["failures"]
