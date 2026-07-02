#!/usr/bin/env python3
"""Build a payload-copy dispatch-blocked artifact from submit-blocked rows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


ARTIFACT_KIND = "premap_payload_cache_copy_descriptor_dispatch_blocked"
SCHEMA_NAME = "payload_cache_copy_descriptor_dispatch_blocked_v1"
SOURCE_ARTIFACT_KIND = "premap_payload_cache_copy_descriptor_submit_blocked"
SOURCE_SCHEMA_NAME = "payload_cache_copy_descriptor_submit_blocked_v1"


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def _expect(payload: dict[str, Any], failures: list[str], key: str, expected: Any) -> None:
    value = payload.get(key)
    if type(value) is not type(expected) or value != expected:
        failures.append(f"source_{key}_mismatch")


def build_dispatch_blocked_artifact(
    *,
    copy_descriptor_submit_blocked_json: str | Path,
    output_json: str | Path,
    dispatch_capacity: int,
    require_pass: bool = False,
) -> dict[str, Any]:
    source_path = _resolve(copy_descriptor_submit_blocked_json)
    output_path = _resolve(output_json)
    source = _load_json_object(source_path)
    failures: list[str] = []

    expected_values = {
        "artifact_kind": SOURCE_ARTIFACT_KIND,
        "schema_name": SOURCE_SCHEMA_NAME,
        "passed": True,
        "failures": [],
        "copy_descriptor_submit_blocked_ready": True,
        "submit_queue_shape_checked": True,
        "copy_descriptor_submit_checked": True,
        "copy_descriptor_submit_rejected": True,
        "copy_descriptor_submit_allowed": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_dispatched": False,
        "copy_descriptor_executed": False,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
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
        "live_runtime_instantiated": False,
        "requires_payload_runtime": False,
    }
    for key, expected in expected_values.items():
        _expect(source, failures, key, expected)

    descriptor_count = _int_metric(source, "copy_descriptor_count")
    submit_queue_row_count = _int_metric(source, "submit_queue_row_count")
    submit_queue_capacity = _int_metric(source, "submit_queue_capacity")
    issued_prefetch_count = _int_metric(source, "issued_prefetch_count")
    requested_issue_count = _int_metric(source, "requested_issue_count")
    planned_payload_bytes_per_issue = _int_metric(
        source,
        "planned_payload_bytes_per_issue",
    )
    planned_payload_bytes = _int_metric(source, "planned_payload_bytes")
    submit_queue_planned_payload_bytes = _int_metric(
        source,
        "submit_queue_planned_payload_bytes",
    )
    packet_count = _int_metric(source, "packet_count")
    nonempty_packet_count = _int_metric(source, "nonempty_packet_count")
    packet_error_count = _int_metric(source, "packet_error_count")

    if descriptor_count is None or descriptor_count <= 0:
        failures.append("source_copy_descriptor_count_invalid")
    if (
        submit_queue_row_count is None
        or descriptor_count is None
        or submit_queue_row_count != descriptor_count
    ):
        failures.append("source_submit_queue_row_count_mismatch")
    if (
        submit_queue_capacity is None
        or descriptor_count is None
        or submit_queue_capacity < descriptor_count
    ):
        failures.append("source_submit_queue_capacity_invalid")
    if issued_prefetch_count is None or descriptor_count is None or issued_prefetch_count != descriptor_count:
        failures.append("source_issued_prefetch_count_mismatch")
    if requested_issue_count is None or requested_issue_count <= 0:
        failures.append("source_requested_issue_count_invalid")
    if planned_payload_bytes_per_issue is None or planned_payload_bytes_per_issue <= 0:
        failures.append("source_planned_payload_bytes_per_issue_invalid")
    if (
        planned_payload_bytes is None
        or submit_queue_planned_payload_bytes is None
        or planned_payload_bytes != submit_queue_planned_payload_bytes
        or descriptor_count is None
        or planned_payload_bytes_per_issue is None
        or planned_payload_bytes != descriptor_count * planned_payload_bytes_per_issue
        or planned_payload_bytes <= 0
    ):
        failures.append("source_planned_payload_bytes_mismatch")
    if packet_count is None or packet_count <= 0:
        failures.append("source_packet_count_invalid")
    if nonempty_packet_count is None or nonempty_packet_count <= 0:
        failures.append("source_nonempty_packet_count_invalid")
    if packet_error_count is None or packet_error_count != 0:
        failures.append("source_packet_error_count_nonzero")
    for key in ("copy_descriptor_row_hash", "copy_descriptor_packet_hash"):
        if not _hex64(source.get(key)):
            failures.append(f"source_{key}_invalid")

    dispatch_capacity_value = int(dispatch_capacity)
    if dispatch_capacity_value <= 0:
        failures.append("dispatch_capacity_invalid")
    if descriptor_count is not None and dispatch_capacity_value < descriptor_count:
        failures.append("dispatch_capacity_too_small")

    dispatch_queue_row_count = int(descriptor_count or 0)
    dispatch_queue_planned_payload_bytes = int(planned_payload_bytes or 0)
    passed = not failures
    payload = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "passed": passed,
        "failures": failures,
        "copy_descriptor_dispatch_blocked_ready": passed,
        "source_copy_descriptor_submit_blocked_json": str(source_path),
        "source_copy_descriptor_submit_blocked_sha256": _sha256(source_path),
        "source_artifact_kind": source.get("artifact_kind"),
        "source_schema_name": source.get("schema_name"),
        "copy_descriptor_row_hash": source.get("copy_descriptor_row_hash"),
        "copy_descriptor_packet_hash": source.get("copy_descriptor_packet_hash"),
        "copy_descriptor_count": dispatch_queue_row_count,
        "issued_prefetch_count": int(issued_prefetch_count or 0),
        "requested_issue_count": int(requested_issue_count or 0),
        "planned_payload_bytes_per_issue": int(planned_payload_bytes_per_issue or 0),
        "planned_payload_bytes": dispatch_queue_planned_payload_bytes,
        "packet_count": int(packet_count or 0),
        "nonempty_packet_count": int(nonempty_packet_count or 0),
        "packet_error_count": int(packet_error_count or 0),
        "submit_queue_row_count": int(submit_queue_row_count or 0),
        "submit_queue_capacity": int(submit_queue_capacity or 0),
        "dispatch_queue_shape_checked": passed,
        "dispatch_capacity": dispatch_capacity_value,
        "dispatch_queue_row_count": dispatch_queue_row_count,
        "dispatch_queue_planned_payload_bytes": dispatch_queue_planned_payload_bytes,
        "copy_descriptor_dispatch_checked": True,
        "copy_descriptor_dispatch_rejected": True,
        "copy_descriptor_dispatch_allowed": False,
        "copy_descriptor_submitted": False,
        "copy_descriptor_dispatched": False,
        "copy_descriptor_executed": False,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
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
        "live_runtime_instantiated": False,
        "requires_payload_runtime": False,
        "execution_mode": "payload_cache_copy_descriptor_dispatch_blocked",
        "next_runtime_stage": "payload_copy_worker_execution_blocked_or_native_dispatch_adapter",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if require_pass and not passed:
        raise SystemExit(f"dispatch-blocked artifact failed validation: {failures}")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy-descriptor-submit-blocked-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--dispatch-capacity", type=int, required=True)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_dispatch_blocked_artifact(
        copy_descriptor_submit_blocked_json=args.copy_descriptor_submit_blocked_json,
        output_json=args.output_json,
        dispatch_capacity=args.dispatch_capacity,
        require_pass=bool(args.require_pass),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
