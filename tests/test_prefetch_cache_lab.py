from __future__ import annotations

import json

import pytest
import torch

from scripts.run_prefetch_cache_lab import (
    CacheLabConfig,
    apply_cache_lab_gate_to_policies,
    build_cache_lab_gate_decision,
    build_policy_masks,
    build_policy_priority_scores,
    compute_queue_pressure,
    clamp_unit_interval,
    copy_cost_us,
    demand_stream_indices,
    hash_demand_stream,
    load_measured_copy_envelope,
    prefetch_copy_cost_us,
    replay_policy,
    select_admitted_experts,
    simulate_event_driven_queue,
    transfer_us,
    true_router_stream_indices,
)
from mtp_expert_prefetch.runtime.cache_lab_gate import CacheLabGateDecision


def _config(**overrides) -> CacheLabConfig:
    values = {
        "transition_topk": 1,
        "mtp_topk": 2,
        "gate_max_extra": 1,
        "keep_fraction": 0.5,
        "cache_capacity": 1,
        "bandwidth_gbps": 1.0,
        "expert_bytes": 100,
        "overlap_factor": 0.0,
        "manager_us_per_issue": 0.0,
        "lookup_us_per_demand": 0.0,
        "decision_us_per_token_layer": 0.0,
        "stress_fallback": False,
    }
    values.update(overrides)
    return CacheLabConfig(**values)


def test_transfer_us_uses_decimal_gbps() -> None:
    assert transfer_us(1_000_000, 1.0) == pytest.approx(1000.0)


def test_clamp_unit_interval_bounds_overlap_factor() -> None:
    assert clamp_unit_interval(-0.5) == 0.0
    assert clamp_unit_interval(0.25) == 0.25
    assert clamp_unit_interval(1.5) == 1.0


def test_measured_copy_envelope_and_copy_cost(tmp_path) -> None:
    payload = {
        "rows": [
            {
                "direction": "h2d",
                "pinned": True,
                "experts": 4,
                "p95_ms": 2.0,
                "p95_gbps": 3.3,
            },
            {
                "direction": "h2d",
                "pinned": False,
                "experts": 1,
                "p95_ms": 1.0,
                "p95_gbps": 1.0,
            },
        ]
    }
    path = tmp_path / "copy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    envelope = load_measured_copy_envelope(
        path, stat="p95", experts=4, pinned="true"
    )

    assert envelope is not None
    assert envelope["copy_us_per_issue"] == pytest.approx(500.0)
    assert envelope["copy_us_per_batch"] == pytest.approx(2000.0)
    assert envelope["effective_gbps"] == pytest.approx(3.3)
    assert copy_cost_us(
        3,
        config=_config(
            measured_copy_us_per_issue=float(envelope["copy_us_per_issue"])
        ),
    ) == pytest.approx(1500.0)


def test_prefetch_copy_cost_uses_batched_measured_copy() -> None:
    config = _config(
        measured_copy_us_per_batch=2000.0,
        measured_copy_batch_size=4,
        queue_batch_size=4,
    )

    assert prefetch_copy_cost_us(
        [1, 4, 5], issued_count=10, config=config
    ) == pytest.approx(8000.0)


def test_prefetch_copy_cost_can_use_global_coalescing() -> None:
    config = _config(
        measured_copy_us_per_batch=2000.0,
        measured_copy_batch_size=4,
        queue_batch_size=4,
        queue_coalesce_scope="global",
    )

    assert prefetch_copy_cost_us(
        [1, 4, 5], issued_count=10, config=config
    ) == pytest.approx(6000.0)


