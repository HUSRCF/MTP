#!/usr/bin/env python3
"""Execute all exported payload-cache issue packets through one ready-time manager.

This stream executor is the next step after the single issue-plan canary.  It
consumes the online producer-state summary, loads every exported packet, and
feeds the issue experts into one ReadyTimeExpertCacheManager instance.  It still
does not move payload bytes, does not grant real ready credit, and does not pass
anything to a kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for _path in (REPO_ROOT, SRC_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mtp_expert_prefetch.runtime import ReadyTimeExpertCacheManager  # noqa: E402


DEFAULT_ONLINE_CANARY_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "payload_cache_producer_state_online_canary_dolly128_gen64_nonempty_issue_minimal_summary_v2_20260620.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "outputs"
    / "reports"
    / "premap_kernel_consumer"
    / "premap_payload_cache_issue_stream_executor_dolly128_gen64_ready_time_v1.json"
)

ARTIFACT_KIND = "premap_payload_cache_issue_stream_executor"
EXECUTOR_NAME = "premap_payload_cache_ready_time_issue_stream_executor_v1"
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF
SAFE_FALSE_FLAGS = (
    "ready_credit",
    "ready_before_demand_credit",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "kernel_arg_pass_allowed",
    "real_ready_credit_granted",
    "passed_to_kernel",
    "changes_kernel_launch_args",
    "uses_current_wna16_args",
    "passes_current_wna16_args",
    "measures_tpot",
    "measures_vllm_latency",
)
SAFE_ZERO_FLAGS = ("payload_bytes",)


def _resolve(path: str | Path, *, base_dir: Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if base_dir is not None:
        based = base_dir / candidate
        if based.exists():
            return based
    return REPO_ROOT / candidate


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _float_rate(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator > 0 else 0.0


def _issue_hash(experts: list[int] | tuple[int, ...]) -> str:
    value = FNV_OFFSET
    count = 0
    for expert_id in experts:
        value ^= int(expert_id) & 0xFFFFFFFF
        value = (value * FNV_PRIME) & U64_MASK
        count += 1
    value ^= count & 0xFFFFFFFF
    value = (value * FNV_PRIME) & U64_MASK
    return f"{value:016x}"


def _canonical_experts(values: Any) -> tuple[int, ...]:
    if not isinstance(values, list):
        raise ValueError("expert list must be a list")
    if any(type(value) is not int for value in values):
        raise ValueError("expert list must contain only ints")
    if any(int(value) < 0 for value in values):
        raise ValueError("expert list must be non-negative")
    seen: set[int] = set()
    experts: list[int] = []
    for value in values:
        expert_id = int(value)
        if expert_id in seen:
            continue
        seen.add(expert_id)
        experts.append(expert_id)
    return tuple(experts)


def _issue_experts_from_packet(packet: dict[str, Any]) -> tuple[int, ...]:
    exported_issue = packet.get("issue_candidate_experts")
    if exported_issue is not None:
        return _canonical_experts(exported_issue)
    previous = _canonical_experts(packet.get("previous_experts", []))
    topk = int(packet.get("transition_topk_count", 0) or 0)
    if topk < 0:
        raise ValueError("transition_topk_count must be non-negative")
    limit = len(previous) if topk == 0 else min(len(previous), topk)
    return previous[:limit]


def _check_issue_provenance(
    payload: dict[str, Any],
    experts: tuple[int, ...],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    expected_count = len(experts)
    expected_first = int(experts[0]) if experts else -1
    expected_last = int(experts[-1]) if experts else -1
    expected_hash = _issue_hash(list(experts))
    checks = (
        ("issue_candidate_count", expected_count),
        ("issue_candidate_first_expert", expected_first),
        ("issue_candidate_last_expert", expected_last),
        ("issue_candidate_hash", expected_hash),
    )
    for key, expected in checks:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) != expected:
            failures.append(f"{prefix}_{key}_mismatch")


def _check_safe_flags(
    payload: dict[str, Any],
    failures: list[str],
    *,
    prefix: str,
) -> None:
    for key in SAFE_FALSE_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif not _valid_number(payload.get(key)) or float(payload.get(key)) != 0.0:
            failures.append(f"{prefix}_{key}_not_zero")


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_positive_finite(value: float, *, label: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{label} must be a positive finite number")
    return numeric


def _validate_nonnegative_finite(value: float, *, label: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(f"{label} must be a non-negative finite number")
    return numeric


def _select_measured_copy_row(
    path: Path,
    *,
    stat: str,
    experts: int,
    pinned: str,
) -> dict[str, Any]:
    payload = _load_json(path, label="measured-copy envelope")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("measured-copy envelope rows must be a list")
    pinned_filter = str(pinned).lower()
    candidates = []
    for row in rows:
        if not isinstance(row, dict) or row.get("direction") != "h2d":
            continue
        if int(row.get("experts", -1) or -1) != int(experts):
            continue
        row_pinned = bool(row.get("pinned", False))
        if pinned_filter in {"true", "1", "yes"} and not row_pinned:
            continue
        if pinned_filter in {"false", "0", "no"} and row_pinned:
            continue
        if pinned_filter not in {"true", "1", "yes", "false", "0", "no", "any"}:
            raise ValueError("measured-copy pinned filter must be true, false, or any")
        candidates.append(row)
    if not candidates:
        raise ValueError("No matching H2D measured-copy row")
    row = candidates[0]
    stat_key = f"{stat}_ms"
    if stat_key not in row:
        raise ValueError(f"measured-copy row is missing {stat_key}")
    total_us = float(row[stat_key]) * 1000.0
    if not math.isfinite(total_us) or total_us <= 0.0:
        raise ValueError("measured-copy time must be finite and positive")
    return {
        "source": str(path),
        "stat": str(stat),
        "selected_experts": int(row["experts"]),
        "pinned": bool(row.get("pinned", False)),
        "copy_us_per_batch": total_us,
        "copy_us_per_issue": total_us / max(1, int(row["experts"])),
        "effective_gbps": (
            None if f"{stat}_gbps" not in row else float(row.get(f"{stat}_gbps") or 0.0)
        ),
    }


def run_issue_stream_executor(args: argparse.Namespace) -> dict[str, Any]:
    online_path = _resolve(args.online_canary_json)
    output_path = _resolve(args.output_json)
    failures: list[str] = []
    online: dict[str, Any] = {}
    try:
        online = _load_json(online_path, label="online canary")
    except Exception as exc:
        failures.append(f"online_canary_load_failed:{exc.__class__.__name__}:{exc}")

    if online:
        for key in ("ok", "passed", "ready"):
            if online.get(key) is not True:
                failures.append(f"online_{key}_not_true")
        if online.get("failures") not in ([], None):
            failures.append("online_failures_not_empty")
        if (
            online.get("online_export_source")
            != "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ):
            failures.append("online_export_source_mismatch")
        _check_safe_flags(online, failures, prefix="online")

    raw_paths = online.get("online_packet_export_paths") if online else None
    if not isinstance(raw_paths, list) or not raw_paths:
        failures.append("online_packet_export_paths_missing")
        raw_paths = []
    online_packet_export_count = online.get("online_packet_export_count")
    online_configured_export_count = online.get("online_configured_export_count")
    if isinstance(online_packet_export_count, int) and not isinstance(
        online_packet_export_count,
        bool,
    ):
        if len(raw_paths) != online_packet_export_count:
            failures.append("online_packet_export_paths_count_mismatch")
    else:
        failures.append("online_packet_export_count_invalid")
    if isinstance(online_configured_export_count, int) and not isinstance(
        online_configured_export_count,
        bool,
    ):
        if online_packet_export_count != online_configured_export_count:
            failures.append("online_configured_export_count_mismatch")
    else:
        failures.append("online_configured_export_count_invalid")

    service_us_per_issue = float(args.service_us_per_issue)
    service_us_per_batch = float(args.service_us_per_batch)
    queue_batch_size = int(args.queue_batch_size)
    event_timing_mode = str(args.event_timing_mode).strip().lower()
    if event_timing_mode not in {"packet_index", "token_index"}:
        raise ValueError("event-timing-mode must be packet_index or token_index")
    token_timing_enabled = event_timing_mode == "token_index"
    decode_token_us = _validate_positive_finite(
        float(args.decode_token_us),
        label="decode-token-us",
    )
    issue_lead_tokens = int(args.issue_lead_tokens)
    if issue_lead_tokens < 0:
        raise ValueError("issue-lead-tokens must be non-negative")
    layer_event_interval_us = _validate_nonnegative_finite(
        float(args.layer_event_interval_us),
        label="layer-event-interval-us",
    )
    measured_copy: dict[str, Any] | None = None
    if args.measured_copy_json is not None:
        try:
            measured_copy = _select_measured_copy_row(
                _resolve(args.measured_copy_json),
                stat=str(args.measured_copy_stat),
                experts=int(args.measured_copy_experts),
                pinned=str(args.measured_copy_pinned),
            )
            service_us_per_issue = float(measured_copy["copy_us_per_issue"])
            service_us_per_batch = 0.0
            queue_batch_size = int(measured_copy["selected_experts"])
        except Exception as exc:
            failures.append(
                f"measured_copy_select_failed:{exc.__class__.__name__}:{exc}"
            )

    manager = ReadyTimeExpertCacheManager(
        capacity=int(args.capacity),
        service_us_per_issue=service_us_per_issue,
        service_us_per_batch=service_us_per_batch,
        queue_batch_size=queue_batch_size,
        queue_deadline_us=float(args.queue_deadline_us),
    )

    packet_count = 0
    nonempty_packet_count = 0
    issue_candidate_total = 0
    requested_issue_total = 0
    empty_packet_count = 0
    packet_errors = 0
    max_packet_issue_width = 0
    layer_ids: set[int] = set()
    issue_hashes: list[str] = []
    token_indices: list[int] = []
    token_source_decode_count = 0
    token_source_config_count = 0
    token_source_missing_count = 0
    empty_issue_provenance_exempt_count = 0
    required_token_provenance_packet_count = 0
    required_token_index_count = 0
    required_token_source_decode_count = 0
    required_token_source_config_count = 0
    required_token_source_missing_count = 0
    min_issue_arrival_us: float | None = None
    max_issue_arrival_us: float | None = None
    min_demand_arrival_us: float | None = None
    max_demand_arrival_us: float | None = None
    first_packet_path: str | None = None
    last_packet_path: str | None = None

    for idx, raw_path in enumerate(raw_paths):
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(f"packet_{idx}_path_invalid")
            packet_errors += 1
            continue
        packet_path = _resolve(raw_path, base_dir=online_path.parent)
        if first_packet_path is None:
            first_packet_path = str(packet_path)
        last_packet_path = str(packet_path)
        try:
            packet = _load_json(packet_path, label=f"packet {idx}")
            _check_safe_flags(packet, failures, prefix=f"packet_{idx}")
            if packet.get("ready") is not True:
                failures.append(f"packet_{idx}_ready_not_true")
            raw_layer_id = packet.get("layer_id")
            if token_timing_enabled:
                if _is_int(raw_layer_id) and int(raw_layer_id) >= 0:
                    layer_id = int(raw_layer_id)
                else:
                    layer_id = 0
                    failures.append(f"packet_{idx}_layer_id_invalid")
            else:
                layer_id = int(raw_layer_id or 0)
            experts = _issue_experts_from_packet(packet)
            requires_token_provenance = not (
                bool(args.allow_empty_config_packets) and not experts
            )
            if token_timing_enabled:
                if requires_token_provenance:
                    required_token_provenance_packet_count += 1
                else:
                    empty_issue_provenance_exempt_count += 1
            _check_issue_provenance(
                packet,
                experts,
                failures,
                prefix=f"packet_{idx}",
            )
            export_context = packet.get("_export_context")
            if isinstance(export_context, dict):
                _check_safe_flags(
                    export_context,
                    failures,
                    prefix=f"packet_{idx}_export_context",
                )
                _check_issue_provenance(
                    export_context,
                    experts,
                    failures,
                    prefix=f"packet_{idx}_export_context",
                )
                if token_timing_enabled:
                    token_index = export_context.get("token_index")
                    if _is_int(token_index) and int(token_index) >= 0:
                        token_indices.append(int(token_index))
                        if requires_token_provenance:
                            required_token_index_count += 1
                    elif requires_token_provenance:
                        failures.append(f"packet_{idx}_token_index_invalid")
                    token_source = export_context.get("token_index_source")
                    if token_source == "decode_workload_collector":
                        token_source_decode_count += 1
                        if requires_token_provenance:
                            required_token_source_decode_count += 1
                    elif token_source == "config":
                        token_source_config_count += 1
                        if requires_token_provenance:
                            required_token_source_config_count += 1
                        if requires_token_provenance and not bool(
                            args.allow_config_token_source
                        ):
                            failures.append(f"packet_{idx}_config_token_source_disallowed")
                    elif token_source is None:
                        token_source_missing_count += 1
                        if requires_token_provenance:
                            required_token_source_missing_count += 1
                            failures.append(f"packet_{idx}_token_index_source_missing")
                    elif requires_token_provenance:
                        failures.append(f"packet_{idx}_token_index_source_unexpected")
            elif token_timing_enabled:
                failures.append(f"packet_{idx}_export_context_missing")
        except Exception as exc:
            failures.append(
                f"packet_{idx}_load_or_parse_failed:{exc.__class__.__name__}:{exc}"
            )
            packet_errors += 1
            continue
        packet_count += 1
        layer_ids.add(layer_id)
        requested_issue_total += len(experts)
        max_packet_issue_width = max(max_packet_issue_width, len(experts))
        issue_hashes.append(_issue_hash(list(experts)))
        if not experts:
            empty_packet_count += 1
            continue
        nonempty_packet_count += 1
        if token_timing_enabled:
            export_context = packet.get("_export_context")
            token_index = (
                int(export_context["token_index"])
                if isinstance(export_context, dict)
                and _is_int(export_context.get("token_index"))
                and int(export_context.get("token_index")) >= 0
                else 0
            )
            demand_arrival = (
                float(args.issue_arrival_us)
                + (float(token_index) * decode_token_us)
                + (float(layer_id) * layer_event_interval_us)
            )
            arrival_us = max(
                0.0,
                demand_arrival - (float(issue_lead_tokens) * decode_token_us),
            )
        else:
            arrival_us = float(args.issue_arrival_us) + (
                float(idx) * float(args.event_interval_us)
            )
            demand_arrival = arrival_us + float(args.demand_gap_us)
        min_issue_arrival_us = (
            arrival_us
            if min_issue_arrival_us is None
            else min(min_issue_arrival_us, arrival_us)
        )
        max_issue_arrival_us = (
            arrival_us
            if max_issue_arrival_us is None
            else max(max_issue_arrival_us, arrival_us)
        )
        min_demand_arrival_us = (
            demand_arrival
            if min_demand_arrival_us is None
            else min(min_demand_arrival_us, demand_arrival)
        )
        max_demand_arrival_us = (
            demand_arrival
            if max_demand_arrival_us is None
            else max(max_demand_arrival_us, demand_arrival)
        )
        issued_now = manager.issue_prefetches(
            layer_id,
            tuple(experts),
            arrival_us=arrival_us,
        )
        issue_candidate_total += issued_now
        for expert_id in experts:
            manager.demand(layer_id, expert_id, arrival_us=demand_arrival)
    manager.finish()

    snapshot = manager.snapshot()
    demand_count = int(snapshot.demand_count)
    issued_count = int(snapshot.issued_fetch_count)
    used_fetch_count = int(snapshot.used_fetch_count)
    demand_hit_count = int(snapshot.demand_hit_count)
    ready_late_miss_count = int(snapshot.ready_late_miss_count)
    demand_hit_rate = _float_rate(demand_hit_count, demand_count)
    ready_late_miss_rate = _float_rate(ready_late_miss_count, demand_count)
    used_per_issued_fetch = _float_rate(used_fetch_count, issued_count)
    dedup_issue_drop_count = max(0, requested_issue_total - issued_count)

    if packet_count < int(args.min_packet_count):
        failures.append("packet_count_below_min")
    if isinstance(online_packet_export_count, int) and not isinstance(
        online_packet_export_count,
        bool,
    ):
        if packet_count != online_packet_export_count:
            failures.append("packet_count_online_export_count_mismatch")
    if nonempty_packet_count < int(args.min_nonempty_packet_count):
        failures.append("nonempty_packet_count_below_min")
    if packet_errors:
        failures.append("packet_errors_nonzero")
    if token_timing_enabled:
        if required_token_index_count != required_token_provenance_packet_count:
            failures.append("token_index_count_packet_count_mismatch")
        if (
            not bool(args.allow_config_token_source)
            and required_token_source_config_count
        ):
            failures.append("config_token_source_present")
        if required_token_source_missing_count:
            failures.append("missing_token_source_present")
    if demand_hit_rate < float(args.min_demand_hit_rate):
        failures.append("demand_hit_rate_below_threshold")
    if ready_late_miss_rate > float(args.max_ready_late_miss_rate):
        failures.append("ready_late_miss_rate_above_threshold")
    if used_per_issued_fetch < float(args.min_used_per_issued_fetch):
        failures.append("used_per_issued_fetch_below_threshold")

    threshold_failure_set = {
        "demand_hit_rate_below_threshold",
        "ready_late_miss_rate_above_threshold",
        "used_per_issued_fetch_below_threshold",
    }
    full_fetch_block_reason = "real_payload_runtime_not_enabled"
    if measured_copy is not None and threshold_failure_set.intersection(failures):
        full_fetch_block_reason = "measured_copy_stream_deadline_miss"
    if (
        measured_copy is not None
        and int(measured_copy["selected_experts"]) < max_packet_issue_width
    ):
        failures.append("measured_copy_experts_below_max_packet_issue_width")
        full_fetch_block_reason = "measured_copy_issue_width_mismatch"
    elif any(str(failure).startswith("measured_copy_select_failed") for failure in failures):
        full_fetch_block_reason = "measured_copy_invalid"

    payload = {
        "artifact_kind": ARTIFACT_KIND,
        "executor_name": EXECUTOR_NAME,
        "passed": not failures,
        "failures": failures,
        "stream_executor_ready": not failures,
        "online_canary_json": str(online_path),
        "online_canary_sha256": _sha256(online_path),
        "packet_count": packet_count,
        "configured_packet_count": int(online.get("online_configured_export_count", 0) or 0)
        if online
        else 0,
        "online_packet_export_count": int(online.get("online_packet_export_count", 0) or 0)
        if online
        else 0,
        "nonempty_packet_count": nonempty_packet_count,
        "empty_packet_count": empty_packet_count,
        "packet_error_count": packet_errors,
        "max_packet_issue_width": max_packet_issue_width,
        "first_packet_path": first_packet_path,
        "last_packet_path": last_packet_path,
        "layer_ids": sorted(layer_ids),
        "event_timing_mode": event_timing_mode,
        "token_timing_enabled": bool(token_timing_enabled),
        "decode_token_us": decode_token_us,
        "issue_lead_tokens": issue_lead_tokens,
        "layer_event_interval_us": layer_event_interval_us,
        "token_index_count": len(token_indices),
        "required_token_index_count": required_token_index_count,
        "token_index_min": min(token_indices) if token_indices else None,
        "token_index_max": max(token_indices) if token_indices else None,
        "token_source_decode_workload_count": token_source_decode_count,
        "token_source_config_count": token_source_config_count,
        "token_source_missing_count": token_source_missing_count,
        "required_token_provenance_packet_count": required_token_provenance_packet_count,
        "empty_issue_provenance_exempt_count": empty_issue_provenance_exempt_count,
        "required_token_source_decode_workload_count": required_token_source_decode_count,
        "required_token_source_config_count": required_token_source_config_count,
        "required_token_source_missing_count": required_token_source_missing_count,
        "allow_config_token_source": bool(args.allow_config_token_source),
        "allow_empty_config_packets": bool(args.allow_empty_config_packets),
        "issue_arrival_min_us": min_issue_arrival_us,
        "issue_arrival_max_us": max_issue_arrival_us,
        "demand_arrival_min_us": min_demand_arrival_us,
        "demand_arrival_max_us": max_demand_arrival_us,
        "issue_hash_chain": _issue_hash([int(h[:8], 16) for h in issue_hashes]),
        "requested_issue_count": requested_issue_total,
        "dedup_issue_drop_count": dedup_issue_drop_count,
        "issued_prefetch_count": issued_count,
        "used_fetch_count": used_fetch_count,
        "demand_count": demand_count,
        "demand_hit_count": demand_hit_count,
        "demand_miss_count": int(snapshot.demand_miss_count),
        "demand_hit_rate": demand_hit_rate,
        "ready_late_miss_count": ready_late_miss_count,
        "ready_late_miss_rate": ready_late_miss_rate,
        "ready_time_model_hit_count": demand_hit_count,
        "real_payload_ready_hit_count": 0,
        "used_per_issued_fetch": used_per_issued_fetch,
        "evicted_before_use_count": int(snapshot.evicted_before_use_count),
        "unused_fetch_count": int(snapshot.unused_fetch_count),
        "queue_batch_count": int(snapshot.queue_batch_count),
        "queue_service_us": float(snapshot.queue_service_us),
        "queue_wait_us": float(snapshot.queue_wait_us),
        "queue_max_delay_us": float(snapshot.queue_max_delay_us),
        "queue_total_span_us": float(snapshot.queue_total_span_us),
        "capacity": int(args.capacity),
        "service_us_per_issue": service_us_per_issue,
        "service_us_per_batch": service_us_per_batch,
        "queue_batch_size": queue_batch_size,
        "queue_deadline_us": float(args.queue_deadline_us),
        "event_interval_us": float(args.event_interval_us),
        "issue_arrival_us": float(args.issue_arrival_us),
        "demand_gap_us": float(args.demand_gap_us),
        "manager_mode": "ready_time_stream",
        "deadline_window_model_only": True,
        "measured_copy_model_enabled": measured_copy is not None,
        "measured_copy_source": None if measured_copy is None else measured_copy["source"],
        "measured_copy_stat": None if measured_copy is None else measured_copy["stat"],
        "measured_copy_selected_experts": (
            None if measured_copy is None else measured_copy["selected_experts"]
        ),
        "measured_copy_pinned": None if measured_copy is None else measured_copy["pinned"],
        "measured_copy_us_per_batch": (
            None if measured_copy is None else measured_copy["copy_us_per_batch"]
        ),
        "measured_copy_us_per_issue": (
            None if measured_copy is None else measured_copy["copy_us_per_issue"]
        ),
        "measured_copy_effective_gbps": (
            None if measured_copy is None else measured_copy["effective_gbps"]
        ),
        "full_fetch_allowed": False,
        "full_fetch_block_reason": full_fetch_block_reason,
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "snapshot": snapshot.as_dict(),
        "min_packet_count": int(args.min_packet_count),
        "min_nonempty_packet_count": int(args.min_nonempty_packet_count),
        "min_demand_hit_rate": float(args.min_demand_hit_rate),
        "max_ready_late_miss_rate": float(args.max_ready_late_miss_rate),
        "min_used_per_issued_fetch": float(args.min_used_per_issued_fetch),
        "next_runtime_stage": "expand_payload_cache_issue_stream_or_real_payload_runtime",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online-canary-json", type=Path, default=DEFAULT_ONLINE_CANARY_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--capacity", type=int, default=12288)
    parser.add_argument("--service-us-per-issue", type=float, default=10.0)
    parser.add_argument("--service-us-per-batch", type=float, default=0.0)
    parser.add_argument("--queue-batch-size", type=int, default=8)
    parser.add_argument("--measured-copy-json", type=Path)
    parser.add_argument("--measured-copy-stat", default="p95")
    parser.add_argument("--measured-copy-experts", type=int, default=8)
    parser.add_argument("--measured-copy-pinned", default="true")
    parser.add_argument("--queue-deadline-us", type=float, default=200.0)
    parser.add_argument(
        "--event-timing-mode",
        choices=("packet_index", "token_index"),
        default="packet_index",
    )
    parser.add_argument("--decode-token-us", type=float, default=75_000.0)
    parser.add_argument("--issue-lead-tokens", type=int, default=0)
    parser.add_argument("--layer-event-interval-us", type=float, default=1.0)
    parser.add_argument("--allow-config-token-source", action="store_true")
    parser.add_argument(
        "--allow-empty-config-packets",
        action="store_true",
        help=(
            "In token-index mode, allow empty issue packets to keep static "
            "token provenance; nonempty issue packets still require decode tokens."
        ),
    )
    parser.add_argument("--event-interval-us", type=float, default=1.0)
    parser.add_argument("--issue-arrival-us", type=float, default=0.0)
    parser.add_argument("--demand-gap-us", type=float, default=0.0)
    parser.add_argument("--min-packet-count", type=int, default=1)
    parser.add_argument("--min-nonempty-packet-count", type=int, default=1)
    parser.add_argument("--min-demand-hit-rate", type=float, default=0.5)
    parser.add_argument("--max-ready-late-miss-rate", type=float, default=0.2)
    parser.add_argument("--min-used-per-issued-fetch", type=float, default=0.5)
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_issue_stream_executor(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
