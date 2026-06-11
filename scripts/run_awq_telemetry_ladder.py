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


_MODE_RESERVED_KEYS = {
    "env",
    "unset_env",
    "trace_overrides",
    "runtime_shadow_enabled",
}


MODES: dict[str, dict[str, Any]] = {
    "production_batch": {
        "runtime_shadow_enabled": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "emit_wna16_kernel_timing": False,
        "trace_overrides": {
            "capture_router_topk": False,
            "capture_router_scores": False,
            "use_router_logits_recorder": False,
            "allow_missing_router_trace": True,
            "vllm_overrides": {
                "use_router_logits_recorder": False,
                "enable_return_routed_experts": False,
                "max_num_seqs": 32,
                "engine_chunk_size": 32,
                "enforce_eager": True,
            },
        },
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
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
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_address_capacity_gate_path": None,
        "premap_consumer_require_readonly_gate": False,
        "premap_consumer_readonly_gate_path": None,
        "premap_descriptor_prep_execution_mode": "off",
        "premap_kernel_arg_handoff_live_enabled": False,
        "premap_kernel_arg_handoff_live_consumer_connected": False,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
        "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": False,
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
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_address_capacity_gate_path": None,
        "premap_consumer_require_readonly_gate": False,
        "premap_consumer_readonly_gate_path": None,
        "premap_descriptor_prep_execution_mode": "off",
        "premap_kernel_arg_handoff_live_enabled": False,
        "premap_kernel_arg_handoff_live_consumer_connected": False,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
        "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": False,
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
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_address_capacity_gate_path": None,
        "premap_consumer_require_readonly_gate": False,
        "premap_consumer_readonly_gate_path": None,
        "premap_descriptor_prep_execution_mode": "off",
        "premap_kernel_arg_handoff_live_enabled": False,
        "premap_kernel_arg_handoff_live_consumer_connected": False,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
        "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": False,
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
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_address_capacity_gate_path": None,
        "premap_consumer_require_readonly_gate": False,
        "premap_consumer_readonly_gate_path": None,
        "premap_descriptor_prep_execution_mode": "off",
        "premap_kernel_arg_handoff_live_enabled": False,
        "premap_kernel_arg_handoff_live_consumer_connected": False,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
        "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": False,
        "env": {"VLLM_DISABLE_SHARED_EXPERTS_STREAM": "1"},
    },
    "premap_real_kernel_arg_mutation_observed_canary": {
        # Endpoint canary benchmark for the already-gated WNA16 launch-argument
        # package path.  This is intentionally not a production default: it keeps
        # the minimal current-router premap stream needed to build the prepared
        # descriptor/address table, then passes identity WNA16 launch values
        # through the live mutation package.
        "record_router_topk": True,
        "emit_premap_summaries": True,
        "emit_premap_address_manager_counters": True,
        "premap_summary_sample_period": 32,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_mapping_source": "fused_moe_prepare_expert_assignment",
        "premap_consumer_resolve_real_handles": True,
        "premap_consumer_mapping_sample_period": 32,
        "premap_address_capacity_gate_path": (
            "configs/runtime/"
            "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
        ),
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "real_kernel_arg_mutation_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_real_kernel_arg_mutation_observed_canary"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_policy": "premap_only_with_consumer_mapping_noop",
        "premap_source": "current_router_topk_premap_shadow",
        "premap_descriptor_bytes": 4096,
        "premap_priority": 2,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_single_field_replacement_live_observed_canary": {
        # Same live handoff as above, plus the current identity-compatible
        # one-field replacement canary.  It replaces B_scale with the original
        # WNA16 argument value through the live package; prepared handle-table
        # candidates remain dry-run only.
        "record_router_topk": True,
        "emit_premap_summaries": True,
        "emit_premap_address_manager_counters": True,
        "premap_summary_sample_period": 32,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_mapping_source": "fused_moe_prepare_expert_assignment",
        "premap_consumer_resolve_real_handles": True,
        "premap_consumer_mapping_sample_period": 32,
        "premap_address_capacity_gate_path": (
            "configs/runtime/"
            "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
        ),
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_single_field_replacement_live_observed_canary"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "premap_policy": "premap_only_with_consumer_mapping_noop",
        "premap_source": "current_router_topk_premap_shadow",
        "premap_descriptor_bytes": 4096,
        "premap_priority": 2,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_single_field_replacement_live_minimal": {
        # Production-compatible TPOT probe for the live handoff path.  It keeps
        # only the internal router-topk capture required to build the premap
        # descriptor/address table and live launch package; it does not persist
        # router_topk/oracle fields or consumer-mapping rows.
        "record_router_topk": False,
        "capture_router_topk": True,
        "emit_premap_summaries": True,
        "emit_premap_address_manager_counters": True,
        "premap_summary_sample_period": 1_000_000_000,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_mapping_source": "fused_moe_prepare_expert_assignment",
        "premap_consumer_resolve_real_handles": True,
        "premap_consumer_mapping_sample_period": 1_000_000_000,
        "premap_address_capacity_gate_path": (
            "configs/runtime/"
            "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
        ),
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_single_field_replacement_live_minimal"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "premap_policy": "premap_only_with_consumer_mapping_noop",
        "premap_source": "current_router_topk_premap_shadow",
        "premap_descriptor_bytes": 4096,
        "premap_priority": 2,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_single_field_replacement_live_minimal_identity_envelope": {
        # Production-compatible TPOT probe for the identity single-field live
        # handoff.  This path relies on the strict lab gate artifact for typed
        # descriptor evidence, but does not rebuild the descriptor table on
        # every WNA16 launch.  It only installs a minimal live envelope after
        # the current address/handle readonly parity check passes.
        "record_router_topk": False,
        "capture_router_topk": True,
        "emit_premap_summaries": True,
        "emit_premap_address_manager_counters": True,
        "premap_summary_sample_period": 1_000_000_000,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_mapping_source": "fused_moe_prepare_expert_assignment",
        "premap_consumer_resolve_real_handles": True,
        "premap_consumer_mapping_sample_period": 1_000_000_000,
        "premap_address_capacity_gate_path": (
            "configs/runtime/"
            "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
        ),
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_single_field_replacement_live_minimal_identity_envelope"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "premap_policy": "premap_only_with_consumer_mapping_noop",
        "premap_source": "current_router_topk_premap_shadow",
        "premap_descriptor_bytes": 4096,
        "premap_priority": 2,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_single_field_replacement_live_producer_identity_envelope": {
        # Lower-overhead live participation probe.  The producer/prelaunch
        # adapter installs the minimal identity envelope directly after expert
        # assignment, and the WNA16 wrapper consumes it without running the
        # per-launch premap manager lookup/descriptor-table path.
        "record_router_topk": False,
        "capture_router_topk": False,
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "off",
        "premap_consumer_resolve_real_handles": False,
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_single_field_replacement_live_producer_identity_envelope"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_single_field_replacement_live_producer_identity_envelope_counter_off": {
        # Benchmark-only lower bound for the producer-side live handoff path.
        # It keeps the same live identity envelope and WNA16 pass-through
        # behavior as the production-compatible producer mode, but disables
        # per-launch diagnostic counters so TPOT measures the participation
        # path rather than bookkeeping.
        "record_router_topk": False,
        "capture_router_topk": False,
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "off",
        "premap_consumer_resolve_real_handles": False,
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_single_field_replacement_live_"
            "producer_identity_envelope_counter_off"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_live_counter_mode": "off",
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "emit_descriptor_layer_timing": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_live_future_wna16_typed_slot_envelope_counter_off": {
        # Future-kernel lower bound: the prelaunch producer installs a typed-slot
        # envelope that is ABI-adjacent to the independent WNA16-side typed
        # consumer variant, while the current WNA16 launch args remain original
        # pass-through values.  This is the benchmark mode for the future
        # typed-slot path before wiring a new WNA16 kernel variant.
        "record_router_topk": False,
        "capture_router_topk": False,
        "emit_premap_summaries": False,
        "emit_premap_address_manager_counters": False,
        "emit_premap_consumer_mapping": False,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "off",
        "premap_consumer_resolve_real_handles": False,
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_live_future_wna16_typed_slot_envelope_counter_off"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled": (
            True
        ),
        "premap_kernel_arg_handoff_live_counter_mode": "off",
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "emit_descriptor_layer_timing": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_live_future_wna16_typed_slot_kernel_variant_counter_off": {
        # True typed-slot kernel canary: the live package still preserves the
        # original WNA16 compute args, but the launched WNA16 variant receives
        # an independent future typed-slot ABI and reads prepared descriptor /
        # address table columns in-kernel.  This is not a speedup claim; it
        # measures the real variant boundary without passing a typed table as
        # an existing WNA16 tensor argument.
        "record_router_topk": False,
        "capture_router_topk": True,
        "emit_premap_summaries": True,
        "emit_premap_address_manager_counters": True,
        "premap_summary_sample_period": 1_000_000_000,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_mapping_source": "fused_moe_prepare_expert_assignment",
        "premap_consumer_resolve_real_handles": True,
        "premap_consumer_mapping_sample_period": 1_000_000_000,
        "premap_address_capacity_gate_path": (
            "configs/runtime/"
            "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
        ),
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "single_field_replacement_live_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled": (
            True
        ),
        "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": (
            True
        ),
        "premap_kernel_arg_handoff_prepared_table_materialization_mode": (
            "producer_native_adapter"
        ),
        "premap_kernel_arg_handoff_live_counter_mode": "off",
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
        "premap_policy": "premap_only_with_consumer_mapping_noop",
        "premap_source": "current_router_topk_premap_shadow",
        "premap_descriptor_bytes": 4096,
        "premap_priority": 2,
        "emit_descriptor_layer_timing": False,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
    },
    "premap_single_field_replacement_live_prepared_handle_table_canary": {
        # Explicit semantic-candidate canary.  It builds the real prepared
        # descriptor/address handle table and attempts a one-field live
        # replacement from that table.  The current WNA16 ABI expects tensor
        # launch args, while prepared handles are typed schema identities, so
        # this mode is expected to fall back unless the field is type-compatible.
        # It is intentionally diagnostic and default-off.
        "record_router_topk": False,
        "capture_router_topk": True,
        "emit_premap_summaries": True,
        "emit_premap_address_manager_counters": True,
        "premap_summary_sample_period": 1_000_000_000,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_mapping_source": "fused_moe_prepare_expert_assignment",
        "premap_consumer_resolve_real_handles": True,
        "premap_consumer_mapping_sample_period": 1_000_000_000,
        "premap_address_capacity_gate_path": (
            "configs/runtime/"
            "premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
        ),
        "premap_consumer_require_readonly_gate": True,
        "premap_consumer_readonly_gate_path": (
            "configs/runtime/"
            "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_"
            "prepared_table_live_fallback_canary.yaml"
        ),
        "premap_descriptor_prep_execution_mode": (
            "readonly_descriptor_address_object"
        ),
        "premap_risky_trace_canary": True,
        "premap_risky_trace_canary_scope": (
            "benchmark_premap_single_field_replacement_live_prepared_handle_table_canary"
        ),
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": True,
        "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "prepared_handle_table"
        ),
        "premap_policy": "premap_only_with_consumer_mapping_noop",
        "premap_source": "current_router_topk_premap_shadow",
        "premap_descriptor_bytes": 4096,
        "premap_priority": 2,
        "emit_decoder_layer_timing": False,
        "emit_decoder_component_timing": False,
        "emit_moe_substage_timing": False,
        "decoder_source_timing_mode": "off",
        "moe_source_timing_mode": "off",
        "emit_wna16_kernel_timing": False,
        "wna16_kernel_timing_mode": "host",
        "emit_summaries": True,
        "emit_outcomes": False,
        "outcome_logging_mode": "off",
        "emit_descriptor_order_summaries": False,
        "emit_transition_summaries": False,
        "unset_env": ["VLLM_DISABLE_SHARED_EXPERTS_STREAM"],
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


_PRODUCTION_BATCH_TRACE_OVERRIDES = dict(MODES["production_batch"]["trace_overrides"])
_PRODUCTION_BATCH_TRACE_OVERRIDES["vllm_overrides"] = dict(
    MODES["production_batch"]["trace_overrides"]["vllm_overrides"]
)

MODES["production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off"] = {
    **MODES["premap_live_future_wna16_typed_slot_envelope_counter_off"],
    # Batch-compatible live participation probe.  It installs the MoE/WNA16
    # prelaunch live config without making it the active router recorder, so
    # router top-k rows and runtime shadow JSONL stay disabled while the WNA16
    # pass-through typed-slot envelope can participate in the true batched
    # vLLM path.
    "runtime_shadow_enabled": False,
    "trace_overrides": {
        **_PRODUCTION_BATCH_TRACE_OVERRIDES,
        "allow_premap_live_config_without_router_recorder": True,
    },
    "emit_summaries": False,
    "emit_outcomes": False,
    "outcome_logging_mode": "off",
}


MODES["production_batch_premap_live_future_wna16_typed_slot_envelope_detailed"] = {
    **MODES["production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off"],
    # Same no-recorder batched live path, but with live mutation counters on so
    # performance_summary can prove package construction/consumption.  Use this
    # for semantic smoke, not final TPOT.
    "premap_kernel_arg_handoff_live_counter_mode": "detailed",
}

MODES[
    "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off"
] = {
    **MODES["production_batch_premap_live_future_wna16_typed_slot_envelope_counter_off"],
    # Native-assignment handoff lower bound: the prelaunch producer attaches the
    # GPU-side sorted_token_ids/expert_ids/num_tokens_post_padded tensor refs to
    # the future typed-slot package.  The WNA16 wrapper only verifies that the
    # package sees the same launch tensors; no CPU extraction, address-manager
    # mapping, prepared table, payload movement, or kernel-arg replacement is
    # enabled.
    "premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled": True,
    "premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
    "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": (
        False
    ),
}

MODES[
    "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_detailed"
] = {
    **MODES[
        "production_batch_premap_live_future_wna16_typed_slot_gpu_assignment_envelope_counter_off"
    ],
    "premap_kernel_arg_handoff_live_counter_mode": "detailed",
}

MODES[
    "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
] = {
    **MODES["premap_live_future_wna16_typed_slot_kernel_variant_counter_off"],
    # Batch-compatible prepared-table typed-slot canary.  This keeps the true
    # no-router-recorder production batch envelope, but still enables the
    # no-row prelaunch consumer mapping path so the future WNA16 typed-slot
    # identity variant can receive real prepared descriptor/address columns.
    "runtime_shadow_enabled": False,
    "trace_overrides": {
        **_PRODUCTION_BATCH_TRACE_OVERRIDES,
        "allow_premap_live_config_without_router_recorder": True,
    },
    "record_router_topk": False,
    "capture_router_topk": False,
    "emit_premap_summaries": False,
    "emit_premap_consumer_mapping": True,
    "premap_consumer_mapping_emit_rows": False,
    "emit_summaries": False,
    "emit_outcomes": False,
    "outcome_logging_mode": "off",
}


MODES[
    "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_detailed"
] = {
    **MODES[
        "production_batch_premap_live_future_wna16_typed_slot_kernel_variant_counter_off"
    ],
    # Same batch-compatible prepared-table path, with live counters enabled for
    # a semantic smoke proving prepared columns were consumed by the variant.
    "premap_kernel_arg_handoff_live_counter_mode": "detailed",
}

MODES["premap_single_field_replacement_live_prepared_alias_adapter"] = {
    **MODES["premap_single_field_replacement_live_prepared_handle_table_canary"],
    # Prepared-handle-table compatibility probe.  The prepared table must
    # resolve the requested field, but the current WNA16 ABI still receives the
    # original tensor arg alias.  This isolates the overhead of prepared-table
    # selection/materialization without pretending that handle tokens are tensor
    # kernel args.
    "premap_risky_trace_canary_scope": (
        "benchmark_premap_single_field_replacement_live_prepared_alias_adapter"
    ),
    "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": False,
    "premap_kernel_arg_handoff_prepared_table_materialization_mode": (
        "original_kernel_arg_alias_after_prepared_handle_check"
    ),
}


MODES["production_batch_premap_live_prepared_alias_adapter_counter_off"] = {
    **MODES["premap_single_field_replacement_live_prepared_alias_adapter"],
    # Production-batch prepared-table lower bound.  It constructs and checks the
    # prepared descriptor/address table from the no-row prelaunch mapping path,
    # but aliases the original WNA16 tensor argument after the handle check
    # instead of launching the slow independent typed-slot canary kernel.
    "runtime_shadow_enabled": False,
    "trace_overrides": {
        **_PRODUCTION_BATCH_TRACE_OVERRIDES,
        "allow_premap_live_config_without_router_recorder": True,
    },
    "record_router_topk": False,
    "capture_router_topk": False,
    "emit_premap_summaries": False,
    "emit_premap_consumer_mapping": True,
    "premap_consumer_mapping_emit_rows": False,
    "emit_summaries": False,
    "emit_outcomes": False,
    "outcome_logging_mode": "off",
    "premap_kernel_arg_handoff_live_counter_mode": "off",
}


MODES["production_batch_premap_live_prepared_alias_adapter_detailed"] = {
    **MODES["production_batch_premap_live_prepared_alias_adapter_counter_off"],
    # Same original-WNA16 prepared-table alias path with counters enabled for
    # semantic smoke.
    "premap_kernel_arg_handoff_live_counter_mode": "detailed",
}


MODES["production_batch_premap_prelaunch_mapping_only_counter_off"] = {
    **MODES["production_batch"],
    # Attribution-only lower bound for the prepared-table slowdown.  It enables
    # the no-row fused-MoE prelaunch mapping path and address-manager prepare,
    # but disables real-handle resolution, descriptor prep, live package
    # construction, and all shadow rows.  This isolates CPU expert extraction
    # plus address-manager staging from the heavier prepared-table path.
    "runtime_shadow_enabled": False,
    "trace_overrides": {
        **_PRODUCTION_BATCH_TRACE_OVERRIDES,
        "allow_premap_live_config_without_router_recorder": True,
    },
    "record_router_topk": False,
    "capture_router_topk": False,
    "emit_premap_summaries": False,
    "emit_premap_address_manager_counters": True,
    "emit_premap_consumer_mapping": True,
    "premap_consumer_mapping_emit_rows": False,
    "premap_consumer_mapping_mode": "noop_assertion",
    "premap_consumer_resolve_real_handles": False,
    # This mode is not a lab precondition.  The readonly gates intentionally
    # require real handles / descriptor-prep / live-toggle evidence, while this
    # attribution pass measures the cheaper mapping/address-manager lower bound.
    "premap_consumer_require_readonly_gate": False,
    "premap_consumer_readonly_gate_path": None,
    "premap_descriptor_prep_execution_mode": "off",
    "premap_kernel_arg_handoff_live_enabled": False,
    "premap_kernel_arg_handoff_live_consumer_connected": False,
    "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
    "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
    "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": False,
    "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled": (
        False
    ),
    "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": (
        False
    ),
    "premap_kernel_arg_handoff_live_counter_mode": "off",
    "emit_summaries": False,
    "emit_outcomes": False,
    "outcome_logging_mode": "off",
}


MODES["premap_live_future_wna16_typed_slot_kernel_variant_prepared_table_strict"] = {
    **MODES["premap_live_future_wna16_typed_slot_kernel_variant_counter_off"],
    # Strict gate mode for real prepared-table typed-slot columns.  It keeps the
    # same kernel path as the counter-off benchmark mode but enables live
    # mutation counters so performance_summary can prove launch/fallback counts.
    "premap_risky_trace_canary_scope": (
        "benchmark_premap_live_future_wna16_typed_slot_kernel_variant_prepared_table_strict"
    ),
    "premap_kernel_arg_handoff_live_counter_mode": "detailed",
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
    trace.update(dict(MODES[mode].get("trace_overrides", {})))
    shadow = trace.setdefault("runtime_shadow", {})
    shadow.update(
        {
            key: value
            for key, value in MODES[mode].items()
            if key not in _MODE_RESERVED_KEYS
        }
    )
    shadow_enabled = bool(MODES[mode].get("runtime_shadow_enabled", True))
    shadow["enabled"] = shadow_enabled
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

    baseline = None
    for baseline_mode in ("production_like", "production_batch"):
        baseline = next(
            (
                row
                for row in results
                if row["mode"] == baseline_mode
                and row.get("generate_seconds_per_requested_output_token")
            ),
            None,
        )
        if baseline is not None:
            break
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
