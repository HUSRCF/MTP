#!/usr/bin/env python3
"""Validate the payloadless useful-execution chain for future WNA16 typed slots.

This stage consumes the useful-consumer artifact and promotes it into a
payloadless execution evidence object.  It still does not pass typed slots to
the current WNA16 fused-MoE kernel, does not dereference payloads, and does not
measure vLLM latency or TPOT.
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


DEFAULT_USEFUL_CONSUMER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_useful_consumer_entry_args_ptr_native_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution_entry_args_ptr_native_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
EXECUTION_NAME = "premap_future_wna16_typed_slot_payloadless_useful_execution_v1"
EXECUTION_MODE = "independent_future_wna16_typed_slot_payloadless_useful_execution"
EXECUTION_SOURCE = "premap_future_wna16_typed_slot_kernel_variant_useful_consumer_v1"
NEXT_RUNTIME_STAGE = "promote_future_wna16_typed_slot_payloadless_useful_execution_gate"
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


def _same_path(lhs: str | None, rhs: str | None) -> bool:
    if not lhs or not rhs:
        return False
    return _resolve(lhs).resolve(strict=False) == _resolve(rhs).resolve(strict=False)


def _combined_hash(*parts: Any) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(json.dumps(part, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _check_noop_flags(
    payload: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
    require_benchmark_identity: bool = True,
) -> None:
    expected = {
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
    if require_benchmark_identity:
        expected["benchmark_is_current_wna16_fused_moe"] = False
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")


def _check_useful_consumer(
    useful: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_useful_consumer",
        "useful_consumer_name": "premap_future_wna16_typed_slot_useful_consumer_v1",
        "useful_consumer_mode": "independent_wna16_side_typed_slot_useful_consumer",
        "useful_consumer_source": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        "useful_consumer_semantics": "wna16_side_variant_all_four_field_projection",
        "passed": True,
        "failures": [],
        "useful_consumer_ready": True,
        "useful_consumer_native_stub_checked": True,
        "wna16_side_consumer_variant_execution_checked": True,
    }
    for key, expected_value in expected.items():
        if useful.get(key) != expected_value:
            failures.append(f"useful_{key}_mismatch")
    _check_noop_flags(useful, failures, prefix="useful")
    source_count = _int_metric(useful, "source_count")
    row_count = _int_metric(useful, "row_count")
    row_ok_count = _int_metric(useful, "row_ok_count")
    rows_consumed = _int_metric(useful, "useful_consumer_rows_consumed")
    if source_count is None or source_count < min_source_count:
        failures.append("useful_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("useful_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("useful_row_ok_count_mismatch")
    if row_count is not None and rows_consumed != row_count:
        failures.append("useful_rows_consumed_mismatch")
    if useful.get("field_names") != list(HANDLE_FIELDS):
        failures.append("useful_field_names_mismatch")
    if useful.get("useful_consumer_fields_consumed") != list(HANDLE_FIELDS):
        failures.append("useful_fields_consumed_mismatch")
    row_ok_counts = useful.get("field_read_row_ok_counts")
    field_hashes = useful.get("field_read_hashes")
    useful_hashes = useful.get("useful_consumer_field_read_hashes")
    if not isinstance(row_ok_counts, dict):
        failures.append("useful_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    if not isinstance(field_hashes, dict):
        failures.append("useful_field_read_hashes_missing")
        field_hashes = {}
    if not isinstance(useful_hashes, dict):
        failures.append("useful_consumer_field_read_hashes_missing")
        useful_hashes = {}
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"useful_{field}_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"useful_{field}_field_hash_invalid")
        if not _is_hex_u64(useful_hashes.get(field)):
            failures.append(f"useful_{field}_useful_hash_invalid")
    for key in (
        "useful_consumer_hash",
        f"{STUB_PREFIX}_hash_accumulator",
        f"{STUB_PREFIX}_handle_projection_hash_accumulator",
    ):
        if not _is_hex_u64(useful.get(key)) and key != "useful_consumer_hash":
            failures.append(f"useful_{key}_invalid")
        if key == "useful_consumer_hash" and not _is_sha256_hex(useful.get(key)):
            failures.append(f"useful_{key}_invalid")
    if row_count is not None:
        for key in (
            f"{STUB_PREFIX}_row_count",
            f"{STUB_PREFIX}_row_ok_count",
        ):
            if useful.get(key) != row_count:
                failures.append(f"useful_{key}_mismatch")
    return failures


def _check_execution_child(
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
        "failures": [],
        "payloadless_gate_ready": True,
        "future_wna16_variant_execution_ready": True,
        "future_wna16_variant_execution_native_requested": True,
        "future_wna16_variant_execution_native_executed": True,
        "future_wna16_variant_execution_native_passed": True,
        "future_wna16_variant_execution_native_artifact_ready": True,
        "future_wna16_variant_execution_not_current_wna16_kernel": True,
    }
    for key, expected_value in expected.items():
        if execution.get(key) != expected_value:
            failures.append(f"execution_{key}_mismatch")
    _check_noop_flags(execution, failures, prefix="execution")
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


def _check_timing_child(
    timing: dict[str, Any],
    *,
    execution: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "passed": True,
        "failures": [],
        "timing_stub_ready": True,
        "native_stub_requested": True,
        "native_stub_executed": True,
        "native_stub_passed": True,
    }
    for key, expected_value in expected.items():
        if timing.get(key) != expected_value:
            failures.append(f"timing_{key}_mismatch")
    _check_noop_flags(
        timing,
        failures,
        prefix="timing",
        require_benchmark_identity=False,
    )
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


def _check_useful_execution_consistency(
    useful: dict[str, Any],
    execution: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    for key in ("source_count", "row_count", "row_ok_count", "field_names"):
        if useful.get(key) != execution.get(key):
            failures.append(f"useful_execution_{key}_mismatch")
    useful_row_counts = useful.get("field_read_row_ok_counts")
    execution_row_counts = execution.get("field_read_row_ok_counts")
    if useful_row_counts != execution_row_counts:
        failures.append("useful_execution_field_read_row_ok_counts_mismatch")
    useful_hashes = useful.get("field_read_hashes")
    execution_hashes = execution.get("field_read_hashes")
    if useful_hashes != execution_hashes:
        failures.append("useful_execution_field_read_hashes_mismatch")
    if isinstance(useful_hashes, dict) and isinstance(execution_hashes, dict):
        for field in HANDLE_FIELDS:
            if useful_hashes.get(field) != execution_hashes.get(field):
                failures.append(f"useful_execution_{field}_field_hash_mismatch")
    return failures


def _check_execution_chain(
    useful: dict[str, Any],
    *,
    useful_path: Path,
    min_source_count: int,
    min_row_count: int,
) -> tuple[list[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    failures: list[str] = []
    execution: dict[str, Any] = {}
    timing: dict[str, Any] = {}
    stub: dict[str, Any] = {}

    execution_path_value = useful.get("execution_json")
    if not isinstance(execution_path_value, str) or not execution_path_value:
        failures.append("useful_execution_json_missing")
        return failures, execution, timing, stub
    execution_path = _resolve(execution_path_value)
    if not execution_path.exists():
        failures.append("useful_execution_json_not_found")
        return failures, execution, timing, stub
    actual_execution_sha = _sha256(execution_path)
    if useful.get("execution_sha256") != actual_execution_sha:
        failures.append("useful_execution_sha256_mismatch")
    try:
        execution = _load_json(execution_path)
    except Exception as exc:
        failures.append(f"execution_json_load_failed:{exc.__class__.__name__}:{exc}")
        return failures, execution, timing, stub
    failures.extend(
        _check_execution_child(
            execution,
            min_source_count=min_source_count,
            min_row_count=min_row_count,
        )
    )
    failures.extend(_check_useful_execution_consistency(useful, execution))

    timing_path_value = useful.get("native_timing_json")
    execution_timing_path = execution.get("future_wna16_variant_execution_native_json")
    execution_timing_sha = execution.get("future_wna16_variant_execution_native_sha256")
    if not _same_path(timing_path_value, execution_timing_path):
        failures.append("execution_timing_path_mismatch")
    if timing_path_value and _resolve(timing_path_value).exists():
        actual_timing_sha = _sha256(_resolve(timing_path_value))
        if useful.get("native_timing_sha256") != actual_timing_sha:
            failures.append("useful_native_timing_sha256_mismatch")
        if execution_timing_sha != actual_timing_sha:
            failures.append("execution_native_timing_sha256_mismatch")
        try:
            timing = _load_json(_resolve(timing_path_value))
        except Exception as exc:
            failures.append(f"timing_json_load_failed:{exc.__class__.__name__}:{exc}")
    else:
        failures.append("useful_native_timing_json_missing")
    if timing:
        failures.extend(_check_timing_child(timing, execution=execution))

    stub_path_value = useful.get("native_stub_json")
    timing_stub_path = timing.get("native_stub_output_json")
    timing_stub_sha = timing.get("native_stub_output_sha256")
    if not _same_path(stub_path_value, timing_stub_path):
        failures.append("timing_stub_path_mismatch")
    if stub_path_value and _resolve(stub_path_value).exists():
        actual_stub_sha = _sha256(_resolve(stub_path_value))
        if useful.get("native_stub_sha256") != actual_stub_sha:
            failures.append("useful_native_stub_sha256_mismatch")
        if timing_stub_sha != actual_stub_sha:
            failures.append("timing_native_stub_sha256_mismatch")
        try:
            stub = _load_json(_resolve(stub_path_value))
        except Exception as exc:
            failures.append(f"stub_json_load_failed:{exc.__class__.__name__}:{exc}")
    else:
        failures.append("useful_native_stub_json_missing")

    if useful_path.exists() and useful.get("execution_json") == str(useful_path):
        failures.append("useful_self_referential_execution_json")
    return failures, execution, timing, stub


def _check_stub_backing(
    useful: dict[str, Any],
    stub: dict[str, Any],
    *,
    row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected = {
        "passed": True,
        "failures": [],
        f"{STUB_PREFIX}_checked": True,
        f"{STUB_PREFIX}_payload_bytes": 0,
        f"{STUB_PREFIX}_payload_deref_allowed": False,
        f"{STUB_PREFIX}_kernel_arg_pass_allowed": False,
        f"{STUB_PREFIX}_passed_to_kernel": False,
        f"{STUB_PREFIX}_changes_kernel_launch_args": False,
        f"{STUB_PREFIX}_current_wna16_arg_compatible": False,
        f"{STUB_PREFIX}_requires_wna16_arg_reinterpretation": False,
        f"{STUB_PREFIX}_reuses_current_wna16_arg_slot": False,
        f"{STUB_PREFIX}_error_count": 0,
        f"{STUB_PREFIX}_row_count": row_count,
        f"{STUB_PREFIX}_row_ok_count": row_count,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"stub_{key}_mismatch")
    for key in (
        f"{STUB_PREFIX}_hash_accumulator",
        f"{STUB_PREFIX}_handle_projection_hash_accumulator",
    ):
        if stub.get(key) != useful.get(key):
            failures.append(f"stub_{key}_useful_mismatch")
    useful_hashes = useful.get("useful_consumer_field_read_hashes")
    if not isinstance(useful_hashes, dict):
        useful_hashes = {}
    for field in HANDLE_FIELDS:
        base = f"{STUB_PREFIX}_{field}_read"
        if stub.get(f"{base}_row_count") != row_count:
            failures.append(f"stub_{field}_row_count_mismatch")
        if stub.get(f"{base}_row_ok_count") != row_count:
            failures.append(f"stub_{field}_row_ok_count_mismatch")
        if stub.get(f"{base}_error_count") != 0:
            failures.append(f"stub_{field}_error_count_mismatch")
        if stub.get(f"{base}_hash_accumulator") != useful_hashes.get(field):
            failures.append(f"stub_{field}_hash_useful_mismatch")
    return failures


def run_payloadless_useful_execution(args: argparse.Namespace) -> dict[str, Any]:
    useful_path = _resolve(args.useful_consumer_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    useful: dict[str, Any] = {}
    execution: dict[str, Any] = {}
    timing: dict[str, Any] = {}
    stub: dict[str, Any] = {}
    try:
        useful = _load_json(useful_path)
    except Exception as exc:
        failures.append(f"useful_json_load_failed:{exc.__class__.__name__}:{exc}")
    if useful:
        failures.extend(
            _check_useful_consumer(
                useful,
                min_source_count=args.min_source_count,
                min_row_count=args.min_row_count,
            )
        )
        chain_failures, execution, timing, stub = _check_execution_chain(
            useful,
            useful_path=useful_path,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
        )
        failures.extend(chain_failures)
    row_count = _int_metric(useful, "row_count") or 0
    field_count = len(HANDLE_FIELDS)
    useful_fields_consumed = useful.get("useful_consumer_fields_consumed")
    useful_field_count = (
        len(useful_fields_consumed)
        if isinstance(useful_fields_consumed, list)
        and all(isinstance(field, str) for field in useful_fields_consumed)
        else 0
    )
    useful_rows_consumed = _int_metric(useful, "useful_consumer_rows_consumed") or 0
    useful_work_units = int(useful_rows_consumed) * int(useful_field_count)
    expected_useful_work_units = int(row_count) * int(field_count)
    useful_work_coverage = (
        float(useful_work_units) / float(expected_useful_work_units)
        if expected_useful_work_units > 0
        else 0.0
    )
    if useful and useful_work_units != expected_useful_work_units:
        failures.append("payloadless_useful_work_units_mismatch")
    if stub and row_count > 0:
        failures.extend(_check_stub_backing(useful, stub, row_count=row_count))
    elif useful:
        failures.append("stub_payload_missing")

    useful_sha = _sha256(useful_path) if useful_path.exists() else None
    execution_json = useful.get("execution_json")
    timing_json = useful.get("native_timing_json")
    stub_json = useful.get("native_stub_json")
    chain_hash = (
        _combined_hash(
            useful.get("useful_consumer_hash"),
            useful.get("field_read_hashes"),
            useful.get("useful_consumer_field_read_hashes"),
            useful.get(f"{STUB_PREFIX}_hash_accumulator"),
            useful.get(f"{STUB_PREFIX}_handle_projection_hash_accumulator"),
        )
        if useful
        else None
    )
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "payloadless_useful_execution_name": EXECUTION_NAME,
        "payloadless_useful_execution_mode": EXECUTION_MODE,
        "payloadless_useful_execution_source": EXECUTION_SOURCE,
        "passed": passed,
        "failures": failures,
        "useful_consumer_json": str(useful_path),
        "useful_consumer_sha256": useful_sha,
        "execution_json": execution_json,
        "execution_sha256": useful.get("execution_sha256"),
        "native_timing_json": timing_json,
        "native_timing_sha256": useful.get("native_timing_sha256"),
        "native_stub_json": stub_json,
        "native_stub_sha256": useful.get("native_stub_sha256"),
        "source_count": useful.get("source_count"),
        "row_count": useful.get("row_count"),
        "row_ok_count": useful.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": useful.get("field_read_row_ok_counts"),
        "field_read_hashes": useful.get("field_read_hashes"),
        "useful_consumer_rows_consumed": useful.get("useful_consumer_rows_consumed"),
        "useful_consumer_fields_consumed": useful.get(
            "useful_consumer_fields_consumed"
        ),
        "useful_consumer_field_read_hashes": useful.get(
            "useful_consumer_field_read_hashes"
        ),
        "useful_consumer_hash": useful.get("useful_consumer_hash"),
        "payloadless_useful_execution_field_count": field_count,
        "payloadless_useful_execution_fields_per_row": useful_field_count,
        "payloadless_useful_execution_useful_work_units": useful_work_units,
        "payloadless_useful_execution_expected_useful_work_units": (
            expected_useful_work_units
        ),
        "payloadless_useful_execution_useful_work_coverage": useful_work_coverage,
        "payloadless_useful_execution_useful_work_kind": (
            "native_typed_slot_four_field_row_projection"
        ),
        "payloadless_useful_execution_native_consumer_has_useful_work": (
            passed and useful_work_units > 0
        ),
        "wna16_side_consumer_variant_execution_hash_accumulator": useful.get(
            f"{STUB_PREFIX}_hash_accumulator"
        ),
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": useful.get(
            f"{STUB_PREFIX}_handle_projection_hash_accumulator"
        ),
        "payloadless_useful_execution_ready": passed,
        "payloadless_useful_execution_gate_ready": passed,
        "payloadless_useful_execution_chain_checked": passed
        and bool(execution and timing and stub),
        "payloadless_useful_execution_native_stub_checked": passed and bool(stub),
        "payloadless_useful_execution_rows_consumed": row_count if passed else 0,
        "payloadless_useful_execution_chain_hash": chain_hash,
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
            "future WNA16 typed-slot payloadless useful execution failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate payloadless useful execution from the future WNA16 "
            "typed-slot useful-consumer artifact. This does not pass current "
            "WNA16 fused-MoE args, dereference payloads, or measure TPOT."
        )
    )
    parser.add_argument(
        "--useful-consumer-json",
        default=str(DEFAULT_USEFUL_CONSUMER_JSON),
    )
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=513)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_payloadless_useful_execution(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
