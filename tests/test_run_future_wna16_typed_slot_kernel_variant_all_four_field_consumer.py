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
        / "run_future_wna16_typed_slot_kernel_variant_all_four_field_consumer.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_all_four_field_consumer",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_default_paths_use_entry_args_ptr_four_field_gate() -> None:
    module = _load_module()

    assert module.DEFAULT_FOURTH_FIELD_JSON.name == (
        "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_entry_args_ptr_default.json"
    )
    assert module.DEFAULT_FOURTH_FIELD_JSON.exists()
    assert module.DEFAULT_OUTPUT_JSON.name == (
        "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default.json"
    )
    assert module.DEFAULT_OUTPUT_DIR.name == (
        "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_entry_args_ptr_default"
    )


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


def _entry_args_ptr_sweep_payload(*, row_count: int = 513) -> dict:
    return {
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
        "passed": True,
        "failures": [],
        "dry_run": False,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "window_size": 512,
        "block_threads": 256,
        "mirror_fields": list(FIELDS),
        "require_program_view_ptr_abi": True,
        "require_kernel_arg_packet_abi": True,
        "require_kernel_entry_args_abi": True,
        "require_kernel_entry_args_ptr_abi": True,
        "row_counts": {field: row_count for field in FIELDS},
        "field_reports": {
            field: {
                "passed": True,
                "sweep_failures": [],
                "check_failures": [],
                "row_count": row_count,
                "window_size": 512,
                "windows_checked": ["full", "head", "middle", "tail"],
                "sweep_json": f"{field}.sweep.json",
                "check_json": f"{field}.check.json",
            }
            for field in FIELDS
        },
    }


def _entry_args_ptr_check_payload(sweep_json: Path, *, row_count: int = 513) -> dict:
    return {
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
        "passed": True,
        "failures": [],
        "all_field_window_sweep_json": str(sweep_json),
        "expected_window_size": 512,
        "expected_block_threads": 256,
        "min_row_count": 257,
        "require_child_checks": True,
        "require_child_field_masks": True,
        "require_child_consumer_view": True,
        "require_child_consumer_view_layout": True,
        "require_child_consumer_view_row_layout": True,
        "require_child_consumer_view_handle_projection": True,
        "require_child_program_view_ptr_abi": True,
        "require_child_kernel_arg_packet_abi": True,
        "require_child_kernel_entry_args_abi": True,
        "require_child_kernel_entry_args_ptr_abi": True,
        "require_child_kernel_entry_row_metadata": True,
        "mirror_fields_checked": list(FIELDS),
        "row_count": row_count,
    }


def _entry_args_ptr_payloadless_payload(
    *,
    sweep_json: Path,
    check_json: Path,
    source_count: int = 128,
    row_count: int = 257,
    sweep_row_count: int = 513,
) -> dict:
    return {
        "passed": True,
        "source_count": source_count,
        "row_count": row_count,
        "payloadless_execution_native_artifact_ready": True,
        "payloadless_execution_lab_preflight_ready": True,
        "payloadless_execution_native_requested": True,
        "payloadless_execution_native_executed": True,
        "payloadless_execution_native_passed": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "entry_args_ptr_required": True,
        "entry_args_ptr_sweep_device": 1,
        "entry_args_ptr_sweep_window_size": 512,
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
        "entry_args_ptr_sweep_mirror_fields": list(FIELDS),
        "entry_args_ptr_sweep_row_count": sweep_row_count,
        "entry_args_ptr_sweep_check_row_count": sweep_row_count,
        "entry_args_ptr_sweep_json": str(sweep_json),
        "entry_args_ptr_sweep_sha256": _sha256(sweep_json),
        "entry_args_ptr_sweep_check_json": str(check_json),
        "entry_args_ptr_sweep_check_sha256": _sha256(check_json),
        "field_read_hashes": {
            "descriptor_ptr": "1111111111111111",
            "packed_weight_descriptor": "5555555555555555",
            "scale_metadata_handle": "6666666666666666",
            "aux_metadata_handle": "7777777777777777",
        },
        "field_read_row_ok_counts": {field: row_count for field in FIELDS},
    }


def _merged_input(input_paths: list[Path]) -> dict:
    return {
        "_merge_context": {
            "source_count": len(input_paths),
            "row_spans": [
                {
                    "source_index": index,
                    "path": str(path),
                    "row_start": index,
                    "row_count": 1,
                    "row_end": index + 1,
                }
                for index, path in enumerate(input_paths)
            ],
        }
    }


