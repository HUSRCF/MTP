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
            "premap_consumer_real_descriptor_handle_hit_count": 20,
            "premap_consumer_real_descriptor_handle_packed_weight_hit_count": 20,
            "premap_consumer_real_descriptor_handle_packed_weight_miss_count": 0,
            "premap_consumer_real_descriptor_handle_scale_metadata_hit_count": 20,
            "premap_consumer_real_descriptor_handle_scale_metadata_miss_count": 0,
            "premap_consumer_real_descriptor_handle_aux_metadata_hit_count": 20,
            "premap_consumer_real_descriptor_handle_aux_metadata_miss_count": 0,
            "premap_consumer_real_descriptor_handle_resolver_disabled_count": 0,
            "premap_consumer_real_descriptor_handle_consumer_layer_missing_count": 0,
            "premap_consumer_real_descriptor_handle_expert_map_miss_count": 0,
            "premap_consumer_real_descriptor_handle_no_handle_parts_count": 0,
            "premap_consumer_lookup_after_prepare_rate": 1.0,
            "premap_consumer_real_descriptor_handle_binding_mismatch_count": 0,
            "premap_consumer_readonly_lookup_count": 20,
            "premap_consumer_readonly_handle_hit_rate": 1.0,
            "premap_consumer_readonly_evicted_before_consume_count": 0,
            "premap_consumer_readonly_stale_handle_count": 0,
            "premap_consumer_readonly_handle_parity_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_attempted_count": 2,
            "premap_consumer_descriptor_prep_executed_count": 2,
            "premap_consumer_descriptor_prep_lookup_count": 20,
            "premap_consumer_descriptor_prep_handle_count": 20,
            "premap_consumer_descriptor_prep_missing_handle_count": 0,
            "premap_consumer_descriptor_prep_handle_hit_rate": 1.0,
            "premap_consumer_descriptor_prep_descriptor_ptr_count": 20,
            "premap_consumer_descriptor_prep_packed_weight_descriptor_count": 20,
            "premap_consumer_descriptor_prep_scale_metadata_handle_count": 20,
            "premap_consumer_descriptor_prep_real_handle_count": 20,
            "premap_consumer_descriptor_prep_real_handle_miss_count": 0,
            "premap_consumer_descriptor_prep_real_handle_hit_rate": 1.0,
            "premap_consumer_descriptor_prep_real_handle_backed_rate": 1.0,
            "premap_consumer_descriptor_prep_execution_ok_rate": 1.0,
            "premap_consumer_descriptor_prep_execution_ok_attempted_rate": 1.0,
            "premap_consumer_descriptor_prep_blocked_count": 0,
            "premap_consumer_descriptor_prep_blocked_attempted_rate": 0.0,
            "premap_consumer_payload_violation_count": 0,
            "premap_consumer_router_change_violation_count": 0,
            "premap_consumer_descriptor_order_change_violation_count": 0,
            "premap_consumer_ready_credit_violation_count": 0,
            "premap_consumer_error_count": 0,
        },
    }


def test_premap_longrun_audit_gate_accepts_read_only_handle_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["metrics"]["premap_summary_count"] == 2


def test_premap_longrun_audit_gate_accepts_descriptor_prep_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_descriptor_prep"] is True
    assert result["metrics"]["premap_consumer_descriptor_prep_attempted_count"] == 2


def test_premap_longrun_audit_gate_accepts_real_descriptor_prep_contract():
    result = check_summary(
        _passing_summary(),
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["require_real_descriptor_prep"] is True
    assert result["metrics"]["premap_consumer_descriptor_prep_real_handle_count"] == 20
    assert (
        result["metrics"]["premap_consumer_descriptor_prep_real_handle_hit_rate"]
        == 1.0
    )


def test_premap_longrun_audit_gate_rejects_descriptor_prep_instability():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_descriptor_prep_executed_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_missing_handle_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_handle_hit_rate"] = 0.95
    summary["aggregate"][
        "premap_consumer_descriptor_prep_execution_ok_attempted_rate"
    ] = 0.5
    summary["aggregate"]["premap_consumer_descriptor_prep_blocked_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_blocked_attempted_rate"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
    )

    assert result["passed"] is False
    assert "descriptor_prep_executed_count_mismatch=1!=2" in result["failures"]
    assert "descriptor_prep_missing_handle_count_nonzero=1" in result["failures"]
    assert "premap_consumer_descriptor_prep_handle_hit_rate_not_one" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_execution_ok_attempted_rate_not_one"
        in result["failures"]
    )
    assert "descriptor_prep_blocked_count_nonzero" in result["failures"]
    assert "descriptor_prep_blocked_attempted_rate_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_rejects_real_descriptor_prep_instability():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_count"] = 19
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_miss_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_hit_rate"] = 0.95
    summary["aggregate"]["premap_consumer_descriptor_prep_real_handle_backed_rate"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
        require_real_descriptor_prep=True,
    )

    assert result["passed"] is False
    assert "descriptor_prep_real_handle_count_mismatch=19!=20" in result["failures"]
    assert "descriptor_prep_real_handle_miss_count_nonzero=1" in result["failures"]
    assert (
        "premap_consumer_descriptor_prep_real_handle_hit_rate_not_one"
        in result["failures"]
    )
    assert (
        "premap_consumer_descriptor_prep_real_handle_backed_rate_not_one"
        in result["failures"]
    )


