from __future__ import annotations

from scripts.check_premap_longrun_audit_gate import check_summary


def _passing_summary() -> dict:
    return {
        "row_count": 4,
        "event_counts": {
            "premap_summary": 2,
            "premap_consumer_mapping": 2,
        },
        "aggregate": {
            "premap_summary_payload_bytes": 0,
            "premap_address_evicted_count": 0,
            "premap_address_eviction_pressure_mean": 0.0,
            "premap_address_resident_count_max": 10,
            "premap_address_reuse_rate_mean": 0.99,
            "premap_consumer_address_hit_rate": 1.0,
            "premap_consumer_descriptor_handle_hit_rate": 1.0,
            "premap_consumer_real_descriptor_handle_hit_rate": 1.0,
            "premap_consumer_lookup_after_prepare_rate": 1.0,
            "premap_consumer_real_descriptor_handle_binding_mismatch_count": 0,
            "premap_consumer_error_count": 0,
        },
    }


def test_premap_longrun_audit_gate_accepts_read_only_handle_contract():
    result = check_summary(_passing_summary(), max_capacity=12, min_reuse_rate=0.98)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"]["premap_summary_count"] == 2


def test_premap_longrun_audit_gate_rejects_payload_and_mismatch():
    summary = _passing_summary()
    summary["event_counts"]["outcome_aggregate"] = 1
    summary["aggregate"]["premap_summary_payload_bytes"] = 128
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_binding_mismatch_count"
    ] = 1

    result = check_summary(summary, max_capacity=12, min_reuse_rate=0.98)

    assert result["passed"] is False
    assert "unexpected_event_types=['outcome_aggregate']" in result["failures"]
    assert "premap_payload_bytes_nonzero" in result["failures"]
    assert "real_descriptor_handle_binding_mismatch_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_rejects_capacity_and_reuse_regression():
    summary = _passing_summary()
    summary["aggregate"]["premap_address_resident_count_max"] = 13
    summary["aggregate"]["premap_address_reuse_rate_mean"] = 0.5

    result = check_summary(summary, max_capacity=12, min_reuse_rate=0.98)

    assert result["passed"] is False
    assert "resident_count_exceeds_capacity=13>12" in result["failures"]
    assert "premap_address_reuse_rate_below_threshold" in result["failures"]
