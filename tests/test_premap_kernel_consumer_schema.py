from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.check_premap_kernel_consumer_schema import (
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
