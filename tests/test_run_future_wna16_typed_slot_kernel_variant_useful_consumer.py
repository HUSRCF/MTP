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
        / "run_future_wna16_typed_slot_kernel_variant_useful_consumer.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_useful_consumer",
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


def _stub_payload(row_count: int = 5345) -> dict:
    payload = {
        "passed": True,
        "failures": [],
        "compiled_macros": {
            "MTP_PREMAP_TYPED_CONSUMER_CHECK_WNA16_SIDE_CONSUMER_VARIANT_EXECUTION_ABI": True
        },
        "wna16_side_consumer_variant_execution_checked": True,
        "wna16_side_consumer_variant_execution_mode": "readonly_wna16_side_consumer_variant_execution",
        "wna16_side_consumer_variant_execution_source": "premap_future_wna16_typed_slot_kernel_variant_v1",
        "wna16_side_consumer_variant_execution_packet_chain_depth": 16,
        "wna16_side_consumer_variant_execution_payload_bytes": 0,
        "wna16_side_consumer_variant_execution_payload_deref_allowed": False,
        "wna16_side_consumer_variant_execution_kernel_arg_pass_allowed": False,
        "wna16_side_consumer_variant_execution_passed_to_kernel": False,
        "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
        "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
        "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
        "wna16_side_consumer_variant_execution_explicit_typed_abi_slot": True,
        "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
        "wna16_side_consumer_variant_execution_error_count": 0,
        "wna16_side_consumer_variant_execution_row_offset": 0,
        "wna16_side_consumer_variant_execution_row_limit": row_count,
        "wna16_side_consumer_variant_execution_row_count": row_count,
        "wna16_side_consumer_variant_execution_row_ok_count": row_count,
        "wna16_side_consumer_variant_execution_hash_accumulator": "d4518e462be9e965",
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": "6e190b4f34afab7e",
    }
    for index, field in enumerate(HANDLE_FIELDS, start=1):
        prefix = f"wna16_side_consumer_variant_execution_{field}_read"
        payload[f"{prefix}_row_count"] = row_count
        payload[f"{prefix}_row_ok_count"] = row_count
        payload[f"{prefix}_error_count"] = 0
        payload[f"{prefix}_hash_accumulator"] = f"{index:016x}"
    return payload


def _timing_payload(
    stub_path: Path,
    *,
    stub_sha: str,
    row_count: int = 5345,
) -> dict:
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "passed": True,
        "failures": [],
        "timing_stub_ready": True,
        "native_stub_requested": True,
        "native_stub_executed": True,
        "native_stub_passed": True,
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
        "source_count": 128,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": {field: row_count for field in HANDLE_FIELDS},
        "field_read_hashes": {
            field: f"{index + 16:016x}"
            for index, field in enumerate(HANDLE_FIELDS)
        },
        "native_stub_output_json": str(stub_path),
        "native_stub_output_sha256": stub_sha,
    }


def _execution_payload(
    timing_path: Path,
    timing_sha: str,
    row_count: int = 5345,
) -> dict:
    field_hashes = {
        field: f"{index + 16:016x}" for index, field in enumerate(HANDLE_FIELDS)
    }
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_execution",
        "execution_name": "premap_future_wna16_typed_slot_kernel_variant_execution_v1",
        "execution_mode": "independent_future_wna16_typed_slot_kernel_variant_execution",
        "execution_source": "premap_future_wna16_typed_slot_payloadless_execution_v1",
        "passed": True,
        "failures": [],
        "payloadless_gate_ready": True,
        "future_wna16_variant_execution_ready": True,
        "future_wna16_variant_execution_native_requested": True,
        "future_wna16_variant_execution_native_executed": True,
        "future_wna16_variant_execution_native_passed": True,
        "future_wna16_variant_execution_native_artifact_ready": True,
        "future_wna16_variant_execution_not_current_wna16_kernel": True,
        "future_wna16_variant_execution_native_json": str(timing_path),
        "future_wna16_variant_execution_native_sha256": timing_sha,
        "benchmark_is_current_wna16_fused_moe": False,
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
        "source_count": 128,
        "row_count": row_count,
        "row_ok_count": row_count,
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": {field: row_count for field in HANDLE_FIELDS},
        "field_read_hashes": field_hashes,
        "row_hash_accumulator": "89665df973602a9f",
        "handle_projection_hash_accumulator": "6e190b4f34afab7e",
    }


