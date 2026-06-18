#!/usr/bin/env python3
"""Run the future WNA16 typed-slot fourth-field handoff canary gate.

This stage requires the third-field canary gate to have passed on
``packed_weight_descriptor``. It reuses that gate's persisted native runner
``input_jsons`` and runs the independent future typed-slot native path on the
fourth field, defaulting to ``descriptor_ptr``. It remains readonly:
live handoff is disabled, current WNA16 fused-MoE kernel arguments are not
passed or reinterpreted, and no payload is dereferenced.
"""

from __future__ import annotations

import argparse
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
from scripts import (  # noqa: E402
    run_future_wna16_typed_slot_kernel_variant_third_field_handoff_canary
    as previous_gate,
)
from scripts import (  # noqa: E402
    run_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary
    as abi_contract,
)


DEFAULT_PREVIOUS_FIELD_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_third_field_handoff_canary_v3_default.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v3_default.json"
)
DEFAULT_CANARY_OUTPUT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
)

CANARY_NAME = "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
CANARY_MODE = "readonly_future_wna16_typed_slot_fourth_field_handoff_canary"
CANARY_SOURCE = "premap_future_wna16_typed_slot_third_field_handoff_canary_v1"
FIRST_FIELD = "scale_metadata_handle"
SECOND_FIELD = "aux_metadata_handle"
PREVIOUS_FIELD = "packed_weight_descriptor"
DEFAULT_FOURTH_FIELD = "descriptor_ptr"
NEXT_RUNTIME_STAGE = (
    "promote_future_wna16_typed_slot_all_four_field_handoff_gate_to_lab_preflight"
)

HANDLE_FIELDS = previous_gate.HANDLE_FIELDS
FIELD_KINDS = previous_gate.FIELD_KINDS


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _resolve_artifact_reference(
    value: Any,
    *,
    roots: list[Path],
    label: str,
) -> tuple[Path | None, list[str]]:
    if not isinstance(value, str) or not value:
        return None, [f"{label}_missing"]
    resolved = _resolve(value)
    if not any(_is_relative_to(resolved, root) for root in roots):
        return resolved, [f"{label}_outside_allowed_roots:{resolved}"]
    return resolved, []


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return previous_gate._sha256(path)


def _is_sha256_hex(value: Any) -> bool:
    return previous_gate._is_sha256_hex(value)


def _is_hex_u64(value: Any) -> bool:
    return previous_gate._is_hex_u64(value)


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    return previous_gate._int_metric(payload, key)


def _required_false_failures(prefix: str, payload: dict[str, Any]) -> list[str]:
    return previous_gate._required_false_failures(prefix, payload)


def _native_safety_failures(prefix: str, payload: dict[str, Any]) -> list[str]:
    return previous_gate._native_safety_failures(prefix, payload)


def _native_top_level_safety_failures(
    prefix: str,
    payload: dict[str, Any],
) -> list[str]:
    return previous_gate._native_top_level_safety_failures(  # noqa: SLF001
        prefix,
        payload,
    )


def _check_bound_evidence_file(
    *,
    prefix: str,
    payload: dict[str, Any],
    path_key: str,
    sha_key: str,
) -> list[str]:
    return previous_gate._check_bound_evidence_file(  # noqa: SLF001
        prefix=prefix,
        payload=payload,
        path_key=path_key,
        sha_key=sha_key,
    )


def _raw_runner_expected(field: str) -> dict[str, Any]:
    field_kind = FIELD_KINDS[field]
    return {
        "passed": True,
        "source": abi_contract.RUNNER_SOURCE,
        "mirror_field": field,
        "require_future_wna16_single_field_handoff_canary": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_wna16_adjacent_typed_slot": True,
        "future_wna16_single_field_handoff_canary_checked": True,
        "future_wna16_single_field_handoff_canary_name": abi_contract.SINGLE_FIELD_NAME,
        "future_wna16_single_field_handoff_canary_abi_name": (
            abi_contract.SINGLE_FIELD_NAME
        ),
        "future_wna16_single_field_handoff_canary_mode": abi_contract.SINGLE_FIELD_MODE,
        "future_wna16_single_field_handoff_canary_source": (
            abi_contract.SINGLE_FIELD_SOURCE
        ),
        "future_wna16_single_field_handoff_canary_field_read_path": (
            abi_contract.SINGLE_FIELD_READ_PATH
        ),
        "future_wna16_single_field_handoff_canary_field_name": field,
        "future_wna16_single_field_handoff_canary_field_kind": field_kind,
        "future_wna16_single_field_handoff_canary_field_mask": 1 << (field_kind - 1),
        "future_wna16_single_field_handoff_canary_error_count": 0,
    }


