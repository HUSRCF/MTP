from __future__ import annotations

from dataclasses import replace

import pytest
import torch

from mtp_expert_prefetch.runtime import (
    ControlledPremapAddressManager,
    ExpertPrefetchDescriptor,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH,
    PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME,
    PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
    PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
    PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_SCHEMA_HASH,
    PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_SCHEMA_NAME,
    PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_NATIVE_ABI_FIELDS,
    PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_NATIVE_ABI_HASH,
    PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_NATIVE_ABI_NAME,
    PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_SCHEMA_FIELDS,
    PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK,
    PREMAP_WNA16_ADJACENT_TYPED_SLOT_MODE,
    PREMAP_WNA16_ADJACENT_TYPED_SLOT_NAME,
    PREMAP_WNA16_ADJACENT_TYPED_SLOT_PACKET_CHAIN_DEPTH,
    PREMAP_WNA16_ADJACENT_TYPED_SLOT_SOURCE,
    PremapRealDescriptorHandle,
    PremapKernelArgHandoffMirrorObject,
    PremapKernelSideConsumerSchemaAdapterObject,
    PremapKernelSideTypedConsumerObject,
    PremapPayloadCacheProducerTransitionStatePacket,
    build_premap_descriptors,
    build_priority_masks,
    descriptor_summary,
    prepare_premap_address_plan,
)
from mtp_expert_prefetch.tracing import vllm_router_trace
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    VllmRouterRecorder,
    _premap_attach_future_wna16_typed_slot_columns_to_package,
    _premap_kernel_arg_live_mutation_counters,
    _reset_premap_kernel_arg_live_mutation_counters,
)


def test_build_priority_masks_are_disjoint_and_ordered():
    transition = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.1, 0.2, 0.3, 0.4, 0.95, 0.85]]]])

    masks = build_priority_masks(transition, mtp, transition_topk=4, mtp_topk=4, max_extra=2)

    assert masks["P2_transition_top16"][0, 0, 0].tolist() == [
        True,
        True,
        True,
        True,
        False,
        False,
    ]
    assert not masks["P3_transition_top17_to_4"].any()
    assert masks["P4_mtp_extra1_to_4"][0, 0, 0].tolist() == [
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    assert not masks["P5_mtp_extra5_to_4"].any()


def test_build_premap_descriptors_deduplicates_by_best_priority():
    transition = torch.zeros((2, 1, 1, 8))
    mtp = torch.zeros_like(transition)
    transition[0, 0, 0, [0, 1, 2, 3]] = torch.tensor([0.9, 0.8, 0.7, 0.6])
    transition[1, 0, 0, [0, 1, 4, 5]] = torch.tensor([0.95, 0.75, 0.5, 0.4])
    mtp[:, 0, 0, [6, 7, 1, 2]] = torch.tensor([0.99, 0.88, 0.77, 0.66])
    sample_ids = torch.tensor([42, 42])

    descriptors = build_premap_descriptors(
        transition,
        mtp,
        sample_ids,
        transition_topk=4,
        mtp_topk=4,
        max_extra=2,
    )

    by_expert = {item.expert_id: item for item in descriptors}
    assert by_expert[0].priority == 2
    assert by_expert[1].priority == 2
    assert by_expert[6].priority == 4
    assert by_expert[7].priority == 4
    assert 2 in by_expert
    assert 6 in by_expert
    assert len(descriptors) == len(by_expert)

    summary = descriptor_summary(descriptors, expert_bytes=100)
    assert summary["num_descriptors"] == len(descriptors)
    assert summary["by_priority"]["2"] == 6
    assert summary["by_priority"]["4"] == 2
    assert summary["per_sample_layer_count"]["max"] == pytest.approx(8.0)
    assert summary["total_descriptor_bytes"] == 800
    assert summary["per_sample_layer_bytes"]["max"] == pytest.approx(800.0)


def test_prepare_premap_address_plan_builds_zero_payload_address_handles():
    descriptors = [
        ExpertPrefetchDescriptor(0, 2, 7, 3, "transition_tail", 0.50),
        ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
        ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
    ]

    plan = prepare_premap_address_plan(
        descriptors,
        descriptor_bytes=128,
        address_namespace="awq_descriptor",
    )
    repeated = prepare_premap_address_plan(
        list(reversed(descriptors)),
        descriptor_bytes=128,
        address_namespace="awq_descriptor",
    )
    other_namespace = prepare_premap_address_plan(
        descriptors,
        descriptor_bytes=128,
        address_namespace="other_descriptor",
    )

    assert plan.descriptor_count == 3
    assert plan.unique_experts == 2
    assert plan.unique_layers == 2
    assert plan.unique_sample_layers == 2
    assert plan.actual_bytes == 384
    assert plan.payload_bytes == 0
    assert [record.descriptor_slot for record in plan.records] == [0, 1, 2]
    assert [record.expert_id for record in plan.records] == [3, 7, 7]
    assert all(record.payload_bytes == 0 for record in plan.records)
    assert plan.records[0].address_key == "awq_descriptor:l1:e3"
    assert plan.by_priority == {"2": 1, "3": 1, "4": 1}
    assert plan.by_source["transition_head"] == 1
    assert plan.descriptor_hash == repeated.descriptor_hash
    assert plan.address_hash == repeated.address_hash
    assert plan.address_hash != other_namespace.address_hash


def test_prepare_premap_address_plan_rejects_negative_descriptor_bytes():
    with pytest.raises(ValueError, match="descriptor_bytes"):
        prepare_premap_address_plan([], descriptor_bytes=-1)


def test_payload_cache_producer_transition_state_packet_is_readonly_native_contract():
    packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=3,
        previous_experts=(7, 2, 7),
        current_experts=(4, 2, 4),
        issue_source="prelaunch_observed_transition_premap_shadow",
        transition_summary_mode="matrix_topk",
        transition_topk_count=8,
        max_num_experts=16,
    )

    assert packet.schema_name == PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_SCHEMA_NAME
    assert packet.schema_hash == PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_SCHEMA_HASH
    assert "max_num_experts" in PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_SCHEMA_FIELDS
    assert packet.ready is True
    assert packet.expert_ids_in_range is True
    assert packet.previous_experts_canonical == (2, 7)
    assert packet.current_experts_canonical == (2, 4)
    assert packet.native_previous_experts_i32 == (2, 7)
    assert packet.native_current_experts_i32 == (2, 4)
    assert packet.payload_bytes == 0
    assert packet.ready_credit is False
    assert packet.passed_to_kernel is False
    assert packet.changes_kernel_launch_args is False
    assert len(packet.state_hash) == 64
    payload = packet.as_dict()
    assert payload["ready"] is True
    assert payload["native_abi_name"] == (
        PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_NATIVE_ABI_NAME
    )
    assert payload["native_abi_hash"] == (
        PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_NATIVE_ABI_HASH
    )
    assert payload["native_abi_field_count"] == len(
        PREMAP_PAYLOAD_CACHE_PRODUCER_TRANSITION_STATE_NATIVE_ABI_FIELDS
    )
    assert payload["max_num_experts"] == 16
    assert payload["previous_expert_count"] == 2
    assert payload["current_expert_count"] == 2
    assert payload["issue_candidate_experts"] == [2, 7]
    assert payload["issue_candidate_count"] == 2
    assert payload["issue_candidate_first_expert"] == 2
    assert payload["issue_candidate_last_expert"] == 7
    assert payload["issue_candidate_hash"] == "ea95d41875d6802c"
    assert payload["payload_bytes"] == 0
    assert payload["ready_credit"] is False
    assert payload["ready_before_demand_credit"] is False
    assert payload["payload_transfer_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["kernel_arg_pass_allowed"] is False
    assert payload["real_ready_credit_granted"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
    assert payload["uses_current_wna16_args"] is False
    assert payload["passes_current_wna16_args"] is False
    assert payload["measures_tpot"] is False
    assert payload["measures_vllm_latency"] is False


def test_payload_cache_producer_transition_state_packet_rejects_invalid_contract():
    base = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(2,),
    )
    payload_packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(2,),
        payload_bytes=1,
    )
    kernel_packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(2,),
        passed_to_kernel=True,
    )
    source_packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(2,),
        issue_source="bad_source",
    )
    mode_packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(2,),
        transition_summary_mode="bad_mode",
    )
    out_of_range_packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(1,),
        current_experts=(8,),
        max_num_experts=8,
    )
    negative_expert_packet = PremapPayloadCacheProducerTransitionStatePacket(
        layer_id=0,
        previous_experts=(-1,),
        current_experts=(2,),
        max_num_experts=8,
    )

    assert payload_packet.ready is False
    assert kernel_packet.ready is False
    assert source_packet.ready is False
    assert mode_packet.ready is False
    assert out_of_range_packet.ready is False
    assert out_of_range_packet.expert_ids_in_range is False
    assert negative_expert_packet.ready is False
    assert negative_expert_packet.expert_ids_in_range is False
    assert payload_packet.state_hash != base.state_hash
    assert kernel_packet.state_hash != base.state_hash


def test_premap_address_hash_changes_with_plan_semantics_but_key_reuses_address():
    transition = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 7, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    mtp = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75)],
        descriptor_bytes=64,
    )

    assert transition.records[0].address_key == mtp.records[0].address_key
    assert transition.descriptor_hash != mtp.descriptor_hash
    assert transition.address_hash != mtp.address_hash


def _kernel_side_schema_adapter(
    **overrides: object,
) -> PremapKernelSideConsumerSchemaAdapterObject:
    base = PremapKernelSideConsumerSchemaAdapterObject(
        mode="readonly_kernel_side_consumer_schema_adapter",
        semantic_adapter_hash="semantic-adapter",
        semantic_adapter_ready=True,
        table_object_hash="table-object",
        launch_schema_mirror_hash="launch-schema",
        row_count=2,
        column_count=len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
        table_schema_hash=PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        semantic_schema_hash=PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
        kernel_side_schema_name=PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME,
        kernel_side_schema_hash=PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
        kernel_side_field_count=len(PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS),
        row_order_hash="row-order",
        ordered_row_hash="ordered-row",
        required_source_hit_count=6,
        required_source_miss_count=0,
        optional_source_hit_count=0,
        optional_source_miss_count=2,
        handle_field_read_count=8,
        consumer_schema_present=True,
        consumer_connected=False,
        live_enabled=False,
        live_eligible=False,
        blocked=True,
        block_reason="kernel_side_consumer_live_disabled",
    )
    return replace(base, **overrides)


def _kernel_side_typed_consumer(
    **overrides: object,
) -> PremapKernelSideTypedConsumerObject:
    base = PremapKernelSideTypedConsumerObject(
        mode="readonly_kernel_side_typed_consumer_object",
        kernel_side_adapter_hash="kernel-side-adapter",
        kernel_side_adapter_ready=True,
        semantic_adapter_hash="semantic-adapter",
        table_object_hash="table-object",
        launch_schema_mirror_hash="launch-schema",
        row_count=2,
        column_count=len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
        table_schema_hash=PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        semantic_schema_hash=PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH,
        kernel_side_schema_hash=PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH,
        typed_consumer_schema_name=PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME,
        typed_consumer_schema_hash=PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH,
        typed_consumer_field_count=len(PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS),
        row_order_hash="row-order",
        ordered_row_hash="ordered-row",
        descriptor_ptr_handle_hash="descriptor-ptr",
        packed_weight_descriptor_handle_hash="packed-weight",
        scale_metadata_handle_hash="scale-metadata",
        aux_metadata_handle_hash="aux-metadata",
        required_source_hit_count=6,
        required_source_miss_count=0,
        optional_source_hit_count=0,
        optional_source_miss_count=2,
        handle_field_read_count=8,
        consumer_object_present=True,
        consumer_connected=False,
        live_enabled=False,
        live_eligible=False,
        blocked=True,
        block_reason="kernel_side_typed_consumer_live_disabled",
    )
    return replace(base, **overrides)


