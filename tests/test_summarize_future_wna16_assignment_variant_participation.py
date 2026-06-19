from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_future_wna16_assignment_variant_participation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_future_wna16_assignment_variant_participation",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _perf(module, *, launch_count: int = 16) -> dict:
    payload = {key: True for key in module.REQUIRED_TRUE_FIELDS}
    payload.update({key: False for key in module.REQUIRED_FALSE_FIELDS})
    payload.update(module.REQUIRED_EQUAL_FIELDS)
    payload.update(
        {
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count": launch_count // 2,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count": launch_count // 2,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_minimal_identity_envelope_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_minimal_identity_envelope_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_missing_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_block_reason_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_layer_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_cache_hit_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_package_cache_miss_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_attached_count": launch_count // 2,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_identity_ok_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_identity_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_missing_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_attached_count": launch_count // 2,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_identity_ok_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_identity_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_missing_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_attached_count": launch_count // 2,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_identity_ok_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_identity_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_missing_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_launch_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_fallback_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_identity_blocked_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_candidate_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_ok_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_source_missing_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_unsupported_field_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_candidate_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_ok_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_replaced_count": launch_count,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_disabled_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_signature_mismatch_allowed_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_signature_mismatch_blocked_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_source_missing_fallback_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_type_mismatch_fallback_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_hit_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_miss_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_type_compatible_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_type_mismatch_count": 0,
            "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_original_count": launch_count,
        }
    )
    return payload


def _rows_and_files(tmp_path: Path, module, *, launch_count: int = 16) -> list[dict]:
    trace_dir = tmp_path / "trace"
    _write_json(trace_dir / "performance_summary.json", _perf(module, launch_count=launch_count))
    return [
        {
            "mode": module.DEFAULT_MODE,
            "repeat": 0,
            "returncode": 0,
            "trace_dir": str(trace_dir),
            "sample_count": 32,
            "requested_output_token_count": 2048,
            "effective_max_tokens": 64,
            "split_id": "external_prompt_gate_dolly_32_gen64_utilization",
        }
    ]


def test_participation_summary_passes_valid_counters(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is True
    assert summary["participation_gate_ready"] is True
    assert summary["performance_claim"] is False
    assert summary["gpu_assignment_kernel_variant_participated"] is True
    assert summary["single_field_replacement_live_participated"] is True
    assert summary["row_summary"]["counters"]["launch_count"] == 16
    assert summary["measures_vllm_latency"] is False


def test_participation_summary_rejects_missing_launches(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=0)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "launch_count_mismatch" in summary["failures"]


def test_participation_summary_rejects_identity_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)
    perf_path = tmp_path / "trace" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_identity_mismatch_count"] = 1
    _write_json(perf_path, perf)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is False
    assert "gpu_assignment_identity_mismatch_nonzero" in summary["failures"]


def test_participation_summary_rejects_single_field_payload(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)
    perf_path = tmp_path / "trace" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes"] = 4
    _write_json(perf_path, perf)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is False
    assert "single_field_live_zero_counter_violation" in summary["failures"]


def test_participation_summary_rejects_prepared_table_source(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)
    perf_path = tmp_path / "trace" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_count"] = 1
    _write_json(perf_path, perf)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is False
    assert "prepared_table_source_nonzero" in summary["failures"]


def test_participation_summary_rejects_counter_mode_off(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)
    perf_path = tmp_path / "trace" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_handoff_live_counter_mode"] = "off"
    _write_json(perf_path, perf)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is False
    assert "performance_runtime_shadow_premap_kernel_arg_handoff_live_counter_mode_mismatch" in summary["failures"]


def test_participation_summary_rejects_partial_launch_count_by_default(
    tmp_path: Path,
) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)

    summary = module.build_summary(rows, results_json=tmp_path / "results.json")

    assert summary["passed"] is False
    assert "launch_count_mismatch" in summary["failures"]


def test_participation_summary_rejects_missing_required_counter(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)
    perf_path = tmp_path / "trace" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf.pop(
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_missing_count"
    )
    _write_json(perf_path, perf)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is False
    assert any(
        failure.startswith(
            "counter_runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_missing_count"
        )
        for failure in summary["failures"]
    )


def test_participation_summary_rejects_string_or_float_counter(tmp_path: Path) -> None:
    module = _load_module()
    rows = _rows_and_files(tmp_path, module, launch_count=16)
    perf_path = tmp_path / "trace" / "performance_summary.json"
    perf = json.loads(perf_path.read_text(encoding="utf-8"))
    perf["runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_launch_count"] = "16"
    perf["runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count"] = 16.0
    _write_json(perf_path, perf)

    summary = module.build_summary(
        rows,
        results_json=tmp_path / "results.json",
        expected_launch_count=16,
    )

    assert summary["passed"] is False
    assert any(
        failure.startswith(
            "counter_runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_launch_count"
        )
        for failure in summary["failures"]
    )
    assert any(
        failure.startswith(
            "counter_runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count"
        )
        for failure in summary["failures"]
    )
