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
            "require_kernel_invocation_entry_abi": True,
            "require_kernel_endpoint_abi": True,
            "require_kernel_endpoint_ptr_abi": True,
            "kernel_launch_context_checked": True,
            "kernel_launch_context_all_handle_fields_read": True,
            "kernel_launch_context_error_count": 0,
            "kernel_launch_context_packet_chain_depth": 10,
            "kernel_launch_context_payload_bytes": 0,
            "kernel_launch_context_passed_to_kernel": False,
            "kernel_launch_context_kernel_arg_pass_allowed": False,
            "kernel_launch_context_changes_kernel_launch_args": False,
            "kernel_launch_context_current_wna16_arg_compatible": False,
            "kernel_launch_context_requires_wna16_arg_reinterpretation": False,
            "kernel_invocation_checked": True,
            "kernel_invocation_all_handle_fields_read": True,
            "kernel_invocation_error_count": 0,
            "kernel_invocation_packet_chain_depth": 11,
            "kernel_invocation_payload_bytes": 0,
            "kernel_invocation_passed_to_kernel": False,
            "kernel_invocation_kernel_arg_pass_allowed": False,
            "kernel_invocation_changes_kernel_launch_args": False,
            "kernel_invocation_current_wna16_arg_compatible": False,
            "kernel_invocation_requires_wna16_arg_reinterpretation": False,
            "kernel_invocation_entry_checked": True,
            "kernel_invocation_entry_all_handle_fields_read": True,
            "kernel_invocation_entry_error_count": 0,
            "kernel_invocation_entry_packet_chain_depth": 11,
            "kernel_invocation_entry_payload_bytes": 0,
            "kernel_invocation_entry_passed_to_kernel": False,
            "kernel_invocation_entry_kernel_arg_pass_allowed": False,
            "kernel_invocation_entry_changes_kernel_launch_args": False,
            "kernel_invocation_entry_current_wna16_arg_compatible": False,
            "kernel_invocation_entry_requires_wna16_arg_reinterpretation": False,
            "kernel_endpoint_checked": True,
            "kernel_endpoint_all_handle_fields_read": True,
            "kernel_endpoint_error_count": 0,
            "kernel_endpoint_packet_chain_depth": 12,
            "kernel_endpoint_payload_bytes": 0,
            "kernel_endpoint_passed_to_kernel": False,
            "kernel_endpoint_kernel_arg_pass_allowed": False,
            "kernel_endpoint_changes_kernel_launch_args": False,
            "kernel_endpoint_current_wna16_arg_compatible": False,
            "kernel_endpoint_requires_wna16_arg_reinterpretation": False,
            "kernel_endpoint_ptr_checked": True,
            "kernel_endpoint_ptr_all_handle_fields_read": True,
            "kernel_endpoint_ptr_error_count": 0,
            "kernel_endpoint_ptr_packet_chain_depth": 13,
            "kernel_endpoint_ptr_payload_bytes": 0,
            "kernel_endpoint_ptr_payload_deref_allowed": False,
            "kernel_endpoint_ptr_passed_to_kernel": False,
            "kernel_endpoint_ptr_kernel_arg_pass_allowed": False,
            "kernel_endpoint_ptr_changes_kernel_launch_args": False,
            "kernel_endpoint_ptr_current_wna16_arg_compatible": False,
            "kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
            "kernel_endpoint_ptr_row_hash_accumulator": "row-hash",
            "kernel_endpoint_ptr_field_read_hash_accumulator": "field-hash",
            "kernel_endpoint_ptr_row_metadata_hash_accumulator": "metadata-hash",
            "stub_requested_macros": [
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_LAUNCH_CONTEXT_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_INVOCATION_ENTRY_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI",
                "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_PTR_ABI",
            ],
            "stub_requested_macros_source": "stub_summary",
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
        "paths": {"arg_slot_runner_json": "arg_slot_runner.json"},
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


