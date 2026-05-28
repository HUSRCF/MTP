from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_premap_online_native_stub_canary import (
    build_parser,
    exported_input_from_performance,
    finalize_report_with_artifact_check,
    run_canary,
    trace_output_dir,
)


def test_trace_output_dir_resolves_repo_relative_path(tmp_path: Path, monkeypatch):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)

    assert trace_output_dir(config) == tmp_path / "outputs/example"


def test_exported_input_from_performance_requires_current_run_path(tmp_path: Path):
    online_input = tmp_path / "online_input.json"
    online_input.write_text("{}\n", encoding="utf-8")
    perf = tmp_path / "performance_summary.json"
    perf.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 1,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": str(
                    online_input
                ),
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [
                    str(online_input)
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert exported_input_from_performance(perf) == online_input


def test_exported_input_from_performance_rejects_unlisted_first_path(tmp_path: Path):
    online_input = tmp_path / "online_input.json"
    online_input.write_text("{}\n", encoding="utf-8")
    perf = tmp_path / "performance_summary.json"
    perf.write_text(
        json.dumps(
            {
                "runtime_shadow_premap_native_typed_consumer_input_export_enabled": True,
                "runtime_shadow_premap_native_typed_consumer_input_export_count": 1,
                "runtime_shadow_premap_native_typed_consumer_input_export_first_path": str(
                    online_input
                ),
                "runtime_shadow_premap_native_typed_consumer_input_export_paths": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="first_path is not listed"):
        exported_input_from_performance(perf)


def test_run_canary_dry_run_includes_compact_preflight_status(
    tmp_path: Path,
    monkeypatch,
):
    config = tmp_path / "trace.yaml"
    config.write_text("output_dir: outputs/example\n", encoding="utf-8")

    import scripts.run_premap_online_native_stub_canary as canary

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    status_output = tmp_path / "status.json"
    args = build_parser().parse_args(
        [
            "--trace-config",
            str(config),
            "--stub-output-json",
            str(tmp_path / "stub.json"),
            "--per-field-stub-output-json",
            str(tmp_path / "stub_per_field.json"),
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(status_output),
            "--output-json",
            str(tmp_path / "runner.json"),
            "--dry-run",
        ]
    )

    result = run_canary(args)

    assert result["passed"] is True
    assert "preflight_status" in result["steps"]
    assert "native_stub_per_field" in result["steps"]
    assert result["preflight_status_output_json"] == str(status_output)
    per_field_cmd = result["steps"]["native_stub_per_field"]["cmd"]
    assert str(tmp_path / "stub_per_field.json") in per_field_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR" in per_field_cmd
    assert "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY" not in per_field_cmd
    assert "--defer-online-prelaunch-runner-evidence" in result["steps"]["preflight"]["cmd"]
    assert "--summary-only" in result["steps"]["preflight_status"]["cmd"]
    assert (
        "--defer-online-prelaunch-runner-evidence"
        in result["steps"]["preflight_status"]["cmd"]
    )
    assert "runtime_gate_evidence_deferred_count" in result["preflight_status_summary"]
    assert (
        "strict_default_gate_evidence_deferred_count"
        in result["preflight_status_summary"]
    )


def test_finalize_report_with_artifact_check_records_summary(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    artifact_output = tmp_path / "artifact_check.json"

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        assert "scripts/check_premap_online_native_stub_canary_artifacts.py" in cmd
        assert dry_run is False
        assert allow_failure is True
        assert env["PYTHONPATH"].startswith(str(tmp_path))
        output_index = cmd.index("--output-json") + 1
        assert Path(cmd[output_index]) == artifact_output
        artifact_output.write_text(
            json.dumps(
                {
                    "passed": True,
                    "failures": [],
                    "runner_stub_row_count": 4,
                    "runner_stub_row_ok_count": 4,
                    "stage1_deferred_count": 1,
                    "final_deferred_count": 0,
                    "status_deferred_count": 0,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {"cmd": cmd, "returncode": 0}

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(canary, "_run", fake_run)
    args = build_parser().parse_args(
        [
            "--preflight-output-json",
            str(tmp_path / "preflight.json"),
            "--preflight-status-output-json",
            str(tmp_path / "status.json"),
            "--artifact-check-output-json",
            str(artifact_output),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": [], "steps": {}}

    result = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=tmp_path / "runner.json",
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["artifact_check_output_json"] == str(artifact_output)
    assert result["artifact_check_summary"] == {
        "passed": True,
        "failures": [],
        "runner_stub_row_count": 4,
        "runner_stub_row_ok_count": 4,
        "stage1_deferred_count": 1,
        "final_deferred_count": 0,
        "status_deferred_count": 0,
    }
    assert "artifact_check" in result["steps"]


def test_finalize_report_with_artifact_check_records_failure_without_raising(
    tmp_path: Path,
    monkeypatch,
):
    import scripts.run_premap_online_native_stub_canary as canary

    artifact_output = tmp_path / "artifact_check.json"

    def fake_run(cmd, *, env, dry_run, allow_failure=False):
        assert allow_failure is True
        artifact_output.write_text(
            json.dumps(
                {
                    "passed": False,
                    "failures": ["runner_not_passed"],
                    "runner_stub_row_count": 4,
                    "runner_stub_row_ok_count": 4,
                    "stage1_deferred_count": 1,
                    "final_deferred_count": 0,
                    "status_deferred_count": 0,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {"cmd": cmd, "returncode": 1}

    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(canary, "_run", fake_run)
    args = build_parser().parse_args(
        [
            "--artifact-check-output-json",
            str(artifact_output),
            "--output-json",
            str(tmp_path / "runner.json"),
        ]
    )
    payload = {"passed": True, "failures": [], "steps": {}}

    result = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=tmp_path / "runner.json",
    )

    assert result["passed"] is False
    assert result["failures"] == ["artifact_consistency_check_failed"]
    assert result["artifact_check_summary"]["passed"] is False
    assert result["artifact_check_summary"]["failures"] == ["runner_not_passed"]
    assert result["steps"]["artifact_check"]["returncode"] == 1
