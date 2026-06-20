#!/usr/bin/env python3
"""Translate stream lookahead requirements into earlier-issue lead budgets."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECISION_GATE_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_stream_full_fetch_decision_gate_dolly4_gen64_current0_v1_20260620.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_stream_earlier_issue_feasibility_dolly4_gen64_v1_20260620.json"
)

SAFE_FALSE_FLAGS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
SAFE_ZERO_FLAGS = ("payload_bytes",)


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _parse_values(raw: str, *, label: str) -> list[float]:
    values = [float(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not values:
        raise ValueError(f"{label} must contain at least one value")
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        raise ValueError(f"{label} values must be positive finite numbers")
    if values != sorted(values):
        raise ValueError(f"{label} values must be sorted in ascending order")
    return values


def _check_safety(payload: dict[str, Any], failures: list[str], *, prefix: str) -> None:
    for key in SAFE_FALSE_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif not _valid_number(payload.get(key)) or float(payload.get(key)) != 0.0:
            failures.append(f"{prefix}_{key}_not_zero")


def build_stream_earlier_issue_feasibility(
    args: argparse.Namespace,
) -> dict[str, Any]:
    decision_path = _resolve(args.decision_gate_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    decision = _load_json(decision_path)

    if decision.get("artifact_kind") != "premap_payload_cache_stream_full_fetch_decision_gate":
        failures.append("decision_gate_artifact_kind_mismatch")
    if decision.get("passed") is not True:
        failures.append("decision_gate_not_passed")
    decision_failures = decision.get("failures")
    if decision_failures not in ([], None):
        failures.append("decision_gate_failures_not_empty")
    _check_safety(decision, failures, prefix="decision_gate")
    if decision.get("full_fetch_runtime_allowed") is not False:
        failures.append("decision_gate_full_fetch_runtime_allowed_not_false")

    required_lookahead_us = decision.get("required_stream_lookahead_us")
    if (
        isinstance(required_lookahead_us, bool)
        or not isinstance(required_lookahead_us, (int, float))
        or not math.isfinite(float(required_lookahead_us))
        or float(required_lookahead_us) < 0.0
    ):
        failures.append("required_stream_lookahead_us_invalid")
        required_lookahead = 0.0
    else:
        required_lookahead = float(required_lookahead_us)

    current_lookahead_us = decision.get("current_lookahead_us")
    if (
        isinstance(current_lookahead_us, bool)
        or not isinstance(current_lookahead_us, (int, float))
        or not math.isfinite(float(current_lookahead_us))
        or float(current_lookahead_us) < 0.0
    ):
        failures.append("current_lookahead_us_invalid")
        current_lookahead = 0.0
    else:
        current_lookahead = float(current_lookahead_us)
    lookahead_deficit_us = max(0.0, required_lookahead - current_lookahead)

    token_us_values = _parse_values(args.decode_token_us_values, label="decode token us")
    layer_count = int(args.decoder_layer_count)
    if layer_count < 0:
        failures.append("decoder_layer_count_negative")
        layer_count = 0

    rows: list[dict[str, Any]] = []
    for decode_token_us in token_us_values:
        required_lead_tokens = int(math.ceil(required_lookahead / decode_token_us))
        deficit_lead_tokens = int(math.ceil(lookahead_deficit_us / decode_token_us))
        row: dict[str, Any] = {
            "decode_token_us": float(decode_token_us),
            "decode_token_s": float(decode_token_us) / 1_000_000.0,
            "required_lead_tokens": required_lead_tokens,
            "deficit_lead_tokens": deficit_lead_tokens,
            "required_lookahead_us": required_lookahead,
            "lookahead_deficit_us": lookahead_deficit_us,
        }
        if layer_count > 0:
            layer_stage_us = float(decode_token_us) / float(layer_count)
            row.update(
                {
                    "decoder_layer_count": layer_count,
                    "estimated_layer_stage_us": layer_stage_us,
                    "required_lead_layer_stages": int(
                        math.ceil(required_lookahead / layer_stage_us)
                    ),
                    "deficit_lead_layer_stages": int(
                        math.ceil(lookahead_deficit_us / layer_stage_us)
                    ),
                }
            )
        rows.append(row)

    min_required_lead_tokens = min(row["required_lead_tokens"] for row in rows)
    min_deficit_lead_tokens = min(row["deficit_lead_tokens"] for row in rows)
    max_required_lead_tokens = max(row["required_lead_tokens"] for row in rows)
    max_deficit_lead_tokens = max(row["deficit_lead_tokens"] for row in rows)

    feasible_within_configured_token_window = (
        max_required_lead_tokens <= int(args.max_candidate_lead_tokens)
    )
    current_runtime_satisfies_model = lookahead_deficit_us <= 0.0
    payload = {
        "artifact_kind": "premap_payload_cache_stream_earlier_issue_feasibility",
        "passed": not failures,
        "failures": failures,
        "decision_gate_json": str(decision_path),
        "current_lookahead_us": current_lookahead,
        "required_stream_lookahead_us": required_lookahead,
        "lookahead_deficit_us": lookahead_deficit_us,
        "decode_token_us_values": token_us_values,
        "decoder_layer_count": layer_count,
        "max_candidate_lead_tokens": int(args.max_candidate_lead_tokens),
        "min_required_lead_tokens": min_required_lead_tokens,
        "max_required_lead_tokens": max_required_lead_tokens,
        "min_deficit_lead_tokens": min_deficit_lead_tokens,
        "max_deficit_lead_tokens": max_deficit_lead_tokens,
        "feasible_within_configured_token_window": (
            feasible_within_configured_token_window
        ),
        "current_runtime_satisfies_model": current_runtime_satisfies_model,
        "full_fetch_runtime_allowed": False,
        "full_fetch_block_reason": (
            "real_payload_runtime_not_enabled"
            if current_runtime_satisfies_model
            else "insufficient_stream_lookahead"
        ),
        "metadata_premap_runtime_preferred": not current_runtime_satisfies_model,
        "descriptor_prep_runtime_preferred": True,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "rows": rows,
        "boundary": (
            "lead-time feasibility model only; no payload movement, ready credit, "
            "kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": (
            "producer_side_earlier_issue_model"
            if feasible_within_configured_token_window
            else "increase_predictive_window_or_keep_full_fetch_blocked"
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-gate-json", type=Path, default=DEFAULT_DECISION_GATE_JSON)
    parser.add_argument(
        "--decode-token-us-values",
        default="50000,75000,100000",
        help="Comma-separated TPOT/decode-token duration assumptions in microseconds.",
    )
    parser.add_argument("--decoder-layer-count", type=int, default=0)
    parser.add_argument("--max-candidate-lead-tokens", type=int, default=4)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_stream_earlier_issue_feasibility(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
