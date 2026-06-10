from pathlib import Path

import pytest
import yaml

from mtp_expert_prefetch.runtime.cache_manager import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
)
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    _apply_premap_address_capacity_gate,
    _apply_premap_consumer_readonly_gate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_gate(path, *, capacity=12288):
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: test_premap_capacity_gate",
                "capacity_gate:",
                f"  recommended_capacity_entries: {capacity}",
                "evidence_paths:",
                "  capacity_sensitivity_json: outputs/test.json",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_readonly_gate(
    path,
    *,
    passed=True,
    payload_bytes=0,
    lab_precondition: bool | None = None,
    descriptor_prep_execution_mode: str | None = None,
    descriptor_prep_payload_bytes: int | None = None,
    descriptor_prep_kernel_arg_mutation: bool | None = None,
    real_descriptor_prep_required: bool | None = None,
    require_real_descriptor_prep: bool | None = None,
    kernel_arg_shadow_table_required: bool | None = None,
    require_kernel_arg_shadow_table: bool | None = None,
    consumer_shim_table_read_required: bool | None = None,
    require_consumer_shim_table_read: bool | None = None,
    consumer_shim_table_consume_required: bool | None = None,
    require_consumer_shim_table_consume: bool | None = None,
    consumer_shim_table_consume_handle_field_reads_required: bool | None = None,
    consumer_shim_table_object_required: bool | None = None,
    require_consumer_shim_table_object: bool | None = None,
    consumer_shim_prep_execution_required: bool | None = None,
    require_consumer_shim_prep_execution: bool | None = None,
    consumer_shim_prep_execution_handle_field_reads_required: bool | None = None,
    kernel_arg_handoff_live_toggle_required: bool | None = None,
    kernel_arg_handoff_live_toggle_enabled_required: bool | None = None,
    kernel_arg_handoff_live_toggle_block_reason: str = "kernel_arg_handoff_live_disabled",
    kernel_arg_handoff_live_toggle_lab_gate_passed_required: bool | None = True,
    kernel_arg_handoff_live_toggle_attempt_record_ready_required: bool | None = True,
    kernel_arg_handoff_live_toggle_live_eligible_required: bool | None = False,
    kernel_arg_handoff_live_toggle_blocked_required: bool | None = True,
    require_kernel_arg_handoff_live_toggle: bool | None = None,
    extra_contract_lines: list[str] | None = None,
    extra_check_lines: list[str] | None = None,
):
    if descriptor_prep_execution_mode is not None:
        if real_descriptor_prep_required is None:
            real_descriptor_prep_required = True
        if require_real_descriptor_prep is None:
            require_real_descriptor_prep = True
        if kernel_arg_shadow_table_required is None:
            kernel_arg_shadow_table_required = True
        if require_kernel_arg_shadow_table is None:
            require_kernel_arg_shadow_table = True
        if consumer_shim_table_read_required is None:
            consumer_shim_table_read_required = True
        if require_consumer_shim_table_read is None:
            require_consumer_shim_table_read = True
        if consumer_shim_table_consume_required is None:
            consumer_shim_table_consume_required = True
        if require_consumer_shim_table_consume is None:
            require_consumer_shim_table_consume = True
        if consumer_shim_table_consume_handle_field_reads_required is None:
            consumer_shim_table_consume_handle_field_reads_required = True
        if consumer_shim_table_object_required is None:
            consumer_shim_table_object_required = True
        if require_consumer_shim_table_object is None:
            require_consumer_shim_table_object = True
        if consumer_shim_prep_execution_required is None:
            consumer_shim_prep_execution_required = True
        if require_consumer_shim_prep_execution is None:
            require_consumer_shim_prep_execution = True
        if consumer_shim_prep_execution_handle_field_reads_required is None:
            consumer_shim_prep_execution_handle_field_reads_required = True
    status = "passed" if passed else "failed"
    gate_passed = "true" if passed else "false"
    lines = [
        "schema_version: 1",
        "artifact_id: test_premap_consumer_readonly_gate",
        f"status: {status}",
    ]
    if lab_precondition is not None:
        lines.append(f"lab_precondition: {str(lab_precondition).lower()}")
    lines.extend(
        [
            "contract:",
            f"  payload_bytes_required: {payload_bytes}",
            "  ready_credit_required: false",
            "  changes_router_required: false",
            "  changes_descriptor_order_required: false",
            "  address_key_scope: layer_expert",
            "  descriptor_bytes: 4096",
            "  handle_resolution: read_only",
        ]
    )
    if descriptor_prep_execution_mode is not None:
        lines.append(
            "  real_descriptor_prep_required: "
            f"{str(bool(real_descriptor_prep_required)).lower()}"
        )
        lines.append(
            f"  descriptor_prep_execution_mode: {descriptor_prep_execution_mode}"
        )
    if descriptor_prep_payload_bytes is not None:
        lines.append(
            f"  descriptor_prep_payload_bytes_required: {descriptor_prep_payload_bytes}"
        )
    if descriptor_prep_kernel_arg_mutation is not None:
        lines.append(
            "  descriptor_prep_kernel_arg_mutation_required: "
            f"{str(descriptor_prep_kernel_arg_mutation).lower()}"
        )
    if kernel_arg_shadow_table_required is not None:
        lines.append(
            "  kernel_arg_shadow_table_required: "
            f"{str(bool(kernel_arg_shadow_table_required)).lower()}"
        )
    if consumer_shim_table_read_required is not None:
        lines.append(
            "  consumer_shim_table_read_required: "
            f"{str(bool(consumer_shim_table_read_required)).lower()}"
        )
    if consumer_shim_table_consume_required is not None:
        lines.append(
            "  consumer_shim_table_consume_required: "
            f"{str(bool(consumer_shim_table_consume_required)).lower()}"
        )
    if consumer_shim_table_consume_handle_field_reads_required is not None:
        lines.append(
            "  consumer_shim_table_consume_handle_field_reads_required: "
            f"{str(bool(consumer_shim_table_consume_handle_field_reads_required)).lower()}"
        )
    if consumer_shim_table_object_required is not None:
        lines.append(
            "  consumer_shim_table_object_required: "
            f"{str(bool(consumer_shim_table_object_required)).lower()}"
        )
    if consumer_shim_prep_execution_required is not None:
        lines.append(
            "  consumer_shim_prep_execution_required: "
            f"{str(bool(consumer_shim_prep_execution_required)).lower()}"
        )
    if consumer_shim_prep_execution_handle_field_reads_required is not None:
        lines.append(
            "  consumer_shim_prep_execution_handle_field_reads_required: "
            f"{str(bool(consumer_shim_prep_execution_handle_field_reads_required)).lower()}"
        )
    if kernel_arg_handoff_live_toggle_required is not None:
        lines.extend(
            [
                "  kernel_arg_handoff_live_toggle_required: "
                f"{str(bool(kernel_arg_handoff_live_toggle_required)).lower()}",
                "  kernel_arg_handoff_live_toggle_mode: "
                "readonly_kernel_arg_handoff_live_toggle",
                "  kernel_arg_handoff_live_toggle_block_reason: "
                f"{kernel_arg_handoff_live_toggle_block_reason}",
                "  kernel_arg_handoff_live_toggle_lab_gate_passed_required: "
                f"{str(bool(kernel_arg_handoff_live_toggle_lab_gate_passed_required)).lower()}",
                "  kernel_arg_handoff_live_toggle_attempt_record_ready_required: "
                f"{str(bool(kernel_arg_handoff_live_toggle_attempt_record_ready_required)).lower()}",
                "  kernel_arg_handoff_live_toggle_live_eligible_required: "
                f"{str(bool(kernel_arg_handoff_live_toggle_live_eligible_required)).lower()}",
                "  kernel_arg_handoff_live_toggle_blocked_required: "
                f"{str(bool(kernel_arg_handoff_live_toggle_blocked_required)).lower()}",
                "  kernel_arg_handoff_live_toggle_payload_bytes_required: 0",
                "  kernel_arg_handoff_live_toggle_passed_to_kernel_required: false",
                "  kernel_arg_handoff_live_toggle_changes_kernel_launch_args_required: false",
            ]
        )
    if kernel_arg_handoff_live_toggle_enabled_required is not None:
        lines.append(
            "  kernel_arg_handoff_live_toggle_enabled_required: "
            f"{str(bool(kernel_arg_handoff_live_toggle_enabled_required)).lower()}"
        )
    if extra_contract_lines:
        lines.extend(extra_contract_lines)
    lines.extend(
        [
            "gate:",
            f"  passed: {gate_passed}",
            "  failures: []",
        ]
    )
    check_lines = []
    if require_real_descriptor_prep is not None:
        check_lines.append(
            "    require_real_descriptor_prep: "
            f"{str(bool(require_real_descriptor_prep)).lower()}"
        )
    if require_kernel_arg_shadow_table is not None:
        check_lines.append(
            "    require_kernel_arg_shadow_table: "
            f"{str(bool(require_kernel_arg_shadow_table)).lower()}"
        )
    if require_consumer_shim_table_read is not None:
        check_lines.append(
            "    require_consumer_shim_table_read: "
            f"{str(bool(require_consumer_shim_table_read)).lower()}"
        )
    if require_consumer_shim_table_consume is not None:
        check_lines.append(
            "    require_consumer_shim_table_consume: "
            f"{str(bool(require_consumer_shim_table_consume)).lower()}"
        )
    if require_consumer_shim_table_object is not None:
        check_lines.append(
            "    require_consumer_shim_table_object: "
            f"{str(bool(require_consumer_shim_table_object)).lower()}"
        )
    if require_consumer_shim_prep_execution is not None:
        check_lines.append(
            "    require_consumer_shim_prep_execution: "
            f"{str(bool(require_consumer_shim_prep_execution)).lower()}"
        )
    if require_kernel_arg_handoff_live_toggle is not None:
        check_lines.append(
            "    require_kernel_arg_handoff_live_toggle: "
            f"{str(bool(require_kernel_arg_handoff_live_toggle)).lower()}"
        )
    if extra_check_lines:
        check_lines.extend(extra_check_lines)
    if check_lines:
        lines.append("  check:")
        lines.extend(check_lines)
    lines.extend(
        [
            "  metrics:",
            "    premap_consumer_mapping_count: 2",
            "evidence_paths:",
            "  longrun_summary: outputs/longrun.json",
            "",
        ]
    )
    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _yaml_bool(value: bool) -> str:
    return str(bool(value)).lower()


