#!/usr/bin/env python3
"""Summarize AWQ/vLLM bottlenecks with telemetry-level boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path | None) -> dict[str, Any] | list[Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text())


def _mode_row(results: list[dict[str, Any]], mode: str) -> dict[str, Any] | None:
    for row in results:
        if row.get("mode") == mode and row.get("returncode") == 0:
            return row
    return None


def _first_mode_row(
    results: list[dict[str, Any]],
    modes: tuple[str, ...],
) -> tuple[str | None, dict[str, Any] | None]:
    for mode in modes:
        row = _mode_row(results, mode)
        if row is not None:
            return mode, row
    return None, None


def _sum_us(breakdown: dict[str, Any] | None, key: str) -> float | None:
    if breakdown is None:
        return None
    value = breakdown.get("sums_us", {}).get(key)
    return float(value) if value is not None else None


def _perf_seconds(breakdown: dict[str, Any] | None, key: str) -> float | None:
    if breakdown is None:
        return None
    value = breakdown.get("performance", {}).get(key)
    return float(value) if value is not None else None


def _row_seconds(row: dict[str, Any] | None, key: str) -> float | None:
    if row is None:
        return None
    value = row.get(key)
    return float(value) if value is not None else None


def _pct(value_us: float | None, total_us: float | None) -> float | None:
    if value_us is None or total_us is None or total_us <= 0:
        return None
    return 100.0 * float(value_us) / float(total_us)


def _ms(value_us: float | None) -> float | None:
    return None if value_us is None else float(value_us) / 1000.0


def _speedup(base_tpot: float | None, candidate_tpot: float | None) -> float | None:
    if base_tpot is None or candidate_tpot is None or candidate_tpot <= 0:
        return None
    return float(base_tpot) / float(candidate_tpot)


def build_summary(
    *,
    results_json: Path | None,
    diagnostic_breakdown: Path | None,
    attention_core_breakdown: Path | None,
    decoder_layer_breakdown: Path | None = None,
    shared_expert_breakdown: Path | None = None,
    attention_total_breakdown: Path | None = None,
    shared_body_total_breakdown: Path | None = None,
    engine_breakdown: Path | None = None,
    diagnostic_mode_override: str | None = None,
) -> dict[str, Any]:
    raw_results = _load_json(results_json)
    results = raw_results if isinstance(raw_results, list) else []
    diagnostic = _load_json(diagnostic_breakdown)
    if diagnostic is not None and not isinstance(diagnostic, dict):
        raise TypeError("diagnostic breakdown must be a JSON object")
    attention_core = _load_json(attention_core_breakdown)
    if attention_core is not None and not isinstance(attention_core, dict):
        raise TypeError("attention-core breakdown must be a JSON object")
    decoder_layer = _load_json(decoder_layer_breakdown)
    if decoder_layer is not None and not isinstance(decoder_layer, dict):
        raise TypeError("decoder-layer breakdown must be a JSON object")
    shared_expert = _load_json(shared_expert_breakdown)
    if shared_expert is not None and not isinstance(shared_expert, dict):
        raise TypeError("shared-expert breakdown must be a JSON object")
    attention_total = _load_json(attention_total_breakdown)
    if attention_total is not None and not isinstance(attention_total, dict):
        raise TypeError("attention-total breakdown must be a JSON object")
    shared_body_total = _load_json(shared_body_total_breakdown)
    if shared_body_total is not None and not isinstance(shared_body_total, dict):
        raise TypeError("shared-body-total breakdown must be a JSON object")
    engine = _load_json(engine_breakdown)
    if engine is not None and not isinstance(engine, dict):
        raise TypeError("engine breakdown must be a JSON object")

    production_row = _mode_row(results, "production_like")
    detected_diagnostic_mode, diagnostic_row = _first_mode_row(
        results,
        ("diagnostic_light", "diagnostic_coarse_breakdown"),
    )
    diagnostic_mode = (
        diagnostic_mode_override
        or detected_diagnostic_mode
        or "diagnostic_unknown"
    )
    attention_core_row = _mode_row(results, "attention_core_light")
    shared_expert_row = _mode_row(results, "shared_expert_light")
    production_tpot = _row_seconds(
        production_row,
        "generate_seconds_per_requested_output_token",
    )
    diagnostic_tpot = _row_seconds(
        diagnostic_row,
        "generate_seconds_per_requested_output_token",
    )
    attention_core_tpot = _row_seconds(
        attention_core_row,
        "generate_seconds_per_requested_output_token",
    )
    shared_expert_tpot = _row_seconds(
        shared_expert_row,
        "generate_seconds_per_requested_output_token",
    )
    if diagnostic_tpot is None:
        diagnostic_tpot = _perf_seconds(
            diagnostic if isinstance(diagnostic, dict) else None,
            "generate_seconds_per_requested_output_token",
        )
    if attention_core_tpot is None:
        attention_core_tpot = _perf_seconds(
            attention_core if isinstance(attention_core, dict) else None,
            "generate_seconds_per_requested_output_token",
        )
    if shared_expert_tpot is None:
        shared_expert_tpot = _perf_seconds(
            shared_expert if isinstance(shared_expert, dict) else None,
            "generate_seconds_per_requested_output_token",
        )

    diagnostic_generate_us = _sum_us(diagnostic, "generate")
    attention_core_generate_us = _sum_us(attention_core, "generate")
    decoder_layer_generate_us = _sum_us(decoder_layer, "generate")
    if diagnostic_generate_us is None:
        diagnostic_generate_s = _perf_seconds(diagnostic, "generate_wall_seconds")
        diagnostic_generate_us = (
            diagnostic_generate_s * 1_000_000.0
            if diagnostic_generate_s is not None
            else None
        )
    if attention_core_generate_us is None:
        attention_core_generate_s = _perf_seconds(
            attention_core,
            "generate_wall_seconds",
        )
        attention_core_generate_us = (
            attention_core_generate_s * 1_000_000.0
            if attention_core_generate_s is not None
            else None
        )
    if decoder_layer_generate_us is None:
        decoder_layer_generate_s = _perf_seconds(
            decoder_layer,
            "generate_wall_seconds",
        )
        decoder_layer_generate_us = (
            decoder_layer_generate_s * 1_000_000.0
            if decoder_layer_generate_s is not None
            else None
        )

    engine_residual_us = _sum_us(diagnostic, "generate_minus_decode_decoder_layer")
    shared_source = shared_expert if shared_expert is not None else diagnostic
    shared_source_generate_us = _sum_us(shared_source, "generate")
    if shared_source_generate_us is None:
        shared_source_generate_s = _perf_seconds(shared_source, "generate_wall_seconds")
        shared_source_generate_us = (
            shared_source_generate_s * 1_000_000.0
            if shared_source_generate_s is not None
            else None
        )
    shared_gate_us = _sum_us(shared_source, "moe_experts_shared_output_gate")
    shared_sigmoid_mul_us = _sum_us(
        shared_source,
        "moe_experts_shared_output_sigmoid_mul",
    )
    shared_direct_us = _sum_us(shared_source, "moe_experts_shared_direct_layer")
    attention_total_generate_us = _sum_us(attention_total, "generate")
    shared_body_generate_us = _sum_us(shared_body_total, "generate")
    engine_generate_us = _sum_us(engine, "generate")
    if attention_total_generate_us is None:
        attention_total_generate_s = _perf_seconds(
            attention_total,
            "generate_wall_seconds",
        )
        attention_total_generate_us = (
            attention_total_generate_s * 1_000_000.0
            if attention_total_generate_s is not None
            else None
        )
    if shared_body_generate_us is None:
        shared_body_generate_s = _perf_seconds(
            shared_body_total,
            "generate_wall_seconds",
        )
        shared_body_generate_us = (
            shared_body_generate_s * 1_000_000.0
            if shared_body_generate_s is not None
            else None
        )
    if engine_generate_us is None:
        engine_generate_s = _perf_seconds(engine, "generate_wall_seconds")
        engine_generate_us = (
            engine_generate_s * 1_000_000.0
            if engine_generate_s is not None
            else None
        )

    summary = {
        "telemetry_contract": {
            "production_like": "TPOT/generate baseline only; no diagnostic attribution.",
            "diagnostic_light": (
                "coarse decoder/MoE/shared-expert attribution; not a production TPOT claim."
            ),
            "diagnostic_coarse_breakdown": (
                "single-artifact coarse diagnostic with decoder component rows, shared-body aggregate, and engine timing; not a production TPOT claim."
            ),
            "attention_core_light": (
                "linear/GDN source-method attribution only; diagnostic-only due to method-wrapper overhead."
            ),
            "shared_expert_light": (
                "shared expert source attribution only; diagnostic-only due to source wrapper overhead."
            ),
            "decoder_layer_only": (
                "low-intrusion decoder total timing; no component/MoE substage rows."
            ),
        },
        "production_like": {
            "tpot_s": production_tpot,
            "generate_s": _row_seconds(production_row, "generate_wall_seconds"),
        },
        "telemetry_overhead": {
            "diagnostic_mode": diagnostic_mode,
            "diagnostic_light_fields_legacy_alias_of": diagnostic_mode,
            "diagnostic_tpot_s": diagnostic_tpot,
            "diagnostic_speedup_vs_production": _speedup(
                production_tpot,
                diagnostic_tpot,
            ),
            "diagnostic_overhead_pct": (
                100.0 * (diagnostic_tpot / production_tpot - 1.0)
                if diagnostic_tpot is not None
                and production_tpot is not None
                and production_tpot > 0
                else None
            ),
            "diagnostic_light_tpot_s": diagnostic_tpot,
            "diagnostic_light_speedup_vs_production": _speedup(
                production_tpot,
                diagnostic_tpot,
            ),
            "diagnostic_light_overhead_pct": (
                100.0 * (diagnostic_tpot / production_tpot - 1.0)
                if diagnostic_tpot is not None
                and production_tpot is not None
                and production_tpot > 0
                else None
            ),
            "attention_core_light_tpot_s": attention_core_tpot,
            "attention_core_light_speedup_vs_production": _speedup(
                production_tpot,
                attention_core_tpot,
            ),
            "attention_core_light_overhead_pct": (
                100.0 * (attention_core_tpot / production_tpot - 1.0)
                if attention_core_tpot is not None
                and production_tpot is not None
                and production_tpot > 0
                else None
            ),
            "shared_expert_light_tpot_s": shared_expert_tpot,
            "shared_expert_light_speedup_vs_production": _speedup(
                production_tpot,
                shared_expert_tpot,
            ),
            "shared_expert_light_overhead_pct": (
                100.0 * (shared_expert_tpot / production_tpot - 1.0)
                if shared_expert_tpot is not None
                and production_tpot is not None
                and production_tpot > 0
                else None
            ),
        },
        "diagnostic_light_bottlenecks": {
            "generate_ms": _ms(diagnostic_generate_us),
            "decoder_layer_ms": _ms(_sum_us(diagnostic, "decode_decoder_layer")),
            "attention_ms": _ms(_sum_us(diagnostic, "decode_attention")),
            "mlp_moe_ms": _ms(_sum_us(diagnostic, "decode_mlp")),
            "moe_apply_ms": _ms(_sum_us(diagnostic, "decode_moe_layer_apply")),
            "shared_expert_direct_ms": _ms(shared_direct_us),
            "shared_expert_output_gate_ms": _ms(shared_gate_us),
            "shared_expert_sigmoid_mul_ms": _ms(shared_sigmoid_mul_us),
            "engine_residual_ms": _ms(engine_residual_us),
        },
        "diagnostic_light_shares_pct": {
            "decoder_layer": _pct(
                _sum_us(diagnostic, "decode_decoder_layer"),
                diagnostic_generate_us,
            ),
            "attention": _pct(_sum_us(diagnostic, "decode_attention"), diagnostic_generate_us),
            "mlp_moe": _pct(_sum_us(diagnostic, "decode_mlp"), diagnostic_generate_us),
            "moe_apply": _pct(
                _sum_us(diagnostic, "decode_moe_layer_apply"),
                diagnostic_generate_us,
            ),
            "shared_expert_direct": _pct(shared_direct_us, diagnostic_generate_us),
            "shared_expert_output_gate": _pct(shared_gate_us, diagnostic_generate_us),
            "engine_residual": _pct(engine_residual_us, diagnostic_generate_us),
        },
        "shared_expert_light": {
            "generate_ms": _ms(shared_source_generate_us),
            "no_overlap_ms": _ms(
                _sum_us(shared_source, "moe_experts_shared_no_overlap")
            ),
            "direct_layer_ms": _ms(shared_direct_us),
            "direct_source_parts_ms": _ms(
                _sum_us(shared_source, "moe_experts_shared_direct_source_parts_sum")
            ),
            "direct_minus_source_parts_ms": _ms(
                _sum_us(shared_source, "moe_experts_shared_direct_minus_source_parts")
            ),
            "w1_ms": _ms(_sum_us(shared_source, "moe_experts_shared_w1")),
            "activation_ms": _ms(
                _sum_us(shared_source, "moe_experts_shared_activation")
            ),
            "w2_ms": _ms(_sum_us(shared_source, "moe_experts_shared_w2")),
            "output_gate_ms": _ms(shared_gate_us),
            "output_sigmoid_mul_ms": _ms(shared_sigmoid_mul_us),
            "no_overlap_minus_inner_parts_ms": _ms(
                _sum_us(
                    shared_source,
                    "moe_experts_shared_no_overlap_minus_inner_parts",
                )
            ),
            "direct_layer_share_pct": _pct(shared_direct_us, shared_source_generate_us),
            "output_gate_share_pct": _pct(shared_gate_us, shared_source_generate_us),
        },
        "attention_core_light": {
            "generate_ms": _ms(attention_core_generate_us),
            "attention_ms": _ms(_sum_us(attention_core, "decode_attention")),
            "linear_core_total_ms": _ms(
                _sum_us(attention_core, "decode_attention_linear_core_total")
            ),
            "linear_core_decode_non_spec_ms": _ms(
                _sum_us(
                    attention_core,
                    "decode_attention_linear_core_decode_non_spec",
                )
            ),
            "linear_source_method_nested_ms": _ms(
                _sum_us(
                    attention_core,
                    "decode_attention_linear_source_method_nested_sum",
                )
            ),
            "full_leaf_parts_ms": _ms(
                _sum_us(attention_core, "decode_attention_full_leaf_parts_sum")
            ),
        },
        "decoder_layer_only": {
            "generate_ms": _ms(decoder_layer_generate_us),
            "decoder_layer_ms": _ms(_sum_us(decoder_layer, "decode_decoder_layer")),
            "engine_residual_ms": _ms(
                _sum_us(decoder_layer, "generate_minus_decode_decoder_layer")
            ),
            "decoder_layer_share_pct": _pct(
                _sum_us(decoder_layer, "decode_decoder_layer"),
                decoder_layer_generate_us,
            ),
            "engine_residual_share_pct": _pct(
                _sum_us(decoder_layer, "generate_minus_decode_decoder_layer"),
                decoder_layer_generate_us,
            ),
        },
        "low_intrusion_coarse": {
            "contract": (
                "Combines separate low-intrusion diagnostic artifacts. Shares "
                "are computed against each artifact's own generate time; do "
                "not treat this as a single-run endpoint TPOT claim."
            ),
            "attention_total_only": {
                "generate_ms": _ms(attention_total_generate_us),
                "attention_ms": _ms(_sum_us(attention_total, "decode_attention")),
                "mlp_moe_ms": _ms(_sum_us(attention_total, "decode_mlp")),
                "moe_apply_ms": _ms(
                    _sum_us(attention_total, "decode_moe_layer_apply")
                ),
                "mlp_minus_moe_apply_ms": _ms(
                    _sum_us(attention_total, "decode_mlp_minus_moe_apply")
                ),
                "outside_attention_mlp_ms": _ms(
                    _sum_us(attention_total, "decode_decoder_outside_attention_mlp")
                ),
                "attention_share_pct": _pct(
                    _sum_us(attention_total, "decode_attention"),
                    attention_total_generate_us,
                ),
                "mlp_moe_share_pct": _pct(
                    _sum_us(attention_total, "decode_mlp"),
                    attention_total_generate_us,
                ),
                "moe_apply_share_pct": _pct(
                    _sum_us(attention_total, "decode_moe_layer_apply"),
                    attention_total_generate_us,
                ),
            },
            "shared_body_total_only": {
                "generate_ms": _ms(shared_body_generate_us),
                "shared_direct_ms": _ms(
                    _sum_us(shared_body_total, "moe_experts_shared_direct_layer")
                ),
                "shared_direct_share_pct": _pct(
                    _sum_us(shared_body_total, "moe_experts_shared_direct_layer"),
                    shared_body_generate_us,
                ),
                "moe_apply_ms": _ms(
                    _sum_us(shared_body_total, "decode_moe_layer_apply")
                ),
                "moe_apply_share_pct": _pct(
                    _sum_us(shared_body_total, "decode_moe_layer_apply"),
                    shared_body_generate_us,
                ),
            },
            "engine_light": {
                "generate_ms": _ms(engine_generate_us),
                "execute_model_minus_model_forward_ms": _ms(
                    _sum_us(engine, "engine_execute_model_minus_model_forward")
                ),
                "generate_minus_execute_model_ms": _ms(
                    _sum_us(engine, "engine_generate_call_minus_execute_model")
                ),
                "prepare_inputs_ms": _ms(
                    _sum_us(engine, "engine_substage_engine_prepare_inputs")
                ),
                "sample_tokens_ms": _ms(
                    _sum_us(engine, "engine_substage_engine_sample_tokens")
                ),
                "logits_processor_ms": _ms(
                    _sum_us(engine, "engine_substage_engine_logits_processor_forward")
                ),
                "sampler_forward_ms": _ms(
                    _sum_us(engine, "engine_substage_engine_sampler_forward")
                ),
                "execute_model_minus_model_forward_share_pct": _pct(
                    _sum_us(engine, "engine_execute_model_minus_model_forward"),
                    engine_generate_us,
                ),
                "generate_minus_execute_model_share_pct": _pct(
                    _sum_us(engine, "engine_generate_call_minus_execute_model"),
                    engine_generate_us,
                ),
                "sample_tokens_share_pct": _pct(
                    _sum_us(engine, "engine_substage_engine_sample_tokens"),
                    engine_generate_us,
                ),
            },
        },
        "next_targets": [
            {
                "target": "attention/GDN core",
                "status": "diagnostic target only",
                "reason": (
                    "attention_core_light localizes linear/GDN core but still adds large TPOT overhead."
                ),
            },
            {
                "target": "shared expert gate linear",
                "status": "real MoE-side candidate",
                "reason": (
                    "shared expert output gate is an explicit named component; needs low-overhead or fused implementation evidence."
                ),
            },
            {
                "target": "engine residual",
                "status": "needs lower-level vLLM engine/sampler breakdown",
                "reason": (
                    "decoder_layer_only gives a low-intrusion residual estimate; it still needs engine/sampler/logits split."
                ),
            },
        ],
    }
    return summary


def _fmt(value: float | None, digits: int = 3) -> str:
    return "" if value is None else f"{float(value):.{digits}f}"


def _fmt_pct(value: float | None, digits: int = 2) -> str:
    return "" if value is None else f"{float(value):.{digits}f}%"


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    production = summary["production_like"]
    overhead = summary["telemetry_overhead"]
    diagnostic_label = str(overhead.get("diagnostic_mode", "diagnostic_light"))
    bottlenecks = summary["diagnostic_light_bottlenecks"]
    shares = summary["diagnostic_light_shares_pct"]
    attention = summary["attention_core_light"]
    shared_expert = summary["shared_expert_light"]
    decoder_layer = summary["decoder_layer_only"]
    low_intrusion = summary.get("low_intrusion_coarse", {})
    low_attention = low_intrusion.get("attention_total_only", {})
    low_shared = low_intrusion.get("shared_body_total_only", {})
    low_engine = low_intrusion.get("engine_light", {})
    lines = [
        "# AWQ Real Bottleneck Summary",
        "",
        "## Telemetry Contract",
        "",
    ]
    for key, text in summary["telemetry_contract"].items():
        lines.append(f"- `{key}`: {text}")
    lines.extend(
        [
            "",
            "## TPOT",
            "",
            "| mode | TPOT s/token | speedup vs production | overhead vs production |",
            "|---|---:|---:|---:|",
            (
                f"| production_like | {_fmt(production.get('tpot_s'), 6)} | "
                f"{'1.000' if production.get('tpot_s') is not None else ''} | "
                f"{'0.000%' if production.get('tpot_s') is not None else ''} |"
            ),
            (
                f"| {diagnostic_label} | "
                f"{_fmt(overhead.get('diagnostic_tpot_s'), 6)} | "
                f"{_fmt(overhead.get('diagnostic_speedup_vs_production'), 4)} | "
                f"{_fmt_pct(overhead.get('diagnostic_overhead_pct'))} |"
            ),
            (
                f"| attention_core_light | {_fmt(overhead.get('attention_core_light_tpot_s'), 6)} | "
                f"{_fmt(overhead.get('attention_core_light_speedup_vs_production'), 4)} | "
                f"{_fmt_pct(overhead.get('attention_core_light_overhead_pct'))} |"
            ),
            (
                f"| shared_expert_light | {_fmt(overhead.get('shared_expert_light_tpot_s'), 6)} | "
                f"{_fmt(overhead.get('shared_expert_light_speedup_vs_production'), 4)} | "
                f"{_fmt_pct(overhead.get('shared_expert_light_overhead_pct'))} |"
            ),
            "",
            (
                "`diagnostic_light_*` JSON fields are retained as legacy aliases "
                f"for the active diagnostic mode `{diagnostic_label}`."
            ),
            "",
            f"## {diagnostic_label} Bottlenecks",
            "",
            "| component | ms | share of diagnostic generate |",
            "|---|---:|---:|",
        ]
    )
    rows = [
        ("decoder layer", "decoder_layer_ms", "decoder_layer"),
        ("attention", "attention_ms", "attention"),
        ("MLP/MoE", "mlp_moe_ms", "mlp_moe"),
        ("MoE apply", "moe_apply_ms", "moe_apply"),
        ("shared expert direct", "shared_expert_direct_ms", "shared_expert_direct"),
        (
            "shared expert output gate",
            "shared_expert_output_gate_ms",
            "shared_expert_output_gate",
        ),
        ("engine residual", "engine_residual_ms", "engine_residual"),
    ]
    for label, ms_key, share_key in rows:
        lines.append(
            f"| {label} | {_fmt(bottlenecks.get(ms_key))} | "
            f"{_fmt_pct(shares.get(share_key))} |"
        )
    lines.extend(
        [
            "",
            "## Attention-Core Light",
            "",
            "These rows are nested diagnostic counters. Do not add them together "
            "or treat them as production timing shares.",
            "",
            "| component | ms |",
            "|---|---:|",
            f"| attention total | {_fmt(attention.get('attention_ms'))} |",
            f"| linear core total | {_fmt(attention.get('linear_core_total_ms'))} |",
            (
                "| linear core decode non-spec | "
                f"{_fmt(attention.get('linear_core_decode_non_spec_ms'))} |"
            ),
            (
                "| linear source method nested sum | "
                f"{_fmt(attention.get('linear_source_method_nested_ms'))} |"
            ),
            f"| full-attention leaf parts | {_fmt(attention.get('full_leaf_parts_ms'))} |",
            "",
            "## Shared-Expert Light",
            "",
            "These rows are source-split diagnostic counters. They localize shared "
            "expert targets but are not production timing shares.",
            "",
            "| component | ms | share of shared-expert-light generate |",
            "|---|---:|---:|",
            (
                f"| shared no-overlap | {_fmt(shared_expert.get('no_overlap_ms'))} |  |"
            ),
            (
                f"| shared direct layer | {_fmt(shared_expert.get('direct_layer_ms'))} | "
                f"{_fmt_pct(shared_expert.get('direct_layer_share_pct'))} |"
            ),
            (
                f"| shared direct source parts | "
                f"{_fmt(shared_expert.get('direct_source_parts_ms'))} |  |"
            ),
            (
                f"| shared direct minus source parts | "
                f"{_fmt(shared_expert.get('direct_minus_source_parts_ms'))} |  |"
            ),
            f"| shared W1/gate-up | {_fmt(shared_expert.get('w1_ms'))} |  |",
            f"| shared activation | {_fmt(shared_expert.get('activation_ms'))} |  |",
            f"| shared W2/down | {_fmt(shared_expert.get('w2_ms'))} |  |",
            (
                f"| shared output gate | {_fmt(shared_expert.get('output_gate_ms'))} | "
                f"{_fmt_pct(shared_expert.get('output_gate_share_pct'))} |"
            ),
            (
                f"| shared output sigmoid/mul | "
                f"{_fmt(shared_expert.get('output_sigmoid_mul_ms'))} |  |"
            ),
            (
                f"| shared no-overlap minus inner parts | "
                f"{_fmt(shared_expert.get('no_overlap_minus_inner_parts_ms'))} |  |"
            ),
            "",
            "## Decoder-Layer Only",
            "",
            "This mode records decoder layer totals only. It is intended to estimate "
            "engine/scheduler/sampling/logits residual with less attribution overhead.",
            "",
            "| component | ms | share |",
            "|---|---:|---:|",
            (
                f"| decoder layer | {_fmt(decoder_layer.get('decoder_layer_ms'))} | "
                f"{_fmt_pct(decoder_layer.get('decoder_layer_share_pct'))} |"
            ),
            (
                f"| engine residual | {_fmt(decoder_layer.get('engine_residual_ms'))} | "
                f"{_fmt_pct(decoder_layer.get('engine_residual_share_pct'))} |"
            ),
            "",
            "## Low-Intrusion Coarse Baseline",
            "",
            str(low_intrusion.get("contract", "")),
            "",
            "| source | component | ms | share of source generate |",
            "|---|---|---:|---:|",
            (
                "| attention_total_only | attention | "
                f"{_fmt(low_attention.get('attention_ms'))} | "
                f"{_fmt_pct(low_attention.get('attention_share_pct'))} |"
            ),
            (
                "| attention_total_only | MLP/MoE | "
                f"{_fmt(low_attention.get('mlp_moe_ms'))} | "
                f"{_fmt_pct(low_attention.get('mlp_moe_share_pct'))} |"
            ),
            (
                "| attention_total_only | MoE apply | "
                f"{_fmt(low_attention.get('moe_apply_ms'))} | "
                f"{_fmt_pct(low_attention.get('moe_apply_share_pct'))} |"
            ),
            (
                "| shared_body_total_only | shared direct | "
                f"{_fmt(low_shared.get('shared_direct_ms'))} | "
                f"{_fmt_pct(low_shared.get('shared_direct_share_pct'))} |"
            ),
            (
                "| shared_body_total_only | MoE apply | "
                f"{_fmt(low_shared.get('moe_apply_ms'))} | "
                f"{_fmt_pct(low_shared.get('moe_apply_share_pct'))} |"
            ),
            (
                "| engine_light | execute_model - model_forward | "
                f"{_fmt(low_engine.get('execute_model_minus_model_forward_ms'))} | "
                f"{_fmt_pct(low_engine.get('execute_model_minus_model_forward_share_pct'))} |"
            ),
            (
                "| engine_light | generate - execute_model | "
                f"{_fmt(low_engine.get('generate_minus_execute_model_ms'))} | "
                f"{_fmt_pct(low_engine.get('generate_minus_execute_model_share_pct'))} |"
            ),
            (
                "| engine_light | sample_tokens | "
                f"{_fmt(low_engine.get('sample_tokens_ms'))} | "
                f"{_fmt_pct(low_engine.get('sample_tokens_share_pct'))} |"
            ),
            "",
            "## Next Targets",
            "",
        ]
    )
    for target in summary["next_targets"]:
        lines.append(
            f"- `{target['target']}`: {target['status']}. {target['reason']}"
        )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-json", type=Path)
    parser.add_argument("--diagnostic-breakdown", type=Path)
    parser.add_argument("--attention-core-breakdown", type=Path)
    parser.add_argument("--decoder-layer-breakdown", type=Path)
    parser.add_argument("--shared-expert-breakdown", type=Path)
    parser.add_argument("--attention-total-breakdown", type=Path)
    parser.add_argument("--shared-body-total-breakdown", type=Path)
    parser.add_argument("--engine-breakdown", type=Path)
    parser.add_argument(
        "--diagnostic-mode",
        choices=("diagnostic_light", "diagnostic_coarse_breakdown"),
        help=(
            "Explicitly label diagnostic_breakdown when results_json does not "
            "contain a diagnostic mode row."
        ),
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()

    summary = build_summary(
        results_json=args.results_json,
        diagnostic_breakdown=args.diagnostic_breakdown,
        attention_core_breakdown=args.attention_core_breakdown,
        decoder_layer_breakdown=args.decoder_layer_breakdown,
        shared_expert_breakdown=args.shared_expert_breakdown,
        attention_total_breakdown=args.attention_total_breakdown,
        shared_body_total_breakdown=args.shared_body_total_breakdown,
        engine_breakdown=args.engine_breakdown,
        diagnostic_mode_override=args.diagnostic_mode,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(summary, args.output_md)


if __name__ == "__main__":
    main()
