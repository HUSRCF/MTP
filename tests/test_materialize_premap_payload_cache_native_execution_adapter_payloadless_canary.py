from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import (
    materialize_premap_payload_cache_native_execution_adapter_payloadless_canary
    as canary,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _native_execution_adapter_blocked_payload(
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_native_execution_adapter_blocked",
        "schema_name": "payload_cache_native_execution_adapter_blocked_v1",
        "passed": True,
        "failures": [],
        "native_execution_adapter_blocked_ready": True,
        "source_artifact_kind": "premap_payload_cache_ready_credit_blocked",
        "source_schema_name": "payload_cache_ready_credit_blocked_v1",
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
        "ready_credit_queue_row_count": 11,
        "ready_credit_capacity": 16,
        "ready_credit_queue_planned_payload_bytes": 704,
        "native_execution_adapter_row_window_checked": True,
        "native_execution_adapter_capacity": 16,
        "native_execution_adapter_row_count": 11,
        "native_execution_adapter_planned_payload_bytes": 704,
        "native_execution_adapter_checked": True,
        "native_execution_adapter_rejected": True,
        "native_execution_adapter_allowed": False,
        "native_execution_adapter_consumes_ready_credit_blocked": True,
        "native_execution_adapter_execution_count": 0,
        "native_execution_adapter_completed_count": 0,
        "native_execution_adapter_payload_copy_count": 0,
        "native_execution_adapter_ready_credit_count": 0,
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


def test_payloadless_canary_consumes_native_adapter_rows(tmp_path: Path) -> None:
    source_path = tmp_path / "adapter_blocked.json"
    output_path = tmp_path / "adapter_payloadless.json"
    _write_json(source_path, _native_execution_adapter_blocked_payload())

    result = canary.build_native_execution_adapter_payloadless_canary_artifact(
        native_execution_adapter_blocked_json=source_path,
        output_json=output_path,
        adapter_capacity=16,
    )

    assert result["passed"] is True
    assert result["native_execution_adapter_payloadless_canary_ready"] is True
    assert result["copy_descriptor_count"] == 11
    assert result["ready_credit_queue_row_count"] == 11
    assert result["payloadless_adapter_capacity"] == 16
    assert result["payloadless_adapter_capacity_checked"] is True
    assert result["native_execution_adapter_payloadless_checked"] is True
    assert result["native_execution_adapter_payloadless_allowed"] is True
    assert result["native_execution_adapter_payloadless_executed"] is True
    assert result["native_execution_adapter_payloadless_rows_consumed"] == 11
    assert result["native_execution_adapter_payloadless_execution_count"] == 11
    assert result["native_execution_adapter_payloadless_completed_count"] == 11
    assert result["native_execution_adapter_payloadless_field_count"] == 4
    assert result["native_execution_adapter_payloadless_fields_per_row"] == 4
    assert result["native_execution_adapter_payloadless_work_units"] == 44
    assert result["native_execution_adapter_payloadless_expected_work_units"] == 44
    assert result["native_execution_adapter_payloadless_work_coverage"] == 1.0
    assert result["native_execution_adapter_payloadless_field_names"] == list(
        canary.ADAPTER_FIELD_NAMES
    )
    assert set(result["native_execution_adapter_payloadless_field_hashes"]) == set(
        canary.ADAPTER_FIELD_NAMES
    )
    assert len(result["native_execution_adapter_payloadless_chain_hash"]) == 64
    assert result["native_execution_adapter_effectful_allowed"] is False
    assert result["native_execution_adapter_effectful_execution_count"] == 0
    assert result["native_execution_adapter_execution_count"] == 0
    assert result["native_execution_adapter_completed_count"] == 0
    assert result["native_execution_adapter_payload_copy_count"] == 0
    assert result["native_execution_adapter_ready_credit_count"] == 0
    assert result["copy_completed"] is False
    assert result["ready_credit"] is False
    assert result["ready_before_demand_credit"] is False
    assert result["real_ready_credit_granted"] is False
    assert result["payload_bytes"] == 0
    assert result["issued_payload_count"] == 0
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["uses_current_wna16_args"] is False
    assert output_path.exists()


def test_payloadless_canary_rejects_unblocked_or_allowed_source(
    tmp_path: Path,
) -> None:
    for field_name, value in (
        ("native_execution_adapter_blocked_ready", False),
        ("native_execution_adapter_checked", False),
        ("native_execution_adapter_rejected", False),
        ("native_execution_adapter_allowed", True),
        ("native_execution_adapter_consumes_ready_credit_blocked", False),
        ("native_execution_adapter_execution_count", 1),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(
            source_path,
            _native_execution_adapter_blocked_payload(**{field_name: value}),
        )

        result = canary.build_native_execution_adapter_payloadless_canary_artifact(
            native_execution_adapter_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_payloadless.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]
        assert result["native_execution_adapter_payloadless_allowed"] is False
        assert result["native_execution_adapter_payloadless_executed"] is False
        assert result["native_execution_adapter_payloadless_rows_consumed"] == 0


def test_payloadless_canary_rejects_wrong_upstream_provenance(
    tmp_path: Path,
) -> None:
    for field_name, value in (
        ("source_artifact_kind", "wrong"),
        ("source_schema_name", "wrong"),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(
            source_path,
            _native_execution_adapter_blocked_payload(**{field_name: value}),
        )

        result = canary.build_native_execution_adapter_payloadless_canary_artifact(
            native_execution_adapter_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_payloadless.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]
        assert result["native_execution_adapter_payloadless_allowed"] is False
        assert result["native_execution_adapter_payloadless_executed"] is False


def test_payloadless_canary_rejects_payload_ready_or_kernel_effects(
    tmp_path: Path,
) -> None:
    for field_name, value in (
        ("payload_bytes", 1),
        ("issued_payload_count", 1),
        ("payload_transfer_enabled", True),
        ("ready_credit", True),
        ("real_ready_credit_granted", True),
        ("kernel_arg_pass_allowed", True),
        ("passed_to_kernel", True),
        ("uses_current_wna16_args", True),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(
            source_path,
            _native_execution_adapter_blocked_payload(**{field_name: value}),
        )

        result = canary.build_native_execution_adapter_payloadless_canary_artifact(
            native_execution_adapter_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_payloadless.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert f"source_{field_name}_mismatch" in result["failures"]
        assert result["native_execution_adapter_payloadless_allowed"] is False


def test_payloadless_canary_rejects_count_and_bytes_mismatches(
    tmp_path: Path,
) -> None:
    for field_name, value, failure in (
        ("copy_descriptor_count", 10, "source_copy_descriptor_count_mismatch"),
        (
            "ready_credit_queue_row_count",
            10,
            "source_ready_credit_queue_row_count_mismatch",
        ),
        ("issued_prefetch_count", 10, "source_issued_prefetch_count_mismatch"),
        ("planned_payload_bytes", 705, "source_planned_payload_bytes_mismatch"),
        (
            "native_execution_adapter_planned_payload_bytes",
            705,
            "source_planned_payload_bytes_mismatch",
        ),
    ):
        source_path = tmp_path / f"{field_name}.json"
        _write_json(
            source_path,
            _native_execution_adapter_blocked_payload(**{field_name: value}),
        )

        result = canary.build_native_execution_adapter_payloadless_canary_artifact(
            native_execution_adapter_blocked_json=source_path,
            output_json=tmp_path / f"{field_name}_payloadless.json",
            adapter_capacity=16,
        )

        assert result["passed"] is False
        assert failure in result["failures"]
        assert result["native_execution_adapter_payloadless_allowed"] is False


def test_payloadless_canary_rejects_invalid_capacity_or_hash(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "adapter_blocked.json"
    _write_json(source_path, _native_execution_adapter_blocked_payload())

    result = canary.build_native_execution_adapter_payloadless_canary_artifact(
        native_execution_adapter_blocked_json=source_path,
        output_json=tmp_path / "too_small.json",
        adapter_capacity=10,
    )

    assert result["passed"] is False
    assert "payloadless_adapter_capacity_too_small" in result["failures"]
    assert result["native_execution_adapter_payloadless_allowed"] is False

    bad_hash_path = tmp_path / "bad_hash.json"
    _write_json(
        bad_hash_path,
        _native_execution_adapter_blocked_payload(copy_descriptor_row_hash="bad"),
    )
    result = canary.build_native_execution_adapter_payloadless_canary_artifact(
        native_execution_adapter_blocked_json=bad_hash_path,
        output_json=tmp_path / "bad_hash_out.json",
        adapter_capacity=16,
    )

    assert result["passed"] is False
    assert "source_copy_descriptor_row_hash_invalid" in result["failures"]
    assert result["native_execution_adapter_payloadless_allowed"] is False


def test_payloadless_canary_require_pass_raises_on_failure(tmp_path: Path) -> None:
    source_path = tmp_path / "adapter_blocked.json"
    _write_json(source_path, _native_execution_adapter_blocked_payload(payload_bytes=1))

    with pytest.raises(SystemExit):
        canary.build_native_execution_adapter_payloadless_canary_artifact(
            native_execution_adapter_blocked_json=source_path,
            output_json=tmp_path / "out.json",
            adapter_capacity=16,
            require_pass=True,
        )
