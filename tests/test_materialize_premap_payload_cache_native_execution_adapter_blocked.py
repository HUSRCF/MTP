from __future__ import annotations

import json
from pathlib import Path

from scripts import (
    materialize_premap_payload_cache_native_execution_adapter_blocked as adapter,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _ready_credit_blocked_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_ready_credit_blocked",
        "schema_name": "payload_cache_ready_credit_blocked_v1",
        "passed": True,
        "failures": [],
        "ready_credit_blocked_ready": True,
        "source_artifact_kind": "premap_payload_cache_copy_completion_blocked",
        "source_schema_name": "payload_cache_copy_completion_blocked_v1",
        "copy_descriptor_count": 11,
        "issued_prefetch_count": 11,
        "requested_issue_count": 24,
        "planned_payload_bytes_per_issue": 64,
        "planned_payload_bytes": 704,
        "packet_count": 8,
        "nonempty_packet_count": 8,
        "packet_error_count": 0,
        "submit_queue_row_count": 11,
        "dispatch_queue_row_count": 11,
        "dispatch_capacity": 16,
        "execution_queue_row_count": 11,
        "execution_capacity": 16,
        "completion_queue_row_count": 11,
        "completion_capacity": 16,
        "ready_credit_queue_shape_checked": True,
        "ready_credit_capacity": 16,
        "ready_credit_queue_row_count": 11,
        "ready_credit_queue_planned_payload_bytes": 704,
        "ready_credit_checked": True,
        "ready_credit_rejected": True,
        "ready_credit_allowed": False,
        "ready_credit_count": 0,
        "copy_completed": False,
        "copy_completion_count": 0,
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


def test_native_execution_adapter_blocked_consumes_ready_credit_rows(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "ready_credit_blocked.json"
    output_path = tmp_path / "native_execution_adapter_blocked.json"
    _write_json(source_path, _ready_credit_blocked_payload())

    result = adapter.build_native_execution_adapter_blocked_artifact(
        ready_credit_blocked_json=source_path,
        output_json=output_path,
        adapter_capacity=16,
    )

    assert result["passed"] is True
    assert result["native_execution_adapter_blocked_ready"] is True
    assert result["copy_descriptor_count"] == 11
    assert result["ready_credit_queue_row_count"] == 11
    assert result["native_execution_adapter_row_count"] == 11
    assert result["native_execution_adapter_capacity"] == 16
    assert result["native_execution_adapter_row_window_checked"] is True
    assert result["native_execution_adapter_checked"] is True
    assert result["native_execution_adapter_rejected"] is True
    assert result["native_execution_adapter_allowed"] is False
    assert result["native_execution_adapter_consumes_ready_credit_blocked"] is True
    assert result["native_execution_adapter_execution_count"] == 0
    assert result["native_execution_adapter_completed_count"] == 0
    assert result["native_execution_adapter_payload_copy_count"] == 0
    assert result["native_execution_adapter_ready_credit_count"] == 0
    assert result["planned_payload_bytes"] == 704
    assert result["native_execution_adapter_planned_payload_bytes"] == 704
    assert result["copy_completed"] is False
    assert result["copy_completion_count"] == 0
    assert result["ready_credit"] is False
    assert result["ready_before_demand_credit"] is False
    assert result["real_ready_credit_granted"] is False
    assert result["payload_bytes"] == 0
    assert result["issued_payload_count"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["uses_current_wna16_args"] is False
    assert output_path.exists()


def test_native_execution_adapter_blocked_rejects_completion_or_ready_source(
    tmp_path: Path,
) -> None:
    for field_name, value in (
        ("copy_completed", True),
        ("copy_completion_count", 1),
        ("ready_credit", True),
        ("ready_before_demand_credit", True),
        ("real_ready_credit_granted", True),
        ("ready_credit_count", 1),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(source_path, _ready_credit_blocked_payload(**{field_name: value}))

        result = adapter.build_native_execution_adapter_blocked_artifact(
            ready_credit_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_adapter_blocked.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]


def test_native_execution_adapter_blocked_rejects_bad_source_contract(
    tmp_path: Path,
) -> None:
    for field_name, value in (
        ("artifact_kind", "wrong"),
        ("schema_name", "wrong"),
        ("passed", False),
        ("failures", ["boom"]),
        ("ready_credit_blocked_ready", False),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(source_path, _ready_credit_blocked_payload(**{field_name: value}))

        result = adapter.build_native_execution_adapter_blocked_artifact(
            ready_credit_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_adapter_blocked.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]


def test_native_execution_adapter_blocked_rejects_payload_or_kernel_source(
    tmp_path: Path,
) -> None:
    for field_name, value in (
        ("payload_transfer_enabled", True),
        ("payload_bytes", 1),
        ("kernel_arg_pass_allowed", True),
        ("passed_to_kernel", True),
        ("uses_current_wna16_args", True),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(source_path, _ready_credit_blocked_payload(**{field_name: value}))

        result = adapter.build_native_execution_adapter_blocked_artifact(
            ready_credit_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_adapter_blocked.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]


def test_native_execution_adapter_blocked_rejects_small_adapter_capacity(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "ready_credit_blocked.json"
    _write_json(source_path, _ready_credit_blocked_payload())

    result = adapter.build_native_execution_adapter_blocked_artifact(
        ready_credit_blocked_json=source_path,
        output_json=tmp_path / "native_execution_adapter_blocked.json",
        adapter_capacity=10,
    )

    assert result["passed"] is False
    assert "native_execution_adapter_capacity_too_small" in result["failures"]


def test_native_execution_adapter_blocked_rejects_zero_adapter_capacity(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "ready_credit_blocked.json"
    _write_json(source_path, _ready_credit_blocked_payload())

    result = adapter.build_native_execution_adapter_blocked_artifact(
        ready_credit_blocked_json=source_path,
        output_json=tmp_path / "native_execution_adapter_blocked.json",
        adapter_capacity=0,
    )

    assert result["passed"] is False
    assert "native_execution_adapter_capacity_invalid" in result["failures"]


def test_native_execution_adapter_blocked_rejects_non_hex_source_hash(
    tmp_path: Path,
) -> None:
    for field_name in ("copy_descriptor_row_hash", "copy_descriptor_packet_hash"):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(
            source_path,
            _ready_credit_blocked_payload(**{field_name: "x" * 64}),
        )

        result = adapter.build_native_execution_adapter_blocked_artifact(
            ready_credit_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_adapter_blocked.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_invalid" in result["failures"]
