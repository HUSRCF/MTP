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
FOURTH_EVIDENCE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "future_wna16_fourth_field_evidence.json"
)


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_kernel_variant_one_field_handoff_canary.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_kernel_variant_one_field_handoff_canary",
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


def _payloadless_payload(
    *,
    source_count: int = 128,
    row_count: int = 257,
    timing_stub_json: str | None = None,
) -> dict:
    fourth_evidence_sha = _sha256(FOURTH_EVIDENCE_PATH)
    payload = {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_payloadless_execution",
        "payloadless_execution_name": (
            "premap_future_wna16_typed_slot_payloadless_execution_v1"
        ),
        "payloadless_execution_mode": (
            "independent_future_wna16_typed_slot_payloadless_execution"
        ),
        "payloadless_execution_source": (
            "premap_future_wna16_typed_slot_kernel_variant_benchmark_v1"
        ),
        "passed": True,
        "failures": [],
        "payloadless_execution_ready": True,
        "payloadless_execution_gate_ready": True,
        "payloadless_execution_native_requested": True,
        "payloadless_execution_native_executed": True,
        "payloadless_execution_native_passed": True,
        "payloadless_execution_native_host_wall_ms": 33.0,
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
        "expected_payload_bytes": 0,
        "expected_payload_deref_allowed": False,
        "expected_kernel_arg_pass_allowed": False,
        "expected_passed_to_kernel": False,
        "expected_changes_kernel_launch_args": False,
        "expected_uses_current_wna16_args": False,
        "expected_passes_current_wna16_args": False,
        "expected_current_wna16_arg_compatible": False,
        "expected_requires_wna16_arg_reinterpretation": False,
        "expected_measures_tpot": False,
        "expected_measures_vllm_latency": False,
        "expected_wna16_benchmark_ready": False,
        "next_runtime_stage": (
            "implement_future_wna16_typed_slot_kernel_variant_one_field_handoff_canary"
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
        "fourth_field_handoff_source_count": source_count,
        "fourth_field_handoff_row_count": row_count,
        "fourth_field_handoff_row_ok_count": row_count,
        "fourth_field_handoff_field_read_hash": "3132333435363738",
        "fourth_field_handoff_runner_hash": "8182838485868788",
        "fourth_field_handoff_evidence_path": str(FOURTH_EVIDENCE_PATH),
        "fourth_field_handoff_evidence_sha256": fourth_evidence_sha,
        "all_four_field_consumer_ready": True,
        "all_four_field_consumer_fields_read": True,
        "all_four_field_consumer_hashes_valid": True,
        "all_four_field_consumer_source_count": source_count,
        "all_four_field_consumer_row_count": row_count,
        "all_four_field_consumer_row_ok_count": row_count,
        "all_four_field_consumer_fourth_field_path_label": str(FOURTH_EVIDENCE_PATH),
        "all_four_field_consumer_fourth_field_sha256": fourth_evidence_sha,
    }
    if timing_stub_json is not None:
        payload["payloadless_execution_timing_stub_json"] = timing_stub_json
    return payload


def _canary_report(
    *,
    source_count: int = 128,
    row_count: int = 257,
    field: str = "scale_metadata_handle",
) -> dict:
    field_kind = {
        "descriptor_ptr": 1,
        "packed_weight_descriptor": 2,
        "scale_metadata_handle": 3,
        "aux_metadata_handle": 4,
    }[field]
    return {
        "passed": True,
        "require_future_wna16_single_field_handoff_canary": True,
        "require_future_wna16_kernel_side_consumer_execution": True,
        "require_future_wna16_kernel_accept_typed_slot": True,
        "require_wna16_adjacent_typed_slot": True,
        "selected_source_count": source_count,
        "merged_row_count": row_count,
        "dispatch_active_rows": row_count,
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
        "future_wna16_single_field_handoff_canary_field_name": field,
        "future_wna16_single_field_handoff_canary_field_kind": field_kind,
        "future_wna16_single_field_handoff_canary_field_mask": 1 << (field_kind - 1),
        "future_wna16_single_field_handoff_canary_row_count": row_count,
        "future_wna16_single_field_handoff_canary_row_ok_count": row_count,
        "future_wna16_single_field_handoff_canary_error_count": 0,
        "future_wna16_single_field_handoff_canary_payload_bytes": 0,
        "future_wna16_single_field_handoff_canary_live_enabled": False,
        "future_wna16_single_field_handoff_canary_passed_to_kernel": False,
        "future_wna16_single_field_handoff_canary_changes_kernel_launch_args": False,
        "future_wna16_single_field_handoff_canary_current_wna16_arg_compatible": False,
        "future_wna16_single_field_handoff_canary_requires_wna16_arg_reinterpretation": (
            False
        ),
        "future_wna16_single_field_handoff_canary_explicit_typed_abi_slot": True,
        "future_wna16_single_field_handoff_canary_reuses_current_wna16_arg_slot": False,
        "future_wna16_single_field_handoff_canary_hash_accumulator": (
            "3132333435363738"
        ),
        "future_wna16_kernel_side_consumer_execution_all_handle_fields_read": True,
        "future_wna16_kernel_side_consumer_execution_payload_bytes": 0,
        "future_wna16_kernel_side_consumer_execution_payload_deref_allowed": False,
        "future_wna16_kernel_side_consumer_execution_kernel_arg_pass_allowed": False,
        "future_wna16_kernel_side_consumer_execution_passed_to_kernel": False,
        "future_wna16_kernel_side_consumer_execution_changes_kernel_launch_args": False,
        "future_wna16_kernel_side_consumer_execution_current_wna16_arg_compatible": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_requires_wna16_arg_reinterpretation": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_explicit_typed_abi_slot": True,
        "future_wna16_kernel_side_consumer_execution_reuses_current_wna16_arg_slot": (
            False
        ),
        "future_wna16_kernel_side_consumer_execution_handle_projection_hash_accumulator": (
            "4142434445464748"
        ),
        "future_wna16_kernel_accept_typed_slot_all_handle_fields_read": True,
        "future_wna16_kernel_accept_typed_slot_payload_bytes": 0,
        "future_wna16_kernel_accept_typed_slot_passed_to_kernel": False,
        "future_wna16_kernel_accept_typed_slot_changes_kernel_launch_args": False,
        "future_wna16_kernel_accept_typed_slot_current_wna16_arg_compatible": False,
        "future_wna16_kernel_accept_typed_slot_requires_wna16_arg_reinterpretation": (
            False
        ),
        "future_wna16_kernel_accept_typed_slot_explicit_typed_abi_slot": True,
        "future_wna16_kernel_accept_typed_slot_reuses_current_wna16_arg_slot": False,
        "future_wna16_kernel_accept_typed_slot_field_read_hash_accumulator": (
            "5152535455565758"
        ),
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
    }


def test_one_field_handoff_canary_runs_native_gate(tmp_path: Path, monkeypatch):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    output = tmp_path / "one_field.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        assert args.field == "scale_metadata_handle"
        return _canary_report(), 7.5

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(output),
            "--canary-output-dir",
            str(tmp_path / "canary"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is True
    assert result["one_field_handoff_canary_ready"] is True
    assert result["one_field_handoff_field_name"] == "scale_metadata_handle"
    assert result["one_field_handoff_live_enabled"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["kernel_arg_pass_allowed"] is False
    assert result["measures_tpot"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_one_field_handoff_canary_accepts_unpadded_u64_hex(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report()
        report["future_wna16_single_field_handoff_canary_hash_accumulator"] = (
            "aaabe281160d022"
        )
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is True


def test_one_field_handoff_canary_rejects_payloadless_current_arg(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["passes_current_wna16_args"] = True
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("passes_current_wna16_args" in item for item in result["failures"])
    assert result["passes_current_wna16_args"] is True


def test_one_field_handoff_canary_rejects_payloadless_expected_kernel_arg(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["expected_kernel_arg_pass_allowed"] = True
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("expected_kernel_arg_pass_allowed" in item for item in result["failures"])


def test_one_field_handoff_canary_rejects_native_live_handoff(tmp_path: Path, monkeypatch):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report()
        report["future_wna16_single_field_handoff_canary_live_enabled"] = True
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("live_enabled" in item for item in result["failures"])
    assert result["one_field_handoff_live_enabled"] is False


def test_one_field_handoff_canary_rejects_row_count_mismatch(tmp_path: Path, monkeypatch):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload(row_count=257))

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        return _canary_report(row_count=128), 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "canary_row_count_payloadless_mismatch" in result["failures"]
    assert "canary_dispatch_rows_payloadless_mismatch" in result["failures"]


def test_one_field_handoff_canary_rejects_partial_dispatch_coverage(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload(row_count=257))

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report(row_count=257)
        report["dispatch_active_rows"] = 128
        report["future_wna16_single_field_handoff_canary_row_count"] = 128
        report["future_wna16_single_field_handoff_canary_row_ok_count"] = 128
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "canary_dispatch_rows_payloadless_mismatch" in result["failures"]


def test_one_field_handoff_canary_rejects_native_top_level_unsafe_flag(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report()
        report["uses_current_wna16_args"] = True
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("canary_uses_current_wna16_args_unsafe_nonzero")
        for item in result["failures"]
    )


def test_one_field_handoff_canary_rejects_numeric_unsafe_flag(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report()
        report["kernel_arg_pass_allowed"] = 1
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("canary_kernel_arg_pass_allowed_unsafe_nonzero")
        for item in result["failures"]
    )


def test_one_field_handoff_canary_rejects_accept_typed_slot_kernel_arg_flag(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report()
        report["future_wna16_kernel_accept_typed_slot_kernel_arg_pass_allowed"] = True
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("kernel_accept_typed_slot_kernel_arg_pass_allowed" in item for item in result["failures"])


def test_one_field_handoff_canary_rejects_string_payload_bytes(
    tmp_path: Path,
    monkeypatch,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        assert payloadless["passed"] is True
        report = _canary_report()
        report["payload_bytes"] = "16"
        return report, 8.0

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        item.startswith("canary_payload_bytes_nonzero")
        for item in result["failures"]
    )


def test_one_field_handoff_canary_rejects_incomplete_selected_field(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload(row_count=257)
    payload["field_read_row_ok_counts"]["scale_metadata_handle"] = 256
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("scale_metadata_handle" in item for item in result["failures"])


def test_one_field_handoff_canary_rejects_missing_fourth_payloadless_envelope(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload.pop("fourth_field_handoff_ready")
    payload.pop("fourth_field_handoff_source_count")
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("fourth_field_handoff_ready" in item for item in result["failures"])
    assert "payloadless_fourth_field_handoff_source_count_invalid" in result[
        "failures"
    ]


def test_one_field_handoff_canary_rejects_payloadless_fourth_hash_drift(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["fourth_field_handoff_field_read_hash"] = "7172737475767778"
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "payloadless_fourth_field_handoff_descriptor_hash_mismatch" in result[
        "failures"
    ]


def test_one_field_handoff_canary_rejects_short_payloadless_hash(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["field_read_hashes"]["scale_metadata_handle"] = "abc"
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "payloadless_scale_metadata_handle_read_hash_invalid" in result[
        "failures"
    ]


def test_one_field_handoff_canary_rejects_short_payloadless_fourth_runner_hash(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["fourth_field_handoff_runner_hash"] = "abc"
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "payloadless_fourth_field_handoff_runner_hash_invalid" in result[
        "failures"
    ]


def test_one_field_handoff_canary_defaults_to_four_field_payloadless_artifact():
    module = _load_module()

    assert (
        "future_wna16_typed_slot_kernel_variant_payloadless_execution_four_field_v3_native_run.json"
        in str(module.DEFAULT_PAYLOADLESS_JSON)
    )


def test_one_field_handoff_canary_rejects_payloadless_failures(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["failures"] = ["upstream failure"]
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "payloadless_failures_not_empty" in result["failures"]


def test_one_field_handoff_canary_rejects_all_four_not_ready(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    payload = _payloadless_payload()
    payload["all_four_field_consumer_ready"] = False
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("all_four_field_consumer_ready" in item for item in result["failures"])


def test_one_field_handoff_canary_rejects_unrelated_fourth_evidence(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    evidence = tmp_path / "evidence.json"
    _write_json(evidence, {"artifact_kind": "unrelated"})
    payload = _payloadless_payload()
    payload["fourth_field_handoff_evidence_path"] = str(evidence)
    payload["fourth_field_handoff_evidence_sha256"] = _sha256(evidence)
    payload["all_four_field_consumer_fourth_field_path_label"] = str(evidence)
    payload["all_four_field_consumer_fourth_field_sha256"] = _sha256(evidence)
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("fourth_evidence" in item for item in result["failures"])


def test_one_field_handoff_canary_rejects_legacy_v1_fourth_evidence_root(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    evidence = tmp_path / "evidence.json"
    evidence_payload = json.loads(FOURTH_EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence_payload["payloadless_execution_json"] = (
        "outputs/reports/premap_kernel_consumer/"
        "future_wna16_typed_slot_kernel_variant_payloadless_execution_four_field_v1_native_run.json"
    )
    evidence_payload["payloadless_execution_sha256"] = "1" * 64
    _write_json(evidence, evidence_payload)
    payload = _payloadless_payload()
    payload["fourth_field_handoff_evidence_path"] = str(evidence)
    payload["fourth_field_handoff_evidence_sha256"] = _sha256(evidence)
    payload["all_four_field_consumer_fourth_field_path_label"] = str(evidence)
    payload["all_four_field_consumer_fourth_field_sha256"] = _sha256(evidence)
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "payloadless_fourth_evidence_payloadless_root_is_legacy_v1" in result[
        "failures"
    ]


def test_one_field_handoff_canary_rejects_fourth_evidence_root_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    evidence = tmp_path / "evidence.json"
    evidence_payload = json.loads(FOURTH_EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence_payload["payloadless_execution_sha256"] = "1" * 64
    _write_json(evidence, evidence_payload)
    payload = _payloadless_payload()
    payload["fourth_field_handoff_evidence_path"] = str(evidence)
    payload["fourth_field_handoff_evidence_sha256"] = _sha256(evidence)
    payload["all_four_field_consumer_fourth_field_path_label"] = str(evidence)
    payload["all_four_field_consumer_fourth_field_sha256"] = _sha256(evidence)
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "payloadless_fourth_evidence_payloadless_root_sha_mismatch" in result[
        "failures"
    ]


def test_one_field_handoff_canary_rejects_fourth_evidence_root_expected_flag(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    evidence = tmp_path / "evidence.json"
    root = tmp_path / "root.json"
    root_payload = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "future_wna16_payloadless_root_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    root_payload["expected_kernel_arg_pass_allowed"] = True
    _write_json(root, root_payload)
    evidence_payload = json.loads(FOURTH_EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence_payload["payloadless_execution_json"] = str(root)
    evidence_payload["payloadless_execution_sha256"] = _sha256(root)
    _write_json(evidence, evidence_payload)
    payload = _payloadless_payload()
    payload["fourth_field_handoff_evidence_path"] = str(evidence)
    payload["fourth_field_handoff_evidence_sha256"] = _sha256(evidence)
    payload["all_four_field_consumer_fourth_field_path_label"] = str(evidence)
    payload["all_four_field_consumer_fourth_field_sha256"] = _sha256(evidence)
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        "payloadless_root_expected_kernel_arg_pass_allowed_mismatch" in item
        for item in result["failures"]
    )


def test_one_field_handoff_canary_rejects_fourth_evidence_root_missing_expected_flag(
    tmp_path: Path,
):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    evidence = tmp_path / "evidence.json"
    root = tmp_path / "renamed_legacy_root.json"
    root_payload = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "future_wna16_payloadless_root_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    root_payload.pop("expected_kernel_arg_pass_allowed")
    _write_json(root, root_payload)
    evidence_payload = json.loads(FOURTH_EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence_payload["payloadless_execution_json"] = str(root)
    evidence_payload["payloadless_execution_sha256"] = _sha256(root)
    _write_json(evidence, evidence_payload)
    payload = _payloadless_payload()
    payload["fourth_field_handoff_evidence_path"] = str(evidence)
    payload["fourth_field_handoff_evidence_sha256"] = _sha256(evidence)
    payload["all_four_field_consumer_fourth_field_path_label"] = str(evidence)
    payload["all_four_field_consumer_fourth_field_sha256"] = _sha256(evidence)
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any(
        "payloadless_root_expected_kernel_arg_pass_allowed_missing" in item
        for item in result["failures"]
    )


def test_one_field_handoff_canary_rejects_all_four_timing_stub_drift(
    tmp_path: Path,
):
    module = _load_module()
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payloadless = tmp_path / "payloadless.json"
    input_json = tmp_path / "input.json"
    _write_json(input_json, {"ok": True})
    _write_json(runner, {"input_jsons": [str(input_json)]})
    timing_payload = {
        **_payloadless_payload(),
        "runner_json": str(runner),
        "runner_sha256": _sha256(runner),
    }
    timing_payload["all_four_field_consumer_row_count"] = 123
    _write_json(timing_stub, timing_payload)
    payload = _payloadless_payload(timing_stub_json=str(timing_stub))
    payload.update(
        {
            "payloadless_execution_timing_stub_sha256": _sha256(timing_stub),
            "payloadless_execution_runner_json": str(runner),
            "payloadless_execution_runner_sha256": _sha256(runner),
        }
    )
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("all_four_field_consumer_row_count mismatch" in item for item in result["failures"])


def test_one_field_handoff_canary_rejects_native_opt_out(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
            "--no-run-native-canary",
            "--no-require-native-canary",
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "run_native_canary_must_remain_enabled_for_lab_gate" in result["failures"]
    assert "require_native_canary_must_remain_enabled_for_lab_gate" in result["failures"]


def test_one_field_handoff_canary_rejects_runner_override(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
            "--runner-json",
            str(tmp_path / "other_runner.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "runner_json_override_not_allowed_for_lab_gate" in result["failures"]


def test_one_field_handoff_canary_rejects_input_json_override(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
            "--input-json",
            str(tmp_path / "other_input.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "input_json_override_not_allowed_for_lab_gate" in result["failures"]


def test_one_field_handoff_canary_writes_failure_for_bad_json(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    output = tmp_path / "one_field.json"
    payloadless.write_text("{not json\n", encoding="utf-8")

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("payloadless_json_load_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_one_field_handoff_canary_writes_failure_for_directory_payloadless(
    tmp_path: Path,
):
    module = _load_module()
    payloadless_dir = tmp_path / "payloadless_dir"
    payloadless_dir.mkdir()
    output = tmp_path / "one_field.json"

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless_dir),
            "--output-json",
            str(output),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("payloadless_json_load_failed" in item for item in result["failures"])
    assert any("payloadless_json_sha256_failed" in item for item in result["failures"])
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_one_field_handoff_canary_requires_native_by_default(tmp_path: Path):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("one_field_handoff_canary_exception" in item for item in result["failures"])
    assert "one_field_handoff_canary_required_but_not_executed" in result["failures"]


def test_one_field_handoff_canary_rejects_dry_run_gate(tmp_path: Path, monkeypatch):
    module = _load_module()
    payloadless = tmp_path / "payloadless.json"
    _write_json(payloadless, _payloadless_payload())

    def fake_run(args, *, payloadless):
        raise AssertionError("dry-run gate must not execute native canary")

    monkeypatch.setattr(module, "_run_native_canary", fake_run)
    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
            "--dry-run-canary",
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert "dry_run_canary_not_allowed_for_lab_gate" in result["failures"]
    assert result["one_field_handoff_canary_native_executed"] is False


def test_one_field_handoff_canary_uses_payloadless_runner_provenance(tmp_path: Path):
    module = _load_module()
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payloadless = tmp_path / "payloadless.json"
    input_json = tmp_path / "input.json"
    _write_json(input_json, {"ok": True})
    _write_json(runner, {"input_jsons": [str(input_json)]})
    timing_payload = {
        **_payloadless_payload(),
        "runner_json": str(runner),
        "runner_sha256": _sha256(runner),
    }
    timing_payload.pop("payloadless_execution_timing_stub_json", None)
    timing_payload.pop("payloadless_execution_timing_stub_sha256", None)
    _write_json(timing_stub, timing_payload)
    _write_json(
        payloadless,
        _payloadless_payload(
            timing_stub_json=str(timing_stub),
        )
        | {
            "payloadless_execution_timing_stub_sha256": _sha256(timing_stub),
            "payloadless_execution_runner_json": str(runner),
            "payloadless_execution_runner_sha256": _sha256(runner),
        },
    )

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    canary_args = module._build_canary_args(
        args,
        payloadless=json.loads(payloadless.read_text(encoding="utf-8")),
    )

    assert canary_args.runner_json != runner
    assert [Path(path) for path in canary_args.input_json] == [input_json]


def test_one_field_handoff_canary_rejects_top_level_runner_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    runner = tmp_path / "runner.json"
    timing_stub = tmp_path / "timing_stub.json"
    payloadless = tmp_path / "payloadless.json"
    input_json = tmp_path / "input.json"
    _write_json(input_json, {"ok": True})
    _write_json(runner, {"input_jsons": [str(input_json)]})
    timing_payload = {
        **_payloadless_payload(),
        "runner_json": str(runner),
        "runner_sha256": _sha256(runner),
    }
    _write_json(timing_stub, timing_payload)
    payload = _payloadless_payload(timing_stub_json=str(timing_stub))
    payload.update(
        {
            "payloadless_execution_timing_stub_sha256": _sha256(timing_stub),
            "payloadless_execution_runner_json": str(runner),
            "payloadless_execution_runner_sha256": "0" * 64,
        }
    )
    _write_json(payloadless, payload)

    args = module.build_parser().parse_args(
        [
            "--payloadless-json",
            str(payloadless),
            "--output-json",
            str(tmp_path / "one_field.json"),
        ]
    )
    result = module.run_one_field_handoff_canary(args)

    assert result["passed"] is False
    assert any("runner sha256" in item for item in result["failures"])
