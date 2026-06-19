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
        / "run_future_wna16_typed_slot_kernel_timing_stub.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_timing_stub",
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


def _entrypoint_payload(*, row_count: int = 257, source_count: int = 128) -> dict:
    evidence_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_fourth_field_evidence.json"
    )
    evidence_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    kernel_side_evidence_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_kernel_side_typed_path_evidence.json"
    )
    kernel_side_evidence_sha = hashlib.sha256(
        kernel_side_evidence_path.read_bytes()
    ).hexdigest()
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_entrypoint",
        "entrypoint_name": "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1",
        "entrypoint_mode": "readonly_independent_typed_slot_kernel_variant_entrypoint",
        "entrypoint_source": "premap_wna16_typed_slot_benchmark_harness_v1",
        "passed": True,
        "typed_slot_entrypoint_ready": True,
        "entrypoint_accepts_typed_slot": True,
        "entrypoint_consumes_handle_fields": True,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "measures_latency": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": "implement_future_wna16_typed_slot_kernel_timing_stub",
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
        "entry_args_ptr_required": True,
        "entry_args_ptr_sweep_json": "outputs/reports/premap_kernel_consumer/sweep.json",
        "entry_args_ptr_sweep_sha256": "4" * 64,
        "entry_args_ptr_sweep_check_json": (
            "outputs/reports/premap_kernel_consumer/sweep.check.json"
        ),
        "entry_args_ptr_sweep_check_sha256": "5" * 64,
        "entry_args_ptr_sweep_row_count": row_count,
        "entry_args_ptr_sweep_check_row_count": row_count,
        "entry_args_ptr_sweep_device": 1,
        "entry_args_ptr_sweep_window_size": 512,
        "entry_args_ptr_sweep_mirror_fields": list(HANDLE_FIELDS),
        "entry_args_ptr_sweep_require_kernel_arg_packet_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_abi": True,
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi": True,
    }


def _canary_report(*, row_count: int = 257, source_count: int = 128) -> dict:
    return {
        "passed": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_wna16_side_consumer_variant_execution": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "wna16_side_consumer_variant_execution_all_handle_fields_read": True,
        "selected_source_count": source_count,
        "merged_row_count": row_count,
        "dispatch_active_rows": row_count,
        "future_wna16_kernel_side_consumer_execution_row_count": row_count,
        "future_wna16_kernel_side_consumer_execution_row_ok_count": row_count,
        "future_wna16_kernel_side_consumer_execution_payload_bytes": 0,
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed": False,
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed": False,
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel": False,
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args": False,
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible": False,
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation": False,
        "future_wna16_kernel_side_consumer_execution_reuses_current_wna16_arg_slot": False,
        "wna16_side_consumer_variant_execution_row_count": row_count,
        "wna16_side_consumer_variant_execution_row_ok_count": row_count,
        "wna16_side_consumer_variant_execution_payload_bytes": 0,
        "wna16_side_consumer_variant_execution_passed_to_kernel": False,
        "wna16_side_consumer_variant_execution_changes_kernel_launch_args": False,
        "wna16_side_consumer_variant_execution_current_wna16_arg_compatible": False,
        "wna16_side_consumer_variant_execution_requires_wna16_arg_reinterpretation": False,
        "wna16_side_consumer_variant_execution_reuses_current_wna16_arg_slot": False,
    }


