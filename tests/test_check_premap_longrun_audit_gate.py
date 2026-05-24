from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
)

from scripts.check_premap_longrun_audit_gate import check_summary


def _passing_summary() -> dict:
    return {
        "row_count": 4,
        "event_counts": {
            "premap_summary": 2,
            "premap_consumer_mapping": 2,
        },
        "aggregate": {
            "premap_summary_payload_bytes": 0,
            "premap_address_evicted_count": 0,
            "premap_address_eviction_pressure_mean": 0.0,
            "premap_address_resident_count_max": 10,
            "premap_address_reuse_rate_mean": 0.99,
            "premap_consumer_address_hit_rate": 1.0,
            "premap_consumer_descriptor_handle_hit_rate": 1.0,
            "premap_consumer_real_descriptor_handle_hit_rate": 1.0,
            "premap_consumer_real_descriptor_handle_hit_count": 20,
            "premap_consumer_real_descriptor_handle_packed_weight_hit_count": 20,
            "premap_consumer_real_descriptor_handle_packed_weight_miss_count": 0,
            "premap_consumer_real_descriptor_handle_scale_metadata_hit_count": 20,
            "premap_consumer_real_descriptor_handle_scale_metadata_miss_count": 0,
            "premap_consumer_real_descriptor_handle_aux_metadata_hit_count": 20,
            "premap_consumer_real_descriptor_handle_aux_metadata_miss_count": 0,
            "premap_consumer_real_descriptor_handle_resolver_disabled_count": 0,
            "premap_consumer_real_descriptor_handle_consumer_layer_missing_count": 0,
            "premap_consumer_real_descriptor_handle_expert_map_miss_count": 0,
            "premap_consumer_real_descriptor_handle_no_handle_parts_count": 0,
            "premap_consumer_lookup_after_prepare_rate": 1.0,
            "premap_consumer_real_descriptor_handle_binding_mismatch_count": 0,
            "premap_consumer_readonly_lookup_count": 20,
            "premap_consumer_readonly_handle_hit_rate": 1.0,
            "premap_consumer_readonly_evicted_before_consume_count": 0,
            "premap_consumer_readonly_stale_handle_count": 0,
            "premap_consumer_readonly_handle_parity_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_attempted_count": 2,
            "premap_consumer_descriptor_prep_executed_count": 2,
            "premap_consumer_descriptor_prep_lookup_count": 20,
            "premap_consumer_descriptor_prep_handle_count": 20,
            "premap_consumer_descriptor_prep_missing_handle_count": 0,
            "premap_consumer_descriptor_prep_handle_hit_rate": 1.0,
            "premap_consumer_descriptor_prep_descriptor_ptr_count": 20,
            "premap_consumer_descriptor_prep_packed_weight_descriptor_count": 20,
            "premap_consumer_descriptor_prep_scale_metadata_handle_count": 20,
            "premap_consumer_descriptor_prep_real_handle_count": 20,
            "premap_consumer_descriptor_prep_real_handle_miss_count": 0,
            "premap_consumer_descriptor_prep_real_handle_hit_rate": 1.0,
            "premap_consumer_descriptor_prep_real_handle_backed_rate": 1.0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count": 2,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_count": 2,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_count": 2,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count": 20,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max": 4,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min": 4,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count": 0,
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_executed_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate": 0.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode": (
                "readonly_consume_kernel_arg_shadow_table"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source": (
                "canonical_address_key_order"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count": 80,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count": 60,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_optional_handle_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_lifecycle_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_lifecycle_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_parity_ok_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count": 80,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count": 60,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_optional_handle_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_read_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_packed_weight_descriptor_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_aux_metadata_handle_field_available_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_row_handle_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count": 0,
            "premap_consumer_prelaunch_boundary_checked_count": 2,
            "premap_consumer_prelaunch_boundary_aligned_count": 2,
            "premap_consumer_prelaunch_boundary_aligned_rate": 1.0,
            "premap_consumer_prelaunch_handle_available_count": 2,
            "premap_consumer_prelaunch_handle_available_rate": 1.0,
            "premap_consumer_prelaunch_block_count": 20,
            "premap_consumer_prelaunch_block_size_max": 16,
            "premap_consumer_prelaunch_unique_expert_count": 20,
            "premap_consumer_descriptor_prep_execution_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_execution_ok_attempted_rate": 1.0,
            "premap_consumer_descriptor_prep_blocked_count": 0,
            "premap_consumer_descriptor_prep_blocked_attempted_rate": 0.0,
            "premap_consumer_payload_violation_count": 0,
            "premap_consumer_router_change_violation_count": 0,
            "premap_consumer_descriptor_order_change_violation_count": 0,
            "premap_consumer_ready_credit_violation_count": 0,
            "premap_consumer_error_count": 0,
        },
    }


def test_premap_longrun_audit_gate_accepts_read_only_handle_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"]["premap_summary_count"] == 2


def test_premap_longrun_audit_gate_accepts_performance_summary_shape():
    summary = _passing_summary()
    performance_summary = {
        "generate_wall_seconds": 1.0,
        "runtime_shadow_aggregate": {
            **summary["aggregate"],
            "premap_summary_count": 2,
            "premap_consumer_mapping_count": 2,
        },
    }

    result = check_summary(
        performance_summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
        require_consumer_shim_prep_execution=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"]["row_count"] == 4
    assert result["metrics"]["premap_summary_count"] == 2
    assert result["metrics"]["premap_consumer_mapping_count"] == 2
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_rate"
        ]
        == 1.0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_ok_rate"
        ]
        == 1.0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
        ]
        == 80
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
        ]
        == 60
    )
    assert result["metrics"]["premap_consumer_prelaunch_boundary_checked_count"] == 2
    assert (
        result["metrics"]["premap_consumer_prelaunch_boundary_aligned_rate"]
        == 1.0
    )


