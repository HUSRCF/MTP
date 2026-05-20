import json

import pytest

from scripts.build_evidence_manifest import build_manifest, render_markdown


def test_build_manifest_hashes_files_and_directories(tmp_path):
    root = tmp_path
    config = root / "config.yaml"
    config.write_text("x: 1\n", encoding="utf-8")
    artifact = root / "artifact"
    artifact.mkdir()
    (artifact / "results.json").write_text('{"ok": true}\n', encoding="utf-8")
    (artifact / "summary.md").write_text("# Summary\n", encoding="utf-8")

    manifest = build_manifest(
        [
            ("config", "config.yaml"),
            ("artifact", "artifact"),
        ],
        root=root,
        title="Test Evidence",
        boundaries=["diagnostic-only"],
    )

    assert manifest["title"] == "Test Evidence"
    assert manifest["missing_count"] == 0
    assert manifest["boundaries"] == ["diagnostic-only"]
    by_label = {row["label"]: row for row in manifest["entries"]}
    assert by_label["config"]["type"] == "file"
    assert len(by_label["config"]["sha256"]) == 64
    assert by_label["artifact"]["type"] == "directory"
    assert by_label["artifact"]["file_count"] == 2
    assert len(by_label["artifact"]["sha256"]) == 64
    assert {row["relative_path"] for row in by_label["artifact"]["files"]} == {
        "results.json",
        "summary.md",
    }

    text = render_markdown(manifest)
    assert "# Test Evidence" in text
    assert "diagnostic-only" in text
    assert "`artifact`" in text


def test_build_manifest_rejects_missing_by_default(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_manifest(
            [("missing", "nope")],
            root=tmp_path,
            title="Missing Test",
        )


def test_build_manifest_can_allow_missing(tmp_path):
    manifest = build_manifest(
        [("missing", "nope")],
        root=tmp_path,
        title="Missing Test",
        allow_missing=True,
    )

    assert manifest["missing_count"] == 1
    assert manifest["entries"][0]["type"] == "missing"
    assert json.loads(json.dumps(manifest))["missing_count"] == 1


def test_build_manifest_can_exclude_output_paths_from_directory_digest(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "results.json").write_text('{"ok": true}\n', encoding="utf-8")
    output = artifact / "manifest.json"
    output.write_text('{"old": true}\n', encoding="utf-8")

    with_output = build_manifest(
        [("artifact", "artifact")],
        root=tmp_path,
        title="With Output",
    )
    without_output = build_manifest(
        [("artifact", "artifact")],
        root=tmp_path,
        title="Without Output",
        exclude_paths={output},
    )

    with_row = with_output["entries"][0]
    without_row = without_output["entries"][0]
    assert with_row["file_count"] == 2
    assert without_row["file_count"] == 1
    assert with_row["sha256"] != without_row["sha256"]
    assert {row["relative_path"] for row in without_row["files"]} == {"results.json"}
