#!/usr/bin/env python3
"""Run AWQ/vLLM telemetry overhead ladder on a fixed split."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


_MODE_RESERVED_KEYS = {"env", "unset_env"}


MODES: dict[str, dict[str, Any]] = {
    "production_like": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": False,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "production_like_no_packed_recurrent": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": False,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "env": {"VLLM_ENABLE_FLA_PACKED_RECURRENT_DECODE": "0"},
    },
    "production_like_force_shared_aux": {
        "record_router_topk": False,
        "shared_experts_force_aux_stream": True,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": False,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "production_like_disable_shared_stream": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": False,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "env": {"VLLM_DISABLE_SHARED_EXPERTS_STREAM": "1"},
    },
    "diagnostic_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "decoder_layer_only": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "emit_engine_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "engine_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "emit_engine_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "diagnostic_coarse_breakdown": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "emit_engine_timing": True,
        "decoder_source_timing_mode": "off",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "shared_body",
        "moe_substage_logging_mode": "aggregate",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "diagnostic_light_force_shared_aux": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "shared_experts_force_aux_stream": True,
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "decoder_coarse_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "qwen3_5",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "shared",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "decoder_component_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "shared",
        "moe_substage_logging_mode": "aggregate",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "decoder_component_sampled_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "shared",
        "moe_substage_logging_mode": "sampled_aggregate",
        "moe_substage_sample_period": 8,
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "decoder_shared_body_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "shared_body",
        "moe_substage_logging_mode": "aggregate",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "shared_body_total_only": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "shared_body",
        "moe_substage_logging_mode": "aggregate",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "decoder_shared_body_regions_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "shared_body_regions",
        "moe_substage_logging_mode": "aggregate",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "shared_body_regions_no_write": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "shared_body_regions",
        "moe_substage_logging_mode": "aggregate_no_write",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "diagnostic_full": {
        "record_router_topk": True,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "full",
        "emit_wna16_kernel_timing": True,
        "wna16_kernel_timing_mode": "gpu_event",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "source_none": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "source_outer": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "outer",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "shared_expert_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "shared",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "shared_gate_ablation": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "shared",
        "shared_expert_output_gate_ablation": "unity",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "shared_gate_inplace": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "shared",
        "shared_expert_output_gate_postprocess": "inplace",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "shared_gate_fused": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "shared",
        "shared_expert_output_gate_postprocess": "fused_triton",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "shared_gate_fused_minimal": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "shared_expert_output_gate_postprocess": "fused_triton",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": False,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "shared_gate_inplace_minimal": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "shared_expert_output_gate_postprocess": "inplace",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": False,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "source_outer_impl": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "outer_impl",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "source_outer_impl_enqueue": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "outer_impl_enqueue",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "source_full": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "full",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "decoder_source": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "qwen3_5",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_source": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "attention_leaf",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_total_only": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "attention_core",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_deep": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "attention_core_deep",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_handoff_light": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": True,
        "decoder_source_timing_mode": "attention_core_handoff_light",
        "decoder_component_logging_mode": "rows",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_handoff_aggregate": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "attention_core_handoff_light",
        "decoder_component_logging_mode": "attention_handoff_aggregate",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_handoff_aggregate_no_write": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "attention_core_handoff_light",
        "decoder_component_logging_mode": "attention_handoff_aggregate_no_write",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_handoff_counter_only": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "attention_core_handoff_light",
        "decoder_component_logging_mode": "attention_handoff_counter_only",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
    "attention_core_handoff_counter_only_no_write": {
        "record_router_topk": False,
        "emit_decoder_layer_timing": True,
        "emit_decoder_component_timing": True,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "attention_core_handoff_light",
        "decoder_component_logging_mode": "attention_handoff_counter_only_no_write",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
    },
}


def _resolve_trace_split(
    *,
    trace: dict[str, Any],
    base_config: Path,
    max_samples: int | None,
    max_tokens: int | None,
    start_sample: int | None,
) -> dict[str, int]:
    resolved: dict[str, int] = {}
    for key, override in (
        ("max_samples", max_samples),
        ("max_tokens", max_tokens),
        ("start_sample", start_sample),
    ):
        if override is None:
            if key not in trace:
                raise ValueError(
                    f"{base_config} does not define trace.{key}; pass --{key.replace('_', '-')}"
                )
            resolved[key] = int(trace[key])
        else:
            resolved[key] = int(override)
    return resolved


def _validate_trace_split_metadata(
    *,
    trace: dict[str, Any],
    split: dict[str, int],
    base_config: Path,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "expected_range_checked": False,
        "split_source_match_checked": False,
        "metadata_checks_passed": True,
    }
    expected_start = trace.get("expected_sample_start")
    expected_end = trace.get("expected_sample_end")
    if expected_start is not None or expected_end is not None:
        if expected_start is None or expected_end is None:
            raise ValueError(
                f"{base_config} must define both trace.expected_sample_start and "
                "trace.expected_sample_end when either is present"
            )
        parsed_start = int(expected_start)
        parsed_end = int(expected_end)
        actual_start = int(split["start_sample"])
        actual_end = actual_start + int(split["max_samples"]) - 1
        report.update(
            {
                "expected_range_checked": True,
                "expected_sample_start": parsed_start,
                "expected_sample_end": parsed_end,
                "effective_sample_start": actual_start,
                "effective_sample_end": actual_end,
            }
        )
        if actual_start != parsed_start or actual_end != parsed_end:
            raise ValueError(
                f"{base_config} split metadata mismatch: expected sample range "
                f"{parsed_start}..{parsed_end}, got {actual_start}..{actual_end}"
            )
    split_source = trace.get("split_source")
    token_source = trace.get("token_source_manifest")
    if split_source is not None and token_source is not None:
        split_source_paths = _normalize_compare_path_candidates(
            split_source,
            base_config=base_config,
        )
        token_source_paths = _normalize_compare_path_candidates(
            token_source,
            base_config=base_config,
        )
        shared_paths = split_source_paths.intersection(token_source_paths)
        report.update(
            {
                "split_source_match_checked": True,
                "split_source_resolved_candidates": sorted(split_source_paths),
                "token_source_manifest_resolved_candidates": sorted(token_source_paths),
                "split_source_resolved_match": _choose_resolved_match(shared_paths),
            }
        )
        if split_source_paths.isdisjoint(token_source_paths):
            raise ValueError(
                f"{base_config} split_source does not match token_source_manifest: "
                f"{split_source!r} != {token_source!r}; normalized "
                f"{sorted(split_source_paths)!r} != {sorted(token_source_paths)!r}"
            )
    return report


def _choose_resolved_match(paths: set[str]) -> str | None:
    if not paths:
        return None
    existing = sorted(path for path in paths if Path(path).exists())
    if existing:
        return existing[0]
    return sorted(paths)[0]


def _normalize_compare_path_candidates(value: Any, *, base_config: Path) -> set[str]:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return {str(path.resolve(strict=False))}
    repo_root = Path(__file__).resolve().parents[1]
    bases = (Path.cwd(), repo_root, base_config.parent)
    return {
        str((base / path).resolve(strict=False))
        for base in bases
    }


def _write_mode_config(
    *,
    base_config: Path,
    output_root: Path,
    mode: str,
    repeat: int,
    max_samples: int | None,
    max_tokens: int | None,
    start_sample: int | None,
) -> Path:
    cfg = yaml.safe_load(base_config.read_text())
    output_dir = output_root / mode / f"repeat_{repeat:02d}"
    cfg["output_dir"] = str(output_dir)
    trace = cfg.setdefault("trace", {})
    split = _resolve_trace_split(
        trace=trace,
        base_config=base_config,
        max_samples=max_samples,
        max_tokens=max_tokens,
        start_sample=start_sample,
    )
    _validate_trace_split_metadata(trace=trace, split=split, base_config=base_config)
    trace.update(split)
    shadow = trace.setdefault("runtime_shadow", {})
    shadow.update(
        {
            key: value
            for key, value in MODES[mode].items()
            if key not in _MODE_RESERVED_KEYS
        }
    )
    shadow["enabled"] = True
    shadow["output_path"] = str(output_dir / "runtime_shadow.jsonl")
    shadow["overwrite"] = True
    shadow["writer_mode"] = "jsonl_batched"
    shadow["flush_every"] = 100000
    shadow["max_pending"] = 10000
    config_path = output_root / "trace_configs" / mode / f"repeat_{repeat:02d}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return config_path


def _read_perf(trace_dir: Path) -> dict[str, Any]:
    path = trace_dir / "performance_summary.json"
    if not path.exists():
        return {"performance_summary_missing": True}
    data = json.loads(path.read_text())
    return {
        "generate_seconds_per_requested_output_token": data.get(
            "generate_seconds_per_requested_output_token"
        ),
        "generate_wall_seconds": data.get("generate_wall_seconds"),
        "total_trace_wall_seconds": data.get("total_trace_wall_seconds"),
        "requested_output_token_count": data.get("requested_output_token_count"),
        "sample_count": data.get("sample_count"),
    }


def _trace_command(conda_env: str, config_path: Path) -> list[str]:
    active_env = os.environ.get("CONDA_DEFAULT_ENV")
    active_prefix = os.environ.get("CONDA_PREFIX")
    if active_env == conda_env or (
        active_prefix is not None and Path(active_prefix).name == conda_env
    ):
        return [sys.executable, "scripts/trace_router_mtp.py", str(config_path)]
    return [
        "conda",
        "run",
        "-n",
        conda_env,
        "python",
        "scripts/trace_router_mtp.py",
        str(config_path),
    ]


def _prepend_pythonpath(env: dict[str, str], path: str) -> None:
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = path if not existing else f"{path}{os.pathsep}{existing}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-config",
        type=Path,
        default=Path(
            "configs/trace/"
            "router_mtp_trace_aya_dataset_awq_vllm_descriptor_order_attr_"
            "no_order_gpu1_decode_heldout128_gen8_diagnostic_off.yaml"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/reports/awq_telemetry_ladder/gpu1"),
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Override trace.max_samples. Defaults to the base config value.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Override trace.max_tokens. Defaults to the base config value.",
    )
    parser.add_argument(
        "--start-sample",
        type=int,
        default=None,
        help="Override trace.start_sample. Defaults to the base config value.",
    )
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--conda-env", default="TRY")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--modes",
        nargs="*",
        choices=tuple(MODES),
        default=list(MODES),
    )
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    base_trace = yaml.safe_load(args.base_config.read_text()).setdefault("trace", {})
    effective_split = _resolve_trace_split(
        trace=base_trace,
        base_config=args.base_config,
        max_samples=args.max_samples,
        max_tokens=args.max_tokens,
        start_sample=args.start_sample,
    )
    split_override_active = any(
        value is not None
        for value in (args.start_sample, args.max_samples, args.max_tokens)
    )
    split_metadata_report = _validate_trace_split_metadata(
        trace=base_trace,
        split=effective_split,
        base_config=args.base_config,
    )

    args.output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    exit_code = 0
    for mode in args.modes:
        for repeat in range(int(args.repeats)):
            config_path = _write_mode_config(
                base_config=args.base_config,
                output_root=args.output_root,
                mode=mode,
                repeat=repeat,
                max_samples=args.max_samples,
                max_tokens=args.max_tokens,
                start_sample=args.start_sample,
            )
            env = os.environ.copy()
            env["HIP_VISIBLE_DEVICES"] = str(args.gpu)
            for key in MODES[mode].get("unset_env", ()):
                env.pop(str(key), None)
            for key, value in dict(MODES[mode].get("env", {})).items():
                env[str(key)] = str(value)
            _prepend_pythonpath(env, "src")
            command = _trace_command(args.conda_env, config_path)
            print(f"[telemetry-ladder] mode={mode} repeat={repeat}", flush=True)
            proc = subprocess.run(
                command,
                cwd=Path.cwd(),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            log_path = args.output_root / "logs" / mode / f"repeat_{repeat:02d}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(proc.stdout)
            trace_dir = args.output_root / mode / f"repeat_{repeat:02d}"
            row = {
                "mode": mode,
                "repeat": repeat,
                "returncode": proc.returncode,
                "trace_config": str(config_path),
                "trace_dir": str(trace_dir),
                "log_path": str(log_path),
                "effective_start_sample": int(effective_split["start_sample"]),
                "effective_max_samples": int(effective_split["max_samples"]),
                "effective_max_tokens": int(effective_split["max_tokens"]),
                "effective_sample_end": int(effective_split["start_sample"])
                + int(effective_split["max_samples"])
                - 1,
                "split_override_active": bool(split_override_active),
                **split_metadata_report,
                "split_id": base_trace.get("split_id"),
                "split_source": base_trace.get("split_source"),
                "token_source_manifest": base_trace.get("token_source_manifest"),
                "expected_sample_start": base_trace.get("expected_sample_start"),
                "expected_sample_end": base_trace.get("expected_sample_end"),
                **_read_perf(trace_dir),
            }
            results.append(row)
            (args.output_root / "results.json").write_text(
                json.dumps(results, indent=2) + "\n"
            )
            print(json.dumps(row, indent=2), flush=True)
            if proc.returncode != 0 and not args.continue_on_error:
                exit_code = proc.returncode
                break
        if exit_code != 0:
            break

    baseline = next(
        (
            row
            for row in results
            if row["mode"] == "production_like"
            and row.get("generate_seconds_per_requested_output_token")
        ),
        None,
    )
    if baseline is not None:
        base_tpot = float(baseline["generate_seconds_per_requested_output_token"])
        for row in results:
            tpot = row.get("generate_seconds_per_requested_output_token")
            if tpot:
                row["tpot_overhead_vs_production_like"] = float(tpot) / base_tpot - 1.0

    (args.output_root / "results.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
    lines = [
        "# AWQ/vLLM Telemetry Ladder",
        "",
        f"base_config: `{args.base_config}`",
        f"max_samples: `{effective_split['max_samples']}`",
        f"max_tokens: `{effective_split['max_tokens']}`",
        f"start_sample: `{effective_split['start_sample']}`",
        "",
        "| mode | repeat | TPOT | overhead_vs_production_like | generate_s | returncode |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        tpot = row.get("generate_seconds_per_requested_output_token")
        overhead = row.get("tpot_overhead_vs_production_like")
        generate = row.get("generate_wall_seconds")
        lines.append(
            "| {mode} | {repeat} | {tpot} | {overhead} | {generate} | {returncode} |".format(
                mode=row["mode"],
                repeat=row["repeat"],
                tpot=f"{float(tpot):.6f}" if tpot else "",
                overhead=f"{100.0 * float(overhead):.2f}%" if overhead is not None else "",
                generate=f"{float(generate):.3f}" if generate else "",
                returncode=row["returncode"],
            )
        )
    (args.output_root / "summary.md").write_text("\n".join(lines) + "\n")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