def test_kernel_side_consumer_schema_adapter_accepts_blocked_live_branches():
    disabled = _kernel_side_schema_adapter()
    assert disabled.ready is True

    enabled_not_connected = _kernel_side_schema_adapter(
        live_enabled=True,
        live_eligible=True,
        block_reason="kernel_side_consumer_not_connected",
    )
    assert enabled_not_connected.ready is True

    connected_no_pass = _kernel_side_schema_adapter(
        consumer_connected=True,
        live_enabled=True,
        live_eligible=True,
        block_reason="kernel_side_consumer_kernel_arg_pass_disabled",
    )
    assert connected_no_pass.ready is True

    connected_shadow_pass = _kernel_side_schema_adapter(
        consumer_connected=True,
        live_enabled=True,
        live_eligible=True,
        block_reason="kernel_side_consumer_shadow_only_kernel_arg_pass_enabled",
    )
    assert connected_shadow_pass.ready is True

    enabled_not_eligible = _kernel_side_schema_adapter(
        live_enabled=True,
        live_eligible=False,
        block_reason="kernel_side_consumer_not_eligible",
    )
    assert enabled_not_eligible.ready is True

    not_eligible_but_connected = replace(
        enabled_not_eligible,
        consumer_connected=True,
    )
    assert not_eligible_but_connected.ready is False

    wrong_reason = replace(
        connected_no_pass,
        block_reason="kernel_side_consumer_live_disabled",
    )
    assert wrong_reason.ready is False


def test_kernel_side_consumer_schema_adapter_rejects_side_effects():
    valid = _kernel_side_schema_adapter()

    assert replace(valid, payload_bytes=1).ready is False
    assert replace(valid, passed_to_kernel=True).ready is False
    assert replace(valid, changes_kernel_launch_args=True).ready is False
    assert replace(valid, live_compatible_with_current_wna16_args=True).ready is False


def test_kernel_side_typed_consumer_object_accepts_blocked_live_branches():
    disabled = _kernel_side_typed_consumer()
    assert disabled.ready is True

    enabled_not_connected = _kernel_side_typed_consumer(
        live_enabled=True,
        live_eligible=True,
        block_reason="kernel_side_typed_consumer_not_connected",
    )
    assert enabled_not_connected.ready is True

    connected_no_pass = _kernel_side_typed_consumer(
        consumer_connected=True,
        live_enabled=True,
        live_eligible=True,
        block_reason="kernel_side_typed_consumer_kernel_arg_pass_disabled",
    )
    assert connected_no_pass.ready is True

    connected_shadow_pass = _kernel_side_typed_consumer(
        consumer_connected=True,
        live_enabled=True,
        live_eligible=True,
        block_reason="kernel_side_typed_consumer_shadow_only_kernel_arg_pass_enabled",
    )
    assert connected_shadow_pass.ready is True

    enabled_not_eligible = _kernel_side_typed_consumer(
        live_enabled=True,
        live_eligible=False,
        block_reason="kernel_side_typed_consumer_not_eligible",
    )
    assert enabled_not_eligible.ready is True

    not_eligible_but_connected = replace(
        enabled_not_eligible,
        consumer_connected=True,
    )
    assert not_eligible_but_connected.ready is False


def test_kernel_side_typed_consumer_object_rejects_side_effects():
    valid = _kernel_side_typed_consumer()

    assert replace(valid, payload_bytes=1).ready is False
    assert replace(valid, passed_to_kernel=True).ready is False
    assert replace(valid, changes_kernel_launch_args=True).ready is False
    assert replace(valid, live_compatible_with_current_wna16_args=True).ready is False


def test_controlled_premap_address_manager_tracks_address_reuse_without_payload():
    first = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    second = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
            ExpertPrefetchDescriptor(0, 2, 9, 3, "transition_tail", 0.50),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=2)

    first_snapshot = manager.prepare(first)
    second_snapshot = manager.prepare(second)

    assert first_snapshot.prepared_plan_count == 1
    assert first_snapshot.prepared_record_count == 2
    assert first_snapshot.new_address_count == 2
    assert first_snapshot.reused_address_count == 0
    assert first_snapshot.prepared_descriptor_actual_bytes == 128
    assert first_snapshot.resident_descriptor_bytes == 128
    assert first_snapshot.payload_bytes == 0

    assert second_snapshot.prepared_plan_count == 2
    assert second_snapshot.prepared_record_count == 4
    assert second_snapshot.new_address_count == 3
    assert second_snapshot.reused_address_count == 1
    assert second_snapshot.resident_address_count == 2
    assert second_snapshot.evicted_address_count == 1
    assert second_snapshot.prepared_descriptor_actual_bytes == 256
    assert second_snapshot.resident_descriptor_bytes == 128
    assert second_snapshot.payload_bytes == 0
    assert manager.contains_address_key("expert_weight_descriptor:l1:e7")
    assert manager.contains_layer_expert(layer_idx=2, expert_id=9)
    assert not manager.contains_layer_expert(layer_idx=1, expert_id=3)
    handle = manager.resolve_layer_expert(layer_idx=2, expert_id=9)
    assert handle is not None
    assert handle.address_key == "expert_weight_descriptor:l2:e9"
    assert handle.descriptor_ptr == "descriptor://expert_weight_descriptor:l2:e9"
    assert handle.packed_weight_descriptor == (
        "packed_weight_descriptor://expert_weight_descriptor:l2:e9"
    )
    assert handle.scale_metadata_handle == (
        "scale_metadata://expert_weight_descriptor:l2:e9"
    )
    assert handle.payload_bytes == 0
    assert handle.handle_hash


def test_controlled_premap_address_manager_readonly_consumer_lifecycle():
    first = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    second = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 2, 9, 3, "transition_tail", 0.50)],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=2)

    manager.prepare(first)
    key3 = ControlledPremapAddressManager.address_key(layer_idx=1, expert_id=3)
    key7 = ControlledPremapAddressManager.address_key(layer_idx=1, expert_id=7)
    handle3 = manager.resolve_address_key(key3)
    handle7 = manager.resolve_address_key(key7)
    assert handle3 is not None
    assert handle7 is not None

    hit = manager.consume_readonly(
        [key3, key7],
        expected_handle_hash_by_address_key={
            key3: handle3.handle_hash,
            key7: handle7.handle_hash,
        },
    )
    assert hit.lookup_count == 2
    assert hit.handle_hit_count == 2
    assert hit.handle_miss_count == 0
    assert hit.evicted_before_consume_count == 0
    assert hit.stale_handle_count == 0
    assert hit.handle_parity_ok is True

    stale = manager.consume_readonly(
        [key3],
        expected_handle_hash_by_address_key={key3: "not-the-current-hash"},
    )
    assert stale.handle_hit_count == 1
    assert stale.stale_handle_count == 1
    assert stale.handle_parity_ok is False

    manager.prepare(second)
    evicted = manager.consume_readonly(
        [key3, key7],
        expected_handle_hash_by_address_key={
            key3: handle3.handle_hash,
            key7: handle7.handle_hash,
        },
    )
    assert evicted.lookup_count == 2
    assert evicted.handle_hit_count == 1
    assert evicted.handle_miss_count == 1
    assert evicted.evicted_before_consume_count == 1
    assert evicted.stale_handle_count == 0
    assert evicted.handle_parity_ok is False

    refreshed = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    manager.prepare(refreshed)
    refreshed_handle3 = manager.resolve_address_key(key3)
    assert refreshed_handle3 is not None
    rehit = manager.consume_readonly(
        [key3],
        expected_handle_hash_by_address_key={key3: refreshed_handle3.handle_hash},
    )
    assert rehit.handle_hit_count == 1
    assert rehit.handle_miss_count == 0
    assert rehit.evicted_before_consume_count == 0
    assert rehit.stale_handle_count == 0
    assert rehit.handle_parity_ok is True