def test_future_wna16_typed_slot_timing_stub_accepts_entrypoint(tmp_path: Path):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    output = tmp_path / "timing.json"
    _write_json(entrypoint, _entrypoint_payload())

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is True
    assert result["timing_stub_ready"] is True
    assert result["native_stub_requested"] is False
    assert result["native_stub_executed"] is False
    assert result["measures_native_stub_host_wall_time"] is False
    assert result["measures_tpot"] is False
    assert result["wna16_benchmark_ready"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["fourth_field_handoff_ready"] is True
    evidence_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_fourth_field_evidence.json"
    )
    evidence_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    assert result["fourth_field_handoff_evidence_path"] == str(evidence_path)
    assert result["fourth_field_handoff_evidence_sha256"] == evidence_sha
    assert result["fourth_field_handoff_source_count"] == 128
    assert result["fourth_field_handoff_row_count"] == 257
    assert result["fourth_field_handoff_row_ok_count"] == 257
    assert result["fourth_field_handoff_field_read_hash"] == "3132333435363738"
    assert result["fourth_field_handoff_runner_hash"] == "8182838485868788"
    assert result["all_four_field_consumer_ready"] is True
    assert result["all_four_field_consumer_fields_read"] is True
    assert result["all_four_field_consumer_hashes_valid"] is True
    assert result["all_four_field_consumer_source_count"] == 128
    assert result["all_four_field_consumer_row_count"] == 257
    assert result["all_four_field_consumer_row_ok_count"] == 257
    assert result["all_four_field_consumer_fourth_field_path_label"] == str(
        evidence_path
    )
    assert result["all_four_field_consumer_fourth_field_sha256"] == evidence_sha
    assert result["future_wna16_kernel_side_typed_consumer_path_ready"] is True
    assert result["future_wna16_kernel_side_typed_consumer_path_source_count"] == 128
    assert result["future_wna16_kernel_side_typed_consumer_path_row_count"] == 257
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_future_wna16_typed_slot_timing_stub_defaults_to_kernel_side_path_entrypoint():
    module = _load_module()

    args = module.build_parser().parse_args([])
    default_path = Path(args.entrypoint_json)
    default_output = Path(args.output_json)

    assert (
        default_path.name
        == "future_wna16_typed_slot_kernel_variant_entrypoint_entry_args_ptr_v1.json"
    )
    assert (
        default_output.name
        == "future_wna16_typed_slot_kernel_timing_stub_entry_args_ptr_native_v1.json"
    )
    assert "premap_kernel_consumer" in default_path.parts


def test_future_wna16_typed_slot_timing_stub_rejects_missing_kernel_side_path(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_ready"] = False
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any(
        "future_wna16_kernel_side_typed_consumer_path_ready" in item
        for item in result["failures"]
    )


def test_future_wna16_typed_slot_timing_stub_rejects_kernel_side_path_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_row_count"] = 1
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_kernel_side_typed_path_row_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_timing_stub_rejects_kernel_side_evidence_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_evidence_sha256"] = "0" * 64
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert (
        "entrypoint_kernel_side_typed_path_evidence_sha_mismatch"
        in result["failures"]
    )


def test_future_wna16_typed_slot_timing_stub_rejects_kernel_side_evidence_manifest_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"] = (
        "0" * 64
    )
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert (
        "entrypoint_kernel_side_typed_path_evidence_selected_manifest_mismatch"
        in result["failures"]
    )


