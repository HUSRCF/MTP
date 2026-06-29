#!/usr/bin/env python3
"""Build the payload/cache-manager useful-work readiness gate.

This gate sits after the stricter vLLM replay-visible count-pointer native
producer contract.  It verifies that issue generation is now on the
production-like device count-pointer path, then binds that producer evidence to
the consumer-visible demand-hit publication boundary.  It does not enable
payload transfer, ready credit, kernel argument handoff, or TPOT measurement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.run_premap_lab_preflight import (
    _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COUNT_PTR_NATIVE_PRODUCER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "native_session_smoke1_gen4_vllm_replay_visible_count_ptr_native_producer_contract.json"
)
DEFAULT_CONSUMER_VISIBLE_HIT_BLOCKED_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_payload_cache"
    / "payload_cache_consumer_visible_hit_blocked_gate.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_payload_cache"
    / "payload_cache_useful_work_readiness_gate.json"
)

ARTIFACT_KIND = "premap_payload_cache_useful_work_readiness_gate"
GATE_MODE = "payload_cache_useful_work_readiness_noop_gate"
NEXT_STAGE = "payload_cache_manager_useful_work_ab_or_payload_runtime_canary"
NOOP_FALSE_FIELDS = (
    "payload_transfer_enabled",
    "ready",
    "payload_deref_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "kernel_arg_pass",
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


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _exact(payload: dict[str, Any], key: str, expected: Any) -> bool:
    value = payload.get(key)
    return type(value) is type(expected) and value == expected


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _validate_count_ptr_native_producer(
    payload: dict[str, Any],
    failures: list[str],
) -> dict[str, int | str]:
    prefix = "count_ptr_native_producer"
    expected_values = {
        "mode": "payload_cache_vllm_replay_visible_count_ptr_native_producer_contract",
        "contract_boundary": "inprocess_vllm_prelaunch_native_count_ptr_producer_op",
        "ok": True,
        "passed": True,
        "failures": [],
        "base_contract_passed": True,
        "host_scalar_count": 0,
        "count_ptr_blocked_count": 0,
        "current_count_source_kind": "num_tokens_post_padded_device_tensor",
        "python_transition_skipped": True,
        "native_runtime": True,
        "inprocess_native_op": True,
        "vllm_replay_visible": True,
        "ready_for_payload_cache_runtime_lab_gate": True,
        "next_boundary": "production_like_payload_cache_manager_or_payload_runtime_canary",
        "payload_bytes": 0,
    }
    for key, expected in expected_values.items():
        if not _exact(payload, key, expected):
            failures.append(f"{prefix}_{key}_mismatch")
    for key in NOOP_FALSE_FIELDS:
        if not _exact(payload, key, False):
            failures.append(f"{prefix}_{key}_mismatch")
    expected_packet_count = _int_metric(payload, "expected_packet_count")
    if expected_packet_count is None or expected_packet_count <= 0:
        failures.append(f"{prefix}_expected_packet_count_invalid")
        expected_packet_count = 0
    for key in (
        "packet_count",
        "prelaunch_probe_count",
        "count_ptr_ready_count",
        "device_count_tensor_count",
        "device_count_scalar_int32_count",
    ):
        value = _int_metric(payload, key)
        if value is None or value <= 0:
            failures.append(f"{prefix}_{key}_invalid")
        elif expected_packet_count and value != expected_packet_count:
            failures.append(f"{prefix}_{key}_mismatch")
    current_expert_source = payload.get("current_expert_ptr_source_kind")
    if current_expert_source not in {
        "vllm_prelaunch_device_tensor",
        "vllm_prelaunch_native_device_tensor",
    }:
        failures.append(f"{prefix}_current_expert_ptr_source_kind_mismatch")
    legacy_ready_count = _int_metric(payload, "legacy_host_scalar_ready_count")
    legacy_blocked_count = _int_metric(payload, "legacy_host_scalar_blocked_count")
    if legacy_ready_count != 0:
        failures.append(f"{prefix}_legacy_host_scalar_ready_count_nonzero")
    if legacy_blocked_count is None or legacy_blocked_count < 0:
        failures.append(f"{prefix}_legacy_host_scalar_blocked_count_invalid")
    return {
        "expected_packet_count": int(expected_packet_count or 0),
        "current_count_source_kind": str(payload.get("current_count_source_kind") or ""),
        "current_expert_ptr_source_kind": str(current_expert_source or ""),
    }


def _validate_consumer_visible_hit_blocked(
    payload: dict[str, Any],
    failures: list[str],
) -> dict[str, int | float | str]:
    prefix = "consumer_visible_hit_blocked"
    strict_failures = _validate_payload_cache_consumer_visible_hit_blocked_gate_evidence(
        payload,
        failure_prefix=prefix,
    )
    failures.extend(strict_failures)
    expected_values = {
        "artifact_kind": "payload_cache_consumer_visible_hit_blocked_gate",
        "schema_version": 1,
        "source": "payload_cache_consumer_visible_hit_blocked_gate",
        "passed": True,
        "failures": [],
        "decision": "blocked",
        "block_reason": "payload_transfer_disabled",
        "request_matches_envelope_source_binding": True,
        "execution_mode": (
            "payload_cache_live_runtime_adapter_"
            "payload_issue_demand_hit_publication_blocked_canary"
        ),
        "demand_hit_publication_allowed": False,
        "demand_hit_published": False,
        "consumer_visible_payload_hit": False,
        "prefetched_demand_hit": False,
        "payload_deref_attempted": False,
        "payload_handle_deref_attempted": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    for key, expected in expected_values.items():
        if not _exact(payload, key, expected):
            failures.append(f"{prefix}_{key}_mismatch")
    if payload.get("ready") is not None and not _exact(payload, "ready", False):
        failures.append(f"{prefix}_ready_mismatch")
    for key in (
        "payload_bytes",
        "resident_payload_bytes",
        "dereferenced_payload_bytes",
        "demand_hit_payload_bytes",
        "issued_payload_count",
        "resident_payload_count",
        "demand_hit_count",
        "demand_hit_publication_count",
        "consumer_visible_payload_hit_count",
    ):
        if _int_metric(payload, key) != 0:
            failures.append(f"{prefix}_{key}_nonzero")
    requested_payload_bytes = _int_metric(payload, "requested_payload_bytes")
    source_issue_packet_count = _int_metric(payload, "source_issue_packet_count")
    source_issue_unique_key_count = _int_metric(payload, "source_issue_unique_key_count")
    if requested_payload_bytes is None or requested_payload_bytes <= 0:
        failures.append(f"{prefix}_requested_payload_bytes_invalid")
        requested_payload_bytes = 0
    if source_issue_packet_count is None or source_issue_packet_count <= 0:
        failures.append(f"{prefix}_source_issue_packet_count_invalid")
        source_issue_packet_count = 0
    if source_issue_unique_key_count is None or source_issue_unique_key_count <= 0:
        failures.append(f"{prefix}_source_issue_unique_key_count_invalid")
        source_issue_unique_key_count = 0
    queue_deadline_us = payload.get("source_queue_deadline_us")
    if isinstance(queue_deadline_us, bool) or not isinstance(queue_deadline_us, (int, float)):
        failures.append(f"{prefix}_source_queue_deadline_us_invalid")
        queue_deadline_us = 0.0
    return {
        "requested_payload_bytes": int(requested_payload_bytes or 0),
        "source_issue_packet_count": int(source_issue_packet_count or 0),
        "source_issue_unique_key_count": int(source_issue_unique_key_count or 0),
        "source_queue_deadline_us": float(queue_deadline_us),
        "block_reason": str(payload.get("block_reason") or ""),
    }


def build_gate(
    *,
    count_ptr_native_producer_json: Path,
    consumer_visible_hit_blocked_json: Path,
) -> dict[str, Any]:
    count_ptr_payload = _load_json(count_ptr_native_producer_json)
    consumer_payload = _load_json(consumer_visible_hit_blocked_json)
    failures: list[str] = []
    producer = _validate_count_ptr_native_producer(count_ptr_payload, failures)
    consumer = _validate_consumer_visible_hit_blocked(consumer_payload, failures)
    producer_ready = not any(
        failure.startswith("count_ptr_native_producer_") for failure in failures
    )
    consumer_ready = not any(
        failure.startswith("consumer_visible_hit_blocked_") for failure in failures
    )
    passed = not failures
    return {
        "artifact_kind": ARTIFACT_KIND,
        "mode": GATE_MODE,
        "passed": passed,
        "ok": passed,
        "failures": failures,
        "producer_count_ptr_ready": producer_ready,
        "consumer_visible_blocked_ready": consumer_ready,
        "native_producer_downshifted": producer_ready,
        "payload_cache_useful_work_ready": False,
        "payload_cache_useful_work_block_reason": (
            "payload_transfer_disabled"
            if consumer_ready
            else "invalid_consumer_visible_hit_blocked_evidence"
        ),
        "next_stage": NEXT_STAGE,
        "producer_expected_packet_count": producer["expected_packet_count"],
        "producer_current_count_source_kind": producer["current_count_source_kind"],
        "producer_current_expert_ptr_source_kind": producer[
            "current_expert_ptr_source_kind"
        ],
        "consumer_requested_payload_bytes": consumer["requested_payload_bytes"],
        "consumer_source_issue_packet_count": consumer["source_issue_packet_count"],
        "consumer_source_issue_unique_key_count": consumer[
            "source_issue_unique_key_count"
        ],
        "consumer_source_queue_deadline_us": consumer["source_queue_deadline_us"],
        "consumer_block_reason": consumer["block_reason"],
        "payload_bytes": 0,
        "payload_transfer_enabled": False,
        "ready": False,
        "payload_deref_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "count_ptr_native_producer_json": _display_path(count_ptr_native_producer_json),
        "consumer_visible_hit_blocked_json": _display_path(
            consumer_visible_hit_blocked_json,
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count-ptr-native-producer-json",
        type=Path,
        default=DEFAULT_COUNT_PTR_NATIVE_PRODUCER_JSON,
    )
    parser.add_argument(
        "--consumer-visible-hit-blocked-json",
        type=Path,
        default=DEFAULT_CONSUMER_VISIBLE_HIT_BLOCKED_JSON,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_gate(
        count_ptr_native_producer_json=args.count_ptr_native_producer_json,
        consumer_visible_hit_blocked_json=args.consumer_visible_hit_blocked_json,
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