def test_controlled_premap_address_manager_executes_descriptor_prep_readonly():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    before_snapshot = manager.snapshot()
    before_lru_order = list(manager._addresses.keys())

    result = manager.execute_descriptor_prep_readonly(keys)
    after_snapshot = manager.snapshot()

    assert result.execution_mode == "readonly_descriptor_address_object"
    assert result.lookup_count == 2
    assert result.prepared_handle_count == 2
    assert result.missing_handle_count == 0
    assert result.descriptor_ptr_count == 2
    assert result.packed_weight_descriptor_count == 2
    assert result.scale_metadata_handle_count == 2
    assert result.payload_bytes == 0
    assert result.ready_credit is False
    assert result.changes_router is False
    assert result.changes_descriptor_order is False
    assert result.consumer_object_count == 2
    assert result.consumer_object_hash
    assert len(result.consumer_object_hash_by_address_key) == 2
    assert result.handle_hash
    assert result.execution_ok is True
    assert after_snapshot == before_snapshot
    assert list(manager._addresses.keys()) == before_lru_order

    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
    )
    assert read_result.lookup_count == 2
    assert read_result.object_hit_count == 2
    assert read_result.object_miss_count == 0
    assert read_result.stale_object_count == 0
    assert read_result.object_hash == result.consumer_object_hash
    assert read_result.payload_bytes == 0
    assert read_result.ready_credit is False
    assert read_result.changes_router is False
    assert read_result.changes_descriptor_order is False
    assert read_result.read_ok is True

    table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
    )
    native_input = table_object.to_native_typed_consumer_input_dict()
    assert native_input["_meta"]["schema_hash"] == (
        PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert native_input["_meta"]["payload_bytes"] == 0
    assert native_input["_meta"]["ready_credit"] is False
    assert native_input["_meta"]["changes_router"] is False
    assert native_input["_meta"]["changes_descriptor_order"] is False
    assert native_input["_meta"]["passed_to_kernel"] is False
    assert native_input["_meta"]["changes_kernel_launch_args"] is False
    assert len(native_input["descriptor_ptr"]) == 2
    assert len(native_input["packed_weight_descriptor"]) == 2
    assert len(native_input["scale_metadata_handle"]) == 2
    assert len(native_input["aux_metadata_handle"]) == 2
    assert native_input["expert_id"] == [3, 7]
    assert all(isinstance(value, int) for value in native_input["descriptor_ptr"])
    assert all(value != 0 for value in native_input["descriptor_ptr"])
    assert native_input["aux_metadata_handle"] == [0, 0]
    direct_columns = [[0, 0], [0, 0], [0, 0], [-1, -1]]
    copied = table_object.copy_native_typed_consumer_columns_to(
        tuple(direct_columns)
    )
    assert copied == 2
    assert direct_columns[0] == native_input["descriptor_ptr"]
    assert direct_columns[1] == native_input["packed_weight_descriptor"]
    assert direct_columns[2] == native_input["scale_metadata_handle"]
    assert direct_columns[3] == native_input["aux_metadata_handle"]
    signed_columns = [[0, 0], [0, 0], [0, 0], [0, 0]]
    signed_copied = table_object.copy_native_typed_consumer_columns_to(
        tuple(signed_columns),
        signed_i64=True,
    )
    assert signed_copied == 2
    assert all(-(1 << 63) <= value < (1 << 63) for column in signed_columns for value in column)
    prep_dry_run_result = manager.execute_descriptor_address_prep_dry_run_readonly(
        table_object,
        read_result=read_result,
    )
    assert (
        prep_dry_run_result.execution_mode
        == "readonly_descriptor_address_prep_execution_dry_run"
    )
    assert prep_dry_run_result.source == "kernel_arg_shadow_table_object"
    assert prep_dry_run_result.row_count == 2
    assert prep_dry_run_result.column_count == len(
        PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
    )
    assert prep_dry_run_result.schema_hash == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    assert prep_dry_run_result.table_object_hash == table_object.object_hash
    assert prep_dry_run_result.lifecycle_ok is True
    assert prep_dry_run_result.execution_ok is True
    assert prep_dry_run_result.row_handle_parity_ok_count == 2
    assert prep_dry_run_result.descriptor_ptr_parity_ok_count == 2
    assert prep_dry_run_result.packed_weight_descriptor_parity_ok_count == 2
    assert prep_dry_run_result.scale_metadata_handle_parity_ok_count == 2
    assert prep_dry_run_result.aux_metadata_handle_parity_ok_count == 2
    assert prep_dry_run_result.row_handle_miss_count == 0
    assert prep_dry_run_result.handle_field_read_count == 8
    assert prep_dry_run_result.required_handle_field_available_count == 6
    assert prep_dry_run_result.optional_handle_field_available_count == 0
    assert prep_dry_run_result.descriptor_ptr_field_read_count == 2
    assert prep_dry_run_result.packed_weight_descriptor_field_read_count == 2
    assert prep_dry_run_result.scale_metadata_handle_field_read_count == 2
    assert prep_dry_run_result.aux_metadata_handle_field_read_count == 2
    assert prep_dry_run_result.descriptor_ptr_field_available_count == 2
    assert prep_dry_run_result.packed_weight_descriptor_field_available_count == 2
    assert prep_dry_run_result.scale_metadata_handle_field_available_count == 2
    assert prep_dry_run_result.aux_metadata_handle_field_available_count == 0
    assert prep_dry_run_result.payload_bytes == 0
    assert prep_dry_run_result.passed_to_kernel is False
    shim_result = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=prep_dry_run_result,
        kernel_arg_handoff_lab_gate_passed=True,
    )
    assert shim_result.execution_mode == "readonly_prelaunch_consumer_shim"
    assert shim_result.object_count == 2
    assert shim_result.object_hash == read_result.object_hash
    assert shim_result.read_ok is True
    assert shim_result.shim_ok is True
    assert shim_result.handle_table_row_count == 2
    assert shim_result.handle_table_column_count == len(
        PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
    )
    assert (
        shim_result.handle_table_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.handle_table_read_ok is True
    assert shim_result.handle_table_lifecycle_ok is True
    assert shim_result.handle_table_per_row_parity_ok_count == 2
    assert shim_result.handle_table_row_miss_count == 0
    assert shim_result.handle_table_stale_row_count == 0
    assert shim_result.handle_table_passed_to_kernel is False
    assert shim_result.handle_table_payload_bytes == 0
    assert shim_result.handle_table_consume_ok is True
    assert shim_result.handle_table_consume_lifecycle_ok is True
    assert shim_result.handle_table_consume_row_count == table_result.row_count
    assert shim_result.handle_table_consume_column_count == table_result.column_count
    assert shim_result.handle_table_consume_schema_hash == table_result.schema_hash
    assert (
        shim_result.handle_table_consume_mode
        == "readonly_consume_kernel_arg_shadow_table"
    )
    assert shim_result.handle_table_consume_source == table_result.row_order_source
    assert (
        shim_result.handle_table_consume_row_order_hash
        == table_result.row_order_hash
    )
    assert (
        shim_result.handle_table_consume_ordered_row_hash
        == table_result.ordered_row_hash
    )
    assert (
        shim_result.handle_table_consume_per_row_parity_ok_count
        == table_result.per_row_parity_ok_count
    )
    assert shim_result.handle_table_consume_handle_field_read_count == 8
    assert (
        shim_result.handle_table_consume_required_handle_field_available_count
        == 6
    )
    assert (
        shim_result.handle_table_consume_optional_handle_field_available_count
        == 0
    )
    assert shim_result.handle_table_consume_descriptor_ptr_field_read_count == 2
    assert (
        shim_result.handle_table_consume_packed_weight_descriptor_field_read_count
        == 2
    )
    assert (
        shim_result.handle_table_consume_scale_metadata_handle_field_read_count
        == 2
    )
    assert shim_result.handle_table_consume_aux_metadata_handle_field_read_count == 2
    assert shim_result.handle_table_consume_descriptor_ptr_field_available_count == 2
    assert (
        shim_result.handle_table_consume_packed_weight_descriptor_field_available_count
        == 2
    )
    assert (
        shim_result.handle_table_consume_scale_metadata_handle_field_available_count
        == 2
    )
    assert shim_result.handle_table_consume_aux_metadata_handle_field_available_count == 0
    assert shim_result.handle_table_consume_source_hit_counts == {
        "descriptor_ptr": 2,
        "packed_weight_descriptor": 2,
        "scale_metadata_handle": 2,
        "aux_metadata_handle": 0,
    }
    assert shim_result.handle_table_consume_source_miss_counts == {
        "descriptor_ptr": 0,
        "packed_weight_descriptor": 0,
        "scale_metadata_handle": 0,
        "aux_metadata_handle": 2,
    }
    assert shim_result.handle_table_consume_row_miss_count == 0
    assert shim_result.handle_table_consume_stale_row_count == 0
    assert shim_result.handle_table_consume_passed_to_kernel is False
    assert shim_result.handle_table_consume_payload_bytes == 0
    assert (
        shim_result.wna16_adjacent_typed_slot_name
        == PREMAP_WNA16_ADJACENT_TYPED_SLOT_NAME
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_mode
        == PREMAP_WNA16_ADJACENT_TYPED_SLOT_MODE
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_source
        == PREMAP_WNA16_ADJACENT_TYPED_SLOT_SOURCE
    )
    assert shim_result.wna16_adjacent_typed_slot_checked is True
    assert shim_result.wna16_adjacent_typed_slot_ready is True
    assert shim_result.wna16_adjacent_typed_slot_row_count == 2
    assert shim_result.wna16_adjacent_typed_slot_row_ok_count == 2
    assert shim_result.wna16_adjacent_typed_slot_error_count == 0
    assert shim_result.wna16_adjacent_typed_slot_all_handle_fields_read is True
    assert (
        shim_result.wna16_adjacent_typed_slot_packet_chain_depth
        == PREMAP_WNA16_ADJACENT_TYPED_SLOT_PACKET_CHAIN_DEPTH
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_field_mask
        == PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK
    )
    assert shim_result.wna16_adjacent_typed_slot_payload_bytes == 0
    assert shim_result.wna16_adjacent_typed_slot_passed_to_kernel is False
    assert (
        shim_result.wna16_adjacent_typed_slot_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_current_wna16_arg_compatible
        is False
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_requires_wna16_arg_reinterpretation
        is False
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_explicit_typed_abi_slot
        is True
    )
    assert (
        shim_result.wna16_adjacent_typed_slot_reuses_current_wna16_arg_slot
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_dry_run_mode
        == "readonly_kernel_arg_handoff_dry_run"
    )
    assert shim_result.kernel_arg_handoff_dry_run_ready is True
    assert shim_result.kernel_arg_handoff_dry_run_row_count == 2
    assert shim_result.kernel_arg_handoff_dry_run_column_count == 4
    assert (
        shim_result.kernel_arg_handoff_dry_run_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.kernel_arg_handoff_dry_run_required_source_hit_count == 6
    assert shim_result.kernel_arg_handoff_dry_run_required_source_miss_count == 0
    assert shim_result.kernel_arg_handoff_dry_run_optional_source_hit_count == 0
    assert shim_result.kernel_arg_handoff_dry_run_optional_source_miss_count == 2
    assert shim_result.kernel_arg_handoff_dry_run_payload_bytes == 0
    assert shim_result.kernel_arg_handoff_dry_run_passed_to_kernel is False
    assert (
        shim_result.kernel_arg_handoff_shadow_slot_mode
        == "readonly_kernel_arg_handoff_shadow_slot"
    )
    assert shim_result.kernel_arg_handoff_shadow_slot_ready is True
    assert shim_result.kernel_arg_handoff_shadow_slot_hash
    assert shim_result.kernel_arg_handoff_shadow_slot_table_object_hash == (
        table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_shadow_slot_row_count == 2
    assert shim_result.kernel_arg_handoff_shadow_slot_column_count == 4
    assert (
        shim_result.kernel_arg_handoff_shadow_slot_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.kernel_arg_handoff_shadow_slot_required_source_hit_count == 6
    assert shim_result.kernel_arg_handoff_shadow_slot_required_source_miss_count == 0
    assert shim_result.kernel_arg_handoff_shadow_slot_optional_source_hit_count == 0
    assert shim_result.kernel_arg_handoff_shadow_slot_optional_source_miss_count == 2
    assert shim_result.kernel_arg_handoff_shadow_slot_payload_bytes == 0
    assert shim_result.kernel_arg_handoff_shadow_slot_passed_to_kernel is False
    assert (
        shim_result.kernel_arg_handoff_shadow_slot_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_mirror_mode
        == "readonly_kernel_arg_handoff_mirror"
    )
    assert shim_result.kernel_arg_handoff_mirror_ready is True
    assert shim_result.kernel_arg_handoff_mirror_hash
    assert shim_result.kernel_arg_handoff_mirror_slot_hash == (
        shim_result.kernel_arg_handoff_shadow_slot_hash
    )
    assert shim_result.kernel_arg_handoff_mirror_table_object_hash == (
        table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_mirror_row_count == 2
    assert shim_result.kernel_arg_handoff_mirror_column_count == 4
    assert (
        shim_result.kernel_arg_handoff_mirror_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.kernel_arg_handoff_mirror_required_source_hit_count == 6
    assert shim_result.kernel_arg_handoff_mirror_required_source_miss_count == 0
    assert shim_result.kernel_arg_handoff_mirror_optional_source_hit_count == 0
    assert shim_result.kernel_arg_handoff_mirror_optional_source_miss_count == 2
    assert shim_result.kernel_arg_handoff_mirror_payload_bytes == 0
    assert shim_result.kernel_arg_handoff_mirror_passed_to_kernel is False
    assert shim_result.kernel_arg_handoff_mirror_changes_kernel_launch_args is False
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_mode
        == "readonly_kernel_arg_handoff_launch_schema_mirror"
    )
    assert shim_result.kernel_arg_handoff_launch_schema_mirror_ready is True
    assert shim_result.kernel_arg_handoff_launch_schema_mirror_hash
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_handoff_mirror_hash
        == shim_result.kernel_arg_handoff_mirror_hash
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_slot_hash
        == shim_result.kernel_arg_handoff_shadow_slot_hash
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_table_object_hash
        == table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_launch_schema_mirror_row_count == 2
    assert shim_result.kernel_arg_handoff_launch_schema_mirror_column_count == 4
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_table_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_launch_schema_name
        == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_NAME
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_launch_schema_hash
        == PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_HASH
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_launch_arg_field_count
        == len(PREMAP_KERNEL_ARG_PRELAUNCH_LAUNCH_SCHEMA_FIELDS)
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_required_source_hit_count
        == 6
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_required_source_miss_count
        == 0
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_optional_source_hit_count
        == 0
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_optional_source_miss_count
        == 2
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_handle_field_read_count
        == 8
    )
    assert shim_result.kernel_arg_handoff_launch_schema_mirror_payload_bytes == 0
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_passed_to_kernel
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_launch_schema_mirror_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_arg_semantic_handle_adapter_mode
        == "readonly_kernel_arg_semantic_handle_adapter"
    )
    assert shim_result.kernel_arg_semantic_handle_adapter_ready is True
    assert shim_result.kernel_arg_semantic_handle_adapter_hash
    assert (
        shim_result.kernel_arg_semantic_handle_adapter_launch_schema_mirror_hash
        == shim_result.kernel_arg_handoff_launch_schema_mirror_hash
    )
    assert shim_result.kernel_arg_semantic_handle_adapter_row_count == 2
    assert shim_result.kernel_arg_semantic_handle_adapter_column_count == 4
    assert (
        shim_result.kernel_arg_semantic_handle_adapter_semantic_schema_hash
        == PREMAP_KERNEL_ARG_SEMANTIC_HANDLE_SCHEMA_HASH
    )
    assert shim_result.kernel_arg_semantic_handle_adapter_required_source_hit_count == 6
    assert shim_result.kernel_arg_semantic_handle_adapter_required_source_miss_count == 0
    assert shim_result.kernel_arg_semantic_handle_adapter_handle_field_read_count == 8
    assert shim_result.kernel_arg_semantic_handle_adapter_payload_bytes == 0
    assert shim_result.kernel_arg_semantic_handle_adapter_passed_to_kernel is False
    assert (
        shim_result.kernel_arg_semantic_handle_adapter_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_arg_semantic_handle_adapter_live_compatible_with_current_wna16_args
        is False
    )
    assert (
        shim_result.single_field_handle_handoff_canary_mode
        == "readonly_single_field_handle_handoff_canary"
    )
    assert shim_result.single_field_handle_handoff_canary_ready is True
    assert shim_result.single_field_handle_handoff_canary_hash
    assert shim_result.single_field_handle_handoff_canary_field_name == "scale_metadata_handle"
    assert shim_result.single_field_handle_handoff_canary_source == "semantic_handle_table"
    assert (
        shim_result.single_field_handle_handoff_canary_mirror_mode
        == "readonly_scale_metadata_handle_mirror"
    )
    assert shim_result.single_field_handle_handoff_canary_mirror_ready is True
    assert (
        shim_result.single_field_handle_handoff_canary_mirror_field_name
        == "scale_metadata_handle"
    )
    assert (
        shim_result.single_field_handle_handoff_canary_mirror_source
        == "semantic_handle_table"
    )
    assert (
        shim_result.single_field_handle_handoff_canary_table_object_hash
        == table_object.object_hash
    )
    assert (
        shim_result.single_field_handle_handoff_canary_semantic_adapter_hash
        == shim_result.kernel_arg_semantic_handle_adapter_hash
    )
    assert shim_result.single_field_handle_handoff_canary_row_count == 2
    assert shim_result.single_field_handle_handoff_canary_field_handle_count == 2
    assert shim_result.single_field_handle_handoff_canary_field_handle_nonzero_count == 2
    assert shim_result.single_field_handle_handoff_canary_field_handle_zero_count == 0
    assert shim_result.single_field_handle_handoff_canary_field_handle_hash
    assert (
        shim_result.single_field_handle_handoff_canary_field_handle_hash
        == shim_result.single_field_handle_handoff_canary_semantic_field_hash
    )
    assert (
        shim_result.single_field_handle_handoff_canary_mirror_handle_hash
        == shim_result.single_field_handle_handoff_canary_field_handle_hash
    )
    assert (
        shim_result.single_field_handle_handoff_canary_mirror_schema_hash
        == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
    )
    assert shim_result.single_field_handle_handoff_canary_parity_ok_count == 2
    assert shim_result.single_field_handle_handoff_canary_parity_mismatch_count == 0
    assert (
        shim_result.single_field_handle_handoff_canary_kernel_side_typed_consumer_compatible
        is True
    )
    assert (
        shim_result.single_field_handle_handoff_canary_current_wna16_arg_compatible
        is False
    )
    assert shim_result.single_field_handle_handoff_canary_live_enabled is False
    assert shim_result.single_field_handle_handoff_canary_blocked is True
    assert (
        shim_result.single_field_handle_handoff_canary_block_reason
        == "single_field_handoff_live_disabled"
    )
    assert shim_result.single_field_handle_handoff_canary_payload_bytes == 0
    assert shim_result.single_field_handle_handoff_canary_ready_credit is False
    assert shim_result.single_field_handle_handoff_canary_passed_to_kernel is False
    assert (
        shim_result.single_field_handle_handoff_canary_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.single_field_handle_handoff_canary_live_compatible_with_current_wna16_args
        is False
    )
    assert (
        shim_result.kernel_side_consumer_schema_adapter_mode
        == "readonly_kernel_side_consumer_schema_adapter"
    )
    assert shim_result.kernel_side_consumer_schema_adapter_ready is True
    assert shim_result.kernel_side_consumer_schema_adapter_hash
    assert (
        shim_result.kernel_side_consumer_schema_adapter_semantic_adapter_hash
        == shim_result.kernel_arg_semantic_handle_adapter_hash
    )
    assert (
        shim_result.kernel_side_consumer_schema_adapter_launch_schema_mirror_hash
        == shim_result.kernel_arg_handoff_launch_schema_mirror_hash
    )
    assert shim_result.kernel_side_consumer_schema_adapter_row_count == 2
    assert shim_result.kernel_side_consumer_schema_adapter_column_count == 4
    assert (
        shim_result.kernel_side_consumer_schema_adapter_kernel_side_schema_name
        == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_NAME
    )
    assert (
        shim_result.kernel_side_consumer_schema_adapter_kernel_side_schema_hash
        == PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_HASH
    )
    assert (
        shim_result.kernel_side_consumer_schema_adapter_kernel_side_field_count
        == len(PREMAP_KERNEL_SIDE_CONSUMER_SCHEMA_FIELDS)
    )
    assert shim_result.kernel_side_consumer_schema_adapter_required_source_hit_count == 6
    assert shim_result.kernel_side_consumer_schema_adapter_required_source_miss_count == 0
    assert shim_result.kernel_side_consumer_schema_adapter_handle_field_read_count == 8
    assert shim_result.kernel_side_consumer_schema_adapter_consumer_schema_present is True
    assert shim_result.kernel_side_consumer_schema_adapter_consumer_connected is False
    assert shim_result.kernel_side_consumer_schema_adapter_live_enabled is False
    assert shim_result.kernel_side_consumer_schema_adapter_live_eligible is False
    assert shim_result.kernel_side_consumer_schema_adapter_blocked is True
    assert (
        shim_result.kernel_side_consumer_schema_adapter_block_reason
        == "kernel_side_consumer_live_disabled"
    )
    assert shim_result.kernel_side_consumer_schema_adapter_payload_bytes == 0
    assert shim_result.kernel_side_consumer_schema_adapter_passed_to_kernel is False
    assert (
        shim_result.kernel_side_consumer_schema_adapter_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_side_consumer_schema_adapter_live_compatible_with_current_wna16_args
        is False
    )
    assert (
        shim_result.kernel_side_typed_consumer_object_mode
        == "readonly_kernel_side_typed_consumer_object"
    )
    assert shim_result.kernel_side_typed_consumer_object_ready is True
    assert shim_result.kernel_side_typed_consumer_object_hash
    assert (
        shim_result.kernel_side_typed_consumer_object_kernel_side_adapter_hash
        == shim_result.kernel_side_consumer_schema_adapter_hash
    )
    assert (
        shim_result.kernel_side_typed_consumer_object_semantic_adapter_hash
        == shim_result.kernel_arg_semantic_handle_adapter_hash
    )
    assert (
        shim_result.kernel_side_typed_consumer_object_launch_schema_mirror_hash
        == shim_result.kernel_arg_handoff_launch_schema_mirror_hash
    )
    assert shim_result.kernel_side_typed_consumer_object_row_count == 2
    assert shim_result.kernel_side_typed_consumer_object_column_count == 4
    assert (
        shim_result.kernel_side_typed_consumer_object_typed_consumer_schema_name
        == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_NAME
    )
    assert (
        shim_result.kernel_side_typed_consumer_object_typed_consumer_schema_hash
        == PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_HASH
    )
    assert (
        shim_result.kernel_side_typed_consumer_object_typed_consumer_field_count
        == len(PREMAP_KERNEL_SIDE_TYPED_CONSUMER_SCHEMA_FIELDS)
    )
    assert shim_result.kernel_side_typed_consumer_object_required_source_hit_count == 6
    assert shim_result.kernel_side_typed_consumer_object_required_source_miss_count == 0
    assert shim_result.kernel_side_typed_consumer_object_handle_field_read_count == 8
    assert shim_result.kernel_side_typed_consumer_object_consumer_object_present is True
    assert shim_result.kernel_side_typed_consumer_object_consumer_connected is False
    assert shim_result.kernel_side_typed_consumer_object_live_enabled is False
    assert shim_result.kernel_side_typed_consumer_object_live_eligible is False
    assert shim_result.kernel_side_typed_consumer_object_blocked is True
    assert (
        shim_result.kernel_side_typed_consumer_object_block_reason
        == "kernel_side_typed_consumer_live_disabled"
    )
    assert shim_result.kernel_side_typed_consumer_object_payload_bytes == 0
    assert shim_result.kernel_side_typed_consumer_object_passed_to_kernel is False
    assert (
        shim_result.kernel_side_typed_consumer_object_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_side_typed_consumer_object_live_compatible_with_current_wna16_args
        is False
    )
    assert (
        shim_result.native_typed_consumer_bridge_mode
        == "readonly_native_typed_consumer_bridge_check"
    )
    assert shim_result.native_typed_consumer_bridge_checked is True
    assert shim_result.native_typed_consumer_bridge_ok is True
    assert shim_result.native_typed_consumer_bridge_input_hash
    assert (
        shim_result.native_typed_consumer_bridge_table_object_hash
        == table_object.object_hash
    )
    assert (
        shim_result.native_typed_consumer_bridge_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.native_typed_consumer_bridge_row_count == 2
    assert shim_result.native_typed_consumer_bridge_column_count == 4
    assert shim_result.native_typed_consumer_bridge_required_handle_nonzero_count == 6
    assert shim_result.native_typed_consumer_bridge_required_handle_zero_count == 0
    assert shim_result.native_typed_consumer_bridge_optional_handle_nonzero_count == 0
    assert shim_result.native_typed_consumer_bridge_optional_handle_zero_count == 2
    assert shim_result.native_typed_consumer_bridge_expert_id_valid_count == 2
    assert shim_result.native_typed_consumer_bridge_expert_id_invalid_count == 0
    assert shim_result.native_typed_consumer_bridge_address_key_hash_nonzero_count == 2
    assert shim_result.native_typed_consumer_bridge_address_key_hash_zero_count == 0
    assert shim_result.native_typed_consumer_bridge_failure_count == 0
    assert shim_result.native_typed_consumer_bridge_failures == ()
    assert shim_result.native_typed_consumer_bridge_payload_bytes == 0
    assert shim_result.native_typed_consumer_bridge_ready_credit is False
    assert shim_result.native_typed_consumer_bridge_changes_router is False
    assert (
        shim_result.native_typed_consumer_bridge_changes_descriptor_order is False
    )
    assert shim_result.native_typed_consumer_bridge_passed_to_kernel is False
    assert (
        shim_result.native_typed_consumer_bridge_changes_kernel_launch_args is False
    )
    assert (
        shim_result.native_stub_online_invocation_mode
        == "readonly_native_stub_online_invocation_canary"
    )
    assert shim_result.native_stub_online_invocation_checked is True
    assert shim_result.native_stub_online_invocation_ready is True
    assert shim_result.native_stub_online_invocation_ok is True
    assert shim_result.native_stub_online_invocation_native_checker_invoked is True
    assert shim_result.native_stub_online_invocation_native_bridge_ok is True
    assert shim_result.native_stub_online_invocation_package_hash
    assert (
        shim_result.native_stub_online_invocation_input_hash
        == shim_result.native_typed_consumer_bridge_input_hash
    )
    assert (
        shim_result.native_stub_online_invocation_table_object_hash
        == table_object.object_hash
    )
    assert (
        shim_result.native_stub_online_invocation_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.native_stub_online_invocation_row_count == 2
    assert shim_result.native_stub_online_invocation_column_count == 4
    assert shim_result.native_stub_online_invocation_required_handle_nonzero_count == 6
    assert shim_result.native_stub_online_invocation_required_handle_zero_count == 0
    assert shim_result.native_stub_online_invocation_optional_handle_nonzero_count == 0
    assert shim_result.native_stub_online_invocation_optional_handle_zero_count == 2
    assert shim_result.native_stub_online_invocation_expert_id_valid_count == 2
    assert shim_result.native_stub_online_invocation_expert_id_invalid_count == 0
    assert (
        shim_result.native_stub_online_invocation_address_key_hash_nonzero_count == 2
    )
    assert shim_result.native_stub_online_invocation_address_key_hash_zero_count == 0
    assert shim_result.native_stub_online_invocation_requested is True
    assert shim_result.native_stub_online_invocation_native_stub_invoked is False
    assert shim_result.native_stub_online_invocation_blocked is True
    assert (
        shim_result.native_stub_online_invocation_block_reason
        == "native_stub_live_disabled"
    )
    assert shim_result.native_stub_online_invocation_failure_count == 0
    assert shim_result.native_stub_online_invocation_failures == ()
    assert shim_result.native_stub_online_invocation_payload_bytes == 0
    assert shim_result.native_stub_online_invocation_ready_credit is False
    assert shim_result.native_stub_online_invocation_changes_router is False
    assert (
        shim_result.native_stub_online_invocation_changes_descriptor_order is False
    )
    assert shim_result.native_stub_online_invocation_passed_to_kernel is False
    assert (
        shim_result.native_stub_online_invocation_changes_kernel_launch_args is False
    )
    ready_credit_table_object = replace(table_object, ready_credit=True)
    ready_credit_bridge = manager.validate_native_typed_consumer_bridge_readonly(
        ready_credit_table_object
    )
    assert ready_credit_bridge.ok is False
    assert ready_credit_bridge.ready_credit is True
    assert "ready_credit_true" in ready_credit_bridge.failures
    ready_credit_canary = manager.build_native_stub_online_invocation_canary_readonly(
        ready_credit_table_object,
        ready_credit_bridge,
    )
    assert ready_credit_canary.ready is False
    assert ready_credit_canary.ready_credit is True
    assert "native_bridge_check_failed" in ready_credit_canary.failures

    router_mutation_table_object = replace(table_object, changes_router=True)
    router_mutation_bridge = manager.validate_native_typed_consumer_bridge_readonly(
        router_mutation_table_object
    )
    assert router_mutation_bridge.ok is False
    assert router_mutation_bridge.changes_router is True
    assert "changes_router_true" in router_mutation_bridge.failures

    order_mutation_table_object = replace(table_object, changes_descriptor_order=True)
    order_mutation_bridge = manager.validate_native_typed_consumer_bridge_readonly(
        order_mutation_table_object
    )
    assert order_mutation_bridge.ok is False
    assert order_mutation_bridge.changes_descriptor_order is True
    assert "changes_descriptor_order_true" in order_mutation_bridge.failures

    stale_table_object = replace(table_object, row_order_source="stale_source")
    stale_canary = manager.build_native_stub_online_invocation_canary_readonly(
        stale_table_object,
        manager.validate_native_typed_consumer_bridge_readonly(table_object),
    )
    assert stale_canary.ready is False
    assert "native_bridge_input_hash_mismatch" in stale_canary.failures
    assert "native_bridge_table_object_hash_mismatch" in stale_canary.failures

    stale_schema_table_object = replace(table_object, schema_hash="stale_schema")
    stale_schema_canary = manager.build_native_stub_online_invocation_canary_readonly(
        stale_schema_table_object,
        manager.validate_native_typed_consumer_bridge_readonly(table_object),
    )
    assert stale_schema_canary.ready is False
    assert "native_bridge_schema_hash_mismatch" in stale_schema_canary.failures

    stale_row_count_bridge = replace(
        manager.validate_native_typed_consumer_bridge_readonly(table_object),
        row_count=3,
    )
    stale_row_count_canary = (
        manager.build_native_stub_online_invocation_canary_readonly(
            table_object,
            stale_row_count_bridge,
        )
    )
    assert stale_row_count_canary.ready is False
    assert "native_bridge_row_count_mismatch" in stale_row_count_canary.failures

    stale_column_count_bridge = replace(
        manager.validate_native_typed_consumer_bridge_readonly(table_object),
        column_count=5,
    )
    stale_column_count_canary = (
        manager.build_native_stub_online_invocation_canary_readonly(
            table_object,
            stale_column_count_bridge,
        )
    )
    assert stale_column_count_canary.ready is False
    assert "native_bridge_column_count_mismatch" in stale_column_count_canary.failures
    assert (
        shim_result.kernel_arg_handoff_attempt_mode
        == "readonly_kernel_arg_handoff_attempt"
    )
    assert shim_result.kernel_arg_handoff_attempt_record_ready is True
    assert shim_result.kernel_arg_handoff_attempt_hash
    assert (
        shim_result.kernel_arg_handoff_attempt_mirror_hash
        == shim_result.kernel_arg_handoff_mirror_hash
    )
    assert (
        shim_result.kernel_arg_handoff_attempt_slot_hash
        == shim_result.kernel_arg_handoff_shadow_slot_hash
    )
    assert (
        shim_result.kernel_arg_handoff_attempt_table_object_hash
        == table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_attempt_row_count == 2
    assert shim_result.kernel_arg_handoff_attempt_column_count == 4
    assert (
        shim_result.kernel_arg_handoff_attempt_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.kernel_arg_handoff_attempt_mirror_ready is True
    assert shim_result.kernel_arg_handoff_attempt_gate_allowed is False
    assert shim_result.kernel_arg_handoff_attempt_blocked is True
    assert (
        shim_result.kernel_arg_handoff_attempt_block_reason
        == "kernel_arg_handoff_disabled_noop_gate"
    )
    assert shim_result.kernel_arg_handoff_attempt_payload_bytes == 0
    assert shim_result.kernel_arg_handoff_attempt_passed_to_kernel is False
    assert (
        shim_result.kernel_arg_handoff_attempt_changes_kernel_launch_args is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_toggle_mode
        == "readonly_kernel_arg_handoff_live_toggle"
    )
    assert shim_result.kernel_arg_handoff_live_toggle_record_ready is True
    assert shim_result.kernel_arg_handoff_live_toggle_hash
    assert (
        shim_result.kernel_arg_handoff_live_toggle_attempt_hash
        == shim_result.kernel_arg_handoff_attempt_hash
    )
    assert (
        shim_result.kernel_arg_handoff_live_toggle_table_object_hash
        == table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_live_toggle_enabled is False
    assert shim_result.kernel_arg_handoff_live_toggle_lab_gate_passed is True
    assert shim_result.kernel_arg_handoff_live_toggle_attempt_record_ready is True
    assert shim_result.kernel_arg_handoff_live_toggle_live_eligible is False
    assert shim_result.kernel_arg_handoff_live_toggle_blocked is True
    assert (
        shim_result.kernel_arg_handoff_live_toggle_block_reason
        == "kernel_arg_handoff_live_disabled"
    )
    assert shim_result.kernel_arg_handoff_live_toggle_payload_bytes == 0
    assert shim_result.kernel_arg_handoff_live_toggle_passed_to_kernel is False
    assert (
        shim_result.kernel_arg_handoff_live_toggle_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_mode
        == "readonly_kernel_arg_handoff_live_noop_integration"
    )
    assert shim_result.kernel_arg_handoff_live_noop_integration_record_ready is True
    assert shim_result.kernel_arg_handoff_live_noop_integration_hash
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_live_toggle_hash
        == shim_result.kernel_arg_handoff_live_toggle_hash
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_launch_schema_mirror_hash
        == shim_result.kernel_arg_handoff_launch_schema_mirror_hash
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_table_object_hash
        == table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_live_noop_integration_enabled is False
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_lab_gate_passed
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_live_toggle_record_ready
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_launch_schema_ready
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_live_eligible
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_consumer_connected
        is False
    )
    assert shim_result.kernel_arg_handoff_live_noop_integration_blocked is True
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_block_reason
        == "kernel_arg_handoff_live_disabled"
    )
    assert shim_result.kernel_arg_handoff_live_noop_integration_payload_bytes == 0
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_passed_to_kernel
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_mode
        == "readonly_kernel_arg_handoff_live_consumer_adapter"
    )
    assert shim_result.kernel_arg_handoff_live_consumer_adapter_record_ready is True
    assert shim_result.kernel_arg_handoff_live_consumer_adapter_hash
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_hash
        == shim_result.kernel_arg_handoff_live_noop_integration_hash
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_launch_schema_mirror_hash
        == shim_result.kernel_arg_handoff_launch_schema_mirror_hash
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_table_object_hash
        == table_object.object_hash
    )
    assert shim_result.kernel_arg_handoff_live_consumer_adapter_enabled is False
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_lab_gate_passed
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_block_reason
        == "kernel_arg_handoff_live_disabled"
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present
        is True
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_consumer_connected
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_live_eligible
        is False
    )
    assert shim_result.kernel_arg_handoff_live_consumer_adapter_blocked is True
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_block_reason
        == "kernel_arg_handoff_live_disabled"
    )
    assert shim_result.kernel_arg_handoff_live_consumer_adapter_payload_bytes == 0
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_passed_to_kernel
        is False
    )
    assert (
        shim_result.kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args
        is False
    )
    enabled_without_gate = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=prep_dry_run_result,
        kernel_arg_handoff_live_enabled=True,
        kernel_arg_handoff_lab_gate_passed=False,
    )
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_record_ready is True
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_enabled is True
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_lab_gate_passed is False
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_live_eligible is False
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_blocked is True
    assert (
        enabled_without_gate.kernel_arg_handoff_live_toggle_block_reason
        == "kernel_arg_handoff_lab_gate_not_passed"
    )
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_payload_bytes == 0
    assert enabled_without_gate.kernel_arg_handoff_live_toggle_passed_to_kernel is False
    assert (
        enabled_without_gate.kernel_arg_handoff_live_toggle_changes_kernel_launch_args
        is False
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_noop_integration_record_ready
        is True
    )
    assert enabled_without_gate.kernel_arg_handoff_live_noop_integration_enabled is True
    assert (
        enabled_without_gate.kernel_arg_handoff_live_noop_integration_lab_gate_passed
        is False
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_noop_integration_live_eligible
        is False
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_noop_integration_blocked
        is True
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_noop_integration_block_reason
        == "kernel_arg_handoff_lab_gate_not_passed"
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_noop_integration_passed_to_kernel
        is False
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_record_ready
        is True
    )
    assert enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_enabled is True
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_lab_gate_passed
        is False
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready
        is True
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_live_eligible
        is False
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_blocked
        is True
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_block_reason
        == "kernel_arg_handoff_lab_gate_not_passed"
    )
    assert (
        enabled_without_gate.kernel_arg_handoff_live_consumer_adapter_passed_to_kernel
        is False
    )

    enabled_with_gate = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=prep_dry_run_result,
        kernel_arg_handoff_live_enabled=True,
        kernel_arg_handoff_lab_gate_passed=True,
    )
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_record_ready is True
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_enabled is True
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_lab_gate_passed is True
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_attempt_record_ready is True
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_live_eligible is True
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_blocked is True
    assert (
        enabled_with_gate.kernel_arg_handoff_live_toggle_block_reason
        == "kernel_arg_handoff_kernel_consumer_not_connected"
    )
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_payload_bytes == 0
    assert enabled_with_gate.kernel_arg_handoff_live_toggle_passed_to_kernel is False
    assert (
        enabled_with_gate.kernel_arg_handoff_live_toggle_changes_kernel_launch_args
        is False
    )
    assert enabled_with_gate.kernel_arg_handoff_live_noop_integration_record_ready is True
    assert enabled_with_gate.kernel_arg_handoff_live_noop_integration_enabled is True
    assert (
        enabled_with_gate.kernel_arg_handoff_live_noop_integration_lab_gate_passed
        is True
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_noop_integration_live_toggle_record_ready
        is True
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_noop_integration_launch_schema_ready
        is True
    )
    assert enabled_with_gate.kernel_arg_handoff_live_noop_integration_live_eligible is True
    assert (
        enabled_with_gate.kernel_arg_handoff_live_noop_integration_consumer_connected
        is False
    )
    assert enabled_with_gate.kernel_arg_handoff_live_noop_integration_blocked is True
    assert (
        enabled_with_gate.kernel_arg_handoff_live_noop_integration_block_reason
        == "kernel_arg_handoff_kernel_consumer_not_connected"
    )
    assert enabled_with_gate.kernel_arg_handoff_live_noop_integration_payload_bytes == 0
    assert (
        enabled_with_gate.kernel_arg_handoff_live_noop_integration_passed_to_kernel
        is False
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_record_ready
        is True
    )
    assert enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_enabled is True
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_lab_gate_passed
        is True
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_record_ready
        is True
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_live_noop_integration_blocked
        is True
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_consumer_adapter_present
        is True
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_consumer_connected
        is False
    )
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_live_eligible
        is True
    )
    assert enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_blocked is True
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_block_reason
        == "kernel_arg_handoff_kernel_consumer_not_connected"
    )
    assert enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_payload_bytes == 0
    assert (
        enabled_with_gate.kernel_arg_handoff_live_consumer_adapter_passed_to_kernel
        is False
    )
    connected_adapter = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=prep_dry_run_result,
        kernel_arg_handoff_live_enabled=True,
        kernel_arg_handoff_consumer_connected=True,
        kernel_arg_handoff_lab_gate_passed=True,
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_noop_integration_record_ready
        is True
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_noop_integration_consumer_connected
        is True
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_noop_integration_block_reason
        == "kernel_arg_handoff_kernel_arg_pass_disabled"
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_noop_integration_passed_to_kernel
        is False
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_noop_integration_changes_kernel_launch_args
        is False
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_consumer_adapter_record_ready
        is True
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_consumer_adapter_consumer_connected
        is True
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_consumer_adapter_block_reason
        == "kernel_arg_handoff_kernel_arg_pass_disabled"
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_consumer_adapter_payload_bytes
        == 0
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_consumer_adapter_passed_to_kernel
        is False
    )
    assert (
        connected_adapter.kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args
        is False
    )
    live_pass_adapter = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=prep_dry_run_result,
        kernel_arg_handoff_live_enabled=True,
        kernel_arg_handoff_consumer_connected=True,
        kernel_arg_handoff_kernel_arg_pass_enabled=True,
        kernel_arg_handoff_lab_gate_passed=True,
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_noop_integration_record_ready
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_noop_integration_consumer_connected
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_noop_integration_block_reason
        == "kernel_arg_handoff_kernel_arg_pass_disabled"
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_noop_integration_passed_to_kernel
        is False
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_record_ready
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_consumer_connected
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_block_reason
        == "kernel_arg_handoff_kernel_arg_pass_live"
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_blocked is False
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_payload_bytes == 0
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_passed_to_kernel
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_contract_live_pass
        is True
    )
    assert (
        live_pass_adapter.kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff
        is False
    )
    real_mutation_adapter = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=prep_dry_run_result,
        kernel_arg_handoff_live_enabled=True,
        kernel_arg_handoff_consumer_connected=True,
        kernel_arg_handoff_kernel_arg_pass_enabled=True,
        kernel_arg_handoff_real_kernel_arg_mutation_enabled=True,
        kernel_arg_handoff_lab_gate_passed=True,
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_record_ready
        is True
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_block_reason
        == "kernel_arg_handoff_real_kernel_arg_mutation_live"
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_blocked
        is False
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_passed_to_kernel
        is True
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args
        is True
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_contract_live_pass
        is True
    )
    assert (
        real_mutation_adapter.kernel_arg_handoff_live_consumer_adapter_real_kernel_arg_handoff
        is True
    )
    assert shim_result.handle_table_object_consumed is True
    assert shim_result.handle_table_object_hash == table_object.object_hash
    assert shim_result.handle_table_object_row_count == 2
    assert shim_result.handle_table_object_lifecycle_ok is True
    assert shim_result.handle_table_object_passed_to_kernel is False
    assert shim_result.handle_table_object_payload_bytes == 0
    assert (
        shim_result.prep_execution_dry_run_mode
        == "readonly_descriptor_address_prep_execution_dry_run"
    )
    assert shim_result.prep_execution_dry_run_source == "kernel_arg_shadow_table_object"
    assert shim_result.prep_execution_dry_run_ok is True
    assert shim_result.prep_execution_dry_run_row_count == 2
    assert shim_result.prep_execution_dry_run_column_count == len(
        PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
    )

    assert (
        shim_result.prep_execution_dry_run_schema_hash
        == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    )
    assert shim_result.prep_execution_dry_run_object_hash == table_object.object_hash
    assert shim_result.prep_execution_dry_run_lifecycle_ok is True
    assert shim_result.prep_execution_dry_run_row_handle_parity_ok_count == 2
    assert shim_result.prep_execution_dry_run_descriptor_ptr_parity_ok_count == 2
    assert (
        shim_result.prep_execution_dry_run_packed_weight_descriptor_parity_ok_count
        == 2
    )
    assert shim_result.prep_execution_dry_run_scale_metadata_handle_parity_ok_count == 2
    assert shim_result.prep_execution_dry_run_aux_metadata_handle_parity_ok_count == 2
    assert shim_result.prep_execution_dry_run_row_handle_miss_count == 0
    assert shim_result.prep_execution_dry_run_handle_field_read_count == 8
    assert (
        shim_result.prep_execution_dry_run_required_handle_field_available_count
        == 6
    )
    assert (
        shim_result.prep_execution_dry_run_optional_handle_field_available_count
        == 0
    )
    assert shim_result.prep_execution_dry_run_descriptor_ptr_field_read_count == 2
    assert (
        shim_result.prep_execution_dry_run_packed_weight_descriptor_field_read_count
        == 2
    )
    assert shim_result.prep_execution_dry_run_scale_metadata_handle_field_read_count == 2
    assert shim_result.prep_execution_dry_run_aux_metadata_handle_field_read_count == 2
    assert shim_result.prep_execution_dry_run_descriptor_ptr_field_available_count == 2
    assert (
        shim_result.prep_execution_dry_run_packed_weight_descriptor_field_available_count
        == 2
    )
    assert (
        shim_result.prep_execution_dry_run_scale_metadata_handle_field_available_count
        == 2
    )
    assert shim_result.prep_execution_dry_run_aux_metadata_handle_field_available_count == 0
    assert shim_result.prep_execution_dry_run_passed_to_kernel is False
    assert shim_result.prep_execution_dry_run_payload_bytes == 0
    assert shim_result.payload_bytes == 0
    assert shim_result.ready_credit is False
    assert shim_result.changes_router is False
    assert shim_result.changes_descriptor_order is False
    assert shim_result.changes_kernel_launch_args is False
    assert table_result.execution_mode == "readonly_kernel_arg_shadow_table"
    assert table_result.row_order_source == "canonical_address_key_order"
    assert table_result.row_count == 2
    assert table_result.column_count == len(
        PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS
    )
    assert table_result.schema_hash == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    assert table_result.row_order_hash
    assert table_result.ordered_row_hash
    assert table_result.per_row_parity_ok_count == 2
    assert table_result.row_miss_count == 0
    assert table_result.stale_row_count == 0
    assert table_result.lifecycle_ok is True
    assert table_result.table_ok is True
    assert table_result.payload_bytes == 0
    assert table_result.ready_credit is False
    assert table_result.changes_router is False
    assert table_result.changes_descriptor_order is False
    assert table_result.changes_kernel_launch_args is False
    assert table_result.passed_to_kernel is False
    assert table_object.row_count == 2
    assert table_object.column_count == len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS)
    assert table_object.schema_hash == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    assert table_object.row_order_hash == table_result.row_order_hash
    assert table_object.ordered_row_hash == table_result.ordered_row_hash
    assert table_object.lifecycle_ok is True
    assert table_object.payload_bytes == 0
    assert table_object.passed_to_kernel is False
    mismatched_dry_run_result = replace(
        prep_dry_run_result,
        table_object_hash="different-table-object-hash",
    )
    mismatched_dry_run_shim_result = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
        kernel_arg_shadow_table_object=table_object,
        descriptor_address_prep_dry_run_result=mismatched_dry_run_result,
    )
    assert mismatched_dry_run_shim_result.prep_execution_dry_run_ok is True
    assert (
        mismatched_dry_run_shim_result.prep_execution_dry_run_object_hash
        == "different-table-object-hash"
    )
    assert mismatched_dry_run_shim_result.handle_table_consume_ok is False
    assert mismatched_dry_run_shim_result.shim_ok is False
    payload_table_object = replace(table_object, payload_bytes=16)
    payload_dry_run_result = manager.execute_descriptor_address_prep_dry_run_readonly(
        payload_table_object,
        read_result=read_result,
    )
    assert payload_dry_run_result.execution_ok is False
    assert payload_dry_run_result.lifecycle_ok is False
    assert payload_dry_run_result.row_handle_parity_ok_count == 2
    assert payload_dry_run_result.descriptor_ptr_parity_ok_count == 2
    assert payload_dry_run_result.payload_bytes == 16
    assert payload_dry_run_result.passed_to_kernel is False
    no_table_shim_result = manager.execute_descriptor_consumer_shim_readonly(
        read_result
    )
    assert no_table_shim_result.read_ok is True
    assert no_table_shim_result.handle_table_read_ok is None
    assert no_table_shim_result.handle_table_lifecycle_ok is None
    assert no_table_shim_result.handle_table_row_miss_count is None
    assert no_table_shim_result.handle_table_per_row_parity_ok_count is None
    assert no_table_shim_result.handle_table_passed_to_kernel is False
    assert no_table_shim_result.handle_table_consume_ok is None
    assert no_table_shim_result.handle_table_consume_row_count is None
    assert no_table_shim_result.handle_table_consume_mode is None
    assert no_table_shim_result.handle_table_consume_source is None
    assert no_table_shim_result.handle_table_consume_passed_to_kernel is False
    assert no_table_shim_result.handle_table_object_consumed is None
    assert no_table_shim_result.shim_ok is False
    object_only_shim_result = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_object=table_object,
    )
    assert object_only_shim_result.read_ok is True
    assert object_only_shim_result.handle_table_read_ok is None
    assert object_only_shim_result.handle_table_consume_ok is None
    assert object_only_shim_result.handle_table_object_consumed is None
    assert object_only_shim_result.handle_table_object_hash is None
    assert object_only_shim_result.handle_table_object_row_count is None
    assert object_only_shim_result.handle_table_object_lifecycle_ok is None
    assert object_only_shim_result.shim_ok is False
    reversed_table_result = manager.build_kernel_arg_shadow_table_readonly(
        list(reversed(keys)),
        read_result=read_result,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
    )
    assert reversed_table_result.row_order_hash != table_result.row_order_hash
    assert reversed_table_result.ordered_row_hash != table_result.ordered_row_hash

    partial_read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key={
            keys[0]: result.consumer_object_hash_by_address_key[keys[0]]
        },
    )
    assert partial_read_result.object_hit_count == 2
    assert partial_read_result.checked_object_count == 1
    assert partial_read_result.stale_object_count == 0
    assert partial_read_result.read_ok is True

    stale_read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key={keys[0]: "stale-object-hash"},
    )
    assert stale_read_result.object_hit_count == 2
    assert stale_read_result.object_miss_count == 0
    assert stale_read_result.checked_object_count == 1
    assert stale_read_result.stale_object_count == 1
    assert stale_read_result.read_ok is False

    (
        stale_table_result,
        stale_table_object,
    ) = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=stale_read_result,
        expected_object_hash_by_address_key={keys[0]: "stale-object-hash"},
    )
    stale_shim_result = manager.execute_descriptor_consumer_shim_readonly(
        stale_read_result,
        kernel_arg_shadow_table_result=stale_table_result,
        kernel_arg_shadow_table_object=stale_table_object,
    )
    assert stale_shim_result.read_ok is False
    assert stale_shim_result.handle_table_read_ok is False
    assert stale_shim_result.handle_table_lifecycle_ok is False
    assert stale_shim_result.handle_table_stale_row_count == 1
    assert stale_shim_result.handle_table_passed_to_kernel is False
    assert stale_shim_result.handle_table_consume_ok is False
    assert stale_shim_result.handle_table_consume_stale_row_count == 1
    assert stale_shim_result.handle_table_consume_passed_to_kernel is False
    assert stale_shim_result.handle_table_object_consumed is True
    assert stale_shim_result.handle_table_object_lifecycle_ok is True
    assert stale_shim_result.shim_ok is False
    assert stale_table_result.row_count == 2
    assert stale_table_result.row_miss_count == 0
    assert stale_table_result.stale_row_count == 1
    assert stale_table_result.lifecycle_ok is False
    assert stale_table_result.table_ok is False
    assert stale_table_result.payload_bytes == 0
    assert stale_table_result.changes_kernel_launch_args is False
    assert stale_table_result.passed_to_kernel is False


