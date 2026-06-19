from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


FIRST_FIELD = "scale_metadata_handle"
SECOND_FIELD = "aux_metadata_handle"
FIELD_KINDS = {
    "descriptor_ptr": 1,
    "packed_weight_descriptor": 2,
    "scale_metadata_handle": 3,
    "aux_metadata_handle": 4,
}
FOURTH_EVIDENCE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "future_wna16_fourth_field_evidence.json"
)
KERNEL_SIDE_EVIDENCE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "future_wna16_kernel_side_typed_path_evidence.json"
)


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary",
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


def _native_runner_payload(
    *,
    field: str,
    source_count: int = 128,
    row_count: int = 257,
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
            "aaabe281160d022" if field == SECOND_FIELD else "5152535455565758"
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


def _first_field_payload(
    payloadless_json: Path,
    runner_json: Path,
    *,
    source_count: int = 128,
    row_count: int = 257,
) -> dict:
    fourth_evidence_sha = _sha256(FOURTH_EVIDENCE_PATH)
    kernel_side_evidence_sha = _sha256(KERNEL_SIDE_EVIDENCE_PATH)
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary",
        "failures": [],
        "one_field_handoff_canary_name": (
            "premap_future_wna16_typed_slot_one_field_handoff_canary_v1"
        ),
        "one_field_handoff_canary_mode": (
            "readonly_future_wna16_typed_slot_one_field_handoff_canary"
        ),
        "passed": True,
        "one_field_handoff_canary_ready": True,
        "one_field_handoff_canary_native_requested": True,
        "one_field_handoff_canary_native_executed": True,
        "one_field_handoff_canary_native_passed": True,
        "one_field_handoff_field_name": FIRST_FIELD,
        "one_field_handoff_field_read_hash": "5152535455565758",
        "one_field_handoff_canary_runner_hash": "5152535455565758",
        "one_field_handoff_live_enabled": False,
        "one_field_handoff_block_reason": "one_field_handoff_live_disabled",
        "payloadless_execution_gate_ready": True,
        "payloadless_execution_json": str(payloadless_json),
        "payloadless_execution_sha256": _sha256(payloadless_json),
        "payloadless_fourth_field_handoff_evidence_path": str(FOURTH_EVIDENCE_PATH),
        "payloadless_fourth_field_handoff_evidence_sha256": fourth_evidence_sha,
        "payloadless_all_four_field_consumer_ready": True,
        "payloadless_all_four_field_consumer_fields_read": True,
        "payloadless_all_four_field_consumer_hashes_valid": True,
        "payloadless_all_four_field_consumer_source_count": source_count,
        "payloadless_all_four_field_consumer_row_count": row_count,
        "payloadless_all_four_field_consumer_row_ok_count": row_count,
        "payloadless_all_four_field_consumer_fourth_field_path_label": str(
            FOURTH_EVIDENCE_PATH
        ),
        "payloadless_all_four_field_consumer_fourth_field_sha256": fourth_evidence_sha,
        "payloadless_future_wna16_kernel_side_typed_consumer_path_ready": True,
        "payloadless_future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        "payloadless_future_wna16_kernel_side_typed_consumer_path_evidence_path": str(
            KERNEL_SIDE_EVIDENCE_PATH
        ),
        "payloadless_future_wna16_kernel_side_typed_consumer_path_evidence_sha256": (
            kernel_side_evidence_sha
        ),
        "payloadless_future_wna16_kernel_side_typed_consumer_path_source_count": (
            source_count
        ),
        "payloadless_future_wna16_kernel_side_typed_consumer_path_input_json_count": (
            source_count
        ),
        "payloadless_future_wna16_kernel_side_typed_consumer_path_row_count": row_count,
        "payloadless_future_wna16_kernel_side_typed_consumer_path_row_ok_count": (
            row_count
        ),
        "payloadless_future_wna16_kernel_side_typed_consumer_path_all_four_sha256": (
            "7" * 64
        ),
        "payloadless_future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": (
            "6" * 64
        ),
        "canary_runner_json": str(runner_json),
        "canary_runner_sha256": _sha256(runner_json),
        "payloadless_field_read_hashes": {
            "descriptor_ptr": "3132333435363738",
            "packed_weight_descriptor": "4142434445464748",
            "scale_metadata_handle": "5152535455565758",
            "aux_metadata_handle": "6162636465666768",
        },
        "payloadless_field_read_row_ok_counts": {
            "descriptor_ptr": row_count,
            "packed_weight_descriptor": row_count,
            "scale_metadata_handle": row_count,
            "aux_metadata_handle": row_count,
        },
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_second_field_handoff_canary"
        ),
        "source_count": source_count,
        "row_count": row_count,
        "row_ok_count": row_count,
        "payloadless_row_count": row_count,
        "one_field_handoff_canary_runner_row_count": row_count,
        "one_field_handoff_canary_runner_row_ok_count": row_count,
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


