from __future__ import annotations

import hashlib
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
        / "run_future_wna16_typed_slot_kernel_variant_payloadless_execution.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_execution",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _timing_stub_payload(
    *,
    row_count: int = 257,
    source_count: int = 128,
    host_wall_ms: float = 12.5,
) -> dict:
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "passed": True,
        "timing_stub_ready": True,
        "native_stub_requested": True,
        "native_stub_executed": True,
        "native_stub_passed": True,
        "measures_native_stub_host_wall_time": True,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "entrypoint_sha256": "a" * 64,
        "runner_sha256": "b" * 64,
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
        "native_stub_host_wall_ms": host_wall_ms,
    }


def _benchmark_payload(
    timing_stub_json: Path,
    *,
    row_count: int = 257,
    source_count: int = 128,
    repeat_count: int = 3,
) -> dict:
    values = [10.0, 11.0, 12.0][:repeat_count]
    timing_payload = json.loads(timing_stub_json.read_text(encoding="utf-8"))
    repeat_output_jsons: list[str] = []
    repeat_output_sha256s: list[str] = []
    repeat_dir = timing_stub_json.parent / "repeat_artifacts"
    for index, value in enumerate(values):
        repeat_payload = dict(timing_payload)
        repeat_payload["native_stub_host_wall_ms"] = value
        repeat_path = repeat_dir / f"timing_stub_repeat_{index:03d}.json"
        _write_json(repeat_path, repeat_payload)
        repeat_output_jsons.append(str(repeat_path))
        repeat_output_sha256s.append(_sha256(repeat_path))
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_benchmark",
        "benchmark_name": "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1",
        "benchmark_mode": "independent_future_wna16_typed_slot_native_stub_benchmark",
        "benchmark_source": "premap_future_wna16_typed_slot_kernel_timing_stub_v1",
        "benchmark_scope": "independent_native_typed_slot_stub_host_wall",
        "passed": True,
        "typed_slot_variant_benchmark_ready": True,
        "future_wna16_variant_benchmark_ready": True,
        "independent_kernel_variant_benchmark": True,
        "independent_kernel_variant_benchmark_scope_declared": True,
        "benchmark_is_current_wna16_fused_moe": False,
        "measures_native_stub_host_wall_time": True,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "next_runtime_stage": "implement_future_wna16_typed_slot_kernel_variant_payloadless_execution",
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
        "repeat_count_measured": repeat_count,
        "repeat_output_jsons": repeat_output_jsons,
        "repeat_output_sha256s": repeat_output_sha256s,
        "native_stub_host_wall_ms_values": values,
        "native_stub_host_wall_ms_stats": {
            "count": len(values),
            "min_ms": min(values),
            "median_ms": values[len(values) // 2],
            "mean_ms": sum(values) / len(values),
            "p90_ms": max(values),
            "max_ms": max(values),
        },
        "timing_stub_json": str(timing_stub_json),
        "timing_stub_sha256": _sha256(timing_stub_json),
    }


def _write_seed_artifacts(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    timing_payload = _timing_stub_payload()
    timing_payload["entrypoint_json"] = str(entrypoint)
    timing_payload["runner_json"] = str(runner)
    timing_payload["entrypoint_sha256"] = _sha256(entrypoint)
    timing_payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, timing_payload)
    return entrypoint, runner, timing_stub, timing_payload


