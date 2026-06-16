from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HANDLE_FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_kernel_timing_stub.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_timing_stub",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _entrypoint_payload(*, row_count: int = 257, source_count: int = 128) -> dict:
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_entrypoint",
        "entrypoint_name": "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1",
        "entrypoint_mode": "readonly_independent_typed_slot_kernel_variant_entrypoint",
        "entrypoint_source": "premap_wna16_typed_slot_benchmark_harness_v1",
        "passed": True,
        "typed_slot_entrypoint_ready": True,
        "entrypoint_accepts_typed_slot": True,
        "entrypoint_consumes_handle_fields": True,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "measures_latency": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": "implement_future_wna16_typed_slot_kernel_timing_stub",
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": {field: row_count for field in HANDLE_FIELDS},
        "field_read_hashes": {
            "descriptor_ptr": "3132333435363738",
            "packed_weight_descriptor": "4142434445464748",
            "scale_metadata_handle": "5152535455565758",
            "aux_metadata_handle": "6162636465666768",
        },
        "row_hash_accumulator": "1112131415161718",
        "handle_projection_hash_accumulator": "2122232425262728",
    }


def _canary_report(*, row_count: int = 257, source_count: int = 128) -> dict:
    return {
        "passed": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_wna16_side_consumer_variant_execution": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "selected_source_count": source_count,
        "merged_row_count": row_count,
        "dispatch_active_rows": row_count,
        "future_wna16_kernel_side_consumer_execution_row_count": row_count,
        "future_wna16_kernel_side_consumer_execution_row_ok_count": row_count,
        "future_wna16_kernel_side_consumer_execution_payload_bytes": 0,
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed": False,
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed": False,
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel": False,
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args": False,
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible": False,
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation": False,
        "future_wna16_kernel_side_consumer_execution_reuses_current_wna16_arg_slot": False,
        "wna16_side_consumer_variant_execution_row_count": row_count,
        "wna16_side_consumer_variant_execution_row_ok_count": row_count,
        "wna16_side_consumer_variant_execution_payload_bytes": 0,
        "wna16_side_consumer_variant_execution_passed_to_kernel": False,
        "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
        "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
        "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
        "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
    }


def test_future_wna16_typed_slot_timing_stub_accepts_entrypoint(tmp_path: Path):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    output = tmp_path / "timing.json"
    _write_json(entrypoint, _entrypoint_payload())

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is True
    assert result["timing_stub_ready"] is True
    assert result["native_stub_requested"] is False
    assert result["native_stub_executed"] is False
    assert result["measures_native_stub_host_wall_time"] is False
    assert result["measures_tpot"] is False
    assert result["wna16_benchmark_ready"] is False
    assert result["uses_current_wna16_args"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_future_wna16_typed_slot_timing_stub_rejects_entrypoint_not_ready(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["typed_slot_entrypoint_ready"] = False
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("typed_slot_entrypoint_ready" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_rejects_current_arg_pass(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["passes_current_wna16_args"] = True
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("passes_current_wna16_args" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_runs_fake_native_canary(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    _write_json(entrypoint, _entrypoint_payload())
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})

    def fake_run_canary(args):
        assert str(args.runner_json) == str(runner)
        assert args.require_future_wna16_kernel_side_consumer_execution is True
        assert args.require_wna16_side_consumer_variant_execution is True
        return _canary_report()

    monkeypatch.setattr(module.canary_runner, "run_canary", fake_run_canary)
    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--runner-json",
            str(runner),
            "--run-native-stub",
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is True
    assert result["native_stub_requested"] is True
    assert result["native_stub_executed"] is True
    assert result["native_stub_passed"] is True
    assert result["native_stub_host_wall_ms"] is not None
    assert result["measures_native_stub_host_wall_time"] is True
    assert result["measures_tpot"] is False


def test_future_wna16_typed_slot_timing_stub_rejects_native_canary_arg_pass(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    _write_json(entrypoint, _entrypoint_payload())
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})

    def fake_run_canary(args):
        report = _canary_report()
        report[
            "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"
        ] = True
        return report

    monkeypatch.setattr(module.canary_runner, "run_canary", fake_run_canary)
    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--runner-json",
            str(runner),
            "--run-native-stub",
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("kernel_arg_pass_allowed" in item for item in result["failures"])
