from __future__ import annotations

import json
import math
from pathlib import Path

from scripts import build_premap_payload_cache_manager_useful_work_ab_gate as gate


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _readiness_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_useful_work_readiness_gate",
        "mode": "payload_cache_useful_work_readiness_noop_gate",
        "passed": True,
        "ok": True,
        "failures": [],
        "producer_count_ptr_ready": True,
        "consumer_visible_blocked_ready": True,
        "native_producer_downshifted": True,
        "payload_cache_useful_work_ready": False,
        "payload_cache_useful_work_block_reason": "payload_transfer_disabled",
        "next_stage": "payload_cache_manager_useful_work_ab_or_payload_runtime_canary",
        "producer_expected_packet_count": 160,
        "consumer_requested_payload_bytes": 64,
        "payload_bytes": 0,
        "ready": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
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
    }
    payload.update(overrides)
    return payload


def _executor_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_kind": "premap_payload_cache_issue_stream_executor",
        "executor_name": "premap_payload_cache_ready_time_issue_stream_executor_v1",
        "passed": True,
        "failures": [],
        "stream_executor_ready": True,
        "manager_mode": "ready_time_stream",
        "issued_prefetch_count": 133,
        "requested_issue_count": 224,
        "demand_count": 224,
        "demand_hit_count": 199,
        "demand_hit_rate": 0.8883928571428571,
        "used_fetch_count": 108,
        "unused_fetch_count": 25,
        "used_per_issued_fetch": 0.8120300751879699,
        "ready_late_miss_rate": 0.11160714285714286,
        "queue_batch_size": 8,
        "real_payload_ready_hit_count": 0,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "full_fetch_allowed": False,
        "full_fetch_block_reason": "real_payload_runtime_not_enabled",
        "full_fetch_runtime_allowed": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_duplicate_issue_key_count": 0,
        "token_timing_enabled": True,
    }
    payload.update(overrides)
    return payload


def _run(tmp_path: Path, readiness: dict[str, object], executor: dict[str, object]):
    readiness_path = tmp_path / "readiness.json"
    executor_path = tmp_path / "executor.json"
    _write_json(readiness_path, readiness)
    _write_json(executor_path, executor)
    return gate.build_gate(
        useful_work_readiness_json=readiness_path,
        issue_stream_executor_json=executor_path,
        min_demand_hit_rate=0.5,
        min_used_per_issued_fetch=0.5,
        min_issue_count=1,
        min_demand_count=1,
    )


def test_manager_useful_work_ab_gate_accepts_payloadless_manager_useful_work(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, _readiness_payload(), _executor_payload())

    assert result["passed"] is True
    assert result["manager_useful_work_ab_ready"] is True
    assert result["payload_runtime_ready"] is False
    assert result["performance_claim_ready"] is False
    assert result["issued_prefetch_count"] == 133
    assert result["issued_payload_count"] == 0
    assert result["issued_payload_count_source"] == "explicit"
    assert result["used_fetch_count"] == 108
    assert result["unused_fetch_count"] == 25
    assert result["demand_hit_rate"] > 0.5
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["measures_tpot"] is False


def test_manager_useful_work_ab_gate_rejects_unready_precondition(
    tmp_path: Path,
) -> None:
    readiness = _readiness_payload(producer_count_ptr_ready=False)

    result = _run(tmp_path, readiness, _executor_payload())

    assert result["passed"] is False
    assert "useful_work_readiness_producer_count_ptr_ready_mismatch" in result[
        "failures"
    ]


def test_manager_useful_work_ab_gate_rejects_empty_or_low_hit_executor(
    tmp_path: Path,
) -> None:
    executor = _executor_payload(
        issued_prefetch_count=0,
        demand_hit_rate=0.1,
        used_per_issued_fetch=0.0,
    )

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is False
    assert "issue_stream_executor_issued_prefetch_count_too_low" in result["failures"]
    assert "issue_stream_executor_demand_hit_rate_below_threshold" in result[
        "failures"
    ]
    assert "issue_stream_executor_used_per_issued_fetch_below_threshold" in result[
        "failures"
    ]


