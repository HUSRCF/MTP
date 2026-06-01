#!/usr/bin/env python3
"""Check an online native-stub tail-window probe runner.

This checker is intentionally narrower than the strict lab preflight checker.
The default lab gate still requires full-table native consumer coverage.  This
script validates a side artifact used to prove that the future kernel-side ABI
can consume a row-window/tail-window slice without touching payloads or WNA16
kernel arguments.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RUNNER_JSON = Path(
    "outputs/reports/premap_kernel_consumer/"
    "online_prelaunch_native_stub_canary_arg_slot_4input_tail8_probe.json"
)

_DISPATCH_SUMMARIES: tuple[tuple[str, str], ...] = (
    (
        "future_kernel_native_consumer_dispatch_stub_summary",
        "scale_metadata_handle",
    ),
    (
        "future_kernel_native_consumer_dispatch_descriptor_ptr_stub_summary",
        "descriptor_ptr",
    ),
    (
        "future_kernel_native_consumer_dispatch_packed_weight_stub_summary",
        "packed_weight_descriptor",
    ),
    (
        "future_kernel_native_consumer_dispatch_aux_metadata_stub_summary",
        "aux_metadata_handle",
    ),
)
_EXTRA_DISPATCH_OUTPUTS: tuple[tuple[str, str], ...] = (
    ("native_stub_future_kernel_native_consumer_dispatch_abi", "scale_metadata_handle"),
    (
        "native_stub_future_kernel_native_consumer_dispatch_descriptor_ptr_mirror",
        "descriptor_ptr",
    ),
    (
        "native_stub_future_kernel_native_consumer_dispatch_packed_weight_mirror",
        "packed_weight_descriptor",
    ),
    (
        "native_stub_future_kernel_native_consumer_dispatch_aux_metadata_mirror",
        "aux_metadata_handle",
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _check_bool(
    payload: dict[str, Any],
    key: str,
    expected: bool,
    failures: list[str],
    *,
    prefix: str,
) -> None:
    if payload.get(key) is not expected:
        failures.append(f"{prefix}_{key}_mismatch")


def _check_dispatch_summary(
    summary: Any,
    *,
    prefix: str,
    expected_field_name: str,
    expected_tail_window_size: int,
    expected_input_row_count: int | None,
    failures: list[str],
) -> tuple[int | None, int | None]:
    if not isinstance(summary, dict):
        failures.append(f"{prefix}_missing")
        return None, None
    if summary.get("passed") is not True or summary.get("ok") is not True:
        failures.append(f"{prefix}_not_passed")
    if _int(summary.get("error_count")) != 0:
        failures.append(f"{prefix}_error_count_mismatch")
    for key in (
        "payload_bytes",
        "future_kernel_native_dispatch_consumer_payload_bytes",
        "future_kernel_native_dispatch_ptr_consumer_payload_bytes",
        "future_kernel_native_arg_slot_consumer_payload_bytes",
    ):
        if _int(summary.get(key)) != 0:
            failures.append(f"{prefix}_{key}_mismatch")
    for key in (
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "future_kernel_native_dispatch_consumer_passed_to_kernel",
        "future_kernel_native_dispatch_consumer_changes_kernel_launch_args",
        "future_kernel_native_dispatch_consumer_current_wna16_arg_compatible",
        "future_kernel_native_dispatch_consumer_requires_wna16_arg_reinterpretation",
        "future_kernel_native_dispatch_ptr_consumer_passed_to_kernel",
        "future_kernel_native_dispatch_ptr_consumer_changes_kernel_launch_args",
        "future_kernel_native_dispatch_ptr_consumer_current_wna16_arg_compatible",
        "future_kernel_native_dispatch_ptr_consumer_requires_wna16_arg_reinterpretation",
        "future_kernel_native_arg_slot_consumer_passed_to_kernel",
        "future_kernel_native_arg_slot_consumer_changes_kernel_launch_args",
        "future_kernel_native_arg_slot_consumer_current_wna16_arg_compatible",
        "future_kernel_native_arg_slot_consumer_requires_wna16_arg_reinterpretation",
    ):
        _check_bool(summary, key, False, failures, prefix=prefix)
    for key in (
        "future_kernel_native_dispatch_consumer_checked",
        "future_kernel_native_dispatch_ptr_consumer_checked",
        "future_kernel_native_arg_slot_consumer_checked",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_checked",
    ):
        _check_bool(summary, key, True, failures, prefix=prefix)
    if (
        summary.get("future_kernel_native_arg_slot_consumer_single_field_mirror_field_name")
        != expected_field_name
    ):
        failures.append(f"{prefix}_arg_slot_mirror_field_mismatch")

    row_count = _int(summary.get("row_count"))
    offset = _int(summary.get("future_kernel_native_dispatch_consumer_row_offset"))
    limit = _int(summary.get("future_kernel_native_dispatch_consumer_row_limit"))
    active = _int(summary.get("future_kernel_native_dispatch_consumer_active_rows"))
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
    if (
        row_count is not None
        and expected_input_row_count is not None
        and row_count != expected_input_row_count
    ):
        failures.append(f"{prefix}_row_count_input_mismatch")
    if offset is None or limit is None or active is None:
        failures.append(f"{prefix}_dispatch_window_missing")
        return row_count, active
    if row_count is not None and limit != row_count:
        failures.append(f"{prefix}_dispatch_limit_not_tail")
    if row_count is not None and offset != max(row_count - expected_tail_window_size, 0):
        failures.append(f"{prefix}_dispatch_offset_not_tail")
    if limit <= offset:
        failures.append(f"{prefix}_dispatch_window_empty")
    if active != min(expected_tail_window_size, row_count or expected_tail_window_size):
        failures.append(f"{prefix}_active_rows_mismatch")
    for key in (
        "future_kernel_native_dispatch_consumer_row_count",
        "future_kernel_native_dispatch_consumer_row_ok_count",
        "future_kernel_native_dispatch_ptr_consumer_row_count",
        "future_kernel_native_dispatch_ptr_consumer_row_ok_count",
        "future_kernel_native_arg_slot_consumer_row_count",
        "future_kernel_native_arg_slot_consumer_row_ok_count",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_count",
        "future_kernel_native_arg_slot_consumer_single_field_mirror_row_ok_count",
    ):
        if _int(summary.get(key)) != active:
            failures.append(f"{prefix}_{key}_mismatch")
    return row_count, active


def check_tail_window_probe(
    *,
    runner_json: Path = DEFAULT_RUNNER_JSON,
    expected_tail_window_size: int = 8,
    min_online_inputs: int = 4,
    min_tail_windowed_inputs: int = 4,
    require_diverse_row_counts: bool = True,
) -> dict[str, Any]:
    runner_path = runner_json.resolve()
    failures: list[str] = []
    if int(expected_tail_window_size) <= 0:
        failures.append("expected_tail_window_size_not_positive")
    if int(min_online_inputs) <= 0:
        failures.append("min_online_inputs_not_positive")
    if int(min_tail_windowed_inputs) <= 0:
        failures.append("min_tail_windowed_inputs_not_positive")
    try:
        runner = _load_json(runner_path)
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return {
            "passed": False,
            "failures": [f"runner_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
        }

    if runner.get("passed") is not True:
        failures.append("runner_not_passed")
    if runner.get("failures") != []:
        failures.append("runner_failures_not_empty")
    if _int(runner.get("future_native_dispatch_tail_window_size")) != int(
        expected_tail_window_size
    ):
        failures.append("runner_tail_window_size_mismatch")

    input_count = _int(runner.get("online_prelaunch_input_check_count"))
    if input_count is None or input_count < int(min_online_inputs):
        failures.append("runner_online_input_count_below_min")
        input_count = input_count or 0
    row_counts = runner.get("online_prelaunch_input_row_counts")
    valid_row_counts: list[int] = []
    if not isinstance(row_counts, list) or len(row_counts) != input_count:
        failures.append("runner_online_input_row_counts_mismatch")
    else:
        for index, value in enumerate(row_counts):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                failures.append(
                    f"runner_online_input_row_counts_{index:04d}_invalid"
                )
                continue
            valid_row_counts.append(value)
    if valid_row_counts:
        if _int(runner.get("online_prelaunch_input_row_count_min")) != min(
            valid_row_counts
        ):
            failures.append("runner_online_input_row_count_min_mismatch")
        if _int(runner.get("online_prelaunch_input_row_count_max")) != max(
            valid_row_counts
        ):
            failures.append("runner_online_input_row_count_max_mismatch")
        if _int(runner.get("online_prelaunch_input_row_count_sum")) != sum(
            valid_row_counts
        ):
            failures.append("runner_online_input_row_count_sum_mismatch")
        row_counts_diverse = min(valid_row_counts) < max(valid_row_counts)
        if runner.get("online_prelaunch_input_row_count_diverse") is not row_counts_diverse:
            failures.append("runner_online_input_row_count_diverse_mismatch")
        if require_diverse_row_counts and not row_counts_diverse:
            failures.append("runner_online_input_row_counts_not_diverse")
        tail_windowed_input_count = sum(
            1 for value in valid_row_counts if value > int(expected_tail_window_size)
        )
        if tail_windowed_input_count < int(min_tail_windowed_inputs):
            failures.append("runner_tail_windowed_input_count_below_min")
    else:
        tail_windowed_input_count = 0

    expected_first_input_row_count = valid_row_counts[0] if valid_row_counts else None
    dispatch_window_rows: dict[str, int | None] = {}
    dispatch_input_rows: dict[str, int | None] = {}
    dispatch_offsets: dict[str, int | None] = {}
    dispatch_limits: dict[str, int | None] = {}
    for summary_key, expected_field in _DISPATCH_SUMMARIES:
        summary = runner.get(summary_key)
        row_count, active = _check_dispatch_summary(
            summary,
            prefix=f"runner_{summary_key}",
            expected_field_name=expected_field,
            expected_tail_window_size=int(expected_tail_window_size),
            expected_input_row_count=expected_first_input_row_count,
            failures=failures,
        )
        dispatch_input_rows[summary_key] = row_count
        dispatch_window_rows[summary_key] = active
        if isinstance(summary, dict):
            dispatch_offsets[summary_key] = _int(
                summary.get("future_kernel_native_dispatch_consumer_row_offset")
            )
            dispatch_limits[summary_key] = _int(
                summary.get("future_kernel_native_dispatch_consumer_row_limit")
            )
        else:
            dispatch_offsets[summary_key] = None
            dispatch_limits[summary_key] = None

    if len({value for value in dispatch_input_rows.values() if value is not None}) > 1:
        failures.append("dispatch_summary_row_counts_not_consistent")
    if len({value for value in dispatch_window_rows.values() if value is not None}) > 1:
        failures.append("dispatch_summary_active_rows_not_consistent")
    if len({value for value in dispatch_offsets.values() if value is not None}) > 1:
        failures.append("dispatch_summary_offsets_not_consistent")
    if len({value for value in dispatch_limits.values() if value is not None}) > 1:
        failures.append("dispatch_summary_limits_not_consistent")

    extra_checked_count = 0
    extra_summaries = runner.get("extra_online_input_check_summaries")
    if input_count > 1:
        expected_extra_count = input_count - 1
        if not isinstance(extra_summaries, list):
            failures.append("runner_extra_online_input_check_summaries_missing")
            extra_summaries = []
        elif len(extra_summaries) != expected_extra_count:
            failures.append("runner_extra_online_input_check_summaries_count_mismatch")
        for index, suite in enumerate(extra_summaries[:expected_extra_count], start=1):
            prefix = f"runner_extra_input_{index:04d}"
            expected_input_row_count = (
                valid_row_counts[index] if index < len(valid_row_counts) else None
            )
            if not isinstance(suite, dict):
                failures.append(f"{prefix}_summary_invalid")
                continue
            if suite.get("passed") is not True:
                failures.append(f"{prefix}_not_passed")
            if suite.get("failures") != []:
                failures.append(f"{prefix}_failures_not_empty")
            outputs = suite.get("outputs")
            if not isinstance(outputs, dict):
                failures.append(f"{prefix}_outputs_missing")
                outputs = {}
            extra_input_rows: dict[str, int | None] = {}
            extra_active_rows: dict[str, int | None] = {}
            extra_offsets: dict[str, int | None] = {}
            extra_limits: dict[str, int | None] = {}
            for label, expected_field in _EXTRA_DISPATCH_OUTPUTS:
                entry = outputs.get(label)
                label_prefix = f"{prefix}_{label}"
                if not isinstance(entry, dict):
                    failures.append(f"{label_prefix}_missing")
                    continue
                summary = entry.get("summary")
                row_count, active = _check_dispatch_summary(
                    summary,
                    prefix=label_prefix,
                    expected_field_name=expected_field,
                    expected_tail_window_size=int(expected_tail_window_size),
                    expected_input_row_count=expected_input_row_count,
                    failures=failures,
                )
                extra_input_rows[label] = row_count
                extra_active_rows[label] = active
                if isinstance(summary, dict):
                    extra_offsets[label] = _int(
                        summary.get(
                            "future_kernel_native_dispatch_consumer_row_offset"
                        )
                    )
                    extra_limits[label] = _int(
                        summary.get(
                            "future_kernel_native_dispatch_consumer_row_limit"
                        )
                    )
                else:
                    extra_offsets[label] = None
                    extra_limits[label] = None
            if len({value for value in extra_input_rows.values() if value is not None}) > 1:
                failures.append(f"{prefix}_dispatch_row_counts_not_consistent")
            if len({value for value in extra_active_rows.values() if value is not None}) > 1:
                failures.append(f"{prefix}_dispatch_active_rows_not_consistent")
            if len({value for value in extra_offsets.values() if value is not None}) > 1:
                failures.append(f"{prefix}_dispatch_offsets_not_consistent")
            if len({value for value in extra_limits.values() if value is not None}) > 1:
                failures.append(f"{prefix}_dispatch_limits_not_consistent")
            extra_checked_count += 1

    return {
        "passed": not failures,
        "failures": failures,
        "runner_json": str(runner_path),
        "expected_tail_window_size": int(expected_tail_window_size),
        "min_online_inputs": int(min_online_inputs),
        "min_tail_windowed_inputs": int(min_tail_windowed_inputs),
        "runner_online_prelaunch_input_check_count": input_count,
        "runner_online_prelaunch_input_row_counts": valid_row_counts,
        "runner_online_prelaunch_input_row_count_min": (
            min(valid_row_counts) if valid_row_counts else None
        ),
        "runner_online_prelaunch_input_row_count_max": (
            max(valid_row_counts) if valid_row_counts else None
        ),
        "runner_online_prelaunch_input_row_count_sum": (
            sum(valid_row_counts) if valid_row_counts else None
        ),
        "runner_online_prelaunch_input_row_count_diverse": (
            (min(valid_row_counts) < max(valid_row_counts))
            if valid_row_counts
            else None
        ),
        "runner_tail_windowed_input_count": tail_windowed_input_count,
        "dispatch_input_rows": dispatch_input_rows,
        "dispatch_window_rows": dispatch_window_rows,
        "dispatch_offsets": dispatch_offsets,
        "dispatch_limits": dispatch_limits,
        "extra_online_input_tail_window_check_count": extra_checked_count,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-json", type=Path, default=DEFAULT_RUNNER_JSON)
    parser.add_argument("--expected-tail-window-size", type=int, default=8)
    parser.add_argument("--min-online-inputs", type=int, default=4)
    parser.add_argument("--min-tail-windowed-inputs", type=int, default=4)
    diverse_group = parser.add_mutually_exclusive_group()
    diverse_group.add_argument(
        "--require-diverse-row-counts",
        action="store_true",
        dest="require_diverse_row_counts",
        default=True,
    )
    diverse_group.add_argument(
        "--allow-uniform-row-counts",
        action="store_false",
        dest="require_diverse_row_counts",
    )
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_tail_window_probe(
        runner_json=args.runner_json,
        expected_tail_window_size=args.expected_tail_window_size,
        min_online_inputs=args.min_online_inputs,
        min_tail_windowed_inputs=args.min_tail_windowed_inputs,
        require_diverse_row_counts=args.require_diverse_row_counts,
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