def _seed_first_gate(tmp_path: Path, *, row_count: int = 257) -> tuple[Path, Path]:
    payloadless = tmp_path / "payloadless.json"
    first = tmp_path / "first.json"
    runner = tmp_path / "first_runner.json"
    input_json = tmp_path / "input_0000.json"
    _write_json(input_json, {"schema_version": 1, "row_count": row_count})
    _write_json(
        payloadless,
        {
            "passed": True,
            "source_count": 128,
            "row_count": row_count,
            "field_read_hashes": {
                "descriptor_ptr": "3132333435363738",
                "packed_weight_descriptor": "4142434445464748",
                "scale_metadata_handle": "5152535455565758",
                "aux_metadata_handle": "6162636465666768",
            },
            "field_read_row_ok_counts": {
                "descriptor_ptr": row_count,
                "packed_weight_descriptor": row_count,
                "scale_metadata_handle": row_count,
                "aux_metadata_handle": row_count,
            },
        },
    )
    _write_json(
        runner,
        _native_runner_payload(
            field=FIRST_FIELD,
            row_count=row_count,
            input_jsons=[str(input_json)],
        ),
    )
    _write_json(first, _first_field_payload(payloadless, runner, row_count=row_count))
    return first, payloadless


def _base_args(first: Path, output: Path, tmp_path: Path) -> list[str]:
    return [
        "--first-field-json",
        str(first),
        "--output-json",
        str(output),
        "--canary-output-dir",
        str(tmp_path / "canary"),
    ]


def _second_report(
    *,
    source_count: int = 128,
    row_count: int = 257,
    field: str = SECOND_FIELD,
) -> dict:
    return _native_runner_payload(
        field=field,
        source_count=source_count,
        row_count=row_count,
        input_jsons=["input_0000.json"],
    )