def test_future_wna16_typed_slot_content_cache_reuses_repeated_tables():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    prep_result = manager.execute_descriptor_prep_readonly(keys)
    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
    )
    _table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
    )

    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(top_k=8)
    device = torch.device("cpu")
    packages: list[dict[str, object]] = []
    for _ in range(3):
        package: dict[str, object] = {"table_object": table_object}
        assert _premap_attach_future_wna16_typed_slot_columns_to_package(
            package,
            device=device,
            stage="test",
            recorder=recorder,
        )
        packages.append(package)

    first_columns = packages[0]["future_wna16_typed_slot_device_columns"][str(device)]
    third_columns = packages[2]["future_wna16_typed_slot_device_columns"][str(device)]
    assert isinstance(first_columns, tuple)
    assert isinstance(third_columns, tuple)
    assert packages[0]["future_wna16_typed_slot_materialization_adapter"] == (
        "persistent_native_typed_slot_buffer"
    )
    assert packages[1]["future_wna16_typed_slot_materialization_adapter"] == (
        "persistent_native_typed_slot_buffer"
    )
    assert packages[2]["future_wna16_typed_slot_materialization_adapter"] == (
        "persistent_content_cache"
    )
    assert packages[2]["future_wna16_typed_slot_content_cache_hit"] is True
    assert len(recorder._premap_future_wna16_typed_slot_content_cache) == 1
    assert all(torch.equal(a, b) for a, b in zip(first_columns, third_columns, strict=True))

    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["future_wna16_typed_slot_producer_materialization_count"] == 3
    assert counters["future_wna16_typed_slot_native_row_fill_count"] == 2
    assert counters["future_wna16_typed_slot_native_row_fill_row_count"] == 4
    assert counters["future_wna16_typed_slot_content_cache_miss_count"] == 2
    assert counters["future_wna16_typed_slot_content_cache_cold_skip_count"] == 1
    assert counters["future_wna16_typed_slot_content_cache_store_count"] == 1
    assert counters["future_wna16_typed_slot_content_cache_store_row_count"] == 2
    assert counters["future_wna16_typed_slot_content_cache_hit_count"] == 1
    assert counters["future_wna16_typed_slot_content_cache_hit_row_count"] == 2
    assert counters["future_wna16_typed_slot_fallback_dict_extract_count"] == 0
    assert counters["future_wna16_typed_slot_fallback_tensor_materialization_count"] == 0


