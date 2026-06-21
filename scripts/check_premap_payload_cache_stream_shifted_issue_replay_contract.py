#!/usr/bin/env python3
"""Check a token-shifted producer issue replay contract.

This checker validates the artifact emitted by
``build_premap_payload_cache_stream_shifted_issue_replay_contract.py``.  It is a
producer-side schedule contract gate only: payload movement, ready credit,
kernel argument passing, current WNA16 arg use, and endpoint timing must remain
disabled.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SAFE_FALSE_FIELDS = (
    "full_fetch_runtime_allowed",
    "full_fetch_allowed",
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
    "current_wna16_arg_compatible",
    "requires_wna16_arg_reinterpretation",
    "wna16_benchmark_ready",
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


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return int(value) if _is_int(value) else None


def _valid_zero(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return math.isfinite(value) and value == 0.0
    return int(value) == 0


def check_shifted_issue_replay_contract(
    payload: dict[str, Any],
    *,
    required_issue_lead_tokens: int | None = None,
    min_schedulable_packet_count: int = 1,
    require_pass: bool = True,
    require_bootstrap_clamp: bool = False,
    require_issue_key_coalescing: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []

    if payload.get("artifact_kind") != "premap_payload_cache_stream_shifted_issue_replay_contract":
        failures.append("artifact_kind_mismatch")
    passed_value = payload.get("passed")
    if not isinstance(passed_value, bool):
        failures.append("passed_not_bool")
        passed = False
    else:
        passed = passed_value
    raw_failures = payload.get("failures")
    if raw_failures is None:
        raw_failures = []
    if not isinstance(raw_failures, list) or not all(
        isinstance(item, str) for item in raw_failures
    ):
        failures.append("failures_not_string_list")
        raw_failures = []
    if require_pass:
        if not passed:
            failures.append("contract_not_passed")
        if raw_failures:
            failures.append("contract_failures_not_empty")

    issue_lead_tokens = _optional_int(payload, "issue_lead_tokens")
    if issue_lead_tokens is None or issue_lead_tokens < 0:
        failures.append("issue_lead_tokens_invalid")
    elif (
        required_issue_lead_tokens is not None
        and issue_lead_tokens != int(required_issue_lead_tokens)
    ):
        failures.append("issue_lead_tokens_mismatch")

    packet_count = _optional_int(payload, "packet_count")
    schedulable = _optional_int(payload, "schedulable_packet_count")
    empty_exempt = _optional_int(payload, "empty_issue_exempt_count")
    clamped = _optional_int(payload, "clamped_issue_count")
    duplicate_demand = _optional_int(payload, "duplicate_demand_key_count")
    duplicate_issue = _optional_int(payload, "duplicate_issue_key_count")
    unique_demand = _optional_int(payload, "unique_demand_key_count")
    unique_issue = _optional_int(payload, "unique_issue_key_count")
    total_candidates = _optional_int(payload, "total_issue_candidates")
    issue_hash_count = _optional_int(payload, "issue_hash_count")

    for key, value in (
        ("packet_count", packet_count),
        ("schedulable_packet_count", schedulable),
        ("empty_issue_exempt_count", empty_exempt),
        ("clamped_issue_count", clamped),
        ("duplicate_demand_key_count", duplicate_demand),
        ("duplicate_issue_key_count", duplicate_issue),
        ("unique_demand_key_count", unique_demand),
        ("unique_issue_key_count", unique_issue),
        ("total_issue_candidates", total_candidates),
        ("issue_hash_count", issue_hash_count),
    ):
        if value is None or value < 0:
            failures.append(f"{key}_invalid")

    if schedulable is not None and schedulable < int(min_schedulable_packet_count):
        failures.append(f"schedulable_packet_count_below_min:{schedulable}")
    if packet_count is not None and schedulable is not None and empty_exempt is not None:
        if schedulable + empty_exempt > packet_count:
            failures.append("packet_count_accounting_overflow")
    if duplicate_demand not in (0, None):
        failures.append(f"duplicate_demand_key_count_nonzero:{duplicate_demand}")
    if unique_demand is not None and schedulable is not None:
        if unique_demand != schedulable:
            failures.append("unique_demand_key_count_mismatch")
    if total_candidates is not None and schedulable is not None:
        if total_candidates <= 0 and schedulable > 0:
            failures.append("total_issue_candidates_nonpositive")
    if issue_hash_count is not None and schedulable is not None:
        if issue_hash_count != schedulable:
            failures.append("issue_hash_count_mismatch")

    allow_clamped = payload.get("allow_clamped_issue_tokens")
    allow_duplicate_issue = payload.get("allow_duplicate_issue_keys")
    if require_bootstrap_clamp:
        if allow_clamped is not True:
            failures.append("bootstrap_clamp_not_allowed")
        if clamped is None or clamped <= 0:
            failures.append("clamped_issue_count_not_positive")
    elif clamped not in (0, None):
        failures.append(f"clamped_issue_count_nonzero:{clamped}")

    if require_issue_key_coalescing:
        if allow_duplicate_issue is not True:
            failures.append("issue_key_coalescing_not_allowed")
        if duplicate_issue is None or duplicate_issue <= 0:
            failures.append("duplicate_issue_key_count_not_positive")
        if (
            unique_issue is not None
            and schedulable is not None
            and unique_issue >= schedulable
        ):
            failures.append("issue_key_coalescing_not_observed")
    elif duplicate_issue not in (0, None):
        failures.append(f"duplicate_issue_key_count_nonzero:{duplicate_issue}")
    if (
        require_issue_key_coalescing
        and duplicate_issue is not None
        and unique_issue is not None
        and schedulable is not None
        and unique_issue + duplicate_issue != schedulable
    ):
        failures.append("issue_key_coalescing_accounting_mismatch")

    payload_bytes = payload.get("payload_bytes")
    if not _valid_zero(payload_bytes):
        failures.append("payload_bytes_not_strict_zero")
    for field in SAFE_FALSE_FIELDS:
        if payload.get(field) is not False:
            failures.append(f"{field}_not_false")

    rows = payload.get("rows")
    row_count = len(rows) if isinstance(rows, list) else None
    if row_count is None:
        failures.append("rows_not_list")
    elif schedulable is not None and row_count != schedulable:
        failures.append("rows_schedulable_count_mismatch")
    row_clamped_count = 0
    row_duplicate_demand_key_count = 0
    row_duplicate_issue_key_count = 0
    row_unique_demand_key_count = 0
    row_unique_issue_key_count = 0
    row_shift_relation_mismatch_count = 0
    row_clamp_relation_mismatch_count = 0
    if isinstance(rows, list):
        demand_keys: set[tuple[Any, Any, Any, Any, Any]] = set()
        issue_keys: set[tuple[Any, Any, Any, Any, Any]] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                failures.append(f"row_{index}_not_object")
                continue
            demand_token_index = row.get("demand_token_index")
            issue_token_index = row.get("issue_token_index")
            issue_clamped_to_zero = row.get("issue_clamped_to_zero")
            if issue_clamped_to_zero is True:
                row_clamped_count += 1
            if not _is_int(demand_token_index):
                failures.append(f"row_{index}_demand_token_index_invalid")
            if not _is_int(issue_token_index):
                failures.append(f"row_{index}_issue_token_index_invalid")
            if not isinstance(issue_clamped_to_zero, bool):
                failures.append(f"row_{index}_issue_clamped_to_zero_not_bool")
            if (
                issue_lead_tokens is not None
                and issue_lead_tokens >= 0
                and _is_int(demand_token_index)
                and _is_int(issue_token_index)
                and isinstance(issue_clamped_to_zero, bool)
            ):
                expected_issue_token_index = max(
                    0,
                    int(demand_token_index) - int(issue_lead_tokens),
                )
                expected_clamped = int(demand_token_index) - int(issue_lead_tokens) < 0
                if int(issue_token_index) != expected_issue_token_index:
                    row_shift_relation_mismatch_count += 1
                    failures.append(f"row_{index}_issue_token_shift_mismatch")
                if bool(issue_clamped_to_zero) is not expected_clamped:
                    row_clamp_relation_mismatch_count += 1
                    failures.append(f"row_{index}_issue_clamp_mismatch")
            demand_key = (
                row.get("sample_idx"),
                row.get("record_id"),
                row.get("sequence_id"),
                row.get("layer_id"),
                demand_token_index,
            )
            issue_key = (
                row.get("sample_idx"),
                row.get("record_id"),
                row.get("sequence_id"),
                row.get("layer_id"),
                issue_token_index,
            )
            if any(value is None for value in demand_key):
                failures.append(f"row_{index}_demand_key_incomplete")
            elif demand_key in demand_keys:
                row_duplicate_demand_key_count += 1
            demand_keys.add(demand_key)
            if any(value is None for value in issue_key):
                failures.append(f"row_{index}_issue_key_incomplete")
                continue
            if issue_key in issue_keys:
                row_duplicate_issue_key_count += 1
            issue_keys.add(issue_key)
        row_unique_demand_key_count = len(demand_keys)
        row_unique_issue_key_count = len(issue_keys)
    if clamped is not None and row_clamped_count != clamped:
        failures.append("row_clamped_issue_count_mismatch")
    if (
        duplicate_demand is not None
        and row_duplicate_demand_key_count != duplicate_demand
    ):
        failures.append("row_duplicate_demand_key_count_mismatch")
    if duplicate_issue is not None and row_duplicate_issue_key_count != duplicate_issue:
        failures.append("row_duplicate_issue_key_count_mismatch")
    if unique_demand is not None and row_unique_demand_key_count != unique_demand:
        failures.append("row_unique_demand_key_count_mismatch")
    if unique_issue is not None and row_unique_issue_key_count != unique_issue:
        failures.append("row_unique_issue_key_count_mismatch")

    return {
        "artifact_kind": "premap_payload_cache_stream_shifted_issue_replay_contract_check",
        "passed": not failures,
        "failures": failures,
        "source_passed": passed if isinstance(passed_value, bool) else None,
        "source_failures": raw_failures,
        "issue_lead_tokens": issue_lead_tokens,
        "packet_count": packet_count,
        "schedulable_packet_count": schedulable,
        "empty_issue_exempt_count": empty_exempt,
        "clamped_issue_count": clamped,
        "duplicate_demand_key_count": duplicate_demand,
        "duplicate_issue_key_count": duplicate_issue,
        "unique_demand_key_count": unique_demand,
        "unique_issue_key_count": unique_issue,
        "row_clamped_issue_count": row_clamped_count,
        "row_duplicate_demand_key_count": row_duplicate_demand_key_count,
        "row_duplicate_issue_key_count": row_duplicate_issue_key_count,
        "row_unique_demand_key_count": row_unique_demand_key_count,
        "row_unique_issue_key_count": row_unique_issue_key_count,
        "row_shift_relation_mismatch_count": row_shift_relation_mismatch_count,
        "row_clamp_relation_mismatch_count": row_clamp_relation_mismatch_count,
        "total_issue_candidates": total_candidates,
        "issue_hash_count": issue_hash_count,
        "require_bootstrap_clamp": bool(require_bootstrap_clamp),
        "require_issue_key_coalescing": bool(require_issue_key_coalescing),
        "source_full_fetch_runtime_allowed": payload.get("full_fetch_runtime_allowed"),
        "source_full_fetch_allowed": payload.get("full_fetch_allowed"),
        "source_payload_bytes": payload.get("payload_bytes"),
        "source_ready_credit": payload.get("ready_credit"),
        "source_ready_before_demand_credit": payload.get("ready_before_demand_credit"),
        "source_real_ready_credit_granted": payload.get("real_ready_credit_granted"),
        "source_payload_transfer_enabled": payload.get("payload_transfer_enabled"),
        "source_payload_deref_allowed": payload.get("payload_deref_allowed"),
        "source_kernel_arg_pass_allowed": payload.get("kernel_arg_pass_allowed"),
        "source_passed_to_kernel": payload.get("passed_to_kernel"),
        "source_changes_kernel_launch_args": payload.get("changes_kernel_launch_args"),
        "source_uses_current_wna16_args": payload.get("uses_current_wna16_args"),
        "source_passes_current_wna16_args": payload.get("passes_current_wna16_args"),
        "source_current_wna16_arg_compatible": payload.get(
            "current_wna16_arg_compatible"
        ),
        "source_requires_wna16_arg_reinterpretation": payload.get(
            "requires_wna16_arg_reinterpretation"
        ),
        "source_wna16_benchmark_ready": payload.get("wna16_benchmark_ready"),
        "source_measures_tpot": payload.get("measures_tpot"),
        "source_measures_vllm_latency": payload.get("measures_vllm_latency"),
        "full_fetch_runtime_allowed": False,
        "full_fetch_allowed": False,
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
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "wna16_benchmark_ready": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "boundary": (
            "shifted producer issue replay contract check only; no payload "
            "movement, ready credit, kernel arg pass, or endpoint latency"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract_json", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--required-issue-lead-tokens", type=int)
    parser.add_argument("--min-schedulable-packet-count", type=int, default=1)
    parser.add_argument("--allow-failing-contract", action="store_true")
    parser.add_argument("--require-bootstrap-clamp", action="store_true")
    parser.add_argument("--require-issue-key-coalescing", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _load_json(args.contract_json)
    result = check_shifted_issue_replay_contract(
        payload,
        required_issue_lead_tokens=args.required_issue_lead_tokens,
        min_schedulable_packet_count=args.min_schedulable_packet_count,
        require_pass=not bool(args.allow_failing_contract),
        require_bootstrap_clamp=bool(args.require_bootstrap_clamp),
        require_issue_key_coalescing=bool(args.require_issue_key_coalescing),
    )
    result["contract_json"] = str(args.contract_json)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not bool(result["passed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