def test_second_field_canary_runs_native_gate(tmp_path: Path, monkeypatch):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    output = tmp_path / "second.json"

    def fake_run(args, *, input_paths):
        assert args.second_field == SECOND_FIELD
        assert len(input_paths) == 1
        report = _second_report()
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            report,
        )
        return report, 9.5

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, output, tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is True
    assert result["first_field_name"] == FIRST_FIELD
    assert result["second_field_name"] == SECOND_FIELD
    assert result["first_field_input_json_count"] == 1
    assert result["second_field_handoff_canary_native_executed"] is True
    assert result["second_field_handoff_live_enabled"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["uses_current_wna16_args"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_second_field_canary_rejects_first_gate_not_passed(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["passed"] = False
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("first_passed_mismatch" in item for item in result["failures"])
    assert "second_field_handoff_canary_required_but_not_executed" in result["failures"]


def test_second_field_canary_rejects_missing_first_runner(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload.pop("canary_runner_json")
    payload.pop("canary_runner_sha256")
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "first_canary_runner_json_missing" in result["failures"]


def test_second_field_canary_rejects_forged_first_runner_source(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    runner = Path(payload["canary_runner_json"])
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["source"] = "forged_runner"
    _write_json(runner, runner_payload)
    payload["canary_runner_sha256"] = _sha256(runner)
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("first_runner_source_mismatch") for item in result["failures"]
    )


def test_second_field_canary_rejects_native_opt_out(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    args = module.build_parser().parse_args(
        [
            *_base_args(first, tmp_path / "second.json", tmp_path),
            "--no-run-native-canary",
            "--no-require-native-canary",
        ]
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "run_native_canary_must_remain_enabled_for_lab_gate" in result["failures"]
    assert "require_native_canary_must_remain_enabled_for_lab_gate" in result["failures"]


def test_second_field_canary_rejects_same_field(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    args = module.build_parser().parse_args(
        [
            *_base_args(first, tmp_path / "second.json", tmp_path),
            "--second-field",
            FIRST_FIELD,
        ]
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "second_field_must_differ_from_first_field" in result["failures"]


def test_second_field_canary_rejects_source_count_mismatch(tmp_path: Path, monkeypatch):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report(source_count=64)
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "second_source_count_invalid" in result["failures"]
    assert "second_source_count_first_mismatch" in result["failures"]


def test_second_field_canary_rejects_row_count_mismatch(tmp_path: Path, monkeypatch):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path, row_count=257)

    def fake_run(args, *, input_paths):
        report = _second_report(row_count=128)
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "second_row_count_first_mismatch" in result["failures"]
    assert "second_single_field_row_count_first_mismatch" in result["failures"]


def test_second_field_canary_rejects_payloadless_hash_missing(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["payloadless_field_read_hashes"].pop(SECOND_FIELD)
    _write_json(first, payload)

    def fake_run(args, *, input_paths):
        report = _second_report()
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "first_payloadless_field_read_hashes_artifact_mismatch" in result["failures"]


def test_second_field_canary_rejects_forged_first_runner_top_level_current_wna16(
    tmp_path: Path,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    runner = Path(payload["canary_runner_json"])
    runner_payload = json.loads(runner.read_text(encoding="utf-8"))
    runner_payload["uses_current_wna16_args"] = True
    _write_json(runner, runner_payload)
    payload["canary_runner_sha256"] = _sha256(runner)
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("first_runner_uses_current_wna16_args")
        for item in result["failures"]
    )


def test_second_field_canary_rejects_first_failures_not_empty(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["failures"] = ["upstream"]
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "first_failures_not_empty" in result["failures"]


def test_second_field_canary_rejects_all_four_not_ready(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["payloadless_all_four_field_consumer_ready"] = False
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("payloadless_all_four_field_consumer_ready" in item for item in result["failures"])


def test_second_field_canary_defaults_to_kernel_side_one_field_artifact():
    module = _load_module()
    assert (
        "future_wna16_typed_slot_kernel_variant_one_field_handoff_canary_kernel_side_path_v1.json"
        in str(module.DEFAULT_FIRST_FIELD_JSON)
    )
    default_path = Path(module.DEFAULT_FIRST_FIELD_JSON)
    assert default_path.exists()
    payload = json.loads(default_path.read_text(encoding="utf-8"))
    assert payload["payloadless_future_wna16_kernel_side_typed_consumer_path_ready"] is True
    assert payload["one_field_handoff_canary_native_executed"] is True


def test_second_field_canary_rejects_payloadless_kernel_side_row_drift(
    tmp_path: Path,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path, row_count=257)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["payloadless_future_wna16_kernel_side_typed_consumer_path_row_count"] = 128
    payload["payloadless_future_wna16_kernel_side_typed_consumer_path_row_ok_count"] = 128
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "first_payloadless_kernel_side_row_count_mismatch" in result["failures"]


def test_second_field_canary_rejects_payloadless_kernel_side_evidence_sha_drift(
    tmp_path: Path,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["payloadless_future_wna16_kernel_side_typed_consumer_path_evidence_sha256"] = (
        "8" * 64
    )
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "first_payloadless_kernel_side_evidence_sha_mismatch" in result["failures"]


def test_second_field_canary_rejects_fourth_evidence_sha_mismatch(tmp_path: Path):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["payloadless_fourth_field_handoff_evidence_sha256"] = "1" * 64
    payload["payloadless_all_four_field_consumer_fourth_field_sha256"] = "1" * 64
    _write_json(first, payload)

    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "first_payloadless_fourth_field_handoff_evidence_payloadless_fourth_field_handoff_evidence_sha256_mismatch" in result["failures"]


def test_second_field_canary_rejects_unsafe_native_flag(tmp_path: Path, monkeypatch):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report()
        report["future_wna16_single_field_handoff_canary_passed_to_kernel"] = True
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            report,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith(
            "second_future_wna16_single_field_handoff_canary_passed_to_kernel_mismatch"
        )
        for item in result["failures"]
    )


def test_second_field_canary_rejects_missing_second_underlying_json(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        return _second_report(), 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        [
            "--first-field-json",
            str(first),
            "--output-json",
            str(tmp_path / "second.json"),
            "--canary-output-dir",
            str(tmp_path / "canary"),
        ]
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert "second_field_underlying_json_missing" in result["failures"]


def test_second_field_canary_rejects_forged_second_underlying_identity(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report()
        persisted = dict(report)
        persisted["future_wna16_single_field_handoff_canary_mode"] = "forged_mode"
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith(
            "second_field_underlying_future_wna16_single_field_handoff_canary_mode_report_mismatch"
        )
        for item in result["failures"]
    )


def test_second_field_canary_rejects_forged_second_underlying_input_jsons(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report()
        persisted = dict(report)
        persisted["input_jsons"] = ["forged_input.json"]
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("second_field_underlying_input_jsons_report_mismatch")
        for item in result["failures"]
    )


def test_second_field_canary_rejects_forged_second_underlying_unsafe_field(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report()
        persisted = dict(report)
        persisted["future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"] = True
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith(
            "second_field_underlying_future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"
        )
        for item in result["failures"]
    )


def test_second_field_canary_rejects_unsafe_native_report_top_level(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report()
        unsafe_report = dict(report)
        unsafe_report["uses_current_wna16_args"] = True
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            report,
        )
        return unsafe_report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("second_uses_current_wna16_args")
        for item in result["failures"]
    )


def test_second_field_canary_rejects_forged_second_underlying_tpot_claim(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    first, _ = _seed_first_gate(tmp_path)

    def fake_run(args, *, input_paths):
        report = _second_report()
        persisted = dict(report)
        persisted["measures_tpot"] = True
        _write_json(
            Path(args.canary_output_dir) / "second_field_native_canary_runner.json",
            persisted,
        )
        return report, 7.0

    monkeypatch.setattr(module, "_run_second_field_native", fake_run)
    args = module.build_parser().parse_args(
        _base_args(first, tmp_path / "second.json", tmp_path)
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("second_field_underlying_measures_tpot")
        for item in result["failures"]
    )


def test_second_field_canary_writes_failure_for_bad_first_json(tmp_path: Path):
    module = _load_module()
    first = tmp_path / "first.json"
    output = tmp_path / "second.json"
    first.write_text("{bad json\n", encoding="utf-8")

    args = module.build_parser().parse_args(
        [
            "--first-field-json",
            str(first),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_second_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("first_field_json_load_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False
