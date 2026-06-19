#!/usr/bin/env python3
"""Validate the production-like timing config for the payloadless typed-slot path.

This gate consumes the payloadless useful runtime-ablation artifact and a vLLM
trace config.  It does not run vLLM and does not measure TPOT.  Its only job is
to prevent the next paired timing benchmark from accidentally using a heavy
shadow/diagnostic config or a native-stub artifact that already mutated payload
or kernel arguments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_RUNTIME_ABLATION_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_runtime_ablation_entry_args_ptr_repeat3_gpu1_v1.json"
)
DEFAULT_TRACE_CONFIG = (
    REPO_ROOT
    / "configs"
    / "trace"
    / "router_mtp_trace_external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_production_no_recorder_graph.yaml"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_dolly32_gen64_graph_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_production_like_timing_gate"
GATE_NAME = "premap_future_wna16_typed_slot_payloadless_useful_production_like_timing_gate_v1"
GATE_MODE = "production_like_config_readiness_gate"
GATE_SOURCE = "premap_future_wna16_typed_slot_payloadless_useful_runtime_ablation_v1"
NEXT_RUNTIME_STAGE = "run_production_like_vllm_paired_tpot_benchmark"
FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)

EXPECTED_RUNTIME_ABLATION_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_payloadless_useful_runtime_ablation",
    "ablation_name": "premap_future_wna16_typed_slot_payloadless_useful_runtime_ablation_v1",
    "ablation_mode": "payloadless_useful_native_stub_repeat_stability_ablation",
    "ablation_source": "premap_future_wna16_typed_slot_payloadless_useful_repeat_benchmark_v1",
    "passed": True,
    "failures": [],
    "runtime_ablation_ready": True,
    "payloadless_useful_runtime_ablation_ready": True,
    "benchmark_is_current_wna16_fused_moe": False,
    "measures_vllm_latency": False,
    "measures_tpot": False,
    "wna16_benchmark_ready": False,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
    "payload_bytes": 0,
    "payload_deref_allowed": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "next_runtime_stage": "implement_future_wna16_typed_slot_payloadless_useful_production_like_timing",
}

TRACE_FALSE_FLAGS = (
    "capture_router_topk",
    "capture_router_scores",
    "use_router_logits_recorder",
    "capture_native_mtp_router",
)
SHADOW_FALSE_FLAGS = (
    "enabled",
    "record_router_topk",
    "emit_transition_summaries",
    "emit_descriptor_order_summaries",
    "emit_summaries",
    "emit_outcomes",
    "emit_decoder_layer_timing",
    "emit_decoder_component_timing",
    "emit_moe_substage_timing",
    "emit_engine_timing",
    "emit_wna16_kernel_timing",
    "descriptor_order_emit_consumer_handle_events",
    "descriptor_order_reorder_mvp_enabled",
)
SHADOW_OFF_VALUES = {
    "outcome_logging_mode": "off",
    "decoder_source_timing_mode": "off",
    "moe_source_timing_mode": "off",
    "descriptor_order_mapping_assertion_mode": "off",
    "descriptor_order_prelaunch_assertion_mode": "off",
}
RISKY_SHADOW_FLAGS = (
    "emit_premap_summaries",
    "emit_premap_address_manager_counters",
    "emit_premap_payload_cache_manager_counters",
    "emit_premap_consumer_mapping",
    "premap_consumer_resolve_real_handles",
    "premap_consumer_require_readonly_gate",
    "premap_kernel_arg_handoff_live_enabled",
    "premap_kernel_arg_handoff_live_consumer_connected",
    "premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "premap_descriptor_prep_enabled",
    "premap_consumer_shim_enabled",
    "premap_native_typed_consumer_bridge_enabled",
    "premap_future_wna16_typed_slot_payloadless_execution_enabled",
    "premap_payload_cache_manager_demand_on_consumer",
    "premap_payload_cache_manager_emit_consumer_rows",
    "premap_payload_cache_producer_state_packet_export_enabled",
    "premap_native_typed_consumer_input_export_enabled",
)
RISKY_TOP_LEVEL_TRACE_FLAGS = (
    "decode_workload_trace",
)
STRICT_FALSE_OR_ABSENT_TOP_LEVEL_TRACE_FLAGS = (
    "allow_premap_live_config_without_router_recorder",
)
RISKY_SHADOW_PREFIXES = (
    "premap_payload_cache_",
    "premap_native_typed_consumer_input_export_",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML config must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 <= parsed <= 0xFFFFFFFFFFFFFFFF


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_runtime_ablation(
    payload: dict[str, Any],
    failures: list[str],
    *,
    min_source_count: int,
    min_row_count: int,
    min_repeat_count: int,
) -> None:
    for key, expected in EXPECTED_RUNTIME_ABLATION_FLAGS.items():
        if payload.get(key) != expected:
            failures.append(f"runtime_ablation_{key}_mismatch")
    if payload.get("field_names") != list(FIELDS):
        failures.append("runtime_ablation_field_names_mismatch")
    source_count = _int_metric(payload, "source_count")
    row_count = _int_metric(payload, "row_count")
    row_ok_count = _int_metric(payload, "row_ok_count")
    rows_consumed = _int_metric(payload, "rows_consumed")
    repeat_count = _int_metric(payload, "repeat_count_measured")
    if source_count is None or source_count < min_source_count:
        failures.append("runtime_ablation_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("runtime_ablation_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("runtime_ablation_row_ok_count_mismatch")
    if row_count is not None and rows_consumed != row_count:
        failures.append("runtime_ablation_rows_consumed_mismatch")
    if repeat_count is None or repeat_count < min_repeat_count:
        failures.append("runtime_ablation_repeat_count_invalid")
    repeat_path = payload.get("repeat_benchmark_json")
    repeat_sha = payload.get("repeat_benchmark_sha256")
    if not isinstance(repeat_path, str) or not repeat_path:
        failures.append("runtime_ablation_repeat_benchmark_json_missing")
    elif not _resolve(repeat_path).exists():
        failures.append("runtime_ablation_repeat_benchmark_json_missing")
    if not _is_sha256_hex(repeat_sha):
        failures.append("runtime_ablation_repeat_benchmark_sha256_invalid")
    elif isinstance(repeat_path, str) and _resolve(repeat_path).exists():
        if _sha256(_resolve(repeat_path)) != repeat_sha:
            failures.append("runtime_ablation_repeat_benchmark_sha256_mismatch")
    field_hashes = payload.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("runtime_ablation_field_read_hashes_missing")
        field_hashes = {}
    for field in FIELDS:
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"runtime_ablation_{field}_field_hash_invalid")


def _require_false(payload: dict[str, Any], key: str, failures: list[str], *, label: str) -> None:
    if payload.get(key) is not False:
        failures.append(f"{label}_{key}_not_false")


def _check_disabled_mapping(payload: dict[str, Any], key: str, failures: list[str], *, label: str) -> None:
    if key not in payload:
        return
    value = payload.get(key)
    if value in (False, None):
        return
    if isinstance(value, dict):
        if bool(value.get("enabled", False)):
            failures.append(f"{label}_{key}_enabled")
        return
    failures.append(f"{label}_{key}_not_disabled")


def _check_trace_config(
    payload: dict[str, Any],
    failures: list[str],
    *,
    min_samples: int,
    min_tokens: int,
    expected_split_id: str | None,
    expected_sample_start: int | None,
    expected_sample_end: int | None,
) -> dict[str, Any]:
    model = payload.get("model")
    data = payload.get("data")
    output_dir = payload.get("output_dir")
    trace = payload.get("trace")
    if not isinstance(model, str) or not model:
        failures.append("trace_config_model_missing")
    if not isinstance(data, str) or not data:
        failures.append("trace_config_data_missing")
    if not isinstance(output_dir, str) or not output_dir:
        failures.append("trace_config_output_dir_missing")
    if not isinstance(trace, dict):
        failures.append("trace_config_trace_missing")
        trace = {}

    for key in TRACE_FALSE_FLAGS:
        _require_false(trace, key, failures, label="trace")
    for key in RISKY_TOP_LEVEL_TRACE_FLAGS:
        _check_disabled_mapping(trace, key, failures, label="trace")
    for key in STRICT_FALSE_OR_ABSENT_TOP_LEVEL_TRACE_FLAGS:
        if key in trace and trace.get(key) is not False:
            failures.append(f"trace_{key}_not_false")
    if trace.get("capture_hidden_states") != "none":
        failures.append("trace_capture_hidden_states_not_none")
    if trace.get("allow_missing_router_trace") is not True:
        failures.append("trace_allow_missing_router_trace_not_true")
    max_samples = _int_metric(trace, "max_samples")
    max_tokens = _int_metric(trace, "max_tokens")
    if max_samples is None or max_samples < min_samples:
        failures.append("trace_max_samples_invalid")
    if max_tokens is None or max_tokens < min_tokens:
        failures.append("trace_max_tokens_invalid")
    if expected_split_id is not None and trace.get("split_id") != expected_split_id:
        failures.append("trace_split_id_mismatch")
    if expected_sample_start is not None:
        if trace.get("start_sample") != expected_sample_start:
            failures.append("trace_start_sample_mismatch")
        if trace.get("expected_sample_start") != expected_sample_start:
            failures.append("trace_expected_sample_start_mismatch")
    if expected_sample_end is not None and trace.get("expected_sample_end") != expected_sample_end:
        failures.append("trace_expected_sample_end_mismatch")

    shadow = trace.get("runtime_shadow")
    if not isinstance(shadow, dict):
        failures.append("trace_runtime_shadow_missing")
        shadow = {}
    for key in SHADOW_FALSE_FLAGS:
        _require_false(shadow, key, failures, label="runtime_shadow")
    for key, expected in SHADOW_OFF_VALUES.items():
        if shadow.get(key) != expected:
            failures.append(f"runtime_shadow_{key}_mismatch")
    for key in RISKY_SHADOW_FLAGS:
        if key in shadow and shadow.get(key) is not False:
            failures.append(f"runtime_shadow_{key}_not_false")
    for key, value in shadow.items():
        if not any(key.startswith(prefix) for prefix in RISKY_SHADOW_PREFIXES):
            continue
        if key in RISKY_SHADOW_FLAGS:
            continue
        if isinstance(value, bool) and value:
            failures.append(f"runtime_shadow_{key}_not_false")

    return {
        "model": model,
        "data": data,
        "output_dir": output_dir,
        "split_id": trace.get("split_id"),
        "start_sample": trace.get("start_sample"),
        "expected_sample_start": trace.get("expected_sample_start"),
        "expected_sample_end": trace.get("expected_sample_end"),
        "max_samples": max_samples,
        "max_tokens": max_tokens,
        "runtime_shadow_enabled": shadow.get("enabled"),
        "record_router_topk": shadow.get("record_router_topk"),
        "outcome_logging_mode": shadow.get("outcome_logging_mode"),
        "decoder_source_timing_mode": shadow.get("decoder_source_timing_mode"),
        "moe_source_timing_mode": shadow.get("moe_source_timing_mode"),
    }


def run_production_like_timing_gate(args: argparse.Namespace) -> dict[str, Any]:
    runtime_ablation_path = _resolve(args.runtime_ablation_json)
    trace_config_path = _resolve(args.trace_config)
    output_path = _resolve(args.output_json)
    failures: list[str] = []

    try:
        runtime_ablation = _load_json(runtime_ablation_path)
    except Exception as exc:
        runtime_ablation = {}
        failures.append(f"runtime_ablation_load_failed:{exc.__class__.__name__}:{exc}")
    try:
        trace_config = _load_yaml(trace_config_path)
    except Exception as exc:
        trace_config = {}
        failures.append(f"trace_config_load_failed:{exc.__class__.__name__}:{exc}")

    _check_runtime_ablation(
        runtime_ablation,
        failures,
        min_source_count=args.min_source_count,
        min_row_count=args.min_row_count,
        min_repeat_count=args.min_repeat_count,
    )
    trace_summary = _check_trace_config(
        trace_config,
        failures,
        min_samples=args.min_samples,
        min_tokens=args.min_tokens,
        expected_split_id=args.expected_split_id,
        expected_sample_start=args.expected_sample_start,
        expected_sample_end=args.expected_sample_end,
    )
    passed = not failures
    safety_keys = (
        "payload_bytes",
        "payload_deref_allowed",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "current_wna16_arg_compatible",
        "requires_wna16_arg_reinterpretation",
        "benchmark_is_current_wna16_fused_moe",
        "measures_tpot",
        "measures_vllm_latency",
        "wna16_benchmark_ready",
    )
    observed_safety = {key: runtime_ablation.get(key) for key in safety_keys}

    result: dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "timing_gate_name": GATE_NAME,
        "timing_gate_mode": GATE_MODE,
        "timing_gate_source": GATE_SOURCE,
        "passed": passed,
        "failures": failures,
        "production_like_timing_ready": passed,
        "production_like_benchmark_config_ready": passed,
        "benchmark_run_ready": False,
        "trace_config_is_production_like": passed,
        "runtime_ablation_ready": bool(runtime_ablation.get("runtime_ablation_ready")),
        "payloadless_useful_runtime_ablation_ready": bool(
            runtime_ablation.get("payloadless_useful_runtime_ablation_ready")
        ),
        "bound_runtime_ablation_safety": observed_safety,
        "runtime_ablation_json": str(runtime_ablation_path),
        "runtime_ablation_sha256": _sha256(runtime_ablation_path)
        if runtime_ablation_path.exists()
        else None,
        "trace_config": str(trace_config_path),
        "trace_config_sha256": _sha256(trace_config_path) if trace_config_path.exists() else None,
        "trace_config_summary": trace_summary,
        "source_count": runtime_ablation.get("source_count"),
        "row_count": runtime_ablation.get("row_count"),
        "repeat_count_measured": runtime_ablation.get("repeat_count_measured"),
        "field_names": runtime_ablation.get("field_names"),
        "payload_bytes": runtime_ablation.get("payload_bytes"),
        "payload_deref_allowed": runtime_ablation.get("payload_deref_allowed"),
        "kernel_arg_pass_allowed": runtime_ablation.get("kernel_arg_pass_allowed"),
        "passed_to_kernel": runtime_ablation.get("passed_to_kernel"),
        "changes_kernel_launch_args": runtime_ablation.get("changes_kernel_launch_args"),
        "uses_current_wna16_args": runtime_ablation.get("uses_current_wna16_args"),
        "passes_current_wna16_args": runtime_ablation.get("passes_current_wna16_args"),
        "current_wna16_arg_compatible": runtime_ablation.get("current_wna16_arg_compatible"),
        "requires_wna16_arg_reinterpretation": runtime_ablation.get(
            "requires_wna16_arg_reinterpretation"
        ),
        "benchmark_is_current_wna16_fused_moe": runtime_ablation.get(
            "benchmark_is_current_wna16_fused_moe"
        ),
        "measures_tpot": runtime_ablation.get("measures_tpot"),
        "measures_vllm_latency": runtime_ablation.get("measures_vllm_latency"),
        "wna16_benchmark_ready": runtime_ablation.get("wna16_benchmark_ready"),
        "current_artifact_is_tpot_benchmark": False,
        "current_wna16_benchmark_ready": False,
        "will_measure_tpot_next": passed,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    _write_json(output_path, result)
    if args.require_pass and not passed:
        raise SystemExit(1)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-ablation-json",
        default=str(DEFAULT_RUNTIME_ABLATION_JSON),
        help="Payloadless useful runtime-ablation artifact to bind.",
    )
    parser.add_argument(
        "--trace-config",
        default=str(DEFAULT_TRACE_CONFIG),
        help="Production-like vLLM trace config to validate for the next benchmark.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Output readiness gate artifact.",
    )
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--min-repeat-count", type=int, default=3)
    parser.add_argument("--min-samples", type=int, default=32)
    parser.add_argument("--min-tokens", type=int, default=64)
    parser.add_argument("--expected-split-id")
    parser.add_argument("--expected-sample-start", type=int)
    parser.add_argument("--expected-sample-end", type=int)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_production_like_timing_gate(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
