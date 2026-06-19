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
        / "run_wna16_typed_slot_benchmark_harness.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_wna16_typed_slot_benchmark_harness",
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


def _entry_args_ptr_sweep_payload(*, row_count: int = 1025) -> dict:
    return {
        "passed": True,
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
        "device": 1,
        "window_size": 512,
        "mirror_fields": HANDLE_FIELDS,
        "require_kernel_arg_packet_abi": True,
        "require_kernel_entry_args_abi": True,
        "require_kernel_entry_args_ptr_abi": True,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "row_counts": {field: row_count for field in HANDLE_FIELDS},
        "field_reports": {
            field: {
                "passed": True,
                "row_count": row_count,
                "window_size": 512,
                "windows_checked": ["full", "head", "middle", "tail"],
                "check_failures": [],
                "sweep_failures": [],
            }
            for field in HANDLE_FIELDS
        },
    }


def _entry_args_ptr_sweep_check_payload(
    sweep: Path,
    *,
    row_count: int = 1025,
) -> dict:
    return {
        "passed": True,
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
        "all_field_window_sweep_json": str(sweep),
        "expected_window_size": 512,
        "min_row_count": 513,
        "mirror_fields_checked": HANDLE_FIELDS,
        "require_child_consumer_view_row_layout": True,
        "require_child_field_masks": True,
        "require_child_kernel_arg_packet_abi": True,
        "require_child_kernel_entry_args_abi": True,
        "require_child_kernel_entry_args_ptr_abi": True,
        "require_child_kernel_entry_row_metadata": True,
        "row_count": row_count,
    }


def _add_entry_args_ptr_required_evidence(
    payload: dict,
    tmp_path: Path,
    *,
    row_count: int = 1025,
) -> None:
    sweep = tmp_path / "online_merged_future_native_arg_slot_all_field_window_sweep_kernel_entry_args_ptr_strict_20260619.json"
    check = tmp_path / "online_merged_future_native_arg_slot_all_field_window_sweep_kernel_entry_args_ptr_strict_20260619.check.json"
    _write_json(sweep, _entry_args_ptr_sweep_payload(row_count=row_count))
    _write_json(check, _entry_args_ptr_sweep_check_payload(sweep, row_count=row_count))
    payload["default_readonly_gate_required_evidence_check"] = {
        "passed": True,
        "failures": [],
        "required_labels": [
            "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json",
            "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json",
        ],
        "deferred_labels": [],
        "rows": [
            {
                "exists": True,
                "failures_value": [],
                "label": "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_check_json",
                "passed_value": True,
                "path": str(check),
                "path_label": (
                    "outputs/reports/premap_kernel_consumer/"
                    "online_merged_future_native_arg_slot_all_field_window_sweep_kernel_entry_args_ptr_strict_20260619.check.json"
                ),
                "sha256": _sha256(check),
                "valid_json": True,
            },
            {
                "exists": True,
                "failures_value": [],
                "label": "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json",
                "passed_value": True,
                "path": str(sweep),
                "path_label": (
                    "outputs/reports/premap_kernel_consumer/"
                    "online_merged_future_native_arg_slot_all_field_window_sweep_kernel_entry_args_ptr_strict_20260619.json"
                ),
                "sha256": _sha256(sweep),
                "valid_json": True,
            },
        ],
    }


