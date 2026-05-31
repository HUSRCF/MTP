from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.check_premap_kernel_consumer_schema import (
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED,
    FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS,
    check_kernel_consumer_schema_artifact,
    main,
)
from tests.test_run_premap_lab_preflight import _valid_schema_payload


def _write_schema(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_kernel_consumer_schema_accepts_valid_artifact(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, _valid_schema_payload())

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["row_field_count"] == 4
    assert result["row_field_names"] == [
        "descriptor_ptr",
        "packed_weight_descriptor",
        "scale_metadata_handle",
        "aux_metadata_handle",
    ]
    assert result["row_metadata_names"] == [
        "layer_id",
        "expert_id",
        "address_key_hash",
        "row_order_hash",
        "ordered_row_hash",
    ]
    assert (
        result["future_kernel_native_consumer_dispatch_abi_name"]
        == "premap_future_kernel_native_consumer_dispatch_abi_v1"
    )
    assert (
        result["future_kernel_native_consumer_dispatch_abi_current_wna16_arg_compatible"]
        is False
    )
    assert result["future_kernel_native_consumer_abi_layout_reported"] is True
    assert (
        result["future_kernel_native_consumer_abi_layout_fields"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_FIELDS
    )
    assert (
        result["future_kernel_native_consumer_abi_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_ABI_LAYOUT_EXPECTED
    )
    assert (
        result["future_kernel_native_consumer_launch_abi_layout_fields"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_FIELDS
    )
    assert (
        result["future_kernel_native_consumer_launch_abi_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_LAUNCH_ABI_LAYOUT_EXPECTED
    )
    assert (
        result["future_kernel_native_consumer_dispatch_abi_layout_fields"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_FIELDS
    )
    assert (
        result["future_kernel_native_consumer_dispatch_abi_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_ABI_LAYOUT_EXPECTED
    )
    assert (
        result["future_kernel_native_consumer_dispatch_ptr_abi_layout_fields"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_FIELDS
    )
    assert (
        result["future_kernel_native_consumer_dispatch_ptr_abi_layout_expected"]
        == FUTURE_KERNEL_NATIVE_CONSUMER_DISPATCH_PTR_ABI_LAYOUT_EXPECTED
    )


def test_kernel_consumer_schema_rejects_missing_required_row_field(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"]["row_fields"] = [
        field
        for field in payload["native_consumer_abi"]["row_fields"]
        if field["name"] != "descriptor_ptr"
    ]
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert "row_field_missing:descriptor_ptr" in result["failures"]


def test_kernel_consumer_schema_rejects_extra_row_field(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"]["row_fields"].append(
        {
            "name": "unexpected_field",
            "source_column": "unexpected_field",
            "abi_dtype": "uint64",
            "shape": ["row_count"],
            "required": False,
            "payload_deref_allowed": False,
            "device_ownership": "model_weight_device",
            "lifetime": "model_load_epoch",
        }
    )
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert any(
        failure.startswith("row_field_order_or_count_mismatch")
        for failure in result["failures"]
    )


def test_kernel_consumer_schema_rejects_metadata_dtype_mismatch(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"]["row_metadata"][0]["abi_dtype"] = "uint64"
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert "row_metadata_abi_dtype_mismatch:layer_id" in result["failures"]


def test_kernel_consumer_schema_rejects_abi_header_mismatch(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"]["cpp_header"] = "wrong/header.h"
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert (
        "native_consumer_abi.cpp_header_mismatch:"
        "'wrong/header.h'!='microbench/premap_kernel_consumer/"
        "premap_typed_consumer_abi_v1.h'"
    ) in result["failures"]


def test_kernel_consumer_schema_rejects_adapter_header_mismatch(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"]["adapter_header"] = "wrong/adapter.h"
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert (
        "native_consumer_abi.adapter_header_mismatch:"
        "'wrong/adapter.h'!='microbench/premap_kernel_consumer/"
        "premap_typed_consumer_adapter_v1.h'"
    ) in result["failures"]


def test_kernel_consumer_schema_rejects_enabled_launch_envelope_default(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"]["launch_envelope_default_enabled"] = True
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert (
        "native_consumer_abi.launch_envelope_default_enabled_mismatch:"
        "True!=False"
    ) in result["failures"]


def test_kernel_consumer_schema_rejects_missing_native_layout_contract(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"].pop(
        "future_kernel_native_consumer_abi_layout_reported"
    )
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert (
        "native_consumer_abi."
        "future_kernel_native_consumer_abi_layout_reported_not_true"
    ) in result["failures"]


def test_kernel_consumer_schema_rejects_dispatch_layout_field_drift(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"][
        "future_kernel_native_consumer_dispatch_abi_layout_fields"
    ] = ["future_kernel_native_dispatch_consumer_dispatch_struct_size"]
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert any(
        failure.startswith(
            "native_consumer_abi."
            "future_kernel_native_consumer_dispatch_abi_layout_fields_mismatch"
        )
        for failure in result["failures"]
    )


def test_kernel_consumer_schema_rejects_native_layout_value_drift(
    tmp_path: Path,
) -> None:
    payload = _valid_schema_payload()
    payload["native_consumer_abi"][
        "future_kernel_native_consumer_abi_layout_expected"
    ]["future_kernel_native_consumer_params_struct_size"] = 120
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert any(
        failure.startswith(
            "native_consumer_abi."
            "future_kernel_native_consumer_abi_layout_expected_mismatch"
        )
        for failure in result["failures"]
    )


def test_kernel_consumer_schema_rejects_enabled_forbidden_macro(
    tmp_path: Path,
) -> None:
    payload = copy.deepcopy(_valid_schema_payload())
    for flag in payload["debug_macro_ladder"]["flags"]:
        if flag["name"] == "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS":
            flag["default"] = "enabled"
            break
    schema_path = tmp_path / "schema.yaml"
    _write_schema(schema_path, payload)

    result = check_kernel_consumer_schema_artifact(schema_path)

    assert result["passed"] is False
    assert (
        "forbidden_macro_default_not_disabled:"
        "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS"
    ) in result["failures"]


def test_kernel_consumer_schema_cli_writes_json(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.yaml"
    output_path = tmp_path / "check.json"
    _write_schema(schema_path, _valid_schema_payload())

    exit_code = main([str(schema_path), "--output-json", str(output_path)])

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
