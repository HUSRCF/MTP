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
    assert result["kernel_arg_packet_field_read_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert result["kernel_arg_packet_all_handle_fields_read"] is True
    assert result["kernel_entry_summary_checked"] is True
    assert result["kernel_entry_summary_packet_valid"] == 1
    assert result["kernel_entry_summary_error_count"] == 0
    assert result["kernel_entry_summary_all_handle_fields_read"] is True
    assert result["kernel_entry_args_checked"] is True
    assert result["kernel_entry_args_error_count"] == 0
    assert result["kernel_entry_args_all_handle_fields_read"] is True
    assert result["consumer_view_source_packet_chain_depth"] == 3
    assert result["stub_summary"]["future_kernel_native_dispatch_consumer_row_offset"] == 0
    assert result["stub_summary"]["future_kernel_native_dispatch_consumer_row_limit"] == 7
    assert (
        result["stub_summary"]["future_kernel_native_dispatch_consumer_rows_per_program"]
        == 4
    )
    assert result["stub_summary"]["future_kernel_native_consumer_view_row_offset"] == 0
    assert result["stub_summary"]["future_kernel_native_consumer_view_row_limit"] == 7
    assert (
        result["stub_summary"]["future_kernel_native_consumer_view_rows_per_program"]
        == 4
    )
    assert (
        result["stub_summary"]["future_kernel_native_consumer_program_view_checked"]
        is True
    )
    assert (
        result["stub_summary"]["future_kernel_native_consumer_program_view_row_count"]
        == 7
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_program_view_program_count"
        ]
        == 2
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_kernel_entry_args_summary_row_count"
        ]
        == 7
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_kernel_entry_summary_struct_size"
        ]
        == 104
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_kernel_entry_summary_offset_row_hash_accumulator"
        ]
        == 80
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_kernel_entry_args_summary_error_count"
        ]
        == 0
    )
    assert json.loads(merged.read_text(encoding="utf-8"))["_meta"]["row_count"] == 7
    stub_payload = json.loads(stub.read_text(encoding="utf-8"))
    assert stub_payload["future_kernel_native_arg_slot_consumer_checked"] is True
    assert stub_payload["future_kernel_native_consumer_view_checked"] is True
    assert stub_payload["future_kernel_native_consumer_view_row_ok_count"] == 7
    assert stub_payload["future_kernel_native_consumer_view_row_offset"] == 0
    assert stub_payload["future_kernel_native_consumer_view_row_limit"] == 7
    assert stub_payload["future_kernel_native_consumer_view_rows_per_program"] == 4
    assert (
        stub_payload[
            "future_kernel_native_consumer_view_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_arg_packet_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_entry_summary_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_entry_summary_row_metadata_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_entry_summary_error_count"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_entry_args_summary_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_entry_args_summary_row_metadata_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_entry_args_summary_error_count"
        ]
        == 0
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


def test_online_merged_arg_slot_canary_macros_can_require_launch_envelope_args():
    module = _load_module()

    macros = module.arg_slot_macros(
        "scale_metadata_handle",
        include_launch_envelope_args=True,
    )

    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in macros
    assert (
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI"
        in macros
    )
    assert macros.index(
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_FUTURE_KERNEL_NATIVE_CONSUMER_KERNEL_ENTRY_ARGS_PTR_ABI"
    ) < macros.index(module.LAUNCH_ENVELOPE_ARGS_MACRO)


def test_online_merged_arg_slot_canary_macros_can_require_launch_envelope_args_ptr():
    module = _load_module()

    macros = module.arg_slot_macros(
        "scale_metadata_handle",
        include_launch_envelope_args_ptr=True,
    )

    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in macros
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in macros
    assert macros.index(module.LAUNCH_ENVELOPE_ARGS_MACRO) < macros.index(
        module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO
    )


def test_online_merged_arg_slot_canary_macros_can_require_invocation():
    module = _load_module()

    macros = module.arg_slot_macros(
        "scale_metadata_handle",
        include_invocation=True,
    )

    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in macros
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in macros
    assert module.KERNEL_LAUNCH_DESCRIPTOR_MACRO in macros
    assert module.KERNEL_LAUNCH_CONTEXT_MACRO in macros
    assert module.INVOCATION_MACRO in macros


def test_online_merged_arg_slot_canary_macros_can_require_invocation_entry():
    module = _load_module()

    macros = module.arg_slot_macros(
        "scale_metadata_handle",
        include_invocation_entry=True,
    )

    assert module.INVOCATION_MACRO in macros
    assert module.INVOCATION_ENTRY_MACRO in macros
    assert macros.index(module.INVOCATION_MACRO) < macros.index(
        module.INVOCATION_ENTRY_MACRO
    )


def test_online_merged_arg_slot_canary_macros_can_require_endpoint():
    module = _load_module()

    macros = module.arg_slot_macros(
        "scale_metadata_handle",
        include_endpoint=True,
    )

    assert module.INVOCATION_MACRO in macros
    assert module.INVOCATION_ENTRY_MACRO in macros
    assert module.ENDPOINT_MACRO in macros


def test_online_merged_arg_slot_canary_macros_can_require_endpoint_ptr():
    module = _load_module()

    macros = module.arg_slot_macros(
        "scale_metadata_handle",
        include_endpoint_ptr=True,
    )

    assert module.INVOCATION_ENTRY_MACRO in macros
    assert module.ENDPOINT_MACRO in macros
    assert module.ENDPOINT_PTR_MACRO in macros
    assert module.KERNEL_LAUNCH_CONTEXT_MACRO in macros
    assert module.KERNEL_LAUNCH_DESCRIPTOR_MACRO in macros
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in macros
    assert macros.index(module.ENDPOINT_MACRO) < macros.index(
        module.ENDPOINT_PTR_MACRO
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_launch_envelope_args(
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
            "--require-launch-envelope-args-abi",
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
    assert result["require_launch_envelope_args_abi"] is True
    assert result["launch_envelope_args_checked"] is True
    assert (
        result["launch_envelope_args_abi_name"]
        == "premap_future_kernel_native_consumer_launch_envelope_args_abi_v1"
    )
    assert (
        result["launch_envelope_args_mode"]
        == "readonly_future_kernel_native_consumer_launch_envelope_args_abi"
    )
    assert (
        result["launch_envelope_args_source"]
        == "premap_future_kernel_native_consumer_kernel_entry_args_ptr_abi_v1"
    )
    assert result["launch_envelope_args_error_count"] == 0
    assert result["launch_envelope_args_all_handle_fields_read"] is True
    assert result["launch_envelope_args_packet_chain_depth"] == 7
    assert result["launch_envelope_args_version"] == 1
    assert result["launch_envelope_args_grid_x"] == 2
    assert result["launch_envelope_args_block_x"] == 4
    assert result["launch_envelope_args_row_offset"] == 0
    assert result["launch_envelope_args_row_limit"] == 7
    assert result["launch_envelope_args_rows_per_program"] == 4
    assert result["launch_envelope_args_struct_size"] == 48
    assert result["launch_envelope_args_struct_align"] == 8
    assert int(result["launch_envelope_args_row_hash_accumulator"], 16) == 1
    assert int(result["launch_envelope_args_field_read_hash_accumulator"], 16) == 2
    assert int(result["launch_envelope_args_row_metadata_hash_accumulator"], 16) == 3
    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in stub_payload["requested_macros"]
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_field_read_path"
        ]
        == "launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_row_offset"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_row_limit"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_payload_bytes"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_passed_to_kernel"
        ]
        is False
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_launch_envelope_args_packet_chain_depth"
        ]
        == 7
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_launch_envelope_args_ptr(
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
            "--require-launch-envelope-args-ptr-abi",
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
    assert args.require_launch_envelope_args_abi is False
    assert result["require_launch_envelope_args_abi"] is True
    assert result["require_launch_envelope_args_ptr_abi"] is True
    assert result["launch_envelope_args_ptr_checked"] is True
    assert (
        result["launch_envelope_args_ptr_abi_name"]
        == "premap_future_kernel_native_consumer_launch_envelope_args_ptr_abi_v1"
    )
    assert (
        result["launch_envelope_args_ptr_mode"]
        == "readonly_future_kernel_native_consumer_launch_envelope_args_ptr_abi"
    )
    assert (
        result["launch_envelope_args_ptr_source"]
        == "premap_future_kernel_native_consumer_launch_envelope_args_abi_v1"
    )
    assert result["launch_envelope_args_ptr_error_count"] == 0
    assert result["launch_envelope_args_ptr_all_handle_fields_read"] is True
    assert result["launch_envelope_args_ptr_packet_chain_depth"] == 8
    assert result["launch_envelope_args_ptr_version"] == 1
    assert result["launch_envelope_args_ptr_struct_size"] == 32
    assert result["launch_envelope_args_ptr_struct_align"] == 8
    assert result["launch_envelope_args_ptr_launch_args_struct_size"] == 48
    assert result["launch_envelope_args_ptr_pointer_size"] == 8
    assert int(result["launch_envelope_args_ptr_row_hash_accumulator"], 16) == 1
    assert int(result["launch_envelope_args_ptr_field_read_hash_accumulator"], 16) == 2
    assert int(result["launch_envelope_args_ptr_row_metadata_hash_accumulator"], 16) == 3
    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in stub_payload["requested_macros"]
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in stub_payload["requested_macros"]
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_ptr_field_read_path"
        ]
        == "launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_ptr_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_ptr_payload_bytes"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_ptr_passed_to_kernel"
        ]
        is False
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_launch_envelope_args_ptr_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_launch_envelope_args_ptr_packet_chain_depth"
        ]
        == 8
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_kernel_launch_descriptor(
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
            "--require-kernel-launch-descriptor-abi",
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
    assert args.require_launch_envelope_args_abi is False
    assert args.require_launch_envelope_args_ptr_abi is False
    assert result["require_launch_envelope_args_abi"] is True
    assert result["require_launch_envelope_args_ptr_abi"] is True
    assert result["require_kernel_launch_descriptor_abi"] is True
    assert result["kernel_launch_descriptor_checked"] is True
    assert (
        result["kernel_launch_descriptor_abi_name"]
        == "premap_future_kernel_native_consumer_kernel_launch_descriptor_abi_v1"
    )
    assert (
        result["kernel_launch_descriptor_mode"]
        == "readonly_future_kernel_native_consumer_kernel_launch_descriptor_abi"
    )
    assert (
        result["kernel_launch_descriptor_source"]
        == "premap_future_kernel_native_consumer_launch_envelope_args_ptr_abi_v1"
    )
    assert result["kernel_launch_descriptor_error_count"] == 0
    assert result["kernel_launch_descriptor_all_handle_fields_read"] is True
    assert result["kernel_launch_descriptor_packet_chain_depth"] == 9
    assert result["kernel_launch_descriptor_version"] == 1
    assert result["kernel_launch_descriptor_struct_size"] == 80
    assert result["kernel_launch_descriptor_struct_align"] == 8
    assert result["kernel_launch_descriptor_launch_args_ptr_struct_size"] == 32
    assert result["kernel_launch_descriptor_summary_struct_size"] == 104
    assert result["kernel_launch_descriptor_pointer_size"] == 8
    assert result["kernel_launch_descriptor_grid_x"] == 2
    assert result["kernel_launch_descriptor_block_x"] == 4
    assert result["kernel_launch_descriptor_row_offset"] == 0
    assert result["kernel_launch_descriptor_row_limit"] == 7
    assert result["kernel_launch_descriptor_rows_per_program"] == 4
    assert int(result["kernel_launch_descriptor_row_hash_accumulator"], 16) == 1
    assert int(result["kernel_launch_descriptor_field_read_hash_accumulator"], 16) == 2
    assert int(result["kernel_launch_descriptor_row_metadata_hash_accumulator"], 16) == 3
    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in stub_payload["requested_macros"]
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in stub_payload["requested_macros"]
    assert module.KERNEL_LAUNCH_DESCRIPTOR_MACRO in stub_payload["requested_macros"]
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_descriptor_field_read_path"
        ]
        == "kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_descriptor_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_descriptor_payload_bytes"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_descriptor_passed_to_kernel"
        ]
        is False
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_descriptor_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_kernel_launch_descriptor_packet_chain_depth"
        ]
        == 9
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_kernel_launch_context(
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
            "--require-kernel-launch-context-abi",
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
    assert args.require_launch_envelope_args_abi is False
    assert args.require_launch_envelope_args_ptr_abi is False
    assert args.require_kernel_launch_descriptor_abi is False
    assert result["require_launch_envelope_args_abi"] is True
    assert result["require_launch_envelope_args_ptr_abi"] is True
    assert result["require_kernel_launch_descriptor_abi"] is True
    assert result["require_kernel_launch_context_abi"] is True
    assert result["kernel_launch_context_checked"] is True
    assert (
        result["kernel_launch_context_abi_name"]
        == "premap_future_kernel_native_consumer_kernel_launch_context_abi_v1"
    )
    assert (
        result["kernel_launch_context_mode"]
        == "readonly_future_kernel_native_consumer_kernel_launch_context_abi"
    )
    assert (
        result["kernel_launch_context_source"]
        == "premap_future_kernel_native_consumer_kernel_launch_descriptor_abi_v1"
    )
    assert result["kernel_launch_context_error_count"] == 0
    assert result["kernel_launch_context_all_handle_fields_read"] is True
    assert result["kernel_launch_context_packet_chain_depth"] == 10
    assert result["kernel_launch_context_version"] == 1
    assert result["kernel_launch_context_struct_size"] == 64
    assert result["kernel_launch_context_struct_align"] == 8
    assert result["kernel_launch_context_launch_descriptor_struct_size"] == 80
    assert result["kernel_launch_context_summary_struct_size"] == 104
    assert result["kernel_launch_context_pointer_size"] == 8
    assert result["kernel_launch_context_device_ordinal"] == module.LAB_DEFAULT_GPU_DEVICE
    assert result["kernel_launch_context_stream_domain"] == 0
    assert result["kernel_launch_context_payload_bytes"] == 0
    assert result["kernel_launch_context_payload_deref_allowed"] is False
    assert result["kernel_launch_context_passed_to_kernel"] is False
    assert result["kernel_launch_context_kernel_arg_pass_allowed"] is False
    assert result["kernel_launch_context_changes_kernel_launch_args"] is False
    assert result["kernel_launch_context_current_wna16_arg_compatible"] is False
    assert (
        result["kernel_launch_context_requires_wna16_arg_reinterpretation"] is False
    )
    assert int(result["kernel_launch_context_row_hash_accumulator"], 16) == 1
    assert int(result["kernel_launch_context_field_read_hash_accumulator"], 16) == 2
    assert int(result["kernel_launch_context_row_metadata_hash_accumulator"], 16) == 3
    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in stub_payload["requested_macros"]
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in stub_payload["requested_macros"]
    assert module.KERNEL_LAUNCH_DESCRIPTOR_MACRO in stub_payload["requested_macros"]
    assert module.KERNEL_LAUNCH_CONTEXT_MACRO in stub_payload["requested_macros"]
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_kernel_launch_context=True,
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_context_field_read_path"
        ]
        == "kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_context_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_context_payload_bytes"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_kernel_launch_context_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_kernel_launch_context_packet_chain_depth"
        ]
        == 10
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_invocation(
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
            "--require-kernel-invocation-abi",
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
    assert args.require_launch_envelope_args_abi is False
    assert args.require_launch_envelope_args_ptr_abi is False
    assert args.require_kernel_launch_descriptor_abi is False
    assert args.require_kernel_launch_context_abi is False
    assert result["require_launch_envelope_args_abi"] is True
    assert result["require_launch_envelope_args_ptr_abi"] is True
    assert result["require_kernel_launch_descriptor_abi"] is True
    assert result["require_kernel_launch_context_abi"] is True
    assert result["require_kernel_invocation_abi"] is True
    assert result["kernel_invocation_checked"] is True
    assert (
        result["kernel_invocation_abi_name"]
        == "premap_future_kernel_native_consumer_invocation_abi_v1"
    )
    assert (
        result["kernel_invocation_mode"]
        == "readonly_future_kernel_native_consumer_invocation_abi"
    )
    assert (
        result["kernel_invocation_source"]
        == "premap_future_kernel_native_consumer_kernel_launch_context_abi_v1"
    )
    assert result["kernel_invocation_error_count"] == 0
    assert result["kernel_invocation_all_handle_fields_read"] is True
    assert result["kernel_invocation_packet_chain_depth"] == 11
    assert result["kernel_invocation_version"] == 1
    assert result["kernel_invocation_struct_size"] == 72
    assert result["kernel_invocation_struct_align"] == 8
    assert result["kernel_invocation_context_struct_size"] == 64
    assert result["kernel_invocation_summary_struct_size"] == 104
    assert result["kernel_invocation_pointer_size"] == 8
    assert result["kernel_invocation_id"] == 1
    assert result["kernel_invocation_device_ordinal"] == module.LAB_DEFAULT_GPU_DEVICE
    assert result["kernel_invocation_stream_domain"] == 0
    assert result["kernel_invocation_payload_bytes"] == 0
    assert result["kernel_invocation_payload_deref_allowed"] is False
    assert result["kernel_invocation_passed_to_kernel"] is False
    assert result["kernel_invocation_kernel_arg_pass_allowed"] is False
    assert result["kernel_invocation_changes_kernel_launch_args"] is False
    assert result["kernel_invocation_current_wna16_arg_compatible"] is False
    assert result["kernel_invocation_requires_wna16_arg_reinterpretation"] is False
    assert int(result["kernel_invocation_row_hash_accumulator"], 16) == 1
    assert int(result["kernel_invocation_field_read_hash_accumulator"], 16) == 2
    assert int(result["kernel_invocation_row_metadata_hash_accumulator"], 16) == 3
    assert module.LAUNCH_ENVELOPE_ARGS_MACRO in stub_payload["requested_macros"]
    assert module.LAUNCH_ENVELOPE_ARGS_PTR_MACRO in stub_payload["requested_macros"]
    assert module.KERNEL_LAUNCH_DESCRIPTOR_MACRO in stub_payload["requested_macros"]
    assert module.KERNEL_LAUNCH_CONTEXT_MACRO in stub_payload["requested_macros"]
    assert module.INVOCATION_MACRO in stub_payload["requested_macros"]
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_invocation=True,
    )
    assert (
        stub_payload["future_kernel_native_consumer_invocation_field_read_path"]
        == "invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload["future_kernel_native_consumer_invocation_summary_row_count"]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_invocation_summary_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload["future_kernel_native_consumer_invocation_payload_bytes"]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_invocation_kernel_arg_pass_allowed"
        ]
        is False
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_invocation_packet_chain_depth"
        ]
        == 11
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_invocation_entry(
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
            "--require-kernel-invocation-entry-abi",
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
    assert result["require_kernel_invocation_abi"] is True
    assert result["require_kernel_invocation_entry_abi"] is True
    assert result["kernel_invocation_checked"] is True
    assert result["kernel_invocation_entry_checked"] is True
    assert (
        result["kernel_invocation_entry_abi_name"]
        == "premap_future_kernel_native_consumer_invocation_entry_abi_v1"
    )
    assert (
        result["kernel_invocation_entry_mode"]
        == "readonly_future_kernel_native_consumer_invocation_entry_abi"
    )
    assert (
        result["kernel_invocation_entry_source"]
        == "premap_future_kernel_native_consumer_invocation_abi_v1_by_value"
    )
    assert result["kernel_invocation_entry_error_count"] == 0
    assert result["kernel_invocation_entry_all_handle_fields_read"] is True
    assert result["kernel_invocation_entry_packet_chain_depth"] == 11
    assert result["kernel_invocation_entry_payload_bytes"] == 0
    assert result["kernel_invocation_entry_payload_deref_allowed"] is False
    assert result["kernel_invocation_entry_passed_to_kernel"] is False
    assert result["kernel_invocation_entry_kernel_arg_pass_allowed"] is False
    assert result["kernel_invocation_entry_changes_kernel_launch_args"] is False
    assert result["kernel_invocation_entry_current_wna16_arg_compatible"] is False
    assert (
        result["kernel_invocation_entry_requires_wna16_arg_reinterpretation"]
        is False
    )
    assert int(result["kernel_invocation_entry_row_hash_accumulator"], 16) == 1
    assert int(result["kernel_invocation_entry_field_read_hash_accumulator"], 16) == 2
    assert int(result["kernel_invocation_entry_row_metadata_hash_accumulator"], 16) == 3
    assert module.INVOCATION_MACRO in stub_payload["requested_macros"]
    assert module.INVOCATION_ENTRY_MACRO in stub_payload["requested_macros"]
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_invocation_entry=True,
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_invocation_entry_field_read_path"
        ]
        == "by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_invocation_entry_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_invocation_entry_summary_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_invocation_entry_payload_bytes"
        ]
        == 0
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_invocation_entry_packet_chain_depth"
        ]
        == 11
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_endpoint(
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
            "--require-kernel-endpoint-abi",
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
    assert result["require_kernel_invocation_abi"] is True
    assert result["require_kernel_invocation_entry_abi"] is True
    assert result["require_kernel_endpoint_abi"] is True
    assert result["kernel_endpoint_checked"] is True
    assert (
        result["kernel_endpoint_abi_name"]
        == "premap_future_kernel_native_consumer_endpoint_abi_v1"
    )
    assert (
        result["kernel_endpoint_mode"]
        == "readonly_future_kernel_native_consumer_endpoint_abi"
    )
    assert (
        result["kernel_endpoint_source"]
        == "premap_future_kernel_native_consumer_invocation_entry_abi_v1"
    )
    assert result["kernel_endpoint_error_count"] == 0
    assert result["kernel_endpoint_all_handle_fields_read"] is True
    assert result["kernel_endpoint_packet_chain_depth"] == 12
    assert result["kernel_endpoint_payload_bytes"] == 0
    assert result["kernel_endpoint_payload_deref_allowed"] is False
    assert result["kernel_endpoint_passed_to_kernel"] is False
    assert result["kernel_endpoint_kernel_arg_pass_allowed"] is False
    assert result["kernel_endpoint_changes_kernel_launch_args"] is False
    assert result["kernel_endpoint_current_wna16_arg_compatible"] is False
    assert result["kernel_endpoint_requires_wna16_arg_reinterpretation"] is False
    assert int(result["kernel_endpoint_row_hash_accumulator"], 16) == 1
    assert int(result["kernel_endpoint_field_read_hash_accumulator"], 16) == 2
    assert int(result["kernel_endpoint_row_metadata_hash_accumulator"], 16) == 3
    assert module.INVOCATION_ENTRY_MACRO in stub_payload["requested_macros"]
    assert module.ENDPOINT_MACRO in stub_payload["requested_macros"]
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_endpoint=True,
    )
    assert (
        stub_payload["future_kernel_native_consumer_endpoint_field_read_path"]
        == "endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload["future_kernel_native_consumer_endpoint_summary_row_count"]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_endpoint_summary_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert stub_payload["future_kernel_native_consumer_endpoint_payload_bytes"] == 0
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_endpoint_packet_chain_depth"
        ]
        == 12
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_endpoint_ptr(
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
            "--require-kernel-endpoint-ptr-abi",
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
    assert args.require_kernel_endpoint_abi is False
    assert result["require_kernel_endpoint_abi"] is True
    assert result["require_kernel_endpoint_ptr_abi"] is True
    assert result["kernel_endpoint_checked"] is True
    assert result["kernel_endpoint_ptr_checked"] is True
    assert (
        result["kernel_endpoint_ptr_abi_name"]
        == "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
    )
    assert (
        result["kernel_endpoint_ptr_mode"]
        == "readonly_future_kernel_native_consumer_endpoint_ptr_abi"
    )
    assert (
        result["kernel_endpoint_ptr_source"]
        == "premap_future_kernel_native_consumer_endpoint_abi_v1"
    )
    assert result["kernel_endpoint_ptr_error_count"] == 0
    assert result["kernel_endpoint_ptr_all_handle_fields_read"] is True
    assert result["kernel_endpoint_ptr_packet_chain_depth"] == 13
    assert result["kernel_endpoint_ptr_version"] == 1
    assert result["kernel_endpoint_ptr_payload_bytes"] == 0
    assert result["kernel_endpoint_ptr_payload_deref_allowed"] is False
    assert result["kernel_endpoint_ptr_passed_to_kernel"] is False
    assert result["kernel_endpoint_ptr_kernel_arg_pass_allowed"] is False
    assert result["kernel_endpoint_ptr_changes_kernel_launch_args"] is False
    assert result["kernel_endpoint_ptr_current_wna16_arg_compatible"] is False
    assert (
        result["kernel_endpoint_ptr_requires_wna16_arg_reinterpretation"]
        is False
    )
    assert int(result["kernel_endpoint_ptr_row_hash_accumulator"], 16) == 1
    assert int(result["kernel_endpoint_ptr_field_read_hash_accumulator"], 16) == 2
    assert int(result["kernel_endpoint_ptr_row_metadata_hash_accumulator"], 16) == 3
    assert module.ENDPOINT_MACRO in stub_payload["requested_macros"]
    assert module.ENDPOINT_PTR_MACRO in stub_payload["requested_macros"]
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_endpoint_ptr=True,
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_endpoint_ptr_field_read_path"
        ]
        == "endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload["future_kernel_native_consumer_endpoint_ptr_summary_row_count"]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_endpoint_ptr_summary_scale_metadata_handle_read_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload["future_kernel_native_consumer_endpoint_ptr_payload_bytes"]
        == 0
    )
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_endpoint_ptr_packet_chain_depth"
        ]
        == 13
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_wna16_adjacent_typed_slot(
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
            "--require-wna16-adjacent-typed-slot",
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
    assert result["require_wna16_adjacent_typed_slot"] is True
    assert result["require_kernel_endpoint_ptr_abi"] is True
    assert result["kernel_endpoint_ptr_checked"] is True
    assert result["wna16_adjacent_typed_slot_checked"] is True
    assert (
        result["wna16_adjacent_typed_slot_name"]
        == "premap_wna16_adjacent_typed_consumer_slot_v1"
    )
    assert (
        result["wna16_adjacent_typed_slot_mode"]
        == "readonly_wna16_adjacent_typed_consumer_slot"
    )
    assert (
        result["wna16_adjacent_typed_slot_source"]
        == "premap_future_kernel_native_consumer_endpoint_ptr_abi_v1"
    )
    assert result["wna16_adjacent_typed_slot_row_count"] == 7
    assert result["wna16_adjacent_typed_slot_row_ok_count"] == 7
    assert result["wna16_adjacent_typed_slot_error_count"] == 0
    assert result["wna16_adjacent_typed_slot_all_handle_fields_read"] is True
    assert result["wna16_adjacent_typed_slot_packet_chain_depth"] == 14
    assert result["wna16_adjacent_typed_slot_payload_bytes"] == 0
    assert result["wna16_adjacent_typed_slot_passed_to_kernel"] is False
    assert result["wna16_adjacent_typed_slot_changes_kernel_launch_args"] is False
    assert result["wna16_adjacent_typed_slot_current_wna16_arg_compatible"] is False
    assert (
        result["wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation"]
        is False
    )
    assert result["wna16_adjacent_typed_slot_explicit_typed_abi_slot"] is True
    assert result["wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot"] is False
    assert (
        result["wna16_adjacent_typed_slot_row_hash_accumulator"]
        == result["kernel_endpoint_ptr_row_hash_accumulator"]
    )
    assert (
        result["wna16_adjacent_typed_slot_field_read_hash_accumulator"]
        == result["kernel_endpoint_ptr_field_read_hash_accumulator"]
    )
    assert module.ENDPOINT_PTR_MACRO in stub_payload["requested_macros"]
    assert (
        module.WNA16_ADJACENT_TYPED_SLOT_MACRO in stub_payload["requested_macros"]
    )
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_wna16_adjacent_typed_slot=True,
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_checked"
        ]
        is True
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_ok_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_error_count"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_payload_bytes"
        ]
        == 0
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_passed_to_kernel"
        ]
        is False
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_current_wna16_arg_compatible"
        ]
        is False
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_future_wna16_variant(
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
            "--require-future-wna16-typed-slot-kernel-variant",
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
    assert result["require_future_wna16_typed_slot_kernel_variant"] is True
    assert result["require_wna16_adjacent_typed_slot"] is True
    assert result["future_wna16_typed_slot_kernel_variant_checked"] is True
    assert (
        result["future_wna16_typed_slot_kernel_variant_name"]
        == "premap_future_wna16_typed_slot_kernel_variant_v1"
    )
    assert (
        result["future_wna16_typed_slot_kernel_variant_mode"]
        == "readonly_future_wna16_typed_slot_kernel_variant"
    )
    assert (
        result["future_wna16_typed_slot_kernel_variant_source"]
        == "premap_wna16_adjacent_typed_consumer_slot_v1"
    )
    assert result["future_wna16_typed_slot_kernel_variant_row_count"] == 7
    assert result["future_wna16_typed_slot_kernel_variant_row_ok_count"] == 7
    assert result["future_wna16_typed_slot_kernel_variant_error_count"] == 0
    assert (
        result["future_wna16_typed_slot_kernel_variant_all_handle_fields_read"]
        is True
    )
    assert result["future_wna16_typed_slot_kernel_variant_packet_chain_depth"] == 15
    assert result["future_wna16_typed_slot_kernel_variant_payload_bytes"] == 0
    assert result["future_wna16_typed_slot_kernel_variant_passed_to_kernel"] is False
    assert (
        result["future_wna16_typed_slot_kernel_variant_changes_kernel_launch_args"]
        is False
    )
    assert (
        result[
            "future_wna16_typed_slot_kernel_variant_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        result[
            "future_wna16_typed_slot_kernel_variant_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert (
        result["future_wna16_typed_slot_kernel_variant_explicit_typed_abi_slot"]
        is True
    )
    assert (
        result["future_wna16_typed_slot_kernel_variant_reuses_current_wna16_arg_slot"]
        is False
    )
    assert (
        module.FUTURE_WNA16_TYPED_SLOT_KERNEL_VARIANT_MACRO
        in stub_payload["requested_macros"]
    )
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_future_wna16_typed_slot_kernel_variant=True,
    )
    assert (
        stub_payload["future_wna16_typed_slot_kernel_variant_checked"] is True
    )
    assert stub_payload[
        "future_wna16_typed_slot_kernel_variant_summary_row_count"
    ] == 7
    assert stub_payload[
        "future_wna16_typed_slot_kernel_variant_summary_error_count"
    ] == 0
    assert (
        stub_payload["future_wna16_typed_slot_kernel_variant_passed_to_kernel"]
        is False
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_future_wna16_accept_slot(
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
            "--require-future-wna16-kernel-accept-typed-slot",
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
    assert result["require_future_wna16_kernel_accept_typed_slot"] is True
    assert result["require_wna16_adjacent_typed_slot"] is True
    assert result["future_wna16_kernel_accept_typed_slot_checked"] is True
    assert (
        result["future_wna16_kernel_accept_typed_slot_name"]
        == "premap_future_wna16_kernel_accept_typed_slot_v1"
    )
    assert (
        result["future_wna16_kernel_accept_typed_slot_mode"]
        == "readonly_future_wna16_kernel_accept_typed_slot"
    )
    assert (
        result["future_wna16_kernel_accept_typed_slot_source"]
        == "premap_wna16_adjacent_typed_consumer_slot_v1"
    )
    assert result["future_wna16_kernel_accept_typed_slot_row_count"] == 7
    assert result["future_wna16_kernel_accept_typed_slot_row_ok_count"] == 7
    assert result["future_wna16_kernel_accept_typed_slot_error_count"] == 0
    assert result["future_wna16_kernel_accept_typed_slot_all_handle_fields_read"] is True
    assert result["future_wna16_kernel_accept_typed_slot_packet_chain_depth"] == 15
    assert result["future_wna16_kernel_accept_typed_slot_payload_bytes"] == 0
    assert result["future_wna16_kernel_accept_typed_slot_passed_to_kernel"] is False
    assert (
        result["future_wna16_kernel_accept_typed_slot_changes_kernel_launch_args"]
        is False
    )
    assert (
        result["future_wna16_kernel_accept_typed_slot_current_wna16_arg_compatible"]
        is False
    )
    assert (
        result[
            "future_wna16_kernel_accept_typed_slot_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert result["future_wna16_kernel_accept_typed_slot_explicit_typed_abi_slot"] is True
    assert result["future_wna16_kernel_accept_typed_slot_reuses_current_wna16_arg_slot"] is False
    assert (
        module.FUTURE_WNA16_KERNEL_ACCEPT_TYPED_SLOT_MACRO
        in stub_payload["requested_macros"]
    )
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_future_wna16_kernel_accept_typed_slot=True,
    )
    assert stub_payload["future_wna16_kernel_accept_typed_slot_checked"] is True
    assert (
        stub_payload["future_wna16_kernel_accept_typed_slot_summary_row_count"]
        == 7
    )
    assert (
        stub_payload["future_wna16_kernel_accept_typed_slot_summary_error_count"]
        == 0
    )
    assert stub_payload["future_wna16_kernel_accept_typed_slot_passed_to_kernel"] is False


def test_online_merged_arg_slot_canary_dry_run_accepts_future_wna16_kernel_side_execution(
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
            "--require-future-wna16-kernel-side-consumer-execution",
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
    assert result["require_future_wna16_kernel_accept_typed_slot"] is True
    assert result["require_future_wna16_kernel_side_consumer_execution"] is True
    assert result["future_wna16_kernel_side_consumer_execution_checked"] is True
    assert (
        result["future_wna16_kernel_side_consumer_execution_name"]
        == "premap_future_wna16_kernel_side_consumer_execution_v1"
    )
    assert (
        result["future_wna16_kernel_side_consumer_execution_mode"]
        == "readonly_future_wna16_kernel_side_consumer_execution"
    )
    assert (
        result["future_wna16_kernel_side_consumer_execution_source"]
        == "premap_future_wna16_kernel_accept_typed_slot_v1"
    )
    assert result["future_wna16_kernel_side_consumer_execution_row_count"] == 7
    assert result["future_wna16_kernel_side_consumer_execution_row_ok_count"] == 7
    assert result["future_wna16_kernel_side_consumer_execution_error_count"] == 0
    assert (
        result["future_wna16_kernel_side_consumer_execution_all_handle_fields_read"]
        is True
    )
    assert (
        result["future_wna16_kernel_side_consumer_execution_packet_chain_depth"]
        == 16
    )
    assert result["future_wna16_kernel_side_consumer_execution_payload_bytes"] == 0
    assert (
        result["future_wna16_kernel_side_consumer_execution_passed_to_kernel"]
        is False
    )
    assert (
        result["future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args"]
        is False
    )
    assert (
        result[
            "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        result[
            "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert (
        result["future_wna16_kernel_side_consumer_execution_reuses_current_wna16_arg_slot"]
        is False
    )
    assert (
        module.FUTURE_WNA16_KERNEL_SIDE_CONSUMER_EXECUTION_MACRO
        in stub_payload["requested_macros"]
    )
    assert module.FUTURE_WNA16_KERNEL_ACCEPT_TYPED_SLOT_MACRO in stub_payload[
        "requested_macros"
    ]
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_future_wna16_kernel_side_consumer_execution=True,
    )
    assert (
        stub_payload["future_wna16_kernel_side_consumer_execution_checked"]
        is True
    )
    assert (
        stub_payload["future_wna16_kernel_side_consumer_execution_row_count"]
        == 7
    )
    assert (
        stub_payload[
            "future_wna16_kernel_side_consumer_execution_descriptor_ptr_read_row_ok_count"
        ]
        == 7
    )


def test_online_merged_arg_slot_canary_dry_run_accepts_future_wna16_single_field_handoff(
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
            "--require-future-wna16-single-field-handoff-canary",
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
    assert result["require_future_wna16_kernel_accept_typed_slot"] is True
    assert result["require_future_wna16_kernel_side_consumer_execution"] is True
    assert result["require_future_wna16_single_field_handoff_canary"] is True
    assert result["future_wna16_single_field_handoff_canary_checked"] is True
    assert (
        result["future_wna16_single_field_handoff_canary_name"]
        == "premap_future_wna16_single_field_handoff_canary_v1"
    )
    assert (
        result["future_wna16_single_field_handoff_canary_abi_name"]
        == "premap_future_wna16_single_field_handoff_canary_v1"
    )
    assert (
        result["future_wna16_single_field_handoff_canary_mode"]
        == "readonly_future_wna16_single_field_handoff_canary"
    )
    assert (
        result["future_wna16_single_field_handoff_canary_source"]
        == "premap_future_wna16_kernel_side_consumer_execution_v1"
    )
    assert (
        result["future_wna16_single_field_handoff_canary_field_read_path"]
        == "future_wna16_single_field_handoff_to_future_wna16_kernel_side_execution_to_accepted_typed_slot_to_program_view_rows"
    )
    assert result["future_wna16_single_field_handoff_canary_field_name"] == (
        "scale_metadata_handle"
    )
    assert result["future_wna16_single_field_handoff_canary_field_kind"] == 3
    assert result["future_wna16_single_field_handoff_canary_field_mask"] == 4
    assert result["future_wna16_single_field_handoff_canary_row_count"] == 7
    assert result["future_wna16_single_field_handoff_canary_row_ok_count"] == 7
    assert result["future_wna16_single_field_handoff_canary_error_count"] == 0
    assert result["future_wna16_single_field_handoff_canary_payload_bytes"] == 0
    assert result["future_wna16_single_field_handoff_canary_live_enabled"] is False
    assert result["future_wna16_single_field_handoff_canary_passed_to_kernel"] is False
    assert (
        result[
            "future_wna16_single_field_handoff_canary_changes_kernel_launch_args"
        ]
        is False
    )
    assert (
        result[
            "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible"
        ]
        is False
    )
    assert (
        result[
            "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation"
        ]
        is False
    )
    assert (
        result["future_wna16_single_field_handoff_canary_explicit_typed_abi_slot"]
        is True
    )
    assert (
        result["future_wna16_single_field_handoff_canary_reuses_current_wna16_arg_slot"]
        is False
    )
    assert (
        module.FUTURE_WNA16_SINGLE_FIELD_HANDOFF_CANARY_MACRO
        in stub_payload["requested_macros"]
    )
    assert (
        module.FUTURE_WNA16_KERNEL_SIDE_CONSUMER_EXECUTION_MACRO
        in stub_payload["requested_macros"]
    )
    assert stub_payload["requested_macros"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_future_wna16_single_field_handoff_canary=True,
    )


def test_online_merged_arg_slot_canary_mock_real_run_accepts_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    dry_stub = tmp_path / "stub_dry.json"
    real_stub = tmp_path / "stub_real.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    dry_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-kernel-invocation-abi",
            "--merged-output-json",
            str(tmp_path / "merged_dry.json"),
            "--stub-output-json",
            str(dry_stub),
            "--output-json",
            str(tmp_path / "report_dry.json"),
            "--dry-run",
        ]
    )
    dry_result = module.run_canary(dry_args)
    assert dry_result["passed"] is True
    dry_stub_payload = json.loads(dry_stub.read_text(encoding="utf-8"))
    captured: dict[str, object] = {}

    def fake_run_stub(namespace):
        captured["macro"] = list(namespace.macro)
        captured["input_json"] = str(namespace.input_json)
        captured["dispatch_row_offset"] = namespace.dispatch_row_offset
        captured["dispatch_row_limit"] = namespace.dispatch_row_limit
        captured["fault_invocation_device_ordinal"] = (
            namespace.fault_invocation_device_ordinal
        )
        captured["fault_invocation_stream_domain"] = (
            namespace.fault_invocation_stream_domain
        )
        payload = dict(dry_stub_payload)
        payload.pop("dry_run", None)
        payload["input_json"] = str(namespace.input_json)
        payload["requested_macros"] = list(namespace.macro)
        return payload

    monkeypatch.setattr(module, "run_stub", fake_run_stub)
    real_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-kernel-invocation-abi",
            "--merged-output-json",
            str(tmp_path / "merged_real.json"),
            "--stub-output-json",
            str(real_stub),
            "--output-json",
            str(tmp_path / "report_real.json"),
        ]
    )

    result = module.run_canary(real_args)
    stub_payload = json.loads(real_stub.read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["require_kernel_invocation_abi"] is True
    assert result["kernel_invocation_checked"] is True
    assert result["kernel_invocation_all_handle_fields_read"] is True
    assert result["kernel_invocation_passed_to_kernel"] is False
    assert result["kernel_invocation_kernel_arg_pass_allowed"] is False
    assert result["kernel_invocation_current_wna16_arg_compatible"] is False
    assert captured["macro"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_invocation=True,
    )
    assert captured["fault_invocation_device_ordinal"] is False
    assert captured["fault_invocation_stream_domain"] is False
    assert captured["dispatch_row_offset"] == 0
    assert captured["dispatch_row_limit"] == 7
    assert stub_payload["requested_macros"] == captured["macro"]
    assert module.INVOCATION_MACRO in stub_payload["requested_macros"]
    assert (
        stub_payload["future_kernel_native_consumer_invocation_packet_chain_depth"]
        == 11
    )


def test_online_merged_arg_slot_canary_mock_real_run_accepts_endpoint_ptr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    dry_stub = tmp_path / "stub_dry.json"
    real_stub = tmp_path / "stub_real.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    dry_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-kernel-endpoint-ptr-abi",
            "--merged-output-json",
            str(tmp_path / "merged_dry.json"),
            "--stub-output-json",
            str(dry_stub),
            "--output-json",
            str(tmp_path / "report_dry.json"),
            "--dry-run",
        ]
    )
    dry_result = module.run_canary(dry_args)
    assert dry_result["passed"] is True
    dry_stub_payload = json.loads(dry_stub.read_text(encoding="utf-8"))
    captured: dict[str, object] = {}

    def fake_run_stub(namespace):
        captured["macro"] = list(namespace.macro)
        captured["input_json"] = str(namespace.input_json)
        captured["dispatch_row_offset"] = namespace.dispatch_row_offset
        captured["dispatch_row_limit"] = namespace.dispatch_row_limit
        payload = dict(dry_stub_payload)
        payload.pop("dry_run", None)
        payload["input_json"] = str(namespace.input_json)
        payload["requested_macros"] = list(namespace.macro)
        return payload

    monkeypatch.setattr(module, "run_stub", fake_run_stub)
    real_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-kernel-endpoint-ptr-abi",
            "--merged-output-json",
            str(tmp_path / "merged_real.json"),
            "--stub-output-json",
            str(real_stub),
            "--output-json",
            str(tmp_path / "report_real.json"),
        ]
    )

    result = module.run_canary(real_args)
    stub_payload = json.loads(real_stub.read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["require_kernel_endpoint_abi"] is True
    assert result["require_kernel_endpoint_ptr_abi"] is True
    assert result["kernel_endpoint_ptr_checked"] is True
    assert result["kernel_endpoint_ptr_all_handle_fields_read"] is True
    assert result["kernel_endpoint_ptr_payload_bytes"] == 0
    assert result["kernel_endpoint_ptr_payload_deref_allowed"] is False
    assert result["kernel_endpoint_ptr_passed_to_kernel"] is False
    assert result["kernel_endpoint_ptr_kernel_arg_pass_allowed"] is False
    assert result["kernel_endpoint_ptr_changes_kernel_launch_args"] is False
    assert result["kernel_endpoint_ptr_current_wna16_arg_compatible"] is False
    assert (
        result["kernel_endpoint_ptr_requires_wna16_arg_reinterpretation"]
        is False
    )
    assert captured["macro"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_endpoint_ptr=True,
    )
    assert captured["dispatch_row_offset"] == 0
    assert captured["dispatch_row_limit"] == 7
    assert stub_payload["requested_macros"] == captured["macro"]
    assert module.ENDPOINT_PTR_MACRO in stub_payload["requested_macros"]
    assert (
        stub_payload[
            "future_kernel_native_consumer_endpoint_ptr_field_read_path"
        ]
        == "endpoint_ptr_to_endpoint_to_by_value_invocation_to_kernel_launch_context_to_kernel_launch_descriptor_to_launch_envelope_args_ptr_to_launch_envelope_args_to_entry_args_ptr_to_kernel_entry_args_to_kernel_arg_packet_to_program_view_rows"
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_endpoint_ptr_packet_chain_depth"
        ]
        == 13
    )
    assert (
        stub_payload["future_kernel_native_consumer_endpoint_ptr_passed_to_kernel"]
        is False
    )


