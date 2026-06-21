from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.check_prefetch_lab_default_gate import (
    check_prefetch_lab_default_gate,
    main,
)

_FULL_FETCH_DECISION_NOOP_FIELDS = {
    "payload_bytes": 0,
    "payload_transfer_enabled": False,
    "payload_deref_allowed": False,
    "ready_credit": False,
    "ready_before_demand_credit": False,
    "real_ready_credit_granted": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "uses_current_wna16_args": False,
    "passes_current_wna16_args": False,
    "measures_tpot": False,
    "measures_vllm_latency": False,
}


def _write_fixture(tmp_path: Path, *, allow_full_fetch: bool = False) -> Path:
    ready = tmp_path / "ready_gate.json"
    ready.write_text(
        json.dumps({"passed": True, "allow_full_fetch": allow_full_fetch}),
        encoding="utf-8",
    )
    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_stream_lookahead",
                "current_lookahead_us": 0.0,
                "required_stream_lookahead_us": 2400000.0,
                "lookahead_deficit_us": 2400000.0,
                "first_model_passing_lookahead_us": 2400000.0,
                "metadata_premap_runtime_preferred": True,
                "descriptor_prep_runtime_preferred": True,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_feasibility = tmp_path / "stream_feasibility.json"
    stream_feasibility.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_feasibility",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "current_runtime_satisfies_model": False,
                "feasible_within_configured_token_window": True,
                "min_required_lead_tokens": 24,
                "max_required_lead_tokens": 48,
                "min_deficit_lead_tokens": 24,
                "max_deficit_lead_tokens": 48,
                "max_candidate_lead_tokens": 64,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_lead = tmp_path / "stream_lead.json"
    stream_lead.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_lead_token_sweep",
                "passed": True,
                "full_fetch_allowed": False,
                "full_fetch_runtime_allowed": False,
                "event_timing_mode": "token_index",
                "token_timing_enabled": True,
                "decode_token_us": 75000.0,
                "first_model_passing_lead_tokens": 32,
                "first_model_passing_lookahead_us": 2400000.0,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    summary = tmp_path / "metadata_premap.json"
    summary.write_text(
        json.dumps(
            {
                "ok": True,
                "metadata_positive_count": 0,
                "premap_positive_count": 4,
            }
        ),
        encoding="utf-8",
    )
    capacity = tmp_path / "capacity.yaml"
    capacity.write_text(
        yaml.safe_dump(
            {
                "capacity_gate": {
                    "recommended_capacity_entries": 12288,
                    "no_eviction_capacity_entries": 12288,
                }
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "gate.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "gate_id": "test-gate",
                "full_fetch": {
                    "default_enabled": False,
                    "ready_time_gate_report": str(ready),
                    "stream_decision_gate_report": str(stream_decision),
                    "stream_earlier_issue_feasibility_report": str(
                        stream_feasibility
                    ),
                    "stream_earlier_issue_lead_token_sweep_report": str(stream_lead),
                },
                "metadata": {
                    "default_enabled": False,
                    "summary": str(summary),
                    "max_default_positive_count": 0,
                },
                "premap": {
                    "default_enabled": True,
                    "summary": str(summary),
                    "min_positive_count": 4,
                    "capacity_gate": str(capacity),
                    "min_capacity_entries": 12288,
                },
            }
        ),
        encoding="utf-8",
    )
    return config


def test_prefetch_lab_default_gate_passes_low_risk_premap_path(tmp_path: Path):
    result = check_prefetch_lab_default_gate(_write_fixture(tmp_path), root=tmp_path)

    assert result["passed"] is True
    assert result["decisions"] == {
        "full_fetch": "blocked_by_ready_time_measured_copy",
        "metadata": "shadow_only",
        "premap": "lab_enabled_descriptor_prep_only",
    }
    assert result["sections"]["premap"]["recommended_capacity_entries"] == 12288


def test_prefetch_lab_default_gate_rejects_full_fetch_allow_report(tmp_path: Path):
    result = check_prefetch_lab_default_gate(
        _write_fixture(tmp_path, allow_full_fetch=True),
        root=tmp_path,
    )

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_allows_full_fetch" in result["failures"]