def _preflight_payload(*, row_count: int = 1025) -> dict:
    prefix = "default_kernel_consumer_wna16_kernel_side_execution"
    fourth_prefix = "default_kernel_consumer_future_wna16_fourth_field_handoff"
    all_four_ready = "default_kernel_consumer_future_wna16_all_four_field_consumer"
    all_four = "default_kernel_consumer_future_wna16_all_four_consumer"
    kernel_side_path = "default_kernel_consumer_future_wna16_kernel_side_typed_path"
    payload = {
        "passed": True,
        f"{fourth_prefix}_ready": True,
        f"{fourth_prefix}_evidence_passed": True,
        f"{fourth_prefix}_evidence_path": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v1.json"
        ),
        f"{fourth_prefix}_evidence_sha256": "8" * 64,
        f"{fourth_prefix}_first_field": "scale_metadata_handle",
        f"{fourth_prefix}_second_field": "aux_metadata_handle",
        f"{fourth_prefix}_third_field": "packed_weight_descriptor",
        f"{fourth_prefix}_fourth_field": "descriptor_ptr",
        f"{fourth_prefix}_fourth_field_kind": 1,
        f"{fourth_prefix}_fourth_field_mask": 1,
        f"{fourth_prefix}_previous_gate_ready": True,
        f"{fourth_prefix}_native_requested": True,
        f"{fourth_prefix}_native_executed": True,
        f"{fourth_prefix}_native_passed": True,
        f"{fourth_prefix}_live_enabled": False,
        f"{fourth_prefix}_block_reason": "fourth_field_handoff_live_disabled",
        f"{fourth_prefix}_source_count": 128,
        f"{fourth_prefix}_previous_source_count": 128,
        f"{fourth_prefix}_row_count": row_count,
        f"{fourth_prefix}_row_ok_count": row_count,
        f"{fourth_prefix}_field_read_row_ok_count": row_count,
        f"{fourth_prefix}_runner_row_count": row_count,
        f"{fourth_prefix}_runner_row_ok_count": row_count,
        f"{fourth_prefix}_field_read_hash": "3132333435363738",
        f"{fourth_prefix}_runner_hash": "8182838485868788",
        f"{fourth_prefix}_third_field_read_hash": "4142434445464748",
        f"{fourth_prefix}_third_field_native_hash": "a1a2a3a4a5a6a7a8",
        f"{fourth_prefix}_payload_bytes": 0,
        f"{fourth_prefix}_expected_payload_bytes": 0,
        f"{fourth_prefix}_payload_deref_allowed": False,
        f"{fourth_prefix}_kernel_arg_pass_allowed": False,
        f"{fourth_prefix}_passed_to_kernel": False,
        f"{fourth_prefix}_changes_kernel_launch_args": False,
        f"{fourth_prefix}_current_wna16_arg_compatible": False,
        f"{fourth_prefix}_requires_wna16_arg_reinterpretation": False,
        f"{fourth_prefix}_uses_current_wna16_args": False,
        f"{fourth_prefix}_passes_current_wna16_args": False,
        f"{fourth_prefix}_measures_tpot": False,
        f"{fourth_prefix}_measures_vllm_latency": False,
        f"{fourth_prefix}_wna16_benchmark_ready": False,
        f"{all_four_ready}_ready": True,
        f"{all_four_ready}_fields_read": True,
        f"{all_four_ready}_hashes_valid": True,
        f"{all_four}_evidence_passed": True,
        f"{all_four}_evidence_path": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_v3_default.json"
        ),
        f"{all_four}_evidence_sha256": "7" * 64,
        f"{all_four}_stage_type": "lab_gate",
        f"{all_four}_bench_semantics": False,
        f"{all_four}_source_count": 128,
        f"{all_four}_row_count": row_count,
        f"{all_four}_row_ok_count": row_count,
        f"{all_four}_selected_input_count": 128,
        f"{all_four}_selected_input_manifest_sha256": "9" * 64,
        f"{all_four}_post_native_input_manifest_sha256": "9" * 64,
        f"{all_four}_fourth_field_path_label": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v1.json"
        ),
        f"{all_four}_fourth_field_sha256": "8" * 64,
        f"{all_four}_native_executed": True,
        f"{all_four}_native_passed": True,
        f"{all_four}_future_kernel_side_all_fields_read": True,
        f"{all_four}_wna16_side_all_fields_read": True,
        f"{all_four}_payload_bytes": 0,
        f"{all_four}_payload_deref_allowed": False,
        f"{all_four}_kernel_arg_pass_allowed": False,
        f"{all_four}_passed_to_kernel": False,
        f"{all_four}_changes_kernel_launch_args": False,
        f"{all_four}_current_wna16_arg_compatible": False,
        f"{all_four}_requires_wna16_arg_reinterpretation": False,
        f"{all_four}_measures_tpot": False,
        f"{all_four}_measures_vllm_latency": False,
        f"{all_four}_wna16_benchmark_ready": False,
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready": True,
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid": True,
        f"{kernel_side_path}_evidence_passed": True,
        f"{kernel_side_path}_artifact_kind": (
            "future_wna16_kernel_side_typed_consumer_path"
        ),
        f"{kernel_side_path}_name": (
            "premap_future_wna16_kernel_side_typed_consumer_path_v1"
        ),
        f"{kernel_side_path}_mode": (
            "independent_future_wna16_kernel_side_typed_consumer_path"
        ),
        f"{kernel_side_path}_source": (
            "premap_future_wna16_typed_slot_all_four_field_consumer_v1"
        ),
        f"{kernel_side_path}_stage_type": "lab_gate",
        f"{kernel_side_path}_bench_semantics": False,
        f"{kernel_side_path}_evidence_path": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_kernel_side_typed_consumer_path_v1.json"
        ),
        f"{kernel_side_path}_evidence_sha256": "8" * 64,
        f"{kernel_side_path}_all_four_gate_ready": True,
        f"{kernel_side_path}_all_four_path_label": (
            "outputs/reports/premap_kernel_consumer/"
            "future_wna16_typed_slot_kernel_variant_all_four_field_consumer_v3_default.json"
        ),
        f"{kernel_side_path}_all_four_sha256": "7" * 64,
        f"{kernel_side_path}_source_count": 128,
        f"{kernel_side_path}_input_json_count": 128,
        f"{kernel_side_path}_row_count": row_count,
        f"{kernel_side_path}_row_ok_count": row_count,
        f"{kernel_side_path}_selected_input_manifest_sha256": "9" * 64,
        f"{kernel_side_path}_native_executed": True,
        f"{kernel_side_path}_native_passed": True,
        f"{kernel_side_path}_independent_path": True,
        f"{kernel_side_path}_explicit_typed_abi_slot": True,
        f"{kernel_side_path}_future_kernel_side_checked": True,
        f"{kernel_side_path}_future_kernel_side_all_fields_read": True,
        f"{kernel_side_path}_wna16_side_checked": True,
        f"{kernel_side_path}_wna16_side_all_fields_read": True,
        f"{kernel_side_path}_payload_bytes": 0,
        f"{kernel_side_path}_payload_deref_allowed": False,
        f"{kernel_side_path}_kernel_arg_pass_allowed": False,
        f"{kernel_side_path}_passed_to_kernel": False,
        f"{kernel_side_path}_changes_kernel_launch_args": False,
        f"{kernel_side_path}_current_wna16_arg_compatible": False,
        f"{kernel_side_path}_requires_wna16_arg_reinterpretation": False,
        f"{kernel_side_path}_uses_current_wna16_args": False,
        f"{kernel_side_path}_measures_tpot": False,
        f"{kernel_side_path}_measures_vllm_latency": False,
        f"{kernel_side_path}_wna16_benchmark_ready": False,
        "default_kernel_consumer_wna16_kernel_side_execution_ready": True,
        "default_kernel_consumer_wna16_benchmark_ready": False,
        "default_kernel_consumer_wna16_benchmark_prerequisites_ready": False,
        "default_kernel_consumer_next_runtime_stage": (
            "implement_wna16_typed_slot_benchmark_harness"
        ),
        f"{prefix}_required": True,
        f"{prefix}_checked": True,
        f"{prefix}_name": "premap_future_wna16_kernel_side_consumer_execution_v1",
        f"{prefix}_mode": "readonly_future_wna16_kernel_side_consumer_execution",
        f"{prefix}_source": "premap_future_wna16_kernel_accept_typed_slot_v1",
        f"{prefix}_packet_chain_depth": 16,
        f"{prefix}_all_handle_fields_read": True,
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
        f"{prefix}_hash_accumulator": "1112131415161718",
        f"{prefix}_handle_projection_hash_accumulator": "2122232425262728",
        f"{prefix}_descriptor_ptr_read_hash_accumulator": "3132333435363738",
        f"{prefix}_packed_weight_descriptor_read_hash_accumulator": "4142434445464748",
        f"{prefix}_scale_metadata_handle_read_hash_accumulator": "5152535455565758",
        f"{prefix}_aux_metadata_handle_read_hash_accumulator": "6162636465666768",
    }
    for field in HANDLE_FIELDS:
        payload[f"{prefix}_{field}_read_row_ok_count"] = row_count
    return payload


