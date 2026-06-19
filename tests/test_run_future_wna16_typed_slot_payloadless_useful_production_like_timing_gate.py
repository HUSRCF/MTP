from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate",
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


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")


def _runtime_ablation_payload(module) -> dict:
    return {
        **module.EXPECTED_RUNTIME_ABLATION_FLAGS,
        "source_count": 128,
        "row_count": 5345,
        "row_ok_count": 5345,
        "rows_consumed": 5345,
        "repeat_count_measured": 3,
        "repeat_count_requested": 3,
        "field_names": list(module.FIELDS),
        "field_read_hashes": {
            "descriptor_ptr": "1111111111111111",
            "packed_weight_descriptor": "2222222222222222",
            "scale_metadata_handle": "3333333333333333",
            "aux_metadata_handle": "4444444444444444",
        },
        "repeat_benchmark_json": "",
        "repeat_benchmark_sha256": "",
    }


def _trace_config_payload() -> dict:
    return {
        "model": "configs/model/qwen3_6_35b_a3b_awq_4bit_prod_batch32_graph.yaml",
        "data": "configs/data/external_prompt_gate_dolly_128.yaml",
        "output_dir": "data/traces/prod_like",
        "trace": {
            "capture_router_topk": False,
            "capture_router_scores": False,
            "use_router_logits_recorder": False,
            "allow_missing_router_trace": True,
            "capture_hidden_states": "none",
            "capture_native_mtp_router": False,
            "max_samples": 32,
            "max_tokens": 64,
            "split_id": "test_prod_like",
            "runtime_shadow": {
                "enabled": False,
                "record_router_topk": False,
                "emit_transition_summaries": False,
                "emit_descriptor_order_summaries": False,
                "emit_summaries": False,
                "emit_outcomes": False,
                "outcome_logging_mode": "off",
                "emit_decoder_layer_timing": False,
                "emit_decoder_component_timing": False,
                "emit_moe_substage_timing": False,
                "emit_engine_timing": False,
                "emit_wna16_kernel_timing": False,
                "decoder_source_timing_mode": "off",
                "moe_source_timing_mode": "off",
                "descriptor_order_mapping_assertion_mode": "off",
                "descriptor_order_prelaunch_assertion_mode": "off",
                "descriptor_order_emit_consumer_handle_events": False,
                "descriptor_order_reorder_mvp_enabled": False,
                "premap_kernel_arg_handoff_live_enabled": False,
                "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
                "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
                "premap_descriptor_prep_enabled": False,
                "premap_consumer_shim_enabled": False,
                "premap_native_typed_consumer_bridge_enabled": False,
                "premap_future_wna16_typed_slot_payloadless_execution_enabled": False,
            },
        },
    }


def _run(module, runtime_path: Path, config_path: Path, output_path: Path) -> dict:
    args = module.build_parser().parse_args(
        [
            "--runtime-ablation-json",
            str(runtime_path),
            "--trace-config",
            str(config_path),
            "--output-json",
            str(output_path),
        ]
    )
    return module.run_production_like_timing_gate(args)


def _prepare_runtime_file(module, tmp_path: Path, payload: dict | None = None) -> Path:
    repeat_path = tmp_path / "repeat.json"
    _write_json(repeat_path, {"artifact_kind": "repeat-placeholder"})
    runtime = _runtime_ablation_payload(module)
    runtime.update(payload or {})
    runtime["repeat_benchmark_json"] = str(repeat_path)
    runtime["repeat_benchmark_sha256"] = module._sha256(repeat_path)  # noqa: SLF001
    runtime_path = tmp_path / "runtime_ablation.json"
    _write_json(runtime_path, runtime)
    return runtime_path


def test_production_like_timing_gate_accepts_clean_config(tmp_path: Path):
    module = _load_module()
    config_path = tmp_path / "prod_like.yaml"
    output_path = tmp_path / "out.json"
    runtime_path = _prepare_runtime_file(module, tmp_path)
    _write_yaml(config_path, _trace_config_payload())

    result = _run(module, runtime_path, config_path, output_path)

    assert result["passed"] is True
    assert result["production_like_timing_ready"] is True
    assert result["production_like_benchmark_config_ready"] is True
    assert result["benchmark_run_ready"] is False
    assert result["measures_tpot"] is False
    assert result["current_artifact_is_tpot_benchmark"] is False
    assert result["current_wna16_benchmark_ready"] is False
    assert result["will_measure_tpot_next"] is True
    assert result["kernel_arg_pass_allowed"] is False
    assert result["trace_config_summary"]["max_samples"] == 32
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_production_like_timing_gate_rejects_runtime_ablation_tpot(tmp_path: Path):
    module = _load_module()
    runtime = _runtime_ablation_payload(module)
    runtime["measures_tpot"] = True
    config_path = tmp_path / "prod_like.yaml"
    runtime_path = _prepare_runtime_file(module, tmp_path, runtime)
    _write_yaml(config_path, _trace_config_payload())

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_ablation_measures_tpot_mismatch" in result["failures"]
    assert result["measures_tpot"] is True