def test_prefetch_lab_default_gate_rejects_missing_stream_reports(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["full_fetch"].pop("stream_decision_gate_report")
    payload["full_fetch"].pop("stream_earlier_issue_feasibility_report")
    payload["full_fetch"].pop("stream_earlier_issue_lead_token_sweep_report")
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_report_missing" in result["failures"]
    assert "full_fetch:stream_feasibility_report_missing" in result["failures"]
    assert "full_fetch:stream_lead_token_sweep_report_missing" in result["failures"]


def test_prefetch_lab_default_gate_accepts_full_fetch_decision_gate(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_ready_time_and_lookahead",
                "current_deadline_us": 200.0,
                "current_lookahead_us": 0.0,
                "first_model_passing_deadline_us": 4000.0,
                "first_model_passing_lookahead_us": 3800.0,
                "required_lookahead_slack_us": 4000.0,
                "required_issue_to_demand_lookahead_us": 3800.0,
                "slack_deficit_us": 3800.0,
                "lookahead_deficit_us": 3800.0,
                "ready_time_model_slack_satisfied": False,
                "ready_time_model_lookahead_satisfied": False,
                "ready_time_any_model_route_satisfied": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)
    full_fetch = result["sections"]["full_fetch"]

    assert result["passed"] is True
    assert full_fetch["ready_time_allow_full_fetch"] is False
    assert (
        full_fetch["ready_time_decision_reason"]
        == "insufficient_ready_time_and_lookahead"
    )
    assert full_fetch["ready_time_current_deadline_us"] == 200.0
    assert full_fetch["ready_time_current_lookahead_us"] == 0.0
    assert full_fetch["ready_time_first_model_passing_deadline_us"] == 4000.0
    assert full_fetch["ready_time_first_model_passing_lookahead_us"] == 3800.0
    assert full_fetch["ready_time_required_lookahead_slack_us"] == 4000.0
    assert (
        full_fetch["ready_time_required_issue_to_demand_lookahead_us"] == 3800.0
    )
    assert full_fetch["ready_time_slack_deficit_us"] == 3800.0
    assert full_fetch["ready_time_lookahead_deficit_us"] == 3800.0
    assert full_fetch["ready_time_model_slack_satisfied"] is False
    assert full_fetch["ready_time_model_lookahead_satisfied"] is False
    assert full_fetch["ready_time_any_model_route_satisfied"] is False


def test_prefetch_lab_default_gate_accepts_stream_full_fetch_block_evidence(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))

    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "decision": "block_full_fetch_insufficient_stream_lookahead",
                "full_fetch_runtime_allowed": False,
                "full_fetch_block_reason": "insufficient_stream_lookahead",
                "current_lookahead_us": 0.0,
                "required_stream_lookahead_us": 2400000.0,
                "lookahead_deficit_us": 2400000.0,
                "first_model_passing_lookahead_us": 2400000.0,
                "metadata_premap_runtime_preferred": True,
                "descriptor_prep_runtime_preferred": True,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_feasibility = tmp_path / "stream_feasibility.json"
    stream_feasibility.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_feasibility",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                "current_runtime_satisfies_model": False,
                "feasible_within_configured_token_window": True,
                "min_required_lead_tokens": 24,
                "max_required_lead_tokens": 48,
                "min_deficit_lead_tokens": 24,
                "max_deficit_lead_tokens": 48,
                "max_candidate_lead_tokens": 64,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    stream_lead = tmp_path / "stream_lead.json"
    stream_lead.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_earlier_issue_lead_token_sweep",
                "passed": True,
                "full_fetch_allowed": False,
                "full_fetch_runtime_allowed": False,
                "event_timing_mode": "token_index",
                "token_timing_enabled": True,
                "decode_token_us": 75000.0,
                "first_model_passing_lead_tokens": 32,
                "first_model_passing_lookahead_us": 2400000.0,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"].update(
        {
            "stream_decision_gate_report": str(stream_decision),
            "stream_earlier_issue_feasibility_report": str(stream_feasibility),
            "stream_earlier_issue_lead_token_sweep_report": str(stream_lead),
        }
    )
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)
    full_fetch = result["sections"]["full_fetch"]

    assert result["passed"] is True
    assert full_fetch["stream_decision_gate_present"] is True
    assert full_fetch["stream_decision_gate_passed"] is True
    assert full_fetch["stream_full_fetch_runtime_allowed"] is False
    assert full_fetch["stream_decision"] == (
        "block_full_fetch_insufficient_stream_lookahead"
    )
    assert full_fetch["stream_required_lookahead_us"] == 2400000.0
    assert full_fetch["stream_feasibility_passed"] is True
    assert full_fetch["stream_current_runtime_satisfies_model"] is False
    assert full_fetch["stream_max_required_lead_tokens"] == 48
    assert full_fetch["stream_lead_token_sweep_passed"] is True
    assert full_fetch["stream_lead_token_sweep_event_timing_mode"] == "token_index"
    assert full_fetch["stream_lead_token_sweep_token_timing_enabled"] is True
    assert full_fetch["stream_first_model_passing_lead_tokens"] == 32


