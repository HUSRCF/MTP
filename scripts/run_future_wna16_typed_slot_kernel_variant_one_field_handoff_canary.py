#!/usr/bin/env python3
"""Run the future WNA16 typed-slot one-field handoff canary gate.

This stage narrows the already-passed payloadless typed-slot execution gate to a
single future-kernel field mirror.  By default the selected field is the safe
metadata/scale handle mirror.  The canary still uses the independent future
typed-slot ABI path: live handoff is disabled, current WNA16 fused-MoE kernel
arguments are not reused or passed, and no payload is dereferenced.
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

from scripts import run_premap_online_merged_native_arg_slot_canary as canary_runner


DEFAULT_PAYLOADLESS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_payloadless_execution_four_field_v1_native_run.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary_v1.json"
)
DEFAULT_CANARY_OUTPUT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary"
)

CANARY_NAME = "premap_future_wna16_typed_slot_one_field_handoff_canary_v1"
CANARY_MODE = "readonly_future_wna16_typed_slot_one_field_handoff_canary"
CANARY_SOURCE = "premap_future_wna16_typed_slot_payloadless_execution_v1"
NEXT_RUNTIME_STAGE = (
    "implement_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary"
)
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
EXPECTED_PAYLOADLESS_FLAGS: dict[str, Any] = {
    "artifact_kind": "future_wna16_typed_slot_kernel_variant_payloadless_execution",
    "payloadless_execution_name": (
        "premap_future_wna16_typed_slot_payloadless_execution_v1"
    ),
    "payloadless_execution_mode": (
        "independent_future_wna16_typed_slot_payloadless_execution"
    ),
    "payloadless_execution_source": (
        "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1"
    ),
    "passed": True,
    "payloadless_execution_ready": True,
    "payloadless_execution_gate_ready": True,
    "payloadless_execution_native_requested": True,
    "payloadless_execution_native_executed": True,
    "payloadless_execution_native_passed": True,
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
    "fourth_field_handoff_ready": True,
    "next_runtime_stage": (
        "implement_future_wna16_typed_slot_kernel_variant_one_field_handoff_canary"
    ),
}


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
    if not isinstance(value, str) or not (1 <= len(value) <= 16):
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 < parsed <= 0xFFFFFFFFFFFFFFFF


def _is_hex_u64_fixed(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 16 and _is_hex_u64(value)


def _positive_ms(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0


def _is_false_like(value: Any) -> bool:
    return value is None or value is False or value == 0


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_payloadless(
    payloadless: dict[str, Any],
    *,
    field: str,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_PAYLOADLESS_FLAGS.items():
        if payloadless.get(key) != expected:
            failures.append(
                f"payloadless_{key}_mismatch:{payloadless.get(key)!r}!={expected!r}"
            )
    source_count = _int_metric(payloadless, "source_count")
    if source_count is None or source_count < min_source_count:
        failures.append("payloadless_source_count_invalid")
    row_count = _int_metric(payloadless, "row_count")
    row_ok_count = _int_metric(payloadless, "row_ok_count")
    if row_count is None or row_count < min_row_count:
        failures.append("payloadless_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("payloadless_row_ok_count_mismatch")
    if payloadless.get("field_names") != list(HANDLE_FIELDS):
        failures.append("payloadless_field_names_mismatch")
    row_ok_counts = payloadless.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("payloadless_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = payloadless.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("payloadless_field_read_hashes_missing")
        field_hashes = {}
    expected_fields = set(HANDLE_FIELDS)
    if set(row_ok_counts) != expected_fields:
        failures.append("payloadless_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != expected_fields:
        failures.append("payloadless_field_read_hashes_keys_mismatch")
    for handle_field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(handle_field) != row_count:
            failures.append(f"payloadless_{handle_field}_read_row_ok_count_mismatch")
        if not _is_hex_u64_fixed(field_hashes.get(handle_field)):
            failures.append(f"payloadless_{handle_field}_read_hash_invalid")
    fourth_source_count = _int_metric(payloadless, "fourth_field_handoff_source_count")
    if fourth_source_count is None:
        failures.append("payloadless_fourth_field_handoff_source_count_invalid")
    elif source_count is not None and fourth_source_count != source_count:
        failures.append("payloadless_fourth_field_handoff_source_count_mismatch")
    fourth_row_count = _int_metric(payloadless, "fourth_field_handoff_row_count")
    if fourth_row_count is None:
        failures.append("payloadless_fourth_field_handoff_row_count_invalid")
    elif row_count is not None and fourth_row_count != row_count:
        failures.append("payloadless_fourth_field_handoff_row_count_mismatch")
    fourth_row_ok_count = _int_metric(payloadless, "fourth_field_handoff_row_ok_count")
    if fourth_row_ok_count is None:
        failures.append("payloadless_fourth_field_handoff_row_ok_count_invalid")
    elif fourth_row_count is not None and fourth_row_ok_count != fourth_row_count:
        failures.append("payloadless_fourth_field_handoff_row_ok_count_mismatch")
    descriptor_hash = field_hashes.get("descriptor_ptr")
    if payloadless.get("fourth_field_handoff_field_read_hash") != descriptor_hash:
        failures.append("payloadless_fourth_field_handoff_descriptor_hash_mismatch")
    if not _is_hex_u64_fixed(payloadless.get("fourth_field_handoff_runner_hash")):
        failures.append("payloadless_fourth_field_handoff_runner_hash_invalid")
    if field not in HANDLE_FIELDS:
        failures.append(f"unsupported_one_field_handoff_field:{field}")
    elif row_count is not None and row_ok_counts.get(field) != row_count:
        failures.append(f"payloadless_{field}_selected_field_read_incomplete")
    if not _positive_ms(payloadless.get("payloadless_execution_native_host_wall_ms")):
        failures.append("payloadless_execution_native_host_wall_ms_invalid")
    return failures


def _check_canary_report(
    canary: dict[str, Any],
    *,
    field: str,
    payloadless: dict[str, Any],
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    field_kind = FIELD_KINDS[field]
    expected_scalars: dict[str, Any] = {
        "passed": True,
        "require_future_wna16_single_field_handoff_canary": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_wna16_adjacent_typed_slot": True,
        "future_wna16_single_field_handoff_canary_checked": True,
        "future_wna16_single_field_handoff_canary_name": (
            "premap_future_wna16_single_field_handoff_canary_v1"
        ),
        "future_wna16_single_field_handoff_canary_abi_name": (
            "premap_future_wna16_single_field_handoff_canary_v1"
        ),
        "future_wna16_single_field_handoff_canary_mode": (
            "readonly_future_wna16_single_field_handoff_canary"
        ),
        "future_wna16_single_field_handoff_canary_source": (
            "premap_future_wna16_kernel_side_consumer_execution_v1"
        ),
        "future_wna16_single_field_handoff_canary_field_name": field,
        "future_wna16_single_field_handoff_canary_field_kind": field_kind,
        "future_wna16_single_field_handoff_canary_field_mask": 1 << (field_kind - 1),
        "future_wna16_single_field_handoff_canary_error_count": 0,
        "future_wna16_single_field_handoff_canary_payload_bytes": 0,
        "future_wna16_single_field_handoff_canary_live_enabled": False,
        "future_wna16_single_field_handoff_canary_passed_to_kernel": False,
        "future_wna16_single_field_handoff_canary_changes_kernel_launch_args": False,
        "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible": False,
        "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation": (
            False
        ),
        "future_wna16_single_field_handoff_canary_explicit_typed_abi_slot": True,
        "future_wna16_single_field_handoff_canary_reuses_current_wna16_arg_slot": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "future_wna16_kernel_side_consumer_execution_payload_bytes": 0,
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed": False,
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel": False,
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_explicit_typed_abi_slot": True,
        "future_wna16_kernel_side_consumer_execution_reuses_current_wna16_arg_slot": (
            False
        ),
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read": True,
        "future_wna16_kernel_accept_typed_slot_payload_bytes": 0,
        "future_wna16_kernel_accept_typed_slot_passed_to_kernel": False,
        "future_wna16_kernel_accept_typed_slot_changes_kernel_launch_args": False,
        "future_wna16_kernel_accept_typed_slot_current_wna16_arg_compatible": False,
        "future_wna16_kernel_accept_typed_slot_requires_wna16_arg_reinterpretation": (
            False
        ),
        "future_wna16_kernel_accept_typed_slot_explicit_typed_abi_slot": True,
        "future_wna16_kernel_accept_typed_slot_reuses_current_wna16_arg_slot": False,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
    }
    for key, expected in expected_scalars.items():
        if canary.get(key) != expected:
            failures.append(f"canary_{key}_mismatch:{canary.get(key)!r}!={expected!r}")
    unsafe_true_keys = (
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
    for key in unsafe_true_keys:
        if not _is_false_like(canary.get(key)):
            failures.append(f"canary_{key}_unsafe_nonzero:{canary.get(key)!r}")
    canary_payload_bytes = canary.get("payload_bytes")
    if not _is_false_like(canary_payload_bytes):
        failures.append(f"canary_payload_bytes_nonzero:{canary_payload_bytes!r}")
    selected_source_count = _int_metric(canary, "selected_source_count")
    if selected_source_count is None or selected_source_count < min_source_count:
        failures.append("canary_selected_source_count_invalid")
    merged_row_count = _int_metric(canary, "merged_row_count")
    if merged_row_count is None or merged_row_count < min_row_count:
        failures.append("canary_merged_row_count_invalid")
    dispatch_rows = _int_metric(canary, "dispatch_active_rows")
    canary_rows = _int_metric(canary, "future_wna16_single_field_handoff_canary_row_count")
    canary_ok_rows = _int_metric(
        canary, "future_wna16_single_field_handoff_canary_row_ok_count"
    )
    if dispatch_rows is None or dispatch_rows < min_row_count:
        failures.append("canary_dispatch_active_rows_invalid")
    if canary_rows != dispatch_rows:
        failures.append("canary_single_field_row_count_mismatch")
    if canary_ok_rows != dispatch_rows:
        failures.append("canary_single_field_row_ok_count_mismatch")
    if selected_source_count != payloadless.get("source_count"):
        failures.append("canary_source_count_payloadless_mismatch")
    if merged_row_count != payloadless.get("row_count"):
        failures.append("canary_row_count_payloadless_mismatch")
    if dispatch_rows != payloadless.get("row_count"):
        failures.append("canary_dispatch_rows_payloadless_mismatch")
    for key in (
        "future_wna16_single_field_handoff_canary_hash_accumulator",
        "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator",
        "future_wna16_kernel_accept_typed_slot_field_read_hash_accumulator",
    ):
        if not _is_hex_u64(canary.get(key)):
            failures.append(f"canary_{key}_invalid")
    return failures


def _payloadless_timing_stub(payloadless: dict[str, Any]) -> dict[str, Any]:
    timing_stub_value = payloadless.get("payloadless_execution_timing_stub_json")
    if not isinstance(timing_stub_value, str) or not timing_stub_value:
        raise ValueError("payloadless artifact does not include timing stub provenance")
    timing_stub_path = _resolve(timing_stub_value)
    expected_sha = payloadless.get("payloadless_execution_timing_stub_sha256")
    if not _is_sha256_hex(expected_sha):
        raise ValueError("payloadless artifact does not include timing stub sha256")
    actual_sha = _sha256(timing_stub_path)
    if actual_sha != expected_sha:
        raise ValueError(
            "payloadless timing stub sha256 mismatch: "
            f"{actual_sha}!={expected_sha}"
        )
    timing_stub = _load_json(timing_stub_path)
    for key in (
        "source_count",
        "row_count",
        "row_ok_count",
        "field_names",
        "field_read_row_ok_counts",
        "field_read_hashes",
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
        "fourth_field_handoff_ready",
        "fourth_field_handoff_source_count",
        "fourth_field_handoff_row_count",
        "fourth_field_handoff_row_ok_count",
        "fourth_field_handoff_field_read_hash",
        "fourth_field_handoff_runner_hash",
    ):
        if timing_stub.get(key) != payloadless.get(key):
            raise ValueError(f"payloadless timing stub {key} mismatch")
    return timing_stub


def _input_jsons_from_payloadless(payloadless: dict[str, Any]) -> list[Path]:
    timing_stub = _payloadless_timing_stub(payloadless)
    runner_json_value = timing_stub.get("runner_json")
    if not isinstance(runner_json_value, str) or not runner_json_value:
        raise ValueError("payloadless timing stub does not include runner_json")
    payloadless_runner_json = payloadless.get("payloadless_execution_runner_json")
    if not isinstance(payloadless_runner_json, str) or not payloadless_runner_json:
        raise ValueError("payloadless artifact does not include runner_json")
    if _resolve(payloadless_runner_json) != _resolve(runner_json_value):
        raise ValueError("payloadless runner_json mismatches timing stub runner_json")
    runner_path = _resolve(runner_json_value)
    expected_runner_sha = timing_stub.get("runner_sha256")
    if not _is_sha256_hex(expected_runner_sha):
        raise ValueError("payloadless timing stub does not include runner sha256")
    payloadless_runner_sha = payloadless.get("payloadless_execution_runner_sha256")
    if not _is_sha256_hex(payloadless_runner_sha):
        raise ValueError("payloadless artifact does not include runner sha256")
    if payloadless_runner_sha != expected_runner_sha:
        raise ValueError("payloadless runner sha256 mismatches timing stub runner sha256")
    actual_runner_sha = _sha256(runner_path)
    if actual_runner_sha != expected_runner_sha:
        raise ValueError(
            "payloadless timing stub runner sha256 mismatch: "
            f"{actual_runner_sha}!={expected_runner_sha}"
        )
    runner = _load_json(runner_path)
    input_values = runner.get("online_prelaunch_input_jsons")
    source_key = "online_prelaunch_input_jsons"
    if input_values is None:
        input_values = runner.get("input_jsons")
        source_key = "input_jsons"
    if not isinstance(input_values, list) or not input_values:
        raise ValueError(
            f"payloadless runner provenance does not include input JSON list: "
            f"{runner_path}"
        )
    paths: list[Path] = []
    for index, value in enumerate(input_values):
        if not isinstance(value, str) or not value:
            raise ValueError(f"invalid {source_key}[{index}] in {runner_path}")
        paths.append(_resolve(value))
    return paths


def _build_canary_args(
    args: argparse.Namespace,
    *,
    payloadless: dict[str, Any],
) -> argparse.Namespace:
    canary_dir = _resolve(args.canary_output_dir)
    input_jsons = _input_jsons_from_payloadless(payloadless)
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
        str(args.field),
        "--require-future-wna16-single-field-handoff-canary",
        "--device",
        str(args.device),
        "--offload-arch",
        str(args.offload_arch),
        "--merged-output-json",
        str(canary_dir / "one_field_handoff_merged_input.json"),
        "--stub-output-json",
        str(canary_dir / "one_field_handoff_typed_consumer_stub.json"),
        "--output-json",
        str(canary_dir / "one_field_handoff_canary_runner.json"),
    ]
    for input_json in input_jsons:
        argv.extend(["--input-json", str(input_json)])
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.tail_window_size is not None:
        argv.extend(["--tail-window-size", str(args.tail_window_size)])
    if args.force_build:
        argv.append("--force-build")
    if args.dry_run_canary:
        argv.append("--dry-run")
    parsed = canary_runner.build_parser().parse_args(argv)
    # The lower-level runner has a historical default runner_json.  This stage
    # must consume only the payloadless-gate provenance expanded above.
    parsed.runner_json = None
    return parsed


def _run_native_canary(
    args: argparse.Namespace,
    *,
    payloadless: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    canary_args = _build_canary_args(args, payloadless=payloadless)
    start_ns = time.perf_counter_ns()
    report = canary_runner.run_canary(canary_args)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def _observed_bool(
    payloadless: dict[str, Any],
    canary: dict[str, Any] | None,
    key: str,
) -> bool:
    return (not _is_false_like(payloadless.get(key))) or (
        canary is not None and not _is_false_like(canary.get(key))
    )


def _observed_payload_bytes(
    payloadless: dict[str, Any],
    canary: dict[str, Any] | None,
) -> Any:
    for payload in (canary or {}, payloadless):
        value = payload.get("payload_bytes")
        if not _is_false_like(value):
            return value
    return 0


def run_one_field_handoff_canary(args: argparse.Namespace) -> dict[str, Any]:
    payloadless_path = _resolve(args.payloadless_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    payloadless: dict[str, Any] = {}
    try:
        payloadless = _load_json(payloadless_path)
    except Exception as exc:
        failures.append(
            f"payloadless_json_load_failed:{exc.__class__.__name__}:{exc}"
        )
    payloadless_sha256: str | None = None
    if payloadless_path.exists():
        try:
            payloadless_sha256 = _sha256(payloadless_path)
        except Exception as exc:
            failures.append(
                f"payloadless_json_sha256_failed:{exc.__class__.__name__}:{exc}"
            )
    if payloadless:
        failures.extend(
            _check_payloadless(
                payloadless,
                field=args.field,
                min_source_count=args.min_source_count,
                min_row_count=args.min_row_count,
            )
        )
    if args.runner_json is not None:
        failures.append("runner_json_override_not_allowed_for_lab_gate")
    if args.input_json:
        failures.append("input_json_override_not_allowed_for_lab_gate")
    if not args.run_native_canary:
        failures.append("run_native_canary_must_remain_enabled_for_lab_gate")
    if not args.require_native_canary:
        failures.append("require_native_canary_must_remain_enabled_for_lab_gate")
    if args.dry_run_canary:
        failures.append("dry_run_canary_not_allowed_for_lab_gate")
    payloadless_gate_ready = bool(payloadless) and not failures
    canary_report: dict[str, Any] | None = None
    canary_outer_wall_ms: float | None = None
    if args.run_native_canary and payloadless_gate_ready:
        try:
            canary_report, canary_outer_wall_ms = _run_native_canary(
                args,
                payloadless=payloadless,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests
            failures.append(
                f"one_field_handoff_canary_exception:{exc.__class__.__name__}:{exc}"
            )
        if canary_report is not None:
            failures.extend(
                _check_canary_report(
                    canary_report,
                    field=args.field,
                    payloadless=payloadless,
                    min_source_count=args.min_source_count,
                    min_row_count=args.min_row_count,
                )
            )
    elif args.run_native_canary:
        failures.append("one_field_handoff_canary_skipped_due_to_payloadless_failure")
    if args.require_native_canary and canary_report is None:
        failures.append("one_field_handoff_canary_required_but_not_executed")

    passed = not failures
    row_ok_counts = payloadless.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        row_ok_counts = {}
    field_hashes = payloadless.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        field_hashes = {}
    canary_dir = _resolve(args.canary_output_dir)
    canary_runner_json = canary_dir / "one_field_handoff_canary_runner.json"
    canary_runner_sha256: str | None = None
    if canary_runner_json.exists():
        try:
            canary_runner_sha256 = _sha256(canary_runner_json)
        except Exception as exc:
            failures.append(
                f"canary_runner_json_sha256_failed:{exc.__class__.__name__}:{exc}"
            )
            passed = False
    field_kind = FIELD_KINDS.get(str(args.field))
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary",
        "one_field_handoff_canary_name": CANARY_NAME,
        "one_field_handoff_canary_mode": CANARY_MODE,
        "one_field_handoff_canary_source": CANARY_SOURCE,
        "passed": passed,
        "failures": failures,
        "payloadless_execution_json": str(payloadless_path),
        "payloadless_execution_sha256": payloadless_sha256,
        "payloadless_execution_gate_ready": payloadless_gate_ready,
        "canary_runner_json": str(canary_runner_json),
        "canary_runner_sha256": canary_runner_sha256,
        "source_count": (
            canary_report.get("selected_source_count")
            if canary_report
            else payloadless.get("source_count")
        ),
        "row_count": (
            canary_report.get("dispatch_active_rows")
            if canary_report
            else payloadless.get("row_count")
        ),
        "row_ok_count": (
            canary_report.get("future_wna16_single_field_handoff_canary_row_ok_count")
            if canary_report
            else payloadless.get("row_ok_count")
        ),
        "merged_row_count": (
            canary_report.get("merged_row_count")
            if canary_report
            else payloadless.get("row_count")
        ),
        "payloadless_source_count": payloadless.get("source_count"),
        "payloadless_row_count": payloadless.get("row_count"),
        "payloadless_field_read_row_ok_counts": row_ok_counts,
        "payloadless_field_read_hashes": field_hashes,
        "field_names": list(HANDLE_FIELDS),
        "one_field_handoff_field_name": args.field,
        "one_field_handoff_field_kind": field_kind,
        "one_field_handoff_field_mask": (
            1 << (int(field_kind) - 1) if field_kind is not None else None
        ),
        "one_field_handoff_field_read_row_ok_count": row_ok_counts.get(args.field),
        "one_field_handoff_field_read_hash": field_hashes.get(args.field),
        "one_field_handoff_field_hash_binding_mode": (
            "same_field_dual_hash_evidence_with_payloadless_timing_stub_sha_"
            "runner_sha_and_full_row_coverage"
        ),
        "one_field_handoff_native_hash_algorithm": (
            "future_wna16_single_field_handoff_hash_accumulator"
        ),
        "one_field_handoff_canary_native_requested": bool(args.run_native_canary),
        "one_field_handoff_canary_native_executed": canary_report is not None,
        "one_field_handoff_canary_native_passed": (
            canary_report.get("passed") if canary_report else None
        ),
        "one_field_handoff_canary_outer_wall_ms": canary_outer_wall_ms,
        "one_field_handoff_canary_runner_row_count": (
            canary_report.get("future_wna16_single_field_handoff_canary_row_count")
            if canary_report
            else None
        ),
        "one_field_handoff_canary_runner_row_ok_count": (
            canary_report.get("future_wna16_single_field_handoff_canary_row_ok_count")
            if canary_report
            else None
        ),
        "one_field_handoff_canary_runner_hash": (
            canary_report.get("future_wna16_single_field_handoff_canary_hash_accumulator")
            if canary_report
            else None
        ),
        "one_field_handoff_canary_ready": passed,
        "one_field_handoff_live_enabled": False,
        "one_field_handoff_block_reason": "one_field_handoff_live_disabled",
        "one_field_handoff_scope": (
            "independent_future_wna16_typed_slot_single_field_handoff_canary"
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
        "measures_vllm_latency": _observed_bool(
            payloadless, canary_report, "measures_vllm_latency"
        ),
        "measures_tpot": _observed_bool(payloadless, canary_report, "measures_tpot"),
        "wna16_benchmark_ready": _observed_bool(
            payloadless, canary_report, "wna16_benchmark_ready"
        ),
        "uses_current_wna16_args": _observed_bool(
            payloadless, canary_report, "uses_current_wna16_args"
        ),
        "passes_current_wna16_args": _observed_bool(
            payloadless, canary_report, "passes_current_wna16_args"
        ),
        "current_wna16_arg_compatible": _observed_bool(
            payloadless, canary_report, "current_wna16_arg_compatible"
        ),
        "requires_wna16_arg_reinterpretation": _observed_bool(
            payloadless, canary_report, "requires_wna16_arg_reinterpretation"
        ),
        "payload_bytes": _observed_payload_bytes(payloadless, canary_report),
        "payload_deref_allowed": _observed_bool(
            payloadless, canary_report, "payload_deref_allowed"
        ),
        "kernel_arg_pass_allowed": _observed_bool(
            payloadless, canary_report, "kernel_arg_pass_allowed"
        ),
        "passed_to_kernel": _observed_bool(
            payloadless, canary_report, "passed_to_kernel"
        ),
        "changes_kernel_launch_args": _observed_bool(
            payloadless, canary_report, "changes_kernel_launch_args"
        ),
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
            "future WNA16 typed-slot one-field handoff canary failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the future WNA16 typed-slot one-field handoff canary. "
            "This keeps live handoff disabled and does not pass current WNA16 "
            "kernel arguments."
        )
    )
    parser.add_argument("--payloadless-json", default=str(DEFAULT_PAYLOADLESS_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--canary-output-dir", default=str(DEFAULT_CANARY_OUTPUT_DIR))
    parser.add_argument(
        "--field",
        choices=sorted(HANDLE_FIELDS),
        default="scale_metadata_handle",
    )
    parser.add_argument("--runner-json", type=Path)
    parser.add_argument("--input-json", type=Path, action="append", default=[])
    parser.add_argument("--max-inputs", type=int, default=128)
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--tail-window-size", type=int)
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--dry-run-canary",
        action="store_true",
        help=(
            "debug only; any artifact produced with this flag fails the lab gate"
        ),
    )
    parser.add_argument(
        "--run-native-canary",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "run the existing native future-WNA16 single-field canary path; "
            "enabled by default for this gate"
        ),
    )
    parser.add_argument(
        "--require-native-canary",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="require native canary execution; enabled by default for this gate",
    )
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_one_field_handoff_canary(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
