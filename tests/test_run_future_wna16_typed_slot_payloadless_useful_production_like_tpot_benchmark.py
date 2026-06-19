from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_payloadless_useful_production_like_tpot_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_production_like_tpot_benchmark",
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


def _write_text(path: Path, content: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _timing_gate_payload(module, *, trace_config: Path, trace_dir: Path) -> dict:
    _write_text(trace_config, "model: x\ntrace: {}\n")
    payload = dict(module.EXPECTED_GATE_FLAGS)
    payload.update(
        {
            "trace_config": str(trace_config),
            "trace_config_sha256": module._sha256(trace_config),  # noqa: SLF001
            "trace_config_summary": {"output_dir": str(trace_dir)},
        }
    )
    return payload


def _performance_summary() -> dict:
    return {
        "generate_seconds_per_requested_output_token": 0.01,
        "generate_wall_seconds": 10.0,
        "total_trace_wall_seconds": 20.0,
        "requested_output_token_count": 1000,
        "sample_count": 32,
        "input_token_count": 512,
        "llm_init_wall_seconds": 5.0,
        "decode_workload_trace_enabled": False,
        "runtime_shadow_enabled": False,
        "runtime_shadow_record_router_topk": False,
        "runtime_shadow_emit_decoder_layer_timing": False,
        "runtime_shadow_emit_decoder_component_timing": False,
        "runtime_shadow_emit_moe_substage_timing": False,
        "runtime_shadow_emit_engine_timing": False,
        "runtime_shadow_emit_wna16_kernel_timing": False,
        "runtime_shadow_emit_premap_summaries": False,
        "runtime_shadow_emit_premap_consumer_mapping": False,
        "runtime_shadow_premap_kernel_arg_handoff_live_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected": False,
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": False,
        "runtime_shadow_decoder_source_timing_mode": "off",
        "runtime_shadow_moe_source_timing_mode": "off",
        "runtime_shadow_outcome_logging_mode": "off",
    }


def _run(module, gate_path: Path, output_path: Path, *extra: str) -> dict:
    args = module.build_parser().parse_args(
        [
            "--timing-gate-json",
            str(gate_path),
            "--output-json",
            str(output_path),
            *extra,
        ]
    )
    return module.run_production_like_tpot_benchmark(args)


def test_production_like_tpot_benchmark_reuses_existing_perf(tmp_path: Path):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    trace_config = tmp_path / "trace.yaml"
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir))
    _write_json(trace_dir / "performance_summary.json", _performance_summary())

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["production_like_tpot_baseline_ready"] is True
    assert result["run_requested"] is False
    assert result["run_executed"] is False
    assert result["measures_tpot"] is True
    assert result["tokens_per_second"] == 100.0
    assert result["payloadless_useful_mode_enabled"] is False
    assert result["benchmark_is_current_vllm_baseline"] is True
    assert result["benchmark_is_future_typed_slot_useful_path"] is False


def test_production_like_tpot_benchmark_rejects_failed_gate(tmp_path: Path):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    trace_config = tmp_path / "trace.yaml"
    gate = _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir)
    gate["passed"] = False
    gate["failures"] = ["x"]
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, gate)
    _write_json(trace_dir / "performance_summary.json", _performance_summary())

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "timing_gate_passed_mismatch" in result["failures"]
    assert "timing_gate_failures_mismatch" in result["failures"]
    assert result["measures_tpot"] is False


def test_production_like_tpot_benchmark_rejects_missing_perf(tmp_path: Path):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    trace_config = tmp_path / "trace.yaml"
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir))

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "performance_summary_missing" in result["failures"]


def test_production_like_tpot_benchmark_rejects_bad_perf(tmp_path: Path):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    trace_config = tmp_path / "trace.yaml"
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir))
    perf = _performance_summary()
    perf["generate_seconds_per_requested_output_token"] = 0.0
    _write_json(trace_dir / "performance_summary.json", perf)

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "generate_seconds_per_requested_output_token_invalid" in result["failures"]


def test_production_like_tpot_benchmark_rejects_trace_dir_mismatch(tmp_path: Path):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    other_trace_dir = tmp_path / "other_trace"
    trace_config = tmp_path / "trace.yaml"
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir))
    _write_json(other_trace_dir / "performance_summary.json", _performance_summary())

    result = _run(
        module,
        gate_path,
        tmp_path / "out.json",
        "--trace-dir",
        str(other_trace_dir),
    )

    assert result["passed"] is False
    assert "trace_dir_not_bound_to_timing_gate" in result["failures"]
    assert result["measures_tpot"] is False


def test_production_like_tpot_benchmark_rejects_heavy_perf_summary(tmp_path: Path):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    trace_config = tmp_path / "trace.yaml"
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir))
    perf = _performance_summary()
    perf["runtime_shadow_enabled"] = True
    perf["decode_workload_trace_enabled"] = True
    _write_json(trace_dir / "performance_summary.json", perf)

    result = _run(module, gate_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "performance_summary_runtime_shadow_enabled_not_false" in result["failures"]
    assert "performance_summary_decode_workload_trace_enabled_not_false" in result["failures"]


def test_production_like_tpot_benchmark_does_not_run_when_gate_fails(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    trace_dir = tmp_path / "trace"
    trace_config = tmp_path / "trace.yaml"
    gate = _timing_gate_payload(module, trace_config=trace_config, trace_dir=trace_dir)
    gate["passed"] = False
    gate["failures"] = ["x"]
    gate_path = tmp_path / "gate.json"
    _write_json(gate_path, gate)

    def fail_run(**_kwargs):
        raise AssertionError("_run_trace must not be called when timing gate failed")

    monkeypatch.setattr(module, "_run_trace", fail_run)
    result = _run(module, gate_path, tmp_path / "out.json", "--run")

    assert result["passed"] is False
    assert result["run_requested"] is True
    assert result["run_executed"] is False
    assert "trace_run_skipped_due_to_gate_failure" in result["failures"]