def test_future_wna16_typed_slot_content_seen_counts_are_bounded():
    def build_table(expert_id: int):
        plan = prepare_premap_address_plan(
            [
                ExpertPrefetchDescriptor(
                    0,
                    1,
                    int(expert_id),
                    2,
                    "transition_head",
                    0.95,
                ),
            ],
            descriptor_bytes=64,
        )
        manager = ControlledPremapAddressManager(capacity=4)
        manager.prepare(plan)
        keys = [record.address_key for record in plan.records]
        prep_result = manager.execute_descriptor_prep_readonly(keys)
        read_result = manager.read_descriptor_consumer_objects_readonly(
            keys,
            expected_object_hash_by_address_key=(
                prep_result.consumer_object_hash_by_address_key
            ),
        )
        _table_result, table_object = (
            manager.build_kernel_arg_shadow_table_object_readonly(
                keys,
                read_result=read_result,
                expected_object_hash_by_address_key=(
                    prep_result.consumer_object_hash_by_address_key
                ),
            )
        )
        return table_object

    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_premap_kernel_arg_handoff_typed_slot_content_cache_max_seen_entries=1,
    )
    device = torch.device("cpu")
    for expert_id in (3, 7, 11):
        package = {"table_object": build_table(expert_id)}
        assert _premap_attach_future_wna16_typed_slot_columns_to_package(
            package,
            device=device,
            stage="test",
            recorder=recorder,
        )

    counters = _premap_kernel_arg_live_mutation_counters()
    assert len(recorder._premap_future_wna16_typed_slot_content_seen_counts) == 1
    assert counters["future_wna16_typed_slot_content_cache_seen_eviction_count"] == 2
    assert counters["future_wna16_typed_slot_content_cache_cold_skip_count"] == 3


