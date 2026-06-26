from __future__ import annotations

import pytest

from mtp_expert_prefetch.runtime import (
    ControlledExpertCacheManager,
    PayloadCacheRuntimeAdapterAccountingDryRun,
    PayloadCacheRuntimeAdapterAccountingDryRunSnapshot,
    PayloadCacheRuntimeAdapterPayloadlessLive,
    PayloadCacheRuntimeDemandHitShadowPublication,
    PayloadCacheRuntimePayloadTransferToggle,
    PayloadCacheRuntimePayloadTransferToggleSnapshot,
    PayloadCacheRuntimePayloadIssueRequest,
    PayloadCacheRuntimeAdapterShell,
    PayloadCacheRuntimeAdapterShellSnapshot,
    ReadyTimeExpertCacheManager,
    build_payload_cache_demand_hit_shadow_publication,
)


def test_controlled_cache_manager_tracks_prefetch_use_and_miss() -> None:
    manager = ControlledExpertCacheManager(capacity=2)

    assert manager.issue_prefetch(0, 1) is True
    assert manager.issue_prefetch(0, 1) is False
    assert manager.demand(0, 1) is True
    assert manager.demand(0, 2) is False

    snapshot = manager.snapshot()
    assert snapshot.issued_fetch_count == 1
    assert snapshot.used_fetch_count == 1
    assert snapshot.demand_count == 2
    assert snapshot.demand_hit_count == 1
    assert snapshot.demand_miss_count == 1
    assert snapshot.unused_fetch_count == 0


def test_controlled_cache_manager_counts_evicted_unused_prefetches() -> None:
    manager = ControlledExpertCacheManager(capacity=1)

    manager.issue_prefetch(0, 1)
    manager.issue_prefetch(0, 2)
    manager.demand(0, 1)

    snapshot = manager.snapshot()
    assert snapshot.issued_fetch_count == 2
    assert snapshot.evicted_before_use_count == 2
    assert snapshot.demand_miss_count == 1
    assert snapshot.used_fetch_count == 0


def test_controlled_cache_manager_capacity_zero_drops_prefetches() -> None:
    manager = ControlledExpertCacheManager(capacity=0)

    manager.issue_prefetch(0, 1)
    manager.demand(0, 1)

    snapshot = manager.snapshot()
    assert snapshot.resident_count == 0
    assert snapshot.issued_fetch_count == 1
    assert snapshot.evicted_before_use_count == 1
    assert snapshot.demand_miss_count == 1


def test_ready_time_cache_manager_hits_only_after_ready_before_deadline() -> None:
    manager = ReadyTimeExpertCacheManager(
        capacity=2,
        service_us_per_issue=2.0,
        queue_batch_size=1,
        queue_deadline_us=5.0,
    )

    assert manager.issue_prefetch(0, 1, arrival_us=0.0) is True
    assert manager.demand(0, 1, arrival_us=0.0) is True

    snapshot = manager.snapshot()
    assert snapshot.issued_fetch_count == 1
    assert snapshot.used_fetch_count == 1
    assert snapshot.demand_hit_count == 1
    assert snapshot.ready_late_miss_count == 0
    assert snapshot.queue_batch_count == 1
    assert snapshot.queue_service_us == 2.0


def test_ready_time_cache_manager_counts_late_inflight_miss() -> None:
    manager = ReadyTimeExpertCacheManager(
        capacity=2,
        service_us_per_issue=10.0,
        queue_batch_size=1,
        queue_deadline_us=5.0,
    )

    assert manager.issue_prefetch(0, 1, arrival_us=0.0) is True
    assert manager.demand(0, 1, arrival_us=0.0) is False
    manager.finish()

    snapshot = manager.snapshot()
    assert snapshot.issued_fetch_count == 1
    assert snapshot.used_fetch_count == 0
    assert snapshot.demand_miss_count == 1
    assert snapshot.ready_late_miss_count == 1
    assert snapshot.late_completion_unused_count == 1
    assert snapshot.unused_fetch_count == 1


