from __future__ import annotations

from mtp_expert_prefetch.runtime import (
    ShadowEventId,
    ShadowPremapSummaryEvent,
    ShadowPolicyConfig,
    ShadowSummaryEvent,
    write_shadow_jsonl,
)
from scripts.summarize_premap_shadow_contract import summarize


def test_premap_shadow_contract_summary_passes_clean_premap_only_artifact(tmp_path):
    event = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", 0, -1, 3),
        premap_policy="premap_only",
        premap_descriptor_count=4,
        premap_unique_experts=4,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=16_384,
        premap_descriptor_hash="desc",
        premap_address_hash="addr",
    )
    path = write_shadow_jsonl([event], tmp_path / "shadow.jsonl")

    payload = summarize(path)

    assert payload["ok"] is True
    assert payload["event_types"] == ["premap_summary"]
    assert payload["premap_summary_count"] == 1
    assert payload["premap_summary_descriptor_count"] == 4
    assert payload["premap_summary_payload_bytes"] == 0
    assert payload["violation_total"] == 0
    assert payload["forbidden_event_total"] == 0


def test_premap_shadow_contract_summary_rejects_forbidden_payload_event(tmp_path):
    premap = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", 0, -1, 3),
        premap_policy="premap_only",
        premap_descriptor_count=4,
        premap_unique_experts=4,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=16_384,
        premap_descriptor_hash="desc",
        premap_address_hash="addr",
    )
    policy = ShadowPolicyConfig(
        policy_mode="default",
        optimization_goal="stall_reduction",
        action_keep_fraction=0.5,
        metadata_score_ratio=0.95,
        full_fetch_max_extra=1,
        metadata_max_extra=0,
        premap_max_extra=0,
    )
    full_fetch = ShadowSummaryEvent(
        event_id=ShadowEventId("req", 0, 1, 3),
        policy=policy,
        transition_topk_count=32,
        mtp_requested_count=64,
        full_fetch_count=1,
        metadata_count=0,
        premap_count=0,
        skip_count=0,
        full_fetch_payload_bytes=1_650_000,
        metadata_actual_bytes=0,
        premap_actual_bytes=0,
    )
    path = write_shadow_jsonl([premap, full_fetch], tmp_path / "bad_shadow.jsonl")

    payload = summarize(path)

    assert payload["ok"] is False
    assert payload["forbidden_events"]["full_fetch_count"] == 1
    assert payload["forbidden_event_total"] == 1


def test_premap_shadow_contract_summary_rejects_non_premap_rows(tmp_path):
    premap = ShadowPremapSummaryEvent(
        event_id=ShadowEventId("req", 0, -1, 3),
        premap_policy="premap_only",
        premap_descriptor_count=4,
        premap_unique_experts=4,
        premap_unique_layers=1,
        premap_unique_sample_layers=1,
        premap_actual_bytes=16_384,
        premap_descriptor_hash="desc",
        premap_address_hash="addr",
    )
    path = write_shadow_jsonl(
        [
            premap,
            {
                "event_type": "descriptor_layer_timing",
                "request_id": "req",
                "sequence_id": 0,
                "token_index": -1,
                "layer": 3,
            },
        ],
        tmp_path / "timing_shadow.jsonl",
    )

    payload = summarize(path)

    assert payload["ok"] is False
    assert payload["event_types"] == ["descriptor_layer_timing", "premap_summary"]
    assert payload["non_premap_event_total"] == 1
