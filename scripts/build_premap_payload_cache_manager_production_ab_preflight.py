#!/usr/bin/env python3
"""Build a production-like A/B preflight for payload-cache manager work.

This checker combines a production-like paired benchmark envelope with the
payload-cache manager useful-work A/B gate.  Passing it means the next run may
execute a production-like manager A/B harness under payloadless constraints.

It does not permit payload transfer, ready credit, WNA16 kernel argument
handoff, or a performance win claim.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANAGER_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_payload_cache"
    / "payload_cache_manager_useful_work_ab_gate.json"
)
DEFAULT_BASELINE_SUMMARY = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "awq_telemetry_ladder"
    / "gpu1_payload_cache_graph_visible_state_only_ab_smoke8_contract_fixed_20260626"
    / "production_batch_graph_warmup_reuse_llm"
    / "repeat_00"
    / "performance_summary.json"
)
DEFAULT_CANDIDATE_SUMMARY = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "awq_telemetry_ladder"
    / "gpu1_payload_cache_graph_visible_state_only_ab_smoke8_contract_fixed_20260626"
    / "production_batch_premap_payload_cache_ready_time_graph_warmup_inside_graph_state_only_producer_counter_off_reuse_llm"
    / "repeat_00"
    / "performance_summary.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_payload_cache"
    / "payload_cache_manager_production_ab_preflight.json"
)

ARTIFACT_KIND = "premap_payload_cache_manager_production_ab_preflight"
MODE = "payload_cache_manager_production_like_ab_preflight"
NEXT_STAGE = "run_production_like_payload_cache_manager_ab"
MANAGER_GATE_KIND = "premap_payload_cache_manager_useful_work_ab_gate"

SUMMARY_FALSE_FIELDS = (
    "runtime_shadow_premap_payload_cache_direct_ready_credit",
    "runtime_shadow_premap_payload_cache_direct_ready_before_demand_credit",
    "runtime_shadow_premap_payload_cache_direct_real_ready_credit_granted",
    "runtime_shadow_premap_payload_cache_direct_payload_transfer_enabled",
    "runtime_shadow_premap_payload_cache_direct_payload_deref_allowed",
    "runtime_shadow_premap_payload_cache_direct_passed_to_kernel",
    "runtime_shadow_premap_payload_cache_direct_uses_current_wna16_args",
    "runtime_shadow_premap_payload_cache_direct_passes_current_wna16_args",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_credit",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_ready_before_demand_credit",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_real_ready_credit_granted",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_transfer_enabled",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_deref_allowed",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_kernel_arg_pass_allowed",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_passed_to_kernel",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_changes_kernel_launch_args",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_uses_current_wna16_args",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_passes_current_wna16_args",
    "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
)
SUMMARY_ZERO_FIELDS = (
    "runtime_shadow_premap_payload_cache_direct_issued_payload_count",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_payload_bytes",
    "runtime_shadow_premap_payload_cache_direct_runtime_execution_issued_payload_count",
    "runtime_shadow_premap_payload_cache_direct_payload_bytes",
)
CONTRACT_SAFETY_PREFIXES = (
    "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract",
    "runtime_shadow_premap_payload_cache_direct_online_inside_graph_producer_boundary_contract",
    "runtime_shadow_premap_payload_cache_direct_online_stream_contract",
)
CONTRACT_FALSE_SUFFIXES = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_allowed",
    "payload_deref_runtime_allowed",
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
    "full_fetch_runtime_allowed",
    "live_runtime_instantiated",
)
CONTRACT_ZERO_SUFFIXES = (
    "payload_bytes",
    "issued_payload_count",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _finite_positive(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        return None
    return value


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _bool_metric(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    if type(value) is not bool:
        return None
    return bool(value)


def _finite_rate(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or not (0.0 <= value <= 1.0):
        return None
    return value


def _optional_false(
    payload: dict[str, Any],
    key: str,
    failures: list[str],
    *,
    prefix: str,
) -> bool:
    if key not in payload:
        return False
    if payload.get(key) is not False:
        failures.append(f"{prefix}_{key}_not_false")
        return bool(payload.get(key))
    return False


def _optional_zero(
    payload: dict[str, Any],
    key: str,
    failures: list[str],
    *,
    prefix: str,
) -> int:
    if key not in payload:
        return 0
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or int(value) != 0:
        failures.append(f"{prefix}_{key}_not_zero")
        return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0
    return int(value)


def _validate_manager_gate(payload: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    prefix = "manager_gate"
    expected = {
        "artifact_kind": MANAGER_GATE_KIND,
        "mode": "payload_cache_manager_useful_work_ab_precondition",
        "passed": True,
        "manager_useful_work_ab_ready": True,
        "payload_runtime_ready": False,
        "performance_claim_ready": False,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    for key, expected_value in expected.items():
        if type(payload.get(key)) is not type(expected_value) or payload.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    issued = _int_metric(payload, "issued_prefetch_count")
    used = _int_metric(payload, "used_fetch_count")
    unused = _int_metric(payload, "unused_fetch_count")
    demand = _int_metric(payload, "demand_count")
    hit = _int_metric(payload, "demand_hit_count")
    demand_hit_rate = _finite_rate(payload, "demand_hit_rate")
    used_per_issued_fetch = _finite_rate(payload, "used_per_issued_fetch")
    if issued is None or issued <= 0:
        failures.append(f"{prefix}_issued_prefetch_count_invalid")
        issued = 0
    if used is None or used <= 0:
        failures.append(f"{prefix}_used_fetch_count_invalid")
        used = 0
    if unused is None or unused < 0:
        failures.append(f"{prefix}_unused_fetch_count_invalid")
        unused = 0
    if demand is None or demand <= 0:
        failures.append(f"{prefix}_demand_count_invalid")
        demand = 0
    if hit is None or hit <= 0:
        failures.append(f"{prefix}_demand_hit_count_invalid")
        hit = 0
    if demand_hit_rate is None:
        failures.append(f"{prefix}_demand_hit_rate_invalid")
        demand_hit_rate = 0.0
    if used_per_issued_fetch is None:
        failures.append(f"{prefix}_used_per_issued_fetch_invalid")
        used_per_issued_fetch = 0.0
    return {
        "issued_prefetch_count": int(issued or 0),
        "used_fetch_count": int(used or 0),
        "unused_fetch_count": int(unused or 0),
        "demand_count": int(demand or 0),
        "demand_hit_count": int(hit or 0),
        "demand_hit_rate": float(demand_hit_rate or 0.0),
        "used_per_issued_fetch": float(used_per_issued_fetch or 0.0),
    }


def _validate_summary(
    payload: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
    min_sample_count: int,
) -> dict[str, Any]:
    tpot = _finite_positive(payload, "generate_seconds_per_requested_output_token")
    if tpot is None:
        failures.append(f"{prefix}_tpot_invalid")
        tpot = 0.0
    sample_count = _int_metric(payload, "sample_count")
    token_count = _int_metric(payload, "requested_output_token_count")
    if sample_count is None or sample_count < min_sample_count:
        failures.append(f"{prefix}_sample_count_too_low")
        sample_count = 0
    if token_count is None or token_count <= 0:
        failures.append(f"{prefix}_requested_output_token_count_invalid")
        token_count = 0
    payload_bytes = 0
    for key in SUMMARY_ZERO_FIELDS:
        payload_bytes += _optional_zero(payload, key, failures, prefix=prefix)
    kernel_arg_enabled = False
    for key in SUMMARY_FALSE_FIELDS:
        kernel_arg_enabled = (
            _optional_false(payload, key, failures, prefix=prefix)
            or kernel_arg_enabled
        )
    for contract_prefix in CONTRACT_SAFETY_PREFIXES:
        for suffix in CONTRACT_ZERO_SUFFIXES:
            payload_bytes += _optional_zero(
                payload,
                f"{contract_prefix}_{suffix}",
                failures,
                prefix=prefix,
            )
        for suffix in CONTRACT_FALSE_SUFFIXES:
            kernel_arg_enabled = (
                _optional_false(
                    payload,
                    f"{contract_prefix}_{suffix}",
                    failures,
                    prefix=prefix,
                )
                or kernel_arg_enabled
            )
    return {
        "tpot_s": float(tpot),
        "sample_count": int(sample_count or 0),
        "requested_output_token_count": int(token_count or 0),
        "payload_bytes": int(payload_bytes),
        "kernel_arg_enabled": bool(kernel_arg_enabled),
        "manager_counter_enabled": _bool_metric(
            payload,
            "runtime_shadow_emit_premap_payload_cache_manager_counters",
        ),
        "manager_mode": payload.get("runtime_shadow_premap_payload_cache_direct_manager_mode")
        or payload.get("runtime_shadow_premap_payload_cache_manager_mode"),
        "producer_contract_passed": (
            _bool_metric(
                payload,
                "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed",
            )
            is True
            or _bool_metric(
                payload,
                "runtime_shadow_premap_payload_cache_direct_online_stream_contract_passed",
            )
            is True
        ),
        "producer_contract_present": (
            "runtime_shadow_premap_payload_cache_direct_graph_visible_producer_contract_passed"
            in payload
            or "runtime_shadow_premap_payload_cache_direct_online_stream_contract_passed"
            in payload
        ),
    }


def build_preflight(
    *,
    manager_gate_json: Path,
    baseline_summary: Path,
    candidate_summary: Path,
    min_sample_count: int,
    max_envelope_overhead_ratio: float,
) -> dict[str, Any]:
    failures: list[str] = []
    if not math.isfinite(max_envelope_overhead_ratio) or max_envelope_overhead_ratio < 0.0:
        failures.append("max_envelope_overhead_ratio_invalid")
    manager_gate = _validate_manager_gate(_load_json(manager_gate_json), failures)
    baseline = _validate_summary(
        _load_json(baseline_summary),
        failures,
        prefix="baseline_summary",
        min_sample_count=min_sample_count,
    )
    candidate = _validate_summary(
        _load_json(candidate_summary),
        failures,
        prefix="candidate_summary",
        min_sample_count=min_sample_count,
    )
    if baseline["sample_count"] != candidate["sample_count"]:
        failures.append("paired_sample_count_mismatch")
    if baseline["requested_output_token_count"] != candidate["requested_output_token_count"]:
        failures.append("paired_requested_output_token_count_mismatch")
    overhead_ratio = (
        (candidate["tpot_s"] / baseline["tpot_s"]) - 1.0
        if baseline["tpot_s"] > 0.0 and candidate["tpot_s"] > 0.0
        else 0.0
    )
    if overhead_ratio > max_envelope_overhead_ratio:
        failures.append("candidate_envelope_overhead_over_threshold")
    if candidate["payload_bytes"] != 0:
        failures.append("candidate_payload_bytes_nonzero")
    if candidate["kernel_arg_enabled"]:
        failures.append("candidate_kernel_arg_enabled")
    if not candidate["manager_counter_enabled"]:
        failures.append("candidate_manager_counters_not_enabled")
    if not candidate["producer_contract_present"]:
        failures.append("candidate_producer_contract_missing")
    if not candidate["producer_contract_passed"]:
        failures.append("candidate_producer_contract_not_passed")
    passed = not failures
    return {
        "artifact_kind": ARTIFACT_KIND,
        "artifact_scope": "preflight_smoke_only",
        "mode": MODE,
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "production_like_manager_ab_harness_ready": passed,
        "final_production_result_ready": False,
        "payload_runtime_ready": False,
        "performance_claim_ready": False,
        "consumes_tpot_summary_for_envelope": True,
        "next_stage": NEXT_STAGE,
        "manager_accounting_source": "payload_cache_manager_useful_work_ab_gate",
        "manager_issued_prefetch_count": manager_gate["issued_prefetch_count"],
        "manager_used_fetch_count": manager_gate["used_fetch_count"],
        "manager_unused_fetch_count": manager_gate["unused_fetch_count"],
        "manager_demand_count": manager_gate["demand_count"],
        "manager_demand_hit_count": manager_gate["demand_hit_count"],
        "manager_demand_hit_rate": manager_gate["demand_hit_rate"],
        "manager_used_per_issued_fetch": manager_gate["used_per_issued_fetch"],
        "baseline_tpot_s": baseline["tpot_s"],
        "candidate_tpot_s": candidate["tpot_s"],
        "candidate_envelope_overhead_ratio": overhead_ratio,
        "candidate_envelope_overhead_percent": overhead_ratio * 100.0,
        "max_envelope_overhead_ratio": max_envelope_overhead_ratio,
        "sample_count": candidate["sample_count"],
        "requested_output_token_count": candidate["requested_output_token_count"],
        "candidate_manager_counter_enabled": candidate["manager_counter_enabled"],
        "candidate_manager_mode": candidate["manager_mode"],
        "candidate_producer_contract_passed": candidate["producer_contract_passed"],
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "manager_gate_json": _display_path(manager_gate_json),
        "baseline_summary": _display_path(baseline_summary),
        "candidate_summary": _display_path(candidate_summary),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager-gate-json", type=Path, default=DEFAULT_MANAGER_GATE_JSON)
    parser.add_argument("--baseline-summary", type=Path, default=DEFAULT_BASELINE_SUMMARY)
    parser.add_argument("--candidate-summary", type=Path, default=DEFAULT_CANDIDATE_SUMMARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--min-sample-count", type=int, default=8)
    parser.add_argument("--max-envelope-overhead-ratio", type=float, default=0.05)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_preflight(
        manager_gate_json=args.manager_gate_json,
        baseline_summary=args.baseline_summary,
        candidate_summary=args.candidate_summary,
        min_sample_count=int(args.min_sample_count),
        max_envelope_overhead_ratio=float(args.max_envelope_overhead_ratio),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
