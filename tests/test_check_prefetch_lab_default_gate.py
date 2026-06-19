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
