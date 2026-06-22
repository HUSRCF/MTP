from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HANDLE_FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]


def _load_module(name: str, script_name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _materialize_useful_consumer(tmp_path: Path, *, row_count: int = 5345) -> Path:
    useful_fixture = _load_module(
        "test_run_future_wna16_typed_slot_kernel_variant_useful_consumer",
        "../tests/test_run_future_wna16_typed_slot_kernel_variant_useful_consumer.py",
    )
    useful_module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_useful_consumer",
        "run_future_wna16_typed_slot_kernel_variant_useful_consumer.py",
    )
    execution = useful_fixture._materialize_inputs(  # noqa: SLF001
        tmp_path,
        row_count=row_count,
    )
    useful_path = tmp_path / "useful.json"
    args = useful_module.build_parser().parse_args(
        ["--execution-json", str(execution), "--output-json", str(useful_path)]
    )
    useful = useful_module.run_useful_consumer(args)
    assert useful["passed"] is True
    return useful_path


def test_payloadless_useful_execution_accepts_useful_consumer_chain(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    output = tmp_path / "payloadless.json"

    args = module.build_parser().parse_args(
        ["--useful-consumer-json", str(useful_path), "--output-json", str(output)]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is True
    assert result["payloadless_useful_execution_ready"] is True
    assert result["payloadless_useful_execution_gate_ready"] is True
    assert result["payloadless_useful_execution_chain_checked"] is True
    assert result["payloadless_useful_execution_native_stub_checked"] is True
    assert result["payloadless_useful_execution_rows_consumed"] == 5345
    assert result["payloadless_useful_execution_field_count"] == 4
    assert result["payloadless_useful_execution_fields_per_row"] == 4
    assert result["payloadless_useful_execution_useful_work_units"] == 5345 * 4
    assert result["payloadless_useful_execution_expected_useful_work_units"] == 5345 * 4
    assert result["payloadless_useful_execution_useful_work_coverage"] == 1.0
    assert result["payloadless_useful_execution_useful_work_kind"] == (
        "native_typed_slot_four_field_row_projection"
    )
    assert result["payloadless_useful_execution_native_consumer_has_useful_work"] is True
    assert result["useful_consumer_fields_consumed"] == HANDLE_FIELDS
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["payload_bytes"] == 0
    assert result["payload_deref_allowed"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["next_runtime_stage"] == (
        "promote_future_wna16_typed_slot_payloadless_useful_execution_gate"
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_payloadless_useful_execution_rejects_payload_or_kernel_arg_path(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    useful["payload_bytes"] = 1
    useful["passed_to_kernel"] = True
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "useful_payload_bytes_mismatch" in result["failures"]
    assert "useful_passed_to_kernel_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_chain_checked"] is False


def test_payloadless_useful_execution_rejects_incomplete_useful_work_units(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    useful["useful_consumer_fields_consumed"] = HANDLE_FIELDS[:-1]
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "useful_fields_consumed_mismatch" in result["failures"]
    assert "payloadless_useful_work_units_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_useful_work_units"] == 5345 * 3
    assert result["payloadless_useful_execution_expected_useful_work_units"] == 5345 * 4
    assert result["payloadless_useful_execution_useful_work_coverage"] == 0.75


def test_payloadless_useful_execution_rejects_execution_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    useful["execution_sha256"] = "0" * 64
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "useful_execution_sha256_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_chain_checked"] is False


def test_payloadless_useful_execution_rejects_semantically_unsafe_execution_child(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    execution_path = Path(useful["execution_json"])
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    execution["payload_bytes"] = 8
    execution["uses_current_wna16_args"] = True
    _write_json(execution_path, execution)
    useful["execution_sha256"] = module._sha256(execution_path)  # noqa: SLF001
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "execution_payload_bytes_mismatch" in result["failures"]
    assert "execution_uses_current_wna16_args_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_chain_checked"] is False


def test_payloadless_useful_execution_rejects_semantically_unsafe_timing_child(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    execution_path = Path(useful["execution_json"])
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    timing_path = Path(useful["native_timing_json"])
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    timing["payload_bytes"] = 8
    timing["native_stub_passed"] = False
    _write_json(timing_path, timing)
    timing_sha = module._sha256(timing_path)  # noqa: SLF001
    execution["future_wna16_variant_execution_native_sha256"] = timing_sha
    _write_json(execution_path, execution)
    useful["native_timing_sha256"] = timing_sha
    useful["execution_sha256"] = module._sha256(execution_path)  # noqa: SLF001
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "timing_payload_bytes_mismatch" in result["failures"]
    assert "timing_native_stub_passed_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_chain_checked"] is False


def test_payloadless_useful_execution_rejects_useful_execution_hash_mismatch(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    hashes = dict(useful["field_read_hashes"])
    hashes["descriptor_ptr"] = "0000000000000001"
    useful["field_read_hashes"] = hashes
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "useful_execution_field_read_hashes_mismatch" in result["failures"]
    assert "useful_execution_descriptor_ptr_field_hash_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_chain_checked"] is False


def test_payloadless_useful_execution_rejects_stub_backing_mismatch(
    tmp_path: Path,
):
    module = _load_module(
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution",
        "run_future_wna16_typed_slot_kernel_variant_payloadless_useful_execution.py",
    )
    useful_path = _materialize_useful_consumer(tmp_path)
    useful = json.loads(useful_path.read_text(encoding="utf-8"))
    hashes = dict(useful["useful_consumer_field_read_hashes"])
    hashes["scale_metadata_handle"] = "0000000000000001"
    useful["useful_consumer_field_read_hashes"] = hashes
    _write_json(useful_path, useful)

    args = module.build_parser().parse_args(
        [
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(tmp_path / "out.json"),
        ]
    )
    result = module.run_payloadless_useful_execution(args)

    assert result["passed"] is False
    assert "stub_scale_metadata_handle_hash_useful_mismatch" in result["failures"]
    assert result["payloadless_useful_execution_native_stub_checked"] is False
