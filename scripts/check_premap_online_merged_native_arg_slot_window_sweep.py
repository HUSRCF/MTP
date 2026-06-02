#!/usr/bin/env python3
"""Check an online-merged future-native arg-slot row-window sweep artifact.

This is a static artifact checker.  It verifies that a previously generated
window sweep covers full/head/middle/tail row slices with the strict no-op
kernel boundary intact.  It does not refresh GPU/native canaries.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_premap_online_merged_native_arg_slot_window_sweep import (  # noqa: E402
    DEFAULT_OUTPUT_JSON,
    _window_bounds,
)


REQUIRED_WINDOWS = ("full", "head", "middle", "tail")
SAFETY_FALSE_FIELDS = (
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "current_wna16_arg_compatible",
)
_FUTURE_KERNEL_REQUIRED_FIELD_MASK = 0x7
_FUTURE_KERNEL_ALL_FIELD_MASK = 0xF
_FUTURE_KERNEL_FIELD_MASK_PREFIXES = (
    "future_kernel_native_consumer",
    "future_kernel_native_launch_consumer",
    "future_kernel_native_dispatch_consumer",
    "future_kernel_native_dispatch_ptr_consumer",
    "future_kernel_native_arg_slot_consumer",
)
ARG_SLOT_FIELD_READ_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON must contain an object")
    return payload


def _safe_load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _load_json(path), None
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return None, type(exc).__name__


def _resolve_child_path(value: object, *, parent: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return parent / path


def _check_future_field_masks(
    summary: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    for prefix in _FUTURE_KERNEL_FIELD_MASK_PREFIXES:
        field_key = f"{prefix}_field_mask"
        required_key = f"{prefix}_required_field_mask"
        field_mask = summary.get(field_key)
        required_mask = summary.get(required_key)
        if field_mask is None:
            failures.append(f"{label}_child_stub_{field_key}_missing")
            continue
        if required_mask is None:
            failures.append(f"{label}_child_stub_{required_key}_missing")
            continue
        if (
            not isinstance(field_mask, int)
            or isinstance(field_mask, bool)
            or not isinstance(required_mask, int)
            or isinstance(required_mask, bool)
        ):
            failures.append(f"{label}_child_stub_{prefix}_field_mask_type_mismatch")
            continue
        if required_mask != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
            failures.append(f"{label}_child_stub_{required_key}_mismatch")
        if field_mask != _FUTURE_KERNEL_ALL_FIELD_MASK:
            failures.append(f"{label}_child_stub_{field_key}_not_all_fields")
    return failures


def _check_arg_slot_field_reads(
    summary: dict[str, Any],
    *,
    label: str,
    expected_active: int,
) -> list[str]:
    failures: list[str] = []
    for field in ARG_SLOT_FIELD_READ_FIELDS:
        prefix = f"future_kernel_native_arg_slot_consumer_{field}_read"
        for suffix, expected in (
            ("row_count", expected_active),
            ("row_ok_count", expected_active),
            ("error_count", 0),
        ):
            key = f"{prefix}_{suffix}"
            if summary.get(key) != expected:
                failures.append(f"{label}_child_stub_{key}_mismatch")
        hash_key = f"{prefix}_hash_accumulator"
        hash_value = summary.get(hash_key)
        if not isinstance(hash_value, str) or not hash_value:
            failures.append(f"{label}_child_stub_{hash_key}_missing")
    return failures


def _check_child_artifact(
    child: dict[str, Any],
    *,
    label: str,
    expected_offset: int,
    expected_limit: int,
    expected_active: int,
    expected_programs: int,
    expected_block_threads: int,
    expected_merged_row_count: int,
    expected_mirror_field: str | None,
) -> list[str]:
    failures: list[str] = []
    expected_pairs: dict[str, Any] = {
        "passed": True,
        "failures": [],
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "handle_projection_hashchain_equal": True,
        "dispatch_row_offset": expected_offset,
        "dispatch_row_limit": expected_limit,
        "dispatch_active_rows": expected_active,
        "dispatch_expected_program_count": expected_programs,
        "block_threads": expected_block_threads,
        "merged_row_count": expected_merged_row_count,
    }
    if expected_mirror_field is not None:
        expected_pairs["mirror_field"] = expected_mirror_field
    for key, expected in expected_pairs.items():
        if child.get(key) != expected:
            failures.append(f"{label}_child_{key}_mismatch")
    stub_summary = child.get("stub_summary")
    if not isinstance(stub_summary, dict):
        failures.append(f"{label}_child_stub_summary_missing")
    else:
        for key, expected in {
            "passed": True,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_row_count": expected_active,
            "future_kernel_native_arg_slot_consumer_row_ok_count": expected_active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": expected_active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": expected_active,
            "future_kernel_native_dispatch_consumer_program_count": expected_programs,
            "future_kernel_native_dispatch_consumer_block_x": expected_block_threads,
            "future_kernel_native_dispatch_consumer_row_limit": expected_limit,
        }.items():
            if stub_summary.get(key) != expected:
                failures.append(f"{label}_child_stub_{key}_mismatch")
        if expected_mirror_field is not None and stub_summary.get(
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
        ) != expected_mirror_field:
            failures.append(
                f"{label}_child_stub_single_field_mirror_field_name_mismatch"
            )
        failures.extend(_check_future_field_masks(stub_summary, label=label))
        failures.extend(
            _check_arg_slot_field_reads(
                stub_summary,
                label=label,
                expected_active=expected_active,
            )
        )
    return failures


def check_window_sweep_artifact(
    path: Path,
    *,
    expected_window_size: int = 512,
    expected_block_threads: int = 256,
    min_row_count: int = 257,
    expected_mirror_field: str | None = "scale_metadata_handle",
    require_child_artifacts: bool = True,
    require_non_degenerate_windows: bool = True,
) -> dict[str, Any]:
    sweep_path = path.resolve()
    payload, error = _safe_load_json(sweep_path)
    if payload is None:
        return {
            "passed": False,
            "failures": [f"window_sweep_json_read_failed:{error}"],
            "source": "online_merged_future_native_arg_slot_window_sweep_check",
            "window_sweep_json": str(sweep_path),
        }

    failures: list[str] = []
    if payload.get("source") != "online_merged_future_native_arg_slot_window_sweep_runner":
        failures.append("source_mismatch")
    if payload.get("passed") is not True:
        failures.append("window_sweep_not_passed")
    if payload.get("failures") != []:
        failures.append("window_sweep_failures_not_empty")
    if payload.get("payload_bytes") != 0:
        failures.append("payload_bytes_mismatch")
    for field in ("passed_to_kernel", "changes_kernel_launch_args"):
        if payload.get(field) is not False:
            failures.append(f"{field}_mismatch")
    if payload.get("window_size") != int(expected_window_size):
        failures.append("window_size_mismatch")
    if expected_mirror_field is not None and payload.get("mirror_field") != expected_mirror_field:
        failures.append("mirror_field_mismatch")

    try:
        row_count = int(payload.get("row_count"))
    except (TypeError, ValueError):
        row_count = -1
        failures.append("row_count_invalid")
    if row_count < int(min_row_count):
        failures.append("row_count_below_min")
    if require_non_degenerate_windows and row_count <= int(expected_window_size):
        failures.append("row_count_not_larger_than_window_size")

    windows = payload.get("windows")
    if not isinstance(windows, dict):
        failures.append("windows_missing")
        windows = {}

    if row_count > 0:
        expected_bounds = {
            "full": (0, row_count),
            **_window_bounds(row_count, int(expected_window_size)),
        }
    else:
        expected_bounds = {}

    for label in REQUIRED_WINDOWS:
        window = windows.get(label)
        if not isinstance(window, dict):
            failures.append(f"{label}_window_missing")
            continue
        expected_offset, expected_limit = expected_bounds.get(label, (-1, -1))
        expected_active = expected_limit - expected_offset
        if window.get("passed") is not True:
            failures.append(f"{label}_window_not_passed")
        if window.get("merged_row_count") != row_count:
            failures.append(f"{label}_merged_row_count_mismatch")
        if window.get("dispatch_row_offset") != expected_offset:
            failures.append(f"{label}_dispatch_row_offset_mismatch")
        if window.get("dispatch_row_limit") != expected_limit:
            failures.append(f"{label}_dispatch_row_limit_mismatch")
        if window.get("dispatch_active_rows") != expected_active:
            failures.append(f"{label}_dispatch_active_rows_mismatch")
        expected_programs = int(math.ceil(expected_active / int(expected_block_threads)))
        if window.get("dispatch_expected_program_count") != expected_programs:
            failures.append(f"{label}_dispatch_expected_program_count_mismatch")

        if require_child_artifacts:
            child_path = _resolve_child_path(window.get("output_json"), parent=sweep_path.parent)
            if child_path is None:
                failures.append(f"{label}_child_output_json_missing")
                continue
            child, child_error = _safe_load_json(child_path)
            if child is None:
                failures.append(f"{label}_child_output_json_read_failed:{child_error}")
                continue
            failures.extend(
                _check_child_artifact(
                    child,
                    label=label,
                    expected_offset=expected_offset,
                    expected_limit=expected_limit,
                    expected_active=expected_active,
                    expected_programs=expected_programs,
                    expected_block_threads=int(expected_block_threads),
                    expected_merged_row_count=row_count,
                    expected_mirror_field=expected_mirror_field,
                )
            )

    return {
        "passed": not failures,
        "failures": failures,
        "source": "online_merged_future_native_arg_slot_window_sweep_check",
        "window_sweep_json": str(sweep_path),
        "expected_window_size": int(expected_window_size),
        "expected_block_threads": int(expected_block_threads),
        "min_row_count": int(min_row_count),
        "expected_mirror_field": expected_mirror_field,
        "require_child_artifacts": bool(require_child_artifacts),
        "require_non_degenerate_windows": bool(require_non_degenerate_windows),
        "require_child_field_masks": bool(require_child_artifacts),
        "row_count": row_count,
        "windows_checked": list(REQUIRED_WINDOWS),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window_sweep_json", nargs="?", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--expected-window-size", type=int, default=512)
    parser.add_argument("--expected-block-threads", type=int, default=256)
    parser.add_argument("--min-row-count", type=int, default=257)
    parser.add_argument("--expected-mirror-field", default="scale_metadata_handle")
    parser.add_argument("--no-require-child-artifacts", action="store_true")
    parser.add_argument("--allow-degenerate-windows", action="store_true")
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_window_sweep_artifact(
        args.window_sweep_json,
        expected_window_size=int(args.expected_window_size),
        expected_block_threads=int(args.expected_block_threads),
        min_row_count=int(args.min_row_count),
        expected_mirror_field=args.expected_mirror_field,
        require_child_artifacts=not bool(args.no_require_child_artifacts),
        require_non_degenerate_windows=not bool(args.allow_degenerate_windows),
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
