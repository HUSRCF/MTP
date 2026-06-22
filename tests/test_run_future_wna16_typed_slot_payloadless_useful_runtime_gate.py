from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HEX = "a" * 64
U64_HEX = "1234567890abcdef"


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_future_wna16_typed_slot_payloadless_useful_runtime_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_future_wna16_typed_slot_payloadless_useful_runtime_gate",
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


def _summary_payload(module, *, row_count: int = 513, source_count: int = 128) -> dict:
    prefix = module.PREFIX
    summary: dict[str, object] = {
        "passed": True,
        "default_required_evidence_passed": True,
        "default_kernel_consumer_wna16_benchmark_ready": False,
        "default_kernel_consumer_next_runtime_stage": (
            "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
        ),
        f"{prefix}_evidence_passed": True,
        f"{prefix}_gate_ready": True,
        f"{prefix}_ready": True,
        f"{prefix}_chain_checked": True,
        f"{prefix}_native_stub_checked": True,
        f"{prefix}_source_count": source_count,
        f"{prefix}_row_count": row_count,
        f"{prefix}_row_ok_count": row_count,
        f"{prefix}_rows_consumed": row_count,
        f"{prefix}_field_count": len(module.FIELDS),
        f"{prefix}_fields_per_row": len(module.FIELDS),
        f"{prefix}_useful_work_units": row_count * len(module.FIELDS),
        f"{prefix}_expected_useful_work_units": row_count * len(module.FIELDS),
        f"{prefix}_useful_work_coverage": 1.0,
        f"{prefix}_useful_work_kind": "native_typed_slot_four_field_row_projection",
        f"{prefix}_native_consumer_has_useful_work": True,
        f"{prefix}_payload_bytes": 0,
        f"{prefix}_payload_deref_allowed": False,
        f"{prefix}_kernel_arg_pass_allowed": False,
        f"{prefix}_passed_to_kernel": False,
        f"{prefix}_changes_kernel_launch_args": False,
        f"{prefix}_current_wna16_arg_compatible": False,
        f"{prefix}_uses_current_wna16_args": False,
        f"{prefix}_passes_current_wna16_args": False,
        f"{prefix}_requires_wna16_arg_reinterpretation": False,
        f"{prefix}_measures_tpot": False,
        f"{prefix}_measures_vllm_latency": False,
        f"{prefix}_wna16_benchmark_ready": False,
        f"{prefix}_evidence_sha256": HEX,
        f"{prefix}_useful_consumer_sha256": HEX,
        f"{prefix}_execution_sha256": HEX,
        f"{prefix}_native_timing_sha256": HEX,
        f"{prefix}_native_stub_sha256": HEX,
        f"{prefix}_chain_hash": HEX,
        f"{prefix}_evidence_path": "outputs/reports/premap_kernel_consumer/payloadless_useful.json",
        f"{prefix}_useful_consumer_json": "outputs/reports/premap_kernel_consumer/useful.json",
        f"{prefix}_execution_json": "outputs/reports/premap_kernel_consumer/execution.json",
        f"{prefix}_native_timing_json": "outputs/reports/premap_kernel_consumer/timing.json",
        f"{prefix}_native_stub_json": "outputs/reports/premap_kernel_consumer/stub.json",
    }
    for field in module.FIELDS:
        summary[f"{prefix}_{field}_row_ok_count"] = row_count
        summary[f"{prefix}_{field}_field_hash"] = U64_HEX
    return summary


def _materialize_inputs(
    tmp_path: Path,
    module,
    *,
    summary_mutation=None,
    check_mutation=None,
) -> tuple[Path, Path]:
    summary_path = tmp_path / "preflight.json"
    check_path = tmp_path / "preflight.check.json"
    summary = _summary_payload(module)
    if summary_mutation is not None:
        summary_mutation(summary)
    _write_json(summary_path, summary)
    check = {
        "passed": True,
        "failures": [],
        "checked_preflight_json": str(summary_path),
        "checked_preflight_json_raw": str(summary_path.relative_to(module.REPO_ROOT))
        if summary_path.is_relative_to(module.REPO_ROOT)
        else str(summary_path),
        "checked_preflight_sha256": module._sha256(summary_path),  # noqa: SLF001
    }
    if check_mutation is not None:
        check_mutation(check)
    _write_json(check_path, check)
    return summary_path, check_path


