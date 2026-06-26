import pytest

from scripts.check_premap_prelaunch_pointer_source_observer import (
    EXPECTED_TRUE_BOOL_KEYS,
    REQUIRED_BOOL_KEYS,
    REQUIRED_INT_KEYS,
    ZERO_INT_KEYS,
    check_premap_prelaunch_pointer_source_observer,
)


def _payload(**overrides):
    payload = {key: False for key in REQUIRED_BOOL_KEYS}
    payload.update({key: 0 for key in REQUIRED_INT_KEYS})
    payload.update(
        {
            "sample_count": 16,
            "requested_output_token_count": 1024,
            "runtime_shadow_premap_live_config_without_router_recorder_enabled": True,
            "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_prelaunch_pointer_source_canary_enabled": True,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_seen_count": 16,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count": 16,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count": 16,
        }
    )
    payload.update(overrides)
    return payload


def test_prelaunch_pointer_source_observer_check_accepts_noop_device_evidence():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(),
        min_seen=8,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["observer_seen"] == 16
    assert result["observer_vllm_device"] == 16
    assert (
        result["zero_counter_values"][
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count"
        ]
        == 0
    )
    assert all(result["zero_counter_values"][key] == 0 for key in ZERO_INT_KEYS)


def test_prelaunch_pointer_source_observer_check_rejects_live_handoff():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(
            runtime_shadow_premap_kernel_arg_handoff_live_enabled=True,
            runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count=1,
        )
    )

    assert result["passed"] is False
    assert "live_handoff_enabled" in result["failures"]
    assert (
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count:nonzero"
        in result["failures"]
    )


@pytest.mark.parametrize(
    "flag",
    [key for key in REQUIRED_BOOL_KEYS if key not in EXPECTED_TRUE_BOOL_KEYS],
)
def test_prelaunch_pointer_source_observer_check_rejects_any_noop_flag_true(flag):
    result = check_premap_prelaunch_pointer_source_observer(_payload(**{flag: True}))

    assert result["passed"] is False
    assert f"{flag}:true" in result["failures"]


@pytest.mark.parametrize("flag", sorted(EXPECTED_TRUE_BOOL_KEYS))
def test_prelaunch_pointer_source_observer_check_rejects_required_true_flag_false(flag):
    result = check_premap_prelaunch_pointer_source_observer(_payload(**{flag: False}))

    assert result["passed"] is False
    assert f"{flag}:not_true" in result["failures"]


def test_prelaunch_pointer_source_observer_check_rejects_non_device_evidence():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(
            runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_available_count=0,
            runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_unavailable_count=16,
            runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_vllm_device_count=0,
            runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_prelaunch_current_expert_ptr_observer_non_device_count=16,
        )
    )

    assert result["passed"] is False
    assert "observer_available_mismatch" in result["failures"]
    assert "observer_vllm_device_mismatch" in result["failures"]
    assert "observer_unavailable_nonzero" in result["failures"]
    assert "observer_non_device_nonzero" in result["failures"]


def test_prelaunch_pointer_source_observer_check_rejects_missing_required_key():
    payload = _payload()
    del payload[
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled"
    ]
    result = check_premap_prelaunch_pointer_source_observer(payload)

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled:missing"
        in result["failures"]
    )


def test_prelaunch_pointer_source_observer_check_rejects_wrong_bool_type():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled=0)
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled:not_bool"
        in result["failures"]
    )


def test_prelaunch_pointer_source_observer_check_rejects_wrong_int_type():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(sample_count=True)
    )

    assert result["passed"] is False
    assert "sample_count:not_int" in result["failures"]


def test_prelaunch_pointer_source_observer_check_rejects_extra_live_mutation_nonzero():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(
            runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_native_row_fill_count=1
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_native_row_fill_count:nonzero"
        in result["failures"]
    )


def test_prelaunch_pointer_source_observer_check_rejects_extra_live_mutation_type():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(
            runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_native_row_fill_count=False
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_live_mutation_future_wna16_typed_slot_native_row_fill_count:not_int"
        in result["failures"]
    )


def test_prelaunch_pointer_source_observer_check_rejects_extra_handoff_bool_true():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(
            runtime_shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled=True
        )
    )

    assert result["passed"] is False
    assert (
        "runtime_shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled:true"
        in result["failures"]
    )


def test_prelaunch_pointer_source_observer_check_ignores_extra_handoff_non_bool_config():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(
            runtime_shadow_premap_kernel_arg_handoff_minimal_identity_envelope_enabled=0
        )
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_prelaunch_pointer_source_observer_check_rejects_kernel_arg_pass():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled=True)
    )

    assert result["passed"] is False
    assert "kernel_arg_pass_enabled" in result["failures"]


def test_prelaunch_pointer_source_observer_check_rejects_min_sample_count():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(sample_count=1),
        min_sample_count=16,
    )

    assert result["passed"] is False
    assert "sample_count_below_min" in result["failures"]


def test_prelaunch_pointer_source_observer_check_rejects_min_output_tokens():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(requested_output_token_count=64),
        min_requested_output_tokens=1024,
    )

    assert result["passed"] is False
    assert "requested_output_token_count_below_min" in result["failures"]


def test_prelaunch_pointer_source_observer_check_rejects_trace_mode_mismatch():
    result = check_premap_prelaunch_pointer_source_observer(
        _payload(mode="unexpected_mode"),
        expected_trace_mode="expected_mode",
    )

    assert result["passed"] is False
    assert "trace_mode_mismatch" in result["failures"]
