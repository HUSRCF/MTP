from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_gate_evidence_paths import check_gate_evidence_paths, main


def _write_gate(path: Path, evidence_paths: dict[str, str]) -> None:
    lines = ["schema_version: 1", "evidence_paths:"]
    for label, evidence_path in evidence_paths.items():
        lines.append(f"  {label}: {evidence_path}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_raw_gate(path: Path, body: str) -> None:
    path.write_text("schema_version: 1\nevidence_paths:\n" + body, encoding="utf-8")


def test_check_gate_evidence_paths_accepts_existing_json_and_text(tmp_path: Path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "gate.json").write_text('{"passed": true}\n')
    (tmp_path / "reports" / "summary.md").write_text("# Summary\n")
    gate = tmp_path / "gate.yaml"
    _write_gate(
        gate,
        {
            "gate_json": "reports/gate.json",
            "summary_md": "reports/summary.md",
        },
    )

    result = check_gate_evidence_paths(gate, root=tmp_path, require_json=True)

    assert result["passed"] is True
    assert result["missing_count"] == 0
    assert result["invalid_json_count"] == 0
    assert result["evidence_path_count"] == 2


def test_check_gate_evidence_paths_accepts_nested_directory_evidence(
    tmp_path: Path,
):
    trace_dir = tmp_path / "traces" / "run"
    trace_dir.mkdir(parents=True)
    (trace_dir / "manifest.jsonl").write_text("{}\n", encoding="utf-8")
    gate = tmp_path / "gate.yaml"
    _write_raw_gate(
        gate,
        "  heldout:\n"
        "    no_order: traces/run\n"
        "    report: traces/run/manifest.jsonl\n",
    )

    result = check_gate_evidence_paths(gate, root=tmp_path, require_json=True)

    rows = {row["label"]: row for row in result["rows"]}
    assert result["passed"] is True
    assert rows["heldout.no_order"]["type"] == "directory"
    assert rows["heldout.report"]["type"] == "file"


def test_check_gate_evidence_paths_rejects_missing_by_default(tmp_path: Path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, {"missing_json": "reports/missing.json"})

    result = check_gate_evidence_paths(gate, root=tmp_path)

    assert result["passed"] is False
    assert result["failures"] == ["missing_json:missing"]
    assert result["missing_count"] == 1


def test_check_gate_evidence_paths_can_allow_missing(tmp_path: Path):
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, {"missing_json": "reports/missing.json"})

    result = check_gate_evidence_paths(gate, root=tmp_path, allow_missing=True)

    assert result["passed"] is True
    assert result["missing_count"] == 1


def test_check_gate_evidence_paths_rejects_invalid_json_when_required(
    tmp_path: Path,
):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "bad.json").write_text("{bad\n")
    gate = tmp_path / "gate.yaml"
    _write_gate(gate, {"bad_json": "reports/bad.json"})

    result = check_gate_evidence_paths(gate, root=tmp_path, require_json=True)

    assert result["passed"] is False
    assert result["failures"] == ["bad_json:invalid_json"]
    assert result["invalid_json_count"] == 1


def test_check_gate_evidence_paths_requires_mapping(tmp_path: Path):
    gate = tmp_path / "gate.yaml"
    gate.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a mapping"):
        check_gate_evidence_paths(gate, root=tmp_path)


def test_check_gate_evidence_paths_can_allow_missing_section(tmp_path: Path):
    gate = tmp_path / "gate.yaml"
    gate.write_text("schema_version: 1\n", encoding="utf-8")

    result = check_gate_evidence_paths(
        gate,
        root=tmp_path,
        allow_missing_section=True,
    )

    assert result["passed"] is True
    assert result["evidence_paths_section_missing"] is True
    assert result["evidence_path_count"] == 0


def test_check_gate_evidence_paths_cli_allows_missing_by_default(
    tmp_path: Path,
):
    gate = tmp_path / "gate.yaml"
    output = tmp_path / "evidence_check.json"
    _write_gate(gate, {"missing_json": "reports/missing.json"})

    exit_code = main([str(gate), "--root", str(tmp_path), "--output-json", str(output)])

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["missing_count"] == 1


def test_check_gate_evidence_paths_cli_allows_missing_section_by_default(
    tmp_path: Path,
):
    gate = tmp_path / "gate.yaml"
    output = tmp_path / "evidence_check.json"
    gate.write_text("schema_version: 1\n", encoding="utf-8")

    exit_code = main([str(gate), "--root", str(tmp_path), "--output-json", str(output)])

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["evidence_paths_section_missing"] is True


def test_check_gate_evidence_paths_cli_can_require_evidence_section(
    tmp_path: Path,
):
    gate = tmp_path / "gate.yaml"
    gate.write_text("schema_version: 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="has no evidence_paths mapping"):
        main([str(gate), "--root", str(tmp_path), "--require-evidence-section"])


def test_check_gate_evidence_paths_cli_strict_rejects_missing(
    tmp_path: Path,
):
    gate = tmp_path / "gate.yaml"
    output = tmp_path / "evidence_check.json"
    _write_gate(gate, {"missing_json": "reports/missing.json"})

    exit_code = main(
        [str(gate), "--root", str(tmp_path), "--strict", "--output-json", str(output)]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert result["passed"] is False
    assert result["failures"] == ["missing_json:missing"]
