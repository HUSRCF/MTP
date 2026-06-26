#!/usr/bin/env python3
"""Check the payload-cache stream producer production-like A/B bridge artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SAFE_FALSE_FIELDS = (
    "ready_credit",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "candidate_kernel_arg_pass",
    "candidate_changes_kernel_launch_args",
    "native_stream_is_current_wna16_fused_moe",
    "native_stream_measures_tpot",
)

SAFE_TRUE_FIELDS = (
    "native_stream_graph_replay_required",
    "native_stream_graph_replay",
    "native_stream_requested_graph_replay",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _finite_positive(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value)) and float(value) > 0.0


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _non_negative_int(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value >= 0


def check_report(
    payload: dict[str, Any],
    *,
    max_overhead_ratio: float = 0.02,
    min_issue_candidate_count: int = 1,
) -> dict[str, Any]:
    failures: list[str] = []

    if payload.get("mode") != "payload_cache_stream_producer_production_like_ab_report":
        failures.append("mode_mismatch")
    if payload.get("passed") is not True or payload.get("ok") is not True:
        failures.append("report_not_passed")
    if payload.get("failures") not in ([], None):
        failures.append("report_failures_not_empty")

    baseline_tpot = payload.get("baseline_tpot_s")
    candidate_tpot = payload.get("candidate_tpot_s")
    overhead_ratio = payload.get("candidate_overhead_ratio")
    if not _finite_positive(baseline_tpot):
        failures.append("baseline_tpot_invalid")
    if not _finite_positive(candidate_tpot):
        failures.append("candidate_tpot_invalid")
    if not _finite(overhead_ratio):
        failures.append("candidate_overhead_ratio_invalid")
    elif float(overhead_ratio) > float(max_overhead_ratio):
        failures.append("candidate_overhead_ratio_over_threshold")

    if payload.get("online_contract_passed") is not True:
        failures.append("online_contract_not_passed")
    if payload.get("measures_tpot") is not True:
        failures.append("measures_tpot_not_true")
    if payload.get("benchmark_is_current_wna16_fused_moe") is not True:
        failures.append("benchmark_is_current_wna16_fused_moe_not_true")

    payload_bytes = payload.get("payload_bytes")
    candidate_payload_bytes = payload.get("candidate_payload_bytes")
    if not _non_negative_int(payload_bytes):
        failures.append("payload_bytes_invalid")
    elif payload_bytes != 0:
        failures.append("payload_bytes_mismatch")
    if not _non_negative_int(candidate_payload_bytes):
        failures.append("candidate_payload_bytes_invalid")
    elif candidate_payload_bytes != 0:
        failures.append("candidate_payload_bytes_mismatch")
    for field in SAFE_FALSE_FIELDS:
        if payload.get(field) is not False:
            failures.append(f"{field}_not_false")
    for field in SAFE_TRUE_FIELDS:
        if payload.get(field) is not True:
            failures.append(f"{field}_not_true")

    issue_count = payload.get("native_stream_issue_candidate_count")
    expected_issue_count = payload.get("online_contract_expected_issue_candidate_count")
    issue_hash = payload.get("native_stream_issue_candidate_hash")
    if type(issue_count) is not int or issue_count < int(min_issue_candidate_count):
        failures.append("native_stream_issue_candidate_count_invalid")
    if type(expected_issue_count) is not int or expected_issue_count <= 0:
        failures.append("online_contract_expected_issue_candidate_count_invalid")
    elif type(issue_count) is int and issue_count != expected_issue_count:
        failures.append("native_stream_issue_candidate_count_mismatch")
    if not isinstance(issue_hash, str) or not issue_hash:
        failures.append("native_stream_issue_candidate_hash_invalid")
    if payload.get("native_stream_persistent_state_on_device") is not True:
        failures.append("native_stream_persistent_state_on_device_not_true")
    if payload.get("native_stream_issue_generation_on_device") is not True:
        failures.append("native_stream_issue_generation_on_device_not_true")

    return {
        "passed": not failures,
        "failures": failures,
        "mode": "premap_payload_cache_stream_producer_ab_bridge_check",
        "max_overhead_ratio": float(max_overhead_ratio),
        "min_issue_candidate_count": int(min_issue_candidate_count),
        "candidate_overhead_ratio": payload.get("candidate_overhead_ratio"),
        "native_stream_issue_candidate_count": payload.get(
            "native_stream_issue_candidate_count"
        ),
        "native_stream_first_issue_expert": payload.get(
            "native_stream_first_issue_expert"
        ),
        "native_stream_last_issue_expert": payload.get(
            "native_stream_last_issue_expert"
        ),
        "native_stream_issue_candidate_hash": payload.get(
            "native_stream_issue_candidate_hash"
        ),
        "online_contract_expected_issue_candidate_count": payload.get(
            "online_contract_expected_issue_candidate_count"
        ),
        "online_transition_issue_last_candidate_present": payload.get(
            "online_transition_issue_last_candidate_present"
        ),
        "online_transition_issue_last_candidate_source": payload.get(
            "online_transition_issue_last_candidate_source"
        ),
        "online_transition_issue_last_candidate_count": payload.get(
            "online_transition_issue_last_candidate_count"
        ),
        "online_transition_issue_last_candidate_first_expert": payload.get(
            "online_transition_issue_last_candidate_first_expert"
        ),
        "online_transition_issue_last_candidate_last_expert": payload.get(
            "online_transition_issue_last_candidate_last_expert"
        ),
        "online_transition_issue_last_candidate_hash": payload.get(
            "online_transition_issue_last_candidate_hash"
        ),
        "payload_bytes": payload.get("payload_bytes"),
        "candidate_payload_bytes": payload.get("candidate_payload_bytes"),
        "ready_credit": payload.get("ready_credit"),
        "passed_to_kernel": payload.get("passed_to_kernel"),
        "changes_kernel_launch_args": payload.get("changes_kernel_launch_args"),
        "uses_current_wna16_args": payload.get("uses_current_wna16_args"),
        "passes_current_wna16_args": payload.get("passes_current_wna16_args"),
        "candidate_kernel_arg_pass": payload.get("candidate_kernel_arg_pass"),
        "candidate_changes_kernel_launch_args": payload.get(
            "candidate_changes_kernel_launch_args"
        ),
        "native_stream_is_current_wna16_fused_moe": payload.get(
            "native_stream_is_current_wna16_fused_moe"
        ),
        "native_stream_measures_tpot": payload.get("native_stream_measures_tpot"),
        "native_stream_graph_replay_required": payload.get(
            "native_stream_graph_replay_required"
        ),
        "native_stream_graph_replay": payload.get("native_stream_graph_replay"),
        "native_stream_requested_graph_replay": payload.get(
            "native_stream_requested_graph_replay"
        ),
        "native_stream_persistent_state_on_device": payload.get(
            "native_stream_persistent_state_on_device"
        ),
        "native_stream_issue_generation_on_device": payload.get(
            "native_stream_issue_generation_on_device"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--max-overhead-ratio", type=float, default=0.02)
    parser.add_argument("--min-issue-candidate-count", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_report(
        _load_json(args.report_json),
        max_overhead_ratio=args.max_overhead_ratio,
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