def test_premap_longrun_audit_gate_rejects_partial_descriptor_prep_coverage():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_descriptor_prep_attempted_count"] = 1
    summary["aggregate"]["premap_consumer_descriptor_prep_executed_count"] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=True,
    )

    assert result["passed"] is False
    assert "descriptor_prep_attempted_count_mismatch=1!=2" in result["failures"]


def test_premap_longrun_audit_gate_rejects_payload_and_mismatch():
    summary = _passing_summary()
    summary["event_counts"]["outcome_aggregate"] = 1
    summary["aggregate"]["premap_summary_payload_bytes"] = 128
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_binding_mismatch_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "unexpected_event_types=['outcome_aggregate']" in result["failures"]
    assert "premap_payload_bytes_nonzero" in result["failures"]
    assert "real_descriptor_handle_binding_mismatch_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_rejects_noop_contract_violations():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_payload_violation_count"] = 1
    summary["aggregate"]["premap_consumer_router_change_violation_count"] = 2
    summary["aggregate"]["premap_consumer_descriptor_order_change_violation_count"] = 3
    summary["aggregate"]["premap_consumer_ready_credit_violation_count"] = 4

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "premap_consumer_payload_violation_count_nonzero=1" in result["failures"]
    assert "premap_consumer_router_change_violation_count_nonzero=2" in result["failures"]
    assert (
        "premap_consumer_descriptor_order_change_violation_count_nonzero=3"
        in result["failures"]
    )
    assert "premap_consumer_ready_credit_violation_count_nonzero=4" in result["failures"]


def test_premap_longrun_audit_gate_rejects_capacity_and_reuse_regression():
    summary = _passing_summary()
    summary["aggregate"]["premap_address_resident_count_max"] = 13
    summary["aggregate"]["premap_address_reuse_rate_mean"] = 0.5

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "resident_count_exceeds_capacity=13>12" in result["failures"]
    assert "premap_address_reuse_rate_below_threshold" in result["failures"]


def test_premap_longrun_audit_gate_rejects_real_handle_source_misses():
    summary = _passing_summary()
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_scale_metadata_hit_count"
    ] = 19
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_aux_metadata_miss_count"
    ] = 1
    summary["aggregate"][
        "premap_consumer_real_descriptor_handle_no_handle_parts_count"
    ] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert (
        "real_descriptor_handle_scale_metadata_hit_count_mismatch=19!=20"
        in result["failures"]
    )
    assert "real_descriptor_handle_aux_metadata_miss_count_nonzero=1" not in result["failures"]
    assert "real_descriptor_handle_no_handle_parts_count_nonzero=1" in result["failures"]


def test_premap_longrun_audit_gate_rejects_readonly_consumer_instability():
    summary = _passing_summary()
    summary["aggregate"]["premap_consumer_readonly_handle_hit_rate"] = 0.95
    summary["aggregate"]["premap_consumer_readonly_evicted_before_consume_count"] = 1
    summary["aggregate"]["premap_consumer_readonly_stale_handle_count"] = 1

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "premap_consumer_readonly_handle_hit_rate_not_one" in result["failures"]
    assert "readonly_evicted_before_consume_nonzero" in result["failures"]
    assert "readonly_stale_handle_nonzero" in result["failures"]


def test_premap_longrun_audit_gate_allows_legacy_summary_without_readonly_requirement():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_readonly_"):
            summary["aggregate"].pop(key)

    result = check_summary(summary, max_capacity=12, min_reuse_rate=0.98)

    assert result["passed"] is True
    assert result["require_readonly_consumer"] is False


def test_premap_longrun_audit_gate_rejects_missing_readonly_when_required():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_readonly_"):
            summary["aggregate"].pop(key)

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
    )

    assert result["passed"] is False
    assert "readonly_consumer_fields_missing" in result["failures"]


def test_premap_longrun_audit_gate_allows_zero_descriptor_prep_placeholders_without_requirement():
    summary = _passing_summary()
    for key in list(summary["aggregate"]):
        if key.startswith("premap_consumer_descriptor_prep_"):
            summary["aggregate"][key] = 0

    result = check_summary(
        summary,
        max_capacity=12,
        min_reuse_rate=0.98,
        require_readonly_consumer=True,
        require_descriptor_prep=False,
    )

    assert result["passed"] is True
    assert result["require_descriptor_prep"] is False
