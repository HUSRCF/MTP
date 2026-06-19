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


def _run(module, slack_path: Path, output_path: Path, *, deadline: float = 200.0) -> dict:
    args = module.build_parser().parse_args(
        [
            "--slack-sweep-json",
            str(slack_path),
            "--current-deadline-us",
            str(deadline),
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
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "insufficient_ready_time_slack"
    assert result["metadata_premap_runtime_preferred"] is True
    assert result["slack_deficit_us"] == 3800.0
    assert result["payload_transfer_enabled"] is False
    assert result["passed_to_kernel"] is False
    assert result["measures_tpot"] is False
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_full_fetch_decision_keeps_runtime_disabled_when_model_slack_passes(
    tmp_path: Path,
):
    module = _load_module()
    slack_path = tmp_path / "slack.json"
    _write_json(slack_path, _slack_payload(first_deadline=4000.0))

    result = _run(module, slack_path, tmp_path / "decision.json", deadline=5000.0)

    assert result["passed"] is True
    assert result["ready_time_model_slack_satisfied"] is True
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
