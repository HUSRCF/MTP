#!/usr/bin/env python3
"""Run the canonical readonly premap lab-gate closure checks.

This is an orchestration helper only.  It refreshes/checks the existing
readonly artifacts and never enables payload movement or current WNA16 kernel
argument handoff.
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

DEFAULT_ARG_SLOT_RUNNER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_endpoint_canary_runner.json"
)
DEFAULT_ARG_SLOT_STUB_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_merged_endpoint_canary.json"
)
DEFAULT_ARG_SLOT_MERGED_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_prelaunch_typed_consumer_input_endpoint_canary.json"
)
DEFAULT_ARG_SLOT_TAIL_RUNNER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_tail_window512_canary_runner_current.json"
)
DEFAULT_ARG_SLOT_TAIL_STUB_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_merged_future_native_arg_slot_tail512_canary.json"
)
DEFAULT_ARG_SLOT_TAIL_MERGED_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_prelaunch_typed_consumer_input_arg_slot_tail512.json"
)
DEFAULT_NATIVE_RUNNER_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_arg_slot_32input_hard_hashchain_preflight_32tables.json"
)
DEFAULT_FULL_PREFLIGHT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_default_with_gate_schema_sha256.full.json"
)
DEFAULT_SUMMARY_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_default_with_gate_schema_sha256.json"
)
DEFAULT_SUMMARY_CHECK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_default_with_gate_schema_sha256.check.json"
)
DEFAULT_ARTIFACT_CHECK_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_artifact_check_current.json"
)
DEFAULT_REPORT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_gate_closure.json"
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


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


def _summary_check_device_args(args: argparse.Namespace) -> list[str]:
    if args.device is None:
        return []
    return ["--expected-online-merged-device", str(int(args.device))]


def _load_json_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"exists": True, "read_error": type(exc).__name__}
    if not isinstance(payload, dict):
        return {"exists": True, "read_error": "non_object_json"}
    summary: dict[str, Any] = {"exists": True}
    for key in (
        "passed",
        "failures",
        "source",
        "device",
        "selected_source_count",
        "merged_row_count",
        "block_threads",
        "tail_window_size",
        "dispatch_row_offset",
        "dispatch_row_limit",
        "dispatch_active_rows",
        "dispatch_expected_program_count",
        "handle_projection_all_handle_fields_checked",
        "no_payload",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "current_wna16_arg_compatible",
        "not_a_single_vllm_launch_table",
        "require_kernel_launch_context_abi",
        "require_kernel_invocation_abi",
        "require_kernel_invocation_entry_abi",
        "require_kernel_endpoint_abi",
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
        "online_merged_source_count",
        "online_merged_row_count",
        "online_merged_dispatch_active_rows",
        "preflight_json_source",
        "status_json_source",
    ):
        if key in payload:
            summary[key] = payload.get(key)
    return summary


def _runner_recorded_path_failures(
    summaries: dict[str, dict[str, Any]],
    *,
    dry_run: bool,
    allow_explicit_artifact_paths: bool,
) -> list[str]:
    if dry_run or allow_explicit_artifact_paths:
        return []

    artifact_summary = summaries.get("native_artifact_check", {})
    if not artifact_summary.get("exists"):
        return ["native_artifact_check_missing_for_runner_recorded_path_check"]

    failures: list[str] = []
    if artifact_summary.get("preflight_json_source") != "runner_recorded":
        failures.append("native_artifact_check_preflight_path_not_runner_recorded")
    if artifact_summary.get("status_json_source") != "runner_recorded":
        failures.append("native_artifact_check_status_path_not_runner_recorded")
    return failures


def _tail_window_probe_failures(
    summaries: dict[str, dict[str, Any]],
    *,
    enabled: bool,
    dry_run: bool,
    expected_tail_window_size: int,
) -> list[str]:
    if not enabled or dry_run:
        return []

    tail_summary = summaries.get("arg_slot_tail_window_runner", {})
    if not tail_summary.get("exists"):
        return ["arg_slot_tail_window_runner_missing"]

    failures: list[str] = []
    if tail_summary.get("passed") is not True:
        failures.append("arg_slot_tail_window_runner_not_passed")
    if tail_summary.get("tail_window_size") != int(expected_tail_window_size):
        failures.append("arg_slot_tail_window_size_mismatch")
    for key, expected_value in {
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
    }.items():
        if tail_summary.get(key) != expected_value:
            failures.append(f"arg_slot_tail_window_{key}_mismatch")
    merged_row_count = tail_summary.get("merged_row_count")
    block_threads = tail_summary.get("block_threads")
    dispatch_offset = tail_summary.get("dispatch_row_offset")
    dispatch_limit = tail_summary.get("dispatch_row_limit")
    dispatch_active = tail_summary.get("dispatch_active_rows")
    dispatch_programs = tail_summary.get("dispatch_expected_program_count")
    if not isinstance(merged_row_count, int) or isinstance(merged_row_count, bool):
        failures.append("arg_slot_tail_window_merged_row_count_invalid")
        return failures
    if not isinstance(block_threads, int) or isinstance(block_threads, bool):
        failures.append("arg_slot_tail_window_block_threads_invalid")
        return failures
    expected_offset = max(0, int(merged_row_count) - int(expected_tail_window_size))
    expected_active = int(merged_row_count) - expected_offset
    expected_programs = (expected_active + int(block_threads) - 1) // int(block_threads)
    if dispatch_offset != expected_offset:
        failures.append("arg_slot_tail_window_dispatch_offset_mismatch")
    if dispatch_limit != int(merged_row_count):
        failures.append("arg_slot_tail_window_dispatch_limit_mismatch")
    if dispatch_active != expected_active:
        failures.append("arg_slot_tail_window_dispatch_active_mismatch")
    if dispatch_programs != expected_programs:
        failures.append("arg_slot_tail_window_dispatch_program_count_mismatch")
    return failures


def run_closure(args: argparse.Namespace) -> dict[str, Any]:
    arg_slot_runner_json = _resolve(args.arg_slot_runner_json)
    arg_slot_stub_json = _resolve(args.arg_slot_stub_json)
    arg_slot_merged_json = _resolve(args.arg_slot_merged_json)
    arg_slot_tail_runner_json = _resolve(args.arg_slot_tail_runner_json)
    arg_slot_tail_stub_json = _resolve(args.arg_slot_tail_stub_json)
    arg_slot_tail_merged_json = _resolve(args.arg_slot_tail_merged_json)
    native_runner_json = _resolve(args.native_runner_json)
    full_preflight_json = _resolve(args.full_preflight_json)
    summary_json = _resolve(args.summary_json)
    summary_check_json = _resolve(args.summary_check_json)
    artifact_check_json = _resolve(args.artifact_check_json)
    arg_slot_device_args = _optional_device_args(args)
    summary_check_device_args = _summary_check_device_args(args)

    steps: dict[str, dict[str, Any]] = {}
    if not args.skip_arg_slot_runner:
        steps["arg_slot_runner"] = _run_step(
            [
                sys.executable,
                "scripts/run_premap_online_merged_native_arg_slot_canary.py",
                "--output-json",
                str(arg_slot_runner_json),
                "--stub-output-json",
                str(arg_slot_stub_json),
                "--merged-output-json",
                str(arg_slot_merged_json),
                "--require-kernel-launch-context-abi",
                "--require-kernel-invocation-abi",
                "--require-kernel-endpoint-abi",
                *arg_slot_device_args,
            ],
            dry_run=bool(args.dry_run),
        )
    if args.run_tail_window_probe:
        steps["arg_slot_tail_window_runner"] = _run_step(
            [
                sys.executable,
                "scripts/run_premap_online_merged_native_arg_slot_canary.py",
                "--runner-json",
                str(native_runner_json),
                "--tail-window-size",
                str(int(args.tail_window_size)),
                "--output-json",
                str(arg_slot_tail_runner_json),
                "--stub-output-json",
                str(arg_slot_tail_stub_json),
                "--merged-output-json",
                str(arg_slot_tail_merged_json),
                *arg_slot_device_args,
            ],
            dry_run=bool(args.dry_run),
        )
    steps["full_preflight"] = _run_step(
        [
            sys.executable,
            "scripts/run_premap_lab_preflight.py",
            "--output-json",
            str(full_preflight_json),
        ],
        dry_run=bool(args.dry_run),
    )
    steps["summary_preflight"] = _run_step(
        [
            sys.executable,
            "scripts/run_premap_lab_preflight.py",
            "--summary-only",
            "--output-json",
            str(summary_json),
        ],
        dry_run=bool(args.dry_run),
    )
    steps["summary_check"] = _run_step(
        [
            sys.executable,
            "scripts/check_premap_lab_preflight_summary.py",
            str(summary_json),
            *summary_check_device_args,
            "--output-json",
            str(summary_check_json),
        ],
        dry_run=bool(args.dry_run),
    )
    steps["native_artifact_check"] = _run_step(
        [
            sys.executable,
            "scripts/check_premap_online_native_stub_canary_artifacts.py",
            "--runner-json",
            str(native_runner_json),
            "--output-json",
            str(artifact_check_json),
        ],
        dry_run=bool(args.dry_run),
    )

    step_failures = [
        name
        for name, step in steps.items()
        if int(step.get("returncode", 1)) != 0
    ]
    summaries = {
        "arg_slot_runner": _load_json_summary(arg_slot_runner_json),
        "arg_slot_tail_window_runner": _load_json_summary(arg_slot_tail_runner_json),
        "full_preflight": _load_json_summary(full_preflight_json),
        "summary_preflight": _load_json_summary(summary_json),
        "summary_check": _load_json_summary(summary_check_json),
        "native_artifact_check": _load_json_summary(artifact_check_json),
    }
    runner_recorded_failures = _runner_recorded_path_failures(
        summaries,
        dry_run=bool(args.dry_run),
        allow_explicit_artifact_paths=bool(args.allow_explicit_artifact_paths),
    )
    tail_window_failures = _tail_window_probe_failures(
        summaries,
        enabled=bool(args.run_tail_window_probe),
        dry_run=bool(args.dry_run),
        expected_tail_window_size=int(args.tail_window_size),
    )
    failures = step_failures + runner_recorded_failures + tail_window_failures
    report = {
        "passed": not failures,
        "failures": failures,
        "source": "premap_lab_gate_closure",
        "dry_run": bool(args.dry_run),
        "requires_runner_recorded_artifact_paths": not bool(
            args.allow_explicit_artifact_paths
        ),
        "paths": {
            "arg_slot_runner_json": str(arg_slot_runner_json),
            "arg_slot_stub_json": str(arg_slot_stub_json),
            "arg_slot_merged_json": str(arg_slot_merged_json),
            "arg_slot_tail_runner_json": str(arg_slot_tail_runner_json),
            "arg_slot_tail_stub_json": str(arg_slot_tail_stub_json),
            "arg_slot_tail_merged_json": str(arg_slot_tail_merged_json),
            "native_runner_json": str(native_runner_json),
            "full_preflight_json": str(full_preflight_json),
            "summary_json": str(summary_json),
            "summary_check_json": str(summary_check_json),
            "artifact_check_json": str(artifact_check_json),
        },
        "steps": steps,
        "summaries": summaries,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "tail_window_probe_enabled": bool(args.run_tail_window_probe),
        "tail_window_size": int(args.tail_window_size),
    }
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arg-slot-runner-json", type=Path, default=DEFAULT_ARG_SLOT_RUNNER_JSON)
    parser.add_argument("--arg-slot-stub-json", type=Path, default=DEFAULT_ARG_SLOT_STUB_JSON)
    parser.add_argument("--arg-slot-merged-json", type=Path, default=DEFAULT_ARG_SLOT_MERGED_JSON)
    parser.add_argument("--arg-slot-tail-runner-json", type=Path, default=DEFAULT_ARG_SLOT_TAIL_RUNNER_JSON)
    parser.add_argument("--arg-slot-tail-stub-json", type=Path, default=DEFAULT_ARG_SLOT_TAIL_STUB_JSON)
    parser.add_argument("--arg-slot-tail-merged-json", type=Path, default=DEFAULT_ARG_SLOT_TAIL_MERGED_JSON)
    parser.add_argument("--native-runner-json", type=Path, default=DEFAULT_NATIVE_RUNNER_JSON)
    parser.add_argument("--full-preflight-json", type=Path, default=DEFAULT_FULL_PREFLIGHT_JSON)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--summary-check-json", type=Path, default=DEFAULT_SUMMARY_CHECK_JSON)
    parser.add_argument("--artifact-check-json", type=Path, default=DEFAULT_ARTIFACT_CHECK_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--skip-arg-slot-runner", action="store_true")
    parser.add_argument(
        "--run-tail-window-probe",
        action="store_true",
        help=(
            "Also run a readonly row-window/tail-window arg-slot canary. This "
            "does not replace the default full-table lab gate."
        ),
    )
    parser.add_argument("--tail-window-size", type=int, default=512)
    parser.add_argument("--device", type=int)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument(
        "--allow-explicit-artifact-paths",
        action="store_true",
        help=(
            "Allow the native artifact checker to use explicit preflight/status "
            "paths. The default lab gate requires runner-recorded paths."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_closure(args)
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
