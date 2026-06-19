from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_future_wna16_assignment_variant_evidence_bundle.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_future_wna16_assignment_variant_evidence_bundle",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _tpot() -> dict:
    return {
        "artifact_kind": "future_wna16_assignment_variant_paired_tpot_summary",
        "passed": True,
        "performance_claim_strength": "weak_positive_existing_repeat3",
        "candidate_positive_all_repeats": True,
        "repeat_count": 3,
        "strict_context_match": True,
        "context_consistent": True,
        "endpoint_or_chunk_tpot_only": True,
        "tail_latency_claim_supported": False,
        "candidate_runtime_participation_counters_available": False,
        "prepared_table_path_enabled": False,
        "payload_bytes": 0,
        "candidate_enables_gpu_assignment_kernel_variant": True,
        "candidate_enables_single_field_replacement_live": True,
        "benchmark_is_future_typed_slot_useful_path": False,
        "current_wna16_fused_moe_arg_reinterpretation": False,
        "candidate_single_field": "B_scale",
        "expected_sample_count": 32,
        "expected_requested_output_token_count": 2048,
        "expected_effective_max_tokens": 64,
        "expected_split_id": "split",
        "paired_speedup": {"median": 1.005},
    }


def _participation() -> dict:
    return {
        "artifact_kind": "future_wna16_assignment_variant_participation_summary",
        "passed": True,
        "performance_claim": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "participation_gate_ready": True,
        "gpu_assignment_kernel_variant_participated": True,
        "single_field_replacement_live_participated": True,
        "prepared_table_path_enabled": False,
        "future_typed_slot_kernel_variant_enabled": False,
        "payload_bytes": 0,
        "single_field": "B_scale",
        "expected_sample_count": 32,
        "expected_requested_output_token_count": 2048,
        "expected_effective_max_tokens": 64,
        "expected_split_id": "split",
        "expected_launch_count": 5120,
        "row_summary": {"counters": {"launch_count": 5120}},
    }


def test_evidence_bundle_passes_when_both_inputs_pass(tmp_path: Path) -> None:
    module = _load_module()

    bundle = module.build_bundle(
        tpot=_tpot(),
        participation=_participation(),
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is True
    assert bundle["combined_evidence_ready"] is True
    assert bundle["performance_claim_strength"] == "weak_positive_with_separate_participation_evidence"
    assert bundle["performance_claim_scope"] == "counter_off_endpoint_or_chunk_tpot_only"
    assert bundle["runtime_participation_counters_available_in_tpot_run"] is False
    assert bundle["diagnostic_participation_counter_path"] is True


def test_evidence_bundle_rejects_tail_claim_in_tpot_input(tmp_path: Path) -> None:
    module = _load_module()
    tpot = _tpot()
    tpot["tail_latency_claim_supported"] = True

    bundle = module.build_bundle(
        tpot=tpot,
        participation=_participation(),
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "tpot_tail_claim_must_be_false" in bundle["failures"]


def test_evidence_bundle_rejects_participation_perf_claim(tmp_path: Path) -> None:
    module = _load_module()
    participation = _participation()
    participation["performance_claim"] = True

    bundle = module.build_bundle(
        tpot=_tpot(),
        participation=participation,
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "participation_performance_claim_not_false" in bundle["failures"]


def test_evidence_bundle_rejects_context_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    participation = _participation()
    participation["expected_effective_max_tokens"] = 32

    bundle = module.build_bundle(
        tpot=_tpot(),
        participation=participation,
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "expected_effective_max_tokens_mismatch" in bundle["failures"]


def test_evidence_bundle_rejects_single_field_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    participation = _participation()
    participation["single_field"] = "B"

    bundle = module.build_bundle(
        tpot=_tpot(),
        participation=participation,
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "single_field_mismatch" in bundle["failures"]


def test_evidence_bundle_rejects_participation_launch_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    participation = _participation()
    participation["row_summary"]["counters"]["launch_count"] = 2560

    bundle = module.build_bundle(
        tpot=_tpot(),
        participation=participation,
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "participation_launch_count_mismatch" in bundle["failures"]


def test_evidence_bundle_rejects_tpot_typed_slot_pollution(tmp_path: Path) -> None:
    module = _load_module()
    tpot = _tpot()
    tpot["benchmark_is_future_typed_slot_useful_path"] = True

    bundle = module.build_bundle(
        tpot=tpot,
        participation=_participation(),
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "tpot_future_typed_slot_path_not_false" in bundle["failures"]


def test_evidence_bundle_rejects_tpot_runtime_counters_available(tmp_path: Path) -> None:
    module = _load_module()
    tpot = _tpot()
    tpot["candidate_runtime_participation_counters_available"] = True

    bundle = module.build_bundle(
        tpot=tpot,
        participation=_participation(),
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "tpot_runtime_counters_must_be_unavailable" in bundle["failures"]


def test_evidence_bundle_rejects_tpot_repeat_count_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    tpot = _tpot()
    tpot["repeat_count"] = 1

    bundle = module.build_bundle(
        tpot=tpot,
        participation=_participation(),
        tpot_json=tmp_path / "tpot.json",
        participation_json=tmp_path / "participation.json",
    )

    assert bundle["passed"] is False
    assert "tpot_repeat_count_mismatch" in bundle["failures"]
