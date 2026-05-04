from __future__ import annotations

import json

import pytest
import torch

from mtp_expert_prefetch.runtime import simulate_stall_proxy, write_stall_proxy_report


def test_simulate_stall_proxy_reports_saved_supplemental_fetches(tmp_path):
    transition = torch.tensor([[[[0.9, 0.8, 0.0, 0.0], [0.9, 0.8, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.0, 0.0, 0.95, 0.7], [0.0, 0.0, 0.95, 0.7]]]])
    target_mass = torch.tensor([[[[0.5, 0.3, 0.2, 0.0], [0.4, 0.3, 0.2, 0.1]]]])

    report = simulate_stall_proxy(
        transition,
        mtp,
        target_mass,
        transition_topk=2,
        mtp_topk=4,
        max_extras=[1],
        num_layers=2,
        layer_ms=1.0,
        bandwidth_gbps=0.0002,
        expert_bytes=100,
    )

    base = report.policies["transition_ready"]
    extra = report.policies["transition_top2_plus_ready_mtp_extra1"]
    assert base["supplemental_fetch_count"] == pytest.approx(3.0)
    assert extra["supplemental_fetch_count"] == pytest.approx(2.0)
    assert extra["issued_count"] == pytest.approx(6.0)
    assert extra["ready_count"] == pytest.approx(5.0)
    assert extra["late_count"] == pytest.approx(1.0)
    assert extra["unused_count"] == pytest.approx(0.0)
    assert extra["skipped_count"] == pytest.approx(0.0)
    assert extra["saved_supplemental_fetch_count_vs_transition"] == pytest.approx(1.0)
    assert extra["saved_supplemental_stall_ms_vs_transition"] > 0.0

    output = write_stall_proxy_report(report, tmp_path / "stall.json")
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["ok"] is True
    assert written["policies"]["transition_ready"]["supplemental_fetch_count"] == 3.0


def test_simulate_stall_proxy_applies_priority_admission_capacity():
    transition = torch.tensor([[[[0.9, 0.8, 0.7, 0.6, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.0, 0.0, 0.0, 0.0, 0.95, 0.85]]]])
    target_mass = torch.tensor([[[[0.0, 0.0, 0.0, 0.0, 0.7, 0.3]]]])
    token_sample_indices = torch.tensor([0])

    report = simulate_stall_proxy(
        transition,
        mtp,
        target_mass,
        transition_topk=4,
        mtp_topk=6,
        max_extras=[2],
        num_layers=1,
        layer_ms=1.0,
        sampling_ms=1.0,
        bandwidth_gbps=1.0,
        expert_bytes=100,
        token_sample_indices=token_sample_indices,
        admission_capacity_per_layer=4,
    )

    extra = report.policies["transition_top4_plus_ready_mtp_extra2"]
    assert extra["issued_count"] == pytest.approx(4.0)
    assert extra["requested_count"] == pytest.approx(6.0)
    assert extra["skipped_count"] == pytest.approx(2.0)
    assert extra["supplemental_fetch_count"] == pytest.approx(2.0)
    assert extra["admitted_pool_mass_coverage"] == pytest.approx(0.0)


def test_simulate_stall_proxy_reports_gated_policy_counters():
    transition = torch.tensor([[[[0.9, 0.8, 0.0, 0.0]]]])
    mtp = torch.tensor([[[[0.0, 0.0, 0.95, 0.7]]]])
    utility = torch.tensor([[[[0.0, 0.0, 0.10, 0.01]]]])
    target_mass = torch.tensor([[[[0.5, 0.3, 0.2, 0.0]]]])

    report = simulate_stall_proxy(
        transition,
        mtp,
        target_mass,
        transition_topk=2,
        mtp_topk=4,
        max_extras=[2],
        num_layers=1,
        layer_ms=1.0,
        sampling_ms=1.0,
        bandwidth_gbps=1.0,
        expert_bytes=100,
        gated_score_tensors={"utility_keep_top": utility},
        gated_score_thresholds={"utility_keep_top": 0.05},
        gated_max_extra=2,
    )

    gated = report.policies["transition_top2_plus_gated_utility_keep_top"]
    assert gated["requested_count"] == pytest.approx(3.0)
    assert gated["issued_count"] == pytest.approx(3.0)
    assert gated["supplemental_fetch_count"] == pytest.approx(0.0)
    assert gated["admission_reason_counters"]["admitted_score_gate"]["count"] == pytest.approx(
        1.0
    )
    assert gated["admission_reason_counters"]["skipped_below_threshold"]["count"] == pytest.approx(
        1.0
    )
    assert gated["admission_action_counters"]["full_fetch"]["count"] == pytest.approx(1.0)
    assert gated["admission_action_counters"]["metadata"]["count"] == pytest.approx(0.0)
    assert gated["admission_action_counters"]["premap"]["count"] == pytest.approx(0.0)
    assert gated["admission_action_counters"]["skip"]["count"] == pytest.approx(3.0)
    assert gated["admission_action_counters"]["full_fetch"]["bytes"] == pytest.approx(100.0)
    matrix = gated["admission_action_reason_matrix"]
    assert matrix["admitted_score_gate"]["full_fetch"]["count"] == pytest.approx(1.0)
    assert matrix["admitted_score_gate"]["skip"]["count"] == pytest.approx(0.0)
    assert matrix["skipped_below_threshold"]["skip"]["count"] == pytest.approx(1.0)
    assert matrix["skipped_not_novel"]["skip"]["count"] == pytest.approx(2.0)
