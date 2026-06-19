from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import yaml


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_future_wna16_typed_slot_payloadless_useful_candidate_config.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_future_wna16_typed_slot_payloadless_useful_candidate_config",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")


def _readonly_gate(*, passed: bool = True, passed_to_kernel: bool = False) -> dict:
    return {
        "schema_version": 1,
        "artifact_id": "tmp_readonly_gate",
        "status": "passed" if passed else "failed",
        "contract": {
            "payload_bytes_required": 0,
            "kernel_arg_handoff_live_noop_integration_passed_to_kernel_required": False,
            "kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_required": passed_to_kernel,
            "kernel_arg_handoff_live_consumer_adapter_changes_kernel_launch_args_required": False,
        },
    }


def _candidate_config(
    module,
    gate_path: Path,
    *,
    split_id: str = "external_prompt_gate_dolly_32_gen64_payloadless_useful_candidate",
    sample_start: int = 0,
    sample_end: int = 31,
    output_dir: str = "data/traces/tmp_payloadless_useful_candidate",
    mutate_trace=None,
    mutate_shadow=None,
) -> dict:
    trace = copy.deepcopy(module.TRACE_EXPECTED)
    shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    shadow["premap_consumer_readonly_gate_path"] = str(gate_path)
    if mutate_trace is not None:
        mutate_trace(trace)
    if mutate_shadow is not None:
        mutate_shadow(shadow)
    return {
        "model": "configs/model/qwen3_6_35b_a3b_awq_4bit_prod_batch32_graph.yaml",
        "data": "configs/data/external_prompt_gate_dolly_128.yaml",
        "output_dir": output_dir,
        "trace": {
            **trace,
            "split_id": split_id,
            "expected_sample_start": sample_start,
            "expected_sample_end": sample_end,
            "start_sample": sample_start,
            "runtime_shadow": shadow,
        },
    }


def _run(
    module,
    trace_config: Path,
    output_json: Path,
    *,
    expected_split_id: str = "external_prompt_gate_dolly_32_gen64_payloadless_useful_candidate",
    expected_sample_start: int = 0,
    expected_sample_end: int = 31,
    output_dir_substring: str = "payloadless_useful_candidate",
) -> dict:
    args = SimpleNamespace(
        trace_config=str(trace_config),
        output_json=str(output_json),
        expected_model="configs/model/qwen3_6_35b_a3b_awq_4bit_prod_batch32_graph.yaml",
        expected_data="configs/data/external_prompt_gate_dolly_128.yaml",
        expected_split_id=expected_split_id,
        expected_sample_start=expected_sample_start,
        expected_sample_end=expected_sample_end,
        output_dir_substring=output_dir_substring,
        require_pass=False,
    )
    return module.check_candidate_config(args)


def test_candidate_config_gate_accepts_payloadless_live_config(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate())
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate.yaml"
    _write_yaml(trace_config, _candidate_config(module, gate))

    result = _run(module, trace_config, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["payloadless_useful_candidate_config_ready"] is True
    assert result["live_config_without_router_recorder"] is True
    assert result["runtime_shadow_enabled"] is False
    assert result["record_router_topk"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False


def test_candidate_config_gate_accepts_heldout_split_parameters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate())
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate_heldout.yaml"
    split_id = "external_prompt_gate_dolly_32_heldout32_gen64_payloadless_useful_candidate"
    _write_yaml(
        trace_config,
        _candidate_config(
            module,
            gate,
            split_id=split_id,
            sample_start=32,
            sample_end=63,
            output_dir="data/traces/tmp_heldout_payloadless_useful_candidate",
        ),
    )

    result = _run(
        module,
        trace_config,
        tmp_path / "out.json",
        expected_split_id=split_id,
        expected_sample_start=32,
        expected_sample_end=63,
        output_dir_substring="heldout_payloadless_useful_candidate",
    )

    assert result["passed"] is True
    assert result["split_id"] == split_id


def test_candidate_config_gate_rejects_runtime_shadow_enabled(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate())
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate.yaml"
    _write_yaml(
        trace_config,
        _candidate_config(
            module,
            gate,
            mutate_shadow=lambda shadow: shadow.__setitem__("enabled", True),
        ),
    )

    result = _run(module, trace_config, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_shadow_enabled_mismatch" in result["failures"]


def test_candidate_config_gate_rejects_heavy_router_recording(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate())
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate.yaml"
    _write_yaml(
        trace_config,
        _candidate_config(
            module,
            gate,
            mutate_trace=lambda trace: trace.__setitem__(
                "allow_premap_live_config_without_router_recorder", False
            ),
            mutate_shadow=lambda shadow: shadow.__setitem__("record_router_topk", True),
        ),
    )

    result = _run(module, trace_config, tmp_path / "out.json")

    assert result["passed"] is False
    assert "trace_allow_premap_live_config_without_router_recorder_mismatch" in result["failures"]
    assert "runtime_shadow_record_router_topk_mismatch" in result["failures"]


def test_candidate_config_gate_rejects_kernel_arg_pass(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate())
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate.yaml"
    _write_yaml(
        trace_config,
        _candidate_config(
            module,
            gate,
            mutate_shadow=lambda shadow: shadow.__setitem__(
                "premap_kernel_arg_handoff_kernel_arg_pass_enabled", True
            ),
        ),
    )

    result = _run(module, trace_config, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled_mismatch" in result["failures"]


def test_candidate_config_gate_rejects_readonly_gate_kernel_pass_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate(passed_to_kernel=True))
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate.yaml"
    _write_yaml(trace_config, _candidate_config(module, gate))

    result = _run(module, trace_config, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "readonly_gate_kernel_arg_handoff_live_consumer_adapter_passed_to_kernel_required_mismatch"
        in result["failures"]
    )


def test_candidate_config_gate_rejects_premap_consumer_rows(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    gate = tmp_path / "readonly_gate.yaml"
    _write_yaml(gate, _readonly_gate())
    expected_shadow = copy.deepcopy(module.SHADOW_EXPECTED)
    expected_shadow["premap_consumer_readonly_gate_path"] = str(gate)
    monkeypatch.setattr(module, "SHADOW_EXPECTED", expected_shadow)
    trace_config = tmp_path / "candidate.yaml"
    _write_yaml(
        trace_config,
        _candidate_config(
            module,
            gate,
            mutate_shadow=lambda shadow: shadow.__setitem__("emit_premap_consumer_mapping", True),
        ),
    )

    result = _run(module, trace_config, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_shadow_emit_premap_consumer_mapping_mismatch" in result["failures"]