def test_ready_time_cache_manager_deduplicates_resident_and_inflight_issue() -> None:
    manager = ReadyTimeExpertCacheManager(
        capacity=2,
        service_us_per_issue=10.0,
        queue_batch_size=1,
        queue_deadline_us=5.0,
    )

    assert manager.issue_prefetch(0, 1, arrival_us=0.0) is True
    assert manager.issue_prefetch(0, 1, arrival_us=1.0) is False
    manager.advance_to(20.0)
    assert manager.issue_prefetch(0, 1, arrival_us=20.0) is False

    snapshot = manager.snapshot()
    assert snapshot.issued_fetch_count == 1
    assert snapshot.resident_count == 1


def test_ready_time_cache_manager_capacity_zero_drops_ready_prefetches() -> None:
    manager = ReadyTimeExpertCacheManager(
        capacity=0,
        service_us_per_issue=1.0,
        queue_batch_size=1,
        queue_deadline_us=5.0,
    )

    assert manager.issue_prefetch(0, 1, arrival_us=0.0) is True
    manager.finish()

    snapshot = manager.snapshot()
    assert snapshot.resident_count == 0
    assert snapshot.issued_fetch_count == 1
    assert snapshot.evicted_before_use_count == 1


def test_ready_time_cache_manager_underfilled_batch_flushes_at_deadline() -> None:
    manager = ReadyTimeExpertCacheManager(
        capacity=2,
        service_us_per_issue=1.0,
        queue_batch_size=2,
        queue_deadline_us=5.0,
    )

    assert manager.issue_prefetch(0, 1, arrival_us=0.0) is True
    assert manager.demand(0, 1, arrival_us=0.0) is False
    manager.finish()

    snapshot = manager.snapshot()
    assert snapshot.queue_batch_count == 1
    assert snapshot.queue_service_us == 1.0
    assert snapshot.queue_total_span_us == 6.0
    assert snapshot.demand_miss_count == 1
    assert snapshot.ready_late_miss_count == 1
    assert snapshot.late_completion_unused_count == 1


