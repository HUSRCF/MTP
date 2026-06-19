#!/usr/bin/env python3
"""Run the all-four-field future WNA16 typed-slot consumer gate.

This stage consumes the fourth-field handoff canary artifact and reruns the
independent native typed-slot consumer with both future WNA16 consumer paths
enabled:

* ``future_wna16_kernel_side_consumer_execution``
* ``wna16_side_consumer_variant_execution``

It is still a no-op lab gate.  It does not pass current WNA16 kernel arguments,
does not dereference payload, and does not mutate the real vLLM launch.
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
    run_future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary
    as fourth_gate,
)
from scripts import (  # noqa: E402
    run_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary
    as abi_contract,
)
from scripts import (  # noqa: E402
    run_premap_online_merged_native_arg_slot_canary as native_runner,
)


DEFAULT_FOURTH_FIELD_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_entry_args_ptr_default.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default.json"
)
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default"
)

ARTIFACT_KIND = "future_wna16_typed_slot_kernel_variant_all_four_field_consumer"
GATE_NAME = "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
GATE_MODE = "readonly_future_wna16_typed_slot_all_four_field_consumer"
GATE_SOURCE = "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
NEXT_RUNTIME_STAGE = (
    "implement_future_wna16_typed_slot_kernel_variant_benchmark_harness"
)

HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
REQUIRED_PREFIXES = (
    "future_wna16_kernel_side_consumer_execution",
    "wna16_side_consumer_variant_execution",
)
REQUIRED_FALSE_BOUNDARY_KEYS = (
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
    "requires_wna16_arg_reinterpretation",
)
REQUIRED_PREFIX_FALSE_BOUNDARY_KEYS = REQUIRED_FALSE_BOUNDARY_KEYS + (
    "reuses_current_wna16_arg_slot",
)


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return fourth_gate._sha256(path)


def _input_manifest(paths: list[Path]) -> dict[str, Any]:
    entries = [
        {
            "index": index,
            "path": str(path),
            "sha256": _sha256(path),
        }
        for index, path in enumerate(paths)
    ]
    digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "input_json_count": len(paths),
        "input_manifest_sha256": digest,
        "input_manifest_entries": entries,
    }


def _is_sha256_hex(value: Any) -> bool:
    return fourth_gate._is_sha256_hex(value)


def _is_hex_u64(value: Any) -> bool:
    return fourth_gate._is_hex_u64(value)


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    return fourth_gate._int_metric(payload, key)


def _bool_is(payload: dict[str, Any], key: str, expected: bool) -> bool:
    return payload.get(key) is expected


def _check_fourth_payloadless_evidence(
    fourth: dict[str, Any],
    *,
    fourth_path: Path,
    source_count: int | None,
    row_count: int | None,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    expected_flattened = {
        "payloadless_execution_native_artifact_ready": True,
        "payloadless_execution_lab_preflight_ready": True,
        "payloadless_entry_args_ptr_required": True,
    }
    for key, expected in expected_flattened.items():
        if fourth.get(key) != expected:
            failures.append(f"fourth_{key}_mismatch:{fourth.get(key)!r}!={expected!r}")
    if list(fourth.get("payloadless_entry_args_ptr_sweep_mirror_fields") or []) != list(
        abi_contract.ENTRY_ARGS_PTR_MIRROR_FIELDS
    ):
        failures.append("fourth_payloadless_entry_args_ptr_sweep_mirror_fields_mismatch")
    sweep_rows = _int_metric(fourth, "payloadless_entry_args_ptr_sweep_row_count")
    check_rows = _int_metric(fourth, "payloadless_entry_args_ptr_sweep_check_row_count")
    if sweep_rows is None or sweep_rows < min_row_count:
        failures.append("fourth_payloadless_entry_args_ptr_sweep_row_count_invalid")
    if check_rows is None or check_rows < min_row_count:
        failures.append("fourth_payloadless_entry_args_ptr_sweep_check_row_count_invalid")
    if sweep_rows is not None and check_rows is not None and sweep_rows != check_rows:
        failures.append("fourth_payloadless_entry_args_ptr_sweep_check_row_count_mismatch")

    payloadless_path, path_failures = fourth_gate._resolve_artifact_reference(
        fourth.get("payloadless_execution_json"),
        roots=[REPO_ROOT, fourth_path.parent],
        label="fourth_payloadless_execution_json",
    )
    failures.extend(path_failures)
    payloadless_sha = fourth.get("payloadless_execution_sha256")
    if payloadless_path is None:
        return failures
    if not _is_sha256_hex(payloadless_sha):
        failures.append("fourth_payloadless_execution_sha256_invalid")
        return failures
    if not payloadless_path.exists():
        failures.append(f"fourth_payloadless_execution_json_missing:{payloadless_path}")
        return failures
    actual_sha = _sha256(payloadless_path)
    if actual_sha != payloadless_sha:
        failures.append("fourth_payloadless_execution_sha256_mismatch")
        return failures
    try:
        payloadless = _load_json(payloadless_path)
    except Exception as exc:
        failures.append(
            f"fourth_payloadless_execution_load_failed:{exc.__class__.__name__}:{exc}"
        )
        return failures
    if payloadless.get("passed") is not True:
        failures.append("fourth_payloadless_execution_passed_mismatch")
    if payloadless.get("source_count") != source_count:
        failures.append("fourth_payloadless_source_count_mismatch")
    if payloadless.get("row_count") != row_count:
        failures.append("fourth_payloadless_row_count_mismatch")
    field_hashes = payloadless.get("field_read_hashes")
    field_counts = payloadless.get("field_read_row_ok_counts")
    if not isinstance(field_hashes, dict):
        failures.append("fourth_payloadless_field_read_hashes_missing")
    else:
        for field in HANDLE_FIELDS:
            if not _is_hex_u64(field_hashes.get(field)):
                failures.append(f"fourth_payloadless_{field}_hash_invalid")
        if field_hashes.get("descriptor_ptr") != fourth.get(
            "fourth_field_handoff_field_read_hash"
        ):
            failures.append("fourth_payloadless_descriptor_ptr_hash_mismatch")
    if not isinstance(field_counts, dict):
        failures.append("fourth_payloadless_field_read_row_ok_counts_missing")
    else:
        for field in HANDLE_FIELDS:
            if field_counts.get(field) != row_count:
                failures.append(f"fourth_payloadless_{field}_row_ok_count_mismatch")
        if field_counts.get("descriptor_ptr") != fourth.get(
            "fourth_field_handoff_field_read_row_ok_count"
        ):
            failures.append("fourth_payloadless_descriptor_ptr_row_ok_mismatch")
    flattened_pairs = (
        ("payloadless_entry_args_ptr_required", "entry_args_ptr_required"),
        ("payloadless_entry_args_ptr_sweep_json", "entry_args_ptr_sweep_json"),
        ("payloadless_entry_args_ptr_sweep_sha256", "entry_args_ptr_sweep_sha256"),
        (
            "payloadless_entry_args_ptr_sweep_check_json",
            "entry_args_ptr_sweep_check_json",
        ),
        (
            "payloadless_entry_args_ptr_sweep_check_sha256",
            "entry_args_ptr_sweep_check_sha256",
        ),
        ("payloadless_entry_args_ptr_sweep_row_count", "entry_args_ptr_sweep_row_count"),
        (
            "payloadless_entry_args_ptr_sweep_check_row_count",
            "entry_args_ptr_sweep_check_row_count",
        ),
        (
            "payloadless_entry_args_ptr_sweep_mirror_fields",
            "entry_args_ptr_sweep_mirror_fields",
        ),
    )
    for fourth_key, payloadless_key in flattened_pairs:
        if fourth.get(fourth_key) != payloadless.get(payloadless_key):
            failures.append(
                f"fourth_{fourth_key}_payloadless_mismatch:"
                f"{fourth.get(fourth_key)!r}!={payloadless.get(payloadless_key)!r}"
            )
    failures.extend(
        abi_contract._check_entry_args_ptr_payloadless_artifact(  # noqa: SLF001
            payloadless,
            source_count=source_count,
            row_count=row_count,
            min_row_count=min_row_count,
            prefix="fourth_payloadless_execution",
        )
    )
    return failures


def _check_false_boundary(prefix: str, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in REQUIRED_FALSE_BOUNDARY_KEYS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    if payload.get("payload_bytes") != 0:
        failures.append(f"{prefix}_payload_bytes_not_zero")
    return failures


def _load_fourth_gate(
    path: Path,
    *,
    min_source_count: int,
    min_row_count: int,
) -> tuple[dict[str, Any] | None, list[Path], list[str]]:
    failures: list[str] = []
    try:
        fourth = _load_json(path)
    except Exception as exc:
        return None, [], [
            f"fourth_field_json_load_failed:{exc.__class__.__name__}:{exc}"
        ]
    expected = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary",
        "fourth_field_handoff_canary_name": (
            "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
        ),
        "fourth_field_handoff_canary_mode": (
            "readonly_future_wna16_typed_slot_fourth_field_handoff_canary"
        ),
        "fourth_field_handoff_canary_source": (
            "premap_future_wna16_typed_slot_third_field_handoff_canary_v1"
        ),
        "passed": True,
        "previous_field_gate_ready": True,
        "fourth_field_name": "descriptor_ptr",
        "fourth_field_handoff_live_enabled": False,
        "fourth_field_handoff_block_reason": "fourth_field_handoff_live_disabled",
        "fourth_field_handoff_canary_native_requested": True,
        "fourth_field_handoff_canary_native_executed": True,
        "fourth_field_handoff_canary_native_passed": True,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    for key, value in expected.items():
        if fourth.get(key) != value:
            failures.append(f"fourth_{key}_mismatch:{fourth.get(key)!r}!={value!r}")
    if fourth.get("failures") != []:
        failures.append("fourth_failures_not_empty")
    source_count = _int_metric(fourth, "source_count")
    row_count = _int_metric(fourth, "row_count")
    if source_count is None or source_count < min_source_count:
        failures.append("fourth_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("fourth_row_count_invalid")
    if row_count is not None:
        for key in (
            "row_ok_count",
            "fourth_field_handoff_field_read_row_ok_count",
            "fourth_field_handoff_canary_runner_row_count",
            "fourth_field_handoff_canary_runner_row_ok_count",
        ):
            if fourth.get(key) != row_count:
                failures.append(f"fourth_{key}_row_count_mismatch")
    for key in (
        "fourth_field_handoff_field_read_hash",
        "fourth_field_handoff_canary_runner_hash",
        "third_field_read_hash",
        "third_field_native_hash",
    ):
        if not _is_hex_u64(fourth.get(key)):
            failures.append(f"fourth_{key}_invalid")
    failures.extend(
        _check_fourth_payloadless_evidence(
            fourth,
            fourth_path=path,
            source_count=source_count,
            row_count=row_count,
            min_row_count=min_row_count,
        )
    )

    underlying_path, path_failures = fourth_gate._resolve_artifact_reference(
        fourth.get("fourth_field_underlying_json"),
        roots=[REPO_ROOT, path.parent],
        label="fourth_field_underlying_json",
    )
    failures.extend(path_failures)
    input_paths: list[Path] = []
    if underlying_path is not None:
        sha_value = fourth.get("fourth_field_underlying_sha256")
        if not _is_sha256_hex(sha_value):
            failures.append("fourth_field_underlying_sha256_invalid")
        elif not underlying_path.exists():
            failures.append(f"fourth_field_underlying_json_missing:{underlying_path}")
        else:
            actual_sha = _sha256(underlying_path)
            if actual_sha != sha_value:
                failures.append("fourth_field_underlying_sha256_mismatch")
            try:
                underlying = _load_json(underlying_path)
            except Exception as exc:
                failures.append(
                    f"fourth_field_underlying_load_failed:"
                    f"{exc.__class__.__name__}:{exc}"
                )
            else:
                input_paths, input_failures = fourth_gate._input_paths_from_runner(
                    underlying,
                    runner_path=underlying_path,
                    prefix="fourth_underlying_runner",
                )
                failures.extend(input_failures)
    return fourth, input_paths, failures


def _native_args(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> argparse.Namespace:
    output_dir = _resolve(args.output_dir)
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
        "descriptor_ptr",
        "--require-future-wna16-kernel-side-consumer-execution",
        "--require-wna16-side-consumer-variant-execution",
        "--device",
        str(args.device),
        "--offload-arch",
        str(args.offload_arch),
        "--merged-output-json",
        str(output_dir / "all_four_field_merged_input.json"),
        "--stub-output-json",
        str(output_dir / "all_four_field_typed_consumer_stub.json"),
        "--output-json",
        str(output_dir / "all_four_field_native_runner.json"),
    ]
    for input_path in input_paths:
        argv.extend(["--input-json", str(input_path)])
    if args.hip_visible_devices is not None:
        argv.extend(["--hip-visible-devices", str(args.hip_visible_devices)])
    if args.force_build:
        argv.append("--force-build")
    parsed = native_runner.build_parser().parse_args(argv)
    parsed.runner_json = None
    return parsed


def _run_native(
    args: argparse.Namespace,
    *,
    input_paths: list[Path],
) -> tuple[dict[str, Any], float]:
    parsed = _native_args(args, input_paths=input_paths)
    start_ns = time.perf_counter_ns()
    report = native_runner.run_canary(parsed)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return report, elapsed_ms


def _check_native_report(
    report: dict[str, Any],
    stub: dict[str, Any],
    *,
    fourth: dict[str, Any],
    selected_input_paths: list[Path],
    selected_input_manifest: dict[str, Any],
    merged_input: dict[str, Any] | None,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    if report.get("passed") is not True:
        failures.append("native_report_not_passed")
    if report.get("failures") != []:
        failures.append("native_report_failures_not_empty")
    if report.get("source") != "online_merged_future_native_arg_slot_canary_runner":
        failures.append("native_report_source_mismatch")
    source_count = _int_metric(report, "selected_source_count")
    row_count = _int_metric(report, "merged_row_count")
    active_rows = _int_metric(report, "dispatch_active_rows")
    fourth_source_count = _int_metric(fourth, "source_count")
    fourth_row_count = _int_metric(fourth, "row_count")
    if source_count is None or source_count < min_source_count:
        failures.append("native_source_count_invalid")
    if row_count is None or row_count < min_row_count:
        failures.append("native_row_count_invalid")
    if fourth_source_count is not None and source_count != fourth_source_count:
        failures.append("native_source_count_fourth_gate_mismatch")
    if fourth_row_count is not None and row_count != fourth_row_count:
        failures.append("native_row_count_fourth_gate_mismatch")
    if row_count is not None and active_rows != row_count:
        failures.append("native_dispatch_active_rows_mismatch")
    native_input_jsons = report.get("input_jsons")
    if native_input_jsons != [str(path) for path in selected_input_paths]:
        failures.append("native_input_jsons_manifest_mismatch")
    if report.get("selected_input_json_count") != len(selected_input_paths):
        failures.append("native_selected_input_json_count_mismatch")
    if (
        report.get("selected_input_manifest_sha256")
        != selected_input_manifest["input_manifest_sha256"]
    ):
        failures.append("native_selected_input_manifest_sha256_mismatch")
    if merged_input is None:
        failures.append("merged_input_payload_missing")
    else:
        merge_context = merged_input.get("_merge_context")
        if not isinstance(merge_context, dict):
            failures.append("merged_input_merge_context_missing")
        else:
            if merge_context.get("source_count") != len(selected_input_paths):
                failures.append("merged_input_source_count_mismatch")
            row_spans = merge_context.get("row_spans")
            if not isinstance(row_spans, list):
                failures.append("merged_input_row_spans_missing")
            else:
                row_span_paths = [
                    row.get("path") for row in row_spans if isinstance(row, dict)
                ]
                if row_span_paths != [str(path) for path in selected_input_paths]:
                    failures.append("merged_input_row_span_paths_mismatch")
    for key in (
        "require_future_wna16_typed_slot_kernel_variant",
        "require_future_wna16_kernel_accept_typed_slot",
        "require_future_wna16_kernel_side_consumer_execution",
        "require_wna16_side_consumer_variant_execution",
        "require_wna16_adjacent_typed_slot",
    ):
        if report.get(key) is not True:
            failures.append(f"{key}_not_true")
    for key in (
        "future_wna16_typed_slot_kernel_variant_all_handle_fields_read",
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read",
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read",
        "wna16_side_consumer_variant_execution_all_handle_fields_read",
    ):
        if report.get(key) is not True:
            failures.append(f"{key}_not_true")
    failures.extend(_check_false_boundary("native_report", report))
    for key in ("uses_current_wna16_args", "passes_current_wna16_args"):
        if key not in report:
            failures.append(f"native_report_{key}_missing")
        elif report.get(key) is not False:
            failures.append(f"native_report_{key}_not_false")
    if report.get("no_payload") is not True:
        failures.append("native_report_no_payload_not_true")
    for prefix in REQUIRED_PREFIXES:
        if stub.get(f"{prefix}_checked") is not True:
            failures.append(f"{prefix}_checked_not_true")
        if stub.get(f"{prefix}_row_count") != row_count:
            failures.append(f"{prefix}_row_count_mismatch")
        if stub.get(f"{prefix}_row_ok_count") != row_count:
            failures.append(f"{prefix}_row_ok_count_mismatch")
        if stub.get(f"{prefix}_error_count") != 0:
            failures.append(f"{prefix}_error_count_nonzero")
        if stub.get(f"{prefix}_payload_bytes") != 0:
            failures.append(f"{prefix}_payload_bytes_nonzero")
        for key in REQUIRED_PREFIX_FALSE_BOUNDARY_KEYS:
            full_key = f"{prefix}_{key}"
            if full_key not in stub:
                failures.append(f"{full_key}_missing")
            elif stub.get(full_key) is not False:
                failures.append(f"{full_key}_not_false")
        if stub.get(f"{prefix}_explicit_typed_abi_slot") is not True:
            failures.append(f"{prefix}_explicit_typed_abi_slot_not_true")
        if not _is_hex_u64(stub.get(f"{prefix}_hash_accumulator")):
            failures.append(f"{prefix}_hash_accumulator_invalid")
        if not _is_hex_u64(stub.get(f"{prefix}_handle_projection_hash_accumulator")):
            failures.append(f"{prefix}_handle_projection_hash_accumulator_invalid")
        for field in HANDLE_FIELDS:
            base = f"{prefix}_{field}_read"
            if stub.get(f"{base}_row_count") != row_count:
                failures.append(f"{base}_row_count_mismatch")
            if stub.get(f"{base}_row_ok_count") != row_count:
                failures.append(f"{base}_row_ok_count_mismatch")
            if stub.get(f"{base}_error_count") != 0:
                failures.append(f"{base}_error_count_nonzero")
            if not _is_hex_u64(stub.get(f"{base}_hash_accumulator")):
                failures.append(f"{base}_hash_invalid")
    return failures


def run_all_four_field_consumer(args: argparse.Namespace) -> dict[str, Any]:
    fourth_path = _resolve(args.fourth_field_json)
    output_path = _resolve(args.output_json)
    output_dir = _resolve(args.output_dir)
    failures: list[str] = []
    fourth: dict[str, Any] | None
    input_paths: list[Path]
    fourth, input_paths, fourth_failures = _load_fourth_gate(
        fourth_path,
        min_source_count=int(args.min_source_count),
        min_row_count=int(args.min_row_count),
    )
    failures.extend(fourth_failures)
    if not args.run_native_consumer:
        failures.append("run_native_consumer_must_remain_enabled_for_lab_gate")
    if not args.require_native_consumer:
        failures.append("require_native_consumer_must_remain_enabled_for_lab_gate")

    native_report: dict[str, Any] | None = None
    native_wall_ms: float | None = None
    stub_payload: dict[str, Any] | None = None
    selected_input_paths = input_paths[: int(args.max_inputs)]
    input_manifest = _input_manifest(selected_input_paths)
    post_native_input_manifest: dict[str, Any] | None = None
    merged_input_payload: dict[str, Any] | None = None
    if fourth is not None and not failures and args.run_native_consumer:
        try:
            native_report, native_wall_ms = _run_native(args, input_paths=input_paths)
        except Exception as exc:  # pragma: no cover - exercised by tests
            failures.append(
                f"all_four_field_native_consumer_exception:"
                f"{exc.__class__.__name__}:{exc}"
            )
        else:
            stub_path = output_dir / "all_four_field_typed_consumer_stub.json"
            merged_path = output_dir / "all_four_field_merged_input.json"
            post_native_input_manifest = _input_manifest(selected_input_paths)
            if (
                post_native_input_manifest["input_manifest_sha256"]
                != input_manifest["input_manifest_sha256"]
            ):
                failures.append("selected_input_manifest_changed_during_native_run")
            try:
                stub_payload = _load_json(stub_path)
            except Exception as exc:
                failures.append(
                    f"all_four_field_stub_load_failed:{exc.__class__.__name__}:{exc}"
                )
            try:
                merged_input_payload = _load_json(merged_path)
            except Exception as exc:
                failures.append(
                    f"all_four_field_merged_input_load_failed:"
                    f"{exc.__class__.__name__}:{exc}"
                )
            if stub_payload is not None:
                failures.extend(
                    _check_native_report(
                        native_report,
                        stub_payload,
                        fourth=fourth,
                        selected_input_paths=selected_input_paths,
                        selected_input_manifest=input_manifest,
                        merged_input=merged_input_payload,
                        min_source_count=int(args.min_source_count),
                        min_row_count=int(args.min_row_count),
                    )
                )
    elif args.run_native_consumer:
        failures.append("all_four_field_native_consumer_skipped_due_to_fourth_gate")
    if args.require_native_consumer and native_report is None:
        failures.append("all_four_field_native_consumer_required_but_not_executed")

    native_json = output_dir / "all_four_field_native_runner.json"
    merged_json = output_dir / "all_four_field_merged_input.json"
    stub_json = output_dir / "all_four_field_typed_consumer_stub.json"
    native_sha = _sha256(native_json) if native_json.exists() else None
    merged_sha = _sha256(merged_json) if merged_json.exists() else None
    stub_sha = _sha256(stub_json) if stub_json.exists() else None
    row_count = (
        native_report.get("merged_row_count")
        if native_report is not None
        else (fourth or {}).get("row_count")
    )
    source_count = (
        native_report.get("selected_source_count")
        if native_report is not None
        else (fourth or {}).get("source_count")
    )
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": ARTIFACT_KIND,
        "all_four_field_consumer_name": GATE_NAME,
        "all_four_field_consumer_mode": GATE_MODE,
        "all_four_field_consumer_source": GATE_SOURCE,
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "wall_ms_observed_only": True,
        "passed": passed,
        "failures": failures,
        "fourth_field_json": str(fourth_path),
        "fourth_field_sha256": _sha256(fourth_path) if fourth_path.exists() else None,
        "fourth_field_gate_ready": fourth is not None and not fourth_failures,
        "input_json_count": len(input_paths),
        "selected_input_json_count": len(selected_input_paths),
        "selected_input_manifest_sha256": input_manifest["input_manifest_sha256"],
        "post_native_input_manifest_sha256": (
            post_native_input_manifest["input_manifest_sha256"]
            if post_native_input_manifest
            else None
        ),
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": (
            native_report.get("dispatch_active_rows")
            if native_report is not None
            else None
        ),
        "native_consumer_json": str(native_json),
        "native_consumer_sha256": native_sha,
        "merged_input_json": str(merged_json),
        "merged_input_sha256": merged_sha,
        "stub_output_json": str(stub_json),
        "stub_output_sha256": stub_sha,
        "native_consumer_requested": bool(args.run_native_consumer),
        "native_consumer_executed": native_report is not None,
        "native_consumer_passed": native_report.get("passed") if native_report else None,
        "native_consumer_outer_wall_ms": native_wall_ms,
        "native_consumer_wall_ms_observed_only": True,
        "field_names": list(HANDLE_FIELDS),
        "future_wna16_kernel_side_consumer_execution_checked": (
            stub_payload.get("future_wna16_kernel_side_consumer_execution_checked")
            if stub_payload
            else None
        ),
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": (
            native_report.get(
                "future_wna16_kernel_side_consumer_execution_all_handle_fields_read"
            )
            if native_report
            else None
        ),
        "wna16_side_consumer_variant_execution_checked": (
            stub_payload.get("wna16_side_consumer_variant_execution_checked")
            if stub_payload
            else None
        ),
        "wna16_side_consumer_variant_execution_all_handle_fields_read": (
            native_report.get("wna16_side_consumer_variant_execution_all_handle_fields_read")
            if native_report
            else None
        ),
        "future_wna16_typed_slot_kernel_variant_all_handle_fields_read": (
            native_report.get("future_wna16_typed_slot_kernel_variant_all_handle_fields_read")
            if native_report
            else None
        ),
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read": (
            native_report.get("future_wna16_kernel_accept_typed_slot_all_handle_fields_read")
            if native_report
            else None
        ),
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
        "block_threads": int(args.block_threads),
        "device": int(args.device),
        "offload_arch": str(args.offload_arch),
        "hip_visible_devices": args.hip_visible_devices,
        "max_inputs": int(args.max_inputs),
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if stub_payload:
        for prefix in REQUIRED_PREFIXES:
            report[f"{prefix}_hash_accumulator"] = stub_payload.get(
                f"{prefix}_hash_accumulator"
            )
            report[f"{prefix}_handle_projection_hash_accumulator"] = (
                stub_payload.get(f"{prefix}_handle_projection_hash_accumulator")
            )
            for field in HANDLE_FIELDS:
                report[f"{prefix}_{field}_read_row_ok_count"] = stub_payload.get(
                    f"{prefix}_{field}_read_row_ok_count"
                )
                report[f"{prefix}_{field}_read_hash_accumulator"] = stub_payload.get(
                    f"{prefix}_{field}_read_hash_accumulator"
                )
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 all-four-field typed-slot consumer failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fourth-field-json", default=str(DEFAULT_FOURTH_FIELD_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-inputs", type=int, default=128)
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--run-native-consumer",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-native-consumer",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_all_four_field_consumer(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
