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
HEX = "a" * 64


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_kernel_variant_execution.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_execution",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_payloadless_test_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "test_run_future_wna16_typed_slot_kernel_variant_payloadless_execution.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_run_future_wna16_typed_slot_kernel_variant_payloadless_execution",
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


def _payloadless_payload(tmp_path: Path, *, row_count: int = 513) -> dict:
    payloadless_tests = _load_payloadless_test_module()
    _, _, timing_stub, timing_payload = payloadless_tests._write_seed_artifacts(  # noqa: SLF001
        tmp_path
    )
    benchmark = tmp_path / "benchmark.json"
    benchmark_payload = payloadless_tests._benchmark_payload(  # noqa: SLF001
        timing_stub,
        row_count=row_count,
    )
    _write_json(benchmark, benchmark_payload)
    runner = Path(timing_payload["runner_json"])
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_payloadless_execution",
        "passed": True,
        "failures": [],
        "payloadless_execution_ready": True,
        "payloadless_execution_gate_ready": True,
        "payloadless_execution_native_requested": True,
        "payloadless_execution_native_executed": True,
        "payloadless_execution_native_passed": True,
        "payloadless_execution_native_artifact_ready": True,
        "payloadless_execution_lab_preflight_ready": True,
        "all_four_field_consumer_ready": True,
        "all_four_field_consumer_fields_read": True,
        "all_four_field_consumer_hashes_valid": True,
        "future_wna16_kernel_side_typed_consumer_path_ready": True,
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        "entry_args_ptr_required": True,
        "entry_args_ptr_sweep_device": 1,
        "entry_args_ptr_sweep_window_size": 512,
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
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
        "field_read_row_ok_counts": benchmark_payload["field_read_row_ok_counts"],
        "field_read_hashes": benchmark_payload["field_read_hashes"],
        "row_hash_accumulator": benchmark_payload["row_hash_accumulator"],
        "handle_projection_hash_accumulator": benchmark_payload[
            "handle_projection_hash_accumulator"
        ],
        "fourth_field_handoff_ready": benchmark_payload["fourth_field_handoff_ready"],
        "fourth_field_handoff_evidence_path": benchmark_payload[
            "fourth_field_handoff_evidence_path"
        ],
        "fourth_field_handoff_evidence_sha256": benchmark_payload[
            "fourth_field_handoff_evidence_sha256"
        ],
        "fourth_field_handoff_source_count": benchmark_payload[
            "fourth_field_handoff_source_count"
        ],
        "fourth_field_handoff_row_count": benchmark_payload[
            "fourth_field_handoff_row_count"
        ],
        "fourth_field_handoff_row_ok_count": benchmark_payload[
            "fourth_field_handoff_row_ok_count"
        ],
        "fourth_field_handoff_field_read_hash": benchmark_payload[
            "fourth_field_handoff_field_read_hash"
        ],
        "fourth_field_handoff_runner_hash": benchmark_payload[
            "fourth_field_handoff_runner_hash"
        ],
        "all_four_field_consumer_ready": benchmark_payload[
            "all_four_field_consumer_ready"
        ],
        "all_four_field_consumer_fields_read": benchmark_payload[
            "all_four_field_consumer_fields_read"
        ],
        "all_four_field_consumer_hashes_valid": benchmark_payload[
            "all_four_field_consumer_hashes_valid"
        ],
        "all_four_field_consumer_source_count": benchmark_payload[
            "all_four_field_consumer_source_count"
        ],
        "all_four_field_consumer_row_count": benchmark_payload[
            "all_four_field_consumer_row_count"
        ],
        "all_four_field_consumer_row_ok_count": benchmark_payload[
            "all_four_field_consumer_row_ok_count"
        ],
        "all_four_field_consumer_fourth_field_path_label": benchmark_payload[
            "all_four_field_consumer_fourth_field_path_label"
        ],
        "all_four_field_consumer_fourth_field_sha256": benchmark_payload[
            "all_four_field_consumer_fourth_field_sha256"
        ],
        "future_wna16_kernel_side_typed_consumer_path_ready": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_ready"
        ],
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_hashes_valid"
        ],
        "future_wna16_kernel_side_typed_consumer_path_evidence_path": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_evidence_path"
        ],
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_evidence_sha256"
        ],
        "future_wna16_kernel_side_typed_consumer_path_source_count": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_source_count"
        ],
        "future_wna16_kernel_side_typed_consumer_path_input_json_count": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_input_json_count"
        ],
        "future_wna16_kernel_side_typed_consumer_path_row_count": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_row_count"
        ],
        "future_wna16_kernel_side_typed_consumer_path_row_ok_count": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_row_ok_count"
        ],
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_all_four_sha256"
        ],
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": benchmark_payload[
            "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"
        ],
        "benchmark_json": str(benchmark),
        "benchmark_sha256": "unused",
        "payloadless_execution_timing_stub_json": str(timing_stub),
        "payloadless_execution_timing_stub_sha256": "unused",
        "payloadless_execution_runner_json": str(runner),
        "payloadless_execution_runner_sha256": "unused",
        "entry_args_ptr_required": benchmark_payload["entry_args_ptr_required"],
        "entry_args_ptr_sweep_json": benchmark_payload["entry_args_ptr_sweep_json"],
        "entry_args_ptr_sweep_sha256": benchmark_payload["entry_args_ptr_sweep_sha256"],
        "entry_args_ptr_sweep_check_json": benchmark_payload[
            "entry_args_ptr_sweep_check_json"
        ],
        "entry_args_ptr_sweep_check_sha256": benchmark_payload[
            "entry_args_ptr_sweep_check_sha256"
        ],
        "entry_args_ptr_sweep_row_count": row_count,
        "entry_args_ptr_sweep_check_row_count": row_count,
        "entry_args_ptr_sweep_device": benchmark_payload["entry_args_ptr_sweep_device"],
        "entry_args_ptr_sweep_window_size": benchmark_payload[
            "entry_args_ptr_sweep_window_size"
        ],
        "entry_args_ptr_sweep_mirror_fields": benchmark_payload[
            "entry_args_ptr_sweep_mirror_fields"
        ],
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": benchmark_payload[
            "entry_args_ptr_sweep_require_kernel_arg_packet_abi"
        ],
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": benchmark_payload[
            "entry_args_ptr_sweep_require_kernel_entry_args_abi"
        ],
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": benchmark_payload[
            "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi"
        ],
    }


