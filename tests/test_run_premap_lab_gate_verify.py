from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_lab_gate_verify import (
    _build_parser,
    _status_failures,
    main,
    run_verify,
)


def test_run_premap_lab_gate_verify_dry_run_records_all_steps(tmp_path: Path):
    args = _build_parser().parse_args(
        [
            "--dry-run",
            "--closure-json",
            str(tmp_path / "closure.json"),
            "--closure-check-json",
            str(tmp_path / "closure.check.json"),
            "--tail-closure-json",
            str(tmp_path / "tail.json"),
            "--tail-closure-check-json",
            str(tmp_path / "tail.check.json"),
            "--tail-window-size",
            "8",
        ]
    )

    result = run_verify(args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["tail_window_size"] == 8
    assert list(result["steps"]) == [
        "default_closure",
        "default_closure_check",
        "tail_window_closure",
        "tail_window_closure_check",
    ]
    tail_cmd = result["steps"]["tail_window_closure_check"]["cmd"]
    assert "--require-tail-window-probe" in tail_cmd
    assert "--expected-tail-window-size" in tail_cmd
    assert "8" in tail_cmd


def test_status_failures_reject_kernel_boundary_mutation():
    statuses = {
        "default_closure": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": True,
            "changes_kernel_launch_args": False,
            "tail_window_probe_enabled": False,
        },
        "default_closure_check": {
            "exists": True,
            "passed": True,
            "failures": [],
        },
        "tail_window_closure": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "tail_window_probe_enabled": True,
        },
        "tail_window_closure_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_tail_window_probe": True,
        },
    }

    failures = _status_failures(statuses)

    assert "default_closure_passed_to_kernel_mismatch" in failures


def test_status_failures_reject_tail_checker_without_tail_requirement():
    statuses = {
        "default_closure": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "tail_window_probe_enabled": False,
        },
        "default_closure_check": {
            "exists": True,
            "passed": True,
            "failures": [],
        },
        "tail_window_closure": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "tail_window_probe_enabled": True,
        },
        "tail_window_closure_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_tail_window_probe": False,
        },
    }

    failures = _status_failures(statuses)

    assert "tail_window_closure_check_did_not_require_tail_window" in failures


def test_run_premap_lab_gate_verify_main_writes_report(tmp_path: Path):
    output_json = tmp_path / "verify.json"

    exit_code = main(["--dry-run", "--output-json", str(output_json)])

    assert exit_code == 0
    result = json.loads(output_json.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["source"] == "premap_lab_gate_verify"
    assert result["dry_run"] is True
