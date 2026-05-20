#!/usr/bin/env python3
"""Build a coarse decode-time breakdown from AWQ/vLLM runtime shadow traces."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import statistics
from pathlib import Path
from typing import Any


DECODER_COMPONENT_NAMES = (
    "attention",
    "mlp",
    "decoder_input_layernorm",
    "decoder_linear_attention",
    "decoder_full_attention",
    "decoder_attention_layer_scale",
    "decoder_post_attention_layernorm",
    "decoder_mlp_call",
    "decoder_ffn_layer_scale",
    "attention_linear_input_proj",
    "attention_linear_ba_proj",
    "attention_linear_conv1d",
    "attention_linear_norm",
    "attention_linear_core",
    "attention_linear_core_total",
    "attention_linear_core_decode_non_spec",
    "attention_linear_core_conv_update",
    "attention_linear_core_recurrent",
    "attention_linear_handoff_linear_proj_total",
    "attention_linear_handoff_norm",
    "attention_linear_handoff_core_total",
    "attention_linear_handoff_core_decode_non_spec",
    "attention_linear_handoff_core_prep_layout",
    "attention_linear_handoff_conv_update",
    "attention_linear_handoff_recurrent",
    "attention_linear_handoff_core_post_layout",
    "attention_linear_handoff_out_proj",
    "attention_linear_layout_unpack",
    "attention_linear_out_proj",
    "attention_linear_leaf_other",
    "attention_full_qkv_proj",
    "attention_full_qk_norm",
    "attention_full_rope",
    "attention_full_core",
    "attention_full_o_proj",
    "attention_full_leaf_other",
    "other",
)


def _phase_buckets() -> dict[str, list[float]]:
    return {"decode": [], "prefill": [], "unknown": []}


def _quantiles(values: list[float]) -> dict[str, float]:
    values = sorted(values)
    if not values:
        return {}

    def q(p: float) -> float:
        return values[min(len(values) - 1, int(round((len(values) - 1) * p)))]

    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "p50": q(0.50),
        "p95": q(0.95),
        "p99": q(0.99),
        "max": values[-1],
        "sum_us": sum(values),
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing required JSON file: {path}")
    return json.loads(path.read_text())


def _read_shadow(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing required runtime shadow file: {path}")
    decode_layer_apply: list[float] = []
    wna16_host: dict[str, list[float]] = {"w1": [], "w2": [], "other": []}
    wna16_gpu: dict[str, list[float]] = {"w1": [], "w2": [], "other": []}
    wna16_host_by_phase: dict[str, dict[str, list[float]]] = {
        bucket: {"decode": [], "prefill": [], "prefill_or_other": [], "unknown": []}
        for bucket in ("w1", "w2", "other")
    }
    wna16_gpu_by_phase: dict[str, dict[str, list[float]]] = {
        bucket: {"decode": [], "prefill": [], "prefill_or_other": [], "unknown": []}
        for bucket in ("w1", "w2", "other")
    }
    decoder_layer: dict[str, list[float]] = {"decode": [], "prefill": [], "unknown": []}
    decoder_component: dict[str, dict[str, list[float]]] = {
        name: _phase_buckets() for name in DECODER_COMPONENT_NAMES
    }
    engine_substage: dict[str, list[float]] = {}
    moe_substage: dict[str, dict[str, list[float]]] = {
        "router_logits": {"decode": [], "prefill": [], "unknown": []},
        "experts_total": {"decode": [], "prefill": [], "unknown": []},
        "select_experts": {"decode": [], "prefill": [], "unknown": []},
        "select_validate_eplb": {"decode": [], "prefill": [], "unknown": []},
        "select_indices_type": {"decode": [], "prefill": [], "unknown": []},
        "select_compute_routing": {"decode": [], "prefill": [], "unknown": []},
        "select_capture_logical_ids": {"decode": [], "prefill": [], "unknown": []},
        "select_eplb_mapping": {"decode": [], "prefill": [], "unknown": []},
        "select_dtype_convert": {"decode": [], "prefill": [], "unknown": []},
        "select_record_topk": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_stream_sync": {"decode": [], "prefill": [], "unknown": []},
        "experts_maybe_dispatch": {"decode": [], "prefill": [], "unknown": []},
        "experts_maybe_combine": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_no_overlap": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_determine_order": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_apply_skipped": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_w1": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_activation": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_w2": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_output_combine": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_output_gate": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_output_sigmoid_mul": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "experts_shared_output_gate_fused": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "experts_shared_child_other": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_direct_layer": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_body_core": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_body_gate_proj": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_body_gate_apply": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_body_gate_fused": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_aux_stream_layer_wait": {"decode": [], "prefill": [], "unknown": []},
        "experts_pre_quant_apply_glue": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_overlap": {"decode": [], "prefill": [], "unknown": []},
        "experts_shared_output_fetch": {"decode": [], "prefill": [], "unknown": []},
        "prepare_expert_assignment": {"decode": [], "prefill": [], "unknown": []},
        "quant_method_apply": {"decode": [], "prefill": [], "unknown": []},
        "quant_method_apply_monolithic": {"decode": [], "prefill": [], "unknown": []},
        "apply_problem_size": {"decode": [], "prefill": [], "unknown": []},
        "apply_config_lookup": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_fused_experts_outer": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_outer_quant_config": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_outer_inplace_assert": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_outer_dispatch_select": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_outer_impl_call": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_impl_entry_overhead": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_emit_overhead": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_impl_total": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_pre_dispatch": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_workspace_alloc": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_quantize_hidden": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_prepare_assignment": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_w1_enqueue": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_w1_post": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_activation": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_quantize_intermediate": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_source_w2_pre": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_w2_enqueue": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_w2_post": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_combine_scatter": {"decode": [], "prefill": [], "unknown": []},
        "apply_source_post_dispatch": {"decode": [], "prefill": [], "unknown": []},
        "apply_resize_cache_w1_output": {"decode": [], "prefill": [], "unknown": []},
        "apply_resize_cache_activation": {"decode": [], "prefill": [], "unknown": []},
        "apply_resize_cache_w2_output": {"decode": [], "prefill": [], "unknown": []},
        "apply_resize_cache_other": {"decode": [], "prefill": [], "unknown": []},
        "apply_quantize_hidden": {"decode": [], "prefill": [], "unknown": []},
        "apply_dispatch_w1_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_dispatch_w1_host_pre_invoke": {"decode": [], "prefill": [], "unknown": []},
        "apply_dispatch_w1_host_cuda_decision": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_dispatch_w1_host_invoke_call": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_activation": {"decode": [], "prefill": [], "unknown": []},
        "apply_quantize_intermediate": {"decode": [], "prefill": [], "unknown": []},
        "apply_dispatch_w2_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_dispatch_w2_host_pre_invoke": {"decode": [], "prefill": [], "unknown": []},
        "apply_dispatch_w2_host_cuda_decision": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_dispatch_w2_host_invoke_call": {
            "decode": [],
            "prefill": [],
            "unknown": [],
        },
        "apply_dispatch_other_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_w1_invoke_setup_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_w1_enqueue_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_w1_event_sync_wait": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_w2_invoke_setup_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_w2_enqueue_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_w2_event_sync_wait": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_other_invoke_setup_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_other_enqueue_host": {"decode": [], "prefill": [], "unknown": []},
        "apply_wna16_other_event_sync_wait": {"decode": [], "prefill": [], "unknown": []},
        "apply_moe_sum": {"decode": [], "prefill": [], "unknown": []},
        "other": {"decode": [], "prefill": [], "unknown": []},
    }
    wna16_counts: dict[str, int] = {}
    timing_kind_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    event_type_counts: Counter[str] = Counter()
    layer_phase_counts: Counter[str] = Counter()
    wna16_phase_counts: Counter[str] = Counter()
    wna16_phase_source_counts: Counter[str] = Counter()
    decoder_phase_source_counts: Counter[str] = Counter()
    decoder_component_phase_source_counts: Counter[str] = Counter()
    decoder_unknown_component_counts: Counter[str] = Counter()
    moe_substage_phase_source_counts: Counter[str] = Counter()
    moe_substage_status_counts: Counter[str] = Counter()
    line_count = 0

    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            line_count += 1
            row = json.loads(line)
            event_type = row.get("event_type")
            event_type_counts[str(event_type or "unknown")] += 1
            if event_type == "descriptor_layer_timing":
                phase = str(row.get("descriptor_order_layer_phase") or "unknown")
                layer_phase_counts[phase] += 1
                if phase != "decode":
                    continue
                value = row.get("descriptor_order_layer_apply_us")
                if value is not None:
                    decode_layer_apply.append(float(value))
                continue
            if event_type == "decoder_layer_timing":
                phase = str(row.get("decoder_layer_phase") or "unknown")
                if phase not in decoder_layer:
                    phase = "unknown"
                source = str(row.get("decoder_layer_phase_source") or "unknown")
                decoder_phase_source_counts[source] += 1
                value = row.get("decoder_layer_elapsed_us")
                if value is not None:
                    decoder_layer[phase].append(float(value))
                continue
            if event_type == "decoder_component_timing":
                component = str(row.get("decoder_component") or "other")
                if component not in decoder_component:
                    decoder_unknown_component_counts[component] += 1
                    decoder_component[component] = _phase_buckets()
                phase = str(row.get("decoder_component_phase") or "unknown")
                if phase not in decoder_component[component]:
                    phase = "unknown"
                source = str(row.get("decoder_component_phase_source") or "unknown")
                decoder_component_phase_source_counts[source] += 1
                value = row.get("decoder_component_elapsed_us")
                if value is not None:
                    decoder_component[component][phase].append(float(value))
                continue
            if event_type == "decoder_component_aggregate":
                phase = str(row.get("decoder_component_phase") or "unknown")
                if phase not in {"decode", "prefill", "unknown"}:
                    phase = "unknown"
                source = str(row.get("decoder_component_phase_source") or "unknown")
                decoder_component_phase_source_counts[source] += 1
                components = row.get("decoder_component_aggregate_components") or {}
                if isinstance(components, dict):
                    for component, component_payload in components.items():
                        component_name = str(component or "other")
                        if component_name not in decoder_component:
                            decoder_unknown_component_counts[component_name] += 1
                            decoder_component[component_name] = _phase_buckets()
                        if isinstance(component_payload, dict):
                            value = component_payload.get("sum_us")
                        else:
                            value = component_payload
                        if value is not None:
                            decoder_component[component_name][phase].append(float(value))
                continue
            if event_type == "moe_substage_timing":
                substage = str(row.get("moe_substage") or "other")
                if substage not in moe_substage:
                    substage = "other"
                phase = str(row.get("moe_substage_phase") or "unknown")
                if substage.startswith("apply_wna16_w1_") or substage.startswith(
                    "apply_wna16_w2_"
                ):
                    phase = "decode"
                if phase not in moe_substage[substage]:
                    phase = "unknown"
                source = str(row.get("moe_substage_phase_source") or "unknown")
                moe_substage_phase_source_counts[source] += 1
                status = str(row.get("moe_substage_status") or "unknown")
                moe_substage_status_counts[f"{substage}:{status}"] += 1
                value = row.get("moe_substage_elapsed_us")
                if value is not None:
                    moe_substage[substage][phase].append(float(value))
                continue
            if event_type == "moe_substage_aggregate":
                phase = str(row.get("moe_substage_phase") or "unknown")
                if phase not in {"decode", "prefill", "unknown"}:
                    phase = "unknown"
                source = str(row.get("moe_substage_phase_source") or "unknown")
                components = row.get("moe_substage_aggregate_components") or {}
                if isinstance(components, dict):
                    for substage_name, substage_payload in components.items():
                        substage = str(substage_name or "other")
                        if substage not in moe_substage:
                            substage = "other"
                        component_phase = phase
                        if substage.startswith("apply_wna16_w1_") or substage.startswith(
                            "apply_wna16_w2_"
                        ):
                            component_phase = "decode"
                        if component_phase not in moe_substage[substage]:
                            component_phase = "unknown"
                        if isinstance(substage_payload, dict):
                            value = substage_payload.get("sum_us")
                            count = int(substage_payload.get("count") or 0)
                            estimated_count = int(
                                substage_payload.get("estimated_count") or count
                            )
                            status_counts = (
                                substage_payload.get("status_counts") or {}
                            )
                            estimated_status_counts = (
                                substage_payload.get("estimated_status_counts")
                                or status_counts
                            )
                        else:
                            value = substage_payload
                            count = 1
                            estimated_count = 1
                            status_counts = {}
                            estimated_status_counts = {}
                        moe_substage_phase_source_counts[source] += max(
                            estimated_count,
                            1,
                        )
                        if (
                            isinstance(estimated_status_counts, dict)
                            and estimated_status_counts
                        ):
                            for status, status_count in (
                                estimated_status_counts.items()
                            ):
                                moe_substage_status_counts[
                                    f"{substage}:{status}"
                                ] += int(status_count)
                        else:
                            moe_substage_status_counts[
                                f"{substage}:aggregate"
                            ] += max(count, 1)
                        if value is not None:
                            moe_substage[substage][component_phase].append(float(value))
                continue
            if event_type == "engine_substage_timing":
                substage = str(row.get("engine_substage") or "other")
                engine_substage.setdefault(substage, [])
                value = row.get("engine_substage_elapsed_us")
                if value is not None:
                    engine_substage[substage].append(float(value))
                continue
            if event_type != "wna16_kernel_timing":
                continue
            phase = str(
                row.get("descriptor_order_layer_phase")
                or row.get("wna16_phase")
                or row.get("phase")
                or "unknown"
            )
            wna16_phase_counts[phase] += 1
            phase_source = str(row.get("wna16_phase_source") or "unknown")
            wna16_phase_source_counts[phase_source] += 1
            bucket = str(row.get("wna16_bucket") or "other")
            if bucket not in wna16_host:
                bucket = "other"
            if phase not in wna16_host_by_phase[bucket]:
                phase = "unknown"
            host = row.get("wna16_kernel_elapsed_us")
            gpu = row.get("wna16_kernel_gpu_elapsed_us")
            if host is not None:
                value = float(host)
                wna16_host[bucket].append(value)
                wna16_host_by_phase[bucket][phase].append(value)
            if gpu is not None:
                value = float(gpu)
                wna16_gpu[bucket].append(value)
                wna16_gpu_by_phase[bucket][phase].append(value)
            key = f"{bucket}:M={row.get('wna16_num_tokens')}:topk={row.get('wna16_top_k')}"
            wna16_counts[key] = wna16_counts.get(key, 0) + 1
            kind = str(row.get("wna16_kernel_timing_kind") or "unknown")
            timing_kind_counts[kind] = timing_kind_counts.get(kind, 0) + 1
            status = str(row.get("wna16_status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "decode_layer_apply_us": _quantiles(decode_layer_apply),
        "wna16_host_us": {
            bucket: _quantiles(values) for bucket, values in wna16_host.items()
        },
        "wna16_gpu_us": {
            bucket: _quantiles(values) for bucket, values in wna16_gpu.items()
        },
        "wna16_host_us_by_phase": {
            bucket: {
                phase: _quantiles(values)
                for phase, values in phase_values.items()
            }
            for bucket, phase_values in wna16_host_by_phase.items()
        },
        "wna16_gpu_us_by_phase": {
            bucket: {
                phase: _quantiles(values)
                for phase, values in phase_values.items()
            }
            for bucket, phase_values in wna16_gpu_by_phase.items()
        },
        "decoder_layer_us": {
            phase: _quantiles(values) for phase, values in decoder_layer.items()
        },
        "decoder_component_us": {
            component: {
                phase: _quantiles(values)
                for phase, values in phase_values.items()
            }
            for component, phase_values in decoder_component.items()
        },
        "moe_substage_us": {
            substage: {
                phase: _quantiles(values)
                for phase, values in phase_values.items()
            }
            for substage, phase_values in moe_substage.items()
        },
        "engine_substage_us": {
            substage: _quantiles(values)
            for substage, values in sorted(engine_substage.items())
        },
        "wna16_counts": wna16_counts,
        "wna16_timing_kind_counts": timing_kind_counts,
        "wna16_status_counts": status_counts,
        "integrity": {
            "line_count": line_count,
            "event_type_counts": dict(sorted(event_type_counts.items())),
            "descriptor_layer_phase_counts": dict(sorted(layer_phase_counts.items())),
            "wna16_phase_counts": dict(sorted(wna16_phase_counts.items())),
            "wna16_phase_source_counts": dict(
                sorted(wna16_phase_source_counts.items())
            ),
            "decoder_phase_source_counts": dict(
                sorted(decoder_phase_source_counts.items())
            ),
            "decoder_component_phase_source_counts": dict(
                sorted(decoder_component_phase_source_counts.items())
            ),
            "decoder_unknown_component_counts": dict(
                sorted(decoder_unknown_component_counts.items())
            ),
            "moe_substage_phase_source_counts": dict(
                sorted(moe_substage_phase_source_counts.items())
            ),
            "moe_substage_status_counts": dict(
                sorted(moe_substage_status_counts.items())
            ),
            "wna16_decode_filter_available": (
                bool(wna16_phase_counts)
                and set(wna16_phase_counts) <= {"decode"}
                and set(wna16_phase_source_counts)
                <= {"explicit", "num_tokens_topk_heuristic"}
            ),
            "wna16_gpu_event_timing_diagnostic_only": (
                event_type_counts.get("wna16_kernel_timing", 0) > 0
            ),
        },
    }


def _pct(part_us: float, total_us: float | None) -> float | None:
    if not total_us or total_us <= 0:
        return None
    return 100.0 * float(part_us) / float(total_us)


def _pct_optional(part_us: float | None, total_us: float | None) -> float | None:
    if part_us is None:
        return None
    return _pct(float(part_us), total_us)


def _fmt(value: float | None, suffix: str = "") -> str:
    if value is None:
        return ""
    return f"{float(value):.3f}{suffix}"


def _per_token_ms(value_us: float | None, output_tokens: int | None) -> float | None:
    if value_us is None or not output_tokens:
        return None
    return float(value_us) / 1000.0 / float(output_tokens)


def _per_layer_us(value_us: float | None, layer_count: int | None) -> float | None:
    if value_us is None or not layer_count:
        return None
    return float(value_us) / float(layer_count)


def _decode_sum(stats: dict[str, dict[str, Any]], key: str) -> float | None:
    row = stats[key]["decode"]
    return float(row.get("sum_us") or 0.0) if row.get("count") else None


def _zero_if_missing(value: float | None) -> float:
    return 0.0 if value is None else float(value)


def build_breakdown(trace_dir: Path) -> dict[str, Any]:
    perf = _load_json(trace_dir / "performance_summary.json")
    required_perf = (
        "generate_wall_seconds",
        "requested_output_token_count",
        "sample_count",
    )
    missing = [key for key in required_perf if perf.get(key) is None]
    if missing:
        raise KeyError(
            f"performance_summary.json is missing required fields: {missing}"
        )
    shadow_path = trace_dir / "runtime_shadow.jsonl"
    shadow = _read_shadow(shadow_path)
    generate_us = (
        float(perf["generate_wall_seconds"]) * 1_000_000.0
        if perf.get("generate_wall_seconds") is not None
        else None
    )
    moe_sum = float(shadow["decode_layer_apply_us"].get("sum_us") or 0.0)
    decoder_decode_stats = shadow["decoder_layer_us"]["decode"]
    decoder_decode_sum = (
        float(decoder_decode_stats.get("sum_us") or 0.0)
        if decoder_decode_stats.get("count")
        else None
    )
    attention_decode_stats = shadow["decoder_component_us"]["attention"]["decode"]
    attention_decode_sum = (
        float(attention_decode_stats.get("sum_us") or 0.0)
        if attention_decode_stats.get("count")
        else None
    )
    mlp_decode_stats = shadow["decoder_component_us"]["mlp"]["decode"]
    mlp_decode_sum = (
        float(mlp_decode_stats.get("sum_us") or 0.0)
        if mlp_decode_stats.get("count")
        else None
    )
    decoder_source_component_names = [
        "decoder_input_layernorm",
        "decoder_linear_attention",
        "decoder_full_attention",
        "decoder_attention_layer_scale",
        "decoder_post_attention_layernorm",
        "decoder_mlp_call",
        "decoder_ffn_layer_scale",
    ]
    decoder_source_sums = {
        name: (
            float(shadow["decoder_component_us"][name]["decode"].get("sum_us") or 0.0)
            if shadow["decoder_component_us"][name]["decode"].get("count")
            else None
        )
        for name in decoder_source_component_names
    }
    decoder_source_parts_sum = (
        sum(float(value) for value in decoder_source_sums.values() if value is not None)
        if any(value is not None for value in decoder_source_sums.values())
        else None
    )
    decoder_source_attention_sum = (
        _zero_if_missing(decoder_source_sums.get("decoder_linear_attention"))
        + _zero_if_missing(decoder_source_sums.get("decoder_full_attention"))
        if decoder_source_sums.get("decoder_linear_attention") is not None
        or decoder_source_sums.get("decoder_full_attention") is not None
        else None
    )
    attention_linear_leaf_names = [
        "attention_linear_input_proj",
        "attention_linear_ba_proj",
        "attention_linear_conv1d",
        "attention_linear_norm",
        "attention_linear_core",
        "attention_linear_out_proj",
        "attention_linear_leaf_other",
    ]
    attention_linear_source_method_names = [
        "attention_linear_core_total",
        "attention_linear_core_decode_non_spec",
        "attention_linear_core_conv_update",
        "attention_linear_core_recurrent",
        "attention_linear_layout_unpack",
    ]
    attention_linear_handoff_names = [
        "attention_linear_handoff_linear_proj_total",
        "attention_linear_handoff_norm",
        "attention_linear_handoff_core_total",
        "attention_linear_handoff_core_decode_non_spec",
        "attention_linear_handoff_conv_update",
        "attention_linear_handoff_recurrent",
        "attention_linear_handoff_core_post_layout",
        "attention_linear_handoff_out_proj",
    ]
    attention_full_leaf_names = [
        "attention_full_qkv_proj",
        "attention_full_qk_norm",
        "attention_full_rope",
        "attention_full_core",
        "attention_full_o_proj",
        "attention_full_leaf_other",
    ]
    attention_leaf_names = attention_linear_leaf_names + attention_full_leaf_names
    attention_leaf_sums = {
        name: (
            float(shadow["decoder_component_us"][name]["decode"].get("sum_us") or 0.0)
            if name in shadow["decoder_component_us"]
            and shadow["decoder_component_us"][name]["decode"].get("count")
            else None
        )
        for name in attention_leaf_names
    }
    attention_linear_source_method_sums = {
        name: (
            float(shadow["decoder_component_us"][name]["decode"].get("sum_us") or 0.0)
            if name in shadow["decoder_component_us"]
            and shadow["decoder_component_us"][name]["decode"].get("count")
            else None
        )
        for name in attention_linear_source_method_names
    }
    attention_linear_handoff_sums = {
        name: (
            float(shadow["decoder_component_us"][name]["decode"].get("sum_us") or 0.0)
            if name in shadow["decoder_component_us"]
            and shadow["decoder_component_us"][name]["decode"].get("count")
            else None
        )
        for name in attention_linear_handoff_names
    }
    handoff_core_decode_non_spec_sum = attention_linear_handoff_sums.get(
        "attention_linear_handoff_core_decode_non_spec"
    )
    handoff_conv_update_sum = attention_linear_handoff_sums.get(
        "attention_linear_handoff_conv_update"
    )
    handoff_recurrent_sum = attention_linear_handoff_sums.get(
        "attention_linear_handoff_recurrent"
    )
    attention_linear_handoff_core_prep_layout_sum = (
        handoff_core_decode_non_spec_sum
        - _zero_if_missing(handoff_conv_update_sum)
        - _zero_if_missing(handoff_recurrent_sum)
        if handoff_core_decode_non_spec_sum is not None
        else None
    )
    if attention_linear_handoff_sums.get(
        "attention_linear_handoff_core_post_layout"
    ) is None and attention_linear_handoff_sums.get(
        "attention_linear_handoff_core_total"
    ) is not None:
        core_total = attention_linear_handoff_sums[
            "attention_linear_handoff_core_total"
        ]
        attention_linear_handoff_sums["attention_linear_handoff_core_post_layout"] = (
            core_total - _zero_if_missing(handoff_core_decode_non_spec_sum)
        )
    attention_linear_leaf_sum = (
        sum(
            float(attention_leaf_sums[name])
            for name in attention_linear_leaf_names
            if attention_leaf_sums.get(name) is not None
        )
        if any(attention_leaf_sums.get(name) is not None for name in attention_linear_leaf_names)
        else None
    )
    attention_full_leaf_sum = (
        sum(
            float(attention_leaf_sums[name])
            for name in attention_full_leaf_names
            if attention_leaf_sums.get(name) is not None
        )
        if any(attention_leaf_sums.get(name) is not None for name in attention_full_leaf_names)
        else None
    )
    attention_leaf_parts_sum = (
        _zero_if_missing(attention_linear_leaf_sum)
        + _zero_if_missing(attention_full_leaf_sum)
        if attention_linear_leaf_sum is not None or attention_full_leaf_sum is not None
        else None
    )
    attention_linear_source_method_sum = (
        sum(
            float(value)
            for value in attention_linear_source_method_sums.values()
            if value is not None
        )
        if any(
            value is not None for value in attention_linear_source_method_sums.values()
        )
        else None
    )
    attention_source_minus_leaf_parts = (
        decoder_source_attention_sum - attention_leaf_parts_sum
        if decoder_source_attention_sum is not None and attention_leaf_parts_sum is not None
        else None
    )
    decoder_source_mlp_sum = decoder_source_sums.get("decoder_mlp_call")
    decoder_layer_minus_source_parts = (
        decoder_decode_sum - decoder_source_parts_sum
        if decoder_decode_sum is not None and decoder_source_parts_sum is not None
        else None
    )
    moe_substage_stats = shadow["moe_substage_us"]
    engine_substage_stats = shadow.get("engine_substage_us", {})
    engine_substage_sums = {
        name: (
            float(stats.get("sum_us") or 0.0)
            if stats.get("count")
            else None
        )
        for name, stats in engine_substage_stats.items()
    }
    engine_generate_call_sum = engine_substage_sums.get("engine_llm_generate_call")
    engine_execute_model_sum = engine_substage_sums.get("engine_execute_model")
    engine_model_forward_sum = engine_substage_sums.get("engine_model_forward")
    engine_generate_minus_execute_model = (
        engine_generate_call_sum - engine_execute_model_sum
        if engine_generate_call_sum is not None
        and engine_execute_model_sum is not None
        else None
    )
    engine_execute_model_minus_model_forward = (
        engine_execute_model_sum - engine_model_forward_sum
        if engine_execute_model_sum is not None
        and engine_model_forward_sum is not None
        else None
    )
    router_logits_sum = _decode_sum(moe_substage_stats, "router_logits")
    experts_total_sum = _decode_sum(moe_substage_stats, "experts_total")
    select_experts_sum = _decode_sum(moe_substage_stats, "select_experts")
    select_validate_sum = _decode_sum(moe_substage_stats, "select_validate_eplb")
    select_indices_sum = _decode_sum(moe_substage_stats, "select_indices_type")
    select_compute_sum = _decode_sum(moe_substage_stats, "select_compute_routing")
    select_capture_sum = _decode_sum(moe_substage_stats, "select_capture_logical_ids")
    select_eplb_sum = _decode_sum(moe_substage_stats, "select_eplb_mapping")
    select_convert_sum = _decode_sum(moe_substage_stats, "select_dtype_convert")
    select_record_sum = _decode_sum(moe_substage_stats, "select_record_topk")
    experts_shared_stream_sync_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_stream_sync",
    )
    experts_maybe_dispatch_sum = _decode_sum(
        moe_substage_stats,
        "experts_maybe_dispatch",
    )
    experts_maybe_combine_sum = _decode_sum(
        moe_substage_stats,
        "experts_maybe_combine",
    )
    experts_shared_no_overlap_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_no_overlap",
    )
    experts_shared_determine_order_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_determine_order",
    )
    experts_shared_apply_skipped_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_apply_skipped",
    )
    experts_shared_w1_sum = _decode_sum(moe_substage_stats, "experts_shared_w1")
    experts_shared_activation_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_activation",
    )
    experts_shared_w2_sum = _decode_sum(moe_substage_stats, "experts_shared_w2")
    experts_shared_output_combine_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_output_combine",
    )
    experts_shared_output_gate_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_output_gate",
    )
    experts_shared_output_sigmoid_mul_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_output_sigmoid_mul",
    )
    experts_shared_output_gate_fused_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_output_gate_fused",
    )
    experts_shared_child_other_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_child_other",
    )
    experts_shared_direct_layer_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_direct_layer",
    )
    experts_shared_body_core_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_body_core",
    )
    experts_shared_body_gate_proj_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_body_gate_proj",
    )
    experts_shared_body_gate_apply_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_body_gate_apply",
    )
    experts_shared_body_gate_fused_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_body_gate_fused",
    )
    experts_shared_aux_stream_layer_wait_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_aux_stream_layer_wait",
    )
    experts_pre_quant_glue_sum = _decode_sum(
        moe_substage_stats,
        "experts_pre_quant_apply_glue",
    )
    experts_shared_overlap_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_overlap",
    )
    experts_shared_output_fetch_sum = _decode_sum(
        moe_substage_stats,
        "experts_shared_output_fetch",
    )
    prepare_assignment_sum = _decode_sum(
        moe_substage_stats,
        "prepare_expert_assignment",
    )
    quant_apply_sum = _decode_sum(moe_substage_stats, "quant_method_apply")
    quant_apply_monolithic_sum = _decode_sum(
        moe_substage_stats,
        "quant_method_apply_monolithic",
    )
    quant_apply_effective_sum = (
        quant_apply_sum
        if quant_apply_sum is not None
        else quant_apply_monolithic_sum
    )
    apply_problem_size_sum = _decode_sum(moe_substage_stats, "apply_problem_size")
    apply_config_lookup_sum = _decode_sum(moe_substage_stats, "apply_config_lookup")
    apply_source_fused_experts_outer_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_fused_experts_outer",
    )
    apply_source_outer_quant_config_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_outer_quant_config",
    )
    apply_source_outer_inplace_assert_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_outer_inplace_assert",
    )
    apply_source_outer_dispatch_select_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_outer_dispatch_select",
    )
    apply_source_outer_impl_call_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_outer_impl_call",
    )
    apply_source_impl_total_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_impl_total",
    )
    apply_source_impl_entry_overhead_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_impl_entry_overhead",
    )
    apply_source_emit_overhead_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_emit_overhead",
    )
    apply_source_pre_dispatch_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_pre_dispatch",
    )
    apply_source_workspace_alloc_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_workspace_alloc",
    )
    apply_source_quantize_hidden_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_quantize_hidden",
    )
    apply_source_prepare_assignment_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_prepare_assignment",
    )
    apply_source_w1_enqueue_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_w1_enqueue",
    )
    apply_source_w1_post_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_w1_post",
    )
    apply_source_activation_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_activation",
    )
    apply_source_quantize_intermediate_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_quantize_intermediate",
    )
    apply_source_w2_pre_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_w2_pre",
    )
    apply_source_w2_enqueue_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_w2_enqueue",
    )
    apply_source_w2_post_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_w2_post",
    )
    apply_source_combine_scatter_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_combine_scatter",
    )
    apply_source_post_dispatch_sum = _decode_sum(
        moe_substage_stats,
        "apply_source_post_dispatch",
    )
    apply_resize_cache_w1_sum = _decode_sum(
        moe_substage_stats,
        "apply_resize_cache_w1_output",
    )
    apply_resize_cache_activation_sum = _decode_sum(
        moe_substage_stats,
        "apply_resize_cache_activation",
    )
    apply_resize_cache_w2_sum = _decode_sum(
        moe_substage_stats,
        "apply_resize_cache_w2_output",
    )
    apply_resize_cache_other_sum = _decode_sum(
        moe_substage_stats,
        "apply_resize_cache_other",
    )
    apply_quantize_hidden_sum = _decode_sum(moe_substage_stats, "apply_quantize_hidden")
    apply_dispatch_w1_host_sum = _decode_sum(moe_substage_stats, "apply_dispatch_w1_host")
    apply_dispatch_w1_pre_invoke_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_w1_host_pre_invoke",
    )
    apply_dispatch_w1_cuda_decision_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_w1_host_cuda_decision",
    )
    apply_dispatch_w1_invoke_call_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_w1_host_invoke_call",
    )
    apply_activation_sum = _decode_sum(moe_substage_stats, "apply_activation")
    apply_quantize_intermediate_sum = _decode_sum(
        moe_substage_stats,
        "apply_quantize_intermediate",
    )
    apply_dispatch_w2_host_sum = _decode_sum(moe_substage_stats, "apply_dispatch_w2_host")
    apply_dispatch_w2_pre_invoke_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_w2_host_pre_invoke",
    )
    apply_dispatch_w2_cuda_decision_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_w2_host_cuda_decision",
    )
    apply_dispatch_w2_invoke_call_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_w2_host_invoke_call",
    )
    apply_dispatch_other_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_dispatch_other_host",
    )
    wna16_w1_setup_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_w1_invoke_setup_host",
    )
    wna16_w1_enqueue_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_w1_enqueue_host",
    )
    wna16_w1_sync_wait_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_w1_event_sync_wait",
    )
    wna16_w2_setup_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_w2_invoke_setup_host",
    )
    wna16_w2_enqueue_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_w2_enqueue_host",
    )
    wna16_w2_sync_wait_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_w2_event_sync_wait",
    )
    wna16_other_setup_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_other_invoke_setup_host",
    )
    wna16_other_enqueue_host_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_other_enqueue_host",
    )
    wna16_other_sync_wait_sum = _decode_sum(
        moe_substage_stats,
        "apply_wna16_other_event_sync_wait",
    )
    apply_moe_sum_sum = _decode_sum(moe_substage_stats, "apply_moe_sum")
    select_minus_record_topk = (
        select_experts_sum - select_record_sum
        if select_experts_sum is not None and select_record_sum is not None
        else None
    )
    measured_apply_parts = [
        apply_problem_size_sum,
        apply_config_lookup_sum,
        apply_resize_cache_w1_sum,
        apply_resize_cache_activation_sum,
        apply_resize_cache_w2_sum,
        apply_resize_cache_other_sum,
        prepare_assignment_sum,
        apply_quantize_hidden_sum,
        apply_dispatch_w1_host_sum,
        apply_activation_sum,
        apply_quantize_intermediate_sum,
        apply_dispatch_w2_host_sum,
        apply_dispatch_other_host_sum,
        apply_moe_sum_sum,
    ]
    apply_measured_parts_sum = (
        sum(float(value) for value in measured_apply_parts if value is not None)
        if any(value is not None for value in measured_apply_parts)
        else None
    )
    measured_experts_nonapply_parts = [
        experts_shared_stream_sync_sum,
        experts_maybe_dispatch_sum,
        select_experts_sum,
        experts_shared_no_overlap_sum,
        experts_pre_quant_glue_sum,
        experts_shared_overlap_sum,
        experts_shared_output_fetch_sum,
        experts_maybe_combine_sum,
    ]
    experts_nonapply_measured_parts_sum = (
        sum(float(value) for value in measured_experts_nonapply_parts if value is not None)
        if any(value is not None for value in measured_experts_nonapply_parts)
        else None
    )
    quant_apply_minus_measured_parts = (
        quant_apply_sum - apply_measured_parts_sum
        if quant_apply_sum is not None and apply_measured_parts_sum is not None
        else None
    )
    shared_no_overlap_inner_parts = [
        experts_shared_determine_order_sum,
        experts_shared_apply_skipped_sum,
        experts_shared_direct_layer_sum,
        experts_shared_aux_stream_layer_wait_sum,
    ]
    shared_no_overlap_inner_parts_sum = (
        sum(float(value) for value in shared_no_overlap_inner_parts if value is not None)
        if any(value is not None for value in shared_no_overlap_inner_parts)
        else None
    )
    shared_no_overlap_minus_inner_parts = (
        experts_shared_no_overlap_sum - shared_no_overlap_inner_parts_sum
        if experts_shared_no_overlap_sum is not None
        and shared_no_overlap_inner_parts_sum is not None
        else None
    )
    shared_output_detailed_parts = (
        [experts_shared_output_gate_fused_sum]
        if experts_shared_output_gate_fused_sum is not None
        else [
            experts_shared_output_gate_sum,
            experts_shared_output_sigmoid_mul_sum,
        ]
    )
    shared_output_detailed_complete = all(
        value is not None for value in shared_output_detailed_parts
    )
    shared_output_detailed_parts_sum = (
        sum(float(value) for value in shared_output_detailed_parts if value is not None)
        if shared_output_detailed_complete
        else None
    )
    shared_output_effective_sum = (
        shared_output_detailed_parts_sum
        if shared_output_detailed_complete
        else experts_shared_output_combine_sum
    )
    shared_direct_source_parts = [
        experts_shared_w1_sum,
        experts_shared_activation_sum,
        experts_shared_w2_sum,
        shared_output_effective_sum,
        experts_shared_child_other_sum,
    ]
    shared_direct_source_parts_sum = (
        sum(float(value) for value in shared_direct_source_parts if value is not None)
        if any(value is not None for value in shared_direct_source_parts)
        else None
    )
    shared_direct_minus_source_parts = (
        experts_shared_direct_layer_sum - shared_direct_source_parts_sum
        if experts_shared_direct_layer_sum is not None
        and shared_direct_source_parts_sum is not None
        else None
    )
    shared_body_region_gate_parts = (
        [experts_shared_body_gate_fused_sum]
        if experts_shared_body_gate_fused_sum is not None
        else [
            experts_shared_body_gate_proj_sum,
            experts_shared_body_gate_apply_sum,
        ]
    )
    shared_body_region_parts = [
        experts_shared_body_core_sum,
        *shared_body_region_gate_parts,
    ]
    shared_body_region_parts_sum = (
        sum(float(value) for value in shared_body_region_parts if value is not None)
        if any(value is not None for value in shared_body_region_parts)
        else None
    )
    shared_direct_minus_body_region_parts = (
        experts_shared_direct_layer_sum - shared_body_region_parts_sum
        if experts_shared_direct_layer_sum is not None
        and shared_body_region_parts_sum is not None
        else None
    )
    apply_source_parts = [
        apply_source_pre_dispatch_sum,
        apply_source_workspace_alloc_sum,
        apply_source_quantize_hidden_sum,
        apply_source_prepare_assignment_sum,
        apply_source_w1_enqueue_sum,
        apply_source_w1_post_sum,
        apply_source_activation_sum,
        apply_source_quantize_intermediate_sum,
        apply_source_w2_pre_sum,
        apply_source_w2_enqueue_sum,
        apply_source_w2_post_sum,
        apply_source_combine_scatter_sum,
        apply_source_post_dispatch_sum,
    ]
    apply_source_parts_sum = (
        sum(float(value) for value in apply_source_parts if value is not None)
        if any(value is not None for value in apply_source_parts)
        else None
    )
    quant_apply_minus_source_parts = (
        quant_apply_sum - apply_source_parts_sum
        if quant_apply_sum is not None and apply_source_parts_sum is not None
        else None
    )
    quant_apply_minus_fused_experts_outer = (
        quant_apply_sum - apply_source_fused_experts_outer_sum
        if quant_apply_sum is not None
        and apply_source_fused_experts_outer_sum is not None
        else None
    )
    fused_experts_outer_minus_inner_source_parts = (
        apply_source_fused_experts_outer_sum - apply_source_parts_sum
        if apply_source_fused_experts_outer_sum is not None
        and apply_source_parts_sum is not None
        else None
    )
    fused_experts_outer_minus_impl_total = (
        apply_source_fused_experts_outer_sum - apply_source_impl_total_sum
        if apply_source_fused_experts_outer_sum is not None
        and apply_source_impl_total_sum is not None
        else None
    )
    fused_experts_impl_total_minus_inner_source_parts = (
        apply_source_impl_total_sum - apply_source_parts_sum
        if apply_source_impl_total_sum is not None
        and apply_source_parts_sum is not None
        else None
    )
    fused_experts_impl_total_minus_inner_source_parts_emit_adjusted = (
        fused_experts_impl_total_minus_inner_source_parts
        - _zero_if_missing(apply_source_emit_overhead_sum)
        if fused_experts_impl_total_minus_inner_source_parts is not None
        else None
    )
    apply_outer_parts = [
        apply_source_outer_quant_config_sum,
        apply_source_outer_inplace_assert_sum,
        apply_source_outer_dispatch_select_sum,
        apply_source_outer_impl_call_sum,
    ]
    apply_outer_parts_sum = (
        sum(float(value) for value in apply_outer_parts if value is not None)
        if any(value is not None for value in apply_outer_parts)
        else None
    )
    fused_experts_outer_minus_outer_parts = (
        apply_source_fused_experts_outer_sum - apply_outer_parts_sum
        if apply_source_fused_experts_outer_sum is not None
        and apply_outer_parts_sum is not None
        else None
    )
    fused_experts_outer_impl_call_minus_impl_total = (
        apply_source_outer_impl_call_sum - apply_source_impl_total_sum
        if apply_source_outer_impl_call_sum is not None
        and apply_source_impl_total_sum is not None
        else None
    )
    fused_experts_outer_impl_call_minus_impl_total_named_overhead = (
        _zero_if_missing(apply_source_impl_entry_overhead_sum)
        + _zero_if_missing(apply_source_emit_overhead_sum)
        if apply_source_impl_entry_overhead_sum is not None
        or apply_source_emit_overhead_sum is not None
        else None
    )
    fused_experts_outer_impl_call_minus_impl_total_unclassified = (
        fused_experts_outer_impl_call_minus_impl_total
        - _zero_if_missing(
            fused_experts_outer_impl_call_minus_impl_total_named_overhead
        )
        if fused_experts_outer_impl_call_minus_impl_total is not None
        else None
    )
    w1_gpu_decode_stats = shadow.get("wna16_gpu_us_by_phase", {}).get("w1", {}).get("decode", {})
    w2_gpu_decode_stats = shadow.get("wna16_gpu_us_by_phase", {}).get("w2", {}).get("decode", {})
    w1_gpu_sum = float(w1_gpu_decode_stats.get("sum_us") or 0.0)
    w2_gpu_sum = float(w2_gpu_decode_stats.get("sum_us") or 0.0)
    other_gpu_decode_stats = shadow.get("wna16_gpu_us_by_phase", {}).get("other", {}).get("decode", {})
    other_gpu_sum = float(other_gpu_decode_stats.get("sum_us") or 0.0)
    wna16_gpu_sum = w1_gpu_sum + w2_gpu_sum + other_gpu_sum
    w1_host_minus_gpu = (
        apply_dispatch_w1_host_sum - w1_gpu_sum
        if apply_dispatch_w1_host_sum is not None
        else None
    )
    w2_host_minus_gpu = (
        apply_dispatch_w2_host_sum - w2_gpu_sum
        if apply_dispatch_w2_host_sum is not None
        else None
    )
    dispatch_host_minus_wna16_gpu = (
        apply_dispatch_w1_host_sum
        + apply_dispatch_w2_host_sum
        - w1_gpu_sum
        - w2_gpu_sum
        if apply_dispatch_w1_host_sum is not None
        and apply_dispatch_w2_host_sum is not None
        else None
    )
    w1_dispatch_host_minus_launch_parts = (
        apply_dispatch_w1_host_sum
        - _zero_if_missing(wna16_w1_setup_host_sum)
        - _zero_if_missing(wna16_w1_enqueue_host_sum)
        - _zero_if_missing(wna16_w1_sync_wait_sum)
        if apply_dispatch_w1_host_sum is not None
        and wna16_w1_setup_host_sum is not None
        and wna16_w1_enqueue_host_sum is not None
        else None
    )
    w1_dispatch_source_parts_sum = (
        _zero_if_missing(apply_dispatch_w1_pre_invoke_sum)
        + _zero_if_missing(apply_dispatch_w1_cuda_decision_sum)
        + _zero_if_missing(apply_dispatch_w1_invoke_call_sum)
        if apply_dispatch_w1_pre_invoke_sum is not None
        or apply_dispatch_w1_cuda_decision_sum is not None
        or apply_dispatch_w1_invoke_call_sum is not None
        else None
    )
    w1_dispatch_host_minus_source_parts = (
        apply_dispatch_w1_host_sum - w1_dispatch_source_parts_sum
        if apply_dispatch_w1_host_sum is not None
        and w1_dispatch_source_parts_sum is not None
        else None
    )
    source_w1_enqueue_minus_launch_parts = (
        apply_source_w1_enqueue_sum
        - _zero_if_missing(wna16_w1_setup_host_sum)
        - _zero_if_missing(wna16_w1_enqueue_host_sum)
        - _zero_if_missing(wna16_w1_sync_wait_sum)
        if apply_source_w1_enqueue_sum is not None
        and wna16_w1_setup_host_sum is not None
        and wna16_w1_enqueue_host_sum is not None
        else None
    )
    source_w1_enqueue_minus_dispatch_host = (
        apply_source_w1_enqueue_sum - apply_dispatch_w1_host_sum
        if apply_source_w1_enqueue_sum is not None
        and apply_dispatch_w1_host_sum is not None
        else None
    )
    source_w2_enqueue_minus_dispatch_host = (
        apply_source_w2_enqueue_sum - apply_dispatch_w2_host_sum
        if apply_source_w2_enqueue_sum is not None
        and apply_dispatch_w2_host_sum is not None
        else None
    )
    source_w2_enqueue_minus_launch_parts = (
        apply_source_w2_enqueue_sum
        - _zero_if_missing(wna16_w2_setup_host_sum)
        - _zero_if_missing(wna16_w2_enqueue_host_sum)
        - _zero_if_missing(wna16_w2_sync_wait_sum)
        if apply_source_w2_enqueue_sum is not None
        and wna16_w2_setup_host_sum is not None
        and wna16_w2_enqueue_host_sum is not None
        else None
    )
    w2_dispatch_source_parts_sum = (
        _zero_if_missing(apply_dispatch_w2_pre_invoke_sum)
        + _zero_if_missing(apply_dispatch_w2_cuda_decision_sum)
        + _zero_if_missing(apply_dispatch_w2_invoke_call_sum)
        if apply_dispatch_w2_pre_invoke_sum is not None
        or apply_dispatch_w2_cuda_decision_sum is not None
        or apply_dispatch_w2_invoke_call_sum is not None
        else None
    )
    w2_dispatch_host_minus_source_parts = (
        apply_dispatch_w2_host_sum - w2_dispatch_source_parts_sum
        if apply_dispatch_w2_host_sum is not None
        and w2_dispatch_source_parts_sum is not None
        else None
    )
    w2_dispatch_host_minus_launch_parts = (
        apply_dispatch_w2_host_sum
        - _zero_if_missing(wna16_w2_setup_host_sum)
        - _zero_if_missing(wna16_w2_enqueue_host_sum)
        - _zero_if_missing(wna16_w2_sync_wait_sum)
        if apply_dispatch_w2_host_sum is not None
        and wna16_w2_setup_host_sum is not None
        and wna16_w2_enqueue_host_sum is not None
        else None
    )
    residual_after_moe = (
        float(generate_us) - moe_sum if generate_us is not None else None
    )
    residual_after_decoder = (
        float(generate_us) - decoder_decode_sum
        if generate_us is not None and decoder_decode_sum is not None
        else None
    )
    moe_non_wna16_gpu = moe_sum - wna16_gpu_sum
    decoder_non_moe = (
        decoder_decode_sum - moe_sum if decoder_decode_sum is not None else None
    )
    decoder_outside_attention_mlp = (
        decoder_decode_sum - attention_decode_sum - mlp_decode_sum
        if decoder_decode_sum is not None
        and attention_decode_sum is not None
        and mlp_decode_sum is not None
        else None
    )
    mlp_minus_moe = (
        mlp_decode_sum - moe_sum if mlp_decode_sum is not None else None
    )
    experts_minus_quant_apply = (
        experts_total_sum - quant_apply_effective_sum
        if experts_total_sum is not None and quant_apply_effective_sum is not None
        else None
    )
    experts_total_measured_parts_sum = (
        experts_nonapply_measured_parts_sum + quant_apply_effective_sum
        if experts_nonapply_measured_parts_sum is not None
        and quant_apply_effective_sum is not None
        else None
    )
    experts_total_minus_measured_parts = (
        experts_total_sum - experts_total_measured_parts_sum
        if experts_total_sum is not None
        and experts_total_measured_parts_sum is not None
        else None
    )
    quant_apply_minus_prepare_wna16 = (
        quant_apply_sum - prepare_assignment_sum - wna16_gpu_sum
        if quant_apply_sum is not None and prepare_assignment_sum is not None
        else None
    )
    moe_apply_minus_prepare_wna16 = (
        moe_sum - prepare_assignment_sum - wna16_gpu_sum
        if prepare_assignment_sum is not None
        else None
    )
    anomalies = {
        "attention_linear_handoff_core_prep_layout_negative": (
            attention_linear_handoff_core_prep_layout_sum is not None
            and attention_linear_handoff_core_prep_layout_sum < 0.0
        ),
        "attention_linear_handoff_core_post_layout_negative": (
            attention_linear_handoff_sums.get(
                "attention_linear_handoff_core_post_layout"
            )
            is not None
            and attention_linear_handoff_sums[
                "attention_linear_handoff_core_post_layout"
            ]
            < 0.0
        ),
        "generate_minus_decode_moe_apply_negative": (
            residual_after_moe is not None and residual_after_moe < 0.0
        ),
        "generate_minus_decode_decoder_layer_negative": (
            residual_after_decoder is not None and residual_after_decoder < 0.0
        ),
        "decode_decoder_layer_minus_moe_apply_negative": (
            decoder_non_moe is not None and decoder_non_moe < 0.0
        ),
        "decode_decoder_outside_attention_mlp_negative": (
            decoder_outside_attention_mlp is not None
            and decoder_outside_attention_mlp < 0.0
        ),
        "decode_mlp_minus_moe_apply_negative": (
            mlp_minus_moe is not None and mlp_minus_moe < 0.0
        ),
        "experts_total_minus_quant_apply_negative": (
            experts_minus_quant_apply is not None
            and experts_minus_quant_apply < 0.0
        ),
        "experts_total_minus_measured_parts_negative": (
            experts_total_minus_measured_parts is not None
            and experts_total_minus_measured_parts < 0.0
        ),
        "quant_apply_minus_prepare_wna16_negative": (
            quant_apply_minus_prepare_wna16 is not None
            and quant_apply_minus_prepare_wna16 < 0.0
        ),
        "select_experts_minus_record_topk_negative": (
            select_minus_record_topk is not None and select_minus_record_topk < 0.0
        ),
        "quant_apply_minus_measured_parts_negative": (
            quant_apply_minus_measured_parts is not None
            and quant_apply_minus_measured_parts < 0.0
        ),
        "moe_apply_minus_prepare_wna16_negative": (
            moe_apply_minus_prepare_wna16 is not None
            and moe_apply_minus_prepare_wna16 < 0.0
        ),
        "moe_apply_minus_wna16_gpu_event_negative": moe_non_wna16_gpu < 0.0,
    }
    return {
        "trace_dir": str(trace_dir),
        "performance": {
            "sample_count": perf.get("sample_count"),
            "requested_output_token_count": perf.get("requested_output_token_count"),
            "generate_wall_seconds": perf.get("generate_wall_seconds"),
            "generate_seconds_per_requested_output_token": perf.get(
                "generate_seconds_per_requested_output_token"
            ),
        },
        "shadow": shadow,
        "sums_us": {
            "generate": generate_us,
            "decode_decoder_layer": decoder_decode_sum,
            "decode_attention": attention_decode_sum,
            "decode_mlp": mlp_decode_sum,
            "decode_source_parts_sum": decoder_source_parts_sum,
            "decode_source_attention": decoder_source_attention_sum,
            "decode_attention_leaf_parts_sum": attention_leaf_parts_sum,
            "decode_attention_linear_leaf_parts_sum": attention_linear_leaf_sum,
            "decode_attention_full_leaf_parts_sum": attention_full_leaf_sum,
            "decode_attention_linear_source_method_nested_sum": (
                attention_linear_source_method_sum
            ),
            "decode_source_attention_minus_leaf_parts": (
                attention_source_minus_leaf_parts
            ),
            "decode_source_mlp_call": decoder_source_mlp_sum,
            "decode_layer_minus_source_parts": decoder_layer_minus_source_parts,
            **{
                f"decode_{name}": value
                for name, value in decoder_source_sums.items()
            },
            **{
                f"decode_{name}": value
                for name, value in attention_leaf_sums.items()
            },
            **{
                f"decode_{name}": value
                for name, value in attention_linear_source_method_sums.items()
            },
            **{
                f"decode_{name}": value
                for name, value in attention_linear_handoff_sums.items()
            },
            "decode_attention_linear_handoff_core_prep_layout": (
                attention_linear_handoff_core_prep_layout_sum
            ),
            "decode_moe_layer_apply": moe_sum,
            "wna16_w1_gpu_event": w1_gpu_sum,
            "wna16_w2_gpu_event": w2_gpu_sum,
            "wna16_other_gpu_event": other_gpu_sum,
            "wna16_total_gpu_event": wna16_gpu_sum,
            "moe_apply_minus_wna16_gpu_event": moe_non_wna16_gpu,
            "decode_decoder_layer_minus_moe_apply": decoder_non_moe,
            "decode_decoder_outside_attention_mlp": decoder_outside_attention_mlp,
            "decode_mlp_minus_moe_apply": mlp_minus_moe,
            "moe_router_logits": router_logits_sum,
            "moe_experts_total": experts_total_sum,
            "moe_select_experts": select_experts_sum,
            "moe_select_validate_eplb": select_validate_sum,
            "moe_select_indices_type": select_indices_sum,
            "moe_select_compute_routing": select_compute_sum,
            "moe_select_capture_logical_ids": select_capture_sum,
            "moe_select_eplb_mapping": select_eplb_sum,
            "moe_select_dtype_convert": select_convert_sum,
            "moe_select_record_topk": select_record_sum,
            "moe_select_experts_minus_record_topk": select_minus_record_topk,
            "moe_experts_shared_stream_sync": experts_shared_stream_sync_sum,
            "moe_experts_maybe_dispatch": experts_maybe_dispatch_sum,
            "moe_experts_maybe_combine": experts_maybe_combine_sum,
            "moe_experts_shared_no_overlap": experts_shared_no_overlap_sum,
            "moe_experts_shared_determine_order": experts_shared_determine_order_sum,
            "moe_experts_shared_apply_skipped": experts_shared_apply_skipped_sum,
            "moe_experts_shared_w1": experts_shared_w1_sum,
            "moe_experts_shared_activation": experts_shared_activation_sum,
            "moe_experts_shared_w2": experts_shared_w2_sum,
            "moe_experts_shared_output_combine": (
                experts_shared_output_combine_sum
            ),
            "moe_experts_shared_output_gate": experts_shared_output_gate_sum,
            "moe_experts_shared_output_sigmoid_mul": (
                experts_shared_output_sigmoid_mul_sum
            ),
            "moe_experts_shared_output_gate_fused": (
                experts_shared_output_gate_fused_sum
            ),
            "moe_experts_shared_output_detailed_parts_sum": (
                shared_output_detailed_parts_sum
            ),
            "moe_experts_shared_child_other": experts_shared_child_other_sum,
            "moe_experts_shared_direct_layer": experts_shared_direct_layer_sum,
            "moe_experts_shared_body_core": experts_shared_body_core_sum,
            "moe_experts_shared_body_gate_proj": (
                experts_shared_body_gate_proj_sum
            ),
            "moe_experts_shared_body_gate_apply": (
                experts_shared_body_gate_apply_sum
            ),
            "moe_experts_shared_body_gate_fused": (
                experts_shared_body_gate_fused_sum
            ),
            "moe_experts_shared_aux_stream_layer_wait": (
                experts_shared_aux_stream_layer_wait_sum
            ),
            "moe_experts_shared_body_region_parts_sum": (
                shared_body_region_parts_sum
            ),
            "moe_experts_shared_direct_minus_body_region_parts": (
                shared_direct_minus_body_region_parts
            ),
            "moe_experts_shared_direct_source_parts_sum": (
                shared_direct_source_parts_sum
            ),
            "moe_experts_shared_direct_minus_source_parts": (
                shared_direct_minus_source_parts
            ),
            "moe_experts_shared_no_overlap_inner_parts_sum": (
                shared_no_overlap_inner_parts_sum
            ),
            "moe_experts_shared_no_overlap_minus_inner_parts": (
                shared_no_overlap_minus_inner_parts
            ),
            "moe_experts_pre_quant_apply_glue": experts_pre_quant_glue_sum,
            "moe_experts_shared_overlap": experts_shared_overlap_sum,
            "moe_experts_shared_output_fetch": experts_shared_output_fetch_sum,
            "moe_experts_nonapply_measured_parts_sum": (
                experts_nonapply_measured_parts_sum
            ),
            "moe_prepare_expert_assignment": prepare_assignment_sum,
            "moe_quant_method_apply": quant_apply_sum,
            "moe_quant_method_apply_monolithic": quant_apply_monolithic_sum,
            "moe_quant_method_apply_effective": quant_apply_effective_sum,
            "moe_apply_problem_size": apply_problem_size_sum,
            "moe_apply_config_lookup": apply_config_lookup_sum,
            "moe_apply_source_fused_experts_outer": (
                apply_source_fused_experts_outer_sum
            ),
            "moe_apply_source_outer_quant_config": (
                apply_source_outer_quant_config_sum
            ),
            "moe_apply_source_outer_inplace_assert": (
                apply_source_outer_inplace_assert_sum
            ),
            "moe_apply_source_outer_dispatch_select": (
                apply_source_outer_dispatch_select_sum
            ),
            "moe_apply_source_outer_impl_call": apply_source_outer_impl_call_sum,
            "moe_apply_source_impl_entry_overhead": (
                apply_source_impl_entry_overhead_sum
            ),
            "moe_apply_source_emit_overhead": apply_source_emit_overhead_sum,
            "moe_apply_source_impl_total": apply_source_impl_total_sum,
            "moe_apply_source_pre_dispatch": apply_source_pre_dispatch_sum,
            "moe_apply_source_workspace_alloc": apply_source_workspace_alloc_sum,
            "moe_apply_source_quantize_hidden": apply_source_quantize_hidden_sum,
            "moe_apply_source_prepare_assignment": (
                apply_source_prepare_assignment_sum
            ),
            "moe_apply_source_w1_enqueue": apply_source_w1_enqueue_sum,
            "moe_apply_source_w1_post": apply_source_w1_post_sum,
            "moe_apply_source_activation": apply_source_activation_sum,
            "moe_apply_source_quantize_intermediate": (
                apply_source_quantize_intermediate_sum
            ),
            "moe_apply_source_w2_pre": apply_source_w2_pre_sum,
            "moe_apply_source_w2_enqueue": apply_source_w2_enqueue_sum,
            "moe_apply_source_w2_post": apply_source_w2_post_sum,
            "moe_apply_source_combine_scatter": apply_source_combine_scatter_sum,
            "moe_apply_source_post_dispatch": apply_source_post_dispatch_sum,
            "moe_apply_resize_cache_w1_output": apply_resize_cache_w1_sum,
            "moe_apply_resize_cache_activation": apply_resize_cache_activation_sum,
            "moe_apply_resize_cache_w2_output": apply_resize_cache_w2_sum,
            "moe_apply_resize_cache_other": apply_resize_cache_other_sum,
            "moe_apply_quantize_hidden": apply_quantize_hidden_sum,
            "moe_apply_dispatch_w1_host": apply_dispatch_w1_host_sum,
            "moe_apply_dispatch_w1_host_pre_invoke": (
                apply_dispatch_w1_pre_invoke_sum
            ),
            "moe_apply_dispatch_w1_host_cuda_decision": (
                apply_dispatch_w1_cuda_decision_sum
            ),
            "moe_apply_dispatch_w1_host_invoke_call": (
                apply_dispatch_w1_invoke_call_sum
            ),
            "moe_apply_dispatch_w1_host_source_parts_sum": (
                w1_dispatch_source_parts_sum
            ),
            "moe_apply_dispatch_w1_host_minus_source_parts": (
                w1_dispatch_host_minus_source_parts
            ),
            "moe_apply_dispatch_w1_host_minus_gpu_event": w1_host_minus_gpu,
            "moe_apply_wna16_w1_invoke_setup_host": wna16_w1_setup_host_sum,
            "moe_apply_wna16_w1_enqueue_host": wna16_w1_enqueue_host_sum,
            "moe_apply_wna16_w1_event_sync_wait": wna16_w1_sync_wait_sum,
            "moe_apply_dispatch_w1_host_minus_launch_parts": (
                w1_dispatch_host_minus_launch_parts
            ),
            "moe_apply_activation": apply_activation_sum,
            "moe_apply_quantize_intermediate": apply_quantize_intermediate_sum,
            "moe_apply_dispatch_w2_host": apply_dispatch_w2_host_sum,
            "moe_apply_dispatch_w2_host_pre_invoke": (
                apply_dispatch_w2_pre_invoke_sum
            ),
            "moe_apply_dispatch_w2_host_cuda_decision": (
                apply_dispatch_w2_cuda_decision_sum
            ),
            "moe_apply_dispatch_w2_host_invoke_call": (
                apply_dispatch_w2_invoke_call_sum
            ),
            "moe_apply_dispatch_w2_host_source_parts_sum": (
                w2_dispatch_source_parts_sum
            ),
            "moe_apply_dispatch_w2_host_minus_source_parts": (
                w2_dispatch_host_minus_source_parts
            ),
            "moe_apply_dispatch_w2_host_minus_gpu_event": w2_host_minus_gpu,
            "moe_apply_wna16_w2_invoke_setup_host": wna16_w2_setup_host_sum,
            "moe_apply_wna16_w2_enqueue_host": wna16_w2_enqueue_host_sum,
            "moe_apply_wna16_w2_event_sync_wait": wna16_w2_sync_wait_sum,
            "moe_apply_dispatch_w2_host_minus_launch_parts": (
                w2_dispatch_host_minus_launch_parts
            ),
            "moe_apply_dispatch_w1w2_host_minus_gpu_event": dispatch_host_minus_wna16_gpu,
            "moe_apply_dispatch_other_host": apply_dispatch_other_host_sum,
            "moe_apply_wna16_other_invoke_setup_host": wna16_other_setup_host_sum,
            "moe_apply_wna16_other_enqueue_host": wna16_other_enqueue_host_sum,
            "moe_apply_wna16_other_event_sync_wait": wna16_other_sync_wait_sum,
            "moe_apply_moe_sum": apply_moe_sum_sum,
            "moe_quant_apply_measured_parts_sum": apply_measured_parts_sum,
            "moe_quant_apply_minus_measured_parts": quant_apply_minus_measured_parts,
            "moe_quant_apply_source_parts_sum": apply_source_parts_sum,
            "moe_quant_apply_minus_source_parts": quant_apply_minus_source_parts,
            "moe_quant_apply_minus_fused_experts_outer": (
                quant_apply_minus_fused_experts_outer
            ),
            "moe_fused_experts_outer_minus_inner_source_parts": (
                fused_experts_outer_minus_inner_source_parts
            ),
            "moe_fused_experts_outer_minus_impl_total": (
                fused_experts_outer_minus_impl_total
            ),
            "moe_fused_experts_impl_total_minus_inner_source_parts": (
                fused_experts_impl_total_minus_inner_source_parts
            ),
            "moe_fused_experts_impl_total_minus_inner_source_parts_emit_adjusted": (
                fused_experts_impl_total_minus_inner_source_parts_emit_adjusted
            ),
            "moe_fused_experts_outer_parts_sum": apply_outer_parts_sum,
            "moe_fused_experts_outer_minus_outer_parts": (
                fused_experts_outer_minus_outer_parts
            ),
            "moe_fused_experts_outer_impl_call_minus_impl_total": (
                fused_experts_outer_impl_call_minus_impl_total
            ),
            "moe_fused_experts_outer_impl_call_minus_impl_total_named_overhead": (
                fused_experts_outer_impl_call_minus_impl_total_named_overhead
            ),
            "moe_fused_experts_outer_impl_call_minus_impl_total_unclassified": (
                fused_experts_outer_impl_call_minus_impl_total_unclassified
            ),
            "moe_apply_source_w1_enqueue_minus_launch_parts": (
                source_w1_enqueue_minus_launch_parts
            ),
            "moe_apply_source_w2_enqueue_minus_launch_parts": (
                source_w2_enqueue_minus_launch_parts
            ),
            "moe_apply_source_w1_enqueue_minus_dispatch_host": (
                source_w1_enqueue_minus_dispatch_host
            ),
            "moe_apply_source_w2_enqueue_minus_dispatch_host": (
                source_w2_enqueue_minus_dispatch_host
            ),
            "moe_experts_total_minus_quant_apply": experts_minus_quant_apply,
            "moe_experts_total_measured_parts_sum": experts_total_measured_parts_sum,
            "moe_experts_total_minus_measured_parts": experts_total_minus_measured_parts,
            "moe_quant_apply_minus_prepare_wna16": quant_apply_minus_prepare_wna16,
            "moe_apply_minus_prepare_wna16": moe_apply_minus_prepare_wna16,
            "generate_minus_decode_decoder_layer": residual_after_decoder,
            "generate_minus_decode_moe_apply": residual_after_moe,
            "engine_generate_call_minus_execute_model": (
                engine_generate_minus_execute_model
            ),
            "engine_execute_model_minus_model_forward": (
                engine_execute_model_minus_model_forward
            ),
            **{
                f"engine_substage_{name}": value
                for name, value in engine_substage_sums.items()
            },
        },
        "anomalies": anomalies,
    }


def write_markdown(result: dict[str, Any], path: Path) -> None:
    sums = result["sums_us"]
    shadow = result["shadow"]
    total = sums.get("generate")
    output_tokens = result["performance"].get("requested_output_token_count")
    moe_count = int(shadow["decode_layer_apply_us"].get("count") or 0)
    engine_substage_counts = {
        name: int(stats.get("count") or 0)
        for name, stats in shadow.get("engine_substage_us", {}).items()
    }
    decoder_decode_count = int(shadow["decoder_layer_us"]["decode"].get("count") or 0)
    attention_count = int(
        shadow["decoder_component_us"]["attention"]["decode"].get("count") or 0
    )
    mlp_count = int(
        shadow["decoder_component_us"]["mlp"]["decode"].get("count") or 0
    )

    def decoder_component_decode_count(component: str) -> int:
        return int(
            shadow["decoder_component_us"]
            .get(component, {})
            .get("decode", {})
            .get("count")
            or 0
        )
    moe_substage_counts = {
        key: int(shadow["moe_substage_us"][key]["decode"].get("count") or 0)
        for key in (
            "router_logits",
            "experts_total",
            "select_experts",
            "select_compute_routing",
            "select_record_topk",
            "experts_shared_stream_sync",
            "experts_maybe_dispatch",
            "experts_maybe_combine",
            "experts_shared_no_overlap",
            "experts_shared_determine_order",
            "experts_shared_apply_skipped",
            "experts_shared_w1",
            "experts_shared_activation",
            "experts_shared_w2",
            "experts_shared_output_combine",
            "experts_shared_output_gate",
            "experts_shared_output_sigmoid_mul",
            "experts_shared_output_gate_fused",
            "experts_shared_child_other",
            "experts_shared_direct_layer",
            "experts_shared_body_core",
            "experts_shared_body_gate_proj",
            "experts_shared_body_gate_apply",
            "experts_shared_body_gate_fused",
            "experts_shared_aux_stream_layer_wait",
            "experts_pre_quant_apply_glue",
            "experts_shared_overlap",
            "experts_shared_output_fetch",
            "prepare_expert_assignment",
            "quant_method_apply",
            "quant_method_apply_monolithic",
            "apply_problem_size",
            "apply_config_lookup",
            "apply_source_fused_experts_outer",
            "apply_source_outer_quant_config",
            "apply_source_outer_inplace_assert",
            "apply_source_outer_dispatch_select",
            "apply_source_outer_impl_call",
            "apply_source_impl_total",
            "apply_source_pre_dispatch",
            "apply_source_workspace_alloc",
            "apply_source_quantize_hidden",
            "apply_source_prepare_assignment",
            "apply_source_w1_enqueue",
            "apply_source_w1_post",
            "apply_source_activation",
            "apply_source_quantize_intermediate",
            "apply_source_w2_pre",
            "apply_source_w2_enqueue",
            "apply_source_w2_post",
            "apply_source_combine_scatter",
            "apply_source_post_dispatch",
            "apply_resize_cache_w1_output",
            "apply_resize_cache_activation",
            "apply_resize_cache_w2_output",
            "apply_resize_cache_other",
            "apply_dispatch_w1_host",
            "apply_wna16_w1_invoke_setup_host",
            "apply_wna16_w1_enqueue_host",
            "apply_wna16_w1_event_sync_wait",
            "apply_activation",
            "apply_dispatch_w2_host",
            "apply_wna16_w2_invoke_setup_host",
            "apply_wna16_w2_enqueue_host",
            "apply_wna16_w2_event_sync_wait",
            "apply_dispatch_other_host",
            "apply_wna16_other_invoke_setup_host",
            "apply_wna16_other_enqueue_host",
            "apply_wna16_other_event_sync_wait",
            "apply_moe_sum",
        )
    }
    wna16_counts_by_bucket = {
        bucket: int(shadow["wna16_gpu_us"][bucket].get("count") or 0)
        for bucket in ("w1", "w2", "other")
    }
    rows = [
        ("generate total", sums.get("generate"), 100.0 if total else None, None),
        (
            "engine llm.generate call",
            sums.get("engine_substage_engine_llm_generate_call"),
            _pct_optional(sums.get("engine_substage_engine_llm_generate_call"), total),
            engine_substage_counts.get("engine_llm_generate_call"),
        ),
        (
            "engine execute_model",
            sums.get("engine_substage_engine_execute_model"),
            _pct_optional(sums.get("engine_substage_engine_execute_model"), total),
            engine_substage_counts.get("engine_execute_model"),
        ),
        (
            "engine model_forward",
            sums.get("engine_substage_engine_model_forward"),
            _pct_optional(sums.get("engine_substage_engine_model_forward"), total),
            engine_substage_counts.get("engine_model_forward"),
        ),
        (
            "engine execute_model minus model_forward",
            sums.get("engine_execute_model_minus_model_forward"),
            _pct_optional(sums.get("engine_execute_model_minus_model_forward"), total),
            None,
        ),
        (
            "engine llm.generate minus execute_model",
            sums.get("engine_generate_call_minus_execute_model"),
            _pct_optional(sums.get("engine_generate_call_minus_execute_model"), total),
            None,
        ),
        (
            "engine update_states",
            sums.get("engine_substage_engine_update_states"),
            _pct_optional(sums.get("engine_substage_engine_update_states"), total),
            engine_substage_counts.get("engine_update_states"),
        ),
        (
            "engine determine batch",
            sums.get("engine_substage_engine_determine_batch"),
            _pct_optional(sums.get("engine_substage_engine_determine_batch"), total),
            engine_substage_counts.get("engine_determine_batch"),
        ),
        (
            "engine slot mappings",
            sums.get("engine_substage_engine_slot_mappings"),
            _pct_optional(sums.get("engine_substage_engine_slot_mappings"), total),
            engine_substage_counts.get("engine_slot_mappings"),
        ),
        (
            "engine attention metadata",
            sums.get("engine_substage_engine_attention_metadata"),
            _pct_optional(
                sums.get("engine_substage_engine_attention_metadata"),
                total,
            ),
            engine_substage_counts.get("engine_attention_metadata"),
        ),
        (
            "engine logits processor",
            sums.get("engine_substage_engine_logits_processor_forward"),
            _pct_optional(
                sums.get("engine_substage_engine_logits_processor_forward"),
                total,
            ),
            engine_substage_counts.get("engine_logits_processor_forward"),
        ),
        (
            "engine sample_tokens",
            sums.get("engine_substage_engine_sample_tokens"),
            _pct_optional(sums.get("engine_substage_engine_sample_tokens"), total),
            engine_substage_counts.get("engine_sample_tokens"),
        ),
        (
            "engine sampler forward",
            sums.get("engine_substage_engine_sampler_forward"),
            _pct_optional(sums.get("engine_substage_engine_sampler_forward"), total),
            engine_substage_counts.get("engine_sampler_forward"),
        ),
        (
            "engine sampler sample",
            sums.get("engine_substage_engine_sampler_sample"),
            _pct_optional(sums.get("engine_substage_engine_sampler_sample"), total),
            engine_substage_counts.get("engine_sampler_sample"),
        ),
        (
            "engine bookkeeping sync",
            sums.get("engine_substage_engine_bookkeeping_sync"),
            _pct_optional(
                sums.get("engine_substage_engine_bookkeeping_sync"),
                total,
            ),
            engine_substage_counts.get("engine_bookkeeping_sync"),
        ),
        (
            "engine eplb step",
            sums.get("engine_substage_engine_eplb_step"),
            _pct_optional(sums.get("engine_substage_engine_eplb_step"), total),
            engine_substage_counts.get("engine_eplb_step"),
        ),
        (
            "decode decoder layer total",
            sums.get("decode_decoder_layer"),
            _pct_optional(sums.get("decode_decoder_layer"), total),
            decoder_decode_count,
        ),
        (
            "decode attention",
            sums.get("decode_attention"),
            _pct_optional(sums.get("decode_attention"), total),
            attention_count,
        ),
        (
            "attention handoff linear proj total",
            sums.get("decode_attention_linear_handoff_linear_proj_total"),
            _pct_optional(
                sums.get("decode_attention_linear_handoff_linear_proj_total"),
                total,
            ),
            decoder_component_decode_count(
                "attention_linear_handoff_linear_proj_total"
            ),
        ),
        (
            "attention handoff norm",
            sums.get("decode_attention_linear_handoff_norm"),
            _pct_optional(sums.get("decode_attention_linear_handoff_norm"), total),
            decoder_component_decode_count("attention_linear_handoff_norm"),
        ),
        (
            "attention handoff core prep-layout",
            sums.get("decode_attention_linear_handoff_core_prep_layout"),
            _pct_optional(
                sums.get("decode_attention_linear_handoff_core_prep_layout"),
                total,
            ),
            decoder_component_decode_count(
                "attention_linear_handoff_core_decode_non_spec"
            ),
        ),
        (
            "attention handoff conv update",
            sums.get("decode_attention_linear_handoff_conv_update"),
            _pct_optional(
                sums.get("decode_attention_linear_handoff_conv_update"),
                total,
            ),
            decoder_component_decode_count("attention_linear_handoff_conv_update"),
        ),
        (
            "attention handoff recurrent",
            sums.get("decode_attention_linear_handoff_recurrent"),
            _pct_optional(
                sums.get("decode_attention_linear_handoff_recurrent"),
                total,
            ),
            decoder_component_decode_count("attention_linear_handoff_recurrent"),
        ),
        (
            "attention handoff core post-layout",
            sums.get("decode_attention_linear_handoff_core_post_layout"),
            _pct_optional(
                sums.get("decode_attention_linear_handoff_core_post_layout"),
                total,
            ),
            decoder_component_decode_count(
                "attention_linear_handoff_core_post_layout"
            )
            or decoder_component_decode_count("attention_linear_handoff_core_total"),
        ),
        (
            "attention handoff out proj",
            sums.get("decode_attention_linear_handoff_out_proj"),
            _pct_optional(sums.get("decode_attention_linear_handoff_out_proj"), total),
            decoder_component_decode_count("attention_linear_handoff_out_proj"),
        ),
        (
            "decode MLP/MoE block",
            sums.get("decode_mlp"),
            _pct_optional(sums.get("decode_mlp"), total),
            mlp_count,
        ),
        (
            "decode MoE layer apply",
            sums.get("decode_moe_layer_apply"),
            _pct(sums.get("decode_moe_layer_apply") or 0.0, total),
            moe_count,
        ),
        (
            "MoE experts total",
            sums.get("moe_experts_total"),
            _pct_optional(sums.get("moe_experts_total"), total),
            moe_substage_counts["experts_total"],
        ),
        (
            "MoE router logits",
            sums.get("moe_router_logits"),
            _pct_optional(sums.get("moe_router_logits"), total),
            moe_substage_counts["router_logits"],
        ),
        (
            "MoE select_experts",
            sums.get("moe_select_experts"),
            _pct_optional(sums.get("moe_select_experts"), total),
            moe_substage_counts["select_experts"],
        ),
        (
            "MoE select compute_routing",
            sums.get("moe_select_compute_routing"),
            _pct_optional(sums.get("moe_select_compute_routing"), total),
            moe_substage_counts["select_compute_routing"],
        ),
        (
            "MoE select record_topk",
            sums.get("moe_select_record_topk"),
            _pct_optional(sums.get("moe_select_record_topk"), total),
            moe_substage_counts["select_record_topk"],
        ),
        (
            "MoE select_experts minus record_topk",
            sums.get("moe_select_experts_minus_record_topk"),
            _pct_optional(sums.get("moe_select_experts_minus_record_topk"), total),
            moe_substage_counts["select_experts"]
            if moe_substage_counts["select_experts"]
            else None,
        ),
        (
            "MoE experts shared stream sync",
            sums.get("moe_experts_shared_stream_sync"),
            _pct_optional(sums.get("moe_experts_shared_stream_sync"), total),
            moe_substage_counts["experts_shared_stream_sync"],
        ),
        (
            "MoE experts maybe dispatch",
            sums.get("moe_experts_maybe_dispatch"),
            _pct_optional(sums.get("moe_experts_maybe_dispatch"), total),
            moe_substage_counts["experts_maybe_dispatch"],
        ),
        (
            "MoE experts maybe combine",
            sums.get("moe_experts_maybe_combine"),
            _pct_optional(sums.get("moe_experts_maybe_combine"), total),
            moe_substage_counts["experts_maybe_combine"],
        ),
        (
            "MoE experts shared no-overlap",
            sums.get("moe_experts_shared_no_overlap"),
            _pct_optional(sums.get("moe_experts_shared_no_overlap"), total),
            moe_substage_counts["experts_shared_no_overlap"],
        ),
        (
            "MoE experts shared determine order",
            sums.get("moe_experts_shared_determine_order"),
            _pct_optional(sums.get("moe_experts_shared_determine_order"), total),
            moe_substage_counts["experts_shared_determine_order"],
        ),
        (
            "MoE experts shared apply skipped",
            sums.get("moe_experts_shared_apply_skipped"),
            _pct_optional(sums.get("moe_experts_shared_apply_skipped"), total),
            moe_substage_counts["experts_shared_apply_skipped"],
        ),
        (
            "MoE experts shared W1/gate-up",
            sums.get("moe_experts_shared_w1"),
            _pct_optional(sums.get("moe_experts_shared_w1"), total),
            moe_substage_counts["experts_shared_w1"],
        ),
        (
            "MoE experts shared activation",
            sums.get("moe_experts_shared_activation"),
            _pct_optional(sums.get("moe_experts_shared_activation"), total),
            moe_substage_counts["experts_shared_activation"],
        ),
        (
            "MoE experts shared W2/down",
            sums.get("moe_experts_shared_w2"),
            _pct_optional(sums.get("moe_experts_shared_w2"), total),
            moe_substage_counts["experts_shared_w2"],
        ),
        (
            "MoE experts shared output/combine",
            sums.get("moe_experts_shared_output_combine"),
            _pct_optional(sums.get("moe_experts_shared_output_combine"), total),
            moe_substage_counts["experts_shared_output_combine"],
        ),
        (
            "MoE experts shared output gate",
            sums.get("moe_experts_shared_output_gate"),
            _pct_optional(sums.get("moe_experts_shared_output_gate"), total),
            moe_substage_counts["experts_shared_output_gate"],
        ),
        (
            "MoE experts shared output sigmoid/mul",
            sums.get("moe_experts_shared_output_sigmoid_mul"),
            _pct_optional(
                sums.get("moe_experts_shared_output_sigmoid_mul"),
                total,
            ),
            moe_substage_counts["experts_shared_output_sigmoid_mul"],
        ),
        (
            "MoE experts shared output fused gate",
            sums.get("moe_experts_shared_output_gate_fused"),
            _pct_optional(
                sums.get("moe_experts_shared_output_gate_fused"),
                total,
            ),
            moe_substage_counts["experts_shared_output_gate_fused"],
        ),
        (
            "MoE experts shared child other",
            sums.get("moe_experts_shared_child_other"),
            _pct_optional(sums.get("moe_experts_shared_child_other"), total),
            moe_substage_counts["experts_shared_child_other"],
        ),
        (
            "MoE experts shared direct layer",
            sums.get("moe_experts_shared_direct_layer"),
            _pct_optional(sums.get("moe_experts_shared_direct_layer"), total),
            moe_substage_counts["experts_shared_direct_layer"],
        ),
        (
            "MoE experts shared body core",
            sums.get("moe_experts_shared_body_core"),
            _pct_optional(sums.get("moe_experts_shared_body_core"), total),
            moe_substage_counts["experts_shared_body_core"],
        ),
        (
            "MoE experts shared body gate proj",
            sums.get("moe_experts_shared_body_gate_proj"),
            _pct_optional(sums.get("moe_experts_shared_body_gate_proj"), total),
            moe_substage_counts["experts_shared_body_gate_proj"],
        ),
        (
            "MoE experts shared body gate apply",
            sums.get("moe_experts_shared_body_gate_apply"),
            _pct_optional(sums.get("moe_experts_shared_body_gate_apply"), total),
            moe_substage_counts["experts_shared_body_gate_apply"],
        ),
        (
            "MoE experts shared body gate fused",
            sums.get("moe_experts_shared_body_gate_fused"),
            _pct_optional(sums.get("moe_experts_shared_body_gate_fused"), total),
            moe_substage_counts["experts_shared_body_gate_fused"],
        ),
        (
            "MoE experts shared aux-stream layer+wait",
            sums.get("moe_experts_shared_aux_stream_layer_wait"),
            _pct_optional(
                sums.get("moe_experts_shared_aux_stream_layer_wait"),
                total,
            ),
            moe_substage_counts["experts_shared_aux_stream_layer_wait"],
        ),
        (
            "MoE experts shared no-overlap inner parts sum",
            sums.get("moe_experts_shared_no_overlap_inner_parts_sum"),
            _pct_optional(
                sums.get("moe_experts_shared_no_overlap_inner_parts_sum"),
                total,
            ),
            moe_substage_counts["experts_shared_no_overlap"],
        ),
        (
            "MoE experts shared body region parts sum",
            sums.get("moe_experts_shared_body_region_parts_sum"),
            _pct_optional(
                sums.get("moe_experts_shared_body_region_parts_sum"),
                total,
            ),
            moe_substage_counts["experts_shared_direct_layer"],
        ),
        (
            "MoE experts shared direct minus body region parts",
            sums.get("moe_experts_shared_direct_minus_body_region_parts"),
            _pct_optional(
                sums.get("moe_experts_shared_direct_minus_body_region_parts"),
                total,
            ),
            moe_substage_counts["experts_shared_direct_layer"],
        ),
        (
            "MoE experts shared direct source parts sum",
            sums.get("moe_experts_shared_direct_source_parts_sum"),
            _pct_optional(
                sums.get("moe_experts_shared_direct_source_parts_sum"),
                total,
            ),
            moe_substage_counts["experts_shared_direct_layer"],
        ),
        (
            "MoE experts shared direct minus source parts",
            sums.get("moe_experts_shared_direct_minus_source_parts"),
            _pct_optional(
                sums.get("moe_experts_shared_direct_minus_source_parts"),
                total,
            ),
            moe_substage_counts["experts_shared_direct_layer"],
        ),
        (
            "MoE experts shared no-overlap minus inner parts",
            sums.get("moe_experts_shared_no_overlap_minus_inner_parts"),
            _pct_optional(
                sums.get("moe_experts_shared_no_overlap_minus_inner_parts"),
                total,
            ),
            moe_substage_counts["experts_shared_no_overlap"],
        ),
        (
            "MoE experts pre-quant apply glue",
            sums.get("moe_experts_pre_quant_apply_glue"),
            _pct_optional(sums.get("moe_experts_pre_quant_apply_glue"), total),
            moe_substage_counts["experts_pre_quant_apply_glue"],
        ),
        (
            "MoE experts shared overlap",
            sums.get("moe_experts_shared_overlap"),
            _pct_optional(sums.get("moe_experts_shared_overlap"), total),
            moe_substage_counts["experts_shared_overlap"],
        ),
        (
            "MoE experts shared output fetch",
            sums.get("moe_experts_shared_output_fetch"),
            _pct_optional(sums.get("moe_experts_shared_output_fetch"), total),
            moe_substage_counts["experts_shared_output_fetch"],
        ),
        (
            "MoE experts non-apply measured parts sum",
            sums.get("moe_experts_nonapply_measured_parts_sum"),
            _pct_optional(
                sums.get("moe_experts_nonapply_measured_parts_sum"),
                total,
            ),
            moe_substage_counts["experts_total"],
        ),
        (
            "MoE prepare_expert_assignment",
            sums.get("moe_prepare_expert_assignment"),
            _pct_optional(sums.get("moe_prepare_expert_assignment"), total),
            moe_substage_counts["prepare_expert_assignment"],
        ),
        (
            "MoE quant_method.apply",
            sums.get("moe_quant_method_apply"),
            _pct_optional(sums.get("moe_quant_method_apply"), total),
            moe_substage_counts["quant_method_apply"],
        ),
        (
            "MoE quant_method.apply monolithic",
            sums.get("moe_quant_method_apply_monolithic"),
            _pct_optional(sums.get("moe_quant_method_apply_monolithic"), total),
            moe_substage_counts["quant_method_apply_monolithic"],
        ),
        (
            "MoE quant_method.apply effective",
            sums.get("moe_quant_method_apply_effective"),
            _pct_optional(sums.get("moe_quant_method_apply_effective"), total),
            (
                moe_substage_counts["quant_method_apply"]
                or moe_substage_counts["quant_method_apply_monolithic"]
            ),
        ),
        (
            "MoE apply problem size",
            sums.get("moe_apply_problem_size"),
            _pct_optional(sums.get("moe_apply_problem_size"), total),
            moe_substage_counts["apply_problem_size"],
        ),
        (
            "MoE apply config lookup",
            sums.get("moe_apply_config_lookup"),
            _pct_optional(sums.get("moe_apply_config_lookup"), total),
            moe_substage_counts["apply_config_lookup"],
        ),
        (
            "MoE apply source fused_experts outer",
            sums.get("moe_apply_source_fused_experts_outer"),
            _pct_optional(sums.get("moe_apply_source_fused_experts_outer"), total),
            moe_substage_counts["apply_source_fused_experts_outer"],
        ),
        (
            "MoE apply source outer quant-config",
            sums.get("moe_apply_source_outer_quant_config"),
            _pct_optional(sums.get("moe_apply_source_outer_quant_config"), total),
            moe_substage_counts["apply_source_outer_quant_config"],
        ),
        (
            "MoE apply source outer inplace assert",
            sums.get("moe_apply_source_outer_inplace_assert"),
            _pct_optional(sums.get("moe_apply_source_outer_inplace_assert"), total),
            moe_substage_counts["apply_source_outer_inplace_assert"],
        ),
        (
            "MoE apply source outer dispatch select",
            sums.get("moe_apply_source_outer_dispatch_select"),
            _pct_optional(sums.get("moe_apply_source_outer_dispatch_select"), total),
            moe_substage_counts["apply_source_outer_dispatch_select"],
        ),
        (
            "MoE apply source outer impl call",
            sums.get("moe_apply_source_outer_impl_call"),
            _pct_optional(sums.get("moe_apply_source_outer_impl_call"), total),
            moe_substage_counts["apply_source_outer_impl_call"],
        ),
        (
            "MoE apply source fused_experts_impl total",
            sums.get("moe_apply_source_impl_total"),
            _pct_optional(sums.get("moe_apply_source_impl_total"), total),
            moe_substage_counts["apply_source_impl_total"],
        ),
        (
            "MoE apply source pre-dispatch",
            sums.get("moe_apply_source_pre_dispatch"),
            _pct_optional(sums.get("moe_apply_source_pre_dispatch"), total),
            moe_substage_counts["apply_source_pre_dispatch"],
        ),
        (
            "MoE apply source workspace alloc",
            sums.get("moe_apply_source_workspace_alloc"),
            _pct_optional(sums.get("moe_apply_source_workspace_alloc"), total),
            moe_substage_counts["apply_source_workspace_alloc"],
        ),
        (
            "MoE apply source quantize hidden",
            sums.get("moe_apply_source_quantize_hidden"),
            _pct_optional(sums.get("moe_apply_source_quantize_hidden"), total),
            moe_substage_counts["apply_source_quantize_hidden"],
        ),
        (
            "MoE apply source prepare assignment",
            sums.get("moe_apply_source_prepare_assignment"),
            _pct_optional(sums.get("moe_apply_source_prepare_assignment"), total),
            moe_substage_counts["apply_source_prepare_assignment"],
        ),
        (
            "MoE apply source W1 enqueue",
            sums.get("moe_apply_source_w1_enqueue"),
            _pct_optional(sums.get("moe_apply_source_w1_enqueue"), total),
            moe_substage_counts["apply_source_w1_enqueue"],
        ),
        (
            "MoE apply source W1 post",
            sums.get("moe_apply_source_w1_post"),
            _pct_optional(sums.get("moe_apply_source_w1_post"), total),
            moe_substage_counts["apply_source_w1_post"],
        ),
        (
            "MoE apply source activation",
            sums.get("moe_apply_source_activation"),
            _pct_optional(sums.get("moe_apply_source_activation"), total),
            moe_substage_counts["apply_source_activation"],
        ),
        (
            "MoE apply source quantize intermediate",
            sums.get("moe_apply_source_quantize_intermediate"),
            _pct_optional(sums.get("moe_apply_source_quantize_intermediate"), total),
            moe_substage_counts["apply_source_quantize_intermediate"],
        ),
        (
            "MoE apply source W2 pre",
            sums.get("moe_apply_source_w2_pre"),
            _pct_optional(sums.get("moe_apply_source_w2_pre"), total),
            moe_substage_counts["apply_source_w2_pre"],
        ),
        (
            "MoE apply source W2 enqueue",
            sums.get("moe_apply_source_w2_enqueue"),
            _pct_optional(sums.get("moe_apply_source_w2_enqueue"), total),
            moe_substage_counts["apply_source_w2_enqueue"],
        ),
        (
            "MoE apply source W2 post",
            sums.get("moe_apply_source_w2_post"),
            _pct_optional(sums.get("moe_apply_source_w2_post"), total),
            moe_substage_counts["apply_source_w2_post"],
        ),
        (
            "MoE apply source combine/scatter",
            sums.get("moe_apply_source_combine_scatter"),
            _pct_optional(sums.get("moe_apply_source_combine_scatter"), total),
            moe_substage_counts["apply_source_combine_scatter"],
        ),
        (
            "MoE apply source post-dispatch",
            sums.get("moe_apply_source_post_dispatch"),
            _pct_optional(sums.get("moe_apply_source_post_dispatch"), total),
            moe_substage_counts["apply_source_post_dispatch"],
        ),
        (
            "MoE apply resize cache W1 output",
            sums.get("moe_apply_resize_cache_w1_output"),
            _pct_optional(sums.get("moe_apply_resize_cache_w1_output"), total),
            moe_substage_counts["apply_resize_cache_w1_output"],
        ),
        (
            "MoE apply resize cache activation",
            sums.get("moe_apply_resize_cache_activation"),
            _pct_optional(sums.get("moe_apply_resize_cache_activation"), total),
            moe_substage_counts["apply_resize_cache_activation"],
        ),
        (
            "MoE apply resize cache W2 output",
            sums.get("moe_apply_resize_cache_w2_output"),
            _pct_optional(sums.get("moe_apply_resize_cache_w2_output"), total),
            moe_substage_counts["apply_resize_cache_w2_output"],
        ),
        (
            "MoE apply resize cache other",
            sums.get("moe_apply_resize_cache_other"),
            _pct_optional(sums.get("moe_apply_resize_cache_other"), total),
            moe_substage_counts["apply_resize_cache_other"],
        ),
        (
            "MoE apply dispatch W1 host",
            sums.get("moe_apply_dispatch_w1_host"),
            _pct_optional(sums.get("moe_apply_dispatch_w1_host"), total),
            moe_substage_counts["apply_dispatch_w1_host"],
        ),
        (
            "MoE apply WNA16 W1 invoke setup host",
            sums.get("moe_apply_wna16_w1_invoke_setup_host"),
            _pct_optional(sums.get("moe_apply_wna16_w1_invoke_setup_host"), total),
            moe_substage_counts["apply_wna16_w1_invoke_setup_host"],
        ),
        (
            "MoE apply WNA16 W1 enqueue host",
            sums.get("moe_apply_wna16_w1_enqueue_host"),
            _pct_optional(sums.get("moe_apply_wna16_w1_enqueue_host"), total),
            moe_substage_counts["apply_wna16_w1_enqueue_host"],
        ),
        (
            "MoE apply WNA16 W1 event sync wait",
            sums.get("moe_apply_wna16_w1_event_sync_wait"),
            _pct_optional(sums.get("moe_apply_wna16_w1_event_sync_wait"), total),
            moe_substage_counts["apply_wna16_w1_event_sync_wait"],
        ),
        (
            "MoE apply W1 dispatch host minus launch parts",
            sums.get("moe_apply_dispatch_w1_host_minus_launch_parts"),
            _pct_optional(
                sums.get("moe_apply_dispatch_w1_host_minus_launch_parts"),
                total,
            ),
            moe_substage_counts["apply_dispatch_w1_host"],
        ),
        (
            "MoE apply dispatch W1 host minus GPU-event",
            sums.get("moe_apply_dispatch_w1_host_minus_gpu_event"),
            _pct_optional(
                sums.get("moe_apply_dispatch_w1_host_minus_gpu_event"),
                total,
            ),
            moe_substage_counts["apply_dispatch_w1_host"],
        ),
        (
            "MoE apply activation",
            sums.get("moe_apply_activation"),
            _pct_optional(sums.get("moe_apply_activation"), total),
            moe_substage_counts["apply_activation"],
        ),
        (
            "MoE apply dispatch W2 host",
            sums.get("moe_apply_dispatch_w2_host"),
            _pct_optional(sums.get("moe_apply_dispatch_w2_host"), total),
            moe_substage_counts["apply_dispatch_w2_host"],
        ),
        (
            "MoE apply WNA16 W2 invoke setup host",
            sums.get("moe_apply_wna16_w2_invoke_setup_host"),
            _pct_optional(sums.get("moe_apply_wna16_w2_invoke_setup_host"), total),
            moe_substage_counts["apply_wna16_w2_invoke_setup_host"],
        ),
        (
            "MoE apply WNA16 W2 enqueue host",
            sums.get("moe_apply_wna16_w2_enqueue_host"),
            _pct_optional(sums.get("moe_apply_wna16_w2_enqueue_host"), total),
            moe_substage_counts["apply_wna16_w2_enqueue_host"],
        ),
        (
            "MoE apply WNA16 W2 event sync wait",
            sums.get("moe_apply_wna16_w2_event_sync_wait"),
            _pct_optional(sums.get("moe_apply_wna16_w2_event_sync_wait"), total),
            moe_substage_counts["apply_wna16_w2_event_sync_wait"],
        ),
        (
            "MoE apply W2 dispatch host minus launch parts",
            sums.get("moe_apply_dispatch_w2_host_minus_launch_parts"),
            _pct_optional(
                sums.get("moe_apply_dispatch_w2_host_minus_launch_parts"),
                total,
            ),
            moe_substage_counts["apply_dispatch_w2_host"],
        ),
        (
            "MoE apply dispatch W2 host minus GPU-event",
            sums.get("moe_apply_dispatch_w2_host_minus_gpu_event"),
            _pct_optional(
                sums.get("moe_apply_dispatch_w2_host_minus_gpu_event"),
                total,
            ),
            moe_substage_counts["apply_dispatch_w2_host"],
        ),
        (
            "MoE apply dispatch W1+W2 host minus GPU-event",
            sums.get("moe_apply_dispatch_w1w2_host_minus_gpu_event"),
            _pct_optional(
                sums.get("moe_apply_dispatch_w1w2_host_minus_gpu_event"),
                total,
            ),
            moe_substage_counts["quant_method_apply"]
            if moe_substage_counts["apply_dispatch_w1_host"]
            and moe_substage_counts["apply_dispatch_w2_host"]
            else None,
        ),
        (
            "MoE apply dispatch other host",
            sums.get("moe_apply_dispatch_other_host"),
            _pct_optional(sums.get("moe_apply_dispatch_other_host"), total),
            moe_substage_counts["apply_dispatch_other_host"],
        ),
        (
            "MoE apply moe_sum",
            sums.get("moe_apply_moe_sum"),
            _pct_optional(sums.get("moe_apply_moe_sum"), total),
            moe_substage_counts["apply_moe_sum"],
        ),
        (
            "MoE quant apply measured parts sum",
            sums.get("moe_quant_apply_measured_parts_sum"),
            _pct_optional(sums.get("moe_quant_apply_measured_parts_sum"), total),
            moe_substage_counts["quant_method_apply"]
            if moe_substage_counts["quant_method_apply"]
            else None,
        ),
        (
            "MoE quant apply minus measured parts",
            sums.get("moe_quant_apply_minus_measured_parts"),
            _pct_optional(sums.get("moe_quant_apply_minus_measured_parts"), total),
            moe_substage_counts["quant_method_apply"]
            if moe_substage_counts["quant_method_apply"]
            else None,
        ),
        (
            "MoE experts minus quant_method.apply",
            sums.get("moe_experts_total_minus_quant_apply"),
            _pct_optional(sums.get("moe_experts_total_minus_quant_apply"), total),
            moe_substage_counts["experts_total"]
            if moe_substage_counts["experts_total"]
            and moe_substage_counts["quant_method_apply"]
            else None,
        ),
        (
            "MoE experts total measured parts sum",
            sums.get("moe_experts_total_measured_parts_sum"),
            _pct_optional(sums.get("moe_experts_total_measured_parts_sum"), total),
            moe_substage_counts["experts_total"],
        ),
        (
            "MoE experts total minus measured parts",
            sums.get("moe_experts_total_minus_measured_parts"),
            _pct_optional(sums.get("moe_experts_total_minus_measured_parts"), total),
            moe_substage_counts["experts_total"],
        ),
        (
            "MoE quant apply minus prepare+WNA16",
            sums.get("moe_quant_apply_minus_prepare_wna16"),
            _pct_optional(sums.get("moe_quant_apply_minus_prepare_wna16"), total),
            moe_substage_counts["quant_method_apply"]
            if moe_substage_counts["quant_method_apply"]
            else None,
        ),
        (
            "decode decoder non-MoE residual",
            sums.get("decode_decoder_layer_minus_moe_apply"),
            _pct_optional(sums.get("decode_decoder_layer_minus_moe_apply"), total),
            decoder_decode_count if decoder_decode_count and moe_count else None,
        ),
        (
            "decode outside attention+MLP residual",
            sums.get("decode_decoder_outside_attention_mlp"),
            _pct_optional(sums.get("decode_decoder_outside_attention_mlp"), total),
            decoder_decode_count
            if decoder_decode_count and attention_count and mlp_count
            else None,
        ),
        (
            "decode MLP minus MoE apply",
            sums.get("decode_mlp_minus_moe_apply"),
            _pct_optional(sums.get("decode_mlp_minus_moe_apply"), total),
            mlp_count if mlp_count and moe_count else None,
        ),
        (
            "WNA16 W1 GPU event",
            sums.get("wna16_w1_gpu_event"),
            _pct(sums.get("wna16_w1_gpu_event") or 0.0, total),
            wna16_counts_by_bucket["w1"],
        ),
        (
            "WNA16 W2 GPU event",
            sums.get("wna16_w2_gpu_event"),
            _pct(sums.get("wna16_w2_gpu_event") or 0.0, total),
            wna16_counts_by_bucket["w2"],
        ),
        (
            "WNA16 other GPU event",
            sums.get("wna16_other_gpu_event"),
            _pct(sums.get("wna16_other_gpu_event") or 0.0, total),
            wna16_counts_by_bucket["other"],
        ),
        (
            "MoE apply minus WNA16 GPU-event sum",
            sums.get("moe_apply_minus_wna16_gpu_event"),
            _pct(sums.get("moe_apply_minus_wna16_gpu_event") or 0.0, total),
            moe_count,
        ),
        (
            "generate minus decode MoE apply",
            sums.get("generate_minus_decode_moe_apply"),
            _pct(sums.get("generate_minus_decode_moe_apply") or 0.0, total),
            None,
        ),
        (
            "generate minus decode decoder layer",
            sums.get("generate_minus_decode_decoder_layer"),
            _pct_optional(sums.get("generate_minus_decode_decoder_layer"), total),
            None,
        ),
    ]
    attributable_rows = sorted(
        [
            row
            for row in rows
            if row[0]
            in {
                "decode MoE layer apply",
                "decode decoder layer total",
                "decode decoder non-MoE residual",
                "decode attention",
                "attention handoff linear proj total",
                "attention handoff norm",
                "attention handoff core prep-layout",
                "attention handoff conv update",
                "attention handoff recurrent",
                "attention handoff core post-layout",
                "attention handoff out proj",
                "decode MLP/MoE block",
                "decode outside attention+MLP residual",
                "decode MLP minus MoE apply",
                "MoE experts total",
                "MoE router logits",
                "MoE select_experts",
                "MoE select compute_routing",
                "MoE select record_topk",
                "MoE select_experts minus record_topk",
                "MoE experts shared stream sync",
                "MoE experts maybe dispatch",
                "MoE experts maybe combine",
                "MoE experts shared no-overlap",
                "MoE experts shared determine order",
                "MoE experts shared apply skipped",
                "MoE experts shared direct layer",
                "MoE experts shared aux-stream layer+wait",
                "MoE experts shared no-overlap inner parts sum",
                "MoE experts shared no-overlap minus inner parts",
                "MoE experts pre-quant apply glue",
                "MoE experts shared overlap",
                "MoE experts shared output fetch",
                "MoE experts non-apply measured parts sum",
                "MoE prepare_expert_assignment",
                "MoE quant_method.apply",
                "MoE quant_method.apply monolithic",
                "MoE apply problem size",
                "MoE apply config lookup",
                "MoE apply resize cache W1 output",
                "MoE apply resize cache activation",
                "MoE apply resize cache W2 output",
                "MoE apply resize cache other",
                "MoE apply alloc cache13",
                "MoE apply alloc activation cache",
                "MoE apply alloc output",
                "MoE apply alloc other",
                "MoE apply dispatch W1 host",
                "MoE apply WNA16 W1 invoke setup host",
                "MoE apply WNA16 W1 enqueue host",
                "MoE apply WNA16 W1 event sync wait",
                "MoE apply W1 dispatch host minus launch parts",
                "MoE apply dispatch W1 host minus GPU-event",
                "MoE apply activation",
                "MoE apply dispatch W2 host",
                "MoE apply WNA16 W2 invoke setup host",
                "MoE apply WNA16 W2 enqueue host",
                "MoE apply WNA16 W2 event sync wait",
                "MoE apply W2 dispatch host minus launch parts",
                "MoE apply dispatch W2 host minus GPU-event",
                "MoE apply dispatch W1+W2 host minus GPU-event",
                "MoE apply dispatch other host",
                "MoE apply moe_sum",
                "MoE quant apply measured parts sum",
                "MoE quant apply minus measured parts",
                "MoE experts minus quant_method.apply",
                "MoE experts total measured parts sum",
                "MoE experts total minus measured parts",
                "MoE quant apply minus prepare+WNA16",
                "WNA16 W1 GPU event",
                "WNA16 W2 GPU event",
                "WNA16 other GPU event",
                "MoE apply minus WNA16 GPU-event sum",
            }
            and row[1] is not None
        ],
        key=lambda row: float(row[1]),
        reverse=True,
    )
    lines = [
        "# AWQ/vLLM Decode Breakdown",
        "",
        f"trace_dir: `{result['trace_dir']}`",
        "",
        "Note: GPU-event rows are synchronized diagnostic timings; use this table for attribution, not production TPOT claims.",
        "`generate minus decode MoE apply` is an unattributed remainder, not a single module bottleneck.",
        "`generate minus decode decoder layer` is the remaining engine/scheduler/sampling/uninstrumented remainder when decoder timing is available.",
        "`decode decoder layer total` contains attention, MLP/MoE, and residual/norm/launch overhead; nested rows are not additive.",
        "`engine_*` rows are nested host-wall diagnostic counters; `execute_model` contains model forward/logits and `sample_tokens` contains sampler/bookkeeping.",
        "`decode_attention_linear_source_method_nested_sum` is a nested diagnostic counter set: `_forward_core` contains `_forward_core_decode_non_spec`, so do not treat this sum as additive attention cost.",
        "`attention handoff core prep-layout` and `attention handoff core post-layout` are derived residuals from nested low-intrusion counters; check the negative-residual anomaly flags before treating them as named costs.",
        "Attention leaf/source rows are Python-hook diagnostic timings; they localize targets but are not production TPOT evidence.",
        "`decode MLP minus MoE apply` is the MLP/MoE block residual relative to MoE apply, not a pure FFN-only measurement.",
        "`MoE router logits` can be a duplicate trace gate measurement in vLLM paths that pass precomputed router_logits into FusedMoE; use its status counts before treating it as production forward cost.",
        "`MoE select record_topk` is tracing/logging overhead from this diagnostic run, not production router compute.",
        "`MoE quant apply measured parts sum` is a nested diagnostic host-wall decomposition; do not add it to `quant_method.apply` as an independent component.",
        "`MoE quant apply minus prepare+WNA16` mixes host wall-time and synchronized GPU-event timing; use it only as a diagnostic residual.",
        "Decode/prefill phase labels are based on a `num_tokens` heuristic; validate phase counts before drawing conclusions for batched decode.",
        "",
        "| component | sum ms | per output token ms | per relevant row us | share of generate |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, value_us, share, row_count in rows:
        value_ms = float(value_us) / 1000.0 if value_us is not None else None
        per_row = _per_layer_us(value_us, row_count)
        lines.append(
            "| {name} | {sum_ms} | {per_token} | {per_layer} | {share} |".format(
                name=name,
                sum_ms=_fmt(value_ms),
                per_token=_fmt(_per_token_ms(value_us, output_tokens)),
                per_layer=_fmt(per_row),
                share=_fmt(share, "%"),
            )
        )

    lines.extend(
        [
            "",
            "## Largest Attributable Components",
            "",
            "Nested rows are not additive: `decode decoder layer total` contains the MoE and non-MoE decoder work.",
            "",
            "| rank | component | sum ms | share of generate |",
            "|---:|---|---:|---:|",
        ]
    )
    for rank, (name, value_us, share, _row_count) in enumerate(
        attributable_rows,
        start=1,
    ):
        lines.append(
            f"| {rank} | {name} | {_fmt(float(value_us) / 1000.0)} | {_fmt(share, '%')} |"
        )
    lines.extend(
        [
            "",
            "## Residual / Integrity",
            "",
            "| field | value |",
            "|---|---:|",
            f"| generate minus decode MoE apply ms | {_fmt((sums.get('generate_minus_decode_moe_apply') or 0.0) / 1000.0)} |",
            f"| generate minus decode decoder layer ms | {_fmt((sums.get('generate_minus_decode_decoder_layer') or 0.0) / 1000.0)} |",
            f"| decode decoder layer minus MoE apply ms | {_fmt((sums.get('decode_decoder_layer_minus_moe_apply') or 0.0) / 1000.0)} |",
            f"| decode decoder outside attention+MLP ms | {_fmt((sums.get('decode_decoder_outside_attention_mlp') or 0.0) / 1000.0)} |",
            f"| decode MLP minus MoE apply ms | {_fmt((sums.get('decode_mlp_minus_moe_apply') or 0.0) / 1000.0)} |",
            f"| MoE experts total minus quant_method.apply ms | {_fmt((sums.get('moe_experts_total_minus_quant_apply') or 0.0) / 1000.0)} |",
            f"| MoE select_experts minus record_topk ms | {_fmt((sums.get('moe_select_experts_minus_record_topk') or 0.0) / 1000.0)} |",
            f"| MoE quant apply measured parts sum ms | {_fmt((sums.get('moe_quant_apply_measured_parts_sum') or 0.0) / 1000.0)} |",
            f"| MoE quant apply minus measured parts ms | {_fmt((sums.get('moe_quant_apply_minus_measured_parts') or 0.0) / 1000.0)} |",
            f"| MoE apply source fused_experts outer ms | {_fmt((sums.get('moe_apply_source_fused_experts_outer') or 0.0) / 1000.0)} |",
            f"| MoE apply source fused_experts_impl total ms | {_fmt((sums.get('moe_apply_source_impl_total') or 0.0) / 1000.0)} |",
            f"| MoE quant apply minus fused_experts outer ms | {_fmt((sums.get('moe_quant_apply_minus_fused_experts_outer') or 0.0) / 1000.0)} |",
            f"| MoE fused_experts outer minus inner source parts ms | {_fmt((sums.get('moe_fused_experts_outer_minus_inner_source_parts') or 0.0) / 1000.0)} |",
            f"| MoE fused_experts outer parts sum ms | {_fmt((sums.get('moe_fused_experts_outer_parts_sum') or 0.0) / 1000.0)} |",
            f"| MoE fused_experts outer minus outer parts ms | {_fmt((sums.get('moe_fused_experts_outer_minus_outer_parts') or 0.0) / 1000.0)} |",
            f"| MoE fused_experts outer minus impl total ms | {_fmt((sums.get('moe_fused_experts_outer_minus_impl_total') or 0.0) / 1000.0)} |",
            f"| MoE fused_experts outer impl-call minus impl-total ms | {_fmt((sums.get('moe_fused_experts_outer_impl_call_minus_impl_total') or 0.0) / 1000.0)} |",
            f"| MoE fused_experts impl total minus inner source parts ms | {_fmt((sums.get('moe_fused_experts_impl_total_minus_inner_source_parts') or 0.0) / 1000.0)} |",
            f"| MoE quant apply source parts sum ms | {_fmt((sums.get('moe_quant_apply_source_parts_sum') or 0.0) / 1000.0)} |",
            f"| MoE quant apply minus source parts ms | {_fmt((sums.get('moe_quant_apply_minus_source_parts') or 0.0) / 1000.0)} |",
            f"| MoE source W1 enqueue minus launch parts ms | {_fmt((sums.get('moe_apply_source_w1_enqueue_minus_launch_parts') or 0.0) / 1000.0)} |",
            f"| MoE source W2 enqueue minus launch parts ms | {_fmt((sums.get('moe_apply_source_w2_enqueue_minus_launch_parts') or 0.0) / 1000.0)} |",
            f"| MoE quant apply minus prepare+WNA16 ms | {_fmt((sums.get('moe_quant_apply_minus_prepare_wna16') or 0.0) / 1000.0)} |",
            f"| MoE shared direct source parts sum ms | {_fmt((sums.get('moe_experts_shared_direct_source_parts_sum') or 0.0) / 1000.0)} |",
            f"| MoE shared direct minus source parts ms | {_fmt((sums.get('moe_experts_shared_direct_minus_source_parts') or 0.0) / 1000.0)} |",
            f"| MoE apply minus WNA16 GPU-event sum ms | {_fmt((sums.get('moe_apply_minus_wna16_gpu_event') or 0.0) / 1000.0)} |",
            f"| residual anomaly | `{bool(any(result.get('anomalies', {}).values()))}` |",
            f"| WNA16 decode phase filter available | `{bool(shadow['integrity']['wna16_decode_filter_available'])}` |",
            f"| WNA16 GPU-event timing diagnostic-only | `{bool(shadow['integrity'].get('wna16_gpu_event_timing_diagnostic_only'))}` |",
        ]
    )
    decoder = shadow["decoder_layer_us"]
    lines.extend(
        [
            "",
            "## Decoder Layer Buckets",
            "",
            "| phase | count | p50 us | p95 us | sum ms |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for phase in ("decode", "prefill", "unknown"):
        row = decoder[phase]
        lines.append(
            "| {phase} | {count} | {p50} | {p95} | {sum_ms} |".format(
                phase=phase,
                count=int(row.get("count") or 0),
                p50=_fmt(row.get("p50")),
                p95=_fmt(row.get("p95")),
                sum_ms=_fmt(
                    float(row["sum_us"]) / 1000.0
                    if row.get("sum_us") is not None
                    else None
                ),
            )
        )

    components = shadow["decoder_component_us"]
    lines.extend(
        [
            "",
            "## Decoder Component Buckets",
            "",
            "| component | phase | count | p50 us | p95 us | sum ms |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for component in sorted(components):
        for phase in ("decode", "prefill", "unknown"):
            row = components[component][phase]
            lines.append(
                "| {component} | {phase} | {count} | {p50} | {p95} | {sum_ms} |".format(
                    component=component,
                    phase=phase,
                    count=int(row.get("count") or 0),
                    p50=_fmt(row.get("p50")),
                    p95=_fmt(row.get("p95")),
                    sum_ms=_fmt(
                        float(row["sum_us"]) / 1000.0
                        if row.get("sum_us") is not None
                        else None
                    ),
                )
            )

    substages = shadow["moe_substage_us"]
    lines.extend(
        [
            "",
            "## MoE Substage Buckets",
            "",
            "| substage | phase | count | p50 us | p95 us | sum ms |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for substage in (
        "router_logits",
        "experts_total",
        "select_experts",
        "select_validate_eplb",
        "select_indices_type",
        "select_compute_routing",
        "select_capture_logical_ids",
        "select_eplb_mapping",
        "select_dtype_convert",
        "select_record_topk",
        "prepare_expert_assignment",
        "quant_method_apply",
        "apply_quantize_hidden",
        "apply_dispatch_w1_host",
        "apply_activation",
        "apply_quantize_intermediate",
        "apply_dispatch_w2_host",
        "apply_dispatch_other_host",
        "apply_moe_sum",
        "other",
    ):
        for phase in ("decode", "prefill", "unknown"):
            row = substages[substage][phase]
            lines.append(
                "| {substage} | {phase} | {count} | {p50} | {p95} | {sum_ms} |".format(
                    substage=substage,
                    phase=phase,
                    count=int(row.get("count") or 0),
                    p50=_fmt(row.get("p50")),
                    p95=_fmt(row.get("p95")),
                    sum_ms=_fmt(
                        float(row["sum_us"]) / 1000.0
                        if row.get("sum_us") is not None
                        else None
                    ),
                )
            )

    lines.extend(
        [
            "",
            "## Kernel Buckets",
            "",
            "| bucket | count | GPU p50 us | GPU p95 us | host p50 us | host p95 us |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for bucket in ("w1", "w2", "other"):
        gpu = shadow["wna16_gpu_us"][bucket]
        host = shadow["wna16_host_us"][bucket]
        lines.append(
            "| {bucket} | {count} | {gpu_p50} | {gpu_p95} | {host_p50} | {host_p95} |".format(
                bucket=bucket,
                count=int(gpu.get("count") or host.get("count") or 0),
                gpu_p50=_fmt(gpu.get("p50")),
                gpu_p95=_fmt(gpu.get("p95")),
                host_p50=_fmt(host.get("p50")),
                host_p95=_fmt(host.get("p95")),
            )
        )
    lines.extend(
        [
            "",
            "## Counts",
            "",
            "```json",
            json.dumps(
                {
                    "wna16_counts": shadow["wna16_counts"],
                    "timing_kind_counts": shadow["wna16_timing_kind_counts"],
                    "status_counts": shadow["wna16_status_counts"],
                    "integrity": shadow["integrity"],
                    "anomalies": result.get("anomalies", {}),
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_dir", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    result = build_breakdown(args.trace_dir)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(result, args.output_md)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
