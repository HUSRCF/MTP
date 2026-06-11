from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_lab_gate_verify import (
    _build_parser,
    _load_status,
    _status_failures,
    main,
    run_verify,
)


def _passing_lab_gate_statuses() -> dict[str, dict]:
    return {
        "default_closure": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
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
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
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
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
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
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
        "wna16_side_consumer_variant": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "require_wna16_side_consumer_variant_execution": True,
            "wna16_side_consumer_variant_execution_checked": True,
            "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
            "wna16_side_consumer_variant_execution_row_count": 1841,
            "wna16_side_consumer_variant_execution_row_ok_count": 1841,
            "wna16_side_consumer_variant_execution_error_count": 0,
            "wna16_side_consumer_variant_execution_payload_bytes": 0,
            "wna16_side_consumer_variant_execution_passed_to_kernel": False,
            "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
            "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
            "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
            "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
            "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
                "9748c8c92c02281b"
            ),
        },
    }


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
            "--window-sweep-json",
            str(tmp_path / "window_sweep.json"),
            "--window-sweep-check-json",
            str(tmp_path / "window_sweep.check.json"),
            "--all-field-window-sweep-json",
            str(tmp_path / "all_field_window_sweep.json"),
            "--all-field-window-sweep-check-json",
            str(tmp_path / "all_field_window_sweep.check.json"),
            "--wna16-side-variant-json",
            str(tmp_path / "wna16_side_variant.json"),
            "--wna16-side-variant-stub-json",
            str(tmp_path / "wna16_side_variant.stub.json"),
            "--wna16-side-variant-merged-json",
            str(tmp_path / "wna16_side_variant.merged.json"),
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
        "window_sweep",
        "window_sweep_check",
        "all_field_window_sweep",
        "all_field_window_sweep_check",
        "wna16_side_consumer_variant",
    ]
    tail_cmd = result["steps"]["tail_window_closure_check"]["cmd"]
    assert "--require-tail-window-probe" in tail_cmd
    assert "--expected-tail-window-size" in tail_cmd
    assert "8" in tail_cmd
    sweep_cmd = result["steps"]["window_sweep"]["cmd"]
    assert "scripts/run_premap_online_merged_native_arg_slot_window_sweep.py" in sweep_cmd
    assert "--window-size" in sweep_cmd
    assert "--require-program-view-ptr-abi" in sweep_cmd
    assert "--require-launch-envelope-args-ptr-abi" in sweep_cmd
    assert "--require-kernel-launch-descriptor-abi" in sweep_cmd
    assert "512" in sweep_cmd
    sweep_check_cmd = result["steps"]["window_sweep_check"]["cmd"]
    assert "scripts/check_premap_online_merged_native_arg_slot_window_sweep.py" in (
        sweep_check_cmd
    )
    assert "--expected-window-size" in sweep_check_cmd
    assert "--require-child-program-view-ptr-abi" in sweep_check_cmd
    assert "--require-child-kernel-arg-packet-abi" in sweep_check_cmd
    assert "--require-child-kernel-entry-args-abi" in sweep_check_cmd
    assert "--require-child-kernel-entry-args-ptr-abi" in sweep_check_cmd
    assert "--require-child-launch-envelope-args-ptr-abi" in sweep_check_cmd
    assert "--require-child-kernel-launch-descriptor-abi" in sweep_check_cmd
    all_field_cmd = result["steps"]["all_field_window_sweep"]["cmd"]
    assert (
        "scripts/run_premap_online_merged_native_arg_slot_all_field_window_sweep.py"
        in all_field_cmd
    )
    assert "--require-program-view-ptr-abi" in all_field_cmd
    assert "--require-kernel-arg-packet-abi" in all_field_cmd
    assert "--require-kernel-entry-args-abi" in all_field_cmd
    assert "--require-kernel-entry-args-ptr-abi" in all_field_cmd
    all_field_check_cmd = result["steps"]["all_field_window_sweep_check"]["cmd"]
    assert (
        "scripts/check_premap_online_merged_native_arg_slot_all_field_window_sweep.py"
        in all_field_check_cmd
    )
    assert "--require-child-program-view-ptr-abi" in all_field_check_cmd
    assert "--require-child-kernel-arg-packet-abi" in all_field_check_cmd
    assert "--require-child-kernel-entry-args-abi" in all_field_check_cmd
    assert "--require-child-kernel-entry-args-ptr-abi" in all_field_check_cmd
    wna16_side_cmd = result["steps"]["wna16_side_consumer_variant"]["cmd"]
    assert "scripts/run_premap_online_merged_native_arg_slot_canary.py" in (
        wna16_side_cmd
    )
    assert "--require-wna16-side-consumer-variant-execution" in wna16_side_cmd
    assert "--min-total-rows" in wna16_side_cmd
    assert "1024" in wna16_side_cmd
    assert "--block-threads" in wna16_side_cmd
    assert "256" in wna16_side_cmd