def _preflight_payload_with_entry_args(
    tmp_path: Path,
    *,
    row_count: int = 1025,
) -> dict:
    payload = _preflight_payload(row_count=row_count)
    _add_entry_args_ptr_required_evidence(payload, tmp_path, row_count=row_count)
    return payload


def _runner_payload(*, row_count: int = 1025, source_count: int = 128) -> dict:
    prefix = "future_wna16_kernel_side_consumer_execution"
    payload = {
        "passed": True,
        "selected_source_count": source_count,
        "merged_row_count": row_count,
        f"{prefix}_checked": True,
        f"{prefix}_abi_name": "premap_future_wna16_kernel_side_consumer_execution_v1",
        f"{prefix}_mode": "readonly_future_wna16_kernel_side_consumer_execution",
        f"{prefix}_source": "premap_future_wna16_kernel_accept_typed_slot_v1",
        f"{prefix}_packet_chain_depth": 16,
        f"{prefix}_all_handle_fields_read": True,
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
        f"{prefix}_hash_accumulator": "1112131415161718",
        f"{prefix}_handle_projection_hash_accumulator": "2122232425262728",
        f"{prefix}_descriptor_ptr_read_hash_accumulator": "3132333435363738",
        f"{prefix}_packed_weight_descriptor_read_hash_accumulator": "4142434445464748",
        f"{prefix}_scale_metadata_handle_read_hash_accumulator": "5152535455565758",
        f"{prefix}_aux_metadata_handle_read_hash_accumulator": "6162636465666768",
    }
    for field in HANDLE_FIELDS:
        payload[f"{prefix}_{field}_read_row_ok_count"] = row_count
    return payload


