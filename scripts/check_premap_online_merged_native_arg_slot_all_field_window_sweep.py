#!/usr/bin/env python3
"""Check the all-field online-merged future-native arg-slot window sweep.

This is a static checker for the convenience all-field runner.  It verifies
that every typed handle field has a passed full/head/middle/tail window sweep
and that each per-field check artifact enforces the strict no-op boundary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_premap_online_merged_native_arg_slot_all_field_window_sweep import (  # noqa: E402
    DEFAULT_OUTPUT_JSON,
    MIRROR_FIELDS,
)


REQUIRED_WINDOWS = ("full", "head", "middle", "tail")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON must contain an object")
    return payload


def _safe_load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _load_json(path), None
    except (
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return None, type(exc).__name__


def _resolve_child_path(value: object, *, parent: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return parent / path


def _check_field_report(
    report: dict[str, Any],
    *,
    field: str,
    expected_row_count: int,
    expected_window_size: int,
    expected_block_threads: int,
    parent: Path,
    require_child_checks: bool,
) -> list[str]:
    failures: list[str] = []
    if report.get("passed") is not True:
        failures.append(f"{field}_report_not_passed")
    if report.get("sweep_failures") != []:
        failures.append(f"{field}_sweep_failures_not_empty")
    if report.get("check_failures") != []:
        failures.append(f"{field}_check_failures_not_empty")
    if report.get("row_count") != expected_row_count:
        failures.append(f"{field}_row_count_mismatch")
    if report.get("window_size") != expected_window_size:
        failures.append(f"{field}_window_size_mismatch")
    if report.get("windows_checked") != list(REQUIRED_WINDOWS):
        failures.append(f"{field}_windows_checked_mismatch")

    if not require_child_checks:
        return failures

    check_path = _resolve_child_path(report.get("check_json"), parent=parent)
    if check_path is None:
        failures.append(f"{field}_check_json_missing")
        return failures
    check_payload, check_error = _safe_load_json(check_path)
    if check_payload is None:
        failures.append(f"{field}_check_json_read_failed:{check_error}")
        return failures
    expected_pairs: dict[str, Any] = {
        "passed": True,
        "failures": [],
        "source": "online_merged_future_native_arg_slot_window_sweep_check",
        "expected_mirror_field": field,
        "expected_window_size": expected_window_size,
        "expected_block_threads": expected_block_threads,
        "require_child_artifacts": True,
        "require_non_degenerate_windows": True,
        "row_count": expected_row_count,
        "windows_checked": list(REQUIRED_WINDOWS),
    }
    for key, expected in expected_pairs.items():
        if check_payload.get(key) != expected:
            failures.append(f"{field}_check_{key}_mismatch")
    return failures


def check_all_field_window_sweep_artifact(
    path: Path,
    *,
    expected_window_size: int = 512,
    expected_block_threads: int = 256,
    min_row_count: int = 257,
    require_child_checks: bool = True,
) -> dict[str, Any]:
    sweep_path = path.resolve()
    payload, error = _safe_load_json(sweep_path)
    if payload is None:
        return {
            "passed": False,
            "failures": [f"all_field_window_sweep_json_read_failed:{error}"],
            "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
            "all_field_window_sweep_json": str(sweep_path),
        }

    failures: list[str] = []
    if payload.get("source") != (
        "online_merged_future_native_arg_slot_all_field_window_sweep_runner"
    ):
        failures.append("source_mismatch")
    if payload.get("passed") is not True:
        failures.append("all_field_window_sweep_not_passed")
    if payload.get("failures") != []:
        failures.append("all_field_failures_not_empty")
    if payload.get("dry_run") is True:
        failures.append("dry_run_not_allowed")
    if payload.get("payload_bytes") != 0:
        failures.append("payload_bytes_mismatch")
    if payload.get("passed_to_kernel") is not False:
        failures.append("passed_to_kernel_mismatch")
    if payload.get("changes_kernel_launch_args") is not False:
        failures.append("changes_kernel_launch_args_mismatch")
    if payload.get("window_size") != int(expected_window_size):
        failures.append("window_size_mismatch")
    if payload.get("block_threads") != int(expected_block_threads):
        failures.append("block_threads_mismatch")
    if payload.get("mirror_fields") != list(MIRROR_FIELDS):
        failures.append("mirror_fields_mismatch")

    row_counts = payload.get("row_counts")
    if not isinstance(row_counts, dict):
        failures.append("row_counts_missing")
        row_counts = {}
    try:
        row_count_values = [int(row_counts.get(field)) for field in MIRROR_FIELDS]
    except (TypeError, ValueError):
        row_count_values = []
        failures.append("row_counts_invalid")
    if row_count_values:
        if len(set(row_count_values)) != 1:
            failures.append("field_row_counts_not_equal")
        expected_row_count = row_count_values[0]
    else:
        expected_row_count = -1
    if expected_row_count < int(min_row_count):
        failures.append("row_count_below_min")
    if expected_row_count <= int(expected_window_size):
        failures.append("row_count_not_larger_than_window_size")

    field_reports = payload.get("field_reports")
    if not isinstance(field_reports, dict):
        failures.append("field_reports_missing")
        field_reports = {}
    for field in MIRROR_FIELDS:
        report = field_reports.get(field)
        if not isinstance(report, dict):
            failures.append(f"{field}_field_report_missing")
            continue
        failures.extend(
            _check_field_report(
                report,
                field=field,
                expected_row_count=expected_row_count,
                expected_window_size=int(expected_window_size),
                expected_block_threads=int(expected_block_threads),
                parent=sweep_path.parent,
                require_child_checks=bool(require_child_checks),
            )
        )

    return {
        "passed": not failures,
        "failures": failures,
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_check",
        "all_field_window_sweep_json": str(sweep_path),
        "expected_window_size": int(expected_window_size),
        "expected_block_threads": int(expected_block_threads),
        "min_row_count": int(min_row_count),
        "require_child_checks": bool(require_child_checks),
        "mirror_fields_checked": list(MIRROR_FIELDS),
        "row_count": expected_row_count,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("all_field_window_sweep_json", nargs="?", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--expected-window-size", type=int, default=512)
    parser.add_argument("--expected-block-threads", type=int, default=256)
    parser.add_argument("--min-row-count", type=int, default=257)
    parser.add_argument("--no-require-child-checks", action="store_true")
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_all_field_window_sweep_artifact(
        args.all_field_window_sweep_json,
        expected_window_size=int(args.expected_window_size),
        expected_block_threads=int(args.expected_block_threads),
        min_row_count=int(args.min_row_count),
        require_child_checks=not bool(args.no_require_child_checks),
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