def test_status_failures_reject_wna16_side_variant_without_execution_gate():
    statuses = _passing_lab_gate_statuses()
    statuses["wna16_side_consumer_variant"][
        "require_wna16_side_consumer_variant_execution"
    ] = False

    failures = _status_failures(statuses)

    assert failures == ["wna16_side_variant_did_not_require_execution"]


def test_status_failures_precisely_reject_window_checker_without_entry_args_ptr_gate():
    statuses = _passing_lab_gate_statuses()
    statuses["window_sweep_check"]["require_child_kernel_entry_args_ptr_abi"] = False

    failures = _status_failures(statuses)

    assert failures == [
        "window_sweep_check_did_not_require_kernel_entry_args_ptr_abi"
    ]


def test_status_failures_precisely_reject_window_checker_without_launch_envelope_ptr_gate():
    statuses = _passing_lab_gate_statuses()
    statuses["window_sweep_check"][
        "require_child_launch_envelope_args_ptr_abi"
    ] = False

    failures = _status_failures(statuses)

    assert failures == [
        "window_sweep_check_did_not_require_launch_envelope_args_ptr_abi"
    ]


def test_status_failures_precisely_reject_window_checker_without_kernel_launch_descriptor_gate():
    statuses = _passing_lab_gate_statuses()
    statuses["window_sweep_check"][
        "require_child_kernel_launch_descriptor_abi"
    ] = False

    failures = _status_failures(statuses)

    assert failures == [
        "window_sweep_check_did_not_require_kernel_launch_descriptor_abi"
    ]


def test_status_failures_precisely_reject_all_field_checker_without_entry_args_ptr_gate():
    statuses = _passing_lab_gate_statuses()
    statuses["all_field_window_sweep_check"][
        "require_child_kernel_entry_args_ptr_abi"
    ] = False

    failures = _status_failures(statuses)

    assert failures == [
        "all_field_window_sweep_check_did_not_require_kernel_entry_args_ptr_abi"
    ]


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
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "default_closure_passed_to_kernel_mismatch" in failures


def test_status_failures_reject_default_closure_without_invocation_abi():
    statuses = _passing_lab_gate_statuses()
    statuses["default_closure"]["arg_slot_runner_require_kernel_invocation_abi"] = False
    statuses["default_closure"]["arg_slot_runner_kernel_invocation_checked"] = False

    failures = _status_failures(statuses)

    assert (
        "default_closure_arg_slot_runner_require_kernel_invocation_abi_mismatch"
        in failures
    )
    assert (
        "default_closure_arg_slot_runner_kernel_invocation_checked_mismatch"
        in failures
    )


def test_status_failures_reject_default_closure_without_endpoint_abi():
    statuses = _passing_lab_gate_statuses()
    statuses["default_closure"]["arg_slot_runner_require_kernel_endpoint_abi"] = False
    statuses["default_closure"]["arg_slot_runner_kernel_endpoint_checked"] = False

    failures = _status_failures(statuses)

    assert (
        "default_closure_arg_slot_runner_require_kernel_endpoint_abi_mismatch"
        in failures
    )
    assert (
        "default_closure_arg_slot_runner_kernel_endpoint_checked_mismatch"
        in failures
    )


def test_status_failures_reject_invalid_default_closure_packet_depth():
    statuses = _passing_lab_gate_statuses()
    statuses["default_closure"][
        "arg_slot_runner_kernel_launch_context_packet_chain_depth"
    ] = False
    statuses["default_closure"]["arg_slot_runner_kernel_invocation_packet_chain_depth"] = 0
    statuses["default_closure"][
        "arg_slot_runner_kernel_invocation_entry_packet_chain_depth"
    ] = None
    statuses["default_closure"]["arg_slot_runner_kernel_endpoint_packet_chain_depth"] = -1

    failures = _status_failures(statuses)

    assert (
        "default_closure_arg_slot_runner_kernel_launch_context_packet_chain_depth_invalid"
        in failures
    )
    assert (
        "default_closure_arg_slot_runner_kernel_invocation_packet_chain_depth_invalid"
        in failures
    )
    assert (
        "default_closure_arg_slot_runner_kernel_invocation_entry_packet_chain_depth_invalid"
        in failures
    )
    assert (
        "default_closure_arg_slot_runner_kernel_endpoint_packet_chain_depth_invalid"
        in failures
    )