def test_payload_cache_runtime_adapter_shell_constructs_disabled_manager() -> None:
    shell = PayloadCacheRuntimeAdapterShell(
        capacity=4096,
        service_us_per_issue=3.0,
        service_us_per_batch=7.0,
        queue_batch_size=8,
        queue_deadline_us=100.0,
    )

    snapshot = shell.snapshot()
    payload = snapshot.as_dict()

    assert payload["present"] is True
    assert payload["enabled"] is False
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["capacity"] == 4096
    assert payload["queue_batch_size"] == 8
    assert payload["queue_deadline_us"] == 100.0
    assert payload["service_us_per_issue"] == 3.0
    assert payload["service_us_per_batch"] == 7.0
    for key in (
        "resident_count",
        "issued_fetch_count",
        "used_fetch_count",
        "demand_count",
        "demand_hit_count",
        "demand_miss_count",
        "ready_late_miss_count",
        "issued_payload_count",
        "payload_bytes",
    ):
        assert payload[key] == 0
    for key in (
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "adapter_instance_created",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False
    assert not hasattr(shell, "manager")


def test_payload_cache_runtime_adapter_shell_rejects_live_side_effects() -> None:
    with pytest.raises(ValueError, match="disabled"):
        PayloadCacheRuntimeAdapterShell(capacity=4096, enabled=True)

    shell = PayloadCacheRuntimeAdapterShell(capacity=4096)
    with pytest.raises(RuntimeError, match="disabled"):
        shell.issue_prefetch(0, 1, arrival_us=0.0)
    with pytest.raises(RuntimeError, match="disabled"):
        shell.demand(0, 1, arrival_us=0.0)

    with pytest.raises(ValueError, match="disabled"):
        PayloadCacheRuntimeAdapterShellSnapshot(
            present=True,
            enabled=True,
            manager_backend="ReadyTimeExpertCacheManager",
            manager_contract="ready_time_issue_demand_skeleton_v1",
            capacity=4096,
            queue_batch_size=1,
            queue_deadline_us=0.0,
            service_us_per_issue=0.0,
            service_us_per_batch=0.0,
            resident_count=0,
            issued_fetch_count=0,
            used_fetch_count=0,
            demand_count=0,
            demand_hit_count=0,
            demand_miss_count=0,
            ready_late_miss_count=0,
        )

    with pytest.raises(ValueError, match="payload_deref_allowed"):
        PayloadCacheRuntimeAdapterShellSnapshot(
            present=True,
            enabled=False,
            manager_backend="ReadyTimeExpertCacheManager",
            manager_contract="ready_time_issue_demand_skeleton_v1",
            capacity=4096,
            queue_batch_size=1,
            queue_deadline_us=0.0,
            service_us_per_issue=0.0,
            service_us_per_batch=0.0,
            resident_count=0,
            issued_fetch_count=0,
            used_fetch_count=0,
            demand_count=0,
            demand_hit_count=0,
            demand_miss_count=0,
            ready_late_miss_count=0,
            payload_deref_allowed=True,
        )


def test_payload_cache_runtime_adapter_accounting_dry_run_tracks_manager_only() -> None:
    adapter = PayloadCacheRuntimeAdapterAccountingDryRun(
        capacity=4096,
        service_us_per_issue=0.0,
        service_us_per_batch=0.0,
        queue_batch_size=1,
        queue_deadline_us=100.0,
    )

    assert adapter.issue_prefetch(3, 7, arrival_us=0.0) is True
    assert adapter.issue_prefetch(3, 7, arrival_us=1.0) is False
    assert adapter.demand(3, 7, arrival_us=2.0) is True
    snapshot = adapter.snapshot()
    payload = snapshot.as_dict()

    assert payload["present"] is True
    assert payload["accounting_dry_run_enabled"] is True
    assert payload["manager_backend"] == "ReadyTimeExpertCacheManager"
    assert payload["manager_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["capacity"] == 4096
    assert payload["queue_batch_size"] == 1
    assert payload["queue_deadline_us"] == 100.0
    assert payload["resident_count"] == 1
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["unused_fetch_count"] == 0
    assert payload["demand_count"] == 1
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 0
    assert payload["ready_late_miss_count"] == 0
    assert payload["queue_batch_count"] == 1
    for key in ("issued_payload_count", "payload_bytes"):
        assert payload[key] == 0
    for key in (
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False


def test_payload_cache_runtime_adapter_accounting_dry_run_snapshot_rejects_side_effects() -> None:
    base_kwargs = {
        "present": True,
        "accounting_dry_run_enabled": True,
        "manager_backend": "ReadyTimeExpertCacheManager",
        "manager_contract": "ready_time_issue_demand_skeleton_v1",
        "capacity": 4096,
        "queue_batch_size": 1,
        "queue_deadline_us": 100.0,
        "service_us_per_issue": 0.0,
        "service_us_per_batch": 0.0,
        "resident_count": 1,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "demand_count": 1,
        "demand_hit_count": 1,
        "demand_miss_count": 0,
        "evicted_before_use_count": 0,
        "ready_late_miss_count": 0,
        "late_completion_unused_count": 0,
        "queue_batch_count": 1,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
        "queue_wait_us": 0.0,
        "queue_max_delay_us": 0.0,
    }

    with pytest.raises(ValueError, match="enabled"):
        PayloadCacheRuntimeAdapterAccountingDryRunSnapshot(
            **{
                **base_kwargs,
                "accounting_dry_run_enabled": False,
            },
        )

    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheRuntimeAdapterAccountingDryRunSnapshot(
            **{
                **base_kwargs,
                "payload_bytes": 1,
            },
        )

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "uses_current_wna16_args",
        "measures_tpot",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheRuntimeAdapterAccountingDryRunSnapshot(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )

    for field_name, bad_value in (
        ("queue_deadline_us", float("nan")),
        ("service_us_per_issue", float("inf")),
        ("queue_service_us", float("nan")),
        ("queue_total_span_us", float("inf")),
    ):
        with pytest.raises(ValueError, match=f"{field_name}.*finite"):
            PayloadCacheRuntimeAdapterAccountingDryRunSnapshot(
                **{
                    **base_kwargs,
                    field_name: bad_value,
                },
            )


def test_payload_cache_runtime_adapter_payloadless_live_tracks_hit_and_miss() -> None:
    adapter = PayloadCacheRuntimeAdapterPayloadlessLive(
        capacity=4096,
        queue_batch_size=1,
        queue_deadline_us=100.0,
    )

    assert adapter.payloadless_live_enabled is True
    assert adapter.payload_transfer_enabled is False
    assert adapter.kernel_arg_pass_allowed is False
    assert adapter.issue_prefetch(0, 0, arrival_us=0.0) is True
    assert adapter.issue_prefetch(0, 0, arrival_us=1.0) is False
    assert adapter.demand(0, 0, arrival_us=2.0) is True
    assert adapter.demand(0, 1, arrival_us=3.0) is False

    snapshot = adapter.snapshot()
    payload = snapshot.as_dict()

    assert payload["accounting_dry_run_enabled"] is True
    assert payload["resident_count"] == 2
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["unused_fetch_count"] == 0
    assert payload["demand_count"] == 2
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 1
    assert payload["queue_batch_count"] == 1
    assert payload["payload_bytes"] == 0
    assert payload["issued_payload_count"] == 0
    for key in (
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False


def test_payload_cache_demand_hit_shadow_publication_from_payloadless_live() -> None:
    adapter = PayloadCacheRuntimeAdapterPayloadlessLive(
        capacity=4096,
        queue_batch_size=1,
        queue_deadline_us=100.0,
    )

    assert adapter.issue_prefetch(0, 0, arrival_us=0.0) is True
    assert adapter.demand(0, 0, arrival_us=2.0) is True
    assert adapter.demand(0, 1, arrival_us=3.0) is False

    publication = build_payload_cache_demand_hit_shadow_publication(adapter.snapshot())
    payload = publication.as_dict()

    assert payload["present"] is True
    assert payload["publication_schema"] == "payload_cache_demand_hit_shadow_publication_v1"
    assert payload["publication_scope"] == "shadow_only"
    assert payload["source_manager_contract"] == "ready_time_issue_demand_skeleton_v1"
    assert payload["demand_hit_shadow_publication_allowed"] is True
    assert payload["demand_hit_published_to_shadow"] is True
    assert payload["consumer_visible_payload_hit"] is False
    assert payload["demand_count"] == 2
    assert payload["demand_hit_count"] == 1
    assert payload["demand_miss_count"] == 1
    assert payload["demand_hit_rate"] == 0.5
    assert payload["issued_fetch_count"] == 1
    assert payload["used_fetch_count"] == 1
    assert payload["payload_bytes"] == 0
    assert payload["demand_hit_payload_bytes"] == 0
    for key in (
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "payload_deref_attempted",
        "payload_handle_deref_attempted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False


def test_payload_cache_demand_hit_shadow_publication_rejects_side_effects() -> None:
    base = {
        "present": True,
        "publication_schema": "payload_cache_demand_hit_shadow_publication_v1",
        "publication_scope": "shadow_only",
        "source_manager_contract": "ready_time_issue_demand_skeleton_v1",
        "source_accounting_dry_run_enabled": True,
        "demand_hit_shadow_publication_allowed": True,
        "demand_hit_published_to_shadow": True,
        "consumer_visible_payload_hit": False,
        "demand_count": 2,
        "demand_hit_count": 1,
        "demand_miss_count": 1,
        "ready_late_miss_count": 0,
        "issued_fetch_count": 1,
        "used_fetch_count": 1,
        "unused_fetch_count": 0,
        "resident_count": 2,
        "queue_batch_count": 1,
        "queue_service_us": 0.0,
        "queue_total_span_us": 0.0,
    }

    with pytest.raises(ValueError, match="shadow-only"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "publication_scope": "consumer_visible"},
        )
    with pytest.raises(ValueError, match="consumer-visible"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "consumer_visible_payload_hit": True},
        )
    with pytest.raises(ValueError, match="payload_bytes"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "payload_bytes": 1},
        )
    with pytest.raises(ValueError, match="ready_credit"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "ready_credit": True},
        )
    with pytest.raises(ValueError, match="payload_deref_attempted"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "payload_deref_attempted": True},
        )
    with pytest.raises(ValueError, match="payload_handle_deref_attempted"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "payload_handle_deref_attempted": True},
        )
    with pytest.raises(ValueError, match="kernel_arg_pass_allowed"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "kernel_arg_pass_allowed": True},
        )
    with pytest.raises(ValueError, match="close over demand_count"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "demand_miss_count": 2},
        )
    with pytest.raises(ValueError, match="queue_service_us.*finite"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "queue_service_us": float("nan")},
        )
    with pytest.raises(ValueError, match="queue_total_span_us.*finite"):
        PayloadCacheRuntimeDemandHitShadowPublication(
            **{**base, "queue_total_span_us": float("inf")},
        )


