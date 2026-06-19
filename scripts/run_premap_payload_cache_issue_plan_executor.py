#!/usr/bin/env python3
"""Execute a payload-cache issue plan through the ready-time manager model.

This is the first consumer above the native producer issue-plan gate.  It does
not move payload bytes and does not grant real ready credit; it only feeds the
issue experts into the controlled ready-time manager to validate queue,
deadline, deduplication, and demand accounting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mtp_expert_prefetch.runtime import ReadyTimeExpertCacheManager  # noqa: E402


DEFAULT_ISSUE_PLAN_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_plan_gate_dolly128_gen64_native_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_plan_executor_dolly128_gen64_ready_time_v1.json"
)
DEFAULT_MEASURED_COPY_BLOCKED_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_plan_executor_dolly128_gen64_measured_copy_blocked_v1.json"
)

ARTIFACT_KIND = "premap_payload_cache_issue_plan_executor"
EXECUTOR_NAME = "premap_payload_cache_ready_time_issue_executor_v1"
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _float_rate(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator > 0 else 0.0


def _select_measured_copy_row(
    path: Path,
    *,
    stat: str,
    experts: int,
    pinned: str,
) -> dict[str, Any]:
    payload = _load_json(path, label="measured-copy envelope")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("measured-copy envelope rows must be a list")
    pinned_filter = str(pinned).lower()
    if pinned_filter not in {"true", "1", "yes", "false", "0", "no", "any"}:
        raise ValueError("measured-copy pinned filter must be true, false, or any")
    candidates = []
    for row in rows:
        if not isinstance(row, dict) or row.get("direction") != "h2d":
            continue
        if int(row.get("experts", -1) or -1) != int(experts):
            continue
        row_pinned = bool(row.get("pinned", False))
        if pinned_filter in {"true", "1", "yes"} and not row_pinned:
            continue
        if pinned_filter in {"false", "0", "no"} and row_pinned:
            continue
        candidates.append(row)
    if not candidates:
        raise ValueError("No matching H2D measured-copy row")
    row = candidates[0]
    stat_key = f"{stat}_ms"
    if stat_key not in row:
        raise ValueError(f"measured-copy row is missing {stat_key}")
    total_us = float(row[stat_key]) * 1000.0
    if not math.isfinite(total_us) or total_us <= 0.0:
        raise ValueError("measured-copy time must be finite and positive")
    copy_us_per_issue = total_us / max(1, int(row["experts"]))
    if not math.isfinite(copy_us_per_issue) or copy_us_per_issue <= 0.0:
        raise ValueError("measured-copy per-issue time must be finite and positive")
    gbps_key = f"{stat}_gbps"
    return {
        "source": str(path),
        "stat": str(stat),
        "selected_experts": int(row["experts"]),
        "pinned": bool(row.get("pinned", False)),
        "copy_us_per_batch": total_us,
        "copy_us_per_issue": copy_us_per_issue,
        "effective_gbps": (
            None if gbps_key not in row else float(row.get(gbps_key) or 0.0)
        ),
    }


def _issue_hash(experts: list[int] | tuple[int, ...]) -> str:
    value = FNV_OFFSET
    count = 0
    for expert_id in experts:
        value ^= int(expert_id) & 0xFFFFFFFF
        value = (value * FNV_PRIME) & U64_MASK
        count += 1
    value ^= count & 0xFFFFFFFF
    value = (value * FNV_PRIME) & U64_MASK
    return f"{value:016x}"


def _check_issue_gate(gate: dict[str, Any], failures: list[str]) -> None:
    expected_true = (
        "passed",
        "issue_plan_ready",
        "payload_cache_issue_plan_candidate",
        "native_issue_plan_valid",
        "runtime_contract_ready",
    )
    for key in expected_true:
        if gate.get(key) is not True:
            failures.append(f"issue_gate_{key}_not_true")
    expected_false = (
        "ready_credit",
        "ready_before_demand_credit",
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    )
    for key in expected_false:
        if gate.get(key) is not False:
            failures.append(f"issue_gate_{key}_not_false")
    if gate.get("payload_bytes") != 0:
        failures.append("issue_gate_payload_bytes_not_zero")
    if not isinstance(gate.get("issue_candidate_experts"), list):
        failures.append("issue_gate_experts_not_list")
    if int(gate.get("issue_candidate_count", -1) or -1) <= 0:
        failures.append("issue_gate_count_not_positive")
    if not isinstance(gate.get("issue_candidate_hash"), str):
        failures.append("issue_gate_hash_missing")


def run_issue_plan_executor(args: argparse.Namespace) -> dict[str, Any]:
    gate_path = _resolve(args.issue_plan_gate_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    gate: dict[str, Any] = {}
    try:
        gate = _load_json(gate_path, label="issue-plan gate")
    except Exception as exc:
        failures.append(f"issue_plan_gate_load_failed:{exc.__class__.__name__}:{exc}")
    if gate:
        _check_issue_gate(gate, failures)

    layer_id = int(gate.get("layer_id", 0) or 0) if gate else 0
    experts_raw = gate.get("issue_candidate_experts", []) if gate else []
    experts: list[int] = []
    if isinstance(experts_raw, list):
        for value in experts_raw:
            if type(value) is int and int(value) >= 0:
                experts.append(int(value))
            else:
                failures.append("issue_candidate_expert_invalid")
                break
    else:
        failures.append("issue_candidate_experts_invalid")
    gate_issue_count = gate.get("issue_candidate_count") if gate else None
    if isinstance(gate_issue_count, int) and not isinstance(gate_issue_count, bool):
        if gate_issue_count != len(experts):
            failures.append("issue_gate_count_expert_list_mismatch")
    elif gate:
        failures.append("issue_gate_count_invalid_type")
    recomputed_issue_hash = _issue_hash(experts)
    if gate and gate.get("issue_candidate_hash") != recomputed_issue_hash:
        failures.append("issue_gate_hash_expert_list_mismatch")

    measured_copy: dict[str, Any] | None = None
    service_us_per_issue = float(args.service_us_per_issue)
    service_us_per_batch = float(args.service_us_per_batch)
    queue_batch_size = int(args.queue_batch_size)
    if args.measured_copy_json is not None:
        measured_copy_path = _resolve(args.measured_copy_json)
        try:
            measured_copy = _select_measured_copy_row(
                measured_copy_path,
                stat=str(args.measured_copy_stat),
                experts=int(args.measured_copy_experts),
                pinned=str(args.measured_copy_pinned),
            )
            service_us_per_issue = float(measured_copy["copy_us_per_issue"])
            service_us_per_batch = 0.0
            queue_batch_size = int(measured_copy["selected_experts"])
            if int(measured_copy["selected_experts"]) != len(experts):
                failures.append("measured_copy_expert_count_issue_plan_mismatch")
        except Exception as exc:
            failures.append(
                f"measured_copy_select_failed:{exc.__class__.__name__}:{exc}"
            )

    manager = ReadyTimeExpertCacheManager(
        capacity=int(args.capacity),
        service_us_per_issue=service_us_per_issue,
        service_us_per_batch=service_us_per_batch,
        queue_batch_size=queue_batch_size,
        queue_deadline_us=float(args.queue_deadline_us),
    )
    issued = 0
    if not failures:
        issued = manager.issue_prefetches(
            layer_id,
            tuple(experts),
            arrival_us=float(args.issue_arrival_us),
        )
        demand_arrival = float(args.issue_arrival_us) + float(args.demand_gap_us)
        for expert_id in experts:
            manager.demand(layer_id, expert_id, arrival_us=demand_arrival)
        manager.finish()
    snapshot = manager.snapshot()
    snapshot_dict = snapshot.as_dict()

    demand_count = int(snapshot.demand_count)
    issued_count = int(snapshot.issued_fetch_count)
    demand_hit_count = int(snapshot.demand_hit_count)
    ready_late_miss_count = int(snapshot.ready_late_miss_count)
    used_fetch_count = int(snapshot.used_fetch_count)
    demand_hit_rate = _float_rate(demand_hit_count, demand_count)
    ready_late_miss_rate = _float_rate(ready_late_miss_count, demand_count)
    used_per_issued_fetch = _float_rate(used_fetch_count, issued_count)

    if not failures and issued != len(experts):
        failures.append("issued_count_does_not_match_issue_plan")
    if not failures and demand_count != len(experts):
        failures.append("demand_count_does_not_match_issue_plan")
    if demand_hit_rate < float(args.min_demand_hit_rate):
        failures.append("demand_hit_rate_below_threshold")
    if ready_late_miss_rate > float(args.max_ready_late_miss_rate):
        failures.append("ready_late_miss_rate_above_threshold")
    if used_per_issued_fetch < float(args.min_used_per_issued_fetch):
        failures.append("used_per_issued_fetch_below_threshold")

    passed = not failures
    threshold_failure_set = {
        "demand_hit_rate_below_threshold",
        "ready_late_miss_rate_above_threshold",
        "used_per_issued_fetch_below_threshold",
    }
    full_fetch_block_reason = "real_payload_runtime_not_enabled"
    if measured_copy is not None and "measured_copy_expert_count_issue_plan_mismatch" in failures:
        full_fetch_block_reason = "measured_copy_issue_plan_mismatch"
    elif measured_copy is not None and threshold_failure_set.intersection(failures):
        full_fetch_block_reason = "measured_copy_deadline_miss"
    elif any(str(failure).startswith("measured_copy_select_failed") for failure in failures):
        full_fetch_block_reason = "measured_copy_invalid"
    payload = {
        "artifact_kind": ARTIFACT_KIND,
        "executor_name": EXECUTOR_NAME,
        "passed": passed,
        "failures": failures,
        "issue_executor_ready": passed,
        "issue_plan_gate_json": str(gate_path),
        "issue_plan_gate_sha256": _sha256(gate_path),
        "issue_candidate_count": len(experts),
        "issue_candidate_hash": gate.get("issue_candidate_hash"),
        "issue_candidate_experts": experts,
        "layer_id": layer_id,
        "manager_mode": "ready_time",
        "measured_copy_model_enabled": measured_copy is not None,
        "measured_copy_source": None if measured_copy is None else measured_copy["source"],
        "measured_copy_stat": None if measured_copy is None else measured_copy["stat"],
        "measured_copy_selected_experts": (
            None if measured_copy is None else measured_copy["selected_experts"]
        ),
        "measured_copy_pinned": None if measured_copy is None else measured_copy["pinned"],
        "measured_copy_us_per_batch": (
            None if measured_copy is None else measured_copy["copy_us_per_batch"]
        ),
        "measured_copy_us_per_issue": (
            None if measured_copy is None else measured_copy["copy_us_per_issue"]
        ),
        "measured_copy_effective_gbps": (
            None if measured_copy is None else measured_copy["effective_gbps"]
        ),
        "measured_copy_expert_count_matches_issue_plan": (
            None
            if measured_copy is None
            else int(measured_copy["selected_experts"]) == len(experts)
        ),
        "full_fetch_allowed": False,
        "full_fetch_block_reason": full_fetch_block_reason,
        "capacity": int(args.capacity),
        "service_us_per_issue": service_us_per_issue,
        "service_us_per_batch": service_us_per_batch,
        "queue_batch_size": queue_batch_size,
        "queue_deadline_us": float(args.queue_deadline_us),
        "issue_arrival_us": float(args.issue_arrival_us),
        "demand_gap_us": float(args.demand_gap_us),
        "deadline_window_model_only": True,
        "same_arrival_demand_model": (
            float(args.issue_arrival_us) + float(args.demand_gap_us)
            == float(args.issue_arrival_us)
        ),
        "issued_prefetch_count": issued_count,
        "used_fetch_count": used_fetch_count,
        "demand_count": demand_count,
        "demand_hit_count": demand_hit_count,
        "demand_miss_count": int(snapshot.demand_miss_count),
        "demand_hit_rate": demand_hit_rate,
        "ready_late_miss_count": ready_late_miss_count,
        "ready_late_miss_rate": ready_late_miss_rate,
        "ready_time_model_hit_count": demand_hit_count,
        "real_payload_ready_hit_count": 0,
        "used_per_issued_fetch": used_per_issued_fetch,
        "evicted_before_use_count": int(snapshot.evicted_before_use_count),
        "unused_fetch_count": int(snapshot.unused_fetch_count),
        "queue_batch_count": int(snapshot.queue_batch_count),
        "queue_service_us": float(snapshot.queue_service_us),
        "queue_wait_us": float(snapshot.queue_wait_us),
        "queue_max_delay_us": float(snapshot.queue_max_delay_us),
        "queue_total_span_us": float(snapshot.queue_total_span_us),
        "snapshot": snapshot_dict,
        "min_demand_hit_rate": float(args.min_demand_hit_rate),
        "max_ready_late_miss_rate": float(args.max_ready_late_miss_rate),
        "min_used_per_issued_fetch": float(args.min_used_per_issued_fetch),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "next_runtime_stage": "implement_real_payload_cache_manager_or_measured_copy_executor",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-plan-gate-json", type=Path, default=DEFAULT_ISSUE_PLAN_GATE_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--capacity", type=int, default=12288)
    parser.add_argument("--service-us-per-issue", type=float, default=10.0)
    parser.add_argument("--service-us-per-batch", type=float, default=0.0)
    parser.add_argument("--queue-batch-size", type=int, default=8)
    parser.add_argument("--measured-copy-json", type=Path)
    parser.add_argument("--measured-copy-stat", default="p95")
    parser.add_argument("--measured-copy-experts", type=int, default=8)
    parser.add_argument("--measured-copy-pinned", default="true")
    parser.add_argument("--queue-deadline-us", type=float, default=200.0)
    parser.add_argument("--issue-arrival-us", type=float, default=0.0)
    parser.add_argument("--demand-gap-us", type=float, default=0.0)
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.5)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.2)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.5)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_issue_plan_executor(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
