from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _gate_payload(*, experts=(3, 5), unsafe: bool = False) -> dict:
    issue_hash = _load_module()._issue_hash(list(experts))  # noqa: SLF001
    payload = {
        "passed": True,
        "issue_plan_ready": True,
        "payload_cache_issue_plan_candidate": True,
        "native_issue_plan_valid": True,
        "runtime_contract_ready": True,
        "issue_candidate_count": len(experts),
        "issue_candidate_hash": issue_hash,
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
    if unsafe:
        payload["payload_transfer_enabled"] = True
    return payload


def _run(module, gate_path: Path, output_path: Path, extra_args: list[str] | None = None):
    args_list = [
        "--issue-plan-gate-json",
        str(gate_path),
        "--output-json",
        str(output_path),
    ]
    if extra_args:
        args_list.extend(extra_args)
    args = module.build_parser().parse_args(args_list)
    return module.run_issue_plan_executor(args)


def test_issue_plan_executor_accepts_ready_time_hit(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _gate_payload(experts=(3, 5)))

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        ["--queue-batch-size", "2"],
    )

    assert result["passed"] is True
    assert result["issue_executor_ready"] is True
    assert result["issue_candidate_count"] == 2
    assert result["issued_prefetch_count"] == 2
    assert result["demand_count"] == 2
    assert result["demand_hit_count"] == 2
    assert result["demand_hit_rate"] == 1.0
    assert result["used_per_issued_fetch"] == 1.0
    assert result["ready_late_miss_count"] == 0
    assert result["deadline_window_model_only"] is True
    assert result["same_arrival_demand_model"] is True
    assert result["real_ready_credit_granted"] is False
    assert result["real_payload_ready_hit_count"] == 0
    assert result["payload_bytes"] == 0
    assert result["payload_transfer_enabled"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_issue_plan_executor_rejects_late_ready_miss(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _gate_payload(experts=(3,)))

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        [
            "--service-us-per-issue",
            "1000",
            "--queue-deadline-us",
            "10",
            "--min-demand-hit-rate",
            "0.5",
            "--max-ready-late-miss-rate",
            "0.2",
            "--min-used-per-issued-fetch",
            "0.5",
        ],
    )

    assert result["passed"] is False
    assert "demand_hit_rate_below_threshold" in result["failures"]
    assert "ready_late_miss_rate_above_threshold" in result["failures"]
    assert "used_per_issued_fetch_below_threshold" in result["failures"]
    assert result["ready_late_miss_count"] == 1


def test_issue_plan_executor_uses_measured_copy_envelope(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload(experts=tuple(range(8))))
    _write_json(
        measured_copy_path,
        {
            "rows": [
                {
                    "direction": "h2d",
                    "pinned": True,
                    "experts": 8,
                    "p95_ms": 16.0,
                    "p95_gbps": 0.8,
                }
            ]
        },
    )

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        [
            "--measured-copy-json",
            str(measured_copy_path),
            "--measured-copy-stat",
            "p95",
            "--measured-copy-experts",
            "8",
            "--measured-copy-pinned",
            "true",
            "--queue-deadline-us",
            "200",
        ],
    )

    assert result["passed"] is False
    assert result["measured_copy_model_enabled"] is True
    assert result["measured_copy_us_per_batch"] == 16000.0
    assert result["measured_copy_us_per_issue"] == 2000.0
    assert result["measured_copy_effective_gbps"] == 0.8
    assert result["measured_copy_expert_count_matches_issue_plan"] is True
    assert result["full_fetch_allowed"] is False
    assert result["full_fetch_block_reason"] == "measured_copy_deadline_miss"
    assert result["queue_batch_size"] == 8
    assert "demand_hit_rate_below_threshold" in result["failures"]
    assert result["real_payload_ready_hit_count"] == 0


def test_issue_plan_executor_rejects_missing_measured_copy_row(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload(experts=(3,)))
    _write_json(
        measured_copy_path,
        {"rows": [{"direction": "d2h", "pinned": True, "experts": 1, "p95_ms": 1.0}]},
    )

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        ["--measured-copy-json", str(measured_copy_path)],
    )

    assert result["passed"] is False
    assert any(
        failure.startswith("measured_copy_select_failed")
        for failure in result["failures"]
    )
    assert result["full_fetch_allowed"] is False
    assert result["full_fetch_block_reason"] == "measured_copy_invalid"


def test_issue_plan_executor_rejects_measured_copy_issue_count_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload(experts=tuple(range(8))))
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

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        [
            "--measured-copy-json",
            str(measured_copy_path),
            "--measured-copy-experts",
            "4",
            "--measured-copy-pinned",
            "true",
        ],
    )

    assert result["passed"] is False
    assert "measured_copy_expert_count_issue_plan_mismatch" in result["failures"]
    assert result["measured_copy_expert_count_matches_issue_plan"] is False
    assert result["full_fetch_block_reason"] == "measured_copy_issue_plan_mismatch"


def test_issue_plan_executor_rejects_invalid_measured_copy_pinned_filter(
    tmp_path: Path,
):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload(experts=(3,)))
    _write_json(
        measured_copy_path,
        {"rows": [{"direction": "h2d", "pinned": True, "experts": 1, "p95_ms": 1.0}]},
    )

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        ["--measured-copy-json", str(measured_copy_path), "--measured-copy-pinned", "maybe"],
    )

    assert result["passed"] is False
    assert result["full_fetch_block_reason"] == "measured_copy_invalid"


def test_issue_plan_executor_rejects_nonpositive_measured_copy_time(
    tmp_path: Path,
):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    measured_copy_path = tmp_path / "measured_copy.json"
    _write_json(gate_path, _gate_payload(experts=(3,)))
    _write_json(
        measured_copy_path,
        {"rows": [{"direction": "h2d", "pinned": True, "experts": 1, "p95_ms": 0.0}]},
    )

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        ["--measured-copy-json", str(measured_copy_path)],
    )

    assert result["passed"] is False
    assert result["full_fetch_block_reason"] == "measured_copy_invalid"


def test_issue_plan_executor_rejects_unsafe_gate(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _gate_payload(unsafe=True))

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "issue_gate_payload_transfer_enabled_not_false" in result["failures"]


def test_issue_plan_executor_rejects_gate_count_hash_mismatch(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    payload = _gate_payload(experts=(3, 5))
    payload["issue_candidate_count"] = 8
    payload["issue_candidate_hash"] = "0000000000000000"
    _write_json(gate_path, payload)

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "issue_gate_count_expert_list_mismatch" in result["failures"]
    assert "issue_gate_hash_expert_list_mismatch" in result["failures"]


def test_issue_plan_executor_rejects_empty_issue(tmp_path: Path):
    module = _load_module()
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _gate_payload(experts=()))

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "issue_gate_count_not_positive" in result["failures"]
