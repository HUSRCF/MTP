#!/usr/bin/env python3
"""Materialize a payload-copy descriptor plan from an online issue stream.

This is the bridge after the ready-time issue stream executor.  It replays the
same exported producer-state packets, records the prefetches accepted by the
bounded manager, and emits a descriptor-table artifact that a future payload
copy worker could consume.  The artifact is intentionally payloadless: it does
not copy bytes, publish ready credit, dereference payloads, or pass kernel args.
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
from scripts import run_premap_payload_cache_issue_stream_executor as executor  # noqa: E402


ARTIFACT_KIND = "premap_payload_cache_copy_descriptor_plan"
SCHEMA_NAME = "payload_cache_issue_copy_descriptor_plan_v1"
ROW_SCHEMA_NAME = "payload_cache_issue_copy_descriptor_row_v1"
SAFE_FALSE_FLAGS = tuple(executor.SAFE_FALSE_FLAGS)
SAFE_ZERO_FLAGS = tuple(executor.SAFE_ZERO_FLAGS)


def _resolve(path: str | Path, *, base_dir: Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if base_dir is not None:
        based = base_dir / candidate
        if based.exists():
            return based
    return REPO_ROOT / candidate


def _resolve_packet_path(path: str | Path, *, base_dir: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    based = base_dir / candidate
    if based.exists():
        return based
    raise FileNotFoundError(
        f"relative packet path must resolve under online manifest directory: {path}"
    )


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _hash_update_json(digest: "hashlib._Hash", payload: dict[str, Any]) -> None:
    digest.update(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    digest.update(b"\n")


def _valid_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_nonnegative_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= 0.0
    )


def _safe_false_zero_fields(payload: dict[str, Any], failures: list[str], *, prefix: str) -> None:
    for key in SAFE_FALSE_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif payload.get(key) is not False:
            failures.append(f"{prefix}_{key}_not_false")
    for key in SAFE_ZERO_FLAGS:
        if key not in payload:
            failures.append(f"{prefix}_{key}_missing")
        elif not _valid_nonnegative_number(payload.get(key)) or float(payload.get(key)) != 0.0:
            failures.append(f"{prefix}_{key}_not_zero")


def _context_int(context: dict[str, Any], key: str, default: int = 0) -> int:
    value = context.get(key)
    if _valid_int(value):
        return int(value)
    return int(default)


def _context_str(context: dict[str, Any], key: str, default: str = "") -> str:
    value = context.get(key)
    if isinstance(value, str) and value:
        return value
    return default


def _build_row(
    *,
    row_index: int,
    packet_index: int,
    packet_path: Path,
    packet: dict[str, Any],
    layer_id: int,
    expert_id: int,
    issue_token_index: int,
    issue_clamped_to_zero: bool,
    issue_arrival_us: float,
    demand_arrival_us: float,
    planned_payload_bytes: int,
) -> dict[str, Any]:
    context = packet.get("_export_context")
    if not isinstance(context, dict):
        context = {}
    token_index = _context_int(context, "token_index", default=0)
    return {
        "row_index": int(row_index),
        "packet_index": int(packet_index),
        "packet_path": str(packet_path),
        "sample_idx": _context_int(context, "sample_idx", default=-1),
        "record_id": _context_str(context, "record_id", default=""),
        "request_id": _context_str(context, "request_id", default=""),
        "sequence_id": _context_int(context, "sequence_id", default=0),
        "token_index": int(token_index),
        "issue_token_index": int(issue_token_index),
        "issue_clamped_to_zero": bool(issue_clamped_to_zero),
        "layer_id": int(layer_id),
        "expert_id": int(expert_id),
        "issue_source": str(packet.get("issue_source", "")),
        "issue_arrival_us": float(issue_arrival_us),
        "demand_arrival_us": float(demand_arrival_us),
        "planned_payload_bytes": int(planned_payload_bytes),
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "ready_credit": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
    }


def build_copy_descriptor_plan(
    *,
    issue_stream_executor_json: Path,
    output_json: Path,
    planned_payload_bytes_per_issue: int = 64,
    row_sample_limit: int = 16,
    require_same_source_packet_budget: bool = False,
    allow_config_token_source: bool = False,
) -> dict[str, Any]:
    executor_path = _resolve(issue_stream_executor_json)
    output_path = _resolve(output_json)
    failures: list[str] = []
    issue_stream = _load_json(executor_path, label="issue stream executor")
    if issue_stream.get("artifact_kind") != "premap_payload_cache_issue_stream_executor":
        failures.append("issue_stream_artifact_kind_mismatch")
    if issue_stream.get("passed") is not True:
        failures.append("issue_stream_not_passed")
    _safe_false_zero_fields(issue_stream, failures, prefix="issue_stream")

    planned_payload_bytes_per_issue = int(planned_payload_bytes_per_issue)
    row_sample_limit = max(0, int(row_sample_limit))
    if planned_payload_bytes_per_issue <= 0:
        failures.append("planned_payload_bytes_per_issue_not_positive")

    online_path = _resolve(str(issue_stream.get("online_canary_json", "")))
    online: dict[str, Any] = {}
    raw_paths: list[Any] = []
    try:
        online = _load_json(online_path, label="online canary")
        raw_packet_paths = online.get("online_packet_export_paths")
        if isinstance(raw_packet_paths, list):
            raw_paths = raw_packet_paths
        else:
            failures.append("online_packet_export_paths_missing")
    except Exception as exc:
        failures.append(f"online_canary_load_failed:{exc.__class__.__name__}:{exc}")

    if online:
        _safe_false_zero_fields(online, failures, prefix="online")
        if online.get("passed") is not True or online.get("ok") is not True:
            failures.append("online_canary_not_passed")
        if online.get("ready") is not True:
            failures.append("online_ready_not_true")
        if online.get("failures") not in ([], None):
            failures.append("online_failures_not_empty")
        if (
            online.get("online_export_source")
            != "runtime_shadow_premap_payload_cache_producer_state_packet_export"
        ):
            failures.append("online_export_source_mismatch")
        online_packet_export_count = online.get("online_packet_export_count")
        online_configured_export_count = online.get("online_configured_export_count")
        if _valid_int(online_packet_export_count) and int(online_packet_export_count) >= 0:
            if len(raw_paths) != int(online_packet_export_count):
                failures.append("online_packet_export_paths_count_mismatch")
        else:
            failures.append("online_packet_export_count_invalid")
        if (
            _valid_int(online_configured_export_count)
            and int(online_configured_export_count) >= 0
        ):
            if online_packet_export_count != online_configured_export_count:
                failures.append("online_configured_export_count_mismatch")
        else:
            failures.append("online_configured_export_count_invalid")

    packet_count = 0
    nonempty_packet_count = 0
    packet_error_count = 0
    requested_issue_count = 0
    accepted_rows: list[dict[str, Any]] = []
    row_sample: list[dict[str, Any]] = []
    row_digest = hashlib.sha256()
    packet_digest = hashlib.sha256()
    layer_ids: set[int] = set()
    token_indices: list[int] = []
    issue_token_indices: list[int] = []
    token_source_decode_count = 0
    token_source_config_count = 0
    token_source_missing_count = 0
    shifted_issue_invalid_export_count = 0
    shifted_issue_row_shift_mismatch_count = 0
    shifted_issue_row_clamp_mismatch_count = 0
    shifted_issue_duplicate_issue_key_count = 0
    shifted_issue_unique_issue_key_count = 0
    shifted_issue_accounted_packet_count = 0
    shifted_issue_keys_seen: set[tuple[int, str, int, int, int]] = set()

    manager = ReadyTimeExpertCacheManager(
        capacity=int(issue_stream.get("capacity", 0) or 0),
        service_us_per_issue=float(issue_stream.get("service_us_per_issue", 0.0) or 0.0),
        service_us_per_batch=float(issue_stream.get("service_us_per_batch", 0.0) or 0.0),
        queue_batch_size=int(issue_stream.get("queue_batch_size", 1) or 1),
        queue_deadline_us=float(issue_stream.get("queue_deadline_us", 0.0) or 0.0),
    )
    event_timing_mode = str(issue_stream.get("event_timing_mode", "packet_index"))
    if event_timing_mode not in {"packet_index", "token_index"}:
        failures.append("event_timing_mode_invalid")
    token_timing_enabled = event_timing_mode == "token_index"
    decode_token_us = float(issue_stream.get("decode_token_us", 75_000.0) or 75_000.0)
    issue_lead_tokens = int(issue_stream.get("issue_lead_tokens", 0) or 0)
    layer_event_interval_us = float(issue_stream.get("layer_event_interval_us", 1.0) or 1.0)

    for packet_index, raw_path in enumerate(raw_paths):
        if not isinstance(raw_path, str) or not raw_path:
            packet_error_count += 1
            failures.append(f"packet_{packet_index}_path_invalid")
            continue
        try:
            packet_path = _resolve_packet_path(raw_path, base_dir=online_path.parent)
            packet = _load_json(packet_path, label=f"packet {packet_index}")
            _safe_false_zero_fields(packet, failures, prefix=f"packet_{packet_index}")
            context = packet.get("_export_context")
            if isinstance(context, dict):
                _safe_false_zero_fields(
                    context,
                    failures,
                    prefix=f"packet_{packet_index}_export_context",
                )
            elif token_timing_enabled:
                failures.append(f"packet_{packet_index}_export_context_missing")
            experts = executor._issue_experts_from_packet(packet)
            executor._check_issue_provenance(
                packet,
                experts,
                failures,
                prefix=f"packet_{packet_index}",
            )
            raw_layer_id = packet.get("layer_id")
            if _valid_int(raw_layer_id) and int(raw_layer_id) >= 0:
                layer_id = int(raw_layer_id)
            else:
                layer_id = 0
                failures.append(f"packet_{packet_index}_layer_id_invalid")
        except Exception as exc:
            packet_error_count += 1
            failures.append(
                f"packet_{packet_index}_load_or_parse_failed:{exc.__class__.__name__}:{exc}"
            )
            continue

        packet_count += 1
        layer_ids.add(layer_id)
        requested_issue_count += len(experts)
        _hash_update_json(
            packet_digest,
            {
                "packet_index": packet_index,
                "layer_id": layer_id,
                "issue_hash": executor._issue_hash(list(experts)),
            },
        )
        if not experts:
            continue
        nonempty_packet_count += 1

        if token_timing_enabled:
            context = packet.get("_export_context")
            context = context if isinstance(context, dict) else {}
            raw_token_index = context.get("token_index")
            if _valid_int(raw_token_index) and int(raw_token_index) >= 0:
                token_index = int(raw_token_index)
            else:
                token_index = 0
                failures.append(f"packet_{packet_index}_token_index_invalid")
            token_source = context.get("token_index_source")
            if token_source == "decode_workload_collector":
                token_source_decode_count += 1
            elif token_source == "config":
                token_source_config_count += 1
                if not allow_config_token_source:
                    failures.append(f"packet_{packet_index}_config_token_source_disallowed")
            elif token_source is None:
                token_source_missing_count += 1
                failures.append(f"packet_{packet_index}_token_index_source_missing")
            else:
                failures.append(f"packet_{packet_index}_token_index_source_unexpected")
            raw_issue_token = context.get("issue_token_index")
            expected_issue_token = max(0, token_index - issue_lead_tokens)
            issue_token_index_invalid = raw_issue_token is not None and not (
                _valid_int(raw_issue_token) and int(raw_issue_token) >= 0
            )
            if issue_token_index_invalid:
                shifted_issue_invalid_export_count += 1
                failures.append(f"packet_{packet_index}_issue_token_index_invalid")
            issue_token_index = (
                int(raw_issue_token)
                if _valid_int(raw_issue_token) and int(raw_issue_token) >= 0
                else expected_issue_token
            )
            raw_issue_clamped = context.get("issue_clamped_to_zero")
            expected_issue_clamped = token_index - issue_lead_tokens < 0
            issue_clamped_export_invalid = raw_issue_clamped is not None and not isinstance(
                raw_issue_clamped,
                bool,
            )
            if issue_clamped_export_invalid:
                shifted_issue_invalid_export_count += 1
                failures.append(f"packet_{packet_index}_issue_clamped_to_zero_invalid")
            issue_clamped_to_zero = (
                bool(raw_issue_clamped)
                if isinstance(raw_issue_clamped, bool)
                else expected_issue_clamped
            )
            if issue_token_index != expected_issue_token:
                shifted_issue_row_shift_mismatch_count += 1
                failures.append(f"packet_{packet_index}_issue_token_index_mismatch")
            if issue_clamped_to_zero != expected_issue_clamped:
                shifted_issue_row_clamp_mismatch_count += 1
                failures.append(f"packet_{packet_index}_issue_clamped_to_zero_mismatch")
            sample_idx = context.get("sample_idx")
            record_id = context.get("record_id")
            sequence_id = context.get("sequence_id")
            if not (_valid_int(sample_idx) and int(sample_idx) >= 0):
                failures.append(f"packet_{packet_index}_sample_idx_invalid")
            if not (isinstance(record_id, str) and record_id):
                failures.append(f"packet_{packet_index}_record_id_invalid")
            if not (_valid_int(sequence_id) and int(sequence_id) >= 0):
                sequence_id = 0
            if (
                _valid_int(sample_idx)
                and int(sample_idx) >= 0
                and isinstance(record_id, str)
                and record_id
            ):
                issue_key = (
                    int(sample_idx),
                    record_id,
                    int(sequence_id),
                    layer_id,
                    issue_token_index,
                )
                shifted_issue_accounted_packet_count += 1
                if issue_key in shifted_issue_keys_seen:
                    shifted_issue_duplicate_issue_key_count += 1
                else:
                    shifted_issue_keys_seen.add(issue_key)
                    shifted_issue_unique_issue_key_count += 1
            demand_arrival_us = (
                float(issue_stream.get("issue_arrival_us", 0.0) or 0.0)
                + (float(token_index) * decode_token_us)
                + (float(layer_id) * layer_event_interval_us)
            )
            issue_arrival_us = max(
                0.0,
                demand_arrival_us - (float(issue_lead_tokens) * decode_token_us),
            )
            token_indices.append(token_index)
            issue_token_indices.append(issue_token_index)
        else:
            issue_token_index = packet_index
            issue_clamped_to_zero = False
            issue_arrival_us = float(issue_stream.get("issue_arrival_us", 0.0) or 0.0) + (
                float(packet_index) * float(issue_stream.get("event_interval_us", 1.0) or 1.0)
            )
            demand_arrival_us = issue_arrival_us + float(
                issue_stream.get("demand_gap_us", 0.0) or 0.0
            )

        for expert_id in experts:
            if manager.issue_prefetch(layer_id, expert_id, arrival_us=issue_arrival_us):
                row = _build_row(
                    row_index=len(accepted_rows),
                    packet_index=packet_index,
                    packet_path=packet_path,
                    packet=packet,
                    layer_id=layer_id,
                    expert_id=int(expert_id),
                    issue_token_index=issue_token_index,
                    issue_clamped_to_zero=issue_clamped_to_zero,
                    issue_arrival_us=issue_arrival_us,
                    demand_arrival_us=demand_arrival_us,
                    planned_payload_bytes=planned_payload_bytes_per_issue,
                )
                accepted_rows.append(row)
                _hash_update_json(row_digest, row)
                if len(row_sample) < row_sample_limit:
                    row_sample.append(row)
            manager.demand(layer_id, expert_id, arrival_us=demand_arrival_us)
    manager.finish()
    snapshot = manager.snapshot()

    copy_descriptor_count = len(accepted_rows)
    expected_issued = int(issue_stream.get("issued_prefetch_count", -1) or -1)
    if copy_descriptor_count != expected_issued:
        failures.append("copy_descriptor_count_issued_prefetch_count_mismatch")
    if int(snapshot.issued_fetch_count) != expected_issued:
        failures.append("manager_replay_issued_prefetch_count_mismatch")
    if packet_count != int(issue_stream.get("packet_count", -1) or -1):
        failures.append("packet_count_issue_stream_mismatch")
    if packet_error_count:
        failures.append("packet_error_count_nonzero")
    if nonempty_packet_count != int(issue_stream.get("nonempty_packet_count", -1) or -1):
        failures.append("nonempty_packet_count_issue_stream_mismatch")
    if requested_issue_count != int(issue_stream.get("requested_issue_count", -1) or -1):
        failures.append("requested_issue_count_issue_stream_mismatch")
    if require_same_source_packet_budget:
        online_export_count = int(online.get("online_packet_export_count", -1) or -1)
        configured_export_count = int(online.get("online_configured_export_count", -1) or -1)
        if packet_count != online_export_count or packet_count != configured_export_count:
            failures.append("same_source_packet_budget_mismatch")

    planned_payload_bytes = copy_descriptor_count * planned_payload_bytes_per_issue
    passed = not failures
    payload = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "row_schema_name": ROW_SCHEMA_NAME,
        "passed": passed,
        "failures": failures,
        "copy_descriptor_plan_ready": passed,
        "issue_stream_executor_json": str(executor_path),
        "issue_stream_executor_sha256": _sha256(executor_path),
        "online_canary_json": str(online_path),
        "online_canary_sha256": _sha256(online_path),
        "packet_count": packet_count,
        "nonempty_packet_count": nonempty_packet_count,
        "packet_error_count": packet_error_count,
        "layer_ids": sorted(layer_ids),
        "event_timing_mode": event_timing_mode,
        "token_timing_enabled": bool(token_timing_enabled),
        "allow_config_token_source": bool(allow_config_token_source),
        "issue_lead_tokens": issue_lead_tokens,
        "queue_deadline_us": float(issue_stream.get("queue_deadline_us", 0.0) or 0.0),
        "capacity": int(issue_stream.get("capacity", 0) or 0),
        "requested_issue_count": requested_issue_count,
        "issued_prefetch_count": expected_issued,
        "copy_descriptor_count": copy_descriptor_count,
        "copy_descriptor_shape_checked": copy_descriptor_count == expected_issued,
        "copy_descriptor_submitted": False,
        "copy_descriptor_executed": False,
        "copy_descriptor_row_hash": row_digest.hexdigest(),
        "copy_descriptor_packet_hash": packet_digest.hexdigest(),
        "row_sample_limit": row_sample_limit,
        "row_sample": row_sample,
        "planned_payload_bytes_per_issue": planned_payload_bytes_per_issue,
        "planned_payload_bytes": planned_payload_bytes,
        "payload_bytes": 0,
        "issued_payload_count": 0,
        "payload_transfer_enabled": False,
        "live_payload_runtime_enabled": False,
        "payload_transfer_runtime_enabled": False,
        "payload_deref_allowed": False,
        "payload_deref_runtime_allowed": False,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "full_fetch_runtime_allowed": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
        "live_runtime_instantiated": False,
        "manager_replay_issued_fetch_count": int(snapshot.issued_fetch_count),
        "manager_replay_demand_count": int(snapshot.demand_count),
        "manager_replay_demand_hit_count": int(snapshot.demand_hit_count),
        "manager_replay_ready_late_miss_count": int(snapshot.ready_late_miss_count),
        "manager_replay_used_fetch_count": int(snapshot.used_fetch_count),
        "token_source_decode_workload_count": token_source_decode_count,
        "token_source_config_count": token_source_config_count,
        "token_source_missing_count": token_source_missing_count,
        "shifted_issue_invalid_export_count": shifted_issue_invalid_export_count,
        "shifted_issue_accounted_packet_count": shifted_issue_accounted_packet_count,
        "shifted_issue_unique_issue_key_count": shifted_issue_unique_issue_key_count,
        "shifted_issue_duplicate_issue_key_count": shifted_issue_duplicate_issue_key_count,
        "shifted_issue_row_shift_mismatch_count": shifted_issue_row_shift_mismatch_count,
        "shifted_issue_row_clamp_mismatch_count": shifted_issue_row_clamp_mismatch_count,
        "token_index_min": min(token_indices) if token_indices else None,
        "token_index_max": max(token_indices) if token_indices else None,
        "issue_token_index_min": min(issue_token_indices) if issue_token_indices else None,
        "issue_token_index_max": max(issue_token_indices) if issue_token_indices else None,
        "requires_payload_runtime": False,
        "next_runtime_stage": "payload_copy_worker_submit_blocked_or_native_copy_descriptor_adapter",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-stream-executor-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--planned-payload-bytes-per-issue", type=int, default=64)
    parser.add_argument("--row-sample-limit", type=int, default=16)
    parser.add_argument("--require-same-source-packet-budget", action="store_true")
    parser.add_argument("--allow-config-token-source", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_copy_descriptor_plan(
        issue_stream_executor_json=args.issue_stream_executor_json,
        output_json=args.output_json,
        planned_payload_bytes_per_issue=args.planned_payload_bytes_per_issue,
        row_sample_limit=args.row_sample_limit,
        require_same_source_packet_budget=bool(args.require_same_source_packet_budget),
        allow_config_token_source=bool(args.allow_config_token_source),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.require_pass and not payload.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
