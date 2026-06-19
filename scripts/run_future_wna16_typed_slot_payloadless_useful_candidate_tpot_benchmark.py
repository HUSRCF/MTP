#!/usr/bin/env python3
"""Run or archive a payloadless useful candidate TPOT benchmark.

This wrapper consumes the production-compatible candidate config gate.  The
candidate may activate the lightweight premap live-config object without the
router recorder, but it must remain payloadless and must not pass or mutate
WNA16 kernel arguments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_CONFIG_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_candidate_config_gate_dolly32_gen64_graph_v1.json"
)
DEFAULT_DECISION_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "payloadless_live_config_performance_decision_gate_v1.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
)
DEFAULT_OUTPUT_JSON = (
    DEFAULT_OUTPUT_ROOT
    / "future_wna16_typed_slot_payloadless_useful_production_like_tpot_candidate_blocked_by_decision_gate_v2.json"
)
DEFAULT_PYTHON = "/home/husrcf/anaconda3/envs/TRY/bin/python"

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_production_like_tpot_benchmark"
BENCHMARK_NAME = "premap_future_wna16_typed_slot_payloadless_useful_candidate_tpot_v1"
BENCHMARK_MODE = "production_like_payloadless_useful_candidate"
BENCHMARK_SOURCE = "premap_future_wna16_typed_slot_payloadless_useful_candidate_config_gate_v1"
NEXT_RUNTIME_STAGE = "compare_payloadless_useful_candidate_tpot"

EXPECTED_GATE_FLAGS: dict[str, Any] = {
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
}
PERF_FIELDS = (
    "generate_seconds_per_requested_output_token",
    "generate_wall_seconds",
    "total_trace_wall_seconds",
    "requested_output_token_count",
    "sample_count",
    "input_token_count",
    "llm_init_wall_seconds",
)
PERF_FALSE_FIELDS = (
    "decode_workload_trace_enabled",
    "runtime_shadow_enabled",
    "runtime_shadow_record_router_topk",
    "runtime_shadow_emit_decoder_layer_timing",
    "runtime_shadow_emit_decoder_component_timing",
    "runtime_shadow_emit_moe_substage_timing",
    "runtime_shadow_emit_engine_timing",
    "runtime_shadow_emit_wna16_kernel_timing",
    "runtime_shadow_emit_premap_summaries",
    "runtime_shadow_emit_premap_consumer_mapping",
    "runtime_shadow_capture_router_topk",
    "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_slim_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
    "runtime_shadow_premap_native_typed_consumer_input_export_enabled",
    "runtime_shadow_premap_payload_cache_producer_state_packet_export_enabled",
    "runtime_shadow_premap_payload_cache_manager_demand_on_consumer",
    "runtime_shadow_premap_payload_cache_manager_emit_consumer_rows",
)
PERF_TRUE_FIELDS = (
    "runtime_shadow_premap_live_config_without_router_recorder_enabled",
    "runtime_shadow_premap_live_config_without_router_recorder_allowed",
    "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected",
)
PERF_OFF_FIELDS = {
    "runtime_shadow_decoder_source_timing_mode": "off",
    "runtime_shadow_moe_source_timing_mode": "off",
    "runtime_shadow_outcome_logging_mode": "off",
    "runtime_shadow_premap_kernel_arg_handoff_live_counter_mode": "off",
    "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
}


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _check_gate(gate: dict[str, Any], failures: list[str]) -> None:
    for key, expected in EXPECTED_GATE_FLAGS.items():
        if gate.get(key) != expected:
            failures.append(f"config_gate_{key}_mismatch")
    trace_config = gate.get("trace_config")
    trace_sha = gate.get("trace_config_sha256")
    if not isinstance(trace_config, str) or not trace_config:
        failures.append("config_gate_trace_config_missing")
        return
    trace_path = _resolve(trace_config)
    if not trace_path.exists():
        failures.append("config_gate_trace_config_missing")
        return
    if _sha256(trace_path) != trace_sha:
        failures.append("config_gate_trace_config_sha256_mismatch")


def _check_decision_gate(decision: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    expected = {
        "artifact_kind": "payloadless_live_config_performance_decision_gate",
        "decision_name": "premap_payloadless_live_config_performance_decision_v1",
        "passed": True,
        "failures": [],
        "freeze_payloadless_live_config_performance_claim": True,
        "payloadless_live_config_status": "safe_participation_path_not_performance_mainline",
        "real_performance_next_path": "future_typed_slot_useful_consumer_or_payload_cache_manager",
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
    }
    for key, expected_value in expected.items():
        if decision.get(key) != expected_value:
            failures.append(f"decision_gate_{key}_mismatch")
    if decision.get("freeze_payloadless_live_config_performance_claim") is True:
        failures.append("payloadless_candidate_tpot_blocked_by_decision_gate")
    return {
        "freeze_payloadless_live_config_performance_claim": decision.get(
            "freeze_payloadless_live_config_performance_claim"
        ),
        "payloadless_live_config_status": decision.get("payloadless_live_config_status"),
        "real_performance_next_path": decision.get("real_performance_next_path"),
    }


def _default_trace_dir_from_gate(gate: dict[str, Any]) -> Path | None:
    output_dir = gate.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        return None
    return _resolve(output_dir)


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def _copy_config_for_run(
    *,
    gate: dict[str, Any],
    output_root: Path,
    repeat: int,
) -> tuple[Path, Path]:
    trace_config_path = _resolve(str(gate["trace_config"]))
    cfg = _load_yaml(trace_config_path)
    trace_dir = output_root / "payloadless_useful_candidate" / f"repeat_{repeat:02d}"
    cfg["output_dir"] = str(trace_dir)
    shadow = cfg.setdefault("trace", {}).setdefault("runtime_shadow", {})
    if isinstance(shadow, dict):
        shadow["output_path"] = str(trace_dir / "runtime_shadow.jsonl")
    config_out = output_root / "trace_configs" / f"payloadless_useful_candidate_repeat_{repeat:02d}.yaml"
    config_out.parent.mkdir(parents=True, exist_ok=True)
    config_out.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return config_out, trace_dir


def _run_trace(
    *,
    python: str,
    config_path: Path,
    gpu: str,
    log_path: Path,
) -> int:
    env = os.environ.copy()
    env["HIP_VISIBLE_DEVICES"] = str(gpu)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing else f"src{os.pathsep}{existing}"
    proc = subprocess.run(
        [python, "scripts/trace_router_mtp_vllm.py", str(config_path)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stdout, encoding="utf-8")
    return int(proc.returncode)


def _read_perf(trace_dir: Path, failures: list[str]) -> dict[str, Any]:
    perf_path = trace_dir / "performance_summary.json"
    if not perf_path.exists():
        failures.append("performance_summary_missing")
        return {}
    try:
        perf = _load_json(perf_path)
    except Exception as exc:
        failures.append(f"performance_summary_load_failed:{exc.__class__.__name__}:{exc}")
        return {}
    tpot = _numeric(perf.get("generate_seconds_per_requested_output_token"))
    generate_wall = _numeric(perf.get("generate_wall_seconds"))
    requested_tokens = perf.get("requested_output_token_count")
    if tpot is None or tpot <= 0:
        failures.append("generate_seconds_per_requested_output_token_invalid")
    if generate_wall is None or generate_wall <= 0:
        failures.append("generate_wall_seconds_invalid")
    if not isinstance(requested_tokens, int) or requested_tokens <= 0:
        failures.append("requested_output_token_count_invalid")
    for key in PERF_FALSE_FIELDS:
        if perf.get(key) is not False:
            failures.append(f"performance_summary_{key}_not_false")
    for key in PERF_TRUE_FIELDS:
        if perf.get(key) is not True:
            failures.append(f"performance_summary_{key}_not_true")
    for key, expected in PERF_OFF_FIELDS.items():
        if perf.get(key) != expected:
            failures.append(f"performance_summary_{key}_mismatch")
    return {
        key: perf.get(key)
        for key in PERF_FIELDS
    } | {
        "performance_summary_json": str(perf_path),
        "performance_summary_sha256": _sha256(perf_path),
        "tokens_per_second": (1.0 / tpot) if tpot and tpot > 0 else None,
    }


def run_candidate_tpot_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    gate_path = _resolve(args.config_gate_json)
    decision_gate_path = _resolve(args.decision_gate_json)
    output_root = _resolve(args.output_root)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    try:
        gate = _load_json(gate_path)
    except Exception as exc:
        gate = {}
        failures.append(f"config_gate_load_failed:{exc.__class__.__name__}:{exc}")
    if gate:
        _check_gate(gate, failures)
    try:
        decision_gate = _load_json(decision_gate_path)
    except Exception as exc:
        decision_gate = {}
        failures.append(f"decision_gate_load_failed:{exc.__class__.__name__}:{exc}")
    decision_summary = _check_decision_gate(decision_gate, failures)

    gate_trace_dir = _default_trace_dir_from_gate(gate) if gate else None
    trace_dir: Path | None = None
    trace_config_for_run: Path | None = None
    log_path: Path | None = None
    returncode: int | None = None
    run_requested = bool(args.run)
    run_executed = False
    if failures:
        if run_requested:
            failures.append("trace_run_skipped_due_to_gate_failure")
    elif args.run:
        trace_config_for_run, trace_dir = _copy_config_for_run(
            gate=gate,
            output_root=output_root,
            repeat=args.repeat,
        )
        log_path = output_root / "logs" / f"payloadless_useful_candidate_repeat_{args.repeat:02d}.log"
        run_executed = True
        returncode = _run_trace(
            python=args.python,
            config_path=trace_config_for_run,
            gpu=str(args.gpu),
            log_path=log_path,
        )
        if returncode != 0:
            failures.append("trace_run_failed")
    else:
        trace_dir = _resolve(args.trace_dir) if args.trace_dir else gate_trace_dir
        if trace_dir is None:
            failures.append("trace_dir_missing")
        elif gate_trace_dir is None:
            failures.append("config_gate_trace_dir_missing")
        elif not _same_path(trace_dir, gate_trace_dir):
            failures.append("trace_dir_not_bound_to_config_gate")

    perf_summary = (
        _read_perf(trace_dir, failures)
        if trace_dir is not None and not (failures and not run_executed)
        else {}
    )
    passed = not failures
    result: dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_mode": BENCHMARK_MODE,
        "benchmark_source": BENCHMARK_SOURCE,
        "passed": passed,
        "failures": failures,
        "production_like_tpot_candidate_ready": passed,
        "payloadless_useful_candidate_config_ready": bool(
            gate.get("payloadless_useful_candidate_config_ready")
        ),
        "config_gate_json": str(gate_path),
        "config_gate_sha256": _sha256(gate_path) if gate_path.exists() else None,
        "decision_gate_json": str(decision_gate_path),
        "decision_gate_sha256": _sha256(decision_gate_path)
        if decision_gate_path.exists()
        else None,
        "decision_summary": decision_summary,
        "payloadless_live_config_performance_claim_frozen": decision_summary.get(
            "freeze_payloadless_live_config_performance_claim"
        ),
        "payloadless_candidate_tpot_allowed": False,
        "trace_config": gate.get("trace_config"),
        "trace_config_sha256": gate.get("trace_config_sha256"),
        "trace_config_for_run": None if trace_config_for_run is None else str(trace_config_for_run),
        "gate_trace_dir": None if gate_trace_dir is None else str(gate_trace_dir),
        "trace_dir": None if trace_dir is None else str(trace_dir),
        "log_path": None if log_path is None else str(log_path),
        "run_requested": run_requested,
        "run_executed": run_executed,
        "returncode": returncode,
        "gpu": str(args.gpu),
        "payloadless_useful_mode_enabled": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": bool(perf_summary),
        "measures_vllm_latency": bool(perf_summary),
        "benchmark_is_current_vllm_baseline": False,
        "benchmark_is_future_typed_slot_useful_path": True,
        "next_runtime_stage": decision_summary.get(
            "real_performance_next_path",
            NEXT_RUNTIME_STAGE,
        ),
        **perf_summary,
    }
    _write_json(output_path, result)
    if args.require_pass and not passed:
        raise SystemExit(1)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-gate-json", default=str(DEFAULT_CONFIG_GATE_JSON))
    parser.add_argument("--decision-gate-json", default=str(DEFAULT_DECISION_GATE_JSON))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--trace-dir", default=None)
    parser.add_argument("--python", default=DEFAULT_PYTHON)
    parser.add_argument("--gpu", default="1")
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_candidate_tpot_benchmark(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
