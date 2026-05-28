from __future__ import annotations

import json
from pathlib import Path

from scripts.check_runtime_gate_evidence_paths import (
    main,
    scan_runtime_gate_evidence_paths,
)


def _write_gate(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_scan_runtime_gate_evidence_paths_summarizes_mixed_runtime_configs(
    tmp_path: Path,
):
    (tmp_path / "configs" / "runtime").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "gate.json").write_text('{"passed": true}\n')
    _write_gate(
        tmp_path / "configs" / "runtime" / "with_evidence.yaml",
        "schema_version: 1\n"
        "evidence_paths:\n"
        "  gate_json: reports/gate.json\n",
    )
    _write_gate(
        tmp_path / "configs" / "runtime" / "without_evidence.yaml",
        "schema_version: 1\n",
    )

    result = scan_runtime_gate_evidence_paths(
        "configs/runtime/*.yaml",
        root=tmp_path,
        require_json=True,
    )

    assert result["passed"] is True
    assert result["gate_count"] == 2
    assert result["passed_gate_count"] == 2
    assert result["evidence_section_present_count"] == 1
    assert result["evidence_section_missing_count"] == 1
    assert result["evidence_path_count"] == 1
    assert result["missing_count"] == 0
    assert result["invalid_json_count"] == 0


def test_scan_runtime_gate_evidence_paths_reports_deferred_labels(
    tmp_path: Path,
):
    (tmp_path / "configs" / "runtime").mkdir(parents=True)
    _write_gate(
        tmp_path / "configs" / "runtime" / "with_deferred.yaml",
        "schema_version: 1\n"
        "evidence_paths:\n"
        "  current_runner: reports/current_runner.json\n",
    )

    result = scan_runtime_gate_evidence_paths(
        "configs/runtime/*.yaml",
        root=tmp_path,
        allow_missing=False,
        deferred_labels={"current_runner"},
    )

    assert result["passed"] is True
    assert result["missing_count"] == 1
    assert result["deferred_count"] == 1
    assert result["results"][0]["rows"][0]["deferred"] is True


def test_scan_runtime_gate_evidence_paths_require_section_fails_non_evidence_config(
    tmp_path: Path,
):
    (tmp_path / "configs" / "runtime").mkdir(parents=True)
    _write_gate(
        tmp_path / "configs" / "runtime" / "without_evidence.yaml",
        "schema_version: 1\n",
    )

    result = scan_runtime_gate_evidence_paths(
        "configs/runtime/*.yaml",
        root=tmp_path,
        allow_missing_section=False,
    )

    assert result["passed"] is False
    assert result["failed_gate_count"] == 1
    assert result["pattern_failure_count"] == 0
    assert result["failures"] == [
        "configs/runtime/without_evidence.yaml:ValueError:Gate artifact has no evidence_paths mapping: "
        f"{tmp_path}/configs/runtime/without_evidence.yaml"
    ]


def test_scan_runtime_gate_evidence_paths_reports_pattern_without_matches(
    tmp_path: Path,
):
    result = scan_runtime_gate_evidence_paths("configs/runtime/*.yaml", root=tmp_path)

    assert result["passed"] is False
    assert result["gate_count"] == 0
    assert result["failed_gate_count"] == 0
    assert result["pattern_failure_count"] == 1
    assert result["failures"] == ["pattern_no_matches:configs/runtime/*.yaml"]


def test_scan_runtime_gate_evidence_paths_cli_writes_summary_json(tmp_path: Path):
    (tmp_path / "configs" / "runtime").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "gate.json").write_text('{"passed": true}\n')
    _write_gate(
        tmp_path / "configs" / "runtime" / "with_evidence.yaml",
        "schema_version: 1\n"
        "evidence_paths:\n"
        "  gate_json: reports/gate.json\n",
    )
    output = tmp_path / "scan.json"

    exit_code = main(
        [
            "--pattern",
            "configs/runtime/*.yaml",
            "--root",
            str(tmp_path),
            "--require-json",
            "--output-json",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["gate_count"] == 1
    assert result["evidence_path_count"] == 1
