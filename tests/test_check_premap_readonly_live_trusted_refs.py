from scripts.check_premap_readonly_live_trusted_refs import (
    EXPECTED_TRUE_BOOL_KEYS,
    REQUIRED_FALSE_BOOL_KEYS,
    REQUIRED_INT_KEYS,
    check_premap_readonly_live_trusted_refs,
)


def _payload(**overrides):
    payload = {key: False for key in EXPECTED_TRUE_BOOL_KEYS | REQUIRED_FALSE_BOOL_KEYS}
    payload.update({key: 0 for key in REQUIRED_INT_KEYS})
    payload.update(
        {
            "sample_count": 1,
            "requested_output_token_count": 4,
            "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_validation_mode": "trusted_refs",
            "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_candidate_source": "original_kernel_arg_identity",
            "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
        }
    )
    for key in EXPECTED_TRUE_BOOL_KEYS:
        payload[key] = True
    producer_count = 160
    package_count = 320
    payload.update(
        {
            "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_seen_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_available_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_seen_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_available_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_vllm_device_count": package_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_seen_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_available_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_vllm_device_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_attached_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_attached_count": producer_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_attached_count": producer_count,
        }
    )
    payload.update(overrides)
    return payload


def test_readonly_live_trusted_refs_check_accepts_pass_through_package():
    result = check_premap_readonly_live_trusted_refs(
        _payload(),
        min_package_seen=16,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["package_seen"] == 320
    assert result["trusted_refs_available"] == 320
    assert result["observer_vllm_device"] == 160


def test_readonly_live_trusted_refs_check_rejects_kernel_arg_pass():
    result = check_premap_readonly_live_trusted_refs(
        _payload(
            runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled=True,
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled:true"
        in result["failures"]
    )


def test_readonly_live_trusted_refs_check_rejects_single_field_kernel_pass_counter():
    result = check_premap_readonly_live_trusted_refs(
        _payload(
            runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count=1,
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count:nonzero"
        in result["failures"]
    )


def test_readonly_live_trusted_refs_check_rejects_future_kernel_variant_launch():
    result = check_premap_readonly_live_trusted_refs(
        _payload(
            runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_kernel_variant_launch_count=1,
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_kernel_variant_launch_count:nonzero"
        in result["failures"]
    )


def test_readonly_live_trusted_refs_check_rejects_trusted_refs_mismatch():
    result = check_premap_readonly_live_trusted_refs(
        _payload(
            runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_ready_source_mismatch_count=1,
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_trusted_refs_prelaunch_current_expert_ptr_ready_source_mismatch_count:nonzero"
        in result["failures"]
    )
    assert "trusted_ptr_ready_source_mismatch_nonzero" in result["failures"]


def test_readonly_live_trusted_refs_check_rejects_wrong_validation_mode():
    result = check_premap_readonly_live_trusted_refs(
        _payload(
            runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_validation_mode="identity",
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_validation_mode:expected_trusted_refs"
        in result["failures"]
    )
