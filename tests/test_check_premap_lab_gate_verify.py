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
        "wna16_side_consumer_variant",
    }:
        payload.update(
            {
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
            }
        )
    if name == "wna16_side_consumer_variant":
        payload.update(
            {
                "require_wna16_side_consumer_variant_execution": True,
                "wna16_side_consumer_variant_execution_checked": True,
                "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
                "wna16_side_consumer_variant_execution_row_count": 1841,
                "wna16_side_consumer_variant_execution_row_ok_count": 1841,
                "wna16_side_consumer_variant_execution_error_count": 0,
                "wna16_side_consumer_variant_execution_payload_bytes": 0,
                "wna16_side_consumer_variant_execution_passed_to_kernel": False,
                "wna16_side_consumer_variant_execution_changes_kernel_launch_args": (
                    False
                ),
                "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": (
                    False
                ),
                "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": (
                    False
                ),
                "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": (
                    False
                ),
                "wna16_side_consumer_variant_execution_explicit_typed_abi_slot": True,
                "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_count": 1841,
                "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count": 1841,
                "wna16_side_consumer_variant_execution_descriptor_ptr_read_error_count": 0,
                "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_row_count": 1841,
                "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_row_ok_count": 1841,
                "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_error_count": 0,
                "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_count": 1841,
                "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_ok_count": 1841,
                "wna16_side_consumer_variant_execution_scale_metadata_handle_read_error_count": 0,
                "wna16_side_consumer_variant_execution_aux_metadata_handle_read_row_count": 1841,
                "wna16_side_consumer_variant_execution_aux_metadata_handle_read_row_ok_count": 1841,
                "wna16_side_consumer_variant_execution_aux_metadata_handle_read_error_count": 0,
                "wna16_side_consumer_variant_execution_hash_accumulator": (
                    "1112131415161718"
                ),
                "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
                    "9748c8c92c02281b"
                ),
                "wna16_side_consumer_variant_execution_descriptor_ptr_read_hash_accumulator": (
                    "3132333435363738"
                ),
                "wna16_side_consumer_variant_execution_packed_weight_descriptor_read_hash_accumulator": (
                    "4142434445464748"
                ),
                "wna16_side_consumer_variant_execution_scale_metadata_handle_read_hash_accumulator": (
                    "5152535455565758"
                ),
                "wna16_side_consumer_variant_execution_aux_metadata_handle_read_hash_accumulator": (
                    "6162636465666768"
                ),
            }
        )
    if name == "default_closure":
        payload.update(
            {
                "tail_window_probe_enabled": False,
                "arg_slot_runner_require_kernel_launch_context_abi": True,
                "arg_slot_runner_require_kernel_invocation_abi": True,
                "arg_slot_runner_require_kernel_invocation_entry_abi": True,
                "arg_slot_runner_require_kernel_endpoint_abi": True,
                "arg_slot_runner_require_kernel_endpoint_ptr_abi": True,
                "arg_slot_runner_kernel_launch_context_checked": True,
                "arg_slot_runner_kernel_launch_context_all_handle_fields_read": True,
                "arg_slot_runner_kernel_launch_context_error_count": 0,
                "arg_slot_runner_kernel_launch_context_packet_chain_depth": 10,
                "arg_slot_runner_kernel_launch_context_payload_bytes": 0,
                "arg_slot_runner_kernel_launch_context_passed_to_kernel": False,
                "arg_slot_runner_kernel_launch_context_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_launch_context_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_launch_context_current_wna16_arg_compatible": False,
                "arg_slot_runner_kernel_launch_context_requires_wna16_arg_reinterpretation": False,
                "arg_slot_runner_kernel_invocation_checked": True,
                "arg_slot_runner_kernel_invocation_all_handle_fields_read": True,
                "arg_slot_runner_kernel_invocation_error_count": 0,
                "arg_slot_runner_kernel_invocation_packet_chain_depth": 11,
                "arg_slot_runner_kernel_invocation_payload_bytes": 0,
                "arg_slot_runner_kernel_invocation_passed_to_kernel": False,
                "arg_slot_runner_kernel_invocation_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_invocation_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_invocation_current_wna16_arg_compatible": False,
                "arg_slot_runner_kernel_invocation_requires_wna16_arg_reinterpretation": False,
                "arg_slot_runner_kernel_invocation_entry_checked": True,
                "arg_slot_runner_kernel_invocation_entry_all_handle_fields_read": True,
                "arg_slot_runner_kernel_invocation_entry_error_count": 0,
                "arg_slot_runner_kernel_invocation_entry_packet_chain_depth": 11,
                "arg_slot_runner_kernel_invocation_entry_payload_bytes": 0,
                "arg_slot_runner_kernel_invocation_entry_passed_to_kernel": False,
                "arg_slot_runner_kernel_invocation_entry_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_invocation_entry_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_invocation_entry_current_wna16_arg_compatible": False,
                "arg_slot_runner_kernel_invocation_entry_requires_wna16_arg_reinterpretation": False,
                "arg_slot_runner_kernel_endpoint_checked": True,
                "arg_slot_runner_kernel_endpoint_all_handle_fields_read": True,
                "arg_slot_runner_kernel_endpoint_error_count": 0,
                "arg_slot_runner_kernel_endpoint_packet_chain_depth": 12,
                "arg_slot_runner_kernel_endpoint_payload_bytes": 0,
                "arg_slot_runner_kernel_endpoint_passed_to_kernel": False,
                "arg_slot_runner_kernel_endpoint_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_endpoint_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_endpoint_current_wna16_arg_compatible": False,
                "arg_slot_runner_kernel_endpoint_requires_wna16_arg_reinterpretation": False,
                "arg_slot_runner_kernel_endpoint_ptr_checked": True,
                "arg_slot_runner_kernel_endpoint_ptr_all_handle_fields_read": True,
                "arg_slot_runner_kernel_endpoint_ptr_error_count": 0,
                "arg_slot_runner_kernel_endpoint_ptr_packet_chain_depth": 13,
                "arg_slot_runner_kernel_endpoint_ptr_payload_bytes": 0,
                "arg_slot_runner_kernel_endpoint_ptr_passed_to_kernel": False,
                "arg_slot_runner_kernel_endpoint_ptr_kernel_arg_pass_allowed": False,
                "arg_slot_runner_kernel_endpoint_ptr_changes_kernel_launch_args": False,
                "arg_slot_runner_kernel_endpoint_ptr_current_wna16_arg_compatible": False,
                "arg_slot_runner_kernel_endpoint_ptr_requires_wna16_arg_reinterpretation": False,
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


def test_lab_gate_verify_check_rejects_refresh_required_artifact(tmp_path: Path):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    payload["reuse_artifact_refresh_required"] = True
    payload["reuse_artifact_refresh_reasons"] = ["tail_window_closure_not_passed"]
    payload["reuse_artifact_refresh_command"] = [
        "python",
        "scripts/run_premap_lab_gate_verify.py",
    ]
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "reuse_artifact_refresh_required_mismatch" in result["failures"]
    assert "reuse_artifact_refresh_reasons_not_empty" in result["failures"]
    assert "reuse_artifact_refresh_command_not_empty" in result["failures"]


def test_lab_gate_verify_check_rejects_wna16_side_variant_missing_gate(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    wna16_status = statuses["wna16_side_consumer_variant"]
    assert isinstance(wna16_status, dict)
    wna16_status["require_wna16_side_consumer_variant_execution"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert "wna16_side_variant_did_not_require_execution" in result["failures"]


def test_lab_gate_verify_check_rejects_wna16_side_variant_bad_stub_field(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    wna16_status = statuses["wna16_side_consumer_variant"]
    assert isinstance(wna16_status, dict)
    wna16_status[
        "wna16_side_consumer_variant_execution_scale_metadata_handle_read_row_ok_count"
    ] = 7
    wna16_status[
        "wna16_side_consumer_variant_execution_aux_metadata_handle_read_hash_accumulator"
    ] = "not_hex"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "wna16_side_variant_scale_metadata_handle_read_row_ok_count_mismatch"
        in result["failures"]
    )
    assert (
        "wna16_side_variant_aux_metadata_handle_read_hash_accumulator_invalid"
        in result["failures"]
    )


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


def test_lab_gate_verify_check_rejects_default_closure_without_endpoint_abi(
    tmp_path: Path,
):
    path = tmp_path / "verify.json"
    payload = _write_verify(path)
    statuses = payload["statuses"]
    assert isinstance(statuses, dict)
    default_closure = statuses["default_closure"]
    assert isinstance(default_closure, dict)
    default_closure["arg_slot_runner_require_kernel_endpoint_abi"] = False
    default_closure["arg_slot_runner_kernel_endpoint_checked"] = False
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = check_lab_gate_verify_artifact(path)

    assert result["passed"] is False
    assert (
        "default_closure_arg_slot_runner_require_kernel_endpoint_abi_mismatch"
        in result["failures"]
    )
    assert (
        "default_closure_arg_slot_runner_kernel_endpoint_checked_mismatch"
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
    default_closure[
        "arg_slot_runner_kernel_invocation_entry_packet_chain_depth"
    ] = None
    default_closure["arg_slot_runner_kernel_endpoint_packet_chain_depth"] = -1
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
    assert (
        "default_closure_arg_slot_runner_kernel_invocation_entry_packet_chain_depth_invalid"
        in result["failures"]
    )
    assert (
        "default_closure_arg_slot_runner_kernel_endpoint_packet_chain_depth_invalid"
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
