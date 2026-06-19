#!/usr/bin/env python3
"""Summarize detailed participation counters for the assignment-kernel variant.

This gate is deliberately separate from TPOT.  The detailed counter path is
diagnostic-only and can perturb performance, but it proves that the
config-enabled assignment variant actually reaches the live mutation /
single-field replacement counters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "awq_telemetry_ladder"
    / "gpu1_production_batch_gpu_assignment_kernel_variant_detailed_smoke32_20260611"
    / "results.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_assignment_variant_participation_smoke32_v1.json"
)
DEFAULT_MODE = "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_detailed"

ARTIFACT_KIND = "future_wna16_assignment_variant_participation_summary"
SUMMARY_NAME = "future_wna16_assignment_variant_participation_smoke32_v1"


REQUIRED_TRUE_FIELDS = (
    "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_live_consumer_connected",
    "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_producer_gpu_assignment_envelope_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_dry_run_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
)
REQUIRED_FALSE_FIELDS = (
    "runtime_shadow_enabled",
    "runtime_shadow_record_router_topk",
    "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_allow_signature_mismatch_live",
)
REQUIRED_EQUAL_FIELDS: dict[str, Any] = {
    "runtime_shadow_premap_kernel_arg_handoff_live_counter_mode": "detailed",
    "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_field": "B_scale",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_candidate_source": "original_kernel_arg_identity",
}


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
        rows = payload["results"]
    else:
        raise ValueError(f"Unsupported results shape: {path}")
    return [row for row in rows if isinstance(row, dict)]


def _int_value(value: Any) -> int | None:
    if type(value) is not int:
        return None
    return value


def _required_counter(perf: dict[str, Any], name: str, failures: list[str]) -> int:
    value = _int_value(perf.get(name))
    if value is None:
        failures.append(f"counter_{name}_missing_or_invalid")
        return 0
    return int(value)


def _check_perf_fields(perf: dict[str, Any], failures: list[str]) -> None:
    for key in REQUIRED_TRUE_FIELDS:
        if perf.get(key) is not True:
            failures.append(f"performance_{key}_not_true")
    for key in REQUIRED_FALSE_FIELDS:
        if perf.get(key) is not False:
            failures.append(f"performance_{key}_not_false")
    for key, expected in REQUIRED_EQUAL_FIELDS.items():
        if perf.get(key) != expected:
            failures.append(f"performance_{key}_mismatch")


def _validate_row(
    row: dict[str, Any],
    *,
    mode: str,
    expected_sample_count: int,
    expected_requested_output_token_count: int,
    expected_effective_max_tokens: int,
    expected_split_id: str | None,
    expected_launch_count: int,
    failures: list[str],
) -> dict[str, Any]:
    if row.get("mode") != mode:
        failures.append("mode_mismatch")
    if _int_value(row.get("returncode")) != 0:
        failures.append("returncode_nonzero")
    if _int_value(row.get("sample_count")) != expected_sample_count:
        failures.append("sample_count_mismatch")
    if _int_value(row.get("requested_output_token_count")) != expected_requested_output_token_count:
        failures.append("requested_output_token_count_mismatch")
    if _int_value(row.get("effective_max_tokens")) != expected_effective_max_tokens:
        failures.append("effective_max_tokens_mismatch")
    if expected_split_id is not None and row.get("split_id") != expected_split_id:
        failures.append("split_id_mismatch")

    trace_dir_raw = row.get("trace_dir")
    if not isinstance(trace_dir_raw, str) or not trace_dir_raw:
        failures.append("trace_dir_missing")
        return {"performance_summary_checked": False, "counters": {}}
    trace_dir = _resolve(trace_dir_raw)
    perf_path = trace_dir / "performance_summary.json"
    if not perf_path.exists():
        failures.append("performance_summary_missing")
        return {"performance_summary_checked": False, "counters": {}}
    perf = _load_json(perf_path)
    if not isinstance(perf, dict):
        failures.append("performance_summary_not_object")
        return {"performance_summary_checked": False, "counters": {}}
    _check_perf_fields(perf, failures)

    launch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_launch_count",
        failures,
    )
    fallback = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_fallback_count",
        failures,
    )
    identity_blocked = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_kernel_variant_identity_blocked_count",
        failures,
    )
    envelope_seen = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_envelope_seen_count",
        failures,
    )
    producer_envelope = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_gpu_assignment_envelope_count",
        failures,
    )
    package_seen = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_seen_count",
        failures,
    )
    package_future_typed = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_future_wna16_typed_slot_envelope_count",
        failures,
    )
    package_minimal_identity = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_minimal_identity_envelope_count",
        failures,
    )
    package_producer_minimal = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_producer_minimal_identity_envelope_count",
        failures,
    )
    package_missing = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_missing_count",
        failures,
    )
    package_pass_through = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_pass_through_count",
        failures,
    )
    package_block_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_block_reason_mismatch_count",
        failures,
    )
    package_layer_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_layer_mismatch_count",
        failures,
    )
    package_cache_hit = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_cache_hit_count",
        failures,
    )
    package_cache_miss = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_package_cache_miss_count",
        failures,
    )
    expert_attached = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_attached_count",
        failures,
    )
    expert_ok = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_identity_ok_count",
        failures,
    )
    expert_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_identity_mismatch_count",
        failures,
    )
    expert_missing = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_expert_ids_missing_count",
        failures,
    )
    sorted_attached = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_attached_count",
        failures,
    )
    sorted_ok = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_identity_ok_count",
        failures,
    )
    sorted_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_identity_mismatch_count",
        failures,
    )
    sorted_missing = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_sorted_token_ids_missing_count",
        failures,
    )
    padded_attached = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_attached_count",
        failures,
    )
    padded_ok = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_identity_ok_count",
        failures,
    )
    padded_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_identity_mismatch_count",
        failures,
    )
    padded_missing = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_gpu_assignment_num_tokens_post_padded_missing_count",
        failures,
    )
    dry_candidate = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_candidate_count",
        failures,
    )
    dry_ok = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_ok_count",
        failures,
    )
    dry_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_parity_mismatch_count",
        failures,
    )
    dry_passed = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_passed_to_kernel_count",
        failures,
    )
    dry_payload = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_payload_bytes",
        failures,
    )
    dry_source_missing = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_source_missing_count",
        failures,
    )
    dry_unsupported = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_dry_run_unsupported_field_count",
        failures,
    )
    live_candidate = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_candidate_count",
        failures,
    )
    live_ok = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_ok_count",
        failures,
    )
    live_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_parity_mismatch_count",
        failures,
    )
    live_passed = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_passed_to_kernel_count",
        failures,
    )
    live_replaced = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_replaced_count",
        failures,
    )
    live_disabled = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_disabled_count",
        failures,
    )
    live_payload = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_payload_bytes",
        failures,
    )
    live_signature_allowed = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_signature_mismatch_allowed_count",
        failures,
    )
    live_signature_blocked = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_signature_mismatch_blocked_count",
        failures,
    )
    live_source_missing = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_source_missing_fallback_count",
        failures,
    )
    live_type_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_live_type_mismatch_fallback_count",
        failures,
    )
    prepared_source = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_count",
        failures,
    )
    prepared_hit = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_hit_count",
        failures,
    )
    prepared_miss = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_miss_count",
        failures,
    )
    prepared_type_compatible = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_type_compatible_count",
        failures,
    )
    prepared_type_mismatch = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_prepared_table_type_mismatch_count",
        failures,
    )
    original_source = _required_counter(
        perf,
        "runtime_shadow_premap_kernel_arg_live_mutation_single_field_replacement_candidate_source_original_count",
        failures,
    )

    if launch != expected_launch_count:
        failures.append("launch_count_mismatch")
    if not (launch == envelope_seen == expert_ok == sorted_ok == padded_ok):
        failures.append("gpu_assignment_identity_counter_mismatch")
    if not (producer_envelope == expert_attached == sorted_attached == padded_attached):
        failures.append("gpu_assignment_attached_counter_mismatch")
    if producer_envelope * 2 != launch:
        failures.append("gpu_assignment_launch_to_attached_ratio_mismatch")
    if package_seen != launch:
        failures.append("package_seen_launch_mismatch")
    if package_future_typed != producer_envelope:
        failures.append("package_future_typed_envelope_mismatch")
    if (
        package_minimal_identity != 0
        or package_producer_minimal != 0
        or package_missing != 0
        or package_pass_through != 0
        or package_block_mismatch != 0
        or package_layer_mismatch != 0
        or package_cache_hit != 0
        or package_cache_miss != 0
    ):
        failures.append("package_zero_counter_violation")
    if fallback != 0 or identity_blocked != 0:
        failures.append("gpu_assignment_fallback_or_blocked_nonzero")
    if expert_mismatch != 0 or sorted_mismatch != 0 or padded_mismatch != 0:
        failures.append("gpu_assignment_identity_mismatch_nonzero")
    if expert_missing != 0 or sorted_missing != 0 or padded_missing != 0:
        failures.append("gpu_assignment_missing_nonzero")
    if not (dry_candidate == dry_ok == launch):
        failures.append("single_field_dry_run_counter_mismatch")
    if (
        dry_mismatch != 0
        or dry_passed != 0
        or dry_payload != 0
        or dry_source_missing != 0
        or dry_unsupported != 0
    ):
        failures.append("single_field_dry_run_zero_counter_violation")
    if not (live_candidate == live_ok == live_passed == live_replaced == launch):
        failures.append("single_field_live_counter_mismatch")
    if (
        live_mismatch != 0
        or live_disabled != 0
        or live_payload != 0
        or live_signature_allowed != 0
        or live_signature_blocked != 0
        or live_source_missing != 0
        or live_type_mismatch != 0
    ):
        failures.append("single_field_live_zero_counter_violation")
    if (
        prepared_source != 0
        or prepared_hit != 0
        or prepared_miss != 0
        or prepared_type_compatible != 0
        or prepared_type_mismatch != 0
    ):
        failures.append("prepared_table_source_nonzero")
    if original_source != launch:
        failures.append("original_source_counter_mismatch")

    counters = {
        "launch_count": launch,
        "expected_launch_count": expected_launch_count,
        "fallback_count": fallback,
        "identity_blocked_count": identity_blocked,
        "envelope_seen_count": envelope_seen,
        "producer_gpu_assignment_envelope_count": producer_envelope,
        "package_seen_count": package_seen,
        "package_producer_future_wna16_typed_slot_envelope_count": package_future_typed,
        "package_minimal_identity_envelope_count": package_minimal_identity,
        "package_producer_minimal_identity_envelope_count": package_producer_minimal,
        "package_missing_count": package_missing,
        "package_pass_through_count": package_pass_through,
        "package_block_reason_mismatch_count": package_block_mismatch,
        "package_layer_mismatch_count": package_layer_mismatch,
        "package_cache_hit_count": package_cache_hit,
        "package_cache_miss_count": package_cache_miss,
        "expert_ids_attached_count": expert_attached,
        "expert_ids_identity_ok_count": expert_ok,
        "expert_ids_missing_count": expert_missing,
        "sorted_token_ids_attached_count": sorted_attached,
        "sorted_token_ids_identity_ok_count": sorted_ok,
        "sorted_token_ids_missing_count": sorted_missing,
        "num_tokens_post_padded_attached_count": padded_attached,
        "num_tokens_post_padded_identity_ok_count": padded_ok,
        "num_tokens_post_padded_missing_count": padded_missing,
        "single_field_dry_run_candidate_count": dry_candidate,
        "single_field_dry_run_parity_ok_count": dry_ok,
        "single_field_dry_run_parity_mismatch_count": dry_mismatch,
        "single_field_dry_run_passed_to_kernel_count": dry_passed,
        "single_field_dry_run_payload_bytes": dry_payload,
        "single_field_dry_run_source_missing_count": dry_source_missing,
        "single_field_dry_run_unsupported_field_count": dry_unsupported,
        "single_field_live_candidate_count": live_candidate,
        "single_field_live_parity_ok_count": live_ok,
        "single_field_live_parity_mismatch_count": live_mismatch,
        "single_field_live_passed_to_kernel_count": live_passed,
        "single_field_live_disabled_count": live_disabled,
        "single_field_live_replaced_count": live_replaced,
        "single_field_live_payload_bytes": live_payload,
        "single_field_live_signature_mismatch_allowed_count": live_signature_allowed,
        "single_field_live_signature_mismatch_blocked_count": live_signature_blocked,
        "single_field_live_source_missing_fallback_count": live_source_missing,
        "single_field_live_type_mismatch_fallback_count": live_type_mismatch,
        "prepared_table_candidate_source_count": prepared_source,
        "prepared_table_candidate_source_hit_count": prepared_hit,
        "prepared_table_candidate_source_miss_count": prepared_miss,
        "prepared_table_candidate_source_type_compatible_count": prepared_type_compatible,
        "prepared_table_candidate_source_type_mismatch_count": prepared_type_mismatch,
        "original_candidate_source_count": original_source,
    }
    return {
        "performance_summary_checked": True,
        "performance_summary_path": str(perf_path),
        "trace_dir": str(trace_dir),
        "counters": counters,
    }


def build_summary(
    rows: list[dict[str, Any]],
    *,
    results_json: Path,
    mode: str = DEFAULT_MODE,
    expected_sample_count: int = 32,
    expected_requested_output_token_count: int = 2048,
    expected_effective_max_tokens: int = 64,
    expected_split_id: str | None = "external_prompt_gate_dolly_32_gen64_utilization",
    expected_launch_count: int = 5120,
) -> dict[str, Any]:
    failures: list[str] = []
    matching = [row for row in rows if row.get("mode") == mode]
    if len(matching) != 1:
        failures.append("expected_exactly_one_matching_row")
    row = matching[0] if matching else {}
    row_summary = (
        _validate_row(
            row,
            mode=mode,
            expected_sample_count=expected_sample_count,
            expected_requested_output_token_count=expected_requested_output_token_count,
            expected_effective_max_tokens=expected_effective_max_tokens,
            expected_split_id=expected_split_id,
            expected_launch_count=expected_launch_count,
            failures=failures,
        )
        if matching
        else {"performance_summary_checked": False, "counters": {}}
    )
    passed = not failures
    return {
        "artifact_kind": ARTIFACT_KIND,
        "summary_name": SUMMARY_NAME,
        "results_json": str(results_json),
        "mode": mode,
        "passed": passed,
        "failures": failures,
        "participation_gate_ready": passed,
        "performance_claim": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "diagnostic_counter_path": True,
        "counter_mode": "detailed",
        "payload_bytes": 0,
        "prepared_table_path_enabled": False,
        "future_typed_slot_kernel_variant_enabled": False,
        "gpu_assignment_kernel_variant_participated": bool(
            row_summary.get("counters", {}).get("launch_count", 0) == expected_launch_count
        ),
        "single_field_replacement_live_participated": bool(
            row_summary.get("counters", {}).get("single_field_live_replaced_count", 0)
            == expected_launch_count
        ),
        "single_field": "B_scale",
        "row_summary": row_summary,
        "expected_sample_count": expected_sample_count,
        "expected_requested_output_token_count": expected_requested_output_token_count,
        "expected_effective_max_tokens": expected_effective_max_tokens,
        "expected_split_id": expected_split_id,
        "expected_launch_count": expected_launch_count,
        "claim_boundary": (
            "Diagnostic participation evidence only.  This proves detailed "
            "counters were exercised; it is not a TPOT or p95/p99 performance "
            "claim and it does not enable the prepared-table typed-slot path."
        ),
        "next_runtime_stage": (
            "combine_with_counter_off_tpot_gate_or_build_native_typed_slot_consumer_variant"
            if passed
            else "fix_participation_counter_gate_failures"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--mode", default=DEFAULT_MODE)
    parser.add_argument("--expected-sample-count", type=int, default=32)
    parser.add_argument("--expected-requested-output-token-count", type=int, default=2048)
    parser.add_argument("--expected-effective-max-tokens", type=int, default=64)
    parser.add_argument(
        "--expected-split-id",
        default="external_prompt_gate_dolly_32_gen64_utilization",
    )
    parser.add_argument("--expected-launch-count", type=int, default=5120)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results_json = _resolve(args.results_json)
    summary = build_summary(
        _load_rows(results_json),
        results_json=results_json,
        mode=args.mode,
        expected_sample_count=args.expected_sample_count,
        expected_requested_output_token_count=args.expected_requested_output_token_count,
        expected_effective_max_tokens=args.expected_effective_max_tokens,
        expected_split_id=args.expected_split_id,
        expected_launch_count=args.expected_launch_count,
    )
    output_json = _resolve(args.output_json)
    _write_json(output_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.require_pass and not summary["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
