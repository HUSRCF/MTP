from __future__ import annotations

import importlib.util
import json
import pytest
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "summarize_awq_real_bottlenecks.py"
    spec = importlib.util.spec_from_file_location("summarize_awq_real_bottlenecks", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload) + "\n")
    return path


def test_real_bottleneck_summary_separates_telemetry_contracts(tmp_path: Path) -> None:
    module = _load_module()
    results = _write_json(
        tmp_path / "results.json",
        [
            {
                "mode": "production_like",
                "returncode": 0,
                "generate_seconds_per_requested_output_token": 0.10,
                "generate_wall_seconds": 10.0,
            },
            {
                "mode": "diagnostic_light",
                "returncode": 0,
                "generate_seconds_per_requested_output_token": 0.12,
                "generate_wall_seconds": 12.0,
            },
            {
                "mode": "attention_core_light",
                "returncode": 0,
                "generate_seconds_per_requested_output_token": 0.13,
                "generate_wall_seconds": 13.0,
            },
            {
                "mode": "shared_expert_light",
                "returncode": 0,
                "generate_seconds_per_requested_output_token": 0.14,
                "generate_wall_seconds": 14.0,
            },
        ],
    )
    diagnostic = _write_json(
        tmp_path / "diagnostic.json",
        {
            "performance": {"generate_wall_seconds": 12.0},
            "sums_us": {
                "generate": 12_000_000.0,
                "decode_decoder_layer": 9_000_000.0,
                "decode_attention": 2_000_000.0,
                "decode_mlp": 5_000_000.0,
                "decode_moe_layer_apply": 2_500_000.0,
                "moe_experts_shared_direct_layer": 1_000_000.0,
                "moe_experts_shared_output_gate": 400_000.0,
                "moe_experts_shared_output_sigmoid_mul": 100_000.0,
                "generate_minus_decode_decoder_layer": 3_000_000.0,
            },
        },
    )
    attention = _write_json(
        tmp_path / "attention.json",
        {
            "performance": {"generate_wall_seconds": 13.0},
            "sums_us": {
                "generate": 13_000_000.0,
                "decode_attention": 3_000_000.0,
                "decode_attention_linear_core_total": 900_000.0,
                "decode_attention_linear_core_decode_non_spec": 800_000.0,
                "decode_attention_linear_source_method_nested_sum": 1_700_000.0,
                "decode_attention_full_leaf_parts_sum": None,
            },
        },
    )
    decoder = _write_json(
        tmp_path / "decoder.json",
        {
            "performance": {"generate_wall_seconds": 11.0},
            "sums_us": {
                "generate": 11_000_000.0,
                "decode_decoder_layer": 9_900_000.0,
                "generate_minus_decode_decoder_layer": 1_100_000.0,
            },
        },
    )
    shared = _write_json(
        tmp_path / "shared.json",
        {
            "performance": {"generate_wall_seconds": 14.0},
            "sums_us": {
                "generate": 14_000_000.0,
                "moe_experts_shared_no_overlap": 2_000_000.0,
                "moe_experts_shared_direct_layer": 1_400_000.0,
                "moe_experts_shared_direct_source_parts_sum": 1_000_000.0,
                "moe_experts_shared_direct_minus_source_parts": 400_000.0,
                "moe_experts_shared_w1": 200_000.0,
                "moe_experts_shared_activation": 100_000.0,
                "moe_experts_shared_w2": 250_000.0,
                "moe_experts_shared_output_gate": 350_000.0,
                "moe_experts_shared_output_sigmoid_mul": 100_000.0,
                "moe_experts_shared_no_overlap_minus_inner_parts": 50_000.0,
            },
        },
    )

    summary = module.build_summary(
        results_json=results,
        diagnostic_breakdown=diagnostic,
        attention_core_breakdown=attention,
        decoder_layer_breakdown=decoder,
        shared_expert_breakdown=shared,
    )

    assert summary["production_like"]["tpot_s"] == 0.10
    assert summary["telemetry_overhead"]["diagnostic_light_speedup_vs_production"] == (
        0.10 / 0.12
    )
    assert summary["telemetry_overhead"]["diagnostic_light_overhead_pct"] == pytest.approx(20.0)
    assert summary["telemetry_overhead"]["diagnostic_light_fields_legacy_alias_of"] == (
        "diagnostic_light"
    )
    assert summary["telemetry_overhead"]["attention_core_light_overhead_pct"] == pytest.approx(30.0)
    assert summary["telemetry_overhead"]["shared_expert_light_overhead_pct"] == pytest.approx(40.0)
    assert summary["diagnostic_light_bottlenecks"]["engine_residual_ms"] == 3000.0
    assert summary["diagnostic_light_shares_pct"]["shared_expert_output_gate"] == (
        100.0 * 350_000.0 / 12_000_000.0
    )
    assert summary["attention_core_light"]["linear_core_total_ms"] == 900.0
    assert summary["shared_expert_light"]["output_gate_ms"] == 350.0
    assert summary["shared_expert_light"]["direct_minus_source_parts_ms"] == 400.0
    assert summary["decoder_layer_only"]["engine_residual_ms"] == 1100.0
    assert summary["decoder_layer_only"]["engine_residual_share_pct"] == pytest.approx(10.0)
    assert "diagnostic-only" in summary["telemetry_contract"]["attention_core_light"]


