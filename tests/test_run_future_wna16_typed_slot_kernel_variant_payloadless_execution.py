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
    row_count: int = 513,
    source_count: int = 128,
    host_wall_ms: float = 12.5,
) -> dict:
    evidence_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_fourth_field_evidence.json"
    )
    evidence_sha = _sha256(evidence_path)
    kernel_side_evidence_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_kernel_side_typed_path_evidence.json"
    )
    kernel_side_evidence_sha = _sha256(kernel_side_evidence_path)
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "failures": [],
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
        "fourth_field_handoff_ready": True,
        "fourth_field_handoff_evidence_path": str(evidence_path),
        "fourth_field_handoff_evidence_sha256": evidence_sha,
        "fourth_field_handoff_source_count": source_count,
        "fourth_field_handoff_row_count": row_count,
        "fourth_field_handoff_row_ok_count": row_count,
        "fourth_field_handoff_field_read_hash": "3132333435363738",
        "fourth_field_handoff_runner_hash": "8182838485868788",
        "all_four_field_consumer_ready": True,
        "all_four_field_consumer_fields_read": True,
        "all_four_field_consumer_hashes_valid": True,
        "all_four_field_consumer_source_count": source_count,
        "all_four_field_consumer_row_count": row_count,
        "all_four_field_consumer_row_ok_count": row_count,
        "all_four_field_consumer_fourth_field_path_label": str(evidence_path),
        "all_four_field_consumer_fourth_field_sha256": evidence_sha,
        "future_wna16_kernel_side_typed_consumer_path_ready": True,
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        "future_wna16_kernel_side_typed_consumer_path_evidence_path": str(
            kernel_side_evidence_path
        ),
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256": (
            kernel_side_evidence_sha
        ),
        "future_wna16_kernel_side_typed_consumer_path_source_count": source_count,
        "future_wna16_kernel_side_typed_consumer_path_input_json_count": source_count,
        "future_wna16_kernel_side_typed_consumer_path_row_count": row_count,
        "future_wna16_kernel_side_typed_consumer_path_row_ok_count": row_count,
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256": "7" * 64,
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": (
            "6" * 64
        ),
        "entry_args_ptr_required": True,
        "entry_args_ptr_sweep_json": "",
        "entry_args_ptr_sweep_sha256": "",
        "entry_args_ptr_sweep_check_json": "",
        "entry_args_ptr_sweep_check_sha256": "",
        "entry_args_ptr_sweep_row_count": row_count,
        "entry_args_ptr_sweep_check_row_count": row_count,
        "entry_args_ptr_sweep_device": 1,
        "entry_args_ptr_sweep_window_size": 512,
        "entry_args_ptr_sweep_mirror_fields": list(HANDLE_FIELDS),
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
        "native_stub_host_wall_ms": host_wall_ms,
    }


