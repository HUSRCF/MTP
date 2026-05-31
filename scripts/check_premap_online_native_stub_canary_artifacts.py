#!/usr/bin/env python3
"""Check online native-stub canary runner/preflight/status consistency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RUNNER_JSON = Path(
    "outputs/reports/premap_kernel_consumer/"
    "online_prelaunch_native_stub_canary_runner.json"
)
DEFAULT_PREFLIGHT_JSON = Path(
    "outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary.json"
)
DEFAULT_STATUS_JSON = Path(
    "outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary.json"
)
_FUTURE_KERNEL_REQUIRED_FIELD_MASK = 0x7
_FUTURE_KERNEL_ALL_FIELD_MASK = 0xF
_FUTURE_KERNEL_AUX_FIELD_MASK = 0x8
_UINT64_MASK = (1 << 64) - 1
_PROGRAM_ITERATION_HASH_FORMULA = (
    "mix64(grid_x + 0xd15c2001) ^ mix64(block_x + 0xd15c2002) ^ "
    "mix64(row_offset + 0xd15c2003) ^ mix64(row_limit + 0xd15c2004) ^ "
    "mix64(last_program_active_rows + 0xd15c2005) ^ "
    "mix64(inactive_lane_count + 0xd15c2006)"
)


def _resolve(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _mix64(value: int) -> int:
    x = value & _UINT64_MASK
    x ^= x >> 33
    x = (x * 0xFF51AFD7ED558CCD) & _UINT64_MASK
    x ^= x >> 33
    x = (x * 0xC4CEB9FE1A85EC53) & _UINT64_MASK
    x ^= x >> 33
    return x & _UINT64_MASK


def _hex64(value: Any) -> int | None:
    if isinstance(value, str) and value:
        try:
            parsed = int(value, 16)
        except ValueError:
            return None
        return parsed if 0 <= parsed <= _UINT64_MASK else None
    return None


def _program_iteration_hash(
    *,
    grid_x: int,
    block_x: int,
    row_offset: int,
    row_limit: int,
    last_program_active_rows: int,
    inactive_lane_count: int,
) -> int:
    return (
        _mix64(grid_x + 0xD15C2001)
        ^ _mix64(block_x + 0xD15C2002)
        ^ _mix64(row_offset + 0xD15C2003)
        ^ _mix64(row_limit + 0xD15C2004)
        ^ _mix64(last_program_active_rows + 0xD15C2005)
        ^ _mix64(inactive_lane_count + 0xD15C2006)
    ) & _UINT64_MASK


def _check_future_field_mask(
    stub: dict[str, Any],
    *,
    prefix: str,
    field_prefix: str,
    expected_field_name: str,
    failures: list[str],
) -> None:
    field_mask = stub.get(f"{field_prefix}_field_mask")
    required_mask = stub.get(f"{field_prefix}_required_field_mask")
    if field_mask is None:
        failures.append(f"{prefix}_{field_prefix}_field_mask_missing")
        return
    if required_mask is None:
        failures.append(f"{prefix}_{field_prefix}_required_field_mask_missing")
        return
    if (
        not isinstance(field_mask, int)
        or isinstance(field_mask, bool)
        or not isinstance(required_mask, int)
        or isinstance(required_mask, bool)
    ):
        failures.append(f"{prefix}_{field_prefix}_field_mask_type_mismatch")
        return
    if required_mask != _FUTURE_KERNEL_REQUIRED_FIELD_MASK:
        failures.append(f"{prefix}_{field_prefix}_required_field_mask_mismatch")
    if (
        field_mask & _FUTURE_KERNEL_REQUIRED_FIELD_MASK
        != _FUTURE_KERNEL_REQUIRED_FIELD_MASK
    ):
        failures.append(f"{prefix}_{field_prefix}_required_field_mask_not_covered")
    if field_mask & ~_FUTURE_KERNEL_ALL_FIELD_MASK:
        failures.append(f"{prefix}_{field_prefix}_field_mask_unknown_bits")
    if expected_field_name == "aux_metadata_handle" and not (
        field_mask & _FUTURE_KERNEL_AUX_FIELD_MASK
    ):
        failures.append(f"{prefix}_{field_prefix}_aux_field_mask_missing")


def _check_stub_summary(
    stub: Any,
    *,
    prefix: str,
    failures: list[str],
    require_kernel_side_consumer_path: bool = False,
) -> tuple[int | None, int | None]:
    if not isinstance(stub, dict):
        failures.append(f"{prefix}_summary_missing")
        stub = {}
    if stub.get("passed") is not True or stub.get("ok") is not True:
        failures.append(f"{prefix}_not_passed")
    row_count = _int(stub.get("row_count"))
    row_ok_count = _int(stub.get("row_ok_count"))
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
    expected_stub = {
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    for key, expected in expected_stub.items():
        if stub.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")
    if require_kernel_side_consumer_path:
        expected_path = {
            "kernel_side_consumer_path_checked": True,
            "kernel_side_consumer_path_error_count": 0,
            "kernel_side_consumer_path_payload_bytes": 0,
            "kernel_side_consumer_path_passed_to_kernel": False,
            "kernel_side_consumer_path_changes_kernel_launch_args": False,
            "kernel_side_consumer_path_current_wna16_arg_compatible": False,
        }
        for key, expected in expected_path.items():
            if stub.get(key) != expected:
                failures.append(f"{prefix}_{key}_mismatch")
        if stub.get("kernel_side_consumer_path_name") != (
            "premap_kernel_side_typed_consumer_path_v1"
        ):
            failures.append(f"{prefix}_kernel_side_consumer_path_name_mismatch")
        path_row_count = _int(stub.get("kernel_side_consumer_path_row_count"))
        path_row_ok_count = _int(stub.get("kernel_side_consumer_path_row_ok_count"))
        if row_count is not None and path_row_count != row_count:
            failures.append(f"{prefix}_kernel_side_consumer_path_row_count_mismatch")
        if row_count is not None and path_row_ok_count != row_count:
            failures.append(
                f"{prefix}_kernel_side_consumer_path_row_ok_count_mismatch"
            )
    return row_count, row_ok_count


def _check_single_field_mirror_summary(
    stub: Any,
    *,
    prefix: str,
    expected_field_name: str,
    failures: list[str],
    require_envelope: bool = False,
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    if require_envelope:
        expected_envelope = {
            "kernel_consumer_envelope_checked": True,
            "kernel_consumer_envelope_payload_bytes": 0,
            "kernel_consumer_envelope_passed_to_kernel": False,
        }
        for key, expected in expected_envelope.items():
            if stub.get(key) != expected:
                failures.append(f"{prefix}_{key}_mismatch")
    expected_mirror = {
        "single_field_mirror_checked": True,
        "single_field_mirror_field_name": expected_field_name,
        "single_field_mirror_error_count": 0,
    }
    for key, expected in expected_mirror.items():
        if stub.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")
    mirror_row_count = _int(stub.get("single_field_mirror_row_count"))
    mirror_row_ok_count = _int(stub.get("single_field_mirror_row_ok_count"))
    if row_count is not None and mirror_row_count != row_count:
        failures.append(f"{prefix}_single_field_mirror_row_count_mismatch")
    if row_count is not None and mirror_row_ok_count != row_count:
        failures.append(f"{prefix}_single_field_mirror_row_ok_count_mismatch")
    return row_count, row_ok_count


def _check_kernel_side_compatible_summary(
    stub: Any,
    *,
    prefix: str,
    failures: list[str],
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    expected = {
        "kernel_side_compatible_consumer_checked": True,
        "kernel_side_compatible_consumer_name": (
            "premap_kernel_side_compatible_consumer_abi_v1"
        ),
        "kernel_side_compatible_consumer_mode": (
            "readonly_kernel_side_compatible_consumer_abi"
        ),
        "kernel_side_compatible_consumer_source": (
            "premap_kernel_side_typed_consumer_launch_envelope_v1"
        ),
        "kernel_side_compatible_consumer_error_count": 0,
        "kernel_side_compatible_consumer_payload_bytes": 0,
        "kernel_side_compatible_consumer_passed_to_kernel": False,
        "kernel_side_compatible_consumer_changes_kernel_launch_args": False,
        "kernel_side_compatible_consumer_current_wna16_arg_compatible": False,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    compatible_row_count = _int(
        stub.get("kernel_side_compatible_consumer_row_count")
    )
    compatible_row_ok_count = _int(
        stub.get("kernel_side_compatible_consumer_row_ok_count")
    )
    if row_count is not None and compatible_row_count != row_count:
        failures.append(f"{prefix}_kernel_side_compatible_row_count_mismatch")
    if row_count is not None and compatible_row_ok_count != row_count:
        failures.append(f"{prefix}_kernel_side_compatible_row_ok_count_mismatch")
    return row_count, row_ok_count


def _check_future_kernel_args_summary(
    stub: Any,
    *,
    prefix: str,
    expected_field_name: str = "scale_metadata_handle",
    failures: list[str],
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    expected = {
        "future_kernel_consumer_args_checked": True,
        "future_kernel_consumer_args_name": (
            "premap_future_kernel_side_consumer_args_v1"
        ),
        "future_kernel_consumer_args_mode": (
            "readonly_future_kernel_consumer_args"
        ),
        "future_kernel_consumer_args_source": (
            "premap_kernel_side_typed_consumer_launch_envelope_v1"
        ),
        "future_kernel_consumer_args_error_count": 0,
        "future_kernel_consumer_args_payload_bytes": 0,
        "future_kernel_consumer_args_passed_to_kernel": False,
        "future_kernel_consumer_args_changes_kernel_launch_args": False,
        "future_kernel_consumer_args_current_wna16_arg_compatible": False,
        "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
        "future_kernel_consumer_args_single_field_mirror_checked": True,
        "future_kernel_consumer_args_single_field_mirror_field_name": expected_field_name,
        "future_kernel_consumer_args_single_field_mirror_error_count": 0,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    _check_future_field_mask(
        stub,
        prefix=prefix,
        field_prefix="future_kernel_consumer_args",
        expected_field_name=expected_field_name,
        failures=failures,
    )
    future_row_count = _int(stub.get("future_kernel_consumer_args_row_count"))
    future_row_ok_count = _int(
        stub.get("future_kernel_consumer_args_row_ok_count")
    )
    if row_count is not None and future_row_count != row_count:
        failures.append(f"{prefix}_future_kernel_args_row_count_mismatch")
    if row_count is not None and future_row_ok_count != row_count:
        failures.append(f"{prefix}_future_kernel_args_row_ok_count_mismatch")
    mirror_row_count = _int(
        stub.get("future_kernel_consumer_args_single_field_mirror_row_count")
    )
    mirror_row_ok_count = _int(
        stub.get("future_kernel_consumer_args_single_field_mirror_row_ok_count")
    )
    if row_count is not None and mirror_row_count != row_count:
        failures.append(f"{prefix}_future_kernel_args_mirror_row_count_mismatch")
    if row_count is not None and mirror_row_ok_count != row_count:
        failures.append(f"{prefix}_future_kernel_args_mirror_row_ok_count_mismatch")
    return row_count, row_ok_count


def _check_future_kernel_args_compatible_path_summary(
    stub: Any,
    *,
    prefix: str,
    failures: list[str],
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    expected = {
        "future_kernel_consumer_args_checked": True,
        "future_kernel_consumer_args_error_count": 0,
        "future_kernel_consumer_args_payload_bytes": 0,
        "future_kernel_consumer_args_passed_to_kernel": False,
        "future_kernel_consumer_args_changes_kernel_launch_args": False,
        "future_kernel_consumer_args_current_wna16_arg_compatible": False,
        "future_kernel_consumer_args_requires_wna16_arg_reinterpretation": False,
        "future_kernel_args_compatible_consumer_path_checked": True,
        "future_kernel_args_compatible_consumer_path_name": (
            "premap_future_kernel_args_compatible_consumer_path_v1"
        ),
        "future_kernel_args_compatible_consumer_path_mode": (
            "readonly_future_kernel_args_to_compatible_consumer_path"
        ),
        "future_kernel_args_compatible_consumer_path_source": (
            "premap_future_kernel_side_consumer_args_v1"
        ),
        "future_kernel_args_compatible_consumer_path_error_count": 0,
        "future_kernel_args_compatible_consumer_path_payload_bytes": 0,
        "future_kernel_args_compatible_consumer_path_passed_to_kernel": False,
        "future_kernel_args_compatible_consumer_path_changes_kernel_launch_args": False,
        "future_kernel_args_compatible_consumer_path_current_wna16_arg_compatible": False,
        "future_kernel_args_compatible_consumer_path_requires_wna16_arg_reinterpretation": False,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    future_row_count = _int(stub.get("future_kernel_consumer_args_row_count"))
    future_row_ok_count = _int(stub.get("future_kernel_consumer_args_row_ok_count"))
    compatible_row_count = _int(
        stub.get("future_kernel_args_compatible_consumer_path_row_count")
    )
    compatible_row_ok_count = _int(
        stub.get("future_kernel_args_compatible_consumer_path_row_ok_count")
    )
    if row_count is not None and future_row_count != row_count:
        failures.append(f"{prefix}_future_kernel_args_row_count_mismatch")
    if row_count is not None and future_row_ok_count != row_count:
        failures.append(f"{prefix}_future_kernel_args_row_ok_count_mismatch")
    if row_count is not None and compatible_row_count != row_count:
        failures.append(f"{prefix}_compatible_path_row_count_mismatch")
    if row_count is not None and compatible_row_ok_count != row_count:
        failures.append(f"{prefix}_compatible_path_row_ok_count_mismatch")
    return row_count, row_ok_count


def _check_future_kernel_native_consumer_summary(
    stub: Any,
    *,
    prefix: str,
    expected_field_name: str = "scale_metadata_handle",
    failures: list[str],
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    expected = {
        "future_kernel_native_consumer_checked": True,
        "future_kernel_native_consumer_abi_name": (
            "premap_future_kernel_native_consumer_abi_v1"
        ),
        "future_kernel_native_consumer_mode": (
            "readonly_future_kernel_native_consumer_abi"
        ),
        "future_kernel_native_consumer_source": (
            "premap_typed_handle_table_soa_fields"
        ),
        "future_kernel_native_consumer_error_count": 0,
        "future_kernel_native_consumer_payload_bytes": 0,
        "future_kernel_native_consumer_passed_to_kernel": False,
        "future_kernel_native_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_consumer_single_field_mirror_checked": True,
        "future_kernel_native_consumer_single_field_mirror_field_name": (
            expected_field_name
        ),
        "future_kernel_native_consumer_single_field_mirror_error_count": 0,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    _check_future_field_mask(
        stub,
        prefix=prefix,
        field_prefix="future_kernel_native_consumer",
        expected_field_name=expected_field_name,
        failures=failures,
    )
    native_row_count = _int(stub.get("future_kernel_native_consumer_row_count"))
    native_row_ok_count = _int(
        stub.get("future_kernel_native_consumer_row_ok_count")
    )
    if row_count is not None and native_row_count != row_count:
        failures.append(f"{prefix}_future_native_row_count_mismatch")
    if row_count is not None and native_row_ok_count != row_count:
        failures.append(f"{prefix}_future_native_row_ok_count_mismatch")
    mirror_row_count = _int(
        stub.get("future_kernel_native_consumer_single_field_mirror_row_count")
    )
    mirror_row_ok_count = _int(
        stub.get("future_kernel_native_consumer_single_field_mirror_row_ok_count")
    )
    if row_count is not None and mirror_row_count != row_count:
        failures.append(f"{prefix}_future_native_mirror_row_count_mismatch")
    if row_count is not None and mirror_row_ok_count != row_count:
        failures.append(f"{prefix}_future_native_mirror_row_ok_count_mismatch")
    return row_count, row_ok_count


def _check_future_kernel_native_launch_consumer_summary(
    stub: Any,
    *,
    prefix: str,
    expected_field_name: str = "scale_metadata_handle",
    failures: list[str],
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    expected = {
        "future_kernel_native_consumer_checked": True,
        "future_kernel_native_consumer_error_count": 0,
        "future_kernel_native_launch_consumer_checked": True,
        "future_kernel_native_launch_consumer_abi_name": (
            "premap_future_kernel_native_consumer_launch_abi_v1"
        ),
        "future_kernel_native_launch_consumer_mode": (
            "readonly_future_kernel_native_consumer_launch_abi"
        ),
        "future_kernel_native_launch_consumer_source": (
            "premap_future_kernel_native_consumer_abi_v1"
        ),
        "future_kernel_native_launch_consumer_error_count": 0,
        "future_kernel_native_launch_consumer_payload_bytes": 0,
        "future_kernel_native_launch_consumer_passed_to_kernel": False,
        "future_kernel_native_launch_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_launch_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_launch_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_launch_consumer_single_field_mirror_checked": True,
        "future_kernel_native_launch_consumer_single_field_mirror_field_name": (
            expected_field_name
        ),
        "future_kernel_native_launch_consumer_single_field_mirror_error_count": 0,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    _check_future_field_mask(
        stub,
        prefix=prefix,
        field_prefix="future_kernel_native_launch_consumer",
        expected_field_name=expected_field_name,
        failures=failures,
    )
    native_row_count = _int(stub.get("future_kernel_native_consumer_row_count"))
    native_row_ok_count = _int(
        stub.get("future_kernel_native_consumer_row_ok_count")
    )
    launch_row_count = _int(
        stub.get("future_kernel_native_launch_consumer_row_count")
    )
    launch_row_ok_count = _int(
        stub.get("future_kernel_native_launch_consumer_row_ok_count")
    )
    mirror_row_count = _int(
        stub.get("future_kernel_native_launch_consumer_single_field_mirror_row_count")
    )
    mirror_row_ok_count = _int(
        stub.get("future_kernel_native_launch_consumer_single_field_mirror_row_ok_count")
    )
    if row_count is not None and native_row_count != row_count:
        failures.append(f"{prefix}_future_native_row_count_mismatch")
    if row_count is not None and native_row_ok_count != row_count:
        failures.append(f"{prefix}_future_native_row_ok_count_mismatch")
    if row_count is not None and launch_row_count != row_count:
        failures.append(f"{prefix}_future_native_launch_row_count_mismatch")
    if row_count is not None and launch_row_ok_count != row_count:
        failures.append(f"{prefix}_future_native_launch_row_ok_count_mismatch")
    if row_count is not None and mirror_row_count != row_count:
        failures.append(f"{prefix}_future_native_launch_mirror_row_count_mismatch")
    if row_count is not None and mirror_row_ok_count != row_count:
        failures.append(f"{prefix}_future_native_launch_mirror_row_ok_count_mismatch")
    return row_count, row_ok_count


def _check_future_kernel_native_dispatch_consumer_summary(
    stub: Any,
    *,
    prefix: str,
    expected_field_name: str = "scale_metadata_handle",
    failures: list[str],
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    expected = {
        "future_kernel_native_consumer_checked": True,
        "future_kernel_native_consumer_error_count": 0,
        "future_kernel_native_launch_consumer_checked": True,
        "future_kernel_native_launch_consumer_error_count": 0,
        "future_kernel_native_dispatch_consumer_checked": True,
        "future_kernel_native_dispatch_consumer_abi_name": (
            "premap_future_kernel_native_consumer_dispatch_abi_v1"
        ),
        "future_kernel_native_dispatch_consumer_mode": (
            "readonly_future_kernel_native_consumer_dispatch_abi"
        ),
        "future_kernel_native_dispatch_consumer_source": (
            "premap_future_kernel_native_consumer_launch_abi_v1"
        ),
        "future_kernel_native_dispatch_consumer_error_count": 0,
        "future_kernel_native_dispatch_consumer_payload_bytes": 0,
        "future_kernel_native_dispatch_consumer_passed_to_kernel": False,
        "future_kernel_native_dispatch_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_dispatch_consumer_single_field_mirror_checked": True,
        "future_kernel_native_dispatch_consumer_single_field_mirror_field_name": (
            expected_field_name
        ),
        "future_kernel_native_dispatch_consumer_single_field_mirror_error_count": 0,
    }
    for key, expected_value in expected.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    _check_future_field_mask(
        stub,
        prefix=prefix,
        field_prefix="future_kernel_native_dispatch_consumer",
        expected_field_name=expected_field_name,
        failures=failures,
    )
    dispatch_grid = _int(stub.get("future_kernel_native_dispatch_consumer_grid_x"))
    dispatch_block = _int(stub.get("future_kernel_native_dispatch_consumer_block_x"))
    dispatch_offset = _int(stub.get("future_kernel_native_dispatch_consumer_row_offset"))
    dispatch_limit = _int(stub.get("future_kernel_native_dispatch_consumer_row_limit"))
    dispatch_rows_per_program = _int(
        stub.get("future_kernel_native_dispatch_consumer_rows_per_program")
    )
    dispatch_active_rows = _int(
        stub.get("future_kernel_native_dispatch_consumer_active_rows")
    )
    dispatch_launch_threads = _int(
        stub.get("future_kernel_native_dispatch_consumer_launch_threads")
    )
    dispatch_program_iteration_checked = stub.get(
        "future_kernel_native_dispatch_consumer_program_iteration_checked"
    )
    dispatch_program_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_program_count")
    )
    dispatch_full_program_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_full_program_count")
    )
    dispatch_last_program_active_rows = _int(
        stub.get("future_kernel_native_dispatch_consumer_last_program_active_rows")
    )
    dispatch_inactive_lane_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_inactive_lane_count")
    )
    dispatch_first_program_row_offset = _int(
        stub.get("future_kernel_native_dispatch_consumer_first_program_row_offset")
    )
    dispatch_last_program_row_offset = _int(
        stub.get("future_kernel_native_dispatch_consumer_last_program_row_offset")
    )
    dispatch_row_assignment_formula = stub.get(
        "future_kernel_native_dispatch_consumer_row_assignment_formula"
    )
    dispatch_program_iteration_hash = _hex64(
        stub.get("future_kernel_native_dispatch_consumer_program_iteration_hash")
    )
    if dispatch_grid is None or dispatch_grid <= 0:
        failures.append(f"{prefix}_future_native_dispatch_grid_x_invalid")
    if dispatch_block is None or dispatch_block <= 0:
        failures.append(f"{prefix}_future_native_dispatch_block_x_invalid")
    if (
        dispatch_rows_per_program is None
        or dispatch_block is None
        or dispatch_rows_per_program != dispatch_block
    ):
        failures.append(f"{prefix}_future_native_dispatch_rows_per_program_mismatch")
    dispatch_window_valid = (
        dispatch_offset is not None
        and dispatch_limit is not None
        and dispatch_offset >= 0
        and dispatch_limit > dispatch_offset
        and (row_count is None or dispatch_limit <= row_count)
    )
    if not dispatch_window_valid:
        failures.append(f"{prefix}_future_native_dispatch_row_window_invalid")
    expected_active_rows = (
        dispatch_limit - dispatch_offset if dispatch_window_valid else None
    )
    if expected_active_rows is not None and dispatch_active_rows != expected_active_rows:
        failures.append(f"{prefix}_future_native_dispatch_active_rows_mismatch")
    if dispatch_active_rows is not None and dispatch_active_rows <= 0:
        failures.append(f"{prefix}_future_native_dispatch_active_rows_invalid")
    if (
        dispatch_grid is not None
        and dispatch_block is not None
        and dispatch_launch_threads != dispatch_grid * dispatch_block
    ):
        failures.append(f"{prefix}_future_native_dispatch_launch_threads_mismatch")
    if (
        dispatch_grid is not None
        and dispatch_block is not None
        and dispatch_active_rows is not None
    ):
        launched_threads = dispatch_grid * dispatch_block
        previous_grid_threads = (dispatch_grid - 1) * dispatch_block
        if launched_threads < dispatch_active_rows:
            failures.append(
                f"{prefix}_future_native_dispatch_launch_under_covers_active_rows"
            )
        if previous_grid_threads >= dispatch_active_rows:
            failures.append(
                f"{prefix}_future_native_dispatch_launch_not_minimal_cover"
            )
        if dispatch_program_iteration_checked is not True:
            failures.append(
                f"{prefix}_future_native_dispatch_program_iteration_not_checked"
            )
        if dispatch_program_count != dispatch_grid:
            failures.append(f"{prefix}_future_native_dispatch_program_count_mismatch")
        if dispatch_rows_per_program != dispatch_block:
            failures.append(
                f"{prefix}_future_native_dispatch_rows_per_program_mismatch"
            )
        expected_full_program_count = dispatch_active_rows // dispatch_block
        expected_last_program_active_rows = (
            dispatch_active_rows - previous_grid_threads
        )
        expected_inactive_lane_count = launched_threads - dispatch_active_rows
        expected_first_program_row_offset = dispatch_offset
        expected_last_program_row_offset = (
            dispatch_offset + previous_grid_threads
            if dispatch_offset is not None
            else None
        )
        if dispatch_full_program_count != expected_full_program_count:
            failures.append(
                f"{prefix}_future_native_dispatch_full_program_count_mismatch"
            )
        if dispatch_last_program_active_rows != expected_last_program_active_rows:
            failures.append(
                f"{prefix}_future_native_dispatch_last_program_active_rows_mismatch"
            )
        if dispatch_inactive_lane_count != expected_inactive_lane_count:
            failures.append(
                f"{prefix}_future_native_dispatch_inactive_lane_count_mismatch"
            )
        if (
            dispatch_first_program_row_offset
            != expected_first_program_row_offset
        ):
            failures.append(
                f"{prefix}_future_native_dispatch_first_program_row_offset_mismatch"
            )
        if dispatch_last_program_row_offset != expected_last_program_row_offset:
            failures.append(
                f"{prefix}_future_native_dispatch_last_program_row_offset_mismatch"
            )
        if dispatch_row_assignment_formula != (
            "row_offset + program_id * rows_per_program + lane_id"
        ):
            failures.append(
                f"{prefix}_future_native_dispatch_row_assignment_formula_mismatch"
            )
        if dispatch_program_iteration_hash is None:
            failures.append(
                f"{prefix}_future_native_dispatch_program_iteration_hash_missing"
            )
        elif dispatch_offset is not None and dispatch_limit is not None:
            expected_program_iteration_hash = _program_iteration_hash(
                grid_x=dispatch_grid,
                block_x=dispatch_block,
                row_offset=dispatch_offset,
                row_limit=dispatch_limit,
                last_program_active_rows=expected_last_program_active_rows,
                inactive_lane_count=expected_inactive_lane_count,
            )
            if dispatch_program_iteration_hash != expected_program_iteration_hash:
                failures.append(
                    f"{prefix}_future_native_dispatch_program_iteration_hash_mismatch"
                )
    expected_dispatch_bools = {
        "future_kernel_native_dispatch_consumer_launch_geometry_checked": True,
        "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
        "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
    }
    for key, expected_value in expected_dispatch_bools.items():
        if stub.get(key) != expected_value:
            failures.append(f"{prefix}_{key}_mismatch")
    native_row_count = _int(stub.get("future_kernel_native_consumer_row_count"))
    native_row_ok_count = _int(
        stub.get("future_kernel_native_consumer_row_ok_count")
    )
    launch_row_count = _int(
        stub.get("future_kernel_native_launch_consumer_row_count")
    )
    launch_row_ok_count = _int(
        stub.get("future_kernel_native_launch_consumer_row_ok_count")
    )
    dispatch_row_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_row_count")
    )
    dispatch_row_ok_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_row_ok_count")
    )
    mirror_row_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_single_field_mirror_row_count")
    )
    mirror_row_ok_count = _int(
        stub.get("future_kernel_native_dispatch_consumer_single_field_mirror_row_ok_count")
    )
    for label, observed in (
        ("future_native", native_row_count),
        ("future_native_launch", launch_row_count),
    ):
        if row_count is not None and observed != row_count:
            failures.append(f"{prefix}_{label}_row_count_mismatch")
    for label, observed in (
        ("future_native", native_row_ok_count),
        ("future_native_launch", launch_row_ok_count),
    ):
        if row_count is not None and observed != row_count:
            failures.append(f"{prefix}_{label}_row_ok_count_mismatch")
    for label, observed in (
        ("future_native_dispatch", dispatch_row_count),
        ("future_native_dispatch_mirror", mirror_row_count),
    ):
        if expected_active_rows is not None and observed != expected_active_rows:
            failures.append(f"{prefix}_{label}_row_count_mismatch")
    for label, observed in (
        ("future_native_dispatch", dispatch_row_ok_count),
        ("future_native_dispatch_mirror", mirror_row_ok_count),
    ):
        if expected_active_rows is not None and observed != expected_active_rows:
            failures.append(f"{prefix}_{label}_row_ok_count_mismatch")
    return row_count, row_ok_count


def check_online_native_stub_canary_artifacts(
    *,
    root: Path,
    runner_json: Path = DEFAULT_RUNNER_JSON,
    preflight_json: Path = DEFAULT_PREFLIGHT_JSON,
    status_json: Path = DEFAULT_STATUS_JSON,
    require_all_field_mirror_stubs: bool = False,
    min_online_inputs: int = 1,
) -> dict[str, Any]:
    root = root.resolve()
    runner_path = _resolve(root, runner_json)
    preflight_path = _resolve(root, preflight_json)
    status_path = _resolve(root, status_json)
    failures: list[str] = []

    try:
        runner = _load_json(runner_path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "passed": False,
            "failures": [f"runner_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
            "preflight_json": str(preflight_path),
            "status_json": str(status_path),
        }
    try:
        preflight = _load_json(preflight_path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "passed": False,
            "failures": [f"preflight_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
            "preflight_json": str(preflight_path),
            "status_json": str(status_path),
        }
    try:
        status = _load_json(status_path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "passed": False,
            "failures": [f"status_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
            "preflight_json": str(preflight_path),
            "status_json": str(status_path),
        }

    if runner.get("passed") is not True:
        failures.append("runner_not_passed")
    if runner.get("failures") != []:
        failures.append("runner_failures_not_empty")
    if preflight.get("passed") is not True:
        failures.append("preflight_not_passed")
    if preflight.get("failures") != []:
        failures.append("preflight_failures_not_empty")
    if status.get("passed") is not True:
        failures.append("status_not_passed")

    observed_preflight = runner.get("preflight_output_json")
    if not isinstance(observed_preflight, str) or not observed_preflight:
        failures.append("runner_preflight_output_json_missing")
    elif _resolve(root, observed_preflight).resolve() != preflight_path.resolve():
        failures.append("runner_preflight_output_json_mismatch")

    observed_status = runner.get("preflight_status_output_json")
    if not isinstance(observed_status, str) or not observed_status:
        failures.append("runner_preflight_status_output_json_missing")
    elif _resolve(root, observed_status).resolve() != status_path.resolve():
        failures.append("runner_preflight_status_output_json_mismatch")

    stage1 = runner.get("preflight_status_summary")
    final = runner.get("final_preflight_status_summary")
    if not isinstance(stage1, dict):
        failures.append("runner_stage1_status_missing")
        stage1 = {}
    if not isinstance(final, dict):
        failures.append("runner_final_status_missing")
        final = {}

    status_required = status.get("required_evidence")
    if not isinstance(status_required, dict):
        failures.append("status_required_evidence_missing")
        status_required = {}
    status_optional = status.get("optional_evidence")
    if not isinstance(status_optional, dict):
        status_optional = {}
    status_required_evidence = status_required.get("evidence")
    if not isinstance(status_required_evidence, dict):
        status_required_evidence = {}
    status_optional_evidence = status_optional.get("evidence")
    if not isinstance(status_optional_evidence, dict):
        status_optional_evidence = {}

    def _deferred_evidence_count(rows: dict[str, object]) -> int:
        count = 0
        for row in rows.values():
            if not isinstance(row, dict):
                continue
            if (
                row.get("present") is False
                and row.get("passed") is False
                and row.get("failure") is None
            ):
                count += 1
        return count

    status_required_count = _int(status_required.get("required_count"))
    if status_required_count is None or status_required_count <= 0:
        failures.append("status_required_evidence_required_count_invalid")
        status_required_count = 0
    status_required_deferred_count = _deferred_evidence_count(
        status_required_evidence
    )
    status_required_present_count = max(
        int(status_required_count) - int(status_required_deferred_count),
        0,
    )
    stage1_deferred_count = _int(stage1.get("runtime_gate_evidence_deferred_count"))
    if stage1_deferred_count is None or stage1_deferred_count < 0:
        failures.append("runner_stage1_runtime_gate_evidence_deferred_count_invalid")
        stage1_deferred_count = 0
    stage1_required_count = _int(stage1.get("required_evidence_required_count"))
    stage1_present_count = _int(stage1.get("required_evidence_present_count"))
    stage1_passed_count = _int(stage1.get("required_evidence_passed_count"))
    if stage1_required_count != status_required_count:
        failures.append("runner_stage1_required_evidence_required_count_mismatch")
    if (
        stage1_present_count is None
        or stage1_present_count < 0
        or stage1_present_count > status_required_count
    ):
        failures.append("runner_stage1_required_evidence_present_count_invalid")
    if (
        stage1_passed_count is None
        or stage1_passed_count < 0
        or stage1_passed_count > status_required_count
    ):
        failures.append("runner_stage1_required_evidence_passed_count_invalid")
    if (
        stage1_present_count is not None
        and stage1_passed_count is not None
        and stage1_present_count != stage1_passed_count
    ):
        failures.append("runner_stage1_required_evidence_present_passed_mismatch")
    if (
        stage1_present_count is not None
        and stage1_present_count < max(status_required_count - stage1_deferred_count, 0)
    ):
        failures.append("runner_stage1_required_evidence_present_count_too_low")
    status_optional_count = _int(status_optional.get("required_count"))
    status_optional_deferred_count = 0
    if status_optional:
        status_optional_deferred_count = _deferred_evidence_count(
            status_optional_evidence
        )
    status_total_deferred_count = (
        int(status_required_deferred_count) + int(status_optional_deferred_count)
    )
    status_runtime_deferred_count = _int(
        status.get("runtime_gate_evidence_deferred_count")
    )
    if status_runtime_deferred_count is None or status_runtime_deferred_count < 0:
        failures.append("status_runtime_gate_evidence_deferred_count_invalid")
        status_runtime_deferred_count = status_total_deferred_count
    elif status_runtime_deferred_count < status_total_deferred_count:
        failures.append("status_runtime_gate_evidence_deferred_count_too_low")
    status_strict_deferred_count = _int(
        status.get("strict_default_gate_evidence_deferred_count")
    )
    if status_strict_deferred_count is None or status_strict_deferred_count < 0:
        failures.append("status_strict_default_gate_evidence_deferred_count_invalid")
        status_strict_deferred_count = status_runtime_deferred_count
    elif status_strict_deferred_count < status_total_deferred_count:
        failures.append("status_strict_default_gate_evidence_deferred_count_too_low")
    expected_stage1 = {
        "passed": True,
        "runtime_gate_evidence_deferred_count": stage1_deferred_count,
        "strict_default_gate_evidence_deferred_count": stage1_deferred_count,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    expected_final = {
        "passed": True,
        "required_evidence_present_count": status_required_present_count,
        "required_evidence_passed_count": status_required_present_count,
        "required_evidence_required_count": status_required_count,
        "runtime_gate_evidence_deferred_count": status_runtime_deferred_count,
        "strict_default_gate_evidence_deferred_count": status_strict_deferred_count,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    for key, expected in expected_stage1.items():
        if stage1.get(key) != expected:
            failures.append(f"runner_stage1_{key}_mismatch")
    for key, expected in expected_final.items():
        if final.get(key) != expected:
            failures.append(f"runner_final_{key}_mismatch")
    expected_status = {
        "passed": True,
        "runtime_gate_evidence_deferred_count": status_runtime_deferred_count,
        "strict_default_gate_evidence_deferred_count": status_strict_deferred_count,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    for key, expected in expected_status.items():
        if status.get(key) != expected:
            failures.append(f"status_{key}_mismatch")
    expected_required = {
        "present_count": status_required_present_count,
        "passed_count": status_required_present_count,
        "required_count": status_required_count,
        "passed": True,
    }
    for key, expected in expected_required.items():
        if status_required.get(key) != expected:
            failures.append(f"status_required_evidence_{key}_mismatch")
    if status_optional:
        if status_optional_count is None or status_optional_count < 0:
            failures.append("status_optional_evidence_required_count_invalid")
            status_optional_count = 0
        status_optional_present_count = max(
            int(status_optional_count) - int(status_optional_deferred_count),
            0,
        )
        expected_optional = {
            "present_count": status_optional_present_count,
            "passed_count": status_optional_present_count,
            "required_count": status_optional_count,
            "passed": True,
        }
        for key, expected in expected_optional.items():
            if status_optional.get(key) != expected:
                failures.append(f"status_optional_evidence_{key}_mismatch")
        stage1_optional_count = _int(stage1.get("optional_evidence_required_count"))
        stage1_optional_present_count = _int(
            stage1.get("optional_evidence_present_count")
        )
        stage1_optional_passed_count = _int(
            stage1.get("optional_evidence_passed_count")
        )
        if stage1_optional_count != status_optional_count:
            failures.append("runner_stage1_optional_evidence_required_count_mismatch")
        if (
            stage1_optional_present_count is None
            or stage1_optional_present_count < 0
            or stage1_optional_present_count > int(status_optional_count)
        ):
            failures.append("runner_stage1_optional_evidence_present_count_invalid")
        if (
            stage1_optional_passed_count is None
            or stage1_optional_passed_count < 0
            or stage1_optional_passed_count > int(status_optional_count)
        ):
            failures.append("runner_stage1_optional_evidence_passed_count_invalid")
        if (
            stage1_optional_present_count is not None
            and stage1_optional_passed_count is not None
            and stage1_optional_present_count != stage1_optional_passed_count
        ):
            failures.append("runner_stage1_optional_evidence_present_passed_mismatch")
        if stage1.get("optional_evidence_passed") is not True:
            failures.append("runner_stage1_optional_evidence_passed_mismatch")
        if (
            stage1_present_count is not None
            and stage1_optional_present_count is not None
        ):
            stage1_expected_deferred_count = (
                max(int(status_required_count) - int(stage1_present_count), 0)
                + max(int(status_optional_count) - int(stage1_optional_present_count), 0)
            )
            if stage1_deferred_count < stage1_expected_deferred_count:
                failures.append(
                    "runner_stage1_runtime_gate_evidence_deferred_count_too_low"
                )
        for key, expected in {
            "optional_evidence_present_count": status_optional_present_count,
            "optional_evidence_passed_count": status_optional_present_count,
            "optional_evidence_required_count": status_optional_count,
            "optional_evidence_passed": True,
        }.items():
            if final.get(key) != expected:
                failures.append(f"runner_final_{key}_mismatch")

    row_count, row_ok_count = _check_stub_summary(
        runner.get("stub_summary"),
        prefix="runner_stub",
        failures=failures,
        require_kernel_side_consumer_path=True,
    )
    per_field_stub = runner.get("per_field_stub_summary")
    per_field_row_count: int | None = None
    per_field_row_ok_count: int | None = None
    if per_field_stub is not None:
        per_field_row_count, per_field_row_ok_count = _check_stub_summary(
            per_field_stub,
            prefix="runner_per_field_stub",
            failures=failures,
        )
    envelope_mirror_row_count: int | None = None
    envelope_mirror_row_ok_count: int | None = None
    envelope_mirror_stub = runner.get("kernel_envelope_mirror_stub_summary")
    if require_all_field_mirror_stubs and envelope_mirror_stub is None:
        failures.append("runner_kernel_envelope_mirror_stub_summary_required")
    if envelope_mirror_stub is not None:
        envelope_mirror_row_count, envelope_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                envelope_mirror_stub,
                prefix="runner_kernel_envelope_mirror_stub",
                expected_field_name="scale_metadata_handle",
                failures=failures,
                require_envelope=True,
            )
        )
    packed_weight_mirror_row_count: int | None = None
    packed_weight_mirror_row_ok_count: int | None = None
    packed_weight_mirror_stub = runner.get("packed_weight_mirror_stub_summary")
    if require_all_field_mirror_stubs and packed_weight_mirror_stub is None:
        failures.append("runner_packed_weight_mirror_stub_summary_required")
    if packed_weight_mirror_stub is not None:
        packed_weight_mirror_row_count, packed_weight_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                packed_weight_mirror_stub,
                prefix="runner_packed_weight_mirror_stub",
                expected_field_name="packed_weight_descriptor",
                failures=failures,
            )
        )
    aux_metadata_mirror_row_count: int | None = None
    aux_metadata_mirror_row_ok_count: int | None = None
    aux_metadata_mirror_stub = runner.get("aux_metadata_mirror_stub_summary")
    if require_all_field_mirror_stubs and aux_metadata_mirror_stub is None:
        failures.append("runner_aux_metadata_mirror_stub_summary_required")
    if aux_metadata_mirror_stub is not None:
        aux_metadata_mirror_row_count, aux_metadata_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                aux_metadata_mirror_stub,
                prefix="runner_aux_metadata_mirror_stub",
                expected_field_name="aux_metadata_handle",
                failures=failures,
            )
        )
    descriptor_ptr_mirror_row_count: int | None = None
    descriptor_ptr_mirror_row_ok_count: int | None = None
    descriptor_ptr_mirror_stub = runner.get("descriptor_ptr_mirror_stub_summary")
    if require_all_field_mirror_stubs and descriptor_ptr_mirror_stub is None:
        failures.append("runner_descriptor_ptr_mirror_stub_summary_required")
    if descriptor_ptr_mirror_stub is not None:
        descriptor_ptr_mirror_row_count, descriptor_ptr_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                descriptor_ptr_mirror_stub,
                prefix="runner_descriptor_ptr_mirror_stub",
                expected_field_name="descriptor_ptr",
                failures=failures,
            )
        )
    kernel_side_compatible_row_count: int | None = None
    kernel_side_compatible_row_ok_count: int | None = None
    kernel_side_compatible_stub = runner.get("kernel_side_compatible_stub_summary")
    if require_all_field_mirror_stubs and kernel_side_compatible_stub is None:
        failures.append("runner_kernel_side_compatible_stub_summary_required")
    if kernel_side_compatible_stub is not None:
        (
            kernel_side_compatible_row_count,
            kernel_side_compatible_row_ok_count,
        ) = _check_kernel_side_compatible_summary(
            kernel_side_compatible_stub,
            prefix="runner_kernel_side_compatible_stub",
            failures=failures,
        )
    future_kernel_args_row_count: int | None = None
    future_kernel_args_row_ok_count: int | None = None
    future_kernel_args_stub = runner.get("future_kernel_args_stub_summary")
    if require_all_field_mirror_stubs and future_kernel_args_stub is None:
        failures.append("runner_future_kernel_args_stub_summary_required")
    if future_kernel_args_stub is not None:
        future_kernel_args_row_count, future_kernel_args_row_ok_count = (
            _check_future_kernel_args_summary(
                future_kernel_args_stub,
                prefix="runner_future_kernel_args_stub",
                failures=failures,
            )
        )
    future_kernel_args_descriptor_ptr_row_count: int | None = None
    future_kernel_args_descriptor_ptr_row_ok_count: int | None = None
    future_kernel_args_descriptor_ptr_stub = runner.get(
        "future_kernel_args_descriptor_ptr_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_args_descriptor_ptr_stub is None:
        failures.append("runner_future_kernel_args_descriptor_ptr_stub_summary_required")
    if future_kernel_args_descriptor_ptr_stub is not None:
        (
            future_kernel_args_descriptor_ptr_row_count,
            future_kernel_args_descriptor_ptr_row_ok_count,
        ) = _check_future_kernel_args_summary(
            future_kernel_args_descriptor_ptr_stub,
            prefix="runner_future_kernel_args_descriptor_ptr_stub",
            expected_field_name="descriptor_ptr",
            failures=failures,
        )
    future_kernel_args_packed_weight_row_count: int | None = None
    future_kernel_args_packed_weight_row_ok_count: int | None = None
    future_kernel_args_packed_weight_stub = runner.get(
        "future_kernel_args_packed_weight_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_args_packed_weight_stub is None:
        failures.append("runner_future_kernel_args_packed_weight_stub_summary_required")
    if future_kernel_args_packed_weight_stub is not None:
        (
            future_kernel_args_packed_weight_row_count,
            future_kernel_args_packed_weight_row_ok_count,
        ) = _check_future_kernel_args_summary(
            future_kernel_args_packed_weight_stub,
            prefix="runner_future_kernel_args_packed_weight_stub",
            expected_field_name="packed_weight_descriptor",
            failures=failures,
        )
    future_kernel_args_aux_metadata_row_count: int | None = None
    future_kernel_args_aux_metadata_row_ok_count: int | None = None
    future_kernel_args_aux_metadata_stub = runner.get(
        "future_kernel_args_aux_metadata_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_args_aux_metadata_stub is None:
        failures.append("runner_future_kernel_args_aux_metadata_stub_summary_required")
    if future_kernel_args_aux_metadata_stub is not None:
        (
            future_kernel_args_aux_metadata_row_count,
            future_kernel_args_aux_metadata_row_ok_count,
        ) = _check_future_kernel_args_summary(
            future_kernel_args_aux_metadata_stub,
            prefix="runner_future_kernel_args_aux_metadata_stub",
            expected_field_name="aux_metadata_handle",
            failures=failures,
        )
    future_kernel_args_compatible_path_row_count: int | None = None
    future_kernel_args_compatible_path_row_ok_count: int | None = None
    future_kernel_args_compatible_path_stub = runner.get(
        "future_kernel_args_compatible_path_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_args_compatible_path_stub is None:
        failures.append(
            "runner_future_kernel_args_compatible_path_stub_summary_required"
        )
    if future_kernel_args_compatible_path_stub is not None:
        (
            future_kernel_args_compatible_path_row_count,
            future_kernel_args_compatible_path_row_ok_count,
        ) = _check_future_kernel_args_compatible_path_summary(
            future_kernel_args_compatible_path_stub,
            prefix="runner_future_kernel_args_compatible_path_stub",
            failures=failures,
        )
    future_kernel_native_consumer_row_count: int | None = None
    future_kernel_native_consumer_row_ok_count: int | None = None
    future_kernel_native_consumer_stub = runner.get(
        "future_kernel_native_consumer_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_native_consumer_stub is None:
        failures.append("runner_future_kernel_native_consumer_stub_summary_required")
    if future_kernel_native_consumer_stub is not None:
        (
            future_kernel_native_consumer_row_count,
            future_kernel_native_consumer_row_ok_count,
        ) = _check_future_kernel_native_consumer_summary(
            future_kernel_native_consumer_stub,
            prefix="runner_future_kernel_native_consumer_stub",
            failures=failures,
        )
    future_kernel_native_consumer_descriptor_ptr_row_count: int | None = None
    future_kernel_native_consumer_descriptor_ptr_row_ok_count: int | None = None
    future_kernel_native_consumer_descriptor_ptr_stub = runner.get(
        "future_kernel_native_consumer_descriptor_ptr_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_descriptor_ptr_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_descriptor_ptr_stub_summary_required"
        )
    if future_kernel_native_consumer_descriptor_ptr_stub is not None:
        (
            future_kernel_native_consumer_descriptor_ptr_row_count,
            future_kernel_native_consumer_descriptor_ptr_row_ok_count,
        ) = _check_future_kernel_native_consumer_summary(
            future_kernel_native_consumer_descriptor_ptr_stub,
            prefix="runner_future_kernel_native_consumer_descriptor_ptr_stub",
            expected_field_name="descriptor_ptr",
            failures=failures,
        )
    future_kernel_native_consumer_packed_weight_row_count: int | None = None
    future_kernel_native_consumer_packed_weight_row_ok_count: int | None = None
    future_kernel_native_consumer_packed_weight_stub = runner.get(
        "future_kernel_native_consumer_packed_weight_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_packed_weight_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_packed_weight_stub_summary_required"
        )
    if future_kernel_native_consumer_packed_weight_stub is not None:
        (
            future_kernel_native_consumer_packed_weight_row_count,
            future_kernel_native_consumer_packed_weight_row_ok_count,
        ) = _check_future_kernel_native_consumer_summary(
            future_kernel_native_consumer_packed_weight_stub,
            prefix="runner_future_kernel_native_consumer_packed_weight_stub",
            expected_field_name="packed_weight_descriptor",
            failures=failures,
        )
    future_kernel_native_consumer_aux_metadata_row_count: int | None = None
    future_kernel_native_consumer_aux_metadata_row_ok_count: int | None = None
    future_kernel_native_consumer_aux_metadata_stub = runner.get(
        "future_kernel_native_consumer_aux_metadata_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_aux_metadata_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_aux_metadata_stub_summary_required"
        )
    if future_kernel_native_consumer_aux_metadata_stub is not None:
        (
            future_kernel_native_consumer_aux_metadata_row_count,
            future_kernel_native_consumer_aux_metadata_row_ok_count,
        ) = _check_future_kernel_native_consumer_summary(
            future_kernel_native_consumer_aux_metadata_stub,
            prefix="runner_future_kernel_native_consumer_aux_metadata_stub",
            expected_field_name="aux_metadata_handle",
            failures=failures,
        )
    future_kernel_native_consumer_launch_row_count: int | None = None
    future_kernel_native_consumer_launch_row_ok_count: int | None = None
    future_kernel_native_consumer_launch_stub = runner.get(
        "future_kernel_native_consumer_launch_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_native_consumer_launch_stub is None:
        failures.append(
            "runner_future_kernel_native_consumer_launch_stub_summary_required"
        )
    if future_kernel_native_consumer_launch_stub is not None:
        (
            future_kernel_native_consumer_launch_row_count,
            future_kernel_native_consumer_launch_row_ok_count,
        ) = _check_future_kernel_native_launch_consumer_summary(
            future_kernel_native_consumer_launch_stub,
            prefix="runner_future_kernel_native_consumer_launch_stub",
            failures=failures,
        )
    future_kernel_native_consumer_launch_descriptor_ptr_row_count: int | None = None
    future_kernel_native_consumer_launch_descriptor_ptr_row_ok_count: int | None = None
    future_kernel_native_consumer_launch_descriptor_ptr_stub = runner.get(
        "future_kernel_native_consumer_launch_descriptor_ptr_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_launch_descriptor_ptr_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_summary_required"
        )
    if future_kernel_native_consumer_launch_descriptor_ptr_stub is not None:
        (
            future_kernel_native_consumer_launch_descriptor_ptr_row_count,
            future_kernel_native_consumer_launch_descriptor_ptr_row_ok_count,
        ) = _check_future_kernel_native_launch_consumer_summary(
            future_kernel_native_consumer_launch_descriptor_ptr_stub,
            prefix="runner_future_kernel_native_consumer_launch_descriptor_ptr_stub",
            expected_field_name="descriptor_ptr",
            failures=failures,
        )
    future_kernel_native_consumer_launch_packed_weight_row_count: int | None = None
    future_kernel_native_consumer_launch_packed_weight_row_ok_count: int | None = None
    future_kernel_native_consumer_launch_packed_weight_stub = runner.get(
        "future_kernel_native_consumer_launch_packed_weight_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_launch_packed_weight_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_launch_packed_weight_stub_summary_required"
        )
    if future_kernel_native_consumer_launch_packed_weight_stub is not None:
        (
            future_kernel_native_consumer_launch_packed_weight_row_count,
            future_kernel_native_consumer_launch_packed_weight_row_ok_count,
        ) = _check_future_kernel_native_launch_consumer_summary(
            future_kernel_native_consumer_launch_packed_weight_stub,
            prefix="runner_future_kernel_native_consumer_launch_packed_weight_stub",
            expected_field_name="packed_weight_descriptor",
            failures=failures,
        )
    future_kernel_native_consumer_launch_aux_metadata_row_count: int | None = None
    future_kernel_native_consumer_launch_aux_metadata_row_ok_count: int | None = None
    future_kernel_native_consumer_launch_aux_metadata_stub = runner.get(
        "future_kernel_native_consumer_launch_aux_metadata_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_launch_aux_metadata_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_launch_aux_metadata_stub_summary_required"
        )
    if future_kernel_native_consumer_launch_aux_metadata_stub is not None:
        (
            future_kernel_native_consumer_launch_aux_metadata_row_count,
            future_kernel_native_consumer_launch_aux_metadata_row_ok_count,
        ) = _check_future_kernel_native_launch_consumer_summary(
            future_kernel_native_consumer_launch_aux_metadata_stub,
            prefix="runner_future_kernel_native_consumer_launch_aux_metadata_stub",
            expected_field_name="aux_metadata_handle",
            failures=failures,
        )
    future_kernel_native_consumer_dispatch_row_count: int | None = None
    future_kernel_native_consumer_dispatch_row_ok_count: int | None = None
    future_kernel_native_consumer_dispatch_stub = runner.get(
        "future_kernel_native_consumer_dispatch_stub_summary"
    )
    if require_all_field_mirror_stubs and future_kernel_native_consumer_dispatch_stub is None:
        failures.append(
            "runner_future_kernel_native_consumer_dispatch_stub_summary_required"
        )
    if future_kernel_native_consumer_dispatch_stub is not None:
        (
            future_kernel_native_consumer_dispatch_row_count,
            future_kernel_native_consumer_dispatch_row_ok_count,
        ) = _check_future_kernel_native_dispatch_consumer_summary(
            future_kernel_native_consumer_dispatch_stub,
            prefix="runner_future_kernel_native_consumer_dispatch_stub",
            failures=failures,
        )
    future_kernel_native_consumer_dispatch_descriptor_ptr_row_count: int | None = None
    future_kernel_native_consumer_dispatch_descriptor_ptr_row_ok_count: int | None = None
    future_kernel_native_consumer_dispatch_descriptor_ptr_stub = runner.get(
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_dispatch_descriptor_ptr_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary_required"
        )
    if future_kernel_native_consumer_dispatch_descriptor_ptr_stub is not None:
        (
            future_kernel_native_consumer_dispatch_descriptor_ptr_row_count,
            future_kernel_native_consumer_dispatch_descriptor_ptr_row_ok_count,
        ) = _check_future_kernel_native_dispatch_consumer_summary(
            future_kernel_native_consumer_dispatch_descriptor_ptr_stub,
            prefix="runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub",
            expected_field_name="descriptor_ptr",
            failures=failures,
        )
    future_kernel_native_consumer_dispatch_packed_weight_row_count: int | None = None
    future_kernel_native_consumer_dispatch_packed_weight_row_ok_count: int | None = None
    future_kernel_native_consumer_dispatch_packed_weight_stub = runner.get(
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_dispatch_packed_weight_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_summary_required"
        )
    if future_kernel_native_consumer_dispatch_packed_weight_stub is not None:
        (
            future_kernel_native_consumer_dispatch_packed_weight_row_count,
            future_kernel_native_consumer_dispatch_packed_weight_row_ok_count,
        ) = _check_future_kernel_native_dispatch_consumer_summary(
            future_kernel_native_consumer_dispatch_packed_weight_stub,
            prefix="runner_future_kernel_native_consumer_dispatch_packed_weight_stub",
            expected_field_name="packed_weight_descriptor",
            failures=failures,
        )
    future_kernel_native_consumer_dispatch_aux_metadata_row_count: int | None = None
    future_kernel_native_consumer_dispatch_aux_metadata_row_ok_count: int | None = None
    future_kernel_native_consumer_dispatch_aux_metadata_stub = runner.get(
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary"
    )
    if (
        require_all_field_mirror_stubs
        and future_kernel_native_consumer_dispatch_aux_metadata_stub is None
    ):
        failures.append(
            "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_summary_required"
        )
    if future_kernel_native_consumer_dispatch_aux_metadata_stub is not None:
        (
            future_kernel_native_consumer_dispatch_aux_metadata_row_count,
            future_kernel_native_consumer_dispatch_aux_metadata_row_ok_count,
        ) = _check_future_kernel_native_dispatch_consumer_summary(
            future_kernel_native_consumer_dispatch_aux_metadata_stub,
            prefix="runner_future_kernel_native_consumer_dispatch_aux_metadata_stub",
            expected_field_name="aux_metadata_handle",
            failures=failures,
        )

    online_input_check_count = _int(runner.get("online_prelaunch_input_check_count"))
    if online_input_check_count is None:
        failures.append("runner_online_prelaunch_input_check_count_missing")
        online_input_check_count = 0
    if online_input_check_count < int(min_online_inputs):
        failures.append("runner_online_prelaunch_input_check_count_below_min")
    extra_input_check_count = _int(
        runner.get("online_prelaunch_input_extra_check_count")
    )
    extra_input_check_passed_count = _int(
        runner.get("online_prelaunch_input_extra_check_passed_count")
    )
    if online_input_check_count > 1:
        expected_extra = online_input_check_count - 1
        if extra_input_check_count != expected_extra:
            failures.append("runner_online_prelaunch_input_extra_check_count_mismatch")
        if extra_input_check_passed_count != expected_extra:
            failures.append(
                "runner_online_prelaunch_input_extra_check_passed_count_mismatch"
            )
        extra_summaries = runner.get("extra_online_input_check_summaries")
        if not isinstance(extra_summaries, list):
            failures.append("runner_extra_online_input_check_summaries_missing")
            extra_summaries = []
        elif len(extra_summaries) != expected_extra:
            failures.append("runner_extra_online_input_check_summaries_count_mismatch")
        expected_labels: dict[str, tuple[str | None, bool]] = {
            "native_stub": (None, False),
            "native_stub_per_field": (None, False),
        }
        if require_all_field_mirror_stubs:
            expected_labels.update(
                {
                    "native_stub_kernel_envelope_mirror": (
                        "scale_metadata_handle",
                        True,
                    ),
                    "native_stub_packed_weight_mirror": (
                        "packed_weight_descriptor",
                        False,
                    ),
                    "native_stub_aux_metadata_mirror": ("aux_metadata_handle", False),
                    "native_stub_descriptor_ptr_mirror": ("descriptor_ptr", False),
                    "native_stub_kernel_side_compatible_consumer_abi": (
                        "kernel_side_compatible_consumer_abi",
                        False,
                    ),
                    "native_stub_future_kernel_consumer_args": (
                        "future_kernel_consumer_args:scale_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_args_descriptor_ptr_mirror": (
                        "future_kernel_consumer_args:descriptor_ptr",
                        False,
                    ),
                    "native_stub_future_kernel_args_packed_weight_mirror": (
                        "future_kernel_consumer_args:packed_weight_descriptor",
                        False,
                    ),
                    "native_stub_future_kernel_args_aux_metadata_mirror": (
                        "future_kernel_consumer_args:aux_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_args_compatible_consumer_path": (
                        "future_kernel_args_compatible_consumer_path",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_abi": (
                        "future_kernel_native_consumer:scale_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_descriptor_ptr_mirror": (
                        "future_kernel_native_consumer:descriptor_ptr",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_packed_weight_mirror": (
                        "future_kernel_native_consumer:packed_weight_descriptor",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_aux_metadata_mirror": (
                        "future_kernel_native_consumer:aux_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_launch_abi": (
                        "future_kernel_native_launch_consumer:scale_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_launch_descriptor_ptr_mirror": (
                        "future_kernel_native_launch_consumer:descriptor_ptr",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_launch_packed_weight_mirror": (
                        "future_kernel_native_launch_consumer:packed_weight_descriptor",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_launch_aux_metadata_mirror": (
                        "future_kernel_native_launch_consumer:aux_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_dispatch_abi": (
                        "future_kernel_native_dispatch_consumer:scale_metadata_handle",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror": (
                        "future_kernel_native_dispatch_consumer:descriptor_ptr",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror": (
                        "future_kernel_native_dispatch_consumer:packed_weight_descriptor",
                        False,
                    ),
                    "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror": (
                        "future_kernel_native_dispatch_consumer:aux_metadata_handle",
                        False,
                    ),
                }
            )
        for index, suite in enumerate(extra_summaries[:expected_extra], start=1):
            prefix = f"runner_extra_input_{index:04d}"
            if not isinstance(suite, dict):
                failures.append(f"{prefix}_summary_invalid")
                continue
            if suite.get("passed") is not True:
                failures.append(f"{prefix}_not_passed")
            if suite.get("failures") != []:
                failures.append(f"{prefix}_failures_not_empty")
            outputs = suite.get("outputs")
            if not isinstance(outputs, dict):
                failures.append(f"{prefix}_outputs_missing")
                outputs = {}
            for label, (expected_field, require_envelope) in expected_labels.items():
                entry = outputs.get(label)
                label_prefix = f"{prefix}_{label}"
                if not isinstance(entry, dict):
                    failures.append(f"{label_prefix}_missing")
                    continue
                summary = entry.get("summary")
                if expected_field is None:
                    _check_stub_summary(
                        summary,
                        prefix=label_prefix,
                        failures=failures,
                        require_kernel_side_consumer_path=(label == "native_stub"),
                    )
                elif expected_field == "kernel_side_compatible_consumer_abi":
                    _check_kernel_side_compatible_summary(
                        summary,
                        prefix=label_prefix,
                        failures=failures,
                    )
                elif expected_field.startswith("future_kernel_consumer_args:"):
                    _, future_expected_field = expected_field.split(":", 1)
                    _check_future_kernel_args_summary(
                        summary,
                        prefix=label_prefix,
                        expected_field_name=future_expected_field,
                        failures=failures,
                    )
                elif expected_field == "future_kernel_args_compatible_consumer_path":
                    _check_future_kernel_args_compatible_path_summary(
                        summary,
                        prefix=label_prefix,
                        failures=failures,
                    )
                elif expected_field.startswith("future_kernel_native_consumer:"):
                    _, native_expected_field = expected_field.split(":", 1)
                    _check_future_kernel_native_consumer_summary(
                        summary,
                        prefix=label_prefix,
                        expected_field_name=native_expected_field,
                        failures=failures,
                    )
                elif expected_field.startswith("future_kernel_native_launch_consumer:"):
                    _, launch_expected_field = expected_field.split(":", 1)
                    _check_future_kernel_native_launch_consumer_summary(
                        summary,
                        prefix=label_prefix,
                        expected_field_name=launch_expected_field,
                        failures=failures,
                    )
                elif expected_field.startswith("future_kernel_native_dispatch_consumer:"):
                    _, dispatch_expected_field = expected_field.split(":", 1)
                    _check_future_kernel_native_dispatch_consumer_summary(
                        summary,
                        prefix=label_prefix,
                        expected_field_name=dispatch_expected_field,
                        failures=failures,
                    )
                else:
                    _check_single_field_mirror_summary(
                        summary,
                        prefix=label_prefix,
                        expected_field_name=expected_field,
                        failures=failures,
                        require_envelope=require_envelope,
                    )

    return {
        "passed": not failures,
        "failures": failures,
        "runner_json": str(runner_path),
        "preflight_json": str(preflight_path),
        "status_json": str(status_path),
        "runner_preflight_output_json": observed_preflight,
        "runner_preflight_status_output_json": observed_status,
        "runner_stub_row_count": row_count,
        "runner_stub_row_ok_count": row_ok_count,
        "runner_stub_kernel_side_consumer_path_checked": (
            bool(runner.get("stub_summary", {}).get("kernel_side_consumer_path_checked"))
            if isinstance(runner.get("stub_summary"), dict)
            else False
        ),
        "runner_per_field_stub_row_count": per_field_row_count,
        "runner_per_field_stub_row_ok_count": per_field_row_ok_count,
        "runner_kernel_envelope_mirror_stub_row_count": envelope_mirror_row_count,
        "runner_kernel_envelope_mirror_stub_row_ok_count": (
            envelope_mirror_row_ok_count
        ),
        "runner_packed_weight_mirror_stub_row_count": packed_weight_mirror_row_count,
        "runner_packed_weight_mirror_stub_row_ok_count": (
            packed_weight_mirror_row_ok_count
        ),
        "runner_aux_metadata_mirror_stub_row_count": aux_metadata_mirror_row_count,
        "runner_aux_metadata_mirror_stub_row_ok_count": (
            aux_metadata_mirror_row_ok_count
        ),
        "runner_descriptor_ptr_mirror_stub_row_count": descriptor_ptr_mirror_row_count,
        "runner_descriptor_ptr_mirror_stub_row_ok_count": (
            descriptor_ptr_mirror_row_ok_count
        ),
        "runner_kernel_side_compatible_stub_row_count": (
            kernel_side_compatible_row_count
        ),
        "runner_kernel_side_compatible_stub_row_ok_count": (
            kernel_side_compatible_row_ok_count
        ),
        "runner_future_kernel_args_stub_row_count": future_kernel_args_row_count,
        "runner_future_kernel_args_stub_row_ok_count": (
            future_kernel_args_row_ok_count
        ),
        "runner_future_kernel_args_descriptor_ptr_stub_row_count": (
            future_kernel_args_descriptor_ptr_row_count
        ),
        "runner_future_kernel_args_descriptor_ptr_stub_row_ok_count": (
            future_kernel_args_descriptor_ptr_row_ok_count
        ),
        "runner_future_kernel_args_packed_weight_stub_row_count": (
            future_kernel_args_packed_weight_row_count
        ),
        "runner_future_kernel_args_packed_weight_stub_row_ok_count": (
            future_kernel_args_packed_weight_row_ok_count
        ),
        "runner_future_kernel_args_aux_metadata_stub_row_count": (
            future_kernel_args_aux_metadata_row_count
        ),
        "runner_future_kernel_args_aux_metadata_stub_row_ok_count": (
            future_kernel_args_aux_metadata_row_ok_count
        ),
        "runner_future_kernel_args_compatible_path_stub_row_count": (
            future_kernel_args_compatible_path_row_count
        ),
        "runner_future_kernel_args_compatible_path_stub_row_ok_count": (
            future_kernel_args_compatible_path_row_ok_count
        ),
        "runner_future_kernel_native_consumer_stub_row_count": (
            future_kernel_native_consumer_row_count
        ),
        "runner_future_kernel_native_consumer_stub_row_ok_count": (
            future_kernel_native_consumer_row_ok_count
        ),
        "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_count": (
            future_kernel_native_consumer_descriptor_ptr_row_count
        ),
        "runner_future_kernel_native_consumer_descriptor_ptr_stub_row_ok_count": (
            future_kernel_native_consumer_descriptor_ptr_row_ok_count
        ),
        "runner_future_kernel_native_consumer_packed_weight_stub_row_count": (
            future_kernel_native_consumer_packed_weight_row_count
        ),
        "runner_future_kernel_native_consumer_packed_weight_stub_row_ok_count": (
            future_kernel_native_consumer_packed_weight_row_ok_count
        ),
        "runner_future_kernel_native_consumer_aux_metadata_stub_row_count": (
            future_kernel_native_consumer_aux_metadata_row_count
        ),
        "runner_future_kernel_native_consumer_aux_metadata_stub_row_ok_count": (
            future_kernel_native_consumer_aux_metadata_row_ok_count
        ),
        "runner_future_kernel_native_consumer_launch_stub_row_count": (
            future_kernel_native_consumer_launch_row_count
        ),
        "runner_future_kernel_native_consumer_launch_stub_row_ok_count": (
            future_kernel_native_consumer_launch_row_ok_count
        ),
        "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_count": (
            future_kernel_native_consumer_launch_descriptor_ptr_row_count
        ),
        "runner_future_kernel_native_consumer_launch_descriptor_ptr_stub_row_ok_count": (
            future_kernel_native_consumer_launch_descriptor_ptr_row_ok_count
        ),
        "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_count": (
            future_kernel_native_consumer_launch_packed_weight_row_count
        ),
        "runner_future_kernel_native_consumer_launch_packed_weight_stub_row_ok_count": (
            future_kernel_native_consumer_launch_packed_weight_row_ok_count
        ),
        "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_count": (
            future_kernel_native_consumer_launch_aux_metadata_row_count
        ),
        "runner_future_kernel_native_consumer_launch_aux_metadata_stub_row_ok_count": (
            future_kernel_native_consumer_launch_aux_metadata_row_ok_count
        ),
        "runner_future_kernel_native_consumer_dispatch_stub_row_count": (
            future_kernel_native_consumer_dispatch_row_count
        ),
        "runner_future_kernel_native_consumer_dispatch_stub_row_ok_count": (
            future_kernel_native_consumer_dispatch_row_ok_count
        ),
        "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_count": (
            future_kernel_native_consumer_dispatch_descriptor_ptr_row_count
        ),
        "runner_future_kernel_native_consumer_dispatch_descriptor_ptr_stub_row_ok_count": (
            future_kernel_native_consumer_dispatch_descriptor_ptr_row_ok_count
        ),
        "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_count": (
            future_kernel_native_consumer_dispatch_packed_weight_row_count
        ),
        "runner_future_kernel_native_consumer_dispatch_packed_weight_stub_row_ok_count": (
            future_kernel_native_consumer_dispatch_packed_weight_row_ok_count
        ),
        "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_count": (
            future_kernel_native_consumer_dispatch_aux_metadata_row_count
        ),
        "runner_future_kernel_native_consumer_dispatch_aux_metadata_stub_row_ok_count": (
            future_kernel_native_consumer_dispatch_aux_metadata_row_ok_count
        ),
        "require_all_field_mirror_stubs": bool(require_all_field_mirror_stubs),
        "min_online_inputs": int(min_online_inputs),
        "runner_online_prelaunch_input_check_count": online_input_check_count,
        "runner_online_prelaunch_input_extra_check_count": extra_input_check_count,
        "runner_online_prelaunch_input_extra_check_passed_count": (
            extra_input_check_passed_count
        ),
        "stage1_deferred_count": stage1.get("runtime_gate_evidence_deferred_count"),
        "final_deferred_count": final.get("runtime_gate_evidence_deferred_count"),
        "status_deferred_count": status.get("runtime_gate_evidence_deferred_count"),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--runner-json", type=Path, default=DEFAULT_RUNNER_JSON)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT_JSON)
    parser.add_argument("--status-json", type=Path, default=DEFAULT_STATUS_JSON)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--require-all-field-mirror-stubs", action="store_true")
    parser.add_argument("--min-online-inputs", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_online_native_stub_canary_artifacts(
        root=args.root,
        runner_json=args.runner_json,
        preflight_json=args.preflight_json,
        status_json=args.status_json,
        require_all_field_mirror_stubs=args.require_all_field_mirror_stubs,
        min_online_inputs=int(args.min_online_inputs),
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