def _input_paths_from_runner(
    runner: dict[str, Any],
    *,
    runner_path: Path,
    prefix: str,
) -> tuple[list[Path], list[str]]:
    failures: list[str] = []
    input_values = runner.get("input_jsons")
    if not isinstance(input_values, list) or not input_values:
        return [], [f"{prefix}_input_jsons_missing"]
    input_paths: list[Path] = []
    for index, value in enumerate(input_values):
        input_path, input_failures = _resolve_artifact_reference(
            value,
            roots=[REPO_ROOT, runner_path.parent],
            label=f"{prefix}_input_json_{index}",
        )
        if input_failures:
            failures.extend(input_failures)
            continue
        if input_path is not None:
            if not input_path.exists():
                failures.append(f"{prefix}_input_json_{index}_missing:{input_path}")
                continue
            if not input_path.is_file():
                failures.append(f"{prefix}_input_json_{index}_not_file:{input_path}")
                continue
            input_paths.append(input_path)
    return input_paths, failures


def _check_raw_runner(
    runner: dict[str, Any],
    *,
    field: str,
    expected_source_count: int | None,
    expected_row_count: int | None,
    expected_hash: str | None,
    min_source_count: int,
    min_row_count: int,
    prefix: str,
) -> list[str]:
    failures: list[str] = []
    for key, value in _raw_runner_expected(field).items():
        if runner.get(key) != value:
            failures.append(f"{prefix}_{key}_mismatch:{runner.get(key)!r}!={value!r}")
    source_count = _int_metric(runner, "selected_source_count")
    merged_row_count = _int_metric(runner, "merged_row_count")
    dispatch_rows = _int_metric(runner, "dispatch_active_rows")
    field_rows = _int_metric(runner, "future_wna16_single_field_handoff_canary_row_count")
    field_ok_rows = _int_metric(
        runner, "future_wna16_single_field_handoff_canary_row_ok_count"
    )
    if source_count is None or source_count < min_source_count:
        failures.append(f"{prefix}_source_count_invalid")
    if merged_row_count is None or merged_row_count < min_row_count:
        failures.append(f"{prefix}_merged_row_count_invalid")
    if expected_source_count is not None and source_count != expected_source_count:
        failures.append(f"{prefix}_source_count_previous_mismatch")
    if expected_row_count is not None and merged_row_count != expected_row_count:
        failures.append(f"{prefix}_row_count_previous_mismatch")
    if expected_row_count is not None and dispatch_rows != expected_row_count:
        failures.append(f"{prefix}_dispatch_rows_previous_mismatch")
    if expected_row_count is not None and field_rows != expected_row_count:
        failures.append(f"{prefix}_single_field_row_count_previous_mismatch")
    if expected_row_count is not None and field_ok_rows != expected_row_count:
        failures.append(f"{prefix}_single_field_row_ok_count_previous_mismatch")
    runner_hash = runner.get("future_wna16_single_field_handoff_canary_hash_accumulator")
    if not _is_hex_u64(runner_hash):
        failures.append(f"{prefix}_single_field_hash_invalid")
    elif expected_hash is not None and runner_hash != expected_hash:
        failures.append(f"{prefix}_single_field_hash_summary_mismatch")
    failures.extend(_native_top_level_safety_failures(prefix, runner))
    failures.extend(_native_safety_failures(prefix, runner))
    return failures


