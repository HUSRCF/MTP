#!/usr/bin/env python3
"""Build a full-fetch decision gate from the stream lookahead sweep."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STREAM_LOOKAHEAD_SWEEP_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_stream_executor_measured_copy_lookahead_sweep_dolly4_gen64_v1_20260620.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_stream_full_fetch_decision_gate_dolly4_gen64_current0_v1_20260620.json"
)
DEFAULT_QUEUE_BUDGET_SWEEP_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_stream_executor_token_index_queue_budget_dolly4_awq_gpu1_smoke_v1.json"
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


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _valid_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _check_safety(payload: dict[str, Any], failures: list[str], *, prefix: str) -> None:
    for key in SAFE_FALSE_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) != 0:
            failures.append(f"{prefix}_{key}_not_zero")


def _validate_rows(
    rows: Any,
    lookahead_values: Any,
    failures: list[str],
) -> tuple[float | None, dict[str, Any] | None]:
    if not isinstance(rows, list) or not rows:
        failures.append("stream_lookahead_rows_missing")
        return None, None
    if not isinstance(lookahead_values, list) or len(rows) != len(lookahead_values):
        failures.append("stream_lookahead_rows_value_count_mismatch")
        return None, None

    first: float | None = None
    last: dict[str, Any] | None = None
    for index, (row, expected_lookahead) in enumerate(zip(rows, lookahead_values)):
        if not isinstance(row, dict):
            failures.append(f"stream_lookahead_row_{index}_not_object")
            continue
        row_lookahead = row.get("lookahead_us")
        if not _valid_number(row_lookahead):
            failures.append(f"stream_lookahead_row_{index}_lookahead_invalid")
            continue
        if float(row_lookahead) != float(expected_lookahead):
            failures.append(f"stream_lookahead_row_{index}_lookahead_mismatch")
        model_passed_raw = row.get("model_passed")
        if type(model_passed_raw) is not bool:
            failures.append(f"stream_lookahead_row_{index}_model_passed_invalid")
            model_passed = False
        else:
            model_passed = model_passed_raw
        passed_raw = row.get("passed")
        if type(passed_raw) is not bool:
            failures.append(f"stream_lookahead_row_{index}_passed_invalid")
            passed = False
        else:
            passed = passed_raw
        safety_passed_raw = row.get("safety_passed")
        if type(safety_passed_raw) is not bool:
            failures.append(f"stream_lookahead_row_{index}_safety_passed_missing")
            safety_passed = False
        else:
            safety_passed = safety_passed_raw
        safety_failures_raw = row.get("safety_failures")
        if not isinstance(safety_failures_raw, list) or any(
            not isinstance(item, str) for item in safety_failures_raw
        ):
            failures.append(f"stream_lookahead_row_{index}_safety_failures_invalid")
            safety_failures: list[str] = []
        else:
            safety_failures = list(safety_failures_raw)
        row_failures_raw = row.get("failures")
        if not isinstance(row_failures_raw, list) or any(
            not isinstance(item, str) for item in row_failures_raw
        ):
            failures.append(f"stream_lookahead_row_{index}_failures_invalid")
            row_failures: list[str] = []
        else:
            row_failures = list(row_failures_raw)
        safety_failure_start = len(failures)
        _check_safety(row, failures, prefix=f"stream_lookahead_row_{index}")
        computed_safety_failures = failures[safety_failure_start:]
        computed_safety_passed = not computed_safety_failures
        if safety_passed is not computed_safety_passed:
            failures.append(f"stream_lookahead_row_{index}_safety_passed_mismatch")
        if safety_failures != computed_safety_failures:
            failures.append(f"stream_lookahead_row_{index}_safety_failures_mismatch")
        if passed is not (model_passed and safety_passed):
            failures.append(f"stream_lookahead_row_{index}_passed_safety_mismatch")
        if passed and row_failures:
            failures.append(f"stream_lookahead_row_{index}_passed_with_failures")
        if model_passed and first is None:
            first = float(row_lookahead)
        last = row
    return first, last


def _row_for_lookahead(rows: Any, current_lookahead_us: float) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_lookahead = row.get("lookahead_us")
        if _valid_number(row_lookahead) and float(row_lookahead) == float(
            current_lookahead_us
        ):
            return row
    return None


def _validate_queue_budget_sweep(
    payload: dict[str, Any],
    failures: list[str],
) -> dict[str, Any] | None:
    if (
        payload.get("artifact_kind")
        != "premap_payload_cache_issue_stream_executor_queue_budget_sweep"
    ):
        failures.append("queue_budget_sweep_artifact_kind_mismatch")
        return None
    if payload.get("passed") is not True:
        failures.append("queue_budget_sweep_not_passed")
    child_failures = payload.get("failures")
    if not isinstance(child_failures, list) or any(
        not isinstance(item, str) for item in child_failures
    ):
        failures.append("queue_budget_sweep_failures_invalid")
    elif child_failures:
        failures.extend(f"queue_budget_sweep_{item}" for item in child_failures)
    _check_safety(payload, failures, prefix="queue_budget_sweep")

    first_cell = payload.get("first_passing_cell")
    if not isinstance(first_cell, dict):
        failures.append("queue_budget_first_passing_cell_missing")
        return None
    for key in ("capacity", "queue_deadline_us", "issue_lead_tokens", "lookahead_us"):
        value = first_cell.get(key)
        if not _valid_number(value):
            failures.append(f"queue_budget_first_passing_cell_{key}_invalid")
            continue
    capacity_value = first_cell.get("capacity")
    deadline_value = first_cell.get("queue_deadline_us")
    lead_value = first_cell.get("issue_lead_tokens")
    first_cell_numbers_valid = all(
        _valid_number(first_cell.get(key))
        for key in ("capacity", "queue_deadline_us", "issue_lead_tokens", "lookahead_us")
    )
    if type(capacity_value) in (int, float) and int(capacity_value) <= 0:
        failures.append("queue_budget_first_passing_cell_capacity_nonpositive")
    if type(deadline_value) in (int, float) and float(deadline_value) < 0.0:
        failures.append("queue_budget_first_passing_cell_deadline_negative")
    if type(lead_value) in (int, float) and int(lead_value) < 0:
        failures.append("queue_budget_first_passing_cell_lead_negative")

    cells = payload.get("cells")
    if not isinstance(cells, list) or not cells:
        failures.append("queue_budget_cells_missing")
        return first_cell
    passing_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("passed") is True
    ]
    if not passing_cells:
        failures.append("queue_budget_no_passing_cells")
    first_cell_matched = False
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            failures.append(f"queue_budget_cell_{index}_not_object")
            continue
        cell_passed = cell.get("passed")
        cell_child_passed = cell.get("child_passed")
        cell_model_passed = cell.get("model_passed")
        if type(cell_passed) is not bool:
            failures.append(f"queue_budget_cell_{index}_passed_invalid")
            cell_passed = False
        if cell_child_passed is not None and type(cell_child_passed) is not bool:
            failures.append(f"queue_budget_cell_{index}_child_passed_invalid")
            cell_child_passed = None
        if cell_model_passed is not None and type(cell_model_passed) is not bool:
            failures.append(f"queue_budget_cell_{index}_model_passed_invalid")
            cell_model_passed = None
        cell_failures = cell.get("failures")
        if not isinstance(cell_failures, list) or any(
            not isinstance(item, str) for item in cell_failures
        ):
            failures.append(f"queue_budget_cell_{index}_failures_invalid")
            cell_failures = []
        if cell_passed and cell_failures:
            failures.append(f"queue_budget_cell_{index}_passed_with_failures")
        if cell_passed and cell_model_passed is not True:
            failures.append(f"queue_budget_cell_{index}_passed_with_model_failed")
        if cell_passed and cell_child_passed is not True:
            failures.append(f"queue_budget_cell_{index}_passed_with_child_failed")
        first_passing_row = cell.get("first_passing_row")
        if cell_passed and not isinstance(first_passing_row, dict):
            failures.append(f"queue_budget_cell_{index}_first_passing_row_missing")
        row_count = cell.get("row_count")
        rows = cell.get("rows")
        if not isinstance(rows, list):
            failures.append(f"queue_budget_cell_{index}_rows_invalid")
            rows = []
        if type(row_count) is not int or row_count != len(rows):
            failures.append(f"queue_budget_cell_{index}_row_count_mismatch")
        row_passed_values: list[bool] = []
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                failures.append(f"queue_budget_cell_{index}_row_{row_index}_not_object")
                row_passed_values.append(False)
                continue
            row_passed = row.get("passed")
            row_model_passed = row.get("model_passed")
            row_safety_passed = row.get("safety_passed")
            if type(row_passed) is not bool:
                failures.append(f"queue_budget_cell_{index}_row_{row_index}_passed_invalid")
                row_passed = False
            if type(row_model_passed) is not bool:
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_model_passed_invalid"
                )
                row_model_passed = False
            if type(row_safety_passed) is not bool:
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_safety_passed_invalid"
                )
                row_safety_passed = False
            row_failures = row.get("failures")
            if not isinstance(row_failures, list) or any(
                not isinstance(item, str) for item in row_failures
            ):
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_failures_invalid"
                )
                row_failures = []
            row_safety_failures = row.get("safety_failures")
            if not isinstance(row_safety_failures, list) or any(
                not isinstance(item, str) for item in row_safety_failures
            ):
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_safety_failures_invalid"
                )
                row_safety_failures = []
            row_safety_failure_start = len(failures)
            _check_safety(row, failures, prefix=f"queue_budget_cell_{index}_row_{row_index}")
            computed_row_safety_failures = failures[row_safety_failure_start:]
            if row_safety_passed is not (not computed_row_safety_failures):
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_safety_passed_mismatch"
                )
            if row_safety_failures != computed_row_safety_failures:
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_safety_failures_mismatch"
                )
            if row_passed and row_model_passed is not True:
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_passed_with_model_failed"
                )
            if row_passed and row_safety_passed is not True:
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_passed_with_safety_failed"
                )
            if row_passed and row_failures:
                failures.append(
                    f"queue_budget_cell_{index}_row_{row_index}_passed_with_failures"
                )
            row_passed_values.append(row_passed)
        first_row_from_rows: dict[str, Any] | None = None
        for row, row_passed in zip(rows, row_passed_values):
            if row_passed and isinstance(row, dict):
                first_row_from_rows = row
                break
        if cell_passed:
            if first_row_from_rows is None:
                failures.append(f"queue_budget_cell_{index}_no_passing_row")
            elif first_passing_row != first_row_from_rows:
                failures.append(f"queue_budget_cell_{index}_first_passing_row_mismatch")
        cell_failure_start = len(failures)
        _check_safety(cell, failures, prefix=f"queue_budget_cell_{index}")
        computed_cell_failures = failures[cell_failure_start:]
        cell_safety_passed = cell.get("safety_passed")
        if type(cell_safety_passed) is not bool:
            failures.append(f"queue_budget_cell_{index}_safety_passed_invalid")
        elif cell_safety_passed is not (not computed_cell_failures):
            failures.append(f"queue_budget_cell_{index}_safety_passed_mismatch")
        if cell_passed and cell_safety_passed is not True:
            failures.append(f"queue_budget_cell_{index}_passed_with_safety_failed")
        cell_failures = cell.get("safety_failures")
        if not isinstance(cell_failures, list) or any(
            not isinstance(item, str) for item in cell_failures
        ):
            failures.append(f"queue_budget_cell_{index}_safety_failures_invalid")
        elif cell_failures != computed_cell_failures:
            failures.append(f"queue_budget_cell_{index}_safety_failures_mismatch")
        if cell_passed:
            required_cell_numbers = {
                "capacity": cell.get("capacity"),
                "queue_deadline_us": cell.get("queue_deadline_us"),
                "first_model_passing_issue_lead_tokens": cell.get(
                    "first_model_passing_issue_lead_tokens"
                ),
                "first_model_passing_lookahead_us": cell.get(
                    "first_model_passing_lookahead_us"
                ),
            }
            for key, value in required_cell_numbers.items():
                if not _valid_number(value):
                    failures.append(f"queue_budget_cell_{index}_{key}_invalid")
            cell_matches_first = (
                first_cell_numbers_valid
                and all(_valid_number(value) for value in required_cell_numbers.values())
                and int(cell.get("capacity")) == int(first_cell.get("capacity"))
                and float(cell.get("queue_deadline_us"))
                == float(first_cell.get("queue_deadline_us"))
                and int(cell.get("first_model_passing_issue_lead_tokens"))
                == int(first_cell.get("issue_lead_tokens"))
                and float(cell.get("first_model_passing_lookahead_us"))
                == float(first_cell.get("lookahead_us"))
            )
            if first_row_from_rows is not None:
                if first_row_from_rows.get("issue_lead_tokens") != cell.get(
                    "first_model_passing_issue_lead_tokens"
                ):
                    failures.append(f"queue_budget_cell_{index}_first_row_lead_mismatch")
                if first_row_from_rows.get("lookahead_us") != cell.get(
                    "first_model_passing_lookahead_us"
                ):
                    failures.append(
                        f"queue_budget_cell_{index}_first_row_lookahead_mismatch"
                    )
            first_cell_matched = first_cell_matched or cell_matches_first
    if not first_cell_matched:
        failures.append("queue_budget_first_passing_cell_not_in_passing_cells")
    return first_cell


def build_stream_full_fetch_decision_gate(args: argparse.Namespace) -> dict[str, Any]:
    sweep_path = _resolve(args.stream_lookahead_sweep_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    sweep = _load_json(sweep_path)
    queue_budget_path = (
        None
        if args.queue_budget_sweep_json is None
        else _resolve(args.queue_budget_sweep_json)
    )

    if (
        sweep.get("artifact_kind")
        != "premap_payload_cache_issue_stream_executor_lookahead_sweep"
    ):
        failures.append("stream_lookahead_sweep_artifact_kind_mismatch")
    if sweep.get("passed") is not True:
        failures.append("stream_lookahead_sweep_not_passed")
    stream_failures = sweep.get("failures")
    if not isinstance(stream_failures, list) or any(
        not isinstance(item, str) for item in stream_failures
    ):
        failures.append("stream_lookahead_sweep_failures_invalid")
    elif stream_failures:
        failures.extend(f"stream_lookahead_sweep_{item}" for item in stream_failures)
    _check_safety(sweep, failures, prefix="stream_lookahead_sweep")

    first_model_lookahead = sweep.get("first_model_passing_lookahead_us")
    if (
        not _valid_number(first_model_lookahead)
        or float(first_model_lookahead) < 0.0
    ):
        failures.append("first_model_passing_lookahead_us_invalid")
        first_model_lookahead = None

    queue_deadline_us = sweep.get("queue_deadline_us")
    if not _valid_number(queue_deadline_us) or float(queue_deadline_us) <= 0.0:
        failures.append("stream_lookahead_queue_deadline_us_invalid")
        queue_deadline_us = None

    lookahead_values = sweep.get("lookahead_us_values")
    if (
        not isinstance(lookahead_values, list)
        or any(not _valid_number(value) for value in lookahead_values)
        or lookahead_values != sorted(lookahead_values)
    ):
        failures.append("stream_lookahead_us_values_not_sorted")
    row_first_model_lookahead, last_row = _validate_rows(
        sweep.get("rows"),
        lookahead_values,
        failures,
    )
    if (
        first_model_lookahead is not None
        and row_first_model_lookahead != float(first_model_lookahead)
    ):
        failures.append("first_model_passing_lookahead_rows_mismatch")

    current_lookahead_raw = args.current_lookahead_us
    if not _valid_number(current_lookahead_raw):
        failures.append("current_lookahead_us_invalid")
        current_lookahead_us = 0.0
    else:
        current_lookahead_us = float(current_lookahead_raw)
    if current_lookahead_us < 0.0:
        failures.append("current_lookahead_us_negative")
    current_queue_deadline_raw = args.current_queue_deadline_us
    if not _valid_number(current_queue_deadline_raw):
        failures.append("current_queue_deadline_us_invalid")
        current_queue_deadline_us = 0.0
    else:
        current_queue_deadline_us = float(current_queue_deadline_raw)
    if current_queue_deadline_us <= 0.0:
        failures.append("current_queue_deadline_us_nonpositive")
    if queue_deadline_us is not None and float(queue_deadline_us) != current_queue_deadline_us:
        failures.append("stream_queue_deadline_current_deadline_mismatch")

    current_row = _row_for_lookahead(sweep.get("rows"), current_lookahead_us)
    queue_budget_first_cell: dict[str, Any] | None = None
    if queue_budget_path is not None:
        queue_budget_first_cell = _validate_queue_budget_sweep(
            _load_json(queue_budget_path),
            failures,
        )

    model_lookahead_satisfied = (
        first_model_lookahead is not None
        and current_lookahead_us >= float(first_model_lookahead)
    )
    required_lookahead_us = float(first_model_lookahead or 0.0)
    lookahead_deficit_us = max(0.0, required_lookahead_us - current_lookahead_us)
    decision = (
        "model_stream_ready_time_satisfied_runtime_still_disabled"
        if model_lookahead_satisfied
        else "block_full_fetch_insufficient_stream_lookahead"
    )

    payload = {
        "artifact_kind": "premap_payload_cache_stream_full_fetch_decision_gate",
        "passed": not failures,
        "failures": failures,
        "stream_lookahead_sweep_json": str(sweep_path),
        "queue_budget_sweep_json": None if queue_budget_path is None else str(queue_budget_path),
        "queue_budget_gate_present": queue_budget_path is not None,
        "queue_budget_first_passing_cell": queue_budget_first_cell,
        "queue_budget_required_capacity": (
            None if queue_budget_first_cell is None else queue_budget_first_cell.get("capacity")
        ),
        "queue_budget_required_deadline_us": (
            None
            if queue_budget_first_cell is None
            else queue_budget_first_cell.get("queue_deadline_us")
        ),
        "queue_budget_required_issue_lead_tokens": (
            None
            if queue_budget_first_cell is None
            else queue_budget_first_cell.get("issue_lead_tokens")
        ),
        "required_queue_capacity": (
            None if queue_budget_first_cell is None else queue_budget_first_cell.get("capacity")
        ),
        "required_queue_deadline_us": (
            None
            if queue_budget_first_cell is None
            else queue_budget_first_cell.get("queue_deadline_us")
        ),
        "required_issue_lead_tokens": (
            None
            if queue_budget_first_cell is None
            else queue_budget_first_cell.get("issue_lead_tokens")
        ),
        "current_lookahead_us": current_lookahead_us,
        "current_queue_deadline_us": current_queue_deadline_us,
        "first_model_passing_lookahead_us": first_model_lookahead,
        "required_stream_lookahead_us": required_lookahead_us,
        "lookahead_deficit_us": lookahead_deficit_us,
        "ready_time_model_lookahead_satisfied": model_lookahead_satisfied,
        "ready_time_any_model_route_satisfied": model_lookahead_satisfied,
        "current_row_present": current_row is not None,
        "current_row_model_passed": (
            None if current_row is None else current_row.get("model_passed")
        ),
        "current_row_demand_hit_rate": (
            None if current_row is None else current_row.get("demand_hit_rate")
        ),
        "current_row_ready_late_miss_rate": (
            None if current_row is None else current_row.get("ready_late_miss_rate")
        ),
        "current_row_used_per_issued_fetch": (
            None if current_row is None else current_row.get("used_per_issued_fetch")
        ),
        "last_row_lookahead_us": None if last_row is None else last_row.get("lookahead_us"),
        "last_row_demand_hit_rate": (
            None if last_row is None else last_row.get("demand_hit_rate")
        ),
        "last_row_ready_late_miss_rate": (
            None if last_row is None else last_row.get("ready_late_miss_rate")
        ),
        "last_row_used_per_issued_fetch": (
            None if last_row is None else last_row.get("used_per_issued_fetch")
        ),
        "measured_copy_json": sweep.get("measured_copy_json"),
        "measured_copy_stat": sweep.get("measured_copy_stat"),
        "measured_copy_experts": sweep.get("measured_copy_experts"),
        "measured_copy_pinned": sweep.get("measured_copy_pinned"),
        "capacity": sweep.get("capacity"),
        "full_fetch_runtime_allowed": False,
        "full_fetch_block_reason": (
            "real_payload_runtime_not_enabled"
            if model_lookahead_satisfied
            else "insufficient_stream_lookahead"
        ),
        "metadata_premap_runtime_preferred": not model_lookahead_satisfied,
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
            "stream decision gate only; it never enables real full-fetch payload "
            "movement, ready credit, kernel arg pass, or endpoint latency"
        ),
        "next_runtime_stage": (
            "implement_earlier_producer_issue_before_real_payload_runtime"
            if not model_lookahead_satisfied
            else "implement_real_payload_runtime_before_enabling_full_fetch"
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
    parser.add_argument(
        "--stream-lookahead-sweep-json",
        type=Path,
        default=DEFAULT_STREAM_LOOKAHEAD_SWEEP_JSON,
    )
    parser.add_argument("--current-lookahead-us", type=float, default=0.0)
    parser.add_argument("--current-queue-deadline-us", type=float, default=200.0)
    parser.add_argument("--queue-budget-sweep-json", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_stream_full_fetch_decision_gate(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