def _seed_fourth_gate(
    tmp_path: Path,
    *,
    source_count: int = 128,
    row_count: int = 257,
) -> Path:
    input_paths: list[Path] = []
    for index in range(source_count):
        input_path = tmp_path / "inputs" / f"input_{index:04d}.json"
        _write_json(input_path, {"schema_version": 1, "row_count": 1})
        input_paths.append(input_path)
    underlying = tmp_path / "fourth_underlying.json"
    _write_json(
        underlying,
        {
            "passed": True,
            "source": "online_merged_future_native_arg_slot_canary_runner",
            "input_jsons": [str(path) for path in input_paths],
        },
    )
    sweep = tmp_path / "entry_args_ptr_sweep.json"
    check = tmp_path / "entry_args_ptr_sweep.check.json"
    _write_json(sweep, _entry_args_ptr_sweep_payload())
    _write_json(check, _entry_args_ptr_check_payload(sweep))
    payloadless = tmp_path / "payloadless_entry_args_ptr.json"
    _write_json(
        payloadless,
        _entry_args_ptr_payloadless_payload(
            sweep_json=sweep,
            check_json=check,
            source_count=source_count,
            row_count=row_count,
        ),
    )
    fourth = tmp_path / "fourth.json"
    _write_json(
        fourth,
        {
            "artifact_kind": (
                "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
            ),
            "fourth_field_handoff_canary_name": (
                "premap_future_wna16_typed_slot_fourth_field_handoff_canary_v1"
            ),
            "fourth_field_handoff_canary_mode": (
                "readonly_future_wna16_typed_slot_fourth_field_handoff_canary"
            ),
            "fourth_field_handoff_canary_source": (
                "premap_future_wna16_typed_slot_third_field_handoff_canary_v1"
            ),
            "passed": True,
            "failures": [],
            "previous_field_gate_ready": True,
            "fourth_field_name": "descriptor_ptr",
            "fourth_field_handoff_live_enabled": False,
            "fourth_field_handoff_block_reason": "fourth_field_handoff_live_disabled",
            "fourth_field_handoff_canary_native_requested": True,
            "fourth_field_handoff_canary_native_executed": True,
            "fourth_field_handoff_canary_native_passed": True,
            "source_count": source_count,
            "row_count": row_count,
            "row_ok_count": row_count,
            "fourth_field_handoff_field_read_row_ok_count": row_count,
            "fourth_field_handoff_canary_runner_row_count": row_count,
            "fourth_field_handoff_canary_runner_row_ok_count": row_count,
            "fourth_field_handoff_field_read_hash": "1111111111111111",
            "fourth_field_handoff_canary_runner_hash": "2222222222222222",
            "third_field_read_hash": "3333333333333333",
            "third_field_native_hash": "4444444444444444",
            "fourth_field_underlying_json": str(underlying),
            "fourth_field_underlying_sha256": _sha256(underlying),
            "payloadless_execution_json": str(payloadless),
            "payloadless_execution_sha256": _sha256(payloadless),
            "payloadless_execution_native_artifact_ready": True,
            "payloadless_execution_lab_preflight_ready": True,
            "payloadless_entry_args_ptr_required": True,
            "payloadless_entry_args_ptr_sweep_json": str(sweep),
            "payloadless_entry_args_ptr_sweep_sha256": _sha256(sweep),
            "payloadless_entry_args_ptr_sweep_check_json": str(check),
            "payloadless_entry_args_ptr_sweep_check_sha256": _sha256(check),
            "payloadless_entry_args_ptr_sweep_row_count": 513,
            "payloadless_entry_args_ptr_sweep_check_row_count": 513,
            "payloadless_entry_args_ptr_sweep_mirror_fields": list(FIELDS),
            "uses_current_wna16_args": False,
            "passes_current_wna16_args": False,
            "current_wna16_arg_compatible": False,
            "requires_wna16_arg_reinterpretation": False,
            "payload_bytes": 0,
            "payload_deref_allowed": False,
            "kernel_arg_pass_allowed": False,
            "passed_to_kernel": False,
            "changes_kernel_launch_args": False,
            "measures_tpot": False,
            "measures_vllm_latency": False,
        },
    )
    return fourth


