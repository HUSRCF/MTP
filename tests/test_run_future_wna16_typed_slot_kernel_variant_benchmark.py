from __future__ import annotations

import importlib.util
import hashlib
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
        / "run_future_wna16_typed_slot_kernel_variant_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_benchmark",
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
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_timing_stub",
        "timing_stub_name": "premap_future_wna16_typed_slot_kernel_timing_stub_v1",
        "timing_stub_mode": "independent_future_wna16_typed_slot_native_stub_timing",
        "timing_stub_source": "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1",
        "passed": True,
        "failures": [],
        "entrypoint_json": "entrypoint.json",
        "entrypoint_sha256": "a" * 64,
        "runner_json": "runner.json",
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
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": "6"
        * 64,
        "timing_stub_ready": True,
        "native_stub_requested": True,
        "native_stub_executed": True,
        "native_stub_host_wall_ms": host_wall_ms,
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
        "next_runtime_stage": "implement_future_wna16_typed_slot_kernel_variant_benchmark",
    }


def _attach_seed_artifacts(tmp_path: Path, payload: dict) -> None:
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    payload["entrypoint_sha256"] = _sha256(entrypoint)
    payload["runner_sha256"] = _sha256(runner)


def test_future_wna16_typed_slot_variant_benchmark_accepts_timing_stub(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    output = tmp_path / "benchmark.json"
    payload = _timing_stub_payload(host_wall_ms=17.0)
    _attach_seed_artifacts(tmp_path, payload)
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(output),
            "--repeat-count",
            "0",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is True
    assert result["typed_slot_variant_benchmark_ready"] is True
    assert result["future_wna16_variant_benchmark_ready"] is True
    assert result["wna16_benchmark_ready"] is False
    assert result["measures_tpot"] is False
    assert result["measures_vllm_latency"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["payload_deref_allowed"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["native_stub_host_wall_ms_stats"]["median_ms"] == 17.0
    assert result["fourth_field_handoff_ready"] is True
    assert result["fourth_field_handoff_source_count"] == 128
    assert result["fourth_field_handoff_row_count"] == 257
    assert result["fourth_field_handoff_row_ok_count"] == 257
    assert result["fourth_field_handoff_field_read_hash"] == "3132333435363738"
    assert result["fourth_field_handoff_runner_hash"] == "8182838485868788"
    assert result["future_wna16_kernel_side_typed_consumer_path_ready"] is True
    assert result["future_wna16_kernel_side_typed_consumer_path_source_count"] == 128
    assert result["future_wna16_kernel_side_typed_consumer_path_row_count"] == 257
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_future_wna16_typed_slot_variant_benchmark_defaults_to_kernel_side_native_stub():
    module = _load_module()

    default_path = Path(module.build_parser().parse_args([]).timing_stub_json)

    assert (
        default_path.name
        == "future_wna16_typed_slot_kernel_timing_stub_kernel_side_path_native_v1.json"
    )
    assert "premap_kernel_consumer" in default_path.parts


def test_future_wna16_typed_slot_variant_benchmark_rejects_missing_kernel_side_path(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["future_wna16_kernel_side_typed_consumer_path_ready"] = False
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any(
        "future_wna16_kernel_side_typed_consumer_path_ready" in item
        for item in result["failures"]
    )


def test_future_wna16_typed_slot_variant_benchmark_rejects_kernel_side_path_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["future_wna16_kernel_side_typed_consumer_path_row_count"] = 1
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "timing_stub_kernel_side_typed_path_row_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_variant_benchmark_rejects_kernel_side_evidence_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["future_wna16_kernel_side_typed_consumer_path_evidence_sha256"] = "0" * 64
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert (
        "timing_stub_kernel_side_typed_path_evidence_sha_mismatch"
        in result["failures"]
    )


def test_future_wna16_typed_slot_variant_benchmark_rejects_kernel_side_evidence_manifest_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"] = (
        "0" * 64
    )
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert (
        "timing_stub_kernel_side_typed_path_evidence_selected_manifest_mismatch"
        in result["failures"]
    )


def test_future_wna16_typed_slot_variant_benchmark_rejects_non_native_stub(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["native_stub_executed"] = False
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-count",
            "0",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any("native_stub_executed" in item for item in result["failures"])


def test_future_wna16_typed_slot_variant_benchmark_rejects_current_arg_pass(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["passes_current_wna16_args"] = True
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any("passes_current_wna16_args" in item for item in result["failures"])


def test_future_wna16_typed_slot_variant_benchmark_rejects_seed_failures(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["failures"] = ["synthetic_seed_failure"]
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "timing_stub_failures_not_empty" in result["failures"]


def test_future_wna16_typed_slot_variant_benchmark_rejects_untrusted_seed_repeat0(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    payload["entrypoint_json"] = str(tmp_path / "missing_entrypoint.json")
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-count",
            "0",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "seed_entrypoint_json_not_found" in result["failures"]
    assert result["repeat_count_measured"] == 0


def test_future_wna16_typed_slot_variant_benchmark_reports_seed_sha_error(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint_dir = tmp_path / "entrypoint_dir"
    entrypoint_dir.mkdir()
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload = _timing_stub_payload()
    payload["entrypoint_json"] = str(entrypoint_dir)
    payload["runner_json"] = str(runner)
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-count",
            "0",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any(item.startswith("seed_entrypoint_sha256_error:") for item in result["failures"])


def test_future_wna16_typed_slot_variant_benchmark_skips_repeats_on_bad_seed(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["passes_current_wna16_args"] = True
    _write_json(timing_stub, payload)

    def fail_if_called(args):
        raise AssertionError("repeat runner must not run for invalid seed")

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fail_if_called)
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-count",
            "1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "repeat_skipped_due_to_seed_contract_failure" in result["failures"]
    assert result["repeat_count_measured"] == 0
    assert result["measures_native_stub_host_wall_time"] is False


def test_future_wna16_typed_slot_variant_benchmark_rejects_extra_field(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["field_read_hashes"]["unexpected"] = "7172737475767778"
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "timing_stub_field_read_hashes_keys_mismatch" in result["failures"]


def test_future_wna16_typed_slot_variant_benchmark_rejects_fourth_source_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["fourth_field_handoff_source_count"] = 129
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "timing_stub_fourth_field_handoff_source_count_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_variant_benchmark_rejects_missing_fourth_row(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    del payload["fourth_field_handoff_row_count"]
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "timing_stub_fourth_field_handoff_row_count_invalid" in result["failures"]


def test_future_wna16_typed_slot_variant_benchmark_rejects_fourth_hash_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["fourth_field_handoff_field_read_hash"] = "7172737475767778"
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "timing_stub_fourth_field_handoff_descriptor_hash_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_variant_benchmark_rejects_missing_all_four_ready(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["all_four_field_consumer_ready"] = False
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any("all_four_field_consumer_ready" in item for item in result["failures"])


def test_future_wna16_typed_slot_variant_benchmark_rejects_unrelated_fourth_evidence(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_text('{"passed": true}\n', encoding="utf-8")
    unrelated_sha = _sha256(unrelated)
    payload = _timing_stub_payload()
    _attach_seed_artifacts(tmp_path, payload)
    payload["fourth_field_handoff_evidence_path"] = str(unrelated)
    payload["fourth_field_handoff_evidence_sha256"] = unrelated_sha
    payload["all_four_field_consumer_fourth_field_path_label"] = str(unrelated)
    payload["all_four_field_consumer_fourth_field_sha256"] = unrelated_sha
    _write_json(timing_stub, payload)

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any(
        "timing_stub_fourth_evidence_artifact_kind" in item
        for item in result["failures"]
    )


def test_future_wna16_typed_slot_variant_benchmark_runs_fake_repeats(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    payload["entrypoint_sha256"] = _sha256(entrypoint)
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)
    values = [10.0, 20.0, 30.0]

    def fake_run_timing_stub(args):
        report = _timing_stub_payload(host_wall_ms=values.pop(0))
        report["entrypoint_json"] = str(entrypoint)
        report["runner_json"] = str(runner)
        report["entrypoint_sha256"] = _sha256(entrypoint)
        report["runner_sha256"] = _sha256(runner)
        _write_json(Path(args.output_json), report)
        return report

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-output-dir",
            str(tmp_path / "repeats"),
            "--repeat-count",
            "3",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is True
    assert result["repeat_count_requested"] == 3
    assert result["repeat_count_measured"] == 3
    assert result["native_stub_host_wall_ms_stats"]["median_ms"] == 20.0
    assert result["native_stub_host_wall_ms_stats"]["mean_ms"] == 20.0
    assert result["benchmark_outer_wall_ms_stats"]["count"] == 3


def test_future_wna16_typed_slot_variant_benchmark_rejects_repeat_drift(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    payload["entrypoint_sha256"] = _sha256(entrypoint)
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)

    def fake_run_timing_stub(args):
        report = _timing_stub_payload(host_wall_ms=20.0)
        report["entrypoint_json"] = str(entrypoint)
        report["runner_json"] = str(runner)
        report["entrypoint_sha256"] = _sha256(entrypoint)
        report["runner_sha256"] = _sha256(runner)
        report["row_hash_accumulator"] = "8182838485868788"
        _write_json(Path(args.output_json), report)
        return report

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-output-dir",
            str(tmp_path / "repeats"),
            "--repeat-count",
            "1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "repeat_0:row_hash_accumulator_mismatch" in result["failures"]
    assert result["repeat_count_measured"] == 0


def test_future_wna16_typed_slot_variant_benchmark_rejects_missing_repeat_output(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    payload["entrypoint_sha256"] = _sha256(entrypoint)
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)

    def fake_run_timing_stub(args):
        report = _timing_stub_payload(host_wall_ms=20.0)
        report["entrypoint_json"] = str(entrypoint)
        report["runner_json"] = str(runner)
        report["entrypoint_sha256"] = _sha256(entrypoint)
        report["runner_sha256"] = _sha256(runner)
        return report

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-output-dir",
            str(tmp_path / "repeats"),
            "--repeat-count",
            "1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "repeat_0:output_json_missing" in result["failures"]
    assert result["repeat_count_measured"] == 0
    assert result["native_stub_host_wall_ms_stats"]["count"] == 0


def test_future_wna16_typed_slot_variant_benchmark_rejects_repeat_fourth_drift(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    payload["entrypoint_sha256"] = _sha256(entrypoint)
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)

    def fake_run_timing_stub(args):
        report = _timing_stub_payload(host_wall_ms=20.0)
        report["entrypoint_json"] = str(entrypoint)
        report["runner_json"] = str(runner)
        report["entrypoint_sha256"] = _sha256(entrypoint)
        report["runner_sha256"] = _sha256(runner)
        report["fourth_field_handoff_runner_hash"] = "9192939495969798"
        _write_json(Path(args.output_json), report)
        return report

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-output-dir",
            str(tmp_path / "repeats"),
            "--repeat-count",
            "1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "repeat_0:fourth_field_handoff_runner_hash_mismatch" in result["failures"]


def test_future_wna16_typed_slot_variant_benchmark_catches_repeat_exception(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    payload["entrypoint_sha256"] = _sha256(entrypoint)
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)

    def fake_run_timing_stub(args):
        raise RuntimeError("boom")

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fake_run_timing_stub)
    output = tmp_path / "benchmark.json"
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(output),
            "--repeat-count",
            "1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert any("repeat_0:exception:RuntimeError:boom" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_future_wna16_typed_slot_variant_benchmark_skips_repeat_on_seed_sha_mismatch(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payload = _timing_stub_payload()
    payload["entrypoint_json"] = str(entrypoint)
    payload["runner_json"] = str(runner)
    _write_json(entrypoint, {"ok": True})
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})
    payload["entrypoint_sha256"] = "0" * 64
    payload["runner_sha256"] = _sha256(runner)
    _write_json(timing_stub, payload)

    def fail_if_called(args):
        raise AssertionError("repeat runner must not run for mismatched seed sha")

    monkeypatch.setattr(module.timing_runner, "run_timing_stub", fail_if_called)
    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-count",
            "1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "seed_entrypoint_sha256_mismatch" in result["failures"]
    assert "repeat_skipped_due_to_seed_contract_failure" in result["failures"]
    assert result["repeat_count_measured"] == 0


def test_future_wna16_typed_slot_variant_benchmark_rejects_negative_repeat(
    tmp_path: Path,
):
    module = _load_module()
    timing_stub = tmp_path / "timing_stub.json"
    _write_json(timing_stub, _timing_stub_payload())

    args = module.build_parser().parse_args(
        [
            "--timing-stub-json",
            str(timing_stub),
            "--output-json",
            str(tmp_path / "benchmark.json"),
            "--repeat-count",
            "-1",
        ]
    )
    result = module.run_benchmark(args)

    assert result["passed"] is False
    assert "repeat_count_negative" in result["failures"]
