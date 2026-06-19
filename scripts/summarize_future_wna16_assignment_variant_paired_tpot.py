#!/usr/bin/env python3
"""Build a strict paired TPOT summary for the future-WNA16 assignment variant.

The input is an existing ``run_awq_telemetry_ladder.py`` ``results.json``.
This helper intentionally does not launch vLLM.  It verifies that the baseline
and candidate rows are paired by repeat, checks production-like telemetry
boundaries from each ``performance_summary.json``, and reports only the claim
that the existing live assignment-kernel variant supports.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RESULTS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "awq_telemetry_ladder"
    / "gpu1_assignment_kernel_variant_repeat3_current_20260611"
    / "results.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_assignment_variant_paired_tpot_repeat3_v1.json"
)
DEFAULT_BASELINE_MODE = "production_batch_reuse_llm"
DEFAULT_CANDIDATE_MODE = (
    "production_batch_premap_live_future_wna16_gpu_assignment_kernel_variant_"
    "counter_off_reuse_llm"
)

ARTIFACT_KIND = "future_wna16_assignment_variant_paired_tpot_summary"
SUMMARY_NAME = "future_wna16_assignment_variant_paired_tpot_repeat3_v1"
BENCHMARK_SCOPE = "existing_telemetry_ladder_paired_repeat_summary"

COMMON_FALSE_PERF_FIELDS = (
    "decode_workload_trace_enabled",
    "runtime_shadow_enabled",
    "runtime_shadow_record_router_topk",
    "runtime_shadow_emit_decoder_layer_timing",
    "runtime_shadow_emit_decoder_component_timing",
    "runtime_shadow_emit_moe_substage_timing",
    "runtime_shadow_emit_engine_timing",
    "runtime_shadow_emit_wna16_kernel_timing",
    "runtime_shadow_emit_premap_summaries",
    "runtime_shadow_emit_premap_consumer_mapping",
    "runtime_shadow_premap_kernel_arg_handoff_future_wna16_typed_slot_kernel_variant_enabled",
)
COMMON_EQUAL_PERF_FIELDS = {
    "runtime_shadow_decoder_source_timing_mode": "off",
    "runtime_shadow_moe_source_timing_mode": "off",
    "runtime_shadow_outcome_logging_mode": "off",
    "runtime_shadow_premap_kernel_arg_handoff_prepared_table_materialization_mode": "off",
}
BASELINE_FALSE_PERF_FIELDS = (
    "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
)
CANDIDATE_TRUE_PERF_FIELDS = (
    "runtime_shadow_premap_kernel_arg_handoff_live_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_kernel_arg_pass_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_real_kernel_arg_mutation_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_gpu_assignment_kernel_variant_enabled",
    "runtime_shadow_premap_kernel_arg_handoff_single_field_replacement_live_enabled",
)
CANDIDATE_EQUAL_PERF_FIELDS = {
    "runtime_shadow_premap_kernel_arg_handoff_live_counter_mode": "off",
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


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_timing_tpots(
    trace_dir: Path,
    failures: list[str],
    *,
    prefix: str,
    scope: str,
) -> list[float]:
    path = trace_dir / "sample_timing.jsonl"
    if not path.exists():
        return []
    values: list[float] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                failures.append(f"{prefix}_sample_timing_invalid_json:{line_no}")
                continue
            if not isinstance(row, dict) or row.get("scope") != scope:
                continue
            if row.get("status", "ok") != "ok":
                failures.append(f"{prefix}_sample_timing_bad_status:{line_no}")
                continue
            tokens = _int_value(row.get("requested_output_tokens"))
            elapsed_us = _finite_float(row.get("generate_elapsed_us"))
            if tokens is None or tokens <= 0 or elapsed_us is None or elapsed_us <= 0:
                failures.append(f"{prefix}_sample_timing_bad_value:{line_no}")
                continue
            values.append((elapsed_us / 1_000_000.0) / float(tokens))
    return values


def _nearest_rank(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def _stats(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "values": ordered,
        "median": statistics.median(ordered),
        "mean": statistics.mean(ordered),
        "min": min(ordered),
        "max": max(ordered),
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
    }


def _tail_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"available": False, "count": 0}
    return {
        "available": True,
        "count": len(values),
        "p50": _nearest_rank(values, 0.50),
        "p95": _nearest_rank(values, 0.95),
        "p99": _nearest_rank(values, 0.99),
        "min": min(values),
        "max": max(values),
    }


def _check_perf(
    perf: dict[str, Any],
    failures: list[str],
    *,
    role: str,
) -> None:
    for key in COMMON_FALSE_PERF_FIELDS:
        if perf.get(key) is not False:
            failures.append(f"{role}_performance_{key}_not_false")
    for key, expected in COMMON_EQUAL_PERF_FIELDS.items():
        if perf.get(key) != expected:
            failures.append(f"{role}_performance_{key}_mismatch")

    if role == "baseline":
        for key in BASELINE_FALSE_PERF_FIELDS:
            if perf.get(key) is not False:
                failures.append(f"{role}_performance_{key}_not_false")
    elif role == "candidate":
        for key in CANDIDATE_TRUE_PERF_FIELDS:
            if perf.get(key) is not True:
                failures.append(f"{role}_performance_{key}_not_true")
        for key, expected in CANDIDATE_EQUAL_PERF_FIELDS.items():
            if perf.get(key) != expected:
                failures.append(f"{role}_performance_{key}_mismatch")
    else:
        raise ValueError(f"unknown role: {role}")


def _close_enough(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1.0e-9, abs_tol=1.0e-12)


def _index_mode_rows(
    rows: list[dict[str, Any]],
    *,
    mode: str,
    role: str,
    failures: list[str],
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row.get("mode") != mode:
            continue
        repeat = _int_value(row.get("repeat"))
        if repeat is None:
            failures.append(f"{role}_repeat_invalid")
            continue
        if repeat in indexed:
            failures.append(f"{role}_repeat_duplicate:{repeat}")
            continue
        indexed[repeat] = row
    if not indexed:
        failures.append(f"{role}_mode_missing")
    return indexed


def _validate_row(
    row: dict[str, Any],
    *,
    role: str,
    repeat: int,
    failures: list[str],
) -> dict[str, Any]:
    row_failures: list[str] = []
    if _int_value(row.get("returncode")) != 0:
        row_failures.append(f"{role}_returncode_nonzero:{repeat}")
    tpot = _finite_float(row.get("generate_seconds_per_requested_output_token"))
    generate_wall = _finite_float(row.get("generate_wall_seconds"))
    sample_count = _int_value(row.get("sample_count"))
    token_count = _int_value(row.get("requested_output_token_count"))
    if tpot is None or tpot <= 0:
        row_failures.append(f"{role}_tpot_invalid:{repeat}")
    if generate_wall is None or generate_wall <= 0:
        row_failures.append(f"{role}_generate_wall_invalid:{repeat}")
    if sample_count is None or sample_count <= 0:
        row_failures.append(f"{role}_sample_count_invalid:{repeat}")
    if token_count is None or token_count <= 0:
        row_failures.append(f"{role}_requested_output_token_count_invalid:{repeat}")

    trace_dir_raw = row.get("trace_dir")
    trace_dir = _resolve(trace_dir_raw) if isinstance(trace_dir_raw, str) else None
    perf: dict[str, Any] = {}
    if trace_dir is None:
        row_failures.append(f"{role}_trace_dir_missing:{repeat}")
    else:
        perf_path = trace_dir / "performance_summary.json"
        if not perf_path.exists():
            row_failures.append(f"{role}_performance_summary_missing:{repeat}")
        else:
            loaded = _load_json(perf_path)
            if not isinstance(loaded, dict):
                row_failures.append(f"{role}_performance_summary_not_object:{repeat}")
            else:
                perf = loaded
                _check_perf(perf, row_failures, role=role)
                perf_tpot = _finite_float(
                    perf.get("generate_seconds_per_requested_output_token")
                )
                perf_wall = _finite_float(perf.get("generate_wall_seconds"))
                perf_sample_count = _int_value(perf.get("sample_count"))
                perf_token_count = _int_value(perf.get("requested_output_token_count"))
                if perf_tpot is None:
                    row_failures.append(f"{role}_performance_tpot_missing_or_invalid:{repeat}")
                elif tpot is not None and not _close_enough(tpot, perf_tpot):
                    row_failures.append(f"{role}_row_perf_tpot_mismatch:{repeat}")
                if perf_wall is None:
                    row_failures.append(f"{role}_performance_generate_wall_missing_or_invalid:{repeat}")
                elif generate_wall is not None and not _close_enough(generate_wall, perf_wall):
                    row_failures.append(f"{role}_row_perf_generate_wall_mismatch:{repeat}")
                if sample_count is not None and perf_sample_count != sample_count:
                    row_failures.append(f"{role}_row_perf_sample_count_mismatch:{repeat}")
                if token_count is not None and perf_token_count != token_count:
                    row_failures.append(f"{role}_row_perf_requested_token_count_mismatch:{repeat}")

    sample_tpots = _read_timing_tpots(
        trace_dir if trace_dir is not None else Path("."),
        row_failures,
        prefix=f"{role}_repeat_{repeat}",
        scope="sample",
    )
    chunk_tpots = _read_timing_tpots(
        trace_dir if trace_dir is not None else Path("."),
        row_failures,
        prefix=f"{role}_repeat_{repeat}",
        scope="chunk",
    )
    if chunk_tpots and tpot is not None and not all(_close_enough(tpot, value) for value in chunk_tpots):
        row_failures.append(f"{role}_chunk_timing_tpot_mismatch:{repeat}")
    failures.extend(row_failures)
    return {
        "repeat": repeat,
        "mode": row.get("mode"),
        "trace_dir": str(trace_dir) if trace_dir is not None else None,
        "tpot": tpot,
        "tokens_per_second": (1.0 / tpot) if tpot and tpot > 0 else None,
        "generate_wall_seconds": generate_wall,
        "sample_count": sample_count,
        "requested_output_token_count": token_count,
        "split_id": row.get("split_id"),
        "effective_max_tokens": row.get("effective_max_tokens"),
        "sample_tpot": _tail_stats(sample_tpots),
        "chunk_tpot": _tail_stats(chunk_tpots),
        "performance_summary_checked": bool(perf),
        "row_failures": row_failures,
    }


def build_summary(
    rows: list[dict[str, Any]],
    *,
    results_json: Path,
    baseline_mode: str = DEFAULT_BASELINE_MODE,
    candidate_mode: str = DEFAULT_CANDIDATE_MODE,
    min_repeats: int = 3,
    expected_sample_count: int = 32,
    expected_requested_output_token_count: int = 2048,
    expected_effective_max_tokens: int = 64,
    expected_split_id: str | None = "external_prompt_gate_dolly_32_gen64_utilization",
    require_positive_all_repeats: bool = True,
    require_sample_tail: bool = False,
    max_allowed_p95_delta_pct: float = 1.0,
    max_allowed_p99_delta_pct: float = 2.0,
) -> dict[str, Any]:
    failures: list[str] = []
    baseline_rows = _index_mode_rows(
        rows,
        mode=baseline_mode,
        role="baseline",
        failures=failures,
    )
    candidate_rows = _index_mode_rows(
        rows,
        mode=candidate_mode,
        role="candidate",
        failures=failures,
    )
    repeats = sorted(set(baseline_rows) & set(candidate_rows))
    missing_baseline = sorted(set(candidate_rows) - set(baseline_rows))
    missing_candidate = sorted(set(baseline_rows) - set(candidate_rows))
    if missing_baseline:
        failures.append(f"baseline_missing_repeats:{missing_baseline}")
    if missing_candidate:
        failures.append(f"candidate_missing_repeats:{missing_candidate}")
    if len(repeats) < int(min_repeats):
        failures.append("insufficient_paired_repeats")

    baseline_runs = [
        _validate_row(baseline_rows[repeat], role="baseline", repeat=repeat, failures=failures)
        for repeat in repeats
    ]
    candidate_runs = [
        _validate_row(candidate_rows[repeat], role="candidate", repeat=repeat, failures=failures)
        for repeat in repeats
    ]

    pair_rows: list[dict[str, Any]] = []
    baseline_tpots: list[float] = []
    candidate_tpots: list[float] = []
    speedups: list[float] = []
    baseline_sample_tpots: list[float] = []
    candidate_sample_tpots: list[float] = []
    baseline_chunk_tpots: list[float] = []
    candidate_chunk_tpots: list[float] = []
    context_pairs: set[tuple[Any, Any, Any, Any, Any, Any, Any, Any]] = set()
    for baseline, candidate in zip(baseline_runs, candidate_runs, strict=True):
        bt = baseline["tpot"]
        ct = candidate["tpot"]
        if isinstance(bt, float) and isinstance(ct, float) and bt > 0 and ct > 0:
            speedup = bt / ct
            improvement_pct = (1.0 - ct / bt) * 100.0
            baseline_tpots.append(bt)
            candidate_tpots.append(ct)
            speedups.append(speedup)
        else:
            speedup = None
            improvement_pct = None
        pair_rows.append(
            {
                "repeat": baseline["repeat"],
                "baseline_tpot": bt,
                "candidate_tpot": ct,
                "speedup": speedup,
                "improvement_pct": improvement_pct,
                "baseline_tokens_per_second": baseline["tokens_per_second"],
                "candidate_tokens_per_second": candidate["tokens_per_second"],
            }
        )
        context_pairs.add(
            (
                baseline.get("sample_count"),
                candidate.get("sample_count"),
                baseline.get("requested_output_token_count"),
                candidate.get("requested_output_token_count"),
                baseline.get("split_id"),
                candidate.get("split_id"),
                baseline.get("effective_max_tokens"),
                candidate.get("effective_max_tokens"),
            )
        )

    for repeat in repeats:
        baseline_trace_dir = _resolve(str(baseline_rows[repeat].get("trace_dir")))
        candidate_trace_dir = _resolve(str(candidate_rows[repeat].get("trace_dir")))
        baseline_sample_tpots.extend(
            _read_timing_tpots(
                baseline_trace_dir,
                failures,
                prefix=f"baseline_repeat_{repeat}_aggregate",
                scope="sample",
            )
        )
        candidate_sample_tpots.extend(
            _read_timing_tpots(
                candidate_trace_dir,
                failures,
                prefix=f"candidate_repeat_{repeat}_aggregate",
                scope="sample",
            )
        )
        baseline_chunk_tpots.extend(
            _read_timing_tpots(
                baseline_trace_dir,
                failures,
                prefix=f"baseline_repeat_{repeat}_chunk_aggregate",
                scope="chunk",
            )
        )
        candidate_chunk_tpots.extend(
            _read_timing_tpots(
                candidate_trace_dir,
                failures,
                prefix=f"candidate_repeat_{repeat}_chunk_aggregate",
                scope="chunk",
            )
        )

    context_consistent = all(
        left_sample == right_sample
        and left_tokens == right_tokens
        and left_split == right_split
        and left_max_tokens == right_max_tokens
        for (
            left_sample,
            right_sample,
            left_tokens,
            right_tokens,
            left_split,
            right_split,
            left_max_tokens,
            right_max_tokens,
        ) in context_pairs
    )
    if not context_consistent:
        failures.append("paired_context_mismatch")
    strict_context_match = all(
        left_sample == expected_sample_count
        and right_sample == expected_sample_count
        and left_tokens == expected_requested_output_token_count
        and right_tokens == expected_requested_output_token_count
        and left_max_tokens == expected_effective_max_tokens
        and right_max_tokens == expected_effective_max_tokens
        and (
            expected_split_id is None
            or (left_split == expected_split_id and right_split == expected_split_id)
        )
        for (
            left_sample,
            right_sample,
            left_tokens,
            right_tokens,
            left_split,
            right_split,
            left_max_tokens,
            right_max_tokens,
        ) in context_pairs
    )
    if not strict_context_match:
        failures.append("strict_context_mismatch")

    if not baseline_tpots or not candidate_tpots or len(speedups) != len(repeats):
        failures.append("paired_tpot_values_incomplete")

    baseline_stats = _stats(baseline_tpots) if baseline_tpots else {"count": 0}
    candidate_stats = _stats(candidate_tpots) if candidate_tpots else {"count": 0}
    speedup_stats = _stats(speedups) if speedups else {"count": 0}
    candidate_positive_all = bool(speedups) and all(value > 1.0 for value in speedups)
    if require_positive_all_repeats and not candidate_positive_all:
        failures.append("candidate_not_positive_all_repeats")

    baseline_tail = _tail_stats(baseline_sample_tpots)
    candidate_tail = _tail_stats(candidate_sample_tpots)
    baseline_chunk = _tail_stats(baseline_chunk_tpots)
    candidate_chunk = _tail_stats(candidate_chunk_tpots)
    p95_delta_pct = None
    p99_delta_pct = None
    sample_tail_available = bool(baseline_tail["available"] and candidate_tail["available"])
    tail_gate_pass = None
    if baseline_tail["available"] and candidate_tail["available"]:
        p95_delta_pct = (
            float(candidate_tail["p95"]) / float(baseline_tail["p95"]) - 1.0
        ) * 100.0
        p99_delta_pct = (
            float(candidate_tail["p99"]) / float(baseline_tail["p99"]) - 1.0
        ) * 100.0
        tail_gate_pass = (
            p95_delta_pct <= float(max_allowed_p95_delta_pct)
            and p99_delta_pct <= float(max_allowed_p99_delta_pct)
        )
    if sample_tail_available and not tail_gate_pass:
        failures.append("sample_tail_gate_failed")
    if require_sample_tail and not sample_tail_available:
        failures.append("sample_tail_required_but_unavailable")

    passed = not failures
    performance_claim_strength = (
        "weak_positive_existing_repeat3"
        if passed and float(speedup_stats["median"]) < 1.01
        else ("positive_existing_repeat3" if passed else "not_supported")
    )
    return {
        "artifact_kind": ARTIFACT_KIND,
        "summary_name": SUMMARY_NAME,
        "benchmark_scope": BENCHMARK_SCOPE,
        "results_json": str(results_json),
        "baseline_mode": baseline_mode,
        "candidate_mode": candidate_mode,
        "min_repeats": int(min_repeats),
        "expected_sample_count": int(expected_sample_count),
        "expected_requested_output_token_count": int(expected_requested_output_token_count),
        "expected_effective_max_tokens": int(expected_effective_max_tokens),
        "expected_split_id": expected_split_id,
        "repeat_count": len(repeats),
        "paired_repeats": repeats,
        "passed": passed,
        "failures": failures,
        "measures_tpot": True,
        "measures_vllm_latency": True,
        "uses_existing_results_only": True,
        "requires_new_gpu_run": False,
        "benchmark_is_current_vllm_baseline": False,
        "benchmark_is_future_assignment_variant_config_enabled_path": True,
        "benchmark_is_future_typed_slot_useful_path": False,
        "current_wna16_fused_moe_arg_reinterpretation": False,
        "prepared_table_path_enabled": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "candidate_enables_live_kernel_arg_handoff": True,
        "candidate_enables_gpu_assignment_kernel_variant": True,
        "candidate_enables_single_field_replacement_live": True,
        "candidate_runtime_participation_counters_available": False,
        "candidate_single_field": "B_scale",
        "claim_boundary": (
            "Existing paired endpoint/chunk TPOT summary for a config-enabled "
            "GPU assignment-kernel variant. Runtime participation counters are "
            "not available in this counter-off artifact. This is not a "
            "prepared-table path and not a current WNA16 fused-MoE typed-table "
            "replacement claim."
        ),
        "endpoint_or_chunk_tpot_only": True,
        "tail_latency_claim_supported": bool(sample_tail_available and tail_gate_pass is True),
        "performance_claim_strength": performance_claim_strength,
        "candidate_positive_all_repeats": candidate_positive_all,
        "max_allowed_p95_delta_pct": float(max_allowed_p95_delta_pct),
        "max_allowed_p99_delta_pct": float(max_allowed_p99_delta_pct),
        "sample_tail_available": sample_tail_available,
        "sample_tail_required": bool(require_sample_tail),
        "sample_tail_gate_pass": tail_gate_pass,
        "sample_tail_p95_delta_pct": p95_delta_pct,
        "sample_tail_p99_delta_pct": p99_delta_pct,
        "baseline_chunk_tpot": baseline_chunk,
        "candidate_chunk_tpot": candidate_chunk,
        "baseline_tpot": baseline_stats,
        "candidate_tpot": candidate_stats,
        "paired_speedup": speedup_stats,
        "pair_rows": pair_rows,
        "baseline_sample_tpot": baseline_tail,
        "candidate_sample_tpot": candidate_tail,
        "baseline_runs": baseline_runs,
        "candidate_runs": candidate_runs,
        "context_consistent": context_consistent,
        "strict_context_match": strict_context_match,
        "next_runtime_stage": (
            "rerun_clean_paired_repeat_or_build_native_typed_slot_consumer_variant"
            if passed
            else "fix_paired_tpot_gate_failures"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--baseline-mode", default=DEFAULT_BASELINE_MODE)
    parser.add_argument("--candidate-mode", default=DEFAULT_CANDIDATE_MODE)
    parser.add_argument("--min-repeats", type=int, default=3)
    parser.add_argument("--expected-sample-count", type=int, default=32)
    parser.add_argument("--expected-requested-output-token-count", type=int, default=2048)
    parser.add_argument("--expected-effective-max-tokens", type=int, default=64)
    parser.add_argument(
        "--expected-split-id",
        default="external_prompt_gate_dolly_32_gen64_utilization",
    )
    parser.add_argument("--max-allowed-p95-delta-pct", type=float, default=1.0)
    parser.add_argument("--max-allowed-p99-delta-pct", type=float, default=2.0)
    parser.add_argument("--require-sample-tail", action="store_true")
    parser.add_argument(
        "--allow-nonpositive-repeat",
        action="store_true",
        help="Do not require every paired repeat to improve candidate TPOT.",
    )
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results_json = _resolve(args.results_json)
    summary = build_summary(
        _load_rows(results_json),
        results_json=results_json,
        baseline_mode=args.baseline_mode,
        candidate_mode=args.candidate_mode,
        min_repeats=args.min_repeats,
        expected_sample_count=args.expected_sample_count,
        expected_requested_output_token_count=args.expected_requested_output_token_count,
        expected_effective_max_tokens=args.expected_effective_max_tokens,
        expected_split_id=args.expected_split_id,
        require_positive_all_repeats=not args.allow_nonpositive_repeat,
        require_sample_tail=args.require_sample_tail,
        max_allowed_p95_delta_pct=args.max_allowed_p95_delta_pct,
        max_allowed_p99_delta_pct=args.max_allowed_p99_delta_pct,
    )
    output_json = _resolve(args.output_json)
    _write_json(output_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.require_pass and not summary["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
