from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_lab_gate_closure import (
    _build_parser,
    _runner_recorded_path_failures,
    _tail_window_probe_failures,
    main,
    run_closure,
)


def test_run_premap_lab_gate_closure_defaults_use_endpoint_artifacts():
    args = _build_parser().parse_args([])

    assert args.arg_slot_runner_json.name == (
        "online_merged_future_native_endpoint_canary_runner.json"
    )
    assert args.arg_slot_stub_json.name == (
        "typed_consumer_stub_gpu1_online_merged_endpoint_canary.json"
    )
    assert args.arg_slot_merged_json.name == (
        "online_merged_prelaunch_typed_consumer_input_endpoint_canary.json"
    )


def test_run_premap_lab_gate_closure_dry_run_records_canonical_steps(
    tmp_path: Path,
):
    args = _build_parser().parse_args(
        [
            "--dry-run",
            "--arg-slot-runner-json",
            str(tmp_path / "arg_slot_runner.json"),
            "--arg-slot-stub-json",
            str(tmp_path / "arg_slot_stub.json"),
            "--arg-slot-merged-json",
            str(tmp_path / "arg_slot_merged.json"),
            "--native-runner-json",
            str(tmp_path / "native_runner.json"),
            "--full-preflight-json",
            str(tmp_path / "full_preflight.json"),
            "--summary-json",
            str(tmp_path / "summary.json"),
            "--summary-check-json",
            str(tmp_path / "summary.check.json"),
            "--artifact-check-json",
            str(tmp_path / "artifact_check.json"),
            "--output-json",
            str(tmp_path / "closure.json"),
        ]
    )

    result = run_closure(args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert list(result["steps"]) == [
        "arg_slot_runner",
        "full_preflight",
        "summary_preflight",
        "summary_check",
        "native_artifact_check",
    ]
    artifact_cmd = result["steps"]["native_artifact_check"]["cmd"]
    assert "scripts/check_premap_online_native_stub_canary_artifacts.py" in artifact_cmd
    assert "--preflight-json" not in artifact_cmd
    assert "--status-json" not in artifact_cmd
    assert "--runner-json" in artifact_cmd
    assert result["requires_runner_recorded_artifact_paths"] is True
    assert result["tail_window_probe_enabled"] is False
    arg_slot_cmd = result["steps"]["arg_slot_runner"]["cmd"]
    assert "--require-kernel-launch-context-abi" in arg_slot_cmd
    assert "--require-kernel-invocation-abi" in arg_slot_cmd
    assert "--require-kernel-endpoint-abi" in arg_slot_cmd


def test_runner_recorded_path_failures_reject_explicit_sources():
    summaries = {
        "native_artifact_check": {
            "exists": True,
            "preflight_json_source": "explicit_arg",
            "status_json_source": "runner_recorded",
        }
    }

    failures = _runner_recorded_path_failures(
        summaries,
        dry_run=False,
        allow_explicit_artifact_paths=False,
    )

    assert failures == ["native_artifact_check_preflight_path_not_runner_recorded"]


def test_runner_recorded_path_failures_accept_runner_recorded_sources():
    summaries = {
        "native_artifact_check": {
            "exists": True,
            "preflight_json_source": "runner_recorded",
            "status_json_source": "runner_recorded",
        }
    }

    failures = _runner_recorded_path_failures(
        summaries,
        dry_run=False,
        allow_explicit_artifact_paths=False,
    )

    assert failures == []


def test_runner_recorded_path_failures_allow_manual_override():
    summaries = {
        "native_artifact_check": {
            "exists": True,
            "preflight_json_source": "explicit_arg",
            "status_json_source": "explicit_arg",
        }
    }

    failures = _runner_recorded_path_failures(
        summaries,
        dry_run=False,
        allow_explicit_artifact_paths=True,
    )

    assert failures == []


def test_tail_window_probe_failures_accept_expected_window():
    summaries = {
        "arg_slot_tail_window_runner": {
            "exists": True,
            "passed": True,
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
    }

    failures = _tail_window_probe_failures(
        summaries,
        enabled=True,
        dry_run=False,
        expected_tail_window_size=4,
    )

    assert failures == []


def test_tail_window_probe_failures_reject_full_table_window():
    summaries = {
        "arg_slot_tail_window_runner": {
            "exists": True,
            "passed": True,
            "tail_window_size": 4,
            "merged_row_count": 16,
            "block_threads": 4,
            "dispatch_row_offset": 0,
            "dispatch_row_limit": 16,
            "dispatch_active_rows": 16,
            "dispatch_expected_program_count": 4,
            "no_payload": True,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "not_a_single_vllm_launch_table": True,
            "handle_projection_all_handle_fields_checked": True,
        }
    }

    failures = _tail_window_probe_failures(
        summaries,
        enabled=True,
        dry_run=False,
        expected_tail_window_size=4,
    )

    assert "arg_slot_tail_window_dispatch_offset_mismatch" in failures
    assert "arg_slot_tail_window_dispatch_active_mismatch" in failures


def test_tail_window_probe_failures_reject_kernel_boundary_mutation():
    summaries = {
        "arg_slot_tail_window_runner": {
            "exists": True,
            "passed": True,
            "tail_window_size": 4,
            "merged_row_count": 16,
            "block_threads": 4,
            "dispatch_row_offset": 12,
            "dispatch_row_limit": 16,
            "dispatch_active_rows": 4,
            "dispatch_expected_program_count": 1,
            "no_payload": True,
            "passed_to_kernel": True,
            "changes_kernel_launch_args": False,
            "current_wna16_arg_compatible": False,
            "not_a_single_vllm_launch_table": True,
            "handle_projection_all_handle_fields_checked": True,
        }
    }

    failures = _tail_window_probe_failures(
        summaries,
        enabled=True,
        dry_run=False,
        expected_tail_window_size=4,
    )

    assert "arg_slot_tail_window_passed_to_kernel_mismatch" in failures


def test_run_premap_lab_gate_closure_dry_run_can_include_tail_window_probe(
    tmp_path: Path,
):
    args = _build_parser().parse_args(
        [
            "--dry-run",
            "--run-tail-window-probe",
            "--tail-window-size",
            "8",
            "--arg-slot-tail-runner-json",
            str(tmp_path / "tail_runner.json"),
            "--arg-slot-tail-stub-json",
            str(tmp_path / "tail_stub.json"),
            "--arg-slot-tail-merged-json",
            str(tmp_path / "tail_merged.json"),
        ]
    )

    result = run_closure(args)

    assert result["passed"] is True
    assert result["tail_window_probe_enabled"] is True
    assert result["tail_window_size"] == 8
    assert "arg_slot_tail_window_runner" in result["steps"]
    tail_cmd = result["steps"]["arg_slot_tail_window_runner"]["cmd"]
    assert "--tail-window-size" in tail_cmd
    assert "8" in tail_cmd


def test_run_premap_lab_gate_closure_dry_run_passes_visible_device_args(
    tmp_path: Path,
):
    args = _build_parser().parse_args(
        [
            "--dry-run",
            "--device",
            "0",
            "--hip-visible-devices",
            "1",
            "--arg-slot-runner-json",
            str(tmp_path / "arg_slot_runner.json"),
            "--arg-slot-stub-json",
            str(tmp_path / "arg_slot_stub.json"),
            "--arg-slot-merged-json",
            str(tmp_path / "arg_slot_merged.json"),
            "--summary-json",
            str(tmp_path / "summary.json"),
            "--summary-check-json",
            str(tmp_path / "summary.check.json"),
            "--output-json",
            str(tmp_path / "closure.json"),
        ]
    )

    result = run_closure(args)

    assert result["passed"] is True
    arg_slot_cmd = result["steps"]["arg_slot_runner"]["cmd"]
    assert "--device" in arg_slot_cmd
    assert "0" in arg_slot_cmd
    assert "--hip-visible-devices" in arg_slot_cmd
    assert "1" in arg_slot_cmd
    summary_check_cmd = result["steps"]["summary_check"]["cmd"]
    assert "--expected-online-merged-device" in summary_check_cmd
    assert "0" in summary_check_cmd


def test_run_premap_lab_gate_closure_main_writes_report(tmp_path: Path):
    output_json = tmp_path / "closure.json"

    exit_code = main(["--dry-run", "--output-json", str(output_json)])

    assert exit_code == 0
    result = json.loads(output_json.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["source"] == "premap_lab_gate_closure"
    assert result["dry_run"] is True
