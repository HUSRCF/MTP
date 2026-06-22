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
        / "run_future_wna16_typed_slot_payloadless_useful_runtime_ablation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_runtime_ablation",
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


def _native_stub_payload(module, *, row_count: int) -> dict:
    payload = dict(module.EXPECTED_STUB_FLAGS)
    payload.update(
        {
            "wna16_side_consumer_variant_execution_row_count": row_count,
            "wna16_side_consumer_variant_execution_row_ok_count": row_count,
        }
    )
    for idx, field in enumerate(module.FIELDS, start=1):
        prefix = f"wna16_side_consumer_variant_execution_{field}_read"
        payload[f"{prefix}_row_count"] = row_count
        payload[f"{prefix}_row_ok_count"] = row_count
        payload[f"{prefix}_error_count"] = 0
        payload[f"{prefix}_hash_accumulator"] = f"{idx:016x}"
    return payload


def _timing_payload(
    module,
    *,
    row_count: int,
    wall_ms: float,
    stub_path: Path,
) -> dict:
    payload = {
        **module.EXPECTED_TIMING_FLAGS,
        **module.EXPECTED_NOOP_FLAGS,
        "source_count": 128,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(module.FIELDS),
        "field_read_hashes": dict(U64_HASHES),
        "native_stub_host_wall_ms": wall_ms,
        "native_stub_output_json": str(stub_path),
        "native_stub_output_sha256": module._sha256(stub_path),  # noqa: SLF001
    }
    return payload