def test_check_closure_artifact_accepts_reused_arg_slot_runner(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["arg_slot_runner_reused"] = True
    payload["steps"]["arg_slot_runner"] = {
        "cmd": [],
        "returncode": 0,
        "dry_run": False,
        "skipped": True,
        "reuse_existing_artifact": True,
        "reason": "skip_arg_slot_runner",
        "output_json": "arg_slot_runner.json",
    }
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is True
    assert result["failures"] == []


def test_check_closure_artifact_rejects_unmarked_arg_slot_runner_skip(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["steps"]["arg_slot_runner"] = {
        "cmd": [],
        "returncode": 0,
        "dry_run": False,
        "skipped": True,
        "reason": "manual_skip",
    }
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "step_arg_slot_runner_unexpected_skip" in result["failures"]


def test_check_closure_artifact_rejects_reused_arg_slot_runner_path_mismatch(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["arg_slot_runner_reused"] = True
    payload["steps"]["arg_slot_runner"] = {
        "cmd": [],
        "returncode": 0,
        "dry_run": False,
        "skipped": True,
        "reuse_existing_artifact": True,
        "reason": "skip_arg_slot_runner",
        "output_json": "other_arg_slot_runner.json",
    }
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "step_arg_slot_runner_output_json_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_reused_arg_slot_runner_missing_path(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["arg_slot_runner_reused"] = True
    payload.pop("paths")
    payload["steps"]["arg_slot_runner"] = {
        "cmd": [],
        "returncode": 0,
        "dry_run": False,
        "skipped": True,
        "reuse_existing_artifact": True,
        "reason": "skip_arg_slot_runner",
    }
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "step_arg_slot_runner_output_json_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_reused_arg_slot_runner_nonempty_cmd(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["arg_slot_runner_reused"] = True
    payload["steps"]["arg_slot_runner"] = {
        "cmd": ["python", "runner.py"],
        "returncode": 0,
        "dry_run": False,
        "skipped": True,
        "reuse_existing_artifact": True,
        "reason": "skip_arg_slot_runner",
        "output_json": "arg_slot_runner.json",
    }
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "step_arg_slot_runner_cmd_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_reused_arg_slot_runner_without_flag(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["steps"]["arg_slot_runner"] = {
        "cmd": [],
        "returncode": 0,
        "dry_run": False,
        "skipped": True,
        "reuse_existing_artifact": True,
        "reason": "skip_arg_slot_runner",
        "output_json": "arg_slot_runner.json",
    }
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "step_arg_slot_runner_reused_flag_mismatch" in result["failures"]


def test_check_closure_artifact_accepts_top_level_endpoint_stub_macro_source(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"]["stub_requested_macros_source"] = "top_level"
    _write_json(path, payload)

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


def test_check_closure_artifact_rejects_missing_endpoint_abi(tmp_path: Path):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"]["require_kernel_endpoint_abi"] = False
    payload["summaries"]["arg_slot_runner"]["kernel_endpoint_checked"] = False
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert (
        "arg_slot_runner_require_kernel_endpoint_abi_mismatch"
        in result["failures"]
    )
    assert "arg_slot_runner_kernel_endpoint_checked_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_missing_endpoint_ptr_abi(tmp_path: Path):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"]["require_kernel_endpoint_ptr_abi"] = False
    payload["summaries"]["arg_slot_runner"]["kernel_endpoint_ptr_checked"] = False
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert (
        "arg_slot_runner_require_kernel_endpoint_ptr_abi_mismatch"
        in result["failures"]
    )
    assert "arg_slot_runner_kernel_endpoint_ptr_checked_mismatch" in result["failures"]


def test_check_closure_artifact_rejects_missing_endpoint_stub_macro(tmp_path: Path):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    macros = payload["summaries"]["arg_slot_runner"]["stub_requested_macros"]
    assert isinstance(macros, list)
    macros.remove(
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
    )
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert (
        "arg_slot_runner_stub_requested_macro_missing:"
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_ENDPOINT_ABI"
        in result["failures"]
    )


def test_check_closure_artifact_rejects_missing_endpoint_stub_macro_source(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"].pop("stub_requested_macros_source")
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "arg_slot_runner_stub_requested_macros_source_invalid" in result["failures"]


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


def test_check_closure_artifact_rejects_endpoint_kernel_boundary_mutation(
    tmp_path: Path,
):
    path = tmp_path / "closure.json"
    payload = _closure_payload()
    payload["summaries"]["arg_slot_runner"]["kernel_endpoint_passed_to_kernel"] = True
    _write_json(path, payload)

    result = check_closure_artifact(path)

    assert result["passed"] is False
    assert "arg_slot_runner_kernel_endpoint_passed_to_kernel_mismatch" in result[
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
