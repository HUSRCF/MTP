from __future__ import annotations

import json
from pathlib import Path

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
from scripts.run_premap_lab_preflight import main, run_premap_lab_preflight


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _valid_schema_payload() -> dict:
    row_fields = []
    required_by_name = {
        "descriptor_ptr": True,
        "packed_weight_descriptor": True,
        "scale_metadata_handle": True,
        "aux_metadata_handle": False,
    }
    for name in PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS:
        row = {
            "name": name,
            "source_column": name,
            "abi_dtype": "uint64",
            "semantic": f"{name}_semantic",
            "shape": ["row_count"],
            "required": required_by_name[name],
            "payload_deref_allowed": False,
            "device_ownership": "model_weight_device",
            "lifetime": "model_load_epoch",
        }
        if name == "aux_metadata_handle":
            row["null_allowed"] = True
        row_fields.append(row)
    return {
        "schema_version": 1,
        "artifact_id": "premap_kernel_side_typed_consumer_schema_v1",
        "artifact_kind": "premap_kernel_consumer_schema",
        "status": "readonly_shadow_only",
        "schema": {
            "name": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
            "hash": PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
            "target_runtime": "vllm_awq_wna16_fused_moe",
            "native_consumer_mode": "typed_shadow_object",
        },
        "source_contract": {
            "handle_table_columns": list(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
            "handle_table_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "semantic_schema_name": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
            "semantic_schema_hash": PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
            "kernel_side_adapter_schema_name": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
            "kernel_side_adapter_schema_hash": PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
        },
        "native_consumer_abi": {
            "layout": "struct_of_arrays",
            "row_order": "vllm_prelaunch_sorted_token_ids_order",
            "row_count_source": "consumer_row_count",
            "row_fields": row_fields,
            "row_metadata": [
                {
                    "name": "layer_id",
                    "abi_dtype": "int32",
                    "shape": "scalar",
                    "source": "prelaunch_layer_context",
                    "required": True,
                },
                {
                    "name": "expert_id",
                    "abi_dtype": "int32",
                    "shape": ["row_count"],
                    "source": "address_key.layer_expert",
                    "required": True,
                },
                {
                    "name": "address_key_hash",
                    "abi_dtype": "uint64",
                    "shape": ["row_count"],
                    "source": "address_key",
                    "required": True,
                },
                {
                    "name": "row_order_hash",
                    "abi_dtype": "uint64",
                    "shape": "scalar",
                    "source": "prepared_handle_table",
                    "required": True,
                },
                {
                    "name": "ordered_row_hash",
                    "abi_dtype": "uint64",
                    "shape": "scalar",
                    "source": "prepared_handle_table",
                    "required": True,
                },
            ],
        },
        "safety_contract": {
            "payload_bytes_required": 0,
            "ready_credit_required": False,
            "changes_router_required": False,
            "changes_descriptor_order_required": False,
            "changes_kernel_launch_args_required": False,
            "passed_to_kernel_required": False,
            "live_compatible_with_current_wna16_args_required": False,
            "current_status": "native_stub_pending",
        },
        "debug_macro_ladder": {
            "compile_guard_macro": "MTP_PREMAP_TYPED_CONSUMER_SCHEMA_V1",
            "flags": [
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
                    "default": "disabled",
                    "individually_enableable": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_ENABLE_PAYLOAD_DEREF",
                    "default": "disabled",
                    "individually_enableable": False,
                    "forbidden_in_lab_default": True,
                },
                {
                    "name": "MTP_PREMAP_TYPED_CONSUMER_ENABLE_KERNEL_ARG_PASS",
                    "default": "disabled",
                    "individually_enableable": False,
                    "forbidden_in_lab_default": True,
                },
            ],
        },
    }


def _write_valid_schema(root: Path) -> str:
    schema_path = "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    _write(root / schema_path, json.dumps(_valid_schema_payload()) + "\n")
    return schema_path