def test_future_wna16_typed_slot_content_cache_store_after_seen_is_configurable():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    prep_result = manager.execute_descriptor_prep_readonly(keys)
    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
    )
    _table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
    )

    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_premap_kernel_arg_handoff_typed_slot_content_cache_store_after_seen=1,
    )
    device = torch.device("cpu")
    packages: list[dict[str, object]] = []
    for _ in range(2):
        package: dict[str, object] = {"table_object": table_object}
        assert _premap_attach_future_wna16_typed_slot_columns_to_package(
            package,
            device=device,
            stage="test",
            recorder=recorder,
        )
        packages.append(package)

    assert packages[0]["future_wna16_typed_slot_materialization_adapter"] == (
        "persistent_native_typed_slot_buffer"
    )
    assert packages[1]["future_wna16_typed_slot_materialization_adapter"] == (
        "persistent_content_cache"
    )
    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["future_wna16_typed_slot_native_row_fill_count"] == 1
    assert counters["future_wna16_typed_slot_content_cache_store_count"] == 1
    assert counters["future_wna16_typed_slot_content_cache_cold_skip_count"] == 0
    assert counters["future_wna16_typed_slot_content_cache_hit_count"] == 1


def test_future_wna16_typed_slot_content_cache_can_be_disabled():
    plan = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    prep_result = manager.execute_descriptor_prep_readonly(keys)
    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
    )
    _table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=prep_result.consumer_object_hash_by_address_key,
    )

    _reset_premap_kernel_arg_live_mutation_counters()
    recorder = VllmRouterRecorder(
        top_k=8,
        shadow_premap_kernel_arg_handoff_typed_slot_content_cache_max_entries=0,
    )
    device = torch.device("cpu")
    for _ in range(2):
        package = {"table_object": table_object}
        assert _premap_attach_future_wna16_typed_slot_columns_to_package(
            package,
            device=device,
            stage="test",
            recorder=recorder,
        )
        assert package["future_wna16_typed_slot_materialization_adapter"] == (
            "persistent_native_typed_slot_buffer"
        )

    counters = _premap_kernel_arg_live_mutation_counters()
    assert counters["future_wna16_typed_slot_content_cache_disabled_count"] == 4
    assert counters["future_wna16_typed_slot_content_cache_hit_count"] == 0
    assert counters["future_wna16_typed_slot_content_cache_store_count"] == 0
    assert counters["future_wna16_typed_slot_native_row_fill_count"] == 2


