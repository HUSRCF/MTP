from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


FIRST_FIELD = "scale_metadata_handle"
SECOND_FIELD = "aux_metadata_handle"
THIRD_FIELD = "packed_weight_descriptor"
FOURTH_FIELD = "descriptor_ptr"
FIELD_KINDS = {
    "descriptor_ptr": 1,
    "packed_weight_descriptor": 2,
    "scale_metadata_handle": 3,
    "aux_metadata_handle": 4,
}
FIELD_HASHES = {
    "descriptor_ptr": "3132333435363738",
    "packed_weight_descriptor": "4142434445464748",
    "scale_metadata_handle": "5152535455565758",
    "aux_metadata_handle": "6162636465666768",
}
HANDLE_FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]
FOURTH_EVIDENCE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "future_wna16_fourth_field_evidence.json"
)


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary",
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
        "mirror_fields": HANDLE_FIELDS,
        "require_program_view_ptr_abi": True,
        "require_kernel_arg_packet_abi": True,
        "require_kernel_entry_args_abi": True,
        "require_kernel_entry_args_ptr_abi": True,
        "row_counts": {field: row_count for field in HANDLE_FIELDS},
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
            for field in HANDLE_FIELDS
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
        "mirror_fields_checked": HANDLE_FIELDS,
        "row_count": row_count,
    }


def _native_runner_payload(
    *,
    field: str,
    source_count: int = 128,
    row_count: int = 513,
    input_jsons: list[str] | None = None,
) -> dict:
    field_kind = FIELD_KINDS[field]
    return {
        "passed": True,
        "source": "online_merged_future_native_arg_slot_canary_runner",
        "mirror_field": field,
        "input_jsons": input_jsons or [],
        "selected_source_count": source_count,
        "merged_row_count": row_count,
        "dispatch_active_rows": row_count,
        "require_future_wna16_single_field_handoff_canary": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_wna16_adjacent_typed_slot": True,
        "future_wna16_single_field_handoff_canary_checked": True,
        "future_wna16_single_field_handoff_canary_name": (
            "premap_future_wna16_single_field_handoff_canary_v1"
        ),
        "future_wna16_single_field_handoff_canary_abi_name": (
            "premap_future_wna16_single_field_handoff_canary_v1"
        ),
        "future_wna16_single_field_handoff_canary_mode": (
            "readonly_future_wna16_single_field_handoff_canary"
        ),
        "future_wna16_single_field_handoff_canary_source": (
            "premap_future_wna16_kernel_side_consumer_execution_v1"
        ),
        "future_wna16_single_field_handoff_canary_field_read_path": (
            "future_wna16_single_field_handoff_to_"
            "future_wna16_kernel_side_execution_to_accepted_typed_slot_to_program_view_rows"
        ),
        "future_wna16_single_field_handoff_canary_field_name": field,
        "future_wna16_single_field_handoff_canary_field_kind": field_kind,
        "future_wna16_single_field_handoff_canary_field_mask": 1 << (field_kind - 1),
        "future_wna16_single_field_handoff_canary_row_count": row_count,
        "future_wna16_single_field_handoff_canary_row_ok_count": row_count,
        "future_wna16_single_field_handoff_canary_error_count": 0,
        "future_wna16_single_field_handoff_canary_hash_accumulator": (
            "ccccf3926bcd1234" if field == FOURTH_FIELD else "bbbcf3926bcd1234"
        ),
        "no_payload": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "measures_vllm_latency": False,
        "measures_tpot": False,
        "wna16_benchmark_ready": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "future_wna16_single_field_handoff_canary_live_enabled": False,
        "future_wna16_single_field_handoff_canary_payload_bytes": 0,
        "future_wna16_single_field_handoff_canary_passed_to_kernel": False,
        "future_wna16_single_field_handoff_canary_changes_kernel_launch_args": False,
        "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible": False,
        "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation": False,
        "future_wna16_single_field_handoff_canary_explicit_typed_abi_slot": True,
        "future_wna16_single_field_handoff_canary_reuses_current_wna16_arg_slot": False,
        "future_wna16_kernel_side_consumer_execution_payload_bytes": 0,
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed": False,
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed": False,
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel": False,
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args": False,
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible": False,
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation": False,
    }