def test_future_wna16_typed_slot_timing_stub_rejects_entrypoint_not_ready(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["typed_slot_entrypoint_ready"] = False
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("typed_slot_entrypoint_ready" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_rejects_current_arg_pass(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["passes_current_wna16_args"] = True
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("passes_current_wna16_args" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_rejects_fourth_source_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_source_count"] = 129
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_source_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_timing_stub_rejects_missing_fourth_row(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    del payload["fourth_field_handoff_row_count"]
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_row_count_invalid" in result["failures"]


def test_future_wna16_typed_slot_timing_stub_rejects_fourth_hash_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_field_read_hash"] = "7172737475767778"
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_descriptor_hash_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_fourth_row_ok_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_row_ok_count"] = 256
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_row_ok_count_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_bad_runner_hash(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_runner_hash"] = "0"
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_runner_hash_invalid" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_missing_fourth_evidence_path(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload.pop("fourth_field_handoff_evidence_path")
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_evidence_path_missing" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_invalid_fourth_evidence_sha(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_evidence_sha256"] = "not-a-sha"
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_evidence_sha_invalid" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_forged_fourth_evidence_binding(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    forged_path = tmp_path / "missing_fourth.json"
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_evidence_path"] = str(forged_path)
    payload["fourth_field_handoff_evidence_sha256"] = "8" * 64
    payload["all_four_field_consumer_fourth_field_path_label"] = str(forged_path)
    payload["all_four_field_consumer_fourth_field_sha256"] = "8" * 64
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_evidence_path_not_found" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_fourth_evidence_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    evidence = tmp_path / "fourth.json"
    evidence.write_text('{"passed": true}\n', encoding="utf-8")
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_evidence_path"] = str(evidence)
    payload["fourth_field_handoff_evidence_sha256"] = "8" * 64
    payload["all_four_field_consumer_fourth_field_path_label"] = str(evidence)
    payload["all_four_field_consumer_fourth_field_sha256"] = "8" * 64
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_fourth_field_handoff_evidence_sha_mismatch" in result[
        "failures"
    ]


def test_fourth_evidence_allows_bootstrap_payloadless_root_sha_drift(
    tmp_path: Path,
):
    module = _load_module()
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    root = json.loads(
        (fixture_dir / "future_wna16_payloadless_root_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    root["payloadless_execution_provenance_mode"] = "bootstrap_cycle_breaker_root"
    root["payloadless_execution_cycle_breaker_root"] = True
    root_path = tmp_path / "payloadless_root.json"
    _write_json(root_path, root)
    fourth = json.loads(
        (fixture_dir / "future_wna16_fourth_field_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    fourth["payloadless_execution_json"] = str(root_path)
    fourth["payloadless_execution_sha256"] = "0" * 64

    failures = module._check_fourth_evidence(  # noqa: SLF001
        fourth,
        entrypoint=_entrypoint_payload(),
    )

    assert "fourth_evidence_payloadless_root_sha_mismatch" not in failures
    assert failures == []


def test_fourth_evidence_rejects_non_bootstrap_payloadless_root_sha_drift(
    tmp_path: Path,
):
    module = _load_module()
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    root = json.loads(
        (fixture_dir / "future_wna16_payloadless_root_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    root_path = tmp_path / "payloadless_root.json"
    _write_json(root_path, root)
    fourth = json.loads(
        (fixture_dir / "future_wna16_fourth_field_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    fourth["payloadless_execution_json"] = str(root_path)
    fourth["payloadless_execution_sha256"] = "0" * 64

    failures = module._check_fourth_evidence(  # noqa: SLF001
        fourth,
        entrypoint=_entrypoint_payload(),
    )

    assert "fourth_evidence_payloadless_root_sha_mismatch" in failures


def test_fourth_evidence_rejects_bootstrap_payloadless_root_with_payload(
    tmp_path: Path,
):
    module = _load_module()
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    root = json.loads(
        (fixture_dir / "future_wna16_payloadless_root_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    root["payloadless_execution_provenance_mode"] = "bootstrap_cycle_breaker_root"
    root["payloadless_execution_cycle_breaker_root"] = True
    root["payload_bytes"] = 1
    root_path = tmp_path / "payloadless_root.json"
    _write_json(root_path, root)
    fourth = json.loads(
        (fixture_dir / "future_wna16_fourth_field_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    fourth["payloadless_execution_json"] = str(root_path)
    fourth["payloadless_execution_sha256"] = "0" * 64

    failures = module._check_fourth_evidence(  # noqa: SLF001
        fourth,
        entrypoint=_entrypoint_payload(),
    )

    assert "fourth_evidence_payloadless_root_sha_mismatch" not in failures
    assert "fourth_evidence_payloadless_root_payload_bytes_unsafe_nonzero" in failures


def test_future_wna16_typed_slot_timing_stub_rejects_unrelated_existing_evidence_file(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_text('{"passed": true}\n', encoding="utf-8")
    unrelated_sha = hashlib.sha256(unrelated.read_bytes()).hexdigest()
    payload = _entrypoint_payload()
    payload["fourth_field_handoff_evidence_path"] = str(unrelated)
    payload["fourth_field_handoff_evidence_sha256"] = unrelated_sha
    payload["all_four_field_consumer_fourth_field_path_label"] = str(unrelated)
    payload["all_four_field_consumer_fourth_field_sha256"] = unrelated_sha
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("fourth_evidence_artifact_kind" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_rejects_fourth_evidence_tpot_semantics(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    evidence = tmp_path / "fourth.json"
    source_evidence = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_fourth_field_evidence.json"
    )
    payload = json.loads(source_evidence.read_text(encoding="utf-8"))
    payload["measures_tpot"] = True
    _write_json(evidence, payload)
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    entrypoint_payload = _entrypoint_payload()
    entrypoint_payload["fourth_field_handoff_evidence_path"] = str(evidence)
    entrypoint_payload["fourth_field_handoff_evidence_sha256"] = evidence_sha
    entrypoint_payload["all_four_field_consumer_fourth_field_path_label"] = str(
        evidence
    )
    entrypoint_payload["all_four_field_consumer_fourth_field_sha256"] = evidence_sha
    _write_json(entrypoint, entrypoint_payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("fourth_evidence_measures_tpot" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_rejects_fourth_evidence_failures(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    evidence = tmp_path / "fourth.json"
    source_evidence = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_fourth_field_evidence.json"
    )
    payload = json.loads(source_evidence.read_text(encoding="utf-8"))
    payload["failures"] = ["synthetic_failure"]
    _write_json(evidence, payload)
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    entrypoint_payload = _entrypoint_payload()
    entrypoint_payload["fourth_field_handoff_evidence_path"] = str(evidence)
    entrypoint_payload["fourth_field_handoff_evidence_sha256"] = evidence_sha
    entrypoint_payload["all_four_field_consumer_fourth_field_path_label"] = str(
        evidence
    )
    entrypoint_payload["all_four_field_consumer_fourth_field_sha256"] = evidence_sha
    _write_json(entrypoint, entrypoint_payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "fourth_evidence_failures_not_empty" in result["failures"]


def test_future_wna16_typed_slot_timing_stub_rejects_missing_all_four_ready(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["all_four_field_consumer_ready"] = False
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("all_four_field_consumer_ready" in item for item in result["failures"])


def test_future_wna16_typed_slot_timing_stub_rejects_all_four_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["all_four_field_consumer_row_count"] = 256
    payload["all_four_field_consumer_row_ok_count"] = 256
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_all_four_field_consumer_row_count_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_all_four_path_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["all_four_field_consumer_fourth_field_path_label"] = "wrong.json"
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_all_four_field_consumer_fourth_path_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_rejects_all_four_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    payload = _entrypoint_payload()
    payload["all_four_field_consumer_fourth_field_sha256"] = "7" * 64
    _write_json(entrypoint, payload)

    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert "entrypoint_all_four_field_consumer_fourth_sha_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_timing_stub_runs_fake_native_canary(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    _write_json(entrypoint, _entrypoint_payload())
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})

    def fake_run_canary(args):
        assert str(args.runner_json) == str(runner)
        assert args.require_future_wna16_kernel_side_consumer_execution is True
        assert args.require_wna16_side_consumer_variant_execution is True
        return _canary_report()

    monkeypatch.setattr(module.canary_runner, "run_canary", fake_run_canary)
    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--runner-json",
            str(runner),
            "--run-native-stub",
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is True
    assert result["native_stub_requested"] is True
    assert result["native_stub_executed"] is True
    assert result["native_stub_passed"] is True
    assert result["native_stub_host_wall_ms"] is not None
    assert result["measures_native_stub_host_wall_time"] is True
    assert result["measures_tpot"] is False


def test_future_wna16_typed_slot_timing_stub_rejects_native_canary_arg_pass(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    entrypoint = tmp_path / "entrypoint.json"
    runner = tmp_path / "runner.json"
    _write_json(entrypoint, _entrypoint_payload())
    _write_json(runner, {"online_prelaunch_input_jsons": [str(tmp_path / "input.json")]})

    def fake_run_canary(args):
        report = _canary_report()
        report[
            "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"
        ] = True
        return report

    monkeypatch.setattr(module.canary_runner, "run_canary", fake_run_canary)
    args = module.build_parser().parse_args(
        [
            "--entrypoint-json",
            str(entrypoint),
            "--runner-json",
            str(runner),
            "--run-native-stub",
            "--output-json",
            str(tmp_path / "timing.json"),
        ]
    )
    result = module.run_timing_stub(args)

    assert result["passed"] is False
    assert any("kernel_arg_pass_allowed" in item for item in result["failures"])