def test_prefetch_lab_default_gate_rejects_unsafe_stream_evidence(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = tmp_path / "stream_decision.json"
    fields = dict(_FULL_FETCH_DECISION_NOOP_FIELDS)
    fields["payload_transfer_enabled"] = True
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "full_fetch_runtime_allowed": True,
                **fields,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_allows_full_fetch" in result["failures"]
    assert "full_fetch:stream_decision_gate_payload_transfer_enabled_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_stream_wna16_arg_usage(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = tmp_path / "stream_decision.json"
    fields = dict(_FULL_FETCH_DECISION_NOOP_FIELDS)
    fields["uses_current_wna16_args"] = True
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                **fields,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_uses_current_wna16_args_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_stream_passed_non_bool(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    stream_decision = tmp_path / "stream_decision.json"
    stream_decision.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
                "passed": "true",
                "full_fetch_runtime_allowed": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )
    payload["full_fetch"]["stream_decision_gate_report"] = str(stream_decision)
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:stream_decision_gate_passed_not_bool" in result["failures"]
    assert "full_fetch:stream_decision_gate_not_passed" in result["failures"]


def test_prefetch_lab_default_gate_rejects_malformed_full_fetch_decision_gate(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "wrong_kind",
                "passed": True,
                "full_fetch_runtime_allowed": True,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_artifact_kind_mismatch" in result[
        "failures"
    ]


def test_prefetch_lab_default_gate_rejects_decision_gate_missing_runtime_allow(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
                "passed": True,
                "allow_full_fetch": False,
                **_FULL_FETCH_DECISION_NOOP_FIELDS,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_missing_full_fetch_runtime_allowed" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_rejects_decision_gate_payload_or_kernel_side_effect(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    fields = dict(_FULL_FETCH_DECISION_NOOP_FIELDS)
    fields["payload_transfer_enabled"] = True
    fields["kernel_arg_pass_allowed"] = True
    ready.write_text(
        json.dumps(
            {
                "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
                "passed": True,
                "full_fetch_runtime_allowed": False,
                **fields,
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "full_fetch:ready_time_gate_report_payload_transfer_enabled_not_false" in (
        result["failures"]
    )
    assert "full_fetch:ready_time_gate_report_kernel_arg_pass_allowed_not_false" in (
        result["failures"]
    )


def test_prefetch_lab_default_gate_sanitizes_malformed_ready_time_diagnostics(
    tmp_path: Path,
):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    ready = Path(payload["full_fetch"]["ready_time_gate_report"])
    ready.write_text(
        json.dumps(
            {
                "passed": True,
                "allow_full_fetch": False,
                "decision_reason": "full_fetch_threshold_not_met",
                "threshold_failures": "not-a-list",
                "metrics": {
                    "demand_hit_rate": True,
                    "ready_late_miss_rate": False,
                    "used_per_issued_fetch": "0.0",
                    "issued_fetch_count": True,
                    "used_fetch_count": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)
    full_fetch = result["sections"]["full_fetch"]

    assert result["passed"] is True
    assert full_fetch["ready_time_threshold_failures"] == []
    assert full_fetch["ready_time_demand_hit_rate"] is None
    assert full_fetch["ready_time_ready_late_miss_rate"] is None
    assert full_fetch["ready_time_used_per_issued_fetch"] == 0.0
    assert full_fetch["ready_time_issued_fetch_count"] is None
    assert full_fetch["ready_time_used_fetch_count"] == 0


def test_prefetch_lab_default_gate_rejects_under_capacity_premap(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    capacity = Path(payload["premap"]["capacity_gate"])
    capacity.write_text(
        yaml.safe_dump(
            {
                "capacity_gate": {
                    "recommended_capacity_entries": 8192,
                    "no_eviction_capacity_entries": 12288,
                }
            }
        ),
        encoding="utf-8",
    )

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "premap:recommended_capacity_below_min:8192" in result["failures"]
    assert "premap:no_eviction_capacity_above_recommended:12288>8192" in result[
        "failures"
    ]


def test_prefetch_lab_default_gate_rejects_metadata_default_enabled(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["metadata"]["default_enabled"] = True
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "metadata:metadata_default_enabled" in result["failures"]


def test_prefetch_lab_default_gate_reports_missing_capacity_gate(tmp_path: Path):
    config = _write_fixture(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["premap"]["capacity_gate"] = str(tmp_path / "missing.yaml")
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = check_prefetch_lab_default_gate(config, root=tmp_path)

    assert result["passed"] is False
    assert "premap:capacity_gate_load_failed:FileNotFoundError" in result["failures"]


def test_prefetch_lab_default_gate_cli_writes_report(tmp_path: Path):
    config = _write_fixture(tmp_path)
    output = tmp_path / "report.json"

    exit_code = main([str(config), "--root", str(tmp_path), "--output-json", str(output)])

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True