def _previous_payload(
    payloadless_json: Path,
    runner_json: Path,
    *,
    row_count: int = 513,
) -> dict:
    fourth_evidence_sha = _sha256(FOURTH_EVIDENCE_PATH)
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_third_field_handoff_canary",
        "failures": [],
        "third_field_handoff_canary_name": (
            "premap_future_wna16_typed_slot_third_field_handoff_canary_v1"
        ),
        "third_field_handoff_canary_mode": (
            "readonly_future_wna16_typed_slot_third_field_handoff_canary"
        ),
        "third_field_handoff_canary_source": (
            "premap_future_wna16_typed_slot_second_field_handoff_canary_v1"
        ),
        "passed": True,
        "previous_field_gate_ready": True,
        "first_field_name": FIRST_FIELD,
        "second_field_name": SECOND_FIELD,
        "third_field_name": THIRD_FIELD,
        "third_field_handoff_canary_native_requested": True,
        "third_field_handoff_canary_native_executed": True,
        "third_field_handoff_canary_native_passed": True,
        "third_field_handoff_field_read_hash": FIELD_HASHES[THIRD_FIELD],
        "third_field_handoff_field_read_row_ok_count": row_count,
        "third_field_handoff_canary_runner_hash": "bbbcf3926bcd1234",
        "third_field_handoff_canary_runner_row_count": row_count,
        "third_field_handoff_canary_runner_row_ok_count": row_count,
        "third_field_handoff_live_enabled": False,
        "third_field_handoff_block_reason": "third_field_handoff_live_disabled",
        "third_field_underlying_json": str(runner_json),
        "third_field_underlying_sha256": _sha256(runner_json),
        "payloadless_execution_json": str(payloadless_json),
        "payloadless_execution_sha256": _sha256(payloadless_json),
        "payloadless_fourth_field_handoff_evidence_path": str(FOURTH_EVIDENCE_PATH),
        "payloadless_fourth_field_handoff_evidence_sha256": fourth_evidence_sha,
        "payloadless_all_four_field_consumer_ready": True,
        "payloadless_all_four_field_consumer_fields_read": True,
        "payloadless_all_four_field_consumer_hashes_valid": True,
        "payloadless_all_four_field_consumer_source_count": 128,
        "payloadless_all_four_field_consumer_row_count": row_count,
        "payloadless_all_four_field_consumer_row_ok_count": row_count,
        "payloadless_all_four_field_consumer_fourth_field_path_label": str(
            FOURTH_EVIDENCE_PATH
        ),
        "payloadless_all_four_field_consumer_fourth_field_sha256": fourth_evidence_sha,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary"
        ),
        "source_count": 128,
        "row_count": row_count,
        "row_ok_count": row_count,
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
    }


def _seed_previous_gate(tmp_path: Path, *, row_count: int = 513) -> Path:
    previous = tmp_path / "previous.json"
    payloadless = tmp_path / "payloadless.json"
    runner = tmp_path / "third_runner.json"
    input_json = tmp_path / "input_0000.json"
    sweep_json = tmp_path / "entry_args_ptr_sweep.json"
    check_json = tmp_path / "entry_args_ptr_sweep.check.json"
    _write_json(input_json, {"schema_version": 1, "row_count": row_count})
    _write_json(sweep_json, _entry_args_ptr_sweep_payload(row_count=row_count))
    _write_json(check_json, _entry_args_ptr_check_payload(sweep_json, row_count=row_count))
    _write_json(
        payloadless,
        {
            "passed": True,
            "source_count": 128,
            "row_count": row_count,
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
            "payloadless_execution_native_artifact_ready": True,
            "payloadless_execution_lab_preflight_ready": True,
            "payloadless_execution_native_requested": True,
            "payloadless_execution_native_executed": True,
            "payloadless_execution_native_passed": True,
            "entry_args_ptr_required": True,
            "entry_args_ptr_sweep_device": 1,
            "entry_args_ptr_sweep_window_size": 512,
            "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
            "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
            "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
            "entry_args_ptr_sweep_mirror_fields": [
                "descriptor_ptr",
                "packed_weight_descriptor",
                "scale_metadata_handle",
                "aux_metadata_handle",
            ],
            "entry_args_ptr_sweep_row_count": row_count,
            "entry_args_ptr_sweep_check_row_count": row_count,
            "entry_args_ptr_sweep_json": str(sweep_json),
            "entry_args_ptr_sweep_sha256": _sha256(sweep_json),
            "entry_args_ptr_sweep_check_json": str(check_json),
            "entry_args_ptr_sweep_check_sha256": _sha256(check_json),
            "field_read_hashes": FIELD_HASHES,
            "field_read_row_ok_counts": {
                field: row_count for field in FIELD_HASHES
            },
        },
    )
    _write_json(
        runner,
        _native_runner_payload(
            field=THIRD_FIELD,
            row_count=row_count,
            input_jsons=[str(input_json)],
        ),
    )
    _write_json(previous, _previous_payload(payloadless, runner, row_count=row_count))
    return previous


def _base_args(previous: Path, output: Path, tmp_path: Path) -> list[str]:
    return [
        "--previous-field-json",
        str(previous),
        "--output-json",
        str(output),
        "--canary-output-dir",
        str(tmp_path / "canary"),
    ]


