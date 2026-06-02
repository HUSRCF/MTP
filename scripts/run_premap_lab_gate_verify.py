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
DEFAULT_VERIFY_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_verify.json"
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


def _load_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"exists": True, "read_error": type(exc).__name__}
    if not isinstance(payload, dict):
        return {"exists": True, "read_error": "non_object_json"}
    return {
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
        "require_non_degenerate_windows": payload.get(
            "require_non_degenerate_windows"
        ),
        "require_child_checks": payload.get("require_child_checks"),
        "mirror_fields_checked": payload.get("mirror_fields_checked"),
        "windows_checked": payload.get("windows_checked"),
    }


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
    if all_field_check.get("expected_window_size") != 512:
        failures.append("all_field_window_sweep_check_window_size_mismatch")
    if all_field_check.get("mirror_fields_checked") != [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]:
        failures.append("all_field_window_sweep_check_fields_checked_mismatch")
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

    steps = {
        "default_closure": _run_step(
            [
                sys.executable,
                "scripts/run_premap_lab_gate_closure.py",
                "--output-json",
                str(closure_json),
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
                "--output-json",
                str(window_sweep_json),
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
                "--output-json",
                str(all_field_window_sweep_json),
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
                "--output-json",
                str(all_field_window_sweep_check_json),
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
    parser.add_argument("--output-json", type=Path, default=DEFAULT_VERIFY_JSON)
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
