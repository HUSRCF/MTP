from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
PREFIXES = (
    "future_wna16_kernel_side_consumer_execution",
    "wna16_side_consumer_variant_execution",
)


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_kernel_side_typed_consumer_path.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_kernel_side_typed_consumer_path",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_manifest_sha(input_paths: list[Path]) -> str:
    entries = [
        {"index": index, "path": str(path), "sha256": _sha256(path)}
        for index, path in enumerate(input_paths)
    ]
    data = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _seed_inputs(tmp_path: Path, count: int = 128) -> list[Path]:
    paths: list[Path] = []
    for index in range(count):
        path = tmp_path / "inputs" / f"input_{index:04d}.json"
        _write_json(path, {"schema_version": 1, "row_count": 1})
        paths.append(path)
    return paths


def _seed_all_four(
    tmp_path: Path,
    *,
    input_paths: list[Path] | None = None,
    source_count: int = 128,
    row_count: int = 257,
) -> Path:
    if input_paths is None:
        input_paths = _seed_inputs(tmp_path, source_count)
    fourth = tmp_path / "fourth.json"
    _write_json(
        fourth,
        {
            "artifact_kind": "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary",
            "passed": True,
            "failures": [],
            "source_count": source_count,
            "row_count": row_count,
            "row_ok_count": row_count,
            "fourth_field_name": "descriptor_ptr",
            "payload_bytes": 0,
            "payload_deref_allowed": False,
            "kernel_arg_pass_allowed": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
            "wna16_benchmark_ready": False,
        },
    )
    native = tmp_path / "all_four_native_runner.json"
    _write_json(
        native,
        {
            "passed": True,
            "input_jsons": [str(path) for path in input_paths],
        },
    )
    manifest_sha = _input_manifest_sha(input_paths)
    all_four = tmp_path / "all_four.json"
    _write_json(
        all_four,
        {
            "artifact_kind": "future_wna16_typed_slot_kernel_variant_all_four_field_consumer",
            "all_four_field_consumer_name": (
                "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
            ),
            "all_four_field_consumer_mode": (
                "readonly_future_wna16_typed_slot_all_four_field_consumer"
            ),
            "all_four_field_consumer_source": (
                "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
            ),
            "stage_type": "lab_gate",
            "bench_semantics": False,
            "passed": True,
            "failures": [],
            "native_consumer_executed": True,
            "native_consumer_passed": True,
            "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
            "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
            "kernel_arg_pass_allowed": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "payload_bytes": 0,
            "payload_deref_allowed": False,
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
            "wna16_benchmark_ready": False,
            "source_count": source_count,
            "row_count": row_count,
            "row_ok_count": row_count,
            "selected_input_json_count": len(input_paths),
            "fourth_field_json": str(fourth),
            "fourth_field_sha256": _sha256(fourth),
            "native_consumer_json": str(native),
            "native_consumer_sha256": _sha256(native),
            "selected_input_manifest_sha256": manifest_sha,
            "post_native_input_manifest_sha256": manifest_sha,
        },
    )
    return all_four


def _native_report(
    *,
    input_paths: list[Path],
    source_count: int = 128,
    row_count: int = 257,
) -> dict:
    return {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_canary_runner",
        "input_jsons": [str(path) for path in input_paths],
        "selected_input_json_count": len(input_paths),
        "selected_input_manifest_sha256": _input_manifest_sha(input_paths),
        "selected_source_count": source_count,
        "merged_row_count": row_count,
        "dispatch_active_rows": row_count,
        "require_future_wna16_typed_slot_kernel_variant": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_wna16_side_consumer_variant_execution": True,
        "require_wna16_adjacent_typed_slot": True,
        "future_wna16_typed_slot_kernel_variant_all_handle_fields_read": True,
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "no_payload": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "future_wna16_kernel_side_consumer_execution_row_count": row_count,
        "future_wna16_kernel_side_consumer_execution_row_ok_count": row_count,
        "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator": (
            "1111111111111111"
        ),
        "wna16_side_consumer_variant_execution_row_count": row_count,
        "wna16_side_consumer_variant_execution_row_ok_count": row_count,
        "wna16_side_consumer_variant_execution_handle_projection_hash_accumulator": (
            "2222222222222222"
        ),
    }


def _stub_payload(*, row_count: int = 257) -> dict:
    payload: dict = {}
    for prefix in PREFIXES:
        payload.update(
            {
                f"{prefix}_checked": True,
                f"{prefix}_row_count": row_count,
                f"{prefix}_row_ok_count": row_count,
                f"{prefix}_error_count": 0,
                f"{prefix}_payload_bytes": 0,
                f"{prefix}_payload_deref_allowed": False,
                f"{prefix}_kernel_arg_pass_allowed": False,
                f"{prefix}_passed_to_kernel": False,
                f"{prefix}_changes_kernel_launch_args": False,
                f"{prefix}_current_wna16_arg_compatible": False,
                f"{prefix}_requires_wna16_arg_reinterpretation": False,
                f"{prefix}_explicit_typed_abi_slot": True,
                f"{prefix}_reuses_current_wna16_arg_slot": False,
                f"{prefix}_hash_accumulator": "aaaaaaaaaaaaaaaa",
                f"{prefix}_handle_projection_hash_accumulator": "bbbbbbbbbbbbbbbb",
            }
        )
        for field in FIELDS:
            payload.update(
                {
                    f"{prefix}_{field}_read_row_count": row_count,
                    f"{prefix}_{field}_read_row_ok_count": row_count,
                    f"{prefix}_{field}_read_error_count": 0,
                    f"{prefix}_{field}_read_hash_accumulator": "cccccccccccccccc",
                }
            )
    return payload