def _benchmark_payload(
    timing_stub_json: Path,
    *,
    row_count: int = 513,
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
        "failures": [],
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
        "fourth_field_handoff_ready": True,
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
        "fourth_field_handoff_source_count": source_count,
        "fourth_field_handoff_row_count": row_count,
        "fourth_field_handoff_row_ok_count": row_count,
        "fourth_field_handoff_field_read_hash": "3132333435363738",
        "fourth_field_handoff_runner_hash": timing_payload[
            "fourth_field_handoff_runner_hash"
        ],
        "fourth_field_handoff_evidence_path": timing_payload[
            "fourth_field_handoff_evidence_path"
        ],
        "fourth_field_handoff_evidence_sha256": timing_payload[
            "fourth_field_handoff_evidence_sha256"
        ],
        "all_four_field_consumer_ready": True,
        "all_four_field_consumer_fields_read": True,
        "all_four_field_consumer_hashes_valid": True,
        "all_four_field_consumer_source_count": source_count,
        "all_four_field_consumer_row_count": row_count,
        "all_four_field_consumer_row_ok_count": row_count,
        "all_four_field_consumer_fourth_field_path_label": timing_payload[
            "all_four_field_consumer_fourth_field_path_label"
        ],
        "all_four_field_consumer_fourth_field_sha256": timing_payload[
            "all_four_field_consumer_fourth_field_sha256"
        ],
        "future_wna16_kernel_side_typed_consumer_path_ready": timing_payload[
            "future_wna16_kernel_side_typed_consumer_path_ready"
        ],
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": timing_payload[
            "future_wna16_kernel_side_typed_consumer_path_hashes_valid"
        ],
        "future_wna16_kernel_side_typed_consumer_path_evidence_path": timing_payload[
            "future_wna16_kernel_side_typed_consumer_path_evidence_path"
        ],
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256": timing_payload[
            "future_wna16_kernel_side_typed_consumer_path_evidence_sha256"
        ],
        "future_wna16_kernel_side_typed_consumer_path_source_count": source_count,
        "future_wna16_kernel_side_typed_consumer_path_input_json_count": source_count,
        "future_wna16_kernel_side_typed_consumer_path_row_count": row_count,
        "future_wna16_kernel_side_typed_consumer_path_row_ok_count": row_count,
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256": timing_payload[
            "future_wna16_kernel_side_typed_consumer_path_all_four_sha256"
        ],
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": timing_payload[
            "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"
        ],
        "entry_args_ptr_required": timing_payload["entry_args_ptr_required"],
        "entry_args_ptr_sweep_json": timing_payload["entry_args_ptr_sweep_json"],
        "entry_args_ptr_sweep_sha256": timing_payload["entry_args_ptr_sweep_sha256"],
        "entry_args_ptr_sweep_check_json": timing_payload[
            "entry_args_ptr_sweep_check_json"
        ],
        "entry_args_ptr_sweep_check_sha256": timing_payload[
            "entry_args_ptr_sweep_check_sha256"
        ],
        "entry_args_ptr_sweep_row_count": row_count,
        "entry_args_ptr_sweep_check_row_count": row_count,
        "entry_args_ptr_sweep_device": timing_payload["entry_args_ptr_sweep_device"],
        "entry_args_ptr_sweep_window_size": timing_payload[
            "entry_args_ptr_sweep_window_size"
        ],
        "entry_args_ptr_sweep_mirror_fields": timing_payload[
            "entry_args_ptr_sweep_mirror_fields"
        ],
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": timing_payload[
            "entry_args_ptr_sweep_require_kernel_arg_packet_abi"
        ],
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": timing_payload[
            "entry_args_ptr_sweep_require_kernel_entry_args_abi"
        ],
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": timing_payload[
            "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi"
        ],
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
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    payloadless_root = tmp_path / "payloadless_root_evidence.json"
    root_payload = json.loads(
        (fixture_dir / "future_wna16_payloadless_root_evidence.json").read_text(
            encoding="utf-8",
        )
    )
    root_payload["source_count"] = timing_payload["source_count"]
    root_payload["row_count"] = timing_payload["row_count"]
    root_payload["row_ok_count"] = timing_payload["row_count"]
    _write_json(payloadless_root, root_payload)
    fourth_evidence = tmp_path / "fourth_field_evidence.json"
    fourth_payload = json.loads(
        (fixture_dir / "future_wna16_fourth_field_evidence.json").read_text(
            encoding="utf-8",
        )
    )
    fourth_payload["source_count"] = timing_payload["source_count"]
    fourth_payload["row_count"] = timing_payload["row_count"]
    fourth_payload["row_ok_count"] = timing_payload["row_count"]
    fourth_payload["fourth_field_handoff_field_read_row_ok_count"] = timing_payload[
        "row_count"
    ]
    fourth_payload["payloadless_execution_json"] = str(payloadless_root)
    fourth_payload["payloadless_execution_sha256"] = _sha256(payloadless_root)
    _write_json(fourth_evidence, fourth_payload)
    kernel_side_evidence = tmp_path / "kernel_side_typed_path_evidence.json"
    kernel_side_payload = json.loads(
        (fixture_dir / "future_wna16_kernel_side_typed_path_evidence.json").read_text(
            encoding="utf-8",
        )
    )
    kernel_side_payload["source_count"] = timing_payload["source_count"]
    kernel_side_payload["input_json_count"] = timing_payload["source_count"]
    kernel_side_payload["row_count"] = timing_payload["row_count"]
    kernel_side_payload["row_ok_count"] = timing_payload["row_count"]
    _write_json(kernel_side_evidence, kernel_side_payload)
    timing_payload["fourth_field_handoff_evidence_path"] = str(fourth_evidence)
    timing_payload["fourth_field_handoff_evidence_sha256"] = _sha256(fourth_evidence)
    timing_payload["all_four_field_consumer_fourth_field_path_label"] = str(
        fourth_evidence
    )
    timing_payload["all_four_field_consumer_fourth_field_sha256"] = _sha256(
        fourth_evidence
    )
    timing_payload["future_wna16_kernel_side_typed_consumer_path_evidence_path"] = str(
        kernel_side_evidence
    )
    timing_payload["future_wna16_kernel_side_typed_consumer_path_evidence_sha256"] = (
        _sha256(kernel_side_evidence)
    )
    sweep = tmp_path / "entry_args_ptr_sweep.json"
    sweep_check = tmp_path / "entry_args_ptr_sweep.check.json"
    _write_json(
        sweep,
        {
            "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
            "passed": True,
            "failures": [],
            "device": 1,
            "window_size": 512,
            "mirror_fields": list(HANDLE_FIELDS),
            "row_counts": {field: timing_payload["row_count"] for field in HANDLE_FIELDS},
            "field_reports": {
                field: {
                    "passed": True,
                    "sweep_failures": [],
                    "check_failures": [],
                    "row_count": timing_payload["row_count"],
                    "window_size": 512,
                    "windows_checked": ["full", "head", "middle", "tail"],
                    "sweep_json": f"window_sweep_{field}.json",
                    "check_json": f"window_sweep_{field}.check.json",
                }
                for field in HANDLE_FIELDS
            },
            "require_program_view_ptr_abi": True,
            "require_kernel_arg_packet_abi": True,
            "require_kernel_entry_args_abi": True,
            "require_kernel_entry_args_ptr_abi": True,
            "payload_bytes": 0,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
        },
    )
    _write_json(
        sweep_check,
        {
            "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
            "passed": True,
            "failures": [],
            "all_field_window_sweep_json": str(sweep),
            "expected_window_size": 512,
            "mirror_fields_checked": list(HANDLE_FIELDS),
            "require_child_program_view_ptr_abi": True,
            "require_child_kernel_arg_packet_abi": True,
            "require_child_kernel_entry_args_abi": True,
            "require_child_kernel_entry_args_ptr_abi": True,
            "row_count": timing_payload["row_count"],
        },
    )
    timing_payload["entry_args_ptr_sweep_json"] = str(sweep)
    timing_payload["entry_args_ptr_sweep_sha256"] = _sha256(sweep)
    timing_payload["entry_args_ptr_sweep_check_json"] = str(sweep_check)
    timing_payload["entry_args_ptr_sweep_check_sha256"] = _sha256(sweep_check)
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
    assert result["payloadless_execution_native_artifact_ready"] is False
    assert result["payloadless_execution_lab_preflight_ready"] is False
    assert result["payloadless_execution_timing_stub_sha256"] is None
    assert result["payloadless_execution_runner_json"] is None
    assert result["payloadless_execution_runner_sha256"] is None
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert result["future_wna16_kernel_side_typed_consumer_path_ready"] is True
    assert result["future_wna16_kernel_side_typed_consumer_path_source_count"] == 128
    assert result["future_wna16_kernel_side_typed_consumer_path_row_count"] == 513
    assert result["entry_args_ptr_required"] is True
    assert result["entry_args_ptr_sweep_row_count"] == 513
    assert result["entry_args_ptr_sweep_check_row_count"] == 513
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


