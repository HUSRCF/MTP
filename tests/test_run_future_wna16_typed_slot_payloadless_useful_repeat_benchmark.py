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
        / "run_future_wna16_typed_slot_payloadless_useful_repeat_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_repeat_benchmark",
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


def _harness_payload(
    module,
    *,
    timing_path: Path,
    stub_path: Path,
    row_count: int = 513,
    source_count: int = 128,
) -> dict:
    payload = dict(module.EXPECTED_HARNESS_FLAGS)
    payload.update(
        {
            "failures": [],
            "source_count": source_count,
            "row_count": row_count,
            "row_ok_count": row_count,
            "rows_consumed": row_count,
            "field_names": list(module.FIELDS),
            "field_read_hashes": dict(U64_HASHES),
            "native_stub_host_wall_ms": 12.5,
            "native_timing_json": str(timing_path),
            "native_timing_sha256": module._sha256(timing_path),  # noqa: SLF001
            "native_stub_json": str(stub_path),
            "native_stub_sha256": module._sha256(stub_path),  # noqa: SLF001
        }
    )
    return payload


def _timing_payload(
    module,
    *,
    stub_path: Path,
    row_count: int = 513,
    source_count: int = 128,
) -> dict:
    payload = dict(module.EXPECTED_TIMING_SEED_FLAGS)
    payload.update(
        {
            "failures": [],
            "entrypoint_json": str(stub_path.parent / "entrypoint.json"),
            "runner_json": str(stub_path.parent / "runner.json"),
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


def _materialize_inputs(tmp_path: Path, module) -> tuple[Path, Path]:
    timing_path = tmp_path / "timing.json"
    harness_path = tmp_path / "harness.json"
    stub_path = tmp_path / "stub.json"
    _write_json(stub_path, {"passed": True})
    _write_json(tmp_path / "entrypoint.json", {"ok": True})
    _write_json(tmp_path / "runner.json", {"ok": True})
    _write_json(
        timing_path,
        _timing_payload(module, stub_path=stub_path),
    )
    _write_json(
        harness_path,
        _harness_payload(module, timing_path=timing_path, stub_path=stub_path),
    )
    return harness_path, timing_path


def _run(module, harness_path: Path, output_path: Path, *extra: str) -> dict:
    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness_path),
            "--output-json",
            str(output_path),
            *extra,
        ]
    )
    return module.run_payloadless_useful_repeat_benchmark(args)


def test_payloadless_useful_repeat_benchmark_accepts_seed_only(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, _ = _materialize_inputs(tmp_path, module)

    result = _run(module, harness_path, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["payloadless_useful_repeat_benchmark_ready"] is True
    assert result["repeat_count_requested"] == 0
    assert result["repeat_count_measured"] == 1
    assert result["seed_only"] is True
    assert result["measurement_source"] == "validated_harness_seed_native_stub_host_wall"
    assert result["native_stub_host_wall_ms_values"] == [12.5]
    assert result["native_stub_host_wall_ms_stats"]["median_ms"] == 12.5
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


def test_payloadless_useful_repeat_benchmark_rejects_failed_harness(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, _ = _materialize_inputs(tmp_path, module)
    harness = json.loads(harness_path.read_text(encoding="utf-8"))
    harness["passed"] = False
    harness["payloadless_useful_benchmark_harness_ready"] = False
    harness["failures"] = ["forced"]
    _write_json(harness_path, harness)

    result = _run(module, harness_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "harness_passed_mismatch" in result["failures"]
    assert "harness_payloadless_useful_benchmark_harness_ready_mismatch" in result[
        "failures"
    ]
    assert "harness_failures_not_empty" in result["failures"]


def test_payloadless_useful_repeat_benchmark_rejects_timing_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, _ = _materialize_inputs(tmp_path, module)
    harness = json.loads(harness_path.read_text(encoding="utf-8"))
    harness["native_timing_sha256"] = "0" * 64
    _write_json(harness_path, harness)

    result = _run(module, harness_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_timing_seed_sha256_mismatch" in result["failures"]


def test_payloadless_useful_repeat_benchmark_rejects_dummy_timing_seed(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, timing_path = _materialize_inputs(tmp_path, module)
    _write_json(timing_path, {"entrypoint_json": "entrypoint.json"})
    harness = json.loads(harness_path.read_text(encoding="utf-8"))
    harness["native_timing_sha256"] = module._sha256(timing_path)  # noqa: SLF001
    _write_json(harness_path, harness)

    result = _run(module, harness_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "timing_seed_passed_mismatch" in result["failures"]
    assert "timing_seed_native_stub_host_wall_ms_invalid" in result["failures"]
    assert "timing_seed_native_stub_output_json_missing" in result["failures"]


def test_payloadless_useful_repeat_benchmark_rejects_seed_host_wall_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, timing_path = _materialize_inputs(tmp_path, module)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["native_stub_host_wall_ms"] = 99.0
    _write_json(timing_path, timing)
    harness = json.loads(harness_path.read_text(encoding="utf-8"))
    harness["native_timing_sha256"] = module._sha256(timing_path)  # noqa: SLF001
    _write_json(harness_path, harness)

    result = _run(module, harness_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "timing_seed_native_stub_host_wall_ms_mismatch" in result["failures"]


def test_payloadless_useful_repeat_benchmark_rejects_missing_timing_path(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, _ = _materialize_inputs(tmp_path, module)
    harness = json.loads(harness_path.read_text(encoding="utf-8"))
    harness.pop("native_timing_json")
    _write_json(harness_path, harness)

    result = _run(module, harness_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_timing_seed_missing" in result["failures"]


def test_payloadless_useful_repeat_benchmark_rejects_negative_repeat(
    tmp_path: Path,
):
    module = _load_module()
    harness_path, _ = _materialize_inputs(tmp_path, module)

    result = _run(
        module,
        harness_path,
        tmp_path / "out.json",
        "--repeat-count",
        "-1",
    )

    assert result["passed"] is False
    assert "repeat_count_negative" in result["failures"]