def _kernel_arg_handoff_adapter_contract_lines(
    *,
    live_enabled: bool,
    consumer_connected_required: bool = False,
    kernel_arg_pass_required: bool = False,
    real_kernel_arg_mutation_required: bool = False,
) -> list[str]:
    integration_block_reason = (
        "kernel_arg_handoff_kernel_arg_pass_disabled"
        if live_enabled and consumer_connected_required
        else
        "kernel_arg_handoff_kernel_consumer_not_connected"
        if live_enabled
        else "kernel_arg_handoff_live_disabled"
    )
    adapter_block_reason = (
        (
            (
                "kernel_arg_handoff_real_kernel_arg_mutation_live"
                if real_kernel_arg_mutation_required
                else "kernel_arg_handoff_kernel_arg_pass_live"
            )
            if kernel_arg_pass_required
            else "kernel_arg_handoff_kernel_arg_pass_disabled"
        )
        if live_enabled and consumer_connected_required
        else
        "kernel_arg_handoff_kernel_consumer_not_connected"
        if live_enabled
        else "kernel_arg_handoff_live_disabled"
    )
    lines = [
        "  kernel_arg_handoff_launch_schema_mirror_required: true",
        "  kernel_arg_handoff_launch_schema_mirror_mode: "
        "readonly_kernel_arg_handoff_launch_schema_mirror",
        "  kernel_arg_handoff_launch_schema_mirror_payload_bytes_required: 0",
        "  kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_required: false",
        "  kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args_required: false",
        "  kernel_arg_handoff_live_noop_integration_required: true",
        "  kernel_arg_handoff_live_noop_integration_mode: "
        "readonly_kernel_arg_handoff_live_noop_integration",
        "  kernel_arg_handoff_live_noop_integration_block_reason: "
        f"{integration_block_reason}",
        "  kernel_arg_handoff_live_noop_integration_enabled_required: "
        f"{_yaml_bool(live_enabled)}",
        "  kernel_arg_handoff_live_noop_integration_lab_gate_passed_required: true",
        "  kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_required: true",
        "  kernel_arg_handoff_live_noop_integration_launch_schema_ready_required: true",
        "  kernel_arg_handoff_live_noop_integration_live_eligible_required: "
        f"{_yaml_bool(live_enabled)}",
        "  kernel_arg_handoff_live_noop_integration_consumer_connected_required: "
        f"{_yaml_bool(consumer_connected_required)}",
        "  kernel_arg_handoff_live_noop_integration_blocked_required: true",
        "  kernel_arg_handoff_live_noop_integration_payload_bytes_required: 0",
        "  kernel_arg_handoff_live_noop_integration_passed_to_kernel_required: false",
        "  kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_required: false",
        "  kernel_arg_handoff_live_consumer_adapter_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_mode: "
        "readonly_kernel_arg_handoff_live_consumer_adapter",
        "  kernel_arg_handoff_live_consumer_adapter_block_reason: "
        f"{adapter_block_reason}",
        "  kernel_arg_handoff_live_consumer_adapter_enabled_required: "
        f"{_yaml_bool(live_enabled)}",
        "  kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_record_ready_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason: "
        f"{integration_block_reason}",
        "  kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_consumer_connected_required: "
        f"{_yaml_bool(consumer_connected_required)}",
        "  kernel_arg_handoff_live_consumer_adapter_live_eligible_required: "
        f"{_yaml_bool(live_enabled)}",
        "  kernel_arg_handoff_live_consumer_adapter_blocked_required: true",
        "  kernel_arg_handoff_live_consumer_adapter_payload_bytes_required: 0",
    ]
    lines[-2] = (
        "  kernel_arg_handoff_live_consumer_adapter_blocked_required: "
        f"{_yaml_bool(not kernel_arg_pass_required)}"
    )
    lines.extend(
        [
            "  kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_required: "
            f"{_yaml_bool(kernel_arg_pass_required)}",
            "  kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_required: "
            f"{_yaml_bool(kernel_arg_pass_required)}",
        ]
    )
    if real_kernel_arg_mutation_required:
        lines.append(
            "  kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_required: true"
        )
    return lines


def _kernel_arg_handoff_adapter_check_lines(
    *,
    allow_kernel_arg_pass: bool = False,
    allow_real_kernel_arg_mutation: bool = False,
) -> list[str]:
    lines = [
        "    require_kernel_arg_handoff_launch_schema_mirror: true",
        "    require_kernel_arg_handoff_live_noop_integration: true",
        "    require_kernel_arg_handoff_live_consumer_adapter: true",
    ]
    if allow_kernel_arg_pass:
        lines.append("    allow_kernel_arg_handoff_live_kernel_arg_pass: true")
    if allow_real_kernel_arg_mutation:
        lines.append("    allow_kernel_arg_handoff_live_real_kernel_arg_mutation: true")
    return lines


