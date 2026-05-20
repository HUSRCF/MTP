from scripts.replay_vllm_trace_premap_address_capacity import _fast_replay_capacities


def test_fast_replay_capacities_tracks_lru_eviction_and_reuse():
    events = [
        [(0, 1), (0, 2)],
        [(0, 2), (0, 3)],
        [(0, 1)],
    ]

    reports = _fast_replay_capacities(
        events,
        capacities=[2, 3, None],
        descriptor_bytes=4,
    )
    by_capacity = {report["capacity"]: report for report in reports}

    cap2 = by_capacity[2]
    assert cap2["descriptor_count"] == 5
    assert cap2["new_address_count"] == 4
    assert cap2["reused_address_count"] == 1
    assert cap2["evicted_address_count"] == 2
    assert cap2["resident_address_count"] == 2
    assert cap2["resident_descriptor_bytes"] == 8

    cap3 = by_capacity[3]
    assert cap3["new_address_count"] == 3
    assert cap3["reused_address_count"] == 2
    assert cap3["evicted_address_count"] == 0
    assert cap3["resident_address_count"] == 3

    unbounded = by_capacity[None]
    assert unbounded["new_address_count"] == cap3["new_address_count"]
    assert unbounded["reused_address_count"] == cap3["reused_address_count"]
    assert unbounded["evicted_address_count"] == 0
