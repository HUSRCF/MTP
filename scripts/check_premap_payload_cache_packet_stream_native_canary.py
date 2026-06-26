#!/usr/bin/env python3
"""Check a manifest-backed packet-stream native producer-state canary artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SAFE_FALSE_FIELDS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
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


def _int_at_least(value: Any, minimum: int) -> bool:
    return type(value) is int and value >= minimum


def _zero_int(value: Any) -> bool:
    return type(value) is int and value == 0


def _hex64_string(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 16:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_safety(
    payload: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    value = payload.get("payload_bytes")
    if not _zero_int(value):
        failures.append(f"{prefix}payload_bytes_mismatch")
    for field in SAFE_FALSE_FIELDS:
        if payload.get(field) is not False:
            failures.append(f"{prefix}{field}_not_false")


def check_packet_stream_native_canary(
    payload: dict[str, Any],
    *,
    min_packet_count: int = 1,
    min_issue_candidate_count: int = 1,
) -> dict[str, Any]:
    failures: list[str] = []
    if payload.get("mode") != "payload_cache_producer_state_packet_stream_native_canary":
        failures.append("mode_mismatch")
    if payload.get("passed") is not True or payload.get("ok") is not True:
        failures.append("report_not_passed")
    if payload.get("failures") != []:
        failures.append("report_failures_not_empty")
    native_runtime_blocked = payload.get("native_runtime_blocked") is True
    if native_runtime_blocked:
        failures.append("native_runtime_blocked")
    _check_safety(payload, failures, prefix="")

    materialized = payload.get("materialized")
    if not isinstance(materialized, dict):
        failures.append("materialized_missing")
        materialized = {}
    elif materialized.get("passed") is not True:
        failures.append("materialized_not_passed")
    if materialized.get("failures") != []:
        failures.append("materialized_failures_not_empty")

    native = payload.get("native")
    if native_runtime_blocked:
        return {
            "passed": False,
            "failures": failures,
            "mode": "premap_payload_cache_packet_stream_native_canary_check",
            "min_packet_count": int(min_packet_count),
            "min_issue_candidate_count": int(min_issue_candidate_count),
            "packet_count": None,
            "issue_candidate_count": None,
            "issue_candidate_hash": None,
            "expected_issue_candidate_hash": None,
            "expected_issue_candidate_count": None,
            "previous_nonempty_packet_count": None,
            "state_override_count": None,
            "state_mismatch_count": None,
            "issue_expert_mismatch_count": None,
            "native_graph_replay": None,
            "native_runtime_blocked": True,
            "payload_bytes": payload.get("payload_bytes"),
            "ready_credit": payload.get("ready_credit"),
            "kernel_arg_pass": payload.get("kernel_arg_pass"),
            "passed_to_kernel": payload.get("passed_to_kernel"),
            "changes_kernel_launch_args": payload.get("changes_kernel_launch_args"),
            "uses_current_wna16_args": payload.get("uses_current_wna16_args"),
            "passes_current_wna16_args": payload.get("passes_current_wna16_args"),
            "materialized_packet_count": materialized.get("packet_count"),
            "materialized_state_override_count": materialized.get(
                "state_override_count"
            ),
            "materialized_expected_issue_candidate_count": materialized.get(
                "expected_issue_candidate_count"
            ),
            "materialized_expected_issue_candidate_hash": materialized.get(
                "expected_issue_candidate_hash"
            ),
            "materialized_expected_previous_nonempty_packet_count": materialized.get(
                "expected_previous_nonempty_packet_count"
            ),
        }

    if not isinstance(native, dict):
        failures.append("native_missing")
        native = {}
    else:
        if native.get("passed") is not True or native.get("ok") is not True:
            failures.append("native_not_passed")
        if native.get("failures") != []:
            failures.append("native_failures_not_empty")
        _check_safety(native, failures, prefix="native_")
        if not _zero_int(native.get("native_returncode")):
            failures.append("native_returncode_nonzero")
        if native.get("native_graph_replay") is not True:
            failures.append("native_graph_replay_not_true")
        if native.get("packet_stream_input") is not True:
            failures.append("native_packet_stream_input_not_true")
        if native.get("persistent_state_on_device") is not True:
            failures.append("native_persistent_state_on_device_not_true")
        if native.get("issue_generation_on_device") is not True:
            failures.append("native_issue_generation_on_device_not_true")
        if native.get("native_stub_invoked") is not True:
            failures.append("native_stub_invoked_not_true")

    comparisons = payload.get("comparisons")
    if not isinstance(comparisons, dict):
        failures.append("comparisons_missing")
        comparisons = {}
    required_comparisons = (
        "packet_count_match",
        "previous_nonempty_packet_count_match",
        "issue_candidate_count_match",
        "issue_candidate_hash_match",
        "expected_issue_candidate_count_match",
        "state_override_count_match",
        "state_mismatch_count_zero",
        "issue_expert_mismatch_count_zero",
    )
    for key in required_comparisons:
        if comparisons.get(key) is not True:
            failures.append(f"{key}_not_true")

    packet_count = native.get("packet_count")
    issue_candidate_count = native.get("issue_candidate_count")
    issue_candidate_hash = native.get("issue_candidate_hash")
    expected_issue_candidate_count = native.get("expected_issue_candidate_count")
    previous_nonempty_packet_count = native.get("previous_nonempty_packet_count")
    state_override_count = native.get("state_override_count")
    state_mismatch_count = native.get("state_mismatch_count")
    issue_expert_mismatch_count = native.get("issue_expert_mismatch_count")
    materialized_packet_count = materialized.get("packet_count")
    materialized_expected_issue_candidate_count = materialized.get(
        "expected_issue_candidate_count"
    )
    materialized_expected_issue_candidate_hash = materialized.get(
        "expected_issue_candidate_hash"
    )
    materialized_expected_previous_nonempty_packet_count = materialized.get(
        "expected_previous_nonempty_packet_count"
    )
    materialized_state_override_count = materialized.get("state_override_count")
    if not _int_at_least(packet_count, int(min_packet_count)):
        failures.append("packet_count_invalid")
    if not _int_at_least(issue_candidate_count, int(min_issue_candidate_count)):
        failures.append("issue_candidate_count_invalid")
    if type(expected_issue_candidate_count) is not int:
        failures.append("expected_issue_candidate_count_invalid")
    if type(state_override_count) is not int:
        failures.append("state_override_count_invalid")
    if not _hex64_string(issue_candidate_hash):
        failures.append("issue_candidate_hash_invalid")
    if not _hex64_string(materialized_expected_issue_candidate_hash):
        failures.append("materialized_expected_issue_candidate_hash_invalid")
    if (
        isinstance(issue_candidate_hash, str)
        and isinstance(materialized_expected_issue_candidate_hash, str)
        and issue_candidate_hash != materialized_expected_issue_candidate_hash
    ):
        failures.append("native_materialized_issue_candidate_hash_mismatch")
    if (
        type(issue_candidate_count) is int
        and type(expected_issue_candidate_count) is int
        and issue_candidate_count != expected_issue_candidate_count
    ):
        failures.append("issue_candidate_count_expected_mismatch")
    if (
        type(materialized_packet_count) is not int
        or type(materialized_expected_issue_candidate_count) is not int
        or type(materialized_state_override_count) is not int
    ):
        failures.append("materialized_counts_invalid")
    if (
        type(packet_count) is int
        and type(materialized_packet_count) is int
        and packet_count != materialized_packet_count
    ):
        failures.append("native_materialized_packet_count_mismatch")
    if (
        type(previous_nonempty_packet_count) is not int
        or type(materialized_expected_previous_nonempty_packet_count) is not int
    ):
        failures.append("previous_nonempty_packet_count_invalid")
    elif (
        previous_nonempty_packet_count
        != materialized_expected_previous_nonempty_packet_count
    ):
        failures.append("native_materialized_previous_nonempty_count_mismatch")
    if (
        type(issue_candidate_count) is int
        and type(materialized_expected_issue_candidate_count) is int
        and issue_candidate_count != materialized_expected_issue_candidate_count
    ):
        failures.append("native_materialized_issue_candidate_count_mismatch")
    if (
        type(expected_issue_candidate_count) is int
        and type(materialized_expected_issue_candidate_count) is int
        and expected_issue_candidate_count
        != materialized_expected_issue_candidate_count
    ):
        failures.append("native_materialized_expected_issue_candidate_count_mismatch")
    if (
        type(state_override_count) is int
        and type(materialized_state_override_count) is int
        and state_override_count != materialized_state_override_count
    ):
        failures.append("native_materialized_state_override_count_mismatch")
    if not _zero_int(state_mismatch_count):
        failures.append("state_mismatch_count_nonzero")
    if not _zero_int(issue_expert_mismatch_count):
        failures.append("issue_expert_mismatch_count_nonzero")

    return {
        "passed": not failures,
        "failures": failures,
        "mode": "premap_payload_cache_packet_stream_native_canary_check",
        "min_packet_count": int(min_packet_count),
        "min_issue_candidate_count": int(min_issue_candidate_count),
        "packet_count": packet_count,
        "issue_candidate_count": issue_candidate_count,
        "issue_candidate_hash": issue_candidate_hash,
        "expected_issue_candidate_hash": materialized_expected_issue_candidate_hash,
        "expected_issue_candidate_count": expected_issue_candidate_count,
        "previous_nonempty_packet_count": previous_nonempty_packet_count,
        "state_override_count": state_override_count,
        "state_mismatch_count": state_mismatch_count,
        "issue_expert_mismatch_count": issue_expert_mismatch_count,
        "native_graph_replay": native.get("native_graph_replay"),
        "native_runtime_blocked": payload.get("native_runtime_blocked"),
        "payload_bytes": payload.get("payload_bytes"),
        "ready_credit": payload.get("ready_credit"),
        "kernel_arg_pass": payload.get("kernel_arg_pass"),
        "passed_to_kernel": payload.get("passed_to_kernel"),
        "changes_kernel_launch_args": payload.get("changes_kernel_launch_args"),
        "uses_current_wna16_args": payload.get("uses_current_wna16_args"),
        "passes_current_wna16_args": payload.get("passes_current_wna16_args"),
        "materialized_packet_count": materialized.get("packet_count"),
        "materialized_state_override_count": materialized.get("state_override_count"),
        "materialized_expected_issue_candidate_count": materialized.get(
            "expected_issue_candidate_count"
        ),
        "materialized_expected_issue_candidate_hash": materialized.get(
            "expected_issue_candidate_hash"
        ),
        "materialized_expected_previous_nonempty_packet_count": materialized.get(
            "expected_previous_nonempty_packet_count"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--min-packet-count", type=int, default=1)
    parser.add_argument("--min-issue-candidate-count", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_packet_stream_native_canary(
        _load_json(args.canary_json),
        min_packet_count=args.min_packet_count,
        min_issue_candidate_count=args.min_issue_candidate_count,
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