def test_online_merged_arg_slot_canary_mock_real_run_accepts_wna16_adjacent_typed_slot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    dry_stub = tmp_path / "stub_dry.json"
    real_stub = tmp_path / "stub_real.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    dry_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-wna16-adjacent-typed-slot",
            "--merged-output-json",
            str(tmp_path / "merged_dry.json"),
            "--stub-output-json",
            str(dry_stub),
            "--output-json",
            str(tmp_path / "report_dry.json"),
            "--dry-run",
        ]
    )
    dry_result = module.run_canary(dry_args)
    assert dry_result["passed"] is True
    dry_stub_payload = json.loads(dry_stub.read_text(encoding="utf-8"))
    captured: dict[str, object] = {}

    def fake_run_stub(namespace):
        captured["macro"] = list(namespace.macro)
        captured["input_json"] = str(namespace.input_json)
        captured["dispatch_row_offset"] = namespace.dispatch_row_offset
        captured["dispatch_row_limit"] = namespace.dispatch_row_limit
        payload = dict(dry_stub_payload)
        payload.pop("dry_run", None)
        payload["input_json"] = str(namespace.input_json)
        payload["requested_macros"] = list(namespace.macro)
        return payload

    monkeypatch.setattr(module, "run_stub", fake_run_stub)
    real_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-wna16-adjacent-typed-slot",
            "--merged-output-json",
            str(tmp_path / "merged_real.json"),
            "--stub-output-json",
            str(real_stub),
            "--output-json",
            str(tmp_path / "report_real.json"),
        ]
    )

    result = module.run_canary(real_args)
    stub_payload = json.loads(real_stub.read_text(encoding="utf-8"))

    assert result["passed"] is True
    assert result["require_wna16_adjacent_typed_slot"] is True
    assert result["require_kernel_endpoint_ptr_abi"] is True
    assert result["kernel_endpoint_ptr_checked"] is True
    assert result["kernel_endpoint_ptr_all_handle_fields_read"] is True
    assert result["wna16_adjacent_typed_slot_checked"] is True
    assert result["wna16_adjacent_typed_slot_all_handle_fields_read"] is True
    assert result["wna16_adjacent_typed_slot_packet_chain_depth"] == 14
    assert result["wna16_adjacent_typed_slot_row_count"] == 7
    assert result["wna16_adjacent_typed_slot_row_ok_count"] == 7
    assert result["wna16_adjacent_typed_slot_error_count"] == 0
    assert result["wna16_adjacent_typed_slot_payload_bytes"] == 0
    assert result["wna16_adjacent_typed_slot_passed_to_kernel"] is False
    assert result["wna16_adjacent_typed_slot_changes_kernel_launch_args"] is False
    assert result["wna16_adjacent_typed_slot_current_wna16_arg_compatible"] is False
    assert (
        result["wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation"]
        is False
    )
    assert result["wna16_adjacent_typed_slot_explicit_typed_abi_slot"] is True
    assert result["wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot"] is False
    assert captured["macro"] == module.arg_slot_macros(
        "scale_metadata_handle",
        include_wna16_adjacent_typed_slot=True,
    )
    assert captured["dispatch_row_offset"] == 0
    assert captured["dispatch_row_limit"] == 7
    assert stub_payload["requested_macros"] == captured["macro"]
    assert module.ENDPOINT_PTR_MACRO in stub_payload["requested_macros"]
    assert (
        module.WNA16_ADJACENT_TYPED_SLOT_MACRO in stub_payload["requested_macros"]
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_checked"
        ]
        is True
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_summary_row_count"
        ]
        == 7
    )
    assert (
        stub_payload[
            "future_kernel_native_consumer_wna16_adjacent_typed_slot_passed_to_kernel"
        ]
        is False
    )


