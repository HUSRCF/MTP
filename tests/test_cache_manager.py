from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    ControlledExpertCacheManager,
    ReadyTimeExpertCacheManager,
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