def test_real_bottleneck_summary_accepts_diagnostic_coarse_breakdown(
    tmp_path: Path,
) -> None:
    module = _load_module()
    results = _write_json(
        tmp_path / "results.json",
        [
            {
                "mode": "production_like",
                "returncode": 0,
                "generate_seconds_per_requested_output_token": 0.10,
                "generate_wall_seconds": 10.0,
            },
            {
                "mode": "diagnostic_coarse_breakdown",
                "returncode": 0,
                "generate_seconds_per_requested_output_token": 0.11,
                "generate_wall_seconds": 11.0,
            },
        ],
    )
    diagnostic = _write_json(
        tmp_path / "diagnostic_coarse.json",
        {
            "performance": {"generate_wall_seconds": 11.0},
            "sums_us": {
                "generate": 11_000_000.0,
                "decode_decoder_layer": 9_000_000.0,
                "decode_attention": 3_000_000.0,
                "decode_mlp": 5_000_000.0,
                "decode_moe_layer_apply": 2_500_000.0,
                "moe_experts_shared_direct_layer": 1_000_000.0,
                "generate_minus_decode_decoder_layer": 2_000_000.0,
            },
        },
    )

    summary = module.build_summary(
        results_json=results,
        diagnostic_breakdown=diagnostic,
        attention_core_breakdown=None,
    )

    assert summary["telemetry_overhead"]["diagnostic_mode"] == (
        "diagnostic_coarse_breakdown"
    )
    assert summary["telemetry_overhead"]["diagnostic_light_fields_legacy_alias_of"] == (
        "diagnostic_coarse_breakdown"
    )
    assert summary["telemetry_overhead"]["diagnostic_tpot_s"] == 0.11
    assert summary["telemetry_overhead"]["diagnostic_overhead_pct"] == pytest.approx(
        10.0
    )
    assert summary["diagnostic_light_bottlenecks"]["attention_ms"] == 3000.0

    output = tmp_path / "summary.md"
    module.write_markdown(summary, output)
    text = output.read_text()
    assert "| diagnostic_coarse_breakdown | 0.110000 |" in text
    assert "legacy aliases" in text
    assert "single-artifact coarse diagnostic" in text


def test_real_bottleneck_summary_adds_low_intrusion_coarse_baseline(
    tmp_path: Path,
) -> None:
    module = _load_module()
    attention_total = _write_json(
        tmp_path / "attention_total.json",
        {
            "performance": {"generate_wall_seconds": 20.0},
            "sums_us": {
                "generate": 20_000_000.0,
                "decode_attention": 6_000_000.0,
                "decode_mlp": 10_000_000.0,
                "decode_moe_layer_apply": 5_000_000.0,
                "decode_mlp_minus_moe_apply": 5_000_000.0,
                "decode_decoder_outside_attention_mlp": 4_000_000.0,
            },
        },
    )
    shared_body = _write_json(
        tmp_path / "shared_body.json",
        {
            "performance": {"generate_wall_seconds": 21.0},
            "sums_us": {
                "generate": 21_000_000.0,
                "moe_experts_shared_direct_layer": 2_100_000.0,
                "decode_moe_layer_apply": 6_300_000.0,
            },
        },
    )
    engine = _write_json(
        tmp_path / "engine.json",
        {
            "performance": {"generate_wall_seconds": 22.0},
            "sums_us": {
                "generate": 22_000_000.0,
                "engine_execute_model_minus_model_forward": 440_000.0,
                "engine_generate_call_minus_execute_model": 220_000.0,
                "engine_substage_engine_prepare_inputs": 110_000.0,
                "engine_substage_engine_sample_tokens": 55_000.0,
                "engine_substage_engine_logits_processor_forward": 22_000.0,
                "engine_substage_engine_sampler_forward": 11_000.0,
            },
        },
    )

    summary = module.build_summary(
        results_json=None,
        diagnostic_breakdown=None,
        attention_core_breakdown=None,
        attention_total_breakdown=attention_total,
        shared_body_total_breakdown=shared_body,
        engine_breakdown=engine,
    )

    coarse = summary["low_intrusion_coarse"]
    assert coarse["attention_total_only"]["attention_ms"] == 6000.0
    assert coarse["attention_total_only"]["attention_share_pct"] == pytest.approx(30.0)
    assert coarse["attention_total_only"]["mlp_moe_share_pct"] == pytest.approx(50.0)
    assert coarse["shared_body_total_only"]["shared_direct_share_pct"] == pytest.approx(10.0)
    assert coarse["engine_light"]["execute_model_minus_model_forward_share_pct"] == (
        pytest.approx(2.0)
    )

    output = tmp_path / "summary.md"
    module.write_markdown(summary, output)
    text = output.read_text()
    assert "Low-Intrusion Coarse Baseline" in text
    assert "attention_total_only | attention" in text
    assert "shared_body_total_only | shared direct" in text
    assert "engine_light | execute_model - model_forward" in text