def _write_gate(
    root: Path,
    name: str,
    evidence_json: str,
    *,
    typed_consumer_required: bool = True,
    canary: bool | None = None,
    lab_default: bool | None = None,
    include_lab_evidence: bool = True,
    lab_evidence_passed: bool = True,
    lab_evidence_failures: list[str] | None = None,
    include_schema_artifact: bool = True,
) -> str:
    schema_path = _write_valid_schema(root)
    evidence_path = f"reports/{evidence_json}"
    _write(root / evidence_path, '{"passed": true}\n')
    lab_gate_path = f"reports/{name}_typed_consumer_gate.json"
    lab_selfcheck_path = f"reports/{name}_typed_consumer_selfcheck.json"
    lab_payload = {
        "passed": lab_evidence_passed,
        "failures": [] if lab_evidence_failures is None else lab_evidence_failures,
    }
    if include_lab_evidence:
        _write(root / lab_gate_path, json.dumps(lab_payload) + "\n")
        _write(root / lab_selfcheck_path, json.dumps(lab_payload) + "\n")
    gate_path = f"configs/runtime/{name}.yaml"
    metadata_lines = ""
    if canary is not None:
        metadata_lines += f"canary: {str(canary).lower()}\n"
    if lab_default is not None:
        metadata_lines += f"lab_default: {str(lab_default).lower()}\n"
    _write(
        root / gate_path,
        "schema_version: 1\n"
        f"{metadata_lines}"
        + (
            "schema_artifacts:\n"
            f"  kernel_side_typed_consumer_schema_yaml: {schema_path}\n"
            if include_schema_artifact
            else ""
        )
        +
        "contract:\n"
        f"  kernel_side_typed_consumer_object_required: {str(typed_consumer_required).lower()}\n"
        "  kernel_side_typed_consumer_object_payload_bytes_required: 0\n"
        "  kernel_side_typed_consumer_object_passed_to_kernel_required: false\n"
        "  kernel_side_typed_consumer_object_changes_kernel_launch_args_required: false\n"
        "  kernel_side_typed_consumer_object_consumer_connected_required: false\n"
        "  kernel_side_typed_consumer_object_live_enabled_required: false\n"
        "  kernel_side_typed_consumer_object_live_eligible_required: false\n"
        "  kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args_required: false\n"
        "evidence_paths:\n"
        f"  gate_json: {evidence_path}\n"
        + (
            "  strict_kernel_side_typed_consumer_object_128_gate_json: "
            f"{lab_gate_path}\n"
            "  strict_kernel_side_typed_consumer_object_128_selfcheck_json: "
            f"{lab_selfcheck_path}\n"
            if include_lab_evidence
            else ""
        ),
    )
    return gate_path


def _write_trace_config(
    root: Path,
    name: str,
    *,
    readonly_gate_path: str,
    live_enabled: bool = False,
    kernel_arg_pass_enabled: bool = False,
    real_kernel_arg_mutation_enabled: bool = False,
    single_field_dry_run_enabled: bool = False,
    single_field_live_enabled: bool = False,
    risky_trace_canary: bool = False,
    risky_trace_canary_scope: str | None = None,
) -> str:
    config_path = f"configs/trace/{name}.yaml"
    canary_lines = ""
    if risky_trace_canary:
        canary_lines += "    premap_risky_trace_canary: true\n"
    if risky_trace_canary_scope is not None:
        canary_lines += (
            f"    premap_risky_trace_canary_scope: {risky_trace_canary_scope}\n"
        )
    _write(
        root / config_path,
        "trace:\n"
        "  runtime_shadow:\n"
        "    premap_consumer_require_readonly_gate: true\n"
        f"    premap_consumer_readonly_gate_path: {readonly_gate_path}\n"
        f"    premap_kernel_arg_handoff_live_enabled: {str(live_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_kernel_arg_pass_enabled: {str(kernel_arg_pass_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled: {str(real_kernel_arg_mutation_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled: {str(single_field_dry_run_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_single_field_replacement_live_enabled: {str(single_field_live_enabled).lower()}\n"
        f"{canary_lines}",
    )
    return config_path


