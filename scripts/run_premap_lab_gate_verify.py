#!/usr/bin/env python3
"""Run and statically verify the canonical premap lab gate closures.

This helper is still read-only with respect to the real vLLM/WNA16 path.  It
refreshes the default full-table closure, refreshes the optional tail-window
closure, refreshes the online-merged row-window sweep, and then checks all
artifacts with static checkers.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CLOSURE_JSON = REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_closure.json"
DEFAULT_CLOSURE_CHECK_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_closure.check.json"
)
DEFAULT_TAIL_CLOSURE_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_closure_tail_window512.json"
)
DEFAULT_TAIL_CLOSURE_CHECK_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_closure_tail_window512.check.json"
)
DEFAULT_WINDOW_SWEEP_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_window_sweep_runner.json"
)
DEFAULT_WINDOW_SWEEP_CHECK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_window_sweep_check.json"
)
DEFAULT_ALL_FIELD_WINDOW_SWEEP_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_all_field_window_sweep_runner.json"
)
DEFAULT_ALL_FIELD_WINDOW_SWEEP_CHECK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_all_field_window_sweep_check.json"
)
DEFAULT_WNA16_SIDE_VARIANT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_wna16_side_consumer_variant_execution_lab_gate_runner.json"
)
DEFAULT_WNA16_SIDE_VARIANT_STUB_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_merged_wna16_side_consumer_variant_execution_lab_gate.json"
)
DEFAULT_WNA16_SIDE_VARIANT_MERGED_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_prelaunch_typed_consumer_input_wna16_side_consumer_variant_execution_lab_gate.json"
)
DEFAULT_VERIFY_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_verify.json"
)
WNA16_SIDE_VARIANT_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
WNA16_SIDE_VARIANT_HASH_FIELDS = (
    "hash_accumulator",
    "handle_projection_hash_accumulator",
    "descriptor_ptr_read_hash_accumulator",
    "packed_weight_descriptor_read_hash_accumulator",
    "scale_metadata_handle_read_hash_accumulator",
    "aux_metadata_handle_read_hash_accumulator",
)

ARG_SLOT_INVOCATION_STATUS_FIELDS = (
    "require_kernel_launch_context_abi",
    "require_kernel_invocation_abi",
    "require_kernel_invocation_entry_abi",
    "require_kernel_endpoint_abi",
    "require_kernel_endpoint_ptr_abi",
    "kernel_launch_context_checked",
    "kernel_launch_context_all_handle_fields_read",
    "kernel_launch_context_error_count",
    "kernel_launch_context_packet_chain_depth",
    "kernel_launch_context_payload_bytes",
    "kernel_launch_context_passed_to_kernel",
    "kernel_launch_context_kernel_arg_pass_allowed",
    "kernel_launch_context_changes_kernel_launch_args",
    "kernel_launch_context_current_wna16_arg_compatible",
    "kernel_launch_context_requires_wna16_arg_reinterpretation",
    "kernel_invocation_checked",
    "kernel_invocation_all_handle_fields_read",
    "kernel_invocation_error_count",
    "kernel_invocation_packet_chain_depth",
    "kernel_invocation_payload_bytes",
    "kernel_invocation_passed_to_kernel",
    "kernel_invocation_kernel_arg_pass_allowed",
    "kernel_invocation_changes_kernel_launch_args",
    "kernel_invocation_current_wna16_arg_compatible",
    "kernel_invocation_requires_wna16_arg_reinterpretation",
    "kernel_invocation_entry_checked",
    "kernel_invocation_entry_all_handle_fields_read",
    "kernel_invocation_entry_error_count",
    "kernel_invocation_entry_packet_chain_depth",
    "kernel_invocation_entry_payload_bytes",
    "kernel_invocation_entry_passed_to_kernel",
    "kernel_invocation_entry_kernel_arg_pass_allowed",
    "kernel_invocation_entry_changes_kernel_launch_args",
    "kernel_invocation_entry_current_wna16_arg_compatible",
    "kernel_invocation_entry_requires_wna16_arg_reinterpretation",
    "kernel_endpoint_checked",
    "kernel_endpoint_all_handle_fields_read",
    "kernel_endpoint_error_count",
    "kernel_endpoint_packet_chain_depth",
    "kernel_endpoint_payload_bytes",
    "kernel_endpoint_passed_to_kernel",
    "kernel_endpoint_kernel_arg_pass_allowed",
    "kernel_endpoint_changes_kernel_launch_args",
    "kernel_endpoint_current_wna16_arg_compatible",
    "kernel_endpoint_requires_wna16_arg_reinterpretation",
    "kernel_endpoint_ptr_checked",
    "kernel_endpoint_ptr_all_handle_fields_read",
    "kernel_endpoint_ptr_error_count",
    "kernel_endpoint_ptr_packet_chain_depth",
    "kernel_endpoint_ptr_payload_bytes",
    "kernel_endpoint_ptr_passed_to_kernel",
    "kernel_endpoint_ptr_kernel_arg_pass_allowed",
    "kernel_endpoint_ptr_changes_kernel_launch_args",
    "kernel_endpoint_ptr_current_wna16_arg_compatible",
    "kernel_endpoint_ptr_requires_wna16_arg_reinterpretation",
)
ARG_SLOT_INVOCATION_EXPECTED = {
    "arg_slot_runner_require_kernel_launch_context_abi": True,
    "arg_slot_runner_require_kernel_invocation_abi": True,
    "arg_slot_runner_require_kernel_invocation_entry_abi": True,
    "arg_slot_runner_require_kernel_endpoint_abi": True,
    "arg_slot_runner_require_kernel_endpoint_ptr_abi": True,
    "arg_slot_runner_kernel_launch_context_checked": True,
    "arg_slot_runner_kernel_launch_context_all_handle_fields_read": True,
    "arg_slot_runner_kernel_launch_context_error_count": 0,
    "arg_slot_runner_kernel_launch_context_payload_bytes": 0,
    "arg_slot_runner_kernel_launch_context_passed_to_kernel": False,
    "arg_slot_runner_kernel_launch_context_kernel_arg_pass_allowed": False,
    "arg_slot_runner_kernel_launch_context_changes_kernel_launch_args": False,
    "arg_slot_runner_kernel_launch_context_current_wna16_arg_compatible": False,
    "arg_slot_runner_kernel_launch_context_requires_wna16_arg_reinterpretation": False,
    "arg_slot_runner_kernel_invocation_checked": True,
    "arg_slot_runner_kernel_invocation_all_handle_fields_read": True,
    "arg_slot_runner_kernel_invocation_error_count": 0,
    "arg_slot_runner_kernel_invocation_payload_bytes": 0,
    "arg_slot_runner_kernel_invocation_passed_to_kernel": False,
    "arg_slot_runner_kernel_invocation_kernel_arg_pass_allowed": False,
    "arg_slot_runner_kernel_invocation_changes_kernel_launch_args": False,
    "arg_slot_runner_kernel_invocation_current_wna16_arg_compatible": False,
    "arg_slot_runner_kernel_invocation_requires_wna16_arg_reinterpretation": False,
    "arg_slot_runner_kernel_invocation_entry_checked": True,
    "arg_slot_runner_kernel_invocation_entry_all_handle_fields_read": True,
    "arg_slot_runner_kernel_invocation_entry_error_count": 0,
    "arg_slot_runner_kernel_invocation_entry_payload_bytes": 0,
    "arg_slot_runner_kernel_invocation_entry_passed_to_kernel": False,
    "arg_slot_runner_kernel_invocation_entry_kernel_arg_pass_allowed": False,
    "arg_slot_runner_kernel_invocation_entry_changes_kernel_launch_args": False,
    "arg_slot_runner_kernel_invocation_entry_current_wna16_arg_compatible": False,
    "arg_slot_runner_kernel_invocation_entry_requires_wna16_arg_reinterpretation": False,
    "arg_slot_runner_kernel_endpoint_checked": True,
    "arg_slot_runner_kernel_endpoint_all_handle_fields_read": True,
    "arg_slot_runner_kernel_endpoint_error_count": 0,
    "arg_slot_runner_kernel_endpoint_payload_bytes": 0,
    "arg_slot_runner_kernel_endpoint_passed_to_kernel": False,
    "arg_slot_runner_kernel_endpoint_kernel_arg_pass_allowed": False,
    "arg_slot_runner_kernel_endpoint_changes_kernel_launch_args": False,
    "arg_slot_runner_kernel_endpoint_current_wna16_arg_compatible": False,
    "arg_slot_runner_kernel_endpoint_requires_wna16_arg_reinterpretation": False,
    "arg_slot_runner_kernel_endpoint_ptr_checked": True,
    "arg_slot_runner_kernel_endpoint_ptr_all_handle_fields_read": True,
    "arg_slot_runner_kernel_endpoint_ptr_error_count": 0,
    "arg_slot_runner_kernel_endpoint_ptr_payload_bytes": 0,
    "arg_slot_runner_kernel_endpoint_ptr_passed_to_kernel": False,
    "arg_slot_runner_kernel_endpoint_ptr_kernel_arg_pass_allowed": False,
    "arg_slot_runner_kernel_endpoint_ptr_changes_kernel_launch_args": False,
    "arg_slot_runner_kernel_endpoint_ptr_current_wna16_arg_compatible": False,
    "arg_slot_runner_kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
}
ARG_SLOT_INVOCATION_POSITIVE_INT_FIELDS = (
    "arg_slot_runner_kernel_launch_context_packet_chain_depth",
    "arg_slot_runner_kernel_invocation_packet_chain_depth",
    "arg_slot_runner_kernel_invocation_entry_packet_chain_depth",
    "arg_slot_runner_kernel_endpoint_packet_chain_depth",
    "arg_slot_runner_kernel_endpoint_ptr_packet_chain_depth",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 <= parsed <= 0xFFFFFFFFFFFFFFFF


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    entries = [str(REPO_ROOT), str(REPO_ROOT / "src")]
    if existing:
        entries.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return env


def _run_step(cmd: list[str], *, dry_run: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"cmd": cmd, "dry_run": bool(dry_run)}
    if dry_run:
        result["returncode"] = 0
        return result
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        env=_subprocess_env(),
    )
    result["returncode"] = int(completed.returncode)
    return result


def _optional_device_args(args: argparse.Namespace) -> list[str]:
    device_args: list[str] = []
    if args.device is not None:
        device_args.extend(["--device", str(int(args.device))])
    if args.hip_visible_devices:
        device_args.extend(["--hip-visible-devices", args.hip_visible_devices])
    return device_args


def _load_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"exists": True, "read_error": type(exc).__name__}
    if not isinstance(payload, dict):
        return {"exists": True, "read_error": "non_object_json"}
    status = {
        "exists": True,
        "passed": payload.get("passed"),
        "failures": payload.get("failures"),
        "source": payload.get("source"),
        "payload_bytes": payload.get("payload_bytes"),
        "passed_to_kernel": payload.get("passed_to_kernel"),
        "changes_kernel_launch_args": payload.get("changes_kernel_launch_args"),
        "tail_window_probe_enabled": payload.get("tail_window_probe_enabled"),
        "tail_window_size": payload.get("tail_window_size"),
        "require_tail_window_probe": payload.get("require_tail_window_probe"),
        "row_count": payload.get("row_count"),
        "expected_window_size": payload.get("expected_window_size"),
        "expected_block_threads": payload.get("expected_block_threads"),
        "require_child_artifacts": payload.get("require_child_artifacts"),
        "require_child_field_masks": payload.get("require_child_field_masks"),
        "require_child_consumer_view": payload.get("require_child_consumer_view"),
        "require_child_consumer_view_layout": payload.get(
            "require_child_consumer_view_layout"
        ),
        "require_child_consumer_view_row_layout": payload.get(
            "require_child_consumer_view_row_layout"
        ),
        "require_child_consumer_view_handle_projection": payload.get(
            "require_child_consumer_view_handle_projection"
        ),
        "require_child_program_view_ptr_abi": payload.get(
            "require_child_program_view_ptr_abi"
        ),
        "require_child_kernel_arg_packet_abi": payload.get(
            "require_child_kernel_arg_packet_abi"
        ),
        "require_child_kernel_entry_args_abi": payload.get(
            "require_child_kernel_entry_args_abi"
        ),
        "require_child_kernel_entry_args_ptr_abi": payload.get(
            "require_child_kernel_entry_args_ptr_abi"
        ),
        "require_child_launch_envelope_args_ptr_abi": payload.get(
            "require_child_launch_envelope_args_ptr_abi"
        ),
        "require_child_kernel_launch_descriptor_abi": payload.get(
            "require_child_kernel_launch_descriptor_abi"
        ),
        "require_child_kernel_entry_row_metadata": payload.get(
            "require_child_kernel_entry_row_metadata"
        ),
        "require_non_degenerate_windows": payload.get(
            "require_non_degenerate_windows"
        ),
        "require_child_checks": payload.get("require_child_checks"),
        "mirror_fields_checked": payload.get("mirror_fields_checked"),
        "windows_checked": payload.get("windows_checked"),
        "require_wna16_side_consumer_variant_execution": payload.get(
            "require_wna16_side_consumer_variant_execution"
        ),
        "wna16_side_consumer_variant_execution_checked": payload.get(
            "wna16_side_consumer_variant_execution_checked"
        ),
        "wna16_side_consumer_variant_execution_all_handle_fields_read": payload.get(
            "wna16_side_consumer_variant_execution_all_handle_fields_read"
        ),
        "wna16_side_consumer_variant_execution_row_count": payload.get(
            "wna16_side_consumer_variant_execution_row_count"
        ),
        "wna16_side_consumer_variant_execution_row_ok_count": payload.get(
            "wna16_side_consumer_variant_execution_row_ok_count"
        ),
        "wna16_side_consumer_variant_execution_error_count": payload.get(
            "wna16_side_consumer_variant_execution_error_count"
        ),
        "wna16_side_consumer_variant_execution_payload_bytes": payload.get(
            "wna16_side_consumer_variant_execution_payload_bytes"
        ),
        "wna16_side_consumer_variant_execution_passed_to_kernel": payload.get(
            "wna16_side_consumer_variant_execution_passed_to_kernel"
        ),
        "wna16_side_consumer_variant_execution_changes_kernel_launch_args": (
            payload.get("wna16_side_consumer_variant_execution_changes_kernel_launch_args")
        ),
        "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": (
            payload.get("wna16_side_consumer_variant_execution_current_wna16_arg_compatible")
        ),
        "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": (
            payload.get(
                "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation"
            )
        ),
        "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": (
            payload.get("wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot")
        ),
        "wna16_side_consumer_variant_execution_explicit_typed_abi_slot": (
            payload.get(
                "wna16_side_consumer_variant_execution_explicit_typed_abi_slot"
            )
        ),
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
            payload.get(
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator"
            )
        ),
    }
    for field in WNA16_SIDE_VARIANT_FIELDS:
        for suffix in (
            "read_row_count",
            "read_row_ok_count",
            "read_error_count",
        ):
            key = f"wna16_side_consumer_variant_execution_{field}_{suffix}"
            status[key] = payload.get(key)
    for suffix in WNA16_SIDE_VARIANT_HASH_FIELDS:
        key = f"wna16_side_consumer_variant_execution_{suffix}"
        status[key] = payload.get(key)
    stub_summary = payload.get("stub_summary")
    if isinstance(stub_summary, dict):
        status["stub_summary"] = stub_summary
        for field in WNA16_SIDE_VARIANT_FIELDS:
            for suffix in (
                "read_row_count",
                "read_row_ok_count",
                "read_error_count",
            ):
                key = f"wna16_side_consumer_variant_execution_{field}_{suffix}"
                if status.get(key) is None:
                    status[key] = stub_summary.get(key)
        for suffix in WNA16_SIDE_VARIANT_HASH_FIELDS:
            key = f"wna16_side_consumer_variant_execution_{suffix}"
            if status.get(key) is None:
                status[key] = stub_summary.get(key)
        if (
            status.get(
                "wna16_side_consumer_variant_execution_explicit_typed_abi_slot"
            )
            is None
        ):
            status["wna16_side_consumer_variant_execution_explicit_typed_abi_slot"] = (
                stub_summary.get(
                    "wna16_side_consumer_variant_execution_explicit_typed_abi_slot"
                )
            )
    summaries = payload.get("summaries")
    if isinstance(summaries, dict):
        arg_slot_runner = summaries.get("arg_slot_runner")
        if isinstance(arg_slot_runner, dict):
            for field in ARG_SLOT_INVOCATION_STATUS_FIELDS:
                status[f"arg_slot_runner_{field}"] = arg_slot_runner.get(field)
    if (
        status.get("payload_bytes") is None
        and status.get("wna16_side_consumer_variant_execution_payload_bytes")
        is not None
    ):
        status["payload_bytes"] = status[
            "wna16_side_consumer_variant_execution_payload_bytes"
        ]
    return status


def _status_failures(statuses: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for name, status in statuses.items():
        if status.get("exists") is not True:
            failures.append(f"{name}_missing")
            continue
        if status.get("passed") is not True:
            failures.append(f"{name}_not_passed")
        if status.get("failures") != []:
            failures.append(f"{name}_failures_not_empty")

    for name in (
        "default_closure",
        "tail_window_closure",
        "window_sweep",
        "all_field_window_sweep",
    ):
        status = statuses.get(name, {})
        if status.get("payload_bytes") != 0:
            failures.append(f"{name}_payload_bytes_mismatch")
        if status.get("passed_to_kernel") is not False:
            failures.append(f"{name}_passed_to_kernel_mismatch")
        if status.get("changes_kernel_launch_args") is not False:
            failures.append(f"{name}_changes_kernel_launch_args_mismatch")

    if statuses.get("default_closure", {}).get("tail_window_probe_enabled") is not False:
        failures.append("default_closure_tail_window_enabled")
    default_closure = statuses.get("default_closure", {})
    for key, expected in ARG_SLOT_INVOCATION_EXPECTED.items():
        if default_closure.get(key) != expected:
            failures.append(f"default_closure_{key}_mismatch")
    for key in ARG_SLOT_INVOCATION_POSITIVE_INT_FIELDS:
        value = default_closure.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            failures.append(f"default_closure_{key}_invalid")
    if statuses.get("tail_window_closure", {}).get("tail_window_probe_enabled") is not True:
        failures.append("tail_window_closure_tail_window_not_enabled")
    if statuses.get("tail_window_closure_check", {}).get("require_tail_window_probe") is not True:
        failures.append("tail_window_closure_check_did_not_require_tail_window")
    window_check = statuses.get("window_sweep_check", {})
    if window_check.get("require_child_artifacts") is not True:
        failures.append("window_sweep_check_did_not_require_child_artifacts")
    if window_check.get("require_child_field_masks") is not True:
        failures.append("window_sweep_check_did_not_require_child_field_masks")
    if window_check.get("require_child_consumer_view") is not True:
        failures.append("window_sweep_check_did_not_require_child_consumer_view")
    if window_check.get("require_child_consumer_view_layout") is not True:
        failures.append(
            "window_sweep_check_did_not_require_child_consumer_view_layout"
        )
    if window_check.get("require_child_consumer_view_row_layout") is not True:
        failures.append(
            "window_sweep_check_did_not_require_child_consumer_view_row_layout"
        )
    if window_check.get("require_child_consumer_view_handle_projection") is not True:
        failures.append(
            "window_sweep_check_did_not_require_child_consumer_view_handle_projection"
        )
    if window_check.get("require_child_program_view_ptr_abi") is not True:
        failures.append("window_sweep_check_did_not_require_program_view_ptr_abi")
    if window_check.get("require_child_kernel_arg_packet_abi") is not True:
        failures.append("window_sweep_check_did_not_require_kernel_arg_packet_abi")
    if window_check.get("require_child_kernel_entry_args_abi") is not True:
        failures.append("window_sweep_check_did_not_require_kernel_entry_args_abi")
    if window_check.get("require_child_kernel_entry_args_ptr_abi") is not True:
        failures.append(
            "window_sweep_check_did_not_require_kernel_entry_args_ptr_abi"
        )
    if window_check.get("require_child_launch_envelope_args_ptr_abi") is not True:
        failures.append(
            "window_sweep_check_did_not_require_launch_envelope_args_ptr_abi"
        )
    if window_check.get("require_child_kernel_launch_descriptor_abi") is not True:
        failures.append(
            "window_sweep_check_did_not_require_kernel_launch_descriptor_abi"
        )
    if window_check.get("require_child_kernel_entry_row_metadata") is not True:
        failures.append("window_sweep_check_did_not_require_kernel_entry_row_metadata")
    if window_check.get("require_non_degenerate_windows") is not True:
        failures.append("window_sweep_check_did_not_require_non_degenerate_windows")
    if window_check.get("expected_window_size") != 512:
        failures.append("window_sweep_check_window_size_mismatch")
    if window_check.get("windows_checked") != ["full", "head", "middle", "tail"]:
        failures.append("window_sweep_check_windows_checked_mismatch")
    all_field_check = statuses.get("all_field_window_sweep_check", {})
    if all_field_check.get("require_child_checks") is not True:
        failures.append("all_field_window_sweep_check_did_not_require_child_checks")
    if all_field_check.get("require_child_field_masks") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_child_field_masks"
        )
    if all_field_check.get("require_child_consumer_view") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_child_consumer_view"
        )
    if all_field_check.get("require_child_consumer_view_layout") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_child_consumer_view_layout"
        )
    if all_field_check.get("require_child_consumer_view_row_layout") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_child_consumer_view_row_layout"
        )
    if (
        all_field_check.get("require_child_consumer_view_handle_projection")
        is not True
    ):
        failures.append(
            "all_field_window_sweep_check_did_not_require_child_consumer_view_handle_projection"
        )
    if all_field_check.get("require_child_program_view_ptr_abi") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_program_view_ptr_abi"
        )
    if all_field_check.get("require_child_kernel_arg_packet_abi") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_kernel_arg_packet_abi"
        )
    if all_field_check.get("require_child_kernel_entry_args_abi") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_kernel_entry_args_abi"
        )
    if all_field_check.get("require_child_kernel_entry_args_ptr_abi") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_kernel_entry_args_ptr_abi"
        )
    if all_field_check.get("require_child_kernel_entry_row_metadata") is not True:
        failures.append(
            "all_field_window_sweep_check_did_not_require_kernel_entry_row_metadata"
        )
    if all_field_check.get("expected_window_size") != 512:
        failures.append("all_field_window_sweep_check_window_size_mismatch")
    if all_field_check.get("mirror_fields_checked") != [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]:
        failures.append("all_field_window_sweep_check_fields_checked_mismatch")
    wna16_status = statuses.get("wna16_side_consumer_variant")
    if isinstance(wna16_status, dict):
        row_count = wna16_status.get("wna16_side_consumer_variant_execution_row_count")
        row_ok_count = wna16_status.get(
            "wna16_side_consumer_variant_execution_row_ok_count"
        )
        if wna16_status.get("require_wna16_side_consumer_variant_execution") is not True:
            failures.append("wna16_side_variant_did_not_require_execution")
        if wna16_status.get("wna16_side_consumer_variant_execution_checked") is not True:
            failures.append("wna16_side_variant_not_checked")
        if (
            wna16_status.get("wna16_side_consumer_variant_execution_all_handle_fields_read")
            is not True
        ):
            failures.append("wna16_side_variant_did_not_read_all_handle_fields")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 1024:
            failures.append("wna16_side_variant_row_count_too_small")
        if row_ok_count != row_count:
            failures.append("wna16_side_variant_row_ok_count_mismatch")
        if wna16_status.get("wna16_side_consumer_variant_execution_error_count") != 0:
            failures.append("wna16_side_variant_error_count_mismatch")
        if wna16_status.get("wna16_side_consumer_variant_execution_payload_bytes") != 0:
            failures.append("wna16_side_variant_payload_bytes_mismatch")
        if (
            wna16_status.get("wna16_side_consumer_variant_execution_passed_to_kernel")
            is not False
        ):
            failures.append("wna16_side_variant_passed_to_kernel_mismatch")
        if (
            wna16_status.get(
                "wna16_side_consumer_variant_execution_changes_kernel_launch_args"
            )
            is not False
        ):
            failures.append("wna16_side_variant_changes_kernel_launch_args_mismatch")
        if (
            wna16_status.get(
                "wna16_side_consumer_variant_execution_current_wna16_arg_compatible"
            )
            is not False
        ):
            failures.append("wna16_side_variant_current_wna16_arg_compatible_mismatch")
        if (
            wna16_status.get(
                "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation"
            )
            is not False
        ):
            failures.append("wna16_side_variant_requires_reinterpretation_mismatch")
        if (
            wna16_status.get(
                "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot"
            )
            is not False
        ):
            failures.append("wna16_side_variant_reuses_current_wna16_arg_slot_mismatch")
        if (
            wna16_status.get(
                "wna16_side_consumer_variant_execution_explicit_typed_abi_slot"
            )
            is not True
        ):
            failures.append("wna16_side_variant_explicit_typed_abi_slot_mismatch")
        for field in WNA16_SIDE_VARIANT_FIELDS:
            if (
                wna16_status.get(
                    f"wna16_side_consumer_variant_execution_{field}_read_row_count"
                )
                != row_count
            ):
                failures.append(
                    f"wna16_side_variant_{field}_read_row_count_mismatch"
                )
            if (
                wna16_status.get(
                    f"wna16_side_consumer_variant_execution_{field}_read_row_ok_count"
                )
                != row_count
            ):
                failures.append(
                    f"wna16_side_variant_{field}_read_row_ok_count_mismatch"
                )
            if (
                wna16_status.get(
                    f"wna16_side_consumer_variant_execution_{field}_read_error_count"
                )
                != 0
            ):
                failures.append(
                    f"wna16_side_variant_{field}_read_error_count_mismatch"
                )
        for suffix in WNA16_SIDE_VARIANT_HASH_FIELDS:
            hash_value = wna16_status.get(
                f"wna16_side_consumer_variant_execution_{suffix}"
            )
            if not _is_hex_u64(hash_value):
                failures.append(f"wna16_side_variant_{suffix}_invalid")
    return failures


def run_verify(args: argparse.Namespace) -> dict[str, Any]:
    closure_json = _resolve(args.closure_json)
    closure_check_json = _resolve(args.closure_check_json)
    tail_closure_json = _resolve(args.tail_closure_json)
    tail_closure_check_json = _resolve(args.tail_closure_check_json)
    window_sweep_json = _resolve(args.window_sweep_json)
    window_sweep_check_json = _resolve(args.window_sweep_check_json)
    all_field_window_sweep_json = _resolve(args.all_field_window_sweep_json)
    all_field_window_sweep_check_json = _resolve(
        args.all_field_window_sweep_check_json
    )
    wna16_side_variant_json = _resolve(args.wna16_side_variant_json)
    wna16_side_variant_stub_json = _resolve(args.wna16_side_variant_stub_json)
    wna16_side_variant_merged_json = _resolve(args.wna16_side_variant_merged_json)
    device_args = _optional_device_args(args)

    steps = {
        "default_closure": _run_step(
            [
                sys.executable,
                "scripts/run_premap_lab_gate_closure.py",
                "--output-json",
                str(closure_json),
                *device_args,
            ],
            dry_run=bool(args.dry_run),
        ),
        "default_closure_check": _run_step(
            [
                sys.executable,
                "scripts/check_premap_lab_gate_closure.py",
                str(closure_json),
                "--output-json",
                str(closure_check_json),
            ],
            dry_run=bool(args.dry_run),
        ),
        "tail_window_closure": _run_step(
            [
                sys.executable,
                "scripts/run_premap_lab_gate_closure.py",
                "--run-tail-window-probe",
                "--tail-window-size",
                str(int(args.tail_window_size)),
                "--output-json",
                str(tail_closure_json),
                *device_args,
            ],
            dry_run=bool(args.dry_run),
        ),
        "tail_window_closure_check": _run_step(
            [
                sys.executable,
                "scripts/check_premap_lab_gate_closure.py",
                str(tail_closure_json),
                "--require-tail-window-probe",
                "--expected-tail-window-size",
                str(int(args.tail_window_size)),
                "--output-json",
                str(tail_closure_check_json),
            ],
            dry_run=bool(args.dry_run),
        ),
        "window_sweep": _run_step(
            [
                sys.executable,
                "scripts/run_premap_online_merged_native_arg_slot_window_sweep.py",
                "--window-size",
                "512",
                "--require-program-view-ptr-abi",
                "--require-launch-envelope-args-ptr-abi",
                "--require-kernel-launch-descriptor-abi",
                "--output-json",
                str(window_sweep_json),
                *device_args,
            ],
            dry_run=bool(args.dry_run),
        ),
        "window_sweep_check": _run_step(
            [
                sys.executable,
                "scripts/check_premap_online_merged_native_arg_slot_window_sweep.py",
                str(window_sweep_json),
                "--expected-window-size",
                "512",
                "--require-child-program-view-ptr-abi",
                "--require-child-kernel-arg-packet-abi",
                "--require-child-kernel-entry-args-abi",
                "--require-child-kernel-entry-args-ptr-abi",
                "--require-child-launch-envelope-args-ptr-abi",
                "--require-child-kernel-launch-descriptor-abi",
                "--output-json",
                str(window_sweep_check_json),
            ],
            dry_run=bool(args.dry_run),
        ),
        "all_field_window_sweep": _run_step(
            [
                sys.executable,
                "scripts/run_premap_online_merged_native_arg_slot_all_field_window_sweep.py",
                "--window-size",
                "512",
                "--require-program-view-ptr-abi",
                "--require-kernel-arg-packet-abi",
                "--require-kernel-entry-args-abi",
                "--require-kernel-entry-args-ptr-abi",
                "--output-json",
                str(all_field_window_sweep_json),
                *device_args,
            ],
            dry_run=bool(args.dry_run),
        ),
        "all_field_window_sweep_check": _run_step(
            [
                sys.executable,
                "scripts/check_premap_online_merged_native_arg_slot_all_field_window_sweep.py",
                str(all_field_window_sweep_json),
                "--expected-window-size",
                "512",
                "--require-child-program-view-ptr-abi",
                "--require-child-kernel-arg-packet-abi",
                "--require-child-kernel-entry-args-abi",
                "--require-child-kernel-entry-args-ptr-abi",
                "--output-json",
                str(all_field_window_sweep_check_json),
            ],
            dry_run=bool(args.dry_run),
        ),
        "wna16_side_consumer_variant": _run_step(
            [
                sys.executable,
                "scripts/run_premap_online_merged_native_arg_slot_canary.py",
                "--require-wna16-side-consumer-variant-execution",
                "--max-inputs",
                "32",
                "--min-source-count",
                "32",
                "--min-total-rows",
                "1024",
                "--block-threads",
                "256",
                "--output-json",
                str(wna16_side_variant_json),
                "--stub-output-json",
                str(wna16_side_variant_stub_json),
                "--merged-output-json",
                str(wna16_side_variant_merged_json),
                *device_args,
            ],
            dry_run=bool(args.dry_run),
        ),
    }
    step_failures = [
        name
        for name, step in steps.items()
        if int(step.get("returncode", 1)) != 0
    ]
    statuses = {
        "default_closure": _load_status(closure_json),
        "default_closure_check": _load_status(closure_check_json),
        "tail_window_closure": _load_status(tail_closure_json),
        "tail_window_closure_check": _load_status(tail_closure_check_json),
        "window_sweep": _load_status(window_sweep_json),
        "window_sweep_check": _load_status(window_sweep_check_json),
        "all_field_window_sweep": _load_status(all_field_window_sweep_json),
        "all_field_window_sweep_check": _load_status(
            all_field_window_sweep_check_json
        ),
        "wna16_side_consumer_variant": _load_status(wna16_side_variant_json),
    }
    status_failures = [] if args.dry_run else _status_failures(statuses)
    failures = step_failures + status_failures
    report = {
        "passed": not failures,
        "failures": failures,
        "source": "premap_lab_gate_verify",
        "dry_run": bool(args.dry_run),
        "tail_window_size": int(args.tail_window_size),
        "paths": {
            "closure_json": str(closure_json),
            "closure_check_json": str(closure_check_json),
            "tail_closure_json": str(tail_closure_json),
            "tail_closure_check_json": str(tail_closure_check_json),
            "window_sweep_json": str(window_sweep_json),
            "window_sweep_check_json": str(window_sweep_check_json),
            "all_field_window_sweep_json": str(all_field_window_sweep_json),
            "all_field_window_sweep_check_json": str(
                all_field_window_sweep_check_json
            ),
            "wna16_side_variant_json": str(wna16_side_variant_json),
            "wna16_side_variant_stub_json": str(wna16_side_variant_stub_json),
            "wna16_side_variant_merged_json": str(wna16_side_variant_merged_json),
        },
        "steps": steps,
        "statuses": statuses,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure-json", type=Path, default=DEFAULT_CLOSURE_JSON)
    parser.add_argument(
        "--closure-check-json",
        type=Path,
        default=DEFAULT_CLOSURE_CHECK_JSON,
    )
    parser.add_argument(
        "--tail-closure-json",
        type=Path,
        default=DEFAULT_TAIL_CLOSURE_JSON,
    )
    parser.add_argument(
        "--tail-closure-check-json",
        type=Path,
        default=DEFAULT_TAIL_CLOSURE_CHECK_JSON,
    )
    parser.add_argument("--tail-window-size", type=int, default=512)
    parser.add_argument(
        "--window-sweep-json",
        type=Path,
        default=DEFAULT_WINDOW_SWEEP_JSON,
    )
    parser.add_argument(
        "--window-sweep-check-json",
        type=Path,
        default=DEFAULT_WINDOW_SWEEP_CHECK_JSON,
    )
    parser.add_argument(
        "--all-field-window-sweep-json",
        type=Path,
        default=DEFAULT_ALL_FIELD_WINDOW_SWEEP_JSON,
    )
    parser.add_argument(
        "--all-field-window-sweep-check-json",
        type=Path,
        default=DEFAULT_ALL_FIELD_WINDOW_SWEEP_CHECK_JSON,
    )
    parser.add_argument(
        "--wna16-side-variant-json",
        type=Path,
        default=DEFAULT_WNA16_SIDE_VARIANT_JSON,
    )
    parser.add_argument(
        "--wna16-side-variant-stub-json",
        type=Path,
        default=DEFAULT_WNA16_SIDE_VARIANT_STUB_JSON,
    )
    parser.add_argument(
        "--wna16-side-variant-merged-json",
        type=Path,
        default=DEFAULT_WNA16_SIDE_VARIANT_MERGED_JSON,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_VERIFY_JSON)
    parser.add_argument("--device", type=int)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_verify(args)
    output_json = _resolve(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
