from __future__ import annotations

import pytest
import torch

from mtp_expert_prefetch.runtime import (
    ControlledPremapAddressManager,
    ExpertPrefetchDescriptor,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_COLUMNS,
    PREMAP_DESCRIPTOR_CONSUMER_HANDLE_TABLE_SCHEMA_HASH,
    PremapRealDescriptorHandle,
    build_premap_descriptors,
    build_priority_masks,
    descriptor_summary,
    prepare_premap_address_plan,
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

    table_result = manager.build_kernel_arg_shadow_table_readonly(
        keys,
        read_result=read_result,
        expected_object_hash_by_address_key=result.consumer_object_hash_by_address_key,
    )
    shim_result = manager.execute_descriptor_consumer_shim_readonly(
        read_result,
        kernel_arg_shadow_table_result=table_result,
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
    assert shim_result.handle_table_consume_row_miss_count == 0
    assert shim_result.handle_table_consume_stale_row_count == 0
    assert shim_result.handle_table_consume_passed_to_kernel is False
    assert shim_result.handle_table_consume_payload_bytes == 0
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
    assert no_table_shim_result.handle_table_consume_passed_to_kernel is False
    assert no_table_shim_result.shim_ok is False
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

    stale_table_result = manager.build_kernel_arg_shadow_table_readonly(
        keys,
        read_result=stale_read_result,
        expected_object_hash_by_address_key={keys[0]: "stale-object-hash"},
    )
    stale_shim_result = manager.execute_descriptor_consumer_shim_readonly(
        stale_read_result,
        kernel_arg_shadow_table_result=stale_table_result,
    )
    assert stale_shim_result.read_ok is False
    assert stale_shim_result.handle_table_read_ok is False
    assert stale_shim_result.handle_table_lifecycle_ok is False
    assert stale_shim_result.handle_table_stale_row_count == 1
    assert stale_shim_result.handle_table_passed_to_kernel is False
    assert stale_shim_result.handle_table_consume_ok is False
    assert stale_shim_result.handle_table_consume_stale_row_count == 1
    assert stale_shim_result.handle_table_consume_passed_to_kernel is False
    assert stale_shim_result.shim_ok is False
    assert stale_table_result.row_count == 2
    assert stale_table_result.row_miss_count == 0
    assert stale_table_result.stale_row_count == 1
    assert stale_table_result.lifecycle_ok is False
    assert stale_table_result.table_ok is False
    assert stale_table_result.payload_bytes == 0
    assert stale_table_result.changes_kernel_launch_args is False
    assert stale_table_result.passed_to_kernel is False


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
    assert result.execution_ok is False


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
