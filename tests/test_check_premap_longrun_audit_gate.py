from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME,
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
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode": (
                "readonly_kernel_arg_handoff_dry_run"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count": 60,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_ready_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode": (
                "readonly_kernel_arg_handoff_shadow_slot"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_column_count_min": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_hit_count": 60,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_required_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_optional_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_shadow_slot_kernel_arg_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_ready_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_slot_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode": (
                "readonly_kernel_arg_handoff_mirror"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_column_count_min": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_hit_count": 60,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_required_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_hit_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_optional_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_mirror_kernel_arg_violation_count": 0,
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


def _add_kernel_arg_handoff_attempt(summary: dict) -> dict:
    aggregate = summary["aggregate"]
    aggregate.update(
        {
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_slot_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode": "readonly_kernel_arg_handoff_attempt",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason": "kernel_arg_handoff_disabled_noop_gate",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_block_reason_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_mirror_ready_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count": 20,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_column_count_min": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_checked_count": 2,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_kernel_arg_violation_count": 0,
        }
    )
    return summary


def _add_kernel_arg_handoff_launch_schema_mirror(summary: dict) -> dict:
    aggregate = summary["aggregate"]
    checked_count = int(
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_executed_count"
        ]
    )
    row_count = int(
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_handle_table_consume_row_count"
        ]
    )
    aggregate.update(
        {
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_slot_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode": "readonly_kernel_arg_handoff_launch_schema_mirror",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_row_count": row_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_max": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_column_count_min": 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash": (
                PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_table_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name": (
                PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash": (
                PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count": (
                checked_count * len(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS)
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_hit_count": row_count * 3,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_required_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count": row_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_handle_field_read_count": row_count * 4,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_kernel_arg_violation_count": 0,
        }
    )
    return summary


def _add_kernel_arg_handoff_live_toggle(
    summary: dict,
    *,
    enabled_blocked: bool = False,
) -> dict:
    aggregate = summary["aggregate"]
    checked_count = int(
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_executed_count"
        ]
    )
    aggregate.update(
        {
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_table_object_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode": "readonly_kernel_arg_handoff_live_toggle",
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason": (
                "kernel_arg_handoff_kernel_consumer_not_connected"
                if enabled_blocked
                else "kernel_arg_handoff_live_disabled"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count": (
                checked_count if enabled_blocked else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_lab_gate_passed_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_attempt_record_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count": (
                checked_count if enabled_blocked else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_blocked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_kernel_arg_violation_count": 0,
        }
    )
    return summary


def _add_kernel_arg_handoff_live_noop_integration(
    summary: dict,
    *,
    enabled_blocked: bool = False,
    consumer_connected: bool = False,
) -> dict:
    aggregate = summary["aggregate"]
    checked_count = int(
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_executed_count"
        ]
    )
    aggregate.update(
        {
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_table_object_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode": (
                "readonly_kernel_arg_handoff_live_noop_integration"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason": (
                "kernel_arg_handoff_kernel_arg_pass_disabled"
                if enabled_blocked and consumer_connected
                else (
                    "kernel_arg_handoff_kernel_consumer_not_connected"
                    if enabled_blocked
                    else "kernel_arg_handoff_live_disabled"
                )
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count": (
                checked_count if enabled_blocked else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_lab_gate_passed_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_toggle_record_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_live_eligible_count": (
                checked_count if enabled_blocked else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count": (
                checked_count if consumer_connected else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_blocked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_kernel_arg_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count": 0,
        }
    )
    return summary


