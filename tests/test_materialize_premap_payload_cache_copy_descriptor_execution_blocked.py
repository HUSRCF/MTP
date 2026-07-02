from __future__ import annotations

import json
from pathlib import Path

from scripts import materialize_premap_payload_cache_copy_descriptor_execution_blocked as execution


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _dispatch_blocked_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_copy_descriptor_dispatch_blocked",
        "schema_name": "payload_cache_copy_descriptor_dispatch_blocked_v1",
        "passed": True,
        "failures": [],
        "copy_descriptor_dispatch_blocked_ready": True,
        "source_artifact_kind": "premap_payload_cache_copy_descriptor_submit_blocked",
        "source_schema_name": "payload_cache_copy_descriptor_submit_blocked_v1",
        "copy_descriptor_count": 11,
        "issued_prefetch_count": 11,
        "requested_issue_count": 24,
        "planned_payload_bytes_per_issue": 64,
        "planned_payload_bytes": 704,
        "packet_count": 8,
        "nonempty_packet_count": 8,
        "packet_error_count": 0,
        "submit_queue_row_count": 11,
        "submit_queue_capacity": 16,
        "dispatch_queue_shape_checked": True,
        "dispatch_capacity": 16,
        "dispatch_queue_row_count": 11,
        "dispatch_queue_planned_payload_bytes": 704,
        "copy_descriptor_dispatch_checked": True,
        "copy_descriptor_dispatch_rejected": True,
        "copy_descriptor_dispatch_allowed": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_dispatched": False,
        "copy_descriptor_executed": False,
        "copy_descriptor_row_hash": "a" * 64,
        "copy_descriptor_packet_hash": "b" * 64,
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


def test_copy_descriptor_execution_blocked_consumes_dispatch_queue(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "dispatch_blocked.json"
    output_path = tmp_path / "execution_blocked.json"
    _write_json(source_path, _dispatch_blocked_payload())

    result = execution.build_execution_blocked_artifact(
        copy_descriptor_dispatch_blocked_json=source_path,
        output_json=output_path,
        execution_capacity=16,
    )

    assert result["passed"] is True
    assert result["copy_descriptor_execution_blocked_ready"] is True
    assert result["copy_descriptor_count"] == 11
    assert result["submit_queue_row_count"] == 11
    assert result["dispatch_queue_row_count"] == 11
    assert result["execution_queue_row_count"] == 11
    assert result["execution_capacity"] == 16
    assert result["execution_queue_shape_checked"] is True
    assert result["planned_payload_bytes"] == 704
    assert result["execution_queue_planned_payload_bytes"] == 704
    assert result["copy_descriptor_execution_checked"] is True
    assert result["copy_descriptor_execution_rejected"] is True
    assert result["copy_descriptor_execution_allowed"] is False
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


def test_copy_descriptor_execution_blocked_rejects_dispatched_or_executed_source(
    tmp_path: Path,
) -> None:
    for field_name in (
        "copy_descriptor_submitted",
        "copy_descriptor_dispatched",
        "copy_descriptor_executed",
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(source_path, _dispatch_blocked_payload(**{field_name: True}))

        result = execution.build_execution_blocked_artifact(
            copy_descriptor_dispatch_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_execution_blocked.json",
            execution_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]


def test_copy_descriptor_execution_blocked_rejects_small_execution_capacity(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "dispatch_blocked.json"
    _write_json(source_path, _dispatch_blocked_payload())

    result = execution.build_execution_blocked_artifact(
        copy_descriptor_dispatch_blocked_json=source_path,
        output_json=tmp_path / "execution_blocked.json",
        execution_capacity=10,
    )

    assert result["passed"] is False
    assert "execution_capacity_too_small" in result["failures"]


def test_copy_descriptor_execution_blocked_rejects_zero_execution_capacity(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "dispatch_blocked.json"
    _write_json(source_path, _dispatch_blocked_payload())

    result = execution.build_execution_blocked_artifact(
        copy_descriptor_dispatch_blocked_json=source_path,
        output_json=tmp_path / "execution_blocked.json",
        execution_capacity=0,
    )

    assert result["passed"] is False
    assert "execution_capacity_invalid" in result["failures"]


def test_copy_descriptor_execution_blocked_rejects_non_hex_source_hash(
    tmp_path: Path,
) -> None:
    for field_name in ("copy_descriptor_row_hash", "copy_descriptor_packet_hash"):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(source_path, _dispatch_blocked_payload(**{field_name: "x" * 64}))

        result = execution.build_execution_blocked_artifact(
            copy_descriptor_dispatch_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_execution_blocked.json",
            execution_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_invalid" in result["failures"]