def test_measured_copy_envelope_reports_missing_h2d_rows(tmp_path) -> None:
    path = tmp_path / "copy.json"
    path.write_text(json.dumps({"rows": [{"direction": "d2h"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="No matching H2D"):
        load_measured_copy_envelope(path, stat="p95", experts=1, pinned="true")


def test_measured_copy_envelope_reports_missing_stat(tmp_path) -> None:
    path = tmp_path / "copy.json"
    path.write_text(
        json.dumps({"rows": [{"direction": "h2d", "pinned": True, "experts": 1}]}),
        encoding="utf-8",
    )

    with pytest.raises(KeyError, match="p95_ms"):
        load_measured_copy_envelope(path, stat="p95", experts=1, pinned="true")


def test_compute_queue_pressure_counts_overflow() -> None:
    metrics = compute_queue_pressure(
        [0, 1, 4, 2],
        max_inflight=2,
        wait_us_per_overflow=10.0,
        batch_size=2,
    )

    assert metrics["queue_group_count"] == 3
    assert metrics["queue_overflow_count"] == 2
    assert metrics["queue_wait_us"] == pytest.approx(20.0)
    assert metrics["queue_pressure"] == pytest.approx(2 / 7)
    assert metrics["max_issue_burst"] == 4
    assert metrics["queue_model"] == "per_token_layer_burst_overflow"
    assert metrics["queue_coalesce_scope"] == "token_layer"
    assert metrics["queue_batch_count"] == 4


def test_compute_queue_pressure_global_coalesces_batch_count() -> None:
    metrics = compute_queue_pressure(
        [1, 4, 5],
        max_inflight=8,
        wait_us_per_overflow=10.0,
        batch_size=4,
        coalesce_scope="global",
    )

    assert metrics["queue_coalesce_scope"] == "global"
    assert metrics["queue_batch_count"] == 3


def test_compute_queue_pressure_disables_nonpositive_inflight_limit() -> None:
    for max_inflight in (0, -1):
        metrics = compute_queue_pressure(
            [4], max_inflight=max_inflight, wait_us_per_overflow=10.0
        )
        assert metrics["queue_overflow_count"] == 0
        assert metrics["queue_wait_us"] == pytest.approx(0.0)


def test_select_admitted_experts_uses_policy_scores() -> None:
    scores = torch.zeros(1, 1, 1, 5)
    scores[0, 0, 0, 3] = 10.0
    scores[0, 0, 0, 1] = 5.0

    admitted = select_admitted_experts(
        [0, 1, 2, 3],
        token_idx=0,
        layer_idx=0,
        limit=2,
        admission_policy="score",
        priority_scores=scores,
    )

    assert admitted == [3, 1]


def test_select_admitted_experts_protected_score_keeps_baseline_first() -> None:
    scores = torch.zeros(1, 1, 1, 5)
    scores[0, 0, 0, 3] = 100.0
    scores[0, 0, 0, 2] = 50.0
    protected_scores = torch.zeros(1, 1, 1, 5)
    protected_scores[0, 0, 0, 1] = 10.0
    protected_scores[0, 0, 0, 0] = 5.0

    admitted = select_admitted_experts(
        [0, 1, 2, 3],
        token_idx=0,
        layer_idx=0,
        limit=3,
        admission_policy="protected_score",
        priority_scores=scores,
        protected_experts=[0, 1],
        protected_priority_scores=protected_scores,
    )

    assert admitted == [1, 0, 3]


def test_simulate_event_driven_queue_batches_across_events() -> None:
    metrics = simulate_event_driven_queue(
        [1, 1, 1, 1],
        requested_issue_batch_sizes=[1, 1, 1, 1],
        config=_config(
            measured_copy_us_per_batch=100.0,
            measured_copy_batch_size=2,
            queue_model="event",
            queue_batch_size=2,
            queue_event_interval_us=10.0,
        ),
    )

    assert metrics["queue_model"] == "event_driven_batch_queue"
    assert "drop clips" in str(metrics["queue_backpressure_semantics"])
    assert metrics["queue_coalesce_scope"] == "global"
    assert metrics["queue_batch_count"] == 2
    assert metrics["queue_service_us"] == pytest.approx(200.0)
    assert metrics["queue_event_interval_us"] == pytest.approx(10.0)


def test_simulate_event_driven_queue_deadline_flushes_partial_batches() -> None:
    metrics = simulate_event_driven_queue(
        [1, 1],
        requested_issue_batch_sizes=[1, 1],
        config=_config(
            measured_copy_us_per_batch=100.0,
            measured_copy_batch_size=4,
            queue_model="event",
            queue_batch_size=4,
            queue_event_interval_us=10.0,
            queue_deadline_us=5.0,
        ),
    )

    assert metrics["queue_batch_count"] == 2
    assert metrics["queue_service_us"] == pytest.approx(50.0)
    assert metrics["queue_deadline_us"] == pytest.approx(5.0)


def test_replay_policy_counts_evicted_prefetch_before_use() -> None:
    target = torch.zeros(2, 1, 1, 2)
    target[0, 0, 0, 0] = 1.0
    target[1, 0, 0, 1] = 1.0
    prefetch = torch.zeros_like(target, dtype=torch.bool)
    prefetch[0, 0, 0, :] = True
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(cache_capacity=1),
    )

    assert row["issued_fetch_count"] == 2
    assert row["used_fetch_count"] == 0
    assert row["evicted_before_use_count"] == 2
    assert row["demand_miss_count"] == 2
    assert row["cache_manager_snapshot"]["issued_fetch_count"] == 2
    assert row["cache_manager_snapshot"]["evicted_before_use_count"] == 2


def test_replay_policy_adds_measured_copy_and_queue_pressure() -> None:
    target = torch.zeros(1, 1, 1, 4)
    target[0, 0, 0, 0] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_issue=100.0,
            max_inflight_prefetches=2,
            queue_wait_us_per_overflow=10.0,
            overlap_factor=0.0,
        ),
    )

    assert row["issued_fetch_count"] == 4
    assert row["prefetch_dma_us"] == pytest.approx(400.0)
    assert row["demand_stall_us"] == pytest.approx(0.0)
    assert row["effective_overlap_factor"] == 0.0
    assert row["prefetch_queue_model"] == "per_token_layer_burst_overflow"
    assert row["prefetch_queue_coalesce_scope"] == "token_layer"
    assert row["prefetch_queue_overflow_count"] == 2
    assert row["prefetch_queue_wait_us"] == pytest.approx(20.0)


def test_replay_policy_drop_backpressure_reduces_issued_prefetches() -> None:
    target = torch.zeros(1, 1, 1, 4)
    target[0, 0, 0, 3] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_issue=100.0,
            max_inflight_prefetches=2,
            queue_policy="drop",
            queue_wait_us_per_overflow=10.0,
        ),
    )

    assert row["issued_fetch_count"] == 2
    assert row["prefetch_backpressure_dropped_count"] == 2
    assert row["prefetch_queue_overflow_count"] == 2
    assert row["prefetch_queue_pressure"] == pytest.approx(0.5)
    assert row["prefetch_queue_wait_us"] == pytest.approx(0.0)
    assert row["demand_miss_count"] == 1


