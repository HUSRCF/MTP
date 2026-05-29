#!/usr/bin/env python3
"""Run the online prelaunch typed-consumer canary end to end.

The canary is intentionally a no-op runtime bridge:

1. Run a small vLLM/AWQ trace that exports one prepared prelaunch handle table.
2. Feed that exported table to the native HIP typed-consumer stub.
3. Run the lab preflight gate, which verifies both the stub evidence and the
   trace performance summary point at the same online-exported input.

It never enables payload dereference, ready credit, descriptor-order mutation,
or WNA16 kernel-argument pass.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_CONFIG = (
    REPO_ROOT
    / "configs"
    / "trace"
    / "router_mtp_trace_external_prompt_gate_dolly_1_awq_vllm_gpu1_decode_gen16_native_input_export_canary.yaml"
)
DEFAULT_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_canary.json"
)
DEFAULT_PER_FIELD_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_per_field_canary.json"
)
DEFAULT_ENVELOPE_MIRROR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_kernel_envelope_mirror_canary.json"
)
DEFAULT_PACKED_WEIGHT_MIRROR_STUB_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "typed_consumer_stub_gpu1_online_prelaunch_input_packed_weight_mirror_canary.json"
)
DEFAULT_PREFLIGHT_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_online_prelaunch_native_stub_canary.json"
)
DEFAULT_PREFLIGHT_STATUS_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_lab_preflight_status_online_prelaunch_native_stub_canary.json"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_runner.json"
)
DEFAULT_ARTIFACT_CHECK_OUTPUT = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "online_prelaunch_native_stub_canary_artifact_check.json"
)
STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
PER_FIELD_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_DESCRIPTOR_PTR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_DESCRIPTOR",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_AUX_METADATA_HANDLE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
ENVELOPE_MIRROR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_POINTER_VISIBILITY",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_LIFETIME",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_KERNEL_CONSUMER_ENVELOPE",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCALE_METADATA_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]
PACKED_WEIGHT_MIRROR_STUB_MACROS = [
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_SCHEMA",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_ROW_ITERATION",
    "MTP_PREMAP_TYPED_CONSUMER_CHECK_PACKED_WEIGHT_MIRROR_FIELD",
    "MTP_PREMAP_TYPED_CONSUMER_HASH_ACCUMULATOR",
]


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resolve_repo_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


def trace_output_dir(config_path: Path) -> Path:
    config = _load_yaml(config_path)
    if not isinstance(config, dict):
        raise ValueError(f"trace config must be a mapping: {config_path}")
    raw_output = config.get("output_dir")
    if not isinstance(raw_output, str) or not raw_output:
        raise ValueError(f"trace config missing output_dir: {config_path}")
    return _resolve_repo_path(raw_output)


def exported_input_from_performance(performance_path: Path) -> Path:
    payload = json.loads(performance_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"performance summary must be an object: {performance_path}")
    if payload.get("runtime_shadow_premap_native_typed_consumer_input_export_enabled") is not True:
        raise ValueError("online typed-consumer input export was not enabled")
    count = payload.get("runtime_shadow_premap_native_typed_consumer_input_export_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise ValueError(f"invalid online typed-consumer input export count: {count!r}")
    first = payload.get(
        "runtime_shadow_premap_native_typed_consumer_input_export_first_path"
    )
    if not isinstance(first, str) or not first:
        raise ValueError("missing online typed-consumer export first_path")
    paths = payload.get("runtime_shadow_premap_native_typed_consumer_input_export_paths")
    if not isinstance(paths, list) or first not in paths:
        raise ValueError("online typed-consumer export first_path is not listed")
    input_path = _resolve_repo_path(first)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    return input_path


def _base_env(*, gpu_index: int | None) -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = f"{REPO_ROOT}:{REPO_ROOT / 'src'}"
    env["PYTHONPATH"] = (
        f"{pythonpath}:{env['PYTHONPATH']}" if env.get("PYTHONPATH") else pythonpath
    )
    if gpu_index is not None:
        env["HIP_VISIBLE_DEVICES"] = str(gpu_index)
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    return env


def _run(
    cmd: list[str],
    *,
    env: dict[str, str],
    dry_run: bool,
    allow_failure: bool = False,
) -> dict[str, object]:
    if dry_run:
        return {"cmd": cmd, "returncode": 0, "dry_run": True}
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    row: dict[str, object] = {
        "cmd": cmd,
        "returncode": int(result.returncode),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(
            f"command failed with code {result.returncode}: {' '.join(cmd)}\n"
            f"stdout tail:\n{result.stdout[-4000:]}\n"
            f"stderr tail:\n{result.stderr[-4000:]}"
        )
    return row


def _stub_command(
    *,
    input_json: Path,
    output_json: Path,
    device: int,
    offload_arch: str,
    macros: list[str] | tuple[str, ...] = STUB_MACROS,
) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/run_premap_typed_consumer_stub.py",
        "--device",
        str(device),
        "--input-json",
        str(input_json),
        "--offload-arch",
        offload_arch,
        "--output-json",
        str(output_json),
    ]
    for macro in macros:
        cmd.extend(["--macro", macro])
    return cmd


def _preflight_command(*, output_json: Path, summary_only: bool, defer_runner: bool) -> list[str]:
    cmd = [sys.executable, "scripts/run_premap_lab_preflight.py"]
    if summary_only:
        cmd.append("--summary-only")
    if defer_runner:
        cmd.append("--defer-online-prelaunch-runner-evidence")
    cmd.extend(["--output-json", str(output_json)])
    return cmd


def _artifact_check_command(
    *,
    runner_json: Path,
    preflight_json: Path,
    status_json: Path,
    output_json: Path,
) -> list[str]:
    return [
        sys.executable,
        "scripts/check_premap_online_native_stub_canary_artifacts.py",
        "--runner-json",
        str(runner_json),
        "--preflight-json",
        str(preflight_json),
        "--status-json",
        str(status_json),
        "--output-json",
        str(output_json),
    ]


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    return {}


def write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_canary(args: argparse.Namespace) -> dict[str, object]:
    trace_config = _resolve_repo_path(args.trace_config)
    output_dir = trace_output_dir(trace_config)
    performance_path = output_dir / "performance_summary.json"
    env = _base_env(gpu_index=args.gpu_index)
    steps: dict[str, object] = {}

    if not args.skip_trace:
        steps["trace"] = _run(
            [sys.executable, "scripts/trace_router_mtp_vllm.py", str(trace_config)],
            env=env,
            dry_run=bool(args.dry_run),
        )
    if args.dry_run:
        input_path = Path("<dry-run-online-input>")
    else:
        input_path = exported_input_from_performance(performance_path)

    stub_output = _resolve_repo_path(args.stub_output_json)
    if not args.skip_stub:
        steps["native_stub"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    per_field_stub_output = _resolve_repo_path(args.per_field_stub_output_json)
    if not args.skip_stub and not args.skip_per_field_stub:
        steps["native_stub_per_field"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=per_field_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=PER_FIELD_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    envelope_mirror_stub_output = _resolve_repo_path(
        args.envelope_mirror_stub_output_json
    )
    if not args.skip_stub and not args.skip_envelope_mirror_stub:
        steps["native_stub_kernel_envelope_mirror"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=envelope_mirror_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=ENVELOPE_MIRROR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    packed_weight_mirror_stub_output = _resolve_repo_path(
        args.packed_weight_mirror_stub_output_json
    )
    if not args.skip_stub and not args.skip_packed_weight_mirror_stub:
        steps["native_stub_packed_weight_mirror"] = _run(
            _stub_command(
                input_json=input_path,
                output_json=packed_weight_mirror_stub_output,
                device=int(args.stub_device),
                offload_arch=str(args.offload_arch),
                macros=PACKED_WEIGHT_MIRROR_STUB_MACROS,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
    preflight_output = _resolve_repo_path(args.preflight_output_json)
    preflight_status_output = _resolve_repo_path(args.preflight_status_output_json)
    if not args.skip_preflight:
        steps["preflight"] = _run(
            _preflight_command(
                output_json=preflight_output,
                summary_only=False,
                defer_runner=True,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )
        steps["preflight_status"] = _run(
            _preflight_command(
                output_json=preflight_status_output,
                summary_only=True,
                defer_runner=True,
            ),
            env=env,
            dry_run=bool(args.dry_run),
        )

    stub_payload = {} if args.dry_run else _load_json_if_exists(stub_output)
    per_field_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(per_field_stub_output)
    )
    envelope_mirror_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(envelope_mirror_stub_output)
    )
    packed_weight_mirror_stub_payload = (
        {} if args.dry_run else _load_json_if_exists(packed_weight_mirror_stub_output)
    )
    preflight_payload = (
        {} if args.dry_run else _load_json_if_exists(preflight_output)
    )
    preflight_status_payload = (
        {} if args.dry_run else _load_json_if_exists(preflight_status_output)
    )

    per_field_required = not bool(args.skip_stub or args.skip_per_field_stub)
    per_field_passed = bool(
        args.dry_run
        or not per_field_required
        or (
            per_field_stub_payload.get("passed") is True
            and per_field_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(per_field_stub_payload.get("input_json")))
            == input_path
        )
    )
    envelope_mirror_required = not bool(
        args.skip_stub or args.skip_envelope_mirror_stub
    )
    envelope_mirror_passed = bool(
        args.dry_run
        or not envelope_mirror_required
        or (
            envelope_mirror_stub_payload.get("passed") is True
            and envelope_mirror_stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(envelope_mirror_stub_payload.get("input_json")))
            == input_path
            and envelope_mirror_stub_payload.get("kernel_consumer_envelope_checked")
            is True
            and envelope_mirror_stub_payload.get("single_field_mirror_checked")
            is True
        )
    )
    packed_weight_mirror_required = not bool(
        args.skip_stub or args.skip_packed_weight_mirror_stub
    )
    packed_weight_mirror_passed = bool(
        args.dry_run
        or not packed_weight_mirror_required
        or (
            packed_weight_mirror_stub_payload.get("passed") is True
            and packed_weight_mirror_stub_payload.get("input_json") is not None
            and _resolve_repo_path(
                str(packed_weight_mirror_stub_payload.get("input_json"))
            )
            == input_path
            and packed_weight_mirror_stub_payload.get("single_field_mirror_checked")
            is True
            and packed_weight_mirror_stub_payload.get("single_field_mirror_field_name")
            == "packed_weight_descriptor"
        )
    )
    passed = bool(
        args.dry_run
        or (
            stub_payload.get("passed") is True
            and stub_payload.get("input_json") is not None
            and _resolve_repo_path(str(stub_payload.get("input_json"))) == input_path
            and per_field_passed
            and envelope_mirror_passed
            and packed_weight_mirror_passed
            and preflight_payload.get("passed") is True
            and preflight_status_payload.get("passed") is True
        )
    )
    failures: list[str] = []
    if not passed:
        if stub_payload.get("passed") is not True:
            failures.append("native_stub_not_passed")
        if stub_payload.get("input_json") is None:
            failures.append("native_stub_input_json_missing")
        elif not args.dry_run and _resolve_repo_path(str(stub_payload.get("input_json"))) != input_path:
            failures.append("native_stub_input_json_mismatch")
        if preflight_payload.get("passed") is not True:
            failures.append("preflight_not_passed")
        if preflight_status_payload.get("passed") is not True:
            failures.append("preflight_status_not_passed")
    if not per_field_passed:
        if per_field_stub_payload.get("passed") is not True:
            failures.append("native_stub_per_field_not_passed")
        if per_field_stub_payload.get("input_json") is None:
            failures.append("native_stub_per_field_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(str(per_field_stub_payload.get("input_json")))
            != input_path
        ):
            failures.append("native_stub_per_field_input_json_mismatch")
    if not envelope_mirror_passed:
        if envelope_mirror_stub_payload.get("passed") is not True:
            failures.append("native_stub_kernel_envelope_mirror_not_passed")
        if envelope_mirror_stub_payload.get("input_json") is None:
            failures.append("native_stub_kernel_envelope_mirror_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(str(envelope_mirror_stub_payload.get("input_json")))
            != input_path
        ):
            failures.append("native_stub_kernel_envelope_mirror_input_json_mismatch")
        if (
            envelope_mirror_stub_payload.get("kernel_consumer_envelope_checked")
            is not True
        ):
            failures.append("native_stub_kernel_envelope_not_checked")
        if envelope_mirror_stub_payload.get("single_field_mirror_checked") is not True:
            failures.append("native_stub_kernel_envelope_mirror_field_not_checked")
    if not packed_weight_mirror_passed:
        if packed_weight_mirror_stub_payload.get("passed") is not True:
            failures.append("native_stub_packed_weight_mirror_not_passed")
        if packed_weight_mirror_stub_payload.get("input_json") is None:
            failures.append("native_stub_packed_weight_mirror_input_json_missing")
        elif (
            not args.dry_run
            and _resolve_repo_path(
                str(packed_weight_mirror_stub_payload.get("input_json"))
            )
            != input_path
        ):
            failures.append("native_stub_packed_weight_mirror_input_json_mismatch")
        if packed_weight_mirror_stub_payload.get("single_field_mirror_checked") is not True:
            failures.append("native_stub_packed_weight_mirror_field_not_checked")
        if (
            packed_weight_mirror_stub_payload.get("single_field_mirror_field_name")
            != "packed_weight_descriptor"
        ):
            failures.append("native_stub_packed_weight_mirror_field_name_mismatch")

    required_evidence = preflight_status_payload.get("required_evidence")
    if not isinstance(required_evidence, dict):
        required_evidence = {}
    optional_evidence = preflight_status_payload.get("optional_evidence")
    if not isinstance(optional_evidence, dict):
        optional_evidence = {}

    return {
        "passed": passed,
        "failures": failures,
        "trace_config": str(trace_config),
        "trace_output_dir": str(output_dir),
        "performance_summary": str(performance_path),
        "online_prelaunch_input_json": str(input_path),
        "native_stub_output_json": str(stub_output),
        "per_field_native_stub_output_json": str(per_field_stub_output),
        "kernel_envelope_mirror_native_stub_output_json": str(
            envelope_mirror_stub_output
        ),
        "packed_weight_mirror_native_stub_output_json": str(
            packed_weight_mirror_stub_output
        ),
        "preflight_output_json": str(preflight_output),
        "preflight_status_output_json": str(preflight_status_output),
        "gpu_index": args.gpu_index,
        "stub_device": int(args.stub_device),
        "steps": steps,
        "stub_summary": {
            key: stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "per_field_stub_summary": {
            key: per_field_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "kernel_envelope_mirror_stub_summary": {
            key: envelope_mirror_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "kernel_consumer_envelope_checked",
                "kernel_consumer_envelope_payload_bytes",
                "kernel_consumer_envelope_passed_to_kernel",
                "single_field_mirror_checked",
                "single_field_mirror_field_name",
                "single_field_mirror_row_count",
                "single_field_mirror_row_ok_count",
                "single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "packed_weight_mirror_stub_summary": {
            key: packed_weight_mirror_stub_payload.get(key)
            for key in (
                "passed",
                "ok",
                "row_count",
                "row_ok_count",
                "error_count",
                "single_field_mirror_checked",
                "single_field_mirror_field_name",
                "single_field_mirror_row_count",
                "single_field_mirror_row_ok_count",
                "single_field_mirror_error_count",
                "payload_bytes",
                "passed_to_kernel",
                "changes_kernel_launch_args",
                "input_json",
            )
        },
        "preflight_summary": {
            "passed": preflight_payload.get("passed"),
            "failures": preflight_payload.get("failures"),
            "deferred_online_prelaunch_runner_evidence": (
                (preflight_payload.get("lab_gate_status_summary") or {}).get(
                    "deferred_online_prelaunch_runner_evidence"
                )
                if isinstance(
                    preflight_payload.get("lab_gate_status_summary"), dict
                )
                else None
            ),
        },
        "preflight_status_summary": {
            "passed": preflight_status_payload.get("passed"),
            "runtime_gate_evidence_deferred_count": (
                preflight_status_payload.get("runtime_gate_evidence_deferred_count")
            ),
            "strict_default_gate_evidence_deferred_count": (
                preflight_status_payload.get(
                    "strict_default_gate_evidence_deferred_count"
                )
            ),
            "required_evidence_passed": required_evidence.get("passed"),
            "required_evidence_present_count": required_evidence.get(
                "present_count"
            ),
            "required_evidence_passed_count": required_evidence.get("passed_count"),
            "required_evidence_required_count": required_evidence.get(
                "required_count"
            ),
            "optional_evidence_passed": optional_evidence.get("passed"),
            "optional_evidence_present_count": optional_evidence.get(
                "present_count"
            ),
            "optional_evidence_passed_count": optional_evidence.get("passed_count"),
            "optional_evidence_required_count": optional_evidence.get(
                "required_count"
            ),
            "native_typed_consumer_bridge_required": preflight_status_payload.get(
                "native_typed_consumer_bridge_required"
            ),
            "native_stub_online_invocation_canary_required": (
                preflight_status_payload.get(
                    "native_stub_online_invocation_canary_required"
                )
            ),
            "payload_bytes_required": preflight_status_payload.get(
                "payload_bytes_required"
            ),
            "passed_to_kernel_required": preflight_status_payload.get(
                "passed_to_kernel_required"
            ),
            "changes_kernel_launch_args_required": preflight_status_payload.get(
                "changes_kernel_launch_args_required"
            ),
        },
    }


def finalize_report_with_strict_preflight(
    *,
    args: argparse.Namespace,
    payload: dict[str, object],
) -> dict[str, object]:
    if args.dry_run or args.skip_preflight:
        return payload
    env = _base_env(gpu_index=args.gpu_index)
    steps = payload.setdefault("steps", {})
    if not isinstance(steps, dict):
        steps = {}
        payload["steps"] = steps
    preflight_output = _resolve_repo_path(args.preflight_output_json)
    preflight_status_output = _resolve_repo_path(args.preflight_status_output_json)
    steps["final_preflight"] = _run(
        _preflight_command(
            output_json=preflight_output,
            summary_only=False,
            defer_runner=False,
        ),
        env=env,
        dry_run=False,
    )
    steps["final_preflight_status"] = _run(
        _preflight_command(
            output_json=preflight_status_output,
            summary_only=True,
            defer_runner=False,
        ),
        env=env,
        dry_run=False,
    )
    final_preflight_payload = _load_json_if_exists(preflight_output)
    final_status_payload = _load_json_if_exists(preflight_status_output)
    final_preflight_summary = {
        "passed": final_preflight_payload.get("passed"),
        "failures": final_preflight_payload.get("failures"),
    }
    required_evidence = final_status_payload.get("required_evidence")
    if not isinstance(required_evidence, dict):
        required_evidence = {}
    optional_evidence = final_status_payload.get("optional_evidence")
    if not isinstance(optional_evidence, dict):
        optional_evidence = {}
    final_status_summary = {
        "passed": final_status_payload.get("passed"),
        "runtime_gate_evidence_deferred_count": final_status_payload.get(
            "runtime_gate_evidence_deferred_count"
        ),
        "strict_default_gate_evidence_deferred_count": final_status_payload.get(
            "strict_default_gate_evidence_deferred_count"
        ),
        "required_evidence_passed": required_evidence.get("passed"),
        "required_evidence_present_count": required_evidence.get("present_count"),
        "required_evidence_passed_count": required_evidence.get("passed_count"),
        "required_evidence_required_count": required_evidence.get("required_count"),
        "optional_evidence_passed": optional_evidence.get("passed"),
        "optional_evidence_present_count": optional_evidence.get("present_count"),
        "optional_evidence_passed_count": optional_evidence.get("passed_count"),
        "optional_evidence_required_count": optional_evidence.get("required_count"),
        "native_typed_consumer_bridge_required": final_status_payload.get(
            "native_typed_consumer_bridge_required"
        ),
        "native_stub_online_invocation_canary_required": final_status_payload.get(
            "native_stub_online_invocation_canary_required"
        ),
        "payload_bytes_required": final_status_payload.get("payload_bytes_required"),
        "passed_to_kernel_required": final_status_payload.get(
            "passed_to_kernel_required"
        ),
        "changes_kernel_launch_args_required": final_status_payload.get(
            "changes_kernel_launch_args_required"
        ),
    }
    payload["final_preflight_summary"] = final_preflight_summary
    payload["final_preflight_status_summary"] = final_status_summary
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    if final_preflight_payload.get("passed") is not True:
        failures.append("final_preflight_not_passed")
    if final_status_payload.get("passed") is not True:
        failures.append("final_preflight_status_not_passed")
    payload["failures"] = failures
    payload["passed"] = bool(payload.get("passed") is True and not failures)
    return payload


def finalize_report_with_artifact_check(
    *,
    args: argparse.Namespace,
    payload: dict[str, object],
    runner_json: Path,
) -> dict[str, object]:
    if args.dry_run or args.skip_preflight or args.skip_artifact_check:
        return payload
    env = _base_env(gpu_index=args.gpu_index)
    steps = payload.setdefault("steps", {})
    if not isinstance(steps, dict):
        steps = {}
        payload["steps"] = steps
    artifact_output = _resolve_repo_path(args.artifact_check_output_json)
    steps["artifact_check"] = _run(
        _artifact_check_command(
            runner_json=runner_json,
            preflight_json=_resolve_repo_path(args.preflight_output_json),
            status_json=_resolve_repo_path(args.preflight_status_output_json),
            output_json=artifact_output,
        ),
        env=env,
        dry_run=False,
        allow_failure=True,
    )
    artifact_payload = _load_json_if_exists(artifact_output)
    payload["artifact_check_output_json"] = str(artifact_output)
    payload["artifact_check_summary"] = {
        "passed": artifact_payload.get("passed"),
        "failures": artifact_payload.get("failures"),
        "runner_stub_row_count": artifact_payload.get("runner_stub_row_count"),
        "runner_stub_row_ok_count": artifact_payload.get("runner_stub_row_ok_count"),
        "stage1_deferred_count": artifact_payload.get("stage1_deferred_count"),
        "final_deferred_count": artifact_payload.get("final_deferred_count"),
        "status_deferred_count": artifact_payload.get("status_deferred_count"),
    }
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
    if artifact_payload.get("passed") is not True:
        failures.append("artifact_consistency_check_failed")
    payload["failures"] = failures
    payload["passed"] = bool(payload.get("passed") is True and not failures)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-config", type=Path, default=DEFAULT_TRACE_CONFIG)
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--stub-device", type=int, default=0)
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--stub-output-json", type=Path, default=DEFAULT_STUB_OUTPUT)
    parser.add_argument(
        "--per-field-stub-output-json",
        type=Path,
        default=DEFAULT_PER_FIELD_STUB_OUTPUT,
    )
    parser.add_argument(
        "--envelope-mirror-stub-output-json",
        type=Path,
        default=DEFAULT_ENVELOPE_MIRROR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--packed-weight-mirror-stub-output-json",
        type=Path,
        default=DEFAULT_PACKED_WEIGHT_MIRROR_STUB_OUTPUT,
    )
    parser.add_argument(
        "--preflight-output-json",
        type=Path,
        default=DEFAULT_PREFLIGHT_OUTPUT,
    )
    parser.add_argument(
        "--preflight-status-output-json",
        type=Path,
        default=DEFAULT_PREFLIGHT_STATUS_OUTPUT,
    )
    parser.add_argument(
        "--artifact-check-output-json",
        type=Path,
        default=DEFAULT_ARTIFACT_CHECK_OUTPUT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--skip-trace", action="store_true")
    parser.add_argument("--skip-stub", action="store_true")
    parser.add_argument("--skip-per-field-stub", action="store_true")
    parser.add_argument("--skip-envelope-mirror-stub", action="store_true")
    parser.add_argument("--skip-packed-weight-mirror-stub", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--skip-artifact-check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_canary(args)
    output = _resolve_repo_path(args.output_json)
    write_report(output, payload)
    payload = finalize_report_with_strict_preflight(args=args, payload=payload)
    write_report(output, payload)
    payload = finalize_report_with_artifact_check(
        args=args,
        payload=payload,
        runner_json=output,
    )
    write_report(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
