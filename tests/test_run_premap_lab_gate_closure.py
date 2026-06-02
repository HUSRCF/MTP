from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_lab_gate_closure import _build_parser, main, run_closure


def test_run_premap_lab_gate_closure_dry_run_records_canonical_steps(
    tmp_path: Path,
):
    args = _build_parser().parse_args(
        [
            "--dry-run",
            "--arg-slot-runner-json",
            str(tmp_path / "arg_slot_runner.json"),
            "--arg-slot-stub-json",
            str(tmp_path / "arg_slot_stub.json"),
            "--arg-slot-merged-json",
            str(tmp_path / "arg_slot_merged.json"),
            "--native-runner-json",
            str(tmp_path / "native_runner.json"),
            "--full-preflight-json",
            str(tmp_path / "full_preflight.json"),
            "--summary-json",
            str(tmp_path / "summary.json"),
            "--summary-check-json",
            str(tmp_path / "summary.check.json"),
            "--artifact-check-json",
            str(tmp_path / "artifact_check.json"),
            "--output-json",
            str(tmp_path / "closure.json"),
        ]
    )

    result = run_closure(args)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert list(result["steps"]) == [
        "arg_slot_runner",
        "full_preflight",
        "summary_preflight",
        "summary_check",
        "native_artifact_check",
    ]
    artifact_cmd = result["steps"]["native_artifact_check"]["cmd"]
    assert "scripts/check_premap_online_native_stub_canary_artifacts.py" in artifact_cmd
    assert "--preflight-json" not in artifact_cmd
    assert "--status-json" not in artifact_cmd
    assert "--runner-json" in artifact_cmd


def test_run_premap_lab_gate_closure_main_writes_report(tmp_path: Path):
    output_json = tmp_path / "closure.json"

    exit_code = main(["--dry-run", "--output-json", str(output_json)])

    assert exit_code == 0
    result = json.loads(output_json.read_text(encoding="utf-8"))
    assert result["passed"] is True
    assert result["source"] == "premap_lab_gate_closure"
    assert result["dry_run"] is True