def test_payloadless_execution_rejects_benchmark_seed_fourth_evidence_drift(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["fourth_field_handoff_evidence_sha256"] = "7" * 64
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
    assert "benchmark_seed_fourth_field_handoff_evidence_sha256_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_benchmark_seed_all_four_drift(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["all_four_field_consumer_row_count"] = payload["row_count"] - 1
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
    assert "benchmark_seed_all_four_field_consumer_row_count_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_kernel_side_evidence_sha_drift(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["future_wna16_kernel_side_typed_consumer_path_evidence_sha256"] = "8" * 64
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
    assert "benchmark_kernel_side_typed_path_evidence_sha_mismatch" in result[
        "failures"
    ]
    assert "benchmark_seed_future_wna16_kernel_side_typed_consumer_path_evidence_sha256_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_kernel_side_selected_manifest_drift(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload[
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"
    ] = "9" * 64
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
    assert "benchmark_kernel_side_typed_path_evidence_selected_manifest_mismatch" in result[
        "failures"
    ]
    assert "benchmark_seed_future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_missing_fourth_field_handoff(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload.pop("fourth_field_handoff_ready")
    payload.pop("fourth_field_handoff_source_count")
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
    assert any("fourth_field_handoff_ready" in item for item in result["failures"])
    assert "benchmark_fourth_field_handoff_source_count_invalid" in result["failures"]


