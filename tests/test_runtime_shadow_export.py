import torch
import pytest

from mtp_expert_prefetch.runtime.admission import AdmissionDecisionMasks
from mtp_expert_prefetch.runtime.shadow_export import iter_shadow_summary_outcome_events
from mtp_expert_prefetch.runtime.shadow_log import ShadowPolicyConfig, aggregate_shadow_events


def test_iter_shadow_summary_outcome_events_exports_action_outcomes():
    shape = (1, 1, 1, 6)
    base = torch.zeros(shape, dtype=torch.bool)
    base[..., 1] = True
    target_mass = torch.zeros(shape, dtype=torch.float32)
    target_mass[..., 1] = 0.1
    target_mass[..., 2] = 0.6
    target_mass[..., 3] = 0.2
    target_mass[..., 5] = 0.1

    full_fetch = torch.zeros(shape, dtype=torch.bool)
    full_fetch[..., 2] = True
    metadata = torch.zeros(shape, dtype=torch.bool)
    metadata[..., 3] = True
    premap = torch.zeros(shape, dtype=torch.bool)
    premap[..., 4] = True
    skipped = torch.zeros(shape, dtype=torch.bool)
    skipped[..., 5] = True
    empty = torch.zeros(shape, dtype=torch.bool)
    decisions = AdmissionDecisionMasks(
        admitted_full_fetch=full_fetch,
        admitted_metadata=metadata,
        admitted_premap=premap,
        skipped_not_novel=empty,
        skipped_rank_cap=empty,
        skipped_below_threshold=skipped,
        skipped_invalid_score=empty,
        skipped_policy=empty,
    )
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=4,
        metadata_max_extra=1,
        premap_max_extra=1,
        policy_reason="normal_envelope",
        allow_full_mtp_fetch=True,
        allow_mtp_metadata=True,
        allow_mtp_premap=True,
    )

    rows = [
        event.as_dict()
        for event in iter_shadow_summary_outcome_events(
            base_mask=base,
            decisions=decisions,
            target_mass=target_mass,
            policy=policy,
            request_id="req",
            token_sample_indices=torch.tensor([7]),
            decision_us=10.0,
            transition_ready_rate=0.9,
            mtp_ready_fraction=0.5,
            bandwidth_gbps=6.589,
            layer_ms=1.0,
        )
    ]

    assert [row["event_type"] for row in rows] == ["summary", "outcome"]
    assert rows[0]["shadow_event_id"] == "req:7:0:0"
    assert rows[0]["full_fetch_count"] == 1
    assert rows[0]["metadata_count"] == 1
    assert rows[0]["premap_count"] == 1
    assert rows[0]["skip_count"] == 1
    assert rows[0]["full_fetch_payload_bytes"] == 1_650_000
    assert rows[1]["true_topk_experts"] == [2, 3, 1, 5]
    assert rows[1]["full_fetch_used_count"] == 1
    assert rows[1]["metadata_later_used_count"] == 1
    assert rows[1]["premap_later_used_count"] == 0
    assert rows[1]["skip_would_have_used_count"] == 1
    assert rows[1]["covered_mass"] == pytest.approx(0.7)
    assert rows[1]["miss_mass"] == pytest.approx(0.3)
    assert rows[1]["top1_ready"] is True
    assert rows[1]["weighted_top1_miss"] == 0.0

    aggregate = aggregate_shadow_events(rows)
    assert aggregate["summary_count"] == 1
    assert aggregate["outcome_count"] == 1
    assert aggregate["top1_ready_rate"] == 1.0
    assert aggregate["decision_us_mean"] == 10.0
