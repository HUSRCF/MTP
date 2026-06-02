from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_lab_gate_verify import (
    REQUIRED_STEPS,
    check_lab_gate_verify_artifact,
    main,
)


def _status_payload(name: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "exists": True,
        "passed": True,
        "failures": [],
        "source": name,
    }
    if name in {"default_closure", "tail_window_closure", "window_sweep"}:
        payload.update(
            {
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
            }
        )
    if name == "default_closure":
        payload["tail_window_probe_enabled"] = False
    if name == "tail_window_closure":
        payload["tail_window_probe_enabled"] = True
    if name == "tail_window_closure_check":
        payload["require_tail_window_probe"] = True
    if name == "window_sweep_check":
        payload.update(
            {
                "expected_window_size": 512,
                "require_child_artifacts": True,
                "require_non_degenerate_windows": True,
                "windows_checked": ["full", "head", "middle", "tail"],
            }
        )
    return payload


def _write_verify(path: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "passed": True,
        "failures": [],
        "source": "premap_lab_gate_verify",
        "dry_run": False,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "steps": {
            name: {"returncode": 0, "dry_run": False, "cmd": ["python", name]}
            for name in REQUIRED_STEPS
        },
        "statuses": {name: _status_payload(name) for name in REQUIRED_STEPS},
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return payload


def test_lab_gate_verify_check_accepts_valid_artifact(tmp_path: Path):
    path = tmp_path / "verify.json"
    _write_verify(path)

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["required_steps"] == list(REQUIRED_STEPS)


def test_lab_gate_verify_check_rejects_kernel_boundary_mutation(tmp_path: Path):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_sweep = statuses["window_sweep"]
    assert isinstance(window_sweep, dict)
    window_sweep["passed_to_kernel"] = True
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_passed_to_kernel_mismatch" in result["failures"]


def test_lab_gate_verify_check_rejects_window_checker_without_child_artifacts(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_artifacts"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_child_artifacts" in result["failures"]


def test_lab_gate_verify_check_rejects_window_checker_without_nondegenerate_gate(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_non_degenerate_windows"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_non_degenerate_windows" in result[
        "failures"
    ]


def test_lab_gate_verify_check_cli_writes_output(tmp_path: Path):
    path = tmp_path / "verify.json"
    output = tmp_path / "check.json"
    _write_verify(path)

    exit_code = main([str(path), "--output-json", str(output)])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == "premap_lab_gate_verify_check"
    assert payload["passed"] is True
