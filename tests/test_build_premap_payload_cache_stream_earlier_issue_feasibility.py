from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_premap_payload_cache_stream_earlier_issue_feasibility.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_premap_payload_cache_stream_earlier_issue_feasibility",
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


def _decision_payload(
    *,
    required_lookahead: float = 200_000.0,
    current_lookahead: float = 0.0,
) -> dict:
    return {
        "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
        "passed": True,
        "failures": [],
        "required_stream_lookahead_us": required_lookahead,
        "current_lookahead_us": current_lookahead,
        "full_fetch_runtime_allowed": False,
        "metadata_premap_runtime_preferred": current_lookahead < required_lookahead,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
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


def _run(
    module,
    decision_path: Path,
    output_path: Path,
    *,
    token_values: str = "50000,100000",
    layer_count: int = 40,
    max_lead_tokens: int = 4,
) -> dict:
    args = module.build_parser().parse_args(
        [
            "--decision-gate-json",
            str(decision_path),
            "--decode-token-us-values",
            token_values,
            "--decoder-layer-count",
            str(layer_count),
            "--max-candidate-lead-tokens",
            str(max_lead_tokens),
            "--output-json",
            str(output_path),
        ]
    )
    return module.build_stream_earlier_issue_feasibility(args)


def test_earlier_issue_feasibility_quantifies_token_and_layer_lead(tmp_path: Path):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    output_path = tmp_path / "feasibility.json"
    _write_json(decision_path, _decision_payload(required_lookahead=200_000.0))

    result = _run(module, decision_path, output_path)

    assert result["passed"] is True
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "insufficient_stream_lookahead"
    assert result["metadata_premap_runtime_preferred"] is True
    assert result["min_required_lead_tokens"] == 2
    assert result["max_required_lead_tokens"] == 4
    assert result["feasible_within_configured_token_window"] is True
    assert result["rows"][0]["required_lead_tokens"] == 4
    assert result["rows"][0]["required_lead_layer_stages"] == 160
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_earlier_issue_feasibility_keeps_runtime_disabled_when_model_satisfied(
    tmp_path: Path,
):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    _write_json(
        decision_path,
        _decision_payload(required_lookahead=200_000.0, current_lookahead=250_000.0),
    )

    result = _run(module, decision_path, tmp_path / "feasibility.json")

    assert result["passed"] is True
    assert result["current_runtime_satisfies_model"] is True
    assert result["full_fetch_runtime_allowed"] is False
    assert result["full_fetch_block_reason"] == "real_payload_runtime_not_enabled"
    assert result["metadata_premap_runtime_preferred"] is False


def test_earlier_issue_feasibility_rejects_unsafe_decision_gate(tmp_path: Path):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    payload = _decision_payload(required_lookahead=200_000.0)
    payload["payload_transfer_enabled"] = True
    payload["full_fetch_runtime_allowed"] = True
    _write_json(decision_path, payload)

    result = _run(module, decision_path, tmp_path / "feasibility.json")

    assert result["passed"] is False
    assert "decision_gate_payload_transfer_enabled_not_false" in result["failures"]
    assert "decision_gate_full_fetch_runtime_allowed_not_false" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_earlier_issue_feasibility_rejects_bool_payload_bytes(tmp_path: Path):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    payload = _decision_payload(required_lookahead=200_000.0)
    payload["payload_bytes"] = False
    _write_json(decision_path, payload)

    result = _run(module, decision_path, tmp_path / "feasibility.json")

    assert result["passed"] is False
    assert "decision_gate_payload_bytes_not_zero" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_earlier_issue_feasibility_rejects_decision_failures_not_empty(
    tmp_path: Path,
):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    payload = _decision_payload(required_lookahead=200_000.0)
    payload["failures"] = ["synthetic_upstream_failure"]
    _write_json(decision_path, payload)

    result = _run(module, decision_path, tmp_path / "feasibility.json")

    assert result["passed"] is False
    assert "decision_gate_failures_not_empty" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_earlier_issue_feasibility_rejects_invalid_current_lookahead(
    tmp_path: Path,
):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    payload = _decision_payload(required_lookahead=200_000.0)
    payload["current_lookahead_us"] = -1.0
    _write_json(decision_path, payload)

    result = _run(module, decision_path, tmp_path / "feasibility.json")

    assert result["passed"] is False
    assert "current_lookahead_us_invalid" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_earlier_issue_feasibility_rejects_boolean_numeric_fields(
    tmp_path: Path,
):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    payload = _decision_payload(required_lookahead=200_000.0)
    payload["required_stream_lookahead_us"] = True
    payload["current_lookahead_us"] = False
    _write_json(decision_path, payload)

    result = _run(module, decision_path, tmp_path / "feasibility.json")

    assert result["passed"] is False
    assert "required_stream_lookahead_us_invalid" in result["failures"]
    assert "current_lookahead_us_invalid" in result["failures"]
    assert result["full_fetch_runtime_allowed"] is False


def test_earlier_issue_feasibility_rejects_unsorted_token_values(tmp_path: Path):
    module = _load_module()
    decision_path = tmp_path / "decision.json"
    _write_json(decision_path, _decision_payload(required_lookahead=200_000.0))
    args = module.build_parser().parse_args(
        [
            "--decision-gate-json",
            str(decision_path),
            "--decode-token-us-values",
            "100000,50000",
            "--output-json",
            str(tmp_path / "feasibility.json"),
        ]
    )

    try:
        module.build_stream_earlier_issue_feasibility(args)
    except ValueError as exc:
        assert "sorted" in str(exc)
    else:
        raise AssertionError("expected unsorted token values to be rejected")