def test_payload_cache_demand_hit_shadow_publication_rejects_mutated_source() -> None:
    def build_snapshot():
        adapter = PayloadCacheRuntimeAdapterPayloadlessLive(
            capacity=4096,
            queue_batch_size=1,
            queue_deadline_us=100.0,
        )
        adapter.issue_prefetch(0, 0, arrival_us=0.0)
        adapter.demand(0, 0, arrival_us=2.0)
        return adapter.snapshot()

    snapshot = build_snapshot()
    object.__setattr__(snapshot, "payload_bytes", 1)
    with pytest.raises(ValueError, match="source snapshot payload_bytes"):
        build_payload_cache_demand_hit_shadow_publication(snapshot)

    snapshot = build_snapshot()
    object.__setattr__(snapshot, "manager_backend", "OtherManager")
    with pytest.raises(ValueError, match="source manager backend"):
        build_payload_cache_demand_hit_shadow_publication(snapshot)

    for field_name in (
        "ready_credit",
        "kernel_arg_pass_allowed",
        "payload_deref_allowed",
    ):
        snapshot = build_snapshot()
        object.__setattr__(snapshot, field_name, True)
        with pytest.raises(ValueError, match=f"source snapshot {field_name}"):
            build_payload_cache_demand_hit_shadow_publication(snapshot)

    for field_name, bad_value, error in (
        ("demand_count", "2", TypeError),
        ("demand_hit_count", True, TypeError),
        ("issued_fetch_count", 1.5, TypeError),
        ("queue_service_us", "0.0", TypeError),
        ("queue_total_span_us", float("nan"), ValueError),
        ("queue_wait_us", float("inf"), ValueError),
    ):
        snapshot = build_snapshot()
        object.__setattr__(snapshot, field_name, bad_value)
        with pytest.raises(error, match=f"source snapshot {field_name}"):
            build_payload_cache_demand_hit_shadow_publication(snapshot)

    snapshot = build_snapshot()
    object.__setattr__(snapshot, "demand_miss_count", 2)
    with pytest.raises(ValueError, match="close over demand_count"):
        build_payload_cache_demand_hit_shadow_publication(snapshot)


