#!/usr/bin/env python3
"""Run and check all mirror-field row-window sweeps for the online arg-slot ABI.

This is a stricter future-kernel consumer preflight.  It runs the
full/head/middle/tail window sweep for each typed handle field and then checks
each artifact with the static window-sweep checker.  It still never passes the
typed table to the current WNA16 kernel and never moves payload bytes.
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

from scripts.check_premap_online_merged_native_arg_slot_window_sweep import (  # noqa: E402
    check_window_sweep_artifact,
)
from scripts.run_premap_online_merged_native_arg_slot_window_sweep import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_RUNNER_JSON,
    LAB_DEFAULT_GPU_DEVICE,
    build_parser as build_window_sweep_parser,
    run_sweep,
)


MIRROR_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_all_field_window_sweep_runner.json"
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _field_paths(output_dir: Path, field: str) -> tuple[Path, Path]:
    return (
        output_dir / f"online_merged_future_native_arg_slot_window_sweep_{field}_runner.json",
        output_dir / f"online_merged_future_native_arg_slot_window_sweep_{field}_check.json",
    )


def _field_sweep_args(
    args: argparse.Namespace,
    *,
    field: str,
    output_json: Path,
) -> argparse.Namespace:
    argv = [
        "--runner-json",
        str(_resolve(args.runner_json)),
        "--output-dir",
        str(_resolve(args.output_dir)),
        "--output-json",
        str(output_json),
        "--window-size",
        str(int(args.window_size)),
        "--max-inputs",
        str(int(args.max_inputs)),
        "--min-source-count",
        str(int(args.min_source_count)),
        "--min-total-rows",
        str(int(args.min_total_rows)),
        "--block-threads",
        str(int(args.block_threads)),
        "--mirror-field",
        field,
        "--device",
        str(int(args.device)),
    ]
    if args.hip_visible_devices:
        argv.extend(["--hip-visible-devices", args.hip_visible_devices])
    if args.force_build:
        argv.append("--force-build")
    if args.dry_run:
        argv.append("--dry-run")
    if args.require_program_view_ptr_abi:
        argv.append("--require-program-view-ptr-abi")
    return build_window_sweep_parser().parse_args(argv)


def run_all_field_sweep(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = _resolve(args.output_dir)
    output_json = _resolve(args.output_json)
    failures: list[str] = []
    field_reports: dict[str, dict[str, Any]] = {}
    for field in MIRROR_FIELDS:
        field_output_json, field_check_json = _field_paths(output_dir, field)
        sweep_result = run_sweep(
            _field_sweep_args(args, field=field, output_json=field_output_json)
        )
        check_result = (
            {
                "passed": True,
                "failures": [],
                "dry_run": True,
                "source": "online_merged_future_native_arg_slot_window_sweep_check",
            }
            if args.dry_run
            else check_window_sweep_artifact(
                field_output_json,
                expected_window_size=int(args.window_size),
                expected_block_threads=int(args.block_threads),
                min_row_count=int(args.min_total_rows),
                expected_mirror_field=field,
                require_child_artifacts=True,
                require_non_degenerate_windows=True,
                require_child_program_view_ptr_abi=bool(
                    args.require_program_view_ptr_abi
                ),
            )
        )
        if not args.dry_run:
            field_check_json.parent.mkdir(parents=True, exist_ok=True)
            field_check_json.write_text(
                json.dumps(check_result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if sweep_result.get("passed") is not True:
            failures.append(f"{field}_sweep_not_passed")
        if check_result.get("passed") is not True:
            failures.append(f"{field}_check_not_passed")
        field_reports[field] = {
            "passed": bool(
                sweep_result.get("passed") is True
                and check_result.get("passed") is True
            ),
            "sweep_json": str(field_output_json),
            "check_json": str(field_check_json),
            "sweep_failures": sweep_result.get("failures"),
            "check_failures": check_result.get("failures"),
            "row_count": sweep_result.get("row_count"),
            "window_size": sweep_result.get("window_size"),
            "windows_checked": check_result.get("windows_checked"),
        }

    row_counts = {
        field: report.get("row_count")
        for field, report in field_reports.items()
    }
    if len(set(row_counts.values())) != 1:
        failures.append("field_row_counts_not_equal")
    report = {
        "passed": not failures,
        "failures": failures,
        "source": "online_merged_future_native_arg_slot_all_field_window_sweep_runner",
        "dry_run": bool(args.dry_run),
        "runner_json": str(_resolve(args.runner_json)),
        "window_size": int(args.window_size),
        "require_program_view_ptr_abi": bool(args.require_program_view_ptr_abi),
        "block_threads": int(args.block_threads),
        "device": int(args.device),
        "mirror_fields": list(MIRROR_FIELDS),
        "field_reports": field_reports,
        "row_counts": row_counts,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-json", type=Path, default=DEFAULT_SOURCE_RUNNER_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--window-size", type=int, default=512)
    parser.add_argument(
        "--require-program-view-ptr-abi",
        action="store_true",
        help=(
            "Require every per-field child window sweep to validate the "
            "future native program-view pointer ABI."
        ),
    )
    parser.add_argument("--max-inputs", type=int, default=32)
    parser.add_argument("--min-source-count", type=int, default=32)
    parser.add_argument("--min-total-rows", type=int, default=257)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument("--device", type=int, default=LAB_DEFAULT_GPU_DEVICE)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_all_field_sweep(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