def test_premap_longrun_audit_gate_allows_legacy_prep_without_prelaunch_requirement():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_prelaunch_"):
            summary["aggregate"].pop(key)

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
        require_consumer_shim_prep_execution=False,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_premap_longrun_audit_gate_rejects_missing_prelaunch_when_required():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_prelaunch_"):
            summary["aggregate"].pop(key)

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
        require_consumer_shim_prep_execution=True,
    )

    assert result["passed"] is False
    assert "prelaunch_boundary_fields_missing" in result["failures"]


def test_premap_longrun_audit_gate_rejects_prelaunch_unavailable():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate["premap_consumer_prelaunch_handle_available_count"] = 1
    aggregate["premap_consumer_prelaunch_handle_available_rate"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
        require_consumer_shim_prep_execution=True,
    )

    assert result["passed"] is False
    assert "prelaunch_handle_available_count_mismatch=1!=2" in result["failures"]


def test_premap_longrun_audit_gate_rejects_missing_prep_field_reads():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_handle_field_read_count"
    ] = 79
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_required_handle_field_available_count"
    ] = 59
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_descriptor_ptr_field_read_count"
    ] = 19
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_prep_execution_dry_run_scale_metadata_handle_field_available_count"
    ] = 19

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
        require_consumer_shim_prep_execution=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_prep_execution_handle_field_read_count_mismatch=79!=80"
        in result["failures"]
    )
    assert (
        "consumer_shim_prep_execution_required_handle_field_available_count_mismatch=59!=60"
        in result["failures"]
    )
    assert (
        "consumer_shim_prep_execution_descriptor_ptr_field_read_count_mismatch=19!=20"
        in result["failures"]
    )
    assert (
        "consumer_shim_prep_execution_scale_metadata_handle_field_available_count_mismatch=19!=20"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_accepts_descriptor_prep_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_descriptor_prep"] is True
    assert result["metrics"]["premap_consumer_descriptor_prep_attempted_count"] == 2


def test_premap_longrun_audit_gate_accepts_real_descriptor_prep_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_real_descriptor_prep"] is True
    assert result["metrics"]["premap_consumer_descriptor_prep_real_handle_count"] == 20
    assert (
        result["metrics"]["premap_consumer_descriptor_prep_real_handle_hit_rate"]
        == 1.0
    )


def test_premap_longrun_audit_gate_accepts_kernel_arg_shadow_table_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_kernel_arg_shadow_table"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
        ]
        == 20
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
        ]
        == 4
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
        ]
        == 4
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )


def test_premap_longrun_audit_gate_accepts_consumer_shim_table_read_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_consumer_shim_table_read"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
        ]
        == 20
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
        ]
        == 20
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
        ]
        == 4
    )


