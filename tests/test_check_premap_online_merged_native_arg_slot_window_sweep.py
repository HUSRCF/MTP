from __future__ import annotations

import json
from pathlib import Path

from scripts.check_premap_online_merged_native_arg_slot_window_sweep import (
    check_window_sweep_artifact,
    main,
)


_FIELD_MASK_PREFIXES = (
    "future_kernel_native_consumer",
    "future_kernel_native_launch_consumer",
    "future_kernel_native_dispatch_consumer",
    "future_kernel_native_dispatch_ptr_consumer",
    "future_kernel_native_arg_slot_consumer",
    "future_kernel_native_consumer_view",
)


def _field_mask_pairs() -> dict[str, int]:
    pairs: dict[str, int] = {}
    for prefix in _FIELD_MASK_PREFIXES:
        pairs[f"{prefix}_field_mask"] = 15
        pairs[f"{prefix}_required_field_mask"] = 7
    return pairs


def _field_read_pairs(prefix: str, active: int) -> dict[str, object]:
    pairs: dict[str, object] = {}
    for field in (
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ):
        field_prefix = f"{prefix}_{field}_read"
        pairs[f"{field_prefix}_row_count"] = active
        pairs[f"{field_prefix}_row_ok_count"] = active
        pairs[f"{field_prefix}_error_count"] = 0
        pairs[f"{field_prefix}_hash_accumulator"] = field
    return pairs


def _child_payload(
    *,
    offset: int,
    limit: int,
    programs: int,
    block_threads: int,
    merged_row_count: int,
    mirror_field: str,
) -> dict[str, object]:
    active = limit - offset
    return {
        "passed": True,
        "failures": [],
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
        "handle_projection_hashchain_equal": True,
        "dispatch_row_offset": offset,
        "dispatch_row_limit": limit,
        "dispatch_active_rows": active,
        "dispatch_expected_program_count": programs,
        "block_threads": block_threads,
        "merged_row_count": merged_row_count,
        "mirror_field": mirror_field,
        "stub_summary": {
            "passed": True,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "future_kernel_native_arg_slot_consumer_row_count": active,
            "future_kernel_native_arg_slot_consumer_row_ok_count": active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": active,
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": mirror_field,
            "future_kernel_native_dispatch_consumer_program_count": programs,
            "future_kernel_native_dispatch_consumer_block_x": block_threads,
            "future_kernel_native_dispatch_consumer_row_limit": limit,
            "future_kernel_native_consumer_view_checked": True,
            "future_kernel_native_consumer_view_row_count": active,
            "future_kernel_native_consumer_view_row_ok_count": active,
            "future_kernel_native_consumer_view_error_count": 0,
            "future_kernel_native_consumer_view_row_offset": offset,
            "future_kernel_native_consumer_view_row_limit": limit,
            "future_kernel_native_consumer_view_rows_per_program": block_threads,
            "future_kernel_native_consumer_view_source_packet_chain_depth": 3,
            "future_kernel_native_consumer_view_payload_bytes": 0,
            "future_kernel_native_consumer_view_passed_to_kernel": False,
            "future_kernel_native_consumer_view_changes_kernel_launch_args": False,
            "future_kernel_native_consumer_view_current_wna16_arg_compatible": False,
            "future_kernel_native_consumer_view_requires_wna16_arg_reinterpretation": False,
            **_field_mask_pairs(),
            **_field_read_pairs("future_kernel_native_arg_slot_consumer", active),
            **_field_read_pairs("future_kernel_native_consumer_view", active),
        },
    }


