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
        / "run_future_wna16_typed_slot_kernel_variant_entrypoint.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_entrypoint",
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


def _harness_payload(*, row_count: int = 257, source_count: int = 128) -> dict:
    kernel_side_evidence_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "future_wna16_kernel_side_typed_path_evidence.json"
    )
    kernel_side_evidence_sha = _sha256(kernel_side_evidence_path)
    return {
        "artifact_kind": "wna16_typed_slot_benchmark_harness",
        "harness_name": "premap_wna16_typed_slot_benchmark_harness_v1",
        "harness_mode": "readonly_future_wna16_typed_slot_benchmark_harness",
        "benchmark_harness_kind": "future_typed_slot_consumer_harness",
        "passed": True,
        "benchmark_harness_ready": True,
        "wna16_kernel_side_execution_ready": True,
        "wna16_benchmark_ready": False,
        "measures_latency": False,
        "current_wna16_arg_pass": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "explicit_typed_abi_slot": True,
        "reuses_current_wna16_arg_slot": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_entrypoint"
        ),
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
        "fourth_field_handoff_evidence_path": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v1.json"
        ),
        "fourth_field_handoff_evidence_sha256": "8" * 64,
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
        "all_four_field_consumer_fourth_field_path_label": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v1.json"
        ),
        "all_four_field_consumer_fourth_field_sha256": "8" * 64,
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


def test_future_wna16_typed_slot_entrypoint_accepts_harness(tmp_path: Path):
    module = _load_module()
    harness = tmp_path / "harness.json"
    output = tmp_path / "entrypoint.json"
    _write_json(harness, _harness_payload())

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is True
    assert result["typed_slot_entrypoint_ready"] is True
    assert result["entrypoint_accepts_typed_slot"] is True
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["wna16_benchmark_ready"] is False
    assert result["measures_latency"] is False
    assert result["row_count"] == 257
    assert result["fourth_field_handoff_ready"] is True
    assert result["fourth_field_handoff_evidence_path"] == (
        "outputs/reports/premap_kernel_consumer/"
        "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v1.json"
    )
    assert result["fourth_field_handoff_source_count"] == 128
    assert result["fourth_field_handoff_row_count"] == 257
    assert result["fourth_field_handoff_field_read_hash"] == "3132333435363738"
    assert result["all_four_field_consumer_ready"] is True
    assert result["all_four_field_consumer_source_count"] == 128
    assert result["all_four_field_consumer_row_count"] == 257
    assert result["future_wna16_kernel_side_typed_consumer_path_ready"] is True
    assert result["future_wna16_kernel_side_typed_consumer_path_source_count"] == 128
    assert result["future_wna16_kernel_side_typed_consumer_path_row_count"] == 257
    assert result["next_runtime_stage"] == (
        "implement_future_wna16_typed_slot_kernel_timing_stub"
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_future_wna16_typed_slot_entrypoint_defaults_to_four_field_harness():
    module = _load_module()

    args = module.build_parser().parse_args([])
    default_path = Path(args.harness_json)
    default_output = Path(args.output_json)

    assert (
        default_path.name
        == "wna16_typed_slot_benchmark_harness_entry_args_ptr_preflight_v1.json"
    )
    assert (
        default_output.name
        == "future_wna16_typed_slot_kernel_variant_entrypoint_entry_args_ptr_v1.json"
    )
    assert "premap_kernel_consumer" in default_path.parts


def test_future_wna16_typed_slot_entrypoint_rejects_missing_kernel_side_path(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_ready"] = False
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert any(
        "future_wna16_kernel_side_typed_consumer_path_ready" in item
        for item in result["failures"]
    )


def test_future_wna16_typed_slot_entrypoint_rejects_kernel_side_path_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_row_count"] = 1
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_kernel_side_typed_path_row_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_kernel_side_evidence_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_evidence_sha256"] = "0" * 64
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_kernel_side_typed_path_evidence_sha_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_kernel_side_evidence_manifest_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256"] = (
        "0" * 64
    )
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert (
        "harness_kernel_side_typed_path_evidence_selected_manifest_mismatch"
        in result["failures"]
    )


def test_future_wna16_typed_slot_entrypoint_rejects_harness_not_ready(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["benchmark_harness_ready"] = False
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert any("benchmark_harness_ready" in item for item in result["failures"])
    assert result["typed_slot_entrypoint_ready"] is False


def test_future_wna16_typed_slot_entrypoint_rejects_current_arg_pass(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["current_wna16_arg_pass"] = True
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert any("current_wna16_arg_pass" in item for item in result["failures"])
    assert result["passes_current_wna16_args"] is False


def test_future_wna16_typed_slot_entrypoint_rejects_wrong_harness_identity(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["harness_name"] = "wrong"
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert any("harness_name" in item for item in result["failures"])


def test_future_wna16_typed_slot_entrypoint_rejects_extra_field_maps(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["field_read_row_ok_counts"]["current_wna16_arg_ptr"] = 257
    payload["field_read_hashes"]["current_wna16_arg_ptr"] = "7172737475767778"
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_field_read_row_ok_counts_keys_mismatch" in result["failures"]
    assert "harness_field_read_hashes_keys_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_field_count_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload(row_count=257)
    payload["field_read_row_ok_counts"]["aux_metadata_handle"] = 256
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_aux_metadata_handle_read_row_ok_count_mismatch" in result[
        "failures"
    ]


def test_future_wna16_typed_slot_entrypoint_rejects_fourth_source_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["fourth_field_handoff_source_count"] = 129
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_fourth_field_handoff_source_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_missing_fourth_source(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    del payload["fourth_field_handoff_source_count"]
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_fourth_field_handoff_source_count_invalid" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_missing_all_four_ready(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["all_four_field_consumer_ready"] = False
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert any("all_four_field_consumer_ready" in item for item in result["failures"])


def test_future_wna16_typed_slot_entrypoint_rejects_all_four_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["all_four_field_consumer_row_count"] = 256
    payload["all_four_field_consumer_row_ok_count"] = 256
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_all_four_field_consumer_row_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_all_four_invalid_sha(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["all_four_field_consumer_fourth_field_sha256"] = "not-a-sha"
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_all_four_field_consumer_fourth_sha_invalid" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_all_four_path_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["all_four_field_consumer_fourth_field_path_label"] = "wrong/fourth.json"
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_all_four_field_consumer_fourth_path_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_all_four_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["all_four_field_consumer_fourth_field_sha256"] = "7" * 64
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_all_four_field_consumer_fourth_sha_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_fourth_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["fourth_field_handoff_row_count"] = 256
    payload["fourth_field_handoff_row_ok_count"] = 256
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_fourth_field_handoff_row_count_mismatch" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_invalid_fourth_row_type(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["fourth_field_handoff_row_count"] = "257"
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_fourth_field_handoff_row_count_invalid" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_missing_fourth_row_ok(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    del payload["fourth_field_handoff_row_ok_count"]
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_fourth_field_handoff_row_ok_count_invalid" in result["failures"]


def test_future_wna16_typed_slot_entrypoint_rejects_fourth_hash_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    harness = tmp_path / "harness.json"
    payload = _harness_payload()
    payload["fourth_field_handoff_field_read_hash"] = "7172737475767778"
    _write_json(harness, payload)

    args = module.build_parser().parse_args(
        [
            "--harness-json",
            str(harness),
            "--output-json",
            str(tmp_path / "entrypoint.json"),
        ]
    )
    result = module.run_entrypoint(args)

    assert result["passed"] is False
    assert "harness_fourth_field_handoff_descriptor_hash_mismatch" in result[
        "failures"
    ]