def _add_kernel_arg_handoff_live_consumer_adapter(
    summary: dict,
    *,
    enabled_blocked: bool = False,
    consumer_connected: bool = False,
    kernel_arg_pass_live: bool = False,
    real_kernel_arg_mutation_live: bool = False,
    single_field_replacement_dry_run: bool = False,
    single_field_replacement_live: bool = False,
) -> dict:
    aggregate = summary["aggregate"]
    checked_count = int(
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_executed_count"
        ]
    )
    block_reason = (
        (
            (
                "kernel_arg_handoff_real_kernel_arg_mutation_live"
                if real_kernel_arg_mutation_live
                else "kernel_arg_handoff_kernel_arg_pass_live"
            )
            if kernel_arg_pass_live
            else "kernel_arg_handoff_kernel_arg_pass_disabled"
        )
        if enabled_blocked and consumer_connected
        else
        "kernel_arg_handoff_kernel_consumer_not_connected"
        if enabled_blocked
        else "kernel_arg_handoff_live_disabled"
    )
    live_noop_block_reason = (
        "kernel_arg_handoff_kernel_arg_pass_disabled"
        if enabled_blocked and consumer_connected
        else
        "kernel_arg_handoff_kernel_consumer_not_connected"
        if enabled_blocked
        else "kernel_arg_handoff_live_disabled"
    )
    aggregate.update(
        {
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_table_object_hash_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode": (
                "readonly_kernel_arg_handoff_live_consumer_adapter"
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_mode_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason": block_reason,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason": live_noop_block_reason,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_checked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_missing_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason_mismatch_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count": (
                checked_count if enabled_blocked else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_lab_gate_passed_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count": checked_count,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count": (
                checked_count if consumer_connected else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count": (
                checked_count if enabled_blocked else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count": (
                0 if kernel_arg_pass_live else checked_count
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_violation_count": 0,
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count": (
                checked_count if kernel_arg_pass_live else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_kernel_arg_violation_count": (
                checked_count if kernel_arg_pass_live else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count": (
                checked_count if kernel_arg_pass_live else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count": (
                checked_count if kernel_arg_pass_live else 0
            ),
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count": 0,
        }
    )
    if real_kernel_arg_mutation_live:
        aggregate[
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count"
        ] = checked_count
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count"
        ] = checked_count
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count"
        ] = checked_count
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_package_missing_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_package_layer_mismatch_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_package_block_reason_mismatch_count"
        ] = 0
    if kernel_arg_pass_live:
        aggregate[
            "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
        ] = True
    if real_kernel_arg_mutation_live:
        aggregate[
            "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled"
        ] = True
    if single_field_replacement_dry_run:
        aggregate[
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"
        ] = True
        aggregate[
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled"
        ] = bool(single_field_replacement_live)
        aggregate[
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field"
        ] = "B_scale"
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_candidate_count"
        ] = checked_count
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_ok_count"
        ] = checked_count
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_mismatch_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_source_missing_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_unsupported_field_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_disabled_count"
        ] = 0 if single_field_replacement_live else checked_count
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_candidate_count"
        ] = checked_count if single_field_replacement_live else 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_replaced_count"
        ] = checked_count if single_field_replacement_live else 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_ok_count"
        ] = checked_count if single_field_replacement_live else 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_mismatch_count"
        ] = 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count"
        ] = checked_count if single_field_replacement_live else 0
        aggregate[
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes"
        ] = 0
    return summary


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


def test_premap_longrun_audit_gate_rejects_kernel_arg_pass_enabled_summary():
    summary = _passing_summary()
    performance_summary = {
        "generate_wall_seconds": 1.0,
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled": True,
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
    )

    assert result["passed"] is False
    assert "kernel_arg_handoff_kernel_arg_pass_enabled_true" in result["failures"]


def test_premap_longrun_audit_gate_rejects_kernel_arg_pass_enabled_aggregate():
    summary = _passing_summary()
    summary["aggregate"][
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    ] = True

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "kernel_arg_handoff_kernel_arg_pass_enabled_true" in result["failures"]


def test_premap_longrun_audit_gate_accepts_gate_report_shape():
    summary = _add_kernel_arg_handoff_launch_schema_mirror(
        _add_kernel_arg_handoff_live_toggle(
            _add_kernel_arg_handoff_attempt(_passing_summary())
        )
    )
    gate_report = check_summary(
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )

    result = check_summary(
        gate_report,
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )

    assert gate_report["passed"] is True
    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"]["row_count"] == 4
    assert result["metrics"]["premap_summary_count"] == 2
    assert result["metrics"]["premap_consumer_mapping_count"] == 2
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count"
        ]
        == 2 * len(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS)
    )


