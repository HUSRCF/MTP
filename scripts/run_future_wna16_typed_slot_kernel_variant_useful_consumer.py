#!/usr/bin/env python3
"""Validate the useful future-WNA16 typed-slot consumer path.

This stage consumes the independent variant-execution artifact and promotes the
native WNA16-side typed-slot consumer output from diagnostic evidence to an
explicit gate.  It still does not pass the typed table to the current WNA16
fused-MoE kernel, does not dereference payloads, and does not measure TPOT.
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


DEFAULT_EXECUTION_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_execution_entry_args_ptr_native_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_useful_consumer_entry_args_ptr_native_v1.json"
)

USEFUL_CONSUMER_NAME = "premap_future_wna16_typed_slot_useful_consumer_v1"
USEFUL_CONSUMER_MODE = "independent_wna16_side_typed_slot_useful_consumer"
USEFUL_CONSUMER_SOURCE = "premap_future_wna16_typed_slot_kernel_variant_execution_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
STUB_PREFIX = "wna16_side_consumer_variant_execution"


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


def _check_execution(
    execution: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
        "execution_name": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        "execution_mode": "independent_future_wna16_typed_slot_kernel_variant_execution",
        "execution_source": "premap_future_wna16_typed_slot_payloadless_execution_v1",
        "passed": True,
        "payloadless_gate_ready": True,
        "future_wna16_variant_execution_ready": True,
        "future_wna16_variant_execution_native_requested": True,
        "future_wna16_variant_execution_native_executed": True,
        "future_wna16_variant_execution_native_passed": True,
        "future_wna16_variant_execution_native_artifact_ready": True,
        "future_wna16_variant_execution_not_current_wna16_kernel": True,
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
    }
    for key, value in expected.items():
        if execution.get(key) != value:
            failures.append(f"execution_{key}_mismatch")
    if execution.get("failures") != []:
        failures.append("execution_failures_not_empty")
    source_count = _int_metric(execution, "source_count")
    row_count = _int_metric(execution, "row_count")
    row_ok_count = _int_metric(execution, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("execution_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("execution_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("execution_row_ok_count_mismatch")
    if execution.get("field_names") != list(HANDLE_FIELDS):
        failures.append("execution_field_names_mismatch")
    row_ok_counts = execution.get("field_read_row_ok_counts")
    field_hashes = execution.get("field_read_hashes")
    if not isinstance(row_ok_counts, dict):
        failures.append("execution_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    if not isinstance(field_hashes, dict):
        failures.append("execution_field_read_hashes_missing")
        field_hashes = {}
    if set(row_ok_counts) != set(HANDLE_FIELDS):
        failures.append("execution_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != set(HANDLE_FIELDS):
        failures.append("execution_field_read_hashes_keys_mismatch")
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"execution_{field}_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"execution_{field}_hash_invalid")
    for key in ("row_hash_accumulator", "handle_projection_hash_accumulator"):
        if not _is_hex_u64(execution.get(key)):
            failures.append(f"execution_{key}_invalid")
    native_json = execution.get("future_wna16_variant_execution_native_json")
    native_sha = execution.get("future_wna16_variant_execution_native_sha256")
    if not isinstance(native_json, str) or not native_json:
        failures.append("execution_native_json_missing")
    elif not _resolve(native_json).exists():
        failures.append("execution_native_json_not_found")
    if not _is_sha256_hex(native_sha):
        failures.append("execution_native_sha256_invalid")
    elif isinstance(native_json, str) and _resolve(native_json).exists():
        if _sha256(_resolve(native_json)) != native_sha:
            failures.append("execution_native_sha256_mismatch")
    return failures


def _check_timing_report(
    timing: dict[str, Any],
    *,
    execution: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "passed": True,
        "timing_stub_ready": True,
        "native_stub_requested": True,
        "native_stub_executed": True,
        "native_stub_passed": True,
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
    }
    for key, value in expected.items():
        if timing.get(key) != value:
            failures.append(f"timing_{key}_mismatch")
    if timing.get("failures") != []:
        failures.append("timing_failures_not_empty")
    for key in ("source_count", "row_count", "row_ok_count"):
        if timing.get(key) != execution.get(key):
            failures.append(f"timing_{key}_mismatch")
    if timing.get("field_names") != list(HANDLE_FIELDS):
        failures.append("timing_field_names_mismatch")
    if timing.get("field_read_row_ok_counts") != execution.get(
        "field_read_row_ok_counts"
    ):
        failures.append("timing_field_read_row_ok_counts_mismatch")
    if timing.get("field_read_hashes") != execution.get("field_read_hashes"):
        failures.append("timing_field_read_hashes_mismatch")
    stub_json = timing.get("native_stub_output_json")
    stub_sha = timing.get("native_stub_output_sha256")
    if not isinstance(stub_json, str) or not stub_json:
        failures.append("timing_native_stub_output_json_missing")
    else:
        stub_path = _resolve(stub_json)
        if not stub_path.exists():
            failures.append("timing_native_stub_output_json_not_found")
        elif not _is_sha256_hex(stub_sha):
            failures.append("timing_native_stub_output_sha256_invalid")
        elif _sha256(stub_path) != stub_sha:
            failures.append("timing_native_stub_output_sha256_mismatch")
    return failures


def _check_stub(
    stub: dict[str, Any],
    *,
    row_count: int,
) -> tuple[list[str], dict[str, str]]:
    failures: list[str] = []
    macros = stub.get("compiled_macros")
    if not isinstance(macros, dict):
        failures.append("stub_compiled_macros_missing")
        macros = {}
    if (
        macros.get(
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_WNA16_SIDE_CONSUMER_VARIANT_EXECUTION_ABI"
        )
        is not True
    ):
        failures.append("stub_wna16_side_consumer_variant_macro_not_enabled")
    if stub.get("passed") is not True:
        failures.append("stub_passed_mismatch")
    if stub.get("failures") != []:
        failures.append("stub_failures_not_empty")
    expected = {
        f"{STUB_PREFIX}_checked": True,
        f"{STUB_PREFIX}_mode": "readonly_wna16_side_consumer_variant_execution",
        f"{STUB_PREFIX}_source": "premap_future_wna16_typed_slot_kernel_variant_v1",
        f"{STUB_PREFIX}_packet_chain_depth": 16,
        f"{STUB_PREFIX}_payload_bytes": 0,
        f"{STUB_PREFIX}_payload_deref_allowed": False,
        f"{STUB_PREFIX}_kernel_arg_pass_allowed": False,
        f"{STUB_PREFIX}_passed_to_kernel": False,
        f"{STUB_PREFIX}_changes_kernel_launch_args": False,
        f"{STUB_PREFIX}_current_wna16_arg_compatible": False,
        f"{STUB_PREFIX}_requires_wna16_arg_reinterpretation": False,
        f"{STUB_PREFIX}_explicit_typed_abi_slot": True,
        f"{STUB_PREFIX}_reuses_current_wna16_arg_slot": False,
        f"{STUB_PREFIX}_error_count": 0,
        f"{STUB_PREFIX}_row_offset": 0,
        f"{STUB_PREFIX}_row_limit": row_count,
        f"{STUB_PREFIX}_row_count": row_count,
        f"{STUB_PREFIX}_row_ok_count": row_count,
    }
    for key, value in expected.items():
        if stub.get(key) != value:
            failures.append(f"stub_{key}_mismatch")
    for key in (
        f"{STUB_PREFIX}_hash_accumulator",
        f"{STUB_PREFIX}_handle_projection_hash_accumulator",
    ):
        if not _is_hex_u64(stub.get(key)):
            failures.append(f"stub_{key}_invalid")
    field_hashes: dict[str, str] = {}
    for field in HANDLE_FIELDS:
        base = f"{STUB_PREFIX}_{field}_read"
        if stub.get(f"{base}_row_count") != row_count:
            failures.append(f"stub_{field}_row_count_mismatch")
        if stub.get(f"{base}_row_ok_count") != row_count:
            failures.append(f"stub_{field}_row_ok_count_mismatch")
        if stub.get(f"{base}_error_count") != 0:
            failures.append(f"stub_{field}_error_count_mismatch")
        hash_value = stub.get(f"{base}_hash_accumulator")
        if not _is_hex_u64(hash_value):
            failures.append(f"stub_{field}_hash_invalid")
        else:
            field_hashes[field] = hash_value
    return failures, field_hashes


def _combined_hash(*parts: Any) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(json.dumps(part, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def run_useful_consumer(args: argparse.Namespace) -> dict[str, Any]:
    execution_path = _resolve(args.execution_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    execution: dict[str, Any] = {}
    timing: dict[str, Any] = {}
    stub: dict[str, Any] = {}
    try:
        execution = _load_json(execution_path)
    except Exception as exc:
        failures.append(f"execution_json_load_failed:{exc.__class__.__name__}:{exc}")
    if execution:
        failures.extend(
            _check_execution(
                execution,
                min_source_count=args.min_source_count,
                min_row_count=args.min_row_count,
            )
        )
    native_path: Path | None = None
    if execution:
        native_value = execution.get("future_wna16_variant_execution_native_json")
        if isinstance(native_value, str) and native_value:
            native_path = _resolve(native_value)
            if native_path.exists():
                try:
                    timing = _load_json(native_path)
                except Exception as exc:
                    failures.append(
                        f"timing_json_load_failed:{exc.__class__.__name__}:{exc}"
                    )
    if timing:
        failures.extend(_check_timing_report(timing, execution=execution))
        stub_value = timing.get("native_stub_output_json")
        if isinstance(stub_value, str) and stub_value:
            stub_path = _resolve(stub_value)
            if stub_path.exists():
                try:
                    stub = _load_json(stub_path)
                except Exception as exc:
                    failures.append(
                        f"stub_json_load_failed:{exc.__class__.__name__}:{exc}"
                    )
    row_count = _int_metric(execution, "row_count") or 0
    stub_field_hashes: dict[str, str] = {}
    if stub and row_count > 0:
        stub_failures, stub_field_hashes = _check_stub(stub, row_count=row_count)
        failures.extend(stub_failures)
    elif execution:
        failures.append("stub_json_missing")
    execution_sha = _sha256(execution_path) if execution_path.exists() else None
    timing_sha = _sha256(native_path) if native_path is not None and native_path.exists() else None
    stub_path_value = timing.get("native_stub_output_json")
    stub_path = _resolve(stub_path_value) if isinstance(stub_path_value, str) else None
    stub_sha = _sha256(stub_path) if stub_path is not None and stub_path.exists() else None
    useful_hash = (
        _combined_hash(
            execution.get("row_hash_accumulator"),
            execution.get("handle_projection_hash_accumulator"),
            stub.get(f"{STUB_PREFIX}_hash_accumulator"),
            stub.get(f"{STUB_PREFIX}_handle_projection_hash_accumulator"),
            stub_field_hashes,
        )
        if stub_field_hashes
        else None
    )
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_useful_consumer",
        "useful_consumer_name": USEFUL_CONSUMER_NAME,
        "useful_consumer_mode": USEFUL_CONSUMER_MODE,
        "useful_consumer_source": USEFUL_CONSUMER_SOURCE,
        "passed": passed,
        "failures": failures,
        "execution_json": str(execution_path),
        "execution_sha256": execution_sha,
        "native_timing_json": str(native_path) if native_path else None,
        "native_timing_sha256": timing_sha,
        "native_stub_json": str(stub_path) if stub_path else None,
        "native_stub_sha256": stub_sha,
        "source_count": execution.get("source_count"),
        "row_count": execution.get("row_count"),
        "row_ok_count": execution.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": execution.get("field_read_row_ok_counts"),
        "field_read_hashes": execution.get("field_read_hashes"),
        "useful_consumer_ready": passed,
        "useful_consumer_semantics": (
            "wna16_side_variant_all_four_field_projection"
        ),
        "useful_consumer_native_stub_checked": bool(stub),
        "useful_consumer_rows_consumed": row_count if passed else 0,
        "useful_consumer_fields_consumed": list(HANDLE_FIELDS) if passed else [],
        "useful_consumer_field_read_hashes": stub_field_hashes,
        "useful_consumer_hash": useful_hash,
        "wna16_side_consumer_variant_execution_checked": stub.get(
            f"{STUB_PREFIX}_checked"
        ),
        "wna16_side_consumer_variant_execution_row_count": stub.get(
            f"{STUB_PREFIX}_row_count"
        ),
        "wna16_side_consumer_variant_execution_row_ok_count": stub.get(
            f"{STUB_PREFIX}_row_ok_count"
        ),
        "wna16_side_consumer_variant_execution_hash_accumulator": stub.get(
            f"{STUB_PREFIX}_hash_accumulator"
        ),
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": stub.get(
            f"{STUB_PREFIX}_handle_projection_hash_accumulator"
        ),
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
            "future WNA16 typed-slot useful consumer failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the WNA16-side useful typed-slot consumer evidence from "
            "the independent native stub. This still does not pass current "
            "WNA16 fused-MoE args or move payload."
        )
    )
    parser.add_argument("--execution-json", default=str(DEFAULT_EXECUTION_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_useful_consumer(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