def _repeat_payload(
    module,
    *,
    tmp_path: Path,
    values: list[float] | None = None,
    row_count: int = 513,
) -> tuple[Path, dict]:
    values = values or [10.0, 10.2, 10.1]
    harness_path = tmp_path / "harness.json"
    timing_seed_path = tmp_path / "timing_seed.json"
    timing_seed_stub_path = tmp_path / "timing_seed_stub.json"
    _write_json(timing_seed_stub_path, _native_stub_payload(module, row_count=row_count))
    _write_json(
        timing_seed_path,
        _timing_payload(
            module,
            row_count=row_count,
            wall_ms=9.9,
            stub_path=timing_seed_stub_path,
        ),
    )
    _write_json(
        harness_path,
        {
            **module.EXPECTED_HARNESS_FLAGS,
            **module.EXPECTED_NOOP_FLAGS,
            "source_count": 128,
            "row_count": row_count,
            "row_ok_count": row_count,
            "rows_consumed": row_count,
            "field_count": len(module.FIELDS),
            "fields_per_row": len(module.FIELDS),
            "useful_work_units": row_count * len(module.FIELDS),
            "expected_useful_work_units": row_count * len(module.FIELDS),
            "useful_work_coverage": 1.0,
            "useful_work_kind": module.USEFUL_WORK_KIND,
            "native_consumer_has_useful_work": True,
            "field_names": list(module.FIELDS),
            "field_read_hashes": dict(U64_HASHES),
            "native_stub_host_wall_ms": 9.9,
        },
    )
    repeat_jsons: list[str] = []
    repeat_sha256s: list[str] = []
    for idx, value in enumerate(values):
        child_path = tmp_path / f"repeat_{idx:03d}.json"
        stub_path = tmp_path / f"repeat_stub_{idx:03d}.json"
        _write_json(stub_path, _native_stub_payload(module, row_count=row_count))
        _write_json(
            child_path,
            _timing_payload(
                module,
                row_count=row_count,
                wall_ms=value,
                stub_path=stub_path,
            ),
        )
        repeat_jsons.append(str(child_path))
        repeat_sha256s.append(module._sha256(child_path))  # noqa: SLF001
    payload = dict(module.EXPECTED_REPEAT_FLAGS)
    payload.update(
        {
            "harness_json": str(harness_path),
            "harness_sha256": module._sha256(harness_path),  # noqa: SLF001
            "native_timing_seed_json": str(timing_seed_path),
            "native_timing_seed_sha256": module._sha256(timing_seed_path),  # noqa: SLF001
            "source_count": 128,
            "row_count": row_count,
            "row_ok_count": row_count,
            "rows_consumed": row_count,
            "field_count": len(module.FIELDS),
            "fields_per_row": len(module.FIELDS),
            "useful_work_units": row_count * len(module.FIELDS),
            "expected_useful_work_units": row_count * len(module.FIELDS),
            "useful_work_coverage": 1.0,
            "useful_work_kind": module.USEFUL_WORK_KIND,
            "native_consumer_has_useful_work": True,
            "field_names": list(module.FIELDS),
            "field_read_hashes": dict(U64_HASHES),
            "repeat_count_requested": len(values),
            "repeat_count_measured": len(values),
            "repeat_output_jsons": repeat_jsons,
            "repeat_output_sha256s": repeat_sha256s,
            "native_stub_host_wall_ms_values": values,
            "native_stub_host_wall_ms_stats": {
                "count": len(values),
                "min_ms": min(values),
                "median_ms": sorted(values)[len(values) // 2],
                "mean_ms": sum(values) / len(values),
                "max_ms": max(values),
            },
        }
    )
    repeat_path = tmp_path / "repeat.json"
    _write_json(repeat_path, payload)
    return repeat_path, payload


def _run(module, repeat_path: Path, output_path: Path, *extra: str) -> dict:
    args = module.build_parser().parse_args(
        [
            "--repeat-benchmark-json",
            str(repeat_path),
            "--output-json",
            str(output_path),
            *extra,
        ]
    )
    return module.run_payloadless_useful_runtime_ablation(args)


def test_payloadless_useful_runtime_ablation_accepts_repeat3(tmp_path: Path):
    module = _load_module()
    repeat_path, _ = _repeat_payload(module, tmp_path=tmp_path)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["runtime_ablation_ready"] is True
    assert result["payloadless_useful_runtime_ablation_ready"] is True
    assert result["field_count"] == 4
    assert result["fields_per_row"] == 4
    assert result["useful_work_units"] == 513 * 4
    assert result["expected_useful_work_units"] == 513 * 4
    assert result["useful_work_coverage"] == 1.0
    assert result["useful_work_kind"] == module.USEFUL_WORK_KIND
    assert result["native_consumer_has_useful_work"] is True
    assert result["repeat_count_measured"] == 3
    assert result["native_stub_host_wall_ms_stats"]["relative_range"] < 0.05
    assert result["next_runtime_stage"] == (
        "implement_future_wna16_typed_slot_payloadless_useful_production_like_timing"
    )
    assert result["measures_tpot"] is False
    assert result["measures_vllm_latency"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_payloadless_useful_runtime_ablation_rejects_seed_only(tmp_path: Path):
    module = _load_module()
    repeat_path, payload = _repeat_payload(module, tmp_path=tmp_path)
    payload["seed_only"] = True
    _write_json(repeat_path, payload)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "repeat_benchmark_seed_only_mismatch" in result["failures"]


def test_payloadless_useful_runtime_ablation_rejects_incomplete_useful_work(
    tmp_path: Path,
):
    module = _load_module()
    repeat_path, payload = _repeat_payload(module, tmp_path=tmp_path)
    payload["fields_per_row"] = 3
    payload["useful_work_units"] = 513 * 3
    payload["useful_work_coverage"] = 0.75
    payload["native_consumer_has_useful_work"] = False
    _write_json(repeat_path, payload)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "fields_per_row_mismatch" in result["failures"]
    assert "useful_work_units_mismatch" in result["failures"]
    assert "useful_work_coverage_mismatch" in result["failures"]
    assert "native_consumer_has_useful_work_mismatch" in result["failures"]


def test_payloadless_useful_runtime_ablation_rejects_incomplete_harness_useful_work(
    tmp_path: Path,
):
    module = _load_module()
    repeat_path, payload = _repeat_payload(module, tmp_path=tmp_path)
    harness_path = Path(payload["harness_json"])
    harness = json.loads(harness_path.read_text(encoding="utf-8"))
    harness["fields_per_row"] = 3
    harness["useful_work_units"] = 513 * 3
    harness["useful_work_coverage"] = 0.75
    harness["native_consumer_has_useful_work"] = False
    _write_json(harness_path, harness)
    payload["harness_sha256"] = module._sha256(harness_path)  # noqa: SLF001
    _write_json(repeat_path, payload)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "harness_fields_per_row_mismatch" in result["failures"]
    assert "harness_useful_work_units_mismatch" in result["failures"]
    assert "harness_useful_work_coverage_mismatch" in result["failures"]
    assert (
        "harness_native_consumer_has_useful_work_mismatch" in result["failures"]
    )


def test_payloadless_useful_runtime_ablation_rejects_unstable_repeat(tmp_path: Path):
    module = _load_module()
    repeat_path, _ = _repeat_payload(module, tmp_path=tmp_path, values=[10.0, 13.0, 20.0])

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "native_stub_host_wall_relative_range_too_high" in result["failures"]
    assert "native_stub_host_wall_cv_too_high" in result["failures"]


def test_payloadless_useful_runtime_ablation_rejects_child_kernel_arg_use(
    tmp_path: Path,
):
    module = _load_module()
    repeat_path, payload = _repeat_payload(module, tmp_path=tmp_path)
    child_path = Path(payload["repeat_output_jsons"][0])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["kernel_arg_pass_allowed"] = True
    _write_json(child_path, child)
    payload["repeat_output_sha256s"][0] = module._sha256(child_path)  # noqa: SLF001
    _write_json(repeat_path, payload)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "repeat_0_kernel_arg_pass_allowed_mismatch" in result["failures"]


def test_payloadless_useful_runtime_ablation_rejects_child_wall_time_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    repeat_path, payload = _repeat_payload(module, tmp_path=tmp_path)
    child_path = Path(payload["repeat_output_jsons"][0])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["native_stub_host_wall_ms"] = 99.0
    _write_json(child_path, child)
    payload["repeat_output_sha256s"][0] = module._sha256(child_path)  # noqa: SLF001
    _write_json(repeat_path, payload)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "repeat_0_native_stub_host_wall_ms_mismatch" in result["failures"]


def test_payloadless_useful_runtime_ablation_rejects_child_native_stub_payload(
    tmp_path: Path,
):
    module = _load_module()
    repeat_path, payload = _repeat_payload(module, tmp_path=tmp_path)
    child_path = Path(payload["repeat_output_jsons"][0])
    child = json.loads(child_path.read_text(encoding="utf-8"))
    stub_path = Path(child["native_stub_output_json"])
    stub = json.loads(stub_path.read_text(encoding="utf-8"))
    stub["wna16_side_consumer_variant_execution_payload_bytes"] = 8
    _write_json(stub_path, stub)
    child["native_stub_output_sha256"] = module._sha256(stub_path)  # noqa: SLF001
    _write_json(child_path, child)
    payload["repeat_output_sha256s"][0] = module._sha256(child_path)  # noqa: SLF001
    _write_json(repeat_path, payload)

    result = _run(module, repeat_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert (
        "repeat_0_native_stub_wna16_side_consumer_variant_execution_payload_bytes_mismatch"
        in result["failures"]
    )
