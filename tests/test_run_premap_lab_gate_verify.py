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
            "--window-sweep-json",
            str(tmp_path / "window_sweep.json"),
            "--window-sweep-check-json",
            str(tmp_path / "window_sweep.check.json"),
            "--all-field-window-sweep-json",
            str(tmp_path / "all_field_window_sweep.json"),
            "--all-field-window-sweep-check-json",
            str(tmp_path / "all_field_window_sweep.check.json"),
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
    ]
    tail_cmd = result["steps"]["tail_window_closure_check"]["cmd"]
    assert "--require-tail-window-probe" in tail_cmd
    assert "--expected-tail-window-size" in tail_cmd
    assert "8" in tail_cmd
    sweep_cmd = result["steps"]["window_sweep"]["cmd"]
    assert "scripts/run_premap_online_merged_native_arg_slot_window_sweep.py" in sweep_cmd
    assert "--window-size" in sweep_cmd
    assert "512" in sweep_cmd
    sweep_check_cmd = result["steps"]["window_sweep_check"]["cmd"]
    assert "scripts/check_premap_online_merged_native_arg_slot_window_sweep.py" in (
        sweep_check_cmd
    )
    assert "--expected-window-size" in sweep_check_cmd
    all_field_cmd = result["steps"]["all_field_window_sweep"]["cmd"]
    assert (
        "scripts/run_premap_online_merged_native_arg_slot_all_field_window_sweep.py"
        in all_field_cmd
    )
    all_field_check_cmd = result["steps"]["all_field_window_sweep_check"]["cmd"]
    assert (
        "scripts/check_premap_online_merged_native_arg_slot_all_field_window_sweep.py"
        in all_field_check_cmd
    )


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