def test_kernel_arg_handoff_mirror_hash_covers_slot_table_rows_and_args():
    mirror = PremapKernelArgHandoffMirrorObject(
        mode="readonly_kernel_arg_handoff_mirror",
        slot_hash="slot-a",
        table_object_hash="table-a",
        row_count=2,
        column_count=len(PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS),
        schema_hash=PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
        row_order_hash="row-order-a",
        ordered_row_hash="ordered-row-a",
        descriptor_ptr_arg_hash="descriptor-arg-a",
        packed_weight_descriptor_arg_hash="packed-arg-a",
        scale_metadata_handle_arg_hash="scale-arg-a",
        aux_metadata_handle_arg_hash="aux-arg-a",
        required_source_hit_count=6,
        required_source_miss_count=0,
        optional_source_hit_count=1,
        optional_source_miss_count=1,
    )

    assert mirror.ready is True
    base_hash = mirror.mirror_hash

    for field_name, value in [
        ("slot_hash", "slot-b"),
        ("table_object_hash", "table-b"),
        ("row_order_hash", "row-order-b"),
        ("ordered_row_hash", "ordered-row-b"),
        ("descriptor_ptr_arg_hash", "descriptor-arg-b"),
        ("packed_weight_descriptor_arg_hash", "packed-arg-b"),
        ("scale_metadata_handle_arg_hash", "scale-arg-b"),
        ("aux_metadata_handle_arg_hash", "aux-arg-b"),
    ]:
        assert replace(mirror, **{field_name: value}).mirror_hash != base_hash

    assert replace(mirror, passed_to_kernel=True).ready is False
    assert replace(mirror, changes_kernel_launch_args=True).ready is False
    assert replace(mirror, payload_bytes=1).ready is False


def test_controlled_premap_address_manager_descriptor_prep_uses_real_handles():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    real_handles = {
        key: PremapRealDescriptorHandle(
            expert_id=record.expert_id,
            local_expert_id=record.expert_id,
            handle_hash=f"real-hash-{record.expert_id}",
            packed_weight_descriptor=f"real-packed-{record.expert_id}",
            scale_metadata_handle=f"real-scale-{record.expert_id}",
            payload_bytes=0,
        )
        for key, record in zip(keys, plan.records, strict=True)
    }

    result = manager.execute_descriptor_prep_readonly(
        keys,
        real_descriptor_handles_by_address_key=real_handles,
    )

    assert result.lookup_count == 2
    assert result.prepared_handle_count == 2
    assert result.missing_handle_count == 0
    assert result.descriptor_ptr_count == 2
    assert result.packed_weight_descriptor_count == 2
    assert result.scale_metadata_handle_count == 2
    assert result.real_descriptor_handle_count == 2
    assert result.real_descriptor_handle_miss_count == 0
    assert result.real_descriptor_handle_backed is True
    assert result.real_descriptor_handle_hash
    assert result.consumer_object_count == 2
    assert result.consumer_object_hash
    assert len(result.consumer_object_hash_by_address_key) == 2
    assert result.payload_bytes == 0
    assert result.ready_credit is False
    assert result.changes_router is False
    assert result.changes_descriptor_order is False
    assert result.execution_ok is True

    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
        real_descriptor_handles_by_address_key=real_handles,
    )
    assert read_result.lookup_count == 2
    assert read_result.object_hit_count == 2
    assert read_result.object_miss_count == 0
    assert read_result.stale_object_count == 0
    assert read_result.object_hash == result.consumer_object_hash
    assert read_result.read_ok is True