def test_payload_cache_demand_hit_shadow_publication_rejects_nonfinite_constructor_inputs() -> None:
    for field_name, bad_value in (
        ("queue_deadline_us", float("nan")),
        ("service_us_per_issue", float("inf")),
        ("service_us_per_batch", float("nan")),
    ):
        with pytest.raises(ValueError, match=f"{field_name}.*finite"):
            PayloadCacheRuntimeAdapterPayloadlessLive(
                capacity=4096,
                queue_batch_size=1,
                **{field_name: bad_value},
            )


def test_payload_cache_runtime_adapter_payloadless_live_rejects_payload_or_kernel_args() -> None:
    with pytest.raises(ValueError, match="payload transfer"):
        PayloadCacheRuntimeAdapterPayloadlessLive(
            capacity=4096,
            payload_transfer_enabled=True,
        )
    with pytest.raises(ValueError, match="kernel arg"):
        PayloadCacheRuntimeAdapterPayloadlessLive(
            capacity=4096,
            kernel_arg_pass_allowed=True,
        )


def test_payload_cache_runtime_payload_transfer_toggle_rejects_payload_issue() -> None:
    toggle = PayloadCacheRuntimePayloadTransferToggle()

    assert toggle.enabled is False
    with pytest.raises(RuntimeError, match="disabled"):
        toggle.issue_payload(0, 0, payload_bytes=64)

    snapshot = toggle.snapshot()
    payload = snapshot.as_dict()

    assert payload["present"] is True
    assert payload["payload_transfer_toggle_created"] is True
    assert payload["payload_transfer_runtime_enabled"] is False
    assert payload["payload_deref_allowed"] is False
    assert payload["payload_deref_runtime_allowed"] is False
    assert payload["payload_issue_rejected"] is True
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False


