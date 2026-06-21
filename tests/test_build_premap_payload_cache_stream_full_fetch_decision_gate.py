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
        "issue_lead_tokens": 1 if passed else 0,
        "lookahead_us": lookahead,
        "model_passed": passed,
        "passed": passed,
        "failures": [] if passed else ["demand_hit_rate_below_threshold"],
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
        "failures": [],
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


def _queue_budget_payload() -> dict:
    shifted_issue_accounting = {
        "shifted_issue_accounting_enabled": True,
        "shifted_issue_lead_tokens": 1,
        "shifted_issue_clamped_issue_count": 1,
        "shifted_issue_duplicate_issue_key_count": 0,
        "shifted_issue_unique_issue_key_count": 4,
        "shifted_issue_accounted_packet_count": 4,
        "shifted_issue_invalid_export_count": 0,
        "shifted_issue_row_shift_mismatch_count": 0,
        "shifted_issue_row_clamp_mismatch_count": 0,
    }
    first_row = {
        **_row(lookahead=75_000.0, passed=True),
        **shifted_issue_accounting,
    }
    first_cell = {
        "capacity": 128,
        "queue_deadline_us": 200.0,
        "issue_lead_tokens": 1,
        "lookahead_us": 75_000.0,
        "shifted_issue_accounting": dict(shifted_issue_accounting),
        "cell_index": 1,
    }
    return {
        **_safe_fields(),
        "artifact_kind": "premap_payload_cache_issue_stream_executor_queue_budget_sweep",
        "passed": True,
        "failures": [],
        "first_passing_cell": first_cell,
        "first_model_passing_cell": first_cell,
        "cells": [
            {
                **_safe_fields(),
                "capacity": 64,
                "queue_deadline_us": 200.0,
                "model_passed": False,
                "child_passed": False,
                "passed": False,
                "failures": [],
                "first_model_passing_issue_lead_tokens": None,
                "first_model_passing_lookahead_us": None,
                "first_passing_row": None,
                "row_count": 1,
                "rows": [_row(lookahead=0.0, passed=False)],
                "safety_passed": True,
                "safety_failures": [],
            },
            {
                **_safe_fields(),
                "capacity": 128,
                "queue_deadline_us": 200.0,
                "model_passed": True,
                "child_passed": True,
                "passed": True,
                "failures": [],
                "first_model_passing_issue_lead_tokens": 1,
                "first_model_passing_lookahead_us": 75_000.0,
                "first_passing_row": first_row,
                "first_passing_shifted_issue_accounting": dict(
                    shifted_issue_accounting
                ),
                "row_count": 1,
                "rows": [first_row],
                "safety_passed": True,
                "safety_failures": [],
            },
        ],
    }


def _run(
    module,
    sweep_path: Path,
    output_path: Path,
    *,
    lookahead: float = 0.0,
    queue_deadline: float = 200.0,
    queue_budget_path: Path | None = None,
) -> dict:
    argv = [
        "--stream-lookahead-sweep-json",
        str(sweep_path),
        "--current-lookahead-us",
        str(lookahead),
        "--current-queue-deadline-us",
        str(queue_deadline),
        "--output-json",
        str(output_path),
    ]
    if queue_budget_path is not None:
        argv.extend(["--queue-budget-sweep-json", str(queue_budget_path)])
    args = module.build_parser().parse_args(argv)
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


def test_stream_full_fetch_decision_rejects_bool_payload_bytes(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["payload_bytes"] = False
    _write_json(sweep_path, payload)

    result = _run(module, sweep_path, tmp_path / "decision.json")

    assert result["passed"] is False
    assert "stream_lookahead_sweep_payload_bytes_not_zero" in result["failures"]


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


def test_stream_full_fetch_decision_rejects_stream_row_failures(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["rows"][1]["failures"] = ["row_should_not_pass"]
    _write_json(sweep_path, payload)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        lookahead=200_000.0,
    )

    assert result["passed"] is False
    assert "stream_lookahead_row_1_passed_with_failures" in result["failures"]


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


def test_stream_full_fetch_decision_includes_queue_budget_gate(tmp_path: Path):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, _queue_budget_payload())

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is True
    assert result["queue_budget_gate_present"] is True
    assert result["queue_budget_sweep_json"] == str(queue_budget_path)
    assert result["required_queue_capacity"] == 128
    assert result["required_queue_deadline_us"] == 200.0
    assert result["required_issue_lead_tokens"] == 1
    assert result["queue_budget_required_capacity"] == 128
    assert result["queue_budget_required_deadline_us"] == 200.0
    assert result["queue_budget_required_issue_lead_tokens"] == 1
    assert result["queue_budget_first_passing_shifted_issue_accounting"][
        "shifted_issue_accounted_packet_count"
    ] == 4
    assert result["queue_budget_first_passing_cell"]["lookahead_us"] == 75_000.0
    assert result["required_shifted_issue_accounting"][
        "shifted_issue_lead_tokens"
    ] == 1
    assert result["payload_transfer_enabled"] is False
    assert result["passed_to_kernel"] is False


def test_stream_full_fetch_decision_rejects_unsafe_queue_budget_cell(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1]["payload_transfer_enabled"] = True
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_payload_transfer_enabled_not_false" in result[
        "failures"
    ]
    assert "queue_budget_cell_1_safety_passed_mismatch" in result["failures"]


def test_stream_full_fetch_decision_rejects_mismatched_queue_first_cell(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"]["capacity"] = 512
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_first_passing_cell_not_in_passing_cells" in result[
        "failures"
    ]


