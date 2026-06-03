from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_online_merged_native_arg_slot_window_sweep import (
    _validate_window_result,
    _window_bounds,
    build_parser,
    main,
    run_sweep,
)


def _write_input(path: Path, *, start: int, rows: int, export_index: int) -> None:
    payload = {
        "descriptor_ptr": [1000 + start + idx for idx in range(rows)],
        "packed_weight_descriptor": [2000 + start + idx for idx in range(rows)],
        "scale_metadata_handle": [3000 + start + idx for idx in range(rows)],
        "aux_metadata_handle": [4000 + start + idx for idx in range(rows)],
        "expert_id": [(start + idx) % 8 for idx in range(rows)],
        "address_key_hash": [5000 + start + idx for idx in range(rows)],
        "_meta": {
            "schema_hash": "schema",
            "row_count": rows,
            "column_count": 4,
            "table_object_hash": f"table-{export_index}",
            "payload_bytes": 0,
            "ready_credit": False,
            "changes_router": False,
            "changes_descriptor_order": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
        "_export_context": {
            "export_index": export_index,
            "layer_id": export_index,
            "request_id": f"req-{export_index}",
            "sequence_id": "seq0",
            "token_index": -1,
            "row_count": rows,
        },
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_runner(path: Path, inputs: list[Path]) -> None:
    path.write_text(
        json.dumps({"online_prelaunch_input_jsons": [str(item) for item in inputs]})
        + "\n",
        encoding="utf-8",
    )


def test_window_bounds_cover_head_middle_tail():
    assert _window_bounds(17, 4) == {
        "head": (0, 4),
        "middle": (6, 10),
        "tail": (13, 17),
    }


def test_window_result_accepts_program_view_ptr_requirement():
    result = {
        "passed": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "dispatch_row_offset": 13,
        "dispatch_row_limit": 17,
        "dispatch_active_rows": 4,
        "stub_summary": {
            "future_kernel_native_consumer_program_view_ptr_checked": True,
            "future_kernel_native_consumer_program_view_ptr_source": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_row_count": 4,
            "future_kernel_native_consumer_program_view_ptr_row_ok_count": 4,
            "future_kernel_native_consumer_program_view_ptr_error_count": 0,
            "future_kernel_native_consumer_program_view_ptr_field_mask": 15,
            "future_kernel_native_consumer_program_view_ptr_required_field_mask": 7,
            "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": (
                False
            ),
            "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": (
                False
            ),
            "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": (
                False
            ),
            "future_kernel_native_consumer_kernel_arg_packet_checked": True,
            "future_kernel_native_consumer_kernel_arg_packet_source": (
                "premap_future_kernel_native_consumer_program_view_ptr_abi_v1"
            ),
            "future_kernel_native_consumer_kernel_arg_packet_row_count": 4,
            "future_kernel_native_consumer_kernel_arg_packet_row_ok_count": 4,
            "future_kernel_native_consumer_kernel_arg_packet_error_count": 0,
            "future_kernel_native_consumer_kernel_arg_packet_field_mask": 15,
            "future_kernel_native_consumer_kernel_arg_packet_required_field_mask": 7,
            "future_kernel_native_consumer_kernel_arg_packet_payload_bytes": 0,
            "future_kernel_native_consumer_kernel_arg_packet_passed_to_kernel": False,
            "future_kernel_native_consumer_kernel_arg_packet_changes_kernel_launch_args": (
                False
            ),
            "future_kernel_native_consumer_kernel_arg_packet_current_wna16_arg_compatible": (
                False
            ),
            "future_kernel_native_consumer_kernel_arg_packet_requires_wna16_arg_reinterpretation": (
                False
            ),
        },
    }

    assert (
        _validate_window_result(
            result,
            label="tail",
            expected_offset=13,
            expected_limit=17,
            require_program_view_ptr_abi=True,
        )
        == []
    )


def test_window_result_rejects_program_view_ptr_row_count_mismatch():
    result = {
        "passed": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "dispatch_row_offset": 0,
        "dispatch_row_limit": 4,
        "dispatch_active_rows": 4,
        "stub_summary": {
            "future_kernel_native_consumer_program_view_ptr_checked": True,
            "future_kernel_native_consumer_program_view_ptr_source": (
                "premap_future_kernel_native_consumer_program_view_abi_v1"
            ),
            "future_kernel_native_consumer_program_view_ptr_row_count": 4,
            "future_kernel_native_consumer_program_view_ptr_row_ok_count": 3,
            "future_kernel_native_consumer_program_view_ptr_error_count": 0,
            "future_kernel_native_consumer_program_view_ptr_field_mask": 15,
            "future_kernel_native_consumer_program_view_ptr_required_field_mask": 7,
            "future_kernel_native_consumer_program_view_ptr_payload_bytes": 0,
            "future_kernel_native_consumer_program_view_ptr_passed_to_kernel": False,
            "future_kernel_native_consumer_program_view_ptr_changes_kernel_launch_args": (
                False
            ),
            "future_kernel_native_consumer_program_view_ptr_current_wna16_arg_compatible": (
                False
            ),
            "future_kernel_native_consumer_program_view_ptr_requires_wna16_arg_reinterpretation": (
                False
            ),
        },
    }

    failures = _validate_window_result(
        result,
        label="head",
        expected_offset=0,
        expected_limit=4,
        require_program_view_ptr_abi=True,
    )

    assert "head_program_view_ptr_row_ok_count_mismatch" in failures


def test_window_result_rejects_missing_program_view_ptr_evidence_and_collects_packet_errors():
    result = {
        "passed": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "dispatch_row_offset": 0,
        "dispatch_row_limit": 4,
        "dispatch_active_rows": 4,
        "stub_summary": {
            "typed_consumer_checked": True,
        },
    }

    failures = _validate_window_result(
        result,
        label="head",
        expected_offset=0,
        expected_limit=4,
        require_program_view_ptr_abi=True,
    )

    assert (
        "head_program_view_ptr_evidence_missing_or_dry_run_unsupported"
        in failures
    )
    assert (
        "head_future_kernel_native_consumer_kernel_arg_packet_checked_mismatch"
        in failures
    )


def test_window_sweep_dry_run_records_expected_windows(tmp_path: Path):
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "sweep.json"
    _write_input(first, start=0, rows=8, export_index=0)
    _write_input(second, start=100, rows=9, export_index=1)
    _write_runner(runner, [first, second])

    args = build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--output-json",
            str(output),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "17",
            "--block-threads",
            "4",
            "--window-size",
            "4",
            "--dry-run",
        ]
    )

    result = run_sweep(args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["row_count"] == 17
    assert result["windows"]["full"]["dispatch_row_offset"] == 0
    assert result["windows"]["full"]["dispatch_row_limit"] == 17
    assert result["windows"]["head"]["dispatch_row_offset"] == 0
    assert result["windows"]["head"]["dispatch_row_limit"] == 4
    assert result["windows"]["middle"]["dispatch_row_offset"] == 6
    assert result["windows"]["middle"]["dispatch_row_limit"] == 10
    assert result["windows"]["tail"]["dispatch_row_offset"] == 13
    assert result["windows"]["tail"]["dispatch_row_limit"] == 17
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_window_sweep_cli_writes_output(tmp_path: Path):
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "sweep.json"
    _write_input(first, start=0, rows=8, export_index=0)
    _write_input(second, start=100, rows=9, export_index=1)
    _write_runner(runner, [first, second])

    exit_code = main(
        [
            "--runner-json",
            str(runner),
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--output-json",
            str(output),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "17",
            "--block-threads",
            "4",
            "--window-size",
            "4",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["source"] == (
        "online_merged_future_native_arg_slot_window_sweep_runner"
    )