def test_payload_cache_runtime_payload_transfer_toggle_rejects_enabled_runtime() -> None:
    with pytest.raises(ValueError, match="disabled"):
        PayloadCacheRuntimePayloadTransferToggle(enabled=True)


def test_payload_cache_runtime_payload_transfer_toggle_snapshot_rejects_side_effects() -> None:
    base_kwargs = {
        "present": True,
        "payload_transfer_toggle_created": True,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "payload_issue_rejected": True,
        "issued_payload_count": 0,
        "payload_bytes": 0,
    }

    with pytest.raises(ValueError, match="payload issue"):
        PayloadCacheRuntimePayloadTransferToggleSnapshot(
            **{
                **base_kwargs,
                "payload_issue_rejected": False,
            },
        )

    for field_name in ("issued_payload_count", "payload_bytes"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheRuntimePayloadTransferToggleSnapshot(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheRuntimePayloadTransferToggleSnapshot(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )


def test_payload_cache_runtime_payload_issue_request_records_request_only() -> None:
    request = PayloadCacheRuntimePayloadIssueRequest(
        present=True,
        request_schema="payload_cache_runtime_payload_issue_request_v1",
        layer_idx=1,
        expert_idx=2,
        requested_payload_bytes=64,
        request_source="queue_budget_first_model_passing_cell",
        source_issue_packet_count=28,
        source_issue_unique_key_count=16,
        source_queue_budget_capacity=4096,
        source_issue_lead_tokens=32,
        source_queue_deadline_us=100.0,
    )
    payload = request.as_dict()

    assert payload["present"] is True
    assert payload["request_schema"] == "payload_cache_runtime_payload_issue_request_v1"
    assert payload["layer_idx"] == 1
    assert payload["expert_idx"] == 2
    assert payload["requested_payload_bytes"] == 64
    assert payload["request_source"] == "queue_budget_first_model_passing_cell"
    assert payload["source_issue_packet_count"] == 28
    assert payload["source_issue_unique_key_count"] == 16
    assert payload["source_queue_budget_capacity"] == 4096
    assert payload["source_issue_lead_tokens"] == 32
    assert payload["source_queue_deadline_us"] == 100.0
    assert payload["issued_payload_count"] == 0
    assert payload["payload_bytes"] == 0
    for key in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        assert payload[key] is False


def test_payload_cache_runtime_payload_issue_request_rejects_side_effects() -> None:
    base_kwargs = {
        "present": True,
        "request_schema": "payload_cache_runtime_payload_issue_request_v1",
        "layer_idx": 1,
        "expert_idx": 2,
        "requested_payload_bytes": 64,
    }

    with pytest.raises(ValueError, match="requested_payload_bytes"):
        PayloadCacheRuntimePayloadIssueRequest(
            **{
                **base_kwargs,
                "requested_payload_bytes": 0,
            },
        )

    for field_name in ("issued_payload_count", "payload_bytes"):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheRuntimePayloadIssueRequest(
                **{
                    **base_kwargs,
                    field_name: 1,
                },
            )

    for field_name in (
        "live_payload_runtime_enabled",
        "payload_transfer_runtime_enabled",
        "payload_deref_allowed",
        "payload_deref_runtime_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "full_fetch_runtime_allowed",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
        "live_runtime_instantiated",
    ):
        with pytest.raises(ValueError, match=field_name):
            PayloadCacheRuntimePayloadIssueRequest(
                **{
                    **base_kwargs,
                    field_name: True,
                },
            )