def test_premap_longrun_audit_gate_does_not_backfill_failed_gate_report():
    summary = _add_kernel_arg_handoff_launch_schema_mirror(
        _add_kernel_arg_handoff_live_toggle(
            _add_kernel_arg_handoff_attempt(_passing_summary())
        )
    )
    gate_report = check_summary(
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )
    gate_report["passed"] = False
    gate_report["failures"] = []

    result = check_summary(
        gate_report,
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )

    assert result["passed"] is False
    assert (
        "descriptor_prep_handle_count_mismatch=0!=20"
        in result["failures"]
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
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count"
        ]
        == 2
    )
    assert result["metrics"][
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_mode"
    ] == "readonly_kernel_arg_handoff_dry_run"
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count"
        ]
        == 60
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
        ]
        == 4
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_min"
        ]
        == 4
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
        ]
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_kernel_arg_handoff_attempt_contract():
    result = check_summary(
        _add_kernel_arg_handoff_attempt(_passing_summary()),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_kernel_arg_handoff_attempt"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_record_ready_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_kernel_arg_launch_schema_mirror_contract():
    result = check_summary(
        _add_kernel_arg_handoff_launch_schema_mirror(
            _add_kernel_arg_handoff_attempt(_passing_summary())
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_kernel_arg_handoff_launch_schema_mirror"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_ready_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_name"
        ]
        == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash"
        ]
        == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count"
        ]
        == 2 * len(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS)
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_requires_kernel_arg_launch_schema_mirror_explicitly():
    result = check_summary(
        _add_kernel_arg_handoff_attempt(_passing_summary()),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_checked_count_mismatch=0!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_mode_mismatch"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_ignores_zeroed_launch_schema_mirror_defaults():
    summary = _add_kernel_arg_handoff_attempt(_passing_summary())
    aggregate = summary["aggregate"]
    prefix = (
        "premap_consumer_descriptor_prep_consumer_shim_"
        "kernel_arg_handoff_launch_schema_mirror_"
    )
    aggregate.update(
        {
            f"{prefix}checked_count": 0,
            f"{prefix}ready_count": 0,
            f"{prefix}mode": "",
            f"{prefix}launch_schema_name": "",
            f"{prefix}launch_schema_hash": "",
            f"{prefix}launch_arg_field_count": 0,
        }
    )

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

    assert result["passed"] is True
    assert result["failures"] == []


def test_premap_longrun_audit_gate_rejects_kernel_arg_launch_schema_mirror_schema_drift():
    summary = _add_kernel_arg_handoff_launch_schema_mirror(
        _add_kernel_arg_handoff_attempt(_passing_summary())
    )
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count"
    ] -= 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash"
    ] = "bad-launch-schema-hash"
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count"
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
        require_kernel_arg_handoff_launch_schema_mirror=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count_mismatch="
        in "\n".join(result["failures"])
    )
    assert (
        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_launch_schema_hash_mismatch"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_launch_schema_mirror_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_requires_kernel_arg_handoff_attempt_explicitly():
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
        require_kernel_arg_handoff_attempt=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_attempt_fields_missing"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_kernel_arg_handoff_attempt_unblocked():
    summary = _add_kernel_arg_handoff_attempt(_passing_summary())
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_blocked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count"
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
        require_kernel_arg_handoff_attempt=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_attempt_gate_allowed_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_attempt_blocked_count_mismatch=1!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_attempt_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_partial_kernel_arg_handoff_attempt_fields():
    summary = _passing_summary()
    summary["aggregate"][
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_attempt_row_count"
    ] = 20

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
        "consumer_shim_kernel_arg_handoff_attempt_checked_count_mismatch=0!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_attempt_mode_mismatch"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_accepts_default_disabled_live_toggle():
    result = check_summary(
        _add_kernel_arg_handoff_live_toggle(
            _add_kernel_arg_handoff_attempt(_passing_summary())
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_kernel_arg_handoff_live_toggle"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_record_ready_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )


def test_premap_longrun_audit_gate_rejects_enabled_live_toggle_for_default_gate():
    summary = _add_kernel_arg_handoff_live_toggle(
        _add_kernel_arg_handoff_attempt(_passing_summary())
    )
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_live_toggle_enabled_count_mismatch=1!=0"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count_mismatch=1!=0"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_accepts_enabled_blocked_live_toggle_canary():
    result = check_summary(
        _add_kernel_arg_handoff_live_toggle(
            _add_kernel_arg_handoff_attempt(_passing_summary()),
            enabled_blocked=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        allow_enabled_blocked_live_toggle=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["allow_enabled_blocked_live_toggle"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_enabled_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_live_eligible_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
        ]
        == "kernel_arg_handoff_kernel_consumer_not_connected"
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_default_disabled_live_noop_integration():
    result = check_summary(
        _add_kernel_arg_handoff_live_noop_integration(
            _add_kernel_arg_handoff_live_toggle(
                _add_kernel_arg_handoff_launch_schema_mirror(
                    _add_kernel_arg_handoff_attempt(_passing_summary())
                )
            )
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_kernel_arg_handoff_live_noop_integration"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_record_ready_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_enabled_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_launch_schema_ready_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_block_reason"
        ]
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        check_summary(
            result,
            max_capacity=12,
            min_reuse_rate=0.98,
            require_readonly_consumer=True,
            require_descriptor_prep=True,
            require_real_descriptor_prep=True,
            require_kernel_arg_shadow_table=True,
            require_consumer_shim_table_read=True,
            require_consumer_shim_table_consume=True,
            require_kernel_arg_handoff_attempt=True,
            require_kernel_arg_handoff_live_toggle=True,
            require_kernel_arg_handoff_launch_schema_mirror=True,
            require_kernel_arg_handoff_live_noop_integration=True,
        )["passed"]
        is True
    )


def test_premap_longrun_audit_gate_backfills_live_noop_changes_for_old_artifact():
    summary = _add_kernel_arg_handoff_live_noop_integration(
        _add_kernel_arg_handoff_live_toggle(
            _add_kernel_arg_handoff_launch_schema_mirror(
                _add_kernel_arg_handoff_attempt(_passing_summary())
            )
        )
    )
    summary["aggregate"].pop(
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
    )

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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
    )

    assert result["passed"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_backfills_live_noop_changes_for_old_gate_report():
    result = check_summary(
        _add_kernel_arg_handoff_live_noop_integration(
            _add_kernel_arg_handoff_live_toggle(
                _add_kernel_arg_handoff_launch_schema_mirror(
                    _add_kernel_arg_handoff_attempt(_passing_summary())
                )
            )
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
    )
    result["metrics"].pop(
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
    )

    rechecked = check_summary(
        result,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
    )

    assert rechecked["passed"] is True
    assert (
        rechecked["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_default_disabled_live_consumer_adapter():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    )
                )
            )
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_kernel_arg_handoff_live_consumer_adapter"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_record_ready_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_payload_bytes"
        ]
        == 0
    )
    assert (
        check_summary(
            result,
            max_capacity=12,
            min_reuse_rate=0.98,
            require_readonly_consumer=True,
            require_descriptor_prep=True,
            require_real_descriptor_prep=True,
            require_kernel_arg_shadow_table=True,
            require_consumer_shim_table_read=True,
            require_consumer_shim_table_consume=True,
            require_kernel_arg_handoff_attempt=True,
            require_kernel_arg_handoff_live_toggle=True,
            require_kernel_arg_handoff_launch_schema_mirror=True,
            require_kernel_arg_handoff_live_noop_integration=True,
            require_kernel_arg_handoff_live_consumer_adapter=True,
        )["passed"]
        is True
    )


def test_premap_longrun_audit_gate_backfills_live_consumer_adapter_changes_for_old_gate_report():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    )
                )
            )
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
    )
    result["metrics"].pop(
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
    )

    rechecked = check_summary(
        result,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
    )

    assert rechecked["passed"] is True
    assert (
        rechecked["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_rejects_live_consumer_adapter_kernel_handoff():
    summary = _add_kernel_arg_handoff_live_consumer_adapter(
        _add_kernel_arg_handoff_live_noop_integration(
            _add_kernel_arg_handoff_live_toggle(
                _add_kernel_arg_handoff_launch_schema_mirror(
                    _add_kernel_arg_handoff_attempt(_passing_summary())
                )
            )
        )
    )
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count_mismatch=1!=0"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count_mismatch=1!=0"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count_mismatch=1!=0"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_accepts_enabled_blocked_live_consumer_adapter_canary():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
            ),
            enabled_blocked=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
    )

    assert result["passed"] is True
    assert result["allow_enabled_blocked_live_toggle"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_enabled_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_live_eligible_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_connected_blocked_live_consumer_adapter_canary():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
    )

    assert result["passed"] is True
    assert result["allow_connected_blocked_consumer_adapter"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_consumer_connected_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
        ]
        == "kernel_arg_handoff_kernel_arg_pass_disabled"
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_live_kernel_arg_pass_with_explicit_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
    )

    assert result["passed"] is True
    assert result["allow_kernel_arg_handoff_live_kernel_arg_pass"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
        ]
        == "kernel_arg_handoff_kernel_arg_pass_live"
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_blocked_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_contract_live_pass_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_accepts_real_kernel_arg_mutation_with_explicit_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
            real_kernel_arg_mutation_live=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=True,
    )

    assert result["passed"] is True
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_block_reason"
        ]
        == "kernel_arg_handoff_real_kernel_arg_mutation_live"
    )
    assert (
        result["metrics"][
            "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count"
        ]
        == 2
    )