def test_online_merged_arg_slot_canary_rejects_bool_int_boundary_confusion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_module()
    first = tmp_path / "input0.json"
    second = tmp_path / "input1.json"
    runner = tmp_path / "runner.json"
    dry_stub = tmp_path / "stub_dry.json"
    real_stub = tmp_path / "stub_real.json"
    _write_input(first, start=0, rows=3, export_index=0)
    _write_input(second, start=100, rows=4, export_index=1)
    _write_runner(runner, [first, second])

    dry_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-kernel-endpoint-ptr-abi",
            "--merged-output-json",
            str(tmp_path / "merged_dry.json"),
            "--stub-output-json",
            str(dry_stub),
            "--output-json",
            str(tmp_path / "report_dry.json"),
            "--dry-run",
        ]
    )
    assert module.run_canary(dry_args)["passed"] is True
    dry_stub_payload = json.loads(dry_stub.read_text(encoding="utf-8"))

    def fake_run_stub(namespace):
        payload = dict(dry_stub_payload)
        payload.pop("dry_run", None)
        payload["input_json"] = str(namespace.input_json)
        payload["requested_macros"] = list(namespace.macro)
        payload["passed_to_kernel"] = 0
        return payload

    monkeypatch.setattr(module, "run_stub", fake_run_stub)
    real_args = module.build_parser().parse_args(
        [
            "--runner-json",
            str(runner),
            "--min-source-count",
            "2",
            "--min-total-rows",
            "7",
            "--block-threads",
            "4",
            "--require-kernel-endpoint-ptr-abi",
            "--merged-output-json",
            str(tmp_path / "merged_real.json"),
            "--stub-output-json",
            str(real_stub),
            "--output-json",
            str(tmp_path / "report_real.json"),
        ]
    )

    result = module.run_canary(real_args)

    assert result["passed"] is False
    assert any("passed_to_kernel_mismatch" in item for item in result["failures"])


