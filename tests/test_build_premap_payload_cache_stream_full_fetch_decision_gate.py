from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_premap_payload_cache_stream_full_fetch_decision_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_premap_payload_cache_stream_full_fetch_decision_gate",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _safe_fields() -> dict:
    return {
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "full_fetch_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def _row(*, lookahead: float, passed: bool) -> dict:
    return {
        **_safe_fields(),
        "lookahead_us": lookahead,
        "model_passed": passed,
        "passed": passed,
        "safety_passed": True,
        "safety_failures": [],
        "demand_hit_rate": 0.9 if passed else 0.25,
        "ready_late_miss_rate": 0.0 if passed else 0.75,
        "used_per_issued_fetch": 0.8 if passed else 0.0,
    }


def _sweep_payload(*, first_lookahead: float = 200_000.0) -> dict:
    return {
        **_safe_fields(),
        "artifact_kind": "premap_payload_cache_issue_stream_executor_lookahead_sweep",
        "passed": True,
        "first_model_passing_lookahead_us": first_lookahead,
        "queue_deadline_us": 200.0,
        "lookahead_us_values": [0.0, first_lookahead, first_lookahead + 50_000.0],
        "measured_copy_json": "/tmp/measured_copy.json",
        "measured_copy_stat": "p95",
        "measured_copy_experts": 8,
        "measured_copy_pinned": "true",
        "capacity": 12288,
        "rows": [
            _row(lookahead=0.0, passed=False),
            _row(lookahead=first_lookahead, passed=True),
            _row(lookahead=first_lookahead + 50_000.0, passed=True),
        ],
    }


def _run(
    module,
    sweep_path: Path,
    output_path: Path,
    *,
    lookahead: float = 0.0,
    queue_deadline: float = 200.0,
) -> dict:
    args = module.build_parser().parse_args(
        [
            "--stream-lookahead-sweep-json",
            str(sweep_path),
            "--current-lookahead-us",
            str(lookahead),
            "--current-queue-deadline-us",
            str(queue_deadline),
            "--output-json",
            str(output_path),
        ]
    )
    return module.build_stream_full_fetch_decision_gate(args)


def test_stream_full_fetch_decision_blocks_insufficient_lookahead(tmp_path: Path):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    output_path = tmp_path / "decision.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))

    result = _run(module, sweep_path, output_path, lookahead=0.0)

    assert result["passed"] is True
    assert result["ready_time_model_lookahead_satisfied"] is False
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "insufficient_stream_lookahead"
    assert result["metadata_premap_runtime_preferred"] is True
    assert result["descriptor_prep_runtime_preferred"] is True
    assert result["lookahead_deficit_us"] == 200_000.0
    assert result["payload_transfer_enabled"] is False
    assert result["passed_to_kernel"] is False
    assert result["measures_tpot"] is False
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_stream_full_fetch_decision_keeps_runtime_disabled_when_model_passes(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        lookahead=200_000.0,
    )

    assert result["passed"] is True
    assert result["ready_time_model_lookahead_satisfied"] is True
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "real_payload_runtime_not_enabled"
    assert result["metadata_premap_runtime_preferred"] is False
    assert result["lookahead_deficit_us"] == 0.0


def test_stream_full_fetch_decision_rejects_unsafe_top_level_artifact(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["payload_transfer_enabled"] = True
    payload["payload_bytes"] = 16
    _write_json(sweep_path, payload)

    result = _run(module, sweep_path, tmp_path / "decision.json")

    assert result["passed"] is False
    assert "stream_lookahead_sweep_payload_transfer_enabled_not_false" in result[
        "failures"
    ]
    assert "stream_lookahead_sweep_payload_bytes_not_zero" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_stream_full_fetch_decision_rejects_unsafe_row(tmp_path: Path):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["rows"][0]["kernel_arg_pass_allowed"] = True
    _write_json(sweep_path, payload)

    result = _run(module, sweep_path, tmp_path / "decision.json")

    assert result["passed"] is False
    assert "stream_lookahead_row_0_kernel_arg_pass_allowed_not_false" in result[
        "failures"
    ]
    assert "stream_lookahead_row_0_safety_passed_mismatch" in result["failures"]
    assert "stream_lookahead_row_0_safety_failures_mismatch" in result["failures"]


def test_stream_full_fetch_decision_rejects_rows_first_mismatch(tmp_path: Path):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["first_model_passing_lookahead_us"] = 0.0
    _write_json(sweep_path, payload)

    result = _run(module, sweep_path, tmp_path / "decision.json")

    assert result["passed"] is False
    assert "first_model_passing_lookahead_rows_mismatch" in result["failures"]


def test_stream_full_fetch_decision_rejects_stale_rows_without_safety_schema(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["rows"][1].pop("safety_passed")
    payload["rows"][1].pop("safety_failures")
    _write_json(sweep_path, payload)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        lookahead=200_000.0,
    )

    assert result["passed"] is False
    assert "stream_lookahead_row_1_safety_passed_missing" in result["failures"]
    assert "stream_lookahead_row_1_safety_failures_invalid" in result["failures"]
    assert "stream_lookahead_row_1_safety_passed_mismatch" in result["failures"]
    assert "stream_lookahead_row_1_passed_safety_mismatch" in result["failures"]


def test_stream_full_fetch_decision_rejects_queue_deadline_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_deadline=1000.0,
    )

    assert result["passed"] is False
    assert "stream_queue_deadline_current_deadline_mismatch" in result["failures"]
