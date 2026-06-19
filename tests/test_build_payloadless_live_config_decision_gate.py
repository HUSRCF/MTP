from __future__ import annotations

import importlib.util
import json
from pathlib import Path


FIELDS = [
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
]


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "build_payloadless_live_config_decision_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_payloadless_live_config_decision_gate",
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


def _noop() -> dict:
    return {
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
    }


def _repeat_summary() -> dict:
    return {
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_ab_repeat_summary",
        "passed": True,
        "failures": [],
        "positive_all_repeats": True,
        "repeat_count": 3,
        "speedup_stats": {"min": 1.01, "mean": 1.02},
        **_noop(),
    }


def _heldout_comparison() -> dict:
    return {
        "artifact_kind": "future_wna16_typed_slot_payloadless_useful_ab_comparison",
        "passed": False,
        "comparison_ready": True,
        "measures_tpot": True,
        "measures_vllm_latency": True,
        "performance_claim_ready": False,
        "candidate_faster": False,
        "diagnostic_only": True,
        "failures": ["candidate_not_faster_than_baseline_diagnostic_only"],
        "speedup_vs_baseline": 0.98,
        "improvement_pct": -2.0,
        "expected_sample_count": 32,
        "expected_requested_output_token_count": 2048,
        "expected_gpu": "1",
        "baseline_json": (
            "/tmp/production_like_tpot_heldout32/"
            "future_wna16_typed_slot_payloadless_useful_production_like_tpot_baseline_heldout32.json"
        ),
        "candidate_json": (
            "/tmp/production_like_tpot_heldout32/"
            "future_wna16_typed_slot_payloadless_useful_production_like_tpot_candidate_heldout32.json"
        ),
        **_noop(),
    }


def _useful_consumer() -> dict:
    row_count = 5345
    return {
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_useful_consumer",
        "passed": True,
        "failures": [],
        "useful_consumer_ready": True,
        "useful_consumer_native_stub_checked": True,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "row_count": row_count,
        "useful_consumer_rows_consumed": row_count,
        "useful_consumer_fields_consumed": list(FIELDS),
        **_noop(),
    }


def _run(module, tmp_path: Path, *, repeat=None, heldout=None, useful=None) -> dict:
    repeat_path = tmp_path / "repeat.json"
    heldout_path = tmp_path / "production_like_tpot_heldout32" / "heldout32.json"
    useful_path = tmp_path / "useful.json"
    output_path = tmp_path / "decision.json"
    _write_json(repeat_path, repeat or _repeat_summary())
    _write_json(heldout_path, heldout or _heldout_comparison())
    _write_json(useful_path, useful or _useful_consumer())
    args = module.build_parser().parse_args(
        [
            "--repeat-summary-json",
            str(repeat_path),
            "--heldout-comparison-json",
            str(heldout_path),
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(output_path),
        ]
    )
    return module.build_decision(args)


def test_payloadless_decision_gate_freezes_live_config_performance(tmp_path: Path) -> None:
    module = _load_module()

    result = _run(module, tmp_path)

    assert result["passed"] is True
    assert result["freeze_payloadless_live_config_performance_claim"] is True
    assert (
        result["payloadless_live_config_status"]
        == "safe_participation_path_not_performance_mainline"
    )
    assert (
        result["real_performance_next_path"]
        == "future_typed_slot_useful_consumer_or_payload_cache_manager"
    )
    assert result["kernel_arg_pass_allowed"] is False
    assert result["payload_bytes"] == 0


def test_payloadless_decision_gate_rejects_heldout_positive_claim(tmp_path: Path) -> None:
    module = _load_module()
    heldout = _heldout_comparison()
    heldout["candidate_faster"] = True
    heldout["performance_claim_ready"] = True
    heldout["diagnostic_only"] = False
    heldout["passed"] = True
    heldout["failures"] = []
    heldout["speedup_vs_baseline"] = 1.01
    heldout["improvement_pct"] = 1.0

    result = _run(module, tmp_path, heldout=heldout)

    assert result["passed"] is False
    assert "heldout_passed_not_false" in result["failures"]
    assert "heldout_performance_claim_ready_not_false" in result["failures"]
    assert "heldout_candidate_faster_not_false" in result["failures"]


def test_payloadless_decision_gate_rejects_non_heldout_provenance(tmp_path: Path) -> None:
    module = _load_module()
    heldout = _heldout_comparison()
    heldout["baseline_json"] = "/tmp/production_like_tpot/baseline_original.json"
    heldout["candidate_json"] = "/tmp/production_like_tpot/candidate_original.json"
    repeat_path = tmp_path / "repeat.json"
    heldout_path = tmp_path / "production_like_tpot" / "comparison_original.json"
    useful_path = tmp_path / "useful.json"
    output_path = tmp_path / "decision.json"
    _write_json(repeat_path, _repeat_summary())
    _write_json(heldout_path, heldout)
    _write_json(useful_path, _useful_consumer())
    args = module.build_parser().parse_args(
        [
            "--repeat-summary-json",
            str(repeat_path),
            "--heldout-comparison-json",
            str(heldout_path),
            "--useful-consumer-json",
            str(useful_path),
            "--output-json",
            str(output_path),
        ]
    )

    result = module.build_decision(args)

    assert result["passed"] is False
    assert "heldout_artifact_path_not_heldout32" in result["failures"]
    assert "heldout_baseline_json_not_heldout32" in result["failures"]
    assert "heldout_candidate_json_not_heldout32" in result["failures"]


def test_payloadless_decision_gate_rejects_useful_consumer_not_ready(tmp_path: Path) -> None:
    module = _load_module()
    useful = _useful_consumer()
    useful["useful_consumer_ready"] = False

    result = _run(module, tmp_path, useful=useful)

    assert result["passed"] is False
    assert "useful_consumer_ready_not_true" in result["failures"]


def test_payloadless_decision_gate_rejects_kernel_arg_pass(tmp_path: Path) -> None:
    module = _load_module()
    repeat = _repeat_summary()
    repeat["kernel_arg_pass_allowed"] = True

    result = _run(module, tmp_path, repeat=repeat)

    assert result["passed"] is False
    assert "repeat_summary_kernel_arg_pass_allowed_not_false" in result["failures"]


def test_payloadless_decision_gate_rejects_heldout_or_useful_safety_violation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    heldout = _heldout_comparison()
    useful = _useful_consumer()
    heldout["payload_deref_allowed"] = True
    useful["payload_bytes"] = 64

    result = _run(module, tmp_path, heldout=heldout, useful=useful)

    assert result["passed"] is False
    assert "heldout_payload_deref_allowed_not_false" in result["failures"]
    assert "useful_payload_bytes_not_zero" in result["failures"]