def _runner_payload_real_like(*, row_count: int = 1025, source_count: int = 128) -> dict:
    prefix = "future_wna16_kernel_side_consumer_execution"
    full = _runner_payload(row_count=row_count, source_count=source_count)
    stub_summary = {}
    top = {
        "passed": full["passed"],
        "selected_source_count": full["selected_source_count"],
        "merged_row_count": full["merged_row_count"],
        f"{prefix}_checked": full[f"{prefix}_checked"],
        f"{prefix}_name": full[f"{prefix}_abi_name"],
        f"{prefix}_mode": full[f"{prefix}_mode"],
        f"{prefix}_source": full[f"{prefix}_source"],
        f"{prefix}_packet_chain_depth": full[f"{prefix}_packet_chain_depth"],
        f"{prefix}_all_handle_fields_read": full[
            f"{prefix}_all_handle_fields_read"
        ],
        f"{prefix}_row_count": full[f"{prefix}_row_count"],
        f"{prefix}_row_ok_count": full[f"{prefix}_row_ok_count"],
        f"{prefix}_error_count": full[f"{prefix}_error_count"],
        f"{prefix}_payload_bytes": full[f"{prefix}_payload_bytes"],
        f"{prefix}_payload_deref_allowed": full[
            f"{prefix}_payload_deref_allowed"
        ],
        f"{prefix}_kernel_arg_pass_allowed": full[
            f"{prefix}_kernel_arg_pass_allowed"
        ],
        f"{prefix}_passed_to_kernel": full[f"{prefix}_passed_to_kernel"],
        f"{prefix}_changes_kernel_launch_args": full[
            f"{prefix}_changes_kernel_launch_args"
        ],
        f"{prefix}_current_wna16_arg_compatible": full[
            f"{prefix}_current_wna16_arg_compatible"
        ],
        f"{prefix}_requires_wna16_arg_reinterpretation": full[
            f"{prefix}_requires_wna16_arg_reinterpretation"
        ],
        f"{prefix}_explicit_typed_abi_slot": full[
            f"{prefix}_explicit_typed_abi_slot"
        ],
        f"{prefix}_reuses_current_wna16_arg_slot": full[
            f"{prefix}_reuses_current_wna16_arg_slot"
        ],
        f"{prefix}_handle_projection_hash_accumulator": full[
            f"{prefix}_handle_projection_hash_accumulator"
        ],
    }
    for key, value in full.items():
        if key.startswith(prefix):
            stub_summary[key] = value
    top["stub_summary"] = stub_summary
    return top


