from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_future_wna16_typed_slot_payloadless_useful_ab_comparison.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_future_wna16_typed_slot_payloadless_useful_ab_comparison",
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


def _artifact(*, role: str, tpot: float = 0.01) -> dict:
    is_baseline = role == "baseline"
    return {
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_production_like_tpot_benchmark",
        "benchmark_mode": "production_like_baseline_only" if is_baseline else "production_like_payloadless_useful_candidate",
        "benchmark_is_current_vllm_baseline": is_baseline,
        "benchmark_is_future_typed_slot_useful_path": not is_baseline,
        "production_like_tpot_baseline_ready": is_baseline,
        "production_like_tpot_candidate_ready": not is_baseline,
        "payloadless_useful_mode_enabled": not is_baseline,
        "next_runtime_stage": "implement_payloadless_useful_typed_slot_ab_comparison" if is_baseline else "compare_payloadless_useful_candidate_tpot",
        "passed": True,
        "failures": [],
        "measures_tpot": True,
        "measures_vllm_latency": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "generate_seconds_per_requested_output_token": tpot,
        "generate_wall_seconds": 20.0,
        "tokens_per_second": 1.0 / tpot,
        "sample_count": 32,
        "requested_output_token_count": 2048,
        "input_token_count": 1626,
        "gpu": "1",
        "trace_config": "/tmp/trace.yaml",
        "trace_config_sha256": "abc",
        "trace_dir": "/tmp/trace",
        "performance_summary_json": "/tmp/trace/performance_summary.json",
        "performance_summary_sha256": "def",
    }


def _run(module, baseline: Path, candidate: Path, output: Path, *extra: str) -> dict:
    args = module.build_parser().parse_args(
        [
            "--baseline-json",
            str(baseline),
            "--candidate-json",
            str(candidate),
            "--output-json",
            str(output),
            *extra,
        ]
    )
    return module.build_comparison(args)


def test_ab_comparison_passes_positive_payloadless_candidate(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    _write_json(candidate, _artifact(role="candidate", tpot=0.009))

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["comparison_ready"] is True
    assert result["candidate_faster"] is True
    assert result["performance_claim_ready"] is True
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["speedup_vs_baseline"] == 0.010 / 0.009


def test_ab_comparison_rejects_missing_candidate(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline"))

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert result["comparison_ready"] is False
    assert "candidate_json_missing" in result["failures"]


def test_ab_comparison_rejects_baseline_only_candidate(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    _write_json(candidate, _artifact(role="baseline", tpot=0.009))

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_benchmark_is_current_vllm_baseline_mismatch" in result["failures"]
    assert "candidate_benchmark_is_future_typed_slot_useful_path_mismatch" in result["failures"]
    assert "candidate_payloadless_useful_mode_enabled_mismatch" in result["failures"]


def test_ab_comparison_rejects_contradictory_baseline_mode_candidate(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload["benchmark_mode"] = "production_like_baseline_only"
    _write_json(candidate, candidate_payload)

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_benchmark_mode_mismatch" in result["failures"]


def test_ab_comparison_rejects_context_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload["requested_output_token_count"] = 1024
    _write_json(candidate, candidate_payload)

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "context_requested_output_token_count_mismatch" in result["failures"]
    assert "candidate_expected_requested_output_token_count_mismatch" in result["failures"]


def test_ab_comparison_rejects_missing_input_token_count(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload.pop("input_token_count")
    _write_json(candidate, candidate_payload)

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_input_token_count_invalid" in result["failures"]
    assert "context_input_token_count_mismatch" in result["failures"]


def test_ab_comparison_rejects_non_integral_input_token_count(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload["input_token_count"] = 1626.9
    _write_json(candidate, candidate_payload)

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_input_token_count_invalid" in result["failures"]
    assert "context_input_token_count_mismatch" in result["failures"]


def test_ab_comparison_rejects_gpu_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload["gpu"] = "0"
    _write_json(candidate, candidate_payload)

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "context_gpu_mismatch" in result["failures"]
    assert "candidate_expected_gpu_mismatch" in result["failures"]


def test_ab_comparison_can_require_trace_config_sha_match(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload["trace_config_sha256"] = "different"
    _write_json(candidate, candidate_payload)

    result = _run(
        module,
        baseline,
        candidate,
        tmp_path / "out.json",
        "--require-same-trace-config-sha",
    )

    assert result["passed"] is False
    assert "context_trace_config_sha256_mismatch" in result["failures"]


def test_ab_comparison_rejects_safety_field_regression(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    candidate_payload = _artifact(role="candidate", tpot=0.009)
    candidate_payload["kernel_arg_pass_allowed"] = True
    _write_json(candidate, candidate_payload)

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert "candidate_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_ab_comparison_rejects_nonpositive_candidate_by_default(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    _write_json(candidate, _artifact(role="candidate", tpot=0.011))

    result = _run(module, baseline, candidate, tmp_path / "out.json")

    assert result["passed"] is False
    assert result["candidate_faster"] is False
    assert "candidate_not_faster_than_baseline" in result["failures"]


def test_ab_comparison_can_report_nonpositive_candidate_when_allowed(tmp_path: Path) -> None:
    module = _load_module()
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_json(baseline, _artifact(role="baseline", tpot=0.010))
    _write_json(candidate, _artifact(role="candidate", tpot=0.011))

    result = _run(
        module,
        baseline,
        candidate,
        tmp_path / "out.json",
        "--allow-nonpositive-candidate",
    )

    assert result["passed"] is False
    assert result["candidate_faster"] is False
    assert result["performance_claim_ready"] is False
    assert result["diagnostic_only"] is True
    assert "candidate_not_faster_than_baseline_diagnostic_only" in result["failures"]
