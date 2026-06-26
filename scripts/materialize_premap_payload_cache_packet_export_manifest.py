#!/usr/bin/env python3
"""Materialize a payload-cache packet-export manifest from performance summary.

This is a payloadless bridge from online runtime shadow output to replay/manager
consumers.  It does not run the native producer-state stub, move payload bytes,
grant ready credit, or pass kernel arguments.  It only exposes the exported
packet list in the same shape consumed by stream replay tools.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF
DEFAULT_PERFORMANCE_SUMMARY = (
    REPO_ROOT
    / "data/traces/external_prompt_gate_dolly_4_awq_vllm_gpu1_decode_gen64_shifted_issue_runtime_shadow_smoke/performance_summary.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs/reports/premap_kernel_consumer/premap_payload_cache_packet_export_manifest_shifted_issue_runtime_shadow_dolly4_gen64_v1.json"
)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"performance summary must be a JSON object: {path}")
    return payload


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _strict_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _strict_zero(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0


def _required_int(
    summary: dict[str, Any],
    key: str,
    failures: list[str],
) -> int:
    value = summary.get(key)
    if not _is_int(value):
        failures.append(f"{key}_invalid")
        return 0
    if int(value) < 0:
        failures.append(f"{key}_negative")
        return 0
    return int(value)


def _normalize_packet_paths(
    paths: list[Any],
    *,
    summary_path: Path,
    failures: list[str],
) -> list[str]:
    resolved: list[str] = []
    for index, raw_path in enumerate(paths):
        if not isinstance(raw_path, str) or not raw_path:
            continue
        candidate = Path(raw_path)
        if candidate.is_absolute():
            if not candidate.is_file():
                failures.append(f"packet_export_path_{index}_missing")
            resolved.append(str(candidate))
            continue
        summary_relative = summary_path.parent / candidate
        if not summary_relative.is_file():
            failures.append(f"packet_export_path_{index}_missing")
        resolved.append(str(summary_relative.resolve()))
    return resolved


SHIFTED_SAFE_FALSE_FIELDS = (
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)


def _issue_hash(experts: list[int]) -> str:
    value = FNV_OFFSET
    count = 0
    for expert_id in experts:
        value ^= int(expert_id) & 0xFFFFFFFF
        value = (value * FNV_PRIME) & U64_MASK
        count += 1
    value ^= count & 0xFFFFFFFF
    value = (value * FNV_PRIME) & U64_MASK
    return f"{value:016x}"


def _load_packet(path: Path, failures: list[str], *, prefix: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"{prefix}_load_failed:{exc.__class__.__name__}:{exc}")
        return None
    if not isinstance(payload, dict):
        failures.append(f"{prefix}_not_json_object")
        return None
    return payload


def _check_safe_false_fields(
    payload: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    for field in SHIFTED_SAFE_FALSE_FIELDS:
        if payload.get(field) is not False:
            failures.append(f"{prefix}_{field}_not_false")
    if not _strict_zero(payload.get("payload_bytes")):
        failures.append(f"{prefix}_payload_bytes_not_zero")


def _issue_experts_from_packet(
    packet: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> list[int]:
    raw_experts = packet.get("issue_candidate_experts")
    if not isinstance(raw_experts, list):
        failures.append(f"{prefix}_issue_candidate_experts_invalid")
        return []
    experts: list[int] = []
    seen: set[int] = set()
    for offset, value in enumerate(raw_experts):
        if not _is_int(value) or int(value) < 0:
            failures.append(f"{prefix}_issue_candidate_expert_{offset}_invalid")
            continue
        expert_id = int(value)
        seen.add(expert_id)
        experts.append(expert_id)
    return experts


def _check_issue_mirror(
    payload: dict[str, Any],
    experts: list[int],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    expected_count = len(experts)
    expected_first = experts[0] if experts else -1
    expected_last = experts[-1] if experts else -1
    expected_hash = _issue_hash(experts)
    checks: tuple[tuple[str, int | str], ...] = (
        ("issue_candidate_count", expected_count),
        ("issue_candidate_first_expert", expected_first),
        ("issue_candidate_last_expert", expected_last),
        ("issue_candidate_hash", expected_hash),
    )
    for key, expected in checks:
        if payload.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")


def _check_packet_contract(
    packet: dict[str, Any],
    failures: list[str],
    *,
    packet_index: int,
    packet_path: str,
    issue_lead_tokens: int | None,
    allow_empty_config_packets: bool,
    allow_config_token_source: bool,
) -> dict[str, Any]:
    prefix = f"packet_{packet_index}"
    result = {
        "loaded_packet_count": 1,
        "schedulable": False,
        "empty_issue_exempt": False,
        "nonempty_issue": False,
        "clamped": False,
        "demand_key": None,
        "issue_key": None,
        "issue_candidate_count": 0,
        "issue_candidate_hash": None,
        "packet_path": packet_path,
    }
    _check_safe_false_fields(packet, failures, prefix=prefix)
    if packet.get("ready") is not True:
        failures.append(f"{prefix}_ready_not_true")
    raw_layer_id = packet.get("layer_id")
    layer_id = int(raw_layer_id) if _is_int(raw_layer_id) and int(raw_layer_id) >= 0 else -1
    if layer_id < 0:
        failures.append(f"{prefix}_layer_id_invalid")
    experts = _issue_experts_from_packet(packet, failures, prefix=prefix)
    _check_issue_mirror(packet, experts, failures, prefix=prefix)

    context = packet.get("_export_context")
    if not isinstance(context, dict):
        failures.append(f"{prefix}_export_context_missing")
        return result
    _check_safe_false_fields(context, failures, prefix=f"{prefix}_export_context")
    if context.get("ready") is not True:
        failures.append(f"{prefix}_export_context_ready_not_true")
    _check_issue_mirror(context, experts, failures, prefix=f"{prefix}_export_context")
    context_layer_id = context.get("layer_id")
    if not _is_int(context_layer_id) or int(context_layer_id) != layer_id:
        failures.append(f"{prefix}_export_context_layer_id_mismatch")

    source = context.get("token_index_source")
    token_index = context.get("token_index")
    if not experts and allow_empty_config_packets and source == "config":
        result["empty_issue_exempt"] = True
        return result
    if allow_empty_config_packets and not experts and source != "config":
        failures.append(f"{prefix}_empty_issue_source_not_config")
    if source == "decode_workload_collector":
        pass
    elif source == "config" and allow_config_token_source:
        pass
    else:
        failures.append(f"{prefix}_token_index_source_unexpected")
    if not _is_int(token_index) or int(token_index) < 0:
        failures.append(f"{prefix}_token_index_invalid")
        return result
    if not _is_int(context.get("sample_idx")):
        failures.append(f"{prefix}_sample_idx_invalid")
        return result
    record_id = context.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        failures.append(f"{prefix}_record_id_invalid")
        return result
    sequence_id = context.get("sequence_id")
    if not _is_int(sequence_id) or int(sequence_id) < 0:
        failures.append(f"{prefix}_sequence_id_invalid")
        return result
    if issue_lead_tokens is None:
        failures.append(f"{prefix}_issue_lead_tokens_unavailable")
        return result
    demand_token_index = int(token_index)
    unclamped_issue_token_index = demand_token_index - int(issue_lead_tokens)
    issue_token_index = max(0, unclamped_issue_token_index)
    result.update(
        {
            "schedulable": True,
            "nonempty_issue": bool(experts),
            "clamped": unclamped_issue_token_index < 0,
            "demand_key": (
                int(context["sample_idx"]),
                record_id,
                int(sequence_id),
                layer_id,
                demand_token_index,
            ),
            "issue_key": (
                int(context["sample_idx"]),
                record_id,
                int(sequence_id),
                layer_id,
                issue_token_index,
            ),
            "issue_candidate_count": len(experts),
            "issue_candidate_hash": _issue_hash(experts),
        }
    )
    return result


def _empty_packet_stats() -> dict[str, Any]:
    return {
        "loaded_packet_count": 0,
        "schedulable_packet_count": 0,
        "empty_issue_exempt_count": 0,
        "nonempty_issue_count": 0,
        "clamped_issue_count": 0,
        "duplicate_demand_key_count": 0,
        "duplicate_issue_key_count": 0,
        "unique_demand_key_count": 0,
        "unique_issue_key_count": 0,
        "total_issue_candidates": 0,
        "issue_hash_count": 0,
        "issue_hash_unique_count": 0,
        "first_nonempty_issue_index": -1,
        "first_nonempty_issue_path": None,
        "first_nonempty_issue_count": 0,
        "first_nonempty_issue_hash": None,
    }


def _accumulate_packet_stats(packet_results: list[dict[str, Any]]) -> dict[str, Any]:
    stats = _empty_packet_stats()
    demand_keys: set[tuple[Any, ...]] = set()
    issue_keys: set[tuple[Any, ...]] = set()
    issue_hashes: list[str] = []
    for packet_index, result in enumerate(packet_results):
        stats["loaded_packet_count"] += int(result.get("loaded_packet_count", 0))
        if result.get("empty_issue_exempt"):
            stats["empty_issue_exempt_count"] += 1
        if result.get("nonempty_issue"):
            stats["nonempty_issue_count"] += 1
        if not result.get("schedulable"):
            continue
        stats["schedulable_packet_count"] += 1
        if result.get("clamped"):
            stats["clamped_issue_count"] += 1
        demand_key = result.get("demand_key")
        if demand_key in demand_keys:
            stats["duplicate_demand_key_count"] += 1
        demand_keys.add(demand_key)
        issue_key = result.get("issue_key")
        if issue_key in issue_keys:
            stats["duplicate_issue_key_count"] += 1
        issue_keys.add(issue_key)
        issue_count = int(result.get("issue_candidate_count", 0))
        issue_hash = result.get("issue_candidate_hash")
        stats["total_issue_candidates"] += max(0, issue_count)
        if isinstance(issue_hash, str) and issue_hash:
            issue_hashes.append(issue_hash)
        if int(stats["first_nonempty_issue_index"]) < 0 and issue_count > 0:
            stats["first_nonempty_issue_index"] = packet_index
            stats["first_nonempty_issue_path"] = result.get("packet_path")
            stats["first_nonempty_issue_count"] = issue_count
            stats["first_nonempty_issue_hash"] = issue_hash
    stats["unique_demand_key_count"] = len(demand_keys)
    stats["unique_issue_key_count"] = len(issue_keys)
    stats["issue_hash_count"] = len(issue_hashes)
    stats["issue_hash_unique_count"] = len(set(issue_hashes))
    return stats


def _compare_shifted_packet_stats(
    packet_stats: dict[str, Any],
    shifted: dict[str, Any],
    failures: list[str],
) -> None:
    checks = (
        ("schedulable_packet_count", "shifted_issue_schedulable_packet_count_packet_mismatch"),
        ("empty_issue_exempt_count", "shifted_issue_empty_issue_exempt_count_packet_mismatch"),
        ("clamped_issue_count", "shifted_issue_clamped_issue_count_packet_mismatch"),
        ("duplicate_demand_key_count", "shifted_issue_duplicate_demand_key_count_packet_mismatch"),
        ("duplicate_issue_key_count", "shifted_issue_duplicate_issue_key_count_packet_mismatch"),
        ("unique_demand_key_count", "shifted_issue_unique_demand_key_count_packet_mismatch"),
        ("unique_issue_key_count", "shifted_issue_unique_issue_key_count_packet_mismatch"),
        ("total_issue_candidates", "shifted_issue_total_issue_candidates_packet_mismatch"),
        ("issue_hash_count", "shifted_issue_issue_hash_count_packet_mismatch"),
        ("issue_hash_unique_count", "shifted_issue_issue_hash_unique_count_packet_mismatch"),
    )
    for key, failure in checks:
        if packet_stats.get(key) != shifted.get(key):
            failures.append(failure)


def _normalize_optional_path(
    raw_path: Any,
    *,
    summary_path: Path,
) -> str | None:
    if not isinstance(raw_path, str) or not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return str(candidate)
    return str((summary_path.parent / candidate).resolve())


def _compare_first_nonempty_summary(
    summary: dict[str, Any],
    packet_stats: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
    summary_path: Path,
) -> None:
    checks: tuple[tuple[str, Any, str], ...] = (
        (
            "first_nonempty_issue_index",
            packet_stats.get("first_nonempty_issue_index"),
            "packet_export_first_nonempty_issue_index_mismatch",
        ),
        (
            "first_nonempty_issue_count",
            packet_stats.get("first_nonempty_issue_count"),
            "packet_export_first_nonempty_issue_count_mismatch",
        ),
        (
            "first_nonempty_issue_hash",
            packet_stats.get("first_nonempty_issue_hash"),
            "packet_export_first_nonempty_issue_hash_mismatch",
        ),
    )
    for suffix, expected, failure in checks:
        raw = summary.get(f"{prefix}{suffix}")
        if raw != expected:
            failures.append(failure)
    raw_path = summary.get(f"{prefix}first_nonempty_issue_path")
    normalized = _normalize_optional_path(raw_path, summary_path=summary_path)
    if normalized != packet_stats.get("first_nonempty_issue_path"):
        failures.append("packet_export_first_nonempty_issue_path_mismatch")


def _check_shifted_issue_summary(
    summary: dict[str, Any],
    failures: list[str],
    *,
    expected_packet_count: int,
) -> dict[str, Any]:
    prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    enabled = summary.get(f"{prefix}runtime_shadow_enabled")
    if enabled is None:
        enabled = summary.get(f"{prefix}enabled")
    if enabled is not True:
        failures.append("shifted_issue_runtime_shadow_not_enabled")

    packet_count = _required_int(summary, f"{prefix}packet_count", failures)
    if packet_count != int(expected_packet_count):
        failures.append("shifted_issue_packet_count_mismatch")
    schedulable_packet_count = _required_int(
        summary, f"{prefix}schedulable_packet_count", failures
    )
    empty_issue_exempt_count = _required_int(
        summary, f"{prefix}empty_issue_exempt_count", failures
    )
    safe_packet_count = _required_int(summary, f"{prefix}safe_packet_count", failures)
    unsafe_packet_count = _required_int(
        summary, f"{prefix}unsafe_packet_count", failures
    )
    invalid_packet_count = _required_int(
        summary, f"{prefix}invalid_packet_count", failures
    )
    scan_error_count = _required_int(summary, f"{prefix}scan_error_count", failures)
    clamped_issue_count = _required_int(
        summary, f"{prefix}clamped_issue_count", failures
    )
    duplicate_demand_key_count = _required_int(
        summary, f"{prefix}duplicate_demand_key_count", failures
    )
    duplicate_issue_key_count = _required_int(
        summary, f"{prefix}duplicate_issue_key_count", failures
    )
    unique_demand_key_count = _required_int(
        summary, f"{prefix}unique_demand_key_count", failures
    )
    unique_issue_key_count = _required_int(
        summary, f"{prefix}unique_issue_key_count", failures
    )
    total_issue_candidates = _required_int(
        summary, f"{prefix}total_issue_candidates", failures
    )
    issue_hash_count = _required_int(summary, f"{prefix}issue_hash_count", failures)
    issue_hash_unique_count = _required_int(
        summary, f"{prefix}issue_hash_unique_count", failures
    )
    canonical_issue_lead_tokens = summary.get(f"{prefix}issue_lead_tokens")
    if f"{prefix}issue_lead_tokens" in summary and not _is_int(
        canonical_issue_lead_tokens
    ):
        failures.append("shifted_issue_lead_tokens_invalid")
        issue_lead_tokens = None
    elif _is_int(canonical_issue_lead_tokens):
        issue_lead_tokens = canonical_issue_lead_tokens
    else:
        issue_lead_tokens = summary.get(f"{prefix}lead_tokens")
    if not _is_int(issue_lead_tokens) or int(issue_lead_tokens) < 0:
        if "shifted_issue_lead_tokens_invalid" not in failures:
            failures.append("shifted_issue_lead_tokens_invalid")
        issue_lead_tokens = None

    if safe_packet_count != packet_count:
        failures.append("shifted_issue_safe_packet_count_mismatch")
    if unsafe_packet_count != 0:
        failures.append("shifted_issue_unsafe_packet_count_nonzero")
    if invalid_packet_count != 0:
        failures.append("shifted_issue_invalid_packet_count_nonzero")
    if scan_error_count != 0:
        failures.append("shifted_issue_scan_error_count_nonzero")
    if clamped_issue_count != 0:
        failures.append("shifted_issue_clamped_issue_count_nonzero")
    if duplicate_demand_key_count != 0:
        failures.append("shifted_issue_duplicate_demand_key_count_nonzero")
    if duplicate_issue_key_count != 0:
        failures.append("shifted_issue_duplicate_issue_key_count_nonzero")
    if unique_demand_key_count != schedulable_packet_count:
        failures.append("shifted_issue_unique_demand_key_count_mismatch")
    if unique_issue_key_count != schedulable_packet_count:
        failures.append("shifted_issue_unique_issue_key_count_mismatch")
    if issue_hash_count != schedulable_packet_count:
        failures.append("shifted_issue_issue_hash_count_mismatch")
    if schedulable_packet_count + empty_issue_exempt_count != packet_count:
        failures.append("shifted_issue_packet_count_accounting_mismatch")
    if total_issue_candidates <= 0 and schedulable_packet_count > 0:
        failures.append("shifted_issue_total_issue_candidates_nonpositive")

    payload_bytes = summary.get(f"{prefix}payload_bytes")
    if not _strict_zero(payload_bytes):
        failures.append("shifted_issue_payload_bytes_not_zero")
    for field in SHIFTED_SAFE_FALSE_FIELDS:
        if summary.get(f"{prefix}{field}") is not False:
            failures.append(f"shifted_issue_{field}_not_false")

    return {
        "enabled": enabled,
        "packet_count": packet_count,
        "schedulable_packet_count": schedulable_packet_count,
        "empty_issue_exempt_count": empty_issue_exempt_count,
        "safe_packet_count": safe_packet_count,
        "unsafe_packet_count": unsafe_packet_count,
        "invalid_packet_count": invalid_packet_count,
        "scan_error_count": scan_error_count,
        "clamped_issue_count": clamped_issue_count,
        "duplicate_demand_key_count": duplicate_demand_key_count,
        "duplicate_issue_key_count": duplicate_issue_key_count,
        "unique_demand_key_count": unique_demand_key_count,
        "unique_issue_key_count": unique_issue_key_count,
        "total_issue_candidates": total_issue_candidates,
        "issue_hash_count": issue_hash_count,
        "issue_hash_unique_count": issue_hash_unique_count,
        "issue_lead_tokens": issue_lead_tokens,
    }


def _packet_export_manifest(args: argparse.Namespace) -> dict[str, Any]:
    summary_path = _resolve(args.performance_summary)
    output_path = _resolve(args.output_json)
    summary = _load_json(summary_path)
    prefix = "runtime_shadow_premap_payload_cache_producer_state_packet_export_"
    shifted_prefix = "runtime_shadow_premap_payload_cache_shifted_issue_"
    failures: list[str] = []
    if int(args.min_nonempty_issue_count) < 0:
        failures.append("min_nonempty_issue_count_negative")

    paths = summary.get(f"{prefix}paths")
    if not isinstance(paths, list) or not paths:
        failures.append("packet_export_paths_missing")
        paths = []
    elif any(not isinstance(path, str) or not path for path in paths):
        failures.append("packet_export_path_invalid")

    count = summary.get(f"{prefix}count")
    configured_count = summary.get(f"{prefix}count")
    if not _is_int(count):
        failures.append("packet_export_count_invalid")
        count = 0
    if not _is_int(configured_count):
        failures.append("packet_export_configured_count_invalid")
        configured_count = 0
    if int(count) != len(paths):
        failures.append("packet_export_count_mismatch")

    enabled = summary.get(f"{prefix}enabled")
    if enabled is not True:
        failures.append("packet_export_not_enabled")
    scan_error_count = summary.get(f"{prefix}scan_error_count", 0)
    if not _is_int(scan_error_count):
        failures.append("packet_export_scan_error_count_invalid")
    elif int(scan_error_count) != 0:
        failures.append("packet_export_scan_error_count_nonzero")

    nonempty_issue_count = summary.get(f"{prefix}nonempty_issue_count")
    if not _is_int(nonempty_issue_count):
        failures.append("packet_export_nonempty_issue_count_invalid")
        nonempty_issue_count = 0
    elif int(nonempty_issue_count) < 0:
        failures.append("packet_export_nonempty_issue_count_negative")
        nonempty_issue_count = 0
    elif int(nonempty_issue_count) < int(args.min_nonempty_issue_count):
        failures.append("packet_export_nonempty_issue_count_below_min")

    normalized_paths = _normalize_packet_paths(
        paths,
        summary_path=summary_path,
        failures=failures,
    )
    if len(normalized_paths) != len(paths):
        failures.append("packet_export_normalized_paths_count_mismatch")
    shifted_enabled = summary.get(f"{shifted_prefix}runtime_shadow_enabled")
    if shifted_enabled is None:
        shifted_enabled = summary.get(f"{shifted_prefix}enabled")
    if args.require_shifted_issue:
        shifted = _check_shifted_issue_summary(
            summary,
            failures,
            expected_packet_count=int(count),
        )
    else:
        shifted_packet_count = summary.get(f"{shifted_prefix}packet_count")
        shifted = {
            "enabled": shifted_enabled,
            "packet_count": (
                int(shifted_packet_count) if _is_int(shifted_packet_count) else None
            ),
            "schedulable_packet_count": summary.get(
                f"{shifted_prefix}schedulable_packet_count"
            ),
            "issue_lead_tokens": summary.get(f"{shifted_prefix}issue_lead_tokens")
            if _is_int(summary.get(f"{shifted_prefix}issue_lead_tokens"))
            else summary.get(f"{shifted_prefix}lead_tokens"),
        }

    packet_results: list[dict[str, Any]] = []
    checked_nonempty_packet_count = 0
    for packet_index, packet_path_str in enumerate(normalized_paths):
        packet = _load_packet(
            Path(packet_path_str),
            failures,
            prefix=f"packet_{packet_index}",
        )
        if packet is None:
            continue
        packet_result = _check_packet_contract(
            packet,
            failures,
            packet_index=packet_index,
            packet_path=packet_path_str,
            issue_lead_tokens=shifted.get("issue_lead_tokens")
            if _is_int(shifted.get("issue_lead_tokens"))
            else None,
            allow_empty_config_packets=bool(args.allow_empty_config_packets),
            allow_config_token_source=bool(args.allow_config_token_source),
        )
        packet_results.append(packet_result)
        if packet_result.get("nonempty_issue"):
            checked_nonempty_packet_count += 1
    packet_stats = _accumulate_packet_stats(packet_results)
    if _is_int(nonempty_issue_count) and checked_nonempty_packet_count != int(
        nonempty_issue_count
    ):
        failures.append("packet_export_nonempty_issue_count_mismatch")
    if args.require_shifted_issue:
        _compare_shifted_packet_stats(packet_stats, shifted, failures)
    _compare_first_nonempty_summary(
        summary,
        packet_stats,
        failures,
        prefix=prefix,
        summary_path=summary_path,
    )

    output = {
        "artifact_kind": "premap_payload_cache_packet_export_manifest",
        "manifest_name": "premap_payload_cache_packet_export_manifest_v1",
        "manifest_source": "runtime_shadow_performance_summary",
        "ok": not failures,
        "ready": not failures,
        "passed": not failures,
        "failures": failures,
        "online_export_source": (
            "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ),
        "online_performance_summary": str(summary_path),
        "online_packet_export_count": int(count),
        "online_configured_export_count": int(configured_count),
        "online_packet_export_paths": normalized_paths,
        "online_packet_export_scan_error_count": (
            int(scan_error_count) if _is_int(scan_error_count) else None
        ),
        "online_packet_export_nonempty_issue_count": (
            int(nonempty_issue_count) if _is_int(nonempty_issue_count) else None
        ),
        "online_nonempty_issue_count": (
            int(nonempty_issue_count) if _is_int(nonempty_issue_count) else None
        ),
        "checked_nonempty_packet_count": checked_nonempty_packet_count,
        "summary_packet_export_first_nonempty_issue_index": summary.get(
            f"{prefix}first_nonempty_issue_index"
        ),
        "summary_packet_export_first_nonempty_issue_path": _normalize_optional_path(
            summary.get(f"{prefix}first_nonempty_issue_path"),
            summary_path=summary_path,
        ),
        "summary_packet_export_first_nonempty_issue_count": summary.get(
            f"{prefix}first_nonempty_issue_count"
        ),
        "summary_packet_export_first_nonempty_issue_hash": summary.get(
            f"{prefix}first_nonempty_issue_hash"
        ),
        "checked_packet_export_first_nonempty_issue_index": packet_stats.get(
            "first_nonempty_issue_index"
        ),
        "checked_packet_export_first_nonempty_issue_path": packet_stats.get(
            "first_nonempty_issue_path"
        ),
        "checked_packet_export_first_nonempty_issue_count": packet_stats.get(
            "first_nonempty_issue_count"
        ),
        "checked_packet_export_first_nonempty_issue_hash": packet_stats.get(
            "first_nonempty_issue_hash"
        ),
        "online_packet_export_first_nonempty_issue_index": packet_stats.get(
            "first_nonempty_issue_index"
        ),
        "online_packet_export_first_nonempty_issue_path": packet_stats.get(
            "first_nonempty_issue_path"
        ),
        "online_packet_export_first_nonempty_issue_count": packet_stats.get(
            "first_nonempty_issue_count"
        ),
        "online_packet_export_first_nonempty_issue_hash": packet_stats.get(
            "first_nonempty_issue_hash"
        ),
        "checked_packet_count": packet_stats.get("loaded_packet_count"),
        "shifted_issue_runtime_shadow_required": bool(args.require_shifted_issue),
        "allow_config_token_source": bool(args.allow_config_token_source),
        "allow_empty_config_packets": bool(args.allow_empty_config_packets),
        "shifted_issue_runtime_shadow_enabled": _strict_bool(shifted.get("enabled")),
        "shifted_issue_enabled": _strict_bool(shifted.get("enabled")),
        "shifted_issue_packet_count": shifted.get("packet_count"),
        "shifted_issue_schedulable_packet_count": shifted.get(
            "schedulable_packet_count"
        ),
        "shifted_issue_empty_issue_exempt_count": shifted.get(
            "empty_issue_exempt_count"
        ),
        "shifted_issue_safe_packet_count": shifted.get("safe_packet_count"),
        "shifted_issue_unsafe_packet_count": shifted.get("unsafe_packet_count"),
        "shifted_issue_invalid_packet_count": shifted.get("invalid_packet_count"),
        "shifted_issue_scan_error_count": shifted.get("scan_error_count"),
        "shifted_issue_clamped_issue_count": shifted.get("clamped_issue_count"),
        "shifted_issue_duplicate_demand_key_count": shifted.get(
            "duplicate_demand_key_count"
        ),
        "shifted_issue_duplicate_issue_key_count": shifted.get(
            "duplicate_issue_key_count"
        ),
        "shifted_issue_unique_demand_key_count": shifted.get(
            "unique_demand_key_count"
        ),
        "shifted_issue_unique_issue_key_count": shifted.get("unique_issue_key_count"),
        "shifted_issue_total_issue_candidates": shifted.get("total_issue_candidates"),
        "shifted_issue_issue_hash_count": shifted.get("issue_hash_count"),
        "shifted_issue_issue_hash_unique_count": shifted.get(
            "issue_hash_unique_count"
        ),
        "shifted_issue_lead_tokens": shifted.get("issue_lead_tokens"),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "next_runtime_stage": (
            "payload_cache_issue_stream_executor"
            if not failures
            else "blocked_by_packet_export_manifest_gate"
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--performance-summary",
        type=Path,
        default=DEFAULT_PERFORMANCE_SUMMARY,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--min-nonempty-issue-count", type=int, default=1)
    parser.add_argument(
        "--require-shifted-issue",
        dest="require_shifted_issue",
        action="store_true",
        help="Require strict shifted-issue runtime-shadow safety counters.",
    )
    parser.add_argument(
        "--no-require-shifted-issue",
        dest="require_shifted_issue",
        action="store_false",
        help="Only materialize packet-export paths without shifted-issue gate.",
    )
    parser.set_defaults(require_shifted_issue=True)
    parser.add_argument(
        "--allow-config-token-source",
        action="store_true",
        help="Allow nonempty shifted issue packets with config token provenance.",
    )
    parser.add_argument(
        "--allow-empty-config-packets",
        dest="allow_empty_config_packets",
        action="store_true",
        help="Exempt empty issue packets with config token provenance.",
    )
    parser.add_argument(
        "--no-allow-empty-config-packets",
        dest="allow_empty_config_packets",
        action="store_false",
        help="Require token provenance even for empty issue packets.",
    )
    parser.set_defaults(allow_empty_config_packets=True)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _packet_export_manifest(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
