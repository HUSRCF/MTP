#!/usr/bin/env python3
"""Run read-only preflight checks for the premap lab gate artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.check_gate_evidence_paths import check_gate_evidence_paths
from scripts.check_runtime_gate_evidence_paths import scan_runtime_gate_evidence_paths


DEFAULT_TRACE_CONFIGS = [
    "configs/trace/router_mtp_trace_external_prompt_gate_dolly_128_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml",
    "configs/trace/router_mtp_trace_external_prompt_gate_dolly_512_awq_vllm_gpu1_decode_gen64_longrun_audit.yaml",
]
DEFAULT_READONLY_GATE = (
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_kernel_arg_shadow.yaml"
)
DEFAULT_CANARY_GATE = (
    "configs/runtime/"
    "premap_consumer_readonly_gate_dolly128_gen64_awq_w7900_gpu1_live_connected_blocked_canary.yaml"
)


def _path_label(path: Path, *, root: Path) -> str:
    path = path.resolve()
    root = root.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def _path_for_label(raw_path: str, root: Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else root / path


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _check_trace_config(
    config_path: Path,
    *,
    root: Path,
    expected_readonly_gate: str,
) -> dict[str, Any]:
    config_path = config_path if config_path.is_absolute() else root / config_path
    label = _path_label(config_path, root=root)
    failures: list[str] = []
    try:
        config = _load_yaml(config_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        return {
            "config_path": label,
            "passed": False,
            "failures": [f"{type(exc).__name__}:{exc}"],
        }
    shadow = ((config or {}).get("trace") or {}).get("runtime_shadow") or {}
    readonly_gate = shadow.get("premap_consumer_readonly_gate_path")
    readonly_gate_label = (
        _path_label(_path_for_label(readonly_gate, root), root=root)
        if isinstance(readonly_gate, str)
        else None
    )
    expected_readonly_gate_label = _path_label(
        _path_for_label(expected_readonly_gate, root),
        root=root,
    )
    kernel_arg_pass = bool(
        shadow.get("premap_kernel_arg_handoff_kernel_arg_pass_enabled", False)
    )
    live_enabled = bool(shadow.get("premap_kernel_arg_handoff_live_enabled", False))
    require_gate = bool(shadow.get("premap_consumer_require_readonly_gate", False))
    if readonly_gate_label != expected_readonly_gate_label:
        failures.append("readonly_gate_path_mismatch")
    if kernel_arg_pass:
        failures.append("kernel_arg_pass_enabled")
    if live_enabled:
        failures.append("live_enabled_in_default_lab_config")
    if not require_gate:
        failures.append("readonly_gate_not_required")
    return {
        "config_path": label,
        "passed": not failures,
        "failures": failures,
        "readonly_gate_path": readonly_gate,
        "readonly_gate_path_label": readonly_gate_label,
        "expected_readonly_gate_path_label": expected_readonly_gate_label,
        "premap_consumer_require_readonly_gate": require_gate,
        "premap_kernel_arg_handoff_live_enabled": live_enabled,
        "premap_kernel_arg_handoff_kernel_arg_pass_enabled": kernel_arg_pass,
    }


def run_premap_lab_preflight(
    *,
    root: Path,
    runtime_pattern: str = "configs/runtime/*.yaml",
    trace_configs: list[str] | None = None,
    default_readonly_gate: str = DEFAULT_READONLY_GATE,
    canary_gate: str = DEFAULT_CANARY_GATE,
    allow_missing_evidence: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    trace_configs = trace_configs or list(DEFAULT_TRACE_CONFIGS)
    gate_pair_failures: list[str] = []
    default_gate_path = _path_label(
        _path_for_label(default_readonly_gate, root),
        root=root,
    )
    canary_gate_path = _path_label(_path_for_label(canary_gate, root), root=root)
    if default_gate_path == canary_gate_path:
        gate_pair_failures.append("default_readonly_gate_equals_canary_gate")
    runtime_scan = scan_runtime_gate_evidence_paths(
        runtime_pattern,
        root=root,
        allow_missing=allow_missing_evidence,
        allow_missing_section=True,
        require_json=True,
    )
    strict_gate_checks: dict[str, Any] = {}
    for label, raw_path in {
        "default_readonly_gate": default_readonly_gate,
        "connected_blocked_canary_gate": canary_gate,
    }.items():
        try:
            strict_gate_checks[label] = check_gate_evidence_paths(
                Path(raw_path),
                root=root,
                allow_missing=allow_missing_evidence,
                allow_missing_section=False,
                require_json=True,
            )
        except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
            strict_gate_checks[label] = {
                "gate_path": _path_label(_path_for_label(raw_path, root), root=root),
                "passed": False,
                "failures": [f"{type(exc).__name__}:{exc}"],
            }

    trace_results = [
        _check_trace_config(
            Path(config_path),
            root=root,
            expected_readonly_gate=default_readonly_gate,
        )
        for config_path in trace_configs
    ]
    failures: list[str] = []
    failures.extend(gate_pair_failures)
    if not runtime_scan.get("passed", False):
        failures.append("runtime_gate_evidence_scan_failed")
    for label, result in strict_gate_checks.items():
        if not result.get("passed", False):
            failures.append(f"{label}_evidence_check_failed")
    for result in trace_results:
        if not result.get("passed", False):
            failures.append(f"{result['config_path']}:trace_config_check_failed")

    return {
        "passed": not failures,
        "failures": failures,
        "gate_pair_failures": gate_pair_failures,
        "runtime_gate_evidence_scan": runtime_scan,
        "strict_gate_evidence_checks": strict_gate_checks,
        "trace_config_checks": trace_results,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--runtime-pattern", default="configs/runtime/*.yaml")
    parser.add_argument("--trace-config", action="append", dest="trace_configs")
    parser.add_argument("--default-readonly-gate", default=DEFAULT_READONLY_GATE)
    parser.add_argument("--canary-gate", default=DEFAULT_CANARY_GATE)
    parser.add_argument(
        "--allow-missing-evidence",
        action="store_true",
        help="Allow missing evidence paths while still checking schema and config wiring.",
    )
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_premap_lab_preflight(
        root=args.root,
        runtime_pattern=args.runtime_pattern,
        trace_configs=args.trace_configs,
        default_readonly_gate=args.default_readonly_gate,
        canary_gate=args.canary_gate,
        allow_missing_evidence=args.allow_missing_evidence,
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
