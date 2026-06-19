from __future__ import annotations

import importlib.util
import json
from pathlib import Path


U64_HASHES = {
    "descriptor_ptr": "1111111111111111",
    "packed_weight_descriptor": "2222222222222222",
    "scale_metadata_handle": "3333333333333333",
    "aux_metadata_handle": "4444444444444444",
}


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_payloadless_useful_benchmark_harness.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_benchmark_harness",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _timing_payload(
    module,
    *,
    stub_path: Path,
    row_count: int = 513,
    source_count: int = 128,
) -> dict:
    payload = dict(module.EXPECTED_TIMING_FLAGS)
    payload.update(
        {
            "failures": [],
            "source_count": source_count,
            "row_count": row_count,
            "row_ok_count": row_count,
            "field_names": list(module.FIELDS),
            "field_read_row_ok_counts": {
                field: row_count for field in module.FIELDS
            },
            "field_read_hashes": dict(U64_HASHES),
            "native_stub_host_wall_ms": 12.5,
            "native_stub_output_json": str(stub_path),
            "native_stub_output_sha256": module._sha256(stub_path),  # noqa: SLF001
        }
    )
    return payload


def _stub_payload(module) -> dict:
    payload = dict(module.EXPECTED_STUB_FLAGS)
    payload.update({"failures": []})
    return payload


def _runtime_payload(
    module,
    *,
    timing_path: Path,
    stub_path: Path,
    row_count: int = 513,
    source_count: int = 128,
) -> dict:
    payload = dict(module.EXPECTED_RUNTIME_GATE_FLAGS)
    payload.update(
        {
            "failures": [],
            "source_count": source_count,
            "row_count": row_count,
            "row_ok_count": row_count,
            "rows_consumed": row_count,
            "field_names": list(module.FIELDS),
            "field_read_hashes": dict(U64_HASHES),
            "native_timing_json": str(timing_path),
            "native_timing_sha256": module._sha256(timing_path),  # noqa: SLF001
            "native_stub_json": str(stub_path),
            "native_stub_sha256": module._sha256(stub_path),  # noqa: SLF001
        }
    )
    return payload


def _materialize_inputs(tmp_path: Path, module) -> tuple[Path, Path, Path]:
    timing_path = tmp_path / "timing.json"
    stub_path = tmp_path / "stub.json"
    runtime_path = tmp_path / "runtime.json"
    _write_json(stub_path, _stub_payload(module))
    _write_json(timing_path, _timing_payload(module, stub_path=stub_path))
    _write_json(
        runtime_path,
        _runtime_payload(module, timing_path=timing_path, stub_path=stub_path),
    )
    return runtime_path, timing_path, stub_path


def _run(module, runtime_path: Path, output_path: Path) -> dict:
    args = module.build_parser().parse_args(
        [
            "--runtime-gate-json",
            str(runtime_path),
            "--output-json",
            str(output_path),
        ]
    )
    return module.run_payloadless_useful_benchmark_harness(args)


def test_payloadless_useful_benchmark_harness_accepts_runtime_gate(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, _, _ = _materialize_inputs(tmp_path, module)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["payloadless_useful_benchmark_harness_ready"] is True
    assert result["benchmark_harness_ready"] is True
    assert result["native_stub_host_wall_ms"] == 12.5
    assert result["source_count"] == 128
    assert result["row_count"] == 513
    assert result["field_read_hashes"] == U64_HASHES
    assert result["measures_native_stub_host_wall_time"] is True
    assert result["benchmark_is_current_wna16_fused_moe"] is False
    assert result["measures_tpot"] is False
    assert result["measures_vllm_latency"] is False
    assert result["wna16_benchmark_ready"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["payload_deref_allowed"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_payloadless_useful_benchmark_harness_rejects_failed_runtime_gate(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, _, _ = _materialize_inputs(tmp_path, module)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["passed"] = False
    runtime["runtime_gate_ready"] = False
    runtime["failures"] = ["forced"]
    _write_json(runtime_path, runtime)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "runtime_gate_passed_mismatch" in result["failures"]
    assert "runtime_gate_runtime_gate_ready_mismatch" in result["failures"]
    assert "runtime_gate_failures_not_empty" in result["failures"]


def test_payloadless_useful_benchmark_harness_rejects_timing_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, _, _ = _materialize_inputs(tmp_path, module)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["native_timing_sha256"] = "0" * 64
    _write_json(runtime_path, runtime)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_timing_sha256_mismatch" in result["failures"]


def test_payloadless_useful_benchmark_harness_rejects_timing_stub_output_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, timing_path, _ = _materialize_inputs(tmp_path, module)
    other_stub = tmp_path / "other_stub.json"
    other_payload = _stub_payload(module)
    other_payload["marker"] = "different_safe_stub"
    _write_json(other_stub, other_payload)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["native_stub_output_json"] = str(other_stub)
    timing["native_stub_output_sha256"] = module._sha256(other_stub)  # noqa: SLF001
    _write_json(timing_path, timing)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["native_timing_sha256"] = module._sha256(timing_path)  # noqa: SLF001
    _write_json(runtime_path, runtime)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "timing_native_stub_output_json_mismatch" in result["failures"]
    assert "timing_native_stub_output_sha256_mismatch" in result["failures"]


def test_payloadless_useful_benchmark_harness_rejects_unsafe_timing(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, timing_path, _ = _materialize_inputs(tmp_path, module)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["uses_current_wna16_args"] = True
    timing["payload_bytes"] = 8
    _write_json(timing_path, timing)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["native_timing_sha256"] = module._sha256(timing_path)  # noqa: SLF001
    _write_json(runtime_path, runtime)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "timing_uses_current_wna16_args_mismatch" in result["failures"]
    assert "timing_payload_bytes_mismatch" in result["failures"]


def test_payloadless_useful_benchmark_harness_rejects_unsafe_stub(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, timing_path, stub_path = _materialize_inputs(tmp_path, module)
    stub = json.loads(stub_path.read_text(encoding="utf-8"))
    stub["payload_bytes"] = 8
    stub["wna16_side_consumer_variant_execution_passed_to_kernel"] = True
    _write_json(stub_path, stub)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["native_stub_output_sha256"] = module._sha256(stub_path)  # noqa: SLF001
    _write_json(timing_path, timing)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime["native_stub_sha256"] = module._sha256(stub_path)  # noqa: SLF001
    runtime["native_timing_sha256"] = module._sha256(timing_path)  # noqa: SLF001
    _write_json(runtime_path, runtime)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "stub_payload_bytes_mismatch" in result["failures"]
    assert (
        "stub_wna16_side_consumer_variant_execution_passed_to_kernel_mismatch"
        in result["failures"]
    )


def test_payloadless_useful_benchmark_harness_rejects_missing_native_paths(
    tmp_path: Path,
):
    module = _load_module()
    runtime_path, _, _ = _materialize_inputs(tmp_path, module)
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    runtime.pop("native_timing_json")
    runtime.pop("native_stub_json")
    _write_json(runtime_path, runtime)

    result = _run(module, runtime_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_timing_json_missing" in result["failures"]
    assert "native_stub_json_missing" in result["failures"]
