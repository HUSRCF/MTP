#!/usr/bin/env python3
"""Combine assignment-variant TPOT and participation artifacts.

The paired TPOT artifact is counter-off and therefore low-overhead, but it
cannot prove runtime participation counters.  The participation artifact is
detailed and proves counters, but it is diagnostic-only.  This bundle requires
both and keeps their claims separate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TPOT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_assignment_variant_paired_tpot_repeat3_v1.json"
)
DEFAULT_PARTICIPATION_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_assignment_variant_participation_smoke32_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_assignment_variant_evidence_bundle_v1.json"
)

ARTIFACT_KIND = "future_wna16_assignment_variant_evidence_bundle"
SUMMARY_NAME = "future_wna16_assignment_variant_evidence_bundle_v1"


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_bundle(
    *,
    tpot: dict[str, Any],
    participation: dict[str, Any],
    tpot_json: Path,
    participation_json: Path,
) -> dict[str, Any]:
    failures: list[str] = []

    if tpot.get("artifact_kind") != "future_wna16_assignment_variant_paired_tpot_summary":
        failures.append("tpot_artifact_kind_mismatch")
    if participation.get("artifact_kind") != "future_wna16_assignment_variant_participation_summary":
        failures.append("participation_artifact_kind_mismatch")
    if tpot.get("passed") is not True:
        failures.append("tpot_gate_not_passed")
    if participation.get("passed") is not True:
        failures.append("participation_gate_not_passed")

    if tpot.get("performance_claim_strength") != "weak_positive_existing_repeat3":
        failures.append("tpot_claim_strength_unexpected")
    if tpot.get("candidate_positive_all_repeats") is not True:
        failures.append("tpot_candidate_not_positive_all_repeats")
    if tpot.get("repeat_count") != 3:
        failures.append("tpot_repeat_count_mismatch")
    if tpot.get("strict_context_match") is not True:
        failures.append("tpot_strict_context_not_true")
    if tpot.get("context_consistent") is not True:
        failures.append("tpot_context_consistent_not_true")
    if tpot.get("endpoint_or_chunk_tpot_only") is not True:
        failures.append("tpot_endpoint_or_chunk_flag_missing")
    if tpot.get("tail_latency_claim_supported") is not False:
        failures.append("tpot_tail_claim_must_be_false")
    if tpot.get("candidate_runtime_participation_counters_available") is not False:
        failures.append("tpot_runtime_counters_must_be_unavailable")
    if tpot.get("prepared_table_path_enabled") is not False:
        failures.append("tpot_prepared_table_path_enabled")
    if tpot.get("payload_bytes") != 0:
        failures.append("tpot_payload_bytes_nonzero")
    if tpot.get("candidate_enables_gpu_assignment_kernel_variant") is not True:
        failures.append("tpot_candidate_gpu_assignment_not_enabled")
    if tpot.get("candidate_enables_single_field_replacement_live") is not True:
        failures.append("tpot_candidate_single_field_live_not_enabled")
    if tpot.get("benchmark_is_future_typed_slot_useful_path") is not False:
        failures.append("tpot_future_typed_slot_path_not_false")
    if tpot.get("current_wna16_fused_moe_arg_reinterpretation") is not False:
        failures.append("tpot_current_wna16_arg_reinterpretation_not_false")

    if participation.get("performance_claim") is not False:
        failures.append("participation_performance_claim_not_false")
    if participation.get("measures_tpot") is not False:
        failures.append("participation_measures_tpot_not_false")
    if participation.get("measures_vllm_latency") is not False:
        failures.append("participation_measures_vllm_latency_not_false")
    if participation.get("participation_gate_ready") is not True:
        failures.append("participation_gate_not_ready")
    if participation.get("gpu_assignment_kernel_variant_participated") is not True:
        failures.append("participation_gpu_assignment_not_observed")
    if participation.get("single_field_replacement_live_participated") is not True:
        failures.append("participation_single_field_not_observed")
    if participation.get("prepared_table_path_enabled") is not False:
        failures.append("participation_prepared_table_path_enabled")
    if participation.get("future_typed_slot_kernel_variant_enabled") is not False:
        failures.append("participation_future_typed_slot_kernel_variant_not_false")
    if participation.get("payload_bytes") != 0:
        failures.append("participation_payload_bytes_nonzero")

    tpot_field = tpot.get("candidate_single_field")
    participation_field = participation.get("single_field")
    if tpot_field != participation_field:
        failures.append("single_field_mismatch")

    expected_sample_count = tpot.get("expected_sample_count")
    expected_tokens = tpot.get("expected_requested_output_token_count")
    expected_max_tokens = tpot.get("expected_effective_max_tokens")
    expected_split = tpot.get("expected_split_id")
    if participation.get("expected_sample_count") != expected_sample_count:
        failures.append("expected_sample_count_mismatch")
    if participation.get("expected_requested_output_token_count") != expected_tokens:
        failures.append("expected_requested_output_token_count_mismatch")
    if participation.get("expected_effective_max_tokens") != expected_max_tokens:
        failures.append("expected_effective_max_tokens_mismatch")
    if participation.get("expected_split_id") != expected_split:
        failures.append("expected_split_id_mismatch")

    speedup = (
        tpot.get("paired_speedup", {}).get("median")
        if isinstance(tpot.get("paired_speedup"), dict)
        else None
    )
    launch_count = (
        participation.get("row_summary", {}).get("counters", {}).get("launch_count")
        if isinstance(participation.get("row_summary"), dict)
        else None
    )
    expected_launch_count = participation.get("expected_launch_count")
    if expected_launch_count != 5120:
        failures.append("participation_expected_launch_count_mismatch")
    if launch_count != expected_launch_count:
        failures.append("participation_launch_count_mismatch")
    passed = not failures
    return {
        "artifact_kind": ARTIFACT_KIND,
        "summary_name": SUMMARY_NAME,
        "passed": passed,
        "failures": failures,
        "tpot_artifact": str(tpot_json),
        "participation_artifact": str(participation_json),
        "combined_evidence_ready": passed,
        "tpot_gate_passed": tpot.get("passed") is True,
        "participation_gate_passed": participation.get("passed") is True,
        "performance_claim_strength": (
            "weak_positive_with_separate_participation_evidence"
            if passed
            else "not_supported"
        ),
        "performance_claim_scope": "counter_off_endpoint_or_chunk_tpot_only",
        "paired_tpot_median_speedup": speedup,
        "candidate_positive_all_repeats": tpot.get("candidate_positive_all_repeats"),
        "tail_latency_claim_supported": False,
        "endpoint_or_chunk_tpot_only": True,
        "diagnostic_participation_counter_path": True,
        "runtime_participation_counters_available_in_tpot_run": False,
        "participation_launch_count": launch_count,
        "participation_expected_launch_count": expected_launch_count,
        "single_field": tpot_field,
        "payload_bytes": 0,
        "prepared_table_path_enabled": False,
        "claim_boundary": (
            "Combined evidence only: counter-off paired endpoint/chunk TPOT is "
            "weak-positive, and a separate detailed diagnostic run proves "
            "assignment-variant participation. This is not a p95/p99 claim and "
            "not a future typed-table/current WNA16 ABI replacement claim."
        ),
        "next_runtime_stage": (
            "build_native_typed_slot_consumer_variant_or_rerun_clean_sample_tail_pair"
            if passed
            else "fix_assignment_variant_evidence_bundle"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tpot-json", type=Path, default=DEFAULT_TPOT_JSON)
    parser.add_argument("--participation-json", type=Path, default=DEFAULT_PARTICIPATION_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tpot_json = _resolve(args.tpot_json)
    participation_json = _resolve(args.participation_json)
    bundle = build_bundle(
        tpot=_load_json(tpot_json),
        participation=_load_json(participation_json),
        tpot_json=tpot_json,
        participation_json=participation_json,
    )
    output_json = _resolve(args.output_json)
    _write_json(output_json, bundle)
    print(json.dumps(bundle, indent=2, sort_keys=True))
    if args.require_pass and not bundle["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
