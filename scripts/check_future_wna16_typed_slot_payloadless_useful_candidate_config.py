#!/usr/bin/env python3
"""Validate the production-compatible payloadless useful candidate trace config.

The candidate config is allowed to create a lightweight premap live config
object without enabling the heavy router recorder.  It must remain payloadless:
no runtime shadow rows, no payload cache demand, no kernel argument pass, and no
current WNA16 argument mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TRACE_CONFIG = (
    REPO_ROOT
    / "configs"
    / "trace"
    / "router_mtp_trace_external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_payloadless_useful_candidate_graph.yaml"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_candidate_config_gate_dolly32_gen64_graph_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_candidate_config_gate"
GATE_NAME = "premap_future_wna16_typed_slot_payloadless_useful_candidate_config_gate_v1"
GATE_MODE = "production_compatible_live_config_without_router_recorder"
NEXT_RUNTIME_STAGE = "run_payloadless_useful_candidate_tpot_artifact"

TRACE_EXPECTED = {
    "capture_router_topk": False,
    "capture_router_scores": False,
    "use_router_logits_recorder": False,
    "allow_missing_router_trace": True,
    "allow_premap_live_config_without_router_recorder": True,
    "capture_native_mtp_router": False,
    "max_samples": 32,
    "max_length": 128,
    "max_tokens": 64,
}

SHADOW_EXPECTED = {
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
    "premap_consumer_require_readonly_gate": True,
    "premap_consumer_readonly_gate_live_config_only_no_rows": True,
    "premap_consumer_readonly_gate_path": (
        "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml"
    ),
    "premap_descriptor_prep_execution_mode": "readonly_descriptor_address_object",
    "premap_kernel_arg_handoff_live_counter_mode": "off",
    "premap_kernel_arg_handoff_live_enabled": True,
    "premap_kernel_arg_handoff_live_consumer_connected": True,
    "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
    "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
    "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": False,
    "premap_kernel_arg_handoff_single_field_replacement_live_enabled": False,
    "premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
    "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled": False,
    "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": False,
    "premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled": False,
    "premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled": False,
    "emit_premap_summaries": False,
    "emit_premap_address_manager_counters": False,
    "emit_premap_payload_cache_manager_counters": False,
    "emit_premap_consumer_mapping": False,
    "premap_consumer_mapping_emit_rows": False,
    "premap_consumer_resolve_real_handles": False,
    "premap_payload_cache_manager_demand_on_consumer": False,
    "premap_payload_cache_manager_emit_consumer_rows": False,
    "premap_native_typed_consumer_input_export_enabled": False,
    "premap_payload_cache_producer_state_packet_export_enabled": False,
    "descriptor_order_mapping_assertion_mode": "off",
    "descriptor_order_prelaunch_assertion_mode": "off",
    "descriptor_order_emit_consumer_handle_events": False,
    "descriptor_order_reorder_mvp_enabled": False,
}


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _check_expected(
    mapping: dict[str, Any],
    expected: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    for key, expected_value in expected.items():
        if mapping.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")


def check_candidate_config(args: argparse.Namespace) -> dict[str, Any]:
    trace_config = _resolve(args.trace_config)
    output_json = _resolve(args.output_json)
    failures: list[str] = []
    try:
        config = _load_yaml(trace_config)
    except Exception as exc:
        config = {}
        failures.append(f"trace_config_load_failed:{exc.__class__.__name__}:{exc}")
    trace = config.get("trace") if isinstance(config.get("trace"), dict) else {}
    shadow = trace.get("runtime_shadow") if isinstance(trace.get("runtime_shadow"), dict) else {}
    if not isinstance(trace, dict) or not trace:
        failures.append("trace_section_missing")
    if not isinstance(shadow, dict) or not shadow:
        failures.append("runtime_shadow_section_missing")
    _check_expected(trace, TRACE_EXPECTED, failures, prefix="trace")
    _check_expected(shadow, SHADOW_EXPECTED, failures, prefix="runtime_shadow")
    if config.get("model") != "configs/model/qwen3_6_35b_a3b_awq_4bit_prod_batch32_graph.yaml":
        failures.append("model_config_mismatch")
    if config.get("data") != "configs/data/external_prompt_gate_dolly_128.yaml":
        failures.append("data_config_mismatch")
    split_id = trace.get("split_id")
    if split_id != "external_prompt_gate_dolly_32_gen64_payloadless_useful_candidate":
        failures.append("split_id_mismatch")
    output_dir = config.get("output_dir")
    if not isinstance(output_dir, str) or "payloadless_useful_candidate" not in output_dir:
        failures.append("output_dir_not_candidate")
    gate_path = shadow.get("premap_consumer_readonly_gate_path")
    gate_exists = False
    gate_passed = None
    gate_artifact_id = None
    if isinstance(gate_path, str) and gate_path:
        resolved_gate = _resolve(gate_path)
        gate_exists = resolved_gate.exists()
        if not gate_exists:
            failures.append("readonly_gate_path_missing")
        else:
            gate_payload = _load_yaml(resolved_gate)
            gate_passed = gate_payload.get("status") == "passed" or (
                isinstance(gate_payload.get("gate"), dict)
                and gate_payload["gate"].get("passed") is True
            )
            gate_artifact_id = gate_payload.get("artifact_id")
            contract = gate_payload.get("contract")
            if not isinstance(contract, dict):
                failures.append("readonly_gate_contract_missing")
            else:
                for key, expected in {
                    "payload_bytes_required": 0,
                    "kernel_arg_handoff_live_noop_integration_passed_to_kernel_required": False,
                    "kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_required": False,
                    "kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_required": False,
                }.items():
                    if contract.get(key) != expected:
                        failures.append(f"readonly_gate_{key}_mismatch")
            if not gate_passed:
                failures.append("readonly_gate_not_passed")

    passed = not failures
    result = {
        "artifact_kind": ARTIFACT_KIND,
        "gate_name": GATE_NAME,
        "gate_mode": GATE_MODE,
        "passed": passed,
        "failures": failures,
        "payloadless_useful_candidate_config_ready": passed,
        "trace_config": str(trace_config),
        "trace_config_sha256": _sha256(trace_config) if trace_config.exists() else None,
        "model": config.get("model"),
        "data": config.get("data"),
        "output_dir": output_dir,
        "split_id": split_id,
        "sample_count": trace.get("max_samples"),
        "max_tokens": trace.get("max_tokens"),
        "requested_output_token_count": (
            int(trace.get("max_samples", 0)) * int(trace.get("max_tokens", 0))
            if isinstance(trace.get("max_samples"), int)
            and isinstance(trace.get("max_tokens"), int)
            else None
        ),
        "live_config_without_router_recorder": bool(
            trace.get("allow_premap_live_config_without_router_recorder")
        ),
        "runtime_shadow_enabled": bool(shadow.get("enabled", False)),
        "record_router_topk": bool(shadow.get("record_router_topk", False)),
        "readonly_gate_path": gate_path,
        "readonly_gate_exists": gate_exists,
        "readonly_gate_passed": gate_passed,
        "readonly_gate_artifact_id": gate_artifact_id,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "next_runtime_stage": (
            NEXT_RUNTIME_STAGE if passed else "fix_payloadless_useful_candidate_config"
        ),
    }
    _write_json(output_json, result)
    if args.require_pass and not passed:
        raise SystemExit(1)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-config", default=str(DEFAULT_TRACE_CONFIG))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = check_candidate_config(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
