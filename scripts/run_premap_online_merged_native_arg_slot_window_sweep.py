#!/usr/bin/env python3
"""Run full/head/middle/tail window canaries for the online-merged arg-slot ABI.

This is a future-kernel consumer geometry probe.  It proves the readonly typed
arg-slot ABI can consume row windows at different offsets in the same
online-derived handle distribution.  It never passes the table to the current
WNA16 kernel and never moves payload bytes.
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

from scripts.run_premap_online_merged_native_arg_slot_canary import (  # noqa: E402
    DEFAULT_SOURCE_RUNNER_JSON,
    LAB_DEFAULT_GPU_DEVICE,
    build_parser as build_arg_slot_parser,
    run_canary,
)


DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_merged_future_native_arg_slot_window_sweep_runner.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "reports" / "premap_kernel_consumer"


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _window_bounds(row_count: int, window_size: int) -> dict[str, tuple[int, int]]:
    if row_count <= 0:
        raise ValueError("row_count must be positive")
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    active = min(int(window_size), int(row_count))
    middle_offset = max(0, (int(row_count) - active) // 2)
    return {
        "head": (0, active),
        "middle": (middle_offset, middle_offset + active),
        "tail": (int(row_count) - active, int(row_count)),
    }


def _artifact_paths(output_dir: Path, *, label: str) -> tuple[Path, Path, Path]:
    return (
        output_dir / f"online_merged_future_native_arg_slot_{label}_window_canary_runner.json",
        output_dir / f"typed_consumer_stub_gpu1_online_merged_future_native_arg_slot_{label}_window_canary.json",
        output_dir / f"online_merged_prelaunch_typed_consumer_input_arg_slot_{label}_window.json",
    )


def _canary_args(
    args: argparse.Namespace,
    *,
    output_json: Path,
    stub_output_json: Path,
    merged_output_json: Path,
    offset: int | None = None,
    limit: int | None = None,
) -> argparse.Namespace:
    argv = [
        "--runner-json",
        str(_resolve(args.runner_json)),
        "--max-inputs",
        str(int(args.max_inputs)),
        "--min-source-count",
        str(int(args.min_source_count)),
        "--min-total-rows",
        str(int(args.min_total_rows)),
        "--block-threads",
        str(int(args.block_threads)),
        "--mirror-field",
        args.mirror_field,
        "--device",
        str(int(args.device)),
        "--output-json",
        str(output_json),
        "--stub-output-json",
        str(stub_output_json),
        "--merged-output-json",
        str(merged_output_json),
    ]
    if args.hip_visible_devices:
        argv.extend(["--hip-visible-devices", args.hip_visible_devices])
    if args.force_build:
        argv.append("--force-build")
    if args.dry_run:
        argv.append("--dry-run")
    if offset is not None and limit is not None:
        argv.extend(["--dispatch-row-offset", str(int(offset))])
        argv.extend(["--dispatch-row-limit", str(int(limit))])
    return build_arg_slot_parser().parse_args(argv)


def _validate_window_result(
    result: dict[str, Any],
    *,
    label: str,
    expected_offset: int,
    expected_limit: int,
) -> list[str]:
    failures: list[str] = []
    expected_active = int(expected_limit) - int(expected_offset)
    for key, expected in {
        "passed": True,
        "no_payload": True,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "not_a_single_vllm_launch_table": True,
        "handle_projection_all_handle_fields_checked": True,
    }.items():
        if result.get(key) != expected:
            failures.append(f"{label}_{key}_mismatch")
    if result.get("dispatch_row_offset") != int(expected_offset):
        failures.append(f"{label}_dispatch_row_offset_mismatch")
    if result.get("dispatch_row_limit") != int(expected_limit):
        failures.append(f"{label}_dispatch_row_limit_mismatch")
    if result.get("dispatch_active_rows") != expected_active:
        failures.append(f"{label}_dispatch_active_rows_mismatch")
    return failures


def run_sweep(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = _resolve(args.output_dir)
    output_json = _resolve(args.output_json)

    full_report, full_stub, full_merged = _artifact_paths(output_dir, label="full")
    full_result = run_canary(
        _canary_args(
            args,
            output_json=full_report,
            stub_output_json=full_stub,
            merged_output_json=full_merged,
        )
    )
    row_count = int(full_result["merged_row_count"])
    window_bounds = _window_bounds(row_count, int(args.window_size))

    failures = _validate_window_result(
        full_result,
        label="full",
        expected_offset=0,
        expected_limit=row_count,
    )
    window_results: dict[str, dict[str, Any]] = {"full": full_result}
    window_artifacts: dict[str, dict[str, str]] = {
        "full": {
            "output_json": str(full_report),
            "stub_output_json": str(full_stub),
            "merged_output_json": str(full_merged),
        }
    }
    for label, (offset, limit) in window_bounds.items():
        report_path, stub_path, merged_path = _artifact_paths(output_dir, label=label)
        result = run_canary(
            _canary_args(
                args,
                output_json=report_path,
                stub_output_json=stub_path,
                merged_output_json=merged_path,
                offset=offset,
                limit=limit,
            )
        )
        failures.extend(
            _validate_window_result(
                result,
                label=label,
                expected_offset=offset,
                expected_limit=limit,
            )
        )
        window_results[label] = result
        window_artifacts[label] = {
            "output_json": str(report_path),
            "stub_output_json": str(stub_path),
            "merged_output_json": str(merged_path),
        }

    report = {
        "passed": not failures,
        "failures": failures,
        "source": "online_merged_future_native_arg_slot_window_sweep_runner",
        "runner_json": str(_resolve(args.runner_json)),
        "window_size": int(args.window_size),
        "row_count": row_count,
        "device": int(args.device),
        "mirror_field": args.mirror_field,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "windows": {
            label: {
                "passed": result.get("passed"),
                "dispatch_row_offset": result.get("dispatch_row_offset"),
                "dispatch_row_limit": result.get("dispatch_row_limit"),
                "dispatch_active_rows": result.get("dispatch_active_rows"),
                "dispatch_expected_program_count": result.get(
                    "dispatch_expected_program_count"
                ),
                "merged_row_count": result.get("merged_row_count"),
                **window_artifacts[label],
            }
            for label, result in window_results.items()
        },
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
    parser.add_argument("--max-inputs", type=int, default=32)
    parser.add_argument("--min-source-count", type=int, default=32)
    parser.add_argument("--min-total-rows", type=int, default=257)
    parser.add_argument("--block-threads", type=int, default=256)
    parser.add_argument(
        "--mirror-field",
        choices=[
            "aux_metadata_handle",
            "descriptor_ptr",
            "packed_weight_descriptor",
            "scale_metadata_handle",
        ],
        default="scale_metadata_handle",
    )
    parser.add_argument("--device", type=int, default=LAB_DEFAULT_GPU_DEVICE)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_sweep(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
