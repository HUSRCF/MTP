#!/usr/bin/env python3
"""Build a payloadless native execution adapter canary artifact."""

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


ARTIFACT_KIND = "premap_payload_cache_native_execution_adapter_payloadless_canary"
SCHEMA_NAME = "payload_cache_native_execution_adapter_payloadless_canary_v1"
SOURCE_ARTIFACT_KIND = "premap_payload_cache_native_execution_adapter_blocked"
SOURCE_SCHEMA_NAME = "payload_cache_native_execution_adapter_blocked_v1"
ADAPTER_FIELD_NAMES = (
    "copy_descriptor_row",
    "copy_descriptor_packet",
    "payload_issue_metadata",
    "ready_credit_blocked_state",
)


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


def _hash_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


def _field_hashes(source: dict[str, Any], *, source_sha: str) -> dict[str, str]:
    return {
        "copy_descriptor_row": _hash_json(
            {
                "row_hash": source.get("copy_descriptor_row_hash"),
                "row_count": source.get("copy_descriptor_count"),
            }
        ),
        "copy_descriptor_packet": _hash_json(
            {
                "packet_hash": source.get("copy_descriptor_packet_hash"),
                "packet_count": source.get("packet_count"),
                "nonempty_packet_count": source.get("nonempty_packet_count"),
            }
        ),
        "payload_issue_metadata": _hash_json(
            {
                "planned_payload_bytes": source.get("planned_payload_bytes"),
                "planned_payload_bytes_per_issue": source.get(
                    "planned_payload_bytes_per_issue"
                ),
                "issued_prefetch_count": source.get("issued_prefetch_count"),
            }
        ),
        "ready_credit_blocked_state": _hash_json(
            {
                "source_sha256": source_sha,
                "ready_credit_queue_row_count": source.get(
                    "ready_credit_queue_row_count"
                ),
                "ready_credit_count": source.get("ready_credit_count"),
                "ready_credit": source.get("ready_credit"),
            }
        ),
    }