def _kernel_arg_semantic_handle_adapter_contract_lines() -> list[str]:
    return [
        "  kernel_arg_semantic_handle_adapter_required: true",
        "  kernel_arg_semantic_handle_adapter_mode: "
        "readonly_kernel_arg_semantic_handle_adapter",
        "  kernel_arg_semantic_handle_adapter_table_schema_hash: "
        f"{PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH}",
        "  kernel_arg_semantic_handle_adapter_semantic_schema_name: "
        f"{PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME}",
        "  kernel_arg_semantic_handle_adapter_semantic_schema_hash: "
        f"{PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH}",
        "  kernel_arg_semantic_handle_adapter_semantic_field_count_required: "
        f"{len(PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS)}",
        "  kernel_arg_semantic_handle_adapter_column_count_required: "
        f"{len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)}",
        "  kernel_arg_semantic_handle_adapter_payload_bytes_required: 0",
        "  kernel_arg_semantic_handle_adapter_passed_to_kernel_required: false",
        "  kernel_arg_semantic_handle_adapter_changes_kernel_launch_args_required: false",
        "  kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_required: false",
    ]


def _kernel_arg_semantic_handle_adapter_check_lines() -> list[str]:
    return ["    require_kernel_arg_semantic_handle_adapter: true"]


def _kernel_side_consumer_schema_adapter_contract_lines(
    *,
    live_enabled: bool = False,
    consumer_connected: bool = False,
    kernel_arg_pass_enabled: bool = False,
) -> list[str]:
    block_reason = (
        "kernel_side_consumer_shadow_only_kernel_arg_pass_enabled"
        if live_enabled and consumer_connected and kernel_arg_pass_enabled
        else "kernel_side_consumer_kernel_arg_pass_disabled"
        if live_enabled and consumer_connected
        else "kernel_side_consumer_not_connected"
        if live_enabled
        else "kernel_side_consumer_live_disabled"
    )
    return [
        "  kernel_side_consumer_schema_adapter_required: true",
        "  kernel_side_consumer_schema_adapter_mode: "
        "readonly_kernel_side_consumer_schema_adapter",
        "  kernel_side_consumer_schema_adapter_table_schema_hash: "
        f"{PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH}",
        "  kernel_side_consumer_schema_adapter_semantic_schema_hash: "
        f"{PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH}",
        "  kernel_side_consumer_schema_adapter_kernel_side_schema_name: "
        f"{PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME}",
        "  kernel_side_consumer_schema_adapter_kernel_side_schema_hash: "
        f"{PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH}",
        "  kernel_side_consumer_schema_adapter_kernel_side_field_count_required: "
        f"{len(PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS)}",
        "  kernel_side_consumer_schema_adapter_column_count_required: "
        f"{len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)}",
        "  kernel_side_consumer_schema_adapter_payload_bytes_required: 0",
        "  kernel_side_consumer_schema_adapter_passed_to_kernel_required: false",
        "  kernel_side_consumer_schema_adapter_changes_kernel_launch_args_required: false",
        "  kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args_required: false",
        "  kernel_side_consumer_schema_adapter_consumer_connected_required: "
        f"{str(live_enabled and consumer_connected).lower()}",
        "  kernel_side_consumer_schema_adapter_live_enabled_required: "
        f"{str(live_enabled).lower()}",
        "  kernel_side_consumer_schema_adapter_live_eligible_required: "
        f"{str(live_enabled).lower()}",
        "  kernel_side_consumer_schema_adapter_block_reason: "
        f"{block_reason}",
    ]


def _kernel_side_consumer_schema_adapter_check_lines() -> list[str]:
    return ["    require_kernel_side_consumer_schema_adapter: true"]


def test_apply_premap_address_capacity_gate_sets_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, capacity=12288)

    options = _apply_premap_address_capacity_gate(
        {
            "enabled": True,
            "premap_address_capacity_gate_path": str(gate),
        },
        project_root=tmp_path,
    )

    assert options["premap_address_manager_capacity"] == 12288
    assert options["premap_address_capacity_gate_id"] == "test_premap_capacity_gate"
    assert options["premap_address_capacity_gate_resolved_path"] == str(gate)
    assert options["premap_address_capacity_gate_recommended_capacity"] == 12288
    assert options["premap_address_capacity_gate_evidence_paths"] == {
        "capacity_sensitivity_json": "outputs/test.json"
    }


