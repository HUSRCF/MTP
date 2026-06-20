#!/usr/bin/env python3
"""Check online shifted-issue runtime shadow evidence.

This gate validates that an online vLLM run wrote the token-shifted producer
issue summary into ``performance_summary.json``.  It is an audit gate only:
payload movement, ready credit, kernel argument passing, and endpoint timing
claims must remain disabled.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SAFE_FALSE_FIELDS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _is_int(value: Any) -> bool:
    return type(value) is int


def _required_int(
    summary: dict[str, Any],
    key: str,
    failures: list[str],
) -> int:
    if key not in summary:
        failures.append(f"{key}_missing")
        return 0
    value = summary.get(key)
    if not _is_int(value):
        failures.append(f"{key}_not_int")
        return 0
    return int(value)


def _valid_zero(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return math.isfinite(value) and value == 0.0
    return int(value) == 0


def check_summary(
    summary: dict[str, Any],
    *,
    min_packet_count: int = 1,
    min_schedulable_packet_count: int = 1,
    required_issue_lead_tokens: int | None = None,
    require_no_clamp: bool = True,
    require_no_demand_duplicates: bool = True,
    require_no_issue_duplicates: bool = True,
) -> dict[str, Any]:
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    failures: list[str] = []

    enabled = summary.get(f"{prefix}runtime_shadow_enabled")
    if enabled is None:
        enabled = summary.get(f"{prefix}enabled")
    if enabled is not True:
        failures.append("shifted_issue_runtime_shadow_not_enabled")

    issue_lead_tokens = summary.get(f"{prefix}issue_lead_tokens")
    if not _is_int(issue_lead_tokens) or int(issue_lead_tokens) < 0:
        failures.append("issue_lead_tokens_invalid")
    elif (
        required_issue_lead_tokens is not None
        and int(issue_lead_tokens) != int(required_issue_lead_tokens)
    ):
        failures.append("issue_lead_tokens_mismatch")

    packet_count = _required_int(summary, f"{prefix}packet_count", failures)
    schedulable_packet_count = _required_int(
        summary, f"{prefix}schedulable_packet_count", failures
    )
    empty_issue_exempt_count = _required_int(
        summary, f"{prefix}empty_issue_exempt_count", failures
    )
    safe_packet_count = _required_int(summary, f"{prefix}safe_packet_count", failures)
    unsafe_packet_count = _required_int(
        summary, f"{prefix}unsafe_packet_count", failures
    )
    invalid_packet_count = _required_int(
        summary, f"{prefix}invalid_packet_count", failures
    )
    scan_error_count = _required_int(summary, f"{prefix}scan_error_count", failures)
    clamped_issue_count = _required_int(
        summary, f"{prefix}clamped_issue_count", failures
    )
    duplicate_demand_key_count = _required_int(
        summary, f"{prefix}duplicate_demand_key_count", failures
    )
    duplicate_issue_key_count = _required_int(
        summary, f"{prefix}duplicate_issue_key_count", failures
    )
    unique_demand_key_count = _required_int(
        summary, f"{prefix}unique_demand_key_count", failures
    )
    unique_issue_key_count = _required_int(
        summary, f"{prefix}unique_issue_key_count", failures
    )
    total_issue_candidates = _required_int(
        summary, f"{prefix}total_issue_candidates", failures
    )
    issue_hash_count = _required_int(summary, f"{prefix}issue_hash_count", failures)
    issue_hash_unique_count = _required_int(
        summary, f"{prefix}issue_hash_unique_count", failures
    )

    if packet_count < int(min_packet_count):
        failures.append(f"packet_count_below_min:{packet_count}")
    if schedulable_packet_count < int(min_schedulable_packet_count):
        failures.append(
            f"schedulable_packet_count_below_min:{schedulable_packet_count}"
        )
    if safe_packet_count != packet_count:
        failures.append("safe_packet_count_not_equal_packet_count")
    if unsafe_packet_count != 0:
        failures.append(f"unsafe_packet_count_nonzero:{unsafe_packet_count}")
    if invalid_packet_count != 0:
        failures.append(f"invalid_packet_count_nonzero:{invalid_packet_count}")
    if scan_error_count != 0:
        failures.append(f"scan_error_count_nonzero:{scan_error_count}")
    if require_no_clamp and clamped_issue_count != 0:
        failures.append(f"clamped_issue_count_nonzero:{clamped_issue_count}")
    if require_no_demand_duplicates and duplicate_demand_key_count != 0:
        failures.append(
            f"duplicate_demand_key_count_nonzero:{duplicate_demand_key_count}"
        )
    if require_no_issue_duplicates and duplicate_issue_key_count != 0:
        failures.append(
            f"duplicate_issue_key_count_nonzero:{duplicate_issue_key_count}"
        )
    if (
        require_no_demand_duplicates
        and unique_demand_key_count != schedulable_packet_count
    ):
        failures.append("unique_demand_key_count_mismatch")
    if (
        require_no_issue_duplicates
        and unique_issue_key_count != schedulable_packet_count
    ):
        failures.append("unique_issue_key_count_mismatch")
    if total_issue_candidates <= 0 and schedulable_packet_count > 0:
        failures.append("total_issue_candidates_nonpositive")
    if issue_hash_count != schedulable_packet_count:
        failures.append("issue_hash_count_mismatch")
    if schedulable_packet_count + empty_issue_exempt_count > packet_count:
        failures.append("packet_count_accounting_overflow")

    payload_bytes = summary.get(f"{prefix}payload_bytes")
    if not _valid_zero(payload_bytes):
        failures.append("payload_bytes_not_strict_zero")
    for field in SAFE_FALSE_FIELDS:
        if summary.get(f"{prefix}{field}") is not False:
            failures.append(f"{field}_not_false")

    return {
        "artifact_kind": "premap_payload_cache_shifted_issue_runtime_shadow_gate",
        "passed": not failures,
        "failures": failures,
        "issue_lead_tokens": issue_lead_tokens if _is_int(issue_lead_tokens) else None,
        "packet_count": packet_count,
        "schedulable_packet_count": schedulable_packet_count,
        "empty_issue_exempt_count": empty_issue_exempt_count,
        "safe_packet_count": safe_packet_count,
        "unsafe_packet_count": unsafe_packet_count,
        "invalid_packet_count": invalid_packet_count,
        "scan_error_count": scan_error_count,
        "clamped_issue_count": clamped_issue_count,
        "duplicate_demand_key_count": duplicate_demand_key_count,
        "duplicate_issue_key_count": duplicate_issue_key_count,
        "unique_demand_key_count": unique_demand_key_count,
        "unique_issue_key_count": unique_issue_key_count,
        "total_issue_candidates": total_issue_candidates,
        "issue_hash_count": issue_hash_count,
        "issue_hash_unique_count": issue_hash_unique_count,
        "full_fetch_runtime_allowed": False,
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
        "boundary": (
            "online shifted-issue runtime shadow gate only; no payload movement, "
            "ready credit, kernel arg pass, or endpoint latency"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("performance_summary", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--min-packet-count", type=int, default=1)
    parser.add_argument("--min-schedulable-packet-count", type=int, default=1)
    parser.add_argument("--required-issue-lead-tokens", type=int)
    parser.add_argument("--allow-clamped-issue-tokens", action="store_true")
    parser.add_argument("--allow-duplicate-issue-keys", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = _load_json(args.performance_summary)
    payload = check_summary(
        summary,
        min_packet_count=args.min_packet_count,
        min_schedulable_packet_count=args.min_schedulable_packet_count,
        required_issue_lead_tokens=args.required_issue_lead_tokens,
        require_no_clamp=not bool(args.allow_clamped_issue_tokens),
        require_no_demand_duplicates=True,
        require_no_issue_duplicates=not bool(args.allow_duplicate_issue_keys),
    )
    payload["performance_summary"] = str(args.performance_summary)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not bool(payload["passed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