def build_native_execution_adapter_payloadless_canary_artifact(
    *,
    native_execution_adapter_blocked_json: str | Path,
    output_json: str | Path,
    adapter_capacity: int,
    require_pass: bool = False,
) -> dict[str, Any]:
    source_path = _resolve(native_execution_adapter_blocked_json)
    output_path = _resolve(output_json)
    source = _load_json_object(source_path)
    source_sha = _sha256(source_path)
    failures: list[str] = []

    expected_values = {
        "artifact_kind": SOURCE_ARTIFACT_KIND,
        "schema_name": SOURCE_SCHEMA_NAME,
        "source_artifact_kind": "premap_payload_cache_ready_credit_blocked",
        "source_schema_name": "payload_cache_ready_credit_blocked_v1",
        "passed": True,
        "failures": [],
        "native_execution_adapter_blocked_ready": True,
        "native_execution_adapter_checked": True,
        "native_execution_adapter_rejected": True,
        "native_execution_adapter_allowed": False,
        "native_execution_adapter_consumes_ready_credit_blocked": True,
        "native_execution_adapter_execution_count": 0,
        "native_execution_adapter_completed_count": 0,
        "native_execution_adapter_payload_copy_count": 0,
        "native_execution_adapter_ready_credit_count": 0,
        "copy_completed": False,
        "copy_completion_count": 0,
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

    row_count = _int_metric(source, "native_execution_adapter_row_count")
    descriptor_count = _int_metric(source, "copy_descriptor_count")
    ready_credit_rows = _int_metric(source, "ready_credit_queue_row_count")
    planned_payload_bytes = _int_metric(source, "planned_payload_bytes")
    adapter_planned_payload_bytes = _int_metric(
        source,
        "native_execution_adapter_planned_payload_bytes",
    )
    bytes_per_issue = _int_metric(source, "planned_payload_bytes_per_issue")
    issued_prefetch_count = _int_metric(source, "issued_prefetch_count")
    packet_count = _int_metric(source, "packet_count")
    nonempty_packet_count = _int_metric(source, "nonempty_packet_count")
    packet_error_count = _int_metric(source, "packet_error_count")

    if row_count is None or row_count <= 0:
        failures.append("source_native_execution_adapter_row_count_invalid")
    if descriptor_count is None or descriptor_count != row_count:
        failures.append("source_copy_descriptor_count_mismatch")
    if ready_credit_rows is None or ready_credit_rows != row_count:
        failures.append("source_ready_credit_queue_row_count_mismatch")
    if issued_prefetch_count is None or issued_prefetch_count != row_count:
        failures.append("source_issued_prefetch_count_mismatch")
    if bytes_per_issue is None or bytes_per_issue <= 0:
        failures.append("source_planned_payload_bytes_per_issue_invalid")
    if (
        planned_payload_bytes is None
        or adapter_planned_payload_bytes is None
        or planned_payload_bytes != adapter_planned_payload_bytes
        or row_count is None
        or bytes_per_issue is None
        or planned_payload_bytes != row_count * bytes_per_issue
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

    adapter_capacity_value = int(adapter_capacity)
    if adapter_capacity_value <= 0:
        failures.append("payloadless_adapter_capacity_invalid")
    if row_count is not None and adapter_capacity_value < row_count:
        failures.append("payloadless_adapter_capacity_too_small")

    row_count_value = int(row_count or 0)
    field_hashes = _field_hashes(source, source_sha=source_sha)
    work_units = row_count_value * len(ADAPTER_FIELD_NAMES)
    chain_hash = _hash_json(
        {
            "source_sha256": source_sha,
            "field_hashes": field_hashes,
            "row_count": row_count_value,
            "field_names": list(ADAPTER_FIELD_NAMES),
        }
    )
    passed = not failures
    payload = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "passed": passed,
        "failures": failures,
        "native_execution_adapter_payloadless_canary_ready": passed,
        "source_native_execution_adapter_blocked_json": str(source_path),
        "source_native_execution_adapter_blocked_sha256": source_sha,
        "source_artifact_kind": source.get("artifact_kind"),
        "source_schema_name": source.get("schema_name"),
        "copy_descriptor_row_hash": source.get("copy_descriptor_row_hash"),
        "copy_descriptor_packet_hash": source.get("copy_descriptor_packet_hash"),
        "copy_descriptor_count": row_count_value,
        "issued_prefetch_count": int(issued_prefetch_count or 0),
        "requested_issue_count": int(source.get("requested_issue_count", 0) or 0),
        "planned_payload_bytes_per_issue": int(bytes_per_issue or 0),
        "planned_payload_bytes": int(planned_payload_bytes or 0),
        "packet_count": int(packet_count or 0),
        "nonempty_packet_count": int(nonempty_packet_count or 0),
        "packet_error_count": int(packet_error_count or 0),
        "ready_credit_queue_row_count": int(ready_credit_rows or 0),
        "native_execution_adapter_capacity": int(source.get("native_execution_adapter_capacity", 0) or 0),
        "payloadless_adapter_capacity": adapter_capacity_value,
        "payloadless_adapter_capacity_checked": (
            row_count is not None and adapter_capacity_value >= row_count
        ),
        "native_execution_adapter_payloadless_checked": True,
        "native_execution_adapter_payloadless_allowed": passed,
        "native_execution_adapter_payloadless_executed": passed,
        "native_execution_adapter_payloadless_rows_consumed": row_count_value if passed else 0,
        "native_execution_adapter_payloadless_execution_count": row_count_value if passed else 0,
        "native_execution_adapter_payloadless_completed_count": row_count_value if passed else 0,
        "native_execution_adapter_payloadless_field_names": list(ADAPTER_FIELD_NAMES),
        "native_execution_adapter_payloadless_field_count": len(ADAPTER_FIELD_NAMES),
        "native_execution_adapter_payloadless_fields_per_row": len(ADAPTER_FIELD_NAMES),
        "native_execution_adapter_payloadless_work_units": work_units if passed else 0,
        "native_execution_adapter_payloadless_expected_work_units": work_units,
        "native_execution_adapter_payloadless_work_coverage": 1.0 if passed else 0.0,
        "native_execution_adapter_payloadless_field_hashes": field_hashes,
        "native_execution_adapter_payloadless_chain_hash": chain_hash,
        "native_execution_adapter_effectful_allowed": False,
        "native_execution_adapter_effectful_execution_count": 0,
        "native_execution_adapter_execution_count": 0,
        "native_execution_adapter_completed_count": 0,
        "native_execution_adapter_payload_copy_count": 0,
        "native_execution_adapter_ready_credit_count": 0,
        "copy_completed": False,
        "copy_completion_count": 0,
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
        "execution_mode": "payload_cache_native_execution_adapter_payloadless_canary",
        "next_runtime_stage": "native_execution_adapter_effectful_canary_or_real_payload_copy_canary",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if require_pass and not passed:
        raise SystemExit(
            "native-execution-adapter-payloadless-canary artifact failed "
            f"validation: {failures}"
        )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-execution-adapter-blocked-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--adapter-capacity", type=int, required=True)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_native_execution_adapter_payloadless_canary_artifact(
        native_execution_adapter_blocked_json=args.native_execution_adapter_blocked_json,
        output_json=args.output_json,
        adapter_capacity=args.adapter_capacity,
        require_pass=bool(args.require_pass),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
