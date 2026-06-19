#!/usr/bin/env python3
"""Compare production-like baseline TPOT against a future payloadless useful path.

This helper does not launch vLLM.  It consumes two TPOT artifacts:

* a baseline artifact produced by
  ``run_future_wna16_typed_slot_payloadless_useful_production_like_tpot_benchmark.py``;
* a future candidate artifact that explicitly enables the payloadless useful
  typed-slot path.

The comparison is intentionally strict.  Missing candidate evidence is a failed
gate, not an implicit performance claim.  The safety boundary remains
payloadless: no payload dereference, no kernel argument pass, and no current
WNA16 fused-MoE argument reinterpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASELINE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_production_like_tpot_baseline_dolly32_gen64_graph_v1.json"
)
DEFAULT_CANDIDATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_production_like_tpot_candidate_dolly32_gen64_graph_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "production_like_tpot"
    / "future_wna16_typed_slot_payloadless_useful_ab_comparison_v1.json"
)

ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_ab_comparison"
COMPARISON_NAME = "premap_future_wna16_typed_slot_payloadless_useful_ab_comparison_v1"
COMPARISON_MODE = "production_like_payloadless_useful_candidate_vs_baseline"
COMPARISON_SOURCE = "premap_future_wna16_typed_slot_payloadless_useful_production_like_tpot_baseline_v1"
NEXT_RUNTIME_STAGE = "run_payloadless_useful_candidate_or_promote_to_real_wna16_typed_slot_path"

TPOT_ARTIFACT_KIND = "future_wna16_typed_slot_payloadless_useful_production_like_tpot_benchmark"

COMMON_FALSE_FIELDS = (
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "current_wna16_arg_compatible",
    "requires_wna16_arg_reinterpretation",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        parsed = int(value)
    else:
        return None
    return parsed if parsed > 0 else None


def _nonempty_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _check_common_artifact(
    artifact: dict[str, Any],
    failures: list[str],
    *,
    role: str,
) -> dict[str, Any]:
    if artifact.get("artifact_kind") != TPOT_ARTIFACT_KIND:
        failures.append(f"{role}_artifact_kind_mismatch")
    if artifact.get("passed") is not True:
        failures.append(f"{role}_passed_not_true")
    if artifact.get("failures") != []:
        failures.append(f"{role}_failures_not_empty")
    if artifact.get("measures_tpot") is not True:
        failures.append(f"{role}_measures_tpot_not_true")
    if artifact.get("measures_vllm_latency") is not True:
        failures.append(f"{role}_measures_vllm_latency_not_true")
    if artifact.get("payload_bytes") != 0:
        failures.append(f"{role}_payload_bytes_not_zero")
    for key in COMMON_FALSE_FIELDS:
        if artifact.get(key) is not False:
            failures.append(f"{role}_{key}_not_false")

    tpot = _finite_float(artifact.get("generate_seconds_per_requested_output_token"))
    generate_wall = _finite_float(artifact.get("generate_wall_seconds"))
    tokens_per_second = _finite_float(artifact.get("tokens_per_second"))
    sample_count = _positive_int(artifact.get("sample_count"))
    requested_tokens = _positive_int(artifact.get("requested_output_token_count"))
    input_tokens = _positive_int(artifact.get("input_token_count"))
    if tpot is None or tpot <= 0:
        failures.append(f"{role}_tpot_invalid")
    if generate_wall is None or generate_wall <= 0:
        failures.append(f"{role}_generate_wall_invalid")
    if sample_count is None:
        failures.append(f"{role}_sample_count_invalid")
    if requested_tokens is None:
        failures.append(f"{role}_requested_output_token_count_invalid")
    if input_tokens is None:
        failures.append(f"{role}_input_token_count_invalid")
    if tokens_per_second is not None and tpot is not None:
        expected = 1.0 / tpot
        if not math.isclose(tokens_per_second, expected, rel_tol=1.0e-9, abs_tol=1.0e-12):
            failures.append(f"{role}_tokens_per_second_mismatch")

    return {
        "tpot": tpot,
        "tokens_per_second": (1.0 / tpot) if tpot and tpot > 0 else None,
        "generate_wall_seconds": generate_wall,
        "sample_count": sample_count,
        "requested_output_token_count": requested_tokens,
        "input_token_count": input_tokens,
        "gpu": artifact.get("gpu"),
        "trace_config": artifact.get("trace_config"),
        "trace_config_sha256": _nonempty_str(artifact.get("trace_config_sha256")),
        "trace_dir": artifact.get("trace_dir"),
        "performance_summary_json": artifact.get("performance_summary_json"),
        "performance_summary_sha256": _nonempty_str(artifact.get("performance_summary_sha256")),
    }


def _check_role_artifact(
    artifact: dict[str, Any],
    failures: list[str],
    *,
    role: str,
) -> None:
    if role == "baseline":
        expected = {
            "production_like_tpot_baseline_ready": True,
            "benchmark_is_current_vllm_baseline": True,
            "benchmark_is_future_typed_slot_useful_path": False,
            "payloadless_useful_mode_enabled": False,
            "benchmark_mode": "production_like_baseline_only",
            "next_runtime_stage": "implement_payloadless_useful_typed_slot_ab_comparison",
        }
    elif role == "candidate":
        expected = {
            "benchmark_mode": "production_like_payloadless_useful_candidate",
            "benchmark_is_current_vllm_baseline": False,
            "benchmark_is_future_typed_slot_useful_path": True,
            "payloadless_useful_mode_enabled": True,
        }
    else:
        raise ValueError(f"unknown role: {role}")

    for key, value in expected.items():
        if artifact.get(key) != value:
            failures.append(f"{role}_{key}_mismatch")

    if role == "candidate":
        ready = artifact.get("production_like_tpot_candidate_ready")
        if ready is not True:
            failures.append("candidate_production_like_tpot_candidate_ready_not_true")


def _load_role(path: Path, failures: list[str], *, role: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.exists():
        failures.append(f"{role}_json_missing")
        return {}, {}
    try:
        artifact = _load_json(path)
    except Exception as exc:
        failures.append(f"{role}_json_load_failed:{exc.__class__.__name__}:{exc}")
        return {}, {}
    facts = _check_common_artifact(artifact, failures, role=role)
    _check_role_artifact(artifact, failures, role=role)
    return artifact, facts


def _check_context(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    failures: list[str],
    *,
    expected_sample_count: int | None,
    expected_requested_output_token_count: int | None,
    expected_gpu: str | None,
    require_same_trace_config_sha: bool,
    require_same_performance_summary_sha: bool,
) -> None:
    for key in (
        "sample_count",
        "requested_output_token_count",
        "input_token_count",
        "gpu",
    ):
        left = baseline.get(key)
        right = candidate.get(key)
        if left != right:
            failures.append(f"context_{key}_mismatch")
    if require_same_trace_config_sha and baseline.get("trace_config_sha256") != candidate.get(
        "trace_config_sha256"
    ):
        failures.append("context_trace_config_sha256_mismatch")
    if require_same_performance_summary_sha and baseline.get(
        "performance_summary_sha256"
    ) != candidate.get("performance_summary_sha256"):
        failures.append("context_performance_summary_sha256_mismatch")

    if expected_sample_count is not None and baseline.get("sample_count") != expected_sample_count:
        failures.append("baseline_expected_sample_count_mismatch")
    if expected_sample_count is not None and candidate.get("sample_count") != expected_sample_count:
        failures.append("candidate_expected_sample_count_mismatch")
    if (
        expected_requested_output_token_count is not None
        and baseline.get("requested_output_token_count") != expected_requested_output_token_count
    ):
        failures.append("baseline_expected_requested_output_token_count_mismatch")
    if (
        expected_requested_output_token_count is not None
        and candidate.get("requested_output_token_count") != expected_requested_output_token_count
    ):
        failures.append("candidate_expected_requested_output_token_count_mismatch")
    if expected_gpu is not None and str(baseline.get("gpu")) != str(expected_gpu):
        failures.append("baseline_expected_gpu_mismatch")
    if expected_gpu is not None and str(candidate.get("gpu")) != str(expected_gpu):
        failures.append("candidate_expected_gpu_mismatch")


def _artifact_has_valid_tpot(artifact: dict[str, Any], facts: dict[str, Any]) -> bool:
    return bool(
        artifact.get("passed") is True
        and artifact.get("failures") == []
        and artifact.get("measures_tpot") is True
        and artifact.get("measures_vllm_latency") is True
        and isinstance(facts.get("tpot"), float)
        and facts["tpot"] > 0
        and isinstance(facts.get("generate_wall_seconds"), float)
        and facts["generate_wall_seconds"] > 0
        and isinstance(facts.get("sample_count"), int)
        and isinstance(facts.get("requested_output_token_count"), int)
        and isinstance(facts.get("input_token_count"), int)
    )


def build_comparison(args: argparse.Namespace) -> dict[str, Any]:
    baseline_path = _resolve(args.baseline_json)
    candidate_path = _resolve(args.candidate_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []

    baseline_artifact, baseline = _load_role(baseline_path, failures, role="baseline")
    candidate_artifact, candidate = _load_role(candidate_path, failures, role="candidate")
    if baseline and candidate:
        _check_context(
            baseline,
            candidate,
            failures,
            expected_sample_count=args.expected_sample_count,
            expected_requested_output_token_count=args.expected_requested_output_token_count,
            expected_gpu=args.expected_gpu,
            require_same_trace_config_sha=args.require_same_trace_config_sha,
            require_same_performance_summary_sha=args.require_same_performance_summary_sha,
        )

    baseline_tpot = baseline.get("tpot")
    candidate_tpot = candidate.get("tpot")
    speedup = None
    tpot_delta = None
    improvement_pct = None
    candidate_faster = None
    if isinstance(baseline_tpot, float) and isinstance(candidate_tpot, float):
        speedup = baseline_tpot / candidate_tpot
        tpot_delta = candidate_tpot - baseline_tpot
        improvement_pct = (1.0 - candidate_tpot / baseline_tpot) * 100.0
        candidate_faster = candidate_tpot < baseline_tpot
        if not args.allow_nonpositive_candidate and not candidate_faster:
            failures.append("candidate_not_faster_than_baseline")
        elif args.allow_nonpositive_candidate and not candidate_faster:
            failures.append("candidate_not_faster_than_baseline_diagnostic_only")

    comparison_ready = bool(
        _artifact_has_valid_tpot(baseline_artifact, baseline)
        and _artifact_has_valid_tpot(candidate_artifact, candidate)
    )
    passed = not failures
    result: dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "comparison_name": COMPARISON_NAME,
        "comparison_mode": COMPARISON_MODE,
        "comparison_source": COMPARISON_SOURCE,
        "passed": passed,
        "failures": failures,
        "comparison_ready": comparison_ready,
        "baseline_json": str(baseline_path),
        "baseline_sha256": _sha256(baseline_path),
        "candidate_json": str(candidate_path),
        "candidate_sha256": _sha256(candidate_path),
        "baseline": baseline,
        "candidate": candidate,
        "baseline_benchmark_mode": baseline_artifact.get("benchmark_mode"),
        "candidate_benchmark_mode": candidate_artifact.get("benchmark_mode"),
        "expected_sample_count": args.expected_sample_count,
        "expected_requested_output_token_count": args.expected_requested_output_token_count,
        "expected_gpu": args.expected_gpu,
        "require_same_trace_config_sha": bool(args.require_same_trace_config_sha),
        "require_same_performance_summary_sha": bool(args.require_same_performance_summary_sha),
        "measures_tpot": comparison_ready,
        "measures_vllm_latency": comparison_ready,
        "payloadless_useful_candidate_required": True,
        "baseline_is_current_vllm": baseline_artifact.get("benchmark_is_current_vllm_baseline"),
        "candidate_is_future_typed_slot_useful_path": candidate_artifact.get(
            "benchmark_is_future_typed_slot_useful_path"
        ),
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "baseline_tpot": baseline_tpot,
        "candidate_tpot": candidate_tpot,
        "tpot_delta_candidate_minus_baseline": tpot_delta,
        "speedup_vs_baseline": speedup,
        "improvement_pct": improvement_pct,
        "candidate_faster": candidate_faster,
        "performance_claim_ready": bool(passed and candidate_faster),
        "diagnostic_only": bool(
            args.allow_nonpositive_candidate and candidate_faster is False
        ),
        "claim_boundary": (
            "Strict production-like TPOT comparison for a future payloadless useful "
            "typed-slot candidate. This artifact does not launch vLLM and does not "
            "permit payload dereference, current WNA16 argument reinterpretation, or "
            "kernel argument handoff."
        ),
        "next_runtime_stage": (
            NEXT_RUNTIME_STAGE if passed else "produce_or_fix_payloadless_useful_candidate_tpot_artifact"
        ),
    }
    _write_json(output_path, result)
    if args.require_pass and not passed:
        raise SystemExit(1)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-json", default=str(DEFAULT_BASELINE_JSON))
    parser.add_argument("--candidate-json", default=str(DEFAULT_CANDIDATE_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--expected-sample-count", type=int, default=32)
    parser.add_argument("--expected-requested-output-token-count", type=int, default=2048)
    parser.add_argument("--expected-gpu", default="1")
    parser.add_argument("--require-same-trace-config-sha", action="store_true")
    parser.add_argument("--require-same-performance-summary-sha", action="store_true")
    parser.add_argument(
        "--allow-nonpositive-candidate",
        action="store_true",
        help="Validate the comparison artifact even if candidate TPOT is not faster.",
    )
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = build_comparison(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