def _write_artifact(
    tmp_path: Path,
    *,
    bad_middle_offset: bool = False,
    row_count: int = 17,
    window_size: int = 4,
    mirror_field: str = "scale_metadata_handle",
) -> Path:
    block_threads = 4
    active = min(window_size, row_count)
    middle_offset = max(0, (row_count - active) // 2)
    bounds = {
        "full": (0, row_count),
        "head": (0, active),
        "middle": (middle_offset, middle_offset + active),
        "tail": (row_count - active, row_count),
    }
    windows: dict[str, dict[str, object]] = {}
    for label, (offset, limit) in bounds.items():
        child_path = tmp_path / f"{label}.json"
        stub_path = tmp_path / f"{label}.stub.json"
        child_offset = offset + 1 if label == "middle" and bad_middle_offset else offset
        expected_active = limit - offset
        programs = (expected_active + block_threads - 1) // block_threads
        child = _child_payload(
            offset=child_offset,
            limit=limit,
            programs=programs,
            block_threads=block_threads,
            merged_row_count=row_count,
            mirror_field=mirror_field,
        )
        child["stub_output_json"] = str(stub_path)
        stub_summary = child["stub_summary"]
        assert isinstance(stub_summary, dict)
        stub_payload = dict(stub_summary)
        child_path.write_text(
            json.dumps(child)
            + "\n",
            encoding="utf-8",
        )
        stub_path.write_text(
            json.dumps(stub_payload)
            + "\n",
            encoding="utf-8",
        )
        windows[label] = {
            "passed": True,
            "dispatch_row_offset": child_offset,
            "dispatch_row_limit": limit,
            "dispatch_active_rows": limit - child_offset,
            "dispatch_expected_program_count": programs,
            "merged_row_count": row_count,
            "output_json": str(child_path),
            "stub_output_json": str(stub_path),
            "merged_output_json": str(tmp_path / f"{label}.merged.json"),
        }
    payload = {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_window_sweep_runner",
        "row_count": row_count,
        "window_size": window_size,
        "device": 1,
        "mirror_field": mirror_field,
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


def test_window_sweep_check_rejects_bad_child_program_count(tmp_path: Path):
    path = _write_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    windows = payload["windows"]
    assert isinstance(windows, dict)
    child_path = Path(windows["head"]["output_json"])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["dispatch_expected_program_count"] = 99
    child["stub_summary"]["future_kernel_native_arg_slot_consumer_row_count"] = 99
    child_path.write_text(json.dumps(child) + "\n", encoding="utf-8")

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert "head_child_dispatch_expected_program_count_mismatch" in result["failures"]
    assert (
        "head_child_stub_future_kernel_native_arg_slot_consumer_row_count_mismatch"
        in result["failures"]
    )


def test_window_sweep_check_rejects_child_mirror_field_mismatch(tmp_path: Path):
    path = _write_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    windows = payload["windows"]
    assert isinstance(windows, dict)
    child_path = Path(windows["tail"]["output_json"])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["mirror_field"] = "descriptor_ptr"
    child["stub_summary"][
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
    ] = "descriptor_ptr"
    child_path.write_text(json.dumps(child) + "\n", encoding="utf-8")

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert "tail_child_mirror_field_mismatch" in result["failures"]
    assert "tail_child_stub_single_field_mirror_field_name_mismatch" in result[
        "failures"
    ]


def test_window_sweep_check_rejects_child_field_mask_mismatch(tmp_path: Path):
    path = _write_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    windows = payload["windows"]
    assert isinstance(windows, dict)
    child_path = Path(windows["full"]["output_json"])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["stub_summary"]["future_kernel_native_arg_slot_consumer_field_mask"] = 7
    child_path.write_text(json.dumps(child) + "\n", encoding="utf-8")

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert (
        "full_child_stub_future_kernel_native_arg_slot_consumer_field_mask_not_all_fields"
        in result["failures"]
    )


def test_window_sweep_check_rejects_missing_consumer_view_read(tmp_path: Path):
    path = _write_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    windows = payload["windows"]
    assert isinstance(windows, dict)
    child_path = Path(windows["head"]["output_json"])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["stub_summary"][
        "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count"
    ] = 0
    child_path.write_text(json.dumps(child) + "\n", encoding="utf-8")

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert (
        "head_child_stub_future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count_mismatch"
        in result["failures"]
    )


def test_window_sweep_check_rejects_stub_consumer_view_geometry_mismatch(
    tmp_path: Path,
):
    path = _write_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    windows = payload["windows"]
    assert isinstance(windows, dict)
    stub_path = Path(windows["middle"]["stub_output_json"])
    stub = json.loads(stub_path.read_text(encoding="utf-8"))
    stub["future_kernel_native_consumer_view_row_offset"] = 0
    stub_path.write_text(json.dumps(stub) + "\n", encoding="utf-8")

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=17,
    )

    assert result["passed"] is False
    assert (
        "middle_child_stub_artifact_future_kernel_native_consumer_view_row_offset_mismatch"
        in result["failures"]
    )


def test_window_sweep_check_rejects_degenerate_windows(tmp_path: Path):
    path = _write_artifact(tmp_path, row_count=4, window_size=4)

    result = check_window_sweep_artifact(
        path,
        expected_window_size=4,
        expected_block_threads=4,
        min_row_count=4,
    )

    assert result["passed"] is False
    assert "row_count_not_larger_than_window_size" in result["failures"]


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
