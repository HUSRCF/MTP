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
    / "wna16_typed_slot_benchmark_harness_kernel_side_path_preflight_v1.json"
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
KERNEL_SIDE_TYPED_PATH_PREFIX = "future_wna16_kernel_side_typed_consumer_path"
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
    "all_four_field_consumer_ready": True,
    "all_four_field_consumer_fields_read": True,
    "all_four_field_consumer_hashes_valid": True,
    f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_ready": True,
    f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_hashes_valid": True,
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


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_kernel_side_typed_path_evidence(
    carrier: dict[str, Any],
    failures: list[str],
    *,
    label: str,
) -> None:
    source_count = _int_metric(carrier, "source_count")
    row_count = _int_metric(carrier, "row_count")
    evidence_path_value = carrier.get(f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_path")
    evidence_sha_value = carrier.get(f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_sha256")
    evidence_payload: dict[str, Any] | None = None
    if not isinstance(evidence_path_value, str) or not evidence_path_value:
        failures.append(f"{label}_kernel_side_typed_path_evidence_path_missing")
    else:
        evidence_path = _resolve(evidence_path_value)
        if not evidence_path.exists():
            failures.append(f"{label}_kernel_side_typed_path_evidence_path_not_found")
        else:
            actual_sha = _sha256(evidence_path)
            if not _is_sha256_hex(evidence_sha_value):
                failures.append(f"{label}_kernel_side_typed_path_evidence_sha_invalid")
            elif actual_sha != evidence_sha_value:
                failures.append(f"{label}_kernel_side_typed_path_evidence_sha_mismatch")
            try:
                evidence_payload = _load_json(evidence_path)
            except (OSError, json.JSONDecodeError, ValueError):
                failures.append(f"{label}_kernel_side_typed_path_evidence_json_invalid")
    if evidence_payload is None:
        return
    expected_values = {
        "artifact_kind": "future_wna16_kernel_side_typed_consumer_path",
        "passed": True,
        "stage_type": "lab_gate",
        "bench_semantics": False,
        "all_four_gate_ready": True,
        "native_consumer_executed": True,
        "native_consumer_passed": True,
        "payload_bytes": 0,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "wna16_benchmark_ready": False,
    }
    for key, expected in expected_values.items():
        if evidence_payload.get(key) != expected:
            failures.append(
                f"{label}_kernel_side_typed_path_evidence_{key}_mismatch:"
                f"{evidence_payload.get(key)!r}!={expected!r}"
            )
    if evidence_payload.get("failures") != []:
        failures.append(f"{label}_kernel_side_typed_path_evidence_failures_not_empty")
    if source_count is not None and _int_metric(evidence_payload, "source_count") != source_count:
        failures.append(f"{label}_kernel_side_typed_path_evidence_source_count_mismatch")
    input_count = _int_metric(carrier, f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_input_json_count")
    if input_count is not None and _int_metric(evidence_payload, "input_json_count") != input_count:
        failures.append(f"{label}_kernel_side_typed_path_evidence_input_json_count_mismatch")
    if row_count is not None and _int_metric(evidence_payload, "row_count") != row_count:
        failures.append(f"{label}_kernel_side_typed_path_evidence_row_count_mismatch")
    if row_count is not None and _int_metric(evidence_payload, "row_ok_count") != row_count:
        failures.append(f"{label}_kernel_side_typed_path_evidence_row_ok_count_mismatch")
    all_four_sha = carrier.get(f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_sha256")
    if _is_sha256_hex(all_four_sha) and evidence_payload.get("all_four_sha256") != all_four_sha:
        failures.append(f"{label}_kernel_side_typed_path_evidence_all_four_sha_mismatch")
    selected_manifest = carrier.get(
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_selected_input_manifest_sha256"
    )
    if (
        _is_sha256_hex(selected_manifest)
        and evidence_payload.get("selected_input_manifest_sha256") != selected_manifest
    ):
        failures.append(
            f"{label}_kernel_side_typed_path_evidence_selected_manifest_mismatch"
        )


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
    fourth_evidence_path = harness.get("fourth_field_handoff_evidence_path")
    if not isinstance(fourth_evidence_path, str) or not fourth_evidence_path:
        failures.append("harness_fourth_field_handoff_evidence_path_missing")
    fourth_evidence_sha = harness.get("fourth_field_handoff_evidence_sha256")
    if not _is_sha256_hex(fourth_evidence_sha):
        failures.append("harness_fourth_field_handoff_evidence_sha_invalid")
    all_four_source_count = _int_metric(harness, "all_four_field_consumer_source_count")
    if all_four_source_count is None:
        failures.append("harness_all_four_field_consumer_source_count_invalid")
    elif source_count is not None and all_four_source_count != source_count:
        failures.append("harness_all_four_field_consumer_source_count_mismatch")
    all_four_row_count = _int_metric(harness, "all_four_field_consumer_row_count")
    all_four_row_ok_count = _int_metric(harness, "all_four_field_consumer_row_ok_count")
    if all_four_row_count is None:
        failures.append("harness_all_four_field_consumer_row_count_invalid")
    elif row_count is not None and all_four_row_count != row_count:
        failures.append("harness_all_four_field_consumer_row_count_mismatch")
    if all_four_row_ok_count is None:
        failures.append("harness_all_four_field_consumer_row_ok_count_invalid")
    elif all_four_row_count is not None and all_four_row_ok_count != all_four_row_count:
        failures.append("harness_all_four_field_consumer_row_ok_count_mismatch")
    fourth_path = harness.get("all_four_field_consumer_fourth_field_path_label")
    if not isinstance(fourth_path, str) or not fourth_path:
        failures.append("harness_all_four_field_consumer_fourth_path_missing")
    elif isinstance(fourth_evidence_path, str) and fourth_path != fourth_evidence_path:
        failures.append("harness_all_four_field_consumer_fourth_path_mismatch")
    fourth_sha = harness.get("all_four_field_consumer_fourth_field_sha256")
    if not _is_sha256_hex(fourth_sha):
        failures.append("harness_all_four_field_consumer_fourth_sha_invalid")
    elif _is_sha256_hex(fourth_evidence_sha) and fourth_sha != fourth_evidence_sha:
        failures.append("harness_all_four_field_consumer_fourth_sha_mismatch")
    kernel_side_source_count = _int_metric(
        harness,
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_source_count",
    )
    if kernel_side_source_count is None:
        failures.append("harness_kernel_side_typed_path_source_count_invalid")
    elif source_count is not None and kernel_side_source_count != source_count:
        failures.append("harness_kernel_side_typed_path_source_count_mismatch")
    kernel_side_input_count = _int_metric(
        harness,
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_input_json_count",
    )
    if kernel_side_input_count is None:
        failures.append("harness_kernel_side_typed_path_input_json_count_invalid")
    elif kernel_side_source_count is not None and kernel_side_input_count != kernel_side_source_count:
        failures.append("harness_kernel_side_typed_path_input_json_count_mismatch")
    kernel_side_row_count = _int_metric(
        harness,
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_row_count",
    )
    kernel_side_row_ok_count = _int_metric(
        harness,
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_row_ok_count",
    )
    if kernel_side_row_count is None:
        failures.append("harness_kernel_side_typed_path_row_count_invalid")
    elif row_count is not None and kernel_side_row_count != row_count:
        failures.append("harness_kernel_side_typed_path_row_count_mismatch")
    if kernel_side_row_ok_count is None:
        failures.append("harness_kernel_side_typed_path_row_ok_count_invalid")
    elif kernel_side_row_count is not None and kernel_side_row_ok_count != kernel_side_row_count:
        failures.append("harness_kernel_side_typed_path_row_ok_count_mismatch")
    kernel_side_evidence_path = harness.get(
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_path"
    )
    if not isinstance(kernel_side_evidence_path, str) or not kernel_side_evidence_path:
        failures.append("harness_kernel_side_typed_path_evidence_path_missing")
    kernel_side_evidence_sha = harness.get(
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_sha256"
    )
    if not _is_sha256_hex(kernel_side_evidence_sha):
        failures.append("harness_kernel_side_typed_path_evidence_sha_invalid")
    kernel_side_all_four_sha = harness.get(
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_sha256"
    )
    if not _is_sha256_hex(kernel_side_all_four_sha):
        failures.append("harness_kernel_side_typed_path_all_four_sha_invalid")
    kernel_side_manifest = harness.get(
        f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_selected_input_manifest_sha256"
    )
    if not _is_sha256_hex(kernel_side_manifest):
        failures.append("harness_kernel_side_typed_path_selected_manifest_invalid")
    _check_kernel_side_typed_path_evidence(harness, failures, label="harness")
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
        "fourth_field_handoff_evidence_path": harness.get(
            "fourth_field_handoff_evidence_path"
        ),
        "fourth_field_handoff_evidence_sha256": harness.get(
            "fourth_field_handoff_evidence_sha256"
        ),
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
        "all_four_field_consumer_ready": harness.get(
            "all_four_field_consumer_ready"
        ),
        "all_four_field_consumer_fields_read": harness.get(
            "all_four_field_consumer_fields_read"
        ),
        "all_four_field_consumer_hashes_valid": harness.get(
            "all_four_field_consumer_hashes_valid"
        ),
        "all_four_field_consumer_source_count": harness.get(
            "all_four_field_consumer_source_count"
        ),
        "all_four_field_consumer_row_count": harness.get(
            "all_four_field_consumer_row_count"
        ),
        "all_four_field_consumer_row_ok_count": harness.get(
            "all_four_field_consumer_row_ok_count"
        ),
        "all_four_field_consumer_fourth_field_path_label": harness.get(
            "all_four_field_consumer_fourth_field_path_label"
        ),
        "all_four_field_consumer_fourth_field_sha256": harness.get(
            "all_four_field_consumer_fourth_field_sha256"
        ),
        "future_wna16_kernel_side_typed_consumer_path_ready": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_ready"
        ),
        "future_wna16_kernel_side_typed_consumer_path_hashes_valid": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_hashes_valid"
        ),
        "future_wna16_kernel_side_typed_consumer_path_evidence_path": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_path"
        ),
        "future_wna16_kernel_side_typed_consumer_path_evidence_sha256": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_evidence_sha256"
        ),
        "future_wna16_kernel_side_typed_consumer_path_source_count": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_source_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_input_json_count": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_input_json_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_row_count": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_row_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_row_ok_count": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_row_ok_count"
        ),
        "future_wna16_kernel_side_typed_consumer_path_all_four_sha256": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_all_four_sha256"
        ),
        "future_wna16_kernel_side_typed_consumer_path_selected_input_manifest_sha256": harness.get(
            f"{KERNEL_SIDE_TYPED_PATH_PREFIX}_selected_input_manifest_sha256"
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