def _run(module, summary_path: Path, check_path: Path, output_path: Path) -> dict:
    args = module.build_parser().parse_args(
        [
            "--preflight-summary-json",
            str(summary_path),
            "--preflight-check-json",
            str(check_path),
            "--output-json",
            str(output_path),
        ]
    )
    return module.run_payloadless_useful_runtime_gate(args)


def test_payloadless_useful_runtime_gate_accepts_strict_preflight(
    tmp_path: Path,
):
    module = _load_module()
    summary_path, check_path = _materialize_inputs(tmp_path, module)

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is True
    assert result["runtime_gate_ready"] is True
    assert result["payloadless_useful_runtime_gate_ready"] is True
    assert result["payloadless_useful_execution_gate_ready"] is True
    assert result["source_count"] == 128
    assert result["row_count"] == 513
    assert result["rows_consumed"] == 513
    assert result["field_count"] == 4
    assert result["fields_per_row"] == 4
    assert result["useful_work_units"] == 513 * 4
    assert result["expected_useful_work_units"] == 513 * 4
    assert result["useful_work_coverage"] == 1.0
    assert result["useful_work_kind"] == "native_typed_slot_four_field_row_projection"
    assert result["native_consumer_has_useful_work"] is True
    assert result["field_names"] == list(module.FIELDS)
    assert set(result["field_read_hashes"]) == set(module.FIELDS)
    assert result["payload_bytes"] == 0
    assert result["payload_deref_allowed"] is False
    assert result["kernel_arg_pass_allowed"] is False
    assert result["passed_to_kernel"] is False
    assert result["changes_kernel_launch_args"] is False
    assert result["uses_current_wna16_args"] is False
    assert result["passes_current_wna16_args"] is False
    assert result["measures_tpot"] is False
    assert result["wna16_benchmark_ready"] is False
    assert result["next_runtime_stage"] == (
        "implement_future_wna16_typed_slot_payloadless_useful_benchmark_harness"
    )
    assert result["preflight_next_runtime_stage"] == (
        "implement_future_wna16_typed_slot_payloadless_useful_runtime_gate"
    )
    assert result["accepted_preflight_next_runtime_stages"] == list(
        module.ACCEPTED_PREFLIGHT_NEXT_RUNTIME_STAGES
    )
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))[
        "passed"
    ] is True


def test_payloadless_useful_runtime_gate_accepts_allowed_preflight_stages(
    tmp_path: Path,
):
    module = _load_module()
    for index, stage in enumerate(module.ACCEPTED_PREFLIGHT_NEXT_RUNTIME_STAGES):
        summary_path, check_path = _materialize_inputs(
            tmp_path / f"case_{index}",
            module,
            summary_mutation=lambda summary, stage=stage: summary.update(
                {"default_kernel_consumer_next_runtime_stage": stage}
            ),
        )

        result = _run(module, summary_path, check_path, tmp_path / f"out_{index}.json")

        assert result["passed"] is True
        assert result["runtime_gate_ready"] is True
        assert result["preflight_next_runtime_stage"] == stage
        assert result["accepted_preflight_next_runtime_stages"] == list(
            module.ACCEPTED_PREFLIGHT_NEXT_RUNTIME_STAGES
        )


def test_payloadless_useful_runtime_gate_rejects_failed_preflight_check(
    tmp_path: Path,
):
    module = _load_module()
    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        check_mutation=lambda check: check.update(
            {"passed": False, "failures": ["forced_failure"]}
        ),
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "preflight_check_not_passed" in result["failures"]
    assert "preflight_check_failures_not_empty" in result["failures"]
    assert result["runtime_gate_ready"] is False


