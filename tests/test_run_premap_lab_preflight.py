from __future__ import annotations

import json
from pathlib import Path

from scripts.run_premap_lab_preflight import main, run_premap_lab_preflight


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_gate(root: Path, name: str, evidence_json: str) -> str:
    evidence_path = f"reports/{evidence_json}"
    _write(root / evidence_path, '{"passed": true}\n')
    gate_path = f"configs/runtime/{name}.yaml"
    _write(
        root / gate_path,
        "schema_version: 1\n"
        "evidence_paths:\n"
        f"  gate_json: {evidence_path}\n",
    )
    return gate_path


def _write_trace_config(
    root: Path,
    name: str,
    *,
    readonly_gate_path: str,
    live_enabled: bool = False,
    kernel_arg_pass_enabled: bool = False,
) -> str:
    config_path = f"configs/trace/{name}.yaml"
    _write(
        root / config_path,
        "trace:\n"
        "  runtime_shadow:\n"
        "    premap_consumer_require_readonly_gate: true\n"
        f"    premap_consumer_readonly_gate_path: {readonly_gate_path}\n"
        f"    premap_kernel_arg_handoff_live_enabled: {str(live_enabled).lower()}\n"
        f"    premap_kernel_arg_handoff_kernel_arg_pass_enabled: {str(kernel_arg_pass_enabled).lower()}\n",
    )
    return config_path


def test_premap_lab_preflight_accepts_default_readonly_wiring(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["runtime_gate_evidence_scan"]["gate_count"] == 2
    assert result["runtime_gate_evidence_scan"]["evidence_path_count"] == 2
    assert result["trace_config_checks"][0]["passed"] is True
    assert result["trace_config_checks"][0]["readonly_gate_path_label"] == default_gate


def test_premap_lab_preflight_accepts_absolute_readonly_gate_path(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    absolute_default_gate = str((tmp_path / default_gate).resolve())
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=absolute_default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is True
    assert result["trace_config_checks"][0]["readonly_gate_path"] == absolute_default_gate
    assert result["trace_config_checks"][0]["readonly_gate_path_label"] == default_gate


def test_premap_lab_preflight_rejects_kernel_arg_pass_in_default_config(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
        kernel_arg_pass_enabled=True,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["trace_config_checks"][0]["failures"] == ["kernel_arg_pass_enabled"]


def test_premap_lab_preflight_rejects_canary_gate_equal_to_default_gate(
    tmp_path: Path,
):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=[trace_config],
        default_readonly_gate=default_gate,
        canary_gate=default_gate,
    )

    assert result["passed"] is False
    assert result["gate_pair_failures"] == [
        "default_readonly_gate_equals_canary_gate"
    ]
    assert "default_readonly_gate_equals_canary_gate" in result["failures"]


def test_premap_lab_preflight_reports_missing_trace_config(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")

    result = run_premap_lab_preflight(
        root=tmp_path,
        runtime_pattern="configs/runtime/*.yaml",
        trace_configs=["configs/trace/missing.yaml"],
        default_readonly_gate=default_gate,
        canary_gate=canary_gate,
    )

    assert result["passed"] is False
    assert result["trace_config_checks"][0]["config_path"] == "configs/trace/missing.yaml"
    assert result["trace_config_checks"][0]["failures"][0].startswith(
        "FileNotFoundError:"
    )


def test_premap_lab_preflight_cli_writes_summary(tmp_path: Path):
    default_gate = _write_gate(tmp_path, "default_gate", "default_gate.json")
    canary_gate = _write_gate(tmp_path, "canary_gate", "canary_gate.json")
    trace_config = _write_trace_config(
        tmp_path,
        "longrun",
        readonly_gate_path=default_gate,
    )
    output = tmp_path / "preflight.json"

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--runtime-pattern",
            "configs/runtime/*.yaml",
            "--trace-config",
            trace_config,
            "--default-readonly-gate",
            default_gate,
            "--canary-gate",
            canary_gate,
            "--output-json",
            str(output),
        ]
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result["passed"] is True
    assert result["runtime_gate_evidence_scan"]["passed"] is True