def test_apply_premap_consumer_readonly_gate_sets_precondition_metadata(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_required"] is True
    assert (
        options["premap_consumer_readonly_gate_id"]
        == "test_premap_consumer_readonly_gate"
    )
    assert options["premap_consumer_readonly_gate_resolved_path"] == str(gate)
    assert options["premap_consumer_readonly_gate_passed"] is True
    assert options["premap_consumer_readonly_gate_failures"] == []
    assert options["premap_consumer_readonly_gate_metrics"] == {
        "premap_consumer_mapping_count": 2
    }
    assert options["premap_consumer_readonly_gate_evidence_paths"] == {
        "longrun_summary": "outputs/longrun.json"
    }


def test_apply_premap_consumer_readonly_gate_allows_mapping_only_without_lab_gate(
    tmp_path,
):
    raw_options = {
        "enabled": False,
        "emit_premap_consumer_mapping": True,
        "premap_consumer_mapping_emit_rows": False,
        "premap_consumer_mapping_mode": "noop_assertion",
        "premap_consumer_resolve_real_handles": False,
        "premap_consumer_require_readonly_gate": False,
        "premap_consumer_readonly_gate_path": None,
        "premap_descriptor_prep_execution_mode": "off",
        "premap_kernel_arg_handoff_live_enabled": False,
        "premap_kernel_arg_handoff_live_consumer_connected": False,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": False,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": False,
    }
    options = _apply_premap_consumer_readonly_gate(
        raw_options,
        project_root=tmp_path,
    )

    assert options == raw_options
    assert "premap_consumer_readonly_gate_required" not in options
    assert "premap_consumer_readonly_gate_passed" not in options
    assert "premap_consumer_readonly_gate_resolved_path" not in options


def test_apply_premap_consumer_readonly_gate_rejects_missing_required_path(tmp_path):
    with pytest.raises(ValueError, match="requires premap_consumer_readonly_gate_path"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_prep_execution_without_gate(tmp_path):
    with pytest.raises(ValueError, match="requires premap_consumer_require_readonly_gate"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_unknown_prep_execution_mode(tmp_path):
    with pytest.raises(ValueError, match="Unsupported premap_descriptor_prep_execution_mode"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_descriptor_prep_execution_mode": "readonly_descriptor_address",
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_descriptor_prep_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    with pytest.raises(ValueError, match="lab_precondition=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_accepts_descriptor_prep_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_rejects_live_toggle_without_gate(tmp_path):
    with pytest.raises(ValueError, match="premap_consumer_require_readonly_gate=True"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_kernel_arg_handoff_live_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_connected_adapter_without_live_toggle(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="premap_kernel_arg_handoff_live_enabled=True",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_kernel_arg_handoff_live_consumer_connected": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_kernel_arg_pass_enabled(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="premap_kernel_arg_handoff_kernel_arg_pass_enabled=True",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_signature_mismatch_live_without_live(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="allow_signature_mismatch_live=True",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_prepared_materialization_without_prepared_source(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="can only be enabled",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
                    "original_kernel_arg_identity"
                ),
                "premap_kernel_arg_handoff_prepared_table_materialization_mode": (
                    "original_kernel_arg_alias_after_prepared_handle_check"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_accepts_producer_native_adapter_materialization(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
            kernel_arg_pass_required=True,
            real_kernel_arg_mutation_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(
            allow_kernel_arg_pass=True,
            allow_real_kernel_arg_mutation=True,
        ),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": False,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "off",
            "premap_consumer_resolve_real_handles": False,
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_producer_future_wna16_typed_slot_envelope_enabled": (
                True
            ),
            "premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled": (
                True
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
            "premap_kernel_arg_handoff_live_consumer_connected": True,
            "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
            "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
            "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
                "original_kernel_arg_identity"
            ),
            "premap_kernel_arg_handoff_prepared_table_materialization_mode": (
                "producer_native_adapter"
            ),
        },
        project_root=tmp_path,
    )

    assert (
        options["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "producer_native_adapter"
    )


def test_apply_premap_consumer_readonly_gate_rejects_producer_native_adapter_without_future_variant(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="producer_native_adapter",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_kernel_arg_handoff_prepared_table_materialization_mode": (
                    "producer_native_adapter"
                ),
            },
            project_root=tmp_path,
        )


@pytest.mark.parametrize(
    "missing_key",
    [
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled",
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled",
    ],
)
def test_apply_premap_consumer_readonly_gate_rejects_producer_identity_envelope_without_required_flags(
    tmp_path,
    missing_key,
):
    options = {
        "enabled": True,
        "premap_consumer_require_readonly_gate": True,
        "premap_kernel_arg_handoff_live_enabled": True,
        "premap_kernel_arg_handoff_live_consumer_connected": True,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
        "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
        "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
            "original_kernel_arg_identity"
        ),
    }
    options.pop(missing_key)

    with pytest.raises(
        ValueError,
        match="producer_minimal_identity_envelope_enabled=True",
    ):
        _apply_premap_consumer_readonly_gate(options, project_root=tmp_path)


def test_apply_premap_consumer_readonly_gate_accepts_producer_identity_envelope_without_mapping(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
            kernel_arg_pass_required=True,
            real_kernel_arg_mutation_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(
            allow_kernel_arg_pass=True,
            allow_real_kernel_arg_mutation=True,
        ),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": False,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "off",
            "premap_consumer_resolve_real_handles": False,
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
            "premap_kernel_arg_handoff_live_consumer_connected": True,
            "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
            "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
            "premap_kernel_arg_handoff_minimal_identity_envelope_enabled": True,
            "premap_kernel_arg_handoff_producer_minimal_identity_envelope_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
                "original_kernel_arg_identity"
            ),
            "premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True
    assert options["premap_consumer_readonly_gate_required"] is True
    assert (
        options["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "off"
    )


def test_apply_premap_consumer_readonly_gate_accepts_prepared_handle_table_live_canary(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
            kernel_arg_pass_required=True,
            real_kernel_arg_mutation_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(
            allow_kernel_arg_pass=True,
            allow_real_kernel_arg_mutation=True,
        ),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
            "premap_kernel_arg_handoff_live_consumer_connected": True,
            "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
            "premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_live_enabled": True,
            "premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live": True,
            "premap_kernel_arg_handoff_single_field_replacement_candidate_source": (
                "prepared_handle_table"
            ),
            "premap_kernel_arg_handoff_prepared_table_materialization_mode": (
                "original_kernel_arg_alias_after_prepared_handle_check"
            ),
            "premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True
    assert options["premap_consumer_readonly_gate_required"] is True
    assert (
        options["premap_kernel_arg_handoff_prepared_table_materialization_mode"]
        == "original_kernel_arg_alias_after_prepared_handle_check"
    )


def test_apply_premap_consumer_readonly_gate_accepts_kernel_arg_pass_live_gate(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
            kernel_arg_pass_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(
            allow_kernel_arg_pass=True
        ),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
            "premap_kernel_arg_handoff_live_consumer_connected": True,
            "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_rejects_kernel_arg_pass_without_gate_allow(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
            kernel_arg_pass_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(),
    )

    with pytest.raises(
        ValueError,
        match="allow_kernel_arg_handoff_live_kernel_arg_pass=true",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": True,
                "premap_kernel_arg_handoff_live_consumer_connected": True,
                "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_kernel_arg_pass_without_adapter_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_check_lines=[
            "    allow_kernel_arg_handoff_live_kernel_arg_pass: true",
        ],
    )

    with pytest.raises(
        ValueError,
        match="kernel_arg_handoff_live_consumer_adapter_required=true",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": True,
                "premap_kernel_arg_handoff_live_consumer_connected": True,
                "premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_live_toggle_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
    )

    with pytest.raises(ValueError, match="kernel_arg_handoff_live_toggle_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_non_bool_live_toggle_required(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
    )
    gate.write_text(
        gate.read_text(encoding="utf-8").replace(
            "kernel_arg_handoff_live_toggle_required: true",
            'kernel_arg_handoff_live_toggle_required: "false"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="live_toggle_required must be boolean"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_accepts_default_disabled_live_toggle_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": False,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_accepts_enabled_blocked_live_toggle_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_rejects_live_toggle_enabled_mismatch(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
    )

    with pytest.raises(ValueError, match="live-toggle enabled requirement"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_accepts_default_disabled_live_adapter_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=False
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": False,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_accepts_semantic_handle_adapter_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + _kernel_arg_semantic_handle_adapter_contract_lines()
        ),
        extra_check_lines=(
            _kernel_arg_handoff_adapter_check_lines()
            + _kernel_arg_semantic_handle_adapter_check_lines()
        ),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": False,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_requires_semantic_adapter_check(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + _kernel_arg_semantic_handle_adapter_contract_lines()
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(),
    )

    with pytest.raises(
        ValueError,
        match="require_kernel_arg_semantic_handle_adapter=true",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_accepts_kernel_side_consumer_schema_adapter_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + _kernel_arg_semantic_handle_adapter_contract_lines()
            + _kernel_side_consumer_schema_adapter_contract_lines()
        ),
        extra_check_lines=(
            _kernel_arg_handoff_adapter_check_lines()
            + _kernel_arg_semantic_handle_adapter_check_lines()
            + _kernel_side_consumer_schema_adapter_check_lines()
        ),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": False,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_requires_semantic_for_kernel_side_schema(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + _kernel_side_consumer_schema_adapter_contract_lines()
        ),
        extra_check_lines=(
            _kernel_arg_handoff_adapter_check_lines()
            + _kernel_side_consumer_schema_adapter_check_lines()
        ),
    )

    with pytest.raises(
        ValueError,
        match="kernel_arg_semantic_handle_adapter_required=true",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_kernel_side_schema_live_enabled(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    bad_kernel_side_lines = [
        (
            "  kernel_side_consumer_schema_adapter_live_enabled_required: true"
            if line.startswith(
                "  kernel_side_consumer_schema_adapter_live_enabled_required:"
            )
            else line
        )
        for line in _kernel_side_consumer_schema_adapter_contract_lines()
    ]
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + _kernel_arg_semantic_handle_adapter_contract_lines()
            + bad_kernel_side_lines
        ),
        extra_check_lines=(
            _kernel_arg_handoff_adapter_check_lines()
            + _kernel_arg_semantic_handle_adapter_check_lines()
            + _kernel_side_consumer_schema_adapter_check_lines()
        ),
    )

    with pytest.raises(ValueError, match="live_enabled_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_launch_schema_for_semantic_adapter(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        extra_contract_lines=_kernel_arg_semantic_handle_adapter_contract_lines(),
        extra_check_lines=_kernel_arg_semantic_handle_adapter_check_lines(),
    )

    with pytest.raises(
        ValueError,
        match="kernel_arg_handoff_launch_schema_mirror_required=true",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_semantic_schema_mismatch(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    bad_semantic_lines = [
        (
            "  kernel_arg_semantic_handle_adapter_semantic_schema_hash: "
            "deadbeef"
            if line.startswith(
                "  kernel_arg_semantic_handle_adapter_semantic_schema_hash:"
            )
            else line
        )
        for line in _kernel_arg_semantic_handle_adapter_contract_lines()
    ]
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + bad_semantic_lines
        ),
        extra_check_lines=(
            _kernel_arg_handoff_adapter_check_lines()
            + _kernel_arg_semantic_handle_adapter_check_lines()
        ),
    )

    with pytest.raises(ValueError, match="semantic_schema_hash"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_semantic_live_compatibility(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    bad_semantic_lines = [
        (
            "  kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_required: true"
            if line.startswith(
                "  kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_required:"
            )
            else line
        )
        for line in _kernel_arg_semantic_handle_adapter_contract_lines()
    ]
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=(
            _kernel_arg_handoff_adapter_contract_lines(live_enabled=False)
            + bad_semantic_lines
        ),
        extra_check_lines=(
            _kernel_arg_handoff_adapter_check_lines()
            + _kernel_arg_semantic_handle_adapter_check_lines()
        ),
    )

    with pytest.raises(ValueError, match="live_compatible"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_accepts_enabled_blocked_live_adapter_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_accepts_connected_blocked_live_adapter_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(),
    )

    options = _apply_premap_consumer_readonly_gate(
        {
            "enabled": True,
            "emit_premap_consumer_mapping": True,
            "premap_consumer_require_readonly_gate": True,
            "premap_consumer_readonly_gate_path": str(gate),
            "premap_consumer_mapping_mode": "noop_assertion",
            "premap_consumer_resolve_real_handles": True,
            "premap_policy": "premap_only_with_consumer_mapping_noop",
            "premap_descriptor_bytes": 4096,
            "premap_descriptor_prep_execution_mode": (
                "readonly_descriptor_address_object"
            ),
            "premap_kernel_arg_handoff_live_enabled": True,
            "premap_kernel_arg_handoff_live_consumer_connected": True,
        },
        project_root=tmp_path,
    )

    assert options["premap_consumer_readonly_gate_passed"] is True


def test_apply_premap_consumer_readonly_gate_rejects_connected_live_adapter_without_runtime_option(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=True,
        kernel_arg_handoff_live_toggle_block_reason=(
            "kernel_arg_handoff_kernel_consumer_not_connected"
        ),
        kernel_arg_handoff_live_toggle_live_eligible_required=True,
        require_kernel_arg_handoff_live_toggle=True,
        extra_contract_lines=_kernel_arg_handoff_adapter_contract_lines(
            live_enabled=True,
            consumer_connected_required=True,
        ),
        extra_check_lines=_kernel_arg_handoff_adapter_check_lines(),
    )

    with pytest.raises(ValueError, match="live no-op integration contract"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": True,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_non_bool_live_toggle_enabled_required(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=True,
    )
    gate.write_text(
        gate.read_text(encoding="utf-8").replace(
            "kernel_arg_handoff_live_toggle_enabled_required: false",
            'kernel_arg_handoff_live_toggle_enabled_required: "false"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="live_toggle_enabled_required must"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_live_toggle_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        kernel_arg_handoff_live_toggle_required=True,
        kernel_arg_handoff_live_toggle_enabled_required=False,
        require_kernel_arg_handoff_live_toggle=False,
    )

    with pytest.raises(ValueError, match="require_kernel_arg_handoff_live_toggle=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
                "premap_kernel_arg_handoff_live_enabled": False,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_real_descriptor_prep_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=False,
    )

    with pytest.raises(ValueError, match="real_descriptor_prep_required=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_real_descriptor_prep_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=False,
    )

    with pytest.raises(ValueError, match="require_real_descriptor_prep=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_kernel_arg_shadow_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=True,
        kernel_arg_shadow_table_required=False,
    )

    with pytest.raises(ValueError, match="kernel_arg_shadow_table_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_kernel_arg_shadow_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=True,
        kernel_arg_shadow_table_required=True,
        require_kernel_arg_shadow_table=False,
    )

    with pytest.raises(ValueError, match="require_kernel_arg_shadow_table=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_read_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=True,
        kernel_arg_shadow_table_required=True,
        require_kernel_arg_shadow_table=True,
        consumer_shim_table_read_required=False,
    )

    with pytest.raises(ValueError, match="consumer_shim_table_read_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_read_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=True,
        kernel_arg_shadow_table_required=True,
        require_kernel_arg_shadow_table=True,
        consumer_shim_table_read_required=True,
        require_consumer_shim_table_read=False,
    )

    with pytest.raises(ValueError, match="require_consumer_shim_table_read=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_consume_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=True,
        kernel_arg_shadow_table_required=True,
        require_kernel_arg_shadow_table=True,
        consumer_shim_table_read_required=True,
        require_consumer_shim_table_read=True,
        consumer_shim_table_consume_required=False,
    )

    with pytest.raises(ValueError, match="consumer_shim_table_consume_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_consume_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        real_descriptor_prep_required=True,
        require_real_descriptor_prep=True,
        kernel_arg_shadow_table_required=True,
        require_kernel_arg_shadow_table=True,
        consumer_shim_table_read_required=True,
        require_consumer_shim_table_read=True,
        consumer_shim_table_consume_required=True,
        require_consumer_shim_table_consume=False,
    )

    with pytest.raises(ValueError, match="require_consumer_shim_table_consume=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_consume_field_read_contract(
    tmp_path,
):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        consumer_shim_table_consume_handle_field_reads_required=False,
    )

    with pytest.raises(
        ValueError,
        match="consumer_shim_table_consume_handle_field_reads_required",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_object_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        consumer_shim_table_object_required=False,
    )

    with pytest.raises(ValueError, match="consumer_shim_table_object_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_table_object_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        require_consumer_shim_table_object=False,
    )

    with pytest.raises(ValueError, match="require_consumer_shim_table_object=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_prep_execution_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        consumer_shim_prep_execution_required=False,
    )

    with pytest.raises(ValueError, match="consumer_shim_prep_execution_required"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_consumer_shim_prep_execution_check(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        require_consumer_shim_prep_execution=False,
    )

    with pytest.raises(ValueError, match="require_consumer_shim_prep_execution=true"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_requires_prep_execution_field_read_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=0,
        descriptor_prep_kernel_arg_mutation=False,
        consumer_shim_prep_execution_handle_field_reads_required=False,
    )

    with pytest.raises(
        ValueError,
        match="consumer_shim_prep_execution_handle_field_reads_required",
    ):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "noop_assertion",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_descriptor_prep_contract_mutation(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(
        gate,
        lab_precondition=True,
        descriptor_prep_execution_mode="readonly_descriptor_address_object",
        descriptor_prep_payload_bytes=128,
        descriptor_prep_kernel_arg_mutation=True,
    )

    with pytest.raises(ValueError, match="descriptor prep contract"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_descriptor_prep_execution_mode": (
                    "readonly_descriptor_address_object"
                ),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_failed_gate(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate, passed=False)

    with pytest.raises(ValueError, match="did not pass"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_non_bool_passed(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)
    text = gate.read_text(encoding="utf-8")
    gate.write_text(text.replace("  passed: true", "  passed: 'false'"), encoding="utf-8")

    with pytest.raises(TypeError, match="gate.passed"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_payload_contract(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate, payload_bytes=4096)

    with pytest.raises(ValueError, match="violates the no-op contract"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_non_noop_runtime_mode(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    with pytest.raises(ValueError, match="mapping_mode=noop_assertion"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "emit_premap_consumer_mapping": True,
                "premap_consumer_require_readonly_gate": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_consumer_mapping_mode": "apply",
                "premap_consumer_resolve_real_handles": True,
                "premap_policy": "premap_only_with_consumer_mapping_noop",
                "premap_descriptor_bytes": 4096,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_rejects_descriptor_size_mismatch(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)

    with pytest.raises(ValueError, match="descriptor size"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
                "premap_descriptor_bytes": 8192,
            },
            project_root=tmp_path,
        )


def test_apply_premap_consumer_readonly_gate_checks_default_descriptor_size(tmp_path):
    gate = tmp_path / "readonly_gate.yaml"
    _write_readonly_gate(gate)
    text = gate.read_text(encoding="utf-8")
    gate.write_text(
        text.replace("  descriptor_bytes: 4096", "  descriptor_bytes: 2048"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="descriptor size"):
        _apply_premap_consumer_readonly_gate(
            {
                "enabled": True,
                "premap_consumer_readonly_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_accepts_matching_inline_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, capacity=8192)

    options = _apply_premap_address_capacity_gate(
        {
            "enabled": True,
            "premap_address_capacity_gate_path": str(gate),
            "premap_address_manager_capacity": 8192,
        },
        project_root=tmp_path,
    )

    assert options["premap_address_manager_capacity"] == 8192


def test_apply_premap_address_capacity_gate_rejects_mismatched_inline_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, capacity=12288)

    with pytest.raises(ValueError, match="does not match"):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
                "premap_address_manager_capacity": 8192,
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_rejects_missing_capacity_gate(tmp_path):
    gate = tmp_path / "gate.yaml"
    gate.write_text("schema_version: 1\nartifact_id: bad_gate\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing `capacity_gate`"):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_rejects_missing_recommended_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: bad_gate",
                "capacity_gate:",
                "  low_footprint_capacity_entries: 8192",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="recommended_capacity_entries"):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


def test_apply_premap_address_capacity_gate_rejects_non_numeric_capacity(tmp_path):
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "artifact_id: bad_gate",
                "capacity_gate:",
                "  recommended_capacity_entries: not-a-number",
                "",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        _apply_premap_address_capacity_gate(
            {
                "enabled": True,
                "premap_address_capacity_gate_path": str(gate),
            },
            project_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("sample_count", "expected_end"),
    [
        (128, 127),
        (512, 511),
    ],
)
def test_default_longrun_audit_config_uses_premap_capacity_gate(
    sample_count, expected_end
):
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        f"router_mtp_trace_external_prompt_gate_dolly_{sample_count}_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["data"] == f"configs/data/external_prompt_gate_dolly_{sample_count}.yaml"
    assert config["trace"]["max_samples"] == sample_count
    assert config["trace"]["expected_sample_end"] == expected_end
    shadow = config["trace"]["runtime_shadow"]

    assert shadow["writer_mode"] == "jsonl_batched"
    assert shadow["outcome_logging_mode"] == "off"
    assert shadow["record_router_topk"] is True
    assert shadow["emit_premap_summaries"] is True
    assert shadow["emit_premap_address_manager_counters"] is True
    assert shadow["premap_summary_sample_period"] == (
        32 if sample_count == 128 else 64
    )
    assert (
        shadow["premap_address_capacity_gate_path"]
        == "configs/runtime/premap_address_capacity_gate_dolly128_gen64_awq_w7900_gpu1.yaml"
    )
    gate = yaml.safe_load(
        (
            PROJECT_ROOT / shadow["premap_address_capacity_gate_path"]
        ).read_text(encoding="utf-8")
    )
    evidence_paths = gate["evidence_paths"]
    assert (
        evidence_paths["premap_only_longrun_summary_md"]
        == "docs/premap_longrun_audit_summary.md"
    )
    assert "premap_only_longrun_512_json" in evidence_paths
    assert "premap_only_longrun_512_gate_json" in evidence_paths
    assert "premap_address_manager_capacity" not in shadow
    assert shadow["emit_premap_consumer_mapping"] is True
    assert shadow["premap_consumer_mapping_mode"] == "noop_assertion"
    assert shadow["premap_consumer_mapping_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert shadow["premap_consumer_resolve_real_handles"] is True
    assert shadow["premap_consumer_mapping_sample_period"] == (
        32 if sample_count == 128 else 64
    )
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_readonly.yaml"
    )
    assert (
        shadow["premap_descriptor_prep_execution_mode"]
        == "readonly_descriptor_address_object"
    )
    assert shadow["premap_kernel_arg_handoff_live_enabled"] is True
    assert shadow["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert shadow["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    readonly_gate = yaml.safe_load(
        (
            PROJECT_ROOT / shadow["premap_consumer_readonly_gate_path"]
        ).read_text(encoding="utf-8")
    )
    assert readonly_gate["status"] == "passed"
    assert readonly_gate["gate"]["passed"] is True
    assert readonly_gate["contract"]["payload_bytes_required"] == 0
    assert readonly_gate["contract"]["ready_credit_required"] is False
    assert readonly_gate["contract"]["changes_router_required"] is False
    assert readonly_gate["contract"]["changes_descriptor_order_required"] is False
    readonly_contract = readonly_gate["contract"]
    readonly_check = readonly_gate["gate"]["check"]
    readonly_metrics = readonly_gate["gate"]["metrics"]
    assert (
        readonly_metrics["premap_consumer_real_descriptor_handle_hit_rate"]
        == 1.0
    )
    assert readonly_contract["kernel_arg_shadow_table_required"] is True
    assert readonly_check["require_kernel_arg_shadow_table"] is True
    assert readonly_contract["consumer_shim_table_read_required"] is True
    assert readonly_check["require_consumer_shim_table_read"] is True
    assert readonly_contract["consumer_shim_table_consume_required"] is True
    assert readonly_check["require_consumer_shim_table_consume"] is True
    assert (
        readonly_contract["consumer_shim_table_consume_handle_field_reads_required"]
        is True
    )
    assert (
        readonly_metrics["premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate"]
        == 1.0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
        ]
        == 1.0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate"
        ]
        == 1.0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
        ]
        == 443592
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
        ]
        == 332694
    )
    assert readonly_contract["kernel_arg_handoff_launch_schema_mirror_required"] is True
    assert readonly_check["require_kernel_arg_handoff_launch_schema_mirror"] is True
    assert readonly_contract["kernel_arg_handoff_live_toggle_required"] is True
    assert readonly_contract["kernel_arg_handoff_live_toggle_enabled_required"] is True
    assert (
        readonly_contract["kernel_arg_handoff_live_toggle_block_reason"]
        == "kernel_arg_handoff_kernel_consumer_not_connected"
    )
    assert readonly_check["require_kernel_arg_handoff_live_toggle"] is True
    assert readonly_contract["kernel_arg_handoff_live_noop_integration_required"] is True
    assert (
        readonly_contract[
            "kernel_arg_handoff_live_noop_integration_consumer_connected_required"
        ]
        is True
    )
    assert readonly_check["require_kernel_arg_handoff_live_noop_integration"] is True
    assert readonly_contract["kernel_arg_handoff_live_consumer_adapter_required"] is True
    assert (
        readonly_contract["kernel_arg_handoff_live_consumer_adapter_mode"]
        == "readonly_kernel_arg_handoff_live_consumer_adapter"
    )
    assert (
        readonly_contract["kernel_arg_handoff_live_consumer_adapter_enabled_required"]
        is True
    )
    assert (
        readonly_contract[
            "kernel_arg_handoff_live_consumer_adapter_consumer_connected_required"
        ]
        is True
    )
    assert (
        readonly_contract[
            "kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_required"
        ]
        is False
    )
    assert readonly_check["require_kernel_arg_handoff_live_consumer_adapter"] is True
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert readonly_contract["kernel_arg_semantic_handle_adapter_required"] is True
    assert (
        readonly_contract["kernel_arg_semantic_handle_adapter_mode"]
        == "readonly_kernel_arg_semantic_handle_adapter"
    )
    assert (
        readonly_contract["kernel_arg_semantic_handle_adapter_semantic_schema_name"]
        == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_NAME
    )
    assert (
        readonly_contract["kernel_arg_semantic_handle_adapter_semantic_schema_hash"]
        == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
    )
    assert (
        readonly_contract[
            "kernel_arg_semantic_handle_adapter_semantic_field_count_required"
        ]
        == len(PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_FIELDS)
    )
    assert (
        readonly_contract["kernel_arg_semantic_handle_adapter_column_count_required"]
        == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
    )
    assert (
        readonly_contract["kernel_arg_semantic_handle_adapter_table_schema_hash"]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        readonly_contract["kernel_arg_semantic_handle_adapter_passed_to_kernel_required"]
        is False
    )
    assert (
        readonly_contract[
            "kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args_required"
        ]
        is False
    )
    assert readonly_check["require_kernel_arg_semantic_handle_adapter"] is True
    assert readonly_contract["native_typed_consumer_bridge_required"] is True
    assert readonly_check["require_native_typed_consumer_bridge"] is True
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_checked_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_ok_count"
        ]
        == 10195
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_row_count"
        ]
        == 110898
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_required_handle_nonzero_count"
        ]
        == 332694
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_failure_count"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_payload_bytes"
        ]
        == 0
    )
    assert (
        readonly_metrics[
            "premap_consumer_descriptor_prep_consumer_shim_native_typed_consumer_bridge_passed_to_kernel_count"
        ]
        == 0
    )
    assert shadow["premap_policy"] == "premap_only_with_consumer_mapping_noop"
    assert shadow["premap_source"] == "current_router_topk_premap_shadow"
    assert shadow["premap_descriptor_bytes"] == 4096
    assert shadow["emit_outcomes"] is False
    assert shadow["emit_descriptor_order_summaries"] is False
    assert shadow["descriptor_order_metrics_mode"] == "count_only"
    assert shadow["descriptor_order_event_mode"] == "minimal"
    assert shadow["emit_decoder_layer_timing"] is False
    assert shadow["emit_decoder_component_timing"] is False
    assert shadow["emit_moe_substage_timing"] is False
    assert shadow["emit_engine_timing"] is False
    assert shadow["emit_wna16_kernel_timing"] is False
    assert shadow["decoder_source_timing_mode"] == "off"
    assert shadow["moe_source_timing_mode"] == "off"


def test_premap_consumer_mapping_smoke_config_requires_readonly_gate():
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        "router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_premap_consumer_mapping_smoke.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    shadow = config["trace"]["runtime_shadow"]

    assert shadow["emit_premap_consumer_mapping"] is True
    assert shadow["premap_consumer_mapping_mode"] == "noop_assertion"
    assert shadow["premap_consumer_resolve_real_handles"] is True
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml"
    )
    assert (
        shadow["premap_descriptor_prep_execution_mode"]
        == "readonly_descriptor_address_object"
    )
    assert shadow["premap_kernel_arg_handoff_live_enabled"] is False
    assert shadow["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert shadow["premap_policy"] == "premap_only_with_consumer_mapping_noop"
    assert shadow["premap_descriptor_bytes"] == 4096


def test_live_connected_adapter_canary_config_uses_connected_blocked_gate():
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        "router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert (
        config["output_dir"]
        == "data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary"
    )
    assert (
        config["trace"]["split_id"]
        == "external_prompt_gate_dolly_1_gen16_live_connected_adapter_canary"
    )
    assert config["trace"]["max_samples"] == 1
    assert config["trace"]["max_tokens"] == 16

    shadow = config["trace"]["runtime_shadow"]
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml"
    )
    assert shadow["premap_kernel_arg_handoff_live_enabled"] is True
    assert shadow["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert shadow["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert shadow["emit_outcomes"] is False
    assert shadow["emit_descriptor_order_summaries"] is False
    assert shadow["emit_decoder_layer_timing"] is False

    updated = _apply_premap_consumer_readonly_gate(
        dict(shadow),
        project_root=PROJECT_ROOT,
    )
    assert updated["premap_consumer_readonly_gate_passed"] is True

    gate = yaml.safe_load(
        (PROJECT_ROOT / shadow["premap_consumer_readonly_gate_path"]).read_text(
            encoding="utf-8"
        )
    )
    contract = gate["contract"]
    metrics = gate["gate"]["metrics"]
    evidence_paths = gate["evidence_paths"]
    assert (
        gate["artifact_id"]
        == "premap_consumer_readonly_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary"
    )
    assert (
        evidence_paths["live_connected_blocked_canary_1_performance_json"]
        == "data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/performance_summary.json"
    )
    assert (
        evidence_paths["live_connected_blocked_canary_1_gate_json"]
        == "data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/connected_blocked_gate_check.json"
    )
    assert (
        evidence_paths["live_connected_blocked_kernel_side_schema_canary_1_gate_json"]
        == "data/traces/external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_live_connected_adapter_canary/connected_blocked_kernel_side_schema_gate_check.json"
    )
    assert (
        evidence_paths["live_connected_blocked_kernel_side_schema_canary_8_gate_json"]
        == "data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary/connected_blocked_kernel_side_schema_gate_check.json"
    )
    assert (
        evidence_paths["live_connected_blocked_canary_8_performance_json"]
        == "data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary/performance_summary.json"
    )
    assert (
        evidence_paths["live_connected_blocked_canary_8_gate_json"]
        == "data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary/connected_blocked_gate_check.json"
    )
    assert contract["payload_bytes_required"] == 0
    assert contract["ready_credit_required"] is False
    assert contract["kernel_arg_handoff_live_toggle_enabled_required"] is True
    assert (
        contract["kernel_arg_handoff_live_noop_integration_consumer_connected_required"]
        is True
    )
    assert (
        contract["kernel_arg_handoff_live_noop_integration_block_reason"]
        == "kernel_arg_handoff_kernel_arg_pass_disabled"
    )
    assert (
        contract[
            "kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_required"
        ]
        is False
    )
    assert (
        contract["kernel_arg_handoff_live_consumer_adapter_consumer_connected_required"]
        is True
    )
    assert (
        contract["kernel_arg_handoff_live_consumer_adapter_block_reason"]
        == "kernel_arg_handoff_kernel_arg_pass_disabled"
    )
    assert contract["kernel_arg_semantic_handle_adapter_required"] is True
    assert contract["kernel_side_consumer_schema_adapter_required"] is True
    assert (
        contract["kernel_side_consumer_schema_adapter_consumer_connected_required"]
        is True
    )
    assert contract["kernel_side_consumer_schema_adapter_live_enabled_required"] is True
    assert contract["kernel_side_consumer_schema_adapter_live_eligible_required"] is True
    assert (
        contract["kernel_side_consumer_schema_adapter_block_reason"]
        == "kernel_side_consumer_kernel_arg_pass_disabled"
    )
    check = gate["gate"]["check"]
    assert check["allow_enabled_blocked_live_toggle"] is True
    assert check["allow_connected_blocked_consumer_adapter"] is True
    assert check["require_kernel_arg_semantic_handle_adapter"] is True
    assert check["require_kernel_side_consumer_schema_adapter"] is True
    live_noop_checked_count = metrics[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count"
    ]
    live_adapter_checked_count = metrics[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count"
    ]
    assert live_noop_checked_count > 0
    assert live_adapter_checked_count > 0
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count"
        ]
        == live_noop_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count"
        ]
        == live_noop_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes"
        ]
        == 0
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
        ]
        == live_adapter_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count"
        ]
        == live_adapter_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count"
        ]
        == 0
    )
    kernel_side_checked_count = metrics[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_checked_count"
    ]
    assert kernel_side_checked_count == live_adapter_checked_count
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_consumer_connected_count"
        ]
        == kernel_side_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_enabled_count"
        ]
        == kernel_side_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_live_eligible_count"
        ]
        == kernel_side_checked_count
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_block_reason"
        ]
        == "kernel_side_consumer_kernel_arg_pass_disabled"
    )
    assert (
        metrics[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_side_consumer_schema_adapter_passed_to_kernel_count"
        ]
        == 0
    )


