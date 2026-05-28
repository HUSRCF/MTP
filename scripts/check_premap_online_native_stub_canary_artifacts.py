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


def check_online_native_stub_canary_artifacts(
    *,
    root: Path,
    runner_json: Path = DEFAULT_RUNNER_JSON,
    preflight_json: Path = DEFAULT_PREFLIGHT_JSON,
    status_json: Path = DEFAULT_STATUS_JSON,
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
    status_required_count = _int(status_required.get("required_count"))
    if status_required_count is None or status_required_count <= 0:
        failures.append("status_required_evidence_required_count_invalid")
        status_required_count = 0
    stage1_deferred_count = _int(stage1.get("runtime_gate_evidence_deferred_count"))
    if stage1_deferred_count is None or stage1_deferred_count < 0:
        failures.append("runner_stage1_runtime_gate_evidence_deferred_count_invalid")
        stage1_deferred_count = 0
    expected_stage1 = {
        "passed": True,
        "required_evidence_present_count": max(
            status_required_count - stage1_deferred_count, 0
        ),
        "required_evidence_passed_count": max(
            status_required_count - stage1_deferred_count, 0
        ),
        "required_evidence_required_count": status_required_count,
        "runtime_gate_evidence_deferred_count": 1,
        "strict_default_gate_evidence_deferred_count": 1,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    expected_final = {
        "passed": True,
        "required_evidence_present_count": status_required_count,
        "required_evidence_passed_count": status_required_count,
        "required_evidence_required_count": status_required_count,
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
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
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    for key, expected in expected_status.items():
        if status.get(key) != expected:
            failures.append(f"status_{key}_mismatch")
    expected_required = {
        "present_count": status_required_count,
        "passed_count": status_required_count,
        "required_count": status_required_count,
        "passed": True,
    }
    for key, expected in expected_required.items():
        if status_required.get(key) != expected:
            failures.append(f"status_required_evidence_{key}_mismatch")

    stub = runner.get("stub_summary")
    if not isinstance(stub, dict):
        failures.append("runner_stub_summary_missing")
        stub = {}
    if stub.get("passed") is not True or stub.get("ok") is not True:
        failures.append("runner_stub_not_passed")
    row_count = _int(stub.get("row_count"))
    row_ok_count = _int(stub.get("row_ok_count"))
    if row_count is None or row_count <= 0:
        failures.append("runner_stub_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("runner_stub_row_ok_count_mismatch")
    expected_stub = {
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    for key, expected in expected_stub.items():
        if stub.get(key) != expected:
            failures.append(f"runner_stub_{key}_mismatch")

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_online_native_stub_canary_artifacts(
        root=args.root,
        runner_json=args.runner_json,
        preflight_json=args.preflight_json,
        status_json=args.status_json,
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