def _base_args(module, all_four: Path, output: Path, tmp_path: Path) -> list[str]:
    return [
        "--all-four-json",
        str(all_four),
        "--output-json",
        str(output),
        "--output-dir",
        str(tmp_path / "out"),
    ]


def test_kernel_side_typed_consumer_path_runs_native_gate(tmp_path: Path, monkeypatch):
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)
    output = tmp_path / "path.json"

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        assert args.max_inputs == 128
        assert len(input_paths) == 128
        _write_json(
            out_dir / "kernel_side_consumer_path_typed_consumer_stub.json",
            _stub_payload(),
        )
        _write_json(out_dir / "kernel_side_consumer_path_native_runner.json", {"ok": True})
        _write_json(out_dir / "kernel_side_consumer_path_merged_input.json", {"ok": True})
        return _native_report(input_paths=input_paths), 12.5

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(_base_args(module, all_four, output, tmp_path))
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is True
    assert result["artifact_kind"] == "future_wna16_kernel_side_typed_consumer_path"
    assert result["independent_kernel_side_consumer_path"] is True
    assert result["future_wna16_kernel_side_consumer_execution_all_handle_fields_read"] is True
    assert result["wna16_side_consumer_variant_execution_all_handle_fields_read"] is True
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["bench_semantics"] is False
    assert result["measures_vllm_latency"] is False
    assert result["measures_tpot"] is False
    assert result["wna16_benchmark_ready"] is False
    assert result["native_consumer_wall_ms_observed_only"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_kernel_side_typed_consumer_path_defaults_to_v3_all_four() -> None:
    module = _load_module()

    default_path = Path(module.build_parser().parse_args([]).all_four_json)

    assert default_path.name == (
        "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_v3_default.json"
    )


def test_kernel_side_typed_consumer_path_rejects_all_four_current_args(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)
    payload = json.loads(all_four.read_text(encoding="utf-8"))
    payload["uses_current_wna16_args"] = True
    _write_json(all_four, payload)

    def fake_run(args, *, input_paths):
        raise AssertionError("native path must not run after failed all-four gate")

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, all_four, tmp_path / "path.json", tmp_path)
    )
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is False
    assert "all_four_uses_current_wna16_args_mismatch" in result["failures"]


def test_kernel_side_typed_consumer_path_rejects_native_arg_pass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(
            out_dir / "kernel_side_consumer_path_typed_consumer_stub.json",
            _stub_payload(),
        )
        _write_json(out_dir / "kernel_side_consumer_path_native_runner.json", {"ok": True})
        _write_json(out_dir / "kernel_side_consumer_path_merged_input.json", {"ok": True})
        report = _native_report(input_paths=input_paths)
        report["kernel_arg_pass_allowed"] = True
        return report, 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, all_four, tmp_path / "path.json", tmp_path)
    )
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is False
    assert "native_report_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_kernel_side_typed_consumer_path_keeps_all_four_ready_on_native_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(
            out_dir / "kernel_side_consumer_path_typed_consumer_stub.json",
            _stub_payload(),
        )
        _write_json(out_dir / "kernel_side_consumer_path_native_runner.json", {"ok": True})
        _write_json(out_dir / "kernel_side_consumer_path_merged_input.json", {"ok": True})
        report = _native_report(input_paths=input_paths)
        report["kernel_arg_pass_allowed"] = True
        return report, 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, all_four, tmp_path / "path.json", tmp_path)
    )
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is False
    assert result["all_four_gate_ready"] is True
    assert "native_report_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_kernel_side_typed_consumer_path_rejects_selected_input_count_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)
    payload = json.loads(all_four.read_text(encoding="utf-8"))
    payload["selected_input_json_count"] = 1
    _write_json(all_four, payload)

    def fake_run(args, *, input_paths):
        raise AssertionError("native path must not run after failed all-four gate")

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, all_four, tmp_path / "path.json", tmp_path)
    )
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is False
    assert "all_four_selected_input_json_count_mismatch" in result["failures"]


def test_kernel_side_typed_consumer_path_rejects_fourth_semantic_regression(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)
    payload = json.loads(all_four.read_text(encoding="utf-8"))
    fourth = Path(payload["fourth_field_json"])
    fourth_payload = json.loads(fourth.read_text(encoding="utf-8"))
    fourth_payload["uses_current_wna16_args"] = True
    _write_json(fourth, fourth_payload)
    payload["fourth_field_sha256"] = _sha256(fourth)
    _write_json(all_four, payload)

    def fake_run(args, *, input_paths):
        raise AssertionError("native path must not run after failed fourth evidence")

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, all_four, tmp_path / "path.json", tmp_path)
    )
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is False
    assert "all_four_fourth_field_uses_current_wna16_args_mismatch" in result["failures"]


def test_kernel_side_typed_consumer_path_rejects_missing_field_read(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    input_paths = _seed_inputs(tmp_path)
    all_four = _seed_all_four(tmp_path, input_paths=input_paths)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        stub = _stub_payload()
        stub[
            "future_wna16_kernel_side_consumer_execution_descriptor_ptr_read_row_ok_count"
        ] = 0
        _write_json(
            out_dir / "kernel_side_consumer_path_typed_consumer_stub.json",
            stub,
        )
        _write_json(out_dir / "kernel_side_consumer_path_native_runner.json", {"ok": True})
        _write_json(out_dir / "kernel_side_consumer_path_merged_input.json", {"ok": True})
        return _native_report(input_paths=input_paths), 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, all_four, tmp_path / "path.json", tmp_path)
    )
    result = module.run_kernel_side_typed_consumer_path(args)

    assert result["passed"] is False
    assert (
        "future_wna16_kernel_side_consumer_execution_descriptor_ptr_read_row_ok_count_mismatch"
        in result["failures"]
    )
