#!/usr/bin/env python3
"""Run the future WNA16 typed-slot second-field handoff canary gate.

This stage requires the first-field canary gate to have passed on
``scale_metadata_handle``.  It then runs the same independent future typed-slot
native path on a second field, defaulting to the metadata-only
``aux_metadata_handle``.  It remains readonly: live handoff is disabled, current
WNA16 fused-MoE kernel arguments are not passed or reinterpreted, and no payload
is dereferenced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import (  # noqa: E402
    run_premap_online_merged_native_arg_slot_canary as canary_runner,
)


DEFAULT_FIRST_FIELD_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary_v3_default.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_second_field_handoff_canary_v3_default.json"
)
DEFAULT_CANARY_OUTPUT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_second_field_handoff_canary"
)

CANARY_NAME = "premap_future_wna16_typed_slot_second_field_handoff_canary_v1"
CANARY_MODE = "readonly_future_wna16_typed_slot_second_field_handoff_canary"
CANARY_SOURCE = "premap_future_wna16_typed_slot_one_field_handoff_canary_v1"
NEXT_RUNTIME_STAGE = (
    "implement_future_wna16_typed_slot_kernel_variant_third_field_handoff_canary"
)
FIRST_FIELD = "scale_metadata_handle"
DEFAULT_SECOND_FIELD = "aux_metadata_handle"
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
FIELD_KINDS = {
    "descriptor_ptr": 1,
    "packed_weight_descriptor": 2,
    "scale_metadata_handle": 3,
    "aux_metadata_handle": 4,
}
SINGLE_FIELD_NAME = "premap_future_wna16_single_field_handoff_canary_v1"
SINGLE_FIELD_MODE = "readonly_future_wna16_single_field_handoff_canary"
SINGLE_FIELD_SOURCE = "premap_future_wna16_kernel_side_consumer_execution_v1"
SINGLE_FIELD_READ_PATH = (
    "future_wna16_single_field_handoff_to_"
    "future_wna16_kernel_side_execution_to_accepted_typed_slot_to_program_view_rows"
)
RUNNER_SOURCE = "online_merged_future_native_arg_slot_canary_runner"


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


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not (1 <= len(value) <= 16):
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 < parsed <= 0xFFFFFFFFFFFFFFFF


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _false_like(value: Any) -> bool:
    return value is None or value is False or value == 0


def _required_false_failures(prefix: str, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    unsafe_keys = (
        "measures_vllm_latency",
        "measures_tpot",
        "wna16_benchmark_ready",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "current_wna16_arg_compatible",
        "requires_wna16_arg_reinterpretation",
        "payload_deref_allowed",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
    )
    for key in unsafe_keys:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
            continue
        if not _false_like(payload.get(key)):
            failures.append(f"{prefix}_{key}_unsafe_nonzero:{payload.get(key)!r}")
    if "payload_bytes" not in payload:
        failures.append(f"{prefix}_payload_bytes_missing")
        return failures
    if not _false_like(payload.get("payload_bytes")):
        failures.append(f"{prefix}_payload_bytes_nonzero:{payload.get('payload_bytes')!r}")
    return failures


def _native_safety_failures(prefix: str, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected = {
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "future_wna16_single_field_handoff_canary_live_enabled": False,
        "future_wna16_single_field_handoff_canary_payload_bytes": 0,
        "future_wna16_single_field_handoff_canary_passed_to_kernel": False,
        "future_wna16_single_field_handoff_canary_changes_kernel_launch_args": False,
        "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible": False,
        "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation": False,
        "future_wna16_single_field_handoff_canary_explicit_typed_abi_slot": True,
        "future_wna16_single_field_handoff_canary_reuses_current_wna16_arg_slot": False,
        "future_wna16_kernel_side_consumer_execution_payload_bytes": 0,
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed": False,
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed": False,
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel": False,
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args": False,
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible": False,
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            failures.append(f"{prefix}_{key}_mismatch:{payload.get(key)!r}!={value!r}")
    return failures


def _check_bound_evidence_file(
    *,
    prefix: str,
    payload: dict[str, Any],
    path_key: str,
    sha_key: str,
) -> list[str]:
    failures: list[str] = []
    path_value = payload.get(path_key)
    sha_value = payload.get(sha_key)
    if not isinstance(path_value, str) or not path_value:
        failures.append(f"{prefix}_{path_key}_missing")
        return failures
    if not _is_sha256_hex(sha_value):
        failures.append(f"{prefix}_{sha_key}_invalid")
        return failures
    path = _resolve(path_value)
    try:
        actual_sha = _sha256(path)
    except Exception as exc:
        failures.append(
            f"{prefix}_{sha_key}_failed:{exc.__class__.__name__}:{exc}"
        )
    else:
        if actual_sha != sha_value:
            failures.append(f"{prefix}_{sha_key}_mismatch")
    return failures


def _check_first_field(
    first: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected = {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary"
        ),
        "one_field_handoff_canary_name": (
            "premap_future_wna16_typed_slot_one_field_handoff_canary_v1"
        ),
        "one_field_handoff_canary_mode": (
            "readonly_future_wna16_typed_slot_one_field_handoff_canary"
        ),
        "passed": True,
        "one_field_handoff_canary_ready": True,
        "one_field_handoff_canary_native_requested": True,
        "one_field_handoff_canary_native_executed": True,
        "one_field_handoff_canary_native_passed": True,
        "one_field_handoff_field_name": FIRST_FIELD,
        "one_field_handoff_live_enabled": False,
        "one_field_handoff_block_reason": "one_field_handoff_live_disabled",
        "payloadless_execution_gate_ready": True,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary"
        ),
    }
    for key, value in expected.items():
        if first.get(key) != value:
            failures.append(f"first_{key}_mismatch:{first.get(key)!r}!={value!r}")
    if first.get("failures") != []:
        failures.append("first_failures_not_empty")
    source_count = _int_metric(first, "source_count")
    row_count = _int_metric(first, "row_count")
    row_ok_count = _int_metric(first, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("first_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("first_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("first_row_ok_count_mismatch")
    payloadless_row_count = _int_metric(first, "payloadless_row_count")
    if row_count is not None and payloadless_row_count != row_count:
        failures.append("first_payloadless_row_count_mismatch")
    runner_rows = _int_metric(first, "one_field_handoff_canary_runner_row_count")
    runner_ok_rows = _int_metric(first, "one_field_handoff_canary_runner_row_ok_count")
    if row_count is not None and runner_rows != row_count:
        failures.append("first_runner_row_count_mismatch")
    if row_count is not None and runner_ok_rows != row_count:
        failures.append("first_runner_row_ok_count_mismatch")
    if not _is_hex_u64(first.get("one_field_handoff_field_read_hash")):
        failures.append("first_field_read_hash_invalid")
    if not _is_hex_u64(first.get("one_field_handoff_canary_runner_hash")):
        failures.append("first_runner_hash_invalid")
    payloadless_path_value = first.get("payloadless_execution_json")
    payloadless_sha_value = first.get("payloadless_execution_sha256")
    payloadless: dict[str, Any] | None = None
    if not isinstance(payloadless_path_value, str) or not payloadless_path_value:
        failures.append("first_payloadless_execution_json_missing")
    elif not _is_sha256_hex(payloadless_sha_value):
        failures.append("first_payloadless_execution_sha256_invalid")
    else:
        payloadless_path = _resolve(payloadless_path_value)
        try:
            actual_sha = _sha256(payloadless_path)
        except Exception as exc:
            failures.append(
                f"first_payloadless_execution_sha256_failed:"
                f"{exc.__class__.__name__}:{exc}"
            )
        else:
            if actual_sha != payloadless_sha_value:
                failures.append("first_payloadless_execution_sha256_mismatch")
            else:
                try:
                    payloadless = _load_json(payloadless_path)
                except Exception as exc:
                    failures.append(
                        f"first_payloadless_execution_json_load_failed:"
                        f"{exc.__class__.__name__}:{exc}"
                    )
    payloadless_hashes = first.get("payloadless_field_read_hashes")
    payloadless_counts = first.get("payloadless_field_read_row_ok_counts")
    if not isinstance(payloadless_hashes, dict):
        failures.append("first_payloadless_field_read_hashes_missing")
    elif payloadless_hashes.get(FIRST_FIELD) != first.get("one_field_handoff_field_read_hash"):
        failures.append("first_payloadless_first_field_hash_summary_mismatch")
    if not isinstance(payloadless_counts, dict):
        failures.append("first_payloadless_field_read_row_ok_counts_missing")
    elif row_count is not None and payloadless_counts.get(FIRST_FIELD) != row_count:
        failures.append("first_payloadless_first_field_row_ok_count_summary_mismatch")
    if payloadless is not None:
        if payloadless.get("passed") is not True:
            failures.append("first_payloadless_execution_passed_mismatch")
        if payloadless.get("source_count") != source_count:
            failures.append("first_payloadless_source_count_summary_mismatch")
        if payloadless.get("row_count") != row_count:
            failures.append("first_payloadless_row_count_summary_mismatch")
        if payloadless.get("field_read_hashes") != payloadless_hashes:
            failures.append("first_payloadless_field_read_hashes_artifact_mismatch")
        if payloadless.get("field_read_row_ok_counts") != payloadless_counts:
            failures.append(
                "first_payloadless_field_read_row_ok_counts_artifact_mismatch"
            )
    all_four_expected = {
        "payloadless_all_four_field_consumer_ready": True,
        "payloadless_all_four_field_consumer_fields_read": True,
        "payloadless_all_four_field_consumer_hashes_valid": True,
    }
    for key, value in all_four_expected.items():
        if first.get(key) != value:
            failures.append(f"first_{key}_mismatch:{first.get(key)!r}!={value!r}")
    all_four_source_count = _int_metric(
        first,
        "payloadless_all_four_field_consumer_source_count",
    )
    all_four_row_count = _int_metric(
        first,
        "payloadless_all_four_field_consumer_row_count",
    )
    all_four_row_ok_count = _int_metric(
        first,
        "payloadless_all_four_field_consumer_row_ok_count",
    )
    if source_count is not None and all_four_source_count != source_count:
        failures.append("first_payloadless_all_four_source_count_mismatch")
    if row_count is not None and all_four_row_count != row_count:
        failures.append("first_payloadless_all_four_row_count_mismatch")
    if row_count is not None and all_four_row_ok_count != row_count:
        failures.append("first_payloadless_all_four_row_ok_count_mismatch")
    fourth_path = first.get("payloadless_fourth_field_handoff_evidence_path")
    fourth_sha = first.get("payloadless_fourth_field_handoff_evidence_sha256")
    all_four_fourth_path = first.get(
        "payloadless_all_four_field_consumer_fourth_field_path_label"
    )
    all_four_fourth_sha = first.get(
        "payloadless_all_four_field_consumer_fourth_field_sha256"
    )
    if fourth_path != all_four_fourth_path:
        failures.append("first_payloadless_fourth_path_all_four_mismatch")
    if fourth_sha != all_four_fourth_sha:
        failures.append("first_payloadless_fourth_sha_all_four_mismatch")
    failures.extend(
        _check_bound_evidence_file(
            prefix="first_payloadless_fourth_field_handoff_evidence",
            payload=first,
            path_key="payloadless_fourth_field_handoff_evidence_path",
            sha_key="payloadless_fourth_field_handoff_evidence_sha256",
        )
    )
    failures.extend(_required_false_failures("first", first))
    return failures


def _first_runner_input_paths(first: dict[str, Any]) -> tuple[list[Path], list[str]]:
    failures: list[str] = []
    runner_json_value = first.get("canary_runner_json")
    runner_sha_value = first.get("canary_runner_sha256")
    if not isinstance(runner_json_value, str) or not runner_json_value:
        return [], ["first_canary_runner_json_missing"]
    if not _is_sha256_hex(runner_sha_value):
        return [], ["first_canary_runner_sha256_invalid"]
    runner_path = _resolve(runner_json_value)
    try:
        actual_sha = _sha256(runner_path)
    except Exception as exc:
        return [], [
            f"first_canary_runner_sha256_failed:{exc.__class__.__name__}:{exc}"
        ]
    if actual_sha != runner_sha_value:
        failures.append("first_canary_runner_sha256_mismatch")
    try:
        runner = _load_json(runner_path)
    except Exception as exc:
        return [], [
            *failures,
            f"first_canary_runner_json_load_failed:{exc.__class__.__name__}:{exc}",
        ]
    input_values = runner.get("input_jsons")
    if not isinstance(input_values, list) or not input_values:
        return [], [*failures, "first_canary_runner_input_jsons_missing"]
    input_paths: list[Path] = []
    for index, value in enumerate(input_values):
        if not isinstance(value, str) or not value:
            failures.append(f"first_canary_runner_input_json_{index}_invalid")
            continue
        input_paths.append(_resolve(value))
    return input_paths, failures


def _check_first_native_runner(
    first: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> tuple[list[Path], list[str]]:
    input_paths, failures = _first_runner_input_paths(first)
    runner_json_value = first.get("canary_runner_json")
    if not isinstance(runner_json_value, str) or not runner_json_value:
        return input_paths, failures
    try:
        runner = _load_json(_resolve(runner_json_value))
    except Exception:
        return input_paths, failures
    expected = {
        "passed": True,
        "source": RUNNER_SOURCE,
        "mirror_field": FIRST_FIELD,
        "require_future_wna16_single_field_handoff_canary": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_wna16_adjacent_typed_slot": True,
        "future_wna16_single_field_handoff_canary_checked": True,
        "future_wna16_single_field_handoff_canary_name": SINGLE_FIELD_NAME,
        "future_wna16_single_field_handoff_canary_abi_name": SINGLE_FIELD_NAME,
        "future_wna16_single_field_handoff_canary_mode": SINGLE_FIELD_MODE,
        "future_wna16_single_field_handoff_canary_source": SINGLE_FIELD_SOURCE,
        "future_wna16_single_field_handoff_canary_field_read_path": (
            SINGLE_FIELD_READ_PATH
        ),
        "future_wna16_single_field_handoff_canary_field_name": FIRST_FIELD,
        "future_wna16_single_field_handoff_canary_field_kind": FIELD_KINDS[FIRST_FIELD],
        "future_wna16_single_field_handoff_canary_field_mask": (
            1 << (FIELD_KINDS[FIRST_FIELD] - 1)
        ),
        "future_wna16_single_field_handoff_canary_error_count": 0,
        "future_wna16_single_field_handoff_canary_live_enabled": False,
        "future_wna16_single_field_handoff_canary_passed_to_kernel": False,
        "future_wna16_single_field_handoff_canary_changes_kernel_launch_args": False,
        "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible": False,
        "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation": False,
    }
    for key, value in expected.items():
        if runner.get(key) != value:
            failures.append(f"first_runner_{key}_mismatch:{runner.get(key)!r}!={value!r}")
    source_count = _int_metric(runner, "selected_source_count")
    merged_row_count = _int_metric(runner, "merged_row_count")
    dispatch_rows = _int_metric(runner, "dispatch_active_rows")
    runner_rows = _int_metric(runner, "future_wna16_single_field_handoff_canary_row_count")
    runner_ok_rows = _int_metric(
        runner, "future_wna16_single_field_handoff_canary_row_ok_count"
    )
    if source_count is None or source_count < min_source_count:
        failures.append("first_runner_source_count_invalid")
    if merged_row_count is None or merged_row_count < min_row_count:
        failures.append("first_runner_merged_row_count_invalid")
    if source_count != first.get("source_count"):
        failures.append("first_runner_source_count_summary_mismatch")
    if merged_row_count != first.get("row_count"):
        failures.append("first_runner_row_count_summary_mismatch")
    if dispatch_rows != first.get("row_count"):
        failures.append("first_runner_dispatch_rows_summary_mismatch")
    if runner_rows != first.get("row_count"):
        failures.append("first_runner_single_field_row_count_summary_mismatch")
    if runner_ok_rows != first.get("row_count"):
        failures.append("first_runner_single_field_row_ok_count_summary_mismatch")
    runner_hash = runner.get("future_wna16_single_field_handoff_canary_hash_accumulator")
    if not _is_hex_u64(runner_hash):
        failures.append("first_runner_single_field_hash_invalid")
    elif runner_hash != first.get("one_field_handoff_canary_runner_hash"):
        failures.append("first_runner_single_field_hash_summary_mismatch")
    failures.extend(_native_safety_failures("first_runner", runner))
    return input_paths, failures


def _check_second_report(
    second: dict[str, Any],
    *,
    first: dict[str, Any],
    second_field: str,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected = {
        "passed": True,
        "source": RUNNER_SOURCE,
        "mirror_field": second_field,
        "require_future_wna16_single_field_handoff_canary": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_wna16_adjacent_typed_slot": True,
        "future_wna16_single_field_handoff_canary_checked": True,
        "future_wna16_single_field_handoff_canary_name": SINGLE_FIELD_NAME,
        "future_wna16_single_field_handoff_canary_abi_name": SINGLE_FIELD_NAME,
        "future_wna16_single_field_handoff_canary_mode": SINGLE_FIELD_MODE,
        "future_wna16_single_field_handoff_canary_source": SINGLE_FIELD_SOURCE,
        "future_wna16_single_field_handoff_canary_field_read_path": (
            SINGLE_FIELD_READ_PATH
        ),
        "future_wna16_single_field_handoff_canary_field_name": second_field,
        "future_wna16_single_field_handoff_canary_field_kind": FIELD_KINDS[second_field],
        "future_wna16_single_field_handoff_canary_field_mask": (
            1 << (FIELD_KINDS[second_field] - 1)
        ),
        "future_wna16_single_field_handoff_canary_error_count": 0,
    }
    for key, value in expected.items():
        if second.get(key) != value:
            failures.append(f"second_{key}_mismatch:{second.get(key)!r}!={value!r}")
    source_count = _int_metric(second, "selected_source_count")
    row_count = _int_metric(second, "merged_row_count")
    dispatch_rows = _int_metric(second, "dispatch_active_rows")
    field_rows = _int_metric(second, "future_wna16_single_field_handoff_canary_row_count")
    field_ok_rows = _int_metric(
        second, "future_wna16_single_field_handoff_canary_row_ok_count"
    )
    if source_count is None or source_count < min_source_count:
        failures.append("second_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("second_row_count_invalid")
    if source_count != first.get("source_count"):
        failures.append("second_source_count_first_mismatch")
    if row_count != first.get("row_count"):
        failures.append("second_row_count_first_mismatch")
    if dispatch_rows != first.get("row_count"):
        failures.append("second_dispatch_rows_first_mismatch")
    if field_rows != first.get("row_count"):
        failures.append("second_single_field_row_count_first_mismatch")
    if field_ok_rows != first.get("row_count"):
        failures.append("second_single_field_row_ok_count_first_mismatch")
    payloadless_hashes = first.get("payloadless_field_read_hashes")
    if not isinstance(payloadless_hashes, dict):
        failures.append("first_payloadless_field_read_hashes_missing")
    elif not _is_hex_u64(payloadless_hashes.get(second_field)):
        failures.append("second_payloadless_selected_field_hash_invalid")
    payloadless_counts = first.get("payloadless_field_read_row_ok_counts")
    if not isinstance(payloadless_counts, dict):
        failures.append("first_payloadless_field_read_row_ok_counts_missing")
    elif payloadless_counts.get(second_field) != first.get("row_count"):
        failures.append("second_payloadless_selected_field_row_ok_count_mismatch")
    second_hash = second.get("future_wna16_single_field_handoff_canary_hash_accumulator")
    if not _is_hex_u64(second_hash):
        failures.append("second_field_read_hash_invalid")
    failures.extend(_native_safety_failures("second", second))
    return failures


def _check_second_underlying_json(
    underlying_json: Path,
    second: dict[str, Any] | None,
) -> tuple[str | None, list[str]]:
    failures: list[str] = []
    if second is None:
        return None, failures
    if not underlying_json.exists():
        return None, ["second_field_underlying_json_missing"]
    try:
        underlying_sha256 = _sha256(underlying_json)
        underlying = _load_json(underlying_json)
    except Exception as exc:
        return None, [
            f"second_field_underlying_json_load_failed:{exc.__class__.__name__}:{exc}"
        ]
    checked_keys = (
        "passed",
        "source",
        "mirror_field",
        "input_jsons",
        "selected_source_count",
        "merged_row_count",
        "dispatch_active_rows",
        "future_wna16_single_field_handoff_canary_field_name",
        "future_wna16_single_field_handoff_canary_name",
        "future_wna16_single_field_handoff_canary_abi_name",
        "future_wna16_single_field_handoff_canary_mode",
        "future_wna16_single_field_handoff_canary_source",
        "future_wna16_single_field_handoff_canary_field_read_path",
        "future_wna16_single_field_handoff_canary_field_kind",
        "future_wna16_single_field_handoff_canary_field_mask",
        "future_wna16_single_field_handoff_canary_error_count",
        "future_wna16_single_field_handoff_canary_hash_accumulator",
        "future_wna16_single_field_handoff_canary_row_count",
        "future_wna16_single_field_handoff_canary_row_ok_count",
        "future_wna16_single_field_handoff_canary_payload_bytes",
        "future_wna16_single_field_handoff_canary_passed_to_kernel",
        "future_wna16_single_field_handoff_canary_changes_kernel_launch_args",
        "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible",
    )
    for key in checked_keys:
        if underlying.get(key) != second.get(key):
            failures.append(
                f"second_field_underlying_{key}_report_mismatch:"
                f"{underlying.get(key)!r}!={second.get(key)!r}"
            )
    failures.extend(_native_safety_failures("second_field_underlying", underlying))
    return underlying_sha256, failures


def _build_one_field_args(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> argparse.Namespace:
    canary_dir = _resolve(args.canary_output_dir)
    argv = [
        "--max-inputs",
        str(args.max_inputs),
        "--min-source-count",
        str(args.min_source_count),
        "--min-total-rows",
        str(args.min_row_count),
        "--block-threads",
        str(args.block_threads),
        "--mirror-field",
        str(args.second_field),
        "--require-future-wna16-single-field-handoff-canary",
        "--device",
        str(args.device),
        "--offload-arch",
        str(args.offload_arch),
        "--merged-output-json",
        str(canary_dir / "second_field_merged_input.json"),
        "--stub-output-json",
        str(canary_dir / "second_field_typed_consumer_stub.json"),
        "--output-json",
        str(canary_dir / "second_field_native_canary_runner.json"),
    ]
    for input_path in input_paths:
        argv.extend(["--input-json", str(input_path)])
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.force_build:
        argv.append("--force-build")
    parsed = canary_runner.build_parser().parse_args(argv)
    parsed.runner_json = None
    return parsed


def _run_second_field_native(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> tuple[dict[str, Any], float]:
    one_field_args = _build_one_field_args(args, input_paths=input_paths)
    start_ns = time.perf_counter_ns()
    report = canary_runner.run_canary(one_field_args)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def run_second_field_handoff_canary(args: argparse.Namespace) -> dict[str, Any]:
    first_path = _resolve(args.first_field_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    first: dict[str, Any] = {}
    try:
        first = _load_json(first_path)
    except Exception as exc:
        failures.append(f"first_field_json_load_failed:{exc.__class__.__name__}:{exc}")
    first_sha256: str | None = None
    if first_path.exists():
        try:
            first_sha256 = _sha256(first_path)
        except Exception as exc:
            failures.append(
                f"first_field_json_sha256_failed:{exc.__class__.__name__}:{exc}"
            )
    if args.second_field == FIRST_FIELD:
        failures.append("second_field_must_differ_from_first_field")
    if first:
        failures.extend(
            _check_first_field(
                first,
                min_source_count=args.min_source_count,
                min_row_count=args.min_row_count,
            )
        )
    first_input_paths: list[Path] = []
    if first:
        first_input_paths, first_runner_failures = _check_first_native_runner(
            first,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
        )
        failures.extend(first_runner_failures)
    if not args.run_native_canary:
        failures.append("run_native_canary_must_remain_enabled_for_lab_gate")
    if not args.require_native_canary:
        failures.append("require_native_canary_must_remain_enabled_for_lab_gate")
    first_gate_ready = bool(first) and not failures
    second_report: dict[str, Any] | None = None
    second_outer_wall_ms: float | None = None
    if args.run_native_canary and first_gate_ready:
        try:
            second_report, second_outer_wall_ms = _run_second_field_native(
                args,
                input_paths=first_input_paths,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            failures.append(
                f"second_field_handoff_canary_exception:"
                f"{exc.__class__.__name__}:{exc}"
            )
        if second_report is not None:
            failures.extend(
                _check_second_report(
                    second_report,
                    first=first,
                    second_field=args.second_field,
                    min_source_count=args.min_source_count,
                    min_row_count=args.min_row_count,
                )
            )
    elif args.run_native_canary:
        failures.append("second_field_canary_skipped_due_to_first_gate_failure")
    if args.require_native_canary and second_report is None:
        failures.append("second_field_handoff_canary_required_but_not_executed")
    passed = not failures
    canary_dir = _resolve(args.canary_output_dir)
    underlying_json = canary_dir / "second_field_native_canary_runner.json"
    underlying_sha256, underlying_failures = _check_second_underlying_json(
        underlying_json,
        second_report,
    )
    if underlying_failures:
        failures.extend(underlying_failures)
        passed = False
    payloadless_hashes = first.get("payloadless_field_read_hashes")
    payloadless_counts = first.get("payloadless_field_read_row_ok_counts")
    second_field_payloadless_hash = (
        payloadless_hashes.get(args.second_field)
        if isinstance(payloadless_hashes, dict)
        else None
    )
    second_field_payloadless_row_ok = (
        payloadless_counts.get(args.second_field)
        if isinstance(payloadless_counts, dict)
        else None
    )
    second_source_count = (
        second_report.get("selected_source_count")
        if second_report
        else first.get("source_count")
    )
    second_row_count = (
        second_report.get("merged_row_count")
        if second_report
        else first.get("row_count")
    )
    second_row_ok_count = (
        second_report.get("future_wna16_single_field_handoff_canary_row_ok_count")
        if second_report
        else None
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_second_field_handoff_canary"
        ),
        "second_field_handoff_canary_name": CANARY_NAME,
        "second_field_handoff_canary_mode": CANARY_MODE,
        "second_field_handoff_canary_source": CANARY_SOURCE,
        "passed": passed,
        "failures": failures,
        "first_field_json": str(first_path),
        "first_field_sha256": first_sha256,
        "first_field_canary_runner_json": first.get("canary_runner_json"),
        "first_field_canary_runner_sha256": first.get("canary_runner_sha256"),
        "first_field_input_json_count": len(first_input_paths),
        "first_field_gate_ready": first_gate_ready,
        "first_field_name": FIRST_FIELD,
        "first_field_read_hash": first.get("one_field_handoff_field_read_hash"),
        "first_field_native_hash": first.get("one_field_handoff_canary_runner_hash"),
        "second_field_name": args.second_field,
        "second_field_kind": FIELD_KINDS.get(str(args.second_field)),
        "second_field_mask": (
            1 << (FIELD_KINDS[str(args.second_field)] - 1)
            if args.second_field in FIELD_KINDS
            else None
        ),
        "second_field_underlying_json": str(underlying_json),
        "second_field_underlying_sha256": underlying_sha256,
        "payloadless_execution_json": first.get("payloadless_execution_json"),
        "payloadless_execution_sha256": first.get("payloadless_execution_sha256"),
        "payloadless_fourth_field_handoff_evidence_path": first.get(
            "payloadless_fourth_field_handoff_evidence_path"
        ),
        "payloadless_fourth_field_handoff_evidence_sha256": first.get(
            "payloadless_fourth_field_handoff_evidence_sha256"
        ),
        "payloadless_all_four_field_consumer_ready": first.get(
            "payloadless_all_four_field_consumer_ready"
        ),
        "payloadless_all_four_field_consumer_fields_read": first.get(
            "payloadless_all_four_field_consumer_fields_read"
        ),
        "payloadless_all_four_field_consumer_hashes_valid": first.get(
            "payloadless_all_four_field_consumer_hashes_valid"
        ),
        "payloadless_all_four_field_consumer_source_count": first.get(
            "payloadless_all_four_field_consumer_source_count"
        ),
        "payloadless_all_four_field_consumer_row_count": first.get(
            "payloadless_all_four_field_consumer_row_count"
        ),
        "payloadless_all_four_field_consumer_row_ok_count": first.get(
            "payloadless_all_four_field_consumer_row_ok_count"
        ),
        "payloadless_all_four_field_consumer_fourth_field_path_label": first.get(
            "payloadless_all_four_field_consumer_fourth_field_path_label"
        ),
        "payloadless_all_four_field_consumer_fourth_field_sha256": first.get(
            "payloadless_all_four_field_consumer_fourth_field_sha256"
        ),
        "source_count": second_source_count,
        "row_count": second_row_count,
        "row_ok_count": second_row_ok_count,
        "second_field_handoff_field_read_row_ok_count": (
            second_field_payloadless_row_ok
        ),
        "second_field_handoff_field_read_hash": second_field_payloadless_hash,
        "second_field_handoff_canary_runner_hash": (
            second_report.get("future_wna16_single_field_handoff_canary_hash_accumulator")
            if second_report
            else None
        ),
        "second_field_handoff_canary_runner_row_count": (
            second_report.get("future_wna16_single_field_handoff_canary_row_count")
            if second_report
            else None
        ),
        "second_field_handoff_canary_runner_row_ok_count": second_row_ok_count,
        "second_field_handoff_canary_native_requested": bool(args.run_native_canary),
        "second_field_handoff_canary_native_executed": second_report is not None,
        "second_field_handoff_canary_native_passed": (
            second_report.get("passed") if second_report else None
        ),
        "second_field_handoff_canary_outer_wall_ms": second_outer_wall_ms,
        "second_field_handoff_live_enabled": False,
        "second_field_handoff_block_reason": "second_field_handoff_live_disabled",
        "second_field_handoff_scope": (
            "independent_future_wna16_typed_slot_second_field_handoff_canary"
        ),
        "expected_measures_vllm_latency": False,
        "expected_measures_tpot": False,
        "expected_wna16_benchmark_ready": False,
        "expected_uses_current_wna16_args": False,
        "expected_passes_current_wna16_args": False,
        "expected_current_wna16_arg_compatible": False,
        "expected_requires_wna16_arg_reinterpretation": False,
        "expected_payload_bytes": 0,
        "expected_payload_deref_allowed": False,
        "expected_kernel_arg_pass_allowed": False,
        "expected_passed_to_kernel": False,
        "expected_changes_kernel_launch_args": False,
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
        "block_threads": int(args.block_threads),
        "device": int(args.device),
        "offload_arch": str(args.offload_arch),
        "hip_visible_devices": args.hip_visible_devices,
        "max_inputs": int(args.max_inputs),
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot second-field handoff canary failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the future WNA16 typed-slot second-field handoff canary. "
            "This requires the scale-metadata first-field gate and keeps live "
            "handoff/current WNA16 args disabled."
        )
    )
    parser.add_argument("--first-field-json", default=str(DEFAULT_FIRST_FIELD_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--canary-output-dir", default=str(DEFAULT_CANARY_OUTPUT_DIR))
    parser.add_argument(
        "--second-field",
        choices=sorted(HANDLE_FIELDS),
        default=DEFAULT_SECOND_FIELD,
    )
    parser.add_argument("--max-inputs", type=int, default=128)
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--run-native-canary",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-native-canary",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_second_field_handoff_canary(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
