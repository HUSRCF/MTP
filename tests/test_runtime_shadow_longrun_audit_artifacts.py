from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("sample_count", "expected_event_count"),
    [
        (128, 10_195),
        (512, 20_342),
    ],
)
def test_dolly_longrun_audit_summaries_are_premap_safe(
    sample_count: int, expected_event_count: int
) -> None:
    summary_path = (
        PROJECT_ROOT
        / "data/traces"
        / f"external_prompt_gate_dolly_{sample_count}_awq_vllm_gpu1_decode_gen64_longrun_audit"
        / "longrun_audit_summary.json"
    )
    if not summary_path.exists():
        pytest.skip(f"long-run audit artifact is not present: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["row_count"] == 2 * expected_event_count
    assert summary["event_counts"] == {
        "premap_summary": expected_event_count,
        "premap_consumer_mapping": expected_event_count,
    }
    aggregate = summary["aggregate"]
    assert aggregate["premap_summary_count"] == expected_event_count
    assert aggregate["premap_consumer_mapping_count"] == expected_event_count
    assert aggregate["premap_summary_payload_bytes"] == 0
    assert aggregate["premap_address_evicted_count"] == 0
    assert aggregate["premap_address_eviction_pressure_mean"] == 0.0
    assert aggregate["premap_address_resident_count_max"] < 12_288
    assert aggregate["premap_address_resident_descriptor_bytes_max"] > 0
    assert aggregate["premap_address_new_count"] > 0
    assert aggregate["premap_address_reused_count"] > 0
    assert aggregate["premap_address_reuse_rate_mean"] > 0.98
    assert aggregate["premap_consumer_address_hit_rate"] == 1.0
    assert aggregate["premap_consumer_descriptor_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_real_descriptor_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_lookup_after_prepare_rate"] == 1.0
    if "premap_consumer_real_descriptor_handle_hit_count" not in aggregate:
        pytest.skip("legacy long-run summary predates source-class handle counters")
    real_handle_hits = aggregate["premap_consumer_real_descriptor_handle_hit_count"]
    assert real_handle_hits > 0
    assert (
        aggregate["premap_consumer_real_descriptor_handle_packed_weight_hit_count"]
        == real_handle_hits
    )
    assert (
        aggregate["premap_consumer_real_descriptor_handle_scale_metadata_hit_count"]
        == real_handle_hits
    )
    assert (
        aggregate["premap_consumer_real_descriptor_handle_aux_metadata_hit_count"]
        == real_handle_hits
    )
    assert aggregate["premap_consumer_real_descriptor_handle_packed_weight_miss_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_scale_metadata_miss_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_aux_metadata_miss_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_resolver_disabled_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_consumer_layer_missing_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_expert_map_miss_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_no_handle_parts_count"] == 0
    assert aggregate["premap_consumer_real_descriptor_handle_binding_mismatch_count"] == 0
    if "premap_consumer_readonly_lookup_count" not in aggregate:
        pytest.skip("legacy long-run summary predates readonly consumer counters")
    assert aggregate["premap_consumer_readonly_lookup_count"] == real_handle_hits
    assert aggregate["premap_consumer_readonly_handle_hit_rate"] == 1.0
    assert aggregate["premap_consumer_readonly_evicted_before_consume_count"] == 0
    assert aggregate["premap_consumer_readonly_stale_handle_count"] == 0
    assert aggregate["premap_consumer_readonly_handle_parity_ok_rate"] == 1.0
    assert aggregate["premap_consumer_error_count"] == 0