def test_production_like_timing_gate_rejects_runtime_ablation_kernel_arg_pass(
    tmp_path: Path,
):
    module = _load_module()
    runtime = _runtime_ablation_payload(module)
    runtime["kernel_arg_pass_allowed"] = True
    config_path = tmp_path / "prod_like.yaml"
    runtime_path = _prepare_runtime_file(module, tmp_path, runtime)
    _write_yaml(config_path, _trace_config_payload())

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_ablation_kernel_arg_pass_allowed_mismatch" in result["failures"]
    assert result["kernel_arg_pass_allowed"] is True


def test_production_like_timing_gate_rejects_shadow_enabled(tmp_path: Path):
    module = _load_module()
    config_path = tmp_path / "prod_like.yaml"
    config = _trace_config_payload()
    config["trace"]["runtime_shadow"]["enabled"] = True
    runtime_path = _prepare_runtime_file(module, tmp_path)
    _write_yaml(config_path, config)

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_shadow_enabled_not_false" in result["failures"]


def test_production_like_timing_gate_rejects_record_topk(tmp_path: Path):
    module = _load_module()
    config_path = tmp_path / "prod_like.yaml"
    config = _trace_config_payload()
    config["trace"]["capture_router_topk"] = True
    config["trace"]["runtime_shadow"]["record_router_topk"] = True
    runtime_path = _prepare_runtime_file(module, tmp_path)
    _write_yaml(config_path, config)

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "trace_capture_router_topk_not_false" in result["failures"]
    assert "runtime_shadow_record_router_topk_not_false" in result["failures"]


def test_production_like_timing_gate_rejects_source_timing(tmp_path: Path):
    module = _load_module()
    config_path = tmp_path / "prod_like.yaml"
    config = _trace_config_payload()
    config["trace"]["runtime_shadow"]["decoder_source_timing_mode"] = "full"
    runtime_path = _prepare_runtime_file(module, tmp_path)
    _write_yaml(config_path, config)

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_shadow_decoder_source_timing_mode_mismatch" in result["failures"]


def test_production_like_timing_gate_rejects_decode_workload_trace(tmp_path: Path):
    module = _load_module()
    runtime_path = _prepare_runtime_file(module, tmp_path)
    config_path = tmp_path / "prod_like.yaml"
    config = _trace_config_payload()
    config["trace"]["decode_workload_trace"] = {"enabled": True}
    _write_yaml(config_path, config)

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "trace_decode_workload_trace_enabled" in result["failures"]


def test_production_like_timing_gate_rejects_premap_live_config(tmp_path: Path):
    module = _load_module()
    runtime_path = _prepare_runtime_file(module, tmp_path)
    config_path = tmp_path / "prod_like.yaml"
    config = _trace_config_payload()
    config["trace"]["allow_premap_live_config_without_router_recorder"] = True
    shadow = config["trace"]["runtime_shadow"]
    shadow["emit_premap_consumer_mapping"] = True
    shadow["premap_payload_cache_producer_state_packet_export_enabled"] = True
    _write_yaml(config_path, config)

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "trace_allow_premap_live_config_without_router_recorder_not_false"
        in result["failures"]
    )
    assert "runtime_shadow_emit_premap_consumer_mapping_not_false" in result["failures"]
    assert (
        "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled_not_false"
        in result["failures"]
    )


def test_production_like_timing_gate_rejects_truthy_live_config_mapping(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path = _prepare_runtime_file(module, tmp_path)
    config_path = tmp_path / "prod_like.yaml"
    config = _trace_config_payload()
    config["trace"]["allow_premap_live_config_without_router_recorder"] = {
        "enabled": False
    }
    _write_yaml(config_path, config)

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "trace_allow_premap_live_config_without_router_recorder_not_false"
        in result["failures"]
    )


def test_production_like_timing_gate_rejects_runtime_ablation_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path = _prepare_runtime_file(module, tmp_path, {"row_ok_count": 1})
    config_path = tmp_path / "prod_like.yaml"
    _write_yaml(config_path, _trace_config_payload())

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_ablation_row_ok_count_mismatch" in result["failures"]


def test_production_like_timing_gate_rejects_runtime_ablation_field_hash_missing(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path = _prepare_runtime_file(module, tmp_path, {"field_read_hashes": {}})
    config_path = tmp_path / "prod_like.yaml"
    _write_yaml(config_path, _trace_config_payload())

    result = _run(module, runtime_path, config_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_ablation_descriptor_ptr_field_hash_invalid" in result["failures"]