def test_premap_longrun_audit_gate_accepts_single_field_replacement_dry_run():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
            real_kernel_arg_mutation_live=True,
            single_field_replacement_dry_run=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=True,
    )

    assert result["passed"] is True
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled"
        ]
        is True
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field"
        ]
        == "B_scale"
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_candidate_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_ok_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count"
        ]
        == 0
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled"
        ]
        is False
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_disabled_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count"
        ]
        == 0
    )


def test_premap_longrun_audit_gate_rejects_single_field_live_without_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
            real_kernel_arg_mutation_live=True,
            single_field_replacement_dry_run=True,
            single_field_replacement_live=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=True,
    )

    assert result["passed"] is False
    assert "single_field_replacement_live_enabled_true" in result["failures"]


def test_premap_longrun_audit_gate_accepts_single_field_live_with_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
            real_kernel_arg_mutation_live=True,
            single_field_replacement_dry_run=True,
            single_field_replacement_live=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=True,
        allow_single_field_replacement_live=True,
    )

    assert result["passed"] is True
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_candidate_count"
        ]
        == 2
    )
    assert (
        result["metrics"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count"
        ]
        == 2
    )


def test_premap_longrun_audit_gate_rejects_single_field_live_without_dry_run():
    summary = _add_kernel_arg_handoff_live_consumer_adapter(
        _add_kernel_arg_handoff_live_noop_integration(
            _add_kernel_arg_handoff_live_toggle(
                _add_kernel_arg_handoff_launch_schema_mirror(
                    _add_kernel_arg_handoff_attempt(_passing_summary())
                ),
                enabled_blocked=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
        ),
        enabled_blocked=True,
        consumer_connected=True,
        kernel_arg_pass_live=True,
        real_kernel_arg_mutation_live=True,
    )
    summary["aggregate"][
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled"
    ] = True

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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=True,
        allow_single_field_replacement_live=True,
    )

    assert result["passed"] is False
    assert (
        "single_field_replacement_live_requires_dry_run_enabled"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_live_counters_when_live_disabled():
    summary = _passing_summary()
    summary["aggregate"][
        "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled"
    ] = False
    summary["aggregate"][
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_replaced_count"
    ] = 1

    result = check_summary(summary, max_capacity=12, min_reuse_rate=0.98)

    assert result["passed"] is False
    assert (
        "single_field_replacement_live_replaced_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_single_field_replacement_mismatch():
    summary = _add_kernel_arg_handoff_live_consumer_adapter(
        _add_kernel_arg_handoff_live_noop_integration(
            _add_kernel_arg_handoff_live_toggle(
                _add_kernel_arg_handoff_launch_schema_mirror(
                    _add_kernel_arg_handoff_attempt(_passing_summary())
                ),
                enabled_blocked=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
        ),
        enabled_blocked=True,
        consumer_connected=True,
        kernel_arg_pass_live=True,
        real_kernel_arg_mutation_live=True,
        single_field_replacement_dry_run=True,
    )
    summary["aggregate"][
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_mismatch_count"
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
        allow_kernel_arg_handoff_live_real_kernel_arg_mutation=True,
    )

    assert result["passed"] is False
    assert (
        "single_field_replacement_dry_run_parity_mismatch_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_real_kernel_arg_mutation_without_explicit_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
            real_kernel_arg_mutation_live=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
    )

    assert result["passed"] is False
    assert (
        "kernel_arg_handoff_real_kernel_arg_mutation_enabled_true"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_allow_kernel_arg_pass_without_runtime_flag():
    summary = _add_kernel_arg_handoff_live_consumer_adapter(
        _add_kernel_arg_handoff_live_noop_integration(
            _add_kernel_arg_handoff_live_toggle(
                _add_kernel_arg_handoff_launch_schema_mirror(
                    _add_kernel_arg_handoff_attempt(_passing_summary())
                ),
                enabled_blocked=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
        ),
        enabled_blocked=True,
        consumer_connected=True,
        kernel_arg_pass_live=True,
    )
    summary["aggregate"].pop(
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    )

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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
        allow_kernel_arg_handoff_live_kernel_arg_pass=True,
    )

    assert result["passed"] is False
    assert (
        "allow_kernel_arg_handoff_live_kernel_arg_pass_requires_runtime_flag_true"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_live_kernel_arg_pass_without_explicit_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
            kernel_arg_pass_live=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_enabled_blocked_live_toggle=True,
        allow_connected_blocked_consumer_adapter=True,
    )

    assert result["passed"] is False
    assert "kernel_arg_handoff_kernel_arg_pass_enabled_true" in result["failures"]
    assert any(
        failure.startswith(
            "consumer_shim_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_count_mismatch="
        )
        for failure in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_connected_adapter_allow_without_live_allow():
    result = check_summary(
        _add_kernel_arg_handoff_live_consumer_adapter(
            _add_kernel_arg_handoff_live_noop_integration(
                _add_kernel_arg_handoff_live_toggle(
                    _add_kernel_arg_handoff_launch_schema_mirror(
                        _add_kernel_arg_handoff_attempt(_passing_summary())
                    ),
                    enabled_blocked=True,
                ),
                enabled_blocked=True,
                consumer_connected=True,
            ),
            enabled_blocked=True,
            consumer_connected=True,
        ),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
        require_kernel_arg_shadow_table=True,
        require_consumer_shim_table_read=True,
        require_consumer_shim_table_consume=True,
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
        require_kernel_arg_handoff_live_consumer_adapter=True,
        allow_connected_blocked_consumer_adapter=True,
    )

    assert result["passed"] is False
    assert (
        "allow_connected_blocked_consumer_adapter_requires_allow_enabled_blocked_live_toggle"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_live_noop_kernel_handoff():
    summary = _add_kernel_arg_handoff_live_noop_integration(
        _add_kernel_arg_handoff_live_toggle(
            _add_kernel_arg_handoff_launch_schema_mirror(
                _add_kernel_arg_handoff_attempt(_passing_summary())
            )
        )
    )
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count"
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        require_kernel_arg_handoff_launch_schema_mirror=True,
        require_kernel_arg_handoff_live_noop_integration=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_live_noop_integration_consumer_connected_count_mismatch=1!=0"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_live_noop_integration_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_enabled_blocked_canary_kernel_handoff():
    summary = _add_kernel_arg_handoff_live_toggle(
        _add_kernel_arg_handoff_attempt(_passing_summary()),
        enabled_blocked=True,
    )
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count"
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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        allow_enabled_blocked_live_toggle=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_live_toggle_passed_to_kernel_count_nonzero=1"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_enabled_blocked_canary_wrong_reason():
    summary = _add_kernel_arg_handoff_live_toggle(
        _add_kernel_arg_handoff_attempt(_passing_summary()),
        enabled_blocked=True,
    )
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_live_toggle_block_reason"
    ] = "kernel_arg_handoff_live_disabled"

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
        require_kernel_arg_handoff_attempt=True,
        require_kernel_arg_handoff_live_toggle=True,
        allow_enabled_blocked_live_toggle=True,
    )

    assert result["passed"] is False
    assert (
        "consumer_shim_kernel_arg_handoff_live_toggle_block_reason_mismatch"
        in result["failures"]
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


def test_premap_longrun_audit_gate_rejects_kernel_arg_handoff_dry_run_instability():
    summary = _passing_summary()
    aggregate = summary["aggregate"]
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_ready_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count"
    ] = 59
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_column_count_max"
    ] = 3
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash"
    ] = "bad-schema"
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count"
    ] = 1
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_optional_source_hit_count"
    ] = 19
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_payload_bytes"
    ] = 4
    aggregate[
        "premap_consumer_descriptor_prep_consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count"
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
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_ready_count_mismatch=1!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_required_source_hit_count_mismatch=59!=60"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_column_count_max_mismatch=3!=4"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_mismatch"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_checked_count_mismatch=1!=2"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_schema_hash_missing_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_required_source_miss_count_nonzero=1"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_optional_source_total_mismatch=19+0!=20"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_payload_bytes_nonzero=4"
        in result["failures"]
    )
    assert (
        "consumer_shim_kernel_arg_handoff_dry_run_passed_to_kernel_count_nonzero=1"
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