def test_controlled_premap_address_manager_builds_wna16_adjacent_typed_slot():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    result = manager.execute_descriptor_prep_readonly(keys)
    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
    )
    _table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
    )

    slot = manager.build_wna16_adjacent_typed_slot_readonly(table_object)
    slot_dict = slot.as_dict()

    assert slot.name == PREMAP_WNA16_ADJACENT_TYPED_SLOT_NAME
    assert slot.mode == PREMAP_WNA16_ADJACENT_TYPED_SLOT_MODE
    assert slot.source == PREMAP_WNA16_ADJACENT_TYPED_SLOT_SOURCE
    assert slot.checked is True
    assert slot.ready is True
    assert slot.input_hash
    assert slot.table_object_hash == table_object.object_hash
    assert slot.schema_hash == PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH
    assert slot.row_count == 2
    assert slot.row_ok_count == 2
    assert slot.error_count == 0
    assert slot.all_handle_fields_read is True
    assert slot.packet_chain_depth == PREMAP_WNA16_ADJACENT_TYPED_SLOT_PACKET_CHAIN_DEPTH
    assert slot.field_mask == PREMAP_WNA16_ADJACENT_TYPED_SLOT_FIELD_MASK
    assert slot.descriptor_ptr_read_row_ok_count == 2
    assert slot.packed_weight_descriptor_read_row_ok_count == 2
    assert slot.scale_metadata_handle_read_row_ok_count == 2
    assert slot.aux_metadata_handle_read_row_ok_count == 2
    assert slot.expert_id_read_row_ok_count == 2
    assert slot.address_key_hash_read_row_ok_count == 2
    assert slot.row_metadata_read_row_ok_count == 2
    assert slot.row_hash_accumulator
    assert slot.field_read_hash_accumulator
    assert slot.row_metadata_hash_accumulator
    assert len(slot.failures) == 0
    assert slot.failures == ()
    assert slot.payload_bytes == 0
    assert slot.passed_to_kernel is False
    assert slot.changes_kernel_launch_args is False
    assert slot.current_wna16_arg_compatible is False
    assert slot.requires_wna16_arg_reinterpretation is False
    assert slot.explicit_typed_abi_slot is True
    assert slot.reuses_current_wna16_arg_slot is False
    assert slot_dict["ready"] is True
    assert slot_dict["failure_count"] == 0
    assert slot_dict["explicit_typed_abi_slot"] is True
    assert slot_dict["current_wna16_arg_compatible"] is False


def test_controlled_premap_address_manager_descriptor_prep_fails_on_missing_real_handle():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    real_handles = {
        keys[0]: PremapRealDescriptorHandle(
            expert_id=plan.records[0].expert_id,
            local_expert_id=plan.records[0].expert_id,
            handle_hash="real-hash-only",
            packed_weight_descriptor="real-packed-only",
            scale_metadata_handle="real-scale-only",
            payload_bytes=0,
        )
    }

    result = manager.execute_descriptor_prep_readonly(
        keys,
        real_descriptor_handles_by_address_key=real_handles,
    )

    assert result.lookup_count == 2
    assert result.prepared_handle_count == 1
    assert result.missing_handle_count == 0
    assert result.real_descriptor_handle_count == 1
    assert result.real_descriptor_handle_miss_count == 1
    assert result.real_descriptor_handle_backed is True
    assert result.consumer_object_count == 1
    assert result.consumer_object_hash
    assert len(result.consumer_object_hash_by_address_key) == 1
    assert result.payload_bytes == 0
    assert result.ready_credit is False
    assert result.changes_router is False
    assert result.changes_descriptor_order is False
    assert result.execution_ok is False

    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
        real_descriptor_handles_by_address_key=real_handles,
    )
    assert read_result.object_hit_count == 1
    assert read_result.object_miss_count == 1
    assert read_result.read_ok is False


def test_controlled_premap_address_manager_descriptor_prep_rejects_mismatched_real_address_key():
    plan = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    key = plan.records[0].address_key
    real_handles = {
        key: PremapRealDescriptorHandle(
            expert_id=3,
            local_expert_id=3,
            handle_hash="real-hash-wrong-address",
            address_key="different-address-key",
            packed_weight_descriptor="real-packed",
            scale_metadata_handle="real-scale",
            payload_bytes=0,
        )
    }

    result = manager.execute_descriptor_prep_readonly(
        [key],
        real_descriptor_handles_by_address_key=real_handles,
    )

    assert result.lookup_count == 1
    assert result.prepared_handle_count == 0
    assert result.missing_handle_count == 0
    assert result.real_descriptor_handle_count == 0
    assert result.real_descriptor_handle_miss_count == 1
    assert result.real_descriptor_handle_backed is True
    assert result.consumer_object_count == 0
    assert result.consumer_object_hash is None
    assert result.payload_bytes == 0
    assert result.ready_credit is False
    assert result.changes_router is False
    assert result.changes_descriptor_order is False


def test_kernel_arg_shadow_table_native_input_exports_optional_aux_when_present():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    real_handles = {
        key: PremapRealDescriptorHandle(
            expert_id=record.expert_id,
            local_expert_id=record.expert_id,
            handle_hash=f"real-hash-{record.expert_id}",
            address_key=key,
            packed_weight_descriptor=f"real-packed-{record.expert_id}",
            scale_metadata_handle=f"real-scale-{record.expert_id}",
            aux_metadata_handle=f"aux-handle-{record.expert_id}",
            payload_bytes=0,
        )
        for key, record in zip(keys, plan.records, strict=True)
    }

    result = manager.execute_descriptor_prep_readonly(
        keys,
        real_descriptor_handles_by_address_key=real_handles,
    )
    read_result = manager.read_descriptor_consumer_objects_readonly(
        keys,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
        real_descriptor_handles_by_address_key=real_handles,
    )
    _table_result, table_object = manager.build_kernel_arg_shadow_table_object_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
        real_descriptor_handles_by_address_key=real_handles,
    )

    native_input = table_object.to_native_typed_consumer_input_dict()

    assert native_input["expert_id"] == [3, 7]
    assert len(native_input["aux_metadata_handle"]) == 2
    assert all(value != 0 for value in native_input["aux_metadata_handle"])
    assert native_input["aux_metadata_handle"][0] != native_input["aux_metadata_handle"][1]
    assert native_input["_meta"]["payload_bytes"] == 0
    assert native_input["_meta"]["passed_to_kernel"] is False
    direct_columns = [[0, 0], [0, 0], [0, 0], [0, 0]]
    copied = table_object.copy_native_typed_consumer_columns_to(
        tuple(direct_columns)
    )
    assert copied == 2
    assert direct_columns[3] == native_input["aux_metadata_handle"]
    assert result.execution_ok is True


def test_controlled_premap_address_manager_descriptor_prep_rejects_real_payload():
    plan = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    key = plan.records[0].address_key
    real_handles = {
        key: PremapRealDescriptorHandle(
            expert_id=3,
            local_expert_id=3,
            handle_hash="real-hash-with-payload",
            packed_weight_descriptor="real-packed",
            scale_metadata_handle="real-scale",
            payload_bytes=16,
        )
    }

    result = manager.execute_descriptor_prep_readonly(
        [key],
        real_descriptor_handles_by_address_key=real_handles,
    )

    assert result.real_descriptor_handle_backed is True
    assert result.real_descriptor_handle_count == 1
    assert result.real_descriptor_handle_miss_count == 0
    assert result.payload_bytes == 16
    assert result.consumer_object_count == 0
    assert result.consumer_object_hash is None
    assert result.ready_credit is False
    assert result.changes_router is False
    assert result.changes_descriptor_order is False
    assert result.execution_ok is False


def test_controlled_premap_address_manager_descriptor_prep_rejects_incomplete_real_handle():
    plan = prepare_premap_address_plan(
        [
            ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
            ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=4)
    manager.prepare(plan)
    keys = [record.address_key for record in plan.records]
    real_handles = {
        keys[0]: PremapRealDescriptorHandle(
            expert_id=3,
            local_expert_id=3,
            handle_hash="real-hash-complete",
            packed_weight_descriptor="real-packed-complete",
            scale_metadata_handle="real-scale-complete",
            payload_bytes=0,
        ),
        keys[1]: PremapRealDescriptorHandle(
            expert_id=7,
            local_expert_id=7,
            handle_hash="real-hash-missing-scale",
            packed_weight_descriptor="real-packed-missing-scale",
            scale_metadata_handle=None,
            payload_bytes=0,
        ),
    }

    result = manager.execute_descriptor_prep_readonly(
        keys,
        real_descriptor_handles_by_address_key=real_handles,
    )

    assert result.lookup_count == 2
    assert result.prepared_handle_count == 2
    assert result.real_descriptor_handle_count == 2
    assert result.real_descriptor_handle_miss_count == 0
    assert result.packed_weight_descriptor_count == 2
    assert result.scale_metadata_handle_count == 1
    assert result.payload_bytes == 0
    assert result.consumer_object_count == 1
    assert result.consumer_object_hash
    assert result.ready_credit is False
    assert result.changes_router is False
    assert result.changes_descriptor_order is False
    assert result.execution_ok is False


def test_controlled_premap_address_manager_descriptor_prep_hash_includes_address_key():
    first = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
        address_namespace="first_namespace",
    )
    second = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
        address_namespace="second_namespace",
    )
    first_manager = ControlledPremapAddressManager(capacity=4)
    second_manager = ControlledPremapAddressManager(capacity=4)
    first_manager.prepare(first)
    second_manager.prepare(second)

    first_result = first_manager.execute_descriptor_prep_readonly(
        [record.address_key for record in first.records]
    )
    second_result = second_manager.execute_descriptor_prep_readonly(
        [record.address_key for record in second.records]
    )

    assert first.records[0].address_key != second.records[0].address_key
    assert first_result.handle_hash
    assert second_result.handle_hash
    assert first_result.handle_hash != second_result.handle_hash


def test_controlled_premap_address_manager_zero_capacity_counts_requests_only():
    plan = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    manager = ControlledPremapAddressManager(capacity=0)

    snapshot = manager.prepare(plan)

    assert snapshot.prepared_plan_count == 1
    assert snapshot.prepared_record_count == 1
    assert snapshot.new_address_count == 1
    assert snapshot.reused_address_count == 0
    assert snapshot.resident_address_count == 0
    assert snapshot.evicted_address_count == 1
    assert snapshot.prepared_descriptor_actual_bytes == 64
    assert snapshot.resident_descriptor_bytes == 0
    assert snapshot.payload_bytes == 0


def test_controlled_premap_address_manager_refreshes_reused_descriptor_bytes():
    small = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=64,
    )
    large = prepare_premap_address_plan(
        [ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95)],
        descriptor_bytes=128,
    )
    manager = ControlledPremapAddressManager(capacity=4)

    manager.prepare(small)
    snapshot = manager.prepare(large)

    assert snapshot.new_address_count == 1
    assert snapshot.reused_address_count == 1
    assert snapshot.prepared_descriptor_actual_bytes == 192
    assert snapshot.resident_descriptor_bytes == 128
    assert snapshot.payload_bytes == 0
