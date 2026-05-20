from __future__ import annotations

from mtp_expert_prefetch.runtime import ControlledExpertCacheManager


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
