from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "analyze_awq_decode_breakdown.py"
    spec = importlib.util.spec_from_file_location(
        "analyze_awq_decode_breakdown", path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_trace(tmp_path: Path, *, generate_seconds: float) -> Path:
    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    (trace_dir / "performance_summary.json").write_text(
        json.dumps(
            {
                "sample_count": 1,
                "requested_output_token_count": 2,
                "generate_wall_seconds": generate_seconds,
                "generate_seconds_per_requested_output_token": generate_seconds / 2.0,
            }
        )
        + "\n"
    )
    return trace_dir


def _write_shadow(trace_dir: Path, rows: list[dict]) -> None:
    (trace_dir / "runtime_shadow.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )


def test_decode_breakdown_filters_descriptor_prefill_rows(tmp_path: Path) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.01)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "descriptor_layer_timing",
                "descriptor_order_layer_phase": "prefill",
                "descriptor_order_layer_apply_us": 9000.0,
            },
            {
                "event_type": "descriptor_layer_timing",
                "descriptor_order_layer_phase": "decode",
                "descriptor_order_layer_apply_us": 1000.0,
            },
            {
                "event_type": "decoder_layer_timing",
                "decoder_layer_phase": "prefill",
                "decoder_layer_elapsed_us": 8000.0,
            },
            {
                "event_type": "decoder_layer_timing",
                "decoder_layer_phase": "decode",
                "decoder_layer_elapsed_us": 1500.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "num_tokens_heuristic",
                "decoder_component_elapsed_us": 300.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "mlp",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "num_tokens_heuristic",
                "decoder_component_elapsed_us": 900.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_core_total",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 100.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_core_decode_non_spec",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 80.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_core_conv_update",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 30.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_core_recurrent",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 45.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_layout_unpack",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 7.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "router_logits",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 50.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_total",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 1200.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "select_experts",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 60.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "select_compute_routing",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "FusedTopKRouter:ok",
                "moe_substage_elapsed_us": 45.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "select_record_topk",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 10.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "prepare_expert_assignment",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "original",
                "moe_substage_elapsed_us": 70.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "quant_method_apply",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 1000.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "apply_dispatch_w1_host",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 200.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "apply_activation",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 30.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "apply_dispatch_w2_host",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 150.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "apply_moe_sum",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 20.0,
            },
            {
                "event_type": "wna16_kernel_timing",
                "wna16_bucket": "w1",
                "wna16_num_tokens": 1,
                "wna16_top_k": 8,
                "wna16_phase": "decode",
                "wna16_phase_source": "num_tokens_topk_heuristic",
                "wna16_kernel_gpu_elapsed_us": 100.0,
                "wna16_kernel_elapsed_us": 120.0,
                "wna16_kernel_timing_kind": "gpu_event_synchronized",
                "wna16_status": "ok",
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["shadow"]["decode_layer_apply_us"]["count"] == 1
    assert result["shadow"]["decode_layer_apply_us"]["sum_us"] == 1000.0
    assert result["shadow"]["decoder_layer_us"]["decode"]["count"] == 1
    assert result["shadow"]["decoder_layer_us"]["decode"]["sum_us"] == 1500.0
    assert result["shadow"]["decoder_layer_us"]["prefill"]["sum_us"] == 8000.0
    assert result["sums_us"]["decode_decoder_layer_minus_moe_apply"] == 500.0
    assert result["shadow"]["decoder_component_us"]["attention"]["decode"]["sum_us"] == 300.0
    assert result["shadow"]["decoder_component_us"]["mlp"]["decode"]["sum_us"] == 900.0
    assert (
        result["shadow"]["decoder_component_us"]["attention_linear_core_total"][
            "decode"
        ]["sum_us"]
        == 100.0
    )
    assert (
        result["shadow"]["decoder_component_us"][
            "attention_linear_core_decode_non_spec"
        ]["decode"]["sum_us"]
        == 80.0
    )
    assert (
        result["shadow"]["decoder_component_us"]["attention_linear_core_conv_update"][
            "decode"
        ]["sum_us"]
        == 30.0
    )
    assert (
        result["shadow"]["decoder_component_us"]["attention_linear_core_recurrent"][
            "decode"
        ]["sum_us"]
        == 45.0
    )
    assert (
        result["shadow"]["decoder_component_us"]["attention_linear_layout_unpack"][
            "decode"
        ]["sum_us"]
        == 7.0
    )
    # Source-method rows are nested diagnostic counters; this sum is not an
    # additive attention cost.
    assert result["sums_us"]["decode_attention_linear_source_method_nested_sum"] == 262.0
    assert result["sums_us"]["decode_attention_linear_leaf_parts_sum"] is None
    assert result["sums_us"]["decode_attention_full_leaf_parts_sum"] is None
    assert result["sums_us"]["decode_attention_leaf_parts_sum"] is None
    assert result["sums_us"]["decode_source_parts_sum"] is None
    assert result["sums_us"]["decode_decoder_outside_attention_mlp"] == 300.0
    assert result["sums_us"]["decode_mlp_minus_moe_apply"] == -100.0
    assert result["anomalies"]["decode_mlp_minus_moe_apply_negative"]
    assert result["shadow"]["moe_substage_us"]["router_logits"]["decode"]["sum_us"] == 50.0
    assert result["shadow"]["moe_substage_us"]["experts_total"]["decode"]["sum_us"] == 1200.0
    assert result["shadow"]["moe_substage_us"]["select_experts"]["decode"]["sum_us"] == 60.0
    assert (
        result["shadow"]["moe_substage_us"]["prepare_expert_assignment"]["decode"][
            "sum_us"
        ]
        == 70.0
    )
    assert result["shadow"]["moe_substage_us"]["quant_method_apply"]["decode"]["sum_us"] == 1000.0
    assert result["sums_us"]["moe_router_logits"] == 50.0
    assert result["sums_us"]["moe_experts_total"] == 1200.0
    assert result["sums_us"]["moe_select_experts"] == 60.0
    assert result["sums_us"]["moe_select_compute_routing"] == 45.0
    assert result["sums_us"]["moe_select_record_topk"] == 10.0
    assert result["sums_us"]["moe_select_experts_minus_record_topk"] == 50.0
    assert result["sums_us"]["moe_prepare_expert_assignment"] == 70.0
    assert result["sums_us"]["moe_quant_method_apply"] == 1000.0
    assert result["sums_us"]["moe_apply_dispatch_w1_host"] == 200.0
    assert result["sums_us"]["moe_apply_dispatch_w1_host_minus_gpu_event"] == 100.0
    assert result["sums_us"]["moe_apply_activation"] == 30.0
    assert result["sums_us"]["moe_apply_dispatch_w2_host"] == 150.0
    assert result["sums_us"]["moe_apply_dispatch_w2_host_minus_gpu_event"] == 150.0
    assert result["sums_us"]["moe_apply_dispatch_w1w2_host_minus_gpu_event"] == 250.0
    assert result["sums_us"]["moe_apply_moe_sum"] == 20.0
    assert result["sums_us"]["moe_quant_apply_measured_parts_sum"] == 470.0
    assert result["sums_us"]["moe_quant_apply_minus_measured_parts"] == 530.0
    assert result["sums_us"]["moe_experts_total_minus_quant_apply"] == 200.0
    assert result["sums_us"]["moe_quant_apply_minus_prepare_wna16"] == 830.0
    assert result["shadow"]["integrity"]["descriptor_layer_phase_counts"] == {
        "decode": 1,
        "prefill": 1,
    }
    assert result["shadow"]["integrity"]["wna16_phase_counts"] == {"decode": 1}
    assert result["shadow"]["integrity"]["wna16_phase_source_counts"] == {
        "num_tokens_topk_heuristic": 1,
    }
    assert result["shadow"]["integrity"]["decoder_phase_source_counts"] == {
        "unknown": 2,
    }
    assert result["shadow"]["integrity"]["decoder_component_phase_source_counts"] == {
        "parent_attention_context": 5,
        "num_tokens_heuristic": 2,
    }
    assert result["shadow"]["integrity"]["moe_substage_phase_source_counts"] == {
        "num_tokens_heuristic": 11,
    }
    assert result["shadow"]["integrity"]["moe_substage_status_counts"] == {
        "apply_activation:ok": 1,
        "apply_dispatch_w1_host:ok": 1,
        "apply_dispatch_w2_host:ok": 1,
        "apply_moe_sum:ok": 1,
        "experts_total:ok": 1,
        "prepare_expert_assignment:original": 1,
        "quant_method_apply:ok": 1,
        "router_logits:ok": 1,
        "select_compute_routing:FusedTopKRouter:ok": 1,
        "select_experts:ok": 1,
        "select_record_topk:ok": 1,
    }
    assert result["shadow"]["integrity"]["wna16_decode_filter_available"]
    assert result["shadow"]["integrity"]["wna16_gpu_event_timing_diagnostic_only"]


def test_decode_breakdown_preserves_negative_residual_anomaly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "descriptor_layer_timing",
                "descriptor_order_layer_phase": "decode",
                "descriptor_order_layer_apply_us": 2000.0,
            },
            {
                "event_type": "wna16_kernel_timing",
                "wna16_bucket": "w1",
                "wna16_num_tokens": 1,
                "wna16_top_k": 8,
                "wna16_phase": "decode",
                "wna16_phase_source": "explicit",
                "wna16_kernel_gpu_elapsed_us": 3000.0,
                "wna16_kernel_elapsed_us": 3100.0,
                "wna16_kernel_timing_kind": "gpu_event_synchronized",
                "wna16_status": "ok",
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["generate_minus_decode_moe_apply"] == -1000.0
    assert result["sums_us"]["moe_apply_minus_wna16_gpu_event"] == -1000.0
    assert result["sums_us"]["decode_decoder_layer"] is None
    assert result["sums_us"]["decode_decoder_layer_minus_moe_apply"] is None
    assert result["anomalies"]["generate_minus_decode_moe_apply_negative"]
    assert result["anomalies"]["moe_apply_minus_wna16_gpu_event_negative"]
    assert not result["anomalies"]["decode_decoder_layer_minus_moe_apply_negative"]


def test_decode_breakdown_preserves_unknown_decoder_component_name(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_new_leaf",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "num_tokens_heuristic",
                "decoder_component_elapsed_us": 123.0,
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert "attention_new_leaf" in result["shadow"]["decoder_component_us"]
    assert (
        result["shadow"]["decoder_component_us"]["attention_new_leaf"]["decode"][
            "sum_us"
        ]
        == 123.0
    )
    assert result["shadow"]["decoder_component_us"]["other"]["decode"] == {}
    assert result["shadow"]["integrity"]["decoder_unknown_component_counts"] == {
        "attention_new_leaf": 1,
    }


def test_decode_breakdown_derives_handoff_residuals_and_flags_negatives(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_handoff_core_total",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 90.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_handoff_core_decode_non_spec",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 50.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_handoff_conv_update",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 30.0,
            },
            {
                "event_type": "decoder_component_timing",
                "decoder_component": "attention_linear_handoff_recurrent",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "parent_attention_context",
                "decoder_component_elapsed_us": 25.0,
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["decode_attention_linear_handoff_core_total"] == 90.0
    assert (
        result["sums_us"][
            "decode_attention_linear_handoff_core_decode_non_spec"
        ]
        == 50.0
    )
    assert result["sums_us"]["decode_attention_linear_handoff_conv_update"] == 30.0
    assert result["sums_us"]["decode_attention_linear_handoff_recurrent"] == 25.0
    assert (
        result["sums_us"]["decode_attention_linear_handoff_core_prep_layout"]
        == -5.0
    )
    assert (
        result["sums_us"]["decode_attention_linear_handoff_core_post_layout"]
        == 40.0
    )
    assert result["anomalies"][
        "attention_linear_handoff_core_prep_layout_negative"
    ]
    assert not result["anomalies"][
        "attention_linear_handoff_core_post_layout_negative"
    ]


def test_decode_breakdown_reads_aggregated_attention_handoff_components(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "decoder_component_aggregate",
                "decoder_component_aggregate_mode": "attention_handoff",
                "decoder_component_phase": "decode",
                "decoder_component_phase_source": "num_tokens_heuristic",
                "decoder_component_aggregate_count": 4,
                "decoder_component_aggregate_components": {
                    "attention_linear_handoff_linear_proj_total": {
                        "sum_us": 100.0,
                        "count": 2,
                    },
                    "attention_linear_handoff_norm": {
                        "sum_us": 40.0,
                        "count": 1,
                    },
                    "attention_linear_handoff_out_proj": {
                        "sum_us": 30.0,
                        "count": 1,
                    },
                },
            }
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["decode_attention_linear_handoff_linear_proj_total"] == 100.0
    assert result["sums_us"]["decode_attention_linear_handoff_norm"] == 40.0
    assert result["sums_us"]["decode_attention_linear_handoff_out_proj"] == 30.0
    assert (
        result["shadow"]["integrity"]["event_type_counts"][
            "decoder_component_aggregate"
        ]
        == 1
    )


def test_decode_breakdown_prefers_detailed_shared_output_parts(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_direct_layer",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 100.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_w1",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 10.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_activation",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 20.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_w2",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 30.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_output_combine",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "coarse_legacy",
                "moe_substage_elapsed_us": 999.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_output_gate",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 15.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_output_sigmoid_mul",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 5.0,
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["moe_experts_shared_output_combine"] == 999.0
    assert result["sums_us"]["moe_experts_shared_output_gate"] == 15.0
    assert result["sums_us"]["moe_experts_shared_output_sigmoid_mul"] == 5.0
    assert result["sums_us"]["moe_experts_shared_output_detailed_parts_sum"] == 20.0
    assert result["sums_us"]["moe_experts_shared_direct_source_parts_sum"] == 80.0
    assert result["sums_us"]["moe_experts_shared_direct_minus_source_parts"] == 20.0

    output_md = tmp_path / "breakdown.md"
    module.write_markdown(result, output_md)
    markdown = output_md.read_text()
    assert "MoE experts shared output gate" in markdown
    assert "MoE experts shared output sigmoid/mul" in markdown


def test_decode_breakdown_reads_moe_substage_aggregate(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "moe_substage_aggregate",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_aggregate_components": {
                    "experts_shared_direct_layer": {
                        "sum_us": 100.0,
                        "count": 2,
                        "status_counts": {"ok": 2},
                    },
                    "experts_shared_w1": {
                        "sum_us": 10.0,
                        "count": 1,
                        "status_counts": {"ok": 1},
                    },
                    "experts_shared_output_gate": {
                        "sum_us": 15.0,
                        "count": 1,
                        "status_counts": {"fallback": 1},
                    },
                },
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["moe_experts_shared_direct_layer"] == 100.0
    assert result["sums_us"]["moe_experts_shared_w1"] == 10.0
    assert result["sums_us"]["moe_experts_shared_output_gate"] == 15.0
    assert result["shadow"]["integrity"]["moe_substage_status_counts"] == {
        "experts_shared_direct_layer:ok": 2,
        "experts_shared_output_gate:fallback": 1,
        "experts_shared_w1:ok": 1,
    }


def test_decode_breakdown_reads_sampled_moe_substage_aggregate_counts(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "moe_substage_aggregate",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_aggregate_components": {
                    "experts_shared_direct_layer": {
                        "sum_us": 80.0,
                        "raw_sum_us": 40.0,
                        "count": 2,
                        "estimated_count": 4,
                        "status_counts": {"ok": 2},
                        "estimated_status_counts": {"ok": 4},
                        "sample_period": 2,
                    },
                },
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["moe_experts_shared_direct_layer"] == 80.0
    assert result["shadow"]["integrity"]["moe_substage_phase_source_counts"] == {
        "num_tokens_heuristic": 4,
    }
    assert result["shadow"]["integrity"]["moe_substage_status_counts"] == {
        "experts_shared_direct_layer:ok": 4,
    }


def test_decode_breakdown_uses_legacy_shared_output_when_detail_missing(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_direct_layer",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 100.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_w1",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 10.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_output_combine",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "legacy",
                "moe_substage_elapsed_us": 40.0,
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["moe_experts_shared_output_detailed_parts_sum"] is None
    assert result["sums_us"]["moe_experts_shared_direct_source_parts_sum"] == 50.0
    assert result["sums_us"]["moe_experts_shared_direct_minus_source_parts"] == 50.0


def test_decode_breakdown_uses_legacy_shared_output_when_detail_partial(
    tmp_path: Path,
) -> None:
    module = _load_module()
    trace_dir = _write_trace(tmp_path, generate_seconds=0.001)
    _write_shadow(
        trace_dir,
        [
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_direct_layer",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 100.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_w1",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "ok",
                "moe_substage_elapsed_us": 10.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_output_combine",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "legacy",
                "moe_substage_elapsed_us": 40.0,
            },
            {
                "event_type": "moe_substage_timing",
                "moe_substage": "experts_shared_output_gate",
                "moe_substage_phase": "decode",
                "moe_substage_phase_source": "num_tokens_heuristic",
                "moe_substage_status": "partial",
                "moe_substage_elapsed_us": 15.0,
            },
        ],
    )

    result = module.build_breakdown(trace_dir)

    assert result["sums_us"]["moe_experts_shared_output_gate"] == 15.0
    assert result["sums_us"]["moe_experts_shared_output_sigmoid_mul"] is None
    assert result["sums_us"]["moe_experts_shared_output_detailed_parts_sum"] is None
    assert result["sums_us"]["moe_experts_shared_direct_source_parts_sum"] == 50.0
    assert result["sums_us"]["moe_experts_shared_direct_minus_source_parts"] == 50.0