def _materialize_inputs(tmp_path: Path, *, row_count: int = 5345) -> Path:
    module = _load_module()
    stub = tmp_path / "stub.json"
    timing = tmp_path / "timing.json"
    execution = tmp_path / "execution.json"
    _write_json(stub, _stub_payload(row_count=row_count))
    _write_json(
        timing,
        _timing_payload(
            stub,
            stub_sha=module._sha256(stub),  # noqa: SLF001
            row_count=row_count,
        ),
    )
    _write_json(
        execution,
        _execution_payload(
            timing,
            module._sha256(timing),  # noqa: SLF001
            row_count=row_count,
        ),
    )
    return execution


def test_future_wna16_useful_consumer_accepts_native_stub(tmp_path: Path):
    module = _load_module()
    execution = _materialize_inputs(tmp_path)
    output = tmp_path / "useful.json"

    args = module.build_parser().parse_args(
        ["--execution-json", str(execution), "--output-json", str(output)]
    )
    result = module.run_useful_consumer(args)

    assert result["passed"] is True
    assert result["useful_consumer_ready"] is True
    assert result["useful_consumer_rows_consumed"] == 5345
    assert result["useful_consumer_fields_consumed"] == HANDLE_FIELDS
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["next_runtime_stage"] == (
        "implement_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution"
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_future_wna16_useful_consumer_rejects_current_wna16_arg_path(
    tmp_path: Path,
):
    module = _load_module()
    execution = _materialize_inputs(tmp_path)
    payload = json.loads(execution.read_text(encoding="utf-8"))
    payload["passes_current_wna16_args"] = True
    _write_json(execution, payload)

    args = module.build_parser().parse_args(
        [
            "--execution-json",
            str(execution),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_useful_consumer(args)

    assert result["passed"] is False
    assert "execution_passes_current_wna16_args_mismatch" in result["failures"]
    assert result["passes_current_wna16_args"] is False


def test_future_wna16_useful_consumer_rejects_incomplete_field_rows(
    tmp_path: Path,
):
    module = _load_module()
    execution = _materialize_inputs(tmp_path)
    timing_path = Path(
        json.loads(execution.read_text(encoding="utf-8"))[
            "future_wna16_variant_execution_native_json"
        ]
    )
    stub_path = Path(
        json.loads(timing_path.read_text(encoding="utf-8"))[
            "native_stub_output_json"
        ]
    )
    stub = json.loads(stub_path.read_text(encoding="utf-8"))
    stub[
        "wna16_side_consumer_variant_execution_"
        "scale_metadata_handle_read_row_ok_count"
    ] -= 1
    _write_json(stub_path, stub)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["native_stub_output_sha256"] = module._sha256(stub_path)  # noqa: SLF001
    _write_json(timing_path, timing)

    args = module.build_parser().parse_args(
        [
            "--execution-json",
            str(execution),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_useful_consumer(args)

    assert result["passed"] is False
    assert "stub_scale_metadata_handle_row_ok_count_mismatch" in result["failures"]


def test_future_wna16_useful_consumer_rejects_stub_self_failure(
    tmp_path: Path,
):
    module = _load_module()
    execution = _materialize_inputs(tmp_path)
    timing_path = Path(
        json.loads(execution.read_text(encoding="utf-8"))[
            "future_wna16_variant_execution_native_json"
        ]
    )
    stub_path = Path(
        json.loads(timing_path.read_text(encoding="utf-8"))[
            "native_stub_output_json"
        ]
    )
    stub = json.loads(stub_path.read_text(encoding="utf-8"))
    stub["passed"] = False
    stub["failures"] = ["synthetic"]
    _write_json(stub_path, stub)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["native_stub_output_sha256"] = module._sha256(stub_path)  # noqa: SLF001
    _write_json(timing_path, timing)

    args = module.build_parser().parse_args(
        [
            "--execution-json",
            str(execution),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_useful_consumer(args)

    assert result["passed"] is False
    assert "stub_passed_mismatch" in result["failures"]
    assert "stub_failures_not_empty" in result["failures"]


def test_future_wna16_useful_consumer_rejects_stub_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    execution = _materialize_inputs(tmp_path)
    timing_path = Path(
        json.loads(execution.read_text(encoding="utf-8"))[
            "future_wna16_variant_execution_native_json"
        ]
    )
    stub_path = Path(
        json.loads(timing_path.read_text(encoding="utf-8"))[
            "native_stub_output_json"
        ]
    )
    stub = json.loads(stub_path.read_text(encoding="utf-8"))
    stub["wna16_side_consumer_variant_execution_hash_accumulator"] = (
        "1111111111111111"
    )
    _write_json(stub_path, stub)

    args = module.build_parser().parse_args(
        [
            "--execution-json",
            str(execution),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_useful_consumer(args)

    assert result["passed"] is False
    assert "timing_native_stub_output_sha256_mismatch" in result["failures"]