def test_live_connected_adapter_canary_8_sample_config_uses_connected_blocked_gate():
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        "router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert (
        config["output_dir"]
        == "data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_live_connected_adapter_canary"
    )
    assert (
        config["trace"]["split_id"]
        == "external_prompt_gate_dolly_8_gen64_live_connected_adapter_canary"
    )
    assert config["trace"]["max_samples"] == 8
    assert config["trace"]["max_tokens"] == 64

    shadow = config["trace"]["runtime_shadow"]
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml"
    )
    assert shadow["premap_kernel_arg_handoff_live_enabled"] is True
    assert shadow["premap_kernel_arg_handoff_live_consumer_connected"] is True
    assert shadow["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert shadow["emit_outcomes"] is False
    assert shadow["emit_descriptor_order_summaries"] is False
    assert shadow["emit_decoder_layer_timing"] is False

    updated = _apply_premap_consumer_readonly_gate(
        dict(shadow),
        project_root=PROJECT_ROOT,
    )
    assert updated["premap_consumer_readonly_gate_passed"] is True


def test_premap_longrun_audit_smoke_config_matches_8_sample_contract():
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        "router_mtp_trace_external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert (
        config["output_dir"]
        == "data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke"
    )
    assert config["data"] == "configs/data/external_prompt_gate_dolly_128.yaml"
    assert config["trace"]["split_id"] == "external_prompt_gate_dolly_8_gen64_longrun_audit_smoke"
    assert config["trace"]["expected_sample_start"] == 0
    assert config["trace"]["expected_sample_end"] == 7
    assert config["trace"]["max_samples"] == 8

    shadow = config["trace"]["runtime_shadow"]
    assert (
        shadow["output_path"]
        == "data/traces/external_prompt_gate_dolly_8_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/runtime_shadow.jsonl"
    )
    assert shadow["writer_mode"] == "jsonl_batched"
    assert shadow["record_router_topk"] is True
    assert shadow["emit_premap_summaries"] is True
    assert shadow["emit_premap_address_manager_counters"] is True
    assert shadow["premap_summary_sample_period"] == 32
    assert shadow["emit_premap_consumer_mapping"] is True
    assert shadow["premap_consumer_mapping_mode"] == "noop_assertion"
    assert shadow["premap_consumer_mapping_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert shadow["premap_consumer_resolve_real_handles"] is True
    assert shadow["premap_consumer_mapping_sample_period"] == 32
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml"
    )
    assert (
        shadow["premap_descriptor_prep_execution_mode"]
        == "readonly_descriptor_address_object"
    )
    assert shadow["premap_kernel_arg_handoff_live_enabled"] is False
    assert shadow["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert shadow["emit_outcomes"] is False
    assert shadow["outcome_logging_mode"] == "off"
    assert shadow["emit_descriptor_order_summaries"] is False
    assert shadow["emit_decoder_layer_timing"] is False
    assert shadow["emit_decoder_component_timing"] is False
    assert shadow["emit_moe_substage_timing"] is False
    assert shadow["emit_engine_timing"] is False


def test_premap_longrun_audit_smoke_config_matches_32_sample_contract():
    config_path = PROJECT_ROOT / (
        "configs/trace/"
        "router_mtp_trace_external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert (
        config["output_dir"]
        == "data/traces/external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke"
    )
    assert config["data"] == "configs/data/external_prompt_gate_dolly_128.yaml"
    assert config["trace"]["split_id"] == "external_prompt_gate_dolly_32_gen64_longrun_audit_smoke"
    assert config["trace"]["expected_sample_start"] == 0
    assert config["trace"]["expected_sample_end"] == 31
    assert config["trace"]["max_samples"] == 32

    shadow = config["trace"]["runtime_shadow"]
    assert (
        shadow["output_path"]
        == "data/traces/external_prompt_gate_dolly_32_awq_vllm_gpu1_decode_gen64_longrun_audit_smoke/runtime_shadow.jsonl"
    )
    assert shadow["writer_mode"] == "jsonl_batched"
    assert shadow["record_router_topk"] is True
    assert shadow["emit_premap_summaries"] is True
    assert shadow["emit_premap_address_manager_counters"] is True
    assert shadow["premap_summary_sample_period"] == 32
    assert shadow["emit_premap_consumer_mapping"] is True
    assert shadow["premap_consumer_mapping_mode"] == "noop_assertion"
    assert shadow["premap_consumer_mapping_source"] == (
        "fused_moe_prepare_expert_assignment"
    )
    assert shadow["premap_consumer_resolve_real_handles"] is True
    assert shadow["premap_consumer_mapping_sample_period"] == 32
    assert shadow["premap_consumer_require_readonly_gate"] is True
    assert (
        shadow["premap_consumer_readonly_gate_path"]
        == "configs/runtime/premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml"
    )
    assert (
        shadow["premap_descriptor_prep_execution_mode"]
        == "readonly_descriptor_address_object"
    )
    assert shadow["premap_kernel_arg_handoff_live_enabled"] is False
    assert shadow["premap_kernel_arg_handoff_kernel_arg_pass_enabled"] is False
    assert shadow["emit_outcomes"] is False
    assert shadow["outcome_logging_mode"] == "off"
    assert shadow["emit_descriptor_order_summaries"] is False
    assert shadow["emit_decoder_layer_timing"] is False
    assert shadow["emit_decoder_component_timing"] is False
    assert shadow["emit_moe_substage_timing"] is False
    assert shadow["emit_engine_timing"] is False