def _load_payloadless_artifact(
    previous: dict[str, Any],
    *,
    previous_path: Path,
    source_count: int | None,
    row_count: int | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    payloadless_sha_value = previous.get("payloadless_execution_sha256")
    payloadless_path, path_failures = _resolve_artifact_reference(
        previous.get("payloadless_execution_json"),
        roots=[REPO_ROOT, previous_path.parent],
        label="previous_payloadless_execution_json",
    )
    if path_failures:
        return None, path_failures
    assert payloadless_path is not None
    if not _is_sha256_hex(payloadless_sha_value):
        return None, ["previous_payloadless_execution_sha256_invalid"]
    try:
        actual_sha = _sha256(payloadless_path)
    except Exception as exc:
        return None, [
            f"previous_payloadless_execution_sha256_failed:"
            f"{exc.__class__.__name__}:{exc}"
        ]
    if actual_sha != payloadless_sha_value:
        failures.append("previous_payloadless_execution_sha256_mismatch")
    try:
        payloadless = _load_json(payloadless_path)
    except Exception as exc:
        return None, [
            *failures,
            f"previous_payloadless_execution_json_load_failed:"
            f"{exc.__class__.__name__}:{exc}",
        ]
    if payloadless.get("passed") is not True:
        failures.append("previous_payloadless_execution_passed_mismatch")
    if payloadless.get("source_count") != source_count:
        failures.append("previous_payloadless_source_count_mismatch")
    if payloadless.get("row_count") != row_count:
        failures.append("previous_payloadless_row_count_mismatch")
    if not isinstance(payloadless.get("field_read_hashes"), dict):
        failures.append("previous_payloadless_field_read_hashes_missing")
    if not isinstance(payloadless.get("field_read_row_ok_counts"), dict):
        failures.append("previous_payloadless_field_read_row_ok_counts_missing")
    return payloadless, failures


def _check_previous_gate(
    previous: dict[str, Any],
    *,
    previous_path: Path,
    fourth_field: str,
    min_source_count: int,
    min_row_count: int,
) -> tuple[list[Path], dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    expected = {
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_third_field_handoff_canary"
        ),
        "third_field_handoff_canary_name": (
            "premap_future_wna16_typed_slot_third_field_handoff_canary_v1"
        ),
        "third_field_handoff_canary_mode": (
            "readonly_future_wna16_typed_slot_third_field_handoff_canary"
        ),
        "third_field_handoff_canary_source": (
            "premap_future_wna16_typed_slot_second_field_handoff_canary_v1"
        ),
        "passed": True,
        "previous_field_gate_ready": True,
        "third_field_handoff_canary_native_requested": True,
        "third_field_handoff_canary_native_executed": True,
        "third_field_handoff_canary_native_passed": True,
        "first_field_name": FIRST_FIELD,
        "second_field_name": SECOND_FIELD,
        "third_field_name": PREVIOUS_FIELD,
        "third_field_handoff_live_enabled": False,
        "third_field_handoff_block_reason": "third_field_handoff_live_disabled",
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
        ),
    }
    for key, value in expected.items():
        if previous.get(key) != value:
            failures.append(f"previous_{key}_mismatch:{previous.get(key)!r}!={value!r}")
    if previous.get("failures") != []:
        failures.append("previous_failures_not_empty")
    source_count = _int_metric(previous, "source_count")
    row_count = _int_metric(previous, "row_count")
    row_ok_count = _int_metric(previous, "row_ok_count")
    if source_count is None or source_count < min_source_count:
        failures.append("previous_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("previous_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("previous_row_ok_count_mismatch")
    if row_count is not None and previous.get("third_field_handoff_canary_runner_row_count") != row_count:
        failures.append("previous_runner_row_count_mismatch")
    if row_count is not None and previous.get("third_field_handoff_canary_runner_row_ok_count") != row_count:
        failures.append("previous_runner_row_ok_count_mismatch")
    if not _is_hex_u64(previous.get("third_field_handoff_field_read_hash")):
        failures.append("previous_third_field_read_hash_invalid")
    if not _is_hex_u64(previous.get("third_field_handoff_canary_runner_hash")):
        failures.append("previous_runner_hash_invalid")
    payloadless, payloadless_failures = _load_payloadless_artifact(
        previous,
        previous_path=previous_path,
        source_count=source_count,
        row_count=row_count,
    )
    failures.extend(payloadless_failures)
    payloadless_hashes = payloadless.get("field_read_hashes") if payloadless else None
    payloadless_counts = (
        payloadless.get("field_read_row_ok_counts") if payloadless else None
    )
    if isinstance(payloadless_hashes, dict):
        if payloadless_hashes.get(PREVIOUS_FIELD) != previous.get(
            "third_field_handoff_field_read_hash"
        ):
            failures.append("previous_payloadless_third_field_hash_mismatch")
        if not _is_hex_u64(payloadless_hashes.get(fourth_field)):
            failures.append("previous_payloadless_default_fourth_field_hash_invalid")
    if isinstance(payloadless_counts, dict):
        if payloadless_counts.get(PREVIOUS_FIELD) != row_count:
            failures.append("previous_payloadless_third_field_row_ok_count_mismatch")
        if payloadless_counts.get(fourth_field) != row_count:
            failures.append("previous_payloadless_default_fourth_field_row_ok_count_mismatch")
    all_four_expected = {
        "payloadless_all_four_field_consumer_ready": True,
        "payloadless_all_four_field_consumer_fields_read": True,
        "payloadless_all_four_field_consumer_hashes_valid": True,
    }
    for key, value in all_four_expected.items():
        if previous.get(key) != value:
            failures.append(f"previous_{key}_mismatch:{previous.get(key)!r}!={value!r}")
    all_four_source_count = _int_metric(
        previous,
        "payloadless_all_four_field_consumer_source_count",
    )
    all_four_row_count = _int_metric(
        previous,
        "payloadless_all_four_field_consumer_row_count",
    )
    all_four_row_ok_count = _int_metric(
        previous,
        "payloadless_all_four_field_consumer_row_ok_count",
    )
    if source_count is not None and all_four_source_count != source_count:
        failures.append("previous_payloadless_all_four_source_count_mismatch")
    if row_count is not None and all_four_row_count != row_count:
        failures.append("previous_payloadless_all_four_row_count_mismatch")
    if row_count is not None and all_four_row_ok_count != row_count:
        failures.append("previous_payloadless_all_four_row_ok_count_mismatch")
    fourth_path = previous.get("payloadless_fourth_field_handoff_evidence_path")
    fourth_sha = previous.get("payloadless_fourth_field_handoff_evidence_sha256")
    all_four_fourth_path = previous.get(
        "payloadless_all_four_field_consumer_fourth_field_path_label"
    )
    all_four_fourth_sha = previous.get(
        "payloadless_all_four_field_consumer_fourth_field_sha256"
    )
    if fourth_path != all_four_fourth_path:
        failures.append("previous_payloadless_fourth_path_all_four_mismatch")
    if fourth_sha != all_four_fourth_sha:
        failures.append("previous_payloadless_fourth_sha_all_four_mismatch")
    failures.extend(
        _check_bound_evidence_file(
            prefix="previous_payloadless_fourth_field_handoff_evidence",
            payload=previous,
            path_key="payloadless_fourth_field_handoff_evidence_path",
            sha_key="payloadless_fourth_field_handoff_evidence_sha256",
        )
    )
    failures.extend(_required_false_failures("previous", previous))

    underlying_sha_value = previous.get("third_field_underlying_sha256")
    input_paths: list[Path] = []
    underlying_path, path_failures = _resolve_artifact_reference(
        previous.get("third_field_underlying_json"),
        roots=[REPO_ROOT, previous_path.parent],
        label="previous_third_field_underlying_json",
    )
    if path_failures:
        failures.extend(path_failures)
    elif not _is_sha256_hex(underlying_sha_value):
        failures.append("previous_third_field_underlying_sha256_invalid")
    else:
        assert underlying_path is not None
        try:
            actual_sha = _sha256(underlying_path)
            runner = _load_json(underlying_path)
        except Exception as exc:
            failures.append(
                f"previous_third_field_underlying_load_failed:"
                f"{exc.__class__.__name__}:{exc}"
            )
        else:
            if actual_sha != underlying_sha_value:
                failures.append("previous_third_field_underlying_sha256_mismatch")
            input_paths, input_failures = _input_paths_from_runner(
                runner,
                runner_path=underlying_path,
                prefix="previous_runner",
            )
            failures.extend(input_failures)
            failures.extend(
                _check_raw_runner(
                    runner,
                    field=PREVIOUS_FIELD,
                    expected_source_count=source_count,
                    expected_row_count=row_count,
                    expected_hash=previous.get("third_field_handoff_canary_runner_hash"),
                    min_source_count=min_source_count,
                    min_row_count=min_row_count,
                    prefix="previous_runner",
                )
            )
    return input_paths, payloadless, failures


def _build_native_args(
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
        str(args.fourth_field),
        "--require-future-wna16-single-field-handoff-canary",
        "--device",
        str(args.device),
        "--offload-arch",
        str(args.offload_arch),
        "--merged-output-json",
        str(canary_dir / "fourth_field_merged_input.json"),
        "--stub-output-json",
        str(canary_dir / "fourth_field_typed_consumer_stub.json"),
        "--output-json",
        str(canary_dir / "fourth_field_native_canary_runner.json"),
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


def _run_fourth_field_native(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> tuple[dict[str, Any], float]:
    native_args = _build_native_args(args, input_paths=input_paths)
    start_ns = time.perf_counter_ns()
    report = canary_runner.run_canary(native_args)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def _check_fourth_report(
    fourth: dict[str, Any],
    *,
    previous: dict[str, Any],
    payloadless: dict[str, Any] | None,
    fourth_field: str,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures = _check_raw_runner(
        fourth,
        field=fourth_field,
        expected_source_count=_int_metric(previous, "source_count"),
        expected_row_count=_int_metric(previous, "row_count"),
        expected_hash=None,
        min_source_count=min_source_count,
        min_row_count=min_row_count,
        prefix="fourth",
    )
    payloadless_hashes = payloadless.get("field_read_hashes") if payloadless else None
    payloadless_counts = (
        payloadless.get("field_read_row_ok_counts") if payloadless else None
    )
    if not isinstance(payloadless_hashes, dict):
        failures.append("fourth_payloadless_field_read_hashes_missing")
    elif not _is_hex_u64(payloadless_hashes.get(fourth_field)):
        failures.append("fourth_payloadless_selected_field_hash_invalid")
    if not isinstance(payloadless_counts, dict):
        failures.append("fourth_payloadless_field_read_row_ok_counts_missing")
    elif payloadless_counts.get(fourth_field) != previous.get("row_count"):
        failures.append("fourth_payloadless_selected_field_row_ok_count_mismatch")
    return failures


def _check_fourth_underlying_json(
    underlying_json: Path,
    fourth: dict[str, Any] | None,
) -> tuple[str | None, list[str]]:
    failures: list[str] = []
    if fourth is None:
        return None, failures
    if not underlying_json.exists():
        return None, ["fourth_field_underlying_json_missing"]
    try:
        underlying_sha256 = _sha256(underlying_json)
        underlying = _load_json(underlying_json)
    except Exception as exc:
        return None, [
            f"fourth_field_underlying_json_load_failed:{exc.__class__.__name__}:{exc}"
        ]
    checked_keys = (
        "passed",
        "source",
        "mirror_field",
        "input_jsons",
        "no_payload",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "current_wna16_arg_compatible",
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
        "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation",
        "future_wna16_single_field_handoff_canary_explicit_typed_abi_slot",
        "future_wna16_single_field_handoff_canary_reuses_current_wna16_arg_slot",
        "future_wna16_kernel_side_consumer_execution_payload_bytes",
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed",
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed",
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel",
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args",
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible",
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation",
    )
    for key in checked_keys:
        if underlying.get(key) != fourth.get(key):
            failures.append(
                f"fourth_field_underlying_{key}_report_mismatch:"
                f"{underlying.get(key)!r}!={fourth.get(key)!r}"
            )
    failures.extend(_native_top_level_safety_failures("fourth_field_underlying", underlying))
    failures.extend(_native_safety_failures("fourth_field_underlying", underlying))
    return underlying_sha256, failures


def run_fourth_field_handoff_canary(args: argparse.Namespace) -> dict[str, Any]:
    previous_path = _resolve(args.previous_field_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    previous: dict[str, Any] = {}
    try:
        previous = _load_json(previous_path)
    except Exception as exc:
        failures.append(
            f"previous_field_json_load_failed:{exc.__class__.__name__}:{exc}"
        )
    previous_sha256: str | None = None
    if previous_path.exists():
        try:
            previous_sha256 = _sha256(previous_path)
        except Exception as exc:
            failures.append(
                f"previous_field_json_sha256_failed:{exc.__class__.__name__}:{exc}"
            )
    if args.fourth_field in {FIRST_FIELD, SECOND_FIELD, PREVIOUS_FIELD}:
        failures.append("fourth_field_must_differ_from_previous_fields")
    if args.fourth_field != DEFAULT_FOURTH_FIELD:
        failures.append("fourth_field_must_be_descriptor_ptr")
    input_paths: list[Path] = []
    payloadless: dict[str, Any] | None = None
    if previous:
        input_paths, payloadless, previous_failures = _check_previous_gate(
            previous,
            previous_path=previous_path,
            fourth_field=args.fourth_field,
            min_source_count=args.min_source_count,
            min_row_count=args.min_row_count,
        )
        failures.extend(previous_failures)
    if not args.run_native_canary:
        failures.append("run_native_canary_must_remain_enabled_for_lab_gate")
    if not args.require_native_canary:
        failures.append("require_native_canary_must_remain_enabled_for_lab_gate")
    previous_gate_ready = bool(previous) and not failures
    fourth_report: dict[str, Any] | None = None
    fourth_outer_wall_ms: float | None = None
    if args.run_native_canary and previous_gate_ready:
        try:
            fourth_report, fourth_outer_wall_ms = _run_fourth_field_native(
                args,
                input_paths=input_paths,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            failures.append(
                f"fourth_field_handoff_canary_exception:"
                f"{exc.__class__.__name__}:{exc}"
            )
        if fourth_report is not None:
            failures.extend(
                _check_fourth_report(
                    fourth_report,
                    previous=previous,
                    payloadless=payloadless,
                    fourth_field=args.fourth_field,
                    min_source_count=args.min_source_count,
                    min_row_count=args.min_row_count,
                )
            )
    elif args.run_native_canary:
        failures.append("fourth_field_canary_skipped_due_to_previous_gate_failure")
    if args.require_native_canary and fourth_report is None:
        failures.append("fourth_field_handoff_canary_required_but_not_executed")
    passed = not failures
    canary_dir = _resolve(args.canary_output_dir)
    underlying_json = canary_dir / "fourth_field_native_canary_runner.json"
    underlying_sha256, underlying_failures = _check_fourth_underlying_json(
        underlying_json,
        fourth_report,
    )
    if underlying_failures:
        failures.extend(underlying_failures)
        passed = False
    payloadless_hashes = payloadless.get("field_read_hashes") if payloadless else None
    payloadless_counts = (
        payloadless.get("field_read_row_ok_counts") if payloadless else None
    )
    fourth_field_payloadless_hash = (
        payloadless_hashes.get(args.fourth_field)
        if isinstance(payloadless_hashes, dict)
        else None
    )
    fourth_field_payloadless_row_ok = (
        payloadless_counts.get(args.fourth_field)
        if isinstance(payloadless_counts, dict)
        else None
    )
    fourth_source_count = (
        fourth_report.get("selected_source_count")
        if fourth_report
        else previous.get("source_count")
    )
    fourth_row_count = (
        fourth_report.get("merged_row_count") if fourth_report else previous.get("row_count")
    )
    fourth_row_ok_count = (
        fourth_report.get("future_wna16_single_field_handoff_canary_row_ok_count")
        if fourth_report
        else None
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": (
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
        ),
        "fourth_field_handoff_canary_name": CANARY_NAME,
        "fourth_field_handoff_canary_mode": CANARY_MODE,
        "fourth_field_handoff_canary_source": CANARY_SOURCE,
        "passed": passed,
        "failures": failures,
        "previous_field_json": str(previous_path),
        "previous_field_sha256": previous_sha256,
        "previous_field_gate_ready": previous_gate_ready,
        "previous_field_input_json_count": len(input_paths),
        "first_field_name": FIRST_FIELD,
        "second_field_name": SECOND_FIELD,
        "third_field_name": PREVIOUS_FIELD,
        "third_field_read_hash": previous.get("third_field_handoff_field_read_hash"),
        "third_field_native_hash": previous.get("third_field_handoff_canary_runner_hash"),
        "fourth_field_name": args.fourth_field,
        "fourth_field_kind": FIELD_KINDS.get(str(args.fourth_field)),
        "fourth_field_mask": (
            1 << (FIELD_KINDS[str(args.fourth_field)] - 1)
            if args.fourth_field in FIELD_KINDS
            else None
        ),
        "fourth_field_underlying_json": str(underlying_json),
        "fourth_field_underlying_sha256": underlying_sha256,
        "payloadless_execution_json": previous.get("payloadless_execution_json"),
        "payloadless_execution_sha256": previous.get("payloadless_execution_sha256"),
        "payloadless_fourth_field_handoff_evidence_path": previous.get(
            "payloadless_fourth_field_handoff_evidence_path"
        ),
        "payloadless_fourth_field_handoff_evidence_sha256": previous.get(
            "payloadless_fourth_field_handoff_evidence_sha256"
        ),
        "payloadless_all_four_field_consumer_ready": previous.get(
            "payloadless_all_four_field_consumer_ready"
        ),
        "payloadless_all_four_field_consumer_fields_read": previous.get(
            "payloadless_all_four_field_consumer_fields_read"
        ),
        "payloadless_all_four_field_consumer_hashes_valid": previous.get(
            "payloadless_all_four_field_consumer_hashes_valid"
        ),
        "payloadless_all_four_field_consumer_source_count": previous.get(
            "payloadless_all_four_field_consumer_source_count"
        ),
        "payloadless_all_four_field_consumer_row_count": previous.get(
            "payloadless_all_four_field_consumer_row_count"
        ),
        "payloadless_all_four_field_consumer_row_ok_count": previous.get(
            "payloadless_all_four_field_consumer_row_ok_count"
        ),
        "payloadless_all_four_field_consumer_fourth_field_path_label": previous.get(
            "payloadless_all_four_field_consumer_fourth_field_path_label"
        ),
        "payloadless_all_four_field_consumer_fourth_field_sha256": previous.get(
            "payloadless_all_four_field_consumer_fourth_field_sha256"
        ),
        "source_count": fourth_source_count,
        "row_count": fourth_row_count,
        "row_ok_count": fourth_row_ok_count,
        "fourth_field_handoff_field_read_row_ok_count": fourth_field_payloadless_row_ok,
        "fourth_field_handoff_field_read_hash": fourth_field_payloadless_hash,
        "fourth_field_handoff_canary_runner_hash": (
            fourth_report.get("future_wna16_single_field_handoff_canary_hash_accumulator")
            if fourth_report
            else None
        ),
        "fourth_field_handoff_canary_runner_row_count": (
            fourth_report.get("future_wna16_single_field_handoff_canary_row_count")
            if fourth_report
            else None
        ),
        "fourth_field_handoff_canary_runner_row_ok_count": fourth_row_ok_count,
        "fourth_field_handoff_canary_native_requested": bool(args.run_native_canary),
        "fourth_field_handoff_canary_native_executed": fourth_report is not None,
        "fourth_field_handoff_canary_native_passed": (
            fourth_report.get("passed") if fourth_report else None
        ),
        "fourth_field_handoff_canary_outer_wall_ms": fourth_outer_wall_ms,
        "fourth_field_handoff_live_enabled": False,
        "fourth_field_handoff_block_reason": "fourth_field_handoff_live_disabled",
        "fourth_field_handoff_scope": (
            "independent_future_wna16_typed_slot_fourth_field_handoff_canary"
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
            "future WNA16 typed-slot fourth-field handoff canary failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the future WNA16 typed-slot fourth-field handoff canary. "
            "This requires the packed-weight third-field gate and keeps live "
            "handoff/current WNA16 args disabled."
        )
    )
    parser.add_argument("--previous-field-json", default=str(DEFAULT_PREVIOUS_FIELD_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--canary-output-dir", default=str(DEFAULT_CANARY_OUTPUT_DIR))
    parser.add_argument(
        "--fourth-field",
        choices=sorted(HANDLE_FIELDS),
        default=DEFAULT_FOURTH_FIELD,
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
    report = run_fourth_field_handoff_canary(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
