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
    if name in {
        "default_closure",
        "tail_window_closure",
        "window_sweep",
        "all_field_window_sweep",
    }:
        payload.update(
            {
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
            }
        )
    if name == "default_closure":
        payload.update(
            {
                "tail_window_probe_enabled": False,
                "arg_slot_runner_require_kernel_launch_context_abi": True,
                "arg_slot_runner_require_kernel_invocation_abi": True,
                "arg_slot_runner_kernel_launch_context_checked": True,
                "arg_slot_runner_kernel_launch_context_all_handle_fields_read": True,
                "arg_slot_runner_kernel_launch_context_packet_chain_depth": 10,
                "arg_slot_runner_kernel_launch_context_payload_bytes": 0,
                "arg_slot_runner_kernel_launch_context_passed_to_kernel": False,
                "arg_slot_runner_kernel_launch_context_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_launch_context_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_launch_context_current_wna16_arg_compatible": False,
                "arg_slot_runner_kernel_invocation_checked": True,
                "arg_slot_runner_kernel_invocation_all_handle_fields_read": True,
                "arg_slot_runner_kernel_invocation_packet_chain_depth": 11,
                "arg_slot_runner_kernel_invocation_payload_bytes": 0,
                "arg_slot_runner_kernel_invocation_passed_to_kernel": False,
                "arg_slot_runner_kernel_invocation_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_invocation_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_invocation_current_wna16_arg_compatible": False,
            }
        )
    if name == "tail_window_closure":
        payload["tail_window_probe_enabled"] = True
    if name == "tail_window_closure_check":
        payload["require_tail_window_probe"] = True
    if name == "window_sweep_check":
        payload.update(
            {
                "expected_window_size": 512,
                "require_child_artifacts": True,
                "require_child_field_masks": True,
                "require_child_consumer_view": True,
                "require_child_consumer_view_layout": True,
                "require_child_consumer_view_row_layout": True,
                "require_child_consumer_view_handle_projection": True,
                "require_child_program_view_ptr_abi": True,
                "require_child_kernel_arg_packet_abi": True,
                "require_child_kernel_entry_args_abi": True,
                "require_child_kernel_entry_args_ptr_abi": True,
                "require_child_launch_envelope_args_ptr_abi": True,
                "require_child_kernel_launch_descriptor_abi": True,
                "require_child_kernel_entry_row_metadata": True,
                "require_non_degenerate_windows": True,
                "windows_checked": ["full", "head", "middle", "tail"],
            }
        )
    if name == "all_field_window_sweep_check":
        payload.update(
            {
                "expected_window_size": 512,
                "require_child_checks": True,
                "require_child_field_masks": True,
                "require_child_consumer_view": True,
                "require_child_consumer_view_layout": True,
                "require_child_consumer_view_row_layout": True,
                "require_child_consumer_view_handle_projection": True,
                "require_child_program_view_ptr_abi": True,
                "require_child_kernel_arg_packet_abi": True,
                "require_child_kernel_entry_args_abi": True,
                "require_child_kernel_entry_args_ptr_abi": True,
                "require_child_kernel_entry_row_metadata": True,
                "mirror_fields_checked": [
                    "descriptor_ptr",
                    "packed_weight_descriptor",
                    "scale_metadata_handle",
                    "aux_metadata_handle",
                ],
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


def test_lab_gate_verify_check_rejects_default_closure_without_invocation_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    default_closure = statuses["default_closure"]
    assert isinstance(default_closure, dict)
    default_closure["arg_slot_runner_require_kernel_invocation_abi"] = False
    default_closure["arg_slot_runner_kernel_invocation_checked"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "default_closure_arg_slot_runner_require_kernel_invocation_abi_mismatch"
        in result["failures"]
    )
    assert (
        "default_closure_arg_slot_runner_kernel_invocation_checked_mismatch"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_invalid_default_closure_packet_depth(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    default_closure = statuses["default_closure"]
    assert isinstance(default_closure, dict)
    default_closure[
        "arg_slot_runner_kernel_launch_context_packet_chain_depth"
    ] = False
    default_closure["arg_slot_runner_kernel_invocation_packet_chain_depth"] = 0
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "default_closure_arg_slot_runner_kernel_launch_context_packet_chain_depth_invalid"
        in result["failures"]
    )
    assert (
        "default_closure_arg_slot_runner_kernel_invocation_packet_chain_depth_invalid"
        in result["failures"]
    )


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


def test_lab_gate_verify_check_rejects_window_checker_without_consumer_view(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_consumer_view"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_child_consumer_view" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_window_checker_without_consumer_view_layout(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_consumer_view_layout"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_child_consumer_view_layout" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_window_checker_without_consumer_view_row_layout(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_consumer_view_row_layout"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "window_sweep_check_did_not_require_child_consumer_view_row_layout"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_window_checker_without_consumer_view_handle_projection(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_consumer_view_handle_projection"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "window_sweep_check_did_not_require_child_consumer_view_handle_projection"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_window_checker_without_program_view_ptr_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_program_view_ptr_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_program_view_ptr_abi" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_window_checker_without_kernel_arg_packet_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_kernel_arg_packet_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_kernel_arg_packet_abi" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_window_checker_without_kernel_entry_args_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_kernel_entry_args_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_kernel_entry_args_abi" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_window_checker_without_kernel_entry_args_ptr_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_kernel_entry_args_ptr_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "window_sweep_check_did_not_require_kernel_entry_args_ptr_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_window_checker_without_launch_envelope_args_ptr_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_launch_envelope_args_ptr_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "window_sweep_check_did_not_require_launch_envelope_args_ptr_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_window_checker_without_kernel_launch_descriptor_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_kernel_launch_descriptor_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "window_sweep_check_did_not_require_kernel_launch_descriptor_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_window_checker_without_kernel_entry_row_metadata(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    window_check = statuses["window_sweep_check"]
    assert isinstance(window_check, dict)
    window_check["require_child_kernel_entry_row_metadata"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "window_sweep_check_did_not_require_kernel_entry_row_metadata" in result[
        "failures"
    ]


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


def test_lab_gate_verify_check_rejects_all_field_checker_without_child_checks(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_checks"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "all_field_window_sweep_check_did_not_require_child_checks" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_all_field_checker_without_consumer_view(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_consumer_view"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "all_field_window_sweep_check_did_not_require_child_consumer_view" in result[
        "failures"
    ]


def test_lab_gate_verify_check_rejects_all_field_checker_without_consumer_view_layout(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_consumer_view_layout"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_child_consumer_view_layout"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_consumer_view_row_layout(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_consumer_view_row_layout"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_child_consumer_view_row_layout"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_consumer_view_handle_projection(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_consumer_view_handle_projection"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_child_consumer_view_handle_projection"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_program_view_ptr_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_program_view_ptr_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_program_view_ptr_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_kernel_arg_packet_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_kernel_arg_packet_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_kernel_arg_packet_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_kernel_entry_args_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_kernel_entry_args_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_kernel_entry_args_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_kernel_entry_args_ptr_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_kernel_entry_args_ptr_abi"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_kernel_entry_args_ptr_abi"
        in result["failures"]
    )


def test_lab_gate_verify_check_rejects_all_field_checker_without_kernel_entry_row_metadata(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    all_field_check = statuses["all_field_window_sweep_check"]
    assert isinstance(all_field_check, dict)
    all_field_check["require_child_kernel_entry_row_metadata"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "all_field_window_sweep_check_did_not_require_kernel_entry_row_metadata"
        in result["failures"]
    )


def test_lab_gate_verify_check_cli_writes_output(tmp_path: Path):
    path = tmp_path / "verify.json"
    output = tmp_path / "check.json"
    _write_verify(path)

    exit_code = main([str(path), "--output-json", str(output)])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == "premap_lab_gate_verify_check"
    assert payload["passed"] is True