def test_stream_full_fetch_decision_rejects_queue_shifted_accounting_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"]["shifted_issue_accounting"][
        "shifted_issue_accounted_packet_count"
    ] = 99
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert (
        "queue_budget_cell_1_first_cell_shifted_issue_accounting_mismatch"
        in result["failures"]
    )


def test_stream_full_fetch_decision_rejects_incomplete_queue_shifted_accounting(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"]["shifted_issue_accounting"].pop(
        "shifted_issue_unique_issue_key_count"
    )
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert (
        "queue_budget_first_passing_cell_shifted_issue_accounting_"
        "shifted_issue_unique_issue_key_count_missing"
    ) in result["failures"]


def test_stream_full_fetch_decision_rejects_malformed_cell_shifted_accounting(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"].pop("shifted_issue_accounting")
    queue_budget["cells"][1]["first_passing_shifted_issue_accounting"] = "bad"
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert (
        "queue_budget_cell_1_first_passing_shifted_issue_accounting_invalid"
        in result["failures"]
    )


def test_stream_full_fetch_decision_rejects_partial_row_shifted_accounting(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"].pop("shifted_issue_accounting")
    queue_budget["cells"][1].pop("first_passing_shifted_issue_accounting")
    queue_budget["cells"][1]["first_passing_row"].pop(
        "shifted_issue_unique_issue_key_count"
    )
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert (
        "queue_budget_cell_1_first_passing_row_shifted_issue_accounting_"
        "shifted_issue_unique_issue_key_count_missing"
    ) in result["failures"]


def test_stream_full_fetch_decision_rejects_queue_cell_contract_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1]["child_passed"] = False
    queue_budget["cells"][1]["failures"] = ["child_row_failure"]
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_passed_with_failures" in result["failures"]
    assert "queue_budget_cell_1_passed_with_child_failed" in result["failures"]


def test_stream_full_fetch_decision_rejects_queue_cell_missing_child_passed(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1].pop("child_passed")
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_passed_with_child_failed" in result["failures"]


def test_stream_full_fetch_decision_rejects_malformed_queue_first_cell(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"]["capacity"] = "128"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_first_passing_cell_capacity_invalid" in result["failures"]


def test_stream_full_fetch_decision_rejects_queue_passed_model_failed(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1]["model_passed"] = False
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_passed_with_model_failed" in result["failures"]


def test_stream_full_fetch_decision_rejects_queue_first_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1]["first_passing_row"] = _row(
        lookahead=150_000.0,
        passed=True,
    )
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_first_passing_row_mismatch" in result["failures"]


def test_stream_full_fetch_decision_rejects_malformed_queue_cell_number(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1]["first_model_passing_issue_lead_tokens"] = True
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_first_model_passing_issue_lead_tokens_invalid" in result[
        "failures"
    ]


def test_stream_full_fetch_decision_rejects_fractional_queue_budget_ints(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"]["capacity"] = 128.5
    queue_budget["first_passing_cell"]["issue_lead_tokens"] = 1.5
    queue_budget["cells"][1]["capacity"] = 128.5
    queue_budget["cells"][1]["first_model_passing_issue_lead_tokens"] = 1.5
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_first_passing_cell_capacity_invalid" in result["failures"]
    assert "queue_budget_first_passing_cell_issue_lead_tokens_invalid" in result[
        "failures"
    ]
    assert "queue_budget_cell_1_capacity_invalid" in result["failures"]
    assert "queue_budget_cell_1_first_model_passing_issue_lead_tokens_invalid" in result[
        "failures"
    ]


def test_stream_full_fetch_decision_rejects_stream_top_level_failures(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["failures"] = ["row_0_payload_transfer_enabled_not_false"]
    _write_json(sweep_path, payload)

    result = _run(module, sweep_path, tmp_path / "decision.json")

    assert result["passed"] is False
    assert "stream_lookahead_sweep_row_0_payload_transfer_enabled_not_false" in result[
        "failures"
    ]


def test_stream_full_fetch_decision_rejects_queue_passing_row_model_failed(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["cells"][1]["rows"][0]["model_passed"] = False
    queue_budget["cells"][1]["first_passing_row"] = queue_budget["cells"][1]["rows"][0]
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_cell_1_row_0_passed_with_model_failed" in result["failures"]


def test_stream_full_fetch_decision_handles_bad_queue_first_cell_without_crash(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    queue_budget_path = tmp_path / "queue_budget.json"
    queue_budget = _queue_budget_payload()
    queue_budget["first_passing_cell"]["capacity"] = "bad"
    _write_json(sweep_path, _sweep_payload(first_lookahead=200_000.0))
    _write_json(queue_budget_path, queue_budget)

    result = _run(
        module,
        sweep_path,
        tmp_path / "decision.json",
        queue_budget_path=queue_budget_path,
    )

    assert result["passed"] is False
    assert "queue_budget_first_passing_cell_capacity_invalid" in result["failures"]
    assert "queue_budget_first_passing_cell_not_in_passing_cells" in result[
        "failures"
    ]


def test_stream_full_fetch_decision_rejects_stream_bool_numeric_fields(
    tmp_path: Path,
):
    module = _load_module()
    sweep_path = tmp_path / "stream_lookahead.json"
    payload = _sweep_payload(first_lookahead=200_000.0)
    payload["first_model_passing_lookahead_us"] = True
    _write_json(sweep_path, payload)

    result = _run(module, sweep_path, tmp_path / "decision.json")

    assert result["passed"] is False
    assert "first_model_passing_lookahead_us_invalid" in result["failures"]