def _native_report(
    *,
    source_count: int = 128,
    row_count: int = 257,
    input_paths: list[Path] | None = None,
) -> dict:
    return {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_canary_runner",
        "input_jsons": [str(path) for path in (input_paths or [])],
        "selected_input_json_count": len(input_paths or []),
        "selected_input_manifest_sha256": _input_manifest_sha(input_paths or []),
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
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
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


def _base_args(module, fourth: Path, output: Path, tmp_path: Path) -> list[str]:
    return [
        "--fourth-field-json",
        str(fourth),
        "--output-json",
        str(output),
        "--output-dir",
        str(tmp_path / "out"),
    ]


def test_all_four_field_consumer_runs_native_gate(tmp_path: Path, monkeypatch):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)
    output = tmp_path / "all_four.json"

    def fake_run(args, *, input_paths):
        assert len(input_paths) == 128
        out_dir = Path(args.output_dir)
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", _stub_payload())
        _write_json(out_dir / "all_four_field_native_runner.json", {"passed": True})
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        return _native_report(input_paths=input_paths), 12.5

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(_base_args(module, fourth, output, tmp_path))
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is True
    assert result["artifact_kind"] == (
        "future_wna16_typed_slot_kernel_variant_all_four_field_consumer"
    )
    assert result["future_wna16_kernel_side_consumer_execution_all_handle_fields_read"] is True
    assert result["wna16_side_consumer_variant_execution_all_handle_fields_read"] is True
    assert result["payload_bytes"] == 0
    assert result["passed_to_kernel"] is False
    assert result["current_wna16_arg_compatible"] is False
    assert result["measures_tpot"] is False
    assert result["wna16_benchmark_ready"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_all_four_field_consumer_rejects_current_wna16_arg_compatible(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", _stub_payload())
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        report = _native_report(input_paths=input_paths)
        report["current_wna16_arg_compatible"] = True
        return report, 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "native_report_current_wna16_arg_compatible_not_false" in result["failures"]


def test_all_four_field_consumer_rejects_native_current_wna16_arg_use(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", _stub_payload())
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        report = _native_report(input_paths=input_paths)
        report["uses_current_wna16_args"] = True
        return report, 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "native_report_uses_current_wna16_args_not_false" in result["failures"]


def test_all_four_field_consumer_rejects_row_mismatch(tmp_path: Path, monkeypatch):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path, row_count=257)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(
            out_dir / "all_four_field_typed_consumer_stub.json",
            _stub_payload(row_count=258),
        )
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        return _native_report(row_count=258, input_paths=input_paths), 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "native_row_count_fourth_gate_mismatch" in result["failures"]


def test_all_four_field_consumer_rejects_missing_field_read(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        stub = _stub_payload()
        stub[
            "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count"
        ] = 0
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", stub)
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        return _native_report(input_paths=input_paths), 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert (
        "wna16_side_consumer_variant_execution_descriptor_ptr_read_row_ok_count_mismatch"
        in result["failures"]
    )


def test_all_four_field_consumer_requires_native_execution(tmp_path: Path):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)
    args = module.build_parser().parse_args(
        [
            *_base_args(module, fourth, tmp_path / "out.json", tmp_path),
            "--no-run-native-consumer",
        ]
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "run_native_consumer_must_remain_enabled_for_lab_gate" in result["failures"]


def test_all_four_field_consumer_rejects_underlying_sha_mismatch(tmp_path: Path):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)
    payload = json.loads(fourth.read_text(encoding="utf-8"))
    payload["fourth_field_underlying_sha256"] = "0" * 64
    _write_json(fourth, payload)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "fourth_field_underlying_sha256_mismatch" in result["failures"]


def test_all_four_field_consumer_rejects_fourth_failures(tmp_path: Path):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)
    payload = json.loads(fourth.read_text(encoding="utf-8"))
    payload["failures"] = ["injected"]
    _write_json(fourth, payload)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "fourth_failures_not_empty" in result["failures"]


def test_all_four_field_consumer_rejects_payloadless_passed_false(tmp_path: Path):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)
    fourth_payload = json.loads(fourth.read_text(encoding="utf-8"))
    payloadless = Path(fourth_payload["payloadless_execution_json"])
    payloadless_payload = json.loads(payloadless.read_text(encoding="utf-8"))
    payloadless_payload["passed"] = False
    _write_json(payloadless, payloadless_payload)
    fourth_payload["payloadless_execution_sha256"] = _sha256(payloadless)
    _write_json(fourth, fourth_payload)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "fourth_payloadless_execution_passed_mismatch" in result["failures"]


def test_all_four_field_consumer_rejects_flattened_payloadless_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)
    payload = json.loads(fourth.read_text(encoding="utf-8"))
    payload["payloadless_entry_args_ptr_sweep_sha256"] = "0" * 64
    _write_json(fourth, payload)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert any(
        failure.startswith(
            "fourth_payloadless_entry_args_ptr_sweep_sha256_payloadless_mismatch"
        )
        for failure in result["failures"]
    )


def test_all_four_field_consumer_rejects_missing_boundary_field(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        stub = _stub_payload()
        del stub["future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"]
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", stub)
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        return _native_report(input_paths=input_paths), 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert (
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed_missing"
        in result["failures"]
    )


def test_all_four_field_consumer_rejects_native_manifest_mismatch(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", _stub_payload())
        _write_json(out_dir / "all_four_field_merged_input.json", _merged_input(input_paths))
        report = _native_report(input_paths=input_paths)
        report["selected_input_manifest_sha256"] = "0" * 64
        return report, 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "native_selected_input_manifest_sha256_mismatch" in result["failures"]


def test_all_four_field_consumer_rejects_merged_input_order_mismatch(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    fourth = _seed_fourth_gate(tmp_path)

    def fake_run(args, *, input_paths):
        out_dir = Path(args.output_dir)
        _write_json(out_dir / "all_four_field_typed_consumer_stub.json", _stub_payload())
        _write_json(
            out_dir / "all_four_field_merged_input.json",
            _merged_input(list(reversed(input_paths))),
        )
        return _native_report(input_paths=input_paths), 1.0

    monkeypatch.setattr(module, "_run_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(module, fourth, tmp_path / "out.json", tmp_path)
    )
    result = module.run_all_four_field_consumer(args)

    assert result["passed"] is False
    assert "merged_input_row_span_paths_mismatch" in result["failures"]
