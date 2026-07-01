#!/usr/bin/env python3
"""Build a payload/cache-manager useful-work A/B readiness gate.

The gate binds two separate facts:

1. The payload/cache-manager runtime is still payloadless and blocked at the
   consumer-visible publication boundary.
2. The ready-time cache manager can nevertheless consume exported issue packets
   and perform non-empty issue/demand/hit accounting.

Passing this gate permits a production-like A/B harness to compare manager
overhead or accounting behavior.  It does not permit payload movement, ready
credit, WNA16 kernel argument handoff, or TPOT/performance claims.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USEFUL_WORK_READINESS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_payload_cache"
    / "payload_cache_useful_work_readiness_gate.json"
)
DEFAULT_ISSUE_STREAM_EXECUTOR_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_stream_executor_token_provenance_smoke_v3_lead32_shifted_accounting_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_payload_cache"
    / "payload_cache_manager_useful_work_ab_gate.json"
)

ARTIFACT_KIND = "premap_payload_cache_manager_useful_work_ab_gate"
GATE_MODE = "payload_cache_manager_useful_work_ab_precondition"
NEXT_STAGE = "production_like_payload_cache_manager_ab_harness"
NOOP_FALSE_FIELDS = (
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "full_fetch_runtime_allowed",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
OPTIONAL_NOOP_FALSE_FIELDS = (
    "kernel_arg_pass",
    "full_fetch_runtime_allowed",
    "live_payload_runtime_enabled",
    "payload_transfer_runtime_enabled",
    "payload_deref_runtime_allowed",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _float_metric(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value):
        return None
    return value


def _exact(payload: dict[str, Any], key: str, expected: Any) -> bool:
    value = payload.get(key)
    return type(value) is type(expected) and value == expected


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _validate_optional_false_fields(
    payload: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    for key in OPTIONAL_NOOP_FALSE_FIELDS:
        if key in payload and not _exact(payload, key, False):
            failures.append(f"{prefix}_{key}_mismatch")


def _rate_matches(numerator: int, denominator: int, rate: float) -> bool:
    if denominator <= 0:
        return False
    return math.isclose(rate, numerator / denominator, rel_tol=1.0e-9, abs_tol=1.0e-12)


def _validate_readiness(
    payload: dict[str, Any],
    failures: list[str],
) -> dict[str, Any]:
    prefix = "useful_work_readiness"
    expected = {
        "artifact_kind": "premap_payload_cache_useful_work_readiness_gate",
        "mode": "payload_cache_useful_work_readiness_noop_gate",
        "passed": True,
        "ok": True,
        "failures": [],
        "producer_count_ptr_ready": True,
        "consumer_visible_blocked_ready": True,
        "native_producer_downshifted": True,
        "payload_cache_useful_work_ready": False,
        "payload_cache_useful_work_block_reason": "payload_transfer_disabled",
        "next_stage": "payload_cache_manager_useful_work_ab_or_payload_runtime_canary",
        "payload_bytes": 0,
        "ready": False,
    }
    for key, expected_value in expected.items():
        if not _exact(payload, key, expected_value):
            failures.append(f"{prefix}_{key}_mismatch")
    for key in NOOP_FALSE_FIELDS:
        if not _exact(payload, key, False):
            failures.append(f"{prefix}_{key}_mismatch")
    _validate_optional_false_fields(payload, failures, prefix=prefix)
    producer_packets = _int_metric(payload, "producer_expected_packet_count")
    requested_payload_bytes = _int_metric(payload, "consumer_requested_payload_bytes")
    if producer_packets is None or producer_packets <= 0:
        failures.append(f"{prefix}_producer_expected_packet_count_invalid")
        producer_packets = 0
    if requested_payload_bytes is None or requested_payload_bytes <= 0:
        failures.append(f"{prefix}_consumer_requested_payload_bytes_invalid")
        requested_payload_bytes = 0
    return {
        "producer_expected_packet_count": int(producer_packets or 0),
        "consumer_requested_payload_bytes": int(requested_payload_bytes or 0),
    }


def _validate_executor(
    payload: dict[str, Any],
    failures: list[str],
    *,
    min_demand_hit_rate: float,
    min_used_per_issued_fetch: float,
    min_issue_count: int,
    min_demand_count: int,
    allow_duplicate_shifted_issue_keys: bool,
) -> dict[str, Any]:
    prefix = "issue_stream_executor"
    expected = {
        "artifact_kind": "premap_payload_cache_issue_stream_executor",
        "executor_name": "premap_payload_cache_ready_time_issue_stream_executor_v1",
        "passed": True,
        "failures": [],
        "stream_executor_ready": True,
        "manager_mode": "ready_time_stream",
        "payload_bytes": 0,
        "real_payload_ready_hit_count": 0,
        "full_fetch_allowed": False,
        "full_fetch_block_reason": "real_payload_runtime_not_enabled",
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "shifted_issue_accounting_enabled": True,
        "token_timing_enabled": True,
    }
    for key, expected_value in expected.items():
        if not _exact(payload, key, expected_value):
            failures.append(f"{prefix}_{key}_mismatch")
    _validate_optional_false_fields(payload, failures, prefix=prefix)
    issued_payload_count_source = "legacy_missing"
    if "issued_payload_count" in payload:
        issued_payload_count_source = "explicit"
        if not _exact(payload, "issued_payload_count", 0):
            failures.append(f"{prefix}_issued_payload_count_mismatch")
    issue_count = _int_metric(payload, "issued_prefetch_count")
    packet_count_present = "packet_count" in payload
    packet_count = _int_metric(payload, "packet_count")
    packet_count_source = "explicit" if packet_count_present else "legacy_missing"
    requested_issue_count = _int_metric(payload, "requested_issue_count")
    demand_count = _int_metric(payload, "demand_count")
    demand_hit_count = _int_metric(payload, "demand_hit_count")
    demand_hit_rate = _float_metric(payload, "demand_hit_rate")
    used_fetch_count = _int_metric(payload, "used_fetch_count")
    unused_fetch_count = _int_metric(payload, "unused_fetch_count")
    used_per_issued_fetch = _float_metric(payload, "used_per_issued_fetch")
    ready_late_miss_rate = _float_metric(payload, "ready_late_miss_rate")
    queue_batch_size = _int_metric(payload, "queue_batch_size")
    if issue_count is None or issue_count < int(min_issue_count):
        failures.append(f"{prefix}_issued_prefetch_count_too_low")
        issue_count = 0
    if packet_count_present and (packet_count is None or packet_count <= 0):
        failures.append(f"{prefix}_packet_count_invalid")
        packet_count = 0
    elif not packet_count_present:
        packet_count = 0
    if requested_issue_count is None or requested_issue_count <= 0:
        failures.append(f"{prefix}_requested_issue_count_invalid")
        requested_issue_count = 0
    if demand_count is None or demand_count < int(min_demand_count):
        failures.append(f"{prefix}_demand_count_too_low")
        demand_count = 0
    if demand_hit_count is None or demand_hit_count <= 0:
        failures.append(f"{prefix}_demand_hit_count_invalid")
        demand_hit_count = 0
    if used_fetch_count is None or used_fetch_count <= 0:
        failures.append(f"{prefix}_used_fetch_count_invalid")
        used_fetch_count = 0
    if unused_fetch_count is None or unused_fetch_count < 0:
        failures.append(f"{prefix}_unused_fetch_count_invalid")
        unused_fetch_count = 0
    if demand_hit_rate is None or demand_hit_rate < float(min_demand_hit_rate):
        failures.append(f"{prefix}_demand_hit_rate_below_threshold")
        demand_hit_rate = 0.0
    if (
        used_per_issued_fetch is None
        or used_per_issued_fetch < float(min_used_per_issued_fetch)
    ):
        failures.append(f"{prefix}_used_per_issued_fetch_below_threshold")
        used_per_issued_fetch = 0.0
    if ready_late_miss_rate is None or ready_late_miss_rate < 0.0:
        failures.append(f"{prefix}_ready_late_miss_rate_invalid")
        ready_late_miss_rate = 0.0
    if queue_batch_size is None or queue_batch_size <= 0:
        failures.append(f"{prefix}_queue_batch_size_invalid")
        queue_batch_size = 0
    shifted_issue_duplicate_issue_key_count = _int_metric(
        payload,
        "shifted_issue_duplicate_issue_key_count",
    )
    if shifted_issue_duplicate_issue_key_count is None:
        failures.append(f"{prefix}_shifted_issue_duplicate_issue_key_count_invalid")
        shifted_issue_duplicate_issue_key_count = 0
    elif shifted_issue_duplicate_issue_key_count < 0:
        failures.append(f"{prefix}_shifted_issue_duplicate_issue_key_count_invalid")
        shifted_issue_duplicate_issue_key_count = 0
    if (
        shifted_issue_duplicate_issue_key_count != 0
        and not allow_duplicate_shifted_issue_keys
    ):
        failures.append(f"{prefix}_shifted_issue_duplicate_issue_key_count_nonzero")
    if issue_count is not None and requested_issue_count is not None:
        if issue_count > requested_issue_count:
            failures.append(f"{prefix}_issued_prefetch_count_exceeds_requested")
    if (
        issue_count is not None
        and used_fetch_count is not None
        and unused_fetch_count is not None
    ):
        if used_fetch_count + unused_fetch_count != issue_count:
            failures.append(f"{prefix}_used_unused_fetch_count_incoherent")
    if (
        issue_count is not None
        and used_fetch_count is not None
        and used_per_issued_fetch is not None
    ):
        if not _rate_matches(used_fetch_count, issue_count, used_per_issued_fetch):
            failures.append(f"{prefix}_used_per_issued_fetch_incoherent")
    if demand_hit_count is not None and demand_count is not None:
        if demand_hit_count > demand_count:
            failures.append(f"{prefix}_demand_hit_count_exceeds_demand_count")
    if demand_hit_count is not None and demand_count is not None and demand_hit_rate is not None:
        if not _rate_matches(demand_hit_count, demand_count, demand_hit_rate):
            failures.append(f"{prefix}_demand_hit_rate_incoherent")
    if demand_hit_rate is not None and not (0.0 <= demand_hit_rate <= 1.0):
        failures.append(f"{prefix}_demand_hit_rate_out_of_range")
    if used_per_issued_fetch is not None and not (0.0 <= used_per_issued_fetch <= 1.0):
        failures.append(f"{prefix}_used_per_issued_fetch_out_of_range")
    if ready_late_miss_rate is not None and not (0.0 <= ready_late_miss_rate <= 1.0):
        failures.append(f"{prefix}_ready_late_miss_rate_out_of_range")
    return {
        "issued_prefetch_count": int(issue_count or 0),
        "issued_payload_count": 0,
        "issued_payload_count_source": issued_payload_count_source,
        "used_fetch_count": int(used_fetch_count or 0),
        "unused_fetch_count": int(unused_fetch_count or 0),
        "packet_count": int(packet_count or 0),
        "packet_count_source": packet_count_source,
        "requested_issue_count": int(requested_issue_count or 0),
        "demand_count": int(demand_count or 0),
        "demand_hit_count": int(demand_hit_count or 0),
        "demand_hit_rate": float(demand_hit_rate or 0.0),
        "used_per_issued_fetch": float(used_per_issued_fetch or 0.0),
        "ready_late_miss_rate": float(ready_late_miss_rate or 0.0),
        "queue_batch_size": int(queue_batch_size or 0),
        "shifted_issue_duplicate_issue_key_count": int(
            shifted_issue_duplicate_issue_key_count or 0,
        ),
        "allow_duplicate_shifted_issue_keys": bool(
            allow_duplicate_shifted_issue_keys,
        ),
    }


def build_gate(
    *,
    useful_work_readiness_json: Path,
    issue_stream_executor_json: Path,
    min_demand_hit_rate: float,
    min_used_per_issued_fetch: float,
    min_issue_count: int,
    min_demand_count: int,
    require_same_source_packet_budget: bool = False,
    allow_duplicate_shifted_issue_keys: bool = False,
) -> dict[str, Any]:
    readiness_payload = _load_json(useful_work_readiness_json)
    executor_payload = _load_json(issue_stream_executor_json)
    failures: list[str] = []
    if not math.isfinite(min_demand_hit_rate) or min_demand_hit_rate < 0.0:
        failures.append("min_demand_hit_rate_invalid")
    if (
        not math.isfinite(min_used_per_issued_fetch)
        or min_used_per_issued_fetch < 0.0
    ):
        failures.append("min_used_per_issued_fetch_invalid")
    if min_issue_count < 0:
        failures.append("min_issue_count_invalid")
    if min_demand_count < 0:
        failures.append("min_demand_count_invalid")
    readiness = _validate_readiness(readiness_payload, failures)
    executor = _validate_executor(
        executor_payload,
        failures,
        min_demand_hit_rate=min_demand_hit_rate,
        min_used_per_issued_fetch=min_used_per_issued_fetch,
        min_issue_count=min_issue_count,
        min_demand_count=min_demand_count,
        allow_duplicate_shifted_issue_keys=bool(allow_duplicate_shifted_issue_keys),
    )
    producer_expected_packet_count = int(readiness["producer_expected_packet_count"])
    executor_packet_count = int(executor["packet_count"])
    executor_requested_issue_count = int(executor["requested_issue_count"])
    source_binding_same_packet_budget = (
        producer_expected_packet_count > 0
        and executor_packet_count > 0
        and producer_expected_packet_count == executor_packet_count
    )
    source_binding_status = (
        "same_packet_budget"
        if source_binding_same_packet_budget
        else "mixed_source_accounting_only"
    )
    if require_same_source_packet_budget and not source_binding_same_packet_budget:
        failures.append("source_binding_packet_budget_mismatch")
    if require_same_source_packet_budget and executor_packet_count <= 0:
        failures.append("source_binding_executor_packet_count_invalid")
    passed = not failures
    return {
        "artifact_kind": ARTIFACT_KIND,
        "mode": GATE_MODE,
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "manager_useful_work_ab_ready": passed,
        "payload_runtime_ready": False,
        "payload_runtime_block_reason": "payload_transfer_disabled",
        "performance_claim_ready": False,
        "next_stage": NEXT_STAGE,
        "producer_expected_packet_count": producer_expected_packet_count,
        "consumer_requested_payload_bytes": readiness["consumer_requested_payload_bytes"],
        "issued_prefetch_count": executor["issued_prefetch_count"],
        "issued_payload_count": executor["issued_payload_count"],
        "issued_payload_count_source": executor["issued_payload_count_source"],
        "executor_packet_count": executor_packet_count,
        "executor_packet_count_source": executor["packet_count_source"],
        "requested_issue_count": executor["requested_issue_count"],
        "source_binding_packet_budget_kind": (
            "producer_expected_packet_count_vs_executor_packet_count"
        ),
        "source_binding_status": source_binding_status,
        "source_binding_same_packet_budget": source_binding_same_packet_budget,
        "source_binding_require_same_packet_budget": bool(
            require_same_source_packet_budget,
        ),
        "source_binding_producer_expected_packet_count": producer_expected_packet_count,
        "source_binding_executor_packet_count": executor_packet_count,
        "source_binding_executor_requested_issue_count": executor_requested_issue_count,
        "demand_count": executor["demand_count"],
        "demand_hit_count": executor["demand_hit_count"],
        "demand_hit_rate": executor["demand_hit_rate"],
        "used_fetch_count": executor["used_fetch_count"],
        "unused_fetch_count": executor["unused_fetch_count"],
        "used_per_issued_fetch": executor["used_per_issued_fetch"],
        "ready_late_miss_rate": executor["ready_late_miss_rate"],
        "queue_batch_size": executor["queue_batch_size"],
        "shifted_issue_duplicate_issue_key_count": executor[
            "shifted_issue_duplicate_issue_key_count"
        ],
        "allow_duplicate_shifted_issue_keys": executor[
            "allow_duplicate_shifted_issue_keys"
        ],
        "payload_bytes": 0,
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
        "useful_work_readiness_json": _display_path(useful_work_readiness_json),
        "issue_stream_executor_json": _display_path(issue_stream_executor_json),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--useful-work-readiness-json",
        type=Path,
        default=DEFAULT_USEFUL_WORK_READINESS_JSON,
    )
    parser.add_argument(
        "--issue-stream-executor-json",
        type=Path,
        default=DEFAULT_ISSUE_STREAM_EXECUTOR_JSON,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.50)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.50)
    parser.add_argument("--min-issue-count", type=int, default=1)
    parser.add_argument("--min-demand-count", type=int, default=1)
    parser.add_argument(
        "--require-same-source-packet-budget",
        action="store_true",
        help=(
            "Require producer_expected_packet_count and executor packet_count to "
            "match. Default is false so existing mixed-source accounting evidence "
            "remains accepted but explicitly labeled."
        ),
    )
    parser.add_argument(
        "--allow-duplicate-shifted-issue-keys",
        action="store_true",
        help=(
            "Allow duplicate shifted issue keys after lead-window clamping. "
            "The gate still requires demand-hit, ready-late-miss, and "
            "used-per-issued thresholds to pass."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_gate(
        useful_work_readiness_json=args.useful_work_readiness_json,
        issue_stream_executor_json=args.issue_stream_executor_json,
        min_demand_hit_rate=float(args.min_demand_hit_rate),
        min_used_per_issued_fetch=float(args.min_used_per_issued_fetch),
        min_issue_count=int(args.min_issue_count),
        min_demand_count=int(args.min_demand_count),
        require_same_source_packet_budget=bool(args.require_same_source_packet_budget),
        allow_duplicate_shifted_issue_keys=bool(
            args.allow_duplicate_shifted_issue_keys
        ),
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
