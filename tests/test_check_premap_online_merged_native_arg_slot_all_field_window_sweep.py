from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_online_merged_native_arg_slot_all_field_window_sweep import (
    check_all_field_window_sweep_artifact,
    main,
)
from scripts.run_premap_online_merged_native_arg_slot_all_field_window_sweep import (
    MIRROR_FIELDS,
)


def _write_field_check(
    path: Path,
    *,
    field: str,
    row_count: int,
    window_size: int,
    block_threads: int,
    require_program_view_ptr_abi: bool = False,
    require_kernel_arg_packet_abi: bool = False,
) -> None:
    payload = {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_window_sweep_check",
        "expected_mirror_field": field,
        "expected_window_size": window_size,
        "expected_block_threads": block_threads,
        "require_child_artifacts": True,
        "require_child_field_masks": True,
        "require_child_consumer_view": True,
        "require_child_consumer_view_layout": True,
        "require_child_consumer_view_row_layout": True,
        "require_child_consumer_view_handle_projection": True,
        "require_child_program_view_ptr_abi": bool(require_program_view_ptr_abi),
        "require_child_kernel_arg_packet_abi": bool(
            require_kernel_arg_packet_abi
        ),
        "require_non_degenerate_windows": True,
        "row_count": row_count,
        "windows_checked": ["full", "head", "middle", "tail"],
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_all_field_artifact(
    tmp_path: Path,
    *,
    bad_field_check: str | None = None,
    mismatched_row_count: bool = False,
    require_program_view_ptr_abi: bool = False,
    require_kernel_arg_packet_abi: bool = False,
) -> Path:
    row_count = 17
    window_size = 4
    block_threads = 4
    field_reports: dict[str, dict[str, object]] = {}
    row_counts: dict[str, int] = {}
    for index, field in enumerate(MIRROR_FIELDS):
        field_row_count = row_count + 1 if mismatched_row_count and index == 0 else row_count
        check_path = tmp_path / f"{field}.check.json"
        _write_field_check(
            check_path,
            field=("descriptor_ptr" if bad_field_check == field else field),
            row_count=field_row_count,
            window_size=window_size,
            block_threads=block_threads,
            require_program_view_ptr_abi=require_program_view_ptr_abi,
            require_kernel_arg_packet_abi=require_kernel_arg_packet_abi,
        )
        field_reports[field] = {
            "passed": True,
            "sweep_json": str(tmp_path / f"{field}.runner.json"),
            "check_json": str(check_path),
            "sweep_failures": [],
            "check_failures": [],
            "row_count": field_row_count,
            "window_size": window_size,
            "windows_checked": ["full", "head", "middle", "tail"],
        }
        row_counts[field] = field_row_count
    payload = {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
        "dry_run": False,
        "window_size": window_size,
        "require_program_view_ptr_abi": bool(require_program_view_ptr_abi),
        "require_kernel_arg_packet_abi": bool(require_kernel_arg_packet_abi),
        "block_threads": block_threads,
        "mirror_fields": list(MIRROR_FIELDS),
        "field_reports": field_reports,
        "row_counts": row_counts,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    path = tmp_path / "all_fields.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def test_all_field_window_sweep_check_accepts_valid_artifact(tmp_path: Path):
    path = _write_all_field_artifact(tmp_path)

    result = check_all_field_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["mirror_fields_checked"] == list(MIRROR_FIELDS)
    assert result["row_count"] == 17


def test_all_field_window_sweep_check_rejects_field_check_mismatch(
    tmp_path: Path,
):
    path = _write_all_field_artifact(
        tmp_path,
        bad_field_check="aux_metadata_handle",
    )

    result = check_all_field_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert "aux_metadata_handle_check_expected_mirror_field_mismatch" in result[
        "failures"
    ]


def test_all_field_window_sweep_check_rejects_mismatched_row_count(
    tmp_path: Path,
):
    path = _write_all_field_artifact(tmp_path, mismatched_row_count=True)

    result = check_all_field_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert "field_row_counts_not_equal" in result["failures"]


def test_all_field_window_sweep_check_accepts_program_view_ptr_requirement(
    tmp_path: Path,
):
    path = _write_all_field_artifact(
        tmp_path,
        require_program_view_ptr_abi=True,
        require_kernel_arg_packet_abi=True,
    )

    result = check_all_field_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
        require_child_program_view_ptr_abi=True,
        require_child_kernel_arg_packet_abi=True,
    )

    assert result["passed"] is True
    assert result["require_child_program_view_ptr_abi"] is True
    assert result["require_child_kernel_arg_packet_abi"] is True


def test_all_field_window_sweep_check_rejects_missing_program_view_ptr_gate(
    tmp_path: Path,
):
    path = _write_all_field_artifact(tmp_path)

    result = check_all_field_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
        require_child_program_view_ptr_abi=True,
        require_child_kernel_arg_packet_abi=True,
    )

    assert result["passed"] is False
    assert "require_program_view_ptr_abi_mismatch" in result["failures"]
    assert "require_kernel_arg_packet_abi_mismatch" in result["failures"]


def test_all_field_window_sweep_check_rejects_missing_kernel_arg_packet_gate(
    tmp_path: Path,
):
    path = _write_all_field_artifact(
        tmp_path,
        require_program_view_ptr_abi=True,
        require_kernel_arg_packet_abi=False,
    )

    result = check_all_field_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
        require_child_program_view_ptr_abi=True,
        require_child_kernel_arg_packet_abi=True,
    )

    assert result["passed"] is False
    assert "require_kernel_arg_packet_abi_mismatch" in result["failures"]


def test_all_field_window_sweep_check_cli_writes_output(tmp_path: Path):
    path = _write_all_field_artifact(tmp_path)
    output = tmp_path / "check.json"

    exit_code = main(
        [
            str(path),
            "--expected-window-size",
            "4",
            "--expected-block-threads",
            "4",
            "--min-row-count",
            "17",
            "--output-json",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == (
        "online_merged_future_native_arg_slot_all_field_window_sweep_check"
    )
    assert payload["passed"] is True