def test_replay_policy_drop_global_keeps_requested_queue_pressure() -> None:
    target = torch.zeros(1, 1, 1, 5)
    target[0, 0, 0, 4] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_batch=100.0,
            measured_copy_batch_size=2,
            max_inflight_prefetches=2,
            queue_batch_size=2,
            queue_coalesce_scope="global",
            queue_policy="drop",
            queue_wait_us_per_overflow=10.0,
        ),
    )

    assert row["issued_fetch_count"] == 2
    assert row["prefetch_dma_us"] == pytest.approx(100.0)
    assert row["prefetch_queue_coalesce_scope"] == "global"
    assert row["prefetch_queue_batch_count"] == 3
    assert row["prefetch_backpressure_dropped_count"] == 3
    assert row["prefetch_queue_overflow_count"] == 3
    assert row["prefetch_queue_pressure"] == pytest.approx(3 / 5)
    assert row["prefetch_queue_wait_us"] == pytest.approx(0.0)


def test_replay_policy_event_queue_uses_measured_batch_service() -> None:
    target = torch.zeros(1, 1, 1, 4)
    target[0, 0, 0, 0] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_batch=100.0,
            measured_copy_batch_size=2,
            queue_model="event",
            queue_batch_size=2,
            queue_event_interval_us=10.0,
            overlap_factor=0.0,
        ),
    )

    assert row["issued_fetch_count"] == 4
    assert row["prefetch_queue_model"] == "event_driven_ready_time_batch_queue"
    assert "virtual DMA queue" in str(row["prefetch_queue_backpressure_semantics"])
    assert "completion no later" in str(row["prefetch_queue_backpressure_semantics"])
    assert row["prefetch_queue_batch_count"] == 2
    assert row["prefetch_dma_us"] == pytest.approx(200.0)
    assert row["prefetch_queue_service_us"] == pytest.approx(200.0)
    assert row["demand_miss_count"] == 1
    assert row["prefetch_ready_late_miss_count"] == 1


