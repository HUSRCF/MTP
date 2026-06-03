from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_lab_gate_closure import check_closure_artifact, main


def _summary(passed: bool = True) -> dict:
    return {"exists": True, "passed": passed, "failures": []}


def _arg_slot_runner_summary(passed: bool = True) -> dict:
    payload = _summary(passed=passed)
    payload.update(
        {
            "require_kernel_launch_context_abi": True,
            "require_kernel_invocation_abi": True,
            "kernel_launch_context_checked": True,
            "kernel_launch_context_all_handle_fields_read": True,
            "kernel_launch_context_packet_chain_depth": 10,
            "kernel_launch_context_payload_bytes": 0,
            "kernel_launch_context_passed_to_kernel": False,
            "kernel_launch_context_kernel_arg_pass_allowed": False,
            "kernel_launch_context_changes_kernel_launch_args": False,
            "kernel_launch_context_current_wna16_arg_compatible": False,
            "kernel_invocation_checked": True,
            "kernel_invocation_all_handle_fields_read": True,
            "kernel_invocation_packet_chain_depth": 11,
            "kernel_invocation_payload_bytes": 0,
            "kernel_invocation_passed_to_kernel": False,
            "kernel_invocation_kernel_arg_pass_allowed": False,
            "kernel_invocation_changes_kernel_launch_args": False,
            "kernel_invocation_current_wna16_arg_compatible": False,
        }
    )
    return payload


def _tail_summary() -> dict:
    return {
        "exists": True,
        "passed": True,
        "failures": [],
        "tail_window_size": 4,
        "merged_row_count": 16,
        "block_threads": 4,
        "dispatch_row_offset": 12,
        "dispatch_row_limit": 16,
        "dispatch_active_rows": 4,
        "dispatch_expected_program_count": 1,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
    }


def _closure_payload(*, tail: bool = False) -> dict:
    steps = {
        "arg_slot_runner": {"returncode": 0, "dry_run": False},
        "full_preflight": {"returncode": 0, "dry_run": False},
        "summary_preflight": {"returncode": 0, "dry_run": False},
        "summary_check": {"returncode": 0, "dry_run": False},
        "native_artifact_check": {"returncode": 0, "dry_run": False},
    }
    summaries = {
        "arg_slot_runner": _arg_slot_runner_summary(),
        "full_preflight": _summary(),
        "summary_preflight": _summary(),
        "summary_check": _summary(),
        "native_artifact_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "preflight_json_source": "runner_recorded",
            "status_json_source": "runner_recorded",
        },
    }
    if tail:
        steps["arg_slot_tail_window_runner"] = {
            "returncode": 0,
            "dry_run": False,
        }
        summaries["arg_slot_tail_window_runner"] = _tail_summary()
    return {
        "source": "premap_lab_gate_closure",
        "passed": True,
        "failures": [],
        "dry_run": False,
        "requires_runner_recorded_artifact_paths": True,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "steps": steps,
        "summaries": summaries,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_check_closure_artifact_accepts_default_closure(tmp_path: Path):
    path = tmp_path / "closure.json"
    _write_json(path, _closure_payload())

    result = check_closure_artifact(path)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_closure_artifact_rejects_explicit_artifact_paths(tmp_path: Path):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["native_artifact_check"][
        "preflight_json_source"
    ] = "explicit_arg"
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "native_artifact_check_preflight_source_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_missing_invocation_abi(tmp_path: Path):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"]["require_kernel_invocation_abi"] = False
    payload["summaries"]["arg_slot_runner"]["kernel_invocation_checked"] = False
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert (
        "arg_slot_runner_require_kernel_invocation_abi_mismatch"
        in result["failures"]
    )
    assert "arg_slot_runner_kernel_invocation_checked_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_invocation_kernel_boundary_mutation(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"]["kernel_invocation_passed_to_kernel"] = True
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "arg_slot_runner_kernel_invocation_passed_to_kernel_mismatch" in result[
        "failures"
    ]


def test_check_closure_artifact_rejects_invocation_launch_arg_mutation(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"][
        "kernel_invocation_changes_kernel_launch_args"
    ] = True
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert (
        "arg_slot_runner_kernel_invocation_changes_kernel_launch_args_mismatch"
        in result["failures"]
    )


def test_check_closure_artifact_rejects_context_launch_arg_mutation(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"][
        "kernel_launch_context_changes_kernel_launch_args"
    ] = True
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert (
        "arg_slot_runner_kernel_launch_context_changes_kernel_launch_args_mismatch"
        in result["failures"]
    )


def test_check_closure_artifact_accepts_tail_window_closure(tmp_path: Path):
    path = tmp_path / "closure.json"
    _write_json(path, _closure_payload(tail=True))

    result = check_closure_artifact(
        path,
        require_tail_window_probe=True,
        expected_tail_window_size=4,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_closure_artifact_rejects_missing_tail_window_when_required(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    _write_json(path, _closure_payload())

    result = check_closure_artifact(
        path,
        require_tail_window_probe=True,
        expected_tail_window_size=4,
    )

    assert result["passed"] is False
    assert "step_arg_slot_tail_window_runner_missing" in result["failures"]
    assert "arg_slot_tail_window_runner_missing" in result["failures"]


def test_check_closure_artifact_cli_writes_output(tmp_path: Path):
    path = tmp_path / "closure.json"
    output = tmp_path / "check.json"
    _write_json(path, _closure_payload(tail=True))

    exit_code = main(
        [
            str(path),
            "--require-tail-window-probe",
            "--expected-tail-window-size",
            "4",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["passed"] is True