def test_premap_longrun_audit_gate_accepts_consumer_shim_table_consume_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_consumer_shim_table_consume"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
        ]
        == 20
    )
    assert result["metrics"][
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
    ] == "readonly_consume_kernel_arg_shadow_table"
    assert result["metrics"][
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
    ] == "canonical_address_key_order"
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
        ]
        == 80
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
        ]
        == 60
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_field_available_count"
        ]
        == 20
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count"
        ]
        == 20
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_rejects_missing_consume_field_reads():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_handle_field_read_count"
    ] = 79
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_required_handle_field_available_count"
    ] = 59
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_field_read_count"
    ] = 19
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_scale_metadata_handle_field_available_count"
    ] = 19

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_table_consume_handle_field_read_count_mismatch=79!=80"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_required_handle_field_available_count_mismatch=59!=60"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_descriptor_ptr_field_read_count_mismatch=19!=20"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_scale_metadata_handle_field_available_count_mismatch=19!=20"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_missing_consume_source_class_hits():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_descriptor_ptr_hit_count"
    ] = 19
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_packed_weight_descriptor_miss_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_aux_metadata_handle_hit_count"
    ] = 19

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_table_consume_descriptor_ptr_hit_count_mismatch=19!=20"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_packed_weight_descriptor_miss_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_aux_metadata_handle_hit_count_mismatch=19!=20"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_aux_metadata_handle_hit_miss_total_mismatch=19+0!=20"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_accepts_consumer_shim_table_object_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_consumer_shim_table_object"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_consumed_checked_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_object_row_count"
        ]
        == 20
    )


def test_premap_longrun_audit_gate_requires_consumer_shim_table_read_independently():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    for key in list(aggregate):
        if key.startswith("premap_consumer_descriptor_prep_consumer_shim"):
            del aggregate[key]

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
    )

    assert result["passed"] is False
    assert "consumer_shim_table_read_fields_missing" in result["failures"]


def test_premap_longrun_audit_gate_requires_consumer_shim_table_consume_independently():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    for key in list(aggregate):
        if "consumer_shim_handle_table_consume" in key:
            del aggregate[key]

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
    )

    assert result["passed"] is False
    assert "consumer_shim_table_consume_fields_missing" in result["failures"]


def test_premap_longrun_audit_gate_requires_consumer_shim_table_object_independently():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    for key in list(aggregate):
        if "consumer_shim_handle_table_object" in key:
            del aggregate[key]

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_consumer_shim_table_object=True,
    )

    assert result["passed"] is False
    assert "consumer_shim_table_object_fields_missing" in result["failures"]


def test_premap_longrun_audit_gate_does_not_auto_require_zero_consume_counters():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    for key in list(aggregate):
        if "consumer_shim_handle_table_consume" in key:
            value = aggregate[key]
            aggregate[key] = "" if isinstance(value, str) else 0

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=False,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"][
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
    ] == 0


def test_premap_longrun_audit_gate_requires_kernel_arg_shadow_table_independently():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    for key in list(aggregate):
        if key.startswith("premap_consumer_descriptor_prep"):
            del aggregate[key]

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_kernel_arg_shadow_table=True,
    )

    assert result["passed"] is False
    assert "kernel_arg_shadow_table_fields_missing" in result["failures"]
    assert "kernel_arg_shadow_table_requires_descriptor_prep_fields" in result["failures"]