def test_online_merged_arg_slot_canary_tail_window_checks_launch_envelope_args(
    tmp_path: Path,
):
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
            "--require-launch-envelope-args-abi",
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
    assert result["launch_envelope_args_checked"] is True
    assert result["launch_envelope_args_all_handle_fields_read"] is True
    assert result["launch_envelope_args_grid_x"] == 1
    assert result["launch_envelope_args_block_x"] == 4
    assert result["launch_envelope_args_row_offset"] == 4
    assert result["launch_envelope_args_row_limit"] == 7
    assert result["launch_envelope_args_rows_per_program"] == 4
    assert (
        result["stub_summary"][
            "future_kernel_native_consumer_launch_envelope_args_summary_row_count"
        ]
        == 3
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
    assert result["stub_summary"]["future_kernel_native_consumer_view_row_count"] == 3
    assert (
        result["stub_summary"]["future_kernel_native_dispatch_consumer_grid_x"] == 1
    )


def test_online_merged_arg_slot_canary_hashchain_includes_consumer_view_projection():
    module = _load_module()
    stub = {
        "future_kernel_native_dispatch_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_dispatch_ptr_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_arg_slot_consumer_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_consumer_view_handle_projection_hash_accumulator": "abc",
        "future_kernel_native_consumer_program_view_handle_projection_hash_accumulator": "abc",
    }

    assert module._handle_projection_hashchain_equal(stub) is True

    stub["future_kernel_native_consumer_view_handle_projection_hash_accumulator"] = (
        "abd"
    )
    assert module._handle_projection_hashchain_equal(stub) is False

    stub["future_kernel_native_consumer_view_handle_projection_hash_accumulator"] = (
        "not_hex"
    )
    assert module._handle_projection_hashchain_equal(stub) is False


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
        device=module.LAB_DEFAULT_GPU_DEVICE,
        mirror_field="scale_metadata_handle",
        require_launch_envelope_args_abi=False,
    )

    assert any("future_kernel_native_dispatch_consumer_grid_x_mismatch" in item for item in failures)
    assert any(
        "future_kernel_native_dispatch_consumer_program_count_mismatch" in item
        for item in failures
    )