def test_replay_policy_event_ready_prefetch_can_hit_future_demand() -> None:
    target = torch.zeros(2, 1, 1, 1)
    target[1, 0, 0, 0] = 1.0
    prefetch = torch.zeros_like(target, dtype=torch.bool)
    prefetch[0, 0, 0, 0] = True
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_batch=50.0,
            measured_copy_batch_size=1,
            queue_model="event",
            queue_batch_size=1,
            queue_event_interval_us=100.0,
            queue_deadline_us=0.0,
            overlap_factor=0.0,
        ),
    )

    assert row["issued_fetch_count"] == 1
    assert row["demand_hit_count"] == 1
    assert row["demand_miss_count"] == 0
    assert row["used_fetch_count"] == 1
    assert row["prefetch_ready_late_miss_count"] == 0


def test_replay_policy_event_late_prefetch_misses_deadline() -> None:
    target = torch.zeros(2, 1, 1, 1)
    target[1, 0, 0, 0] = 1.0
    prefetch = torch.zeros_like(target, dtype=torch.bool)
    prefetch[0, 0, 0, 0] = True
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_batch=50.0,
            measured_copy_batch_size=1,
            queue_model="event",
            queue_batch_size=1,
            queue_event_interval_us=10.0,
            queue_deadline_us=0.0,
            overlap_factor=0.0,
        ),
    )

    assert row["issued_fetch_count"] == 1
    assert row["demand_hit_count"] == 0
    assert row["demand_miss_count"] == 1
    assert row["used_fetch_count"] == 0
    assert row["prefetch_ready_late_miss_count"] == 1
    assert row["prefetch_late_completion_unused_count"] == 1
    assert row["unused_fetch_count"] == 1


def test_replay_policy_event_drop_reports_pressure_and_timeline() -> None:
    target = torch.zeros(1, 1, 1, 5)
    target[0, 0, 0, 4] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_batch=100.0,
            measured_copy_batch_size=2,
            max_inflight_prefetches=2,
            queue_model="event",
            queue_batch_size=2,
            queue_policy="drop",
            queue_event_interval_us=10.0,
            queue_deadline_us=5.0,
        ),
    )

    assert row["issued_fetch_count"] == 2
    assert row["prefetch_backpressure_dropped_count"] == 3
    assert row["prefetch_queue_overflow_count"] == 3
    assert row["prefetch_queue_pressure"] == pytest.approx(3 / 5)
    assert row["prefetch_queue_model"] == "event_driven_ready_time_batch_queue"
    assert row["prefetch_queue_wait_us"] == pytest.approx(0.0)
    assert row["prefetch_queue_service_us"] == pytest.approx(100.0)
    assert row["prefetch_queue_total_span_us"] == pytest.approx(100.0)
    assert row["prefetch_queue_max_delay_us"] == pytest.approx(100.0)


def test_replay_policy_drop_score_admission_keeps_high_score_expert() -> None:
    target = torch.zeros(1, 1, 1, 5)
    target[0, 0, 0, 4] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    scores = torch.zeros_like(target)
    scores[0, 0, 0, 4] = 100.0
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_issue=100.0,
            max_inflight_prefetches=2,
            queue_policy="drop",
            queue_admission_policy="score",
        ),
        priority_scores=scores,
    )

    assert row["issued_fetch_count"] == 2
    assert row["demand_miss_count"] == 0
    assert row["demand_hit_count"] == 1
    assert row["prefetch_queue_admission_policy"] == "score"


