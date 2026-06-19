from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_payloadless_useful_candidate_tpot_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_candidate_tpot_benchmark",
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


def _gate(trace_config: Path, trace_dir: Path) -> dict:
    return {
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_candidate_config_gate",
        "gate_name": "premap_future_wna16_typed_slot_payloadless_useful_candidate_config_gate_v1",
        "gate_mode": "production_compatible_live_config_without_router_recorder",
        "passed": True,
        "failures": [],
        "payloadless_useful_candidate_config_ready": True,
        "live_config_without_router_recorder": True,
        "runtime_shadow_enabled": False,
        "record_router_topk": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "next_runtime_stage": "run_payloadless_useful_candidate_tpot_artifact",
        "trace_config": str(trace_config),
        "trace_config_sha256": _sha256(trace_config),
        "output_dir": str(trace_dir),
    }


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _performance_summary(**overrides) -> dict:
    payload = {
        "generate_seconds_per_requested_output_token": 0.006,
        "generate_wall_seconds": 12.288,
        "total_trace_wall_seconds": 20.0,
        "requested_output_token_count": 2048,
        "sample_count": 32,
        "input_token_count": 1626,
        "llm_init_wall_seconds": 3.0,
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
        "runtime_shadow_capture_router_topk": False,
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled": False,
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled": False,
        "runtime_shadow_premap_native_typed_consumer_input_export_enabled": False,
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled": False,
        "runtime_shadow_premap_payload_cache_manager_demand_on_consumer": False,
        "runtime_shadow_premap_payload_cache_manager_emit_consumer_rows": False,
        "runtime_shadow_premap_live_config_without_router_recorder_enabled": True,
        "runtime_shadow_premap_live_config_without_router_recorder_allowed": True,
        "runtime_shadow_premap_kernel_arg_handoff_live_enabled": True,
        "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected": True,
        "runtime_shadow_decoder_source_timing_mode": "off",
        "runtime_shadow_moe_source_timing_mode": "off",
        "runtime_shadow_outcome_logging_mode": "off",
        "runtime_shadow_premap_kernel_arg_handoff_live_counter_mode": "off",
        "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
    }
    payload.update(overrides)
    return payload


def _run(module, gate_json: Path, output_json: Path, *extra: str) -> dict:
    args = module.build_parser().parse_args(
        [
            "--config-gate-json",
            str(gate_json),
            "--output-json",
            str(output_json),
            *extra,
        ]
    )
    return module.run_candidate_tpot_benchmark(args)


def test_candidate_tpot_wrapper_accepts_payloadless_live_config_summary(tmp_path: Path) -> None:
    module = _load_module()
    trace_config = tmp_path / "trace.yaml"
    trace_config.write_text("trace:\n  runtime_shadow: {}\n", encoding="utf-8")
    trace_dir = tmp_path / "trace"
    _write_json(trace_dir / "performance_summary.json", _performance_summary())
    gate = tmp_path / "gate.json"
    _write_json(gate, _gate(trace_config, trace_dir))

    result = _run(module, gate, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["production_like_tpot_candidate_ready"] is True
    assert result["benchmark_mode"] == "production_like_payloadless_useful_candidate"
    assert result["benchmark_is_current_vllm_baseline"] is False
    assert result["benchmark_is_future_typed_slot_useful_path"] is True
    assert result["payloadless_useful_mode_enabled"] is True
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["tokens_per_second"] == 1.0 / 0.006


def test_candidate_tpot_wrapper_rejects_missing_live_config_summary(tmp_path: Path) -> None:
    module = _load_module()
    trace_config = tmp_path / "trace.yaml"
    trace_config.write_text("trace:\n  runtime_shadow: {}\n", encoding="utf-8")
    trace_dir = tmp_path / "trace"
    _write_json(
        trace_dir / "performance_summary.json",
        _performance_summary(
            runtime_shadow_premap_live_config_without_router_recorder_enabled=False
        ),
    )
    gate = tmp_path / "gate.json"
    _write_json(gate, _gate(trace_config, trace_dir))

    result = _run(module, gate, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "performance_summary_runtime_shadow_premap_live_config_without_router_recorder_enabled_not_true"
        in result["failures"]
    )


def test_candidate_tpot_wrapper_rejects_kernel_arg_pass(tmp_path: Path) -> None:
    module = _load_module()
    trace_config = tmp_path / "trace.yaml"
    trace_config.write_text("trace:\n  runtime_shadow: {}\n", encoding="utf-8")
    trace_dir = tmp_path / "trace"
    _write_json(
        trace_dir / "performance_summary.json",
        _performance_summary(
            runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled=True
        ),
    )
    gate = tmp_path / "gate.json"
    _write_json(gate, _gate(trace_config, trace_dir))

    result = _run(module, gate, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "performance_summary_runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled_not_false"
        in result["failures"]
    )


def test_candidate_tpot_wrapper_rejects_unbound_trace_dir(tmp_path: Path) -> None:
    module = _load_module()
    trace_config = tmp_path / "trace.yaml"
    trace_config.write_text("trace:\n  runtime_shadow: {}\n", encoding="utf-8")
    trace_dir = tmp_path / "trace"
    other_trace_dir = tmp_path / "other"
    _write_json(other_trace_dir / "performance_summary.json", _performance_summary())
    gate = tmp_path / "gate.json"
    _write_json(gate, _gate(trace_config, trace_dir))

    result = _run(module, gate, tmp_path / "out.json", "--trace-dir", str(other_trace_dir))

    assert result["passed"] is False
    assert "trace_dir_not_bound_to_config_gate" in result["failures"]
