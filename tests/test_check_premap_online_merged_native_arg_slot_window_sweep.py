from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_online_merged_native_arg_slot_window_sweep import (
    check_window_sweep_artifact,
    main,
)


def _child_payload(*, offset: int, limit: int) -> dict[str, object]:
    active = limit - offset
    return {
        "passed": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "dispatch_row_offset": offset,
        "dispatch_row_limit": limit,
        "dispatch_active_rows": active,
    }


def _write_artifact(tmp_path: Path, *, bad_middle_offset: bool = False) -> Path:
    row_count = 17
    block_threads = 4
    bounds = {
        "full": (0, 17),
        "head": (0, 4),
        "middle": (6, 10),
        "tail": (13, 17),
    }
    windows: dict[str, dict[str, object]] = {}
    for label, (offset, limit) in bounds.items():
        child_path = tmp_path / f"{label}.json"
        child_offset = offset + 1 if label == "middle" and bad_middle_offset else offset
        child_path.write_text(
            json.dumps(_child_payload(offset=child_offset, limit=limit)) + "\n",
            encoding="utf-8",
        )
        windows[label] = {
            "passed": True,
            "dispatch_row_offset": child_offset,
            "dispatch_row_limit": limit,
            "dispatch_active_rows": limit - child_offset,
            "dispatch_expected_program_count": (limit - offset + block_threads - 1)
            // block_threads,
            "merged_row_count": row_count,
            "output_json": str(child_path),
            "stub_output_json": str(tmp_path / f"{label}.stub.json"),
            "merged_output_json": str(tmp_path / f"{label}.merged.json"),
        }
    payload = {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_window_sweep_runner",
        "row_count": row_count,
        "window_size": 4,
        "device": 1,
        "mirror_field": "scale_metadata_handle",
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "windows": windows,
    }
    path = tmp_path / "sweep.json"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def test_window_sweep_check_accepts_valid_artifact(tmp_path: Path):
    path = _write_artifact(tmp_path)

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["row_count"] == 17
    assert result["windows_checked"] == ["full", "head", "middle", "tail"]


def test_window_sweep_check_rejects_bad_middle_offset(tmp_path: Path):
    path = _write_artifact(tmp_path, bad_middle_offset=True)

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert "middle_dispatch_row_offset_mismatch" in result["failures"]
    assert "middle_child_dispatch_row_offset_mismatch" in result["failures"]


def test_window_sweep_check_cli_writes_output(tmp_path: Path):
    path = _write_artifact(tmp_path)
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
    assert payload["source"] == "online_merged_future_native_arg_slot_window_sweep_check"
    assert payload["passed"] is True