def test_replay_policy_drop_protected_score_keeps_baseline_before_extra() -> None:
    target = torch.zeros(1, 1, 1, 5)
    target[0, 0, 0, 1] = 1.0
    prefetch = torch.ones_like(target, dtype=torch.bool)
    protected = torch.zeros_like(target, dtype=torch.bool)
    protected[0, 0, 0, 0] = True
    protected[0, 0, 0, 1] = True
    scores = torch.zeros_like(target)
    scores[0, 0, 0, 4] = 100.0
    protected_scores = torch.zeros_like(target)
    protected_scores[0, 0, 0, 1] = 10.0
    demands = demand_stream_indices(target)

    row = replay_policy(
        "unit",
        prefetch,
        target_mass=target,
        demand_indices=demands,
        config=_config(
            cache_capacity=8,
            measured_copy_us_per_issue=100.0,
            max_inflight_prefetches=2,
            queue_policy="drop",
            queue_admission_policy="protected_score",
        ),
        priority_scores=scores,
        protected_mask=protected,
        protected_priority_scores=protected_scores,
    )

    assert row["issued_fetch_count"] == 2
    assert row["demand_miss_count"] == 0
    assert row["demand_hit_count"] == 1
    assert row["prefetch_queue_admission_policy"] == "protected_score"


def test_true_router_stream_hash_uses_full_future_window() -> None:
    target = torch.zeros(1, 2, 1, 2)
    target[0, 0, 0, 0] = 1.0
    target[0, 1, 0, 1] = 1.0

    demand = demand_stream_indices(target)
    true_router = true_router_stream_indices(target)

    assert demand.tolist() == [[0, 0, 0]]
    assert true_router.tolist() == [[0, 0, 0, 0], [0, 1, 0, 1]]
    assert hash_demand_stream(demand) != hash_demand_stream(true_router)


def test_build_policy_masks_reports_stress_shutdown_counts() -> None:
    transition = torch.tensor([[[[0.9, 0.0]]]])
    mtp = torch.tensor([[[[0.0, 0.8]]]])
    target = torch.tensor([[[[0.0, 1.0]]]])

    policies, shutdown = build_policy_masks(
        train_transition_scores=transition,
        train_mtp_scores=mtp,
        train_target_mass=target,
        transition_scores=transition,
        mtp_scores=mtp,
        target_mass=target,
        config=_config(stress_fallback=True),
    )

    assert policies["transition_top1_plus_score_keep50"].sum().item() == 1
    assert policies["transition_top1_plus_utility_keep50"].sum().item() == 1
    assert shutdown["transition_top1_plus_score_keep50"] == 1
    assert shutdown["transition_top1_plus_utility_keep50"] == 1


def test_build_cache_lab_gate_decision_reads_replay_contract(tmp_path) -> None:
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "min_payload_capacity: 10240",
                "min_overlap_factor: 0.5",
                "max_manager_us_per_issue: 50.0",
                "min_bandwidth_gbps: 3.0",
                "max_bandwidth_gbps: 12.0",
                "require_stress_fallback_clear: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    decision = build_cache_lab_gate_decision(
        gate,
        config=_config(
            cache_capacity=8192,
            overlap_factor=0.8,
            manager_us_per_issue=0.0,
            bandwidth_gbps=6.589,
        ),
    )

    assert decision is not None
    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "payload_capacity_below_gate"


def test_build_cache_lab_gate_decision_applies_ready_time_block_report(tmp_path) -> None:
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "min_payload_capacity: 10240",
                "min_overlap_factor: 0.5",
                "max_manager_us_per_issue: 50.0",
                "min_bandwidth_gbps: 3.0",
                "max_bandwidth_gbps: 12.0",
                "require_stress_fallback_clear: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = tmp_path / "ready_time_gate.json"
    report.write_text(
        json.dumps({"passed": True, "allow_full_fetch": False}),
        encoding="utf-8",
    )

    decision = build_cache_lab_gate_decision(
        gate,
        config=_config(
            cache_capacity=10240,
            overlap_factor=0.8,
            manager_us_per_issue=0.0,
            bandwidth_gbps=6.589,
        ),
        ready_time_gate_report=report,
    )

    assert decision is not None
    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "ready_time_payload_cache_gate_blocked"
    assert decision.ready_time_allow_full_fetch is False


