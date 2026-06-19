#!/usr/bin/env python3
"""Build a full-fetch decision gate from the measured-copy slack sweep."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLACK_SWEEP_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_plan_executor_measured_copy_slack_sweep_v1.json"
)
DEFAULT_LOOKAHEAD_SWEEP_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_plan_executor_measured_copy_lookahead_sweep_v1.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_full_fetch_decision_gate_dolly128_gen64_v1.json"
)


SAFE_FALSE_FLAGS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "full_fetch_allowed",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
SAFE_ZERO_FLAGS = ("payload_bytes",)
PROVENANCE_KEYS = (
    "issue_plan_gate_json",
    "measured_copy_json",
    "measured_copy_stat",
    "measured_copy_experts",
    "measured_copy_pinned",
    "capacity",
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _check_safety(payload: dict[str, Any], failures: list[str], *, prefix: str) -> None:
    for key in SAFE_FALSE_FLAGS:
        if payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if payload.get(key) != 0:
            failures.append(f"{prefix}_{key}_not_zero")


def _check_matching_provenance(
    slack: dict[str, Any],
    lookahead: dict[str, Any],
    failures: list[str],
) -> None:
    for key in PROVENANCE_KEYS:
        if key not in slack:
            failures.append(f"slack_sweep_{key}_missing")
        if key not in lookahead:
            failures.append(f"lookahead_sweep_{key}_missing")
        if key in slack and key in lookahead and slack.get(key) != lookahead.get(key):
            failures.append(f"sweep_{key}_mismatch")


def _first_model_passing_deadline_from_rows(
    rows: Any,
    deadline_values: Any,
    failures: list[str],
) -> float | None:
    if not isinstance(rows, list) or not rows:
        failures.append("slack_sweep_rows_missing")
        return None
    if not isinstance(deadline_values, list) or len(rows) != len(deadline_values):
        failures.append("slack_sweep_rows_deadline_count_mismatch")
        return None
    first: float | None = None
    for index, (row, expected_deadline) in enumerate(zip(rows, deadline_values)):
        if not isinstance(row, dict):
            failures.append(f"slack_sweep_row_{index}_not_object")
            continue
        row_deadline = row.get("deadline_us")
        if not isinstance(row_deadline, (int, float)):
            failures.append(f"slack_sweep_row_{index}_deadline_invalid")
            continue
        if float(row_deadline) != float(expected_deadline):
            failures.append(f"slack_sweep_row_{index}_deadline_mismatch")
        if row.get("full_fetch_allowed") is not False:
            failures.append(f"slack_sweep_row_{index}_full_fetch_allowed_not_false")
        model_passed = bool(row.get("model_passed", row.get("passed", False)))
        if model_passed and first is None:
            first = float(row_deadline)
    return first


def _first_model_passing_lookahead_from_rows(
    rows: Any,
    lookahead_values: Any,
    failures: list[str],
) -> float | None:
    if not isinstance(rows, list) or not rows:
        failures.append("lookahead_sweep_rows_missing")
        return None
    if not isinstance(lookahead_values, list) or len(rows) != len(lookahead_values):
        failures.append("lookahead_sweep_rows_lookahead_count_mismatch")
        return None
    first: float | None = None
    for index, (row, expected_lookahead) in enumerate(zip(rows, lookahead_values)):
        if not isinstance(row, dict):
            failures.append(f"lookahead_sweep_row_{index}_not_object")
            continue
        row_lookahead = row.get("lookahead_us")
        if not isinstance(row_lookahead, (int, float)):
            failures.append(f"lookahead_sweep_row_{index}_lookahead_invalid")
            continue
        if float(row_lookahead) != float(expected_lookahead):
            failures.append(f"lookahead_sweep_row_{index}_lookahead_mismatch")
        if row.get("full_fetch_allowed") is not False:
            failures.append(
                f"lookahead_sweep_row_{index}_full_fetch_allowed_not_false"
            )
        model_passed = bool(row.get("model_passed", row.get("passed", False)))
        if model_passed and first is None:
            first = float(row_lookahead)
    return first


def _row_for_deadline(rows: Any, current_deadline_us: float) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_deadline = row.get("deadline_us")
        if isinstance(row_deadline, (int, float)) and float(row_deadline) == float(
            current_deadline_us
        ):
            return row
    return None


def _row_for_lookahead(rows: Any, current_lookahead_us: float) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_lookahead = row.get("lookahead_us")
        if isinstance(row_lookahead, (int, float)) and float(row_lookahead) == float(
            current_lookahead_us
        ):
            return row
    return None


def build_full_fetch_decision_gate(args: argparse.Namespace) -> dict[str, Any]:
    slack_path = _resolve(args.slack_sweep_json)
    lookahead_path = _resolve(args.lookahead_sweep_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    slack = _load_json(slack_path)
    lookahead = _load_json(lookahead_path)

    if slack.get("artifact_kind") != "premap_payload_cache_issue_plan_executor_slack_sweep":
        failures.append("slack_sweep_artifact_kind_mismatch")
    if slack.get("passed") is not True:
        failures.append("slack_sweep_not_passed")
    _check_safety(slack, failures, prefix="slack_sweep")

    first_model_deadline = slack.get("first_model_passing_deadline_us")
    if not isinstance(first_model_deadline, (int, float)) or first_model_deadline < 0:
        failures.append("first_model_passing_deadline_us_invalid")
        first_model_deadline = None
    deadline_values = slack.get("deadline_us_values")
    if not isinstance(deadline_values, list) or deadline_values != sorted(deadline_values):
        failures.append("deadline_us_values_not_sorted")
    row_first_model_deadline = _first_model_passing_deadline_from_rows(
        slack.get("rows"),
        deadline_values,
        failures,
    )
    if first_model_deadline is not None and row_first_model_deadline != first_model_deadline:
        failures.append("first_model_passing_deadline_rows_mismatch")

    current_deadline_us = float(args.current_deadline_us)
    if current_deadline_us < 0:
        failures.append("current_deadline_us_negative")
    current_row = _row_for_deadline(slack.get("rows"), current_deadline_us)
    if current_row is not None and current_row.get("full_fetch_allowed") is not False:
        failures.append("current_deadline_row_full_fetch_allowed_not_false")

    if (
        lookahead.get("artifact_kind")
        != "premap_payload_cache_issue_plan_executor_lookahead_sweep"
    ):
        failures.append("lookahead_sweep_artifact_kind_mismatch")
    if lookahead.get("passed") is not True:
        failures.append("lookahead_sweep_not_passed")
    _check_safety(lookahead, failures, prefix="lookahead_sweep")
    _check_matching_provenance(slack, lookahead, failures)
    lookahead_queue_deadline = lookahead.get("queue_deadline_us")
    if not isinstance(lookahead_queue_deadline, (int, float)):
        failures.append("lookahead_sweep_queue_deadline_us_invalid")
    first_model_lookahead = lookahead.get("first_model_passing_lookahead_us")
    if (
        not isinstance(first_model_lookahead, (int, float))
        or first_model_lookahead < 0
    ):
        failures.append("first_model_passing_lookahead_us_invalid")
        first_model_lookahead = None
    lookahead_values = lookahead.get("lookahead_us_values")
    if not isinstance(lookahead_values, list) or lookahead_values != sorted(
        lookahead_values
    ):
        failures.append("lookahead_us_values_not_sorted")
    row_first_model_lookahead = _first_model_passing_lookahead_from_rows(
        lookahead.get("rows"),
        lookahead_values,
        failures,
    )
    if (
        first_model_lookahead is not None
        and row_first_model_lookahead != first_model_lookahead
    ):
        failures.append("first_model_passing_lookahead_rows_mismatch")

    current_lookahead_us = float(args.current_lookahead_us)
    if current_lookahead_us < 0:
        failures.append("current_lookahead_us_negative")
    if isinstance(lookahead_queue_deadline, (int, float)) and float(
        lookahead_queue_deadline
    ) != float(current_deadline_us):
        failures.append("lookahead_sweep_queue_deadline_current_deadline_mismatch")
    current_lookahead_row = _row_for_lookahead(
        lookahead.get("rows"),
        current_lookahead_us,
    )
    if (
        current_lookahead_row is not None
        and current_lookahead_row.get("full_fetch_allowed") is not False
    ):
        failures.append("current_lookahead_row_full_fetch_allowed_not_false")
    model_slack_satisfied = (
        first_model_deadline is not None and current_deadline_us >= first_model_deadline
    )
    required_slack_us = float(first_model_deadline or 0.0)
    slack_deficit_us = max(0.0, required_slack_us - current_deadline_us)
    model_lookahead_satisfied = (
        first_model_lookahead is not None
        and current_lookahead_us >= first_model_lookahead
    )
    required_lookahead_us = float(first_model_lookahead or 0.0)
    lookahead_deficit_us = max(0.0, required_lookahead_us - current_lookahead_us)
    decision = (
        "model_ready_time_route_satisfied_runtime_still_disabled"
        if model_slack_satisfied or model_lookahead_satisfied
        else "block_full_fetch_insufficient_ready_time_and_lookahead"
    )
    next_runtime_stage = (
        "implement_real_payload_runtime_before_enabling_full_fetch"
        if model_slack_satisfied or model_lookahead_satisfied
        else "prefer_metadata_premap_or_increase_prefetch_lookahead"
    )

    payload = {
        "artifact_kind": "premap_payload_cache_full_fetch_decision_gate",
        "passed": not failures,
        "failures": failures,
        "slack_sweep_json": str(slack_path),
        "lookahead_sweep_json": str(lookahead_path),
        "current_deadline_us": current_deadline_us,
        "current_lookahead_us": current_lookahead_us,
        "first_model_passing_deadline_us": first_model_deadline,
        "first_model_passing_lookahead_us": first_model_lookahead,
        "required_lookahead_slack_us": required_slack_us,
        "required_issue_to_demand_lookahead_us": required_lookahead_us,
        "slack_deficit_us": slack_deficit_us,
        "lookahead_deficit_us": lookahead_deficit_us,
        "ready_time_model_slack_satisfied": model_slack_satisfied,
        "ready_time_model_lookahead_satisfied": model_lookahead_satisfied,
        "ready_time_any_model_route_satisfied": (
            model_slack_satisfied or model_lookahead_satisfied
        ),
        "full_fetch_runtime_allowed": False,
        "full_fetch_block_reason": (
            "real_payload_runtime_not_enabled"
            if model_slack_satisfied or model_lookahead_satisfied
            else "insufficient_ready_time_and_lookahead"
        ),
        "metadata_premap_runtime_preferred": not (
            model_slack_satisfied or model_lookahead_satisfied
        ),
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
        "decision": decision,
        "boundary": (
            "decision gate only; it may satisfy the measured-copy ready-time "
            "model but never enables real full-fetch payload movement"
        ),
        "next_runtime_stage": next_runtime_stage,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slack-sweep-json", type=Path, default=DEFAULT_SLACK_SWEEP_JSON)
    parser.add_argument(
        "--lookahead-sweep-json",
        type=Path,
        default=DEFAULT_LOOKAHEAD_SWEEP_JSON,
    )
    parser.add_argument("--current-deadline-us", type=float, default=200.0)
    parser.add_argument("--current-lookahead-us", type=float, default=0.0)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_full_fetch_decision_gate(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
