from __future__ import annotations

import json
from pathlib import Path

from scripts import run_payload_cache_consumer_visible_hit_blocked_gate as gate


def test_payload_cache_consumer_visible_hit_blocked_gate_report() -> None:
    report = gate.build_report()

    assert report["passed"] is True
    assert report["failures"] == []
    assert report["schema_version"] == 1
    assert report["source"] == "payload_cache_consumer_visible_hit_blocked_gate"
    assert report["artifact_kind"] == "payload_cache_consumer_visible_hit_blocked_gate"
    assert report["cell_count"] == 60
    assert report["event_timing_mode"] == "token_index"
    assert report["first_model_passing_lookahead_us"] == 2_400_000.0
    assert report["decision"] == "blocked"
    assert report["block_reason"] == "payload_transfer_disabled"
    assert report["execution_mode"] == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_demand_hit_publication_blocked_canary"
    )
    assert report["request_source"] == "queue_budget_first_model_passing_cell"
    assert report["request_layer_idx"] == 0
    assert report["request_expert_idx"] == 0
    assert report["requested_payload_bytes"] == 64
    assert report["request_matches_envelope_source_binding"] is True
    assert report["source_issue_packet_count"] == 28
    assert report["source_issue_unique_key_count"] == 16
    assert report["source_queue_budget_capacity"] == 4096
    assert report["source_issue_lead_tokens"] == 8
    assert report["source_queue_deadline_us"] == 100.0
    assert report["payload_bytes"] == 0
    assert report["resident_payload_bytes"] == 0
    assert report["dereferenced_payload_bytes"] == 0
    assert report["demand_hit_payload_bytes"] == 0
    assert report["issued_payload_count"] == 0
    assert report["resident_payload_count"] == 0
    assert report["demand_hit_count"] == 0
    assert report["demand_hit_publication_count"] == 0
    assert report["consumer_visible_payload_hit_count"] == 0
    assert report["payload_deref_attempted"] is False
    assert report["payload_handle_deref_attempted"] is False
    assert report["demand_hit_publication_allowed"] is False
    assert report["demand_hit_published"] is False
    assert report["consumer_visible_payload_hit"] is False
    assert report["prefetched_demand_hit"] is False
    assert report["ready_credit"] is False
    assert report["ready_before_demand_credit"] is False
    assert report["real_ready_credit_granted"] is False
    assert report["live_payload_runtime_enabled"] is False
    assert report["payload_transfer_runtime_enabled"] is False
    assert report["payload_deref_allowed"] is False
    assert report["payload_deref_runtime_allowed"] is False
    assert report["kernel_arg_pass_allowed"] is False
    assert report["passed_to_kernel"] is False
    assert report["changes_kernel_launch_args"] is False
    assert report["full_fetch_runtime_allowed"] is False
    assert report["uses_current_wna16_args"] is False
    assert report["passes_current_wna16_args"] is False
    assert report["measures_tpot"] is False
    assert report["measures_vllm_latency"] is False
    assert report["live_runtime_instantiated"] is False

    canary = report["canary"]
    assert canary["stage"] == (
        "payload_cache_live_runtime_adapter_"
        "payload_issue_demand_hit_publication_blocked_canary"
    )
    assert canary["payload_issue_demand_hit_publication_schema"] == (
        "payload_cache_runtime_payload_issue_demand_hit_publication_v1"
    )
    assert canary["payload_issue_demand_hit_publication_canary_created"] is True
    assert canary["payload_issue_payload_deref_consumed"] is True
    assert canary["demand_hit_publication_checked"] is True
    assert canary["demand_hit_publication_rejected"] is True
    assert canary["decision"] == "blocked"
    assert canary["block_reason"] == "payload_transfer_disabled"
    assert canary["request_source"] == "queue_budget_first_model_passing_cell"
    assert canary["source_queue_budget_capacity"] == 4096
    assert canary["source_issue_packet_count"] == 28
    assert canary["source_issue_unique_key_count"] == 16
    assert canary["source_issue_lead_tokens"] == 8
    assert canary["source_queue_deadline_us"] == 100.0


def test_payload_cache_consumer_visible_hit_blocked_gate_rejects_source_binding_drift() -> None:
    report = gate.build_report(
        request_source_binding_overrides={
            "first_model_passing_capacity": 8192,
        },
    )

    assert report["passed"] is False
    assert "request_source_binding_mismatch" in report["failures"]
    assert report["request_matches_envelope_source_binding"] is False
    assert report["source_queue_budget_capacity"] == 8192
    assert report["canary"]["source_queue_budget_capacity"] == 8192
    assert report["payload_bytes"] == 0
    assert report["consumer_visible_payload_hit"] is False
    assert report["passed_to_kernel"] is False

    for field_name, drift_value in (
        ("shifted_issue_accounted_packet_count", 29),
        ("shifted_issue_unique_issue_key_count", 17),
        ("first_model_passing_issue_lead_tokens", 9),
        ("first_model_passing_queue_deadline_us", 200.0),
    ):
        drift_report = gate.build_report(
            request_source_binding_overrides={field_name: drift_value},
        )
        assert drift_report["passed"] is False
        assert "request_source_binding_mismatch" in drift_report["failures"]
        assert drift_report["request_matches_envelope_source_binding"] is False


def test_payload_cache_consumer_visible_hit_blocked_gate_cli(tmp_path: Path) -> None:
    output = tmp_path / "consumer_visible_hit_blocked_gate.json"

    rc = gate.main(["--output-json", str(output)])

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["failures"] == []
    assert payload["schema_version"] == 1
    assert payload["request_matches_envelope_source_binding"] is True
    assert payload["payload_bytes"] == 0
    assert payload["demand_hit_payload_bytes"] == 0
    assert payload["demand_hit_publication_allowed"] is False
    assert payload["demand_hit_published"] is False
    assert payload["consumer_visible_payload_hit"] is False
    assert payload["payload_deref_attempted"] is False
    assert payload["payload_handle_deref_attempted"] is False
    assert payload["passed_to_kernel"] is False
    assert payload["changes_kernel_launch_args"] is False