def test_build_cache_lab_gate_decision_blocks_invalid_ready_time_report(tmp_path) -> None:
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "min_payload_capacity: 10240",
                "min_overlap_factor: 0.5",
                "max_manager_us_per_issue: 50.0",
                "min_bandwidth_gbps: 3.0",
                "max_bandwidth_gbps: 12.0",
                "require_stress_fallback_clear: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = tmp_path / "ready_time_gate.json"
    report.write_text(
        json.dumps({"passed": False, "allow_full_fetch": True}),
        encoding="utf-8",
    )

    decision = build_cache_lab_gate_decision(
        gate,
        config=_config(
            cache_capacity=10240,
            overlap_factor=0.8,
            manager_us_per_issue=0.0,
            bandwidth_gbps=6.589,
        ),
        ready_time_gate_report=report,
    )

    assert decision is not None
    assert decision.allow_full_fetch_mtp is False
    assert decision.reason == "ready_time_payload_cache_gate_blocked"


def test_build_cache_lab_gate_decision_blocks_malformed_ready_time_report(tmp_path) -> None:
    gate = tmp_path / "gate.yaml"
    gate.write_text(
        "\n".join(
            [
                "min_payload_capacity: 10240",
                "min_overlap_factor: 0.5",
                "max_manager_us_per_issue: 50.0",
                "min_bandwidth_gbps: 3.0",
                "max_bandwidth_gbps: 12.0",
                "require_stress_fallback_clear: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    reports = []
    for name, payload in (
        ("bad_json", "{"),
        ("list", "[]"),
        ("non_bool_allow", json.dumps({"passed": True, "allow_full_fetch": "yes"})),
    ):
        report = tmp_path / f"{name}.json"
        report.write_text(payload, encoding="utf-8")
        reports.append(report)

    for report in reports:
        decision = build_cache_lab_gate_decision(
            gate,
            config=_config(
                cache_capacity=10240,
                overlap_factor=0.8,
                manager_us_per_issue=0.0,
                bandwidth_gbps=6.589,
            ),
            ready_time_gate_report=report,
        )

        assert decision is not None
        assert decision.allow_full_fetch_mtp is False
        assert decision.reason == "ready_time_payload_cache_gate_blocked"


def test_apply_cache_lab_gate_collapses_gated_policies() -> None:
    transition = torch.tensor([[[[True, False, False]]]])
    utility = torch.tensor([[[[True, True, False]]]])
    score = torch.tensor([[[[True, False, True]]]])
    policies = {
        "transition_top1": transition.clone(),
        "transition_top1_plus_utility_keep50": utility.clone(),
        "transition_top1_plus_score_keep50": score.clone(),
        "oracle_used": torch.ones_like(transition),
    }
    shutdown: dict[str, int] = {}

    apply_cache_lab_gate_to_policies(
        policies,
        shutdown,
        gate_decision=CacheLabGateDecision(
            allow_full_fetch_mtp=False,
            reason="payload_capacity_below_gate",
            payload_capacity=1,
            overlap_factor=0.5,
            manager_us_per_issue=0.0,
            bandwidth_gbps=6.589,
            stress_fallback_active=False,
            ready_time_allow_full_fetch=None,
        ),
        config=_config(transition_topk=1),
    )

    assert torch.equal(policies["transition_top1_plus_utility_keep50"], transition)
    assert torch.equal(policies["transition_top1_plus_score_keep50"], transition)
    assert torch.equal(policies["oracle_used"], torch.ones_like(transition))
    assert shutdown["transition_top1_plus_utility_keep50"] == 1
    assert shutdown["transition_top1_plus_score_keep50"] == 1
