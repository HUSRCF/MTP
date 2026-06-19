#!/usr/bin/env python3
"""Promote payloadless useful execution into a runtime-gate artifact.

This is still a no-payload, no-current-WNA16-arg, no-TPOT gate.  It consumes the
compact lab preflight summary and its checker output, then records that the
payloadless useful-execution chain is a default lab precondition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_PREFLIGHT_SUMMARY_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_lab_preflight_entry_args_ptr_all_four_default_gate.json"
)
DEFAULT_PREFLIGHT_CHECK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_lab_preflight_entry_args_ptr_all_four_default_gate.check.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_payloadless_useful_runtime_gate_entry_args_ptr_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_runtime_gate"
GATE_NAME = "premap_future_wna16_typed_slot_payloadless_useful_runtime_gate_v1"
GATE_MODE = "readonly_payloadless_useful_runtime_gate"
GATE_SOURCE = "premap_lab_preflight_payloadless_useful_execution_gate"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_payloadless_useful_benchmark_harness"
FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
PREFIX = "default_kernel_consumer_future_wna16_payloadless_useful_execution"


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 <= parsed <= 0xFFFFFFFFFFFFFFFF


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _path_matches(path_value: Any, expected_path: Path) -> bool:
    if not isinstance(path_value, str) or not path_value:
        return False
    try:
        return _resolve(path_value).resolve() == expected_path.resolve()
    except OSError:
        return False


def _check_noop_summary_flags(summary: dict[str, Any], failures: list[str]) -> None:
    expected = {
        f"{PREFIX}_payload_bytes": 0,
        f"{PREFIX}_payload_deref_allowed": False,
        f"{PREFIX}_kernel_arg_pass_allowed": False,
        f"{PREFIX}_passed_to_kernel": False,
        f"{PREFIX}_changes_kernel_launch_args": False,
        f"{PREFIX}_current_wna16_arg_compatible": False,
        f"{PREFIX}_uses_current_wna16_args": False,
        f"{PREFIX}_passes_current_wna16_args": False,
        f"{PREFIX}_requires_wna16_arg_reinterpretation": False,
        f"{PREFIX}_measures_tpot": False,
        f"{PREFIX}_measures_vllm_latency": False,
        f"{PREFIX}_wna16_benchmark_ready": False,
    }
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            failures.append(f"{key}_mismatch")


def run_payloadless_useful_runtime_gate(args: argparse.Namespace) -> dict[str, Any]:
    summary_path = _resolve(args.preflight_summary_json)
    check_path = _resolve(args.preflight_check_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    summary: dict[str, Any] = {}
    check: dict[str, Any] = {}
    try:
        summary = _load_json(summary_path)
    except Exception as exc:
        failures.append(f"preflight_summary_load_failed:{exc.__class__.__name__}:{exc}")
    try:
        check = _load_json(check_path)
    except Exception as exc:
        failures.append(f"preflight_check_load_failed:{exc.__class__.__name__}:{exc}")

    summary_sha = _sha256(summary_path) if summary_path.exists() else None
    check_sha = _sha256(check_path) if check_path.exists() else None
    if summary and check:
        if check.get("passed") is not True:
            failures.append("preflight_check_not_passed")
        if check.get("failures") != []:
            failures.append("preflight_check_failures_not_empty")
        if check.get("checked_preflight_sha256") != summary_sha:
            failures.append("preflight_check_summary_sha256_mismatch")
        if "checked_preflight_json" not in check:
            failures.append("preflight_check_summary_path_missing")
        elif not _path_matches(check.get("checked_preflight_json"), summary_path):
            failures.append("preflight_check_summary_path_mismatch")
        if "checked_preflight_json_raw" not in check:
            failures.append("preflight_check_summary_raw_path_missing")
        elif not _path_matches(check.get("checked_preflight_json_raw"), summary_path):
            failures.append("preflight_check_summary_raw_path_mismatch")
        if summary.get("passed") is not True:
            failures.append("preflight_summary_not_passed")
        if summary.get("default_required_evidence_passed") is not True:
            failures.append("default_required_evidence_not_passed")
        if summary.get(f"{PREFIX}_evidence_passed") is not True:
            failures.append("payloadless_useful_execution_evidence_not_passed")
        if summary.get("default_kernel_consumer_wna16_benchmark_ready") is not False:
            failures.append("default_wna16_benchmark_ready_mismatch")
        if summary.get(f"{PREFIX}_gate_ready") is not True:
            failures.append("payloadless_useful_execution_gate_not_ready")
        if summary.get(f"{PREFIX}_ready") is not True:
            failures.append("payloadless_useful_execution_not_ready")
        if summary.get(f"{PREFIX}_chain_checked") is not True:
            failures.append("payloadless_useful_execution_chain_not_checked")
        if summary.get(f"{PREFIX}_native_stub_checked") is not True:
            failures.append("payloadless_useful_execution_native_stub_not_checked")
        if summary.get("default_kernel_consumer_next_runtime_stage") != (
            "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
        ):
            failures.append("preflight_next_runtime_stage_mismatch")
        _check_noop_summary_flags(summary, failures)

    source_count = _int_metric(summary, f"{PREFIX}_source_count")
    row_count = _int_metric(summary, f"{PREFIX}_row_count")
    row_ok_count = _int_metric(summary, f"{PREFIX}_row_ok_count")
    rows_consumed = _int_metric(summary, f"{PREFIX}_rows_consumed")
    if source_count is None or source_count < args.min_source_count:
        failures.append("source_count_invalid")
    if row_count is None or row_count < args.min_row_count:
        failures.append("row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("row_ok_count_mismatch")
    if row_count is not None and rows_consumed != row_count:
        failures.append("rows_consumed_mismatch")

    field_hashes: dict[str, str] = {}
    for field in FIELDS:
        row_key = f"{PREFIX}_{field}_row_ok_count"
        hash_key = f"{PREFIX}_{field}_field_hash"
        if row_count is not None and _int_metric(summary, row_key) != row_count:
            failures.append(f"{field}_row_ok_count_mismatch")
        hash_value = summary.get(hash_key)
        if not _is_hex_u64(hash_value):
            failures.append(f"{field}_field_hash_invalid")
        else:
            field_hashes[field] = hash_value
    for key in (
        f"{PREFIX}_evidence_sha256",
        f"{PREFIX}_useful_consumer_sha256",
        f"{PREFIX}_execution_sha256",
        f"{PREFIX}_native_timing_sha256",
        f"{PREFIX}_native_stub_sha256",
        f"{PREFIX}_chain_hash",
    ):
        if not _is_sha256_hex(summary.get(key)):
            failures.append(f"{key}_invalid")
    for key in (
        f"{PREFIX}_evidence_path",
        f"{PREFIX}_useful_consumer_json",
        f"{PREFIX}_execution_json",
        f"{PREFIX}_native_timing_json",
        f"{PREFIX}_native_stub_json",
    ):
        if not isinstance(summary.get(key), str) or not summary.get(key):
            failures.append(f"{key}_missing")

    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "runtime_gate_name": GATE_NAME,
        "runtime_gate_mode": GATE_MODE,
        "runtime_gate_source": GATE_SOURCE,
        "passed": passed,
        "failures": failures,
        "preflight_summary_json": str(summary_path),
        "preflight_summary_sha256": summary_sha,
        "preflight_check_json": str(check_path),
        "preflight_check_sha256": check_sha,
        "payloadless_useful_execution_json": summary.get(f"{PREFIX}_evidence_path"),
        "payloadless_useful_execution_sha256": summary.get(
            f"{PREFIX}_evidence_sha256"
        ),
        "useful_consumer_json": summary.get(f"{PREFIX}_useful_consumer_json"),
        "useful_consumer_sha256": summary.get(f"{PREFIX}_useful_consumer_sha256"),
        "execution_json": summary.get(f"{PREFIX}_execution_json"),
        "execution_sha256": summary.get(f"{PREFIX}_execution_sha256"),
        "native_timing_json": summary.get(f"{PREFIX}_native_timing_json"),
        "native_timing_sha256": summary.get(f"{PREFIX}_native_timing_sha256"),
        "native_stub_json": summary.get(f"{PREFIX}_native_stub_json"),
        "native_stub_sha256": summary.get(f"{PREFIX}_native_stub_sha256"),
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_ok_count,
        "rows_consumed": rows_consumed,
        "field_names": list(FIELDS),
        "field_read_hashes": field_hashes,
        "runtime_gate_ready": passed,
        "payloadless_useful_runtime_gate_ready": passed,
        "payloadless_useful_execution_gate_ready": summary.get(f"{PREFIX}_gate_ready"),
        "payloadless_useful_execution_chain_hash": summary.get(f"{PREFIX}_chain_hash"),
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot payloadless useful runtime gate failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight-summary-json",
        default=str(DEFAULT_PREFLIGHT_SUMMARY_JSON),
    )
    parser.add_argument("--preflight-check-json", default=str(DEFAULT_PREFLIGHT_CHECK_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_payloadless_useful_runtime_gate(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
