from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_future_wna16_typed_slot_payloadless_useful_ab_repeats.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_future_wna16_typed_slot_payloadless_useful_ab_repeats",
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


def _comparison(
    *,
    repeat_id: int = 0,
    baseline_tpot: float = 1.0,
    candidate_tpot: float = 0.99,
) -> dict:
    speedup = baseline_tpot / candidate_tpot
    return {
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_ab_comparison",
        "passed": True,
        "failures": [],
        "comparison_ready": True,
        "measures_tpot": True,
        "measures_vllm_latency": True,
        "performance_claim_ready": True,
        "candidate_faster": True,
        "baseline_tpot": baseline_tpot,
        "candidate_tpot": candidate_tpot,
        "speedup_vs_baseline": speedup,
        "improvement_pct": (1.0 - candidate_tpot / baseline_tpot) * 100.0,
        "expected_gpu": 1,
        "expected_sample_count": 32,
        "expected_requested_output_token_count": 2048,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "baseline_json": f"/tmp/baseline_{repeat_id}.json",
        "candidate_json": f"/tmp/candidate_{repeat_id}.json",
        "baseline_sha256": f"baseline-sha-{repeat_id}",
        "candidate_sha256": f"candidate-sha-{repeat_id}",
        "baseline": {"trace_dir": f"/tmp/baseline_{repeat_id}"},
        "candidate": {"trace_dir": f"/tmp/candidate_{repeat_id}"},
    }


def _decision_gate() -> dict:
    return {
        "artifact_kind": "payloadless_live_config_performance_decision_gate",
        "decision_name": "premap_payloadless_live_config_performance_decision_v1",
        "passed": True,
        "failures": [],
        "freeze_payloadless_live_config_performance_claim": True,
        "payloadless_live_config_status": "safe_participation_path_not_performance_mainline",
        "real_performance_next_path": "future_typed_slot_useful_consumer_or_payload_cache_manager",
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
    }


def _run(module, inputs: list[Path], output: Path, *extra: str) -> dict:
    decision = output.parent / "decision_gate.json"
    _write_json(decision, _decision_gate())
    args = module.build_parser().parse_args(
        [
            "--inputs",
            *[str(path) for path in inputs],
            "--decision-gate-json",
            str(decision),
            "--output-json",
            str(output),
            *extra,
        ]
    )
    return module.build_summary(args)


def test_payloadless_ab_repeat_summary_blocks_positive_repeats(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx, candidate_tpot in enumerate([0.99, 0.985, 0.98]):
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, _comparison(repeat_id=idx, candidate_tpot=candidate_tpot))
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert result["repeat_count"] == 3
    assert result["positive_all_repeats"] is True
    assert result["performance_claim_ready"] is False
    assert result["payloadless_live_config_performance_claim_frozen"] is True
    assert result["payloadless_repeat_summary_allowed"] is False
    assert "payloadless_repeat_summary_blocked_by_decision_gate" in result["failures"]
    assert result["speedup_stats"]["count"] == 3
    assert result["speedup_stats"]["min"] > 1.0
    assert result["kernel_arg_pass_allowed"] is False


def test_payloadless_ab_repeat_summary_rejects_unmeasured_repeat(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx in range(3):
        payload = _comparison(repeat_id=idx)
        if idx == 1:
            payload["measures_tpot"] = False
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert any("measures_tpot_not_true" in item for item in result["failures"])


def test_payloadless_ab_repeat_summary_rejects_nonpositive_repeat(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx, candidate_tpot in enumerate([0.99, 1.01, 0.98]):
        payload = _comparison(repeat_id=idx, candidate_tpot=candidate_tpot)
        if candidate_tpot > 1.0:
            payload["candidate_faster"] = False
            payload["speedup_vs_baseline"] = 1.0 / candidate_tpot
            payload["improvement_pct"] = (1.0 - candidate_tpot) * 100.0
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert "not_positive_all_repeats" in result["failures"]


def test_payloadless_ab_repeat_summary_rejects_kernel_arg_pass(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx in range(3):
        payload = _comparison(repeat_id=idx)
        if idx == 2:
            payload["kernel_arg_pass_allowed"] = True
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert any("kernel_arg_pass_allowed_not_false" in item for item in result["failures"])


def test_payloadless_ab_repeat_summary_rejects_payload_bytes(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx in range(3):
        payload = _comparison(repeat_id=idx)
        if idx == 1:
            payload["payload_bytes"] = 1
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert any("payload_bytes_not_zero" in item for item in result["failures"])


def test_payloadless_ab_repeat_summary_rejects_duplicate_inputs(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "repeat0.json"
    _write_json(path, _comparison(repeat_id=0))

    result = _run(module, [path, path, path], tmp_path / "out.json")

    assert result["passed"] is False
    assert "duplicate_input_paths" in result["failures"]


def test_payloadless_ab_repeat_summary_rejects_duplicate_trace_dirs(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx in range(3):
        payload = _comparison(repeat_id=idx)
        if idx == 2:
            payload["candidate"]["trace_dir"] = "/tmp/candidate_1"
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_trace_dir_not_unique" in result["failures"]


def test_payloadless_ab_repeat_summary_rejects_context_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx in range(3):
        payload = _comparison(repeat_id=idx)
        if idx == 1:
            payload["expected_sample_count"] = 16
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert any("expected_sample_count_mismatch" in item for item in result["failures"])


def test_payloadless_ab_repeat_summary_rejects_duplicate_sha(tmp_path: Path) -> None:
    module = _load_module()
    inputs = []
    for idx in range(3):
        payload = _comparison(repeat_id=idx)
        if idx == 2:
            payload["candidate_sha256"] = "candidate-sha-1"
        path = tmp_path / f"repeat{idx}.json"
        _write_json(path, payload)
        inputs.append(path)

    result = _run(module, inputs, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_sha256_not_unique" in result["failures"]