def test_manager_useful_work_ab_gate_rejects_payload_or_kernel_enablement(
    tmp_path: Path,
) -> None:
    executor = _executor_payload(
        payload_transfer_enabled=True,
        payload_bytes=64,
        issued_payload_count=1,
        passed_to_kernel=True,
        measures_tpot=True,
    )

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is False
    assert "issue_stream_executor_payload_transfer_enabled_mismatch" in result[
        "failures"
    ]
    assert "issue_stream_executor_payload_bytes_mismatch" in result["failures"]
    assert "issue_stream_executor_issued_payload_count_mismatch" in result["failures"]
    assert "issue_stream_executor_passed_to_kernel_mismatch" in result["failures"]
    assert "issue_stream_executor_measures_tpot_mismatch" in result["failures"]


def test_manager_useful_work_ab_gate_rejects_legacy_runtime_aliases(
    tmp_path: Path,
) -> None:
    readiness = _readiness_payload(kernel_arg_pass=True)
    executor = _executor_payload(
        full_fetch_runtime_allowed=True,
        live_payload_runtime_enabled=True,
        payload_transfer_runtime_enabled=True,
        payload_deref_runtime_allowed=True,
    )

    result = _run(tmp_path, readiness, executor)

    assert result["passed"] is False
    assert "useful_work_readiness_kernel_arg_pass_mismatch" in result["failures"]
    assert "issue_stream_executor_full_fetch_runtime_allowed_mismatch" in result[
        "failures"
    ]
    assert "issue_stream_executor_live_payload_runtime_enabled_mismatch" in result[
        "failures"
    ]
    assert "issue_stream_executor_payload_transfer_runtime_enabled_mismatch" in result[
        "failures"
    ]
    assert "issue_stream_executor_payload_deref_runtime_allowed_mismatch" in result[
        "failures"
    ]


def test_manager_useful_work_ab_gate_rejects_non_finite_metrics(
    tmp_path: Path,
) -> None:
    executor = _executor_payload(
        demand_hit_rate=math.nan,
        used_per_issued_fetch=math.inf,
        ready_late_miss_rate=-math.inf,
    )

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is False
    assert "issue_stream_executor_demand_hit_rate_below_threshold" in result[
        "failures"
    ]
    assert "issue_stream_executor_used_per_issued_fetch_below_threshold" in result[
        "failures"
    ]
    assert "issue_stream_executor_ready_late_miss_rate_invalid" in result["failures"]


def test_manager_useful_work_ab_gate_rejects_null_issued_payload_count(
    tmp_path: Path,
) -> None:
    executor = _executor_payload(issued_payload_count=None)

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is False
    assert "issue_stream_executor_issued_payload_count_mismatch" in result["failures"]


def test_manager_useful_work_ab_gate_accepts_legacy_missing_issued_payload_count(
    tmp_path: Path,
) -> None:
    executor = _executor_payload()
    del executor["issued_payload_count"]

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is True
    assert result["issued_payload_count"] == 0
    assert result["issued_payload_count_source"] == "legacy_missing"


def test_manager_useful_work_ab_gate_rejects_incoherent_accounting(
    tmp_path: Path,
) -> None:
    executor = _executor_payload(
        issued_prefetch_count=225,
        requested_issue_count=224,
        demand_count=224,
        demand_hit_count=225,
        demand_hit_rate=0.5,
    )

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is False
    assert "issue_stream_executor_issued_prefetch_count_exceeds_requested" in result[
        "failures"
    ]
    assert "issue_stream_executor_demand_hit_count_exceeds_demand_count" in result[
        "failures"
    ]
    assert "issue_stream_executor_demand_hit_rate_incoherent" in result["failures"]


def test_manager_useful_work_ab_gate_rejects_incoherent_used_fetch_accounting(
    tmp_path: Path,
) -> None:
    executor = _executor_payload(
        used_fetch_count=0,
        unused_fetch_count=133,
        used_per_issued_fetch=1.0,
    )

    result = _run(tmp_path, _readiness_payload(), executor)

    assert result["passed"] is False
    assert "issue_stream_executor_used_fetch_count_invalid" in result["failures"]
    assert "issue_stream_executor_used_per_issued_fetch_incoherent" in result[
        "failures"
    ]