def test_payloadless_execution_rejects_fourth_descriptor_hash_drift(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["fourth_field_handoff_field_read_hash"] = "7172737475767778"
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
    assert "benchmark_fourth_field_handoff_descriptor_hash_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_missing_entry_args_ptr_contract(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["entry_args_ptr_required"] = False
    payload["entry_args_ptr_sweep_mirror_fields"] = ["descriptor_ptr"]
    payload["entry_args_ptr_sweep_check_row_count"] = payload["row_count"] - 1
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
    assert any("entry_args_ptr_required" in item for item in result["failures"])
    assert "benchmark_entry_args_ptr_sweep_mirror_fields_mismatch" in result[
        "failures"
    ]
    assert "benchmark_entry_args_ptr_sweep_check_row_count_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_entry_args_ptr_evidence_content_drift(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    sweep_path = Path(payload["entry_args_ptr_sweep_json"])
    sweep_payload = json.loads(sweep_path.read_text(encoding="utf-8"))
    sweep_payload["require_kernel_entry_args_ptr_abi"] = False
    _write_json(sweep_path, sweep_payload)
    payload["entry_args_ptr_sweep_sha256"] = _sha256(sweep_path)
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
    assert "benchmark_entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi_mismatch:False!=True" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_entry_args_ptr_field_report_drift(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    sweep_path = Path(payload["entry_args_ptr_sweep_json"])
    sweep_payload = json.loads(sweep_path.read_text(encoding="utf-8"))
    sweep_payload["field_reports"]["descriptor_ptr"]["passed"] = False
    _write_json(sweep_path, sweep_payload)
    payload["entry_args_ptr_sweep_sha256"] = _sha256(sweep_path)
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
    assert "benchmark_entry_args_ptr_sweep_descriptor_ptr_passed_mismatch:False!=True" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_entry_args_ptr_check_path_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    check_path = Path(payload["entry_args_ptr_sweep_check_json"])
    check_payload = json.loads(check_path.read_text(encoding="utf-8"))
    check_payload["all_field_window_sweep_json"] = "entry_args_ptr_sweep.json"
    _write_json(check_path, check_payload)
    payload["entry_args_ptr_sweep_check_sha256"] = _sha256(check_path)
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
    assert "benchmark_entry_args_ptr_sweep_check_sweep_path_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_all_four_not_ready(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["all_four_field_consumer_ready"] = False
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
    assert any("all_four_field_consumer_ready" in item for item in result["failures"])


def test_payloadless_execution_rejects_unrelated_fourth_evidence(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_text('{"passed": true}\n', encoding="utf-8")
    unrelated_sha = _sha256(unrelated)
    payload = _benchmark_payload(timing_stub)
    payload["fourth_field_handoff_evidence_path"] = str(unrelated)
    payload["fourth_field_handoff_evidence_sha256"] = unrelated_sha
    payload["all_four_field_consumer_fourth_field_path_label"] = str(unrelated)
    payload["all_four_field_consumer_fourth_field_sha256"] = unrelated_sha
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
    assert any("benchmark_fourth_evidence_artifact_kind" in item for item in result["failures"])


def test_payloadless_execution_rejects_fourth_row_count_mismatch(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["fourth_field_handoff_row_count"] = payload["row_count"] - 1
    payload["fourth_field_handoff_row_ok_count"] = payload["row_count"] - 1
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
    assert "benchmark_fourth_field_handoff_row_count_mismatch" in result["failures"]


def test_payloadless_execution_rejects_fourth_row_ok_mismatch(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["fourth_field_handoff_row_ok_count"] = payload["row_count"] - 1
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
    assert "benchmark_fourth_field_handoff_row_ok_count_mismatch" in result[
        "failures"
    ]


def test_payloadless_execution_rejects_fourth_runner_hash_invalid(tmp_path: Path):
    module = _load_module()
    _, _, timing_stub, _ = _write_seed_artifacts(tmp_path)
    benchmark = tmp_path / "benchmark.json"
    payload = _benchmark_payload(timing_stub)
    payload["fourth_field_handoff_runner_hash"] = "not-hex"
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
    assert "benchmark_fourth_field_handoff_runner_hash_invalid" in result["failures"]


def test_payloadless_execution_defaults_to_four_field_repeat3_benchmark():
    module = _load_module()
    default_path = Path(module.DEFAULT_BENCHMARK_JSON)

    assert (
        "future_wna16_typed_slot_kernel_variant_benchmark_entry_args_ptr_repeat3_v1.json"
        in str(default_path)
    )
    if default_path.exists():
        payload = json.loads(default_path.read_text(encoding="utf-8"))
        assert payload["fourth_field_handoff_ready"] is True
        assert payload["future_wna16_kernel_side_typed_consumer_path_ready"] is True
        assert payload["repeat_count_measured"] >= module.build_parser().get_default(
            "min_repeat_count"
        )
        assert len(payload["repeat_output_jsons"]) == payload["repeat_count_measured"]
        assert len(payload["repeat_output_sha256s"]) == payload["repeat_count_measured"]
        assert payload["entry_args_ptr_required"] is True
        assert payload["entry_args_ptr_sweep_row_count"] >= module.build_parser().get_default(
            "min_row_count"
        )
        assert payload["entry_args_ptr_sweep_check_row_count"] == payload[
            "entry_args_ptr_sweep_row_count"
        ]
        assert module._check_benchmark(  # noqa: SLF001
            payload,
            min_source_count=module.build_parser().get_default("min_source_count"),
            min_row_count=module.build_parser().get_default("min_row_count"),
            min_repeat_count=module.build_parser().get_default("min_repeat_count"),
        ) == []
        assert payload["field_read_hashes"]["descriptor_ptr"] == payload[
            "fourth_field_handoff_field_read_hash"
        ]


def test_payloadless_execution_default_entrypoint_passes_without_native_run(
    tmp_path: Path,
):
    module = _load_module()
    default_path = Path(module.DEFAULT_BENCHMARK_JSON)
    assert default_path.exists()
    output = tmp_path / "payloadless_default.json"
    args = module.build_parser().parse_args(["--output-json", str(output)])

    result = module.run_payloadless_execution(args)

    assert result["passed"] is True
    assert result["benchmark_json"] == str(default_path)
    assert result["payloadless_execution_gate_ready"] is True
    assert result["payloadless_execution_native_executed"] is False
    assert result["benchmark_repeat_count_measured"] >= module.build_parser().get_default(
        "min_repeat_count"
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


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
    assert result["payloadless_execution_native_artifact_ready"] is True
    assert result["payloadless_execution_lab_preflight_ready"] is True
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