def test_load_status_flattens_default_closure_invocation_summary(tmp_path: Path):
    path = tmp_path / "closure.json"
    path.write_text(
        json.dumps(
            {
                "passed": True,
                "failures": [],
                "source": "premap_lab_gate_closure",
                "payload_bytes": 0,
                "passed_to_kernel": False,
                "changes_kernel_launch_args": False,
                "summaries": {
                    "arg_slot_runner": {
                        "require_kernel_invocation_abi": True,
                        "require_kernel_endpoint_abi": True,
                        "require_kernel_endpoint_ptr_abi": True,
                        "kernel_invocation_checked": True,
                        "kernel_invocation_all_handle_fields_read": True,
                        "kernel_invocation_packet_chain_depth": 11,
                        "kernel_endpoint_checked": True,
                        "kernel_endpoint_all_handle_fields_read": True,
                        "kernel_endpoint_packet_chain_depth": 12,
                        "kernel_endpoint_ptr_checked": True,
                        "kernel_endpoint_ptr_all_handle_fields_read": True,
                        "kernel_endpoint_ptr_packet_chain_depth": 13,
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    status = _load_status(path)

    assert status["arg_slot_runner_require_kernel_invocation_abi"] is True
    assert status["arg_slot_runner_kernel_invocation_checked"] is True
    assert status["arg_slot_runner_kernel_invocation_all_handle_fields_read"] is True
    assert status["arg_slot_runner_kernel_invocation_packet_chain_depth"] == 11
    assert status["arg_slot_runner_require_kernel_endpoint_abi"] is True
    assert status["arg_slot_runner_kernel_endpoint_checked"] is True
    assert status["arg_slot_runner_kernel_endpoint_all_handle_fields_read"] is True
    assert status["arg_slot_runner_kernel_endpoint_packet_chain_depth"] == 12
    assert status["arg_slot_runner_require_kernel_endpoint_ptr_abi"] is True
    assert status["arg_slot_runner_kernel_endpoint_ptr_checked"] is True
    assert (
        status["arg_slot_runner_kernel_endpoint_ptr_all_handle_fields_read"] is True
    )
    assert status["arg_slot_runner_kernel_endpoint_ptr_packet_chain_depth"] == 13


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
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "tail_window_closure_check_did_not_require_tail_window" in failures


def test_status_failures_reject_window_sweep_checker_without_child_artifacts():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": False,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "window_sweep_check_did_not_require_child_artifacts" in failures


def test_status_failures_reject_window_sweep_checker_without_consumer_view():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": False,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "window_sweep_check_did_not_require_child_consumer_view" in failures


def test_status_failures_reject_window_sweep_checker_without_consumer_view_layout():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": False,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "window_sweep_check_did_not_require_child_consumer_view_layout" in failures


def test_status_failures_reject_window_sweep_checker_without_consumer_view_row_layout():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": False,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "window_sweep_check_did_not_require_child_consumer_view_row_layout" in failures


def test_status_failures_reject_window_sweep_checker_without_nondegenerate_gate():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": False,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "window_sweep_check_did_not_require_non_degenerate_windows" in failures


def test_status_failures_reject_all_field_checker_without_child_checks():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": False,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert "all_field_window_sweep_check_did_not_require_child_checks" in failures


def test_status_failures_reject_all_field_checker_without_consumer_view():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": False,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert (
        "all_field_window_sweep_check_did_not_require_child_consumer_view"
        in failures
    )


def test_status_failures_reject_all_field_checker_without_consumer_view_layout():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": False,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert (
        "all_field_window_sweep_check_did_not_require_child_consumer_view_layout"
        in failures
    )


def test_status_failures_reject_all_field_checker_without_consumer_view_row_layout():
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
            "require_tail_window_probe": True,
        },
        "window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_artifacts": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": True,
            "require_child_consumer_view_handle_projection": True,
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_row_metadata": True,
            "require_non_degenerate_windows": True,
            "expected_window_size": 512,
            "windows_checked": ["full", "head", "middle", "tail"],
        },
        "all_field_window_sweep": {
            "exists": True,
            "passed": True,
            "failures": [],
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "all_field_window_sweep_check": {
            "exists": True,
            "passed": True,
            "failures": [],
            "require_child_checks": True,
            "require_child_field_masks": True,
            "require_child_consumer_view": True,
            "require_child_consumer_view_layout": True,
            "require_child_consumer_view_row_layout": False,
            "expected_window_size": 512,
            "mirror_fields_checked": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
        },
    }

    failures = _status_failures(statuses)

    assert (
        "all_field_window_sweep_check_did_not_require_child_consumer_view_row_layout"
        in failures
    )


def test_run_premap_lab_gate_verify_main_writes_report(tmp_path: Path):
    output_json = tmp_path / "verify.json"

    exit_code = main(["--dry-run", "--output-json", str(output_json)])

    assert exit_code == 0
    result = json.loads(output_json.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["source"] == "premap_lab_gate_verify"
    assert result["dry_run"] is True
