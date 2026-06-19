from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_executor_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_premap_payload_cache_issue_plan_executor.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_premap_payload_cache_issue_plan_executor",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "sweep_premap_payload_cache_issue_plan_executor_slack.py"
    )
    spec = importlib.util.spec_from_file_location(
        "sweep_premap_payload_cache_issue_plan_executor_slack",
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


def _gate_payload() -> dict:
    executor = _load_executor_module()
    experts = tuple(range(4))
    return {
        "passed": True,
        "issue_plan_ready": True,
        "payload_cache_issue_plan_candidate": True,
        "native_issue_plan_valid": True,
        "runtime_contract_ready": True,
        "issue_candidate_count": len(experts),
        "issue_candidate_hash": executor._issue_hash(list(experts)),  # noqa: SLF001
        "issue_candidate_experts": list(experts),
        "layer_id": 0,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }


def test_slack_sweep_finds_first_passing_deadline(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload())
    _write_json(
        measured_copy_path,
        {
            "rows": [
                {
                    "direction": "h2d",
                    "pinned": True,
                    "experts": 4,
                    "p95_ms": 4.0,
                }
            ]
        },
    )

    args = module.build_parser().parse_args(
        [
            "--issue-plan-gate-json",
            str(gate_path),
            "--measured-copy-json",
            str(measured_copy_path),
            "--measured-copy-experts",
            "4",
            "--deadline-us-values",
            "200,3999,4000,5000",
            "--output-json",
            str(tmp_path / "sweep.json"),
        ]
    )
    result = module.run_slack_sweep(args)

    assert result["passed"] is True
    assert result["first_passing_deadline_us"] == 4000.0
    assert [row["passed"] for row in result["rows"]] == [False, False, True, True]
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert json.loads((tmp_path / "sweep.json").read_text(encoding="utf-8"))[
        "first_passing_deadline_us"
    ] == 4000.0


def test_slack_sweep_reports_no_passing_deadline(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload())
    _write_json(
        measured_copy_path,
        {
            "rows": [
                {
                    "direction": "h2d",
                    "pinned": True,
                    "experts": 4,
                    "p95_ms": 4.0,
                }
            ]
        },
    )

    args = module.build_parser().parse_args(
        [
            "--issue-plan-gate-json",
            str(gate_path),
            "--measured-copy-json",
            str(measured_copy_path),
            "--measured-copy-experts",
            "4",
            "--deadline-us-values",
            "0,100,200",
            "--output-json",
            str(tmp_path / "sweep.json"),
        ]
    )
    result = module.run_slack_sweep(args)

    assert result["passed"] is False
    assert result["first_passing_deadline_us"] is None
    assert all(not row["passed"] for row in result["rows"])


def test_slack_sweep_rejects_unsorted_deadlines():
    module = _load_module()

    with pytest.raises(ValueError, match="ascending"):
        module._parse_deadlines("1000,200,500")  # noqa: SLF001
