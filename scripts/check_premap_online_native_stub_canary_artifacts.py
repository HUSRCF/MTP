#!/usr/bin/env python3
"""Check online native-stub canary runner/preflight/status consistency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RUNNER_JSON = Path(
    "outputs/reports/premap_kernel_consumer/"
    "online_prelaunch_native_stub_canary_runner.json"
)
DEFAULT_PREFLIGHT_JSON = Path(
    "outputs/reports/premap_lab_preflight_online_prelaunch_native_stub_canary.json"
)
DEFAULT_STATUS_JSON = Path(
    "outputs/reports/premap_lab_preflight_status_online_prelaunch_native_stub_canary.json"
)


def _resolve(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _check_stub_summary(
    stub: Any,
    *,
    prefix: str,
    failures: list[str],
    require_kernel_side_consumer_path: bool = False,
) -> tuple[int | None, int | None]:
    if not isinstance(stub, dict):
        failures.append(f"{prefix}_summary_missing")
        stub = {}
    if stub.get("passed") is not True or stub.get("ok") is not True:
        failures.append(f"{prefix}_not_passed")
    row_count = _int(stub.get("row_count"))
    row_ok_count = _int(stub.get("row_ok_count"))
    if row_count is None or row_count <= 0:
        failures.append(f"{prefix}_row_count_invalid")
    if row_count is not None and row_ok_count != row_count:
        failures.append(f"{prefix}_row_ok_count_mismatch")
    expected_stub = {
        "error_count": 0,
        "payload_bytes": 0,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }
    for key, expected in expected_stub.items():
        if stub.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")
    if require_kernel_side_consumer_path:
        expected_path = {
            "kernel_side_consumer_path_checked": True,
            "kernel_side_consumer_path_error_count": 0,
            "kernel_side_consumer_path_payload_bytes": 0,
            "kernel_side_consumer_path_passed_to_kernel": False,
            "kernel_side_consumer_path_changes_kernel_launch_args": False,
            "kernel_side_consumer_path_current_wna16_arg_compatible": False,
        }
        for key, expected in expected_path.items():
            if stub.get(key) != expected:
                failures.append(f"{prefix}_{key}_mismatch")
        if stub.get("kernel_side_consumer_path_name") != (
            "premap_kernel_side_typed_consumer_path_v1"
        ):
            failures.append(f"{prefix}_kernel_side_consumer_path_name_mismatch")
        path_row_count = _int(stub.get("kernel_side_consumer_path_row_count"))
        path_row_ok_count = _int(stub.get("kernel_side_consumer_path_row_ok_count"))
        if row_count is not None and path_row_count != row_count:
            failures.append(f"{prefix}_kernel_side_consumer_path_row_count_mismatch")
        if row_count is not None and path_row_ok_count != row_count:
            failures.append(
                f"{prefix}_kernel_side_consumer_path_row_ok_count_mismatch"
            )
    return row_count, row_ok_count


def _check_single_field_mirror_summary(
    stub: Any,
    *,
    prefix: str,
    expected_field_name: str,
    failures: list[str],
    require_envelope: bool = False,
) -> tuple[int | None, int | None]:
    row_count, row_ok_count = _check_stub_summary(
        stub,
        prefix=prefix,
        failures=failures,
    )
    if not isinstance(stub, dict):
        stub = {}
    if require_envelope:
        expected_envelope = {
            "kernel_consumer_envelope_checked": True,
            "kernel_consumer_envelope_payload_bytes": 0,
            "kernel_consumer_envelope_passed_to_kernel": False,
        }
        for key, expected in expected_envelope.items():
            if stub.get(key) != expected:
                failures.append(f"{prefix}_{key}_mismatch")
    expected_mirror = {
        "single_field_mirror_checked": True,
        "single_field_mirror_field_name": expected_field_name,
        "single_field_mirror_error_count": 0,
    }
    for key, expected in expected_mirror.items():
        if stub.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")
    mirror_row_count = _int(stub.get("single_field_mirror_row_count"))
    mirror_row_ok_count = _int(stub.get("single_field_mirror_row_ok_count"))
    if row_count is not None and mirror_row_count != row_count:
        failures.append(f"{prefix}_single_field_mirror_row_count_mismatch")
    if row_count is not None and mirror_row_ok_count != row_count:
        failures.append(f"{prefix}_single_field_mirror_row_ok_count_mismatch")
    return row_count, row_ok_count


def check_online_native_stub_canary_artifacts(
    *,
    root: Path,
    runner_json: Path = DEFAULT_RUNNER_JSON,
    preflight_json: Path = DEFAULT_PREFLIGHT_JSON,
    status_json: Path = DEFAULT_STATUS_JSON,
    require_all_field_mirror_stubs: bool = False,
    min_online_inputs: int = 1,
) -> dict[str, Any]:
    root = root.resolve()
    runner_path = _resolve(root, runner_json)
    preflight_path = _resolve(root, preflight_json)
    status_path = _resolve(root, status_json)
    failures: list[str] = []

    try:
        runner = _load_json(runner_path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "passed": False,
            "failures": [f"runner_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
            "preflight_json": str(preflight_path),
            "status_json": str(status_path),
        }
    try:
        preflight = _load_json(preflight_path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "passed": False,
            "failures": [f"preflight_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
            "preflight_json": str(preflight_path),
            "status_json": str(status_path),
        }
    try:
        status = _load_json(status_path)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "passed": False,
            "failures": [f"status_json_read_failed:{type(exc).__name__}"],
            "runner_json": str(runner_path),
            "preflight_json": str(preflight_path),
            "status_json": str(status_path),
        }

    if runner.get("passed") is not True:
        failures.append("runner_not_passed")
    if runner.get("failures") != []:
        failures.append("runner_failures_not_empty")
    if preflight.get("passed") is not True:
        failures.append("preflight_not_passed")
    if preflight.get("failures") != []:
        failures.append("preflight_failures_not_empty")
    if status.get("passed") is not True:
        failures.append("status_not_passed")

    observed_preflight = runner.get("preflight_output_json")
    if not isinstance(observed_preflight, str) or not observed_preflight:
        failures.append("runner_preflight_output_json_missing")
    elif _resolve(root, observed_preflight).resolve() != preflight_path.resolve():
        failures.append("runner_preflight_output_json_mismatch")

    observed_status = runner.get("preflight_status_output_json")
    if not isinstance(observed_status, str) or not observed_status:
        failures.append("runner_preflight_status_output_json_missing")
    elif _resolve(root, observed_status).resolve() != status_path.resolve():
        failures.append("runner_preflight_status_output_json_mismatch")

    stage1 = runner.get("preflight_status_summary")
    final = runner.get("final_preflight_status_summary")
    if not isinstance(stage1, dict):
        failures.append("runner_stage1_status_missing")
        stage1 = {}
    if not isinstance(final, dict):
        failures.append("runner_final_status_missing")
        final = {}

    status_required = status.get("required_evidence")
    if not isinstance(status_required, dict):
        failures.append("status_required_evidence_missing")
        status_required = {}
    status_optional = status.get("optional_evidence")
    if not isinstance(status_optional, dict):
        status_optional = {}
    status_required_count = _int(status_required.get("required_count"))
    if status_required_count is None or status_required_count <= 0:
        failures.append("status_required_evidence_required_count_invalid")
        status_required_count = 0
    stage1_deferred_count = _int(stage1.get("runtime_gate_evidence_deferred_count"))
    if stage1_deferred_count is None or stage1_deferred_count < 0:
        failures.append("runner_stage1_runtime_gate_evidence_deferred_count_invalid")
        stage1_deferred_count = 0
    expected_stage1 = {
        "passed": True,
        "required_evidence_present_count": max(
            status_required_count - stage1_deferred_count, 0
        ),
        "required_evidence_passed_count": max(
            status_required_count - stage1_deferred_count, 0
        ),
        "required_evidence_required_count": status_required_count,
        "runtime_gate_evidence_deferred_count": 1,
        "strict_default_gate_evidence_deferred_count": 1,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    expected_final = {
        "passed": True,
        "required_evidence_present_count": status_required_count,
        "required_evidence_passed_count": status_required_count,
        "required_evidence_required_count": status_required_count,
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    for key, expected in expected_stage1.items():
        if stage1.get(key) != expected:
            failures.append(f"runner_stage1_{key}_mismatch")
    for key, expected in expected_final.items():
        if final.get(key) != expected:
            failures.append(f"runner_final_{key}_mismatch")
    expected_status = {
        "passed": True,
        "runtime_gate_evidence_deferred_count": 0,
        "strict_default_gate_evidence_deferred_count": 0,
        "payload_bytes_required": 0,
        "passed_to_kernel_required": False,
        "changes_kernel_launch_args_required": False,
    }
    for key, expected in expected_status.items():
        if status.get(key) != expected:
            failures.append(f"status_{key}_mismatch")
    expected_required = {
        "present_count": status_required_count,
        "passed_count": status_required_count,
        "required_count": status_required_count,
        "passed": True,
    }
    for key, expected in expected_required.items():
        if status_required.get(key) != expected:
            failures.append(f"status_required_evidence_{key}_mismatch")
    status_optional_count = _int(status_optional.get("required_count"))
    if status_optional:
        if status_optional_count is None or status_optional_count < 0:
            failures.append("status_optional_evidence_required_count_invalid")
            status_optional_count = 0
        expected_optional = {
            "present_count": status_optional_count,
            "passed_count": status_optional_count,
            "required_count": status_optional_count,
            "passed": True,
        }
        for key, expected in expected_optional.items():
            if status_optional.get(key) != expected:
                failures.append(f"status_optional_evidence_{key}_mismatch")
        for key, expected in {
            "optional_evidence_present_count": status_optional_count,
            "optional_evidence_passed_count": status_optional_count,
            "optional_evidence_required_count": status_optional_count,
            "optional_evidence_passed": True,
        }.items():
            if stage1.get(key) != expected:
                failures.append(f"runner_stage1_{key}_mismatch")
            if final.get(key) != expected:
                failures.append(f"runner_final_{key}_mismatch")

    row_count, row_ok_count = _check_stub_summary(
        runner.get("stub_summary"),
        prefix="runner_stub",
        failures=failures,
        require_kernel_side_consumer_path=True,
    )
    per_field_stub = runner.get("per_field_stub_summary")
    per_field_row_count: int | None = None
    per_field_row_ok_count: int | None = None
    if per_field_stub is not None:
        per_field_row_count, per_field_row_ok_count = _check_stub_summary(
            per_field_stub,
            prefix="runner_per_field_stub",
            failures=failures,
        )
    envelope_mirror_row_count: int | None = None
    envelope_mirror_row_ok_count: int | None = None
    envelope_mirror_stub = runner.get("kernel_envelope_mirror_stub_summary")
    if require_all_field_mirror_stubs and envelope_mirror_stub is None:
        failures.append("runner_kernel_envelope_mirror_stub_summary_required")
    if envelope_mirror_stub is not None:
        envelope_mirror_row_count, envelope_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                envelope_mirror_stub,
                prefix="runner_kernel_envelope_mirror_stub",
                expected_field_name="scale_metadata_handle",
                failures=failures,
                require_envelope=True,
            )
        )
    packed_weight_mirror_row_count: int | None = None
    packed_weight_mirror_row_ok_count: int | None = None
    packed_weight_mirror_stub = runner.get("packed_weight_mirror_stub_summary")
    if require_all_field_mirror_stubs and packed_weight_mirror_stub is None:
        failures.append("runner_packed_weight_mirror_stub_summary_required")
    if packed_weight_mirror_stub is not None:
        packed_weight_mirror_row_count, packed_weight_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                packed_weight_mirror_stub,
                prefix="runner_packed_weight_mirror_stub",
                expected_field_name="packed_weight_descriptor",
                failures=failures,
            )
        )
    aux_metadata_mirror_row_count: int | None = None
    aux_metadata_mirror_row_ok_count: int | None = None
    aux_metadata_mirror_stub = runner.get("aux_metadata_mirror_stub_summary")
    if require_all_field_mirror_stubs and aux_metadata_mirror_stub is None:
        failures.append("runner_aux_metadata_mirror_stub_summary_required")
    if aux_metadata_mirror_stub is not None:
        aux_metadata_mirror_row_count, aux_metadata_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                aux_metadata_mirror_stub,
                prefix="runner_aux_metadata_mirror_stub",
                expected_field_name="aux_metadata_handle",
                failures=failures,
            )
        )
    descriptor_ptr_mirror_row_count: int | None = None
    descriptor_ptr_mirror_row_ok_count: int | None = None
    descriptor_ptr_mirror_stub = runner.get("descriptor_ptr_mirror_stub_summary")
    if require_all_field_mirror_stubs and descriptor_ptr_mirror_stub is None:
        failures.append("runner_descriptor_ptr_mirror_stub_summary_required")
    if descriptor_ptr_mirror_stub is not None:
        descriptor_ptr_mirror_row_count, descriptor_ptr_mirror_row_ok_count = (
            _check_single_field_mirror_summary(
                descriptor_ptr_mirror_stub,
                prefix="runner_descriptor_ptr_mirror_stub",
                expected_field_name="descriptor_ptr",
                failures=failures,
            )
        )

    online_input_check_count = _int(runner.get("online_prelaunch_input_check_count"))
    if online_input_check_count is None:
        if int(min_online_inputs) > 1:
            failures.append("runner_online_prelaunch_input_check_count_missing")
        online_input_check_count = 1
    if online_input_check_count < int(min_online_inputs):
        failures.append("runner_online_prelaunch_input_check_count_below_min")
    extra_input_check_count = _int(
        runner.get("online_prelaunch_input_extra_check_count")
    )
    extra_input_check_passed_count = _int(
        runner.get("online_prelaunch_input_extra_check_passed_count")
    )
    if online_input_check_count > 1:
        expected_extra = online_input_check_count - 1
        if extra_input_check_count != expected_extra:
            failures.append("runner_online_prelaunch_input_extra_check_count_mismatch")
        if extra_input_check_passed_count != expected_extra:
            failures.append(
                "runner_online_prelaunch_input_extra_check_passed_count_mismatch"
            )
        extra_summaries = runner.get("extra_online_input_check_summaries")
        if not isinstance(extra_summaries, list):
            failures.append("runner_extra_online_input_check_summaries_missing")
            extra_summaries = []
        elif len(extra_summaries) != expected_extra:
            failures.append("runner_extra_online_input_check_summaries_count_mismatch")
        expected_labels: dict[str, tuple[str | None, bool]] = {
            "native_stub": (None, False),
            "native_stub_per_field": (None, False),
        }
        if require_all_field_mirror_stubs:
            expected_labels.update(
                {
                    "native_stub_kernel_envelope_mirror": (
                        "scale_metadata_handle",
                        True,
                    ),
                    "native_stub_packed_weight_mirror": (
                        "packed_weight_descriptor",
                        False,
                    ),
                    "native_stub_aux_metadata_mirror": ("aux_metadata_handle", False),
                    "native_stub_descriptor_ptr_mirror": ("descriptor_ptr", False),
                }
            )
        for index, suite in enumerate(extra_summaries[:expected_extra], start=1):
            prefix = f"runner_extra_input_{index:04d}"
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
            for label, (expected_field, require_envelope) in expected_labels.items():
                entry = outputs.get(label)
                label_prefix = f"{prefix}_{label}"
                if not isinstance(entry, dict):
                    failures.append(f"{label_prefix}_missing")
                    continue
                summary = entry.get("summary")
                if expected_field is None:
                    _check_stub_summary(
                        summary,
                        prefix=label_prefix,
                        failures=failures,
                        require_kernel_side_consumer_path=(label == "native_stub"),
                    )
                else:
                    _check_single_field_mirror_summary(
                        summary,
                        prefix=label_prefix,
                        expected_field_name=expected_field,
                        failures=failures,
                        require_envelope=require_envelope,
                    )

    return {
        "passed": not failures,
        "failures": failures,
        "runner_json": str(runner_path),
        "preflight_json": str(preflight_path),
        "status_json": str(status_path),
        "runner_preflight_output_json": observed_preflight,
        "runner_preflight_status_output_json": observed_status,
        "runner_stub_row_count": row_count,
        "runner_stub_row_ok_count": row_ok_count,
        "runner_stub_kernel_side_consumer_path_checked": (
            bool(runner.get("stub_summary", {}).get("kernel_side_consumer_path_checked"))
            if isinstance(runner.get("stub_summary"), dict)
            else False
        ),
        "runner_per_field_stub_row_count": per_field_row_count,
        "runner_per_field_stub_row_ok_count": per_field_row_ok_count,
        "runner_kernel_envelope_mirror_stub_row_count": envelope_mirror_row_count,
        "runner_kernel_envelope_mirror_stub_row_ok_count": (
            envelope_mirror_row_ok_count
        ),
        "runner_packed_weight_mirror_stub_row_count": packed_weight_mirror_row_count,
        "runner_packed_weight_mirror_stub_row_ok_count": (
            packed_weight_mirror_row_ok_count
        ),
        "runner_aux_metadata_mirror_stub_row_count": aux_metadata_mirror_row_count,
        "runner_aux_metadata_mirror_stub_row_ok_count": (
            aux_metadata_mirror_row_ok_count
        ),
        "runner_descriptor_ptr_mirror_stub_row_count": descriptor_ptr_mirror_row_count,
        "runner_descriptor_ptr_mirror_stub_row_ok_count": (
            descriptor_ptr_mirror_row_ok_count
        ),
        "require_all_field_mirror_stubs": bool(require_all_field_mirror_stubs),
        "min_online_inputs": int(min_online_inputs),
        "runner_online_prelaunch_input_check_count": online_input_check_count,
        "runner_online_prelaunch_input_extra_check_count": extra_input_check_count,
        "runner_online_prelaunch_input_extra_check_passed_count": (
            extra_input_check_passed_count
        ),
        "stage1_deferred_count": stage1.get("runtime_gate_evidence_deferred_count"),
        "final_deferred_count": final.get("runtime_gate_evidence_deferred_count"),
        "status_deferred_count": status.get("runtime_gate_evidence_deferred_count"),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--runner-json", type=Path, default=DEFAULT_RUNNER_JSON)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT_JSON)
    parser.add_argument("--status-json", type=Path, default=DEFAULT_STATUS_JSON)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--require-all-field-mirror-stubs", action="store_true")
    parser.add_argument("--min-online-inputs", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_online_native_stub_canary_artifacts(
        root=args.root,
        runner_json=args.runner_json,
        preflight_json=args.preflight_json,
        status_json=args.status_json,
        require_all_field_mirror_stubs=args.require_all_field_mirror_stubs,
        min_online_inputs=int(args.min_online_inputs),
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
