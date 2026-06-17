#!/usr/bin/env python3
"""Create a no-mutation future WNA16 typed-slot kernel-variant entrypoint.

The entrypoint is the next artifact after the benchmark harness readiness gate.
It models the launch boundary a future WNA16 typed-slot variant would expose,
but it still does not pass arguments to the current WNA16 fused-MoE kernel and
does not measure latency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_HARNESS_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "wna16_typed_slot_benchmark_harness_four_field_preflight_v2.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "future_wna16_typed_slot_kernel_variant_entrypoint_v1.json"
)

ENTRYPOINT_NAME = "premap_future_wna16_typed_slot_kernel_variant_entrypoint_v1"
ENTRYPOINT_MODE = "readonly_independent_typed_slot_kernel_variant_entrypoint"
ENTRYPOINT_SOURCE = "premap_wna16_typed_slot_benchmark_harness_v1"
NEXT_RUNTIME_STAGE = "implement_future_wna16_typed_slot_kernel_timing_stub"
HANDLE_FIELDS = (
    "descriptor_ptr",
    "packed_weight_descriptor",
    "scale_metadata_handle",
    "aux_metadata_handle",
)
EXPECTED_HARNESS_FLAGS: dict[str, Any] = {
    "artifact_kind": "wna16_typed_slot_benchmark_harness",
    "harness_name": "premap_wna16_typed_slot_benchmark_harness_v1",
    "harness_mode": "readonly_future_wna16_typed_slot_benchmark_harness",
    "benchmark_harness_kind": "future_typed_slot_consumer_harness",
    "passed": True,
    "benchmark_harness_ready": True,
    "wna16_kernel_side_execution_ready": True,
    "wna16_benchmark_ready": False,
    "measures_latency": False,
    "current_wna16_arg_pass": False,
    "current_wna16_arg_compatible": False,
    "requires_wna16_arg_reinterpretation": False,
    "explicit_typed_abi_slot": True,
    "reuses_current_wna16_arg_slot": False,
    "payload_bytes": 0,
    "payload_deref_allowed": False,
    "kernel_arg_pass_allowed": False,
    "passed_to_kernel": False,
    "changes_kernel_launch_args": False,
    "next_runtime_stage": (
        "implement_future_wna16_typed_slot_kernel_variant_entrypoint"
    ),
    "fourth_field_handoff_ready": True,
}


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _int_metric(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _is_hex_u64(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 16:
        return False
    try:
        parsed = int(value, 16)
    except ValueError:
        return False
    return 0 < parsed <= 0xFFFFFFFFFFFFFFFF


def _check_harness(
    harness: dict[str, Any],
    *,
    min_source_count: int,
    min_row_count: int,
) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_HARNESS_FLAGS.items():
        if harness.get(key) != expected:
            failures.append(f"harness_{key}_mismatch:{harness.get(key)!r}!={expected!r}")
    source_count = _int_metric(harness, "source_count")
    if source_count is None or source_count < min_source_count:
        failures.append("harness_source_count_invalid")
    row_count = _int_metric(harness, "row_count")
    row_ok_count = _int_metric(harness, "row_ok_count")
    if row_count is None or row_count < min_row_count:
        failures.append("harness_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append("harness_row_ok_count_mismatch")
    fields = harness.get("field_names")
    if fields != list(HANDLE_FIELDS):
        failures.append("harness_field_names_mismatch")
    row_ok_counts = harness.get("field_read_row_ok_counts")
    if not isinstance(row_ok_counts, dict):
        failures.append("harness_field_read_row_ok_counts_missing")
        row_ok_counts = {}
    field_hashes = harness.get("field_read_hashes")
    if not isinstance(field_hashes, dict):
        failures.append("harness_field_read_hashes_missing")
        field_hashes = {}
    expected_field_set = set(HANDLE_FIELDS)
    if set(row_ok_counts) != expected_field_set:
        failures.append("harness_field_read_row_ok_counts_keys_mismatch")
    if set(field_hashes) != expected_field_set:
        failures.append("harness_field_read_hashes_keys_mismatch")
    for field in HANDLE_FIELDS:
        if row_count is not None and row_ok_counts.get(field) != row_count:
            failures.append(f"harness_{field}_read_row_ok_count_mismatch")
        if not _is_hex_u64(field_hashes.get(field)):
            failures.append(f"harness_{field}_read_hash_invalid")
    for key in (
        "row_hash_accumulator",
        "handle_projection_hash_accumulator",
        "fourth_field_handoff_field_read_hash",
        "fourth_field_handoff_runner_hash",
    ):
        if not _is_hex_u64(harness.get(key)):
            failures.append(f"harness_{key}_invalid")
    fourth_source_count = _int_metric(harness, "fourth_field_handoff_source_count")
    if fourth_source_count is None:
        failures.append("harness_fourth_field_handoff_source_count_invalid")
    elif source_count is not None and fourth_source_count != source_count:
        failures.append("harness_fourth_field_handoff_source_count_mismatch")
    fourth_row_count = _int_metric(harness, "fourth_field_handoff_row_count")
    fourth_row_ok_count = _int_metric(harness, "fourth_field_handoff_row_ok_count")
    if fourth_row_count is None:
        failures.append("harness_fourth_field_handoff_row_count_invalid")
    elif row_count is not None and fourth_row_count != row_count:
        failures.append("harness_fourth_field_handoff_row_count_mismatch")
    if fourth_row_ok_count is None:
        failures.append("harness_fourth_field_handoff_row_ok_count_invalid")
    elif fourth_row_count is not None and fourth_row_ok_count != fourth_row_count:
        failures.append("harness_fourth_field_handoff_row_ok_count_mismatch")
    descriptor_hash = field_hashes.get("descriptor_ptr")
    if harness.get("fourth_field_handoff_field_read_hash") != descriptor_hash:
        failures.append("harness_fourth_field_handoff_descriptor_hash_mismatch")
    return failures


def run_entrypoint(args: argparse.Namespace) -> dict[str, Any]:
    harness_path = _resolve(args.harness_json)
    output_path = _resolve(args.output_json)
    harness = _load_json(harness_path)
    failures = _check_harness(
        harness,
        min_source_count=args.min_source_count,
        min_row_count=args.min_row_count,
    )
    passed = not failures
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_kind": "future_wna16_typed_slot_kernel_variant_entrypoint",
        "entrypoint_name": ENTRYPOINT_NAME,
        "entrypoint_mode": ENTRYPOINT_MODE,
        "entrypoint_source": ENTRYPOINT_SOURCE,
        "passed": passed,
        "failures": failures,
        "harness_json": str(harness_path),
        "harness_sha256": _sha256(harness_path),
        "source_count": harness.get("source_count"),
        "row_count": harness.get("row_count"),
        "row_ok_count": harness.get("row_ok_count"),
        "field_names": list(HANDLE_FIELDS),
        "field_read_row_ok_counts": harness.get("field_read_row_ok_counts"),
        "field_read_hashes": harness.get("field_read_hashes"),
        "row_hash_accumulator": harness.get("row_hash_accumulator"),
        "handle_projection_hash_accumulator": harness.get(
            "handle_projection_hash_accumulator"
        ),
        "fourth_field_handoff_ready": harness.get("fourth_field_handoff_ready"),
        "fourth_field_handoff_source_count": harness.get(
            "fourth_field_handoff_source_count"
        ),
        "fourth_field_handoff_row_count": harness.get(
            "fourth_field_handoff_row_count"
        ),
        "fourth_field_handoff_row_ok_count": harness.get(
            "fourth_field_handoff_row_ok_count"
        ),
        "fourth_field_handoff_field_read_hash": harness.get(
            "fourth_field_handoff_field_read_hash"
        ),
        "fourth_field_handoff_runner_hash": harness.get(
            "fourth_field_handoff_runner_hash"
        ),
        "typed_slot_entrypoint_ready": passed,
        "entrypoint_accepts_typed_slot": passed,
        "entrypoint_consumes_handle_fields": passed,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "current_wna16_arg_compatible": False,
        "requires_wna16_arg_reinterpretation": False,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "measures_latency": False,
        "wna16_benchmark_ready": False,
        "next_runtime_stage": NEXT_RUNTIME_STAGE,
    }
    if args.output_json:
        _write_json(output_path, report)
    if args.require_pass and not passed:
        raise SystemExit(
            "future WNA16 typed-slot entrypoint gate failed: "
            + ", ".join(failures)
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the future WNA16 typed-slot benchmark harness and build "
            "a no-mutation kernel-variant entrypoint artifact."
        )
    )
    parser.add_argument("--harness-json", default=str(DEFAULT_HARNESS_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--min-source-count", type=int, default=128)
    parser.add_argument("--min-row-count", type=int, default=1)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_entrypoint(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