def test_payloadless_execution_accepts_benchmark_without_native_run(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    output = tmp_path / "payloadless.json"
    _write_json(benchmark, _benchmark_payload(timing_stub))

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is True
    assert result["payloadless_execution_gate_ready"] is True
    assert result["payloadless_execution_native_executed"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_payloadless_execution_rejects_current_arg_benchmark(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["passes_current_wna16_args"] = True
    _write_json(benchmark, payload)

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert any("passes_current_wna16_args" in item for item in result["failures"])
    assert result["passes_current_wna16_args"] is True


def test_payloadless_execution_rejects_low_repeat_count(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    _write_json(benchmark, _benchmark_payload(timing_stub, repeat_count=1))

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert "benchmark_repeat_count_measured_invalid" in result["failures"]


def test_payloadless_execution_rejects_missing_repeat_artifacts(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload.pop("repeat_output_jsons")
    payload.pop("repeat_output_sha256s")
    _write_json(benchmark, payload)

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert "benchmark_repeat_output_jsons_count_mismatch" in result["failures"]
    assert "benchmark_repeat_output_sha256s_count_mismatch" in result["failures"]


def test_payloadless_execution_rejects_repeat_sha_mismatch(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["repeat_output_sha256s"][0] = "0" * 64
    _write_json(benchmark, payload)

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert "benchmark_repeat_0_sha256_mismatch" in result["failures"]


def test_payloadless_execution_writes_failure_for_repeat_directory(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    output = tmp_path / "payloadless.json"
    payload = _benchmark_payload(timing_stub)
    repeat_dir = tmp_path / "repeat_dir"
    repeat_dir.mkdir()
    payload["repeat_output_jsons"][0] = str(repeat_dir)
    payload["repeat_output_sha256s"][0] = "0" * 64
    _write_json(benchmark, payload)

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert any("benchmark_repeat_0_sha256_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_payloadless_execution_rejects_benchmark_seed_hash_drift(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["row_hash_accumulator"] = "8182838485868788"
    _write_json(benchmark, payload)

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert "benchmark_seed_row_hash_accumulator_mismatch" in result["failures"]


def test_payloadless_execution_runs_fake_native_execution(tmp_path: Path, monkeypatch):
    module = _load_module()
    _, _, timing_stub, timing_payload = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    _write_json(benchmark, _benchmark_payload(timing_stub))

    def fake_run_timing_stub(args):
        assert args.run_native_stub is True
        assert str(args.entrypoint_json) == str(tmp_path / "entrypoint.json")
        assert str(args.runner_json) == str(tmp_path / "runner.json")
        assert "execution" in str(args.output_json)
        report = dict(timing_payload)
        report["native_stub_host_wall_ms"] = 42.0
        _write_json(Path(args.output_json), report)
        return report

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
            "--execution-output-dir",
            str(tmp_path / "execution"),
            "--run-native-execution",
            "--require-native-execution",
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is True
    assert result["payloadless_execution_native_executed"] is True
    assert result["payloadless_execution_native_passed"] is True
    assert result["payloadless_execution_native_host_wall_ms"] == 42.0
    assert result["changes_kernel_launch_args"] is False


def test_payloadless_execution_rejects_native_contract_drift(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    _, _, timing_stub, timing_payload = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    _write_json(benchmark, _benchmark_payload(timing_stub))

    def fake_run_timing_stub(args):
        report = dict(timing_payload)
        report["row_hash_accumulator"] = "8182838485868788"
        _write_json(Path(args.output_json), report)
        return report

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(tmp_path / "payloadless.json"),
            "--run-native-execution",
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert "execution_row_hash_accumulator_mismatch" in result["failures"]


def test_payloadless_execution_catches_native_exception(tmp_path: Path, monkeypatch):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    _write_json(benchmark, _benchmark_payload(timing_stub))

    def fake_run_timing_stub(args):
        raise RuntimeError("boom")

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    output = tmp_path / "payloadless.json"
    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(output),
            "--run-native-execution",
            "--require-native-execution",
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert any("payloadless_execution_exception:RuntimeError:boom" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_payloadless_execution_writes_failure_for_bad_benchmark_json(
    tmp_path: Path,
):
    module = _load_module()
    benchmark = tmp_path / "benchmark.json"
    output = tmp_path / "payloadless.json"
    benchmark.write_text("{bad json\n", encoding="utf-8")

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert any("benchmark_json_load_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_payloadless_execution_writes_failure_for_benchmark_directory(
    tmp_path: Path,
):
    module = _load_module()
    benchmark_dir = tmp_path / "benchmark_dir"
    benchmark_dir.mkdir()
    output = tmp_path / "payloadless.json"

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark_dir),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert any("benchmark_json_load_failed" in item for item in result["failures"])
    assert any("benchmark_json_sha256_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_payloadless_execution_writes_failure_for_timing_stub_directory(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    timing_stub_dir = tmp_path / "timing_stub_dir"
    timing_stub_dir.mkdir()
    benchmark = tmp_path / "benchmark.json"
    output = tmp_path / "payloadless.json"
    payload = _benchmark_payload(timing_stub)
    payload["timing_stub_json"] = str(timing_stub_dir)
    payload["timing_stub_sha256"] = "0" * 64
    _write_json(benchmark, payload)

    args = module.build_parser().parse_args(
        [
            "--benchmark-json",
            str(benchmark),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_payloadless_execution(args)

    assert result["passed"] is False
    assert any("benchmark_timing_stub_sha256_failed" in item for item in result["failures"])
    assert any("benchmark_timing_stub_json_load_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False