def test_premap_lab_preflight_accepts_default_readonly_wiring(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["runtime_gate_evidence_scan"]["gate_count"] == 3
    assert result["runtime_gate_evidence_scan"]["evidence_path_count"] == 6
    assert result["default_readonly_gate_required_evidence_check"]["passed"] is True
    assert result["trace_config_checks"][0]["passed"] is True
    assert result["trace_config_checks"][0]["readonly_gate_path_label"] == default_gate


def test_premap_lab_preflight_rejects_default_gate_without_typed_consumer_contract(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        typed_consumer_required=False,
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_contract_check_failed" in result["failures"]
    assert result["default_readonly_gate_contract_check"]["failures"] == [
        "kernel_side_typed_consumer_object_required_mismatch"
    ]


def test_premap_lab_preflight_rejects_default_gate_with_bad_schema_artifact(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    schema_path = tmp_path / "configs/runtime/premap_kernel_side_typed_consumer_schema_v1.yaml"
    payload = _valid_schema_payload()
    payload["debug_macro_ladder"]["flags"][0]["default"] = "enabled"
    _write(schema_path, json.dumps(payload) + "\n")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    assert (
        "schema_check:debug_macro_default_not_disabled:"
        "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA"
    ) in result["default_kernel_consumer_schema_check"]["failures"]


def test_premap_lab_preflight_rejects_default_gate_without_schema_artifact(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        include_schema_artifact=False,
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_kernel_consumer_schema_check_failed" in result["failures"]
    assert result["default_kernel_consumer_schema_check"]["failures"] == [
        "schema_artifacts_missing_or_not_mapping"
    ]


def test_premap_lab_preflight_rejects_default_gate_without_typed_evidence(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        include_lab_evidence=False,
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:missing_evidence_path",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:missing_evidence_path",
    ]


def test_premap_lab_preflight_rejects_failed_typed_evidence(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        lab_evidence_passed=False,
        lab_evidence_failures=["typed_gate_failed"],
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert "default_readonly_gate_required_evidence_check_failed" in result["failures"]
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:not_passed",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:not_passed",
    ]


def test_premap_lab_preflight_rejects_typed_evidence_with_failures(
    tmp_path: Path,
):
    default_gate = _write_gate(
        tmp_path,
        "default_gate",
        "default_gate.json",
        lab_evidence_passed=True,
        lab_evidence_failures=["unexpected_failure"],
    )
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:failures_not_empty",
        "strict_kernel_side_typed_consumer_object_128_selfcheck_json:failures_not_empty",
    ]


def test_premap_lab_preflight_rejects_missing_typed_evidence_file(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    (tmp_path / "reports/default_gate_typed_consumer_gate.json").unlink()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:missing_file"
    ]


def test_premap_lab_preflight_allows_missing_typed_evidence_file_when_requested(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    (tmp_path / "reports/default_gate_typed_consumer_gate.json").unlink()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        allow_missing_evidence=True,
    )

    assert result["passed"] is True
    row = result["default_readonly_gate_required_evidence_check"]["rows"][0]
    assert row["failure"] == "missing_file"
    assert row["allowed_missing"] is True


def test_premap_lab_preflight_rejects_directory_typed_evidence_path(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    gate_path = tmp_path / "reports/default_gate_typed_consumer_gate.json"
    gate_path.unlink()
    gate_path.mkdir()
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["default_readonly_gate_required_evidence_check"]["failures"] == [
        "strict_kernel_side_typed_consumer_object_128_gate_json:not_file"
    ]


def test_premap_lab_preflight_accepts_absolute_readonly_gate_path(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    absolute_default_gate = str((tmp_path / default_gate).resolve())
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=absolute_default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["trace_config_checks"][0]["readonly_gate_path"] == absolute_default_gate
    assert result["trace_config_checks"][0]["readonly_gate_path_label"] == default_gate


def test_premap_lab_preflight_rejects_kernel_arg_pass_in_default_config(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
        kernel_arg_pass_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["trace_config_checks"][0]["failures"] == ["kernel_arg_pass_enabled"]


def test_premap_lab_preflight_rejects_canary_gate_equal_to_default_gate(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=default_gate,
    )

    assert result["passed"] is False
    assert result["gate_pair_failures"] == [
        "default_readonly_gate_equals_canary_gate"
    ]
    assert "default_readonly_gate_equals_canary_gate" in result["failures"]


def test_premap_lab_preflight_accepts_risky_canary_metadata(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is True
    assert result["risky_canary_metadata_checks"][risky_gate]["passed"] is True


def test_premap_lab_preflight_rejects_risky_canary_without_metadata(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(tmp_path, "risky_gate", "risky_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_canary_metadata_checks"][risky_gate]["failures"] == [
        "canary_mismatch",
        "lab_default_mismatch",
    ]
    assert f"{risky_gate}:risky_canary_metadata_check_failed" in result["failures"]


def test_premap_lab_preflight_accepts_risky_trace_with_canary_gate_and_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    trace_config = _write_trace_config(
        tmp_path,
        "strict_name_without_canary",
        readonly_gate_path=risky_gate,
        live_enabled=True,
        kernel_arg_pass_enabled=True,
        risky_trace_canary=True,
        risky_trace_canary_scope="explicit_test_canary",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["passed"] is True
    assert result["trace_config_checks"][0]["failures"] == [
        "readonly_gate_path_mismatch",
        "kernel_arg_pass_enabled",
        "live_enabled_in_default_lab_config",
    ]


def test_premap_lab_preflight_rejects_risky_trace_without_canary_gate_metadata(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(tmp_path, "risky_gate", "risky_gate.json")
    _write_trace_config(
        tmp_path,
        "danger_canary",
        readonly_gate_path=risky_gate,
        live_enabled=True,
        risky_trace_canary=True,
        risky_trace_canary_scope="explicit_test_canary",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_gate_canary_mismatch",
        "risky_gate_lab_default_mismatch",
    ]
    assert (
        "configs/trace/danger_canary.yaml:risky_trace_config_check_failed"
        in result["failures"]
    )


def test_premap_lab_preflight_rejects_risky_trace_without_canary_label_or_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    _write_trace_config(
        tmp_path,
        "strict_name_without_marker",
        readonly_gate_path=risky_gate,
        live_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_trace_canary_marker_missing"
    ]


def test_premap_lab_preflight_rejects_named_canary_trace_without_explicit_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    _write_trace_config(
        tmp_path,
        "danger_canary",
        readonly_gate_path=risky_gate,
        live_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_trace_canary_marker_missing"
    ]


def test_premap_lab_preflight_all_risky_flags_require_explicit_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    flag_kwargs = [
        {"live_enabled": True},
        {"kernel_arg_pass_enabled": True},
        {"real_kernel_arg_mutation_enabled": True},
        {"single_field_dry_run_enabled": True},
        {"single_field_live_enabled": True},
    ]
    for index, kwargs in enumerate(flag_kwargs):
        _write_trace_config(
            tmp_path,
            f"risky_{index}",
            readonly_gate_path=risky_gate,
            **kwargs,
        )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    failures = {
        item["config_path"]: item["failures"]
        for item in result["risky_trace_config_checks"]
        if item["enabled_risky_flags"]
    }
    assert failures == {
        f"configs/trace/risky_{index}.yaml": ["risky_trace_canary_marker_missing"]
        for index in range(5)
    }


def test_premap_lab_preflight_rejects_truthy_string_canary_marker(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    risky_gate = _write_gate(
        tmp_path,
        "risky_gate",
        "risky_gate.json",
        canary=True,
        lab_default=False,
    )
    config_path = "configs/trace/risky_truthy_marker.yaml"
    _write(
        tmp_path / config_path,
        "trace:\n"
        "  runtime_shadow:\n"
        "    premap_consumer_require_readonly_gate: true\n"
        f"    premap_consumer_readonly_gate_path: {risky_gate}\n"
        "    premap_kernel_arg_handoff_live_enabled: true\n"
        "    premap_risky_trace_canary: 'true'\n"
        "    premap_risky_trace_canary_scope: malformed_truthy_string\n",
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
        risky_canary_gates=[risky_gate],
    )

    assert result["passed"] is False
    assert result["risky_trace_config_checks"][0]["failures"] == [
        "risky_trace_canary_marker_missing"
    ]


def test_premap_lab_preflight_reports_missing_trace_config(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=["configs/trace/missing.yaml"],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["trace_config_checks"][0]["config_path"] == "configs/trace/missing.yaml"
    assert result["trace_config_checks"][0]["failures"][0].startswith(
        "FileNotFoundError:"
    )


def test_premap_lab_preflight_cli_writes_summary(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    output = tmp_path / "preflight.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runtime-pattern",
            "configs/runtime/*.yaml",
            "--trace-config",
            trace_config,
            "--default-readonly-gate",
            default_gate,
            "--canary-gate",
            canary_gate,
            "--output-json",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["runtime_gate_evidence_scan"]["passed"] is True
