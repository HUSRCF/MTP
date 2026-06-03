#!/usr/bin/env python3
"""Check a premap lab-gate closure artifact.

This is a static artifact checker.  It does not refresh GPU/native canaries; it
verifies that a previously generated closure report records the required
readonly safety boundary and evidence-source contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_premap_lab_gate_closure import (  # noqa: E402
    _tail_window_probe_failures,
)


DEFAULT_CLOSURE_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_closure.json"
)

REQUIRED_STEPS = (
    "arg_slot_runner",
    "full_preflight",
    "summary_preflight",
    "summary_check",
    "native_artifact_check",
)


def _arg_slot_invocation_summary_failures(summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected = {
        "require_kernel_launch_context_abi": True,
        "require_kernel_invocation_abi": True,
        "kernel_launch_context_checked": True,
        "kernel_launch_context_all_handle_fields_read": True,
        "kernel_launch_context_payload_bytes": 0,
        "kernel_launch_context_passed_to_kernel": False,
        "kernel_launch_context_kernel_arg_pass_allowed": False,
        "kernel_launch_context_changes_kernel_launch_args": False,
        "kernel_launch_context_current_wna16_arg_compatible": False,
        "kernel_invocation_checked": True,
        "kernel_invocation_all_handle_fields_read": True,
        "kernel_invocation_payload_bytes": 0,
        "kernel_invocation_passed_to_kernel": False,
        "kernel_invocation_kernel_arg_pass_allowed": False,
        "kernel_invocation_changes_kernel_launch_args": False,
        "kernel_invocation_current_wna16_arg_compatible": False,
    }
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            failures.append(f"arg_slot_runner_{key}_mismatch")
    for key in (
        "kernel_launch_context_packet_chain_depth",
        "kernel_invocation_packet_chain_depth",
    ):
        value = summary.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            failures.append(f"arg_slot_runner_{key}_invalid")
    return failures


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("closure JSON must contain an object")
    return payload


def check_closure_artifact(
    path: Path,
    *,
    allow_dry_run: bool = False,
    require_tail_window_probe: bool = False,
    expected_tail_window_size: int = 512,
) -> dict[str, Any]:
    closure_path = path.resolve()
    failures: list[str] = []
    try:
        payload = _load_json(closure_path)
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return {
            "passed": False,
            "failures": [f"closure_json_read_failed:{type(exc).__name__}"],
            "closure_json": str(closure_path),
            "source": "premap_lab_gate_closure_check",
        }

    if payload.get("source") != "premap_lab_gate_closure":
        failures.append("source_mismatch")
    if payload.get("passed") is not True:
        failures.append("closure_not_passed")
    if payload.get("failures") != []:
        failures.append("closure_failures_not_empty")
    if payload.get("requires_runner_recorded_artifact_paths") is not True:
        failures.append("runner_recorded_artifact_paths_not_required")
    if payload.get("payload_bytes") != 0:
        failures.append("payload_bytes_mismatch")
    if payload.get("passed_to_kernel") is not False:
        failures.append("passed_to_kernel_mismatch")
    if payload.get("changes_kernel_launch_args") is not False:
        failures.append("changes_kernel_launch_args_mismatch")
    if payload.get("dry_run") is True and not allow_dry_run:
        failures.append("dry_run_not_allowed")

    steps = payload.get("steps")
    if not isinstance(steps, dict):
        failures.append("steps_missing")
        steps = {}
    required_steps = list(REQUIRED_STEPS)
    if require_tail_window_probe:
        required_steps.append("arg_slot_tail_window_runner")
    for step_name in required_steps:
        step = steps.get(step_name)
        if not isinstance(step, dict):
            failures.append(f"step_{step_name}_missing")
            continue
        if step.get("returncode") != 0:
            failures.append(f"step_{step_name}_returncode_mismatch")
        if step.get("dry_run") is True and not allow_dry_run:
            failures.append(f"step_{step_name}_dry_run_not_allowed")

    summaries = payload.get("summaries")
    if not isinstance(summaries, dict):
        failures.append("summaries_missing")
        summaries = {}
    native_summary = summaries.get("native_artifact_check")
    if not isinstance(native_summary, dict):
        failures.append("native_artifact_check_summary_missing")
    else:
        if native_summary.get("passed") is not True:
            failures.append("native_artifact_check_summary_not_passed")
        if native_summary.get("preflight_json_source") != "runner_recorded":
            failures.append("native_artifact_check_preflight_source_mismatch")
        if native_summary.get("status_json_source") != "runner_recorded":
            failures.append("native_artifact_check_status_source_mismatch")
    for summary_name in (
        "arg_slot_runner",
        "full_preflight",
        "summary_preflight",
        "summary_check",
    ):
        summary = summaries.get(summary_name)
        if not isinstance(summary, dict):
            failures.append(f"{summary_name}_summary_missing")
        elif summary.get("passed") is not True:
            failures.append(f"{summary_name}_summary_not_passed")
    arg_slot_summary = summaries.get("arg_slot_runner")
    if isinstance(arg_slot_summary, dict):
        failures.extend(_arg_slot_invocation_summary_failures(arg_slot_summary))

    failures.extend(
        _tail_window_probe_failures(
            summaries,
            enabled=require_tail_window_probe,
            dry_run=bool(payload.get("dry_run") and allow_dry_run),
            expected_tail_window_size=int(expected_tail_window_size),
        )
    )
    return {
        "passed": not failures,
        "failures": failures,
        "source": "premap_lab_gate_closure_check",
        "closure_json": str(closure_path),
        "require_tail_window_probe": bool(require_tail_window_probe),
        "expected_tail_window_size": int(expected_tail_window_size),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("closure_json", nargs="?", type=Path, default=DEFAULT_CLOSURE_JSON)
    parser.add_argument("--allow-dry-run", action="store_true")
    parser.add_argument("--require-tail-window-probe", action="store_true")
    parser.add_argument("--expected-tail-window-size", type=int, default=512)
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_closure_artifact(
        args.closure_json,
        allow_dry_run=bool(args.allow_dry_run),
        require_tail_window_probe=bool(args.require_tail_window_probe),
        expected_tail_window_size=int(args.expected_tail_window_size),
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
