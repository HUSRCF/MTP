from __future__ import annotations

from mtp_expert_prefetch.runtime import ExpertPrefetchDescriptor, read_shadow_jsonl
from scripts.export_prefetch_premap_descriptors import _write_premap_shadow_jsonl


def test_write_premap_shadow_jsonl_groups_by_sample_layer(tmp_path):
    descriptors = [
        ExpertPrefetchDescriptor(0, 1, 7, 4, "mtp_token_extra_head", 0.75),
        ExpertPrefetchDescriptor(0, 1, 3, 2, "transition_head", 0.95),
        ExpertPrefetchDescriptor(0, 2, 7, 3, "transition_tail", 0.50),
        ExpertPrefetchDescriptor(1, 1, 9, 4, "mtp_token_extra_head", 0.60),
    ]
    output = tmp_path / "premap_shadow.jsonl"

    aggregate = _write_premap_shadow_jsonl(
        descriptors=descriptors,
        output=output,
        descriptor_bytes=128,
        premap_policy="premap_only",
        premap_source="unit_test",
    )
    rows = read_shadow_jsonl(output)

    assert [row["event_type"] for row in rows] == [
        "premap_summary",
        "premap_summary",
        "premap_summary",
    ]
    assert [row["shadow_event_id"] for row in rows] == [
        "premap_export:0:-1:1",
        "premap_export:0:-1:2",
        "premap_export:1:-1:1",
    ]
    assert rows[0]["premap_descriptor_count"] == 2
    assert rows[0]["premap_actual_bytes"] == 256
    assert rows[0]["premap_payload_bytes"] == 0
    assert rows[0]["premap_changes_router"] is False
    assert rows[0]["premap_changes_descriptor_order"] is False
    assert aggregate["premap_summary_count"] == 3
    assert aggregate["premap_summary_descriptor_count"] == 4
    assert aggregate["premap_summary_actual_bytes"] == 512
    assert aggregate["premap_summary_payload_violation_count"] == 0
    assert aggregate["premap_summary_router_change_violation_count"] == 0
    assert aggregate["premap_summary_descriptor_order_change_violation_count"] == 0
    assert aggregate["descriptor_order_summary_count"] == 0