def test_payloadless_useful_runtime_gate_rejects_summary_sha_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        check_mutation=lambda check: check.update(
            {"checked_preflight_sha256": "0" * 64}
        ),
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "preflight_check_summary_sha256_mismatch" in result["failures"]


def test_payloadless_useful_runtime_gate_rejects_summary_path_mismatch(
    tmp_path: Path,
):
    module = _load_module()
    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        check_mutation=lambda check: check.update(
            {
                "checked_preflight_json": str(tmp_path / "other.json"),
                "checked_preflight_json_raw": "other.json",
            }
        ),
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "preflight_check_summary_path_mismatch" in result["failures"]
    assert "preflight_check_summary_raw_path_mismatch" in result["failures"]


def test_payloadless_useful_runtime_gate_rejects_missing_summary_paths(
    tmp_path: Path,
):
    module = _load_module()

    def mutate(check: dict) -> None:
        check.pop("checked_preflight_json")
        check.pop("checked_preflight_json_raw")

    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        check_mutation=mutate,
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "preflight_check_summary_path_missing" in result["failures"]
    assert "preflight_check_summary_raw_path_missing" in result["failures"]


def test_payloadless_useful_runtime_gate_rejects_payload_or_current_wna16(
    tmp_path: Path,
):
    module = _load_module()
    prefix = module.PREFIX

    def mutate(summary: dict) -> None:
        summary[f"{prefix}_payload_bytes"] = 1
        summary[f"{prefix}_uses_current_wna16_args"] = True

    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        summary_mutation=mutate,
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert f"{prefix}_payload_bytes_mismatch" in result["failures"]
    assert f"{prefix}_uses_current_wna16_args_mismatch" in result["failures"]


def test_payloadless_useful_runtime_gate_rejects_next_stage_or_benchmark_ready(
    tmp_path: Path,
):
    module = _load_module()

    def mutate(summary: dict) -> None:
        summary["default_kernel_consumer_next_runtime_stage"] = "wrong_stage"
        summary["default_kernel_consumer_wna16_benchmark_ready"] = True
        summary[f"{module.PREFIX}_evidence_passed"] = False

    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        summary_mutation=mutate,
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "preflight_next_runtime_stage_mismatch" in result["failures"]
    assert "default_wna16_benchmark_ready_mismatch" in result["failures"]
    assert "payloadless_useful_execution_evidence_not_passed" in result["failures"]


def test_payloadless_useful_runtime_gate_rejects_missing_field_coverage(
    tmp_path: Path,
):
    module = _load_module()
    prefix = module.PREFIX

    def mutate(summary: dict) -> None:
        summary[f"{prefix}_descriptor_ptr_row_ok_count"] = 512
        summary[f"{prefix}_scale_metadata_handle_field_hash"] = "not_hex"

    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        summary_mutation=mutate,
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "descriptor_ptr_row_ok_count_mismatch" in result["failures"]
    assert "scale_metadata_handle_field_hash_invalid" in result["failures"]


def test_payloadless_useful_runtime_gate_rejects_incomplete_useful_work(
    tmp_path: Path,
):
    module = _load_module()
    prefix = module.PREFIX

    def mutate(summary: dict) -> None:
        summary[f"{prefix}_fields_per_row"] = 3
        summary[f"{prefix}_useful_work_units"] = 513 * 3
        summary[f"{prefix}_useful_work_coverage"] = 0.75
        summary[f"{prefix}_native_consumer_has_useful_work"] = False

    summary_path, check_path = _materialize_inputs(
        tmp_path,
        module,
        summary_mutation=mutate,
    )

    result = _run(module, summary_path, check_path, tmp_path / "out.json")

    assert result["passed"] is False
    assert "fields_per_row_mismatch" in result["failures"]
    assert "useful_work_units_mismatch" in result["failures"]
    assert "useful_work_coverage_mismatch" in result["failures"]
    assert "native_consumer_has_useful_work_mismatch" in result["failures"]
