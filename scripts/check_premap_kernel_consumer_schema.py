#!/usr/bin/env python3
"""Validate the readonly premap kernel-side typed consumer schema artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
)


REQUIRED_ROW_FIELDS = {
    "descriptor_ptr": {"required": True, "null_allowed": False},
    "packed_weight_descriptor": {"required": True, "null_allowed": False},
    "scale_metadata_handle": {"required": True, "null_allowed": False},
    "aux_metadata_handle": {"required": False, "null_allowed": True},
}
REQUIRED_ROW_METADATA = {
    "layer_id": {
        "abi_dtype": "int32",
        "shape": "scalar",
        "source": "prelaunch_layer_context",
        "required": True,
    },
    "expert_id": {
        "abi_dtype": "int32",
        "shape": ["row_count"],
        "source": "address_key.layer_expert",
        "required": True,
    },
    "address_key_hash": {
        "abi_dtype": "uint64",
        "shape": ["row_count"],
        "source": "address_key",
        "required": True,
    },
    "row_order_hash": {
        "abi_dtype": "uint64",
        "shape": "scalar",
        "source": "prepared_handle_table",
        "required": True,
    },
    "ordered_row_hash": {
        "abi_dtype": "uint64",
        "shape": "scalar",
        "source": "prepared_handle_table",
        "required": True,
    },
}
FORBIDDEN_LAB_DEFAULT_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
    "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
}
REQUIRED_STEPWISE_DEBUG_MACROS = {
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
}


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_kernel_consumer_schema_artifact(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        payload = _load_yaml(path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return {
            "path": str(path),
            "passed": False,
            "failures": [f"load_failed:{type(exc).__name__}:{exc}"],
            "rows": rows,
        }
    if not isinstance(payload, dict):
        return {
            "path": str(path),
            "passed": False,
            "failures": ["schema_not_mapping"],
            "rows": rows,
        }

    schema = payload.get("schema") or {}
    source_contract = payload.get("source_contract") or {}
    native_abi = payload.get("native_consumer_abi") or {}
    safety = payload.get("safety_contract") or {}
    macro_ladder = payload.get("debug_macro_ladder") or {}

    expected_scalars = {
        "schema_version": 1,
        "artifact_id": "premap_kernel_side_typed_consumer_schema_v1",
        "artifact_kind": "premap_kernel_consumer_schema",
        "status": "readonly_shadow_only",
    }
    for key, expected in expected_scalars.items():
        observed = payload.get(key)
        if observed != expected:
            failures.append(f"{key}_mismatch:{observed!r}!={expected!r}")

    expected_schema = {
        "name": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
        "hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
        "target_runtime": "vllm_awq_wna16_fused_moe",
        "native_consumer_mode": "typed_shadow_object",
    }
    for key, expected in expected_schema.items():
        observed = schema.get(key)
        if observed != expected:
            failures.append(f"schema.{key}_mismatch:{observed!r}!={expected!r}")

    expected_source = {
        "handle_table_columns": list(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
        "handle_table_schema_hash": PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        "semantic_schema_name": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
        "semantic_schema_hash": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
        "kernel_side_adapter_schema_name": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
        "kernel_side_adapter_schema_hash": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    }
    for key, expected in expected_source.items():
        observed = source_contract.get(key)
        if observed != expected:
            failures.append(f"source_contract.{key}_mismatch")

    if native_abi.get("layout") != "struct_of_arrays":
        failures.append("native_consumer_abi.layout_mismatch")
    if native_abi.get("row_order") != "vllm_prelaunch_sorted_token_ids_order":
        failures.append("native_consumer_abi.row_order_mismatch")
    if native_abi.get("row_count_source") != "consumer_row_count":
        failures.append("native_consumer_abi.row_count_source_mismatch")

    row_fields = native_abi.get("row_fields")
    row_fields = row_fields if isinstance(row_fields, list) else []
    row_field_names = [
        item.get("name") if isinstance(item, dict) else None for item in row_fields
    ]
    expected_row_field_names = list(REQUIRED_ROW_FIELDS)
    if row_field_names != expected_row_field_names:
        failures.append(
            "row_field_order_or_count_mismatch:"
            f"{row_field_names!r}!={expected_row_field_names!r}"
        )
    duplicate_row_fields = sorted(
        {name for name in row_field_names if name is not None and row_field_names.count(name) > 1}
    )
    failures.extend(f"row_field_duplicate:{name}" for name in duplicate_row_fields)
    fields_by_name = {
        item.get("name"): item for item in row_fields if isinstance(item, dict)
    }
    for name, expected_field in REQUIRED_ROW_FIELDS.items():
        field = fields_by_name.get(name)
        row: dict[str, Any] = {
            "field": name,
            "present": field is not None,
            "required": expected_field["required"],
        }
        if field is None:
            failures.append(f"row_field_missing:{name}")
            rows.append(row)
            continue
        row.update(
            {
                "abi_dtype": field.get("abi_dtype"),
                "shape": field.get("shape"),
                "payload_deref_allowed": field.get("payload_deref_allowed"),
                "device_ownership": field.get("device_ownership"),
                "lifetime": field.get("lifetime"),
            }
        )
        if field.get("source_column") != name:
            failures.append(f"row_field_source_column_mismatch:{name}")
        if field.get("abi_dtype") != "uint64":
            failures.append(f"row_field_dtype_mismatch:{name}")
        if field.get("shape") != ["row_count"]:
            failures.append(f"row_field_shape_mismatch:{name}")
        if field.get("required") is not expected_field["required"]:
            failures.append(f"row_field_required_mismatch:{name}")
        if field.get("null_allowed", False) is not expected_field["null_allowed"]:
            failures.append(f"row_field_null_allowed_mismatch:{name}")
        if field.get("payload_deref_allowed") is not False:
            failures.append(f"row_field_payload_deref_allowed:{name}")
        if field.get("device_ownership") != "model_weight_device":
            failures.append(f"row_field_device_ownership_mismatch:{name}")
        if field.get("lifetime") != "model_load_epoch":
            failures.append(f"row_field_lifetime_mismatch:{name}")
        rows.append(row)

    metadata = native_abi.get("row_metadata")
    metadata = metadata if isinstance(metadata, list) else []
    metadata_names = [
        item.get("name") if isinstance(item, dict) else None for item in metadata
    ]
    expected_metadata_names = list(REQUIRED_ROW_METADATA)
    if metadata_names != expected_metadata_names:
        failures.append(
            "row_metadata_order_or_count_mismatch:"
            f"{metadata_names!r}!={expected_metadata_names!r}"
        )
    duplicate_metadata = sorted(
        {name for name in metadata_names if name is not None and metadata_names.count(name) > 1}
    )
    failures.extend(f"row_metadata_duplicate:{name}" for name in duplicate_metadata)
    metadata_by_name = {
        item.get("name"): item for item in metadata if isinstance(item, dict)
    }
    for name, expected in REQUIRED_ROW_METADATA.items():
        item = metadata_by_name.get(name)
        if item is None:
            failures.append(f"row_metadata_missing:{name}")
            continue
        for key, expected_value in expected.items():
            if item.get(key) != expected_value:
                failures.append(f"row_metadata_{key}_mismatch:{name}")

    expected_safety = {
        "payload_bytes_required": 0,
        "ready_credit_required": False,
        "changes_router_required": False,
        "changes_descriptor_order_required": False,
        "changes_kernel_launch_args_required": False,
        "passed_to_kernel_required": False,
        "live_compatible_with_current_wna16_args_required": False,
        "current_status": "native_stub_pending",
    }
    for key, expected in expected_safety.items():
        observed = safety.get(key)
        if observed != expected:
            failures.append(f"safety_contract.{key}_mismatch:{observed!r}")

    flags = macro_ladder.get("flags")
    flags = flags if isinstance(flags, list) else []
    if macro_ladder.get("compile_guard_macro") != "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1":
        failures.append("debug_macro_compile_guard_mismatch")
    flags_by_name = {
        item.get("name"): item for item in flags if isinstance(item, dict)
    }
    for name in sorted(REQUIRED_STEPWISE_DEBUG_MACROS):
        flag = flags_by_name.get(name)
        if flag is None:
            failures.append(f"debug_macro_missing:{name}")
            continue
        if flag.get("default") != "disabled":
            failures.append(f"debug_macro_default_not_disabled:{name}")
        if flag.get("individually_enableable") is not True:
            failures.append(f"debug_macro_not_individual:{name}")
    for name in sorted(FORBIDDEN_LAB_DEFAULT_MACROS):
        flag = flags_by_name.get(name)
        if flag is None:
            failures.append(f"debug_macro_missing:{name}")
            continue
        if flag.get("default") != "disabled":
            failures.append(f"forbidden_macro_default_not_disabled:{name}")
        if flag.get("individually_enableable") is not False:
            failures.append(f"forbidden_macro_individually_enableable:{name}")
        if flag.get("forbidden_in_lab_default") is not True:
            failures.append(f"forbidden_macro_not_marked:{name}")

    return {
        "path": str(path),
        "passed": not failures,
        "failures": failures,
        "schema_name": schema.get("name"),
        "schema_hash": schema.get("hash"),
        "row_field_count": len(row_fields),
        "row_metadata_count": len(metadata),
        "macro_count": len(flags),
        "rows": rows,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema_path", type=Path)
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_kernel_consumer_schema_artifact(args.schema_path)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
