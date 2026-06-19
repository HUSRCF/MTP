#!/usr/bin/env python3
"""Check the default lab gate for prefetch/premap experiments.

This checker combines the current evidence boundary:

* full payload fetch is blocked by measured-copy ready-time evidence;
* metadata is not default-enabled without positive setup evidence;
* premap may be used as a lab path only when setup evidence and address
  capacity evidence both pass.

It is a lab preflight checker, not an endpoint latency benchmark.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def check_prefetch_lab_default_gate(path: Path, *, root: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    failures: list[str] = []

    full_fetch = _check_full_fetch(config.get("full_fetch") or {}, root=root)
    metadata = _check_metadata(config.get("metadata") or {}, root=root)
    premap = _check_premap(config.get("premap") or {}, root=root)
    for section_name, section in (
        ("full_fetch", full_fetch),
        ("metadata", metadata),
        ("premap", premap),
    ):
        for failure in section["failures"]:
            failures.append(f"{section_name}:{failure}")

    return {
        "passed": not failures,
        "failures": failures,
        "boundary": (
            "Lab default preflight only; not endpoint TPOT and not a real "
            "vLLM payload/cache-manager performance claim."
        ),
        "gate_id": config.get("gate_id"),
        "decisions": {
            "full_fetch": full_fetch["decision"],
            "metadata": metadata["decision"],
            "premap": premap["decision"],
        },
        "sections": {
            "full_fetch": full_fetch,
            "metadata": metadata,
            "premap": premap,
        },
    }


def _check_full_fetch(section: dict[str, Any], *, root: Path) -> dict[str, Any]:
    failures: list[str] = []
    expected_default = bool(section.get("default_enabled", False))
    report_path = _resolve(section.get("ready_time_gate_report"), root=root)
    report = _load_json(report_path, failures, label="ready_time_gate_report")
    passed = bool(report.get("passed", False)) if isinstance(report, dict) else False
    allow = _ready_time_allow_full_fetch(report, failures)
    metrics = report.get("metrics") if isinstance(report, dict) else None
    metrics = metrics if isinstance(metrics, dict) else {}
    if not passed:
        failures.append("ready_time_gate_report_not_passed")
    if allow:
        failures.append("ready_time_gate_report_allows_full_fetch")
    if expected_default:
        failures.append("full_fetch_default_enabled_despite_ready_time_block")
    return {
        "decision": "blocked_by_ready_time_measured_copy",
        "failures": failures,
        "default_enabled": expected_default,
        "ready_time_gate_report": str(report_path),
        "ready_time_report_passed": passed,
        "ready_time_allow_full_fetch": allow,
        "ready_time_decision_reason": (
            _ready_time_decision_reason(report) if isinstance(report, dict) else None
        ),
        "ready_time_threshold_failures": _string_list(
            report.get("threshold_failures") if isinstance(report, dict) else None
        ),
        "ready_time_demand_hit_rate": _optional_float(metrics, "demand_hit_rate"),
        "ready_time_ready_late_miss_rate": _optional_float(
            metrics,
            "ready_late_miss_rate",
        ),
        "ready_time_used_per_issued_fetch": _optional_float(
            metrics,
            "used_per_issued_fetch",
        ),
        "ready_time_issued_fetch_count": _optional_int(
            metrics,
            "issued_fetch_count",
        ),
        "ready_time_used_fetch_count": _optional_int(metrics, "used_fetch_count"),
    }


def _ready_time_allow_full_fetch(
    report: dict[str, Any],
    failures: list[str],
) -> bool:
    artifact_kind = report.get("artifact_kind")
    runtime_allow = report.get("full_fetch_runtime_allowed")
    if artifact_kind == "premap_payload_cache_full_fetch_decision_gate":
        if not isinstance(runtime_allow, bool):
            failures.append("ready_time_gate_report_missing_full_fetch_runtime_allowed")
            return False
        _check_full_fetch_decision_gate_noop_safety(report, failures)
        return runtime_allow
    if isinstance(runtime_allow, bool):
        if artifact_kind != "premap_payload_cache_full_fetch_decision_gate":
            failures.append("ready_time_gate_report_artifact_kind_mismatch")
            return False
        return runtime_allow
    return bool(report.get("allow_full_fetch", False))


def _check_full_fetch_decision_gate_noop_safety(
    report: dict[str, Any],
    failures: list[str],
) -> None:
    if report.get("payload_bytes") != 0:
        failures.append("ready_time_gate_report_payload_bytes_nonzero")
    for field in (
        "payload_transfer_enabled",
        "payload_deref_allowed",
        "ready_credit",
        "ready_before_demand_credit",
        "real_ready_credit_granted",
        "kernel_arg_pass_allowed",
        "passed_to_kernel",
        "changes_kernel_launch_args",
        "uses_current_wna16_args",
        "passes_current_wna16_args",
        "measures_tpot",
        "measures_vllm_latency",
    ):
        if report.get(field) is not False:
            failures.append(f"ready_time_gate_report_{field}_not_false")


def _ready_time_decision_reason(report: dict[str, Any]) -> str | None:
    reason = report.get("full_fetch_block_reason")
    if isinstance(reason, str):
        return reason
    reason = report.get("decision_reason")
    return reason if isinstance(reason, str) else None


def _check_metadata(section: dict[str, Any], *, root: Path) -> dict[str, Any]:
    failures: list[str] = []
    default_enabled = bool(section.get("default_enabled", False))
    summary_path = _resolve(section.get("summary"), root=root)
    summary = _load_json(summary_path, failures, label="summary")
    metadata_positive_count = (
        int(summary.get("metadata_positive_count", 0) or 0)
        if isinstance(summary, dict)
        else 0
    )
    max_default_positive = int(section.get("max_default_positive_count", 0) or 0)
    if default_enabled:
        failures.append("metadata_default_enabled")
    if default_enabled and metadata_positive_count <= max_default_positive:
        failures.append("metadata_default_enabled_without_positive_evidence")
    return {
        "decision": "shadow_only",
        "failures": failures,
        "default_enabled": default_enabled,
        "summary": str(summary_path),
        "metadata_positive_count": metadata_positive_count,
        "max_default_positive_count": max_default_positive,
    }


def _check_premap(section: dict[str, Any], *, root: Path) -> dict[str, Any]:
    failures: list[str] = []
    default_enabled = bool(section.get("default_enabled", False))
    summary_path = _resolve(section.get("summary"), root=root)
    summary = _load_json(summary_path, failures, label="summary")
    premap_positive_count = (
        int(summary.get("premap_positive_count", 0) or 0)
        if isinstance(summary, dict)
        else 0
    )
    min_positive_count = int(section.get("min_positive_count", 1) or 1)
    if premap_positive_count < min_positive_count:
        failures.append(f"premap_positive_count_too_low:{premap_positive_count}")

    capacity_path = _resolve(section.get("capacity_gate"), root=root)
    capacity = _load_yaml_or_failure(capacity_path, failures, label="capacity_gate")
    capacity_gate = capacity.get("capacity_gate") or {}
    recommended = int(capacity_gate.get("recommended_capacity_entries", 0) or 0)
    no_eviction = int(capacity_gate.get("no_eviction_capacity_entries", 0) or 0)
    min_capacity = int(section.get("min_capacity_entries", 1) or 1)
    if recommended < min_capacity:
        failures.append(f"recommended_capacity_below_min:{recommended}")
    if no_eviction <= 0:
        failures.append("no_eviction_capacity_missing")
    if no_eviction > recommended:
        failures.append(
            f"no_eviction_capacity_above_recommended:{no_eviction}>{recommended}"
        )
    if not default_enabled:
        failures.append("premap_default_disabled")
    return {
        "decision": "lab_enabled_descriptor_prep_only",
        "failures": failures,
        "default_enabled": default_enabled,
        "summary": str(summary_path),
        "capacity_gate": str(capacity_path),
        "premap_positive_count": premap_positive_count,
        "min_positive_count": min_positive_count,
        "recommended_capacity_entries": recommended,
        "no_eviction_capacity_entries": no_eviction,
        "min_capacity_entries": min_capacity,
    }


def _resolve(value: Any, *, root: Path) -> Path:
    if value in (None, ""):
        return Path("<missing>")
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else root / path


def _load_json(path: Path, failures: list[str], *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}_load_failed:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{label}_not_object")
        return {}
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object.")
    return payload


def _load_yaml_or_failure(
    path: Path,
    failures: list[str],
    *,
    label: str,
) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        failures.append(f"{label}_load_failed:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"{label}_not_object")
        return {}
    return payload


def _optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = check_prefetch_lab_default_gate(args.config, root=args.root)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