def test_real_bottleneck_summary_does_not_guess_diagnostic_mode_without_results(
    tmp_path: Path,
) -> None:
    module = _load_module()
    diagnostic = _write_json(
        tmp_path / "diagnostic.json",
        {
            "performance": {"generate_wall_seconds": 11.0},
            "sums_us": {
                "generate": 11_000_000.0,
                "decode_attention": 3_000_000.0,
            },
        },
    )

    summary = module.build_summary(
        results_json=None,
        diagnostic_breakdown=diagnostic,
        attention_core_breakdown=None,
    )

    assert summary["telemetry_overhead"]["diagnostic_mode"] == "diagnostic_unknown"
    assert summary["telemetry_overhead"]["diagnostic_light_fields_legacy_alias_of"] == (
        "diagnostic_unknown"
    )


def test_real_bottleneck_summary_allows_explicit_diagnostic_mode_without_results(
    tmp_path: Path,
) -> None:
    module = _load_module()
    diagnostic = _write_json(
        tmp_path / "diagnostic.json",
        {
            "performance": {"generate_wall_seconds": 11.0},
            "sums_us": {
                "generate": 11_000_000.0,
                "decode_attention": 3_000_000.0,
            },
        },
    )

    summary = module.build_summary(
        results_json=None,
        diagnostic_breakdown=diagnostic,
        attention_core_breakdown=None,
        diagnostic_mode_override="diagnostic_coarse_breakdown",
    )

    assert summary["telemetry_overhead"]["diagnostic_mode"] == (
        "diagnostic_coarse_breakdown"
    )
    assert summary["telemetry_overhead"]["diagnostic_light_fields_legacy_alias_of"] == (
        "diagnostic_coarse_breakdown"
    )


def test_real_bottleneck_markdown_labels_nested_attention(tmp_path: Path) -> None:
    module = _load_module()
    summary = {
        "telemetry_contract": {
            "production_like": "baseline",
            "diagnostic_light": "diagnostic",
            "attention_core_light": "diagnostic-only",
            "shared_expert_light": "diagnostic-only",
            "decoder_layer_only": "low-intrusion",
        },
        "production_like": {"tpot_s": 0.1},
        "telemetry_overhead": {
            "diagnostic_light_tpot_s": 0.12,
            "diagnostic_light_speedup_vs_production": 0.8333,
            "attention_core_light_tpot_s": 0.13,
            "attention_core_light_speedup_vs_production": 0.7692,
            "attention_core_light_overhead_pct": 30.0,
            "shared_expert_light_tpot_s": 0.14,
            "shared_expert_light_speedup_vs_production": 0.7142,
            "shared_expert_light_overhead_pct": 40.0,
        },
        "diagnostic_light_bottlenecks": {},
        "diagnostic_light_shares_pct": {},
        "attention_core_light": {
            "attention_ms": 3000.0,
            "linear_core_total_ms": 900.0,
            "linear_core_decode_non_spec_ms": 800.0,
            "linear_source_method_nested_ms": 1700.0,
            "full_leaf_parts_ms": None,
        },
        "shared_expert_light": {
            "no_overlap_ms": 2000.0,
            "direct_layer_ms": 1400.0,
            "direct_source_parts_ms": 1000.0,
            "direct_minus_source_parts_ms": 400.0,
            "w1_ms": 200.0,
            "activation_ms": 100.0,
            "w2_ms": 250.0,
            "output_gate_ms": 350.0,
            "output_sigmoid_mul_ms": 100.0,
            "no_overlap_minus_inner_parts_ms": 50.0,
            "direct_layer_share_pct": 10.0,
            "output_gate_share_pct": 2.5,
        },
        "decoder_layer_only": {
            "decoder_layer_ms": 9900.0,
            "decoder_layer_share_pct": 90.0,
            "engine_residual_ms": 1100.0,
            "engine_residual_share_pct": 10.0,
        },
        "next_targets": [],
    }
    output = tmp_path / "summary.md"
    module.write_markdown(summary, output)
    text = output.read_text()

    assert "linear source method nested sum" in text
    assert "diagnostic-only" in text
    assert "Do not add" in text
    assert "Decoder-Layer Only" in text
    assert "Shared-Expert Light" in text
    assert "shared output gate" in text
    assert "engine residual" in text


def test_real_bottleneck_summary_keeps_missing_generate_absent(tmp_path: Path) -> None:
    module = _load_module()
    empty = _write_json(tmp_path / "empty.json", {"performance": {}, "sums_us": {}})

    summary = module.build_summary(
        results_json=None,
        diagnostic_breakdown=empty,
        attention_core_breakdown=empty,
        decoder_layer_breakdown=empty,
        shared_expert_breakdown=empty,
    )

    assert summary["diagnostic_light_bottlenecks"]["generate_ms"] is None
    assert summary["attention_core_light"]["generate_ms"] is None
    assert summary["shared_expert_light"]["output_gate_ms"] is None
    assert summary["decoder_layer_only"]["engine_residual_ms"] is None

    output = tmp_path / "missing.md"
    module.write_markdown(summary, output)
    text = output.read_text()
    assert "| production_like |  |  |  |" in text