def _materialize_payloadless(tmp_path: Path, payload: dict) -> Path:
    module = _load_module()
    for path_key, sha_key in (
        ("benchmark_json", "benchmark_sha256"),
        (
            "payloadless_execution_timing_stub_json",
            "payloadless_execution_timing_stub_sha256",
        ),
        ("payloadless_execution_runner_json", "payloadless_execution_runner_sha256"),
    ):
        payload[sha_key] = module._sha256(Path(payload[path_key]))  # noqa: SLF001
    path = tmp_path / "payloadless.json"
    _write_json(path, payload)
    return path


def test_future_wna16_variant_execution_accepts_payloadless_gate(tmp_path: Path):
    module = _load_module()
    payloadless = _materialize_payloadless(tmp_path, _payloadless_payload(tmp_path))
    output = tmp_path / "execution.json"

    args = module.build_parser().parse_args(
        ["--payloadless-json", str(payloadless), "--output-json", str(output)]
    )
    result = module.run_variant_execution(args)

    assert result["passed"] is True
    assert result["payloadless_gate_ready"] is True
    assert result["future_wna16_variant_execution_native_executed"] is False
    assert result["future_wna16_variant_execution_native_artifact_ready"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert (
        result["next_runtime_stage"]
        == "implement_future_wna16_typed_slot_kernel_variant_useful_consumer"
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_future_wna16_variant_execution_rejects_current_wna16_arg_path(
    tmp_path: Path,
):
    module = _load_module()
    payload = _payloadless_payload(tmp_path)
    payload["passes_current_wna16_args"] = True
    payloadless = _materialize_payloadless(tmp_path, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "execution.json"),
        ]
    )
    result = module.run_variant_execution(args)

    assert result["passed"] is False
    assert any("passes_current_wna16_args" in item for item in result["failures"])
    assert result["passes_current_wna16_args"] is False


def test_future_wna16_variant_execution_rejects_dummy_runner_child(
    tmp_path: Path,
):
    module = _load_module()
    payload = _payloadless_payload(tmp_path)
    _write_json(Path(payload["payloadless_execution_runner_json"]), {"ok": True})
    payloadless = _materialize_payloadless(tmp_path, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "execution.json"),
        ]
    )
    result = module.run_variant_execution(args)

    assert result["passed"] is False
    assert "payloadless_runner_input_jsons_missing" in result["failures"]
    assert "payloadless_timing_stub_runner_sha256_mismatch" in result["failures"]


def test_future_wna16_variant_execution_rejects_unsafe_timing_stub_child(
    tmp_path: Path,
):
    module = _load_module()
    payload = _payloadless_payload(tmp_path)
    timing_stub = Path(payload["payloadless_execution_timing_stub_json"])
    timing_payload = json.loads(timing_stub.read_text(encoding="utf-8"))
    timing_payload["payload_bytes"] = 8
    _write_json(timing_stub, timing_payload)
    payloadless = _materialize_payloadless(tmp_path, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "execution.json"),
        ]
    )
    result = module.run_variant_execution(args)

    assert result["passed"] is False
    assert any(
        "payloadless_timing_stub_execution_payload_bytes_mismatch" in item
        for item in result["failures"]
    )


def test_future_wna16_variant_execution_rejects_required_native_without_run(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = _materialize_payloadless(tmp_path, _payloadless_payload(tmp_path))

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "execution.json"),
            "--require-native-execution",
        ]
    )
    result = module.run_variant_execution(args)

    assert result["passed"] is False
    assert "future_variant_execution_required_but_not_executed" in result["failures"]