def test_premap_longrun_audit_gate_rejects_descriptor_prep_instability():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_descriptor_prep_executed_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_missing_handle_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_handle_hit_rate"] = 0.95
    summary["aggregate"][
        "premap_consumer_descriptor_prep_execution_ok_attempted_rate"
    ] = 0.5
    summary["aggregate"]["premap_consumer_descriptor_prep_blocked_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_blocked_attempted_rate"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
    )

    assert result["passed"] is False
    assert "descriptor_prep_executed_count_mismatch=1!=2" in result["failures"]
    assert "descriptor_prep_missing_handle_count_nonzero=1" in result["failures"]
    assert "premap_consumer_descriptor_prep_handle_hit_rate_not_one" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_execution_ok_attempted_rate_not_one"
        in result["failures"]
    )
    assert "descriptor_prep_blocked_count_nonzero" in result["failures"]
    assert "descriptor_prep_blocked_attempted_rate_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_rejects_real_descriptor_prep_instability():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_count"] = 19
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_miss_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_hit_rate"] = 0.95
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_backed_rate"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
    )

    assert result["passed"] is False
    assert "descriptor_prep_real_handle_count_mismatch=19!=20" in result["failures"]
    assert "descriptor_prep_real_handle_miss_count_nonzero=1" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_real_handle_hit_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_real_handle_backed_rate_not_one"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_kernel_arg_shadow_table_instability():
    summary = _passing_summary()
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_executed_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate"
    ] = 0.5
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate"
    ] = 0.5
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_count"
    ] = 19
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_per_row_parity_ok_count"
    ] = 18
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_max"
    ] = 3
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_column_count_min"
    ] = 3
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash"
    ] = "bad-schema"
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_checked_count"
    ] = 0
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_missing_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_schema_hash_mismatch_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes"
    ] = 4
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
    )

    assert result["passed"] is False
    assert "kernel_arg_shadow_table_executed_count_mismatch=1!=2" in result["failures"]
    assert "kernel_arg_shadow_table_row_count_mismatch=19!=20" in result["failures"]
    assert "kernel_arg_shadow_table_parity_count_mismatch=18!=19" in result["failures"]
    assert "kernel_arg_shadow_table_column_count_max_mismatch=3!=4" in result["failures"]
    assert "kernel_arg_shadow_table_column_count_min_mismatch=3!=4" in result["failures"]
    assert "kernel_arg_shadow_table_schema_hash_mismatch" in result["failures"]
    assert (
        "kernel_arg_shadow_table_schema_hash_checked_count_mismatch=0!=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_"
        "schema_hash_missing_count_nonzero=1"
    ) in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_"
        "schema_hash_mismatch_count_nonzero=1"
    ) in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ok_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_lifecycle_ok_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_row_miss_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_stale_row_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_payload_bytes_nonzero=4"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_ready_credit_violation_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_router_change_violation_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_descriptor_order_change_violation_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_kernel_arg_violation_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_kernel_arg_shadow_table_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_consumer_shim_table_read_instability():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate["premap_consumer_descriptor_prep_consumer_shim_executed_count"] = 1
    aggregate["premap_consumer_descriptor_prep_consumer_shim_ok_rate"] = 0.5
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_not_checked_rate"
    ] = 0.5
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate"
    ] = 0.5
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate"
    ] = 0.5
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_per_row_parity_ok_count"
    ] = 19
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_count"
    ] = 18
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_column_count_max"
    ] = 3
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes"
    ] = 4
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
    )

    assert result["passed"] is False
    assert "consumer_shim_executed_count_mismatch=1!=2" in result["failures"]
    assert "consumer_shim_table_read_checked_count_mismatch=1!=1" not in result["failures"]
    assert "consumer_shim_table_read_not_checked_count_nonzero=1" in result["failures"]
    assert "consumer_shim_table_read_ok_count_mismatch=1!=1" not in result["failures"]
    assert (
        "consumer_shim_table_read_lifecycle_ok_count_mismatch=1!=1"
        not in result["failures"]
    )
    assert "consumer_shim_table_row_count_mismatch=18!=20" in result["failures"]
    assert "consumer_shim_table_column_count_max_mismatch=3!=4" in result["failures"]
    assert "consumer_shim_table_read_parity_count_mismatch=19!=18" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_ok_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_read_ok_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_lifecycle_ok_rate_not_one"
        in result["failures"]
    )
    assert "consumer_shim_table_read_not_checked_rate_nonzero" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_row_miss_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_stale_row_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_bytes_nonzero=4"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_payload_violation_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_violation_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_consumer_shim_table_consume_instability():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate"
    ] = 0.5
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate"
    ] = 0.5
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
    ] = 19
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_column_count_max"
    ] = 3
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash"
    ] = "bad-schema"
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_missing_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_schema_hash_mismatch_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode"
    ] = "bad-mode"
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_missing_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_mode_mismatch_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source"
    ] = "bad-source"
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_missing_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_source_mismatch_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_per_row_parity_ok_count"
    ] = 18
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes"
    ] = 4
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
    )

    assert result["passed"] is False
    assert "consumer_shim_table_consume_checked_count_mismatch=1!=2" in result["failures"]
    assert "consumer_shim_table_consume_ok_count_mismatch=1!=2" in result["failures"]
    assert (
        "consumer_shim_table_consume_lifecycle_ok_count_mismatch=1!=2"
        in result["failures"]
    )
    assert "consumer_shim_table_consume_row_count_mismatch=19!=20" in result["failures"]
    assert (
        "consumer_shim_table_consume_column_count_max_mismatch=3!=4"
        in result["failures"]
    )
    assert "consumer_shim_table_consume_schema_hash_mismatch" in result["failures"]
    assert (
        "consumer_shim_table_consume_schema_hash_checked_count_mismatch=1!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_schema_hash_missing_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_schema_hash_mismatch_count_nonzero=1"
        in result["failures"]
    )
    assert "consumer_shim_table_consume_mode_mismatch" in result["failures"]
    assert (
        "consumer_shim_table_consume_mode_checked_count_mismatch=1!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_mode_missing_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_mode_mismatch_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_source_checked_count_mismatch=1!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_source_missing_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_table_consume_source_mismatch_count_nonzero=1"
        in result["failures"]
    )
    assert "consumer_shim_table_consume_parity_count_mismatch=18!=19" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_ok_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_lifecycle_ok_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_miss_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_stale_row_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_bytes_nonzero=4"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_payload_violation_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_partial_descriptor_prep_coverage():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_descriptor_prep_attempted_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_executed_count"] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
    )

    assert result["passed"] is False
    assert "descriptor_prep_attempted_count_mismatch=1!=2" in result["failures"]


