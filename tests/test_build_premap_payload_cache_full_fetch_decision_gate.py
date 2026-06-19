from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_premap_payload_cache_full_fetch_decision_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_premap_payload_cache_full_fetch_decision_gate",
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


def _slack_payload(*, first_deadline: float = 4000.0) -> dict:
    return {
        "artifact_kind": "premap_payload_cache_issue_plan_executor_slack_sweep",
        "passed": True,
        "first_model_passing_deadline_us": first_deadline,
        "deadline_us_values": [200.0, first_deadline, first_deadline + 1000.0],
        "issue_plan_gate_json": "/tmp/issue_gate.json",
        "measured_copy_json": "/tmp/measured_copy.json",
        "measured_copy_stat": "p95",
        "measured_copy_experts": 4,
        "measured_copy_pinned": "true",
        "capacity": 12288,
        "rows": [
            {
                "deadline_us": 200.0,
                "model_passed": False,
                "passed": False,
                "full_fetch_allowed": False,
            },
            {
                "deadline_us": first_deadline,
                "model_passed": True,
                "passed": True,
                "full_fetch_allowed": False,
            },
            {
                "deadline_us": first_deadline + 1000.0,
                "model_passed": True,
                "passed": True,
                "full_fetch_allowed": False,
            },
        ],
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


def _lookahead_payload(
    *,
    first_lookahead: float = 3800.0,
    queue_deadline: float = 200.0,
) -> dict:
    return {
        "artifact_kind": "premap_payload_cache_issue_plan_executor_lookahead_sweep",
        "passed": True,
        "first_model_passing_lookahead_us": first_lookahead,
        "queue_deadline_us": queue_deadline,
        "lookahead_us_values": [0.0, first_lookahead, first_lookahead + 1000.0],
        "issue_plan_gate_json": "/tmp/issue_gate.json",
        "measured_copy_json": "/tmp/measured_copy.json",
        "measured_copy_stat": "p95",
        "measured_copy_experts": 4,
        "measured_copy_pinned": "true",
        "capacity": 12288,
        "rows": [
            {
                "lookahead_us": 0.0,
                "model_passed": False,
                "passed": False,
                "full_fetch_allowed": False,
            },
            {
                "lookahead_us": first_lookahead,
                "model_passed": True,
                "passed": True,
                "full_fetch_allowed": False,
            },
            {
                "lookahead_us": first_lookahead + 1000.0,
                "model_passed": True,
                "passed": True,
                "full_fetch_allowed": False,
            },
        ],
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


def _run(
    module,
    slack_path: Path,
    output_path: Path,
    *,
    deadline: float = 200.0,
    lookahead_path: Path | None = None,
    lookahead: float = 0.0,
) -> dict:
    if lookahead_path is None:
        lookahead_path = output_path.parent / "lookahead.json"
        _write_json(lookahead_path, _lookahead_payload())
    args = module.build_parser().parse_args(
        [
            "--slack-sweep-json",
            str(slack_path),
            "--lookahead-sweep-json",
            str(lookahead_path),
            "--current-deadline-us",
            str(deadline),
            "--current-lookahead-us",
            str(lookahead),
            "--output-json",
            str(output_path),
        ]
    )
    return module.build_full_fetch_decision_gate(args)


def test_full_fetch_decision_blocks_insufficient_deadline(tmp_path: Path):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    output_path = tmp_path / "decision.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))

    result = _run(module, slack_path, output_path, deadline=200.0)

    assert result["passed"] is True
    assert result["ready_time_model_slack_satisfied"] is False
    assert result["ready_time_model_lookahead_satisfied"] is False
    assert result["ready_time_any_model_route_satisfied"] is False
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "insufficient_ready_time_and_lookahead"
    assert result["metadata_premap_runtime_preferred"] is True
    assert result["slack_deficit_us"] == 3800.0
    assert result["lookahead_deficit_us"] == 3800.0
    assert result["payload_transfer_enabled"] is False
    assert result["passed_to_kernel"] is False
    assert result["measures_tpot"] is False
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_full_fetch_decision_keeps_runtime_disabled_when_model_slack_passes(
    tmp_path: Path,
):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    lookahead_path = tmp_path / "lookahead.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))
    _write_json(
        lookahead_path,
        _lookahead_payload(first_lookahead=3800.0, queue_deadline=5000.0),
    )

    result = _run(
        module,
        slack_path,
        tmp_path / "decision.json",
        deadline=5000.0,
        lookahead_path=lookahead_path,
        lookahead=5000.0,
    )

    assert result["passed"] is True
    assert result["ready_time_model_slack_satisfied"] is True
    assert result["ready_time_model_lookahead_satisfied"] is True
    assert result["ready_time_any_model_route_satisfied"] is True
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "real_payload_runtime_not_enabled"
    assert result["metadata_premap_runtime_preferred"] is False
    assert result["descriptor_prep_runtime_preferred"] is True


def test_full_fetch_decision_rejects_unsafe_slack_artifact(tmp_path: Path):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    payload = _slack_payload(first_deadline=4000.0)
    payload["full_fetch_allowed"] = True
    payload["payload_bytes"] = 16
    _write_json(slack_path, payload)

    result = _run(module, slack_path, tmp_path / "decision.json", deadline=200.0)

    assert result["passed"] is False
    assert "slack_sweep_full_fetch_allowed_not_false" in result["failures"]
    assert "slack_sweep_payload_bytes_not_zero" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_full_fetch_decision_rejects_rows_first_deadline_mismatch(tmp_path: Path):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    payload = _slack_payload(first_deadline=4000.0)
    payload["first_model_passing_deadline_us"] = 200.0
    _write_json(slack_path, payload)

    result = _run(module, slack_path, tmp_path / "decision.json", deadline=200.0)

    assert result["passed"] is False
    assert "first_model_passing_deadline_rows_mismatch" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_full_fetch_decision_rejects_row_full_fetch_allowed(tmp_path: Path):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    payload = _slack_payload(first_deadline=4000.0)
    payload["rows"][0]["full_fetch_allowed"] = True
    _write_json(slack_path, payload)

    result = _run(module, slack_path, tmp_path / "decision.json", deadline=200.0)

    assert result["passed"] is False
    assert "slack_sweep_row_0_full_fetch_allowed_not_false" in result["failures"]
    assert "current_deadline_row_full_fetch_allowed_not_false" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_full_fetch_decision_rejects_lookahead_rows_first_mismatch(tmp_path: Path):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    lookahead_path = tmp_path / "lookahead.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))
    payload = _lookahead_payload(first_lookahead=3800.0)
    payload["first_model_passing_lookahead_us"] = 0.0
    _write_json(lookahead_path, payload)

    result = _run(
        module,
        slack_path,
        tmp_path / "decision.json",
        lookahead_path=lookahead_path,
        deadline=200.0,
        lookahead=0.0,
    )

    assert result["passed"] is False
    assert "first_model_passing_lookahead_rows_mismatch" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_full_fetch_decision_rejects_lookahead_provenance_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    lookahead_path = tmp_path / "lookahead.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))
    payload = _lookahead_payload(first_lookahead=3800.0)
    payload["measured_copy_json"] = "/tmp/other_measured_copy.json"
    _write_json(lookahead_path, payload)

    result = _run(
        module,
        slack_path,
        tmp_path / "decision.json",
        lookahead_path=lookahead_path,
    )

    assert result["passed"] is False
    assert "sweep_measured_copy_json_mismatch" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_full_fetch_decision_rejects_lookahead_deadline_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    lookahead_path = tmp_path / "lookahead.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))
    payload = _lookahead_payload(first_lookahead=3800.0)
    payload["queue_deadline_us"] = 1000.0
    _write_json(lookahead_path, payload)

    result = _run(
        module,
        slack_path,
        tmp_path / "decision.json",
        lookahead_path=lookahead_path,
        deadline=200.0,
    )

    assert result["passed"] is False
    assert "lookahead_sweep_queue_deadline_current_deadline_mismatch" in result[
        "failures"
    ]
    assert result["full_fetch_runtime_allowed"] is False


def test_full_fetch_decision_rejects_unsafe_lookahead_artifact(tmp_path: Path):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    lookahead_path = tmp_path / "lookahead.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))
    payload = _lookahead_payload(first_lookahead=3800.0)
    payload["payload_transfer_enabled"] = True
    _write_json(lookahead_path, payload)

    result = _run(
        module,
        slack_path,
        tmp_path / "decision.json",
        lookahead_path=lookahead_path,
    )

    assert result["passed"] is False
    assert "lookahead_sweep_payload_transfer_enabled_not_false" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False
