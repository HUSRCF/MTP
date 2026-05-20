import json

import pytest

from scripts.summarize_runtime_shadow_mixed_diag import (
    StrictValidationError,
    summarize,
    validate_mixed_diagnostic,
)


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _mixed_rows():
    return [
        {
            "event_type": "decoder_layer_timing",
            "request_id": "sample_0",
            "layer": 0,
            "token_index": 0,
            "decoder_layer_phase": "decode",
            "decoder_layer_elapsed_us": 3.0,
        },
        {
            "event_type": "descriptor_summary_min",
            "request_id": "sample_0",
            "layer": 0,
            "token_index": 0,
            "descriptor_order_policy": "layer_prior_frequency",
            "descriptor_order_execution_mode": "two_level_group_plan",
            "descriptor_order_metrics_mode": "count_only",
            "descriptor_order_build_us": 2.0,
            "descriptor_tile_request_count": 8,
            "descriptor_unique_b_tiles": 8,
            "descriptor_window_count": 1,
            "descriptor_order_gate_allow": True,
        },
        {
            "event_type": "outcome_aggregate",
            "request_id": "sample_0",
            "layer": 0,
            "token_index": 0,
            "outcome_logging_mode": "aggregate",
            "token_count": 1,
            "topk_entry_count": 8,
            "routed_expert_count": 8,
            "top_k": 8,
            "topk_weight_mass_sum": 1.0,
            "top1_weight_sum": 0.25,
            "top1_weight_mean": 0.25,
        },
        {
            "event_type": "premap_summary",
            "request_id": "sample_0",
            "layer": 0,
            "token_index": 0,
            "premap_descriptor_count": 8,
            "premap_actual_bytes": 32768,
            "premap_payload_bytes": 0,
            "premap_changes_router": False,
            "premap_changes_descriptor_order": False,
            "premap_ready_credit": False,
            "premap_full_fetch_count": 0,
            "premap_metadata_count": 0,
            "premap_build_us": 1.0,
            "counter_update_us": 4.0,
            "premap_address_manager_capacity": 16,
            "premap_address_new_count": 8,
            "premap_address_reused_count": 0,
            "premap_address_evicted_count": 0,
            "premap_address_resident_count": 8,
            "premap_address_resident_descriptor_bytes": 32768,
            "premap_address_prepared_descriptor_actual_bytes": 32768,
            "premap_address_reuse_rate": 0.0,
        },
    ]


def test_mixed_diag_summary_strict_passes(tmp_path):
    path = tmp_path / "runtime_shadow.jsonl"
    _write_jsonl(path, _mixed_rows())

    summary = summarize(path)

    validate_mixed_diagnostic(_mixed_rows(), summary, require_decode_phase=True)
    assert summary["event_counts"] == {
        "decoder_layer_timing": 1,
        "descriptor_summary_min": 1,
        "outcome_aggregate": 1,
        "premap_summary": 1,
    }
    assert summary["aggregate"]["premap_summary_payload_bytes"] == 0
    assert summary["descriptor_order_stats"]["descriptor_order_build_us"]["p50"] == 2.0


def test_mixed_diag_summary_includes_premap_consumer_source_aggregate(tmp_path):
    rows = [
        {
            "event_type": "premap_consumer_mapping",
            "premap_consumer_real_descriptor_handle_hit_count": 4,
            "premap_consumer_real_descriptor_handle_miss_count": 0,
            "premap_consumer_real_descriptor_handle_available": True,
            "premap_consumer_real_descriptor_handle_source_hit_counts": {
                "packed_weight": 4,
                "scale_metadata": 4,
                "aux_metadata": 4,
            },
            "premap_consumer_real_descriptor_handle_source_miss_counts": {
                "packed_weight": 0,
                "scale_metadata": 0,
                "aux_metadata": 0,
            },
            "premap_consumer_real_descriptor_handle_miss_reason_counts": {
                "resolver_disabled": 0,
                "consumer_layer_missing": 0,
                "expert_map_miss": 0,
                "no_handle_parts": 0,
            },
        }
    ]
    path = tmp_path / "runtime_shadow.jsonl"
    _write_jsonl(path, rows)

    summary = summarize(path)

    aggregate = summary["aggregate"]
    assert aggregate["premap_consumer_real_descriptor_handle_hit_count"] == 4
    assert aggregate["premap_consumer_real_descriptor_handle_packed_weight_hit_count"] == 4
    assert aggregate["premap_consumer_real_descriptor_handle_scale_metadata_hit_count"] == 4
    assert aggregate["premap_consumer_real_descriptor_handle_aux_metadata_hit_count"] == 4
    assert aggregate["premap_consumer_real_descriptor_handle_no_handle_parts_count"] == 0


def test_mixed_diag_strict_rejects_missing_core_event(tmp_path):
    rows = [row for row in _mixed_rows() if row["event_type"] != "outcome_aggregate"]
    path = tmp_path / "runtime_shadow.jsonl"
    _write_jsonl(path, rows)

    summary = summarize(path)

    with pytest.raises(StrictValidationError, match="missing required event types"):
        validate_mixed_diagnostic(rows, summary)


def test_mixed_diag_strict_rejects_premap_payload(tmp_path):
    rows = _mixed_rows()
    rows[-1] = {**rows[-1], "premap_payload_bytes": 4096}
    path = tmp_path / "runtime_shadow.jsonl"
    _write_jsonl(path, rows)

    summary = summarize(path)

    with pytest.raises(StrictValidationError, match="payload"):
        validate_mixed_diagnostic(rows, summary)


def test_mixed_diag_strict_allows_matching_descriptor_layer_timing(tmp_path):
    rows = _mixed_rows() + [
        {
            "event_type": "descriptor_layer_timing",
            "request_id": "sample_0",
            "layer": 0,
            "token_index": 0,
            "descriptor_layer_elapsed_us": 5.0,
        }
    ]
    path = tmp_path / "runtime_shadow.jsonl"
    _write_jsonl(path, rows)

    summary = summarize(path)

    validate_mixed_diagnostic(rows, summary)


def test_mixed_diag_strict_rejects_descriptor_layer_count_mismatch(tmp_path):
    rows = _mixed_rows() + [
        {
            "event_type": "descriptor_layer_timing",
            "request_id": "sample_0",
            "layer": 0,
            "token_index": 0,
            "descriptor_layer_elapsed_us": 5.0,
        },
        {
            "event_type": "descriptor_layer_timing",
            "request_id": "sample_0",
            "layer": 1,
            "token_index": 0,
            "descriptor_layer_elapsed_us": 6.0,
        },
    ]
    path = tmp_path / "runtime_shadow.jsonl"
    _write_jsonl(path, rows)

    summary = summarize(path)

    with pytest.raises(StrictValidationError, match="descriptor_layer_timing count"):
        validate_mixed_diagnostic(rows, summary)
