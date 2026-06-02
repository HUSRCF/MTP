#!/usr/bin/env python3
"""Run and statically verify the canonical premap lab gate closures.

This helper is still read-only with respect to the real vLLM/WNA16 path.  It
refreshes the default full-table closure, refreshes the optional tail-window
closure, and then checks both artifacts with the static closure checker.
"""

from __future__ import annotations

import argparse
import json
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
DEFAULT_VERIFY_JSON = (
    REPO_ROOT / "outputs" / "reports" / "premap_lab_gate_verify.json"
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _run_step(cmd: list[str], *, dry_run: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"cmd": cmd, "dry_run": bool(dry_run)}
    if dry_run:
        result["returncode"] = 0
        return result
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
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
    }


def run_verify(args: argparse.Namespace) -> dict[str, Any]:
    closure_json = _resolve(args.closure_json)
    closure_check_json = _resolve(args.closure_check_json)
    tail_closure_json = _resolve(args.tail_closure_json)
    tail_closure_check_json = _resolve(args.tail_closure_check_json)

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
    }
    failures = [
        name
        for name, step in steps.items()
        if int(step.get("returncode", 1)) != 0
    ]
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
        },
        "steps": steps,
        "statuses": {
            "default_closure": _load_status(closure_json),
            "default_closure_check": _load_status(closure_check_json),
            "tail_window_closure": _load_status(tail_closure_json),
            "tail_window_closure_check": _load_status(tail_closure_check_json),
        },
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