def test_premap_longrun_audit_gate_rejects_payload_and_mismatch():
    summary = _passing_summary()
    summary["event_counts"]["outcome_aggregate"] = 1
    summary["aggregate"]["premap_summary_payload_bytes"] = 128
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_binding_mismatch_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "unexpected_event_types=['outcome_aggregate']" in result["failures"]
    assert "premap_payload_bytes_nonzero" in result["failures"]
    assert "real_descriptor_handle_binding_mismatch_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_rejects_noop_contract_violations():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_payload_violation_count"] = 1
    summary["aggregate"]["premap_consumer_router_change_violation_count"] = 2
    summary["aggregate"]["premap_consumer_descriptor_order_change_violation_count"] = 3
    summary["aggregate"]["premap_consumer_ready_credit_violation_count"] = 4

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "premap_consumer_payload_violation_count_nonzero=1" in result["failures"]
    assert "premap_consumer_router_change_violation_count_nonzero=2" in result["failures"]
    assert (
        "premap_consumer_descriptor_order_change_violation_count_nonzero=3"
        in result["failures"]
    )
    assert "premap_consumer_ready_credit_violation_count_nonzero=4" in result["failures"]


def test_premap_longrun_audit_gate_rejects_capacity_and_reuse_regression():
    summary = _passing_summary()
    summary["aggregate"]["premap_address_resident_count_max"] = 13
    summary["aggregate"]["premap_address_reuse_rate_mean"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "resident_count_exceeds_capacity=13>12" in result["failures"]
    assert "premap_address_reuse_rate_below_threshold" in result["failures"]


def test_premap_longrun_audit_gate_rejects_real_handle_source_misses():
    summary = _passing_summary()
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_scale_metadata_hit_count"
    ] = 19
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_aux_metadata_miss_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_no_handle_parts_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert (
        "real_descriptor_handle_scale_metadata_hit_count_mismatch=19!=20"
        in result["failures"]
    )
    assert "real_descriptor_handle_aux_metadata_miss_count_nonzero=1" not in result["failures"]
    assert "real_descriptor_handle_no_handle_parts_count_nonzero=1" in result["failures"]


def test_premap_longrun_audit_gate_rejects_readonly_consumer_instability():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_readonly_handle_hit_rate"] = 0.95
    summary["aggregate"]["premap_consumer_readonly_evicted_before_consume_count"] = 1
    summary["aggregate"]["premap_consumer_readonly_stale_handle_count"] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "premap_consumer_readonly_handle_hit_rate_not_one" in result["failures"]
    assert "readonly_evicted_before_consume_nonzero" in result["failures"]
    assert "readonly_stale_handle_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_allows_legacy_summary_without_readonly_requirement():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_readonly_"):
            summary["aggregate"].pop(key)

    result = check_summary(summary, max_capacity=12, min_reuse_rate=0.98)

    assert result["passed"] is True
    assert result["require_readonly_consumer"] is False


def test_premap_longrun_audit_gate_rejects_missing_readonly_when_required():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_readonly_"):
            summary["aggregate"].pop(key)

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "readonly_consumer_fields_missing" in result["failures"]


def test_premap_longrun_audit_gate_allows_zero_descriptor_prep_placeholders_without_requirement():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_descriptor_prep_"):
            summary["aggregate"][key] = 0

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=False,
    )

    assert result["passed"] is True
    assert result["require_descriptor_prep"] is False