def _fourth_report(
    *,
    source_count: int = 128,
    row_count: int = 513,
    field: str = FOURTH_FIELD,
) -> dict:
    return _native_runner_payload(
        field=field,
        source_count=source_count,
        row_count=row_count,
        input_jsons=["input_0000.json"],
    )


def test_fourth_field_canary_runs_native_gate(tmp_path: Path, monkeypatch):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    output = tmp_path / "fourth.json"

    def fake_run(args, *, input_paths):
        assert args.fourth_field == FOURTH_FIELD
        assert len(input_paths) == 1
        report = _fourth_report()
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            report,
        )
        return report, 9.5

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(_base_args(previous, output, tmp_path))
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is True
    assert result["fourth_field_name"] == FOURTH_FIELD
    assert result["previous_field_input_json_count"] == 1
    assert result["fourth_field_handoff_canary_native_executed"] is True
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["uses_current_wna16_args"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_fourth_field_default_previous_points_to_kernel_side_artifact():
    module = _load_module()

    assert (
        module.DEFAULT_PREVIOUS_FIELD_JSON.name
        == "future_wna16_typed_slot_kernel_variant_third_field_handoff_canary_entry_args_ptr_default.json"
    )
    assert module.DEFAULT_PREVIOUS_FIELD_JSON.exists()


def test_fourth_field_canary_rejects_previous_not_passed(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["passed"] = False
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("previous_passed_mismatch" in item for item in result["failures"])
    assert "fourth_field_handoff_canary_required_but_not_executed" in result["failures"]


def test_fourth_field_canary_rejects_forged_previous_runner_source(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    runner = Path(payload["third_field_underlying_json"])
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["source"] = "forged_runner"
    _write_json(runner, runner_payload)
    payload["third_field_underlying_sha256"] = _sha256(runner)
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("previous_runner_source_mismatch")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_previous_underlying_sha_mismatch(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["third_field_underlying_sha256"] = "0" * 64
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "previous_third_field_underlying_sha256_mismatch" in result["failures"]


def test_fourth_field_canary_rejects_payloadless_sha_mismatch(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["payloadless_execution_sha256"] = "0" * 64
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "previous_payloadless_execution_sha256_mismatch" in result["failures"]


def test_fourth_field_canary_rejects_missing_previous_runner_input_json(
    tmp_path: Path,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    runner = Path(payload["third_field_underlying_json"])
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["input_jsons"] = [str(tmp_path / "missing_input.json")]
    _write_json(runner, runner_payload)
    payload["third_field_underlying_sha256"] = _sha256(runner)
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("previous_runner_input_json_0_missing")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_directory_previous_runner_input_json(
    tmp_path: Path,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    runner = Path(payload["third_field_underlying_json"])
    input_dir = tmp_path / "input_dir"
    input_dir.mkdir()
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["input_jsons"] = [str(input_dir)]
    _write_json(runner, runner_payload)
    payload["third_field_underlying_sha256"] = _sha256(runner)
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("previous_runner_input_json_0_not_file")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_outside_previous_runner_input_json(
    tmp_path: Path,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    runner = Path(payload["third_field_underlying_json"])
    outside_input = tmp_path.parent / "outside_input.json"
    _write_json(outside_input, {"schema_version": 1})
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["input_jsons"] = [str(outside_input)]
    _write_json(runner, runner_payload)
    payload["third_field_underlying_sha256"] = _sha256(runner)
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("previous_runner_input_json_0_outside_allowed_roots")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_previous_field(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    args = module.build_parser().parse_args(
        [
            *_base_args(previous, tmp_path / "fourth.json", tmp_path),
            "--fourth-field",
            THIRD_FIELD,
        ]
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "fourth_field_must_differ_from_previous_fields" in result["failures"]


def test_fourth_field_canary_rejects_non_descriptor_fourth_field(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    args = module.build_parser().parse_args(
        [
            *_base_args(previous, tmp_path / "fourth.json", tmp_path),
            "--fourth-field",
            "aux_metadata_handle",
        ]
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "fourth_field_must_be_descriptor_ptr" in result["failures"]


def test_fourth_field_canary_rejects_payloadless_outside_allowed_roots(
    tmp_path: Path,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    outside = tmp_path.parent / "outside_payloadless.json"
    _write_json(
        outside,
        {
            "passed": True,
            "source_count": 128,
            "row_count": 257,
            "field_read_hashes": FIELD_HASHES,
            "field_read_row_ok_counts": {field: 257 for field in FIELD_HASHES},
        },
    )
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["payloadless_execution_json"] = str(outside)
    payload["payloadless_execution_sha256"] = _sha256(outside)
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith(
            "previous_payloadless_execution_json_outside_allowed_roots"
        )
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_source_count_mismatch(tmp_path: Path, monkeypatch):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _fourth_report(source_count=64)
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "fourth_source_count_invalid" in result["failures"]
    assert "fourth_source_count_previous_mismatch" in result["failures"]


def test_fourth_field_canary_rejects_row_count_mismatch(tmp_path: Path, monkeypatch):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path, row_count=513)

    def fake_run(args, *, input_paths):
        report = _fourth_report(row_count=128)
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "fourth_row_count_previous_mismatch" in result["failures"]
    assert "fourth_single_field_row_count_previous_mismatch" in result["failures"]


def test_fourth_field_canary_rejects_missing_payloadless_fourth_hash(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payloadless = Path(payload["payloadless_execution_json"])
    payloadless_payload = json.loads(payloadless.read_text(encoding="utf-8"))
    payloadless_payload["field_read_hashes"].pop(FOURTH_FIELD)
    _write_json(payloadless, payloadless_payload)
    payload["payloadless_execution_sha256"] = _sha256(payloadless)
    _write_json(previous, payload)

    def fake_run(args, *, input_paths):
        report = _fourth_report()
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "previous_payloadless_default_fourth_field_hash_invalid" in result["failures"]


def test_fourth_field_canary_rejects_previous_failures_not_empty(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["failures"] = ["upstream"]
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "previous_failures_not_empty" in result["failures"]


def test_fourth_field_canary_rejects_all_four_not_ready(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["payloadless_all_four_field_consumer_ready"] = False
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("payloadless_all_four_field_consumer_ready" in item for item in result["failures"])


def test_fourth_field_canary_rejects_fourth_evidence_sha_mismatch(tmp_path: Path):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    payload["payloadless_fourth_field_handoff_evidence_sha256"] = "1" * 64
    payload["payloadless_all_four_field_consumer_fourth_field_sha256"] = "1" * 64
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert (
        "previous_payloadless_fourth_field_handoff_evidence_payloadless_fourth_field_handoff_evidence_sha256_mismatch"
        in result["failures"]
    )


def test_fourth_field_canary_rejects_unsafe_native_flag(tmp_path: Path, monkeypatch):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _fourth_report()
        report["future_wna16_single_field_handoff_canary_passed_to_kernel"] = True
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith(
            "fourth_future_wna16_single_field_handoff_canary_passed_to_kernel_mismatch"
        )
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_unsafe_native_report_top_level(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _fourth_report()
        unsafe_report = dict(report)
        unsafe_report["uses_current_wna16_args"] = True
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            report,
        )
        return unsafe_report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("fourth_uses_current_wna16_args")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_missing_fourth_underlying_json(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        return _fourth_report(), 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert "fourth_field_underlying_json_missing" in result["failures"]


def test_fourth_field_canary_rejects_forged_fourth_underlying_identity(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _fourth_report()
        persisted = dict(report)
        persisted["future_wna16_single_field_handoff_canary_mode"] = "forged_mode"
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith(
            "fourth_field_underlying_future_wna16_single_field_handoff_canary_mode_report_mismatch"
        )
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_forged_fourth_underlying_top_level_kernel_arg(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _fourth_report()
        persisted = dict(report)
        persisted["kernel_arg_pass_allowed"] = True
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("fourth_field_underlying_kernel_arg_pass_allowed")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_forged_fourth_underlying_tpot_claim(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _fourth_report()
        persisted = dict(report)
        persisted["measures_tpot"] = True
        _write_json(
            Path(args.canary_output_dir) / "fourth_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_fourth_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("fourth_field_underlying_measures_tpot")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_previous_underlying_top_level_current_wna16(
    tmp_path: Path,
):
    module = _load_module()
    previous = _seed_previous_gate(tmp_path)
    payload = json.loads(previous.read_text(encoding="utf-8"))
    runner = Path(payload["third_field_underlying_json"])
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["uses_current_wna16_args"] = True
    _write_json(runner, runner_payload)
    payload["third_field_underlying_sha256"] = _sha256(runner)
    _write_json(previous, payload)

    args = module.build_parser().parse_args(
        _base_args(previous, tmp_path / "fourth.json", tmp_path)
    )
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("previous_runner_uses_current_wna16_args")
        for item in result["failures"]
    )


def test_fourth_field_canary_rejects_bad_previous_json(tmp_path: Path):
    module = _load_module()
    previous = tmp_path / "previous.json"
    output = tmp_path / "fourth.json"
    previous.write_text("{bad json\n", encoding="utf-8")

    args = module.build_parser().parse_args(_base_args(previous, output, tmp_path))
    result = module.run_fourth_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("previous_field_json_load_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False
