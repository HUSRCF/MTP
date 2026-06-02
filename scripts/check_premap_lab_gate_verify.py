#!/usr/bin/env python3
"""Check the one-step premap lab gate verify artifact.

This checker is intentionally static: it validates that a generated
`premap_lab_gate_verify.json` records the required no-op lab gate evidence and
that all child steps/statuses passed.  It does not refresh native/GPU canaries.
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

from scripts.run_premap_lab_gate_verify import DEFAULT_VERIFY_JSON  # noqa: E402


REQUIRED_STEPS = (
    "default_closure",
    "default_closure_check",
    "tail_window_closure",
    "tail_window_closure_check",
    "window_sweep",
    "window_sweep_check",
)
SAFETY_STATUS_NAMES = ("default_closure", "tail_window_closure", "window_sweep")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("verify JSON must contain an object")
    return payload


def check_lab_gate_verify_artifact(
    path: Path,
    *,
    allow_dry_run: bool = False,
    expected_window_size: int = 512,
) -> dict[str, Any]:
    verify_path = path.resolve()
    failures: list[str] = []
    try:
        payload = _load_json(verify_path)
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return {
            "passed": False,
            "failures": [f"verify_json_read_failed:{type(exc).__name__}"],
            "source": "premap_lab_gate_verify_check",
            "verify_json": str(verify_path),
        }

    if payload.get("source") != "premap_lab_gate_verify":
        failures.append("source_mismatch")
    if payload.get("passed") is not True:
        failures.append("verify_not_passed")
    if payload.get("failures") != []:
        failures.append("verify_failures_not_empty")
    if payload.get("dry_run") is True and not allow_dry_run:
        failures.append("dry_run_not_allowed")
    if payload.get("payload_bytes") != 0:
        failures.append("payload_bytes_mismatch")
    if payload.get("passed_to_kernel") is not False:
        failures.append("passed_to_kernel_mismatch")
    if payload.get("changes_kernel_launch_args") is not False:
        failures.append("changes_kernel_launch_args_mismatch")

    steps = payload.get("steps")
    if not isinstance(steps, dict):
        failures.append("steps_missing")
        steps = {}
    for name in REQUIRED_STEPS:
        step = steps.get(name)
        if not isinstance(step, dict):
            failures.append(f"step_{name}_missing")
            continue
        if step.get("returncode") != 0:
            failures.append(f"step_{name}_returncode_mismatch")
        if step.get("dry_run") is True and not allow_dry_run:
            failures.append(f"step_{name}_dry_run_not_allowed")

    statuses = payload.get("statuses")
    if not isinstance(statuses, dict):
        failures.append("statuses_missing")
        statuses = {}
    for name in REQUIRED_STEPS:
        status = statuses.get(name)
        if not isinstance(status, dict):
            failures.append(f"status_{name}_missing")
            continue
        if status.get("exists") is not True:
            failures.append(f"status_{name}_missing_artifact")
        if status.get("passed") is not True:
            failures.append(f"status_{name}_not_passed")
        if status.get("failures") != []:
            failures.append(f"status_{name}_failures_not_empty")

    for name in SAFETY_STATUS_NAMES:
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
    if window_check.get("expected_window_size") != int(expected_window_size):
        failures.append("window_sweep_check_window_size_mismatch")
    if window_check.get("require_child_artifacts") is not True:
        failures.append("window_sweep_check_did_not_require_child_artifacts")
    if window_check.get("require_non_degenerate_windows") is not True:
        failures.append("window_sweep_check_did_not_require_non_degenerate_windows")
    if window_check.get("windows_checked") != ["full", "head", "middle", "tail"]:
        failures.append("window_sweep_check_windows_checked_mismatch")

    return {
        "passed": not failures,
        "failures": failures,
        "source": "premap_lab_gate_verify_check",
        "verify_json": str(verify_path),
        "allow_dry_run": bool(allow_dry_run),
        "expected_window_size": int(expected_window_size),
        "required_steps": list(REQUIRED_STEPS),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verify_json", nargs="?", type=Path, default=DEFAULT_VERIFY_JSON)
    parser.add_argument("--allow-dry-run", action="store_true")
    parser.add_argument("--expected-window-size", type=int, default=512)
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_lab_gate_verify_artifact(
        args.verify_json,
        allow_dry_run=bool(args.allow_dry_run),
        expected_window_size=int(args.expected_window_size),
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