def test_wna16_typed_slot_benchmark_harness_accepts_strict_artifacts(tmp_path: Path):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    check = tmp_path / "preflight.check.json"
    runner = tmp_path / "runner.json"
    output = tmp_path / "out.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(
        check,
        {
            "passed": True,
            "result": {"passed": True},
            "checked_preflight_json": str(preflight),
            "checked_preflight_sha256": _sha256(preflight),
        },
    )
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--preflight-check-json",
            str(check),
            "--runner-json",
            str(runner),
            "--output-json",
            str(output),
            "--require-preflight-check",
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is True
    assert result["benchmark_harness_ready"] is True
    assert result["wna16_benchmark_ready"] is False
    assert result["current_wna16_arg_pass"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["payload_deref_allowed"] is False
    assert result["row_count"] == 1025
    assert result["field_read_row_ok_counts"]["scale_metadata_handle"] == 1025
    assert result["fourth_field_handoff_ready"] is True
    assert result["fourth_field_handoff_evidence_path"] == (
        "outputs/reports/premap_kernel_consumer/"
        "future_wna16_typed_slot_kernel_variant_fourth_field_handoff_canary_v1.json"
    )
    assert result["fourth_field_handoff_evidence_sha256"] == "8" * 64
    assert result["fourth_field_handoff_source_count"] == 128
    assert result["fourth_field_handoff_row_count"] == 1025
    assert result["fourth_field_handoff_row_ok_count"] == 1025
    assert result["fourth_field_handoff_field_read_hash"] == "3132333435363738"
    assert result["fourth_field_handoff_runner_hash"] == "8182838485868788"
    assert result["all_four_field_consumer_ready"] is True
    assert result["all_four_field_consumer_fields_read"] is True
    assert result["all_four_field_consumer_hashes_valid"] is True
    assert result["all_four_field_consumer_source_count"] == 128
    assert result["all_four_field_consumer_row_count"] == 1025
    assert result["future_wna16_kernel_side_typed_consumer_path_ready"] is True
    assert result["future_wna16_kernel_side_typed_consumer_path_source_count"] == 128
    assert result["future_wna16_kernel_side_typed_consumer_path_row_count"] == 1025
    assert (
        result["future_wna16_kernel_side_typed_consumer_path_all_four_sha256"]
        == "7" * 64
    )
    assert result["next_runtime_stage"] == (
        "implement_future_wna16_typed_slot_kernel_variant_entrypoint"
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_wna16_typed_slot_benchmark_harness_accepts_real_like_stub_summary(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(runner, _runner_payload_real_like())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is True
    assert result["field_read_hashes"]["descriptor_ptr"] == "3132333435363738"


def test_wna16_typed_slot_benchmark_harness_rejects_missing_kernel_side_path_gate(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload["default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"] = False
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any(
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_ready"
        in failure
        for failure in result["failures"]
    )


def test_wna16_typed_slot_benchmark_harness_rejects_kernel_side_path_bad_hash_gate(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload[
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid"
    ] = False
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any(
        "default_kernel_consumer_future_wna16_kernel_side_typed_consumer_path_hashes_valid"
        in failure
        for failure in result["failures"]
    )


def test_wna16_typed_slot_benchmark_harness_rejects_kernel_side_path_bad_evidence(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload["default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_path"] = ""
    payload["default_kernel_consumer_future_wna16_kernel_side_typed_path_evidence_sha256"] = "not-sha"
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_kernel_side_typed_path_evidence_path_missing" in result["failures"]
    assert "preflight_kernel_side_typed_path_evidence_sha256_invalid" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_benchmark_ready(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload["default_kernel_consumer_wna16_benchmark_ready"] = True
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("default_kernel_consumer_wna16_benchmark_ready" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_nested_summary_conflict(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    nested = dict(payload)
    nested["default_kernel_consumer_wna16_benchmark_ready"] = True
    payload["lab_gate_status_summary"] = nested
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any(
        item.startswith("preflight_summary_top_level_conflict:")
        for item in result["failures"]
    )


def test_wna16_typed_slot_benchmark_harness_rejects_missing_fourth_field_ready(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload["default_kernel_consumer_future_wna16_fourth_field_handoff_ready"] = False
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("fourth_field_handoff_ready" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_missing_all_four_gate(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload["default_kernel_consumer_future_wna16_all_four_field_consumer_ready"] = (
        False
    )
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("all_four_field_consumer_ready" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_all_four_fourth_binding_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload[
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_path_label"
    ] = "outputs/reports/premap_kernel_consumer/wrong_fourth.json"
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_all_four_fourth_path_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_all_four_missing_fourth_path(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload.pop(
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_path_label"
    )
    payload.pop("default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_path")
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_all_four_fourth_path_missing" in result["failures"]
    assert "preflight_fourth_field_evidence_path_missing" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_all_four_invalid_sha(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload[
        "default_kernel_consumer_future_wna16_all_four_consumer_fourth_field_sha256"
    ] = "not-a-sha"
    payload[
        "default_kernel_consumer_future_wna16_fourth_field_handoff_evidence_sha256"
    ] = "not-a-sha"
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_all_four_fourth_sha_invalid" in result["failures"]
    assert "preflight_fourth_field_evidence_sha_invalid" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_all_four_manifest_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload[
        "default_kernel_consumer_future_wna16_all_four_consumer_post_native_input_manifest_sha256"
    ] = "a" * 64
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_all_four_post_native_input_manifest_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_all_four_source_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload["default_kernel_consumer_future_wna16_all_four_consumer_source_count"] = 129
    payload["default_kernel_consumer_future_wna16_all_four_consumer_row_count"] = 1026
    payload["default_kernel_consumer_future_wna16_all_four_consumer_row_ok_count"] = 1026
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_all_four_selected_input_count_mismatch" in result["failures"]
    assert "preflight_all_four_fourth_source_count_mismatch" in result["failures"]
    assert "preflight_all_four_fourth_row_count_mismatch" in result["failures"]
    assert "preflight_all_four_wna16_row_count_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_fourth_field_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path, row_count=1025)
    fourth_prefix = "default_kernel_consumer_future_wna16_fourth_field_handoff"
    for suffix in (
        "row_count",
        "row_ok_count",
        "field_read_row_ok_count",
        "runner_row_count",
        "runner_row_ok_count",
    ):
        payload[f"{fourth_prefix}_{suffix}"] = 1026
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_fourth_field_handoff_wna16_row_count_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_fourth_field_hash_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    payload[
        "default_kernel_consumer_future_wna16_fourth_field_handoff_field_read_hash"
    ] = "7172737475767778"
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_fourth_field_handoff_descriptor_hash_mismatch" in result["failures"]
    assert "runner_fourth_field_handoff_descriptor_hash_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_preflight_check_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    check = tmp_path / "preflight.check.json"
    runner = tmp_path / "runner.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(
        check,
        {
            "passed": True,
            "result": {"passed": True},
            "checked_preflight_json": str(preflight),
            "checked_preflight_sha256": "0" * 64,
        },
    )
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--preflight-check-json",
            str(check),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
            "--require-preflight-check",
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_check_sha256_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_unbound_preflight_check(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    check = tmp_path / "preflight.check.json"
    runner = tmp_path / "runner.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(check, {"passed": True, "result": {"passed": True}})
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--preflight-check-json",
            str(check),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
            "--require-preflight-check",
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_check_json_target_missing" in result["failures"]
    assert "preflight_check_sha256_missing" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_preflight_check_target_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    other_preflight = tmp_path / "other_preflight.json"
    check = tmp_path / "preflight.check.json"
    runner = tmp_path / "runner.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(other_preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(
        check,
        {
            "passed": True,
            "result": {"passed": True},
            "checked_preflight_json": str(other_preflight),
            "checked_preflight_sha256": _sha256(preflight),
        },
    )
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--preflight-check-json",
            str(check),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
            "--require-preflight-check",
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "preflight_check_json_target_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_source_count_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(runner, _runner_payload(source_count=129))

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "runner_fourth_field_handoff_source_count_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_runner_safety_open(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    runner_payload = _runner_payload()
    runner_payload[
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"
    ] = True
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(runner, runner_payload)

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("kernel_arg_pass_allowed" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_stub_summary_safety_conflict(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    runner_payload = _runner_payload_real_like()
    runner_payload["stub_summary"][
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed"
    ] = True
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(runner, runner_payload)

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("duplicate_mismatch" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_row_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path, row_count=1025))
    _write_json(runner, _runner_payload(row_count=1026))

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert "runner_preflight_row_count_mismatch" in result["failures"]


def test_wna16_typed_slot_benchmark_harness_rejects_cross_hash_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    runner_payload = _runner_payload()
    runner_payload[
        "future_wna16_kernel_side_consumer_execution_scale_metadata_handle_read_hash_accumulator"
    ] = "aaaaaaaaaaaaaaaa"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(runner, runner_payload)

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("scale_metadata_handle_read_hash_accumulator_mismatch" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_weak_hash(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    runner_payload = _runner_payload()
    runner_payload[
        "future_wna16_kernel_side_consumer_execution_hash_accumulator"
    ] = "0"
    _write_json(preflight, _preflight_payload_with_entry_args(tmp_path))
    _write_json(runner, runner_payload)

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert any("hash_accumulator_invalid" in item for item in result["failures"])


def test_wna16_typed_slot_benchmark_harness_rejects_missing_entry_args_ptr_row(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    rows = payload["default_readonly_gate_required_evidence_check"]["rows"]
    payload["default_readonly_gate_required_evidence_check"]["rows"] = [
        row
        for row in rows
        if row["label"]
        != "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json"
    ]
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json_required_evidence_row_missing"
        in result["failures"]
    )


def test_wna16_typed_slot_benchmark_harness_rejects_entry_args_ptr_child_abi_gap(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    rows = payload["default_readonly_gate_required_evidence_check"]["rows"]
    sweep_path = Path(
        next(
            row["path"]
            for row in rows
            if row["label"]
            == "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json"
        )
    )
    sweep_payload = json.loads(sweep_path.read_text(encoding="utf-8"))
    sweep_payload["require_kernel_entry_args_ptr_abi"] = False
    _write_json(sweep_path, sweep_payload)
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert (
        "entry_args_ptr_sweep_require_kernel_entry_args_ptr_abi_not_required"
        in result["failures"]
    )
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json_artifact_sha256_mismatch"
        in result["failures"]
    )


def test_wna16_typed_slot_benchmark_harness_rejects_entry_args_ptr_stale_sha(
    tmp_path: Path,
):
    module = _load_module()
    preflight = tmp_path / "preflight.json"
    runner = tmp_path / "runner.json"
    payload = _preflight_payload_with_entry_args(tmp_path)
    rows = payload["default_readonly_gate_required_evidence_check"]["rows"]
    for row in rows:
        if (
            row["label"]
            == "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json"
        ):
            row["sha256"] = "0" * 64
    _write_json(preflight, payload)
    _write_json(runner, _runner_payload())

    args = module.build_parser().parse_args(
        [
            "--preflight-json",
            str(preflight),
            "--runner-json",
            str(runner),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_harness(args)

    assert result["passed"] is False
    assert (
        "future_kernel_native_arg_slot_all_field_entry_args_ptr_sweep_json_artifact_sha256_mismatch"
        in result["failures"]
    )
