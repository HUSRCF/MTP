from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_premap_online_merged_native_arg_slot_canary.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_premap_online_merged_native_arg_slot_canary", path
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


def test_online_merged_arg_slot_canary_dry_run_writes_artifacts(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    merged = tmp_path / "merged.json"
    stub = tmp_path / "stub.json"
    report = tmp_path / "report.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--merged-output-json",
            str(merged),
            "--stub-output-json",
            str(stub),
            "--output-json",
            str(report),
            "--dry-run",
        ]
    )

    result = module.run_canary(args)

    assert result["passed"] is True
    assert result["selected_source_count"] == 2
    assert result["merged_row_count"] == 7
    assert result["merged_expected_program_count"] == 2
    assert result["dispatch_active_rows"] == 7
    assert result["dispatch_expected_program_count"] == 2
    assert result["device"] == module.LAB_DEFAULT_GPU_DEVICE == 1
    assert result["not_a_single_vllm_launch_table"] is True
    assert result["handle_projection_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert result["handle_projection_hashchain_equal"] is True
    assert result["handle_projection_all_handle_fields_checked"] is True
    assert result["arg_slot_field_read_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert result["arg_slot_all_handle_fields_read"] is True
    assert result["consumer_view_field_read_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert result["consumer_view_all_handle_fields_read"] is True
    assert result["consumer_view_source_packet_chain_depth"] == 3
    assert json.loads(merged.read_text(encoding="utf-8"))["_meta"]["row_count"] == 7
    stub_payload = json.loads(stub.read_text(encoding="utf-8"))
    assert stub_payload["future_kernel_native_arg_slot_consumer_checked"] is True
    assert stub_payload["future_kernel_native_consumer_view_checked"] is True
    assert stub_payload["future_kernel_native_consumer_view_row_ok_count"] == 7
    assert (
        stub_payload[
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle"
    )
    assert (
        stub_payload[
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
        ]
        == "scale_metadata_handle"
    )
    assert json.loads(report.read_text(encoding="utf-8"))["passed"] is True
    assert (
        json.loads(report.read_text(encoding="utf-8"))[
            "handle_projection_all_handle_fields_checked"
        ]
        is True
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_mirror_field(
    tmp_path: Path,
):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    stub = tmp_path / "stub.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--mirror-field",
            "packed_weight_descriptor",
            "--merged-output-json",
            str(tmp_path / "merged.json"),
            "--stub-output-json",
            str(stub),
            "--output-json",
            str(tmp_path / "report.json"),
            "--dry-run",
        ]
    )

    result = module.run_canary(args)
    stub_payload = json.loads(stub.read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["mirror_field"] == "packed_weight_descriptor"
    assert result["stub_summary"]["requested_macros"] == module.arg_slot_macros(
        "packed_weight_descriptor"
    )
    assert (
        stub_payload[
            "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name"
        ]
        == "packed_weight_descriptor"
    )
    assert (
        module.MIRROR_FIELD_MACRO["packed_weight_descriptor"]
        in stub_payload["requested_macros"]
    )


def test_online_merged_arg_slot_canary_rejects_too_few_sources(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    runner = tmp_path / "runner.json"
    _write_input(first, start=0, rows=5, export_index=0)
    _write_runner(runner, [first])

    args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--block-threads",
            "4",
            "--merged-output-json",
            str(tmp_path / "merged.json"),
            "--stub-output-json",
            str(tmp_path / "stub.json"),
            "--output-json",
            str(tmp_path / "report.json"),
            "--dry-run",
        ]
    )

    with pytest.raises(ValueError, match="need at least 2"):
        module.run_canary(args)


def test_online_merged_arg_slot_canary_tail_window_uses_active_rows(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--tail-window-size",
            "3",
            "--merged-output-json",
            str(tmp_path / "merged.json"),
            "--stub-output-json",
            str(tmp_path / "stub.json"),
            "--output-json",
            str(tmp_path / "report.json"),
            "--dry-run",
        ]
    )

    result = module.run_canary(args)

    assert result["passed"] is True
    assert result["dispatch_row_offset"] == 4
    assert result["dispatch_row_limit"] == 7
    assert result["dispatch_active_rows"] == 3
    assert result["dispatch_expected_program_count"] == 1
    assert result["stub_summary"]["future_kernel_native_arg_slot_consumer_row_count"] == 3
    assert (
        result["stub_summary"]["future_kernel_native_dispatch_consumer_grid_x"] == 1
    )


def test_online_merged_arg_slot_canary_flags_stub_geometry_mismatch(tmp_path: Path):
    module = _load_module()
    merged_input = {
        "_meta": {"row_count": 7},
    }
    stub = {
        "passed": True,
        "ok": True,
        "row_count": 7,
        "row_ok_count": 7,
        "error_count": 0,
        "input_json": str(tmp_path / "merged.json"),
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "requested_macros": module.arg_slot_macros("scale_metadata_handle"),
        "future_kernel_native_arg_slot_consumer_checked": True,
        "future_kernel_native_arg_slot_consumer_row_count": 7,
        "future_kernel_native_arg_slot_consumer_row_ok_count": 7,
        "future_kernel_native_arg_slot_consumer_error_count": 0,
        "future_kernel_native_arg_slot_consumer_payload_bytes": 0,
        "future_kernel_native_arg_slot_consumer_passed_to_kernel": False,
        "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args": False,
        "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible": False,
        "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation": False,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_checked": True,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_field_name": "scale_metadata_handle",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count": 7,
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count": 7,
        "future_kernel_native_dispatch_consumer_checked": True,
        "future_kernel_native_dispatch_consumer_grid_x": 1,
        "future_kernel_native_dispatch_consumer_block_x": 4,
        "future_kernel_native_dispatch_consumer_row_offset": 0,
        "future_kernel_native_dispatch_consumer_row_limit": 7,
        "future_kernel_native_dispatch_consumer_active_rows": 7,
        "future_kernel_native_dispatch_consumer_row_count": 7,
        "future_kernel_native_dispatch_consumer_row_ok_count": 7,
        "future_kernel_native_dispatch_consumer_rows_per_program": 4,
        "future_kernel_native_dispatch_consumer_program_count": 1,
        "future_kernel_native_dispatch_consumer_launch_covers_active_rows": True,
        "future_kernel_native_dispatch_consumer_launch_minimal_cover": True,
        "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_dispatch_ptr_consumer_checked": True,
        "future_kernel_native_dispatch_ptr_consumer_packet_visible": True,
        "future_kernel_native_dispatch_ptr_consumer_dispatch_packet_visible": True,
        "future_kernel_native_dispatch_ptr_consumer_row_count": 7,
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count": 7,
        "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_arg_slot_consumer_slot_visible": True,
        "future_kernel_native_arg_slot_consumer_dispatch_ptr_packet_visible": True,
        "future_kernel_native_arg_slot_consumer_dispatch_packet_visible": True,
        "future_kernel_native_arg_slot_consumer_packet_chain_depth": 3,
        "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_count": 7,
        "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_row_ok_count": 7,
        "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_error_count": 0,
        "future_kernel_native_arg_slot_consumer_descriptor_ptr_read_hash_accumulator": "d",
        "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_count": 7,
        "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_row_ok_count": 7,
        "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_error_count": 0,
        "future_kernel_native_arg_slot_consumer_packed_weight_descriptor_read_hash_accumulator": "p",
        "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_count": 7,
        "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_row_ok_count": 7,
        "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_error_count": 0,
        "future_kernel_native_arg_slot_consumer_scale_metadata_handle_read_hash_accumulator": "s",
        "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_count": 7,
        "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_row_ok_count": 7,
        "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_error_count": 0,
        "future_kernel_native_arg_slot_consumer_aux_metadata_handle_read_hash_accumulator": "a",
    }

    failures = module._validate_stub(
        stub,
        merged_input=merged_input,
        merged_output_json=tmp_path / "merged.json",
        block_threads=4,
        dispatch_row_offset=0,
        dispatch_row_limit=7,
        mirror_field="scale_metadata_handle",
    )

    assert any("future_kernel_native_dispatch_consumer_grid_x_mismatch" in item for item in failures)
    assert any(
        "future_kernel_native_dispatch_consumer_program_count_mismatch" in item
        for item in failures
    )
